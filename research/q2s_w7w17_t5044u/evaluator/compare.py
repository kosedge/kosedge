#!/usr/bin/env python3
"""t5055u evaluator — ΔMAE + game bootstrap + week-cluster bootstrap.

evaluate() is in-memory (synthetic fixtures in tests).
look_real() is a complete callable path: gates → score-only identity
join → n=141 unique finite pairs → evaluate → LOOK_CONSUMED.
It remains REFUSED without matching independent Alex + CoS receipts.
Production main() does not join 50bda875 unless those receipts exist.
"""

from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass
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
    paired_week_cluster_bootstrap_ci,
    week_block_sensitivity,
)
from verify_final_prelook import (  # noqa: E402
    ALEX_RECEIPT_PATH,
    COS_EXECUTE_PATH,
    T5055U_FREEZE_PATH,
    LookGateRefuse,
    sha256_file,
    verify_complete_set,
)

PARENT_FREEZE_SHA = (
    "90774bd40c03c1b1de6f16967f29ba3ff2017b25d93620c6d5e351f56460df98"
)
Q2S_ROWS_PATH = PACKET / "phase4" / "artifacts" / "q2s_rows_w7w17.json"
Q2S_SHA = "55d8c8bc2155705c04e9ef88ba5637ea491bf5c245e4f7bb8fcfb3523f9ec925"
OUTCOMES_PIN_PATH = PACKET / "pins" / "outcomes_2013_2022_score_only.csv"
OUTCOMES_PIN_SHA = (
    "50bda875daa8bf1aadd56dd0a3bc19f1bb52dafe42b6a9c921a5816c7d7dc081"
)
LOOK_CONSUMED = PACKET / "phase4" / "artifacts" / "LOOK_CONSUMED.json"
REAL_N = 141
RETRO = "RETRO_FIT / DEV_RESEARCH"

# Audit of which outcomes files the join opened. Tests assert production
# look_real() without receipts never appends the 50bda875 pin.
OUTCOMES_JOINS: list[str] = []


class EvalRefuse(RuntimeError):
    pass


@dataclass
class LookContext:
    """Callable look path. Production defaults. Tests inject temp files."""

    q2s_path: Path = Q2S_ROWS_PATH
    outcomes_path: Path = OUTCOMES_PIN_PATH
    expected_outcomes_sha: str = OUTCOMES_PIN_SHA
    expected_q2s_sha: str | None = Q2S_SHA
    expected_n: int = REAL_N
    alex_path: Path = ALEX_RECEIPT_PATH
    cos_path: Path = COS_EXECUTE_PATH
    consumed_path: Path = LOOK_CONSUMED
    final_freeze_path: Path = T5055U_FREEZE_PATH
    write_consumed: bool = True


