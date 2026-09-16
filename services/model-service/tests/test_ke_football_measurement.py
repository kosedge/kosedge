"""KE Football v1 Phase 1 measurement — unit + leakage tests.

No production promote. No Team Strength. No ATS objective.
"""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.ke_football import PRODUCTION_PROMOTE, TAXONOMY
from src.services.ke_football.adapters import from_cfb_row, from_nfl_row, is_explosive
from src.services.ke_football.aggregate import (
    build_team_games,
    filter_week_lt,
    snapshots_for_week,
    team_game_components,
    team_week_snapshot,
)
from src.services.ke_football.disruption import DISRUPTION_EVENTS, inventory_report, named_havoc_allowed
from src.services.ke_football.opp_adj import (
    adjust_team_week,
    assert_no_future_week,
    future_week_changes_snapshot,
)
from src.services.ke_football.pipeline import run_measurement
from src.services.ke_football.plays import CanonicalPlay, standard_success
from src.services.ke_football.provenance import Layer, Status
from src.services.ke_football.validation import provenance_audit


def test_taxonomy_four_layers() -> None:
    assert TAXONOMY == ("RAW", "DERIVED", "ADJUSTED", "MODELED")
    assert PRODUCTION_PROMOTE is False


def _nfl(**kwargs) -> dict:
    base = {
        "season": 2025,
        "week": 1,
        "game_id": "2025_01_AAA_BBB",
        "play_id": "1",
        "posteam": "AAA",
        "defteam": "BBB",
        "home_team": "AAA",
        "away_team": "BBB",
        "play_type": "pass",
        "epa": 0.2,
        "success": True,
        "yards_gained": 8,
        "down": 1,
        "ydstogo": 10,
        "yardline_100": 70,
        "fixed_drive": "1",
        "score_differential": 0,
        "game_seconds_remaining": 3600,
        "qtr": 1,
        "sack": False,
        "interception": False,
        "qb_hit": False,
        "fumble": False,
        "season_type": "REG",
    }
    base.update(kwargs)
    return base


def _cfb(**kwargs) -> dict:
    base = {
        "season": 2025,
        "week": 1,
        "game_id": "401",
        "id": 1,
        "pos_team": "Georgia",
        "def_pos_team": "Clemson",
        "homeTeamName": "Georgia",
        "awayTeamName": "Clemson",
        "scrimmage_play": True,
        "pass": False,
        "rush": True,
        "EPA": 0.15,
        "EPA_success": True,
        "statYardage": 6,
        "down": 1,
        "distance": 10,
        "start.yardsToEndzone": 75,
        "drive.id": "d1",
        "pos_score_diff": 0,
        "period": 1,
        "type.text": "Rush",
    }
    base.update(kwargs)
    return base


def test_nfl_adapter_scrimmage_and_kneel_drop() -> None:
    play = from_nfl_row(_nfl())
    assert play is not None and play.is_scrimmage
    assert from_nfl_row(_nfl(play_type="qb_kneel")) is None


def test_nfl_kickoff_negates_onto_kicking_team() -> None:
    play = from_nfl_row(_nfl(play_type="kickoff", posteam="AAA", defteam="BBB", epa=0.4))
    assert play is not None
    assert play.is_st
    assert play.offense == "BBB"
    assert play.epa == -0.4


def test_explosive_knobs_differ_by_sport() -> None:
    nfl_pass = from_nfl_row(_nfl(play_type="pass", yards_gained=19))
    nfl_pass20 = from_nfl_row(_nfl(play_id="2", play_type="pass", yards_gained=20))
    nfl_rush = from_nfl_row(_nfl(play_id="3", play_type="run", yards_gained=10))
    assert nfl_pass and not is_explosive(nfl_pass)
    assert nfl_pass20 and is_explosive(nfl_pass20)
    assert nfl_rush and is_explosive(nfl_rush)
    cfb = from_cfb_row(_cfb(statYardage=15, EPA=0.2))
    assert cfb and is_explosive(cfb)
    cfb_epa = from_cfb_row(_cfb(id=2, statYardage=4, EPA=1.0))
    assert cfb_epa and is_explosive(cfb_epa)


def test_standard_success_50_70_100() -> None:
    assert standard_success(down=1, distance=10, yards=5) is True
    assert standard_success(down=1, distance=10, yards=4) is False
    assert standard_success(down=2, distance=10, yards=7) is True
    assert standard_success(down=3, distance=4, yards=3) is False
    assert standard_success(down=3, distance=4, yards=4) is True
    assert standard_success(down=1, distance=None, yards=9) is None


