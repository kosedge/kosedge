"""Owned NFL Odds API lake — primary market source for training/grading.

Join key: (game_date, home_name, away_name). Close = last snapshot strictly
before kickoff. Open = first legal snapshot. Prefer DraftKings, then FanDuel.

nflverse ``spread_line`` is home-favored-positive. Odds API ``spread_home``
is negative when home is favored. Callers that need nflverse convention
must flip: ``home_favored = -spread_home``.
"""

from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from src.services.cfb_warehouse.leakage import is_available_before_kickoff
from src.services.nfl_warehouse.paths import ensure_lake_dir, sqlite_path

PREFER_BOOKS = ("draftkings", "fanduel")
MAINLINE_MARKETS = frozenset({"h2h", "spreads", "totals"})
MARKET_TO_CODE = {"h2h": "moneyline", "spreads": "spread", "totals": "total"}
PATH_KINDS = ("open", "pre7d", "pre3d", "pre1d", "close", "mid")
PERIOD_MARKETS = frozenset(
    {
        "h2h_h1",
        "spreads_h1",
        "totals_h1",
        "team_totals",
        "alternate_spreads",
        "alternate_totals",
    }
)

NFL_FULL_NAME_TO_ABBR = {
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
    "Washington Football Team": "WAS",
    "Washington Redskins": "WAS",
    "Oakland Raiders": "LV",
    "San Diego Chargers": "LAC",
    "St. Louis Rams": "LA",
}

ABBR_ALIASES = {
    "LAR": "LA",
    "JAC": "JAX",
    "WSH": "WAS",
    "WFT": "WAS",
    "OAK": "LV",
    "SD": "LAC",
    "STL": "LA",
    "AZ": "ARI",
}
_KNOWN_ABBRS = frozenset(NFL_FULL_NAME_TO_ABBR.values()) | frozenset(ABBR_ALIASES.values())


def normalize_name(name: str) -> str:
    text = (name or "").casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def team_abbr(name: str) -> str:
    raw = (name or "").strip()
    mapped = NFL_FULL_NAME_TO_ABBR.get(raw) or NFL_FULL_NAME_TO_ABBR.get(name or "", "")
    if mapped:
        return mapped
    token = raw.upper()
    if token in ABBR_ALIASES:
        return ABBR_ALIASES[token]
    if token in _KNOWN_ABBRS:
        return token
    return ""


def join_key(game_date: Any, home: str, away: str) -> Tuple[str, str, str]:
    return (str(game_date)[:10], normalize_name(home), normalize_name(away))


def _book_rank(book: str) -> int:
    b = (book or "").lower()
    try:
        return PREFER_BOOKS.index(b)
    except ValueError:
        return len(PREFER_BOOKS)


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


def _as_season(commence_time: Any) -> Optional[int]:
    text = str(commence_time or "")
    if len(text) < 10:
        return None
    try:
        year = int(text[:4])
        month = int(text[5:7])
    except ValueError:
        return None
    if month <= 2:
        return year - 1
    return year


def reduce_open_close(
    snaps: Sequence[Mapping[str, Any]],
    *,
    kickoff: Any = None,
    game_date: Any = None,
) -> Dict[str, Any]:
    """Open = first legal snap; close = last snap strictly before kickoff."""
    legal: List[Mapping[str, Any]] = []
    for row in snaps:
        captured = row.get("captured_at") or row.get("snapshot_ts")
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
        market = str(row.get("market") or MARKET_TO_CODE.get(str(row.get("market_raw") or ""), ""))
        book = str(row.get("book") or "")
        by_market_book[(market, book)].append(row)

    def _ts(row: Mapping[str, Any]) -> str:
        return str(row.get("captured_at") or row.get("snapshot_ts") or "")

    def pick(market: str) -> Tuple[Optional[Mapping[str, Any]], Optional[Mapping[str, Any]], str]:
        market_rows = [
            row
            for (mkt, _book), rows in by_market_book.items()
            if mkt == market
            for row in rows
        ]
        if not market_rows:
            return None, None, ""
        labeled_close = [r for r in market_rows if str(r.get("snapshot_kind") or "") == "close"]
        labeled_open = [r for r in market_rows if str(r.get("snapshot_kind") or "") == "open"]
        prefer_close = [
            r for r in labeled_close if str(r.get("book") or "").lower() in PREFER_BOOKS
        ]
        prefer_open = [
            r for r in labeled_open if str(r.get("book") or "").lower() in PREFER_BOOKS
        ]
        first_book_rows = sorted(
            [(book, rows) for (mkt, book), rows in by_market_book.items() if mkt == market],
            key=lambda item: _book_rank(item[0]),
        )[0][1]
        ordered_book = sorted(first_book_rows, key=_ts)
        if prefer_open:
            open_row = sorted(prefer_open, key=lambda r: (_book_rank(str(r.get("book") or "")), _ts(r)))[0]
        elif labeled_open:
            open_row = sorted(labeled_open, key=_ts)[0]
        else:
            open_row = ordered_book[0]
        # True close = last labeled DK/FD snap. Do not let an unlabeled path
        # mid from DK beat a later labeled FD/jsonl close.
        if prefer_close:
            close_row = sorted(prefer_close, key=_ts)[-1]
        elif labeled_close:
            close_row = sorted(labeled_close, key=_ts)[-1]
        else:
            close_row = ordered_book[-1]
        book = str((close_row or open_row or {}).get("book") or "")
        return open_row, close_row, book

    open_sp, close_sp, sp_book = pick("spread")
    open_tot, close_tot, tot_book = pick("total")
    open_ml, close_ml, ml_book = pick("moneyline")

    close_at = None
    for row in (close_sp, close_tot, close_ml):
        if row and (row.get("captured_at") or row.get("snapshot_ts")):
            close_at = str(row.get("captured_at") or row.get("snapshot_ts"))
            break
    open_at = None
    for row in (open_sp, open_tot, open_ml):
        if row and (row.get("captured_at") or row.get("snapshot_ts")):
            open_at = str(row.get("captured_at") or row.get("snapshot_ts"))
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


