from datetime import datetime, timezone

from sqlalchemy import text, bindparam
from sqlalchemy.dialects.postgresql import JSONB

from src.celery_app import app
from src.db import engine


@app.task(name="src.tasks.refresh_odds")
def refresh_odds():
    """
    Demo refresh task that writes a snapshot row.
    """
    payload = {
        "ok": True,
        "ts": datetime.now(timezone.utc).isoformat(),
        "note": "demo odds snapshot from refresh_odds",
    }

    sql = (
        text("""
            INSERT INTO odds_snapshots (source, payload)
            VALUES (:source, :payload)
            RETURNING id
        """)
        .bindparams(bindparam("payload", type_=JSONB))
    )

    with engine.begin() as conn:
        new_id = conn.execute(sql, {"source": "odds_refresh", "payload": payload}).scalar_one()

    return {"inserted_id": new_id, "payload": payload}


@app.task(name="src.tasks.run_model_pipeline")
def run_model_pipeline():
    """
    Placeholder pipeline task.
    """
    return {"ok": True, "ts": datetime.now(timezone.utc).isoformat(), "note": "run_model_pipeline placeholder"}