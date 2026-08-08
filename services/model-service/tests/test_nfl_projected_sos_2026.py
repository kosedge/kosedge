"""Smell tests for 2026 Projected Schedule Difficulty (Future SOS)."""

from __future__ import annotations

from copy import deepcopy

from src.services.nfl_season_engine.adjusted_sos import (
    PriorGameContext,
    apply_past_sos_to_package,
    compute_team_past_sos,
)
from src.services.nfl_season_engine.continuity_score import (
    build_team_continuity_from_inputs,
)
from src.services.nfl_season_engine.efficiency_backbone import (
    TeamEfficiencyPackage,
    UnitEfficiency,
    hierarchy_composite,
    package_to_strength_indices,
)
from src.services.nfl_season_engine.game_script import build_game_script
from src.services.nfl_season_engine.loaders import build_demo_universe
from src.services.nfl_season_engine.projected_sos import (
    analytic_expected_wins_from_schedule,
    assert_strengths_unchanged,
    compute_league_projected_sos,
    compute_team_projected_sos,
    path_difficulty_grade,
)
from src.services.nfl_season_engine.qb_premium import (
    QbQualitySignal,
    apply_qb_premium_to_payload,
    build_team_qb_premium_from_inputs,
)
from src.services.nfl_season_engine.season_sim import simulate_full_season
from src.services.nfl_season_engine.survivor import evaluate_survivor
from src.services.nfl_season_engine.team_strength import (
    copy_strength_book,
    initialize_strengths,
)
from src.services.nfl_season_engine.types import (
    EngineUniverse,
    ScheduledGame,
    TeamStrengthState,
)


def _equal_pr_strength(team: str) -> TeamStrengthState:
    return TeamStrengthState(
        team=team,
        offense_index=1.05,
        defense_index=1.05,
        full_strength_offense_index=1.05,
        full_strength_defense_index=1.05,
        source="test_equal_pr",
        games_played=0,
        qb_premium=0.0,
        drivers={"blend": {"w_prior": 1.0, "w_current": 0.0}},
    )


def _elite_strength(team: str) -> TeamStrengthState:
    return TeamStrengthState(
        team=team,
        offense_index=1.18,
        defense_index=1.14,
        full_strength_offense_index=1.18,
        full_strength_defense_index=1.14,
        source="test_elite",
        games_played=0,
    )


def _weak_strength(team: str) -> TeamStrengthState:
    return TeamStrengthState(
        team=team,
        offense_index=0.88,
        defense_index=0.90,
        full_strength_offense_index=0.88,
        full_strength_defense_index=0.90,
        source="test_weak",
        games_played=0,
    )


def _avg_strength(team: str) -> TeamStrengthState:
    return TeamStrengthState(
        team=team,
        offense_index=1.0,
        defense_index=1.0,
        full_strength_offense_index=1.0,
        full_strength_defense_index=1.0,
        source="test_avg",
        games_played=0,
    )


def _two_team_outlook_universe() -> EngineUniverse:
    """Equal-PR SOFT vs HARD with opposite 17-game opponent books."""
    soft_opps = [f"E{i}" for i in range(1, 10)] + [f"SM{i}" for i in range(1, 9)]
    hard_opps = [f"H{i}" for i in range(1, 10)] + [f"HM{i}" for i in range(1, 9)]
    strengths: dict[str, TeamStrengthState] = {
        "SOFT": _equal_pr_strength("SOFT"),
        "HARD": _equal_pr_strength("HARD"),
    }
    for t in soft_opps[:9]:
        strengths[t] = _weak_strength(t)
    for t in soft_opps[9:]:
        strengths[t] = _avg_strength(t)
    for t in hard_opps[:9]:
        strengths[t] = _elite_strength(t)
    for t in hard_opps[9:]:
        strengths[t] = _avg_strength(t)

    schedule: list[ScheduledGame] = []
    for week, (s_opp, h_opp) in enumerate(zip(soft_opps, hard_opps), start=1):
        # SOFT plays mostly at home vs weak; HARD mostly on road vs elite.
        schedule.append(
            ScheduledGame(
                season=2026,
                week=week,
                game_id=f"2026_{week:02d}_SOFT_{s_opp}",
                home_team="SOFT",
                away_team=s_opp,
            )
        )
        schedule.append(
            ScheduledGame(
                season=2026,
                week=week,
                game_id=f"2026_{week:02d}_HARD_{h_opp}",
                home_team=h_opp,
                away_team="HARD",
            )
        )

    # Minimal rosters so season sim path can run if needed.
    from src.services.nfl_season_engine.types import PlayerRole

    rosters = {
        t: [
            PlayerRole(
                player_key=f"{t}-qb",
                player_name=f"{t} QB",
                team=t,
                position="QB",
                depth_order=1,
                snap_share=1.0,
                source="test",
            )
        ]
        for t in strengths
    }
    return EngineUniverse(
        season=2026,
        schedule=schedule,
        strengths=strengths,
        rosters=rosters,
        notes={"mode": "test", "schedule_source": "synthetic_soft_hard"},
    )


