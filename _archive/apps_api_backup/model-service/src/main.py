from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.celery_app import celery_app, celery_healthcheck
from src.db import engine
from src.routes import edge_board_router

APP_NAME: str = os.getenv("APP_NAME", "kosedge")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger(APP_NAME)

TASK_PULL_ODDS_SNAPSHOT = "src.tasks.pull_odds_snapshot"


def _parse_cors_origins(raw: str) -> List[str]:
    raw = (raw or "").strip()
    if not raw:
        return []
    return [o.strip() for o in raw.split(",") if o.strip()]


app = FastAPI(
    title="KosEdge Model Service",
    version=os.getenv("APP_VERSION", "0.1.0"),
)

# Routers
app.include_router(edge_board_router)

# CORS (single middleware registration)
origins = _parse_cors_origins(os.getenv("CORS_ORIGINS", ""))
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],  # tighten in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "service": APP_NAME}


@app.get("/health/db")
def health_db() -> Dict[str, Any]:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except SQLAlchemyError as e:
        log.exception("DB healthcheck failed")
        raise HTTPException(status_code=503, detail=f"db_unavailable: {e}")


@app.get("/health/celery")
def health_celery() -> Dict[str, Any]:
    return {"status": "ok", "celery": celery_healthcheck()}


@app.get("/api/odds/snapshots")
def get_odds_snapshots(
    limit: int = Query(10, ge=1, le=200),
    offset: int = Query(0, ge=0),
    include_payload: bool = Query(False),
) -> List[Dict[str, Any]]:
    cols = "id, source, created_at"
    if include_payload:
        cols += ", payload"

    sql = text(
        f"""
        SELECT {cols}
        FROM odds_snapshots
        ORDER BY created_at DESC
        LIMIT :limit
        OFFSET :offset
        """
    )

    try:
        with engine.connect() as conn:
            rows = conn.execute(sql, {"limit": limit, "offset": offset}).fetchall()
        return [dict(r._mapping) for r in rows]
    except SQLAlchemyError as e:
        log.exception("Failed to query odds_snapshots")
        raise HTTPException(status_code=500, detail=f"db_error: {e}")


@app.post("/api/jobs/pull-odds-snapshot")
def job_pull_odds_snapshot() -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(TASK_PULL_ODDS_SNAPSHOT)
        return {"task_id": async_result.id, "task_name": TASK_PULL_ODDS_SNAPSHOT}
    except Exception as e:
        log.exception("Failed to enqueue pull-odds-snapshot")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.get("/api/jobs/{task_id}")
def job_status(task_id: str) -> Dict[str, Any]:
    res = celery_app.AsyncResult(task_id)
    payload: Dict[str, Any] = {"task_id": task_id, "state": res.state}

    if res.successful():
        payload["result"] = res.result
    elif res.failed():
        payload["error"] = str(res.result)

    return payload