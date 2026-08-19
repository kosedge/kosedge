"""Hard lock: PLAY band, blend weights, weekly props stay gated."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.nfl_side_total_publish_policy import (
    POLICY_VERSION,
    SPREAD_PLAY_MAX,
    SPREAD_PLAY_MIN,
    candidate_tag,
)
from src.services.nfl_simulator import NFL_MARKET_BLEND_SPREAD_WEIGHT, NFL_MARKET_BLEND_TOTAL_WEIGHT
from src.services.nfl_warehouse.path_features import PLAY_ABS_EDGE_MAX, PLAY_ABS_EDGE_MIN
from src.services.nfl_warehouse.weekly_prop_means import should_touch_season_artifacts


def test_play_band_is_spread_play_v2_cap7() -> None:
    assert POLICY_VERSION == "spread_play_v2_cap7"
    assert SPREAD_PLAY_MIN == 2.5
    assert SPREAD_PLAY_MAX == 7.0
    assert PLAY_ABS_EDGE_MIN == SPREAD_PLAY_MIN
    assert PLAY_ABS_EDGE_MAX == SPREAD_PLAY_MAX
    assert candidate_tag("spread", 2.5) == "PLAY"
    assert candidate_tag("spread", 6.99) == "PLAY"
    assert candidate_tag("spread", 7.0) == "PASS"


def test_blend_weights_stay_at_gate_default() -> None:
    assert NFL_MARKET_BLEND_SPREAD_WEIGHT == 0.30
    assert NFL_MARKET_BLEND_TOTAL_WEIGHT == 0.30


def test_weekly_props_and_season_artifacts_stay_off() -> None:
    assert should_touch_season_artifacts() is False
    web = Path(__file__).resolve().parents[3] / "apps" / "web" / "lib" / "nfl-weekly-props-live.ts"
    text = web.read_text(encoding="utf-8")
    assert "export const NFL_WEEKLY_PROPS_LIVE = false" in text
