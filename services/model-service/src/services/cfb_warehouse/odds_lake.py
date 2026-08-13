"""Owned CFB Odds API lake — primary market source; SDV/CFBD betting is fill.

Join key: (game_date, home_name, away_name). Odds API abbrs (GEBU, FLGA) are
not engine codes — names are the join. Close = last snapshot strictly before
kickoff. Open = first snapshot. Prefer DraftKings, then FanDuel.
"""

from __future__ import annotations

import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from src.services.cfb_warehouse.leakage import is_available_before_kickoff
from src.services.cfb_warehouse.paths import odds_lake_dir

PREFER_BOOKS = ("draftkings", "fanduel")
LOCAL_DSN = "postgresql://ryankos:postgres@127.0.0.1:5432/kosedge"

_EXPORT_SQL = """
SELECT
  g.game_date::text AS game_date,
  s.season_year AS season,
  ht.name AS home,
  at.name AS away,
  ht.abbr AS home_abbr,
  at.abbr AS away_abbr,
  m.code AS market,
  sb.code AS book,
  o.spread_home,
  o.total_points,
  o.price_home,
  o.price_away,
  o.over_price,
  o.under_price,
  o.captured_at,
  o.source
FROM odds_snapshots o
JOIN games g ON g.id = o.game_id
JOIN seasons s ON s.id = g.season_id
JOIN leagues l ON l.id = s.league_id
JOIN teams ht ON ht.id = g.home_team_id
JOIN teams at ON at.id = g.away_team_id
JOIN markets m ON m.id = o.market_id
JOIN sportsbooks sb ON sb.id = o.sportsbook_id
WHERE l.code = 'cfb'
ORDER BY g.game_date, o.captured_at
"""


def _dsn() -> str:
    raw = (os.environ.get("DATABASE_URL") or "").strip()
    if raw:
        return raw.replace("postgresql+psycopg://", "postgresql://", 1)
    return LOCAL_DSN


def normalize_name(name: str) -> str:
    text = (name or "").casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def join_key(game_date: Any, home: str, away: str) -> Tuple[str, str, str]:
    return (str(game_date)[:10], normalize_name(home), normalize_name(away))


def export_odds_lake(*, prefer_hd: bool = True) -> Dict[str, Any]:
    """Dump local/prod CFB odds_snapshots onto HD parquet (NFL-style lake)."""
    import pandas as pd
    import psycopg

    out = odds_lake_dir(prefer_hd=prefer_hd)
    out.mkdir(parents=True, exist_ok=True)
    with psycopg.connect(_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(_EXPORT_SQL)
            cols = [d.name for d in cur.description]
            rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=cols)
    if df.empty:
        return {"status": "empty", "rows": 0, "dir": str(out)}
    df["captured_at"] = pd.to_datetime(df["captured_at"], utc=True)
    by_season: Dict[str, int] = {}
    for season, part in df.groupby("season"):
        path = out / f"snapshots-{int(season)}.parquet"
        part.to_parquet(path, index=False)
        by_season[str(int(season))] = int(len(part))
    inventory = {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "source": "odds_snapshots postgres (the-odds-api-historical-enterprise)",
        "rows": int(len(df)),
        "games": int(df.groupby(["game_date", "home", "away"]).ngroups),
        "by_season": by_season,
        "dir": str(out),
        "join_key": "(game_date, home_name, away_name)",
    }
    (out / "inventory.json").write_text(
        __import__("json").dumps(inventory, indent=2) + "\n", encoding="utf-8"
    )
    return inventory


def load_odds_lake(*, prefer_hd: bool = True) -> List[Dict[str, Any]]:
    import pandas as pd

    out = odds_lake_dir(prefer_hd=prefer_hd)
    files = sorted(out.glob("snapshots-*.parquet"))
    if not files:
        return []
    frames = [pd.read_parquet(p) for p in files]
    return pd.concat(frames, ignore_index=True).to_dict(orient="records")


def _book_rank(book: str) -> int:
    b = (book or "").lower()
    try:
        return PREFER_BOOKS.index(b)
    except ValueError:
        return len(PREFER_BOOKS)


