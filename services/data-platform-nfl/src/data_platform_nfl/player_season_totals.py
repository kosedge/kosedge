"""Real, permanent generator for the player season-total artifact CSVs
(`player_regular_season_totals.csv` / `player_playoff_totals.csv`) consumed
directly by the live web app (see apps/web/lib/nfl-preseason-artifacts.ts).

Replaces the prior undocumented approach in scripts/nfl/simulate_2026_season.py,
which simply `shutil.copy`'d these two files forward from whatever the oldest
existing data/ops bundle happened to contain -- meaning they silently froze at
whatever methodology produced them (a flat `games_projected=18` for every
regular-season player, and `games_projected=4` for every playoff player,
neither reflecting real per-week variation), and were never regenerated after
this session's player-projection pipeline fixes (nfl_dp_player_usage_weekly /
nfl_player_projection_features_weekly / rookie baselines).

This module is DB-only (reads nfl_player_projection_baselines and
nfl_dp_schedules, both plain tables -- no model-service Python imports
required), so it lives here rather than in services/model-service, matching
the service-boundary convention used by preseason_hydration.py and
rookie_baselines.py: model-service owns *producing* the weekly baseline rows
(materialize_nfl_player_baseline_projections), this module owns *aggregating*
already-materialized rows into a season-total shape.

Regular season methodology
---------------------------
For every player, across every week that player's team has a REAL scheduled
game that season (see `_real_game_weeks_by_team`, keyed off game_id being
non-empty on the weekly baseline row -- bye weeks leave game_id blank, see
nfl_player_projection_features_weekly's `source <> ` guarded ingestion):
  - `*_yards_total` / `*_tds_total` = sum of that week's `*_mean` projection.
    Summing per-week means is the statistically correct way to build an
    expected season total from a set of per-week expected values (linearity
    of expectation) -- no distributional assumption beyond independence
    across weeks is required.
  - `games_projected` = COUNT of real weeks with a row for that player (NOT a
    hardcoded constant). A player whose team has a bye some week, or who is
    being projected mid-season with fewer remaining weeks, naturally gets a
    smaller count.
  - `anytime_td_prob` = 1 - PRODUCT_w(1 - anytime_td_prob_w): the probability
    the player scores a TD in AT LEAST ONE of their real games this season,
    assuming independence across weeks. This is the deliberate choice over
    the alternative "expected total TD-scoring games" (= sum of weekly
    rush_tds_mean+rec_tds_mean, which is already redundant with the
    rush_tds_total/rec_tds_total columns two columns over) because the field
    is literally named `anytime_td_prob` -- callers (including the web app)
    reasonably expect a bounded [0, 1] probability, not a raw expected count
    that can exceed 1.0 for a bell-cow RB/WR over a full season. Summing the
    means already gives you the "expected TD count" number via
    rush_tds_total + rec_tds_total; this field intentionally preserves
    probability semantics instead of duplicating that.

Playoff methodology
--------------------
There is no real playoff schedule to project against. Instead:
  - Compute each player's REGULAR-SEASON per-game rate (season total / real
    games played, from the exact same aggregation above) as the basis rate --
    a team's playoff-week usage pattern for a given player is assumed to look
    like their season-average usage, which is the same assumption the task
    explicitly sanctions ("a team's playoff roster/usage doesn't fundamentally
    change"). Using the season AVERAGE per-game rate rather than picking one
    arbitrary regular-season week is a deliberate refinement: it is a smoothed
    read on the player's role that already nets out any single bye-adjacent
    or blowout-distorted week.
  - Multiply by that player's team's EXPECTED number of playoff games, which
    should be the real Monte-Carlo-derived value from
    scripts/nfl/simulate_2026_season.py's 50,000-replicate bracket sim (each
    replicate already resolves exactly how many playoff games a team plays --
    0 if eliminated in the regular season, up through 4 for a Super Bowl
    winner -- see `total_playoff_games_played` counter added to that script).
    If that per-team dict isn't available (e.g. this module used standalone
    without the simulator wired in), `FALLBACK_EXPECTED_GAMES_GIVEN_APPEARANCE`
    provides a documented, derived (not guessed) fallback -- see its
    docstring for the bracket-structure derivation.
  - `anytime_td_prob` for playoffs re-applies the same "at least one game"
    formula, but over a fractional/expected number of games: using each
    player's regular-season AVERAGE (not summed) weekly anytime_td_prob as a
    per-game rate p, playoff anytime_td_prob = 1 - (1-p)^expected_games. This
    is the continuous generalization of the regular-season formula (valid for
    non-integer "games" because it's already an expectation calculation, not
    a per-game simulation) and collapses to the same formula if
    expected_games happened to be a whole number of certain playoff games.
"""

from __future__ import annotations

import csv
import os
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import text

