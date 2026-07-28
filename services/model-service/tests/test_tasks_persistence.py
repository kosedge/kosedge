from __future__ import annotations

import os
from datetime import datetime, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src import tasks


def _create_sqlite_schema(engine) -> None:
    statements = [
        """
        CREATE TABLE sports (
          id TEXT PRIMARY KEY,
          code TEXT UNIQUE NOT NULL,
          name TEXT NOT NULL,
          created_at TEXT
        )
        """,
        """
        CREATE TABLE leagues (
          id TEXT PRIMARY KEY,
          sport_id TEXT NOT NULL,
          code TEXT NOT NULL,
          name TEXT NOT NULL,
          created_at TEXT,
          UNIQUE (sport_id, code)
        )
        """,
        """
        CREATE TABLE seasons (
          id TEXT PRIMARY KEY,
          league_id TEXT NOT NULL,
          season_year INTEGER NOT NULL,
          created_at TEXT,
          UNIQUE (league_id, season_year)
        )
        """,
        """
        CREATE TABLE teams (
          id TEXT PRIMARY KEY,
          league_id TEXT NOT NULL,
          external_id TEXT,
          abbr TEXT NOT NULL,
          name TEXT NOT NULL,
          market TEXT,
          created_at TEXT,
          UNIQUE (league_id, abbr)
        )
        """,
        """
        CREATE TABLE games (
          id TEXT PRIMARY KEY,
          season_id TEXT NOT NULL,
          external_id TEXT,
          game_date TEXT NOT NULL,
          start_time TEXT,
          status TEXT NOT NULL,
          home_team_id TEXT NOT NULL,
          away_team_id TEXT NOT NULL,
          created_at TEXT,
          UNIQUE (season_id, external_id)
        )
        """,
        """
        CREATE TABLE sportsbooks (
          id TEXT PRIMARY KEY,
          code TEXT UNIQUE NOT NULL,
          name TEXT NOT NULL,
          created_at TEXT
        )
        """,
        """
        CREATE TABLE markets (
          id TEXT PRIMARY KEY,
          code TEXT UNIQUE NOT NULL,
          created_at TEXT
        )
        """,
        """
        CREATE TABLE odds_snapshots (
          id TEXT PRIMARY KEY,
          game_id TEXT NOT NULL,
          sportsbook_id TEXT NOT NULL,
          market_id TEXT NOT NULL,
          price_home INTEGER,
          price_away INTEGER,
          spread_home REAL,
          spread_away REAL,
          total_points REAL,
          over_price INTEGER,
          under_price INTEGER,
          captured_at TEXT,
          source TEXT,
          created_at TEXT
        )
        """,
    ]
    with engine.begin() as conn:
        for ddl in statements:
            conn.execute(text(ddl))


def _sample_odds_payload():
    return [
        {
            "id": "evt_1",
            "sport_key": "basketball_ncaab",
            "commence_time": "2026-04-10T01:00:00Z",
            "home_team": "Duke Blue Devils",
            "away_team": "North Carolina Tar Heels",
            "bookmakers": [
                {
                    "key": "draftkings",
                    "last_update": "2026-04-10T00:40:00Z",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "Duke Blue Devils", "price": -120},
                                {"name": "North Carolina Tar Heels", "price": 105},
                            ],
                        },
                        {
                            "key": "spreads",
                            "outcomes": [
                                {"name": "Duke Blue Devils", "point": -2.5, "price": -110},
                                {"name": "North Carolina Tar Heels", "point": 2.5, "price": -110},
                            ],
                        },
                        {
                            "key": "totals",
                            "outcomes": [
                                {"name": "Over", "point": 149.5, "price": -108},
                                {"name": "Under", "point": 149.5, "price": -112},
                            ],
                        },
                    ],
                }
            ],
        }
    ]


def test_pull_odds_snapshot_persists_rows(monkeypatch) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    _create_sqlite_schema(engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    monkeypatch.setattr(tasks, "SessionLocal", TestSession)

    def _fake_fetch_odds(endpoint, params):
        if endpoint == "sports/basketball_ncaab/odds":
            return _sample_odds_payload()
        return []

    def _fake_fetch_odds_with_metadata(endpoint, params):
        return {
            "payload": _fake_fetch_odds(endpoint, params),
            "source": "test",
            "x_requests_remaining": "42",
            "x_requests_used": "7",
        }

    monkeypatch.setattr(tasks, "fetch_odds", _fake_fetch_odds)
    monkeypatch.setattr(tasks, "fetch_odds_with_metadata", _fake_fetch_odds_with_metadata)

    first = tasks.pull_odds_snapshot()
    assert first["events_fetched"] == 1
    assert first["events_persisted"] == 1
    assert first["snapshots_inserted"] == 3

    second = tasks.pull_odds_snapshot()
    assert second["events_fetched"] == 1
    assert second["events_persisted"] == 1
    assert second["snapshots_inserted"] == 3

    with engine.connect() as conn:
        games = conn.execute(text("SELECT COUNT(*) FROM games")).scalar_one()
        books = conn.execute(text("SELECT COUNT(*) FROM sportsbooks")).scalar_one()
        markets = conn.execute(text("SELECT COUNT(*) FROM markets")).scalar_one()
        snapshots = conn.execute(text("SELECT COUNT(*) FROM odds_snapshots")).scalar_one()
        sport_code = conn.execute(text("SELECT code FROM sports LIMIT 1")).scalar_one()
        captured_at = conn.execute(text("SELECT captured_at FROM odds_snapshots LIMIT 1")).scalar_one()

    assert games == 1
    assert books == 1
    assert markets == 3
    assert snapshots == 6  # append-only behavior across two pulls
    assert sport_code == "ncaam"
    assert datetime.fromisoformat(captured_at).tzinfo is timezone.utc
