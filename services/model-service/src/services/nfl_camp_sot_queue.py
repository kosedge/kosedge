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

import hashlib
import json
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

from src.services.nfl_daily_intel import (
    ALLOWED_FIELDS,
    PACK_DEFAULT,
    apply_intel_overrides,
    format_smoke_diff,
    kei_smoke_for_teams,
    normalize_override,
)

ET = ZoneInfo("America/New_York")
# Midweek + Friday final KEI publish (matches nfl-injury-kei-cadence config).
_KEI_PUBLISH_WEEKDAYS = (3, 4)  # Thu, Fri
_KEI_PUBLISH_HOUR_ET = 16
_KEI_PUBLISH_MINUTE_ET = 0


# Hard contract — notes must never touch projection / market numbers.
NOTES_MAY_TOUCH_MEANS = False
NOTES_MAY_TOUCH_PROPS = False
NOTES_MAY_TOUCH_SPREADS = False
PROPOSALS_MAY_AUTO_APPLY = False

_SERVICES = Path(__file__).resolve().parent


def _resolve_repo_root() -> Path:
    """Monorepo checkout *or* Railway ``path-as-root`` image (WORKDIR=/app)."""
    candidates = [
        _SERVICES.parents[3],  # …/repo (services/model-service/src/services)
        _SERVICES.parents[2],  # …/model-service or /app
        Path("/app"),
        Path.cwd(),
    ]
    for root in candidates:
        if (root / "content" / "writers" / "camp-desk-2026").is_dir():
            return root
        if (root / "src" / "services" / "nfl_camp_sot_queue.py").is_file() and (
            root / "src" / "services" / "nfl_season_engine"
        ).is_dir():
            # Image without camp desk still resolves for pack/receipts under /app
            return root
    return _SERVICES.parents[2]


_REPO = _resolve_repo_root()
CAMP_DESK_DEFAULT = _REPO / "content" / "writers" / "camp-desk-2026"
# Runtime queue — generated work items; not committed (see .gitignore).
QUEUE_RUNTIME_DEFAULT = _REPO / "data" / "ops" / "nfl-daily-intel" / "queue" / "runtime"
PROPOSED_DEFAULT = QUEUE_RUNTIME_DEFAULT  # alias
PENDING_DEFAULT = _REPO / "data" / "ops" / "nfl-daily-intel" / "pending"
ACCEPTED_LOG_DEFAULT = (
    _REPO / "data" / "ops" / "nfl-daily-intel" / "accepted" / "camp-sot-log.jsonl"
)
RECEIPTS_DEFAULT = _REPO / "data" / "ops" / "nfl-daily-intel" / "receipts"

WORK_ITEM_SCHEMA = "nfl-depth-sot-work-item/v1"
RECEIPT_SCHEMA = "nfl-depth-sot-receipt/v1"

# T1 same-day · T2 next remat · T3 Pass (no pack write expected)
TIER_SLA_HOURS = {"T1": 12, "T2": 48, "T3": 72}
DEFAULT_OVERDUE_HOURS = TIER_SLA_HOURS["T1"]  # scan fallback; per-item SLA wins
# T1 also overdue at next KEI publish (Thu/Fri 16:00 ET) — see next_kei_publish_utc.

SAFE_REMAT_HINT = (
    "POST /nfl/ops/rebuild-props-layers?season=2026"
    "&weeks=1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18"
)

CLOSED_DISPOSITIONS = frozenset({"accepted", "reject", "no_change"})
# remat_failed is audited but does NOT close the ticket (retryable; pack rolled back).


@dataclass
class RematResult:
    """Outcome of the rematerialize step. Fail ⇒ accept disposition is not written."""

    ok: bool
    run_id: str = ""
    error: str = ""
    mode: str = "enqueue"  # enqueue | receipt_only | dry_run


RematFn = Callable[[], RematResult]


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def receipt_only_remat() -> RematResult:
    """Desk default when enqueue is not wired — still yields a remat_run_id."""
    return RematResult(ok=True, run_id=f"receipt-only-{uuid.uuid4().hex[:12]}", mode="receipt_only")


def failing_remat(message: str = "remat failed") -> RematFn:
    def _fn() -> RematResult:
        return RematResult(ok=False, run_id="", error=message, mode="enqueue")

    return _fn


DEFAULT_REMAT_WEEKS = list(range(1, 19))


