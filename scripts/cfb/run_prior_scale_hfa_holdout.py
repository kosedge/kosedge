#!/usr/bin/env python3
"""Fit CFB prior scale + HFA on train years; evaluate holdout. No EPA. No KEI.

Usage:
  python scripts/cfb/run_prior_scale_hfa_holdout.py
  python scripts/cfb/run_prior_scale_hfa_holdout.py --train 2021-2023 --holdout 2024-2025
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.cfb_warehouse.paths import clean_dir  # noqa: E402
from src.services.cfb_warehouse.scale_hfa import (  # noqa: E402
    HOLDOUT_YEARS,
    TRAIN_YEARS,
    run_holdout_calibration,
    write_pack,
)
from src.services.cfb_warehouse.walkforward import build_program_priors  # noqa: E402


def _read(path: Path):
    import pandas as pd

    return pd.read_parquet(path).to_dict(orient="records")


def _parse_years(raw: str) -> list[int]:
    raw = raw.strip()
    if "-" in raw and "," not in raw:
        a, b = raw.split("-", 1)
        return list(range(int(a), int(b) + 1))
    return [int(s.strip()) for s in raw.split(",") if s.strip()]


def _join(games, closes):
    by_id = {str(c.get("game_id")): c for c in closes}
    out = []
    for g in games:
        row = dict(g)
        c = by_id.get(str(g.get("game_id")))
        if not c:
            out.append(row)
            continue
        for k in (
            "close_spread_home",
            "open_spread_home",
            "close_total",
            "book",
            "source",
            "line_fidelity",
            "close_captured_at",
            "available_at",
        ):
            if c.get(k) is not None:
                row[k] = c.get(k)
        out.append(row)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", default="2020-2023")
    parser.add_argument("--holdout", default="2024-2025")
    parser.add_argument("--repo-fallback", action="store_true")
    parser.add_argument("--example-id", default="401628323")
    args = parser.parse_args(argv)
    train_years = _parse_years(args.train) or list(TRAIN_YEARS)
    holdout_years = _parse_years(args.holdout) or list(HOLDOUT_YEARS)
    clean = clean_dir(prefer_hd=not args.repo_fallback)
    games_path = clean / "games.parquet"
    closes_path = clean / "closing_lines.parquet"
    season_path = clean / "efficiency" / "team_season_efficiency.parquet"
    missing = [p for p in (games_path, closes_path, season_path) if not p.is_file()]
    if missing:
        print(f"Missing {missing}", file=sys.stderr)
        return 1
    years = sorted(set(train_years) | set(holdout_years))
    games = [g for g in _read(games_path) if int(g.get("season") or 0) in set(years)]
    joined = _join(games, _read(closes_path))
    priors = build_program_priors(_read(season_path), years)
    pack = run_holdout_calibration(
        joined,
        priors,
        train_years=train_years,
        holdout_years=holdout_years,
        example_id=args.example_id,
    )
    packaged = write_pack(pack)
    out_dir = clean / "walkforward"
    out_dir.mkdir(parents=True, exist_ok=True)
    full_path = out_dir / "prior_scale_hfa_holdout.json"
    full_path.write_text(json.dumps(pack, indent=2, default=str) + "\n")
    print(
        json.dumps(
            {
                "adopted": pack["adopted"],
                "adopt_reason": pack["adopt_reason"],
                "fitted_scale": pack["fitted_scale"],
                "fitted_hfa": pack["fitted_hfa"],
                "packaged": str(packaged),
                "full": str(full_path),
                "train_w0_4": {
                    "baseline": pack["train"]["baseline"]["w0_4"],
                    "calibrated": pack["train"]["calibrated"]["w0_4"],
                },
                "holdout_w0_4": {
                    "baseline": pack["holdout"]["baseline"]["w0_4"],
                    "calibrated": pack["holdout"]["calibrated"]["w0_4"],
                },
                "holdout_w0_1": {
                    "baseline": pack["holdout"]["baseline"]["w0_1"],
                    "calibrated": pack["holdout"]["calibrated"]["w0_1"],
                },
                "example_baseline": pack.get("example_baseline"),
                "example_calibrated": pack.get("example_calibrated"),
                "exclusions": pack.get("exclusions"),
            },
            indent=2,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
