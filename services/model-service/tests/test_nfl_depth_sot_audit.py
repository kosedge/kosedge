"""Go-mode Gate A: 32/32 depth+coaching SoT, no silent demo fill."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.nfl_season_engine.coaching_staff import (
    load_packaged_coaching_staff,
    packaged_depth_intel_rows,
)
from src.services.nfl_season_engine.continuity_score import fetch_current_qb1
from src.services.nfl_season_engine.loaders import (
    NFL_TEAMS,
    ROSTER_SOURCE_DEMO,
    ROSTER_SOURCE_PACKAGED,
    _ensure_team_rosters,
    build_packaged_real_universe,
    load_packaged_depth_chart,
    resolve_season_universe,
)
from src.services.nfl_season_engine import project_game_player_boxes

SKILL = ("QB", "RB", "WR", "TE")


def _starters(rows):
    by = {}
    for r in rows:
        key = (r["team"], r["position"])
        cur = by.get(key)
        if cur is None or int(r["depth_order"]) < int(cur["depth_order"]):
            by[key] = r
    return by


def test_pack_covers_32_named_skill_starters() -> None:
    rows, meta = load_packaged_depth_chart(2026)
    assert meta["roster_source"] == ROSTER_SOURCE_PACKAGED
    starters = _starters(rows)
    missing = [
        f"{team}-{pos}"
        for team in NFL_TEAMS
        for pos in SKILL
        if (team, pos) not in starters or not starters[(team, pos)].get("player_name")
    ]
    assert missing == []
    assert len({r["team"] for r in rows}) == 32


def test_coaching_covers_32_named_hc() -> None:
    book, meta = load_packaged_coaching_staff(2026)
    assert meta["coaching_named_hc_count"] == 32
    assert not meta["coaching_holes"]
    assert "TB" in (meta.get("coaching_thin_dc") or [])
    assert book["TB"]["hc_name"]
    assert not book["TB"].get("dc_name")


def test_known_conflicts_match_desk() -> None:
    rows, _ = load_packaged_depth_chart(2026)
    starters = _starters([r for r in rows if r["position"] == "QB"])
    assert starters[("MIN", "QB")]["player_name"] == "Kyler Murray"
    assert starters[("ARI", "QB")]["player_name"] == "Jacoby Brissett"
    assert starters[("ATL", "QB")]["player_name"] == "Tua Tagovailoa"
    assert starters[("MIA", "QB")]["player_name"] == "Malik Willis"
    assert starters[("WAS", "QB")]["player_name"] == "Jayden Daniels"
    assert starters[("KC", "QB")]["player_name"] == "Patrick Mahomes"
    assert starters[("SF", "QB")]["player_name"] == "Brock Purdy"

    kyler = [r for r in rows if r["player_name"] == "Kyler Murray"]
    assert len(kyler) == 1 and kyler[0]["team"] == "MIN"
    tua = [r for r in rows if r["player_name"] == "Tua Tagovailoa"]
    assert len(tua) == 1 and tua[0]["team"] == "ATL"
    willis = [r for r in rows if r["player_name"] == "Malik Willis"]
    assert len(willis) == 1 and willis[0]["team"] == "MIA"

    atl_qbs = sorted(
        [r for r in rows if r["team"] == "ATL" and r["position"] == "QB"],
        key=lambda r: int(r["depth_order"]),
    )
    assert atl_qbs[0]["competition_status"] == "open_competition"
    assert atl_qbs[1]["player_name"] == "Michael Penix Jr."
    cle_qbs = sorted(
        [r for r in rows if r["team"] == "CLE" and r["position"] == "QB"],
        key=lambda r: int(r["depth_order"]),
    )
    assert cle_qbs[0]["competition_status"] == "open_competition"
    assert cle_qbs[1]["player_name"] == "Shedeur Sanders"


def test_no_demo_fill_when_pack_present() -> None:
    universe, meta = resolve_season_universe(season=2026, demo=False, session=None)
    assert meta["roster_source"] == ROSTER_SOURCE_PACKAGED
    assert universe.notes.get("demo_depth_fill") == "blocked_pack_present"
    assert universe.notes.get("depth_team_holes") == []
    fake = [f"{t} QB1" for t in NFL_TEAMS]
    names = [r.player_name for roles in universe.rosters.values() for r in roles]
    assert not any(n in fake for n in names)
    assert all(universe.rosters.get(t) for t in NFL_TEAMS)


def test_ensure_team_rosters_fail_closed_without_demo() -> None:
    empty: dict = {}
    holes = _ensure_team_rosters(empty, allow_demo_fill=False)
    assert set(holes) == set(NFL_TEAMS)
    assert empty["MIN"] == []
    filled: dict = {}
    _ensure_team_rosters(filled, allow_demo_fill=True)
    assert filled["MIN"]
    assert filled["MIN"][0].source.startswith(ROSTER_SOURCE_DEMO)


def test_engine_intel_continuity_agree_on_min() -> None:
    universe = build_packaged_real_universe(2026)
    min_qb1 = next(
        r for r in universe.rosters["MIN"] if r.position == "QB" and r.depth_order == 1
    )
    assert min_qb1.player_name == "Kyler Murray"
    intel, meta = packaged_depth_intel_rows(season=2026, week=1, team="MIN")
    assert meta["roster_source"] == ROSTER_SOURCE_PACKAGED
    intel_qb1 = next(
        r for r in intel if r["position"] == "QB" and int(r["depth_order"]) == 1
    )
    assert intel_qb1["player_name"] == min_qb1.player_name
    qb1_map = fetch_current_qb1(None, season=2026, as_of_week=1)
    assert qb1_map["MIN"][1] == "Kyler Murray"
    assert qb1_map["ATL"][1] == "Tua Tagovailoa"
    assert qb1_map["MIA"][1] == "Malik Willis"


def test_was_skill_and_ol_flashpoints_still_in_pack() -> None:
    rows, meta = load_packaged_depth_chart(2026)
    wr = sorted(
        [r for r in rows if r["team"] == "WAS" and r["position"] == "WR"],
        key=lambda r: int(r["depth_order"]),
    )
    te = sorted(
        [r for r in rows if r["team"] == "WAS" and r["position"] == "TE"],
        key=lambda r: int(r["depth_order"]),
    )
    assert wr[0]["player_name"] == "Terry McLaurin"
    assert wr[1]["player_name"] == "Stefon Diggs"
    assert te[2]["player_name"] == "John Bates"
    assert te[2].get("injury_status") == "out"
    ol = meta.get("ol_roles") or []
    tunsil = next(r for r in ol if r.get("player_name") == "Laremy Tunsil")
    assert tunsil.get("injury_status") == "out"
    fano = next(r for r in ol if r.get("player_name") == "Spencer Fano")
    assert fano["team"] == "CLE"


def test_smoke_min_box_uses_pack_qb1() -> None:
    universe = build_packaged_real_universe(2026)
    min_game = next(g for g in universe.schedule if "MIN" in {g.home_team, g.away_team})
    proj = project_game_player_boxes(
        universe,
        home_team=min_game.home_team,
        away_team=min_game.away_team,
        week=int(min_game.week),
        n_replicates=24,
        seed=13,
    )
    min_players = [p for p in proj.players if p.get("team") == "MIN"]
    qb = next(
        p
        for p in min_players
        if p.get("usage_role") == "QB1" or p.get("position") == "QB"
    )
    assert qb["player_name"] == "Kyler Murray"
    assert proj.notes.get("schedule_match") == "on_loaded_schedule"


def test_demo_true_still_allowed_for_tests() -> None:
    universe, meta = resolve_season_universe(season=2026, demo=True, session=None)
    assert meta["roster_source"] == ROSTER_SOURCE_DEMO
