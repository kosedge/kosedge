"""Packaged NFL coaching staff (HC / OC / DC) — shared product + continuity source.

Depth charts remain in ``loaders.load_packaged_depth_chart``. This module is
the single named-staff book for team intel UI and continuity staff factors.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from src.services.nfl_season_engine.loaders import NFL_TEAMS, normalize_team_abbr

_PACKAGE_DATA_DIR = Path(__file__).resolve().parent / "data"
_PACKAGED_COACHING_FILES = {
    2026: _PACKAGE_DATA_DIR / "nfl_coaching_staff_2026.json",
}

COACHING_SOURCE_PACKAGED = "packaged_nfl_coaching_staff_2026"


def _tri_bool(raw: Any) -> Optional[bool]:
    """Parse continuity flag: True/False known, None = unknown (do not invent)."""
    if raw is None:
        return None
    if isinstance(raw, bool):
        return raw
    token = str(raw).strip().lower()
    if token in ("", "null", "none", "unknown", "thin"):
        return None
    if token in ("1", "true", "yes", "new"):
        return True
    if token in ("0", "false", "no", "returning", "return"):
        return False
    return None


def _role_payload(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, Mapping):
        return {"name": None, "new": None, "status": "unknown"}
    name_raw = raw.get("name")
    name = str(name_raw).strip() if name_raw is not None else ""
    name_out: Optional[str] = name if name else None
    new_flag = _tri_bool(raw.get("new"))
    if name_out is None:
        status = "unknown"
    elif new_flag is True:
        status = "new"
    elif new_flag is False:
        status = "returning"
    else:
        status = "named"
    return {"name": name_out, "new": new_flag, "status": status}


def load_packaged_coaching_staff(
    season: int,
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """Load packaged HC/OC/DC book for ``season``.

    Returns ``(by_team, meta)``. Missing artifact → empty map (callers label thin).
    """
    path = _PACKAGED_COACHING_FILES.get(int(season))
    if path is None or not path.is_file():
        return {}, {
            "coaching_source": "missing",
            "coaching_path": "",
            "coaching_team_count": 0,
            "coaching_named_hc_count": 0,
            "coaching_full_staff_count": 0,
            "coaching_holes": list(NFL_TEAMS),
        }

    payload = json.loads(path.read_text(encoding="utf-8"))
    teams_raw = payload.get("teams") or {}
    by_team: Dict[str, Dict[str, Any]] = {}
    if isinstance(teams_raw, Mapping):
        for team_raw, entry in teams_raw.items():
            team = normalize_team_abbr(str(team_raw))
            if team not in NFL_TEAMS or not isinstance(entry, Mapping):
                continue
            hc = _role_payload(entry.get("hc"))
            oc = _role_payload(entry.get("oc"))
            dc = _role_payload(entry.get("dc"))
            notes = entry.get("notes")
            by_team[team] = {
                "team": team,
                "hc": hc,
                "oc": oc,
                "dc": dc,
                "hc_name": hc.get("name"),
                "oc_name": oc.get("name"),
                "dc_name": dc.get("name"),
                "new_hc": hc.get("new"),
                "new_oc": oc.get("new"),
                "new_dc": dc.get("new"),
                "notes": str(notes).strip() if notes else "",
                "source": str(payload.get("source") or COACHING_SOURCE_PACKAGED),
            }

    named_hc = sum(1 for t in by_team.values() if t.get("hc_name"))
    full_staff = sum(
        1
        for t in by_team.values()
        if t.get("hc_name") and t.get("oc_name") and t.get("dc_name")
    )
    holes = [t for t in NFL_TEAMS if t not in by_team]
    thin_dc = sorted(
        t for t, row in by_team.items() if not row.get("dc_name")
    )
    meta = {
        "coaching_source": str(payload.get("source") or COACHING_SOURCE_PACKAGED),
        "coaching_path": str(path.name),
        "coaching_as_of": str(payload.get("as_of") or ""),
        "coaching_team_count": len(by_team),
        "coaching_named_hc_count": named_hc,
        "coaching_full_staff_count": full_staff,
        "coaching_holes": holes,
        "coaching_thin_dc": thin_dc,
        "coaching_upstream": str(payload.get("upstream") or "curated"),
    }
    return by_team, meta


def continuity_staff_from_packaged(
    season: int,
) -> Dict[str, Dict[str, Any]]:
    """Map packaged staff → continuity ``new_hc`` / ``new_oc`` inputs.

    Unknown continuity flags stay omitted (→ approximate neutral), never
    defaulted to ``new=True``.
    """
    book, _meta = load_packaged_coaching_staff(season)
    out: Dict[str, Dict[str, Any]] = {}
    for team, row in book.items():
        entry: Dict[str, Any] = {"notes": row.get("notes") or ""}
        if row.get("new_hc") is not None:
            entry["new_hc"] = bool(row["new_hc"])
        if row.get("new_oc") is not None:
            entry["new_oc"] = bool(row["new_oc"])
        # Only include teams with at least one known continuity flag or a note.
        if "new_hc" in entry or "new_oc" in entry or entry["notes"]:
            out[team] = entry
    return out


def coaching_intel_rows(
    *,
    season: int,
    team: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Flatten packaged staff into intel-style rows for UI tables."""
    book, meta = load_packaged_coaching_staff(season)
    wanted = normalize_team_abbr(team) if team else None
    rows: List[Dict[str, Any]] = []
    for code in NFL_TEAMS:
        if wanted and code != wanted:
            continue
        entry = book.get(code)
        if entry is None:
            rows.append(
                {
                    "season": int(season),
                    "team": code,
                    "hc_name": None,
                    "oc_name": None,
                    "dc_name": None,
                    "new_hc": None,
                    "new_oc": None,
                    "new_dc": None,
                    "continuity_label": "unknown",
                    "notes": "",
                    "source": "missing",
                    "status": "thin",
                }
            )
            continue
        new_hc = entry.get("new_hc")
        new_oc = entry.get("new_oc")
        if new_hc is True or new_oc is True:
            continuity_label = "new_staff"
        elif new_hc is False and new_oc is False:
            continuity_label = "returning"
        elif new_hc is False or new_oc is False:
            continuity_label = "partial_change"
        else:
            continuity_label = "unknown"
        status = "live"
        if not entry.get("hc_name") or not entry.get("oc_name"):
            status = "thin"
        elif not entry.get("dc_name"):
            status = "thin_dc"
        rows.append(
            {
                "season": int(season),
                "team": code,
                "hc_name": entry.get("hc_name"),
                "oc_name": entry.get("oc_name"),
                "dc_name": entry.get("dc_name"),
                "new_hc": new_hc,
                "new_oc": new_oc,
                "new_dc": entry.get("new_dc"),
                "continuity_label": continuity_label,
                "notes": entry.get("notes") or "",
                "source": entry.get("source") or meta.get("coaching_source"),
                "status": status,
            }
        )
    return rows, meta


