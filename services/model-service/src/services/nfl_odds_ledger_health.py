"""NFL odds warehouse ledger lag health — ops/diagnostics only (#5 R1 Slice B).

Reads MAX(captured_at) from raw ``odds_snapshots`` (NFL-scoped) and
``nfl_market_history_snapshots``. Does **not** invent FRESH/AGING/STALE product
windows, CLOSE/Best formulas, or beat probes.

``diagnostics.odds_persisted`` zeros on subscriber ``persist=0`` GET are expected
and must not be read as a dark warehouse ledger — use this nested block instead.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

log = logging.getLogger(__name__)

LedgerHealthStatus = Literal["ok", "history_lagging", "raw_dark", "unknown"]

ODDS_LEDGER_HEALTH_NOTE = (
    "ops-only: odds_persisted zeros on persist=0 page-data/subscriber GET "
    "≠ dark warehouse ledger. last_* timestamps are MAX(captured_at) from "
    "beat/worker-owned tables; no FRESH/AGING/STALE product windows."
)

# Bound cold MAX on large odds_snapshots so fair-lines / Edge Board never hang.
# Bare '2000' = 2000ms in Postgres. Timeout → ledger_health=unknown (fail closed).
LEDGER_PROBE_STATEMENT_TIMEOUT = "2000"

_LEDGER_MAX_SQL = """
SELECT
  (
    SELECT MAX(os.captured_at)
    FROM odds_snapshots os
    JOIN games g ON g.id = os.game_id
    JOIN seasons s ON s.id = g.season_id
    JOIN leagues l ON l.id = s.league_id
    WHERE l.code = 'nfl'
  ) AS last_odds_snapshot_captured_at,
  (
    SELECT MAX(mhs.captured_at)
    FROM nfl_market_history_snapshots mhs
  ) AS last_market_history_captured_at
"""


def _as_utc(ts: Optional[datetime]) -> Optional[datetime]:
    if ts is None:
        return None
    if not isinstance(ts, datetime):
        return None
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def _iso_or_none(ts: Optional[datetime]) -> Optional[str]:
    aware = _as_utc(ts)
    if aware is None:
        return None
    return aware.isoformat()


def history_lag_seconds(
    raw_max: Optional[datetime],
    history_max: Optional[datetime],
) -> Optional[int]:
    """Seconds raw is ahead of history. Null if either timestamp is missing.

    Positive ⇒ history behind raw. Negative ⇒ history ahead of raw (ok).
    """
    raw = _as_utc(raw_max)
    hist = _as_utc(history_max)
    if raw is None or hist is None:
        return None
    return int((raw - hist).total_seconds())


def derive_ledger_health(
    *,
    raw_max: Optional[datetime],
    history_max: Optional[datetime],
    probe_ok: bool = True,
) -> LedgerHealthStatus:
    """Classify ledger health from warehouse timestamps only.

    Rules (Slice B — document in PR; no customer STALE labels):
    - ``unknown`` when the DB probe failed
    - ``raw_dark`` when MAX(odds_snapshots.captured_at) is missing (NFL-scoped)
    - ``history_lagging`` when raw exists and history is missing **or**
      ``history_lag_seconds > 0`` (history strictly behind raw)
    - ``ok`` when both exist and history is not behind raw (lag <= 0)
    """
    if not probe_ok:
        return "unknown"
    if raw_max is None:
        return "raw_dark"
    lag = history_lag_seconds(raw_max, history_max)
    if history_max is None or (lag is not None and lag > 0):
        return "history_lagging"
    return "ok"


def build_odds_ledger_health_payload(
    *,
    raw_max: Optional[datetime] = None,
    history_max: Optional[datetime] = None,
    probe_ok: bool = True,
) -> Dict[str, Any]:
    """Snake_case payload nested under fair-lines ``diagnostics.odds_ledger_health``."""
    return {
        "last_odds_snapshot_captured_at": _iso_or_none(raw_max) if probe_ok else None,
        "last_market_history_captured_at": _iso_or_none(history_max) if probe_ok else None,
        "history_lag_seconds": history_lag_seconds(raw_max, history_max) if probe_ok else None,
        "ledger_health": derive_ledger_health(
            raw_max=raw_max if probe_ok else None,
            history_max=history_max if probe_ok else None,
            probe_ok=probe_ok,
        ),
        "note": ODDS_LEDGER_HEALTH_NOTE,
    }


def probe_nfl_odds_ledger_health(session: Any) -> Dict[str, Any]:
    """Cheap MAX(captured_at) probe; never raises into the fair-lines board.

    Applies ``SET LOCAL statement_timeout`` so a cold scan of large
    ``odds_snapshots`` fails closed to ``ledger_health=unknown`` instead of
    hanging fair-lines / Edge Board assemble.
    """
    try:
        session.execute(
            text(f"SET LOCAL statement_timeout = '{LEDGER_PROBE_STATEMENT_TIMEOUT}'")
        )
        row = session.execute(text(_LEDGER_MAX_SQL)).fetchone()
    except SQLAlchemyError:
        # Includes Postgres statement_timeout / query canceled.
        log.exception("NFL odds ledger health probe failed")
        return build_odds_ledger_health_payload(probe_ok=False)
    except Exception:
        log.exception("NFL odds ledger health probe unexpected failure")
        return build_odds_ledger_health_payload(probe_ok=False)

    if row is None:
        return build_odds_ledger_health_payload(probe_ok=False)

    mapped = dict(row._mapping) if hasattr(row, "_mapping") else {}
    raw_max = mapped.get("last_odds_snapshot_captured_at")
    history_max = mapped.get("last_market_history_captured_at")
    if raw_max is not None and not isinstance(raw_max, datetime):
        raw_max = None
    if history_max is not None and not isinstance(history_max, datetime):
        history_max = None
    return build_odds_ledger_health_payload(
        raw_max=raw_max,
        history_max=history_max,
        probe_ok=True,
    )
