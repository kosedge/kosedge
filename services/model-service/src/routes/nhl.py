"""NHL model-service routes — Chapter 4 team KEI fair-lines / kei-lines.

--kei-only desk. Props stay dark. No walking KEI to the book.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query

from src.services.nhl_season_engine import priors as P
from src.services.nhl_season_engine.nhl_kei import (
    KEI_VERSION,
    kei_lines_for_dates,
    load_kei_pack,
    tag_from_edge,
)

router = APIRouter(prefix="/nhl", tags=["nhl-model"])


def _is_nhl_preseason(d: date) -> bool:
    """RS window ≈ Sep 29–Jun 30; else preseason / offseason → PASS posture."""
    if d.month in {10, 11, 12, 1, 2, 3, 4, 5, 6}:
        return False
    if d.month == 9 and d.day >= 29:
        return False
    return True


def _to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None  # NaN guard


def _publish_tag(model_line: Optional[float], *, preseason: bool) -> Dict[str, Any]:
    # No market line on the pack path — Best trust is web-side vs icehockey_nhl.
    tag = tag_from_edge(
        None if model_line is None else 0.0,
        best_trusted=False,
        preseason=preseason,
    )
    return {
        "tag": tag,
        "edge": None,
        "best_trusted": False,
        "preseason": preseason,
        "reason": "preseason" if preseason else "await_trusted_best",
    }


def _kei_pack_as_fair_lines(
    *,
    target_date: date,
    days_ahead: int,
    preseason: bool,
) -> List[Dict[str, Any]]:
    rows = kei_lines_for_dates(
        game_date=target_date.isoformat(),
        days_ahead=days_ahead,
        limit=120,
    )
    out: List[Dict[str, Any]] = []
    for g in rows:
        spread = _to_float(g.get("kei_puck_home") if g.get("kei_puck_home") is not None else g.get("kei_spread_home"))
        total = _to_float(g.get("kei_total"))
        wp = _to_float(g.get("kei_home_win_prob"))
        out.append(
            {
                "game_id": g.get("game_id"),
                "game_date": g.get("date") or target_date.isoformat(),
                "start_time": g.get("start_time_utc"),
                "home_team": g.get("home_team") or g.get("home"),
                "away_team": g.get("away_team") or g.get("away"),
                "home_abbr": g.get("home"),
                "away_abbr": g.get("away"),
                "home_win_prob": wp,
                "fair_home_ml": None,
                "total_mean": total,
                "fair_total": total,
                "fair_spread_home": spread,
                "home_cover_prob": wp,
                "margin_mean": None if spread is None else -spread,
                "worker_build_id": KEI_VERSION,
                "projected_at": None,
                "kei_version": KEI_VERSION,
                "source": "season_engine_ch4",
                "venue": g.get("venue"),
                "publish": {
                    "spread": _publish_tag(spread, preseason=preseason),
                    "total": _publish_tag(total, preseason=preseason),
                },
            }
        )
    return out


@router.get("/health")
def nhl_health() -> Dict[str, Any]:
    pack = load_kei_pack()
    return {
        "ok": True,
        "sport": "nhl",
        "engine_version": P.ENGINE_VERSION,
        "kei_version": KEI_VERSION,
        "kei_pack_present": bool(pack.get("present")),
        "kei_game_count": pack.get("game_count") or 0,
        "NHL_TEAM_CARRY_SHRINK": P.NHL_TEAM_CARRY_SHRINK,
        "ODDS_SPORT_KEY": P.ODDS_SPORT_KEY,
        "phase": "ch4",
    }


@router.get("/fair-lines")
def nhl_fair_lines(
    game_date: Optional[date] = Query(None, description="UTC date; defaults to today"),
    days_ahead: int = Query(14, ge=0, le=60),
    source: str = Query(
        "auto",
        description="auto | season_engine (Ch4 KEI) | kei | ch4",
    ),
) -> Dict[str, Any]:
    """Desk fair-lines board — Chapter 4 team KEI only."""
    target_date = game_date or date.today()
    preseason = _is_nhl_preseason(target_date)
    src = (source or "auto").strip().lower()
    if src not in {"auto", "season_engine", "kei", "ch4"}:
        src = "auto"

    lines = _kei_pack_as_fair_lines(
        target_date=target_date, days_ahead=days_ahead, preseason=preseason
    )
    pack = load_kei_pack()
    return {
        "game_date": target_date.isoformat(),
        "model_version": pack.get("kei_version") or KEI_VERSION,
        "worker_build_id": KEI_VERSION,
        "count": len(lines),
        "lines": lines,
        "slate_status": "ok"
        if lines
        else ("offseason_empty" if preseason else "no_kei_for_date"),
        "message": None
        if lines
        else "NHL Ch4 KEI pack has no games in this date window.",
        "source": "season_engine_ch4",
        "features_mode": "season_engine_team_kei_ch4",
        "phase": "ch4",
        "ODDS_SPORT_KEY": P.ODDS_SPORT_KEY,
        "preseason": preseason,
    }


@router.get("/kei-lines")
def nhl_kei_lines(
    game_date: Optional[date] = Query(None),
    days_ahead: int = Query(14, ge=0, le=60),
) -> Dict[str, Any]:
    target_date = game_date or date.today()
    rows = kei_lines_for_dates(
        game_date=target_date.isoformat(),
        days_ahead=days_ahead,
        limit=120,
    )
    pack = load_kei_pack()
    return {
        "game_date": target_date.isoformat(),
        "kei_version": pack.get("kei_version") or KEI_VERSION,
        "count": len(rows),
        "games": rows,
        "source": "season_engine_ch4",
        "features_mode": "season_engine_team_kei_ch4",
        "phase": "ch4",
    }
