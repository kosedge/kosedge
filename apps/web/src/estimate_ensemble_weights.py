"""
Estimate ensemble weights from training window (no look-ahead). Fits weights to minimize
MAE of (actual_margin - predicted_spread). Use season <= TRAIN_END_YEAR; validate on later seasons.
Run from apps/web: python src/estimate_ensemble_weights.py
Writes: data/processed/ensemble_weights.json. Merge uses these when present.
"""
import json
import sys
from pathlib import Path

import polars as pl

_WEB = Path(__file__).resolve().parent.parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
from pipeline_paths import MERGED_GAMES_PATH, ENSEMBLE_WEIGHTS_PATH, PROCESSED

# Training window: fit weights on seasons <= this year. Validate on TRAIN_END_YEAR+1 and later.
TRAIN_END_YEAR = 2022


def main() -> None:
    if not MERGED_GAMES_PATH.exists():
        print(f"Run merge_games_ensemble.py first. Missing {MERGED_GAMES_PATH}")
        return
    df = pl.read_parquet(MERGED_GAMES_PATH).unique(subset="event_id", keep="first")
    if "actual_margin" not in df.columns:
        print("No actual_margin in merged data. Add results or actual_margins for training.")
        return

    train = df.filter(
        pl.col("actual_margin").is_not_null()
        & (pl.col("season") <= TRAIN_END_YEAR)
    )
    if len(train) < 100:
        train = df.filter(pl.col("actual_margin").is_not_null())
        if len(train) < 50:
            print(f"Too few rows with actual_margin ({len(train)}). Run merge with results/actual_margins first.")
            return
        print(f"Warning: only {len(train)} rows with season<={TRAIN_END_YEAR}; using all {len(train)} games for weights.")
    else:
        print(f"Training on {len(train)} games (season <= {TRAIN_END_YEAR}).")

    # Component diffs (match merge_games_ensemble). adjem_diff, torvik_diff, barthag*20, bpr, haslam.
    adjem_diff = pl.col("adjem").fill_null(0) - pl.col("adjem_away").fill_null(0)
    torvik_diff = (pl.col("net_torvik").fill_null(0) - pl.col("net_torvik_away").fill_null(0))
    barthag_diff = (pl.col("barthag").fill_null(0) - pl.col("barthag_away").fill_null(0)) * 20.0
    bpr_diff = pl.col("bpr").fill_null(0) - pl.col("bpr_away").fill_null(0)
    haslam_diff = (
        (pl.col("haslam_net").fill_null(0) - pl.col("haslam_net_away").fill_null(0))
        if "haslam_net" in train.columns and "haslam_net_away" in train.columns
        else pl.lit(0.0)
    )

    train = train.with_columns([
        adjem_diff.alias("_adjem"),
        torvik_diff.alias("_torvik"),
        barthag_diff.alias("_barthag"),
        bpr_diff.alias("_bpr"),
        haslam_diff.alias("_haslam"),
    ])

    # OLS: actual_margin ~ _adjem + _torvik + _barthag + _bpr + _haslam + const
    import numpy as np
    X = train.select(["_adjem", "_torvik", "_barthag", "_bpr", "_haslam"]).to_numpy()
    y = train.select("actual_margin").to_numpy().ravel()
    ones = np.ones((len(X), 1))
    X_with_const = np.hstack([X, ones])
    try:
        coeffs = np.linalg.lstsq(X_with_const, y, rcond=None)[0]
    except Exception as e:
        print("OLS failed:", e)
        return
    w_adjem, w_torvik, w_barthag, w_bpr, w_haslam, home_court = coeffs

    raw = np.array([w_adjem, w_torvik, w_barthag, w_bpr, w_haslam])
    raw = np.maximum(raw, 0.0)
    total = raw.sum()
    if total <= 0:
        total = 1.0
    weights = (raw / total).tolist()
    home_court = float(home_court)

    out = {
        "adjem": round(weights[0], 4),
        "torvik": round(weights[1], 4),
        "barthag": round(weights[2], 4),
        "bpr": round(weights[3], 4),
        "haslam": round(weights[4], 4),
        "home_court": round(home_court, 4),
        "train_end_year": TRAIN_END_YEAR,
        "n_train": len(train),
    }
    PROCESSED.mkdir(parents=True, exist_ok=True)
    with open(ENSEMBLE_WEIGHTS_PATH, "w") as f:
        json.dump(out, f, indent=2)
    print("Ensemble weights (trained on season <=", TRAIN_END_YEAR, "):")
    print(out)
    print("Wrote", ENSEMBLE_WEIGHTS_PATH)


if __name__ == "__main__":
    main()
