"""Unit shock table + player-value dictionary (pts of KEI vs replacement).

When accept takes out **C / LT / EDGE1 / CB1 / S1**, remat surfaces that read
the pack (Week 1 KEI reprice / accept smoke) apply **one** role shock from
``SHOCK_TABLE_V1`` (``kei_live: true``).

**Research dictionary (v2):** RT / LG / RG / WR1 / TE1 / RB1 / DL1 / LB1 /
EDGE2 / CB2 live in ``DICTIONARY_RESEARCH`` with ``kei_live: false``. Week 1
KEI logs them on ``considered_not_applied`` with a stated point value and
does **not** apply them. Promoting a research role requires unused holdout
+ explicit Ryan flip — see ``NFL_PLAYER_VALUE_DICTIONARY.md``.

**No double-count:** a keystone player deletion must **not** also fire a full
unit wipe for the same event. Role shock replaces flat ``ol_out`` /
``defense_out`` for that row; unit wipe is explicitly skipped and logged.

**QB** stays on ``qb_confirmation`` — never in this table.

Out of scope (this module / PR): rest, weather, snap shares, auto-accept,
WAR leaderboard / product tile.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

SHOCK_TABLE_VERSION = "shock_table_v1"
DICTIONARY_VERSION = "player_value_dictionary_v1"

# Team-weaker spread / total points for keystone starter (or depth_slot=out) hits.
# Differentiated from flat ol_out (0.50/0.25) and defense_out (0.60/0.20).
# Locked Week 1 live magnitudes — do not retune without Ryan flip.
SHOCK_TABLE_V1: Dict[str, Dict[str, float]] = {
    "C": {"spread": 0.65, "total": 0.30},
    "LT": {"spread": 0.80, "total": 0.35},
    "EDGE1": {"spread": 0.85, "total": 0.25},
    "CB1": {"spread": 0.70, "total": 0.20},
    "S1": {"spread": 0.55, "total": 0.18},
}

# Research-only dictionary roles (same scale as v1; never invent 3-pt WR shocks).
# kei_live is always false here — logging only until Ryan flip + holdout.
DICTIONARY_RESEARCH: Dict[str, Dict[str, float]] = {
    "RT": {"spread": 0.70, "total": 0.30},  # below LT
    "LG": {"spread": 0.45, "total": 0.22},  # IOL class
    "RG": {"spread": 0.45, "total": 0.22},  # IOL class
    "WR1": {"spread": 0.70, "total": 0.35},
    "TE1": {"spread": 0.50, "total": 0.25},
    "RB1": {"spread": 0.55, "total": 0.28},
    "DL1": {"spread": 0.60, "total": 0.20},  # IDL / DL pack slot
    "LB1": {"spread": 0.50, "total": 0.18},
    "EDGE2": {"spread": 0.45, "total": 0.15},
    "CB2": {"spread": 0.40, "total": 0.12},
}

# Unified view for ops / tests: live + research with kei_live flag.
PLAYER_VALUE_DICTIONARY: Dict[str, Dict[str, Any]] = {
    **{
        role: {**pts, "kei_live": True, "source": SHOCK_TABLE_VERSION}
        for role, pts in SHOCK_TABLE_V1.items()
    },
    **{
        role: {**pts, "kei_live": False, "source": DICTIONARY_VERSION}
        for role, pts in DICTIONARY_RESEARCH.items()
    },
}

ROLE_TO_UNIT: Dict[str, str] = {
    "C": "ol",
    "LT": "ol",
    "RT": "ol",
    "LG": "ol",
    "RG": "ol",
    "EDGE1": "defense",
    "EDGE2": "defense",
    "CB1": "defense",
    "CB2": "defense",
    "S1": "defense",
    "DL1": "defense",
    "LB1": "defense",
    "WR1": "skill",
    "TE1": "skill",
    "RB1": "skill",
}

# Magnitudes that would have been a full-unit wipe — never stacked with a
# keystone role shock on the same unit/event.
UNIT_WIPE_V1: Dict[str, Dict[str, float]] = {
    "ol": {"spread": 2.0, "total": 1.0},
    "defense": {"spread": 2.2, "total": 0.8},
}

_OUT = frozenset({"out", "ir", "pup", "suspended", "inactive"})
_STARTER_SLOTS = frozenset({"starter", "starter_competition"})
_SKILL_RESEARCH_ROLES = frozenset({"WR1", "TE1", "RB1"})


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
    """Map a pack ol_roles / defense_roles row to a shock_table_v1 key (or None).

    Live keystones only. QB never resolves here.
    """
    pos = _pos(row.get("position"))
    if pos == "QB":
        return None
    order = _order(row)
    if not is_starterish(row) and order not in {0, 1}:
        return None
    if pos == "C":
        return "C"
    if pos == "LT":
        return "LT"
    if pos == "EDGE" and (order <= 1 or is_starterish(row)):
        # depth_order=2 EDGE is EDGE2 research — not EDGE1.
        if order == 2:
            return None
        return "EDGE1"
    if pos == "CB" and (order <= 1 or is_starterish(row)):
        if order == 2:
            return None
        return "CB1"
    if pos == "S" and (order <= 1 or is_starterish(row)):
        return "S1"
    return None


def resolve_dictionary_research_role(row: Mapping[str, Any]) -> Optional[str]:
    """Map a pack row to a research dictionary role (kei_live=false), or None.

    Does not return live keystones. QB never resolves here.
    """
    pos = _pos(row.get("position"))
    if pos == "QB":
        return None
    order = _order(row)

    # Skill SoT — WR1 / TE1 / RB1 only (depth_order 1 or starter who left).
    if pos == "WR":
        if order == 1 or order >= 90 or _slot(row) == "out":
            return "WR1"
        return None
    if pos == "TE":
        if order == 1 or order >= 90 or _slot(row) == "out":
            return "TE1"
        return None
    if pos in {"RB", "HB"}:
        if order == 1 or order >= 90 or _slot(row) == "out":
            return "RB1"
        return None

    # OL research — RT / IOL (LG, RG). Never C/LT (live).
    if pos == "RT" and (order <= 1 or is_starterish(row)):
        return "RT"
    if pos == "LG" and (order <= 1 or is_starterish(row)):
        return "LG"
    if pos == "RG" and (order <= 1 or is_starterish(row)):
        return "RG"

    # Defense research — DL1 / LB1 / EDGE2 / CB2.
    if pos in {"DL", "IDL", "DT", "NT"} and (order <= 1 or is_starterish(row)):
        if order == 2:
            return None
        return "DL1"
    if pos == "LB" and (order <= 1 or is_starterish(row)):
        if order == 2:
            return None
        return "LB1"
    if pos == "EDGE" and order == 2:
        return "EDGE2"
    if pos == "CB" and order == 2:
        return "CB2"
    return None


def dictionary_role_kei_live(role: str) -> bool:
    row = PLAYER_VALUE_DICTIONARY.get(role) or {}
    return bool(row.get("kei_live"))


@dataclass
class RoleShock:
    role: str
    unit: str
    team: str
    player_name: str
    spread_pts: float
    total_pts: float
    source: str = SHOCK_TABLE_VERSION
    kei_live: bool = True

    def reason(self) -> str:
        if self.kei_live:
            return (
                f"{self.player_name} {self.role} out — {self.source} "
                f"(no unit wipe)"
            )
        return (
            f"{self.player_name} {self.role} out — {self.source} research "
            f"would-be {self.spread_pts:.2f} spr / {self.total_pts:.2f} tot "
            f"(kei_live=false; not applied)"
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
    # Research dictionary hits — log only; never summed into team totals.
    research_hits: List[RoleShock] = field(default_factory=list)
    # Skill research rows that must skip flat skill_out (WR1/TE1/RB1).
    research_skill_row_keys: List[str] = field(default_factory=list)

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
    skill_rows: Sequence[Mapping[str, Any]] = (),
) -> ShockTableResult:
    """Apply shock_table_v1 for keystone outs; collect research dictionary hits.

    Live keystones skip unit wipe for those units. Research hits are attached
    for logging only (``kei_live=false``) and never enter ``role_shocks``.
    """
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
            source=SHOCK_TABLE_VERSION,
            kei_live=True,
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

    # Research dictionary — OL / DEF / skill. Never applied; never unit-wipe.
    live_keys = set(result.covered_row_keys)
    for row in list(ol_rows) + list(defense_rows) + list(skill_rows):
        row_team = str(row.get("team") or "").strip().upper()
        if row_team and row_team != team_u:
            continue
        if not is_out_row(row):
            continue
        key = _row_key(row)
        if key in live_keys:
            continue  # already a live keystone
        role = resolve_dictionary_research_role(row)
        if not role:
            continue
        pts = DICTIONARY_RESEARCH[role]
        unit = ROLE_TO_UNIT[role]
        name = str(row.get("player_name") or role)
        hit = RoleShock(
            role=role,
            unit=unit,
            team=team_u,
            player_name=name,
            spread_pts=float(pts["spread"]),
            total_pts=float(pts["total"]),
            source=DICTIONARY_VERSION,
            kei_live=False,
        )
        result.research_hits.append(hit)
        if role in _SKILL_RESEARCH_ROLES:
            result.research_skill_row_keys.append(key)
    return result


def row_covered_by_shock_table(row: Mapping[str, Any], result: ShockTableResult) -> bool:
    return _row_key(row) in set(result.covered_row_keys)


def row_covered_by_skill_research(
    row: Mapping[str, Any], result: ShockTableResult
) -> bool:
    """True when WR1/TE1/RB1 research hit should skip flat skill_out."""
    return _row_key(row) in set(result.research_skill_row_keys)
