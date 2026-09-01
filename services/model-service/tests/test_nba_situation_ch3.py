"""NBA Chapter 3 — situation class gates (apply-on-read)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from src.services.nba_season_engine import priors as P
from src.services.nba_season_engine.situation import (
    apply_situation_player_projections,
    apply_situation_team_line,
    load_paper_sim,
    load_schedule_pack,
    load_situation_coeffs,
    load_venue_flags,
    situation_delta_pts,
)

CFB_KEI = (
    Path(__file__).resolve().parents[1]
    / "src/services/cfb_season_engine/data/cfb_kei_w0_w1_2026.json"
)
SITUATION_PY = (
    Path(__file__).resolve().parents[1]
    / "src/services/nba_season_engine/situation.py"
)
BUILDER_PY = (
    Path(__file__).resolve().parents[3] / "scripts/nba/build_situation_ch3.py"
)


def test_ch3_constants_shrink_untouched() -> None:
    assert P.TEAM_CARRY_SHRINK == 0.85
    assert P.TEAM_REBASE_RESIDUAL_CAP == 3.0
    assert P.SITUATION_TEAM_PTS_CAP == 3.0
    coeffs = load_situation_coeffs()
    assert coeffs["present"] is True
    assert coeffs["SITUATION_TEAM_PTS_CAP"] == 3.0
    assert coeffs["TEAM_CARRY_SHRINK_unchanged"] == 0.85
    c = coeffs["coefficients"]
    assert set(c) == {"home", "b2b", "travel", "altitude"}


def test_paper_sim_chose_before_write() -> None:
    paper = load_paper_sim()
    coeffs = load_situation_coeffs()
    assert paper["present"] is True
    assert paper["chosen"] == coeffs["coefficients"]
    assert paper["ppg_adj_range"][0] >= 100.0
    assert paper["ppg_adj_range"][1] <= 130.0


def test_schedule_and_venue_flags() -> None:
    sched = load_schedule_pack()
    venue = load_venue_flags()
    assert sched["game_count"] == 1200
    assert sched["team_game_count"] == 2400
    assert len(venue["altitude_venues"]) == 2
    arenas = {(v["arena"], v["city"], v["state"]) for v in venue["altitude_venues"]}
    assert ("Ball Arena", "Denver", "CO") in arenas
    assert ("Delta Center", "Salt Lake City", "UT") in arenas


def test_altitude_is_venue_not_team_if() -> None:
    text = SITUATION_PY.read_text(encoding="utf-8") + BUILDER_PY.read_text(encoding="utf-8")
    # Forbid team-identity branches in situation compose.
    assert not re.search(r'if\s+.*\bteam\b.*==\s*[\'"]DEN[\'"]', text)
    assert not re.search(r'if\s+.*\bteam\b.*==\s*[\'"]UTA[\'"]', text)
    assert "altitude_venues" in load_venue_flags()


def test_apply_on_read_team_line_within_cap() -> None:
    sched = load_schedule_pack()
    # Pick a stacked row if any; otherwise first.
    row = next(
        (
            r
            for r in sched["team_games"]
            if r["home"] and r["b2b"] and r["travel"] and r["altitude"]
        ),
        sched["team_games"][0],
    )
    line = apply_situation_team_line(row["team"], row["game_id"], flags=row)
    assert line["situation_applied"] is True
    assert abs(line["delta_pts"]) <= P.SITUATION_TEAM_PTS_CAP + 1e-9
    assert line["within_residual_cap"] is True
    assert 100.0 <= line["implied_ppg"] <= 130.0
    # ORtg/DRtg unchanged (situation is points Δ, not a second net prior)
    assert line["ortg"] > 100.0
    assert line["drtg"] > 100.0


def test_player_copy_through_keeps_pts_identity() -> None:
    sched = load_schedule_pack()
    # Prefer a row with nonzero Δ so copy-through fires.
    row = next(r for r in sched["team_games"] if r["home"] or r["b2b"] or r["travel"])
    out = apply_situation_player_projections(row["team"], row["game_id"], flags=row)
    assert out["present"] is True
    assert out["within_residual_cap"] is True
    assert out["pts_drift"] <= P.TEAM_REBASE_RESIDUAL_CAP + 1e-6
    assert abs(sum(p["MIN"] for p in out["players"]) - 240.0) < 1e-3
    if abs(out["team_line"]["delta_pts"]) > 1e-12:
        assert out["copy_through"] is True
        assert abs(out["sum_pts"] - out["target_pts"]) <= 1e-3


def test_delta_clip_enforced() -> None:
    flags = {"home": True, "b2b": False, "travel": False, "altitude": True}
    # Extreme coeffs must still clip (|5+5| > cap).
    adj = situation_delta_pts(
        flags, coeffs={"home": 5.0, "b2b": -5.0, "travel": -5.0, "altitude": 5.0}
    )
    assert abs(adj["delta_pts"]) <= P.SITUATION_TEAM_PTS_CAP + 1e-9
    assert adj["clipped"] is True
    assert abs(adj["raw"]) > P.SITUATION_TEAM_PTS_CAP


def test_cfb_ball_osu_untouched() -> None:
    kei = json.loads(CFB_KEI.read_text(encoding="utf-8"))
    game = next(
        g
        for g in kei["games"]
        if g.get("away") == "BALL" and g.get("home") == "OSU" and g.get("week") == 1
    )
    assert abs(float(game["kei"]["kei_spread_home"]) - (-40.51)) < 1e-9


def test_no_prop_tags() -> None:
    coeffs = load_situation_coeffs()
    for row_key in ("tag", "PLAY", "LEAN", "fantasy_points"):
        assert row_key not in coeffs.get("coefficients", {})
    does_not = " ".join(coeffs.get("does_not") or []).lower()
    assert "play" in does_not or "props" in does_not
