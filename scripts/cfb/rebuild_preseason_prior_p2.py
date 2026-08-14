#!/usr/bin/env python3
"""Rebuild the 2026 CFB preseason prior (P2) for official FBS.

Usage:
  python scripts/cfb/rebuild_preseason_prior_p2.py
  python scripts/cfb/rebuild_preseason_prior_p2.py --from-hd   # season finals if mounted
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.cfb_warehouse.paths import clean_dir, hd_mounted  # noqa: E402
from src.services.cfb_warehouse.preseason_prior import (  # noqa: E402
    PRIOR_VERSION,
    USED_IN_SPREAD,
    rebuild_p2_from_packaged,
    write_preseason_priors,
)


def _season_finals():
    path = clean_dir(prefer_hd=True) / "efficiency" / "team_season_efficiency.parquet"
    if not path.is_file():
        return None
    import pandas as pd

    return pd.read_parquet(path).to_dict(orient="records")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-hd", action="store_true")
    parser.add_argument("--as-of", default="2026-08-13")
    args = parser.parse_args(argv)
    finals = _season_finals() if args.from_hd else None
    if args.from_hd and finals is None:
        print("HD season finals missing; falling back to stored program net", file=sys.stderr)
    rows = rebuild_p2_from_packaged(
        prior_year=2026,
        as_of=args.as_of,
        season_finals=finals,
    )
    written = write_preseason_priors(
        rows, prior_year=2026, prefer_hd=bool(args.from_hd and hd_mounted()), package_json=True
    )
    smell = [
        {
            "team": r["team_id"],
            "rank": r["rank"],
            "mean": r["mean_points"],
            "sigma": r["sigma_points"],
            "qb_class": r["components"]["qb_class"],
            "qb_sigma": r["components"]["qb_sigma"],
            "conference": r.get("conference"),
            "missing": r["components"]["missing_data"],
        }
        for r in rows
        if r["team_id"]
        in {"OSU", "UGA", "ALA", "MICH", "FSU", "LSU", "TEX", "ORE", "PSU", "BALL", "MASS", "MIZZ"}
    ]
    report = {
        "prior_version": PRIOR_VERSION,
        "used_in_spread": USED_IN_SPREAD,
        "n": len(rows),
        "hd_finals": finals is not None,
        "written": written,
        "smell": smell,
    }
    out = ROOT / "data" / "ops" / "cfb-p2-prior-smell-20260813.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
