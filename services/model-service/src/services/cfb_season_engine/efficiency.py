"""Opponent-adjusted efficiency backbone (SP+/EPA-style; 2025→2026 carry).

College football preseason 2026 has no in-season PBP yet. This layer packages
final-2025 SP+ offense/defense (opponent-adjusted efficiency) as a primary
complementary driver beside roster / QB / unit identity — not a replacement.

Honesty
-------
- ``off_eff`` / ``def_eff`` are SP+-derived 0–100 scores (higher = better).
- ``success_off`` / ``success_def`` / ``explosiveness`` are SP+-correlated
  proxies, **not** true play-by-play success-rate / iso-explosiveness.
- Full PBP EPA / CFBD advanced refresh is optional when a key is present;
  the shipped snapshot is the default.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from src.services.cfb_season_engine import priors as P
from src.services.cfb_season_engine.types import EfficiencyProfile

DATA_DIR = Path(__file__).resolve().parent / "data"
PACKAGED_EFFICIENCY = DATA_DIR / "cfb_efficiency_snapshot_2025_carry_2026.json"

_SNAPSHOT_CACHE: Optional[Dict[str, Any]] = None


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, float(value)))


def load_efficiency_snapshot() -> Dict[str, Any]:
    global _SNAPSHOT_CACHE
    if _SNAPSHOT_CACHE is not None:
        return _SNAPSHOT_CACHE
    if not PACKAGED_EFFICIENCY.exists():
        _SNAPSHOT_CACHE = {
            "as_of": "",
            "fidelity": "placeholder",
            "teams": {},
            "notes": ["missing packaged efficiency snapshot"],
        }
        return _SNAPSHOT_CACHE
    with PACKAGED_EFFICIENCY.open("r", encoding="utf-8") as fh:
        _SNAPSHOT_CACHE = json.load(fh)
    return _SNAPSHOT_CACHE


def snapshot_meta(snap: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    snap = snap if snap is not None else load_efficiency_snapshot()
    teams = snap.get("teams") or {}
    mapped = sum(
        1
        for row in teams.values()
        if str(row.get("source", "")).startswith("packaged_sp_plus")
    )
    return {
        "present": bool(teams),
        "path": str(PACKAGED_EFFICIENCY.name),
        "as_of": str(snap.get("as_of") or ""),
        "prior_season": snap.get("prior_season"),
        "carry_to_season": snap.get("carry_to_season"),
        "fidelity": str(snap.get("fidelity") or "approximate"),
        "metric_family": str(snap.get("metric_family") or ""),
        "team_count": len(teams),
        "mapped_from_sp_plus": mapped,
        "source": snap.get("source") or {},
        "notes": list(snap.get("notes") or []),
    }


def build_efficiency_profile(
    team: str,
    payload: Optional[Mapping[str, Any]] = None,
    *,
    default_source: str = "packaged_sp_plus_final_2025",
    apply_inseason: bool = True,
) -> EfficiencyProfile:
    """Build inspectable efficiency profile for one team.

    Preference: explicit payload → packaged snapshot → league-average placeholder.
    When ``apply_inseason`` is True (default), cumulative in-season deltas from
    ``in_season_update`` are layered on top of the preseason baseline.
    """
    team = str(team).upper()
    row: Dict[str, Any] = {}
    if payload:
        row = dict(payload)
    else:
        snap = load_efficiency_snapshot()
        row = dict((snap.get("teams") or {}).get(team) or {})

    if not row:
        profile = EfficiencyProfile(
            team=team,
            off_eff=50.0,
            def_eff=50.0,
            success_off=50.0,
            success_def=50.0,
            explosiveness=50.0,
            sp_plus=0.0,
            prior_year=2025,
            carry_to_season=2026,
            source="league_average_fill",
            fidelity="placeholder",
            notes=(
                "No packaged SP+ row; league-average efficiency fill. "
                "Not opponent-adjusted for this code."
            ),
        )
    else:
        fidelity = str(row.get("fidelity") or "approximate")
        if fidelity not in ("real", "approximate", "placeholder"):
            fidelity = "approximate"

        profile = EfficiencyProfile(
            team=team,
            off_eff=_clamp(row.get("off_eff", 50.0)),
            def_eff=_clamp(row.get("def_eff", 50.0)),
            success_off=_clamp(row.get("success_off", row.get("off_eff", 50.0))),
            success_def=_clamp(row.get("success_def", row.get("def_eff", 50.0))),
            explosiveness=_clamp(row.get("explosiveness", 50.0)),
            sp_plus=float(row.get("sp_plus", 0.0) or 0.0),
            sp_offense=float(row.get("sp_offense", 0.0) or 0.0)
            if row.get("sp_offense") is not None
            else None,
            sp_defense=float(row.get("sp_defense", 0.0) or 0.0)
            if row.get("sp_defense") is not None
            else None,
            sp_rank=int(row["sp_rank"]) if row.get("sp_rank") is not None else None,
            prior_year=int(row.get("prior_year") or 2025),
            carry_to_season=int(row.get("carry_to_season") or 2026),
            source=str(row.get("source") or default_source),
            fidelity=fidelity,  # type: ignore[arg-type]
            notes=str(
                row.get("notes")
                or (
                    "Prior-year opponent-adjusted efficiency carry "
                    "(SP+); success/explosiveness are proxies."
                )
            ),
        )

    if apply_inseason:
        try:
            from src.services.cfb_season_engine.in_season_update import (
                apply_efficiency_deltas,
            )

            profile = apply_efficiency_deltas(profile)
        except Exception:
            pass
    return profile


def efficiency_to_dict(profile: Optional[EfficiencyProfile]) -> Optional[Dict[str, Any]]:
    if profile is None:
        return None
    return {
        "team": profile.team,
        "off_eff": round(profile.off_eff, 2),
        "def_eff": round(profile.def_eff, 2),
        "success_off": round(profile.success_off, 2),
        "success_def": round(profile.success_def, 2),
        "explosiveness": round(profile.explosiveness, 2),
        "sp_plus": round(profile.sp_plus, 2),
        "sp_offense": profile.sp_offense,
        "sp_defense": profile.sp_defense,
        "sp_rank": profile.sp_rank,
        "prior_year": profile.prior_year,
        "carry_to_season": profile.carry_to_season,
        "source": profile.source,
        "fidelity": profile.fidelity,
        "notes": profile.notes,
        "blend_weights": {
            "offense": {
                "efficiency": P.WEIGHT_OFF_EFF,
                "roster": P.WEIGHT_ROSTER_STRENGTH,
                "qb": P.WEIGHT_QB_SITUATION,
                "skill": P.WEIGHT_SKILL_GROUP,
                "ol": P.WEIGHT_OL_GROUP,
                "eff_index_blend": P.EFF_OFF_INDEX_BLEND,
            },
            "defense": {
                "efficiency": P.WEIGHT_DEF_EFF,
                "roster": P.WEIGHT_DEF_ROSTER_STRENGTH,
                "front_seven": P.WEIGHT_DEF_FRONT_SEVEN,
                "secondary": P.WEIGHT_DEF_SECONDARY,
                "experience": P.WEIGHT_DEF_EXPERIENCE,
                "eff_index_blend": P.EFF_DEF_INDEX_BLEND,
            },
            "anti_double_count": (
                "Unit grade weights + unit index blends reduced vs v0.7 so "
                "SP+ efficiency and talent composites do not both fully drive "
                "the same variance."
            ),
        },
    }


def efficiency_index(score_0_100: float) -> float:
    """Map 0–100 efficiency score to strength-index space (1.0 at 50)."""
    lo, hi = P.SCORE_TO_INDEX_CLAMP
    return max(
        lo,
        min(
            hi,
            1.0 + (float(score_0_100) - 50.0) / P.SCORE_TO_INDEX_DIVISOR,
        ),
    )


def documentation() -> Dict[str, Any]:
    meta = snapshot_meta()
    return {
        "layer": "efficiency_backbone",
        "name": "efficiency",
        "module": "src.services.cfb_season_engine.efficiency",
        "engine_version_introduced": "cfb-season-engine-v0.8-efficiency",
        "real_vs_approximate": (
            "Structure is REAL (inspectable off_eff/def_eff + blend weights). "
            "Packaged values are APPROXIMATE final-2025 SP+ carry — not live "
            "2026 PBP EPA. success/explosiveness are proxies."
        ),
        "primary_role": (
            "Primary complementary driver of team O/D indices alongside "
            "roster_strength + qb_situation (does not replace them)."
        ),
        "fields": [
            "off_eff",
            "def_eff",
            "success_off",
            "success_def",
            "explosiveness",
            "sp_plus",
        ],
        "data": meta,
        "blend_weights": {
            "offense": {
                "efficiency": P.WEIGHT_OFF_EFF,
                "roster": P.WEIGHT_ROSTER_STRENGTH,
                "qb": P.WEIGHT_QB_SITUATION,
                "skill": P.WEIGHT_SKILL_GROUP,
                "ol": P.WEIGHT_OL_GROUP,
            },
            "defense": {
                "efficiency": P.WEIGHT_DEF_EFF,
                "roster": P.WEIGHT_DEF_ROSTER_STRENGTH,
                "front_seven": P.WEIGHT_DEF_FRONT_SEVEN,
                "secondary": P.WEIGHT_DEF_SECONDARY,
                "experience": P.WEIGHT_DEF_EXPERIENCE,
            },
        },
        "limitations": [
            "No full PBP store; not true EPA / success-rate / explosiveness from plays",
            "2026 preseason: prior-year carry + roster/QB update (labeled)",
            "Some packaged codes lack SP+ rows (league-average placeholder)",
            "Not a live weekly SP+ refresh pipeline",
        ],
    }
