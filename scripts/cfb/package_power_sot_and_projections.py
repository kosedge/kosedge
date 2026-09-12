#!/usr/bin/env python3
"""Package the CFB Power SoT + frozen-SoT season projection artifact.

Research only. used_in_spread stays false. Official ESPN slate. N=10000.

Default stamps are POWER_AS_OF=2026-08-14 and overwrite week0-close canaries.
For a provenance remint of the close model, pass ``--stamps week0-close``
and keep the original W0 pack under data/ops/cfb-w0-canary-20260831/.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")


def main() -> None:
    from src.services.cfb_season_engine import build_packaged_universe
    from src.services.cfb_season_engine.power_sot import (
        CLOSE_AS_OF,
        CLOSE_POWER_VERSION,
        CLOSE_PROJECTION_ARTIFACT_ID,
        DEFAULT_N_SIMS,
        POWER_AS_OF,
        POWER_VERSION,
        PROJECTION_ARTIFACT_ID,
        package_research_desk,
    )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stamps",
        choices=("research", "week0-close"),
        default="research",
        help="research=2026-08-14 (overwrites canaries); week0-close=2026-08-31",
    )
    parser.add_argument("--n-sims", type=int, default=DEFAULT_N_SIMS)
    parser.add_argument("--seed", type=int, default=20260831)
    args = parser.parse_args()

    if args.stamps == "week0-close":
        as_of = CLOSE_AS_OF
        power_version = CLOSE_POWER_VERSION
        artifact_id = CLOSE_PROJECTION_ARTIFACT_ID
        seed = args.seed
    else:
        as_of = POWER_AS_OF
        power_version = POWER_VERSION
        artifact_id = PROJECTION_ARTIFACT_ID
        seed = 2026 if args.seed == 20260831 else args.seed

    universe = build_packaged_universe(2026)
    paths = package_research_desk(
        universe,
        n_sims=args.n_sims,
        seed=seed,
        as_of=as_of,
        power_version=power_version,
        artifact_id=artifact_id,
    )
    print(f"power_version={power_version}")
    print(f"artifact={artifact_id}")
    print(f"as_of={as_of}")
    for key, path in paths.items():
        print(f"  {key}: {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
