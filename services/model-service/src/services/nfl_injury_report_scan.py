"""Week-of injury report → DepthSot T1 scanner (propose only).

Sleeper (or one free report) DNP / LP / FP / Out vs live pack.

T1 only when:
  - starter OR snap_share_prior >= 0.40
  - AND (Out/IR **or** 2× DNP)
  - AND pack still full-go (not already out/ir/pup)

``proposed_patch`` only. ``confirmation=low`` unless official Out/IR.
Idempotent key: ``(player_id, event, as_of_date)``. No auto-accept.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

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
    queue_flags,
    work_item_filename,
)
from src.services.nfl_daily_intel import PACK_DEFAULT, PACK_SOT_LAYERS, normalize_override
from src.services.nfl_snap_share_prior import resolve_snap_share_prior

SLEEPER_PLAYERS_URL = "https://api.sleeper.app/v1/players/nfl"
# services/model-service/src/services → repo root is parents[4]
CACHE_DIR_DEFAULT = (
    Path(__file__).resolve().parents[4]
    / "data"
    / "ops"
    / "nfl-daily-intel"
    / "cache"
)
SLEEPER_CACHE_NAME = "sleeper_players_nfl.json"
DNP_HISTORY_NAME = "injury_report_dnp_history.json"
CACHE_TTL_SECONDS = 90 * 60  # 1.5h

SNAP_SHARE_T1_FLOOR = 0.40
REPORT_SOURCE = "sleeper"

# Pack already durable — do not re-open T1.
PACK_NOT_FULL_GO = frozenset({"out", "ir", "pup", "nfi", "suspended", "inactive", "waived"})
PACK_FULL_GO = frozenset({"", "active", "healthy", "questionable", "doubtful", "limited"})

# Sleeper / report tokens.
_OUT_TOKENS = frozenset({"out", "ir"})
def _today_as_of() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _norm_name(raw: Any) -> str:
    return " ".join(str(raw or "").lower().replace(".", " ").split())


def _norm_gsis(raw: Any) -> str:
    return str(raw or "").strip()


def _status_token(raw: Any) -> str:
    return str(raw or "").strip().lower()


def pack_is_full_go(injury_status: Any) -> bool:
    tok = _status_token(injury_status)
    if tok in PACK_NOT_FULL_GO:
        return False
    return tok in PACK_FULL_GO or tok == ""


def is_starter_row(row: Mapping[str, Any]) -> bool:
    try:
        order = int(row.get("depth_order") or 99)
    except (TypeError, ValueError):
        order = 99
    slot = str(row.get("depth_slot") or "").strip().lower()
    if order <= 1:
        return True
    if slot in {"starter", "starter_competition", "named_starter"}:
        return True
    return False


def meets_volume_gate(row: Mapping[str, Any]) -> bool:
    if is_starter_row(row):
        return True
    return resolve_snap_share_prior(row) >= SNAP_SHARE_T1_FLOOR


def classify_practice(participation: Any, description: Any) -> Optional[str]:
    """Return DNP / LP / FP or None."""
    part = _status_token(participation)
    desc = _status_token(description)
    blob = f"{part} {desc}".strip()
    if not blob:
        return None
    if "limited" in blob:
        return "LP"
    if part in {"dnp", "out"} or "did not practice" in blob or "did not participate" in blob:
        return "DNP"
    if "definitely will not play" in blob:
        return "DNP"
    if part in {"full", "fp"} or blob.startswith("full"):
        return "FP"
    return None


def classify_report_injury(injury_status: Any) -> Optional[str]:
    """Normalize Sleeper injury_status → Out | IR | Questionable | …"""
    tok = _status_token(injury_status)
    if not tok or tok in {"na", "dnr", "cov"}:
        return None
    if tok in {"out"}:
        return "Out"
    if tok in {"ir"}:
        return "IR"
    if tok in {"pup"}:
        return "PUP"
    if tok in {"doubtful"}:
        return "Doubtful"
    if tok in {"questionable"}:
        return "Questionable"
    if tok in {"sus", "suspended"}:
        return "Suspended"
    return tok.title()


def event_for_t1(*, report_out: bool, dnp_count: int) -> Optional[str]:
    """Idempotent event token for work_item key."""
    if report_out:
        return "out"
    if dnp_count >= 2:
        return "dnp2"
    return None


@dataclass
class ReportPlayer:
    sleeper_id: str
    full_name: str
    team: str
    position: str
    gsis_id: str
    injury_status: Optional[str]
    practice: Optional[str]  # DNP|LP|FP|None
    depth_chart_order: Optional[int] = None


def parse_sleeper_players(payload: Mapping[str, Any]) -> List[ReportPlayer]:
    out: List[ReportPlayer] = []
    for sid, raw in payload.items():
        if not isinstance(raw, Mapping):
            continue
        team = _norm_team(raw.get("team"))
        if not team:
            continue
        name = str(raw.get("full_name") or "").strip()
        if not name:
            continue
        pos = str(raw.get("position") or "").strip().upper()
        practice = classify_practice(
            raw.get("practice_participation"), raw.get("practice_description")
        )
        injury = classify_report_injury(raw.get("injury_status"))
        order = raw.get("depth_chart_order")
        try:
            order_i = int(order) if order is not None else None
        except (TypeError, ValueError):
            order_i = None
        out.append(
            ReportPlayer(
                sleeper_id=str(sid),
                full_name=name,
                team=team,
                position=pos,
                gsis_id=_norm_gsis(raw.get("gsis_id")),
                injury_status=injury,
                practice=practice,
                depth_chart_order=order_i,
            )
        )
    return out


def load_or_fetch_sleeper(
    *,
    cache_dir: Path = CACHE_DIR_DEFAULT,
    ttl_seconds: int = CACHE_TTL_SECONDS,
    force_refresh: bool = False,
    fetch_fn: Optional[Any] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Return (players_map, meta). Cache gitignored; TTL 1–2h."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / SLEEPER_CACHE_NAME
    now = time.time()
    if path.is_file() and not force_refresh:
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
            as_of = float(cached.get("fetched_at") or 0)
            if now - as_of <= ttl_seconds and isinstance(cached.get("players"), dict):
                return cached["players"], {
                    "cache_hit": True,
                    "fetched_at": cached.get("fetched_at_iso"),
                    "path": str(path),
                }
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass

    if fetch_fn is not None:
        players = fetch_fn()
    else:
        req = urllib.request.Request(
            SLEEPER_PLAYERS_URL,
            headers={"User-Agent": "kosedge-injury-report/1.0"},
        )
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                players = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            if path.is_file():
                cached = json.loads(path.read_text(encoding="utf-8"))
                return cached.get("players") or {}, {
                    "cache_hit": True,
                    "stale": True,
                    "error": str(exc),
                    "fetched_at": cached.get("fetched_at_iso"),
                }
            raise

    if not isinstance(players, dict):
        raise ValueError("Sleeper players payload must be an object")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    path.write_text(
        json.dumps(
            {"fetched_at": now, "fetched_at_iso": stamp, "players": players},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return players, {"cache_hit": False, "fetched_at": stamp, "path": str(path)}


def load_dnp_history(cache_dir: Path = CACHE_DIR_DEFAULT) -> Dict[str, List[str]]:
    path = cache_dir / DNP_HISTORY_NAME
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out: Dict[str, List[str]] = {}
    for k, v in (raw.get("by_player") or {}).items():
        if isinstance(v, list):
            out[str(k)] = sorted({str(x) for x in v})
    return out


def save_dnp_history(
    history: Mapping[str, Sequence[str]],
    *,
    cache_dir: Path = CACHE_DIR_DEFAULT,
    as_of: str,
) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / DNP_HISTORY_NAME
    path.write_text(
        json.dumps(
            {
                "as_of": as_of,
                "updated_at": _now_iso(),
                "by_player": {k: list(v) for k, v in history.items()},
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def update_dnp_history(
    history: Dict[str, List[str]],
    players: Sequence[ReportPlayer],
    *,
    as_of: str,
) -> Dict[str, List[str]]:
    """Append today's DNP marks; idempotent per (player, as_of)."""
    out = {k: list(v) for k, v in history.items()}
    for p in players:
        if p.practice != "DNP":
            continue
        key = p.gsis_id or f"sleeper:{p.sleeper_id}"
        days = set(out.get(key) or [])
        days.add(as_of)
        out[key] = sorted(days)
    return out


