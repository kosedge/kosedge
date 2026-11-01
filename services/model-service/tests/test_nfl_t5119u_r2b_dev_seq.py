"""t5119u R2-B: sequencing (0 target reads on refuse) + DEV numerical E2E."""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from src.services.nfl_t5107u.dev_research import (
    DEV_REG_N,
    DEV_REG_SHA256,
    LABEL,
    NON_REG_WILDCARD_N,
    NON_REG_WILDCARD_SHA256,
    OUTPUT_CONTRACT,
    DevResearchRefuse,
    first_eligible_dev_game,
    fixed_half_half_candidate,
    freeze_dev_metadata_eligibility,
    load_single_game_outcome_from_schedule,
    materialize_pinned_dev_research,
    run_dev_research_e2e,
    validate_dev_research_record,
    write_dev_research_record,
)
from src.services.nfl_t5107u.evaluator import EvalRefuse, FrozenCohort, freeze_forecast_cohort, run_eval_score
from src.services.nfl_t5107u.inputs import QUOTE_MANIFEST_SHA256
from src.services.nfl_t5107u.metric_cohorts import WILDCARD_2020_W18, declared_reg_hold_table
from src.services.nfl_t5107u.one_run import STATUS_BOUND, bind_one_run, claim_one_run, load_one_run
from src.services.nfl_t5107u.outcome_gate import ScoringOutcomeLoader, refuse_preserved_t5116u_path

ROOT = Path(__file__).resolve().parents[3]
FREEZE = ROOT / "data/ops/nfl-forecast-builder-t5107u/FORECAST_FREEZE_t5112u.json"
SCHEDULE = ROOT / "data/ops/nfl-forecast-builder-t5107u/inputs/schedule_results_2020_2023.csv"
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
        alex_go_id="ALEX_GO_T5119U",
        path=path,
    )


def _score_kwargs(path: Path, rec, eligible, loader):
    return dict(
        outcome_loader=loader,
        exec_bind=rec["bind_id"],
        alex_go_id="ALEX_GO_T5119U",
        one_run_path=path,
        live_effective_spec_sha256="1" * 64,
        live_code_sha256="2" * 64,
        live_input_sha256="3" * 64,
        eligible_cohorts=eligible,
        score_body=lambda *a, **k: {"n": 1, "mae_challenger": 1.0, "mean_signed_diff_vs_if": -1.0},
    )


def _loader():
    return ScoringOutcomeLoader(
        lambda: {"e": {"season": 2022, "week": 2, "home_score": 20, "away_score": 10}}
    )


def test_hold_refuse_does_not_call_target_outcome_loader(tmp_path: Path):
    frozen = freeze_forecast_cohort(_eval_payload())
    path = tmp_path / "ONE_RUN.json"
    rec = _bind(path, frozen)
    loader = _loader()
    with pytest.raises(EvalRefuse, match="HOLD tripped"):
        run_eval_score(frozen, **_score_kwargs(path, rec, _eligible(hold=_hold(trip=True)), loader))
    assert loader.call_count == 0
    assert load_one_run(path)["status"] == STATUS_BOUND
    assert not Path(str(path) + f".claim.{rec['bind_id']}").is_file()


def test_hash_mismatch_does_not_call_target_outcome_loader():
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
    with pytest.raises(EvalRefuse, match="hash mismatch"):
        run_eval_score(tampered, outcome_loader=loader, exec_bind="b" * 64)
    assert loader.call_count == 0


def test_claim_refuse_does_not_call_target_outcome_loader(tmp_path: Path):
    frozen = freeze_forecast_cohort(_eval_payload())
    path = tmp_path / "ONE_RUN.json"
    rec = _bind(path, frozen)
    claim_one_run(path, rec["bind_id"])
    loader = _loader()
    with pytest.raises(EvalRefuse, match="claim|IN_PROGRESS|second"):
        run_eval_score(frozen, **_score_kwargs(path, rec, _eligible(), loader))
    assert loader.call_count == 0


def test_success_calls_target_outcome_loader_once_after_claim(tmp_path: Path):
    frozen = freeze_forecast_cohort(_eval_payload())
    path = tmp_path / "ONE_RUN.json"
    rec = _bind(path, frozen)
    loader = _loader()
    scored = run_eval_score(frozen, **_score_kwargs(path, rec, _eligible(), loader))
    assert loader.call_count == 1
    assert scored["one_run_status"] == "CONSUMED"
    assert scored["target_join_phase"] == "AFTER_HOLD_HASH_CLAIM"


