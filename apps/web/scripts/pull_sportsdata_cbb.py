#!/usr/bin/env python3
"""
SportsData.io NCAAB free-trial pulls: results, live odds, player props.

Uses your free-trial or production key (1,000 calls/month on trial; ~100/min rate limit).
Data is scrambled in trial but structure matches production — good for pipeline testing,
backtest margin gaps, and a proof-of-concept KosEdge board.

Key: SPORTSDATA_API_KEY or SPORTSDATA_REPLAY_KEY in .env.local or env.

Usage (from apps/web):
  python scripts/pull_sportsdata_cbb.py --results              # season games 2016-2025 (~10 calls)
  python scripts/pull_sportsdata_cbb.py --results --season 2024 # one season (1 call)
  python scripts/pull_sportsdata_cbb.py --today                # today's games + odds (2 calls)
  python scripts/pull_sportsdata_cbb.py --today --date 2025-02-15
  python scripts/pull_sportsdata_cbb.py --props --season 2025   # player season stats + projections (2 calls)

Output:
  data/processed/sportsdata_games_{season}.parquet
  data/processed/all_sportsdata_results_2016-2025.parquet (when --results for 2016-2025)
  data/raw/sportsdata_cbb/games_by_date_{date}.json, game_odds_by_date_{date}.json
  data/raw/sportsdata_cbb/player_season_stats_{season}.json, player_projections_{date}.json
"""
import argparse
import json
import os
import sys
import time
from datetime import date, datetime
from pathlib import Path

import requests

# Paths: run from apps/web or repo root
_WEB = Path(__file__).resolve().parent.parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
from pipeline_paths import PROCESSED, ensure_dirs

BASE_URL = "https://api.sportsdata.io"
# College basketball: try "cbb" first (trial/docs); fallback "ncaab" if 404
_CBB_SLUG = os.environ.get("SPORTSDATA_CBB_SLUG", "cbb")


def _cbb_path(prefix: str) -> str:
    return f"v3/{_CBB_SLUG}/{prefix}"

# Trial: 1,000 calls/month; ~100/min. Be polite.
DELAY_SECONDS = 0.7
CALL_COUNT: list[int] = []  # mutable so we can track


def _load_dotenv() -> None:
    for name in (".env.local", ".env"):
        p = _WEB / name
        if not p.is_file():
            continue
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k = k.strip()
                if k in ("SPORTSDATA_API_KEY", "SPORTSDATA_REPLAY_KEY"):
                    os.environ.setdefault(k, v.strip().strip('"').strip("'"))


def _get_key() -> str:
    return (
        os.environ.get("SPORTSDATA_API_KEY")
        or os.environ.get("SPORTSDATA_REPLAY_KEY")
        or ""
    ).strip()


def _get(path: str, key: str, params: dict | None = None) -> tuple[dict | list | None, int]:
    """GET with key as query param. Returns (data, status_code). Increments CALL_COUNT on request."""
    url = f"{BASE_URL.rstrip('/')}/{path.lstrip('/')}"
    headers = {"Ocp-Apim-Subscription-Key": key}
    r = requests.get(url, params=params or {}, headers=headers, timeout=30)
    CALL_COUNT.append(1)
    if r.status_code != 200:
        return None, r.status_code
    try:
        return r.json(), 200
    except Exception:
        return None, 500


def pull_season_results(season: int, key: str) -> int:
    """Fetch Games/{season}, save parquet. Returns number of games."""
    path = f"{_cbb_path('scores/json')}/Games/{season}"
    data, code = _get(path, key)
    if code != 200 or data is None:
        print(f"  Games/{season}: HTTP {code}")
        return 0
    try:
        import polars as pl
    except ImportError:
        # Fallback: save JSON; user can load elsewhere
        out = PROCESSED / f"sportsdata_games_{season}.json"
        PROCESSED.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        n = len(data) if isinstance(data, list) else 0
        print(f"  Saved {n} games -> {out.name} (no polars; use parquet with pip install polars)")
        return n
    df = pl.DataFrame(data)
    if "HomeTeamScore" in df.columns and "AwayTeamScore" in df.columns:
        df = df.with_columns(
            (pl.col("HomeTeamScore") - pl.col("AwayTeamScore")).alias("actual_home_margin")
        )
    out = PROCESSED / f"sportsdata_games_{season}.parquet"
    PROCESSED.mkdir(parents=True, exist_ok=True)
    df.write_parquet(out)
    print(f"  Saved {len(df)} games -> {out.name}")
    return len(df)


