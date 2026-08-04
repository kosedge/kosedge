"""Layer 1 — Roster construction (the real CFB foundation).

Returning production (snap/start weighted), portal in/out net, recruiting
capital, and experience distribution compose into an inspectable
``roster_strength`` signal. Historical team strength is a *weak* prior;
2026 identity is rebuilt from how the roster was assembled.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Tuple

from src.services.cfb_season_engine import priors as P
from src.services.cfb_season_engine.types import RosterConstruction


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, float(value)))


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def returning_production_from_shares(
    returning_snap_share: float,
    returning_start_share: float,
) -> float:
    """Snap-weighted returning production (0–100).

    Starts matter, but snaps better reflect true production returning —
    a backup who started once is not equal to a 700-snap starter.
    """
    snap = _clamp01(returning_snap_share)
    start = _clamp01(returning_start_share)
    return _clamp(
        100.0
        * (
            P.ROSTER_SNAP_WEIGHT * snap
            + P.ROSTER_START_WEIGHT * start
        )
    )


def portal_net_value(portal_in_value: float, portal_out_value: float) -> float:
    """Net portal residual on 0–100 scale (inspectable).

    Outflow is weighted slightly less than 1:1 so elite inbound classes can
    still show net positive even with moderate churn.
    """
    pin = _clamp(portal_in_value)
    pout = _clamp(portal_out_value)
    return _clamp(pin - P.ROSTER_PORTAL_OUT_WEIGHT * pout + P.ROSTER_PORTAL_NET_OFFSET)


def continuity_from_components(
    returning_production: float,
    portal_in_value: float,
    portal_out_value: float,
    experience_index: float,
) -> float:
    """Derive a continuity score from churn components (approximate)."""
    # High returning + low portal-out → continuity; portal-in helps talent
    # but *reduces* continuity (new scheme/chemistry).
    base = 0.55 * returning_production + 0.25 * experience_index
    churn_penalty = 0.35 * portal_out_value + 0.15 * max(0.0, portal_in_value - 40.0)
    return _clamp(base - 0.35 * churn_penalty + 35.0)


def compute_roster_strength(
    *,
    returning_production: float,
    portal_net: float,
    recruiting_class_score: float,
    experience_index: float,
) -> Tuple[float, Dict[str, float]]:
    """Transparent weighted roster strength (0–100) + component breakdown."""
    w_ret = P.ROSTER_STRENGTH_RETURNING
    w_portal = P.ROSTER_STRENGTH_PORTAL_NET
    w_rec = P.ROSTER_STRENGTH_RECRUITING
    w_exp = P.ROSTER_STRENGTH_EXPERIENCE
    contrib = {
        "returning_production": round(w_ret * returning_production, 3),
        "portal_net": round(w_portal * portal_net, 3),
        "recruiting_class_score": round(w_rec * recruiting_class_score, 3),
        "experience_index": round(w_exp * experience_index, 3),
    }
    strength = _clamp(sum(contrib.values()))
    return strength, {
        **contrib,
        "weights": {
            "returning_production": w_ret,
            "portal_net": w_portal,
            "recruiting_class_score": w_rec,
            "experience_index": w_exp,
        },
        "roster_strength": round(strength, 3),
    }


def build_roster_construction(
    team: str,
    payload: Optional[Mapping[str, Any]] = None,
    *,
    default_source: str = "packaged_prior",
) -> RosterConstruction:
    """Build Layer 1 for one team from a payload or league-average defaults."""
    p = dict(payload or {})

    # Prefer explicit snap/start shares; fall back from returning_production.
    snap_raw = p.get("returning_snap_share")
    start_raw = p.get("returning_start_share")
    ret_raw = p.get("returning_production")

    if snap_raw is not None or start_raw is not None:
        snap = _clamp01(snap_raw if snap_raw is not None else (float(ret_raw or 50.0) / 100.0))
        start = _clamp01(start_raw if start_raw is not None else snap)
        returning = (
            _clamp(ret_raw)
            if ret_raw is not None
            else returning_production_from_shares(snap, start)
        )
    else:
        returning = _clamp(ret_raw if ret_raw is not None else 48.0)
        # Approximate shares from production (starts slightly stickier than snaps).
        snap = _clamp01(returning / 100.0)
        start = _clamp01(min(1.0, returning / 100.0 + 0.03))

    # Portal value fields (new) with back-compat to *_score keys.
    portal_in = _clamp(
        p.get("portal_in_value", p.get("portal_in_score", 50.0))
    )
    portal_out = _clamp(
        p.get("portal_out_value", p.get("portal_out_score", 52.0))
    )
    portal_net = p.get("portal_net")
    if portal_net is None:
        portal_net = portal_net_value(portal_in, portal_out)
    else:
        portal_net = _clamp(portal_net)

    recruiting = _clamp(
        p.get("recruiting_class_score", p.get("recruiting_capital", 50.0))
    )
    experience = _clamp(p.get("experience_index", 50.0))

    continuity = p.get("continuity_score")
    if continuity is None:
        continuity = continuity_from_components(
            returning, portal_in, portal_out, experience
        )

    strength_override = p.get("roster_strength")
    if strength_override is None:
        strength, _breakdown = compute_roster_strength(
            returning_production=returning,
            portal_net=float(portal_net),
            recruiting_class_score=recruiting,
            experience_index=experience,
        )
    else:
        strength = _clamp(strength_override)

    fidelity = str(p.get("fidelity", "approximate"))
    if fidelity not in ("real", "approximate", "placeholder"):
        fidelity = "approximate"

    return RosterConstruction(
        team=str(team),
        returning_production=returning,
        returning_snap_share=round(snap, 4),
        returning_start_share=round(start, 4),
        portal_in_value=portal_in,
        portal_out_value=portal_out,
        portal_net=round(float(portal_net), 2),
        recruiting_class_score=recruiting,
        experience_index=experience,
        continuity_score=_clamp(continuity),
        roster_strength=round(strength, 2),
        portal_in_score=portal_in,
        portal_out_score=portal_out,
        recruiting_capital=recruiting,
        source=str(p.get("source", default_source)),
        fidelity=fidelity,  # type: ignore[arg-type]
        notes=str(p.get("notes", "")),
    )


def roster_strength_breakdown(roster: RosterConstruction) -> Dict[str, Any]:
    """Inspectable component breakdown for diagnostics / status."""
    _strength, breakdown = compute_roster_strength(
        returning_production=roster.returning_production,
        portal_net=roster.portal_net,
        recruiting_class_score=roster.recruiting_class_score,
        experience_index=roster.experience_index,
    )
    return {
        "team": roster.team,
        "returning_snap_share": round(roster.returning_snap_share, 4),
        "returning_start_share": round(roster.returning_start_share, 4),
        "portal_in_value": round(roster.portal_in_value, 2),
        "portal_out_value": round(roster.portal_out_value, 2),
        "portal_net": round(roster.portal_net, 2),
        "recruiting_class_score": round(roster.recruiting_class_score, 2),
        "experience_index": round(roster.experience_index, 2),
        "continuity_score": round(roster.continuity_score, 2),
        "components": breakdown,
        "fidelity": roster.fidelity,
        "source": roster.source,
    }


def roster_to_dict(roster: RosterConstruction) -> Dict[str, Any]:
    return {
        "team": roster.team,
        "returning_production": round(roster.returning_production, 2),
        "returning_snap_share": round(roster.returning_snap_share, 4),
        "returning_start_share": round(roster.returning_start_share, 4),
        "portal_in_value": round(roster.portal_in_value, 2),
        "portal_out_value": round(roster.portal_out_value, 2),
        "portal_net": round(roster.portal_net, 2),
        "recruiting_class_score": round(roster.recruiting_class_score, 2),
        "experience_index": round(roster.experience_index, 2),
        "continuity_score": round(roster.continuity_score, 2),
        "roster_strength": round(roster.roster_strength, 2),
        # Back-compat aliases
        "portal_in_score": round(roster.portal_in_score, 2),
        "portal_out_score": round(roster.portal_out_score, 2),
        "recruiting_capital": round(roster.recruiting_capital, 2),
        "components": roster_strength_breakdown(roster)["components"],
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
            "Packaged 2026 FBS priors are APPROXIMATE curated/estimated "
            "composites — not measured SNAP% returning from a live feed. "
            "Formula structure (snap/start weighting, portal net, roster "
            "strength weights) is REAL and inspectable. Live portal/"
            "returning-production DB feeds remain a gap."
        ),
        "formula": {
            "returning_production": (
                f"{P.ROSTER_SNAP_WEIGHT}*returning_snap_share*100 + "
                f"{P.ROSTER_START_WEIGHT}*returning_start_share*100"
            ),
            "portal_net": (
                f"portal_in_value - {P.ROSTER_PORTAL_OUT_WEIGHT}*portal_out_value "
                f"+ {P.ROSTER_PORTAL_NET_OFFSET}"
            ),
            "roster_strength": (
                f"{P.ROSTER_STRENGTH_RETURNING}*returning_production + "
                f"{P.ROSTER_STRENGTH_PORTAL_NET}*portal_net + "
                f"{P.ROSTER_STRENGTH_RECRUITING}*recruiting_class_score + "
                f"{P.ROSTER_STRENGTH_EXPERIENCE}*experience_index"
            ),
        },
        "fields": [
            "returning_snap_share",
            "returning_start_share",
            "returning_production",
            "portal_in_value",
            "portal_out_value",
            "portal_net",
            "recruiting_class_score",
            "experience_index",
            "continuity_score",
            "roster_strength",
        ],
    }
