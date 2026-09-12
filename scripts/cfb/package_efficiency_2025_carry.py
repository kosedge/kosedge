#!/usr/bin/env python3
"""Package final-2025 SP+ opponent-adjusted efficiency for 2026 preseason carry.

Default source: public final SP+ table (cfbupdate / ESPN story).
Optional: when CFBD_API_KEY is set, prefer CFBD /ratings/sp?year=2025.

Writes:
  services/model-service/src/services/cfb_season_engine/data/
    cfb_efficiency_snapshot_2025_carry_2026.json

Honesty: success_off/def and explosiveness are SP+-correlated proxies —
not true play-by-play success-rate / iso-explosiveness. No full PBP store.
"""

from __future__ import annotations

import argparse
import html as html_lib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
sys.path.insert(0, str(MS))

from src.services.cfb_season_engine.fbs_universe import official_fbs_codes  # noqa: E402
from src.services.cfb_season_engine.name_to_code import (  # noqa: E402
    NAME_TO_CODE,
    P0_REQUIRED_CODES,
    P0_REQUIRED_NAME_TO_CODE,
    assert_p0_codes_mapped,
    require_mapped_code,
    resolve_public_table_name,
)
from src.services.cfb_season_engine.team_features import (  # noqa: E402
    MissingRequiredTeamFeature,
)

DATA = (
    ROOT
    / "services"
    / "model-service"
    / "src"
    / "services"
    / "cfb_season_engine"
    / "data"
)
PRIORS_PATH = DATA / "cfb_fbs_team_priors_2026.json"
OUT_PATH = DATA / "cfb_efficiency_snapshot_2025_carry_2026.json"

ALIASES = {
    "TXAM": "TAMU",
    "TA&M": "TAMU",
    "OLE": "MISS",
    "OREST": "ORST",
    "ULL": "UL",
    "FAU2": "FAU",
}


def _num_rank(s: str) -> Tuple[float, Optional[int]]:
    mm = re.match(r"([-+]?\d+(?:\.\d+)?)\s*(?:\((\d+)\))?", s.strip())
    if not mm:
        return 0.0, None
    return float(mm.group(1)), int(mm.group(2)) if mm.group(2) else None


def _z_to_score(z: float, scale: float = 18.0) -> float:
    return max(5.0, min(95.0, 50.0 + scale * z))


# Chapter 2 Phase 2B — must match priors.EFF_CARRY_SHRINK (compose SoT).
CARRY_SHRINK = 0.85


def _apply_carry_shrink(value: float, shrink: float = CARRY_SHRINK) -> float:
    return 50.0 + float(shrink) * (float(value) - 50.0)


def fetch_sp_plus_public() -> List[Dict[str, Any]]:
    url = "https://cfbupdate.com/sp-ratings"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 kosedge"})
    html = urllib.request.urlopen(req, timeout=45).read().decode("utf-8", "replace")
    rows = re.findall(r"<tr[^>]*>.*?</tr>", html, flags=re.I | re.S)
    out: List[Dict[str, Any]] = []
    miami_seen = 0
    for r in rows[1:]:
        cells = [
            " ".join(re.sub("<[^>]+>", "", c).split())
            for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, flags=re.I | re.S)
        ]
        if len(cells) < 5:
            continue
        team_cell = html_lib.unescape(cells[0])
        m = re.match(r"(\d+)\.\s*(.+?)\s*\(([^)]*)\)\s*$", team_cell)
        if not m:
            continue
        name = m.group(2).strip()
        if name == "Miami":
            miami_seen += 1
        if name in P0_REQUIRED_NAME_TO_CODE:
            code = require_mapped_code(name)
        else:
            code = resolve_public_table_name(name, miami_ordinal=miami_seen)
        off, off_r = _num_rank(cells[2])
        deff, def_r = _num_rank(cells[3])
        st, st_r = _num_rank(cells[4])
        out.append(
            {
                "rank": int(m.group(1)),
                "name": name,
                "record": m.group(3),
                "team": code,
                "sp_plus": float(cells[1]),
                "sp_offense": off,
                "sp_offense_rank": off_r,
                "sp_defense": deff,
                "sp_defense_rank": def_r,
                "sp_special_teams": st,
                "sp_st_rank": st_r,
            }
        )
    return out