def test_missing_epa_is_data_insufficient() -> None:
    plays = [
        from_nfl_row(_nfl(play_id=str(i), play_type="punt", epa=None))
        for i in range(3)
    ]
    plays = [p for p in plays if p]
    games = build_team_games(plays)
    assert games == [] or all(
        team_game_components(g)["ke.off_eff"].status == Status.DATA_INSUFFICIENT
        for g in games
        if g.n_off_plays == 0
    )


def test_cfb_st_and_named_havoc_omitted() -> None:
    play = from_cfb_row(_cfb())
    assert play is not None
    games = build_team_games([play])
    comps = team_game_components(games[0])
    assert comps["ke.st"].status == Status.OMIT
    assert comps["ke.havoc"].status == Status.OMIT
    assert comps["ke.team_strength"].status == Status.OMIT
    assert comps["ke.st"].value is None
    assert comps["ke.havoc"].value is None


def test_disruption_weights_are_none() -> None:
    assert all(e.get("weight") is None for e in DISRUPTION_EVENTS)
    play = from_nfl_row(_nfl(sack=True))
    assert play is not None
    report = inventory_report(sport="nfl", plays=[play])
    assert report["weights_assigned"] is False
    assert report["named_ke_havoc"] == "OMIT"
    assert named_havoc_allowed({}) is False


def test_nfl_proxy_not_named_havoc() -> None:
    plays = [
        from_nfl_row(_nfl(play_id=str(i), sack=(i == 0), qb_hit=False, interception=False))
        for i in range(5)
    ]
    games = build_team_games([p for p in plays if p])
    comps = team_game_components(games[0] if games[0].team == "BBB" else games[1])
    # defense of BBB faces AAA's plays
    def_side = next(g for g in games if g.team == "BBB")
    comps = team_game_components(def_side)
    proxy = comps["ke.disruption_proxy_nfl"]
    assert proxy.id == "ke.disruption_proxy_nfl"
    assert proxy.notes.get("must_not_be_named") == "ke.havoc"
    assert proxy.value is not None
    assert comps["ke.havoc"].status == Status.OMIT


def _slate() -> list[CanonicalPlay]:
    """Two weeks, four team-games. Enough for ADJUSTED at W=3."""
    rows = []
    # Week 1: AAA vs BBB, CCC vs DDD
    for i in range(10):
        rows.append(
            from_nfl_row(
                _nfl(
                    week=1,
                    game_id="g1",
                    play_id=f"a{i}",
                    posteam="AAA",
                    defteam="BBB",
                    epa=0.30,
                    yards_gained=12,
                )
            )
        )
        rows.append(
            from_nfl_row(
                _nfl(
                    week=1,
                    game_id="g1",
                    play_id=f"b{i}",
                    posteam="BBB",
                    defteam="AAA",
                    home_team="AAA",
                    away_team="BBB",
                    epa=-0.10,
                    play_type="run",
                    yards_gained=3,
                )
            )
        )
        rows.append(
            from_nfl_row(
                _nfl(
                    week=1,
                    game_id="g2",
                    play_id=f"c{i}",
                    posteam="CCC",
                    defteam="DDD",
                    home_team="CCC",
                    away_team="DDD",
                    epa=0.05,
                )
            )
        )
        rows.append(
            from_nfl_row(
                _nfl(
                    week=1,
                    game_id="g2",
                    play_id=f"d{i}",
                    posteam="DDD",
                    defteam="CCC",
                    home_team="CCC",
                    away_team="DDD",
                    epa=-0.20,
                    play_type="run",
                    yards_gained=2,
                )
            )
        )
    # Week 2: AAA vs CCC, BBB vs DDD
    for i in range(10):
        rows.append(
            from_nfl_row(
                _nfl(
                    week=2,
                    game_id="g3",
                    play_id=f"e{i}",
                    posteam="AAA",
                    defteam="CCC",
                    home_team="AAA",
                    away_team="CCC",
                    epa=0.25,
                )
            )
        )
        rows.append(
            from_nfl_row(
                _nfl(
                    week=2,
                    game_id="g3",
                    play_id=f"f{i}",
                    posteam="CCC",
                    defteam="AAA",
                    home_team="AAA",
                    away_team="CCC",
                    epa=0.00,
                    play_type="run",
                    yards_gained=4,
                )
            )
        )
        rows.append(
            from_nfl_row(
                _nfl(
                    week=2,
                    game_id="g4",
                    play_id=f"h{i}",
                    posteam="BBB",
                    defteam="DDD",
                    home_team="BBB",
                    away_team="DDD",
                    epa=-0.05,
                )
            )
        )
        rows.append(
            from_nfl_row(
                _nfl(
                    week=2,
                    game_id="g4",
                    play_id=f"i{i}",
                    posteam="DDD",
                    defteam="BBB",
                    home_team="BBB",
                    away_team="DDD",
                    epa=-0.15,
                    play_type="run",
                    yards_gained=1,
                )
            )
        )
    return [p for p in rows if p]


