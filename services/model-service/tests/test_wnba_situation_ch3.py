"""WNBA Chapter 3 — situation class gates (apply-on-read)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from src.services.wnba_season_engine import priors as P
from src.services.wnba_season_engine.situation import (
    apply_situation_player_projections,
    apply_situation_team_line,
    load_paper_sim,
    load_schedule_pack,
    load_situation_coeffs,
    load_venue_flags,
    situation_delta_pts,
)

ROOT = Path(__file__).resolve().parents[1]
CFB_KEI = ROOT / "src/services/cfb_season_engine/data/cfb_kei_w0_w1_2026.json"
NBA_KEI = ROOT / "src/services/nba_season_engine/data/nba_kei_lines_ch4.json"
NBA_COEFFS = (
    ROOT / "src/services/nba_season_engine/data/nba_situation_coeffs_v0.json"
)
SITUATION_PY = ROOT / "src/services/wnba_season_engine/situation.py"
BUILDER_PY = Path(__file__).resolve().parents[3] / "scripts/wnba/build_situation_ch3.py"
CH5 = (
    ROOT
    / "src/services/wnba_season_engine/data/wnba_player_projection_2026.json"
)


def test_ch3_constants_shrink_and_grid_untouched() -> None:
    assert P.WNBA_TEAM_CARRY_SHRINK == 0.85
    assert P.WNBA_TEAM_REBASE_RESIDUAL_CAP == 3.0
    assert P.MINUTE_GRID_SUM == 200
    assert P.SITUATION_TEAM_PTS_CAP == 3.0
    assert not hasattr(P, "TEAM_CARRY_SHRINK")
    coeffs = load_situation_coeffs()
    assert coeffs["present"] is True
    assert coeffs["SITUATION_TEAM_PTS_CAP"] == 3.0
    assert coeffs["WNBA_TEAM_CARRY_SHRINK_unchanged"] == 0.85
    assert coeffs["MINUTE_GRID_SUM_unchanged"] == 200
    c = coeffs["coefficients"]
    assert set(c) == {"home", "b2b", "travel", "altitude"}


def test_paper_sim_chose_before_write_not_nba_copy() -> None:
    paper = load_paper_sim()
    coeffs = load_situation_coeffs()
    assert paper["present"] is True
    assert paper["chosen"] == coeffs["coefficients"]
    assert paper["SITUATION_TEAM_PTS_CAP"] == 3.0
    low, high = P.PPG_BAND_AFTER_SITUATION
    assert paper["ppg_adj_range"][0] >= low
    assert paper["ppg_adj_range"][1] <= high
    # Must not be a byte-copy of NBA registered coeffs.
    nba = json.loads(NBA_COEFFS.read_text(encoding="utf-8"))["coefficients"]
    assert coeffs["coefficients"] != nba


def test_schedule_and_venue_flags() -> None:
    sched = load_schedule_pack()
    venue = load_venue_flags()
    assert sched["game_count"] == 286
    assert sched["team_game_count"] == 572
    assert isinstance(venue["altitude_venues"], list)
    # v0: no WNBA altitude venues registered
    assert venue["altitude_venues"] == []


def test_altitude_is_venue_not_team_if() -> None:
    text = SITUATION_PY.read_text(encoding="utf-8") + BUILDER_PY.read_text(
        encoding="utf-8"
    )
    assert not re.search(r'if\s+.*\bteam\b.*==\s*[\'"]LAS[\'"]', text)
    assert not re.search(r'if\s+.*\bteam\b.*==\s*[\'"]PHX[\'"]', text)
    assert "altitude_venues" in load_venue_flags()


def test_apply_on_read_team_line_within_cap() -> None:
    sched = load_schedule_pack()
    row = next(
        (
            r
            for r in sched["team_games"]
            if r["home"] and r["b2b"] and r["travel"]
        ),
        sched["team_games"][0],
    )
    line = apply_situation_team_line(row["team"], row["game_id"], flags=row)
    assert line["situation_applied"] is True
    assert abs(line["delta_pts"]) <= P.SITUATION_TEAM_PTS_CAP + 1e-9
    assert line["within_residual_cap"] is True
    low, high = P.PPG_BAND_AFTER_SITUATION
    assert low <= line["implied_ppg"] <= high
    # ORtg/DRtg unchanged (situation is points Δ, not a second net prior)
    assert line["ortg"] > 90.0
    assert line["drtg"] > 90.0


def test_player_copy_through_keeps_pts_identity() -> None:
    sched = load_schedule_pack()
    row = next(
        r for r in sched["team_games"] if r["home"] or r["b2b"] or r["travel"]
    )
    out = apply_situation_player_projections(row["team"], row["game_id"], flags=row)
    assert out["present"] is True
    assert out["within_residual_cap"] is True
    assert out["pts_drift"] <= P.WNBA_TEAM_REBASE_RESIDUAL_CAP + 1e-6
    assert abs(sum(p["MIN"] for p in out["players"]) - 200.0) < 1e-3
    if abs(out["team_line"]["delta_pts"]) > 1e-12:
        assert out["copy_through"] is True
        assert abs(out["sum_pts"] - out["target_pts"]) <= 1e-3


def test_delta_clip_enforced() -> None:
    # Sum must exceed ±cap so clip fires (canceling ±5 cancels to 0).
    flags = {"home": True, "b2b": True, "travel": True, "altitude": True}
    adj = situation_delta_pts(
        flags, coeffs={"home": 5.0, "b2b": -0.5, "travel": -0.5, "altitude": 5.0}
    )
    assert abs(adj["delta_pts"]) <= P.SITUATION_TEAM_PTS_CAP + 1e-9
    assert adj["clipped"] is True
    assert abs(adj["raw"]) > P.SITUATION_TEAM_PTS_CAP


def test_ch5_pack_not_rewritten_by_ch3() -> None:
    pack = json.loads(CH5.read_text(encoding="utf-8"))
    assert pack["object"] == "PlayerProjection"
    assert pack["player_count"] == 135
    assert pack["MINUTE_GRID_SUM"] == 200


def test_leftover_fair_lines_not_blended() -> None:
    coeffs = load_situation_coeffs()
    assert coeffs["forbidden_leftover_fair_line_game_ids"] == [
        "401857105",
        "401857106",
    ]


def test_cfb_ball_osu_kei_untouched() -> None:
    kei = json.loads(CFB_KEI.read_text(encoding="utf-8"))
    game = next(
        g
        for g in kei["games"]
        if g.get("away") == "BALL" and g.get("home") == "OSU" and g.get("week") == 1
    )
    assert abs(float(game["kei"]["kei_spread_home"]) - (-40.51)) < 1e-9


def test_nba_hou_okc_kei_untouched() -> None:
    kei = json.loads(NBA_KEI.read_text(encoding="utf-8"))
    opener = next(g for g in kei["games"] if g.get("game_id") == "0022500001")
    assert opener["away"] == "HOU" and opener["home"] == "OKC"
    assert abs(float(opener["kei_spread_home"]) - (-4.16)) < 1e-9