def test_soft_slate_higher_expected_wins_than_brutal() -> None:
    """Smell 1: equal PR + soft slate → higher expected wins than brutal slate."""
    uni = _two_team_outlook_universe()
    soft_sos = compute_team_projected_sos("SOFT", uni.schedule, uni.strengths)
    hard_sos = compute_team_projected_sos("HARD", uni.schedule, uni.strengths)
    assert soft_sos.projected_sos_2026 < hard_sos.projected_sos_2026
    assert soft_sos.difficulty_band in ("easy", "average")
    assert hard_sos.difficulty_band in ("hard", "average")

    soft_wins = analytic_expected_wins_from_schedule(
        "SOFT", uni.schedule, uni.strengths
    )
    hard_wins = analytic_expected_wins_from_schedule(
        "HARD", uni.schedule, uni.strengths
    )
    assert soft_wins > hard_wins + 1.5


def test_intrinsic_pr_unchanged_by_projected_sos() -> None:
    """Smell 2 / HARD RULE: intrinsic PR at g=0 unchanged by Future SOS."""
    uni = build_demo_universe(2026)
    before = copy_strength_book(uni.strengths)
    before_rank = sorted(
        (
            (
                t,
                float(s.full_strength_offense_index)
                + float(s.full_strength_defense_index),
            )
            for t, s in before.items()
        ),
        key=lambda x: (-x[1], x[0]),
    )

    sos = compute_league_projected_sos(uni)
    assert len(sos) == 32
    after = uni.strengths
    assert_strengths_unchanged(before, after)

    after_rank = sorted(
        (
            (
                t,
                float(s.full_strength_offense_index)
                + float(s.full_strength_defense_index),
            )
            for t, s in after.items()
        ),
        key=lambda x: (-x[1], x[0]),
    )
    assert [t for t, _ in before_rank] == [t for t, _ in after_rank]

    # Season sim attaches SOS to outlook but must not reshuffle PR book.
    result = simulate_full_season(uni, n_sims=2, seed=7, include_diagnostics=True)
    assert_strengths_unchanged(before, uni.strengths)
    sample = next(iter(result.team_wins.values()))
    assert "projected_sos_2026" in sample
    assert "schedule_difficulty" in sample
    assert result.diagnostics["projected_sos_2026"]["intrinsic_pr_unchanged"] is True


