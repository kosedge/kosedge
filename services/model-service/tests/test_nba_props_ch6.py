"""NBA Chapter 6 — props dark gates (PlayerProjection desk, zero PLAY)."""

from __future__ import annotations

import json
from pathlib import Path

from src.services.nba_season_engine import priors as P
from src.services.nba_season_engine.nba_props import (
    PROP_MINUTES_GATE,
    PROP_PLAY_ABS,
    PROP_PLAY_CAP_PER_SLATE,
    PROP_PLAY_SIGMA,
    PROPS_VERSION,
    build_dark_props_board,
    evaluate_dark_prop,
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


def test_dark_board_reads_player_projection_means() -> None:
    pack = load_player_projection_pack(force=True)
    assert pack["present"] is True
    board = build_dark_props_board(limit=40, market_key="pts")
    assert board["present"] is True
    assert board["dark_only"] is True
    assert board["count"] > 0
    assert board["play_n"] == 0
    # Means match Ch5 for a known player
    sample = next(r for r in board["lines"] if r["player_id"])
    ch5 = (pack.get("players") or {}).get(f"{sample['team']}:{sample['player_id']}")
    assert ch5 is not None
    assert abs(float(sample["model_mean"]) - float(ch5["PTS"])) < 1e-3


def test_zero_play_even_when_abs_edge_clears_register() -> None:
    # Huge gap vs line would clear PROP_PLAY register — still PASS in dark.
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
    assert would_clear_prop_play(abs_edge=11.5, z=2.875) is True


def test_minutes_gate_omits_bench() -> None:
    board = build_dark_props_board(limit=5000)
    for row in board["lines"]:
        assert float((row.get("diagnostics") or {}).get("minutes") or 0) >= PROP_MINUTES_GATE


def test_proj_vs_line_when_market_joined() -> None:
    pack = load_player_projection_pack()
    _key, player = next(iter((pack.get("players") or {}).items()))
    pid = player["player_id"]
    pname = player["player_name"]
    mean = float(player["PTS"])
    board = build_dark_props_board(
        market_key="pts",
        limit=50,
        market_by_player={
            (pid.lower(), "pts"): {"line": mean - 5.0, "over_price": -110, "under_price": -110},
            (pname.lower(), "pts"): {"line": mean - 5.0, "over_price": -110, "under_price": -110},
        },
        best_trusted=True,
    )
    hit = next(r for r in board["lines"] if r["player_id"] == pid and r["market_key"] == "pts")
    assert hit["line"] is not None
    assert abs(float(hit["model_mean"]) - mean) < 1e-6
    assert hit["tag"] == "PASS"
    assert hit["diagnostics"]["tag"] == "PASS"
    assert board["play_n"] == 0


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
