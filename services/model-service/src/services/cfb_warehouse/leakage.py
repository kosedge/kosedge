"""Zero-leakage contract for CFB historical features and backtests.

Rule (v1, sticky): predicting game G may only use information with
``available_at`` **strictly before kickoff of G**.

Fallbacks when kickoff is missing (same spirit, never looser):
1. ``available_at`` date < ``game_date`` (calendar day of G)
2. ``feature_week`` < ``game_week`` (week-level, same as NFL KAV)

Forbidden as feature inputs (not enforced by type system — ops + tests):
- final-season ratings for season S used inside season S
- end-of-year SOS
- post-hoc recruiting revisions
- "what the freshman became"
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Iterable, Mapping, Optional, Sequence

LEAKAGE_RULE = "strictly_before_kickoff"

ERA_TAGS = (
    "pre-2002",
    "2002-09",
    "2010-17",
    "2018-21",
    "2022-present",
)


def era_tag(season: int) -> str:
    year = int(season)
    if year < 2002:
        return "pre-2002"
    if year <= 2009:
        return "2002-09"
    if year <= 2017:
        return "2010-17"
    if year <= 2021:
        return "2018-21"
    return "2022-present"


def _as_datetime(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    if isinstance(value, date) and not isinstance(value, datetime):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        try:
            return datetime.strptime(text[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def is_available_before_kickoff(
    *,
    available_at: Any,
    kickoff: Any = None,
    game_date: Any = None,
    feature_week: Optional[int] = None,
    game_week: Optional[int] = None,
) -> bool:
    """Return True iff ``available_at`` is legal for predicting game G."""
    avail = _as_datetime(available_at)
    kick = _as_datetime(kickoff)
    if avail is not None and kick is not None:
        return avail < kick
    gdate = _as_datetime(game_date)
    if avail is not None and gdate is not None:
        # Calendar-day fallback: feature must be from a strictly earlier day.
        return avail.date() < gdate.date()
    if feature_week is not None and game_week is not None:
        return int(feature_week) < int(game_week)
    # Missing timestamps: cannot prove safety → not available.
    return False


def assert_available_before_kickoff(
    *,
    available_at: Any,
    kickoff: Any = None,
    game_date: Any = None,
    feature_week: Optional[int] = None,
    game_week: Optional[int] = None,
    feature_name: str = "feature",
) -> None:
    """Raise if a feature would leak future information into game G."""
    if is_available_before_kickoff(
        available_at=available_at,
        kickoff=kickoff,
        game_date=game_date,
        feature_week=feature_week,
        game_week=game_week,
    ):
        return
    raise ValueError(
        f"CFB leakage ({LEAKAGE_RULE}): {feature_name} available_at={available_at!r} "
        f"is not strictly before kickoff={kickoff!r} "
        f"(game_date={game_date!r} feature_week={feature_week} game_week={game_week})"
    )


def filter_available(
    rows: Iterable[Mapping[str, Any]],
    *,
    kickoff: Any = None,
    game_date: Any = None,
    game_week: Optional[int] = None,
    available_at_key: str = "available_at",
    feature_week_key: str = "feature_week",
) -> list[dict[str, Any]]:
    """Drop rows that are not strictly available before G (null, do not invent)."""
    kept: list[dict[str, Any]] = []
    for row in rows:
        if is_available_before_kickoff(
            available_at=row.get(available_at_key),
            kickoff=kickoff,
            game_date=game_date,
            feature_week=row.get(feature_week_key),
            game_week=game_week,
        ):
            kept.append(dict(row))
    return kept


def documentation() -> dict[str, Any]:
    return {
        "rule": LEAKAGE_RULE,
        "fallbacks": ["available_at.date < game_date", "feature_week < game_week"],
        "unsafe_if_unprovable": True,
        "era_tags": list(ERA_TAGS),
        "forbidden": [
            "final-season ratings for the same season",
            "end-of-year SOS",
            "post-hoc recruiting revisions",
            "what the freshman became",
        ],
    }
