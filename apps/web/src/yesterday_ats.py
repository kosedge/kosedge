# src/yesterday_ats.py
"""
Model ATS performance for a single day. Uses same edge/EV logic as flat_betting_backtest.
Run from apps/web: python src/yesterday_ats.py [YYYY-MM-DD]
Default date: yesterday (local).
"""
import sys
from datetime import date, timedelta
from pathlib import Path

import polars as pl

_WEB = Path(__file__).resolve().parent.parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
from pipeline_paths import MERGED_GAMES_PATH

# Match flat_betting_backtest defaults
EDGE_THRESHOLD = 6.0
EV_FILTER = True
EV_MIN_PROB_MARGIN = 0.05


def main() -> None:
    target = (date.today() - timedelta(days=1)).isoformat()
    if len(sys.argv) >= 2:
        target = sys.argv[1]

    if not MERGED_GAMES_PATH.exists():
        print(f"Merged parquet not found: {MERGED_GAMES_PATH}")
        print("Run: python src/merge_games_ensemble.py")
        return

    df = pl.read_parquet(MERGED_GAMES_PATH)
    deduped = df.unique(subset="event_id", keep="first")

    if "commence_time" not in deduped.columns:
        print("No commence_time in merged data.")
        return
    game_date = pl.col("commence_time").str.slice(0, 10)
    deduped = deduped.with_columns(game_date.alias("game_date_str"))
    day = deduped.filter(pl.col("game_date_str") == target)

    if "actual_margin" not in day.columns:
        print(f"No actual_margin in merged data for {target}. Run merge with actual_margins or results.")
        return

    day = day.filter(pl.col("actual_margin").is_not_null())
    if day.is_empty():
        print(f"No games with results for {target}.")
        return

    line_col = "consensus_close_spread" if "consensus_close_spread" in day.columns else "close_spread_home"
    spread_edge = pl.col("ensemble_spread") - pl.col(line_col)
    day = day.with_columns(spread_edge.alias("spread_edge"))
    edge_home_ok = pl.col("spread_edge") >= EDGE_THRESHOLD
    edge_away_ok = (pl.col(line_col) - pl.col("ensemble_spread")) >= EDGE_THRESHOLD
    spread_ok = edge_home_ok | edge_away_ok

    if EV_FILTER and "ev_positive_home" in day.columns and "ev_positive_away" in day.columns:
        spread_ok = (pl.col("ev_positive_home") & edge_home_ok) | (pl.col("ev_positive_away") & edge_away_ok)
    if EV_FILTER and EV_MIN_PROB_MARGIN is not None and "model_win_prob_home" in day.columns and "implied_prob_home" in day.columns:
        prob_margin_home = pl.col("model_win_prob_home") - pl.col("implied_prob_home")
        prob_margin_away = pl.col("implied_prob_home") - pl.col("model_win_prob_home")
        spread_ok = spread_ok & (
            (edge_home_ok & (prob_margin_home >= EV_MIN_PROB_MARGIN))
            | (edge_away_ok & (prob_margin_away >= EV_MIN_PROB_MARGIN))
        )

    backtest = day.filter(spread_ok)
    backtest = backtest.with_columns(
        pl.when(edge_home_ok).then(pl.col("home_cover")).when(edge_away_ok).then(~pl.col("home_cover")).otherwise(None).alias("bet_won")
    )
    backtest = backtest.with_columns(
        pl.when(pl.col("bet_won").is_not_null())
        .then(pl.when(pl.col("bet_won")).then(1.0).otherwise(-1.0))
        .otherwise(pl.lit(None))
        .alias("units")
    )
    valid = backtest.filter(pl.col("bet_won").is_not_null())
    valid = valid.with_columns(
        pl.when(pl.col("spread_edge") >= EDGE_THRESHOLD).then(pl.lit("home")).otherwise(pl.lit("away")).alias("bet_side")
    )

    n_all = len(day)
    n_bets = len(valid)
    if n_bets == 0:
        print(f"=== {target} ===\nGames with results: {n_all}. No model picks met edge ≥ {EDGE_THRESHOLD} pts" + (" (+EV)" if EV_FILTER else "") + ".")
        return

    ats_pct = valid["bet_won"].mean()
    total_units = valid["units"].sum()

    print(f"=== Model vs spread — {target} ===")
    print(f"Games with results: {n_all}  |  Model picks (edge ≥ {EDGE_THRESHOLD}, +EV): {n_bets}")
    print(f"ATS: {valid['bet_won'].sum():.0f}-{n_bets - valid['bet_won'].sum():.0f}  ({ats_pct:.1%})  |  Units: {total_units:+.1f}")
    print()
    home_team = "home_team" if "home_team" in valid.columns else pl.lit("?")
    away_team = "away_team" if "away_team" in valid.columns else pl.lit("?")
    for row in valid.select([home_team, away_team, "bet_side", "spread_edge", "bet_won", "actual_margin", line_col]).iter_rows(named=True):
        ht = row.get("home_team", "?")
        at = row.get("away_team", "?")
        side = row["bet_side"]
        edge = row["spread_edge"]
        won = "✓" if row["bet_won"] else "✗"
        margin = row["actual_margin"]
        line = row.get(line_col, "")
        print(f"  {won}  {ht} vs {at}  — bet {side} (edge {edge:+.1f})  actual margin {margin:+.1f}  line {line}")


if __name__ == "__main__":
    main()
