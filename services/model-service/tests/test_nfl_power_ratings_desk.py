"""Unit tests — NFL Power Ratings desk Method B + early-season shrinkage."""

from __future__ import annotations

import pytest

from src.services.nfl_season_engine.power_ratings_desk import (
    ALPHA_BY_WEEK,
    METHOD_ID,
    adjusted_alpha,
    alpha_for_week,
    apply_shrinkage,
    build_desk_rows,
    derive_raw_model_prs,
    expected_margin_vs_average,
    product_team_id,
    serialize_power_ratings_desk,
    shrink_model_prs,
    zero_center,
)
from src.services.nfl_season_engine.types import EngineUniverse, TeamStrengthState


def _strength(
    team: str,
    off: float,
    deff: float,
    *,
    st: float = 1.0,
    active_off: float | None = None,
    active_def: float | None = None,
) -> TeamStrengthState:
    ao = off if active_off is None else active_off
    ad = deff if active_def is None else active_def
    return TeamStrengthState(
        team=team,
        offense_index=ao,
        defense_index=ad,
        full_strength_offense_index=off,
        full_strength_defense_index=deff,
        st_index=st,
        source="test",
        blend_prior_weight=1.0,
        blend_current_weight=0.0,
        games_played=0,
    )


def _book() -> dict[str, TeamStrengthState]:
    # Spread of strengths so Model PR is non-flat.
    return {
        "KC": _strength("KC", 1.12, 1.08),
        "PHI": _strength("PHI", 1.10, 1.06),
        "DET": _strength("DET", 1.08, 1.04),
        "LAR": _strength("LAR", 1.06, 1.02),
        "DAL": _strength("DAL", 1.00, 1.00),
        "NYG": _strength("NYG", 0.94, 0.96),
        "CAR": _strength("CAR", 0.90, 0.92),
        "NE": _strength("NE", 0.88, 0.90),
    }


def test_method_is_b():
    assert METHOD_ID == "B"


def test_alpha_schedule_early_small_late_larger():
    assert alpha_for_week(1) == ALPHA_BY_WEEK[1]
    assert alpha_for_week(1) <= 0.15
    assert alpha_for_week(1) >= 0.10
    assert alpha_for_week(10) >= 0.70
    assert alpha_for_week(1) < alpha_for_week(4) < alpha_for_week(10)


def test_week1_extreme_data_moves_little():
    prior = 2.0
    data = 12.0  # absurd Week-1 signal
    a = alpha_for_week(1)
    published = apply_shrinkage(prior, data, a)
    # Must not replace prior; move is α * gap.
    assert abs(published - prior) < abs(data - prior) * 0.20
    assert abs(published - prior) == pytest.approx(abs(a * (data - prior)))


def test_week10_same_shock_moves_more():
    prior = 2.0
    data = 12.0
    w1 = apply_shrinkage(prior, data, alpha_for_week(1))
    w10 = apply_shrinkage(prior, data, alpha_for_week(10))
    assert abs(w10 - prior) > abs(w1 - prior)


def test_shrink_league_mean_approx_zero():
    prior = {t: float(i - 3) for i, t in enumerate(["A", "B", "C", "D", "E", "F", "G"])}
    prior = zero_center(prior)
    # Extreme data shock that would destroy the board if α=1.
    data = {t: 20.0 if t == "A" else -4.0 for t in prior}
    published, alphas = shrink_model_prs(prior, data, week=1)
    assert abs(sum(published.values()) / len(published)) < 1e-9
    assert all(0.0 < a <= 0.15 for a in alphas.values())


def test_adjusted_alpha_shrinks_more_for_backup_qb():
    base = alpha_for_week(3)
    adj = adjusted_alpha(3, backup_qb=True)
    assert adj < base


def test_model_pr_mean_approx_zero_from_strengths():
    rows = build_desk_rows(_book(), as_of_week=0)
    mean = sum(r.model_pr for r in rows) / len(rows)
    assert abs(mean) < 1e-9
    assert len(rows) == 8
    # Stronger teams should sit above weaker ones.
    by = {r.team: r.model_pr for r in rows}
    assert by["KC"] > by["NE"]
    assert by["PHI"] > by["CAR"]


def test_ryan_adj_default_zero_and_does_not_overwrite_model():
    rows = build_desk_rows(_book())
    for r in rows:
        assert r.ryan_adj == 0.0
        assert r.ryan_pr == r.model_pr
        assert r.base_pr == r.model_pr


def test_la_maps_to_lar_one_row():
    book = {
        "LA": _strength("LA", 1.05, 1.02),
        "KC": _strength("KC", 1.10, 1.05),
    }
    rows = build_desk_rows(book)
    teams = [r.team for r in rows]
    assert "LAR" in teams
    assert "LA" not in teams
    assert product_team_id("LA") == "LAR"


def test_active_pr_reflects_injury_delta():
    book = {
        "KC": _strength(
            "KC", 1.12, 1.08, active_off=1.02, active_def=1.08
        ),
        "DAL": _strength("DAL", 1.00, 1.00),
    }
    rows = build_desk_rows(book)
    kc = next(r for r in rows if r.team == "KC")
    # Injured active offense should pull Active PR below Base/Model.
    assert kc.active_pr < kc.model_pr


def test_expected_margin_monotonic():
    strong = _strength("X", 1.15, 1.10)
    weak = _strength("Y", 0.90, 0.92)
    assert expected_margin_vs_average(strong) > expected_margin_vs_average(weak)


def test_serialize_includes_method_and_lineage():
    strengths = _book()
    universe = EngineUniverse(
        season=2026,
        schedule=[],
        strengths=strengths,
        rosters={t: [] for t in strengths},
    )
    payload = serialize_power_ratings_desk(
        universe,
        season=2026,
        as_of_week=0,
        phase="preseason",
        active_run_id="nfl-preseason-sim-2026-test",
        engine_version="test-engine",
    )
    assert payload["method"] == "B"
    assert payload["active_run_id"] == "nfl-preseason-sim-2026-test"
    assert payload["invariants"]["mean_model_pr_approx_0"] is True
    assert len(payload["teams"]) == 8
    assert "Model PR" in payload["columns"]
    assert "Ryan Adj" in payload["columns"]


def test_derive_raw_then_center():
    raw = derive_raw_model_prs(_book())
    centered = zero_center(raw)
    assert abs(sum(centered.values()) / len(centered)) < 1e-9
