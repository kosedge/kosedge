"""WNBA Chapter 7 — fantasy from PlayerProjection gates."""

from __future__ import annotations

import json
from pathlib import Path

from src.services.wnba_season_engine import priors as P
from src.services.wnba_season_engine.player_projection import load_player_projection_pack
from src.services.wnba_season_engine.wnba_fantasy import (
    FANTASY_VERSION,
    SCORING_MAP,
    SCORING_PROFILE,
    SEASON_GAMES,
    build_fantasy_board,
    fantasy_points_from_projection,
)
from src.services.wnba_season_engine.wnba_props import build_dark_props_board

ROOT = Path(__file__).resolve().parents[1]
CFB_KEI = ROOT / "src/services/cfb_season_engine/data/cfb_kei_w0_w1_2026.json"
NBA_FANTASY = (
    ROOT / "src/services/nba_season_engine/nba_fantasy.py"
)


def test_ch7_scoring_map_registered() -> None:
    assert P.WNBA_TEAM_CARRY_SHRINK == 0.85
    assert P.MINUTE_GRID_SUM == 200
    assert FANTASY_VERSION == "wnba-fantasy-ch7-v1"
    assert SCORING_PROFILE == "kos_default_points"
    assert SEASON_GAMES == 40
    assert SCORING_MAP == {
        "PTS": 1.0,
        "REB": 1.2,
        "AST": 1.5,
        "STL": 3.0,
        "BLK": 3.0,
        "TOV": -1.0,
        "3PM": 0.5,
    }


def test_fantasy_points_from_projection_formula() -> None:
    fp = fantasy_points_from_projection(
        pts=20, reb=10, ast=5, stl=1, blk=1, tov=2, threes=2
    )
    # 20 + 12 + 7.5 + 3 + 3 - 2 + 1 = 44.5
    assert abs(fp - 44.5) < 1e-9


def test_box_stats_equal_ch5_fields() -> None:
    pack = load_player_projection_pack(force=True)
    board = build_fantasy_board(view="season", limit=50)
    assert board["present"] is True
    assert board["count"] > 0
    for row in board["rows"]:
        ch5 = (pack.get("players") or {}).get(f"{row['team']}:{row['player_id']}")
        assert ch5 is not None
        for key in ("PTS", "REB", "AST", "STL", "BLK", "TOV", "3PM", "MIN"):
            assert abs(float(row[key]) - float(ch5[key])) < 1e-6
        expected = fantasy_points_from_projection(
            pts=ch5["PTS"],
            reb=ch5["REB"],
            ast=ch5["AST"],
            stl=ch5["STL"],
            blk=ch5["BLK"],
            tov=ch5["TOV"],
            threes=ch5["3PM"],
        )
        assert abs(float(row["fantasy_pts"]) - expected) < 1e-6
        assert abs(float(row["season_fantasy_pts"]) - expected * SEASON_GAMES) < 1e-2


def test_minute_grid_and_pts_drift() -> None:
    board = build_fantasy_board(limit=10)
    assert board["MINUTE_GRID_SUM_unchanged"] == 200
    assert board["minute_grid_ok"] is True
    assert board["max_team_pts_drift"] <= P.WNBA_TEAM_REBASE_RESIDUAL_CAP
    assert board["max_team_pts_drift"] < 0.01


def test_slate_same_means_sorted_by_fantasy_pts() -> None:
    season = build_fantasy_board(view="season", limit=20)
    slate = build_fantasy_board(view="slate", limit=20)
    assert season["rows"][0]["player_id"] == slate["rows"][0]["player_id"]
    fps = [float(r["fantasy_pts"]) for r in slate["rows"]]
    assert fps == sorted(fps, reverse=True)


def test_props_still_untagged() -> None:
    props = build_dark_props_board(limit=20)
    assert props["play_n"] == 0
    assert props.get("lean_n", 0) == 0
    for row in props["lines"]:
        assert row["tag"] == "PASS"


def test_nba_fantasy_module_untouched() -> None:
    text = NBA_FANTASY.read_text(encoding="utf-8")
    assert 'FANTASY_VERSION = "nba-fantasy-ch7-v1"' in text
    assert "SEASON_GAMES = 82" in text


def test_cfb_ball_osu_untouched() -> None:
    kei = json.loads(CFB_KEI.read_text(encoding="utf-8"))
    game = next(
        g
        for g in kei["games"]
        if g.get("away") == "BALL" and g.get("home") == "OSU" and g.get("week") == 1
    )
    assert abs(float(game["kei"]["kei_spread_home"]) - (-40.51)) < 1e-9