def depth_slot_for_order(depth_order: int) -> str:
    if depth_order <= 1:
        return "starter"
    if depth_order == 2:
        return "backup"
    if depth_order == 3:
        return "rotation"
    return "depth"


def packaged_depth_intel_rows(
    *,
    season: int,
    week: int = 1,
    team: Optional[str] = None,
    limit: int = 800,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Project packaged depth into ``/intel/depth-charts`` row shape."""
    from src.services.nfl_season_engine.loaders import load_packaged_depth_chart

    rows_raw, meta = load_packaged_depth_chart(int(season))
    wanted = normalize_team_abbr(team) if team else None
    pos_rank = {"QB": 0, "RB": 1, "WR": 2, "TE": 3}
    out: List[Dict[str, Any]] = []
    for r in rows_raw:
        code = str(r.get("team") or "")
        if wanted and code != wanted:
            continue
        depth_order = int(r.get("depth_order") or 0)
        out.append(
            {
                "season": int(season),
                "week": int(week),
                "team": code,
                "position": str(r.get("position") or ""),
                "depth_slot": depth_slot_for_order(depth_order),
                "depth_order": depth_order,
                "player_uid": str(r.get("player_id") or "") or None,
                "player_id": str(r.get("player_id") or "") or None,
                "player_name": str(r.get("player_name") or ""),
                "role_confidence": float(r.get("role_confidence") or 0.0),
                "inferred_source": str(
                    meta.get("roster_source") or "packaged_nflverse_depth_2026"
                ),
            }
        )
    out.sort(
        key=lambda row: (
            str(row["team"]),
            pos_rank.get(str(row["position"]), 10),
            str(row["position"]),
            {"starter": 0, "backup": 1, "rotation": 2, "depth": 3}.get(
                str(row["depth_slot"]), 4
            ),
            int(row["depth_order"]),
            str(row["player_name"]),
        )
    )
    if limit > 0:
        out = out[: int(limit)]
    pack_meta = {
        **meta,
        "packaged_fallback": True,
        "depth_intel_row_count": len(out),
    }
    return out, pack_meta


def packaged_roster_pulse_rows(
    *,
    season: int,
    week: int = 1,
    team: Optional[str] = None,
    limit: int = 500,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Hierarchy pulse from the same packaged depth (not a second research path)."""
    depth_rows, meta = packaged_depth_intel_rows(
        season=season, week=week, team=team, limit=limit
    )
    out: List[Dict[str, Any]] = []
    for r in depth_rows:
        out.append(
            {
                "season": int(season),
                "week": int(week),
                "team": r["team"],
                "player_id": r.get("player_id"),
                "player_name": r.get("player_name"),
                "position": r.get("position"),
                "jersey_number": None,
                "roster_source": meta.get("roster_source"),
                "depth_slot": r.get("depth_slot"),
                "depth_order": r.get("depth_order"),
                "role_confidence": r.get("role_confidence"),
                "report_status": None,
                "practice_status": None,
                "injury": None,
                "injury_source": None,
            }
        )
    return out, {**meta, "roster_pulse_from": "packaged_depth"}
