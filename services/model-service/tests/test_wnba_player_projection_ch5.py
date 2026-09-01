"""WNBA Chapter 5 — PlayerProjection gates (single scorer)."""

from __future__ import annotations

import json
from pathlib import Path

from src.services.wnba_season_engine import priors as P
from src.services.wnba_season_engine.player_projection import (
    VECTOR_KEYS,
    get_team_projections,
    load_player_projection_pack,
    team_pts_identity,
)
from src.services.wnba_season_engine.roster_minutes import load_rebased_team_prior

ROOT = Path(__file__).resolve().parents[1]
CFB_KEI = ROOT / "src/services/cfb_season_engine/data/cfb_kei_w0_w1_2026.json"
NBA_KEI = ROOT / "src/services/nba_season_engine/data/nba_kei_lines_ch4.json"
CH1 = (
    ROOT
    / "src/services/wnba_season_engine/data/wnba_team_prior_2026.json"
)
CH2_GRID = (
    ROOT
    / "src/services/wnba_season_engine/data/wnba_minutes_grid_2026.json"
)
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


def test_ch5_constants_and_shrink_untouched() -> None:
    assert P.ENGINE_VERSION == "wnba-season-engine-v0.1"
    assert P.WNBA_TEAM_CARRY_SHRINK == 0.85
    assert P.WNBA_TEAM_REBASE_RESIDUAL_CAP == 3.0
    assert P.MINUTE_GRID_SUM == 200
    assert P.PLAYER_YEAR_WEIGHTS == {
        "2024": 0.20,
        "2025": 0.30,
        "2026": 0.50,
    }
    assert not hasattr(P, "TEAM_CARRY_SHRINK")
    pack = load_player_projection_pack(force=True)
    assert pack["present"] is True
    assert pack["object"] == "PlayerProjection"
    assert pack["WNBA_TEAM_REBASE_RESIDUAL_CAP"] == 3.0
    assert pack["WNBA_TEAM_CARRY_SHRINK_unchanged"] == 0.85
    assert pack["MINUTE_GRID_SUM"] == 200
    ch1 = json.loads(CH1.read_text(encoding="utf-8"))
    assert ch1["WNBA_TEAM_CARRY_SHRINK"] == 0.85


def test_every_min_gt0_has_full_vector_and_sigma() -> None:
    pack = load_player_projection_pack()
    assert pack["player_count"] == 135  # 15 × 9
    for key, row in pack["players"].items():
        assert float(row["MIN"]) > 0, key
        for k in VECTOR_KEYS:
            assert k in row, (key, k)
            assert row[k] is not None
        assert "sigma" in row
        for k in VECTOR_KEYS:
            assert k in row["sigma"], (key, k)
            assert float(row["sigma"][k]) >= 0.0


def test_team_min_200_and_pts_within_residual_cap() -> None:
    rebased = load_rebased_team_prior()
    for team in TEAMS:
        rows = get_team_projections(team)
        assert abs(sum(float(r["MIN"]) for r in rows) - 200.0) < 1e-3, team
        ident = team_pts_identity(team)
        target = float(rebased["teams"][team]["implied_ppg"])
        assert abs(ident["target_pts"] - target) < 1e-6, team
        assert ident["pts_drift"] <= P.WNBA_TEAM_REBASE_RESIDUAL_CAP + 1e-6, (
            team,
            ident["pts_drift"],
        )
        assert abs(ident["sum_pts"] - target) <= P.WNBA_TEAM_REBASE_RESIDUAL_CAP + 1e-6, (
            team
        )


def test_sigma_computed_not_hardcoded_four() -> None:
    pack = load_player_projection_pack()
    sigmas = []
    for row in pack["players"].values():
        for k, v in row["sigma"].items():
            if k == "MIN":
                continue
            sigmas.append(float(v))
    assert sigmas
    distinct = {round(s, 4) for s in sigmas}
    assert len(distinct) > 50
    share_eq_four = sum(1 for s in sigmas if abs(s - 4.0) < 1e-9) / len(sigmas)
    assert share_eq_four < 0.01


def test_ch2_grid_not_rewritten() -> None:
    grid = json.loads(CH2_GRID.read_text(encoding="utf-8"))
    assert grid["MINUTE_GRID_SUM"] == 200
    assert len(grid["teams"]) == 15


def test_leftover_fair_lines_not_blended() -> None:
    pack = load_player_projection_pack()
    assert pack["forbidden_leftover_fair_line_game_ids"] == [
        "401857105",
        "401857106",
    ]


def test_no_prop_or_board_tag_fields() -> None:
    pack = load_player_projection_pack()
    for row in pack["players"].values():
        for banned in (
            "tag",
            "edge_tag",
            "prop_tag",
            "play",
            "lean",
            "fantasy_points",
            "board_emit",
        ):
            assert banned not in row
            assert banned not in (row.get("sigma") or {})
    does_not = " ".join(pack.get("does_not") or []).lower()
    assert "board" in does_not
    assert "props" in does_not or "play" in does_not


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
