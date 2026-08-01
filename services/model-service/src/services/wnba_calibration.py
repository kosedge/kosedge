"""WNBA walkforward / calibration helpers (Phase 2).

Uses existing odds_snapshots closing lines only — never triggers Odds API
historical re-pulls unless densify job is explicitly invoked with credit cap.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional, Sequence


@dataclass
class WnbaWalkforwardRow:
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
    if not model_spread_home or len(model_spread_home) != len(actual_margins):
        return None
    covers = 0
    decisions = 0
    for spread, margin in zip(model_spread_home, actual_margins):
        edge = margin + spread
        if edge == 0:
            continue
        decisions += 1
        if edge > 0:
            covers += 1
    if decisions == 0:
        return None
    return covers / decisions


def market_ats_cover_rate(
    *,
    model_spread_home: Sequence[float],
    close_spread_home: Sequence[float],
    actual_margins: Sequence[float],
) -> Optional[float]:
    if not model_spread_home or len(model_spread_home) != len(actual_margins):
        return None
    if len(model_spread_home) != len(close_spread_home):
        return None
    covers = 0
    decisions = 0
    for model_sp, close_sp, margin in zip(
        model_spread_home, close_spread_home, actual_margins
    ):
        edge = float(close_sp) - float(model_sp)
        if abs(edge) < 1e-9:
            continue
        home_covers = (float(margin) + float(close_sp)) > 0
        push = (float(margin) + float(close_sp)) == 0
        if push:
            continue
        decisions += 1
        bet_home = edge > 0
        if bet_home == home_covers:
            covers += 1
    if decisions == 0:
        return None
    return covers / decisions


def summarize_walkforward(rows: List[WnbaWalkforwardRow]) -> Dict[str, Any]:
    spread_err: List[float] = []
    total_err: List[float] = []
    model_spreads: List[float] = []
    actual_margins: List[float] = []
    close_spread_err: List[float] = []
    close_total_err: List[float] = []
    model_vs_close_spreads: List[float] = []
    close_spreads_for_ats: List[float] = []
    margins_for_ats: List[float] = []

    for r in rows:
        if r.actual_margin is not None:
            pred_margin = -float(r.model_spread_home)
            spread_err.append(pred_margin - float(r.actual_margin))
            model_spreads.append(float(r.model_spread_home))
            actual_margins.append(float(r.actual_margin))
            if r.close_spread_home is not None:
                close_pred = -float(r.close_spread_home)
                close_spread_err.append(close_pred - float(r.actual_margin))
                model_vs_close_spreads.append(float(r.model_spread_home))
                close_spreads_for_ats.append(float(r.close_spread_home))
                margins_for_ats.append(float(r.actual_margin))
        if r.actual_total is not None:
            total_err.append(float(r.model_total) - float(r.actual_total))
            if r.close_total is not None:
                close_total_err.append(float(r.close_total) - float(r.actual_total))

    n_with_close = sum(
        1 for r in rows if r.close_spread_home is not None or r.close_total is not None
    )
    model_spread_mae = mae(spread_err)
    close_spread_mae = mae(close_spread_err)
    blend_hint = "hold"
    if (
        model_spread_mae is not None
        and close_spread_mae is not None
        and close_spread_mae > 0
    ):
        ratio = model_spread_mae / close_spread_mae
        if ratio >= 1.25:
            blend_hint = "raise_market_blend"
        elif ratio <= 0.95:
            blend_hint = "lower_market_blend"

    return {
        "n_games": len(rows),
        "n_spread_graded": len(spread_err),
        "n_total_graded": len(total_err),
        "n_with_close_lines": n_with_close,
        "model_spread_mae": model_spread_mae,
        "model_spread_bias": bias(spread_err),
        "model_total_mae": mae(total_err),
        "model_total_bias": bias(total_err),
        "close_spread_mae": close_spread_mae,
        "close_total_mae": mae(close_total_err),
        "model_ats_cover_rate": cover_rate(
            model_spread_home=model_spreads,
            actual_margins=actual_margins,
        ),
        "model_vs_close_ats_cover_rate": market_ats_cover_rate(
            model_spread_home=model_vs_close_spreads,
            close_spread_home=close_spreads_for_ats,
            actual_margins=margins_for_ats,
        ),
        "blend_hint": blend_hint,
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
        "note": "Pre-ingest / empty slate — no graded sample yet.",
    }
    return {
        "sport": "wnba",
        "phase": phase,
        "model_version": model_version,
        "worker_build_id": worker_build_id,
        "walkforward": wf,
        "publish_policy": {
            "mainlines": "research_only" if wf.get("status") != "ready" else "calibrating",
            "props": "research_only",
        },
        "sport_specific": {
            "game_minutes": 40,
            "pace_method": "harmonic_mean",
            "league_pace_prior": 81.0,
            "league_ortg_prior": 103.0,
            "home_court_prior": 2.25,
            "season_rule": "calendar_tip_year_may_start",
            "team_count": 13,
            "abbr_collision_note": "CHI/DAL/IND/MIN/PHX sport-scoped via leagues.code=wnba",
        },
        "data_policy": {
            "odds_api_historical_repull": (
                "targeted_mainlines_only_if_empty_with_credit_cap"
            ),
            "market_blend_source": "existing_odds_snapshots_plus_targeted_densify",
            "primary_ingest": "data.wnba.com/schedule+gamedetail",
            "close_line_join": "et_date_plus_full_name_or_abbr_aliases",
            "no_nba_prior_import": True,
        },
    }
