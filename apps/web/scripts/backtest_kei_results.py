"""
KEI model backtest: winning percentage and ROI for spread bets (model side vs close).
Segments: yesterday's games, this season's games, all historical games with odds + results.
Logs results to data/processed/kei_backtest_results.json.

Bet rule: bet home when ensemble_spread > consensus_close_spread, else away (flat 1u).
Requires: merged_games_with_odds_and_ratings.parquet with actual_margin (run merge_games_ensemble after build_actual_margins or results).
Run from apps/web: python scripts/backtest_kei_results.py
"""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import polars as pl

_WEB = Path(__file__).resolve().parent.parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
from pipeline_paths import MERGED_GAMES_PATH, PROCESSED, KEI_BACKTEST_RESULTS_PATH


def _current_ncaab_season() -> int:
    """Current NCAAB season (e.g. Nov 2024 -> 2025)."""
    today = date.today()
    return today.year + 1 if today.month >= 11 else today.year


def _run_segment(
    df: pl.DataFrame,
    line_col: str,
    label: str,
) -> dict:
    """Compute win%, ROI, n_games for a segment. Bet model side (home when model > line, else away)."""
    if df.is_empty():
        return {
            "label": label,
            "n_games": 0,
            "wins": 0,
            "win_pct": None,
            "total_units": 0.0,
            "roi_pct": None,
        }
    # Model side: home if ensemble_spread > close_spread, else away
    df = df.with_columns(
        (pl.col("ensemble_spread") > pl.col(line_col)).alias("bet_home")
    )
    df = df.with_columns(
        pl.when(pl.col("bet_home"))
        .then(pl.col("home_cover"))
        .otherwise(~pl.col("home_cover"))
        .alias("bet_won")
    )
    df = df.with_columns(
        pl.when(pl.col("bet_won")).then(1.0).otherwise(-1.0).alias("units")
    )
    n = len(df)
    wins = int(df["bet_won"].sum())
    total_units = float(df["units"].sum())
    win_pct = (wins / n * 100) if n else None
    roi_pct = (total_units / n * 100) if n else None
    return {
        "label": label,
        "n_games": n,
        "wins": wins,
        "win_pct": round(win_pct, 2) if win_pct is not None else None,
        "total_units": round(total_units, 2),
        "roi_pct": round(roi_pct, 2) if roi_pct is not None else None,
    }


