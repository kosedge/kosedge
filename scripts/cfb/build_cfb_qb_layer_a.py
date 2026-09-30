#!/usr/bin/env python3
"""Build CFB QB Layer A (2022–2024) under cfb-qb-feature-v1.

Legal sources only:
  - ESPN core ``seasons/{Y}/teams/{id}/athletes`` (membership)
  - ESPN core ``seasons/{Y-1}/types/2/athletes/{id}/statistics`` (counting stats)
  - Portal = Y vs Y-1 roster-id join
  - Class = first roster/stats appearance (never raw ESPN experience)

Forbidden:
  - site roster / current-club endpoints
  - same-season counting stats as Week-0 talent
  - 2026 recruiting floor, teamHistory, overrides, W1 confirms
  - 2025 labels / 2026 confirmatory books (not read)

Does not change MATCHUP_RESPONSE, QB weights, or production compose.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "services/model-service"))

from src.services.cfb_season_engine.fbs_universe import (  # noqa: E402
    NON_FBS_CODES,
    official_fbs_codes,
)
from src.services.cfb_season_engine.qb_feature_contract import (  # noqa: E402
    FORBIDDEN_ROSTER_SOURCES,
    LOWSAMPLE_ATTEMPTS,
    MISSING_QB_CLASS,
    MISSING_QB_TALENT,
    QB_FEATURE_CONTRACT_VERSION,
    classify_qb,
    depth_sort_key,
    prior_season_for_prediction,
    resolve_qb_talent,
    talent_from_qb_stats,
)
from src.services.cfb_warehouse.identity import (  # noqa: E402
    known_engine_codes,
    resolve_team_code,
)

CACHE_DIR = REPO / "data/cfb/raw/espn_core_layer_a"
OUT_DIR = (
    REPO
    / "services/model-service/src/services/cfb_season_engine/data/cfb_qb_layer_a"
)
OPS_MD = REPO / "data/ops/cfb-qb-layer-a-20260911.md"
OPS_JSON = REPO / "data/ops/cfb-qb-layer-a-20260911.json"

ESPN_CORE = "http://sports.core.api.espn.com/v2/sports/football/leagues/college-football"
UA = {
    "User-Agent": "Mozilla/5.0 (compatible; KosEdgeCFB-LayerA/1.0; +https://www.kosedge.com)",
    "Accept": "application/json",
}
ROSTER_SOURCE = "espn_core_seasons_Y_team_athletes"
STATS_SOURCE = "espn_core_seasons_Ym1_athlete_statistics"
FIRST_STATS_FLOOR = 2017
WORKERS = 16

REASON = {
    "NO_QB_ON_ROSTER": "season-Y core athlete list had no position=QB",
    "EMPTY_ATHLETE_LIST": "season-Y core athlete list empty or fetch failed",
    "STATS_404": "year-scoped prior-season statistics 404 / empty",
    "UNMAPPED_TEAM": "ESPN group-80 team did not resolve to an engine FBS code",
    "RECRUITING_UNAVAILABLE_LAYER_B": "year-Y recruiting not ingested; not 2026 floor",
    "CAST_UNAVAILABLE_LAYER_B": "OL/weapons require recruiting-anchored unit grades",
    "OVERRIDE_UNAVAILABLE": "expert override book is 2026-only",
    "W1_CONFIRM_UNAVAILABLE": "W1 confirm book is 2026-only",
    "EXPERIENCE_RECONSTRUCTED": "first roster/stats appearance; ESPN experience ignored",
    "ESPN_EXPERIENCE_IGNORED": "season-scoped athlete.experience is current class",
    "PORTAL_ROSTER_JOIN": "portal from Y vs Y-1 team-list membership",
    "CLASS_LEFT_CENSORED": "first appearance at stats walk floor; years may be understated",
    "LAYER_A_OK": "named QB1 with legal prior-year stats or documented att=0",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _cache_path(*parts: str) -> Path:
    path = CACHE_DIR.joinpath(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _http_json(url: str, *, retries: int = 6) -> Any:
    last: Optional[Exception] = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=40) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            last = exc
            time.sleep(0.4 * (attempt + 1))
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(0.6 * (attempt + 1))
    # Fail the *row*, not the crawl — resume must survive DNS blips.
    return None


def cached_json(rel: Sequence[str], url: str) -> Any:
    path = _cache_path(*rel)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            path.unlink(missing_ok=True)
    blob = _http_json(url)
    path.write_text(json.dumps(blob), encoding="utf-8")
    return blob


def paged_items(url: str, cache_key: Sequence[str]) -> List[Dict[str, Any]]:
    first = cached_json(cache_key + ("page1.json",), url)
    if not first:
        return []
    items = list(first.get("items") or [])
    pages = int(first.get("pageCount") or 1)
    for page in range(2, pages + 1):
        sep = "&" if "?" in url else "?"
        blob = cached_json(
            cache_key + (f"page{page}.json",), f"{url}{sep}page={page}"
        )
        if blob:
            items.extend(blob.get("items") or [])
    return items


def athlete_id_from_ref(ref: str) -> str:
    # .../seasons/2023/athletes/4918121?lang=...
    core = str(ref).split("athletes/")[-1]
    return core.split("?")[0].strip("/")


def team_id_from_ref(ref: str) -> str:
    core = str(ref).split("teams/")[-1]
    return core.split("?")[0].strip("/")


def load_season_teams(season: int) -> List[Dict[str, Any]]:
    items = paged_items(
        f"{ESPN_CORE}/seasons/{season}/types/2/groups/80/teams?limit=200",
        ("teams", str(season)),
    )
    known = known_engine_codes()
    official = official_fbs_codes(include_transition=False)
    out: List[Dict[str, Any]] = []
    for item in items:
        ref = item.get("$ref") or ""
        tid = team_id_from_ref(ref)
        team = cached_json(
            ("team_obj", str(season), f"{tid}.json"),
            ref or f"{ESPN_CORE}/seasons/{season}/teams/{tid}",
        )
        if not team:
            continue
        abbr = str(team.get("abbreviation") or "").upper()
        name = str(team.get("displayName") or team.get("name") or "")
        code = resolve_team_code(abbr=abbr, name=name, known_codes=known)
        if code in NON_FBS_CODES:
            code = None
        out.append(
            {
                "espn_team_id": str(team.get("id") or tid),
                "espn_abbreviation": abbr,
                "espn_team_name": name,
                "engine_code": code,
                "in_official_2026": bool(code and code in official),
                "season": season,
            }
        )
    return out


def load_team_athlete_ids(season: int, espn_team_id: str) -> List[str]:
    items = paged_items(
        f"{ESPN_CORE}/seasons/{season}/teams/{espn_team_id}/athletes?limit=200",
        ("athlete_list", str(season), str(espn_team_id)),
    )
    ids = []
    for item in items:
        ref = item.get("$ref") or ""
        if ref:
            ids.append(athlete_id_from_ref(ref))
    return ids


def load_athlete(season: int, player_id: str) -> Optional[Dict[str, Any]]:
    # Prefer new cache; fall back to prior diagnostic cache if season-scoped.
    path = _cache_path("athletes", str(season), f"{player_id}.json")
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            path.unlink(missing_ok=True)
    legacy = REPO / "data/cfb/raw/espn_core_athletes" / str(season) / f"{player_id}.json"
    if legacy.exists():
        try:
            blob = json.loads(legacy.read_text(encoding="utf-8"))
            path.write_text(json.dumps(blob), encoding="utf-8")
            return blob
        except json.JSONDecodeError:
            pass
    url = f"{ESPN_CORE}/seasons/{season}/athletes/{player_id}"
    blob = _http_json(url)
    if blob is None:
        return None
    path.write_text(json.dumps(blob), encoding="utf-8")
    return blob


def parse_passing_stats(blob: Optional[Mapping[str, Any]]) -> Optional[Dict[str, int]]:
    if not blob:
        return None
    cats = ((blob.get("splits") or {}).get("categories") or [])
    passing = None
    for cat in cats:
        if str(cat.get("name") or "").lower() in {"passing", "pass"}:
            passing = cat
            break
    if passing is None:
        return {"attempts": 0, "yards": 0, "tds": 0, "present": True}
    stats = {str(s.get("name")): s.get("value") for s in (passing.get("stats") or [])}

    def _i(*keys: str) -> int:
        for k in keys:
            if stats.get(k) is not None:
                try:
                    return int(float(stats[k]))
                except (TypeError, ValueError):
                    continue
        return 0

    return {
        "attempts": _i("passingAttempts", "attempts"),
        "yards": _i("passingYards", "netPassingYards", "yards"),
        "tds": _i("passingTouchdowns", "touchdowns"),
        "present": True,
    }


def load_stats(stats_season: int, player_id: str) -> Optional[Dict[str, int]]:
    path = _cache_path("stats", str(stats_season), f"{player_id}.json")
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            raw = None
        if raw is not None and raw.get("_missing"):
            return None
        if raw is not None:
            return parse_passing_stats(raw)
    url = (
        f"{ESPN_CORE}/seasons/{stats_season}/types/2/athletes/{player_id}/statistics"
    )
    blob = _http_json(url)
    if blob is None:
        path.write_text(json.dumps({"_missing": True}), encoding="utf-8")
        return None
    path.write_text(json.dumps(blob), encoding="utf-8")
    return parse_passing_stats(blob)


def experience_from_first_appearance(
    prediction_season: int, first_season: Optional[int]
) -> Tuple[str, int, str, Optional[str]]:
    if first_season is None or int(first_season) >= int(prediction_season):
        return "FR", 1, "no prior roster or stats; first college season", None
    years = max(1, int(prediction_season) - int(first_season))
    if years <= 1:
        abbr = "FR"
    elif years == 2:
        abbr = "SO"
    elif years == 3:
        abbr = "JR"
    else:
        abbr = "SR"
    left = None
    if int(first_season) <= FIRST_STATS_FLOOR:
        left = "CLASS_LEFT_CENSORED"
    return abbr, years, f"first_college_season={first_season}", left


def first_college_season(
    player_id: str,
    *,
    prediction_season: int,
    roster_years: Mapping[int, Mapping[str, str]],
) -> Tuple[Optional[int], Dict[str, Any]]:
    """Earliest season the player appears on a cached roster or has stats.

    Stats walk is backward from Y-1 to FIRST_STATS_FLOOR. ESPN experience unused.
    """
    roster_first = None
    for year, owners in roster_years.items():
        if player_id in owners and year < prediction_season:
            roster_first = year if roster_first is None else min(roster_first, year)
    stats_years: List[int] = []
    for year in range(prediction_season - 1, FIRST_STATS_FLOOR - 1, -1):
        parsed = load_stats(year, player_id)
        if parsed is not None:
            stats_years.append(year)
    stats_first = min(stats_years) if stats_years else None
    candidates = [x for x in (roster_first, stats_first) if x is not None]
    first = min(candidates) if candidates else None
    return first, {
        "roster_first": roster_first,
        "stats_first": stats_first,
        "stats_years_found": sorted(stats_years),
        "experience_source": "first_appearance_roster_or_stats",
    }


def _percentiles(xs: Sequence[float]) -> Dict[str, float]:
    if not xs:
        return {}
    s = sorted(float(x) for x in xs)
    n = len(s)

    def q(p: float) -> float:
        if n == 1:
            return s[0]
        idx = (n - 1) * p
        lo = int(math.floor(idx))
        hi = int(math.ceil(idx))
        if lo == hi:
            return s[lo]
        w = idx - lo
        return s[lo] * (1 - w) + s[hi] * w

    mean = sum(s) / n
    var = sum((x - mean) ** 2 for x in s) / n
    return {
        "n": n,
        "mean": round(mean, 4),
        "sd": round(math.sqrt(var), 4),
        "p10": round(q(0.10), 4),
        "p25": round(q(0.25), 4),
        "p50": round(q(0.50), 4),
        "p75": round(q(0.75), 4),
        "p90": round(q(0.90), 4),
        "min": round(s[0], 4),
        "max": round(s[-1], 4),
    }


def build_season(
    prediction_season: int,
    *,
    teams_by_season: Mapping[int, Sequence[Mapping[str, Any]]],
    ids_by_season_team: Mapping[Tuple[int, str], Sequence[str]],
    qbs_by_season_team: Mapping[Tuple[int, str], Sequence[Mapping[str, Any]]],
    owner_by_season: Mapping[int, Mapping[str, str]],
) -> Dict[str, Any]:
    prior = prior_season_for_prediction(prediction_season)
    teams = [
        t
        for t in teams_by_season.get(prediction_season, [])
        if t.get("engine_code")
    ]
    # One row per engine code (first ESPN id wins; collisions listed).
    by_code: Dict[str, Mapping[str, Any]] = {}
    collisions: List[str] = []
    for t in teams:
        code = str(t["engine_code"])
        if code in by_code:
            collisions.append(code)
            continue
        by_code[code] = t

    rows: Dict[str, Any] = {}
    misses: List[Dict[str, Any]] = []
    for code, team in sorted(by_code.items()):
        tid = str(team["espn_team_id"])
        qbs = list(qbs_by_season_team.get((prediction_season, tid), []))
        athlete_ids = list(ids_by_season_team.get((prediction_season, tid), []))
        reasons: List[str] = [
            "RECRUITING_UNAVAILABLE_LAYER_B",
            "CAST_UNAVAILABLE_LAYER_B",
            "OVERRIDE_UNAVAILABLE",
            "W1_CONFIRM_UNAVAILABLE",
            "ESPN_EXPERIENCE_IGNORED",
        ]
        if not athlete_ids:
            reasons.append("EMPTY_ATHLETE_LIST")
            misses.append({"team": code, "reasons": list(reasons)})
            rows[code] = _empty_row(team, prediction_season, prior, reasons)
            continue
        if not qbs:
            reasons.append("NO_QB_ON_ROSTER")
            misses.append({"team": code, "reasons": list(reasons)})
            rows[code] = _empty_row(team, prediction_season, prior, reasons)
            continue

        enriched: List[Dict[str, Any]] = []
        for qb in qbs:
            pid = str(qb["player_id"])
            stats = load_stats(prior, pid)
            if stats is None:
                att = yds = td = 0
                stats_avail = "MISSING"
                stats_reason = "STATS_404"
            else:
                att = int(stats["attempts"])
                yds = int(stats["yards"])
                td = int(stats["tds"])
                stats_avail = "RECONSTRUCTABLE"
                stats_reason = None
            prior_owner = (owner_by_season.get(prior) or {}).get(pid)
            is_portal = bool(prior_owner and prior_owner != tid)
            if (not prior_owner) and stats is not None and att > 0:
                # Played last year, not on this team's Y-1 list → portal/transfer.
                is_portal = True
            first, first_meta = first_college_season(
                pid,
                prediction_season=prediction_season,
                roster_years=owner_by_season,
            )
            exp_abbr, exp_years, exp_note, left = experience_from_first_appearance(
                prediction_season, first
            )
            enriched.append(
                {
                    "player_id": pid,
                    "player_name": qb.get("player_name") or "",
                    "pass_attempts_prior": att,
                    "pass_yards_prior": yds,
                    "pass_td_prior": td,
                    "stats_availability": stats_avail,
                    "stats_reason": stats_reason,
                    "is_portal": is_portal,
                    "prior_team_espn_id": prior_owner,
                    "experience_abbr": exp_abbr,
                    "experience_years": exp_years,
                    "experience_note": exp_note,
                    "first_college_season": first,
                    "first_appearance": first_meta,
                    "left_censored": left,
                }
            )

        ordered = sorted(enriched, key=depth_sort_key)
        starter = ordered[0]
        competing = int(ordered[1]["pass_attempts_prior"]) if len(ordered) > 1 else 0
        qb_class, starts_proxy, class_notes = classify_qb(
            experience_abbr=str(starter["experience_abbr"]),
            experience_years=int(starter["experience_years"]),
            pass_attempts_prior=int(starter["pass_attempts_prior"]),
            is_portal=bool(starter["is_portal"]),
            qb_room_size=len(ordered),
            competing_with_attempts=competing,
        )
        talent, talent_avail = resolve_qb_talent(
            int(starter["pass_attempts_prior"]),
            int(starter["pass_yards_prior"]),
            int(starter["pass_td_prior"]),
            is_portal=bool(starter["is_portal"]),
            recruiting_class_score=None,
            recruiting_availability="MISSING",
        )
        if starter["stats_availability"] == "MISSING" and int(starter["pass_attempts_prior"]) == 0:
            reasons.append("STATS_404")
        if starter.get("left_censored"):
            reasons.append("CLASS_LEFT_CENSORED")
        reasons.append("PORTAL_ROSTER_JOIN")
        reasons.append("EXPERIENCE_RECONSTRUCTED")
        layer_a_ok = bool(starter.get("player_id"))
        if layer_a_ok:
            reasons.append("LAYER_A_OK")

        rows[code] = {
            "team": code,
            "espn_team_id": tid,
            "espn_abbreviation": team.get("espn_abbreviation"),
            "espn_team_name": team.get("espn_team_name"),
            "prediction_season": prediction_season,
            "prior_season": prior,
            "week0_freeze": True,
            "qb_feature_contract_version": QB_FEATURE_CONTRACT_VERSION,
            "qb_class": qb_class,
            "qb_talent": round(float(talent), 2),
            "ol_support": None,
            "weapons_support": None,
            "supporting_cast": None,
            "starter_name": starter["player_name"],
            "starter_key": starter["player_id"],
            "is_portal": bool(starter["is_portal"]),
            "experience_abbr": starter["experience_abbr"],
            "experience_years": starter["experience_years"],
            "experience_starts": starts_proxy,
            "pass_attempts_prior": int(starter["pass_attempts_prior"]),
            "pass_yards_prior": int(starter["pass_yards_prior"]),
            "pass_td_prior": int(starter["pass_td_prior"]),
            "recruiting_class_score": None,
            "established": int(starter["pass_attempts_prior"]) >= LOWSAMPLE_ATTEMPTS,
            "talent_availability": talent_avail,
            "availability": {
                "roster_membership": "RECONSTRUCTABLE",
                "prior_year_stats": starter["stats_availability"],
                "portal": "RECONSTRUCTABLE",
                "class": "RECONSTRUCTABLE",
                "recruiting": "MISSING",
                "ol_support": "MISSING",
                "weapons_support": "MISSING",
                "expert_override": "MISSING",
                "w1_confirm": "MISSING",
            },
            "reason_codes": reasons,
            "qb_room": [
                {
                    "player_id": r["player_id"],
                    "player_name": r["player_name"],
                    "pass_attempts_prior": r["pass_attempts_prior"],
                    "is_portal": r["is_portal"],
                    "experience_abbr": r["experience_abbr"],
                    "experience_years": r["experience_years"],
                }
                for r in ordered
            ],
            "provenance": {
                "roster_source": ROSTER_SOURCE,
                "stats_source": STATS_SOURCE,
                "stats_season": prior,
                "prediction_season": prediction_season,
                "temporal_cutoff": "prior_season_completed_totals_only",
                "starter_rule": "max prior-season attempts, then experience years, then name",
                "starter_selection": class_notes,
                "portal_rule": "Y vs Y-1 roster-id join (or Y-1 attempts not on this Y-1 list)",
                "prior_team_espn_id": starter.get("prior_team_espn_id"),
                "class_reconstruction": starter.get("experience_note"),
                "first_college_season": starter.get("first_college_season"),
                "first_appearance": starter.get("first_appearance"),
                "espn_experience_used": False,
                "recruiting_used": False,
                "same_season_stats_used": False,
                "site_roster_used": False,
                "team_history_used": False,
                "override_used": False,
                "w1_confirm_used": False,
                "qb_feature_contract_version": QB_FEATURE_CONTRACT_VERSION,
            },
        }
        if not layer_a_ok:
            misses.append({"team": code, "reasons": reasons})

    denom = sorted(by_code)
    covered = [
        c
        for c in denom
        if rows[c].get("starter_key") and "LAYER_A_OK" in (rows[c].get("reason_codes") or [])
    ]
    talents = [float(rows[c]["qb_talent"]) for c in covered]
    established = [
        float(rows[c]["qb_talent"])
        for c in covered
        if rows[c].get("established")
    ]
    return {
        "qb_feature_contract_version": QB_FEATURE_CONTRACT_VERSION,
        "prediction_season": prediction_season,
        "prior_season": prior,
        "as_of": "week0_freeze",
        "generated_at": _utc(),
        "roster_source": ROSTER_SOURCE,
        "stats_source": STATS_SOURCE,
        "layer": "A",
        "n_mapped_fbs": len(denom),
        "n_layer_a": len(covered),
        "coverage": round(len(covered) / max(len(denom), 1), 4),
        "collisions": collisions,
        "misses": misses,
        "talent_all": _percentiles(talents),
        "talent_established": _percentiles(established),
        "class_counts": dict(Counter(rows[c]["qb_class"] for c in covered)),
        "portal_n": sum(1 for c in covered if rows[c].get("is_portal")),
        "lowsample_n": sum(1 for c in covered if not rows[c].get("established")),
        "teams": rows,
    }


def _empty_row(
    team: Mapping[str, Any],
    prediction_season: int,
    prior: int,
    reasons: Sequence[str],
) -> Dict[str, Any]:
    return {
        "team": team.get("engine_code"),
        "espn_team_id": team.get("espn_team_id"),
        "espn_abbreviation": team.get("espn_abbreviation"),
        "espn_team_name": team.get("espn_team_name"),
        "prediction_season": prediction_season,
        "prior_season": prior,
        "week0_freeze": True,
        "qb_feature_contract_version": QB_FEATURE_CONTRACT_VERSION,
        "qb_class": MISSING_QB_CLASS,
        "qb_talent": MISSING_QB_TALENT,
        "ol_support": None,
        "weapons_support": None,
        "supporting_cast": None,
        "starter_name": "",
        "starter_key": "",
        "is_portal": False,
        "pass_attempts_prior": 0,
        "pass_yards_prior": 0,
        "pass_td_prior": 0,
        "recruiting_class_score": None,
        "established": False,
        "availability": {
            "roster_membership": "MISSING"
            if "EMPTY_ATHLETE_LIST" in reasons
            else "RECONSTRUCTABLE",
            "prior_year_stats": "MISSING",
            "portal": "MISSING",
            "class": "MISSING",
            "recruiting": "MISSING",
            "ol_support": "MISSING",
            "weapons_support": "MISSING",
            "expert_override": "MISSING",
            "w1_confirm": "MISSING",
        },
        "reason_codes": list(reasons),
        "qb_room": [],
        "provenance": {
            "roster_source": ROSTER_SOURCE,
            "stats_source": STATS_SOURCE,
            "stats_season": prior,
            "prediction_season": prediction_season,
            "espn_experience_used": False,
            "recruiting_used": False,
            "same_season_stats_used": False,
            "site_roster_used": False,
            "qb_feature_contract_version": QB_FEATURE_CONTRACT_VERSION,
        },
    }


def resolve_qbs_for_team(
    season: int, espn_team_id: str, player_ids: Sequence[str]
) -> List[Dict[str, Any]]:
    qbs: List[Dict[str, Any]] = []
    for pid in player_ids:
        blob = load_athlete(season, pid)
        if not blob:
            continue
        pos = (blob.get("position") or {}).get("abbreviation")
        if str(pos or "").upper() != "QB":
            continue
        qbs.append(
            {
                "player_id": str(blob.get("id") or pid),
                "player_name": str(blob.get("displayName") or blob.get("fullName") or ""),
            }
        )
    return qbs


def crawl(*, seasons: Sequence[int], workers: int) -> None:
    need = sorted(set(seasons) | {min(seasons) - 1})
    print(f"[{_utc()}] loading group-80 teams for {need}", flush=True)
    teams_by_season: Dict[int, List[Dict[str, Any]]] = {}
    for season in need:
        teams_by_season[season] = load_season_teams(season)
        mapped = [t for t in teams_by_season[season] if t.get("engine_code")]
        print(
            f"  season {season}: group80={len(teams_by_season[season])} "
            f"mapped={len(mapped)}",
            flush=True,
        )

    jobs: List[Tuple[int, str]] = []
    for season in need:
        for t in teams_by_season[season]:
            if t.get("engine_code"):
                jobs.append((season, str(t["espn_team_id"])))

    ids_by_season_team: Dict[Tuple[int, str], List[str]] = {}
    print(f"[{_utc()}] fetching athlete id lists ({len(jobs)})", flush=True)

    def _ids(job: Tuple[int, str]) -> Tuple[Tuple[int, str], List[str]]:
        season, tid = job
        return job, load_team_athlete_ids(season, tid)

    with ThreadPoolExecutor(max_workers=min(8, workers)) as pool:
        for fut in as_completed(pool.submit(_ids, j) for j in jobs):
            key, ids = fut.result()
            ids_by_season_team[key] = ids

    owner_by_season: Dict[int, Dict[str, str]] = defaultdict(dict)
    for (season, tid), ids in ids_by_season_team.items():
        for pid in ids:
            owner_by_season[season].setdefault(pid, tid)

    # Resolve QBs only for prediction seasons. Prior-year ID lists are enough
    # for portal joins; do not spend fetches resolving 2021 positions.
    resolve_seasons = set(seasons)
    athlete_jobs: List[Tuple[int, str, str]] = []
    for season in resolve_seasons:
        for t in teams_by_season[season]:
            if not t.get("engine_code"):
                continue
            tid = str(t["espn_team_id"])
            for pid in ids_by_season_team.get((season, tid), []):
                athlete_jobs.append((season, tid, pid))
    print(
        f"[{_utc()}] resolving {len(athlete_jobs)} season-scoped athletes for QB filter",
        flush=True,
    )
    qbs_by_season_team: Dict[Tuple[int, str], List[Dict[str, Any]]] = defaultdict(list)

    def _one(job: Tuple[int, str, str]) -> Optional[Tuple[int, str, Dict[str, Any]]]:
        season, tid, pid = job
        blob = load_athlete(season, pid)
        if not blob:
            return None
        pos = (blob.get("position") or {}).get("abbreviation")
        if str(pos or "").upper() != "QB":
            return None
        return (
            season,
            tid,
            {
                "player_id": str(blob.get("id") or pid),
                "player_name": str(blob.get("displayName") or blob.get("fullName") or ""),
            },
        )

    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(_one, j) for j in athlete_jobs]
        for fut in as_completed(futs):
            done += 1
            if done % 500 == 0 or done == len(athlete_jobs):
                print(f"  athletes {done}/{len(athlete_jobs)}", flush=True)
            row = fut.result()
            if row:
                season, tid, qb = row
                qbs_by_season_team[(season, tid)].append(qb)
    print(f"[{_utc()}] QB rows {sum(len(v) for v in qbs_by_season_team.values())}", flush=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    artifacts: Dict[str, Any] = {}
    for season in seasons:
        print(f"[{_utc()}] assembling {season} + walking first-appearance stats", flush=True)
        art = build_season(
            season,
            teams_by_season=teams_by_season,
            ids_by_season_team=ids_by_season_team,
            qbs_by_season_team=qbs_by_season_team,
            owner_by_season=owner_by_season,
        )
        path = OUT_DIR / f"season_{season}.json"
        path.write_text(json.dumps(art, indent=2), encoding="utf-8")
        artifacts[str(season)] = {
            "path": str(path.relative_to(REPO)),
            "n_mapped_fbs": art["n_mapped_fbs"],
            "n_layer_a": art["n_layer_a"],
            "coverage": art["coverage"],
            "talent_all": art["talent_all"],
            "talent_established": art["talent_established"],
            "class_counts": art["class_counts"],
            "portal_n": art["portal_n"],
            "lowsample_n": art["lowsample_n"],
            "misses": art["misses"],
        }
        print(
            f"  {season} coverage {art['n_layer_a']}/{art['n_mapped_fbs']} "
            f"= {art['coverage']:.1%}",
            flush=True,
        )

    index = {
        "qb_feature_contract_version": QB_FEATURE_CONTRACT_VERSION,
        "generated_at": _utc(),
        "layer": "A",
        "seasons": artifacts,
        "forbidden_roster_sources": sorted(FORBIDDEN_ROSTER_SOURCES),
        "notes": [
            "Layer B recruiting/cast/overrides/confirms are MISSING by contract.",
            "2025 sealed. 2026 W1/W2 not used.",
            "MATCHUP_RESPONSE not changed.",
        ],
    }
    (OUT_DIR / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(f"[{_utc()}] wrote {OUT_DIR}", flush=True)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seasons", default="2022,2023,2024")
    parser.add_argument("--workers", type=int, default=WORKERS)
    args = parser.parse_args(argv)
    seasons = [int(x) for x in str(args.seasons).split(",") if x.strip()]
    for src in FORBIDDEN_ROSTER_SOURCES:
        if src == ROSTER_SOURCE:
            raise SystemExit("illegal roster source configured")
    crawl(seasons=seasons, workers=int(args.workers))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