def enqueue_props_layer_remat(
    *,
    season: int = 2026,
    weeks: Optional[Sequence[int]] = None,
) -> RematResult:
    """Enqueue Celery ``run_nfl_props_layer_rebuild`` — real remat_run_id = task id.

    Prefer this on the API/worker. Never return ``receipt-only-*`` when enqueue works.
    """
    week_list = list(weeks) if weeks else list(DEFAULT_REMAT_WEEKS)
    try:
        from src.celery_app import QUEUE_MODELS, celery_app
    except Exception as exc:  # pragma: no cover - import env
        return RematResult(ok=False, run_id="", error=f"celery import failed: {exc}", mode="enqueue")
    task_name = "src.tasks.run_nfl_props_layer_rebuild"
    try:
        task = celery_app.send_task(
            task_name,
            kwargs={
                "season": int(season),
                "week": None,
                "weeks": week_list,
                "model_version": "nfl-player-v1",
                "replace_features": True,
                "rematerialize_season_features": False,
            },
            queue=QUEUE_MODELS,
        )
        run_id = str(getattr(task, "id", "") or "")
        if not run_id:
            return RematResult(ok=False, run_id="", error="enqueue returned empty task id", mode="enqueue")
        return RematResult(ok=True, run_id=run_id, mode="enqueue")
    except Exception as exc:
        return RematResult(ok=False, run_id="", error=str(exc), mode="enqueue")


def http_props_layer_remat(
    *,
    base_url: Optional[str] = None,
    season: int = 2026,
    weeks: Optional[Sequence[int]] = None,
) -> RematResult:
    """CLI/prod bridge: POST ``/nfl/ops/rebuild-props-layers``; remat_run_id = task_id."""
    import json as _json
    import urllib.error
    import urllib.parse
    import urllib.request

    root = (base_url or os.environ.get("MODEL_SERVICE_URL") or "").strip().rstrip("/")
    # Prefer the full model-service host when env points at a thin edge proxy.
    if "kosedge-production.up.railway.app" in root or not root:
        root = "https://model-service-production-e253.up.railway.app"
    week_list = list(weeks) if weeks else list(DEFAULT_REMAT_WEEKS)
    weeks_q = ",".join(str(w) for w in week_list)
    url = (
        f"{root}/nfl/ops/rebuild-props-layers?"
        + urllib.parse.urlencode({"season": int(season), "weeks": weeks_q})
    )
    try:
        req = urllib.request.Request(url, method="POST", data=b"")
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = _json.loads(resp.read().decode("utf-8"))
        task_id = str(payload.get("task_id") or "")
        if not task_id:
            return RematResult(ok=False, run_id="", error=f"no task_id in {payload!r}", mode="enqueue")
        return RematResult(ok=True, run_id=task_id, mode="enqueue")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:300]
        return RematResult(ok=False, run_id="", error=f"HTTP {exc.code}: {body}", mode="enqueue")
    except Exception as exc:
        return RematResult(ok=False, run_id="", error=str(exc), mode="enqueue")


def live_remat_fn() -> RematFn:
    """Prefer Celery enqueue; fall back to HTTP rebuild-props (never receipt-only)."""

    def _fn() -> RematResult:
        via_celery = enqueue_props_layer_remat()
        if via_celery.ok:
            return via_celery
        via_http = http_props_layer_remat()
        if via_http.ok:
            return via_http
        return RematResult(
            ok=False,
            run_id="",
            error=f"celery:{via_celery.error}; http:{via_http.error}",
            mode="enqueue",
        )

    return _fn


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


def next_kei_publish_utc(after: datetime) -> datetime:
    """Next Thu/Fri 16:00 America/New_York at or after ``after`` (UTC-aware)."""
    if after.tzinfo is None:
        after = after.replace(tzinfo=timezone.utc)
    local = after.astimezone(ET)
    for offset in range(0, 10):
        day = (local + timedelta(days=offset)).date()
        if day.weekday() not in _KEI_PUBLISH_WEEKDAYS:
            continue
        candidate = datetime(
            day.year,
            day.month,
            day.day,
            _KEI_PUBLISH_HOUR_ET,
            _KEI_PUBLISH_MINUTE_ET,
            tzinfo=ET,
        )
        if candidate >= local:
            return candidate.astimezone(timezone.utc)
    # Fallback: +7d Thursday
    return (local + timedelta(days=7)).astimezone(timezone.utc)


def work_item_id_for(*, as_of: str, team_id: str, note_id: Optional[str] = None) -> str:
    """Stable id: note_id + team_id + as_of (idempotent queue key)."""
    team = _norm_team(team_id)
    nid = (note_id or f"note-{as_of}-{team}").strip()
    return f"{as_of}:{team}:{nid}"


