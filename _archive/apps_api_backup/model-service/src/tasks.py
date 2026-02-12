import logging
from .services.odds_api import fetch_odds
from .celery_app import celery_app

log = logging.getLogger(__name__)

@celery_app.task(name="src.tasks.pull_odds_snapshot")
def pull_odds_snapshot():
    log.info("Running scheduled pull_odds_snapshot")

    data = fetch_odds(
        endpoint="sports/upcoming/odds",
        params={
            "regions": "us",
            "markets": "h2h,spreads,totals",
            "oddsFormat": "american",
        },
    )

    log.info(f"Pulled odds snapshot (len={len(data) if hasattr(data, '__len__') else 'ok'})")
    return True