CSV_FIELDNAMES: List[str] = [
    "season",
    "player_key",
    "player_name",
    "team",
    "position",
    "games_projected",
    "pass_yards_total",
    "rush_yards_total",
    "receiving_yards_total",
    "receptions_total",
    "pass_tds_total",
    "rush_tds_total",
    "rec_tds_total",
    "anytime_td_prob",
]

_WEEKLY_STAT_KEYS = (
    "pass_yards_mean",
    "rush_yards_mean",
    "receiving_yards_mean",
    "receptions_mean",
    "pass_tds_mean",
    "rush_tds_mean",
    "rec_tds_mean",
)

# Derivation: the current 7-seeds-per-conference (14-team) playoff bracket
# plays 6 wildcard-round games + 4 divisional-round games + 2 conference
# championship games + 1 Super Bowl = 13 games total, i.e. 26 team-game
# appearances (each game has 2 participating teams). Spread evenly across
# the 14 teams that make the playoffs in any given season, that is
# 26 / 14 ~= 1.857 games per playoff appearance on average. This is an
# unweighted average across all seeds (a bye-week #1 seed plays fewer early
# games but survives longer on average, a 7-seed usually plays exactly one
# game and exits) -- a real per-team estimate (from the season Monte Carlo,
# see scripts/nfl/simulate_2026_season.py's total_playoff_games_played
# counter) is always preferred over this leaguewide constant when available.
FALLBACK_EXPECTED_GAMES_GIVEN_APPEARANCE = 26.0 / 14.0


