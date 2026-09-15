"""KE Disruption inventory — no composite weights.

Named ``ke.havoc`` requires certified TFL ∧ FF ∧ INT on the SoT.
Until that certification exists, publish per-event rates (and the NFL
sack∨INT∨qb_hit proxy) under their own IDs. Do not assign arbitrary
bundle weights.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from src.services.ke_football.plays import CanonicalPlay
from src.services.ke_football.provenance import Component, Layer, Status, THIN_PLAYS_STD, derived, omitted


# Inventory first. weight is always None in Phase 1.
DISRUPTION_EVENTS: List[Dict[str, Any]] = [
    {
        "event_id": "sack",
        "nfl_mart": True,
        "nfl_raw_typical": True,
        "cfb_core31": False,
        "cfb_raw_2025_26_flag": True,
        "required_for_named_havoc": False,
        "optional_if_tfl_includes_sacks": True,
        "weight": None,
    },
    {
        "event_id": "interception",
        "nfl_mart": True,
        "nfl_raw_typical": True,
        "cfb_core31": False,
        "cfb_raw_2025_26_flag": True,
        "required_for_named_havoc": True,
        "weight": None,
    },
    {
        "event_id": "qb_hit",
        "nfl_mart": True,
        "nfl_raw_typical": True,
        "cfb_core31": False,
        "cfb_raw_2025_26_flag": False,
        "required_for_named_havoc": False,
        "weight": None,
        "notes": "Allowed inside ke.disruption_proxy_nfl only",
    },
    {
        "event_id": "fumble",
        "nfl_mart": True,
        "nfl_raw_typical": True,
        "cfb_core31": False,
        "cfb_raw_2025_26_flag": False,
        "required_for_named_havoc": False,
        "weight": None,
        "notes": "Not forced fumble; not a havoc substitute",
    },
    {
        "event_id": "fumble_forced",
        "nfl_mart": False,
        "nfl_raw_typical": True,
        "cfb_core31": False,
        "cfb_raw_2025_26_flag": True,
        "required_for_named_havoc": True,
        "weight": None,
    },
    {
        "event_id": "tackle_for_loss",
        "nfl_mart": False,
        "nfl_raw_typical": True,
        "cfb_core31": False,
        "cfb_raw_2025_26_flag": True,
        "required_for_named_havoc": True,
        "weight": None,
    },
    {
        "event_id": "pass_breakup",
        "nfl_mart": False,
        "nfl_raw_typical": False,
        "cfb_core31": False,
        "cfb_raw_2025_26_flag": True,
        "required_for_named_havoc": False,
        "optional_add_if_certified": True,
        "weight": None,
    },
]


@dataclass
class ColumnAudit:
    name: str
    present: bool
    n_scrimmage: int = 0
    n_non_null: int = 0
    n_true: int = 0
    certified: bool = False
    notes: str = ""

    @property
    def null_rate(self) -> Optional[float]:
        if not self.present or self.n_scrimmage <= 0:
            return None
        return 1.0 - (self.n_non_null / self.n_scrimmage)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "present": self.present,
            "n_scrimmage": self.n_scrimmage,
            "n_non_null": self.n_non_null,
            "n_true": self.n_true,
            "null_rate": self.null_rate,
            "certified": self.certified,
            "weight": None,
            "notes": self.notes,
        }


def _attr_for(event_id: str) -> str:
    return {
        "sack": "sack",
        "interception": "interception",
        "qb_hit": "qb_hit",
        "fumble": "fumble",
        "fumble_forced": "fumble_forced",
        "tackle_for_loss": "tfl",
        "pass_breakup": "pass_breakup",
        "havoc_vendor": "havoc_vendor",
    }[event_id]


def audit_disruption_columns(plays: Sequence[CanonicalPlay]) -> Dict[str, ColumnAudit]:
    """Null-rate inventory on scrimmage plays. Certification is conservative."""
    scrim = [p for p in plays if p.is_scrimmage]
    n = len(scrim)
    out: Dict[str, ColumnAudit] = {}
    for spec in DISRUPTION_EVENTS:
        eid = str(spec["event_id"])
        attr = _attr_for(eid)
        present = any(getattr(p, attr) is not None for p in scrim) if scrim else False
        non_null = sum(1 for p in scrim if getattr(p, attr) is not None)
        n_true = sum(1 for p in scrim if getattr(p, attr) is True)
        null_rate = (1.0 - non_null / n) if n and present else 1.0
        # Conservative: present + null rate ≤ 5% is "inventory-ok", still not
        # official-charting certified. Named havoc stays omitted.
        certified = bool(present and n > 0 and null_rate <= 0.05)
        out[eid] = ColumnAudit(
            name=eid,
            present=present,
            n_scrimmage=n,
            n_non_null=non_null,
            n_true=n_true,
            certified=certified,
            notes="inventory_ok_not_official_charting" if certified else "uncertified_or_absent",
        )
    return out


def named_havoc_allowed(audit: Dict[str, ColumnAudit]) -> bool:
    needed = ("tackle_for_loss", "fumble_forced", "interception")
    return all(audit.get(k) and audit[k].certified for k in needed)


def inventory_report(
    *,
    sport: str,
    plays: Sequence[CanonicalPlay],
) -> Dict[str, Any]:
    audit = audit_disruption_columns(plays)
    return {
        "sport": sport,
        "named_ke_havoc": "OMIT",
        "named_havoc_allowed": named_havoc_allowed(audit),
        "weights_assigned": False,
        "rule": "validate components before any weighting — no arbitrary composite",
        "events": [e | {"audit": audit[e["event_id"]].to_dict()} for e in DISRUPTION_EVENTS if e["event_id"] in audit],
        "proxy_id_nfl": "ke.disruption_proxy_nfl" if sport == "nfl" else None,
        "flags_id_cfb": "ke.disruption_flags_cfb" if sport == "cfb" else None,
        "production_promote": False,
    }


def event_rate(plays: Sequence[CanonicalPlay], attr: str) -> Component:
    """Rate on scrimmage. Sparse flags (null-rate > 5%) are DATA_INSUFFICIENT.

    Do not treat "only True rows exist" as a 100% rate. That is the CFB 2025
    TFL/FF pattern and is why named havoc stays omitted.
    """
    scrim = [p for p in plays if p.is_scrimmage]
    usable = [p for p in scrim if getattr(p, attr) is not None]
    if not scrim or not usable:
        return derived(
            f"ke.disruption_{attr}",
            None,
            unit="rate",
            n=0,
            missing_fields=[attr],
            notes={"weight": None},
        )
    null_rate = 1.0 - (len(usable) / len(scrim))
    if null_rate > 0.05:
        return derived(
            f"ke.disruption_{attr}",
            None,
            unit="rate",
            n=len(usable),
            missing_fields=[attr],
            notes={
                "weight": None,
                "null_rate": null_rate,
                "reason": "sparse_or_event_only_flag_uncertified",
                "do_not_treat_null_as_false": True,
            },
        )
    hits = sum(1 for p in usable if getattr(p, attr) is True)
    return derived(
        f"ke.disruption_{attr}",
        hits / len(usable),
        unit="rate",
        n=len(usable),
        thin_n=THIN_PLAYS_STD,
        notes={"weight": None, "numerator": hits, "null_rate": null_rate},
    )


def nfl_proxy_rate(plays: Sequence[CanonicalPlay]) -> Component:
    """sack OR interception OR qb_hit. Must not be named ke.havoc."""
    usable = [
        p
        for p in plays
        if p.is_scrimmage
        and (p.sack is not None or p.interception is not None or p.qb_hit is not None)
    ]
    if not usable:
        return omitted(
            "ke.disruption_proxy_nfl",
            unit="rate",
            reason="sack/int/qb_hit columns absent",
        )
    hits = 0
    for p in usable:
        if p.sack is True or p.interception is True or p.qb_hit is True:
            hits += 1
    return Component(
        id="ke.disruption_proxy_nfl",
        value=hits / len(usable),
        unit="rate",
        layer=Layer.DERIVED,
        status=Status.OK if len(usable) >= THIN_PLAYS_STD else Status.THIN,
        n=len(usable),
        notes={
            "events": ["sack", "interception", "qb_hit"],
            "must_not_be_named": "ke.havoc",
            "weight": None,
            "numerator": hits,
        },
    )


def havoc_component(audit: Dict[str, ColumnAudit]) -> Component:
    if named_havoc_allowed(audit):
        # Still omit the named rating in Phase 1 until a later certify-and-weight GO.
        return omitted(
            "ke.havoc",
            unit="rate",
            reason="TFL∧FF∧INT inventory-ok but named havoc waits for a certify/weight GO",
        )
    return omitted(
        "ke.havoc",
        unit="rate",
        reason="TFL and/or FF and/or INT uncertified — omit > impute",
    )