def dnp_count_for(history: Mapping[str, Sequence[str]], player_key: str) -> int:
    return len(list(history.get(player_key) or []))


def iter_pack_players(pack: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for layer in PACK_SOT_LAYERS:
        for row in pack.get(layer) or []:
            if not isinstance(row, dict):
                continue
            enriched = dict(row)
            enriched["_layer"] = layer
            rows.append(enriched)
    return rows


def match_pack_row(
    pack_rows: Sequence[Mapping[str, Any]],
    report: ReportPlayer,
) -> Optional[Mapping[str, Any]]:
    gsis = report.gsis_id
    if gsis:
        for row in pack_rows:
            if _norm_gsis(row.get("player_id")) == gsis:
                return row
    name = _norm_name(report.full_name)
    team = report.team
    pos = report.position
    for row in pack_rows:
        if _norm_team(row.get("team")) != team:
            continue
        if _norm_name(row.get("player_name")) != name:
            continue
        row_pos = str(row.get("position") or "").upper()
        # Soft pos match — Sleeper DL vs pack EDGE, etc.
        if pos and row_pos and pos != row_pos:
            if not (
                {pos, row_pos} <= {"DL", "EDGE", "DE", "DT"}
                or {pos, row_pos} <= {"DB", "CB", "S", "NB", "FS", "SS"}
                or {pos, row_pos} <= {"LB", "ILB", "OLB"}
            ):
                continue
        return row
    return None


@dataclass
class InjuryReportT1:
    team: str
    player_name: str
    player_id: str
    position: str
    layer: str
    event: str  # out | dnp2
    report_status: str
    practice: str
    dnp_count: int
    snap_share_prior: float
    starter: bool
    pack_injury: str
    confirmation: str
    work_item_id: str
    proposed_patch: List[Dict[str, Any]] = field(default_factory=list)
    source: str = REPORT_SOURCE

    def as_dict(self) -> Dict[str, Any]:
        return {
            "team": self.team,
            "player": self.player_name,
            "player_id": self.player_id,
            "position": self.position,
            "event": self.event,
            "report_status": self.report_status,
            "practice": self.practice,
            "dnp_count": self.dnp_count,
            "snap_share_prior": self.snap_share_prior,
            "starter": self.starter,
            "pack_injury": self.pack_injury,
            "confirmation": self.confirmation,
            "source": self.source,
            "work_item_id": self.work_item_id,
            "proposed_patch": self.proposed_patch,
        }


def work_item_id_for_report(*, player_id: str, event: str, as_of: str) -> str:
    safe = str(player_id).replace(" ", "").replace(":", "-").replace("/", "-")
    return f"{as_of}:injury-report:{safe}:{event}"


def _build_patch(
    *,
    pack_row: Mapping[str, Any],
    report: ReportPlayer,
    event: str,
    confirmation: str,
    as_of: str,
) -> List[Dict[str, Any]]:
    after = "ir" if report.injury_status == "IR" else "out"
    current = pack_row.get("injury_status")
    ov = {
        "team": _norm_team(pack_row.get("team")),
        "player_name": pack_row.get("player_name"),
        "player_id": str(pack_row.get("player_id") or ""),
        "position": str(pack_row.get("position") or "").upper(),
        "layer": pack_row.get("_layer") or "rows",
        "field": "injury_status",
        "before": current,
        "after": after,
        "reason": (
            f"Week-of injury report ({REPORT_SOURCE}): "
            f"{report.injury_status or report.practice or event}"
        ),
        "as_of": as_of,
        "confidence": "high" if confirmation == "high" else "low",
        "confirmation": confirmation,
        "destination": "kei_only",
        "sources": [f"{REPORT_SOURCE}:injury_report:{as_of}"],
        "draft": True,
    }
    try:
        clean = normalize_override(ov)
    except ValueError:
        return []
    return [{**clean, "draft": True, "confirmation": confirmation}]


def scan_injury_report(
    *,
    pack_path: Path = PACK_DEFAULT,
    cache_dir: Path = CACHE_DIR_DEFAULT,
    as_of: Optional[str] = None,
    force_refresh: bool = False,
    sleeper_players: Optional[Mapping[str, Any]] = None,
    dnp_history: Optional[Dict[str, List[str]]] = None,
    accepted_log: Path = ACCEPTED_LOG_DEFAULT,
    proposed_dir: Path = QUEUE_RUNTIME_DEFAULT,
) -> Tuple[List[DepthSotWorkItem], List[InjuryReportT1], Dict[str, Any]]:
    """Diff report vs pack → T1 work items. Never writes pack/means."""
    assert_notes_cannot_touch_lines()
    assert PROPOSALS_MAY_AUTO_APPLY is False
    day = as_of or _today_as_of()
    meta: Dict[str, Any] = {"as_of": day, "source": REPORT_SOURCE}

    if sleeper_players is None:
        players_map, fetch_meta = load_or_fetch_sleeper(
            cache_dir=cache_dir, force_refresh=force_refresh
        )
        meta["fetch"] = fetch_meta
    else:
        players_map = dict(sleeper_players)
        meta["fetch"] = {"cache_hit": False, "fixture": True}

    reports = parse_sleeper_players(players_map)
    hist = dnp_history if dnp_history is not None else load_dnp_history(cache_dir)
    hist = update_dnp_history(hist, reports, as_of=day)
    if dnp_history is None:
        save_dnp_history(hist, cache_dir=cache_dir, as_of=day)
    meta["dnp_players_tracked"] = len(hist)

    pack = load_pack(pack_path)
    pack_rows = iter_pack_players(pack)
    closed = _disposition_map(accepted_log)
    queued = _queued_flag_ids(proposed_dir)
    clock = _now_utc()

    t1_rows: List[InjuryReportT1] = []
    items: List[DepthSotWorkItem] = []

    for report in reports:
        pack_row = match_pack_row(pack_rows, report)
        if pack_row is None:
            continue
        if not pack_is_full_go(pack_row.get("injury_status")):
            continue
        if not meets_volume_gate(pack_row):
            continue

        player_key = report.gsis_id or f"sleeper:{report.sleeper_id}"
        # Include today's DNP in count before gate.
        dnp_n = dnp_count_for(hist, player_key)
        report_out = report.injury_status in {"Out", "IR"}
        event = event_for_t1(report_out=report_out, dnp_count=dnp_n)
        if not event:
            continue

        # Official Out/IR → high; 2× DNP without Out → low.
        confirmation = "high" if report_out else "low"
        pid = str(pack_row.get("player_id") or player_key)
        wid = work_item_id_for_report(player_id=pid, event=event, as_of=day)
        patch = _build_patch(
            pack_row=pack_row,
            report=report,
            event=event,
            confirmation=confirmation,
            as_of=day,
        )
        if not patch:
            continue

        row = InjuryReportT1(
            team=_norm_team(pack_row.get("team")),
            player_name=str(pack_row.get("player_name") or report.full_name),
            player_id=pid,
            position=str(pack_row.get("position") or report.position).upper(),
            layer=str(pack_row.get("_layer") or "rows"),
            event=event,
            report_status=str(report.injury_status or ""),
            practice=str(report.practice or ""),
            dnp_count=dnp_n,
            snap_share_prior=resolve_snap_share_prior(pack_row),
            starter=is_starter_row(pack_row),
            pack_injury=str(pack_row.get("injury_status") or "(blank)"),
            confirmation=confirmation,
            work_item_id=wid,
            proposed_patch=patch,
        )

        if wid in closed:
            continue

        try:
            start = desk_date_start_utc(day)
        except ValueError:
            start = clock
        age_h = max(0.0, (clock - start).total_seconds() / 3600.0)
        tier = "T1"
        sla = TIER_SLA_HOURS[tier]
        overdue, overdue_reason = _is_overdue(
            tier=tier, age_h=age_h, sla_hours=sla, desk_start=start, now=clock
        )
        status = "queued" if wid in queued else ("overdue" if overdue else "open")
        flag = f"{report.injury_status or ''} {report.practice or ''} → {event}".strip()
        item = DepthSotWorkItem(
            work_item_id=wid,
            desk_date=day,
            team=row.team,
            note_id=f"injury-report:{pid}:{event}",
            title=f"Injury report {event}: {row.player_name}",
            sot_flag=flag,
            bottom_line=(
                f"{row.player_name} {row.position} report={row.report_status or row.practice} "
                f"pack={row.pack_injury} confirmation={confirmation}"
            ),
            tier=tier,
            sla_hours=sla,
            next_kei_publish=next_kei_publish_utc(start).strftime("%Y-%m-%dT%H:%M:%SZ"),
            sources=[{"label": REPORT_SOURCE, "href": SLEEPER_PLAYERS_URL}],
            proposed_patch=patch,
            status=status,
            overdue=overdue,
            overdue_reason=overdue_reason,
            age_hours=age_h,
        )
        t1_rows.append(row)
        items.append(item)

    t1_rows.sort(key=lambda r: (r.team, r.player_name, r.event))
    items.sort(key=lambda f: (f.team, f.work_item_id))
    meta["t1_count"] = len(t1_rows)
    return items, t1_rows, meta


def proposal_doc_for_injury_report(flag: DepthSotWorkItem) -> Dict[str, Any]:
    return {
        "schema": WORK_ITEM_SCHEMA,
        "work_item_id": flag.work_item_id,
        "note_id": flag.note_id,
        "flag_id": flag.work_item_id,
        "as_of": flag.desk_date,
        "team_id": flag.team,
        "source": REPORT_SOURCE,
        "feed": "injury_report",
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
            "Week-of injury report proposed_patch only — never auto-applied. "
            "confirmation=low unless official Out/IR."
        ),
        "proposed_patch": {"overrides": flag.proposed_patch},
        "overrides": flag.proposed_patch,
        "contract": {
            "notes_may_touch_means": NOTES_MAY_TOUCH_MEANS,
            "notes_may_touch_props": NOTES_MAY_TOUCH_PROPS,
            "notes_may_touch_spreads": NOTES_MAY_TOUCH_SPREADS,
            "proposals_may_auto_apply": PROPOSALS_MAY_AUTO_APPLY,
        },
    }


