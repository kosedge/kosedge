"""Preseason prior v2 — program + unit roster + QB σ + coaching + uncertainty.

For preseason year Y, only seasons < Y are used. 2026 prior never reads 2026
PBP/results. Roster pack is the 2026-08-12 ESPN snapshot (pre-Week 0).
Official 2026 FBS universe is 136 full members. Research only — used_in_spread
stays false.
"""

from __future__ import annotations

import json
import math
from typing import Any, Dict, List, Mapping, Optional, Sequence

from src.services.cfb_season_engine.coaching_continuity import build_coaching_continuity
from src.services.cfb_season_engine.fbs_universe import (
    fcs_or_unknown_label,
    is_official_fbs,
    load_fbs_universe,
    membership_row,
    official_fbs_codes,
)
from src.services.cfb_season_engine.loaders import load_packaged_team_priors
from src.services.cfb_season_engine.qb_situation import build_qb_situation
from src.services.cfb_season_engine.qb_situation_overrides import apply_qb_situation_override
from src.services.cfb_season_engine.roster_construction import build_roster_construction
from src.services.cfb_warehouse.identity import canonical_code
from src.services.cfb_warehouse.leakage import era_tag
from src.services.cfb_warehouse.paths import REPO_ROOT, clean_dir

PRIOR_VERSION = "cfb-preseason-prior-v2-20260813"
USED_IN_SPREAD = False

YEAR_DECAY = 0.70
ERA_MULT = {
    "pre-2002": 0.20,
    "2002-09": 0.30,
    "2010-17": 0.45,
    "2018-21": 0.75,
    "2022-present": 1.20,
}
NET_EPA_TO_POINTS = 28.0
ROSTER_POINTS_SCALE = 0.12
QB_MEAN = {
    "incumbent": 1.2,
    "portal": -0.4,
    "open_competition": -1.8,
    "true_freshman": -2.2,
    "unknown": -0.6,
}
QB_SIGMA = {
    "incumbent": 3.4,
    "portal": 5.6,
    "open_competition": 7.2,
    "true_freshman": 7.6,
    "unknown": 6.0,
}
PROGRAM_SIGMA_BASE = 4.8
CHURN_SIGMA_SCALE = 4.0
NEW_HC_SIGMA = 1.4
NEW_HC_MEAN = -0.8
NEW_OC_SIGMA = 0.7
NEW_DC_SIGMA = 1.0
NEW_OC_MEAN = -0.25
NEW_DC_MEAN = -0.35
CAST_MEAN_SCALE = 0.60
CAST_SIGMA_SCALE = 0.12
ST_POINTS_SCALE = 0.04
UNIT_NEUTRAL = 50.0
MIN_SIGMA = 3.2
MAX_SIGMA = 9.5
MISSING_ROSTER_SIGMA = 1.6

PACKAGED_PRIOR_PATH = (
    REPO_ROOT
    / "services"
    / "model-service"
    / "src"
    / "services"
    / "cfb_season_engine"
    / "data"
    / "cfb_preseason_prior_2026.json"
)


def _f(raw: Any, default: float = 0.0) -> float:
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(val):
        return default
    return val


def season_weight(season: int, prior_year: int) -> float:
    if int(season) >= int(prior_year):
        return 0.0
    lag = int(prior_year) - int(season) - 1
    return float(ERA_MULT.get(era_tag(season), 0.5)) * (YEAR_DECAY ** lag)


def assert_prior_season_boundary(
    rows: Sequence[Mapping[str, Any]],
    *,
    prior_year: int,
) -> None:
    for row in rows:
        if int(_f(row.get("season"), 0)) >= int(prior_year):
            raise ValueError(
                f"CFB leakage: preseason {prior_year} prior used season "
                f"{row.get('season')} for {row.get('team_id')}"
            )


