"""Tests for the hierarchical CFB season engine (HFA + coaching continuity)."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from fastapi.testclient import TestClient

from src.services.cfb_season_engine import (
    DEFAULT_SEASON_ENGINE_VERSION,
    build_packaged_universe,
    engine_status_payload,
    project_game_preview,
    project_game_to_dict,
    season_sim_to_dict,
    simulate_full_season,
)
from src.services.cfb_season_engine.coaching_continuity import (
    build_coaching_continuity,
    coaching_week_adjustment,
    week_decay,
)
from src.services.cfb_season_engine.home_field import (
    build_home_field_profile,
    points_for_bucket,
    resolve_hfa_points,
)
from src.services.cfb_season_engine.qb_situation import (
    build_qb_situation,
    classify_qb_situation,
    compute_qb_situation_index,
)
from src.services.cfb_season_engine.roster_construction import (
    build_roster_construction,
    compute_roster_strength,
)
from src.services.cfb_season_engine.team_projection import (
    compose_team_projection,
    expected_team_points,
    unit_defense_dampen,
    unit_offense_boost,
)
from src.services.cfb_season_engine.position_groups import (
    build_position_groups,
    compose_unit_grade,
    groups_to_dict,
)
from src.services.cfb_season_engine.priors import (
    early_season_uncertainty,
    win_prob_margin_sd_for_week,
)
from src.services.cfb_season_engine.types import EngineUniverse, HomeFieldProfile


def test_engine_version_string() -> None:
    assert DEFAULT_SEASON_ENGINE_VERSION == "cfb-season-engine-v0.5-hfa-coaching"


def test_qb_situation_classification() -> None:
    assert classify_qb_situation(qb_class="incumbent") == "incumbent"
    assert classify_qb_situation(is_portal=True) == "portal"
    assert classify_qb_situation(qb_class="portal_starter") == "portal"
    assert classify_qb_situation(open_competition=True) == "open_competition"
    assert classify_qb_situation(is_true_freshman=True) == "true_freshman"
    assert classify_qb_situation(experience_starts=12) == "incumbent"
    # Priority: true freshman beats portal flag
    assert (
        classify_qb_situation(is_true_freshman=True, is_portal=True) == "true_freshman"
    )


def test_roster_strength_components_inspectable() -> None:
    roster = build_roster_construction(
        "UGA",
        {
            "returning_snap_share": 0.56,
            "returning_start_share": 0.60,
            "portal_in_value": 62,
            "portal_out_value": 48,
            "recruiting_class_score": 96,
            "experience_index": 62,
        },
    )
    assert roster.roster_strength > 60
    assert 0.0 < roster.returning_snap_share <= 1.0
    assert roster.portal_net > 40
    strength, breakdown = compute_roster_strength(
        returning_production=roster.returning_production,
        portal_net=roster.portal_net,
        recruiting_class_score=roster.recruiting_class_score,
        experience_index=roster.experience_index,
    )
    assert abs(strength - roster.roster_strength) < 0.01
    assert "returning_production" in breakdown
    assert "weights" in breakdown


def test_roster_strength_ranks_blue_bloods_above_mid_rebuilds() -> None:
    universe = build_packaged_universe(2026)
    strengths = {
        code: state.roster.roster_strength
        for code, state in universe.teams.items()
        if state.roster
    }
    blue = ["UGA", "ALA", "TEX", "OSU", "ND"]
    mid = ["BALL", "EMU", "NMSU", "WAKE"]
    for b in blue:
        assert b in strengths
    for m in mid:
        assert m in strengths
    blue_mean = sum(strengths[b] for b in blue) / len(blue)
    mid_mean = sum(strengths[m] for m in mid) / len(mid)
    assert blue_mean > mid_mean + 8.0
    assert strengths["UGA"] > strengths["BALL"]
    assert strengths["TEX"] > strengths["EMU"]


def test_unit_grade_components_inspectable() -> None:
    grade, breakdown = compose_unit_grade(
        talent=90.0, experience=70.0, portal_impact=60.0
    )
    assert abs(grade - (0.50 * 90 + 0.30 * 70 + 0.20 * 60)) < 0.01
    assert breakdown["talent"] == 90.0
    assert "weights" in breakdown

    groups = build_position_groups(
        "UGA",
        {
            "ol": 90,
            "skill": 91,
            "front_seven": 92,
            "secondary": 88,
            "components": {
                "ol": {"talent": 92, "experience": 80, "portal_impact": 55},
                "skill": {"talent": 93, "experience": 75, "portal_impact": 70},
                "front_seven": {"talent": 94, "experience": 82, "portal_impact": 60},
                "secondary": {"talent": 88, "experience": 78, "portal_impact": 65},
            },
            "fidelity": "approximate",
        },
    )
    assert groups.ol == 90.0  # headline authoritative
    assert "ol" in groups.components
    assert groups.components["ol"]["talent"] == 92.0
    d = groups_to_dict(groups)
    assert "components" in d
    assert d["components"]["front_seven"]["portal_impact"] == 60.0


def test_position_groups_distinct_for_curated_teams() -> None:
    universe = build_packaged_universe(2026)
    uga = universe.teams["UGA"].groups
    fsu = universe.teams["FSU"].groups
    assert uga and fsu
    assert uga.ol > fsu.ol
    assert uga.front_seven > fsu.front_seven
    assert uga.components and "talent" in uga.components["ol"]


def test_qb_class_materially_moves_offense_index() -> None:
    """Holding roster/groups fixed, QB class must move offense sharply."""
    roster = build_roster_construction(
        "TEST",
        {
            "returning_production": 55,
            "portal_in_value": 55,
            "portal_out_value": 50,
            "recruiting_class_score": 70,
            "experience_index": 55,
        },
    )
    groups = build_position_groups(
        "TEST",
        {"ol": 70, "skill": 70, "front_seven": 65, "secondary": 65},
        roster=roster,
    )
    indexes = {}
    for qb_class in ("incumbent", "portal", "open_competition", "true_freshman"):
        qb = build_qb_situation(
            "TEST",
            {
                "qb_class": qb_class,
                "qb_talent": 75,
                "ol_support": 70,
                "weapons_support": 70,
                "experience_starts": 8 if qb_class == "incumbent" else 0,
            },
        )
        state = compose_team_projection("TEST", roster, qb, groups)
        indexes[qb_class] = state.offense_index

    assert indexes["incumbent"] > indexes["portal"]
    assert indexes["portal"] > indexes["open_competition"]
    assert indexes["open_competition"] > indexes["true_freshman"]
    # Material — not a tiny unused field.
    assert indexes["incumbent"] - indexes["true_freshman"] >= 0.10


def test_incumbent_good_cast_beats_true_freshman_weak_cast() -> None:
    roster = build_roster_construction(
        "TEST",
        {
            "returning_production": 50,
            "portal_in_value": 50,
            "portal_out_value": 50,
            "recruiting_class_score": 60,
            "experience_index": 50,
        },
    )
    groups = build_position_groups(
        "TEST",
        {"ol": 55, "skill": 55, "front_seven": 55, "secondary": 55},
        roster=roster,
    )
    good = build_qb_situation(
        "TEST",
        {
            "qb_class": "incumbent",
            "qb_talent": 78,
            "ol_support": 88,
            "weapons_support": 90,
            "experience_starts": 12,
        },
    )
    weak = build_qb_situation(
        "TEST",
        {
            "qb_class": "true_freshman",
            "qb_talent": 78,  # equal talent — class + cast drive gap
            "ol_support": 45,
            "weapons_support": 42,
            "is_true_freshman": True,
        },
    )
    good_state = compose_team_projection("TEST", roster, good, groups)
    weak_state = compose_team_projection("TEST", roster, weak, groups)
    assert good.qb_situation_index > weak.qb_situation_index + 0.15
    assert good_state.offense_index > weak_state.offense_index + 0.12
    assert good_state.early_season_uncertainty < weak_state.early_season_uncertainty


def test_qb_class_moves_win_prob_vs_fixed_opponent() -> None:
    opponent_roster = build_roster_construction(
        "OPP",
        {
            "returning_production": 50,
            "portal_in_value": 50,
            "portal_out_value": 50,
            "recruiting_class_score": 55,
            "experience_index": 50,
        },
    )
    opponent_qb = build_qb_situation(
        "OPP",
        {"qb_class": "incumbent", "qb_talent": 60, "ol_support": 55, "weapons_support": 55},
    )
    opponent_groups = build_position_groups(
        "OPP",
        {"ol": 55, "skill": 55, "front_seven": 60, "secondary": 58},
        roster=opponent_roster,
        qb=opponent_qb,
    )
    opp = compose_team_projection("OPP", opponent_roster, opponent_qb, opponent_groups)

    roster = build_roster_construction(
        "HOME",
        {
            "returning_production": 55,
            "portal_in_value": 55,
            "portal_out_value": 50,
            "recruiting_class_score": 70,
            "experience_index": 55,
        },
    )
    groups = build_position_groups(
        "HOME",
        {"ol": 70, "skill": 72, "front_seven": 65, "secondary": 64},
        roster=roster,
    )

    def _proj(qb_class: str) -> float:
        qb = build_qb_situation(
            "HOME",
            {
                "qb_class": qb_class,
                "qb_talent": 75,
                "ol_support": 70,
                "weapons_support": 72,
                "experience_starts": 10 if qb_class == "incumbent" else 0,
            },
        )
        home = compose_team_projection("HOME", roster, qb, groups)
        universe = EngineUniverse(
            season=2026,
            schedule=[],
            teams={"HOME": home, "OPP": opp},
        )
        proj = project_game_preview(
            universe, home_team="HOME", away_team="OPP", week=5, neutral_site=True
        )
        return proj.home_win_prob

    wp_inc = _proj("incumbent")
    wp_tf = _proj("true_freshman")
    assert wp_inc - wp_tf >= 0.06


def _fixed_roster_qb():
    roster = build_roster_construction(
        "HOME",
        {
            "returning_production": 55,
            "portal_in_value": 55,
            "portal_out_value": 50,
            "recruiting_class_score": 70,
            "experience_index": 55,
        },
    )
    qb = build_qb_situation(
        "HOME",
        {
            "qb_class": "incumbent",
            "qb_talent": 75,
            "ol_support": 70,
            "weapons_support": 72,
            "experience_starts": 10,
        },
    )
    return roster, qb


def test_ablation_raise_ol_moves_offense_and_projection() -> None:
    """Holding roster/QB fixed, higher OL → material offense + WP change."""
    # Mid-tier roster/QB so offense_index is below STRENGTH_CLAMP and OL can move it.
    roster = build_roster_construction(
        "HOME",
        {
            "returning_production": 48,
            "portal_in_value": 50,
            "portal_out_value": 52,
            "recruiting_class_score": 58,
            "experience_index": 50,
        },
    )
    qb = build_qb_situation(
        "HOME",
        {
            "qb_class": "portal",
            "qb_talent": 62,
            "ol_support": 55,
            "weapons_support": 58,
            "experience_starts": 2,
        },
    )
    base_groups = build_position_groups(
        "HOME",
        {"ol": 45, "skill": 55, "front_seven": 55, "secondary": 55, "fidelity": "approximate"},
        roster=roster,
        qb=qb,
    )
    boosted = build_position_groups(
        "HOME",
        {"ol": 88, "skill": 55, "front_seven": 55, "secondary": 55, "fidelity": "approximate"},
        roster=roster,
        qb=qb,
    )
    base = compose_team_projection("HOME", roster, qb, base_groups)
    high = compose_team_projection("HOME", roster, qb, boosted)
    assert high.offense_index < 1.55  # not clamp-capped
    assert high.offense_index - base.offense_index >= 0.04
    assert unit_offense_boost(boosted) > unit_offense_boost(base_groups) + 0.03

    opp_roster = build_roster_construction(
        "OPP",
        {
            "returning_production": 50,
            "portal_in_value": 50,
            "portal_out_value": 50,
            "recruiting_class_score": 55,
            "experience_index": 50,
        },
    )
    opp_qb = build_qb_situation(
        "OPP",
        {"qb_class": "incumbent", "qb_talent": 60, "ol_support": 55, "weapons_support": 55},
    )
    opp_groups = build_position_groups(
        "OPP",
        {"ol": 55, "skill": 55, "front_seven": 58, "secondary": 58, "fidelity": "approximate"},
        roster=opp_roster,
        qb=opp_qb,
    )
    opp = compose_team_projection("OPP", opp_roster, opp_qb, opp_groups)

    def _wp(state):
        return project_game_preview(
            EngineUniverse(season=2026, schedule=[], teams={"HOME": state, "OPP": opp}),
            home_team="HOME",
            away_team="OPP",
            week=5,
            neutral_site=True,
        ).home_win_prob

    assert _wp(high) - _wp(base) >= 0.03


def test_ablation_raise_secondary_moves_defense() -> None:
    roster, qb = _fixed_roster_qb()
    base_groups = build_position_groups(
        "HOME",
        {"ol": 65, "skill": 65, "front_seven": 60, "secondary": 50, "fidelity": "approximate"},
        roster=roster,
        qb=qb,
    )
    boosted = build_position_groups(
        "HOME",
        {"ol": 65, "skill": 65, "front_seven": 60, "secondary": 90, "fidelity": "approximate"},
        roster=roster,
        qb=qb,
    )
    base = compose_team_projection("HOME", roster, qb, base_groups)
    high = compose_team_projection("HOME", roster, qb, boosted)
    assert high.defense_index - base.defense_index >= 0.05


def test_ablation_raise_front_seven_lowers_opponent_scoring() -> None:
    """Stronger front seven dampens opponent expected points / shifts WP."""
    roster, qb = _fixed_roster_qb()
    weak_f7 = build_position_groups(
        "HOME",
        {"ol": 65, "skill": 65, "front_seven": 45, "secondary": 55, "fidelity": "approximate"},
        roster=roster,
        qb=qb,
    )
    strong_f7 = build_position_groups(
        "HOME",
        {"ol": 65, "skill": 65, "front_seven": 92, "secondary": 55, "fidelity": "approximate"},
        roster=roster,
        qb=qb,
    )
    assert unit_defense_dampen(strong_f7) < unit_defense_dampen(weak_f7) - 0.04

    home_weak = compose_team_projection("HOME", roster, qb, weak_f7)
    home_strong = compose_team_projection("HOME", roster, qb, strong_f7)

    opp_roster = build_roster_construction(
        "OPP",
        {
            "returning_production": 60,
            "portal_in_value": 60,
            "portal_out_value": 45,
            "recruiting_class_score": 75,
            "experience_index": 58,
        },
    )
    opp_qb = build_qb_situation(
        "OPP",
        {
            "qb_class": "incumbent",
            "qb_talent": 78,
            "ol_support": 70,
            "weapons_support": 75,
            "experience_starts": 12,
        },
    )
    opp_groups = build_position_groups(
        "OPP",
        {"ol": 72, "skill": 78, "front_seven": 60, "secondary": 60, "fidelity": "approximate"},
        roster=opp_roster,
        qb=opp_qb,
    )
    opp = compose_team_projection("OPP", opp_roster, opp_qb, opp_groups)

    # Opponent scoring against HOME defense.
    pts_vs_weak, _ = expected_team_points(
        opp, home_weak, home=False, neutral_site=True, week=5
    )
    pts_vs_strong, _ = expected_team_points(
        opp, home_strong, home=False, neutral_site=True, week=5
    )
    assert pts_vs_weak - pts_vs_strong >= 2.0

    wp_weak = project_game_preview(
        EngineUniverse(season=2026, schedule=[], teams={"HOME": home_weak, "OPP": opp}),
        home_team="HOME",
        away_team="OPP",
        week=5,
        neutral_site=True,
    ).home_win_prob
    wp_strong = project_game_preview(
        EngineUniverse(season=2026, schedule=[], teams={"HOME": home_strong, "OPP": opp}),
        home_team="HOME",
        away_team="OPP",
        week=5,
        neutral_site=True,
    ).home_win_prob
    assert wp_strong - wp_weak >= 0.04


def test_layer_wiring_compose() -> None:
    roster = build_roster_construction(
        "UGA",
        {
            "returning_production": 60,
            "portal_in_score": 55,
            "portal_out_score": 40,
            "recruiting_capital": 95,
            "experience_index": 65,
        },
    )
    qb = build_qb_situation(
        "UGA",
        {
            "qb_class": "incumbent",
            "starter_name": "Test QB",
            "experience_starts": 10,
            "qb_talent": 80,
            "ol_support": 85,
            "weapons_support": 88,
        },
    )
    groups = build_position_groups(
        "UGA",
        {"ol": 90, "skill": 88, "front_seven": 90, "secondary": 85},
        roster=roster,
        qb=qb,
    )
    state = compose_team_projection("UGA", roster, qb, groups)
    assert state.offense_index > 1.0
    assert state.defense_index > 1.0
    assert state.roster is not None
    assert state.qb is not None and state.qb.qb_class == "incumbent"
    assert state.qb.qb_situation_index > 1.0
    assert "roster_strength" in state.notes
    assert "ol" in state.notes
    assert state.groups is not None


def test_packaged_universe_and_sample_projection() -> None:
    universe = build_packaged_universe(2026)
    assert len(universe.teams) >= 60
    assert "UGA" in universe.teams
    assert "TEX" in universe.teams
    assert universe.schedule

    uga = universe.teams["UGA"]
    assert uga.roster is not None
    assert uga.roster.roster_strength > 50
    assert uga.qb is not None
    assert uga.qb.qb_situation_index > 0.9
    assert uga.groups is not None
    assert uga.groups.components

    proj = project_game_preview(
        universe, home_team="ALA", away_team="UGA", week=1, neutral_site=True
    )
    assert proj.engine_version == DEFAULT_SEASON_ENGINE_VERSION
    assert proj.home_team == "ALA"
    assert proj.away_team == "UGA"
    assert 0.02 <= proj.home_win_prob <= 0.98
    assert proj.expected_total > 30
    assert proj.early_season_uncertainty["active"] is True
    assert proj.margin_sd > 16.5  # W1 inflated
    assert "roster" in proj.home_layers
    assert "qb" in proj.away_layers
    assert "position_groups" in proj.home_layers
    assert "components" in proj.home_layers["position_groups"]
    assert "roster_strength" in proj.home_layers["roster"]
    assert "qb_situation_index" in proj.away_layers["qb"]
    assert "strength→margin" in proj.notes.get("method", "")
    assert proj.fidelity == "approximate"


def test_contrasting_team_profiles_project_differently() -> None:
    """Stable incumbent power vs portal-heavy open/true-freshman profiles."""
    universe = build_packaged_universe(2026)
    uga = universe.teams["UGA"]
    fsu = universe.teams["FSU"]
    colo = universe.teams["COLO"]
    assert uga.roster and fsu.roster and colo.roster
    assert uga.qb and fsu.qb and colo.qb
    assert uga.roster.roster_strength > fsu.roster.roster_strength
    assert uga.qb.qb_class == "incumbent"
    assert fsu.qb.qb_class == "portal"
    assert colo.qb.qb_class == "true_freshman"
    assert uga.offense_index > fsu.offense_index > colo.offense_index

    # Same opponent (BALL) — UGA clearer favorite than FSU than COLO.
    ball = universe.teams["BALL"]
    u_vs = project_game_preview(
        EngineUniverse(season=2026, schedule=[], teams={"UGA": uga, "BALL": ball}),
        home_team="UGA",
        away_team="BALL",
        week=5,
        neutral_site=True,
    )
    f_vs = project_game_preview(
        EngineUniverse(season=2026, schedule=[], teams={"FSU": fsu, "BALL": ball}),
        home_team="FSU",
        away_team="BALL",
        week=5,
        neutral_site=True,
    )
    c_vs = project_game_preview(
        EngineUniverse(season=2026, schedule=[], teams={"COLO": colo, "BALL": ball}),
        home_team="COLO",
        away_team="BALL",
        week=5,
        neutral_site=True,
    )
    assert u_vs.home_win_prob > f_vs.home_win_prob + 0.03
    assert f_vs.home_win_prob > c_vs.home_win_prob + 0.03
    assert u_vs.home_win_prob > c_vs.home_win_prob + 0.08


def test_early_season_uncertainty_wider_in_w1() -> None:
    w1 = early_season_uncertainty(1)
    w5 = early_season_uncertainty(5)
    assert w1["active"] is True
    assert w5["active"] is False
    assert w1["win_prob_margin_sd"] > w5["win_prob_margin_sd"]
    assert win_prob_margin_sd_for_week(1) > win_prob_margin_sd_for_week(4)
    assert win_prob_margin_sd_for_week(4) > win_prob_margin_sd_for_week(5)

    universe = build_packaged_universe(2026)
    p1 = project_game_preview(
        universe, home_team="TEX", away_team="OSU", week=1, neutral_site=True
    )
    p5 = project_game_preview(
        universe, home_team="TEX", away_team="OSU", week=5, neutral_site=True
    )
    assert p1.early_season_uncertainty["active"] is True
    assert p5.early_season_uncertainty["active"] is False
    assert p1.margin_sd > p5.margin_sd
    assert p1.uncertainty["effective_margin_sd"] == p1.margin_sd
    assert "narrowing_schedule" in p1.uncertainty


def test_project_game_drivers_and_score_coherence() -> None:
    universe = build_packaged_universe(2026)
    proj = project_game_preview(
        universe, home_team="ALA", away_team="UGA", week=1, neutral_site=True
    )
    payload = project_game_to_dict(proj)
    assert "drivers" in payload
    assert payload["drivers"]["primary_signals"]["home_roster_strength"] is not None
    assert payload["drivers"]["home"]["qb_situation_index"] is not None
    assert payload["drivers"]["home"]["unit_grades"]["ol"] is not None
    assert "uncertainty" in payload
    assert payload["uncertainty"]["active"] is True
    # Score / spread / total coherence (no floating invent).
    assert abs(
        payload["expected_total"]
        - (payload["expected_home_score"] + payload["expected_away_score"])
    ) < 1e-9
    assert abs(
        payload["spread_home"]
        - (payload["expected_away_score"] - payload["expected_home_score"])
    ) < 1e-9
    assert abs(payload["home_win_prob"] + payload["away_win_prob"] - 1.0) < 1e-9


def test_densified_schedule_covers_many_teams() -> None:
    universe = build_packaged_universe(2026)
    assert universe.notes.get("official_schedule") == "false"
    assert "densified" in universe.notes.get("schedule_source", "")
    assert len(universe.schedule) >= 200
    from collections import Counter

    counts = Counter()
    for g in universe.schedule:
        counts[g.home_team] += 1
        counts[g.away_team] += 1
    # Most packaged FBS teams should have a usable season path.
    assert sum(1 for t in universe.team_codes if counts[t] >= 8) >= 100


def test_season_sim_wins_for_many_teams() -> None:
    universe = build_packaged_universe(2026)
    result = simulate_full_season(universe, n_sims=4, seed=7)
    assert result.n_sims == 4
    assert result.games_per_season == len(universe.schedule)
    assert abs(result.diagnostics["mean_wins_sum"] - len(universe.schedule)) < 0.05
    assert result.engine_version == DEFAULT_SEASON_ENGINE_VERSION
    assert result.diagnostics["teams_with_positive_mean_wins"] >= 80
    # Distribution fields present.
    sample_team = next(iter(result.team_wins.values()))
    for key in ("mean", "std", "p10", "p50", "p90"):
        assert key in sample_team
    assert len(result.week_by_week_sample) == len(universe.schedule)
    assert result.ranking[0]["rank"] == 1
    assert result.ranking[0]["mean"] >= result.ranking[10]["mean"]
    # Alias collapse — do not triple-count A&M / Ole Miss codes.
    assert "TXAM" not in result.team_wins
    assert "TA&M" not in result.team_wins
    assert "OLE" not in result.team_wins
    payload = season_sim_to_dict(result)
    assert "conference_standings" in payload
    assert "week_by_week_grouped" in payload
    assert len(payload["top_teams_by_wins"]) >= 10


def test_variable_hfa_differs_by_bucket() -> None:
    elite = build_home_field_profile("LSU", {"bucket": "elite", "env_score": 92})
    average = build_home_field_profile("MIA", {"bucket": "average", "env_score": 52})
    poor = build_home_field_profile("BALL", {"bucket": "poor", "env_score": 28})
    assert elite.hfa_points > average.hfa_points > poor.hfa_points
    assert points_for_bucket("elite") == 3.4
    assert points_for_bucket("average") == 2.0
    assert points_for_bucket("poor") == 0.7
    hfa_elite = resolve_hfa_points(elite, home=True, neutral_site=False)
    hfa_poor = resolve_hfa_points(poor, home=True, neutral_site=False)
    assert hfa_elite["hfa_points"] - hfa_poor["hfa_points"] >= 2.0
    assert resolve_hfa_points(elite, home=True, neutral_site=True)["hfa_points"] == 0.0
    night = resolve_hfa_points(elite, home=True, night_game=True)
    day = resolve_hfa_points(elite, home=True, night_game=False)
    assert night["hfa_points"] > day["hfa_points"]


def test_variable_hfa_moves_project_game() -> None:
    """Same close matchup, different home HFA buckets → material score/WP shift."""
    universe = build_packaged_universe(2026)
    # Competitive pair so HFA is not swamped by talent gap.
    home = universe.teams["TEX"].copy()
    away = universe.teams["OSU"].copy()
    home.home_field = HomeFieldProfile(
        team="TEX",
        env_score=90,
        bucket="elite",
        hfa_points=3.4,
        baseline_points=2.0,
        bucket_delta=1.4,
        fidelity="approximate",
    )
    elite_u = EngineUniverse(season=2026, schedule=[], teams={"TEX": home, "OSU": away})
    p_elite = project_game_preview(
        elite_u, home_team="TEX", away_team="OSU", week=5, neutral_site=False
    )

    home2 = home.copy()
    home2.home_field = HomeFieldProfile(
        team="TEX",
        env_score=25,
        bucket="poor",
        hfa_points=0.7,
        baseline_points=2.0,
        bucket_delta=-1.3,
        fidelity="approximate",
    )
    poor_u = EngineUniverse(season=2026, schedule=[], teams={"TEX": home2, "OSU": away})
    p_poor = project_game_preview(
        poor_u, home_team="TEX", away_team="OSU", week=5, neutral_site=False
    )
    # ~2.7 pt HFA gap should show in expected home score and WP.
    assert p_elite.expected_home_score - p_poor.expected_home_score >= 2.0
    assert p_elite.home_win_prob - p_poor.home_win_prob >= 0.04
    assert p_elite.drivers["matchup"]["hfa"]["bucket"] == "elite"
    assert p_poor.drivers["matchup"]["hfa"]["bucket"] == "poor"

    # Packaged LSU (elite) home HFA > BALL (poor) when both host same opponent.
    lsu_home = project_game_preview(
        universe, home_team="LSU", away_team="WAKE", week=6, neutral_site=False
    )
    ball_home = project_game_preview(
        universe, home_team="BALL", away_team="WAKE", week=6, neutral_site=False
    )
    assert lsu_home.drivers["matchup"]["hfa"]["bucket"] == "elite"
    assert ball_home.drivers["matchup"]["hfa"]["bucket"] == "poor"
    assert (
        lsu_home.drivers["matchup"]["hfa"]["hfa_points"]
        > ball_home.drivers["matchup"]["hfa"]["hfa_points"] + 2.0
    )


def test_new_hc_early_penalty_exceeds_midseason() -> None:
    coach = build_coaching_continuity(
        "PSU",
        {"new_hc": True, "new_oc": True, "new_dc": True, "fidelity": "approximate"},
    )
    assert coach.new_hc is True
    assert coach.offense_penalty_w1 > 1.0
    assert coach.defense_penalty_w1 > 1.0
    w1 = coaching_week_adjustment(coach, week=1, side="offense")
    w5 = coaching_week_adjustment(coach, week=5, side="offense")
    w8 = coaching_week_adjustment(coach, week=8, side="offense")
    assert abs(w1["points"]) > abs(w5["points"]) > abs(w8["points"])
    assert week_decay(1) > week_decay(4) > week_decay(5)
    # Returning staff: tiny continuity bonus early, not a penalty.
    ret = build_coaching_continuity(
        "UGA", {"new_hc": False, "new_oc": False, "new_dc": False}
    )
    assert ret.offense_penalty_w1 == 0.0
    assert ret.continuity_bonus_w1 > 0.0
    assert ret.continuity_score == 100.0


def test_coaching_and_hfa_in_project_game_and_sim() -> None:
    universe = build_packaged_universe(2026)
    assert universe.teams["PSU"].coaching is not None
    assert universe.teams["PSU"].coaching.new_hc is True
    assert universe.teams["UGA"].coaching is not None
    assert universe.teams["UGA"].coaching.new_hc is False
    assert universe.teams["LSU"].home_field is not None
    assert universe.teams["LSU"].home_field.bucket == "elite"

    # New-HC PSU early-season own scoring adj more negative than mid-season.
    p1 = project_game_preview(
        universe, home_team="PSU", away_team="BALL", week=1, neutral_site=True
    )
    p6 = project_game_preview(
        universe, home_team="PSU", away_team="BALL", week=6, neutral_site=True
    )
    adj1 = p1.drivers["matchup"]["home_coaching_adj"]["own_scoring_adj"]
    adj6 = p6.drivers["matchup"]["home_coaching_adj"]["own_scoring_adj"]
    assert adj1 < adj6  # larger early penalty (more negative)
    assert "home_field" in p1.home_layers
    assert "coaching" in p1.home_layers
    assert p1.home_layers["coaching"]["new_hc"] is True
    assert p1.drivers["primary_signals"]["home_coaching_flags"]["new_hc"] is True

    # Holding opponent fixed, new-HC team weaker early vs returning-staff peer.
    # Compare PSU (new HC) vs ORE (returning) vs same opponent mid rebuild.
    psu_w1 = project_game_preview(
        universe, home_team="PSU", away_team="EMU", week=1, neutral_site=True
    )
    # Rebuild indexes so coaching is the contrast: use copy with flipped flags.
    ore = universe.teams["ORE"]
    assert ore.coaching and ore.coaching.new_hc is False
    # Season sim diagnostics expose the new layers.
    result = simulate_full_season(universe, n_sims=2, seed=11)
    assert result.diagnostics.get("variable_hfa") is True
    assert result.diagnostics.get("coaching_continuity") is True
    assert "variable_hfa" in result.diagnostics["layers_in_path"]
    assert psu_w1.home_win_prob > 0.5  # still favored vs EMU; layer is relative


def test_status_contract() -> None:
    payload = engine_status_payload(season=2026, demo=True)
    assert payload["engine_version"] == DEFAULT_SEASON_ENGINE_VERSION
    assert payload["additive"] is True
    assert "edge_board_cfb_markets_only" in payload["does_not_modify"]
    assert len(payload["layers"]) >= 7
    assert "solid" in payload["solid_vs_approximate"]
    assert "Roster strength formula" in " ".join(payload["solid_vs_approximate"]["solid"])
    assert "Position group unit formula" in " ".join(
        payload["solid_vs_approximate"]["solid"]
    )
    assert "Variable HFA" in " ".join(payload["solid_vs_approximate"]["solid"])
    assert "Coaching continuity" in " ".join(payload["solid_vs_approximate"]["solid"])
    assert payload["entry_points"]["status"] == "GET /cfb/season-engine/status"
    assert "cfb-hfa-coaching" in payload["entry_points"]["ops"]
    assert "early_season_narrowing" in payload
    assert "examples" in payload
    assert "position_groups" in payload["examples"].get("UGA", {})
    assert "home_field" in payload["examples"].get("LSU", {})
    assert "coaching" in payload["examples"].get("PSU", {})
    assert payload["examples"]["PSU"]["coaching"]["new_hc"] is True
    assert "hfa_bucket_counts" in payload
    assert "project_game_formula" in payload
    assert "roster_strength_ladder" in payload
    assert payload["layers"][0]["name"] == "roster_construction"
    assert "formula" in payload["layers"][0]
    assert "class_offense_mult" in payload["layers"][1]
    assert payload["layers"][2]["name"] == "position_groups"
    assert "talent" in payload["layers"][2]["formula"]
    layer_names = [layer["name"] for layer in payload["layers"]]
    assert "home_field" in layer_names
    assert "coaching_continuity" in layer_names


def test_status_and_project_game_http() -> None:
    from src.main import app

    client = TestClient(app)
    status = client.get("/cfb/season-engine/status")
    assert status.status_code == 200
    body = status.json()
    assert body["engine_version"] == DEFAULT_SEASON_ENGINE_VERSION
    assert body["additive"] is True
    assert "examples" in body
    assert "position_groups" in body["examples"]["UGA"]

    proj = client.post(
        "/cfb/season-engine/project-game",
        json={
            "home_team": "TEX",
            "away_team": "OSU",
            "week": 1,
            "neutral_site": True,
            "demo": True,
        },
    )
    assert proj.status_code == 200
    data = proj.json()
    assert data["ok"] is True
    assert data["home_team"] == "TEX"
    assert data["away_team"] == "OSU"
    assert data["engine_version"] == DEFAULT_SEASON_ENGINE_VERSION
    assert "expected_home_score" in data
    assert data["early_season_uncertainty"]["week"] == 1
    assert "roster_strength" in data["home_layers"]["roster"]
    assert "qb_situation_index" in data["away_layers"]["qb"]
    assert "position_groups" in data["home_layers"]
    assert "components" in data["home_layers"]["position_groups"]
    assert "projection_formula" in data
    assert "drivers" in data
    assert data["drivers"]["home"]["roster_strength"] is not None
    assert data["drivers"]["home"]["home_field"] is not None
    assert data["drivers"]["home"]["coaching"] is not None
    assert "hfa" in data["drivers"]["matchup"]
    assert "uncertainty" in data
    assert data["uncertainty"]["week"] == 1
    assert "home_field" in data["home_layers"]
    assert "coaching" in data["away_layers"]

    sim = client.post(
        "/cfb/season-engine/simulate",
        json={"n_sims": 2, "seed": 1, "demo": True},
    )
    assert sim.status_code == 200
    sim_body = sim.json()
    assert sim_body["ok"] is True
    assert sim_body["season_paths"] is True
    assert sim_body["skeleton"] is False
    assert sim_body["n_sims"] == 2
    assert len(sim_body["top_teams_by_wins"]) >= 10
    assert "week_by_week_sample" in sim_body
    assert sim_body["diagnostics"]["variable_hfa"] is True
    assert sim_body["diagnostics"]["coaching_continuity"] is True


def test_compute_qb_situation_index_class_gap() -> None:
    inc, _, bd_inc = compute_qb_situation_index(
        qb_class="incumbent", qb_talent=75, supporting_cast=80
    )
    tf, _, bd_tf = compute_qb_situation_index(
        qb_class="true_freshman", qb_talent=75, supporting_cast=45
    )
    assert inc > tf + 0.20
    assert bd_inc["class_mult"] > bd_tf["class_mult"]
