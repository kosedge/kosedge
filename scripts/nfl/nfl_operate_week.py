"""Resolve the NFL operate week from the canonical schedule.

The web/research pin (`nfl-web-launch-bundle.json`) may stay preseason.
Operate week is independent: last REG week whose every game has already
kicked off as-of UTC. Never invents scores. Never flips the research pin.

Platform Reliability owns cron / Beat enablement. This module only answers
"which finished week is the operate loop allowed to ingest?"
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PACK = ROOT / "apps/web/lib/nfl-canonical-schedule-2026.json"


def parse_kickoff_utc(value: str) -> datetime:
    s = (value or "").strip()
    if s.endswith(".000Z"):
        s = s[:-5] + "Z"
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def load_schedule_pack(path: Path = DEFAULT_PACK) -> Dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"canonical schedule pack missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _reg_games(pack: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for raw in pack.get("games") or []:
        if not isinstance(raw, dict):
            continue
        if str(raw.get("game_type") or "REG").upper() not in {"REG", "REGULAR"}:
            continue
        try:
            week = int(raw.get("week") or 0)
        except (TypeError, ValueError):
            continue
        if week < 1:
            continue
        ko = raw.get("kickoff_utc")
        if not ko:
            continue
        out.append(raw)
    return out


def resolve_operate_week(
    *,
    as_of: Optional[datetime] = None,
    pack: Optional[Dict[str, Any]] = None,
    pack_path: Path = DEFAULT_PACK,
    explicit_week: Optional[int] = None,
) -> Dict[str, Any]:
    """Return the finished REG week and provenance.

    ``explicit_week`` is honored when the caller names a week (CLI ``--week``).
    Week 0 means preseason / no finished REG week — ingest must skip.
    """
    now = as_of or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    else:
        now = now.astimezone(timezone.utc)

    doc = pack if pack is not None else load_schedule_pack(pack_path)
    games = _reg_games(doc)
    by_week: Dict[int, List[Dict[str, Any]]] = {}
    for g in games:
        by_week.setdefault(int(g["week"]), []).append(g)

    finished: List[int] = []
    incomplete: Dict[int, List[str]] = {}
    for week, rows in sorted(by_week.items()):
        pending = []
        for g in rows:
            ko = parse_kickoff_utc(str(g["kickoff_utc"]))
            if ko >= now:
                pending.append(str(g.get("game_id") or f"week-{week}"))
        if pending:
            incomplete[week] = pending
        else:
            finished.append(week)

    inferred = max(finished) if finished else 0
    week = inferred
    week_source = "schedule_last_completed"
    if explicit_week is not None:
        week = int(explicit_week)
        week_source = "cli_explicit"

    next_ko = None
    next_gid = None
    upcoming = []
    for g in games:
        ko = parse_kickoff_utc(str(g["kickoff_utc"]))
        if ko >= now:
            upcoming.append((ko, str(g.get("game_id") or "")))
    if upcoming:
        upcoming.sort()
        next_ko, next_gid = upcoming[0][0].strftime("%Y-%m-%dT%H:%M:%SZ"), upcoming[0][1]

    return {
        "season": int(doc.get("season") or 2026),
        "as_of_utc": now.replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "operate_week": week,
        "inferred_finished_week": inferred,
        "week_source": week_source,
        "in_season": inferred >= 1,
        "research_pin_decoupled": True,
        "schedule_pack_as_of": doc.get("as_of"),
        "schedule_pack_source": doc.get("source"),
        "next_kickoff_utc": next_ko,
        "next_game_id": next_gid,
        "incomplete_weeks": {str(k): v for k, v in incomplete.items()},
        "note": (
            "Operate week is last REG week with every kickoff < as_of. "
            "Research pin may remain preseason. Scores are not inferred here."
        ),
    }
