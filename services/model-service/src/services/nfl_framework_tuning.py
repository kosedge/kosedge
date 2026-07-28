from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import product
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.services.nfl_handicapping_framework import evaluate_nfl_edge_guardrails


def _safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _safe_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def _logit(prob: float) -> float:
    p = _clamp(prob, 0.001, 0.999)
    return math.log(p / (1.0 - p))


def _american_implied_prob(odds: Optional[float]) -> Optional[float]:
    if odds is None:
        return None
    try:
        value = float(odds)
    except (TypeError, ValueError):
        return None
    if value == 0:
        return None
    if value > 0:
        return 100.0 / (value + 100.0)
    return abs(value) / (abs(value) + 100.0)


def _market_home_prob_no_vig(home_odds: Optional[float], away_odds: Optional[float]) -> Optional[float]:
    p_home = _american_implied_prob(home_odds)
    p_away = _american_implied_prob(away_odds)
    if p_home is None or p_away is None:
        return None
    denom = p_home + p_away
    if denom <= 0:
        return None
    return p_home / denom


@dataclass(frozen=True)
class TuningThresholds:
    min_fold_count: int = 2
    min_sample_size: int = 30
    min_recommendations: int = 12
    min_coverage: float = 0.08
    max_coverage: float = 0.80
    target_coverage: float = 0.32


def build_tuning_candidates(
    *,
    base_guardrails: Dict[str, Any],
    max_candidates: int = 180,
) -> List[Dict[str, Any]]:
    weight_grid = {
        "base_efficiency_margin_scale": [0.92, 1.0, 1.08],
        "base_efficiency_total_scale": [0.92, 1.0, 1.08],
        "injuries_margin_scale": [0.9, 1.0, 1.1],
        "injuries_total_scale": [0.9, 1.0, 1.1],
        "regression_margin_scale": [0.9, 1.0, 1.1],
    }
    guardrail_grid = {
        "min_ml_edge_prob": [0.0075, 0.01, 0.0125],
        "min_confidence_score": [0.5, 0.53, 0.56],
        "max_uncertainty_penalty": [0.26, 0.33, 0.38],
        "min_factor_coverage": [0.5, 0.6, 0.7],
    }
    weight_keys = sorted(weight_grid.keys())
    guardrail_keys = sorted(guardrail_grid.keys())
    all_candidates: List[Dict[str, Any]] = []
    for weight_vals in product(*(weight_grid[k] for k in weight_keys)):
        for guard_vals in product(*(guardrail_grid[k] for k in guardrail_keys)):
            weight_scales = {k: float(v) for k, v in zip(weight_keys, weight_vals)}
            guardrails = {
                "min_quality_score": float(base_guardrails.get("min_quality_score", 58.0)),
                "max_injury_freshness_hours": float(base_guardrails.get("max_injury_freshness_hours", 72.0)),
                **{k: float(v) for k, v in zip(guardrail_keys, guard_vals)},
            }
            all_candidates.append({"weight_scales": weight_scales, "guardrails": guardrails})

    if len(all_candidates) <= max_candidates:
        return all_candidates

    step = len(all_candidates) / float(max_candidates)
    sampled: List[Dict[str, Any]] = []
    seen: set[int] = set()
    for i in range(max_candidates):
        idx = int(round(i * step))
        idx = min(len(all_candidates) - 1, idx)
        if idx in seen:
            continue
        seen.add(idx)
        sampled.append(all_candidates[idx])
    if all_candidates[-1] not in sampled:
        sampled[-1] = all_candidates[-1]
    return sampled


