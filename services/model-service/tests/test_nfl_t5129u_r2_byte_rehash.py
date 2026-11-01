"""t5129u: R2 file-byte rehash + inherited EVAL result contract (no live EVAL)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.services.nfl_t5107u.eval_result_contract import (
    SCHEMA as CONTRACT_SCHEMA,
    apply_eval_result_contract,
    validate_eval_result_contract,
    EvalResultContractRefuse,
)
from src.services.nfl_t5107u.evaluator import (
    EvalRefuse,
    freeze_forecast_cohort,
    run_paired_margin_eval,
)
from src.services.nfl_t5107u.inputs import QUOTE_MANIFEST_SHA256
from src.services.nfl_t5107u.metric_cohorts import declared_reg_hold_table
from src.services.nfl_t5107u.one_run import STATUS_BOUND, bind_one_run, load_one_run
from src.services.nfl_t5107u.outcome_gate import (
    FIRST_CASE_FILE_SHA256,
    FIRST_CASE_RECORD_SHA256,
    ScoringOutcomeLoader,
)
from src.services.nfl_t5107u.r2_byte_rehash import (
    R2ByteRefuse,
    bind_r2_runtime_bytes,
    r2_hash_set,
    sha256_file_bytes,
    verify_r2_runtime_bytes,
)
from src.services.nfl_t5107u.r2_eval_runner import run_eval_score_r2

ROOT = Path(__file__).resolve().parents[3]
FIRST_CASE = ROOT / "data/ops/nfl-forecast-builder-t5107u/DEV_RESEARCH_t5119u_R2B.json"
DEV437 = ROOT / "data/ops/nfl-forecast-builder-t5107u/DEV_RESEARCH_t5125u_R2B2_437.json"
ONE_RUN_SPENT = ROOT / "data/ops/nfl-forecast-builder-t5107u/ONE_RUN.json"
ONE_EXEC_SPENT = ROOT / "data/ops/nfl-forecast-builder-t5107u/ONE_EXEC_RESULT_t5116u.json"
ONE_EXEC_MD = ROOT / "ops/CURSOR_ONE_EXEC_RESULT_t5116u.md"


def _row(gid: str, season: int, week: int = 2, **extra) -> dict:
    base = {
        "game_id": gid,
        "season": season,
        "week": week,
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
        "forecasts": [_row("d", 2022, 1), _row("e", 2023, 2)],
    }


def _hold():
    excluded = {2020: 16, 2021: 16, 2022: 18, 2023: 16}
    partial = {2020: 30, 2021: 29, 2022: 32, 2023: 28}
    return declared_reg_hold_table(recon_excluded_n=excluded, recon_partial_n=partial)


def _eligible():
    return {
        "sealed_after_eligibility_before_outcome_join": True,
        "quote_manifest_sha256": QUOTE_MANIFEST_SHA256,
        "metric_split": "EVAL",
        "margin_cohort": {"game_ids": ["d", "e"], "n": 2},
        "g5_hold": _hold(),
    }


def _bind(path: Path, frozen, r2=None):
    return bind_one_run(
        effective_spec_sha256="1" * 64,
        code_sha256="2" * 64,
        input_sha256="3" * 64,
        forecast_sha256=frozen.forecast_sha256,
        cohort_sha256=frozen.cohort_sha256,
        alex_go_id="ALEX_GO_T5129U",
        path=path,
        r2_runtime_bytes=None if r2 is None else r2_hash_set(r2),
    )


def _loader():
    return ScoringOutcomeLoader(
        lambda: {
            "d": {"season": 2022, "week": 1, "home_score": 27, "away_score": 20},
            "e": {"season": 2023, "week": 2, "home_score": 10, "away_score": 13},
        }
    )


def _write_manifest(path: Path, extracts: list[Path]) -> None:
    body = {
        "admitted_extracts": [
            {"path": str(p.resolve()), "sha256": sha256_file_bytes(p)} for p in extracts
        ]
    }
    path.write_bytes((json.dumps(body, sort_keys=True) + "\n").encode("utf-8"))


def _pins(tmp_path: Path, *, extra_extract: bool = False):
    freeze = tmp_path / "freeze.json"
    freeze.write_bytes(json.dumps(_eval_payload(), sort_keys=True).encode("utf-8") + b"\n")
    extract_a = tmp_path / "quote_extract_a.jsonl"
    extract_a.write_bytes(b'{"game_id":"d"}\n')
    extracts = [extract_a]
    if extra_extract:
        extract_b = tmp_path / "quote_extract_b.jsonl"
        extract_b.write_bytes(b'{"game_id":"e"}\n')
        extracts.append(extract_b)
    manifest = tmp_path / "quote_manifest.json"
    _write_manifest(manifest, extracts)
    bind_path = tmp_path / "R2_RUNTIME_BYTES.json"
    record = bind_r2_runtime_bytes(
        forecast_file=freeze,
        quote_manifest_file=manifest,
        quote_extract_files=extracts,
        path=bind_path,
    )
    return {
        "forecast_file": freeze,
        "quote_manifest_file": manifest,
        "quote_extract_files": extracts,
        "r2_byte_bind": bind_path,
        "bind_record": record,
    }


def _r2_kwargs(path: Path, rec, loader, pins, *, score_body=None, market_points=None):
    kwargs = dict(
        outcome_loader=loader,
        exec_bind=rec["bind_id"],
        alex_go_id="ALEX_GO_T5129U",
        one_run_path=path,
        live_effective_spec_sha256="1" * 64,
        live_code_sha256="2" * 64,
        live_input_sha256="3" * 64,
        eligible_cohorts=_eligible(),
        forecast_file=pins["forecast_file"],
        quote_manifest_file=pins["quote_manifest_file"],
        quote_extract_files=pins["quote_extract_files"],
        r2_byte_bind=pins["r2_byte_bind"],
    )
    if score_body is not None:
        kwargs["score_body"] = score_body
    if market_points is not None:
        kwargs["market_points"] = market_points
    return kwargs


def _claim_path(path: Path, bind_id: str) -> Path:
    return Path(str(path) + f".claim.{bind_id}")


def test_sha256_file_bytes_is_raw_not_reserialize(tmp_path: Path):
    dest = tmp_path / "freeze.json"
    dest.write_bytes(b'{"b":2,"a":1}\n')
    assert sha256_file_bytes(dest) == hashlib.sha256(b'{"b":2,"a":1}\n').hexdigest()
    dest.write_bytes(b'{"a":1,"b":2}\n')
    assert sha256_file_bytes(dest) == hashlib.sha256(b'{"a":1,"b":2}\n').hexdigest()


def test_bind_refuses_empty_extracts_and_preserved_dests(tmp_path: Path):
    freeze = tmp_path / "freeze.json"
    freeze.write_text("{}\n")
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}\n")
    with pytest.raises(R2ByteRefuse, match="extract files required"):
        bind_r2_runtime_bytes(
            forecast_file=freeze,
            quote_manifest_file=manifest,
            quote_extract_files=[],
            path=tmp_path / "R2_RUNTIME_BYTES.json",
        )
    with pytest.raises(R2ByteRefuse, match="explicit dest"):
        bind_r2_runtime_bytes(
            forecast_file=freeze,
            quote_manifest_file=manifest,
            quote_extract_files=[freeze],
            path=None,
        )
    with pytest.raises(R2ByteRefuse, match="preserved"):
        bind_r2_runtime_bytes(
            forecast_file=freeze,
            quote_manifest_file=manifest,
            quote_extract_files=[freeze],
            path=tmp_path / "ONE_RUN.json",
        )
    with pytest.raises(R2ByteRefuse, match="preserved"):
        bind_r2_runtime_bytes(
            forecast_file=freeze,
            quote_manifest_file=manifest,
            quote_extract_files=[freeze],
            path=ONE_RUN_SPENT,
        )
    with pytest.raises(R2ByteRefuse, match="R2-A|preserved"):
        bind_r2_runtime_bytes(
            forecast_file=freeze,
            quote_manifest_file=manifest,
            quote_extract_files=[freeze],
            path=tmp_path / "R2A_COVERAGE_MANIFEST.json",
        )


@pytest.mark.parametrize(
    "mutate",
    ["freeze", "manifest", "extract"],
)
def test_mutated_file_bytes_refuse_before_claim_and_loader(tmp_path: Path, mutate: str):
    frozen = freeze_forecast_cohort(_eval_payload())
    path = tmp_path / "ONE_RUN.json"
    pins = _pins(tmp_path, extra_extract=True)
    rec = _bind(path, frozen, r2=pins["bind_record"])
    if mutate == "freeze":
        pins["forecast_file"].write_bytes(pins["forecast_file"].read_bytes() + b" ")
        match = "forecast file bytes mutated"
    elif mutate == "manifest":
        pins["quote_manifest_file"].write_bytes(pins["quote_manifest_file"].read_bytes() + b" ")
        match = "manifest file bytes mutated"
    else:
        pins["quote_extract_files"][0].write_bytes(
            pins["quote_extract_files"][0].read_bytes() + b" "
        )
        match = "extract file bytes mutated|manifest-listed extract"
    loader = _loader()
    with pytest.raises(EvalRefuse, match=match):
        run_eval_score_r2(
            frozen,
            None,
            **_r2_kwargs(
                path,
                rec,
                loader,
                pins,
                score_body=lambda *a, **k: {"n": 1},
            ),
        )
    assert loader.call_count == 0
    assert load_one_run(path)["status"] == STATUS_BOUND
    assert not _claim_path(path, rec["bind_id"]).is_file()


def test_in_memory_hash_ok_but_file_mutation_still_refuses(tmp_path: Path):
    payload = _eval_payload()
    frozen = freeze_forecast_cohort(payload)
    rehash = freeze_forecast_cohort(payload)
    assert rehash.forecast_sha256 == frozen.forecast_sha256
    path = tmp_path / "ONE_RUN.json"
    pins = _pins(tmp_path)
    rec = _bind(path, frozen, r2=pins["bind_record"])
    pins["forecast_file"].write_bytes(pins["forecast_file"].read_bytes() + b" ")
    loader = _loader()
    with pytest.raises(EvalRefuse, match="forecast file bytes mutated"):
        run_eval_score_r2(frozen, None, **_r2_kwargs(path, rec, loader, pins))
    assert loader.call_count == 0
    assert load_one_run(path)["status"] == STATUS_BOUND


def test_empty_extracts_refuse_before_claim(tmp_path: Path):
    frozen = freeze_forecast_cohort(_eval_payload())
    path = tmp_path / "ONE_RUN.json"
    pins = _pins(tmp_path)
    rec = _bind(path, frozen, r2=pins["bind_record"])
    loader = _loader()
    with pytest.raises(EvalRefuse, match="extract files required|manifest pin|extract set"):
        run_eval_score_r2(
            frozen,
            None,
            **{
                **_r2_kwargs(path, rec, loader, pins),
                "quote_extract_files": [],
            },
        )
    assert loader.call_count == 0
    assert not _claim_path(path, rec["bind_id"]).is_file()


def test_verify_passes_then_attaches_runtime_bytes(tmp_path: Path):
    frozen = freeze_forecast_cohort(_eval_payload())
    path = tmp_path / "ONE_RUN.json"
    pins = _pins(tmp_path)
    rec = _bind(path, frozen, r2=pins["bind_record"])
    loader = _loader()
    scored = run_eval_score_r2(
        frozen,
        None,
        **_r2_kwargs(
            path,
            rec,
            loader,
            pins,
            score_body=lambda *a, **k: {"n": 1, "mae_challenger": 1.0},
        ),
    )
    assert loader.call_count == 1
    assert scored["r2_runtime_bytes"]["bind_id"] == pins["bind_record"]["bind_id"]
    assert scored["r2_runtime_bytes"]["verified_before_claim"] is True
    assert scored["r2_runtime_bytes"]["manifest_pin_alone"] is False
    assert scored["r2_runtime_bytes"]["in_memory_serialize_only"] is False
    live = verify_r2_runtime_bytes(
        forecast_file=pins["forecast_file"],
        quote_manifest_file=pins["quote_manifest_file"],
        quote_extract_files=pins["quote_extract_files"],
        r2_byte_bind=pins["r2_byte_bind"],
    )
    assert live["forecast_file_sha256"] == sha256_file_bytes(pins["forecast_file"])


def test_if_only_fails_eval_result_contract():
    forecasts = [
        _row("g1", 2020, 1, m_challenger=6.0, m_if=3.0),
        _row("g2", 2020, 2, m_challenger=-2.0, m_if=0.0),
    ]
    outcomes = {
        "g1": {"season": 2020, "week": 1, "home_score": 27, "away_score": 20},
        "g2": {"season": 2020, "week": 2, "home_score": 10, "away_score": 13},
    }
    scored = run_paired_margin_eval(forecasts, outcomes)
    assert "mae_if" in scored
    assert "rmse_if" in scored
    assert "bias_if" in scored
    assert "per_season" in scored
    assert "mae_market" not in scored
    with pytest.raises(EvalResultContractRefuse, match="IF and market|IF-only"):
        validate_eval_result_contract(scored)


def test_if_and_market_passes_eval_result_contract():
    forecasts = [
        _row("g1", 2020, 1, m_challenger=6.0, m_if=3.0),
        _row("g2", 2021, 2, m_challenger=-2.0, m_if=0.0),
    ]
    outcomes = {
        "g1": {"season": 2020, "week": 1, "home_score": 27, "away_score": 20},
        "g2": {"season": 2021, "week": 2, "home_score": 10, "away_score": 13},
    }
    market = [
        {"game_id": "g1", "market_margin": 10.0},
        {"game_id": "g2", "market_margin": 4.0},
    ]
    scored = run_paired_margin_eval(forecasts, outcomes, market_points=market)
    apply_eval_result_contract(scored)
    assert scored["eval_result_contract"] == CONTRACT_SCHEMA
    assert scored["mae_challenger"] == pytest.approx(1.0)
    assert scored["mae_if"] == pytest.approx(3.5)
    assert scored["mae_market"] == pytest.approx(5.0)
    assert scored["rmse_challenger"] == pytest.approx(1.0)
    assert scored["rmse_if"] == pytest.approx(((4.0**2 + 3.0**2) / 2) ** 0.5)
    assert scored["rmse_market"] == pytest.approx(((3.0**2 + 7.0**2) / 2) ** 0.5)
    assert scored["bias_challenger"] == pytest.approx(0.0)
    assert scored["bias_if"] == pytest.approx(-0.5)
    assert scored["bias_market"] == pytest.approx(5.0)
    assert scored["n_by_season"] == {"2020": 1, "2021": 1}
    assert scored["per_season"]["2020"]["mae_market"] == pytest.approx(3.0)
    assert scored["per_season"]["2021"]["mae_market"] == pytest.approx(7.0)
    assert scored["bootstrap_game"]["B"] == 10000
    assert scored["bootstrap_season_week"]["seed"] == 20261101
    assert scored["bootstrap_game_vs_market"]["B"] == 10000
    assert scored["bootstrap_season_week_vs_market"]["seed"] == 20261101
    assert "ci95" in scored["bootstrap_season_week_vs_market"]


def test_r2_real_score_if_only_refuses_before_claim(tmp_path: Path):
    frozen = freeze_forecast_cohort(_eval_payload())
    path = tmp_path / "ONE_RUN.json"
    pins = _pins(tmp_path)
    rec = _bind(path, frozen, r2=pins["bind_record"])
    loader = _loader()
    with pytest.raises(EvalRefuse, match="market incomplete|refuse before claim"):
        run_eval_score_r2(frozen, None, **_r2_kwargs(path, rec, loader, pins))
    assert loader.call_count == 0
    assert load_one_run(path)["status"] == STATUS_BOUND
    assert not _claim_path(path, rec["bind_id"]).is_file()


def test_r2_real_score_if_and_market_emits_contract(tmp_path: Path):
    frozen = freeze_forecast_cohort(_eval_payload())
    path = tmp_path / "ONE_RUN.json"
    pins = _pins(tmp_path)
    rec = _bind(path, frozen, r2=pins["bind_record"])
    loader = _loader()
    market = [
        {"game_id": "d", "market_margin": 10.0},
        {"game_id": "e", "market_margin": 4.0},
    ]
    scored = run_eval_score_r2(
        frozen, None, **_r2_kwargs(path, rec, loader, pins, market_points=market)
    )
    assert loader.call_count == 1
    assert scored["eval_result_contract"] == CONTRACT_SCHEMA
    assert scored["mae_market"] is not None
    assert scored["rmse_market"] is not None
    assert scored["bias_market"] is not None
    assert "bootstrap_season_week_vs_market" in scored
    assert scored["r2_runtime_bytes"]["quote_extract_n"] == 1
    assert scored["one_run_status"] == "CONSUMED"


def test_mutate_and_fresh_rebind_refuses_before_claim(tmp_path: Path):
    frozen = freeze_forecast_cohort(_eval_payload())
    pins = _pins(tmp_path)
    path = tmp_path / "ONE_RUN.json"
    rec = _bind(path, frozen, r2=pins["bind_record"])
    pins["forecast_file"].write_bytes(pins["forecast_file"].read_bytes() + b" ")
    fresh = tmp_path / "R2_RUNTIME_BYTES_FRESH.json"
    bind_r2_runtime_bytes(
        forecast_file=pins["forecast_file"],
        quote_manifest_file=pins["quote_manifest_file"],
        quote_extract_files=pins["quote_extract_files"],
        path=fresh,
    )
    loader = _loader()
    with pytest.raises(EvalRefuse, match="ONE_RUN r2_runtime_bytes mismatch"):
        run_eval_score_r2(
            frozen,
            None,
            **{
                **_r2_kwargs(
                    path,
                    rec,
                    loader,
                    pins,
                    score_body=lambda *a, **k: {"n": 1},
                ),
                "r2_byte_bind": fresh,
            },
        )
    assert loader.call_count == 0
    assert load_one_run(path)["status"] == STATUS_BOUND
    assert not _claim_path(path, rec["bind_id"]).is_file()


def test_unrelated_freeze_file_plus_rebind_refuses(tmp_path: Path):
    frozen = freeze_forecast_cohort(_eval_payload())
    pins = _pins(tmp_path)
    path = tmp_path / "ONE_RUN.json"
    rec = _bind(path, frozen, r2=pins["bind_record"])
    other_payload = {
        "schema_version": "nfl-t5107u-forecast-v1",
        "eval": None,
        "fit_policy": "TRANSFER_FROZEN_DEV_2013_2016",
        "if_arm": {"total": 1, "archived": 0, "reconstructed": 1, "blocked": 0},
        "forecasts": [_row("zz", 2022, 1)],
    }
    other = tmp_path / "other_freeze.json"
    other.write_bytes(json.dumps(other_payload, sort_keys=True).encode("utf-8") + b"\n")
    fresh = tmp_path / "R2_RUNTIME_BYTES_OTHER.json"
    bind_r2_runtime_bytes(
        forecast_file=other,
        quote_manifest_file=pins["quote_manifest_file"],
        quote_extract_files=pins["quote_extract_files"],
        path=fresh,
    )
    loader = _loader()
    with pytest.raises(EvalRefuse, match="do not match frozen.payload"):
        run_eval_score_r2(
            frozen,
            None,
            **{
                **_r2_kwargs(
                    path,
                    rec,
                    loader,
                    pins,
                    score_body=lambda *a, **k: {"n": 1},
                ),
                "forecast_file": other,
                "r2_byte_bind": fresh,
            },
        )
    assert loader.call_count == 0
    assert load_one_run(path)["status"] == STATUS_BOUND
    assert not _claim_path(path, rec["bind_id"]).is_file()


def test_caller_extract_set_must_match_manifest(tmp_path: Path):
    frozen = freeze_forecast_cohort(_eval_payload())
    pins = _pins(tmp_path)
    path = tmp_path / "ONE_RUN.json"
    rec = _bind(path, frozen, r2=pins["bind_record"])
    extra = tmp_path / "not_in_manifest.jsonl"
    extra.write_bytes(b'{"game_id":"extra"}\n')
    loader = _loader()
    with pytest.raises(EvalRefuse, match="extract set"):
        run_eval_score_r2(
            frozen,
            None,
            **{
                **_r2_kwargs(
                    path,
                    rec,
                    loader,
                    pins,
                    score_body=lambda *a, **k: {"n": 1},
                ),
                "quote_extract_files": list(pins["quote_extract_files"]) + [extra],
            },
        )
    assert loader.call_count == 0
    assert not _claim_path(path, rec["bind_id"]).is_file()


def test_market_incomplete_refuses_before_claim(tmp_path: Path):
    frozen = freeze_forecast_cohort(_eval_payload())
    pins = _pins(tmp_path)
    path = tmp_path / "ONE_RUN.json"
    rec = _bind(path, frozen, r2=pins["bind_record"])
    loader = _loader()
    with pytest.raises(EvalRefuse, match="market incomplete"):
        run_eval_score_r2(
            frozen,
            None,
            **_r2_kwargs(
                path,
                rec,
                loader,
                pins,
                market_points=[{"game_id": "d", "market_margin": 10.0}],
            ),
        )
    assert loader.call_count == 0
    assert load_one_run(path)["status"] == STATUS_BOUND
    assert not _claim_path(path, rec["bind_id"]).is_file()


def test_dev437_does_not_complete_eval_contract():
    record = json.loads(DEV437.read_text())
    assert record["n"] == 437
    assert record["market"]["status"] == "NOT_READY"
    with pytest.raises(EvalResultContractRefuse, match="IF and market|IF-only|incomplete"):
        validate_eval_result_contract(record)


def test_preserved_artifacts_untouched():
    assert hashlib.sha256(FIRST_CASE.read_bytes()).hexdigest() == FIRST_CASE_FILE_SHA256
    assert json.loads(FIRST_CASE.read_text())["record_sha256"] == FIRST_CASE_RECORD_SHA256
    assert hashlib.sha256(DEV437.read_bytes()).hexdigest() == (
        "66c3bde18fd6b1a4766f1001403deb68b9f625ccd00372f280f187ef95a54e50"
    )
    assert json.loads(DEV437.read_text())["record_sha256"] == (
        "0550ef9b498a2240919d8cf570ccb7c94b67f6815ba3625789901f8390143637"
    )
    assert hashlib.sha256(ONE_RUN_SPENT.read_bytes()).hexdigest() == (
        "96478f6b91fb12c6c9a0f3941870819cf3d9fa8da4804feecaf9650b7180cc7d"
    )
    assert hashlib.sha256(ONE_EXEC_SPENT.read_bytes()).hexdigest() == (
        "913242590b43dc03f45b88ca970f39db5523e53e67983a65d599fb124adf81f6"
    )
    assert hashlib.sha256(ONE_EXEC_MD.read_bytes()).hexdigest() == (
        "be409f70ba94e48b21ad5e18a78d22f4264c70442538b4c8f2039b9695848df3"
    )
    assert not (ROOT / "data/ops/nfl-forecast-builder-t5107u/OWNED_COVERAGE_t5119u.json").exists()
    assert not (ROOT / "data/ops/nfl-forecast-builder-t5107u/R2A_COVERAGE_MANIFEST.json").exists()


def test_preload_still_refused_before_byte_verify(tmp_path: Path):
    frozen = freeze_forecast_cohort(_eval_payload())
    loader = _loader()
    with pytest.raises(EvalRefuse, match="refuses preloaded scoring outcomes"):
        run_eval_score_r2(
            frozen,
            {"d": {"season": 2020, "week": 1, "home_score": 1, "away_score": 0}},
            outcome_loader=loader,
        )
    assert loader.call_count == 0
