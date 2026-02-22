#!/usr/bin/env python3
"""
Fetch historical NCAAB odds for this season through yesterday so the backtest
can include "yesterday" and "this season" once results are matched.

NCAAB season: Nov 1 (previous year) through Apr. We fetch from season start
through yesterday. After this, run process_odds.py, then scrape this season's
results (scrape_cbb_results_espn.py), build_actual_margins.py, merge_games_ensemble.py,
and backtest:kei.

Usage (from apps/web):
  python scripts/pull_odds_this_season.py
  python scripts/pull_odds_this_season.py --dry-run

Requires: ODDS_API_KEY (e.g. in .env.local).
"""
import argparse
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

_WEB = Path(__file__).resolve().parent.parent


def _ncaab_season_start(season: int) -> date:
    """First day of NCAAB season (Nov 1 of previous calendar year)."""
    return date(season - 1, 11, 1)


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch historical odds for this season through yesterday")
    ap.add_argument("--dry-run", action="store_true", help="Print command only, do not run")
    args = ap.parse_args()

    today = date.today()
    yesterday = today - timedelta(days=1)
    # Current season: 2026 if we're in Nov 2025 - Oct 2026
    season = today.year + 1 if today.month >= 11 else today.year
    start = _ncaab_season_start(season)
    # Don't fetch future
    end = min(yesterday, today - timedelta(days=1))
    if start > end:
        # e.g. we're in Oct, season hasn't started
        start = _ncaab_season_start(season - 1)
    start_str = start.isoformat()
    end_str = end.isoformat()

    cmd = [
        sys.executable,
        str(_WEB / "scripts" / "fetch_historical_ncaab_odds.py"),
        "--start", start_str,
        "--end", end_str,
    ]
    print(f"Odds date range: {start_str} through {end_str} (yesterday={yesterday})")
    if args.dry_run:
        print("Dry run. Would run:", " ".join(cmd))
        print("\nThen: process_odds → scrape results (scrape_cbb_results_espn) → build_actual_margins → merge_games_ensemble → backtest:kei")
        return 0

    r = subprocess.run(cmd, cwd=str(_WEB))
    if r.returncode != 0:
        return r.returncode
    print("\nNext steps to get yesterday + this season in the backtest (run from apps/web):")
    print("  1. python src/process_odds.py")
    print("  2. python scrape_cbb_results_espn.py   # or ensure data/raw/games/ has this season results")
    print("  3. python src/build_actual_margins.py")
    print("  4. python src/merge_games_ensemble.py")
    print("  5. pnpm run backtest:kei   # or from repo root: pnpm run backtest:kei")
    return 0


if __name__ == "__main__":
    sys.exit(main())
