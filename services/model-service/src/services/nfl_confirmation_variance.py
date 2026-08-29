"""Confirmation + variance on committed DepthSot / situation events (KEI).

Every committed pack/situation event is stamped ``confirmation``:
``high`` | ``med`` | ``low``.

- **high** — IR / named starter / official depth → full mean shock
- **med** — default accepted SoT → half mean, modest variance widen
- **low** — beat-only / questionable → widen variance, small or zero mean move

Open competition stays a **mixture**. Sleeper / notes cannot close it
(``competition_status`` → ``named_starter`` blocked when source is notes/sleeper
and confirmation is not high).

KEI surfaces expose ``mean`` + ``uncertainty``. No desk accepts, no scanner /
rest-weather / shock_table_v1 rewrites in this module.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

CONFIRMATION_VARIANCE_VERSION = "confirmation_variance_v1"
CONFIRMATION_FIELD = "confirmation"
CONFIRMATION_LEVELS = frozenset({"high", "med", "low"})

# Mean shock scale applied to KEI point deltas (spread / total).
MEAN_SHOCK_SCALE: Dict[str, float] = {
    "high": 1.0,
    "med": 0.5,
    "low": 0.1,  # small or zero mean move
}

# Variance widen multiplier (std / uncertainty band; never shrinks).
VARIANCE_WIDEN: Dict[str, float] = {
    "high": 1.0,
    "med": 1.15,
    "low": 1.35,
}

# Extra confidence_delta (negative = less confident) when variance widens.
VARIANCE_CONFIDENCE_DELTA: Dict[str, float] = {
    "high": 0.0,
    "med": -0.04,
    "low": -0.10,
}

_IR_OUT = frozenset({"ir", "out", "pup", "suspended", "inactive"})
_QUESTIONABLE = frozenset({"questionable", "doubtful", "limited"})
_HIGH_COMP = frozenset({"named_starter", "starter", "official_depth"})
_OPEN_COMP = frozenset({"open_competition", "starter_competition"})

# Source tokens that cannot close an open competition (notes / sleeper / beat).
_WEAK_SOURCE_TOKENS = (
    "sleeper",
    "note",
    "notes",
    "camp-desk",
    "camp_desk",
    "twitter",
    "x.com",
    "beat",
    "rumor",
)


def normalize_confirmation(raw: Any) -> Optional[str]:
    token = str(raw or "").strip().lower()
    if token in {"medium", "mid"}:
        token = "med"
    if token in CONFIRMATION_LEVELS:
        return token
    return None


def mean_shock_scale(level: str) -> float:
    return float(MEAN_SHOCK_SCALE.get(normalize_confirmation(level) or "med", 0.5))


def variance_widen(level: str) -> float:
    return float(VARIANCE_WIDEN.get(normalize_confirmation(level) or "med", 1.15))


def variance_confidence_delta(level: str) -> float:
    return float(
        VARIANCE_CONFIDENCE_DELTA.get(normalize_confirmation(level) or "med", -0.04)
    )


def _sources_blob(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw.lower()
    if isinstance(raw, Mapping):
        parts = [str(v) for v in raw.values()]
        return " ".join(parts).lower()
    if isinstance(raw, (list, tuple)):
        return " ".join(str(x) for x in raw).lower()
    return str(raw).lower()


def sources_are_weak(sources: Any, *, confidence: Any = None) -> bool:
    """Beat-only / notes / sleeper / rumor — not official depth."""
    blob = _sources_blob(sources)
    conf = str(confidence or "").strip().lower()
    if conf in {"low", "weak", "beat", "beat-only", "beat_only"}:
        return True
    if not blob:
        return conf in {"", "medium", "med"} and False
    return any(tok in blob for tok in _WEAK_SOURCE_TOKENS)


def sources_are_official_depth(sources: Any, *, confidence: Any = None) -> bool:
    blob = _sources_blob(sources)
    conf = str(confidence or "").strip().lower()
    if conf in {"high", "official", "official_depth"}:
        return True
    official_tokens = (
        "official",
        "depth chart",
        "depth_chart",
        "injury report",
        "injury_report",
        "team release",
        "nfl.com",
        "official_depth",
    )
    return any(tok in blob for tok in official_tokens)


def resolve_confirmation(
    *,
    explicit: Any = None,
    injury_status: Any = None,
    competition_status: Any = None,
    depth_slot: Any = None,
    field: Any = None,
    after: Any = None,
    confidence: Any = None,
    sources: Any = None,
    reason: Any = None,
) -> str:
    """Infer confirmation high|med|low for a committed pack/situation event."""
    forced = normalize_confirmation(explicit)
    if forced:
        return forced

    inj = str(injury_status or "").strip().lower()
    comp = str(competition_status or "").strip().lower()
    slot = str(depth_slot or "").strip().lower()
    field_n = str(field or "").strip().lower()
    after_n = str(after or "").strip().lower()
    conf = str(confidence or "").strip().lower()
    reason_l = str(reason or "").strip().lower()

    # Target status after commit (override after wins for injury/competition writes).
    if field_n == "injury_status" and after_n:
        inj = after_n
    if field_n == "competition_status" and after_n:
        comp = after_n

    # Explicit low signals: beat-only / questionable / low confidence.
    if conf in {"low", "weak", "beat", "beat-only", "beat_only"}:
        return "low"
    if inj in _QUESTIONABLE:
        return "low"
    if "beat-only" in reason_l or "beat only" in reason_l or "questionable" in reason_l:
        if not sources_are_official_depth(sources, confidence=confidence):
            return "low"
    if sources_are_weak(sources, confidence=confidence) and not sources_are_official_depth(
        sources, confidence=confidence
    ):
        # Weak source alone is low unless IR / named_starter hard signal below.
        if inj not in _IR_OUT and comp not in _HIGH_COMP and slot not in {
            "starter",
            "official",
        }:
            return "low"

    # High: IR / named starter / official depth.
    if inj in {"ir"} or (inj in _IR_OUT and sources_are_official_depth(sources, confidence=confidence)):
        return "high"
    if inj in _IR_OUT and conf in {"high", "official", "medium", "med", ""}:
        # IR/out from accept SoT is high unless explicitly weak.
        if not sources_are_weak(sources, confidence=confidence):
            return "high"
    if comp in _HIGH_COMP or after_n in _HIGH_COMP:
        return "high"
    if slot in {"starter", "official"} and sources_are_official_depth(
        sources, confidence=confidence
    ):
        return "high"
    if conf in {"high", "official"} or sources_are_official_depth(
        sources, confidence=confidence
    ):
        return "high"

    return "med"


def scale_mean_shock(
    spread_pts: float,
    total_pts: float,
    confirmation: str,
) -> Tuple[float, float, Dict[str, Any]]:
    """Apply confirmation scale to mean points; return uncertainty block."""
    level = normalize_confirmation(confirmation) or "med"
    scale = mean_shock_scale(level)
    widen = variance_widen(level)
    mean_spread = round(float(spread_pts) * scale, 4)
    mean_total = round(float(total_pts) * scale, 4)
    uncertainty = {
        "confirmation": level,
        "mean_shock_scale": scale,
        "variance_widen": widen,
        "confidence_delta": variance_confidence_delta(level),
        "version": CONFIRMATION_VARIANCE_VERSION,
    }
    return mean_spread, mean_total, uncertainty


def expose_kei_mean_uncertainty(
    *,
    mean_spread: float,
    mean_total: float,
    confirmation: str,
    extra: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """KEI surface: mean + uncertainty (never mean-only)."""
    level = normalize_confirmation(confirmation) or "med"
    _, _, unc = scale_mean_shock(mean_spread, mean_total, level)
    # Recompute means from already-scaled inputs (pass-through).
    out = {
        "mean": {
            "spread": round(float(mean_spread), 4),
            "total": round(float(mean_total), 4),
        },
        "uncertainty": unc,
    }
    if extra:
        out["uncertainty"] = {**unc, **dict(extra)}
    return out


def stamp_situation_event(
    override: Mapping[str, Any],
    *,
    pack_row: Optional[Mapping[str, Any]] = None,
    confirmation: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a committed situation event with confirmation + mean/uncertainty knobs."""
    row = pack_row or {}
    level = resolve_confirmation(
        explicit=confirmation
        if confirmation is not None
        else override.get(CONFIRMATION_FIELD) or row.get(CONFIRMATION_FIELD),
        injury_status=row.get("injury_status"),
        competition_status=row.get("competition_status"),
        depth_slot=row.get("depth_slot"),
        field=override.get("field"),
        after=override.get("after"),
        confidence=override.get("confidence"),
        sources=override.get("sources"),
        reason=override.get("reason"),
    )
    scale = mean_shock_scale(level)
    widen = variance_widen(level)
    return {
        "team": override.get("team") or row.get("team"),
        "player_id": override.get("matched_player_id")
        or override.get("player_id")
        or row.get("player_id"),
        "player_name": override.get("player_name") or row.get("player_name"),
        "position": override.get("position") or row.get("position"),
        "field": override.get("field"),
        "before": override.get("before") if "before" in override else override.get("previous"),
        "after": override.get("after"),
        "destination": override.get("destination"),
        CONFIRMATION_FIELD: level,
        "mean_shock_scale": scale,
        "variance_widen": widen,
        "kei": expose_kei_mean_uncertainty(
            mean_spread=scale,  # unit scale as placeholder mean weight
            mean_total=scale,
            confirmation=level,
        ),
        "version": CONFIRMATION_VARIANCE_VERSION,
    }


