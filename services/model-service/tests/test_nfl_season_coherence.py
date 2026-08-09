"""Phase-1 season coherence guards: QB1 shape, league pools, W/L zero-sum."""

from __future__ import annotations

from src.services.nfl_season_engine import (
    build_demo_universe,
    compute_universe_season_budgets,
    qb1_distribution_metrics,
    simulate_full_season,
)
from src.services.nfl_season_engine.calibration import (
    ENGINE_VERSION,
    LEAGUE_PASS_YARDS_POOL,
    LEAGUE_RUSH_YARDS_POOL,
    QB1_DISTRIBUTION_TARGETS,
)
from src.services.nfl_season_engine.scoring_bridge import (
    production_to_offensive_points,
    wins_zero_sum_ok,
)
from src.services.nfl_season_engine.season_budgets import (
    TEAM_PASS_VOLUME_IDENTITY_ADJUSTMENTS,
    TeamVolumeFactors,
    allocate_season_totals_into_team_budgets,
    apply_team_pass_volume_identity_adjustments,
    budget_pool_diagnostics,
    compute_team_season_budgets,
    factors_from_universe,
    structural_team_budget,
)


def test_engine_version_is_season_coherence() -> None:
    assert ENGINE_VERSION.startswith("nfl-season-engine-v1.")
    assert any(
        token in ENGINE_VERSION
        for token in (
            "season-coherence",
            "team-priors",
            "offensive-production",
            "defense-points",
            "defense-variance",
            "team-variance",
            "phase2-features",
            "soft-flags",
        )
    )


def test_team_budgets_conserve_league_pools() -> None:
    universe = build_demo_universe(2026)
    budgets = compute_universe_season_budgets(universe)
    diag = budget_pool_diagnostics(budgets)
    assert diag["n_teams"] == 32
    assert diag["pass_pool_ok"] is True
    assert diag["rush_pool_ok"] is True
    assert abs(diag["pass_pool"] - LEAGUE_PASS_YARDS_POOL) < 1.0
    assert abs(diag["rush_pool"] - LEAGUE_RUSH_YARDS_POOL) < 1.0
    # Shape: budgets must not collapse into a tiny band.
    assert diag["pass_budget_stdev"] >= 150.0
    assert diag["pass_budget_max"] - diag["pass_budget_min"] >= 400.0


def test_budget_factors_respond_to_pass_identity() -> None:
    high = TeamVolumeFactors(
        team="KC", offense_index=1.15, pace_factor=1.04, pass_rate_bias=0.04
    )
    low = TeamVolumeFactors(
        team="SF", offense_index=0.95, pace_factor=0.96, pass_rate_bias=-0.04
    )
    budgets = compute_team_season_budgets({"KC": high, "SF": low})
    assert budgets["KC"].pass_yards > budgets["SF"].pass_yards


def test_named_team_identity_overlays_removed_phase2() -> None:
    """Phase 2: ARI/BAL/SEA named pass identity overlays are gone."""
    assert TEAM_PASS_VOLUME_IDENTITY_ADJUSTMENTS == {}
    teams = [
        "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE",
        "DAL", "DEN", "DET", "GB", "HOU", "IND", "JAX", "KC",
        "LA", "LAC", "LV", "MIA", "MIN", "NE", "NO", "NYG",
        "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS",
    ]
    factors = {t: TeamVolumeFactors(team=t) for t in teams}
    raw = {t: structural_team_budget(f) for t, f in factors.items()}
    # Deprecated helper is a no-op.
    adjusted = apply_team_pass_volume_identity_adjustments(raw)
    for t in teams:
        assert adjusted[t].pass_yards == raw[t].pass_yards
    budgets = compute_team_season_budgets(factors)
    assert abs(sum(b.pass_yards for b in budgets.values()) - LEAGUE_PASS_YARDS_POOL) < 1.0


def test_fantasy_budget_allocation_caps_flat_qb1_band() -> None:
    """If every QB1 is ~4250 raw, allocation into budgets must break 32/32≥4000."""
    rows = []
    teams = [
        "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE",
        "DAL", "DEN", "DET", "GB", "HOU", "IND", "JAX", "KC",
        "LA", "LAC", "LV", "MIA", "MIN", "NE", "NO", "NYG",
        "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS",
    ]
    for team in teams:
        rows.append(
            {
                "player_key": f"{team}-QB1",
                "player_name": f"{team} QB1",
                "team": team,
                "position": "QB",
                "pass_yards_total": 4250.0,
                "pass_tds_total": 28.0,
                "rush_yards_total": 200.0,
                "rush_tds_total": 2.0,
                "receiving_yards_total": 0.0,
                "rec_tds_total": 0.0,
            }
        )
        rows.append(
            {
                "player_key": f"{team}-RB1",
                "player_name": f"{team} RB1",
                "team": team,
                "position": "RB",
                "pass_yards_total": 0.0,
                "pass_tds_total": 0.0,
                "rush_yards_total": 900.0,
                "rush_tds_total": 8.0,
                "receiving_yards_total": 300.0,
                "rec_tds_total": 2.0,
            }
        )
    factors = factors_from_universe(build_demo_universe(2026))
    budgets = compute_team_season_budgets(factors)
    allocated, audit = allocate_season_totals_into_team_budgets(rows, budgets)
    metrics = qb1_distribution_metrics(allocated, pass_key="pass_yards_total")
    assert metrics["ge_4000"] < 32
    assert metrics["n_teams"] == 32
    assert audit["method"] == "fantasy_team_budget_alloc_v1"


def test_scoring_bridge_and_wins_guard() -> None:
    pts = production_to_offensive_points(
        pass_yards=3800, rush_yards=1800, pass_tds=24, rush_tds=12, ints=10
    )
    assert pts["offensive_points"] > 200
    assert wins_zero_sum_ok(272.0)
    assert not wins_zero_sum_ok(290.0)


def test_full_season_qb1_distribution_not_all_4000() -> None:
    """Success criteria: FAIL if 32 QB1s still ≥4000; W/L zero-sum holds."""
    universe = build_demo_universe(2026)
    result = simulate_full_season(
        universe, n_sims=16, seed=42, include_diagnostics=True
    )
    assert abs(result.diagnostics["mean_wins_sum"] - 272.0) < 0.05
    coherence = result.diagnostics["season_coherence"]
    qb1 = coherence["qb1_pass_yards"]
    targets = QB1_DISTRIBUTION_TARGETS

    assert coherence["wins_zero_sum_ok"] is True
    assert coherence["all_qb1_ge_4000"] is False
    assert qb1["n_teams"] == 32
    assert qb1["ge_4000"] < 32
    assert qb1["ge_4000"] <= targets["ge_4000_max"]
    assert qb1["ge_4500"] <= targets["ge_4500_max"]
    assert targets["median_min"] <= qb1["median"] <= targets["median_max"]
    assert qb1["p10"] <= targets["p10_max"]
    pools = coherence["league_yards"]
    assert targets["league_pass_pool_min"] <= pools["pass_yards"] <= targets["league_pass_pool_max"]
    assert targets["league_rush_pool_min"] <= pools["rush_yards"] <= targets["league_rush_pool_max"]
