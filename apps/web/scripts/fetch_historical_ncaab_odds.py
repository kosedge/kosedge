#!/usr/bin/env python3
"""
Fetch NCAAB historical odds (open + close) from The Odds API and save to
data/raw/odds/open/ and data/raw/odds/close/.

Uses ODDS_API_KEY from environment. Historical data is only available from
2020-11-16 for NCAAB. Cost: 20 credits per request (regions=us, markets=spreads,totals);
we do 2 requests per day = 40 credits/day.

Usage (from apps/web):
  export ODDS_API_KEY="your_key"
  python scripts/fetch_historical_ncaab_odds.py
  python scripts/fetch_historical_ncaab_odds.py --start 2024-11-01 --end 2025-02-15
  python scripts/fetch_historical_ncaab_odds.py --dates-file /tmp/dates.txt --force
  python scripts/fetch_historical_ncaab_odds.py --start 2024-01-29 --end 2025-10-31 --max-credits 10000
"""

import argparse
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

BASE_URL = "https://api.the-odds-api.com/v4/historical/sports/basketball_ncaab/odds"
# NCAAB historical data starts 2020-11-16 per Odds API docs
DEFAULT_START = "2020-11-16"
CREDITS_PER_REQUEST = 20  # regions=us (1) * markets=spreads,totals (2) * 10 = 20
OPEN_HONESTY_MAX_DRIFT_DAYS = 7


def parse_args():
    p = argparse.ArgumentParser(description="Fetch NCAAB historical odds (open + close)")
    p.add_argument("--start", default=None, help=f"Start date YYYY-MM-DD (default {DEFAULT_START} if no --dates-file)")
    p.add_argument("--end", default=None, help="End date YYYY-MM-DD (default today)")
    p.add_argument(
        "--dates-file",
        default=None,
        help="Newline-separated YYYY-MM-DD list (overrides --start/--end when set)",
    )
    p.add_argument("--delay", type=float, default=0.35, help="Seconds between requests (default 0.35)")
    p.add_argument("--force", action="store_true", help="Re-fetch even when output file exists")
    p.add_argument(
        "--max-credits",
        type=int,
        default=None,
        help="Stop before exceeding this credit budget (best-effort from x-requests-last)",
    )
    p.add_argument(
        "--drop-dishonest-open",
        action="store_true",
        help="After open fetch, delete open+close for that date if open API timestamp drifts >7d",
    )
    p.add_argument("--receipt", default=None, help="Write JSON receipt path")
    p.add_argument("--dry-run", action="store_true", help="Print requests only, do not fetch")
    return p.parse_args()


def fetch_snapshot(api_key: str, dt: datetime) -> tuple[dict | None, int, str | None, dict]:
    """Fetch one historical snapshot at dt (UTC).

    Returns (response_json, credits_used, error_msg or None, header_meta).
    """
    iso = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    params = {
        "regions": "us",
        "markets": "spreads,totals",
        "oddsFormat": "american",
        "apiKey": api_key,
        "date": iso,
    }
    try:
        r = requests.get(BASE_URL, params=params, timeout=60)
    except requests.RequestException as e:
        return None, 0, str(e)[:80], {}
    credits = int(r.headers.get("x-requests-last", CREDITS_PER_REQUEST) or CREDITS_PER_REQUEST)
    meta = {
        "remaining": r.headers.get("x-requests-remaining"),
        "used": r.headers.get("x-requests-used"),
        "last": r.headers.get("x-requests-last"),
        "status": r.status_code,
    }
    if r.status_code != 200:
        try:
            body = (r.json() or {}).get("message", r.text[:100] if r.text else "")
        except Exception:
            body = r.text[:100] if r.text else ""
        err = f"{r.status_code} {r.reason or ''}".strip()
        if body:
            err += f" — {body}"
        return None, credits, err[:120], meta
    return r.json(), credits, None, meta


def _load_dotenv():
    """Load .env.local or .env from apps/web so ODDS_API_KEY is set if not in env."""
    if os.environ.get("ODDS_API_KEY"):
        return
    root = Path(__file__).resolve().parent.parent
    for name in (".env.local", ".env"):
        path = root / name
        if not path.is_file():
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line and line.split("=", 1)[0].strip() == "ODDS_API_KEY":
                    _key, _, value = line.partition("=")
                    value = value.strip().strip('"').strip("'")
                    if value and value != "[SENSITIVE]":
                        os.environ["ODDS_API_KEY"] = value
                    return


def _parse_dates(args) -> list:
    if args.dates_file:
        dates = []
        for line in Path(args.dates_file).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            dates.append(datetime.strptime(line[:10], "%Y-%m-%d").date())
        return sorted(set(dates))
    start_s = args.start or DEFAULT_START
    start = datetime.strptime(start_s, "%Y-%m-%d").date()
    end = datetime.strptime(args.end, "%Y-%m-%d").date() if args.end else datetime.now(timezone.utc).date()
    if start > end:
        raise SystemExit("Start must be <= end.")
    out = []
    d = start
    while d <= end:
        out.append(d)
        d += timedelta(days=1)
    return out