def test_both_preload_and_loader_refused_without_loader_call(tmp_path: Path):
    frozen = freeze_forecast_cohort(_eval_payload())
    path = tmp_path / "ONE_RUN.json"
    rec = _bind(path, frozen)
    loader = _loader()
    with pytest.raises(EvalRefuse, match="source READ"):
        run_eval_score(
            frozen,
            {"e": {"season": 2022, "week": 2, "home_score": 1, "away_score": 0}},
            **_score_kwargs(path, rec, _eligible(), loader),
        )
    assert loader.call_count == 0
    assert load_one_run(path)["status"] == STATUS_BOUND


def test_eval_concurrency_loser_does_not_call_loader(tmp_path: Path):
    frozen = freeze_forecast_cohort(_eval_payload())
    path = tmp_path / "ONE_RUN.json"
    rec = _bind(path, frozen)
    in_body = threading.Event()
    release = threading.Event()
    entered: list[int] = []

    def score_body(*_a, **_k):
        entered.append(threading.get_ident())
        in_body.set()
        release.wait(timeout=2)
        return {"n": 1, "mae_challenger": 1.0, "mean_signed_diff_vs_if": -1.0}

    loaders = [_loader(), _loader()]
    results: list[object] = [None, None]

    def worker(idx: int) -> None:
        try:
            kw = _score_kwargs(path, rec, _eligible(), loaders[idx])
            kw["score_body"] = score_body
            results[idx] = run_eval_score(frozen, **kw)
        except Exception as exc:  # noqa: BLE001
            results[idx] = exc

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
    for thread in threads:
        thread.start()
    assert in_body.wait(timeout=2)
    release.set()
    for thread in threads:
        thread.join(timeout=3)
    assert len(entered) == 1
    oks = [r for r in results if isinstance(r, dict)]
    errs = [r for r in results if isinstance(r, Exception)]
    assert len(oks) == 1 and len(errs) == 1
    assert sum(ld.call_count for ld in loaders) == 1
    winner_idx = 0 if isinstance(results[0], dict) else 1
    loser_idx = 1 - winner_idx
    assert loaders[winner_idx].call_count == 1
    assert loaders[loser_idx].call_count == 0


def _dev_forecasts():
    # Pin order: first metadata-complete row is selected; WC is listed first to
    # prove it cannot win; a later complete row must not be selected.
    return [
        _row(
            "2020_18_BAL_TEN",
            2020,
            week=18,
            season_type="POST",
            home="TEN",
            away="BAL",
            kickoff_utc="2021-01-10T21:05:00Z",
        ),
        _row("2020_02_CIN_CLE", 2020),
        _row("2020_02_ATL_DAL", 2020, home="DAL", away="ATL", m_if=1.0, m_q2=1.0, m_challenger=1.0),
    ]


def test_dev_first_eligible_excludes_wildcard_and_is_pin_order():
    forecasts = _dev_forecasts()
    eligibility = freeze_dev_metadata_eligibility(forecasts, require_dev_reg_pin=False)
    assert "2020_18_BAL_TEN" not in eligibility["eligible_game_ids"]
    picked = first_eligible_dev_game(eligibility, forecasts)
    assert picked["game_id"] == "2020_02_CIN_CLE"
    assert picked["game_id"] not in set(WILDCARD_2020_W18)


