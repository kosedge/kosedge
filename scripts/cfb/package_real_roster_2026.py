#!/usr/bin/env python3
"""Package real 2026 CFB roster / depth / portal signals into the season engine.

Primary source (no paid key required): ESPN public roster + athlete bio/overview.
Optional overlay when ``CFBD_API_KEY`` is set:
  - GET /player/returning
  - GET /player/portal
  - GET /recruiting/teams

Writes:
  1. ``cfb_real_roster_snapshot_2026.json`` — inspectable depth + portal rows
  2. Merges roster / qb / position_groups / players into ``cfb_fbs_team_priors_2026.json``
     (preserves home_field + coaching blocks)

Usage:
  python scripts/cfb/package_real_roster_2026.py
  python scripts/cfb/package_real_roster_2026.py --limit-teams 12   # smoke
  CFBD_API_KEY=... python scripts/cfb/package_real_roster_2026.py
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = (
    REPO_ROOT
    / "services/model-service/src/services/cfb_season_engine/data"
)
PRIORS_PATH = DATA_DIR / "cfb_fbs_team_priors_2026.json"
SNAPSHOT_PATH = DATA_DIR / "cfb_real_roster_snapshot_2026.json"
RAW_CACHE_DIR = REPO_ROOT / "data/cfb/raw"

ESPN_WEB = "https://site.web.api.espn.com/apis"
ESPN_UA = {
    "User-Agent": "Mozilla/5.0 (compatible; KosEdgeCFB/0.6; +https://www.kosedge.com)",
    "Accept": "application/json",
    "Referer": "https://www.espn.com/",
}

ROSTER_SOURCE = "packaged_espn_roster_2026"
DEPTH_SOURCE = "espn_roster_production_depth"
PORTAL_SOURCE = "espn_athlete_team_history"
RETURNING_SOURCE = "espn_class_year_plus_qb_stats"
RECRUITING_SOURCE_PRIOR = "packaged_recruiting_prior_retained"
RECRUITING_SOURCE_CFBD = "cfbd_recruiting_teams"

# Exact abbreviation bridges only (no fuzzy slug matching).
ESPN_CODE_ALIASES: Dict[str, str] = {
    "AFA": "AF",
    "ARI": "ARIZ",
    "BOISE": "BOIS",
    "BUFF": "BUF",
    "CHAR": "CLT",
    "CHAT": "UTC",
    "FAU2": "FAU",
    "KENNESAW": "KENN",
    "NW": "NU",
    "OLE": "MISS",
    "OREST": "ORST",
    "RUT": "RUTG",
    "SCAR": "SC",
    "TAMU": "TA&M",
    "TXAM": "TA&M",
    "ULL": "UL",
    "UTAHST": "USU",
    "HAWAII": "HAW",
    "UCONN": "CONN",
    "UMASS": "MASS",
    "APST": "APP",
    "GSU": "GAST",
    "SOMISS": "USM",
    "PIT": "PITT",
    "FRESNO": "FRES",
    "NMST": "NMSU",
    # ESPN uses FLA for the Gators; UF is Findlay (D2).
    "UF": "FLA",
}

UNIT_POS = {
    "ol": {"OT", "OG", "C", "OL", "G", "T"},
    "skill": {"RB", "FB", "WR", "TE", "HB"},
    "front_seven": {"DE", "DT", "DL", "NT", "LB", "ILB", "OLB", "EDGE"},
    "secondary": {"CB", "S", "DB", "FS", "SS", "NB"},
    "qb": {"QB"},
}

CLASS_WEIGHT = {"FR": 0.15, "SO": 0.45, "JR": 0.75, "SR": 0.95, "GR": 1.0}


def _get_json(url: str, *, retries: int = 3, sleep_s: float = 0.12) -> Any:
    last: Optional[Exception] = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=ESPN_UA)
            with urllib.request.urlopen(req, timeout=45) as resp:
                return json.load(resp)
        except Exception as exc:  # noqa: BLE001 — packaging script
            last = exc
            time.sleep(sleep_s * (attempt + 1) * 2)
    raise RuntimeError(f"GET failed {url}: {last}")


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(v)))


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def _parse_int(raw: Any) -> int:
    if raw is None:
        return 0
    if isinstance(raw, (int, float)):
        return int(raw)
    s = str(raw).replace(",", "").strip()
    if not s or s == "-":
        return 0
    try:
        return int(float(s))
    except ValueError:
        return 0


def _parse_float(raw: Any) -> float:
    if raw is None:
        return 0.0
    if isinstance(raw, (int, float)):
        return float(raw)
    s = str(raw).replace(",", "").strip()
    if not s or s == "-":
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def _team_rank_for_abbrev(team: Mapping[str, Any]) -> Tuple[int, int]:
    """Lower rank wins on abbreviation collisions (OSU Buckeyes vs Newark)."""
    name = str(team.get("displayName") or "").lower()
    # Deprioritize junior-college / satellite / club-ish collisions.
    penalty = 0
    for token in (
        "newark",
        "junior",
        "club",
        "alumni",
        "scout",
        "findlay",
        "oilers",
    ):
        if token in name:
            penalty += 100
    try:
        tid = int(team.get("id") or 10**9)
    except ValueError:
        tid = 10**9
    return (penalty, tid)


def load_espn_fbs_teams() -> Dict[str, Dict[str, str]]:
    # groups=80 pagination is incomplete for Power schools; pull full directory
    # and resolve only via exact abbreviation / alias (never fuzzy).
    url = f"{ESPN_WEB}/site/v2/sports/football/college-football/teams?limit=1000"
    blob = _get_json(url)
    best: Dict[str, Mapping[str, Any]] = {}
    for row in blob["sports"][0]["leagues"][0]["teams"]:
        team = row["team"]
        ab = str(team["abbreviation"]).upper()
        prev = best.get(ab)
        if prev is None or _team_rank_for_abbrev(team) < _team_rank_for_abbrev(prev):
            best[ab] = team
    out: Dict[str, Dict[str, str]] = {}
    for ab, team in best.items():
        out[ab] = {
            "id": str(team["id"]),
            "name": str(team["displayName"]),
            "slug": str(team.get("slug") or ""),
            "location": str(team.get("location") or ""),
        }
    return out


def resolve_espn_team(
    code: str, espn: Mapping[str, Mapping[str, str]]
) -> Optional[Tuple[str, Mapping[str, str]]]:
    code_u = code.upper()
    # Explicit engine aliases win over ESPN's raw abbreviation (UF=Findlay vs FLA=Gators).
    alias = ESPN_CODE_ALIASES.get(code_u)
    if alias and alias in espn:
        return alias, espn[alias]
    if code_u in espn:
        return code_u, espn[code_u]
    return None


def flatten_roster(blob: Mapping[str, Any]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for group in blob.get("athletes") or []:
        for ath in group.get("items") or []:
            pos = ath.get("position") or {}
            exp = ath.get("experience") or {}
            items.append(
                {
                    "player_id": str(ath.get("id") or ""),
                    "player_name": str(ath.get("displayName") or ath.get("fullName") or ""),
                    "jersey": str(ath.get("jersey") or ""),
                    "position": str(pos.get("abbreviation") or ""),
                    "position_name": str(pos.get("displayName") or ""),
                    "experience_abbr": str(exp.get("abbreviation") or ""),
                    "experience_years": int(exp.get("years") or 0),
                    "experience_label": str(exp.get("displayValue") or ""),
                }
            )
    return items


def fetch_roster(espn_id: str) -> List[Dict[str, Any]]:
    url = f"{ESPN_WEB}/site/v2/sports/football/college-football/teams/{espn_id}/roster"
    return flatten_roster(_get_json(url))


def fetch_bio(player_id: str) -> Dict[str, Any]:
    url = (
        f"{ESPN_WEB}/common/v3/sports/football/college-football/"
        f"athletes/{player_id}/bio"
    )
    try:
        return _get_json(url)
    except Exception:
        return {}


def fetch_overview(player_id: str) -> Dict[str, Any]:
    url = (
        f"{ESPN_WEB}/common/v3/sports/football/college-football/"
        f"athletes/{player_id}/overview"
    )
    try:
        return _get_json(url)
    except Exception:
        return {}


def team_history_rows(bio: Mapping[str, Any]) -> List[Dict[str, str]]:
    rows = []
    for h in bio.get("teamHistory") or []:
        rows.append(
            {
                "team_id": str(h.get("id") or ""),
                "team_name": str(h.get("displayName") or ""),
                "seasons": str(h.get("seasons") or ""),
                "season_count": str(h.get("seasonCount") or ""),
                "is_active": bool(h.get("isActive", False)),
            }
        )
    return rows


def is_portal_addition(
    history: Sequence[Mapping[str, str]], *, current_espn_id: str
) -> bool:
    """True when athlete has a prior school distinct from the current roster team."""
    if not history:
        return False
    others = [
        h
        for h in history
        if h.get("team_id") and h.get("team_id") != str(current_espn_id)
    ]
    if not others:
        return False
    # Active CURRENT-only single-school history is not portal.
    active = [h for h in history if h.get("is_active")]
    if len(history) == 1 and active:
        return False
    return True


def qb_pass_attempts_2025(overview: Mapping[str, Any]) -> Tuple[int, int, int]:
    """Return (attempts_2025, yards_2025, td_2025) from career splits."""
    stats = overview.get("statistics") or {}
    names = list(stats.get("names") or [])
    splits = list(stats.get("splits") or [])
    if not names or not splits:
        return 0, 0, 0
    try:
        att_i = names.index("passingAttempts")
    except ValueError:
        att_i = 1 if len(names) > 1 else -1
    try:
        yds_i = names.index("passingYards")
    except ValueError:
        yds_i = 3 if len(names) > 3 else -1
    try:
        td_i = names.index("passingTouchdowns")
    except ValueError:
        td_i = 5 if len(names) > 5 else -1
    for split in splits:
        if str(split.get("displayName") or "") != "2025":
            continue
        vals = list(split.get("stats") or [])
        att = _parse_int(vals[att_i]) if att_i >= 0 and att_i < len(vals) else 0
        yds = _parse_int(vals[yds_i]) if yds_i >= 0 and yds_i < len(vals) else 0
        td = _parse_int(vals[td_i]) if td_i >= 0 and td_i < len(vals) else 0
        return att, yds, td
    return 0, 0, 0


def classify_qb(
    *,
    experience_abbr: str,
    experience_years: int,
    pass_attempts_2025: int,
    is_portal: bool,
    qb_room_size: int,
    competing_with_attempts: int,
) -> Tuple[str, int, str]:
    """Return (qb_class, experience_starts_proxy, notes)."""
    starts_proxy = max(0, int(round(pass_attempts_2025 / 30.0)))
    if experience_abbr == "FR" and experience_years <= 1 and pass_attempts_2025 < 15:
        return "true_freshman", 0, "true freshman / no meaningful 2025 attempts"
    if is_portal and pass_attempts_2025 >= 50:
        return "portal", starts_proxy, "portal addition with prior production"
    if is_portal and pass_attempts_2025 < 50 and experience_years >= 2:
        # Portal depth piece — room may still be open.
        if competing_with_attempts >= 80 or qb_room_size >= 4:
            return "open_competition", starts_proxy, "portal body in unsettled room"
        return "portal", starts_proxy, "portal addition"
    if pass_attempts_2025 >= 120:
        return "incumbent", max(starts_proxy, 4), "returning production starter"
    if competing_with_attempts >= 40 and pass_attempts_2025 < 120:
        return "open_competition", starts_proxy, "split / unsettled QB room"
    if experience_years >= 2 and pass_attempts_2025 >= 20:
        return "incumbent", starts_proxy, "returning depth with some 2025 work"
    if experience_abbr == "FR":
        return "true_freshman", 0, "freshman listed without prior attempts"
    return "open_competition", starts_proxy, "insufficient starter signal"


def talent_from_qb_stats(attempts: int, yards: int, tds: int, *, is_portal: bool) -> float:
    """Approximate QB talent prior from prior-season counting stats.

    Attempt term (Phase 1D): ``min(22, attempts/22)`` — saturates at 484
    attempts with a 22-pt cap. The prior ``min(28, attempts/18)`` let G5
    volume (e.g. 430 att) print talent 80+ alongside P4 elites.
    """
    if attempts <= 0:
        return 48.0 if not is_portal else 52.0
    ypa = yards / max(attempts, 1)
    base = (
        42.0
        + min(22.0, attempts / 22.0)
        + min(12.0, ypa * 1.1)
        + min(10.0, tds * 0.35)
    )
    if is_portal:
        base += 2.0
    return _clamp(base, 35.0, 96.0)


# Phase 1E — low-sample attempts. Below N, three throws must not print ~50.
# MICH (82) sits at/above N and stays on the stats path.
QB_TALENT_LOWSAMPLE_ATTEMPTS = 80


def resolve_qb_talent(
    attempts: int,
    yards: int,
    tds: int,
    *,
    is_portal: bool,
    recruiting_class_score: float,
) -> float:
    """Stats talent, blended to packaged recruiting when attempts are thin.

    ``w = sqrt(att/N)`` — continuous; ``w(0)=0`` (all fallback), ``w(N)=1``
    (all stats). Linear ``att/N`` reordered top-7 by over-lifting blue-blood
    low samples (ALA/UGA); sqrt tightens the pull while still raising STAN.
    Fallback field: ``roster.recruiting_class_score`` (already packaged).
    """
    stats = talent_from_qb_stats(
        int(attempts), int(yards), int(tds), is_portal=bool(is_portal)
    )
    att = int(attempts or 0)
    if att >= QB_TALENT_LOWSAMPLE_ATTEMPTS:
        return stats
    fallback = _clamp(float(recruiting_class_score))
    w = math.sqrt(att / float(QB_TALENT_LOWSAMPLE_ATTEMPTS)) if att > 0 else 0.0
    return _clamp((1.0 - w) * fallback + w * stats)


def experience_index_from_roster(roster: Sequence[Mapping[str, Any]]) -> float:
    if not roster:
        return 50.0
    weights = []
    for row in roster:
        ab = str(row.get("experience_abbr") or "")
        weights.append(CLASS_WEIGHT.get(ab, 0.5))
    return _clamp(100.0 * (sum(weights) / len(weights)))


def returning_shares_from_roster(roster: Sequence[Mapping[str, Any]]) -> Tuple[float, float]:
    """Class-year proxy for returning snap/start shares (honestly approximate)."""
    if not roster:
        return 0.45, 0.48
    non_fr = [r for r in roster if str(r.get("experience_abbr") or "") not in ("", "FR")]
    snap = _clamp01(len(non_fr) / max(len(roster), 1))
    # Starters skew slightly stickier / more experienced than snap share.
    upper = [
        r
        for r in roster
        if str(r.get("experience_abbr") or "") in ("JR", "SR", "GR")
    ]
    start = _clamp01(0.55 * snap + 0.45 * (len(upper) / max(len(roster), 1)))
    return snap, start


def unit_roster_slice(
    roster: Sequence[Mapping[str, Any]], unit: str
) -> List[Mapping[str, Any]]:
    allowed = UNIT_POS[unit]
    return [r for r in roster if str(r.get("position") or "") in allowed]


def depth_sort_key(row: Mapping[str, Any]) -> Tuple[float, float, str]:
    """Higher production / experience first."""
    att = float(row.get("pass_attempts_2025") or 0)
    years = float(row.get("experience_years") or 0)
    # Prefer production, then experience, then name for stability.
    return (-att, -years, str(row.get("player_name") or ""))


def build_depth_chart(enriched: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    by_pos: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in enriched:
        pos = str(row.get("position") or "")
        if not pos:
            continue
        by_pos[pos].append(row)
    out: List[Dict[str, Any]] = []
    for pos, rows in sorted(by_pos.items()):
        ordered = sorted(rows, key=depth_sort_key)
        for i, row in enumerate(ordered[:4], start=1):
            out.append(
                {
                    "position": pos,
                    "depth_order": i,
                    "player_id": row.get("player_id"),
                    "player_name": row.get("player_name"),
                    "experience_abbr": row.get("experience_abbr"),
                    "experience_years": row.get("experience_years"),
                    "pass_attempts_2025": row.get("pass_attempts_2025", 0),
                    "is_portal": bool(row.get("is_portal")),
                    "depth_slot": {1: "starter", 2: "backup", 3: "rotation"}.get(
                        i, "depth"
                    ),
                    "role_confidence": 0.72 if i == 1 else (0.55 if i == 2 else 0.4),
                }
            )
    return out


def portal_values(
    enriched: Sequence[Mapping[str, Any]],
) -> Tuple[float, float, List[Dict[str, Any]], List[Dict[str, Any]]]:
    portal_in = [r for r in enriched if r.get("is_portal")]
    # Outflow is not directly observable from current roster alone.
    # Approximate from FR+portal churn pressure (documented gap).
    fr = [r for r in enriched if str(r.get("experience_abbr") or "") == "FR"]
    portal_in_value = _clamp(
        38.0
        + 4.5 * len(portal_in)
        + 2.0 * sum(1 for r in portal_in if r.get("position") == "QB")
        + 1.2 * sum(1 for r in portal_in if r.get("position") in UNIT_POS["skill"])
        + 1.0 * sum(1 for r in portal_in if r.get("position") in UNIT_POS["ol"])
        + 1.0
        * sum(1 for r in portal_in if r.get("position") in UNIT_POS["front_seven"])
    )
    portal_out_value = _clamp(40.0 + 0.25 * len(fr) + 1.5 * max(0, 6 - len(portal_in)))
    in_rows = [
        {
            "player_id": r.get("player_id"),
            "player_name": r.get("player_name"),
            "position": r.get("position"),
            "from_teams": r.get("prior_teams") or [],
        }
        for r in portal_in
    ]
    return portal_in_value, portal_out_value, in_rows, []


def blend_roster_metrics(
    *,
    recruiting: float,
    espn_returning: float,
    espn_portal_in: float,
    espn_portal_out: float,
    espn_experience: float,
) -> Dict[str, float]:
    """Blend ESPN class/portal proxies with recruiting-informed baselines.

    Pure class-year returning proxies flatten FBS talent hierarchy (mid-majors
    look like blue bloods). Keep ESPN movement, but anchor levels to retained
    recruiting capital so roster_strength / unit talent stay credible.
    """
    ret_base = _clamp(32.0 + 0.38 * recruiting)
    pin_base = _clamp(28.0 + 0.42 * recruiting)
    pout_base = _clamp(55.0 - 0.12 * recruiting)
    returning = _clamp(0.40 * espn_returning + 0.60 * ret_base)
    portal_in = _clamp(0.45 * espn_portal_in + 0.55 * pin_base)
    portal_out = _clamp(0.40 * espn_portal_out + 0.60 * pout_base)
    experience = _clamp(0.55 * espn_experience + 0.45 * (30.0 + 0.45 * recruiting))
    snap = _clamp01(returning / 100.0)
    start = _clamp01(min(1.0, snap + 0.03))
    return {
        "returning_production": returning,
        "returning_snap_share": snap,
        "returning_start_share": start,
        "portal_in_value": portal_in,
        "portal_out_value": portal_out,
        "experience_index": experience,
    }


def unit_grades_from_roster(
    roster: Sequence[Mapping[str, Any]],
    *,
    recruiting: float,
    portal_in_value: float,
    experience_index: float,
    returning_production: float,
) -> Dict[str, Any]:
    components: Dict[str, Any] = {}
    headlines: Dict[str, float] = {}
    for unit in ("ol", "skill", "front_seven", "secondary"):
        rows = unit_roster_slice(roster, unit)
        if rows:
            exp = _clamp(
                0.50 * experience_index_from_roster(rows) + 0.50 * experience_index
            )
            portal_share = sum(1 for r in rows if r.get("is_portal")) / max(len(rows), 1)
        else:
            exp = experience_index
            portal_share = 0.0
        # Recruiting dominates talent; ESPN experience/portal modulate.
        talent = _clamp(
            0.62 * recruiting
            + 0.22 * exp
            + 0.16 * returning_production
            + 4.0 * portal_share
        )
        portal_impact = _clamp(
            0.45 * portal_in_value + 0.35 * recruiting + 0.20 * exp
        )
        grade = _clamp(0.50 * talent + 0.30 * exp + 0.20 * portal_impact)
        components[unit] = {
            "talent": round(talent, 2),
            "experience": round(exp, 2),
            "portal_impact": round(portal_impact, 2),
        }
        headlines[unit] = round(grade, 2)
    return {
        **headlines,
        "special_teams": round(_clamp(0.45 * experience_index + 0.55 * recruiting), 2),
        "components": components,
        "fidelity": "approximate",
        "source": ROSTER_SOURCE,
        "notes": (
            "unit talent anchored on retained recruiting prior + ESPN roster "
            "experience/portal composition; not SP+/PFF"
        ),
    }


def enrich_team(
    *,
    team_code: str,
    espn_ab: str,
    espn_meta: Mapping[str, str],
    prior_payload: Mapping[str, Any],
    sleep_s: float,
    enrich_portal_sample: int,
) -> Dict[str, Any]:
    espn_id = str(espn_meta["id"])
    roster = fetch_roster(espn_id)
    time.sleep(sleep_s)

    # Enrich QBs fully; sample experienced non-QBs for portal detection.
    qbs = [r for r in roster if r.get("position") == "QB"]
    non_qb = [r for r in roster if r.get("position") != "QB"]
    non_qb_sorted = sorted(
        non_qb, key=lambda r: (-int(r.get("experience_years") or 0), r.get("player_name") or "")
    )
    sample = non_qb_sorted[: max(0, enrich_portal_sample)]

    enriched: List[Dict[str, Any]] = []
    portal_checked_ids = {r["player_id"] for r in qbs + sample if r.get("player_id")}

    for row in roster:
        e = dict(row)
        e["pass_attempts_2025"] = 0
        e["pass_yards_2025"] = 0
        e["pass_td_2025"] = 0
        e["is_portal"] = False
        e["prior_teams"] = []
        e["team_history"] = []
        if row.get("player_id") in portal_checked_ids:
            bio = fetch_bio(str(row["player_id"]))
            time.sleep(sleep_s)
            hist = team_history_rows(bio)
            e["team_history"] = hist
            e["is_portal"] = is_portal_addition(hist, current_espn_id=espn_id)
            e["prior_teams"] = [
                h["team_name"]
                for h in hist
                if h.get("team_id") and h.get("team_id") != espn_id
            ]
            if row.get("position") == "QB":
                ov = fetch_overview(str(row["player_id"]))
                time.sleep(sleep_s)
                att, yds, td = qb_pass_attempts_2025(ov)
                e["pass_attempts_2025"] = att
                e["pass_yards_2025"] = yds
                e["pass_td_2025"] = td
        enriched.append(e)

    depth = build_depth_chart(enriched)
    qb_rows = [r for r in enriched if r.get("position") == "QB"]
    qb_rows_sorted = sorted(qb_rows, key=depth_sort_key)
    starter = qb_rows_sorted[0] if qb_rows_sorted else None
    competing_attempts = 0
    if len(qb_rows_sorted) > 1:
        competing_attempts = int(qb_rows_sorted[1].get("pass_attempts_2025") or 0)

    prior_roster = dict(prior_payload.get("roster") or {})
    prior_qb = dict(prior_payload.get("qb") or {})
    prior_groups = dict(prior_payload.get("position_groups") or {})
    recruiting = float(
        prior_roster.get(
            "recruiting_class_score",
            prior_roster.get("recruiting_capital", 55.0),
        )
    )

    snap_raw, start_raw = returning_shares_from_roster(enriched)
    # Boost returning shares slightly when QB1 has real 2025 attempts.
    if starter and int(starter.get("pass_attempts_2025") or 0) >= 100:
        snap_raw = _clamp01(snap_raw + 0.04)
        start_raw = _clamp01(start_raw + 0.06)
    espn_returning = _clamp(100.0 * (0.65 * snap_raw + 0.35 * start_raw))
    espn_experience = experience_index_from_roster(enriched)
    espn_portal_in, espn_portal_out, portal_in_rows, portal_out_rows = portal_values(
        enriched
    )
    blended = blend_roster_metrics(
        recruiting=recruiting,
        espn_returning=espn_returning,
        espn_portal_in=espn_portal_in,
        espn_portal_out=espn_portal_out,
        espn_experience=espn_experience,
    )
    returning_production = blended["returning_production"]
    experience_index = blended["experience_index"]
    portal_in_value = blended["portal_in_value"]
    portal_out_value = blended["portal_out_value"]
    snap = blended["returning_snap_share"]
    start = blended["returning_start_share"]

    if starter:
        qb_class, starts_proxy, qb_notes = classify_qb(
            experience_abbr=str(starter.get("experience_abbr") or ""),
            experience_years=int(starter.get("experience_years") or 0),
            pass_attempts_2025=int(starter.get("pass_attempts_2025") or 0),
            is_portal=bool(starter.get("is_portal")),
            qb_room_size=len(qb_rows),
            competing_with_attempts=competing_attempts,
        )
        qb_talent = resolve_qb_talent(
            int(starter.get("pass_attempts_2025") or 0),
            int(starter.get("pass_yards_2025") or 0),
            int(starter.get("pass_td_2025") or 0),
            is_portal=bool(starter.get("is_portal")),
            recruiting_class_score=float(recruiting),
        )
        # Retain prior OL/weapons support if present (unit grades overwrite later).
        ol_support = float(prior_qb.get("ol_support", prior_groups.get("ol", 55)))
        weapons = float(prior_qb.get("weapons_support", prior_groups.get("skill", 55)))
        qb_block = {
            "qb_class": qb_class,
            "starter_name": starter.get("player_name") or "",
            "starter_key": str(starter.get("player_id") or ""),
            "qb_name": starter.get("player_name") or "",
            "experience_starts": starts_proxy,
            "qb_talent": round(qb_talent, 2),
            "ol_support": ol_support,
            "weapons_support": weapons,
            "is_portal": bool(starter.get("is_portal")),
            "is_true_freshman": qb_class == "true_freshman",
            "open_competition": qb_class == "open_competition",
            "pass_attempts_2025": int(starter.get("pass_attempts_2025") or 0),
            "pass_yards_2025": int(starter.get("pass_yards_2025") or 0),
            "fidelity": "approximate",
            "source": ROSTER_SOURCE,
            "identity_fidelity": "real",
            "notes": (
                f"ESPN 2026 roster QB1 by 2025 attempts/experience; {qb_notes}"
            ),
        }
    else:
        qb_block = {
            "qb_class": "unknown",
            "starter_name": "",
            "experience_starts": 0,
            "qb_talent": 50.0,
            "fidelity": "placeholder",
            "source": ROSTER_SOURCE,
            "notes": "no QB on ESPN 2026 roster",
        }

    groups = unit_grades_from_roster(
        enriched,
        recruiting=recruiting,
        portal_in_value=portal_in_value,
        experience_index=experience_index,
        returning_production=returning_production,
    )
    # Feed QB supporting cast from derived unit grades.
    if starter:
        qb_block["ol_support"] = groups["ol"]
        qb_block["weapons_support"] = groups["skill"]

    players = []
    for row in depth:
        if row["position"] in {"QB", "RB", "WR", "TE"} and row["depth_order"] <= 2:
            players.append(
                {
                    "player_name": row["player_name"],
                    "player_id": row["player_id"],
                    "position": row["position"],
                    "usage_share": 0.95
                    if row["position"] == "QB" and row["depth_order"] == 1
                    else max(0.08, 0.28 - 0.06 * (row["depth_order"] - 1)),
                    "talent": qb_block.get("qb_talent", 55)
                    if row["position"] == "QB"
                    else round(0.55 * recruiting + 0.45 * experience_index, 1),
                    "is_portal": row.get("is_portal"),
                    "source": ROSTER_SOURCE,
                }
            )

    roster_block = {
        "returning_snap_share": round(snap, 4),
        "returning_start_share": round(start, 4),
        "returning_production": round(returning_production, 2),
        "portal_in_value": round(portal_in_value, 2),
        "portal_out_value": round(portal_out_value, 2),
        "portal_in_score": round(portal_in_value, 2),
        "portal_out_score": round(portal_out_value, 2),
        "recruiting_class_score": round(recruiting, 2),
        "recruiting_capital": round(recruiting, 2),
        "experience_index": round(experience_index, 2),
        "fidelity": "approximate",
        "source": ROSTER_SOURCE,
        "field_provenance": "espn_2026_roster_derived",
        "returning_source": RETURNING_SOURCE,
        "portal_source": PORTAL_SOURCE,
        "depth_source": DEPTH_SOURCE,
        "recruiting_source": RECRUITING_SOURCE_PRIOR,
        "notes": (
            "ESPN 2026 roster identities + QB/portal-in sample. Returning/"
            "portal levels blended with recruiting-informed baselines (not "
            "measured SNAP%). Portal-out approximate. Recruiting retained "
            "from curated prior until CFBD overlay."
        ),
    }

    return {
        "team": team_code,
        "espn_abbreviation": espn_ab,
        "espn_team_id": espn_id,
        "espn_team_name": espn_meta.get("name"),
        "roster_source": ROSTER_SOURCE,
        "depth_source": DEPTH_SOURCE,
        "portal_source": PORTAL_SOURCE,
        "returning_source": RETURNING_SOURCE,
        "recruiting_source": RECRUITING_SOURCE_PRIOR,
        "athlete_count": len(enriched),
        "qb_count": len(qb_rows),
        "portal_in_count": len(portal_in_rows),
        "portal_checked_count": len(portal_checked_ids),
        "depth": depth,
        "portal_in": portal_in_rows,
        "portal_out": portal_out_rows,
        "roster": roster_block,
        "qb": qb_block,
        "position_groups": groups,
        "players": players,
        "fidelity": "approximate",
    }


def optional_cfbd_overlay(teams: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    key = (os.environ.get("CFBD_API_KEY") or os.environ.get("BEARER_TOKEN") or "").strip()
    meta = {"enabled": False, "reason": "CFBD_API_KEY not set"}
    if not key:
        return meta
    headers = {
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
    }

    def cfbd_get(path: str, params: Dict[str, Any]) -> Any:
        qs = urllib.parse.urlencode(params)
        url = f"https://api.collegefootballdata.com{path}?{qs}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.load(resp)

    try:
        returning = cfbd_get("/player/returning", {"year": 2026})
        portal = cfbd_get("/player/portal", {"year": 2026})
        recruiting = cfbd_get("/recruiting/teams", {"year": 2026})
    except Exception as exc:  # noqa: BLE001
        return {"enabled": False, "reason": f"cfbd_fetch_failed: {exc}"[:240]}

    # Index CFBD rows by lowercase team name for soft join via ESPN display name.
    ret_by_name: Dict[str, Any] = {}
    for row in returning or []:
        name = str(row.get("team") or "").strip().lower()
        if name:
            ret_by_name[name] = row
    rec_by_name: Dict[str, Any] = {}
    for row in recruiting or []:
        name = str(row.get("team") or "").strip().lower()
        if name:
            rec_by_name[name] = row

    portal_in_by_dest: Dict[str, List[Any]] = defaultdict(list)
    portal_out_by_origin: Dict[str, List[Any]] = defaultdict(list)
    for row in portal or []:
        dest = str(row.get("destination") or "").strip().lower()
        origin = str(row.get("origin") or "").strip().lower()
        if dest:
            portal_in_by_dest[dest].append(row)
        if origin:
            portal_out_by_origin[origin].append(row)

    applied = 0
    for _code, payload in teams.items():
        name = str(payload.get("espn_team_name") or "").lower()
        # strip mascot-ish trailing token loosely
        name_root = re.sub(r"\s+(bulldogs|tigers|wildcats|crimson tide|longhorns|buckeyes|seminoles|buffaloes|nittany lions)$", "", name)
        ret = ret_by_name.get(name) or ret_by_name.get(name_root)
        rec = rec_by_name.get(name) or rec_by_name.get(name_root)
        pin = portal_in_by_dest.get(name) or portal_in_by_dest.get(name_root) or []
        pout = portal_out_by_origin.get(name) or portal_out_by_origin.get(name_root) or []
        roster = payload.setdefault("roster", {})
        if ret:
            # CFBD returning production fields vary; prefer percent shares when present.
            pct = ret.get("passingUsage") or ret.get("percentPPA") or ret.get("totalPPA")
            if ret.get("usage") is not None:
                snap = _clamp01(float(ret.get("usage")))
                roster["returning_snap_share"] = round(snap, 4)
                roster["returning_start_share"] = round(_clamp01(snap + 0.03), 4)
                roster["returning_production"] = round(100.0 * snap, 2)
                roster["returning_source"] = "cfbd_player_returning"
            elif pct is not None:
                snap = _clamp01(float(pct) if float(pct) <= 1.5 else float(pct) / 100.0)
                roster["returning_snap_share"] = round(snap, 4)
                roster["returning_start_share"] = round(_clamp01(snap + 0.03), 4)
                roster["returning_production"] = round(100.0 * snap, 2)
                roster["returning_source"] = "cfbd_player_returning"
            applied += 1
        if pin or pout:
            roster["portal_in_value"] = round(
                _clamp(40.0 + 3.0 * len(pin) + 1.5 * sum(1 for r in pin if str(r.get("position") or "").upper() == "QB")),
                2,
            )
            roster["portal_out_value"] = round(_clamp(40.0 + 2.5 * len(pout)), 2)
            roster["portal_in_score"] = roster["portal_in_value"]
            roster["portal_out_score"] = roster["portal_out_value"]
            roster["portal_source"] = "cfbd_player_portal"
            payload["portal_source"] = "cfbd_player_portal"
            payload["portal_in"] = [
                {
                    "player_name": r.get("name") or r.get("firstName"),
                    "position": r.get("position"),
                    "from_teams": [r.get("origin")],
                }
                for r in pin[:25]
            ]
            applied += 1
        if rec and rec.get("points") is not None:
            # Normalize CFBD points roughly onto 0–100 via rank-ish squash later; here keep relative.
            pts = float(rec["points"])
            roster["recruiting_class_score"] = round(_clamp(35.0 + pts / 8.0), 2)
            roster["recruiting_capital"] = roster["recruiting_class_score"]
            roster["recruiting_source"] = RECRUITING_SOURCE_CFBD
            payload["recruiting_source"] = RECRUITING_SOURCE_CFBD
            applied += 1

    meta = {
        "enabled": True,
        "returning_rows": len(returning or []),
        "portal_rows": len(portal or []),
        "recruiting_rows": len(recruiting or []),
        "teams_touched": applied,
    }
    return meta


def merge_into_priors(
    priors: Dict[str, Any],
    team_payloads: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    out = json.loads(json.dumps(priors))  # deep copy
    out["as_of"] = date.today().isoformat()
    out["fidelity"] = "approximate"
    out["scope"] = "FBS priors with ESPN 2026 real-roster overlay"
    notes = list(out.get("notes") or [])
    notes = [
        n
        for n in notes
        if "Portal/recruiting/returning production live feeds remain gaps" not in n
        and "Named QBs are illustrative" not in n
    ]
    notes.extend(
        [
            "v0.6: roster/QB/position_groups overlaid from ESPN 2026 rosters + athlete teamHistory/career splits.",
            "Returning snap/start shares remain approximate class-year proxies unless CFBD returning overlay applied.",
            "Depth order is production/experience heuristic — official camp depth charts often unpublished preseason.",
            "Portal-out is incomplete without a full departure feed; portal-in from teamHistory sample (+ optional CFBD).",
            "home_field and coaching blocks retained from curated priors.",
        ]
    )
    out["notes"] = notes
    teams = out.setdefault("teams", {})
    for code, payload in team_payloads.items():
        row = teams.setdefault(code, {})
        row["roster"] = dict(payload["roster"])
        row["qb"] = dict(payload["qb"])
        row["position_groups"] = dict(payload["position_groups"])
        if payload.get("players"):
            row["players"] = list(payload["players"])
        # Preserve home_field / coaching if present.
    out["real_roster"] = {
        "enabled": True,
        "roster_source": ROSTER_SOURCE,
        "depth_source": DEPTH_SOURCE,
        "portal_source": PORTAL_SOURCE,
        "snapshot": str(SNAPSHOT_PATH.name),
        "team_count": len(team_payloads),
    }
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit-teams", type=int, default=0, help="Optional cap for smoke runs")
    parser.add_argument("--sleep", type=float, default=0.08, help="Delay between ESPN calls")
    parser.add_argument(
        "--portal-sample",
        type=int,
        default=12,
        help="Non-QB athletes per team to check for portal teamHistory",
    )
    parser.add_argument("--skip-cfbd", action="store_true")
    parser.add_argument("--snapshot-out", type=Path, default=SNAPSHOT_PATH)
    parser.add_argument("--priors-out", type=Path, default=PRIORS_PATH)
    args = parser.parse_args(list(argv) if argv is not None else None)

    if not PRIORS_PATH.is_file():
        raise SystemExit(f"Missing priors: {PRIORS_PATH}")
    priors = json.loads(PRIORS_PATH.read_text(encoding="utf-8"))
    team_codes = sorted(priors.get("teams") or {})
    if args.limit_teams and args.limit_teams > 0:
        # Prefer familiar codes first for smoke runs.
        preferred = [
            "UGA",
            "ALA",
            "TEX",
            "OSU",
            "FSU",
            "COLO",
            "PSU",
            "LSU",
            "BALL",
            "ORE",
            "MICH",
            "OU",
        ]
        ordered = [c for c in preferred if c in team_codes] + [
            c for c in team_codes if c not in preferred
        ]
        team_codes = ordered[: args.limit_teams]

    print(f"Loading ESPN FBS team list…", file=sys.stderr)
    espn = load_espn_fbs_teams()
    print(f"ESPN FBS teams: {len(espn)}", file=sys.stderr)
    # Sanity: OSU must resolve to Buckeyes, not Newark.
    osu = espn.get("OSU") or {}
    if "newark" in str(osu.get("name") or "").lower():
        raise SystemExit(f"OSU abbreviation collided with satellite team: {osu}")

    cache_path = RAW_CACHE_DIR / "real_roster_team_cache.json"
    payloads: Dict[str, Dict[str, Any]] = {}
    if cache_path.is_file():
        try:
            payloads = json.loads(cache_path.read_text(encoding="utf-8"))
            if not isinstance(payloads, dict):
                payloads = {}
            print(f"Resuming with {len(payloads)} cached teams from {cache_path}", file=sys.stderr)
        except Exception:
            payloads = {}

    unmatched: List[str] = []
    for i, code in enumerate(team_codes, start=1):
        if code in payloads and int(payloads[code].get("athlete_count") or 0) > 0:
            # Skip already-cached successful rows (allows resume after interrupt).
            if payloads[code].get("espn_team_name") and "newark" not in str(
                payloads[code].get("espn_team_name") or ""
            ).lower():
                print(f"[{i}/{len(team_codes)}] {code}: cached", file=sys.stderr)
                continue
        resolved = resolve_espn_team(code, espn)
        if not resolved:
            unmatched.append(code)
            print(f"[{i}/{len(team_codes)}] {code}: NO ESPN MATCH", file=sys.stderr)
            continue
        espn_ab, meta = resolved
        print(
            f"[{i}/{len(team_codes)}] {code} ← ESPN {espn_ab} ({meta['name']})",
            file=sys.stderr,
        )
        try:
            payloads[code] = enrich_team(
                team_code=code,
                espn_ab=espn_ab,
                espn_meta=meta,
                prior_payload=priors["teams"].get(code) or {},
                sleep_s=args.sleep,
                enrich_portal_sample=args.portal_sample,
            )
            RAW_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(payloads), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            print(f"  ERROR {code}: {exc}", file=sys.stderr)
            unmatched.append(code)

    cfbd_meta: Dict[str, Any] = {"enabled": False, "reason": "skipped"}
    if not args.skip_cfbd:
        cfbd_meta = optional_cfbd_overlay(payloads)

    as_of = date.today().isoformat()
    snapshot = {
        "season": 2026,
        "as_of": as_of,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "roster_source": ROSTER_SOURCE,
        "depth_source": DEPTH_SOURCE,
        "portal_source": PORTAL_SOURCE,
        "returning_source": RETURNING_SOURCE,
        "recruiting_source": RECRUITING_SOURCE_PRIOR,
        "cfbd": cfbd_meta,
        "team_count": len(payloads),
        "unmatched_team_codes": unmatched,
        "coverage": {
            "teams_with_roster": sum(1 for p in payloads.values() if p.get("athlete_count", 0) > 0),
            "teams_with_named_qb": sum(
                1 for p in payloads.values() if (p.get("qb") or {}).get("starter_name")
            ),
            "teams_with_portal_in": sum(1 for p in payloads.values() if p.get("portal_in_count", 0) > 0),
            "total_athletes": sum(int(p.get("athlete_count") or 0) for p in payloads.values()),
            "total_depth_rows": sum(len(p.get("depth") or []) for p in payloads.values()),
        },
        "notes": [
            "ESPN 2026 preseason rosters are the authoritative identity feed in this snapshot.",
            "Depth order is heuristic (2025 pass attempts for QBs, experience otherwise) — camp battles unresolved.",
            "Returning production uses class-year proxies (+ QB attempt boost) unless CFBD returning overlay applied.",
            "Portal-in from teamHistory on QBs + experienced sample; portal-out incomplete without departure feed.",
            "Recruiting capital retained from curated priors unless CFBD recruiting overlay applied.",
        ],
        "teams": payloads,
    }

    args.snapshot_out.parent.mkdir(parents=True, exist_ok=True)
    args.snapshot_out.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")

    # Full merge only when not a tiny smoke limit (or when covering most teams).
    if not args.limit_teams or args.limit_teams >= 100:
        merged = merge_into_priors(priors, payloads)
        # For unmatched codes, leave prior rows but mark weak only if still placeholder.
        args.priors_out.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote priors merge → {args.priors_out}", file=sys.stderr)
    else:
        # Smoke: still merge the limited set so local tests can see deltas.
        merged = merge_into_priors(priors, payloads)
        args.priors_out.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote partial priors merge → {args.priors_out}", file=sys.stderr)

    RAW_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_CACHE_DIR / "package_real_roster_summary.json").write_text(
        json.dumps(
            {
                "as_of": as_of,
                "team_count": len(payloads),
                "unmatched": unmatched,
                "coverage": snapshot["coverage"],
                "cfbd": cfbd_meta,
                "examples": {
                    code: {
                        "qb": (payloads[code].get("qb") or {}).get("starter_name"),
                        "qb_class": (payloads[code].get("qb") or {}).get("qb_class"),
                        "roster_strength_inputs": {
                            "returning_production": payloads[code]["roster"][
                                "returning_production"
                            ],
                            "portal_in_value": payloads[code]["roster"]["portal_in_value"],
                            "experience_index": payloads[code]["roster"]["experience_index"],
                        },
                    }
                    for code in ("UGA", "TEX", "FSU", "COLO", "PSU", "BALL")
                    if code in payloads
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "snapshot": str(args.snapshot_out),
                "priors": str(args.priors_out),
                "team_count": len(payloads),
                "unmatched": len(unmatched),
                "coverage": snapshot["coverage"],
                "cfbd": cfbd_meta,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
