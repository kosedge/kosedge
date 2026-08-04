"""Layer 2 — Quarterback situation (first-class CFB variable).

Classifies starter context: incumbent / portal / open competition /
true freshman, and attaches supporting-cast context (OL + weapons).
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from src.services.cfb_season_engine.priors import QB_CLASS_UNCERTAINTY
from src.services.cfb_season_engine.types import QbClass, QbSituation

VALID_QB_CLASSES = frozenset(QB_CLASS_UNCERTAINTY.keys())


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, float(value)))


def classify_qb_situation(
    *,
    qb_class: Optional[str] = None,
    experience_starts: int = 0,
    is_true_freshman: bool = False,
    is_portal: bool = False,
    open_competition: bool = False,
) -> QbClass:
    """Classify QB situation from explicit flags or class string.

    Priority: explicit class string → true freshman → open competition →
    portal → incumbent (if starts) → unknown.
    """
    if qb_class:
        key = str(qb_class).strip().lower().replace(" ", "_").replace("-", "_")
        if key in VALID_QB_CLASSES:
            return key  # type: ignore[return-value]
    if is_true_freshman:
        return "true_freshman"
    if open_competition:
        return "open_competition"
    if is_portal:
        return "portal"
    if int(experience_starts or 0) >= 4:
        return "incumbent"
    if int(experience_starts or 0) >= 1:
        return "incumbent"
    return "unknown"


def supporting_cast_score(ol_support: float, weapons_support: float) -> float:
    return _clamp(0.55 * ol_support + 0.45 * weapons_support)


def build_qb_situation(
    team: str,
    payload: Optional[Mapping[str, Any]] = None,
    *,
    default_source: str = "packaged_prior",
) -> QbSituation:
    """Build Layer 2 for one team."""
    p = dict(payload or {})
    starts = int(p.get("experience_starts", 0) or 0)
    qb_class = classify_qb_situation(
        qb_class=p.get("qb_class"),
        experience_starts=starts,
        is_true_freshman=bool(p.get("is_true_freshman", False)),
        is_portal=bool(p.get("is_portal", False)),
        open_competition=bool(p.get("open_competition", False)),
    )
    ol = _clamp(p.get("ol_support", p.get("ol", 50.0)))
    weapons = _clamp(p.get("weapons_support", p.get("weapons", 50.0)))
    cast = p.get("supporting_cast")
    if cast is None:
        cast = supporting_cast_score(ol, weapons)
    unc = p.get("uncertainty")
    if unc is None:
        unc = QB_CLASS_UNCERTAINTY.get(qb_class, 0.5)
        # Better supporting cast slightly reduces QB uncertainty.
        unc = max(0.08, float(unc) - 0.08 * (float(cast) - 50.0) / 50.0)
    fidelity = str(p.get("fidelity", "approximate"))
    if fidelity not in ("real", "approximate", "placeholder"):
        fidelity = "approximate"
    name = str(p.get("starter_name", "") or "")
    key = str(p.get("starter_key", "") or "")
    if not key and name:
        key = name.lower().replace(" ", "_").replace(".", "")
    return QbSituation(
        team=str(team),
        qb_class=qb_class,
        starter_name=name,
        starter_key=key,
        experience_starts=starts,
        qb_talent=_clamp(p.get("qb_talent", 50.0)),
        ol_support=ol,
        weapons_support=weapons,
        supporting_cast=_clamp(cast),
        uncertainty=max(0.05, min(0.95, float(unc))),
        source=str(p.get("source", default_source)),
        fidelity=fidelity,  # type: ignore[arg-type]
        notes=str(p.get("notes", "")),
    )


def qb_to_dict(qb: QbSituation) -> Dict[str, Any]:
    return {
        "team": qb.team,
        "qb_class": qb.qb_class,
        "starter_name": qb.starter_name,
        "starter_key": qb.starter_key,
        "experience_starts": qb.experience_starts,
        "qb_talent": round(qb.qb_talent, 2),
        "ol_support": round(qb.ol_support, 2),
        "weapons_support": round(qb.weapons_support, 2),
        "supporting_cast": round(qb.supporting_cast, 2),
        "uncertainty": round(qb.uncertainty, 3),
        "source": qb.source,
        "fidelity": qb.fidelity,
        "notes": qb.notes,
    }


def documentation() -> Dict[str, Any]:
    return {
        "layer": 2,
        "name": "qb_situation",
        "module": "src.services.cfb_season_engine.qb_situation",
        "classes": sorted(VALID_QB_CLASSES),
        "real_vs_approximate": (
            "Classification rules are REAL (deterministic). Named starters and "
            "talent scores in packaged priors are APPROXIMATE until depth-chart "
            "feeds land."
        ),
        "uncertainty_priors": dict(QB_CLASS_UNCERTAINTY),
    }