def fetch_sp_plus_cfbd(year: int = 2025) -> Optional[List[Dict[str, Any]]]:
    key = os.environ.get("CFBD_API_KEY") or os.environ.get("CFBD_KEY")
    if not key:
        return None
    url = f"https://api.collegefootballdata.com/ratings/sp?year={year}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
            "User-Agent": "kosedge-efficiency-packager",
        },
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        rows = json.loads(resp.read().decode("utf-8"))
    out: List[Dict[str, Any]] = []
    for i, row in enumerate(sorted(rows, key=lambda r: -float(r.get("rating") or 0))):
        name = str(row.get("team") or "")
        if name in P0_REQUIRED_NAME_TO_CODE:
            code = require_mapped_code(name)
        else:
            code = resolve_public_table_name(name)
        offense = row.get("offense") or {}
        defense = row.get("defense") or {}
        specials = row.get("specialTeams") or {}
        out.append(
            {
                "rank": i + 1,
                "name": name,
                "record": "",
                "team": code,
                "sp_plus": float(row.get("rating") or 0.0),
                "sp_offense": float(offense.get("rating") or 0.0),
                "sp_offense_rank": offense.get("ranking"),
                "sp_defense": float(defense.get("rating") or 0.0),
                "sp_defense_rank": defense.get("ranking"),
                "sp_special_teams": float(specials.get("rating") or 0.0),
                "sp_st_rank": specials.get("ranking"),
            }
        )
    return out