def verdict_from_uncertainty(
    game_boot: dict[str, float],
    week_boot: dict[str, float],
) -> tuple[str, dict[str, Any]]:
    """Dual pooled-CI stopping. Per-week signs are not a stopping rule."""
    g_cross = float(game_boot["ci_lo"]) <= 0.0 <= float(game_boot["ci_hi"])
    w_cross = float(week_boot["ci_lo"]) <= 0.0 <= float(week_boot["ci_hi"])
    g_neg = float(game_boot["ci_hi"]) < 0.0
    w_neg = float(week_boot["ci_hi"]) < 0.0
    g_pos = float(game_boot["ci_lo"]) > 0.0
    w_pos = float(week_boot["ci_lo"]) > 0.0
    disagree = (g_neg and w_pos) or (g_pos and w_neg)
    if g_cross or w_cross:
        verdict = (
            "INCONCLUSIVE — a pooled CI includes zero; NOT FQ PASS"
        )
    elif disagree:
        verdict = (
            "INCONCLUSIVE — game-bootstrap and week-cluster CIs disagree "
            "in direction; no favorable claim"
        )
    elif float(game_boot["mean"]) < 0.0:
        verdict = (
            "POINT_IMPROVEMENT — negative ΔMAE; both pooled CIs exclude 0 "
            "and agree; not FQ PASS; CERT=0"
        )
    else:
        verdict = (
            "POINT_WORSE — positive ΔMAE; both pooled CIs exclude 0 "
            "and agree; not FQ FAIL-as-cert; CERT=0"
        )
    meta = {
        "game_ci_includes_zero": g_cross,
        "week_cluster_ci_includes_zero": w_cross,
        "direction_disagree": disagree,
        "per_week_sign_not_required": True,
    }
    return verdict, meta


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
    game_boot = paired_game_bootstrap_ci(deltas, B=B, seed=seed)
    try:
        week_boot = paired_week_cluster_bootstrap_ci(
            deltas, week_a, B=B, seed=seed
        )
        blocks = week_block_sensitivity(
            deltas, week_a, cand, base, act, B=B, seed=seed
        )
    except ValueError as exc:
        raise EvalRefuse(f"week-cluster miswire: {exc}") from exc
    if set(blocks) != {str(w) for w in WEEK_BLOCKS}:
        raise EvalRefuse("week-block miswire: keys != W7–W17")
    mae_c = float(np.mean(np.abs(cand - act)))
    mae_b = float(np.mean(np.abs(base - act)))
    rmse_c = float(np.sqrt(np.mean((cand - act) ** 2)))
    rmse_b = float(np.sqrt(np.mean((base - act) ** 2)))
    verdict, umeta = verdict_from_uncertainty(game_boot, week_boot)
    return {
        "label": RETRO,
        "cert": 0,
        "n": int(expected_n),
        "weight": 0.5,
        "B": BOOT_B,
        "seed": BOOT_SEED,
        "primary": {
            "delta_mae": game_boot["mean"],
            "mae_baseline": mae_b,
            "mae_candidate": mae_c,
            "n": int(expected_n),
            "bootstrap": game_boot,
            "week_cluster_bootstrap": week_boot,
            "ci_crosses_zero": umeta["game_ci_includes_zero"],
            "sign_note": (
                "Negative Δ = point improvement; either pooled CI "
                "including zero, or the two CIs disagreeing in direction, "
                "= inconclusive, NOT FQ PASS. Per-week signs are descriptive."
            ),
        },
        "uncertainty": {
            "game_bootstrap": game_boot,
            "week_cluster_bootstrap": week_boot,
            **umeta,
        },
        "descriptive": {
            "rmse_baseline": rmse_b,
            "rmse_candidate": rmse_c,
            "week_blocks": blocks,
            "n_week_blocks": 11,
            "week_blocks_role": "descriptive_only",
        },
        "verdict": verdict,
        "look_run": False,
        "realized_source": None,
    }


def _identity(row: dict[str, Any]) -> tuple[int, int, str, str]:
    return (
        int(row["season"]),
        int(row["week"]),
        str(row["home"]),
        str(row["away"]),
    )


def load_score_only_outcomes(path: Path) -> dict[tuple[int, int, str, str], tuple[float, float]]:
    """Pinned score-only identity map. Tests pass temp CSVs, never 2017 pin."""
    OUTCOMES_JOINS.append(str(path.resolve()))
    out: dict[tuple[int, int, str, str], tuple[float, float]] = {}
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"season", "week", "home", "away", "home_score", "away_score"}
        if reader.fieldnames is None or not required <= set(reader.fieldnames):
            raise EvalRefuse("outcomes CSV missing score-only identity columns")
        for rec in reader:
            key = (
                int(rec["season"]),
                int(rec["week"]),
                str(rec["home"]),
                str(rec["away"]),
            )
            hs = float(rec["home_score"])
            aws = float(rec["away_score"])
            if key in out:
                raise EvalRefuse(f"duplicate outcome identity {key}")
            out[key] = (hs, aws)
    return out


def join_score_only_identity(
    pred_rows: Sequence[dict[str, Any]],
    outcomes: dict[tuple[int, int, str, str], tuple[float, float]],
    *,
    expected_n: int,
) -> dict[str, list]:
    """Exact (season, week, home, away) join. No subset. Unique finite pairs."""
    if len(pred_rows) != int(expected_n):
        raise EvalRefuse(
            f"prediction subset/extra n={len(pred_rows)} != expected {expected_n}"
        )
    seen: set[tuple[int, int, str, str]] = set()
    candidate: list[float] = []
    baseline: list[float] = []
    actual: list[float] = []
    weeks: list[int] = []
    for row in pred_rows:
        key = _identity(row)
        if key in seen:
            raise EvalRefuse(f"duplicate prediction identity {key}")
        seen.add(key)
        if key not in outcomes:
            raise EvalRefuse(f"identity miss {key} — refuse subset")
        hs, aws = outcomes[key]
        act = float(hs) - float(aws)
        try:
            cand = float(row["research"]["q2s"]["margin_mu_q2s"])
            base = float(row["baseline"]["if_margin_mu"])
        except (KeyError, TypeError, ValueError) as exc:
            raise EvalRefuse(f"prediction fields missing for {key}") from exc
        if not np.isfinite(cand) or not np.isfinite(base) or not np.isfinite(act):
            raise EvalRefuse(f"non-finite pair {key}")
        candidate.append(cand)
        baseline.append(base)
        actual.append(act)
        weeks.append(int(key[1]))
    if len(candidate) != int(expected_n):
        raise EvalRefuse("silent subset after join")
    if len(seen) != int(expected_n):
        raise EvalRefuse("paired identities not unique")
    return {
        "candidate": candidate,
        "baseline": baseline,
        "actual": actual,
        "weeks": weeks,
    }


