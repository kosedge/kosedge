"""NHL Chapter 3 — situation class gates (apply-on-read, goal units)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from src.services.nhl_data import NHL_TEAM_ABBREVS
from src.services.nhl_season_engine import priors as P
from src.services.nhl_season_engine.player_projection import (
    load_player_projection_pack,
    team_g_identity,
)
from src.services.nhl_season_engine.situation import (
    apply_situation_player_projections,
    apply_situation_team_line,
    load_paper_sim,
    load_schedule_pack,
    load_situation_coeffs,
    load_venue_flags,
    situation_delta_goals,
)
from src.services.nhl_season_engine.team_prior import load_team_prior_pack
from src.services.nhl_season_engine.toi_grid import load_goalie_tandem, load_toi_grid

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
CFB_KEI = ROOT / "src/services/cfb_season_engine/data/cfb_kei_w0_w1_2026.json"
NBA_PRIORS = ROOT / "src/services/nba_season_engine/priors.py"
WNBA_PRIORS = ROOT / "src/services/wnba_season_engine/priors.py"
NBA_COEFFS = ROOT / "src/services/nba_season_engine/data/nba_situation_coeffs_v0.json"
WNBA_COEFFS = ROOT / "src/services/wnba_season_engine/data/wnba_situation_coeffs_v0.json"
EDGE_KEI_AVAIL = REPO / "apps/web/lib/edge-board-kei-availability.ts"
SITUATION_PY = ROOT / "src/services/nhl_season_engine/situation.py"
BUILDER_PY = REPO / "scripts/nhl/build_situation_ch3.py"
CH1 = ROOT / "src/services/nhl_season_engine/data/nhl_team_prior_2026.json"
CH2_TOI = ROOT / "src/services/nhl_season_engine/data/nhl_toi_grid_2026.json"
CH5 = ROOT / "src/services/nhl_season_engine/data/nhl_player_projection_2026.json"
RAW_SCHED = ROOT / "src/services/nhl_season_engine/data/nhl_schedule_2026.json"


def test_ch3_constants_shrink_untouched() -> None:
    assert P.ENGINE_VERSION == "nhl-season-engine-v0.1"
    assert P.NHL_TEAM_CARRY_SHRINK == 0.85
    assert P.NHL_TEAM_REBASE_RESIDUAL_CAP == 0.15
    assert P.NHL_SITUATION_GOAL_CAP == 0.35
    coeffs = load_situation_coeffs()
    assert coeffs["present"] is True
    assert coeffs["NHL_SITUATION_GOAL_CAP"] == 0.35
    assert coeffs["NHL_TEAM_CARRY_SHRINK_unchanged"] == 0.85
    c = coeffs["coefficients"]
    assert set(c) == {"home", "b2b", "travel", "altitude"}
    # Do not copy NBA +2.0 or WNBA +1.5.
    assert abs(float(c["home"]) - 2.0) > 1e-9
    assert abs(float(c["home"]) - 1.5) > 1e-9
    ch1 = load_team_prior_pack(force=True)
    assert ch1["NHL_TEAM_CARRY_SHRINK"] == 0.85


def test_paper_sim_chose_before_write() -> None:
    paper = load_paper_sim()
    coeffs = load_situation_coeffs()
    assert paper["present"] is True
    assert paper["chosen"] == coeffs["coefficients"]
    lo, hi = paper["gf_pg_adj_range"]
    assert 2.0 <= lo <= hi <= 4.5
    assert paper["units"] == "goals_per_game_on_team_gf"


def test_schedule_and_venue_flags() -> None:
    sched = load_schedule_pack()
    venue = load_venue_flags()
    assert sched["game_count"] == 1344
    assert sched["team_game_count"] == 2688
    venues = {v["venue"] for v in venue["altitude_venues"]}
    assert "Ball Arena" in venues
    assert "Delta Center" in venues
    assert RAW_SCHED.is_file()  # fetcher pack untouched


def test_altitude_is_venue_not_team_if() -> None:
    text = SITUATION_PY.read_text(encoding="utf-8") + BUILDER_PY.read_text(
        encoding="utf-8"
    )
    assert not re.search(r'if\s+.*\bteam\b.*==\s*[\'"]COL[\'"]', text)
    assert not re.search(r'if\s+.*\bteam\b.*==\s*[\'"]UTA[\'"]', text)
    assert "altitude_venues" in load_venue_flags()


def test_apply_on_read_team_line_league_sane() -> None:
    sched = load_schedule_pack()
    row = next(
        (
            r
            for r in sched["team_games"]
            if r["home"] and r["b2b"] and r["travel"] and r["altitude"]
        ),
        next(r for r in sched["team_games"] if r["home"] or r["b2b"]),
    )
    line = apply_situation_team_line(row["team"], row["game_id"], flags=row)
    assert line["situation_applied"] is True
    assert abs(line["delta_goals"]) <= P.NHL_SITUATION_GOAL_CAP + 1e-9
    assert line["within_situation_cap"] is True
    assert 2.0 <= line["gf_pg"] <= 4.5
    assert 2.0 <= line["ga_pg"] <= 4.5
    # GA unchanged (situation is GF Δ, not a second net prior)
    assert abs(line["ga_pg"] - line["ga_pg_base"]) < 1e-12


def test_skater_g_and_goalie_share_identity_after_apply() -> None:
    sched = load_schedule_pack()
    row = next(r for r in sched["team_games"] if r["home"] or r["b2b"] or r["travel"])
    out = apply_situation_player_projections(row["team"], row["game_id"], flags=row)
    assert out["present"] is True
    assert out["within_residual_cap"] is True
    assert abs(out["sum_start_share"] - 1.0) < 1e-6
    if abs(out["team_line"]["delta_goals"]) > 1e-12:
        assert out["copy_through"] is True
        assert abs(out["sum_g"] - out["target_gf_pg"]) <= P.NHL_TEAM_REBASE_RESIDUAL_CAP + 1e-6
    # Opening-night Ch5 identity still holds on disk (no rewrite).
    for team in NHL_TEAM_ABBREVS:
        ident = team_g_identity(team)
        assert ident["g_drift"] <= P.NHL_TEAM_REBASE_RESIDUAL_CAP + 1e-6
        assert abs(ident["sum_start_share"] - 1.0) < 1e-6


def test_delta_clip_enforced() -> None:
    flags = {"home": True, "b2b": False, "travel": False, "altitude": True}
    adj = situation_delta_goals(
        flags,
        coeffs={"home": 0.5, "b2b": -0.5, "travel": -0.5, "altitude": 0.5},
    )
    assert abs(adj["delta_goals"]) <= P.NHL_SITUATION_GOAL_CAP + 1e-9
    assert adj["clipped"] is True
    assert abs(adj["raw"]) > P.NHL_SITUATION_GOAL_CAP


def test_ch1_ch2_ch5_packs_not_rewritten() -> None:
    assert load_team_prior_pack(force=True)["NHL_TEAM_CARRY_SHRINK"] == 0.85
    toi = load_toi_grid()
    tandem = load_goalie_tandem()
    ch5 = load_player_projection_pack(force=True)
    assert toi.get("skaters_per_team") == 18
    assert tandem.get("present") is True
    assert ch5["skater_count"] == 32 * 18
    disk_ch1 = json.loads(CH1.read_text(encoding="utf-8"))
    disk_toi = json.loads(CH2_TOI.read_text(encoding="utf-8"))
    disk_ch5 = json.loads(CH5.read_text(encoding="utf-8"))
    assert disk_ch1["NHL_TEAM_CARRY_SHRINK"] == 0.85
    assert disk_toi["skaters_per_team"] == 18
    assert disk_ch5["NHL_TEAM_CARRY_SHRINK_unchanged"] == 0.85


def test_keinhl_still_blank() -> None:
    text = EDGE_KEI_AVAIL.read_text(encoding="utf-8")
    assert 'return sport === "nhl"' in text
    coeffs = load_situation_coeffs()
    blob = " ".join(coeffs.get("does_not") or []).lower()
    assert "kei" in blob or "keinhl" in blob
    assert "props" in blob


def test_nba_wnba_cfb_untouched() -> None:
    assert "TEAM_CARRY_SHRINK = 0.85" in NBA_PRIORS.read_text(encoding="utf-8")
    assert "NHL_TEAM_CARRY_SHRINK" not in NBA_PRIORS.read_text(encoding="utf-8")
    assert "WNBA_TEAM_CARRY_SHRINK = 0.85" in WNBA_PRIORS.read_text(encoding="utf-8")
    nba_c = json.loads(NBA_COEFFS.read_text(encoding="utf-8"))["coefficients"]
    wnba_c = json.loads(WNBA_COEFFS.read_text(encoding="utf-8"))["coefficients"]
    nhl_c = load_situation_coeffs()["coefficients"]
    assert nba_c["home"] == 2.0
    assert wnba_c["home"] == 1.5
    assert nhl_c["home"] != nba_c["home"]
    assert nhl_c["home"] != wnba_c["home"]
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
