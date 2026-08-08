"""Injury & availability path shocks for the hierarchical season engine.

Applies explicit, inspectable availability paths onto Layers 1 and 3
(team strength + player usage). Layer 2 (game script) and Layer 4
(production) respond automatically via adjusted O/D indices and role shares.

Statuses
--------
- ``out``       – availability 0.0 for weeks in [week_start, week_end]
- ``limited``   – fixed availability fraction (default 0.50) in range
- ``returning`` – linear ramp from ``availability`` (default 0.40) → 1.0
                  across the inclusive week range

Team-strength impact (value-weighted, offense_index only)
---------------------------------------------------------
Missing-player offense delta ≈ −value × (1 − availability), where value
is derived from position + depth + absolute usage shares (see
``player_offense_value``). Defense index is untouched. Pass-rate bias
nudges slightly when a primary RB or WR is unavailable.

Usage reallocation (role-aware, residual-bucket aware)
------------------------------------------------------
Freed volume = role_share × (1 − availability). Of that freed volume:

* Role-taxonomy sinks (see ``usage_roles.INJURY_REALLOC_RULES``) — e.g.
  RB1 out → RB2 gets the largest rush share (not equal committee split);
  WR1 out → WR2 > WR_SLOT > WR3; TE1 out → TE2 + differentiated WR mix.
* Cross-position spill remains explicit and small.
* A residual fraction stays in the calibration "other" bucket so sparse
  skill rosters do not over-inflate named backups (same spirit as
  ``USAGE_OTHER_BUCKET_FLOOR``).

QB out: starter snap/rush collapse; QB2 inherits pass-attempt weight via
elevated snap_share (Layer 3 starter draw already respects snap weights).

Paths outside the active week leave roles and strengths unchanged.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import (
    Any,
    Dict,
    List,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Tuple,
)

from src.services.nfl_season_engine.calibration import USAGE_OTHER_BUCKET_FLOOR
from src.services.nfl_season_engine.depth_chart import (
    classify_team_depth,
    committee_remaining_rush_weights,
    promote_roles_after_injury,
)
from src.services.nfl_season_engine.types import PlayerRole, TeamStrengthState
from src.services.nfl_season_engine.usage_roles import (
    INJURY_REALLOC_RULES,
    annotate_usage_roles,
    split_by_role_sinks,
)

InjuryStatus = Literal["out", "limited", "returning"]

# Fraction of freed volume that stays in residual "other" (not reassigned
# to named skill players). Mirrors absolute-share philosophy.
REALLOC_OTHER_FRACTION = max(0.10, USAGE_OTHER_BUCKET_FLOOR)

# Default availability when status=limited / returning and caller omits it.
DEFAULT_LIMITED_AVAILABILITY = 0.50
DEFAULT_RETURNING_START_AVAILABILITY = 0.40

# Cap cumulative offense shock from stacked injuries in one week.
MAX_OFFENSE_SHOCK = 0.22


@dataclass(frozen=True)
class InjuryPath:
    """One player's availability schedule inside a season sim / game query."""

    team: str
    status: InjuryStatus
    week_start: int
    week_end: int
    player_key: str = ""
    player_name: str = ""
    # For limited: fixed fraction. For returning: ramp start fraction.
    availability: Optional[float] = None
    severity: Optional[float] = None  # optional 0–1 metadata; does not drive math alone

    def __post_init__(self) -> None:
        if self.week_end < self.week_start:
            raise ValueError(
                f"week_end ({self.week_end}) must be >= week_start ({self.week_start})"
            )
        if self.status not in ("out", "limited", "returning"):
            raise ValueError(f"unsupported injury status: {self.status!r}")
        if not self.player_key and not self.player_name:
            raise ValueError("InjuryPath requires player_key or player_name")


@dataclass
class AvailabilityAdjustment:
    """Inspectable record of what an injury path did for one week."""

    player_key: str
    player_name: str
    team: str
    week: int
    status: InjuryStatus
    availability: float
    offense_delta: float
    freed_target_share: float
    freed_rush_share: float
    realloc_notes: str = ""


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def normalize_team_code(team: str) -> str:
    """Normalize common aliases (LAR→LA). Empty stays empty."""
    t = str(team or "").strip().upper()
    if t == "LAR":
        return "LA"
    return t


def _name_tokens(name: str) -> Tuple[str, ...]:
    """Tokenize player names for dual-form matching.

    ``C.McCaffrey`` → ``("c", "mccaffrey")``;
    ``Christian McCaffrey`` → ``("christian", "mccaffrey")``;
    ``A.St. Brown`` → ``("a", "st", "brown")``.
    """
    cleaned = re.sub(r"[^a-z0-9\s.]", " ", (name or "").lower())
    parts = [p for p in cleaned.replace(".", " ").split() if p]
    return tuple(parts)