def _require_receipt(path: Path, *, bind_sha: str, flag: str, label: str) -> dict[str, Any]:
    if not path.exists():
        raise EvalRefuse(f"{label} receipt absent — real look refused")
    receipt = json.loads(path.read_text())
    if str(receipt.get("binds_final_freeze_sha256") or "") != bind_sha:
        raise EvalRefuse(f"{label} receipt does not bind the live final freeze sha")
    if receipt.get(flag) is not True:
        raise EvalRefuse(f"{label} receipt does not authorize ({flag})")
    return receipt


def require_look_gates(ctx: LookContext) -> dict[str, Any]:
    """All look gates. Must refuse before any outcomes join."""
    if ctx.consumed_path.exists():
        raise EvalRefuse("LOOK_CONSUMED already present — no second look")
    try:
        final = verify_complete_set()
    except LookGateRefuse as exc:
        raise EvalRefuse(f"final freeze gate: {exc}") from exc
    if not ctx.final_freeze_path.exists():
        raise EvalRefuse("t5055u final freeze missing")
    live = sha256_file(ctx.final_freeze_path)
    _require_receipt(
        ctx.alex_path,
        bind_sha=live,
        flag="authorizes_look",
        label="Alex",
    )
    _require_receipt(
        ctx.cos_path,
        bind_sha=live,
        flag="authorizes_execute",
        label="CoS execute",
    )
    return final


def execute_authorized_look(ctx: LookContext) -> dict[str, Any]:
    """Join + evaluate + consume. Call only after require_look_gates."""
    if not ctx.q2s_path.exists():
        raise EvalRefuse("q2s rows missing")
    if not ctx.outcomes_path.exists():
        raise EvalRefuse("outcomes file missing")
    q2s_sha = sha256_file(ctx.q2s_path)
    if ctx.expected_q2s_sha is not None and q2s_sha != ctx.expected_q2s_sha:
        raise EvalRefuse("q2s rows sha != expected")
    out_sha = sha256_file(ctx.outcomes_path)
    if out_sha != ctx.expected_outcomes_sha:
        raise EvalRefuse("outcomes sha != expected pin / fixture")
    payload = json.loads(ctx.q2s_path.read_text())
    rows = payload.get("rows") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise EvalRefuse("q2s rows payload invalid")
    outcomes = load_score_only_outcomes(ctx.outcomes_path)
    paired = join_score_only_identity(rows, outcomes, expected_n=ctx.expected_n)
    result = evaluate(
        paired["candidate"],
        paired["baseline"],
        paired["actual"],
        paired["weeks"],
        expected_n=ctx.expected_n,
    )
    result["look_run"] = True
    result["realized_source"] = {
        "path": str(ctx.outcomes_path),
        "sha256": out_sha,
        "join": "season,week,home,away",
        "n_paired": ctx.expected_n,
    }
    if ctx.write_consumed:
        consumed = {
            "ticket": "t5055u",
            "look_consumed": True,
            "n": ctx.expected_n,
            "q2s_sha256": q2s_sha,
            "outcomes_sha256": out_sha,
            "final_freeze_sha256": sha256_file(ctx.final_freeze_path),
            "parent_freeze_sha256": PARENT_FREEZE_SHA,
            "cert": 0,
        }
        ctx.consumed_path.parent.mkdir(parents=True, exist_ok=True)
        ctx.consumed_path.write_text(json.dumps(consumed, indent=2, sort_keys=True) + "\n")
    return result


def look_real(ctx: LookContext | None = None) -> dict[str, Any]:
    """Complete callable look. REFUSED without matching receipts.

    Production defaults join the pinned score-only file only after
    verify_complete_set + independent Alex receipt + CoS execute
    receipt + LOOK_CONSUMED absent. Tests inject LookContext with
    synthetic fixtures; they must not pass the 2017 pin.
    """
    ctx = ctx or LookContext()
    require_look_gates(ctx)
    return execute_authorized_look(ctx)


def main() -> int:
    try:
        result = look_real()
    except EvalRefuse as exc:
        print(f"LOOK_REFUSE: {exc}")
        return 2
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
