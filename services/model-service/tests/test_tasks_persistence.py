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
          created_at TEXT,
          ingest_run_id TEXT
        )
        """,
    ]
    with engine.begin() as conn:
        for ddl in statements:
            conn.execute(text(ddl))


def _sample_odds_payload(*, last_update: str = "2026-04-10T00:40:00Z"):
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
                    "last_update": last_update,
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


def _patch_fetch(monkeypatch, payload_fn):
    def _fake_fetch_odds(endpoint, params):
        return payload_fn(endpoint, params)

    def _fake_fetch_odds_with_metadata(endpoint, params):
        return {
            "payload": _fake_fetch_odds(endpoint, params),
            "source": "test",
            "x_requests_remaining": "42",
            "x_requests_used": "7",
            "x_requests_last": "1",
        }

    monkeypatch.setattr(tasks, "fetch_odds", _fake_fetch_odds)
    monkeypatch.setattr(tasks, "fetch_odds_with_metadata", _fake_fetch_odds_with_metadata)


def test_pull_odds_snapshot_persists_rows(monkeypatch) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    _create_sqlite_schema(engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    monkeypatch.setattr(tasks, "SessionLocal", TestSession)

    def _payload(endpoint, params):
        if endpoint == "sports/basketball_ncaab/odds":
            return _sample_odds_payload()
        return []

    _patch_fetch(monkeypatch, _payload)

    first = tasks.pull_odds_snapshot()
    assert first["events_fetched"] == 1
    assert first["events_persisted"] == 1
    assert first["snapshots_inserted"] == 3
    assert first.get("snapshots_skipped_dup", 0) == 0
    assert first.get("run_id")
    assert "americanfootball_ncaaf" in first["sport_keys"]
    assert "basketball_ncaab" in first["sport_keys"]

    second = tasks.pull_odds_snapshot()
    assert second["events_fetched"] == 1
    assert second["events_persisted"] == 1
    # Same book vintage → skip-dup; do not double-insert.
    assert second["snapshots_inserted"] == 0
    assert second["snapshots_skipped_dup"] == 3
    assert second.get("run_id")
    assert second["run_id"] != first["run_id"]

    with engine.connect() as conn:
        games = conn.execute(text("SELECT COUNT(*) FROM games")).scalar_one()
        books = conn.execute(text("SELECT COUNT(*) FROM sportsbooks")).scalar_one()
        markets = conn.execute(text("SELECT COUNT(*) FROM markets")).scalar_one()
        snapshots = conn.execute(text("SELECT COUNT(*) FROM odds_snapshots")).scalar_one()
        sport_code = conn.execute(text("SELECT code FROM sports LIMIT 1")).scalar_one()
        captured_at = conn.execute(
            text("SELECT captured_at FROM odds_snapshots LIMIT 1")
        ).scalar_one()
        ledger_n = conn.execute(
            text("SELECT COUNT(*) FROM odds_api_credit_ledger")
        ).scalar_one()
        prod_live = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM odds_api_credit_ledger
                WHERE bucket = 'PROD_LIVE'
                  AND caller = 'celery.pull_odds_snapshot'
                """
            )
        ).scalar_one()
        ingest_ids = conn.execute(
            text(
                "SELECT DISTINCT ingest_run_id FROM odds_snapshots WHERE ingest_run_id IS NOT NULL"
            )
        ).fetchall()

    assert games == 1
    assert books == 1
    assert markets == 3
    assert snapshots == 3  # skip-dup keeps natural-key vintage unique
    assert sport_code == "ncaam"
    assert datetime.fromisoformat(captured_at).tzinfo is timezone.utc
    assert ledger_n >= 1
    assert prod_live >= 1
    assert len(ingest_ids) == 1
    assert ingest_ids[0][0] == first["run_id"]