def test_past_sos_polarity_still_intact() -> None:
    """Smell 3: Past SOS soft/hard polarity on prior still intact."""
    from src.services.nfl_season_engine.adjusted_sos import OpponentRating

    weekly = {}
    season_book = {
        "BAD1": OpponentRating(off_epa=-0.05, def_epa=0.10, source="approximate"),
        "GOOD1": OpponentRating(off_epa=0.12, def_epa=-0.08, source="approximate"),
    }
    soft = compute_team_past_sos(
        "SOFT",
        [
            PriorGameContext(team="SOFT", week=3, opponent="BAD1", is_home=True),
            PriorGameContext(team="SOFT", week=4, opponent="BAD1", is_home=True),
        ],
        raw_off_epa=0.08,
        raw_def_epa_allowed=0.0,
        weekly_book=weekly,
        season_book=season_book,
        league_off_epa=0.0,
        league_def_epa=0.0,
    )
    hard = compute_team_past_sos(
        "HARD",
        [
            PriorGameContext(team="HARD", week=3, opponent="GOOD1", is_home=False),
            PriorGameContext(team="HARD", week=4, opponent="GOOD1", is_home=False),
        ],
        raw_off_epa=0.08,
        raw_def_epa_allowed=0.0,
        weekly_book=weekly,
        season_book=season_book,
        league_off_epa=0.0,
        league_def_epa=0.0,
    )
    soft_pkg = apply_past_sos_to_package(
        TeamEfficiencyPackage(
            team="SOFT",
            offense=UnitEfficiency(epa_per_play=0.08, plays=1000),
            defense=UnitEfficiency(epa_per_play=0.0, plays=1000),
            games_played=17,
        ),
        soft,
    )
    hard_pkg = apply_past_sos_to_package(
        TeamEfficiencyPackage(
            team="HARD",
            offense=UnitEfficiency(epa_per_play=0.08, plays=1000),
            defense=UnitEfficiency(epa_per_play=0.0, plays=1000),
            games_played=17,
        ),
        hard,
    )
    assert soft_pkg.offense.epa_per_play < 0.08
    assert hard_pkg.offense.epa_per_play > 0.08
    assert soft.future_schedule_excluded is True


def test_continuity_and_qb_premium_still_visible() -> None:
    """Smell 4: Continuity + QB premium still visible on strength."""
    cont = build_team_continuity_from_inputs(
        "KC",
        prior_qb=("15", "Mahomes"),
        current_qb=("15", "Mahomes"),
        prior_qb_on_roster=True,
        staff={"new_hc": False, "new_oc": False, "status": "approximate"},
        skill_return_share=0.88,
        ol_return_share=0.75,
        roster_return_share=0.62,
        major_churn=False,
    )
    assert cont.continuity_score > 0.55

    elite = build_team_qb_premium_from_inputs(
        "KC",
        starter=("15", "Mahomes"),
        prior_qb=("15", "Mahomes"),
        starter_signal=QbQualitySignal(
            player_id="15",
            player_name="Mahomes",
            dropbacks=550,
            epa_per_play=0.22,
            success_rate=0.52,
            cpoe=4.5,
            source="epa_process",
            fidelity="real",
        ),
        prior_signal_dropbacks=600,
    )
    payload = {
        "offense_index": 1.08,
        "defense_index": 1.05,
        "full_strength_offense_index": 1.08,
        "full_strength_defense_index": 1.05,
        "qb_premium": 0.0,
        "drivers": {},
    }
    applied = apply_qb_premium_to_payload(payload, elite)
    assert float(applied["qb_premium"]) > 0.01
    assert float(applied["offense_index"]) > float(payload["offense_index"])

    # Future SOS must not clobber those strength signals when attached.
    strengths = initialize_strengths(
        {
            "KC": {
                **applied,
                "qb_premium": applied["qb_premium"],
                "games_played": 0,
            },
            "NE": {
                "offense_index": 0.95,
                "defense_index": 0.97,
                "full_strength_offense_index": 0.95,
                "full_strength_defense_index": 0.97,
                "games_played": 0,
            },
        }
    )
    schedule = [
        ScheduledGame(
            season=2026,
            week=1,
            game_id="2026_01_KC_NE",
            home_team="KC",
            away_team="NE",
        )
    ]
    before = deepcopy(
        {
            t: (
                s.offense_index,
                s.defense_index,
                s.qb_premium,
                s.full_strength_offense_index,
            )
            for t, s in strengths.items()
        }
    )
    compute_team_projected_sos("KC", schedule, strengths)
    after = {
        t: (
            s.offense_index,
            s.defense_index,
            s.qb_premium,
            s.full_strength_offense_index,
        )
        for t, s in strengths.items()
    }
    assert before == after
    assert strengths["KC"].qb_premium > 0.01


