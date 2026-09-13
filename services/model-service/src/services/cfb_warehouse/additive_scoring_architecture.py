"""Additive raw O/D scoring architecture. Research only.

C2 is architectural evidence, not a coefficient. This module:

1. Audits C2 distribution compression (Val-1 ≥68 bucket 54 → 3).
2. Specifies a first-principles additive scoring equation in point space.
3. Scores a small predeclared candidate set on the frozen splits.

Do not fit α/β, do not write MATCHUP_RESPONSE, do not ship C2, do not
unseal 2025, do not turn the board on. Actual scores are the objective.
Sportsbook close is diagnostic only.
"""

from __future__ import annotations

import math
import statistics
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from src.services.cfb_season_engine import priors as P
from src.services.cfb_season_engine.priors import (
    overlay_matchup_response,
    overlay_score_components,
)
from src.services.cfb_season_engine.qb_feature_contract import (
    QB_FEATURE_CONTRACT_VERSION,
)
from src.services.cfb_season_engine.team_features import (
    CFB_EDGE_BOARD_PUBLIC_ENABLED,
)
from src.services.cfb_warehouse.frozen_140_scoring import (
    LEGAL_SEASONS,
    FrozenScoringError,
    assert_frozen_priors,
    load_legal_scoring_bundle,
    refuse_sealed_or_confirm,
    score_joined_rows,
    summarize_scored,
)
from src.services.cfb_warehouse.matchup_architecture_holdout import (
    FROZEN_BASELINE,
    PROTOCOL_SPLITS,
    _card,
    _enrich,
    _favorite_card,
    _split_rows,
)
from src.services.cfb_warehouse.raw_od_interaction import (
    ACTUAL_BUCKETS,
    MIN_BUCKET_N,
    PROJ_BUCKETS,
    _bias_range,
    _bucket_card,
    _mae,
    _mean,
    _ols,
)

# Documented identities. Not Train-0 fits.
LEAGUE_TEAM_POSSESSIONS = 12.6
HALF_INDEX_SLOPE = P.LEAGUE_TEAM_PPG / (2.0 * P.SCORE_TO_INDEX_DIVISOR)
FULL_INDEX_SLOPE = P.LEAGUE_TEAM_PPG / P.SCORE_TO_INDEX_DIVISOR
ALGEBRA_TOL = 0.02
A1_A4_MAX_ABS_DIFF = 0.02

# Predeclared gates. Do not edit after seeing scores.
RANGE_DROP = 8.0
BIAS_ABS_OK = 3.0
FAV_DROP_OK = 0.03
DISPERSION_FLOOR = 0.50
TAIL_GT65_RATIO_FLOOR = 0.25
P90_UNDER_MAX = 12.0
P10_OVER_MAX = 12.0

# ---------------------------------------------------------------------------
# Predeclared candidates. This list is the spec. Do not append after scoring.
# ---------------------------------------------------------------------------
#
# References (not promotion candidates):
#   E3_ref  — raw off/def ratio. Known: mean fixed, 21-pt residual range.
#   C2_ref  — 25.9 × (0.5·off_idx + 0.5·(2−def_idx)) × units × pace.
#             Architectural evidence only. Do not fit the 0.5/0.5.
#   A5_c2_unclamped — C2 with the (7, 55) team-score rail off. Isolates
#             whether the 54→3 high-total drop is the 55 cap.
#
# First-principles additive equation (point space, not a matchup product):
#
#   E[pts_i] = pace · (μ + α(Off_i − 50) + β(50 − Def_j)) + HFA_i + coach_i
#   total    = E[home] + E[away]
#   spread   = E[away] − E[home]   (existing home-spread convention)
#
#   μ = 25.9          documented league team PPG
#   center = 50       documented 0–100 scale center
#   α = β             same packaged scale; symmetry, not a Val-1 fit
#   α_half = 25.9/136 each quality axis owns half a linearized index unit
#   α_full = 25.9/68  C3-equivalent negative control (too steep already)
#
# Scoring level (μ) is separate from the matchup differential (α, β).
# Pace scales possessions of the whole rate. HFA/coach stay additive
# point adjustments. Total and margin share one scoring path.
#
# A1_point_half:
#   α = β = 25.9/136, units = 1, no index clamp, no (7, 55) rail.
#   Football: additive raw O/D around the league baseline.
#
# A2_point_units:
#   A1 with roster unit multipliers on the rate. Tests whether units
#   belong in an honest additive engine or reintroduce a product leak.
#
# A3_point_full:
#   α = β = 25.9/68. Negative control: C3 in point space. Pretty means
#   with a worse residual range are not a pass.
#
# A4_point_poss:
#   poss = 12.6 · pace
#   ppp  = μ/12.6 + (α/12.6)(Off−50) + (β/12.6)(50−Def)
#   E[pts] = poss · ppp + HFA + coach
#   Must equal A1. If it does not, the implementation is wrong.

