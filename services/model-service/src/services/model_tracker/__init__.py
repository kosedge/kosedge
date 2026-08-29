"""Model performance + pick/unit tracker (sport-agnostic).

PLAY = 1 unit; LEAN = 0 units (hit-rate only). Complements proof_projections.
"""

from __future__ import annotations

from src.services.model_tracker.core import (
    TRACKER_VERSION,
    close_pick,
    documentation,
    export_picks,
    get_pick,
    grade_pick,
    list_picks,
    log_pick,
    sports_status,
    status_payload,
    summary,
    units_for_tag,
)
from src.services.model_tracker.grading import (
    american_odds_profit,
    compute_clv,
    grade_market,
    grade_to_units,
)

__all__ = [
    "TRACKER_VERSION",
    "american_odds_profit",
    "close_pick",
    "compute_clv",
    "documentation",
    "export_picks",
    "get_pick",
    "grade_market",
    "grade_pick",
    "grade_to_units",
    "list_picks",
    "log_pick",
    "sports_status",
    "status_payload",
    "summary",
    "units_for_tag",
]
