"""Real backtest: does a full-season Monte Carlo (independent per-game win
draws from simulate_nfl_game's home_win_prob, using each real game's actual
week-by-week team-strength snapshot -- no leakage, same shape as the live
pipeline) reproduce a plausible real NFL win-total distribution (bell-shaped,
roughly 3-15 wins) for real 2024/2025 seasons? Run once with the RECORD-based
signal (what's actually live in production once week 2+) and once with the
EPA-based signal (what scripts/nfl/historical_market_backtest.py validated),
to see which one's simulated distribution tracks the real, actual final win
totals better.
"""

from __future__ import annotations

import os
import random
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "services", "model-service"))
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge")

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from src.services.nfl_data import team_strength_from_record  # noqa: E402
from src.services.nfl_simulator import NflGameInputs, simulate_nfl_game  # noqa: E402

SEASONS = [2024, 2025]
SEASON_REPLICATES = 2000


def _offense_defense_index_epa(off_epa, def_epa_allowed, pressure_generated, pressure_allowed):
    off_epa = float(off_epa or 0.0)
    def_epa_allowed = float(def_epa_allowed or 0.0)
    pressure_generated = float(pressure_generated or 0.0)
    pressure_allowed = float(pressure_allowed or 0.0)
    pressure_delta = pressure_generated - pressure_allowed
    offense_index = max(0.82, min(1.22, 1.0 + (off_epa * 0.75) + (pressure_delta * 0.18)))
    defense_index = max(0.82, min(1.24, 1.0 + ((-def_epa_allowed) * 0.90) + (pressure_delta * 0.14)))
    return offense_index, defense_index


def summarize_win_dist(name, win_counts_by_team, real_wins_by_team):
    all_teams = sorted(real_wins_by_team.keys())
    print(f"\n  {name}:")
    sim_means = []
    errs = []
    for team in all_teams:
        counts = win_counts_by_team.get(team)
        if not counts:
            continue
        sim_mean = sum(counts) / len(counts)
        sim_means.append(sim_mean)
        real_w = real_wins_by_team[team]
        errs.append(abs(sim_mean - real_w))
    mae_wins = sum(errs) / len(errs) if errs else 0.0
    all_sim_wins = [w for counts in win_counts_by_team.values() for w in counts]
    print(f"    Per-team simulated-mean-wins vs real-wins MAE: {mae_wins:.3f} (n_teams={len(errs)})")
    print(f"    Simulated season win-total distribution (all replicates pooled, n={len(all_sim_wins)}):")
    print(f"      min={min(all_sim_wins)}  p10={sorted(all_sim_wins)[int(0.10*len(all_sim_wins))]}  "
          f"p50={sorted(all_sim_wins)[int(0.50*len(all_sim_wins))]}  "
          f"p90={sorted(all_sim_wins)[int(0.90*len(all_sim_wins))]}  max={max(all_sim_wins)}")
    histogram = defaultdict(int)
    for w in all_sim_wins:
        histogram[w] += 1
    print("    Histogram (wins: count):")
    for w in sorted(histogram):
        pct = 100.0 * histogram[w] / len(all_sim_wins)
        print(f"      {w:>2}: {'#' * int(pct)} ({pct:.1f}%)")
    real_hist = defaultdict(int)
    for team, w in real_wins_by_team.items():
        real_hist[w] += 1
    print("    Real actual final win totals (this season, one point per team):")
    for w in sorted(real_hist):
        print(f"      {w:>2}: {'#' * real_hist[w]} ({real_hist[w]} teams)")


