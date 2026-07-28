#!/usr/bin/env python3
"""Grade NFL model vs owned open/close odds — DB-first, never pulls Odds API.

Joins:
  - Owned open/close from odds_snapshots (min/max captured_at per game)
  - Fallback close: nfl_dp_schedules.spread_line / total_line (nflverse)
  - Projections: nfl_market_projections (optional)
  - Outcomes: nfl_market_outcomes or schedule final scores

Writes: data/ops/nfl-odds-open-close-grading.json (+ markdown summary).

Usage:
  DATABASE_URL=postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge \\
    /Users/ryankos/kosedge/.venv/bin/python scripts/nfl/odds_open_close_grading.py
"""

from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "model-service"))
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge")

from sqlalchemy import create_engine, text  # noqa: E402

OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "ops"
OUT_JSON = OUT_DIR / "nfl-odds-open-close-grading.json"
OUT_MD = OUT_DIR / "nfl-odds-open-close-grading.md"


def _f(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _american_to_implied(price: Optional[float]) -> Optional[float]:
    if price is None:
        return None
    p = float(price)
    if p == 0:
        return None
    if p > 0:
        return 100.0 / (p + 100.0)
    return (-p) / ((-p) + 100.0)


def _brier(prob: float, won: bool) -> float:
    y = 1.0 if won else 0.0
    return (prob - y) ** 2


def _mae(pred: float, actual: float) -> float:
    return abs(pred - actual)


def _ats_hit(home_margin: float, spread_home_odds_api: float) -> bool:
    """Odds API: negative spread_home = home favored. Cover if home_margin + spread > 0."""
    return (home_margin + spread_home_odds_api) > 0


def main() -> int:
    engine = create_engine(os.environ["DATABASE_URL"])
    with engine.connect() as conn:
        inventory = {
            "games": int(conn.execute(text("SELECT count(*) FROM games")).scalar() or 0),
            "odds_snapshots": int(conn.execute(text("SELECT count(*) FROM odds_snapshots")).scalar() or 0),
            "nfl_dp_schedules": int(conn.execute(text("SELECT count(*) FROM nfl_dp_schedules")).scalar() or 0),
            "nfl_market_projections": int(
                conn.execute(text("SELECT count(*) FROM nfl_market_projections")).scalar() or 0
            ),
            "nfl_market_outcomes": int(
                conn.execute(text("SELECT count(*) FROM nfl_market_outcomes")).scalar() or 0
            ),
            "nfl_market_history_snapshots": int(
                conn.execute(text("SELECT count(*) FROM nfl_market_history_snapshots")).scalar() or 0
            ),
        }

        # Owned open/close from odds_snapshots (DK-preferred via sportsbooks if present).
        open_close = conn.execute(
            text(
                """
                WITH nfl_games AS (
                  SELECT g.id AS game_id
                  FROM games g
                  JOIN seasons s ON s.id = g.season_id
                  JOIN leagues l ON l.id = s.league_id
                  WHERE lower(l.code) IN ('nfl', 'americanfootball_nfl')
                     OR lower(COALESCE(l.name, '')) LIKE '%nfl%'
                ),
                ranked AS (
                  SELECT
                    o.game_id,
                    FIRST_VALUE(o.spread_home) OVER w AS open_spread,
                    FIRST_VALUE(o.total_points) OVER w AS open_total,
                    FIRST_VALUE(o.price_home) OVER w AS open_price_home,
                    LAST_VALUE(o.spread_home) OVER w AS close_spread,
                    LAST_VALUE(o.total_points) OVER w AS close_total,
                    LAST_VALUE(o.price_home) OVER w AS close_price_home,
                    ROW_NUMBER() OVER (PARTITION BY o.game_id ORDER BY o.captured_at) AS rn
                  FROM odds_snapshots o
                  JOIN nfl_games g ON g.game_id = o.game_id
                  WHERE o.spread_home IS NOT NULL OR o.total_points IS NOT NULL OR o.price_home IS NOT NULL
                  WINDOW w AS (
                    PARTITION BY o.game_id
                    ORDER BY o.captured_at
                    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                  )
                )
                SELECT
                  game_id, open_spread, close_spread, open_total, close_total,
                  open_price_home, close_price_home
                FROM ranked
                WHERE rn = 1
                """
            )
        ).fetchall()
        oc_by_game = {str(r.game_id): dict(r._mapping) for r in open_close}

        # Schedule closes + outcomes (free substrate)
        sched = conn.execute(
            text(
                """
                SELECT
                  sch.season, sch.week, sch.game_id AS dp_game_id,
                  sch.home_team, sch.away_team,
                  sch.spread_line, sch.total_line,
                  sch.home_score, sch.away_score,
                  g.id AS game_uuid
                FROM nfl_dp_schedules sch
                LEFT JOIN games g ON g.external_id = sch.game_id
                WHERE sch.home_score IS NOT NULL
                  AND sch.away_score IS NOT NULL
                  AND sch.season BETWEEN 2020 AND 2025
                ORDER BY sch.season, sch.week, sch.game_id
                """
            )
        ).fetchall()

        # Latest projection per game (if any). Prefer pipeline_run_at (wall-clock
        # ingest) over created_at — historical re-sims backdate created_at to
        # kickoff-minus-buffer, so created_at DESC alone can keep stale rows.
        proj_rows = conn.execute(
            text(
                """
                SELECT DISTINCT ON (game_id)
                  game_id, model_version,
                  home_win_prob, away_win_prob,
                  spread_home, total_mean,
                  created_at,
                  COALESCE(
                    (projection->'audit'->>'pipeline_run_at')::timestamptz,
                    created_at
                  ) AS effective_at
                FROM nfl_market_projections
                ORDER BY game_id,
                  COALESCE(
                    (projection->'audit'->>'pipeline_run_at')::timestamptz,
                    created_at
                  ) DESC
                """
            )
        ).fetchall()
        proj_by_game = {str(r.game_id): dict(r._mapping) for r in proj_rows}

    # Metrics accumulators
    market_close_spread_mae: List[float] = []
    market_close_total_mae: List[float] = []
    model_spread_mae: List[float] = []
    model_total_mae: List[float] = []
    model_brier: List[float] = []
    market_brier: List[float] = []
    model_ats: List[bool] = []
    market_clv_spread: List[float] = []  # close - open in home-favored points
    model_clv_spread: List[float] = []
    model_clv_total: List[float] = []
    n_owned_oc = 0
    n_nflverse_close = 0
    n_with_proj = 0

    by_season: Dict[int, Dict[str, Any]] = {}

    for row in sched:
        m = dict(row._mapping)
        season = int(m["season"])
        home_score = float(m["home_score"])
        away_score = float(m["away_score"])
        home_margin = home_score - away_score
        actual_total = home_score + away_score
        game_uuid = str(m["game_uuid"]) if m.get("game_uuid") else None

        # Close line: prefer owned odds close; else nflverse (convert sign)
        oc = oc_by_game.get(game_uuid or "", {})
        close_spread_api = _f(oc.get("close_spread"))
        open_spread_api = _f(oc.get("open_spread"))
        close_total = _f(oc.get("close_total"))
        open_total = _f(oc.get("open_total"))
        close_ml = _f(oc.get("close_price_home"))
        open_ml = _f(oc.get("open_price_home"))

        nflverse_spread = _f(m.get("spread_line"))  # + when home favored
        nflverse_total = _f(m.get("total_line"))

        if close_spread_api is not None or close_total is not None:
            n_owned_oc += 1
        if close_spread_api is None and nflverse_spread is not None:
            # Convert nflverse → Odds API sign
            close_spread_api = -nflverse_spread
            n_nflverse_close += 1
        if close_total is None and nflverse_total is not None:
            close_total = nflverse_total

        if close_spread_api is not None:
            # Market MAE vs actual margin in home-margin space: predicted home margin ≈ -spread_api
            market_pred_margin = -close_spread_api
            market_close_spread_mae.append(_mae(market_pred_margin, home_margin))
            market_ats = _ats_hit(home_margin, close_spread_api)
        else:
            market_ats = None

        if close_total is not None:
            market_close_total_mae.append(_mae(close_total, actual_total))

        if open_spread_api is not None and close_spread_api is not None:
            # Positive CLV for home side if close moves toward home (spread becomes more negative)
            market_clv_spread.append(open_spread_api - close_spread_api)

        proj = proj_by_game.get(game_uuid or "")
        if proj:
            n_with_proj += 1
            model_spread = _f(proj.get("spread_home"))
            model_total = _f(proj.get("total_mean"))
            model_hp = _f(proj.get("home_win_prob"))
            if model_spread is not None:
                model_spread_mae.append(_mae(-model_spread, home_margin))
                model_ats.append(_ats_hit(home_margin, model_spread))
                if open_spread_api is not None and close_spread_api is not None:
                    # Model CLV: did we beat the close relative to open?
                    # If model sided home (spread more negative than open), CLV = open - close
                    model_edge_vs_open = open_spread_api - model_spread
                    if abs(model_edge_vs_open) >= 0.5:
                        side_home = model_spread < open_spread_api
                        clv = (open_spread_api - close_spread_api) if side_home else (close_spread_api - open_spread_api)
                        model_clv_spread.append(clv)
            if model_total is not None:
                model_total_mae.append(_mae(model_total, actual_total))
                if open_total is not None and close_total is not None and abs(model_total - open_total) >= 1.0:
                    sided_over = model_total > open_total
                    clv_t = (close_total - open_total) if sided_over else (open_total - close_total)
                    model_clv_total.append(clv_t)
            if model_hp is not None:
                model_brier.append(_brier(model_hp, home_margin > 0))
            close_imp = _american_to_implied(close_ml)
            if close_imp is not None:
                market_brier.append(_brier(close_imp, home_margin > 0))

        bucket = by_season.setdefault(
            season,
            {"n": 0, "spread_mae": [], "total_mae": [], "n_owned_oc": 0},
        )
        bucket["n"] += 1
        if close_spread_api is not None:
            bucket["spread_mae"].append(_mae(-close_spread_api, home_margin))
        if close_total is not None:
            bucket["total_mae"].append(_mae(close_total, actual_total))
        if oc:
            bucket["n_owned_oc"] += 1

    def _avg(xs: List[float]) -> Optional[float]:
        return round(sum(xs) / len(xs), 4) if xs else None

    def _rate(xs: List[bool]) -> Optional[float]:
        return round(sum(1 for x in xs if x) / len(xs), 4) if xs else None

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "database_url_host": os.environ["DATABASE_URL"].split("@")[-1],
        "inventory": inventory,
        "coverage": {
            "schedule_games_2020_2025": len(sched),
            "owned_open_close_games": len(oc_by_game),
            "rows_with_owned_oc_join": n_owned_oc,
            "rows_using_nflverse_close_fallback": n_nflverse_close,
            "rows_with_model_projection": n_with_proj,
        },
        "market_close": {
            "spread_mae": _avg(market_close_spread_mae),
            "total_mae": _avg(market_close_total_mae),
            "ml_brier": _avg(market_brier),
            "open_to_close_spread_move_avg": _avg(market_clv_spread),
            "n_spread": len(market_close_spread_mae),
            "n_total": len(market_close_total_mae),
        },
        "model": {
            "spread_mae": _avg(model_spread_mae),
            "total_mae": _avg(model_total_mae),
            "ml_brier": _avg(model_brier),
            "ats_hit_rate": _rate(model_ats),
            "clv_spread_avg": _avg(model_clv_spread),
            "clv_spread_positive_rate": _rate([x > 0 for x in model_clv_spread]),
            "clv_total_avg": _avg(model_clv_total),
            "clv_total_positive_rate": _rate([x > 0 for x in model_clv_total]),
            "n_spread": len(model_spread_mae),
            "n_total": len(model_total_mae),
            "n_clv_spread": len(model_clv_spread),
            "n_clv_total": len(model_clv_total),
        },
        "by_season": {
            str(s): {
                "n": v["n"],
                "n_owned_oc": v["n_owned_oc"],
                "market_spread_mae": _avg(v["spread_mae"]),
                "market_total_mae": _avg(v["total_mae"]),
            }
            for s, v in sorted(by_season.items())
        },
        "notes": [
            "DB-first: no Odds API calls.",
            "Owned open/close from odds_snapshots min/max captured_at when present.",
            "nflverse spread_line/total_line used as close fallback (sign-converted).",
            "Model metrics require nfl_market_projections rows joined on games.id.",
        ],
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2) + "\n")
    md = [
        "# NFL odds open/close grading",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "## Inventory",
        "",
        "```json",
        json.dumps(inventory, indent=2),
        "```",
        "",
        "## Coverage",
        "",
        "```json",
        json.dumps(report["coverage"], indent=2),
        "```",
        "",
        "## Market close",
        "",
        "```json",
        json.dumps(report["market_close"], indent=2),
        "```",
        "",
        "## Model",
        "",
        "```json",
        json.dumps(report["model"], indent=2),
        "```",
        "",
    ]
    OUT_MD.write_text("\n".join(md) + "\n")
    print(json.dumps(report, indent=2))
    print(f"\nWrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