def _apply_scales_to_projection(
    *,
    point: Dict[str, Any],
    candidate: Dict[str, Any],
) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float], Optional[float]]:
    base_prob = _safe_float(point.get("home_win_prob"))
    base_total = _safe_float(point.get("total_mean"))
    projection = point.get("projection") if isinstance(point.get("projection"), dict) else {}
    decomposition = projection.get("decomposition") if isinstance(projection.get("decomposition"), dict) else {}
    factors = decomposition.get("factor_contributions") if isinstance(decomposition.get("factor_contributions"), dict) else {}
    if base_prob is None or base_total is None:
        return None, None, None, None, None

    scales = candidate.get("weight_scales") if isinstance(candidate.get("weight_scales"), dict) else {}

    def _factor_points(name: str, key: str) -> float:
        payload = factors.get(name)
        if not isinstance(payload, dict):
            return 0.0
        return _safe_float(payload.get(key), 0.0) or 0.0

    margin_delta = (
        (_safe_float(scales.get("base_efficiency_margin_scale"), 1.0) - 1.0) * _factor_points("base_efficiency", "margin_points")
        + (_safe_float(scales.get("injuries_margin_scale"), 1.0) - 1.0) * _factor_points("injuries_depth", "margin_points")
        + (_safe_float(scales.get("regression_margin_scale"), 1.0) - 1.0) * _factor_points("regression_luck", "margin_points")
    )
    total_delta = (
        (_safe_float(scales.get("base_efficiency_total_scale"), 1.0) - 1.0) * _factor_points("base_efficiency", "total_points")
        + (_safe_float(scales.get("injuries_total_scale"), 1.0) - 1.0) * _factor_points("injuries_depth", "total_points")
    )
    adjusted_prob = _sigmoid(_logit(base_prob) + (margin_delta * 0.16))
    adjusted_total = base_total + total_delta

    confidence = _safe_float(decomposition.get("confidence_score"), 0.0) or 0.0
    factor_coverage = _safe_float(decomposition.get("factor_coverage"), 0.0) or 0.0
    penalties = decomposition.get("uncertainty_penalties") if isinstance(decomposition.get("uncertainty_penalties"), dict) else {}
    uncertainty_penalty = _safe_float(penalties.get("total_penalty"), 0.0) or 0.0
    return adjusted_prob, adjusted_total, confidence, factor_coverage, uncertainty_penalty


def _candidate_overrides(candidate: Dict[str, Any]) -> Dict[str, Any]:
    scales = candidate.get("weight_scales") if isinstance(candidate.get("weight_scales"), dict) else {}
    return {
        "factors": {
            "base_efficiency": {
                "margin_weight_scale": _safe_float(scales.get("base_efficiency_margin_scale"), 1.0),
                "total_weight_scale": _safe_float(scales.get("base_efficiency_total_scale"), 1.0),
            },
            "injuries_depth": {
                "margin_weight_scale": _safe_float(scales.get("injuries_margin_scale"), 1.0),
                "total_weight_scale": _safe_float(scales.get("injuries_total_scale"), 1.0),
            },
            "regression_luck": {
                "margin_weight_scale": _safe_float(scales.get("regression_margin_scale"), 1.0),
            },
        },
        "guardrails": candidate.get("guardrails") if isinstance(candidate.get("guardrails"), dict) else {},
    }


def _coverage_score(coverage: float, target: float) -> float:
    if target <= 0:
        return 0.0
    return _clamp(1.0 - (abs(coverage - target) / max(0.05, target)), 0.0, 1.0)


def _scoring(
    *,
    moneyline_brier: float,
    totals_mae: float,
    clv_ml_avg: float,
    clv_total_avg: float,
    coverage: float,
    thresholds: TuningThresholds,
) -> float:
    brier_term = _clamp(1.0 - (moneyline_brier / 0.30), 0.0, 1.0)
    mae_term = _clamp(1.0 - (totals_mae / 11.0), 0.0, 1.0)
    clv_ml_term = _clamp((clv_ml_avg + 0.03) / 0.08, 0.0, 1.0)
    clv_total_term = _clamp((clv_total_avg + 0.03) / 0.08, 0.0, 1.0)
    clv_term = (0.65 * clv_ml_term) + (0.35 * clv_total_term)
    coverage_term = _coverage_score(coverage, thresholds.target_coverage)
    return round((0.38 * brier_term) + (0.28 * mae_term) + (0.24 * clv_term) + (0.10 * coverage_term), 6)


