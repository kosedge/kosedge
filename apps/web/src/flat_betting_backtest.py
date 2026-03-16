# src/flat_betting_backtest.py
"""
Flat 1-unit backtest on merged parquet. Dedupes by event_id, filters by edge threshold.

Run from apps/web:
  python src/flat_betting_backtest.py                  # default profile
  python src/flat_betting_backtest.py --profile base   # same as default
  python src/flat_betting_backtest.py --profile tight  # higher edge + situational filters
"""
import sys
import argparse
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
# Situational filters
HOME_DOG_ONLY = False          # when True, only bet home underdogs (consensus_close_spread > 0)
TEMPO_MIN = None               # e.g. 68.0 to restrict to high-tempo games (adjt >= TEMPO_MIN)
INJURY_FILTER = False          # when True and injury flags present, skip games with key_player_out_home/away
# Rest/travel: only bet when home has rest advantage (>= 1 day) or away traveled 500+ miles. Requires rest_travel.parquet.
REST_TRAVEL_FILTER = True      # when data present; skip if columns missing
# +EV: require model prob to exceed implied by at least this (e.g. 0.05). None = any positive.
EV_MIN_PROB_MARGIN = 0.05
# Totals: edge threshold in points (ensemble_total - line). Run totals backtest when set.
TOTAL_EDGE_THRESHOLD = 4.0     # None = skip totals
# Totals: only bet when both teams have pace data (adjt non-null). More reliable totals.
TOTALS_PACE_QUALITY = True


