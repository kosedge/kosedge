"""NBA Chapter 4 — team KEI gates."""

from __future__ import annotations

import json
from pathlib import Path

from src.services.nba_season_engine import priors as P
from src.services.nba_season_engine.nba_kei import (
    KEI_VERSION,
    LEAN_EDGE_PTS,
    PLAY_EDGE_PTS,
    compute_game_kei,
    load_kei_pack,
    tag_from_edge,
)
from src.services.nba_season_engine.situation import load_situation_coeffs

CFB_KEI = (
    Path(__file__).resolve().parents[1]
    / "src/services/cfb_season_engine/data/cfb_kei_w0_w1_2026.json"
)


def test_ch4_constants_frozen() -> None:
    assert P.TEAM_CARRY_SHRINK == 0.85
    assert P.SITUATION_TEAM_PTS_CAP == 3.0
    assert PLAY_EDGE_PTS == 4.0
    assert LEAN_EDGE_PTS == 2.5
    # Ch3 coeffs not retuned
    c = load_situation_coeffs()["coefficients"]
    assert c == {"home": 2.0, "b2b": -1.5, "travel": -0.5, "altitude": 1.0}


def test_kei_pack_present_and_not_empty() -> None:
    pack = load_kei_pack(force=True)
    assert pack["present"] is True
    assert pack["kei_version"] == KEI_VERSION
    assert pack["game_count"] == 1200
    assert len(pack["games"]) == 1200


def test_kei_not_a_copy_of_zero_and_has_wp() -> None:
    pack = load_kei_pack()
    g0 = pack["games"][0]
    assert g0["kei_spread_home"] is not None
    assert g0["kei_total"] is not None
    assert 0.02 <= float(g0["kei_home_win_prob"]) <= 0.98
    # Sanity: total in league range
    assert 200.0 <= float(g0["kei_total"]) <= 260.0


def test_compute_game_kei_matches_pack_sample() -> None:
    pack = load_kei_pack()
    sample = pack["games"][0]
    live = compute_game_kei(sample["home"], sample["away"], sample["game_id"])
    assert abs(float(live["kei_spread_home"]) - float(sample["kei_spread_home"])) < 0.05
    assert abs(float(live["kei_total"]) - float(sample["kei_total"])) < 0.05


def test_tag_pass_without_trusted_best_or_preseason() -> None:
    assert tag_from_edge(5.0, best_trusted=False) == "PASS"
    assert tag_from_edge(5.0, best_trusted=True, preseason=True) == "PASS"
    assert tag_from_edge(4.0, best_trusted=True) == "PLAY"
    assert tag_from_edge(2.5, best_trusted=True) == "LEAN"
    assert tag_from_edge(2.0, best_trusted=True) == "PASS"


def test_ortg_drtg_league_sane_on_inputs() -> None:
    pack = load_kei_pack()
    for g in pack["games"][:50]:
        inp = g["inputs"]
        assert 105.0 <= float(inp["ortg_home"]) <= 125.0
        assert 105.0 <= float(inp["drtg_home"]) <= 125.0


def test_cfb_ball_osu_untouched() -> None:
    kei = json.loads(CFB_KEI.read_text(encoding="utf-8"))
    game = next(
        g
        for g in kei["games"]
        if g.get("away") == "BALL" and g.get("home") == "OSU" and g.get("week") == 1
    )
    assert abs(float(game["kei"]["kei_spread_home"]) - (-40.51)) < 1e-9


def test_no_props_fields_on_kei_pack() -> None:
    pack = load_kei_pack()
    does_not = " ".join(pack.get("does_not") or []).lower()
    assert "props" in does_not
    for g in pack["games"][:5]:
        assert "prop" not in g
        assert "PLAY" not in g  # tags computed at board vs Best, not baked in pack
