#!/usr/bin/env python3
"""B2-PACE-NEUTRAL-v1 — single authorized Train-A research diagnostic.

Preregistration: docs/lab/NCAAM_B2_PACE_NEUTRAL_v1_PREREGISTRATION.md

Hard locks:
  - Train-A parquet only (refuses Test-A / holdout / pocket / 2024-25 pack)
  - One atomic candidate evaluation; no post-result retune
  - Research evidence only; not promotion; not production default
  - Does not mutate frozen B2-PACE-v1
"""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import polars as pl

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "apps" / "web" / "src"))

from ncaam_lab.fair_b2 import compute_fair_b2  # noqa: E402
from ncaam_lab.fair_b2_pace_v1 import (  # noqa: E402
    ELIGIBLE_COL as PACE_ELIGIBLE,
    FAIR_COL as PACE_FAIR,
    FROZEN_HCA,
    compute_fair_b2_pace_v1,
)
from ncaam_lab.fair_b2_pace_neutral_v1 import (  # noqa: E402
    CANDIDATE_ID,
    ELIGIBLE_COL,
    FAIR_COL,
    HCA_COL,
    METHOD_ID,
    compute_fair_b2_pace_neutral_v1,
)
from ncaam_lab.neutral_site_identity import (  # noqa: E402
    VENUE_STATUS_HOME,
    VENUE_STATUS_NEUTRAL,
    VENUE_STATUS_UNKNOWN,
    assert_no_holdout_or_test_a_paths,
    attach_venue_status,
    default_train_a_schedule_packs,
)
from ncaam_lab.results_attach import attach_lab_outcomes  # noqa: E402

OUT_DIR = REPO / "data" / "ops" / "lab" / "ncaam"
TRAIN_PARQUET = OUT_DIR / "ncaam-fair-lab-train_a-latest.parquet"
BOOT_N = 2000
BOOT_SEED = 20260909
IMPL_PATH = "apps/web/src/ncaam_lab/fair_b2_pace_neutral_v1.py"
PARENT_IMPL = "apps/web/src/ncaam_lab/fair_b2_pace_v1.py"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_head() -> str:
    return (
        subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"])
        .decode()
        .strip()
    )


def mae(y, p):
    return float(np.mean(np.abs(y - p)))


def rmse(y, p):
    return float(np.sqrt(np.mean((y - p) ** 2)))


def bias(y, p):
    return float(np.mean(y - p))


def cal(y, p) -> Tuple[float, float]:
    if len(y) < 2 or float(np.std(p)) < 1e-12:
        return float("nan"), float("nan")
    x = np.column_stack([p, np.ones(len(y))])
    coef, _, _, _ = np.linalg.lstsq(x, y, rcond=None)
    return float(coef[0]), float(coef[1])


def boot_mae(y, p) -> Dict[str, Any]:
    rng = np.random.default_rng(BOOT_SEED)
    n = len(y)
    abs_e = np.abs(y - p)
    point = float(abs_e.mean()) if n else None
    if n == 0:
        return {
            "n": 0,
            "mae": None,
            "ci95": None,
            "n_bootstrap": BOOT_N,
            "seed": BOOT_SEED,
        }
    idx = rng.integers(0, n, size=(BOOT_N, n))
    samples = abs_e[idx].mean(axis=1)
    lo, hi = np.quantile(samples, [0.025, 0.975])
    return {
        "n": int(n),
        "mae": point,
        "ci95": [float(lo), float(hi)],
        "n_bootstrap": BOOT_N,
        "seed": BOOT_SEED,
        "grain": "game_row",
    }


def metrics(y, p) -> Dict[str, Any]:
    if len(y) == 0:
        return {"n": 0}
    slope, intercept = cal(y, p)
    return {
        "n": int(len(y)),
        "mae": mae(y, p),
        "rmse": rmse(y, p),
        "signed_bias": bias(y, p),
        "cal_slope": slope,
        "cal_intercept": intercept,
        "bootstrap_mae": boot_mae(y, p),
    }


def refuse_forbidden_artifacts() -> None:
    """Validate only the paths this script will open (Train-A + 22/23–23/24 packs)."""
    assert_no_holdout_or_test_a_paths([TRAIN_PARQUET])
    assert_no_holdout_or_test_a_paths(default_train_a_schedule_packs())
    # Document sibling artifacts that exist but must never be opened here.
    _not_opened = [
        "data/ops/lab/ncaam/ncaam-fair-lab-test_a-latest.parquet",
        "data/ops/lab/ncaam/holdout_2024_25/seal/seal_receipt.json",
    ]
    del _not_opened