def notes_or_sleeper_cannot_close_open_competition(
    override: Mapping[str, Any],
    pack_row: Mapping[str, Any],
) -> Optional[str]:
    """Return skip reason when notes/sleeper try to crown an open competition.

    Open competition stays a mixture — Sleeper/notes cannot close ATL-style races.
    """
    field = str(override.get("field") or "").strip().lower()
    if field != "competition_status":
        return None
    after = str(override.get("after") or "").strip().lower()
    if after not in _HIGH_COMP:
        return None
    current = str(pack_row.get("competition_status") or "").strip().lower()
    if current not in _OPEN_COMP:
        return None

    level = resolve_confirmation(
        explicit=override.get(CONFIRMATION_FIELD),
        competition_status=after,
        field=field,
        after=after,
        confidence=override.get("confidence"),
        sources=override.get("sources"),
        reason=override.get("reason"),
    )
    # Only official high confirmation may close an open competition.
    if level == "high" and sources_are_official_depth(
        override.get("sources"), confidence=override.get("confidence")
    ):
        return None
    if sources_are_weak(override.get("sources"), confidence=override.get("confidence")):
        return (
            "open_competition stays a mixture — sleeper/notes cannot close "
            f"(confirmation={level})"
        )
    if level != "high":
        return (
            "open_competition stays a mixture — confirmation "
            f"{level!r} cannot crown named_starter"
        )
    return (
        "open_competition stays a mixture — official depth confirmation required to close"
    )


