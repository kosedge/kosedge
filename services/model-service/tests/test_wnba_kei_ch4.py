"""WNBA Chapter 4 — team KEI gates."""

from __future__ import annotations

import json
from pathlib import Path

from src.services.wnba_season_engine import priors as P
from src.services.wnba_season_engine.situation import load_situation_coeffs
from src.services.wnba_season_engine.wnba_kei import (
    FORBIDDEN_LEFTOVER_FAIR_LINE_GAME_IDS,
    KEI_VERSION,
    LEAN_EDGE_PTS,
    PLAY_EDGE_PTS,
    WNBA_MARGIN_SD,
    compute_game_kei,
    kei_lines_for_dates,
    load_kei_pack,
    tag_from_edge,
)

ROOT = Path(__file__).resolve().parents[1]
CFB_KEI = ROOT / "src/services/cfb_season_engine/data/cfb_kei_w0_w1_2026.json"
NBA_KEI = ROOT / "src/services/nba_season_engine/data/nba_kei_lines_ch4.json"
CH5 = (
    ROOT / "src/services/wnba_season_engine/data/wnba_player_projection_2026.json"
)
SIT = (
    ROOT / "src/services/wnba_season_engine/data/wnba_situation_coeffs_v0.json"
)


def test_ch4_constants_frozen() -> None:
    assert P.WNBA_TEAM_CARRY_SHRINK == 0.85
    assert P.SITUATION_TEAM_PTS_CAP == 3.0
    assert P.MINUTE_GRID_SUM == 200
    assert PLAY_EDGE_PTS == 4.0
    assert LEAN_EDGE_PTS == 2.5
    assert WNBA_MARGIN_SD == 11.0
    c = load_situation_coeffs()["coefficients"]
    assert c == {"home": 1.5, "b2b": -1.5, "travel": -0.5, "altitude": 0.5}
    # Disk stamp matches reader
    disk = json.loads(SIT.read_text(encoding="utf-8"))["coefficients"]
    assert disk == c


def test_kei_pack_present_and_drops_leftovers() -> None:
    pack = load_kei_pack(force=True)
    assert pack["present"] is True
    assert pack["kei_version"] == KEI_VERSION
    assert pack["game_count"] == 287
    assert len(pack["games"]) == 287
    ids = {str(g["game_id"]) for g in pack["games"]}
    assert "401857105" not in ids
    assert "401857106" not in ids
    assert pack["forbidden_leftover_fair_line_game_ids"] == list(
        FORBIDDEN_LEFTOVER_FAIR_LINE_GAME_IDS
    )


def test_con_atl_kei_filled_not_market_copy() -> None:
    pack = load_kei_pack()
    con = next(g for g in pack["games"] if str(g["game_id"]) == "401857190")
    assert con["away"] == "CON" and con["home"] == "ATL"
    assert con["kei_spread_home"] is not None
    assert abs(float(con["kei_spread_home"]) - 14.5) > 0.5
    assert abs(float(con["kei_spread_home"]) + 14.5) > 0.5
    assert 150.0 <= float(con["kei_total"]) <= 200.0
    assert 0.02 <= float(con["kei_home_win_prob"]) <= 0.98
    live = kei_lines_for_dates(game_date="2026-09-01", days_ahead=30)
    assert any(str(g["game_id"]) == "401857190" for g in live)


def test_compute_game_kei_matches_live_sample() -> None:
    pack = load_kei_pack()
    sample = next(g for g in pack["games"] if str(g["game_id"]) == "401857190")
    live = compute_game_kei(
        sample["home"],
        sample["away"],
        sample["game_id"],
        flags_home={
            "home": True,
            "b2b": False,
            "travel": False,
            "altitude": False,
        },
        flags_away={
            "home": False,
            "b2b": False,
            "travel": True,
            "altitude": False,
        },
    )
    assert abs(float(live["kei_spread_home"]) - float(sample["kei_spread_home"])) < 0.05
    assert abs(float(live["kei_total"]) - float(sample["kei_total"])) < 0.05


def test_tag_pass_without_trusted_best_or_final() -> None:
    assert tag_from_edge(5.0, best_trusted=False) == "PASS"
    assert tag_from_edge(5.0, best_trusted=True, already_final=True) == "PASS"
    assert tag_from_edge(4.0, best_trusted=True) == "PLAY"
    assert tag_from_edge(2.5, best_trusted=True) == "LEAN"
    assert tag_from_edge(2.0, best_trusted=True) == "PASS"


def test_ch5_pack_not_rematerialized() -> None:
    pack = json.loads(CH5.read_text(encoding="utf-8"))
    assert pack["object"] == "PlayerProjection"
    assert pack["player_count"] == 135
    assert pack["MINUTE_GRID_SUM"] == 200


def test_no_props_fields_on_kei_pack() -> None:
    pack = load_kei_pack()
    does_not = " ".join(pack.get("does_not") or []).lower()
    assert "props" in does_not
    for g in pack["games"][:5]:
        assert "prop" not in g
        assert "PLAY" not in g


def test_nba_hou_okc_kei_untouched() -> None:
    kei = json.loads(NBA_KEI.read_text(encoding="utf-8"))
    opener = next(g for g in kei["games"] if g.get("game_id") == "0022500001")
    assert opener["away"] == "HOU" and opener["home"] == "OKC"
    assert abs(float(opener["kei_spread_home"]) - (-4.16)) < 1e-9


def test_cfb_ball_osu_untouched() -> None:
    kei = json.loads(CFB_KEI.read_text(encoding="utf-8"))
    game = next(
        g
        for g in kei["games"]
        if g.get("away") == "BALL" and g.get("home") == "OSU" and g.get("week") == 1
    )
    assert abs(float(game["kei"]["kei_spread_home"]) - (-40.51)) < 1e-9
