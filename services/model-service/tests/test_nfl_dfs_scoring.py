from __future__ import annotations

from src.services.nfl_dfs_scoring import (
    DK_CLASSIC,
    FD_CLASSIC,
    score_counting_line,
    score_production_for_site,
)
from src.services.nfl_player_production import production_from_baseline_row


def _wr_prod():
    return production_from_baseline_row(
        {
            "pass_yards_mean": 0,
            "rush_yards_mean": 8,
            "receiving_yards_mean": 92,
            "receptions_mean": 7.0,
            "pass_tds_mean": 0,
            "rush_tds_mean": 0.1,
            "rec_tds_mean": 0.6,
            "pass_yards_std": 4,
            "rush_yards_std": 6,
            "receiving_yards_std": 28,
            "receptions_std": 2.1,
        }
    )


def test_dk_is_full_ppr_fd_is_half() -> None:
    wr = dict(
        pass_yards=0,
        pass_tds=0,
        rush_yards=10,
        rush_tds=0,
        receiving_yards=80,
        receptions=8,
        rec_tds=1,
        apply_threshold_bonuses=False,
    )
    dk = score_counting_line(scoring_system=DK_CLASSIC, **wr)
    fd = score_counting_line(scoring_system=FD_CLASSIC, **wr)
    assert abs(dk - fd - 4.0) < 1e-6  # 8 receptions * 0.5


def test_dk_threshold_bonus_not_applied_to_fd() -> None:
    line = dict(
        pass_yards=0,
        pass_tds=0,
        rush_yards=0,
        rush_tds=0,
        receiving_yards=110,
        receptions=6,
        rec_tds=0,
    )
    dk = score_counting_line(scoring_system=DK_CLASSIC, **line, apply_threshold_bonuses=True)
    fd = score_counting_line(scoring_system=FD_CLASSIC, **line, apply_threshold_bonuses=True)
    assert dk - fd > 3.0  # reception delta + DK 100-yard bonus


def test_no_distribution_leaves_floor_ceiling_unavailable() -> None:
    scored = score_production_for_site(_wr_prod(), site="DK", baseline_row={})
    assert scored.projection > 0
    assert scored.floor is None
    assert scored.ceiling is None
    assert scored.distribution_available is False
    assert scored.unavailable_reason == "distribution_unavailable"
    # Forbidden heuristic.
    assert scored.ceiling != scored.projection * 1.35


def test_distribution_outcomes_are_site_scored() -> None:
    row = {
        "pass_yards_std": 40,
        "rush_yards_std": 6,
        "receiving_yards_std": 28,
        "receptions_std": 2,
        "floor_outcome": {
            "pass_yards": 0,
            "rush_yards": 2,
            "receiving_yards": 50,
            "receptions": 4,
            "touchdowns": 0.2,
        },
        "median_outcome": {
            "pass_yards": 0,
            "rush_yards": 8,
            "receiving_yards": 92,
            "receptions": 7,
            "touchdowns": 0.7,
        },
        "ceiling_outcome": {
            "pass_yards": 0,
            "rush_yards": 20,
            "receiving_yards": 140,
            "receptions": 10,
            "touchdowns": 1.4,
        },
    }
    scored = score_production_for_site(_wr_prod(), site="DK", baseline_row=row)
    assert scored.distribution_available is True
    assert scored.floor is not None and scored.ceiling is not None
    assert scored.floor < scored.projection < scored.ceiling
    assert scored.ceiling != scored.projection * 1.35