def _open_drift_days(payload: dict, file_date) -> float | None:
    ts = payload.get("timestamp") if isinstance(payload, dict) else None
    if not ts:
        return None
    try:
        api_dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        file_dt = datetime(file_date.year, file_date.month, file_date.day, tzinfo=timezone.utc)
    except ValueError:
        return None
    return abs((api_dt - file_dt).total_seconds()) / 86400.0


def main():
    _load_dotenv()
    args = parse_args()
    api_key = (os.environ.get("ODDS_API_KEY") or "").strip()
    if not api_key or api_key == "[SENSITIVE]":
        print("Set ODDS_API_KEY in the environment or in apps/web/.env.local")
        return 1

    dates = _parse_dates(args)
    root = Path(__file__).resolve().parent.parent
    import sys
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from pipeline_paths import ODDS_OPEN, ODDS_CLOSE, ensure_dirs
    ensure_dirs()
    open_dir = ODDS_OPEN
    close_dir = ODDS_CLOSE

    total_credits = 0
    days = len(dates)
    estimated_credits = days * 2 * CREDITS_PER_REQUEST
    print(
        f"Dates: {dates[0] if dates else '—'} .. {dates[-1] if dates else '—'} "
        f"({days} days). Estimated credits if all fetched: {estimated_credits} "
        f"(20 per request, 2 per day). force={args.force} max_credits={args.max_credits}"
    )

    receipt = {
        "sport_key": "basketball_ncaab",
        "path": "A",
        "force": bool(args.force),
        "drop_dishonest_open": bool(args.drop_dishonest_open),
        "dates_requested": [d.isoformat() for d in dates],
        "fetched": [],
        "skipped_exists": [],
        "failed": [],
        "dropped_dishonest": [],
        "stopped_for_credits": False,
        "credits_used_headers_sum": 0,
        "credits_remaining_last": None,
        "credits_used_period_last": None,
    }

    if args.dry_run:
        print("Dry run: would request open + close for each day.")
        if args.receipt:
            Path(args.receipt).write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        return 0

    budget_hit = False
    for d in dates:
        if budget_hit:
            break
        date_str = d.strftime("%Y-%m-%d")
        open_ts = datetime(d.year, d.month, d.day, 12, 0, 0)
        close_ts = datetime(d.year, d.month, d.day, 22, 0, 0)
        day_record = {"date": date_str, "open": None, "close": None}

        for label, ts, out_dir in [("open", open_ts, open_dir), ("close", close_ts, close_dir)]:
            if args.max_credits is not None and total_credits >= args.max_credits:
                print(f"  Stop: credit budget reached ({total_credits} >= {args.max_credits})")
                receipt["stopped_for_credits"] = True
                budget_hit = True
                break
            # Leave headroom for the upcoming request
            if args.max_credits is not None and total_credits + CREDITS_PER_REQUEST > args.max_credits:
                print(
                    f"  Stop: next request would exceed budget "
                    f"({total_credits}+{CREDITS_PER_REQUEST} > {args.max_credits})"
                )
                receipt["stopped_for_credits"] = True
                budget_hit = True
                break

            out_file = out_dir / f"{date_str}.json"
            if out_file.exists() and not args.force:
                print(f"  Skip {date_str} {label} (exists)")
                receipt["skipped_exists"].append(f"{date_str}:{label}")
                continue
            data, used, err, meta = fetch_snapshot(api_key, ts)
            total_credits += used
            receipt["credits_used_headers_sum"] = total_credits
            if meta.get("remaining") is not None:
                receipt["credits_remaining_last"] = meta.get("remaining")
            if meta.get("used") is not None:
                receipt["credits_used_period_last"] = meta.get("used")
            if data is None:
                print(f"  Fail {date_str} {label}" + (f" ({err})" if err else ""))
                receipt["failed"].append({"date": date_str, "label": label, "error": err})
                continue
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            n_events = len(data.get("data", []))
            api_ts = data.get("timestamp")
            print(f"  {date_str} {label}: {n_events} events ts={api_ts} -> {out_file.name} (+{used})")
            day_record[label] = {"events": n_events, "timestamp": api_ts, "credits": used}
            time.sleep(args.delay)

        if day_record["open"] or day_record["close"]:
            receipt["fetched"].append(day_record)

        if args.drop_dishonest_open and not budget_hit:
            open_fp = open_dir / f"{date_str}.json"
            if open_fp.exists():
                try:
                    payload = json.loads(open_fp.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    payload = None
                drift = _open_drift_days(payload, d) if payload else None
                if drift is None or drift > OPEN_HONESTY_MAX_DRIFT_DAYS:
                    for p in (open_dir / f"{date_str}.json", close_dir / f"{date_str}.json"):
                        if p.exists():
                            p.unlink()
                    print(
                        f"  Drop {date_str}: open timestamp drift "
                        f"{None if drift is None else round(drift, 1)}d > {OPEN_HONESTY_MAX_DRIFT_DAYS}d"
                    )
                    receipt["dropped_dishonest"].append(
                        {"date": date_str, "drift_days": drift, "open_timestamp": (payload or {}).get("timestamp")}
                    )

    print(f"Done. Total credits used this run (header sum): ~{total_credits}")
    if args.receipt:
        Path(args.receipt).parent.mkdir(parents=True, exist_ok=True)
        Path(args.receipt).write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        print(f"Receipt: {args.receipt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
