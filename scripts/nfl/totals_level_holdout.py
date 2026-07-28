#!/usr/bin/env python3
"""Walk-forward totals level holdout: signed bias, O/U mix, MAE vs Vegas.

Uses stored projection base totals (pre-calibration) vs actual finals and
nflverse closing totals. Compares legacy broken calibrator clamps vs the
mean-preserving fit shipping in nfl_totals_calibration.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge")

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from src.services.nfl_totals_calibration import (  # noqa: E402
    _fit_linear_calibration,
    apply_totals_calibration,
)


def _legacy_broken_apply(pred: float, slope: float, intercept: float) -> float:
    slope = max(0.8, min(1.2, slope))
    intercept = max(-8.0, min(8.0, intercept))
    return max(24.0, min(66.0, slope * pred + intercept))


def main() -> int:
    # Historical holdout evaluates calibrator quality on old-prior projections.
    # Live sims use prior-delta removal separately (see nfl_totals_calibration).
    os.environ.setdefault("NFL_FRAMEWORK_PRIOR_TOTAL_POINTS", "43.5")
    os.environ.setdefault("NFL_TOTALS_CALIBRATION_PRIOR_REFERENCE", "43.5")
    db_url = os.environ["DATABASE_URL"]
    if db_url.startswith("postgresql://") and "+psycopg" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    rows = session.execute(
        text(
            """
            SELECT
              s.season_year AS season,
              g.game_date AS game_date,
              COALESCE(
                NULLIF(p.projection->'diagnostics'->'totals_calibration'->>'base_total', '')::double precision,
                p.total_mean
              ) AS pred_base,
              p.total_mean AS pred_stored,
              o.final_total_points AS actual_total,
              sch.total_line AS close_total
            FROM nfl_market_projections p
            JOIN games g ON g.id = p.game_id
            JOIN seasons s ON s.id = g.season_id
            JOIN nfl_market_outcomes o ON o.game_id = p.game_id
            JOIN teams home ON home.id = g.home_team_id
            JOIN teams away ON away.id = g.away_team_id
            LEFT JOIN nfl_dp_schedules sch
              ON sch.season = s.season_year
             AND sch.home_team = home.abbr
             AND sch.away_team = away.abbr
            WHERE s.season_year BETWEEN 2023 AND 2025
              AND o.final_total_points IS NOT NULL
              AND p.total_mean IS NOT NULL
            """
        )
    ).fetchall()
    session.close()

    by_season: dict[int, list] = {}
    for r in rows:
        m = dict(r._mapping)
        by_season.setdefault(int(m["season"]), []).append(m)

    report: dict = {"seasons": {}, "summary": {}}
    all_new_bias = []
    all_adaptive_bias = []
    all_legacy_bias = []
    all_stored_bias = []

    seasons = sorted(by_season)
    for holdout in seasons:
        train = [p for s, pts in by_season.items() if s < holdout for p in pts]
        test = by_season[holdout]
        if len(train) < 80 or len(test) < 40:
            continue
        # Recency vs the start of the holdout season (enterprise walk-forward).
        as_of = date(holdout, 9, 1)
        train_points = []
        for p in train:
            gd = p.get("game_date")
            if hasattr(gd, "toordinal"):
                days_ago = max(0, (as_of - gd).days)
            else:
                days_ago = 365
            train_points.append(
                {
                    "pred_total": float(p["pred_base"]),
                    "actual_total": float(p["actual_total"]),
                    "days_ago": days_ago,
                }
            )
        fit = _fit_linear_calibration(
            train_points,
            min_sample_size=80,
            slope_min=0.85,
            slope_max=1.25,
            intercept_abs_max=18.0,
        )
        # Reconstruct raw OLS then apply legacy clamps for comparison.
        x_mean = sum(float(p["pred_base"]) for p in train) / len(train)
        y_mean = sum(float(p["actual_total"]) for p in train) / len(train)
        var_x = sum((float(p["pred_base"]) - x_mean) ** 2 for p in train)
        cov = sum((float(p["pred_base"]) - x_mean) * (float(p["actual_total"]) - y_mean) for p in train)
        raw_slope = (cov / var_x) if var_x > 1e-9 else 1.0
        raw_intercept = y_mean - raw_slope * x_mean

        def metrics(preds, actuals, closes):
            n = len(preds)
            bias = sum(p - a for p, a in zip(preds, actuals)) / n
            mae = sum(abs(p - a) for p, a in zip(preds, actuals)) / n
            under_mkt = sum(1 for p, c in zip(preds, closes) if c is not None and p < c)
            over_mkt = sum(1 for p, c in zip(preds, closes) if c is not None and p > c)
            mkt_n = under_mkt + over_mkt
            vegas_mae = (
                sum(abs(c - a) for c, a in zip(closes, actuals) if c is not None)
                / max(1, sum(1 for c in closes if c is not None))
            )
            return {
                "n": n,
                "signed_bias": round(bias, 3),
                "mae": round(mae, 3),
                "vegas_mae": round(vegas_mae, 3),
                "pct_under_market": round(100.0 * under_mkt / mkt_n, 1) if mkt_n else None,
                "pct_over_market": round(100.0 * over_mkt / mkt_n, 1) if mkt_n else None,
            }

        actuals = [float(p["actual_total"]) for p in test]
        closes = [float(p["close_total"]) if p["close_total"] is not None else None for p in test]
        stored = [float(p["pred_stored"]) for p in test]
        bases = [float(p["pred_base"]) for p in test]
        # Historical bases still embed the old prior. Evaluate calibrators at full
        # strength (shrink=1); live boards apply transition shrink separately.
        os.environ["NFL_TOTALS_LEVEL_SHIFT_SHRINK"] = "1.0"
        new_preds = [float(apply_totals_calibration(b, fit) or b) for b in bases]
        slate_pre = sum(bases) / len(bases) if bases else None
        adaptive_preds = [
            float(apply_totals_calibration(b, fit, slate_pre_mean=slate_pre) or b) for b in bases
        ]
        os.environ.pop("NFL_TOTALS_LEVEL_SHIFT_SHRINK", None)
        legacy_preds = [_legacy_broken_apply(b, raw_slope, raw_intercept) for b in bases]

        season_report = {
            "train_n": len(train),
            "fit": {k: fit.get(k) for k in ("slope", "intercept", "signed_bias_pre", "signed_bias_post", "mae_improvement", "mean_preserved", "prior_delta_removed", "fit_mode")},
            "stored_published": metrics(stored, actuals, closes),
            "base_uncalibrated": metrics(bases, actuals, closes),
            "legacy_clamp_calibrator": metrics(legacy_preds, actuals, closes),
            "mean_preserving_calibrator": metrics(new_preds, actuals, closes),
            "adaptive_level_calibrator": metrics(adaptive_preds, actuals, closes),
        }
        report["seasons"][str(holdout)] = season_report
        all_stored_bias.append(season_report["stored_published"]["signed_bias"])
        all_legacy_bias.append(season_report["legacy_clamp_calibrator"]["signed_bias"])
        all_new_bias.append(season_report["mean_preserving_calibrator"]["signed_bias"])
        all_adaptive_bias.append(season_report["adaptive_level_calibrator"]["signed_bias"])

    report["summary"] = {
        "avg_signed_bias_stored": round(sum(all_stored_bias) / len(all_stored_bias), 3) if all_stored_bias else None,
        "avg_signed_bias_legacy_clamp": round(sum(all_legacy_bias) / len(all_legacy_bias), 3) if all_legacy_bias else None,
        "avg_signed_bias_mean_preserving": round(sum(all_new_bias) / len(all_new_bias), 3) if all_new_bias else None,
        "avg_signed_bias_adaptive": round(sum(all_adaptive_bias) / len(all_adaptive_bias), 3) if all_adaptive_bias else None,
        # Historical bases still carry the old generative prior; full neutrality
        # requires re-simming settled seasons. Gate = material improvement vs stored
        # plus |bias| under a transition ceiling until that re-sim lands.
        "gate_pass": bool(all_new_bias)
        and abs(sum(all_new_bias) / len(all_new_bias))
        < abs(sum(all_stored_bias) / len(all_stored_bias)) - 0.75
        and abs(sum(all_new_bias) / len(all_new_bias)) <= 2.0,
    }

    out = ROOT / "data" / "ops" / "nfl-totals-level-holdout.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summary"], indent=2))
    for season, payload in report["seasons"].items():
        mp = payload["mean_preserving_calibrator"]
        st = payload["stored_published"]
        print(
            f"holdout {season}: stored_bias={st['signed_bias']} under%={st['pct_under_market']} "
            f"| fixed_bias={mp['signed_bias']} under%={mp['pct_under_market']} mae={mp['mae']} vegas_mae={mp['vegas_mae']}"
        )
    print(f"wrote {out}")
    return 0 if report["summary"].get("gate_pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
