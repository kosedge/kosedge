#!/usr/bin/env python3
"""Upsert kickoff-safe NFL lake snaps into Postgres odds_snapshots.

Reads the parquet lake (run export_nfl_odds_lake.py first). Reconstructs
Odds-API-shaped events and reuses persist_mainline_odds. Does not pull API.

Usage:
  DATABASE_URL=postgresql+psycopg://... \\
    PYTHONPATH=services/model-service:. \\
    python scripts/nfl/ingest_nfl_odds_warehouse.py
"""

from __future__ import annotations

import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))
sys.path.insert(0, str(ROOT))

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge")

import psycopg  # noqa: E402

from scripts.odds.persist_mainline_odds import persist_odds_events  # noqa: E402
from src.services.cfb_warehouse.leakage import is_available_before_kickoff  # noqa: E402
from src.services.nfl_warehouse.odds_lake import load_odds_lake  # noqa: E402


def _dsn() -> str:
    raw = (os.environ.get("DATABASE_URL") or "").strip()
    return raw.replace("postgresql+psycopg://", "postgresql://", 1)


def _events_from_lake(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        kickoff = row.get("kickoff")
        captured = row.get("captured_at")
        if not is_available_before_kickoff(available_at=captured, kickoff=kickoff, game_date=row.get("game_date")):
            continue
        key = (row.get("event_id"), row.get("captured_at"), row.get("book"))
        grouped[key].append(row)

    events: List[Dict[str, Any]] = []
    for (event_id, captured, _book), snaps in grouped.items():
        if not event_id:
            continue
        first = snaps[0]
        bookmakers: Dict[str, Dict[str, Any]] = {}
        for snap in snaps:
            book = str(snap.get("book") or "draftkings")
            bm = bookmakers.setdefault(book, {"key": book, "markets": []})
            raw = str(snap.get("market_raw") or "")
            market_key = {"moneyline": "h2h", "spread": "spreads", "total": "totals"}.get(
                str(snap.get("market") or ""), raw or str(snap.get("market") or "")
            )
            home = first.get("home")
            away = first.get("away")
            if market_key == "h2h":
                outcomes = [
                    {"name": home, "price": snap.get("price_home")},
                    {"name": away, "price": snap.get("price_away")},
                ]
            elif market_key == "spreads":
                sh = snap.get("spread_home")
                outcomes = [
                    {"name": home, "price": snap.get("price_home"), "point": sh},
                    {"name": away, "price": snap.get("price_away"), "point": -float(sh) if sh is not None else None},
                ]
            elif market_key == "totals":
                outcomes = [
                    {"name": "Over", "price": snap.get("over_price"), "point": snap.get("total_points")},
                    {"name": "Under", "price": snap.get("under_price"), "point": snap.get("total_points")},
                ]
            else:
                continue
            bm["markets"].append({"key": market_key, "last_update": captured, "outcomes": outcomes})
        events.append(
            {
                "id": str(event_id),
                "sport_key": "americanfootball_nfl",
                "commence_time": first.get("kickoff"),
                "home_team": first.get("home"),
                "away_team": first.get("away"),
                "bookmakers": list(bookmakers.values()),
            }
        )
    return events


def main() -> int:
    rows = load_odds_lake(prefer_hd=True)
    if not rows:
        print("empty lake — run scripts/nfl/export_nfl_odds_lake.py first")
        return 1
    events = _events_from_lake(rows)
    print(f"legal events={len(events)} from lake_rows={len(rows)}")
    with psycopg.connect(_dsn()) as conn:
        stats = persist_odds_events(
            conn,
            sport_key="americanfootball_nfl",
            events=events,
            source_label="nfl-odds-warehouse-lake",
        )
        conn.commit()
    print(stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
