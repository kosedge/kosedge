"""
Process odds JSON into open/close parquet per game per book.

Reads from (in order):
1. data/raw/odds/open/ and data/raw/odds/close/ — from fetch_historical_ncaab_odds.py
   (paired YYYY-MM-DD.json; open = 12 UTC, close = 22 UTC that day).
2. data/raw/odds/*.json — list of events or {"data": [...]} (fallback or extra).

Run from apps/web: python src/process_odds.py
"""
import json
import sys
from pathlib import Path
from typing import Optional

import polars as pl

_WEB = Path(__file__).resolve().parent.parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
from pipeline_paths import ODDS_OPEN, ODDS_CLOSE, RAW_ODDS, ODDS_PARQUET_PATH, ensure_dirs

ensure_dirs()


def _extract_spread(markets: list, home_team: str, away_team: str) -> Optional[float]:
    for m in markets or []:
        if m.get("key") != "spreads":
            continue
        for o in m.get("outcomes") or []:
            if o.get("name") == home_team and "point" in o:
                return float(o["point"])
            if o.get("name") == away_team and "point" in o:
                return -float(o["point"])  # away spread -> home = -away
    return None


def _extract_total(markets: list) -> Optional[float]:
    for m in markets or []:
        if m.get("key") != "totals":
            continue
        for o in m.get("outcomes") or []:
            if "point" in o:
                return float(o["point"])
        break
    return None


def load_events_from_file(fp: Path) -> list:
    with open(fp, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "data" in data:
        return data["data"]
    if isinstance(data, dict) and "events" in data:
        return data["events"]
    return []


def build_from_historical() -> Optional[pl.DataFrame]:
    """Build open/close from data/raw/odds/open and close/ (paired by date)."""
    if not ODDS_OPEN.exists() or not ODDS_CLOSE.exists():
        return None
    open_files = sorted(ODDS_OPEN.glob("*.json"))
    if not open_files:
        return None

    rows = []
    for open_fp in open_files:
        date_str = open_fp.stem
        close_fp = ODDS_CLOSE / f"{date_str}.json"
        if not close_fp.exists():
            continue
        open_events = load_events_from_file(open_fp)
        close_events = load_events_from_file(close_fp)
        close_by_id = {ev.get("id"): ev for ev in close_events if ev.get("id")}
        for ev_open in open_events:
            event_id = ev_open.get("id") or ""
            ev_close = close_by_id.get(event_id) if event_id else None
            home = ev_open.get("home_team") or ""
            away = ev_open.get("away_team") or ""
            commence = ev_open.get("commence_time") or ""
            bookmakers_open = {b.get("key"): b for b in (ev_open.get("bookmakers") or []) if b.get("key")}
            bookmakers_close = {b.get("key"): b for b in (ev_close.get("bookmakers") or []) if b.get("key")} if ev_close else {}
            for book_key in bookmakers_open:
                b_open = bookmakers_open[book_key]
                b_close = bookmakers_close.get(book_key)
                markets_o = b_open.get("markets") or []
                markets_c = (b_close.get("markets") or []) if b_close else []
                spread_o = _extract_spread(markets_o, home, away)
                total_o = _extract_total(markets_o)
                spread_c = _extract_spread(markets_c, home, away) if b_close else spread_o
                total_c = _extract_total(markets_c) if b_close else total_o
                rows.append({
                    "event_id": event_id,
                    "home_team": home,
                    "away_team": away,
                    "commence_time": commence,
                    "book": book_key,
                    "open_time": f"{date_str}T12:00:00Z",
                    "close_time": f"{date_str}T22:00:00Z",
                    "open_spread_home": spread_o,
                    "close_spread_home": spread_c,
                    "open_total": total_o,
                    "close_total": total_c,
                })
    if not rows:
        return None
    return pl.DataFrame(rows)


def main() -> None:
    open_close = build_from_historical()
    if open_close is not None:
        print(f"Using historical odds: {ODDS_OPEN} / {ODDS_CLOSE} -> {len(open_close)} rows")
    else:
        # Fallback: data/raw/odds/*.json (multiple snapshots -> first/last per event-book)
        odds_files = list(RAW_ODDS.glob("*.json"))
        if not odds_files:
            print(f"No odds data. Run scripts/fetch_historical_ncaab_odds.py (saves to data/raw/odds/open and close/) or add JSON to {RAW_ODDS}.")
            return
        rows = []
        for fp in odds_files:
            events = load_events_from_file(fp)
            for ev in events:
                event_id = ev.get("id") or ""
                home = ev.get("home_team") or ""
                away = ev.get("away_team") or ""
                commence = ev.get("commence_time") or ""
                for book in ev.get("bookmakers") or []:
                    key = book.get("key") or ""
                    last_update = book.get("last_update") or commence
                    markets = book.get("markets") or []
                    spread = _extract_spread(markets, home, away)
                    total = _extract_total(markets)
                    rows.append({
                        "event_id": event_id,
                        "home_team": home,
                        "away_team": away,
                        "commence_time": commence,
                        "source_file": fp.stem,
                        "book": key,
                        "update_time": last_update,
                        "spread_home": spread,
                        "total": total,
                    })
        if not rows:
            print("No event/bookmaker rows parsed. Check JSON shape.")
            return
        raw = pl.DataFrame(rows)
        open_close = raw.sort("update_time").group_by(["event_id", "home_team", "away_team", "commence_time", "book"]).agg([
            pl.col("update_time").min().alias("open_time"),
            pl.col("update_time").max().alias("close_time"),
            pl.col("spread_home").first().alias("open_spread_home"),
            pl.col("spread_home").last().alias("close_spread_home"),
            pl.col("total").first().alias("open_total"),
            pl.col("total").last().alias("close_total"),
        ])

    open_close.write_parquet(ODDS_PARQUET_PATH)
    print(f"Wrote {ODDS_PARQUET_PATH} with {len(open_close)} rows (game-book open/close).")


if __name__ == "__main__":
    main()
