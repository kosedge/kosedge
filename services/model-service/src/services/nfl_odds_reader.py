"""Smallest reusable local NFL odds reader + game/cutoff join (2020–2023).

Read-only. Does not ingest, write, or call paid Odds. Reuses the later
warehouse identity maps without depending on modules that are absent
from restore-working-ui. Timestamps must carry an explicit offset or an
explicit source-timezone contract; naive values are refused, not coerced
to UTC.

Season bound is hard: commence-derived season in {2020, 2021, 2022, 2023}.
Quotes after 2024-03-01 (2024 regular season and later) are refused.
"""

from __future__ import annotations

import csv
import json
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, tzinfo, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

PERMITTED_SEASONS = frozenset({2020, 2021, 2022, 2023})
SEASON_WINDOW_START = "2020-03-01"
SEASON_WINDOW_END = "2024-03-01"  # exclusive; keeps 2023 Super Bowl, drops 2024 REG

HD_ROOT = Path("/Volumes/KosEdgeData")
HD_SQLITE = HD_ROOT / "clean" / "odds" / "gapfill" / "odds_gapfill.sqlite"
HD_JSONL_DIR = HD_ROOT / "clean" / "odds" / "nfl"
HD_OC_CSV = HD_ROOT / "clean" / "odds" / "americanfootball_nfl" / "open_close" / "lines.csv"
HD_LAKE = HD_ROOT / "clean" / "odds" / "nfl" / "lake"
HD_RAW_HIST = HD_ROOT / "raw" / "odds" / "americanfootball_nfl" / "historical"
HD_NFLVERSE = HD_ROOT / "nflverse"

NFL_SPORT_KEY = "americanfootball_nfl"

# Same maps as services/model-service/src/services/nfl_warehouse/odds_lake.py
# on later branches. Copied so this module is usable on restore-working-ui.
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

# Store-canonical 2-letter codes. "LA" means Rams in Odds API / nflverse.
# City-only tokens below are still rejected as ambiguous.
_CANONICAL_ABBRS = frozenset(NFL_FULL_NAME_TO_ABBR.values()) | frozenset(ABBR_ALIASES.values())

AMBIGUOUS_CITY_TOKENS = frozenset(
    {
        "los angeles",
        "new york",
        "ny",
        "la rams or chargers",
    }
)

MAINLINE_RAW = frozenset({"h2h", "spreads", "totals"})
MAINLINE_CODE = frozenset({"moneyline", "spread", "total"})
MARKET_TO_CODE = {"h2h": "moneyline", "spreads": "spread", "totals": "total"}
CODE_TO_RAW = {"moneyline": "h2h", "spread": "spreads", "total": "totals"}
PERIOD_MARKETS = frozenset(
    {
        "h2h_h1",
        "spreads_h1",
        "totals_h1",
        "h2h_q1",
        "spreads_q1",
        "totals_q1",
        "team_totals",
        "alternate_spreads",
        "alternate_totals",
    }
)

MISSING_CUTOFF = "missing_cutoff"
UNRESOLVABLE_TIMESTAMP = "unresolvable_timestamp"
POST_CUTOFF = "post_cutoff"
AMBIGUOUS_IDENTITY = "ambiguous_identity"
UNKNOWN_TEAM = "unknown_team"
INCOMPATIBLE_MARKET = "incompatible_market"
MARKET_LINE_MISMATCH = "market_line_mismatch"
MISSING_VALUE = "missing_value"
DUPLICATE_CONFLICT = "duplicate_conflict"
SEASON_OUT_OF_BOUNDS = "season_out_of_bounds"
NO_GAME_MATCH = "no_game_match"
HD_NOT_MOUNTED = "hd_not_mounted"

SIGN_CONVENTION = "odds_api_spread_home_negative_when_home_favored"


@dataclass(frozen=True)
class TeamIdentity:
    raw: str
    abbr: str = ""
    status: str = "unknown"  # resolved | ambiguous | unknown


@dataclass
class EligibleQuote:
    event_id: str
    game_id: str
    season: int
    game_date: str
    home_abbr: str
    away_abbr: str
    book: str
    market: str
    market_class: str
    line: Optional[float]
    price: Optional[float]
    price_home: Optional[float]
    price_away: Optional[float]
    over_price: Optional[float]
    under_price: Optional[float]
    spread_home: Optional[float]
    total_points: Optional[float]
    captured_at: str
    snapshot_kind: str
    source: str
    provenance: str
    sign_convention: str = SIGN_CONVENTION

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExcludedRow:
    reason: str
    detail: str
    row: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {"reason": self.reason, "detail": self.detail, "row": self.row}