def test_survivor_ranks_easier_vs_harder_path() -> None:
    """Smell 5: survivor can rank easier vs harder path coherently."""
    uni = _two_team_outlook_universe()
    soft = compute_team_projected_sos("SOFT", uni.schedule, uni.strengths)
    hard = compute_team_projected_sos("HARD", uni.schedule, uni.strengths)
    order = {"A": 0, "B": 1, "C": 2, "D": 3, "F": 4}
    assert order[path_difficulty_grade(soft.projected_sos_2026)] < order[
        path_difficulty_grade(hard.projected_sos_2026)
    ]

    demo = build_demo_universe(2026)
    result = evaluate_survivor(demo, week=1, n_sims=8, seed=3, include_diagnostics=True)
    assert any("projected_sos_2026" in r for r in result.all_teams_week)
    assert any("path_difficulty_grade" in r for r in result.ranked_picks)
    assert result.diagnostics.get("projected_sos_2026", {}).get(
        "intrinsic_pr_unchanged"
    )


def test_edge_board_game_lines_not_driven_by_season_sos() -> None:
    """Smell 6: game-level lines from matchup strengths, not season SOS blob."""
    uni = _two_team_outlook_universe()
    soft_sos = compute_team_projected_sos("SOFT", uni.schedule, uni.strengths)
    hard_sos = compute_team_projected_sos("HARD", uni.schedule, uni.strengths)

    # Equal intrinsic PR → nearly identical game WP when facing the same opponent
    # at the same venue, regardless of season SOS blob.
    common_opp = "SM1"
    g_soft = ScheduledGame(
        season=2026, week=1, game_id="x1", home_team="SOFT", away_team=common_opp
    )
    g_hard = ScheduledGame(
        season=2026, week=1, game_id="x2", home_team="HARD", away_team=common_opp
    )
    import random

    script_soft, _ = build_game_script(
        g_soft, uni.strengths, rng=random.Random(1), realized=False
    )
    script_hard, _ = build_game_script(
        g_hard, uni.strengths, rng=random.Random(1), realized=False
    )
    assert abs(script_soft.home_win_prob - script_hard.home_win_prob) < 0.02
    # Season SOS differs a lot, but game line does not follow the SOS blob.
    assert abs(soft_sos.projected_sos_2026 - hard_sos.projected_sos_2026) > 0.05

    # build_game_script signature has no projected_sos parameter.
    import inspect

    sig = inspect.signature(build_game_script)
    assert "projected_sos" not in sig.parameters
    assert "sos" not in sig.parameters


def test_drivers_expose_opponents_and_home_away() -> None:
    uni = _two_team_outlook_universe()
    sos = compute_team_projected_sos("HARD", uni.schedule, uni.strengths)
    d = sos.drivers()
    assert d["intrinsic_pr_unchanged"] is True
    assert d["home_away_balance"]["away"] > d["home_away_balance"]["home"]
    assert len(d["toughest_opponents"]) >= 1
    assert len(d["easiest_opponents"]) >= 1
    assert sos.early_sos is not None
    assert sos.late_sos is not None


def test_packaged_hierarchy_composite_untouched_by_future_sos_math() -> None:
    """Future SOS does not enter hierarchy_composite / package indices."""
    pkg = TeamEfficiencyPackage(
        team="BUF",
        offense=UnitEfficiency(epa_per_play=0.06, plays=1000),
        defense=UnitEfficiency(epa_per_play=-0.04, plays=1000),
        games_played=0,
    )
    c0 = hierarchy_composite(pkg)
    idx0 = package_to_strength_indices(pkg)
    # Computing projected SOS on a universe must not require mutating packages.
    strengths = initialize_strengths(
        {
            "BUF": {
                **{
                    "offense_index": idx0["offense_index"],
                    "defense_index": idx0["defense_index"],
                    "full_strength_offense_index": idx0["offense_index"],
                    "full_strength_defense_index": idx0["defense_index"],
                    "games_played": 0,
                }
            },
            "MIA": {
                "offense_index": 1.0,
                "defense_index": 1.0,
                "full_strength_offense_index": 1.0,
                "full_strength_defense_index": 1.0,
                "games_played": 0,
            },
        }
    )
    schedule = [
        ScheduledGame(
            season=2026,
            week=1,
            game_id="g",
            home_team="BUF",
            away_team="MIA",
        )
    ]
    compute_team_projected_sos("BUF", schedule, strengths)
    assert hierarchy_composite(pkg) == c0
    assert package_to_strength_indices(pkg) == idx0
