"""CFB model routes — hierarchical season engine foundation (additive)."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Path, Query
from pydantic import BaseModel, Field

log = logging.getLogger("kosedge.cfb")

router = APIRouter(prefix="/cfb", tags=["cfb-model"])


class ProjectGameBody(BaseModel):
    home_team: str = Field(..., min_length=2, max_length=48)
    away_team: str = Field(..., min_length=2, max_length=48)
    season: int = Field(2026, ge=2010, le=2100)
    week: int = Field(0, ge=0, le=20)
    neutral_site: bool = False
    night_game: bool = False
    demo: bool = True
    # Research smoke default; 15 is too thin for a distribution.
    n_sims: int = Field(5000, ge=200, le=25000)
    # Explicit opt-in log for this request (also: CFB_AUTO_LOG_PROJECTIONS=1).
    log_projection: bool = False


class SimulateBody(BaseModel):
    season: int = Field(2026, ge=2010, le=2100)
    # Densified full-FBS paths are heavier than the old skeleton sample slate.
    # Raised off the toy default of 15; still not an official-slate futures run.
    n_sims: int = Field(200, ge=1, le=2000)
    seed: int = 2026
    demo: bool = True
    as_of_week: int = Field(0, ge=0, le=20)


class LogProjectionBody(BaseModel):
    """Manual projection log (or pass-through of a project-game payload)."""

    home_team: str = Field(..., min_length=2, max_length=48)
    away_team: str = Field(..., min_length=2, max_length=48)
    season: int = Field(2026, ge=2010, le=2100)
    week: int = Field(0, ge=0, le=20)
    engine_version: Optional[str] = None
    spread_home: Optional[float] = None
    model_spread_home: Optional[float] = None
    expected_total: Optional[float] = None
    model_total: Optional[float] = None
    home_win_prob: Optional[float] = None
    away_win_prob: Optional[float] = None
    expected_home_score: Optional[float] = None
    expected_away_score: Optional[float] = None
    drivers: Optional[Dict[str, Any]] = None
    game_id: Optional[str] = None
    fidelity: Optional[str] = None
    mode: Optional[str] = None
    notes: Optional[Dict[str, Any]] = None
    projected_at: Optional[str] = None


class CloseBody(BaseModel):
    close_spread_home: Optional[float] = None
    close_total: Optional[float] = None
    source: str = Field("manual", max_length=64)


class ResultBody(BaseModel):
    home_score: int = Field(..., ge=0, le=200)
    away_score: int = Field(..., ge=0, le=200)
    source: str = Field("manual", max_length=64)
    apply_inseason: bool = False


class InSeasonIngestBody(BaseModel):
    home_team: str = Field(..., min_length=2, max_length=8)
    away_team: str = Field(..., min_length=2, max_length=8)
    home_score: int = Field(..., ge=0, le=200)
    away_score: int = Field(..., ge=0, le=200)
    week: int = Field(1, ge=1, le=20)
    season: int = Field(2026, ge=2010, le=2100)
    model_spread_home: Optional[float] = None
    expected_home_score: Optional[float] = None
    expected_away_score: Optional[float] = None
    game_id: Optional[str] = None
    projection_id: Optional[str] = None
    source: str = Field("manual", max_length=64)


class InSeasonResetBody(BaseModel):
    season: int = Field(2026, ge=2010, le=2100)
    confirm: bool = False


@router.get("/season-engine/status")
def cfb_season_engine_status(
    season: int = Query(2026, ge=2010, le=2100),
    as_of_week: int = Query(1, ge=1, le=20),
    demo: bool = Query(True, description="Packaged universe probe (default)"),
) -> Dict[str, Any]:
    """Describe CFB hierarchical engine layers, data sources, solid vs approximate."""
    from src.services.cfb_season_engine import (
        DEFAULT_SEASON_ENGINE_VERSION,
        engine_status_payload,
    )

    try:
        return engine_status_payload(season=season, as_of_week=as_of_week, demo=demo)
    except Exception as exc:  # pragma: no cover — never 500 a version probe
        log.exception("cfb season-engine status failed")
        return {
            "ok": False,
            "engine_version": DEFAULT_SEASON_ENGINE_VERSION,
            "used_in_spread": False,
            "error": str(exc),
            "note": (
                "Status degraded; version string is still authoritative. "
                "Research prior only — no KEI."
            ),
        }


@router.post("/season-engine/project-game")
def cfb_season_engine_project_game(
    body: ProjectGameBody = Body(...),
) -> Dict[str, Any]:
    """Team-level hierarchical projection for a matchup (foundation)."""
    from src.services.cfb_season_engine import (
        project_game_preview,
        project_game_to_dict,
        resolve_season_universe,
    )

    universe, meta = resolve_season_universe(
        season=body.season,
        as_of_week=body.week,
        demo=body.demo,
        session=None,
    )
    try:
        proj = project_game_preview(
            universe,
            home_team=body.home_team,
            away_team=body.away_team,
            week=body.week,
            season=body.season,
            neutral_site=body.neutral_site,
            night_game=body.night_game,
            n_sims=body.n_sims,
        )
    except KeyError as exc:
        return {
            "ok": False,
            "error": str(exc),
            "mode": meta.get("mode"),
            "hint": "Use packaged FBS codes from GET /cfb/season-engine/status universe",
        }
    payload = project_game_to_dict(proj)
    payload["ok"] = True
    payload["mode"] = meta.get("mode")
    payload["used_in_spread"] = False
    # Immutable research snapshot — never mutate; never fail the request.
    try:
        from datetime import datetime, timezone

        from src.services.cfb_warehouse.predictions import write_prediction

        as_of = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        game_id = str(
            payload.get("game_id")
            or f"{body.season}-W{body.week}-{body.away_team}-{body.home_team}"
        )
        snap = write_prediction(
            {
                "model_version": payload.get("engine_version"),
                "as_of": as_of,
                "game_id": game_id,
                "season": body.season,
                "week": body.week,
                "home_team_id": body.home_team,
                "away_team_id": body.away_team,
                "fair_spread": payload.get("fair_spread", payload.get("spread_home")),
                "fair_total": payload.get("fair_total", payload.get("expected_total")),
                "wp": payload.get("home_win_prob"),
                "uncertainty": payload.get("uncertainty")
                or payload.get("margin_sd"),
                "notes": {
                    "used_in_spread": False,
                    "kei": False,
                    "research_prior": True,
                    "n_sims": payload.get("n_sims"),
                },
            },
            prefer_hd=False,
            formats=("json",),
        )
        payload["research_snapshot"] = {
            "written": True,
            "as_of": snap.get("as_of"),
            "game_id": snap.get("game_id"),
            "used_in_spread": False,
        }
    except Exception as exc:  # pragma: no cover
        log.debug("immutable research snapshot skipped: %s", exc)
        payload["research_snapshot"] = {"written": False, "used_in_spread": False}
    # Best-effort tracking — never slows / fails the projection path.
    try:
        from src.services.cfb_season_engine.performance_tracking import (
            auto_log_enabled,
            log_projection,
            maybe_auto_log_projection,
        )

        if body.log_projection:
            try:
                logged = log_projection(payload)
                payload["projection_log_id"] = logged.id
                payload["projection_logged"] = True
            except Exception as exc:  # pragma: no cover
                log.warning("explicit projection log failed: %s", exc)
                payload["projection_logged"] = False
        elif auto_log_enabled():
            maybe_auto_log_projection(payload)
            payload["projection_logged"] = "async"
    except Exception as exc:  # pragma: no cover
        log.debug("projection tracking skipped: %s", exc)
    return payload


@router.post("/season-engine/game-preview")
def cfb_season_engine_game_preview(
    body: ProjectGameBody = Body(...),
) -> Dict[str, Any]:
    """Alias for project-game (NFL-style naming convenience)."""
    return cfb_season_engine_project_game(body)


@router.post("/season-engine/projections/log")
def cfb_log_projection(
    body: LogProjectionBody = Body(...),
) -> Dict[str, Any]:
    """Persist a projection for later close/result grading (JSONL + optional DB)."""
    from src.services.cfb_season_engine.performance_tracking import log_projection

    record = log_projection(body.model_dump(exclude_none=True))
    return {"ok": True, "projection": record.to_dict()}


@router.post("/season-engine/projections/{projection_id}/close")
def cfb_projection_close(
    projection_id: str = Path(..., min_length=8, max_length=64),
    body: CloseBody = Body(...),
) -> Dict[str, Any]:
    """Record closing spread/total and compute CLV."""
    from src.services.cfb_season_engine.performance_tracking import record_close

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


@router.post("/season-engine/projections/{projection_id}/result")
def cfb_projection_result(
    projection_id: str = Path(..., min_length=8, max_length=64),
    body: ResultBody = Body(...),
) -> Dict[str, Any]:
    """Record final score and grade ATS / O/U / SU.

    Set ``apply_inseason=true`` to also feed the in-season rating foundation.
    """
    from src.services.cfb_season_engine.performance_tracking import record_result

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
    if body.apply_inseason:
        try:
            from src.services.cfb_season_engine.in_season_update import state_summary

            out["in_season"] = {
                "home": state_summary(team=record.home_team),
                "away": state_summary(team=record.away_team),
            }
        except Exception as exc:  # pragma: no cover
            out["in_season_error"] = str(exc)
    return out


@router.post("/season-engine/in-season/ingest-result")
def cfb_inseason_ingest(
    body: InSeasonIngestBody = Body(...),
) -> Dict[str, Any]:
    """Apply one completed game to the in-season rating foundation."""
    from src.services.cfb_season_engine.in_season_update import ingest_result

    return ingest_result(
        home_team=body.home_team,
        away_team=body.away_team,
        home_score=body.home_score,
        away_score=body.away_score,
        week=body.week,
        season=body.season,
        model_spread_home=body.model_spread_home,
        expected_home_score=body.expected_home_score,
        expected_away_score=body.expected_away_score,
        game_id=body.game_id or "",
        projection_id=body.projection_id or "",
        source=body.source,
    )


@router.get("/season-engine/in-season/state")
def cfb_inseason_state() -> Dict[str, Any]:
    """Inspect preseason baseline vs current in-season deltas."""
    from src.services.cfb_season_engine.in_season_update import state_summary

    return state_summary()


@router.get("/season-engine/in-season/team/{team}")
def cfb_inseason_team(
    team: str = Path(..., min_length=2, max_length=8),
) -> Dict[str, Any]:
    from src.services.cfb_season_engine.in_season_update import state_summary

    return state_summary(team=team)


@router.post("/season-engine/in-season/reset")
def cfb_inseason_reset(
    body: InSeasonResetBody = Body(...),
) -> Dict[str, Any]:
    """Clear in-season deltas (back to preseason priors). Requires confirm=true."""
    if not body.confirm:
        return {"ok": False, "error": "Pass confirm=true to reset in-season state"}
    from src.services.cfb_season_engine.in_season_update import reset_state

    st = reset_state(season=body.season)
    return {"ok": True, "state": st.to_dict()}


@router.get("/season-engine/performance")
def cfb_performance_summary(
    limit: int = Query(200, ge=1, le=500),
    engine_version: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """Recent performance summary: record, avg error, CLV."""
    try:
        from src.services.cfb_season_engine.performance_tracking import (
            documentation,
            performance_summary,
        )

        payload = performance_summary(limit=limit, engine_version=engine_version)
        payload["tracking"] = documentation()
        return payload
    except Exception as exc:
        log.exception("cfb performance summary failed: %s", exc)
        return {
            "ok": False,
            "error": f"performance summary failed: {exc}",
            "n_logged": 0,
            "n_with_close": 0,
            "n_with_result": 0,
        }


@router.post("/season-engine/simulate")
def cfb_season_engine_simulate(
    body: Optional[SimulateBody] = Body(None),
    season: int = Query(2026, ge=2010, le=2100),
    n_sims: int = Query(200, ge=1, le=2000),
    seed: int = Query(2026),
    demo: bool = Query(True),
    as_of_week: int = Query(1, ge=1, le=20),
) -> Dict[str, Any]:
    """Path-coherent season sim (wins dist, week sample, ranking). Prefer CLI for heavy runs."""
    from src.services.cfb_season_engine import (
        resolve_season_universe,
        season_sim_to_dict,
        simulate_full_season,
    )

    cfg = body or SimulateBody(
        season=season, n_sims=n_sims, seed=seed, demo=demo, as_of_week=as_of_week
    )
    universe, meta = resolve_season_universe(
        season=cfg.season,
        as_of_week=cfg.as_of_week,
        demo=cfg.demo,
        session=None,
    )
    result = simulate_full_season(
        universe, n_sims=cfg.n_sims, seed=cfg.seed
    )
    payload = season_sim_to_dict(result)
    payload["ok"] = True
    payload["mode"] = meta.get("mode")
    payload["skeleton"] = False
    payload["season_paths"] = True
    return payload
