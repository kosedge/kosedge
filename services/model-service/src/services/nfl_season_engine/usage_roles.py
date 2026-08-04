"""Explicit usage-role taxonomy for Layer 3 (player usage).

Inspectable labels (QB1/QB2, RB1/RB2/RB_COMMITTEE, WR1/WR2/WR3/WR_SLOT,
TE1/TE2) drive:

1. Base absolute usage tables (targets / carries / routes / snaps)
2. Game-script modifier matrix (lead / trail / neutral), intensity-scaled
3. Light personnel / play-mix tilts (11 vs 12/21)
4. Role-aware injury reallocation sinks (used by ``injury_paths``)

Depth-chart structure (feature vs committee RB, clear vs murky WR) and
weekly role volatility live in ``depth_chart.py`` and feed absolute
shares before this module's script/personnel modifiers apply.

v1.6 sharpens SCRIPT_USAGE_MATRIX and scales deltas by script intensity ×
time bucket (from Layer 2). No parallel opaque usage system — same matrix,
stronger late-game reactions.

All tables are absolute fractions of team volume where applicable; the
calibration residual "other" bucket still absorbs unnamed volume.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from src.services.nfl_season_engine.types import (
    PlayerRole,
    ScriptDetail,
    ScriptState,
    TimeBucket,
)

# Canonical role labels — keep short and stable for diagnostics / dumps.
USAGE_ROLE_LABELS = (
    "QB1",
    "QB2",
    "RB1",
    "RB2",
    "RB_COMMITTEE",
    "RB_GL",  # optional goal-line specialist (v1.7 scoring-usage)
    "WR1",
    "WR2",
    "WR3",
    "WR_SLOT",
    "TE1",
    "TE2",
    "OTHER",
)

# Absolute-ish base usage by role. Named skill cores should sum with residual
# other to ~1.0 across a typical 1QB/2RB/3WR/1TE modeled set.
BASE_USAGE_BY_ROLE: Dict[str, Dict[str, float]] = {
    "QB1": {"snap_share": 0.97, "rush_share": 0.075, "target_share": 0.0, "route_share": 0.0},
    "QB2": {"snap_share": 0.08, "rush_share": 0.01, "target_share": 0.0, "route_share": 0.0},
    "RB1": {"snap_share": 0.62, "rush_share": 0.55, "target_share": 0.10, "route_share": 0.30},
    "RB2": {"snap_share": 0.32, "rush_share": 0.26, "target_share": 0.05, "route_share": 0.18},
    "RB_COMMITTEE": {"snap_share": 0.45, "rush_share": 0.36, "target_share": 0.07, "route_share": 0.24},
    # Goal-line specialist: low general rush, elevated scoring usage (see red_zone.py).
    "RB_GL": {"snap_share": 0.18, "rush_share": 0.12, "target_share": 0.02, "route_share": 0.08},
    "WR1": {"snap_share": 0.88, "rush_share": 0.01, "target_share": 0.23, "route_share": 0.92},
    "WR2": {"snap_share": 0.76, "rush_share": 0.0, "target_share": 0.16, "route_share": 0.80},
    "WR3": {"snap_share": 0.52, "rush_share": 0.0, "target_share": 0.09, "route_share": 0.55},
    "WR_SLOT": {"snap_share": 0.68, "rush_share": 0.0, "target_share": 0.13, "route_share": 0.74},
    # cal-v2: TE1 target slightly lower (was matching WR1 yards on real depth).
    "TE1": {"snap_share": 0.70, "rush_share": 0.0, "target_share": 0.125, "route_share": 0.66},
    "TE2": {"snap_share": 0.40, "rush_share": 0.0, "target_share": 0.07, "route_share": 0.38},
    "OTHER": {"snap_share": 0.15, "rush_share": 0.05, "target_share": 0.04, "route_share": 0.15},
}

# Game-script modifiers applied to absolute shares before Dirichlet draw.
# Mults are relative to neutral; deltas are additive on snap after mults.
# Documented in ops markdown — keep explicit, not opaque stacks of magic.
#
# v1.6: sharpened vs v1.3/v1.5 so trailing late feeds WR1/TE and fades RB
# carries more clearly; leading late boosts RB and fades WR3. Intensity ×
# time-bucket scaling in ``effective_usage_shares`` amplifies these further
# for large_lead / large_deficit late without a parallel system.
#
# | Script | RB1 rush | WR1 tgt | TE1 tgt | WR3 tgt | Intent |
# | trail  | ×0.80    | ×1.20   | ×1.16   | ×0.90   | chase  |
# | lead   | ×1.24    | ×0.94   | ×0.96   | ×0.78   | protect|
# | neutral| ×1.0     | ×1.0    | ×1.0    | ×1.0    | baseline|
SCRIPT_USAGE_MATRIX: Dict[ScriptState, Dict[str, Dict[str, float]]] = {
    "neutral": {},
    "trail": {
        # Pass-heavy chase: feed WR1/TE1, RB carry fade, WR3 mild fade.
        "WR1": {"target_mult": 1.20, "route_mult": 1.12, "snap_delta": 0.04},
        "WR2": {"target_mult": 1.09, "route_mult": 1.06, "snap_delta": 0.025},
        "WR_SLOT": {"target_mult": 1.12, "route_mult": 1.09, "snap_delta": 0.03},
        "WR3": {"target_mult": 0.90, "route_mult": 0.94, "snap_delta": -0.01},
        "TE1": {"target_mult": 1.16, "route_mult": 1.10, "snap_delta": 0.04},
        "TE2": {"target_mult": 1.06, "route_mult": 1.03, "snap_delta": 0.015},
        "RB1": {"rush_mult": 0.80, "target_mult": 1.10, "snap_delta": -0.05},
        "RB2": {"rush_mult": 0.84, "target_mult": 1.07, "snap_delta": -0.03},
        "RB_COMMITTEE": {"rush_mult": 0.84, "target_mult": 1.08, "snap_delta": -0.03},
        "QB1": {"rush_mult": 1.08},
    },
    "lead": {
        # Protect lead: RB volume up; WR3 / deep-threat volume down.
        "RB1": {"rush_mult": 1.24, "target_mult": 0.88, "snap_delta": 0.07},
        "RB2": {"rush_mult": 1.14, "target_mult": 0.90, "snap_delta": 0.04},
        "RB_COMMITTEE": {"rush_mult": 1.16, "target_mult": 0.90, "snap_delta": 0.05},
        "WR1": {"target_mult": 0.94, "route_mult": 0.95, "snap_delta": -0.015},
        "WR2": {"target_mult": 0.90, "route_mult": 0.92, "snap_delta": -0.025},
        "WR3": {"target_mult": 0.78, "route_mult": 0.82, "snap_delta": -0.06},
        "WR_SLOT": {"target_mult": 0.92, "route_mult": 0.94, "snap_delta": -0.02},
        "TE1": {"target_mult": 0.96, "route_mult": 0.97, "snap_delta": 0.025},
        "TE2": {"target_mult": 1.04, "route_mult": 1.0, "snap_delta": 0.03},
        "QB1": {"rush_mult": 0.88},
    },
}

# Extra mult boosts when fine detail is large_* (applied after intensity scale).
# Kept tiny/transparent — detail already drives pass_rate in Layer 2.
SCRIPT_DETAIL_EXTRA: Dict[ScriptDetail, Dict[str, Dict[str, float]]] = {
    "large_deficit": {
        "WR1": {"target_mult": 1.04},
        "TE1": {"target_mult": 1.03},
        "RB1": {"rush_mult": 0.95},
    },
    "large_lead": {
        "RB1": {"rush_mult": 1.05},
        "WR3": {"target_mult": 0.94},
    },
    "small_deficit": {},
    "small_lead": {},
    "neutral": {},
}

# Personnel / play-mix tilts keyed by inferred package.
# pass_heavy ≈ 11 personnel (3 WR); balanced ≈ mix; rush_heavy ≈ 12/21 (TE/FB).
PERSONNEL_MIX_TABLE: Dict[str, Dict[str, Dict[str, float]]] = {
    "pass_heavy": {
        "WR1": {"route_mult": 1.04, "target_mult": 1.02, "snap_delta": 0.02},
        "WR2": {"route_mult": 1.05, "target_mult": 1.03, "snap_delta": 0.02},
        "WR3": {"route_mult": 1.08, "target_mult": 1.05, "snap_delta": 0.04},
        "WR_SLOT": {"route_mult": 1.06, "target_mult": 1.04, "snap_delta": 0.03},
        "TE1": {"route_mult": 0.96, "target_mult": 0.97, "snap_delta": -0.03},
        "TE2": {"route_mult": 0.92, "snap_delta": -0.04},
        "RB1": {"rush_mult": 0.96},
    },
    "balanced": {},
    "rush_heavy": {
        "TE1": {"route_mult": 1.04, "target_mult": 1.03, "snap_delta": 0.04},
        "TE2": {"route_mult": 1.06, "snap_delta": 0.05},
        "WR3": {"route_mult": 0.90, "target_mult": 0.90, "snap_delta": -0.05},
        "WR_SLOT": {"route_mult": 0.96, "snap_delta": -0.02},
        "RB1": {"rush_mult": 1.04, "snap_delta": 0.02},
        "RB2": {"rush_mult": 1.03, "snap_delta": 0.02},
        "RB_COMMITTEE": {"rush_mult": 1.03, "snap_delta": 0.02},
    },
}

# Injury reallocation sink weights by injured role → absorber role.
# Values are relative weights inside each bucket (same-pos / cross-pos).
# Fractions below are of the *assignable* freed volume (after other residual).
INJURY_REALLOC_RULES: Dict[str, Dict[str, Any]] = {
    "RB1": {
        "rush_sinks": {"RB2": 0.58, "RB_COMMITTEE": 0.28, "RB1": 0.0, "OTHER_RB": 0.14},
        "target_split": {"same_pos": 0.65, "WR": 0.22, "TE": 0.13},
        "same_pos_tgt_sinks": {"RB2": 0.55, "RB_COMMITTEE": 0.30, "OTHER_RB": 0.15},
        "note": "RB1_out→RB2 primary rush sink; committee/RB3 residual; WR/TE catch spill",
    },
    "RB2": {
        "rush_sinks": {"RB1": 0.45, "RB_COMMITTEE": 0.35, "OTHER_RB": 0.20},
        "target_split": {"same_pos": 0.70, "WR": 0.18, "TE": 0.12},
        "same_pos_tgt_sinks": {"RB1": 0.50, "RB_COMMITTEE": 0.30, "OTHER_RB": 0.20},
        "note": "RB2_out→RB1 + committee absorb; modest WR/TE target spill",
    },
    "RB_COMMITTEE": {
        # Remaining committee members absorb with uneven weights (depth_chart
        # committee_remaining_rush_weights); sink map below is a fallback when
        # structure helpers are unavailable.
        "rush_sinks": {"RB_COMMITTEE": 0.70, "RB1": 0.10, "RB2": 0.10, "OTHER_RB": 0.10},
        "target_split": {"same_pos": 0.68, "WR": 0.20, "TE": 0.12},
        "same_pos_tgt_sinks": {"RB_COMMITTEE": 0.70, "RB1": 0.10, "RB2": 0.10, "OTHER_RB": 0.10},
        "note": "Committee out→remaining committee uneven (≈58/42 or 45/35/20)",
        "committee_aware": True,
    },
    "WR1": {
        "target_split": {"WR": 0.62, "TE": 0.22, "RB": 0.16},
        "wr_sinks": {"WR2": 0.42, "WR_SLOT": 0.28, "WR3": 0.18, "OTHER_WR": 0.12},
        "te_sinks": {"TE1": 0.70, "TE2": 0.30},
        "rb_sinks": {"RB1": 0.55, "RB2": 0.25, "RB_COMMITTEE": 0.20},
        "note": "WR1_out→WR2 largest; slot > WR3; TE1 + RB1 catch spill",
    },
    "WR2": {
        "target_split": {"WR": 0.68, "TE": 0.18, "RB": 0.14},
        "wr_sinks": {"WR1": 0.38, "WR_SLOT": 0.30, "WR3": 0.22, "OTHER_WR": 0.10},
        "te_sinks": {"TE1": 0.70, "TE2": 0.30},
        "rb_sinks": {"RB1": 0.55, "RB2": 0.25, "RB_COMMITTEE": 0.20},
        "note": "WR2_out→WR1/slot primary; WR3 secondary",
    },
    "WR3": {
        "target_split": {"WR": 0.72, "TE": 0.16, "RB": 0.12},
        "wr_sinks": {"WR_SLOT": 0.40, "WR2": 0.30, "WR1": 0.20, "OTHER_WR": 0.10},
        "te_sinks": {"TE1": 0.65, "TE2": 0.35},
        "rb_sinks": {"RB1": 0.50, "RB2": 0.30, "RB_COMMITTEE": 0.20},
        "note": "WR3_out→slot/WR2 absorb most; modest alpha WR1 bump",
    },
    "WR_SLOT": {
        "target_split": {"WR": 0.70, "TE": 0.18, "RB": 0.12},
        "wr_sinks": {"WR2": 0.35, "WR1": 0.30, "WR3": 0.25, "OTHER_WR": 0.10},
        "te_sinks": {"TE1": 0.70, "TE2": 0.30},
        "rb_sinks": {"RB1": 0.55, "RB2": 0.25, "RB_COMMITTEE": 0.20},
        "note": "Slot out→WR2/WR1; WR3 inherits some slot volume",
    },
    "TE1": {
        "target_split": {"TE": 0.38, "WR": 0.52, "RB": 0.10},
        "te_sinks": {"TE2": 0.85, "OTHER_TE": 0.15},
        "wr_sinks": {"WR1": 0.35, "WR2": 0.28, "WR_SLOT": 0.22, "WR3": 0.15},
        "rb_sinks": {"RB1": 0.60, "RB2": 0.25, "RB_COMMITTEE": 0.15},
        "note": "TE1_out→TE2 primary TE sink; WR mix (WR1>WR2>slot>WR3); small RB",
    },
    "TE2": {
        "target_split": {"TE": 0.45, "WR": 0.45, "RB": 0.10},
        "te_sinks": {"TE1": 0.85, "OTHER_TE": 0.15},
        "wr_sinks": {"WR1": 0.30, "WR2": 0.30, "WR_SLOT": 0.25, "WR3": 0.15},
        "rb_sinks": {"RB1": 0.55, "RB2": 0.30, "RB_COMMITTEE": 0.15},
        "note": "TE2_out→TE1 + balanced WR mix",
    },
    "QB1": {
        "snap_sinks": {"QB2": 0.90, "OTHER_QB": 0.10},
        "rush_to_rb_frac": 0.35,
        "note": "QB1_out→QB2 snap inheritance; most designed rush lost to other",
    },
    "QB2": {
        "snap_sinks": {"QB1": 1.0},
        "rush_to_rb_frac": 0.20,
        "note": "QB2_out→minimal; QB1 already primary",
    },
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def infer_personnel_package(
    pass_rate: float,
    script: ScriptState,
    *,
    script_intensity: float = 0.55,
    time_bucket: TimeBucket = "mid",
) -> str:
    """Map pass rate + script (+ intensity/clock) to a personnel package."""
    late_hot = time_bucket == "late" and script_intensity >= 0.55
    if script == "trail" or pass_rate >= 0.62:
        return "pass_heavy"
    if late_hot and script != "lead" and pass_rate >= 0.56:
        return "pass_heavy"
    if script == "lead" or pass_rate <= 0.50:
        return "rush_heavy"
    if late_hot and script == "lead" and pass_rate <= 0.56:
        return "rush_heavy"
    return "balanced"


def _intensity_scale(
    script_intensity: float,
    time_bucket: TimeBucket,
    *,
    script: ScriptState,
) -> float:
    """How hard to apply SCRIPT_USAGE_MATRIX deltas (1.0 ≈ historical mid)."""
    if script == "neutral":
        return 0.0
    late = {"early": 0.55, "mid": 0.90, "late": 1.30}[time_bucket]
    # Typical mid-game lead/trail ≈ 0.55 intensity → scale ≈ 1.0
    raw = (0.40 + 1.10 * _clamp(script_intensity, 0.0, 1.0)) * late
    return _clamp(raw, 0.30, 1.85)


def assign_usage_role_label(role: PlayerRole, teammates: Sequence[PlayerRole]) -> str:
    """Derive an inspectable usage-role label for one player given team depth."""
    pos = (role.position or "").upper()
    depth = max(1, int(role.depth_order or 1))
    same = [r for r in teammates if (r.position or "").upper() == pos]

    if pos == "QB":
        return "QB1" if depth == 1 else "QB2"

    if pos == "RB":
        rbs = sorted(same, key=lambda r: (r.depth_order, -r.rush_share))
        if len(rbs) >= 2:
            top, second = rbs[0], rbs[1]
            # Committee: top two both meaningful and close in rush share.
            if (
                top.rush_share >= 0.28
                and second.rush_share >= 0.28
                and abs(top.rush_share - second.rush_share) <= 0.14
            ):
                if role.player_key in (top.player_key, second.player_key):
                    return "RB_COMMITTEE"
        if depth == 1:
            return "RB1"
        if depth == 2:
            return "RB2"
        return "RB_COMMITTEE" if role.rush_share >= 0.20 else "OTHER"

    if pos == "WR":
        wrs = sorted(same, key=lambda r: (r.depth_order, -r.target_share))
        # Map by depth rank among WRs (not raw depth_order gaps).
        rank = next((i + 1 for i, r in enumerate(wrs) if r.player_key == role.player_key), depth)
        if rank == 1:
            return "WR1"
        if rank == 2:
            return "WR2"
        if rank == 3:
            # 3-WR sets: treat depth-3 as WR3; 4+ WR sets: depth-3 = WR3, 4th = slot.
            return "WR3"
        return "WR_SLOT"

    if pos == "TE":
        return "TE1" if depth == 1 else "TE2"

    return "OTHER"


def annotate_usage_roles(roles: Sequence[PlayerRole]) -> List[PlayerRole]:
    """Return roles with ``usage_role`` filled (idempotent if already set)."""
    roles_list = list(roles)
    out: List[PlayerRole] = []
    for role in roles_list:
        if role.usage_role and role.usage_role in USAGE_ROLE_LABELS:
            out.append(role)
            continue
        label = assign_usage_role_label(role, roles_list)
        out.append(replace(role, usage_role=label))
    return out


def annotate_roster_book(
    rosters: Mapping[str, Sequence[PlayerRole]],
) -> Dict[str, List[PlayerRole]]:
    return {team: annotate_usage_roles(roles) for team, roles in rosters.items()}


def base_usage_for_role(usage_role: str) -> Dict[str, float]:
    return dict(BASE_USAGE_BY_ROLE.get(usage_role) or BASE_USAGE_BY_ROLE["OTHER"])


def effective_usage_shares(
    role: PlayerRole,
    *,
    script: ScriptState,
    pass_rate: float,
    prefer_role_priors: bool = True,
    script_intensity: float = 0.55,
    time_bucket: TimeBucket = "mid",
    script_detail: Optional[ScriptDetail] = None,
) -> Dict[str, Any]:
    """Combine loaded role shares with script + personnel modifiers.

    When ``prefer_role_priors`` is True (default), start from the player's
    loaded absolute shares (depth/demo/DB) and only fill zeros from the
    role table. Script/personnel mults always apply.

    v1.6: matrix deltas are scaled by ``script_intensity`` × time bucket so
    trailing late reacts more sharply than an early small deficit. Optional
    ``script_detail`` applies a tiny ``SCRIPT_DETAIL_EXTRA`` overlay for
    large_lead / large_deficit only.
    """
    label = role.usage_role or assign_usage_role_label(role, [role])
    table = base_usage_for_role(label)
    pos = (role.position or "").upper()

    if prefer_role_priors:
        # Trust loaded absolute shares, including explicit zeros from injury
        # shocks. Only fill snap/route defaults when those fields were never set.
        snap = float(role.snap_share) if role.snap_share > 0 else table["snap_share"]
        rush = float(role.rush_share)
        tgt = float(role.target_share)
        if role.route_share > 0:
            route = float(role.route_share)
        elif tgt > 0 or pos in ("WR", "TE", "RB"):
            route = table["route_share"]
        else:
            route = 0.0
    else:
        snap = table["snap_share"]
        rush = table["rush_share"]
        tgt = table["target_share"]
        route = table["route_share"]

    script_mods = SCRIPT_USAGE_MATRIX.get(script, {}).get(label, {})
    detail: ScriptDetail = script_detail or (
        "neutral"
        if script == "neutral"
        else ("small_lead" if script == "lead" else "small_deficit")
    )
    detail_mods = SCRIPT_DETAIL_EXTRA.get(detail, {}).get(label, {})
    scale = _intensity_scale(script_intensity, time_bucket, script=script)
    personnel = infer_personnel_package(
        pass_rate,
        script,
        script_intensity=script_intensity,
        time_bucket=time_bucket,
    )
    pers_mods = PERSONNEL_MIX_TABLE.get(personnel, {}).get(label, {})

    def _scaled_mult(table_mult: float) -> float:
        # 1 + (m - 1) * scale  → scale=1 preserves table; scale=0 → identity.
        return 1.0 + (float(table_mult) - 1.0) * scale

    def _apply(base: float, key_mult: str) -> float:
        script_m = _scaled_mult(float(script_mods.get(key_mult, 1.0)))
        detail_m = float(detail_mods.get(key_mult, 1.0))
        # Detail extras are small and already "full strength" for large_* only.
        if detail_m != 1.0:
            detail_m = 1.0 + (detail_m - 1.0) * _clamp(0.5 + 0.5 * scale, 0.5, 1.25)
        pers_m = float(pers_mods.get(key_mult, 1.0))
        return max(0.0, base * script_m * detail_m * pers_m)

    snap = _clamp(
        snap
        + float(script_mods.get("snap_delta", 0.0)) * scale
        + float(pers_mods.get("snap_delta", 0.0)),
        0.0,
        1.0,
    )
    return {
        "usage_role": label,
        "personnel": personnel,
        "script": script,
        "script_detail": detail,
        "script_intensity": round(float(script_intensity), 4),
        "time_bucket": time_bucket,
        "intensity_scale": round(scale, 4),
        "snap_share": snap,
        "rush_share": _apply(rush, "rush_mult"),
        "target_share": _apply(tgt, "target_mult"),
        "route_share": _apply(route, "route_mult"),
    }


def script_matrix_documentation() -> Dict[str, Any]:
    """Serialize matrices for diagnostics / ops dumps."""
    from src.services.nfl_season_engine.depth_chart import depth_chart_documentation
    from src.services.nfl_season_engine.red_zone import red_zone_share_tables

    return {
        "base_usage_by_role": BASE_USAGE_BY_ROLE,
        "script_usage_matrix": SCRIPT_USAGE_MATRIX,
        "script_detail_extra": SCRIPT_DETAIL_EXTRA,
        "personnel_mix_table": PERSONNEL_MIX_TABLE,
        "injury_realloc_rules": {
            k: {rk: rv for rk, rv in v.items() if rk == "note" or isinstance(rv, (dict, float, int, str))}
            for k, v in INJURY_REALLOC_RULES.items()
        },
        "personnel_inference": (
            "pass_heavy if trail or pass_rate>=0.62 (or late high-intensity trail "
            "with pass_rate>=0.56); rush_heavy if lead or pass_rate<=0.50 "
            "(or late high-intensity lead with pass_rate<=0.56); else balanced"
        ),
        "intensity_scaling": (
            "matrix deltas scaled by (0.40 + 1.10*intensity) * "
            "{early:0.55, mid:0.90, late:1.30}; clamped [0.30, 1.85]"
        ),
        "depth_chart": depth_chart_documentation(),
        "red_zone": red_zone_share_tables(),
    }


def role_weight_from_sink_map(
    role: PlayerRole,
    sink_map: Mapping[str, float],
) -> float:
    """Look up relative reallocation weight for a role from a sink map."""
    label = role.usage_role or ""
    if label in sink_map:
        return float(sink_map[label])
    # Fallbacks for unlabeled / generic depth.
    pos = (role.position or "").upper()
    depth = max(1, int(role.depth_order or 1))
    if pos == "RB" and "OTHER_RB" in sink_map and depth >= 3:
        return float(sink_map["OTHER_RB"])
    if pos == "WR" and "OTHER_WR" in sink_map and depth >= 4:
        return float(sink_map["OTHER_WR"])
    if pos == "TE" and "OTHER_TE" in sink_map and depth >= 3:
        return float(sink_map["OTHER_TE"])
    if pos == "QB" and "OTHER_QB" in sink_map and depth >= 3:
        return float(sink_map["OTHER_QB"])
    return 0.0


def split_by_role_sinks(
    amount: float,
    candidates: Sequence[PlayerRole],
    sink_map: Mapping[str, float],
) -> Dict[str, float]:
    """Allocate ``amount`` across candidates using role sink weights."""
    if amount <= 1e-12 or not candidates:
        return {}
    weights = [max(0.0, role_weight_from_sink_map(r, sink_map)) for r in candidates]
    # If no labeled sinks matched, fall back to depth-order heuristic.
    if sum(weights) <= 1e-12:
        weights = [{1: 1.0, 2: 0.70, 3: 0.45}.get(int(r.depth_order or 1), 0.25) for r in candidates]
    total = sum(weights)
    if total <= 1e-12:
        return {}
    return {r.player_key: amount * (w / total) for r, w in zip(candidates, weights) if w > 0}
