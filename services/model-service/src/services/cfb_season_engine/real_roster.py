"""Real 2026 roster snapshot helpers (ESPN packaged feed).

Preference order used by loaders:

1. DB universe (when wired / populated)
2. Packaged ``cfb_real_roster_snapshot_2026.json`` overlay on team priors
3. Legacy curated/placeholder priors alone

This module never invents precision — derived returning/portal numerics stay
labeled approximate even when athlete identities are real.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

DATA_DIR = Path(__file__).resolve().parent / "data"
SNAPSHOT_PATH = DATA_DIR / "cfb_real_roster_snapshot_2026.json"

ROSTER_SOURCE_PACKAGED_ESPN = "packaged_espn_roster_2026"
ROSTER_SOURCE_LEGACY_PRIORS = "packaged_curated_priors"
DEPTH_SOURCE_PACKAGED = "espn_roster_production_depth"
PORTAL_SOURCE_PACKAGED = "espn_athlete_team_history"
RETURNING_SOURCE_PACKAGED = "espn_class_year_plus_qb_stats"


def snapshot_path() -> Path:
    return SNAPSHOT_PATH


def load_real_roster_snapshot() -> Optional[Dict[str, Any]]:
    if not SNAPSHOT_PATH.is_file():
        return None
    with SNAPSHOT_PATH.open("r", encoding="utf-8") as fh:
        blob = json.load(fh)
    if not isinstance(blob, dict) or not blob.get("teams"):
        return None
    return blob


def snapshot_coverage(blob: Mapping[str, Any]) -> Dict[str, Any]:
    cov = dict(blob.get("coverage") or {})
    teams = blob.get("teams") or {}
    cov.setdefault("team_count", len(teams))
    cov.setdefault(
        "teams_with_named_qb",
        sum(1 for t in teams.values() if (t.get("qb") or {}).get("starter_name")),
    )
    cov.setdefault(
        "teams_with_roster",
        sum(1 for t in teams.values() if int(t.get("athlete_count") or 0) > 0),
    )
    return cov


def snapshot_meta(blob: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if not blob:
        return {
            "present": False,
            "roster_source": ROSTER_SOURCE_LEGACY_PRIORS,
            "depth_source": "none",
            "portal_source": "none",
            "returning_source": "none",
            "as_of": "",
            "coverage": {},
        }
    return {
        "present": True,
        "roster_source": str(blob.get("roster_source") or ROSTER_SOURCE_PACKAGED_ESPN),
        "depth_source": str(blob.get("depth_source") or DEPTH_SOURCE_PACKAGED),
        "portal_source": str(blob.get("portal_source") or PORTAL_SOURCE_PACKAGED),
        "returning_source": str(blob.get("returning_source") or RETURNING_SOURCE_PACKAGED),
        "recruiting_source": str(blob.get("recruiting_source") or ""),
        "as_of": str(blob.get("as_of") or ""),
        "coverage": snapshot_coverage(blob),
        "cfbd": blob.get("cfbd") or {},
        "unmatched_team_codes": list(blob.get("unmatched_team_codes") or []),
    }


def apply_snapshot_team_payload(
    base: Mapping[str, Any],
    snap_team: Mapping[str, Any],
) -> Dict[str, Any]:
    """Merge snapshot roster/qb/units/players onto a priors team row."""
    out = dict(base)
    if snap_team.get("roster"):
        out["roster"] = dict(snap_team["roster"])
    if snap_team.get("qb"):
        out["qb"] = dict(snap_team["qb"])
    if snap_team.get("position_groups"):
        out["position_groups"] = dict(snap_team["position_groups"])
    if snap_team.get("players"):
        out["players"] = list(snap_team["players"])
    return out


def documentation() -> Dict[str, Any]:
    blob = load_real_roster_snapshot()
    meta = snapshot_meta(blob)
    return {
        "module": "src.services.cfb_season_engine.real_roster",
        "snapshot_path": str(SNAPSHOT_PATH),
        "preference": "DB → packaged ESPN snapshot → legacy curated priors",
        **meta,
        "real_vs_approximate": (
            "Snapshot artifact is REAL and shipped in-image. Athlete identities "
            "and QB classification inputs are from ESPN 2026 rosters. Returning "
            "snap/start shares and portal-out remain APPROXIMATE proxies unless "
            "a CFBD overlay was applied at package time."
        ),
    }
