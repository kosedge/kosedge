"""Path A2 — prior-year usage-share anchor (not path-end yard blend)."""

from __future__ import annotations

from src.services.nfl_season_engine.calibration import ENGINE_VERSION
from src.services.nfl_season_engine.player_usage import (
    anchor_roles_to_prior_usage_shares,
)
from src.services.nfl_season_engine.types import PlayerRole


def test_engine_version_path_a2() -> None:
    assert "pathA2" in ENGINE_VERSION or "usage-prior" in ENGINE_VERSION


def test_returning_wr_target_share_pulls_toward_prior() -> None:
    role = PlayerRole(
        player_key="KC-WR1-Rice",
        player_name="R.Rice",
        team="KC",
        position="WR",
        depth_order=1,
        player_id="00-0039900",
        target_share=0.22,  # depth archetype
        snap_share=0.85,
        route_share=0.90,
        source="depth",
    )
    prior = {
        "00-0039900": {
            "targets": 120.0,
            "rush_attempts": 0.0,
            "target_share": 0.28,
            "rush_share": 0.0,
        }
    }
    out, diag = anchor_roles_to_prior_usage_shares([role], prior, weight=0.80)
    assert diag["anchored_target"] == 1
    # 0.2 * 0.22 + 0.8 * 0.28 = 0.268
    assert out[0].target_share == 0.268
    assert "prior_usage_anchor" in out[0].source


def test_rookie_without_prior_keeps_depth_share() -> None:
    role = PlayerRole(
        player_key="KC-WR3-Rook",
        player_name="A.Rookie",
        team="KC",
        position="WR",
        depth_order=3,
        player_id="00-0099999",
        target_share=0.09,
        source="depth",
        is_rookie=True,
    )
    out, diag = anchor_roles_to_prior_usage_shares([role], {}, weight=0.80)
    assert diag["anchored_target"] == 0
    assert out[0].target_share == 0.09
    assert out[0].source == "depth"


def test_qb_prior_anchors_rush_not_inventing_pass_share() -> None:
    role = PlayerRole(
        player_key="BAL-QB1-Jackson",
        player_name="L.Jackson",
        team="BAL",
        position="QB",
        depth_order=1,
        player_id="00-0034796",
        snap_share=0.97,
        rush_share=0.07,
        target_share=0.0,
        source="depth",
    )
    prior = {
        "00-0034796": {
            "targets": 0.0,
            "rush_attempts": 150.0,
            "target_share": 0.0,
            "rush_share": 0.18,
        }
    }
    out, diag = anchor_roles_to_prior_usage_shares([role], prior, weight=0.80)
    assert diag["anchored_rush"] == 1
    assert diag["anchored_target"] == 0
    # 0.2 * 0.07 + 0.8 * 0.18 = 0.158
    assert out[0].rush_share == 0.158
    assert out[0].target_share == 0.0
    assert out[0].snap_share == 0.97
