"""Raw O/D interaction specification. Research only.

E3 is the lead architecture, not a production coefficient. This module
diagnoses why E3 residuals stay sloped and scores **predeclared**
replacement identities on the same frozen splits.

Do not fit k, subtract a constant, apply bucket corrections, isotonic
maps, splines, or market anchoring. Actual scores are the objective.
2025 sealed. 2026 not in the loss. Production MATCHUP_RESPONSE stays 1.40.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
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

# ---------------------------------------------------------------------------
# Predeclared candidates. This list is the spec. Do not append after scoring.
# ---------------------------------------------------------------------------
#
# E3 (reference):
#   pts = 25.9 * (eff_idx(off) / eff_idx(def)) * units * pace + HFA + coach
#   eff_idx(x) = clamp(1 + (x − 50) / 68)
# Football: raw efficiency should drive the matchup, not composed indexes.
# Known failure: mean bias is almost gone; residual vs projected total is
# still ~−8 (low) to ~+13 (high).
#
# C1 e3_no_leak:
#   same E3 identity, units forced to 1, pace forced to 1.
# Tests whether explosiveness→pace or unit boosts still steepen the tails.
#
# C2 raw_additive:
#   pts = 25.9 * (0.5*off_idx + 0.5*(2 − def_idx)) * units * pace + adders
# Football: offense quality and opponent defense quality add, they do not
# multiply. Extreme mismatches grow linearly instead of as a product.
#
# C3 raw_diff:
#   pts = 25.9 * (1 + (off_eff − def_eff) / 68) * units * pace + adders
# Football: first-order (off − def) in the documented 0–100 scale. No
# ratio, no exponent. Slope 25.9/68 is the existing index identity, not a fit.
#
# C4 raw_sat:
#   pts = 25.9 * (1 + tanh(ratio − 1)) * units * pace + adders
#   ratio = eff_idx(off) / eff_idx(def)
# Football: clock, finishing, and FG/TD conversion saturate. tanh is a
# predeclared squash, not a fitted spline.
#
# Flatten gate (predeclared, not tuned after seeing scores):
#   Val-1 projected-total bucket bias range drops ≥ 8 vs E3
#   AND |Val-1 mean bias| ≤ 3
#   AND favorite-agree vs close does not fall more than 0.03 vs E3
#   AND Train-0 / Val-0 move in the same direction on the range
# If the gate fails: NO_WINNER. Nothing is shipped either way.

CANDIDATES: Tuple[Dict[str, Any], ...] = (
    {
        "id": "E3_raw_efficiency_r1",
        "family": "E3_reference",
        "label": "E3 raw off_eff/def_eff ratio ** 1.00",
        "response": 1.00,
        "overlay": {"matchup_mode": "raw_efficiency"},
        "rationale": (
            "Lead architecture from the E1–E5 holdout. Mean bias collapsed; "
            "shape did not."
        ),
    },
    {
        "id": "C1_e3_no_leak",
        "family": "leak_control",
        "label": "E3 with units=1 and pace=1 (composed leak off)",
        "response": 1.00,
        "overlay": {
            "matchup_mode": "raw_efficiency",
            "force_unit_identity": True,
            "force_pace_one": True,
        },
        "rationale": (
            "On the v1 universe units are already ~50. Pace still carries "
            "explosiveness. If the slope dies here, leftover compose is the "
            "shape problem. If it survives, the raw ratio→points map is."
        ),
    },
    {
        "id": "C2_raw_additive",
        "family": "raw_od",
        "label": "additive 0.5*off_idx + 0.5*(2−def_idx)",
        "response": None,
        "overlay": {"matchup_mode": "raw_additive"},
        "rationale": (
            "Offense and opponent defense contribute separately. Product "
            "explosion on high-off / low-def games is the suspected slope."
        ),
    },
    {
        "id": "C3_raw_diff",
        "family": "raw_od",
        "label": "linear (off_eff − def_eff) / 68",
        "response": None,
        "overlay": {"matchup_mode": "raw_diff"},
        "rationale": (
            "First-order Taylor of the ratio around 50/50, written in the "
            "raw 0–100 scale. No index ratio, no exponent."
        ),
    },
    {
        "id": "C4_raw_sat",
        "family": "raw_od",
        "label": "1 + tanh(raw-eff ratio − 1)",
        "response": None,
        "overlay": {"matchup_mode": "raw_sat"},
        "rationale": (
            "Saturating matchup: clock and finishing bound how far an "
            "efficiency mismatch can push scoring. tanh is predeclared."
        ),
    },
)

PROJ_BUCKETS = (
    ("lt_48", 0.0, 48.0),
    ("48_54", 48.0, 54.0),
    ("54_60", 54.0, 60.0),
    ("60_68", 60.0, 68.0),
    ("ge_68", 68.0, None),
)
ACTUAL_BUCKETS = (
    ("lt_45", 0.0, 45.0),
    ("45_52", 45.0, 52.0),
    ("52_60", 52.0, 60.0),
    ("60_70", 60.0, 70.0),
    ("ge_70", 70.0, None),
)
SPREAD_BUCKETS = (
    ("pick_3", 0.0, 3.0),
    ("3_7", 3.0, 7.0),
    ("7_14", 7.0, 14.0),
    ("ge_14", 14.0, None),
)
RANGE_DROP = 8.0
BIAS_ABS_OK = 3.0
FAV_DROP_OK = 0.03
MIN_BUCKET_N = 15


def _mean(xs: Sequence[float]) -> Optional[float]:
    return statistics.fmean(xs) if xs else None


def _mae(xs: Sequence[float]) -> Optional[float]:
    return _mean([abs(x) for x in xs])


def _ols(xs: Sequence[float], ys: Sequence[float]) -> Dict[str, Any]:
    if len(xs) < 8:
        return {"n": len(xs)}
    mx = statistics.fmean(xs)
    my = statistics.fmean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    syy = sum((y - my) ** 2 for y in ys)
    slope = sxy / sxx if sxx else float("nan")
    intercept = my - slope * mx
    r2 = 1.0 - (sum((y - intercept - slope * x) ** 2 for x, y in zip(xs, ys)) / syy) if syy else float("nan")
    return {
        "n": len(xs),
        "slope": round(slope, 4),
        "intercept": round(intercept, 4),
        "r2": round(r2, 4),
        "mean_x": round(mx, 3),
        "mean_y": round(my, 3),
    }


def _in_bucket(value: float, lo: float, hi: Optional[float]) -> bool:
    if hi is None:
        return value >= lo
    return lo <= value < hi


def _tertile_labels(values: Sequence[float]) -> List[str]:
    ordered = sorted(float(v) for v in values)
    if not ordered:
        return []
    q1 = ordered[max(0, len(ordered) // 3 - 1)]
    q2 = ordered[max(0, (2 * len(ordered)) // 3 - 1)]

    def _lab(v: float) -> str:
        if v <= q1:
            return "lo"
        if v <= q2:
            return "mid"
        return "hi"

    return [_lab(float(v)) for v in values]


def _bucket_card(
    rows: Sequence[Mapping[str, Any]],
    key: str,
    spec: Sequence[Tuple[str, float, Optional[float]]],
) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for name, lo, hi in spec:
        subset = [r for r in rows if _in_bucket(float(r[key]), lo, hi)]
        res = [float(r["err_total_vs_actual"]) for r in subset]
        out[name] = {
            "n": len(subset),
            "bias": _mean(res),
            "mae": _mae(res),
            "mean_model": _mean([float(r["model_total"]) for r in subset]),
            "mean_actual": _mean([float(r["actual_total"]) for r in subset]),
        }
    return out


def _group_card(rows: Sequence[Mapping[str, Any]], labels: Sequence[str]) -> Dict[str, Any]:
    buckets: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row, lab in zip(rows, labels):
        buckets[lab].append(row)
    out: Dict[str, Any] = {}
    for name, subset in sorted(buckets.items()):
        res = [float(r["err_total_vs_actual"]) for r in subset]
        out[name] = {
            "n": len(subset),
            "bias": _mean(res),
            "mae": _mae(res),
            "mean_model": _mean([float(r["model_total"]) for r in subset]),
            "mean_actual": _mean([float(r["actual_total"]) for r in subset]),
        }
    return out


def _bias_range(bucket_card: Mapping[str, Any]) -> Optional[float]:
    vals = [
        float(row["bias"])
        for row in bucket_card.values()
        if row.get("bias") is not None and int(row.get("n") or 0) >= MIN_BUCKET_N
    ]
    if len(vals) < 2:
        return None
    return max(vals) - min(vals)


def _scale_diag(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    def _col(name: str) -> List[float]:
        return [float(r[name]) for r in rows if r.get(name) is not None]

    home_off = _col("home_off_eff")
    away_off = _col("away_off_eff")
    home_def = _col("home_def_eff")
    away_def = _col("away_def_eff")
    offs = home_off + away_off
    defs = home_def + away_def
    ratios = []
    for r in rows:
        if r.get("home_ratio_raw") is None or r.get("away_ratio_raw") is None:
            continue
        ratios.append(0.5 * (float(r["home_ratio_raw"]) + float(r["away_ratio_raw"])))
    composed_off = _col("home_off_idx") + _col("away_off_idx")
    composed_def = _col("home_def_idx") + _col("away_def_idx")
    return {
        "n": len(rows),
        "mean_off_eff": _mean(offs),
        "mean_def_eff": _mean(defs),
        "p10_off_eff": sorted(offs)[max(0, int(0.1 * (len(offs) - 1)))] if offs else None,
        "p90_off_eff": sorted(offs)[int(0.9 * (len(offs) - 1))] if offs else None,
        "p10_def_eff": sorted(defs)[max(0, int(0.1 * (len(defs) - 1)))] if defs else None,
        "p90_def_eff": sorted(defs)[int(0.9 * (len(defs) - 1))] if defs else None,
        "mean_raw_ratio": _mean(ratios),
        "mean_composed_off_idx": _mean(composed_off),
        "mean_composed_def_idx": _mean(composed_def),
        "mean_composed_off_minus_def": (
            None
            if not composed_off or not composed_def
            else statistics.fmean(composed_off) - statistics.fmean(composed_def)
        ),
        "league_ppg_times_two": 2.0 * P.LEAGUE_TEAM_PPG,
        "note": (
            "If mean off_eff and def_eff sit near 50, the E3 intercept "
            "should be near 2×25.9 plus HFA. A sloped residual with a "
            "centered scale is a transformation problem, not a baseline."
        ),
    }


def attribute_e3(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Component / segment ledger for the E3 reference on one split."""
    if not rows:
        return {"n": 0}
    res = [float(r["err_total_vs_actual"]) for r in rows]
    pred = [float(r["model_total"]) for r in rows]
    actual = [float(r["actual_total"]) for r in rows]
    mean_off = []
    mean_def = []
    mismatch = []
    pace = []
    for r in rows:
        ho = r.get("home_off_eff")
        ao = r.get("away_off_eff")
        hd = r.get("home_def_eff")
        ad = r.get("away_def_eff")
        if None not in (ho, ao, hd, ad):
            mo = 0.5 * (float(ho) + float(ao))
            md = 0.5 * (float(hd) + float(ad))
            mean_off.append(mo)
            mean_def.append(md)
            mismatch.append(abs(mo - md))
        if r.get("home_pace_used") is not None:
            pace.append(float(r["home_pace_used"]))
    off_labs = _tertile_labels(mean_off) if mean_off else []
    def_labs = _tertile_labels(mean_def) if mean_def else []
    interact = [f"off_{o}__def_{d}" for o, d in zip(off_labs, def_labs)]
    mismatch_labs = _tertile_labels(mismatch) if mismatch else []
    pace_labs = _tertile_labels(pace) if pace else []
    strength = []
    for r in rows:
        if r.get("home_off_idx") is None:
            continue
        strength.append(
            0.25
            * (
                float(r["home_off_idx"])
                + float(r["home_def_idx"])
                + float(r["away_off_idx"])
                + float(r["away_def_idx"])
            )
        )
    strength_labs = _tertile_labels(strength) if strength else []
    proj_buckets = _bucket_card(rows, "model_total", PROJ_BUCKETS)
    return {
        "n": len(rows),
        "mean_residual": _mean(res),
        "mae": _mae(res),
        "ols_residual_on_projected_total": _ols(pred, res),
        "ols_residual_on_actual_total": _ols(actual, res),
        "ols_model_on_actual": _ols(actual, pred),
        "scale": _scale_diag(rows),
        "projected_total_buckets": proj_buckets,
        "projected_total_bias_range": _bias_range(proj_buckets),
        "actual_total_buckets": _bucket_card(rows, "actual_total", ACTUAL_BUCKETS),
        "spread_magnitude_buckets": _bucket_card(
            rows, "abs_disagree_spread", SPREAD_BUCKETS
        ),
        "close_spread_abs_buckets": _bucket_card(
            [
                {**r, "abs_close_spread": abs(float(r["close_spread_home"]))}
                for r in rows
            ],
            "abs_close_spread",
            SPREAD_BUCKETS,
        ),
        "home_favorite": {
            "True": _group_card(
                [r for r in rows if r.get("favorite_home")],
                ["home_favorite"] * sum(1 for r in rows if r.get("favorite_home")),
            ).get("home_favorite"),
            "False": _group_card(
                [r for r in rows if not r.get("favorite_home")],
                ["home_dog"] * sum(1 for r in rows if not r.get("favorite_home")),
            ).get("home_dog"),
        },
        "raw_off_tertile": _group_card(rows[: len(off_labs)], off_labs),
        "raw_def_tertile": _group_card(rows[: len(def_labs)], def_labs),
        "od_interaction": _group_card(rows[: len(interact)], interact),
        "od_mismatch_tertile": _group_card(rows[: len(mismatch_labs)], mismatch_labs),
        "pace_tertile": _group_card(rows[: len(pace_labs)], pace_labs),
        "composed_strength_tertile": _group_card(
            rows[: len(strength_labs)], strength_labs
        ),
        "favorite": _favorite_card(rows),
        "clamped_home_n": sum(1 for r in rows if r.get("home_clamped")),
        "clamped_away_n": sum(1 for r in rows if r.get("away_clamped")),
    }


