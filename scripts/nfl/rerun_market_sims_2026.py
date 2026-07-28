"""Re-run NFL market simulations across the full 2026 schedule so persisted
nfl_market_projections pick up: the fixed team-strength priors lookup, and
the consolidated (post ghost-team-merge) odds data.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "model-service"))
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge")

from src import tasks as tasks_module  # noqa: E402

result = tasks_module.backfill_nfl_historical_projections.run(
    start_date="2026-01-03",
    # Week 17-18 games of the 2026 season are played in early January 2027
    # and get mislabeled season_year=2027 at ingestion time (see
    # simulate_2026_season.py's schedule query note) -- extend into next
    # January so those games' projections get refreshed too.
    end_date="2027-01-15",
    simulations=4000,
    model_version=tasks_module.DEFAULT_NFL_MODEL_VERSION,
    kickoff_buffer_minutes=30,
)
print(result)
