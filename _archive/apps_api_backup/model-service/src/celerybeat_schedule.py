"""
Celery Beat schedule for KosEdge.

- Single source of truth for periodic jobs
- Task names must match @celery_app.task(name="...")
- Environment overrides for easy tuning
"""

from __future__ import annotations

import os
from typing import Any, Dict

from celery.schedules import crontab

TASK_PULL_ODDS_SNAPSHOT = os.getenv("TASK_PULL_ODDS_SNAPSHOT", "src.tasks.pull_odds_snapshot")

ACTIVE_START_HOUR = os.getenv("ODDS_PULL_ACTIVE_START_HOUR", "7")   # 7am
ACTIVE_END_HOUR = os.getenv("ODDS_PULL_ACTIVE_END_HOUR", "21")      # 9pm
LATE_START_HOUR = os.getenv("ODDS_PULL_LATE_START_HOUR", "22")      # 10pm
LATE_END_HOUR = os.getenv("ODDS_PULL_LATE_END_HOUR", "23")          # 11pm

ACTIVE_MINUTE_PATTERN = os.getenv("ODDS_PULL_ACTIVE_MINUTE_PATTERN", "*/30")
LATE_MINUTE = os.getenv("ODDS_PULL_LATE_MINUTE", "0")

ODDS_QUEUE = os.getenv("CELERY_ODDS_QUEUE", "odds")

beat_schedule: Dict[str, Dict[str, Any]] = {
    "pull-odds-every-30-min-active": {
        "task": TASK_PULL_ODDS_SNAPSHOT,
        "schedule": crontab(
            minute=ACTIVE_MINUTE_PATTERN,
            hour=f"{ACTIVE_START_HOUR}-{ACTIVE_END_HOUR}",
        ),
        "options": {"queue": ODDS_QUEUE},
    },
    "pull-odds-hourly-late": {
        "task": TASK_PULL_ODDS_SNAPSHOT,
        "schedule": crontab(
            minute=LATE_MINUTE,
            hour=f"{LATE_START_HOUR}-{LATE_END_HOUR}",
        ),
        "options": {"queue": ODDS_QUEUE},
    },
}