"""Snap-share priors on DepthSot accept — same pack, no second SoT.

``proposed_patch`` may set per-player ``snap_share_prior`` (0–1) and optional
``snap_share_package``. Accept is the only write gate.

Defaults come from depth rank (or package table) when the field is missing.
When accept takes a player **out**, freed share redistributes to the existing
same-position committee — **no new WR1/QB1 crown** (depth_order /
competition_status untouched).

Fantasy / season-engine remat reads the same pack shares via
``resolve_snap_share_prior`` / loader wiring.

Out of scope: rest/weather, shock_table edits, live desk accepts, confirmation
or variance layers.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from src.services.nfl_season_engine.usage_roles import BASE_USAGE_BY_ROLE, USAGE_ROLE_LABELS

SNAP_SHARE_PRIOR_VERSION = "snap_share_prior_v1"
SNAP_SHARE_PRIOR_FIELD = "snap_share_prior"
SNAP_SHARE_PACKAGE_FIELD = "snap_share_package"
SNAP_SHARE_PATCH_FIELDS = frozenset({SNAP_SHARE_PRIOR_FIELD, SNAP_SHARE_PACKAGE_FIELD})

# Depth-rank defaults (align with loaders._role_from_depth_row skill snaps).
DEPTH_SNAP_DEFAULTS: Dict[str, Dict[int, float]] = {
    "QB": {1: 0.9, 2: 0.45, 3: 0.2},
    "RB": {1: 0.65, 2: 0.38, 3: 0.18},
    "WR": {1: 0.65, 2: 0.38, 3: 0.18},
    "TE": {1: 0.65, 2: 0.38, 3: 0.18},
}

_OUT = frozenset({"out", "ir", "pup", "suspended", "inactive", "waived"})
_SKILL = frozenset({"QB", "RB", "WR", "TE", "HB", "FB"})


def _pos(raw: Any) -> str:
    pos = str(raw or "").strip().upper()
    if pos in {"HB", "FB"}:
        return "RB"
    return pos


def _order(row: Mapping[str, Any]) -> int:
    try:
        return int(row.get("depth_order") or 99)
    except (TypeError, ValueError):
        return 99


def _status(row: Mapping[str, Any]) -> str:
    return str(row.get("injury_status") or "").strip().lower()


def _slot(row: Mapping[str, Any]) -> str:
    return str(row.get("depth_slot") or "").strip().lower()


def is_out_row(row: Mapping[str, Any]) -> bool:
    if _status(row) in _OUT:
        return True
    return _slot(row) == "out" or _order(row) >= 90


def clamp_share(value: Any) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, v))


def default_snap_share_from_depth(position: str, depth_order: Any) -> float:
    """Default prior from depth rank when pack field is missing."""
    pos = _pos(position)
    try:
        d = int(depth_order) if depth_order is not None else 99
    except (TypeError, ValueError):
        d = 99
    if d < 1:
        d = 1
    table = DEPTH_SNAP_DEFAULTS.get(pos) or DEPTH_SNAP_DEFAULTS["WR"]
    if d in table:
        return float(table[d])
    return 0.1


def default_snap_share_from_package(package: Any) -> Optional[float]:
    label = str(package or "").strip().upper()
    if not label:
        return None
    # Accept common aliases from desk drafts.
    aliases = {
        "RB_COMMITTEE": "RB_COMMITTEE",
        "COMMITTEE": "RB_COMMITTEE",
        "WR_SLOT": "WR_SLOT",
        "SLOT": "WR_SLOT",
    }
    key = aliases.get(label, label)
    if key not in USAGE_ROLE_LABELS:
        return None
    table = BASE_USAGE_BY_ROLE.get(key) or {}
    if "snap_share" not in table:
        return None
    return clamp_share(table["snap_share"])


def resolve_snap_share_prior(row: Mapping[str, Any]) -> float:
    """Explicit pack prior → package table → depth-rank default.

    Out / IR rows resolve to **0** for fantasy / remat (freed mass is handled
    by ``redistribute_out_snap_share`` before this is read downstream).
    """
    if is_out_row(row):
        return 0.0
    raw = row.get(SNAP_SHARE_PRIOR_FIELD)
    if raw is not None and str(raw).strip() != "":
        return clamp_share(raw)
    pkg = default_snap_share_from_package(row.get(SNAP_SHARE_PACKAGE_FIELD))
    if pkg is not None:
        return pkg
    return default_snap_share_from_depth(row.get("position"), row.get("depth_order"))


def committee_recipients(
    rows: Sequence[Mapping[str, Any]],
    *,
    team: str,
    position: str,
    exclude_player_id: str = "",
    exclude_player_name: str = "",
) -> List[Mapping[str, Any]]:
    """Healthy same-pos teammates already on the chart (no invented crowns)."""
    team_n = str(team or "").strip().upper()
    pos_n = _pos(position)
    out: List[Mapping[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        if str(row.get("team") or "").strip().upper() != team_n:
            continue
        if _pos(row.get("position")) != pos_n:
            continue
        if is_out_row(row):
            continue
        pid = str(row.get("player_id") or "")
        name = str(row.get("player_name") or "").strip()
        if exclude_player_id and pid and pid == exclude_player_id:
            continue
        if exclude_player_name and name and name == exclude_player_name:
            continue
        # Existing committee only — must already have a depth slot/order.
        if _order(row) >= 90 and _slot(row) == "out":
            continue
        out.append(row)
    return out


def redistribute_out_snap_share(
    rows: Sequence[MutableMapping[str, Any]],
    *,
    team: str,
    position: str,
    out_player_id: str = "",
    out_player_name: str = "",
) -> Dict[str, Any]:
    """Zero the out player's prior; split freed share across existing committee.

    Never mutates ``depth_order`` / ``competition_status`` (no WR1/QB1 crown).
    """
    team_n = str(team or "").strip().upper()
    pos_n = _pos(position)
    target: Optional[MutableMapping[str, Any]] = None
    for row in rows:
        if not isinstance(row, MutableMapping):
            continue
        if str(row.get("team") or "").strip().upper() != team_n:
            continue
        if _pos(row.get("position")) != pos_n:
            continue
        pid = str(row.get("player_id") or "")
        name = str(row.get("player_name") or "").strip()
        if out_player_id and pid == out_player_id:
            target = row
            break
        if out_player_name and name == out_player_name:
            target = row
            break
    if target is None:
        return {"redistributed": False, "reason": "out player not found"}

    # Prefer explicit prior / package / depth — ignore out-zeroing for freed mass.
    raw_prior = target.get(SNAP_SHARE_PRIOR_FIELD)
    if raw_prior is not None and str(raw_prior).strip() != "":
        freed = clamp_share(raw_prior)
    else:
        pkg = default_snap_share_from_package(target.get(SNAP_SHARE_PACKAGE_FIELD))
        freed = (
            float(pkg)
            if pkg is not None
            else default_snap_share_from_depth(pos_n, target.get("depth_order"))
        )

    target[SNAP_SHARE_PRIOR_FIELD] = 0.0
    # Preserve package label for audit; share is zero while out.
    recipients = [
        r
        for r in rows
        if isinstance(r, MutableMapping)
        and str(r.get("team") or "").strip().upper() == team_n
        and _pos(r.get("position")) == pos_n
        and r is not target
        and not is_out_row(r)
    ]
    if not recipients or freed <= 1e-12:
        return {
            "redistributed": True,
            "freed": freed,
            "recipients": [],
            "crowned": False,
            "version": SNAP_SHARE_PRIOR_VERSION,
        }

    # Weight by current prior (or depth default) — existing committee only.
    weights: List[Tuple[MutableMapping[str, Any], float]] = []
    for r in recipients:
        w = resolve_snap_share_prior(r)
        if w <= 1e-12:
            w = default_snap_share_from_depth(pos_n, r.get("depth_order"))
        weights.append((r, max(0.05, w)))
    total_w = sum(w for _, w in weights) or 1.0
    applied: List[Dict[str, Any]] = []
    for r, w in weights:
        before = resolve_snap_share_prior(r)
        add = freed * (w / total_w)
        after = clamp_share(before + add)
        r[SNAP_SHARE_PRIOR_FIELD] = after
        # Explicitly do not touch depth / competition.
        applied.append(
            {
                "player_id": r.get("player_id"),
                "player_name": r.get("player_name"),
                "depth_order": r.get("depth_order"),
                "before": before,
                "after": after,
            }
        )
    return {
        "redistributed": True,
        "freed": freed,
        "out_player": {
            "player_id": target.get("player_id"),
            "player_name": target.get("player_name"),
            "depth_order": target.get("depth_order"),
        },
        "recipients": applied,
        "crowned": False,
        "version": SNAP_SHARE_PRIOR_VERSION,
    }


def apply_out_redistribution_after_overrides(
    payload: MutableMapping[str, Any],
    applied_overrides: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """After accept writes injury_status=out, redistribute snap priors on skill rows."""
    events: List[Dict[str, Any]] = []
    rows = payload.get("rows")
    if not isinstance(rows, list):
        return events
    seen: set[Tuple[str, str, str]] = set()
    for ov in applied_overrides:
        field = str(ov.get("field") or "")
        after = str(ov.get("after") or "").strip().lower()
        if field != "injury_status" or after not in _OUT:
            continue
        team = str(ov.get("team") or "").strip().upper()
        pos = _pos(ov.get("position") or "")
        # Resolve position from matched row when override omitted it.
        if pos not in _SKILL:
            for row in rows:
                if not isinstance(row, dict):
                    continue
                if str(row.get("team") or "").upper() != team:
                    continue
                pid = str(ov.get("matched_player_id") or ov.get("player_id") or "")
                name = str(ov.get("player_name") or "").strip()
                if pid and str(row.get("player_id") or "") == pid:
                    pos = _pos(row.get("position"))
                    break
                if name and str(row.get("player_name") or "").strip() == name:
                    pos = _pos(row.get("position"))
                    break
        if pos not in _SKILL:
            continue
        key = (
            team,
            pos,
            str(ov.get("matched_player_id") or ov.get("player_id") or ov.get("player_name") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        result = redistribute_out_snap_share(
            rows,
            team=team,
            position=pos,
            out_player_id=str(ov.get("matched_player_id") or ov.get("player_id") or ""),
            out_player_name=str(ov.get("player_name") or ""),
        )
        events.append({**result, "team": team, "position": pos})
    return events


def fantasy_shares_from_pack_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    team: str,
    position: str,
) -> Dict[str, float]:
    """Fantasy / remat helper: {player_id: snap_share_prior} for a room."""
    team_n = str(team or "").strip().upper()
    pos_n = _pos(position)
    out: Dict[str, float] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        if str(row.get("team") or "").strip().upper() != team_n:
            continue
        if _pos(row.get("position")) != pos_n:
            continue
        pid = str(row.get("player_id") or row.get("player_name") or "")
        if not pid:
            continue
        out[pid] = resolve_snap_share_prior(row)
    return out


def validate_no_crown_from_redistribution(
    before_rows: Sequence[Mapping[str, Any]],
    after_rows: Sequence[Mapping[str, Any]],
) -> None:
    """Guard: redistribution must not invent depth_order / competition crowns."""
    before = {
        (str(r.get("player_id") or ""), str(r.get("player_name") or "")): r
        for r in before_rows
        if isinstance(r, Mapping)
    }
    for r in after_rows:
        if not isinstance(r, Mapping):
            continue
        key = (str(r.get("player_id") or ""), str(r.get("player_name") or ""))
        prev = before.get(key)
        if not prev:
            continue
        if prev.get("depth_order") != r.get("depth_order"):
            raise AssertionError("snap redistribute must not change depth_order")
        if prev.get("competition_status") != r.get("competition_status"):
            raise AssertionError("snap redistribute must not change competition_status")


def copy_rows(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    return [deepcopy(dict(r)) for r in rows if isinstance(r, Mapping)]
