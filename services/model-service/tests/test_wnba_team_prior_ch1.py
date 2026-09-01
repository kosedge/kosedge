"""WNBA Chapter 1 — team prior shell gates."""

from __future__ import annotations

import json
from pathlib import Path

from src.services.wnba_season_engine import priors as P
from src.services.wnba_season_engine.team_prior import (
    apply_wnba_team_carry_shrink,
    documentation,
    get_team_prior,
    load_team_prior_pack,
)

ROOT = Path(__file__).resolve().parents[1]
CFB_KEI = ROOT / "src/services/cfb_season_engine/data/cfb_kei_w0_w1_2026.json"
NBA_KEI = ROOT / "src/services/nba_season_engine/data/nba_kei_lines_ch4.json"
NBA_PRIORS = ROOT / "src/services/nba_season_engine/priors.py"
EXPECTED = {
    "ATL",
    "CHI",
    "CON",
    "DAL",
    "GSV",
    "IND",
    "LAS",
    "LA",
    "MIN",
    "NY",
    "PHX",
    "POR",
    "SEA",
    "TOR",
    "WSH",
}


def test_engine_stamp_and_own_shrink_constant() -> None:
    assert P.ENGINE_VERSION == "wnba-season-engine-v0.1"
    assert P.WNBA_TEAM_CARRY_SHRINK == 0.85
    assert P.WNBA_TEAM_CARRY_SHRINK in P.PAPER_SIM_S_SET
    assert not hasattr(P, "TEAM_CARRY_SHRINK")
    assert not hasattr(P, "EFF_CARRY_SHRINK")
    # NBA constant file untouched / not imported
    nba_txt = NBA_PRIORS.read_text(encoding="utf-8")
    assert "TEAM_CARRY_SHRINK = 0.85" in nba_txt
    assert "WNBA_TEAM_CARRY_SHRINK" not in nba_txt


def test_pack_has_every_2026_team_and_post_fields() -> None:
    pack = load_team_prior_pack(force=True)
    assert pack["present"] is True
    assert pack["engine_version"] == "wnba-season-engine-v0.1"
    assert pack["WNBA_TEAM_CARRY_SHRINK"] == 0.85
    assert pack["season"] == "2026"
    assert pack["team_count"] == 15
    assert set(pack["teams"]) == EXPECTED
    for code, row in pack["teams"].items():
        assert row["team"] == code
        for key in (
            "ortg_pre",
            "drtg_pre",
            "net_pre",
            "pace_pre",
            "ortg",
            "drtg",
            "net_rating",
            "pace",
        ):
            assert key in row, (code, key)
        assert row["carry_shrink"] == 0.85
        assert row["gp"] >= 30  # midseason ~40/44
    # Expansion: YTD + shrink only — flag present, no invented 2025 fields
    for code in ("TOR", "POR"):
        assert pack["teams"][code]["expansion_ytd_only"] is True
        assert "ortg_2025" not in pack["teams"][code]


def test_league_mean_net_near_zero_documented() -> None:
    pack = load_team_prior_pack(force=True)
    mean_net = float(pack["league_mean_post"]["net_rating"])
    # Affine shrink preserves mean; BR rounding leaves a micro-offset.
    assert abs(mean_net) < 0.05


def test_top_bottom_order_preserved_no_lottery_favorites() -> None:
    pack = load_team_prior_pack(force=True)
    teams = list(pack["teams"].values())
    by_pre = sorted(teams, key=lambda t: -t["net_pre"])
    by_post = sorted(teams, key=lambda t: -t["net_rating"])
    assert [t["team"] for t in by_pre[:5]] == [t["team"] for t in by_post[:5]]
    assert [t["team"] for t in by_pre[-5:]] == [t["team"] for t in by_post[-5:]]
    lottery = {t["team"] for t in sorted(teams, key=lambda t: t["w"])[:5]}
    top5 = {t["team"] for t in by_post[:5]}
    assert top5.isdisjoint(lottery)
    assert by_post[0]["team"] == "MIN"
    assert by_post[-1]["team"] == "CON"


def test_apply_matches_pack_formula() -> None:
    pack = load_team_prior_pack(force=True)
    lm = pack["league_mean_pre"]
    minn = get_team_prior("MIN")
    assert minn is not None
    assert (
        abs(
            apply_wnba_team_carry_shrink(minn["net_pre"], lm["net_rating"])
            - minn["net_rating"]
        )
        < 1e-3
    )


def test_paper_sim_covers_s_set() -> None:
    pack = load_team_prior_pack(force=True)
    sims = {round(float(r["s"]), 2): r for r in pack["paper_sim"]}
    for s in P.PAPER_SIM_S_SET:
        assert s in sims
        assert sims[s]["lottery_in_top5_post"] == []


def test_documentation_forbids_board_emit_and_nba_reuse() -> None:
    doc = documentation()
    blob = " ".join(doc["does_not"]).lower()
    assert "kei" in blob
    assert "401857105" in blob or "leftover" in blob
    assert "nba" in blob
    pack = load_team_prior_pack(force=True)
    assert pack["forbidden_leftover_fair_line_game_ids"] == [
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
    """Gate: NBA HOU/OKC KEI still ≈ +4.2 / −4.2 (pack −4.16 home OKC)."""
    kei = json.loads(NBA_KEI.read_text(encoding="utf-8"))
    games = kei.get("games") or []
    opener = next(g for g in games if g.get("game_id") == "0022500001")
    assert opener["away"] == "HOU" and opener["home"] == "OKC"
    # Desk shorthand +4.2 / −4.2; stamped value is −4.16 home.
    assert abs(float(opener["kei_spread_home"]) - (-4.16)) < 1e-9
