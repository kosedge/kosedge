from fastapi import FastAPI, Query, HTTPException
from sqlalchemy import text
from src.db import engine

# IMPORTANT: this matches celery_app.py where the Celery instance is named "app"
from src.celery_app import app as celery_app

app = FastAPI(title="KosEdge Model Service")


# ------------------------
# Health check
# ------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


# ------------------------
# Odds snapshots API
# ------------------------
@app.get("/api/odds/snapshots")
def get_odds_snapshots(
    limit: int = Query(10, ge=1, le=200),
    offset: int = Query(0, ge=0),
    include_payload: bool = Query(False),
):
    cols = "id, source, created_at"
    if include_payload:
        cols += ", payload"

    sql = text(f"""
        SELECT {cols}
        FROM odds_snapshots
        ORDER BY created_at DESC
        LIMIT :limit
        OFFSET :offset
    """)

    with engine.connect() as conn:
        result = conn.execute(sql, {"limit": limit, "offset": offset})
        return [dict(row._mapping) for row in result]


# ------------------------
# Jobs API (Celery triggers)
# ------------------------

TASK_REFRESH_ODDS = "src.tasks.refresh_odds"
TASK_RUN_MODEL = "src.tasks.run_model_pipeline"


@app.post("/api/jobs/refresh-odds")
def job_refresh_odds():
    """
    Enqueue the refresh_odds Celery task.
    Returns task_id for polling.
    """
    try:
        async_result = celery_app.send_task(TASK_REFRESH_ODDS)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enqueue task: {e}")

    return {"task_id": async_result.id, "task_name": TASK_REFRESH_ODDS}


@app.post("/api/jobs/run-model")
def job_run_model():
    """
    Enqueue the run_model_pipeline Celery task.
    Returns task_id for polling.
    """
    try:
        async_result = celery_app.send_task(TASK_RUN_MODEL)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enqueue task: {e}")

    return {"task_id": async_result.id, "task_name": TASK_RUN_MODEL}


@app.get("/api/jobs/{task_id}")
def job_status(task_id: str):
    """
    Get Celery job status + result (if backend is configured).
    """
    res = celery_app.AsyncResult(task_id)

    payload = {
        "task_id": task_id,
        "state": res.state,
    }

    # If result backend is enabled, these will work:
    if res.successful():
        payload["result"] = res.result
    elif res.failed():
        payload["error"] = str(res.result)

    return payload