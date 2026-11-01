"""t5125u R2-B2: loader-only R2 EVAL runner + 437 DEV REG diagnostic."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.services.nfl_t5107u.dev_research import (
    DEV_REG_N,
    DEV_REG_SHA256,
    LABEL,
    DevResearchRefuse,
    freeze_dev_metadata_eligibility,
)
from src.services.nfl_t5107u.dev_research_cohort import (
    COHORT_OUTPUT_CONTRACT,
    materialize_dev_research_cohort_437,
    run_dev_research_cohort,
    validate_cohort_record,
)
from src.services.nfl_t5107u.evaluator import EvalRefuse, FrozenCohort, freeze_forecast_cohort
from src.services.nfl_t5107u.inputs import QUOTE_MANIFEST_SHA256
from src.services.nfl_t5107u.metric_cohorts import declared_reg_hold_table
from src.services.nfl_t5107u.one_run import STATUS_BOUND, bind_one_run, claim_one_run, load_one_run
from src.services.nfl_t5107u.outcome_gate import (
    FIRST_CASE_FILE_SHA256,
    FIRST_CASE_GAME_ID,
    FIRST_CASE_RECORD_SHA256,
    ScoringOutcomeLoader,
    refuse_overwrite_first_case_record,
)
from src.services.nfl_t5107u.r2_byte_rehash import bind_r2_runtime_bytes
from src.services.nfl_t5107u.r2_eval_runner import run_eval_score_r2

ROOT = Path(__file__).resolve().parents[3]
FIRST_CASE = ROOT / "data/ops/nfl-forecast-builder-t5107u/DEV_RESEARCH_t5119u_R2B.json"
ONE_RUN_SPENT = ROOT / "data/ops/nfl-forecast-builder-t5107u/ONE_RUN.json"
ONE_EXEC_SPENT = ROOT / "data/ops/nfl-forecast-builder-t5107u/ONE_EXEC_RESULT_t5116u.json"


def _row(gid: str, season: int, **extra) -> dict:
    base = {
        "game_id": gid,
        "season": season,
        "week": 2,
        "season_type": "REG",
        "home": "CLE",
        "away": "CIN",
        "kickoff_utc": "2020-09-18T00:20:00Z",
        "m_if": 2.0,
        "m_q2": 4.0,
        "m_challenger": 3.0,
        "if_status": "reconstructed",
        "if_label": "RECONSTRUCTED_IF_6ca03716",
    }
    base.update(extra)
    return base


def _eval_payload():
    return {
        "schema_version": "nfl-t5107u-forecast-v1",
        "eval": None,
        "fit_policy": "TRANSFER_FROZEN_DEV_2013_2016",
        "if_arm": {"total": 2, "archived": 0, "reconstructed": 2, "blocked": 0},
        "forecasts": [_row("d", 2020), _row("e", 2022)],
    }


def _hold(*, trip: bool = False) -> dict:
    excluded = {2020: 16, 2021: 16, 2022: 18, 2023: 16}
    partial = {2020: 30, 2021: 29, 2022: 200 if trip else 32, 2023: 28}
    return declared_reg_hold_table(recon_excluded_n=excluded, recon_partial_n=partial)


def _eligible(*, hold=None):
    return {
        "sealed_after_eligibility_before_outcome_join": True,
        "quote_manifest_sha256": QUOTE_MANIFEST_SHA256,
        "metric_split": "EVAL",
        "margin_cohort": {"game_ids": ["e"], "n": 1},
        "g5_hold": hold if hold is not None else _hold(),
    }


def _bind(path: Path, frozen):
    return bind_one_run(
        effective_spec_sha256="1" * 64,
        code_sha256="2" * 64,
        input_sha256="3" * 64,
        forecast_sha256=frozen.forecast_sha256,
        cohort_sha256=frozen.cohort_sha256,
        alex_go_id="ALEX_GO_T5125U",
        path=path,
    )


def _loader():
    return ScoringOutcomeLoader(
        lambda: {"e": {"season": 2022, "week": 2, "home_score": 20, "away_score": 10}}
    )


def _byte_pins(tmp_path: Path, payload: dict | None = None) -> dict:
    freeze = tmp_path / "freeze.json"
    freeze.write_text(json.dumps(payload or _eval_payload(), sort_keys=True) + "\n")
    manifest = tmp_path / "quote_manifest.json"
    manifest.write_text('{"admitted":true,"note":"tmp-not-r2a"}\n')
    extract = tmp_path / "quote_extract.jsonl"
    extract.write_text('{"game_id":"e"}\n')
    bind_path = tmp_path / "R2_RUNTIME_BYTES.json"
    bind_r2_runtime_bytes(
        forecast_file=freeze,
        quote_manifest_file=manifest,
        quote_extract_files=[extract],
        path=bind_path,
    )
    return dict(
        forecast_file=freeze,
        quote_manifest_file=manifest,
        quote_extract_files=[extract],
        r2_byte_bind=bind_path,
    )


def _r2_kwargs(path: Path, rec, eligible, loader, *, pins=None):
    kwargs = dict(
        outcome_loader=loader,
        exec_bind=rec["bind_id"],
        alex_go_id="ALEX_GO_T5125U",
        one_run_path=path,
        live_effective_spec_sha256="1" * 64,
        live_code_sha256="2" * 64,
        live_input_sha256="3" * 64,
        eligible_cohorts=eligible,
        score_body=lambda *a, **k: {"n": 1, "mae_challenger": 1.0, "mean_signed_diff_vs_if": -1.0},
    )
    kwargs.update(pins if pins is not None else _byte_pins(path.parent))
    return kwargs


def test_r2_runner_refuses_preloaded_outcomes_loader_count_zero(tmp_path: Path):
    frozen = freeze_forecast_cohort(_eval_payload())
    path = tmp_path / "ONE_RUN.json"
    rec = _bind(path, frozen)
    loader = _loader()
    with pytest.raises(EvalRefuse, match="refuses preloaded scoring outcomes"):
        run_eval_score_r2(
            frozen,
            {"e": {"season": 2022, "week": 2, "home_score": 1, "away_score": 0}},
            **_r2_kwargs(path, rec, _eligible(), loader),
        )
    assert loader.call_count == 0
    assert load_one_run(path)["status"] == STATUS_BOUND


def test_r2_runner_requires_outcome_loader():
    frozen = freeze_forecast_cohort(_eval_payload())
    with pytest.raises(EvalRefuse, match="requires outcome_loader"):
        run_eval_score_r2(frozen, None)


def test_r2_hold_refuse_loader_count_zero(tmp_path: Path):
    frozen = freeze_forecast_cohort(_eval_payload())
    path = tmp_path / "ONE_RUN.json"
    rec = _bind(path, frozen)
    loader = _loader()
    with pytest.raises(EvalRefuse, match="HOLD tripped"):
        run_eval_score_r2(frozen, None, **_r2_kwargs(path, rec, _eligible(hold=_hold(trip=True)), loader))
    assert loader.call_count == 0


def test_r2_hash_refuse_loader_count_zero(tmp_path: Path):
    payload = _eval_payload()
    frozen = freeze_forecast_cohort(payload)
    tampered = FrozenCohort(
        forecast_sha256="a" * 64,
        cohort_sha256=frozen.cohort_sha256,
        game_ids=frozen.game_ids,
        n=frozen.n,
        sealed_before_outcome_join=True,
        payload=payload,
    )
    loader = _loader()
    pins = _byte_pins(tmp_path, payload)
    with pytest.raises(EvalRefuse, match="hash mismatch"):
        run_eval_score_r2(tampered, None, outcome_loader=loader, exec_bind="b" * 64, **pins)
    assert loader.call_count == 0


def test_r2_claim_refuse_loader_count_zero(tmp_path: Path):
    frozen = freeze_forecast_cohort(_eval_payload())
    path = tmp_path / "ONE_RUN.json"
    rec = _bind(path, frozen)
    claim_one_run(path, rec["bind_id"])
    loader = _loader()
    with pytest.raises(EvalRefuse, match="claim|IN_PROGRESS|second"):
        run_eval_score_r2(frozen, None, **_r2_kwargs(path, rec, _eligible(), loader))
    assert loader.call_count == 0


def test_r2_success_calls_loader_once(tmp_path: Path):
    frozen = freeze_forecast_cohort(_eval_payload())
    path = tmp_path / "ONE_RUN.json"
    rec = _bind(path, frozen)
    loader = _loader()
    scored = run_eval_score_r2(frozen, None, **_r2_kwargs(path, rec, _eligible(), loader))
    assert loader.call_count == 1
    assert scored["r2_runner"] == "run_eval_score_r2"
    assert scored["preloaded_outcomes"] is False
    assert scored["one_run_status"] == "CONSUMED"


def test_cohort_refuses_preloaded_outcomes_and_requires_loader():
    forecasts = [_row("2020_02_CIN_CLE", 2020)]
    loader = ScoringOutcomeLoader(
        lambda: {"2020_02_CIN_CLE": {"season": 2020, "week": 2, "home_score": 35, "away_score": 30}}
    )
    with pytest.raises(DevResearchRefuse, match="refuses preloaded"):
        run_dev_research_cohort(
            forecasts,
            outcomes={"2020_02_CIN_CLE": {"home_score": 1, "away_score": 0}},
            outcome_loader=loader,
            require_dev_reg_pin=False,
            synthetic=True,
        )
    assert loader.call_count == 0
    with pytest.raises(DevResearchRefuse, match="requires outcome_loader"):
        run_dev_research_cohort(forecasts, require_dev_reg_pin=False, synthetic=True)


def test_cohort_synthetic_contract_and_metrics(tmp_path: Path):
    forecasts = [
        _row("2020_02_CIN_CLE", 2020),
        _row("2020_02_ATL_DAL", 2020, home="DAL", away="ATL", m_if=0.0, m_q2=2.0, m_challenger=1.0),
    ]
    # actuals: 35-30=5 → err_c 3-5=-2; 27-20=7 → err_c 1-7=-6
    loader = ScoringOutcomeLoader(
        lambda: {
            "2020_02_CIN_CLE": {"season": 2020, "week": 2, "home_score": 35, "away_score": 30},
            "2020_02_ATL_DAL": {"season": 2020, "week": 2, "home_score": 27, "away_score": 20},
        }
    )
    dest = tmp_path / "DEV_RESEARCH_t5125u_R2B2_437.json"
    record = run_dev_research_cohort(
        forecasts,
        outcome_loader=loader,
        require_dev_reg_pin=False,
        synthetic=True,
        dest=dest,
    )
    assert loader.call_count == 1
    assert record["n"] == 2
    assert record["mae_challenger"] == pytest.approx(4.0)
    assert record["mae_if"] == pytest.approx(5.0)
    assert record["rmse_challenger"] == pytest.approx(20.0**0.5)
    assert record["bias_challenger"] == pytest.approx(-4.0)
    assert record["market"]["status"] == "NOT_READY"
    assert record["market"]["invented_comparison"] is False
    assert record["one_run_claim"] is False
    assert record["bootstrap_game"]["B"] == 10000
    assert record["bootstrap_game"]["seed"] == 20261101
    assert record["bootstrap_season_week"]["B"] == 10000
    assert "ci95" in record["bootstrap_game"]
    assert "ci95" in record["bootstrap_season_week"]
    validate_cohort_record(record)
    for key in COHORT_OUTPUT_CONTRACT:
        assert key in record
    assert dest.is_file()


def test_first_case_and_t5116u_preserved():
    assert FIRST_CASE.is_file()
    body = json.loads(FIRST_CASE.read_text())
    assert body["game_id"] == FIRST_CASE_GAME_ID
    assert body["record_sha256"] == FIRST_CASE_RECORD_SHA256
    assert hashlib.sha256(FIRST_CASE.read_bytes()).hexdigest() == FIRST_CASE_FILE_SHA256
    assert hashlib.sha256(ONE_RUN_SPENT.read_bytes()).hexdigest() == (
        "96478f6b91fb12c6c9a0f3941870819cf3d9fa8da4804feecaf9650b7180cc7d"
    )
    assert hashlib.sha256(ONE_EXEC_SPENT.read_bytes()).hexdigest() == (
        "913242590b43dc03f45b88ca970f39db5523e53e67983a65d599fb124adf81f6"
    )
    with pytest.raises(Exception, match="first-case"):
        refuse_overwrite_first_case_record(FIRST_CASE)


def test_materialize_437_real_freeze(tmp_path: Path):
    dest = tmp_path / "DEV_RESEARCH_t5125u_R2B2_437.json"
    record = materialize_dev_research_cohort_437(dest=dest)
    assert record["dev_reg_n"] == DEV_REG_N
    assert record["dev_reg_sha256"] == DEV_REG_SHA256
    assert record["n"] == 437
    assert record["joined_n"] == 437
    assert record["n_by_season"]["2020"] + record["n_by_season"]["2021"] == 437
    assert record["label"] == LABEL
    assert record["market"]["status"] == "NOT_READY"
    assert record["one_run_claim"] is False
    assert record["first_case_preserved"]["record_sha256"] == FIRST_CASE_RECORD_SHA256
    assert record["first_case_preserved"]["in_cohort"] is True
    # first-case arithmetic must match the sealed single-game record
    first = next(g for g in record["games"] if g["game_id"] == FIRST_CASE_GAME_ID)
    assert first["actual_margin"] == pytest.approx(5.0)
    assert first["m_challenger"] == pytest.approx(1.5119867482428484)
    assert first["err_challenger"] == pytest.approx(-3.4880132517571516)
    assert record["rng"]["if_seed_first_case"] == 672662
    assert record["rng"]["if_simulations"] == 4000
    assert record["rng"]["if_mus_reproduced"] is False
    assert record["bootstrap_game"]["n"] == 437
    assert record["bootstrap_season_week"]["n"] == 437
    # eligibility freeze happened before loader: pin still 437
    eligibility = freeze_dev_metadata_eligibility(
        json.loads((ROOT / "data/ops/nfl-forecast-builder-t5107u/FORECAST_FREEZE_t5112u.json").read_text())[
            "forecasts"
        ]
    )
    assert eligibility["eligible_n"] == 437
    # sealed first-case file still intact after cohort write to tmp
    assert hashlib.sha256(FIRST_CASE.read_bytes()).hexdigest() == FIRST_CASE_FILE_SHA256
    with pytest.raises(DevResearchRefuse, match="first-case"):
        materialize_dev_research_cohort_437(dest=FIRST_CASE)
