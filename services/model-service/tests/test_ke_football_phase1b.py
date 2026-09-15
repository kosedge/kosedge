"""KE Football v1 Phase 1B — finishing repair, bakeoff, component validation.

No production promote. No Team Strength. No ATS objective.
"""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.ke_football import PHASE, PRODUCTION_PROMOTE, TAXONOMY
from src.services.ke_football.adapters import from_cfb_row, from_nfl_row
from src.services.ke_football.aggregate import build_team_games, team_game_components
from src.services.ke_football.bakeoff import (
    CANDIDATES,
    future_week_changes_any_method,
    run_bakeoff,
    unadjusted,
)
from src.services.ke_football.component_validate import (
    FORBIDDEN_OBJECTIVES,
    team_game_metric,
    validate_all_components,
)
from src.services.ke_football.finishing import build_drives, finishing_diagnosis
from src.services.ke_football.provenance import Status
from src.services.ke_football.scorecard import build_scorecard, grade_adjustment
from tests.test_ke_football_measurement import _cfb, _nfl, _slate


def test_phase1b_flags() -> None:
    assert PRODUCTION_PROMOTE is False
    assert TAXONOMY == ("RAW", "DERIVED", "ADJUSTED", "MODELED")
    assert PHASE == "measurement_phase1b"


def _drive_plays(*, result: str, yte_scrim: float, kickoff_yte: float = 35.0, xp: bool = False):
    rows = []
    rows.append(
        from_nfl_row(
            _nfl(
                play_id="ko",
                play_type="kickoff",
                posteam="AAA",
                defteam="BBB",
                yardline_100=kickoff_yte,
                fixed_drive="7",
                fixed_drive_result=result,
                epa=0.0,
            )
        )
    )
    rows.append(
        from_nfl_row(
            _nfl(
                play_id="p1",
                play_type="pass",
                posteam="AAA",
                defteam="BBB",
                yardline_100=yte_scrim,
                fixed_drive="7",
                fixed_drive_result=result,
                epa=0.2,
                yards_gained=8,
                touchdown=(result == "touchdown" and yte_scrim <= 10),
            )
        )
    )
    if result == "touchdown":
        extra = _nfl(
            play_id="xp",
            play_type="extra_point",
            posteam="AAA",
            defteam="BBB",
            yardline_100=15,
            fixed_drive="7",
            fixed_drive_result=result,
            extra_point_result="good",
            epa=0.0,
        )
        if xp:
            rows.append(from_nfl_row(extra))
    if result == "field goal":
        rows.append(
            from_nfl_row(
                _nfl(
                    play_id="fg",
                    play_type="field_goal",
                    posteam="AAA",
                    defteam="BBB",
                    yardline_100=22,
                    fixed_drive="7",
                    fixed_drive_result=result,
                    field_goal_result="made",
                    epa=0.1,
                )
            )
        )
    return [p for p in rows if p]


def test_kickoff_at_35_is_not_an_opportunity() -> None:
    """Phase 1 defect: KO at yl=35 shared fixed_drive → false opportunity."""
    plays = _drive_plays(result="punt", yte_scrim=72.0, kickoff_yte=35.0)
    drives = build_drives(plays)
    assert len(drives) == 1
    assert drives[0].scoring_opportunity is False
    assert drives[0].offense == "AAA"
    assert drives[0].points == 0


def test_scrimmage_inside_40_is_opportunity() -> None:
    plays = _drive_plays(result="punt", yte_scrim=38.0, kickoff_yte=35.0)
    drives = build_drives(plays)
    assert drives[0].scoring_opportunity is True
    assert drives[0].finished is False


def test_td_plus_xp_is_seven_from_drive_result() -> None:
    plays = _drive_plays(result="touchdown", yte_scrim=8.0, xp=True)
    drives = build_drives(plays)
    assert drives[0].points == 7
    assert drives[0].points_source == "fixed_drive_result+pat_flags"
    assert drives[0].finished is True
    assert drives[0].scoring_opportunity is True


def test_field_goal_result_is_three() -> None:
    plays = _drive_plays(result="field goal", yte_scrim=28.0)
    drives = build_drives(plays)
    assert drives[0].points == 3
    assert drives[0].finished is True


def test_opp_touchdown_credits_zero_to_offense() -> None:
    plays = _drive_plays(result="opp touchdown", yte_scrim=55.0)
    drives = build_drives(plays)
    assert drives[0].points == 0


