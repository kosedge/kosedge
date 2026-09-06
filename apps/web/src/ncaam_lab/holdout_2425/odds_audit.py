"""Path-A odds / B1 honesty audit for 2024–25 (no API calls)."""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import polars as pl

from ncaam_lab.holdout_2425.constants import ODDS_PARQUET, WINDOW_END, WINDOW_START

_WEB_SRC = Path(__file__).resolve().parents[2]
if str(_WEB_SRC) not in sys.path:
    sys.path.insert(0, str(_WEB_SRC))

from ncaam_identity import odds_name_to_team_norm, resolve_team_id  # noqa: E402


def _parse_ts(raw: Any) -> Optional[datetime]:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def load_odds_event_grain(
    parquet: Path = ODDS_PARQUET,
    *,
    start: date = WINDOW_START,
    end: date = WINDOW_END,
) -> pl.DataFrame:
    df = pl.read_parquet(parquet)
    cols = set(df.columns)
    commence_col = "commence_time" if "commence_time" in cols else "commence_time"
    event_col = "event_id" if "event_id" in cols else "event_id"
    book_col = "book" if "book" in cols else "book"
    open_spread = "open_spread_home" if "open_spread_home" in cols else "open_spread_home"
    close_spread = (
        "close_spread_home" if "close_spread_home" in cols else "close_spread_home"
    )

    df = df.with_columns(
        pl.col(commence_col).cast(pl.Utf8).str.slice(0, 10).alias("tip_date")
    )
    df = df.filter(
        (pl.col("tip_date") >= start.isoformat())
        & (pl.col("tip_date") <= end.isoformat())
    )
    events = df.group_by(event_col).agg(
        [
            pl.col("tip_date").min().alias("tip_date"),
            pl.col(commence_col).min().alias("commence_time"),
            pl.col("home_team").first().alias("home_team"),
            pl.col("away_team").first().alias("away_team"),
            pl.col(book_col).n_unique().alias("n_books"),
            pl.col(open_spread).drop_nulls().len().alias("n_open_spread"),
            pl.col(close_spread).drop_nulls().len().alias("n_close_spread"),
            pl.col("open_time").min().alias("open_time_min"),
            pl.col("close_time").max().alias("close_time_max"),
            pl.len().alias("n_rows"),
        ]
    )
    if event_col != "event_id":
        events = events.rename({event_col: "event_id"})
    return events


