"""Layer 3 — Position group grades (OL, skill, front seven, secondary)."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from src.services.cfb_season_engine.types import PositionGroupGrades, QbSituation, RosterConstruction


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, float(value)))


def build_position_groups(
    team: str,
    payload: Optional[Mapping[str, Any]] = None,
    *,
    roster: Optional[RosterConstruction] = None,
    qb: Optional[QbSituation] = None,
    default_source: str = "packaged_prior",
) -> PositionGroupGrades:
    """Build Layer 3 grades, optionally informed by roster/QB context."""
    p = dict(payload or {})
    ol = p.get("ol")
    skill = p.get("skill")
    front = p.get("front_seven")
    secondary = p.get("secondary")
    st = _clamp(p.get("special_teams", 50.0))

    # Soft fills from roster/QB when unit grades missing (approximate).
    if ol is None:
        ol = (qb.ol_support if qb else 50.0)
        if roster:
            ol = 0.6 * float(ol) + 0.4 * roster.experience_index
    if skill is None:
        skill = (qb.weapons_support if qb else 50.0)
        if roster:
            skill = (
                0.55 * float(skill)
                + 0.25 * roster.recruiting_class_score
                + 0.20 * roster.portal_in_value
            )
    if front is None:
        front = 50.0
        if roster:
            front = (
                0.4 * roster.recruiting_class_score
                + 0.35 * roster.returning_production
                + 0.25 * roster.experience_index
            )
    if secondary is None:
        secondary = 50.0
        if roster:
            secondary = (
                0.35 * roster.recruiting_class_score
                + 0.35 * roster.returning_production
                + 0.30 * roster.portal_in_value
            )

    fidelity = str(p.get("fidelity", "approximate"))
    if fidelity not in ("real", "approximate", "placeholder"):
        fidelity = "approximate"
    return PositionGroupGrades(
        team=str(team),
        ol=_clamp(ol),
        skill=_clamp(skill),
        front_seven=_clamp(front),
        secondary=_clamp(secondary),
        special_teams=st,
        source=str(p.get("source", default_source)),
        fidelity=fidelity,  # type: ignore[arg-type]
        notes=str(p.get("notes", "")),
    )


def groups_to_dict(groups: PositionGroupGrades) -> Dict[str, Any]:
    return {
        "team": groups.team,
        "ol": round(groups.ol, 2),
        "skill": round(groups.skill, 2),
        "front_seven": round(groups.front_seven, 2),
        "secondary": round(groups.secondary, 2),
        "special_teams": round(groups.special_teams, 2),
        "source": groups.source,
        "fidelity": groups.fidelity,
        "notes": groups.notes,
    }


def documentation() -> Dict[str, Any]:
    return {
        "layer": 3,
        "name": "position_groups",
        "module": "src.services.cfb_season_engine.position_groups",
        "units": ["ol", "skill", "front_seven", "secondary", "special_teams"],
        "real_vs_approximate": (
            "Packaged unit grades are APPROXIMATE talent composites. Soft fills "
            "from roster/QB context are PLACEHOLDER bridges when unit rows missing."
        ),
    }
