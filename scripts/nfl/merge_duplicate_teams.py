"""One-time data-quality fix: merge duplicate NFL "ghost" teams/games.

Root cause: the canonical `games`/`teams` rows for NFL were bulk-backfilled
from nfl_dp_schedules using nflverse abbreviations (e.g. name=abbr="LA" for
the Rams). Odds ingestion (`_persist_odds_events` -> `_ensure_hierarchy` in
tasks.py) resolves teams by matching `teams.name` against the full team name
The Odds API returns (e.g. "Los Angeles Rams"), which never matches the
abbreviated canonical row. This silently created a second "ghost" team row
per team (with a garbled auto-generated abbreviation such as "LOANRA") and,
because the games unique constraint includes team_id, a second "ghost" game
row per matchup -- orphaning all odds snapshots attached to those games from
the canonical simulation/market pipeline.

This script, for every NFL ghost team:
  1. Resolves the canonical team row by real-world abbreviation.
  2. For every ghost game referencing the ghost team (as home or away),
     finds the equivalent canonical game (same season + date + canonical
     home/away team ids). If found, re-points every FK table that references
     games(id) from the ghost game to the canonical game (row-by-row, so a
     unique-constraint conflict on one row just drops that row instead of
     aborting the whole migration), then deletes the now-empty ghost game.
     If no canonical game exists, it just repoints the ghost game's
     home/away team ids in place (no game row is deleted).
  3. Deletes the now-unreferenced ghost team row.

Safe to re-run: it is idempotent once ghost rows are gone.
"""

from __future__ import annotations

import os

import psycopg
from psycopg import errors as psycopg_errors

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://ryankos:postgres@127.0.0.1:5432/kosedge"
)

# Ghost team full name -> canonical current-day nflverse abbreviation.
FULL_NAME_TO_ABBR = {
    "Arizona Cardinals": "ARI",
    "Atlanta Falcons": "ATL",
    "Baltimore Ravens": "BAL",
    "Buffalo Bills": "BUF",
    "Carolina Panthers": "CAR",
    "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN",
    "Cleveland Browns": "CLE",
    "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN",
    "Detroit Lions": "DET",
    "Green Bay Packers": "GB",
    "Houston Texans": "HOU",
    "Indianapolis Colts": "IND",
    "Jacksonville Jaguars": "JAX",
    "Kansas City Chiefs": "KC",
    "Las Vegas Raiders": "LV",
    "Los Angeles Chargers": "LAC",
    "Los Angeles Rams": "LA",
    "Miami Dolphins": "MIA",
    "Minnesota Vikings": "MIN",
    "New England Patriots": "NE",
    "New Orleans Saints": "NO",
    "New York Giants": "NYG",
    "New York Jets": "NYJ",
    "Philadelphia Eagles": "PHI",
    "Pittsburgh Steelers": "PIT",
    "San Francisco 49ers": "SF",
    "Seattle Seahawks": "SEA",
    "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN",
    "Washington Commanders": "WAS",
}

# Tables with a `game_id` FK into games(id) (see information_schema query).
# Most have a surrogate `id` PK; a couple key directly on `game_id`.
GAME_FK_TABLES = [
    "odds_snapshots",
    "closing_lines",
    "model_game_predictions",
    "model_edges",
    "bets",
    "nfl_game_context",
    "nfl_market_projections",
    "nfl_market_outcomes",
    "nfl_market_history_snapshots",
    "nfl_clv_attribution",
    "nfl_portfolio_recommendations",
    "nfl_player_prop_market_snapshots",
    "nfl_player_prop_model_edges",
]

# Tables whose primary key IS `game_id` (one row per game); there is no
# separate surrogate `id` column to select/delete by.
GAME_ID_KEYED_TABLES = {"nfl_game_context", "nfl_market_outcomes"}


