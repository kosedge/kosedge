"""Coaching continuity / change layer (CFB).

Explicitly models new HC, new OC, new DC, and returning staff.

Observed-pattern priors (approximate, transparent):
- New HC and new DC carry the largest early-season penalties.
- New OC is material but smaller than HC/DC.
- Strongest effect Weeks 1–4, then decays toward a small residual.
- Interacts with early-season uncertainty (extra identity noise).

Effects apply as:
1. Mild offense/defense index multipliers at compose time
2. Week-decayed point adjustments in expected points / season sim
3. Uncertainty boost blended into team early_season_uncertainty

Packaged staff flags are APPROXIMATE until live coaching feeds exist.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Tuple

from src.services.cfb_season_engine import priors as P
from src.services.cfb_season_engine.types import CoachingContinuity, DataFidelity

# Week → decay of the early coaching penalty (1.0 = full W1 hit).
WEEK_DECAY: Dict[int, float] = {
    1: 1.00,
    2: 0.85,
    3: 0.65,
    4: 0.45,
    5: 0.22,
    6: 0.14,
    7: 0.10,
    8: 0.08,
}

# Point-equivalent penalties at full early strength (week-1 scale).
# Applied as scoring drag on the team (offense & defense sides).
NEW_HC_OFFENSE_PENALTY = 1.35
NEW_HC_DEFENSE_PENALTY = 1.10
NEW_OC_OFFENSE_PENALTY = 0.75
NEW_DC_DEFENSE_PENALTY = 1.20
RETURNING_CONTINUITY_BONUS = 0.15  # tiny early boost if all three returning

# Index multipliers at compose (mild permanent disruption vs returning).
NEW_HC_OFF_INDEX = 0.965
NEW_HC_DEF_INDEX = 0.970
NEW_OC_OFF_INDEX = 0.980
NEW_DC_DEF_INDEX = 0.975

# Uncertainty boosts (0–1) blended into early_season_uncertainty.
NEW_HC_UNCERTAINTY = 0.18
NEW_OC_UNCERTAINTY = 0.08
NEW_DC_UNCERTAINTY = 0.14

# Curated 2026 staff-change flags (approximate / illustrative).
# Real depth charts lag — labeled approximate in packaged priors.
CURATED_STAFF: Dict[str, Dict[str, Any]] = {
    # Post-Franklin era — new HC is the headline continuity break.
    "PSU": {
        "new_hc": True,
        "new_oc": True,
        "new_dc": True,
        "hc_name": "new_hc_2026",
        "notes": "curated: new HC regime (largest early penalty)",
    },
    # Chip Kelly exit / new regime settling into 2026.
    "UCLA": {
        "new_hc": True,
        "new_oc": True,
        "new_dc": False,
        "hc_name": "new_hc_2026",
        "notes": "curated: new HC + OC",
    },
    # Portal-era rebuild with staff churn.
    "FSU": {
        "new_hc": False,
        "new_oc": True,
        "new_dc": True,
        "hc_name": "Mike Norvell",
        "notes": "curated: returning HC, new OC+DC",
    },
    "COLO": {
        "new_hc": False,
        "new_oc": True,
        "new_dc": False,
        "hc_name": "Deion Sanders",
        "notes": "curated: returning HC, new OC",
    },
    "MICH": {
        "new_hc": False,
        "new_oc": False,
        "new_dc": True,
        "hc_name": "Sherrone Moore",
        "notes": "curated: returning HC/OC, new DC",
    },
    "NEB": {
        "new_hc": True,
        "new_oc": True,
        "new_dc": True,
        "hc_name": "new_hc_2026",
        "notes": "curated: full staff reset",
    },
    "ARIZ": {
        "new_hc": True,
        "new_oc": True,
        "new_dc": True,
        "hc_name": "new_hc_2026",
        "notes": "curated: new HC regime",
    },
    # Stable continuity controls.
    "UGA": {
        "new_hc": False,
        "new_oc": False,
        "new_dc": False,
        "hc_name": "Kirby Smart",
        "notes": "curated: returning staff",
    },
    "ALA": {
        "new_hc": False,
        "new_oc": False,
        "new_dc": False,
        "hc_name": "Kalen DeBoer",
        "notes": "curated: returning HC (year-2 continuity)",
    },
    "ORE": {
        "new_hc": False,
        "new_oc": False,
        "new_dc": False,
        "hc_name": "Dan Lanning",
        "notes": "curated: returning staff",
    },
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def week_decay(week: int) -> float:
    w = int(week or 0)
    if w <= 0:
        return 1.0
    if w in WEEK_DECAY:
        return float(WEEK_DECAY[w])
    if w > 8:
        return 0.05
    return 0.08


def _flags_from_payload(raw: Mapping[str, Any]) -> Tuple[bool, bool, bool]:
    new_hc = bool(raw.get("new_hc", False))
    new_oc = bool(raw.get("new_oc", False))
    new_dc = bool(raw.get("new_dc", False))
    # Explicit returning_* can override.
    if "returning_hc" in raw:
        new_hc = not bool(raw["returning_hc"])
    if "returning_oc" in raw:
        new_oc = not bool(raw["returning_oc"])
    if "returning_dc" in raw:
        new_dc = not bool(raw["returning_dc"])
    return new_hc, new_oc, new_dc


def score_continuity(new_hc: bool, new_oc: bool, new_dc: bool) -> float:
    """0–100 continuity score (100 = all returning)."""
    score = 100.0
    if new_hc:
        score -= 40.0
    if new_dc:
        score -= 30.0
    if new_oc:
        score -= 20.0
    return _clamp(score, 0.0, 100.0)


def compute_penalties(
    new_hc: bool, new_oc: bool, new_dc: bool
) -> Dict[str, float]:
    """Week-1-scale penalties and index multipliers."""
    off_pts = 0.0
    def_pts = 0.0
    off_mult = 1.0
    def_mult = 1.0
    u_boost = 0.0

    if new_hc:
        off_pts += NEW_HC_OFFENSE_PENALTY
        def_pts += NEW_HC_DEFENSE_PENALTY
        off_mult *= NEW_HC_OFF_INDEX
        def_mult *= NEW_HC_DEF_INDEX
        u_boost += NEW_HC_UNCERTAINTY
    if new_oc:
        off_pts += NEW_OC_OFFENSE_PENALTY
        off_mult *= NEW_OC_OFF_INDEX
        u_boost += NEW_OC_UNCERTAINTY
    if new_dc:
        def_pts += NEW_DC_DEFENSE_PENALTY
        def_mult *= NEW_DC_DEF_INDEX
        u_boost += NEW_DC_UNCERTAINTY

    all_returning = not (new_hc or new_oc or new_dc)
    continuity_bonus = RETURNING_CONTINUITY_BONUS if all_returning else 0.0

    return {
        "offense_penalty_w1": round(off_pts, 3),
        "defense_penalty_w1": round(def_pts, 3),
        "offense_index_mult": round(off_mult, 4),
        "defense_index_mult": round(def_mult, 4),
        "uncertainty_boost": round(_clamp(u_boost, 0.0, 0.45), 4),
        "continuity_bonus_w1": round(continuity_bonus, 3),
    }


def build_coaching_continuity(
    team: str,
    payload: Optional[Mapping[str, Any]] = None,
) -> CoachingContinuity:
    """Build coaching continuity profile for ``team``."""
    team = str(team).upper()
    raw = dict(payload or {})
    fidelity: DataFidelity = "approximate"
    source = "packaged_prior"
    notes = ""

    if not raw and team in CURATED_STAFF:
        raw = dict(CURATED_STAFF[team])
        source = "curated_staff_proxy"
        fidelity = "approximate"
    elif not raw:
        # Default: assume returning staff (continuity), placeholder fidelity
        # for non-curated teams — honest that we did not invent a change.
        raw = {"new_hc": False, "new_oc": False, "new_dc": False}
        source = "default_returning"
        fidelity = "placeholder"
        notes = "default returning staff (no curated change flag)"

    new_hc, new_oc, new_dc = _flags_from_payload(raw)
    returning_hc = not new_hc
    returning_oc = not new_oc
    returning_dc = not new_dc
    if "fidelity" in raw and raw["fidelity"] in ("real", "approximate", "placeholder"):
        fidelity = raw["fidelity"]  # type: ignore[assignment]
    if raw.get("source"):
        source = str(raw["source"])
    if raw.get("notes"):
        notes = str(raw["notes"])
    elif team in CURATED_STAFF and not notes:
        notes = str(CURATED_STAFF[team].get("notes", ""))

    pens = compute_penalties(new_hc, new_oc, new_dc)
    continuity = score_continuity(new_hc, new_oc, new_dc)

    return CoachingContinuity(
        team=team,
        new_hc=new_hc,
        new_oc=new_oc,
        new_dc=new_dc,
        returning_hc=returning_hc,
        returning_oc=returning_oc,
        returning_dc=returning_dc,
        hc_name=str(raw.get("hc_name") or ""),
        continuity_score=round(continuity, 2),
        offense_penalty_w1=pens["offense_penalty_w1"],
        defense_penalty_w1=pens["defense_penalty_w1"],
        offense_index_mult=pens["offense_index_mult"],
        defense_index_mult=pens["defense_index_mult"],
        uncertainty_boost=pens["uncertainty_boost"],
        continuity_bonus_w1=pens["continuity_bonus_w1"],
        source=source,
        fidelity=fidelity,
        notes=notes,
    )


def coaching_week_adjustment(
    coaching: Optional[CoachingContinuity],
    *,
    week: int,
    side: str = "offense",
) -> Dict[str, Any]:
    """Week-decayed point adjustment for offense or defense side.

    Negative = scoring drag on this team; positive = continuity bonus.
    """
    if coaching is None:
        return {
            "points": 0.0,
            "decay": week_decay(week),
            "applied": False,
            "side": side,
        }
    decay = week_decay(week)
    if side == "defense":
        # Defense penalty → opponent scores more → we model as negative
        # contribution to *this team's* expected points via a defense drag
        # applied in expected_team_points (opponent points get a boost equal
        # to our defense penalty, or we subtract from our own scoring via
        # a combined team adjustment). We expose the raw penalty here.
        base = -float(coaching.defense_penalty_w1)
    else:
        base = -float(coaching.offense_penalty_w1)

    bonus = float(coaching.continuity_bonus_w1) if side == "offense" else 0.0
    points = (base + bonus) * decay
    return {
        "points": round(points, 3),
        "decay": round(decay, 3),
        "w1_penalty": round(-base, 3),
        "continuity_bonus_w1": round(bonus, 3),
        "new_hc": coaching.new_hc,
        "new_oc": coaching.new_oc,
        "new_dc": coaching.new_dc,
        "continuity_score": coaching.continuity_score,
        "applied": abs(points) > 1e-9,
        "side": side,
        "fidelity": coaching.fidelity,
    }


def team_game_point_adjustment(
    coaching: Optional[CoachingContinuity],
    *,
    week: int,
) -> Dict[str, Any]:
    """Net expected-points adjustment for a team in a given week.

    Offense penalty reduces own scoring; defense penalty is applied as a
    separate opponent boost in ``expected_team_points``. This helper returns
    the own-scoring (offense + continuity) piece for diagnostics.
    """
    off = coaching_week_adjustment(coaching, week=week, side="offense")
    deff = coaching_week_adjustment(coaching, week=week, side="defense")
    return {
        "own_scoring_adj": off["points"],
        "defense_penalty_points": abs(deff["points"]) if deff["applied"] else 0.0,
        "decay": off["decay"],
        "new_hc": bool(coaching.new_hc) if coaching else False,
        "new_oc": bool(coaching.new_oc) if coaching else False,
        "new_dc": bool(coaching.new_dc) if coaching else False,
        "continuity_score": coaching.continuity_score if coaching else 100.0,
        "uncertainty_boost": coaching.uncertainty_boost if coaching else 0.0,
        "fidelity": coaching.fidelity if coaching else "placeholder",
    }


def coaching_to_dict(c: Optional[CoachingContinuity]) -> Optional[Dict[str, Any]]:
    if c is None:
        return None
    return {
        "team": c.team,
        "new_hc": c.new_hc,
        "new_oc": c.new_oc,
        "new_dc": c.new_dc,
        "returning_hc": c.returning_hc,
        "returning_oc": c.returning_oc,
        "returning_dc": c.returning_dc,
        "hc_name": c.hc_name,
        "continuity_score": c.continuity_score,
        "offense_penalty_w1": c.offense_penalty_w1,
        "defense_penalty_w1": c.defense_penalty_w1,
        "offense_index_mult": c.offense_index_mult,
        "defense_index_mult": c.defense_index_mult,
        "uncertainty_boost": c.uncertainty_boost,
        "continuity_bonus_w1": c.continuity_bonus_w1,
        "source": c.source,
        "fidelity": c.fidelity,
        "notes": c.notes,
        "week_decay_table": {str(k): v for k, v in WEEK_DECAY.items()},
    }


def documentation() -> Dict[str, Any]:
    return {
        "layer": "coaching_continuity",
        "name": "coaching_continuity",
        "module": "src.services.cfb_season_engine.coaching_continuity",
        "real_vs_approximate": (
            "Change flags + week-decay schedule + relative HC/DC > OC penalties "
            "are REAL structure. Specific 2026 staff assignments are APPROXIMATE "
            "curated proxies — not a live coaching feed."
        ),
        "formula": (
            "W1 penalties: new_hc off/def, new_oc off, new_dc def; "
            "week_decay W1=1.0 … W4=0.45 … residual; "
            "compose: offense/defense index multipliers; "
            "uncertainty_boost blends into early_season_uncertainty"
        ),
        "penalties_w1": {
            "new_hc_offense": NEW_HC_OFFENSE_PENALTY,
            "new_hc_defense": NEW_HC_DEFENSE_PENALTY,
            "new_oc_offense": NEW_OC_OFFENSE_PENALTY,
            "new_dc_defense": NEW_DC_DEFENSE_PENALTY,
            "returning_bonus": RETURNING_CONTINUITY_BONUS,
        },
        "week_decay": dict(WEEK_DECAY),
        "feeds": [
            "team_projection.compose_team_projection",
            "team_projection.expected_team_points",
            "season_sim",
        ],
    }