def queue_injury_report_flags(
    flags: Sequence[DepthSotWorkItem],
    *,
    proposed_dir: Path = QUEUE_RUNTIME_DEFAULT,
    accepted_log: Path = ACCEPTED_LOG_DEFAULT,
) -> QueueRunResult:
    """Upsert injury-report T1s. Idempotent; no pack writes."""
    assert_notes_cannot_touch_lines()
    proposed_dir.mkdir(parents=True, exist_ok=True)
    closed = _disposition_map(accepted_log)
    result = QueueRunResult()
    for flag in flags:
        if flag.work_item_id in closed:
            result.skipped.append(f"{flag.work_item_id}:{closed[flag.work_item_id]}")
            continue
        path = proposed_dir / work_item_filename(flag.work_item_id)
        doc = proposal_doc_for_injury_report(flag)
        new_body = _canonical_work_item_doc(doc)
        if path.is_file():
            try:
                old = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                old = {}
            if _canonical_work_item_doc(old) == new_body:
                result.unchanged.append(path)
                continue
            path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
            result.updated.append(path)
        else:
            path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
            result.created.append(path)
    return result


def format_t1_table(rows: Sequence[InjuryReportT1]) -> str:
    if not rows:
        return "team | player | event | confirmation | pack | source\n(none)"
    lines = [
        "team | player | pos | event | confirmation | starter | snap | pack | report | source"
    ]
    for r in rows:
        lines.append(
            f"{r.team} | {r.player_name} | {r.position} | {r.event} | "
            f"{r.confirmation} | {r.starter} | {r.snap_share_prior:.2f} | "
            f"{r.pack_injury} | {r.report_status or r.practice or '-'} | {r.source}"
        )
    return "\n".join(lines)


# Re-export queue_flags for callers that mix camp + report alerts.
__all__ = [
    "scan_injury_report",
    "queue_injury_report_flags",
    "format_t1_table",
    "load_or_fetch_sleeper",
    "REPORT_SOURCE",
    "queue_flags",
]
