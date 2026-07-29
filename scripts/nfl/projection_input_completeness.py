#!/usr/bin/env python3
"""Audit projection input completeness for recent NFL boards (sim quality).

Checks whether latest pre-kickoff projections serialize key KAV / rest /
injury / weather / travel fields used by the simulator.

Writes: data/ops/nfl-projection-input-completeness.json
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge"
)

from sqlalchemy import create_engine, text  # noqa: E402

OUT = ROOT / "data" / "ops" / "nfl-projection-input-completeness.json"

REQUIRED_INPUT_KEYS = (
    "home_kav_net_5g",
    "away_kav_net_5g",
    "rest_days_home",
    "rest_days_away",
    "injury_nowcast_impact_home",
    "injury_nowcast_impact_away",
)


def _db_url() -> str:
    url = os.environ["DATABASE_URL"]
    if url.startswith("postgresql://") and "+psycopg" not in url:
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


def main() -> int:
    engine = create_engine(_db_url())
    with engine.connect() as conn:
        rows = list(
            conn.execute(
                text(
                    """
                    SELECT DISTINCT ON (mp.game_id)
                      g.external_id,
                      s.season_year,
                      mp.created_at,
                      mp.projection
                    FROM nfl_market_projections mp
                    JOIN games g ON g.id = mp.game_id
                    JOIN seasons s ON s.id = g.season_id
                    JOIN leagues l ON l.id = s.league_id
                    WHERE l.code = 'nfl'
                      AND s.season_year IN (2025, 2026)
                      AND mp.spread_home IS NOT NULL
                    ORDER BY mp.game_id,
                      CASE WHEN mp.projection->'audit'->>'pipeline_run_at' IS NOT NULL THEN 0 ELSE 1 END,
                      COALESCE(
                        (mp.projection->'audit'->>'pipeline_run_at')::timestamptz,
                        mp.created_at
                      ) DESC
                    """
                )
            ).mappings()
        )

    by_season: Dict[int, Dict[str, Any]] = {}
    for r in rows:
        season = int(r["season_year"])
        bucket = by_season.setdefault(
            season,
            {"n": 0, "missing": {k: 0 for k in REQUIRED_INPUT_KEYS}, "has_inputs_obj": 0},
        )
        bucket["n"] += 1
        proj = r["projection"] if isinstance(r["projection"], dict) else {}
        inputs = proj.get("inputs") if isinstance(proj.get("inputs"), dict) else {}
        if inputs:
            bucket["has_inputs_obj"] += 1
        for k in REQUIRED_INPUT_KEYS:
            if inputs.get(k) is None:
                bucket["missing"][k] += 1

    for season, bucket in by_season.items():
        n = max(bucket["n"], 1)
        bucket["pct_with_inputs_obj"] = bucket["has_inputs_obj"] / n
        bucket["pct_missing"] = {k: bucket["missing"][k] / n for k in REQUIRED_INPUT_KEYS}

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "required_input_keys": list(REQUIRED_INPUT_KEYS),
        "by_season": by_season,
        "notes": [
            "Missing KAV/rest/injury fields degrade auditability even if sim used them live.",
            "Weather/travel are optional (null outdoors/dome) — not counted as required.",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["by_season"], indent=2))
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
