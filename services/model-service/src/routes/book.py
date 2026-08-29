"""The Book ops routes — /ops/book/*.

Auth: same DepthSot gate (x-kosedge-secret / INTERNAL_API_SECRET).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from src.ops_auth import require_kosedge_internal
from src.services.book_ledger.metrics import (
    calibration_by_kei_edge,
    clv_distribution,
    lean_hit_rate,
    live_exposure,
    unit_roi,
)
from src.services.book_ledger.schema import BookRow
from src.services.book_ledger.store import get_store

router = APIRouter(tags=["book"])


class SnapshotBody(BaseModel):
    sport: str
    season: int
    week_or_slate: str
    game_id: str
    home: str
    away: str
    type: str
    market: str
    side: str
    posted_at: str
    line: Optional[float] = None
    price: Optional[float] = None
    kei_at_post: Dict[str, Any] = Field(default_factory=dict)
    market_at_post: Dict[str, Any] = Field(default_factory=dict)
    market_source: Optional[str] = None
    stake_flag: str = "paper"
    actor: Optional[str] = None
    late_post: bool = False
    post_timing: Optional[str] = None
    confirmation: Optional[str] = None
    info_overlap: Optional[str] = None
    rest_flag: Optional[str] = None
    weather_flag: Optional[str] = None
    notes_ref: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class CloseBody(BaseModel):
    close_line: Optional[float] = None
    close_price: Optional[float] = None
    close_at: Optional[str] = None


class SettleBody(BaseModel):
    result: str
    pnl_units: Optional[float] = None


class CfbSnapshotBody(BaseModel):
    slate_date: str
    season: int = 2026
    stake_flag: str = "paper"
    actor: str = "ops"
    include_aug30_late: bool = False


@router.get("/ops/book/ping")
def book_ping(request: Request) -> Dict[str, Any]:
    require_kosedge_internal(request)
    return {"ok": True, "service": "book", "public_ui": False}


@router.get("/ops/book/status")
def book_status(
    request: Request,
    sport: Optional[str] = None,
    week_or_slate: Optional[str] = None,
) -> Dict[str, Any]:
    require_kosedge_internal(request)
    store = get_store()
    rows = store.list_rows(sport=sport, week_or_slate=week_or_slate)
    counts = {
        "n": len(rows),
        "play": sum(1 for r in rows if r.get("type") == "play"),
        "lean": sum(1 for r in rows if r.get("type") == "lean"),
        "pass": sum(1 for r in rows if r.get("type") == "pass"),
        "pending": sum(1 for r in rows if r.get("result") == "pending"),
    }
    return {
        "ok": True,
        "sport": sport,
        "week_or_slate": week_or_slate,
        "counts": counts,
        "live_exposure": live_exposure(rows, week_or_slate=week_or_slate),
        "primary_metric": "clv",
    }


@router.get("/ops/book/rows")
def book_rows(
    request: Request,
    sport: Optional[str] = None,
    week_or_slate: Optional[str] = None,
    result: Optional[str] = None,
) -> Dict[str, Any]:
    require_kosedge_internal(request)
    rows = get_store().list_rows(sport=sport, week_or_slate=week_or_slate, result=result)
    return {"ok": True, "n": len(rows), "rows": rows}


@router.post("/ops/book/snapshot")
def book_snapshot(request: Request, body: SnapshotBody) -> Dict[str, Any]:
    require_kosedge_internal(request)
    row = BookRow(
        book_id="",
        sport=body.sport,
        season=body.season,
        week_or_slate=body.week_or_slate,
        game_id=body.game_id,
        home=body.home,
        away=body.away,
        type=body.type,
        market=body.market,
        side=body.side,
        posted_at=body.posted_at,
        line=body.line,
        price=body.price,
        kei_at_post=body.kei_at_post,
        market_at_post=body.market_at_post,
        market_source=body.market_source,
        stake_flag=body.stake_flag,
        actor=body.actor,
        late_post=body.late_post,
        post_timing=body.post_timing,
        confirmation=body.confirmation,
        info_overlap=body.info_overlap,
        rest_flag=body.rest_flag,
        weather_flag=body.weather_flag,
        notes_ref=body.notes_ref,
        payload=body.payload,
        result="pending",
    )
    return get_store().snapshot(row)


@router.post("/ops/book/cfb/snapshot")
def book_cfb_snapshot(request: Request, body: CfbSnapshotBody) -> Dict[str, Any]:
    require_kosedge_internal(request)
    from src.services.book_ledger.cfb_snapshot import snapshot_cfb_slate

    return snapshot_cfb_slate(
        slate_date=body.slate_date,
        season=body.season,
        actor=body.actor,
        stake_flag=body.stake_flag,
        include_aug30_late=body.include_aug30_late,
    )


@router.post("/ops/book/{book_id}/close")
def book_close(request: Request, book_id: str, body: CloseBody) -> Dict[str, Any]:
    require_kosedge_internal(request)
    try:
        return get_store().record_close(
            book_id,
            close_line=body.close_line,
            close_price=body.close_price,
            close_at=body.close_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/ops/book/{book_id}/settle")
def book_settle(request: Request, book_id: str, body: SettleBody) -> Dict[str, Any]:
    require_kosedge_internal(request)
    try:
        return get_store().settle(book_id, result=body.result, pnl_units=body.pnl_units)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/ops/book/metrics")
def book_metrics(
    request: Request,
    sport: Optional[str] = None,
    week_or_slate: Optional[str] = None,
    include_paper: bool = Query(False),
) -> Dict[str, Any]:
    require_kosedge_internal(request)
    rows = get_store().list_rows(sport=sport, week_or_slate=week_or_slate)
    return {
        "ok": True,
        "primary_metric": "clv",
        "clv_plays": clv_distribution(rows, book_type="play"),
        "clv_leans": clv_distribution(rows, book_type="lean"),
        "unit_roi": unit_roi(rows, include_paper=include_paper),
        "lean_hit_rate": lean_hit_rate(rows),
        "calibration": calibration_by_kei_edge(rows),
        "live_exposure": live_exposure(rows, week_or_slate=week_or_slate),
    }
