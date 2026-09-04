"""Scorecard grading unit tests — frozen gates, no peek-tune."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

WEB_ROOT = Path(__file__).resolve().parent.parent
SRC = WEB_ROOT / "src"
for p in (str(WEB_ROOT), str(SRC)):
    if p not in sys.path:
        sys.path.insert(0, p)

from ncaam_lab.scorecard import (
    DATA_GAP,
    grade_evidence,
    grade_market_edge,
    grade_predictive,
    influence_decision,
)


def test_predictive_red_when_worse_than_market():
    grade, _ = grade_predictive(
        {
            "n_with_actual": 120,
            "outcome_coverage": 0.5,
            "b2_margin_mae": 14.0,
            "b1_margin_mae": 10.0,
            "b2_signed_bias": 0.5,
        }
    )
    assert grade == "RED"


def test_predictive_green_when_beats_market():
    grade, _ = grade_predictive(
        {
            "n_with_actual": 120,
            "outcome_coverage": 0.5,
            "b2_margin_mae": 9.0,
            "b1_margin_mae": 10.0,
            "b2_signed_bias": 0.2,
        }
    )
    assert grade == "GREEN"


def test_market_edge_red_on_negative_roi():
    grade, _ = grade_market_edge(
        {
            "n_ats": 80,
            "ats": 0.48,
            "roi_minus110": -0.05,
            "n_clv_move": 50,
            "clv_positive_rate": 0.45,
        }
    )
    assert grade == "RED"


def test_evidence_red_on_leakage():
    grade, _ = grade_evidence(
        {"n_with_actual": 200, "outcome_coverage": 0.5, "settled_forbidden_count": 0},
        leakage_ok=False,
        leakage_violations=3,
        manifests={},
    )
    assert grade == "RED"


def test_evidence_red_on_settled():
    grade, _ = grade_evidence(
        {"n_with_actual": 200, "outcome_coverage": 0.5, "settled_forbidden_count": 2},
        leakage_ok=True,
        leakage_violations=0,
        manifests={},
    )
    assert grade == "RED"


def test_influence_no_on_red_pillar():
    decision, _ = influence_decision(
        {
            "predictive_quality": "RED",
            "market_edge_evidence": "AMBER",
            "evidence_quality": "AMBER",
        }
    )
    assert decision == "NO"


def test_influence_insufficient_on_data_gap():
    decision, _ = influence_decision(
        {
            "predictive_quality": DATA_GAP,
            "market_edge_evidence": "AMBER",
            "evidence_quality": "AMBER",
        }
    )
    assert decision == "INSUFFICIENT EVIDENCE"
