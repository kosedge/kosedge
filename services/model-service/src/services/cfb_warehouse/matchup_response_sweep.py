"""MATCHUP_RESPONSE-only coefficient sweep on the reconstructed v1 universe.

Research fit. Production ``MATCHUP_RESPONSE`` stays 1.40. All other model
components are frozen (QB contract, class multipliers, roster logic, PPG,
close semantics, historical universes, train/val splits).

Primary objective is predictive accuracy vs **actual** scores. Market close
is a benchmark and calibration diagnostic, not the loss.

Does not unseal 2025. Does not use 2026 for parameter selection. Does not
publish PLAY or write a new production coefficient.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from src.services.cfb_season_engine import priors as P
from src.services.cfb_season_engine.priors import overlay_matchup_response
from src.services.cfb_season_engine.qb_feature_contract import (
    QB_FEATURE_CONTRACT_VERSION,
)
from src.services.cfb_warehouse.frozen_140_scoring import (
    HIGH_TOTAL_TAIL,
    LEGAL_SEASONS,
    TRAIN0_GATE,
    VAL1_GATE,
    FrozenScoringError,
    assert_frozen_priors,
    load_legal_scoring_bundle,
    refuse_sealed_or_confirm,
    score_joined_rows,
    summarize_scored,
)

COARSE_LO = 0.90
COARSE_HI = 1.40
COARSE_STEP = 0.05
REFINE_RADIUS = 0.04
REFINE_STEP = 0.02
EXTEND_LO = 0.70
EXTEND_STEP = 0.05
FROZEN_RESPONSE = 1.40

# PR #543 published Val-1 frozen 1.40 diagnostics. Sweep candidate 1.40 must
# reproduce these or the universe drifted.
PUBLISHED_VAL1_N = 717
PUBLISHED_TRAIN0_N = 712
PUBLISHED_VAL1_CLOSE_BIAS = 11.34
PUBLISHED_VAL1_TAIL_CLOSE_BIAS = 17.79
PUBLISHED_VAL1_ACTUAL_BIAS = 10.10
SANITY_N_TOL = 2
SANITY_BIAS_TOL = 0.40

# Selection / earn gates. Actual-primary. Close is diagnostic only.
MIN_MAE_IMPROVE = 0.25
BIAS_REDUCE_FRAC = 0.50
BIAS_ABS_OK = 3.0
TAIL_N_DROP_FRAC = 0.30
TAIL_BIAS_ABS_OK = 4.0
STABILITY_ABS = 0.10
MIN_DISAGREE = 3.0
DISAGREE_KEEP_FRAC = 0.40
MARGIN_MAE_DESTROY = 1.0
ATS_DESTROY = 0.03
MAE_VS_BIAS_SPLIT = 0.15
BOUNDARY_FLOOR = 0.72

OBJECTIVE_SPLITS = ("train_0", "val_0", "val_1")


def _round2(value: float) -> float:
    return round(float(value) + 1e-12, 2)


def coarse_grid() -> List[float]:
    n = int(round((COARSE_HI - COARSE_LO) / COARSE_STEP))
    return [_round2(COARSE_LO + i * COARSE_STEP) for i in range(n + 1)]


def refine_grid(center: float) -> List[float]:
    lo = max(EXTEND_LO, _round2(center - REFINE_RADIUS))
    hi = min(COARSE_HI, _round2(center + REFINE_RADIUS))
    n = int(round((hi - lo) / REFINE_STEP))
    return [_round2(lo + i * REFINE_STEP) for i in range(n + 1)]


def extend_low_grid() -> List[float]:
    n = int(round((COARSE_LO - EXTEND_LO) / EXTEND_STEP))
    return [_round2(EXTEND_LO + i * EXTEND_STEP) for i in range(n)]


def merge_grid(*grids: Iterable[float]) -> List[float]:
    seen = set()
    out: List[float] = []
    for grid in grids:
        for raw in grid:
            value = _round2(raw)
            if value in seen:
                continue
            seen.add(value)
            out.append(value)
    out.sort()
    return out


def split_card(block: Mapping[str, Any]) -> Dict[str, Any]:
    high = (block.get("slices") or {}).get("high_total_tail_ge_68") or {}
    buckets = block.get("total_disagree_buckets") or {}
    bucket_cards = {}
    for name, brow in buckets.items():
        bucket_cards[name] = {
            "n": brow.get("n"),
            "mae_vs_actual": brow.get("total_vs_actual_mae"),
            "bias_vs_actual": brow.get("total_vs_actual_bias"),
            "mae_vs_close": brow.get("total_vs_close_mae"),
            "bias_vs_close": brow.get("total_vs_close_bias"),
            "ats_hit_rate": brow.get("ats_hit_rate"),
            "ats_roi_minus_110": brow.get("ats_roi_minus_110"),
            "mean_model_total": brow.get("mean_model_total"),
            "mean_actual_total": brow.get("mean_actual_total"),
            "mean_close_total": brow.get("mean_close_total"),
        }
    return {
        "n": block.get("n") or 0,
        "mae_vs_actual": block.get("total_vs_actual_mae"),
        "rmse_vs_actual": block.get("total_vs_actual_rmse"),
        "bias_vs_actual": block.get("total_vs_actual_bias"),
        "medae_vs_actual": block.get("total_vs_actual_median_abs"),
        "error_vs_actual_quantiles": block.get("error_vs_actual_quantiles"),
        "mae_vs_close": block.get("total_vs_close_mae"),
        "rmse_vs_close": block.get("total_vs_close_rmse"),
        "bias_vs_close": block.get("total_vs_close_bias"),
        "medae_vs_close": block.get("total_vs_close_median_abs"),
        "disagree_vs_close_quantiles": block.get("disagree_vs_close_quantiles"),
        "mean_abs_disagree_total": block.get("mean_abs_disagree_total")
        or block.get("total_vs_close_mae"),
        "mean_model_total": block.get("mean_model_total"),
        "mean_close_total": block.get("mean_close_total"),
        "mean_actual_total": block.get("mean_actual_total"),
        "high_tail_n": int(high.get("n") or 0),
        "high_tail_mae_vs_actual": high.get("total_vs_actual_mae"),
        "high_tail_bias_vs_actual": high.get("total_vs_actual_bias"),
        "high_tail_bias_vs_close": high.get("total_vs_close_bias"),
        "high_tail_mean_model": high.get("mean_model_total"),
        "high_tail_mean_actual": high.get("mean_actual_total"),
        "high_tail_mean_close": high.get("mean_close_total"),
        "ats_n": block.get("ats_n") or 0,
        "ats_hit_rate": block.get("ats_hit_rate"),
        "ats_roi_minus_110": block.get("ats_roi_minus_110"),
        "ou_n": block.get("ou_n") or 0,
        "ou_hit_rate": block.get("ou_hit_rate"),
        "ou_roi_minus_110": block.get("ou_roi_minus_110"),
        "margin_mae_vs_actual": block.get("margin_vs_actual_mae"),
        "spread_mae_vs_close": block.get("spread_vs_close_mae"),
        "total_disagree_buckets": bucket_cards,
    }


def candidate_record(
    matchup_response: float,
    summary: Mapping[str, Any],
    *,
    phase: str,
) -> Dict[str, Any]:
    splits = summary.get("splits") or {}
    cards = {name: split_card(splits.get(name) or {}) for name in OBJECTIVE_SPLITS}
    return {
        "matchup_response": _round2(matchup_response),
        "phase": phase,
        "frozen_constant_still": P.MATCHUP_RESPONSE,
        "splits": cards,
    }


def _num(card: Mapping[str, Any], key: str) -> Optional[float]:
    val = card.get(key)
    if val is None:
        return None
    return float(val)


def argmin_response(
    records: Sequence[Mapping[str, Any]],
    split: str,
    metric: str,
    *,
    abs_metric: bool = False,
) -> Optional[float]:
    best_r: Optional[float] = None
    best_v: Optional[float] = None
    for rec in records:
        card = (rec.get("splits") or {}).get(split) or {}
        raw = _num(card, metric)
        if raw is None:
            continue
        value = abs(raw) if abs_metric else raw
        resp = float(rec["matchup_response"])
        if best_v is None or value < best_v - 1e-12 or (
            abs(value - best_v) <= 1e-12 and resp < float(best_r or resp)
        ):
            best_v = value
            best_r = resp
    return best_r


def _improved(new: Optional[float], old: Optional[float], min_delta: float) -> bool:
    if new is None or old is None:
        return False
    return (old - new) >= min_delta - 1e-12


def _reduced_abs(
    new: Optional[float],
    old: Optional[float],
    frac: float,
    abs_ok: float,
) -> bool:
    if new is None or old is None:
        return False
    if abs(new) <= abs_ok + 1e-12:
        return True
    return abs(new) <= abs(old) * (1.0 - frac) + 1e-12


def decide_coefficient(
    records: Sequence[Mapping[str, Any]],
    *,
    lake_mounted: bool,
    sanity: Mapping[str, Any],
) -> Dict[str, Any]:
    """One decision. Actual metrics are the objective. Close is diagnostic."""
    reasons: List[str] = []
    if not lake_mounted:
        return {
            "decision": "INSUFFICIENT EVIDENCE",
            "recommended": None,
            "best_region": None,
            "why": ["legal Odds-API lake not mounted; cannot score Train-0/Val-0/Val-1"],
            "sanity": sanity,
        }
    if not sanity.get("ok"):
        return {
            "decision": "INSUFFICIENT EVIDENCE",
            "recommended": None,
            "best_region": None,
            "why": list(sanity.get("why") or ["frozen 1.40 candidate failed PR #543 sanity"]),
            "sanity": sanity,
        }
    if not records:
        return {
            "decision": "INSUFFICIENT EVIDENCE",
            "recommended": None,
            "best_region": None,
            "why": ["no candidates scored"],
            "sanity": sanity,
        }

    by_r = {float(r["matchup_response"]): r for r in records}
    frozen = by_r.get(FROZEN_RESPONSE)
    if frozen is None:
        return {
            "decision": "INSUFFICIENT EVIDENCE",
            "recommended": None,
            "best_region": None,
            "why": ["sweep did not rescore frozen 1.40 on the same universe"],
            "sanity": sanity,
        }

    f_val1 = (frozen.get("splits") or {}).get("val_1") or {}
    f_train = (frozen.get("splits") or {}).get("train_0") or {}
    f_val0 = (frozen.get("splits") or {}).get("val_0") or {}
    n_val1 = int(f_val1.get("n") or 0)
    n_train = int(f_train.get("n") or 0)
    n_val0 = int(f_val0.get("n") or 0)
    if n_val1 < VAL1_GATE or n_train < TRAIN0_GATE or n_val0 < TRAIN0_GATE:
        return {
            "decision": "INSUFFICIENT EVIDENCE",
            "recommended": None,
            "best_region": None,
            "why": [
                f"Train-0 n={n_train} (need {TRAIN0_GATE})",
                f"Val-0 n={n_val0} (need {TRAIN0_GATE})",
                f"Val-1 n={n_val1} (need {VAL1_GATE})",
            ],
            "sanity": sanity,
        }

    mae_best = argmin_response(records, "val_1", "mae_vs_actual")
    bias_best = argmin_response(records, "val_1", "bias_vs_actual", abs_metric=True)
    rmse_best = argmin_response(records, "val_1", "rmse_vs_actual")
    train_mae_best = argmin_response(records, "train_0", "mae_vs_actual")
    val0_mae_best = argmin_response(records, "val_0", "mae_vs_actual")
    if mae_best is None:
        return {
            "decision": "INSUFFICIENT EVIDENCE",
            "recommended": None,
            "best_region": None,
            "why": ["Val-1 MAE vs actual missing on all candidates"],
            "sanity": sanity,
        }

    rec = by_r[mae_best]
    card = (rec.get("splits") or {}).get("val_1") or {}
    region = {
        "val1_mae_vs_actual_min": mae_best,
        "val1_abs_bias_vs_actual_min": bias_best,
        "val1_rmse_vs_actual_min": rmse_best,
        "train0_mae_vs_actual_min": train_mae_best,
        "val0_mae_vs_actual_min": val0_mae_best,
    }

    if mae_best == FROZEN_RESPONSE:
        reasons.append("Val-1 MAE vs actual is minimized at frozen 1.40")
        reasons.append(
            "MATCHUP_RESPONSE alone cannot improve predictive location vs 1.40"
        )
        return {
            "decision": "BROADER MODEL RECALIBRATION REQUIRED",
            "recommended": None,
            "best_region": region,
            "why": reasons,
            "sanity": sanity,
            "comparison_vs_140": _compare(card, f_val1),
        }

    if mae_best <= BOUNDARY_FLOOR + 1e-12:
        reasons.append(
            f"Val-1 MAE vs actual still minimized at the floor ({mae_best:.2f})"
        )
        reasons.append(
            "response would have to leave the authorized neighborhood of 1.40"
        )
        return {
            "decision": "BROADER MODEL RECALIBRATION REQUIRED",
            "recommended": None,
            "best_region": region,
            "why": reasons,
            "sanity": sanity,
            "comparison_vs_140": _compare(card, f_val1),
        }

    if (
        bias_best is not None
        and abs(float(bias_best) - float(mae_best)) > MAE_VS_BIAS_SPLIT + 1e-12
    ):
        bias_card = ((by_r[bias_best].get("splits") or {}).get("val_1") or {})
        if not _reduced_abs(
            _num(card, "bias_vs_actual"),
            _num(f_val1, "bias_vs_actual"),
            BIAS_REDUCE_FRAC,
            BIAS_ABS_OK,
        ):
            reasons.append(
                f"Val-1 MAE-best {mae_best:.2f} and |bias|-best {bias_best:.2f} "
                f"differ by > {MAE_VS_BIAS_SPLIT:.2f}"
            )
            reasons.append(
                "one coefficient cannot jointly fix location and tails/bias"
            )
            reasons.append(
                f"MAE-best actual bias={_num(card, 'bias_vs_actual')} "
                f"vs |bias|-best {_num(bias_card, 'bias_vs_actual')}"
            )
            return {
                "decision": "BROADER MODEL RECALIBRATION REQUIRED",
                "recommended": None,
                "best_region": region,
                "why": reasons,
                "sanity": sanity,
                "comparison_vs_140": _compare(card, f_val1),
            }

    checks: List[Tuple[bool, str]] = []
    checks.append(
        (
            _improved(
                _num(card, "mae_vs_actual"),
                _num(f_val1, "mae_vs_actual"),
                MIN_MAE_IMPROVE,
            ),
            (
                f"Val-1 MAE vs actual {_num(card, 'mae_vs_actual')} vs "
                f"1.40 {_num(f_val1, 'mae_vs_actual')} "
                f"(need ≥{MIN_MAE_IMPROVE:.2f} improvement)"
            ),
        )
    )
    checks.append(
        (
            _reduced_abs(
                _num(card, "bias_vs_actual"),
                _num(f_val1, "bias_vs_actual"),
                BIAS_REDUCE_FRAC,
                BIAS_ABS_OK,
            ),
            (
                f"Val-1 bias vs actual {_num(card, 'bias_vs_actual')} vs "
                f"1.40 {_num(f_val1, 'bias_vs_actual')} "
                f"(need |bias|<{BIAS_ABS_OK} or ≥{int(BIAS_REDUCE_FRAC*100)}% reduction)"
            ),
        )
    )
    tail_n = int(card.get("high_tail_n") or 0)
    f_tail_n = int(f_val1.get("high_tail_n") or 0)
    tail_ok = _reduced_abs(
        _num(card, "high_tail_bias_vs_actual"),
        _num(f_val1, "high_tail_bias_vs_actual"),
        BIAS_REDUCE_FRAC,
        TAIL_BIAS_ABS_OK,
    ) or (
        f_tail_n > 0 and tail_n <= f_tail_n * (1.0 - TAIL_N_DROP_FRAC) + 1e-12
    )
    checks.append(
        (
            tail_ok,
            (
                f"high-tail n={tail_n} bias-vs-actual "
                f"{_num(card, 'high_tail_bias_vs_actual')} vs 1.40 n={f_tail_n} "
                f"bias {_num(f_val1, 'high_tail_bias_vs_actual')}"
            ),
        )
    )

    stable = True
    if train_mae_best is not None and abs(train_mae_best - mae_best) > STABILITY_ABS:
        stable = False
    if val0_mae_best is not None and abs(val0_mae_best - mae_best) > STABILITY_ABS:
        stable = False
    checks.append(
        (
            stable,
            (
                f"stability: Train-0 MAE-min={train_mae_best} "
                f"Val-0 MAE-min={val0_mae_best} Val-1 MAE-min={mae_best} "
                f"(need within ±{STABILITY_ABS:.2f})"
            ),
        )
    )

    disagree = _num(card, "mean_abs_disagree_total")
    f_disagree = _num(f_val1, "mean_abs_disagree_total")
    floor = MIN_DISAGREE
    if f_disagree is not None:
        floor = max(MIN_DISAGREE, DISAGREE_KEEP_FRAC * f_disagree)
    checks.append(
        (
            disagree is not None and disagree + 1e-12 >= floor,
            (
                f"Val-1 mean |model−close|={disagree} "
                f"(need ≥{floor:.2f} so the model is not a Vegas clone)"
            ),
        )
    )

    margin_new = _num(card, "margin_mae_vs_actual")
    margin_old = _num(f_val1, "margin_mae_vs_actual")
    margin_ok = True
    if margin_new is not None and margin_old is not None:
        margin_ok = margin_new <= margin_old + MARGIN_MAE_DESTROY + 1e-12
    checks.append(
        (
            margin_ok,
            (
                f"Val-1 margin MAE vs actual {margin_new} vs 1.40 {margin_old} "
                f"(must not worsen by >{MARGIN_MAE_DESTROY:.1f})"
            ),
        )
    )

    ats_new = _num(card, "ats_hit_rate")
    ats_old = _num(f_val1, "ats_hit_rate")
    ats_n = int(card.get("ats_n") or 0)
    ats_ok = True
    if ats_new is not None and ats_old is not None and ats_n >= 400:
        ats_ok = ats_new + 1e-12 >= ats_old - ATS_DESTROY
    checks.append(
        (
            ats_ok,
            (
                f"Val-1 ATS {ats_new} vs 1.40 {ats_old} "
                f"(must not drop >{ATS_DESTROY:.0%} when ATS n≥400)"
            ),
        )
    )

    failed = [msg for ok, msg in checks if not ok]
    passed = [msg for ok, msg in checks if ok]
    if failed:
        return {
            "decision": "BROADER MODEL RECALIBRATION REQUIRED",
            "recommended": None,
            "best_region": region,
            "why": [
                f"Val-1 MAE-best candidate {mae_best:.2f} did not earn a ship",
                *failed,
            ],
            "passed": passed,
            "sanity": sanity,
            "comparison_vs_140": _compare(card, f_val1),
        }

    reasons = [
        f"Val-1 MAE vs actual minimized at {mae_best:.2f}",
        *passed,
        "close metrics used as diagnostics only; selection did not minimize |model−close|",
        "production MATCHUP_RESPONSE remains 1.40 until a later ship authorization",
    ]
    return {
        "decision": "COEFFICIENT CANDIDATE EARNED",
        "recommended": mae_best,
        "best_region": region,
        "why": reasons,
        "passed": passed,
        "sanity": sanity,
        "comparison_vs_140": _compare(card, f_val1),
        "note": (
            "Earned for research. Do not write priors.MATCHUP_RESPONSE. "
            "Do not touch 2025, 2026, PLAY, or Line Curve."
        ),
    }


def _compare(new: Mapping[str, Any], old: Mapping[str, Any]) -> Dict[str, Any]:
    keys = (
        "n",
        "mae_vs_actual",
        "rmse_vs_actual",
        "bias_vs_actual",
        "medae_vs_actual",
        "bias_vs_close",
        "mae_vs_close",
        "mean_abs_disagree_total",
        "high_tail_n",
        "high_tail_bias_vs_actual",
        "high_tail_bias_vs_close",
        "mean_model_total",
        "mean_actual_total",
        "mean_close_total",
        "ats_hit_rate",
        "ats_roi_minus_110",
        "margin_mae_vs_actual",
    )
    out: Dict[str, Any] = {}
    for key in keys:
        n = new.get(key)
        o = old.get(key)
        delta = None
        if n is not None and o is not None:
            try:
                delta = float(n) - float(o)
            except (TypeError, ValueError):
                delta = None
        out[key] = {"candidate": n, "frozen_140": o, "delta": delta}
    return out


def sanity_check_frozen_140(card: Mapping[str, Any]) -> Dict[str, Any]:
    why: List[str] = []
    n = int(card.get("n") or 0)
    close_bias = _num(card, "bias_vs_close")
    tail_bias = _num(card, "high_tail_bias_vs_close")
    actual_bias = _num(card, "bias_vs_actual")
    if abs(n - PUBLISHED_VAL1_N) > SANITY_N_TOL:
        why.append(f"Val-1 n={n} ≠ published {PUBLISHED_VAL1_N}")
    if close_bias is None or abs(close_bias - PUBLISHED_VAL1_CLOSE_BIAS) > SANITY_BIAS_TOL:
        why.append(
            f"Val-1 close bias={close_bias} ≠ published {PUBLISHED_VAL1_CLOSE_BIAS}"
        )
    if (
        tail_bias is None
        or abs(tail_bias - PUBLISHED_VAL1_TAIL_CLOSE_BIAS) > SANITY_BIAS_TOL
    ):
        why.append(
            f"Val-1 tail close bias={tail_bias} ≠ published "
            f"{PUBLISHED_VAL1_TAIL_CLOSE_BIAS}"
        )
    if (
        actual_bias is None
        or abs(actual_bias - PUBLISHED_VAL1_ACTUAL_BIAS) > SANITY_BIAS_TOL
    ):
        why.append(
            f"Val-1 actual bias={actual_bias} ≠ published {PUBLISHED_VAL1_ACTUAL_BIAS}"
        )
    return {
        "ok": not why,
        "why": why,
        "observed": {
            "n": n,
            "bias_vs_close": close_bias,
            "high_tail_bias_vs_close": tail_bias,
            "bias_vs_actual": actual_bias,
        },
        "published": {
            "n": PUBLISHED_VAL1_N,
            "bias_vs_close": PUBLISHED_VAL1_CLOSE_BIAS,
            "high_tail_bias_vs_close": PUBLISHED_VAL1_TAIL_CLOSE_BIAS,
            "bias_vs_actual": PUBLISHED_VAL1_ACTUAL_BIAS,
            "source": "PR #543 / data/ops/cfb-frozen-140-scoring-20260912.json",
        },
    }


def score_candidate(
    matchup_response: float,
    bundle: Mapping[str, Any],
    *,
    lake_only: bool,
    phase: str,
) -> Dict[str, Any]:
    assert_frozen_priors()
    if abs(float(P.MATCHUP_RESPONSE) - FROZEN_RESPONSE) > 1e-9:
        raise FrozenScoringError("production MATCHUP_RESPONSE drifted from 1.40")
    with overlay_matchup_response(matchup_response):
        if abs(P.matchup_response_base() - float(matchup_response)) > 1e-9:
            raise FrozenScoringError("overlay failed to apply")
        if abs(float(P.MATCHUP_RESPONSE) - FROZEN_RESPONSE) > 1e-9:
            raise FrozenScoringError("overlay mutated MATCHUP_RESPONSE")
        scored, skipped = score_joined_rows(
            bundle["joined"], bundle["universes"], lake_only=lake_only
        )
    if abs(float(P.MATCHUP_RESPONSE) - FROZEN_RESPONSE) > 1e-9:
        raise FrozenScoringError("overlay leaked after reset")
    if P.matchup_response_base() != float(P.MATCHUP_RESPONSE):
        raise FrozenScoringError("overlay leaked into matchup_response_base")
    summary = summarize_scored(scored)
    rec = candidate_record(matchup_response, summary, phase=phase)
    rec["skipped"] = skipped
    rec["n_scored"] = summary.get("n_scored")
    return rec


def run_matchup_response_sweep(
    *,
    cache_dir=None,
    lake_only: bool = True,
) -> Dict[str, Any]:
    assert_frozen_priors()
    refuse_sealed_or_confirm(LEGAL_SEASONS)
    if QB_FEATURE_CONTRACT_VERSION != "cfb-qb-feature-v1":
        raise FrozenScoringError("qb feature contract drifted")

    bundle = load_legal_scoring_bundle(cache_dir=cache_dir, lake_only=lake_only)
    lake_mounted = all(
        (bundle.get("lake_locate") or {}).get(str(season), {}).get("mounted")
        for season in LEGAL_SEASONS
    )

    records: List[Dict[str, Any]] = []
    scored_r: set[float] = set()

    def _run(values: Sequence[float], phase: str) -> None:
        for raw in values:
            resp = _round2(raw)
            if resp in scored_r:
                continue
            records.append(
                score_candidate(resp, bundle, lake_only=lake_only, phase=phase)
            )
            scored_r.add(resp)

    if not lake_mounted:
        gate = decide_coefficient([], lake_mounted=False, sanity={"ok": False, "why": []})
        return _payload(bundle, records, gate, lake_mounted=False)

    _run(coarse_grid(), "coarse")
    frozen = next(
        (r for r in records if abs(float(r["matchup_response"]) - FROZEN_RESPONSE) < 1e-9),
        None,
    )
    sanity = sanity_check_frozen_140(
        ((frozen or {}).get("splits") or {}).get("val_1") or {}
    )
    if not sanity.get("ok"):
        gate = decide_coefficient(records, lake_mounted=True, sanity=sanity)
        return _payload(bundle, records, gate, lake_mounted=True)

    mae_best = argmin_response(records, "val_1", "mae_vs_actual")
    if mae_best is not None and abs(mae_best - COARSE_LO) < 1e-9:
        _run(extend_low_grid(), "extend_low")
        mae_best = argmin_response(records, "val_1", "mae_vs_actual")
    if mae_best is not None:
        _run(refine_grid(mae_best), "refine")

    records.sort(key=lambda r: float(r["matchup_response"]))
    gate = decide_coefficient(records, lake_mounted=True, sanity=sanity)
    return _payload(bundle, records, gate, lake_mounted=True)


def _payload(
    bundle: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    gate: Mapping[str, Any],
    *,
    lake_mounted: bool,
) -> Dict[str, Any]:
    return {
        "qb_feature_contract_version": QB_FEATURE_CONTRACT_VERSION,
        "matchup_response_frozen": P.MATCHUP_RESPONSE,
        "engine_version": P.ENGINE_VERSION,
        "kill_switch": True,
        "opened_2025": False,
        "used_2026_for_fitting": False,
        "wrote_production_coefficient": False,
        "play": False,
        "lake_only": True,
        "lake_mounted": lake_mounted,
        "objective": (
            "actual MAE / RMSE / signed bias / MedAE / tail error; "
            "close is benchmark only"
        ),
        "frozen_components": [
            "QB feature contract",
            "QB weights",
            "class multipliers",
            "roster logic",
            "PPG assumptions",
            "close semantics",
            "historical universes",
            "train/validation splits",
        ],
        "grid": {
            "coarse": coarse_grid(),
            "refine_radius": REFINE_RADIUS,
            "refine_step": REFINE_STEP,
            "extend_low_if_needed": extend_low_grid(),
        },
        "lake_locate": bundle.get("lake_locate"),
        "load": bundle.get("load"),
        "layer_a_talent": bundle.get("layer_a_talent"),
        "candidates": list(records),
        "decision": gate,
        "high_total_tail": HIGH_TOTAL_TAIL,
        "reconstruction_limits": [
            "Only MATCHUP_RESPONSE is overlaid at score time. Production constant remains 1.40.",
            "Early-season soften (W1=0.90 / W2=0.93 / W3=0.96 / W4=0.98) still multiplies the candidate.",
            "Layer A QB only. Layer B cast/recruiting held out at 50.",
            "2025 sealed. 2026 not used for selection.",
            "Selection does not minimize |model−close|. A model at 61 can beat a close of 52 when the game finishes 66.",
        ],
    }