def names_match(path_name: str, role_name: str) -> bool:
    """True when path name and roster name refer to the same player.

    Handles exact, substring, and initial.last ↔ First Last forms.
    Last-name-only paths match when the last token equals the role last
    token (callers should prefer unique-on-team disambiguation).
    """
    a = (path_name or "").strip().lower()
    b = (role_name or "").strip().lower()
    if not a or not b:
        return False
    if a == b or a in b or b in a:
        return True
    ta, tb = _name_tokens(a), _name_tokens(b)
    if not ta or not tb:
        return False
    if ta[-1] != tb[-1]:
        return False
    # Last names match. Accept single-token last-name-only paths.
    if len(ta) == 1 or len(tb) == 1:
        return True
    fa, fb = ta[0], tb[0]
    if fa == fb:
        return True
    # Initial ↔ full first name (C ↔ Christian).
    if len(fa) == 1 and fb.startswith(fa):
        return True
    if len(fb) == 1 and fa.startswith(fb):
        return True
    return False


def parse_injury_paths(raw: Optional[Sequence[Mapping[str, Any]]]) -> List[InjuryPath]:
    """Parse API/CLI JSON dicts into ``InjuryPath`` rows. Empty/None → []."""
    if not raw:
        return []
    out: List[InjuryPath] = []
    for row in raw:
        if not isinstance(row, Mapping):
            continue
        status = str(row.get("status") or "out").strip().lower()
        if status not in ("out", "limited", "returning"):
            raise ValueError(f"unsupported injury status: {status!r}")
        avail = row.get("availability", row.get("availability_fraction"))
        severity = row.get("severity")
        out.append(
            InjuryPath(
                team=normalize_team_code(str(row.get("team") or "")),
                status=status,  # type: ignore[arg-type]
                week_start=int(row["week_start"]),
                week_end=int(row["week_end"]),
                player_key=str(row.get("player_key") or row.get("player_id") or ""),
                player_name=str(row.get("player_name") or row.get("name") or ""),
                availability=float(avail) if avail is not None else None,
                severity=float(severity) if severity is not None else None,
            )
        )
    return out


def injury_paths_to_dicts(paths: Sequence[InjuryPath]) -> List[Dict[str, Any]]:
    return [
        {
            "player_key": p.player_key,
            "player_name": p.player_name,
            "team": p.team,
            "status": p.status,
            "week_start": p.week_start,
            "week_end": p.week_end,
            "availability": p.availability,
            "severity": p.severity,
        }
        for p in paths
    ]


def availability_for_week(path: InjuryPath, week: int) -> float:
    """Return availability in [0, 1] for ``week``. 1.0 = fully available (path inactive)."""
    if week < path.week_start or week > path.week_end:
        return 1.0
    if path.status == "out":
        return 0.0
    if path.status == "limited":
        base = (
            DEFAULT_LIMITED_AVAILABILITY
            if path.availability is None
            else float(path.availability)
        )
        if path.severity is not None:
            # Severity nudges limited availability downward (optional).
            base = base * (1.0 - 0.35 * _clamp(float(path.severity), 0.0, 1.0))
        return _clamp(base, 0.0, 1.0)
    # returning — linear ramp from start_avail → 1.0 inclusive
    start = (
        DEFAULT_RETURNING_START_AVAILABILITY
        if path.availability is None
        else float(path.availability)
    )
    start = _clamp(start, 0.0, 1.0)
    span = path.week_end - path.week_start
    if span <= 0:
        return 1.0
    t = (week - path.week_start) / float(span)
    return _clamp(start + (1.0 - start) * t, 0.0, 1.0)


def player_offense_value(role: PlayerRole) -> float:
    """Transparent offense-index value weight for one skill role (full-season healthy).

    Anchored so a QB1 out ≈ −0.12 O, RB1 workhorse ≈ −0.05, WR1 ≈ −0.04.
    """
    pos = (role.position or "").upper()
    depth = max(1, int(role.depth_order or 1))
    if pos == "QB":
        return 0.12 if depth == 1 else 0.035
    if pos == "RB":
        rush = max(0.0, float(role.rush_share))
        tgt = max(0.0, float(role.target_share))
        return _clamp(0.035 * (rush / 0.50) + 0.020 * (tgt / 0.12) + (0.01 if depth == 1 else 0.0), 0.01, 0.08)
    if pos == "WR":
        tgt = max(0.0, float(role.target_share))
        return _clamp(0.038 * (tgt / 0.22) + (0.008 if depth == 1 else 0.0), 0.008, 0.06)
    if pos == "TE":
        tgt = max(0.0, float(role.target_share))
        return _clamp(0.028 * (tgt / 0.14) + (0.006 if depth == 1 else 0.0), 0.006, 0.045)
    return 0.01