CANDIDATES: Tuple[Dict[str, Any], ...] = (
    {
        "id": "E3_ref",
        "family": "reference",
        "label": "E3 raw off_eff/def_eff ratio ** 1.00",
        "response": 1.00,
        "overlay": {"matchup_mode": "raw_efficiency"},
        "role": "reference",
        "rationale": (
            "Lead ratio architecture. Mean bias almost gone; residual "
            "range still ~21. The ≥68 bucket is the compression baseline."
        ),
    },
    {
        "id": "C2_ref",
        "family": "reference",
        "label": "C2 additive 0.5*off_idx + 0.5*(2−def_idx) (product form)",
        "response": None,
        "overlay": {"matchup_mode": "raw_additive"},
        "role": "reference",
        "rationale": (
            "Architectural evidence only. Do not ship. Do not fit 0.5/0.5. "
            "Still a 25.9 × matchup × units × pace product."
        ),
    },
    {
        "id": "A5_c2_unclamped",
        "family": "diagnostic",
        "label": "C2 with (7, 55) team-score clamp off",
        "response": None,
        "overlay": {"matchup_mode": "raw_additive", "disable_clamp": True},
        "role": "diagnostic",
        "rationale": (
            "If ≥68 stays near 3 after removing the 55 rail, the missing "
            "high totals are the half-index slope, not the clamp."
        ),
    },
    {
        "id": "A1_point_half",
        "family": "point_additive",
        "label": "μ + (25.9/136)(Off−50) + (25.9/136)(50−Def), pace scales rate",
        "response": None,
        "overlay": {
            "matchup_mode": "point_additive_half",
            "disable_clamp": True,
        },
        "role": "candidate",
        "rationale": (
            "First-principles additive scoring in point space. μ=25.9 is "
            "the scoring level. α=β=25.9/136 is each axis owning half a "
            "linearized index unit — the C2 slope written without a "
            "matchup product. Units off (C1: units were not the slope). "
            "Pace scales possessions of the whole rate. No index clamp, "
            "no (7, 55) rail, so tails are the equation."
        ),
    },
    {
        "id": "A2_point_units",
        "family": "point_additive",
        "label": "A1 with unit offense boost × defense dampen on the rate",
        "response": None,
        "overlay": {
            "matchup_mode": "point_additive_units",
            "disable_clamp": True,
        },
        "role": "candidate",
        "rationale": (
            "Same additive rate as A1, then roster units scale the whole "
            "rate. Tests whether units belong in an additive engine or "
            "reintroduce a product."
        ),
    },
    {
        "id": "A3_point_full",
        "family": "point_additive",
        "label": "μ + (25.9/68)(Off−50) + (25.9/68)(50−Def) — C3 in point space",
        "response": None,
        "overlay": {
            "matchup_mode": "point_additive_full",
            "disable_clamp": True,
        },
        "role": "candidate",
        "rationale": (
            "Negative control. Full linearized index slope on both axes. "
            "C3 already showed a pretty mean and a worse residual range. "
            "If A3 looks calibrated only because it stretches tails, it fails."
        ),
    },
    {
        "id": "A4_point_poss",
        "family": "identity_check",
        "label": "poss=12.6·pace, ppp = A1 rate / 12.6 (must equal A1)",
        "response": None,
        "overlay": {
            "matchup_mode": "point_additive_poss",
            "disable_clamp": True,
        },
        "role": "identity_check",
        "rationale": (
            "Possession-explicit rewrite of A1. Algebraically identical "
            "if poss=12.6·pace. 12.6 is the existing E4 scaffold, not a fit. "
            "If A4 ≠ A1, the implementation is wrong."
        ),
    },
)

TAIL_CUTS = (40.0, 45.0, 60.0, 65.0, 70.0)
PERCENTILES = (5, 10, 25, 50, 75, 90, 95)


def _stdev(xs: Sequence[float]) -> Optional[float]:
    if len(xs) < 2:
        return None
    return statistics.pstdev(xs)


def _rmse(xs: Sequence[float]) -> Optional[float]:
    if not xs:
        return None
    return math.sqrt(statistics.fmean([x * x for x in xs]))


def _percentile(xs: Sequence[float], p: float) -> Optional[float]:
    if not xs:
        return None
    ordered = sorted(float(v) for v in xs)
    idx = int(round((p / 100.0) * (len(ordered) - 1)))
    idx = min(len(ordered) - 1, max(0, idx))
    return ordered[idx]


