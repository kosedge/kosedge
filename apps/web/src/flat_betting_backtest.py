# src/flat_betting_backtest.py
"""
Flat 1-unit backtest on merged parquet. Dedupes by event_id, filters by edge threshold.
Run from apps/web: python src/flat_betting_backtest.py
"""
import sys
from pathlib import Path

import polars as pl

_WEB = Path(__file__).resolve().parent.parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
from pipeline_paths import MERGED_GAMES_PATH, FLAT_BETTING_PICKS_PATH

# Adjustable parameters — consolidated Option A setup
EDGE_THRESHOLD = 6.0
BET_ON_HOME_ONLY = False
FULL_RATINGS_ONLY = True
NIL_ERA_ONLY = True
# Exclude Nov/Dec (games before Jan 1) to reduce look-ahead bias from end-of-season ratings
NO_EARLY_SEASON = True
# Only bet when model win prob > implied (true +EV)
EV_FILTER = True
# Tempo matchup: exclude extreme pace mismatch (|adjt_home - adjt_away| > threshold). None = no filter.
TEMPO_DIFF_MAX = 12.0  # e.g. 12 = drop games where tempo diff > 12; set None to disable
# Rest/travel: only bet when home has rest advantage (>= 1 day) or away traveled 500+ miles. Requires rest_travel.parquet.
REST_TRAVEL_FILTER = True  # when data present; skip if columns missing
# +EV: require model prob to exceed implied by at least this (e.g. 0.05). None = any positive.
EV_MIN_PROB_MARGIN = 0.05
# Totals: edge threshold in points (ensemble_total - line). Run totals backtest when set.
TOTAL_EDGE_THRESHOLD = 4.0  # None = skip totals
# Totals: only bet when both teams have pace data (adjt non-null). More reliable totals.
TOTALS_PACE_QUALITY = True