def build_snapshot(rows: List[Dict[str, Any]], *, source_primary: str) -> Dict[str, Any]:
    assert_p0_codes_mapped(NAME_TO_CODE)
    official = official_fbs_codes()
    # Official 2026 FBS lock is the snapshot universe — not the stale priors key set.
    codes = set(official)
    mean_off = mean(p["sp_offense"] for p in rows) if rows else 27.0
    mean_def = mean(p["sp_defense"] for p in rows) if rows else 27.0
    sd_off = pstdev(p["sp_offense"] for p in rows) if len(rows) > 1 else 1.0
    sd_def = pstdev(p["sp_defense"] for p in rows) if len(rows) > 1 else 1.0
    mean_st = mean(p["sp_special_teams"] for p in rows) if rows else 0.0
    sd_off = sd_off or 1.0
    sd_def = sd_def or 1.0

    teams: Dict[str, Any] = {}
    for p in rows:
        code = p.get("team")
        if not code or code not in codes:
            continue
        z_off = (p["sp_offense"] - mean_off) / sd_off
        z_def = (mean_def - p["sp_defense"]) / sd_def
        # Raw z→score, then global carry shrink toward league 50 (Chapter 2 2B).
        off_raw = _z_to_score(z_off)
        def_raw = _z_to_score(z_def)
        suc_off_raw = _z_to_score(0.85 * z_off, scale=16.0)
        suc_def_raw = _z_to_score(0.85 * z_def, scale=16.0)
        expl_raw = _z_to_score(
            max(-1.5, z_off - 0.35 * max(0.0, -z_off)), scale=17.0
        )
        teams[code] = {
            "team": code,
            "sp_plus": p["sp_plus"],
            "sp_offense": p["sp_offense"],
            "sp_defense": p["sp_defense"],
            "sp_special_teams": p["sp_special_teams"],
            "sp_rank": p["rank"],
            "sp_offense_rank": p.get("sp_offense_rank"),
            "sp_defense_rank": p.get("sp_defense_rank"),
            "off_eff": round(_apply_carry_shrink(off_raw), 2),
            "def_eff": round(_apply_carry_shrink(def_raw), 2),
            "success_off": round(_apply_carry_shrink(suc_off_raw), 2),
            "success_def": round(_apply_carry_shrink(suc_def_raw), 2),
            "explosiveness": round(_apply_carry_shrink(expl_raw), 2),
            "off_eff_pre_shrink": round(off_raw, 2),
            "def_eff_pre_shrink": round(def_raw, 2),
            "prior_year": 2025,
            "carry_to_season": 2026,
            "carry_shrink": CARRY_SHRINK,
            "source": "packaged_sp_plus_final_2025",
            "fidelity": "approximate",
            "notes": (
                "Final-2025 SP+ offense/defense (opponent-adjusted efficiency). "
                "success_* / explosiveness are SP+-correlated proxies, not PBP EPA rates. "
                f"Preseason 2026 carry — EFF_CARRY_SHRINK={CARRY_SHRINK} toward 50."
            ),
        }

    missing_official: List[str] = []
    for code in sorted(official):
        row = teams.get(code)
        if row and str(row.get("source") or "") == "league_average_fill":
            missing_official.append(code)
            continue
        if row:
            continue
        canon = ALIASES.get(code, code)
        if canon in teams and code != canon:
            copied = dict(teams[canon])
            copied["team"] = code
            copied["alias_of"] = canon
            copied["source"] = "packaged_sp_plus_final_2025_alias"
            teams[code] = copied
            continue
        missing_official.append(code)
    if missing_official:
        raise MissingRequiredTeamFeature(
            "Official 2026 FBS codes have no mapped SP+ row — hard-fail, "
            f"do not league-average fill: {missing_official}"
        )

    return {
        "as_of": "2026-08-31",
        "prior_season": 2025,
        "carry_to_season": 2026,
        "carry_shrink": CARRY_SHRINK,
        "fidelity": "approximate",
        "metric_family": "sp_plus_opponent_adjusted_efficiency",
        "source": {
            "primary": source_primary,
            "reference_url": "https://cfbupdate.com/sp-ratings",
            "espn_story": (
                "https://www.espn.com/college-football/story/_/id/46128861/"
                "2025-college-football-sp+-rankings-all-136-fbs-teams"
            ),
            "cfbd": "optional_when_CFBD_API_KEY (ratings/sp)",
            "pbp": "not_used",
            "carry_shrink": (
                f"off_eff/def_eff/success/explosiveness = "
                f"50 + {CARRY_SHRINK}*(raw_2025 - 50); sp_* unchanged"
            ),
        },
        "normalization": {
            "sp_offense_mean": round(mean_off, 4),
            "sp_defense_mean": round(mean_def, 4),
            "sp_offense_sd": round(sd_off, 4),
            "sp_defense_sd": round(sd_def, 4),
            "score_map": (
                "raw off_eff/def_eff = 50 + 18*z (clamp 5–95); "
                "defense z inverted so higher=better; "
                f"then EFF_CARRY_SHRINK={CARRY_SHRINK} toward 50"
            ),
            "success_explosiveness": (
                "Proxies from SP+ z-scores (muted), not true success-rate / "
                "iso-explosiveness PBP; same carry shrink as off/def_eff"
            ),
            "eff_carry_shrink": CARRY_SHRINK,
        },
        "notes": [
            "2025 final SP+ is opponent-adjusted efficiency (Bill Connelly). "
            "Packaged for 2026 preseason carry.",
            f"Chapter 2 Phase 2B: EFF_CARRY_SHRINK={CARRY_SHRINK} toward league 50.",
            "No full PBP store in-repo; CFBD advanced/PPA optional when key present.",
            "success_off/def and explosiveness are approximate SP+-correlated proxies.",
            "Do not treat as live in-season SP+ updates until a refresh pipeline is wired.",
        ],
        "team_count": len(teams),
        "mapped_from_sp_plus": sum(
            1 for t in teams.values() if str(t["source"]).startswith("packaged_sp_plus")
        ),
        "teams": teams,
    }


ESPN_FINAL_2025_STORY = (
    "https://www.espn.com/college-football/story/_/id/46128861/"
    "2025-college-football-sp+-rankings-all-136-fbs-teams"
)


