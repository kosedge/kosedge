#!/usr/bin/env python3
"""Enterprise Odds API training pull (DK-primary, skip-if-owned, credit-capped).

High-end open+close mainlines + pro-sport player props for subscription-grade
training. Persists to odds_snapshots / nfl_player_prop_market_snapshots /
player_prop_market_snapshots + odds_api_request_cache / credit ledger.

Usage:
  /Users/ryankos/kosedge/.venv/bin/python3 scripts/odds/enterprise_training_pull.py
  /Users/ryankos/kosedge/.venv/bin/python3 scripts/odds/enterprise_training_pull.py --sports nfl,mlb
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import date, datetime, time as dt_time, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import psycopg
import requests
from psycopg.types.json import Json

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from persist_mainline_odds import persist_odds_events  # noqa: E402

OUT_DIR = ROOT / "data" / "ops" / "odds-enterprise-training-pull"
CHECKPOINT_PATH = OUT_DIR / "checkpoint.json"
SUMMARY_PATH = OUT_DIR / "summary.json"
LOG_PATH = OUT_DIR / "pull.log"

DATABASE_URL_PSYCOPG = "postgresql://ryankos:postgres@127.0.0.1:5432/kosedge"
DATABASE_URL_SQLA = "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge"
ENV_CANDIDATES = [
    ROOT / "apps" / "web" / ".env.local",
    ROOT / "apps" / "web" / ".env",
]
BASE_URL = "https://api.the-odds-api.com/v4"
BOOKMAKERS = "draftkings,fanduel"
MAINLINE_MARKETS = "h2h,spreads,totals"
REGIONS = "us"
SLEEP_S = 0.30  # ~3 req/s polite rate limit (band 2–5/s)
REQUEST_TIMEOUT = 60

# Session hard stops (user policy): leave ≥1.5M for live ops; cap this run ~3.5M
MAX_SESSION_SPEND = 3_500_000
MIN_REMAINING_FLOOR = 1_500_000
# Soft target band (base CLV plan ~2.2M)
TARGET_HIGH = 2_200_000
MAINLINES_EARLIEST = date(2020, 6, 6)
PROPS_EARLIEST = date(2023, 5, 3)

NFL_FULL_NAME_TO_ABBR: Dict[str, str] = {
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
}


@dataclass
class SportPlan:
    code: str
    sport_key: str
    include_props: bool
    prop_markets: List[str]
    prop_market_map: Dict[str, str]
    # Calendar windows for mainline densify (inclusive)
    mainline_ranges: List[Tuple[date, date]]
    # Optional skip ranges for mainlines already owned densely
    mainline_skip_ranges: List[Tuple[date, date]] = field(default_factory=list)
    # NFL schedule-driven seasons for mainlines/props
    nfl_seasons: List[int] = field(default_factory=list)
    props_open_close: bool = True  # high-end


PLANS: Dict[str, SportPlan] = {
    "nfl": SportPlan(
        code="nfl",
        sport_key="americanfootball_nfl",
        include_props=True,
        prop_markets=[
            "player_pass_yds",
            "player_rush_yds",
            "player_reception_yds",
            "player_receptions",
            "player_anytime_td",
        ],
        prop_market_map={
            "player_pass_yds": "pass_yds",
            "player_rush_yds": "rush_yds",
            "player_reception_yds": "rec_yds",
            "player_receptions": "receptions",
            "player_anytime_td": "anytime_td",
        },
        mainline_ranges=[],
        # Mainlines from Odds API earliest; props from 2023 onward
        nfl_seasons=[2020, 2021, 2022, 2023, 2024, 2025],
        props_open_close=True,
    ),
    "mlb": SportPlan(
        code="mlb",
        sport_key="baseball_mlb",
        include_props=True,
        prop_markets=[
            "batter_hits",
            "batter_total_bases",
            "batter_home_runs",
            "batter_rbis",
            "pitcher_strikeouts",
            "pitcher_outs",
        ],
        prop_market_map={
            "batter_hits": "batter_hits",
            "batter_total_bases": "batter_total_bases",
            "batter_home_runs": "batter_home_runs",
            "batter_rbis": "batter_rbis",
            "pitcher_strikeouts": "pitcher_strikeouts",
            "pitcher_outs": "pitcher_outs",
        },
        # Featured history ~2020-06; May–Jul 2026 mainlines largely owned → skip densify burn
        mainline_ranges=[
            (date(2020, 7, 23), date(2020, 10, 27)),  # COVID short season
            (date(2021, 4, 1), date(2021, 11, 2)),
            (date(2022, 4, 7), date(2022, 11, 5)),
            (date(2023, 3, 30), date(2023, 11, 1)),
            (date(2024, 3, 20), date(2024, 10, 30)),
            (date(2025, 3, 27), date(2025, 11, 2)),
            (date(2026, 3, 20), date(2026, 5, 8)),
        ],
        mainline_skip_ranges=[
            (date(2026, 5, 9), date(2026, 7, 25)),
        ],
        props_open_close=True,
    ),
    "nba": SportPlan(
        code="nba",
        sport_key="basketball_nba",
        include_props=True,
        prop_markets=[
            "player_points",
            "player_rebounds",
            "player_assists",
            "player_threes",
            "player_points_rebounds_assists",
        ],
        prop_market_map={
            "player_points": "pts",
            "player_rebounds": "reb",
            "player_assists": "ast",
            "player_threes": "threes",
            "player_points_rebounds_assists": "pra",
        },
        mainline_ranges=[
            (date(2020, 12, 22), date(2021, 7, 20)),
            (date(2021, 10, 19), date(2022, 6, 16)),
            (date(2022, 10, 18), date(2023, 6, 12)),
            (date(2023, 10, 24), date(2024, 6, 17)),
            (date(2024, 10, 22), date(2025, 6, 22)),
            (date(2025, 10, 21), date(2026, 6, 22)),
        ],
        props_open_close=True,
    ),
    "nhl": SportPlan(
        code="nhl",
        sport_key="icehockey_nhl",
        include_props=True,
        prop_markets=[
            "player_points",
            "player_goals",
            "player_assists",
            "player_shots_on_goal",
        ],
        prop_market_map={
            "player_points": "pts",
            "player_goals": "goals",
            "player_assists": "assists",
            "player_shots_on_goal": "sog",
        },
        mainline_ranges=[
            (date(2021, 1, 13), date(2021, 7, 7)),
            (date(2021, 10, 12), date(2022, 6, 26)),
            (date(2022, 10, 7), date(2023, 6, 13)),
            (date(2023, 10, 10), date(2024, 6, 24)),
            (date(2024, 10, 8), date(2025, 6, 24)),
            (date(2025, 10, 7), date(2026, 6, 24)),
        ],
        props_open_close=True,
    ),
    "wnba": SportPlan(
        code="wnba",
        sport_key="basketball_wnba",
        include_props=True,
        prop_markets=[
            "player_points",
            "player_rebounds",
            "player_assists",
            "player_threes",
        ],
        prop_market_map={
            "player_points": "pts",
            "player_rebounds": "reb",
            "player_assists": "ast",
            "player_threes": "threes",
        },
        mainline_ranges=[
            (date(2021, 5, 14), date(2021, 10, 17)),
            (date(2022, 5, 6), date(2022, 9, 18)),
            (date(2023, 5, 19), date(2023, 10, 18)),
            (date(2024, 5, 14), date(2024, 10, 20)),
            (date(2025, 5, 16), date(2025, 10, 20)),
            (date(2026, 5, 15), date(2026, 7, 25)),
        ],
        props_open_close=True,
    ),
    "cfb": SportPlan(
        code="cfb",
        sport_key="americanfootball_ncaaf",
        include_props=False,
        prop_markets=[],
        prop_market_map={},
        mainline_ranges=[
            (date(2020, 9, 3), date(2021, 1, 11)),
            (date(2021, 8, 28), date(2022, 1, 10)),
            (date(2022, 8, 27), date(2023, 1, 9)),
            (date(2023, 8, 26), date(2024, 1, 8)),
            (date(2024, 8, 24), date(2025, 1, 20)),
            (date(2025, 8, 23), date(2026, 1, 20)),
        ],
        props_open_close=False,
    ),
    "ncaam": SportPlan(
        code="ncaam",
        sport_key="basketball_ncaab",
        include_props=False,
        prop_markets=[],
        prop_market_map={},
        mainline_ranges=[
            (date(2020, 11, 25), date(2021, 4, 5)),
            (date(2021, 11, 9), date(2022, 4, 4)),
            (date(2022, 11, 7), date(2023, 4, 3)),
            (date(2023, 11, 6), date(2024, 4, 8)),
            (date(2024, 11, 4), date(2025, 4, 8)),
            (date(2025, 11, 3), date(2026, 4, 7)),
        ],
        props_open_close=False,
    ),
}

# Pull order from estimate (leverage-first)
DEFAULT_ORDER = ["nfl", "mlb", "nba", "nhl", "wnba", "cfb", "ncaam"]


def log(msg: str) -> None:
    line = f"{datetime.now(timezone.utc).isoformat()} {msg}"
    print(line, flush=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a") as f:
        f.write(line + "\n")


def load_api_key() -> str:
    for path in ENV_CANDIDATES:
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            if line.startswith("ODDS_API_KEY=") and not line.startswith("ODDS_API_KEY_"):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                if key:
                    return key
    raise RuntimeError("ODDS_API_KEY not found in apps/web/.env.local or .env")


def daterange(start: date, end: date) -> Iterable[date]:
    if end < start:
        return
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def in_skip_ranges(d: date, ranges: Sequence[Tuple[date, date]]) -> bool:
    for a, b in ranges:
        if a <= d <= b:
            return True
    return False


def signature(endpoint: str, params: Dict[str, Any]) -> str:
    stable = {k: str(v) for k, v in sorted(params.items()) if k != "apiKey"}
    payload = json.dumps({"endpoint": endpoint, "params": stable}, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _safe_int(v: Any) -> Optional[int]:
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _safe_float(v: Any) -> Optional[float]:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _parse_iso(raw: Optional[str]) -> Optional[datetime]:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


def _implied_prob(price: Optional[int]) -> Optional[float]:
    if price is None:
        return None
    return (abs(price) / (abs(price) + 100.0)) if price < 0 else (100.0 / (price + 100.0))


class CreditBudget:
    def __init__(self, starting_remaining: Optional[int]) -> None:
        self.starting_remaining = starting_remaining
        self.latest_remaining = starting_remaining
        self.spent = 0
        self.requests = 0
        self.stop_reason: Optional[str] = None

    def observe(self, remaining: Optional[int], last: Optional[int]) -> None:
        if remaining is not None:
            if self.latest_remaining is not None and remaining <= self.latest_remaining:
                self.spent = max(self.spent, (self.starting_remaining or remaining) - remaining)
            if self.starting_remaining is None:
                self.starting_remaining = remaining
                self.spent = 0
            else:
                self.spent = max(0, self.starting_remaining - remaining)
            self.latest_remaining = remaining
        elif last is not None:
            self.spent += int(last)
        self.requests += 1

    def should_stop(self) -> bool:
        if self.spent >= MAX_SESSION_SPEND:
            self.stop_reason = f"session spend {self.spent} >= {MAX_SESSION_SPEND}"
            return True
        if self.latest_remaining is not None and self.latest_remaining < MIN_REMAINING_FLOOR:
            self.stop_reason = (
                f"remaining {self.latest_remaining} < floor {MIN_REMAINING_FLOOR}"
            )
            return True
        return False


class PullState:
    def __init__(self) -> None:
        self.by_sport: Dict[str, Dict[str, Any]] = {}
        self.budget: Optional[CreditBudget] = None

    def sport(self, code: str) -> Dict[str, Any]:
        if code not in self.by_sport:
            self.by_sport[code] = {
                "mainline_dates_attempted": 0,
                "mainline_requests": 0,
                "mainline_skipped_cached": 0,
                "mainline_skipped_owned_range": 0,
                "mainline_skipped_empty": 0,
                "mainline_events": 0,
                "mainline_snapshots": 0,
                "prop_events_pulled": 0,
                "prop_events_skipped_owned": 0,
                "prop_events_skipped_no_match": 0,
                "prop_rows": 0,
                "prop_open_pulled": 0,
                "errors": 0,
            }
        return self.by_sport[code]


def ensure_prop_table(conn: psycopg.Connection) -> None:
    conn.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS player_prop_market_snapshots (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          sport_key text NOT NULL,
          season integer,
          week integer,
          external_game_id text,
          sportsbook text NOT NULL,
          captured_at timestamptz NOT NULL,
          player_name text NOT NULL,
          team text,
          opponent text,
          market_key text NOT NULL,
          line numeric,
          over_price integer,
          under_price integer,
          implied_prob_over numeric,
          implied_prob_under numeric,
          source text NOT NULL DEFAULT 'odds_api_historical',
          snapshot_kind text NOT NULL DEFAULT 'close',
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_player_prop_market_snapshots_key
          ON player_prop_market_snapshots (
            sport_key, sportsbook, captured_at, player_name, market_key,
            COALESCE(line, -9999), snapshot_kind
          )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_player_prop_market_snapshots_event
          ON player_prop_market_snapshots (sport_key, external_game_id, market_key)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS odds_api_request_cache (
          request_signature text PRIMARY KEY,
          endpoint text NOT NULL,
          sport_key text NOT NULL,
          request_params jsonb NOT NULL,
          status text NOT NULL,
          source_key text,
          credits_last integer,
          credits_used integer,
          credits_remaining integer,
          events_count integer NOT NULL DEFAULT 0,
          response_timestamp timestamptz,
          response_previous_timestamp timestamptz,
          response_next_timestamp timestamptz,
          last_error text,
          last_requested_at timestamptz NOT NULL,
          updated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS odds_api_credit_ledger (
          id bigserial PRIMARY KEY,
          endpoint text NOT NULL,
          sport_key text NOT NULL,
          request_signature text NOT NULL,
          requested_at timestamptz NOT NULL,
          request_params jsonb NOT NULL,
          status text NOT NULL,
          source_key text,
          credits_last integer,
          credits_used integer,
          credits_remaining integer,
          events_count integer NOT NULL DEFAULT 0,
          response_timestamp timestamptz,
          response_previous_timestamp timestamptz,
          response_next_timestamp timestamptz,
          error text,
          created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )


def cache_hit(conn: psycopg.Connection, sig: str) -> bool:
    row = conn.execute(
        "SELECT status FROM odds_api_request_cache WHERE request_signature = %s LIMIT 1",
        (sig,),
    ).fetchone()
    return bool(row and str(row[0]) == "success")


def record_request(
    conn: psycopg.Connection,
    *,
    endpoint: str,
    sport_key: str,
    params: Dict[str, Any],
    meta: Dict[str, Any],
    events_count: int,
    payload: Optional[Dict[str, Any]],
) -> str:
    requested_at = datetime.now(timezone.utc)
    stable = {k: str(v) for k, v in sorted(params.items()) if k != "apiKey"}
    sig = signature(endpoint, params)
    response_timestamp = _parse_iso(payload.get("timestamp")) if isinstance(payload, dict) else None
    response_previous = (
        _parse_iso(payload.get("previous_timestamp")) if isinstance(payload, dict) else None
    )
    response_next = _parse_iso(payload.get("next_timestamp")) if isinstance(payload, dict) else None
    err = meta.get("error")
    if err:
        err = re.sub(r"(apiKey=)[^&\s]+", r"\1REDACTED", str(err))
    conn.execute(
        """
        INSERT INTO odds_api_credit_ledger (
          endpoint, sport_key, request_signature, requested_at, request_params,
          status, source_key, credits_last, credits_used, credits_remaining,
          events_count, response_timestamp, response_previous_timestamp,
          response_next_timestamp, error, created_at
        ) VALUES (
          %(endpoint)s, %(sport_key)s, %(request_signature)s, %(requested_at)s, %(request_params)s,
          %(status)s, %(source_key)s, %(credits_last)s, %(credits_used)s, %(credits_remaining)s,
          %(events_count)s, %(response_timestamp)s, %(response_previous_timestamp)s,
          %(response_next_timestamp)s, %(error)s, %(requested_at)s
        )
        """,
        {
            "endpoint": endpoint,
            "sport_key": sport_key,
            "request_signature": sig,
            "requested_at": requested_at,
            "request_params": Json(stable),
            "status": meta["status"],
            "source_key": "enterprise-training-pull",
            "credits_last": _safe_int(meta.get("credits_last")),
            "credits_used": _safe_int(meta.get("credits_used")),
            "credits_remaining": _safe_int(meta.get("credits_remaining")),
            "events_count": int(events_count),
            "response_timestamp": response_timestamp,
            "response_previous_timestamp": response_previous,
            "response_next_timestamp": response_next,
            "error": err,
        },
    )
    conn.execute(
        """
        INSERT INTO odds_api_request_cache (
          request_signature, endpoint, sport_key, request_params, status, source_key,
          credits_last, credits_used, credits_remaining, events_count,
          response_timestamp, response_previous_timestamp, response_next_timestamp,
          last_error, last_requested_at, updated_at
        ) VALUES (
          %(request_signature)s, %(endpoint)s, %(sport_key)s, %(request_params)s, %(status)s,
          %(source_key)s, %(credits_last)s, %(credits_used)s, %(credits_remaining)s,
          %(events_count)s, %(response_timestamp)s, %(response_previous_timestamp)s,
          %(response_next_timestamp)s, %(last_error)s, %(last_requested_at)s, %(updated_at)s
        )
        ON CONFLICT (request_signature) DO UPDATE SET
          status = EXCLUDED.status,
          source_key = EXCLUDED.source_key,
          credits_last = EXCLUDED.credits_last,
          credits_used = EXCLUDED.credits_used,
          credits_remaining = EXCLUDED.credits_remaining,
          events_count = EXCLUDED.events_count,
          response_timestamp = EXCLUDED.response_timestamp,
          response_previous_timestamp = EXCLUDED.response_previous_timestamp,
          response_next_timestamp = EXCLUDED.response_next_timestamp,
          last_error = EXCLUDED.last_error,
          last_requested_at = EXCLUDED.last_requested_at,
          updated_at = EXCLUDED.updated_at
        """,
        {
            "request_signature": sig,
            "endpoint": endpoint,
            "sport_key": sport_key,
            "request_params": Json(stable),
            "status": meta["status"],
            "source_key": "enterprise-training-pull",
            "credits_last": _safe_int(meta.get("credits_last")),
            "credits_used": _safe_int(meta.get("credits_used")),
            "credits_remaining": _safe_int(meta.get("credits_remaining")),
            "events_count": int(events_count),
            "response_timestamp": response_timestamp,
            "response_previous_timestamp": response_previous,
            "response_next_timestamp": response_next,
            "last_error": err,
            "last_requested_at": requested_at,
            "updated_at": requested_at,
        },
    )
    return sig


def _redact_secrets(text: str) -> str:
    return re.sub(r"(apiKey=)[^&\s]+", r"\1REDACTED", text or "")


def call_odds_api(
    endpoint: str, params: Dict[str, Any], api_key: str
) -> Tuple[Optional[Any], Dict[str, Any]]:
    meta: Dict[str, Any] = {
        "status": "failed",
        "credits_last": None,
        "credits_used": None,
        "credits_remaining": None,
        "error": None,
    }
    try:
        resp = requests.get(
            f"{BASE_URL}/{endpoint}",
            params={**params, "apiKey": api_key},
            timeout=REQUEST_TIMEOUT,
        )
        meta["credits_last"] = _safe_int(resp.headers.get("x-requests-last"))
        meta["credits_used"] = _safe_int(resp.headers.get("x-requests-used"))
        meta["credits_remaining"] = _safe_int(resp.headers.get("x-requests-remaining"))
        if resp.status_code != 200:
            meta["error"] = _redact_secrets(f"HTTP {resp.status_code}: {resp.text[:400]}")
            return None, meta
        meta["status"] = "success"
        return resp.json(), meta
    except Exception as exc:  # noqa: BLE001
        meta["error"] = _redact_secrets(str(exc)[:800])
        return None, meta


def league_code_for_plan(plan: SportPlan) -> str:
    return "ncaam" if plan.code == "ncaam" else plan.code


def mainline_date_owned(conn: psycopg.Connection, plan: SportPlan, game_date: date) -> bool:
    """True when odds_snapshots already has open+close-like coverage for this slate date."""
    league = league_code_for_plan(plan)
    row = conn.execute(
        """
        SELECT
          COUNT(DISTINCT g.id) AS games_with_odds,
          COUNT(DISTINCT date_trunc('hour', o.captured_at)) AS distinct_hours
        FROM games g
        JOIN seasons s ON s.id = g.season_id
        JOIN leagues l ON l.id = s.league_id
        JOIN odds_snapshots o ON o.game_id = g.id
        WHERE l.code = %s
          AND g.game_date BETWEEN %s AND %s
        """,
        (league, game_date - timedelta(days=1), game_date + timedelta(days=1)),
    ).fetchone()
    games = int(row[0] or 0) if row else 0
    hours = int(row[1] or 0) if row else 0
    # Thresholds: NFL slate often 10–16; daily sports lower. Require multi-hour (= open+close-ish).
    if plan.code == "nfl":
        return games >= 8 and hours >= 2
    if plan.code in {"mlb", "nba", "nhl", "wnba"}:
        return games >= 4 and hours >= 2
    # College: denser calendars; slightly lower bar
    return games >= 6 and hours >= 2


def load_checkpoint() -> Dict[str, Any]:
    if CHECKPOINT_PATH.exists():
        return json.loads(CHECKPOINT_PATH.read_text())
    return {"completed_sports": [], "completed_phases": {}}


def save_checkpoint(cp: Dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_PATH.write_text(json.dumps(cp, indent=2, default=str))


def save_state_summary(state: PullState, extra: Dict[str, Any]) -> None:
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "credits_spent": state.budget.spent if state.budget else None,
        "credits_remaining": state.budget.latest_remaining if state.budget else None,
        "credits_starting": state.budget.starting_remaining if state.budget else None,
        "stop_reason": state.budget.stop_reason if state.budget else None,
        "by_sport": state.by_sport,
        **extra,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(payload, indent=2, default=str))


# ---------------------------------------------------------------------------
# Mainline densify
# ---------------------------------------------------------------------------


def pull_mainline_snapshot(
    conn: psycopg.Connection,
    *,
    plan: SportPlan,
    snapshot_dt: datetime,
    api_key: str,
    budget: CreditBudget,
    state: PullState,
) -> bool:
    """Returns False if budget stop triggered."""
    if budget.should_stop():
        return False
    endpoint = f"historical/sports/{plan.sport_key}/odds"
    params = {
        "regions": REGIONS,
        "markets": MAINLINE_MARKETS,
        "oddsFormat": "american",
        "dateFormat": "iso",
        "bookmakers": BOOKMAKERS,
        "date": snapshot_dt.isoformat().replace("+00:00", "Z"),
    }
    sig = signature(endpoint, params)
    st = state.sport(plan.code)
    if cache_hit(conn, sig):
        st["mainline_skipped_cached"] += 1
        return True
    payload, meta = call_odds_api(endpoint, params, api_key)
    budget.observe(_safe_int(meta.get("credits_remaining")), _safe_int(meta.get("credits_last")))
    events = payload.get("data") if isinstance(payload, dict) else None
    events_list = events if isinstance(events, list) else []
    st["mainline_requests"] += 1
    persist_ok = True
    if meta["status"] == "success" and events_list:
        try:
            for event in events_list:
                if isinstance(event, dict) and not event.get("sport_key"):
                    event["sport_key"] = plan.sport_key
            persisted = persist_odds_events(
                conn, sport_key=plan.sport_key, events=events_list
            )
            st["mainline_events"] += int(persisted.get("events_persisted") or 0)
            st["mainline_snapshots"] += int(persisted.get("snapshots_inserted") or 0)
            if int(persisted.get("event_errors") or 0) > 0:
                st["errors"] += int(persisted["event_errors"])
                persist_ok = int(persisted.get("events_persisted") or 0) > 0
        except Exception:
            persist_ok = False
            st["errors"] += 1
            log(f"[{plan.code}] mainline persist error: {traceback.format_exc()[-400:]}")
            meta = dict(meta)
            meta["status"] = "persist_error"
            meta["error"] = "persist failed after successful API pull"
    elif meta["status"] != "success":
        st["errors"] += 1
        log(f"[{plan.code}] mainline fail {params['date']}: {meta.get('error')}")
    # Only mark cache success after persist so resume can retry incomplete pulls
    if meta["status"] == "success" and not persist_ok:
        meta = dict(meta)
        meta["status"] = "persist_error"
    record_request(
        conn,
        endpoint=endpoint,
        sport_key=plan.sport_key,
        params=params,
        meta=meta,
        events_count=len(events_list),
        payload=payload if isinstance(payload, dict) else None,
    )
    time.sleep(SLEEP_S)
    return not budget.should_stop()


_EVENTS_MEMO: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}


def probe_events_for_date(
    conn: psycopg.Connection,
    *,
    plan: SportPlan,
    game_date: date,
    api_key: str,
    budget: CreditBudget,
) -> List[Dict[str, Any]]:
    memo_key = (plan.sport_key, game_date.isoformat())
    if memo_key in _EVENTS_MEMO:
        return _EVENTS_MEMO[memo_key]
    endpoint = f"historical/sports/{plan.sport_key}/events"
    # Midday UTC ahead of typical US slates
    query_dt = f"{game_date.isoformat()}T16:00:00Z"
    params = {"date": query_dt, "dateFormat": "iso"}
    if budget.should_stop():
        return []
    sig = signature(endpoint, params)
    if cache_hit(conn, sig):
        # Re-fetch is free of credits via cache-hit skip; return empty and force a live
        # call only when we have no memo — for events lists we still need the payload.
        # Prefer a lightweight re-pull only if not cached-as-empty; store events in memo
        # via a dedicated events payload cache table is out of scope — re-call API when
        # cache says success but we lack memo (1 credit). To avoid that, mark empty
        # successes in memo by reading events_count from cache.
        row = conn.execute(
            """
            SELECT events_count FROM odds_api_request_cache
            WHERE request_signature = %s AND status = 'success' LIMIT 1
            """,
            (sig,),
        ).fetchone()
        if row is not None and int(row[0] or 0) == 0:
            _EVENTS_MEMO[memo_key] = []
            return []
        # Non-empty cached success without in-memory payload: must re-pull (1 credit)
        # OR skip and treat as unknown. Prefer re-pull so props/mainlines can proceed.
    payload, meta = call_odds_api(endpoint, params, api_key)
    budget.observe(_safe_int(meta.get("credits_remaining")), _safe_int(meta.get("credits_last")))
    events = payload.get("data") if isinstance(payload, dict) else None
    events_list = events if isinstance(events, list) else []
    record_request(
        conn,
        endpoint=endpoint,
        sport_key=plan.sport_key,
        params=params,
        meta=meta,
        events_count=len(events_list),
        payload=payload if isinstance(payload, dict) else None,
    )
    time.sleep(SLEEP_S)
    out = events_list if meta["status"] == "success" else []
    _EVENTS_MEMO[memo_key] = out
    return out


def nfl_game_dates(conn: psycopg.Connection, seasons: Sequence[int]) -> List[date]:
    rows = conn.execute(
        """
        SELECT DISTINCT game_date
        FROM nfl_dp_schedules
        WHERE season = ANY(%s)
          AND home_score IS NOT NULL
        ORDER BY game_date
        """,
        (list(seasons),),
    ).fetchall()
    return [r[0] for r in rows if isinstance(r[0], date)]


def run_mainlines(
    conn: psycopg.Connection,
    *,
    plan: SportPlan,
    api_key: str,
    budget: CreditBudget,
    state: PullState,
    checkpoint: Dict[str, Any],
) -> None:
    phase = f"{plan.code}:mainlines"
    if phase in checkpoint.get("completed_phases", {}):
        log(f"[{plan.code}] mainlines already completed — skip")
        return
    st = state.sport(plan.code)
    if plan.code == "nfl":
        dates = nfl_game_dates(conn, plan.nfl_seasons)
    else:
        dates = []
        today = date.today()
        for start, end in plan.mainline_ranges:
            end_eff = min(end, today)
            for d in daterange(start, end_eff):
                if in_skip_ranges(d, plan.mainline_skip_ranges):
                    st["mainline_skipped_owned_range"] += 1
                    continue
                dates.append(d)
        dates = sorted(set(dates))

    log(f"[{plan.code}] mainline candidate dates={len(dates)}")
    # Passes: close (game day 17:00 UTC), open (prior day 18:00 UTC)
    passes = [
        ("close", 0, 17),
        ("open", -1, 18),
    ]
    empty_dates: Set[str] = set()
    for i, game_date in enumerate(dates):
        if budget.should_stop():
            log(f"[{plan.code}] STOP mainlines: {budget.stop_reason}")
            break
        st["mainline_dates_attempted"] += 1
        # DB-first: skip dates we already own open+close-like coverage for
        if mainline_date_owned(conn, plan, game_date):
            st["mainline_skipped_owned_range"] += 1
            if (i + 1) % 50 == 0:
                log(
                    f"[{plan.code}] mainline ownership scan {i+1}/{len(dates)} "
                    f"skipped_owned={st['mainline_skipped_owned_range']}"
                )
                save_state_summary(state, {"phase": phase, "date_index": i})
            continue
        # Probe once per date for non-NFL calendar sports to avoid 30-credit empties
        if plan.code != "nfl" and game_date.isoformat() not in empty_dates:
            events = probe_events_for_date(
                conn, plan=plan, game_date=game_date, api_key=api_key, budget=budget
            )
            if budget.should_stop():
                break
            if not events:
                empty_dates.add(game_date.isoformat())
                st["mainline_skipped_empty"] += 1
                continue
        elif plan.code != "nfl" and game_date.isoformat() in empty_dates:
            st["mainline_skipped_empty"] += 1
            continue

        for _label, day_offset, hour in passes:
            snap = datetime.combine(
                game_date + timedelta(days=day_offset),
                dt_time(hour=hour, minute=0),
                tzinfo=timezone.utc,
            )
            ok = pull_mainline_snapshot(
                conn,
                plan=plan,
                snapshot_dt=snap,
                api_key=api_key,
                budget=budget,
                state=state,
            )
            if not ok:
                break
        if (i + 1) % 25 == 0:
            log(
                f"[{plan.code}] mainline progress {i+1}/{len(dates)} "
                f"spent={budget.spent} remaining={budget.latest_remaining}"
            )
            save_checkpoint(checkpoint)
            save_state_summary(state, {"phase": phase, "date_index": i})

    if not budget.should_stop():
        checkpoint.setdefault("completed_phases", {})[phase] = {
            "at": datetime.now(timezone.utc).isoformat(),
            "dates": len(dates),
        }
        save_checkpoint(checkpoint)
    save_state_summary(state, {"phase": phase})


# ---------------------------------------------------------------------------
# Player props
# ---------------------------------------------------------------------------


def owned_nfl_prop_events(conn: psycopg.Connection) -> Dict[Tuple[int, int, str, str], Set[str]]:
    rows = conn.execute(
        """
        SELECT season, week,
               COALESCE(metadata->>'queried_home_team', ''),
               COALESCE(metadata->>'queried_away_team', ''),
               market_key
        FROM nfl_player_prop_market_snapshots
        WHERE source = 'odds_api_historical'
        """
    ).fetchall()
    out: Dict[Tuple[int, int, str, str], Set[str]] = {}
    for season, week, home, away, market in rows:
        if not home or not away:
            continue
        key = (int(season), int(week), home, away)
        out.setdefault(key, set()).add(str(market))
    return out


def owned_generic_prop_events(conn: psycopg.Connection, sport_key: str) -> Dict[str, Set[str]]:
    rows = conn.execute(
        """
        SELECT external_game_id, market_key
        FROM player_prop_market_snapshots
        WHERE sport_key = %s AND external_game_id IS NOT NULL
        """,
        (sport_key,),
    ).fetchall()
    out: Dict[str, Set[str]] = {}
    for eid, market in rows:
        out.setdefault(str(eid), set()).add(str(market))
    return out


def insert_nfl_prop_rows(
    conn: psycopg.Connection,
    *,
    sample_game: Dict[str, Any],
    event_id: str,
    commence: Optional[datetime],
    details: Dict[str, Any],
    market_map: Dict[str, str],
    snapshot_kind: str,
) -> int:
    inserted = 0
    meta_base = {
        "event_id": event_id,
        "event_commence_time": commence.isoformat() if commence else None,
        "queried_home_team": sample_game["home_team"],
        "queried_away_team": sample_game["away_team"],
        "response_home_team": details.get("home_team"),
        "response_away_team": details.get("away_team"),
        "snapshot_kind": snapshot_kind,
        "pull": "enterprise-training",
    }
    for bookmaker in details.get("bookmakers") or []:
        sportsbook = str(bookmaker.get("key") or bookmaker.get("title") or "unknown")
        for market in bookmaker.get("markets") or []:
            raw_key = str(market.get("key") or "")
            market_key = market_map.get(raw_key)
            if market_key is None:
                continue
            by_player: Dict[Tuple[str, Optional[float]], Dict[str, Any]] = {}
            for outcome in market.get("outcomes") or []:
                player_name = str(outcome.get("description") or "").strip()
                if not player_name:
                    # anytime_td often uses name=player
                    player_name = str(outcome.get("name") or "").strip()
                    side = "yes"
                else:
                    side = str(outcome.get("name") or "").strip().lower()
                if not player_name:
                    continue
                point = _safe_float(outcome.get("point"))
                key = (player_name, point)
                row = by_player.setdefault(
                    key,
                    {"player_name": player_name, "line": point, "over_price": None, "under_price": None},
                )
                price = _safe_int(outcome.get("price"))
                if side in {"over", "yes"}:
                    row["over_price"] = price
                elif side in {"under", "no"}:
                    row["under_price"] = price
            captured_at = _parse_iso(bookmaker.get("last_update")) or commence or datetime.now(
                timezone.utc
            )
            for (_pn, line), row in by_player.items():
                metadata = dict(meta_base)
                metadata["raw_market_key"] = raw_key
                conn.execute(
                    """
                    INSERT INTO nfl_player_prop_market_snapshots (
                      season, week, game_id, external_game_id, sportsbook, captured_at,
                      player_id, player_name, team, opponent, market_key, line,
                      over_price, under_price, implied_prob_over, implied_prob_under,
                      source, metadata, created_at
                    ) VALUES (
                      %(season)s, %(week)s, NULL, %(external_game_id)s, %(sportsbook)s, %(captured_at)s,
                      NULL, %(player_name)s, NULL, NULL, %(market_key)s, %(line)s,
                      %(over_price)s, %(under_price)s, %(implied_over)s, %(implied_under)s,
                      %(source)s, %(metadata)s, NOW()
                    )
                    ON CONFLICT (sportsbook, captured_at, player_name, market_key, COALESCE(line, -9999))
                    DO UPDATE SET
                      over_price = COALESCE(EXCLUDED.over_price, nfl_player_prop_market_snapshots.over_price),
                      under_price = COALESCE(EXCLUDED.under_price, nfl_player_prop_market_snapshots.under_price),
                      implied_prob_over = COALESCE(EXCLUDED.implied_prob_over, nfl_player_prop_market_snapshots.implied_prob_over),
                      implied_prob_under = COALESCE(EXCLUDED.implied_prob_under, nfl_player_prop_market_snapshots.implied_prob_under),
                      metadata = EXCLUDED.metadata
                    """,
                    {
                        "season": sample_game["season"],
                        "week": sample_game["week"],
                        "external_game_id": event_id,
                        "sportsbook": sportsbook,
                        "captured_at": captured_at,
                        "player_name": row["player_name"],
                        "market_key": market_key,
                        "line": line,
                        "over_price": row["over_price"],
                        "under_price": row["under_price"],
                        "implied_over": _implied_prob(row["over_price"]),
                        "implied_under": _implied_prob(row["under_price"]),
                        "source": "odds_api_historical",
                        "metadata": Json(metadata),
                    },
                )
                inserted += 1
    return inserted


def insert_generic_prop_rows(
    conn: psycopg.Connection,
    *,
    sport_key: str,
    event_id: str,
    commence: Optional[datetime],
    details: Dict[str, Any],
    market_map: Dict[str, str],
    snapshot_kind: str,
    season: Optional[int],
) -> int:
    inserted = 0
    meta_base = {
        "event_id": event_id,
        "event_commence_time": commence.isoformat() if commence else None,
        "response_home_team": details.get("home_team"),
        "response_away_team": details.get("away_team"),
        "pull": "enterprise-training",
    }
    for bookmaker in details.get("bookmakers") or []:
        sportsbook = str(bookmaker.get("key") or bookmaker.get("title") or "unknown")
        for market in bookmaker.get("markets") or []:
            raw_key = str(market.get("key") or "")
            market_key = market_map.get(raw_key)
            if market_key is None:
                continue
            by_player: Dict[Tuple[str, Optional[float]], Dict[str, Any]] = {}
            for outcome in market.get("outcomes") or []:
                player_name = str(outcome.get("description") or "").strip()
                side = str(outcome.get("name") or "").strip().lower()
                if not player_name:
                    player_name = str(outcome.get("name") or "").strip()
                    side = "yes"
                if not player_name:
                    continue
                point = _safe_float(outcome.get("point"))
                key = (player_name, point)
                row = by_player.setdefault(
                    key,
                    {"player_name": player_name, "line": point, "over_price": None, "under_price": None},
                )
                price = _safe_int(outcome.get("price"))
                if side in {"over", "yes"}:
                    row["over_price"] = price
                elif side in {"under", "no"}:
                    row["under_price"] = price
            captured_at = _parse_iso(bookmaker.get("last_update")) or commence or datetime.now(
                timezone.utc
            )
            for (_pn, line), row in by_player.items():
                metadata = dict(meta_base)
                metadata["raw_market_key"] = raw_key
                conn.execute(
                    """
                    INSERT INTO player_prop_market_snapshots (
                      sport_key, season, week, external_game_id, sportsbook, captured_at,
                      player_name, team, opponent, market_key, line,
                      over_price, under_price, implied_prob_over, implied_prob_under,
                      source, snapshot_kind, metadata, created_at
                    ) VALUES (
                      %(sport_key)s, %(season)s, NULL, %(external_game_id)s, %(sportsbook)s, %(captured_at)s,
                      %(player_name)s, NULL, NULL, %(market_key)s, %(line)s,
                      %(over_price)s, %(under_price)s, %(implied_over)s, %(implied_under)s,
                      %(source)s, %(snapshot_kind)s, %(metadata)s, NOW()
                    )
                    ON CONFLICT (
                      sport_key, sportsbook, captured_at, player_name, market_key,
                      COALESCE(line, -9999), snapshot_kind
                    )
                    DO UPDATE SET
                      over_price = COALESCE(EXCLUDED.over_price, player_prop_market_snapshots.over_price),
                      under_price = COALESCE(EXCLUDED.under_price, player_prop_market_snapshots.under_price),
                      implied_prob_over = COALESCE(EXCLUDED.implied_prob_over, player_prop_market_snapshots.implied_prob_over),
                      implied_prob_under = COALESCE(EXCLUDED.implied_prob_under, player_prop_market_snapshots.implied_prob_under),
                      metadata = EXCLUDED.metadata
                    """,
                    {
                        "sport_key": sport_key,
                        "season": season,
                        "external_game_id": event_id,
                        "sportsbook": sportsbook,
                        "captured_at": captured_at,
                        "player_name": row["player_name"],
                        "market_key": market_key,
                        "line": line,
                        "over_price": row["over_price"],
                        "under_price": row["under_price"],
                        "implied_over": _implied_prob(row["over_price"]),
                        "implied_under": _implied_prob(row["under_price"]),
                        "source": "odds_api_historical",
                        "snapshot_kind": snapshot_kind,
                        "metadata": Json(metadata),
                    },
                )
                inserted += 1
    return inserted


def pull_event_props(
    conn: psycopg.Connection,
    *,
    plan: SportPlan,
    event: Dict[str, Any],
    api_key: str,
    budget: CreditBudget,
    state: PullState,
    sample_game: Optional[Dict[str, Any]] = None,
    season_hint: Optional[int] = None,
) -> bool:
    if budget.should_stop():
        return False
    event_id = str(event.get("id") or "")
    commence = _parse_iso(event.get("commence_time"))
    if not event_id or commence is None:
        state.sport(plan.code)["prop_events_skipped_no_match"] += 1
        return True

    kinds: List[Tuple[str, datetime]] = [("close", commence)]
    if plan.props_open_close:
        kinds.append(("open", commence - timedelta(hours=24)))

    st = state.sport(plan.code)
    for kind, when in kinds:
        if budget.should_stop():
            return False
        endpoint = f"historical/sports/{plan.sport_key}/events/{event_id}/odds"
        params = {
            "regions": REGIONS,
            "markets": ",".join(plan.prop_markets),
            "bookmakers": BOOKMAKERS,
            "oddsFormat": "american",
            "dateFormat": "iso",
            "date": when.isoformat().replace("+00:00", "Z"),
        }
        sig = signature(endpoint, params)
        if cache_hit(conn, sig):
            st["prop_events_skipped_owned"] += 1
            continue
        payload, meta = call_odds_api(endpoint, params, api_key)
        budget.observe(_safe_int(meta.get("credits_remaining")), _safe_int(meta.get("credits_last")))
        details = payload.get("data") if isinstance(payload, dict) else None
        if isinstance(details, dict) and meta["status"] == "success":
            details["_snapshot_timestamp"] = (
                payload.get("timestamp") if isinstance(payload, dict) else None
            )
            try:
                if plan.code == "nfl" and sample_game is not None:
                    n = insert_nfl_prop_rows(
                        conn,
                        sample_game=sample_game,
                        event_id=event_id,
                        commence=commence,
                        details=details,
                        market_map=plan.prop_market_map,
                        snapshot_kind=kind,
                    )
                else:
                    n = insert_generic_prop_rows(
                        conn,
                        sport_key=plan.sport_key,
                        event_id=event_id,
                        commence=commence,
                        details=details,
                        market_map=plan.prop_market_map,
                        snapshot_kind=kind,
                        season=season_hint or commence.year,
                    )
                st["prop_rows"] += n
                if kind == "close":
                    st["prop_events_pulled"] += 1
                else:
                    st["prop_open_pulled"] += 1
            except Exception:
                st["errors"] += 1
                meta = dict(meta)
                meta["status"] = "persist_error"
                meta["error"] = _redact_secrets(traceback.format_exc()[-300:])
                log(f"[{plan.code}] prop persist error event={event_id}: {meta['error']}")
        elif meta["status"] != "success":
            st["errors"] += 1
            log(f"[{plan.code}] prop fail event={event_id} kind={kind}: {meta.get('error')}")
        record_request(
            conn,
            endpoint=endpoint.replace(event_id, "{eventId}"),
            sport_key=plan.sport_key,
            params=params,
            meta=meta,
            events_count=1 if isinstance(details, dict) else 0,
            payload=payload if isinstance(payload, dict) else None,
        )
        time.sleep(SLEEP_S)
    return not budget.should_stop()


def run_nfl_props(
    conn: psycopg.Connection,
    *,
    plan: SportPlan,
    api_key: str,
    budget: CreditBudget,
    state: PullState,
    checkpoint: Dict[str, Any],
) -> None:
    phase = f"{plan.code}:props"
    if phase in checkpoint.get("completed_phases", {}):
        log("[nfl] props already completed — skip")
        return
    needed = set(plan.prop_market_map.values())
    owned = owned_nfl_prop_events(conn)
    prop_seasons = [y for y in plan.nfl_seasons if y >= PROPS_EARLIEST.year]
    rows = conn.execute(
        """
        SELECT season, week, game_id, game_date, home_team, away_team
        FROM nfl_dp_schedules
        WHERE season = ANY(%s)
          AND week BETWEEN 1 AND 22
          AND home_score IS NOT NULL
          AND game_date >= %s
        ORDER BY season, week, game_date, game_id
        """,
        (prop_seasons, PROPS_EARLIEST),
    ).fetchall()
    targets: List[Dict[str, Any]] = []
    st = state.sport("nfl")
    for r in rows:
        g = {
            "season": int(r[0]),
            "week": int(r[1]),
            "game_id": r[2],
            "game_date": r[3],
            "home_team": r[4],
            "away_team": r[5],
        }
        key = (g["season"], g["week"], g["home_team"], g["away_team"])
        have = owned.get(key, set())
        if needed.issubset(have):
            st["prop_events_skipped_owned"] += 1
            continue
        targets.append(g)
    log(f"[nfl] props targets={len(targets)} (skip owned={st['prop_events_skipped_owned']})")

    by_date: Dict[str, List[Dict[str, Any]]] = {}
    for g in targets:
        by_date.setdefault(str(g["game_date"]), []).append(g)

    for di, (game_date, games) in enumerate(sorted(by_date.items())):
        if budget.should_stop():
            break
        events = probe_events_for_date(
            conn,
            plan=plan,
            game_date=date.fromisoformat(game_date),
            api_key=api_key,
            budget=budget,
        )
        if budget.should_stop():
            break
        by_abbr: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for ev in events:
            home = NFL_FULL_NAME_TO_ABBR.get(str(ev.get("home_team") or ""))
            away = NFL_FULL_NAME_TO_ABBR.get(str(ev.get("away_team") or ""))
            if home and away:
                by_abbr[(home, away)] = ev
        for g in games:
            if budget.should_stop():
                break
            ev = by_abbr.get((g["home_team"], g["away_team"]))
            if ev is None:
                st["prop_events_skipped_no_match"] += 1
                continue
            ok = pull_event_props(
                conn,
                plan=plan,
                event=ev,
                api_key=api_key,
                budget=budget,
                state=state,
                sample_game=g,
            )
            if not ok:
                break
        if (di + 1) % 10 == 0:
            log(
                f"[nfl] props date progress {di+1}/{len(by_date)} "
                f"pulled={st['prop_events_pulled']} spent={budget.spent}"
            )
            save_checkpoint(checkpoint)
            save_state_summary(state, {"phase": phase})

    if not budget.should_stop():
        checkpoint.setdefault("completed_phases", {})[phase] = {
            "at": datetime.now(timezone.utc).isoformat(),
            "targets": len(targets),
        }
        save_checkpoint(checkpoint)


def run_calendar_props(
    conn: psycopg.Connection,
    *,
    plan: SportPlan,
    api_key: str,
    budget: CreditBudget,
    state: PullState,
    checkpoint: Dict[str, Any],
) -> None:
    phase = f"{plan.code}:props"
    if phase in checkpoint.get("completed_phases", {}):
        log(f"[{plan.code}] props already completed — skip")
        return
    needed = set(plan.prop_market_map.values())
    owned = owned_generic_prop_events(conn, plan.sport_key)
    today = date.today()
    dates: List[date] = []
    for start, end in plan.mainline_ranges:
        # Props history only from 2023-05-03; do not skip May–Jul for props (empty inventory)
        start_eff = max(start, PROPS_EARLIEST)
        end_eff = min(end, today)
        if end_eff < start_eff:
            continue
        dates.extend(list(daterange(start_eff, end_eff)))
    # MLB props need full 2026 YTD including May–Jul (mainline densify skip range)
    if plan.code == "mlb":
        dates.extend(list(daterange(date(2026, 5, 9), min(date(2026, 7, 25), today))))
    dates = sorted({d for d in dates if d >= PROPS_EARLIEST})
    log(f"[{plan.code}] props candidate dates={len(dates)} owned_events={len(owned)}")
    st = state.sport(plan.code)

    for i, game_date in enumerate(dates):
        if budget.should_stop():
            break
        events = probe_events_for_date(
            conn, plan=plan, game_date=game_date, api_key=api_key, budget=budget
        )
        if budget.should_stop():
            break
        for ev in events:
            if budget.should_stop():
                break
            eid = str(ev.get("id") or "")
            have = owned.get(eid, set())
            if eid and needed.issubset(have) and not plan.props_open_close:
                st["prop_events_skipped_owned"] += 1
                continue
            # If close owned but we want open too, still pull — cache will skip close
            if eid and needed.issubset(have) and plan.props_open_close:
                # still attempt; request cache skips identical close; open may be new
                pass
            season_hint = game_date.year
            if plan.code in {"nba", "nhl", "ncaam"} and game_date.month >= 8:
                season_hint = game_date.year + 1
            ok = pull_event_props(
                conn,
                plan=plan,
                event=ev,
                api_key=api_key,
                budget=budget,
                state=state,
                season_hint=season_hint,
            )
            if eid and ok:
                # refresh owned set cheaply
                owned.setdefault(eid, set()).update(needed)
            if not ok:
                break
        if (i + 1) % 15 == 0:
            log(
                f"[{plan.code}] props date progress {i+1}/{len(dates)} "
                f"pulled={st['prop_events_pulled']} spent={budget.spent} rem={budget.latest_remaining}"
            )
            save_checkpoint(checkpoint)
            save_state_summary(state, {"phase": phase})

    if not budget.should_stop():
        checkpoint.setdefault("completed_phases", {})[phase] = {
            "at": datetime.now(timezone.utc).isoformat(),
            "dates": len(dates),
        }
        save_checkpoint(checkpoint)


def verify_inventory(conn: psycopg.Connection) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for code, plan in PLANS.items():
        row = conn.execute(
            """
            SELECT COUNT(DISTINCT g.id)
            FROM odds_snapshots o
            JOIN games g ON g.id = o.game_id
            JOIN seasons s ON s.id = g.season_id
            JOIN leagues l ON l.id = s.league_id
            WHERE l.code = %s
            """,
            (plan.code if plan.code != "ncaam" else "ncaam",),
        ).fetchone()
        # SPORT_MAP uses ncaam for basketball_ncaab
        mainline_games = int(row[0] or 0) if row else 0
        if plan.code == "nfl":
            props = conn.execute(
                """
                SELECT COUNT(*), COUNT(DISTINCT external_game_id),
                       array_agg(DISTINCT market_key)
                FROM nfl_player_prop_market_snapshots
                WHERE source = 'odds_api_historical'
                """
            ).fetchone()
            out[code] = {
                "mainline_games": mainline_games,
                "prop_rows": int(props[0] or 0),
                "prop_events": int(props[1] or 0),
                "prop_markets": props[2],
            }
        elif plan.include_props:
            props = conn.execute(
                """
                SELECT COUNT(*), COUNT(DISTINCT external_game_id),
                       array_agg(DISTINCT market_key)
                FROM player_prop_market_snapshots
                WHERE sport_key = %s
                """,
                (plan.sport_key,),
            ).fetchone()
            out[code] = {
                "mainline_games": mainline_games,
                "prop_rows": int(props[0] or 0),
                "prop_events": int(props[1] or 0),
                "prop_markets": props[2],
            }
        else:
            out[code] = {"mainline_games": mainline_games, "props": "excluded"}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--sports",
        default=",".join(DEFAULT_ORDER),
        help="Comma-separated sport codes in pull order",
    )
    ap.add_argument("--skip-mainlines", action="store_true")
    ap.add_argument("--skip-props", action="store_true")
    ap.add_argument("--max-spend", type=int, default=None)
    args = ap.parse_args()

    global MAX_SESSION_SPEND
    if args.max_spend is not None:
        MAX_SESSION_SPEND = int(args.max_spend)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    log("[boot] loading API key")
    api_key = load_api_key()
    os.environ["ODDS_API_KEY"] = api_key

    log("[boot] connecting DB")
    conn = psycopg.connect(DATABASE_URL_PSYCOPG, autocommit=True)
    ensure_prop_table(conn)

    row = conn.execute(
        """
        SELECT credits_remaining FROM odds_api_credit_ledger
        WHERE credits_remaining IS NOT NULL
        ORDER BY requested_at DESC LIMIT 1
        """
    ).fetchone()
    log("[boot] probing remaining credits")
    _payload, meta = call_odds_api("sports", {}, api_key)
    starting = _safe_int(meta.get("credits_remaining"))
    if starting is None and row:
        starting = int(row[0])
    budget = CreditBudget(starting)
    if meta.get("credits_remaining") is not None:
        budget.observe(starting, 0)
    state = PullState()
    state.budget = budget
    checkpoint = load_checkpoint()

    log(
        f"[start] remaining={budget.latest_remaining} max_spend={MAX_SESSION_SPEND} "
        f"floor={MIN_REMAINING_FLOOR} target_high~{TARGET_HIGH}"
    )
    save_state_summary(state, {"status": "started"})

    sports = [s.strip() for s in args.sports.split(",") if s.strip()]
    try:
        for code in sports:
            if budget.should_stop():
                break
            plan = PLANS[code]
            log(f"==== {code} ====")
            if not args.skip_mainlines:
                run_mainlines(
                    conn,
                    plan=plan,
                    api_key=api_key,
                    budget=budget,
                    state=state,
                    checkpoint=checkpoint,
                )
            if plan.include_props and not args.skip_props and not budget.should_stop():
                if code == "nfl":
                    run_nfl_props(
                        conn,
                        plan=plan,
                        api_key=api_key,
                        budget=budget,
                        state=state,
                        checkpoint=checkpoint,
                    )
                else:
                    run_calendar_props(
                        conn,
                        plan=plan,
                        api_key=api_key,
                        budget=budget,
                        state=state,
                        checkpoint=checkpoint,
                    )
            if not budget.should_stop():
                checkpoint.setdefault("completed_sports", [])
                if code not in checkpoint["completed_sports"]:
                    checkpoint["completed_sports"].append(code)
                save_checkpoint(checkpoint)
            save_state_summary(state, {"status": "running", "last_sport": code})
    finally:
        inv = verify_inventory(conn)
        save_state_summary(
            state,
            {
                "status": "stopped" if budget.should_stop() else "completed",
                "stop_reason": budget.stop_reason,
                "inventory": inv,
                "tables_written": [
                    "odds_snapshots",
                    "games/teams/seasons/leagues/sports",
                    "nfl_player_prop_market_snapshots",
                    "player_prop_market_snapshots",
                    "odds_api_request_cache",
                    "odds_api_credit_ledger",
                ],
            },
        )
        conn.close()
        log(
            f"[done] spent={budget.spent} remaining={budget.latest_remaining} "
            f"stop={budget.stop_reason}"
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        err = traceback.format_exc()
        log(f"[fatal] {err}")
        with (OUT_DIR / "fatal.log").open("a") as f:
            f.write(err + "\n")
        raise