def _forward_folds(
    points: Sequence[Dict[str, Any]],
    *,
    training_days: int,
    step_days: int,
) -> List[Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]]:
    dated = [row for row in points if row.get("game_date") is not None]
    dated.sort(key=lambda row: (str(row.get("game_date")), str(row.get("game_id") or "")))
    unique_days = sorted({str(row["game_date"])[:10] for row in dated})
    folds: List[Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]] = []
    min_train = max(14, int(training_days))
    step = max(1, int(step_days))
    for idx in range(min_train, len(unique_days), step):
        train_days = set(unique_days[max(0, idx - min_train):idx])
        test_days = set(unique_days[idx:idx + step])
        train_points = [row for row in dated if str(row["game_date"])[:10] in train_days]
        test_points = [row for row in dated if str(row["game_date"])[:10] in test_days]
        if len(train_points) < 24 or len(test_points) < 8:
            continue
        folds.append((train_points, test_points))
    return folds


def count_leakage_violations(points: Sequence[Dict[str, Any]]) -> int:
    violations = 0
    for row in points:
        proj_at = _safe_datetime(row.get("projection_created_at"))
        outcome_at = _safe_datetime(row.get("outcome_completed_at"))
        if proj_at is None or outcome_at is None or not (proj_at < outcome_at):
            violations += 1
    return violations