def fetch_sp_plus_espn_final_2025() -> List[Dict[str, Any]]:
    """Year-locked final-2025 SP+ table. Do not use the live cfbupdate board."""
    req = urllib.request.Request(
        ESPN_FINAL_2025_STORY, headers={"User-Agent": "Mozilla/5.0 kosedge"}
    )
    html = urllib.request.urlopen(req, timeout=45).read().decode("utf-8", "replace")
    rows = re.findall(r"<tr[^>]*>.*?</tr>", html, flags=re.I | re.S)
    out: List[Dict[str, Any]] = []
    miami_seen = 0
    for r in rows:
        cells = [
            " ".join(re.sub("<[^>]+>", "", c).split())
            for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, flags=re.I | re.S)
        ]
        if len(cells) < 5:
            continue
        team_cell = html_lib.unescape(cells[0])
        m = re.match(r"(\d+)\.\s*(.+?)\s*\(([^)]*)\)\s*$", team_cell)
        if not m:
            continue
        name = m.group(2).strip()
        if name == "Miami":
            miami_seen += 1
        if name in P0_REQUIRED_NAME_TO_CODE:
            code = require_mapped_code(name)
        else:
            code = resolve_public_table_name(name, miami_ordinal=miami_seen)
        if not code:
            continue
        off, off_r = _num_rank(cells[2])
        deff, def_r = _num_rank(cells[3])
        st, st_r = _num_rank(cells[4])
        out.append(
            {
                "rank": int(m.group(1)),
                "name": name,
                "record": m.group(3),
                "team": code,
                "sp_plus": float(cells[1]),
                "sp_offense": off,
                "sp_offense_rank": off_r,
                "sp_defense": deff,
                "sp_defense_rank": def_r,
                "sp_special_teams": st,
                "sp_st_rank": st_r,
            }
        )
    return out


def _row_from_sp(
    p: Dict[str, Any],
    *,
    mean_off: float,
    mean_def: float,
    sd_off: float,
    sd_def: float,
) -> Dict[str, Any]:
    z_off = (p["sp_offense"] - mean_off) / sd_off
    z_def = (mean_def - p["sp_defense"]) / sd_def
    off_raw = _z_to_score(z_off)
    def_raw = _z_to_score(z_def)
    suc_off_raw = _z_to_score(0.85 * z_off, scale=16.0)
    suc_def_raw = _z_to_score(0.85 * z_def, scale=16.0)
    expl_raw = _z_to_score(max(-1.5, z_off - 0.35 * max(0.0, -z_off)), scale=17.0)
    return {
        "team": p["team"],
        "sp_plus": p["sp_plus"],
        "sp_offense": p["sp_offense"],
        "sp_defense": p["sp_defense"],
        "sp_special_teams": p["sp_special_teams"],
        "sp_rank": p["rank"],
        "sp_offense_rank": p.get("sp_offense_rank"),
        "sp_defense_rank": p.get("sp_defense_rank"),
        "off_eff": round(_apply_carry_shrink(off_raw), 2),
        "def_eff": round(_apply_carry_shrink(def_raw), 2),
        "success_off": round(_apply_carry_shrink(suc_off_raw), 2),
        "success_def": round(_apply_carry_shrink(suc_def_raw), 2),
        "explosiveness": round(_apply_carry_shrink(expl_raw), 2),
        "off_eff_pre_shrink": round(off_raw, 2),
        "def_eff_pre_shrink": round(def_raw, 2),
        "prior_year": 2025,
        "carry_to_season": 2026,
        "carry_shrink": CARRY_SHRINK,
        "source": "packaged_sp_plus_final_2025",
        "fidelity": "approximate",
        "notes": (
            "Final-2025 SP+ offense/defense (opponent-adjusted efficiency). "
            "success_* / explosiveness are SP+-correlated proxies, not PBP EPA rates. "
            f"Preseason 2026 carry — EFF_CARRY_SHRINK={CARRY_SHRINK} toward 50. "
            "Spliced onto the frozen carry snapshot (league z-score norms unchanged)."
        ),
    }


