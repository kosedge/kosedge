"""Timestamp roles for PART B close. Client receive time is never a close."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional


def parse_utc(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def require_provider_server_ts(
    *,
    provider_server_ts: Any,
    client_received_at: Any = None,
) -> Optional[datetime]:
    """Provider HTTP / API server stamp only. Client receive is ignored."""
    del client_received_at  # not a close source
    return parse_utc(provider_server_ts)


def market_last_update_status(last_update: Any) -> str:
    """Missing last_update is UNKNOWN — not filled, not a close."""
    if parse_utc(last_update) is None:
        return "UNKNOWN"
    return "PRESENT"
