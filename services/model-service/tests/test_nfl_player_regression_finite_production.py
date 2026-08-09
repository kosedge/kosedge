"""Smell tests — player process regression + finite production (v1.13)."""

from __future__ import annotations

import random

from src.services.nfl_season_engine import (
    DEFAULT_SEASON_ENGINE_VERSION,
    InjuryPath,
    apply_process_priors,
    build_demo_universe,
    build_packaged_real_universe,
    build_player_process_prior,
    enforce_finite_team_production,
    project_game_player_boxes,
    simulate_full_season,
)
from src.services.nfl_season_engine.calibration import apply_efficiency_priors
from src.services.nfl_season_engine.game_script import build_game_script
from src.services.nfl_season_engine.injury_paths import apply_injury_paths_for_week
from src.services.nfl_season_engine.player_regression import (
    ROOKIE_EXPERIENCE_CONFIDENCE,
    efficiency_cv_mult,
    named_sums_within_caps,
)
from src.services.nfl_season_engine.player_usage import allocate_game_usage
from src.services.nfl_season_engine.production import produce_box_scores
from src.services.nfl_season_engine.types import PlayerBoxScore, PlayerRole, ScheduledGame
from src.services.nfl_season_engine.loaders import STRENGTH_SOURCE_DEMO


def test_engine_version_player_regression() -> None:
    assert DEFAULT_SEASON_ENGINE_VERSION.startswith("nfl-season-engine-v1.")
    # v1.15+ keeps player-regression; tag may be true-pr-harden / projected-sos.
    assert any(
        token in DEFAULT_SEASON_ENGINE_VERSION
        for token in (
            "player-regression",
            "projected-sos",
            "true-pr-harden",
            "season-coherence",
        )
    )
    assert any(
        v in DEFAULT_SEASON_ENGINE_VERSION
        for v in ("v1.25", "v1.24", "v1.23", "v1.22", "v1.21", "v1.20", "v1.19", "v1.18", "v1.17", "v1.16", "v1.15", "v1.14", "v1.13")
    )


def test_negative_regression_high_td_thin_process() -> None:
    """Smell 2: high TD rate / league-ish efficiency → negative when evidence ok."""
    role = PlayerRole(
        player_key="KC-WR1-Over",
        player_name="Over Finisher",
        team="KC",
        position="WR",
        depth_order=1,
        target_share=0.22,
        snap_share=0.85,
        role_confidence=0.80,
        ypr=11.6,
        catch_rate=0.60,
        rec_td_rate=0.11,  # well above league ~0.055
        source="unit+baseline_efficiency",
    )
    prior = build_player_process_prior(role)
    assert prior.td_process_gap > 0.12
    assert prior.regression_posture == "negative"
    assert prior.regression_confidence >= 0.35
    assert any("td_rate_above" in d or "finish_rate" in d for d in prior.regression_drivers)

    adjusted = apply_process_priors(role)
    assert adjusted.rec_td_rate < role.rec_td_rate
    assert adjusted.regression_posture == "negative"


def test_positive_regression_strong_process_soft_finish() -> None:
    """Smell 3: strong process / soft TD finish → positive candidate."""
    role = PlayerRole(
        player_key="BUF-WR1-Under",
        player_name="Process Guy",
        team="BUF",
        position="WR",
        depth_order=1,
        target_share=0.24,
        snap_share=0.88,
        role_confidence=0.82,
        ypr=14.2,
        catch_rate=0.68,
        rec_td_rate=0.035,  # soft finish vs process
        source="unit+baseline_efficiency",
    )
    prior = build_player_process_prior(role)
    assert prior.td_process_gap < -0.12
    assert prior.regression_posture == "positive"
    adjusted = apply_process_priors(role)
    assert adjusted.rec_td_rate > role.rec_td_rate * 0.98  # mild lift or hold


def test_thin_evidence_stays_neutral() -> None:
    role = PlayerRole(
        player_key="X-WR3-Thin",
        player_name="Thin Sample",
        team="ARI",
        position="WR",
        depth_order=3,
        target_share=0.04,
        role_confidence=0.25,
        ypr=12.0,
        rec_td_rate=0.09,
        source="unit",  # no baseline
    )
    prior = build_player_process_prior(role)
    assert prior.regression_posture == "neutral"
    assert any("thin" in d for d in prior.regression_drivers)


def test_rookie_conservative_mean_wide_uncertainty() -> None:
    """Smell 4: rookies do not dominate veterans on draft hype alone."""
    vet = apply_efficiency_priors(
        PlayerRole(
            player_key="MIN-WR1-Vet",
            player_name="Vet WR",
            team="MIN",
            position="WR",
            depth_order=1,
            target_share=0.22,
            snap_share=0.85,
            role_confidence=0.8,
            is_rookie=False,
            source="unit",
        ),
        overrides={"ypr": 13.5, "rec_td_rate": 0.06},
    )
    rook = apply_efficiency_priors(
        PlayerRole(
            player_key="MIN-WR2-Rook",
            player_name="Rook WR",
            team="MIN",
            position="WR",
            depth_order=2,
            target_share=0.14,
            snap_share=0.65,
            role_confidence=0.55,
            is_rookie=True,
            draft_round=1,
            source="unit",
        ),
        overrides={"ypr": 16.0, "rec_td_rate": 0.09},  # hyped counting rates
    )
    vet_a = apply_process_priors(vet)
    rook_a = apply_process_priors(rook)
    assert rook_a.is_rookie
    assert rook_a.experience_confidence <= ROOKIE_EXPERIENCE_CONFIDENCE
    assert efficiency_cv_mult(rook_a) > efficiency_cv_mult(vet_a)
    # Rookie mean pulled toward league — should not keep full hype ypr.
    assert rook_a.ypr < 14.0
    assert rook_a.ypr < 16.0 * 0.9
    # Depth-2 rookie with hype rates stays near vet WR1 process — not above it.
    assert rook_a.ypr <= vet_a.ypr + 0.4


