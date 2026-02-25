"""
Train XGBoost to predict actual_margin from ratings/spread features.
Requires: data/processed/games_with_edges.parquet with actual_margin non-null.
Writes: data/processed/margin_model.json (XGBoost model).
Run from apps/web: python src/train_margin_model.py
"""
import sys
from pathlib import Path

import polars as pl

_WEB = Path(__file__).resolve().parent.parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
from pipeline_paths import GAMES_WITH_EDGES_PATH, MARGIN_MODEL_PATH

try:
    from xgboost import XGBRegressor
except ImportError:
    XGBRegressor = None


def main() -> None:
    games_path = GAMES_WITH_EDGES_PATH
    if not games_path.exists():
        print(f"Run join_and_backtest.py first. Missing {games_path}")
        return
    if XGBRegressor is None:
        print("Install xgboost: pip install xgboost")
        return

    games = pl.read_parquet(games_path)
    if games.filter(pl.col("actual_margin").is_not_null()).is_empty():
        print("No actual_margin in games. Add results or actual_margins.parquet to run backtest and train model.")
        return

    # One row per game (dedupe by event_id if multiple books)
    g = games.unique(subset=["event_id"], keep="first")
    g = g.filter(pl.col("actual_margin").is_not_null())

    feature_cols = [
        "adj_em_diff",
        "sos_diff",
        "model_spread",
        "close_spread_home",
        "close_total",
    ]
    missing = [c for c in feature_cols if c not in g.columns]
    if missing:
        print(f"Missing columns for features: {missing}. Using available: {[c for c in feature_cols if c in g.columns]}")
        feature_cols = [c for c in feature_cols if c in g.columns]
    if not feature_cols:
        print("No feature columns available.")
        return

    X = g.select(feature_cols).to_numpy()
    y = g["actual_margin"].to_numpy()

    model = XGBRegressor(n_estimators=100, max_depth=4, random_state=42)
    model.fit(X, y)

    model.save_model(str(MARGIN_MODEL_PATH))
    print(f"Saved {MARGIN_MODEL_PATH}")


if __name__ == "__main__":
    main()
