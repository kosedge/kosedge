#!/usr/bin/env python3
"""t5053u evaluator — ΔMAE + bootstrap + week-blocks. PRE-LOOK only.

evaluate() runs on in-memory arrays (synthetic fixtures in tests).
look_real() always refuses until a NEW Alex receipt binds the final
evaluator freeze. It does not open 50bda875 / 1ee90fac in this ticket.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Sequence

import numpy as np

EVAL = Path(__file__).resolve().parent
PACKET = EVAL.parent
if str(EVAL) not in sys.path:
    sys.path.insert(0, str(EVAL))

from bootstrap import (  # noqa: E402
    BOOT_B,
    BOOT_SEED,
    WEEK_BLOCKS,
    paired_delta_mae,
    paired_game_bootstrap_ci,
    week_block_sensitivity,
)
from verify_final_prelook import (  # noqa: E402
    ALEX_RECEIPT_PATH,
    FINAL_FREEZE_PATH,
    LookGateRefuse,
    verify_complete_set,
)

PARENT_FREEZE_SHA = (
    "90774bd40c03c1b1de6f16967f29ba3ff2017b25d93620c6d5e351f56460df98"
)
LOOK_CONSUMED = PACKET / "phase4" / "artifacts" / "LOOK_CONSUMED.json"
REAL_N = 141
RETRO = "RETRO_FIT / DEV_RESEARCH"


class EvalRefuse(RuntimeError):
    pass


def evaluate(
    candidate: Sequence[float],
    baseline: Sequence[float],
    actual: Sequence[float],
    weeks: Sequence[int],
    *,
    expected_n: int,
    B: int = BOOT_B,
    seed: int = BOOT_SEED,
) -> dict[str, Any]:
    """Pure in-memory evaluate. No file I/O. No outcomes pin."""
    if int(B) != BOOT_B:
        raise EvalRefuse(f"B {B} != frozen {BOOT_B}")
    if int(seed) != BOOT_SEED:
        raise EvalRefuse(f"seed {seed} != frozen {BOOT_SEED}")
    cand = np.asarray(candidate, dtype=float)
    base = np.asarray(baseline, dtype=float)
    act = np.asarray(actual, dtype=float)
    week_a = np.asarray(weeks, dtype=int)
    if cand.size != expected_n:
        raise EvalRefuse(f"missing/extra rows n={cand.size} != expected {expected_n}")
    if cand.shape != base.shape or cand.shape != act.shape or cand.shape != week_a.shape:
        raise EvalRefuse("paired arrays must share shape")
    if not np.isfinite(cand).all() or not np.isfinite(base).all() or not np.isfinite(act).all():
        raise EvalRefuse("non-finite prediction or actual")
    deltas = paired_delta_mae(cand, base, act)
    boot = paired_game_bootstrap_ci(deltas, B=B, seed=seed)
    try:
        blocks = week_block_sensitivity(
            deltas, week_a, cand, base, act, B=B, seed=seed
        )
    except ValueError as exc:
        raise EvalRefuse(f"week-block miswire: {exc}") from exc
    if set(blocks) != {str(w) for w in WEEK_BLOCKS}:
        raise EvalRefuse("week-block miswire: keys != W7–W17")
    mae_c = float(np.mean(np.abs(cand - act)))
    mae_b = float(np.mean(np.abs(base - act)))
    rmse_c = float(np.sqrt(np.mean((cand - act) ** 2)))
    rmse_b = float(np.sqrt(np.mean((base - act) ** 2)))
    ci_crosses = boot["ci_lo"] <= 0.0 <= boot["ci_hi"]
    if ci_crosses:
        verdict = "INCONCLUSIVE — CI crosses zero; NOT FQ PASS"
    elif boot["mean"] < 0:
        verdict = "POINT_IMPROVEMENT — negative ΔMAE; not FQ PASS; CERT=0"
    else:
        verdict = "POINT_WORSE — positive ΔMAE; not FQ FAIL-as-cert; CERT=0"
    week_signs = {w: blocks[w]["delta_mae"] for w in blocks}
    disagree = False
    if not ci_crosses:
        primary_neg = boot["mean"] < 0
        if any((v < 0) != primary_neg for v in week_signs.values() if v != 0.0):
            disagree = True
    if disagree:
        verdict = "INCONCLUSIVE — primary and week-blocks disagree; no favorable claim"
    return {
        "label": RETRO,
        "cert": 0,
        "n": int(expected_n),
        "weight": 0.5,
        "B": BOOT_B,
        "seed": BOOT_SEED,
        "primary": {
            "delta_mae": boot["mean"],
            "mae_baseline": mae_b,
            "mae_candidate": mae_c,
            "n": int(expected_n),
            "bootstrap": boot,
            "ci_crosses_zero": ci_crosses,
            "sign_note": (
                "Negative Δ = point improvement; CI crossing zero = "
                "inconclusive, NOT FQ PASS"
            ),
        },
        "descriptive": {
            "rmse_baseline": rmse_b,
            "rmse_candidate": rmse_c,
            "week_blocks": blocks,
            "n_week_blocks": 11,
        },
        "verdict": verdict,
        "look_run": False,
        "realized_source": None,
    }


def look_real() -> None:
    """Real 2017 outcomes path — REFUSED on this ticket.

    Requires (all): final freeze complete-set verify, parent 90774bd4
    history intact, independent Alex receipt bound to the *final*
    evaluator freeze, LOOK_CONSUMED absent, and a later CoS
    re-authorization. None of that is present for t5053u.
    """
    if LOOK_CONSUMED.exists():
        raise EvalRefuse("LOOK_CONSUMED already present — no second look")
    try:
        verify_complete_set()
    except LookGateRefuse as exc:
        raise EvalRefuse(f"final freeze gate: {exc}") from exc
    if not ALEX_RECEIPT_PATH.exists():
        raise EvalRefuse(
            "independent Alex receipt absent — real look refused "
            "(8b80ad7b does not bind the final evaluator freeze)"
        )
    receipt = json.loads(ALEX_RECEIPT_PATH.read_text())
    final_sha = _sha256(FINAL_FREEZE_PATH)
    if str(receipt.get("binds_final_freeze_sha256") or "") != final_sha:
        raise EvalRefuse("Alex receipt does not bind the live final freeze sha")
    if receipt.get("authorizes_look") is not True:
        raise EvalRefuse("Alex receipt does not authorize a look")
    # Even if a receipt file were planted, t5053u does not join outcomes.
    raise EvalRefuse(
        "t5053u HARD STOP: evaluator is bound but must not join real "
        "2017 outcomes until CoS re-authorizes after Alex PASS on the "
        f"final freeze (parent history {PARENT_FREEZE_SHA[:8]})"
    )


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    try:
        look_real()
    except EvalRefuse as exc:
        print(f"LOOK_REFUSE: {exc}")
        return 2
    raise EvalRefuse("unreachable — real look must refuse")


if __name__ == "__main__":
    raise SystemExit(main())
