"""NHL Chapter 6 — props dark gates (PlayerProjection desk, zero PLAY/LEAN)."""

from __future__ import annotations

import json
from pathlib import Path

from src.services.nhl_season_engine import priors as P
from src.services.nhl_season_engine.nhl_kei import load_kei_pack
from src.services.nhl_season_engine.nhl_props import (
    ODDS_BACKED_MARKETS,
    ODDS_MISSING_VECTORS,
    PROP_PLAY_ABS,
    PROP_PLAY_CAP_PER_SLATE,
    PROP_PLAY_SIGMA,
    PROP_TOI_GATE,
    PROPS_VERSION,
    STARTER_GATE,
    build_dark_props_board,
    evaluate_dark_prop,
    trust_prop_best,
    would_clear_prop_play,
)
from src.services.nhl_season_engine.player_projection import load_player_projection_pack
from src.services.nhl_season_engine.situation import load_situation_coeffs

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
CFB_KEI = ROOT / "src/services/cfb_season_engine/data/cfb_kei_w0_w1_2026.json"
NBA_PRIORS = ROOT / "src/services/nba_season_engine/priors.py"
EDGE_KEI_AVAIL = REPO / "apps/web/lib/edge-board-kei-availability.ts"


def test_ch6_constants_registered() -> None:
    assert P.NHL_TEAM_CARRY_SHRINK == 0.85
    assert P.NHL_SITUATION_GOAL_CAP == 0.35
    assert PROP_PLAY_ABS == 4.0
    assert PROP_PLAY_SIGMA == 0.6
    assert PROP_PLAY_CAP_PER_SLATE == 6
    assert PROP_TOI_GATE == 8.0
    assert STARTER_GATE == "unknown"
    assert PROPS_VERSION == "nhl-props-ch6-dark-v1"
    assert ODDS_BACKED_MARKETS == ("goals", "assists", "pts", "sog")
    assert ODDS_MISSING_VECTORS == ("SAVES",)
    c = load_situation_coeffs()["coefficients"]
    assert c == {"home": 0.1, "b2b": -0.15, "travel": -0.08, "altitude": 0.12}


def test_dark_board_reads_ch5_means_and_zero_tags() -> None:
    pack = load_player_projection_pack(force=True)
    assert pack["present"] is True
    board = build_dark_props_board(limit=40, market_key="pts")
    assert board["present"] is True
    assert board["dark_only"] is True
    assert board["count"] > 0
    assert board["play_n"] == 0
    assert board["lean_n"] == 0
    sample = next(r for r in board["lines"] if r["player_type"] == "skater")
    ch5 = (pack.get("skaters") or {}).get(f"{sample['team']}:{sample['player_id']}")
    assert ch5 is not None
    assert abs(float(sample["model_mean"]) - float(ch5["P"])) < 1e-3
    assert sample["tag"] == "PASS"
    assert "PLAY" not in str(sample)
    assert "LEAN" not in str(sample.get("tag"))


def test_goalie_starter_unknown_rows_stay_dash() -> None:
    board = build_dark_props_board(limit=80, include_goalie_dash_rows=True)
    goalies = [r for r in board["lines"] if r.get("player_type") == "goalie"]
    assert goalies
    for g in goalies:
        assert g["market_key"] == "saves"
        assert g["best"] is None
        assert g["edge"] is None
        assert g["tag"] == "PASS"
        assert g["diagnostics"]["trust_reason"] == "starter_gate_unknown"
        assert g["diagnostics"]["starter_gate"] == "unknown"


def test_missing_odds_key_not_guessed() -> None:
    board = build_dark_props_board(market_key="gaa")
    assert board["count"] == 0
    assert "missing_odds_key" in str(board.get("message") or "")


def test_zero_play_even_when_register_clears() -> None:
    edge = evaluate_dark_prop(
        market_key="goals",
        model_mean=5.0,
        model_std=0.5,
        line=0.5,
        toi=18.0,
        book_count=2,
        best_trusted=True,
    )
    assert edge["tag"] == "PASS"
    assert edge["would_clear_play"] is True  # |edge| and z clear register
    assert would_clear_prop_play(abs_edge=4.5, z=9.0) is True
    assert edge["stake_eligible"] is False


def test_trust_clears_untrusted_and_starter() -> None:
    assert trust_prop_best(best=None)["best"] is None
    assert trust_prop_best(best=2.5, starter_unknown=True)["best"] is None
    assert (
        trust_prop_best(best=12.0, model_mean=0.3, book_count=1)["reason"]
        == "absurd_vs_proj"
    )


def test_ch4_kei_untouched() -> None:
    pack = load_kei_pack(force=True)
    assert pack["present"] is True
    fla = next(
        g for g in pack["games"] if g.get("away") == "FLA" and g.get("home") == "CAR"
    )
    assert abs(float(fla["kei_puck_home"]) - (-0.94)) < 0.05
    text = EDGE_KEI_AVAIL.read_text(encoding="utf-8")
    assert '"nhl"' in text
    assert 'return sport === "nhl"' not in text


def test_nba_cfb_untouched() -> None:
    assert "TEAM_CARRY_SHRINK = 0.85" in NBA_PRIORS.read_text(encoding="utf-8")
    kei = json.loads(CFB_KEI.read_text(encoding="utf-8"))
    game = next(
        g
        for g in kei["games"]
        if g.get("away") == "BALL" and g.get("home") == "OSU" and g.get("week") == 1
    )
    assert abs(float(game["kei"]["kei_spread_home"]) - (-40.51)) < 1e-9
