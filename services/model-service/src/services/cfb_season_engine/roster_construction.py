"""Layer 1 — Roster construction (the real CFB foundation).

Returning production, portal in/out, recruiting capital, and experience
distribution. Historical team strength is a *weak* prior here; 2026
identity is rebuilt from how the roster was assembled.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from src.services.cfb_season_engine.types import RosterConstruction


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, float(value)))


def continuity_from_components(
    returning_production: float,
    portal_in_score: float,
    portal_out_score: float,
    experience_index: float,
) -> float:
    """Derive a continuity score from churn components (approximate)."""
    # High returning + low portal-out → continuity; portal-in helps talent
    # but *reduces* continuity (new scheme/chemistry).
    base = 0.55 * returning_production + 0.25 * experience_index
    churn_penalty = 0.35 * portal_out_score + 0.15 * max(0.0, portal_in_score - 40.0)
    return _clamp(base - 0.35 * churn_penalty + 35.0)


def build_roster_construction(
    team: str,
    payload: Optional[Mapping[str, Any]] = None,
    *,
    default_source: str = "packaged_prior",
) -> RosterConstruction:
    """Build Layer 1 for one team from a payload or league-average defaults."""
    p = dict(payload or {})
    returning = _clamp(p.get("returning_production", 48.0))
    portal_in = _clamp(p.get("portal_in_score", 50.0))
    portal_out = _clamp(p.get("portal_out_score", 52.0))
    recruiting = _clamp(p.get("recruiting_capital", 50.0))
    experience = _clamp(p.get("experience_index", 50.0))
    continuity = p.get("continuity_score")
    if continuity is None:
        continuity = continuity_from_components(
            returning, portal_in, portal_out, experience
        )
    fidelity = str(p.get("fidelity", "approximate"))
    if fidelity not in ("real", "approximate", "placeholder"):
        fidelity = "approximate"
    return RosterConstruction(
        team=str(team),
        returning_production=returning,
        portal_in_score=portal_in,
        portal_out_score=portal_out,
        recruiting_capital=recruiting,
        experience_index=experience,
        continuity_score=_clamp(continuity),
        source=str(p.get("source", default_source)),
        fidelity=fidelity,  # type: ignore[arg-type]
        notes=str(p.get("notes", "")),
    )


def roster_to_dict(roster: RosterConstruction) -> Dict[str, Any]:
    return {
        "team": roster.team,
        "returning_production": round(roster.returning_production, 2),
        "portal_in_score": round(roster.portal_in_score, 2),
        "portal_out_score": round(roster.portal_out_score, 2),
        "recruiting_capital": round(roster.recruiting_capital, 2),
        "experience_index": round(roster.experience_index, 2),
        "continuity_score": round(roster.continuity_score, 2),
        "source": roster.source,
        "fidelity": roster.fidelity,
        "notes": roster.notes,
    }


def documentation() -> Dict[str, Any]:
    return {
        "layer": 1,
        "name": "roster_construction",
        "module": "src.services.cfb_season_engine.roster_construction",
        "real_vs_approximate": (
            "Packaged 2026 FBS priors are APPROXIMATE. Live portal/returning "
            "production feeds are a gap — do not treat continuity scores as "
            "measured SNAP% returning."
        ),
        "fields": [
            "returning_production",
            "portal_in_score",
            "portal_out_score",
            "recruiting_capital",
            "experience_index",
            "continuity_score",
        ],
    }
