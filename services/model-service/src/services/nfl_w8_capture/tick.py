"""Beat tick: due REG close-window samples. Never fetches Odds API.

First sealed capture is NOT this tick. Use the one-shot CLI
``python -m src.services.nfl_w8_capture`` (fetch→snapshot→close→seal).
attempt_fetch stays default False; when True it only refuse_odds_fetch.
Do not wire this tick to OddsHttpTransport or produce_seal.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from src.services.nfl_w8_capture.alerts import control_alert, deliver_alert
from src.services.nfl_w8_capture.cadence import (
    GameKickoff,
    due_sample_windows,
    plan_pre_kickoff_samples,
    review_sample_coverage,
)
from src.services.nfl_w8_capture.fixture_load import SYNTHETIC_W8_REG, load_json_fixture
from src.services.nfl_w8_capture.hold import odds_api_hold_is_on, refuse_odds_fetch
from src.services.nfl_w8_capture.store import BundleStore
from src.services.nfl_w8_capture.timestamps import parse_utc

ENV_KICKOFFS_JSON = "NFL_W8_KICKOFFS_JSON"
ENV_USE_SYNTHETIC = "NFL_W8_USE_SYNTHETIC_SLATE"
ENV_BUNDLE_DIR = "NFL_W8_EVIDENCE_DIR"
ENV_DUE_SLACK_SEC = "NFL_W8_DUE_SLACK_SECONDS"

# Beat default is */2; slack covers one tick interval.
DEFAULT_DUE_SLACK = timedelta(minutes=2)


def load_kickoffs(
    env: Optional[Mapping[str, str]] = None,
) -> list[GameKickoff]:
    source = env if env is not None else os.environ
    path_raw = str(source.get(ENV_KICKOFFS_JSON) or "").strip()
    if path_raw:
        payload = json.loads(Path(path_raw).read_text(encoding="utf-8"))
        return _kickoffs_from_payload(payload)
    flag = str(source.get(ENV_USE_SYNTHETIC) or "").strip().lower()
    if flag in {"1", "true", "yes", "y", "on"}:
        event = load_json_fixture(SYNTHETIC_W8_REG)
        return _kickoffs_from_payload({"games": [event]})
    return []


def _kickoffs_from_payload(payload: Mapping[str, Any]) -> list[GameKickoff]:
    games = payload.get("games")
    if games is None and payload.get("kickoff_utc"):
        games = [payload]
    out: list[GameKickoff] = []
    for raw in games or []:
        kickoff = parse_utc(raw.get("kickoff_utc"))
        if kickoff is None:
            continue
        out.append(
            GameKickoff(
                game_id=str(raw.get("game_id") or ""),
                kickoff_utc=kickoff,
                season_type=str(raw.get("season_type") or "REG"),
            )
        )
    return out


def run_capture_tick(
    *,
    now_utc: Optional[datetime] = None,
    env: Optional[Mapping[str, str]] = None,
    bundle_dir: Optional[str | Path] = None,
    kickoffs: Optional[Sequence[GameKickoff]] = None,
    attempt_fetch: bool = False,
) -> dict[str, Any]:
    """Plan due close-window samples. Hold blocks any fetch.

    Not the first-seal path. Live fetch/seal stays on the one-shot CLI.
    """
    source = env if env is not None else os.environ
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    slack_raw = str(source.get(ENV_DUE_SLACK_SEC) or "").strip()
    slack = timedelta(seconds=int(slack_raw)) if slack_raw else DEFAULT_DUE_SLACK

    games = list(kickoffs) if kickoffs is not None else load_kickoffs(source)
    plan = plan_pre_kickoff_samples(games, now_utc=now)
    due = due_sample_windows(plan, now_utc=now, slack=slack)

    root = Path(
        bundle_dir
        or source.get(ENV_BUNDLE_DIR)
        or (Path.cwd() / "data" / "ops" / "nfl-w8-capture-bundle")
    )
    store = BundleStore(root)

    if attempt_fetch:
        if odds_api_hold_is_on(source):
            deliver_alert(
                control_alert(
                    kind="hold",
                    detail="tick attempt_fetch refused: hold default-on",
                    market="hold",
                ),
                store,
                env=source,
            )
        refuse_odds_fetch(env=source)

    deliveries: list[dict[str, Any]] = []
    for window in due:
        # No live snapshot under hold → coverage is MISSING for this tick.
        alert = review_sample_coverage(
            game_id=window.game_id,
            market="spreads",
            book_statuses=[],
        )
        delivery = deliver_alert(alert, store, env=source)
        deliveries.append(
            {
                "game_id": window.game_id,
                "sample_at": window.sample_at.isoformat(),
                "in_close_window": window.in_close_window,
                "alert": alert.kind,
                "delivery": delivery.status,
            }
        )

    return {
        "now_utc": now.isoformat(),
        "games": len(games),
        "planned_windows": len(plan.windows),
        "due_windows": len(due),
        "close_window_due": sum(1 for w in due if w.in_close_window),
        "odds_fetch": "blocked_hold",
        "bundle": str(store.root),
        "deliveries": deliveries,
    }