def evaluate_tuning_grid(
    *,
    points: Sequence[Dict[str, Any]],
    candidates: Sequence[Dict[str, Any]],
    training_days: int,
    step_days: int,
    thresholds: Optional[TuningThresholds] = None,
) -> Dict[str, Any]:
    resolved_thresholds = thresholds or TuningThresholds()
    leakage_violations = count_leakage_violations(points)
    if leakage_violations > 0:
        return {
            "status": "rejected",
            "reason": "leakage_detected",
            "leakage_violations": leakage_violations,
            "ranked_candidates": [],
            "recommended_candidate": None,
            "fold_count": 0,
            "sample_size": 0,
        }

    folds = _forward_folds(points, training_days=training_days, step_days=step_days)
    sample_size = sum(len(test) for _train, test in folds)
    if len(folds) < resolved_thresholds.min_fold_count or sample_size < resolved_thresholds.min_sample_size:
        return {
            "status": "rejected",
            "reason": "insufficient_forward_sample",
            "leakage_violations": 0,
            "ranked_candidates": [],
            "recommended_candidate": None,
            "fold_count": len(folds),
            "sample_size": sample_size,
        }

    ranked: List[Dict[str, Any]] = []
    for candidate in candidates:
        brier_terms: List[float] = []
        mae_terms: List[float] = []
        recommendation_clv_ml: List[float] = []
        recommendation_clv_total: List[float] = []
        recommendation_count = 0
        tested = 0

        for _train, test_points in folds:
            for row in test_points:
                adjusted = _apply_scales_to_projection(point=row, candidate=candidate)
                adj_prob, adj_total, confidence, factor_coverage, uncertainty_penalty = adjusted
                actual_home = row.get("home_team_won")
                actual_total = _safe_float(row.get("final_total_points"))
                if adj_prob is None or adj_total is None or actual_home is None or actual_total is None:
                    continue
                tested += 1
                brier_terms.append((adj_prob - (1.0 if bool(actual_home) else 0.0)) ** 2)
                mae_terms.append(abs(adj_total - actual_total))
                market_home_prob = _market_home_prob_no_vig(
                    _safe_float(row.get("open_home_price")),
                    _safe_float(row.get("open_away_price")),
                )
                edge_prob = (
                    abs(adj_prob - market_home_prob)
                    if market_home_prob is not None
                    else abs(adj_prob - 0.5)
                )
                guardrails = candidate.get("guardrails") if isinstance(candidate.get("guardrails"), dict) else {}
                eval_guardrail = evaluate_nfl_edge_guardrails(
                    edge_prob=edge_prob,
                    quality_score=60.0 + (adj_prob - 0.5) * 24.0 - (uncertainty_penalty * 20.0),
                    confidence_score=confidence or 0.0,
                    uncertainty_penalty=uncertainty_penalty or 0.0,
                    factor_coverage=factor_coverage or 0.0,
                    injury_freshness_hours=_safe_float(row.get("injury_freshness_hours"), 0.0),
                    min_quality_score=_safe_float(guardrails.get("min_quality_score")),
                    min_confidence_score=_safe_float(guardrails.get("min_confidence_score")),
                    min_ml_edge_prob=_safe_float(guardrails.get("min_ml_edge_prob")),
                    max_uncertainty_penalty=_safe_float(guardrails.get("max_uncertainty_penalty")),
                    min_factor_coverage=_safe_float(guardrails.get("min_factor_coverage")),
                )
                if bool(eval_guardrail.get("eligible")):
                    recommendation_count += 1
                    clv_ml_actual = _safe_float(row.get("clv_ml_avg"))
                    clv_total_actual = _safe_float(row.get("clv_total_avg"))
                    recommendation_clv_ml.append(
                        clv_ml_actual if clv_ml_actual is not None else ((edge_prob - 0.01) * 0.5)
                    )
                    recommendation_clv_total.append(
                        clv_total_actual if clv_total_actual is not None else ((abs(adj_total - actual_total) * -0.005) + 0.03)
                    )

        if tested <= 0:
            continue
        coverage = recommendation_count / float(tested)
        moneyline_brier = sum(brier_terms) / len(brier_terms) if brier_terms else 1.0
        totals_mae = sum(mae_terms) / len(mae_terms) if mae_terms else 99.0
        clv_ml_avg = sum(recommendation_clv_ml) / len(recommendation_clv_ml) if recommendation_clv_ml else -0.05
        clv_total_avg = sum(recommendation_clv_total) / len(recommendation_clv_total) if recommendation_clv_total else -0.05
        clv_blended = (0.65 * clv_ml_avg) + (0.35 * clv_total_avg)
        passes_throughput = (
            recommendation_count >= resolved_thresholds.min_recommendations
            and coverage >= resolved_thresholds.min_coverage
            and coverage <= resolved_thresholds.max_coverage
        )
        score = _scoring(
            moneyline_brier=moneyline_brier,
            totals_mae=totals_mae,
            clv_ml_avg=clv_ml_avg,
            clv_total_avg=clv_total_avg,
            coverage=coverage,
            thresholds=resolved_thresholds,
        )
        if not passes_throughput:
            score = round(score * 0.55, 6)

        ranked.append(
            {
                "candidate": candidate,
                "config_overrides": _candidate_overrides(candidate),
                "metrics": {
                    "moneyline_brier": round(moneyline_brier, 6),
                    "totals_mae": round(totals_mae, 4),
                    "clv_avg": round(clv_blended, 6),
                    "clv_ml_avg": round(clv_ml_avg, 6),
                    "clv_total_avg": round(clv_total_avg, 6),
                    "coverage": round(coverage, 6),
                    "recommendation_count": recommendation_count,
                    "tested_points": tested,
                    "throughput_ok": passes_throughput,
                },
                "score": score,
            }
        )

    ranked.sort(
        key=lambda item: (
            float(item.get("score") or 0.0),
            -float(item.get("metrics", {}).get("moneyline_brier") or 1.0),
            -float(item.get("metrics", {}).get("clv_avg") or -1.0),
        ),
        reverse=True,
    )
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index

    return {
        "status": "ok" if ranked else "rejected",
        "reason": None if ranked else "no_candidates_scored",
        "leakage_violations": 0,
        "fold_count": len(folds),
        "sample_size": sample_size,
        "ranked_candidates": ranked,
        "recommended_candidate": ranked[0] if ranked else None,
        "thresholds": {
            "min_fold_count": resolved_thresholds.min_fold_count,
            "min_sample_size": resolved_thresholds.min_sample_size,
            "min_recommendations": resolved_thresholds.min_recommendations,
            "min_coverage": resolved_thresholds.min_coverage,
            "max_coverage": resolved_thresholds.max_coverage,
            "target_coverage": resolved_thresholds.target_coverage,
        },
    }