def classify_odds_events(
    events: pl.DataFrame,
    schedule_games: List[Dict[str, Any]],
) -> Dict[str, Any]:
    sched_keys: Dict[Tuple[str, str, str], str] = {}
    for g in schedule_games:
        tip = str(g.get("date") or "")[:10]
        home = str(g.get("home") or "")
        away = str(g.get("away") or "")
        if tip and home and away:
            sched_keys[(tip, home, away)] = str(
                g.get("espn_game_id") or g.get("game_id") or ""
            )

    rows: List[Dict[str, Any]] = []
    for rec in events.to_dicts():
        home_raw = rec.get("home_team") or ""
        away_raw = rec.get("away_team") or ""
        home_id = resolve_team_id(home_raw) or odds_name_to_team_norm(home_raw)
        away_id = resolve_team_id(away_raw) or odds_name_to_team_norm(away_raw)
        tip = rec.get("tip_date")
        commence = _parse_ts(rec.get("commence_time"))
        open_ts = _parse_ts(rec.get("open_time_min"))
        close_ts = _parse_ts(rec.get("close_time_max"))

        b1_status = "B1_ELIGIBLE"
        reasons: List[str] = []

        if not home_id or not away_id:
            b1_status = "IDENTITY_UNRESOLVED"
            reasons.append("b7_unresolved")
        if (rec.get("n_open_spread") or 0) <= 0:
            if b1_status == "B1_ELIGIBLE":
                b1_status = "MISSING_OPEN"
            reasons.append("missing_open")
        if (rec.get("n_close_spread") or 0) <= 0:
            if b1_status == "B1_ELIGIBLE":
                b1_status = "MISSING_CLOSE"
            reasons.append("missing_close")

        if commence and close_ts and close_ts >= commence:
            b1_status = "TIMESTAMP_DISHONEST"
            reasons.append("close_not_before_tip")
        if commence and open_ts and open_ts > commence:
            b1_status = "TIMESTAMP_DISHONEST"
            reasons.append("open_after_tip")

        sched_id = None
        if tip and home_id and away_id:
            sched_id = sched_keys.get((str(tip), home_id, away_id)) or None
            if sched_id is None and sched_keys.get((str(tip), away_id, home_id)):
                b1_status = "DUPLICATE_CONFLICT"
                reasons.append("participant_orientation_mismatch")

        rows.append(
            {
                "event_id": rec.get("event_id"),
                "tip_date": tip,
                "home_team_raw": home_raw,
                "away_team_raw": away_raw,
                "home_team_id": home_id,
                "away_team_id": away_id,
                "n_books": rec.get("n_books"),
                "books_present": rec.get("n_books"),
                "n_open_spread": rec.get("n_open_spread"),
                "n_close_spread": rec.get("n_close_spread"),
                "open_snapshot_ts": rec.get("open_time_min"),
                "close_snapshot_ts": rec.get("close_time_max"),
                "open_time_min": rec.get("open_time_min"),
                "close_time_max": rec.get("close_time_max"),
                "b1_status": b1_status,
                "status": b1_status,
                "reasons": reasons,
                "schedule_espn_game_id": sched_id,
                "joined_to_schedule": bool(sched_id),
                "timestamp_honesty_ok": b1_status != "TIMESTAMP_DISHONEST",
            }
        )

    key_counts: Dict[Tuple[str, str, str], int] = {}
    for r in rows:
        if r["home_team_id"] and r["away_team_id"] and r["tip_date"]:
            k = (str(r["tip_date"]), str(r["home_team_id"]), str(r["away_team_id"]))
            key_counts[k] = key_counts.get(k, 0) + 1
    n_dup = sum(1 for n in key_counts.values() if n > 1)
    for r in rows:
        if r["home_team_id"] and r["away_team_id"] and r["tip_date"]:
            k = (str(r["tip_date"]), str(r["home_team_id"]), str(r["away_team_id"]))
            if key_counts.get(k, 0) > 1:
                r["b1_status"] = "DUPLICATE_CONFLICT"
                r["status"] = "DUPLICATE_CONFLICT"
                r["reasons"] = sorted(set(r["reasons"] + ["duplicate_event_grain"]))

    counts: Dict[str, int] = {}
    for r in rows:
        counts[r["b1_status"]] = counts.get(r["b1_status"], 0) + 1

    odds_espn_ids = {
        r["schedule_espn_game_id"] for r in rows if r.get("schedule_espn_game_id")
    }
    n_sched_missing_odds = sum(
        1
        for g in schedule_games
        if str(g.get("espn_game_id") or "") not in odds_espn_ids
    )

    return {
        "n_odds_events_in_window": len(rows),
        "status_counts": counts,
        "n_b1_eligible": sum(1 for r in rows if r["b1_status"] == "B1_ELIGIBLE"),
        "n_joined_to_schedule_sot": sum(1 for r in rows if r["joined_to_schedule"]),
        "n_schedule_events_missing_odds_join": n_sched_missing_odds,
        "n_duplicate_schedule_keys": n_dup,
        "offline_external_drive": {
            "ownership": "USER_CONFIRMED_OWNED_OFFLINE",
            "cloud_availability": "NOT_PRESENT",
            "technical_coverage": "OFFLINE_UNVERIFIED",
        },
        "api_calls_made": False,
        "rows": rows,
        "spread_values_omitted": True,
    }


def index_odds_by_espn_id(odds_audit: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for r in odds_audit.get("rows") or []:
        eid = r.get("schedule_espn_game_id")
        if not eid:
            continue
        prev = out.get(str(eid))
        if prev is None or (
            prev.get("b1_status") != "B1_ELIGIBLE" and r.get("b1_status") == "B1_ELIGIBLE"
        ):
            out[str(eid)] = r
    return out
