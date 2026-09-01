"""NHL Chapter 2 — TOI grid + goalie tandem gates."""

from __future__ import annotations

import json
from pathlib import Path

from src.services.nhl_data import NHL_TEAM_ABBREVS
from src.services.nhl_season_engine import priors as P
from src.services.nhl_season_engine.toi_grid import (
    documentation,
    get_team_goalie_tandem,
    get_team_toi,
    load_goalie_tandem,
    load_toi_grid,
)
from src.services.nhl_season_engine.team_prior import load_team_prior_pack

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
CFB_KEI = ROOT / "src/services/cfb_season_engine/data/cfb_kei_w0_w1_2026.json"
NBA_PRIORS = ROOT / "src/services/nba_season_engine/priors.py"
WNBA_PRIORS = ROOT / "src/services/wnba_season_engine/priors.py"
EDGE_KEI_AVAIL = REPO / "apps/web/lib/edge-board-kei-availability.ts"
CH1_PACK = (
    ROOT
    / "src/services/nhl_season_engine/data/nhl_team_prior_2026.json"
)


def test_ch2_constants_and_ch1_shrink_frozen() -> None:
    assert P.ENGINE_VERSION == "nhl-season-engine-v0.1"
    assert P.NHL_TEAM_CARRY_SHRINK == 0.85
    assert P.NHL_TOI_GRID_SKATER_MINUTES == 300.0
    assert P.NHL_GOALIE_TANDEM_SHARE_SUM == 1.0
    assert P.PLAYER_YEAR_WEIGHTS_BY_SEASON_ID[20232024] == 0.20
    assert P.PLAYER_YEAR_WEIGHTS_BY_SEASON_ID[20242025] == 0.30
    assert P.PLAYER_YEAR_WEIGHTS_BY_SEASON_ID[20252026] == 0.50
    # Ch1 pack unchanged by Ch2.
    ch1 = load_team_prior_pack(force=True)
    assert ch1["NHL_TEAM_CARRY_SHRINK"] == 0.85
    assert ch1["team_count"] == 32


def test_toi_grid_32_teams_share_and_minutes_identity() -> None:
    pack = load_toi_grid()
    assert pack.get("present") is True
    assert pack["engine_version"] == "nhl-season-engine-v0.1"
    assert pack["skaters_per_team"] == 18
    assert set(pack["teams"]) == set(NHL_TEAM_ABBREVS)
    for team in NHL_TEAM_ABBREVS:
        rows = get_team_toi(team)
        assert len(rows) == 18, team
        share = sum(float(r["toi_share"]) for r in rows)
        mins = sum(float(r["toi_min"]) for r in rows)
        assert abs(share - 1.0) < 1e-6, (team, share)
        assert abs(mins - 300.0) < 0.05, (team, mins)


def test_goalie_tandem_shares_sum_to_one() -> None:
    pack = load_goalie_tandem()
    assert pack.get("present") is True
    assert set(pack["teams"]) == set(NHL_TEAM_ABBREVS)
    for team in NHL_TEAM_ABBREVS:
        row = get_team_goalie_tandem(team)
        assert row is not None
        assert row.get("starter") is not None
        assert abs(float(row["gs_share_sum"]) - 1.0) < 1e-6, team
        shares = [float(g["gs_share"]) for g in row.get("goalies") or []]
        assert abs(sum(shares) - 1.0) < 1e-6


def test_documentation_forbids_emit_and_shrink_retune() -> None:
    doc = documentation()
    blob = " ".join(doc["does_not"]).lower()
    assert "kei" in blob or "keinhl" in blob
    assert "shrink" in blob
    assert doc["NHL_TEAM_CARRY_SHRINK_unchanged"] == 0.85


def test_keinhl_still_blank() -> None:
    text = EDGE_KEI_AVAIL.read_text(encoding="utf-8")
    assert 'return sport === "nhl"' in text


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


def test_ch1_prior_file_byte_stable_under_ch2_readers() -> None:
    before = CH1_PACK.read_bytes()
    load_toi_grid()
    load_goalie_tandem()
    documentation()
    assert CH1_PACK.read_bytes() == before