def _shape_card(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    proj = _bucket_card(rows, "model_total", PROJ_BUCKETS)
    res = [float(r["err_total_vs_actual"]) for r in rows]
    pred = [float(r["model_total"]) for r in rows]
    return {
        "projected_total_buckets": proj,
        "projected_total_bias_range": _bias_range(proj),
        "ols_residual_on_projected_total": _ols(pred, res),
        "favorite": _favorite_card(rows),
    }


def score_candidate(
    spec: Mapping[str, Any],
    bundle: Mapping[str, Any],
    *,
    lake_only: bool,
    with_components: bool,
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
                with_components=with_components,
            )
    if abs(float(P.MATCHUP_RESPONSE) - FROZEN_BASELINE) > 1e-9:
        raise FrozenScoringError("overlay leaked after reset")
    summary = _enrich(summarize_scored(scored), scored)
    payload = {
        "id": spec["id"],
        "family": spec["family"],
        "label": spec["label"],
        "rationale": spec.get("rationale"),
        "response_overlay": spec.get("response"),
        "score_overlay": spec.get("overlay") or {},
        "production_matchup_response_still": P.MATCHUP_RESPONSE,
        "skipped": skipped,
        "n_scored": summary.get("n_scored"),
        "splits": {name: _card(summary, name) for name in PROTOCOL_SPLITS},
        "shape": {
            name: _shape_card(_split_rows(scored, name)) for name in PROTOCOL_SPLITS
        },
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


def decide(records: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    by_id = {r["id"]: r for r in records}
    ref = by_id.get("E3_raw_efficiency_r1")
    if ref is None:
        return {
            "decision": "INSUFFICIENT_EVIDENCE_DO_NOT_SHIP",
            "ship": False,
            "winner": None,
            "why": ["E3 reference missing"],
        }
    ref_range = (ref.get("shape") or {}).get("val_1", {}).get("projected_total_bias_range")
    ref_bias = (ref.get("splits") or {}).get("val_1", {}).get("total_bias_vs_actual")
    ref_fav = (ref.get("splits") or {}).get("val_1", {}).get("favorite_agree_vs_close")
    why: List[str] = [
        "No coefficient search. No −10. No bucket correction. No isotonic.",
        "Market close is diagnostic. Actual scores are the objective.",
        f"E3 Val-1 bias={ref_bias} range={ref_range} fav-agree={ref_fav}",
    ]
    passed: List[str] = []
    for rec in records:
        if rec["id"] == "E3_raw_efficiency_r1":
            continue
        v1 = (rec.get("splits") or {}).get("val_1") or {}
        s1 = (rec.get("shape") or {}).get("val_1") or {}
        s0 = (rec.get("shape") or {}).get("val_0") or {}
        st = (rec.get("shape") or {}).get("train_0") or {}
        rng = s1.get("projected_total_bias_range")
        bias = v1.get("total_bias_vs_actual")
        fav = v1.get("favorite_agree_vs_close")
        notes = []
        ok = True
        if ref_range is None or rng is None or (ref_range - rng) < RANGE_DROP - 1e-12:
            ok = False
            notes.append(
                f"Val-1 range {rng} vs E3 {ref_range} (need drop ≥{RANGE_DROP})"
            )
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
        ref_v0 = (ref.get("shape") or {}).get("val_0", {}).get("projected_total_bias_range")
        ref_tr = (ref.get("shape") or {}).get("train_0", {}).get("projected_total_bias_range")
        v0r = s0.get("projected_total_bias_range")
        tr = st.get("projected_total_bias_range")
        if ref_v0 is None or v0r is None or v0r >= ref_v0 - 1e-12:
            ok = False
            notes.append(f"Val-0 range did not improve ({v0r} vs {ref_v0})")
        if ref_tr is None or tr is None or tr >= ref_tr - 1e-12:
            ok = False
            notes.append(f"Train-0 range did not improve ({tr} vs {ref_tr})")
        why.append(f"{rec['id']}: " + "; ".join(notes))
        if ok:
            passed.append(rec["id"])
    if passed:
        return {
            "decision": "SHAPE_IMPROVED_DO_NOT_SHIP",
            "ship": False,
            "winner": None,
            "passed_flatten_gate": passed,
            "why": [
                "Flatten gate passed on holdout, but this is still a research identity.",
                "Do not write production constants. Board stays OFF.",
                *why,
            ],
        }
    return {
        "decision": "NO_WINNER_DO_NOT_SHIP",
        "ship": False,
        "winner": None,
        "passed_flatten_gate": [],
        "why": [
            "No predeclared candidate flattened the residual shape out of sample.",
            "E3 remains the lead architecture, not a production coefficient.",
            *why,
        ],
    }


def run_raw_od_interaction(
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
    e3_attr: Dict[str, Any] = {}
    if lake_mounted:
        for spec in CANDIDATES:
            rec, scored = score_candidate(
                spec,
                bundle,
                lake_only=lake_only,
                with_components=spec["id"] == "E3_raw_efficiency_r1",
            )
            if spec["id"] == "E3_raw_efficiency_r1":
                e3_attr = {
                    name: attribute_e3(_split_rows(scored, name))
                    for name in PROTOCOL_SPLITS
                }
            records.append(rec)
    gate = (
        decide(records)
        if lake_mounted
        else {
            "decision": "INSUFFICIENT_EVIDENCE_DO_NOT_SHIP",
            "ship": False,
            "winner": None,
            "why": ["odds lake not mounted"],
        }
    )
    return {
        "role": "raw_od_interaction_spec",
        "do_not_tune": True,
        "do_not_subtract_10": True,
        "kill_switch": "OFF",
        "merge_532": False,
        "used_2026_for_fitting": False,
        "opened_2025": False,
        "wrote_production_coefficient": False,
        "qb_feature_contract_version": QB_FEATURE_CONTRACT_VERSION,
        "matchup_response_frozen": P.MATCHUP_RESPONSE,
        "engine_version": P.ENGINE_VERSION,
        "protocol_splits": PROTOCOL_SPLITS,
        "predeclared_candidates": [
            {
                "id": c["id"],
                "label": c["label"],
                "rationale": c["rationale"],
                "overlay": c["overlay"],
            }
            for c in CANDIDATES
        ],
        "flatten_gate": {
            "val1_range_drop": RANGE_DROP,
            "val1_abs_bias_max": BIAS_ABS_OK,
            "val1_fav_drop_max": FAV_DROP_OK,
            "min_bucket_n": MIN_BUCKET_N,
        },
        "lake_mounted": lake_mounted,
        "e3_residual_attribution": e3_attr,
        "candidates": records,
        "decision": gate,
        "reconstruction_limits": [
            "v1 universe: Layer A QB + prior-year efficiency + league-avg roster.",
            "E3 still uses SCORE_TO_INDEX_DIVISOR=68 and LEAGUE_TEAM_PPG=25.9.",
            "C3 uses 25.9/68 as the documented index identity, not a Train-0 fit.",
            "C4 tanh is a predeclared squash, not a fitted spline.",
            "2025 sealed. 2026 W2 n=47 is not in this loss.",
        ],
    }