def test_dev_e2e_hand_checkable_missing_market_and_zero_loader_until_pick():
    forecasts = _dev_forecasts()

    def _load():
        # Loader must not run during freeze/pick; this function is the proof.
        return {
            "2020_02_CIN_CLE": {
                "season": 2020,
                "week": 2,
                "home_score": 35,
                "away_score": 30,
            }
        }

    loader = ScoringOutcomeLoader(_load)
    assert loader.call_count == 0
    eligibility = freeze_dev_metadata_eligibility(forecasts, require_dev_reg_pin=False)
    assert loader.call_count == 0
    first_eligible_dev_game(eligibility, forecasts)
    assert loader.call_count == 0
    record = run_dev_research_e2e(
        forecasts,
        quotes=None,
        outcome_loader=loader,
        require_dev_reg_pin=False,
        synthetic=True,
    )
    assert loader.call_count == 1
    assert record["label"] == LABEL
    assert record["game_id"] == "2020_02_CIN_CLE"
    assert record["one_run_claim"] is False
    assert record["eval"] is None
    assert record["market"]["status"] == "MISSING"
    assert record["market"]["market_margin"] is None
    # 0.5*2 + 0.5*4 = 3; actual 35-30=5; err_c=-2; err_if=-3; L_c=2; L_if=3; d=-1
    assert record["candidate"]["m_challenger"] == pytest.approx(3.0)
    assert record["candidate"]["weight_if"] == 0.5
    assert record["candidate"]["weight_q2"] == 0.5
    assert record["outcome"]["actual_margin"] == pytest.approx(5.0)
    assert record["numerical_error"]["err_challenger"] == pytest.approx(-2.0)
    assert record["numerical_error"]["err_if"] == pytest.approx(-3.0)
    assert record["numerical_error"]["L_challenger"] == pytest.approx(2.0)
    assert record["numerical_error"]["L_if"] == pytest.approx(3.0)
    assert record["numerical_error"]["signed_diff_vs_if"] == pytest.approx(-1.0)
    assert record["numerical_error"]["err_market"] is None
    assert record["numerical_error"]["market_status"] == "MISSING"
    validate_dev_research_record(record)
    for key in OUTPUT_CONTRACT:
        assert key in record


def test_dev_e2e_joined_market_is_hand_checkable():
    forecasts = _dev_forecasts()
    quotes = [
        {
            "event_id": "2020_02_CIN_CLE",
            "season": 2020,
            "game_date": "2020-09-18",
            "home": "Cleveland Browns",
            "away": "Cincinnati Bengals",
            "book": "draftkings",
            "market": "spreads",
            "spread_home": -6.0,
            "price_home": -110,
            "captured_at": "2020-09-17T23:20:00Z",
            "source": "synthetic",
            "provenance": "synthetic",
        }
    ]
    loader = ScoringOutcomeLoader(
        lambda: {"2020_02_CIN_CLE": {"season": 2020, "week": 2, "home_score": 35, "away_score": 30}}
    )
    record = run_dev_research_e2e(
        forecasts,
        quotes=quotes,
        outcome_loader=loader,
        require_dev_reg_pin=False,
        synthetic=True,
    )
    # handicap -6 → home-margin +6; actual +5; err_mkt = 1; L_mkt=1; L_c=2; d_mkt=1
    assert record["market"]["status"] == "JOINED"
    assert record["market"]["market_margin"] == pytest.approx(6.0)
    assert record["numerical_error"]["err_market"] == pytest.approx(1.0)
    assert record["numerical_error"]["L_market"] == pytest.approx(1.0)
    assert record["numerical_error"]["signed_diff_vs_market"] == pytest.approx(1.0)


def test_dev_refuses_weight_search_and_half_half_mismatch():
    forecasts = [_row("2020_02_CIN_CLE", 2020, m_challenger=9.9)]
    loader = ScoringOutcomeLoader(lambda: {})
    with pytest.raises(DevResearchRefuse, match="0.5/0.5"):
        run_dev_research_e2e(
            forecasts, outcome_loader=loader, require_dev_reg_pin=False, synthetic=True
        )
    assert loader.call_count == 0
    from src.services.nfl_t5107u.builder import BuilderRefuse, challenger_margin

    with pytest.raises(BuilderRefuse, match="0.5"):
        challenger_margin(2.0, 4.0, w=0.6)


def test_dev_eligibility_refuse_does_not_call_loader():
    forecasts = [_row("2020_02_CIN_CLE", 2020, kickoff_utc="2020-09-18T00:20:00")]  # naive TZ
    loader = ScoringOutcomeLoader(lambda: {"2020_02_CIN_CLE": {"home_score": 1, "away_score": 0}})
    with pytest.raises(DevResearchRefuse, match="no metadata-eligible"):
        run_dev_research_e2e(
            forecasts, outcome_loader=loader, require_dev_reg_pin=False, synthetic=True
        )
    assert loader.call_count == 0