def _freq(xs: Sequence[float], *, lt: Optional[float] = None, gt: Optional[float] = None) -> float:
    if not xs:
        return 0.0
    if lt is not None:
        return sum(1 for x in xs if x < lt) / len(xs)
    if gt is not None:
        return sum(1 for x in xs if x > gt) / len(xs)
    return 0.0


def distribution_card(values: Sequence[float]) -> Dict[str, Any]:
    xs = [float(v) for v in values]
    pcts = {f"p{p}": _percentile(xs, p) for p in PERCENTILES}
    return {
        "n": len(xs),
        "mean": _mean(xs),
        "sd": _stdev(xs),
        **pcts,
        "freq_lt40": _freq(xs, lt=40.0),
        "freq_lt45": _freq(xs, lt=45.0),
        "freq_gt60": _freq(xs, gt=60.0),
        "freq_gt65": _freq(xs, gt=65.0),
        "freq_gt70": _freq(xs, gt=70.0),
    }


def _region_cal(rows: Sequence[Mapping[str, Any]], pred: Sequence[float], actual: Sequence[float]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    specs = (
        ("pred_lt40", lambda p, _a: p < 40.0),
        ("pred_lt45", lambda p, _a: p < 45.0),
        ("pred_gt60", lambda p, _a: p > 60.0),
        ("pred_gt65", lambda p, _a: p > 65.0),
        ("pred_gt70", lambda p, _a: p > 70.0),
        ("actual_lt40", lambda _p, a: a < 40.0),
        ("actual_lt45", lambda _p, a: a < 45.0),
        ("actual_gt60", lambda _p, a: a > 60.0),
        ("actual_gt65", lambda _p, a: a > 65.0),
        ("actual_gt70", lambda _p, a: a > 70.0),
    )
    for name, pred_fn in specs:
        subset = [
            (p, a, r)
            for p, a, r in zip(pred, actual, rows)
            if pred_fn(p, a)
        ]
        if not subset:
            out[name] = {"n": 0}
            continue
        ps = [p for p, _a, _r in subset]
        als = [a for _p, a, _r in subset]
        res = [p - a for p, a in zip(ps, als)]
        out[name] = {
            "n": len(subset),
            "mean_pred": _mean(ps),
            "mean_actual": _mean(als),
            "bias": _mean(res),
            "mae": _mae(res),
        }
    return out


def _algebra_card(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    total_gaps: List[float] = []
    margin_gaps: List[float] = []
    missing = 0
    for r in rows:
        home = r.get("expected_home_score")
        away = r.get("expected_away_score")
        if home is None or away is None:
            missing += 1
            continue
        total_gaps.append(abs(float(home) + float(away) - float(r["model_total"])))
        margin_gaps.append(abs(float(away) - float(home) - float(r["model_spread_home"])))
    return {
        "n": len(rows),
        "missing_team_scores": missing,
        "max_abs_total_identity_gap": max(total_gaps) if total_gaps else None,
        "max_abs_margin_identity_gap": max(margin_gaps) if margin_gaps else None,
        "n_total_violations": sum(1 for g in total_gaps if g > ALGEBRA_TOL),
        "n_margin_violations": sum(1 for g in margin_gaps if g > ALGEBRA_TOL),
        "identity": "away+home=total and away-home=spread_home",
    }


def _team_score_card(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    home_pred: List[float] = []
    home_act: List[float] = []
    away_pred: List[float] = []
    away_act: List[float] = []
    for r in rows:
        eh = r.get("expected_home_score")
        ea = r.get("expected_away_score")
        if eh is None or ea is None:
            continue
        actual_home = 0.5 * (float(r["actual_total"]) + float(r["actual_margin"]))
        actual_away = 0.5 * (float(r["actual_total"]) - float(r["actual_margin"]))
        home_pred.append(float(eh))
        home_act.append(actual_home)
        away_pred.append(float(ea))
        away_act.append(actual_away)
    home_res = [p - a for p, a in zip(home_pred, home_act)]
    away_res = [p - a for p, a in zip(away_pred, away_act)]
    return {
        "n": len(home_pred),
        "home": {
            "mae": _mae(home_res),
            "rmse": _rmse(home_res),
            "bias": _mean(home_res),
            "sd_pred": _stdev(home_pred),
            "sd_actual": _stdev(home_act),
            "ols_residual_on_pred": _ols(home_pred, home_res),
        },
        "away": {
            "mae": _mae(away_res),
            "rmse": _rmse(away_res),
            "bias": _mean(away_res),
            "sd_pred": _stdev(away_pred),
            "sd_actual": _stdev(away_act),
            "ols_residual_on_pred": _ols(away_pred, away_res),
        },
    }


def distribution_compare(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    pred = [float(r["model_total"]) for r in rows]
    actual = [float(r["actual_total"]) for r in rows]
    pred_d = distribution_card(pred)
    act_d = distribution_card(actual)
    sd_p = pred_d.get("sd")
    sd_a = act_d.get("sd")
    sd_ratio = None if sd_p is None or not sd_a else sd_p / sd_a
    p90_gap = None
    p10_gap = None
    if pred_d.get("p90") is not None and act_d.get("p90") is not None:
        p90_gap = float(act_d["p90"]) - float(pred_d["p90"])
    if pred_d.get("p10") is not None and act_d.get("p10") is not None:
        p10_gap = float(pred_d["p10"]) - float(act_d["p10"])
    tail_ratio = None
    if act_d.get("freq_gt65"):
        tail_ratio = float(pred_d["freq_gt65"]) / float(act_d["freq_gt65"])
    elif pred_d.get("freq_gt65") == 0:
        tail_ratio = 0.0
    return {
        "predicted": pred_d,
        "actual": act_d,
        "sd_ratio_pred_over_actual": sd_ratio,
        "mean_gap_pred_minus_actual": (
            None
            if pred_d.get("mean") is None or act_d.get("mean") is None
            else float(pred_d["mean"]) - float(act_d["mean"])
        ),
        "p90_actual_minus_pred": p90_gap,
        "p10_pred_minus_actual": p10_gap,
        "freq_gt65_pred_over_actual": tail_ratio,
        "region_calibration": _region_cal(rows, pred, actual),
    }


def _eval_split(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    total_err = [float(r["err_total_vs_actual"]) for r in rows]
    spread_close = [float(r["err_spread_vs_close"]) for r in rows]
    margin_err = [float(r["err_margin_vs_actual"]) for r in rows]
    pred = [float(r["model_total"]) for r in rows]
    actual = [float(r["actual_total"]) for r in rows]
    proj = _bucket_card(rows, "model_total", PROJ_BUCKETS)
    return {
        "n": len(rows),
        "total_mae": _mae(total_err),
        "total_rmse": _rmse(total_err),
        "total_bias": _mean(total_err),
        "spread_mae_vs_close": _mae(spread_close),
        "spread_rmse_vs_close": _rmse(spread_close),
        "spread_bias_vs_close": _mean(spread_close),
        "spread_mae_vs_actual": _mae(margin_err),
        "spread_rmse_vs_actual": _rmse(margin_err),
        "spread_bias_vs_actual": _mean(margin_err),
        "favorite": _favorite_card(rows),
        "ols_residual_on_projected_total": _ols(pred, total_err),
        "ols_model_on_actual": _ols(actual, pred),
        "projected_total_buckets": proj,
        "projected_total_bias_range": _bias_range(proj),
        "actual_total_buckets": _bucket_card(rows, "actual_total", ACTUAL_BUCKETS),
        "distribution": distribution_compare(rows),
        "team_scores": _team_score_card(rows),
        "algebra": _algebra_card(rows),
        "clamped_home_n": sum(1 for r in rows if r.get("home_clamped")),
        "clamped_away_n": sum(1 for r in rows if r.get("away_clamped")),
        "high_tail_ge68_n": sum(1 for r in rows if float(r["model_total"]) >= 68.0),
    }


def _row_key(row: Mapping[str, Any]) -> Tuple[int, int, str, str]:
    return (int(row["season"]), int(row["week"]), str(row["home"]), str(row["away"]))


def compression_forensic(
    e3_rows: Sequence[Mapping[str, Any]],
    other_by_id: Mapping[str, Sequence[Mapping[str, Any]]],
) -> Dict[str, Any]:
    """Why did Val-1 ≥68 fall from 54 (E3) to 3 (C2)?"""
    e3_high = [r for r in e3_rows if float(r["model_total"]) >= 68.0]
    e3_actual_high = [r for r in e3_rows if float(r["actual_total"]) >= 68.0]
    e3_map = {_row_key(r): r for r in e3_rows}
    out: Dict[str, Any] = {
        "e3_pred_ge68_n": len(e3_high),
        "e3_actual_ge68_n": len(e3_actual_high),
        "e3_pred_ge68": {
            "mean_pred": _mean([float(r["model_total"]) for r in e3_high]),
            "mean_actual": _mean([float(r["actual_total"]) for r in e3_high]),
            "bias": _mean([float(r["err_total_vs_actual"]) for r in e3_high]),
            "distribution_pred": distribution_card([float(r["model_total"]) for r in e3_high]),
            "distribution_actual": distribution_card(
                [float(r["actual_total"]) for r in e3_high]
            ),
            "actual_ge68_n": sum(1 for r in e3_high if float(r["actual_total"]) >= 68.0),
            "actual_gt65_n": sum(1 for r in e3_high if float(r["actual_total"]) > 65.0),
        },
        "e3_actual_ge68": {
            "n": len(e3_actual_high),
            "mean_pred": _mean([float(r["model_total"]) for r in e3_actual_high]),
            "mean_actual": _mean([float(r["actual_total"]) for r in e3_actual_high]),
            "bias": _mean([float(r["err_total_vs_actual"]) for r in e3_actual_high]),
        },
        "by_model": {},
        "note": (
            "If E3's predicted-≥68 games actually scored near ~59 and C2/A1 "
            "project those same games near ~59, the missing tail is false "
            "amplification removed. If those games actually scored ~70 and "
            "C2/A1 sit near 55, the engine collapsed legitimate variance."
        ),
    }
    for mid, rows in other_by_id.items():
        mmap = {_row_key(r): r for r in rows}
        paired_high = []
        for r in e3_high:
            other = mmap.get(_row_key(r))
            if other is None:
                continue
            paired_high.append(
                {
                    "e3_pred": float(r["model_total"]),
                    "other_pred": float(other["model_total"]),
                    "actual": float(r["actual_total"]),
                }
            )
        paired_actual_high = []
        for r in e3_actual_high:
            other = mmap.get(_row_key(r))
            if other is None:
                continue
            paired_actual_high.append(
                {
                    "e3_pred": float(e3_map[_row_key(r)]["model_total"]),
                    "other_pred": float(other["model_total"]),
                    "actual": float(r["actual_total"]),
                }
            )
        model_high = [r for r in rows if float(r["model_total"]) >= 68.0]
        out["by_model"][mid] = {
            "own_pred_ge68_n": len(model_high),
            "own_pred_ge68_mean_pred": _mean(
                [float(r["model_total"]) for r in model_high]
            ),
            "own_pred_ge68_mean_actual": _mean(
                [float(r["actual_total"]) for r in model_high]
            ),
            "on_e3_pred_ge68": {
                "n": len(paired_high),
                "mean_e3_pred": _mean([p["e3_pred"] for p in paired_high]),
                "mean_other_pred": _mean([p["other_pred"] for p in paired_high]),
                "mean_actual": _mean([p["actual"] for p in paired_high]),
                "other_pred_ge68_n": sum(
                    1 for p in paired_high if p["other_pred"] >= 68.0
                ),
                "other_pred_distribution": distribution_card(
                    [p["other_pred"] for p in paired_high]
                ),
            },
            "on_e3_actual_ge68": {
                "n": len(paired_actual_high),
                "mean_e3_pred": _mean([p["e3_pred"] for p in paired_actual_high]),
                "mean_other_pred": _mean(
                    [p["other_pred"] for p in paired_actual_high]
                ),
                "mean_actual": _mean([p["actual"] for p in paired_actual_high]),
            },
        }
    return out


def score_candidate(
    spec: Mapping[str, Any],
    bundle: Mapping[str, Any],
    *,
    lake_only: bool,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    assert_frozen_priors()
    if abs(float(P.MATCHUP_RESPONSE) - FROZEN_BASELINE) > 1e-9:
        raise FrozenScoringError("production MATCHUP_RESPONSE drifted from 1.40")
    with overlay_matchup_response(spec.get("response")):
        with overlay_score_components(spec.get("overlay") or {}):
            if abs(float(P.MATCHUP_RESPONSE) - FROZEN_BASELINE) > 1e-9:
                raise FrozenScoringError("overlay mutated MATCHUP_RESPONSE")
            scored, skipped = score_joined_rows(
                bundle["joined"],
                bundle["universes"],
                lake_only=lake_only,
                with_components=True,
            )
    if abs(float(P.MATCHUP_RESPONSE) - FROZEN_BASELINE) > 1e-9:
        raise FrozenScoringError("overlay leaked after reset")
    summary = _enrich(summarize_scored(scored), scored)
    evals = {name: _eval_split(_split_rows(scored, name)) for name in PROTOCOL_SPLITS}
    payload = {
        "id": spec["id"],
        "family": spec["family"],
        "label": spec["label"],
        "role": spec.get("role"),
        "rationale": spec.get("rationale"),
        "response_overlay": spec.get("response"),
        "score_overlay": spec.get("overlay") or {},
        "production_matchup_response_still": P.MATCHUP_RESPONSE,
        "skipped": skipped,
        "n_scored": summary.get("n_scored"),
        "splits": {name: _card(summary, name) for name in PROTOCOL_SPLITS},
        "eval": evals,
        "by_season": {
            season: {
                "n": block.get("n"),
                "total_bias_vs_actual": block.get("total_vs_actual_bias"),
                "total_mae_vs_actual": block.get("total_vs_actual_mae"),
                "spread_mae_vs_close": block.get("spread_vs_close_mae"),
                "favorite_agree_vs_close": (block.get("favorite") or {}).get(
                    "favorite_agree_vs_close"
                ),
            }
            for season, block in (summary.get("by_season") or {}).items()
        },
    }
    return payload, scored


def _dispersion_notes(ev: Mapping[str, Any]) -> Tuple[bool, List[str]]:
    dist = ev.get("distribution") or {}
    notes: List[str] = []
    ok = True
    sd_ratio = dist.get("sd_ratio_pred_over_actual")
    if sd_ratio is None or float(sd_ratio) < DISPERSION_FLOOR - 1e-12:
        ok = False
        notes.append(f"sd_ratio {sd_ratio} (need ≥{DISPERSION_FLOOR})")
    else:
        notes.append(f"sd_ratio {sd_ratio:.3f}")
    tail = dist.get("freq_gt65_pred_over_actual")
    if tail is None or float(tail) < TAIL_GT65_RATIO_FLOOR - 1e-12:
        ok = False
        notes.append(f"freq>65 pred/actual {tail} (need ≥{TAIL_GT65_RATIO_FLOOR})")
    else:
        notes.append(f"freq>65 ratio {float(tail):.3f}")
    p90 = dist.get("p90_actual_minus_pred")
    if p90 is None or float(p90) > P90_UNDER_MAX + 1e-12:
        ok = False
        notes.append(f"actual P90 − pred P90 {p90} (need ≤{P90_UNDER_MAX})")
    else:
        notes.append(f"P90 gap {p90}")
    p10 = dist.get("p10_pred_minus_actual")
    if p10 is None or float(p10) > P10_OVER_MAX + 1e-12:
        ok = False
        notes.append(f"pred P10 − actual P10 {p10} (need ≤{P10_OVER_MAX})")
    else:
        notes.append(f"P10 gap {p10}")
    return ok, notes


def _shape_notes(
    rec: Mapping[str, Any],
    ref: Mapping[str, Any],
) -> Tuple[bool, List[str]]:
    notes: List[str] = []
    ok = True
    ref_range = (ref.get("eval") or {}).get("val_1", {}).get("projected_total_bias_range")
    ref_bias = (ref.get("eval") or {}).get("val_1", {}).get("total_bias")
    ref_fav = ((ref.get("eval") or {}).get("val_1", {}).get("favorite") or {}).get(
        "favorite_agree_vs_close"
    )
    v1 = (rec.get("eval") or {}).get("val_1") or {}
    rng = v1.get("projected_total_bias_range")
    bias = v1.get("total_bias")
    fav = (v1.get("favorite") or {}).get("favorite_agree_vs_close")
    if ref_range is None or rng is None or (ref_range - rng) < RANGE_DROP - 1e-12:
        ok = False
        notes.append(f"Val-1 range {rng} vs E3 {ref_range} (need drop ≥{RANGE_DROP})")
    else:
        notes.append(f"Val-1 range {rng} vs E3 {ref_range}")
    if bias is None or abs(float(bias)) > BIAS_ABS_OK:
        ok = False
        notes.append(f"Val-1 |bias| {bias} (need ≤{BIAS_ABS_OK})")
    else:
        notes.append(f"Val-1 bias {bias}")
    if ref_fav is None or fav is None or (float(ref_fav) - float(fav)) > FAV_DROP_OK:
        ok = False
        notes.append(f"Val-1 fav-agree {fav} vs E3 {ref_fav}")
    else:
        notes.append(f"Val-1 fav-agree {fav}")
    for split in ("train_0", "val_0"):
        ref_r = (ref.get("eval") or {}).get(split, {}).get("projected_total_bias_range")
        this_r = (rec.get("eval") or {}).get(split, {}).get("projected_total_bias_range")
        if ref_r is None or this_r is None or this_r >= ref_r - 1e-12:
            ok = False
            notes.append(f"{split} range did not improve ({this_r} vs {ref_r})")
        else:
            notes.append(f"{split} range {this_r} vs E3 {ref_r}")
    return ok, notes


def decide(
    records: Sequence[Mapping[str, Any]],
    *,
    a1_a4_ok: Optional[bool],
) -> Dict[str, Any]:
    by_id = {r["id"]: r for r in records}
    ref = by_id.get("E3_ref")
    if ref is None:
        return {
            "decision": "INSUFFICIENT_EVIDENCE_DO_NOT_SHIP",
            "ship": False,
            "winner": None,
            "sealed_2025_candidates": [],
            "why": ["E3 reference missing"],
        }
    why: List[str] = [
        "C2 is architectural evidence, not a coefficient. Do not fit 0.5/0.5.",
        "No production write. Board stays OFF. 2025 stays sealed.",
        "A candidate does not pass merely because MAE/bias improve.",
        "Distributional calibration is required (anti-variance-collapse).",
    ]
    if a1_a4_ok is False:
        why.append("A4 did not match A1 — point-space identity is broken.")
        return {
            "decision": "IMPLEMENTATION_INCONSISTENT_DO_NOT_SHIP",
            "ship": False,
            "winner": None,
            "sealed_2025_candidates": [],
            "why": why,
        }
    if a1_a4_ok:
        why.append("A4 equals A1 within tolerance (possession rewrite is identical).")

    shape_pass: List[str] = []
    dispersion_pass: List[str] = []
    both_pass: List[str] = []
    collapse: List[str] = []
    for rec in records:
        if rec.get("role") != "candidate":
            continue
        s_ok, s_notes = _shape_notes(rec, ref)
        why.append(f"{rec['id']} shape: " + "; ".join(s_notes))
        d_ok = True
        for split in PROTOCOL_SPLITS:
            ok, notes = _dispersion_notes((rec.get("eval") or {}).get(split) or {})
            why.append(f"{rec['id']} {split} dispersion: " + "; ".join(notes))
            if not ok:
                d_ok = False
        if s_ok:
            shape_pass.append(rec["id"])
        if d_ok:
            dispersion_pass.append(rec["id"])
        if s_ok and d_ok:
            both_pass.append(rec["id"])
        elif s_ok and not d_ok:
            collapse.append(rec["id"])

    if both_pass:
        return {
            "decision": "CANDIDATE_FOR_SEALED_2025",
            "ship": False,
            "winner": None,
            "sealed_2025_candidates": both_pass,
            "shape_pass": shape_pass,
            "dispersion_pass": dispersion_pass,
            "variance_collapse": collapse,
            "why": [
                "Architecture survived Train-0 / Val-0 / Val-1 on shape and "
                "dispersion. Not a production winner. 2025 stays sealed "
                "until explicit approval.",
                *why,
            ],
        }
    if collapse:
        return {
            "decision": "VARIANCE_COLLAPSE_DO_NOT_PROMOTE",
            "ship": False,
            "winner": None,
            "sealed_2025_candidates": [],
            "shape_pass": shape_pass,
            "dispersion_pass": dispersion_pass,
            "variance_collapse": collapse,
            "why": [
                "Shape improved but predicted variance/tails collapsed "
                "relative to actual football. Do not promote a model that "
                "looks calibrated by predicting everything near 52–55.",
                *why,
            ],
        }
    return {
        "decision": "NO_CANDIDATE_DO_NOT_SHIP",
        "ship": False,
        "winner": None,
        "sealed_2025_candidates": [],
        "shape_pass": shape_pass,
        "dispersion_pass": dispersion_pass,
        "variance_collapse": collapse,
        "why": [
            "No predeclared candidate flattened the residual function "
            "while keeping legitimate projection variance.",
            *why,
        ],
    }


def _a1_a4_identity(
    a1_rows: Sequence[Mapping[str, Any]],
    a4_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    a1_map = {_row_key(r): r for r in a1_rows}
    diffs: List[float] = []
    missing = 0
    for r in a4_rows:
        other = a1_map.get(_row_key(r))
        if other is None:
            missing += 1
            continue
        diffs.append(abs(float(r["model_total"]) - float(other["model_total"])))
    max_abs = max(diffs) if diffs else None
    return {
        "n_paired": len(diffs),
        "missing": missing,
        "max_abs_total_diff": max_abs,
        "mean_abs_total_diff": _mean(diffs),
        "ok": max_abs is not None and max_abs <= A1_A4_MAX_ABS_DIFF and missing == 0,
    }


def run_additive_scoring_architecture(
    *,
    cache_dir=None,
    lake_only: bool = True,
) -> Dict[str, Any]:
    assert_frozen_priors()
    refuse_sealed_or_confirm(LEGAL_SEASONS)
    if QB_FEATURE_CONTRACT_VERSION != "cfb-qb-feature-v1":
        raise FrozenScoringError("qb feature contract drifted")
    if CFB_EDGE_BOARD_PUBLIC_ENABLED:
        raise FrozenScoringError("public board kill switch must stay off")

    bundle = load_legal_scoring_bundle(cache_dir=cache_dir, lake_only=lake_only)
    lake_mounted = all(
        (bundle.get("lake_locate") or {}).get(str(season), {}).get("mounted")
        for season in LEGAL_SEASONS
    )
    records: List[Dict[str, Any]] = []
    scored_by_id: Dict[str, List[Dict[str, Any]]] = {}
    if lake_mounted:
        for spec in CANDIDATES:
            rec, scored = score_candidate(spec, bundle, lake_only=lake_only)
            records.append(rec)
            scored_by_id[spec["id"]] = scored

    identity = None
    forensic = None
    if lake_mounted and "A1_point_half" in scored_by_id and "A4_point_poss" in scored_by_id:
        identity = _a1_a4_identity(
            scored_by_id["A1_point_half"], scored_by_id["A4_point_poss"]
        )
    if lake_mounted and "E3_ref" in scored_by_id:
        e3_val = _split_rows(scored_by_id["E3_ref"], "val_1")
        others = {
            mid: _split_rows(rows, "val_1")
            for mid, rows in scored_by_id.items()
            if mid != "E3_ref"
        }
        forensic = compression_forensic(e3_val, others)

    gate = (
        decide(records, a1_a4_ok=None if identity is None else bool(identity.get("ok")))
        if lake_mounted
        else {
            "decision": "INSUFFICIENT_EVIDENCE_DO_NOT_SHIP",
            "ship": False,
            "winner": None,
            "sealed_2025_candidates": [],
            "why": ["odds lake not mounted"],
        }
    )
    return {
        "role": "additive_scoring_architecture",
        "do_not_tune": True,
        "do_not_subtract_10": True,
        "do_not_fit_c2_weights": True,
        "kill_switch": "OFF",
        "merge_532": False,
        "used_2026_for_fitting": False,
        "opened_2025": False,
        "wrote_production_coefficient": False,
        "qb_feature_contract_version": QB_FEATURE_CONTRACT_VERSION,
        "matchup_response_frozen": P.MATCHUP_RESPONSE,
        "league_team_ppg_frozen": P.LEAGUE_TEAM_PPG,
        "engine_version": P.ENGINE_VERSION,
        "protocol_splits": PROTOCOL_SPLITS,
        "equation": {
            "form": (
                "E[pts_i] = pace * (μ + α(Off_i − 50) + β(50 − Def_j)) "
                "[* units] + HFA_i + coach_i"
            ),
            "total": "E[home] + E[away]",
            "spread_home": "E[away] − E[home]",
            "mu": P.LEAGUE_TEAM_PPG,
            "center": 50.0,
            "alpha_half": HALF_INDEX_SLOPE,
            "alpha_full": FULL_INDEX_SLOPE,
            "alpha_equals_beta": True,
            "league_team_possessions": LEAGUE_TEAM_POSSESSIONS,
            "justification": {
                "mu": "Documented LEAGUE_TEAM_PPG. Scoring level, not a residual intercept.",
                "center": "Documented 0–100 efficiency center. Empirically ~50.6/51.2 on Val-1.",
                "alpha_equals_beta": (
                    "Offense and defense share the packaged 0–100 scale "
                    "and SCORE_TO_INDEX_DIVISOR=68. Symmetry, not a fit."
                ),
                "alpha_half": (
                    "25.9/136: each axis owns half of one linearized index "
                    "unit. Giving both axes 25.9/68 is C3 and double-counts."
                ),
                "pace": "Scales possessions of the whole scoring rate, not a secret product on the mismatch only.",
                "units": "A1 off (C1: units were not the E3 slope). A2 tests putting them back on the rate.",
                "possessions": "12.6 is the existing E4 scaffold. A4 must equal A1.",
            },
        },
        "predeclared_candidates": [
            {
                "id": c["id"],
                "label": c["label"],
                "role": c["role"],
                "rationale": c["rationale"],
                "overlay": c["overlay"],
            }
            for c in CANDIDATES
        ],
        "gates": {
            "val1_range_drop": RANGE_DROP,
            "val1_abs_bias_max": BIAS_ABS_OK,
            "val1_fav_drop_max": FAV_DROP_OK,
            "dispersion_floor": DISPERSION_FLOOR,
            "tail_gt65_ratio_floor": TAIL_GT65_RATIO_FLOOR,
            "p90_under_max": P90_UNDER_MAX,
            "p10_over_max": P10_OVER_MAX,
            "min_bucket_n": MIN_BUCKET_N,
            "a1_a4_max_abs_diff": A1_A4_MAX_ABS_DIFF,
        },
        "lake_mounted": lake_mounted,
        "a1_a4_identity": identity,
        "c2_compression_forensic": forensic,
        "candidates": records,
        "decision": gate,
        "reconstruction_limits": [
            "v1 universe: Layer A QB + prior-year efficiency + league-avg roster.",
            "C2 remains a product form. A1 writes the same half-slope in point space.",
            "α/β are documented index identities, not Train-0 or Val-1 fits.",
            "2025 sealed. 2026 W2 n=47 is not in this loss.",
        ],
    }
