"""Unified proof layer API — projection log / close / result / performance."""

from __future__ import annotations

import logging
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Body, Path, Query
from pydantic import BaseModel, Field

log = logging.getLogger("kosedge.proof")

router = APIRouter(prefix="/proof", tags=["proof-layer"])


class LogProjectionBody(BaseModel):
    sport: Literal["nfl", "cfb"] = Field(..., description="Sport discriminator")
    market_type: str = Field("game", description="Market type (game spread/total/wp)")
    home_team: str = Field(..., min_length=2, max_length=8)
    away_team: str = Field(..., min_length=2, max_length=8)
    season: int = Field(2026, ge=2010, le=2100)
    week: int = Field(1, ge=1, le=22)
    engine_version: Optional[str] = None
    spread_home: Optional[float] = None
    model_spread_home: Optional[float] = None
    expected_total: Optional[float] = None
    model_total: Optional[float] = None
    home_win_prob: Optional[float] = None
    away_win_prob: Optional[float] = None
    expected_home_score: Optional[float] = None
    expected_away_score: Optional[float] = None
    game_id: Optional[str] = None
    drivers: Optional[Dict[str, Any]] = None
    projection: Optional[Dict[str, Any]] = None


class CloseBody(BaseModel):
    close_spread_home: Optional[float] = None
    close_total: Optional[float] = None
    source: str = "manual"


class ResultBody(BaseModel):
    home_score: int = Field(..., ge=0, le=200)
    away_score: int = Field(..., ge=0, le=200)
    source: str = "manual"
    apply_inseason: bool = False


@router.post("/projections")
def proof_log_projection(body: LogProjectionBody = Body(...)) -> Dict[str, Any]:
    from src.services.proof_layer.core import log_projection

    record = log_projection(body.model_dump(exclude_none=True), sport=body.sport)
    return {"ok": True, "projection": record.to_dict()}


@router.post("/projections/{projection_id}/close")
def proof_projection_close(
    projection_id: str = Path(..., min_length=8, max_length=64),
    body: CloseBody = Body(...),
) -> Dict[str, Any]:
    from src.services.proof_layer.core import record_close

    if body.close_spread_home is None and body.close_total is None:
        return {
            "ok": False,
            "error": "Provide close_spread_home and/or close_total",
        }
    record = record_close(
        projection_id,
        close_spread_home=body.close_spread_home,
        close_total=body.close_total,
        source=body.source,
    )
    if record is None:
        return {"ok": False, "error": "projection not found", "id": projection_id}
    return {"ok": True, "projection": record.to_dict()}


@router.post("/projections/{projection_id}/result")
def proof_projection_result(
    projection_id: str = Path(..., min_length=8, max_length=64),
    body: ResultBody = Body(...),
) -> Dict[str, Any]:
    from src.services.proof_layer.core import record_result

    record = record_result(
        projection_id,
        home_score=body.home_score,
        away_score=body.away_score,
        source=body.source,
        apply_inseason=bool(body.apply_inseason),
    )
    if record is None:
        return {"ok": False, "error": "projection not found", "id": projection_id}
    out: Dict[str, Any] = {"ok": True, "projection": record.to_dict()}
    if body.apply_inseason and record.sport == "cfb":
        try:
            from src.services.cfb_season_engine.in_season_update import state_summary

            out["in_season"] = {
                "home": state_summary(team=record.home_team),
                "away": state_summary(team=record.away_team),
            }
        except Exception as exc:  # pragma: no cover
            out["in_season_error"] = str(exc)
    return out


@router.get("/performance")
def proof_performance_summary(
    sport: Optional[Literal["nfl", "cfb"]] = Query(None),
    limit: int = Query(200, ge=1, le=500),
    engine_version: Optional[str] = Query(None),
) -> Dict[str, Any]:
    from src.services.proof_layer.core import documentation, performance_summary
    from src.services.proof_layer.proof_lake import ProofLakeError

    try:
        payload = performance_summary(
            sport=sport, limit=limit, engine_version=engine_version
        )
        payload["tracking"] = documentation()
        return payload
    except ProofLakeError as exc:
        log.exception("proof lake unavailable: %s", exc)
        return {
            "ok": False,
            "error": f"proof lake unavailable: {exc}",
            "backend": documentation().get("backend"),
            "lake_dir": documentation().get("lake_dir"),
        }
    except Exception as exc:
        log.exception("proof performance summary failed: %s", exc)
        return {
            "ok": False,
            "error": f"performance summary failed: {exc}",
        }


@router.get("/calibration-report")
def proof_calibration_report(
    sport: Literal["nfl", "cfb"] = Query(..., description="Sport filter (required)"),
    engine_version: Optional[str] = Query(None),
    season: Optional[int] = Query(None, ge=2010, le=2100),
    from_ts: Optional[str] = Query(None, alias="from", description="ISO projected_at lower bound"),
    to_ts: Optional[str] = Query(None, alias="to", description="ISO projected_at upper bound"),
) -> Dict[str, Any]:
    from src.services.proof_layer.calibration_report import build_calibration_report

    try:
        return build_calibration_report(
            sport=sport,
            engine_version=engine_version,
            season=season,
            from_ts=from_ts,
            to_ts=to_ts,
        )
    except Exception as exc:
        log.exception("calibration report failed: %s", exc)
        return {
            "ok": False,
            "error": f"calibration report failed: {exc}",
            "report_type": "historical_calibration",
        }


class GenerateCalibrationReportBody(BaseModel):
    sport: Literal["nfl", "cfb"]
    engine_version: Optional[str] = None
    season: Optional[int] = Field(None, ge=2010, le=2100)
    from_ts: Optional[str] = None
    to_ts: Optional[str] = None


@router.post("/calibration-report/generate")
def proof_calibration_report_generate(
    body: GenerateCalibrationReportBody = Body(...),
) -> Dict[str, Any]:
    from src.services.proof_layer.calibration_report import generate_calibration_report

    try:
        return generate_calibration_report(
            sport=body.sport,
            engine_version=body.engine_version,
            season=body.season,
            from_ts=body.from_ts,
            to_ts=body.to_ts,
            write_artifact=True,
        )
    except Exception as exc:
        log.exception("calibration report generate failed: %s", exc)
        return {
            "ok": False,
            "error": f"calibration report generate failed: {exc}",
            "report_type": "historical_calibration",
        }


@router.get("/docs")
def proof_docs() -> Dict[str, Any]:
    from src.services.proof_layer.core import documentation

    return documentation()
