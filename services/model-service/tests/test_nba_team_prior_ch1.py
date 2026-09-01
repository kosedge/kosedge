"""NBA Chapter 1 — team prior shell gates."""

from __future__ import annotations

import json
from pathlib import Path

from src.services.nba_season_engine import priors as P
from src.services.nba_season_engine.team_prior import (
    apply_team_carry_shrink,
    documentation,
    get_team_prior,
    load_team_prior_pack,
)

CFB_KEI = (
    Path(__file__).resolve().parents[1]
    / "src/services/cfb_season_engine/data/cfb_kei_w0_w1_2026.json"
)


def test_engine_stamp_and_shrink_constant() -> None:
    assert P.ENGINE_VERSION == "nba-season-engine-v0.1"
    assert P.TEAM_CARRY_SHRINK == 0.85
    assert P.TEAM_CARRY_SHRINK in P.PAPER_SIM_S_SET
    assert not hasattr(P, "EFF_CARRY_SHRINK")


def test_pack_has_30_teams_and_post_fields() -> None:
    pack = load_team_prior_pack(force=True)
    assert pack["present"] is True
    assert pack["engine_version"] == "nba-season-engine-v0.1"
    assert pack["TEAM_CARRY_SHRINK"] == 0.85
    assert pack["team_count"] == 30
    assert len(pack["teams"]) == 30
    for code, row in pack["teams"].items():
        assert row["team"] == code
        for key in ("ortg_pre", "drtg_pre", "net_pre", "pace_pre", "ortg", "drtg", "net_rating", "pace"):
            assert key in row, (code, key)
        assert row["carry_shrink"] == 0.85


def test_league_mean_net_near_zero_documented() -> None:
    pack = load_team_prior_pack(force=True)
    mean_net = float(pack["league_mean_post"]["net_rating"])
    # Affine shrink preserves mean; BR rounding leaves a micro-offset — document gate.
    assert abs(mean_net) < 1e-3


def test_top_bottom_order_preserved_no_lottery_favorites() -> None:
    pack = load_team_prior_pack(force=True)
    teams = list(pack["teams"].values())
    by_pre = sorted(teams, key=lambda t: -t["net_pre"])
    by_post = sorted(teams, key=lambda t: -t["net_rating"])
    assert [t["team"] for t in by_pre[:5]] == [t["team"] for t in by_post[:5]]
    assert [t["team"] for t in by_pre[-5:]] == [t["team"] for t in by_post[-5:]]
    lottery = {t["team"] for t in sorted(teams, key=lambda t: t["w"])[:8]}
    top5 = {t["team"] for t in by_post[:5]}
    assert top5.isdisjoint(lottery)
    assert by_post[0]["team"] == "OKC"
    assert by_post[-1]["team"] == "WAS"


def test_apply_matches_pack_formula() -> None:
    pack = load_team_prior_pack(force=True)
    lm = pack["league_mean_pre"]
    okc = get_team_prior("OKC")
    assert okc is not None
    assert abs(
        apply_team_carry_shrink(okc["net_pre"], lm["net_rating"]) - okc["net_rating"]
    ) < 1e-3


def test_paper_sim_covers_s_set() -> None:
    pack = load_team_prior_pack(force=True)
    sims = {round(float(r["s"]), 2): r for r in pack["paper_sim"]}
    for s in P.PAPER_SIM_S_SET:
        assert s in sims
        assert sims[s]["lottery_in_top5_post"] == []


def test_documentation_forbids_props_and_cfb_reuse() -> None:
    doc = documentation()
    blob = " ".join(doc["does_not"]).lower()
    assert "kei" in blob
    assert "props" in blob
    assert "eff_carry_shrink" in blob


def test_cfb_ball_osu_kei_untouched() -> None:
    kei = json.loads(CFB_KEI.read_text(encoding="utf-8"))
    game = next(
        g
        for g in kei["games"]
        if g.get("away") == "BALL" and g.get("home") == "OSU" and g.get("week") == 1
    )
    assert abs(float(game["kei"]["kei_spread_home"]) - (-40.51)) < 1e-9
