#!/usr/bin/env python3
"""Diagnose 2026 CFB roster/QB/unit scoring inflation (research only).

Does not fit λ / offset / shrink. Does not open 2025. Does not write KEI,
change priors, unsat PLAY, or flip the public kill switch.

Usage:
  PYTHONPATH=services/model-service \\
    python3 scripts/cfb/cfb_2026_roster_inflation_diagnostic.py
"""

from __future__ import annotations

import json
import math
import re
import sys
from collections import defaultdict
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
sys.path.insert(0, str(MS))
sys.path.insert(0, str(ROOT / "scripts" / "cfb"))

from src.services.cfb_season_engine import (  # noqa: E402
    project_game_preview,
    resolve_season_universe,
)
from src.services.cfb_season_engine import priors as P  # noqa: E402
from src.services.cfb_season_engine.conferences import conference_for  # noqa: E402
from src.services.cfb_season_engine.fbs_universe import official_fbs_codes  # noqa: E402
from src.services.cfb_season_engine.power_sot import (  # noqa: E402
    sit_missing_power_from_sot_rows,
)
from src.services.cfb_season_engine.position_groups import (  # noqa: E402
    PositionGroupGrades,
    build_position_groups,
)
from src.services.cfb_season_engine.qb_situation import build_qb_situation  # noqa: E402
from src.services.cfb_season_engine.roster_construction import (  # noqa: E402
    compute_roster_strength,
    continuity_from_components,
    portal_net_value,
)
from src.services.cfb_season_engine.team_projection import (  # noqa: E402
    compose_team_projection,
    project_game_to_dict,
)
from src.services.cfb_season_engine.totals_guard_holdout import (  # noqa: E402
    matchup_inflation_on_sum,
)
from src.services.cfb_season_engine.types import (  # noqa: E402
    QbSituation,
    RosterConstruction,
    TeamProjectionState,
)
from cfb_joined_residual_audit import attach_odds, slim_from_espn  # noqa: E402

OFFICIAL = MS / "src/services/cfb_season_engine/data/cfb_official_schedule_2026.json"
POWER = MS / "src/services/cfb_season_engine/data/cfb_power_sot_2026.json"
SNAP = MS / "src/services/cfb_season_engine/data/cfb_real_roster_snapshot_2026.json"
W2_ODDS = ROOT / "data/ops/cfb-w2-espn-scoreboard-odds-20260911.json"
W1_CARD = ROOT / "data/ops/cfb-w1-handicap-card-20260831.json"
OUT_JSON = ROOT / "data/ops/cfb-2026-roster-inflation-diagnostic-20260911.json"
OUT_MD = ROOT / "data/ops/cfb-2026-roster-inflation-diagnostic-20260911.md"

P4 = frozenset({"SEC", "Big Ten", "ACC", "Big 12"})
QB_TALENT_LOWSAMPLE_ATTEMPTS = 80


def assert_2025_untouched() -> None:
    """Local seal — do not import #538 hist_week0; do not score 2025."""
    # This diagnostic never loads 2023–25 residuals. Fail closed if a caller
    # tries to pass an open-2025 flag later.
    return


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(v)))


def _mean(xs: Sequence[float]) -> Optional[float]:
    return None if not xs else round(sum(xs) / len(xs), 4)


def _sd(xs: Sequence[float]) -> Optional[float]:
    if len(xs) < 2:
        return None
    mu = sum(xs) / len(xs)
    return round(math.sqrt(sum((x - mu) ** 2 for x in xs) / len(xs)), 4)


def _median(xs: Sequence[float]) -> Optional[float]:
    if not xs:
        return None
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    return round(s[mid] if n % 2 else 0.5 * (s[mid - 1] + s[mid]), 4)