def open_competition_mixture_shares(
    rows: Sequence[Mapping[str, Any]],
    *,
    team: str,
    position: str = "QB",
) -> Dict[str, Any]:
    """Describe an open competition as a mixture (no crown)."""
    team_n = str(team or "").strip().upper()
    pos_n = str(position or "QB").strip().upper()
    members: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        if str(row.get("team") or "").strip().upper() != team_n:
            continue
        if str(row.get("position") or "").strip().upper() != pos_n:
            continue
        status = str(row.get("competition_status") or "").strip().lower()
        if status not in _OPEN_COMP and status not in _HIGH_COMP:
            # Include depth-chart peers when any open_competition exists.
            pass
        members.append(
            {
                "player_id": row.get("player_id"),
                "player_name": row.get("player_name"),
                "depth_order": row.get("depth_order"),
                "competition_status": status or None,
                "snap_share_prior": row.get("snap_share_prior"),
            }
        )
    open_members = [
        m for m in members if str(m.get("competition_status") or "") in _OPEN_COMP
    ]
    crowned = any(
        str(m.get("competition_status") or "") in _HIGH_COMP for m in open_members
    )
    n = len(open_members) or len(members)
    equal = round(1.0 / n, 4) if n else 0.0
    mixture = []
    for m in open_members or members:
        share = m.get("snap_share_prior")
        try:
            w = float(share) if share is not None and str(share).strip() != "" else equal
        except (TypeError, ValueError):
            w = equal
        mixture.append({**m, "mixture_weight": w})
    total_w = sum(float(x["mixture_weight"]) for x in mixture) or 1.0
    for x in mixture:
        x["mixture_weight"] = round(float(x["mixture_weight"]) / total_w, 4)
    return {
        "team": team_n,
        "position": pos_n,
        "is_open_competition": bool(open_members),
        "crowned": crowned,
        "mixture": mixture,
        "version": CONFIRMATION_VARIANCE_VERSION,
    }


def apply_confirmation_to_pack_events(
    payload: MutableMapping[str, Any],
    applied_overrides: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """Stamp confirmation on applied overrides → ``situation_events`` on pack."""
    events: List[Dict[str, Any]] = []
    # Index rows across layers for pack_row lookup.
    layer_rows: List[Mapping[str, Any]] = []
    for key in ("rows", "ol_roles", "defense_roles"):
        for row in payload.get(key) or []:
            if isinstance(row, Mapping):
                layer_rows.append(row)

    for ov in applied_overrides:
        if not isinstance(ov, Mapping):
            continue
        match: Optional[Mapping[str, Any]] = None
        pid = str(ov.get("matched_player_id") or ov.get("player_id") or "")
        name = str(ov.get("player_name") or "").strip()
        team = str(ov.get("team") or "").strip().upper()
        for row in layer_rows:
            if str(row.get("team") or "").strip().upper() != team:
                continue
            if pid and str(row.get("player_id") or "") == pid:
                match = row
                break
            if name and str(row.get("player_name") or "").strip() == name:
                match = row
                break
        event = stamp_situation_event(ov, pack_row=match)
        events.append(event)
        # Persist confirmation onto the matched pack row when mutable.
        if match is not None and isinstance(match, MutableMapping):
            match[CONFIRMATION_FIELD] = event[CONFIRMATION_FIELD]

    if events:
        existing = list(payload.get("situation_events") or [])
        existing.extend(events)
        payload["situation_events"] = existing
        payload["confirmation_variance_version"] = CONFIRMATION_VARIANCE_VERSION
    return events


def row_confirmation(row: Mapping[str, Any]) -> str:
    """Confirmation for a pack row used by KEI mean/uncertainty scaling."""
    return resolve_confirmation(
        explicit=row.get(CONFIRMATION_FIELD),
        injury_status=row.get("injury_status"),
        competition_status=row.get("competition_status"),
        depth_slot=row.get("depth_slot"),
        confidence=row.get("role_confidence") or row.get("confidence"),
        sources=row.get("sources"),
        reason=row.get("injury_note") or row.get("note"),
    )


def copy_payload(payload: Mapping[str, Any]) -> Dict[str, Any]:
    return deepcopy(dict(payload))
