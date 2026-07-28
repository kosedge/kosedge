#!/usr/bin/env python3
"""Fast DB-first totals/blend calibration using owned projections + closes.

No Odds API. No re-simulation. Inverts default market blend from stored
projections when pre-blend diagnostics are absent, then sweeps blend weights
and fits the totals calibrator on 2023–2024 with 2025 holdout.

Writes: data/ops/nfl-calibration-retune-owned-YYYYMMDD.json
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "model-service"))
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge")

from sqlalchemy import create_engine, text  # noqa: E402

from src.services.nfl_simulator import (  # noqa: E402
    NFL_MARKET_BLEND_SPREAD_WEIGHT,
    NFL_MARKET_BLEND_TOTAL_WEIGHT,
)
from src.services.nfl_totals_calibration import _fit_linear_calibration  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "ops"
WEIGHTS = [0.0, 0.10, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50]


def _avg(xs: List[float]) -> Optional[float]:
    return round(sum(xs) / len(xs), 4) if xs else None


def main() -> int:
    eng = create_engine(os.environ["DATABASE_URL"])
    with eng.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT
                  sch.season, sch.week,
                  sch.spread_line, sch.total_line,
                  sch.home_score, sch.away_score,
                  p.spread_home AS model_spread_home,
                  p.total_mean AS model_total,
                  p.projection
                FROM nfl_dp_schedules sch
                JOIN games g ON g.external_id = sch.game_id
                JOIN LATERAL (
                  SELECT spread_home, total_mean, projection
                  FROM nfl_market_projections mp
                  WHERE mp.game_id = g.id
                  ORDER BY mp.created_at DESC
                  LIMIT 1
                ) p ON TRUE
                WHERE sch.season BETWEEN 2023 AND 2025
                  AND sch.home_score IS NOT NULL
                  AND sch.away_score IS NOT NULL
                  AND sch.spread_line IS NOT NULL
                  AND sch.total_line IS NOT NULL
                  AND sch.week >= 2
                ORDER BY sch.season, sch.week
                """
            )
        ).fetchall()

    comps: List[Dict[str, Any]] = []
    for row in rows:
        m = dict(row._mapping)
        proj = m.get("projection") or {}
        if isinstance(proj, str):
            try:
                proj = json.loads(proj)
            except Exception:
                proj = {}
        if not isinstance(proj, dict):
            proj = {}
        diagnostics = proj.get("diagnostics") if isinstance(proj.get("diagnostics"), dict) else proj
        mb = diagnostics.get("market_blend") if isinstance(diagnostics, dict) else {}
        if not isinstance(mb, dict):
            mb = {}
        # Also accept markets nested under projection payload
        markets = proj.get("markets") if isinstance(proj.get("markets"), dict) else {}
        pre_spread = (
            mb.get("pre_blend_spread_home")
            or mb.get("pre_spread_home")
            or markets.get("pre_blend_spread_home")
        )
        pre_total = mb.get("pre_blend_total") or mb.get("pre_total") or markets.get("pre_blend_total")
        model_spread = float(m["model_spread_home"]) if m["model_spread_home"] is not None else None
        model_total = float(m["model_total"]) if m["model_total"] is not None else None
        if model_spread is None or model_total is None:
            continue
        market_spread_api = -float(m["spread_line"])
        market_total = float(m["total_line"])
        if pre_spread is not None:
            raw_spread = float(pre_spread)
        else:
            w = NFL_MARKET_BLEND_SPREAD_WEIGHT
            raw_spread = (
                (model_spread - w * market_spread_api) / max(1e-6, 1 - w) if w < 1 else model_spread
            )
        if pre_total is not None:
            raw_total = float(pre_total)
        else:
            w = NFL_MARKET_BLEND_TOTAL_WEIGHT
            raw_total = (model_total - w * market_total) / max(1e-6, 1 - w) if w < 1 else model_total
        comps.append(
            {
                "season": int(m["season"]),
                "raw_margin": -raw_spread,
                "raw_total": raw_total,
                "market_margin": float(m["spread_line"]),
                "market_total": market_total,
                "actual_margin": float(m["home_score"]) - float(m["away_score"]),
                "actual_total": float(m["home_score"]) + float(m["away_score"]),
            }
        )

    tune = [x for x in comps if x["season"] in (2023, 2024)]
    hold = [x for x in comps if x["season"] == 2025]
    if not tune or not hold:
        print(json.dumps({"ok": False, "error": "insufficient rows", "n": len(comps)}))
        return 2

    cal = _fit_linear_calibration(
        [
            {
                "pred_total": x["raw_total"],
                "actual_total": x["actual_total"],
                "days_ago": (2025 - x["season"]) * 365.0,
            }
            for x in tune
        ],
        min_sample_size=80,
        slope_min=0.75,
        slope_max=1.25,
        intercept_abs_max=8.0,
    )

    def sweep(rows_in: List[Dict[str, Any]], sw: float, tw: float, use_cal: bool) -> Dict[str, float]:
        se: List[float] = []
        te: List[float] = []
        for x in rows_in:
            pm = (1 - sw) * x["raw_margin"] + sw * x["market_margin"]
            pt = (1 - tw) * x["raw_total"] + tw * x["market_total"]
            if use_cal:
                pt = float(cal["slope"]) * pt + float(cal["intercept"])
            se.append(abs(pm - x["actual_margin"]))
            te.append(abs(pt - x["actual_total"]))
        return {"spread_mae": _avg(se) or 0.0, "total_mae": _avg(te) or 0.0}

    before_hold = sweep(hold, NFL_MARKET_BLEND_SPREAD_WEIGHT, NFL_MARKET_BLEND_TOTAL_WEIGHT, False)
    before_tune = sweep(tune, NFL_MARKET_BLEND_SPREAD_WEIGHT, NFL_MARKET_BLEND_TOTAL_WEIGHT, False)
    best = None
    for sw in WEIGHTS:
        for tw in WEIGHTS:
            metrics = sweep(tune, sw, tw, True)
            score = metrics["spread_mae"] + metrics["total_mae"]
            cand = {"spread_w": sw, "total_w": tw, **metrics, "score": round(score, 4)}
            if best is None or cand["score"] < best["score"]:
                best = cand
    assert best is not None
    after_hold = sweep(hold, best["spread_w"], best["total_w"], True)
    after_tune = sweep(tune, best["spread_w"], best["total_w"], True)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": "owned_projections_invert_blend",
        "ok": True,
        "n_components": len(comps),
        "n_tune": len(tune),
        "n_holdout_2025": len(hold),
        "before": {
            "blend_spread": NFL_MARKET_BLEND_SPREAD_WEIGHT,
            "blend_total": NFL_MARKET_BLEND_TOTAL_WEIGHT,
            "tune": before_tune,
            "holdout_2025": before_hold,
        },
        "totals_calibrator": cal,
        "best_blend": best,
        "after": {
            "blend_spread": best["spread_w"],
            "blend_total": best["total_w"],
            "tune": after_tune,
            "holdout_2025_calibrated": after_hold,
        },
        "holdout_delta": {
            "spread_mae": round(after_hold["spread_mae"] - before_hold["spread_mae"], 4),
            "total_mae": round(after_hold["total_mae"] - before_hold["total_mae"], 4),
        },
        "recommendation": {
            "NFL_MARKET_BLEND_SPREAD_WEIGHT": best["spread_w"],
            "NFL_MARKET_BLEND_TOTAL_WEIGHT": best["total_w"],
            "totals_calibration_slope": cal.get("slope"),
            "totals_calibration_intercept": cal.get("intercept"),
            "totals_fit_mode": cal.get("fit_mode"),
            "promote_if_holdout_improves": bool(
                after_hold["spread_mae"] <= before_hold["spread_mae"]
                and after_hold["total_mae"] <= before_hold["total_mae"]
            ),
        },
    }
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"nfl-calibration-retune-owned-{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
