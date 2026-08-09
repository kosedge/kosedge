"""Phase 1 formal data-integrity gate — hard-fail validators."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import date
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

import pytest

from src.services.nfl_season_engine.data_integrity import (
    DataIntegrityError,
    assert_depth_sot_integrity,
    build_run_lineage,
    packaged_depth_path,
    validate_depth_sot_pack,
    validate_packaged_depth_file,
)
from src.services.nfl_season_engine.loaders import (
    build_packaged_real_universe,
    load_packaged_depth_chart,
    universe_schedule_meta,
)

REF = date(2026, 8, 9)


def _production_payload() -> tuple[dict, Path]:
    path = packaged_depth_path(2026)
    return json.loads(path.read_text(encoding="utf-8")), path


def test_production_pack_passes_integrity_gate() -> None:
    report = validate_packaged_depth_file(
        2026,
        reference_date=REF,
        max_age_days=7,
        require_archive=False,
    )
    assert report.ok, report.to_dict()
    assert report.snapshot_id.startswith("nfl-depth-2026-w1-")
    for check in (
        "missing_qb1",
        "duplicate_active_assignment",
        "usage_share_limits",
        "stale_snapshot",
        "engine_web_roster_agreement",
        "critical_role_gaps",
    ):
        assert check in report.checks_run


def test_loader_exposes_snapshot_lineage() -> None:
    rows, meta = load_packaged_depth_chart(2026)
    assert meta.get("snapshot_id")
    assert meta.get("pack_sha256")
    assert meta.get("identity_scheme") == "nflverse_gsis_player_id"
    assert all(r.get("player_id") for r in rows)

    universe = build_packaged_real_universe(2026)
    assert universe.notes.get("snapshot_id") == meta["snapshot_id"]
    sm = universe_schedule_meta(universe)
    assert sm.get("snapshot_id") == meta["snapshot_id"]
    lineage = build_run_lineage(
        snapshot_id=sm["snapshot_id"],
        pack_sha256=sm.get("pack_sha256") or "",
        roster_as_of=sm.get("roster_as_of") or "",
        n_team_sims=100,
        seed=7,
    )
    assert lineage["snapshot_id"] == meta["snapshot_id"]
    assert lineage["engine_version"]
    assert "run_config" in lineage


def test_bad_duplicate_assignment_fails() -> None:
    payload, path = _production_payload()
    bad = deepcopy(payload)
    bad["snapshot_id"] = "nfl-depth-fixture-dup-id"
    ari = next(
        r
        for r in bad["rows"]
        if r["team"] == "ARI" and r["position"] == "QB" and int(r["depth_order"]) == 1
    )
    for r in bad["rows"]:
        if r["team"] == "ATL" and r["position"] == "QB" and int(r["depth_order"]) == 1:
            r["player_id"] = ari["player_id"]
            break
    report = validate_depth_sot_pack(bad, pack_path=path, reference_date=REF)
    assert not report.ok
    assert any(f.check == "duplicate_active_assignment" for f in report.findings)
    with pytest.raises(DataIntegrityError):
        assert_depth_sot_integrity(bad, pack_path=path, reference_date=REF)


def test_bad_missing_qb1_fails() -> None:
    payload, path = _production_payload()
    bad = deepcopy(payload)
    bad["snapshot_id"] = "nfl-depth-fixture-missing-qb1"
    bad["rows"] = [
        r
        for r in bad["rows"]
        if not (
            r["team"] == "KC"
            and r["position"] == "QB"
            and int(r["depth_order"]) == 1
        )
    ]
    report = validate_depth_sot_pack(
        bad, pack_path=path, reference_date=REF, check_stale=False
    )
    assert not report.ok
    finding = next(f for f in report.findings if f.check == "missing_qb1")
    assert "KC" in finding.details.get("teams", [])


def test_bad_critical_role_gap_fails() -> None:
    payload, path = _production_payload()
    bad = deepcopy(payload)
    bad["snapshot_id"] = "nfl-depth-fixture-role-gap"
    bad["rows"] = [
        r for r in bad["rows"] if not (r["team"] == "SF" and r["position"] == "TE")
    ]
    report = validate_depth_sot_pack(
        bad, pack_path=path, reference_date=REF, check_stale=False
    )
    assert not report.ok
    assert any(f.check == "critical_role_gaps" for f in report.findings)


def test_bad_stale_snapshot_fails() -> None:
    payload, path = _production_payload()
    bad = deepcopy(payload)
    bad["snapshot_id"] = "nfl-depth-fixture-stale"
    bad["as_of"] = "2026-07-01"
    bad["as_of_timestamp"] = "2026-07-01T00:00:00Z"
    bad["daily_intel_as_of"] = "2026-07-01"
    report = validate_depth_sot_pack(
        bad,
        pack_path=path,
        reference_date=date(2026, 8, 9),
        max_age_days=7,
        check_stale=True,
    )
    assert not report.ok
    assert any(f.check == "stale_snapshot" for f in report.findings)


def test_share_blowup_fails_when_named_sums_absurd(monkeypatch) -> None:
    """Prove share gate hard-fails when named sums exceed policy ceiling."""
    import src.services.nfl_season_engine.data_integrity as di

    monkeypatch.setattr(di, "SHARE_NAMED_HARD_MAX", 1.0)
    report = validate_packaged_depth_file(2026, reference_date=REF, max_age_days=30)
    assert not report.ok
    assert any(f.check == "usage_share_limits" for f in report.findings)


def test_diggs_gsis_not_colliding_with_adams() -> None:
    rows, _ = load_packaged_depth_chart(2026)
    diggs = [r for r in rows if r["player_name"] == "Stefon Diggs"]
    adams = [r for r in rows if r["player_name"] == "Davante Adams"]
    assert len(diggs) == 1 and diggs[0]["team"] == "WAS"
    assert diggs[0]["player_id"] == "00-0031588"
    assert adams[0]["player_id"] == "00-0031381"
    assert diggs[0]["player_id"] != adams[0]["player_id"]
