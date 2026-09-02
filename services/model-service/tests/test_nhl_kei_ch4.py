"""NHL Chapter 4 — team KEI gates."""

from __future__ import annotations

import json
from pathlib import Path

from src.services.nhl_season_engine import priors as P
from src.services.nhl_season_engine.nhl_kei import (
    KEI_VERSION,
    LEAN_EDGE_PTS,
    NHL_MARGIN_SD,
    PLAY_EDGE_PTS,
    compute_game_kei,
    load_kei_pack,
    tag_from_edge,
)
from src.services.nhl_season_engine.situation import load_situation_coeffs

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
CFB_KEI = ROOT / "src/services/cfb_season_engine/data/cfb_kei_w0_w1_2026.json"
NBA_PRIORS = ROOT / "src/services/nba_season_engine/priors.py"
WNBA_PRIORS = ROOT / "src/services/wnba_season_engine/priors.py"
NBA_KEI = ROOT / "src/services/nba_season_engine/data/nba_kei_lines_ch4.json"
EDGE_KEI_AVAIL = REPO / "apps/web/lib/edge-board-kei-availability.ts"
TRUSTED = REPO / "apps/web/lib/nhl-trusted-market.ts"
ODDS = REPO / "apps/web/lib/odds-api.ts"
CH3_COEFFS = ROOT / "src/services/nhl_season_engine/data/nhl_situation_coeffs_v0.json"
CH1 = ROOT / "src/services/nhl_season_engine/data/nhl_team_prior_2026.json"
CH5 = ROOT / "src/services/nhl_season_engine/data/nhl_player_projection_2026.json"


def test_ch4_constants_frozen() -> None:
    assert P.ENGINE_VERSION == "nhl-season-engine-v0.1"
    assert P.NHL_TEAM_CARRY_SHRINK == 0.85
    assert P.NHL_SITUATION_GOAL_CAP == 0.35
    assert PLAY_EDGE_PTS == 4.0
    assert LEAN_EDGE_PTS == 2.5
    assert NHL_MARGIN_SD == 1.85
    c = load_situation_coeffs()["coefficients"]
    assert c == {"home": 0.1, "b2b": -0.15, "travel": -0.08, "altitude": 0.12}
    disk = json.loads(CH3_COEFFS.read_text(encoding="utf-8"))
    assert disk["coefficients"] == c
    assert json.loads(CH1.read_text(encoding="utf-8"))["NHL_TEAM_CARRY_SHRINK"] == 0.85
    assert json.loads(CH5.read_text(encoding="utf-8"))["NHL_TEAM_CARRY_SHRINK_unchanged"] == 0.85


def test_kei_pack_present_and_fla_car() -> None:
    pack = load_kei_pack(force=True)
    assert pack["present"] is True
    assert pack["kei_version"] == KEI_VERSION
    assert pack["game_count"] == 1344
    assert pack["mode"] == "kei_only"
    fla = next(
        g for g in pack["games"] if g.get("away") == "FLA" and g.get("home") == "CAR"
    )
    assert fla["date"] == "2026-09-29"
    assert fla["kei_puck_home"] is not None
    assert fla["kei_total"] is not None
    assert 0.02 <= float(fla["kei_home_win_prob"]) <= 0.98
    # League-sane totals band
    assert 4.5 <= float(fla["kei_total"]) <= 8.5
    # Not a trivial zero / not a copy of a book Best
    assert abs(float(fla["kei_puck_home"])) > 0.05
    assert "best" not in fla
    assert "PLAY" not in fla
    live = compute_game_kei("CAR", "FLA", str(fla["game_id"]))
    assert abs(float(live["kei_puck_home"]) - float(fla["kei_puck_home"])) < 0.05
    assert abs(float(live["kei_total"]) - float(fla["kei_total"])) < 0.05


def test_tag_pass_without_trusted_best_or_preseason() -> None:
    assert tag_from_edge(5.0, best_trusted=False) == "PASS"
    assert tag_from_edge(5.0, best_trusted=True, preseason=True) == "PASS"
    assert tag_from_edge(4.0, best_trusted=True) == "PLAY"
    assert tag_from_edge(2.5, best_trusted=True) == "LEAN"
    assert tag_from_edge(2.0, best_trusted=True) == "PASS"


def test_edge_board_nhl_no_longer_markets_only() -> None:
    text = EDGE_KEI_AVAIL.read_text(encoding="utf-8")
    assert '"nhl"' in text
    assert "sportHasKeiSource" in text
    # Markets-only helper must not hard-code nhl as the sole blank sport.
    assert "return sport === \"nhl\"" not in text
    assert 'return sport === "nhl"' not in text
    trust = TRUSTED.read_text(encoding="utf-8")
    assert "icehockey_nhl" in trust
    assert "NHL_LEAN_EDGE_PTS = 2.5" in trust
    assert "NHL_PLAY_EDGE_PTS = 4.0" in trust
    odds = ODDS.read_text(encoding="utf-8")
    assert 'nhl: "icehockey_nhl"' in odds


def test_nba_wnba_cfb_untouched() -> None:
    assert "TEAM_CARRY_SHRINK = 0.85" in NBA_PRIORS.read_text(encoding="utf-8")
    assert "WNBA_TEAM_CARRY_SHRINK = 0.85" in WNBA_PRIORS.read_text(encoding="utf-8")
    nba = json.loads(NBA_KEI.read_text(encoding="utf-8"))
    # HOU@OKC sample left alone
    hou = next(
        (
            g
            for g in nba["games"]
            if g.get("away") == "HOU" and g.get("home") == "OKC"
        ),
        None,
    )
    if hou is not None:
        assert abs(float(hou["kei_spread_home"]) - (-4.16)) < 0.05
    kei = json.loads(CFB_KEI.read_text(encoding="utf-8"))
    game = next(
        g
        for g in kei["games"]
        if g.get("away") == "BALL" and g.get("home") == "OSU" and g.get("week") == 1
    )
    assert abs(float(game["kei"]["kei_spread_home"]) - (-40.51)) < 1e-9