def test_kickoff_only_drive_is_dropped() -> None:
    ko = from_nfl_row(
        _nfl(
            play_id="ko",
            play_type="kickoff",
            posteam="AAA",
            defteam="BBB",
            yardline_100=35,
            fixed_drive="99",
            fixed_drive_result="Touchdown",
            touchdown=True,
            epa=0.5,
        )
    )
    assert ko is not None
    assert build_drives([ko]) == []


def test_finishing_attaches_to_team_game() -> None:
    plays = _drive_plays(result="touchdown", yte_scrim=8.0, xp=True)
    games = build_team_games(plays)
    off = next(g for g in games if g.team == "AAA")
    assert off.n_drives == 1
    assert off.n_opp == 1
    assert off.opp_points == 7
    assert off.finished_opp == 1
    comps = team_game_components(off)
    assert comps["ke.ppo"].value == 7.0
    assert comps["ke.finish"].value == 1.0
    assert comps["ke.ppo"].notes.get("kickoff_excluded_from_opportunity") is True


def test_diagnosis_flags_kickoff_false_opportunity_rate() -> None:
    plays = _drive_plays(result="punt", yte_scrim=72.0, kickoff_yte=35.0)
    diag = finishing_diagnosis(plays)
    assert diag["calibrated"] is False
    assert diag["kickoff_false_opp_rate"] == 1.0
    assert diag["opportunity_rate"] == 0.0


def test_cfb_sparse_tfl_still_data_insufficient() -> None:
    plays = []
    for i in range(20):
        plays.append(from_cfb_row(_cfb(id=i, TFL=True if i == 0 else None)))
    games = build_team_games([p for p in plays if p])
    def_side = next(g for g in games if g.team == "Clemson")
    comps = team_game_components(def_side)
    assert comps["ke.disruption_tfl"].status == Status.DATA_INSUFFICIENT
    assert comps["ke.disruption_tfl"].value is None
    assert comps["ke.havoc"].status == Status.OMIT


def test_bakeoff_runs_and_allows_no_adjustment_winner() -> None:
    games = build_team_games(_slate())
    out = run_bakeoff(games, selection_weeks=(2, 2), confirmation_weeks=(2, 2), full_weeks=(2, 2))
    assert out["production_promote"] is False
    assert "ats" in out["forbidden"]
    assert "unadjusted" in out["candidates"]
    assert "loo_sos" in out["candidates"]
    assert out["winner"] in set(CANDIDATES) | {"NO_ADJUSTMENT_WINNER"}
    assert out["phase1_loo_sos_preserved"] is True


def test_bakeoff_leakage_future_week() -> None:
    games = build_team_games(_slate())
    from copy import deepcopy

    leak = deepcopy(games[0])
    leak.week = 3
    leak.game_id = "LEAK_FUTURE"
    leak.off_epa_sum = 50.0
    leak.off_epa_n = 80
    changed = future_week_changes_any_method(games, team=leak.team, as_of_week=3, future_game=leak)
    assert all(v is False for v in changed.values())


def test_unadjusted_trailing_on_slate() -> None:
    games = build_team_games(_slate())
    off, deff = unadjusted(games, team="AAA", as_of_week=3)
    assert off is not None
    assert deff is not None


def test_component_validate_forbidden_and_keys() -> None:
    games = build_team_games(_slate())
    out = validate_all_components(
        games, sport="nfl", season=2025, early_through=1, late_from=2
    )
    assert out["no_composite_weights"] is True
    assert set(FORBIDDEN_OBJECTIVES) <= set(out["forbidden_objectives"])
    ids = {r["id"] for r in out["components"]}
    assert "ke.off_eff" in ids
    assert "ke.ppo" in ids
    assert "ke.st" in ids
    assert "correlation_matrix" in out
    assert out["off_def_symmetry"]["n_teams"] >= 1
    aaa = next(g for g in games if g.team == "AAA")
    assert team_game_metric(aaa, "ke.off_eff") == aaa.off_epa


def test_scorecard_no_adjustment_winner_not_promoted() -> None:
    grade = grade_adjustment({"winner": "NO_ADJUSTMENT_WINNER", "candidates": {}})
    assert grade["winner"] == "NO_ADJUSTMENT_WINNER"
    assert grade["phase2_eligible"] is False
    card = build_scorecard(
        sport="nfl",
        validation={"components": []},
        inventory={"named_havoc_allowed": False, "events": []},
        bakeoff={"winner": "NO_ADJUSTMENT_WINNER", "candidates": {}},
        finishing={"calibrated": False, "ppo_repaired": 3.9},
    )
    assert card["production_promote"] is False
    havoc = next(g for g in card["grades"] if g["id"] == "ke.havoc")
    assert havoc["grade"] == "DATA_INSUFFICIENT"
    assert havoc["phase2_eligible"] is False
