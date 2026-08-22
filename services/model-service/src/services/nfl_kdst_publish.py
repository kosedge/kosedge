"""K/DST publish contract — Fantasy draft rankings + ST / kicker_layer.

Fantasy waits on named K/DST rows in ``nfl_fantasy_season_draft_rankings``.
Those rows are produced by ``materialize_nfl_fantasy_season_draft_rankings``
from ``nfl_kicker_dst_projections`` (history rates today).

A later 100k resim can drop an optional JSON artifact; this module loads it
without inventing players. Until the file exists, ``load`` returns None and
the Fantasy desk stays honest-empty for K/DST.

Artifact schema (optional file)::

    {
      "season": 2026,
      "source": "player-production-vN-100k",
      "kickers": [
        {"player_id": "...", "team": "KC", "fg_attempts": 32.0, "xp_attempts": 48.0}
      ],
      "dst": [
        {"team": "KC", "points_allowed_mean": 20.4, "sacks": 42.0}
      ]
    }

Path: ``NFL_KDST_PUBLISH_PATH`` or
``data/ops/artifacts/nfl-kdst-season-{season}.json``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


def default_kdst_artifact_path(season: int) -> Path:
    here = Path(__file__).resolve()
    repo = here.parents[4] if len(here.parents) >= 4 else here.parents[-1]
    return repo / "data" / "ops" / "artifacts" / f"nfl-kdst-season-{int(season)}.json"


def load_kdst_publish_artifact(season: int) -> Optional[Dict[str, Any]]:
    override = os.environ.get("NFL_KDST_PUBLISH_PATH")
    path = Path(override) if override else default_kdst_artifact_path(season)
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    art_season = raw.get("season")
    if art_season is not None and int(art_season) != int(season):
        return None
    kickers = raw.get("kickers") if isinstance(raw.get("kickers"), list) else []
    dst = raw.get("dst") if isinstance(raw.get("dst"), list) else []
    return {
        "season": int(season),
        "source": str(raw.get("source") or "artifact"),
        "path": str(path),
        "kickers": list(kickers),
        "dst": list(dst),
    }


def kdst_publish_status(season: int) -> Dict[str, Any]:
    art = load_kdst_publish_artifact(season)
    if not art:
        return {
            "status": "missing",
            "kickers": 0,
            "dst": 0,
            "note": "Honest empty until artifact or history remat publishes K/DST into draft rankings.",
        }
    return {
        "status": "ready",
        "kickers": len(art["kickers"]),
        "dst": len(art["dst"]),
        "source": art.get("source"),
        "path": art.get("path"),
    }


def _team_aliases(team: str) -> set[str]:
    code = str(team or "").strip().upper()
    if code in {"LA", "LAR"}:
        return {"LA", "LAR"}
    return {code} if code else set()


def kdst_volume_overlay_for_team(
    artifact: Optional[Dict[str, Any]],
    team: str,
) -> Optional[Dict[str, float]]:
    """Optional FG/XP volume from a 100k publish — None means keep history priors."""
    if not artifact:
        return None
    aliases = _team_aliases(team)
    for row in artifact.get("kickers") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("team") or "").strip().upper() not in aliases:
            continue
        fg = row.get("fg_attempts")
        xp = row.get("xp_attempts")
        out: Dict[str, float] = {}
        if isinstance(fg, (int, float)):
            out["fg_attempts"] = float(fg)
        if isinstance(xp, (int, float)):
            out["xp_attempts"] = float(xp)
        return out or None
    return None


def named_kickers_from_artifact(
    artifact: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Named K rows from a publish file. Empty if missing ids — never invents names."""
    if not artifact:
        return []
    out: List[Dict[str, Any]] = []
    seen_teams: set[str] = set()
    for row in artifact.get("kickers") or []:
        if not isinstance(row, dict):
            continue
        team = str(row.get("team") or "").strip().upper()
        player_id = str(row.get("player_id") or "").strip()
        if not team or not player_id or team in seen_teams:
            continue
        seen_teams.add(team)
        name = str(row.get("player_name") or "").strip() or player_id
        out.append({"team": team, "player_id": player_id, "player_name": name})
    return out


def dst_overlay_for_team(
    artifact: Optional[Dict[str, Any]],
    team: str,
) -> Optional[Dict[str, float]]:
    """Optional DST volume from a 100k publish — None means keep history priors."""
    if not artifact:
        return None
    aliases = _team_aliases(team)
    for row in artifact.get("dst") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("team") or "").strip().upper() not in aliases:
            continue
        out: Dict[str, float] = {}
        pa = row.get("points_allowed_mean")
        sacks = row.get("sacks")
        if isinstance(pa, (int, float)):
            out["points_allowed_mean"] = float(pa)
        if isinstance(sacks, (int, float)):
            out["sacks"] = float(sacks)
        return out or None
    return None
