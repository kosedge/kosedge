"""Optional overlay of archive close-implied weekly player means.

Season artifacts / DFS / fantasy stay on the packaged season-engine path.
This hook is off until prop-archive holdout beats frozen calibration.
"""

from __future__ import annotations

import os
from typing import Any, Mapping, Optional

ENABLED = os.getenv("NFL_WEEKLY_PROP_MEANS_FROM_LAKE", "").strip() in {"1", "true", "yes"}


def overlay_weekly_mean(
    market_key: str,
    engine_mean: float,
    *,
    close_line: Optional[float] = None,
    enabled: bool = ENABLED,
) -> float:
    """Return engine_mean unless the lake overlay is explicitly enabled."""
    if not enabled or close_line is None:
        return float(engine_mean)
    # Conservative 15% shrink toward close — same spirit as prop market shrink.
    return (0.85 * float(engine_mean)) + (0.15 * float(close_line))


def should_touch_season_artifacts() -> bool:
    return False
