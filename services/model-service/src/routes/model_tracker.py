"""Model performance + pick/unit tracker API (sport-agnostic)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Body, Path, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

log = logging.getLogger("kosedge.model_tracker.routes")

router = APIRouter(prefix="/model-tracker", tags=["model-tracker"])


class LogPickBody(BaseModel):
    sport: Literal["cfb", "nfl", "nba", "mlb", "wnba"]
    season: int = Field(2026, ge=2010, le=2100)
    week: int = Field(0, ge=0, le=30)
    home_team: str = Field(..., min_length=2, max_length=12)
    away_team: str = Field(..., min_length=2, max_length=12)
    market_type: Literal["spread", "total", "moneyline", "prop"] = "spread"
    side: str = Field(..., min_length=1, max_length=32)
    tag: Literal["PLAY", "LEAN"]
    line_at_publish: Optional[float] = None
    odds_american: int = -110
    units: Optional[float] = Field(None, ge=0, le=10)
    slate_id: Optional[str] = None
    game_id: Optional[str] = None
    game_key: Optional[str] = None
    engine_version: Optional[str] = None
    artifact_as_of: Optional[str] = None
    deploy_git_sha: Optional[str] = None
    kei_version: Optional[str] = None
    fair_line: Optional[float] = None
    kei_line: Optional[float] = None
    edge_pts: Optional[float] = None
    confidence: Optional[str] = None
    variance: Optional[float] = None
    confirmation: Optional[str] = None
    info_overlap: Optional[str] = None
    proof_projection_id: Optional[str] = None
    created_by: Literal["desk", "system"] = "desk"
    source: Literal["manual", "kei_board", "auto"] = "manual"
    notes: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None


class CloseBody(BaseModel):
    line_at_close: float
    source: str = "manual"


class GradeBody(BaseModel):
    home_score: Optional[int] = Field(None, ge=0, le=200)
    away_score: Optional[int] = Field(None, ge=0, le=200)
    grade: Optional[Literal["win", "loss", "push", "void"]] = None
    source: str = "manual"


class ImportKeiBody(BaseModel):
    weeks: Optional[List[int]] = None
    tags: List[Literal["PLAY", "LEAN"]] = Field(default_factory=lambda: ["PLAY", "LEAN"])
    dry_run: bool = True


@router.get("/status")
def tracker_status() -> Dict[str, Any]:
    from src.services.model_tracker.core import status_payload

    return status_payload()


@router.get("/sports")
def tracker_sports() -> Dict[str, Any]:
    from src.services.model_tracker.core import sports_status
    from src.services.model_tracker.sports import all_stub_statuses

    return {
        "ok": True,
        "sports": sports_status(),
        "adapters": all_stub_statuses(),
    }


@router.post("/picks")
def tracker_log_pick(body: LogPickBody = Body(...)) -> Dict[str, Any]:
    from src.services.model_tracker.core import log_pick

    try:
        pick = log_pick(body.model_dump(exclude_none=True))
        return {"ok": True, "pick": pick}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/picks")
def tracker_list_picks(
    sport: Optional[str] = Query(None),
    season: Optional[int] = Query(None, ge=2010, le=2100),
    week: Optional[int] = Query(None, ge=0, le=30),
    tag: Optional[Literal["PLAY", "LEAN"]] = Query(None),
    grade: Optional[str] = Query(None),
    engine_version: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=2000),
) -> Dict[str, Any]:
    from src.services.model_tracker.core import list_picks

    picks = list_picks(
        sport=sport,
        season=season,
        week=week,
        tag=tag,
        grade=grade,
        engine_version=engine_version,
        limit=limit,
    )
    return {"ok": True, "n": len(picks), "picks": picks}


@router.get("/picks/{pick_id}")
def tracker_get_pick(pick_id: str = Path(..., min_length=8, max_length=64)) -> Dict[str, Any]:
    from src.services.model_tracker.core import get_pick

    pick = get_pick(pick_id)
    if pick is None:
        return {"ok": False, "error": "pick not found", "id": pick_id}
    return {"ok": True, "pick": pick}


@router.post("/picks/{pick_id}/close")
def tracker_close_pick(
    pick_id: str = Path(..., min_length=8, max_length=64),
    body: CloseBody = Body(...),
) -> Dict[str, Any]:
    from src.services.model_tracker.core import close_pick

    pick = close_pick(pick_id, line_at_close=body.line_at_close, source=body.source)
    if pick is None:
        return {"ok": False, "error": "pick not found", "id": pick_id}
    return {"ok": True, "pick": pick}


@router.post("/picks/{pick_id}/grade")
def tracker_grade_pick(
    pick_id: str = Path(..., min_length=8, max_length=64),
    body: GradeBody = Body(...),
) -> Dict[str, Any]:
    from src.services.model_tracker.core import grade_pick

    try:
        pick = grade_pick(
            pick_id,
            home_score=body.home_score,
            away_score=body.away_score,
            grade=body.grade,
            source=body.source,
        )
    except ValueError as exc:
        return {"ok": False, "error": str(exc), "id": pick_id}
    if pick is None:
        return {"ok": False, "error": "pick not found", "id": pick_id}
    return {"ok": True, "pick": pick}


@router.get("/summary")
def tracker_summary(
    sport: Optional[str] = Query(None),
    season: Optional[int] = Query(None, ge=2010, le=2100),
    week: Optional[int] = Query(None, ge=0, le=30),
    engine_version: Optional[str] = Query(None),
    limit: int = Query(1000, ge=1, le=5000),
) -> Dict[str, Any]:
    from src.services.model_tracker.core import summary

    return summary(
        sport=sport,
        season=season,
        week=week,
        engine_version=engine_version,
        limit=limit,
    )


@router.get("/export")
def tracker_export(
    sport: Optional[str] = Query(None),
    season: Optional[int] = Query(None, ge=2010, le=2100),
    week: Optional[int] = Query(None, ge=0, le=30),
    fmt: Literal["json", "csv"] = Query("json"),
    limit: int = Query(5000, ge=1, le=20000),
):
    from src.services.model_tracker.core import export_picks

    payload = export_picks(
        sport=sport, season=season, week=week, fmt=fmt, limit=limit
    )
    if fmt == "csv":
        return PlainTextResponse(
            payload.get("csv") or "",
            media_type="text/csv",
            headers={
                "Content-Disposition": 'attachment; filename="model_pick_ledger.csv"'
            },
        )
    return payload


@router.post("/cfb/import-kei-board")
def tracker_cfb_import_kei(body: ImportKeiBody = Body(default_factory=ImportKeiBody)) -> Dict[str, Any]:
    from src.services.model_tracker.cfb_adapter import import_kei_board_picks

    try:
        return import_kei_board_picks(
            weeks=body.weeks,
            tags=body.tags,
            dry_run=body.dry_run,
        )
    except Exception as exc:
        log.exception("cfb kei import failed")
        return {"ok": False, "error": str(exc)}
