"""Camp Desk ``is_material_depth`` → DepthSotWorkItem handoff (one SoT).

Contract (non-negotiable)
------------------------
- Notes are **copy only**. They never write means / props / spreads / fair lines.
- ``is_material_depth`` / ``sot_flag`` become a **DepthSotWorkItem** ticket with an SLA.
- An LLM / heuristic may **propose** a pack patch. It may **never** apply it.
- **Accept** is the only gate that may write the depth pack and rematerialize.
- Path: note → SOT FLAG / work item → human accept structured pack fields
  → rematerialize → receipt / board.

Extends daily intel + the one depth pack. No second SoT. No public UI required.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from src.services.nfl_daily_intel import (
    ALLOWED_FIELDS,
    PACK_DEFAULT,
    apply_intel_overrides,
    normalize_override,
)

# Hard contract — notes must never touch projection / market numbers.
NOTES_MAY_TOUCH_MEANS = False
NOTES_MAY_TOUCH_PROPS = False
NOTES_MAY_TOUCH_SPREADS = False
PROPOSALS_MAY_AUTO_APPLY = False

_SERVICES = Path(__file__).resolve().parent
_REPO = _SERVICES.parents[3]  # services/ → src → model-service → services → repo
CAMP_DESK_DEFAULT = _REPO / "content" / "writers" / "camp-desk-2026"
PROPOSED_DEFAULT = _REPO / "data" / "ops" / "nfl-daily-intel" / "proposed"
PENDING_DEFAULT = _REPO / "data" / "ops" / "nfl-daily-intel" / "pending"
ACCEPTED_LOG_DEFAULT = _REPO / "data" / "ops" / "nfl-daily-intel" / "accepted" / "camp-sot-log.jsonl"
RECEIPTS_DEFAULT = _REPO / "data" / "ops" / "nfl-daily-intel" / "receipts"

WORK_ITEM_SCHEMA = "nfl-depth-sot-work-item/v1"
RECEIPT_SCHEMA = "nfl-depth-sot-receipt/v1"

# T1 same-day · T2 next remat · T3 Pass (no pack write expected)
TIER_SLA_HOURS = {"T1": 12, "T2": 48, "T3": 72}
DEFAULT_OVERDUE_HOURS = TIER_SLA_HOURS["T1"]  # scan fallback; per-item SLA wins

SAFE_REMAT_HINT = (
    "POST /nfl/ops/rebuild-props-layers?season=2026"
    "&weeks=1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18"
)

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
_PASS_RE = re.compile(
    r"(?i)\b("
    r"pass\b|do not crown|do not invent|do not elevate|do not (?:silently )?(?:assign|promote|transfer)|"
    r"leave thin|thin august|no starter should be inferred|flag (?:for |arizona )?.*do not"
    r")"
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


def assert_notes_cannot_touch_lines() -> None:
    """Guardrail for callers / tests — notes never rewrite board numbers."""
    assert NOTES_MAY_TOUCH_MEANS is False
    assert NOTES_MAY_TOUCH_PROPS is False
    assert NOTES_MAY_TOUCH_SPREADS is False
    assert PROPOSALS_MAY_AUTO_APPLY is False


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
    hits: List[Mapping[str, Any]] = []
    seen: set[str] = set()
    for match in pattern.finditer(text):
        if same_clause:
            c0, _c1 = _clause_span(text, match.start())
            start = c0
            end = match.end()
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
    return _names_near_pattern(text, _OUT_RE, players, same_clause=True)


def _propose_pack_patch(
    *,
    team: str,
    sot_flag: str,
    sources: Sequence[Mapping[str, Any]],
    desk_date: str,
    players: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """Heuristic / LLM-shaped proposed patch. Never applied here."""
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

    clean: List[Dict[str, Any]] = []
    for raw in drafts:
        try:
            ov = normalize_override(raw)
            if ov["field"] not in ALLOWED_FIELDS:
                continue
            if ov["field"] in {"player_name", "player_id", "depth_order", "depth_slot"}:
                continue
            clean.append({**ov, "draft": True})
        except ValueError:
            continue
    return clean


# Back-compat alias used by older tests / callers.
_draft_overrides_for_flag = _propose_pack_patch


def classify_tier(
    *,
    sot_flag: str,
    proposed_patch: Sequence[Mapping[str, Any]],
) -> str:
    """T1 same-day · T2 next remat · T3 Pass."""
    fields = {str(o.get("field")) for o in proposed_patch}
    if "injury_status" in fields or "competition_status" in fields:
        return "T1"
    text = sot_flag or ""
    # Actionable injury / starter claims stay T1 even when the note also says Pass.
    if _OUT_RE.search(text) or _NAMED_STARTER_RE.search(text):
        return "T1"
    if _PASS_RE.search(text) and not proposed_patch:
        return "T3"
    if _OPEN_COMP_RE.search(text) and not proposed_patch:
        return "T3"
    return "T2"


@dataclass
class DepthSotWorkItem:
    """Ticket created from a Camp Desk SOT FLAG. Notes stay copy."""

    work_item_id: str
    desk_date: str
    team: str
    title: str
    sot_flag: str
    bottom_line: str
    tier: str = "T2"
    sla_hours: int = 48
    sources: List[Dict[str, Any]] = field(default_factory=list)
    proposed_patch: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "open"  # open | queued | accepted | overdue | pass
    overdue: bool = False
    age_hours: float = 0.0

    # Legacy aliases for thinner-cut callers / tests.
    @property
    def flag_id(self) -> str:
        return self.work_item_id

    @property
    def draft_overrides(self) -> List[Dict[str, Any]]:
        return self.proposed_patch

    def as_dict(self) -> Dict[str, Any]:
        return {
            "schema": WORK_ITEM_SCHEMA,
            "work_item_id": self.work_item_id,
            "flag_id": self.work_item_id,
            "desk_date": self.desk_date,
            "team": self.team,
            "title": self.title,
            "sot_flag": self.sot_flag,
            "bottom_line": self.bottom_line,
            "tier": self.tier,
            "sla_hours": self.sla_hours,
            "sources": self.sources,
            "proposed_patch": {"overrides": self.proposed_patch},
            "draft_overrides": self.proposed_patch,  # legacy
            "status": self.status,
            "overdue": self.overdue,
            "age_hours": round(self.age_hours, 1),
            "contract": {
                "notes_may_touch_means": NOTES_MAY_TOUCH_MEANS,
                "notes_may_touch_props": NOTES_MAY_TOUCH_PROPS,
                "notes_may_touch_spreads": NOTES_MAY_TOUCH_SPREADS,
                "proposals_may_auto_apply": PROPOSALS_MAY_AUTO_APPLY,
            },
        }


# Thinner-cut alias.
CampSotFlag = DepthSotWorkItem


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
        fid = str(row.get("work_item_id") or row.get("flag_id") or "")
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
        fid = str(doc.get("work_item_id") or doc.get("flag_id") or "")
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
    overdue_hours: Optional[int] = None,
    latest_desk_only: bool = True,
) -> List[DepthSotWorkItem]:
    """Scan Camp Desk material flags → DepthSotWorkItem list with overdue SLAs."""
    assert_notes_cannot_touch_lines()
    payload = dict(pack) if pack is not None else load_pack(pack_path)
    accepted = _accepted_flag_ids(accepted_log)
    queued = _queued_flag_ids(proposed_dir)
    clock = now or _now_utc()
    days = load_camp_day_files(camp_dir)
    if latest_desk_only and days:
        newest = max(str(d.get("desk_date") or "") for d in days)
        days = [d for d in days if str(d.get("desk_date") or "") == newest]
    items: List[DepthSotWorkItem] = []

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
            work_item_id = f"{desk_date}:{team}"
            players = _pack_players_for_team(payload, team)
            patch = _propose_pack_patch(
                team=team,
                sot_flag=sot_flag or str(note.get("bottom_line") or ""),
                sources=list(note.get("sources") or []),
                desk_date=desk_date,
                players=players,
            )
            tier = classify_tier(sot_flag=sot_flag, proposed_patch=patch)
            sla = overdue_hours if overdue_hours is not None else TIER_SLA_HOURS[tier]
            overdue = False
            if work_item_id in accepted:
                status = "accepted"
            elif work_item_id in queued:
                status = "queued"
                overdue = age_h >= sla
            else:
                overdue = age_h >= sla
                if tier == "T3" and not patch:
                    status = "pass" if not overdue else "overdue"
                else:
                    status = "overdue" if overdue else "open"
            items.append(
                DepthSotWorkItem(
                    work_item_id=work_item_id,
                    desk_date=desk_date,
                    team=team,
                    title=str(note.get("title") or ""),
                    sot_flag=sot_flag,
                    bottom_line=str(note.get("bottom_line") or ""),
                    tier=tier,
                    sla_hours=sla,
                    sources=list(note.get("sources") or []),
                    proposed_patch=patch,
                    status=status,
                    overdue=overdue,
                    age_hours=age_h,
                )
            )
    items.sort(key=lambda f: (0 if f.tier == "T1" else 1 if f.tier == "T2" else 2, -int(f.overdue), f.team))
    return items


def proposal_doc_for_flag(flag: DepthSotWorkItem) -> Dict[str, Any]:
    """Serialize a DepthSotWorkItem for the proposed/ queue (never auto-applied)."""
    return {
        "schema": WORK_ITEM_SCHEMA,
        "work_item_id": flag.work_item_id,
        "flag_id": flag.work_item_id,
        "as_of": flag.desk_date,
        "source": "camp_desk",
        "team": flag.team,
        "title": flag.title,
        "sot_flag": flag.sot_flag,
        "bottom_line": flag.bottom_line,
        "tier": flag.tier,
        "sla_hours": flag.sla_hours,
        "sources": flag.sources,
        "status": "proposed",
        "requires_human_accept": True,
        "may_auto_apply": PROPOSALS_MAY_AUTO_APPLY,
        "queued_at": _now_iso(),
        "notes": (
            "Proposed pack patch only — never auto-applied. "
            "Notes must not touch means/props/spreads. "
            "Accept → pack write → rematerialize → receipt. "
            "Never invent depth_order / new starters from prose. "
            "CLI: scripts/nfl/queue_camp_sot_flags.py --accept <file> [--write]"
        ),
        "proposed_patch": {"overrides": flag.proposed_patch},
        # Legacy key so older accept paths keep working.
        "overrides": flag.proposed_patch,
        "contract": {
            "notes_may_touch_means": NOTES_MAY_TOUCH_MEANS,
            "notes_may_touch_props": NOTES_MAY_TOUCH_PROPS,
            "notes_may_touch_spreads": NOTES_MAY_TOUCH_SPREADS,
            "proposals_may_auto_apply": PROPOSALS_MAY_AUTO_APPLY,
        },
    }


def queue_flags(
    flags: Sequence[DepthSotWorkItem],
    *,
    proposed_dir: Path = PROPOSED_DEFAULT,
    only_overdue: bool = False,
    only_with_drafts: bool = False,
    tiers: Optional[Sequence[str]] = None,
) -> List[Path]:
    """Write DepthSotWorkItem JSON. Does not touch the depth pack or means."""
    assert_notes_cannot_touch_lines()
    proposed_dir.mkdir(parents=True, exist_ok=True)
    wanted = {t.upper() for t in tiers} if tiers else None
    written: List[Path] = []
    for flag in flags:
        if flag.status == "accepted":
            continue
        if only_overdue and not flag.overdue:
            continue
        if only_with_drafts and not flag.proposed_patch:
            continue
        if wanted and flag.tier not in wanted:
            continue
        path = proposed_dir / f"camp-flag-{flag.desk_date}-{flag.team}.json"
        path.write_text(json.dumps(proposal_doc_for_flag(flag), indent=2) + "\n", encoding="utf-8")
        written.append(path)
    return written


def _strip_draft_markers(overrides: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for raw in overrides:
        ov = dict(raw)
        ov.pop("draft", None)
        out.append(normalize_override(ov))
    return out


def _overrides_from_doc(doc: Mapping[str, Any]) -> List[Dict[str, Any]]:
    patch = doc.get("proposed_patch")
    if isinstance(patch, dict) and patch.get("overrides") is not None:
        return list(patch.get("overrides") or [])
    return list(doc.get("overrides") or [])


def write_receipt(
    *,
    work_item_id: str,
    tier: str,
    pending_path: Path,
    wrote_pack: bool,
    apply_result: Optional[Mapping[str, Any]],
    rematerialize_status: str,
    receipts_dir: Path = RECEIPTS_DEFAULT,
) -> Path:
    receipts_dir.mkdir(parents=True, exist_ok=True)
    safe_id = work_item_id.replace(":", "-")
    path = receipts_dir / f"receipt-{safe_id}.json"
    payload = {
        "schema": RECEIPT_SCHEMA,
        "work_item_id": work_item_id,
        "tier": tier,
        "accepted_at": _now_iso(),
        "pending": str(pending_path),
        "wrote_pack": wrote_pack,
        "apply": dict(apply_result) if apply_result else None,
        "rematerialize": {
            "status": rematerialize_status,
            "entrypoint": SAFE_REMAT_HINT,
            "ops_note": "data/ops/nfl-spine-safe-rematerialize.md",
            "rule": "Accept is the only gate that may rematerialize. Notes never write means.",
        },
        "contract": {
            "notes_may_touch_means": NOTES_MAY_TOUCH_MEANS,
            "notes_may_touch_props": NOTES_MAY_TOUCH_PROPS,
            "notes_may_touch_spreads": NOTES_MAY_TOUCH_SPREADS,
            "proposals_may_auto_apply": PROPOSALS_MAY_AUTO_APPLY,
        },
        "board_path": (
            "depth pack → rematerialize weeks 1–18 → props/fantasy/KEI inherit"
            if wrote_pack
            else "no pack write — board unchanged"
        ),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def accept_proposal(
    proposal_path: Path,
    *,
    pack_path: Path = PACK_DEFAULT,
    pending_dir: Path = PENDING_DEFAULT,
    accepted_log: Path = ACCEPTED_LOG_DEFAULT,
    receipts_dir: Path = RECEIPTS_DEFAULT,
    write_pack: bool = False,
    rematerialize: bool = False,
    allow_empty_overrides: bool = False,
) -> Dict[str, Any]:
    """Accept a DepthSotWorkItem: pending → optional pack write → receipt.

    Rematerialize is **requested** only after accept+write. This never lets
    note prose rewrite means. ``rematerialize=True`` records a remat-required
    receipt with the safe rebuild entrypoint (does not bare ``season=`` curl).
    """
    assert_notes_cannot_touch_lines()
    if rematerialize and not write_pack:
        raise ValueError("rematerialize requires --write (accept is the only remat gate)")

    doc = json.loads(proposal_path.read_text(encoding="utf-8"))
    work_item_id = str(doc.get("work_item_id") or doc.get("flag_id") or "")
    tier = str(doc.get("tier") or "T2")
    overrides_raw = _overrides_from_doc(doc)
    if not overrides_raw and not allow_empty_overrides:
        raise ValueError(
            "work item has no proposed_patch overrides — fill field/after "
            "(or pass allow_empty_overrides for T3 Pass / reviewed-no-write)"
        )
    overrides = _strip_draft_markers(overrides_raw) if overrides_raw else []

    pending_dir.mkdir(parents=True, exist_ok=True)
    as_of = str(doc.get("as_of") or "")
    pending_name = proposal_path.name.replace("camp-flag-", "camp-accepted-", 1)
    pending_path = pending_dir / pending_name
    pending_doc = {
        "as_of": as_of,
        "approved_by": "depth-sot-accept",
        "fixture": False,
        "work_item_id": work_item_id,
        "flag_id": work_item_id,
        "tier": tier,
        "source": "camp_desk",
        "notes": doc.get("sot_flag") or doc.get("notes") or "",
        "overrides": overrides,
        "contract": {
            "notes_may_touch_means": NOTES_MAY_TOUCH_MEANS,
            "proposals_may_auto_apply": PROPOSALS_MAY_AUTO_APPLY,
        },
    }
    pending_path.write_text(json.dumps(pending_doc, indent=2) + "\n", encoding="utf-8")

    apply_result: Optional[Dict[str, Any]] = None
    if write_pack and overrides:
        pack = load_pack(pack_path)
        result = apply_intel_overrides(pack, overrides, as_of=as_of or None)
        pack_path.write_text(json.dumps(result.payload, indent=2) + "\n", encoding="utf-8")
        apply_result = result.as_dict()

    if write_pack and overrides and rematerialize:
        remat_status = "required"
    elif write_pack and overrides:
        remat_status = "required_after_accept"
    else:
        remat_status = "skipped"

    receipt_path = write_receipt(
        work_item_id=work_item_id or proposal_path.stem,
        tier=tier,
        pending_path=pending_path,
        wrote_pack=bool(write_pack and overrides),
        apply_result=apply_result,
        rematerialize_status=remat_status,
        receipts_dir=receipts_dir,
    )

    accepted_log.parent.mkdir(parents=True, exist_ok=True)
    with accepted_log.open("a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "work_item_id": work_item_id,
                    "flag_id": work_item_id,
                    "tier": tier,
                    "accepted_at": _now_iso(),
                    "proposal": str(proposal_path),
                    "pending": str(pending_path),
                    "receipt": str(receipt_path),
                    "wrote_pack": bool(write_pack and overrides),
                    "rematerialize_status": remat_status,
                    "override_count": len(overrides),
                }
            )
            + "\n"
        )

    if proposal_path.is_file() and (
        proposal_path.parent == PROPOSED_DEFAULT or "proposed" in proposal_path.parts
    ):
        proposal_path.unlink()

    return {
        "work_item_id": work_item_id,
        "flag_id": work_item_id,
        "tier": tier,
        "pending": str(pending_path),
        "receipt": str(receipt_path),
        "wrote_pack": bool(write_pack and overrides),
        "apply": apply_result,
        "rematerialize_status": remat_status,
        "rematerialize_hint": SAFE_REMAT_HINT if remat_status.startswith("required") else None,
        "contract": {
            "notes_may_touch_means": NOTES_MAY_TOUCH_MEANS,
            "proposals_may_auto_apply": PROPOSALS_MAY_AUTO_APPLY,
        },
    }


def overdue_summary(flags: Iterable[DepthSotWorkItem]) -> Dict[str, Any]:
    rows = list(flags)
    overdue = [f for f in rows if f.overdue]
    open_flags = [f for f in rows if f.status in {"open", "overdue"}]
    queued = [f for f in rows if f.status == "queued"]
    by_tier = {t: sum(1 for f in rows if f.tier == t) for t in ("T1", "T2", "T3")}
    return {
        "total_material": len(rows),
        "open": len(open_flags),
        "queued": len(queued),
        "overdue": len(overdue),
        "overdue_flag_ids": [f.work_item_id for f in overdue],
        "by_tier": by_tier,
        "draft_override_count": sum(len(f.proposed_patch) for f in rows),
        "contract": {
            "notes_may_touch_means": NOTES_MAY_TOUCH_MEANS,
            "proposals_may_auto_apply": PROPOSALS_MAY_AUTO_APPLY,
        },
    }
