"""Season-ready closeout smell tests — SOS on outlook + in-season blend guards."""

from __future__ import annotations

import pytest

from src.services.nfl_season_engine.efficiency_backbone import (
    EARLY_SEASON_PRIOR_HEAVY_GAMES,
    TeamEfficiencyPackage,
    UnitEfficiency,
    assert_no_early_season_blend_cliff,
    blend_packages,
    early_season_prior_heavy,
    prior_current_blend_weight,
)
from src.services.nfl_season_engine.injury_paths import apply_strength_shock
from src.services.nfl_season_engine.loaders import build_packaged_real_universe
from src.services.nfl_season_engine.projected_sos import (
    analytic_expected_wins_from_schedule,
    assert_strengths_unchanged,
    compute_league_projected_sos,
    compute_team_projected_sos,
)
from src.services.nfl_season_engine.survivor import evaluate_survivor
from src.services.nfl_season_engine.true_pr_product import serialize_true_pr_product_surface
from src.services.nfl_season_engine.types import (
    EngineUniverse,
    PlayerRole,
    ScheduledGame,
    TeamStrengthState,
)


def _equal_pr(team: str) -> TeamStrengthState:
    return TeamStrengthState(
        team=team,
        offense_index=1.05,
        defense_index=1.05,
        full_strength_offense_index=1.05,
        full_strength_defense_index=1.05,
        source="test_equal_pr",
        games_played=0,
        drivers={"blend": {"w_prior": 1.0, "w_current": 0.0}},
    )


def _elite(team: str) -> TeamStrengthState:
    return TeamStrengthState(
        team=team,
        offense_index=1.18,
        defense_index=1.14,
        full_strength_offense_index=1.18,
        full_strength_defense_index=1.14,
        source="test_elite",
        games_played=0,
    )


def _weak(team: str) -> TeamStrengthState:
    return TeamStrengthState(
        team=team,
        offense_index=0.88,
        defense_index=0.90,
        full_strength_offense_index=0.88,
        full_strength_defense_index=0.90,
        source="test_weak",
        games_played=0,
    )


def _avg(team: str) -> TeamStrengthState:
    return TeamStrengthState(
        team=team,
        offense_index=1.0,
        defense_index=1.0,
        full_strength_offense_index=1.0,
        full_strength_defense_index=1.0,
        source="test_avg",
        games_played=0,
    )


def _soft_vs_hard_universe() -> EngineUniverse:
    """Equal-PR SOFT vs HARD with opposite slate difficulty (outlook only)."""
    soft_opps = [f"E{i}" for i in range(1, 10)] + [f"SM{i}" for i in range(1, 9)]
    hard_opps = [f"H{i}" for i in range(1, 10)] + [f"HM{i}" for i in range(1, 9)]
    strengths: dict[str, TeamStrengthState] = {
        "SOFT": _equal_pr("SOFT"),
        "HARD": _equal_pr("HARD"),
    }
    for t in soft_opps[:9]:
        strengths[t] = _weak(t)
    for t in soft_opps[9:]:
        strengths[t] = _avg(t)
    for t in hard_opps[:9]:
        strengths[t] = _elite(t)
    for t in hard_opps[9:]:
        strengths[t] = _avg(t)

    schedule: list[ScheduledGame] = []
    for week, (s_opp, h_opp) in enumerate(zip(soft_opps, hard_opps), start=1):
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


def test_soft_sos_better_outlook_than_equal_pr_hard_sos() -> None:
    """Smell 1: soft slate → higher analytic E[wins] / easier path grade."""
    uni = _soft_vs_hard_universe()
    before = {t: s.copy() for t, s in uni.strengths.items()}
    soft_sos = compute_team_projected_sos("SOFT", uni.schedule, uni.strengths)
    hard_sos = compute_team_projected_sos("HARD", uni.schedule, uni.strengths)
    soft_e = analytic_expected_wins_from_schedule(
        "SOFT", uni.schedule, uni.strengths
    )
    hard_e = analytic_expected_wins_from_schedule(
        "HARD", uni.schedule, uni.strengths
    )
    assert soft_e > hard_e + 0.5
    assert soft_sos.projected_sos_2026 < hard_sos.projected_sos_2026
    assert soft_sos.difficulty_band in ("easy", "average")
    assert hard_sos.difficulty_band in ("hard", "average")
    assert_strengths_unchanged(before, uni.strengths)

    result = evaluate_survivor(uni, week=1, n_sims=40, seed=7, top_n=32)
    by_team = {r["team"]: r for r in result.all_teams_week}
    assert "schedule_difficulty" in by_team["SOFT"]
    assert "path_difficulty_grade" in by_team["SOFT"]
    assert float(by_team["SOFT"]["projected_sos_2026"]) < float(
        by_team["HARD"]["projected_sos_2026"]
    )
    assert "Harder schedule" in result.notes.get("projected_sos_2026", "")
    assert "intrinsic PR" in result.notes.get("schedule_difficulty", "").lower() or (
        "does not rewrite" in result.formula.get("projected_sos_2026", "").lower()
    )


