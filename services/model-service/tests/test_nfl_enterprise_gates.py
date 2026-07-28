"""Tests for NFL enterprise gates + selective publish policy."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.nfl_enterprise_gates import evaluate_enterprise_gates
from src.services.nfl_side_total_publish_policy import (
    DEFAULT_SEGMENT_EVIDENCE,
    SegmentEvidence,
    candidate_tag,
    publish_tag,
)


def test_candidate_tag_spread_play_and_lean_disabled():
    assert candidate_tag("spread", 2.5) == "PLAY"
    assert candidate_tag("spread", 1.5) == "PASS"  # LEAN disabled
    assert candidate_tag("spread", 0.5) == "PASS"


def test_candidate_tag_total_narrow_play_band():
    assert candidate_tag("total", 2.7) == "PLAY"
    assert candidate_tag("total", 3.5) == "PASS"  # oversized toxic
    assert candidate_tag("total", 2.0) == "PASS"


def test_publish_tag_requires_segment_and_respects_red_product_gate():
    red = publish_tag(market="spread", abs_edge=4.0, product_gate_status="RED")
    assert red["tag"] == "PASS"
    assert red["stake_eligible"] is False

    play = publish_tag(market="spread", abs_edge=3.0, product_gate_status="GREEN")
    assert play["tag"] == "PLAY"
    assert play["stake_eligible"] is True

    lean_cand = publish_tag(market="spread", abs_edge=1.5, product_gate_status="GREEN")
    assert lean_cand["tag"] == "PASS"


def test_publish_tag_fails_when_segment_evidence_red():
    bad = {
        "spread:PLAY": SegmentEvidence(
            n_ats=100,
            ats_hit_rate=0.48,
            beats_minus_110=False,
        )
    }
    out = publish_tag(
        market="spread",
        abs_edge=3.0,
        product_gate_status="GREEN",
        segment_evidence=bad,
    )
    assert out["tag"] == "PASS"
    assert out["reason"] == "segment_evidence_failed"


def test_evaluate_gates_red_when_ats_and_clv_thin():
    report = evaluate_enterprise_gates(
        grading={
            "model": {
                "ats_hit_rate": 0.49,
                "n_spread": 1693,
                "clv_spread_positive_rate": 0.66,
                "n_clv_spread": 159,
                "spread_mae": 9.6,
                "total_mae": 10.1,
            },
            "market_close": {"spread_mae": 9.8, "total_mae": 10.3},
            "coverage": {"owned_open_close_games": 724},
        },
        supervised={
            "schema_version": 3,
            "feature_keys": ["diff_kav_net_5g"],
            "metrics": {
                "test_brier": 0.15,
                "test_margin_mae": 7.5,
                "test_total_mae": 9.2,
                "test_rows": 570,
            },
        },
        props_stake_eligible=False,
    )
    assert report.betting_product_ready is False
    assert report.selective_play_ready is False
    assert report.overall in {"YELLOW", "RED"}
    by_name = {c.name: c.status for c in report.checks}
    assert by_name["ats_vs_minus_110"] == "RED"
    assert by_name["clv_spread_sample"] == "YELLOW"
    assert by_name["supervised_holdout"] == "GREEN"
    assert by_name["props_stake_policy"] == "GREEN"
    assert by_name["play_only_holdout"] == "RED"  # artifact missing


def test_play_only_holdout_yellow_when_ats_clears_clv_thin():
    report = evaluate_enterprise_gates(
        grading={
            "model": {
                "ats_hit_rate": 0.53,
                "n_spread": 500,
                "clv_spread_positive_rate": 0.56,
                "n_clv_spread": 220,
                "spread_mae": 9.4,
                "total_mae": 10.0,
            },
            "market_close": {"spread_mae": 9.8, "total_mae": 10.3},
            "coverage": {"owned_open_close_games": 900},
        },
        supervised={
            "schema_version": 3,
            "feature_keys": ["diff_kav_net_5g"],
            "metrics": {
                "test_brier": 0.15,
                "test_margin_mae": 7.5,
                "test_total_mae": 9.2,
                "test_rows": 570,
            },
        },
        play_holdout={
            "primary_holdout_2025": {
                "spread": {
                    "n": 206,
                    "hit_rate": 0.76,
                    "n_clv": 105,
                    "clv_positive_rate": 0.53,
                    "gate": "YELLOW",
                },
                "combined": {"gate": "YELLOW"},
            },
            "overall": {"gate": "YELLOW"},
            "green_segments_2025": [],
        },
        props_stake_eligible=False,
    )
    by_name = {c.name: c.status for c in report.checks}
    assert by_name["play_only_holdout"] == "YELLOW"
    assert report.selective_play_ready is False
    assert report.betting_product_ready is False


def test_default_segment_play_clears():
    assert DEFAULT_SEGMENT_EVIDENCE["spread:PLAY"].clears()
    assert not DEFAULT_SEGMENT_EVIDENCE["spread:LEAN"].clears()