def reduce_open_close(
    snaps: Sequence[Mapping[str, Any]],
    *,
    kickoff: Any = None,
    game_date: Any = None,
) -> Dict[str, Any]:
    """Open = first snap; close = last snap strictly before kickoff.

    Post-kickoff snapshots are dropped (leakage). Prefer DK then FD.
    """
    legal: List[Mapping[str, Any]] = []
    for row in snaps:
        captured = row.get("captured_at")
        if kickoff or game_date:
            if not is_available_before_kickoff(
                available_at=captured,
                kickoff=kickoff,
                game_date=game_date,
            ):
                continue
        legal.append(row)
    if not legal:
        return {}

    by_market_book: Dict[Tuple[str, str], List[Mapping[str, Any]]] = defaultdict(list)
    for row in legal:
        market = str(row.get("market") or "")
        book = str(row.get("book") or "")
        by_market_book[(market, book)].append(row)

    def pick(market: str) -> Tuple[Optional[Mapping[str, Any]], Optional[Mapping[str, Any]], str]:
        candidates = [
            (book, rows)
            for (mkt, book), rows in by_market_book.items()
            if mkt == market
        ]
        candidates.sort(key=lambda item: _book_rank(item[0]))
        if not candidates:
            return None, None, ""
        book, rows = candidates[0]
        ordered = sorted(rows, key=lambda r: str(r.get("captured_at") or ""))
        return ordered[0], ordered[-1], book

    open_sp, close_sp, sp_book = pick("spread")
    open_tot, close_tot, tot_book = pick("total")
    open_ml, close_ml, ml_book = pick("moneyline")

    def _f(row: Optional[Mapping[str, Any]], key: str) -> Any:
        if not row:
            return None
        val = row.get(key)
        if val is None or val == "":
            return None
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    close_at = None
    for row in (close_sp, close_tot, close_ml):
        if row and row.get("captured_at"):
            close_at = str(row.get("captured_at"))
            break
    open_at = None
    for row in (open_sp, open_tot, open_ml):
        if row and row.get("captured_at"):
            open_at = str(row.get("captured_at"))
            break

    return {
        "open_spread_home": _f(open_sp, "spread_home"),
        "close_spread_home": _f(close_sp, "spread_home"),
        "open_total": _f(open_tot, "total_points"),
        "close_total": _f(close_tot, "total_points"),
        "open_ml_home": _f(open_ml, "price_home"),
        "close_ml_home": _f(close_ml, "price_home"),
        "close_ml_away": _f(close_ml, "price_away"),
        "book": sp_book or tot_book or ml_book,
        "source": "odds_api_lake",
        "line_fidelity": "book_timestamped",
        "open_captured_at": open_at,
        "close_captured_at": close_at,
        "available_at": close_at,
        "n_lake_snaps": len(legal),
    }


def overlay_closing_lines(
    games: Sequence[Mapping[str, Any]],
    closes: Sequence[Mapping[str, Any]],
    lake_snaps: Sequence[Mapping[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Lake primary; SDV/CFBD fill. Games without a lake match are kept (no silent year drop)."""
    by_key: Dict[Tuple[str, str, str], List[Mapping[str, Any]]] = defaultdict(list)
    for row in lake_snaps:
        by_key[join_key(row.get("game_date"), str(row.get("home") or ""), str(row.get("away") or ""))].append(row)

    close_by_id = {str(c.get("game_id")): dict(c) for c in closes}
    matched = 0
    matched_with_close = 0
    for game in games:
        gid = str(game.get("game_id") or "")
        key = join_key(
            game.get("game_date"),
            str(game.get("home_name") or ""),
            str(game.get("away_name") or ""),
        )
        snaps = by_key.get(key) or []
        if not snaps and game.get("game_date"):
            # UTC date vs US evening: try ±1 calendar day, unique name match only.
            day = str(game.get("game_date"))[:10]
            for alt in _adjacent_dates(day):
                alt_key = (alt, key[1], key[2])
                if alt_key in by_key:
                    snaps = by_key[alt_key]
                    break
        reduced = reduce_open_close(
            snaps,
            kickoff=game.get("kickoff"),
            game_date=game.get("game_date"),
        )
        base = close_by_id.get(gid) or {
            "game_id": gid,
            "season": game.get("season"),
            "week": game.get("week"),
            "home_team_id": game.get("home_team_id"),
            "away_team_id": game.get("away_team_id"),
        }
        if reduced:
            matched += 1
            if reduced.get("close_spread_home") is not None:
                matched_with_close += 1
            for field in (
                "open_spread_home",
                "close_spread_home",
                "open_total",
                "close_total",
                "open_ml_home",
                "close_ml_home",
                "close_ml_away",
                "book",
                "source",
                "line_fidelity",
                "open_captured_at",
                "close_captured_at",
                "available_at",
                "n_lake_snaps",
            ):
                val = reduced.get(field)
                if val is not None and val != "":
                    base[field] = val
        close_by_id[gid] = base

    merged = list(close_by_id.values())
    stats = {
        "lake_snaps": len(lake_snaps),
        "games": len(games),
        "matched": matched,
        "matched_with_close_spread": matched_with_close,
        "unmatched": len(games) - matched,
        "primary": "odds_api_lake",
        "fill": "sportsdataverse_espn_cfb_betting",
    }
    return merged, stats


def _adjacent_dates(day: str) -> List[str]:
    try:
        dt = datetime.strptime(day, "%Y-%m-%d")
    except ValueError:
        return []
    from datetime import timedelta

    return [
        (dt - timedelta(days=1)).strftime("%Y-%m-%d"),
        (dt + timedelta(days=1)).strftime("%Y-%m-%d"),
    ]
