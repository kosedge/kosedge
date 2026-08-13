"""QB situation SoT overrides + recomputed 2026 prior honesty."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_season_engine import (
    build_packaged_universe,
    engine_status_payload,
    project_game_preview,
    project_game_to_dict,
)
from src.services.cfb_season_engine.qb_situation import build_qb_situation
from src.services.cfb_season_engine.qb_situation_overrides import (
    apply_qb_situation_override,
    load_qb_overrides,
    override_for,
)
from src.services.cfb_warehouse.preseason_prior import lookup_prior


OVERRIDE_TEAMS = ("UGA", "MICH", "FSU", "LSU", "ALA", "UF")
CLEAN_INCUMBENTS = ("OSU", "TEX")


def test_override_book_covers_minimum_set() -> None:
    book = load_qb_overrides()
    assert book["present"] is True
    assert book["as_of"] == "2026-08-12"
    for team in OVERRIDE_TEAMS:
        row = override_for(team)
        assert row, team
        assert row["qb_class"] != "incumbent"
        assert row["qb_class"] in {"open_competition", "portal", "true_freshman"}


def test_does_not_invent_missing_espn_identities() -> None:
    uga = apply_qb_situation_override(
        "UGA",
        {"starter_name": "Ryan Puglisi", "starter_key": "5079679", "qb_class": "incumbent"},
    )
    assert uga["qb_class"] == "open_competition"
    assert "Stockton" not in uga["starter_name"]
    assert uga["starter_name"] == "Ryan Puglisi"

    mich = apply_qb_situation_override(
        "MICH",
        {
            "starter_name": "Brayden Fowler-Nicolosi",
            "qb_class": "incumbent",
        },
    )
    assert mich["qb_class"] == "open_competition"
    assert "Underwood" not in mich["starter_name"]


def test_fsu_lsu_align_to_espn_present_public_starters() -> None:
    fsu = apply_qb_situation_override(
        "FSU",
        {"starter_name": "Dean DeNobile", "qb_class": "incumbent"},
    )
    assert fsu["starter_name"] == "Ashton Daniels"
    assert fsu["qb_class"] == "open_competition"
    assert "DeNobile" not in fsu["starter_name"]

    lsu = apply_qb_situation_override(
        "LSU",
        {"starter_name": "Landen Clark", "qb_class": "incumbent"},
    )
    assert lsu["starter_name"] == "Sam Leavitt"
    assert lsu["qb_class"] == "open_competition"
    assert "Clark" not in lsu["starter_name"]


def test_synthetic_payload_without_loader_is_unchanged() -> None:
    """Overrides are applied at universe/prior load, not inside the primitive."""
    qb = build_qb_situation(
        "UGA",
        {
            "qb_class": "incumbent",
            "starter_name": "Test QB",
            "experience_starts": 10,
            "qb_talent": 80,
        },
    )
    assert qb.qb_class == "incumbent"
    assert qb.starter_name == "Test QB"


def test_universe_labels_are_not_false_incumbents() -> None:
    universe = build_packaged_universe(2026)
    for team in OVERRIDE_TEAMS:
        qb = universe.teams[team].qb
        assert qb is not None, team
        assert qb.qb_class != "incumbent", team
        assert qb.uncertainty > 0.35, team
        assert "override" in (qb.source or "").lower() or "override" in (qb.notes or "").lower()
    assert universe.teams["OSU"].qb.qb_class == "incumbent"
    assert universe.teams["TEX"].qb.qb_class == "incumbent"
    assert universe.teams["FSU"].qb.starter_name == "Ashton Daniels"
    assert universe.teams["LSU"].qb.starter_name == "Sam Leavitt"


def test_recomputed_prior_sigma_widens_for_overrides() -> None:
    patched = [lookup_prior(t) for t in OVERRIDE_TEAMS]
    assert all(p for p in patched)
    for row in patched:
        assert row["qb_class"] != "incumbent", row
        assert row["sigma_points"] > 5.5, row
    osu = lookup_prior("OSU")
    tex = lookup_prior("TEX")
    ball = lookup_prior("BALL")
    assert osu["qb_class"] == "incumbent"
    assert tex["qb_class"] == "incumbent"
    assert osu["sigma_points"] < 5.0
    assert tex["sigma_points"] < 5.0
    uga = lookup_prior("UGA")
    assert uga["sigma_points"] > osu["sigma_points"]
    assert ball["sigma_points"] > osu["sigma_points"]
    assert uga["mean_points"] > ball["mean_points"]


def test_project_game_still_research_only() -> None:
    universe = build_packaged_universe(2026)
    proj = project_game_preview(
        universe, home_team="UGA", away_team="BALL", week=1, neutral_site=True
    )
    payload = project_game_to_dict(proj)
    assert payload["research_prior"]["used_in_spread"] is False
    assert payload["spread_home"] == proj.spread_home
    assert payload["research_prior"]["home"]["qb_class"] != "incumbent"
    status = engine_status_payload(season=2026, demo=True)
    assert status["qb_situation_overrides"]["n"] == 6
    assert status["preseason_prior"]["used_in_spread"] is False
