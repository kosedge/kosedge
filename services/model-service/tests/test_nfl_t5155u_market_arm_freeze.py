"""t5155u market-arm freeze — metadata only, before scoring."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.services.nfl_t5107u.cohort_enforcement import (
    FEATURE_RECON_REG496_ARTIFACT_SHA256,
    PROFILE_FEATURE_RECON_REG496,
    REG496_IDENTITY_SHA256,
    CohortEnforcementRefuse,
    OutcomeReadSpy,
    expected_profile_ids,
)
from src.services.nfl_t5107u.evaluator import PER_SEASON_EXCLUSION_HOLD
from src.services.nfl_t5107u.market_arm_freeze import (
    B1_UNIVERSE_PATH,
    B1_UNIVERSE_SHA256,
    INTERSECTION_BYTES_SHA256,
    INTERSECTION_IDENTITY_SHA256,
    INTERSECTION_N,
    REG496_ONLY_EXTRAS_VS_DEV437,
    MarketArmFreezeRefuse,
    assert_b1_universe_bytes,
    build_market_arm_freeze,
    intersection_bytes_sha256,
    run_market_arm_freeze,
    write_market_arm_freeze,
)
from src.services.nfl_t5107u.metric_cohorts import DECLARED_REG_UNIVERSE, WILDCARD_2020_W18
from src.services.nfl_t5107u.recon_driver import sha256_file

ROOT = Path(__file__).resolve().parents[3]


def test_b1_universe_pin():
    digest = assert_b1_universe_bytes(ROOT)
    assert digest == B1_UNIVERSE_SHA256
    assert sha256_file(ROOT / B1_UNIVERSE_PATH) == "b4a3a4dbb8c5404d095b8095ec4018b96ceae532a50600d6d7f29f9d8fe950e6"


def test_intersection_is_reg496_dev_only_no_eval_seasons():
    payload = build_market_arm_freeze(root=ROOT)
    inter = payload["intersection"]
    reg_ids = set(expected_profile_ids(PROFILE_FEATURE_RECON_REG496, ROOT))
    assert payload["reg496"]["identity_sha256"] == REG496_IDENTITY_SHA256
    assert set(inter["game_ids"]) <= reg_ids
    assert inter["n"] == INTERSECTION_N == 96
    assert inter["n"] != 94
    assert inter["n"] == len(inter["game_ids"])
    assert inter["n"] + inter["missing_n"] == 496
    assert set(REG496_ONLY_EXTRAS_VS_DEV437) <= set(inter["game_ids"])
    assert inter["bytes_sha256"] == INTERSECTION_BYTES_SHA256
    assert inter["identity_sha256"] == INTERSECTION_IDENTITY_SHA256
    assert not any(gid.startswith("2022_") or gid.startswith("2023_") for gid in inter["game_ids"])
    assert not set(inter["game_ids"]) & set(WILDCARD_2020_W18)
    assert not any(int(gid.split("_")[1]) < 2 for gid in inter["game_ids"])
    assert payload["scoring"] is None
    assert payload["eval"] is None
    assert "ml" not in payload
    assert "brier" not in payload
    assert "log_loss" not in payload
    assert payload["odds_pulls"] is False
    assert payload["outcome_based_selection"] is False
    assert payload["selection_limited"] == "DEV_2020_2021_REG496"


def test_home_margin_is_negation_of_median_spread():
    payload = build_market_arm_freeze(root=ROOT)
    for row in payload["intersection"]["games"]:
        assert row["home_margin"] == pytest.approx(-float(row["spread_home_median"]))
        assert row["book_count"] >= 1
        assert set(row["books_used"]) <= {"draftkings", "fanduel"}


def test_one_book_and_missing_counts_disclosed():
    payload = build_market_arm_freeze(root=ROOT)
    inter = payload["intersection"]
    assert inter["one_book_n"] + inter["two_book_n"] == inter["n"]
    assert inter["missing_n_by_season"]["2020"] + inter["n_by_season"].get("2020", 0) == 240
    assert inter["missing_n_by_season"]["2021"] + inter["n_by_season"].get("2021", 0) == 256
    hold = payload["r2c_hold"]
    assert hold["hold_threshold"] == PER_SEASON_EXCLUSION_HOLD == 0.30
    assert hold["threshold_unchanged"] is True
    assert hold["loosened"] is False
    assert hold["declared_pbp_reg"]["2020"] == DECLARED_REG_UNIVERSE[2020] == 256
    assert hold["declared_pbp_reg"]["2021"] == DECLARED_REG_UNIVERSE[2021] == 272


def test_intersection_bytes_deterministic():
    one = build_market_arm_freeze(root=ROOT)
    two = build_market_arm_freeze(root=ROOT)
    assert one["intersection"]["bytes_sha256"] == two["intersection"]["bytes_sha256"]
    assert one["intersection"]["identity_sha256"] == two["intersection"]["identity_sha256"]
    assert one["intersection"]["bytes_sha256"] == intersection_bytes_sha256(one["intersection"]["games"])


def test_refusal_reads_zero_target_scoring_labels():
    spy = OutcomeReadSpy(lambda: {"2020_02_CIN_CLE": {"home_score": 24, "away_score": 21}})
    with pytest.raises(CohortEnforcementRefuse, match="blocked coverage"):
        run_market_arm_freeze(root=ROOT, outcome_loader=spy, coverage_blocked=True)
    assert spy.reads == 0
    assert spy.ids_returned == []


def test_b1_byte_change_refuses_before_loader(tmp_path):
    spy = OutcomeReadSpy(lambda: {"2020_02_CIN_CLE": {"home_score": 99}})
    dest = tmp_path / "ADMISSIBLE_QUOTES_B1.jsonl"
    dest.write_text('{"game_id":"x"}\n', encoding="utf-8")
    # Pin check uses repo path, not dest — mutate via outcome-bearing quotes.
    bad = [
        {
            "game_id": "2020_02_CIN_CLE",
            "season": 2020,
            "week": 2,
            "book": "draftkings",
            "market": "spread",
            "spread_home": -3.5,
            "captured_at": "2020-09-17T16:00:00Z",
            "kickoff_utc": "2020-09-17T20:20:00Z",
            "home_score": 27,
            "away_score": 13,
        }
    ]
    with pytest.raises(MarketArmFreezeRefuse, match="scoring/outcome"):
        build_market_arm_freeze(root=ROOT, quotes=bad)
    assert spy.reads == 0


def test_late_quote_not_selected():
    late = [
        {
            "game_id": "2020_02_CIN_CLE",
            "season": 2020,
            "week": 2,
            "book": "draftkings",
            "market": "spread",
            "spread_home": -7.0,
            "captured_at": "2020-09-17T20:00:00Z",
            "kickoff_utc": "2020-09-17T20:20:00Z",
        }
    ]
    payload = build_market_arm_freeze(root=ROOT, quotes=late)
    assert "2020_02_CIN_CLE" not in payload["intersection"]["game_ids"]
    assert any(row.get("reason") == "late_quote_post_cutoff" for row in payload["excluded_slots"])


def test_valid_positive_invokes_loader_after_gates(tmp_path):
    spy = OutcomeReadSpy(lambda: {"2020_02_CIN_CLE": {"home_score": 27, "away_score": 22}})
    dest = tmp_path / "MARKET_ARM_FREEZE.json"
    result = run_market_arm_freeze(
        root=ROOT,
        outcome_loader=spy,
        invoke_outcome_after_gates=True,
        dest=dest,
    )
    assert result["ok"] is True
    assert result["outcome_loader_invoked_after_gates"] is True
    assert result["outcome_loader_reads"] == 1
    assert spy.reads == 1
    assert result["real_eval_executed"] is False
    assert dest.is_file()
    written = json.loads(dest.read_text(encoding="utf-8"))
    assert written["intersection"]["bytes_sha256"] == result["bytes_sha256"]
    assert written["b1_universe"]["sha256"] == B1_UNIVERSE_SHA256
    assert FEATURE_RECON_REG496_ARTIFACT_SHA256.startswith("282f979b")


def test_writer_refuses_protected_b1(tmp_path):
    payload = build_market_arm_freeze(root=ROOT)
    with pytest.raises(MarketArmFreezeRefuse, match="protected original"):
        write_market_arm_freeze(
            payload,
            root=ROOT,
            dest=ROOT / B1_UNIVERSE_PATH,
        )
    assert sha256_file(ROOT / B1_UNIVERSE_PATH) == B1_UNIVERSE_SHA256
    write_market_arm_freeze(payload, root=ROOT, dest=tmp_path / "ok.json")
    assert (tmp_path / "ok.json").is_file()
