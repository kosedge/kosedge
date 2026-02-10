import os
from celery import Celery
from celery.schedules import crontab

# Broker / backend
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# If you don't set a result backend, job status will still work,
# but returning results is limited. This enables full status + result retrieval.
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

app = Celery(
    "kosedge",
    broker=REDIS_URL,
    backend=RESULT_BACKEND,
    include=["src.tasks"],
)

# Optional but nice: sane defaults
app.conf.update(
    task_track_started=True,
    result_expires=3600,  # 1 hour
    timezone="UTC",
)

# Beat schedule (optional)
# If you already have beat config elsewhere, keep yours and remove this block.
app.conf.beat_schedule = {
    "refresh-odds-every-5-min": {
        "task": "src.tasks.refresh_odds",
        "schedule": crontab(minute="*/5"),
    },
}