"""Playing-time / opportunity layer — who gets volume, before production.

Depth SoT is authoritative for role. Team pass/rush/rec budgets stay
conserved: capped share is reassigned up the depth chart, not deleted.

Injury / starter_out reallocation stays in ``nfl_injury_role_shocks``.
Priors and snaps must not crown a QB3 over a healthy SoT QB1.
"""

from __future__ import annotations

from typing import Dict, Iterable, Mapping

# Healthy-room defaults (Phase 1 2026-08-20). Tune only with evidence.
QB1_SHARE = 0.94
QB2_SHARE = 0.06
QB3_PLUS_SHARE = 0.0

# Skill caps by depth_order. WR4+ / RB3+ / TE2+ near-zero unless committee.
# Values are ceilings; conservation renormalizes leftover to higher roles.
ROLE_SHARE_CAPS: Dict[str, Dict[int, float]] = {
    "QB": {1: 0.98, 2: 0.08, 3: 0.005},
    "RB": {1: 1.0, 2: 0.40, 3: 0.04},
    "WR": {1: 0.50, 2: 0.28, 3: 0.16, 4: 0.02},
    "TE": {1: 0.40, 2: 0.14, 3: 0.04},
}

WR_DEPTH_TARGET_PRIOR: Dict[int, float] = {1: 0.32, 2: 0.17, 3: 0.11, 4: 0.015}
TE_DEPTH_TARGET_PRIOR: Dict[int, float] = {1: 0.22, 2: 0.10, 3: 0.02}


def role_from_depth_order(position: str, depth_order: float | None) -> str:
    """Map SoT depth_order → QB1 / RB2 / WR4+ style labels."""
    pos = str(position or "").upper()
    if depth_order is None:
        return f"{pos}+"
    d = int(round(float(depth_order)))
    if d < 1:
        d = 1
    if pos == "QB":
        if d <= 1:
            return "QB1"
        if d == 2:
            return "QB2"
        return "QB3+"
    if pos in {"RB", "HB", "FB"}:
        if d <= 1:
            return "RB1"
        if d == 2:
            return "RB2"
        return "RB3+"
    if pos == "WR":
        if d <= 3:
            return f"WR{d}"
        return "WR4+"
    if pos == "TE":
        if d <= 1:
            return "TE1"
        return "TE2+"
    return f"{pos}{d}"


def rank_keys_by_depth_sot(
    keys: Iterable[str],
    depth_orders: Mapping[str, float] | None,
    *,
    snaps: Mapping[str, float] | None = None,
) -> list[str]:
    """Rank a room by SoT depth_order (1 first). Snaps only break ties."""
    depths = depth_orders or {}
    snap_map = snaps or {}
    return sorted(
        list(keys),
        key=lambda k: (
            float(depths.get(k, 99.0) or 99.0),
            -float(snap_map.get(k, 0.0) or 0.0),
            str(k),
        ),
    )


def allocate_qb_role_shares(ranked_keys: list[str]) -> Dict[str, float]:
    """Hard QB1 / QB2 / QB3+ shares. Sums to 1.0. QB3+ is ≈ 0."""
    out: Dict[str, float] = {key: 0.0 for key in ranked_keys}
    if not ranked_keys:
        return out
    if len(ranked_keys) == 1:
        out[ranked_keys[0]] = 1.0
        return out
    out[ranked_keys[0]] = float(QB1_SHARE)
    out[ranked_keys[1]] = float(QB2_SHARE)
    # QB3+ stay 0; residual already sits on QB1+QB2 (0.94+0.06=1.0).
    return out


def _cap_for_depth(position: str, depth_order: float | None) -> float:
    pos = str(position or "").upper()
    if pos in {"HB", "FB"}:
        pos = "RB"
    table = ROLE_SHARE_CAPS.get(pos) or {}
    if depth_order is None:
        # Unknown depth: treat as deep dust, not a silent starter.
        return float(min(table.values())) if table else 0.02
    d = int(round(float(depth_order)))
    if d < 1:
        d = 1
    if d in table:
        return float(table[d])
    last_key = max(table) if table else 4
    return float(table.get(last_key, 0.02))


def apply_hard_share_caps(
    shares: Mapping[str, float],
    depth_orders: Mapping[str, float] | None,
    *,
    position: str,
    committee: bool = False,
) -> Dict[str, float]:
    """Clip shares to role ceilings; leftover flows up the depth chart.

    Committee flag relaxes RB2/WR3 only — RB3+/WR4+/QB3+ stay near-zero.
    """
    keys = list(shares.keys())
    if not keys:
        return {}
    depths = depth_orders or {}
    capped: Dict[str, float] = {}
    leftover = 0.0
    for k in keys:
        raw = max(0.0, float(shares.get(k) or 0.0))
        depth = depths.get(k)
        cap = _cap_for_depth(position, depth)
        d = int(round(float(depth))) if depth is not None else 99
        pos = str(position or "").upper()
        if committee and pos in {"RB", "HB", "FB"} and d == 2:
            cap = max(cap, 0.40)
        if committee and pos == "WR" and d == 3:
            cap = max(cap, 0.16)
        if raw > cap:
            leftover += raw - cap
            capped[k] = cap
        else:
            capped[k] = raw

    if leftover > 1e-9:
        # Prefer lower depth_order (QB1/RB1/WR1).
        receivers = rank_keys_by_depth_sot(keys, depths)
        for k in receivers:
            depth = depths.get(k)
            cap = _cap_for_depth(position, depth)
            d = int(round(float(depth))) if depth is not None else 99
            pos = str(position or "").upper()
            if committee and pos in {"RB", "HB", "FB"} and d == 2:
                cap = max(cap, 0.40)
            room = max(0.0, cap - capped[k])
            if room <= 0.0:
                continue
            take = min(room, leftover)
            capped[k] += take
            leftover -= take
            if leftover <= 1e-12:
                break
        if leftover > 1e-9:
            # Last resort: dump onto SoT primary so team budget is not destroyed.
            primary = receivers[0]
            capped[primary] = capped.get(primary, 0.0) + leftover

    total = sum(capped.values())
    if total <= 0.0:
        primary = rank_keys_by_depth_sot(keys, depths)[0]
        return {k: (1.0 if k == primary else 0.0) for k in keys}
    return {k: v / total for k, v in capped.items()}


def depth_target_prior(position: str, depth_order: float | None) -> float:
    """Depth-chart target share prior for WR/TE (WR4+ near-zero)."""
    pos = str(position or "").upper()
    table = WR_DEPTH_TARGET_PRIOR if pos == "WR" else TE_DEPTH_TARGET_PRIOR
    if depth_order is None:
        return 0.015 if pos == "WR" else 0.02
    d = int(round(float(depth_order)))
    if d < 1:
        d = 1
    if d in table:
        return float(table[d])
    return 0.01 if pos == "WR" else 0.015
