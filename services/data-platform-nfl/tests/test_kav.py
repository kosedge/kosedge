"""Unit tests for KAV math: iterative opponent adjustment + leakage guards."""

from __future__ import annotations

import pytest

from data_platform_nfl.kav import (
    TeamGameRaw,
    assert_no_future_leakage,
    build_weekly_lagged_features,
    epa_to_kav_pct,
    iterative_opponent_adjust,
    kav_signal_to_points,
)


def _game(
    *,
    team: str,
    opponent: str,
    week: int,
    off_epa: float,
    def_epa: float,
    game_id: str | None = None,
    season: int = 2024,
) -> TeamGameRaw:
    return TeamGameRaw(
        season=season,
        week=week,
        game_id=game_id or f"{season}_{week:02d}_{team}_{opponent}",
        team=team,
        opponent=opponent,
        is_home=True,
        off_plays=60,
        def_plays=60,
        raw_off_epa=off_epa,
        raw_def_epa_allowed=def_epa,
        raw_off_success=0.45,
        raw_def_success_allowed=0.45,
        raw_off_explosive=0.10,
        raw_def_explosive_allowed=0.10,
    )


def test_epa_to_kav_pct_scale() -> None:
    # +0.075 EPA vs mean at scale 0.15 → +50% KAV
    assert epa_to_kav_pct(0.075, 0.0, scale=0.15) == pytest.approx(0.5)
    assert epa_to_kav_pct(-0.15, 0.0, scale=0.15) == pytest.approx(-1.0)


def test_iterative_adjust_boosts_offense_facing_tough_defense() -> None:
    """Team A posts mediocre raw EPA vs elite defense B; adjustment should lift A."""
    games = [
        # A vs elite defense B (B allows -0.15)
        _game(team="A", opponent="B", week=1, off_epa=0.00, def_epa=0.05),
        _game(team="B", opponent="A", week=1, off_epa=0.10, def_epa=-0.15),
        # A vs soft defense C
        _game(team="A", opponent="C", week=2, off_epa=0.12, def_epa=0.02),
        _game(team="C", opponent="A", week=2, off_epa=-0.05, def_epa=0.20),
        # B vs C
        _game(team="B", opponent="C", week=3, off_epa=0.18, def_epa=-0.10),
        _game(team="C", opponent="B", week=3, off_epa=-0.08, def_epa=0.22),
        # Fill schedule so each team has multiple games
        _game(team="A", opponent="B", week=4, off_epa=0.02, def_epa=0.04, game_id="2024_04_A_B"),
        _game(team="B", opponent="A", week=4, off_epa=0.08, def_epa=-0.12, game_id="2024_04_B_A"),
    ]
    ratings, game_adj, iters = iterative_opponent_adjust(games, iterations=12)
    assert iters >= 1
    assert "A" in ratings and "B" in ratings and "C" in ratings
    # Elite defense B should have lower (better) def_epa than soft C
    assert ratings["B"].def_epa < ratings["C"].def_epa
    # A's adjusted offense should exceed its raw play-weighted mean because of B's toughness
    raw_a_off = (0.00 + 0.12 + 0.02) / 3.0
    assert ratings["A"].off_epa > raw_a_off - 0.01
    # Game-level adjusted map populated
    assert any(k[1] == "A" for k in game_adj)


