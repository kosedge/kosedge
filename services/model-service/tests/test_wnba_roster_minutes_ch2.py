"""WNBA Chapter 2 — roster × minutes rebase gates."""

from __future__ import annotations

import json
from pathlib import Path

from src.services.wnba_season_engine import priors as P
from src.services.wnba_season_engine.roster_minutes import (
    get_rebased_team,
    get_team_minutes,
    load_minutes_grid,
    load_player_talent_pack,
    load_rebased_team_prior,
)
from src.services.wnba_season_engine.team_prior import load_team_prior_pack

ROOT = Path(__file__).resolve().parents[1]
CFB_KEI = ROOT / "src/services/cfb_season_engine/data/cfb_kei_w0_w1_2026.json"
NBA_KEI = ROOT / "src/services/nba_season_engine/data/nba_kei_lines_ch4.json"
TEAMS = [
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
]


def test_ch2_constants_and_ch1_shrink_untouched() -> None:
    assert P.ENGINE_VERSION == "wnba-season-engine-v0.1"
    assert P.WNBA_TEAM_CARRY_SHRINK == 0.85
    assert P.PLAYER_YEAR_WEIGHTS == {
        "2024": 0.20,
        "2025": 0.30,
        "2026": 0.50,
    }
    assert P.MINUTE_GRID_SUM == 200
    assert P.WNBA_TEAM_REBASE_RESIDUAL_CAP == 3.0
    assert P.PPG_BAND == (75.0, 91.0)
    ch1 = load_team_prior_pack(force=True)
    assert ch1["WNBA_TEAM_CARRY_SHRINK"] == 0.85
    assert not hasattr(P, "TEAM_CARRY_SHRINK")


def test_fifteen_teams_minutes_sum_200() -> None:
    grid = load_minutes_grid()
    assert grid["present"] is True
    assert grid["MINUTE_GRID_SUM"] == 200
    assert len(grid["teams"]) == 15
    for team in TEAMS:
        rows = get_team_minutes(team)
        assert len(rows) == 9, team
        assert abs(sum(r["minutes"] for r in rows) - 200.0) < 1e-6, team
        roles = [r["role"] for r in rows]
        assert roles.count("star") == 2
        assert roles.count("starter") == 3
        assert roles.count("bench") == 4
        # WNBA class mids — not NBA 34/30
        assert abs(rows[0]["minutes"] - 32.0) < 0.05 or rows[0]["role"] == "star"


def test_rebased_residual_within_cap_and_ppg_band() -> None:
    pack = load_rebased_team_prior()
    assert pack["present"] is True
    assert pack["WNBA_TEAM_REBASE_RESIDUAL_CAP"] == 3.0
    assert pack["team_count"] == 15
    low, high = P.PPG_BAND
    for team in TEAMS:
        row = get_rebased_team(team)
        assert row is not None
        assert abs(row["residual"]) <= 3.0 + 1e-9
        assert abs(row["minutes_sum"] - 200.0) < 1e-6
        assert low <= row["implied_ppg"] <= high, (team, row["implied_ppg"])


def test_expansion_only_players_stay_on_tor_por() -> None:
    talent = load_player_talent_pack()
    grid = load_minutes_grid()
    expansion = [
        p
        for p in (talent.get("players") or {}).values()
        if p.get("expansion_only")
    ]
    assert expansion, "expected some expansion-only 2026 players"
    for p in expansion:
        assert p["team_2026"] in {"TOR", "POR"}, p
        # Must not appear on another team's grid
        for team, rows in (grid.get("teams") or {}).items():
            if team == p["team_2026"]:
                continue
            assert all(r["player_id"] != p["player_id"] for r in rows), (
                p["player_id"],
                team,
            )


def test_talent_metric_and_weights() -> None:
    talent = load_player_talent_pack()
    assert talent["metric"] == "per_minus_15"
    assert talent["PLAYER_YEAR_WEIGHTS"] == P.PLAYER_YEAR_WEIGHTS
    assert talent["player_count"] >= 150
    aja = talent["players"]["wilsoa01w"]
    assert aja["team_2026"] == "LAS"
    assert set(aja["seasons"]) == {"2024", "2025", "2026"}


def test_leftover_fair_lines_not_blended() -> None:
    pack = load_rebased_team_prior()
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
    kei = json.loads(NBA_KEI.read_text(encoding="utf-8"))
    opener = next(g for g in kei["games"] if g.get("game_id") == "0022500001")
    assert opener["away"] == "HOU" and opener["home"] == "OKC"
    assert abs(float(opener["kei_spread_home"]) - (-4.16)) < 1e-9
