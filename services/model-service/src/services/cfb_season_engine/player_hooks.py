"""Player-level hooks (QB + skill) allocated from team offense totals.

v0.7 — first real player projection layer:
- ESPN roster names / depth order supply identity
- Team pass/rush yards + TDs derived from project-game expected points
- Role shares allocate down to QB1 + primary skill (residual "other" OK)
- Does **not** mutate team scores / spreads / totals

Honesty: approximate role-share allocation, not a box-score engine.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from src.services.cfb_season_engine import priors as P
from src.services.cfb_season_engine.types import (
    EngineUniverse,
    GameProjection,
    PlayerHook,
    QbSituation,
    TeamProjectionState,
)

SKILL_POSITIONS = ("RB", "WR", "TE")
OFFENSE_POSITIONS = ("QB", "RB", "WR", "TE")


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _normalize(weights: Sequence[float], *, residual: float = 0.0) -> List[float]:
    """Normalize non-negative weights so they sum to (1 - residual)."""
    res = _clamp(residual, 0.0, 0.45)
    target = 1.0 - res
    cleaned = [max(0.0, float(w)) for w in weights]
    total = sum(cleaned)
    if total <= 0.0:
        n = len(cleaned)
        if n == 0:
            return []
        return [target / n] * n
    return [target * w / total for w in cleaned]


def _role_label(position: str, depth_order: int) -> str:
    pos = position.upper()
    if pos in OFFENSE_POSITIONS:
        return f"{pos}{max(1, int(depth_order))}"
    return pos


def _rb_committee_label(rbs: Sequence[PlayerHook]) -> str:
    """feature | committee — rough, from depth-1 vs depth-2 usage."""
    ordered = sorted(rbs, key=lambda h: (h.depth_order, -h.usage_share))
    if not ordered:
        return "committee"
    if len(ordered) == 1:
        return "feature"
    top, second = ordered[0], ordered[1]
    top_w = max(top.usage_share, 1.0 / max(1, top.depth_order))
    sec_w = max(second.usage_share, 1.0 / max(1, second.depth_order))
    if top_w >= P.PLAYER_RB_FEATURE_RATIO * sec_w:
        return "feature"
    return "committee"


def build_player_hooks(
    team: str,
    payload_rows: Optional[Sequence[Mapping[str, Any]]] = None,
    *,
    qb: Optional[QbSituation] = None,
    default_source: str = "packaged_prior",
) -> List[PlayerHook]:
    """Build player hooks for a team; synthesize QB hook from Layer 2 if needed.

    Depth order is assigned within position from payload order when missing
    (ESPN snapshot lists production-depth rows per position).
    """
    out: List[PlayerHook] = []
    depth_counters: Dict[str, int] = {}
    for row in payload_rows or []:
        name = str(row.get("player_name", "") or "")
        key = str(row.get("player_key", "") or "")
        player_id = str(row.get("player_id", "") or "")
        if not key and player_id:
            key = f"{team.lower()}_{player_id}"
        if not key and name:
            key = name.lower().replace(" ", "_").replace(".", "").replace("'", "")
        fidelity = str(row.get("fidelity", "approximate"))
        if fidelity not in ("real", "approximate", "placeholder"):
            fidelity = "approximate"
        position = str(row.get("position", "WR")).upper()
        if "depth_order" in row and row.get("depth_order") is not None:
            depth_order = int(row.get("depth_order") or 1)
        else:
            depth_counters[position] = depth_counters.get(position, 0) + 1
            depth_order = depth_counters[position]
        out.append(
            PlayerHook(
                player_key=key or f"{team.lower()}_unk",
                player_name=name or key,
                team=str(team),
                position=position,
                depth_order=depth_order,
                usage_share=float(row.get("usage_share", 0.0) or 0.0),
                talent=float(row.get("talent", 50.0) or 50.0),
                source=str(row.get("source", default_source)),
                fidelity=fidelity,  # type: ignore[arg-type]
            )
        )

    has_qb = any(h.position == "QB" for h in out)
    if qb and qb.starter_name and not has_qb:
        out.insert(
            0,
            PlayerHook(
                player_key=qb.starter_key or f"{team.lower()}_qb1",
                player_name=qb.starter_name,
                team=str(team),
                position="QB",
                depth_order=1,
                usage_share=0.92,
                talent=qb.qb_talent,
                source=qb.source,
                fidelity=qb.fidelity,
            ),
        )
    return out


def hooks_to_summaries(hooks: Sequence[PlayerHook]) -> List[Dict[str, Any]]:
    return [
        {
            "player_key": h.player_key,
            "player_name": h.player_name,
            "team": h.team,
            "position": h.position,
            "depth_order": h.depth_order,
            "role": _role_label(h.position, h.depth_order),
            "usage_share": round(h.usage_share, 3),
            "talent": round(h.talent, 2),
            "source": h.source,
            "fidelity": h.fidelity,
        }
        for h in hooks
    ]


def derive_team_offense_totals(
    expected_points: float,
    state: TeamProjectionState,
) -> Dict[str, float]:
    """Approximate team pass/rush yards + TDs from expected points + pace/pass bias.

    Transparent prior — not calibrated to play-by-play. Used only as the
    allocation pool for player hooks (does not feed back into team scores).
    """
    pts = max(3.0, float(expected_points))
    plays = _clamp(
        P.LEAGUE_BASE_PLAYS * float(state.pace_factor),
        *P.PACE_PLAYS_CLAMP,
    )
    pass_rate = _clamp(
        P.LEAGUE_BASE_PASS_RATE + float(state.pass_rate_bias),
        0.35,
        0.72,
    )
    total_yards = pts * P.PLAYER_YARDS_PER_POINT
    # Pass YPP > rush YPP → pass yard share slightly above play pass rate.
    pass_yard_share = _clamp(pass_rate + 0.06, 0.38, 0.74)
    pass_yards = total_yards * pass_yard_share
    rush_yards = total_yards - pass_yards

    offensive_tds = max(0.35, pts / P.PLAYER_POINTS_PER_OFFENSIVE_TD)
    pass_td_share = _clamp(0.45 + 0.65 * (pass_rate - 0.50), 0.32, 0.72)
    pass_tds = offensive_tds * pass_td_share
    rush_tds = offensive_tds - pass_tds

    pass_attempts = pass_yards / max(5.5, P.PLAYER_PASS_YARDS_PER_ATTEMPT)
    qb_idx = float(state.qb.qb_situation_index) if state.qb else 1.0
    int_rate = P.PLAYER_BASE_INT_RATE * _clamp(1.12 - 0.35 * (qb_idx - 1.0), 0.70, 1.35)
    # Supporting cast mildly lowers INT rate (does not change team yards).
    if state.qb is not None:
        cast = float(state.qb.supporting_cast)
        int_rate *= _clamp(1.08 - (cast - 50.0) / 400.0, 0.85, 1.15)
    interceptions = pass_attempts * int_rate

    # Dual-threat / young QB rush share of team rush yards.
    qb_rush_share = P.PLAYER_QB_RUSH_SHARE_BASE
    if state.qb is not None:
        if state.qb.qb_class in ("true_freshman", "open_competition"):
            qb_rush_share += 0.03
        qb_rush_share += _clamp((float(state.qb.qb_talent) - 50.0) / 500.0, -0.02, 0.05)
        # Better weapons → slightly less designed QB run volume.
        qb_rush_share *= _clamp(
            1.05 - (float(state.qb.weapons_support) - 50.0) / 500.0, 0.85, 1.12
        )
    qb_rush_share = _clamp(qb_rush_share, 0.02, 0.18)

    return {
        "expected_points": round(pts, 3),
        "plays": round(plays, 2),
        "pass_rate": round(pass_rate, 4),
        "pass_yards": round(pass_yards, 2),
        "rush_yards": round(rush_yards, 2),
        "pass_tds": round(pass_tds, 3),
        "rush_tds": round(rush_tds, 3),
        "interceptions": round(interceptions, 3),
        "pass_attempts": round(pass_attempts, 2),
        "qb_rush_share": round(qb_rush_share, 4),
    }


def _position_weight(hook: PlayerHook) -> float:
    """Within-position weight from packaged usage_share or depth fallback."""
    if hook.usage_share > 0.0:
        return float(hook.usage_share)
    return 1.0 / max(1, int(hook.depth_order))


def _receiving_base_weight(hook: PlayerHook) -> float:
    """Prior target weight by role, scaled by usage_share."""
    role = _role_label(hook.position, hook.depth_order)
    priors = {
        "WR1": 0.26,
        "WR2": 0.18,
        "WR3": 0.12,
        "TE1": 0.14,
        "TE2": 0.08,
        "RB1": 0.12,
        "RB2": 0.07,
        "RB3": 0.04,
    }
    base = priors.get(role, 0.05)
    return base * max(0.35, _position_weight(hook))


def allocate_team_player_projections(
    *,
    team: str,
    hooks: Sequence[PlayerHook],
    expected_points: float,
    state: TeamProjectionState,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Allocate team offense totals onto named QB + skill hooks."""
    team = str(team).upper()
    totals = derive_team_offense_totals(expected_points, state)
    offense_hooks = [h for h in hooks if h.position in OFFENSE_POSITIONS]
    qbs = sorted(
        [h for h in offense_hooks if h.position == "QB"],
        key=lambda h: (h.depth_order, -h.usage_share),
    )
    rbs = sorted(
        [h for h in offense_hooks if h.position == "RB"],
        key=lambda h: (h.depth_order, -h.usage_share),
    )
    receivers = sorted(
        [h for h in offense_hooks if h.position in ("WR", "TE", "RB")],
        key=lambda h: (h.position != "WR", h.position != "TE", h.depth_order),
    )

    # --- Pass volume (QB) ---
    qb_weights = [_position_weight(h) for h in qbs]
    # Soft-cap backup so QB1 clearly leads even if snapshot usage is noisy.
    if qbs:
        qb_weights = [
            w * (1.0 if h.depth_order == 1 else 0.35) for h, w in zip(qbs, qb_weights)
        ]
    qb_pass_shares = _normalize(qb_weights, residual=P.PLAYER_PASS_RESIDUAL)
    qb_pass_by_key = {
        h.player_key: share for h, share in zip(qbs, qb_pass_shares)
    }

    # --- Rush volume (RB pool + QB scramble/design) ---
    qb_rush_pool = float(totals["qb_rush_share"])
    rb_pool = max(0.0, 1.0 - qb_rush_pool - P.PLAYER_RUSH_RESIDUAL)
    rb_weights = [_position_weight(h) for h in rbs]
    rb_shares_within = _normalize(rb_weights, residual=0.0)
    rush_by_key: Dict[str, float] = {}
    for h, share in zip(rbs, rb_shares_within):
        rush_by_key[h.player_key] = rb_pool * share
    if qbs:
        # Almost all QB rush to QB1; tiny backup residual.
        qb1 = qbs[0]
        rush_by_key[qb1.player_key] = rush_by_key.get(qb1.player_key, 0.0) + qb_rush_pool * 0.92
        if len(qbs) > 1:
            rush_by_key[qbs[1].player_key] = (
                rush_by_key.get(qbs[1].player_key, 0.0) + qb_rush_pool * 0.08
            )

    # --- Receiving yards / pass TDs to skill ---
    rec_weights = [_receiving_base_weight(h) for h in receivers]
    rec_shares = _normalize(rec_weights, residual=P.PLAYER_REC_RESIDUAL)
    rec_by_key = {h.player_key: share for h, share in zip(receivers, rec_shares)}

    # Pass TD share mirrors receiving share among skill; QB gets the pass TD credit.
    rush_td_weights = [
        rush_by_key.get(h.player_key, 0.0) * (1.15 if h.position == "RB" else 1.0)
        for h in offense_hooks
        if h.position in ("RB", "QB")
    ]
    rush_td_hooks = [h for h in offense_hooks if h.position in ("RB", "QB")]
    rush_td_shares = _normalize(rush_td_weights, residual=P.PLAYER_RUSH_TD_RESIDUAL)
    rush_td_by_key = {
        h.player_key: share for h, share in zip(rush_td_hooks, rush_td_shares)
    }

    rb_style = _rb_committee_label(rbs)
    rows: List[Dict[str, Any]] = []
    named_pass_yds = 0.0
    named_rush_yds = 0.0
    named_rec_yds = 0.0
    named_pass_tds = 0.0
    named_rush_tds = 0.0
    named_rec_tds = 0.0
    named_ints = 0.0

    for h in sorted(
        offense_hooks,
        key=lambda x: (
            0 if x.position == "QB" else 1 if x.position == "RB" else 2 if x.position == "WR" else 3,
            x.depth_order,
            x.player_name,
        ),
    ):
        role = _role_label(h.position, h.depth_order)
        pass_share = qb_pass_by_key.get(h.player_key, 0.0)
        rush_share = rush_by_key.get(h.player_key, 0.0)
        rec_share = rec_by_key.get(h.player_key, 0.0)

        pass_yds = totals["pass_yards"] * pass_share if h.position == "QB" else 0.0
        pass_tds = totals["pass_tds"] * pass_share if h.position == "QB" else 0.0
        ints = totals["interceptions"] * pass_share if h.position == "QB" else 0.0
        rush_yds = totals["rush_yards"] * rush_share
        rush_tds_i = totals["rush_tds"] * rush_td_by_key.get(h.player_key, 0.0)
        rec_yds = totals["pass_yards"] * rec_share if h.position != "QB" else 0.0
        rec_tds = totals["pass_tds"] * rec_share if h.position != "QB" else 0.0

        named_pass_yds += pass_yds
        named_rush_yds += rush_yds
        named_rec_yds += rec_yds
        named_pass_tds += pass_tds
        named_rush_tds += rush_tds_i
        named_rec_tds += rec_tds
        named_ints += ints

        row: Dict[str, Any] = {
            "player_key": h.player_key,
            "player_name": h.player_name,
            "team": team,
            "position": h.position,
            "depth_order": h.depth_order,
            "role": role,
            "usage_share": round(h.usage_share, 3),
            "pass_yards": round(pass_yds, 1) if h.position == "QB" else None,
            "pass_tds": round(pass_tds, 2) if h.position == "QB" else None,
            "interceptions": round(ints, 2) if h.position == "QB" else None,
            "rush_yards": round(rush_yds, 1) if rush_yds >= 0.5 or h.position in ("QB", "RB") else None,
            "rush_tds": round(rush_tds_i, 2) if rush_tds_i >= 0.01 or h.position in ("QB", "RB") else None,
            "rec_yards": round(rec_yds, 1) if h.position in SKILL_POSITIONS else None,
            "rec_tds": round(rec_tds, 2) if h.position in SKILL_POSITIONS else None,
            "pass_share": round(pass_share, 4) if h.position == "QB" else None,
            "rush_share": round(rush_share, 4),
            "rec_share": round(rec_share, 4) if h.position in SKILL_POSITIONS else None,
            "rb_role_style": rb_style if h.position == "RB" else None,
            "source": h.source,
            "fidelity": "approximate",
            "method": "role_share_from_team_totals",
        }
        rows.append(row)

    residual = {
        "pass_yards": round(max(0.0, totals["pass_yards"] - named_pass_yds), 2),
        "rush_yards": round(max(0.0, totals["rush_yards"] - named_rush_yds), 2),
        "rec_yards": round(max(0.0, totals["pass_yards"] - named_rec_yds), 2),
        "pass_tds": round(max(0.0, totals["pass_tds"] - named_pass_tds), 3),
        "rush_tds": round(max(0.0, totals["rush_tds"] - named_rush_tds), 3),
        "rec_tds": round(max(0.0, totals["pass_tds"] - named_rec_tds), 3),
        "interceptions": round(max(0.0, totals["interceptions"] - named_ints), 3),
        "note": "Unallocated residual = depth beyond named hooks / committee leftovers",
    }
    meta = {
        "team": team,
        "team_totals": totals,
        "residual": residual,
        "rb_role_style": rb_style,
        "named_player_count": len(rows),
        "qb_situation_index": (
            round(float(state.qb.qb_situation_index), 4) if state.qb else None
        ),
        "supporting_cast": (
            round(float(state.qb.supporting_cast), 2) if state.qb else None
        ),
        "fidelity": "approximate",
        "honesty": (
            "Player yards/TDs are role-share allocations of team totals derived "
            "from expected points — not independent box-score forecasts."
        ),
    }
    return rows, meta


