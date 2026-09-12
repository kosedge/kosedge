"""Authorized MATCHUP_RESPONSE coefficient-fit on the #543 v1 universe.

Research only. Isolates MATCHUP_RESPONSE. Does not change production priors,
QB contract, close semantics, gates, PPG, class multipliers, or Layer B.
Does not unseal 2025. Does not use 2026 in the loss. Does not publish PLAY.

Primary ranking uses actuals. Close is a diagnostic. ATS/ROI cannot override
a failed MAE/bias gate.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from src.services.cfb_season_engine import priors as P
from src.services.cfb_season_engine.qb_feature_contract import QB_FEATURE_CONTRACT_VERSION
from src.services.cfb_warehouse.frozen_140_scoring import (
    HIGH_TOTAL_TAIL,
    LEGAL_SEASONS,
    TRAIN0_GATE,
    VAL1_GATE,
    FrozenScoringError,
    assert_frozen_priors,
    load_v1_scoring_context,
    refuse_sealed_or_confirm,
    score_joined_rows,
    summarize_scored,
)

PRODUCTION_MATCHUP_RESPONSE = 1.40
AUTHORITATIVE_PR = 543

# Pre-registered coarse grid. 1.18 is listed because it was previously guessed;
# it has no privilege over any other node.
COARSE_GRID: Tuple[float, ...] = (
    0.70,
    0.75,
    0.80,
    0.85,
    0.90,
    0.95,
    1.00,
    1.05,
    1.10,
    1.15,
    1.18,
    1.20,
    1.25,
    1.30,
    1.35,
    1.40,
    1.45,
    1.50,
)
REFINE_HALF_WIDTH = 0.04
REFINE_STEP = 0.01

# Materiality vs frozen 1.40 on Val-1 (pre-registered).
MAE_IMPROVE_ABS = 1.0
MAE_IMPROVE_REL = 0.08
BIAS_SHRINK_REL = 0.50
BIAS_ABS_OK = 4.0
TAIL_IMPROVE_REL = 0.40
TAIL_BIAS_OK = 8.0
SPREAD_MAE_WORSEN_MAX = 0.75
SPREAD_COLLAPSE_FRAC = 0.50
STABILITY_TOL = 0.05
DISAGREE_MAX = 0.15
CLOSE_IMITATION_RATIO = 2.0
LOW_RESPONSE_FLOOR = 0.75


class FitError(FrozenScoringError):
    pass


@contextmanager
def temporary_matchup_response(value: float):
    """Swap only MATCHUP_RESPONSE; restore 1.40 even on failure."""
    prior = float(P.MATCHUP_RESPONSE)
    if prior != PRODUCTION_MATCHUP_RESPONSE:
        raise FitError(f"production MATCHUP_RESPONSE drifted before fit: {prior}")
    P.MATCHUP_RESPONSE = float(value)
    try:
        yield float(value)
    finally:
        P.MATCHUP_RESPONSE = PRODUCTION_MATCHUP_RESPONSE
        if float(P.MATCHUP_RESPONSE) != PRODUCTION_MATCHUP_RESPONSE:
            raise FitError("failed to restore MATCHUP_RESPONSE=1.40")


def _f(block: Mapping[str, Any], key: str) -> Optional[float]:
    val = block.get(key)
    return None if val is None else float(val)


def primary_loss(split: Mapping[str, Any]) -> Optional[float]:
    """Train-1 ranking loss. Actuals only. Lower is better."""
    mae = _f(split, "total_vs_actual_mae")
    bias = _f(split, "total_vs_actual_bias")
    if mae is None or bias is None:
        return None
    frozen_tail = (split.get("slices") or {}).get("frozen140_high_tail") or {}
    tail_bias = _f(frozen_tail, "total_vs_actual_bias")
    tail_term = abs(tail_bias) if tail_bias is not None else abs(bias)
    return mae + 0.25 * abs(bias) + 0.50 * tail_term


def overlay_frozen_tail(
    rows: Sequence[Mapping[str, Any]],
    frozen_tail_ids: Sequence[str],
) -> Dict[str, Any]:
    ids = set(frozen_tail_ids)
    subset = [r for r in rows if str(r.get("game_id")) in ids]
    return summarize_scored(subset)["overall"] if subset else {"n": 0}


def _game_id(row: Mapping[str, Any]) -> str:
    return str(row.get("game_id") or f"{row.get('season')}-{row.get('home')}-{row.get('away')}-{row.get('week')}")


def score_candidate(
    joined: Sequence[Mapping[str, Any]],
    universes: Mapping[int, Any],
    candidate: float,
    *,
    lake_only: bool,
    frozen_tail_ids: Sequence[str],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], Dict[str, Any]]:
    with temporary_matchup_response(candidate):
        scored, skipped = score_joined_rows(joined, universes, lake_only=lake_only)
    summary = summarize_scored(scored)
    frozen_tail = overlay_frozen_tail(scored, frozen_tail_ids)
    for name, block in (summary.get("splits") or {}).items():
        split_rows = [
            r
            for r in scored
            if int(r["season"]) in {2022, 2023, 2024}
            and (
                (name == "train_0" and int(r["season"]) == 2022)
                or (name == "val_0" and int(r["season"]) == 2023)
                or (name == "train_1" and int(r["season"]) in (2022, 2023))
                or (name == "val_1" and int(r["season"]) == 2024)
            )
        ]
        block["slices"] = dict(block.get("slices") or {})
        block["slices"]["frozen140_high_tail"] = overlay_frozen_tail(
            split_rows, frozen_tail_ids
        )
        block["primary_loss"] = primary_loss(block)
    summary["frozen140_high_tail_overall"] = frozen_tail
    return summary, scored, skipped


def _top_keys(items: Mapping[float, float], k: int = 3) -> List[float]:
    ranked = sorted(items.items(), key=lambda kv: kv[1])
    return [c for c, _ in ranked[:k]]


def refine_grid(center: float) -> List[float]:
    lo = round(center - REFINE_HALF_WIDTH, 2)
    hi = round(center + REFINE_HALF_WIDTH, 2)
    out: List[float] = []
    x = lo
    while x <= hi + 1e-9:
        val = round(x, 2)
        if val not in COARSE_GRID:
            out.append(val)
        x += REFINE_STEP
    return out


def _improve_mae(base: Optional[float], cand: Optional[float]) -> bool:
    if base is None or cand is None:
        return False
    return (base - cand) >= MAE_IMPROVE_ABS or (cand <= base * (1.0 - MAE_IMPROVE_REL))


def _bias_fixed(base: Optional[float], cand: Optional[float]) -> bool:
    if base is None or cand is None:
        return False
    if abs(cand) <= BIAS_ABS_OK:
        return True
    return abs(cand) <= abs(base) * (1.0 - BIAS_SHRINK_REL)


def _tail_fixed(base: Optional[float], cand: Optional[float]) -> bool:
    if cand is None:
        return False
    if abs(cand) < TAIL_BIAS_OK:
        return True
    if base is None:
        return False
    return abs(cand) <= abs(base) * (1.0 - TAIL_IMPROVE_REL)


def decide_fit(
    *,
    baseline: Mapping[str, Any],
    candidates: Mapping[float, Mapping[str, Any]],
    selected: float,
) -> Dict[str, Any]:
    """Pre-registered decision. Val-1 is the decision split. Actuals primary."""
    reasons: List[str] = []
    flags: List[str] = []
    base_val = (baseline.get("splits") or {}).get("val_1") or {}
    sel = (candidates.get(selected) or {}).get("splits") or {}
    sel_val = sel.get("val_1") or {}
    sel_train1 = sel.get("train_1") or {}
    sel_val0 = sel.get("val_0") or {}
    train0_n = int(((baseline.get("splits") or {}).get("train_0") or {}).get("n") or 0)
    val1_n = int(base_val.get("n") or 0)
    if train0_n < TRAIN0_GATE or val1_n < VAL1_GATE:
        return {
            "decision": "INSUFFICIENT EVIDENCE",
            "selected": selected,
            "why": [
                f"Train-0 n={train0_n} (need {TRAIN0_GATE})",
                f"Val-1 n={val1_n} (need {VAL1_GATE})",
            ],
        }

    base_mae = _f(base_val, "total_vs_actual_mae")
    sel_mae = _f(sel_val, "total_vs_actual_mae")
    base_bias = _f(base_val, "total_vs_actual_bias")
    sel_bias = _f(sel_val, "total_vs_actual_bias")
    base_close_mae = _f(base_val, "total_vs_close_mae")
    sel_close_mae = _f(sel_val, "total_vs_close_mae")
    base_spread = _f(base_val, "margin_vs_actual_mae")
    sel_spread = _f(sel_val, "margin_vs_actual_mae")
    base_abs_spread = _f(base_val, "mean_abs_model_spread")
    sel_abs_spread = _f(sel_val, "mean_abs_model_spread")
    close_abs_spread = _f(sel_val, "mean_abs_close_spread")
    base_tail = _f(
        (base_val.get("slices") or {}).get("frozen140_high_tail")
        or (base_val.get("slices") or {}).get("high_total_tail_ge_68")
        or {},
        "total_vs_actual_bias",
    )
    sel_tail = _f(
        (sel_val.get("slices") or {}).get("frozen140_high_tail") or {},
        "total_vs_actual_bias",
    )

    mae_ok = _improve_mae(base_mae, sel_mae)
    bias_ok = _bias_fixed(base_bias, sel_bias)
    tail_ok = _tail_fixed(base_tail, sel_tail)
    spread_ok = True
    if base_spread is not None and sel_spread is not None:
        spread_ok = (sel_spread - base_spread) <= SPREAD_MAE_WORSEN_MAX
    collapse = False
    if sel_abs_spread is not None and close_abs_spread is not None and close_abs_spread > 0:
        collapse = sel_abs_spread < SPREAD_COLLAPSE_FRAC * close_abs_spread

    losses: Dict[str, Dict[float, float]] = {"train_1": {}, "val_0": {}, "val_1": {}}
    for cand, summary in candidates.items():
        for split_name in losses:
            loss = ((summary.get("splits") or {}).get(split_name) or {}).get("primary_loss")
            if loss is not None:
                losses[split_name][float(cand)] = float(loss)
    top_train = _top_keys(losses["train_1"]) if losses["train_1"] else []
    top_val0 = _top_keys(losses["val_0"]) if losses["val_0"] else []
    top_val1 = _top_keys(losses["val_1"]) if losses["val_1"] else []
    stable = any(abs(selected - t) <= STABILITY_TOL for t in top_train) and any(
        abs(selected - t) <= STABILITY_TOL for t in top_val1
    )
    train1_best = top_train[0] if top_train else None
    val1_best = top_val1[0] if top_val1 else None
    disagree = (
        train1_best is not None
        and val1_best is not None
        and abs(train1_best - val1_best) > DISAGREE_MAX
    )

    close_imitation = False
    if (
        base_mae is not None
        and sel_mae is not None
        and base_close_mae is not None
        and sel_close_mae is not None
        and (base_mae - sel_mae) > 0
    ):
        close_gain = base_close_mae - sel_close_mae
        actual_gain = base_mae - sel_mae
        if close_gain > CLOSE_IMITATION_RATIO * actual_gain:
            close_imitation = True
            flags.append(
                "close-imitation risk: total-vs-close MAE gain "
                f"{close_gain:.2f} > {CLOSE_IMITATION_RATIO}× actual MAE gain {actual_gain:.2f}"
            )

    reasons.append(f"selected MATCHUP_RESPONSE={selected:.2f} (production remains 1.40)")
    reasons.append(f"Val-1 total vs actual MAE {base_mae} → {sel_mae} (ok={mae_ok})")
    reasons.append(f"Val-1 total vs actual bias {base_bias} → {sel_bias} (ok={bias_ok})")
    reasons.append(f"Val-1 frozen-1.40-tail vs actual bias {base_tail} → {sel_tail} (ok={tail_ok})")
    reasons.append(f"Val-1 margin vs actual MAE {base_spread} → {sel_spread} (ok={spread_ok})")
    reasons.append(f"stability train-1 top={top_train[:3]} val-1 top={top_val1[:3]} stable={stable}")

    if selected <= LOW_RESPONSE_FLOOR and not bias_ok:
        return {
            "decision": "BROADER MODEL RECALIBRATION REQUIRED",
            "selected": selected,
            "why": reasons
            + [
                f"response ≤ {LOW_RESPONSE_FLOOR} still fails location; "
                "PPG / QB index location likely need to move, not only the exponent"
            ],
            "flags": flags,
        }
    if (not spread_ok) or collapse:
        return {
            "decision": "BROADER MODEL RECALIBRATION REQUIRED",
            "selected": selected,
            "why": reasons
            + [
                "isolating MATCHUP_RESPONSE fixes (or chases) totals only by "
                "collapsing useful spread differentiation"
            ],
            "flags": flags,
            "spread_collapsed": collapse,
        }
    if mae_ok and bias_ok and tail_ok and spread_ok and stable and not disagree:
        decision = "COEFFICIENT CANDIDATE EARNED"
        if close_imitation:
            flags.append("earned on actuals, but close-imitation flag is on")
        return {
            "decision": decision,
            "selected": selected,
            "why": reasons,
            "flags": flags,
            "production_unchanged": True,
        }
    if disagree and not (mae_ok and bias_ok and tail_ok):
        return {
            "decision": "INSUFFICIENT EVIDENCE",
            "selected": selected,
            "why": reasons
            + [
                f"Train-1 best={train1_best} and Val-1 best={val1_best} "
                f"disagree by > {DISAGREE_MAX}"
            ],
            "flags": flags,
        }
    if not (mae_ok and bias_ok and tail_ok):
        return {
            "decision": "BROADER MODEL RECALIBRATION REQUIRED",
            "selected": selected,
            "why": reasons
            + [
                "no isolated MATCHUP_RESPONSE value materially corrects "
                "location + MAE + high-tail on Val-1 actuals while keeping spreads"
            ],
            "flags": flags,
        }
    return {
        "decision": "INSUFFICIENT EVIDENCE",
        "selected": selected,
        "why": reasons + ["gates mixed; do not promote a coefficient"],
        "flags": flags,
    }


def select_from_losses(candidates: Mapping[float, Mapping[str, Any]]) -> float:
    """Pick on Train-1 primary loss. Val-1 is reserved for the decision."""
    losses: Dict[float, float] = {}
    for cand, summary in candidates.items():
        loss = ((summary.get("splits") or {}).get("train_1") or {}).get("primary_loss")
        if loss is not None:
            losses[float(cand)] = float(loss)
    if not losses:
        return PRODUCTION_MATCHUP_RESPONSE
    return min(losses, key=losses.get)


def slim_split(block: Mapping[str, Any]) -> Dict[str, Any]:
    keys = (
        "n",
        "primary_loss",
        "total_vs_actual_mae",
        "total_vs_actual_rmse",
        "total_vs_actual_bias",
        "total_vs_close_mae",
        "total_vs_close_rmse",
        "total_vs_close_bias",
        "margin_vs_actual_mae",
        "margin_vs_actual_rmse",
        "margin_vs_actual_bias",
        "spread_vs_close_mae",
        "spread_vs_close_rmse",
        "spread_vs_close_bias",
        "mean_model_total",
        "mean_close_total",
        "mean_actual_total",
        "mean_abs_model_spread",
        "mean_abs_close_spread",
        "ats_n",
        "ats_hit_rate",
        "ats_roi_minus_110",
        "ou_n",
        "ou_hit_rate",
        "ou_roi_minus_110",
        "brier_home_wp",
    )
    out = {k: block.get(k) for k in keys}
    slices = block.get("slices") or {}
    out["high_total_tail_ge_68"] = {
        "n": (slices.get("high_total_tail_ge_68") or {}).get("n"),
        "total_vs_actual_bias": (slices.get("high_total_tail_ge_68") or {}).get(
            "total_vs_actual_bias"
        ),
        "total_vs_close_bias": (slices.get("high_total_tail_ge_68") or {}).get(
            "total_vs_close_bias"
        ),
        "total_vs_actual_mae": (slices.get("high_total_tail_ge_68") or {}).get(
            "total_vs_actual_mae"
        ),
    }
    out["frozen140_high_tail"] = {
        "n": (slices.get("frozen140_high_tail") or {}).get("n"),
        "total_vs_actual_bias": (slices.get("frozen140_high_tail") or {}).get(
            "total_vs_actual_bias"
        ),
        "total_vs_close_bias": (slices.get("frozen140_high_tail") or {}).get(
            "total_vs_close_bias"
        ),
        "total_vs_actual_mae": (slices.get("frozen140_high_tail") or {}).get(
            "total_vs_actual_mae"
        ),
    }
    return out


def run_matchup_response_fit(
    *,
    cache_dir=None,
    lake_only: bool = True,
    grid: Optional[Sequence[float]] = None,
) -> Dict[str, Any]:
    assert_frozen_priors()
    refuse_sealed_or_confirm(LEGAL_SEASONS)
    if QB_FEATURE_CONTRACT_VERSION != "cfb-qb-feature-v1":
        raise FitError("qb feature contract drifted")
    ctx = load_v1_scoring_context(cache_dir=cache_dir)
    joined = ctx["joined_all"]
    universes = ctx["universes"]

    baseline_rows, _ = score_joined_rows(joined, universes, lake_only=lake_only)
    frozen_tail_ids = [
        _game_id(r) for r in baseline_rows if bool(r.get("high_total_tail"))
    ]
    baseline = summarize_scored(baseline_rows)
    for name, block in (baseline.get("splits") or {}).items():
        split_rows = [
            r
            for r in baseline_rows
            if (
                (name == "train_0" and int(r["season"]) == 2022)
                or (name == "val_0" and int(r["season"]) == 2023)
                or (name == "train_1" and int(r["season"]) in (2022, 2023))
                or (name == "val_1" and int(r["season"]) == 2024)
            )
        ]
        block["slices"] = dict(block.get("slices") or {})
        block["slices"]["frozen140_high_tail"] = overlay_frozen_tail(
            split_rows, frozen_tail_ids
        )
        block["primary_loss"] = primary_loss(block)

    coarse = list(grid) if grid is not None else list(COARSE_GRID)
    if PRODUCTION_MATCHUP_RESPONSE not in coarse:
        coarse.append(PRODUCTION_MATCHUP_RESPONSE)
    candidates: Dict[float, Dict[str, Any]] = {}
    skipped_last: Dict[str, Any] = {}
    for cand in coarse:
        summary, _scored, skipped = score_candidate(
            joined,
            universes,
            cand,
            lake_only=lake_only,
            frozen_tail_ids=frozen_tail_ids,
        )
        candidates[float(cand)] = summary
        skipped_last = skipped

    selected_coarse = select_from_losses(candidates)
    for extra in refine_grid(selected_coarse):
        if extra in candidates:
            continue
        if extra < 0.60 or extra > 1.60:
            continue
        summary, _scored, skipped = score_candidate(
            joined,
            universes,
            extra,
            lake_only=lake_only,
            frozen_tail_ids=frozen_tail_ids,
        )
        candidates[float(extra)] = summary
        skipped_last = skipped

    selected = select_from_losses(candidates)
    decision = decide_fit(baseline=baseline, candidates=candidates, selected=selected)
    if float(P.MATCHUP_RESPONSE) != PRODUCTION_MATCHUP_RESPONSE:
        raise FitError("MATCHUP_RESPONSE leaked out of the fit loop")

    sensitivity = []
    for cand in sorted(candidates):
        splits = (candidates[cand].get("splits") or {})
        sensitivity.append(
            {
                "matchup_response": cand,
                "train_0": slim_split(splits.get("train_0") or {}),
                "val_0": slim_split(splits.get("val_0") or {}),
                "train_1": slim_split(splits.get("train_1") or {}),
                "val_1": slim_split(splits.get("val_1") or {}),
            }
        )

    return {
        "kind": "cfb_matchup_response_coefficient_fit",
        "authoritative_recovery_pr": AUTHORITATIVE_PR,
        "qb_feature_contract_version": QB_FEATURE_CONTRACT_VERSION,
        "production_matchup_response": PRODUCTION_MATCHUP_RESPONSE,
        "production_unchanged": True,
        "opened_2025": False,
        "used_2026_for_fitting": False,
        "recalibrated_production": False,
        "play": False,
        "kill_switch": True,
        "lake_only": lake_only,
        "coarse_grid": list(COARSE_GRID),
        "selected": selected,
        "selected_coarse": selected_coarse,
        "decision": decision,
        "baseline_1_40": {
            "splits": {
                name: slim_split(block)
                for name, block in (baseline.get("splits") or {}).items()
            }
        },
        "sensitivity": sensitivity,
        "lake_locate": ctx["lake_locate"],
        "skipped": skipped_last,
        "frozen140_high_tail_n": len(frozen_tail_ids),
        "notes": [
            "Fit isolates MATCHUP_RESPONSE. Early-season soften still applies.",
            "Train-1 primary_loss ranks candidates. Val-1 decides.",
            "Actual MAE/bias/tail are primary. Close is diagnostic.",
            "1.18 is on the grid with no privilege.",
            "Production MATCHUP_RESPONSE remains 1.40.",
        ],
    }
