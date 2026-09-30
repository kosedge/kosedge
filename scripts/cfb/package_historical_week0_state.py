#!/usr/bin/env python3
"""Package year-locked Week-0 ESPN core rosters for 2023–2025.

Research only. Does not apply 2026 recruiting/SP+/coaching. Does not
write KEI. Site roster ?season= is forbidden (current-club leak).

Usage:
  PYTHONPATH=services/model-service \\
    python3 scripts/cfb/package_historical_week0_state.py --seasons 2023,2024,2025
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
sys.path.insert(0, str(MS))

from src.services.cfb_season_engine.fbs_universe import official_fbs_codes  # noqa: E402
from src.services.cfb_season_engine.hist_week0 import (  # noqa: E402
    FIELD_AUDIT,
    reconstruction_inventory,
)

SNAP_2026 = MS / "src/services/cfb_season_engine/data/cfb_real_roster_snapshot_2026.json"
OUT_DIR = MS / "src/services/cfb_season_engine/data"
RAW = ROOT / "data/cfb/raw/espn_core_athletes"
UA = {
    "User-Agent": "Mozilla/5.0 (compatible; KosEdgeHistWeek0/1.0)",
    "Accept": "application/json",
}
CLASS_WEIGHT = {"FR": 0.15, "SO": 0.45, "JR": 0.75, "SR": 0.95, "GR": 1.0}
UNIT_POS = {
    "ol": {"OT", "OG", "C", "OL", "G", "T"},
    "skill": {"RB", "FB", "WR", "TE", "HB"},
    "front_seven": {"DE", "DT", "DL", "NT", "LB", "ILB", "OLB", "EDGE"},
    "secondary": {"CB", "S", "DB", "FS", "SS", "NB"},
    "qb": {"QB"},
}


def _get_json(url: str, *, retries: int = 3) -> Any:
    last: Optional[Exception] = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(0.15 * (i + 1))
    raise RuntimeError(f"GET failed {url}: {last}")


def _https(ref: str) -> str:
    return str(ref).replace("http://", "https://")


def athlete_cache_path(season: int, athlete_id: str) -> Path:
    return RAW / str(season) / f"{athlete_id}.json"


def fetch_athlete(season: int, ref: str) -> Dict[str, Any]:
    aid = ref.rstrip("/").split("athletes/")[-1].split("?")[0]
    path = athlete_cache_path(season, aid)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    blob = _get_json(_https(ref))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(blob), encoding="utf-8")
    return blob


def list_athlete_refs(season: int, espn_team_id: str) -> List[str]:
    refs: List[str] = []
    page = 1
    while True:
        url = (
            "https://sports.core.api.espn.com/v2/sports/football/"
            f"leagues/college-football/seasons/{season}/teams/"
            f"{espn_team_id}/athletes?limit=200&page={page}"
        )
        blob = _get_json(url)
        for item in blob.get("items") or []:
            ref = item.get("$ref") if isinstance(item, dict) else None
            if ref:
                refs.append(ref)
        if page >= int(blob.get("pageCount") or 1):
            break
        page += 1
    return refs


def slim_athlete(blob: Mapping) -> Dict[str, Any]:
    pos = blob.get("position") or {}
    exp = blob.get("experience") or {}
    return {
        "player_id": str(blob.get("id") or ""),
        "player_name": str(blob.get("displayName") or blob.get("fullName") or ""),
        "position": str(pos.get("abbreviation") or ""),
        "experience_abbr": str(exp.get("abbreviation") or ""),
        "experience_years": int(exp.get("years") or 0),
        "is_portal": False,
        "recruiting_unminted": True,
    }


def experience_index(rows: List[Dict[str, Any]]) -> float:
    if not rows:
        return 50.0
    w = [CLASS_WEIGHT.get(str(r.get("experience_abbr") or ""), 0.5) for r in rows]
    return max(0.0, min(100.0, 100.0 * (sum(w) / len(w))))


def qb_class_from_rows(rows: List[Dict[str, Any]]) -> str:
    qbs = [r for r in rows if r.get("position") == "QB"]
    if not qbs:
        return "unknown"
    qbs = sorted(qbs, key=lambda r: -int(r.get("experience_years") or 0))
    ab = str(qbs[0].get("experience_abbr") or "")
    if ab == "FR":
        return "true_freshman"
    if ab in {"SR", "GR", "JR"}:
        return "incumbent"
    return "unknown"


def team_payload(code: str, espn_id: str, season: int, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    exp = experience_index(rows)
    non_fr = [r for r in rows if r.get("experience_abbr") not in ("", "FR")]
    snap = len(non_fr) / max(len(rows), 1) if rows else 0.45
    returning = max(0.0, min(100.0, 100.0 * snap))
    # Recruiting / portal unminted — league 50. Do not copy 2026 priors.
    return {
        "team": code,
        "season": season,
        "espn_team_id": espn_id,
        "athlete_count": len(rows),
        "recruiting_class_score": 50.0,
        "recruiting_unminted": True,
        "portal_in_value": 50.0,
        "portal_out_value": 50.0,
        "portal_unminted": True,
        "experience_index": round(exp, 2),
        "returning_production": round(returning, 2),
        "returning_snap_share": round(snap, 4),
        "qb_class": qb_class_from_rows(rows),
        "qb_talent": 50.0,
        "qb_unminted": True,
        "ol": 50.0,
        "skill": 50.0,
        "front_seven": 50.0,
        "secondary": 50.0,
        "special_teams": 50.0,
        "units_unminted_no_recruiting_anchor": True,
        "athletes": rows,
        "source": "espn_core_season_athletes_year_locked",
        "fidelity": "approximate",
        "notes": (
            "Year-locked ESPN core athletes only. Recruiting/portal/unit talent "
            "unminted (50). Not the 2026 live compose stack."
        ),
    }


def package_season(season: int, *, workers: int, limit_teams: int) -> Dict[str, Any]:
    snap = json.loads(SNAP_2026.read_text(encoding="utf-8"))
    official = official_fbs_codes()
    teams_in = []
    for code, row in (snap.get("teams") or {}).items():
        if code not in official:
            continue
        espn_id = str(row.get("espn_team_id") or "")
        if espn_id:
            teams_in.append((code, espn_id))
    teams_in.sort()
    if limit_teams > 0:
        teams_in = teams_in[:limit_teams]

    out_teams: Dict[str, Any] = {}
    errors: List[str] = []

    def one(item: tuple[str, str]) -> tuple[str, Dict[str, Any]]:
        code, espn_id = item
        refs = list_athlete_refs(season, espn_id)
        rows = []
        with ThreadPoolExecutor(max_workers=min(12, workers)) as pool:
            futs = [pool.submit(fetch_athlete, season, ref) for ref in refs]
            for fut in as_completed(futs):
                rows.append(slim_athlete(fut.result()))
        return code, team_payload(code, espn_id, season, rows)

    with ThreadPoolExecutor(max_workers=max(2, workers // 8)) as pool:
        futs = {pool.submit(one, item): item[0] for item in teams_in}
        for fut in as_completed(futs):
            code = futs[fut]
            try:
                c, payload = fut.result()
                out_teams[c] = payload
                print(f"  {season} {c} n={payload['athlete_count']}")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{code}: {exc}")
                print(f"  ERR {season} {code}: {exc}")

    return {
        "season": season,
        "as_of": f"{season}-08-01",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "path_name": "year_locked_espn_core_roster_plus_sdv_adj_epa",
        "same_as_2026_live_path": False,
        "roster_source": "espn_core_season_athletes_year_locked",
        "recruiting_source": "unminted",
        "portal_source": "unminted",
        "efficiency_source": "not_in_this_file — pair with SDV cfb_ratings_{season-1}",
        "sp_plus_source": "missing",
        "field_audit": FIELD_AUDIT,
        "team_count": len(out_teams),
        "errors": errors,
        "teams": out_teams,
        "notes": [
            "Do not treat this snapshot as 2026 live identity.",
            "Unit grades left at 50 — 2026 talent is recruiting-anchored and that prior is 2026-only.",
            "2025 residuals remain sealed until a 2023–24 freeze exists.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seasons", default="2023,2024,2025")
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--limit-teams", type=int, default=0)
    args = ap.parse_args()
    seasons = [int(s) for s in args.seasons.split(",") if s.strip()]
    print("inventory", json.dumps(reconstruction_inventory()["stop_reason"]))
    for season in seasons:
        print(f"packaging {season}")
        payload = package_season(
            season, workers=args.workers, limit_teams=args.limit_teams
        )
        path = OUT_DIR / f"cfb_week0_roster_snapshot_{season}.json"
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {path} teams={payload['team_count']} errors={len(payload['errors'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