def apply_profile(profile: str) -> None:
    """
    Named profiles for quick experimentation.

    base: current defaults (EDGE_THRESHOLD=6, rest/travel, NIL era, etc.)
    tight: higher edge + situational filters (home dogs, high tempo).
    """
    global EDGE_THRESHOLD, HOME_DOG_ONLY, TEMPO_MIN, INJURY_FILTER

    if profile in ("base", "default", ""):
        # Leave globals as-is (defaults defined above)
        return

    if profile == "tight":
        EDGE_THRESHOLD = 7.0
        HOME_DOG_ONLY = True
        TEMPO_MIN = 68.0
        # Keep INJURY_FILTER off until injury.parquet is populated reliably
        INJURY_FILTER = False
        return

    print(f"Unknown profile '{profile}'. Using defaults.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Flat 1-unit NCAAB backtest with presets.")
    ap.add_argument(
        "--profile",
        default="base",
        help="Backtest profile to use (e.g. 'base', 'tight').",
    )
    args = ap.parse_args()

    apply_profile(args.profile)

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

    if HOME_DOG_ONLY and "consensus_close_spread" in deduped.columns:
        before = len(deduped)
        deduped = deduped.filter(pl.col("consensus_close_spread") > 0)
        print(f"Home dogs only (consensus_close_spread > 0): {len(deduped):,} games (dropped {before - len(deduped):,})")

    if TEMPO_MIN is not None and "adjt" in deduped.columns:
        before = len(deduped)
        deduped = deduped.filter(pl.col("adjt") >= TEMPO_MIN)
        print(f"High tempo only (adjt ≥ {TEMPO_MIN}): {len(deduped):,} games (dropped {before - len(deduped):,})")

    if INJURY_FILTER and "key_player_out_home" in deduped.columns and "key_player_out_away" in deduped.columns:
        before = len(deduped)
        # Only bet when we do NOT have a key player flagged out on either side
        deduped = deduped.filter(
            (pl.col("key_player_out_home").is_null() | (pl.col("key_player_out_home") == False))
            & (pl.col("key_player_out_away").is_null() | (pl.col("key_player_out_away") == False))
        )
        print(f"Injury filter (skip games with key_player_out_*): {len(deduped):,} games (dropped {before - len(deduped):,})")

    # Close-line spread edge (default)
    line_col_close = "consensus_close_spread" if "consensus_close_spread" in deduped.columns else "close_spread_home"
    spread_edge_expr = pl.col("ensemble_spread") - pl.col(line_col_close)
    if line_col_close != "close_spread_home" or "spread_edge" not in deduped.columns:
        deduped = deduped.with_columns(spread_edge_expr.alias("spread_edge"))
    edge_home_ok = pl.col("spread_edge") >= EDGE_THRESHOLD
    edge_away_ok = (pl.col(line_col_close) - pl.col("ensemble_spread")) >= EDGE_THRESHOLD
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

    # --- Open-line spread backtest (when open_spread_home exists) ---
    if "open_spread_home" in deduped.columns:
        print("\n=== Open-Line Spread Backtest ===")
        spread_edge_open = (pl.col("ensemble_spread") - pl.col("open_spread_home")).alias("spread_edge_open")
        tmp = deduped.with_columns(spread_edge_open)
        edge_home_ok_o = pl.col("spread_edge_open") >= EDGE_THRESHOLD
        edge_away_ok_o = (pl.col("open_spread_home") - pl.col("ensemble_spread")) >= EDGE_THRESHOLD
        spread_ok_o = edge_home_ok_o | (edge_away_ok_o if not BET_ON_HOME_ONLY else pl.lit(False))
        if EV_FILTER and "ev_positive_home" in tmp.columns:
            spread_ok_o = (pl.col("ev_positive_home") & edge_home_ok_o) | (pl.col("ev_positive_away") & edge_away_ok_o)
        if EV_FILTER and EV_MIN_PROB_MARGIN is not None and "model_win_prob_home" in tmp.columns and "implied_prob_home" in tmp.columns:
            prob_margin_home_o = pl.col("model_win_prob_home") - pl.col("implied_prob_home")
            prob_margin_away_o = pl.col("implied_prob_home") - pl.col("model_win_prob_home")
            spread_ok_o = spread_ok_o & (
                (edge_home_ok_o & (prob_margin_home_o >= EV_MIN_PROB_MARGIN))
                | (edge_away_ok_o & (prob_margin_away_o >= EV_MIN_PROB_MARGIN))
            )

        backtest_o = tmp.filter(pl.col("actual_margin").is_not_null() & spread_ok_o)
        print(
            f"Games with actual result + edge ≥ {EDGE_THRESHOLD} pts vs OPEN"
            + (" (+EV only)" if EV_FILTER else "")
            + f": {len(backtest_o):,}"
        )
        if len(backtest_o) > 0:
            backtest_o = backtest_o.with_columns(
                pl.when(edge_home_ok_o)
                .then(pl.col("home_cover"))
                .when(edge_away_ok_o)
                .then(~pl.col("home_cover"))
                .otherwise(None)
                .alias("bet_won_open")
            ).with_columns(
                pl.when(pl.col("bet_won_open").is_not_null())
                .then(pl.when(pl.col("bet_won_open")).then(1.0).otherwise(-1.0))
                .otherwise(pl.lit(None))
                .alias("units_open")
            )
            valid_o = backtest_o.filter(pl.col("bet_won_open").is_not_null())
            n_bets_o = len(valid_o)
            ats_pct_o = valid_o["bet_won_open"].mean()
            total_units_o = valid_o["units_open"].sum()
            roi_o = total_units_o / n_bets_o * 100 if n_bets_o > 0 else 0

            print(f"Total bets (open): {n_bets_o}")
            print(f"ATS hit rate (open): {ats_pct_o:.1%}")
            print(f"Total units won/lost (open, flat 1u): {total_units_o:.1f}")
            print(f"ROI (open): {roi_o:.1f}%")

            by_season_o = valid_o.group_by("season").agg(
                pl.len().alias("n_bets"),
                pl.col("bet_won_open").mean().alias("ats_pct"),
                pl.col("units_open").sum().alias("units"),
            ).with_columns((pl.col("units") / pl.col("n_bets")).alias("units_per_bet")).sort("season")
            print("\nOpen-line by season:")
            print(by_season_o)

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
