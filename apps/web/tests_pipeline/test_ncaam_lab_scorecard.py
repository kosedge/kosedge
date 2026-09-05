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


def test_v1_1_write_paths_distinct_from_v1(tmp_path, monkeypatch):
    """Explicit v1.1 card freezes v1.1 artifacts without touching v1 filenames."""
    import ncaam_lab.scorecard as sc
    from ncaam_lab.scorecard import SCORECARD_VERSION_V1_1, write_scorecard_artifacts

    monkeypatch.setattr(sc, "_repo_root", lambda: tmp_path)
    (tmp_path / "data" / "ops").mkdir(parents=True)
    (tmp_path / "docs" / "lab").mkdir(parents=True)
    out = tmp_path / "lab"
    out.mkdir()

    card = {
        "scorecard_version": SCORECARD_VERSION_V1_1,
        "protocol_version": "ncaam-fair-lab-protocol-v1.0",
        "protocol_doc": "docs/lab/NCAAM_FAIR_LAB_PROTOCOL_v1.md",
        "scorecard_doc": "docs/lab/NCAAM_FAIR_LAB_SCORECARD_v1_1.md",
        "status": "results_filled",
        "generated_at": "2026-09-04T00:00:00+00:00",
        "sport": "ncaam",
        "grades": {
            "predictive_quality": "AMBER",
            "market_edge_evidence": "AMBER",
            "evidence_quality": "GREEN",
        },
        "grade_detail": {
            "predictive_quality": "unit",
            "market_edge_evidence": "unit",
            "evidence_quality": "unit",
        },
        "subscriber_influence": "INSUFFICIENT EVIDENCE",
        "subscriber_influence_detail": "unit",
        "leakage_receipt": {
            "kenpom_leakage_ok": True,
            "kenpom_leakage_violations": 0,
            "settled_forbidden_total": 0,
        },
        "cuts": {
            "test_a": {
                "predictive": {
                    "n_lab_games": 10,
                    "n_with_actual": 9,
                    "outcome_coverage": 0.9,
                },
                "market_edge": {},
                "evidence": {"continuity_counts": {"PRIOR": 10}},
            },
            "train_a": {
                "predictive": {
                    "n_lab_games": 10,
                    "n_with_actual": 9,
                    "outcome_coverage": 0.9,
                },
                "market_edge": {},
            },
        },
        "inputs": {"results_densify": False},
        "version_note": "unit",
        "v1_1_allowed_deltas": ["denser_results_join_schedule_sot_packs"],
    }
    paths = write_scorecard_artifacts(card, out_dir=out)
    assert paths.get("frozen_v1_untouched") == "true"
    assert (out / "ncaam-fair-lab-scorecard-v1.1.json").exists()
    assert (out / "ncaam-fair-lab-scorecard-v1.1.md").exists()
    assert not (out / "ncaam-fair-lab-scorecard-v1.json").exists()
    assert (tmp_path / "docs" / "lab" / "NCAAM_FAIR_LAB_SCORECARD_v1_1.md").exists()
    assert (tmp_path / "data" / "ops" / "ncaam-lab-scorecard-v1-1-20260904.md").exists()


def test_v1_2_write_paths_distinct_from_v1_and_v1_1(tmp_path, monkeypatch):
    """Densified card freezes v1.2 artifacts without touching v1 / v1.1 filenames."""
    import ncaam_lab.scorecard as sc
    from ncaam_lab.scorecard import SCORECARD_VERSION_V1_2, write_scorecard_artifacts

    monkeypatch.setattr(sc, "_repo_root", lambda: tmp_path)
    (tmp_path / "data" / "ops").mkdir(parents=True)
    (tmp_path / "docs" / "lab").mkdir(parents=True)
    out = tmp_path / "lab"
    out.mkdir()
    # Pre-seed frozen v1.1 so we can assert it stays untouched
    (out / "ncaam-fair-lab-scorecard-v1.1.json").write_text('{"frozen":true}\n')

    card = {
        "scorecard_version": SCORECARD_VERSION_V1_2,
        "protocol_version": "ncaam-fair-lab-protocol-v1.0",
        "protocol_doc": "docs/lab/NCAAM_FAIR_LAB_PROTOCOL_v1.md",
        "scorecard_doc": "docs/lab/NCAAM_FAIR_LAB_SCORECARD_v1_2.md",
        "status": "results_filled",
        "generated_at": "2026-09-05T00:00:00+00:00",
        "sport": "ncaam",
        "grades": {
            "predictive_quality": "AMBER",
            "market_edge_evidence": "AMBER",
            "evidence_quality": "GREEN",
        },
        "grade_detail": {
            "predictive_quality": "unit",
            "market_edge_evidence": "unit",
            "evidence_quality": "unit",
        },
        "subscriber_influence": "INSUFFICIENT EVIDENCE",
        "subscriber_influence_detail": "unit",
        "leakage_receipt": {
            "kenpom_leakage_ok": True,
            "kenpom_leakage_violations": 0,
            "settled_forbidden_total": 0,
        },
        "cuts": {
            "test_a": {
                "predictive": {
                    "n_lab_games": 10,
                    "n_with_actual": 9,
                    "outcome_coverage": 0.9,
                    "b2_margin_mae": 9.2,
                    "b1_margin_mae": 8.5,
                },
                "market_edge": {"ats": 0.53, "clv_positive_rate": 0.5},
                "evidence": {"continuity_counts": {"PRIOR": 10}},
            },
            "train_a": {
                "predictive": {
                    "n_lab_games": 10,
                    "n_with_actual": 9,
                    "outcome_coverage": 0.9,
                },
                "market_edge": {},
            },
        },
        "inputs": {"results_densify": True},
        "version_note": "unit",
        "v1_2_allowed_deltas": ["denser_path_a_odds_lake_honesty_clean"],
    }
    paths = write_scorecard_artifacts(card, out_dir=out)
    assert paths.get("frozen_v1_untouched") == "true"
    assert paths.get("frozen_v1_1_untouched") == "true"
    assert (out / "ncaam-fair-lab-scorecard-v1.2.json").exists()
    assert (out / "ncaam-fair-lab-scorecard-v1.2.md").exists()
    assert not (out / "ncaam-fair-lab-scorecard-v1.json").exists()
    assert (out / "ncaam-fair-lab-scorecard-v1.1.json").read_text() == '{"frozen":true}\n'
    assert (tmp_path / "docs" / "lab" / "NCAAM_FAIR_LAB_SCORECARD_v1_2.md").exists()
    assert (tmp_path / "data" / "ops" / "ncaam-lab-scorecard-v1-2-20260905.md").exists()
