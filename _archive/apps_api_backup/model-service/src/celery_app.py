# services/model-service/src/celery_app.py
from __future__ import annotations

import os
from typing import Any, Dict

from celery import Celery
from kombu import Exchange, Queue


def _env_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None or not v.strip():
        return default
    try:
        return int(v)
    except ValueError:
        return default


# ----------------------------
# Identity
# ----------------------------
APP_NAME: str = os.getenv("CELERY_APP_NAME", os.getenv("APP_NAME", "kosedge"))

# ----------------------------
# Broker / Backend
# ----------------------------
REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
BROKER_URL: str = os.getenv("CELERY_BROKER_URL", REDIS_URL)
RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

# ----------------------------
# Time
# ----------------------------
TIMEZONE: str = os.getenv("CELERY_TIMEZONE", os.getenv("TZ", "US/Eastern"))
ENABLE_UTC: bool = _env_bool("CELERY_ENABLE_UTC", True)

# ----------------------------
# Reliability / scaling knobs
# ----------------------------
TASK_ACKS_LATE: bool = _env_bool("CELERY_TASK_ACKS_LATE", True)
TASK_TRACK_STARTED: bool = _env_bool("CELERY_TASK_TRACK_STARTED", True)

WORKER_PREFETCH_MULTIPLIER: int = _env_int("CELERY_WORKER_PREFETCH_MULTIPLIER", 1)
WORKER_MAX_TASKS_PER_CHILD: int = _env_int("CELERY_WORKER_MAX_TASKS_PER_CHILD", 200)

BROKER_CONNECTION_RETRY_ON_STARTUP: bool = _env_bool(
    "CELERY_BROKER_RETRY_ON_STARTUP",
    True,
)

# Queues (names are env-overridable)
QUEUE_DEFAULT = os.getenv("CELERY_DEFAULT_QUEUE", "default")
QUEUE_ODDS = os.getenv("CELERY_ODDS_QUEUE", "odds")
QUEUE_MODELS = os.getenv("CELERY_MODELS_QUEUE", "models")

# ----------------------------
# App
# ----------------------------
celery_app: Celery = Celery(
    APP_NAME,
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=["src.tasks"],  # deterministic discovery
)

# Exchanges/Queues (explicit is “reviewer-friendly”)
ex_default = Exchange(QUEUE_DEFAULT, type="direct")
ex_odds = Exchange(QUEUE_ODDS, type="direct")
ex_models = Exchange(QUEUE_MODELS, type="direct")

celery_app.conf.update(
    # Timezone
    timezone=TIMEZONE,
    enable_utc=ENABLE_UTC,

    # Celery 6+ startup behavior (removes your warning when you set it)
    broker_connection_retry_on_startup=BROKER_CONNECTION_RETRY_ON_STARTUP,

    # Execution behavior
    task_acks_late=TASK_ACKS_LATE,
    task_track_started=TASK_TRACK_STARTED,
    worker_prefetch_multiplier=WORKER_PREFETCH_MULTIPLIER,
    worker_max_tasks_per_child=WORKER_MAX_TASKS_PER_CHILD,

    # JSON-only (safe)
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Results retention
    result_expires=int(os.getenv("CELERY_RESULT_EXPIRES_SECONDS", str(60 * 60 * 6))),

    # Broker safety (Redis visibility timeout)
    broker_transport_options={
        "visibility_timeout": int(os.getenv("CELERY_VISIBILITY_TIMEOUT", str(60 * 60))),
    },

    # Defaults reviewers expect
    task_default_queue=QUEUE_DEFAULT,
    task_default_exchange=QUEUE_DEFAULT,
    task_default_exchange_type="direct",
    task_default_routing_key=QUEUE_DEFAULT,

    # Explicit queues (enterprise clarity)
    task_queues=(
        Queue(QUEUE_DEFAULT, ex_default, routing_key=QUEUE_DEFAULT),
        Queue(QUEUE_ODDS, ex_odds, routing_key=QUEUE_ODDS),
        Queue(QUEUE_MODELS, ex_models, routing_key=QUEUE_MODELS),
    ),
)

# Route only tasks that exist TODAY (avoid “phantom routes”)
celery_app.conf.task_routes = {
    "src.tasks.pull_odds_snapshot": {"queue": QUEUE_ODDS, "routing_key": QUEUE_ODDS},
    # Enable once implemented:
    # "src.tasks.run_model_pipeline": {"queue": QUEUE_MODELS, "routing_key": QUEUE_MODELS},
}

# Beat schedule (optional; beat container can boot even if file missing)
try:
    from src.celerybeat_schedule import beat_schedule  # type: ignore

    celery_app.conf.beat_schedule = beat_schedule
except Exception:
    celery_app.conf.beat_schedule = {}


def celery_healthcheck() -> Dict[str, Any]:
    return {
        "app": APP_NAME,
        "broker": BROKER_URL,
        "backend": RESULT_BACKEND,
        "timezone": TIMEZONE,
        "enable_utc": ENABLE_UTC,
        "acks_late": TASK_ACKS_LATE,
        "track_started": TASK_TRACK_STARTED,
        "prefetch_multiplier": WORKER_PREFETCH_MULTIPLIER,
        "max_tasks_per_child": WORKER_MAX_TASKS_PER_CHILD,
        "broker_retry_on_startup": BROKER_CONNECTION_RETRY_ON_STARTUP,
        "queues": {
            "default": QUEUE_DEFAULT,
            "odds": QUEUE_ODDS,
            "models": QUEUE_MODELS,
        },
    }