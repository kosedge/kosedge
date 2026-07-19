"""Backtest B: preseason team EPA prior methodology, walk-forward.

Read-only analysis script. Does NOT write to any production table and does
NOT call hydrate_preseason_team_situational() (which would be a safe no-op
against real historical data anyway, since its UPDATE/INSERT guards only
ever touch rows tagged with its own synthetic source values -- but we avoid
even that for a pure validation task).

For each target season Y, replicates the exact "full prior-season average"
core query used by hydrate_preseason_team_situational() (AVG over every
weekly row in nfl_dp_team_situational_weekly for season=Y-1, grouped by
team -- includes playoff weeks for playoff teams, exactly as production
does), for epa_per_play_offense and epa_per_play_defense_allowed. Compares
it against:
  (a) truth = full target-season (Y) average, same columns
  (b) naive = flat carry-forward of the team's single LAST played week of
      season Y-1 (max week with games_played > 0) -- the exact behavior of
      the old carryforward_2025 bug this fix replaced.

Usage: python3 backtest_b_team_epa_prior.py
"""

from __future__ import annotations

import statistics
from collections import defaultdict

import psycopg

DATABASE_URL = "postgresql://ryankos:postgres@127.0.0.1:5432/kosedge"
TARGET_SEASONS = [2023, 2024, 2025]
COLUMNS = ["epa_per_play_offense", "epa_per_play_defense_allowed"]


def full_season_avg(conn, season: int) -> dict[str, dict[str, float]]:
    rows = conn.execute(
        """
        SELECT team, AVG(epa_per_play_offense)::float AS off, AVG(epa_per_play_defense_allowed)::float AS def
        FROM nfl_dp_team_situational_weekly
        WHERE season = %(season)s AND source = 'nflverse'
        GROUP BY team
        """,
        {"season": season},
    ).fetchall()
    return {team: {"epa_per_play_offense": off, "epa_per_play_defense_allowed": defv} for team, off, defv in rows}


def last_week_snapshot(conn, season: int) -> dict[str, dict[str, float]]:
    rows = conn.execute(
        """
        SELECT DISTINCT ON (team) team, epa_per_play_offense::float AS off, epa_per_play_defense_allowed::float AS def, week
        FROM nfl_dp_team_situational_weekly
        WHERE season = %(season)s AND source = 'nflverse' AND games_played > 0
        ORDER BY team, week DESC
        """,
        {"season": season},
    ).fetchall()
    return {team: {"epa_per_play_offense": off, "epa_per_play_defense_allowed": defv, "week": week} for team, off, defv, week in rows}


def mae(errors: list[float]) -> float:
    return statistics.mean(abs(e) for e in errors) if errors else float("nan")


def bias(errors: list[float]) -> float:
    return statistics.mean(errors) if errors else float("nan")


def main() -> None:
    conn = psycopg.connect(DATABASE_URL, autocommit=True)

    all_records = []
    for season in TARGET_SEASONS:
        prior = season - 1
        truth = full_season_avg(conn, season)
        prior_avg = full_season_avg(conn, prior)
        prior_last_week = last_week_snapshot(conn, prior)

        teams = sorted(set(truth) & set(prior_avg) & set(prior_last_week))
        for team in teams:
            rec = {
                "season": season,
                "team": team,
                "last_week_used": prior_last_week[team]["week"],
            }
            for col in COLUMNS:
                rec[f"truth_{col}"] = truth[team][col]
                rec[f"prior_avg_{col}"] = prior_avg[team][col]
                rec[f"last_week_{col}"] = prior_last_week[team][col]
            all_records.append(rec)

    print(f"Seasons backtested: {TARGET_SEASONS}  (n_team_seasons={len(all_records)})")
    print()

    for col in COLUMNS:
        print(f"=== {col} ===")
        avg_err = [r[f"prior_avg_{col}"] - r[f"truth_{col}"] for r in all_records]
        lw_err = [r[f"last_week_{col}"] - r[f"truth_{col}"] for r in all_records]
        print(f"  full prior-season average  -> MAE={mae(avg_err):.4f}  bias={bias(avg_err):.4f}")
        print(f"  last-week-of-prior-season  -> MAE={mae(lw_err):.4f}  bias={bias(lw_err):.4f}")
        improvement = (mae(lw_err) - mae(avg_err)) / mae(lw_err) * 100 if mae(lw_err) else float("nan")
        print(f"  MAE improvement (avg vs last-week): {improvement:.1f}%")
        print()

    print("=== Per-season breakdown ===")
    by_season = defaultdict(list)
    for r in all_records:
        by_season[r["season"]].append(r)
    for season in sorted(by_season):
        rows = by_season[season]
        print(f"-- season {season} (n={len(rows)} teams) --")
        for col in COLUMNS:
            avg_err = [r[f"prior_avg_{col}"] - r[f"truth_{col}"] for r in rows]
            lw_err = [r[f"last_week_{col}"] - r[f"truth_{col}"] for r in rows]
            print(f"   {col}: avg_MAE={mae(avg_err):.4f} avg_bias={bias(avg_err):.4f} | last_week_MAE={mae(lw_err):.4f} last_week_bias={bias(lw_err):.4f}")
    print()

    print("=== Per-team detail (season, team, truth vs prior_avg vs last_week) for epa_per_play_offense ===")
    header = f"{'season':>6} {'team':<5} {'truth':>8} {'prior_avg':>10} {'last_wk':>8} {'lw_week':>7} {'avg_err':>8} {'lw_err':>8}"
    print(header)
    for r in sorted(all_records, key=lambda x: (x["season"], x["team"])):
        col = "epa_per_play_offense"
        avg_err = r[f"prior_avg_{col}"] - r[f"truth_{col}"]
        lw_err = r[f"last_week_{col}"] - r[f"truth_{col}"]
        print(
            f"{r['season']:>6} {r['team']:<5} {r[f'truth_{col}']:>8.3f} {r[f'prior_avg_{col}']:>10.3f} "
            f"{r[f'last_week_{col}']:>8.3f} {r['last_week_used']:>7} {avg_err:>8.3f} {lw_err:>8.3f}"
        )

    import json

    with open(
        "/Users/ryankos/kosedge/data/ops/nfl-preseason-methodology-backtest/backtest_b_records.json",
        "w",
    ) as f:
        json.dump(all_records, f, indent=2, default=str)


if __name__ == "__main__":
    main()
