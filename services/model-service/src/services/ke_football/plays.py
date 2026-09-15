"""Canonical play record + small helpers. Sport adapters fill this shape."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


def finite(raw: Any) -> Optional[float]:
    if raw is None or raw == "":
        return None
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(val):
        return None
    return val


def truthy(raw: Any) -> Optional[bool]:
    """None if the column is absent / unusable; else bool."""
    if raw is None or raw == "" or (isinstance(raw, float) and raw != raw):
        return None
    if isinstance(raw, bool):
        return raw
    if raw in (0, "0", "false", "False", "f", "F", "no"):
        return False
    if raw in (1, "1", "true", "True", "t", "T", "yes"):
        return True
    text = str(raw).strip().lower()
    if text in {"nan", "<na>", "none"}:
        return None
    return text in {"1", "true", "t", "yes"}


def standard_success(*, down: Optional[float], distance: Optional[float], yards: Optional[float]) -> Optional[bool]:
    """Football Study Hall 50/70/100. None if any input is missing."""
    if down is None or distance is None or yards is None or distance <= 0:
        return None
    d = int(down)
    if d <= 1:
        need = 0.50 * distance
    elif d == 2:
        need = 0.70 * distance
    else:
        need = distance
    return yards + 1e-9 >= need


@dataclass
class CanonicalPlay:
    sport: str
    season: int
    week: int
    game_id: str
    play_id: str
    offense: str
    defense: str
    home: str
    away: str
    is_scrimmage: bool
    is_st: bool
    play_type: str
    epa: Optional[float]
    success_native: Optional[bool]
    yards: Optional[float]
    down: Optional[float]
    distance: Optional[float]
    yards_to_endzone: Optional[float]
    drive_id: Optional[str]
    score_diff: Optional[float]
    game_seconds_remaining: Optional[float]
    period: Optional[int]
    is_pass: bool = False
    is_rush: bool = False
    touchdown: Optional[bool] = None
    points: int = 0
    points_source: str = ""
    sack: Optional[bool] = None
    interception: Optional[bool] = None
    qb_hit: Optional[bool] = None
    fumble: Optional[bool] = None
    fumble_forced: Optional[bool] = None
    tfl: Optional[bool] = None
    pass_breakup: Optional[bool] = None
    havoc_vendor: Optional[bool] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def overtime(self) -> bool:
        return self.period is not None and self.period >= 5