def program_component(
    season_finals: Sequence[Mapping[str, Any]],
    team_id: str,
    *,
    prior_year: int,
) -> Dict[str, Any]:
    used = [
        r
        for r in season_finals
        if str(r.get("team_id")) == team_id
        and int(_f(r.get("season"), 0)) < int(prior_year)
        and not str(team_id).startswith("fcs:")
    ]
    assert_prior_season_boundary(used, prior_year=prior_year)
    num = den = off_num = def_num = 0.0
    seasons_used: List[int] = []
    for row in used:
        w = season_weight(int(row["season"]), prior_year)
        if w <= 0:
            continue
        off_epa = _f(row.get("off_epa_adj"))
        def_epa = _f(row.get("def_epa_adj"))
        net = off_epa - def_epa
        num += w * net
        off_num += w * off_epa
        def_num += w * def_epa
        den += w
        seasons_used.append(int(row["season"]))
    net = num / den if den else 0.0
    off_epa = off_num / den if den else 0.0
    def_epa = def_num / den if den else 0.0
    points = net * NET_EPA_TO_POINTS
    sigma = PROGRAM_SIGMA_BASE / math.sqrt(max(den, 0.35))
    return {
        "net_epa": round(net, 5),
        "off_epa": round(off_epa, 5),
        "def_epa": round(def_epa, 5),
        "points": round(points, 3),
        "off_points": round(off_epa * NET_EPA_TO_POINTS, 3),
        "def_points": round(-def_epa * NET_EPA_TO_POINTS, 3),
        "sigma": round(sigma, 3),
        "n_seasons": len(set(seasons_used)),
        "weight_sum": round(den, 4),
        "seasons": sorted(set(seasons_used)),
        "label": "opponent_adj_epa_decay" if den else "no_fbs_history_neutral",
    }


