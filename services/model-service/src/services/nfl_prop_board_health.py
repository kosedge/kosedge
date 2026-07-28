"""Desk-facing publish gates for the weekly prop / projection board.

Complements season pass/skill leader quality with operational health:
snap coverage, injury freshness, dual RB rooms, pass MAE proxy readiness.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence


def evaluate_prop_board_health(
    *,
    baseline_rows: Sequence[Mapping[str, Any]],
    snap_linked_rate: Optional[float] = None,
    injury_rows_present: Optional[int] = None,
    pass_mae_recent: Optional[float] = None,
    dual_1000_rb_rooms: int = 0,
) -> Dict[str, Any]:
    """Return structured health report; publish_ready_ops is advisory."""
    n = len(baseline_rows)
    with_snap = 0
    with_rb_share = 0
    qb_full = 0
    for row in baseline_rows:
        cov = row.get("source_coverage") if isinstance(row.get("source_coverage"), dict) else {}
        if cov.get("offense_snap_pct") is not None or cov.get("snap_source") == "nfl_dp_snap_counts_weekly":
            with_snap += 1
        if cov.get("rb_rush_share") is not None:
            with_rb_share += 1
        if str(row.get("position") or "").upper() == "QB":
            share = cov.get("qb_starter_share")
            if share is not None and float(share) >= 0.85:
                qb_full += 1

    snap_rate = (with_snap / n) if n else 0.0
    if snap_linked_rate is not None:
        snap_rate = max(snap_rate, float(snap_linked_rate))

    checks = {
        "baseline_rows": n,
        "snap_coverage_rate": round(snap_rate, 4),
        "snap_coverage_ok": snap_rate >= 0.15 or n == 0,  # preseason often low
        "rb_rush_share_rows": with_rb_share,
        "qb_full_starter_rows": qb_full,
        "injury_rows_present": injury_rows_present,
        "injury_feed_ok": injury_rows_present is None or int(injury_rows_present) > 0,
        "pass_mae_recent": pass_mae_recent,
        "pass_mae_gate_ok": pass_mae_recent is None or float(pass_mae_recent) <= 12.0,
        "dual_1000_rb_rooms": int(dual_1000_rb_rooms),
        "dual_rb_rooms_ok": int(dual_1000_rb_rooms) == 0,
    }
    checks["publish_ready_ops"] = bool(
        checks["snap_coverage_ok"]
        and checks["injury_feed_ok"]
        and checks["dual_rb_rooms_ok"]
        # pass MAE gate is hard only when a recent metric is supplied
        and (pass_mae_recent is None or checks["pass_mae_gate_ok"])
    )
    checks["research_only_pass_props"] = not checks["pass_mae_gate_ok"]
    return checks