def test_finite_production_caps_teammate_overflow() -> None:
    """Smell 1: three teammates cannot all regress past the team pool."""
    universe = build_demo_universe(2026)
    game = ScheduledGame(
        season=2026, week=3, game_id="t-finite", home_team="DET", away_team="GB"
    )
    script, _ = build_game_script(game, universe.strengths, rng=random.Random(1), realized=False)
    # Invent absurd overflow boxes.
    absurd = [
        PlayerBoxScore(
            player_key="a", player_name="A", team="DET", position="RB",
            rush_yards=180, rush_tds=3,
        ),
        PlayerBoxScore(
            player_key="b", player_name="B", team="DET", position="RB",
            rush_yards=160, rush_tds=2,
        ),
        PlayerBoxScore(
            player_key="c", player_name="C", team="DET", position="WR",
            rec_yards=220, rec_tds=3,
        ),
        PlayerBoxScore(
            player_key="qb", player_name="Q", team="DET", position="QB",
            pass_yards=520, pass_tds=6,
        ),
    ]
    oi = {"DET": universe.strengths["DET"].offense_index}
    assert not named_sums_within_caps(absurd, script, strengths_offense=oi)
    capped, diag = enforce_finite_team_production(
        absurd,
        script=script,
        strengths_offense=oi,
    )
    assert named_sums_within_caps(capped, script, strengths_offense=oi, tol=1.02)
    assert diag["teams"]["DET"]["scales_applied"]


def test_injury_lifts_handcuff_inside_team_pool() -> None:
    """Smell 5: lead-back injury lifts handcuff; shares stay team-finite."""
    universe = build_demo_universe(2026)
    gibbs = next(r for r in universe.rosters["DET"] if "Gibbs" in r.player_name)
    mont = next(r for r in universe.rosters["DET"] if "Montgomery" in r.player_name)
    path = InjuryPath(
        player_key=gibbs.player_key,
        team="DET",
        status="out",
        week_start=1,
        week_end=1,
    )
    adj, _, _ = apply_injury_paths_for_week(
        universe.rosters, universe.strengths, [path], week=1
    )
    mont_adj = next(r for r in adj["DET"] if r.player_key == mont.player_key)
    assert mont_adj.rush_share > mont.rush_share
    # Team rush shares among healthy RBs should not explode past ~1.0 named.
    rb_rush = sum(
        r.rush_share for r in adj["DET"] if r.position == "RB" and r.rush_share > 0
    )
    assert rb_rush <= 1.05


def test_produce_boxes_respects_finite_and_regression_fields() -> None:
    universe = build_demo_universe(2026)
    game = next(g for g in universe.schedule if g.home_team == "DET")
    rng = random.Random(42)
    script, _ = build_game_script(game, universe.strengths, rng=rng, realized=True)
    usage = allocate_game_usage(script, universe.rosters, rng=rng)
    boxes = produce_box_scores(
        usage_rows=usage,
        roles=universe.rosters,
        script=script,
        strengths=universe.strengths,
        rng=rng,
        enforce_finite=True,
    )
    assert boxes
    oi = {t: universe.strengths[t].offense_index for t in (script.home_team, script.away_team)}
    assert named_sums_within_caps(boxes, script, strengths_offense=oi, tol=1.05)
    # Rosters carry regression annotation from loader.
    sample = universe.rosters["DET"][0]
    assert sample.regression_posture in ("positive", "negative", "neutral")
    assert "process_regression_v1" in sample.source


def test_season_and_gamebox_expose_regression_bands() -> None:
    universe = build_demo_universe(2026)
    result = simulate_full_season(universe, n_sims=4, seed=9, include_diagnostics=True)
    assert result.engine_version == DEFAULT_SEASON_ENGINE_VERSION
    assert result.player_season_totals
    row = result.player_season_totals[0]
    assert "regression_posture" in row
    assert "rush_yards_p10" in row or "pass_yards_p10" in row or "rec_yards_p10" in row
    assert "player_regression" in result.diagnostics

    boxes = project_game_player_boxes(
        universe,
        home_team="DET",
        away_team="GB",
        week=1,
        n_replicates=60,
        seed=3,
    )
    assert boxes.players
    assert "regression_posture" in boxes.players[0]
    assert "distributions" in boxes.players[0]


def test_packaged_real_no_demo_strength_and_has_process() -> None:
    """Smell 6/7: packaged path stays demo-free on strength; stubs labeled."""
    universe = build_packaged_real_universe(2026)
    assert universe.notes.get("mode") == "real"
    for st in universe.strengths.values():
        assert STRENGTH_SOURCE_DEMO not in (st.source or "")
    # Process layer applied on skill roles.
    any_process = any(
        "process_regression_v1" in (r.source or "")
        for roles in universe.rosters.values()
        for r in roles
    )
    assert any_process


def test_true_pr_blend_fields_intact_on_demo_strengths() -> None:
    """Do not regress true-PR full-strength / current split structure."""
    universe = build_demo_universe(2026)
    st = universe.strengths["SEA"]
    assert hasattr(st, "full_strength_offense_index")
    assert hasattr(st, "blend_prior_weight")
    # At load, current == full-strength until injury shocks.
    assert st.offense_index == st.full_strength_offense_index