def main() -> None:
    conn = psycopg.connect(DATABASE_URL, autocommit=False)
    cur = conn.cursor()

    cur.execute("SELECT id FROM leagues WHERE code = 'nfl'")
    league_row = cur.fetchone()
    if not league_row:
        print("No NFL league row found; nothing to do.")
        return
    league_id = league_row[0]

    cur.execute(
        "SELECT id, name, abbr FROM teams WHERE league_id = %s",
        (league_id,),
    )
    all_teams = cur.fetchall()
    canonical_by_abbr = {abbr: tid for tid, name, abbr in all_teams if name == abbr}
    ghost_teams = [
        (tid, name, abbr)
        for tid, name, abbr in all_teams
        if name in FULL_NAME_TO_ABBR and FULL_NAME_TO_ABBR[name] != abbr
    ]

    print(f"Found {len(ghost_teams)} ghost NFL team rows.")

    ghost_to_canonical_team: dict = {}
    for tid, name, abbr in ghost_teams:
        canonical_abbr = FULL_NAME_TO_ABBR[name]
        canonical_id = canonical_by_abbr.get(canonical_abbr)
        if not canonical_id:
            print(f"  SKIP {name} ({abbr}): no canonical '{canonical_abbr}' team row found")
            continue
        ghost_to_canonical_team[tid] = canonical_id

    ghost_team_ids = list(ghost_to_canonical_team.keys())
    if not ghost_team_ids:
        print("No resolvable ghost teams; exiting.")
        return

    cur.execute(
        """
        SELECT id, season_id, game_date, home_team_id, away_team_id
        FROM games
        WHERE home_team_id = ANY(%s) OR away_team_id = ANY(%s)
        """,
        (ghost_team_ids, ghost_team_ids),
    )
    ghost_games = cur.fetchall()
    print(f"Found {len(ghost_games)} ghost game rows to reconcile.")

    games_deleted = 0
    games_repointed_in_place = 0
    rows_migrated = 0
    rows_dropped_on_conflict = 0

    for game_id, season_id, game_date, home_id, away_id in ghost_games:
        canonical_home = ghost_to_canonical_team.get(home_id, home_id)
        canonical_away = ghost_to_canonical_team.get(away_id, away_id)

        cur.execute(
            """
            SELECT id FROM games
            WHERE season_id = %s AND game_date = %s
              AND home_team_id = %s AND away_team_id = %s
              AND id <> %s
            """,
            (season_id, game_date, canonical_home, canonical_away, game_id),
        )
        canonical_game_row = cur.fetchone()

        if canonical_game_row is None:
            # No canonical duplicate exists yet; just fix this game's team ids in place.
            cur.execute(
                "UPDATE games SET home_team_id = %s, away_team_id = %s WHERE id = %s",
                (canonical_home, canonical_away, game_id),
            )
            games_repointed_in_place += 1
            continue

        canonical_game_id = canonical_game_row[0]

        for table in GAME_FK_TABLES:
            if table in GAME_ID_KEYED_TABLES:
                cur.execute("SAVEPOINT row_move")
                try:
                    cur.execute(
                        f"UPDATE {table} SET game_id = %s WHERE game_id = %s",
                        (canonical_game_id, game_id),
                    )
                    rows_migrated += cur.rowcount
                except psycopg_errors.UniqueViolation:
                    cur.execute("ROLLBACK TO SAVEPOINT row_move")
                    cur.execute(f"DELETE FROM {table} WHERE game_id = %s", (game_id,))
                    rows_dropped_on_conflict += 1
                else:
                    cur.execute("RELEASE SAVEPOINT row_move")
                continue

            cur.execute(f"SELECT id FROM {table} WHERE game_id = %s", (game_id,))
            row_ids = [r[0] for r in cur.fetchall()]
            for row_id in row_ids:
                cur.execute("SAVEPOINT row_move")
                try:
                    cur.execute(
                        f"UPDATE {table} SET game_id = %s WHERE id = %s",
                        (canonical_game_id, row_id),
                    )
                    rows_migrated += 1
                except psycopg_errors.UniqueViolation:
                    cur.execute("ROLLBACK TO SAVEPOINT row_move")
                    cur.execute(f"DELETE FROM {table} WHERE id = %s", (row_id,))
                    rows_dropped_on_conflict += 1
                else:
                    cur.execute("RELEASE SAVEPOINT row_move")

        cur.execute("DELETE FROM games WHERE id = %s", (game_id,))
        games_deleted += 1

    cur.execute(
        "DELETE FROM teams WHERE id = ANY(%s) RETURNING abbr",
        (ghost_team_ids,),
    )
    deleted_teams = cur.fetchall()

    conn.commit()

    print(f"Ghost games merged into canonical games and deleted: {games_deleted}")
    print(f"Ghost games repointed in place (no canonical dup existed): {games_repointed_in_place}")
    print(f"Rows migrated to canonical game_id: {rows_migrated}")
    print(f"Rows dropped due to unique-constraint conflict at canonical game: {rows_dropped_on_conflict}")
    print(f"Ghost team rows deleted: {len(deleted_teams)}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