def work_item_filename(work_item_id: str) -> str:
    """Stable runtime filename from work_item_id (no duplicates on re-queue)."""
    # as_of:TEAM:note-as_of-TEAM → work-item-as_of-TEAM.json
    parts = work_item_id.split(":")
    if len(parts) >= 2:
        return f"work-item-{parts[0]}-{parts[1]}.json"
    return f"work-item-{work_item_id.replace(':', '-')}.json"


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
    note_id: str = ""
    tier: str = "T2"
    sla_hours: int = 48
    next_kei_publish: str = ""
    sources: List[Dict[str, Any]] = field(default_factory=list)
    proposed_patch: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "open"  # open | queued | accepted | overdue | pass | reject | no_change
    overdue: bool = False
    age_hours: float = 0.0
    overdue_reason: str = ""

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
            "note_id": self.note_id,
            "flag_id": self.work_item_id,
            "desk_date": self.desk_date,
            "as_of": self.desk_date,
            "team": self.team,
            "team_id": self.team,
            "title": self.title,
            "sot_flag": self.sot_flag,
            "bottom_line": self.bottom_line,
            "tier": self.tier,
            "sla_hours": self.sla_hours,
            "next_kei_publish": self.next_kei_publish,
            "sources": self.sources,
            "proposed_patch": {"overrides": self.proposed_patch},
            "draft_overrides": self.proposed_patch,
            "status": self.status,
            "overdue": self.overdue,
            "overdue_reason": self.overdue_reason,
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


def _disposition_map(log_path: Path) -> Dict[str, str]:
    """work_item_id → disposition (accepted|reject|no_change)."""
    if not log_path.is_file():
        return {}
    out: Dict[str, str] = {}
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        fid = str(row.get("work_item_id") or row.get("flag_id") or "")
        disp = str(row.get("disposition") or row.get("status") or "")
        if not fid:
            continue
        if disp in CLOSED_DISPOSITIONS:
            out[fid] = disp
        elif row.get("wrote_pack") is not None or row.get("accepted_at"):
            out[fid] = "accepted"
    return out


def _accepted_flag_ids(log_path: Path) -> set[str]:
    return set(_disposition_map(log_path))


def _queued_flag_ids(proposed_dir: Path) -> Dict[str, Path]:
    if not proposed_dir.is_dir():
        return {}
    ids: Dict[str, Path] = {}
    for path in list(proposed_dir.glob("work-item-*.json")) + list(
        proposed_dir.glob("camp-flag-*.json")
    ):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        fid = str(doc.get("work_item_id") or doc.get("flag_id") or "")
        if fid:
            ids[fid] = path
    return ids


def _is_overdue(
    *,
    tier: str,
    age_h: float,
    sla_hours: int,
    desk_start: datetime,
    now: datetime,
) -> Tuple[bool, str]:
    if age_h >= sla_hours:
        return True, f"age_h>={sla_hours}"
    if tier == "T1":
        deadline = next_kei_publish_utc(desk_start)
        if now >= deadline:
            return True, f"past_kei_publish:{deadline.strftime('%Y-%m-%dT%H:%MZ')}"
    return False, ""


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
    closed = _disposition_map(accepted_log)
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
        kei_deadline = next_kei_publish_utc(start)
        for note in day.get("team_notes") or []:
            if not isinstance(note, dict) or not note.get("is_material_depth"):
                continue
            team = _norm_team(note.get("team_id"))
            sot_flag = str(note.get("sot_flag") or "").strip()
            if not team:
                continue
            note_id = f"note-{desk_date}-{team}"
            wid = work_item_id_for(as_of=desk_date, team_id=team, note_id=note_id)
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
            overdue, overdue_reason = _is_overdue(
                tier=tier,
                age_h=age_h,
                sla_hours=sla,
                desk_start=start,
                now=clock,
            )
            if wid in closed:
                status = closed[wid]
                overdue = False
                overdue_reason = ""
            elif wid in queued:
                status = "queued"
            else:
                if tier == "T3" and not patch and not overdue:
                    status = "pass"
                else:
                    status = "overdue" if overdue else "open"
            items.append(
                DepthSotWorkItem(
                    work_item_id=wid,
                    desk_date=desk_date,
                    team=team,
                    note_id=note_id,
                    title=str(note.get("title") or ""),
                    sot_flag=sot_flag,
                    bottom_line=str(note.get("bottom_line") or ""),
                    tier=tier,
                    sla_hours=sla,
                    next_kei_publish=kei_deadline.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    sources=list(note.get("sources") or []),
                    proposed_patch=patch,
                    status=status,
                    overdue=overdue,
                    overdue_reason=overdue_reason,
                    age_hours=age_h,
                )
            )
    items.sort(
        key=lambda f: (
            0 if f.tier == "T1" else 1 if f.tier == "T2" else 2,
            -int(f.overdue),
            f.team,
        )
    )
    return items


