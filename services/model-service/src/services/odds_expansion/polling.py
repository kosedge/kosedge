"""Polling tiers — do not use game-day rate on dormant far-future.

Bulk ``/odds`` is already one credit per sport. These tiers gate *extra*
per-event fetches (catalog backfill, movement boost), not the bulk pull.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal, Optional
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

PollingTier = Literal["far_future", "d7_plus", "d1_7", "game_day", "final_hours"]
Cadence = Literal["hourly", "overnight", "movement"]

POLLING_TIERS: tuple[PollingTier, ...] = (
    "far_future",
    "d7_plus",
    "d1_7",
    "game_day",
    "final_hours",
)

# Hours before kickoff that count as "final hours".
FINAL_HOURS = 6.0


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def classify_polling_tier(
    event_start: datetime | None,
    *,
    now: Optional[datetime] = None,
) -> PollingTier:
    if event_start is None:
        return "far_future"
    start = _aware(event_start)
    clock = _aware(now or datetime.now(timezone.utc))
    delta = start - clock
    hours = delta.total_seconds() / 3600.0
    if hours <= FINAL_HOURS:
        return "final_hours"
    start_et = start.astimezone(ET).date()
    now_et = clock.astimezone(ET).date()
    if start_et == now_et:
        return "game_day"
    if delta <= timedelta(days=7):
        return "d1_7"
    if delta <= timedelta(days=14):
        return "d7_plus"
    return "far_future"


def should_refresh_on_cadence(
    tier: PollingTier,
    cadence: Cadence,
    *,
    meaningful_movement: bool = False,
) -> bool:
    """Whether to spend an *extra* per-event odds fetch.

    Overnight (3am) may refresh every tier. Hourly must not poll dormant
    far-future at game-day rate. Movement boost elevates one tier.
    """
    if meaningful_movement:
        # Elevate: far_future → treat as d7_plus; others refresh.
        if tier == "far_future":
            return cadence in {"overnight", "movement"}
        return True

    if cadence == "overnight":
        return True
    if cadence == "movement":
        return tier in {"final_hours", "game_day", "d1_7"}
    # hourly active beat
    if tier in {"final_hours", "game_day", "d1_7"}:
        return True
    if tier == "d7_plus":
        return False  # moderate: overnight only unless movement
    return False  # far_future: overnight only


def tier_counts(tiers: list[PollingTier]) -> dict[str, int]:
    out = {name: 0 for name in POLLING_TIERS}
    for tier in tiers:
        out[tier] = out.get(tier, 0) + 1
    return out
