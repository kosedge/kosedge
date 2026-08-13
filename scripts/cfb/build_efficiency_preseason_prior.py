#!/usr/bin/env python3
"""Phase A then B: opponent-adj efficiency → preseason prior v1.

Usage:
  python scripts/cfb/build_efficiency_preseason_prior.py
  python scripts/cfb/build_efficiency_preseason_prior.py --skip-prior
  python scripts/cfb/build_efficiency_preseason_prior.py --pbp-seasons 2022-2025
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.cfb_warehouse.efficiency_adj import (  # noqa: E402
    PBP_SEASONS,
    build_efficiency,
    season_final_from_snapshots,
)
from src.services.cfb_warehouse.paths import clean_dir  # noqa: E402
from src.services.cfb_warehouse.preseason_prior import (  # noqa: E402
    build_preseason_priors,
    write_preseason_priors,
)


def _parse_seasons(raw: str) -> list[int]:
    raw = raw.strip()
    if "-" in raw and "," not in raw:
        a, b = raw.split("-", 1)
        return list(range(int(a), int(b) + 1))
    return [int(s.strip()) for s in raw.split(",") if s.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pbp-seasons", default="2014-2025")
    parser.add_argument("--prior-year", type=int, default=2026)
    parser.add_argument("--skip-efficiency", action="store_true")
    parser.add_argument("--skip-prior", action="store_true")
    parser.add_argument("--repo-fallback", action="store_true")
    args = parser.parse_args(argv)
    prefer_hd = not args.repo_fallback
    out: dict = {}
    if not args.skip_efficiency:
        seasons = _parse_seasons(args.pbp_seasons) or list(PBP_SEASONS)
        out["efficiency"] = build_efficiency(seasons=seasons, prefer_hd=prefer_hd)
    if not args.skip_prior:
        import pandas as pd

        path = clean_dir(prefer_hd=prefer_hd) / "efficiency" / "team_season_efficiency.parquet"
        if not path.exists():
            print(f"Missing {path}; run efficiency first", file=sys.stderr)
            return 1
        finals = pd.read_parquet(path).to_dict(orient="records")
        rows = build_preseason_priors(finals, prior_year=args.prior_year)
        out["prior"] = write_preseason_priors(
            rows, prior_year=args.prior_year, prefer_hd=prefer_hd
        )
        # Smell-test slice for the ops note.
        want = ["UGA", "OSU", "TEX", "ALA", "FSU", "COLO", "PSU", "BALL", "KENT", "MASS"]
        by = {r["team_id"]: r for r in rows}
        out["smell"] = {
            t: {
                "mean": by[t]["mean_points"],
                "sigma": by[t]["sigma_points"],
                "rank": by[t]["rank"],
                "qb": by[t]["components"]["qb_class"],
            }
            for t in want
            if t in by
        }
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