def reduce_path(
    snaps: Sequence[Mapping[str, Any]],
    *,
    kickoff: Any = None,
    game_date: Any = None,
) -> Dict[str, Any]:
    """Labeled 7d/3d/1d/open/close plus steam (close − earlier)."""
    base = reduce_open_close(snaps, kickoff=kickoff, game_date=game_date)
    if not base:
        return {}

    legal: List[Mapping[str, Any]] = []
    for row in snaps:
        captured = row.get("captured_at") or row.get("snapshot_ts")
        if kickoff or game_date:
            if not is_available_before_kickoff(
                available_at=captured,
                kickoff=kickoff,
                game_date=game_date,
            ):
                continue
        legal.append(row)

    by_kind: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in legal:
        kind = str(row.get("snapshot_kind") or "")
        if kind in PATH_KINDS:
            by_kind[kind].append(row)

    def _point(kind: str, market: str, field: str) -> Optional[float]:
        rows = [
            r
            for r in by_kind.get(kind, [])
            if str(r.get("market") or "") == market
        ]
        if not rows:
            return None
        rows.sort(key=lambda r: (_book_rank(str(r.get("book") or "")), str(r.get("captured_at") or "")))
        return _f(rows[0], field)

    out = dict(base)
    for kind in ("pre7d", "pre3d", "pre1d"):
        out[f"{kind}_spread_home"] = _point(kind, "spread", "spread_home")
        out[f"{kind}_total"] = _point(kind, "total", "total_points")
        out[f"{kind}_ml_home"] = _point(kind, "moneyline", "price_home")

    close_sp = out.get("close_spread_home")
    close_tot = out.get("close_total")
    for kind in ("pre7d", "pre3d", "pre1d"):
        earlier_sp = out.get(f"{kind}_spread_home")
        earlier_tot = out.get(f"{kind}_total")
        out[f"steam_spread_{kind}"] = (
            float(close_sp) - float(earlier_sp)
            if close_sp is not None and earlier_sp is not None
            else None
        )
        out[f"steam_total_{kind}"] = (
            float(close_tot) - float(earlier_tot)
            if close_tot is not None and earlier_tot is not None
            else None
        )
    return out


def _adjacent_dates(day: str) -> List[str]:
    try:
        dt = datetime.strptime(day, "%Y-%m-%d")
    except ValueError:
        return []
    return [
        (dt - timedelta(days=1)).strftime("%Y-%m-%d"),
        (dt + timedelta(days=1)).strftime("%Y-%m-%d"),
    ]


