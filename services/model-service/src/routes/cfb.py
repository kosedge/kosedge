"""CFB model routes — hierarchical season engine foundation (additive)."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Query
from pydantic import BaseModel, Field

log = logging.getLogger("kosedge.cfb")

router = APIRouter(prefix="/cfb", tags=["cfb-model"])


class ProjectGameBody(BaseModel):
    home_team: str = Field(..., min_length=2, max_length=8)
    away_team: str = Field(..., min_length=2, max_length=8)
    season: int = Field(2026, ge=2010, le=2100)
    week: int = Field(1, ge=1, le=20)
    neutral_site: bool = False
    demo: bool = True


class SimulateBody(BaseModel):
    season: int = Field(2026, ge=2010, le=2100)
    n_sims: int = Field(25, ge=1, le=500)
    seed: int = 2026
    demo: bool = True
    as_of_week: int = Field(1, ge=1, le=20)


@router.get("/season-engine/status")
def cfb_season_engine_status(
    season: int = Query(2026, ge=2010, le=2100),
    as_of_week: int = Query(1, ge=1, le=20),
    demo: bool = Query(True, description="Packaged universe probe (default)"),
) -> Dict[str, Any]:
    """Describe CFB hierarchical engine layers, data sources, solid vs approximate."""
    from src.services.cfb_season_engine import engine_status_payload

    return engine_status_payload(season=season, as_of_week=as_of_week, demo=demo)


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
    return payload


@router.post("/season-engine/game-preview")
def cfb_season_engine_game_preview(
    body: ProjectGameBody = Body(...),
) -> Dict[str, Any]:
    """Alias for project-game (NFL-style naming convenience)."""
    return cfb_season_engine_project_game(body)


@router.post("/season-engine/simulate")
def cfb_season_engine_simulate(
    body: Optional[SimulateBody] = Body(None),
    season: int = Query(2026, ge=2010, le=2100),
    n_sims: int = Query(25, ge=1, le=500),
    seed: int = Query(2026),
    demo: bool = Query(True),
    as_of_week: int = Query(1, ge=1, le=20),
) -> Dict[str, Any]:
    """Skeleton path-coherent season sim (team W/L). Prefer CLI for heavy runs."""
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
    payload["skeleton"] = True
    return payload
