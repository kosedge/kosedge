#!/usr/bin/env python3
"""Integrity checks for NCAAM Path A odds lake (raw JSON + processed parquet).

Coverage, duplicates, event/team identity, timestamps, line/price validity,
missingness, outliers. Research/ops only — no Path B invent, no board writes.

Usage (from apps/web):
  python3 scripts/ncaam_odds_lake_integrity.py --receipt ../../data/ops/ncaam-odds-lake-integrity-20260905.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import polars as pl

WEB = Path(__file__).resolve().parents[1]
if str(WEB) not in sys.path:
    sys.path.insert(0, str(WEB))

from pipeline_paths import ODDS_CLOSE, ODDS_OPEN, ODDS_PARQUET_PATH  # noqa: E402

OPEN_HONESTY_MAX_DRIFT_DAYS = 7
SPREAD_ABS_OUTLIER = 45.0
TOTAL_LO_OUTLIER = 100.0
TOTAL_HI_OUTLIER = 200.0
PRICE_ABS_OUTLIER = 1000


def _parse_ts(ts: Any) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None


def _open_drift_days(payload: dict, file_date: str) -> Optional[float]:
    api_dt = _parse_ts(payload.get("timestamp"))
    if api_dt is None:
        return None
    y, m, d = map(int, file_date.split("-"))
    file_dt = datetime(y, m, d, tzinfo=timezone.utc)
    return abs((api_dt - file_dt).total_seconds()) / 86400.0


def check_raw() -> Dict[str, Any]:
    open_files = sorted(ODDS_OPEN.glob("*.json"))
    close_files = sorted(ODDS_CLOSE.glob("*.json"))
    open_dates = {p.stem for p in open_files}
    close_dates = {p.stem for p in close_files}
    paired = sorted(open_dates & close_dates)
    open_only = sorted(open_dates - close_dates)
    close_only = sorted(close_dates - open_dates)

    dishonest = []
    empty_events = []
    bad_json = []
    for date_str in paired:
        fp = ODDS_OPEN / f"{date_str}.json"
        try:
            payload = json.loads(fp.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            bad_json.append({"date": date_str, "error": str(e)[:80]})
            continue
        drift = _open_drift_days(payload, date_str)
        if drift is None or drift > OPEN_HONESTY_MAX_DRIFT_DAYS:
            dishonest.append({"date": date_str, "drift_days": drift, "ts": payload.get("timestamp")})
        n_events = len(payload.get("data") or [])
        if n_events == 0:
            empty_events.append(date_str)

    ranges: List[Dict[str, Any]] = []
    if paired:
        run_start = paired[0]
        prev = paired[0]
        for d in paired[1:]:
            y1, m1, d1 = map(int, prev.split("-"))
            y2, m2, d2 = map(int, d.split("-"))
            gap = (datetime(y2, m2, d2) - datetime(y1, m1, d1)).days
            if gap != 1:
                ranges.append({"start": run_start, "end": prev, "days": None})
                run_start = d
            prev = d
        ranges.append({"start": run_start, "end": prev, "days": None})
        for r in ranges:
            a = datetime.strptime(r["start"], "%Y-%m-%d").date()
            b = datetime.strptime(r["end"], "%Y-%m-%d").date()
            r["days"] = (b - a).days + 1

    return {
        "n_open_json": len(open_files),
        "n_close_json": len(close_files),
        "n_paired": len(paired),
        "open_only": open_only,
        "close_only": close_only,
        "honesty_fails_gt7d": dishonest,
        "n_honesty_fails": len(dishonest),
        "empty_open_event_days": empty_events,
        "bad_json": bad_json,
        "paired_ranges": ranges,
        "paired_min": paired[0] if paired else None,
        "paired_max": paired[-1] if paired else None,
    }


def check_parquet() -> Dict[str, Any]:
    if not ODDS_PARQUET_PATH.exists():
        return {"error": f"missing {ODDS_PARQUET_PATH}"}
    df = pl.read_parquet(ODDS_PARQUET_PATH)
    cols = set(df.columns)
    n_rows = df.height
    n_events = df["event_id"].n_unique() if "event_id" in cols else None

    book_col = "book" if "book" in cols else ("bookmaker" if "bookmaker" in cols else None)
    dup_keys = []
    for key in (("event_id", book_col, "open_time"), ("event_id", book_col)):
        key_t = tuple(k for k in key if k)
        if key_t and all(k in cols for k in key_t):
            dups = (
                df.group_by(list(key_t))
                .len()
                .filter(pl.col("len") > 1)
                .sort("len", descending=True)
            )
            dup_keys.append(
                {
                    "key": list(key_t),
                    "n_dup_groups": dups.height,
                    "max_count": int(dups["len"].max()) if dups.height else 1,
                }
            )

    # Identity
    null_event = int(df["event_id"].null_count()) if "event_id" in cols else None
    blank_home = int((df["home_team"].cast(pl.Utf8).str.strip_chars() == "").sum()) if "home_team" in cols else None
    blank_away = int((df["away_team"].cast(pl.Utf8).str.strip_chars() == "").sum()) if "away_team" in cols else None
    same_team = (
        int((df["home_team"] == df["away_team"]).sum())
        if "home_team" in cols and "away_team" in cols
        else None
    )

    # Timestamps
    open_span = None
    close_span = None
    if "open_time" in cols:
        ot = df["open_time"].drop_nulls()
        if ot.len():
            open_span = {"min": str(ot.min()), "max": str(ot.max())}
    if "close_time" in cols:
        ct = df["close_time"].drop_nulls()
        if ct.len():
            close_span = {"min": str(ct.min()), "max": str(ct.max())}

    # Line / price validity
    spread_col = next((c for c in ("open_spread_home", "close_spread_home", "spread_home") if c in cols), None)
    total_col = next((c for c in ("open_total", "close_total", "total") if c in cols), None)
    price_cols = [c for c in cols if "price" in c.lower() or "odds" in c.lower()]

    outliers: Dict[str, Any] = {}
    if "close_spread_home" in cols:
        s = df["close_spread_home"].drop_nulls()
        outliers["close_spread_abs_gt_45"] = int((s.abs() > SPREAD_ABS_OUTLIER).sum())
        outliers["close_spread_null"] = int(df["close_spread_home"].null_count())
    if "open_spread_home" in cols:
        s = df["open_spread_home"].drop_nulls()
        outliers["open_spread_abs_gt_45"] = int((s.abs() > SPREAD_ABS_OUTLIER).sum())
        outliers["open_spread_null"] = int(df["open_spread_home"].null_count())
    if "close_total" in cols:
        t = df["close_total"].drop_nulls()
        outliers["close_total_lt_100"] = int((t < TOTAL_LO_OUTLIER).sum())
        outliers["close_total_gt_200"] = int((t > TOTAL_HI_OUTLIER).sum())
        outliers["close_total_null"] = int(df["close_total"].null_count())
    if "open_total" in cols:
        t = df["open_total"].drop_nulls()
        outliers["open_total_lt_100"] = int((t < TOTAL_LO_OUTLIER).sum())
        outliers["open_total_gt_200"] = int((t > TOTAL_HI_OUTLIER).sum())
        outliers["open_total_null"] = int(df["open_total"].null_count())

    price_outlier_n = 0
    for c in price_cols:
        if df[c].dtype in (pl.Int64, pl.Int32, pl.Float64, pl.Float32):
            price_outlier_n += int((df[c].drop_nulls().abs() > PRICE_ABS_OUTLIER).sum())

    missingness = {
        c: {
            "nulls": int(df[c].null_count()),
            "pct": round(float(df[c].null_count()) / n_rows, 4) if n_rows else None,
        }
        for c in (
            "event_id",
            "home_team",
            "away_team",
            "book",
            "bookmaker",
            "open_spread_home",
            "close_spread_home",
            "open_total",
            "close_total",
            "open_time",
            "close_time",
        )
        if c in cols
    }

    # Bookmaker / team frequency sanity
    book_counts = (
        df[book_col].value_counts().sort("count", descending=True).head(15).to_dicts()
        if book_col
        else []
    )

    return {
        "path": str(ODDS_PARQUET_PATH),
        "n_rows": n_rows,
        "n_events": n_events,
        "columns": sorted(cols),
        "duplicates": dup_keys,
        "identity": {
            "null_event_id": null_event,
            "blank_home_team": blank_home,
            "blank_away_team": blank_away,
            "home_eq_away": same_team,
        },
        "timestamps": {"open_time": open_span, "close_time": close_span},
        "outliers": outliers,
        "price_abs_gt_1000_cells": price_outlier_n,
        "missingness": missingness,
        "top_bookmakers": book_counts,
        "spread_col_used": spread_col,
        "total_col_used": total_col,
    }


def grade_integrity(raw: Dict[str, Any], pq: Dict[str, Any]) -> Dict[str, str]:
    grades: Dict[str, str] = {}
    # Coverage
    if raw.get("n_paired", 0) >= 400 and not raw.get("open_only") and not raw.get("close_only"):
        grades["coverage"] = "GREEN"
    elif raw.get("n_paired", 0) >= 200:
        grades["coverage"] = "AMBER"
    else:
        grades["coverage"] = "RED"

    # Honesty
    if raw.get("n_honesty_fails", 0) == 0:
        grades["open_honesty"] = "GREEN"
    elif raw.get("n_honesty_fails", 0) <= 5:
        grades["open_honesty"] = "AMBER"
    else:
        grades["open_honesty"] = "RED"

    # Duplicates — only same-day event/book/open_time collisions are defects.
    # Multi-day event+book rows are expected (game listed across pre-tip snapshots).
    same_day_dups = 0
    for d in (pq.get("duplicates") or []):
        key = d.get("key") or []
        if set(key) >= {"event_id", "open_time"} and ("book" in key or "bookmaker" in key):
            same_day_dups = int(d.get("n_dup_groups") or 0)
    grades["duplicates"] = (
        "GREEN" if same_day_dups == 0 else ("AMBER" if same_day_dups < 50 else "RED")
    )
    grades["duplicates_note"] = (
        "graded on event_id+book+open_time only; multi-day event+book is expected"
    )

    # Identity
    ident = pq.get("identity") or {}
    bad_id = (ident.get("null_event_id") or 0) + (ident.get("blank_home_team") or 0) + (ident.get("blank_away_team") or 0) + (ident.get("home_eq_away") or 0)
    grades["event_team_identity"] = "GREEN" if bad_id == 0 else ("AMBER" if bad_id < 50 else "RED")

    # Timestamps present
    ts = pq.get("timestamps") or {}
    grades["timestamps"] = "GREEN" if ts.get("open_time") and ts.get("close_time") else "RED"

    # Line/price
    out = pq.get("outliers") or {}
    extreme = (out.get("close_spread_abs_gt_45") or 0) + (out.get("close_total_lt_100") or 0) + (out.get("close_total_gt_200") or 0)
    grades["line_price_validity"] = "GREEN" if extreme < 100 else ("AMBER" if extreme < 1000 else "RED")

    # Missingness on close spread
    miss = ((pq.get("missingness") or {}).get("close_spread_home") or {}).get("pct")
    if miss is None:
        grades["missingness"] = "INSUFFICIENT"
    elif miss < 0.05:
        grades["missingness"] = "GREEN"
    elif miss < 0.20:
        grades["missingness"] = "AMBER"
    else:
        grades["missingness"] = "RED"

    grades["outliers"] = grades["line_price_validity"]
    return grades


def main() -> int:
    parser = argparse.ArgumentParser(description="NCAAM Path A odds lake integrity")
    parser.add_argument("--receipt", default=None, help="Write JSON receipt path")
    parser.add_argument("--md", default=None, help="Write markdown ops note path")
    args = parser.parse_args()

    raw = check_raw()
    pq = check_parquet()
    grades = grade_integrity(raw, pq)
    receipt = {
        "task": "NCAAM Path A odds lake integrity",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "path": "A",
        "grades": grades,
        "raw": raw,
        "parquet": pq,
    }

    print(json.dumps({"grades": grades, "n_paired": raw.get("n_paired"), "n_rows": pq.get("n_rows"), "n_events": pq.get("n_events"), "n_honesty_fails": raw.get("n_honesty_fails")}, indent=2))

    if args.receipt:
        Path(args.receipt).parent.mkdir(parents=True, exist_ok=True)
        Path(args.receipt).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        print(f"Receipt: {args.receipt}")

    if args.md:
        lines = [
            "# NCAAM Path A odds lake integrity",
            "",
            f"**Generated:** {receipt['generated_at']}",
            "",
            "## Grades",
            "",
            "| Check | Grade |",
            "| ----- | ----- |",
        ]
        for k, v in grades.items():
            lines.append(f"| {k} | **{v}** |")
        lines += [
            "",
            f"- Paired open/close days: `{raw.get('n_paired')}`",
            f"- Honesty fails (>7d): `{raw.get('n_honesty_fails')}`",
            f"- Parquet rows / events: `{pq.get('n_rows')}` / `{pq.get('n_events')}`",
            f"- Open span: `{((pq.get('timestamps') or {}).get('open_time') or {})}`",
            "",
        ]
        Path(args.md).write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"MD: {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