def overlay_closing_lines(
    games: Sequence[Mapping[str, Any]],
    lake_snaps: Sequence[Mapping[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    by_key: Dict[Tuple[str, str, str], List[Mapping[str, Any]]] = defaultdict(list)
    by_abbr: Dict[Tuple[str, str, str], List[Mapping[str, Any]]] = defaultdict(list)
    for row in lake_snaps:
        by_key[
            join_key(row.get("game_date"), str(row.get("home") or ""), str(row.get("away") or ""))
        ].append(row)
        day = str(row.get("game_date") or "")[:10]
        ha = team_abbr(str(row.get("home") or "")) or str(row.get("home_abbr") or "")
        aa = team_abbr(str(row.get("away") or "")) or str(row.get("away_abbr") or "")
        if day and ha and aa:
            by_abbr[(day, ha, aa)].append(row)

    merged: List[Dict[str, Any]] = []
    matched = 0
    matched_with_close = 0
    for game in games:
        key = join_key(
            game.get("game_date") or game.get("kickoff"),
            str(game.get("home_name") or game.get("home_team") or ""),
            str(game.get("away_name") or game.get("away_team") or ""),
        )
        snaps = by_key.get(key) or []
        if not snaps and key[0]:
            for alt in _adjacent_dates(key[0]):
                alt_key = (alt, key[1], key[2])
                if alt_key in by_key:
                    snaps = by_key[alt_key]
                    break
        if not snaps:
            ha = team_abbr(str(game.get("home_name") or game.get("home_team") or ""))
            aa = team_abbr(str(game.get("away_name") or game.get("away_team") or ""))
            if key[0] and ha and aa:
                snaps = by_abbr.get((key[0], ha, aa)) or []
                if not snaps:
                    for alt in _adjacent_dates(key[0]):
                        alt_key = (alt, ha, aa)
                        if alt_key in by_abbr:
                            snaps = by_abbr[alt_key]
                            break
        reduced = reduce_path(
            snaps,
            kickoff=game.get("kickoff") or game.get("commence_time"),
            game_date=game.get("game_date") or key[0],
        )
        row = dict(game)
        if reduced:
            matched += 1
            if reduced.get("close_spread_home") is not None:
                matched_with_close += 1
            row.update(reduced)
            if reduced.get("close_spread_home") is not None:
                row["owned_close_spread_home_favored"] = -float(reduced["close_spread_home"])
            if reduced.get("close_total") is not None:
                row["owned_close_total"] = float(reduced["close_total"])
        merged.append(row)

    stats = {
        "lake_snaps": len(lake_snaps),
        "games": len(games),
        "matched": matched,
        "matched_with_close_spread": matched_with_close,
        "unmatched": len(games) - matched,
        "primary": "odds_api_lake",
        "fill": "nflverse_spread_line_total_line",
        "leakage_rule": "strictly_before_kickoff",
    }
    return merged, stats


def _pivot_line_group(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Turn flattened outcome rows into lake snapshots (one per book/market)."""
    grouped: Dict[Tuple[Any, ...], List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        market = str(row.get("market") or "")
        if market not in MAINLINE_MARKETS:
            continue
        key = (
            row.get("event_id"),
            row.get("snapshot_kind"),
            row.get("snapshot_ts"),
            row.get("book"),
            market,
        )
        grouped[key].append(row)

    out: List[Dict[str, Any]] = []
    for (event_id, snap_kind, snap_ts, book, market), group in grouped.items():
        first = group[0]
        home = str(first.get("home_team") or "")
        away = str(first.get("away_team") or "")
        commence = first.get("commence_time")
        rec: Dict[str, Any] = {
            "event_id": event_id,
            "game_date": str(commence or "")[:10],
            "season": _as_season(commence),
            "home": home,
            "away": away,
            "home_abbr": team_abbr(home),
            "away_abbr": team_abbr(away),
            "market": MARKET_TO_CODE.get(market, market),
            "market_raw": market,
            "book": str(book or "").lower(),
            "snapshot_kind": snap_kind,
            "captured_at": snap_ts,
            "kickoff": commence,
            "source": "odds_gapfill_sqlite",
            "spread_home": None,
            "total_points": None,
            "price_home": None,
            "price_away": None,
            "over_price": None,
            "under_price": None,
        }
        by_outcome = {str(r.get("outcome") or ""): r for r in group}
        if market == "h2h":
            rec["price_home"] = _f(by_outcome.get(home), "price")
            rec["price_away"] = _f(by_outcome.get(away), "price")
        elif market == "spreads":
            rec["spread_home"] = _f(by_outcome.get(home), "point")
            rec["price_home"] = _f(by_outcome.get(home), "price")
            rec["price_away"] = _f(by_outcome.get(away), "price")
        elif market == "totals":
            over = by_outcome.get("Over")
            under = by_outcome.get("Under")
            rec["total_points"] = _f(over, "point") if over else _f(under, "point")
            rec["over_price"] = _f(over, "price")
            rec["under_price"] = _f(under, "price")
        out.append(rec)
    return out


def export_odds_lake_from_csv(
    csv_path: Path,
    *,
    prefer_hd: bool = True,
) -> Dict[str, Any]:
    """Build the parquet lake from a flattened lines.csv (much faster than SQLite)."""
    import csv as csvlib

    import pandas as pd

    out = ensure_lake_dir(prefer_hd=prefer_hd)
    if not csv_path.is_file():
        return {"status": "missing_csv", "path": str(csv_path), "rows": 0}

    kept: List[Dict[str, Any]] = []
    path_kinds = {"open", "close", "pre7d", "pre3d", "pre1d", "mid"}
    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csvlib.DictReader(fh)
        for row in reader:
            if str(row.get("market") or "") not in MAINLINE_MARKETS:
                continue
            if str(row.get("snapshot_kind") or "") not in path_kinds:
                continue
            kept.append(row)
    pivoted = _pivot_line_group(kept)
    if not pivoted:
        return {"status": "empty", "rows": 0, "dir": str(out)}
    df = pd.DataFrame(pivoted)
    by_season: Dict[str, int] = {}
    for season, part in df.groupby("season"):
        if season is None or (isinstance(season, float) and season != season):
            continue
        path = out / f"snapshots-{int(season)}.parquet"
        part.to_parquet(path, index=False)
        by_season[str(int(season))] = int(len(part))
    inventory = {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "source": str(csv_path),
        "rows": int(len(df)),
        "games": int(df.groupby(["event_id"]).ngroups) if "event_id" in df else 0,
        "by_season": by_season,
        "dir": str(out),
        "join_key": "(game_date, home_name, away_name)",
        "leakage_rule": "strictly_before_kickoff",
    }
    (out / "inventory.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    return inventory


def export_odds_lake(
    *,
    prefer_hd: bool = True,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Dump NFL mainlines from the HD SQLite warehouse onto season parquet."""
    import pandas as pd

    src = Path(db_path) if db_path else sqlite_path(prefer_hd=prefer_hd)
    out = ensure_lake_dir(prefer_hd=prefer_hd)
    if not src.is_file():
        return {"status": "missing_sqlite", "path": str(src), "rows": 0}

    conn = sqlite3.connect(f"file:{src}?mode=ro", uri=True, timeout=60)
    conn.row_factory = sqlite3.Row
    # Path + open/close only. Dense 6h grids are for residual checks, not the
    # blend gate — skipping them avoids a multi-hour full-table scan.
    raw = conn.execute(
        """
        SELECT sport_key, event_id, commence_time, home_team, away_team,
               snapshot_kind, snapshot_ts, book, market, outcome, price, point
        FROM lines
        WHERE sport_key = 'americanfootball_nfl'
          AND market IN ('h2h', 'spreads', 'totals')
          AND snapshot_kind IN ('open', 'close', 'pre7d', 'pre3d', 'pre1d', 'mid')
        """
    ).fetchall()
    conn.close()
    pivoted = _pivot_line_group([dict(r) for r in raw])
    frames: List[Any] = [pd.DataFrame(pivoted)] if pivoted else []
    by_season: Dict[str, int] = {}

    if not frames:
        return {"status": "empty", "rows": 0, "dir": str(out)}

    all_df = pd.concat(frames, ignore_index=True)
    for season, part in all_df.groupby("season"):
        if season is None or (isinstance(season, float) and season != season):
            continue
        path = out / f"snapshots-{int(season)}.parquet"
        part.to_parquet(path, index=False)
        by_season[str(int(season))] = int(len(part))

    inventory = {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "source": str(src),
        "rows": int(len(all_df)),
        "games": int(all_df.groupby(["event_id"]).ngroups) if "event_id" in all_df else 0,
        "by_season": by_season,
        "dir": str(out),
        "join_key": "(game_date, home_name, away_name)",
        "leakage_rule": "strictly_before_kickoff",
    }
    (out / "inventory.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    return inventory


def load_odds_lake(*, prefer_hd: bool = True) -> List[Dict[str, Any]]:
    import pandas as pd

    out = ensure_lake_dir(prefer_hd=prefer_hd)
    files = sorted(out.glob("snapshots-*.parquet"))
    if not files:
        return []
    frames = [pd.read_parquet(p) for p in files]
    return pd.concat(frames, ignore_index=True).to_dict(orient="records")


def iter_prop_lines(
    *,
    prefer_hd: bool = True,
    db_path: Optional[Path] = None,
    markets: Optional[Iterable[str]] = None,
) -> List[Dict[str, Any]]:
    """Read flattened NFL player-prop rows (close preferred) from SQLite."""
    src = Path(db_path) if db_path else sqlite_path(prefer_hd=prefer_hd)
    if not src.is_file():
        return []
    wanted = tuple(markets or ())
    conn = sqlite3.connect(f"file:{src}?mode=ro", uri=True, timeout=30)
    conn.row_factory = sqlite3.Row
    sql = """
        SELECT event_id, commence_time, home_team, away_team, snapshot_kind,
               snapshot_ts, book, market, outcome, price, point
        FROM lines
        WHERE sport_key = 'americanfootball_nfl'
          AND (
            market LIKE 'player_%'
            OR market LIKE 'batter_%'
            OR market IN (
              'player_pass_yds', 'player_rush_yds', 'player_reception_yds',
              'player_receptions', 'player_pass_tds', 'player_anytime_td'
            )
          )
    """
    params: List[Any] = []
    if wanted:
        sql += " AND market IN ({})".format(",".join("?" * len(wanted)))
        params.extend(wanted)
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    return rows
