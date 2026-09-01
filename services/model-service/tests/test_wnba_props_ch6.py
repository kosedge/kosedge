"""WNBA Chapter 6 — props dark gates (PlayerProjection desk, zero PLAY/LEAN)."""

from __future__ import annotations

import json
from pathlib import Path

from src.services.wnba_publish_policy import board_publish_posture
from src.services.wnba_season_engine import priors as P
from src.services.wnba_season_engine.player_projection import load_player_projection_pack
from src.services.wnba_season_engine.situation import load_situation_coeffs
from src.services.wnba_season_engine.wnba_kei import load_kei_pack
from src.services.wnba_season_engine.wnba_props import (
    ODDS_BACKED_MARKETS,
    ODDS_MISSING_VECTORS,
    PROP_MINUTES_GATE,
    PROP_PLAY_ABS,
    PROP_PLAY_CAP_PER_SLATE,
    PROP_PLAY_SIGMA,
    PROPS_VERSION,
    build_dark_props_board,
    evaluate_dark_prop,
    trust_prop_best,
    would_clear_prop_play,
)

ROOT = Path(__file__).resolve().parents[1]
CFB_KEI = ROOT / "src/services/cfb_season_engine/data/cfb_kei_w0_w1_2026.json"
NBA_KEI = ROOT / "src/services/nba_season_engine/data/nba_kei_lines_ch4.json"


def test_ch6_constants_registered() -> None:
    assert P.WNBA_TEAM_CARRY_SHRINK == 0.85
    assert P.MINUTE_GRID_SUM == 200
    assert PROP_PLAY_ABS == 4.0
    assert PROP_PLAY_SIGMA == 0.6
    assert PROP_PLAY_CAP_PER_SLATE == 4
    assert PROP_MINUTES_GATE == 10.0
    assert PROPS_VERSION == "wnba-props-ch6-dark-v1"
    assert ODDS_BACKED_MARKETS == ("pts", "reb", "ast", "threes")
    assert "PRA" in ODDS_MISSING_VECTORS
    assert "PR" in ODDS_MISSING_VECTORS
    assert "RA" in ODDS_MISSING_VECTORS
    # Ch3 coeffs frozen
    c = load_situation_coeffs()["coefficients"]
    assert c == {"home": 1.5, "b2b": -1.5, "travel": -0.5, "altitude": 0.5}


def test_dark_board_reads_player_projection_means() -> None:
    pack = load_player_projection_pack(force=True)
    assert pack["present"] is True
    board = build_dark_props_board(limit=40, market_key="pts")
    assert board["present"] is True
    assert board["dark_only"] is True
    assert board["count"] > 0
    assert board["play_n"] == 0
    assert board["lean_n"] == 0
    sample = next(r for r in board["lines"] if r["player_id"])
    ch5 = (pack.get("players") or {}).get(f"{sample['team']}:{sample['player_id']}")
    assert ch5 is not None
    assert abs(float(sample["model_mean"]) - float(ch5["PTS"])) < 1e-3
    assert sample["tag"] == "PASS"
    assert sample["tag"] not in {"PLAY", "LEAN"}
    assert sample.get("tag_side") is None


def test_missing_odds_key_pra_pr_ra_not_guessed() -> None:
    for mk in ("pra", "pr", "ra"):
        board = build_dark_props_board(market_key=mk)
        assert board["count"] == 0
        assert "missing_odds_key" in str(board.get("message") or "")


def test_zero_play_and_lean_even_when_register_clears() -> None:
    edge = evaluate_dark_prop(
        market_key="pts",
        model_mean=22.0,
        model_std=3.0,
        line=12.5,
        minutes=32.0,
        best_trusted=True,
    )
    assert edge["tag"] == "PASS"
    assert edge["dark_only"] is True
    assert edge["would_clear_play"] is True
    assert edge["stake_eligible"] is False
    assert edge["edge"] == 9.5
    assert would_clear_prop_play(abs_edge=9.5, z=9.5 / 3.0) is True


def test_untrusted_best_cleared_to_none() -> None:
    trust = trust_prop_best(best=None)
    assert trust["trusted"] is False
    assert trust["best"] is None
    edge = evaluate_dark_prop(
        market_key="pts",
        model_mean=18.0,
        model_std=3.0,
        line=None,
        minutes=30.0,
    )
    assert edge["best"] is None
    assert edge["edge"] is None
    absurd = evaluate_dark_prop(
        market_key="pts",
        model_mean=18.0,
        model_std=3.0,
        line=55.0,
        minutes=30.0,
    )
    assert absurd["best"] is None
    assert absurd["edge"] is None


def test_proj_vs_trusted_best_edge() -> None:
    pack = load_player_projection_pack()
    _key, player = next(iter((pack.get("players") or {}).items()))
    pid = player["player_id"]
    pname = player["player_name"]
    mean = float(player["PTS"])
    best = mean - 5.0
    board = build_dark_props_board(
        market_key="pts",
        limit=50,
        market_by_player={
            (pid.lower(), "pts"): {
                "line": best,
                "over_price": -110,
                "under_price": -110,
                "book_count": 2,
            },
            (pname.lower(), "pts"): {
                "line": best,
                "over_price": -110,
                "under_price": -110,
                "book_count": 2,
            },
        },
        best_trusted=True,
    )
    hit = next(
        r for r in board["lines"] if r["player_id"] == pid and r["market_key"] == "pts"
    )
    assert hit["best"] is not None
    assert abs(float(hit["model_mean"]) - mean) < 1e-3
    assert abs(float(hit["edge"]) - 5.0) < 1e-2
    assert hit["tag"] == "PASS"
    assert board["play_n"] == 0
    assert board["lean_n"] == 0


def test_minutes_gate_omits_bench() -> None:
    board = build_dark_props_board(limit=5000)
    for row in board["lines"]:
        assert float((row.get("diagnostics") or {}).get("minutes") or 0) >= PROP_MINUTES_GATE


def test_publish_posture_props_dark() -> None:
    posture = board_publish_posture()
    assert posture["props"] == "dark"
    assert posture["props_dark_only"] is True


def test_ch4_con_atl_kei_unchanged() -> None:
    pack = load_kei_pack(force=True)
    con = next(g for g in pack["games"] if str(g["game_id"]) == "401857190")
    assert con["away"] == "CON" and con["home"] == "ATL"
    assert abs(float(con["kei_spread_home"]) - (-8.49)) < 0.05
    ids = {str(g["game_id"]) for g in pack["games"]}
    assert "401857105" not in ids
    assert "401857106" not in ids


def test_nba_hou_okc_kei_untouched() -> None:
    kei = json.loads(NBA_KEI.read_text(encoding="utf-8"))
    opener = next(g for g in kei["games"] if g.get("game_id") == "0022500001")
    assert abs(float(opener["kei_spread_home"]) - (-4.16)) < 1e-9


def test_cfb_ball_osu_untouched() -> None:
    kei = json.loads(CFB_KEI.read_text(encoding="utf-8"))
    game = next(
        g
        for g in kei["games"]
        if g.get("away") == "BALL" and g.get("home") == "OSU" and g.get("week") == 1
    )
    assert abs(float(game["kei"]["kei_spread_home"]) - (-40.51)) < 1e-9