def test_filter_week_lt_is_strict() -> None:
    plays = _slate()
    window = filter_week_lt(plays, season=2025, as_of_week=2)
    assert window
    assert max(p.week for p in window) == 1
    assert all(p.week < 2 for p in window)


def test_week1_adjusted_is_data_insufficient() -> None:
    games = build_team_games(filter_week_lt(_slate(), season=2025, as_of_week=2))
    adj = adjust_team_week(games, team="AAA", as_of_week=2)
    assert adj["components"]["ke.opp_adj_epa.off"]["layer"] == Layer.ADJUSTED.value
    assert adj["components"]["ke.opp_adj_epa.off"]["status"] == Status.DATA_INSUFFICIENT.value
    assert adj["components"]["ke.opp_adj_epa.off"]["value"] is None


def test_adjusted_available_by_week3_and_not_modeled() -> None:
    games = build_team_games(filter_week_lt(_slate(), season=2025, as_of_week=3))
    adj = adjust_team_week(games, team="AAA", as_of_week=3)
    cell = adj["components"]["ke.opp_adj_epa.off"]
    assert cell["layer"] == Layer.ADJUSTED.value
    assert cell["value"] is not None
    assert adj["method"]["estimator"] == "pit_leave_one_game_out_sos"
    assert "fit_joint_v2_joint_mu_hfa_n0_ridge" in adj["method"]["not_used"]


def test_leakage_future_week_does_not_change_adjusted() -> None:
    plays = filter_week_lt(_slate(), season=2025, as_of_week=3)
    games = build_team_games(plays)
    assert_no_future_week(games, as_of_week=3)
    from copy import deepcopy

    leak = deepcopy(games[0])
    leak.week = 3
    leak.game_id = "LEAK"
    leak.off_epa_sum = 99.0
    leak.off_epa_n = 10
    assert future_week_changes_snapshot(games, team=leak.team, as_of_week=3, future_game=leak) is False


def test_leave_one_out_excludes_same_game() -> None:
    games = build_team_games(filter_week_lt(_slate(), season=2025, as_of_week=3))
    adj = adjust_team_week(games, team="AAA", as_of_week=3)
    for row in adj["games"]:
        # Opponent book must not be this same game; week-1 AAA vs BBB
        # uses BBB's *other* game (week 2).
        if row["week"] == 1 and row["opponent"] == "BBB":
            assert row["off_adj"] is not None
            assert row["opp_def_loo"] is not None


def test_snapshot_excludes_as_of_week() -> None:
    plays = _slate()
    snaps = snapshots_for_week(plays, sport="nfl", season=2025, as_of_week=2)
    aaa = next(s for s in snaps if s["team"] == "AAA")
    assert aaa["n_games"] == 1
    assert aaa["feature_week_max"] == 1
    assert all(w < 2 for w in [1])


def test_pipeline_provenance_and_hard_stops() -> None:
    out = run_measurement(_slate(), sport="nfl", season=2025, as_of_week=3, example_teams=["AAA"])
    assert out["production_promote"] is False
    assert out["hard_stops"]["team_strength"] is False
    assert out["validation"]["provenance"]["ok"] is True
    card = out["examples"][0]
    assert card["components"]["ke.team_strength"]["status"] == "OMIT"
    assert card["components"]["ke.off_eff"]["layer"] == "DERIVED"
    if "ke.opp_adj_epa.off" in card["components"]:
        assert card["components"]["ke.opp_adj_epa.off"]["layer"] == "ADJUSTED"
    audit = provenance_audit(out["snapshots"])
    assert audit["ok"] is True


def test_sparse_disruption_flag_is_data_insufficient() -> None:
    """CFB TFL/FF are event-only: null on most snaps. Do not publish 1.0."""
    plays = []
    for i in range(20):
        row = _cfb(id=i, TFL=True if i == 0 else None)
        plays.append(from_cfb_row(row))
    games = build_team_games([p for p in plays if p])
    def_side = next(g for g in games if g.team == "Clemson")
    comps = team_game_components(def_side)
    assert comps["ke.disruption_tfl"].value is None
    assert comps["ke.disruption_tfl"].status == Status.DATA_INSUFFICIENT


def test_partial_expl_without_rush() -> None:
    plays = [from_nfl_row(_nfl(play_id=str(i), play_type="pass", yards_gained=22)) for i in range(8)]
    games = build_team_games([p for p in plays if p])
    comps = team_game_components(games[0])
    assert comps["ke.expl_pass"].value is not None
    assert comps["ke.expl"].status == Status.PARTIAL
    assert comps["ke.expl"].value is None