def _matches_path(role: PlayerRole, path: InjuryPath) -> bool:
    path_team = normalize_team_code(path.team)
    role_team = normalize_team_code(role.team)
    if path_team and role_team != path_team:
        return False
    if path.player_key:
        return role.player_key == path.player_key
    if not (path.player_name or "").strip():
        return False
    return names_match(path.player_name, role.player_name)


def _find_role(
    rosters: Mapping[str, Sequence[PlayerRole]],
    path: InjuryPath,
) -> Optional[PlayerRole]:
    path_team = normalize_team_code(path.team)
    teams = [path_team] if path_team else list(rosters.keys())
    # Prefer exact key, then dual-form name match on the declared team.
    for team in teams:
        team_roles = list(rosters.get(team, []))
        if path.player_key:
            for role in team_roles:
                if role.player_key == path.player_key:
                    return role
        name_hits = [
            role for role in team_roles if names_match(path.player_name, role.player_name)
        ]
        if len(name_hits) == 1:
            return name_hits[0]
        if len(name_hits) > 1 and path.player_name:
            # Disambiguate: prefer deeper first-token agreement.
            tokens = _name_tokens(path.player_name)
            if tokens:
                for role in name_hits:
                    rt = _name_tokens(role.player_name)
                    if rt and (rt[0] == tokens[0] or rt[0][:1] == tokens[0][:1]):
                        return role
            return name_hits[0]
    # Fallback: scan all teams by key/name when team omitted / mistyped.
    for roles in rosters.values():
        for role in roles:
            if path.player_key and role.player_key == path.player_key:
                return role
            if path.player_name and names_match(path.player_name, role.player_name):
                return role
    return None


def _depth_weight(role: PlayerRole) -> float:
    return {1: 1.0, 2: 0.70, 3: 0.45}.get(int(role.depth_order or 1), 0.25)


def _allocate_freed(
    *,
    amount: float,
    candidates: Sequence[PlayerRole],
    weight_fn,
) -> Dict[str, float]:
    """Split ``amount`` across candidates by weight_fn; empty → {}."""
    if amount <= 1e-12 or not candidates:
        return {}
    weights = [max(1e-6, float(weight_fn(r))) for r in candidates]
    total = sum(weights)
    return {r.player_key: amount * (w / total) for r, w in zip(candidates, weights)}


def _merge_boost(dst: Dict[str, float], src: Mapping[str, float]) -> None:
    for k, v in src.items():
        dst[k] = dst.get(k, 0.0) + v


