"""Batch 6: densify 2025 W16-17 (and any missing residue) for product board.

Pulls every scheduled game not already in DB for those weeks.
Persists team/opponent on insert. Includes receptions.
DB-first de-dupe. Credits floor 400.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import psycopg
import requests
from psycopg.types.json import Json

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services" / "model-service"))
from src.services.nfl_player_identity import (  # noqa: E402
    prop_market_position_compatible,
    prop_market_position_rank,
    prop_player_match_keys,
)

DATABASE_URL = "postgresql://ryankos:postgres@127.0.0.1:5432/kosedge"
ENV_FILE = "/Users/ryankos/kosedge/apps/web/.env.local"
BASE_URL = "https://api.the-odds-api.com/v4"
SPORT_KEY = "americanfootball_nfl"

MARKET_KEYS = [
    "player_pass_yds",
    "player_rush_yds",
    "player_reception_yds",
    "player_receptions",
]
MARKET_MAP = {
    "player_pass_yds": "pass_yds",
    "player_rush_yds": "rush_yds",
    "player_reception_yds": "rec_yds",
    "player_receptions": "receptions",
}
PREFERRED_BOOKMAKERS = "draftkings,fanduel"

TARGET_WEEKS = [(2025, 16), (2025, 17)]
MIN_CREDITS_FLOOR = 400
MAX_SPEND_BUDGET = 900
SLEEP_BETWEEN_CALLS = 0.20

OUTPUT_DIR = Path(__file__).parent
RUN_LOG_PATH = OUTPUT_DIR / "pull_run_log_batch6_densify.json"

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
    raise RuntimeError(f"ODDS_API_KEY not found in {ENV_FILE}")


def _parse_iso(raw: Optional[str]) -> Optional[datetime]:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


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
        resp = requests.get(f"{BASE_URL}/{endpoint}", params=query, timeout=45)
        meta["credits_last"] = _safe_int(resp.headers.get("x-requests-last"))
        meta["credits_used"] = _safe_int(resp.headers.get("x-requests-used"))
        meta["credits_remaining"] = _safe_int(resp.headers.get("x-requests-remaining"))
        if resp.status_code != 200:
            meta["error"] = f"HTTP {resp.status_code}: {resp.text[:300]}"
            return None, meta
        meta["status"] = "success"
        return resp.json(), meta
    except Exception as exc:  # noqa: BLE001
        meta["error"] = str(exc)
        return None, meta


def record_ledger(
    conn: psycopg.Connection,
    *,
    endpoint: str,
    params: Dict[str, Any],
    meta: Dict[str, Any],
    events_count: int,
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    requested_at = datetime.now(timezone.utc)
    stable_params = {k: str(v) for k, v in sorted(params.items()) if k != "apiKey"}
    signature = hashlib.sha256(
        json.dumps({"endpoint": endpoint, "params": stable_params, "batch": "6"}, sort_keys=True).encode("utf-8")
    ).hexdigest()
    conn.execute(
        """
        INSERT INTO odds_api_credit_ledger (
          endpoint, sport_key, request_signature, requested_at, request_params,
          status, source_key, credits_last, credits_used, credits_remaining,
          events_count, error, created_at
        ) VALUES (
          %(endpoint)s, %(sport_key)s, %(request_signature)s, %(requested_at)s, %(request_params)s,
          %(status)s, %(source_key)s, %(credits_last)s, %(credits_used)s, %(credits_remaining)s,
          %(events_count)s, %(error)s, %(requested_at)s
        )
        """,
        {
            "endpoint": endpoint,
            "sport_key": SPORT_KEY,
            "request_signature": signature,
            "requested_at": requested_at,
            "request_params": Json(stable_params),
            "status": meta["status"],
            "source_key": "the-odds-api-historical-props-batch6",
            "credits_last": _safe_int(meta.get("credits_last")),
            "credits_used": _safe_int(meta.get("credits_used")),
            "credits_remaining": _safe_int(meta.get("credits_remaining")),
            "events_count": int(events_count),
            "error": meta.get("error"),
        },
    )


def load_already_pulled(conn: psycopg.Connection) -> Set[Tuple[int, int, str, str]]:
    rows = conn.execute(
        """
        SELECT DISTINCT season, week, metadata->>'queried_home_team', metadata->>'queried_away_team'
        FROM nfl_player_prop_market_snapshots
        WHERE source = 'odds_api_historical'
          AND metadata ? 'queried_home_team'
        """
    ).fetchall()
    return {(int(r[0]), int(r[1]), r[2], r[3]) for r in rows if r[2] and r[3]}


def load_target_games(conn: psycopg.Connection) -> List[Dict[str, Any]]:
    already = load_already_pulled(conn)
    out: List[Dict[str, Any]] = []
    for season, week in TARGET_WEEKS:
        rows = conn.execute(
            """
            SELECT season, week, game_id, game_date, home_team, away_team
            FROM nfl_dp_schedules
            WHERE season = %s AND week = %s AND home_score IS NOT NULL
            ORDER BY game_date, game_id
            """,
            (season, week),
        ).fetchall()
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
            if key not in already:
                out.append(g)
    return out


def resolve_player_team(
    roster: List[Tuple[str, str, str, Set[str]]],
    *,
    player_name: str,
    market_key: str,
    home: str,
    away: str,
) -> Optional[str]:
    m_keys = set(prop_player_match_keys(player_uid=None, player_name=player_name))
    candidates = []
    for team, pos, _name, b_keys in roster:
        if not (m_keys & b_keys):
            continue
        if team not in {home, away}:
            continue
        if not prop_market_position_compatible(market_key, pos):
            continue
        candidates.append((team, pos))
    if not candidates:
        return None
    candidates.sort(key=lambda c: prop_market_position_rank(market_key, c[1]))
    best = prop_market_position_rank(market_key, candidates[0][1])
    top = [c for c in candidates if prop_market_position_rank(market_key, c[1]) == best]
    teams = {c[0] for c in top}
    return top[0][0] if len(teams) == 1 else None


def insert_snapshot_rows(
    conn: psycopg.Connection,
    *,
    sample_game: Dict[str, Any],
    event_id: str,
    event_commence_time: Optional[datetime],
    details: Dict[str, Any],
    roster: List[Tuple[str, str, str, Set[str]]],
) -> int:
    inserted = 0
    home = str(sample_game["home_team"])
    away = str(sample_game["away_team"])
    snapshot_meta_base = {
        "event_id": event_id,
        "event_commence_time": event_commence_time.isoformat() if event_commence_time else None,
        "queried_home_team": home,
        "queried_away_team": away,
        "response_home_team": details.get("home_team"),
        "response_away_team": details.get("away_team"),
        "response_timestamp": details.get("_snapshot_timestamp"),
        "pull_batch": 6,
    }
    for bookmaker in details.get("bookmakers") or []:
        sportsbook = str(bookmaker.get("key") or bookmaker.get("title") or "unknown")
        for market in bookmaker.get("markets") or []:
            market_key_raw = str(market.get("key") or "")
            market_key = MARKET_MAP.get(market_key_raw)
            if market_key is None:
                continue
            by_player_line: Dict[Tuple[str, Optional[float]], Dict[str, Any]] = {}
            for outcome in market.get("outcomes") or []:
                player_name = str(outcome.get("description") or "").strip()
                if not player_name:
                    continue
                side = str(outcome.get("name") or "").strip().lower()
                point = _safe_float(outcome.get("point"))
                key = (player_name, point)
                row = by_player_line.setdefault(
                    key, {"player_name": player_name, "line": point, "over_price": None, "under_price": None}
                )
                price = _safe_int(outcome.get("price"))
                if side == "over":
                    row["over_price"] = price
                elif side == "under":
                    row["under_price"] = price

            captured_at = _parse_iso(bookmaker.get("last_update")) or event_commence_time or datetime.now(timezone.utc)
            for (player_name, line), row in by_player_line.items():
                team = resolve_player_team(
                    roster, player_name=player_name, market_key=market_key, home=home, away=away
                )
                opponent = None
                if team == home:
                    opponent = away
                elif team == away:
                    opponent = home
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
                      NULL, %(player_name)s, %(team)s, %(opponent)s, %(market_key)s, %(line)s,
                      %(over_price)s, %(under_price)s, %(implied_over)s, %(implied_under)s,
                      %(source)s, %(metadata)s, NOW()
                    )
                    ON CONFLICT (sportsbook, captured_at, player_name, market_key, COALESCE(line, -9999))
                    DO UPDATE SET
                      team = COALESCE(EXCLUDED.team, nfl_player_prop_market_snapshots.team),
                      opponent = COALESCE(EXCLUDED.opponent, nfl_player_prop_market_snapshots.opponent),
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
                        "team": team,
                        "opponent": opponent,
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


def load_roster(conn: psycopg.Connection, season: int, week: int) -> List[Tuple[str, str, str, Set[str]]]:
    rows = conn.execute(
        """
        SELECT team, position, player_name
        FROM nfl_player_projection_baselines
        WHERE season = %s AND week = %s
        """,
        (season, week),
    ).fetchall()
    out = []
    for team, pos, name in rows:
        keys = set(prop_player_match_keys(player_uid=None, player_name=str(name or "")))
        out.append((str(team or ""), str(pos or ""), str(name or ""), keys))
    return out


def main() -> None:
    api_key = load_api_key()
    conn = psycopg.connect(DATABASE_URL, autocommit=True)
    row = conn.execute("SELECT credits_remaining FROM odds_api_credit_ledger ORDER BY requested_at DESC LIMIT 1").fetchone()
    credits_start = int(row[0]) if row and row[0] is not None else None
    print(f"[budget] credits_remaining start={credits_start}")
    if credits_start is not None and credits_start < MIN_CREDITS_FLOOR:
        print("[budget] below floor — abort")
        return

    games = load_target_games(conn)
    print(f"[plan] {len(games)} games missing from DB for {TARGET_WEEKS}")
    by_date: Dict[str, List[Dict[str, Any]]] = {}
    for g in games:
        by_date.setdefault(str(g["game_date"]), []).append(g)

    run_log: Dict[str, Any] = {
        "batch": 6,
        "purpose": "densify_board_weeks_2025_w16_w17",
        "credits_remaining_start": credits_start,
        "games_planned": len(games),
        "games_pulled": [],
        "games_skipped_no_event_match": [],
        "stopped_early_reason": None,
        "credits_remaining_end": credits_start,
        "snapshot_rows": 0,
    }
    stop = False
    roster_cache: Dict[Tuple[int, int], List[Any]] = {}

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
            payload=events_payload if isinstance(events_payload, dict) else None,
        )
        time.sleep(SLEEP_BETWEEN_CALLS)
        remaining = events_meta.get("credits_remaining")
        if remaining is not None:
            run_log["credits_remaining_end"] = int(remaining)
            if int(remaining) < MIN_CREDITS_FLOOR:
                run_log["stopped_early_reason"] = f"floor {remaining}"
                stop = True
                break
            if credits_start is not None and (credits_start - int(remaining)) > MAX_SPEND_BUDGET:
                run_log["stopped_early_reason"] = "spend_cap"
                stop = True
                break

        events_by_abbr: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for ev in events_list:
            home_abbr = NFL_FULL_NAME_TO_ABBR.get(str(ev.get("home_team") or ""))
            away_abbr = NFL_FULL_NAME_TO_ABBR.get(str(ev.get("away_team") or ""))
            if home_abbr and away_abbr:
                events_by_abbr[(home_abbr, away_abbr)] = ev

        for g in games_this_date:
            if stop:
                break
            event = events_by_abbr.get((g["home_team"], g["away_team"]))
            if event is None:
                run_log["games_skipped_no_event_match"].append(g)
                print(f"[skip] no event {g['away_team']}@{g['home_team']} {game_date}")
                continue
            event_id = str(event.get("id") or "")
            commence = _parse_iso(event.get("commence_time"))
            if not event_id or commence is None:
                run_log["games_skipped_no_event_match"].append(g)
                continue

            odds_params = {
                "regions": "us",
                "markets": ",".join(MARKET_KEYS),
                "bookmakers": PREFERRED_BOOKMAKERS,
                "oddsFormat": "american",
                "dateFormat": "iso",
                "date": commence.isoformat().replace("+00:00", "Z"),
            }
            details_payload, details_meta = call_odds_api(
                f"historical/sports/{SPORT_KEY}/events/{event_id}/odds",
                odds_params,
                api_key,
            )
            details = (details_payload or {}).get("data") if isinstance(details_payload, dict) else None
            if isinstance(details, dict) and isinstance(details_payload, dict):
                details["_snapshot_timestamp"] = details_payload.get("timestamp")
            record_ledger(
                conn,
                endpoint=f"historical/sports/{SPORT_KEY}/events/{{eventId}}/odds",
                params=odds_params,
                meta=details_meta,
                events_count=1 if isinstance(details, dict) else 0,
                payload=details_payload if isinstance(details_payload, dict) else None,
            )
            time.sleep(SLEEP_BETWEEN_CALLS)
            remaining = details_meta.get("credits_remaining")
            if remaining is not None:
                run_log["credits_remaining_end"] = int(remaining)
                if int(remaining) < MIN_CREDITS_FLOOR:
                    run_log["stopped_early_reason"] = f"floor {remaining}"
                    stop = True
                if credits_start is not None and (credits_start - int(remaining)) > MAX_SPEND_BUDGET:
                    run_log["stopped_early_reason"] = "spend_cap"
                    stop = True

            if isinstance(details, dict) and details_meta["status"] == "success":
                rk = (int(g["season"]), int(g["week"]))
                if rk not in roster_cache:
                    roster_cache[rk] = load_roster(conn, rk[0], rk[1])
                n = insert_snapshot_rows(
                    conn,
                    sample_game=g,
                    event_id=event_id,
                    event_commence_time=commence,
                    details=details,
                    roster=roster_cache[rk],
                )
                run_log["snapshot_rows"] += n
                run_log["games_pulled"].append(
                    {"season": g["season"], "week": g["week"], "home": g["home_team"], "away": g["away_team"], "rows": n}
                )
                print(f"[ok] {g['season']} W{g['week']} {g['away_team']}@{g['home_team']} +{n} rows; credits={remaining}")

    RUN_LOG_PATH.write_text(json.dumps(run_log, indent=2, default=str) + "\n")
    print(f"[done] pulled={len(run_log['games_pulled'])} rows={run_log['snapshot_rows']} credits_end={run_log['credits_remaining_end']}")
    print(f"[log] {RUN_LOG_PATH}")
    conn.close()


if __name__ == "__main__":
    main()
