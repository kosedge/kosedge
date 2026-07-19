"""Pull a real, budget-conscious sample of historical CLOSING player-prop
lines (pass/rush/receiving yards) for real 2023-2025 NFL games, via The
Odds API's historical per-event odds endpoint.

Why this script exists: `nfl_player_prop_market_snapshots` (the production
table meant to hold exactly this data -- see
infra/db/020_nfl_player_props_fantasy_foundation.sql) was confirmed empty
at the start of this task. The existing production task
(`src.tasks.pull_nfl_player_prop_market_snapshots`) only pulls LIVE/current
props, not historical closing lines for completed games, so it can't
answer "would betting the model's favored side at the real closing price
have paid off historically" -- this script fills that gap, once, for a
deliberately small sample (see SAMPLING PLAN below), not as a recurring
production task.

SAMPLING PLAN (see data/ops/nfl-player-prop-vegas-benchmark-report.md for
the full writeup and final numbers)
----------------------------------------------------------------------
- Real completed games, weeks 4-17 (the same walk-forward-eligible window
  as data/ops/nfl-matchup-engine-backtest/backtest_matchup_engine.py --
  needs >=3 trailing real weeks that season; playoffs excluded for the
  same reason), seasons 2023/2024/2025 -- 624 candidate games.
- Every SAMPLE_STRIDE-th game in (season, week, game_date, game_id) order
  -> a sample spread evenly across every season and every week in the
  window, not clustered on one week or one season.
- Markets: player_pass_yds, player_rush_yds, player_reception_yds only
  (the three highest-volume prop types, per task budget guidance) --
  receptions/anytime-TD deliberately excluded to control cost.
- Two real API calls per distinct game date:
    1. `historical/sports/americanfootball_nfl/events?date=<date>T13:30:00Z`
       (well before the earliest realistic NFL kickoff that date) to
       resolve the Odds-API event id + real commence_time for every game
       that date. Cost: 1 credit (0 if no events found).
    2. `historical/sports/americanfootball_nfl/events/{event_id}/odds
       ?date=<real commence_time>` per game -- this asks for the odds
       snapshot AT kickoff, i.e. the real CLOSING line (not an
       open-of-week snapshot). Cost: 10 x [markets actually returned] x
       [1 region] <= 30 credits/game.
- Hard stop if remaining credits drop below MIN_CREDITS_FLOOR (5000) or
  total spend for this pull exceeds MAX_SPEND_BUDGET (3000), even mid-run
  -- partial results persisted so far are kept; nothing is rolled back.

Persists into the EXISTING `nfl_player_prop_market_snapshots` table (its
schema already fit -- no new migration needed) and logs every real call's
cost into the EXISTING `odds_api_credit_ledger` table, reusing the exact
column set `src.tasks._record_odds_api_request` writes (this script talks
to Postgres directly via psycopg, not through the model-service's
SQLAlchemy session, so the insert is hand-written here rather than
importing that function, but the schema/semantics are identical).

`team`/`opponent`/`player_uid` are deliberately left NULL on the inserted
snapshot rows -- exactly the same choice the existing LIVE-props
production task makes (see `pull_nfl_player_prop_market_snapshots` in
src/tasks.py) -- player-name-to-roster resolution is deferred to whatever
consumes this table (here, compute_benchmark.py, which already needs the
real roster/team-context data walk-forward anyway).

Usage: /Users/ryankos/kosedge/.venv/bin/python3 pull_historical_player_props.py
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psycopg
import requests
from psycopg.types.json import Json

DATABASE_URL = "postgresql://ryankos:postgres@127.0.0.1:5432/kosedge"
ENV_FILE = "/Users/ryankos/kosedge/apps/web/.env.local"
BASE_URL = "https://api.the-odds-api.com/v4"
SPORT_KEY = "americanfootball_nfl"

MARKET_KEYS = ["player_pass_yds", "player_rush_yds", "player_reception_yds"]
MARKET_MAP = {
    "player_pass_yds": "pass_yds",
    "player_rush_yds": "rush_yds",
    "player_reception_yds": "rec_yds",
}
PREFERRED_BOOKMAKERS = "draftkings,fanduel"

SEASONS = [2023, 2024, 2025]
WEEK_MIN, WEEK_MAX = 4, 17
SAMPLE_STRIDE = 8  # ~624 candidate games / 8 =~ 78 games sampled

MIN_CREDITS_FLOOR = 5000
MAX_SPEND_BUDGET = 3000
SLEEP_BETWEEN_CALLS = 0.15

OUTPUT_DIR = Path(__file__).parent
RUN_LOG_PATH = OUTPUT_DIR / "pull_run_log.json"

# Full team name (as returned by The Odds API) -> canonical nflverse
# abbreviation used in nfl_dp_schedules. Copied from
# services/model-service/src/tasks.py's NFL_FULL_NAME_TO_ABBR (kept as a
# literal copy, not an import, since this script intentionally has zero
# dependency on the model-service package -- it only talks to Postgres and
# the Odds API directly).
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
}


def load_api_key() -> str:
    for line in Path(ENV_FILE).read_text().splitlines():
        if line.startswith("ODDS_API_KEY=") and not line.startswith("ODDS_API_KEY_"):
            key = line.split("=", 1)[1].strip().strip('"').strip("'")
            if key:
                return key
    raise RuntimeError(f"ODDS_API_KEY not found or empty in {ENV_FILE}")


def _redact(text_: str) -> str:
    return re.sub(r"(apiKey=)[^&\s]+", r"\1REDACTED", str(text_))


def _parse_iso(raw: Optional[str]) -> Optional[datetime]:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


def call_odds_api(endpoint: str, params: Dict[str, Any], api_key: str) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """Returns (payload_or_None, meta). meta always has status/credits_* /
    error, even on failure, so the caller can always log a ledger row."""
    query = {**params, "apiKey": api_key}
    meta: Dict[str, Any] = {
        "status": "failed",
        "credits_last": None,
        "credits_used": None,
        "credits_remaining": None,
        "error": None,
    }
    try:
        resp = requests.get(f"{BASE_URL}/{endpoint}", params=query, timeout=25)
        meta["credits_remaining"] = resp.headers.get("x-requests-remaining")
        meta["credits_used"] = resp.headers.get("x-requests-used")
        meta["credits_last"] = resp.headers.get("x-requests-last")
        resp.raise_for_status()
        meta["status"] = "success"
        return resp.json(), meta
    except requests.HTTPError as exc:
        meta["error"] = _redact(str(exc))
        return None, meta
    except requests.RequestException as exc:
        meta["error"] = _redact(str(exc))
        return None, meta


def record_ledger(
    conn: psycopg.Connection,
    *,
    endpoint: str,
    params: Dict[str, Any],
    meta: Dict[str, Any],
    events_count: int,
    payload: Optional[Dict[str, Any]],
) -> None:
    requested_at = datetime.now(timezone.utc)
    stable_params = {k: str(v) for k, v in sorted(params.items())}
    signature = hashlib.sha256(
        json.dumps({"endpoint": endpoint, "params": stable_params}, sort_keys=True).encode("utf-8")
    ).hexdigest()

    def _to_int(v: Any) -> Optional[int]:
        try:
            return int(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    response_timestamp = _parse_iso(payload.get("timestamp")) if isinstance(payload, dict) else None
    response_previous = _parse_iso(payload.get("previous_timestamp")) if isinstance(payload, dict) else None
    response_next = _parse_iso(payload.get("next_timestamp")) if isinstance(payload, dict) else None

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
            "sport_key": SPORT_KEY,
            "request_signature": signature,
            "requested_at": requested_at,
            "request_params": Json(stable_params),
            "status": meta["status"],
            "source_key": "the-odds-api-historical-props",
            "credits_last": _to_int(meta.get("credits_last")),
            "credits_used": _to_int(meta.get("credits_used")),
            "credits_remaining": _to_int(meta.get("credits_remaining")),
            "events_count": int(events_count),
            "response_timestamp": response_timestamp,
            "response_previous_timestamp": response_previous,
            "response_next_timestamp": response_next,
            "error": meta.get("error"),
        },
    )


def load_sample_games(conn: psycopg.Connection) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT season, week, game_id, game_date, home_team, away_team
        FROM nfl_dp_schedules
        WHERE season = ANY(%(seasons)s)
          AND week BETWEEN %(week_min)s AND %(week_max)s
          AND home_score IS NOT NULL
        ORDER BY season, week, game_date, game_id
        """,
        {"seasons": SEASONS, "week_min": WEEK_MIN, "week_max": WEEK_MAX},
    ).fetchall()
    cols = ["season", "week", "game_id", "game_date", "home_team", "away_team"]
    all_games = [dict(zip(cols, r)) for r in rows]
    sampled = all_games[::SAMPLE_STRIDE]
    return sampled