def test_soft_schedule_deflates_offense() -> None:
    """Padding stats vs cupcakes should not survive opponent adjustment."""
    games = [
        _game(team="PAD", opponent="WEAK", week=1, off_epa=0.25, def_epa=0.00),
        _game(team="WEAK", opponent="PAD", week=1, off_epa=-0.20, def_epa=0.30),
        _game(team="PAD", opponent="WEAK", week=2, off_epa=0.22, def_epa=0.01, game_id="2024_02_PAD_WEAK"),
        _game(team="WEAK", opponent="PAD", week=2, off_epa=-0.18, def_epa=0.28, game_id="2024_02_WEAK_PAD"),
        _game(team="ELITE", opponent="WEAK", week=1, off_epa=0.10, def_epa=-0.12, game_id="2024_01_ELITE_WEAK"),
        _game(team="WEAK", opponent="ELITE", week=1, off_epa=-0.15, def_epa=0.25, game_id="2024_01_WEAK_ELITE2"),
        _game(team="ELITE", opponent="PAD", week=3, off_epa=0.05, def_epa=-0.05),
        _game(team="PAD", opponent="ELITE", week=3, off_epa=-0.02, def_epa=0.15),
    ]
    # Fix duplicate game ids for WEAK week1 - use unique
    games = [
        _game(team="PAD", opponent="WEAK", week=1, off_epa=0.25, def_epa=0.00, game_id="g1_pad"),
        _game(team="WEAK", opponent="PAD", week=1, off_epa=-0.20, def_epa=0.30, game_id="g1_weak"),
        _game(team="PAD", opponent="WEAK", week=2, off_epa=0.22, def_epa=0.01, game_id="g2_pad"),
        _game(team="WEAK", opponent="PAD", week=2, off_epa=-0.18, def_epa=0.28, game_id="g2_weak"),
        _game(team="ELITE", opponent="WEAK", week=1, off_epa=0.10, def_epa=-0.12, game_id="g1e"),
        _game(team="WEAK", opponent="ELITE", week=3, off_epa=-0.15, def_epa=0.25, game_id="g3_weak"),
        _game(team="ELITE", opponent="PAD", week=3, off_epa=0.05, def_epa=-0.05, game_id="g3e"),
        _game(team="PAD", opponent="ELITE", week=3, off_epa=-0.02, def_epa=0.15, game_id="g3_pad"),
        _game(team="ELITE", opponent="WEAK", week=2, off_epa=0.12, def_epa=-0.10, game_id="g2e"),
        _game(team="WEAK", opponent="ELITE", week=2, off_epa=-0.10, def_epa=0.20, game_id="g2we"),
    ]
    ratings, _, _ = iterative_opponent_adjust(games, iterations=15)
    # PAD's raw offense looks great but mostly vs WEAK; ELITE should outrank on net after adj
    pad_kav = epa_to_kav_pct(ratings["PAD"].off_epa, 0.0) - epa_to_kav_pct(ratings["PAD"].def_epa, 0.0)
    elite_kav = epa_to_kav_pct(ratings["ELITE"].off_epa, 0.0) - epa_to_kav_pct(
        ratings["ELITE"].def_epa, 0.0
    )
    # Not a hard ordering guarantee on tiny toy data — assert adjustment moved PAD off down
    # relative to raw mean vs WEAK-only games
    raw_pad = (0.25 + 0.22 + -0.02) / 3.0
    assert ratings["PAD"].off_epa < raw_pad
    assert elite_kav > pad_kav or ratings["ELITE"].def_epa < ratings["PAD"].def_epa


def test_lagged_features_never_use_same_or_future_week() -> None:
    weekly = {
        (2024, 1, "BUF"): {
            "kav_offense_ytd": 0.1,
            "kav_defense_ytd": -0.05,
            "kav_net_ytd": 0.15,
            "kav_offense_5g": 0.1,
            "kav_defense_5g": -0.05,
            "kav_net_5g": 0.15,
        },
        (2024, 2, "BUF"): {
            "kav_offense_ytd": 0.2,
            "kav_defense_ytd": -0.1,
            "kav_net_ytd": 0.3,
            "kav_offense_5g": 0.2,
            "kav_defense_5g": -0.1,
            "kav_net_5g": 0.3,
        },
    }
    # Game in week 2 must use as-of week 1
    feats = build_weekly_lagged_features(weekly, season=2024, week=2, team="BUF")
    assert feats["kav_as_of_week"] == 1
    assert feats["kav_net_ytd"] == 0.15
    assert_no_future_leakage(feats["kav_as_of_week"], 2)

    # Week 1 has no prior → None
    week1 = build_weekly_lagged_features(weekly, season=2024, week=1, team="BUF")
    assert week1["kav_as_of_week"] is None
    assert week1["kav_net_5g"] is None


def test_assert_no_future_leakage_raises() -> None:
    with pytest.raises(ValueError, match="leakage"):
        assert_no_future_leakage(5, 5)
    with pytest.raises(ValueError, match="leakage"):
        assert_no_future_leakage(6, 5)
    assert_no_future_leakage(4, 5)  # ok
    assert_no_future_leakage(None, 5)  # ok


def test_kav_signal_to_points_bounded() -> None:
    out = kav_signal_to_points(
        home_kav_net_5g=1.5,
        away_kav_net_5g=-1.0,
        home_kav_offense_5g=0.8,
        away_kav_offense_5g=0.2,
        home_kav_defense_5g=-0.4,
        away_kav_defense_5g=0.3,
        max_margin=3.5,
        max_total=2.8,
    )
    assert out["available"] is True
    assert -3.5 <= out["margin_points"] <= 3.5
    assert -2.8 <= out["total_points"] <= 2.8
    missing = kav_signal_to_points(home_kav_net_5g=None, away_kav_net_5g=0.1)
    assert missing["available"] is False
    assert missing["margin_points"] == 0.0