def main() -> None:
    df = pl.read_parquet(MERGED_GAMES_PATH)

    print(f"Loaded merged parquet: {len(df):,} rows (games × books)")

    deduped = df.unique(subset="event_id", keep="first")
    print(f"Unique games: {len(deduped):,}")

    if FULL_RATINGS_ONLY and "adjem" in deduped.columns and "adjem_away" in deduped.columns:
        before = len(deduped)
        deduped = deduped.filter(pl.col("adjem").is_not_null() & pl.col("adjem_away").is_not_null())
        print(f"Full ratings only: {len(deduped):,} games (dropped {before - len(deduped):,})")

    if NIL_ERA_ONLY:
        deduped = deduped.filter(pl.col("season") >= 2022)
        print(f"NIL era only (season ≥ 2022): {len(deduped):,} games")

    if NO_EARLY_SEASON and "commence_time" in deduped.columns:
        before = len(deduped)
        # commence_time may be str; parse date then exclude Nov/Dec
        month = pl.col("commence_time").str.slice(0, 10).str.to_datetime(strict=False).dt.month()
        deduped = deduped.filter(~month.is_in([11, 12]))
        print(f"No early season (excl. Nov/Dec): {len(deduped):,} games (dropped {before - len(deduped):,})")

    if TEMPO_DIFF_MAX is not None and "tempo_diff" in deduped.columns:
        before = len(deduped)
        deduped = deduped.filter(pl.col("tempo_diff") <= TEMPO_DIFF_MAX)
        print(f"Tempo matchup (tempo_diff ≤ {TEMPO_DIFF_MAX}): {len(deduped):,} games (dropped {before - len(deduped):,})")

    if REST_TRAVEL_FILTER and "days_rest_home" in deduped.columns and "travel_miles_away" in deduped.columns:
        before = len(deduped)
        rest_adv = (pl.col("days_rest_home") - pl.col("days_rest_away")) >= 1
        travel_away = pl.col("travel_miles_away") >= 500
        has_rt = pl.col("days_rest_home").is_not_null() | pl.col("travel_miles_away").is_not_null()
        deduped = deduped.filter(~has_rt | (rest_adv | travel_away))
        print(f"Rest/travel filter (when data: rest adv or away 500+ mi): {len(deduped):,} games (dropped {before - len(deduped):,})")

    line_col = "consensus_close_spread" if "consensus_close_spread" in deduped.columns else "close_spread_home"
    spread_edge_expr = pl.col("ensemble_spread") - pl.col(line_col)
    if line_col != "close_spread_home" or "spread_edge" not in deduped.columns:
        deduped = deduped.with_columns(spread_edge_expr.alias("spread_edge"))
    edge_home_ok = pl.col("spread_edge") >= EDGE_THRESHOLD
    edge_away_ok = (pl.col(line_col) - pl.col("ensemble_spread")) >= EDGE_THRESHOLD
    spread_ok = edge_home_ok | (edge_away_ok if not BET_ON_HOME_ONLY else pl.lit(False))
    if EV_FILTER and "ev_positive_home" in deduped.columns:
        spread_ok = (pl.col("ev_positive_home") & edge_home_ok) | (pl.col("ev_positive_away") & edge_away_ok)
    if EV_FILTER and EV_MIN_PROB_MARGIN is not None and "model_win_prob_home" in deduped.columns and "implied_prob_home" in deduped.columns:
        prob_margin_home = pl.col("model_win_prob_home") - pl.col("implied_prob_home")
        prob_margin_away = pl.col("implied_prob_home") - pl.col("model_win_prob_home")
        spread_ok = spread_ok & (
            (edge_home_ok & (prob_margin_home >= EV_MIN_PROB_MARGIN))
            | (edge_away_ok & (prob_margin_away >= EV_MIN_PROB_MARGIN))
        )

    backtest = deduped.filter(
        pl.col("actual_margin").is_not_null() & spread_ok
    )

    print(f"Games with actual result + edge ≥ {EDGE_THRESHOLD} pts" + (" (+EV only)" if EV_FILTER else "") + f": {len(backtest):,}")

    if len(backtest) == 0:
        print("No qualifying bets. Try lowering EDGE_THRESHOLD or check data.")
        return

    # One bet per game: home if edge_home (and prefer home when both); away if edge_away only
    backtest = backtest.with_columns(
        pl.when(edge_home_ok)
        .then(pl.col("home_cover"))
        .when(edge_away_ok)
        .then(~pl.col("home_cover"))
        .otherwise(None)
        .alias("bet_won")
    )

    backtest = backtest.with_columns(
        pl.when(pl.col("bet_won").is_not_null())
        .then(pl.when(pl.col("bet_won")).then(1.0).otherwise(-1.0))
        .otherwise(pl.lit(None))
        .alias("units")
    )

    valid_bets = backtest.filter(pl.col("bet_won").is_not_null())
    # Which side we bet (when both have edge we take home)
    valid_bets = valid_bets.with_columns(
        pl.when(pl.col("spread_edge") >= EDGE_THRESHOLD).then(pl.lit("home")).otherwise(pl.lit("away")).alias("bet_side")
    )
    n_bets = len(valid_bets)
    ats_pct = valid_bets["bet_won"].mean()
    total_units = valid_bets["units"].sum()
    roi = total_units / n_bets * 100 if n_bets > 0 else 0

    # Diagnostic: home vs away
    by_side = valid_bets.group_by("bet_side").agg(
        pl.len().alias("n"),
        pl.col("bet_won").mean().alias("ats"),
        pl.col("units").sum().alias("units"),
    )
    print("\n--- Home vs Away ---")
    for row in by_side.iter_rows(named=True):
        print(f"Bet {row['bet_side'].upper()}: {row['n']} bets, ATS {row['ats']:.1%}, units {row['units']:.1f}")

    print("\n=== Flat Betting Backtest Results ===")
    print(f"Edge threshold: ≥ {EDGE_THRESHOLD} pts")
    print(f"Bet both sides: {'Yes' if not BET_ON_HOME_ONLY else 'No (home only)'}")
    print(f"Total bets: {n_bets}")
    print(f"ATS hit rate: {ats_pct:.1%}")
    print(f"Total units won/lost (flat 1u): {total_units:.1f}")
    print(f"ROI: {roi:.1f}%")
    print(f"Units per bet: {total_units / n_bets:.2f}" if n_bets > 0 else "N/A")

    print("\nBy season:")
    by_season = valid_bets.group_by("season").agg(
        pl.len().alias("n_bets"),
        pl.col("bet_won").mean().alias("ats_pct"),
        pl.col("units").sum().alias("units"),
    ).with_columns((pl.col("units") / pl.col("n_bets")).alias("units_per_bet")).sort("season")
    print(by_season)

    valid_bets.write_csv(FLAT_BETTING_PICKS_PATH)
    print(f"\nSaved picks to {FLAT_BETTING_PICKS_PATH}")

    # --- Totals backtest (when actual_total and total_edge exist) ---
    if TOTAL_EDGE_THRESHOLD is not None and "total_edge" in deduped.columns and "actual_total" in deduped.columns:
        tot = deduped.filter(
            pl.col("actual_total").is_not_null()
            & (pl.col("total_edge").abs() >= TOTAL_EDGE_THRESHOLD)
        )
        if TOTALS_PACE_QUALITY and "adjt" in tot.columns and "adjt_away" in tot.columns and len(tot) > 0:
            before_tot = len(tot)
            tot = tot.filter(pl.col("adjt").is_not_null() & pl.col("adjt_away").is_not_null())
            if before_tot > len(tot):
                print(f"Totals pace quality: {len(tot):,} games (dropped {before_tot - len(tot):,} missing pace)")
        if len(tot) > 0:
            tot = tot.with_columns(
                pl.when(pl.col("total_edge") > 0)
                .then(pl.col("actual_total") > pl.col("consensus_close_total"))
                .when(pl.col("total_edge") < 0)
                .then(pl.col("actual_total") < pl.col("consensus_close_total"))
                .otherwise(None)
                .alias("total_bet_won")
            )
            tot_valid = tot.filter(pl.col("total_bet_won").is_not_null())
            n_tot = len(tot_valid)
            if n_tot > 0:
                tot_units = tot_valid.with_columns(
                    pl.when(pl.col("total_bet_won")).then(1.0).otherwise(-1.0).alias("u")
                )["u"].sum()
                print("\n=== Totals Backtest ===")
                print(f"Total edge threshold: ≥ {TOTAL_EDGE_THRESHOLD} pts")
                print(f"Bets: {n_tot} | Hit rate: {tot_valid['total_bet_won'].mean():.1%} | Units: {tot_units:.1f}")


if __name__ == "__main__":
    main()