def pull_today_games_and_odds(game_date: date, key: str, raw_dir: Path) -> int:
    """GamesByDate + GameOddsByDate. Saves JSON to raw_dir. Returns total API calls (2)."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    date_str = game_date.strftime("%Y-%m-%d")
    # Games by date
    path_games = f"{_cbb_path('scores/json')}/GamesByDate/{date_str}"
    data_games, code = _get(path_games, key)
    if code == 200 and data_games is not None:
        with open(raw_dir / f"games_by_date_{date_str}.json", "w", encoding="utf-8") as f:
            json.dump(data_games, f, indent=2)
        n = len(data_games) if isinstance(data_games, list) else 0
        print(f"  GamesByDate {date_str}: {n} games -> games_by_date_{date_str}.json")
    else:
        print(f"  GamesByDate {date_str}: HTTP {code}")
    time.sleep(DELAY_SECONDS)
    # Odds by date
    path_odds = f"{_cbb_path('odds/json')}/GameOddsByDate/{date_str}"
    data_odds, code = _get(path_odds, key)
    if code == 200 and data_odds is not None:
        with open(raw_dir / f"game_odds_by_date_{date_str}.json", "w", encoding="utf-8") as f:
            json.dump(data_odds, f, indent=2)
        print(f"  GameOddsByDate {date_str} -> game_odds_by_date_{date_str}.json")
    else:
        print(f"  GameOddsByDate {date_str}: HTTP {code}")
    return 2


def pull_player_stats(season: int, key: str, raw_dir: Path) -> int:
    """PlayerSeasonStats/{season}. One call."""
    path = f"{_cbb_path('stats/json')}/PlayerSeasonStats/{season}"
    data, code = _get(path, key)
    if code != 200 or data is None:
        print(f"  PlayerSeasonStats/{season}: HTTP {code}")
        return 0
    raw_dir.mkdir(parents=True, exist_ok=True)
    with open(raw_dir / f"player_season_stats_{season}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    n = len(data) if isinstance(data, list) else 0
    print(f"  PlayerSeasonStats/{season}: {n} rows -> player_season_stats_{season}.json")
    return 1


def pull_player_projections(game_date: date, key: str, raw_dir: Path) -> int:
    """PlayerGameProjectionStatsByDate/{date}. One call."""
    date_str = game_date.strftime("%Y-%m-%d")
    path = f"{_cbb_path('stats/json')}/PlayerGameProjectionStatsByDate/{date_str}"
    data, code = _get(path, key)
    if code != 200 or data is None:
        print(f"  PlayerGameProjectionStatsByDate/{date_str}: HTTP {code}")
        return 0
    raw_dir.mkdir(parents=True, exist_ok=True)
    with open(raw_dir / f"player_projections_{date_str}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    n = len(data) if isinstance(data, list) else 0
    print(f"  PlayerGameProjectionStatsByDate/{date_str}: {n} rows -> player_projections_{date_str}.json")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description="SportsData.io NCAAB free-trial: results, today, props")
    ap.add_argument("--results", action="store_true", help="Pull season games (default 2016-2025, 10 calls)")
    ap.add_argument("--today", action="store_true", help="Pull today's games + odds (2 calls)")
    ap.add_argument("--props", action="store_true", help="Pull player season stats + projections for --season/--date")
    ap.add_argument("--season", type=int, default=None, help="Season year (e.g. 2024). For --results or --props.")
    ap.add_argument("--date", default=None, help="Date YYYY-MM-DD. Default: today. For --today or --props projections.")
    ap.add_argument("--results-seasons", default="2016-2025", help="For --results: range e.g. 2016-2025 (default)")
    args = ap.parse_args()

    _load_dotenv()
    key = _get_key()
    if not key:
        print("Set SPORTSDATA_API_KEY or SPORTSDATA_REPLAY_KEY in .env.local")
        return 1

    ensure_dirs()
    raw_cbb = _WEB / "data" / "raw" / "sportsdata_cbb"
    raw_cbb.mkdir(parents=True, exist_ok=True)

    if not args.results and not args.today and not args.props:
        print("Use at least one of: --results, --today, --props")
        return 1

    if args.results:
        if args.season:
            seasons = [args.season]
        else:
            lo, hi = args.results_seasons.split("-")[0], args.results_seasons.split("-")[-1]
            seasons = list(range(int(lo), int(hi) + 1))
        print(f"Results: seasons {seasons}")
        for yr in seasons:
            pull_season_results(yr, key)
            time.sleep(DELAY_SECONDS)
        if not args.season and len(seasons) > 1:
            try:
                import polars as pl
                dfs = []
                for yr in seasons:
                    p = PROCESSED / f"sportsdata_games_{yr}.parquet"
                    if p.exists():
                        dfs.append(pl.read_parquet(p))
                if len(dfs) >= 2:
                    all_df = pl.concat(dfs)
                    out = PROCESSED / "all_sportsdata_results_2016-2025.parquet"
                    all_df.write_parquet(out)
                    print(f"  Concatenated {len(all_df)} games -> {out.name}")
                elif len(dfs) == 1:
                    print("  Only one season saved (trial may limit to current season); skipped all_sportsdata_results_2016-2025.parquet")
            except ImportError:
                pass
            except Exception as e:
                print(f"  Concat skip: {e}")

    if args.today:
        game_date = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else date.today()
        print(f"Today: games + odds for {game_date}")
        pull_today_games_and_odds(game_date, key, raw_cbb)

    if args.props:
        season = args.season or date.today().year
        game_date = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else date.today()
        print(f"Props: season {season}, projections date {game_date}")
        pull_player_stats(season, key, raw_cbb)
        time.sleep(DELAY_SECONDS)
        pull_player_projections(game_date, key, raw_cbb)

    n = len(CALL_COUNT)
    print(f"API calls this run: {n} (trial limit 1,000/month)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