@dataclass
class JoinResult:
    eligible: List[EligibleQuote]
    excluded: List[ExcludedRow]
    reason_tallies: Dict[str, int]
    latest_per_book_market: List[EligibleQuote]
    identical_duplicate_n: int = 0

    def as_dict(self) -> Dict[str, Any]:
        return {
            "eligible_n": len(self.eligible),
            "excluded_n": len(self.excluded),
            "identical_duplicate_n": self.identical_duplicate_n,
            "reason_tallies": dict(self.reason_tallies),
            "eligible": [q.as_dict() for q in self.eligible],
            "excluded": [e.as_dict() for e in self.excluded],
            "latest_per_book_market_n": len(self.latest_per_book_market),
            "latest_per_book_market": [q.as_dict() for q in self.latest_per_book_market],
        }


def hd_mounted() -> bool:
    return HD_ROOT.is_dir() and (HD_ROOT / "clean").is_dir()


def require_hd() -> None:
    if not hd_mounted():
        raise RuntimeError(
            "BLOCKER: /Volumes/KosEdgeData is not mounted "
            "(expected clean/ and inventory/ on the KosEdgeData APFS volume)."
        )


def normalize_name(name: str) -> str:
    text = (name or "").casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _normalized_full_name_index() -> Dict[str, str]:
    index: Dict[str, str] = {}
    for full, abbr in NFL_FULL_NAME_TO_ABBR.items():
        index[normalize_name(full)] = abbr
    return index


_FULL_NAME_NORM = _normalized_full_name_index()


def resolve_team_identity(name: str) -> TeamIdentity:
    """Explicit event/team identity. Fail closed on city-only aliases."""
    raw = (name or "").strip()
    if not raw:
        return TeamIdentity(raw="", status="unknown")

    if raw in NFL_FULL_NAME_TO_ABBR:
        return TeamIdentity(raw=raw, abbr=NFL_FULL_NAME_TO_ABBR[raw], status="resolved")

    token = raw.upper()
    if token in ABBR_ALIASES:
        return TeamIdentity(raw=raw, abbr=ABBR_ALIASES[token], status="resolved")
    if token in _CANONICAL_ABBRS:
        return TeamIdentity(raw=raw, abbr=token, status="resolved")

    norm = normalize_name(raw)
    if not norm:
        return TeamIdentity(raw=raw, status="unknown")
    if norm in AMBIGUOUS_CITY_TOKENS:
        return TeamIdentity(raw=raw, status="ambiguous")

    hits = {
        abbr
        for full_norm, abbr in _FULL_NAME_NORM.items()
        if full_norm == norm or full_norm.endswith(" " + norm) or norm in full_norm.split()
    }
    # Token-in-name is too loose for "LA" / "New" — only accept exact norm or unique mascot.
    exact = _FULL_NAME_NORM.get(norm)
    if exact:
        return TeamIdentity(raw=raw, abbr=exact, status="resolved")

    mascot_hits = {
        abbr
        for full_norm, abbr in _FULL_NAME_NORM.items()
        if full_norm.split()[-1:] == [norm]
    }
    if len(mascot_hits) == 1:
        return TeamIdentity(raw=raw, abbr=next(iter(mascot_hits)), status="resolved")
    if len(mascot_hits) > 1 or len(hits) > 1:
        return TeamIdentity(raw=raw, status="ambiguous")
    return TeamIdentity(raw=raw, status="unknown")


def join_key(game_date: Any, home: str, away: str) -> Tuple[str, str, str]:
    home_id = resolve_team_identity(home)
    away_id = resolve_team_identity(away)
    return (
        str(game_date or "")[:10],
        home_id.abbr or normalize_name(home),
        away_id.abbr or normalize_name(away),
    )