def _safe_float(value: Any) -> Optional[float]:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> Optional[int]:
    try:
        return int(round(float(value))) if value is not None else None
    except (TypeError, ValueError):
        return None


def _implied_prob(price: Optional[int]) -> Optional[float]:
    if price is None:
        return None
    return (abs(price) / (abs(price) + 100.0)) if price < 0 else (100.0 / (price + 100.0))


def insert_snapshot_rows(conn: psycopg.Connection, *, sample_game: Dict[str, Any], event_id: str, event_commence_time: Optional[datetime], details: Dict[str, Any]) -> int:
    inserted = 0
    snapshot_meta_base = {
        "event_id": event_id,
        "event_commence_time": event_commence_time.isoformat() if event_commence_time else None,
        "queried_home_team": sample_game["home_team"],
        "queried_away_team": sample_game["away_team"],
        "response_home_team": details.get("home_team"),
        "response_away_team": details.get("away_team"),
        "response_timestamp": details.get("_snapshot_timestamp"),
    }
    for bookmaker in details.get("bookmakers") or []:
        sportsbook = str(bookmaker.get("key") or bookmaker.get("title") or "unknown")
        for market in bookmaker.get("markets") or []:
            market_key_raw = str(market.get("key") or "")
            market_key = MARKET_MAP.get(market_key_raw)
            if market_key is None:
                continue
            outcomes = market.get("outcomes") or []
            by_player_line: Dict[Tuple[str, Optional[float]], Dict[str, Any]] = {}
            for outcome in outcomes:
                player_name = str(outcome.get("description") or "").strip()
                if not player_name:
                    continue
                side = str(outcome.get("name") or "").strip().lower()
                point = _safe_float(outcome.get("point"))
                key = (player_name, point)
                row = by_player_line.setdefault(key, {"player_name": player_name, "line": point, "over_price": None, "under_price": None})
                price = _safe_int(outcome.get("price"))
                if side == "over":
                    row["over_price"] = price
                elif side == "under":
                    row["under_price"] = price

            captured_at = _parse_iso(bookmaker.get("last_update")) or event_commence_time or datetime.now(timezone.utc)
            for (player_name, line), row in by_player_line.items():
                implied_over = _implied_prob(row["over_price"])
                implied_under = _implied_prob(row["under_price"])
                metadata = dict(snapshot_meta_base)
                metadata["raw_market_key"] = market_key_raw
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
                        "player_name": player_name,
                        "market_key": market_key,
                        "line": line,
                        "over_price": row["over_price"],
                        "under_price": row["under_price"],
                        "implied_over": implied_over,
                        "implied_under": implied_under,
                        "source": "odds_api_historical",
                        "metadata": Json(metadata),
                    },
                )
                inserted += 1
    return inserted


