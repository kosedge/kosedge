"""Fantasy-path team volume budget allocation (season coherence v1.16)."""

from __future__ import annotations

from data_platform_nfl.team_volume_budgets import (
    LEAGUE_PASS_YARDS_POOL,
    apply_team_volume_budgets,
    compute_team_season_budgets,
)


def test_budgets_sum_to_league_pool() -> None:
    strengths = {
        t: {"offense_index": 1.0 + (i - 16) * 0.01, "pace_factor": 1.0, "pass_rate_bias": 0.0}
        for i, t in enumerate(
            [
                "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE",
                "DAL", "DEN", "DET", "GB", "HOU", "IND", "JAX", "KC",
                "LA", "LAC", "LV", "MIA", "MIN", "NE", "NO", "NYG",
                "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS",
            ]
        )
    }
    budgets = compute_team_season_budgets(strengths)
    assert abs(sum(b.pass_yards for b in budgets.values()) - LEAGUE_PASS_YARDS_POOL) < 1.0


def test_apply_breaks_flat_4000_band() -> None:
    rows = []
    for team in [
        "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE",
        "DAL", "DEN", "DET", "GB", "HOU", "IND", "JAX", "KC",
        "LA", "LAC", "LV", "MIA", "MIN", "NE", "NO", "NYG",
        "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS",
    ]:
        rows.append(
            {
                "player_key": f"{team}-QB1",
                "player_name": f"{team} QB",
                "team": team,
                "position": "QB",
                "pass_yards_total": 4300.0,
                "pass_tds_total": 30.0,
                "rush_yards_total": 150.0,
                "rush_tds_total": 1.0,
                "receiving_yards_total": 0.0,
                "rec_tds_total": 0.0,
            }
        )
    out, audit = apply_team_volume_budgets(rows)
    qb1 = [
        float(r["pass_yards_total"])
        for r in out
        if r["position"] == "QB"
    ]
    assert sum(1 for y in qb1 if y >= 4000) < 32
    assert audit["applied"] is True
    assert abs(audit["pass_pool"] - LEAGUE_PASS_YARDS_POOL) < 1.0
