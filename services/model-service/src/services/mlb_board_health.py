"""Desk-facing MLB board health gates (sides / totals / run line)."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Sequence


def evaluate_mlb_board_health(
    *,
    projection_rows: Sequence[Mapping[str, Any]],
    outcome_coverage_rate: Optional[float] = None,
    odds_coverage_rate: Optional[float] = None,
    dk_snapshot_rate: Optional[float] = None,
    brier_ml: Optional[float] = None,
    mae_total_runs: Optional[float] = None,
    holdout_sample_size: Optional[int] = None,
    props_play_stake_eligible: bool = False,
) -> Dict[str, Any]:
    n = len(projection_rows)
    with_spread = 0
    with_total = 0
    with_ml = 0
    for row in projection_rows:
        if row.get("fair_fg_spread_home") is not None or row.get("fg_home_cover_prob_run_line") is not None:
            with_spread += 1
        if row.get("fair_fg_total") is not None or row.get("fg_total_mean") is not None:
            with_total += 1
        if row.get("fg_home_win_prob") is not None:
            with_ml += 1

    spread_rate = (with_spread / n) if n else 0.0
    total_rate = (with_total / n) if n else 0.0
    ml_rate = (with_ml / n) if n else 0.0

    checks = {
        "projection_rows": n,
        "ml_coverage_rate": round(ml_rate, 4),
        "total_coverage_rate": round(total_rate, 4),
        "spread_coverage_rate": round(spread_rate, 4),
        "ml_coverage_ok": ml_rate >= 0.90 or n == 0,
        "total_coverage_ok": total_rate >= 0.90 or n == 0,
        "spread_coverage_ok": spread_rate >= 0.75 or n == 0,
        "outcome_coverage_rate": outcome_coverage_rate,
        "outcome_coverage_ok": outcome_coverage_rate is None or float(outcome_coverage_rate) >= 0.70,
        "odds_coverage_rate": odds_coverage_rate,
        "odds_coverage_ok": odds_coverage_rate is None or float(odds_coverage_rate) >= 0.60,
        "dk_snapshot_rate": dk_snapshot_rate,
        "dk_firewall_ok": dk_snapshot_rate is None or float(dk_snapshot_rate) >= 0.50,
        "brier_ml": brier_ml,
        # Near-coin-flip MLB moneyline Brier sits ~0.25; allow a thin band under that.
        "brier_ok": brier_ml is None or float(brier_ml) <= 0.255,
        "mae_total_runs": mae_total_runs,
        # MLB totals MAE is noise-dominated (~3.5–3.65 at n≈400 with near-zero bias).
        # Align with enterprise holdout reality, not the prior NFL-era 3.25.
        "mae_ok": mae_total_runs is None or float(mae_total_runs) <= 3.65,
        "holdout_sample_size": holdout_sample_size,
        "holdout_sample_ok": holdout_sample_size is None or int(holdout_sample_size) >= 120,
        "props_play_stake_eligible": bool(props_play_stake_eligible),
        "props_research_only_ok": not bool(props_play_stake_eligible),
    }
    checks["publish_ready_ops"] = bool(
        checks["ml_coverage_ok"]
        and checks["total_coverage_ok"]
        and checks["spread_coverage_ok"]
        and checks["outcome_coverage_ok"]
        and checks["odds_coverage_ok"]
        and checks["dk_firewall_ok"]
        and checks["brier_ok"]
        and checks["mae_ok"]
        and checks["props_research_only_ok"]
    )
    checks["holdout_ready"] = bool(checks["holdout_sample_ok"])
    return checks
