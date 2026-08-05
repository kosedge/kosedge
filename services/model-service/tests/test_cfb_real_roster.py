"""Tests for CFB v0.6 real-roster snapshot wiring."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_season_engine import (
    DEFAULT_SEASON_ENGINE_VERSION,
    build_packaged_universe,
    engine_status_payload,
    resolve_season_universe,
)
from src.services.cfb_season_engine.real_roster import (
    ROSTER_SOURCE_PACKAGED_ESPN,
    load_real_roster_snapshot,
    snapshot_meta,
)

DATA_DIR = (
    Path(__file__).resolve().parents[1]
    / "src/services/cfb_season_engine/data"
)
SNAPSHOT = DATA_DIR / "cfb_real_roster_snapshot_2026.json"
# Legacy priors backup is not required; we compare against known weak names.


def test_engine_version_real_roster() -> None:
    assert DEFAULT_SEASON_ENGINE_VERSION == "cfb-season-engine-v0.7-player-hooks"


def test_loader_prefers_real_snapshot_when_present() -> None:
    snap = load_real_roster_snapshot()
    assert snap is not None, "packaged ESPN snapshot must ship in-image"
    meta = snapshot_meta(snap)
    assert meta["present"] is True
    assert meta["roster_source"] == ROSTER_SOURCE_PACKAGED_ESPN
    assert int(meta["coverage"].get("teams_with_named_qb") or 0) >= 80

    universe, res_meta = resolve_season_universe(season=2026, demo=True, session=None)
    assert res_meta["roster_source"] == ROSTER_SOURCE_PACKAGED_ESPN
    assert res_meta["depth_source"]
    assert res_meta["portal_source"]
    assert universe.notes.get("mode") == "packaged_real_roster"
    assert "demo" not in (res_meta.get("roster_source") or "").lower()
    assert "weak" not in (res_meta.get("roster_source") or "").lower()


def test_status_exposes_roster_depth_portal_sources() -> None:
    payload = engine_status_payload(season=2026, demo=True)
    assert payload["engine_version"] == "cfb-season-engine-v0.7-player-hooks"
    assert payload["roster_source"] == ROSTER_SOURCE_PACKAGED_ESPN
    assert payload["depth_source"]
    assert payload["portal_source"]
    assert payload["as_of"] or payload["roster_as_of"]
    assert payload["data_sources"]["roster_source"] == ROSTER_SOURCE_PACKAGED_ESPN
    # Must not claim portal feeds are simply "not_wired" when snapshot is present.
    assert "not_wired" not in str(payload["data_sources"].get("roster_source", ""))
    assert payload["team_fidelity_counts"].get("espn_named_qb", 0) >= 50


def test_known_teams_differ_from_legacy_placeholder_qb_names() -> None:
    """Material identity / class changes vs old curated illustrative QBs."""
    snap = load_real_roster_snapshot()
    assert snap is not None
    teams = snap["teams"]
    # Arch Manning should remain the Texas QB1 with real 2025 production.
    tex = teams["TEX"]["qb"]
    assert "Manning" in tex["starter_name"]
    assert tex["qb_class"] == "incumbent"
    assert int(tex.get("pass_attempts_2025") or 0) >= 200

    # Georgia no longer lists Gunner Stockton as the packaged starter.
    uga = teams["UGA"]["qb"]
    assert uga["starter_name"]
    assert "Stockton" not in uga["starter_name"]

    # FSU should not still claim Tommy Castellanos if ESPN roster moved on.
    fsu = teams["FSU"]["qb"]
    assert fsu["starter_name"]
    assert "Castellanos" not in fsu["starter_name"]

    universe = build_packaged_universe(2026)
    # Roster strength / QB class should be inspectable and non-default for TEX.
    tex_state = universe.teams["TEX"]
    assert tex_state.qb and tex_state.qb.qb_class == "incumbent"
    assert tex_state.roster and tex_state.roster.roster_strength > 55
    assert tex_state.roster.source == ROSTER_SOURCE_PACKAGED_ESPN

    ball = universe.teams.get("BALL")
    if ball and ball.roster:
        # Mid-major should not silently stay on placeholder league-average source.
        assert ball.roster.source == ROSTER_SOURCE_PACKAGED_ESPN
        assert ball.qb and ball.qb.starter_name


def test_snapshot_file_coverage_counts() -> None:
    blob = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    cov = blob.get("coverage") or {}
    assert int(cov.get("teams_with_roster") or 0) >= 100
    assert int(cov.get("total_depth_rows") or 0) >= 500
    assert blob.get("roster_source") == ROSTER_SOURCE_PACKAGED_ESPN
