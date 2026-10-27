"""Cadence so every REG game has a <=10 min pre-kickoff sample.

Planner + due-window selector. Beat wiring lives in celerybeat_schedule
(`nfl-w8-capture-pre-kickoff-tick`) and does not fetch Odds API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Iterable, Literal, Optional, Sequence

from src.services.nfl_w8_capture.books import PRIMARY_BOOKS
from src.services.nfl_w8_capture.close import CLOSE_MAX_AGE, PRIMARY_K_REQUIRED
from src.services.nfl_w8_capture.timestamps import parse_utc

AlertKind = Literal["missing", "stale", "partial", "unknown", "ok"]

# Suggested offsets before kickoff. The last slot is inside the S=10 window.
SAMPLE_OFFSETS = (
    timedelta(hours=24),
    timedelta(hours=3),
    timedelta(hours=1),
    timedelta(minutes=30),
    timedelta(minutes=15),
    timedelta(minutes=8),
)


@dataclass(frozen=True)
class GameKickoff:
    game_id: str
    kickoff_utc: datetime
    season_type: str = "REG"


@dataclass
class SampleWindow:
    game_id: str
    kickoff_utc: datetime
    sample_at: datetime
    in_close_window: bool


@dataclass
class CoverageAlert:
    game_id: str
    market: str
    kind: AlertKind
    detail: str
    primary_present: int = 0
    primary_stale: int = 0
    primary_missing: int = 0
    primary_unknown: int = 0


@dataclass
class SamplePlan:
    windows: list[SampleWindow] = field(default_factory=list)
    skipped_non_reg: list[str] = field(default_factory=list)


def plan_pre_kickoff_samples(
    games: Sequence[GameKickoff],
    *,
    now_utc: Optional[datetime] = None,
) -> SamplePlan:
    """Emit sample times that guarantee a slot inside (kickoff−S, kickoff]."""
    del now_utc  # planner is kickoff-relative; now is for future dry-run clocks
    plan = SamplePlan()
    for game in games:
        kickoff = parse_utc(game.kickoff_utc)
        if kickoff is None:
            continue
        if str(game.season_type).upper() != "REG":
            plan.skipped_non_reg.append(game.game_id)
            continue
        for offset in SAMPLE_OFFSETS:
            sample_at = kickoff - offset
            plan.windows.append(
                SampleWindow(
                    game_id=game.game_id,
                    kickoff_utc=kickoff,
                    sample_at=sample_at,
                    in_close_window=offset <= CLOSE_MAX_AGE,
                )
            )
    return plan


def due_sample_windows(
    plan: SamplePlan,
    *,
    now_utc: datetime,
    slack: timedelta = timedelta(minutes=2),
) -> list[SampleWindow]:
    """Windows whose sample_at is within ``slack`` of ``now_utc``."""
    now = parse_utc(now_utc)
    if now is None:
        return []
    due: list[SampleWindow] = []
    for window in plan.windows:
        delta = abs((window.sample_at - now).total_seconds())
        if delta <= slack.total_seconds():
            due.append(window)
    return due


def close_window_guaranteed(plan: SamplePlan, game_id: str) -> bool:
    return any(
        window.game_id == game_id and window.in_close_window for window in plan.windows
    )


def review_sample_coverage(
    *,
    game_id: str,
    market: str,
    book_statuses: Iterable[tuple[str, str]],
) -> CoverageAlert:
    """Alert for missing / stale / partial PRIMARY coverage."""
    present = stale = missing = unknown = 0
    for book, status in book_statuses:
        if book not in PRIMARY_BOOKS:
            continue
        token = str(status).upper()
        if token == "PRESENT":
            present += 1
        elif token == "STALE":
            stale += 1
        elif token == "UNKNOWN":
            unknown += 1
        else:
            missing += 1

    if unknown and present < PRIMARY_K_REQUIRED:
        kind: AlertKind = "unknown"
        detail = "one or more PRIMARY last_update UNKNOWN; not a close"
    elif present >= PRIMARY_K_REQUIRED and stale == 0 and missing == 0:
        kind = "ok"
        detail = "all PRIMARY present and non-stale"
    elif present >= PRIMARY_K_REQUIRED and (stale or missing):
        kind = "partial"
        detail = "k>=3 fresh PRIMARY but slate is partial (missing/stale cells remain)"
    elif stale and present == 0:
        kind = "stale"
        detail = "PRIMARY cells stale (age > S=10min)"
    elif missing == len(PRIMARY_BOOKS):
        kind = "missing"
        detail = "all PRIMARY cells MISSING (never impute)"
    else:
        kind = "partial"
        detail = f"k={present} < {PRIMARY_K_REQUIRED} PRIMARY present+non-stale"

    return CoverageAlert(
        game_id=game_id,
        market=market,
        kind=kind,
        detail=detail,
        primary_present=present,
        primary_stale=stale,
        primary_missing=missing,
        primary_unknown=unknown,
    )
