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
    # As-of selection only — team/AdjEM gate covered in dedicated tests below.
    elig = build_game_eligibility(games, snaps, require_both_teams_ratings=False)
    by_id = {r["event_id"]: r for r in elig["rows"]}
    assert by_id["1"]["eligibility_status"] == "PIT_ELIGIBLE"
    assert by_id["1"]["selected_snapshot_id"] == "kenpom_2024-11-10.parquet"
    assert by_id["2"]["eligibility_status"] == "MISSING_PIT_SNAPSHOT"


def test_odds_timestamp_honesty_fail_closed():
    """B1 requires parseable tip+open+close with open < tip and close < tip."""
    import polars as pl
    from ncaam_lab.holdout_2425.odds_audit import classify_odds_events

    tip = "2024-12-01T19:00:00+00:00"
    schedule = [
        {
            "espn_game_id": "g1",
            "date": "2024-12-01",
            "home": "duke",
            "away": "kentucky",
        }
    ]

    def _events(**overrides):
        base = {
            "event_id": "e1",
            "tip_date": "2024-12-01",
            "commence_time": tip,
            "home_team": "Duke Blue Devils",
            "away_team": "Kentucky Wildcats",
            "n_books": 3,
            "n_open_spread": 2,
            "n_close_spread": 2,
            "open_time_min": "2024-11-30T12:00:00+00:00",
            "close_time_max": "2024-12-01T18:00:00+00:00",
            "n_rows": 4,
        }
        base.update(overrides)
        return pl.DataFrame([base])

    ok = classify_odds_events(_events(), schedule)
    assert ok["rows"][0]["b1_status"] == "B1_ELIGIBLE"

    missing_close = classify_odds_events(
        _events(close_time_max=None, n_close_spread=0), schedule
    )
    assert missing_close["rows"][0]["b1_status"] != "B1_ELIGIBLE"
    assert "missing_or_unparseable_close" in missing_close["rows"][0]["reasons"] or (
        "missing_close" in missing_close["rows"][0]["reasons"]
    )

    missing_commence = classify_odds_events(_events(commence_time=None), schedule)
    assert missing_commence["rows"][0]["b1_status"] != "B1_ELIGIBLE"
    assert "missing_or_unparseable_commence" in missing_commence["rows"][0]["reasons"]

    open_eq_tip = classify_odds_events(_events(open_time_min=tip), schedule)
    assert open_eq_tip["rows"][0]["b1_status"] == "TIMESTAMP_DISHONEST"
    assert "open_not_strictly_before_tip" in open_eq_tip["rows"][0]["reasons"]

    close_eq_tip = classify_odds_events(_events(close_time_max=tip), schedule)
    assert close_eq_tip["rows"][0]["b1_status"] == "TIMESTAMP_DISHONEST"
    assert "close_not_strictly_before_tip" in close_eq_tip["rows"][0]["reasons"]


def test_campus_schools_do_not_collapse_to_di_parents():
    """Negative regression: strip-final-token must not map campus schools to D-I parents."""
    from ncaam_identity import odds_name_to_team_norm, resolve_team_id

    cases = [
        ("Texas A&M Kingsville", "texas a&m"),
        ("Texas A&M-Kingsville", "texas a&m"),
        ("South Carolina Beaufort", "south carolina"),
        ("North Carolina Wesleyan", "north carolina"),
        ("Colorado State Pueblo", "colorado state"),
        ("Colorado State-Pueblo", "colorado state"),
    ]
    for raw, parent in cases:
        got = odds_name_to_team_norm(raw)
        assert got != parent, f"{raw!r} collapsed to {parent!r}"
        assert got is None, f"{raw!r} unexpectedly resolved to {got!r}"
        assert resolve_team_id(raw) is None


def test_raw_ingestion_receipt_requires_verified_sidecars(tmp_path):
    import importlib.util

    script = (
        WEB_ROOT.parent.parent / "scripts" / "ncaam" / "build_2425_sealed_holdout.py"
    )
    spec = importlib.util.spec_from_file_location("build_2425_sealed_holdout", script)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)

    raw = tmp_path / "raw"
    raw.mkdir()
    payload = raw / "espn_scoreboard_2024-11-04.json"
    payload.write_text('{"events":[]}\n', encoding="utf-8")

    # Missing sidecar → not preserved
    receipt_missing = mod._raw_ingestion_receipt(raw)
    assert receipt_missing["immutable_raw_preserved"] is False
    assert receipt_missing["n_missing_sidecars"] == 1

    # Wrong digest → refuse
    (raw / "espn_scoreboard_2024-11-04.sha256").write_text(
        "0" * 64 + "\n", encoding="utf-8"
    )
    receipt_bad = mod._raw_ingestion_receipt(raw)
    assert receipt_bad["immutable_raw_preserved"] is False
    assert receipt_bad["n_digest_mismatches"] == 1

    # Matching digest → ok
    import hashlib

    digest = hashlib.sha256(payload.read_bytes()).hexdigest()
    (raw / "espn_scoreboard_2024-11-04.sha256").write_text(digest + "\n", encoding="utf-8")
    receipt_ok = mod._raw_ingestion_receipt(raw)
    assert receipt_ok["immutable_raw_preserved"] is True
    assert receipt_ok["n_day_receipts_indexed"] == 1


