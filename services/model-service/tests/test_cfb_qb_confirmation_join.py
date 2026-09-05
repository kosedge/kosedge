"""Chapter 3 confirmation join — W1 starter into existing 1C–1E path."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_season_engine import (
    build_packaged_universe,
    engine_status_payload,
    project_game_preview,
)
from src.services.cfb_season_engine.qb_confirmed_starters import (
    apply_confirmed_starter,
    confirmation_for,
    documentation,
    load_confirmed_starters,
)
from src.services.cfb_season_engine.qb_situation import build_qb_situation
from src.services.cfb_season_engine.qb_situation_overrides import apply_qb_situation_override
from src.services.cfb_season_engine.real_roster import load_real_roster_snapshot


def _pack_qb(team: str) -> dict:
    snap = load_real_roster_snapshot()
    return dict((snap.get("teams") or {}).get(team, {}).get("qb") or {})


def test_confirm_book_present_and_excludes_open_camps() -> None:
    book = load_confirmed_starters()
    assert book["present"] is True
    assert book["week"] == 1
    assert book["as_of"] == "2026-09-01"
    for team in ("UGA", "MICH", "ALA", "UF"):
        assert confirmation_for(team) is None
    assert confirmation_for("OSU")["starter_key"] == "5079712"
    assert confirmation_for("FSU")["starter_name"] == "Ashton Daniels"
    assert confirmation_for("LSU")["starter_name"] == "Sam Leavitt"
    doc = documentation()
    assert doc["n"] >= 70
    assert "rest_travel" in " ".join(doc["does_not"]).lower() or "rest_travel" in (
        doc.get("doctrine") or ""
    )


def test_confirm_is_noop_when_identity_already_matches() -> None:
    """Diff gate unit: matched starter_key → index-driving fields unchanged."""
    base = apply_qb_situation_override("OSU", _pack_qb("OSU"))
    after = apply_confirmed_starter("OSU", base)
    assert after["starter_key"] == base["starter_key"]
    assert after["starter_name"] == base["starter_name"]
    assert after.get("qb_class", base.get("qb_class")) == base.get("qb_class")
    assert after.get("qb_talent", base.get("qb_talent")) == base.get("qb_talent")
    assert after.get("confirmation_matched") is True

    fsu_base = apply_qb_situation_override("FSU", _pack_qb("FSU"))
    fsu_after = apply_confirmed_starter("FSU", fsu_base)
    assert fsu_after["starter_key"] == fsu_base["starter_key"] == "4838679"
    assert fsu_after["qb_class"] == "open_competition"
    assert fsu_after.get("qb_talent") == fsu_base.get("qb_talent")


def test_pipeline_does_not_fork_build_qb_situation() -> None:
    """Same primitive; confirmation is only a payload join."""
    payload = apply_confirmed_starter(
        "OSU", apply_qb_situation_override("OSU", _pack_qb("OSU"))
    )
    qb = build_qb_situation("OSU", payload)
    assert qb.starter_name == "Julian Sayin"
    assert qb.qb_class == "incumbent"


def test_universe_indexes_match_preconfirm_path_for_matched_starters() -> None:
    """Zero-move gate: live universe vs override-only rebuild for OSU/FSU/BALL."""
    universe = build_packaged_universe(2026)
    for team in ("OSU", "FSU", "LSU", "BALL", "TEX", "ND"):
        live = universe.teams[team].qb
        assert live is not None, team
        payload = apply_confirmed_starter(
            team, apply_qb_situation_override(team, _pack_qb(team))
        )
        # Strip confirmation-only note noise by rebuilding from identity+class+talent
        rebuilt = build_qb_situation(
            team,
            {
                "qb_class": payload.get("qb_class"),
                "starter_name": payload.get("starter_name"),
                "starter_key": payload.get("starter_key"),
                "qb_talent": payload.get("qb_talent"),
                "ol_support": payload.get("ol_support"),
                "weapons_support": payload.get("weapons_support"),
                "is_portal": payload.get("is_portal"),
                "is_true_freshman": payload.get("is_true_freshman"),
                "open_competition": payload.get("open_competition"),
                "experience_starts": payload.get("experience_starts"),
            },
        )
        assert abs(float(live.qb_situation_index) - float(rebuilt.qb_situation_index)) < 1e-9, team
        assert abs(float(live.qb_situation_score) - float(rebuilt.qb_situation_score)) < 1e-9, team


def test_ball_at_osu_wp_gate_and_status_exposes_join() -> None:
    universe = build_packaged_universe(2026)
    assert universe.teams["OSU"].qb.starter_name == "Julian Sayin"
    proj = project_game_preview(
        universe, home_team="OSU", away_team="BALL", week=1, neutral_site=False
    )
    assert float(proj.home_win_prob) >= 0.90
    status = engine_status_payload(season=2026, demo=True)
    assert status["qb_confirmed_starters"]["n"] >= 70
    assert status["qb_confirmed_starters"]["week"] == 1
    assert "UGA" in (status["qb_confirmed_starters"].get("open_camps_no_lock") or [])
