"""Phase-2 defense / PF-PA / W-L conservation guards."""

from __future__ import annotations

from data_platform_nfl.defensive_production_stack import (
    EXPECTED_WINS_SUM,
    apply_defensive_production_stack,
    smoke_defensive_stack,
)


class _Game:
    def __init__(self, home: str, away: str):
        self.home_team = home
        self.away_team = away


def _board_and_schedule():
    teams = [
        "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE",
        "DAL", "DEN", "DET", "GB", "HOU", "IND", "JAX", "KC",
        "LA", "LAC", "LV", "MIA", "MIN", "NE", "NO", "NYG",
        "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS",
    ]
    rows = []
    for i, t in enumerate(teams):
        rows.append(
            {
                "team": t,
                "position": "QB",
                "pass_yards_total": 3900 + (i - 16) * 40,
                "pass_tds_total": 28 + (i - 16) * 0.3,
                "rush_yards_total": 200,
                "rush_tds_total": 2,
                "rec_tds_total": 0,
                "ints_total": 11.0 + (i - 16) * 0.55,  # ~league 350; spread for INT stretch
            }
        )
        rows.append(
            {
                "team": t,
                "position": "RB",
                "pass_yards_total": 0,
                "pass_tds_total": 0,
                "rush_yards_total": 1600 + (i - 16) * 20,
                "rush_tds_total": 10,
                "rec_tds_total": 3,
                "ints_total": 0,
            }
        )
    # Circle method: 272 games, 17 per team.
    schedule = []
    n = len(teams)
    for round_i in range(n - 1):
        for i in range(n // 2):
            home = teams[i]
            away = teams[n - 1 - i]
            schedule.append(_Game(home, away))
        # rotate all but teams[0]
        teams = [teams[0]] + [teams[-1]] + teams[1:-1]
    schedule = schedule[:272]
    # Wider D ladder so takeaways / sacks enter the stretch with real residuals.
    defense = {t: 1.0 + (i - 16) * 0.035 for i, t in enumerate(teams)}
    offense = {t: 1.0 + (16 - i) * 0.02 for i, t in enumerate(teams)}
    return rows, schedule, defense, offense


def test_defense_stack_conserves_pf_pa_wins() -> None:
    rows, schedule, defense, offense = _board_and_schedule()
    # Scale pass yards near 126k for lock check.
    scale = 126_000.0 / sum(float(r["pass_yards_total"]) for r in rows)
    for r in rows:
        r["pass_yards_total"] *= scale
    budgets, audit = apply_defensive_production_stack(
        rows,
        schedule=schedule,
        defense_index=defense,
        offense_index=offense,
    )
    assert audit["applied"] is True
    smoke = audit["smoke"]
    assert smoke["all_pass"] is True, smoke
    assert abs(smoke["league"]["wins_sum"] - EXPECTED_WINS_SUM) <= 0.05
    assert abs(smoke["league"]["points_for"] - smoke["league"]["points_against"]) <= 1.0
    assert smoke_defensive_stack(budgets, rows)["all_pass"] is True
    assert audit["variance_lift"]["applied"] is True
    assert smoke["ranges"]["pa"] >= 85.0
    assert smoke["ranges"]["sacks"] >= 18.0
    assert smoke["ranges"]["ints"] >= 6.0
