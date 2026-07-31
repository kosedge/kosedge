"""NBA walkforward / calibration helpers (Phase 2 scaffold).

Uses existing odds_snapshots closing lines only — never triggers Odds API
historical re-pulls. Metrics feed data/ops/nba-model-enterprise-grade-report.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional, Sequence


@dataclass
class NbaWalkforwardRow:
    game_id: str
    game_date: date
    model_spread_home: float
    model_total: float
    close_spread_home: Optional[float]
    close_total: Optional[float]
    actual_margin: Optional[float]
    actual_total: Optional[float]


def mae(errors: Sequence[float]) -> Optional[float]:
    if not errors:
        return None
    return sum(abs(e) for e in errors) / len(errors)


def bias(errors: Sequence[float]) -> Optional[float]:
    if not errors:
        return None
    return sum(errors) / len(errors)


def cover_rate(
    *,
    model_spread_home: Sequence[float],
    actual_margins: Sequence[float],
) -> Optional[float]:
    """ATS cover rate of model fair spread vs actual margin (home perspective)."""
    if not model_spread_home or len(model_spread_home) != len(actual_margins):
        return None
    covers = 0
    decisions = 0
    for spread, margin in zip(model_spread_home, actual_margins):
        # Home covers if margin + spread > 0 (spread is home line).
        edge = margin + spread
        if edge == 0:
            continue
        decisions += 1
        if edge > 0:
            covers += 1
    if decisions == 0:
        return None
    return covers / decisions


def summarize_walkforward(rows: List[NbaWalkforwardRow]) -> Dict[str, Any]:
    spread_err: List[float] = []
    total_err: List[float] = []
    model_spreads: List[float] = []
    actual_margins: List[float] = []
    close_spread_err: List[float] = []
    close_total_err: List[float] = []

    for r in rows:
        if r.actual_margin is not None:
            # Model fair spread vs actual: predicted margin = -spread.
            pred_margin = -float(r.model_spread_home)
            spread_err.append(pred_margin - float(r.actual_margin))
            model_spreads.append(float(r.model_spread_home))
            actual_margins.append(float(r.actual_margin))
            if r.close_spread_home is not None:
                close_pred = -float(r.close_spread_home)
                close_spread_err.append(close_pred - float(r.actual_margin))
        if r.actual_total is not None:
            total_err.append(float(r.model_total) - float(r.actual_total))
            if r.close_total is not None:
                close_total_err.append(float(r.close_total) - float(r.actual_total))

    return {
        "n_games": len(rows),
        "n_spread_graded": len(spread_err),
        "n_total_graded": len(total_err),
        "model_spread_mae": mae(spread_err),
        "model_spread_bias": bias(spread_err),
        "model_total_mae": mae(total_err),
        "model_total_bias": bias(total_err),
        "close_spread_mae": mae(close_spread_err),
        "close_total_mae": mae(close_total_err),
        "model_ats_cover_rate": cover_rate(
            model_spread_home=model_spreads,
            actual_margins=actual_margins,
        ),
        "status": "ready" if spread_err or total_err else "awaiting_outcomes",
    }


def build_enterprise_report_stub(
    *,
    walkforward: Optional[Dict[str, Any]] = None,
    worker_build_id: str,
    model_version: str,
    phase: str = "phase0",
) -> Dict[str, Any]:
    wf = walkforward or {
        "n_games": 0,
        "status": "awaiting_outcomes",
        "note": "Offseason / pre-ingest — no graded sample yet.",
    }
    return {
        "sport": "nba",
        "phase": phase,
        "model_version": model_version,
        "worker_build_id": worker_build_id,
        "walkforward": wf,
        "publish_policy": {
            "mainlines": "research_only" if wf.get("status") != "ready" else "calibrating",
            "props": "queued_until_mainlines_honest",
        },
        "data_policy": {
            "odds_api_historical_repull": False,
            "market_blend_source": "existing_odds_snapshots_only",
            "primary_ingest": "stats.nba.com",
        },
    }
