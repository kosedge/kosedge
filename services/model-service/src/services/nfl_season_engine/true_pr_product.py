"""True PR product-surface serializer — display only, no rating math.

Exposes already-computed Layer-1 drivers (continuity, QB premium, past SOS,
blend, projected 2026 SOS outlook) for Pro UI. Never mutates intrinsic /
full-strength indices. Future SOS is framed as schedule outlook only.

North star: ``data/ops/nfl-model-vision.md``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Tuple

from src.services.nfl_season_engine.projected_sos import compute_league_projected_sos


def _intrinsic_power(strength: Any) -> float:
    """Composite full-strength PR — same (off+def)/2 contract as projected SOS."""
    off = float(
        getattr(strength, "full_strength_offense_index", None)
        or getattr(strength, "offense_index", 1.0)
        or 1.0
    )
    deff = float(
        getattr(strength, "full_strength_defense_index", None)
        or getattr(strength, "defense_index", 1.0)
        or 1.0
    )
    return 0.5 * (off + deff)

TRUE_PR_PRODUCT_VERSION = "v1.0"

# Past SOS hardness = actual_sos_defense − actual_sos_offense (higher = harder).
# Thresholds are approximate product bands, not a new model.
_PAST_SOS_SOFT = -0.02
_PAST_SOS_HARD = 0.02

# QB premium magnitude bands (offense-index units) — approximate labels.
_QB_ELITE = 0.035
_QB_LIFT = 0.012
_QB_DRAG = -0.012
_QB_HEAVY_DRAG = -0.035


def _as_dict(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _continuity_reason(cont: Mapping[str, Any]) -> str:
    factors = cont.get("factors") if isinstance(cont.get("factors"), list) else []
    bits: List[str] = []
    for factor in factors:
        if not isinstance(factor, Mapping):
            continue
        name = str(factor.get("name") or "")
        status = str(factor.get("status") or "")
        detail = str(factor.get("detail") or "").strip()
        score = _safe_float(factor.get("score"))
        if status in {"missing", "thin_unavailable"}:
            continue
        if name == "qb":
            if score is not None and score >= 0.7:
                bits.append("same QB")
            elif score is not None and score <= 0.35:
                bits.append("new / uncertain QB")
            # Skip neutral "partial QB evidence" noise — prefer material factors.
        elif name == "staff":
            if score is not None and score <= 0.35:
                bits.append("new staff")
            elif score is not None and score >= 0.7:
                bits.append("staff returning")
            elif "new OC" in detail or "OC departed" in detail:
                bits.append("OC change")
            elif "new HC" in detail.lower():
                bits.append("new HC")
        elif name == "returning_production":
            if score is not None and score >= 0.7:
                bits.append("returning production")
            elif score is not None and score <= 0.35:
                bits.append("production churn")
        elif name == "roster_churn":
            if score is not None and score <= 0.35:
                bits.append("roster overhaul")
        if len(bits) >= 3:
            break
    if bits:
        return "; ".join(bits)
    fidelity = str(cont.get("fidelity") or "")
    if fidelity in {"approximate", "mixed"}:
        return "Limited continuity evidence — labeled approximate"
    if fidelity == "missing":
        return "Continuity evidence missing"
    return "Continuity not scored"


def _shape_continuity(
    drivers: Mapping[str, Any],
    *,
    display_overlay: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    stubs = _as_dict(drivers.get("stubs"))
    cont = _as_dict(drivers.get("continuity"))
    source = "strength_drivers"
    if not cont and display_overlay:
        cont = _as_dict(display_overlay)
        source = "display_overlay"
    stub = str(stubs.get("continuity") or "")
    if not cont:
        return {
            "available": False,
            "band": None,
            "score": None,
            "reason": "Continuity not applied on this strength path",
            "fidelity": "missing",
            "label": "unavailable",
            "approximate": True,
            "source": source,
            "stub": stub or "stub_not_applied",
        }
    score = _safe_float(cont.get("continuity_score"))
    band = str(cont.get("band") or "") or None
    fidelity = str(cont.get("fidelity") or "approximate")
    approximate = fidelity != "real"
    return {
        "available": True,
        "band": band,
        "score": score,
        "reason": _continuity_reason(cont),
        "fidelity": fidelity,
        "label": band or "mid",
        "approximate": approximate,
        "prior_travel_weight": _safe_float(cont.get("prior_travel_weight")),
        "source": source,
        "stub": stub or ("applied" if source == "strength_drivers" else "display_only"),
    }


def _qb_band(premium: Optional[float], fidelity: str) -> Tuple[Optional[str], str]:
    if fidelity in {"missing", ""} or premium is None:
        return None, "unavailable"
    if premium >= _QB_ELITE:
        return "elite_lift", "Elite lift"
    if premium >= _QB_LIFT:
        return "lift", "Lift"
    if premium <= _QB_HEAVY_DRAG:
        return "heavy_drag", "Heavy drag"
    if premium <= _QB_DRAG:
        return "drag", "Drag"
    return "neutral", "Neutral"


def _shape_qb_premium(
    drivers: Mapping[str, Any],
    *,
    qb_premium_value: float,
    display_overlay: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    stubs = _as_dict(drivers.get("stubs"))
    qb = _as_dict(drivers.get("qb_premium"))
    source = "strength_drivers"
    if (not qb or str(qb.get("fidelity") or "") == "missing") and display_overlay:
        qb = _as_dict(display_overlay)
        source = "display_overlay"
    stub = str(stubs.get("qb_premium") or "")
    fidelity = str(qb.get("fidelity") or ("missing" if not qb else "approximate"))
    premium = _safe_float(qb.get("premium_full"), qb_premium_value)
    starter = str(qb.get("starter_name") or "").strip() or None
    tenure = str(qb.get("tenure") or "") or None
    same = qb.get("same_as_prior")
    band_key, band_label = _qb_band(premium, fidelity)
    if not qb and stub == "stub_not_applied":
        return {
            "available": False,
            "band": None,
            "band_label": "unavailable",
            "premium": None,
            "starter_name": None,
            "tenure": None,
            "same_as_prior": None,
            "fidelity": "missing",
            "reason": "QB premium not applied — no invented starter edge",
            "approximate": True,
            "source": source,
            "stub": stub,
        }
    # Without a quality sample, keep starter context but never invent a lift band
    # or trust noisy tenure labels from thin packaged books.
    if fidelity == "missing":
        band_key = None
        band_label = "Context only" if starter else "unavailable"
        premium = None
        tenure = None
    reason_bits: List[str] = []
    if starter:
        reason_bits.append(starter)
    if fidelity != "missing":
        if tenure and tenure not in {"unknown", "incumbent"}:
            reason_bits.append(tenure.replace("_", " "))
        elif same is True:
            reason_bits.append("same starter")
        elif same is False:
            reason_bits.append("new starter")
    if fidelity == "missing":
        reason_bits.append("quality sample missing — no invented lift/drag")
    elif fidelity == "approximate":
        reason_bits.append("approximate")
    return {
        "available": band_key is not None or bool(starter),
        "band": band_key,
        "band_label": band_label,
        "premium": premium,
        "starter_name": starter,
        "tenure": tenure,
        "same_as_prior": same if fidelity != "missing" else None,
        "fidelity": fidelity,
        "reason": " · ".join(reason_bits) if reason_bits else "QB context thin",
        "approximate": fidelity != "real",
        "source": source,
        "stub": stub
        or ("applied" if source == "strength_drivers" else "display_only"),
    }


def _shape_past_sos(drivers: Mapping[str, Any]) -> Dict[str, Any]:
    past = _as_dict(drivers.get("past_sos"))
    status = str(past.get("status") or "thin_unavailable")
    if not past or status == "thin_unavailable":
        return {
            "available": False,
            "band": None,
            "label": "unavailable",
            "reason": "Past SOS thin / unavailable",
            "approximate": True,
            "status": status,
            "intrinsic_note": "Past SOS adjusts how prior performance is read",
        }
    off = _safe_float(past.get("actual_sos_offense"))
    deff = _safe_float(past.get("actual_sos_defense"))
    if off is None or deff is None:
        return {
            "available": False,
            "band": None,
            "label": "unavailable",
            "reason": "Past SOS metrics incomplete",
            "approximate": True,
            "status": status,
            "intrinsic_note": "Past SOS adjusts how prior performance is read",
        }
    hardness = float(deff) - float(off)
    if hardness <= _PAST_SOS_SOFT:
        band = "soft"
    elif hardness >= _PAST_SOS_HARD:
        band = "hard"
    else:
        band = "average"
    approx_games = int(past.get("approximate_games") or 0)
    games = int(past.get("games_used") or past.get("games") or 0)
    approximate = status != "time_of_game" or approx_games > 0
    reason = f"Prior slate {band}"
    if approximate:
        reason += " (approx)"
    if games:
        reason += f" · {games}g"
    off_delta = _safe_float(past.get("off_delta"))
    if off_delta is not None and abs(off_delta) >= 0.015:
        direction = "below" if off_delta < 0 else "above"
        reason += f" · schedule-adj offense {direction} raw"
    return {
        "available": True,
        "band": band,
        "label": band,
        "reason": reason,
        "approximate": approximate,
        "status": status,
        "hardness": round(hardness, 4),
        "games_used": games,
        "intrinsic_note": "Past SOS adjusts how prior performance is read",
    }


def _shape_projected_sos(sos_row: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if not sos_row:
        return {
            "available": False,
            "band": None,
            "label": "unavailable",
            "reason": "2026 schedule outlook unavailable",
            "approximate": True,
            "intrinsic_pr_unchanged": True,
            "framing": "Schedule outlook only — does not change intrinsic PR",
        }
    band = str(sos_row.get("difficulty_band") or "average")
    status = str(sos_row.get("status") or "")
    value = _safe_float(sos_row.get("projected_sos_2026"))
    home = int(sos_row.get("home_games") or 0)
    away = int(sos_row.get("away_games") or 0)
    reason = f"2026 slate {band}"
    if away > home:
        reason += " · road-heavy"
    elif home > away:
        reason += " · home-lean"
    return {
        "available": True,
        "band": band,
        "label": band,
        "projected_sos_2026": value,
        "reason": reason,
        "approximate": status.startswith("applied_partial") or "partial" in status,
        "status": status,
        "home_games": home,
        "away_games": away,
        "intrinsic_pr_unchanged": True,
        "framing": "Schedule outlook only — does not change intrinsic PR",
    }


def _shape_blend(drivers: Mapping[str, Any], strength: Any) -> Dict[str, Any]:
    blend = _as_dict(drivers.get("blend"))
    w_prior = _safe_float(
        blend.get("w_prior"), getattr(strength, "blend_prior_weight", 1.0)
    )
    w_current = _safe_float(
        blend.get("w_current"), getattr(strength, "blend_current_weight", 0.0)
    )
    if w_prior is None:
        w_prior = 1.0
    if w_current is None:
        w_current = 0.0
    uncertainty = _as_dict(drivers.get("uncertainty"))
    games = int(
        uncertainty.get("games_played")
        if uncertainty.get("games_played") is not None
        else getattr(strength, "games_played", 0) or 0
    )
    # Preseason / zero sample: never cosplay "current sample".
    if games <= 0 or w_current <= 1e-9:
        state = "prior_heavy"
        label = "Prior-heavy"
        reason = "Preseason / 0 REG games — prior only (no current sample)"
        show = True
    elif w_current >= 0.999:
        state = "current_dominated"
        label = "Current sample"
        reason = f"{games} REG games into ramp — current-dominated"
        show = True
    else:
        state = "blending"
        label = "Blending"
        reason = (
            f"{games}/8 REG into ramp · "
            f"prior {w_prior:.0%} / current {w_current:.0%}"
        )
        show = True
    return {
        "available": show,
        "state": state,
        "label": label,
        "reason": reason,
        "w_prior": round(float(w_prior), 4),
        "w_current": round(float(w_current), 4),
        "games_played": games,
        "ramp_games": 8,
        "approximate": False,
        "preseason": games <= 0,
    }


def _display_overlays(
    session: Any,
    *,
    season: int,
    as_of_week: int,
    teams: List[str],
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """Optional display-only continuity / QB books when strength stubs omit them.

    Does not mutate TeamStrength indices.
    """
    cont_overlay: Dict[str, Dict[str, Any]] = {}
    qb_overlay: Dict[str, Dict[str, Any]] = {}
    try:
        from src.services.nfl_season_engine.continuity_score import (
            build_continuity_book,
        )

        book = build_continuity_book(
            session,
            season=int(season),
            as_of_week=int(as_of_week),
            teams=teams,
        )
        for team, cont in book.items():
            cont_overlay[team] = cont.to_drivers()
    except Exception:
        cont_overlay = {}
    try:
        from src.services.nfl_season_engine.qb_premium import build_qb_premium_book

        qbook = build_qb_premium_book(
            session,
            season=int(season),
            as_of_week=int(as_of_week),
            teams=teams,
            team_games={t: 0 for t in teams},
        )
        for team, qb in qbook.items():
            qb_overlay[team] = qb.to_drivers()
    except Exception:
        qb_overlay = {}
    return cont_overlay, qb_overlay


def serialize_true_pr_product_surface(
    universe: Any,
    *,
    season: int = 2026,
    as_of_week: int = 1,
    mode: str = "real",
    schedule_meta: Optional[Mapping[str, Any]] = None,
    engine_version: str = "",
    session: Any = None,
    enrich_display_drivers: bool = True,
) -> Dict[str, Any]:
    """Build scannable True PR driver payload for Pro UI (no math changes)."""
    strengths = getattr(universe, "strengths", {}) or {}
    teams = sorted(str(t) for t in strengths.keys())
    sos_book = compute_league_projected_sos(universe)
    cont_overlay: Dict[str, Dict[str, Any]] = {}
    qb_overlay: Dict[str, Dict[str, Any]] = {}
    if enrich_display_drivers:
        cont_overlay, qb_overlay = _display_overlays(
            session,
            season=season,
            as_of_week=as_of_week,
            teams=teams,
        )

    rows: List[Dict[str, Any]] = []
    for team in teams:
        strength = strengths[team]
        drivers = _as_dict(getattr(strength, "drivers", None))
        intrinsic = round(float(_intrinsic_power(strength)), 4)
        full_off = round(
            float(
                getattr(strength, "full_strength_offense_index", None)
                or strength.offense_index
            ),
            4,
        )
        full_def = round(
            float(
                getattr(strength, "full_strength_defense_index", None)
                or strength.defense_index
            ),
            4,
        )
        cont = _shape_continuity(
            drivers, display_overlay=cont_overlay.get(team)
        )
        qb = _shape_qb_premium(
            drivers,
            qb_premium_value=float(getattr(strength, "qb_premium", 0.0) or 0.0),
            display_overlay=qb_overlay.get(team),
        )
        past = _shape_past_sos(drivers)
        projected = _shape_projected_sos(
            sos_book[team].to_dict() if team in sos_book else None
        )
        blend = _shape_blend(drivers, strength)
        rows.append(
            {
                "team": team,
                "intrinsic_pr": intrinsic,
                "full_strength_offense_index": full_off,
                "full_strength_defense_index": full_def,
                "offense_index": round(float(strength.offense_index), 4),
                "defense_index": round(float(strength.defense_index), 4),
                "drivers": {
                    "continuity": cont,
                    "qb_premium": qb,
                    "past_sos": past,
                    "projected_sos_2026": projected,
                    "blend": blend,
                },
            }
        )

    rows.sort(key=lambda r: (-float(r["intrinsic_pr"]), r["team"]))
    for idx, row in enumerate(rows, start=1):
        row["rank"] = idx

    meta = dict(schedule_meta or {})
    return {
        "product_version": TRUE_PR_PRODUCT_VERSION,
        "engine_version": engine_version,
        "season": int(season),
        "as_of_week": int(as_of_week),
        "mode": mode,
        "schedule_source": meta.get("schedule_source") or "",
        "strength_source": meta.get("strength_source")
        or meta.get("strengths")
        or "",
        "team_count": len(rows),
        "contract": {
            "model": "research fair / intrinsic PR",
            "kei": "late reprice (not shown here)",
            "edge": "KEI vs market only (Edge Board unchanged)",
            "projected_sos": "outlook only — never rewrites intrinsic PR",
            "approximate_rule": (
                "If a driver is missing or approximate, label or hide — "
                "never invent elite confidence"
            ),
        },
        "copy_rules": {
            "continuity": "High / mid / low + short reason; approximate when fidelity ≠ real",
            "qb_premium": "Band + starter context; hide magnitude when fidelity missing",
            "past_sos": "Soft / average / hard prior slate (approximate bands)",
            "projected_sos_2026": "Easy / average / hard outlook — not power ranking",
            "blend": "Prior-heavy until REG sample; show games into 8-game ramp in-season",
        },
        "teams": rows,
    }
