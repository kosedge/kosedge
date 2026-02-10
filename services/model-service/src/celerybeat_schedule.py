from celery.schedules import crontab

beat_schedule = {
    "pull-odds-every-30-min": {
        "task": "src.tasks.pull_odds_snapshot",
        "schedule": crontab(minute="*/30", hour="7-21"),
    },
    "pull-odds-hourly-late": {
        "task": "src.tasks.pull_odds_snapshot",
        "schedule": crontab(minute=0, hour="22-23"),
    },
}