def test_intrinsic_pr_unchanged_by_sos_wiring() -> None:
    """Smell 2: equal intrinsic PR before/after SOS annotate."""
    uni = _soft_vs_hard_universe()
    soft_pr = 0.5 * (
        uni.strengths["SOFT"].full_strength_offense_index
        + uni.strengths["SOFT"].full_strength_defense_index
    )
    hard_pr = 0.5 * (
        uni.strengths["HARD"].full_strength_offense_index
        + uni.strengths["HARD"].full_strength_defense_index
    )
    assert abs(soft_pr - hard_pr) < 1e-9
    compute_league_projected_sos(uni)
    soft_pr2 = 0.5 * (
        uni.strengths["SOFT"].full_strength_offense_index
        + uni.strengths["SOFT"].full_strength_defense_index
    )
    hard_pr2 = 0.5 * (
        uni.strengths["HARD"].full_strength_offense_index
        + uni.strengths["HARD"].full_strength_defense_index
    )
    assert abs(soft_pr2 - soft_pr) < 1e-12
    assert abs(hard_pr2 - hard_pr) < 1e-12


def test_after_one_game_no_prior_cliff() -> None:
    """Smell 3: after 1 REG game, prior stays ~7/8 — not near-zero."""
    assert EARLY_SEASON_PRIOR_HEAVY_GAMES == 2
    assert early_season_prior_heavy(current_games=0)
    assert early_season_prior_heavy(current_games=1)
    assert early_season_prior_heavy(current_games=2)
    assert not early_season_prior_heavy(current_games=3)

    w1 = prior_current_blend_weight(current_games=1)
    assert abs(w1 - 0.125) < 1e-9
    assert_no_early_season_blend_cliff(current_games=1, w_current=w1)

    prior = TeamEfficiencyPackage(
        team="SEA",
        offense=UnitEfficiency(epa_per_play=0.04, success_rate=0.45, plays=1000),
        defense=UnitEfficiency(epa_per_play=-0.05, success_rate=0.42, plays=1000),
        games_played=17,
        source="prior",
    )
    current = TeamEfficiencyPackage(
        team="SEA",
        offense=UnitEfficiency(epa_per_play=0.55, success_rate=0.55, plays=60),
        defense=UnitEfficiency(epa_per_play=-0.50, success_rate=0.35, plays=60),
        games_played=1,
        source="current",
    )
    blended = blend_packages(prior, current, current_games=1)
    assert abs(float(blended.notes["blend_current_weight"]) - 0.125) < 1e-9
    assert abs(float(blended.notes["blend_prior_weight"]) - 0.875) < 1e-9

    with pytest.raises(AssertionError, match="cliff|mismatch"):
        assert_no_early_season_blend_cliff(current_games=1, w_current=0.95)


def test_injury_shock_uses_current_path_not_full_strength() -> None:
    """Confirm live boards' current indices move when starter/injury scar hits."""
    state = TeamStrengthState(
        team="PHI",
        offense_index=1.12,
        defense_index=1.06,
        full_strength_offense_index=1.12,
        full_strength_defense_index=1.06,
        source="efficiency_backbone_blend",
    )
    shocked = apply_strength_shock(state, offense_delta=-0.09)
    assert shocked.offense_index < state.offense_index
    assert shocked.full_strength_offense_index == pytest.approx(1.12)
    assert shocked.offense_index == pytest.approx(1.03)
    assert shocked.injury_delta_offense < 0


def test_true_pr_surface_preseason_blend_and_drivers() -> None:
    """Smell 4–5: no fake in-season sample; continuity + QB chips still shaped."""
    uni = build_packaged_real_universe(season=2026)
    payload = serialize_true_pr_product_surface(
        uni,
        season=2026,
        as_of_week=1,
        mode="real",
        engine_version="closeout-test",
        enrich_display_drivers=True,
    )
    assert payload["teams"]
    for row in payload["teams"][:8]:
        blend = row["drivers"]["blend"]
        assert blend["preseason"] is True
        assert blend["early_season"] is True
        assert blend["w_current"] == 0.0
        assert blend["state"] == "prior_heavy"
        assert "continuity" in row["drivers"]
        assert "qb_premium" in row["drivers"]
        proj = row["drivers"]["projected_sos_2026"]
        if proj.get("available"):
            assert proj.get("intrinsic_pr_unchanged") is True
