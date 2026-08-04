"""Layer 3 — Position group grades (OL, skill, front seven, secondary).

Each unit grade is an inspectable composite of talent, experience, and
portal impact. Packaged headline scores remain the talent prior when
present; thin/placeholder rows get distinct unit fills from roster context
so units are never a flat 50 across the board.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Tuple

from src.services.cfb_season_engine import priors as P
from src.services.cfb_season_engine.types import PositionGroupGrades, QbSituation, RosterConstruction

UNIT_KEYS = ("ol", "skill", "front_seven", "secondary")


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, float(value)))


def compose_unit_grade(
    *,
    talent: float,
    experience: float,
    portal_impact: float,
) -> Tuple[float, Dict[str, float]]:
    """Transparent unit grade from inspectable components."""
    w_t = P.UNIT_TALENT_WEIGHT
    w_e = P.UNIT_EXPERIENCE_WEIGHT
    w_p = P.UNIT_PORTAL_WEIGHT
    grade = _clamp(w_t * talent + w_e * experience + w_p * portal_impact)
    breakdown = {
        "talent": round(_clamp(talent), 2),
        "experience": round(_clamp(experience), 2),
        "portal_impact": round(_clamp(portal_impact), 2),
        "grade": round(grade, 2),
        "weights": {
            "talent": w_t,
            "experience": w_e,
            "portal_impact": w_p,
        },
    }
    return grade, breakdown


def _roster_defaults(roster: Optional[RosterConstruction]) -> Dict[str, float]:
    if roster is None:
        return {
            "recruiting": 50.0,
            "experience": 50.0,
            "portal_in": 50.0,
            "returning": 50.0,
            "continuity": 50.0,
        }
    return {
        "recruiting": float(roster.recruiting_class_score),
        "experience": float(roster.experience_index),
        "portal_in": float(roster.portal_in_value),
        "returning": float(roster.returning_production),
        "continuity": float(roster.continuity_score),
    }


def _derive_unit_components(
    unit: str,
    *,
    headline: Optional[float],
    unit_payload: Mapping[str, Any],
    roster: Optional[RosterConstruction],
    qb: Optional[QbSituation],
) -> Tuple[float, float, float, float, str]:
    """Return talent, experience, portal_impact, grade, fill_mode."""
    rd = _roster_defaults(roster)
    # Unit-specific soft fills when headline missing (distinct inputs).
    if unit == "ol":
        soft_talent = qb.ol_support if qb else rd["recruiting"]
        soft_exp = 0.55 * rd["experience"] + 0.45 * rd["continuity"]
        soft_portal = 0.40 * rd["portal_in"] + 0.60 * rd["returning"]
        soft_grade = (
            0.40 * float(soft_talent)
            + 0.35 * soft_exp
            + 0.25 * soft_portal
        )
    elif unit == "skill":
        soft_talent = qb.weapons_support if qb else rd["recruiting"]
        soft_exp = 0.45 * rd["experience"] + 0.55 * rd["returning"]
        soft_portal = 0.55 * rd["portal_in"] + 0.45 * rd["recruiting"]
        soft_grade = (
            0.45 * float(soft_talent)
            + 0.25 * soft_exp
            + 0.30 * soft_portal
        )
    elif unit == "front_seven":
        soft_talent = 0.55 * rd["recruiting"] + 0.45 * rd["returning"]
        soft_exp = 0.60 * rd["experience"] + 0.40 * rd["returning"]
        soft_portal = 0.50 * rd["portal_in"] + 0.50 * rd["recruiting"]
        soft_grade = 0.40 * soft_talent + 0.35 * soft_exp + 0.25 * soft_portal
    else:  # secondary
        soft_talent = 0.50 * rd["recruiting"] + 0.50 * rd["portal_in"]
        soft_exp = 0.50 * rd["experience"] + 0.50 * rd["returning"]
        soft_portal = 0.60 * rd["portal_in"] + 0.40 * rd["recruiting"]
        soft_grade = 0.40 * soft_talent + 0.30 * soft_exp + 0.30 * soft_portal

    # Explicit component payload wins when present.
    comps = unit_payload.get("components") if isinstance(unit_payload.get("components"), Mapping) else {}
    if not isinstance(comps, Mapping):
        comps = {}
    # Also accept flat ol_talent / ol_experience / ol_portal_impact keys.
    talent_key = f"{unit}_talent"
    exp_key = f"{unit}_experience"
    portal_key = f"{unit}_portal_impact"

    talent_raw = comps.get("talent", unit_payload.get(talent_key))
    exp_raw = comps.get("experience", unit_payload.get(exp_key))
    portal_raw = comps.get("portal_impact", unit_payload.get(portal_key))

    has_components = talent_raw is not None or exp_raw is not None or portal_raw is not None

    if has_components:
        talent = _clamp(talent_raw if talent_raw is not None else soft_talent)
        experience = _clamp(exp_raw if exp_raw is not None else soft_exp)
        portal_impact = _clamp(portal_raw if portal_raw is not None else soft_portal)
        grade, _ = compose_unit_grade(
            talent=talent, experience=experience, portal_impact=portal_impact
        )
        # Explicit headline override keeps curated unit scores authoritative.
        if headline is not None:
            grade = _clamp(headline)
        return talent, experience, portal_impact, grade, "components"

    if headline is not None:
        # Decompose packaged headline into inspectable components that
        # recompose near the headline (talent anchored on the grade).
        grade = _clamp(headline)
        talent = grade
        experience = _clamp(0.65 * rd["experience"] + 0.35 * grade)
        portal_impact = _clamp(0.55 * rd["portal_in"] + 0.45 * grade)
        return talent, experience, portal_impact, grade, "headline_decompose"

    # Thin / missing — soft fill from roster/QB (distinct by unit).
    talent = _clamp(soft_talent)
    experience = _clamp(soft_exp)
    portal_impact = _clamp(soft_portal)
    grade, _ = compose_unit_grade(
        talent=talent, experience=experience, portal_impact=portal_impact
    )
    # Prefer soft_grade blend for thin fills so units diverge.
    grade = _clamp(0.70 * grade + 0.30 * soft_grade)
    return talent, experience, portal_impact, grade, "roster_soft_fill"


def _thin_flat_headlines(payload: Mapping[str, Any]) -> bool:
    """True when packaged unit rows are a flat placeholder (all equal / all ~50)."""
    fidelity = str(payload.get("fidelity", "approximate"))
    vals = []
    for unit in UNIT_KEYS:
        raw = payload.get(unit)
        if isinstance(raw, Mapping):
            raw = raw.get("grade")
        if raw is None:
            continue
        vals.append(float(raw))
    if not vals:
        return True
    if fidelity == "placeholder" and (max(vals) - min(vals) < 0.5):
        return True
    if fidelity == "placeholder" and all(abs(v - 50.0) < 0.5 for v in vals):
        return True
    return False


def build_position_groups(
    team: str,
    payload: Optional[Mapping[str, Any]] = None,
    *,
    roster: Optional[RosterConstruction] = None,
    qb: Optional[QbSituation] = None,
    default_source: str = "packaged_prior",
) -> PositionGroupGrades:
    """Build Layer 3 grades with inspectable talent/experience/portal components."""
    p = dict(payload or {})
    nested = p.get("units") if isinstance(p.get("units"), Mapping) else {}
    thin_flat = _thin_flat_headlines(p)

    components: Dict[str, Dict[str, Any]] = {}
    grades: Dict[str, float] = {}
    fill_modes: Dict[str, str] = {}

    for unit in UNIT_KEYS:
        unit_payload: Dict[str, Any] = {}
        if isinstance(nested.get(unit), Mapping):
            unit_payload.update(dict(nested[unit]))  # type: ignore[arg-type]
        # Flat packaged shape: {"ol": 90, "ol_talent": 92, ...}
        if unit in p and not isinstance(p.get(unit), Mapping):
            unit_payload.setdefault("grade", p.get(unit))
        elif isinstance(p.get(unit), Mapping):
            unit_payload.update(dict(p[unit]))  # type: ignore[index]
        for suffix in ("talent", "experience", "portal_impact"):
            flat_key = f"{unit}_{suffix}"
            if flat_key in p and suffix not in unit_payload:
                unit_payload[suffix] = p[flat_key]
        if "components" in p and isinstance(p["components"], Mapping):
            unit_comps = p["components"].get(unit)
            if isinstance(unit_comps, Mapping):
                unit_payload["components"] = unit_comps

        headline = unit_payload.get("grade", p.get(unit) if not isinstance(p.get(unit), Mapping) else None)
        # Flat placeholder 50s are not authoritative — soft-fill distinct units.
        if thin_flat:
            headline = None
        talent, experience, portal_impact, grade, mode = _derive_unit_components(
            unit,
            headline=float(headline) if headline is not None else None,
            unit_payload=unit_payload,
            roster=roster,
            qb=qb,
        )
        _, breakdown = compose_unit_grade(
            talent=talent, experience=experience, portal_impact=portal_impact
        )
        # Keep headline/soft grade as the projection input; components remain inspectable.
        breakdown["grade"] = round(grade, 2)
        breakdown["fill_mode"] = mode  # type: ignore[assignment]
        components[unit] = {
            "talent": breakdown["talent"],
            "experience": breakdown["experience"],
            "portal_impact": breakdown["portal_impact"],
            "grade": breakdown["grade"],
            "weights": breakdown["weights"],  # type: ignore[dict-item]
        }
        grades[unit] = grade
        fill_modes[unit] = mode

    st_raw = p.get("special_teams", 50.0)
    if isinstance(st_raw, Mapping):
        st = _clamp(st_raw.get("grade", 50.0))
    else:
        st = _clamp(st_raw)

    fidelity = str(p.get("fidelity", "approximate"))
    if fidelity not in ("real", "approximate", "placeholder"):
        fidelity = "approximate"
    # Soft-filled units without packaged headlines are closer to placeholder.
    if all(m == "roster_soft_fill" for m in fill_modes.values()) and fidelity == "approximate":
        fidelity = "placeholder"

    notes = str(p.get("notes", ""))
    if not notes:
        notes = (
            "unit_grade = 0.50*talent + 0.30*experience + 0.20*portal_impact; "
            "packaged headline is authoritative when present"
        )

    return PositionGroupGrades(
        team=str(team),
        ol=round(grades["ol"], 2),
        skill=round(grades["skill"], 2),
        front_seven=round(grades["front_seven"], 2),
        secondary=round(grades["secondary"], 2),
        special_teams=round(st, 2),
        components=components,
        source=str(p.get("source", default_source)),
        fidelity=fidelity,  # type: ignore[arg-type]
        notes=notes,
    )


def groups_to_dict(groups: PositionGroupGrades) -> Dict[str, Any]:
    return {
        "team": groups.team,
        "ol": round(groups.ol, 2),
        "skill": round(groups.skill, 2),
        "front_seven": round(groups.front_seven, 2),
        "secondary": round(groups.secondary, 2),
        "special_teams": round(groups.special_teams, 2),
        "components": {
            unit: {
                "talent": comps.get("talent"),
                "experience": comps.get("experience"),
                "portal_impact": comps.get("portal_impact"),
                "grade": comps.get("grade"),
                "weights": comps.get("weights"),
            }
            for unit, comps in (groups.components or {}).items()
        },
        "source": groups.source,
        "fidelity": groups.fidelity,
        "notes": groups.notes,
    }


def unit_grade_breakdown(groups: PositionGroupGrades) -> Dict[str, Any]:
    """Status/diagnostics helper — inspectable unit components + weights."""
    return {
        "formula": (
            f"unit_grade = {P.UNIT_TALENT_WEIGHT}*talent + "
            f"{P.UNIT_EXPERIENCE_WEIGHT}*experience + "
            f"{P.UNIT_PORTAL_WEIGHT}*portal_impact"
        ),
        "units": groups_to_dict(groups),
        "headline": {
            "ol": groups.ol,
            "skill": groups.skill,
            "front_seven": groups.front_seven,
            "secondary": groups.secondary,
            "special_teams": groups.special_teams,
        },
        "fidelity": groups.fidelity,
    }


def documentation() -> Dict[str, Any]:
    return {
        "layer": 3,
        "name": "position_groups",
        "module": "src.services.cfb_season_engine.position_groups",
        "units": ["ol", "skill", "front_seven", "secondary", "special_teams"],
        "formula": (
            f"unit_grade = {P.UNIT_TALENT_WEIGHT}*talent + "
            f"{P.UNIT_EXPERIENCE_WEIGHT}*experience + "
            f"{P.UNIT_PORTAL_WEIGHT}*portal_impact"
        ),
        "component_keys": ["talent", "experience", "portal_impact"],
        "real_vs_approximate": (
            "Unit grade *structure* and component weights are REAL/inspectable. "
            "Packaged talent composites are APPROXIMATE. Soft fills from roster/QB "
            "when unit rows are missing are PLACEHOLDER bridges. Special teams are thin."
        ),
    }
