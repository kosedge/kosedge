"""t4770u offline 2026 efficiency recovery — contract 24600552, no DATABASE_URL."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.pop("DATABASE_URL", None)

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / "data" / "ops" / "nfl-efficiency-2026-w1-w8-t4770u"

REQUIRED_20 = (
    "offense_index_home",
    "offense_index_away",
    "defense_index_home",
    "defense_index_away",
    "home_off_epa_5g",
    "away_off_epa_5g",
    "home_def_epa_allowed_5g",
    "away_def_epa_allowed_5g",
    "home_pass_rate_5g",
    "away_pass_rate_5g",
    "home_success_offense_5g",
    "away_success_offense_5g",
    "home_success_defense_allowed_5g",
    "away_success_defense_allowed_5g",
    "matchup_diff_off_epa_5g",
    "matchup_diff_def_epa_allowed_5g",
    "matchup_diff_success_rate_5g",
    "matchup_diff_pressure_generated_5g",
    "matchup_diff_pressure_allowed_5g",
    "matchup_diff_red_zone_td_rate_5g",
)

W9_IDS = [
    "2026-W09-ARI@SEA",
    "2026-W09-BUF@MIN",
    "2026-W09-CIN@ATL",
    "2026-W09-CLE@NO",
    "2026-W09-DAL@IND",
    "2026-W09-DEN@CAR",
    "2026-W09-DET@MIA",
    "2026-W09-GB@NE",
    "2026-W09-HOU@LAC",
    "2026-W09-JAX@BAL",
    "2026-W09-LAR@WAS",
    "2026-W09-LV@SF",
    "2026-W09-NYG@PHI",
    "2026-W09-NYJ@KC",
    "2026-W09-TB@CHI",
]


def _load(name: str):
    return json.loads((ART / name).read_text(encoding="utf-8"))


def test_status_is_data_partial_through_w8_incomplete() -> None:
    status = _load("STATUS.json")
    assert status["status"] == "DATA_PARTIAL"
    assert status["through_w8_declared_complete"] is False
    assert status["through_w7_complete"] is True
    assert status["alex_contract_sha8"] == "24600552"
    assert status["contract_bind"] == "NOT_FINAL"
    assert status["imv_return"] == "d2587de7"
    assert status["week8_expected_count"] == 14
    assert status["week8_complete_count"] == 1
    missing = {row["game_id"] for row in status["week8_missing"]}
    assert "2026-W08-CHI@SEA" in missing
    assert "2026-W08-PHI@WAS" in missing
    assert "2026-W08-CAR@GB" not in missing
    assert len(missing) == 13
    assert status["e1_retry"]["scoring_admissible_now"] is False


def test_no_2025_prior_and_no_week9_rolling() -> None:
    current = _load("team_efficiency_current_through_w7.json")
    assert current["2025_prior_used"] is False
    assert current["n"] == 32
    for team, row in current["teams"].items():
        assert row["2025_prior_used"] is False
        assert int(row["as_of_week"]) == 7
        assert int(row["rolling_as_of_week"]) <= 7
        assert row["t5_ok"] is True
        assert row["offense_index"] is not None
        assert 0.82 <= float(row["offense_index"]) <= 1.18
        assert 0.82 <= float(row["defense_index"]) <= 1.20


def test_w09_consume_pack_has_20_required_fields() -> None:
    pack = _load("w09_consume_pack.json")
    assert pack["n_games"] == 15
    assert pack["week_scoring_admissible"] is False
    assert pack["as_of_week"] == 7
    ids = [g["game_id"] for g in pack["games"]]
    assert ids == W9_IDS
    for game in pack["games"]:
        assert game["row_status"] == "ACCEPT"
        assert game["t4_both_success_terms"] is True
        assert game["2025_prior_used"] is False
        assert int(game["rolling_as_of_week"]) <= 7
        for name in REQUIRED_20:
            assert game[name] is not None, name
            float(game[name])
        assert game["weather_available"] is None
        assert game["kav_as_of_week"] is None
        assert game["tendency_total_signal"] is None
        assert game["injury_nowcast_impact_home"] is None
        assert game["travel_available"] is None
        assert game["travel_miles_home"] is None
        assert game["travel_miles_away"] is None
        assert game["travel_timezone_delta_home"] is None
        assert game["travel_timezone_delta_away"] is None
        assert game["info_velocity_home"] is None
        assert game["info_velocity_away"] is None
        assert game["hours_since_change_home"] is None
        assert game["hours_since_change_away"] is None


def test_if_consume_without_database_url() -> None:
    assert not os.environ.get("DATABASE_URL")
    from src.services.nfl_simulator import (
        INDEPENDENT_FAIR_FORECAST_LABEL,
        NFL_INDEPENDENT_FAIR_PATH,
        NflGameInputs,
        independent_fair_mus,
        simulate_nfl_game_independent_fair,
    )

    pack = _load("w09_consume_pack.json")
    game = pack["games"][0]
    inputs = NflGameInputs(
        game_id=game["game_id"],
        home_team=game["home_team"],
        away_team=game["away_team"],
        offense_index_home=float(game["offense_index_home"]),
        offense_index_away=float(game["offense_index_away"]),
        defense_index_home=float(game["defense_index_home"]),
        defense_index_away=float(game["defense_index_away"]),
        rest_days_home=float(game["rest_days_home"]),
        rest_days_away=float(game["rest_days_away"]),
        matchup_season=2026,
        matchup_week=9,
        home_off_epa_5g=float(game["home_off_epa_5g"]),
        away_off_epa_5g=float(game["away_off_epa_5g"]),
        home_def_epa_allowed_5g=float(game["home_def_epa_allowed_5g"]),
        away_def_epa_allowed_5g=float(game["away_def_epa_allowed_5g"]),
        home_pass_rate_5g=float(game["home_pass_rate_5g"]),
        away_pass_rate_5g=float(game["away_pass_rate_5g"]),
        home_success_offense_5g=float(game["home_success_offense_5g"]),
        away_success_offense_5g=float(game["away_success_offense_5g"]),
        home_success_defense_allowed_5g=float(game["home_success_defense_allowed_5g"]),
        away_success_defense_allowed_5g=float(game["away_success_defense_allowed_5g"]),
        matchup_diff_off_epa_5g=float(game["matchup_diff_off_epa_5g"]),
        matchup_diff_def_epa_allowed_5g=float(game["matchup_diff_def_epa_allowed_5g"]),
        matchup_diff_success_rate_5g=float(game["matchup_diff_success_rate_5g"]),
        matchup_diff_pressure_generated_5g=float(
            game["matchup_diff_pressure_generated_5g"]
        ),
        matchup_diff_pressure_allowed_5g=float(game["matchup_diff_pressure_allowed_5g"]),
        matchup_diff_red_zone_td_rate_5g=float(game["matchup_diff_red_zone_td_rate_5g"]),
    )
    assert NFL_INDEPENDENT_FAIR_PATH is False
    out = simulate_nfl_game_independent_fair(
        inputs, simulations=200, seed=4770, market_spread_home=None, market_total=None
    )
    assert out["forecast_label"] == INDEPENDENT_FAIR_FORECAST_LABEL
    assert out["independent_fair"]["market_blend"] == 0
    margin_mu, total_mu = independent_fair_mus(out)
    assert total_mu == total_mu
    assert margin_mu == margin_mu


def test_sha256sums_cover_sealed_json() -> None:
    sums = (ART / "SHA256SUMS").read_text(encoding="utf-8").strip().splitlines()
    names = {line.split()[-1] for line in sums if line.strip()}
    assert "w09_consume_pack.json" in names
    assert "STATUS.json" in names
    assert "SOURCE_MANIFEST.json" in names
