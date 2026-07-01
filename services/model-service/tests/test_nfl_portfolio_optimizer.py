from __future__ import annotations

from src.services.nfl_portfolio_optimizer import optimize_nfl_portfolio


def test_optimizer_enforces_exposure_caps() -> None:
    candidates = [
        {
            "game_id": "g1",
            "home_team": "A",
            "away_team": "B",
            "time_window": "prime",
            "quality_score": 78.0,
            "confidence_score": 0.70,
            "ml_edge_prob": 0.045,
        },
        {
            "game_id": "g2",
            "home_team": "A",
            "away_team": "C",
            "time_window": "prime",
            "quality_score": 74.0,
            "confidence_score": 0.66,
            "ml_edge_prob": 0.040,
        },
    ]
    out = optimize_nfl_portfolio(
        candidates=candidates,
        bankroll=1000.0,
        risk_profile="balanced",
        max_total_exposure=0.05,
        max_per_game_exposure=0.04,
        max_per_team_exposure=0.015,
        max_per_window_exposure=0.05,
        max_bet_fraction=0.03,
        correlation_penalty=0.35,
    )
    assert out["diagnostics"]["selected_count"] == 1
    assert out["diagnostics"]["excluded_reasons"]["team_exposure_cap"] >= 1
    assert out["diagnostics"]["exposure_utilization"]["total"] <= 0.05


def test_optimizer_applies_correlation_penalty_same_game() -> None:
    candidates = [
        {
            "game_id": "g1",
            "home_team": "KC",
            "away_team": "BUF",
            "time_window": "prime",
            "quality_score": 80.0,
            "confidence_score": 0.75,
            "ml_edge_prob": 0.05,
        },
        {
            "game_id": "g1",
            "home_team": "KC",
            "away_team": "BUF",
            "time_window": "prime",
            "quality_score": 76.0,
            "confidence_score": 0.72,
            "ml_edge_prob": -0.04,
        },
    ]
    out = optimize_nfl_portfolio(
        candidates=candidates,
        bankroll=1000.0,
        risk_profile="aggressive",
        max_total_exposure=0.20,
        max_per_game_exposure=0.20,
        max_per_team_exposure=0.20,
        max_per_window_exposure=0.20,
        max_bet_fraction=0.10,
        correlation_penalty=0.50,
    )
    assert out["diagnostics"]["selected_count"] == 2
    first, second = out["recommendations"][0], out["recommendations"][1]
    assert second["recommended_stake_fraction"] < first["recommended_stake_fraction"]
