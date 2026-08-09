"""Transparent OL → protection / efficiency feature (Phase 2).

Replaces the pure OL→EPA stub and named-team ``RB_OL_PROXY_BUMP`` piles with
an inspectable protection index derived from SoT ``ol_roles``.

Formula (documented — small, directional, not a calibrated EPA model):

  protection_index starts at 1.0
  For each starting-slot hit (depth_order==1 or depth_slot starter*):
    LT / RT out or injured-out : −0.055 each (blindside / edge)
    C out or injured-out       : −0.040
    LG / RG out                : −0.025 each
    starter_competition (not locked) on any OL slot: −0.012 each
  Clamp protection_index to [0.82, 1.05]

Derived multipliers (applied modestly; conservation still owns pools):
  ypa_mult            = 0.55 + 0.45 * protection_index   → [0.90, 1.02]
  offense_index_delta = 0.12 * (protection_index − 1.0)  → ≈ [−0.022, +0.006]
  rb_ypc_bump_yards   = 80.0 * (protection_index − 0.92) → soft RB prior nudge

No invented injury→power beyond these terms. Missing ``ol_roles`` → neutral
1.0 (honest gap stays labeled, not magicked).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

OL_PROTECTION_VERSION = "ol-protection-v1"
OL_PROTECTION_REVISIT_BY = "2026-10-01"

_EDGE = frozenset({"LT", "RT", "T", "OT"})
_INTERIOR_G = frozenset({"LG", "RG", "G", "OG"})
_CENTER = frozenset({"C"})
_OUT_STATUS = frozenset({"out", "ir", "pup", "suspended", "inactive"})


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _norm_pos(raw: Any) -> str:
    return str(raw or "").strip().upper()


def _is_starter_slot(row: Mapping[str, Any]) -> bool:
    try:
        depth = int(row.get("depth_order") or 99)
    except (TypeError, ValueError):
        depth = 99
    slot = str(row.get("depth_slot") or "").strip().lower()
    if depth == 1:
        return True
    if slot in {"starter", "starter_competition"}:
        return True
    return False


def _is_out(row: Mapping[str, Any]) -> bool:
    status = str(row.get("injury_status") or "").strip().lower()
    slot = str(row.get("depth_slot") or "").strip().lower()
    if status in _OUT_STATUS:
        return True
    if slot == "out":
        return True
    return False


def _is_competition(row: Mapping[str, Any]) -> bool:
    slot = str(row.get("depth_slot") or "").strip().lower()
    return "competition" in slot or slot == "starter_competition"


@dataclass(frozen=True)
class OlProtectionFeature:
    """Per-team OL protection feature from SoT ol_roles."""

    team: str
    protection_index: float
    ypa_mult: float
    offense_index_delta: float
    rb_ypc_bump_yards: float
    drivers: Tuple[str, ...] = ()
    fidelity: str = "applied"  # applied | missing_neutral
    source: str = "ol_roles_sot"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "team": self.team,
            "protection_index": round(self.protection_index, 4),
            "ypa_mult": round(self.ypa_mult, 4),
            "offense_index_delta": round(self.offense_index_delta, 5),
            "rb_ypc_bump_yards": round(self.rb_ypc_bump_yards, 2),
            "drivers": list(self.drivers),
            "fidelity": self.fidelity,
            "source": self.source,
            "version": OL_PROTECTION_VERSION,
            "revisit_by": OL_PROTECTION_REVISIT_BY,
            "formula": (
                "protection=1.0 − edge_out*0.055 − C_out*0.040 − G_out*0.025 "
                "− competition*0.012; clamp[0.82,1.05]; "
                "ypa_mult=0.55+0.45*protection; "
                "offense_delta=0.12*(protection−1); "
                "rb_bump=80*(protection−0.92)"
            ),
        }


def neutral_ol_protection(team: str) -> OlProtectionFeature:
    return OlProtectionFeature(
        team=str(team or "").upper(),
        protection_index=1.0,
        ypa_mult=1.0,
        offense_index_delta=0.0,
        rb_ypc_bump_yards=80.0 * (1.0 - 0.92),
        drivers=("missing_ol_roles_neutral",),
        fidelity="missing_neutral",
        source="neutral_default",
    )


def compute_ol_protection(
    team: str,
    ol_roles: Sequence[Mapping[str, Any]],
) -> OlProtectionFeature:
    """Build protection feature for one team from ol_roles rows."""
    team_u = str(team or "").upper()
    rows = [
        r
        for r in ol_roles
        if str(r.get("team") or "").strip().upper() == team_u
    ]
    if not rows:
        return neutral_ol_protection(team_u)

    index = 1.0
    drivers: List[str] = []
    seen_comp: set[str] = set()

    for row in rows:
        pos = _norm_pos(row.get("position"))
        name = str(row.get("player_name") or pos or "OL")
        if _is_out(row) and (_is_starter_slot(row) or str(row.get("depth_slot")) == "out"):
            if pos in _EDGE:
                index -= 0.055
                drivers.append(f"edge_out:{name}")
            elif pos in _CENTER:
                index -= 0.040
                drivers.append(f"center_out:{name}")
            elif pos in _INTERIOR_G:
                index -= 0.025
                drivers.append(f"guard_out:{name}")
            else:
                index -= 0.020
                drivers.append(f"ol_out:{name}")
        if _is_competition(row) and pos not in seen_comp:
            seen_comp.add(pos)
            index -= 0.012
            drivers.append(f"competition:{pos}")

    index = _clamp(index, 0.82, 1.05)
    ypa_mult = _clamp(0.55 + 0.45 * index, 0.90, 1.02)
    offense_delta = 0.12 * (index - 1.0)
    rb_bump = 80.0 * (index - 0.92)
    return OlProtectionFeature(
        team=team_u,
        protection_index=round(index, 4),
        ypa_mult=round(ypa_mult, 4),
        offense_index_delta=round(offense_delta, 5),
        rb_ypc_bump_yards=round(rb_bump, 2),
        drivers=tuple(drivers) if drivers else ("healthy_ol_baseline",),
        fidelity="applied",
        source="ol_roles_sot",
    )


def build_ol_protection_book(
    ol_roles: Sequence[Mapping[str, Any]],
    teams: Optional[Iterable[str]] = None,
) -> Dict[str, OlProtectionFeature]:
    """Per-team protection book. Teams with no rows → neutral."""
    team_set = {str(t).upper() for t in (teams or [])}
    if not team_set:
        team_set = {
            str(r.get("team") or "").strip().upper()
            for r in ol_roles
            if r.get("team")
        }
    return {t: compute_ol_protection(t, ol_roles) for t in sorted(team_set) if t}


def apply_ol_protection_to_strength(
    offense_index: float,
    protection: Optional[OlProtectionFeature],
) -> float:
    """Modest offense_index nudge from protection (no magic EPA scale)."""
    if protection is None or protection.fidelity == "missing_neutral":
        return float(offense_index)
    return _clamp(float(offense_index) + float(protection.offense_index_delta), 0.80, 1.25)
