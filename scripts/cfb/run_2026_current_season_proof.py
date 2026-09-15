#!/usr/bin/env python3
"""Retrieve 2026 CFB PBP + schedule via SportsDataverse (no CFBD key).

Writes bulky parquet under gitignored data/cfb/research/pbp_current/as_of_YYYYMMDD/.
Writes committed summaries under data/ops/cfb-2026-current-season-proof-20260915/.

Does not touch /Volumes/KosEdgeData/raw/cfb/pbp/ (2014–2025 canonical lake).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.cfb_warehouse.current_season_2026 import (  # noqa: E402
    committed_ops_dir,
    research_dest_dir,
    run_proof,
    today_as_of,
    write_json,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--as-of",
        default=today_as_of(),
        help="YYYYMMDD stamp for the versioned current-season folder",
    )
    parser.add_argument(
        "--skip-espn-sample",
        action="store_true",
        help="Skip the public ESPN summary probe for one completed game",
    )
    args = parser.parse_args(argv)

    dest = research_dest_dir(args.as_of)
    proof = run_proof(
        as_of=args.as_of,
        dest_dir=dest,
        include_espn_sample=not args.skip_espn_sample,
    )
    ops = committed_ops_dir()
    write_json(ops / "evidence.json", proof)
    write_json(ops / "coverage.json", proof["coverage"])
    write_json(ops / "field_support.json", proof["pbp"]["field_support"])
    write_json(ops / "path_convention.json", proof["path_convention"])
    write_json(dest / "proof_summary.json", proof)

    cov = proof["coverage"]
    print(f"dest={dest}")
    print(f"hd_target={proof['path_convention']['current_season_hd_target']}")
    print(
        f"pbp plays={proof['pbp']['plays']} games={proof['pbp']['games']} "
        f"bytes={proof['pbp']['bytes']}"
    )
    print(
        f"schedule games={cov['schedule_games']} completed={cov['completed_on_schedule']} "
        f"completed_in_pbp={cov['completed_in_pbp']} "
        f"completed_missing_pbp={cov['completed_missing_pbp']}"
    )
    print(f"ops={ops}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