def test_dev_research_exclusive_write_and_concurrency(tmp_path: Path):
    forecasts = _dev_forecasts()
    dest = tmp_path / "DEV_RESEARCH_t5119u_R2B.json"
    loader = ScoringOutcomeLoader(
        lambda: {"2020_02_CIN_CLE": {"season": 2020, "week": 2, "home_score": 35, "away_score": 30}}
    )
    record = run_dev_research_e2e(
        forecasts,
        outcome_loader=loader,
        require_dev_reg_pin=False,
        synthetic=True,
        dest=dest,
    )
    assert dest.is_file()
    with pytest.raises(DevResearchRefuse, match="exists"):
        write_dev_research_record(record, dest)

    dest2 = tmp_path / "DEV_RESEARCH_concurrent.json"
    results: list[object] = [None, None]
    barrier = threading.Barrier(2)

    def worker(idx: int) -> None:
        barrier.wait(timeout=2)
        try:
            write_dev_research_record(record, dest2)
            results[idx] = "ok"
        except Exception as exc:  # noqa: BLE001
            results[idx] = exc

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=3)
    assert results.count("ok") == 1
    assert sum(1 for r in results if isinstance(r, DevResearchRefuse)) == 1


def test_dev_refuses_overwrite_of_spent_t5116u_artifacts():
    with pytest.raises(Exception, match="preserved t5116u"):
        refuse_preserved_t5116u_path(ONE_RUN_SPENT)
    with pytest.raises(Exception, match="preserved t5116u"):
        refuse_preserved_t5116u_path(ONE_EXEC_SPENT)
    with pytest.raises(Exception, match="preserved t5116u"):
        write_dev_research_record({"label": LABEL}, Path("ONE_RUN.json"))


def test_t5116u_spent_artifacts_untouched():
    assert ONE_RUN_SPENT.is_file()
    assert ONE_EXEC_SPENT.is_file()
    import hashlib

    def sha(p: Path) -> str:
        return hashlib.sha256(p.read_bytes()).hexdigest()

    assert sha(ONE_RUN_SPENT) == "96478f6b91fb12c6c9a0f3941870819cf3d9fa8da4804feecaf9650b7180cc7d"
    assert sha(ONE_EXEC_SPENT) == "913242590b43dc03f45b88ca970f39db5523e53e67983a65d599fb124adf81f6"
    body = json.loads(ONE_RUN_SPENT.read_text())
    assert body["status"] == "FAILED"


def test_real_freeze_pins_and_first_eligible_cin_cle():
    freeze = json.loads(FREEZE.read_text())
    forecasts = freeze["forecasts"]
    eligibility = freeze_dev_metadata_eligibility(forecasts, require_dev_reg_pin=True)
    assert eligibility["dev_reg_n"] == DEV_REG_N
    assert eligibility["dev_reg_sha256"] == DEV_REG_SHA256
    assert eligibility["wildcard_n"] == NON_REG_WILDCARD_N
    assert eligibility["wildcard_sha256"] == NON_REG_WILDCARD_SHA256
    picked = first_eligible_dev_game(eligibility, forecasts)
    assert picked["game_id"] == "2020_02_CIN_CLE"
    cand = fixed_half_half_candidate(picked)
    assert cand["m_challenger"] == pytest.approx(0.5 * cand["m_if"] + 0.5 * cand["m_q2"])
    loaded = load_single_game_outcome_from_schedule("2020_02_CIN_CLE", SCHEDULE)
    assert loaded["2020_02_CIN_CLE"]["home_score"] == "35"
    assert loaded["2020_02_CIN_CLE"]["away_score"] == "30"


def test_materialize_real_dev_research_record(tmp_path: Path):
    dest = tmp_path / "DEV_RESEARCH_t5119u_R2B.json"
    record = materialize_pinned_dev_research(dest=dest, quotes=None)
    assert dest.is_file()
    assert record["game_id"] == "2020_02_CIN_CLE"
    assert record["dev_reg_n"] == 437
    assert record["dev_reg_sha256"] == DEV_REG_SHA256
    assert record["wildcard_excluded"] is True
    assert record["one_run_claim"] is False
    assert record["market"]["status"] == "MISSING"
    assert record["r2a_coverage"]["status"] == "not_ready"
    assert record["outcome"]["actual_margin"] == pytest.approx(5.0)
    # freeze m_if/m_q2/m_c vs actual 5 — hand-checkable
    m_c = record["candidate"]["m_challenger"]
    m_if = record["candidate"]["m_if"]
    assert m_c == pytest.approx(1.5119867482428484)
    assert record["numerical_error"]["err_challenger"] == pytest.approx(m_c - 5.0)
    assert record["numerical_error"]["err_if"] == pytest.approx(m_if - 5.0)
    validate_dev_research_record(record)
    for key in OUTPUT_CONTRACT:
        assert key in record
    # Must not have created a claim next to spent ONE_RUN
    spent_claims = list(ONE_RUN_SPENT.parent.glob("ONE_RUN.json.claim.*"))
    assert spent_claims == []