def splice_p0_into_existing_snapshot(
    snap: Dict[str, Any], rows: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Add missing P0 official codes only. Do not retune existing team rows."""
    assert_p0_codes_mapped(NAME_TO_CODE)
    official = official_fbs_codes()
    teams = dict(snap.get("teams") or {})
    norm = snap.get("normalization") or {}
    mean_off = float(norm.get("sp_offense_mean") or 27.2147)
    mean_def = float(norm.get("sp_defense_mean") or 26.486)
    sd_off = float(norm.get("sp_offense_sd") or 7.1878) or 1.0
    sd_def = float(norm.get("sp_defense_sd") or 7.3995) or 1.0
    by_code = {str(p.get("team") or ""): p for p in rows if p.get("team")}
    missing: List[str] = []
    added: List[str] = []
    for code in P0_REQUIRED_CODES:
        if code not in official:
            continue
        if code in teams and str(teams[code].get("source") or "").startswith(
            "packaged_sp_plus"
        ):
            continue
        p = by_code.get(code)
        if not p:
            missing.append(code)
            continue
        teams[code] = _row_from_sp(
            p, mean_off=mean_off, mean_def=mean_def, sd_off=sd_off, sd_def=sd_def
        )
        added.append(code)
    if missing:
        raise MissingRequiredTeamFeature(
            "Required official FBS codes have no mapped SP+ row — hard-fail, "
            f"do not league-average fill: {missing}"
        )
    snap = dict(snap)
    snap["teams"] = teams
    snap["team_count"] = len(teams)
    snap["mapped_from_sp_plus"] = sum(
        1 for t in teams.values() if str(t["source"]).startswith("packaged_sp_plus")
    )
    notes = list(snap.get("notes") or [])
    notes.append(
        "P0 splice 2026-09-11: MIZZ/ARST/CSU/ECU/JVST/NEV/ODU/TOL/UAB/UNM/UNT "
        "from ESPN final-2025 story using frozen snapshot z-score norms "
        "(no live cfbupdate retune)."
    )
    snap["notes"] = notes
    src = dict(snap.get("source") or {})
    src["p0_splice"] = "espn_final_2025_story_onto_frozen_norms"
    snap["source"] = src
    print(f"spliced P0 codes {added}", file=sys.stderr)
    return snap


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    parser.add_argument(
        "--splice-p0-only",
        action="store_true",
        help="Add missing P0 rows onto the existing snapshot; do not rebuild league z-scores",
    )
    args = parser.parse_args()

    if args.splice_p0_only:
        if not args.out.is_file():
            print(f"ERROR: missing snapshot {args.out}", file=sys.stderr)
            return 1
        rows = fetch_sp_plus_espn_final_2025()
        if not rows:
            print("ERROR: no ESPN final-2025 SP+ rows fetched", file=sys.stderr)
            return 1
        try:
            snap = splice_p0_into_existing_snapshot(
                json.loads(args.out.read_text(encoding="utf-8")), rows
            )
        except MissingRequiredTeamFeature as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        args.out.write_text(json.dumps(snap, indent=2) + "\n", encoding="utf-8")
        print(
            f"Spliced P0 into {args.out} teams={snap['team_count']} "
            f"mapped={snap['mapped_from_sp_plus']} source=espn_final_2025_story"
        )
        return 0

    rows = fetch_sp_plus_cfbd(2025)
    source = "cfbd_ratings_sp_2025"
    if not rows:
        rows = fetch_sp_plus_espn_final_2025()
        source = "espn_final_2025_sp_plus_story"
    if not rows:
        rows = fetch_sp_plus_public()
        source = "final_2025_sp_plus_public_table"
    if not rows:
        print("ERROR: no SP+ rows fetched", file=sys.stderr)
        return 1

    try:
        snap = build_snapshot(rows, source_primary=source)
    except MissingRequiredTeamFeature as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(snap, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {args.out} teams={snap['team_count']} "
        f"mapped={snap['mapped_from_sp_plus']} source={source}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
