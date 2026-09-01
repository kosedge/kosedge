"""NBA Chapter 2 — roster × minutes rebase gates."""

from __future__ import annotations

import json
from pathlib import Path

from src.services.nba_season_engine import priors as P
from src.services.nba_season_engine.roster_minutes import (
    get_rebased_team,
    get_team_minutes,
    load_minutes_grid,
    load_player_talent_pack,
    load_rebased_team_prior,
    load_transactions,
)
from src.services.nba_season_engine.team_prior import load_team_prior_pack

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


def test_ch2_constants_and_ch1_shrink_untouched() -> None:
    assert P.ENGINE_VERSION == "nba-season-engine-v0.1"
    assert P.TEAM_CARRY_SHRINK == 0.85
    assert P.PLAYER_YEAR_WEIGHTS == {
        "2023-24": 0.20,
        "2024-25": 0.30,
        "2025-26": 0.50,
    }
    assert P.MINUTE_GRID_SUM == 240
    assert P.TEAM_REBASE_RESIDUAL_CAP == 3.0
    ch1 = load_team_prior_pack(force=True)
    assert ch1["TEAM_CARRY_SHRINK"] == 0.85


def test_thirty_teams_minutes_sum_240() -> None:
    grid = load_minutes_grid()
    assert grid["present"] is True
    assert len(grid["teams"]) == 30
    for team in TEAMS:
        rows = get_team_minutes(team)
        assert len(rows) == 9, team
        assert abs(sum(r["minutes"] for r in rows) - 240.0) < 1e-6, team


def test_rebased_residual_within_cap() -> None:
    pack = load_rebased_team_prior()
    assert pack["TEAM_REBASE_RESIDUAL_CAP"] == 3.0
    assert pack["team_count"] == 30
    for team, row in pack["teams"].items():
        assert abs(float(row["residual"])) <= 3.0 + 1e-9, team
        assert abs(float(row["residual_raw"])) >= abs(float(row["residual"])) - 1e-9


def test_pace_ppg_sanity_no_ghosts() -> None:
    pack = load_rebased_team_prior()
    ppgs = [float(r["implied_ppg"]) for r in pack["teams"].values()]
    assert min(ppgs) >= 100.0
    assert max(ppgs) <= 130.0
    for row in pack["teams"].values():
        assert 90.0 <= float(row["pace"]) <= 110.0


def test_transaction_stars_not_on_old_team_grid() -> None:
    tx = load_transactions()
    grid = load_minutes_grid()["teams"]
    talent = load_player_talent_pack()["players"]
    for row in tx["transactions"]:
        pid = row["player_id"]
        fr, to = row["from_team"], row["to_team"]
        assert talent[pid]["team_2026_27"] == to
        on_old = any(p["player_id"] == pid for p in grid.get(fr) or [])
        assert not on_old, (pid, fr)
        # High-talent movers should land on new rotation; low-BPM signings may be roster-only.
        on_new = any(p["player_id"] == pid for p in grid.get(to) or [])
        if float(talent[pid]["talent_bpm"]) >= 1.0:
            assert on_new, (pid, to)


def test_cfb_ball_osu_untouched() -> None:
    kei = json.loads(CFB_KEI.read_text(encoding="utf-8"))
    game = next(
        g
        for g in kei["games"]
        if g.get("away") == "BALL" and g.get("home") == "OSU" and g.get("week") == 1
    )
    assert abs(float(game["kei"]["kei_spread_home"]) - (-40.51)) < 1e-9


def test_get_rebased_team_okc() -> None:
    okc = get_rebased_team("OKC")
    assert okc is not None
    assert okc["net_rating"] > 0


def test_no_multi_stint_minute_double_count() -> None:
    """BR 2TM/3TM/4TM totals must not be summed with team splits."""
    talent = load_player_talent_pack()["players"]
    for pid, row in talent.items():
        for season, s in row["seasons"].items():
            assert float(s["mp"]) <= 3500.0, (pid, season, s["mp"])
            assert float(s["g"]) <= 100.0, (pid, season, s["g"])


def test_injury_carry_haliburton_on_ind_grid() -> None:
    """Stars who missed 2025-26 still land on last-known 2026-27 roster."""
    talent = load_player_talent_pack()["players"]
    hali = talent["halibty01"]
    assert hali["roster_carry"] is True
    assert hali["team_2026_27"] == "IND"
    assert hali["talent_bpm"] > 5.0
    ind = get_team_minutes("IND")
    assert any(p["player_id"] == "halibty01" for p in ind)
    assert ind[0]["player_id"] == "halibty01"