def proposal_doc_for_flag(flag: DepthSotWorkItem) -> Dict[str, Any]:
    """Serialize a DepthSotWorkItem for the runtime queue (never auto-applied)."""
    return {
        "schema": WORK_ITEM_SCHEMA,
        "work_item_id": flag.work_item_id,
        "note_id": flag.note_id,
        "flag_id": flag.work_item_id,
        "as_of": flag.desk_date,
        "team_id": flag.team,
        "source": "camp_desk",
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
            "Proposed pack patch only — never auto-applied. "
            "Notes must not touch means/props/spreads. "
            "Accept → pack write → rematerialize → receipt. "
            "reject / no_change writes nothing. "
            "CLI: scripts/nfl/queue_camp_sot_flags.py --accept|--reject|--no-change"
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


def _canonical_work_item_doc(doc: Mapping[str, Any]) -> str:
    """Compare queue docs ignoring queued_at timestamps."""
    payload = {k: v for k, v in doc.items() if k != "queued_at"}
    return json.dumps(payload, sort_keys=True, default=str)


@dataclass
class QueueRunResult:
    created: List[Path] = field(default_factory=list)
    updated: List[Path] = field(default_factory=list)
    unchanged: List[Path] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)

    @property
    def written(self) -> List[Path]:
        return [*self.created, *self.updated]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "created": [str(p) for p in self.created],
            "updated": [str(p) for p in self.updated],
            "unchanged": [str(p) for p in self.unchanged],
            "skipped": list(self.skipped),
            "created_count": len(self.created),
            "updated_count": len(self.updated),
            "unchanged_count": len(self.unchanged),
        }


def queue_flags(
    flags: Sequence[DepthSotWorkItem],
    *,
    proposed_dir: Path = PROPOSED_DEFAULT,
    accepted_log: Path = ACCEPTED_LOG_DEFAULT,
    only_overdue: bool = False,
    only_with_drafts: bool = False,
    tiers: Optional[Sequence[str]] = None,
) -> QueueRunResult:
    """Upsert DepthSotWorkItem JSON by note_id+team_id+as_of. Idempotent.

    Does not touch the depth pack or means. Re-runs update in place — no duplicates.
    """
    assert_notes_cannot_touch_lines()
    proposed_dir.mkdir(parents=True, exist_ok=True)
    closed = _disposition_map(accepted_log)
    wanted = {t.upper() for t in tiers} if tiers else None
    result = QueueRunResult()
    for flag in flags:
        if flag.work_item_id in closed:
            result.skipped.append(f"{flag.work_item_id}:{closed[flag.work_item_id]}")
            continue
        if flag.status in CLOSED_DISPOSITIONS:
            result.skipped.append(f"{flag.work_item_id}:{flag.status}")
            continue
        if only_overdue and not flag.overdue:
            continue
        if only_with_drafts and not flag.proposed_patch:
            continue
        if wanted and flag.tier not in wanted:
            continue
        path = proposed_dir / work_item_filename(flag.work_item_id)
        doc = proposal_doc_for_flag(flag)
        if path.is_file():
            try:
                old = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                old = {}
            # Preserve original queued_at for stable identity.
            if old.get("queued_at"):
                doc["queued_at"] = old["queued_at"]
            if _canonical_work_item_doc(old) == _canonical_work_item_doc(doc):
                result.unchanged.append(path)
                continue
            path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
            result.updated.append(path)
        else:
            path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
            result.created.append(path)
    return result


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


