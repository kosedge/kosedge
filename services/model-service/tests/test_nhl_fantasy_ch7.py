"""NHL Chapter 7 — fantasy from PlayerProjection gates."""

from __future__ import annotations

from pathlib import Path

from src.services.nba_season_engine import nba_fantasy as nba_f
from src.services.nhl_season_engine import priors as P
from src.services.nhl_season_engine.nhl_fantasy import (
    FANTASY_VERSION,
    SCORING_MAP,
    SCORING_PROFILE,
    SEASON_GAMES,
    build_fantasy_board,
    fantasy_points_from_projection,
    fantasy_points_goalie,
    fantasy_points_skater,
)
from src.services.nhl_season_engine.nhl_kei import load_kei_pack
from src.services.nhl_season_engine.nhl_props import build_dark_props_board
from src.services.nhl_season_engine.player_projection import load_player_projection_pack
from src.services.wnba_season_engine import wnba_fantasy as wnba_f

REPO = Path(__file__).resolve().parents[2]
NBA_FANTASY = (
    Path(__file__).resolve().parents[1]
    / "src/services/nba_season_engine/nba_fantasy.py"
)
WNBA_FANTASY = (
    Path(__file__).resolve().parents[1]
    / "src/services/wnba_season_engine/wnba_fantasy.py"
)


def test_ch7_scoring_map_registered() -> None:
    assert P.NHL_TEAM_CARRY_SHRINK == 0.85
    assert P.STARTER_GATE == "unknown"
    assert FANTASY_VERSION == "nhl-fantasy-ch7-v1"
    assert SCORING_PROFILE == "kos_default_points"
    assert SEASON_GAMES == 82
    assert SCORING_MAP == {
        "G": 3.0,
        "A": 2.0,
        "SOG": 0.4,
        "SAVES": 0.2,
    }


def test_fantasy_points_from_projection_formula() -> None:
    # 3*0.5 + 2*1.0 + 0.4*3.0 = 1.5 + 2.0 + 1.2 = 4.7
    assert abs(fantasy_points_skater(g=0.5, a=1.0, sog=3.0) - 4.7) < 1e-9
    assert abs(fantasy_points_goalie(saves=25.0) - 5.0) < 1e-9
    assert (
        abs(
            fantasy_points_from_projection(g=0.5, a=1.0, sog=3.0, player_type="skater")
            - 4.7
        )
        < 1e-9
    )
    assert (
        abs(
            fantasy_points_from_projection(saves=25.0, player_type="goalie") - 5.0
        )
        < 1e-9
    )


def test_box_stats_equal_ch5_fields() -> None:
    pack = load_player_projection_pack(force=True)
    board = build_fantasy_board(view="season", limit=80)
    assert board["present"] is True
    assert board["count"] > 0
    skaters = (pack.get("skaters") or {})
    goalies = (pack.get("goalies") or {})
    saw_skater = False
    saw_goalie = False
    for row in board["rows"]:
        key = f"{row['team']}:{row['player_id']}"
        if row["player_type"] == "skater":
            saw_skater = True
            ch5 = skaters.get(key)
            assert ch5 is not None
            for k in ("G", "A", "P", "SOG", "TOI_EV", "TOI_PP"):
                assert abs(float(row[k]) - float(ch5[k])) < 1e-6
            expected = fantasy_points_skater(
                g=ch5["G"], a=ch5["A"], sog=ch5["SOG"]
            )
            assert abs(float(row["fantasy_pts"]) - expected) < 1e-6
        else:
            saw_goalie = True
            ch5 = goalies.get(key)
            assert ch5 is not None
            for k in ("start_share", "SV_pct", "SA", "GAA", "SAVES"):
                assert abs(float(row[k]) - float(ch5[k])) < 1e-5
            expected = fantasy_points_goalie(saves=ch5["SAVES"])
            assert abs(float(row["fantasy_pts"]) - expected) < 1e-6
    assert saw_skater and saw_goalie


def test_goalie_start_share_still_near_one() -> None:
    board = build_fantasy_board(limit=10)
    assert board["goalie_start_share_ok"] is True
    pack = load_player_projection_pack()
    for checks in (pack.get("team_checks") or {}).values():
        assert abs(float(checks.get("sum_start_share") or 0.0) - 1.0) < 1e-6


def test_team_g_drift_inside_residual_cap() -> None:
    board = build_fantasy_board(limit=10)
    assert board["max_team_g_drift"] <= P.NHL_TEAM_REBASE_RESIDUAL_CAP
    assert board["max_team_g_drift"] < 0.01


def test_slate_same_means_sorted_by_fantasy_pts() -> None:
    season = build_fantasy_board(view="season", limit=20)
    slate = build_fantasy_board(view="slate", limit=20)
    assert season["rows"][0]["player_id"] == slate["rows"][0]["player_id"]
    fps = [float(r["fantasy_pts"]) for r in slate["rows"]]
    assert fps == sorted(fps, reverse=True)


def test_goalies_not_double_counted_as_skaters() -> None:
    board = build_fantasy_board(limit=500)
    ids = [(r["player_type"], r["team"], r["player_id"]) for r in board["rows"]]
    assert len(ids) == len(set(ids))
    for r in board["rows"]:
        if r["player_type"] == "goalie":
            assert r.get("G") is None
            assert r.get("SAVES") is not None
        else:
            assert r.get("SAVES") is None


def test_props_still_untagged() -> None:
    props = build_dark_props_board(limit=20)
    assert props["play_n"] == 0
    assert props.get("lean_n", 0) == 0
    for row in props["lines"]:
        assert row["tag"] == "PASS"


def test_kei_fla_car_unchanged() -> None:
    pack = load_kei_pack()
    game = next(
        g
        for g in pack["games"]
        if g.get("away") == "FLA" and g.get("home") == "CAR"
    )
    assert abs(float(game["kei_puck_home"]) - (-0.94)) < 1e-9
    assert abs(float(game["kei_total"]) - 6.71) < 1e-9


def test_nba_wnba_fantasy_untouched() -> None:
    assert nba_f.FANTASY_VERSION == "nba-fantasy-ch7-v1"
    assert wnba_f.FANTASY_VERSION == "wnba-fantasy-ch7-v1"
    assert NBA_FANTASY.is_file() and WNBA_FANTASY.is_file()
