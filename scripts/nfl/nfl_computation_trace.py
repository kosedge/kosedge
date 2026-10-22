"""End-to-end NFL computation trace (t4141u).

schedule → teams → players/injuries → market → model → sim → fair lines → Edge Board

Each hop records input fingerprints, output fingerprints, missing flags, and
record_class. Reconstructions are labelled RETROSPECTIVE. Prospective hops
that lack a stored pregame snapshot stay BLOCKED rather than inventing one.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence

SCHEMA = "nfl-computation-trace/v1"
HOPS = (
    "schedule",
    "teams",
    "players",
    "injuries",
    "market",
    "model",
    "sim",
    "fair_lines",
    "edge_board",
)

VALID_RECORD_CLASS = {"PROSPECTIVE", "PROSPECTIVE-RESEARCH", "RETROSPECTIVE"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def hop(
    name: str,
    *,
    status: str,
    record_class: str,
    inputs: Optional[Sequence[Mapping[str, Any]]] = None,
    outputs: Optional[Sequence[Mapping[str, Any]]] = None,
    flags: Optional[Sequence[str]] = None,
    detail: str = "",
) -> Dict[str, Any]:
    if name not in HOPS:
        raise ValueError(f"unknown hop {name!r}")
    if record_class not in VALID_RECORD_CLASS:
        raise ValueError(f"unknown record_class {record_class!r}")
    if status not in {"ok", "missing", "blocked", "skipped", "retrospective"}:
        raise ValueError(f"unknown hop status {status!r}")
    return {
        "hop": name,
        "status": status,
        "record_class": record_class,
        "inputs": list(inputs or []),
        "outputs": list(outputs or []),
        "flags": list(flags or []),
        "detail": detail,
    }


def build_trace(
    *,
    season: int,
    week: int,
    hops: Sequence[Mapping[str, Any]],
    record_class: str,
    capture_ts: Optional[str] = None,
    extra: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    if record_class not in VALID_RECORD_CLASS:
        raise ValueError(f"unknown record_class {record_class!r}")
    seen = [str(h.get("hop")) for h in hops]
    missing_hops = [name for name in HOPS if name not in seen]
    blocked = [
        h
        for h in hops
        if str(h.get("status")) in {"blocked", "missing"}
        or "BLOCKED" in {str(f) for f in (h.get("flags") or [])}
    ]
    status = "BLOCKED" if blocked or missing_hops else "COMPLETE"
    doc: Dict[str, Any] = {
        "schema": SCHEMA,
        "season": int(season),
        "week": int(week),
        "record_class": record_class,
        "capture_ts": capture_ts or utc_now(),
        "status": status,
        "hops": list(hops),
        "missing_hops": missing_hops,
        "never_silent_default": True,
        "fabricated_pregame": False,
        "note": (
            "A hop without a stored pregame snapshot is RETROSPECTIVE or BLOCKED. "
            "Do not back-write a prospective B0 after kickoff."
        ),
    }
    if extra:
        doc.update(dict(extra))
    return doc


def empty_in_season_trace(
    *,
    season: int,
    week: int,
    record_class: str,
    reason: str,
) -> Dict[str, Any]:
    """Honest skeleton when local inputs are not ready — no invented hops."""
    hops = [
        hop(
            name,
            status="missing",
            record_class=record_class,
            flags=["NOT_BUILT"],
            detail=reason,
        )
        for name in HOPS
    ]
    return build_trace(
        season=season, week=week, hops=hops, record_class=record_class
    )
