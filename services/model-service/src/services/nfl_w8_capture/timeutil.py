"""UTC / ET helpers for W8 capture. No week-number proofs."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from src.services.nfl_w8_capture.constants import ET, MIN_LEAD_MINUTES


def parse_utc(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def to_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def et_to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ET)
    return dt.astimezone(timezone.utc)


def seal_deadline_utc(kickoff_utc: datetime, *, min_lead_minutes: int = MIN_LEAD_MINUTES) -> datetime:
    return kickoff_utc - timedelta(minutes=int(min_lead_minutes))


def is_late(
    as_of_utc: datetime,
    kickoff_utc: datetime,
    *,
    min_lead_minutes: int = MIN_LEAD_MINUTES,
) -> bool:
    return as_of_utc >= seal_deadline_utc(kickoff_utc, min_lead_minutes=min_lead_minutes)
