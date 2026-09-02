"""QB anytime TD must not include passing scores."""

from __future__ import annotations

from src.services.nfl_prop_edge_policy import anytime_td_prob_from_td_mean
from src.services.nfl_player_production import production_from_baseline_row


def test_qb_anytime_td_excludes_pass_tds() -> None:
    row = {
        "pass_yards_mean": 250.0,
        "rush_yards_mean": 20.0,
        "receiving_yards_mean": 0.0,
        "receptions_mean": 0.0,
        "pass_tds_mean": 1.8,
        "rush_tds_mean": 0.15,
        "rec_tds_mean": 0.0,
        "total_tds_mean": 1.95,
        "pass_yards_std": 40.0,
        "rush_yards_std": 8.0,
        "receiving_yards_std": 1.0,
        "receptions_std": 0.5,
    }
    prod = production_from_baseline_row(row)
    # Wrong path (old bug): total_tds → ~0.86
    inflated = anytime_td_prob_from_td_mean(prod.total_tds)
    # Correct path: rush only for QB
    fixed = anytime_td_prob_from_td_mean(prod.rush_tds)
    assert inflated > 0.7
    assert fixed < 0.25
    assert fixed < inflated


def test_skill_anytime_td_uses_rush_plus_rec() -> None:
    row = {
        "pass_yards_mean": 0.0,
        "rush_yards_mean": 60.0,
        "receiving_yards_mean": 25.0,
        "receptions_mean": 3.0,
        "pass_tds_mean": 0.0,
        "rush_tds_mean": 0.4,
        "rec_tds_mean": 0.2,
        "total_tds_mean": 0.6,
        "pass_yards_std": 1.0,
        "rush_yards_std": 15.0,
        "receiving_yards_std": 10.0,
        "receptions_std": 1.5,
    }
    prod = production_from_baseline_row(row)
    assert abs(
        anytime_td_prob_from_td_mean(prod.rush_tds + prod.rec_tds)
        - anytime_td_prob_from_td_mean(prod.total_tds)
    ) < 1e-9
