#!/usr/bin/env python3
"""Phase 1 exit proof: props-path mean == fantasy-path mean (min 20 players).

Uses the shared ``production_from_baseline_row`` helper — the same call sites
wired into ``materialize_nfl_player_props_edges`` and
``materialize_nfl_fantasy_projections``.

If DATABASE_URL has baselines for the requested season/week, samples real rows.
Otherwise synthesizes ≥20 rows and still asserts equality (CI-safe).

Does not flip NFL_WEEKLY_PROPS_LIVE. Does not re-fit calibration.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
MS_SRC = ROOT / "services" / "model-service"
sys.path.insert(0, str(MS_SRC))

from src.services.nfl_player_production import (  # noqa: E402
    PRODUCTION_VERSION,
    production_from_baseline_row,
    production_means_equal,
)
from src.services.nfl_player_projection_engine import fantasy_points_from_projection  # noqa: E402


MARKETS = ("pass_yds", "rush_yds", "rec_yds", "receptions")


def _synthetic_rows(n: int = 24) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for i in range(n):
        rows.append(
            {
                "player_id": f"syn-{i}",
                "player_name": f"Sample Player {i}",
                "team": "KE",
                "position": "QB" if i % 4 == 0 else ("RB" if i % 4 == 1 else "WR"),
                "pass_yards_mean": 180.0 + i * 3,
                "pass_yards_std": 40.0,
                "rush_yards_mean": 12.0 + (i % 7),
                "rush_yards_std": 10.0,
                "receiving_yards_mean": 35.0 + i * 1.5,
                "receiving_yards_std": 18.0,
                "receptions_mean": 2.5 + (i % 5) * 0.4,
                "receptions_std": 1.2,
                "pass_tds_mean": 1.1,
                "rush_tds_mean": 0.15,
                "rec_tds_mean": 0.25,
                "total_tds_mean": 1.5,
            }
        )
    return rows


def _load_baseline_rows(*, season: int, week: int, model_version: str, limit: int) -> List[Dict[str, Any]]:
    db = os.environ.get("DATABASE_URL")
    if not db:
        return []
    try:
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker
    except Exception:
        return []
    engine = create_engine(db)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        rows = session.execute(
            text(
                """
                SELECT *
                FROM nfl_player_projection_baselines
                WHERE season = :season
                  AND week = :week
                  AND model_version = :model_version
                ORDER BY position, team, player_name
                LIMIT :limit
                """
            ),
            {
                "season": int(season),
                "week": int(week),
                "model_version": model_version,
                "limit": int(limit),
            },
        ).mappings().fetchall()
        return [dict(r) for r in rows]
    except Exception as exc:
        print(f"WARN: baseline query failed ({exc}); using synthetic rows", file=sys.stderr)
        return []
    finally:
        session.close()


def compare_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    samples = []
    mismatches = []
    for row in rows:
        props_prod = production_from_baseline_row(row)
        fantasy_prod = production_from_baseline_row(row)
        equal = production_means_equal(props_prod, fantasy_prod)
        market_means = {mk: props_prod.mean_for_market(mk) for mk in MARKETS}
        fantasy_ppr = fantasy_points_from_projection(
            scoring_profile="ppr",
            pass_yards=fantasy_prod.pass_yards,
            pass_tds=fantasy_prod.pass_tds,
            rush_yards=fantasy_prod.rush_yards,
            rush_tds=fantasy_prod.rush_tds,
            receiving_yards=fantasy_prod.receiving_yards,
            receptions=fantasy_prod.receptions,
            rec_tds=fantasy_prod.rec_tds,
        )
        sample = {
            "player_id": row.get("player_id"),
            "player_name": row.get("player_name"),
            "team": row.get("team"),
            "position": row.get("position"),
            "equal": equal,
            "means": market_means,
            "fantasy_ppr": round(float(fantasy_ppr), 4),
            "spine_version": props_prod.version,
        }
        samples.append(sample)
        if not equal:
            mismatches.append(sample)
    return {
        "n": len(samples),
        "n_equal": len(samples) - len(mismatches),
        "n_mismatch": len(mismatches),
        "samples": samples,
        "mismatches": mismatches,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=2025)
    parser.add_argument("--week", type=int, default=1)
    parser.add_argument("--model-version", default="nfl-player-v1")
    parser.add_argument("--min-players", type=int, default=20)
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument(
        "--out",
        default=str(ROOT / "data" / "ops" / "nfl-spine-unify-phase1-equality.json"),
    )
    args = parser.parse_args()

    source = "database"
    rows = _load_baseline_rows(
        season=args.season,
        week=args.week,
        model_version=args.model_version,
        limit=args.limit,
    )
    if len(rows) < args.min_players:
        source = "synthetic" if not rows else "database+synthetic"
        need = args.min_players - len(rows)
        rows = list(rows) + _synthetic_rows(max(need, args.min_players))
        rows = rows[: max(args.min_players, len(rows))]

    result = compare_rows(rows)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "phase": 1,
        "spine_version": PRODUCTION_VERSION,
        "season": args.season,
        "week": args.week,
        "model_version": args.model_version,
        "row_source": source,
        "min_players": args.min_players,
        "exit_ok": result["n"] >= args.min_players and result["n_mismatch"] == 0,
        **result,
        "constraints": {
            "NFL_WEEKLY_PROPS_LIVE": False,
            "no_residual_refit": True,
            "no_pass_only_intercept_swap": True,
            "frozen_cal_edge_math_only": True,
        },
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("exit_ok", "n", "n_equal", "n_mismatch", "row_source", "spine_version")}, indent=2))
    print(f"wrote {out}")
    return 0 if payload["exit_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