def pack_diff_from_apply(apply_result: Optional[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    if not apply_result:
        return []
    rows = []
    for item in apply_result.get("applied") or []:
        rows.append(
            {
                "team": item.get("team"),
                "player_name": item.get("player_name"),
                "field": item.get("field"),
                "before": item.get("previous", item.get("before")),
                "after": item.get("after"),
            }
        )
    return rows


def line_delta_from_kei(
    before_rows: Sequence[Mapping[str, Any]],
    after_rows: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    before = {str(r.get("game")): r for r in before_rows}
    deltas: List[Dict[str, Any]] = []
    for row in after_rows:
        game = str(row.get("game"))
        prev = before.get(game) or {}
        d_spread = float(row.get("spread_delta") or 0) - float(prev.get("spread_delta") or 0)
        d_total = float(row.get("total_delta") or 0) - float(prev.get("total_delta") or 0)
        new_factors = [
            f for f in (row.get("factors") or []) if f not in (prev.get("factors") or [])
        ]
        if abs(d_spread) > 1e-9 or abs(d_total) > 1e-9 or new_factors:
            deltas.append(
                {
                    "game": game,
                    "spread_delta": round(d_spread, 3),
                    "total_delta": round(d_total, 3),
                    "new_factors": new_factors,
                }
            )
    return deltas


def write_receipt(
    *,
    work_item_id: str,
    tier: str,
    pending_path: Optional[Path],
    wrote_pack: bool,
    apply_result: Optional[Mapping[str, Any]],
    rematerialize_status: str,
    disposition: str,
    pack_diff: Optional[Sequence[Mapping[str, Any]]] = None,
    line_delta: Optional[Sequence[Mapping[str, Any]]] = None,
    actor: str = "",
    reason: str = "",
    pack_before_sha256: str = "",
    pack_after_sha256: str = "",
    remat_run_id: str = "",
    remat_error: str = "",
    receipts_dir: Path = RECEIPTS_DEFAULT,
) -> Path:
    receipts_dir.mkdir(parents=True, exist_ok=True)
    safe_id = work_item_id.replace(":", "-")
    path = receipts_dir / f"receipt-{safe_id}.json"
    payload = {
        "schema": RECEIPT_SCHEMA,
        "work_item_id": work_item_id,
        "tier": tier,
        "disposition": disposition,
        "actor": actor or "unknown",
        "reason": reason,
        "accepted_at": _now_iso(),
        "pending": str(pending_path) if pending_path else None,
        "wrote_pack": wrote_pack,
        "pack_before_sha256": pack_before_sha256,
        "pack_after_sha256": pack_after_sha256,
        "pack_diff": list(pack_diff or []),
        "line_delta": list(line_delta or []),
        "apply": dict(apply_result) if apply_result else None,
        "rematerialize": {
            "status": rematerialize_status,
            "run_id": remat_run_id or None,
            "error": remat_error or None,
            "entrypoint": SAFE_REMAT_HINT if rematerialize_status.startswith("required") or remat_run_id else None,
            "ops_note": "data/ops/nfl-spine-safe-rematerialize.md",
            "rule": (
                "Accept is the only gate that may rematerialize. "
                "Remat fail ≠ accepted (pack rolled back)."
            ),
        },
        "audit": {
            "actor": actor or "unknown",
            "reason": reason,
            "pack_before_sha256": pack_before_sha256,
            "pack_after_sha256": pack_after_sha256,
            "remat_run_id": remat_run_id or None,
            "line_delta_count": len(list(line_delta or [])),
            "pack_diff_count": len(list(pack_diff or [])),
        },
        "contract": {
            "notes_may_touch_means": NOTES_MAY_TOUCH_MEANS,
            "notes_may_touch_props": NOTES_MAY_TOUCH_PROPS,
            "notes_may_touch_spreads": NOTES_MAY_TOUCH_SPREADS,
            "proposals_may_auto_apply": PROPOSALS_MAY_AUTO_APPLY,
            "public_accept_ui": False,
            "internal_auth_only": True,
        },
        "board_path": (
            "depth pack → rematerialize weeks 1–18 → props/fantasy/KEI inherit"
            if wrote_pack
            else "no pack write — board unchanged"
        ),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _append_disposition_log(
    log_path: Path,
    row: Mapping[str, Any],
) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(dict(row)) + "\n")


def _unlink_queue_file(proposal_path: Path) -> None:
    if proposal_path.is_file() and (
        proposal_path.parent == PROPOSED_DEFAULT
        or "runtime" in proposal_path.parts
        or "proposed" in proposal_path.parts
        or "queue" in proposal_path.parts
    ):
        proposal_path.unlink()


def _preview_pack_apply(
    *,
    pack_path: Path,
    overrides: Sequence[Mapping[str, Any]],
    as_of: str,
) -> Tuple[str, str, List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """In-memory pack apply for dry-run. Never writes the pack."""
    backup = pack_path.read_bytes()
    pack_before_sha = _sha256_bytes(backup)
    pack_before = json.loads(backup.decode("utf-8"))
    teams = sorted({str(o.get("team") or "") for o in overrides if o.get("team")})
    before_smoke = kei_smoke_for_teams(pack_before, teams) if teams else []
    result = apply_intel_overrides(pack_before, overrides, as_of=as_of or None)
    new_raw = (json.dumps(result.payload, indent=2) + "\n").encode("utf-8")
    pack_after_sha = _sha256_bytes(new_raw)
    apply_result = result.as_dict()
    pack_diff = pack_diff_from_apply(apply_result)
    after_smoke = (
        kei_smoke_for_teams(result.payload, result.touched_teams)
        if result.touched_teams
        else []
    )
    line_delta = line_delta_from_kei(before_smoke, after_smoke)
    apply_result = {
        **apply_result,
        "kei_smoke_lines": format_smoke_diff(before_smoke, after_smoke),
    }
    return pack_before_sha, pack_after_sha, pack_diff, line_delta, apply_result


def accept_proposal(
    proposal_path: Path,
    *,
    pack_path: Path = PACK_DEFAULT,
    pending_dir: Path = PENDING_DEFAULT,
    accepted_log: Path = ACCEPTED_LOG_DEFAULT,
    receipts_dir: Path = RECEIPTS_DEFAULT,
    write_pack: bool = False,
    rematerialize: bool = False,
    remat_fn: Optional[RematFn] = None,
    allow_empty_overrides: bool = False,
    actor: str = "",
    reason: str = "",
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Accept a DepthSotWorkItem with enterprise gate semantics.

    - Notes never rewrite means.
    - ``proposed_patch`` never auto-applies (caller must Accept).
    - Pack write happens only here.
    - If ``rematerialize`` is set and remat fails: pack is rolled back and
      disposition is ``remat_failed`` (not accepted). Ticket stays open.
    - ``dry_run`` previews pack_diff / line_delta and writes nothing
      (pack, pending, disposition log, queue unlink all skipped).
    """
    assert_notes_cannot_touch_lines()
    if dry_run and write_pack:
        raise ValueError("dry_run cannot combine with --write")
    if rematerialize and not write_pack and not dry_run:
        raise ValueError("rematerialize requires --write (accept is the only remat gate)")

    doc = json.loads(proposal_path.read_text(encoding="utf-8"))
    work_item_id = str(doc.get("work_item_id") or doc.get("flag_id") or "")
    closed = _disposition_map(accepted_log)
    if work_item_id in closed:
        raise ValueError(
            f"work item {work_item_id} already closed as {closed[work_item_id]} "
            "(accept remats once)"
        )

    tier = str(doc.get("tier") or "T2")
    overrides_raw = _overrides_from_doc(doc)
    if not overrides_raw and not allow_empty_overrides:
        raise ValueError(
            "work item has no proposed_patch overrides — fill field/after "
            "(or pass allow_empty_overrides for T3 Pass / reviewed-no-write)"
        )
    overrides = _strip_draft_markers(overrides_raw) if overrides_raw else []
    actor_s = (actor or "cli").strip() or "cli"
    reason_s = (reason or str(doc.get("sot_flag") or "")).strip()
    as_of = str(doc.get("as_of") or "")

    if dry_run:
        pack_before_sha = ""
        pack_after_sha = ""
        pack_diff: List[Dict[str, Any]] = []
        line_delta: List[Dict[str, Any]] = []
        apply_result: Optional[Dict[str, Any]] = None
        if overrides:
            (
                pack_before_sha,
                pack_after_sha,
                pack_diff,
                line_delta,
                apply_result,
            ) = _preview_pack_apply(
                pack_path=pack_path, overrides=overrides, as_of=as_of
            )
        return {
            "work_item_id": work_item_id,
            "flag_id": work_item_id,
            "tier": tier,
            "disposition": "dry_run",
            "actor": actor_s,
            "reason": reason_s,
            "pending": None,
            "receipt": None,
            "wrote_pack": False,
            "pack_diff": pack_diff,
            "line_delta": line_delta,
            "pack_before_sha256": pack_before_sha,
            "pack_after_sha256": pack_after_sha,
            "apply": apply_result,
            "committed_fields": [
                {
                    "team": o.get("team"),
                    "player_name": o.get("player_name"),
                    "field": o.get("field"),
                    "before": o.get("before"),
                    "after": o.get("after"),
                    "destination": o.get("destination"),
                }
                for o in overrides
            ],
            "rematerialize_status": "would_remat",
            "remat_run_id": None,
            "remat_error": None,
            "rematerialize_hint": SAFE_REMAT_HINT,
            "contract": {
                "notes_may_touch_means": NOTES_MAY_TOUCH_MEANS,
                "proposals_may_auto_apply": PROPOSALS_MAY_AUTO_APPLY,
                "public_accept_ui": False,
                "internal_auth_only": True,
            },
        }

    pending_dir.mkdir(parents=True, exist_ok=True)
    pending_name = work_item_filename(work_item_id).replace("work-item-", "camp-accepted-", 1)
    pending_path = pending_dir / pending_name
    pending_doc = {
        "as_of": as_of,
        "approved_by": actor_s,
        "fixture": False,
        "work_item_id": work_item_id,
        "flag_id": work_item_id,
        "note_id": doc.get("note_id"),
        "tier": tier,
        "source": "camp_desk",
        "notes": doc.get("sot_flag") or doc.get("notes") or "",
        "reason": reason_s,
        "overrides": overrides,
        "contract": {
            "notes_may_touch_means": NOTES_MAY_TOUCH_MEANS,
            "proposals_may_auto_apply": PROPOSALS_MAY_AUTO_APPLY,
            "public_accept_ui": False,
        },
    }
    pending_path.write_text(json.dumps(pending_doc, indent=2) + "\n", encoding="utf-8")

    apply_result = None
    pack_diff = []
    line_delta = []
    pack_before_sha = ""
    pack_after_sha = ""
    remat_run_id = ""
    remat_error = ""
    wrote_pack = False
    disposition = "accepted"
    remat_status = "skipped"
    backup: Optional[bytes] = None

    if write_pack and overrides:
        backup = pack_path.read_bytes()
        pack_before_sha = _sha256_bytes(backup)
        pack_before = json.loads(backup.decode("utf-8"))
        teams = sorted({str(o.get("team") or "") for o in overrides if o.get("team")})
        before_smoke = kei_smoke_for_teams(pack_before, teams) if teams else []
        result = apply_intel_overrides(pack_before, overrides, as_of=as_of or None)
        new_raw = (json.dumps(result.payload, indent=2) + "\n").encode("utf-8")
        pack_path.write_bytes(new_raw)
        wrote_pack = True
        pack_after_sha = _sha256_bytes(new_raw)
        apply_result = result.as_dict()
        pack_diff = pack_diff_from_apply(apply_result)
        after_smoke = (
            kei_smoke_for_teams(result.payload, result.touched_teams)
            if result.touched_teams
            else []
        )
        line_delta = line_delta_from_kei(before_smoke, after_smoke)
        apply_result = {
            **apply_result,
            "kei_smoke_lines": format_smoke_diff(before_smoke, after_smoke),
        }

        if rematerialize:
            # Default stays receipt_only for unit tests / offline desks.
            # API + CLI pass live_remat_fn() so remat_run_id is a real Celery task id.
            fn = remat_fn or receipt_only_remat
            remat = fn()
            remat_run_id = remat.run_id
            if not remat.ok:
                # Remat fail ≠ accepted — roll pack back; keep queue item open.
                pack_path.write_bytes(backup)
                wrote_pack = False
                pack_after_sha = pack_before_sha
                disposition = "remat_failed"
                remat_status = "failed"
                remat_error = remat.error or "remat failed"
            else:
                remat_status = "ok" if remat.mode != "receipt_only" else "required"
        else:
            remat_status = "required_after_accept"
    elif rematerialize:
        remat_status = "skipped"

    receipt_path = write_receipt(
        work_item_id=work_item_id or proposal_path.stem,
        tier=tier,
        pending_path=pending_path if disposition == "accepted" else None,
        wrote_pack=wrote_pack,
        apply_result=apply_result if disposition == "accepted" else None,
        rematerialize_status=remat_status,
        disposition=disposition,
        pack_diff=pack_diff if disposition == "accepted" else [],
        line_delta=line_delta if disposition == "accepted" else [],
        actor=actor_s,
        reason=reason_s,
        pack_before_sha256=pack_before_sha,
        pack_after_sha256=pack_after_sha if disposition == "accepted" else pack_before_sha,
        remat_run_id=remat_run_id,
        remat_error=remat_error,
        receipts_dir=receipts_dir,
    )

    _append_disposition_log(
        accepted_log,
        {
            "work_item_id": work_item_id,
            "flag_id": work_item_id,
            "note_id": doc.get("note_id"),
            "tier": tier,
            "disposition": disposition,
            "actor": actor_s,
            "reason": reason_s,
            "accepted_at": _now_iso(),
            "proposal": str(proposal_path),
            "pending": str(pending_path) if disposition == "accepted" else None,
            "receipt": str(receipt_path),
            "wrote_pack": wrote_pack,
            "rematerialize_status": remat_status,
            "remat_run_id": remat_run_id or None,
            "remat_error": remat_error or None,
            "pack_before_sha256": pack_before_sha or None,
            "pack_after_sha256": pack_after_sha if disposition == "accepted" else None,
            "override_count": len(overrides),
            "pack_diff_count": len(pack_diff) if disposition == "accepted" else 0,
            "line_delta_count": len(line_delta) if disposition == "accepted" else 0,
        },
    )

    if disposition == "accepted":
        _unlink_queue_file(proposal_path)

    committed_fields = [
        {
            "team": o.get("team"),
            "player_name": o.get("player_name"),
            "field": o.get("field"),
            "before": o.get("before"),
            "after": o.get("after"),
            "destination": o.get("destination"),
        }
        for o in overrides
    ]
    return {
        "work_item_id": work_item_id,
        "flag_id": work_item_id,
        "tier": tier,
        "disposition": disposition,
        "actor": actor_s,
        "reason": reason_s,
        "pending": str(pending_path) if disposition == "accepted" else None,
        "receipt": str(receipt_path),
        "wrote_pack": wrote_pack,
        "pack_diff": pack_diff if disposition == "accepted" else [],
        "line_delta": line_delta if disposition == "accepted" else [],
        "pack_before_sha256": pack_before_sha,
        "pack_after_sha256": pack_after_sha if disposition == "accepted" else pack_before_sha,
        "apply": apply_result if disposition == "accepted" else None,
        "committed_fields": committed_fields if disposition == "accepted" else [],
        "rematerialize_status": remat_status,
        "remat_run_id": remat_run_id or None,
        "remat_error": remat_error or None,
        "rematerialize_hint": SAFE_REMAT_HINT if remat_status.startswith("required") else None,
        "contract": {
            "notes_may_touch_means": NOTES_MAY_TOUCH_MEANS,
            "proposals_may_auto_apply": PROPOSALS_MAY_AUTO_APPLY,
            "public_accept_ui": False,
            "internal_auth_only": True,
        },
    }


def close_work_item(
    proposal_path: Path,
    *,
    disposition: str,
    accepted_log: Path = ACCEPTED_LOG_DEFAULT,
    receipts_dir: Path = RECEIPTS_DEFAULT,
    reason: str = "",
    actor: str = "",
) -> Dict[str, Any]:
    """reject / no_change — writes nothing to the depth pack and does not remat."""
    assert_notes_cannot_touch_lines()
    if disposition not in {"reject", "no_change"}:
        raise ValueError("disposition must be reject or no_change")
    doc = json.loads(proposal_path.read_text(encoding="utf-8"))
    work_item_id = str(doc.get("work_item_id") or doc.get("flag_id") or "")
    closed = _disposition_map(accepted_log)
    if work_item_id in closed:
        raise ValueError(f"work item {work_item_id} already closed as {closed[work_item_id]}")
    tier = str(doc.get("tier") or "T2")
    actor_s = (actor or "cli").strip() or "cli"
    reason_s = reason or disposition
    receipt_path = write_receipt(
        work_item_id=work_item_id or proposal_path.stem,
        tier=tier,
        pending_path=None,
        wrote_pack=False,
        apply_result=None,
        rematerialize_status="skipped",
        disposition=disposition,
        pack_diff=[],
        line_delta=[],
        actor=actor_s,
        reason=reason_s,
        receipts_dir=receipts_dir,
    )
    _append_disposition_log(
        accepted_log,
        {
            "work_item_id": work_item_id,
            "flag_id": work_item_id,
            "note_id": doc.get("note_id"),
            "tier": tier,
            "disposition": disposition,
            "actor": actor_s,
            "reason": reason_s,
            "accepted_at": _now_iso(),
            "proposal": str(proposal_path),
            "receipt": str(receipt_path),
            "wrote_pack": False,
            "rematerialize_status": "skipped",
        },
    )
    _unlink_queue_file(proposal_path)
    return {
        "work_item_id": work_item_id,
        "disposition": disposition,
        "actor": actor_s,
        "reason": reason_s,
        "wrote_pack": False,
        "rematerialize_status": "skipped",
        "receipt": str(receipt_path),
        "pack_diff": [],
        "line_delta": [],
    }


def t1_past_kei_publish(
    flags: Iterable[DepthSotWorkItem],
    *,
    now: Optional[datetime] = None,
) -> List[DepthSotWorkItem]:
    """T1 items still open after a KEI publish window — ops alert set."""
    clock = now or _now_utc()
    out: List[DepthSotWorkItem] = []
    for flag in flags:
        if flag.tier != "T1":
            continue
        if flag.status in CLOSED_DISPOSITIONS:
            continue
        if not flag.next_kei_publish:
            if flag.overdue:
                out.append(flag)
            continue
        try:
            deadline = datetime.fromisoformat(
                flag.next_kei_publish.replace("Z", "+00:00")
            )
        except ValueError:
            continue
        if clock >= deadline:
            out.append(flag)
    return out


def overdue_summary(flags: Iterable[DepthSotWorkItem]) -> Dict[str, Any]:
    rows = list(flags)
    overdue = [f for f in rows if f.overdue]
    open_flags = [f for f in rows if f.status in {"open", "overdue"}]
    queued = [f for f in rows if f.status == "queued"]
    by_tier = {t: sum(1 for f in rows if f.tier == t) for t in ("T1", "T2", "T3")}
    t1_alert = t1_past_kei_publish(rows)
    return {
        "total_material": len(rows),
        "open": len(open_flags),
        "queued": len(queued),
        "overdue": len(overdue),
        "overdue_flag_ids": [f.work_item_id for f in overdue],
        "overdue_reasons": {f.work_item_id: f.overdue_reason for f in overdue},
        "by_tier": by_tier,
        "t1_past_kei_publish": [f.work_item_id for f in t1_alert],
        "t1_past_kei_publish_count": len(t1_alert),
        "draft_override_count": sum(len(f.proposed_patch) for f in rows),
        "contract": {
            "notes_may_touch_means": NOTES_MAY_TOUCH_MEANS,
            "proposals_may_auto_apply": PROPOSALS_MAY_AUTO_APPLY,
            "public_accept_ui": False,
            "internal_auth_only": True,
        },
    }
