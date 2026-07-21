"""Backfill team/opponent on historical prop snapshots (no API credits).

Uses metadata queried_home/away + week roster baselines with the same
position-aware name keys as production prop joins.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import psycopg

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_player_identity import (  # noqa: E402
    prop_market_position_compatible,
    prop_market_position_rank,
    prop_player_match_keys,
)

DATABASE_URL = "postgresql://ryankos:postgres@127.0.0.1:5432/kosedge"


def main() -> None:
    conn = psycopg.connect(DATABASE_URL, autocommit=False)
    try:
        snaps = conn.execute(
            """
            SELECT id, season, week, player_name, market_key, team,
                   metadata->>'queried_home_team' AS home,
                   metadata->>'queried_away_team' AS away
            FROM nfl_player_prop_market_snapshots
            WHERE season IS NOT NULL AND week IS NOT NULL
              AND (team IS NULL OR team = '' OR opponent IS NULL OR opponent = '')
            """
        ).fetchall()
        print(f"[load] {len(snaps)} snapshots needing team/opponent")

        weeks: Set[Tuple[int, int]] = {(int(r[1]), int(r[2])) for r in snaps}
        roster_by_week: Dict[Tuple[int, int], List[Tuple[str, str, str, Set[str]]]] = {}
        for season, week in sorted(weeks):
            rows = conn.execute(
                """
                SELECT team, position, player_name
                FROM nfl_player_projection_baselines
                WHERE season = %s AND week = %s
                """,
                (season, week),
            ).fetchall()
            packed = []
            for team, pos, name in rows:
                keys = set(prop_player_match_keys(player_uid=None, player_name=str(name or "")))
                packed.append((str(team or ""), str(pos or ""), str(name or ""), keys))
            roster_by_week[(season, week)] = packed
            print(f"[roster] {season} W{week}: {len(packed)} players")

        updated = 0
        ambiguous = 0
        unresolved = 0
        for sid, season, week, player_name, market_key, cur_team, home, away in snaps:
            home_u = (home or "").strip().upper() or None
            away_u = (away or "").strip().upper() or None
            m_keys = set(prop_player_match_keys(player_uid=None, player_name=str(player_name or "")))
            roster = roster_by_week.get((int(season), int(week)), [])
            candidates = []
            for team, pos, name, b_keys in roster:
                if not (m_keys & b_keys):
                    continue
                if home_u and away_u and team not in {home_u, away_u}:
                    continue
                if not prop_market_position_compatible(str(market_key), pos):
                    continue
                candidates.append((team, pos, name))
            resolved_team: Optional[str] = None
            if len(candidates) == 1:
                resolved_team = candidates[0][0]
            elif len(candidates) > 1:
                candidates.sort(key=lambda c: prop_market_position_rank(str(market_key), c[1]))
                best = prop_market_position_rank(str(market_key), candidates[0][1])
                top = [c for c in candidates if prop_market_position_rank(str(market_key), c[1]) == best]
                teams = {c[0] for c in top}
                if len(teams) == 1:
                    resolved_team = top[0][0]
                else:
                    ambiguous += 1
            else:
                unresolved += 1

            opponent = None
            if resolved_team and home_u and away_u:
                if resolved_team == home_u:
                    opponent = away_u
                elif resolved_team == away_u:
                    opponent = home_u

            if resolved_team is None and not opponent:
                continue
            conn.execute(
                """
                UPDATE nfl_player_prop_market_snapshots
                SET team = COALESCE(NULLIF(team, ''), %s),
                    opponent = COALESCE(NULLIF(opponent, ''), %s)
                WHERE id = %s
                """,
                (resolved_team, opponent, sid),
            )
            updated += 1

        conn.commit()
        print(f"[done] updated={updated} ambiguous={ambiguous} unresolved={unresolved}")
        row = conn.execute(
            """
            SELECT COUNT(*) FILTER (WHERE team IS NOT NULL AND team <> '') with_team,
                   COUNT(*) total
            FROM nfl_player_prop_market_snapshots WHERE season = 2025
            """
        ).fetchone()
        print(f"[2025] with_team={row[0]} / {row[1]}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
