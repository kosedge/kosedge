from __future__ import annotations

from src.services.nfl_portfolio_optimizer import optimize_nfl_portfolio


def test_optimizer_enforces_player_exposure_cap() -> None:
    candidates = [
        {
            "game_id": "g1",
            "home_team": "A",
            "away_team": "B",
            "time_window": "prime",
            "quality_score": 90,
            "confidence_score": 0.8,
            "ml_edge_prob": 0.035,
            "player_id": "player-1",
            "player_name": "Player One",
            "position": "WR",
            "market": "receiving_yards",
        },
        {
            "game_id": "g1",
            "home_team": "A",
            "away_team": "B",
            "time_window": "prime",
            "quality_score": 88,
            "confidence_score": 0.78,
            "ml_edge_prob": 0.030,
            "player_id": "player-1",
            "player_name": "Player One",
            "position": "WR",
            "market": "receptions",
        },
    ]
    result = optimize_nfl_portfolio(
        candidates=candidates,
        bankroll=1000.0,
        risk_profile="balanced",
        max_total_exposure=0.15,
        max_per_game_exposure=0.12,
        max_per_team_exposure=0.12,
        max_per_window_exposure=0.15,
        max_per_player_exposure=0.02,
        max_bet_fraction=0.05,
        correlation_penalty=0.40,
        same_game_player_penalty=0.35,
        qb_wr_correlation_penalty=0.45,
    )
    assert result["diagnostics"]["exposure_utilization"]["player_exposure"]["player-1"] <= 0.02
    assert result["diagnostics"]["excluded_reasons"]["player_exposure_cap"] >= 0


def test_optimizer_records_excluded_reasons() -> None:
    candidates = [
        {
            "game_id": "g1",
            "home_team": "A",
            "away_team": "B",
            "time_window": "early",
            "quality_score": 20,
            "confidence_score": 0.2,
            "ml_edge_prob": 0.002,
        }
    ]
    result = optimize_nfl_portfolio(
        candidates=candidates,
        bankroll=500.0,
        risk_profile="balanced",
        max_total_exposure=0.10,
        max_per_game_exposure=0.05,
        max_per_team_exposure=0.05,
        max_per_window_exposure=0.08,
        max_bet_fraction=0.03,
        correlation_penalty=0.3,
    )
    assert result["recommendations"] == []
    assert result["diagnostics"]["excluded_reasons"]["low_quality"] == 1
    assert len(result["diagnostics"]["excluded_examples"]) == 1
