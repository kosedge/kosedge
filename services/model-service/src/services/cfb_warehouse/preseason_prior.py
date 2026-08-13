"""Preseason prior v1 — program + roster + QB uncertainty (leakage-safe).

For preseason year Y, only seasons < Y are used. 2026 prior never reads 2026
PBP/results. Roster pack is the 2026-08-12 ESPN snapshot (pre-Week 0).
"""

from __future__ import annotations

import json
import math
from typing import Any, Dict, List, Mapping, Optional, Sequence

from src.services.cfb_season_engine.coaching_continuity import build_coaching_continuity
from src.services.cfb_season_engine.loaders import load_packaged_team_priors
from src.services.cfb_season_engine.qb_situation import build_qb_situation
from src.services.cfb_season_engine.qb_situation_overrides import apply_qb_situation_override
from src.services.cfb_season_engine.roster_construction import build_roster_construction
from src.services.cfb_warehouse.identity import known_engine_codes
from src.services.cfb_warehouse.leakage import era_tag
from src.services.cfb_warehouse.paths import REPO_ROOT, clean_dir

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
MIN_SIGMA = 3.2
MAX_SIGMA = 9.5

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
    num = den = 0.0
    seasons_used: List[int] = []
    for row in used:
        w = season_weight(int(row["season"]), prior_year)
        if w <= 0:
            continue
        net = _f(row.get("off_epa_adj")) - _f(row.get("def_epa_adj"))
        num += w * net
        den += w
        seasons_used.append(int(row["season"]))
    net = num / den if den else 0.0
    points = net * NET_EPA_TO_POINTS
    sigma = PROGRAM_SIGMA_BASE / math.sqrt(max(den, 0.35))
    return {
        "net_epa": round(net, 5),
        "points": round(points, 3),
        "sigma": round(sigma, 3),
        "n_seasons": len(set(seasons_used)),
        "weight_sum": round(den, 4),
        "seasons": sorted(set(seasons_used)),
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
) -> Dict[str, Any]:
    qb_class = str(qb_class or "unknown")
    roster_pts = (float(roster_strength) - 50.0) * ROSTER_POINTS_SCALE
    qb_pts = float(QB_MEAN.get(qb_class, QB_MEAN["unknown"]))
    qb_sig = float(QB_SIGMA.get(qb_class, QB_SIGMA["unknown"]))
    churn = max(0.0, (50.0 - float(returning_production)) / 50.0)
    churn += max(0.0, (float(portal_out) - 40.0) / 80.0)
    churn_sig = CHURN_SIGMA_SCALE * min(1.0, churn)
    coach_pts = NEW_HC_MEAN if new_hc else 0.0
    coach_sig = NEW_HC_SIGMA if new_hc else 0.0
    mean = float(program.get("points") or 0.0) + roster_pts + qb_pts + coach_pts
    if not math.isfinite(mean):
        mean = roster_pts + qb_pts + coach_pts
    sigma = math.sqrt(
        float(program.get("sigma") or PROGRAM_SIGMA_BASE) ** 2
        + qb_sig ** 2
        + churn_sig ** 2
        + coach_sig ** 2
    )
    if not math.isfinite(sigma):
        sigma = PROGRAM_SIGMA_BASE
    sigma = max(MIN_SIGMA, min(MAX_SIGMA, sigma))
    return {
        "team_id": team_id,
        "season": int(prior_year),
        "as_of": as_of,
        "mean_points": round(mean, 3),
        "sigma_points": round(sigma, 3),
        "available_at": f"{prior_year}-08-01T00:00:00+00:00",
        "leakage_rule": "seasons < prior_year; roster pre-Week 0",
        "components": {
            "program_points": program.get("points"),
            "program_net_epa": program.get("net_epa"),
            "program_seasons": program.get("seasons"),
            "roster_points": round(roster_pts, 3),
            "roster_strength": round(float(roster_strength), 2),
            "returning_production": round(float(returning_production), 2),
            "qb_class": qb_class,
            "qb_points": qb_pts,
            "qb_sigma": qb_sig,
            "churn_sigma": round(churn_sig, 3),
            "new_hc": bool(new_hc),
            "coach_points": coach_pts,
        },
        "notes": (
            "Neutral-field points vs average FBS. Wide σ = high-churn / new QB. "
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
    known = known_engine_codes()
    team_ids = sorted(
        {str(r["team_id"]) for r in legal if str(r["team_id"]) in known}
        | {str(k).upper() for k in teams_payload}
    )
    rows: list[dict[str, Any]] = []
    for team in team_ids:
        payload = dict(teams_payload.get(team) or {})
        roster = build_roster_construction(team, payload.get("roster"))
        qb = build_qb_situation(
            team, apply_qb_situation_override(team, payload.get("qb"))
        )
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
    import pandas as pd

    clean = clean_dir(prefer_hd=prefer_hd) / "priors"
    clean.mkdir(parents=True, exist_ok=True)
    path = clean / f"team_preseason_prior_{int(prior_year)}.parquet"
    flat = []
    for row in rows:
        item = dict(row)
        item["components_json"] = json.dumps(item.pop("components", {}))
        flat.append(item)
    pd.DataFrame(flat).to_parquet(path, index=False)
    payload = {
        "as_of": rows[0]["as_of"] if rows else "",
        "season": int(prior_year),
        "n": len(rows),
        "teams": {r["team_id"]: r for r in rows},
    }
    (clean / f"team_preseason_prior_{int(prior_year)}.json").write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n"
    )
    if package_json:
        PACKAGED_PRIOR_PATH.parent.mkdir(parents=True, exist_ok=True)
        slim = {
            "as_of": payload["as_of"],
            "season": int(prior_year),
            "n": len(rows),
            "source": "cfb_warehouse.preseason_prior",
            "leakage": "seasons < prior_year",
            "teams": {
                r["team_id"]: {
                    "mean_points": r["mean_points"],
                    "sigma_points": r["sigma_points"],
                    "rank": r["rank"],
                    "qb_class": r["components"]["qb_class"],
                    "program_points": r["components"]["program_points"],
                    "roster_strength": r["components"]["roster_strength"],
                }
                for r in rows
            },
        }
        PACKAGED_PRIOR_PATH.write_text(json.dumps(slim, indent=2, allow_nan=False) + "\n")
    return {
        "n": len(rows),
        "parquet": str(path),
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
    return {
        "season": int(season),
        "home": lookup_prior(home_team, season=season),
        "away": lookup_prior(away_team, season=season),
        "used_in_spread": False,
        "note": (
            "Leakage-safe preseason prior (mean + σ vs average FBS). "
            "Research input only; does not change spread, win probability, or KEI."
        ),
    }
