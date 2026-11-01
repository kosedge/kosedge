"""t5141u R3-DEV-CALIBRATION — refusal, 1e-9, tie-break, freeze-before-2021."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.services.nfl_t5107u.dev_research import LABEL
from src.services.nfl_t5107u.dev_research_matched72 import (
    MATCHED72_N,
    SEALED_MATCHED72_SHA256,
    load_matched72_ids,
)
from src.services.nfl_t5107u.evaluator import BOOT_B, BOOT_SEED, EvalRefuse, bootstrap_ci
from src.services.nfl_t5107u.outcome_gate import (
    FIRST_CASE_FILE_SHA256,
    FIRST_CASE_GAME_ID,
    FIRST_CASE_RECORD_SHA256,
)
from src.services.nfl_t5107u.r2_market_e2e import (
    SEALED_MANIFEST_SHA256,
    SEALED_QUOTES_SHA256,
    sha256_file,
)
from src.services.nfl_t5107u.r3_dev_calibration import (
    ALEX_PRECOMP_GO_TOKEN,
    BLEND_REPRODUCE_TOL,
    DEFAULT_DEST,
    DEV437_N,
    DEV437_N_2020,
    DEV437_N_2021,
    DEV437_PATH,
    ISOLATED_OPS,
    MATCHED37_N,
    PARENT_OPS,
    SEALED_DEV437_FILE_SHA256,
    SEALED_DEV437_RECORD_SHA256,
    W_GRID,
    CalibRow,
    CalibrationRefuse,
    blend_x,
    break_c3_ties,
    build_pre_fit_freeze_package,
    fit_c2,
    freeze_matched37_ids,
    load_dev437_rows,
    persist_c3_selection,
    predict_arm,
    recover_q2_from_frozen_blend,
    refuse_eval_bind,
    refuse_normalized_94,
    require_alex_precomp_go,
    run_r3_calibration,
    score_arms,
    select_c3,
    validate_r3_record,
    verify_frozen_half_half,
)

ROOT = Path(__file__).resolve().parents[3]
R2A = ROOT / "data/ops/nfl-t5119u-r2-owned-coverage"
FIRST_CASE = PARENT_OPS / "DEV_RESEARCH_t5119u_R2B.json"
MATCHED72_RECORD = PARENT_OPS / "DEV_RESEARCH_t5137u_MATCHED72.json"
PARENT_RECEIPT = PARENT_OPS / "MARKET_E2E_R2B_CONSUME.json"
ONE_RUN = PARENT_OPS / "ONE_RUN.json"
ONE_EXEC = PARENT_OPS / "ONE_EXEC_RESULT_t5116u.json"
ONE_EXEC_MD = ROOT / "ops/CURSOR_ONE_EXEC_RESULT_t5116u.md"


def _row(
    gid: str,
    season: int,
    *,
    week: int = 2,
    actual: float = 3.0,
    m_if: float = 1.0,
    m_q2: float = 5.0,
) -> CalibRow:
    blend = blend_x(0.5, m_if, m_q2)
    return CalibRow(
        game_id=gid,
        season=season,
        week=week,
        actual_margin=actual,
        m_if=m_if,
        m_challenger=blend,
        m_q2=m_q2,
        q2_source="synthetic_known_q2",
    )


def _synth_rows() -> list[CalibRow]:
    train = [
        _row("2020_02_AAA_BBB", 2020, week=2, actual=4.0, m_if=0.0, m_q2=2.0),
        _row("2020_03_CCC_DDD", 2020, week=3, actual=-1.0, m_if=-2.0, m_q2=0.0),
        _row("2020_04_EEE_FFF", 2020, week=4, actual=6.0, m_if=1.0, m_q2=3.0),
        _row("2020_05_GGG_HHH", 2020, week=5, actual=0.0, m_if=2.0, m_q2=-2.0),
    ]
    hold = [
        _row("2021_02_III_JJJ", 2021, week=2, actual=2.0, m_if=1.0, m_q2=5.0),
        _row("2021_03_KKK_LLL", 2021, week=3, actual=-4.0, m_if=-1.0, m_q2=-3.0),
        _row("2021_04_MMM_NNN", 2021, week=4, actual=1.0, m_if=0.0, m_q2=2.0),
    ]
    return train + hold


def test_parent_pins_and_isolated_dir():
    assert sha256_file(DEV437_PATH) == SEALED_DEV437_FILE_SHA256
    record = json.loads(DEV437_PATH.read_text(encoding="utf-8"))
    assert record["record_sha256"] == SEALED_DEV437_RECORD_SHA256
    assert record["n"] == DEV437_N
    assert record["n_by_season"] == {"2020": DEV437_N_2020, "2021": DEV437_N_2021}
    assert record["eval"] is None
    assert record["label"] == LABEL
    assert sha256_file(R2A / "DEV_MATCHED_GAME_IDS.json") == SEALED_MATCHED72_SHA256
    assert sha256_file(R2A / "ADMISSIBLE_QUOTES.jsonl") == SEALED_QUOTES_SHA256
    assert sha256_file(R2A / "COVERAGE_MANIFEST.json") == SEALED_MANIFEST_SHA256
    assert hashlib.sha256(FIRST_CASE.read_bytes()).hexdigest() == FIRST_CASE_FILE_SHA256
    assert json.loads(FIRST_CASE.read_text())["record_sha256"] == FIRST_CASE_RECORD_SHA256
    assert hashlib.sha256(ONE_RUN.read_bytes()).hexdigest() == (
        "96478f6b91fb12c6c9a0f3941870819cf3d9fa8da4804feecaf9650b7180cc7d"
    )
    assert hashlib.sha256(ONE_EXEC.read_bytes()).hexdigest() == (
        "913242590b43dc03f45b88ca970f39db5523e53e67983a65d599fb124adf81f6"
    )
    assert hashlib.sha256(ONE_EXEC_MD.read_bytes()).hexdigest() == (
        "be409f70ba94e48b21ad5e18a78d22f4264c70442538b4c8f2039b9695848df3"
    )
    assert ISOLATED_OPS != PARENT_OPS
    assert DEFAULT_DEST.parent == ISOLATED_OPS
    assert not DEFAULT_DEST.is_file(), "2021 diagnostic record must not exist before Alex GO"


def test_load_dev437_recovers_q2_and_1e9():
    rows, meta = load_dev437_rows()
    assert len(rows) == DEV437_N
    assert meta["n_by_season"] == {"2020": DEV437_N_2020, "2021": DEV437_N_2021}
    assert meta["q2_lineage"]["json_lacks_m_q2"] is True
    assert meta["q2_lineage"]["not_newly_generated_forecast"] is True
    assert meta["outcomes_already_consumed"] is True
    assert meta["q2_lineage"]["max_abs_blend_residual"] <= BLEND_REPRODUCE_TOL
    assert {row.q2_source for row in rows} == {"algebraic_recovery_Q2_eq_2_blend_minus_IF"}
    for row in rows[:5]:
        assert abs(blend_x(0.5, row.m_if, row.m_q2) - row.m_challenger) <= BLEND_REPRODUCE_TOL
        assert abs(recover_q2_from_frozen_blend(row.m_if, row.m_challenger) - row.m_q2) <= BLEND_REPRODUCE_TOL


def test_verify_1e9_refuses_mismatched_identity():
    with pytest.raises(CalibrationRefuse, match="1e-9"):
        verify_frozen_half_half(1.0, 5.0, 9.0)


def test_blend_refuses_extra_hfa_and_nonfinite():
    with pytest.raises(CalibrationRefuse, match="NO separate HFA"):
        blend_x(0.5, 1.0, 2.0, extra_hfa=1.0)
    with pytest.raises(CalibrationRefuse, match="nonfinite"):
        blend_x(0.5, float("nan"), 2.0)
    with pytest.raises(CalibrationRefuse, match="outside"):
        blend_x(1.5, 1.0, 2.0)


def test_load_refuses_missing_and_nonfinite(tmp_path: Path):
    sealed = json.loads(DEV437_PATH.read_text(encoding="utf-8"))
    bad = dict(sealed)
    bad["games"] = [dict(sealed["games"][0])]
    bad["games"][0]["actual_margin"] = None
    dest = tmp_path / "missing.json"
    dest.write_text(json.dumps(bad))
    with pytest.raises(CalibrationRefuse, match="no imputation"):
        load_dev437_rows(dest)

    bad2 = dict(sealed)
    bad2["games"] = [dict(sealed["games"][0])]
    bad2["games"][0]["m_if"] = float("inf")
    dest2 = tmp_path / "inf.json"
    dest2.write_text(json.dumps(bad2))
    with pytest.raises(CalibrationRefuse, match="nonfinite"):
        load_dev437_rows(dest2)


def test_load_refuses_hash_mismatch_on_sealed_path(monkeypatch: pytest.MonkeyPatch):
    def _wrong(_path: Path) -> str:
        return "0" * 64

    monkeypatch.setattr("src.services.nfl_t5107u.r3_dev_calibration.sha256_file", _wrong)
    with pytest.raises(CalibrationRefuse, match="66c3bde1"):
        load_dev437_rows()


def test_matched37_freeze_and_refuse_94():
    ids = load_matched72_ids()
    assert len(ids) == MATCHED72_N
    ids37 = freeze_matched37_ids()
    assert len(ids37) == MATCHED37_N
    assert ids37[0] == "2021_02_NYG_WAS"
    assert ids37[-1] == "2021_18_DAL_PHI"
    assert all(gid.startswith("2021_") for gid in ids37)
    rows, _ = load_dev437_rows()
    hold = {row.game_id for row in rows if row.season == 2021}
    assert set(ids37) <= hold
    with pytest.raises(CalibrationRefuse, match="94-DEV"):
        refuse_normalized_94([f"g{i}" for i in range(94)])


def test_tie_break_prefers_closer_then_smaller_w():
    candidates = [
        {"w": 0.30, "mae_2020": 2.0, "b": 0.0},
        {"w": 0.40, "mae_2020": 1.0, "b": 0.0},
        {"w": 0.60, "mae_2020": 1.0, "b": 0.0},
        {"w": 0.50, "mae_2020": 1.5, "b": 0.0},
    ]
    chosen = break_c3_ties(candidates)
    assert chosen["w"] == 0.40

    equidistant = [
        {"w": 0.40, "mae_2020": 1.0, "b": 1.0},
        {"w": 0.60, "mae_2020": 1.0, "b": 2.0},
    ]
    assert break_c3_ties(equidistant)["w"] == 0.40

    single = [_row("2020_02_AAA_BBB", 2020, actual=7.0, m_if=1.0, m_q2=3.0)]
    selected = select_c3(single)
    assert selected["w"] == 0.5
    assert selected["n_candidates"] == 101
    assert list(selected["grid"]) == list(W_GRID)
    assert abs(selected["mae_2020"]) <= 1e-12


def test_c3_refuses_2021_and_holdout():
    rows = _synth_rows()
    with pytest.raises(CalibrationRefuse, match="2020 only"):
        select_c3([row for row in rows if row.season == 2021])
    with pytest.raises(CalibrationRefuse, match="must not see 2021"):
        select_c3(
            [row for row in rows if row.season == 2020],
            holdout_rows=[row for row in rows if row.season == 2021],
        )
    with pytest.raises(CalibrationRefuse, match="2020 only"):
        fit_c2([row for row in rows if row.season == 2021])


def test_freeze_before_2021_ordering(tmp_path: Path):
    rows = _synth_rows()
    train = [row for row in rows if row.season == 2020]
    hold = [row for row in rows if row.season == 2021]
    seen: list[str] = []

    def _score(target, **kwargs):
        seen.append("2021" if target[0].season == 2021 else "2020")
        if "2021" in seen and not (tmp_path / "C3_SELECTION_FREEZE.json").is_file():
            raise AssertionError("2021 scored before C3 freeze persist")
        return score_arms(target, **kwargs)

    c2 = fit_c2(train)
    c3 = select_c3(train)
    assert c3["frozen_before_2021"] is True
    persist_c3_selection(c3, dest=tmp_path / "C3_SELECTION_FREEZE.json")
    assert (tmp_path / "C3_SELECTION_FREEZE.json").is_file()
    _score(train, c2=c2, c3=c3)
    _score(hold, c2=c2, c3=c3)
    assert seen == ["2020", "2021"]
    with pytest.raises(CalibrationRefuse, match="not frozen"):
        score_arms(hold, c2=c2, c3={**c3, "frozen_before_2021": False})


def test_seed_and_bootstrap_hyperparams_frozen():
    with pytest.raises(EvalRefuse, match="seed"):
        bootstrap_ci([1.0, -1.0], seed=1)
    with pytest.raises(EvalRefuse, match="B"):
        bootstrap_ci([1.0, -1.0], b=10)
    out = bootstrap_ci([0.5, -0.25, 0.0], seed=BOOT_SEED, b=BOOT_B)
    assert out["seed"] == 20261101
    assert out["B"] == 10000
    assert out["n"] == 3
    assert "verdict" in out


def test_diagnostic_refuses_without_go(tmp_path: Path):
    with pytest.raises(CalibrationRefuse, match="awaiting Alex pre-computation GO"):
        require_alex_precomp_go(None)
    with pytest.raises(CalibrationRefuse, match="awaiting Alex pre-computation GO"):
        require_alex_precomp_go("nope")
    with pytest.raises(CalibrationRefuse, match="awaiting Alex pre-computation GO"):
        run_r3_calibration(rows=_synth_rows(), dest=tmp_path / "nope.json", persist_record=False)
    refuse_eval_bind(None)
    with pytest.raises(CalibrationRefuse, match="EVAL bind"):
        refuse_eval_bind({"one_run": True})
    with pytest.raises(CalibrationRefuse, match="EVAL bind"):
        run_r3_calibration(
            go=ALEX_PRECOMP_GO_TOKEN,
            rows=_synth_rows(),
            eval_payload={"bound": True},
            persist_record=False,
        )


def test_refuses_overwrite_parent_artifacts(tmp_path: Path):
    rows = _synth_rows()
    market = {row.game_id: 1.5 for row in rows if row.season == 2021}
    ids = [row.game_id for row in rows if row.season == 2021]
    for dest in (DEV437_PATH, FIRST_CASE, MATCHED72_RECORD, PARENT_RECEIPT, ONE_RUN):
        with pytest.raises(CalibrationRefuse, match="preserved|parent|R2"):
            run_r3_calibration(
                go=ALEX_PRECOMP_GO_TOKEN,
                rows=rows,
                market_by_id=market,
                market_ids=ids,
                dest=dest,
                c3_dest=tmp_path / f"c3-{dest.name}.json",
            )


def test_synthetic_one_run_after_go(tmp_path: Path):
    rows = _synth_rows()
    hold = [row for row in rows if row.season == 2021]
    market = {row.game_id: float(row.actual_margin) + 1.0 for row in hold}
    dest = tmp_path / "DEV_RESEARCH_t5141u_R3_DEV_CALIBRATION.json"
    c3_dest = tmp_path / "C3_SELECTION_FREEZE.json"
    record = run_r3_calibration(
        go=ALEX_PRECOMP_GO_TOKEN,
        rows=rows,
        market_by_id=market,
        market_ids=[row.game_id for row in hold],
        dest=dest,
        c3_dest=c3_dest,
    )
    validate_r3_record(record)
    assert dest.is_file()
    assert c3_dest.is_file()
    assert record["label"] == LABEL
    assert record["eval"] is None
    assert record["winner"] is None
    assert record["selected_from_2021"] is False
    assert record["outcomes_already_consumed"] is True
    assert record["g5_status"] == "DATA_COVERAGE_BLOCKED"
    assert record["diagnostic_2021"]["n"] == 3
    assert record["training_2020"]["n"] == 4
    assert record["c3_selection"]["frozen_before_2021"] is True
    assert set(record["diagnostic_2021"]["comparisons"]) == {
        "C2_vs_C0",
        "C2_vs_C1",
        "C3_vs_C0",
        "C3_vs_C1",
    }
    assert record["diagnostic_2021"]["comparisons"]["C2_vs_C0"]["bootstrap_game"]["seed"] == 20261101
    assert record["diagnostic_2021"]["comparisons"]["C2_vs_C0"]["bootstrap_game"]["B"] == 10000
    assert record["market_n37"]["identity"]["representative_market_validation"] is False
    c0 = predict_arm(hold[0], "C0", c2=record["c2"], c3=record["c3_selection"])
    assert c0 == hold[0].m_if
    with pytest.raises(CalibrationRefuse, match="exists|exclusive"):
        run_r3_calibration(
            go=ALEX_PRECOMP_GO_TOKEN,
            rows=rows,
            market_by_id=market,
            market_ids=[row.game_id for row in hold],
            dest=dest,
            c3_dest=tmp_path / "c3-second.json",
        )


def test_pre_fit_freeze_package_does_not_fit(tmp_path: Path):
    out = tmp_path / "r3-freeze"
    # Isolated synthetic freeze is not used here — sealed inputs, isolated dest.
    manifest = build_pre_fit_freeze_package(out)
    assert manifest["frozen_before_fit"] is True
    assert manifest["c2_c3_fitted"] is False
    assert manifest["diagnostic_executed"] is False
    assert manifest["status"] == "STOP_AWAITING_ALEX_PRECOMP_GO"
    assert manifest["g5_status"] == "DATA_COVERAGE_BLOCKED"
    stop = json.loads((out / "STOP_AWAITING_ALEX_PRECOMP_GO.json").read_text())
    assert stop["c2_c3_fitted"] is False
    assert stop["diagnostic_executed"] is False
    identity = json.loads((out / "IDENTITY_FREEZE.json").read_text())
    assert identity["matched72_intersect_2021_n"] == MATCHED37_N
    assert identity["frozen_before_fit"] is True
    market = json.loads((out / "MARKET_N37_IDENTITY.json").read_text())
    assert market["n"] == MATCHED37_N
    assert market["frozen_before_fit"] is True
    assert len(market["points"]) == MATCHED37_N
    assert not (out / "DEV_RESEARCH_t5141u_R3_DEV_CALIBRATION.json").is_file()
    assert not (out / "C3_SELECTION_FREEZE.json").is_file()
    with pytest.raises(CalibrationRefuse, match="exists|exclusive"):
        build_pre_fit_freeze_package(out)


def test_freeze_refuses_parent_ops_directory():
    with pytest.raises(CalibrationRefuse, match="isolated"):
        build_pre_fit_freeze_package(PARENT_OPS)


def test_w_grid_is_101_inclusive():
    assert W_GRID[0] == 0.0
    assert W_GRID[-1] == 1.0
    assert 0.5 in W_GRID
    assert len(W_GRID) == 101
    assert len(set(W_GRID)) == 101


def test_repo_freeze_package_is_pre_fit_and_stopped():
    manifest_path = ISOLATED_OPS / "FREEZE_MANIFEST.json"
    assert manifest_path.is_file(), "isolated pre-fit freeze package must be tipped"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["c2_c3_fitted"] is False
    assert manifest["diagnostic_executed"] is False
    assert manifest["status"] == "STOP_AWAITING_ALEX_PRECOMP_GO"
    assert manifest["eval"] is None
    assert manifest["g5_status"] == "DATA_COVERAGE_BLOCKED"
    assert not (ISOLATED_OPS / "DEV_RESEARCH_t5141u_R3_DEV_CALIBRATION.json").is_file()
    assert not (ISOLATED_OPS / "C3_SELECTION_FREEZE.json").is_file()
    pins = json.loads((ISOLATED_OPS / "INPUT_PINS.json").read_text(encoding="utf-8"))
    assert pins["dev437_file_sha256"] == SEALED_DEV437_FILE_SHA256
    assert pins["dev437_record_sha256"] == SEALED_DEV437_RECORD_SHA256
    assert pins["matched72_sha256"] == SEALED_MATCHED72_SHA256
    assert pins["admissible_quotes_sha256"] == SEALED_QUOTES_SHA256
    assert pins["coverage_manifest_sha256"] == SEALED_MANIFEST_SHA256
    assert pins["code_sha256"] == sha256_file(
        Path(__file__).resolve().parents[1]
        / "src/services/nfl_t5107u/r3_dev_calibration.py"
    )
    identity = json.loads((ISOLATED_OPS / "IDENTITY_FREEZE.json").read_text(encoding="utf-8"))
    assert identity["frozen_before_fit"] is True
    assert identity["dev437_n"] == DEV437_N
    assert identity["season_2020_n"] == DEV437_N_2020
    assert identity["season_2021_n"] == DEV437_N_2021
    assert identity["matched72_intersect_2021_n"] == MATCHED37_N
    assert identity["outcomes_already_consumed"] is True
    lineage = json.loads((ISOLATED_OPS / "Q2_LINEAGE.json").read_text(encoding="utf-8"))
    assert lineage["json_lacks_m_q2"] is True
    assert lineage["not_newly_generated_forecast"] is True
    assert lineage["max_abs_blend_residual"] == 0.0
    stop = json.loads((ISOLATED_OPS / "STOP_AWAITING_ALEX_PRECOMP_GO.json").read_text())
    assert stop["diagnostic_executed"] is False
    assert stop["c2_c3_fitted"] is False