def main() -> None:
    engine = create_engine(os.environ["DATABASE_URL"])
    Session = sessionmaker(bind=engine)
    session = Session()

    for season in SEASONS:
        rows = session.execute(
            text(
                """
                SELECT
                  sch.week, sch.game_id, sch.home_team, sch.away_team,
                  sch.home_score, sch.away_score,
                  hf.off_epa_per_play_5g AS home_off_epa, hf.def_epa_allowed_per_play_5g AS home_def_epa,
                  hf.pressure_rate_generated_5g AS home_pressure_gen, hf.pressure_rate_allowed_5g AS home_pressure_allowed,
                  af.off_epa_per_play_5g AS away_off_epa, af.def_epa_allowed_per_play_5g AS away_def_epa,
                  af.pressure_rate_generated_5g AS away_pressure_gen, af.pressure_rate_allowed_5g AS away_pressure_allowed
                FROM nfl_dp_schedules sch
                LEFT JOIN nfl_dp_team_rolling_features_weekly hf
                  ON hf.season = sch.season AND hf.week = sch.week AND hf.team = sch.home_team
                LEFT JOIN nfl_dp_team_rolling_features_weekly af
                  ON af.season = sch.season AND af.week = sch.week AND af.team = sch.away_team
                WHERE sch.season = :season
                  AND sch.week <= 18
                  AND sch.home_score IS NOT NULL AND sch.away_score IS NOT NULL
                ORDER BY sch.week, sch.game_id
                """
            ),
            {"season": season},
        ).fetchall()

        real_wins_by_team: dict[str, int] = defaultdict(int)
        record: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        game_probs_record = []
        game_probs_epa = []
        game_teams = []

        for r in rows:
            home = str(r.home_team)
            away = str(r.away_team)
            game_teams.append((home, away))
            if r.home_score > r.away_score:
                real_wins_by_team[home] += 1
            elif r.away_score > r.home_score:
                real_wins_by_team[away] += 1

            home_wl = record[home]
            away_wl = record[away]
            rec_off_home, rec_def_home = team_strength_from_record(f"{home_wl[0]}-{home_wl[1]}")
            rec_off_away, rec_def_away = team_strength_from_record(f"{away_wl[0]}-{away_wl[1]}")
            epa_off_home, epa_def_home = _offense_defense_index_epa(
                r.home_off_epa, r.home_def_epa, r.home_pressure_gen, r.home_pressure_allowed
            )
            epa_off_away, epa_def_away = _offense_defense_index_epa(
                r.away_off_epa, r.away_def_epa, r.away_pressure_gen, r.away_pressure_allowed
            )

            seed = abs(hash((str(r.game_id), "season-win-backtest"))) % (2**31)
            rec_proj = simulate_nfl_game(
                NflGameInputs(
                    game_id=str(r.game_id), home_team=home, away_team=away,
                    offense_index_home=rec_off_home, offense_index_away=rec_off_away,
                    defense_index_home=rec_def_home, defense_index_away=rec_def_away,
                    rest_days_home=7.0, rest_days_away=7.0,
                ),
                simulations=800, seed=seed,
            )
            epa_proj = simulate_nfl_game(
                NflGameInputs(
                    game_id=str(r.game_id), home_team=home, away_team=away,
                    offense_index_home=epa_off_home, offense_index_away=epa_off_away,
                    defense_index_home=epa_def_home, defense_index_away=epa_def_away,
                    rest_days_home=7.0, rest_days_away=7.0,
                ),
                simulations=800, seed=seed,
            )
            game_probs_record.append(float(rec_proj["markets"]["home_win_prob"]))
            game_probs_epa.append(float(epa_proj["markets"]["home_win_prob"]))

            if r.home_score > r.away_score:
                home_wl[0] += 1
                away_wl[1] += 1
            elif r.away_score > r.home_score:
                away_wl[0] += 1
                home_wl[1] += 1

        rng = random.Random(1234 + season)
        win_counts_record: dict[str, list[int]] = defaultdict(list)
        win_counts_epa: dict[str, list[int]] = defaultdict(list)
        for _rep in range(SEASON_REPLICATES):
            season_wins_record: dict[str, int] = defaultdict(int)
            season_wins_epa: dict[str, int] = defaultdict(int)
            for (home, away), p_rec, p_epa in zip(game_teams, game_probs_record, game_probs_epa):
                if rng.random() < p_rec:
                    season_wins_record[home] += 1
                else:
                    season_wins_record[away] += 1
                if rng.random() < p_epa:
                    season_wins_epa[home] += 1
                else:
                    season_wins_epa[away] += 1
            for team in real_wins_by_team:
                win_counts_record[team].append(season_wins_record.get(team, 0))
                win_counts_epa[team].append(season_wins_epa.get(team, 0))

        print(f"\n{'=' * 90}\nSEASON {season} (real games={len(rows)}, real teams={len(real_wins_by_team)})")
        summarize_win_dist("RECORD-based (live production signal)", win_counts_record, real_wins_by_team)
        summarize_win_dist("EPA-based (validated backtest signal)", win_counts_epa, real_wins_by_team)

    session.close()


if __name__ == "__main__":
    main()