def aggregate_weekly_projection_rows(weekly_rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Pure aggregation: turn a player's list of real-week baseline rows into
    one season-total dict. Each item of `weekly_rows` must provide the keys in
    `_WEEKLY_STAT_KEYS` plus `anytime_td_prob` (all as floats/None).

    Returns the season-shaped numeric fields only (games_projected plus the
    8 `*_total` / `anytime_td_prob` fields) -- identity fields (player_name,
    team, position, player_key) are attached by the caller since they don't
    require any statistical aggregation.
    """
    rows = list(weekly_rows)
    games_projected = len(rows)

    def _sum(key: str) -> float:
        return round(sum(float(row.get(key) or 0.0) for row in rows), 3)

    prob_survives_tdless = 1.0
    for row in rows:
        p = max(0.0, min(1.0, float(row.get("anytime_td_prob") or 0.0)))
        prob_survives_tdless *= (1.0 - p)
    season_anytime_td_prob = round(1.0 - prob_survives_tdless, 4)

    return {
        "games_projected": games_projected,
        "pass_yards_total": _sum("pass_yards_mean"),
        "rush_yards_total": _sum("rush_yards_mean"),
        "receiving_yards_total": _sum("receiving_yards_mean"),
        "receptions_total": _sum("receptions_mean"),
        "pass_tds_total": _sum("pass_tds_mean"),
        "rush_tds_total": _sum("rush_tds_mean"),
        "rec_tds_total": _sum("rec_tds_mean"),
        "anytime_td_prob": season_anytime_td_prob,
    }


def _fetch_real_weekly_rows(
    session: Any, *, season: int, model_version: str, weeks: Optional[List[int]] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """Returns {player_key: [weekly_row_dict, ...]} for every REAL game week
    (game_id present -- bye weeks leave it blank, see module docstring),
    ordered by week. player_key is `player_uid` when resolved, else falls
    back to `team:player_id` so no player is silently dropped even if
    identity resolution hasn't run for them yet.
    """
    week_filter = "AND week = ANY(:weeks)" if weeks else ""
    params: Dict[str, Any] = {"season": int(season), "model_version": model_version}
    if weeks:
        params["weeks"] = list(weeks)
    rows = session.execute(
        text(
            f"""
            SELECT
              week, team, player_id, player_uid, player_name, position, game_id,
              pass_yards_mean, rush_yards_mean, receiving_yards_mean, receptions_mean,
              pass_tds_mean, rush_tds_mean, rec_tds_mean, anytime_td_prob
            FROM nfl_player_projection_baselines
            WHERE season = :season
              AND model_version = :model_version
              AND game_id IS NOT NULL AND game_id <> ''
              {week_filter}
            ORDER BY week
            """
        ),
        params,
    ).mappings().all()

    by_player: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        player_key = str(row["player_uid"]) if row["player_uid"] is not None else f"{row['team']}:{row['player_id']}"
        by_player.setdefault(player_key, []).append(dict(row))
    return by_player


def generate_player_regular_season_totals(
    session: Any, *, season: int, model_version: str = "nfl-player-v1"
) -> List[Dict[str, Any]]:
    """Season-total rows for every player with at least one real regular-season
    weekly projection, in `CSV_FIELDNAMES` shape."""
    by_player = _fetch_real_weekly_rows(session, season=season, model_version=model_version)

    output_rows: List[Dict[str, Any]] = []
    for player_key, weekly_rows in by_player.items():
        latest = weekly_rows[-1]
        totals = aggregate_weekly_projection_rows(weekly_rows)
        output_rows.append(
            {
                "season": season,
                "player_key": player_key,
                "player_name": latest["player_name"],
                "team": latest["team"],
                "position": latest["position"],
                **totals,
            }
        )
    output_rows.sort(key=lambda r: (-r["pass_yards_total"] - r["rush_yards_total"] - r["receiving_yards_total"], r["player_name"]))
    return output_rows


def generate_player_playoff_totals(
    session: Any,
    *,
    season: int,
    expected_playoff_games_by_team: Dict[str, float],
    model_version: str = "nfl-player-v1",
) -> List[Dict[str, Any]]:
    """Expectation-weighted playoff season-total rows (see module docstring
    for the full methodology). `expected_playoff_games_by_team` should be the
    real per-team expected-games-played value from the season Monte Carlo;
    any team missing from the dict is treated as 0 expected playoff games
    (did not make the field in this simulation).
    """
    by_player = _fetch_real_weekly_rows(session, season=season, model_version=model_version)

    output_rows: List[Dict[str, Any]] = []
    for player_key, weekly_rows in by_player.items():
        latest = weekly_rows[-1]
        team = latest["team"]
        expected_games = float(expected_playoff_games_by_team.get(team, 0.0))
        real_games_played = len(weekly_rows)
        if real_games_played == 0 or expected_games <= 0.0:
            per_game = {key: 0.0 for key in _WEEKLY_STAT_KEYS}
            mean_weekly_anytime_td_prob = 0.0
        else:
            season_totals = aggregate_weekly_projection_rows(weekly_rows)
            per_game = {
                "pass_yards_mean": season_totals["pass_yards_total"] / real_games_played,
                "rush_yards_mean": season_totals["rush_yards_total"] / real_games_played,
                "receiving_yards_mean": season_totals["receiving_yards_total"] / real_games_played,
                "receptions_mean": season_totals["receptions_total"] / real_games_played,
                "pass_tds_mean": season_totals["pass_tds_total"] / real_games_played,
                "rush_tds_mean": season_totals["rush_tds_total"] / real_games_played,
                "rec_tds_mean": season_totals["rec_tds_total"] / real_games_played,
            }
            mean_weekly_anytime_td_prob = sum(
                max(0.0, min(1.0, float(r.get("anytime_td_prob") or 0.0))) for r in weekly_rows
            ) / real_games_played

        playoff_anytime_td_prob = round(1.0 - (1.0 - mean_weekly_anytime_td_prob) ** expected_games, 4)
        output_rows.append(
            {
                "season": season,
                "player_key": player_key,
                "player_name": latest["player_name"],
                "team": team,
                "position": latest["position"],
                "games_projected": round(expected_games, 4),
                "pass_yards_total": round(per_game["pass_yards_mean"] * expected_games, 3),
                "rush_yards_total": round(per_game["rush_yards_mean"] * expected_games, 3),
                "receiving_yards_total": round(per_game["receiving_yards_mean"] * expected_games, 3),
                "receptions_total": round(per_game["receptions_mean"] * expected_games, 3),
                "pass_tds_total": round(per_game["pass_tds_mean"] * expected_games, 3),
                "rush_tds_total": round(per_game["rush_tds_mean"] * expected_games, 3),
                "rec_tds_total": round(per_game["rec_tds_mean"] * expected_games, 3),
                "anytime_td_prob": playoff_anytime_td_prob,
            }
        )
    output_rows.sort(key=lambda r: (-r["pass_yards_total"] - r["rush_yards_total"] - r["receiving_yards_total"], r["player_name"]))
    return output_rows


def write_player_totals_csv(rows: List[Dict[str, Any]], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in CSV_FIELDNAMES})


def generate_and_write_player_season_totals(
    session: Any,
    *,
    season: int,
    out_dir: str,
    expected_playoff_games_by_team: Dict[str, float],
    model_version: str = "nfl-player-v1",
) -> Dict[str, Any]:
    """The single entry point called from scripts/nfl/simulate_2026_season.py.
    Writes both CSVs directly into `out_dir` and returns a small summary dict
    suitable for embedding in that script's run_summary.json."""
    regular_rows = generate_player_regular_season_totals(session, season=season, model_version=model_version)
    playoff_rows = generate_player_playoff_totals(
        session,
        season=season,
        expected_playoff_games_by_team=expected_playoff_games_by_team,
        model_version=model_version,
    )
    write_player_totals_csv(regular_rows, os.path.join(out_dir, "player_regular_season_totals.csv"))
    write_player_totals_csv(playoff_rows, os.path.join(out_dir, "player_playoff_totals.csv"))
    games_projected_values = sorted({r["games_projected"] for r in regular_rows})
    return {
        "status": "ok",
        "season": season,
        "model_version": model_version,
        "regular_season_player_rows": len(regular_rows),
        "playoff_player_rows": len(playoff_rows),
        "distinct_games_projected_values": games_projected_values,
    }
