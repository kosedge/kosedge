"""t5115u: EVAL-only metric cohort + 2020 identity pin. No scoring."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.services.nfl_t5107u.evaluator import EvalRefuse, freeze_forecast_cohort, run_eval_score
from src.services.nfl_t5107u.metric_cohorts import (
    DECLARED_REG_UNIVERSE,
    WILDCARD_2020_W18,
    declared_reg_hold_table,
    pin_metric_cohorts,
    refuse_pooled_or_default_eval,
)
from src.services.nfl_t5107u.one_run import STATUS_BOUND, bind_one_run, load_one_run

ROOT = Path(__file__).resolve().parents[3]
FREEZE = ROOT / "data/ops/nfl-forecast-builder-t5107u/FORECAST_FREEZE_t5112u.json"


def _row(gid: str, season: int) -> dict:
    return {
        "game_id": gid,
        "season": season,
        "week": 2,
        "m_challenger": 3.0,
        "m_if": 2.0,
    }


def test_pin_metric_cohorts_splits_eval_and_dev():
    forecasts = [
        _row("2020_02_A", 2020),
        _row("2021_02_B", 2021),
        _row("2022_02_C", 2022),
        _row("2023_02_D", 2023),
        _row("2020_18_BAL_TEN", 2020),
    ]
    pins = pin_metric_cohorts(forecasts)
    assert pins["full_freeze_is_eval_accuracy_cohort"] is False
    assert pins["eval"]["n"] == 2
    assert pins["eval"]["game_ids"] == ["2022_02_C", "2023_02_D"]
    assert pins["eval"]["pooled_dev"] is False
    assert pins["dev"]["n"] == 3
    assert pins["dev"]["wildcard_2020_w18_game_ids"] == ["2020_18_BAL_TEN"]
    assert pins["dev"]["not_pooled_into_eval"] is True


def test_refuse_default_to_full_mixed_freeze():
    forecasts = [_row("d", 2020), _row("e", 2022)]
    with pytest.raises(Exception, match="full freeze"):
        refuse_pooled_or_default_eval(forecasts, None)


def test_refuse_pooled_eligible_ids():
    forecasts = [_row("d", 2020), _row("e", 2022)]
    with pytest.raises(Exception, match="pooled DEV\\+EVAL"):
        refuse_pooled_or_default_eval(
            forecasts,
            {"margin_cohort": {"game_ids": ["d", "e"]}},
        )


def test_eval_only_eligible_ok():
    forecasts = [_row("d", 2020), _row("e", 2022)]
    refuse_pooled_or_default_eval(
        forecasts,
        {"metric_split": "EVAL", "game_ids": ["e"], "margin_cohort": {"game_ids": ["e"]}},
    )


def test_mixed_freeze_refuses_before_claim(tmp_path: Path):
    payload = {
        "schema_version": "nfl-t5107u-forecast-v1",
        "eval": None,
        "fit_policy": "TRANSFER_FROZEN_DEV_2013_2016",
        "if_arm": {"total": 2, "archived": 0, "reconstructed": 2, "blocked": 0},
        "forecasts": [_row("d", 2020), _row("e", 2022)],
    }
    frozen = freeze_forecast_cohort(payload)
    path = tmp_path / "ONE_RUN.json"
    rec = bind_one_run(
        effective_spec_sha256="1" * 64,
        code_sha256="2" * 64,
        input_sha256="3" * 64,
        forecast_sha256=frozen.forecast_sha256,
        cohort_sha256=frozen.cohort_sha256,
        alex_go_id="ALEX_GO_T5115U",
        path=path,
    )
    with pytest.raises(EvalRefuse, match="full freeze|pooled"):
        run_eval_score(
            frozen,
            {"e": {"season": 2022, "week": 2, "home_score": 20, "away_score": 10}},
            exec_bind=rec["bind_id"],
            alex_go_id="ALEX_GO_T5115U",
            one_run_path=path,
            live_effective_spec_sha256="1" * 64,
            live_code_sha256="2" * 64,
            live_input_sha256="3" * 64,
        )
    assert load_one_run(path)["status"] == STATUS_BOUND
    assert not Path(str(path) + f".claim.{rec['bind_id']}").is_file()


def test_live_freeze_eval_pin_and_2020_wildcard():
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    pins = pin_metric_cohorts(freeze["forecasts"])
    assert pins["full_freeze_n"] == 892
    assert pins["eval"]["n"] == 449
    assert pins["eval"]["n_by_season"] == {2022: 221, 2023: 228}
    assert pins["eval"]["cohort_sha256"] == (
        "fac21ebed92b6ef91e27095026751f088440dbd81e47ca368d256c580b58d7f0"
    )
    assert pins["dev"]["n"] == 443
    assert pins["dev"]["n_by_season"] == {2020: 216, 2021: 227}
    assert pins["dev"]["cohort_sha256"] == (
        "f240fde23025d7584a5f8031ec1e0e74f902be1100ce1630aca4f2f20ed326b0"
    )
    assert set(pins["dev"]["wildcard_2020_w18_game_ids"]) == set(WILDCARD_2020_W18)
    assert freeze["cohort_sha256"] == (
        "af129383acdad81316897cea6a1d5b48ca51647b3fc51092b55b29ca284908bc"
    )


def test_declared_reg_hold_uses_pbp_256_not_pin_262():
    table = declared_reg_hold_table(
        recon_excluded_n={2020: 16, 2021: 16, 2022: 18, 2023: 16},
        recon_partial_n={2020: 30, 2021: 29, 2022: 32, 2023: 28},
    )
    by = {row["season"]: row for row in table["seasons"]}
    assert by[2020]["declared_n"] == DECLARED_REG_UNIVERSE[2020] == 256
    assert by[2020]["pin_week_1_18"] == 262
    assert by[2020]["pin_minus_declared"] == 6
    assert by[2020]["excluded_n"] == 46
    assert by[2020]["hold"] is False
    assert table["any_season_hold"] is False
    assert table["quote_eligibility"] == "REQUIRED_BEFORE_METRICS_NOT_APPLIED_t5115u"