def reallocate_role_shares(
    roles: Sequence[PlayerRole],
    *,
    injured: PlayerRole,
    availability: float,
) -> Tuple[List[PlayerRole], str]:
    """Scale injured role by availability and reallocate freed volume.

    Uses ``usage_roles.INJURY_REALLOC_RULES`` when the injured player's
    usage_role is known; falls back to position-aware depth weights.

    Returns (new_roles_same_order, human-readable rule note).
    """
    avail = _clamp(availability, 0.0, 1.0)
    missing = 1.0 - avail
    if missing <= 1e-12:
        return list(roles), "no_reallocation_full_availability"

    # Ensure taxonomy labels exist before looking up sink rules.
    roles = annotate_usage_roles(roles)
    injured = next((r for r in roles if r.player_key == injured.player_key), injured)
    injured = annotate_usage_roles([injured])[0] if not injured.usage_role else injured

    freed_tgt = max(0.0, injured.target_share) * missing
    freed_rush = max(0.0, injured.rush_share) * missing
    freed_snap = max(0.0, injured.snap_share) * missing
    freed_route = max(0.0, injured.route_share) * missing
    freed_rz = max(0.0, injured.red_zone_share) * missing

    # Keep a residual slice in the "other" bucket.
    keep_other = REALLOC_OTHER_FRACTION
    assign_frac = 1.0 - keep_other
    assign_tgt = freed_tgt * assign_frac
    assign_rush = freed_rush * assign_frac
    assign_snap = freed_snap * assign_frac
    assign_route = freed_route * assign_frac
    assign_rz = freed_rz * assign_frac

    others = [r for r in roles if r.player_key != injured.player_key]
    pos = (injured.position or "").upper()
    label = injured.usage_role or ""
    rules = INJURY_REALLOC_RULES.get(label) or {}

    tgt_boost: Dict[str, float] = {}
    rush_boost: Dict[str, float] = {}
    snap_boost: Dict[str, float] = {}
    route_boost: Dict[str, float] = {}
    notes: List[str] = []

    rbs = [r for r in others if r.position == "RB"]
    wrs = [r for r in others if r.position == "WR"]
    tes = [r for r in others if r.position == "TE"]
    qbs = [r for r in others if r.position == "QB"]
    structure = classify_team_depth(injured.team, roles)

    if pos == "RB" and rules:
        rush_sinks = rules.get("rush_sinks") or {}
        # Feature RB1 out → RB2 inherits feature-like lion's share.
        # Committee out → redistribute across remaining with uneven weights.
        if (
            structure.rb_structure == "feature"
            and label == "RB1"
            and rbs
        ):
            # Prefer RB2 sink; give feature-like concentration (~68% of assignable).
            rush_boost = split_by_role_sinks(
                assign_rush,
                rbs,
                {"RB2": 0.68, "RB_COMMITTEE": 0.18, "OTHER_RB": 0.14, "RB1": 0.0},
            )
            notes.append(
                "feature_RB1_out→RB2 inherits feature-like share; "
                f"{keep_other:.0%} residual→other"
            )
        elif structure.rb_structure == "committee" or label == "RB_COMMITTEE":
            weights = committee_remaining_rush_weights(len(rbs))
            if rbs and assign_rush > 1e-12:
                # Uneven depth-order weights (58/42 or 45/35/20), not equal.
                wsum = sum(weights.get(int(r.depth_order or 1), 0.20) for r in rbs)
                if wsum <= 1e-12:
                    wsum = float(len(rbs))
                    rush_boost = {
                        r.player_key: assign_rush / wsum for r in rbs
                    }
                else:
                    rush_boost = {
                        r.player_key: assign_rush
                        * (weights.get(int(r.depth_order or 1), 0.20) / wsum)
                        for r in rbs
                    }
            notes.append(
                f"committee_RB_out→uneven remaining split; {keep_other:.0%} residual→other"
            )
        else:
            rush_boost = split_by_role_sinks(assign_rush, rbs, rush_sinks)
            notes.append(f"{rules.get('note', 'RB_role_realloc')}; {keep_other:.0%} residual→other")
        split = rules.get("target_split") or {"same_pos": 0.65, "WR": 0.22, "TE": 0.13}
        same_sinks = rules.get("same_pos_tgt_sinks") or rush_sinks
        if structure.rb_structure == "committee" or label == "RB_COMMITTEE":
            # Mirror rush unevenness for same-pos targets.
            same_amt = assign_tgt * float(split.get("same_pos", 0.65))
            weights = committee_remaining_rush_weights(len(rbs))
            if rbs and same_amt > 1e-12:
                wsum = sum(weights.get(int(r.depth_order or 1), 0.20) for r in rbs) or float(
                    len(rbs)
                )
                _merge_boost(
                    tgt_boost,
                    {
                        r.player_key: same_amt
                        * (weights.get(int(r.depth_order or 1), 0.20) / wsum)
                        for r in rbs
                    },
                )
        else:
            _merge_boost(
                tgt_boost,
                split_by_role_sinks(
                    assign_tgt * float(split.get("same_pos", 0.65)), rbs, same_sinks
                ),
            )
        _merge_boost(
            tgt_boost,
            split_by_role_sinks(
                assign_tgt * float(split.get("WR", 0.22)),
                wrs,
                {"WR1": 0.40, "WR2": 0.30, "WR_SLOT": 0.18, "WR3": 0.12},
            ),
        )
        _merge_boost(
            tgt_boost,
            split_by_role_sinks(
                assign_tgt * float(split.get("TE", 0.13)),
                tes,
                {"TE1": 0.70, "TE2": 0.30},
            ),
        )
        if structure.rb_structure == "committee" or label == "RB_COMMITTEE":
            weights = committee_remaining_rush_weights(len(rbs))
            if rbs and assign_snap > 1e-12:
                wsum = sum(weights.get(int(r.depth_order or 1), 0.20) for r in rbs) or float(
                    len(rbs)
                )
                snap_boost = {
                    r.player_key: assign_snap
                    * (weights.get(int(r.depth_order or 1), 0.20) / wsum)
                    for r in rbs
                }
            else:
                snap_boost = {}
        else:
            snap_boost = split_by_role_sinks(assign_snap, rbs or others, rush_sinks)
    elif pos == "WR" and rules:
        split = rules.get("target_split") or {"WR": 0.62, "TE": 0.22, "RB": 0.16}
        wr_sinks = rules.get("wr_sinks") or {}
        te_sinks = rules.get("te_sinks") or {"TE1": 0.70, "TE2": 0.30}
        rb_sinks = rules.get("rb_sinks") or {"RB1": 0.55, "RB2": 0.25, "RB_COMMITTEE": 0.20}
        _merge_boost(
            tgt_boost,
            split_by_role_sinks(assign_tgt * float(split.get("WR", 0.62)), wrs, wr_sinks),
        )
        _merge_boost(
            tgt_boost,
            split_by_role_sinks(assign_tgt * float(split.get("TE", 0.22)), tes, te_sinks),
        )
        _merge_boost(
            tgt_boost,
            split_by_role_sinks(assign_tgt * float(split.get("RB", 0.16)), rbs, rb_sinks),
        )
        snap_boost = split_by_role_sinks(assign_snap, wrs or others, wr_sinks)
        route_boost = split_by_role_sinks(assign_route, wrs or others, wr_sinks)
        notes.append(f"{rules.get('note', 'WR_role_realloc')}; {keep_other:.0%} residual→other")
    elif pos == "TE" and rules:
        split = rules.get("target_split") or {"TE": 0.38, "WR": 0.52, "RB": 0.10}
        te_sinks = rules.get("te_sinks") or {"TE2": 0.85, "OTHER_TE": 0.15}
        wr_sinks = rules.get("wr_sinks") or {
            "WR1": 0.35,
            "WR2": 0.28,
            "WR_SLOT": 0.22,
            "WR3": 0.15,
        }
        rb_sinks = rules.get("rb_sinks") or {"RB1": 0.60, "RB2": 0.25, "RB_COMMITTEE": 0.15}
        _merge_boost(
            tgt_boost,
            split_by_role_sinks(assign_tgt * float(split.get("TE", 0.38)), tes, te_sinks),
        )
        _merge_boost(
            tgt_boost,
            split_by_role_sinks(assign_tgt * float(split.get("WR", 0.52)), wrs, wr_sinks),
        )
        _merge_boost(
            tgt_boost,
            split_by_role_sinks(assign_tgt * float(split.get("RB", 0.10)), rbs, rb_sinks),
        )
        snap_boost = split_by_role_sinks(
            assign_snap, (tes + wrs[:2]) if (tes or wrs) else others, {**te_sinks, **wr_sinks}
        )
        notes.append(f"{rules.get('note', 'TE_role_realloc')}; {keep_other:.0%} residual→other")
    elif pos == "QB" and rules:
        snap_sinks = rules.get("snap_sinks") or {"QB2": 0.90, "OTHER_QB": 0.10}
        snap_boost = split_by_role_sinks(assign_snap, qbs, snap_sinks)
        rb_frac = float(rules.get("rush_to_rb_frac", 0.35))
        rush_boost = split_by_role_sinks(
            assign_rush * rb_frac,
            rbs,
            {"RB1": 0.55, "RB2": 0.25, "RB_COMMITTEE": 0.20},
        )
        notes.append(f"{rules.get('note', 'QB_role_realloc')}; {keep_other:.0%} residual→other")
    elif pos == "RB":
        # Fallback without label — depth-weighted (v1.2 behavior).
        rush_boost = _allocate_freed(
            amount=assign_rush,
            candidates=rbs,
            weight_fn=lambda r: _depth_weight(r) * (0.35 + max(0.0, r.rush_share)),
        )
        for k, v in _allocate_freed(
            amount=assign_tgt * 0.70,
            candidates=rbs,
            weight_fn=lambda r: _depth_weight(r) * (0.25 + max(0.0, r.target_share)),
        ).items():
            tgt_boost[k] = tgt_boost.get(k, 0.0) + v
        for k, v in _allocate_freed(
            amount=assign_tgt * 0.30,
            candidates=wrs + tes,
            weight_fn=lambda r: _depth_weight(r) * (0.20 + max(0.0, r.target_share)),
        ).items():
            tgt_boost[k] = tgt_boost.get(k, 0.0) + v
        snap_boost = _allocate_freed(
            amount=assign_snap, candidates=rbs or others, weight_fn=_depth_weight
        )
        notes.append(
            f"RB_out→depth-weighted fallback; {keep_other:.0%} residual→other"
        )
    elif pos == "WR":
        for k, v in _allocate_freed(
            amount=assign_tgt * 0.70,
            candidates=wrs,
            weight_fn=lambda r: _depth_weight(r) * (0.25 + max(0.0, r.target_share)),
        ).items():
            tgt_boost[k] = tgt_boost.get(k, 0.0) + v
        for k, v in _allocate_freed(
            amount=assign_tgt * 0.20,
            candidates=tes,
            weight_fn=lambda r: _depth_weight(r) * (0.25 + max(0.0, r.target_share)),
        ).items():
            tgt_boost[k] = tgt_boost.get(k, 0.0) + v
        for k, v in _allocate_freed(
            amount=assign_tgt * 0.10,
            candidates=rbs,
            weight_fn=lambda r: _depth_weight(r) * (0.20 + max(0.0, r.target_share)),
        ).items():
            tgt_boost[k] = tgt_boost.get(k, 0.0) + v
        snap_boost = _allocate_freed(
            amount=assign_snap, candidates=wrs or others, weight_fn=_depth_weight
        )
        route_boost = _allocate_freed(
            amount=assign_route,
            candidates=wrs or others,
            weight_fn=lambda r: _depth_weight(r) * (0.2 + max(0.0, r.route_share)),
        )
        notes.append(
            f"WR_out→depth-weighted fallback; {keep_other:.0%} residual→other"
        )
    elif pos == "TE":
        for k, v in _allocate_freed(
            amount=assign_tgt * 0.35,
            candidates=tes,
            weight_fn=lambda r: _depth_weight(r) * (0.25 + max(0.0, r.target_share)),
        ).items():
            tgt_boost[k] = tgt_boost.get(k, 0.0) + v
        for k, v in _allocate_freed(
            amount=assign_tgt * 0.65,
            candidates=wrs,
            weight_fn=lambda r: _depth_weight(r) * (0.25 + max(0.0, r.target_share)),
        ).items():
            tgt_boost[k] = tgt_boost.get(k, 0.0) + v
        snap_boost = _allocate_freed(
            amount=assign_snap,
            candidates=tes + wrs[:2] if (tes or wrs) else others,
            weight_fn=_depth_weight,
        )
        notes.append(
            f"TE_out→depth-weighted fallback; {keep_other:.0%} residual→other"
        )
    elif pos == "QB":
        snap_boost = _allocate_freed(amount=assign_snap, candidates=qbs, weight_fn=_depth_weight)
        rush_boost = _allocate_freed(
            amount=assign_rush * 0.35,
            candidates=rbs,
            weight_fn=lambda r: _depth_weight(r) * (0.3 + max(0.0, r.rush_share)),
        )
        notes.append(
            f"QB_out→depth-weighted fallback; {keep_other:.0%} residual→other"
        )
    else:
        snap_boost = _allocate_freed(amount=assign_snap, candidates=others, weight_fn=_depth_weight)
        tgt_boost = _allocate_freed(amount=assign_tgt, candidates=others, weight_fn=_depth_weight)
        rush_boost = _allocate_freed(amount=assign_rush, candidates=others, weight_fn=_depth_weight)
        notes.append("generic_depth_weighted_reallocation")

    rz_boost = _allocate_freed(
        amount=assign_rz,
        candidates=[r for r in others if r.position == injured.position] or others,
        weight_fn=lambda r: _depth_weight(r) * (0.2 + max(0.0, r.red_zone_share)),
    )

    new_roles: List[PlayerRole] = []
    for role in roles:
        if role.player_key == injured.player_key:
            new_roles.append(
                replace(
                    role,
                    snap_share=round(role.snap_share * avail, 5),
                    target_share=round(role.target_share * avail, 5),
                    rush_share=round(role.rush_share * avail, 5),
                    route_share=round(role.route_share * avail, 5),
                    red_zone_share=round(role.red_zone_share * avail, 5),
                    source=f"{role.source}+injury_{avail:.2f}",
                )
            )
            continue
        new_roles.append(
            replace(
                role,
                snap_share=round(role.snap_share + snap_boost.get(role.player_key, 0.0), 5),
                target_share=round(role.target_share + tgt_boost.get(role.player_key, 0.0), 5),
                rush_share=round(role.rush_share + rush_boost.get(role.player_key, 0.0), 5),
                route_share=round(role.route_share + route_boost.get(role.player_key, 0.0), 5),
                red_zone_share=round(
                    role.red_zone_share + rz_boost.get(role.player_key, 0.0), 5
                ),
                source=(
                    f"{role.source}+injury_absorb"
                    if (
                        snap_boost.get(role.player_key)
                        or tgt_boost.get(role.player_key)
                        or rush_boost.get(role.player_key)
                    )
                    else role.source
                ),
            )
        )
    # Role promotions / committee reorder for inspectability (labels only).
    if avail <= 1e-9:
        new_roles, promo = promote_roles_after_injury(
            new_roles, injured=injured, structure=structure
        )
        if promo:
            notes.append(f"promotions={len(promo)}")
    return new_roles, "; ".join(notes)


