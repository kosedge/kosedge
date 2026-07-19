"""Season-level Monte Carlo for the 2026 NFL season using the CURRENT model
(post ghost-team-merge, team-strength-priors fix, live market blend,
validated supervised ML overlay with placeholder-safe adaptive weighting --
see today's session work). This regenerates team_regular_season_outcomes.csv /
super_bowl_winner_probabilities.csv / quality_checks.json with the fixed
model, AND regenerates player_regular_season_totals.csv / player_playoff_totals.csv
fresh from the real per-week nfl_player_projection_baselines data every run
(see services/data_platform_nfl/player_season_totals.py) -- these used to be
`shutil.copy`'d forward unchanged from whatever the oldest existing bundle
contained, silently freezing them at a stale, undocumented methodology. That
is no longer the case: every bundle this script produces is fully
self-contained and regenerated from current data.

Design:
  1. Regular season: reuse the 272 real games' home_win_prob already
     persisted in nfl_market_projections (the actual current-model output,
     including market blend where live odds exist). Bernoulli draw per game
     per replicate -- the standard simplification for season Monte Carlo
     (independent draws; no game-to-game correlation modeled).
  2. Playoffs: no real schedule exists for hypothetical playoff matchups, so
     precompute a 32x32 pairwise home-win-probability matrix ONCE using the
     same simulate_nfl_game() the regular season uses, with each team's real
     offense/defense index and a neutral context (no weather/travel, 7 days
     rest both sides) -- then reuse that matrix for every replicate's
     bracket instead of re-simulating per replicate.
  3. Seeding: top-4 division winners by regular-season win total + next-3
     best remaining records = 7 seeds/conference (current NFL format).
     Ties broken by a small random tiebreak-margin (not a full real
     tiebreaker chain -- documented simplification).
  4. Bracket: standard wildcard/divisional/conference-championship/Super
     Bowl with NFL-style re-seeding (no rematches enforced beyond standard
     seeding). Super Bowl uses a neutral-site probability (symmetrized, no
     home edge) rather than the 32x32 matrix's home-team entry. Each
     replicate's bracket also tallies exactly how many playoff games each
     team played (0 for non-playoff teams, up to 4 for a Super Bowl winner);
     averaged across all 50,000 replicates this gives a real, per-team
     `expected_playoff_games` value (see `total_playoff_games_played` below)
     used directly by the player playoff-totals generator instead of a
     hardcoded games-per-team constant.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from datetime import date, datetime, timezone
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "model-service"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "data-platform-nfl", "src"))
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge")

import numpy as np  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from data_platform_nfl.player_season_totals import generate_and_write_player_season_totals  # noqa: E402
from src.services.nfl_simulator import NflGameInputs, simulate_nfl_game  # noqa: E402
from src.tasks import (  # noqa: E402
    DEFAULT_NFL_MODEL_VERSION,
    NFL_TEAM_DIVISION,
    _load_team_strength_priors,
)

NFL_PLAYER_PROJECTION_MODEL_VERSION = "nfl-player-v1"

SEASON = 2026
N_REPLICATES = 50000
NEUTRAL_SIM_COUNT = 900

CONFERENCE_OF = {abbr: div.split("_")[0] for abbr, div in NFL_TEAM_DIVISION.items()}
DIVISION_LABEL = {
    "AFC_EAST": "AFC East", "AFC_NORTH": "AFC North", "AFC_SOUTH": "AFC South", "AFC_WEST": "AFC West",
    "NFC_EAST": "NFC East", "NFC_NORTH": "NFC North", "NFC_SOUTH": "NFC South", "NFC_WEST": "NFC West",
}
ALL_TEAMS = sorted(NFL_TEAM_DIVISION.keys())


def build_pairwise_matrix(session):
    """team_win_prob[A][B] = P(A wins | A is home, B is away)."""
    priors = _load_team_strength_priors(session, season_year=SEASON)
    matrix: dict[str, dict[str, float]] = {a: {} for a in ALL_TEAMS}
    for home in ALL_TEAMS:
        home_prior = priors.get(home, {})
        for away in ALL_TEAMS:
            if home == away:
                continue
            away_prior = priors.get(away, {})
            inputs = NflGameInputs(
                game_id=f"neutral-{home}-{away}",
                home_team=home,
                away_team=away,
                offense_index_home=float(home_prior.get("offense_index", 1.0)),
                offense_index_away=float(away_prior.get("offense_index", 1.0)),
                defense_index_home=float(home_prior.get("defense_index", 1.0)),
                defense_index_away=float(away_prior.get("defense_index", 1.0)),
                rest_days_home=10.0,
                rest_days_away=10.0,
            )
            seed = abs(hash((home, away, "playoff-matrix"))) % (2**31)
            out = simulate_nfl_game(inputs, simulations=NEUTRAL_SIM_COUNT, seed=seed)
            matrix[home][away] = float(out["markets"]["home_win_prob"])
    return matrix


def neutral_prob(matrix, team_a: str, team_b: str) -> float:
    """Symmetrized neutral-site win prob for team_a over team_b."""
    p_a_home = matrix[team_a][team_b]
    p_b_home = matrix[team_b][team_a]
    # Average team_a's win prob as home vs. its win prob as the visiting
    # team (1 - p_b_home) to cancel out home-field advantage.
    return 0.5 * (p_a_home + (1.0 - p_b_home))


def run_bracket(rng, matrix, seeds_by_conf: dict[str, list[str]]) -> dict[str, Any]:
    """Returns {'AFC_champ':..., 'NFC_champ':..., 'superbowl_winner':...,
    'games_played': {team: games_played_in_this_replicate_bracket}}.

    `games_played` counts every playoff game each of the 14 participating
    teams actually played in THIS replicate (wildcard through Super Bowl,
    inclusive of losses -- a team that loses in the divisional round still
    played 2 games). Non-participating teams are simply absent (0 implied).
    Averaged across all replicates by the caller, this becomes a real
    per-team expected-playoff-games value.
    """
    games_played: dict[str, int] = {}

    def play(home: str, away: str) -> str:
        games_played[home] = games_played.get(home, 0) + 1
        games_played[away] = games_played.get(away, 0) + 1
        p = matrix[home][away]
        return home if rng.random() < p else away

    conf_champs = {}
    for conf, seeds in seeds_by_conf.items():
        # seeds[0..6] = seed 1..7 (best to worst)
        s1, s2, s3, s4, s5, s6, s7 = seeds
        wc1 = play(s2, s7)
        wc2 = play(s3, s6)
        wc3 = play(s4, s5)
        # Divisional re-seeding: #1 hosts lowest remaining seed; other two play.
        survivors = [(2, wc1), (3, wc2), (4, wc3)]
        survivors_by_seed = sorted(survivors, key=lambda x: x[0])
        lowest_remaining = survivors_by_seed[-1][1]
        others = [s for seed, s in survivors_by_seed[:-1]]
        div1 = play(s1, lowest_remaining)
        div2 = play(others[0], others[1]) if len(others) == 2 else div1
        conf_champs[conf] = play(div1, div2) if div1 != div2 else div1

    afc_champ = conf_champs.get("AFC")
    nfc_champ = conf_champs.get("NFC")
    sb_prob_afc = neutral_prob(matrix, afc_champ, nfc_champ)
    games_played[afc_champ] = games_played.get(afc_champ, 0) + 1
    games_played[nfc_champ] = games_played.get(nfc_champ, 0) + 1
    sb_winner = afc_champ if rng.random() < sb_prob_afc else nfc_champ
    return {
        "AFC_champ": afc_champ,
        "NFC_champ": nfc_champ,
        "superbowl_winner": sb_winner,
        "games_played": games_played,
    }


def seed_conference(rng, records: dict[str, int], teams: list[str]) -> list[str]:
    division_winners = []
    for div_key in sorted({NFL_TEAM_DIVISION[t] for t in teams}):
        div_teams = [t for t in teams if NFL_TEAM_DIVISION[t] == div_key]
        winner = max(div_teams, key=lambda t: (records[t], rng.random()))
        division_winners.append(winner)
    division_winners.sort(key=lambda t: (-records[t], rng.random()))
    remaining = [t for t in teams if t not in division_winners]
    remaining.sort(key=lambda t: (-records[t], rng.random()))
    wildcards = remaining[:3]
    return division_winners + wildcards


def main() -> None:
    engine = create_engine(os.environ["DATABASE_URL"])
    Session = sessionmaker(bind=engine)
    session = Session()

    # nfl_dp_schedules (nflverse) is the clean ground truth for the real
    # 272-game schedule (17 games/team, verified). The `games`/
    # nfl_market_projections chain has a residual data-quality issue (~29
    # near-duplicate rows from an earlier ESPN/nflverse date mismatch, see
    # session notes) that corrupts per-team game counts if joined naively --
    # so use nfl_dp_schedules for schedule structure and pull each real
    # matchup's model home_win_prob by (home_abbr, away_abbr) team pair
    # rather than by the unreliable game_id foreign key chain. "LA" is
    # nflverse's Rams code; the web-facing code is "LAR" -- not used here
    # since this script works entirely in nflverse abbreviations.
    rows = session.execute(
        text(
            """
            WITH latest AS (
              SELECT
                mp.home_win_prob,
                ht.abbr AS home_abbr, at.abbr AS away_abbr,
                g.game_date,
                ROW_NUMBER() OVER (
                  PARTITION BY ht.abbr, at.abbr, g.game_date
                  ORDER BY mp.created_at DESC
                ) AS rn
              FROM nfl_market_projections mp
              JOIN games g ON g.id = mp.game_id
              JOIN seasons s ON s.id = g.season_id
              JOIN teams ht ON ht.id = g.home_team_id
              JOIN teams at ON at.id = g.away_team_id
              -- season_year is naively derived from calendar year at
              -- ingestion time (_ensure_hierarchy), so week 17-18 games
              -- played in early January get mislabeled season_year+1 --
              -- accept both for the real 2026 NFL season (Sep 2026-Jan 2027).
              WHERE s.season_year IN (:season, :season + 1) AND mp.model_version = :model_version
                AND mp.home_win_prob IS NOT NULL
            ),
            per_matchup AS (
              SELECT
                home_abbr, away_abbr, home_win_prob,
                ROW_NUMBER() OVER (PARTITION BY home_abbr, away_abbr ORDER BY game_date) AS matchup_rn
              FROM latest WHERE rn = 1
            ),
            schedule AS (
              SELECT
                CASE WHEN home_team = 'LA' THEN 'LA' ELSE home_team END AS home,
                CASE WHEN away_team = 'LA' THEN 'LA' ELSE away_team END AS away,
                week
              FROM nfl_dp_schedules
              WHERE season = :season
            )
            SELECT DISTINCT ON (schedule.home, schedule.away)
              schedule.home, schedule.away, pm.home_win_prob
            FROM schedule
            LEFT JOIN per_matchup pm
              ON pm.home_abbr = schedule.home AND pm.away_abbr = schedule.away
            """
        ),
        {"season": SEASON, "model_version": DEFAULT_NFL_MODEL_VERSION},
    ).fetchall()
    games = [(str(r.home), str(r.away), float(r.home_win_prob)) for r in rows if r.home_win_prob is not None]
    missing = [(str(r.home), str(r.away)) for r in rows if r.home_win_prob is None]
    print(f"Loaded {len(games)}/272 real 2026 schedule games with a model win-prob.")
    if missing:
        print(f"WARNING: {len(missing)} schedule games have no model projection yet, excluded: {missing[:10]}...")

    games_per_team: dict[str, int] = {t: 0 for t in ALL_TEAMS}
    for home, away, _ in games:
        games_per_team[home] += 1
        games_per_team[away] += 1
    off_counts = {t: n for t, n in games_per_team.items() if n < 15}
    if off_counts:
        print(f"NOTE: teams with fewer than 15 games (missing projections): {off_counts}")

    print("Precomputing 32x32 pairwise matchup matrix for playoffs...")
    matrix = build_pairwise_matrix(session)
    session.close()
    print("Matrix ready.")

    rng = np.random.default_rng(2026)
    win_counts = {t: np.zeros(N_REPLICATES, dtype=np.int16) for t in ALL_TEAMS}
    made_playoffs = {t: 0 for t in ALL_TEAMS}
    won_division = {t: 0 for t in ALL_TEAMS}
    won_superbowl = {t: 0 for t in ALL_TEAMS}
    total_playoff_games_played = {t: 0 for t in ALL_TEAMS}

    home_teams = [g[0] for g in games]
    away_teams = [g[0 - 1] if False else g[1] for g in games]
    probs = np.array([g[2] for g in games])

    for rep in range(N_REPLICATES):
        draws = rng.random(len(games)) < probs
        records = {t: 0 for t in ALL_TEAMS}
        for i, (home, away, _p) in enumerate(games):
            if draws[i]:
                records[home] += 1
            else:
                records[away] += 1
        for t in ALL_TEAMS:
            win_counts[t][rep] = records[t]

        afc_teams = [t for t in ALL_TEAMS if CONFERENCE_OF[t] == "AFC"]
        nfc_teams = [t for t in ALL_TEAMS if CONFERENCE_OF[t] == "NFC"]
        seeds = {
            "AFC": seed_conference(rng, records, afc_teams),
            "NFC": seed_conference(rng, records, nfc_teams),
        }
        for conf_seeds in seeds.values():
            for i, t in enumerate(conf_seeds):
                if i < 4:
                    won_division[t] += 1
                made_playoffs[t] += 1

        result = run_bracket(rng, matrix, seeds)
        won_superbowl[result["superbowl_winner"]] += 1
        for t, games_played_count in result["games_played"].items():
            total_playoff_games_played[t] += games_played_count

        if rep % 2000 == 0:
            print(f"  ...{rep}/{N_REPLICATES} replicates")

    print("Simulation complete. Building output rows.")

    expected_playoff_games_by_team = {
        t: round(total_playoff_games_played[t] / N_REPLICATES, 4) for t in ALL_TEAMS
    }

    team_rows = []
    for t in ALL_TEAMS:
        wins = win_counts[t]
        team_rows.append(
            {
                "season": SEASON,
                "team": t,
                "conference": CONFERENCE_OF[t],
                "division": DIVISION_LABEL[NFL_TEAM_DIVISION[t]],
                "expected_wins": round(float(np.mean(wins)), 3),
                "wins_p10": int(np.percentile(wins, 10)),
                "wins_p90": int(np.percentile(wins, 90)),
                "playoff_prob": round(made_playoffs[t] / N_REPLICATES, 4),
                "division_title_prob": round(won_division[t] / N_REPLICATES, 4),
                "super_bowl_win_prob": round(won_superbowl[t] / N_REPLICATES, 5),
            }
        )
    team_rows.sort(key=lambda r: -r["expected_wins"])

    sum_sb = sum(r["super_bowl_win_prob"] for r in team_rows)
    sum_div = sum(r["division_title_prob"] for r in team_rows)
    sum_playoff = sum(r["playoff_prob"] for r in team_rows)
    print(f"Sanity: sum_sb_prob={sum_sb:.4f} sum_div_title_prob={sum_div:.4f} sum_playoff_prob={sum_playoff:.4f}")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    ops_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "ops")
    out_dir = os.path.join(ops_dir, f"nfl-preseason-sim-2026-{timestamp}")
    os.makedirs(out_dir, exist_ok=True)

    print("Generating fresh player season-total CSVs from nfl_player_projection_baselines...")
    player_totals_engine = create_engine(os.environ["DATABASE_URL"])
    PlayerTotalsSession = sessionmaker(bind=player_totals_engine)
    player_totals_session = PlayerTotalsSession()
    try:
        player_totals_summary = generate_and_write_player_season_totals(
            player_totals_session,
            season=SEASON,
            out_dir=out_dir,
            expected_playoff_games_by_team=expected_playoff_games_by_team,
            model_version=NFL_PLAYER_PROJECTION_MODEL_VERSION,
        )
        print(f"Player season totals: {player_totals_summary}")
    finally:
        player_totals_session.close()

    with open(os.path.join(out_dir, "team_regular_season_outcomes.csv"), "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "season", "team", "conference", "division", "expected_wins",
                "wins_p10", "wins_p90", "playoff_prob", "division_title_prob", "super_bowl_win_prob",
            ],
        )
        writer.writeheader()
        writer.writerows(team_rows)

    sb_rows = sorted(team_rows, key=lambda r: -r["super_bowl_win_prob"])
    with open(os.path.join(out_dir, "super_bowl_winner_probabilities.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["season", "team", "super_bowl_win_prob"])
        writer.writeheader()
        for r in sb_rows:
            writer.writerow({"season": r["season"], "team": r["team"], "super_bowl_win_prob": r["super_bowl_win_prob"]})

    quality_checks = {
        "metadata": {
            "season": SEASON,
            "model_version": DEFAULT_NFL_MODEL_VERSION,
            "game_simulation_count": NEUTRAL_SIM_COUNT,
            "season_monte_carlo_iterations": N_REPLICATES,
            "note": "Regular season reuses persisted nfl_market_projections home_win_prob per real game (current fixed model); playoffs use a precomputed pairwise matrix from the same simulator with neutral context.",
        },
        "counts": {
            "games_total": len(games),
            "games_regular": len(games),
            "team_outcome_rows": len(team_rows),
            "super_bowl_rows": len(sb_rows),
        },
        "sanity": {
            "sum_super_bowl_prob": round(sum_sb, 4),
            "sum_division_title_prob": round(sum_div, 4),
            "sum_playoff_prob": round(sum_playoff, 4),
        },
        "top10_playoff_odds": team_rows[:10],
        "top10_super_bowl": [
            {"season": r["season"], "team": r["team"], "super_bowl_win_prob": r["super_bowl_win_prob"]}
            for r in sb_rows[:10]
        ],
        "expected_playoff_games_by_team": expected_playoff_games_by_team,
        "player_season_totals": player_totals_summary,
    }
    with open(os.path.join(out_dir, "quality_checks.json"), "w") as f:
        json.dump(quality_checks, f, indent=2)

    with open(os.path.join(out_dir, "run_summary.json"), "w") as f:
        json.dump(
            {
                "output_dir": out_dir,
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "files": [
                    "team_regular_season_outcomes.csv",
                    "super_bowl_winner_probabilities.csv",
                    "quality_checks.json",
                    "player_regular_season_totals.csv",
                    "player_playoff_totals.csv",
                ],
                "note": "Player projection CSVs are freshly generated every run from nfl_player_projection_baselines (see data_platform_nfl.player_season_totals) -- no longer copied forward from a prior bundle.",
                "player_projection_model_version": NFL_PLAYER_PROJECTION_MODEL_VERSION,
            },
            f,
            indent=2,
        )

    print(f"\nWrote bundle to {out_dir}")
    print("\nTop 10 by expected wins:")
    for r in team_rows[:10]:
        print(
            f"  {r['team']:<4} {r['conference']} {r['division']:<12} exp_wins={r['expected_wins']:<6} "
            f"playoff={r['playoff_prob']:.3f} div_title={r['division_title_prob']:.3f} sb={r['super_bowl_win_prob']:.4f}"
        )
    print(f"\nBundle dir: {out_dir}")


if __name__ == "__main__":
    main()
