#!/usr/bin/env python3
"""Verify Odds API training pull inventory + emit summary.json fragment."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "ops" / "odds-enterprise-training-pull" / "summary.json"
DB = "postgresql://ryankos:postgres@127.0.0.1:5432/kosedge"


def main() -> int:
    conn = psycopg.connect(DB)
    cur = conn.cursor()
    rem = cur.execute(
        """
        SELECT credits_remaining, credits_used, requested_at
        FROM odds_api_credit_ledger
        WHERE credits_remaining IS NOT NULL
        ORDER BY requested_at DESC LIMIT 1
        """
    ).fetchone()
    inv = {}
    for code, sport_key in [
        ("mlb", "baseball_mlb"),
        ("nfl", "americanfootball_nfl"),
        ("nba", "basketball_nba"),
        ("nhl", "icehockey_nhl"),
        ("wnba", "basketball_wnba"),
        ("cfb", "americanfootball_ncaaf"),
        ("ncaam", "basketball_ncaab"),
    ]:
        games = cur.execute(
            """
            SELECT COUNT(DISTINCT g.id)
            FROM odds_snapshots o
            JOIN games g ON g.id = o.game_id
            JOIN seasons s ON s.id = g.season_id
            JOIN leagues l ON l.id = s.league_id
            WHERE l.code = %s
            """,
            (code,),
        ).fetchone()[0]
        if code == "nfl":
            props = cur.execute(
                """
                SELECT COUNT(*), COUNT(DISTINCT external_game_id),
                       array_agg(DISTINCT market_key ORDER BY market_key)
                FROM nfl_player_prop_market_snapshots
                WHERE source = 'odds_api_historical'
                """
            ).fetchone()
        else:
            props = cur.execute(
                """
                SELECT COUNT(*), COUNT(DISTINCT external_game_id),
                       array_agg(DISTINCT market_key ORDER BY market_key)
                FROM player_prop_market_snapshots
                WHERE sport_key = %s
                """,
                (sport_key,),
            ).fetchone()
        inv[code] = {
            "mainline_games": int(games or 0),
            "prop_rows": int(props[0] or 0),
            "prop_events": int(props[1] or 0),
            "prop_markets": props[2],
        }
    ledger = cur.execute(
        """
        SELECT sport_key,
               COUNT(*) FILTER (WHERE source_key = 'enterprise-training-pull'),
               COALESCE(SUM(credits_last) FILTER (WHERE source_key = 'enterprise-training-pull'), 0)
        FROM odds_api_credit_ledger
        GROUP BY 1 ORDER BY 3 DESC
        """
    ).fetchall()
    payload = {
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "credits_remaining": rem[0] if rem else None,
        "credits_used_header": rem[1] if rem else None,
        "inventory": inv,
        "enterprise_ledger_by_sport": [
            {"sport_key": r[0], "requests": int(r[1]), "sum_credits_last": int(r[2])} for r in ledger
        ],
    }
    print(json.dumps(payload, indent=2, default=str))
    if OUT.exists():
        existing = json.loads(OUT.read_text())
        existing["verify"] = payload
        OUT.write_text(json.dumps(existing, indent=2, default=str))
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(payload, indent=2, default=str))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
