#!/usr/bin/env python3
"""Backfill KAV fields into nfl_market_projections.projection->inputs.

Historical 2025 boards serialized EPA matchup inputs but omitted KAV keys
(added later to NflGameInputs / matchup_pack_to_sim_input_kwargs). This patch
restores audit completeness from nfl_dp_matchup_features_weekly without
changing spread/total markets.

Does NOT invent 2026 KAV when matchup pack has nulls.
Writes: data/ops/nfl-kav-projection-inputs-backfill.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge"
)
OUT = ROOT / "data" / "ops" / "nfl-kav-projection-inputs-backfill.json"

KAV_KEYS = (
    "home_kav_offense_5g",
    "away_kav_offense_5g",
    "home_kav_defense_5g",
    "away_kav_defense_5g",
    "home_kav_net_5g",
    "away_kav_net_5g",
    "kav_as_of_week",
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
    updated = 0
    skipped_no_pack = 0
    skipped_no_kav = 0
    scanned = 0
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT mp.id AS proj_id, g.external_id, s.season_year,
                       mp.projection, mf.home_kav_offense_5g, mf.away_kav_offense_5g,
                       mf.home_kav_defense_5g, mf.away_kav_defense_5g,
                       mf.home_kav_net_5g, mf.away_kav_net_5g, mf.kav_as_of_week
                FROM nfl_market_projections mp
                JOIN games g ON g.id = mp.game_id
                JOIN seasons s ON s.id = g.season_id
                JOIN leagues l ON l.id = s.league_id
                LEFT JOIN nfl_dp_matchup_features_weekly mf
                  ON mf.game_id = g.external_id AND mf.season = s.season_year
                WHERE l.code = 'nfl'
                  AND s.season_year IN (2025, 2026)
                  AND mp.projection IS NOT NULL
                """
            )
        ).mappings()

        for r in rows:
            scanned += 1
            proj = r["projection"] if isinstance(r["projection"], dict) else {}
            inputs = proj.get("inputs") if isinstance(proj.get("inputs"), dict) else {}
            if r["home_kav_net_5g"] is None and r["away_kav_net_5g"] is None:
                if r["external_id"] is None:
                    skipped_no_pack += 1
                else:
                    skipped_no_kav += 1
                continue
            # Already complete
            if inputs.get("home_kav_net_5g") is not None and inputs.get("away_kav_net_5g") is not None:
                continue
            patch = {
                "home_kav_offense_5g": float(r["home_kav_offense_5g"]) if r["home_kav_offense_5g"] is not None else None,
                "away_kav_offense_5g": float(r["away_kav_offense_5g"]) if r["away_kav_offense_5g"] is not None else None,
                "home_kav_defense_5g": float(r["home_kav_defense_5g"]) if r["home_kav_defense_5g"] is not None else None,
                "away_kav_defense_5g": float(r["away_kav_defense_5g"]) if r["away_kav_defense_5g"] is not None else None,
                "home_kav_net_5g": float(r["home_kav_net_5g"]) if r["home_kav_net_5g"] is not None else None,
                "away_kav_net_5g": float(r["away_kav_net_5g"]) if r["away_kav_net_5g"] is not None else None,
                "kav_as_of_week": int(r["kav_as_of_week"]) if r["kav_as_of_week"] is not None else None,
            }
            new_inputs = dict(inputs)
            new_inputs.update(patch)
            new_proj = dict(proj)
            new_proj["inputs"] = new_inputs
            conn.execute(
                text(
                    """
                    UPDATE nfl_market_projections
                    SET projection = CAST(:projection AS jsonb)
                    WHERE id = :id
                    """
                ),
                {"id": r["proj_id"], "projection": json.dumps(new_proj)},
            )
            updated += 1

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scanned": scanned,
        "updated": updated,
        "skipped_no_pack": skipped_no_pack,
        "skipped_no_kav": skipped_no_kav,
        "keys": list(KAV_KEYS),
        "note": "Audit-only backfill; markets unchanged. 2026 KAV null until weekly features exist.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
