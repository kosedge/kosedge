"""t5116u: quote-eligible EVAL + G5 HOLD fail-closed before claim/join."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.services.nfl_t5107u.evaluator import EvalRefuse, freeze_forecast_cohort, run_eval_score
from src.services.nfl_t5107u.inputs import QUOTE_MANIFEST_SHA256
from src.services.nfl_t5107u.metric_cohorts import declared_reg_hold_table
from src.services.nfl_t5107u.one_run import STATUS_BOUND, bind_one_run, load_one_run


def _row(gid: str, season: int) -> dict:
    return {
        "game_id": gid,
        "season": season,
        "week": 2,
        "m_challenger": 3.0,
        "m_if": 2.0,
    }


def _payload():
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


def _eligible(*, quote: str = QUOTE_MANIFEST_SHA256, sealed: bool = True, hold=None, extra=None):
    ids = ["e"] + list(extra or [])
    return {
        "sealed_after_eligibility_before_outcome_join": sealed,
        "quote_manifest_sha256": quote,
        "metric_split": "EVAL",
        "margin_cohort": {"game_ids": ids, "n": len(ids)},
        "g5_hold": hold if hold is not None else _hold(),
    }


def _bind(path: Path, frozen):
    return bind_one_run(
        effective_spec_sha256="1" * 64,
        code_sha256="2" * 64,
        input_sha256="3" * 64,
        forecast_sha256=frozen.forecast_sha256,
        cohort_sha256=frozen.cohort_sha256,
        alex_go_id="ALEX_GO_T5116U",
        path=path,
    )


def _score(frozen, path, rec, eligible):
    return run_eval_score(
        frozen,
        {"e": {"season": 2022, "week": 2, "home_score": 20, "away_score": 10}},
        exec_bind=rec["bind_id"],
        alex_go_id="ALEX_GO_T5116U",
        one_run_path=path,
        live_effective_spec_sha256="1" * 64,
        live_code_sha256="2" * 64,
        live_input_sha256="3" * 64,
        eligible_cohorts=eligible,
        score_body=lambda *a, **k: {"n": 1, "mae_challenger": 1.0, "mean_signed_diff_vs_if": -1.0},
    )


def test_eval_missing_quote_pin_refuses_before_claim(tmp_path: Path):
    frozen = freeze_forecast_cohort(_payload())
    path = tmp_path / "ONE_RUN.json"
    rec = _bind(path, frozen)
    with pytest.raises(EvalRefuse, match="6a1c1b37"):
        _score(frozen, path, rec, _eligible(quote="0" * 64))
    assert load_one_run(path)["status"] == STATUS_BOUND
    assert not Path(str(path) + f".claim.{rec['bind_id']}").is_file()


def test_eval_unsealed_eligible_refuses_before_claim(tmp_path: Path):
    frozen = freeze_forecast_cohort(_payload())
    path = tmp_path / "ONE_RUN.json"
    rec = _bind(path, frozen)
    with pytest.raises(EvalRefuse, match="sealed before outcome join"):
        _score(frozen, path, rec, _eligible(sealed=False))
    assert load_one_run(path)["status"] == STATUS_BOUND


def test_eval_hold_trip_refuses_before_claim(tmp_path: Path):
    frozen = freeze_forecast_cohort(_payload())
    path = tmp_path / "ONE_RUN.json"
    rec = _bind(path, frozen)
    hold = _hold(trip=True)
    assert hold["any_season_hold"] is True
    with pytest.raises(EvalRefuse, match="HOLD tripped"):
        _score(frozen, path, rec, _eligible(hold=hold))
    assert load_one_run(path)["status"] == STATUS_BOUND


def test_eval_wrong_declared_n_refuses_before_claim(tmp_path: Path):
    frozen = freeze_forecast_cohort(_payload())
    path = tmp_path / "ONE_RUN.json"
    rec = _bind(path, frozen)
    hold = _hold()
    hold["seasons"][0]["declared_n"] = 262
    with pytest.raises(EvalRefuse, match="owned PBP REG"):
        _score(frozen, path, rec, _eligible(hold=hold))
    assert load_one_run(path)["status"] == STATUS_BOUND


def test_eval_id_outside_eval_cohort_refuses_before_claim(tmp_path: Path):
    frozen = freeze_forecast_cohort(_payload())
    path = tmp_path / "ONE_RUN.json"
    rec = _bind(path, frozen)
    with pytest.raises(EvalRefuse, match="not in EVAL metric cohort"):
        _score(frozen, path, rec, _eligible(extra=["2022_99_ZZZ"]))
    assert load_one_run(path)["status"] == STATUS_BOUND


def test_eval_quote_and_hold_gate_opens_without_real_exec(tmp_path: Path):
    frozen = freeze_forecast_cohort(_payload())
    path = tmp_path / "ONE_RUN.json"
    rec = _bind(path, frozen)
    scored = _score(frozen, path, rec, _eligible())
    assert scored["n"] == 1
    assert scored["one_run_status"] == "CONSUMED"
    assert QUOTE_MANIFEST_SHA256.startswith("6a1c1b37")
