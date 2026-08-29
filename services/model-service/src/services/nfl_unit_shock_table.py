"""Unit shock table v1 — keystone outs on DepthSot accept → remat / KEI.

When accept takes out **C / LT / EDGE1 / CB1 / S1**, remat surfaces that read
the pack (Week 1 KEI reprice / accept smoke) apply **one** role shock from
``SHOCK_TABLE_V1``.

**No double-count:** a keystone player deletion must **not** also fire a full
unit wipe for the same event. Role shock replaces flat ``ol_out`` /
``defense_out`` for that row; unit wipe is explicitly skipped and logged.

Out of scope (this module / PR): rest, weather, snap shares, auto-accept.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

SHOCK_TABLE_VERSION = "shock_table_v1"

# Team-weaker spread / total points for keystone starter (or depth_slot=out) hits.
# Differentiated from flat ol_out (0.50/0.25) and defense_out (0.60/0.20).
SHOCK_TABLE_V1: Dict[str, Dict[str, float]] = {
    "C": {"spread": 0.65, "total": 0.30},
    "LT": {"spread": 0.80, "total": 0.35},
    "EDGE1": {"spread": 0.85, "total": 0.25},
    "CB1": {"spread": 0.70, "total": 0.20},
    "S1": {"spread": 0.55, "total": 0.18},
}

ROLE_TO_UNIT: Dict[str, str] = {
    "C": "ol",
    "LT": "ol",
    "EDGE1": "defense",
    "CB1": "defense",
    "S1": "defense",
}

# Magnitudes that would have been a full-unit wipe — never stacked with a
# keystone role shock on the same unit/event.
UNIT_WIPE_V1: Dict[str, Dict[str, float]] = {
    "ol": {"spread": 2.0, "total": 1.0},
    "defense": {"spread": 2.2, "total": 0.8},
}

_OUT = frozenset({"out", "ir", "pup", "suspended", "inactive"})
_STARTER_SLOTS = frozenset({"starter", "starter_competition"})


def _status(raw: Any) -> str:
    return str(raw or "").strip().lower()


def _pos(raw: Any) -> str:
    return str(raw or "").strip().upper()


def _order(row: Mapping[str, Any]) -> int:
    try:
        return int(row.get("depth_order") or 0)
    except (TypeError, ValueError):
        return 0


def _slot(row: Mapping[str, Any]) -> str:
    return str(row.get("depth_slot") or "").strip().lower()


def is_out_row(row: Mapping[str, Any]) -> bool:
    if _status(row.get("injury_status")) in _OUT:
        return True
    return _slot(row) == "out" or _order(row) >= 90


def is_starterish(row: Mapping[str, Any]) -> bool:
    order = _order(row)
    slot = _slot(row)
    if order == 1:
        return True
    if slot in _STARTER_SLOTS:
        return True
    # Desk ``depth_slot=out`` with order>=90 still counts as the starter who left.
    if slot == "out" or order >= 90:
        return True
    return False


def resolve_shock_role(row: Mapping[str, Any]) -> Optional[str]:
    """Map a pack ol_roles / defense_roles row to a shock_table_v1 key (or None)."""
    pos = _pos(row.get("position"))
    order = _order(row)
    if not is_starterish(row) and order not in {0, 1}:
        return None
    if pos == "C":
        return "C"
    if pos == "LT":
        return "LT"
    if pos == "EDGE" and (order <= 1 or is_starterish(row)):
        return "EDGE1"
    if pos == "CB" and (order <= 1 or is_starterish(row)):
        return "CB1"
    if pos == "S" and (order <= 1 or is_starterish(row)):
        return "S1"
    return None


@dataclass
class RoleShock:
    role: str
    unit: str
    team: str
    player_name: str
    spread_pts: float
    total_pts: float
    source: str = SHOCK_TABLE_VERSION

    def reason(self) -> str:
        return (
            f"{self.player_name} {self.role} out — {self.source} "
            f"(no unit wipe)"
        )


@dataclass
class UnitWipeSkip:
    unit: str
    team: str
    covered_by_roles: Tuple[str, ...]
    spread_pts_not_applied: float
    total_pts_not_applied: float

    def reason(self) -> str:
        roles = ",".join(self.covered_by_roles) or "?"
        return (
            f"{self.team} {self.unit} unit wipe skipped — "
            f"{SHOCK_TABLE_VERSION} already applied ({roles}); no double-count"
        )


@dataclass
class ShockTableResult:
    role_shocks: List[RoleShock] = field(default_factory=list)
    unit_wipe_skips: List[UnitWipeSkip] = field(default_factory=list)
    # Rows that already consumed shock_table (do not also add flat ol/def pts).
    covered_row_keys: List[str] = field(default_factory=list)

    def team_spread_total(self, team: str) -> Tuple[float, float]:
        spr = tot = 0.0
        for s in self.role_shocks:
            if s.team == team:
                spr += s.spread_pts
                tot += s.total_pts
        return spr, tot


def _row_key(row: Mapping[str, Any]) -> str:
    pid = str(row.get("player_id") or "").strip()
    if pid:
        return pid
    return (
        f"{_pos(row.get('team'))}:{_pos(row.get('position'))}:"
        f"{row.get('player_name') or ''}:{_order(row)}"
    )


def collect_shock_table_v1(
    *,
    team: str,
    ol_rows: Sequence[Mapping[str, Any]] = (),
    defense_rows: Sequence[Mapping[str, Any]] = (),
) -> ShockTableResult:
    """Apply shock_table_v1 for keystone outs; skip unit wipe for those units."""
    team_u = str(team or "").strip().upper()
    result = ShockTableResult()
    units_hit: Dict[str, List[str]] = {}

    for row in list(ol_rows) + list(defense_rows):
        row_team = str(row.get("team") or "").strip().upper()
        if row_team and row_team != team_u:
            continue
        if not is_out_row(row):
            continue
        role = resolve_shock_role(row)
        if not role:
            continue
        pts = SHOCK_TABLE_V1[role]
        unit = ROLE_TO_UNIT[role]
        name = str(row.get("player_name") or role)
        shock = RoleShock(
            role=role,
            unit=unit,
            team=team_u,
            player_name=name,
            spread_pts=float(pts["spread"]),
            total_pts=float(pts["total"]),
        )
        result.role_shocks.append(shock)
        result.covered_row_keys.append(_row_key(row))
        units_hit.setdefault(unit, []).append(role)

    for unit, roles in units_hit.items():
        wipe = UNIT_WIPE_V1[unit]
        result.unit_wipe_skips.append(
            UnitWipeSkip(
                unit=unit,
                team=team_u,
                covered_by_roles=tuple(roles),
                spread_pts_not_applied=float(wipe["spread"]),
                total_pts_not_applied=float(wipe["total"]),
            )
        )
    return result


def row_covered_by_shock_table(row: Mapping[str, Any], result: ShockTableResult) -> bool:
    return _row_key(row) in set(result.covered_row_keys)
