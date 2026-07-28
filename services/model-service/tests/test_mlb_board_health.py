from src.services.mlb_board_health import evaluate_mlb_board_health
from src.services.mlb_prop_edge_policy import PLAY_STAKE_ELIGIBLE, evaluate_mlb_prop_edge


def test_props_play_stake_always_false() -> None:
    assert PLAY_STAKE_ELIGIBLE is False
    tag = evaluate_mlb_prop_edge(model_prob=0.62, market_implied_prob=0.50, market_key="hits")
    assert tag["tag"] == "PLAY"
    assert tag["stake_eligible"] is False
    assert tag["play_stake_eligible_policy"] is False


def test_board_health_requires_spread_coverage_and_research_props() -> None:
    rows = [
        {
            "fg_home_win_prob": 0.54,
            "fair_fg_total": 8.5,
            "fair_fg_spread_home": -1.5,
            "fg_home_cover_prob_run_line": 0.48,
        }
        for _ in range(10)
    ]
    health = evaluate_mlb_board_health(
        projection_rows=rows,
        outcome_coverage_rate=0.8,
        odds_coverage_rate=0.7,
        dk_snapshot_rate=0.6,
        brier_ml=0.24,
        mae_total_runs=2.8,
        holdout_sample_size=130,
        props_play_stake_eligible=False,
    )
    assert health["spread_coverage_ok"] is True
    assert health["holdout_sample_ok"] is True
    assert health["props_research_only_ok"] is True
    assert health["publish_ready_ops"] is True


def test_board_health_blocks_when_props_stake_enabled() -> None:
    health = evaluate_mlb_board_health(
        projection_rows=[],
        props_play_stake_eligible=True,
    )
    assert health["props_research_only_ok"] is False
    assert health["publish_ready_ops"] is False
