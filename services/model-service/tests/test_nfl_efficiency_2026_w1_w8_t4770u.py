"""t4770u / t4776u offline 2026 efficiency recovery — v2 PASS_CONTRACT 1a53bbd3."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

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


def _sha256(name: str) -> str:
    digest = hashlib.sha256()
    digest.update((ART / name).read_bytes())
    return digest.hexdigest()


def test_status_is_data_partial_bound_to_v2_pass_contract() -> None:
    status = _load("STATUS.json")
    assert status["status"] == "DATA_PARTIAL"
    assert status["through_w8_declared_complete"] is False
    assert status["through_w7_complete"] is True
    assert status["alex_contract_sha8"] == "b41f4b43"
    assert status["alex_contract_version"] == "v2"
    assert status["contract_bind"] == "BOUND_TO_V2_PASS_CONTRACT_1a53bbd3"
    assert status["imv_pass_contract"] == "1a53bbd3"
    assert status["imv_d1"].startswith("CLOSED")
    assert status["week8_expected_count"] == 14
    assert status["week8_complete_count"] == 1
    missing = {row["game_id"] for row in status["week8_missing"]}
    assert "2026-W08-CHI@SEA" in missing
    assert "2026-W08-PHI@WAS" in missing
    assert "2026-W08-CAR@GB" not in missing
    assert len(missing) == 13
    assert status["e1_retry"]["scoring_admissible_now"] is False
    assert "t4776u" in status.get("addon_tickets", [])


def test_authority_files_match_operative_hashes() -> None:
    assert _sha256("ALEX_E1_EFFICIENCY_CONTRACT_t4770u_v2.md").startswith("b41f4b43")
    assert _sha256("IMV_GRADE_t4770u_E1_EFFICIENCY_CONTRACT_v2.txt").startswith("1a53bbd3")
    assert _sha256("ALEX_E1_EFFICIENCY_CONTRACT_t4770u_v1.md").startswith("24600552")


def test_no_2025_prior_and_no_week9_rolling() -> None:
    current = _load("team_efficiency_current_through_w7.json")
    assert current["2025_prior_used"] is False
    assert current["n"] == 32
    for _team, row in current["teams"].items():
        assert row["2025_prior_used"] is False
        assert int(row["as_of_week"]) == 7
        assert int(row["rolling_as_of_week"]) <= 7
        assert row["t5_ok"] is True
        assert row["offense_index"] is not None
        assert 0.82 <= float(row["offense_index"]) <= 1.18
        assert 0.82 <= float(row["defense_index"]) <= 1.20


def test_w09_consume_pack_has_20_required_fields_and_v2_catchall() -> None:
    pack = _load("w09_consume_pack.json")
    assert pack["n_games"] == 15
    assert pack["week_scoring_admissible"] is False
    assert pack["as_of_week"] == 7
    assert pack["contract_bind"] == "BOUND_TO_V2_PASS_CONTRACT_1a53bbd3"
    ids = [g["game_id"] for g in pack["games"]]
    assert ids == W9_IDS
    from src.services.nfl_simulator import NflGameInputs

    allowed = set(REQUIRED_20) | {
        "game_id",
        "home_team",
        "away_team",
        "matchup_season",
        "matchup_week",
        "rest_days_home",
        "rest_days_away",
    }
    for game in pack["games"]:
        assert game["row_status"] == "ACCEPT"
        assert game["t4_both_success_terms"] is True
        assert game["2025_prior_used"] is False
        assert int(game["rolling_as_of_week"]) <= 7
        for name in REQUIRED_20:
            assert game[name] is not None, name
            float(game[name])
        for name in NflGameInputs.__dataclass_fields__:
            if name in allowed:
                continue
            assert game.get(name) is None, name


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


def test_required_20_consumed_by_if_path_call_graph_and_input_hash() -> None:
    """t4776u: present-in-dataset is not enough — IF path must consume each field."""
    consumed = _load("if_required_20_consumed.json")
    proof = _load("if_consume_proof.json")
    assert consumed["contract_bind"] == "BOUND_TO_V2_PASS_CONTRACT_1a53bbd3"
    assert consumed["imv_pass_contract"] == "1a53bbd3"
    assert consumed["n_required"] == 20
    assert consumed["n_consumed_by_if_path"] == 20
    assert consumed["all_20_consumed"] is True
    assert consumed["scoring_admissible"] is False
    assert consumed["entrypoint"] == "simulate_nfl_game_independent_fair"
    chain = consumed["call_graph"]
    assert chain["independent_fair_kwarg_true"] is True
    assert chain["simulate_nfl_game_calls"]["_build_matchup_adjustments"]
    assert chain["simulate_nfl_game_calls"]["_build_totals_adjustments"]
    assert chain["simulate_nfl_game_calls"]["compute_nfl_projection_decomposition"]
    names = []
    for row in consumed["fields"]:
        names.append(row["field"])
        assert row["in_call_graph"] is True
        assert row["present_in_dataset"] is True
        assert row["passed_into_NflGameInputs"] is True
        assert row["input_hash_changed"] is True
        assert row["output_hash_changed"] is True
        assert row["consumed_by_if_path"] is True
        assert row["readers"]
        moved = (
            abs(float(row["delta_predicted_margin"])) > 0.0
            or abs(float(row["delta_predicted_total"])) > 0.0
            or abs(float(row["delta_margin_mu"])) > 0.0
            or abs(float(row["delta_total_mu"])) > 0.0
        )
        assert moved, row["field"]
    assert names == list(REQUIRED_20)
    assert proof["required_20_consumed_by_if_path"] is True
    assert proof["n_consumed"] == 15
    assert proof["scoring_admissible"] is False


def test_data_partial_accept_standby_does_not_claim_ready() -> None:
    accept = _load("ACCEPT.json")
    status = _load("STATUS.json")
    assert accept["verdict"] == "DATA_PARTIAL_ACCEPT"
    assert accept["imv_data_partial_accept"] == "c674da77"
    assert accept["accepted_tip_sha8"] == "ba9e8426"
    assert accept["panel"] == "through-W7 only"
    assert accept["status_remains"] == "DATA_PARTIAL"
    assert "DATA_READY" in accept["do_not_claim"]
    assert status["status"] == "DATA_PARTIAL"
    assert status["through_w8_declared_complete"] is False
    assert _sha256("STATUS.json") == (
        "81d7dd9f4b028ea65386cfa277f714ce4ce4ffdf103481efa4aa9093d6cce445"
    )
    assert _sha256("IMV_GRADE_t4770u_DATA_PARTIAL.txt").startswith("c674da77")


def test_rest_days_spotcheck_records_heuristic() -> None:
    spot = _load("rest_days_spotcheck.json")
    assert spot["function"] == "nfl_data.rest_days_from_schedule"
    assert spot["n"] == 15
    assert spot["scoring_admissible"] is False
    short = [row for row in spot["rows"] if row["short_week"]]
    assert short
    assert all(row["game_id"].startswith("2026-W09-") for row in spot["rows"])


def test_sha256sums_cover_sealed_json_and_authority() -> None:
    sums = (ART / "SHA256SUMS").read_text(encoding="utf-8").strip().splitlines()
    names = {line.split()[-1] for line in sums if line.strip()}
    required = {
        "w09_consume_pack.json",
        "STATUS.json",
        "SOURCE_MANIFEST.json",
        "if_consume_proof.json",
        "if_required_20_consumed.json",
        "ALEX_E1_EFFICIENCY_CONTRACT_t4770u_v2.md",
        "IMV_GRADE_t4770u_E1_EFFICIENCY_CONTRACT_v2.txt",
        "COS_ORDER_CURSOR_t4770u_BIND_PASS_CONTRACT.txt",
        "ACCEPT.json",
        "STANDBY.md",
        "IMV_GRADE_t4770u_DATA_PARTIAL.txt",
        "COS_ORDER_CURSOR_t4770u_STANDBY_DATA_READY.txt",
        "rest_days_spotcheck.json",
        "T4842U_READY_STANDBY_RECEIPT.json",
        "T4845U_WEEKEND_LAUNCH_ASSESS_RECEIPT.json",
    }
    assert required <= names
    for line in sums:
        digest, name = line.split()
        assert _sha256(name) == digest
