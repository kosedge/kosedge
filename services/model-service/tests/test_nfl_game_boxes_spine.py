"""Game Boxes spine overlay — Props mean and Boxes headline must agree."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.services.nfl_game_boxes_spine import (
    SpineOverlayMissError,
    _index_keys_for_player,
    apply_spine_overlay_to_game_boxes_payload,
    load_spine_means_for_game,
    name_from_player_key,
    overlay_spine_means_on_players,
)
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
    # Baselines ship as nflverse abbrev — must join to full engine name.
    means = {
        "pass_yards": 216.2,
        "rush_yards": 17.4,
        "receiving_yards": 0.0,
        "receptions": 0.0,
    }
    spine = {
        key: means for key in _index_keys_for_player(team="NE", player_name="D.Maye")
    }

    hit = overlay_spine_means_on_players(players, spine)
    assert hit == 1, "overlay_count must be >0 for Maye NE@SEA"
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
    spine = {
        k: {"pass_yards": props_mean, "rush_yards": 17.4}
        for k in _index_keys_for_player(team="NE", player_name="D.Maye")
    }
    hit = overlay_spine_means_on_players(players, spine)
    assert hit == 1
    boxes = float(players[0]["point_estimate"]["pass_yards"])
    assert abs(boxes - props_mean) < 0.05


def test_overlay_count_zero_raises_and_does_not_stamp_spine() -> None:
    payload = {
        "season": 2026,
        "week": 1,
        "home_team": "SEA",
        "away_team": "NE",
        "notes": {},
        "players": [
            {
                "player_name": "Drake Maye",
                "team": "NE",
                "position": "QB",
                "point_estimate": {"pass_yards": 160.0},
                "distributions": {
                    "pass_yards": {"mean": 160.0, "p50": 160.0, "p10": 111.0, "p90": 208.0}
                },
            }
        ],
    }

    class _EmptySession:
        def execute(self, *_a, **_k):
            return SimpleNamespace(fetchall=lambda: [])

    with pytest.raises(SpineOverlayMissError) as ei:
        apply_spine_overlay_to_game_boxes_payload(payload, _EmptySession())
    assert ei.value.meta.get("overlay_count") == 0
    assert "spine_version" not in payload
    assert payload["notes"].get("yards_headline") == "overlay_miss"
    assert payload["notes"].get("spine_version") is None


def test_load_spine_uses_text_array_cast() -> None:
    """Regression: bare ANY(:teams) returns 0 rows under psycopg — must CAST."""
    captured: dict = {}

    class _Session:
        def execute(self, stmt, params):
            captured["sql"] = str(stmt)
            captured["params"] = params
            return SimpleNamespace(fetchall=lambda: [])

    load_spine_means_for_game(_Session(), season=2026, week=1, teams=["NE", "SEA"])
    assert "CAST(:teams AS text[])" in captured["sql"]
    assert captured["params"]["teams"] == ["NE", "SEA"]


def test_overlay_hits_player_key_ne_qb1_drakemaye() -> None:
    """Alex live dump: box player_key is NE-QB1-DrakeMaye — overlay must hit it."""
    assert name_from_player_key("NE-QB1-DrakeMaye") == "Drake Maye"
    players = [
        {
            "player_key": "NE-QB1-DrakeMaye",
            "player_name": "Drake Maye",
            "team": "NE",
            "position": "QB",
            "point_estimate": {"pass_yards": 160.048},
            "distributions": {
                "pass_yards": {"mean": 160.048, "p50": 159.67, "p10": 110.58, "p90": 208.16}
            },
        }
    ]
    # Index only via baseline abbrev — join through player_key / identity keys.
    spine = {
        k: {"pass_yards": 216.164, "rush_yards": 17.4, "receiving_yards": 0.0, "receptions": 0.0}
        for k in _index_keys_for_player(team="NE", player_name="D.Maye")
    }
    # Also ensure pk index from baseline side.
    for k in _index_keys_for_player(
        team="NE", player_name="D.Maye", player_key="NE-QB1-DrakeMaye"
    ):
        spine.setdefault(
            k,
            {"pass_yards": 216.164, "rush_yards": 17.4, "receiving_yards": 0.0, "receptions": 0.0},
        )
    hit = overlay_spine_means_on_players(players, spine)
    assert hit == 1, "overlay_count must be >0 for NE-QB1-DrakeMaye"
    assert abs(float(players[0]["point_estimate"]["pass_yards"]) - 216.164) < 0.05


def test_props_edges_fallback_does_not_zero_missing_markets() -> None:
    """Bugbot: sparse edges must not seed rush/rec at 0.0 and wipe live box stats."""
    edge_pass = SimpleNamespace(
        player_name="D.Maye",
        player_uid=None,
        team="NE",
        market_key="pass_yds",
        model_mean=216.2,
    )
    payload = {
        "season": 2026,
        "week": 1,
        "home_team": "SEA",
        "away_team": "NE",
        "notes": {},
        "players": [
            {
                "player_key": "NE-QB1-DrakeMaye",
                "player_name": "Drake Maye",
                "team": "NE",
                "position": "QB",
                "point_estimate": {
                    "pass_yards": 160.0,
                    "rush_yards": 15.8,
                    "rec_yards": 0.0,
                    "receptions": 0.0,
                },
                "distributions": {
                    "pass_yards": {"mean": 160.0, "p50": 160.0},
                    "rush_yards": {"mean": 15.8, "p50": 15.8},
                },
            }
        ],
    }

    class _Session:
        def __init__(self) -> None:
            self.calls = 0

        def execute(self, *_a, **_k):
            self.calls += 1
            # First call: baselines empty → fallback to props edges.
            if self.calls == 1:
                return SimpleNamespace(fetchall=lambda: [])
            return SimpleNamespace(fetchall=lambda: [edge_pass])

        def rollback(self) -> None:
            return None

    meta = apply_spine_overlay_to_game_boxes_payload(payload, _Session())
    assert meta["source"] == "nfl_player_prop_model_edges"
    assert meta["overlay_count"] == 1
    pe = payload["players"][0]["point_estimate"]
    assert pe["pass_yards"] == 216.2
    # Missing rush_yds / rec markets must leave live box values alone.
    assert pe["rush_yards"] == 15.8
    assert pe["receptions"] == 0.0
    assert payload["spine_version"] == PRODUCTION_VERSION


def test_overlay_skips_absent_spine_fields() -> None:
    players = [
        {
            "player_name": "Drake Maye",
            "team": "NE",
            "position": "QB",
            "point_estimate": {"pass_yards": 160.0, "rush_yards": 15.8},
            "distributions": {
                "pass_yards": {"mean": 160.0, "p50": 160.0},
                "rush_yards": {"mean": 15.8, "p50": 15.8},
            },
        }
    ]
    spine = {
        k: {"pass_yards": 216.2}  # rush intentionally absent — not 0.0
        for k in _index_keys_for_player(team="NE", player_name="Drake Maye")
    }
    hit = overlay_spine_means_on_players(players, spine)
    assert hit == 1
    assert players[0]["point_estimate"]["pass_yards"] == 216.2
    assert players[0]["point_estimate"]["rush_yards"] == 15.8


def test_maye_ne_sea_overlay_count_must_not_be_zero() -> None:
    """Live FAIL lock: Maye NE@SEA must overlay; overlay_count==0 is a hard fail."""
    maye_row = SimpleNamespace(
        player_name="D.Maye",
        player_uid=None,
        team="NE",
        position="QB",
        pass_yards_mean=216.164,
        rush_yards_mean=17.4,
        receiving_yards_mean=0.0,
        receptions_mean=0.0,
        pass_tds_mean=1.5,
        rush_tds_mean=0.2,
        rec_tds_mean=0.0,
        total_tds_mean=1.7,
        pass_yards_std=56.0,
        rush_yards_std=8.0,
        receiving_yards_std=1.0,
        receptions_std=0.5,
    )
    payload = {
        "season": 2026,
        "week": 1,
        "home_team": "SEA",
        "away_team": "NE",
        "notes": {},
        "players": [
            {
                "player_key": "NE-QB1-DrakeMaye",
                "player_name": "Drake Maye",
                "team": "NE",
                "position": "QB",
                "point_estimate": {"pass_yards": 160.048},
                "distributions": {
                    "pass_yards": {
                        "mean": 160.048,
                        "p50": 159.67,
                        "p10": 110.58,
                        "p90": 208.16,
                    }
                },
            }
        ],
    }

    class _Session:
        def execute(self, *_a, **_k):
            return SimpleNamespace(fetchall=lambda: [maye_row])

    meta = apply_spine_overlay_to_game_boxes_payload(payload, _Session())
    assert meta["overlay_count"] == 1
    assert meta["rows"] == 1
    assert abs(float(payload["players"][0]["point_estimate"]["pass_yards"]) - 216.164) < 0.05
    assert payload["spine_version"] == PRODUCTION_VERSION
    assert payload["notes"]["yards_headline"] == "spine_mean"
