"""Layer 3 — Player usage (targets, carries, routes, snap share).

Consumes Layer 2 game script + roster roles. Script tilts pass/rush volume;
role shares come from depth-chart / prior-usage ``PlayerRole`` rows.

REAL vs PLACEHOLDER
-------------------
- REAL roles: loaded from depth chart + usage features when DB is available.
- PLACEHOLDER roles: demo depth charts in ``loaders.build_demo_universe``.
- Script tilts (lead→rush, trail→pass) are thin structural priors, not a
  fitted tendency model (see ``nfl_tendency_pricing`` for the live board).
"""

from __future__ import annotations

import random
from typing import Dict, List, Mapping, Optional, Sequence

from src.services.nfl_season_engine.types import (
    GameScript,
    PlayerRole,
    PlayerUsage,
    ScriptState,
)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _normalize(shares: Sequence[float]) -> List[float]:
    total = sum(max(0.0, s) for s in shares)
    if total <= 0.0:
        n = len(shares)
        return [1.0 / n] * n if n else []
    return [max(0.0, s) / total for s in shares]


def _dirichlet_noise(rng: random.Random, shares: Sequence[float], concentration: float = 28.0) -> List[float]:
    alphas = [max(1e-3, s * concentration) for s in shares]
    draws = [rng.gammavariate(a, 1.0) for a in alphas]
    return _normalize(draws)


def allocate_team_usage(
    *,
    team: str,
    roles: Sequence[PlayerRole],
    script: GameScript,
    side: str,
    rng: Optional[random.Random] = None,
) -> List[PlayerUsage]:
    """Allocate one-team usage for a single game replicate."""
    rng = rng or random.Random()
    if side == "home":
        pass_rate = script.home_pass_rate
        team_script: ScriptState = script.home_script
    else:
        pass_rate = script.away_pass_rate
        team_script = script.away_script

    # script.pace_plays is already a per-team offensive-play expectation.
    plays = _clamp(script.pace_plays + rng.gauss(0.0, 4.0), 48.0, 85.0)
    pass_plays = plays * pass_rate
    rush_plays = plays * (1.0 - pass_rate)

    qbs = [r for r in roles if r.position == "QB"]
    rushers = [r for r in roles if r.rush_share > 0.0 or r.position in ("RB", "QB")]
    receivers = [r for r in roles if r.target_share > 0.0 or r.position in ("WR", "TE", "RB")]

    # QB starter draw (categorical) — same spirit as box-score simulator.
    qb_attempts: Dict[str, float] = {r.player_key: 0.0 for r in qbs}
    if qbs:
        weights = [max(0.01, (1.0 / max(1, r.depth_order)) * max(0.05, r.snap_share or 0.2)) for r in qbs]
        weight_sum = sum(weights)
        pick = rng.random() * weight_sum
        running = 0.0
        starter = qbs[0]
        for role, w in zip(qbs, weights):
            running += w
            if pick <= running:
                starter = role
                break
        # Small residual for backup in blowouts / injuries (thin).
        starter_share = 0.94 if starter.depth_order <= 1 else 0.88
        qb_attempts[starter.player_key] = pass_plays * starter_share
        backups = [r for r in qbs if r.player_key != starter.player_key]
        if backups:
            residual = pass_plays * (1.0 - starter_share)
            each = residual / len(backups)
            for b in backups:
                qb_attempts[b.player_key] = each

    rush_base = [max(0.0, r.rush_share) for r in rushers]
    if not any(rush_base) and rushers:
        # Depth-order fallback
        rush_base = [1.0 / max(1, r.depth_order) for r in rushers]
    rush_shares = _dirichlet_noise(rng, _normalize(rush_base), concentration=24.0)
    rush_by_key = {r.player_key: rush_plays * s for r, s in zip(rushers, rush_shares)}

    tgt_base = [max(0.0, r.target_share) for r in receivers]
    if not any(tgt_base) and receivers:
        tgt_base = [1.0 / max(1, r.depth_order) for r in receivers]
    tgt_shares = _dirichlet_noise(rng, _normalize(tgt_base), concentration=30.0)
    tgt_by_key = {r.player_key: pass_plays * s for r, s in zip(receivers, tgt_shares)}

    # Script nudge: trailing teams push a bit more volume to WR1; leading
    # teams feed the RB1 a few extra carries.
    if team_script == "trail":
        wr1 = next((r for r in receivers if r.position == "WR" and r.depth_order == 1), None)
        if wr1 is not None:
            tgt_by_key[wr1.player_key] = tgt_by_key.get(wr1.player_key, 0.0) + 1.2
    elif team_script == "lead":
        rb1 = next((r for r in rushers if r.position == "RB" and r.depth_order == 1), None)
        if rb1 is not None:
            rush_by_key[rb1.player_key] = rush_by_key.get(rb1.player_key, 0.0) + 1.5

    out: List[PlayerUsage] = []
    for role in roles:
        snap = role.snap_share
        if snap <= 0.0:
            if role.position == "QB":
                snap = 0.95 if role.depth_order == 1 else 0.08
            elif role.position == "RB":
                snap = {1: 0.62, 2: 0.28, 3: 0.12}.get(role.depth_order, 0.05)
            elif role.position == "WR":
                snap = {1: 0.88, 2: 0.72, 3: 0.55}.get(role.depth_order, 0.25)
            else:  # TE
                snap = {1: 0.70, 2: 0.40}.get(role.depth_order, 0.15)
        # Mild script snap tilt
        if team_script == "trail" and role.position in ("WR", "TE"):
            snap = _clamp(snap + 0.03, 0.0, 1.0)
        if team_script == "lead" and role.position == "RB":
            snap = _clamp(snap + 0.04, 0.0, 1.0)

        out.append(
            PlayerUsage(
                player_key=role.player_key,
                player_name=role.player_name,
                team=team,
                position=role.position,
                snap_share=round(snap, 4),
                route_share=round(role.route_share or (tgt_by_key.get(role.player_key, 0.0) / max(1.0, pass_plays)), 4),
                targets=round(tgt_by_key.get(role.player_key, 0.0), 3),
                carries=round(rush_by_key.get(role.player_key, 0.0), 3),
                pass_attempts=round(qb_attempts.get(role.player_key, 0.0), 3),
                script=team_script,
            )
        )
    return out


def allocate_game_usage(
    script: GameScript,
    rosters: Mapping[str, Sequence[PlayerRole]],
    *,
    rng: Optional[random.Random] = None,
) -> List[PlayerUsage]:
    """Allocate usage for both teams in one game."""
    rng = rng or random.Random()
    home_roles = list(rosters.get(script.home_team, []))
    away_roles = list(rosters.get(script.away_team, []))
    home = allocate_team_usage(team=script.home_team, roles=home_roles, script=script, side="home", rng=rng)
    away = allocate_team_usage(team=script.away_team, roles=away_roles, script=script, side="away", rng=rng)
    return home + away
