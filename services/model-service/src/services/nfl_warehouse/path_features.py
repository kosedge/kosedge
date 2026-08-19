"""Kickoff-safe NFL line-path features for supervised overlay (schema v5 candidate).

These keys are NOT in the default v3 FEATURE_KEYS. Promote only after
``scripts/nfl/retrain_supervised_path_v5.py`` holdout beats v3.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Tuple

from src.services.nfl_side_total_publish_policy import SPREAD_PLAY_MAX, SPREAD_PLAY_MIN

FEATURE_KEYS_PATH_EXPERIMENTAL: Tuple[str, ...] = (
    "owned_close_spread_home_favored",
    "owned_close_total",
    "steam_spread_pre7d",
    "steam_spread_pre3d",
    "steam_spread_pre1d",
    "steam_total_pre7d",
    "steam_total_pre3d",
    "steam_total_pre1d",
)

MODEL_SCHEMA_VERSION_PATH = 5
PLAY_ABS_EDGE_MIN = SPREAD_PLAY_MIN
PLAY_ABS_EDGE_MAX = SPREAD_PLAY_MAX
MIN_STEAM_PTS = 1.0


def steam_home_favored(steam_spread_api: Any) -> Optional[float]:
    """Odds API steam is close − earlier. Negative steam = home got more favored."""
    if steam_spread_api is None:
        return None
    try:
        return -float(steam_spread_api)
    except (TypeError, ValueError):
        return None


def sides_agree(
    model_edge_home_favored: float,
    steam_hf: Optional[float],
    *,
    min_steam: float = MIN_STEAM_PTS,
) -> bool:
    if steam_hf is None or abs(float(steam_hf)) < min_steam:
        return False
    return (float(model_edge_home_favored) > 0) == (float(steam_hf) > 0)


def in_play_band(abs_edge: float) -> bool:
    return PLAY_ABS_EDGE_MIN <= float(abs_edge) < PLAY_ABS_EDGE_MAX


def path_feature_row(reduced: Mapping[str, Any]) -> Dict[str, Optional[float]]:
    """Extract numeric path features; missing stays None (HGB NaN branch)."""
    out: Dict[str, Optional[float]] = {}
    close_sp = reduced.get("close_spread_home")
    if close_sp is not None:
        try:
            out["owned_close_spread_home_favored"] = -float(close_sp)
        except (TypeError, ValueError):
            out["owned_close_spread_home_favored"] = None
    else:
        out["owned_close_spread_home_favored"] = None
    for key in (
        "owned_close_total",
        "steam_spread_pre7d",
        "steam_spread_pre3d",
        "steam_spread_pre1d",
        "steam_total_pre7d",
        "steam_total_pre3d",
        "steam_total_pre1d",
    ):
        src = key if key != "owned_close_total" else "close_total"
        if key == "owned_close_total":
            src = "close_total"
        val = reduced.get(src)
        try:
            out[key] = float(val) if val is not None else None
        except (TypeError, ValueError):
            out[key] = None
    return out