def test_seal_payload_sha256_differs_from_file_hash(tmp_path, monkeypatch):
    import hashlib
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
    seal = build_feature_and_label_packages(
        schedule_rows=schedule,
        venue_rows=venue_rows,
        kenpom_eligibility=kenpom_rows,
        odds_by_espn_id=odds_by,
    )
    assert "seal_payload_sha256" in seal
    assert "seal_receipt_sha256" not in json.loads(
        (tmp_path / "seal" / "seal_receipt.json").read_text()
    )
    file_sha = hashlib.sha256(
        (tmp_path / "seal" / "seal_receipt.json").read_bytes()
    ).hexdigest()
    assert seal["seal_file_sha256"] == file_sha
    assert seal["seal_payload_sha256"] != file_sha
    assert (tmp_path / "seal" / "seal_receipt.file_sha256").read_text().strip() == file_sha


def test_kenpom_null_captured_at_requires_policy_and_team_ratings(tmp_path):
    import polars as pl
    from ncaam_lab.holdout_2425 import kenpom_audit as ka

    snap_dir = tmp_path / "snaps"
    snap_dir.mkdir()
    fp = snap_dir / "kenpom_2024-11-10.parquet"
    pl.DataFrame(
        {
            "team_norm": ["duke", "kentucky", "north carolina"],
            "adjem": [30.0, 25.0, 28.0],
            "adjtempo": [68.0, 70.0, 69.0],
        }
    ).write_parquet(fp)

    snaps = ka.inventory_snapshots(
        snap_dir,
        window_start=date(2024, 11, 4),
        window_end=date(2025, 4, 8),
        require_captured_at=False,
    )
    assert len(snaps) == 1
    assert snaps[0]["eligible"] is True
    assert snaps[0]["captured_at"] is None
    assert snaps[0]["archive_date_semantics"] == "filename_date_is_as_of"
    assert snaps[0]["null_captured_at_policy"] == "allowed_when_filename_date_is_as_of"

    snaps_req = ka.inventory_snapshots(
        snap_dir,
        window_start=date(2024, 11, 4),
        window_end=date(2025, 4, 8),
        require_captured_at=True,
    )
    assert snaps_req[0]["eligible"] is False
    assert snaps_req[0]["quarantine_reason"] == "captured_at_required_but_null"

    games = [
        {"espn_game_id": "1", "date": "2024-11-15", "home": "duke", "away": "kentucky"},
        {
            "espn_game_id": "2",
            "date": "2024-11-15",
            "home": "duke",
            "away": "not-a-real-team-xyz",
        },
    ]
    elig = ka.build_game_eligibility(games, snaps, require_both_teams_ratings=True)
    by_id = {r["event_id"]: r for r in elig["rows"]}
    assert by_id["1"]["eligibility_status"] == "PIT_ELIGIBLE"
    assert by_id["2"]["eligibility_status"] == "PIT_TEAMS_OR_RATINGS_MISSING"

    # Missing AdjEM/AdjT fails closed
    fp2 = snap_dir / "kenpom_2024-11-17.parquet"
    pl.DataFrame(
        {
            "team_norm": ["duke", "kentucky"],
            "adjem": [30.0, None],
            "adjtempo": [68.0, 70.0],
        }
    ).write_parquet(fp2)
    snaps2 = ka.inventory_snapshots(
        snap_dir,
        window_start=date(2024, 11, 4),
        window_end=date(2025, 4, 8),
    )
    # completeness may quarantine the whole snapshot; force-eligible for team gate test
    for s in snaps2:
        if s["filename"] == "kenpom_2024-11-17.parquet":
            s["eligible"] = True
            s["path"] = fp2.as_posix()
    elig2 = ka.build_game_eligibility(
        [
            {
                "espn_game_id": "3",
                "date": "2024-11-18",
                "home": "duke",
                "away": "kentucky",
            }
        ],
        snaps2,
        require_both_teams_ratings=True,
    )
    assert elig2["rows"][0]["eligibility_status"] == "PIT_TEAMS_OR_RATINGS_MISSING"


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


def test_odds_identity_alias_families_26b():
    """Deterministic odds-name expansions; no fuzzy; Miami FL≠OH; USC≠South Carolina."""
    from ncaam_identity import odds_name_to_team_norm

    assert odds_name_to_team_norm("Washington St Cougars") == "washington state"
    assert odds_name_to_team_norm("Texas A&M-Commerce Lions") == "east texas a&m"
    assert odds_name_to_team_norm("UMKC Kangaroos") == "kansas city"
    assert odds_name_to_team_norm("St. Thomas (MN) Tommies") == "st thomas"
    assert odds_name_to_team_norm("St. Francis (PA) Red Flash") == "saint francis"
    assert odds_name_to_team_norm("Florida Int'l Golden Panthers") == "fiu"
    assert odds_name_to_team_norm("Miami") is None
    assert odds_name_to_team_norm("Miami (OH)") == "miami oh"
    assert odds_name_to_team_norm("USC Trojans") == "usc"
    assert odds_name_to_team_norm("South Carolina Gamecocks") == "south carolina"
    # Must not collapse Commerce into Texas A&M
    assert odds_name_to_team_norm("Texas A&M-Commerce Lions") != "texas a&m"


def test_readiness_no_longer_sealed_and_ready_by_default():
    from ncaam_lab.holdout_2425.readiness import compute_readiness
    import inspect
    src = inspect.getsource(compute_readiness)
    assert "SEALED_AND_READY" not in src or "SEALED_COVERAGE_REVIEW_REQUIRED" in src
    assert "SEALED_COVERAGE_REVIEW_REQUIRED" in src
