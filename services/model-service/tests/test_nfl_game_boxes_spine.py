"""Game Boxes spine overlay — Props mean and Boxes headline must agree."""

from __future__ import annotations

from src.services.nfl_game_boxes_spine import overlay_spine_means_on_players
from src.services.nfl_player_production import PRODUCTION_VERSION


def test_overlay_replaces_mc_median_with_spine_mean_maye() -> None:
    players = [
        {
            "player_name": "Drake Maye",
            "team": "NE",
            "position": "QB",
            "point_estimate": {"pass_yards": 198.0, "rush_yards": 15.8},
            "distributions": {
                "pass_yards": {
                    "mean": 198.0,
                    "p50": 160.0,
                    "p10": 111.0,
                    "p90": 278.0,
                },
                "rush_yards": {
                    "mean": 15.8,
                    "p50": 15.8,
                    "p10": 5.5,
                    "p90": 33.4,
                },
            },
        }
    ]
    spine = {
        "NE|drake maye": {
            "pass_yards": 216.2,
            "rush_yards": 17.4,
            "receiving_yards": 0.0,
            "receptions": 0.0,
        }
    }
    hit = overlay_spine_means_on_players(players, spine)
    assert hit == 1
    assert players[0]["point_estimate"]["pass_yards"] == 216.2
    assert players[0]["point_estimate"]["rush_yards"] == 17.4
    assert players[0]["distributions"]["pass_yards"]["mean"] == 216.2
    # p50 remains research band; headline uses point_estimate / mean.
    assert players[0]["distributions"]["pass_yards"]["p50"] == 160.0
    assert players[0]["spine_version"] == PRODUCTION_VERSION


def test_overlay_matches_props_mean_within_rounding() -> None:
    props_mean = 216.2
    players = [
        {
            "player_name": "Drake Maye",
            "team": "NE",
            "position": "QB",
            "point_estimate": {"pass_yards": 160.0},
            "distributions": {"pass_yards": {"mean": 160.0, "p50": 160.0}},
        }
    ]
    overlay_spine_means_on_players(
        players, {"NE|drake maye": {"pass_yards": props_mean, "rush_yards": 17.4}}
    )
    boxes = float(players[0]["point_estimate"]["pass_yards"])
    assert abs(boxes - props_mean) < 0.05
