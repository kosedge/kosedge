"""CFB game-odds open/close ingest — warehouse lake, not Railway Postgres.

Odds API sport key: ``americanfootball_ncaaf``. Game markets only
(spread / total / ML). No props. No KEI. ``used_in_spread`` stays false.

Unmatched events are logged, never forced onto a slate key.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from src.services.cfb_warehouse.identity import (
    ESPN_NAME_TO_CODE,
    canonical_code,
    known_engine_codes,
    resolve_team_code,
)
from src.services.cfb_warehouse.odds_lake import normalize_name, reduce_open_close
from src.services.cfb_warehouse.paths import live_odds_dir

SPORT_KEY = "americanfootball_ncaaf"
SOURCE = "the-odds-api"
MARKETS = "h2h,spreads,totals"
REGIONS = "us,us2"
MARKET_MAP = {"h2h": "moneyline", "spreads": "spread", "totals": "total"}
USED_IN_SPREAD = False
INGEST_ID = "cfb-open-ingest-v0.15.1-20260814"

# Odds API names that are not exact ESPN_NAME_TO_CODE keys. Unlisted names
# stay unmatched — do not invent peer substitutions.
ODDS_API_NAME_ALIASES: Dict[str, str] = {
    "miami fl": "MIA",
    "miami florida": "MIA",
    "miami (fl)": "MIA",
    "miami oh": "M-OH",
    "miami ohio": "M-OH",
    "miami (oh)": "M-OH",
    "southern california trojans": "USC",
    "southern california": "USC",
    "connecticut huskies": "CONN",
    "mississippi rebels": "MISS",
    "north carolina state wolfpack": "NCSU",
    "app state mountaineers": "APP",
    "appalachian st mountaineers": "APP",
    "central florida knights": "UCF",
    "southern methodist mustangs": "SMU",
    "brigham young cougars": "BYU",
    "pennsylvania state nittany lions": "PSU",
    "texas san antonio roadrunners": "UTSA",
    "texas el paso miners": "UTEP",
    "middle tennessee state blue raiders": "MTSU",
    "florida international golden panthers": "FIU",
    "sam houston state bearkats": "SHSU",
    "southern mississippi golden eagles": "USM",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def snapshot_key(row: Mapping[str, Any]) -> str:
    return "|".join(
        [
            str(row.get("pulled_at") or ""),
            str(row.get("book") or ""),
            str(row.get("odds_event_id") or ""),
            str(row.get("market") or ""),
        ]
    )


def resolve_odds_team_name(name: str) -> Optional[str]:
    """Map an Odds API team name → engine code. None if unknown / FCS."""
    raw = (name or "").strip()
    if not raw:
        return None
    known = known_engine_codes()
    direct = resolve_team_code(name=raw, known_codes=known)
    if direct and direct in known:
        return direct
    target = normalize_name(raw)
    if not target:
        return None
    alias = ODDS_API_NAME_ALIASES.get(target)
    if alias:
        return canonical_code(alias)
    for espn_name, code in ESPN_NAME_TO_CODE.items():
        if normalize_name(espn_name) == target:
            return canonical_code(code)
    return None


def flatten_event(event: Mapping[str, Any], *, pulled_at: str) -> List[Dict[str, Any]]:
    """Book × allowed market rows. Player-prop markets are dropped."""
    home = str(event.get("home_team") or "")
    away = str(event.get("away_team") or "")
    commence = str(event.get("commence_time") or "")
    eid = str(event.get("id") or event.get("odds_event_id") or "")
    rows: List[Dict[str, Any]] = []
    for book in event.get("bookmakers") or []:
        book_key = str(book.get("key") or "")
        for market in book.get("markets") or []:
            mapped = MARKET_MAP.get(str(market.get("key") or ""))
            if not mapped:
                continue
            outcomes = list(market.get("outcomes") or [])
            row: Dict[str, Any] = {
                "pulled_at": pulled_at,
                "odds_event_id": eid,
                "book": book_key,
                "market": mapped,
                "home_name": home,
                "away_name": away,
                "commence_time": commence,
                "captured_at": pulled_at,
                "game_date": commence[:10],
                "source": SOURCE,
                "sport_key": SPORT_KEY,
                "used_in_spread": USED_IN_SPREAD,
                "kei": False,
            }
            if mapped == "spread":
                home_o = next((o for o in outcomes if o.get("name") == home), None)
                away_o = next((o for o in outcomes if o.get("name") == away), None)
                if home_o and home_o.get("point") is not None:
                    row["spread_home"] = float(home_o["point"])
                    row["price_home"] = home_o.get("price")
                elif away_o and away_o.get("point") is not None:
                    row["spread_home"] = -float(away_o["point"])
                    row["price_away"] = away_o.get("price")
            elif mapped == "total":
                over = next((o for o in outcomes if str(o.get("name") or "").lower() == "over"), None)
                under = next((o for o in outcomes if str(o.get("name") or "").lower() == "under"), None)
                if over and over.get("point") is not None:
                    row["total_points"] = float(over["point"])
                    row["over_price"] = over.get("price")
                if under:
                    row["under_price"] = under.get("price")
            elif mapped == "moneyline":
                home_o = next((o for o in outcomes if o.get("name") == home), None)
                away_o = next((o for o in outcomes if o.get("name") == away), None)
                if home_o:
                    row["price_home"] = home_o.get("price")
                if away_o:
                    row["price_away"] = away_o.get("price")
            row["snapshot_key"] = snapshot_key(row)
            rows.append(row)
    return rows


def flatten_events(events: Sequence[Mapping[str, Any]], *, pulled_at: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for event in events:
        if not isinstance(event, Mapping):
            continue
        for row in flatten_event(event, pulled_at=pulled_at):
            key = str(row["snapshot_key"])
            if key in seen:
                continue
            seen.add(key)
            out.append(row)
    return out


def _kickoff_date(game: Any) -> str:
    kick = str(getattr(game, "kickoff", "") or "")
    return kick[:10]


def _dates_near(day: str) -> List[str]:
    if len(day) < 10:
        return []
    try:
        dt = datetime.strptime(day[:10], "%Y-%m-%d")
    except ValueError:
        return []
    return [
        (dt + timedelta(days=delta)).strftime("%Y-%m-%d")
        for delta in (0, -1, 1)
    ]


def match_slate_game(
    home_code: Optional[str],
    away_code: Optional[str],
    commence: str,
    slate_by_pair: Mapping[Tuple[str, str], Sequence[Any]],
) -> Tuple[Optional[Any], Optional[str]]:
    """Join to official slate. Unmatched stays unmatched — never forced."""
    if not home_code or not away_code:
        return None, "unresolved_team"
    cands = list(slate_by_pair.get((home_code, away_code)) or [])
    if not cands:
        return None, "no_slate_pair"
    if len(cands) == 1:
        return cands[0], None
    days = set(_dates_near(commence[:10]))
    dated = [g for g in cands if _kickoff_date(g) in days]
    if len(dated) == 1:
        return dated[0], None
    if len(dated) > 1:
        return None, "ambiguous_slate"
    return None, "ambiguous_slate"


def map_rows_to_slate(
    rows: Sequence[Mapping[str, Any]],
    slate_games: Sequence[Any],
) -> List[Dict[str, Any]]:
    by_pair: Dict[Tuple[str, str], List[Any]] = defaultdict(list)
    for game in slate_games:
        home = canonical_code(str(getattr(game, "home_team", "") or ""))
        away = canonical_code(str(getattr(game, "away_team", "") or ""))
        if home and away:
            by_pair[(home, away)].append(game)

    mapped: List[Dict[str, Any]] = []
    for raw in rows:
        row = dict(raw)
        home_code = resolve_odds_team_name(str(row.get("home_name") or ""))
        away_code = resolve_odds_team_name(str(row.get("away_name") or ""))
        row["home_team_id"] = home_code
        row["away_team_id"] = away_code
        game, reason = match_slate_game(
            home_code,
            away_code,
            str(row.get("commence_time") or row.get("game_date") or ""),
            by_pair,
        )
        if game is None:
            row["matched"] = False
            row["unmatched_reason"] = reason
            row["slate_game_id"] = None
            row["espn_game_id"] = None
            row["week"] = None
            row["season"] = 2026
        else:
            row["matched"] = True
            row["unmatched_reason"] = None
            row["slate_game_id"] = str(getattr(game, "game_id", "") or "")
            row["espn_game_id"] = str(
                getattr(game, "source_game_id", "") or getattr(game, "game_id", "") or ""
            )
            row["week"] = int(getattr(game, "week", 0) or 0)
            row["season"] = int(getattr(game, "season", 2026) or 2026)
            row["kickoff"] = str(getattr(game, "kickoff", "") or "")
        row["used_in_spread"] = USED_IN_SPREAD
        row["kei"] = False
        mapped.append(row)
    return mapped


def _parse_iso(raw: Any) -> Optional[datetime]:
    text = str(raw or "").replace("Z", "+00:00")
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def reduce_mapped_games(
    mapped: Sequence[Mapping[str, Any]],
    *,
    weeks: Optional[Sequence[int]] = None,
) -> List[Dict[str, Any]]:
    """Open = first snap; close = last snap strictly before kickoff."""
    by_game: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    meta: Dict[str, Mapping[str, Any]] = {}
    week_set = set(int(w) for w in weeks) if weeks is not None else None
    for row in mapped:
        if not row.get("matched"):
            continue
        gid = str(row.get("slate_game_id") or "")
        if not gid:
            continue
        week_val = row.get("week")
        if week_set is not None and (week_val is None or int(week_val) not in week_set):
            continue
        by_game[gid].append(row)
        meta[gid] = row

    now = datetime.now(timezone.utc)
    out: List[Dict[str, Any]] = []
    for gid, snaps in by_game.items():
        head = meta[gid]
        kickoff = head.get("kickoff") or head.get("commence_time")
        reduced = reduce_open_close(
            snaps,
            kickoff=kickoff,
            game_date=head.get("game_date"),
        )
        kick_dt = _parse_iso(kickoff)
        kicked = bool(kick_dt and kick_dt <= now)
        # A live upcoming snap is an open candidate, not a close.
        if not kicked:
            if reduced.get("open_spread_home") is None and reduced.get("close_spread_home") is not None:
                reduced["open_spread_home"] = reduced.get("close_spread_home")
            reduced["close_spread_home"] = None
            reduced["close_total"] = None
            reduced["close_ml_home"] = None
            reduced["close_ml_away"] = None
            reduced["close_captured_at"] = None
        row = {
            "game_id": gid,
            "slate_game_id": gid,
            "espn_game_id": head.get("espn_game_id"),
            "season": head.get("season") or 2026,
            "week": head.get("week"),
            "home_team_id": head.get("home_team_id"),
            "away_team_id": head.get("away_team_id"),
            "home_name": head.get("home_name"),
            "away_name": head.get("away_name"),
            "kickoff": kickoff,
            "game_date": head.get("game_date"),
            "used_in_spread": USED_IN_SPREAD,
            "kei": False,
            **reduced,
        }
        out.append(row)
    return out


def inventory_from_mapped(
    mapped: Sequence[Mapping[str, Any]],
    *,
    pulled_at: str,
    n_events: int,
    weeks: Optional[Sequence[int]] = None,
    attempt_status: str = "ok",
    note: str = "",
    extra: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    reduced = reduce_mapped_games(mapped, weeks=weeks)
    n_opens = sum(1 for r in reduced if r.get("open_spread_home") is not None)
    n_closes = sum(1 for r in reduced if r.get("close_spread_home") is not None)
    events: Dict[str, Dict[str, Any]] = {}
    for row in mapped:
        eid = str(row.get("odds_event_id") or "")
        events.setdefault(
            eid,
            {
                "matched": bool(row.get("matched")),
                "week": row.get("week"),
                "unmatched_reason": row.get("unmatched_reason"),
            },
        )
    n_matched = sum(1 for e in events.values() if e.get("matched"))
    n_unmatched = max(0, len(events) - n_matched)
    by_week: Dict[str, int] = defaultdict(int)
    by_book: Dict[str, int] = defaultdict(int)
    by_reason: Dict[str, int] = defaultdict(int)
    for row in mapped:
        book = str(row.get("book") or "")
        if book:
            by_book[book] += 1
        if not row.get("matched") and row.get("unmatched_reason"):
            by_reason[str(row["unmatched_reason"])] += 1
    for r in reduced:
        if r.get("week") is not None:
            by_week[str(int(r["week"]))] += 1
    match_rate = round(n_matched / len(events), 4) if events else None
    payload: Dict[str, Any] = {
        "ingest_id": INGEST_ID,
        "as_of": pulled_at,
        "source": SOURCE,
        "sources": [SOURCE],
        "sport_key": SPORT_KEY,
        "markets": MARKETS,
        "n_events": int(n_events),
        "n_snapshot_rows": len(mapped),
        "n_matched_events": n_matched,
        "n_unmatched_events": n_unmatched,
        "match_rate": match_rate,
        "n_opens": n_opens,
        "n_closes": n_closes,
        "n_current": n_opens,
        "by_week": dict(sorted(by_week.items(), key=lambda kv: int(kv[0]))),
        "by_book": dict(sorted(by_book.items())),
        "unmatched_reasons": dict(sorted(by_reason.items())),
        "weeks_requested": list(weeks) if weeks is not None else None,
        "status": "empty" if n_events == 0 else attempt_status,
        "note": note
        or (
            "Honest empty — Odds API returned 0 events."
            if n_events == 0
            else "Live game-market snapshot. Upcoming lines count as opens, not closes."
        ),
        "used_in_spread": USED_IN_SPREAD,
        "kei": False,
        "blend": False,
        "storage": "warehouse_odds_lake_live",
        "not": ["railway_postgres_dump", "kei", "used_in_spread"],
    }
    if extra:
        payload.update(dict(extra))
    return payload


def live_dir(*, prefer_hd: bool = True, root: Optional[Path] = None) -> Path:
    if root is not None:
        return Path(root)
    return live_odds_dir(prefer_hd=prefer_hd)


def write_attempt(
    inventory: Mapping[str, Any],
    *,
    prefer_hd: bool = True,
    root: Optional[Path] = None,
    events: Optional[Sequence[Mapping[str, Any]]] = None,
    mapped: Optional[Sequence[Mapping[str, Any]]] = None,
) -> Dict[str, Any]:
    """Idempotent snapshot write. Empty attempts are recorded."""
    out = live_dir(prefer_hd=prefer_hd, root=root)
    snaps_dir = out / "snapshots"
    mapped_dir = out / "mapped"
    snaps_dir.mkdir(parents=True, exist_ok=True)
    mapped_dir.mkdir(parents=True, exist_ok=True)

    pulled_at = str(inventory.get("as_of") or _now_iso())
    stamp = pulled_at.replace(":", "").replace("+00:00", "Z")
    snap_path = snaps_dir / f"{stamp}.json"
    mapped_path = mapped_dir / f"{stamp}.jsonl"
    inv_path = out / "inventory.json"
    attempts_path = out / "attempts.jsonl"

    if snap_path.is_file() and mapped_path.is_file() and inv_path.is_file():
        existing = json.loads(inv_path.read_text(encoding="utf-8"))
        if existing.get("as_of") == pulled_at:
            return {"status": "idempotent", "dir": str(out), "inventory": existing}

    if events is not None:
        snap_path.write_text(
            json.dumps(list(events), indent=2, default=str) + "\n",
            encoding="utf-8",
        )
    if mapped is not None:
        with mapped_path.open("w", encoding="utf-8") as fh:
            for row in mapped:
                fh.write(json.dumps(row, default=str) + "\n")

    body = dict(inventory)
    body["dir"] = str(out)
    body["snapshot_path"] = str(snap_path) if events is not None else None
    body["mapped_path"] = str(mapped_path) if mapped is not None else None
    inv_path.write_text(json.dumps(body, indent=2, default=str) + "\n", encoding="utf-8")
    with attempts_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(body, default=str) + "\n")
    return {"status": body.get("status") or "ok", "dir": str(out), "inventory": body}


def load_mapped(*, prefer_hd: bool = True, root: Optional[Path] = None) -> List[Dict[str, Any]]:
    mapped_dir = live_dir(prefer_hd=prefer_hd, root=root) / "mapped"
    if not mapped_dir.is_dir():
        return []
    rows: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for path in sorted(mapped_dir.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            key = str(row.get("snapshot_key") or snapshot_key(row))
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)
    return rows


def latest_inventory(*, prefer_hd: bool = True, root: Optional[Path] = None) -> Dict[str, Any]:
    path = live_dir(prefer_hd=prefer_hd, root=root) / "inventory.json"
    if not path.is_file():
        return {
            "n_opens": 0,
            "n_closes": 0,
            "as_of": None,
            "sources": [SOURCE],
            "sport_key": SPORT_KEY,
            "status": "no_attempt",
            "used_in_spread": USED_IN_SPREAD,
            "kei": False,
        }
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "n_opens": 0,
            "n_closes": 0,
            "status": "unreadable",
            "used_in_spread": USED_IN_SPREAD,
            "kei": False,
        }
    raw.setdefault("used_in_spread", USED_IN_SPREAD)
    raw.setdefault("kei", False)
    return raw


def ingest_events(
    events: Sequence[Mapping[str, Any]],
    slate_games: Sequence[Any],
    *,
    pulled_at: Optional[str] = None,
    weeks: Optional[Sequence[int]] = None,
    prefer_hd: bool = True,
    root: Optional[Path] = None,
    note: str = "",
) -> Dict[str, Any]:
    """Map + write one pull. Empty ``events`` is a recorded attempt."""
    ts = pulled_at or _now_iso()
    flat = flatten_events(events, pulled_at=ts)
    mapped = map_rows_to_slate(flat, slate_games)
    inventory = inventory_from_mapped(
        mapped,
        pulled_at=ts,
        n_events=len(events),
        weeks=weeks,
        attempt_status="ok" if events else "empty",
        note=note,
    )
    written = write_attempt(
        inventory,
        prefer_hd=prefer_hd,
        root=root,
        events=events,
        mapped=mapped,
    )
    return {
        **written,
        "n_mapped_rows": len(mapped),
        "used_in_spread": USED_IN_SPREAD,
        "kei": False,
    }


def fetch_ncaaf_odds(*, pulled_at: Optional[str] = None) -> Dict[str, Any]:
    """Live Odds API pull. Secrets via existing ODDS_API_KEY env only."""
    from src.services.odds_api import fetch_odds_with_metadata

    ts = pulled_at or _now_iso()
    meta = fetch_odds_with_metadata(
        endpoint=f"sports/{SPORT_KEY}/odds",
        params={
            "regions": REGIONS,
            "markets": MARKETS,
            "oddsFormat": "american",
            "dateFormat": "iso",
        },
    )
    payload = meta.get("payload")
    events = payload if isinstance(payload, list) else []
    return {
        "pulled_at": ts,
        "events": events,
        "source": meta.get("source") or SOURCE,
        "x_requests_remaining": meta.get("x_requests_remaining"),
        "x_requests_used": meta.get("x_requests_used"),
        "used_in_spread": USED_IN_SPREAD,
        "kei": False,
    }


def load_official_slate_games(season: int = 2026) -> List[Any]:
    from src.services.cfb_season_engine.official_schedule import (
        games_from_blob,
        load_official_schedule_blob,
    )

    return games_from_blob(load_official_schedule_blob(season), season=season)
