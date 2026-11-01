"""t5113u: exclusive one-run claim before any outcome join."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from src.services.nfl_t5107u.evaluator import EvalRefuse, freeze_forecast_cohort, run_eval_score
from src.services.nfl_t5107u.one_run import (
    STATUS_FAILED,
    STATUS_IN_PROGRESS,
    OneRunRefuse,
    bind_one_run,
    claim_path_for,
    load_one_run,
    result_path_for,
)


def _frozen():
    payload = {
        "schema_version": "nfl-t5107u-forecast-v1",
        "eval": None,
        "fit_policy": {"fit_policy": "TRANSFER"},
        "if_arm": {"total": 1, "archived": 1, "reconstructed": 0, "blocked": 0},
        "forecasts": [
            {"game_id": "g1", "season": 2020, "week": 1, "m_challenger": 6.0, "m_if": 3.0},
        ],
    }
    return freeze_forecast_cohort(payload)


def _bind(path: Path, frozen) -> dict:
    return bind_one_run(
        effective_spec_sha256="1" * 64,
        code_sha256="2" * 64,
        input_sha256="3" * 64,
        forecast_sha256=frozen.forecast_sha256,
        cohort_sha256=frozen.cohort_sha256,
        alex_go_id="ALEX_GO_ATOMIC",
        path=path,
    )


def _kwargs(rec, path: Path) -> dict:
    return {
        "exec_bind": rec["bind_id"],
        "alex_go_id": "ALEX_GO_ATOMIC",
        "one_run_path": path,
        "live_effective_spec_sha256": "1" * 64,
        "live_code_sha256": "2" * 64,
        "live_input_sha256": "3" * 64,
    }


def test_concurrent_contenders_only_one_reaches_scoring_body(tmp_path: Path):
    frozen = _frozen()
    outcomes = {"g1": {"season": 2020, "week": 1, "home_score": 27, "away_score": 20}}
    path = tmp_path / "ONE_RUN.json"
    rec = _bind(path, frozen)
    entered: list[int] = []
    in_body = threading.Event()
    release = threading.Event()

    def score_body(*_args, **_kwargs):
        entered.append(threading.get_ident())
        in_body.set()
        release.wait(timeout=2)
        return {
            "n": 1,
            "mae_challenger": 1.0,
            "mean_signed_diff_vs_if": -3.0,
        }

    results: list[object] = [None, None]

    def worker(idx: int) -> None:
        try:
            results[idx] = run_eval_score(
                frozen, outcomes, score_body=score_body, **_kwargs(rec, path)
            )
        except Exception as exc:  # noqa: BLE001 — capture refuse vs score
            results[idx] = exc

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
    for thread in threads:
        thread.start()
    assert in_body.wait(timeout=2)
    # Winner is inside score_body (claimed). Loser must refuse without entering.
    release.set()
    for thread in threads:
        thread.join(timeout=3)
    assert len(entered) == 1
    oks = [r for r in results if isinstance(r, dict)]
    errs = [r for r in results if isinstance(r, Exception)]
    assert len(oks) == 1
    assert len(errs) == 1
    assert oks[0]["one_run_status"] == "CONSUMED"
    assert isinstance(errs[0], EvalRefuse)
    assert "claim" in str(errs[0]).lower() or "second" in str(errs[0]).lower() or "IN_PROGRESS" in str(errs[0]) or "CONSUMED" in str(errs[0])
    record = load_one_run(path)
    assert record["status"] == "CONSUMED"
    assert result_path_for(path, rec["bind_id"]).is_file()


def test_injected_failure_after_claim_refuses_automatic_rerun(tmp_path: Path):
    frozen = _frozen()
    outcomes = {"g1": {"season": 2020, "week": 1, "home_score": 27, "away_score": 20}}
    path = tmp_path / "ONE_RUN.json"
    rec = _bind(path, frozen)
    entered: list[str] = []

    def boom(*_args, **_kwargs):
        entered.append("scoring_body")
        raise RuntimeError("injected failure after exclusive claim")

    with pytest.raises(EvalRefuse, match="claimed then failed|injected failure"):
        run_eval_score(frozen, outcomes, score_body=boom, **_kwargs(rec, path))
    assert entered == ["scoring_body"]
    record = load_one_run(path)
    assert record["status"] in {STATUS_FAILED, STATUS_IN_PROGRESS}
    assert claim_path_for(path, rec["bind_id"]).is_file()
    assert not result_path_for(path, rec["bind_id"]).is_file()
    with pytest.raises(EvalRefuse, match="FAILED|IN_PROGRESS|claim|second"):
        run_eval_score(frozen, outcomes, **_kwargs(rec, path))
    assert load_one_run(path)["status"] == STATUS_FAILED


def test_claim_file_is_exclusive_for_bind_id(tmp_path: Path):
    frozen = _frozen()
    path = tmp_path / "ONE_RUN.json"
    rec = _bind(path, frozen)
    from src.services.nfl_t5107u.one_run import claim_one_run

    first = claim_one_run(path, rec["bind_id"])
    assert first["status"] == STATUS_IN_PROGRESS
    with pytest.raises(OneRunRefuse, match="exclusive claim|already"):
        claim_one_run(path, rec["bind_id"])