def main() -> int:
    refuse_forbidden_artifacts()
    if not TRAIN_PARQUET.exists():
        print(f"ERROR: missing Train-A parquet {TRAIN_PARQUET}", file=sys.stderr)
        return 2

    df0 = pl.read_parquet(TRAIN_PARQUET)
    # Guard window labels if present
    if "cut_window" in df0.columns:
        bad = df0.filter(~pl.col("cut_window").cast(pl.Utf8).str.to_lowercase().str.contains("train"))
        # Some frames stamp cut_window as train_a; refuse any test_a rows if mixed.
        testish = df0.filter(
            pl.col("cut_window").cast(pl.Utf8).str.to_lowercase().str.contains("test")
        )
        if testish.height > 0:
            raise RuntimeError("Train-A parquet contains test window rows — refuse")

    with_outcomes, attach_receipt = attach_lab_outcomes(df0)
    with_venue, venue_receipt = attach_venue_status(with_outcomes)

    incumbent = compute_fair_b2(with_venue, hca=FROZEN_HCA)
    pace = compute_fair_b2_pace_v1(incumbent, hca=FROZEN_HCA)
    neut = compute_fair_b2_pace_neutral_v1(pace)

    # Eligible intersection: actual margin + parent pace eligible + neutral eligible
    need = ["actual_margin", PACE_FAIR, FAIR_COL, "b1_consensus_close_spread", "venue_status"]
    for c in need:
        if c not in neut.columns:
            raise RuntimeError(f"missing required column {c}")

    scored = neut.filter(
        pl.col("actual_margin").is_not_null()
        & pl.col(PACE_ELIGIBLE)
        & pl.col(ELIGIBLE_COL)
        & pl.col("b1_consensus_close_spread").is_finite()
        & pl.col(PACE_FAIR).is_finite()
        & pl.col(FAIR_COL).is_finite()
    )

    y = scored["actual_margin"].to_numpy()
    p_c0 = scored["fair_spread_home"].to_numpy()
    p_pace = scored[PACE_FAIR].to_numpy()
    p_neut = scored[FAIR_COL].to_numpy()
    # B1 close consensus: market home spread → home-margin prediction via negation
    # (same convention as lab_ncaam_b2_pace_v1_train_a_diagnostics.py).
    p_b1 = (-scored["b1_consensus_close_spread"]).to_numpy()

    # Descriptive venue splits (no result-dependent filtering)
    by_venue: Dict[str, Any] = {}
    for status in (VENUE_STATUS_HOME, VENUE_STATUS_NEUTRAL, VENUE_STATUS_UNKNOWN):
        sub = scored.filter(pl.col("venue_status") == status)
        if sub.height == 0:
            by_venue[status] = {"n": 0}
            continue
        yy = sub["actual_margin"].to_numpy()
        by_venue[status] = {
            "n": int(sub.height),
            "C0_incumbent_b2": metrics(yy, sub["fair_spread_home"].to_numpy()),
            "B2_PACE_v1": metrics(yy, sub[PACE_FAIR].to_numpy()),
            "B2_PACE_NEUTRAL_v1": metrics(yy, sub[FAIR_COL].to_numpy()),
            "B1_close_consensus": metrics(
                yy, (-sub["b1_consensus_close_spread"]).to_numpy()
            ),
        }

    # Paired deltas (game grain) — research evidence only
    d_neut_vs_pace = p_neut - p_pace
    d_mae_vs_pace = np.abs(y - p_neut) - np.abs(y - p_pace)
    d_mae_vs_b1 = np.abs(y - p_neut) - np.abs(y - p_b1)
    d_mae_vs_c0 = np.abs(y - p_neut) - np.abs(y - p_c0)

    def boot_delta(deltas: np.ndarray) -> Dict[str, Any]:
        rng = np.random.default_rng(BOOT_SEED)
        n = len(deltas)
        if n == 0:
            return {"n": 0, "mean": None, "ci95": None}
        idx = rng.integers(0, n, size=(BOOT_N, n))
        samples = deltas[idx].mean(axis=1)
        lo, hi = np.quantile(samples, [0.025, 0.975])
        return {
            "n": int(n),
            "mean": float(deltas.mean()),
            "ci95": [float(lo), float(hi)],
            "n_bootstrap": BOOT_N,
            "seed": BOOT_SEED,
        }

    head = git_head()
    receipt = {
        "schema_version": "ncaam-b2-pace-neutral-v1-train-a-v1",
        "candidate_id": CANDIDATE_ID,
        "method_id": METHOD_ID,
        "status": "research_evidence_only_not_promoted",
        "population": "Train-A only",
        "train_parquet": str(TRAIN_PARQUET.relative_to(REPO)),
        "train_parquet_sha256": sha256_file(TRAIN_PARQUET),
        "impl_path": IMPL_PATH,
        "impl_sha256": sha256_file(REPO / IMPL_PATH),
        "parent_impl_path": PARENT_IMPL,
        "parent_impl_sha256": sha256_file(REPO / PARENT_IMPL),
        "generating_commit": head,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "bootstrap": {"n": BOOT_N, "seed": BOOT_SEED},
        "attach_outcomes_receipt": attach_receipt,
        "venue_identity_receipt": venue_receipt,
        "n_train_rows": int(df0.height),
        "n_scored_eligible": int(scored.height),
        "n_unknown_venue_in_scored": int(
            scored.filter(pl.col("venue_status") == VENUE_STATUS_UNKNOWN).height
        ),
        "overall": {
            "C0_incumbent_b2": metrics(y, p_c0),
            "B2_PACE_v1": metrics(y, p_pace),
            "B2_PACE_NEUTRAL_v1": metrics(y, p_neut),
            "B1_close_consensus": metrics(y, p_b1),
        },
        "paired_delta_mae": {
            "definition_neut_minus_pace": "MAE(NEUTRAL)-MAE(PACE) via mean(|e_n|-|e_p|)",
            "neut_vs_pace": boot_delta(d_mae_vs_pace),
            "neut_vs_b1": boot_delta(d_mae_vs_b1),
            "neut_vs_c0": boot_delta(d_mae_vs_c0),
            "mean_fair_diff_neut_minus_pace": float(np.mean(d_neut_vs_pace))
            if len(d_neut_vs_pace)
            else None,
        },
        "by_venue_status": by_venue,
        "acceptance_gates_preregistered": {
            "note": "Train-A is development evidence only; pocket/holdout gates NOT evaluated",
            "train_a_gates_evaluated": False,
            "holdout_scored": False,
            "test_a_scored": False,
            "pocket_scored": False,
            "promoted": False,
            "production_default": False,
        },
        "hard_stops_honored": {
            "no_holdout_unseal": True,
            "no_test_a_scoring": True,
            "no_parent_candidate_mutation": True,
            "no_promotion": True,
            "no_play_lean_claims": True,
            "single_run_no_retune": True,
        },
    }

    out_json = OUT_DIR / "ncaam-b2-pace-neutral-v1-train-a-diagnostics.json"
    out_md = OUT_DIR / "ncaam-b2-pace-neutral-v1-train-a-diagnostics.md"
    out_json.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    o = receipt["overall"]
    md = [
        "# B2-PACE-NEUTRAL-v1 Train-A diagnostics (research only)",
        "",
        f"- Candidate: `{CANDIDATE_ID}` / `{METHOD_ID}`",
        f"- Generating commit: `{head}`",
        f"- Scored eligible n: **{scored.height}**",
        f"- Status: **research evidence only — not promoted**",
        "",
        "## Overall MAE",
        "",
        f"| Model | MAE | bias | cal slope |",
        f"| --- | ---: | ---: | ---: |",
        f"| C0 | {o['C0_incumbent_b2']['mae']:.3f} | {o['C0_incumbent_b2']['signed_bias']:.3f} | {o['C0_incumbent_b2']['cal_slope']:.3f} |",
        f"| B2-PACE-v1 | {o['B2_PACE_v1']['mae']:.3f} | {o['B2_PACE_v1']['signed_bias']:.3f} | {o['B2_PACE_v1']['cal_slope']:.3f} |",
        f"| B2-PACE-NEUTRAL-v1 | {o['B2_PACE_NEUTRAL_v1']['mae']:.3f} | {o['B2_PACE_NEUTRAL_v1']['signed_bias']:.3f} | {o['B2_PACE_NEUTRAL_v1']['cal_slope']:.3f} |",
        f"| B1 | {o['B1_close_consensus']['mae']:.3f} | {o['B1_close_consensus']['signed_bias']:.3f} | {o['B1_close_consensus']['cal_slope']:.3f} |",
        "",
        "## Paired ΔMAE (NEUTRAL − comparator)",
        "",
        f"- vs PACE: {receipt['paired_delta_mae']['neut_vs_pace']}",
        f"- vs B1: {receipt['paired_delta_mae']['neut_vs_b1']}",
        f"- vs C0: {receipt['paired_delta_mae']['neut_vs_c0']}",
        "",
        "## Hard stops",
        "",
        "- Holdout / Test-A / pocket: **not scored**",
        "- Parent B2-PACE-v1: **unchanged**",
        "- No promotion / PLAY / LEAN",
        "",
    ]
    out_md.write_text("\n".join(md), encoding="utf-8")
    print(json.dumps({"wrote": str(out_json), "n_scored": scored.height}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