def apply_strength_shock(
    state: TeamStrengthState,
    *,
    offense_delta: float,
    pass_rate_nudge: float = 0.0,
    defense_delta: float = 0.0,
) -> TeamStrengthState:
    """Return a copy of ``state`` with injury shock applied to *current* PR.

    Full-strength indices are preserved (intrinsic team without this week's
    availability scars). Downstream can read both; offense_index/defense_index
    remain the current (availability-adjusted) contract.
    """
    shocked = state.copy()
    # Lock full-strength to the pre-shock book the first time we scar.
    if "injury_shock" not in (state.source or ""):
        shocked.full_strength_offense_index = float(state.offense_index)
        shocked.full_strength_defense_index = float(state.defense_index)
    else:
        shocked.full_strength_offense_index = float(
            state.full_strength_offense_index or state.offense_index
        )
        shocked.full_strength_defense_index = float(
            state.full_strength_defense_index or state.defense_index
        )
    shocked.offense_index = _clamp(shocked.offense_index + offense_delta, 0.55, 1.45)
    if abs(defense_delta) > 1e-9:
        shocked.defense_index = _clamp(shocked.defense_index + defense_delta, 0.55, 1.45)
    shocked.injury_delta_offense = round(
        float(shocked.offense_index) - float(shocked.full_strength_offense_index), 6
    )
    shocked.injury_delta_defense = round(
        float(shocked.defense_index) - float(shocked.full_strength_defense_index), 6
    )
    if isinstance(shocked.drivers, dict):
        drivers = dict(shocked.drivers)
        drivers["injury_availability_delta"] = {
            "offense": shocked.injury_delta_offense,
            "defense": shocked.injury_delta_defense,
            "status": "applied",
        }
        shocked.drivers = drivers
    if abs(pass_rate_nudge) > 1e-9:
        shocked.pass_rate_bias = _clamp(shocked.pass_rate_bias + pass_rate_nudge, -0.12, 0.12)
    if "injury_shock" not in shocked.source:
        shocked.source = f"{shocked.source}+injury_shock"
    return shocked