def main() -> None:
    if not MERGED_GAMES_PATH.exists():
        print(f"Merged parquet not found: {MERGED_GAMES_PATH}")
        print("Run: python src/merge_games_ensemble.py (after build_ensemble_ratings + odds + actual_margins/results).")
        # Write empty log so downstream knows we ran
        PROCESSED.mkdir(parents=True, exist_ok=True)
        with open(KEI_BACKTEST_RESULTS_PATH, "w") as f:
            json.dump({"error": "merged parquet not found", "segments": {}}, f, indent=2)
        return

    df = pl.read_parquet(MERGED_GAMES_PATH)
    deduped = df.unique(subset="event_id", keep="first")

    if "actual_margin" not in deduped.columns:
        print("No actual_margin in merged data. Run merge with actual_margins.parquet or data/raw/games/results.csv.")
        PROCESSED.mkdir(parents=True, exist_ok=True)
        with open(KEI_BACKTEST_RESULTS_PATH, "w") as f:
            json.dump({"error": "no actual_margin", "segments": {}}, f, indent=2)
        return

    # game_date and season
    if "game_date" not in deduped.columns and "commence_time" in deduped.columns:
        deduped = deduped.with_columns(
            pl.col("commence_time").str.slice(0, 10).str.to_date(strict=False).alias("game_date")
        )
    if "season" not in deduped.columns and "commence_time" in deduped.columns:
        date_str = pl.col("commence_time").str.slice(0, 10)
        dt = date_str.str.to_datetime(format="%Y-%m-%d")
        y, m = dt.dt.year(), dt.dt.month()
        deduped = deduped.with_columns(pl.when(m >= 11).then(y + 1).otherwise(y).alias("season"))

    line_col = "consensus_close_spread" if "consensus_close_spread" in deduped.columns else "close_spread_home"
    if line_col not in deduped.columns:
        print(f"Missing line column {line_col}. Cannot run backtest.")
        return

    # home_cover: actual_margin + close_spread > 0
    if "home_cover" not in deduped.columns:
        deduped = deduped.with_columns(
            (pl.col("actual_margin") + pl.col(line_col) > 0).alias("home_cover")
        )

    with_results = deduped.filter(pl.col("actual_margin").is_not_null())
    # Log date coverage so we can see why yesterday/this_season might be empty
    game_date_str = pl.col("game_date").cast(pl.Utf8) if "game_date" in deduped.columns else None
    if game_date_str is not None:
        odds_dates = deduped.filter(pl.col("game_date").is_not_null()).select(pl.col("game_date"))
        if not odds_dates.is_empty():
            min_od, max_od = odds_dates.min().item(), odds_dates.max().item()
            log_odds_range = f"{min_od!s} to {max_od!s}"
        else:
            log_odds_range = "no dates"
    else:
        log_odds_range = "no game_date"
    results_date_range = None
    if not with_results.is_empty() and "game_date" in with_results.columns:
        rd = with_results.select(pl.col("game_date")).filter(pl.col("game_date").is_not_null())
        if not rd.is_empty():
            results_date_range = f"{rd.min().item()!s} to {rd.max().item()!s}"

    if with_results.is_empty():
        print("No games with actual_margin. Add actual_margins.parquet or results.csv and re-run merge.")
        segments = {}
    else:
        yesterday_str = (date.today() - timedelta(days=1)).isoformat()
        this_season = _current_ncaab_season()

        yesterday = with_results.filter(pl.col("game_date").cast(pl.Utf8) == yesterday_str)
        this_year = with_results.filter(pl.col("season") == this_season)
        all_time = with_results

        segments = {
            "yesterday": _run_segment(yesterday, line_col, f"Yesterday ({yesterday_str})"),
            "this_season": _run_segment(this_year, line_col, f"This season ({this_season})"),
            "all_historical": _run_segment(all_time, line_col, "All games (historical odds + results)"),
        }

    # Log to JSON
    log = {
        "run_date": date.today().isoformat(),
        "merged_path": str(MERGED_GAMES_PATH),
        "total_events_in_merged": len(deduped),
        "events_with_actual_margin": len(with_results),
        "odds_date_range": log_odds_range,
        "results_date_range": results_date_range,
        "segments": segments,
    }
    PROCESSED.mkdir(parents=True, exist_ok=True)
    with open(KEI_BACKTEST_RESULTS_PATH, "w") as f:
        json.dump(log, f, indent=2)

    # Print summary
    print("=== KEI model backtest (model side vs close, flat 1u) ===")
    print(f"Logged to {KEI_BACKTEST_RESULTS_PATH}")
    print(f"Odds date range: {log_odds_range}  |  Results range: {results_date_range or 'n/a'}")
    print(f"Games with results: {log['events_with_actual_margin']:,}")
    for key, seg in segments.items():
        s = seg
        n = s["n_games"]
        if n == 0:
            print(f"  {s['label']}: no games")
        else:
            print(f"  {s['label']}: n={n}  Win%={s['win_pct']}%  ROI={s['roi_pct']}%  Units={s['total_units']:+.1f}")
    # Hint when yesterday or this season have no data
    if segments.get("yesterday", {}).get("n_games", 0) == 0 or segments.get("this_season", {}).get("n_games", 0) == 0:
        print("\nTo include yesterday + this season: run pnpm run pull:odds-this-season (or fetch_historical_ncaab_odds for this season through yesterday),")
        print("  then process_odds, scrape this season results (scrape_cbb_results_espn), build_actual_margins, merge_games_ensemble, backtest:kei.")


if __name__ == "__main__":
    main()
