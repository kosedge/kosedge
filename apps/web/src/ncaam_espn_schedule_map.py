"""ESPN NCAAM team → B7 team_id map helpers (fail-closed).

Uses ``ncaam_identity.resolve_team_id`` / aliases.json. Never invents IDs.
Bare ``miami`` stays omit (Miami FL ≠ Miami OH).
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from ncaam_identity import resolve_team_id

# Prefer full ESPN display names before bare location (bare "Miami" is omit).
_CANDIDATE_KEYS = (
    "displayName",
    "location_name",  # synthetic location + name
    "shortDisplayName",
    "location",
    "abbreviation",
)


def espn_team_candidates(team: Mapping[str, Any]) -> Sequence[str]:
    location = str(team.get("location") or "").strip()
    name = str(team.get("name") or "").strip()
    loc_name = f"{location} {name}".strip()
    ordered = [
        str(team.get("displayName") or "").strip(),
        loc_name,
        str(team.get("shortDisplayName") or "").strip(),
        location,
        str(team.get("abbreviation") or "").strip(),
    ]
    out: list[str] = []
    seen: set[str] = set()
    for c in ordered:
        if not c:
            continue
        key = c.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def resolve_espn_team_id(team: Mapping[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """Return ``(team_id, matched_alias)`` or ``(None, None)`` if omit/unknown."""
    for cand in espn_team_candidates(team):
        tid = resolve_team_id(cand, source="espn")
        if tid:
            return tid, cand
    return None, None


def map_espn_event_sides(
    home_team: Mapping[str, Any], away_team: Mapping[str, Any]
) -> Dict[str, Any]:
    """Fail-closed both-side map for one ESPN competition.

    If either side is unknown/ambiguous, ``ok`` is False and team_ids are null.
    """
    home_id, home_alias = resolve_espn_team_id(home_team)
    away_id, away_alias = resolve_espn_team_id(away_team)
    ok = bool(home_id and away_id and home_id != away_id)
    return {
        "ok": ok,
        "home": home_id,
        "away": away_id,
        "home_matched_alias": home_alias,
        "away_matched_alias": away_alias,
        "home_name": str(home_team.get("displayName") or home_team.get("location") or ""),
        "away_name": str(away_team.get("displayName") or away_team.get("location") or ""),
        "home_espn_id": str(home_team.get("id") or ""),
        "away_espn_id": str(away_team.get("id") or ""),
        "reason": None
        if ok
        else (
            "same_side"
            if home_id and away_id and home_id == away_id
            else "unmapped_or_ambiguous"
        ),
    }
