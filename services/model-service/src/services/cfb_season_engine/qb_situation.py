"""Layer 2 — Quarterback situation (first-class CFB variable).

Classifies starter context: incumbent / portal starter / open competition /
true freshman, attaches supporting-cast context (OL + weapons), and emits
``qb_situation_index`` — a material lever on team offense (not a tiny unused
field).
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Tuple

from src.services.cfb_season_engine import priors as P
from src.services.cfb_season_engine.types import QbClass, QbSituation

VALID_QB_CLASSES = frozenset(P.QB_CLASS_UNCERTAINTY.keys())


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
        # Accept portal_starter as alias for portal.
        if key == "portal_starter":
            key = "portal"
        if key in VALID_QB_CLASSES:
            return key  # type: ignore[return-value]
    if is_true_freshman:
        return "true_freshman"
    if open_competition:
        return "open_competition"
    if is_portal:
        return "portal"
    if int(experience_starts or 0) >= 1:
        return "incumbent"
    return "unknown"


def supporting_cast_score(ol_support: float, weapons_support: float) -> float:
    return _clamp(
        P.QB_CAST_OL_WEIGHT * ol_support + P.QB_CAST_WEAPONS_WEIGHT * weapons_support
    )


def compute_qb_situation_index(
    *,
    qb_class: QbClass,
    qb_talent: float,
    supporting_cast: float,
) -> Tuple[float, float, Dict[str, Any]]:
    """First-class QB lever → (index, 0–100 score, inspectable breakdown).

    Index ≈ 0.55–1.55 (1.0 ≈ FBS-average situation). Class multiplier and
    supporting cast are applied *after* talent so true_freshman vs incumbent
    separates sharply even at equal talent.
    """
    talent = _clamp(qb_talent)
    cast = _clamp(supporting_cast)
    talent_index = 1.0 + (talent - 50.0) / 80.0
    class_mult = float(P.QB_CLASS_OFFENSE_MULT.get(qb_class, 0.94))
    cast_mult = 1.0 + P.QB_CAST_INDEX_SCALE * (cast - 50.0) / 50.0
    raw = talent_index * class_mult * cast_mult
    index = max(P.STRENGTH_CLAMP[0], min(P.STRENGTH_CLAMP[1], raw))
    score = _clamp(50.0 + (index - 1.0) * 80.0)
    breakdown = {
        "qb_talent": round(talent, 2),
        "talent_index": round(talent_index, 4),
        "qb_class": qb_class,
        "class_mult": round(class_mult, 4),
        "supporting_cast": round(cast, 2),
        "cast_mult": round(cast_mult, 4),
        "qb_situation_index": round(index, 4),
        "qb_situation_score": round(score, 2),
    }
    return index, score, breakdown


def build_qb_situation(
    team: str,
    payload: Optional[Mapping[str, Any]] = None,
    *,
    default_source: str = "packaged_prior",
    ol_grade: Optional[float] = None,
    skill_grade: Optional[float] = None,
) -> QbSituation:
    """Build Layer 2 for one team.

    Optional ``ol_grade`` / ``skill_grade`` (from position groups) override
    packaged OL/weapons support when callers wire Layer 3 → Layer 2.
    """
    p = dict(payload or {})
    starts = int(p.get("experience_starts", 0) or 0)
    qb_class = classify_qb_situation(
        qb_class=p.get("qb_class"),
        experience_starts=starts,
        is_true_freshman=bool(p.get("is_true_freshman", False)),
        is_portal=bool(p.get("is_portal", False)),
        open_competition=bool(p.get("open_competition", False)),
    )

    # Supporting cast: prefer explicit qb ol/weapons, else position-group grades.
    ol = p.get("ol_support", p.get("ol"))
    if ol is None and ol_grade is not None:
        ol = ol_grade
    if ol is None:
        ol = 50.0
    weapons = p.get("weapons_support", p.get("weapons", p.get("skill")))
    if weapons is None and skill_grade is not None:
        weapons = skill_grade
    if weapons is None:
        weapons = 50.0
    ol = _clamp(ol)
    weapons = _clamp(weapons)

    cast = p.get("supporting_cast")
    if cast is None:
        cast = supporting_cast_score(ol, weapons)
    else:
        cast = _clamp(cast)

    unc = p.get("uncertainty")
    if unc is None:
        unc = P.QB_CLASS_UNCERTAINTY.get(qb_class, 0.5)
        # Better supporting cast slightly reduces QB uncertainty.
        unc = max(0.08, float(unc) - 0.08 * (float(cast) - 50.0) / 50.0)
    unc = max(0.05, min(0.95, float(unc)))

    talent = _clamp(p.get("qb_talent", 50.0))
    index_override = p.get("qb_situation_index")
    if index_override is None:
        index, score, _bd = compute_qb_situation_index(
            qb_class=qb_class,
            qb_talent=talent,
            supporting_cast=float(cast),
        )
    else:
        index = max(P.STRENGTH_CLAMP[0], min(P.STRENGTH_CLAMP[1], float(index_override)))
        score = _clamp(p.get("qb_situation_score", 50.0 + (index - 1.0) * 80.0))

    fidelity = str(p.get("fidelity", "approximate"))
    if fidelity not in ("real", "approximate", "placeholder"):
        fidelity = "approximate"
    name = str(p.get("starter_name", p.get("qb_name", "")) or "")
    key = str(p.get("starter_key", "") or "")
    if not key and name:
        key = name.lower().replace(" ", "_").replace(".", "")

    return QbSituation(
        team=str(team),
        qb_class=qb_class,
        starter_name=name,
        starter_key=key,
        experience_starts=starts,
        qb_talent=talent,
        ol_support=ol,
        weapons_support=weapons,
        supporting_cast=_clamp(cast),
        uncertainty=unc,
        qb_situation_index=round(index, 4),
        qb_situation_score=round(score, 2),
        source=str(p.get("source", default_source)),
        fidelity=fidelity,  # type: ignore[arg-type]
        notes=str(p.get("notes", "")),
    )


def qb_situation_breakdown(qb: QbSituation) -> Dict[str, Any]:
    _index, _score, breakdown = compute_qb_situation_index(
        qb_class=qb.qb_class,
        qb_talent=qb.qb_talent,
        supporting_cast=qb.supporting_cast,
    )
    return {
        "team": qb.team,
        "starter_name": qb.starter_name,
        "experience_starts": qb.experience_starts,
        "uncertainty": round(qb.uncertainty, 3),
        "components": breakdown,
        "fidelity": qb.fidelity,
        "source": qb.source,
    }


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
        "qb_situation_index": round(qb.qb_situation_index, 4),
        "qb_situation_score": round(qb.qb_situation_score, 2),
        "components": qb_situation_breakdown(qb)["components"],
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
            "Classification rules and class→offense multipliers are REAL "
            "(deterministic, inspectable). Named starters and talent scores "
            "in packaged priors are APPROXIMATE until depth-chart feeds land. "
            "Supporting cast blends OL + weapons (packaged grades approximate)."
        ),
        "formula": {
            "supporting_cast": (
                f"{P.QB_CAST_OL_WEIGHT}*ol_support + "
                f"{P.QB_CAST_WEAPONS_WEIGHT}*weapons_support"
            ),
            "qb_situation_index": (
                "(1 + (qb_talent-50)/80) * class_mult * "
                f"(1 + {P.QB_CAST_INDEX_SCALE}*(supporting_cast-50)/50)"
            ),
            "class_mult": dict(P.QB_CLASS_OFFENSE_MULT),
        },
        "uncertainty_priors": dict(P.QB_CLASS_UNCERTAINTY),
        "class_offense_mult": dict(P.QB_CLASS_OFFENSE_MULT),
    }
