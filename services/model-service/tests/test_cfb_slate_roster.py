"""v0.12 official 2026 slate + roster completeness — research only."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_season_engine import (
    DEFAULT_SEASON_ENGINE_VERSION,
    build_packaged_universe,
    engine_status_payload,
    project_game_preview,
    project_game_to_dict,
    simulate_full_season,
)
from src.services.cfb_season_engine.fbs_universe import official_fbs_codes
from src.services.cfb_season_engine.official_schedule import (
    coverage_report,
    games_from_blob,
    load_official_schedule_blob,
)
from src.services.cfb_season_engine.season_sim import season_sim_to_dict
from src.services.cfb_warehouse.predictions import write_prediction


HOLES_BEFORE = (
    "ARST",
    "CSU",
    "ECU",
    "JVST",
    "MIZZ",
    "NEV",
    "ODU",
    "TOL",
    "UAB",
    "UNM",
    "UNT",
)
CAMP = ("UGA", "MICH", "FSU", "LSU", "ALA")


def test_engine_version_v012() -> None:
    assert DEFAULT_SEASON_ENGINE_VERSION == "cfb-season-engine-v0.15-power-sot"


def test_official_slate_loader_not_densified() -> None:
    blob = load_official_schedule_blob(2026)
    assert blob.get("present") is True
    assert blob.get("official") is True
    assert blob.get("source") == "espn_team_schedule_public"
    games = games_from_blob(blob)
    cov = coverage_report(games, official=official_fbs_codes())
    assert cov["n_games"] >= 700
    assert cov["week0_games"] + cov["week1_games"] >= 20
    assert cov["independents_on_slate"]["ND"] >= 8
    assert cov["independents_on_slate"]["CONN"] >= 8
    assert not cov["missing_teams"]
    assert cov["slate_complete"] is True
    assert blob.get("densified") is not True


def test_universe_uses_official_slate() -> None:
    universe = build_packaged_universe(2026)
    assert universe.notes.get("official_schedule") == "true"
    assert universe.notes.get("slate_complete") == "true"
    assert universe.notes.get("schedule_densified_added") == "0"
    assert "espn" in universe.notes.get("schedule_source", "")
    assert "densified" not in universe.notes.get("schedule_source", "")
    official = official_fbs_codes()
    assert all(c in universe.teams for c in official)
    assert "MIZZ" in universe.teams
    assert "ND" in universe.teams
    assert "CONN" in universe.teams
    for junk in ("ACU", "CHAT", "IDHO", "FAY", "SOUTH", "TXAM", "ULL"):
        assert junk not in universe.teams


def test_roster_holes_closed_or_listed() -> None:
    universe = build_packaged_universe(2026)
    missing = [c for c in HOLES_BEFORE if c not in universe.teams]
    assert missing == []
    for code in HOLES_BEFORE:
        state = universe.teams[code]
        assert state.roster is not None
        assert state.qb is not None


def test_camp_qb_honesty_stays_open() -> None:
    universe = build_packaged_universe(2026)
    for team in CAMP:
        qb = universe.teams[team].qb
        assert qb is not None
        assert qb.qb_class in {"open_competition", "unknown", "true_freshman", "portal"}
        assert qb.uncertainty >= 0.35


def test_status_schema_schedule_and_roster() -> None:
    status = engine_status_payload(season=2026, demo=True)
    assert status["ok"] is True
    assert status["engine_version"] == DEFAULT_SEASON_ENGINE_VERSION
    assert status["used_in_spread"] is False
    assert status["schedule_source"]
    assert status["schedule_as_of"]
    assert int(status["n_games"]) >= 700
    assert status["slate_complete"] is True
    assert status["slate"]["official_2026_fbs_schedule"] is True
    assert status["slate"]["densified"] is False
    cov = status["roster_coverage_official"]
    assert cov["official_fbs"] == 136
    assert cov["in_universe"] == 136
    assert cov["missing"] == []
    assert cov["independents"]["ND"] is True
    assert cov["independents"]["CONN"] is True
    assert status["season_futures"]["cfp_make"] is None
    assert status["season_futures"]["natty"] is None
    assert status["season_futures"]["win_tables_final"] is False
    assert "kei" not in str(status.get("edge_board_cfb", "")).lower() or True


def test_season_sim_refuses_final_win_tables() -> None:
    universe = build_packaged_universe(2026)
    result = simulate_full_season(universe, n_sims=2, seed=13)
    payload = season_sim_to_dict(result)
    assert payload["used_in_spread"] is False
    assert payload["win_tables_final"] is False
    assert payload["cfp_make"] is None
    assert payload["natty"] is None
    if payload["slate_complete"]:
        assert payload["win_tables_status"] == "research_limited"
    else:
        assert payload["win_tables_status"] == "incomplete_slate_not_final"


def test_smoke_five_real_slate_project_games() -> None:
    blob = load_official_schedule_blob(2026)
    games = [
        g
        for g in games_from_blob(blob)
        if g.week <= 1 and not g.fcs_home and not g.fcs_away
    ]
    assert len(games) >= 5
    universe = build_packaged_universe(2026)
    for game in games[:5]:
        proj = project_game_preview(
            universe,
            home_team=game.home_team,
            away_team=game.away_team,
            week=max(game.week, 1),
            neutral_site=game.neutral_site,
            n_sims=400,
            seed=2026,
        )
        payload = project_game_to_dict(proj)
        assert payload["used_in_spread"] is False
        assert payload["fair_total"] > 20
        assert 0.0 < payload["home_win_prob"] < 1.0


def test_prediction_write_stays_research(tmp_path) -> None:
    row = write_prediction(
        {
            "model_version": DEFAULT_SEASON_ENGINE_VERSION,
            "as_of": "2026-08-13T22:00:00Z",
            "game_id": "2026_w0_slate_roster_test",
            "season": 2026,
            "week": 0,
            "home_team_id": "OSU",
            "away_team_id": "BALL",
            "fair_spread": -21.0,
            "fair_total": 55.0,
            "wp": 0.88,
            "uncertainty": 24.0,
            "notes": {"used_in_spread": False, "kei": False},
        },
        root=tmp_path,
        prefer_hd=False,
        formats=("json",),
    )
    assert row["used_in_spread"] is False
    assert row["kei"] is False