def _resolve_source_timezone(source_timezone: Any) -> Optional[tzinfo]:
    """Return a tzinfo only when the caller named an explicit contract."""
    if source_timezone is None or source_timezone == "":
        return None
    if isinstance(source_timezone, tzinfo):
        return source_timezone
    text = str(source_timezone).strip()
    if not text:
        return None
    if text.upper() in {"UTC", "Z", "GMT", "ETC/UTC"}:
        return timezone.utc
    try:
        return ZoneInfo(text)
    except (ZoneInfoNotFoundError, ValueError):
        return None


def _first_source_timezone(*candidates: Any) -> Any:
    for candidate in candidates:
        if candidate not in (None, ""):
            return candidate
    return None


def normalize_quote_timestamp(value: Any, source_timezone: Any = None) -> Optional[datetime]:
    """Normalize to UTC when the source timezone is explicit. Refuse naive values.

    A timestamp is qualified when it carries an offset/Z, a tz-aware datetime,
    or the caller supplies an explicit ``source_timezone`` contract. Unqualified
    timestamps return None — they are never silently assigned UTC.
    """
    if value is None or value == "":
        return None
    tz_contract = _resolve_source_timezone(source_timezone)
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            if tz_contract is None:
                return None
            dt = dt.replace(tzinfo=tz_contract)
        return dt.astimezone(timezone.utc)
    if isinstance(value, date) and not isinstance(value, datetime):
        if tz_contract is None:
            return None
        return datetime(value.year, value.month, value.day, tzinfo=tz_contract).astimezone(timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z") or text.endswith("z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        if tz_contract is None:
            return None
        dt = dt.replace(tzinfo=tz_contract)
    return dt.astimezone(timezone.utc)


def timestamp_to_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def season_from_commence(commence: Any, *, source_timezone: Any = None) -> Optional[int]:
    dt = normalize_quote_timestamp(commence, source_timezone=source_timezone)
    if dt is None:
        text = str(commence or "")
        if len(text) < 10:
            return None
        try:
            year = int(text[:4])
            month = int(text[5:7])
        except ValueError:
            return None
        return year - 1 if month <= 2 else year
    return dt.year - 1 if dt.month <= 2 else dt.year


def in_permitted_season(commence: Any, *, seasons: Iterable[int] = PERMITTED_SEASONS) -> bool:
    season = season_from_commence(commence)
    return season in set(seasons)


def classify_market(market: Any) -> str:
    raw = str(market or "").strip().lower()
    if not raw:
        return "unknown"
    if raw in MAINLINE_RAW or raw in MAINLINE_CODE:
        return "mainline"
    if raw in PERIOD_MARKETS or raw.endswith("_h1") or raw.endswith("_q1"):
        return "period"
    if raw.startswith("player_") or raw.startswith("batter_"):
        return "prop"
    return "unknown"


def canonical_market(market: Any) -> str:
    raw = str(market or "").strip().lower()
    return MARKET_TO_CODE.get(raw, raw)


def _as_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def market_line_fields(market: str, row: Mapping[str, Any]) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """Return (line, price, mismatch_reason)."""
    code = canonical_market(market)
    if code == "spread":
        line = _as_float(row.get("spread_home") if row.get("spread_home") not in (None, "") else row.get("point"))
        price = _as_float(row.get("price_home") if row.get("price_home") not in (None, "") else row.get("price"))
        if line is None:
            return None, price, MARKET_LINE_MISMATCH
        return line, price, None
    if code == "total":
        line = _as_float(row.get("total_points") if row.get("total_points") not in (None, "") else row.get("point"))
        price = _as_float(row.get("over_price") if row.get("over_price") not in (None, "") else row.get("price"))
        if line is None:
            return None, price, MARKET_LINE_MISMATCH
        return line, price, None
    if code == "moneyline":
        price = _as_float(row.get("price_home") if row.get("price_home") not in (None, "") else row.get("price"))
        point = _as_float(row.get("point"))
        if point is not None:
            return None, price, MARKET_LINE_MISMATCH
        if price is None and _as_float(row.get("price_away")) is None:
            return None, None, MARKET_LINE_MISMATCH
        return None, price, None
    return None, _as_float(row.get("price")), INCOMPATIBLE_MARKET


def line_for_side(spread_home: Any, side: str) -> Optional[float]:
    """Home keeps Odds API sign; away is an explicit flip. Never a silent substitute."""
    value = _as_float(spread_home)
    if value is None:
        return None
    token = (side or "").strip().lower()
    if token == "home":
        return value
    if token == "away":
        return -value
    raise ValueError(f"side must be 'home' or 'away', got {side!r}")


def jsonl_path_for_season(season: int) -> Path:
    if season not in PERMITTED_SEASONS:
        raise ValueError(f"refusing season {season}; permitted {sorted(PERMITTED_SEASONS)}")
    matches = sorted(HD_JSONL_DIR.glob(f"snapshots-{season}-*.jsonl"))
    if matches:
        return matches[0]
    return HD_JSONL_DIR / f"snapshots-{season}.jsonl"


def iter_jsonl_quotes(
    *,
    seasons: Iterable[int] = PERMITTED_SEASONS,
    path_for_season=jsonl_path_for_season,
) -> Iterator[Dict[str, Any]]:
    """Read only the 2020–2023 clean JSONL files. Never opens 2024–26 snapshots."""
    for season in sorted(set(seasons)):
        if season not in PERMITTED_SEASONS:
            continue
        path = path_for_season(season)
        if not path.is_file():
            continue
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                row.setdefault("season", season)
                row.setdefault("source", str(path))
                row.setdefault("provenance", f"clean_jsonl:{path.name}")
                row.setdefault("snapshot_kind", "enterprise_snapshot")
                yield row


def iter_sqlite_quotes(
    *,
    seasons: Iterable[int] = PERMITTED_SEASONS,
    db_path: Optional[Path] = None,
    mainline_only: bool = False,
) -> Iterator[Dict[str, Any]]:
    """RO scan of gapfill SQLite with a hard commence-time window (2020–2023)."""
    src = Path(db_path) if db_path else HD_SQLITE
    if not src.is_file():
        return
    wanted = set(seasons) & PERMITTED_SEASONS
    conn = sqlite3.connect(f"file:{src}?mode=ro", uri=True, timeout=60)
    conn.row_factory = sqlite3.Row
    sql = """
        SELECT sport_key, event_id, commence_time, home_team, away_team,
               snapshot_kind, snapshot_ts, book, market, outcome, price, point
        FROM lines
        WHERE sport_key = ?
          AND commence_time >= ?
          AND commence_time < ?
    """
    params: List[Any] = [NFL_SPORT_KEY, SEASON_WINDOW_START, SEASON_WINDOW_END]
    if mainline_only:
        sql += " AND market IN ('h2h', 'spreads', 'totals')"
    try:
        for raw in conn.execute(sql, params):
            row = dict(raw)
            season = season_from_commence(row.get("commence_time"))
            if season not in wanted:
                continue
            row["season"] = season
            row["game_date"] = str(row.get("commence_time") or "")[:10]
            row["home"] = row.get("home_team")
            row["away"] = row.get("away_team")
            row["captured_at"] = row.get("snapshot_ts")
            row["source"] = str(src)
            row["provenance"] = "odds_gapfill_sqlite"
            yield row
    finally:
        conn.close()


def iter_open_close_csv_quotes(
    *,
    seasons: Iterable[int] = PERMITTED_SEASONS,
    csv_path: Optional[Path] = None,
) -> Iterator[Dict[str, Any]]:
    src = Path(csv_path) if csv_path else HD_OC_CSV
    if not src.is_file():
        return
    wanted = set(seasons) & PERMITTED_SEASONS
    with src.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            commence = row.get("commence_time")
            if not in_permitted_season(commence, seasons=wanted):
                continue
            if str(row.get("sport_key") or "") not in ("", NFL_SPORT_KEY):
                continue
            season = season_from_commence(commence)
            row["season"] = season
            row["game_date"] = str(commence or "")[:10]
            row["home"] = row.get("home_team")
            row["away"] = row.get("away_team")
            row["captured_at"] = row.get("snapshot_ts")
            row["source"] = str(src)
            row["provenance"] = "open_close_csv"
            yield row


def load_nflverse_games(*, seasons: Iterable[int] = PERMITTED_SEASONS) -> List[Dict[str, Any]]:
    """Distinct games from on-disk 2020–2023 PBP CSVs. Does not download."""
    games: Dict[str, Dict[str, Any]] = {}
    for season in sorted(set(seasons) & PERMITTED_SEASONS):
        path = HD_NFLVERSE / f"play_by_play_{season}.csv"
        if not path.is_file():
            continue
        with path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                game_id = str(row.get("game_id") or "")
                if not game_id or game_id in games:
                    continue
                home = resolve_team_identity(str(row.get("home_team") or ""))
                away = resolve_team_identity(str(row.get("away_team") or ""))
                games[game_id] = {
                    "game_id": game_id,
                    "season": int(row.get("season") or season),
                    "week": row.get("week"),
                    "season_type": row.get("season_type"),
                    "game_date": str(row.get("game_date") or "")[:10],
                    "home_team": home.abbr or row.get("home_team"),
                    "away_team": away.abbr or row.get("away_team"),
                    "kickoff": None,  # PBP start_time has no timezone — do not invent
                    "source": str(path),
                }
    return list(games.values())


def games_from_quotes(quotes: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Build explicit game identities from quote commence/event fields only."""
    by_id: Dict[str, Dict[str, Any]] = {}
    for row in quotes:
        home = resolve_team_identity(str(row.get("home") or row.get("home_team") or ""))
        away = resolve_team_identity(str(row.get("away") or row.get("away_team") or ""))
        if home.status != "resolved" or away.status != "resolved":
            continue
        event_id = str(row.get("event_id") or "")
        game_date = str(row.get("game_date") or row.get("commence_time") or "")[:10]
        key = event_id or f"{game_date}|{home.abbr}|{away.abbr}"
        if key in by_id:
            continue
        kickoff = row.get("kickoff") or row.get("commence_time")
        by_id[key] = {
            "game_id": str(row.get("game_id") or key),
            "event_id": event_id,
            "season": row.get("season") or season_from_commence(kickoff or game_date),
            "game_date": game_date,
            "home_team": home.abbr,
            "away_team": away.abbr,
            "kickoff": kickoff,
            "source": row.get("source"),
        }
    return list(by_id.values())


def _index_games(games: Sequence[Mapping[str, Any]]) -> Tuple[
    Dict[str, List[Dict[str, Any]]],
    Dict[Tuple[str, str, str], List[Dict[str, Any]]],
]:
    by_event: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_key: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    for game in games:
        row = dict(game)
        event_id = str(row.get("event_id") or "")
        if event_id:
            by_event[event_id].append(row)
        home = resolve_team_identity(str(row.get("home_team") or row.get("home") or row.get("home_name") or ""))
        away = resolve_team_identity(str(row.get("away_team") or row.get("away") or row.get("away_name") or ""))
        day = str(row.get("game_date") or row.get("kickoff") or "")[:10]
        if home.status == "resolved" and away.status == "resolved" and day:
            by_key[(day, home.abbr, away.abbr)].append(row)
    return by_event, by_key


def _match_game(
    row: Mapping[str, Any],
    by_event: Mapping[str, List[Dict[str, Any]]],
    by_key: Mapping[Tuple[str, str, str], List[Dict[str, Any]]],
) -> Tuple[Optional[Dict[str, Any]], Optional[str], str]:
    event_id = str(row.get("event_id") or "")
    if event_id and event_id in by_event:
        hits = by_event[event_id]
        if len(hits) > 1:
            return None, AMBIGUOUS_IDENTITY, f"event_id {event_id} matches {len(hits)} games"
        return hits[0], None, ""

    home = resolve_team_identity(str(row.get("home") or row.get("home_team") or ""))
    away = resolve_team_identity(str(row.get("away") or row.get("away_team") or ""))
    if home.status == "ambiguous" or away.status == "ambiguous":
        return None, AMBIGUOUS_IDENTITY, f"home={home.raw!r} away={away.raw!r}"
    if home.status != "resolved" or away.status != "resolved":
        return None, UNKNOWN_TEAM, f"home={home.raw!r}->{home.status} away={away.raw!r}->{away.status}"
    day = str(row.get("game_date") or row.get("commence_time") or "")[:10]
    hits = list(by_key.get((day, home.abbr, away.abbr), []))
    if not hits:
        return None, NO_GAME_MATCH, f"{day} {home.abbr} vs {away.abbr}"
    if len(hits) > 1:
        return None, AMBIGUOUS_IDENTITY, f"{day} {home.abbr} vs {away.abbr} matches {len(hits)} games"
    return hits[0], None, ""


def _identity_token(row: Mapping[str, Any]) -> Tuple[str, str, str, str]:
    home = resolve_team_identity(str(row.get("home") or row.get("home_team") or ""))
    away = resolve_team_identity(str(row.get("away") or row.get("away_team") or ""))
    return (
        str(row.get("event_id") or ""),
        str(row.get("game_date") or row.get("commence_time") or "")[:10],
        home.abbr or normalize_name(str(row.get("home") or row.get("home_team") or "")),
        away.abbr or normalize_name(str(row.get("away") or row.get("away_team") or "")),
    )


def _quote_fingerprint(row: Mapping[str, Any]) -> Tuple[Any, ...]:
    return _identity_token(row) + (
        str(row.get("book") or "").lower(),
        canonical_market(row.get("market")),
        str(row.get("captured_at") or row.get("snapshot_ts") or ""),
        str(row.get("outcome") or ""),
        row.get("point") if row.get("point") not in (None, "") else row.get("spread_home") or row.get("total_points"),
        row.get("price") if row.get("price") not in (None, "") else row.get("price_home"),
    )


def _conflict_key(row: Mapping[str, Any]) -> Tuple[Any, ...]:
    return _identity_token(row) + (
        str(row.get("book") or "").lower(),
        canonical_market(row.get("market")),
        str(row.get("captured_at") or row.get("snapshot_ts") or ""),
        str(row.get("outcome") or ""),
    )


def join_quotes_at_cutoff(
    quotes: Sequence[Mapping[str, Any]],
    games: Sequence[Mapping[str, Any]],
    forecast_cutoff: Any,
    *,
    requested_markets: Optional[Iterable[str]] = None,
    per_game_cutoff_key: str = "forecast_cutoff",
    source_timezone: Any = None,
) -> JoinResult:
    """Select quotes with source timestamp ≤ an explicit cutoff. Never invent a later close.

    ``forecast_cutoff`` is required. A per-game cutoff on the game row
    (``forecast_cutoff`` or ``kickoff`` when the caller set it as the cutoff)
    overrides the global value for that game. Missing cutoff rejects the row.
    Naive timestamps are refused unless ``source_timezone`` (function argument
    or ``source_timezone`` on the quote/game row) names an explicit contract.
    """
    excluded: List[ExcludedRow] = []
    eligible: List[EligibleQuote] = []
    identical_duplicate_n = 0

    wanted_markets = None
    if requested_markets is not None:
        wanted_markets = {canonical_market(m) for m in requested_markets} | {
            str(m).strip().lower() for m in requested_markets
        }

    by_event, by_key = _index_games(games)

    seen_fp: set[Tuple[Any, ...]] = set()
    conflict_values: Dict[Tuple[Any, ...], set[Tuple[Any, ...]]] = defaultdict(set)
    raw_rows = list(quotes)
    for row in raw_rows:
        conflict_values[_conflict_key(row)].add(_quote_fingerprint(row))
    conflict_keys = {key for key, values in conflict_values.items() if len(values) > 1}

    for row in raw_rows:
        game, ident_reason, ident_detail = _match_game(row, by_event, by_key)

        cutoff_raw = forecast_cutoff
        if game is not None and game.get(per_game_cutoff_key) not in (None, ""):
            cutoff_raw = game.get(per_game_cutoff_key)
        if forecast_cutoff in (None, "") and (
            game is None or game.get(per_game_cutoff_key) in (None, "")
        ):
            excluded.append(ExcludedRow(MISSING_CUTOFF, "forecast_cutoff is required", dict(row)))
            continue
        tz_contract = _first_source_timezone(
            row.get("source_timezone"),
            None if game is None else game.get("source_timezone"),
            source_timezone,
        )
        cutoff_dt = normalize_quote_timestamp(cutoff_raw, source_timezone=tz_contract)
        if cutoff_dt is None:
            excluded.append(
                ExcludedRow(
                    UNRESOLVABLE_TIMESTAMP,
                    f"cutoff unparseable or missing timezone contract: {cutoff_raw!r}",
                    dict(row),
                )
            )
            continue

        if ident_reason:
            excluded.append(ExcludedRow(ident_reason, ident_detail, dict(row)))
            continue

        assert game is not None
        home = resolve_team_identity(str(game.get("home_team") or game.get("home") or ""))
        away = resolve_team_identity(str(game.get("away_team") or game.get("away") or ""))
        if home.status != "resolved" or away.status != "resolved":
            excluded.append(
                ExcludedRow(
                    AMBIGUOUS_IDENTITY if "ambiguous" in {home.status, away.status} else UNKNOWN_TEAM,
                    f"game home={home.raw!r} away={away.raw!r}",
                    dict(row),
                )
            )
            continue

        season = game.get("season") or season_from_commence(row.get("commence_time") or game.get("kickoff") or game.get("game_date"))
        try:
            season_i = int(season) if season is not None else None
        except (TypeError, ValueError):
            season_i = None
        if season_i not in PERMITTED_SEASONS:
            excluded.append(ExcludedRow(SEASON_OUT_OF_BOUNDS, f"season={season!r}", dict(row)))
            continue

        market = str(row.get("market") or "")
        market_class = classify_market(market)
        code = canonical_market(market)
        if wanted_markets is not None and code not in wanted_markets and market.lower() not in wanted_markets:
            excluded.append(ExcludedRow(INCOMPATIBLE_MARKET, f"market={market!r} class={market_class}", dict(row)))
            continue
        if wanted_markets is None and market_class != "mainline":
            excluded.append(ExcludedRow(INCOMPATIBLE_MARKET, f"market={market!r} class={market_class}", dict(row)))
            continue

        book = str(row.get("book") or "").strip().lower()
        if not book:
            excluded.append(ExcludedRow(MISSING_VALUE, "missing book", dict(row)))
            continue

        captured = normalize_quote_timestamp(
            row.get("captured_at") or row.get("snapshot_ts"),
            source_timezone=tz_contract,
        )
        if captured is None:
            excluded.append(
                ExcludedRow(
                    UNRESOLVABLE_TIMESTAMP,
                    f"captured_at={row.get('captured_at')!r} (unparseable or missing timezone contract)",
                    dict(row),
                )
            )
            continue
        if captured > cutoff_dt:
            excluded.append(
                ExcludedRow(
                    POST_CUTOFF,
                    f"{timestamp_to_iso(captured)} > {timestamp_to_iso(cutoff_dt)}",
                    dict(row),
                )
            )
            continue

        line, price, mismatch = market_line_fields(market, row)
        if mismatch:
            excluded.append(ExcludedRow(mismatch, f"market={market!r}", dict(row)))
            continue

        fp = _quote_fingerprint(row)
        if fp in seen_fp:
            identical_duplicate_n += 1
            continue
        if _conflict_key(row) in conflict_keys:
            excluded.append(ExcludedRow(DUPLICATE_CONFLICT, "same book/market/timestamp with conflicting line/price", dict(row)))
            continue
        seen_fp.add(fp)

        eligible.append(
            EligibleQuote(
                event_id=str(row.get("event_id") or game.get("event_id") or ""),
                game_id=str(game.get("game_id") or ""),
                season=season_i,
                game_date=str(game.get("game_date") or "")[:10],
                home_abbr=home.abbr,
                away_abbr=away.abbr,
                book=book,
                market=code,
                market_class=market_class,
                line=line,
                price=price,
                price_home=_as_float(row.get("price_home") or (row.get("price") if code == "moneyline" else None)),
                price_away=_as_float(row.get("price_away")),
                over_price=_as_float(row.get("over_price")),
                under_price=_as_float(row.get("under_price")),
                spread_home=_as_float(row.get("spread_home") if code == "spread" else None) or (line if code == "spread" else None),
                total_points=_as_float(row.get("total_points") if code == "total" else None) or (line if code == "total" else None),
                captured_at=timestamp_to_iso(captured),
                snapshot_kind=str(row.get("snapshot_kind") or ""),
                source=str(row.get("source") or ""),
                provenance=str(row.get("provenance") or row.get("source") or ""),
            )
        )

    latest_map: Dict[Tuple[str, str, str], EligibleQuote] = {}
    for quote in eligible:
        key = (quote.game_id or quote.event_id, quote.book, quote.market)
        prev = latest_map.get(key)
        if prev is None or quote.captured_at > prev.captured_at:
            latest_map[key] = quote

    tallies = Counter(item.reason for item in excluded)
    return JoinResult(
        eligible=eligible,
        excluded=excluded,
        reason_tallies=dict(tallies),
        latest_per_book_market=list(latest_map.values()),
        identical_duplicate_n=identical_duplicate_n,
    )