def main() -> None:
    api_key = load_api_key()
    conn = psycopg.connect(DATABASE_URL, autocommit=True)

    row = conn.execute("SELECT credits_remaining FROM odds_api_credit_ledger ORDER BY requested_at DESC LIMIT 1").fetchone()
    credits_remaining_start = int(row[0]) if row and row[0] is not None else None
    print(f"[budget] credits_remaining at start: {credits_remaining_start}")
    if credits_remaining_start is not None and credits_remaining_start < MIN_CREDITS_FLOOR:
        print("[budget] Already below floor before starting -- aborting.")
        return

    sample_games = load_sample_games(conn)
    print(f"[plan] {len(sample_games)} candidate games sampled (stride={SAMPLE_STRIDE}) from weeks {WEEK_MIN}-{WEEK_MAX}, seasons {SEASONS}")

    by_date: Dict[str, List[Dict[str, Any]]] = {}
    for g in sample_games:
        by_date.setdefault(str(g["game_date"]), []).append(g)
    print(f"[plan] spread across {len(by_date)} distinct game dates")

    run_log: Dict[str, Any] = {
        "credits_remaining_start": credits_remaining_start,
        "games_planned": len(sample_games),
        "dates_planned": len(by_date),
        "games_pulled": [],
        "games_skipped_no_event_match": [],
        "stopped_early_reason": None,
        "credits_remaining_end": credits_remaining_start,
    }

    total_events_inserted = 0
    total_snapshot_rows = 0
    stop = False

    for game_date, games_this_date in sorted(by_date.items()):
        if stop:
            break
        query_dt = f"{game_date}T13:30:00Z"
        events_payload, events_meta = call_odds_api(
            f"historical/sports/{SPORT_KEY}/events",
            {"date": query_dt},
            api_key,
        )
        events_list = (events_payload or {}).get("data") if isinstance(events_payload, dict) else None
        events_list = events_list if isinstance(events_list, list) else []
        record_ledger(
            conn,
            endpoint=f"historical/sports/{SPORT_KEY}/events",
            params={"date": query_dt},
            meta=events_meta,
            events_count=len(events_list),
            payload=events_payload,
        )
        time.sleep(SLEEP_BETWEEN_CALLS)

        if events_meta["credits_remaining"] is not None:
            remaining = int(events_meta["credits_remaining"])
            run_log["credits_remaining_end"] = remaining
            if remaining < MIN_CREDITS_FLOOR:
                run_log["stopped_early_reason"] = f"credits_remaining {remaining} < floor {MIN_CREDITS_FLOOR}"
                print(f"[budget] STOP: {run_log['stopped_early_reason']}")
                stop = True
                break
            if credits_remaining_start is not None and (credits_remaining_start - remaining) > MAX_SPEND_BUDGET:
                run_log["stopped_early_reason"] = f"spend {credits_remaining_start - remaining} > budget cap {MAX_SPEND_BUDGET}"
                print(f"[budget] STOP: {run_log['stopped_early_reason']}")
                stop = True
                break

        events_by_abbr: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for ev in events_list:
            home_full = str(ev.get("home_team") or "")
            away_full = str(ev.get("away_team") or "")
            home_abbr = NFL_FULL_NAME_TO_ABBR.get(home_full)
            away_abbr = NFL_FULL_NAME_TO_ABBR.get(away_full)
            if home_abbr and away_abbr:
                events_by_abbr[(home_abbr, away_abbr)] = ev

        for g in games_this_date:
            if stop:
                break
            event = events_by_abbr.get((g["home_team"], g["away_team"]))
            if event is None:
                run_log["games_skipped_no_event_match"].append(
                    {"season": g["season"], "week": g["week"], "game_id": g["game_id"], "game_date": game_date}
                )
                print(f"[skip] no odds-api event match for {g['season']} wk{g['week']} {g['away_team']}@{g['home_team']} ({game_date})")
                continue

            event_id = str(event.get("id") or "")
            commence_time = _parse_iso(event.get("commence_time"))
            if not event_id or commence_time is None:
                run_log["games_skipped_no_event_match"].append(
                    {"season": g["season"], "week": g["week"], "game_id": g["game_id"], "game_date": game_date}
                )
                continue

            odds_params = {
                "regions": "us",
                "markets": ",".join(MARKET_KEYS),
                "bookmakers": PREFERRED_BOOKMAKERS,
                "oddsFormat": "american",
                "dateFormat": "iso",
                "date": commence_time.isoformat().replace("+00:00", "Z"),
            }
            details_payload, details_meta = call_odds_api(
                f"historical/sports/{SPORT_KEY}/events/{event_id}/odds",
                odds_params,
                api_key,
            )
            details = (details_payload or {}).get("data") if isinstance(details_payload, dict) else None
            if isinstance(details, dict):
                details["_snapshot_timestamp"] = details_payload.get("timestamp") if isinstance(details_payload, dict) else None
            record_ledger(
                conn,
                endpoint=f"historical/sports/{SPORT_KEY}/events/{{eventId}}/odds",
                params=odds_params,
                meta=details_meta,
                events_count=1 if isinstance(details, dict) else 0,
                payload=details_payload,
            )
            time.sleep(SLEEP_BETWEEN_CALLS)

            if details_meta["credits_remaining"] is not None:
                remaining = int(details_meta["credits_remaining"])
                run_log["credits_remaining_end"] = remaining
                if remaining < MIN_CREDITS_FLOOR:
                    run_log["stopped_early_reason"] = f"credits_remaining {remaining} < floor {MIN_CREDITS_FLOOR}"
                    print(f"[budget] STOP: {run_log['stopped_early_reason']}")
                    stop = True
                if credits_remaining_start is not None and (credits_remaining_start - remaining) > MAX_SPEND_BUDGET:
                    run_log["stopped_early_reason"] = f"spend {credits_remaining_start - remaining} > budget cap {MAX_SPEND_BUDGET}"
                    print(f"[budget] STOP: {run_log['stopped_early_reason']}")
                    stop = True

            if isinstance(details, dict) and details_meta["status"] == "success":
                n_rows = insert_snapshot_rows(conn, sample_game=g, event_id=event_id, event_commence_time=commence_time, details=details)
                total_snapshot_rows += n_rows
                total_events_inserted += 1
                run_log["games_pulled"].append(
                    {
                        "season": g["season"],
                        "week": g["week"],
                        "game_id": g["game_id"],
                        "home_team": g["home_team"],
                        "away_team": g["away_team"],
                        "event_id": event_id,
                        "commence_time": commence_time.isoformat(),
                        "snapshot_rows": n_rows,
                        "credits_last": details_meta.get("credits_last"),
                    }
                )
                print(
                    f"[pull] {g['season']} wk{g['week']} {g['away_team']}@{g['home_team']}: "
                    f"{n_rows} snapshot rows, credits_last={details_meta.get('credits_last')}, "
                    f"remaining={details_meta.get('credits_remaining')}"
                )
            else:
                print(f"[error] event-odds pull failed for {g['season']} wk{g['week']} event={event_id}: {details_meta.get('error')}")

    print(f"\n[done] events pulled: {total_events_inserted}/{len(sample_games)}  snapshot rows inserted/updated: {total_snapshot_rows}")
    print(f"[done] credits_remaining_start={credits_remaining_start}  credits_remaining_end={run_log['credits_remaining_end']}")
    if run_log["stopped_early_reason"]:
        print(f"[done] STOPPED EARLY: {run_log['stopped_early_reason']}")

    RUN_LOG_PATH.write_text(json.dumps(run_log, indent=2, default=str))
    print(f"[done] run log written to {RUN_LOG_PATH}")


if __name__ == "__main__":
    main()
