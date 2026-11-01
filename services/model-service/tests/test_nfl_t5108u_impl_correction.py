"""t5108u implementation correction: produce-μ, signed bootstrap, one-run, inputs."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.services.nfl_t5107u.builder import BuilderRefuse, build_forecasts
from src.services.nfl_t5107u.evaluator import (
    BOOT_B,
    BOOT_SEED,
    EvalRefuse,
    freeze_eligible_cohorts,
    freeze_forecast_cohort,
    mean_stat,
    run_eval_score,
    run_paired_margin_eval,
    signed_loss_diffs,
)
from src.services.nfl_t5107u.if_control import (
    LABEL_RECONSTRUCTED,
    REQUIRED_FIELDS,
    resolve_if_margin,
)
from src.services.nfl_t5107u.if_produce import IF_TIP, produce_if_mu, seed_for
from src.services.nfl_t5107u.inputs import (
    PERMITTED_SEASONS,
    SEALED_SEASONS,
    InputRefuse,
    extract_reg_games,
    input_availability_table,
    prepare_local_inputs,
)
from src.services.nfl_t5107u.manifest import DESIGN_SEAL_SHA256, append_input_bindings, design_body_sha256
from src.services.nfl_t5107u.one_run import OneRunRefuse, bind_one_run, load_one_run
from src.services.nfl_t5107u.q2 import Game


def _complete_packet(game_id: str = "2020_01_HOU_KC") -> dict:
    packet = {name: {"status": "DERIVED_PREGAME", "reconstructed_value": 1.0} for name in REQUIRED_FIELDS}
    packet["game_id"] = {"status": "DERIVED_PREGAME", "reconstructed_value": game_id}
    packet["home_team"] = {"status": "DERIVED_PREGAME", "reconstructed_value": "KC"}
    packet["away_team"] = {"status": "DERIVED_PREGAME", "reconstructed_value": "HOU"}
    packet["matchup_season"] = {"status": "DERIVED_PREGAME", "reconstructed_value": 2020}
    packet["matchup_week"] = {"status": "DERIVED_PREGAME", "reconstructed_value": 1}
    packet["rest_days_home"] = {"status": "DERIVED_PREGAME", "reconstructed_value": 7.0}
    packet["rest_days_away"] = {"status": "DERIVED_PREGAME", "reconstructed_value": 7.0}
    return packet


def test_produce_mu_from_frozen_if_tree():
    produced = produce_if_mu(_complete_packet("2020_01_HOU_KC"))
    assert produced["source"] == "reconstructed_if_produce"
    assert produced["if_tip"] == IF_TIP
    assert produced["market_blend"] == 0
    assert produced["simulations"] == 4000
    assert produced["seed"] == seed_for("2020_01_HOU_KC")
    assert isinstance(produced["if_margin_mu"], float)

    resolved = resolve_if_margin("2020_01_HOU_KC", recon_packet=_complete_packet("2020_01_HOU_KC"))
    assert resolved.status == "reconstructed"
    assert resolved.label == LABEL_RECONSTRUCTED
    assert resolved.source == "reconstructed_if_produce"
    assert resolved.margin_mu == pytest.approx(produced["if_margin_mu"])


def test_builder_refuses_supplied_reconstructed_mus():
    target = Game(
        season=2020,
        week=1,
        game_id="2020_01_HOU_KC",
        home="KC",
        away="HOU",
        kickoff_utc=datetime(2020, 9, 13, 17, tzinfo=timezone.utc),
    )
    with pytest.raises(BuilderRefuse, match="produce-μ"):
        build_forecasts([target], history=[], reconstructed_if_mus={target.game_id: 2.5})


def test_signed_loss_mean_and_negative_paired_improvement():
    # Hand-checkable:
    # g1 actual=7 C=6 IF=3 M=10 → Lc=1 Lif=4 Lm=3  dIF=-3 dM=-2
    # g2 actual=-3 C=-2 IF=0 M=4 → Lc=1 Lif=3 Lm=7  dIF=-2 dM=-6
    diffs_if = signed_loss_diffs([6.0, -2.0], [3.0, 0.0], [7.0, -3.0])
    diffs_m = signed_loss_diffs([6.0, -2.0], [10.0, 4.0], [7.0, -3.0])
    assert diffs_if == pytest.approx([-3.0, -2.0])
    assert diffs_m == pytest.approx([-2.0, -6.0])
    assert mean_stat(diffs_if) == pytest.approx(-2.5)
    assert mean_stat(diffs_m) == pytest.approx(-4.0)
    assert mean_stat(diffs_if) < 0


def test_paired_margin_eval_hand_checkable_negative_improvement():
    forecasts = [
        {"game_id": "g1", "season": 2020, "week": 1, "m_challenger": 6.0, "m_if": 3.0},
        {"game_id": "g2", "season": 2020, "week": 2, "m_challenger": -2.0, "m_if": 0.0},
    ]
    outcomes = {
        "g1": {"season": 2020, "week": 1, "home_score": 27, "away_score": 20},
        "g2": {"season": 2020, "week": 2, "home_score": 10, "away_score": 13},
    }
    market = [
        {"game_id": "g1", "market_margin": 10.0},
        {"game_id": "g2", "market_margin": 4.0},
    ]
    scored = run_paired_margin_eval(forecasts, outcomes, market_points=market)
    assert scored["n"] == 2
    assert scored["mae_challenger"] == pytest.approx(1.0)
    assert scored["mae_if"] == pytest.approx(3.5)
    assert scored["delta_mae_vs_if"] == pytest.approx(-2.5)
    assert scored["mean_signed_diff_vs_if"] == pytest.approx(-2.5)
    assert scored["mean_signed_diff_vs_market"] == pytest.approx(-4.0)
    assert scored["bootstrap_game"]["B"] == BOOT_B
    assert scored["bootstrap_game"]["seed"] == BOOT_SEED
    assert scored["bootstrap_game"]["stat" if False else "point"] == pytest.approx(-2.5)
    assert scored["bootstrap_season_week"]["B"] == BOOT_B
    assert scored["mean_signed_diff_vs_if"] < 0
    assert scored["bootstrap_game"]["ci95"][1] < 0


def test_freeze_cohorts_after_eligibility_before_outcomes():
    payload = {
        "schema_version": "nfl-t5107u-forecast-v1",
        "eval": None,
        "fit_policy": {"fit_policy": "TRANSFER_FROZEN_DEV_2013_2016"},
        "if_arm": {"archived": 0, "reconstructed": 0, "blocked": 0, "total": 2},
        "forecasts": [
            {"game_id": "g1", "season": 2020},
            {"game_id": "g2", "season": 2020},
        ],
    }
    market = {
        "points": [
            {"game_id": "g1", "market_margin": 7.5, "p_compare": "bound", "p_home_fair": 0.62},
            {"game_id": "g2", "market_margin": None, "p_compare": "unavailable", "p_home_fair": None},
        ]
    }
    frozen = freeze_eligible_cohorts(payload, market)
    assert frozen["sealed_after_eligibility_before_outcome_join"] is True
    assert frozen["margin_cohort"]["game_ids"] == ["g1"]
    assert frozen["probability_cohort"]["game_ids"] == ["g1"]
    assert frozen["declared_game_ids"] == ["g1", "g2"]
    dirty = {"points": [{**market["points"][0], "home_score": 27, "actual_margin": 7}]}
    with pytest.raises(EvalRefuse, match="already joined"):
        freeze_eligible_cohorts(payload, dirty)


def test_one_run_bind_refuses_duplicate_and_mismatch(tmp_path: Path):
    path = tmp_path / "ONE_RUN.json"
    rec = bind_one_run(
        effective_spec_sha256="a" * 64,
        code_sha256="b" * 64,
        input_sha256="c" * 64,
        forecast_sha256="d" * 64,
        cohort_sha256="e" * 64,
        alex_go_id="ALEX_GO_TEST",
        path=path,
    )
    assert rec["alex_go_id"] == "ALEX_GO_TEST"
    assert load_one_run(path)["bind_id"] == rec["bind_id"]
    with pytest.raises(OneRunRefuse, match="duplicate"):
        bind_one_run(
            effective_spec_sha256="a" * 64,
            code_sha256="b" * 64,
            input_sha256="c" * 64,
            forecast_sha256="d" * 64,
            cohort_sha256="e" * 64,
            alex_go_id="ALEX_GO_TEST",
            path=path,
        )
    with pytest.raises(OneRunRefuse, match="mismatch"):
        bind_one_run(
            effective_spec_sha256="a" * 64,
            code_sha256="b" * 64,
            input_sha256="c" * 64,
            forecast_sha256="f" * 64,
            cohort_sha256="e" * 64,
            alex_go_id="ALEX_GO_TEST",
            path=path,
        )


def test_real_eval_gate_and_one_run_numerical_path(tmp_path: Path):
    payload = {
        "schema_version": "nfl-t5107u-forecast-v1",
        "eval": None,
        "fit_policy": {"fit_policy": "TRANSFER"},
        "if_arm": {"total": 1, "archived": 1, "reconstructed": 0, "blocked": 0},
        "forecasts": [
            {"game_id": "g1", "season": 2020, "week": 1, "m_challenger": 6.0, "m_if": 3.0},
        ],
    }
    frozen = freeze_forecast_cohort(payload)
    outcomes = {"g1": {"season": 2020, "week": 1, "home_score": 27, "away_score": 20}}
    with pytest.raises(EvalRefuse, match="Alex preflight"):
        run_eval_score(frozen, outcomes)

    path = tmp_path / "ONE_RUN.json"
    rec = bind_one_run(
        effective_spec_sha256="1" * 64,
        code_sha256="2" * 64,
        input_sha256="3" * 64,
        forecast_sha256=frozen.forecast_sha256,
        cohort_sha256=frozen.cohort_sha256,
        alex_go_id="ALEX_GO_SYNTHETIC",
        path=path,
    )
    scored = run_eval_score(
        frozen,
        outcomes,
        exec_bind=rec["bind_id"],
        alex_go_id="ALEX_GO_SYNTHETIC",
        one_run_path=path,
    )
    assert scored["n"] == 1
    assert scored["mae_challenger"] == pytest.approx(1.0)
    assert scored["mean_signed_diff_vs_if"] == pytest.approx(-3.0)
    assert scored["one_run_bind_id"] == rec["bind_id"]


def test_input_availability_lists_missing_with_owner_and_field():
    table = input_availability_table()
    by = {row["input"]: row for row in table}
    assert by["b41f4b43 hist inputs / efficiency+index 5g"]["status"] == "MISSING"
    assert "offense_index_home" in by["b41f4b43 hist inputs / efficiency+index 5g"]["dependent_field"]
    assert by["frozen IF tree 6ca03716"]["status"] == "available"
    assert by["Stage C / scored columns"]["status"] == "FORBIDDEN"
    assert set(PERMITTED_SEASONS) == {2020, 2021, 2022, 2023}
    assert set(SEALED_SEASONS) == {2024, 2025, 2026}


def test_prepare_local_inputs_extracts_2023_and_refuses_sealed(tmp_path: Path):
    archive = Path("/Volumes/KosEdgeData/nflverse/archive/pbp/2026-11-01")
    if not (archive / "play_by_play_2023.csv").is_file():
        pytest.skip("owned PBP archive not mounted")
    with pytest.raises(InputRefuse, match="sealed"):
        extract_reg_games(archive / "play_by_play_2024.csv", season=2024)
    dest = tmp_path / "inputs"
    bindings = prepare_local_inputs(archive=archive, dest=dest)
    assert bindings["prepared"][1]["n"] >= 200
    assert bindings["prepared"][1]["sha256"]
    rows = (dest / "schedule_results_2023.csv").read_text(encoding="utf-8").splitlines()
    assert rows[0].startswith("game_id,season,week")
    assert any(line.startswith("2023_01_") for line in rows)
    assert "2024_" not in (dest / "schedule_results_2020_2023.csv").read_text(encoding="utf-8")


def test_append_preserves_design_seal(tmp_path: Path):
    src = Path(__file__).resolve().parents[3] / "data/ops/nfl-forecast-builder-t5107u/FROZEN_MANIFEST.json"
    if not src.is_file():
        pytest.skip("FROZEN_MANIFEST not in cwd")
    dest = tmp_path / "FROZEN_MANIFEST.json"
    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    original = __import__("json").loads(dest.read_text(encoding="utf-8"))
    assert design_body_sha256(original) == DESIGN_SEAL_SHA256
    appended = append_input_bindings(
        dest,
        bindings={"availability": input_availability_table(), "notes": ["unit"]},
    )
    assert appended["design_seal_sha256"] == DESIGN_SEAL_SHA256
    assert appended["design_seal_is_forecast_freeze"] is False
    assert appended["appended_manifest_sha256"]
    assert design_body_sha256(appended) == DESIGN_SEAL_SHA256
    assert appended["input_bindings"]["availability"]
