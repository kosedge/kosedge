"""Camp Desk ``is_material_depth`` flags → daily-intel queue (one SoT).

Thinner first cut: model + queue + accept only. No public UI.

Camp prose never auto-writes the depth pack. This module:

1. Scans Camp Desk day files for ``is_material_depth`` team notes.
2. Builds open / overdue tickets (and optional *draft* override stubs).
3. Queues proposals under ``data/ops/nfl-daily-intel/proposed/``.
4. Accept promotes a human-filled override doc into the existing
   ``apply_intel_overrides`` path (pending/ or --write).

Draft stubs may suggest ``injury_status`` / ``competition_status`` when the
flag text + pack name match are unambiguous. They never invent
``depth_order``, new rows, or starter crowns from thin language.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from src.services.nfl_daily_intel import (
    ALLOWED_FIELDS,
    PACK_DEFAULT,
    apply_intel_overrides,
    normalize_override,
)

_SERVICES = Path(__file__).resolve().parent
_REPO = _SERVICES.parents[3]  # services/ → src → model-service → services → repo
CAMP_DESK_DEFAULT = _REPO / "content" / "writers" / "camp-desk-2026"
PROPOSED_DEFAULT = _REPO / "data" / "ops" / "nfl-daily-intel" / "proposed"
PENDING_DEFAULT = _REPO / "data" / "ops" / "nfl-daily-intel" / "pending"
ACCEPTED_LOG_DEFAULT = _REPO / "data" / "ops" / "nfl-daily-intel" / "accepted" / "camp-sot-log.jsonl"

# Flags older than this without accept are overdue (unblock lines this week).
DEFAULT_OVERDUE_HOURS = 24

_OUT_RE = re.compile(
    r"(?i)\b("
    r"season[- ]ending|out for the season|waived/?injured|"
    r"placed on (?:season[- ]ending )?ir|on (?:season[- ]ending )?ir|"
    r"long[- ]term (?:absence|out)|unavailable for the opening"
    r")\b"
)
_NAMED_STARTER_RE = re.compile(
    r"(?i)\b(?:is the named qb1|named (?:the )?qb1|named (?:the )?starter)\b"
)
_OPEN_COMP_RE = re.compile(
    r"(?i)\b(open competition|qb1 remains unresolved|do not crown|"
    r"unresolved between)\b"
)


def _norm_team(abbr: Any) -> str:
    token = str(abbr or "").strip().upper()
    if token in {"LAR", "LA"}:
        return "LA"
    if token == "AZ":
        return "ARI"
    return token


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")


def desk_date_start_utc(desk_date: str) -> datetime:
    """Camp desk dates are Eastern calendar days; use noon ET ≈ 16:00Z."""
    return datetime.fromisoformat(f"{desk_date}T16:00:00+00:00")


def load_camp_day_files(camp_dir: Path) -> List[Dict[str, Any]]:
    files: List[Dict[str, Any]] = []
    if not camp_dir.is_dir():
        return files
    for path in sorted(camp_dir.glob("????-??-??.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload["_path"] = str(path)
            files.append(payload)
    return files


def load_pack(pack_path: Path = PACK_DEFAULT) -> Dict[str, Any]:
    return json.loads(pack_path.read_text(encoding="utf-8"))


def _pack_players_for_team(payload: Mapping[str, Any], team: str) -> List[Dict[str, Any]]:
    team_n = _norm_team(team)
    rows: List[Dict[str, Any]] = []
    for layer in ("rows", "ol_roles"):
        for row in payload.get(layer) or []:
            if not isinstance(row, dict):
                continue
            if _norm_team(row.get("team")) != team_n:
                continue
            name = str(row.get("player_name") or "").strip()
            if not name:
                continue
            rows.append({**row, "_layer": layer})
    # Longest names first so "Michael Penix Jr." beats "Michael".
    rows.sort(key=lambda r: len(str(r.get("player_name") or "")), reverse=True)
    return rows


def _names_in_text(text: str, players: Sequence[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    hay = f" {text} "
    found: List[Mapping[str, Any]] = []
    seen: set[str] = set()
    for row in players:
        name = str(row.get("player_name") or "").strip()
        if not name or name.lower() in seen:
            continue
        # Match full name or last-token surname when unique enough (≥5 chars).
        patterns = [name]
        parts = name.replace(".", "").split()
        if parts:
            last = parts[-1]
            if len(last) >= 5 and last.lower() not in {"junior", "senior"}:
                patterns.append(last)
        for pat in patterns:
            if re.search(rf"(?i)(?<![A-Za-z]){re.escape(pat)}(?![A-Za-z])", hay):
                found.append(row)
                seen.add(name.lower())
                break
    return found


def _clause_span(text: str, index: int) -> tuple[int, int]:
    """Return [start, end) of the `.` / `;` clause containing ``index``."""
    start = 0
    for i, ch in enumerate(text):
        if i >= index:
            break
        if ch in ".;":
            start = i + 1
    end = len(text)
    for i in range(index, len(text)):
        if text[i] in ".;":
            end = i
            break
    return start, end


def _names_near_pattern(
    text: str,
    pattern: re.Pattern[str],
    players: Sequence[Mapping[str, Any]],
    *,
    before: int = 80,
    after: int = 0,
    same_clause: bool = False,
) -> List[Mapping[str, Any]]:
    """Names in a window around each pattern hit (default: subject precedes verb)."""
    hits: List[Mapping[str, Any]] = []
    seen: set[str] = set()
    for match in pattern.finditer(text):
        if same_clause:
            c0, c1 = _clause_span(text, match.start())
            start = c0
            end = match.end()  # subject only — never names after the verb
        else:
            start = max(0, match.start() - before)
            end = min(len(text), match.end() + after)
        window = text[start:end]
        for row in _names_in_text(window, players):
            key = str(row.get("player_name") or "").lower()
            if key and key not in seen:
                seen.add(key)
                hits.append(row)
    return hits


def _names_near_out_clause(
    text: str, players: Sequence[Mapping[str, Any]]
) -> List[Mapping[str, Any]]:
    """Only players named as the subject of an OUT clause."""
    return _names_near_pattern(text, _OUT_RE, players, same_clause=True)


def _draft_overrides_for_flag(
    *,
    team: str,
    sot_flag: str,
    sources: Sequence[Mapping[str, Any]],
    desk_date: str,
    players: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """Conservative drafts only. Empty list = human must fill fields."""
    drafts: List[Dict[str, Any]] = []
    source_hrefs = [str(s.get("href") or "") for s in sources if s.get("href")]
    source_hrefs = [h for h in source_hrefs if h]

    if _OUT_RE.search(sot_flag):
        for row in _names_near_out_clause(sot_flag, players):
            current = row.get("injury_status")
            if str(current or "").lower() in {"out", "ir", "pup"}:
                continue
            drafts.append(
                {
                    "team": team,
                    "player_name": row.get("player_name"),
                    "player_id": str(row.get("player_id") or ""),
                    "position": str(row.get("position") or "").upper(),
                    "layer": row.get("_layer") or "rows",
                    "field": "injury_status",
                    "before": current,
                    "after": "out",
                    "reason": f"Camp Desk SoT flag ({desk_date}): {sot_flag}",
                    "as_of": desk_date,
                    "confidence": "medium",
                    "destination": "kei_only",
                    "sources": source_hrefs or [f"camp-desk:{desk_date}:{team}"],
                    "draft": True,
                }
            )

    # Named-starter: only QBs adjacent to the named-starter clause.
    if _NAMED_STARTER_RE.search(sot_flag):
        for row in _names_near_pattern(
            sot_flag, _NAMED_STARTER_RE, players, before=40, after=0
        ):
            if str(row.get("position") or "").upper() != "QB":
                continue
            current = row.get("competition_status")
            if str(current or "") == "named_starter":
                continue
            drafts.append(
                {
                    "team": team,
                    "player_name": row.get("player_name"),
                    "player_id": str(row.get("player_id") or ""),
                    "position": "QB",
                    "layer": "rows",
                    "field": "competition_status",
                    "before": current,
                    "after": "named_starter",
                    "reason": f"Camp Desk SoT flag ({desk_date}): {sot_flag}",
                    "as_of": desk_date,
                    "confidence": "medium",
                    "destination": "sot",
                    "sources": source_hrefs or [f"camp-desk:{desk_date}:{team}"],
                    "draft": True,
                }
            )
    elif _OPEN_COMP_RE.search(sot_flag):
        for row in _names_near_pattern(
            sot_flag, _OPEN_COMP_RE, players, before=80, after=40
        ):
            if str(row.get("position") or "").upper() != "QB":
                continue
            current = row.get("competition_status")
            if str(current or "") == "open_competition":
                continue
            drafts.append(
                {
                    "team": team,
                    "player_name": row.get("player_name"),
                    "player_id": str(row.get("player_id") or ""),
                    "position": "QB",
                    "layer": "rows",
                    "field": "competition_status",
                    "before": current,
                    "after": "open_competition",
                    "reason": f"Camp Desk SoT flag ({desk_date}): {sot_flag}",
                    "as_of": desk_date,
                    "confidence": "medium",
                    "destination": "sot",
                    "sources": source_hrefs or [f"camp-desk:{desk_date}:{team}"],
                    "draft": True,
                }
            )

    # Validate against daily-intel schema; drop bad drafts.
    clean: List[Dict[str, Any]] = []
    for raw in drafts:
        try:
            ov = normalize_override(raw)
            if ov["field"] not in ALLOWED_FIELDS:
                continue
            # Never auto-draft identity / depth_order from camp prose.
            if ov["field"] in {"player_name", "player_id", "depth_order", "depth_slot"}:
                continue
            clean.append({**ov, "draft": True})
        except ValueError:
            continue
    return clean


@dataclass
class CampSotFlag:
    flag_id: str
    desk_date: str
    team: str
    title: str
    sot_flag: str
    bottom_line: str
    sources: List[Dict[str, Any]] = field(default_factory=list)
    draft_overrides: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "open"  # open | queued | accepted | overdue
    overdue: bool = False
    age_hours: float = 0.0

    def as_dict(self) -> Dict[str, Any]:
        return {
            "flag_id": self.flag_id,
            "desk_date": self.desk_date,
            "team": self.team,
            "title": self.title,
            "sot_flag": self.sot_flag,
            "bottom_line": self.bottom_line,
            "sources": self.sources,
            "draft_overrides": self.draft_overrides,
            "status": self.status,
            "overdue": self.overdue,
            "age_hours": round(self.age_hours, 1),
        }


def _accepted_flag_ids(log_path: Path) -> set[str]:
    if not log_path.is_file():
        return set()
    ids: set[str] = set()
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        fid = str(row.get("flag_id") or "")
        if fid:
            ids.add(fid)
    return ids


def _queued_flag_ids(proposed_dir: Path) -> set[str]:
    if not proposed_dir.is_dir():
        return set()
    ids: set[str] = set()
    for path in proposed_dir.glob("camp-flag-*.json"):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        fid = str(doc.get("flag_id") or "")
        if fid:
            ids.add(fid)
    return ids


def scan_camp_sot_flags(
    *,
    camp_dir: Path = CAMP_DESK_DEFAULT,
    pack: Optional[Mapping[str, Any]] = None,
    pack_path: Path = PACK_DEFAULT,
    proposed_dir: Path = PROPOSED_DEFAULT,
    accepted_log: Path = ACCEPTED_LOG_DEFAULT,
    now: Optional[datetime] = None,
    overdue_hours: int = DEFAULT_OVERDUE_HOURS,
    latest_desk_only: bool = True,
) -> List[CampSotFlag]:
    """Scan Camp Desk for material depth flags and annotate queue state.

    By default only the newest ``desk_date`` is scanned (older packages are
    historical). Pass ``latest_desk_only=False`` for a full archive scan.
    """
    payload = dict(pack) if pack is not None else load_pack(pack_path)
    accepted = _accepted_flag_ids(accepted_log)
    queued = _queued_flag_ids(proposed_dir)
    clock = now or _now_utc()
    days = load_camp_day_files(camp_dir)
    if latest_desk_only and days:
        newest = max(str(d.get("desk_date") or "") for d in days)
        days = [d for d in days if str(d.get("desk_date") or "") == newest]
    flags: List[CampSotFlag] = []

    for day in days:
        desk_date = str(day.get("desk_date") or "")
        if not desk_date:
            continue
        try:
            start = desk_date_start_utc(desk_date)
        except ValueError:
            continue
        age_h = max(0.0, (clock - start).total_seconds() / 3600.0)
        for note in day.get("team_notes") or []:
            if not isinstance(note, dict) or not note.get("is_material_depth"):
                continue
            team = _norm_team(note.get("team_id"))
            sot_flag = str(note.get("sot_flag") or "").strip()
            if not team:
                continue
            flag_id = f"{desk_date}:{team}"
            players = _pack_players_for_team(payload, team)
            drafts = _draft_overrides_for_flag(
                team=team,
                sot_flag=sot_flag or str(note.get("bottom_line") or ""),
                sources=list(note.get("sources") or []),
                desk_date=desk_date,
                players=players,
            )
            overdue = False
            if flag_id in accepted:
                status = "accepted"
            elif flag_id in queued:
                status = "queued"
                overdue = age_h >= overdue_hours
            else:
                overdue = age_h >= overdue_hours
                status = "overdue" if overdue else "open"
            flags.append(
                CampSotFlag(
                    flag_id=flag_id,
                    desk_date=desk_date,
                    team=team,
                    title=str(note.get("title") or ""),
                    sot_flag=sot_flag,
                    bottom_line=str(note.get("bottom_line") or ""),
                    sources=list(note.get("sources") or []),
                    draft_overrides=drafts,
                    status=status,
                    overdue=overdue,
                    age_hours=age_h,
                )
            )
    flags.sort(key=lambda f: (-int(f.overdue), f.desk_date, f.team))
    return flags


def proposal_doc_for_flag(flag: CampSotFlag) -> Dict[str, Any]:
    return {
        "schema": "nfl-camp-sot-proposal/v1",
        "flag_id": flag.flag_id,
        "as_of": flag.desk_date,
        "source": "camp_desk",
        "team": flag.team,
        "title": flag.title,
        "sot_flag": flag.sot_flag,
        "bottom_line": flag.bottom_line,
        "sources": flag.sources,
        "status": "proposed",
        "requires_human_accept": True,
        "queued_at": _now_iso(),
        "notes": (
            "Draft overrides are suggestions only. Review before accept. "
            "Never invent depth_order / new starters from prose. "
            "Accept via scripts/nfl/queue_camp_sot_flags.py --accept <file>."
        ),
        "overrides": flag.draft_overrides,
    }


def queue_flags(
    flags: Sequence[CampSotFlag],
    *,
    proposed_dir: Path = PROPOSED_DEFAULT,
    only_overdue: bool = False,
    only_with_drafts: bool = False,
) -> List[Path]:
    """Write proposal JSON files. Does not touch the depth pack."""
    proposed_dir.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []
    for flag in flags:
        if flag.status == "accepted":
            continue
        if only_overdue and not flag.overdue:
            continue
        if only_with_drafts and not flag.draft_overrides:
            continue
        # Skip rewrite if already queued with same flag_id unless re-queue open.
        path = proposed_dir / f"camp-flag-{flag.desk_date}-{flag.team}.json"
        doc = proposal_doc_for_flag(flag)
        path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        written.append(path)
    return written


def _strip_draft_markers(overrides: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for raw in overrides:
        ov = dict(raw)
        ov.pop("draft", None)
        out.append(normalize_override(ov))
    return out


def accept_proposal(
    proposal_path: Path,
    *,
    pack_path: Path = PACK_DEFAULT,
    pending_dir: Path = PENDING_DEFAULT,
    accepted_log: Path = ACCEPTED_LOG_DEFAULT,
    write_pack: bool = False,
    allow_empty_overrides: bool = False,
) -> Dict[str, Any]:
    """Accept a proposal: validate overrides → pending (and optionally --write pack).

    Extends the existing daily-intel accept path. Does not rematerialize;
    callers rematerialize after pack write via the safe rebuild entrypoint.
    """
    doc = json.loads(proposal_path.read_text(encoding="utf-8"))
    flag_id = str(doc.get("flag_id") or "")
    overrides_raw = list(doc.get("overrides") or [])
    if not overrides_raw and not allow_empty_overrides:
        raise ValueError(
            "proposal has no overrides — fill field/after (or pass allow_empty_overrides "
            "to mark the flag reviewed without a pack write)"
        )
    overrides = _strip_draft_markers(overrides_raw) if overrides_raw else []

    pending_dir.mkdir(parents=True, exist_ok=True)
    as_of = str(doc.get("as_of") or "")
    pending_name = proposal_path.name.replace("camp-flag-", "camp-accepted-", 1)
    pending_path = pending_dir / pending_name
    pending_doc = {
        "as_of": as_of,
        "approved_by": "camp-sot-accept",
        "fixture": False,
        "flag_id": flag_id,
        "source": "camp_desk",
        "notes": doc.get("sot_flag") or doc.get("notes") or "",
        "overrides": overrides,
    }
    pending_path.write_text(json.dumps(pending_doc, indent=2) + "\n", encoding="utf-8")

    apply_result: Optional[Dict[str, Any]] = None
    if write_pack and overrides:
        pack = load_pack(pack_path)
        result = apply_intel_overrides(pack, overrides, as_of=as_of or None)
        pack_path.write_text(json.dumps(result.payload, indent=2) + "\n", encoding="utf-8")
        apply_result = result.as_dict()

    accepted_log.parent.mkdir(parents=True, exist_ok=True)
    with accepted_log.open("a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "flag_id": flag_id,
                    "accepted_at": _now_iso(),
                    "proposal": str(proposal_path),
                    "pending": str(pending_path),
                    "wrote_pack": bool(write_pack and overrides),
                    "override_count": len(overrides),
                }
            )
            + "\n"
        )

    # Remove proposal once accepted so overdue scan clears.
    if proposal_path.is_file() and proposal_path.parent == PROPOSED_DEFAULT:
        proposal_path.unlink()
    elif proposal_path.is_file() and "proposed" in proposal_path.parts:
        proposal_path.unlink()

    return {
        "flag_id": flag_id,
        "pending": str(pending_path),
        "wrote_pack": bool(write_pack and overrides),
        "apply": apply_result,
        "rematerialize_hint": (
            "After pack write: use /nfl/ops/rebuild-props-layers weeks 1–18 "
            "(see data/ops/nfl-spine-safe-rematerialize.md). Do not bare season= rebuild."
            if write_pack and overrides
            else None
        ),
    }


def overdue_summary(flags: Iterable[CampSotFlag]) -> Dict[str, Any]:
    rows = list(flags)
    overdue = [f for f in rows if f.overdue]
    open_flags = [f for f in rows if f.status in {"open", "overdue"}]
    queued = [f for f in rows if f.status == "queued"]
    return {
        "total_material": len(rows),
        "open": len(open_flags),
        "queued": len(queued),
        "overdue": len(overdue),
        "overdue_flag_ids": [f.flag_id for f in overdue],
        "draft_override_count": sum(len(f.draft_overrides) for f in rows),
    }
