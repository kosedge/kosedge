"""NHL Chapter 5 — PlayerProjection gates (skater + goalie)."""

from __future__ import annotations

import json
from pathlib import Path

from src.services.nhl_data import NHL_TEAM_ABBREVS
from src.services.nhl_season_engine import priors as P
from src.services.nhl_season_engine.player_projection import (
    GOALIE_VECTOR_KEYS,
    SKATER_VECTOR_KEYS,
    get_team_goalies,
    get_team_skaters,
    load_player_projection_pack,
    team_g_identity,
)
from src.services.nhl_season_engine.team_prior import load_team_prior_pack
from src.services.nhl_season_engine.toi_grid import load_goalie_tandem, load_toi_grid

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
CFB_KEI = ROOT / "src/services/cfb_season_engine/data/cfb_kei_w0_w1_2026.json"
NBA_PRIORS = ROOT / "src/services/nba_season_engine/priors.py"
WNBA_PRIORS = ROOT / "src/services/wnba_season_engine/priors.py"
EDGE_KEI_AVAIL = REPO / "apps/web/lib/edge-board-kei-availability.ts"
CH1 = ROOT / "src/services/nhl_season_engine/data/nhl_team_prior_2026.json"
CH2_TOI = ROOT / "src/services/nhl_season_engine/data/nhl_toi_grid_2026.json"
CH2_TANDEM = ROOT / "src/services/nhl_season_engine/data/nhl_goalie_tandem_2026.json"


def test_ch5_constants_and_shrink_untouched() -> None:
    assert P.ENGINE_VERSION == "nhl-season-engine-v0.1"
    assert P.NHL_TEAM_CARRY_SHRINK == 0.85
    assert P.NHL_TEAM_REBASE_RESIDUAL_CAP == 0.15
    assert P.NHL_TOI_GRID_SKATER_MINUTES == 300.0
    pack = load_player_projection_pack(force=True)
    assert pack["present"] is True
    assert pack["object"] == "PlayerProjection"
    assert pack["NHL_TEAM_REBASE_RESIDUAL_CAP"] == 0.15
    assert pack["NHL_TEAM_CARRY_SHRINK_unchanged"] == 0.85
    ch1 = load_team_prior_pack(force=True)
    assert ch1["NHL_TEAM_CARRY_SHRINK"] == 0.85


def test_every_toi_gt0_skater_has_full_vector_and_sigma() -> None:
    pack = load_player_projection_pack()
    assert pack["skater_count"] == 32 * 18
    for key, row in (pack.get("skaters") or {}).items():
        assert float(row["TOI_EV"]) + float(row["TOI_PP"]) > 0, key
        for k in SKATER_VECTOR_KEYS:
            assert k in row, (key, k)
            assert row[k] is not None
        assert "sigma" in row
        for k in SKATER_VECTOR_KEYS:
            assert k in row["sigma"], (key, k)
            assert float(row["sigma"][k]) >= 0.0
        # Raw box has no PP TOI — Phase 1 honesty.
        assert float(row["TOI_PP"]) == 0.0


def test_every_team_goalie_shares_sum_and_full_vector() -> None:
    pack = load_player_projection_pack()
    assert pack["goalie_count"] > 0
    for team in NHL_TEAM_ABBREVS:
        rows = get_team_goalies(team)
        assert rows
        share = sum(float(r["start_share"]) for r in rows)
        assert abs(share - 1.0) < 1e-6, (team, share)
        for row in rows:
            for k in GOALIE_VECTOR_KEYS:
                assert k in row
                assert row[k] is not None
            for k in GOALIE_VECTOR_KEYS:
                assert k in row["sigma"]
                assert float(row["sigma"][k]) >= 0.0


def test_team_toi_300_and_g_within_residual_cap() -> None:
    ch1 = load_team_prior_pack(force=True)
    for team in NHL_TEAM_ABBREVS:
        rows = get_team_skaters(team)
        assert abs(sum(float(r["TOI_EV"]) + float(r["TOI_PP"]) for r in rows) - 300.0) < 0.05
        ident = team_g_identity(team)
        target = float(ch1["teams"][team]["gf"]) / float(ch1["teams"][team]["gp"])
        assert abs(ident["target_gf_pg"] - target) < 1e-6, team
        assert ident["g_drift"] <= P.NHL_TEAM_REBASE_RESIDUAL_CAP + 1e-6, (
            team,
            ident["g_drift"],
        )
        assert abs(ident["sum_g"] - target) <= P.NHL_TEAM_REBASE_RESIDUAL_CAP + 1e-6
        assert abs(ident["sum_start_share"] - 1.0) < 1e-6


def test_sigma_computed_not_hardcoded_four() -> None:
    pack = load_player_projection_pack()
    sigmas = []
    for row in (pack.get("skaters") or {}).values():
        for k, v in row["sigma"].items():
            if k.startswith("TOI"):
                continue
            sigmas.append(float(v))
    for row in (pack.get("goalies") or {}).values():
        for k, v in row["sigma"].items():
            if k == "start_share":
                continue
            sigmas.append(float(v))
    assert sigmas
    distinct = {round(s, 4) for s in sigmas}
    assert len(distinct) > 50
    share_eq_four = sum(1 for s in sigmas if abs(s - 4.0) < 1e-9) / len(sigmas)
    assert share_eq_four < 0.01


def test_ch2_packs_not_rewritten() -> None:
    toi = load_toi_grid()
    tandem = load_goalie_tandem()
    assert toi.get("present") is True
    assert tandem.get("present") is True
    assert toi.get("skaters_per_team") == 18
    assert len(toi.get("teams") or {}) == 32
    disk_toi = json.loads(CH2_TOI.read_text(encoding="utf-8"))
    disk_tan = json.loads(CH2_TANDEM.read_text(encoding="utf-8"))
    assert disk_toi["skaters_per_team"] == 18
    assert len(disk_tan["teams"]) == 32


def test_keinhl_still_blank() -> None:
    text = EDGE_KEI_AVAIL.read_text(encoding="utf-8")
    assert 'return sport === "nhl"' in text
    pack = load_player_projection_pack()
    blob = " ".join(pack.get("does_not") or []).lower()
    assert "kei" in blob or "keinhl" in blob
    assert "props" in blob


def test_nba_wnba_cfb_untouched() -> None:
    assert "TEAM_CARRY_SHRINK = 0.85" in NBA_PRIORS.read_text(encoding="utf-8")
    assert "NHL_TEAM_CARRY_SHRINK" not in NBA_PRIORS.read_text(encoding="utf-8")
    assert "WNBA_TEAM_CARRY_SHRINK = 0.85" in WNBA_PRIORS.read_text(encoding="utf-8")
    kei = json.loads(CFB_KEI.read_text(encoding="utf-8"))
    game = next(
        g
        for g in kei["games"]
        if g.get("away") == "BALL" and g.get("home") == "OSU" and g.get("week") == 1
    )
    assert abs(float(game["kei"]["kei_spread_home"]) - (-40.51)) < 1e-9