def project_game_player_projections(
    universe: EngineUniverse,
    proj: GameProjection,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Build both-team player projections for a completed team-level game proj."""
    sides = (
        (proj.home_team, proj.expected_home_score),
        (proj.away_team, proj.expected_away_score),
    )
    all_rows: List[Dict[str, Any]] = []
    by_team: Dict[str, Any] = {}
    for team, exp_pts in sides:
        state = universe.teams.get(team)
        if state is None:
            continue
        hooks = universe.player_hooks.get(team, [])
        rows, meta = allocate_team_player_projections(
            team=team,
            hooks=hooks,
            expected_points=exp_pts,
            state=state,
        )
        all_rows.extend(rows)
        by_team[team] = meta
    diagnostics = {
        "by_team": by_team,
        "method": "allocate team pass/rush/TD pools via depth-order role shares",
        "fidelity": "approximate",
        "does_not_modify_team_totals": True,
    }
    return all_rows, diagnostics


def attach_player_projections(
    universe: EngineUniverse,
    proj: GameProjection,
) -> GameProjection:
    """Return a copy of ``proj`` with player_projections populated."""
    rows, diagnostics = project_game_player_projections(universe, proj)
    notes = dict(proj.notes)
    notes["player_layer"] = (
        "v0.7 role-share player hooks; team scores/spreads unchanged by allocation"
    )
    drivers = dict(proj.drivers)
    drivers["player_projections"] = diagnostics
    return replace(
        proj,
        player_projections=rows,
        drivers=drivers,
        notes=notes,
    )


def documentation() -> Dict[str, Any]:
    return {
        "layer": "player_hooks",
        "name": "player_hooks",
        "module": "src.services.cfb_season_engine.player_hooks",
        "status": "v0.7_role_share_allocation",
        "engine_version": P.ENGINE_VERSION,
        "real_vs_approximate": (
            "ESPN roster names + depth order are REAL (packaged snapshot). "
            "Usage shares, yards/TDs, and residual pools are APPROXIMATE "
            "role-share allocations from team expected points — not a "
            "calibrated box-score engine."
        ),
        "focus": ["QB", "RB", "WR", "TE"],
        "method": [
            "derive team pass/rush yards + TDs from expected points × pace/pass bias",
            "allocate pass yards/TDs/INTs to QB depth (QB1 dominates)",
            "allocate rush yards/TDs to RB committee/feature + small QB rush share",
            "allocate receiving yards/pass TDs to WR/TE/RB role priors",
            "leave residual 'other' so named shares sum ≤ team totals",
        ],
        "does_not": [
            "mutate team expected scores / spread / total / win prob",
            "invent full box scores (completions, routes, air yards)",
            "claim market-grade prop calibration",
        ],
    }
