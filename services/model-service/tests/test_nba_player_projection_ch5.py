"""NBA Chapter 5 — PlayerProjection gates (single scorer)."""

from __future__ import annotations

import json
from pathlib import Path

from src.services.nba_season_engine import priors as P
from src.services.nba_season_engine.player_projection import (
    VECTOR_KEYS,
    get_team_projections,
    load_player_projection_pack,
    team_pts_identity,
)
from src.services.nba_season_engine.roster_minutes import load_rebased_team_prior

CFB_KEI = (
    Path(__file__).resolve().parents[1]
    / "src/services/cfb_season_engine/data/cfb_kei_w0_w1_2026.json"
)
TEAMS = [
    "ATL",
    "BOS",
    "BKN",
    "CHA",
    "CHI",
    "CLE",
    "DAL",
    "DEN",
    "DET",
    "GSW",
    "HOU",
    "IND",
    "LAC",
    "LAL",
    "MEM",
    "MIA",
    "MIL",
    "MIN",
    "NOP",
    "NYK",
    "OKC",
    "ORL",
    "PHI",
    "PHX",
    "POR",
    "SAC",
    "SAS",
    "TOR",
    "UTA",
    "WAS",
]


def test_ch5_constants_and_shrink_untouched() -> None:
    assert P.ENGINE_VERSION == "nba-season-engine-v0.1"
    assert P.TEAM_CARRY_SHRINK == 0.85
    assert P.TEAM_REBASE_RESIDUAL_CAP == 3.0
    assert P.MINUTE_GRID_SUM == 240
    pack = load_player_projection_pack(force=True)
    assert pack["present"] is True
    assert pack["TEAM_REBASE_RESIDUAL_CAP"] == 3.0
    assert pack["object"] == "PlayerProjection"


def test_every_min_gt0_has_full_vector_and_sigma() -> None:
    pack = load_player_projection_pack()
    assert pack["player_count"] == 270  # 30 × 9
    for key, row in pack["players"].items():
        assert float(row["MIN"]) > 0, key
        for k in VECTOR_KEYS:
            assert k in row, (key, k)
            assert row[k] is not None
        assert "sigma" in row
        for k in VECTOR_KEYS:
            assert k in row["sigma"], (key, k)
            assert float(row["sigma"][k]) >= 0.0


def test_team_min_240_and_pts_within_residual_cap() -> None:
    rebased = load_rebased_team_prior()
    for team in TEAMS:
        rows = get_team_projections(team)
        assert abs(sum(float(r["MIN"]) for r in rows) - 240.0) < 1e-3, team
        ident = team_pts_identity(team)
        target = float(rebased["teams"][team]["implied_ppg"])
        assert abs(ident["target_pts"] - target) < 1e-6, team
        assert ident["pts_drift"] <= P.TEAM_REBASE_RESIDUAL_CAP + 1e-6, (
            team,
            ident["pts_drift"],
        )
        assert abs(ident["sum_pts"] - target) <= P.TEAM_REBASE_RESIDUAL_CAP + 1e-6, team


def test_sigma_computed_not_hardcoded_four() -> None:
    pack = load_player_projection_pack()
    sigmas = []
    for row in pack["players"].values():
        for k, v in row["sigma"].items():
            if k == "MIN":
                continue
            sigmas.append(float(v))
    assert sigmas
    # Must not be a constant-4 board; dispersion across players/stats required.
    distinct = {round(s, 4) for s in sigmas}
    assert len(distinct) > 50
    share_eq_four = sum(1 for s in sigmas if abs(s - 4.0) < 1e-9) / len(sigmas)
    assert share_eq_four < 0.01


def test_transaction_stars_on_new_team_only() -> None:
    pack = load_player_projection_pack()
    by_pid: dict[str, list] = {}
    for row in pack["players"].values():
        by_pid.setdefault(row["player_id"], []).append(row["team"])
    # Ch2 map movers that clear the 9-man cut
    assert by_pid.get("jamesle01") == ["PHI"]
    assert by_pid.get("antetgi01") == ["MIA"]
    assert by_pid.get("halibty01") == ["IND"]


def test_cfb_ball_osu_untouched() -> None:
    kei = json.loads(CFB_KEI.read_text(encoding="utf-8"))
    game = next(
        g
        for g in kei["games"]
        if g.get("away") == "BALL" and g.get("home") == "OSU" and g.get("week") == 1
    )
    assert abs(float(game["kei"]["kei_spread_home"]) - (-40.51)) < 1e-9


def test_no_prop_tag_fields_on_pack() -> None:
    pack = load_player_projection_pack()
    for row in pack["players"].values():
        for banned in ("tag", "edge_tag", "prop_tag", "play", "lean", "fantasy_points"):
            assert banned not in row
            assert banned not in (row.get("sigma") or {})
    # Pack must declare props dark
    does_not = " ".join(pack.get("does_not") or []).lower()
    assert "props" in does_not
    assert "play" in does_not
