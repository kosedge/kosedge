#!/usr/bin/env python3
"""Package the CFB Power SoT + frozen-SoT season projection artifact.

Research only. used_in_spread stays false. Official ESPN slate. N=10000.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")


def main() -> None:
    from src.services.cfb_season_engine import build_packaged_universe
    from src.services.cfb_season_engine.power_sot import (
        DEFAULT_N_SIMS,
        POWER_VERSION,
        PROJECTION_ARTIFACT_ID,
        package_research_desk,
    )

    universe = build_packaged_universe(2026)
    paths = package_research_desk(universe, n_sims=DEFAULT_N_SIMS, seed=2026)
    print(f"power_version={POWER_VERSION}")
    print(f"artifact={PROJECTION_ARTIFACT_ID}")
    for key, path in paths.items():
        print(f"  {key}: {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