def apply_injury_paths_for_week(
    rosters: Mapping[str, Sequence[PlayerRole]],
    strengths: Mapping[str, TeamStrengthState],
    paths: Sequence[InjuryPath],
    *,
    week: int,
    strengths_only: bool = False,
) -> Tuple[
    Dict[str, List[PlayerRole]],
    Dict[str, TeamStrengthState],
    List[AvailabilityAdjustment],
]:
    """Apply all active injury paths for ``week``.

    Returns adjusted roster book, temporary strength book (copy + shocks),
    and inspectable adjustment records. Callers should use these for the
    game's Layers 2–4, then evolve the *unshocked* path strength book.

    When ``strengths_only=True`` (survivor team W/L paths), skip roster
    deep-copy + usage reallocation and only apply Layer-1 offense / pass
    nudges. Rosters returned are shallow references to the input lists.
    """
    adj_strengths: Dict[str, TeamStrengthState] = {
        team: state.copy() for team, state in strengths.items()
    }
    adjustments: List[AvailabilityAdjustment] = []
    offense_deltas: Dict[str, float] = {t: 0.0 for t in adj_strengths}
    pass_nudges: Dict[str, float] = {t: 0.0 for t in adj_strengths}

    if not paths:
        if strengths_only:
            return {}, adj_strengths, adjustments
        adj_rosters = {team: list(roles) for team, roles in rosters.items()}
        return adj_rosters, adj_strengths, adjustments

    if strengths_only:
        # Strength shocks only — no roster copy / usage reallocation.
        for path in paths:
            avail = availability_for_week(path, week)
            if avail >= 1.0 - 1e-12:
                continue
            role = _find_role(rosters, path)
            if role is None:
                adjustments.append(
                    AvailabilityAdjustment(
                        player_key=path.player_key,
                        player_name=path.player_name,
                        team=path.team,
                        week=week,
                        status=path.status,
                        availability=avail,
                        offense_delta=0.0,
                        freed_target_share=0.0,
                        freed_rush_share=0.0,
                        realloc_notes="player_not_found_on_roster",
                    )
                )
                continue
            team = role.team
            missing = 1.0 - avail
            offense_delta = -player_offense_value(role) * missing
            offense_deltas[team] = offense_deltas.get(team, 0.0) + offense_delta
            if role.position == "RB" and role.depth_order <= 2:
                pass_nudges[team] = pass_nudges.get(team, 0.0) + 0.025 * missing
            elif role.position == "WR" and role.depth_order == 1:
                pass_nudges[team] = pass_nudges.get(team, 0.0) - 0.015 * missing
            elif role.position == "QB" and role.depth_order == 1:
                pass_nudges[team] = pass_nudges.get(team, 0.0) - 0.02 * missing
            adjustments.append(
                AvailabilityAdjustment(
                    player_key=role.player_key,
                    player_name=role.player_name,
                    team=team,
                    week=week,
                    status=path.status,
                    availability=round(avail, 4),
                    offense_delta=round(offense_delta, 5),
                    freed_target_share=round(max(0.0, role.target_share) * missing, 5),
                    freed_rush_share=round(max(0.0, role.rush_share) * missing, 5),
                    realloc_notes="strengths_only_skip_usage_realloc",
                )
            )
        for team, delta in offense_deltas.items():
            if abs(delta) < 1e-12 and abs(pass_nudges.get(team, 0.0)) < 1e-12:
                continue
            capped = _clamp(delta, -MAX_OFFENSE_SHOCK, MAX_OFFENSE_SHOCK)
            adj_strengths[team] = apply_strength_shock(
                adj_strengths[team],
                offense_delta=capped,
                pass_rate_nudge=pass_nudges.get(team, 0.0),
            )
        return {}, adj_strengths, adjustments

    # Full path: deep-copy roles + usage reallocation (Layers 1 + 3).
    adj_rosters = {team: list(roles) for team, roles in rosters.items()}

    for path in paths:
        avail = availability_for_week(path, week)
        if avail >= 1.0 - 1e-12:
            continue
        role = _find_role(adj_rosters, path)
        if role is None:
            adjustments.append(
                AvailabilityAdjustment(
                    player_key=path.player_key,
                    player_name=path.player_name,
                    team=path.team,
                    week=week,
                    status=path.status,
                    availability=avail,
                    offense_delta=0.0,
                    freed_target_share=0.0,
                    freed_rush_share=0.0,
                    realloc_notes="player_not_found_on_roster",
                )
            )
            continue

        team = role.team
        team_roles = adj_rosters.get(team, [])
        missing = 1.0 - avail
        value = player_offense_value(role)
        offense_delta = -value * missing
        offense_deltas[team] = offense_deltas.get(team, 0.0) + offense_delta

        # Pass-rate nudges: RB missing → slightly more pass; WR1 missing → slight pass down.
        if role.position == "RB" and role.depth_order <= 2:
            pass_nudges[team] = pass_nudges.get(team, 0.0) + 0.025 * missing
        elif role.position == "WR" and role.depth_order == 1:
            pass_nudges[team] = pass_nudges.get(team, 0.0) - 0.015 * missing
        elif role.position == "QB" and role.depth_order == 1:
            pass_nudges[team] = pass_nudges.get(team, 0.0) - 0.02 * missing

        new_roles, note = reallocate_role_shares(
            team_roles, injured=role, availability=avail
        )
        adj_rosters[team] = new_roles

        adjustments.append(
            AvailabilityAdjustment(
                player_key=role.player_key,
                player_name=role.player_name,
                team=team,
                week=week,
                status=path.status,
                availability=round(avail, 4),
                offense_delta=round(offense_delta, 5),
                freed_target_share=round(max(0.0, role.target_share) * missing, 5),
                freed_rush_share=round(max(0.0, role.rush_share) * missing, 5),
                realloc_notes=note,
            )
        )

    for team, delta in offense_deltas.items():
        if abs(delta) < 1e-12 and abs(pass_nudges.get(team, 0.0)) < 1e-12:
            continue
        capped = _clamp(delta, -MAX_OFFENSE_SHOCK, MAX_OFFENSE_SHOCK)
        base = adj_strengths[team]
        adj_strengths[team] = apply_strength_shock(
            base,
            offense_delta=capped,
            pass_rate_nudge=pass_nudges.get(team, 0.0),
        )

    return adj_rosters, adj_strengths, adjustments


