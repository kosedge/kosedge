"""book_id + units policy for The Book."""

from __future__ import annotations

import hashlib
from typing import Optional


def units_for_type(book_type: str) -> float:
    """play → 1; lean/pass → 0. Leans excluded from unit ROI via units=0."""
    token = str(book_type or "").strip().lower()
    if token == "play":
        return 1.0
    if token in {"lean", "pass"}:
        return 0.0
    raise ValueError(f"unsupported book type for units: {book_type!r}")


def make_book_id(
    *,
    sport: str,
    game_id: str,
    market: str,
    side: str,
    posted_at: str,
    type: str,
) -> str:
    """Idempotent id on (sport, game_id, market, side, posted_at, type)."""
    parts = [
        str(sport).strip().lower(),
        str(game_id).strip(),
        str(market).strip().lower(),
        str(side).strip().lower(),
        str(posted_at).strip(),
        str(type).strip().lower(),
    ]
    if not all(parts):
        raise ValueError("all book_id components required")
    raw = "|".join(parts)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    return f"book_{digest}"


def normalize_posted_at(ts: str) -> str:
    """Normalize posted_at for stable idempotency (second precision, Z)."""
    s = str(ts).strip()
    if not s:
        raise ValueError("posted_at empty")
    if s.endswith("+00:00"):
        s = s[:-6] + "Z"
    if len(s) == 19 and "T" in s:
        s = s + "Z"
    # Truncate fractional seconds for idempotent keying.
    if "." in s and s.endswith("Z"):
        head, _ = s.split(".", 1)
        s = head + "Z"
    return s
