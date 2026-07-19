"""Batch 2: grow the real historical player-prop sample with a DIFFERENT,
non-overlapping set of real games from the same candidate pool used by
`pull_historical_player_props.py` (see that file's docstring for the full
sampling-plan rationale -- this file only documents what's different).

Why a second script rather than re-running the first: the first script's
`SAMPLE_STRIDE=8` sampling (`all_games[::8]`, i.e. residue-0-mod-8 games in
(season, week, game_date, game_id) order) already consumed the original
~2,469-credit budget for 78 real games. This follow-up task asks for MORE
real games, non-overlapping with that sample, to test whether the
receiving-yards high-conviction signal found afterward holds up at scale.
Since 624 candidate games / 8 = 78 exactly (no remainder), taking a
DIFFERENT residue class mod 8 -- `SAMPLE_OFFSET=4` (`all_games[4::8]`,
i.e. indices 4, 12, 20, ... 620) -- gives another disjoint 78-game sample,
spread just as evenly across every season/week in the window, with zero
possibility of overlap by construction (residue 4 mod 8 can never equal
residue 0 mod 8). A live DB de-dup guard (`already_pulled_games`) is kept
anyway as a defense-in-depth check in case the candidate list or schedule
data changed between runs.

Usage: /Users/ryankos/kosedge/.venv/bin/python3 pull_historical_player_props_batch2.py
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
SAMPLE_STRIDE = 8
SAMPLE_OFFSET = 4  # disjoint residue class from batch 1's offset-0 sample

MIN_CREDITS_FLOOR = 5000
MAX_SPEND_BUDGET = 3000
SLEEP_BETWEEN_CALLS = 0.15

OUTPUT_DIR = Path(__file__).parent
RUN_LOG_PATH = OUTPUT_DIR / "pull_run_log_batch2.json"

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
        json.dumps({"endpoint": endpoint, "params": stable_params, "batch": "2"}, sort_keys=True).encode("utf-8")
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


def load_already_pulled_games(conn: psycopg.Connection) -> set:
    """(season, week, queried_home_team, queried_away_team) tuples already
    present in nfl_player_prop_market_snapshots, from EITHER batch -- a
    defense-in-depth de-dup guard so this batch never re-spends credits on
    a game already pulled, even if the disjoint-residue guarantee were
    somehow violated by upstream schedule-data changes between runs."""
    rows = conn.execute(
        """
        SELECT DISTINCT season, week, metadata->>'queried_home_team', metadata->>'queried_away_team'
        FROM nfl_player_prop_market_snapshots
        WHERE source = 'odds_api_historical'
        """
    ).fetchall()
    return {(int(r[0]), int(r[1]), r[2], r[3]) for r in rows if r[2] and r[3]}


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
    sampled = all_games[SAMPLE_OFFSET::SAMPLE_STRIDE]

    already = load_already_pulled_games(conn)
    deduped = [g for g in sampled if (g["season"], g["week"], g["home_team"], g["away_team"]) not in already]
    n_dropped = len(sampled) - len(deduped)
    if n_dropped:
        print(f"[dedup] dropped {n_dropped} already-pulled games from the batch-2 plan (defense-in-depth guard fired)")
    return deduped


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
        "pull_batch": 2,
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
    print(f"[plan] {len(sample_games)} candidate games sampled (offset={SAMPLE_OFFSET}, stride={SAMPLE_STRIDE}) from weeks {WEEK_MIN}-{WEEK_MAX}, seasons {SEASONS}")

    by_date: Dict[str, List[Dict[str, Any]]] = {}
    for g in sample_games:
        by_date.setdefault(str(g["game_date"]), []).append(g)
    print(f"[plan] spread across {len(by_date)} distinct game dates")

    run_log: Dict[str, Any] = {
        "batch": 2,
        "sample_offset": SAMPLE_OFFSET,
        "sample_stride": SAMPLE_STRIDE,
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
