"""DraftKings / FanDuel salary + slate ingest.

Raw source payloads are kept separately from normalized observations.
The parser stamps site from the source format — a caller cannot relabel
DK salaries as FD.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from src.services.nfl_dfs_identity import (
    DFS_SKILL_POSITIONS,
    canonical_dfs_position,
    canonical_dfs_site,
    canonical_team_code,
)

INGEST_VERSION = "nfl-dfs-salary-ingest-v1"
GAME_INFO_RE = re.compile(
    r"(?P<away>[A-Za-z]{2,4})\s*@\s*(?P<home>[A-Za-z]{2,4})"
)


@dataclass
class NormalizedSalaryRow:
    site: str
    source_player_id: str
    player_name: str
    team: str
    opponent: str
    position: str
    salary: int
    game_label: Optional[str]
    game_time: Optional[str]
    source: str
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedSlate:
    site: str
    season: int
    week: int
    slate_id: str
    slate_name: Optional[str]
    contest_style: str
    source: str
    source_version: str
    captured_at: str
    rows: List[NormalizedSalaryRow]
    raw_payload: Dict[str, Any]
    rejected: List[Dict[str, Any]] = field(default_factory=list)


class SalaryParseError(ValueError):
    pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def payload_sha256(payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _parse_salary(raw: Any) -> Optional[int]:
    if raw is None or raw == "":
        return None
    text = str(raw).strip().replace("$", "").replace(",", "")
    try:
        value = int(round(float(text)))
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _split_game(label: str) -> tuple[Optional[str], Optional[str]]:
    match = GAME_INFO_RE.search(str(label or ""))
    if not match:
        return None, None
    return canonical_team_code(match.group("away")), canonical_team_code(match.group("home"))


def infer_opponent(*, team: str, game_label: str) -> Optional[str]:
    away, home = _split_game(game_label)
    team_c = canonical_team_code(team)
    if not team_c or not away or not home:
        return None
    if team_c == away:
        return home
    if team_c == home:
        return away
    return None


def _detect_site_from_headers(headers: Sequence[str]) -> Optional[str]:
    cols = {str(h or "").strip().lower() for h in headers}
    if {"name + id", "teamabbrev", "game info"} & cols or (
        "name + id" in cols and "salary" in cols
    ):
        return "DK"
    if {"nickname", "first name", "last name"} <= cols or (
        "opponent" in cols and "first name" in cols and "salary" in cols
    ):
        return "FD"
    return None


def parse_dk_csv(text: str) -> List[NormalizedSalaryRow]:
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise SalaryParseError("DK CSV missing header")
    detected = _detect_site_from_headers(reader.fieldnames)
    if detected not in {None, "DK"}:
        raise SalaryParseError("FD CSV cannot be ingested as DraftKings")
    rows: List[NormalizedSalaryRow] = []
    for raw in reader:
        name = (raw.get("Name") or raw.get("Name + ID") or "").strip()
        if " (" in name:
            name = name.rsplit(" (", 1)[0].strip()
        source_id = str(raw.get("ID") or raw.get("Id") or "").strip()
        if not source_id and raw.get("Name + ID"):
            match = re.search(r"\((\d+)\)", str(raw.get("Name + ID")))
            source_id = match.group(1) if match else ""
        team = canonical_team_code(raw.get("TeamAbbrev") or raw.get("Team"))
        game_label = (raw.get("Game Info") or raw.get("GameInfo") or "").strip() or None
        opponent = infer_opponent(team=team or "", game_label=game_label or "")
        position = canonical_dfs_position(raw.get("Roster Position") or raw.get("Position"))
        salary = _parse_salary(raw.get("Salary"))
        if not name or not source_id or not team or not opponent or not position or salary is None:
            continue
        if position not in DFS_SKILL_POSITIONS:
            continue
        rows.append(
            NormalizedSalaryRow(
                site="DK",
                source_player_id=source_id,
                player_name=name,
                team=team,
                opponent=opponent,
                position=position,
                salary=salary,
                game_label=game_label,
                game_time=None,
                source="dk_csv",
                raw=dict(raw),
            )
        )
    return rows


def parse_fd_csv(text: str) -> List[NormalizedSalaryRow]:
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise SalaryParseError("FD CSV missing header")
    detected = _detect_site_from_headers(reader.fieldnames)
    if detected not in {None, "FD"}:
        raise SalaryParseError("DK CSV cannot be ingested as FanDuel")
    rows: List[NormalizedSalaryRow] = []
    for raw in reader:
        first = (raw.get("First Name") or "").strip()
        last = (raw.get("Last Name") or "").strip()
        nick = (raw.get("Nickname") or "").strip()
        name = nick or " ".join(part for part in (first, last) if part)
        source_id = str(raw.get("Id") or raw.get("ID") or "").strip()
        team = canonical_team_code(raw.get("Team"))
        opponent = canonical_team_code(raw.get("Opponent") or raw.get("Opp"))
        game_label = (raw.get("Game") or raw.get("Game Info") or "").strip() or None
        if not opponent and game_label and team:
            opponent = infer_opponent(team=team, game_label=game_label)
        position = canonical_dfs_position(raw.get("Position"))
        salary = _parse_salary(raw.get("Salary"))
        if not name or not source_id or not team or not opponent or not position or salary is None:
            continue
        if position not in DFS_SKILL_POSITIONS:
            continue
        rows.append(
            NormalizedSalaryRow(
                site="FD",
                source_player_id=source_id,
                player_name=name,
                team=team,
                opponent=opponent,
                position=position,
                salary=salary,
                game_label=game_label,
                game_time=None,
                source="fd_csv",
                raw=dict(raw),
            )
        )
    return rows


def parse_dk_draftables(payload: Dict[str, Any]) -> List[NormalizedSalaryRow]:
    draftables = payload.get("draftables") if isinstance(payload, dict) else None
    if not isinstance(draftables, list):
        raise SalaryParseError("DK draftables payload missing draftables[]")
    rows: List[NormalizedSalaryRow] = []
    seen: set[str] = set()
    for raw in draftables:
        if not isinstance(raw, dict):
            continue
        source_id = str(raw.get("playerId") or raw.get("id") or "").strip()
        if not source_id or source_id in seen:
            continue
        position = canonical_dfs_position(raw.get("position") or raw.get("rosterSlotId"))
        if position not in DFS_SKILL_POSITIONS:
            continue
        team = canonical_team_code(raw.get("teamAbbreviation") or raw.get("team"))
        competition = raw.get("competition") if isinstance(raw.get("competition"), dict) else {}
        game_label = str(competition.get("name") or raw.get("game") or "").strip() or None
        opponent = infer_opponent(team=team or "", game_label=game_label or "")
        salary = _parse_salary(raw.get("salary"))
        name = str(raw.get("displayName") or raw.get("name") or "").strip()
        if not name or not team or not opponent or salary is None:
            continue
        seen.add(source_id)
        rows.append(
            NormalizedSalaryRow(
                site="DK",
                source_player_id=source_id,
                player_name=name,
                team=team,
                opponent=opponent,
                position=position,
                salary=salary,
                game_label=game_label,
                game_time=str(competition.get("startTime") or "") or None,
                source="dk_draftables",
                raw=raw,
            )
        )
    return rows


def parse_site_payload(
    *,
    claimed_site: str,
    csv_text: Optional[str] = None,
    json_payload: Optional[Dict[str, Any]] = None,
) -> List[NormalizedSalaryRow]:
    site = canonical_dfs_site(claimed_site)
    if site is None:
        raise SalaryParseError("site must be DK or FD")
    if csv_text and csv_text.strip():
        header_line = csv_text.splitlines()[0] if csv_text.splitlines() else ""
        detected = _detect_site_from_headers([c.strip() for c in header_line.split(",")])
        if detected and detected != site:
            raise SalaryParseError(f"{detected} salary file cannot be ingested as {site}")
        return parse_dk_csv(csv_text) if site == "DK" else parse_fd_csv(csv_text)
    if json_payload:
        if site != "DK":
            raise SalaryParseError("JSON draftables ingest is DK-only; FD requires official CSV")
        return parse_dk_draftables(json_payload)
    raise SalaryParseError("missing salary payload")


def normalize_slate(
    *,
    site: str,
    season: int,
    week: int,
    slate_id: str,
    source: str,
    source_version: str,
    captured_at: Optional[str] = None,
    csv_text: Optional[str] = None,
    json_payload: Optional[Dict[str, Any]] = None,
    slate_name: Optional[str] = None,
) -> NormalizedSlate:
    site_c = canonical_dfs_site(site)
    if site_c is None:
        raise SalaryParseError("site must be DK or FD")
    if int(week) < 1 or int(week) > 18:
        raise SalaryParseError("week must be a regular-season week")
    if not str(slate_id).strip():
        raise SalaryParseError("slate_id is required")
    rows = parse_site_payload(claimed_site=site_c, csv_text=csv_text, json_payload=json_payload)
    # Source-stamped site wins. A DK row can never land on an FD slate.
    kept: List[NormalizedSalaryRow] = []
    rejected: List[Dict[str, Any]] = []
    for row in rows:
        if row.site != site_c:
            rejected.append({"reason": "site_mismatch", "source_player_id": row.source_player_id})
            continue
        kept.append(row)
    raw_payload: Dict[str, Any] = {
        "site": site_c,
        "season": int(season),
        "week": int(week),
        "slate_id": str(slate_id),
        "source": source,
        "source_version": source_version,
        "csv_text": csv_text,
        "json_payload": json_payload,
    }
    return NormalizedSlate(
        site=site_c,
        season=int(season),
        week=int(week),
        slate_id=str(slate_id),
        slate_name=slate_name,
        contest_style="classic",
        source=source,
        source_version=source_version,
        captured_at=captured_at or _now_iso(),
        rows=kept,
        raw_payload=raw_payload,
        rejected=rejected,
    )


def salary_name_keys(name: str) -> List[str]:
    raw = re.sub(r"[^a-z0-9]+", " ", str(name or "").strip().lower())
    compact = " ".join(raw.split()).replace(" jr", "").replace(" sr", "")
    return [compact] if compact else []


def slate_as_dict(slate: NormalizedSlate) -> Dict[str, Any]:
    payload = asdict(slate)
    return payload
