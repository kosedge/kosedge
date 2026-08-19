"""Build kickoff-safe labeled open/close from the Aug-6 enterprise jsonl + nflverse.

Does not re-pull Odds API. Writes ``snapshots-trueclose-YYYY.parquet`` beside
the path lake so ``load_odds_lake`` picks them up.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from src.services.cfb_warehouse.leakage import is_available_before_kickoff
from src.services.nfl_warehouse.odds_lake import _as_season, team_abbr
from src.services.nfl_warehouse.paths import HD_ROOT, ensure_lake_dir

HD_JSONL_DIR = HD_ROOT / "clean" / "odds" / "nfl"
PREFER = ("draftkings", "fanduel")


def jsonl_paths() -> List[Path]:
    return sorted(HD_JSONL_DIR.glob("snapshots-*-20260806.jsonl"))


def _parse_ts(raw: Any) -> Optional[datetime]:
    text = str(raw or "").replace("Z", "+00:00")
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _book_rank(book: str) -> int:
    b = (book or "").lower()
    try:
        return PREFER.index(b)
    except ValueError:
        return len(PREFER)


def load_enterprise_jsonl(paths: Optional[Sequence[Path]] = None) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for path in paths or jsonl_paths():
        if not path.is_file():
            continue
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                raw = json.loads(line)
                home = team_abbr(str(raw.get("home") or ""))
                away = team_abbr(str(raw.get("away") or ""))
                if not home or not away:
                    continue
                rows.append(
                    {
                        "game_date": str(raw.get("game_date") or "")[:10],
                        "home": home,
                        "away": away,
                        "home_abbr": home,
                        "away_abbr": away,
                        "market": str(raw.get("market") or ""),
                        "book": str(raw.get("book") or "").lower(),
                        "spread_home": raw.get("spread_home"),
                        "total_points": raw.get("total_points"),
                        "price_home": raw.get("price_home"),
                        "price_away": raw.get("price_away"),
                        "over_price": raw.get("over_price"),
                        "under_price": raw.get("under_price"),
                        "captured_at": raw.get("captured_at"),
                        "source": str(raw.get("source") or "the-odds-api-historical-enterprise"),
                    }
                )
    return rows


def reduce_labeled_open_close(
    snaps: Sequence[Mapping[str, Any]],
    *,
    kickoff: Any,
    game_date: Any,
    season: Any,
    home: str,
    away: str,
) -> List[Dict[str, Any]]:
    legal = [
        row
        for row in snaps
        if is_available_before_kickoff(
            available_at=row.get("captured_at"), kickoff=kickoff, game_date=None
        )
        or (
            kickoff is None
            and is_available_before_kickoff(
                available_at=row.get("captured_at"), game_date=game_date
            )
        )
    ]
    if not legal:
        return []
    by_mkt: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in legal:
        mkt = str(row.get("market") or "")
        if mkt in {"spread", "total", "moneyline"}:
            by_mkt[mkt].append(row)

    out: List[Dict[str, Any]] = []
    event_id = f"{game_date}|{home}|{away}"
    for market, group in by_mkt.items():
        ranked = sorted(
            group,
            key=lambda r: (
                _book_rank(str(r.get("book") or "")),
                str(r.get("captured_at") or ""),
            ),
        )
        preferred = [r for r in ranked if str(r.get("book") or "") in PREFER] or ranked
        preferred_sorted = sorted(preferred, key=lambda r: str(r.get("captured_at") or ""))
        open_row = preferred_sorted[0]
        close_row = preferred_sorted[-1]
        for kind, src in (("open", open_row), ("close", close_row)):
            rec = {
                "event_id": event_id,
                "game_date": str(game_date)[:10],
                "season": season,
                "home": home,
                "away": away,
                "home_abbr": home,
                "away_abbr": away,
                "market": market,
                "market_raw": {"spread": "spreads", "total": "totals", "moneyline": "h2h"}.get(market, market),
                "book": src.get("book"),
                "snapshot_kind": kind,
                "captured_at": src.get("captured_at"),
                "kickoff": kickoff,
                "source": src.get("source") or "enterprise_jsonl",
                "spread_home": src.get("spread_home") if market == "spread" else None,
                "total_points": src.get("total_points") if market == "total" else None,
                "price_home": src.get("price_home") if market == "moneyline" else src.get("price_home"),
                "price_away": src.get("price_away"),
                "over_price": src.get("over_price"),
                "under_price": src.get("under_price"),
            }
            out.append(rec)
    return out


def nflverse_close_row(game: Mapping[str, Any]) -> List[Dict[str, Any]]:
    spread = game.get("spread_line")
    total = game.get("total_line")
    if spread is None and total is None:
        return []
    day = str(game.get("game_date") or "")[:10]
    home = team_abbr(str(game.get("home_team") or game.get("home") or ""))
    away = team_abbr(str(game.get("away_team") or game.get("away") or ""))
    kickoff = game.get("kickoff")
    # Conservative timestamp: 08:00 UTC on game date is before any NFL kickoff.
    captured = f"{day}T08:00:00+00:00" if day else None
    if kickoff and not is_available_before_kickoff(available_at=captured, kickoff=kickoff):
        kick_dt = _parse_ts(kickoff)
        if kick_dt is None:
            return []
        captured = (kick_dt - timedelta(minutes=30)).isoformat()
    base = {
        "event_id": f"{day}|{home}|{away}",
        "game_date": day,
        "season": game.get("season"),
        "home": home,
        "away": away,
        "home_abbr": home,
        "away_abbr": away,
        "book": "nflverse",
        "snapshot_kind": "close",
        "captured_at": captured,
        "kickoff": kickoff,
        "source": "nflverse",
        "spread_home": None,
        "total_points": None,
        "price_home": None,
        "price_away": None,
        "over_price": None,
        "under_price": None,
    }
    rows = []
    if spread is not None:
        rec = dict(base)
        rec["market"] = "spread"
        rec["market_raw"] = "spreads"
        rec["spread_home"] = -float(spread)  # nflverse home-favored-positive → Odds API
        rows.append(rec)
    if total is not None:
        rec = dict(base)
        rec["market"] = "total"
        rec["market_raw"] = "totals"
        rec["total_points"] = float(total)
        rows.append(rec)
    return rows


def export_true_close_lake(
    *,
    games: Sequence[Mapping[str, Any]],
    jsonl_rows: Optional[Sequence[Mapping[str, Any]]] = None,
    prefer_hd: bool = True,
) -> Dict[str, Any]:
    import pandas as pd

    out = ensure_lake_dir(prefer_hd=prefer_hd)
    snaps = list(jsonl_rows) if jsonl_rows is not None else load_enterprise_jsonl()
    by_game: Dict[Tuple[str, str, str], List[Mapping[str, Any]]] = defaultdict(list)
    for row in snaps:
        key = (str(row.get("game_date") or "")[:10], str(row.get("home") or ""), str(row.get("away") or ""))
        if key[0] and key[1] and key[2]:
            by_game[key].append(row)

    labeled: List[Dict[str, Any]] = []
    n_owned = 0
    n_nflverse = 0
    for game in games:
        day = str(game.get("game_date") or "")[:10]
        home = team_abbr(str(game.get("home_team") or game.get("home") or ""))
        away = team_abbr(str(game.get("away_team") or game.get("away") or ""))
        kickoff = game.get("kickoff")
        season = game.get("season") or _as_season(kickoff or day)
        group = by_game.get((day, home, away), [])
        if not group and day:
            for delta in (-1, 1):
                try:
                    alt = (datetime.strptime(day, "%Y-%m-%d") + timedelta(days=delta)).strftime("%Y-%m-%d")
                except ValueError:
                    continue
                if (alt, home, away) in by_game:
                    group = by_game[(alt, home, away)]
                    break
        owned = reduce_labeled_open_close(
            group, kickoff=kickoff, game_date=day, season=season, home=home, away=away
        )
        if owned:
            n_owned += 1
            labeled.extend(owned)
        nv = nflverse_close_row({**dict(game), "home": home, "away": away, "kickoff": kickoff})
        if nv:
            n_nflverse += 1
            labeled.extend(nv)

    if not labeled:
        return {"status": "empty", "rows": 0, "dir": str(out)}

    df = pd.DataFrame(labeled)
    by_season: Dict[str, int] = {}
    for season, part in df.groupby("season"):
        if season is None or (isinstance(season, float) and season != season):
            continue
        path = out / f"snapshots-trueclose-{int(season)}.parquet"
        part.to_parquet(path, index=False)
        by_season[str(int(season))] = int(len(part))
    inventory = {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "rows": int(len(df)),
        "games_owned_oc": n_owned,
        "games_nflverse_close": n_nflverse,
        "by_season": by_season,
        "dir": str(out),
        "label": "true_close_jsonl_plus_nflverse",
        "leakage_rule": "strictly_before_kickoff",
    }
    (out / "trueclose-inventory.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    return inventory
