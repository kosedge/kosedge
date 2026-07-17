from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Sequence


def _safe_float(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _week_key(value: Any) -> str:
    return str(value)[:10]


def summarize_decomposition_drift(
    *,
    rows: Sequence[Dict[str, Any]],
    baseline_weeks: int = 4,
    warn_threshold: float = 0.18,
    critical_threshold: float = 0.30,
) -> Dict[str, Any]:
    weekly: Dict[str, Dict[str, Dict[str, float]]] = {}
    for row in rows:
        projection = row.get("projection") if isinstance(row.get("projection"), dict) else {}
        decomposition = projection.get("decomposition") if isinstance(projection.get("decomposition"), dict) else {}
        factors = decomposition.get("factor_contributions") if isinstance(decomposition.get("factor_contributions"), dict) else {}
        week = _week_key(row.get("week_bucket"))
        if not week:
            continue
        week_bucket = weekly.setdefault(week, {})
        for factor_name, payload in factors.items():
            if not isinstance(payload, dict):
                continue
            factor_bucket = week_bucket.setdefault(str(factor_name), {"rows": 0.0, "sum_abs": 0.0})
            factor_bucket["rows"] += 1.0
            factor_bucket["sum_abs"] += abs(_safe_float(payload.get("margin_points"))) + abs(
                _safe_float(payload.get("total_points"))
            )

    ordered_weeks = sorted(weekly.keys())
    if not ordered_weeks:
        return {
            "status": "insufficient_data",
            "latest_week": None,
            "top_shifts": [],
            "weekly_factor_distributions": {},
        }
    latest_week = ordered_weeks[-1]
    baseline_window = ordered_weeks[max(0, len(ordered_weeks) - 1 - baseline_weeks): len(ordered_weeks) - 1]
    if not baseline_window:
        return {
            "status": "insufficient_data",
            "latest_week": latest_week,
            "top_shifts": [],
            "weekly_factor_distributions": {
                week: {
                    factor: round(values["sum_abs"] / max(1.0, values["rows"]), 6)
                    for factor, values in factor_map.items()
                }
                for week, factor_map in weekly.items()
            },
        }

    factor_names = sorted({name for week in weekly.values() for name in week.keys()})
    top_shifts: List[Dict[str, Any]] = []
    severity = "stable"
    for factor_name in factor_names:
        latest_vals = weekly.get(latest_week, {}).get(factor_name, {"rows": 0.0, "sum_abs": 0.0})
        latest_mean = latest_vals["sum_abs"] / max(1.0, latest_vals["rows"])
        baseline_means = []
        for week in baseline_window:
            week_vals = weekly.get(week, {}).get(factor_name, {"rows": 0.0, "sum_abs": 0.0})
            baseline_means.append(week_vals["sum_abs"] / max(1.0, week_vals["rows"]))
        baseline_mean = sum(baseline_means) / max(1, len(baseline_means))
        abs_shift = abs(latest_mean - baseline_mean)
        rel_shift = abs_shift / max(0.05, abs(baseline_mean))
        if rel_shift >= critical_threshold:
            severity = "critical"
        elif rel_shift >= warn_threshold and severity != "critical":
            severity = "warning"
        top_shifts.append(
            {
                "factor": factor_name,
                "latest_mean_abs_points": round(latest_mean, 6),
                "baseline_mean_abs_points": round(baseline_mean, 6),
                "absolute_shift": round(abs_shift, 6),
                "relative_shift": round(rel_shift, 6),
            }
        )
    top_shifts.sort(key=lambda item: float(item.get("relative_shift") or 0.0), reverse=True)
    return {
        "status": severity,
        "latest_week": latest_week,
        "baseline_weeks": baseline_window,
        "top_shifts": top_shifts[:8],
        "weekly_factor_distributions": {
            week: {
                factor: round(values["sum_abs"] / max(1.0, values["rows"]), 6)
                for factor, values in factor_map.items()
            }
            for week, factor_map in weekly.items()
        },
        "snapshot_date": date.today().isoformat(),
    }
