# services/model-service/src/celery_app.py

import os
from celery import Celery

# -------------------------------------------------
# Core App Identity
# -------------------------------------------------
APP_NAME = os.getenv("CELERY_APP_NAME", "kosedge-model-service")

# -------------------------------------------------
# Broker / Backend (Redis)
# -------------------------------------------------
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

# -------------------------------------------------
# Time & Execution Settings
# -------------------------------------------------
TIMEZONE = os.getenv("CELERY_TIMEZONE", "US/Eastern")
ENABLE_UTC = os.getenv("CELERY_ENABLE_UTC", "true").lower() == "true"

# -------------------------------------------------
# Reliability / Scaling Knobs
# -------------------------------------------------
TASK_ACKS_LATE = os.getenv("CELERY_TASK_ACKS_LATE", "true").lower() == "true"
TASK_TRACK_STARTED = os.getenv("CELERY_TASK_TRACK_STARTED", "true").lower() == "true"
WORKER_PREFETCH_MULTIPLIER = int(os.getenv("CELERY_WORKER_PREFETCH_MULTIPLIER", "1"))
TASK_ALWAYS_EAGER = os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true"

# -------------------------------------------------
# Create Celery App
# -------------------------------------------------
celery_app = Celery(
    APP_NAME,
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=[
        "src.tasks",  # explicit task discovery (enterprise-safe)
    ],
)

# -------------------------------------------------
# Celery Configuration
# -------------------------------------------------
celery_app.conf.update(
    timezone=TIMEZONE,
    enable_utc=ENABLE_UTC,

    # Execution guarantees
    task_acks_late=TASK_ACKS_LATE,
    task_track_started=TASK_TRACK_STARTED,
    worker_prefetch_multiplier=WORKER_PREFETCH_MULTIPLIER,
    task_always_eager=TASK_ALWAYS_EAGER,

    # Serialization (safe + fast)
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Result behavior
    result_expires=60 * 60 * 6,  # 6 hours
)

# -------------------------------------------------
# Celery Beat Schedule (Periodic Jobs)
# -------------------------------------------------
try:
    from src.celerybeat_schedule import beat_schedule

    celery_app.conf.beat_schedule = beat_schedule
except ImportError:
    # Allows worker-only containers to boot cleanly
    celery_app.conf.beat_schedule = {}

# -------------------------------------------------
# Optional: Named Queues (future scaling)
# -------------------------------------------------
celery_app.conf.task_default_queue = "default"
celery_app.conf.task_routes = {
    "src.tasks.pull_odds_snapshot": {"queue": "odds"},
    "src.tasks.run_model_pipeline": {"queue": "models"},
}

# -------------------------------------------------
# Health Hook (used by FastAPI / monitoring)
# -------------------------------------------------
def celery_healthcheck() -> dict:
    return {
        "app": APP_NAME,
        "broker": BROKER_URL,
        "backend": RESULT_BACKEND,
        "timezone": TIMEZONE,
    }