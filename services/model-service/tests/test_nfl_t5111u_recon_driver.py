"""t5111u reconstruction driver — helper pin, identity overlay, freeze, parity."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.services.nfl_t5107u.recon_contract import CONTRACT_27, compare_cell_maps
from src.services.nfl_t5107u.recon_driver import (
    ERA_2020_23_PBP_TO_CANON,
    HELPER_PBP_TO_CANON_2017,
    HELPER_SHA256,
    INCOMPATIBILITIES,
    ReconRefuse,
    apply_2020_23_identity,
    cell_row_hash,
    freeze_completeness,
    load_stage_b_input_ref,
    load_verified_helper,
    reconstruct_slate,
    refuse_forbidden_path,
    t4_from_t2_sides,
    verify_helper_pin,
    write_recon_bindings,
)

def _pd():
    return pytest.importorskip("pandas")


def _helper():
    pytest.importorskip("pandas")
    return load_verified_helper()


def test_helper_pin_matches_7e77c57f():
    path = verify_helper_pin()
    assert path.name == "build_recon_t4893u.py"
    assert HELPER_SHA256 == (
        "7e77c57f3cc7c1b00527309cdcb556a3f4af8e50b0112bbaedc08ca1049fec64"
    )


def test_refuse_1ee90fac_and_old_oos_paths():
    with pytest.raises(ReconRefuse, match="1ee90fac"):
        refuse_forbidden_path("/tmp/historical_oos_1ee90fac.csv")
    with pytest.raises(ReconRefuse, match="historical_oos"):
        refuse_forbidden_path("data/ops/nfl-reopening-packet-20260916/historical-oos/historical_oos_games.csv")


def test_refuses_helper_main_and_oos_reader():
    mod = _helper()
    with pytest.raises(ReconRefuse, match="main / load_oos"):
        mod.main()
    with pytest.raises(ReconRefuse, match="main / load_oos"):
        mod.load_oos_2016_2017()


def test_identity_overlay_keeps_lv():
    mod = _helper()
    assert dict(mod.PBP_TO_CANON) == HELPER_PBP_TO_CANON_2017
    assert mod.normalize_pbp_abbr("LV") == "OAK"
    overlay = apply_2020_23_identity(mod)
    assert overlay["applied"] == ERA_2020_23_PBP_TO_CANON
    assert mod.normalize_pbp_abbr("LV") == "LV"
    assert mod.normalize_pbp_abbr("LA") == "LAR"
    assert mod.normalize_pbp_abbr("WAS") == "WSH"
    assert any(item["item"].startswith("PBP_TO_CANON") for item in INCOMPATIBILITIES)


def test_synthetic_t1_selfcheck_and_lv_stays_lv():
    mod = _helper()
    apply_2020_23_identity(mod)
    check = mod.synthetic_t1_selfcheck()
    assert check["status"] == "pass"
    assert check["n_checks"] == 7

    rows = [
        {
            "season": 2023,
            "week": 1,
            "game_id": "2023_01_DEN_LV",
            "posteam": "LV",
            "defteam": "DEN",
            "play_type": "pass",
            "sack": 1.0,
            "qb_hit": 0.0,
            "yardline_100": 50.0,
            "touchdown": 0.0,
            "down": 1.0,
            "first_down": 0.0,
            "success": 0.0,
            "epa": -1.0,
        },
        {
            "season": 2023,
            "week": 1,
            "game_id": "2023_01_DEN_LV",
            "posteam": "DEN",
            "defteam": "LV",
            "play_type": "run",
            "sack": 0.0,
            "qb_hit": 0.0,
            "yardline_100": 5.0,
            "touchdown": 1.0,
            "down": 2.0,
            "first_down": 1.0,
            "success": 1.0,
            "epa": 2.0,
        },
    ]
    t1 = mod.t1_from_plays(_pd().DataFrame(rows))
    assert set(t1["team"]) == {"LV", "DEN"}
    assert "OAK" not in set(t1["team"])


def test_t5_and_rest_goldens_from_helper():
    mod = _helper()
    off, deff = mod.team_strength_from_record("1-0")
    assert off == pytest.approx(1.12)
    assert deff == pytest.approx(1.12)
    off0, def0 = mod.team_strength_from_record("0-1")
    assert off0 == pytest.approx(0.90)
    assert def0 == pytest.approx(0.92)
    with pytest.raises(ValueError, match="0-0"):
        mod.team_strength_from_record("0-0")
    # Thursday 20:15 ET = 2023-09-15T00:15:00Z → rest 4
    assert mod.rest_days_et("2023-09-15T00:15:00Z") == 4.0
    # Sunday 13:00 ET
    assert mod.rest_days_et("2023-09-17T17:00:00Z") == 7.0
    # Monday 20:15 ET
    assert mod.rest_days_et("2023-09-19T00:15:00Z") == 6.0


def test_t4_contract_signs_unchanged():
    home = {
        "epa_per_play_offense_5g": 0.10,
        "epa_per_play_defense_allowed_5g": 0.02,
        "pass_rate_5g": 0.55,
        "success_rate_offense_5g": 0.50,
        "success_rate_defense_allowed_5g": 0.40,
        "pressure_rate_generated_5g": 0.30,
        "pressure_rate_allowed_5g": 0.20,
        "red_zone_td_rate_5g": 0.60,
    }
    away = {
        "epa_per_play_offense_5g": -0.10,
        "epa_per_play_defense_allowed_5g": 0.08,
        "pass_rate_5g": 0.45,
        "success_rate_offense_5g": 0.40,
        "success_rate_defense_allowed_5g": 0.46,
        "pressure_rate_generated_5g": 0.22,
        "pressure_rate_allowed_5g": 0.28,
        "red_zone_td_rate_5g": 0.50,
    }
    diffs = t4_from_t2_sides(home, away)
    assert diffs["matchup_diff_off_epa_5g"] == pytest.approx(0.20)
    assert diffs["matchup_diff_def_epa_allowed_5g"] == pytest.approx(0.06)
    assert diffs["matchup_diff_pressure_generated_5g"] == pytest.approx(0.08)
    assert diffs["matchup_diff_pressure_allowed_5g"] == pytest.approx(0.08)
    assert diffs["matchup_diff_red_zone_td_rate_5g"] == pytest.approx(0.10)
    assert diffs["matchup_diff_success_rate_5g"] == pytest.approx(
        ((0.50 - 0.40) + (0.46 - 0.40)) / 2.0
    )
    assert t4_from_t2_sides(None, away)["home_off_epa_5g"] is None


def test_stage_b_input_ref_field_set_no_2017_rescore():
    ref = load_stage_b_input_ref()
    assert ref["rescored_2017_outcomes"] is False
    assert ref["n_games"] == 28
    assert ref["n_rows"] == 28 * 27
    assert ref["fields"] == list(CONTRACT_27)
    assert ref["self_compare"]["pass"] is True
    assert ref["self_compare"]["n_cells"] == 28 * 27
    assert ref["full_matrix_pin"].startswith("cd9af285")
    assert ref["slice_sha256"].startswith("3ab291d6")


def test_freeze_completeness_before_errors():
    mod = _helper()
    apply_2020_23_identity(mod)
    games = [
        {
            "season": 2023,
            "week": 1,
            "game_id": "2023_01_DEN_LV",
            "home": "LV",
            "away": "DEN",
            "kickoff_utc": "2023-09-10T20:00:00Z",
        },
        {
            "season": 2023,
            "week": 2,
            "game_id": "2023_02_BUF_LV",
            "home": "LV",
            "away": "BUF",
            "kickoff_utc": "2023-09-17T20:00:00Z",
        },
    ]
    completed = [
        {
            "season": 2023,
            "week": 1,
            "game_id": "2023_01_DEN_LV",
            "home": "LV",
            "away": "DEN",
            "home_score": 17.0,
            "away_score": 10.0,
            "kickoff_utc": "2023-09-10T20:00:00Z",
        },
        {
            "season": 2023,
            "week": 1,
            "game_id": "2023_01_BUF_NYJ",
            "home": "NYJ",
            "away": "BUF",
            "home_score": 16.0,
            "away_score": 22.0,
            "kickoff_utc": "2023-09-11T17:00:00Z",
        },
    ]
    seal = freeze_completeness(games, completed, mod)
    assert seal["frozen_before_errors"] is True
    assert seal["frozen_before_pbp_open"] is True
    assert "2023_01_DEN_LV" in {e["game_id"] for e in seal["excluded"]}
    assert seal["eligible_game_ids"] == ["2023_02_BUF_LV"]
    with pytest.raises(ReconRefuse, match="frozen before errors"):
        reconstruct_slate(
            targets=games,
            games=games,
            completed=completed,
            helper=mod,
            plays=_pd().DataFrame(),
            completeness_seal=None,
        )


def test_leakage_refuses_same_or_later_kickoff():
    mod = _helper()
    apply_2020_23_identity(mod)
    games = [
        {
            "season": 2023,
            "week": 1,
            "game_id": "2023_01_DEN_LV",
            "home": "LV",
            "away": "DEN",
            "kickoff_utc": "2023-09-17T20:00:00Z",
        },
        {
            "season": 2023,
            "week": 2,
            "game_id": "2023_02_BUF_LV",
            "home": "LV",
            "away": "BUF",
            "kickoff_utc": "2023-09-17T20:00:00Z",
        },
    ]
    completed = [
        {
            "season": 2023,
            "week": 1,
            "game_id": "2023_01_DEN_LV",
            "home": "LV",
            "away": "DEN",
            "home_score": 17.0,
            "away_score": 10.0,
            "kickoff_utc": "2023-09-10T20:00:00Z",
        },
        {
            "season": 2023,
            "week": 1,
            "game_id": "2023_01_BUF_NYJ",
            "home": "NYJ",
            "away": "BUF",
            "home_score": 16.0,
            "away_score": 22.0,
            "kickoff_utc": "2023-09-11T17:00:00Z",
        },
    ]
    # T5 uses completed kickoffs (prior). Leakage uses games.csv kickoff of consumed PBP id.
    games[0]["kickoff_utc"] = "2023-09-17T20:00:00Z"
    seal = freeze_completeness([games[1]], completed, mod)
    assert seal["eligible_game_ids"] == ["2023_02_BUF_LV"]
    plays = _pd().DataFrame(
        [
            {
                "season": 2023,
                "week": 1,
                "game_id": "2023_01_DEN_LV",
                "posteam": "LV",
                "defteam": "DEN",
                "play_type": "pass",
                "sack": 0.0,
                "qb_hit": 0.0,
                "yardline_100": 40.0,
                "touchdown": 0.0,
                "down": 1.0,
                "first_down": 0.0,
                "success": 1.0,
                "epa": 0.2,
            },
            {
                "season": 2023,
                "week": 1,
                "game_id": "2023_01_DEN_LV",
                "posteam": "DEN",
                "defteam": "LV",
                "play_type": "run",
                "sack": 0.0,
                "qb_hit": 0.0,
                "yardline_100": 40.0,
                "touchdown": 0.0,
                "down": 1.0,
                "first_down": 0.0,
                "success": 0.0,
                "epa": -0.1,
            },
            {
                "season": 2023,
                "week": 1,
                "game_id": "2023_01_BUF_NYJ",
                "posteam": "BUF",
                "defteam": "NYJ",
                "play_type": "pass",
                "sack": 0.0,
                "qb_hit": 0.0,
                "yardline_100": 40.0,
                "touchdown": 0.0,
                "down": 1.0,
                "first_down": 0.0,
                "success": 1.0,
                "epa": 0.3,
            },
            {
                "season": 2023,
                "week": 1,
                "game_id": "2023_01_BUF_NYJ",
                "posteam": "NYJ",
                "defteam": "BUF",
                "play_type": "run",
                "sack": 0.0,
                "qb_hit": 0.0,
                "yardline_100": 40.0,
                "touchdown": 0.0,
                "down": 1.0,
                "first_down": 0.0,
                "success": 0.0,
                "epa": 0.0,
            },
        ]
    )
    with pytest.raises(ReconRefuse, match="leakage"):
        reconstruct_slate(
            targets=[games[1]],
            games=games,
            completed=completed,
            helper=mod,
            plays=plays,
            completeness_seal=seal,
        )


def _two_team_plays():
    def play(gid: str, off: str, deff: str, **kw: object) -> dict:
        row = {
            "season": 2023,
            "week": 1,
            "game_id": gid,
            "posteam": off,
            "defteam": deff,
            "play_type": "pass",
            "sack": 0.0,
            "qb_hit": 0.0,
            "yardline_100": 40.0,
            "touchdown": 0.0,
            "down": 1.0,
            "first_down": 0.0,
            "success": 1.0,
            "epa": 0.1,
        }
        row.update(kw)
        return row

    return _pd().DataFrame(
        [
            play("2023_01_DEN_LV", "LV", "DEN"),
            play(
                "2023_01_DEN_LV",
                "LV",
                "DEN",
                play_type="run",
                yardline_100=5.0,
                touchdown=1.0,
                success=1.0,
                epa=2.0,
            ),
            play("2023_01_DEN_LV", "DEN", "LV"),
            play(
                "2023_01_DEN_LV",
                "DEN",
                "LV",
                play_type="run",
                yardline_100=5.0,
                touchdown=0.0,
                success=0.0,
                epa=-0.2,
            ),
            play("2023_01_BUF_NYJ", "BUF", "NYJ"),
            play(
                "2023_01_BUF_NYJ",
                "BUF",
                "NYJ",
                play_type="run",
                yardline_100=5.0,
                touchdown=1.0,
                success=1.0,
                epa=2.0,
            ),
            play("2023_01_BUF_NYJ", "NYJ", "BUF"),
            play(
                "2023_01_BUF_NYJ",
                "NYJ",
                "BUF",
                play_type="run",
                yardline_100=5.0,
                touchdown=0.0,
                success=0.0,
                epa=-0.2,
            ),
        ]
    )


def test_synthetic_slate_new_hashes_and_labels():
    mod = _helper()
    apply_2020_23_identity(mod)
    games = [
        {
            "season": 2023,
            "week": 1,
            "game_id": "2023_01_DEN_LV",
            "home": "LV",
            "away": "DEN",
            "kickoff_utc": "2023-09-10T20:00:00Z",
        },
        {
            "season": 2023,
            "week": 1,
            "game_id": "2023_01_BUF_NYJ",
            "home": "NYJ",
            "away": "BUF",
            "kickoff_utc": "2023-09-11T17:00:00Z",
        },
        {
            "season": 2023,
            "week": 2,
            "game_id": "2023_02_BUF_LV",
            "home": "LV",
            "away": "BUF",
            "kickoff_utc": "2023-09-17T20:00:00Z",
        },
    ]
    completed = [
        {
            "season": 2023,
            "week": 1,
            "game_id": g["game_id"],
            "home": g["home"],
            "away": g["away"],
            "home_score": 21.0,
            "away_score": 17.0,
            "kickoff_utc": g["kickoff_utc"],
        }
        for g in games
        if g["week"] == 1
    ]
    seal = freeze_completeness(games, completed, mod)
    assert seal["eligible_game_ids"] == ["2023_02_BUF_LV"]
    result = reconstruct_slate(
        targets=games,
        games=games,
        completed=completed,
        helper=mod,
        plays=_two_team_plays(),
        completeness_seal=seal,
    )
    assert result["label"] == "RECONSTRUCTED"
    assert result["fit_label"] == "RETRO_FIT"
    assert result["research_label"] == "RESEARCH_CONSUMED_RETRO"
    assert result["cert_candidate"] == 0
    assert result["archived_if_mus_required"] is False
    assert result["old_main_oos_invoked"] is False
    assert result["opened_1ee90fac"] is False
    assert result["n_complete_27"] == 1
    assert result["n_cells"] == 27
    assert result["matrix_sha256"] != "b41f4b43e1367bd5658c743475b9b84535c65395630a0b06c804f8b3552b81f4"
    fields = [row["field"] for row in result["matrix"]]
    assert set(fields) == set(CONTRACT_27)
    assert len(fields) == 27
    assert all(row["row_sha256"] == cell_row_hash(row) for row in result["matrix"])
    assert all(row["label"] == "RECONSTRUCTED" for row in result["matrix"])
    rest = next(r for r in result["matrix"] if r["field"] == "rest_days_home")
    assert rest["reconstructed_value"] == "7.0"
    lv_off = next(r for r in result["matrix"] if r["field"] == "offense_index_home")
    assert lv_off["reconstructed_value"] == "1.120000"


def test_write_bindings_and_compare_tolerances_not_loosened(tmp_path: Path):
    result = {
        "matrix_sha256": "abc",
        "n_cells": 27,
        "n_complete_27": 1,
        "n_partial": 0,
        "completeness_seal": {"completeness_sha256": "def"},
        "incompatibilities": list(INCOMPATIBILITIES),
        "provenance": [],
    }
    dest = tmp_path / "RECON_BINDINGS.json"
    digest = write_recon_bindings(result, dest)
    payload = json.loads(dest.read_text())
    assert payload["cert_candidate"] == 0
    assert payload["old_b41f4b43_row_hash_match_expected"] is False
    assert digest
    prior = {("g", "rest_days_home"): {"status": "DERIVED_PREGAME", "reconstructed_value": "7.0"}}
    rebuilt = {("g", "rest_days_home"): {"status": "DERIVED_PREGAME", "reconstructed_value": "7.0000001"}}
    # keyset/fields incomplete on purpose — tolerances themselves stay 1e-9
    compared = compare_cell_maps(rebuilt, prior)
    assert compared["tolerances"]["rest"] == 1e-9
    assert compared["tolerances"]["index"] == 1e-6
    assert compared["tolerances"]["pass_rate_pressure_rz_def_epa_diff"] == 0.0
