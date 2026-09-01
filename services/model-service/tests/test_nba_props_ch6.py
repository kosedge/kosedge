"""NBA Chapter 6 — props dark gates (PlayerProjection desk, zero PLAY/LEAN)."""

from __future__ import annotations

import json
from pathlib import Path

from src.services.nba_season_engine import priors as P
from src.services.nba_season_engine.nba_props import (
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
from src.services.nba_season_engine.player_projection import load_player_projection_pack
from src.services.nba_publish_policy import board_publish_posture

CFB_KEI = (
    Path(__file__).resolve().parents[1]
    / "src/services/cfb_season_engine/data/cfb_kei_w0_w1_2026.json"
)


def test_ch6_constants_registered() -> None:
    assert P.TEAM_CARRY_SHRINK == 0.85
    assert PROP_PLAY_ABS == 4.0
    assert PROP_PLAY_SIGMA == 0.6
    assert PROP_PLAY_CAP_PER_SLATE == 8
    assert PROP_MINUTES_GATE == 12.0
    assert PROPS_VERSION == "nba-props-ch6-dark-v1"
    assert ODDS_BACKED_MARKETS == ("pts", "reb", "ast", "threes", "pra")
    assert ODDS_MISSING_VECTORS == ("PR", "RA")


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


def test_pra_market_from_ch5_when_odds_backed() -> None:
    pack = load_player_projection_pack()
    board = build_dark_props_board(limit=20, market_key="pra")
    assert board["count"] > 0
    sample = board["lines"][0]
    ch5 = (pack.get("players") or {}).get(f"{sample['team']}:{sample['player_id']}")
    assert abs(float(sample["model_mean"]) - float(ch5["PRA"])) < 1e-3


def test_missing_odds_key_pr_ra_not_guessed() -> None:
    board = build_dark_props_board(market_key="pr")
    assert board["count"] == 0
    assert "missing_odds_key" in str(board.get("message") or "")
    board_ra = build_dark_props_board(market_key="ra")
    assert board_ra["count"] == 0


def test_zero_play_and_lean_even_when_register_clears() -> None:
    edge = evaluate_dark_prop(
        market_key="pts",
        model_mean=30.0,
        model_std=4.0,
        line=18.5,
        minutes=34.0,
        best_trusted=True,
    )
    assert edge["tag"] == "PASS"
    assert edge["dark_only"] is True
    assert edge["would_clear_play"] is True
    assert edge["stake_eligible"] is False
    assert edge["edge"] == 11.5  # 30 − 18.5
    assert would_clear_prop_play(abs_edge=11.5, z=2.875) is True


def test_untrusted_best_cleared_to_none() -> None:
    trust = trust_prop_best(best=None)
    assert trust["trusted"] is False
    assert trust["best"] is None
    edge = evaluate_dark_prop(
        market_key="pts",
        model_mean=25.0,
        model_std=4.0,
        line=None,
        minutes=34.0,
    )
    assert edge["best"] is None
    assert edge["edge"] is None
    # Absurd book → cleared
    absurd = evaluate_dark_prop(
        market_key="pts",
        model_mean=25.0,
        model_std=4.0,
        line=90.0,
        minutes=34.0,
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
    hit = next(r for r in board["lines"] if r["player_id"] == pid and r["market_key"] == "pts")
    assert hit["best"] is not None
    assert abs(float(hit["model_mean"]) - mean) < 1e-6
    assert abs(float(hit["edge"]) - 5.0) < 1e-3
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


def test_cfb_ball_osu_untouched() -> None:
    kei = json.loads(CFB_KEI.read_text(encoding="utf-8"))
    game = next(
        g
        for g in kei["games"]
        if g.get("away") == "BALL" and g.get("home") == "OSU" and g.get("week") == 1
    )
    assert abs(float(game["kei"]["kei_spread_home"]) - (-40.51)) < 1e-9
