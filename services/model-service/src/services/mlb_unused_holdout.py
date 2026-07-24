"""Pre-registered MLB unused holdout — forbidden for train/tune.

Stake marketing for moneyline / totals / run-line may only claim after this
slice is evaluated and passes. Props stay research-only
(`PLAY_STAKE_ELIGIBLE=false`) regardless.

Registry artifact (source of truth for dates):
  data/ops/mlb-enterprise-holdout/unused_holdout_registry.json
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set

# Repo-relative default; overridden via MLB_UNUSED_HOLDOUT_REGISTRY env in ops.
_DEFAULT_REGISTRY_CANDIDATES = (
    Path(__file__).resolve().parents[4]
    / "data"
    / "ops"
    / "mlb-enterprise-holdout"
    / "unused_holdout_registry.json",
    Path.cwd() / "data" / "ops" / "mlb-enterprise-holdout" / "unused_holdout_registry.json",
)

# Frozen fallback if the artifact is missing (must match registry windows).
FALLBACK_UNUSED_WINDOWS: tuple[Dict[str, str], ...] = (
    {
        "id": "late_july_2026_frozen",
        "start_date": "2026-07-18",
        "end_date": "2026-07-23",
        "role": "unused_evaluation",
    },
    {
        "id": "post_july_2026_reserved",
        "start_date": "2026-07-25",
        "end_date": "2026-08-10",
        "role": "reserved_future",
    },
)


def _registry_path() -> Optional[Path]:
    import os

    override = (os.getenv("MLB_UNUSED_HOLDOUT_REGISTRY") or "").strip()
    if override:
        p = Path(override)
        return p if p.exists() else None
    for candidate in _DEFAULT_REGISTRY_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


@lru_cache(maxsize=4)
def load_unused_holdout_registry() -> Dict[str, Any]:
    path = _registry_path()
    if path is None:
        return {
            "title": "MLB enterprise unused holdout (fallback constants)",
            "status": "frozen_unused",
            "source": "fallback_constants",
            "windows": list(FALLBACK_UNUSED_WINDOWS),
        }
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"unused holdout registry must be an object: {path}")
    payload = dict(payload)
    payload.setdefault("source", str(path))
    return payload


def clear_unused_holdout_cache() -> None:
    load_unused_holdout_registry.cache_clear()
    unused_holdout_date_set.cache_clear()


def _iter_iso_dates(start: str, end: str) -> Iterable[str]:
    from datetime import date, timedelta

    start_d = date.fromisoformat(str(start)[:10])
    end_d = date.fromisoformat(str(end)[:10])
    if end_d < start_d:
        return
    cur = start_d
    while cur <= end_d:
        yield cur.isoformat()
        cur += timedelta(days=1)


@lru_cache(maxsize=4)
def unused_holdout_date_set(*, roles: Optional[tuple[str, ...]] = None) -> frozenset[str]:
    """Calendar dates forbidden for train/tune (evaluation-only)."""
    registry = load_unused_holdout_registry()
    allowed_roles = set(roles) if roles is not None else {
        "unused_evaluation",
        "reserved_future",
    }
    dates: Set[str] = set()
    for window in registry.get("windows") or []:
        if not isinstance(window, Mapping):
            continue
        role = str(window.get("role") or "unused_evaluation")
        if role not in allowed_roles:
            continue
        start = window.get("start_date")
        end = window.get("end_date")
        if not start or not end:
            continue
        dates.update(_iter_iso_dates(str(start), str(end)))
    return frozenset(dates)


def is_unused_holdout_date(game_date: Any) -> bool:
    if game_date is None:
        return False
    key = str(game_date)[:10]
    return key in unused_holdout_date_set()


def filter_points_excluding_unused_holdout(
    points: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """Drop unused-holdout games — use for train / tune / calibration fit."""
    out: List[Dict[str, Any]] = []
    for p in points:
        if is_unused_holdout_date(p.get("game_date")):
            continue
        out.append(dict(p))
    return out


def filter_points_in_unused_holdout(
    points: Sequence[Mapping[str, Any]],
    *,
    roles: Optional[tuple[str, ...]] = ("unused_evaluation",),
) -> List[Dict[str, Any]]:
    """Keep only unused-holdout games — use for stake-gate evaluation."""
    allowed = unused_holdout_date_set(roles=roles)
    out: List[Dict[str, Any]] = []
    for p in points:
        key = str(p.get("game_date") or "")[:10]
        if key in allowed:
            out.append(dict(p))
    return out


def unused_holdout_summary() -> Dict[str, Any]:
    registry = load_unused_holdout_registry()
    dates = sorted(unused_holdout_date_set())
    return {
        "title": registry.get("title"),
        "status": registry.get("status"),
        "registered_at": registry.get("registered_at"),
        "source": registry.get("source"),
        "window_count": len(registry.get("windows") or []),
        "date_count": len(dates),
        "first_date": dates[0] if dates else None,
        "last_date": dates[-1] if dates else None,
        "props_play_stake_eligible": False,
        "stake_marketing_requires_unused_pass": True,
    }
