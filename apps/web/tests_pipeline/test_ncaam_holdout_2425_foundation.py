"""Phase 2.6A — 2024–25 sealed holdout foundation tests (no scoring / no unseal)."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import date, datetime
from pathlib import Path

import pytest

WEB_ROOT = Path(__file__).resolve().parents[1]
SRC = WEB_ROOT / "src"
for p in (str(WEB_ROOT), str(SRC)):
    if p not in sys.path:
        sys.path.insert(0, p)

from ncaam_lab.holdout_2425.constants import HOLDOUT_ID  # noqa: E402
from ncaam_lab.holdout_2425.evaluator_gate import (  # noqa: E402
    HoldoutSealError,
    UnsealAuthorization,
    assert_may_evaluate,
    evaluate_holdout_refused_by_default,
)
from ncaam_lab.holdout_2425.io_util import write_json  # noqa: E402
from ncaam_lab.holdout_2425.kenpom_audit import (  # noqa: E402
    build_game_eligibility,
    select_snapshot_for_tip,
)
from ncaam_lab.holdout_2425.schedule_normalize import (  # noqa: E402
    detect_duplicate_event_ids,
    detect_participant_reversals,
    outcome_label_ok,
    quarantine_nonfinal,
)
from ncaam_lab.holdout_2425.seal_package import (  # noqa: E402
    build_feature_and_label_packages,
)
from ncaam_lab.holdout_2425.venue_contract import normalize_venue_status  # noqa: E402


def test_raw_to_normalized_final_and_incomplete():
    final = {
        "espn_game_id": "1",
        "date": "2024-12-01",
        "status": "final",
        "home": "duke",
        "away": "kentucky",
        "home_score": 80,
        "away_score": 70,
    }
    incomplete = {
        "espn_game_id": "2",
        "date": "2024-12-01",
        "status": "postponed",
        "home": "duke",
        "away": "unc",
        "home_score": None,
        "away_score": None,
    }
    canceled = {
        "espn_game_id": "3",
        "date": "2024-12-01",
        "status": "canceled",
        "home": "x",
        "away": "y",
        "home_score": 0,
        "away_score": 0,
    }
    assert outcome_label_ok(final) is True
    assert outcome_label_ok(incomplete) is False
    assert outcome_label_ok(canceled) is False
    kept, quar = quarantine_nonfinal([final, incomplete, canceled])
    assert len(kept) == 1 and len(quar) == 2


def test_duplicate_and_orientation_detection():
    games = [
        {
            "espn_game_id": "a",
            "date": "2024-12-01",
            "home": "duke",
            "away": "kentucky",
            "status": "final",
            "home_score": 1,
            "away_score": 2,
        },
        {
            "espn_game_id": "a",
            "date": "2024-12-01",
            "home": "duke",
            "away": "kentucky",
            "status": "final",
            "home_score": 1,
            "away_score": 2,
        },
        {
            "espn_game_id": "b",
            "date": "2024-12-02",
            "home": "duke",
            "away": "unc",
            "status": "final",
            "home_score": 1,
            "away_score": 2,
        },
        {
            "espn_game_id": "c",
            "date": "2024-12-02",
            "home": "unc",
            "away": "duke",
            "status": "final",
            "home_score": 2,
            "away_score": 1,
        },
    ]
    assert detect_duplicate_event_ids(games) == ["a"]
    assert len(detect_participant_reversals(games)) >= 1


def test_venue_neutral_home_unknown_fail_closed():
    home = normalize_venue_status(
        neutral_site_raw=False,
        venue_name="Cameron Indoor Stadium",
        home_team_id="duke",
        season_type="regular",
    )
    assert home["venue_status"] == "confirmed_home"

    neut = normalize_venue_status(
        neutral_site_raw=True,
        venue_name="Madison Square Garden",
        home_team_id="duke",
        season_type="regular",
    )
    assert neut["venue_status"] == "confirmed_neutral"

    unknown = normalize_venue_status(
        neutral_site_raw=None,
        venue_name="Somewhere Arena",
        home_team_id="duke",
        season_type="regular",
    )
    assert unknown["venue_status"] == "unknown"

    conflict = normalize_venue_status(
        neutral_site_raw=False,
        venue_name="State Farm Center",
        home_team_id="duke",
        season_type="postseason",
    )
    assert conflict["venue_status"] == "unknown"
    assert conflict["conflict_reason"]


def test_snapshot_asof_selection_and_future_rejection():
    snaps = [
        {
            "eligible": True,
            "snapshot_date": "2024-11-10",
            "filename": "kenpom_2024-11-10.parquet",
            "sha256": "aaa",
        },
        {
            "eligible": True,
            "snapshot_date": "2024-11-17",
            "filename": "kenpom_2024-11-17.parquet",
            "sha256": "bbb",
        },
    ]
    sel = select_snapshot_for_tip(date(2024, 11, 15), snaps)
    assert sel is not None
    assert sel["snapshot_date"] == "2024-11-10"
    assert date.fromisoformat(sel["snapshot_date"]) <= date(2024, 11, 15)

    games = [
        {"espn_game_id": "1", "date": "2024-11-15", "home": "duke", "away": "kentucky"},
        {"espn_game_id": "2", "date": "2024-11-05", "home": "duke", "away": "unc"},
    ]
    elig = build_game_eligibility(games, snaps)
    by_id = {r["event_id"]: r for r in elig["rows"]}
    assert by_id["1"]["eligibility_status"] == "PIT_ELIGIBLE"
    assert by_id["1"]["selected_snapshot_id"] == "kenpom_2024-11-10.parquet"
    assert by_id["2"]["eligibility_status"] == "MISSING_PIT_SNAPSHOT"


def test_odds_timestamp_honesty_ordering():
    tip = datetime.fromisoformat("2024-12-01T19:00:00+00:00")
    close_ok = datetime.fromisoformat("2024-12-01T18:00:00+00:00")
    close_bad = datetime.fromisoformat("2024-12-01T19:30:00+00:00")
    assert close_ok < tip
    assert not (close_bad < tip)


def test_feature_label_separation_and_deterministic_hashes(tmp_path, monkeypatch):
    import ncaam_lab.holdout_2425.constants as constants
    import ncaam_lab.holdout_2425.seal_package as seal_mod

    monkeypatch.setattr(constants, "FEATURE_DIR", tmp_path / "feature_package")
    monkeypatch.setattr(constants, "LABEL_DIR", tmp_path / "label_package")
    monkeypatch.setattr(constants, "REJECTED_DIR", tmp_path / "rejected")
    monkeypatch.setattr(constants, "SEAL_DIR", tmp_path / "seal")
    monkeypatch.setattr(seal_mod, "FEATURE_DIR", tmp_path / "feature_package")
    monkeypatch.setattr(seal_mod, "LABEL_DIR", tmp_path / "label_package")
    monkeypatch.setattr(seal_mod, "REJECTED_DIR", tmp_path / "rejected")
    monkeypatch.setattr(seal_mod, "SEAL_DIR", tmp_path / "seal")

    schedule = [
        {
            "espn_game_id": "10",
            "date": "2024-12-01",
            "tipoff": "2024-12-01T19:00Z",
            "home": "duke",
            "away": "kentucky",
            "status": "final",
            "home_score": 80,
            "away_score": 70,
        }
    ]
    venue_rows = [
        {
            "source_event_id": "10",
            "venue_status": "confirmed_home",
            "validation_status": "ok",
            "historical_reconstruction": True,
            "b7_join_key": "2024-12-01|duke|kentucky",
            "conflict_reason": None,
        }
    ]
    kenpom_rows = [
        {
            "source_event_id": "10",
            "event_id": "10",
            "eligibility_status": "PIT_ELIGIBLE",
            "selected_snapshot_id": "kenpom_2024-11-24.parquet",
            "selected_snapshot_sha256": "abc",
        }
    ]
    odds_by = {
        "10": {
            "event_id": "odds1",
            "b1_status": "B1_ELIGIBLE",
            "open_snapshot_ts": "2024-11-30T12:00:00Z",
            "close_snapshot_ts": "2024-12-01T18:00:00Z",
            "n_books": 5,
        }
    }

    seal1 = build_feature_and_label_packages(
        schedule_rows=schedule,
        venue_rows=venue_rows,
        kenpom_eligibility=kenpom_rows,
        odds_by_espn_id=odds_by,
    )
    seal2 = build_feature_and_label_packages(
        schedule_rows=schedule,
        venue_rows=venue_rows,
        kenpom_eligibility=kenpom_rows,
        odds_by_espn_id=odds_by,
    )
    assert seal1["feature_content_sha256"] == seal2["feature_content_sha256"]
    assert seal1["label_content_sha256"] == seal2["label_content_sha256"]
    assert seal1["features_labels_joined_for_evaluation"] is False
    assert seal1["n_complete_intersection"] == 1

    features = json.loads((tmp_path / "feature_package" / "features.json").read_text())
    labels = json.loads((tmp_path / "label_package" / "labels.json").read_text())
    assert "home_score" not in features[0]
    assert "away_score" not in features[0]
    assert "actual_home_margin" not in features[0]
    assert labels[0]["label_present"] is True


def test_evaluator_refuses_without_unseal():
    with pytest.raises(HoldoutSealError):
        evaluate_holdout_refused_by_default(None)

    partial = UnsealAuthorization(
        holdout_id="wrong",
        authorize_unseal=False,
        candidate_code_hash="",
        feature_manifest_hash="",
        label_manifest_hash="",
        evaluation_spec_hash="",
        git_clean=False,
        prior_result_receipt_exists=False,
    )
    with pytest.raises(HoldoutSealError):
        assert_may_evaluate(partial)

    full = UnsealAuthorization(
        holdout_id=HOLDOUT_ID,
        authorize_unseal=True,
        candidate_code_hash="a" * 32,
        feature_manifest_hash="b" * 32,
        label_manifest_hash="c" * 32,
        evaluation_spec_hash="d" * 32,
        git_clean=True,
        prior_result_receipt_exists=True,
        governance_replication_authorized=False,
    )
    with pytest.raises(HoldoutSealError, match="prior result"):
        assert_may_evaluate(full)

    authorized = UnsealAuthorization(
        holdout_id=HOLDOUT_ID,
        authorize_unseal=True,
        candidate_code_hash="a" * 32,
        feature_manifest_hash="b" * 32,
        label_manifest_hash="c" * 32,
        evaluation_spec_hash="d" * 32,
        git_clean=True,
        prior_result_receipt_exists=False,
    )
    with pytest.raises(HoldoutSealError, match="not authorized to execute"):
        evaluate_holdout_refused_by_default(authorized)


def test_incumbent_model_code_untouched():
    from ncaam_lab import fair_b2, materialize  # noqa: F401

    fair_path = SRC / "ncaam_lab" / "fair_b2.py"
    mat_path = SRC / "ncaam_lab" / "materialize.py"
    assert fair_path.exists() and mat_path.exists()
    fair_txt = fair_path.read_text(encoding="utf-8")
    assert "holdout_2425" not in fair_txt
    assert "unseal" not in fair_txt.lower()


def test_write_json_deterministic(tmp_path):
    p = tmp_path / "a.json"
    h1 = write_json(p, {"b": 1, "a": 2})
    h2 = write_json(p, {"a": 2, "b": 1})
    assert h1 == h2
    assert hashlib.sha256(p.read_bytes()).hexdigest() == h1