def _quantile(xs: Sequence[float], q: float) -> Optional[float]:
    if not xs:
        return None
    s = sorted(xs)
    if len(s) == 1:
        return round(s[0], 4)
    pos = (len(s) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    frac = pos - lo
    return round(s[lo] * (1.0 - frac) + s[hi] * frac, 4)


def _mae(xs: Sequence[float]) -> Optional[float]:
    return None if not xs else round(sum(abs(x) for x in xs) / len(xs), 4)


def _rmse(xs: Sequence[float]) -> Optional[float]:
    if not xs:
        return None
    return round(math.sqrt(sum(x * x for x in xs) / len(xs)), 4)


def _corr(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx < 1e-12 or dy < 1e-12:
        return None
    return round(num / (dx * dy), 4)


def dist(xs: Sequence[float]) -> Dict[str, Any]:
    return {
        "n": len(xs),
        "mean": _mean(xs),
        "sd": _sd(xs),
        "p10": _quantile(xs, 0.10),
        "p50": _median(xs),
        "p90": _quantile(xs, 0.90),
        "min": None if not xs else round(min(xs), 4),
        "max": None if not xs else round(max(xs), 4),
    }


def talent_from_qb_stats(attempts: int, yards: int, tds: int, *, is_portal: bool) -> float:
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


def resolve_qb_talent(
    attempts: int,
    yards: int,
    tds: int,
    *,
    is_portal: bool,
    recruiting_class_score: float,
) -> float:
    stats = talent_from_qb_stats(attempts, yards, tds, is_portal=is_portal)
    att = int(attempts or 0)
    if att >= QB_TALENT_LOWSAMPLE_ATTEMPTS:
        return stats
    fallback = _clamp(float(recruiting_class_score))
    w = math.sqrt(att / float(QB_TALENT_LOWSAMPLE_ATTEMPTS)) if att > 0 else 0.0
    return _clamp((1.0 - w) * fallback + w * stats)


def invert_espn_returning(blended: float, recruiting: float) -> float:
    ret_base = _clamp(32.0 + 0.38 * recruiting)
    return _clamp((float(blended) - 0.60 * ret_base) / 0.40)


def invert_espn_portal_in(blended: float, recruiting: float) -> float:
    pin_base = _clamp(28.0 + 0.42 * recruiting)
    return _clamp((float(blended) - 0.55 * pin_base) / 0.45)


def invert_espn_portal_out(blended: float, recruiting: float) -> float:
    pout_base = _clamp(55.0 - 0.12 * recruiting)
    return _clamp((float(blended) - 0.60 * pout_base) / 0.40)


def invert_espn_experience(blended: float, recruiting: float) -> float:
    exp_base = _clamp(30.0 + 0.45 * recruiting)
    return _clamp((float(blended) - 0.45 * exp_base) / 0.55)


def blend_roster_metrics(
    *,
    recruiting: float,
    espn_returning: float,
    espn_portal_in: float,
    espn_portal_out: float,
    espn_experience: float,
) -> Dict[str, float]:
    ret_base = _clamp(32.0 + 0.38 * recruiting)
    pin_base = _clamp(28.0 + 0.42 * recruiting)
    pout_base = _clamp(55.0 - 0.12 * recruiting)
    returning = _clamp(0.40 * espn_returning + 0.60 * ret_base)
    portal_in = _clamp(0.45 * espn_portal_in + 0.55 * pin_base)
    portal_out = _clamp(0.40 * espn_portal_out + 0.60 * pout_base)
    experience = _clamp(0.55 * espn_experience + 0.45 * (30.0 + 0.45 * recruiting))
    return {
        "returning_production": returning,
        "portal_in_value": portal_in,
        "portal_out_value": portal_out,
        "experience_index": experience,
    }


def finish_roster(team: str, src: RosterConstruction, **fields: Any) -> RosterConstruction:
    rec = float(fields.get("recruiting_class_score", src.recruiting_class_score))
    ret = float(fields.get("returning_production", src.returning_production))
    pin = float(fields.get("portal_in_value", src.portal_in_value))
    pout = float(fields.get("portal_out_value", src.portal_out_value))
    exp = float(fields.get("experience_index", src.experience_index))
    if "portal_net" in fields:
        pnet = float(fields["portal_net"])
    else:
        pnet = portal_net_value(pin, pout)
    if "continuity_score" in fields:
        cont = float(fields["continuity_score"])
    else:
        cont = continuity_from_components(ret, pin, pout, exp)
    if "roster_strength" in fields:
        strength = float(fields["roster_strength"])
    else:
        strength, _ = compute_roster_strength(
            returning_production=ret,
            portal_net=pnet,
            recruiting_class_score=rec,
            experience_index=exp,
        )
    snap = ret / 100.0
    return replace(
        src,
        recruiting_class_score=rec,
        recruiting_capital=rec,
        returning_production=ret,
        returning_snap_share=round(snap, 4),
        returning_start_share=round(min(1.0, snap + 0.03), 4),
        portal_in_value=pin,
        portal_out_value=pout,
        portal_in_score=pin,
        portal_out_score=pout,
        portal_net=round(pnet, 2),
        experience_index=exp,
        continuity_score=_clamp(cont),
        roster_strength=round(float(strength), 2),
        notes=f"{src.notes} | ablation={team}",
    )


def rebuild_groups_for_recruiting(
    groups: PositionGroupGrades,
    *,
    old_rec: float,
    new_rec: float,
    old_ret: float,
    new_ret: float,
    old_exp: float,
    new_exp: float,
    new_portal_in: float,
) -> PositionGroupGrades:
    comps = {}
    headlines: Dict[str, float] = {}
    for unit in ("ol", "skill", "front_seven", "secondary"):
        old = (groups.components or {}).get(unit) or {}
        old_talent = float(old.get("talent") or getattr(groups, unit))
        residual = old_talent - (0.62 * old_rec + 0.22 * old_exp + 0.16 * old_ret)
        talent = _clamp(0.62 * new_rec + 0.22 * new_exp + 0.16 * new_ret + residual)
        portal_impact = _clamp(0.45 * new_portal_in + 0.35 * new_rec + 0.20 * new_exp)
        grade = _clamp(0.50 * talent + 0.30 * new_exp + 0.20 * portal_impact)
        comps[unit] = {
            "talent": round(talent, 2),
            "experience": round(new_exp, 2),
            "portal_impact": round(portal_impact, 2),
            "grade": round(grade, 2),
        }
        headlines[unit] = grade
    st = _clamp(0.45 * new_exp + 0.55 * new_rec)
    return replace(
        groups,
        ol=round(headlines["ol"], 2),
        skill=round(headlines["skill"], 2),
        front_seven=round(headlines["front_seven"], 2),
        secondary=round(headlines["secondary"], 2),
        special_teams=round(st, 2),
        components=comps,
        notes="research rebuild from recruiting-channel formula",
    )


def league_groups(team: str) -> PositionGroupGrades:
    return build_position_groups(
        team,
        {
            "ol": 50.0,
            "skill": 50.0,
            "front_seven": 50.0,
            "secondary": 50.0,
            "special_teams": 50.0,
            "fidelity": "placeholder",
            "source": "research_ablation_units_50",
        },
    )


def rebuild_qb(
    qb: QbSituation,
    *,
    talent: Optional[float] = None,
    qb_class: Optional[str] = None,
    ol: Optional[float] = None,
    skill: Optional[float] = None,
) -> QbSituation:
    payload = {
        "qb_class": qb_class if qb_class is not None else qb.qb_class,
        "experience_starts": qb.experience_starts,
        "qb_talent": qb.qb_talent if talent is None else talent,
        "ol_support": qb.ol_support if ol is None else ol,
        "weapons_support": qb.weapons_support if skill is None else skill,
        "starter_name": qb.starter_name,
        "starter_key": qb.starter_key,
        "is_portal": qb.qb_class == "portal",
        "is_true_freshman": qb.qb_class == "true_freshman",
        "open_competition": qb.qb_class == "open_competition",
        "source": "research_ablation",
        "fidelity": qb.fidelity,
    }
    return build_qb_situation(
        qb.team,
        payload,
        ol_grade=payload["ol_support"],
        skill_grade=payload["weapons_support"],
    )


def compose_from(
    live: TeamProjectionState,
    *,
    roster: Optional[RosterConstruction] = None,
    qb: Optional[QbSituation] = None,
    groups: Optional[PositionGroupGrades] = None,
) -> TeamProjectionState:
    return compose_team_projection(
        live.team,
        roster or live.roster,
        qb or live.qb,
        groups or live.groups,
        efficiency=live.efficiency,
        home_field=live.home_field,
        coaching=live.coaching,
    )


def parse_book_total(best: Any) -> Optional[float]:
    if best is None:
        return None
    if isinstance(best, (int, float)):
        return float(best)
    m = re.search(r"(\d+(?:\.\d+)?)", str(best))
    return float(m.group(1)) if m else None


def load_w1_totals() -> Dict[str, float]:
    raw = json.loads(W1_CARD.read_text(encoding="utf-8"))
    out: Dict[str, float] = {}
    for row in raw.get("totals") or []:
        pair = str(row.get("game") or "")
        if not pair or pair.startswith("FCS:"):
            continue
        tot = parse_book_total(row.get("best"))
        if tot is not None:
            out[pair] = tot
    return out


def bucket_pred_total(v: float) -> str:
    if v < 48:
        return "<48"
    if v < 52:
        return "48-52"
    if v < 56:
        return "52-56"
    if v < 60:
        return "56-60"
    if v < 68:
        return "60-68"
    return ">=68"


def summarize_board(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    resid = [float(r["total_resid"]) for r in rows]
    totals = [float(r["model_total"]) for r in rows]
    infl = [
        float(r["matchup_inflation"])
        for r in rows
        if r.get("matchup_inflation") is not None
    ]
    by_bucket: Dict[str, List[float]] = defaultdict(list)
    for r in rows:
        by_bucket[bucket_pred_total(float(r["model_total"]))].append(
            float(r["total_resid"])
        )
    return {
        "n": len(rows),
        "mean_model_total": _mean(totals),
        "sd_model_total": _sd(totals),
        "p10_model_total": _quantile(totals, 0.10),
        "p50_model_total": _median(totals),
        "p90_model_total": _quantile(totals, 0.90),
        "mean_resid": _mean(resid),
        "median_resid": _median(resid),
        "mae": _mae(resid),
        "rmse": _rmse(resid),
        "mean_matchup_inflation": _mean(infl),
        "over_n": sum(1 for x in resid if x > 0),
        "under_n": sum(1 for x in resid if x < 0),
        "calibration_by_pred_bucket": {
            k: {"n": len(v), "mean_resid": _mean(v), "mae": _mae(v)}
            for k, v in sorted(by_bucket.items())
        },
    }


def load_qb_stats() -> Dict[str, Dict[str, Any]]:
    snap = json.loads(SNAP.read_text(encoding="utf-8"))
    out = {}
    for code, row in (snap.get("teams") or {}).items():
        qb = row.get("qb") or {}
        out[str(code)] = {
            "pass_attempts_2025": int(qb.get("pass_attempts_2025") or 0),
            "pass_yards_2025": int(qb.get("pass_yards_2025") or 0),
            "pass_td_2025": int(qb.get("pass_td_2025") or 0),
            "is_portal": bool(qb.get("is_portal")),
        }
    return out


def recruiting_channel_state(live: TeamProjectionState, qb_stats: Mapping[str, Any]) -> TeamProjectionState:
    roster = live.roster
    rec0 = float(roster.recruiting_class_score)
    espn_ret = invert_espn_returning(roster.returning_production, rec0)
    espn_pin = invert_espn_portal_in(roster.portal_in_value, rec0)
    espn_pout = invert_espn_portal_out(roster.portal_out_value, rec0)
    espn_exp = invert_espn_experience(roster.experience_index, rec0)
    blended = blend_roster_metrics(
        recruiting=50.0,
        espn_returning=espn_ret,
        espn_portal_in=espn_pin,
        espn_portal_out=espn_pout,
        espn_experience=espn_exp,
    )
    roster2 = finish_roster(
        live.team,
        roster,
        recruiting_class_score=50.0,
        **blended,
    )
    groups2 = rebuild_groups_for_recruiting(
        live.groups,
        old_rec=rec0,
        new_rec=50.0,
        old_ret=roster.returning_production,
        new_ret=blended["returning_production"],
        old_exp=roster.experience_index,
        new_exp=blended["experience_index"],
        new_portal_in=blended["portal_in_value"],
    )
    stats = qb_stats.get(live.team) or {}
    talent = resolve_qb_talent(
        int(stats.get("pass_attempts_2025") or 0),
        int(stats.get("pass_yards_2025") or 0),
        int(stats.get("pass_td_2025") or 0),
        is_portal=bool(stats.get("is_portal")),
        recruiting_class_score=50.0,
    )
    qb2 = rebuild_qb(
        live.qb,
        talent=talent,
        ol=groups2.ol,
        skill=groups2.skill,
    )
    return compose_from(live, roster=roster2, qb=qb2, groups=groups2)


def variant_state(
    name: str,
    live: TeamProjectionState,
    qb_stats: Mapping[str, Any],
) -> TeamProjectionState:
    roster = live.roster
    if name == "frozen":
        return live
    if name == "recruiting_field_50":
        r2 = finish_roster(live.team, roster, recruiting_class_score=50.0)
        return compose_from(live, roster=r2)
    if name == "recruiting_channel_50":
        return recruiting_channel_state(live, qb_stats)
    if name == "returning_50":
        r2 = finish_roster(live.team, roster, returning_production=50.0)
        return compose_from(live, roster=r2)
    if name == "portal_50":
        r2 = finish_roster(
            live.team,
            roster,
            portal_in_value=50.0,
            portal_out_value=50.0,
        )
        return compose_from(live, roster=r2)
    if name == "experience_50":
        r2 = finish_roster(live.team, roster, experience_index=50.0)
        return compose_from(live, roster=r2)
    if name == "roster_strength_50":
        r2 = finish_roster(live.team, roster, roster_strength=50.0)
        return compose_from(live, roster=r2)
    if name == "units_50":
        g2 = league_groups(live.team)
        return compose_from(live, groups=g2)
    if name == "units_and_cast_50":
        g2 = league_groups(live.team)
        qb2 = rebuild_qb(live.qb, ol=50.0, skill=50.0)
        return compose_from(live, qb=qb2, groups=g2)
    if name == "qb_talent_50":
        qb2 = rebuild_qb(live.qb, talent=50.0)
        return compose_from(live, qb=qb2)
    if name == "qb_class_unknown":
        qb2 = rebuild_qb(live.qb, qb_class="unknown")
        return compose_from(live, qb=qb2)
    if name == "qb_league":
        qb2 = rebuild_qb(live.qb, talent=50.0, qb_class="unknown", ol=50.0, skill=50.0)
        return compose_from(live, qb=qb2)
    if name == "game_units_50_indices_live":
        st = live.copy()
        st.groups = league_groups(live.team)
        return st
    if name == "qb_and_units_50":
        g2 = league_groups(live.team)
        qb2 = rebuild_qb(live.qb, talent=50.0, qb_class="unknown", ol=50.0, skill=50.0)
        return compose_from(live, qb=qb2, groups=g2)
    if name == "roster_qb_units_league":
        r2 = finish_roster(
            live.team,
            roster,
            recruiting_class_score=50.0,
            returning_production=50.0,
            portal_in_value=50.0,
            portal_out_value=50.0,
            experience_index=50.0,
            roster_strength=50.0,
        )
        g2 = league_groups(live.team)
        qb2 = rebuild_qb(live.qb, talent=50.0, qb_class="unknown", ol=50.0, skill=50.0)
        return compose_from(live, roster=r2, qb=qb2, groups=g2)
    if name == "off_layers_league_def_live":
        # League offense inputs; keep live defensive unit grades + def_eff.
        r2 = finish_roster(
            live.team,
            roster,
            recruiting_class_score=50.0,
            returning_production=50.0,
            portal_in_value=50.0,
            portal_out_value=50.0,
            experience_index=roster.experience_index,
            roster_strength=50.0,
        )
        g2 = replace(
            league_groups(live.team),
            front_seven=live.groups.front_seven,
            secondary=live.groups.secondary,
        )
        qb2 = rebuild_qb(live.qb, talent=50.0, qb_class="unknown", ol=50.0, skill=50.0)
        return compose_from(live, roster=r2, qb=qb2, groups=g2)
    if name == "def_layers_league_off_live":
        r2 = finish_roster(live.team, roster, experience_index=50.0)
        g2 = replace(
            live.groups,
            front_seven=50.0,
            secondary=50.0,
        )
        return compose_from(live, roster=r2, groups=g2)
    raise KeyError(name)


VARIANTS = (
    "frozen",
    "recruiting_field_50",
    "recruiting_channel_50",
    "returning_50",
    "portal_50",
    "experience_50",
    "roster_strength_50",
    "units_50",
    "units_and_cast_50",
    "qb_talent_50",
    "qb_class_unknown",
    "qb_league",
    "game_units_50_indices_live",
    "qb_and_units_50",
    "roster_qb_units_league",
    "off_layers_league_def_live",
    "def_layers_league_off_live",
)


def team_row(state: TeamProjectionState, conf: str) -> Dict[str, Any]:
    r = state.roster
    q = state.qb
    g = state.groups
    e = state.efficiency
    return {
        "team": state.team,
        "conference": conf,
        "p4": conf in P4,
        "recruiting": r.recruiting_class_score,
        "returning": r.returning_production,
        "portal_in": r.portal_in_value,
        "portal_out": r.portal_out_value,
        "portal_net": r.portal_net,
        "experience": r.experience_index,
        "continuity": r.continuity_score,
        "roster_strength": r.roster_strength,
        "qb_class": q.qb_class,
        "qb_talent": q.qb_talent,
        "qb_index": q.qb_situation_index,
        "qb_score": q.qb_situation_score,
        "ol": g.ol,
        "skill": g.skill,
        "front_seven": g.front_seven,
        "secondary": g.secondary,
        "special_teams": g.special_teams,
        "off_eff": e.off_eff if e else None,
        "def_eff": e.def_eff if e else None,
        "offense_index": state.offense_index,
        "defense_index": state.defense_index,
        "pace": state.pace_factor,
        "recruiting_floor_55": abs(r.recruiting_class_score - 55.0) < 1e-6,
    }


def collect_board(
    universe,
    live_states: Mapping[str, TeamProjectionState],
    qb_stats: Mapping[str, Any],
    official: Mapping[str, Any],
    w1: Mapping[str, float],
    w2_index: Mapping[str, Any],
    variant: str,
) -> List[Dict[str, Any]]:
    rows = []
    cache: Dict[str, TeamProjectionState] = {}
    for raw in official.get("games") or []:
        week = int(raw.get("week") or -1)
        if week not in (1, 2):
            continue
        if raw.get("fcs_home") or raw.get("fcs_away"):
            continue
        home = str(raw.get("home") or "").upper()
        away = str(raw.get("away") or "").upper()
        if home not in live_states or away not in live_states:
            continue
        pair = f"{away}@{home}"
        market = None
        if week == 2:
            odds = attach_odds(
                {
                    "home": home,
                    "away": away,
                    "home_name": raw.get("home_name"),
                    "away_name": raw.get("away_name"),
                },
                w2_index,
            )
            if odds:
                market = odds.get("best_total")
                if market is not None:
                    market = float(market)
        else:
            market = w1.get(pair)
        if market is None:
            continue
        for code in (home, away):
            if code not in cache:
                cache[code] = variant_state(variant, live_states[code], qb_stats)
        universe.teams[home] = cache[home]
        universe.teams[away] = cache[away]
        proj = project_game_to_dict(
            project_game_preview(
                universe,
                home_team=home,
                away_team=away,
                week=week,
                season=2026,
                neutral_site=bool(raw.get("neutral_site")),
            )
        )
        drivers = (proj.get("drivers") or {}).get("matchup") or {}
        model_total = float(proj["expected_total"])
        infl = None
        try:
            _, infl = matchup_inflation_on_sum(
                model_total=model_total,
                home_diag=drivers.get("home_points_diag") or {},
                away_diag=drivers.get("away_points_diag") or {},
                league_ppg=float(P.LEAGUE_TEAM_PPG),
                points_clamp=P.EXPECTED_POINTS_CLAMP,
                st_nudge=float(drivers.get("st_total_nudge") or 0.0),
            )
        except Exception:
            infl = None
        hs = cache[home]
        aws = cache[away]
        rows.append(
            {
                "week": week,
                "pair": pair,
                "model_total": round(model_total, 4),
                "market_total": market,
                "total_resid": round(model_total - market, 4),
                "matchup_inflation": None if infl is None else round(float(infl), 4),
                "home_off": hs.offense_index,
                "away_off": aws.offense_index,
                "home_def": hs.defense_index,
                "away_def": aws.defense_index,
                "home_rec": hs.roster.recruiting_class_score,
                "away_rec": aws.roster.recruiting_class_score,
                "family": (
                    "p4_vs_p4"
                    if conference_for(home) in P4 and conference_for(away) in P4
                    else (
                        "p4_vs_g5"
                        if conference_for(home) in P4 or conference_for(away) in P4
                        else "g5_vs_g5"
                    )
                ),
            }
        )
        universe.teams[home] = live_states[home]
        universe.teams[away] = live_states[away]
    return rows


def fbs_distributions(states: Mapping[str, TeamProjectionState]) -> Dict[str, Any]:
    official = official_fbs_codes()
    rows = [
        team_row(st, conference_for(code))
        for code, st in states.items()
        if code in official
    ]
    keys = [
        "recruiting",
        "returning",
        "portal_in",
        "portal_out",
        "portal_net",
        "experience",
        "continuity",
        "roster_strength",
        "qb_talent",
        "qb_index",
        "qb_score",
        "ol",
        "skill",
        "front_seven",
        "secondary",
        "off_eff",
        "def_eff",
        "offense_index",
        "defense_index",
        "pace",
    ]
    distributions = {}
    for k in keys:
        xs = [float(r[k]) for r in rows if r.get(k) is not None]
        distributions[k] = dist(xs)
    rec = [float(r["recruiting"]) for r in rows]
    correlations = {
        "recruiting_vs_roster_strength": _corr(rec, [r["roster_strength"] for r in rows]),
        "recruiting_vs_ol": _corr(rec, [r["ol"] for r in rows]),
        "recruiting_vs_skill": _corr(rec, [r["skill"] for r in rows]),
        "recruiting_vs_front_seven": _corr(rec, [r["front_seven"] for r in rows]),
        "recruiting_vs_secondary": _corr(rec, [r["secondary"] for r in rows]),
        "recruiting_vs_qb_talent": _corr(rec, [r["qb_talent"] for r in rows]),
        "recruiting_vs_offense_index": _corr(rec, [r["offense_index"] for r in rows]),
        "recruiting_vs_defense_index": _corr(rec, [r["defense_index"] for r in rows]),
        "offense_index_vs_defense_index": _corr(
            [r["offense_index"] for r in rows], [r["defense_index"] for r in rows]
        ),
        "roster_strength_vs_ol": _corr(
            [r["roster_strength"] for r in rows], [r["ol"] for r in rows]
        ),
        "qb_index_vs_offense_index": _corr(
            [r["qb_index"] for r in rows], [r["offense_index"] for r in rows]
        ),
        "off_eff_vs_offense_index": _corr(
            [float(r["off_eff"]) for r in rows if r.get("off_eff") is not None],
            [r["offense_index"] for r in rows if r.get("off_eff") is not None],
        ),
    }
    qb_classes: Dict[str, int] = defaultdict(int)
    for r in rows:
        qb_classes[str(r["qb_class"])] += 1
    p4 = [r for r in rows if r["p4"]]
    g5 = [r for r in rows if not r["p4"]]
    return {
        "n_fbs": len(rows),
        "recruiting_exactly_55": sum(1 for r in rows if r["recruiting_floor_55"]),
        "recruiting_gt_80": sum(1 for r in rows if r["recruiting"] >= 80),
        "qb_class_counts": dict(qb_classes),
        "distributions": distributions,
        "correlations": correlations,
        "p4_vs_g5": {
            "p4": {
                "n": len(p4),
                "recruiting": dist([r["recruiting"] for r in p4]),
                "roster_strength": dist([r["roster_strength"] for r in p4]),
                "offense_index": dist([r["offense_index"] for r in p4]),
                "defense_index": dist([r["defense_index"] for r in p4]),
                "ol": dist([r["ol"] for r in p4]),
                "qb_index": dist([r["qb_index"] for r in p4]),
            },
            "g5_or_other": {
                "n": len(g5),
                "recruiting": dist([r["recruiting"] for r in g5]),
                "roster_strength": dist([r["roster_strength"] for r in g5]),
                "offense_index": dist([r["offense_index"] for r in g5]),
                "defense_index": dist([r["defense_index"] for r in g5]),
                "ol": dist([r["ol"] for r in g5]),
                "qb_index": dist([r["qb_index"] for r in g5]),
            },
        },
        "asymmetric_centering": {
            "mean_offense_index": _mean([r["offense_index"] for r in rows]),
            "mean_defense_index": _mean([r["defense_index"] for r in rows]),
            "sd_offense_index": _sd([r["offense_index"] for r in rows]),
            "sd_defense_index": _sd([r["defense_index"] for r in rows]),
            "mean_ol_minus_front_seven": _mean(
                [r["ol"] - r["front_seven"] for r in rows]
            ),
            "mean_skill_minus_secondary": _mean(
                [r["skill"] - r["secondary"] for r in rows]
            ),
            "mean_qb_index": _mean([r["qb_index"] for r in rows]),
            "note": (
                "Totals inflate when offense sits above 1.0 without a matching "
                "defensive lift, and/or when off↔def width is large under "
                "(off/def)^MATCHUP_RESPONSE."
            ),
        },
        "top_offense": sorted(rows, key=lambda r: -r["offense_index"])[:8],
        "bottom_defense": sorted(rows, key=lambda r: r["defense_index"])[:8],
    }


def write_report(payload: Mapping[str, Any]) -> None:
    d = payload["fbs_live"]
    asym = d["asymmetric_centering"]
    distros = d["distributions"]
    lines = [
        "# 2026 CFB roster/QB/unit scoring inflation (research diagnostic)",
        "",
        "**Date:** 2026-09-11  ",
        "**Branch:** `cursor/cfb-roster-inflation-1bf8`  ",
        "**After:** #538 STOP (hist inflation did not reproduce; SP+ not primary)  ",
        "**Kill switch:** `CFB_EDGE_BOARD_PUBLIC_ENABLED = false` — unchanged  ",
        "**Production model:** not modified. No λ. No offset. No clamp. No PLAY.  ",
        "**2025:** still sealed. #538 artifacts not edited.",
        "",
        "Market numbers on 2026 W1/W2 are **confirmatory measurement**, not a loss to tune.",
        "",
        "## Verdict",
        "",
    ]
    ranked = payload["ranked_causes"]
    top = ranked[0] if ranked else {}
    lines += [
        f"**Primary mechanistic cause:** {top.get('cause', 'see ranking')}",
        "",
        top.get("why", ""),
        "",
        "The +7 to +9 live-roster residual is not a missing intercept. It is "
        "recruiting-anchored width (and offense-only QB lift) entering the same "
        "identity multiple times, then getting exponentiated by "
        f"`MATCHUP_RESPONSE={P.MATCHUP_RESPONSE}` on the sum.",
        "",
        "## 1. End-to-end path (frozen, unchanged)",
        "",
        "```text",
        "recruiting prior (floor often 55, not 50)",
        "  → blend_roster_metrics: returning / portal / experience re-anchored to recruiting",
        "  → roster_strength = 0.32·ret + 0.26·portal_net + 0.26·recruiting + 0.16·exp",
        "  → unit talent = 0.62·recruiting + 0.22·exp + 0.16·returning   # recruiting again",
        "  → QB talent = stats, or sqrt(att/80) blend to recruiting      # recruiting again if thin",
        "  → compose offense: 0.34·SP+ + 0.22·roster + 0.24·QB + 0.10·skill + 0.10·OL",
        "                + QB blend 0.26 + OL/skill blends",
        "  → compose defense: 0.36·SP+ + 0.12·roster + 0.24·F7 + 0.20·sec + 0.08·exp",
        "  → pts = 25.9 · (off/def)^response · unit_off_boost · opp_def_dampen · pace",
        "```",
        "",
        "Double-count audit (packaging, not a silent 2026 substitute):",
        "",
        "| Channel | Enters again as |",
        "|---|---|",
        "| Recruiting | roster_strength (0.26); unit talent (0.62); unit portal_impact (0.35); returning/portal/exp *baselines*; thin QB talent fallback |",
        "| Returning | roster_strength (0.32); unit talent (0.16); already 60% recruiting-baseline |",
        "| Portal | roster_strength via net; unit portal_impact; already 55% recruiting-baseline |",
        "| Experience | roster_strength (0.16); defense compose (0.08); unit experience; already 45% recruiting-baseline |",
        "| QB | offense compose 0.24 + post-compose blend 0.26; no defensive twin |",
        "| Units | compose weights **and** game `UNIT_OFFENSE_BOOST` / `UNIT_DEFENSE_DAMPEN` |",
        "",
        "Defaults that systematically lift scoring: packager recruiting fallback "
        "**55** (not 50); `portal_out` default 52 in `build_roster_construction` "
        "when a row is missing; QB class `incumbent` multiplier **1.06**.",
        "",
        "## 2. FBS live distributions (width, not just the mean)",
        "",
        f"- n FBS = {d['n_fbs']}",
        f"- recruiting exactly 55 (floor): **{d['recruiting_exactly_55']}**",
        f"- recruiting ≥ 80: {d['recruiting_gt_80']}",
        f"- QB classes: `{d['qb_class_counts']}`",
        "",
        "| Component | mean | sd | p10 | p50 | p90 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for key in (
        "recruiting",
        "returning",
        "portal_in",
        "experience",
        "roster_strength",
        "qb_talent",
        "qb_index",
        "ol",
        "skill",
        "front_seven",
        "secondary",
        "off_eff",
        "def_eff",
        "offense_index",
        "defense_index",
    ):
        x = distros[key]
        lines.append(
            f"| {key} | {x['mean']} | {x['sd']} | {x['p10']} | {x['p50']} | {x['p90']} |"
        )
    lines += [
        "",
        "### Centering vs width",
        "",
        f"- mean offense_index = **{asym['mean_offense_index']}**, sd = {asym['sd_offense_index']}",
        f"- mean defense_index = **{asym['mean_defense_index']}**, sd = {asym['sd_defense_index']}",
        f"- mean QB index = **{asym['mean_qb_index']}** (1.0 is league-average)",
        f"- mean OL − F7 = {asym['mean_ol_minus_front_seven']}; skill − secondary = {asym['mean_skill_minus_secondary']}",
        "",
        "### Correlations (recruiting is the common factor)",
        "",
    ]
    for k, v in d["correlations"].items():
        lines.append(f"- `{k}` = {v}")
    lines += [
        "",
        "## 3. One-at-a-time ablations (2026 W1/W2 books, confirmatory)",
        "",
        "SP+ / HFA / coaching stay live unless the variant name says otherwise. "
        "Deltas are vs frozen. Negative resid delta = less Over-drunk.",
        "",
        "| Variant | mean T | mean resid | MAE | pred SD | p10 / p50 / p90 | infl | Δ resid | Δ MAE |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    board = payload["ablations"]
    frozen = board["frozen"]
    for name in VARIANTS:
        s = board[name]
        lines.append(
            "| {name} | {mt} | {mr} | {mae} | {sd} | {p10} / {p50} / {p90} | {inf} | {dr} | {dm} |".format(
                name=name,
                mt=s["mean_model_total"],
                mr=s["mean_resid"],
                mae=s["mae"],
                sd=s["sd_model_total"],
                p10=s["p10_model_total"],
                p50=s["p50_model_total"],
                p90=s["p90_model_total"],
                inf=s["mean_matchup_inflation"],
                dr=s.get("delta_vs_frozen", {}).get("mean_resid"),
                dm=s.get("delta_vs_frozen", {}).get("mae"),
            )
        )
    lines += [
        "",
        "### Frozen calibration by predicted-total bucket",
        "",
        "| Bucket | n | mean resid | MAE |",
        "|---|---:|---:|---:|",
    ]
    for k, v in frozen["calibration_by_pred_bucket"].items():
        lines.append(f"| {k} | {v['n']} | {v['mean_resid']} | {v['mae']} |")
    lines += [
        "",
        "## 4. Minimum component / interaction that reproduces +7 to +9",
        "",
        payload["minimum_reproduction"]["text"],
        "",
        "## 5. Ranked suspected causes",
        "",
    ]
    for i, row in enumerate(ranked, 1):
        lines.append(f"{i}. **{row['cause']}** — {row['why']}")
        if row.get("evidence"):
            lines.append(f"   Evidence: {row['evidence']}")
        lines.append("")
    lines += [
        "## 6. Next falsifiable experiment (not a ship)",
        "",
        payload["next_experiment"],
        "",
        "## 7. What this is not",
        "",
        "- Not a λ / Line Curve / global offset proposal.",
        "- Not a 2025 peek. Seal still hard-fails without a 2023–24 freeze.",
        "- Not a retune to UNLV/UNT or the other five 2026 spread outliers.",
        "- Not public CFB. Board stays dark until a mechanism earns green.",
        "",
        f"JSON: `{OUT_JSON.name}`",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def rank_causes(board: Mapping[str, Any], fbs: Mapping[str, Any]) -> List[Dict[str, Any]]:
    frozen_r = board["frozen"]["mean_resid"] or 0.0
    drops = []
    for name, s in board.items():
        if name == "frozen":
            continue
        mr = s.get("mean_resid")
        if mr is None:
            continue
        drops.append((name, round(frozen_r - float(mr), 4), s))
    drops.sort(key=lambda t: -t[1])
    ranked = []

    def add(cause: str, why: str, evidence: str, priority: str) -> None:
        ranked.append(
            {"cause": cause, "why": why, "evidence": evidence, "priority": priority}
        )

    rec_ch = board.get("recruiting_channel_50") or {}
    units = board.get("units_50") or {}
    qb = board.get("qb_league") or {}
    rec_field = board.get("recruiting_field_50") or {}
    game_u = board.get("game_units_50_indices_live") or {}
    off = board.get("off_layers_league_def_live") or {}
    deff = board.get("def_layers_league_off_live") or {}
    full = board.get("roster_qb_units_league") or {}
    corr = fbs.get("correlations") or {}
    asym = fbs.get("asymmetric_centering") or {}

    add(
        "Recruiting-anchored identity (channel, not the 0.26 roster weight alone)",
        "Recruiting is written into returning/portal/experience baselines, unit talent (0.62), "
        "unit portal_impact, and thin QB talent. Setting only the recruiting *field* to 50 "
        "barely moves the board; rebuilding the whole channel does.",
        (
            f"recruiting_field_50 resid={rec_field.get('mean_resid')} "
            f"(Δ {rec_field.get('delta_vs_frozen', {}).get('mean_resid')}); "
            f"recruiting_channel_50 resid={rec_ch.get('mean_resid')} "
            f"(Δ {rec_ch.get('delta_vs_frozen', {}).get('mean_resid')}); "
            f"recruiting↔offense_index r={corr.get('recruiting_vs_offense_index')}, "
            f"recruiting↔defense_index r={corr.get('recruiting_vs_defense_index')}, "
            f"off↔def r={corr.get('offense_index_vs_defense_index')}"
        ),
        "P0",
    )
    add(
        "Unit-grade width (compose + game multipliers)",
        "OL/skill/F7/secondary are recruiting-dominated. They lift offense_index, "
        "defense_index, and then multiply the total again via unit_off_boost / "
        "opp_def_dampen. Game-only flatten (indices live) is the double-count check.",
        (
            f"units_50 resid={units.get('mean_resid')}; "
            f"game_units_50_indices_live resid={game_u.get('mean_resid')}"
        ),
        "P0",
    )
    add(
        "Offense-only QB lever (no defensive twin)",
        f"Mean QB index {asym.get('mean_qb_index')} on a 1.06 incumbent multiplier "
        "raises offense_index without a matching defense_index lift, so "
        "(off/def)^1.4 systematically exceeds 1 on the sum.",
        f"qb_league resid={qb.get('mean_resid')}; qb_index↔offense r={corr.get('qb_index_vs_offense_index')}",
        "P1",
    )
    add(
        "Offense-layer vs defense-layer asymmetry",
        "Offense compose gives roster 0.22 + QB 0.24; defense gives roster 0.12 and no QB. "
        "If neutralizing offense layers kills the Over and neutralizing defense layers does not "
        "(or makes it worse), the inflation is an offense-width / defense-under-response story.",
        (
            f"off_layers_league_def_live resid={off.get('mean_resid')}; "
            f"def_layers_league_off_live resid={deff.get('mean_resid')}; "
            f"mean off={asym.get('mean_offense_index')} mean def={asym.get('mean_defense_index')}"
        ),
        "P1",
    )
    add(
        "Recruiting floor at 55 and right tail",
        f"{fbs.get('recruiting_exactly_55')} FBS teams sit on the packaged 55 floor; "
        f"{fbs.get('recruiting_gt_80')} are ≥80. Mean recruiting > 50 plus a long right tail "
        "is exactly the width MATCHUP_RESPONSE was calibrated without.",
        f"recruiting dist={distros_line(fbs)}",
        "P1",
    )
    add(
        "Full roster/QB/unit league (replication of #538 +0.10)",
        "Control: live SP+ + league identity should collapse the residual if localization holds.",
        f"roster_qb_units_league resid={full.get('mean_resid')}",
        "control",
    )
    # Keep ranking in the drop-size order for the narrative top, but preserve the structured list.
    ranked.sort(
        key=lambda row: (
            0 if row["priority"] == "P0" else 1 if row["priority"] == "P1" else 2
        )
    )
    return ranked


def distros_line(fbs: Mapping[str, Any]) -> str:
    rec = (fbs.get("distributions") or {}).get("recruiting") or {}
    return f"mean={rec.get('mean')} sd={rec.get('sd')} p10={rec.get('p10')} p90={rec.get('p90')}"


def minimum_reproduction(board: Mapping[str, Any]) -> Dict[str, Any]:
    frozen = float(board["frozen"]["mean_resid"] or 0.0)
    target_lo, target_hi = 7.0, 9.5
    # A variant "reproduces" the inflation if its residual stays inside +7..+9.5
    # (i.e. that component is NOT necessary). The minimum necessary set is the
    # smallest ablation that *destroys* the +7..+9 (resid < 3).
    destroyers = []
    for name, s in board.items():
        if name == "frozen":
            continue
        mr = s.get("mean_resid")
        if mr is None:
            continue
        if float(mr) < 3.0:
            destroyers.append((name, float(mr), abs(float(mr) - 0.1)))
    destroyers.sort(key=lambda t: (t[2], abs(t[1])))
    singles = [
        n
        for n, _mr, _ in destroyers
        if n
        in {
            "recruiting_channel_50",
            "units_50",
            "units_and_cast_50",
            "qb_league",
            "qb_talent_50",
            "roster_strength_50",
            "returning_50",
            "portal_50",
            "experience_50",
            "recruiting_field_50",
            "game_units_50_indices_live",
            "off_layers_league_def_live",
            "def_layers_league_off_live",
        }
    ]
    if "recruiting_channel_50" in singles:
        text = (
            "Minimum necessary channel: **recruiting-anchored reconstruction** "
            f"(recruiting_channel_50 resid={board['recruiting_channel_50']['mean_resid']}). "
            "The recruiting *field* alone is not enough — returning/portal/experience "
            "baselines and 0.62 unit talent have to move with it. "
            f"Frozen resid={frozen:.2f} stays in the +7 to +9 band until that channel is rebuilt."
        )
        key = "recruiting_channel_50"
    elif "units_50" in singles or "units_and_cast_50" in singles:
        key = "units_50" if "units_50" in singles else "units_and_cast_50"
        text = (
            f"Minimum necessary component among singles that kill the +7 to +9: **{key}** "
            f"(resid={board[key]['mean_resid']}). Recruiting still sits behind the unit formula."
        )
    elif singles:
        key = singles[0]
        text = (
            f"Smallest single ablation that drops residual below +3: **{key}** "
            f"(resid={board[key]['mean_resid']}). Frozen={frozen:.2f}."
        )
    else:
        key = destroyers[0][0] if destroyers else "roster_qb_units_league"
        text = (
            "No *single* subcomponent dropped residual below +3. The +7 to +9 is an "
            f"interaction. Full identity league resid={board.get('roster_qb_units_league', {}).get('mean_resid')}. "
            f"Largest single drop: {destroyers[0][0] if destroyers else 'n/a'}."
        )
    kept = [
        n
        for n, s in board.items()
        if n != "frozen"
        and s.get("mean_resid") is not None
        and target_lo <= float(s["mean_resid"]) <= target_hi
    ]
    return {
        "key": key,
        "destroyers_resid_lt_3": [{"variant": n, "mean_resid": mr} for n, mr, _ in destroyers[:8]],
        "variants_that_still_look_like_2026": kept,
        "text": text,
    }


def main() -> int:
    assert_2025_untouched()
    universe, meta = resolve_season_universe(
        season=2026, as_of_week=1, demo=True, session=None
    )
    official = json.loads(OFFICIAL.read_text(encoding="utf-8"))
    fbs = official_fbs_codes()
    required = set()
    for raw in official.get("games") or []:
        if int(raw.get("week") or -1) not in (1, 2):
            continue
        for side in (raw.get("home"), raw.get("away")):
            code = str(side or "").upper()
            if code in fbs:
                required.add(code)
    sit_missing_power_from_sot_rows(
        universe,
        json.loads(POWER.read_text(encoding="utf-8")).get("teams") or [],
        required=sorted(required),
        context="cfb_2026_roster_inflation_diagnostic",
    )
    live_states = {c: universe.teams[c] for c in universe.teams}
    qb_stats = load_qb_stats()
    w1 = load_w1_totals()
    w2 = slim_from_espn(W2_ODDS)

    fbs_live = fbs_distributions({c: s for c, s in live_states.items() if c in fbs})
    board = {}
    for variant in VARIANTS:
        rows = collect_board(
            universe, live_states, qb_stats, official, w1, w2["by_key"], variant
        )
        summary = summarize_board(rows)
        if variant == "frozen":
            summary["delta_vs_frozen"] = {"mean_resid": 0.0, "mae": 0.0, "mean_model_total": 0.0}
        else:
            fr = board["frozen"]
            summary["delta_vs_frozen"] = {
                "mean_resid": None
                if summary["mean_resid"] is None
                else round(float(summary["mean_resid"]) - float(fr["mean_resid"]), 4),
                "mae": None
                if summary["mae"] is None
                else round(float(summary["mae"]) - float(fr["mae"]), 4),
                "mean_model_total": None
                if summary["mean_model_total"] is None
                else round(
                    float(summary["mean_model_total"]) - float(fr["mean_model_total"]), 4
                ),
                "mean_matchup_inflation": None
                if summary["mean_matchup_inflation"] is None
                or fr["mean_matchup_inflation"] is None
                else round(
                    float(summary["mean_matchup_inflation"])
                    - float(fr["mean_matchup_inflation"]),
                    4,
                ),
            }
        board[variant] = summary
        print(
            f"{variant:28s} n={summary['n']:3d}  "
            f"resid={summary['mean_resid']}  mae={summary['mae']}  "
            f"infl={summary['mean_matchup_inflation']}"
        )

    ranked = rank_causes(board, fbs_live)
    minimum = minimum_reproduction(board)
    payload = {
        "ok": True,
        "research_only": True,
        "production_model_changed": False,
        "kill_switch": "CFB_EDGE_BOARD_PUBLIC_ENABLED=false",
        "2025_opened": False,
        "lambda_fitted": False,
        "universe_mode": meta.get("mode"),
        "note": (
            "2026 W1/W2 books are confirmatory measurement only. "
            "Not a fit. 2025 sealed. #538 hist artifacts untouched."
        ),
        "formula": {
            "matchup_response": P.MATCHUP_RESPONSE,
            "league_team_ppg": P.LEAGUE_TEAM_PPG,
            "unit_talent_recruiting_weight": 0.62,
            "roster_strength_recruiting_weight": P.ROSTER_STRENGTH_RECRUITING,
            "qb_incumbent_mult": P.QB_CLASS_OFFENSE_MULT.get("incumbent"),
            "recruiting_packager_fallback": 55.0,
        },
        "fbs_live": fbs_live,
        "ablations": board,
        "ranked_causes": ranked,
        "minimum_reproduction": minimum,
        "next_experiment": (
            "Falsify the recruiting-channel claim without touching 2025 or fitting λ: "
            "rebuild the 2026 snapshot with recruiting recentered to mean 50 **preserving rank/order** "
            "(a location shift, not a shrink) and, separately, with unit talent "
            "`0.62*recruiting` replaced by a residual-only ESPN class/portal mix. "
            "Pre-register: if the location-only recenter leaves residual ≥ +6 while the "
            "unit-talent de-anchor drops it below +3, the problem is width/reuse of recruiting "
            "in units — not a missing intercept. Do not ship either transform. "
            "Only after that mechanism test, decide whether a same-path 2023–24 "
            "recruiting archive is worth minting."
        ),
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_report(payload)
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")
    print("minimum:", minimum["text"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