def summarize_adjustments(rows: Sequence[AvailabilityAdjustment]) -> Dict[str, Any]:
    return {
        "active_count": len(rows),
        "by_team": {
            team: [
                {
                    "player_key": r.player_key,
                    "player_name": r.player_name,
                    "status": r.status,
                    "availability": r.availability,
                    "offense_delta": r.offense_delta,
                    "freed_target_share": r.freed_target_share,
                    "freed_rush_share": r.freed_rush_share,
                    "realloc_notes": r.realloc_notes,
                }
                for r in rows
                if r.team == team
            ]
            for team in sorted({r.team for r in rows})
        },
        "rules": {
            "strength": (
                "offense_index += −player_offense_value × (1 − availability); "
                f"capped at ±{MAX_OFFENSE_SHOCK}; defense unchanged"
            ),
            "reallocation": (
                "Role-aware absorption via usage_roles.INJURY_REALLOC_RULES "
                "(RB1→RB2 primary, WR1→WR2>slot>WR3, TE1→TE2+WR mix); "
                f"{REALLOC_OTHER_FRACTION:.0%} of freed volume stays in residual other bucket"
            ),
            "limited_default": DEFAULT_LIMITED_AVAILABILITY,
            "returning_ramp": (
                f"linear from availability|default {DEFAULT_RETURNING_START_AVAILABILITY} → 1.0"
            ),
        },
    }
