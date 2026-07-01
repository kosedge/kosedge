import os

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.nfl_matchup_features import matchup_pack_to_sim_input_kwargs


def test_matchup_pack_to_sim_input_kwargs_maps_expected_fields() -> None:
    matchup_pack = {
        "season": 2025,
        "week": 9,
        "game_id": "2025_09_NE_BUF",
        "home_team": "BUF",
        "away_team": "NE",
        "home_off_epa_5g": 0.13,
        "away_off_epa_5g": -0.01,
        "home_pass_rate_5g": 0.62,
        "away_pass_rate_5g": 0.55,
        "home_success_offense_5g": 0.47,
        "away_success_offense_5g": 0.40,
        "home_success_defense_allowed_5g": 0.41,
        "away_success_defense_allowed_5g": 0.45,
        "diff_off_epa_5g": 0.14,
        "diff_def_epa_allowed_5g": 0.08,
        "diff_pressure_generated_5g": 0.03,
        "diff_pressure_allowed_5g": 0.02,
        "diff_red_zone_td_rate_5g": 0.06,
    }

    mapped = matchup_pack_to_sim_input_kwargs(matchup_pack)
    assert mapped["matchup_season"] == 2025
    assert mapped["matchup_week"] == 9
    assert mapped["feature_pack_version"] == "nfl-v1-matchup-pack"
    assert mapped["matchup_diff_off_epa_5g"] == 0.14
    assert mapped["matchup_diff_pressure_generated_5g"] == 0.03
    assert mapped["matchup_diff_success_rate_5g"] == pytest.approx(0.055)


def test_matchup_pack_to_sim_input_kwargs_handles_missing_values() -> None:
    mapped = matchup_pack_to_sim_input_kwargs(
        {
            "season": 2025,
            "week": 9,
            "game_id": "g1",
            "home_team": "A",
            "away_team": "B",
            "diff_off_epa_5g": None,
        }
    )
    assert mapped["matchup_diff_off_epa_5g"] is None
    assert mapped["matchup_diff_success_rate_5g"] is None