def _unit_returning(groups: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """Unit returning proxies from position-group experience (not SNAP%)."""
    raw = dict(groups or {})
    comps = dict(raw.get("components") or {})
    labels: List[str] = []

    def _exp(key: str) -> float:
        block = comps.get(key) if isinstance(comps.get(key), Mapping) else {}
        val = block.get("experience") if block else None
        if val is None:
            labels.append(f"{key}:neutral_missing")
            return UNIT_NEUTRAL
        return _f(val, UNIT_NEUTRAL)

    units = {
        "ol": round(_exp("ol"), 2),
        "skill": round(_exp("skill"), 2),
        "front_seven": round(_exp("front_seven"), 2),
        "secondary": round(_exp("secondary"), 2),
    }
    st = raw.get("special_teams")
    if st is None:
        labels.append("st:neutral_missing")
        st_val = UNIT_NEUTRAL
    else:
        st_val = _f(st, UNIT_NEUTRAL)
    return {
        "units": units,
        "special_teams": round(st_val, 2),
        "source": str(raw.get("source") or "missing"),
        "fidelity": str(raw.get("fidelity") or "approximate"),
        "missing_labels": labels,
        "honesty": (
            "Unit experience from roster composition — not measured SNAP% by unit."
            if groups
            else "No unit table; units set to neutral 50 with missing labels."
        ),
    }


def combine_prior(
    *,
    team_id: str,
    prior_year: int,
    program: Mapping[str, Any],
    roster_strength: float,
    returning_production: float,
    portal_out: float,
    qb_class: str,
    new_hc: bool,
    as_of: str,
    new_oc: bool = False,
    new_dc: bool = False,
    ol_support: float = 50.0,
    weapons_support: float = 50.0,
    portal_in: float = 50.0,
    recruiting: float = 50.0,
    position_groups: Optional[Mapping[str, Any]] = None,
    roster_present: bool = True,
    qb_name: str = "",
    qb_source: str = "",
) -> Dict[str, Any]:
    qb_class = str(qb_class or "unknown")
    roster_pts = (float(roster_strength) - 50.0) * ROSTER_POINTS_SCALE
    qb_pts = float(QB_MEAN.get(qb_class, QB_MEAN["unknown"]))
    qb_sig = float(QB_SIGMA.get(qb_class, QB_SIGMA["unknown"]))
    cast = 0.5 * (_f(ol_support, 50.0) + _f(weapons_support, 50.0))
    cast_adj = (cast - 50.0) / 50.0
    qb_pts = qb_pts + CAST_MEAN_SCALE * cast_adj
    qb_sig = qb_sig * (1.0 - CAST_SIGMA_SCALE * cast_adj)
    qb_sig = max(2.8, qb_sig)
    churn = max(0.0, (50.0 - float(returning_production)) / 50.0)
    churn += max(0.0, (float(portal_out) - 40.0) / 80.0)
    churn_sig = CHURN_SIGMA_SCALE * min(1.0, churn)
    coach_pts = NEW_HC_MEAN if new_hc else 0.0
    coach_pts += NEW_OC_MEAN if new_oc else 0.0
    coach_pts += NEW_DC_MEAN if new_dc else 0.0
    coach_sig = NEW_HC_SIGMA if new_hc else 0.0
    coach_sig = math.sqrt(
        coach_sig ** 2
        + (NEW_OC_SIGMA if new_oc else 0.0) ** 2
        + (NEW_DC_SIGMA if new_dc else 0.0) ** 2
    )
    units = _unit_returning(position_groups)
    st_pts = (float(units["special_teams"]) - 50.0) * ST_POINTS_SCALE
    missing: List[str] = list(units.get("missing_labels") or [])
    if not roster_present:
        missing.append("roster_pack_missing_neutral")
        roster_pts = 0.0
    mean = (
        float(program.get("points") or 0.0)
        + roster_pts
        + qb_pts
        + coach_pts
        + st_pts
    )
    if not math.isfinite(mean):
        mean = roster_pts + qb_pts + coach_pts
    extra_sig = MISSING_ROSTER_SIGMA if not roster_present else 0.0
    sigma = math.sqrt(
        float(program.get("sigma") or PROGRAM_SIGMA_BASE) ** 2
        + qb_sig ** 2
        + churn_sig ** 2
        + coach_sig ** 2
        + extra_sig ** 2
    )
    if not math.isfinite(sigma):
        sigma = PROGRAM_SIGMA_BASE
    sigma = max(MIN_SIGMA, min(MAX_SIGMA, sigma))
    member = membership_row(team_id) or {}
    off_pts = program.get("off_points")
    def_pts = program.get("def_points")
    if off_pts is None and def_pts is None:
        off_pts = round(float(program.get("points") or 0.0) * 0.55, 3)
        def_pts = round(float(program.get("points") or 0.0) * 0.45, 3)
        split_label = "net_split_unavailable"
    else:
        split_label = str(program.get("label") or "opponent_adj_epa_decay")
    return {
        "team_id": canonical_code(team_id),
        "season": int(prior_year),
        "as_of": as_of,
        "prior_version": PRIOR_VERSION,
        "rating_mean": round(mean, 3),
        "rating_sigma": round(sigma, 3),
        "mean_points": round(mean, 3),
        "sigma_points": round(sigma, 3),
        "used_in_spread": USED_IN_SPREAD,
        "official_fbs": is_official_fbs(team_id),
        "conference": member.get("conference"),
        "membership": member.get("membership") or "unknown",
        "available_at": f"{prior_year}-08-01T00:00:00+00:00",
        "leakage_rule": "seasons < prior_year; roster pre-Week 0",
        "components": {
            "program_points": program.get("points"),
            "program_off_points": off_pts,
            "program_def_points": def_pts,
            "program_st_points": round(st_pts, 3),
            "program_split_label": split_label,
            "program_net_epa": program.get("net_epa"),
            "program_seasons": program.get("seasons"),
            "program_label": program.get("label"),
            "roster_points": round(roster_pts, 3),
            "roster_strength": round(float(roster_strength), 2),
            "returning_production": round(float(returning_production), 2),
            "returning_by_unit": units["units"],
            "portal_in": round(float(portal_in), 2),
            "portal_out": round(float(portal_out), 2),
            "recruiting": round(float(recruiting), 2),
            "qb_class": qb_class,
            "qb_name": qb_name,
            "qb_source": qb_source,
            "qb_points": round(qb_pts, 3),
            "qb_sigma": round(qb_sig, 3),
            "supporting_cast": round(cast, 2),
            "churn_sigma": round(churn_sig, 3),
            "new_hc": bool(new_hc),
            "new_oc": bool(new_oc),
            "new_dc": bool(new_dc),
            "coach_points": round(coach_pts, 3),
            "missing_data": missing,
        },
        "notes": (
            "Neutral-field points vs average FBS. Research only "
            f"(used_in_spread={USED_IN_SPREAD}). Wide σ = high-churn / new QB / "
            "new staff. Missing roster → neutral + label, not silent 0. "
            "Open camp battles remain human review."
        ),
    }


def build_preseason_priors(
    season_finals: Sequence[Mapping[str, Any]],
    *,
    prior_year: int = 2026,
    as_of: str = "2026-08-12",
    packaged: Optional[Mapping[str, Any]] = None,
) -> list[dict[str, Any]]:
    legal = [
        r
        for r in season_finals
        if int(_f(r.get("season"), 0)) < int(prior_year)
        and not str(r.get("team_id", "")).startswith("fcs:")
    ]
    assert_prior_season_boundary(legal, prior_year=prior_year)
    packaged = packaged if packaged is not None else load_packaged_team_priors()
    teams_payload = packaged.get("teams") or {}
    official = official_fbs_codes(include_transition=False)
    team_ids = sorted(official)
    rows: list[dict[str, Any]] = []
    for team in team_ids:
        payload = dict(teams_payload.get(team) or {})
        roster_present = bool(payload.get("roster"))
        roster = build_roster_construction(
            team, payload.get("roster"), default_source="missing_neutral"
        )
        qb_payload = apply_qb_situation_override(team, payload.get("qb"))
        qb = build_qb_situation(team, qb_payload)
        coaching = build_coaching_continuity(team, payload.get("coaching"))
        program = program_component(legal, team, prior_year=prior_year)
        rows.append(
            combine_prior(
                team_id=team,
                prior_year=prior_year,
                program=program,
                roster_strength=float(roster.roster_strength),
                returning_production=float(roster.returning_production),
                portal_out=float(roster.portal_out_value),
                qb_class=str(qb.qb_class),
                new_hc=bool(coaching.new_hc),
                as_of=as_of,
                new_oc=bool(coaching.new_oc),
                new_dc=bool(coaching.new_dc),
                ol_support=float(qb.ol_support),
                weapons_support=float(qb.weapons_support),
                portal_in=float(roster.portal_in_value),
                recruiting=float(roster.recruiting_class_score),
                position_groups=payload.get("position_groups"),
                roster_present=roster_present,
                qb_name=str(qb.starter_name or ""),
                qb_source=str(qb.source or ""),
            )
        )
    rows.sort(
        key=lambda r: (
            r["mean_points"] if math.isfinite(r["mean_points"]) else float("-inf")
        ),
        reverse=True,
    )
    for i, row in enumerate(rows, start=1):
        row["rank"] = i
    return rows


def write_preseason_priors(
    rows: Sequence[Mapping[str, Any]],
    *,
    prior_year: int = 2026,
    prefer_hd: bool = True,
    package_json: bool = True,
) -> Dict[str, Any]:
    clean = clean_dir(prefer_hd=prefer_hd) / "priors"
    try:
        clean.mkdir(parents=True, exist_ok=True)
    except OSError:
        clean = clean_dir(prefer_hd=False) / "priors"
        clean.mkdir(parents=True, exist_ok=True)
    path = clean / f"team_preseason_prior_{int(prior_year)}.parquet"
    parquet_path = None
    try:
        import pandas as pd

        flat = []
        for row in rows:
            item = dict(row)
            item["components_json"] = json.dumps(item.pop("components", {}))
            flat.append(item)
        pd.DataFrame(flat).to_parquet(path, index=False)
        parquet_path = str(path)
    except Exception:
        parquet_path = None
    payload = {
        "as_of": rows[0]["as_of"] if rows else "",
        "season": int(prior_year),
        "n": len(rows),
        "teams": {r["team_id"]: r for r in rows},
    }
    try:
        (clean / f"team_preseason_prior_{int(prior_year)}.json").write_text(
            json.dumps(payload, indent=2, allow_nan=False) + "\n"
        )
    except OSError:
        pass
    if package_json:
        PACKAGED_PRIOR_PATH.parent.mkdir(parents=True, exist_ok=True)
        slim = {
            "as_of": payload["as_of"],
            "season": int(prior_year),
            "n": len(rows),
            "source": "cfb_warehouse.preseason_prior",
            "prior_version": PRIOR_VERSION,
            "used_in_spread": USED_IN_SPREAD,
            "leakage": "seasons < prior_year",
            "universe": "official_2026_fbs_full_136",
            "teams": {
                r["team_id"]: {
                    "mean_points": r["mean_points"],
                    "sigma_points": r["sigma_points"],
                    "rating_mean": r["rating_mean"],
                    "rating_sigma": r["rating_sigma"],
                    "rank": r["rank"],
                    "qb_class": r["components"]["qb_class"],
                    "qb_sigma": r["components"]["qb_sigma"],
                    "program_points": r["components"]["program_points"],
                    "program_off_points": r["components"]["program_off_points"],
                    "program_def_points": r["components"]["program_def_points"],
                    "program_st_points": r["components"]["program_st_points"],
                    "roster_strength": r["components"]["roster_strength"],
                    "returning_by_unit": r["components"]["returning_by_unit"],
                    "new_hc": r["components"]["new_hc"],
                    "new_oc": r["components"]["new_oc"],
                    "new_dc": r["components"]["new_dc"],
                    "conference": r.get("conference"),
                    "used_in_spread": USED_IN_SPREAD,
                    "missing_data": r["components"]["missing_data"],
                }
                for r in rows
            },
        }
        PACKAGED_PRIOR_PATH.write_text(json.dumps(slim, indent=2, allow_nan=False) + "\n")
        clear_prior_cache()
    return {
        "n": len(rows),
        "parquet": parquet_path,
        "packaged": str(PACKAGED_PRIOR_PATH) if package_json else None,
        "top5": [
            {"team": r["team_id"], "mean": r["mean_points"], "sigma": r["sigma_points"]}
            for r in rows[:5]
        ],
        "bottom5": [
            {"team": r["team_id"], "mean": r["mean_points"], "sigma": r["sigma_points"]}
            for r in rows[-5:]
        ],
    }


_PRIOR_CACHE: Optional[Dict[str, Any]] = None


def clear_prior_cache() -> None:
    global _PRIOR_CACHE
    _PRIOR_CACHE = None


def load_packaged_prior(season: int = 2026) -> Dict[str, Any]:
    global _PRIOR_CACHE
    if _PRIOR_CACHE is not None:
        return _PRIOR_CACHE
    if not PACKAGED_PRIOR_PATH.exists():
        _PRIOR_CACHE = {"teams": {}, "present": False}
        return _PRIOR_CACHE
    raw = json.loads(PACKAGED_PRIOR_PATH.read_text(encoding="utf-8"))
    raw["present"] = True
    _PRIOR_CACHE = raw
    return raw


def lookup_prior(team: str, *, season: int = 2026) -> Optional[Dict[str, Any]]:
    teams = load_packaged_prior(season).get("teams") or {}
    return teams.get(str(team).upper())


def research_prior_block(
    home_team: str,
    away_team: str,
    *,
    season: int = 2026,
) -> Dict[str, Any]:
    """Attach to project-game as a research input. Never feeds spread/WP."""
    home = lookup_prior(home_team, season=season)
    away = lookup_prior(away_team, season=season)
    return {
        "season": int(season),
        "prior_version": PRIOR_VERSION,
        "home": home,
        "away": away,
        "used_in_spread": USED_IN_SPREAD,
        "kei": False,
        "note": (
            "Leakage-safe preseason prior (mean + σ vs average FBS). "
            "Research input only; does not change spread, win probability, or KEI."
        ),
    }


def program_from_stored(row: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """Reuse a previously computed leakage-safe program net when HD is absent."""
    row = dict(row or {})
    points = _f(row.get("program_points"), 0.0)
    return {
        "net_epa": points / NET_EPA_TO_POINTS if NET_EPA_TO_POINTS else 0.0,
        "off_epa": None,
        "def_epa": None,
        "points": round(points, 3),
        "off_points": row.get("program_off_points"),
        "def_points": row.get("program_def_points"),
        "sigma": PROGRAM_SIGMA_BASE / math.sqrt(max(_f(row.get("n_seasons"), 3.0), 0.35)),
        "n_seasons": int(_f(row.get("n_seasons"), 0)),
        "weight_sum": 0.0,
        "seasons": list(row.get("program_seasons") or []),
        "label": "stored_program_net_no_hd",
    }


def rebuild_p2_from_packaged(
    *,
    prior_year: int = 2026,
    as_of: str = "2026-08-13",
    season_finals: Optional[Sequence[Mapping[str, Any]]] = None,
) -> list[dict[str, Any]]:
    """Rebuild the 2026 prior for official FBS without requiring HD.

    If season_finals are provided, program EPA is recomputed (seasons < Y).
    Otherwise the stored program_points from the last packaged prior are reused.
    """
    stored = load_packaged_prior(prior_year).get("teams") or {}
    if season_finals is not None:
        return build_preseason_priors(
            season_finals, prior_year=prior_year, as_of=as_of
        )
    packaged = load_packaged_team_priors()
    teams_payload = packaged.get("teams") or {}
    rows: list[dict[str, Any]] = []
    for team in sorted(official_fbs_codes(include_transition=False)):
        payload = dict(teams_payload.get(team) or {})
        roster_present = bool(payload.get("roster"))
        roster = build_roster_construction(
            team, payload.get("roster"), default_source="missing_neutral"
        )
        qb_payload = apply_qb_situation_override(team, payload.get("qb"))
        qb = build_qb_situation(team, qb_payload)
        coaching = build_coaching_continuity(team, payload.get("coaching"))
        program = program_from_stored(stored.get(team))
        rows.append(
            combine_prior(
                team_id=team,
                prior_year=prior_year,
                program=program,
                roster_strength=float(roster.roster_strength),
                returning_production=float(roster.returning_production),
                portal_out=float(roster.portal_out_value),
                qb_class=str(qb.qb_class),
                new_hc=bool(coaching.new_hc),
                as_of=as_of,
                new_oc=bool(coaching.new_oc),
                new_dc=bool(coaching.new_dc),
                ol_support=float(qb.ol_support),
                weapons_support=float(qb.weapons_support),
                portal_in=float(roster.portal_in_value),
                recruiting=float(roster.recruiting_class_score),
                position_groups=payload.get("position_groups"),
                roster_present=roster_present,
                qb_name=str(qb.starter_name or ""),
                qb_source=str(qb.source or ""),
            )
        )
    rows.sort(
        key=lambda r: (
            r["mean_points"] if math.isfinite(r["mean_points"]) else float("-inf")
        ),
        reverse=True,
    )
    for i, row in enumerate(rows, start=1):
        row["rank"] = i
    return rows
