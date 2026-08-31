#!/usr/bin/env python3
"""Chapter 1 Phase 1B — fit named bucket margin→points map (train 2020–24).

Reads a replay JSON from cfb_ch1_replay_v015_vs_close.py (--include-rows).
Writes named scales to data/ops/cfb-ch1-bucket-map-v1.json.

Does not mutate engine files — apply constants via priors after review.

Usage:
  python3 scripts/cfb/cfb_ch1_replay_v015_vs_close.py --seasons 2020,2021,2022,2023,2024,2025 \\
    --include-rows --json > /tmp/cfb-ch1-replay-full.json
  python3 scripts/cfb/cfb_ch1_bucket_map_fit.py --replay /tmp/cfb-ch1-replay-full.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

ROOT = Path(__file__).resolve().parents[2]

BUCKETS = ("pick", "short", "mid", "long", "cupcake")
MAP_ID = "cfb-bucket-margin-map-v1-20260831"


def bucket_abs(abs_m: float) -> str:
    if abs_m < 3:
        return "pick"
    if abs_m < 7:
        return "short"
    if abs_m < 14:
        return "mid"
    if abs_m < 21:
        return "long"
    return "cupcake"


def fit_scales(
    train: Sequence[Dict[str, Any]],
    *,
    freeze: Sequence[str],
    lo: float = 0.90,
    hi: float = 1.25,
    min_n: int = 30,
) -> Dict[str, Any]:
    by: Dict[str, List[tuple]] = defaultdict(list)
    for r in train:
        by[r["bucket_raw_margin"]].append(
            (float(r["raw_margin_home"]), -float(r["close_spread_home"]))
        )
    scales = {b: 1.0 for b in BUCKETS}
    n_by = {b: len(by[b]) for b in BUCKETS}
    ols_raw = {}
    for b in BUCKETS:
        xs = by[b]
        if not xs:
            ols_raw[b] = None
            continue
        num = sum(t * m for m, t in xs)
        den = sum(m * m for m, _ in xs) or 1.0
        ols_raw[b] = num / den
        if b in freeze or len(xs) < min_n:
            continue
        scales[b] = max(lo, min(hi, ols_raw[b]))
    return {"scales": scales, "ols_uncapped": ols_raw, "n_by_raw_bucket": n_by}


def mae_by_close_bucket(
    rows: Sequence[Dict[str, Any]], scales: Dict[str, float]
) -> Dict[str, Any]:
    by: Dict[str, List[float]] = defaultdict(list)
    for r in rows:
        mapped = float(r["raw_margin_home"]) * float(
            scales[bucket_abs(abs(float(r["raw_margin_home"])))]
        )
        spread = -mapped
        by[r["bucket_close"]].append(spread - float(r["close_spread_home"]))
    out = {}
    for b in BUCKETS:
        xs = by[b]
        out[b] = {
            "n": len(xs),
            "mae": (sum(abs(x) for x in xs) / len(xs)) if xs else None,
            "mean_residual": (sum(xs) / len(xs)) if xs else None,
        }
    return out


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--replay", required=True, type=Path)
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT / "data/ops/cfb-ch1-bucket-map-v1.json",
    )
    args = ap.parse_args(argv)
    payload = json.loads(args.replay.read_text(encoding="utf-8"))
    rows = payload.get("rows") or []
    if not rows:
        print("replay missing rows — re-run with --include-rows", file=sys.stderr)
        return 2
    train = [r for r in rows if 2020 <= int(r["season"]) <= 2024]
    hold = [r for r in rows if int(r["season"]) == 2025]
    # Mid/pick frozen: hist OLS wants mid>1 but live TCU (long raw) needs ≤1.
    # Long/cupcake frozen: long OLS>1 worsens live TCU (|raw|~19); cupcake n<30.
    freeze = ("pick", "mid", "long", "cupcake")
    fit = fit_scales(train, freeze=freeze, lo=0.90, hi=1.25, min_n=30)
    scales = fit["scales"]
    identity = {b: 1.0 for b in BUCKETS}
    out = {
        "map_id": MAP_ID,
        "engine_start": "cfb-season-engine-v0.15-power-sot",
        "train_seasons": [2020, 2021, 2022, 2023, 2024],
        "holdout_season": 2025,
        "freeze_buckets": list(freeze),
        "freeze_reason": (
            "mid/pick identity — hist proxy mid is short of close (OLS>1) while "
            "live W0 TCU is long (needs <1); one scale cannot fix both. "
            "long identity — OLS>1 would lengthen TCU (|raw|≈19). "
            "cupcake identity — raw-bucket n=9 < min_n."
        ),
        "scales": scales,
        "ols_uncapped": fit["ols_uncapped"],
        "n_by_raw_bucket_train": fit["n_by_raw_bucket"],
        "holdout_identity": mae_by_close_bucket(hold, identity),
        "holdout_fit": mae_by_close_bucket(hold, scales),
        "train_identity": mae_by_close_bucket(train, identity),
        "train_fit": mae_by_close_bucket(train, scales),
        "win_prob_margin_sd_untouched": 15.2,
        "used_in_spread_tanh": False,
        "fit": True,
    }
    mid0 = out["holdout_identity"]["mid"]["mae"]
    mid1 = out["holdout_fit"]["mid"]["mae"]
    cup0 = out["holdout_identity"]["cupcake"]["mae"]
    cup1 = out["holdout_fit"]["cupcake"]["mae"]
    out["holdout_mid_mae_delta"] = None if mid0 is None or mid1 is None else mid1 - mid0
    out["holdout_cupcake_mae_delta"] = (
        None if cup0 is None or cup1 is None else cup1 - cup0
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in (
        "map_id", "scales", "holdout_mid_mae_delta", "holdout_cupcake_mae_delta",
        "holdout_identity", "holdout_fit",
    )}, indent=2))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
