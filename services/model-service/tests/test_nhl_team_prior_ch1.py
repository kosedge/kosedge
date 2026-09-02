"""NHL Chapter 1 — team prior shell gates."""

from __future__ import annotations

import json
from pathlib import Path

from src.services.nhl_season_engine import priors as P
from src.services.nhl_season_engine.team_prior import (
    apply_nhl_team_carry_shrink,
    documentation,
    get_team_prior,
    load_team_prior_pack,
)
from src.services.nhl_data import NHL_TEAM_ABBREVS

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
CFB_KEI = ROOT / "src/services/cfb_season_engine/data/cfb_kei_w0_w1_2026.json"
NBA_PRIORS = ROOT / "src/services/nba_season_engine/priors.py"
WNBA_PRIORS = ROOT / "src/services/wnba_season_engine/priors.py"
EDGE_KEI_AVAIL = REPO / "apps/web/lib/edge-board-kei-availability.ts"


def test_engine_stamp_and_own_shrink_constant() -> None:
    assert P.ENGINE_VERSION == "nhl-season-engine-v0.1"
    assert P.NHL_TEAM_CARRY_SHRINK == 0.85
    assert P.NHL_TEAM_CARRY_SHRINK in P.PAPER_SIM_S_SET
    assert not hasattr(P, "TEAM_CARRY_SHRINK")
    assert not hasattr(P, "WNBA_TEAM_CARRY_SHRINK")
    nba_txt = NBA_PRIORS.read_text(encoding="utf-8")
    assert "TEAM_CARRY_SHRINK = 0.85" in nba_txt
    assert "NHL_TEAM_CARRY_SHRINK" not in nba_txt
    wnba_txt = WNBA_PRIORS.read_text(encoding="utf-8")
    assert "WNBA_TEAM_CARRY_SHRINK = 0.85" in wnba_txt
    assert "NHL_TEAM_CARRY_SHRINK" not in wnba_txt


def test_pack_has_32_teams_from_box_only() -> None:
    pack = load_team_prior_pack(force=True)
    assert pack["present"] is True
    assert pack["engine_version"] == "nhl-season-engine-v0.1"
    assert pack["NHL_TEAM_CARRY_SHRINK"] == 0.85
    assert pack["season"] == "2025-26"
    assert pack["carry_to_season"] == "2026-27"
    assert pack["team_count"] == 32
    assert set(pack["teams"]) == set(NHL_TEAM_ABBREVS)
    for code, row in pack["teams"].items():
        assert row["team"] == code
        for key in ("gf_pre", "ga_pre", "net_pre", "gf", "ga", "net_rating"):
            assert key in row, (code, key)
        assert row["carry_shrink"] == 0.85
        assert abs(row["net_pre"] - (row["gf_pre"] - row["ga_pre"])) < 1e-9
        assert abs(row["net_rating"] - (row["gf"] - row["ga"])) < 0.02


def test_league_mean_net_near_zero() -> None:
    pack = load_team_prior_pack(force=True)
    mean_net = float(pack["league_mean_post"]["net_rating"])
    # Closed league ΣGF≈ΣGA; affine shrink preserves mean (exact 0 here).
    assert abs(mean_net) < 1e-6


def test_top_bottom_order_preserved_no_lottery_favorites() -> None:
    pack = load_team_prior_pack(force=True)
    teams = list(pack["teams"].values())
    by_pre = sorted(teams, key=lambda t: -t["net_pre"])
    by_post = sorted(teams, key=lambda t: -t["net_rating"])
    assert [t["team"] for t in by_pre[:5]] == [t["team"] for t in by_post[:5]]
    assert [t["team"] for t in by_pre[-5:]] == [t["team"] for t in by_post[-5:]]
    lottery = {
        t["team"]
        for t in sorted(teams, key=lambda t: (t["pts"], t["w"], -t["l"]))[:10]
    }
    top5 = {t["team"] for t in by_post[:5]}
    assert top5.isdisjoint(lottery)
    assert by_post[0]["team"] == "COL"
    assert by_post[-1]["team"] == "VAN"


def test_apply_matches_pack_formula() -> None:
    pack = load_team_prior_pack(force=True)
    lm = pack["league_mean_pre"]
    col = get_team_prior("COL")
    assert col is not None
    assert (
        abs(
            apply_nhl_team_carry_shrink(col["net_pre"], lm["net_rating"])
            - col["net_rating"]
        )
        < 1e-3
    )
    assert (
        abs(apply_nhl_team_carry_shrink(col["gf_pre"], lm["gf"]) - col["gf"]) < 1e-3
    )


def test_paper_sim_covers_s_set() -> None:
    pack = load_team_prior_pack(force=True)
    sims = {round(float(r["s"]), 2): r for r in pack["paper_sim"]}
    for s in P.PAPER_SIM_S_SET:
        assert s in sims
        assert sims[s]["lottery_in_top5_post"] == []


def test_documentation_forbids_board_emit() -> None:
    doc = documentation()
    blob = " ".join(doc["does_not"]).lower()
    assert "kei" in blob or "keinhl" in blob
    assert "xg" in blob
    assert "nba" in blob or "wnba" in blob


def test_keinhl_availability_helper_present() -> None:
    # Ch1 does not emit board KEI; helper module still exists (Ch4 fills).
    text = EDGE_KEI_AVAIL.read_text(encoding="utf-8")
    assert "sportIsMarketsOnlyEdgeBoard" in text
    assert "sportHasKeiSource" in text


def test_cfb_ball_osu_untouched() -> None:
    kei = json.loads(CFB_KEI.read_text(encoding="utf-8"))
    game = next(
        g
        for g in kei["games"]
        if g.get("away") == "BALL" and g.get("home") == "OSU" and g.get("week") == 1
    )
    assert abs(float(game["kei"]["kei_spread_home"]) - (-40.51)) < 1e-9
