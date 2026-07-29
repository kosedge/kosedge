#!/usr/bin/env python3
"""Regenerate player season-total CSVs into an existing preseason-sim bundle.

Does NOT re-run the 100k team/futures Monte Carlo — reuses
`quality_checks.json` → `expected_playoff_games_by_team` from the bundle.

Usage:
  DATABASE_URL=postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge \\
    PYTHONPATH=services/data-platform-nfl/src:. \\
    .venv/bin/python scripts/nfl/regen_player_season_totals.py \\
      --bundle data/ops/nfl-preseason-sim-2026-20260729T160818Z
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "data-platform-nfl" / "src"))

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge"
)

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from data_platform_nfl.player_season_totals import (  # noqa: E402
    generate_and_write_player_season_totals,
)


def _db_url() -> str:
    url = os.environ["DATABASE_URL"]
    if url.startswith("postgresql://") and "+psycopg" not in url:
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if "@postgres:" in url:
        return url.replace("@postgres:", "@127.0.0.1:")
    return url


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--bundle",
        type=Path,
        default=ROOT / "data/ops/nfl-preseason-sim-2026-20260729T160818Z",
    )
    ap.add_argument("--season", type=int, default=2026)
    ap.add_argument("--model-version", default="nfl-player-v1")
    args = ap.parse_args()
    bundle: Path = args.bundle
    if not bundle.is_dir():
        raise SystemExit(f"bundle not found: {bundle}")
    qc_path = bundle / "quality_checks.json"
    if not qc_path.exists():
        raise SystemExit(f"missing {qc_path}")
    qc = json.loads(qc_path.read_text(encoding="utf-8"))
    expected = qc.get("expected_playoff_games_by_team") or {}
    if not expected:
        raise SystemExit("quality_checks.json missing expected_playoff_games_by_team")

    engine = create_engine(_db_url())
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        summary = generate_and_write_player_season_totals(
            session,
            season=args.season,
            out_dir=str(bundle),
            expected_playoff_games_by_team={str(k): float(v) for k, v in expected.items()},
            model_version=args.model_version,
        )
    finally:
        session.close()

    # Refresh quality_checks player section + run_summary honesty fields.
    qc["player_season_totals"] = summary
    qc_path.write_text(json.dumps(qc, indent=2) + "\n", encoding="utf-8")

    rs_path = bundle / "run_summary.json"
    rs = json.loads(rs_path.read_text(encoding="utf-8")) if rs_path.exists() else {}
    rs.update(
        {
            "player_totals_regenerated_at_utc": datetime.now(timezone.utc).isoformat(),
            "player_publish_ready": summary.get("publish_ready"),
            "player_projection_model_version": args.model_version,
            "qb_starter_lock": summary.get("qb_starter_lock"),
            "pass_leader_quality": {
                "dual_full_volume_qb_rooms_count": (
                    (summary.get("pass_leader_quality") or {}).get(
                        "dual_full_volume_qb_rooms_count"
                    )
                ),
                "publish_ready": (summary.get("pass_leader_quality") or {}).get(
                    "publish_ready"
                ),
                "top_passer": (summary.get("pass_leader_quality") or {}).get("top_passer"),
            },
            "skill_leader_quality": {
                "publish_ready_skill": (
                    (summary.get("skill_leader_quality") or {}).get("publish_ready_skill")
                ),
                "top_rusher": (summary.get("skill_leader_quality") or {}).get("top_rusher"),
                "top_receiver": (summary.get("skill_leader_quality") or {}).get(
                    "top_receiver"
                ),
                "wr_with_1200_plus_count": (
                    (summary.get("skill_leader_quality") or {}).get("wr_with_1200_plus_count")
                ),
            },
        }
    )
    why = []
    pq = summary.get("pass_leader_quality") or {}
    sq = summary.get("skill_leader_quality") or {}
    if not pq.get("publish_ready"):
        why.append(
            f"pass_gate dual_rooms={pq.get('dual_full_volume_qb_rooms_count')} "
            f"top={pq.get('top_passer')}"
        )
    if not sq.get("publish_ready_skill"):
        why.append(
            f"skill_gate rush>={sq.get('top_rusher_yards_gte_1400')} "
            f"rec>={sq.get('top_receiver_yards_gte_1300')} "
            f"wr1200={sq.get('wr_with_1200_plus_count')}"
        )
    rs["player_publish_ready_why"] = why
    rs_path.write_text(json.dumps(rs, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
