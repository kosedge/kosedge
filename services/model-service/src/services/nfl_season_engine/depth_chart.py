"""Depth-chart structure, committee splits, and role volatility (Layer 3).

Builds on ``usage_roles`` taxonomy. Does **not** change game-script logic
(``SCRIPT_USAGE_MATRIX`` stays authoritative for lead/trail/neutral).

Structures
----------
- RB ``feature``: clear RB1 + RB2 (dominant starter)
- RB ``committee``: 2–3 backs with unequal but non-dominant shares
- WR ``clear``: WR1 >> WR2 >> WR3 gaps
- WR ``murky``: compressed WR1–WR3 gaps (shared alpha)

Committee base splits (absolute fractions of team rush volume among
named committee RBs; residual other still applies in Layer 3):

| Backs | Split label | Absolute rush shares |
| ----- | ----------- | -------------------- |
| 2     | 55/45       | 0.42 / 0.34          |
| 3     | 45/35/20    | 0.36 / 0.28 / 0.16   |

Feature RB absolute rush shares (named RB pool):

| Backs | Split label | Absolute rush shares |
| ----- | ----------- | -------------------- |
| 2     | 68/32       | 0.55 / 0.26          |
| 3     | 60/25/15    | 0.50 / 0.22 / 0.12   |

Volatility (deterministic given seed)
-------------------------------------
Per season-path week: small share drift + rare role-rank shuffle from a
performance shock draw. Injury of a starter triggers promotion /
committee redistribution via ``promote_roles_after_injury`` (called from
injury realloc). Diagnostics expose ``depth_structure`` and
``role_transitions``.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from src.services.nfl_season_engine.types import PlayerRole
from src.services.nfl_season_engine.usage_roles import annotate_usage_roles

# ---------------------------------------------------------------------------
# Documented split tables (absolute team-volume fractions for named backs)
# ---------------------------------------------------------------------------
COMMITTEE_RUSH_SPLITS: Dict[int, Tuple[float, ...]] = {
    2: (0.42, 0.34),  # 55/45 of ~0.76 RB pool
    3: (0.36, 0.28, 0.16),  # 45/35/20 of ~0.80 RB pool
}
FEATURE_RUSH_SPLITS: Dict[int, Tuple[float, ...]] = {
    2: (0.55, 0.26),  # 68/32 of ~0.81
    3: (0.50, 0.22, 0.12),  # 60/25/15
}

# Snap / target companions for RB structures (aligned with BASE_USAGE_BY_ROLE).
COMMITTEE_SNAP_SPLITS: Dict[int, Tuple[float, ...]] = {
    2: (0.52, 0.42),
    3: (0.48, 0.38, 0.28),
}
COMMITTEE_TARGET_SPLITS: Dict[int, Tuple[float, ...]] = {
    2: (0.09, 0.06),
    3: (0.08, 0.06, 0.04),
}
FEATURE_SNAP_SPLITS: Dict[int, Tuple[float, ...]] = {
    2: (0.62, 0.32),
    3: (0.58, 0.30, 0.18),
}
FEATURE_TARGET_SPLITS: Dict[int, Tuple[float, ...]] = {
    2: (0.10, 0.05),
    3: (0.10, 0.05, 0.03),
}

# Clear vs murky WR absolute target tables (top-3).
CLEAR_WR_TARGET_SPLITS: Tuple[float, ...] = (0.23, 0.16, 0.09)
MURKY_WR_TARGET_SPLITS: Tuple[float, ...] = (0.18, 0.15, 0.12)
CLEAR_WR_SNAP_SPLITS: Tuple[float, ...] = (0.88, 0.76, 0.52)
MURKY_WR_SNAP_SPLITS: Tuple[float, ...] = (0.80, 0.74, 0.62)

# Classification thresholds.
_RB_COMMITTEE_MIN_SHARE = 0.26
_RB_COMMITTEE_MAX_GAP = 0.14
_WR_MURKY_TOP_GAP = 0.05  # WR1 − WR2
_WR_MURKY_SPAN = 0.10  # WR1 − WR3

# Volatility knobs (inspectable).
VOL_RUSH_DRIFT_SD = 0.018
VOL_TARGET_DRIFT_SD = 0.012
VOL_SNAP_DRIFT_SD = 0.015
VOL_SHUFFLE_PROB = 0.08  # chance of adjacent rank swap among murky/committee
VOL_DRIFT_CLAMP = 0.06


@dataclass(frozen=True)
class DepthStructure:
    """Inspectable per-team depth-chart structure."""

    team: str
    rb_structure: str  # feature | committee | thin
    wr_hierarchy: str  # clear | murky | thin
    rb_count: int = 0
    wr_count: int = 0
    committee_split: str = ""
    wr_split: str = ""
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "team": self.team,
            "rb_structure": self.rb_structure,
            "wr_hierarchy": self.wr_hierarchy,
            "rb_count": self.rb_count,
            "wr_count": self.wr_count,
            "committee_split": self.committee_split,
            "wr_split": self.wr_split,
            "notes": self.notes,
        }


@dataclass
class RoleTransition:
    """One inspectable role / share change inside a path week."""

    team: str
    week: int
    player_key: str
    player_name: str
    reason: str
    from_role: str
    to_role: str
    rush_delta: float = 0.0
    target_delta: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "team": self.team,
            "week": self.week,
            "player_key": self.player_key,
            "player_name": self.player_name,
            "reason": self.reason,
            "from_role": self.from_role,
            "to_role": self.to_role,
            "rush_delta": round(self.rush_delta, 5),
            "target_delta": round(self.target_delta, 5),
        }


@dataclass
class DepthChartState:
    """Mutable path-level depth book + transition log."""

    rosters: Dict[str, List[PlayerRole]]
    structures: Dict[str, DepthStructure] = field(default_factory=dict)
    transitions: List[RoleTransition] = field(default_factory=list)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _sorted_pos(roles: Sequence[PlayerRole], pos: str) -> List[PlayerRole]:
    same = [r for r in roles if (r.position or "").upper() == pos]
    if pos == "RB":
        return sorted(same, key=lambda r: (r.depth_order, -r.rush_share))
    if pos == "WR":
        return sorted(same, key=lambda r: (r.depth_order, -r.target_share))
    return sorted(same, key=lambda r: (r.depth_order, -r.target_share))


def classify_rb_structure(rbs: Sequence[PlayerRole]) -> str:
    """Return ``feature``, ``committee``, or ``thin``."""
    ordered = list(rbs)
    if len(ordered) < 2:
        return "thin"
    top, second = ordered[0], ordered[1]
    if (
        top.rush_share >= _RB_COMMITTEE_MIN_SHARE
        and second.rush_share >= _RB_COMMITTEE_MIN_SHARE
        and abs(top.rush_share - second.rush_share) <= _RB_COMMITTEE_MAX_GAP
    ):
        return "committee"
    # Third back can join a committee if also meaningful and close to #2.
    if len(ordered) >= 3:
        third = ordered[2]
        if (
            second.rush_share >= _RB_COMMITTEE_MIN_SHARE
            and third.rush_share >= 0.18
            and abs(top.rush_share - second.rush_share) <= _RB_COMMITTEE_MAX_GAP + 0.04
        ):
            return "committee"
    return "feature"


def classify_wr_hierarchy(wrs: Sequence[PlayerRole]) -> str:
    """Return ``clear``, ``murky``, or ``thin``."""
    ordered = list(wrs)
    if len(ordered) < 2:
        return "thin"
    top = ordered[0].target_share
    second = ordered[1].target_share
    third = ordered[2].target_share if len(ordered) >= 3 else second
    if (top - second) <= _WR_MURKY_TOP_GAP or (top - third) <= _WR_MURKY_SPAN:
        return "murky"
    return "clear"


def _split_label(parts: Sequence[float]) -> str:
    total = sum(parts) or 1.0
    pcts = [int(round(100.0 * p / total)) for p in parts]
    # Fix rounding so parts sum to 100.
    drift = 100 - sum(pcts)
    if pcts:
        pcts[0] += drift
    return "/".join(str(p) for p in pcts)


def classify_team_depth(team: str, roles: Sequence[PlayerRole]) -> DepthStructure:
    # Classification uses shares/depth_order; labels optional.
    rbs = _sorted_pos(roles, "RB")
    wrs = _sorted_pos(roles, "WR")
    rb_struct = classify_rb_structure(rbs)
    wr_hier = classify_wr_hierarchy(wrs)

    committee_split = ""
    if rb_struct == "committee":
        n = min(3, max(2, len(rbs)))
        parts = COMMITTEE_RUSH_SPLITS.get(n) or COMMITTEE_RUSH_SPLITS[2]
        if len(rbs) == 2:
            parts = COMMITTEE_RUSH_SPLITS[2]
        elif len(rbs) >= 3:
            parts = COMMITTEE_RUSH_SPLITS[3]
        committee_split = _split_label(parts)
    elif rb_struct == "feature" and len(rbs) >= 2:
        n = 3 if len(rbs) >= 3 else 2
        committee_split = _split_label(FEATURE_RUSH_SPLITS[n])

    wr_split = ""
    if wr_hier == "murky" and len(wrs) >= 3:
        wr_split = _split_label(MURKY_WR_TARGET_SPLITS)
    elif wr_hier == "clear" and len(wrs) >= 3:
        wr_split = _split_label(CLEAR_WR_TARGET_SPLITS)

    notes_parts = []
    if rb_struct == "committee":
        notes_parts.append(f"RB committee {committee_split}")
    elif rb_struct == "feature":
        notes_parts.append("feature RB1/RB2")
    if wr_hier == "murky":
        notes_parts.append("murky WR hierarchy")
    elif wr_hier == "clear":
        notes_parts.append("clear WR hierarchy")

    return DepthStructure(
        team=team,
        rb_structure=rb_struct,
        wr_hierarchy=wr_hier,
        rb_count=len(rbs),
        wr_count=len(wrs),
        committee_split=committee_split,
        wr_split=wr_split,
        notes="; ".join(notes_parts),
    )


def classify_roster_book(
    rosters: Mapping[str, Sequence[PlayerRole]],
) -> Dict[str, DepthStructure]:
    return {team: classify_team_depth(team, roles) for team, roles in rosters.items()}


def _apply_splits(
    roles: List[PlayerRole],
    ordered_keys: Sequence[str],
    *,
    rush: Sequence[float],
    snap: Sequence[float],
    target: Sequence[float],
) -> List[PlayerRole]:
    by_key = {r.player_key: r for r in roles}
    for i, key in enumerate(ordered_keys):
        role = by_key.get(key)
        if role is None or i >= len(rush):
            continue
        by_key[key] = replace(
            role,
            rush_share=round(float(rush[i]), 5),
            snap_share=round(float(snap[i]), 5),
            target_share=round(float(target[i]), 5),
            route_share=round(max(role.route_share, float(target[i]) * 2.4), 5)
            if role.position == "RB"
            else role.route_share,
            source=f"{role.source}+depth_split",
        )
    return [by_key[r.player_key] for r in roles]


def apply_depth_chart_base_shares(
    roles: Sequence[PlayerRole],
    *,
    structure: Optional[DepthStructure] = None,
    force_table_splits: bool = False,
) -> Tuple[List[PlayerRole], DepthStructure]:
    """Annotate roles and (optionally) overwrite RB/WR shares from structure tables.

    When ``force_table_splits`` is False (default), only rewrite shares when
    the loaded book already looks like a committee / murky set — preserves
    elite feature-back priors (CMC, Barkley) from demo/DB.
    When True, always apply the documented table for the classified structure
    (used by tests / explicit committee construction).
    """
    annotated = annotate_usage_roles(roles)
    team = annotated[0].team if annotated else ""
    struct = structure or classify_team_depth(team, annotated)
    out = list(annotated)
    rbs = _sorted_pos(out, "RB")
    wrs = _sorted_pos(out, "WR")

    apply_rb = force_table_splits or struct.rb_structure == "committee"
    if apply_rb and len(rbs) >= 2:
        n = 3 if len(rbs) >= 3 and struct.rb_structure == "committee" else min(3, len(rbs))
        if struct.rb_structure == "committee":
            n = 3 if len(rbs) >= 3 else 2
            rush = COMMITTEE_RUSH_SPLITS[n]
            snap = COMMITTEE_SNAP_SPLITS[n]
            tgt = COMMITTEE_TARGET_SPLITS[n]
            # Ensure committee labels on the participating backs.
            labeled: Dict[str, PlayerRole] = {}
            for i, role in enumerate(rbs[:n]):
                labeled[role.player_key] = replace(role, usage_role="RB_COMMITTEE")
            out = [labeled.get(r.player_key, r) for r in out]
            rbs = _sorted_pos(out, "RB")
        else:
            n = 3 if len(rbs) >= 3 else 2
            rush = FEATURE_RUSH_SPLITS[n]
            snap = FEATURE_SNAP_SPLITS[n]
            tgt = FEATURE_TARGET_SPLITS[n]
            # Feature labels: RB1 / RB2 / OTHER.
            labeled = {}
            for i, role in enumerate(rbs[:n]):
                label = "RB1" if i == 0 else ("RB2" if i == 1 else "OTHER")
                labeled[role.player_key] = replace(role, usage_role=label)
            out = [labeled.get(r.player_key, r) for r in out]
            rbs = _sorted_pos(out, "RB")
        out = _apply_splits(
            out,
            [r.player_key for r in rbs[:n]],
            rush=rush,
            snap=snap,
            target=tgt,
        )

    apply_wr = force_table_splits or struct.wr_hierarchy == "murky"
    if apply_wr and len(wrs) >= 3:
        if struct.wr_hierarchy == "murky":
            tgt = MURKY_WR_TARGET_SPLITS
            snap = MURKY_WR_SNAP_SPLITS
        else:
            tgt = CLEAR_WR_TARGET_SPLITS
            snap = CLEAR_WR_SNAP_SPLITS
        # Keep WR labels; only compress/expand targets + snaps for top-3.
        by_key = {r.player_key: r for r in out}
        for i, role in enumerate(wrs[:3]):
            route = max(role.route_share, float(tgt[i]) * 3.8)
            by_key[role.player_key] = replace(
                role,
                target_share=round(float(tgt[i]), 5),
                snap_share=round(float(snap[i]), 5),
                route_share=round(route, 5),
                source=f"{role.source}+wr_hierarchy_{struct.wr_hierarchy}",
            )
        out = [by_key[r.player_key] for r in out]

    # Re-annotate in case labels need refresh after share edits.
    out = annotate_usage_roles(out)
    # Preserve committee labels (annotate may flip to RB1/RB2 after equalish shares).
    if struct.rb_structure == "committee":
        rbs = _sorted_pos(out, "RB")
        n = 3 if len(rbs) >= 3 else 2
        by_key = {r.player_key: r for r in out}
        for role in rbs[:n]:
            by_key[role.player_key] = replace(role, usage_role="RB_COMMITTEE")
        out = [by_key[r.player_key] for r in out]

    return out, struct


def apply_depth_chart_roster_book(
    rosters: Mapping[str, Sequence[PlayerRole]],
    *,
    force_table_splits: bool = False,
) -> Tuple[Dict[str, List[PlayerRole]], Dict[str, DepthStructure]]:
    out: Dict[str, List[PlayerRole]] = {}
    structures: Dict[str, DepthStructure] = {}
    for team, roles in rosters.items():
        adjusted, struct = apply_depth_chart_base_shares(
            roles, force_table_splits=force_table_splits
        )
        out[team] = adjusted
        structures[team] = struct
    return out, structures


def herfindahl_rush(roles: Sequence[PlayerRole]) -> float:
    """Herfindahl-Hirschman index on RB rush shares (concentration)."""
    rbs = [r for r in roles if (r.position or "").upper() == "RB"]
    shares = [max(0.0, float(r.rush_share)) for r in rbs]
    total = sum(shares)
    if total <= 1e-12:
        return 0.0
    fracs = [s / total for s in shares]
    return sum(f * f for f in fracs)


def top1_rush_share(roles: Sequence[PlayerRole]) -> float:
    rbs = [r for r in roles if (r.position or "").upper() == "RB"]
    if not rbs:
        return 0.0
    return max(float(r.rush_share) for r in rbs)


def wr_hierarchy_gap(roles: Sequence[PlayerRole]) -> float:
    """WR1 − WR3 target gap (0 if fewer than 3 WRs)."""
    wrs = _sorted_pos(roles, "WR")
    if len(wrs) < 3:
        return 0.0
    return float(wrs[0].target_share) - float(wrs[2].target_share)


def apply_weekly_role_volatility(
    rosters: Mapping[str, Sequence[PlayerRole]],
    *,
    week: int,
    rng: random.Random,
    structures: Optional[Mapping[str, DepthStructure]] = None,
) -> Tuple[Dict[str, List[PlayerRole]], List[RoleTransition]]:
    """Small deterministic share drift + rare adjacent role shuffle for one week."""
    structures = structures or classify_roster_book(rosters)
    out: Dict[str, List[PlayerRole]] = {}
    transitions: List[RoleTransition] = []

    for team, roles in rosters.items():
        struct = structures.get(team) or classify_team_depth(team, roles)
        # Locked feature/clear books stay put — volatility targets murky /
        # committee situations where roles are genuinely contested.
        volatile_rb = struct.rb_structure == "committee"
        volatile_wr = struct.wr_hierarchy == "murky"
        if not volatile_rb and not volatile_wr:
            out[team] = list(roles)
            continue

        annotated = (
            list(roles)
            if all(r.usage_role for r in roles)
            else annotate_usage_roles(roles)
        )
        by_key = {r.player_key: r for r in annotated}

        rush_sd = VOL_RUSH_DRIFT_SD * 1.35
        tgt_sd = VOL_TARGET_DRIFT_SD * 1.35

        for role in list(by_key.values()):
            pos = (role.position or "").upper()
            if pos == "RB" and not volatile_rb:
                continue
            if pos in ("WR", "TE") and not volatile_wr:
                continue
            if pos not in ("RB", "WR", "TE"):
                continue
            rush_d = rng.gauss(0.0, rush_sd) if pos == "RB" else 0.0
            tgt_d = rng.gauss(0.0, tgt_sd) if pos in ("WR", "TE", "RB") else 0.0
            snap_d = rng.gauss(0.0, VOL_SNAP_DRIFT_SD)
            rush_d = _clamp(rush_d, -VOL_DRIFT_CLAMP, VOL_DRIFT_CLAMP)
            tgt_d = _clamp(tgt_d, -VOL_DRIFT_CLAMP, VOL_DRIFT_CLAMP)
            snap_d = _clamp(snap_d, -VOL_DRIFT_CLAMP, VOL_DRIFT_CLAMP)
            if abs(rush_d) < 1e-6 and abs(tgt_d) < 1e-6 and abs(snap_d) < 1e-6:
                continue
            new_role = replace(
                role,
                rush_share=round(_clamp(role.rush_share + rush_d, 0.0, 0.85), 5),
                target_share=round(_clamp(role.target_share + tgt_d, 0.0, 0.40), 5),
                snap_share=round(_clamp(role.snap_share + snap_d, 0.05, 1.0), 5),
                source=f"{role.source}+vol_w{week}",
            )
            by_key[role.player_key] = new_role
            # Log only material drifts (keeps diagnostics compact).
            if abs(rush_d) >= 0.02 or abs(tgt_d) >= 0.015:
                transitions.append(
                    RoleTransition(
                        team=team,
                        week=week,
                        player_key=role.player_key,
                        player_name=role.player_name,
                        reason="performance_drift",
                        from_role=role.usage_role or "",
                        to_role=new_role.usage_role or role.usage_role or "",
                        rush_delta=rush_d,
                        target_delta=tgt_d,
                    )
                )

        team_roles = [by_key[r.player_key] for r in annotated]

        # Adjacent shuffle among committee RBs or murky WRs.
        did_shuffle = False
        shuffle_pool_pos = None
        if struct.rb_structure == "committee" and rng.random() < VOL_SHUFFLE_PROB:
            shuffle_pool_pos = "RB"
        elif struct.wr_hierarchy == "murky" and rng.random() < VOL_SHUFFLE_PROB:
            shuffle_pool_pos = "WR"

        if shuffle_pool_pos:
            pool = _sorted_pos(team_roles, shuffle_pool_pos)
            if len(pool) >= 2:
                i = rng.randrange(0, len(pool) - 1)
                a, b = pool[i], pool[i + 1]
                if shuffle_pool_pos == "RB":
                    a2 = replace(
                        a,
                        depth_order=b.depth_order,
                        rush_share=b.rush_share,
                        snap_share=b.snap_share,
                        usage_role=b.usage_role or a.usage_role,
                        source=f"{a.source}+role_shuffle",
                    )
                    b2 = replace(
                        b,
                        depth_order=a.depth_order,
                        rush_share=a.rush_share,
                        snap_share=a.snap_share,
                        usage_role=a.usage_role or b.usage_role,
                        source=f"{b.source}+role_shuffle",
                    )
                else:
                    a2 = replace(
                        a,
                        depth_order=b.depth_order,
                        target_share=b.target_share,
                        snap_share=b.snap_share,
                        route_share=b.route_share,
                        usage_role=b.usage_role or a.usage_role,
                        source=f"{a.source}+role_shuffle",
                    )
                    b2 = replace(
                        b,
                        depth_order=a.depth_order,
                        target_share=a.target_share,
                        snap_share=a.snap_share,
                        route_share=a.route_share,
                        usage_role=a.usage_role or b.usage_role,
                        source=f"{b.source}+role_shuffle",
                    )
                by_key[a.player_key] = a2
                by_key[b.player_key] = b2
                did_shuffle = True
                transitions.append(
                    RoleTransition(
                        team=team,
                        week=week,
                        player_key=a.player_key,
                        player_name=a.player_name,
                        reason="role_shuffle",
                        from_role=a.usage_role or "",
                        to_role=a2.usage_role or "",
                        rush_delta=a2.rush_share - a.rush_share,
                        target_delta=a2.target_share - a.target_share,
                    )
                )
                transitions.append(
                    RoleTransition(
                        team=team,
                        week=week,
                        player_key=b.player_key,
                        player_name=b.player_name,
                        reason="role_shuffle",
                        from_role=b.usage_role or "",
                        to_role=b2.usage_role or "",
                        rush_delta=b2.rush_share - b.rush_share,
                        target_delta=b2.target_share - b.target_share,
                    )
                )
                team_roles = [by_key[r.player_key] for r in annotated]

        # Re-annotate only after a shuffle (drift keeps labels).
        if did_shuffle:
            team_roles = annotate_usage_roles(team_roles)
            if struct.rb_structure == "committee":
                rbs = _sorted_pos(team_roles, "RB")
                n = 3 if len(rbs) >= 3 else 2
                by_key2 = {r.player_key: r for r in team_roles}
                for role in rbs[:n]:
                    by_key2[role.player_key] = replace(role, usage_role="RB_COMMITTEE")
                team_roles = [by_key2[r.player_key] for r in team_roles]

        out[team] = team_roles

    return out, transitions


def promote_roles_after_injury(
    roles: Sequence[PlayerRole],
    *,
    injured: PlayerRole,
    structure: Optional[DepthStructure] = None,
) -> Tuple[List[PlayerRole], List[RoleTransition]]:
    """After injury zeroing, promote backups / re-label remaining committee.

    Share redistribution itself lives in ``injury_paths.reallocate_role_shares``;
    this only updates ``usage_role`` / depth_order for inspectability.
    """
    roles = annotate_usage_roles(roles)
    team = injured.team
    struct = structure or classify_team_depth(team, roles)
    transitions: List[RoleTransition] = []
    injured_key = injured.player_key
    pos = (injured.position or "").upper()
    injured_label = injured.usage_role or ""

    by_key = {r.player_key: r for r in roles}
    healthy = [r for r in roles if r.player_key != injured_key]

    if pos == "RB":
        rbs = _sorted_pos(healthy, "RB")
        if not rbs:
            return list(roles), transitions
        if struct.rb_structure == "feature" and injured_label == "RB1":
            # RB2 becomes temporary RB1.
            rb2 = next((r for r in rbs if r.usage_role == "RB2"), rbs[0])
            old = rb2.usage_role
            by_key[rb2.player_key] = replace(
                rb2, usage_role="RB1", depth_order=1, source=f"{rb2.source}+promo_rb1"
            )
            transitions.append(
                RoleTransition(
                    team=team,
                    week=0,
                    player_key=rb2.player_key,
                    player_name=rb2.player_name,
                    reason="injury_promotion_feature",
                    from_role=old or "RB2",
                    to_role="RB1",
                )
            )
        elif struct.rb_structure == "committee" or injured_label == "RB_COMMITTEE":
            # Remaining committee keep RB_COMMITTEE; depth_order compresses.
            for i, role in enumerate(rbs[:3]):
                old = role.usage_role
                by_key[role.player_key] = replace(
                    role,
                    usage_role="RB_COMMITTEE",
                    depth_order=i + 1,
                    source=f"{role.source}+committee_reorder",
                )
                if old != "RB_COMMITTEE" or role.depth_order != i + 1:
                    transitions.append(
                        RoleTransition(
                            team=team,
                            week=0,
                            player_key=role.player_key,
                            player_name=role.player_name,
                            reason="injury_committee_reorder",
                            from_role=old or "",
                            to_role="RB_COMMITTEE",
                        )
                    )
    elif pos == "WR" and injured_label in ("WR1", "WR2", "WR_SLOT"):
        wrs = _sorted_pos(healthy, "WR")
        labels = ["WR1", "WR2", "WR3", "WR_SLOT"]
        for i, role in enumerate(wrs[:4]):
            new_label = labels[i] if i < len(labels) else "WR_SLOT"
            old = role.usage_role
            if old != new_label:
                by_key[role.player_key] = replace(
                    role,
                    usage_role=new_label,
                    depth_order=i + 1,
                    source=f"{role.source}+promo_{new_label}",
                )
                transitions.append(
                    RoleTransition(
                        team=team,
                        week=0,
                        player_key=role.player_key,
                        player_name=role.player_name,
                        reason="injury_promotion_wr",
                        from_role=old or "",
                        to_role=new_label,
                    )
                )

    return [by_key[r.player_key] for r in roles], transitions


def committee_remaining_rush_weights(n_remaining: int) -> Dict[int, float]:
    """Uneven weights for redistributing rush among remaining committee members.

    Indexed by depth_order (1-based). Not equal splits.
    """
    if n_remaining <= 1:
        return {1: 1.0}
    if n_remaining == 2:
        return {1: 0.58, 2: 0.42}  # ~58/42
    return {1: 0.45, 2: 0.35, 3: 0.20}


def depth_chart_documentation() -> Dict[str, Any]:
    return {
        "committee_rush_splits": {
            str(k): {"absolute": list(v), "label": _split_label(v)}
            for k, v in COMMITTEE_RUSH_SPLITS.items()
        },
        "feature_rush_splits": {
            str(k): {"absolute": list(v), "label": _split_label(v)}
            for k, v in FEATURE_RUSH_SPLITS.items()
        },
        "clear_wr_targets": list(CLEAR_WR_TARGET_SPLITS),
        "murky_wr_targets": list(MURKY_WR_TARGET_SPLITS),
        "volatility": {
            "rush_drift_sd": VOL_RUSH_DRIFT_SD,
            "target_drift_sd": VOL_TARGET_DRIFT_SD,
            "snap_drift_sd": VOL_SNAP_DRIFT_SD,
            "shuffle_prob": VOL_SHUFFLE_PROB,
            "drift_clamp": VOL_DRIFT_CLAMP,
            "seed": "deterministic given path rng",
        },
        "classification": {
            "rb_committee": (
                f"top-2 rush_share >= {_RB_COMMITTEE_MIN_SHARE} and "
                f"|gap| <= {_RB_COMMITTEE_MAX_GAP}"
            ),
            "wr_murky": (
                f"WR1−WR2 <= {_WR_MURKY_TOP_GAP} or WR1−WR3 <= {_WR_MURKY_SPAN}"
            ),
        },
    }


def depth_structure_diagnostics(
    rosters: Mapping[str, Sequence[PlayerRole]],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for team, roles in sorted(rosters.items()):
        annotated = annotate_usage_roles(roles)
        struct = classify_team_depth(team, annotated)
        row = struct.to_dict()
        row["herfindahl_rush"] = round(herfindahl_rush(annotated), 4)
        row["top1_rush_share"] = round(top1_rush_share(annotated), 4)
        row["wr1_wr3_target_gap"] = round(wr_hierarchy_gap(annotated), 4)
        rows.append(row)
    return rows
