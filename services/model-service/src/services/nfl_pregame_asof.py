"""Shared Independent Fair / #665 pregame as-of contract (t4822u).

Authority: DECISION 312d4c65 · ORDER 9c9f7cfc · finding 4219a1bb (ACCEPT).

Trace (verified on this tree, pin ``ingest.py@1b39f4e9`` preserved as reference):

* ``rating_week`` is the **completed-data** week: the CURRENT ROW of
  ``ROWS BETWEEN 4 PRECEDING AND CURRENT ROW`` on
  ``nfl_dp_team_situational_weekly`` (ingest L1283–1314). It is not the
  forecast target.
* Pin matchup materialization joined ``h.week = s.week`` (L1497–1501).
  Combined with CURRENT ROW that lets a Week-W forecast consume Week-W
  game stats (target-game leakage into raw IF).
* Correct join: last admissible completed rating week, normally
  ``target_week - 1``. No latest-week substitute on bye / missing /
  stale / incomplete source.

This module is the single lag rule for the IF matchup join and the
snap-share exposure ledger. It does not score, rematerialize, or wire
Independent Fair.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Iterable, Optional, Sequence

# Sealed #657 / IF ingest pin. Do not treat this SHA as the corrected join.
PINNED_IF_INGEST_SHA = "1b39f4e9"
PINNED_IF_SAME_WEEK_JOIN_CITE = (
    "services/model-service/data_platform_nfl/ingest.py@1b39f4e9 L1497-1501"
)
PINNED_IF_5G_FRAME_CITE = (
    "services/model-service/data_platform_nfl/ingest.py@1b39f4e9 L1305-1314"
)

# Rolling frame is unchanged. CURRENT ROW is legal only when that row is
# completed historical information available before the target cutoff.
IF_5G_SQL_FRAME = (
    "nfl_dp_team_situational_weekly WHERE season=:season; "
    "PARTITION BY team ORDER BY season, week "
    "ROWS BETWEEN 4 PRECEDING AND CURRENT ROW"
)

# Pin join (leakage). Kept so tests can prove we left it.
PINNED_IF_MATCHUP_JOIN_HOME = (
    "h.season = s.season AND h.week = s.week AND h.team = s.home_team"
)
PINNED_IF_MATCHUP_JOIN_AWAY = (
    "a.season = s.season AND a.week = s.week AND a.team = s.away_team"
)

# Corrected contiguous pregame join. Exact week-1; no MAX(week) fallback.
IF_MATCHUP_ROLLING_JOIN_HOME = (
    "h.season = s.season AND h.week = (s.week - 1) AND h.team = s.home_team"
)
IF_MATCHUP_ROLLING_JOIN_AWAY = (
    "a.season = s.season AND a.week = (s.week - 1) AND a.team = s.away_team"
)

IF_MATCHUP_ASOF_CONTRACT = (
    "pregame as-of: every consumed game completed and required source "
    "available before target forecast cutoff; "
    "rating_week = target_week - 1 (contiguous weekly IF pipeline); "
    "no silent substitute window"
)

REJECT_TARGET_WEEK_INVALID = "TARGET_WEEK_INVALID"
REJECT_RATING_WEEK_NOT_LAGGED = "RATING_WEEK_NOT_LAGGED"
REJECT_RATING_WEEK_STALE = "RATING_WEEK_STALE"
REJECT_RATING_WEEK_UNRESOLVED = "RATING_WEEK_UNRESOLVED"
REJECT_FUTURE_GAME_IN_WINDOW = "FUTURE_GAME_IN_WINDOW"
REJECT_AS_OF_VIOLATION = "AS_OF_VIOLATION"
REJECT_INPUT_INVALID = "INPUT_INVALID"


class PregameAsofReject(Exception):
    """Fail-closed as-of reject. Never substitute a different week."""

    def __init__(self, code: str, message: str) -> None:
        self.code = str(code)
        self.message = str(message)
        super().__init__(f"{self.code}: {self.message}")


def require_positive_week(value: Any, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise PregameAsofReject(
            REJECT_TARGET_WEEK_INVALID
            if field_name == "target_week"
            else REJECT_INPUT_INVALID,
            f"{field_name} must be a positive int (no impute)",
        )
    return value


def contiguous_pregame_rating_week(target_week: int) -> int:
    """Approved contiguous weekly pipeline: last completed week before target."""
    week = require_positive_week(target_week, field_name="target_week")
    rating_week = week - 1
    if rating_week < 1:
        raise PregameAsofReject(
            REJECT_TARGET_WEEK_INVALID,
            f"target_week={week} has no prior completed rating week "
            f"(week-1 forecast cannot join a same-week or empty window)",
        )
    return rating_week


def resolve_pregame_rating_week(
    *,
    target_week: Any,
    rating_week: Any = None,
    available_rating_weeks: Optional[Iterable[int]] = None,
) -> int:
    """Return the exact pregame rating week. No latest-week substitute.

    ``available_rating_weeks`` is the set of completed-data weeks that
    actually exist (situational / rolling rows). A bye or missing
    ``target_week - 1`` row is unresolved — not filled from week-2.
    """
    target = require_positive_week(target_week, field_name="target_week")
    expected = contiguous_pregame_rating_week(target)
    if rating_week is None:
        resolved = expected
    else:
        if isinstance(rating_week, bool) or not isinstance(rating_week, int):
            raise PregameAsofReject(
                REJECT_INPUT_INVALID, "rating_week must be a positive int"
            )
        resolved = rating_week
        if resolved < 1:
            raise PregameAsofReject(
                REJECT_INPUT_INVALID, "rating_week must be a positive int"
            )
        if resolved >= target:
            raise PregameAsofReject(
                REJECT_RATING_WEEK_NOT_LAGGED,
                f"rating_week={resolved} is not < target_week={target} "
                f"(same-week / future rating row is target-game leakage)",
            )
        if resolved != expected:
            raise PregameAsofReject(
                REJECT_RATING_WEEK_STALE,
                f"rating_week={resolved} is stale for target_week={target}; "
                f"contiguous pipeline requires rating_week={expected} "
                f"(no silent substitute window)",
            )
    if available_rating_weeks is not None:
        available = {int(w) for w in available_rating_weeks}
        if resolved not in available:
            raise PregameAsofReject(
                REJECT_RATING_WEEK_UNRESOLVED,
                f"no completed rating row at rating_week={resolved} "
                f"for target_week={target} (bye / missing-week / incomplete "
                f"source — not filled from a later or earlier week)",
            )
    return resolved


def reject_if_not_pregame_game(
    *,
    game_week: int,
    target_week: int,
    game_id: Optional[str] = None,
    target_game_id: Optional[str] = None,
    game_date: Any = None,
    target_game_date: Any = None,
    game_kickoff_ts: Any = None,
    forecast_cutoff_ts: Any = None,
) -> None:
    """Fail closed if a candidate game is the target or is in the future."""
    label = game_id or f"week {game_week}"
    if int(game_week) >= int(target_week):
        raise PregameAsofReject(
            REJECT_FUTURE_GAME_IN_WINDOW,
            f"{label} week={game_week} is not < target_week={target_week}",
        )
    if target_game_id and game_id and str(game_id) == str(target_game_id):
        raise PregameAsofReject(
            REJECT_FUTURE_GAME_IN_WINDOW,
            f"target game_id {target_game_id} cannot enter the historical window",
        )
    if target_game_date is not None:
        if game_date is None:
            raise PregameAsofReject(
                REJECT_FUTURE_GAME_IN_WINDOW,
                f"{label} missing game_date while target_game_date is bound "
                f"(cannot verify pregame as-of)",
            )
        if _as_date(game_date) >= _as_date(target_game_date):
            raise PregameAsofReject(
                REJECT_FUTURE_GAME_IN_WINDOW,
                f"{label} game_date {game_date} is not before target "
                f"game_date {target_game_date}",
            )
    if forecast_cutoff_ts is not None and game_kickoff_ts is not None:
        if _as_utc(game_kickoff_ts) >= _as_utc(forecast_cutoff_ts):
            raise PregameAsofReject(
                REJECT_AS_OF_VIOLATION,
                f"{label} kickoff {game_kickoff_ts} is not before "
                f"forecast_cutoff_ts {forecast_cutoff_ts}",
            )


def resolve_if_matchup_rolling_row(
    *,
    target_week: int,
    team: str,
    rolling_weeks: Sequence[int],
) -> int:
    """Python reconstruction of the corrected IF matchup rolling join.

    Returns the single rating week that ``nfl_dp_matchup_features_weekly``
    may consume for a schedule game at ``target_week``. Missing
    ``target_week - 1`` does not fall back to the latest earlier week.
    """
    return resolve_pregame_rating_week(
        target_week=target_week,
        available_rating_weeks=rolling_weeks,
    )


def _as_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = str(value).strip()
    if not raw:
        raise PregameAsofReject(REJECT_INPUT_INVALID, "game_date empty (no impute)")
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        if "T" in raw:
            return datetime.fromisoformat(raw).date()
        return date.fromisoformat(raw[:10])
    except ValueError as exc:
        raise PregameAsofReject(
            REJECT_INPUT_INVALID, f"game_date unparseable: {value!r}"
        ) from exc


def _as_utc(value: Any) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        raw = str(value).strip()
        if not raw:
            raise PregameAsofReject(
                REJECT_INPUT_INVALID, "timestamp empty (no impute)"
            )
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(raw)
        except ValueError as exc:
            raise PregameAsofReject(
                REJECT_INPUT_INVALID, f"timestamp unparseable: {value!r}"
            ) from exc
    if dt.tzinfo is None:
        raise PregameAsofReject(
            REJECT_INPUT_INVALID,
            "naive timestamp rejected (no impute to UTC); offset or Z required",
        )
    return dt.astimezone(timezone.utc)