def test_pull_odds_snapshot_meters_shared_run_id(monkeypatch) -> None:
    """Beat path meters every sport fetch to PROD_LIVE with one shared run_id."""
    engine = create_engine("sqlite+pysqlite:///:memory:")
    _create_sqlite_schema(engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    monkeypatch.setattr(tasks, "SessionLocal", TestSession)

    def _payload(endpoint, params):
        if endpoint == "sports/basketball_ncaab/odds":
            return _sample_odds_payload()
        return []

    _patch_fetch(monkeypatch, _payload)

    result = tasks.pull_odds_snapshot()
    run_id = result["run_id"]
    assert run_id

    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT bucket, caller, run_id, sport_key, status, markets, regions
                FROM odds_api_credit_ledger
                ORDER BY sport_key
                """
            )
        ).fetchall()

    assert len(rows) >= 1
    assert all(r[0] == "PROD_LIVE" for r in rows)
    assert all(r[1] == "celery.pull_odds_snapshot" for r in rows)
    assert all(r[2] == run_id for r in rows)
    # One ledger row per pulled sport (shared run_id across the invocation).
    assert len(rows) == len(result["sport_keys"])
    ncaab = [r for r in rows if r[3] == "basketball_ncaab"]
    assert len(ncaab) == 1
    assert ncaab[0][4] == "success"
    assert ncaab[0][5] == "h2h,spreads,totals"
    assert ncaab[0][6] == "us"


def test_persist_odds_events_skips_dup_keeps_new_vintage(monkeypatch) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    _create_sqlite_schema(engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSession()
    try:
        tasks._ensure_odds_api_request_tables(session)
        first = tasks._persist_odds_events(
            session,
            events=_sample_odds_payload(last_update="2026-04-10T00:40:00Z"),
            source_label="the-odds-api",
            ingest_run_id="run-a",
        )
        assert first["snapshots_inserted"] == 3
        assert first["snapshots_skipped_dup"] == 0
        same = tasks._persist_odds_events(
            session,
            events=_sample_odds_payload(last_update="2026-04-10T00:40:00Z"),
            source_label="the-odds-api",
            ingest_run_id="run-b",
        )
        assert same["snapshots_inserted"] == 0
        assert same["snapshots_skipped_dup"] == 3
        newer = tasks._persist_odds_events(
            session,
            events=_sample_odds_payload(last_update="2026-04-10T01:15:00Z"),
            source_label="the-odds-api",
            ingest_run_id="run-c",
        )
        assert newer["snapshots_inserted"] == 3
        assert newer["snapshots_skipped_dup"] == 0
        session.commit()
    finally:
        session.close()

    with engine.connect() as conn:
        snapshots = conn.execute(text("SELECT COUNT(*) FROM odds_snapshots")).scalar_one()
        vintages = conn.execute(
            text("SELECT COUNT(DISTINCT captured_at) FROM odds_snapshots")
        ).scalar_one()
    assert snapshots == 6
    assert vintages == 2


def test_pull_odds_snapshot_cfb_only_filter(monkeypatch) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    _create_sqlite_schema(engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    monkeypatch.setattr(tasks, "SessionLocal", TestSession)

    def _fake_fetch_odds_with_metadata(endpoint, params):
        payload = []
        if endpoint == "sports/americanfootball_ncaaf/odds":
            payload = [
                {
                    "id": "cfb-evt-1",
                    "sport_key": "americanfootball_ncaaf",
                    "commence_time": "2026-09-06T19:00:00Z",
                    "home_team": "Ohio State Buckeyes",
                    "away_team": "Ball State Cardinals",
                    "bookmakers": [
                        {
                            "key": "draftkings",
                            "last_update": "2026-09-05T12:00:00Z",
                            "markets": [
                                {
                                    "key": "h2h",
                                    "outcomes": [
                                        {
                                            "name": "Ohio State Buckeyes",
                                            "price": -5000,
                                        },
                                        {
                                            "name": "Ball State Cardinals",
                                            "price": 1800,
                                        },
                                    ],
                                },
                                {
                                    "key": "spreads",
                                    "outcomes": [
                                        {
                                            "name": "Ohio State Buckeyes",
                                            "point": -42.5,
                                            "price": -110,
                                        },
                                        {
                                            "name": "Ball State Cardinals",
                                            "point": 42.5,
                                            "price": -110,
                                        },
                                    ],
                                },
                                {
                                    "key": "totals",
                                    "outcomes": [
                                        {
                                            "name": "Over",
                                            "point": 55.5,
                                            "price": -108,
                                        },
                                        {
                                            "name": "Under",
                                            "point": 55.5,
                                            "price": -112,
                                        },
                                    ],
                                },
                            ],
                        }
                    ],
                }
            ]
        return {
            "payload": payload,
            "source": "test",
            "x_requests_remaining": "40",
            "x_requests_used": "1",
        }

    monkeypatch.setattr(
        tasks, "fetch_odds_with_metadata", _fake_fetch_odds_with_metadata
    )

    result = tasks.pull_odds_snapshot(sport_keys="americanfootball_ncaaf")
    assert result["sport_keys"] == ["americanfootball_ncaaf"]
    assert result["events_fetched"] == 1
    assert result["events_persisted"] == 1
    assert result["snapshots_inserted"] == 3
    assert result.get("run_id")

    with engine.connect() as conn:
        league = conn.execute(text("SELECT code FROM leagues LIMIT 1")).scalar_one()
        sport = conn.execute(text("SELECT code FROM sports LIMIT 1")).scalar_one()
        ledger = conn.execute(
            text(
                """
                SELECT bucket, caller, run_id FROM odds_api_credit_ledger
                WHERE sport_key = 'americanfootball_ncaaf'
                """
            )
        ).fetchone()
    assert league == "cfb"
    assert sport == "cfb"
    assert ledger is not None
    assert ledger[0] == "PROD_LIVE"
    assert ledger[1] == "celery.pull_odds_snapshot"
    assert ledger[2] == result["run_id"]
