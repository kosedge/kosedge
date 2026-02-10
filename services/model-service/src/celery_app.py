import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "kosedge",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.timezone = "US/Eastern"
celery_app.conf.enable_utc = True

# schedule loaded below
from .celerybeat_schedule import beat_schedule  # noqa: E402
celery_app.conf.beat_schedule = beat_schedule