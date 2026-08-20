"""NFL rematerialize week policy.

Bare ``season=`` rebuilds used to resolve ``MAX(week)`` on usage (week 22 for
historical seasons) and land on the Celery ``default`` queue. That is the
week-22 wipe class from the #268 / LIVE-smoke incident.

Contract:
- Regular-season remat default is weeks 1–18.
- Playoff weeks (19–22) are allowed only when explicitly passed.
- Beat cycle week is clamped to 1–18 so env cannot re-enqueue week 22.
"""

from __future__ import annotations

import ast
import os
from typing import Any, Iterable, List, Optional, Sequence

NFL_REGULAR_SEASON_MIN_WEEK = 1
NFL_REGULAR_SEASON_MAX_WEEK = 18
NFL_REGULAR_SEASON_WEEKS: List[int] = list(
    range(NFL_REGULAR_SEASON_MIN_WEEK, NFL_REGULAR_SEASON_MAX_WEEK + 1)
)

POISON_REMAT_TASKS = frozenset(
    {
        "src.tasks.run_nfl_props_layer_rebuild",
        "src.tasks.materialize_nfl_player_baseline_projections",
        "src.tasks.materialize_nfl_player_projection_features",
    }
)

NFL_MODELS_QUEUE_TASKS = (
    "src.tasks.run_nfl_props_layer_rebuild",
    "src.tasks.materialize_nfl_player_baseline_projections",
    "src.tasks.materialize_nfl_player_projection_features",
    "src.tasks.materialize_nfl_player_box_score_sims",
    "src.tasks.materialize_nfl_player_props_edges",
    "src.tasks.materialize_nfl_fantasy_projections",
    "src.tasks.materialize_nfl_fantasy_season_draft_rankings",
    "src.tasks.materialize_nfl_award_projections",
    "src.tasks.run_nfl_player_projection_cycle",
    "src.tasks.run_nfl_identity_refresh",
    "src.tasks.apply_nfl_identity_manual_resolutions",
    "src.tasks.run_nfl_identity_quality_snapshot",
    "src.tasks.run_nfl_weekly_resilience_cycle",
    "src.tasks.run_nfl_enterprise_weekly_sharpening_cycle",
    "src.tasks.run_nfl_supervised_retrain",
    "src.tasks.run_nfl_walkforward_backtest",
    "src.tasks.run_nfl_data_freshness_check",
    "src.tasks.run_nfl_dr_backup",
    "src.tasks.pull_nfl_player_prop_market_snapshots",
)


def clamp_cycle_week(week: Any, default: int = 1) -> int:
    try:
        parsed = int(week)
    except (TypeError, ValueError):
        parsed = int(default)
    return max(NFL_REGULAR_SEASON_MIN_WEEK, min(parsed, NFL_REGULAR_SEASON_MAX_WEEK))


def cycle_week_from_env() -> int:
    return clamp_cycle_week(os.getenv("NFL_PLAYER_CYCLE_WEEK", "1"))


def resolve_remat_weeks(
    *,
    week: Optional[int] = None,
    weeks: Optional[Sequence[int]] = None,
) -> List[int]:
    """Return the week list a remat job should run.

    Explicit ``weeks`` wins. Explicit ``week`` is a one-week remat (playoff
    weeks allowed). Season-only (both missing) expands to regular season 1–18
    — never ``MAX(week)``.
    """
    if weeks:
        resolved = sorted({int(w) for w in weeks if w is not None})
        if resolved:
            return resolved
    if week is not None:
        return [int(week)]
    return list(NFL_REGULAR_SEASON_WEEKS)


def is_bare_season_kwargs(kwargs: Optional[dict[str, Any]]) -> bool:
    if not kwargs:
        return True
    weeks = kwargs.get("weeks")
    week = kwargs.get("week")
    has_weeks = bool(weeks)
    has_week = week is not None
    return not has_weeks and not has_week


def _parse_kwargsrepr(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not raw or not isinstance(raw, str):
        return {}
    try:
        parsed = ast.literal_eval(raw)
    except (SyntaxError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def decode_celery_message(raw: Any) -> dict[str, Any]:
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", "replace")
    if isinstance(raw, str):
        import json

        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            return {"parse_error": True, "prefix": raw[:160]}
    elif isinstance(raw, dict):
        body = raw
    else:
        return {"parse_error": True}
    headers = body.get("headers") or {}
    kwargs = body.get("kwargs")
    if not isinstance(kwargs, dict):
        kwargs = _parse_kwargsrepr(headers.get("kwargsrepr"))
    return {
        "task": headers.get("task") or body.get("task"),
        "id": headers.get("id") or body.get("id"),
        "kwargs": kwargs if isinstance(kwargs, dict) else {},
        "kwargsrepr": headers.get("kwargsrepr"),
        "args": body.get("args") or headers.get("argsrepr"),
    }


def is_poison_remat(info: dict[str, Any]) -> bool:
    """True for bare season remats / implicit week-22 wipe class."""
    task = str(info.get("task") or "")
    if task not in POISON_REMAT_TASKS:
        return False
    kwargs = info.get("kwargs") if isinstance(info.get("kwargs"), dict) else {}
    if is_bare_season_kwargs(kwargs):
        return True
    weeks = kwargs.get("weeks") or []
    week = kwargs.get("week")
    if task == "src.tasks.run_nfl_props_layer_rebuild":
        only_weeks = [int(w) for w in weeks] if weeks else ([int(week)] if week is not None else [])
        return only_weeks == [22]
    if week is None and not weeks:
        return True
    if week == 22 and not weeks:
        return True
    return False


def redact_broker_url(url: str) -> str:
    from urllib.parse import urlsplit, urlunsplit

    if not url:
        return "unset"
    parts = urlsplit(url)
    if not parts.hostname:
        return "redacted"
    host = parts.hostname
    if parts.port:
        host = f"{host}:{parts.port}"
    if parts.username:
        host = f"{parts.username}:***@{host}"
    return urlunsplit((parts.scheme, host, parts.path, "", ""))
