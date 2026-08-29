"""Free NFL transaction feed → DepthSot T1/T2 scanner (propose only).

Contract
--------
- Sleeper / optional PFR are **signals**, never writers of means/props/spreads.
- Diff vs live pack ``injury_status`` + ``depth_order`` → ``proposed_patch`` only.
- Never invent WR1/QB1 / depth_order from Sleeper ``depth_chart_order``.
- Never close ATL-style open races (no ``competition_status`` from this feed).
- No auto-accept. Human Accept is the only pack/remat gate.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
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
    work_item_filename,
)
from src.services.nfl_daily_intel import ALLOWED_FIELDS, PACK_DEFAULT, normalize_override


def normalize_name_key(value: str) -> str:
    """Local copy of identity normalize — avoid sqlalchemy import for CLI/tests."""
    raw = str(value or "").strip().lower()
    raw = re.sub(r"[^a-z0-9]+", " ", raw)
    compact = " ".join(raw.split())
    compact = compact.replace(" jr", "").replace(" sr", "")
    compact = compact.replace(" iii", "").replace(" ii", "").replace(" iv", "")
    return compact


def _default_cache_dir() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "data" / "ops").is_dir() or (parent / ".git").exists():
            return parent / "data" / "ops" / "nfl-daily-intel" / "cache"
    return Path("/tmp/nfl-daily-intel-cache")


CACHE_DIR_DEFAULT = _default_cache_dir()
SLEEPER_PLAYERS_URL = "https://api.sleeper.app/v1/players/nfl"
SLEEPER_CACHE_TTL_SECONDS = 90 * 60  # 1.5h within 1–2h band

SKILL_POS = frozenset({"QB", "RB", "WR", "TE"})
OL_POS = frozenset({"OL", "OT", "OG", "C", "T", "G", "LT", "LG", "RG", "RT"})
POS_FAMILY = {
    "QB": "QB",
    "RB": "RB",
    "FB": "RB",
    "HB": "RB",
    "WR": "WR",
    "TE": "TE",
    "OL": "OL",
    "OT": "OL",
    "OG": "OL",
    "C": "OL",
    "T": "OL",
    "G": "OL",
    "LT": "OL",
    "LG": "OL",
    "RG": "OL",
    "RT": "OL",
}

# Pack rows treated as already durable-out (no new T1).
PACK_DURABLE_OUT = frozenset({"out", "ir", "pup", "nfi", "waived_injured"})
PACK_HEALTHY = frozenset({"", "active", "limited", "questionable", "doubtful"})

DURABLE_EVENTS = frozenset({"ir", "out_for_season", "waived_injured", "out"})
SOFT_EVENTS = frozenset({"pup", "nfi", "questionable"})

# Feed must never propose these from Sleeper depth / race chrome.
FORBIDDEN_FEED_FIELDS = frozenset(
    {"depth_order", "depth_slot", "player_name", "player_id", "competition_status"}
)


def _repo_cache_dir(repo_root: Optional[Path] = None) -> Path:
    if repo_root is not None:
        return repo_root / "data" / "ops" / "nfl-daily-intel" / "cache"
    return _default_cache_dir()


def _http_get(url: str, *, timeout: int = 60) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "KosEdgeTxnScanner/1.0 (+https://www.kosedge.com; research)",
            "Accept": "application/json,text/html,*/*",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def load_sleeper_players(
    *,
    cache_dir: Optional[Path] = None,
    ttl_seconds: int = SLEEPER_CACHE_TTL_SECONDS,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """GET Sleeper players/nfl with gitignored disk cache (TTL 1–2h)."""
    cdir = cache_dir or _repo_cache_dir()
    cdir.mkdir(parents=True, exist_ok=True)
    cache_path = cdir / "sleeper_players_nfl.json"
    meta_path = cdir / "sleeper_players_nfl.meta.json"
    now = time.time()
    if not force_refresh and cache_path.is_file() and meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            fetched_at = float(meta.get("fetched_at") or 0)
            if now - fetched_at <= ttl_seconds:
                payload = json.loads(cache_path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    return payload
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass
    raw = _http_get(SLEEPER_PLAYERS_URL)
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Sleeper players payload must be an object")
    cache_path.write_text(json.dumps(payload), encoding="utf-8")
    meta_path.write_text(
        json.dumps(
            {
                "fetched_at": now,
                "fetched_at_iso": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "url": SLEEPER_PLAYERS_URL,
                "ttl_seconds": ttl_seconds,
                "player_count": len(payload),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return payload


def pfr_month_url(*, year: Optional[int] = None, month: Optional[int] = None) -> str:
    now = datetime.now(timezone.utc)
    y = int(year or now.year)
    m = int(month or now.month)
    return f"https://www.pro-football-reference.com/years/{y}/transactions.htm?month={m}"


def load_pfr_events(
    *,
    as_of_date: str,
    cache_dir: Optional[Path] = None,
    force_refresh: bool = False,
    year: Optional[int] = None,
    month: Optional[int] = None,
) -> List["TxnFeedEvent"]:
    """Optional PFR scrape — soft-fail to [] on network/parse errors."""
    cdir = cache_dir or _repo_cache_dir()
    cdir.mkdir(parents=True, exist_ok=True)
    url = pfr_month_url(year=year, month=month)
    cache_path = cdir / "pfr_transactions_month.html"
    meta_path = cdir / "pfr_transactions_month.meta.json"
    html = ""
    try:
        use_cache = False
        if not force_refresh and cache_path.is_file() and meta_path.is_file():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if time.time() - float(meta.get("fetched_at") or 0) <= SLEEPER_CACHE_TTL_SECONDS:
                html = cache_path.read_text(encoding="utf-8", errors="replace")
                use_cache = True
        if not use_cache:
            raw = _http_get(url, timeout=45)
            html = raw.decode("utf-8", errors="replace")
            cache_path.write_text(html, encoding="utf-8")
            meta_path.write_text(
                json.dumps(
                    {"fetched_at": time.time(), "url": url, "bytes": len(raw)},
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError):
        return []
    return parse_pfr_transactions_html(html, as_of_date=as_of_date, href=url)


def ingest_txn_events(
    *,
    as_of_date: Optional[str] = None,
    with_pfr: bool = False,
    force_refresh: bool = False,
    cache_dir: Optional[Path] = None,
    sleeper_payload: Optional[Mapping[str, Any]] = None,
) -> List["TxnFeedEvent"]:
    """Fetch (or accept fixture) feeds → normalized TxnFeedEvent list."""
    day = as_of_date or as_of_today_et()
    cdir = cache_dir or _repo_cache_dir()
    if sleeper_payload is None:
        sleeper_payload = load_sleeper_players(cache_dir=cdir, force_refresh=force_refresh)
    events = sleeper_players_to_events(sleeper_payload, as_of_date=day)
    if with_pfr:
        events.extend(
            load_pfr_events(as_of_date=day, cache_dir=cdir, force_refresh=force_refresh)
        )
    return events


def as_of_today_et() -> str:
    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo("America/New_York")).date().isoformat()


def classify_sleeper_event(player: Mapping[str, Any]) -> Optional[str]:
    """Map Sleeper status/injury_status → durable or soft event key."""
    status = str(player.get("status") or "").strip().lower()
    injury = str(player.get("injury_status") or "").strip().lower()
    notes = str(player.get("injury_notes") or "").strip().lower()

    if "waived" in notes and "injur" in notes:
        return "waived_injured"
    if injury in {"ir"} or status == "injured reserve" or "injured reserve" in status:
        return "ir"
    if injury in {"out"} or "out for the season" in notes or "season-ending" in notes:
        return "out"
    if injury in {"pup"} or "physically unable" in status:
        return "pup"
    if injury in {"nfi"} or "non football injury" in status or "non-football" in status:
        return "nfi"
    if injury in {"questionable", "doubtful"}:
        return "questionable"
    return None


def classify_pfr_event(text: str) -> Optional[str]:
    t = (text or "").lower()
    if "waived" in t and "injur" in t:
        return "waived_injured"
    if "activated from ir" in t or "activated from injured reserve" in t:
        return None  # activation is not a T1 out signal
    if "placed on ir" in t or "placed on injured reserve" in t:
        return "ir"
    if "out for the season" in t or "season-ending" in t:
        return "out_for_season"
    return None


def event_is_durable(event: str) -> bool:
    return event in DURABLE_EVENTS


def event_is_soft(event: str) -> bool:
    return event in SOFT_EVENTS


def pack_injury_is_healthy(status: Any) -> bool:
    token = str(status or "").strip().lower()
    if token in PACK_DURABLE_OUT:
        return False
    return token in PACK_HEALTHY or token == ""


def pack_row_skill_relevant(row: Mapping[str, Any]) -> bool:
    """Depth 1–3 **or** skill position on the pack (not Sleeper depth)."""
    pos = str(row.get("position") or "").upper()
    try:
        depth = int(row.get("depth_order") or 99)
    except (TypeError, ValueError):
        depth = 99
    if depth in {1, 2, 3}:
        return True
    if pos in SKILL_POS and depth <= 3:
        return True
    # Skill chart depth 1–3 already covered; depth≤3 skill-only is enough.
    # Also treat OL starters (depth 1) as relevant — already covered by depth check.
    return False


def txn_work_item_id(*, player_id: str, event: str, as_of_date: str) -> str:
    """Idempotent key: (player_id, event, as_of_date)."""
    pid = str(player_id or "").strip() or "unknown"
    ev = str(event or "").strip().lower() or "unknown"
    return f"{as_of_date}:{pid}:{ev}"


def _gsis_key(raw: Any) -> str:
    return str(raw or "").strip()


def _pos_family(pos: Any) -> str:
    return POS_FAMILY.get(str(pos or "").strip().upper(), str(pos or "").strip().upper())


def index_pack_players(pack: Mapping[str, Any]) -> Dict[str, Any]:
    """Build lookup structures over rows + ol_roles."""
    by_gsis: Dict[str, Dict[str, Any]] = {}
    by_team_name: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    all_rows: List[Dict[str, Any]] = []
    for layer in ("rows", "ol_roles"):
        for row in pack.get(layer) or []:
            if not isinstance(row, dict):
                continue
            enriched = {**row, "_layer": layer}
            all_rows.append(enriched)
            gsis = _gsis_key(row.get("player_id"))
            # Synthetic OL ids (WAS-LT-1) are not GSIS — still index for exact id match.
            if gsis:
                by_gsis[gsis] = enriched
            team = _norm_team(row.get("team"))
            nkey = normalize_name_key(str(row.get("player_name") or ""))
            if team and nkey:
                by_team_name.setdefault((team, nkey), []).append(enriched)
    return {"by_gsis": by_gsis, "by_team_name": by_team_name, "rows": all_rows}


def map_feed_player_to_pack(
    feed: Mapping[str, Any],
    pack_index: Mapping[str, Any],
) -> Optional[Dict[str, Any]]:
    """Map Sleeper/PFR player → KosEdge pack row (gsis or team+name+pos)."""
    gsis = _gsis_key(feed.get("gsis_id") or feed.get("player_id_kos") or "")
    by_gsis: Dict[str, Dict[str, Any]] = pack_index["by_gsis"]
    if gsis and gsis in by_gsis and gsis.startswith("00-"):
        return by_gsis[gsis]

    team = _norm_team(feed.get("team"))
    name = str(feed.get("full_name") or feed.get("player_name") or "").strip()
    nkey = normalize_name_key(name)
    if not team or not nkey:
        return None
    candidates = list(pack_index["by_team_name"].get((team, nkey)) or [])
    if not candidates:
        # Soft suffix tolerance already in normalize_name_key (drops III/Jr).
        return None
    feed_fam = _pos_family(feed.get("position"))
    if feed_fam:
        fam_hits = [c for c in candidates if _pos_family(c.get("position")) == feed_fam]
        if len(fam_hits) == 1:
            return fam_hits[0]
        if fam_hits:
            candidates = fam_hits
    if len(candidates) == 1:
        return candidates[0]
    # Prefer skill-chart / lower depth when ambiguous.
    candidates.sort(key=lambda r: int(r.get("depth_order") or 99))
    return candidates[0]


def proposed_injury_after(event: str) -> str:
    if event in {"ir", "out_for_season", "waived_injured", "out"}:
        return "out"
    if event == "pup":
        return "pup"
    if event == "nfi":
        return "nfi"
    if event == "questionable":
        return "questionable"
    return "out"


@dataclass
class TxnFeedEvent:
    source: str  # sleeper | pfr
    event: str
    as_of_date: str
    team: str
    player_name: str
    position: str
    gsis_id: str = ""
    sleeper_id: str = ""
    injury_status_raw: str = ""
    status_raw: str = ""
    depth_chart_order: Optional[int] = None  # never written to pack
    href: str = ""
    note: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "event": self.event,
            "as_of_date": self.as_of_date,
            "team": self.team,
            "player_name": self.player_name,
            "position": self.position,
            "gsis_id": self.gsis_id,
            "sleeper_id": self.sleeper_id,
            "injury_status_raw": self.injury_status_raw,
            "status_raw": self.status_raw,
            "depth_chart_order": self.depth_chart_order,
            "href": self.href,
            "note": self.note,
        }


def sleeper_players_to_events(
    players: Mapping[str, Any],
    *,
    as_of_date: str,
) -> List[TxnFeedEvent]:
    out: List[TxnFeedEvent] = []
    for sid, raw in players.items():
        if not isinstance(raw, dict):
            continue
        team = _norm_team(raw.get("team"))
        if not team:
            continue
        event = classify_sleeper_event(raw)
        if not event:
            continue
        pos = str(raw.get("position") or "").upper()
        if _pos_family(pos) not in {"QB", "RB", "WR", "TE", "OL"}:
            continue
        name = str(raw.get("full_name") or "").strip()
        if not name:
            continue
        depth = raw.get("depth_chart_order")
        try:
            depth_i = int(depth) if depth is not None else None
        except (TypeError, ValueError):
            depth_i = None
        out.append(
            TxnFeedEvent(
                source="sleeper",
                event=event,
                as_of_date=as_of_date,
                team=team,
                player_name=name,
                position=pos,
                gsis_id=_gsis_key(raw.get("gsis_id")),
                sleeper_id=str(raw.get("player_id") or sid),
                injury_status_raw=str(raw.get("injury_status") or ""),
                status_raw=str(raw.get("status") or ""),
                depth_chart_order=depth_i,
                href=SLEEPER_PLAYERS_URL,
                note=str(raw.get("injury_notes") or ""),
            )
        )
    return out


_PFR_ROW_RE = re.compile(
    r"(?i)(placed on(?: injured reserve| ir)|activated from(?: injured reserve| ir)|"
    r"waived/?\s*injured|out for the season)"
)


def parse_pfr_transactions_html(html: str, *, as_of_date: str, href: str = "") -> List[TxnFeedEvent]:
    """Best-effort scrape of PFR transaction blurbs. Soft-fail friendly."""
    events: List[TxnFeedEvent] = []
    # Very light HTML → text; avoid bringing BeautifulSoup as a hard dep.
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    # Split on date-like boundaries when present.
    chunks = re.split(r"(?=\b(?:January|February|March|April|May|June|July|August|"
                      r"September|October|November|December)\s+\d{1,2})", text)
    for chunk in chunks:
        if not _PFR_ROW_RE.search(chunk):
            continue
        event = classify_pfr_event(chunk)
        if not event:
            continue
        # Heuristic: "Player Name Team-Pos ..." — keep short note; mapper needs name+team.
        m = re.search(
            r"([A-Z][a-zA-Z.'\-]+(?:\s[A-Z][a-zA-Z.'\-]+){0,3})\s+"
            r"((?:ARI|ATL|BAL|BUF|CAR|CHI|CIN|CLE|DAL|DEN|DET|GB|HOU|IND|JAX|KC|"
            r"LA|LAC|LAR|LV|MIA|MIN|NE|NO|NYG|NYJ|PHI|PIT|SEA|SF|TB|TEN|WAS|WSH))"
            r"(?:[\s\-_/]+([A-Za-z]{1,3}))?",
            chunk,
        )
        if not m:
            continue
        team = _norm_team(m.group(2))
        if team == "WSH":
            team = "WAS"
        events.append(
            TxnFeedEvent(
                source="pfr",
                event=event,
                as_of_date=as_of_date,
                team=team,
                player_name=m.group(1).strip(),
                position=str(m.group(3) or "").upper(),
                href=href or "https://www.pro-football-reference.com/",
                note=chunk.strip()[:240],
            )
        )
    return events


def _propose_txn_patch(
    *,
    pack_row: Mapping[str, Any],
    event: TxnFeedEvent,
) -> List[Dict[str, Any]]:
    """Injury-only proposed_patch. Never depth / competition / means."""
    after = proposed_injury_after(event.event)
    current = pack_row.get("injury_status")
    if str(current or "").strip().lower() == after:
        return []
    raw = {
        "team": _norm_team(pack_row.get("team") or event.team),
        "player_name": pack_row.get("player_name") or event.player_name,
        "player_id": str(pack_row.get("player_id") or ""),
        "position": str(pack_row.get("position") or event.position or "").upper(),
        "layer": pack_row.get("_layer") or "rows",
        "field": "injury_status",
        "before": current,
        "after": after,
        "reason": (
            f"Txn feed ({event.source}/{event.event}): "
            f"{event.player_name} {event.status_raw or ''} "
            f"{event.injury_status_raw or ''} {event.note or ''}"
        ).strip(),
        "as_of": event.as_of_date,
        "confidence": "medium" if event.source == "sleeper" else "low",
        "destination": "kei_only",
        "sources": [event.href] if event.href else [f"{event.source}:{event.as_of_date}"],
        "draft": True,
    }
    try:
        ov = normalize_override(raw)
    except ValueError:
        return []
    if ov["field"] not in ALLOWED_FIELDS or ov["field"] in FORBIDDEN_FEED_FIELDS:
        return []
    return [{**ov, "draft": True}]


def scan_txn_flags(
    *,
    events: Sequence[TxnFeedEvent],
    pack: Optional[Mapping[str, Any]] = None,
    pack_path: Path = PACK_DEFAULT,
    proposed_dir: Path = PROPOSED_DEFAULT,
    accepted_log: Path = ACCEPTED_LOG_DEFAULT,
    now: Optional[datetime] = None,
    overdue_hours: Optional[int] = None,
) -> List[DepthSotWorkItem]:
    """Diff txn feed vs live pack → DepthSotWorkItem list (propose only)."""
    assert_notes_cannot_touch_lines()
    payload = dict(pack) if pack is not None else load_pack(pack_path)
    index = index_pack_players(payload)
    closed = _disposition_map(accepted_log)
    queued = _queued_flag_ids(proposed_dir)
    clock = now or _now_utc()
    items: List[DepthSotWorkItem] = []
    seen_keys: set[str] = set()

    for event in events:
        pack_row = map_feed_player_to_pack(
            {
                "gsis_id": event.gsis_id,
                "team": event.team,
                "full_name": event.player_name,
                "position": event.position,
            },
            index,
        )
        if pack_row is None:
            continue
        pid = str(pack_row.get("player_id") or "").strip()
        if not pid:
            continue
        wid = txn_work_item_id(
            player_id=pid, event=event.event, as_of_date=event.as_of_date
        )
        if wid in seen_keys:
            continue
        seen_keys.add(wid)

        pack_healthy = pack_injury_is_healthy(pack_row.get("injury_status"))
        durable = event_is_durable(event.event)
        soft = event_is_soft(event.event)
        relevant = pack_row_skill_relevant(pack_row)

        # T1: pack healthy AND durable out AND depth/skill relevant
        # T2: soft (PUP/NFI/Q) with no durable out already on pack
        if durable and pack_healthy and relevant:
            tier = "T1"
        elif soft and pack_healthy and relevant:
            tier = "T2"
        else:
            # Already reflected in SoT, or not depth-relevant — skip open item.
            continue

        patch = _propose_txn_patch(pack_row=pack_row, event=event)
        if not patch and tier == "T1":
            # No-op vs pack (already matching after) — skip.
            continue

        try:
            start = desk_date_start_utc(event.as_of_date)
        except ValueError:
            start = clock
        age_h = max(0.0, (clock - start).total_seconds() / 3600.0)
        sla = overdue_hours if overdue_hours is not None else TIER_SLA_HOURS[tier]
        overdue, overdue_reason = _is_overdue(
            tier=tier, age_h=age_h, sla_hours=sla, desk_start=start, now=clock
        )
        kei_deadline = next_kei_publish_utc(start)
        team = _norm_team(pack_row.get("team") or event.team)
        note_id = f"txn-{event.source}-{pid}-{event.event}"
        if wid in closed:
            status = closed[wid]
            overdue = False
            overdue_reason = ""
        elif wid in queued:
            status = "queued"
        else:
            status = "overdue" if overdue else "open"

        sot_flag = (
            f"{pack_row.get('player_name')} ({team} {pack_row.get('position')}"
            f"{pack_row.get('depth_order')}): feed={event.source}/{event.event} "
            f"pack_injury={pack_row.get('injury_status')!r}. "
            f"Propose injury_status only — do not invent depth from Sleeper."
        )
        items.append(
            DepthSotWorkItem(
                work_item_id=wid,
                desk_date=event.as_of_date,
                team=team,
                note_id=note_id,
                title=f"Txn {event.event}: {pack_row.get('player_name')}",
                sot_flag=sot_flag,
                bottom_line=sot_flag,
                tier=tier,
                sla_hours=sla,
                next_kei_publish=kei_deadline.strftime("%Y-%m-%dT%H:%M:%SZ"),
                sources=[
                    {
                        "label": f"{event.source}:{event.event}",
                        "href": event.href,
                        "source": event.source,
                    }
                ],
                proposed_patch=patch,
                status=status,
                overdue=overdue,
                overdue_reason=overdue_reason,
                age_hours=age_h,
            )
        )

    items.sort(
        key=lambda f: (
            0 if f.tier == "T1" else 1,
            -int(f.overdue),
            f.team,
            f.work_item_id,
        )
    )
    return items


def proposal_doc_for_txn_flag(flag: DepthSotWorkItem) -> Dict[str, Any]:
    """Queue doc for txn-sourced work items (never auto-applied)."""
    source = "sleeper"
    for s in flag.sources:
        if isinstance(s, dict) and s.get("source"):
            source = str(s["source"])
            break
    return {
        "schema": WORK_ITEM_SCHEMA,
        "work_item_id": flag.work_item_id,
        "note_id": flag.note_id,
        "flag_id": flag.work_item_id,
        "as_of": flag.desk_date,
        "team_id": flag.team,
        "source": source,
        "feed": "nfl_transactions",
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
            "Txn feed proposed_patch only — never auto-applied. "
            "Feed must not write means/props/spreads or invent depth. "
            "Accept → pack write → rematerialize → receipt. "
            "CLI: scripts/nfl/queue_camp_sot_flags.py --scan-txns / --accept"
        ),
        "proposed_patch": {"overrides": flag.proposed_patch},
        "overrides": flag.proposed_patch,
        "contract": {
            "notes_may_touch_means": NOTES_MAY_TOUCH_MEANS,
            "notes_may_touch_props": NOTES_MAY_TOUCH_PROPS,
            "notes_may_touch_spreads": NOTES_MAY_TOUCH_SPREADS,
            "proposals_may_auto_apply": PROPOSALS_MAY_AUTO_APPLY,
            "feed_may_write_depth_order": False,
            "feed_may_close_open_races": False,
        },
    }


def queue_txn_flags(
    flags: Sequence[DepthSotWorkItem],
    *,
    proposed_dir: Path = QUEUE_RUNTIME_DEFAULT,
    accepted_log: Path = ACCEPTED_LOG_DEFAULT,
    only_overdue: bool = False,
    only_with_drafts: bool = False,
    tiers: Optional[Sequence[str]] = None,
) -> QueueRunResult:
    """Upsert txn work items; reuse camp queue idempotency (no pack writes)."""
    assert_notes_cannot_touch_lines()
    proposed_dir.mkdir(parents=True, exist_ok=True)
    closed = _disposition_map(accepted_log)
    wanted = {t.upper() for t in tiers} if tiers else None
    result = QueueRunResult()
    for flag in flags:
        if flag.work_item_id in closed:
            result.skipped.append(f"{flag.work_item_id}:{closed[flag.work_item_id]}")
            continue
        if only_overdue and not flag.overdue:
            continue
        if only_with_drafts and not flag.proposed_patch:
            continue
        if wanted and flag.tier not in wanted:
            continue
        path = proposed_dir / work_item_filename(flag.work_item_id)
        # as_of:pid:event → work-item-as_of-pid.json (no camp TEAM collision).
        doc = proposal_doc_for_txn_flag(flag)
        if path.is_file():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                existing = None
            if existing is not None and _canonical_work_item_doc(existing) == _canonical_work_item_doc(
                doc
            ):
                result.unchanged.append(path)
                continue
            path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
            result.updated.append(path)
        else:
            path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
            result.created.append(path)
    return result


def format_scan_table(flags: Sequence[DepthSotWorkItem]) -> str:
    lines = [
        f"{'tier':<4} {'team':<4} {'player / flag':<56} {'patch':>5} {'source':<8}",
        "-" * 86,
    ]
    for f in flags:
        src = "sleeper"
        for s in f.sources:
            if isinstance(s, dict) and s.get("source"):
                src = str(s["source"])
                break
        title = (f.title or f.sot_flag or "")[:56]
        lines.append(
            f"{f.tier:<4} {f.team:<4} {title:<56} {len(f.proposed_patch):>5} {src:<8}"
        )
    if not flags:
        lines.append("(none)")
    return "\n".join(lines)
