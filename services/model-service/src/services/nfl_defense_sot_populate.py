"""Populate defense SoT — durable IR/out + named starters → DepthSot T1s.

Contract
--------
- One pack. One ``DepthSotWorkItem`` queue. No second SoT.
- Source → work item → human accept → pack. **No auto-accept.**
- Diff official IR/out + official-ish named defense depth vs live
  ``defense_roles`` (EDGE / DL / LB / CB / S; NB only when already seeded).
- Open T1 when pack is blank/healthy and source is durable out **or** a
  named starter already attested in-repo (camp desk / pack seed).
- Do **not** invent starters. Unknown slots stay empty (no shock).
- No weather feed, no ID-map rewrite, no CFB, no unit-shock rewrites.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from src.services.nfl_camp_sot_queue import (
    ACCEPTED_LOG_DEFAULT,
    NOTES_MAY_TOUCH_MEANS,
    NOTES_MAY_TOUCH_PROPS,
    NOTES_MAY_TOUCH_SPREADS,
    PROPOSALS_MAY_AUTO_APPLY,
    PROPOSED_DEFAULT,
    QUEUE_RUNTIME_DEFAULT,
    TIER_SLA_HOURS,
    WORK_ITEM_SCHEMA,
    DepthSotWorkItem,
    QueueRunResult,
    _canonical_work_item_doc,
    _disposition_map,
    _is_overdue,
    _norm_team,
    _now_iso,
    _now_utc,
    _queued_flag_ids,
    assert_notes_cannot_touch_lines,
    desk_date_start_utc,
    load_pack,
    next_kei_publish_utc,
)
from src.services.nfl_daily_intel import (
    DEFENSE_POSITIONS,
    PACK_DEFAULT,
    normalize_override,
)

# Positions in scope for this populate pass (NB only if already seeded).
POPULATE_POSITIONS = frozenset({"EDGE", "DL", "LB", "CB", "S"})
PACK_DURABLE_OUT = frozenset({"out", "ir", "pup", "nfi", "waived_injured", "inactive"})
PACK_HEALTHY = frozenset({"", "active", "limited", "questionable", "doubtful"})

AS_OF_DEFAULT = "2026-08-29"


@dataclass(frozen=True)
class DefensePopulateFact:
    """Durable defense fact — camp desk / Athletic / team IR — not invented."""

    team: str
    player_name: str
    position: str  # EDGE|DL|LB|CB|S
    kind: str  # durable_out | named_starter
    injury_after: str  # ir|out|pup|active
    depth_order: int
    depth_slot: str  # starter | depth (never invent starter for unknowns)
    player_id: str
    sot_flag: str
    sources: Tuple[str, ...]
    note_id: str
    role_note: str = ""

    def work_item_id(self, *, as_of: str) -> str:
        pid = self.player_id or f"{self.team}-{self.position}-{self.player_name}"
        safe = pid.replace(" ", "").replace("/", "-")
        return f"{as_of}:defense:{safe}:{self.kind}"


# Curated from Camp Desk 2026-08-26 + Athletic/team IR links already in desk.
# Empty stays empty: no 32-team chart invent.
DURABLE_DEFENSE_FACTS: Tuple[DefensePopulateFact, ...] = (
    DefensePopulateFact(
        team="MIN",
        player_name="Jamal Adams",
        position="S",
        kind="durable_out",
        injury_after="ir",
        depth_order=1,
        depth_slot="starter",
        player_id="MIN-S-ADAMS",
        sot_flag=(
            "Adams season-ending IR (quad). Pack blank for MIN S — open T1 to "
            "seed S1 as ir. Do not invent a replacement starter."
        ),
        sources=(
            "The Athletic — Adams season-ending quad",
            "camp-desk:2026-08-26:MIN",
        ),
        note_id="defense-populate-MIN-Adams",
        role_note="Adams-class S1 IR — planned safety hybrid; durable out only.",
    ),
    DefensePopulateFact(
        team="CAR",
        player_name="Nic Scourton",
        position="EDGE",
        kind="durable_out",
        injury_after="ir",
        depth_order=1,
        depth_slot="starter",
        player_id="CAR-EDGE-SCOURTON",
        sot_flag=(
            "Scourton season-ending ACL — intended EDGE starter opposite Phillips. "
            "Pack blank — open T1 for EDGE ir. Do not invent a one-for-one replacement."
        ),
        sources=(
            "Panthers — Hubbard and Legette update (Aug 24)",
            "camp-desk:2026-08-26:CAR",
        ),
        note_id="defense-populate-CAR-Scourton",
        role_note="Scourton EDGE1 season-ending ACL — durable out.",
    ),
    DefensePopulateFact(
        team="CAR",
        player_name="Jaelan Phillips",
        position="EDGE",
        kind="named_starter",
        injury_after="active",
        depth_order=1,
        depth_slot="starter",
        player_id="CAR-EDGE-PHILLIPS",
        sot_flag=(
            "Camp Desk names Phillips as the EDGE opposite Scourton. Pack blank — "
            "open T1 for named EDGE starter (active). No invented depth behind him."
        ),
        sources=("camp-desk:2026-08-26:CAR",),
        note_id="defense-populate-CAR-Phillips",
        role_note="Named EDGE opposite Scourton (desk). Accept path only.",
    ),
    DefensePopulateFact(
        team="NO",
        player_name="Bryan Bresee",
        position="DL",
        kind="durable_out",
        injury_after="ir",
        depth_order=1,
        depth_slot="starter",
        player_id="NO-DL-BRESEE",
        sot_flag=(
            "Bresee season-ending ACL / IR. Pack blank for NO DL — open T1 for "
            "DL ir. Do not invent a replacement starter."
        ),
        sources=(
            "Saints — injury and IR update (Aug 25)",
            "camp-desk:2026-08-26:NO",
        ),
        note_id="defense-populate-NO-Bresee",
        role_note="Bresee DL1 season-ending IR — durable out.",
    ),
    DefensePopulateFact(
        team="SEA",
        player_name="Bud Clark",
        position="S",
        kind="durable_out",
        injury_after="ir",
        depth_order=2,
        depth_slot="depth",
        player_id="SEA-S-CLARK",
        sot_flag=(
            "Clark season-ending IR (broken ankle). Official out, but desk says "
            "he was pushing for a role — not a named starter. Open T1 as S depth "
            "ir only; leave S1 empty (no shock invent)."
        ),
        sources=(
            "ESPN — Clark and Richman placed on IR (Aug 25)",
            "Seahawks — Clark, Richman and Bobo injury context",
            "camp-desk:2026-08-26:SEA",
        ),
        note_id="defense-populate-SEA-Clark",
        role_note="Clark S IR — durable out; not crowned starter.",
    ),
    DefensePopulateFact(
        team="GB",
        player_name="Micah Parsons",
        position="EDGE",
        kind="durable_out",
        injury_after="pup",
        depth_order=1,
        depth_slot="starter",
        player_id="GB-EDGE-PARSONS",
        sot_flag=(
            "Parsons on PUP / unavailable for opening stretch. Pack blank — open "
            "T1 for EDGE1 pup. Do not invent a full-substitute EDGE from camp standouts."
        ),
        sources=(
            "PackersNews — defense and participation report (Aug 24)",
            "camp-desk:2026-08-26:GB",
        ),
        note_id="defense-populate-GB-Parsons",
        role_note="Parsons EDGE1 PUP — durable out for opener window.",
    ),
)


def _pack_defense_index(
    pack: Mapping[str, Any],
) -> Dict[Tuple[str, str, str], Dict[str, Any]]:
    """(team, position, name_key) → defense_roles row."""
    out: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for row in pack.get("defense_roles") or []:
        if not isinstance(row, dict):
            continue
        team = _norm_team(row.get("team"))
        pos = str(row.get("position") or "").strip().upper()
        name = str(row.get("player_name") or "").strip().lower()
        if team and pos and name:
            out[(team, pos, name)] = row
    return out


def _name_key(name: str) -> str:
    return " ".join(str(name or "").strip().lower().split())


def pack_injury_is_healthy(status: Any) -> bool:
    token = str(status or "").strip().lower()
    if token in PACK_DURABLE_OUT:
        return False
    return token in PACK_HEALTHY or token == ""


def _propose_defense_patch(
    *,
    fact: DefensePopulateFact,
    pack_row: Optional[Mapping[str, Any]],
    as_of: str,
) -> List[Dict[str, Any]]:
    """Build proposed_patch for defense_roles (create_if_missing when blank)."""
    current = pack_row.get("injury_status") if pack_row else None
    after = fact.injury_after
    if pack_row is not None and str(current or "").strip().lower() == after:
        return []
    create = pack_row is None
    before = current if pack_row is not None else None
    raw: Dict[str, Any] = {
        "team": fact.team,
        "player_name": fact.player_name,
        "player_id": (
            str(pack_row.get("player_id") or "") if pack_row else fact.player_id
        ),
        "position": fact.position,
        "layer": "defense_roles",
        "field": "injury_status",
        "before": before,
        "after": after,
        "reason": f"Defense populate ({fact.kind}): {fact.sot_flag}",
        "as_of": as_of,
        "confidence": "high",
        "destination": "kei_only" if fact.kind == "durable_out" else "sot",
        "sources": list(fact.sources),
        "confirmation": "high",
        "draft": True,
    }
    if create:
        raw["create_if_missing"] = True
        raw["seed_row"] = {
            "depth_order": fact.depth_order,
            "depth_slot": fact.depth_slot,
            "player_id": fact.player_id,
            "role_note": fact.role_note or fact.sot_flag,
            "sources": list(fact.sources),
        }
    try:
        ov = normalize_override(raw)
    except ValueError:
        return []
    return [{**ov, "draft": True, **({"create_if_missing": True, "seed_row": raw["seed_row"]} if create else {})}]


@dataclass
class DefensePopulateRow:
    """One print-table row: team / player / already-in-SoT / proposed T1."""

    team: str
    player: str
    position: str
    already_in_sot: bool
    proposed_t1: bool
    pack_injury: str
    source_kind: str
    work_item_id: str
    reason: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "team": self.team,
            "player": self.player,
            "position": self.position,
            "already_in_sot": self.already_in_sot,
            "proposed_t1": self.proposed_t1,
            "pack_injury": self.pack_injury,
            "source_kind": self.source_kind,
            "work_item_id": self.work_item_id,
            "reason": self.reason,
        }


def scan_defense_populate(
    *,
    pack: Optional[Mapping[str, Any]] = None,
    pack_path: Path = PACK_DEFAULT,
    facts: Sequence[DefensePopulateFact] = DURABLE_DEFENSE_FACTS,
    proposed_dir: Path = PROPOSED_DEFAULT,
    accepted_log: Path = ACCEPTED_LOG_DEFAULT,
    as_of: str = AS_OF_DEFAULT,
    now: Optional[datetime] = None,
) -> Tuple[List[DepthSotWorkItem], List[DefensePopulateRow]]:
    """Diff durable defense facts vs live pack → T1 work items + print rows."""
    assert_notes_cannot_touch_lines()
    payload = dict(pack) if pack is not None else load_pack(pack_path)
    index = _pack_defense_index(payload)
    closed = _disposition_map(accepted_log)
    queued = _queued_flag_ids(proposed_dir)
    clock = now or _now_utc()
    items: List[DepthSotWorkItem] = []
    table: List[DefensePopulateRow] = []

    # Inventory already-seeded pack defense (SF fixture etc.) — report only.
    for row in payload.get("defense_roles") or []:
        if not isinstance(row, dict):
            continue
        team = _norm_team(row.get("team"))
        pos = str(row.get("position") or "").upper()
        name = str(row.get("player_name") or "").strip()
        if not team or not name or pos not in POPULATE_POSITIONS | DEFENSE_POSITIONS:
            continue
        # Skip if covered by a durable fact below (avoid double print).
        covered = any(
            f.team == team
            and f.position == pos
            and _name_key(f.player_name) == _name_key(name)
            for f in facts
        )
        if covered:
            continue
        table.append(
            DefensePopulateRow(
                team=team,
                player=name,
                position=pos,
                already_in_sot=True,
                proposed_t1=False,
                pack_injury=str(row.get("injury_status") or ""),
                source_kind="pack_seed",
                work_item_id="",
                reason="Already in defense_roles seed — no T1 (healthy/blank invent skipped).",
            )
        )

    for fact in facts:
        if fact.position not in POPULATE_POSITIONS:
            continue
        team = _norm_team(fact.team)
        key = (team, fact.position, _name_key(fact.player_name))
        pack_row = index.get(key)
        already = pack_row is not None
        wid = fact.work_item_id(as_of=as_of)

        if already and not pack_injury_is_healthy(pack_row.get("injury_status")):
            # Already durable-out in SoT — no new T1.
            table.append(
                DefensePopulateRow(
                    team=team,
                    player=fact.player_name,
                    position=fact.position,
                    already_in_sot=True,
                    proposed_t1=False,
                    pack_injury=str(pack_row.get("injury_status") or ""),
                    source_kind=fact.kind,
                    work_item_id=wid,
                    reason="Already durable-out in pack — no new T1.",
                )
            )
            continue

        if already and fact.kind == "named_starter":
            # Named starter already seeded healthy — no T1.
            table.append(
                DefensePopulateRow(
                    team=team,
                    player=fact.player_name,
                    position=fact.position,
                    already_in_sot=True,
                    proposed_t1=False,
                    pack_injury=str(pack_row.get("injury_status") or ""),
                    source_kind=fact.kind,
                    work_item_id=wid,
                    reason="Named starter already in SoT — no T1.",
                )
            )
            continue

        # Pack blank OR healthy vs durable out / missing named starter → T1.
        if already and fact.kind == "durable_out" and pack_injury_is_healthy(
            pack_row.get("injury_status")
        ):
            open_t1 = True
        elif not already and fact.kind in {"durable_out", "named_starter"}:
            open_t1 = True
        else:
            open_t1 = False

        if not open_t1:
            table.append(
                DefensePopulateRow(
                    team=team,
                    player=fact.player_name,
                    position=fact.position,
                    already_in_sot=already,
                    proposed_t1=False,
                    pack_injury=str((pack_row or {}).get("injury_status") or ""),
                    source_kind=fact.kind,
                    work_item_id=wid,
                    reason="No open T1 (unknown / leave empty).",
                )
            )
            continue

        patch = _propose_defense_patch(fact=fact, pack_row=pack_row, as_of=as_of)
        if not patch:
            table.append(
                DefensePopulateRow(
                    team=team,
                    player=fact.player_name,
                    position=fact.position,
                    already_in_sot=already,
                    proposed_t1=False,
                    pack_injury=str((pack_row or {}).get("injury_status") or ""),
                    source_kind=fact.kind,
                    work_item_id=wid,
                    reason="Patch no-op vs pack — skip T1.",
                )
            )
            continue

        try:
            start = desk_date_start_utc(as_of)
        except ValueError:
            start = clock
        age_h = max(0.0, (clock - start).total_seconds() / 3600.0)
        tier = "T1"
        sla = TIER_SLA_HOURS[tier]
        overdue, overdue_reason = _is_overdue(
            tier=tier, age_h=age_h, sla_hours=sla, desk_start=start, now=clock
        )
        if wid in closed:
            status = closed[wid]
            overdue = False
            overdue_reason = ""
            open_t1 = False
        elif wid in queued:
            status = "queued"
        else:
            status = "overdue" if overdue else "open"

        table.append(
            DefensePopulateRow(
                team=team,
                player=fact.player_name,
                position=fact.position,
                already_in_sot=already,
                proposed_t1=open_t1 and wid not in closed,
                pack_injury=str((pack_row or {}).get("injury_status") or "(blank)"),
                source_kind=fact.kind,
                work_item_id=wid,
                reason=fact.sot_flag,
            )
        )

        if wid in closed:
            continue

        items.append(
            DepthSotWorkItem(
                work_item_id=wid,
                desk_date=as_of,
                team=team,
                note_id=fact.note_id,
                title=f"Defense populate {fact.kind}: {fact.player_name}",
                sot_flag=fact.sot_flag,
                bottom_line=fact.sot_flag,
                tier=tier,
                sla_hours=sla,
                next_kei_publish=next_kei_publish_utc(start).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
                sources=[{"label": s} for s in fact.sources],
                proposed_patch=patch,
                status=status,
                overdue=overdue,
                overdue_reason=overdue_reason,
                age_hours=age_h,
            )
        )

    items.sort(key=lambda f: (f.team, f.work_item_id))
    table.sort(key=lambda r: (0 if r.proposed_t1 else 1, r.team, r.player))
    return items, table


def proposal_doc_for_defense_flag(flag: DepthSotWorkItem) -> Dict[str, Any]:
    return {
        "schema": WORK_ITEM_SCHEMA,
        "work_item_id": flag.work_item_id,
        "note_id": flag.note_id,
        "flag_id": flag.work_item_id,
        "as_of": flag.desk_date,
        "team_id": flag.team,
        "source": "defense_populate",
        "feed": "defense_sot_populate",
        "team": flag.team,
        "title": flag.title,
        "sot_flag": flag.sot_flag,
        "bottom_line": flag.bottom_line,
        "tier": flag.tier,
        "sla_hours": flag.sla_hours,
        "next_kei_publish": flag.next_kei_publish,
        "sources": flag.sources,
        "status": "proposed",
        "requires_human_accept": True,
        "may_auto_apply": PROPOSALS_MAY_AUTO_APPLY,
        "queued_at": _now_iso(),
        "notes": (
            "Defense populate proposed_patch only — never auto-applied. "
            "Blank pack uses create_if_missing on Accept. "
            "Do not invent starters. Empty stays empty. "
            "CLI: scripts/nfl/queue_camp_sot_flags.py --scan-defense / --queue-defense"
        ),
        "proposed_patch": {"overrides": flag.proposed_patch},
        "overrides": flag.proposed_patch,
        "contract": {
            "notes_may_touch_means": NOTES_MAY_TOUCH_MEANS,
            "notes_may_touch_props": NOTES_MAY_TOUCH_PROPS,
            "notes_may_touch_spreads": NOTES_MAY_TOUCH_SPREADS,
            "proposals_may_auto_apply": PROPOSALS_MAY_AUTO_APPLY,
            "may_invent_starters": False,
        },
    }


def queue_defense_flags(
    flags: Sequence[DepthSotWorkItem],
    *,
    proposed_dir: Path = QUEUE_RUNTIME_DEFAULT,
    accepted_log: Path = ACCEPTED_LOG_DEFAULT,
) -> QueueRunResult:
    """Upsert defense populate T1s into the same runtime queue (no pack writes)."""
    assert_notes_cannot_touch_lines()
    proposed_dir.mkdir(parents=True, exist_ok=True)
    closed = _disposition_map(accepted_log)
    result = QueueRunResult()
    for flag in flags:
        if flag.work_item_id in closed:
            result.skipped.append(f"{flag.work_item_id}:{closed[flag.work_item_id]}")
            continue
        # Prefer full-id filename so defense keys do not collide with camp as_of:TEAM.
        safe = flag.work_item_id.replace(":", "-").replace("/", "-")
        path = proposed_dir / f"work-item-{safe}.json"
        doc = proposal_doc_for_defense_flag(flag)
        if path.is_file():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                existing = None
            if existing is not None and _canonical_work_item_doc(
                existing
            ) == _canonical_work_item_doc(doc):
                result.unchanged.append(path)
                continue
            path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
            result.updated.append(path)
        else:
            path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
            result.created.append(path)
    return result


def format_populate_table(rows: Sequence[DefensePopulateRow]) -> str:
    lines = [
        "| team | player | pos | already-in-SoT | proposed T1 | pack_injury | kind |",
        "|------|--------|-----|----------------|-------------|-------------|------|",
    ]
    for r in rows:
        lines.append(
            f"| {r.team} | {r.player} | {r.position} | "
            f"{'yes' if r.already_in_sot else 'no'} | "
            f"{'T1' if r.proposed_t1 else '—'} | "
            f"{r.pack_injury or '—'} | {r.source_kind} |"
        )
    if not rows:
        lines.append("| — | (none) | — | — | — | — | — |")
    return "\n".join(lines)


# Re-export for CLI convenience.
__all__ = [
    "DURABLE_DEFENSE_FACTS",
    "DefensePopulateFact",
    "DefensePopulateRow",
    "format_populate_table",
    "queue_defense_flags",
    "scan_defense_populate",
]
