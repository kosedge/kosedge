#!/usr/bin/env python3
"""Close CFB Week 0 without a power refit.

Idempotent: writes Week-0 FBS finals into the official schedule pack, advances
as_of, rebuilds power/projections from the existing composed universe (no
in_season_update efficiency moves), then rebuilds KEI + futures.

Usage:
  python scripts/cfb/close_week0.py
  python scripts/cfb/close_week0.py --n-sims 2000
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
sys.path.insert(0, str(MS))
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

SCHEDULE_PATH = MS / "src/services/cfb_season_engine/data/cfb_official_schedule_2026.json"

# Official Week-0 FBS finals (2026-08-29/30). Home/away match schedule codes.
# Sources: Yahoo Sports Week 0 recap, ESPN / USC athletics box scores.
# Close ≠ train: these lock sim start-state only; power is not refit.
WEEK0_FINALS = {
    ("UNC", "TCU"): (15, 10),
    ("SJSU", "USC"): (26, 42),
    ("NCSU", "UVA"): (8, 34),
    ("HAW", "STAN"): (27, 37),
    ("NMSU", "FSU"): (17, 34),
    ("MEM", "UNLV"): (27, 21),
}

AS_OF = "2026-08-31"


def apply_week0_finals(blob: dict) -> int:
    n = 0
    for row in blob.get("games") or []:
        try:
            week = int(row.get("week"))
        except (TypeError, ValueError):
            continue
        if week != 0:
            continue
        key = (str(row.get("away") or "").upper(), str(row.get("home") or "").upper())
        if key not in WEEK0_FINALS:
            continue
        away_s, home_s = WEEK0_FINALS[key]
        row["away_score"] = away_s
        row["home_score"] = home_s
        row["status"] = "final"
        n += 1
    blob["as_of"] = AS_OF
    blob["week0_closed"] = True
    blob["week0_close_note"] = (
        "FBS finals locked for research sim start-state. Power SoT not refit "
        "from these results (close ≠ train)."
    )
    return n


def _run_kei_futures(as_of: str, seed: int) -> None:
    path = ROOT / "scripts/cfb/build_cfb_kei_futures_2026.py"
    spec = importlib.util.spec_from_file_location("build_cfb_kei_futures_2026", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.AS_OF = as_of
    mod.SEED = seed
    mod.main()


def main() -> None:
    n_sims = 10_000
    seed = 20260831
    if "--n-sims" in sys.argv:
        i = sys.argv.index("--n-sims")
        n_sims = int(sys.argv[i + 1])

    blob = json.loads(SCHEDULE_PATH.read_text(encoding="utf-8"))
    n = apply_week0_finals(blob)
    SCHEDULE_PATH.write_text(json.dumps(blob, indent=2) + "\n", encoding="utf-8")
    print(f"week0 finals written: {n} (as_of={AS_OF})")

    from src.services.cfb_season_engine import loaders
    from src.services.cfb_season_engine import build_packaged_universe
    from src.services.cfb_season_engine.power_sot import (
        CLOSE_AS_OF,
        CLOSE_POWER_VERSION,
        CLOSE_PROJECTION_ARTIFACT_ID,
        package_research_desk,
    )

    loaders._PACKAGED_UNIVERSE_CACHE.clear()
    universe = build_packaged_universe(2026)
    print(
        f"universe schedule={len(universe.schedule)} "
        f"official={universe.notes.get('official_schedule')} "
        f"schedule_as_of={universe.notes.get('schedule_as_of')}"
    )
    paths = package_research_desk(
        universe,
        n_sims=n_sims,
        seed=seed,
        as_of=CLOSE_AS_OF,
        power_version=CLOSE_POWER_VERSION,
        artifact_id=CLOSE_PROJECTION_ARTIFACT_ID,
        write_web_mirrors=True,
    )
    for k, p in paths.items():
        print(f"  {k}: {p}")

    _run_kei_futures(CLOSE_AS_OF, seed)
    print("close_week0 complete")


if __name__ == "__main__":
    main()
