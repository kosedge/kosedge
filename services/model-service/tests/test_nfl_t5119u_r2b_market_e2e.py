"""t5119u R2-B market E2E consume — no EVAL, no R2-A rewrite."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.services.nfl_t5107u.outcome_gate import (
    FIRST_CASE_FILE_SHA256,
    FIRST_CASE_GAME_ID,
    FIRST_CASE_RECORD_SHA256,
    ScoringOutcomeLoader,
)
from src.services.nfl_t5107u.r2_market_e2e import (
    SEALED_CONSUME_SHA256,
    SEALED_MANIFEST_SHA256,
    SEALED_QUOTES_SHA256,
    MarketE2ERefuse,
    join_market_points,
    load_eligible_ids,
    load_r2b_consume,
    load_sealed_quotes,
    run_market_e2e,
    sha256_file,
)

ROOT = Path(__file__).resolve().parents[3]
R2A = ROOT / "data/ops/nfl-t5119u-r2-owned-coverage"
FIRST_CASE = ROOT / "data/ops/nfl-forecast-builder-t5107u/DEV_RESEARCH_t5119u_R2B.json"
DEV437 = ROOT / "data/ops/nfl-forecast-builder-t5107u/DEV_RESEARCH_t5125u_R2B2_437.json"
ONE_RUN = ROOT / "data/ops/nfl-forecast-builder-t5107u/ONE_RUN.json"
ONE_EXEC = ROOT / "data/ops/nfl-forecast-builder-t5107u/ONE_EXEC_RESULT_t5116u.json"
ONE_EXEC_MD = ROOT / "ops/CURSOR_ONE_EXEC_RESULT_t5116u.md"


def _loader(ids):
    return ScoringOutcomeLoader(
        lambda: {gid: {"season": 2022, "week": 2, "home_score": 20, "away_score": 10} for gid in ids}
    )


def test_consume_pins_match_694_tip():
    consume = load_r2b_consume()
    assert consume["market_e2e"] == "READY_FOR_R2B_DEV_E2E"
    assert sha256_file(R2A / "R2B_CONSUME.json") == SEALED_CONSUME_SHA256
    assert sha256_file(R2A / "ADMISSIBLE_QUOTES.jsonl") == SEALED_QUOTES_SHA256
    assert sha256_file(R2A / "COVERAGE_MANIFEST.json") == SEALED_MANIFEST_SHA256
    quotes = load_sealed_quotes()
    assert len(quotes) == 1475


def test_eval_449_not_bind_ready_and_no_eval():
    record = run_market_e2e(split="eval", emit_metrics=False)
    assert record["eval"] is None
    assert record["eval_invoked"] is False
    assert record["r2_eval_called"] is False
    assert record["one_run_claim"] is False
    assert record["eligible_n"] == 449
    assert record["joined_n"] == 95
    assert record["missing_n"] == 354
    assert record["bind_ready"] is False
    assert "incomplete" in record["bind_ready_reason"]


def test_dev_437_join_and_first_case_has_market():
    record = run_market_e2e(split="dev_reg", emit_metrics=False)
    assert record["eligible_n"] == 437
    assert record["joined_n"] == 72
    assert record["missing_n"] == 365
    assert record["bind_ready"] is False
    first = next(p for p in record["market_points"] if p["game_id"] == FIRST_CASE_GAME_ID)
    assert first["market_margin"] is not None
    assert first["book_count"] >= 1
    assert set(first["books_used"]) <= {"draftkings", "fanduel"}


def test_matched_subset_is_bind_ready():
    matched = json.loads((R2A / "DEV_MATCHED_GAME_IDS.json").read_text())
    record = run_market_e2e(eligible_ids=matched, emit_metrics=False)
    assert record["eligible_n"] == 72
    assert record["joined_n"] == 72
    assert record["missing_n"] == 0
    assert record["bind_ready"] is True


def test_preload_refused_loader_zero():
    loader = _loader(["2020_02_CIN_CLE"])
    with pytest.raises(MarketE2ERefuse, match="preloaded"):
        run_market_e2e(
            eligible_ids=["2020_02_CIN_CLE"],
            outcomes={"2020_02_CIN_CLE": {"home_score": 1, "away_score": 0}},
            outcome_loader=loader,
        )
    assert loader.call_count == 0


def test_conflict_fingerprint_fail_closed():
    quotes = [
        {
            "game_id": "g1",
            "book": "draftkings",
            "market": "spread",
            "spread_home": -3.0,
            "captured_at": "2020-01-01T00:00:00Z",
            "age_hours": 1.0,
            "season": 2020,
            "week": 2,
        }
    ]
    conflicts = [
        {
            "game_id": "g1",
            "book": "draftkings",
            "market": "spread",
            "captured_at": "2020-01-01T00:00:00Z",
        }
    ]
    with pytest.raises(MarketE2ERefuse, match="conflict"):
        join_market_points(["g1"], quotes, conflicts=conflicts)


def test_missing_consume_refuses(tmp_path: Path):
    with pytest.raises(MarketE2ERefuse, match="R2B_CONSUME missing"):
        load_r2b_consume(tmp_path / "nope.json")


def test_refuses_r2a_dest(tmp_path: Path):
    with pytest.raises(MarketE2ERefuse, match="R2-A|preserved"):
        run_market_e2e(
            eligible_ids=["2020_02_CIN_CLE"],
            emit_metrics=False,
            dest=R2A / "R2B_CONSUME.json",
        )


def test_loader_after_join_emits_market_contract_fields():
    matched = json.loads((R2A / "DEV_MATCHED_GAME_IDS.json").read_text())[:2]
    loader = ScoringOutcomeLoader(
        lambda: {
            gid: {
                "season": 2020,
                "week": 2,
                "home_score": 21,
                "away_score": 17,
            }
            for gid in matched
        }
    )
    record = run_market_e2e(
        eligible_ids=matched,
        outcome_loader=loader,
        emit_metrics=True,
    )
    assert loader.call_count == 1
    assert record["bind_ready"] is True
    assert record["eval_invoked"] is False
    fields = record["market_contract"]
    assert fields["mae_market"] is not None
    assert fields["rmse_market"] is not None
    assert fields["bias_market"] is not None
    assert fields["bootstrap_game_vs_market"]["B"] == 10000
    assert fields["bootstrap_season_week_vs_market"]["seed"] == 20261101
    assert record["target_join_phase"] == "AFTER_MARKET_JOIN"


def test_eval_incomplete_contract_not_complete():
    record = run_market_e2e(split="eval", emit_metrics=False)
    assert record["market_contract"]["eval_result_contract_complete"] is False
    assert record["bind_ready"] is False


def test_preserved_and_r2a_not_rewritten():
    assert hashlib.sha256(FIRST_CASE.read_bytes()).hexdigest() == FIRST_CASE_FILE_SHA256
    assert json.loads(FIRST_CASE.read_text())["record_sha256"] == FIRST_CASE_RECORD_SHA256
    assert hashlib.sha256(DEV437.read_bytes()).hexdigest() == (
        "66c3bde18fd6b1a4766f1001403deb68b9f625ccd00372f280f187ef95a54e50"
    )
    assert hashlib.sha256(ONE_RUN.read_bytes()).hexdigest() == (
        "96478f6b91fb12c6c9a0f3941870819cf3d9fa8da4804feecaf9650b7180cc7d"
    )
    assert hashlib.sha256(ONE_EXEC.read_bytes()).hexdigest() == (
        "913242590b43dc03f45b88ca970f39db5523e53e67983a65d599fb124adf81f6"
    )
    assert hashlib.sha256(ONE_EXEC_MD.read_bytes()).hexdigest() == (
        "be409f70ba94e48b21ad5e18a78d22f4264c70442538b4c8f2039b9695848df3"
    )
    assert sha256_file(R2A / "ADMISSIBLE_QUOTES.jsonl") == SEALED_QUOTES_SHA256
    assert sha256_file(R2A / "COVERAGE_MANIFEST.json") == SEALED_MANIFEST_SHA256
    assert sha256_file(R2A / "R2B_CONSUME.json") == SEALED_CONSUME_SHA256


def test_eligible_ids_pins():
    assert len(load_eligible_ids("eval")) == 449
    assert len(load_eligible_ids("dev_reg")) == 437
