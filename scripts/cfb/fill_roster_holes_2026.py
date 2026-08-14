#!/usr/bin/env python3
"""Fill the 11 official-FBS roster-pack holes from ESPN (2026-08-13).

Does not rewrite camp QB SoT for UGA/MICH/FSU/LSU/ALA. Research only.

Usage:
  python scripts/cfb/fill_roster_holes_2026.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

HOLES = ("ARST", "CSU", "ECU", "JVST", "MIZZ", "NEV", "ODU", "TOL", "UAB", "UNM", "UNT")
CAMP = ("UGA", "MICH", "FSU", "LSU", "ALA")

PACK = (
    ROOT
    / "scripts"
    / "cfb"
    / "package_real_roster_2026.py"
)


def _load_packer():
    spec = importlib.util.spec_from_file_location("package_real_roster_2026", PACK)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    from src.services.cfb_season_engine.fbs_universe import official_fbs_codes
    from src.services.cfb_warehouse.preseason_prior import (
        USED_IN_SPREAD,
        rebuild_p2_from_packaged,
        write_preseason_priors,
    )

    packer = _load_packer()
    priors = json.loads(packer.PRIORS_PATH.read_text(encoding="utf-8"))
    snap = json.loads(packer.SNAPSHOT_PATH.read_text(encoding="utf-8"))
    espn = packer.load_espn_fbs_teams()
    before = [c for c in HOLES if c not in (snap.get("teams") or {})]
    print(f"holes before: {before}", file=sys.stderr)

    filled: Dict[str, Dict[str, Any]] = {}
    still: List[str] = []
    for code in HOLES:
        resolved = packer.resolve_espn_team(code, espn)
        if not resolved:
            still.append(code)
            print(f"{code}: NO ESPN MATCH", file=sys.stderr)
            continue
        espn_ab, meta = resolved
        print(f"{code} ← ESPN {espn_ab} ({meta['name']})", file=sys.stderr)
        payload = packer.enrich_team(
            team_code=code,
            espn_ab=espn_ab,
            espn_meta=meta,
            prior_payload=(priors.get("teams") or {}).get(code) or {},
            sleep_s=0.08,
            enrich_portal_sample=12,
        )
        filled[code] = payload

    teams = snap.setdefault("teams", {})
    for code, payload in filled.items():
        teams[code] = payload
    snap["as_of"] = date.today().isoformat()
    snap["team_count"] = len(teams)
    snap["unmatched_team_codes"] = [
        c for c in (snap.get("unmatched_team_codes") or []) if c not in filled
    ]
    snap["coverage"] = {
        "teams_with_roster": sum(1 for p in teams.values() if p.get("athlete_count", 0) > 0),
        "teams_with_named_qb": sum(
            1 for p in teams.values() if (p.get("qb") or {}).get("starter_name")
        ),
        "teams_with_portal_in": sum(1 for p in teams.values() if p.get("portal_in_count", 0) > 0),
        "total_athletes": sum(int(p.get("athlete_count") or 0) for p in teams.values()),
        "total_depth_rows": sum(len(p.get("depth") or []) for p in teams.values()),
        "official_holes_filled": sorted(filled),
        "official_holes_still_missing": still,
    }
    notes = list(snap.get("notes") or [])
    notes.append(
        "2026-08-13: filled official-FBS roster holes ARST/CSU/ECU/JVST/MIZZ/NEV/ODU/TOL/UAB/UNM/UNT from ESPN."
    )
    snap["notes"] = notes
    packer.SNAPSHOT_PATH.write_text(json.dumps(snap, indent=2) + "\n", encoding="utf-8")

    merged = packer.merge_into_priors(priors, {**{k: teams[k] for k in filled}})
    # Drop FCS contaminants from the engine prior book.
    official = official_fbs_codes()
    merged_teams = merged.setdefault("teams", {})
    for junk in list(merged_teams):
        if junk not in official and junk not in filled:
            # keep existing official; drop known extras only
            if junk in {
                "ACU",
                "CHAT",
                "FAU2",
                "FAY",
                "IDHO",
                "OLE",
                "OREST",
                "SOUTH",
                "TA&M",
                "TXAM",
                "ULL",
            }:
                merged_teams.pop(junk, None)
    packer.PRIORS_PATH.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")

    rows = rebuild_p2_from_packaged(prior_year=2026, as_of=date.today().isoformat())
    write_preseason_priors(rows, prior_year=2026, prefer_hd=False, package_json=True)

    after_missing = [
        r["team_id"]
        for r in rows
        if "roster_pack_missing_neutral" in (r.get("components") or {}).get("missing_data", [])
    ]
    camp = {}
    from src.services.cfb_season_engine import build_packaged_universe

    # bust cache
    from src.services.cfb_season_engine import loaders

    loaders._PACKAGED_UNIVERSE_CACHE.clear()
    universe = build_packaged_universe(2026)
    for team in CAMP:
        qb = universe.teams[team].qb
        camp[team] = qb.qb_class if qb else None

    report = {
        "as_of": date.today().isoformat(),
        "used_in_spread": USED_IN_SPREAD,
        "holes_before": before,
        "filled": {
            code: {
                "espn": filled[code].get("espn_team_name"),
                "athletes": filled[code].get("athlete_count"),
                "qb": (filled[code].get("qb") or {}).get("starter_name"),
                "qb_class": (filled[code].get("qb") or {}).get("qb_class"),
            }
            for code in filled
        },
        "still_missing": still,
        "prior_roster_pack_missing": after_missing,
        "official_in_universe": sum(1 for c in official if c in universe.teams),
        "camp_qb_classes": camp,
        "mizz_in_universe": "MIZZ" in universe.teams,
    }
    out = ROOT / "data" / "ops" / "cfb-2026-roster-holes-20260813.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if not still else 1


if __name__ == "__main__":
    raise SystemExit(main())
