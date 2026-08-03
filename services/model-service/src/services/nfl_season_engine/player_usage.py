"""Layer 3 — Player usage (targets, carries, routes, snap share).

Consumes Layer 2 game script + roster roles. Script tilts pass/rush volume;
role shares come from depth-chart / prior-usage ``PlayerRole`` rows.

REAL vs PLACEHOLDER
-------------------
- REAL roles: loaded from depth chart + usage features when DB is available.
- PLACEHOLDER roles: demo depth charts in ``loaders.build_demo_universe``.
- Script tilts (lead→rush, trail→pass) are thin structural priors, not a
  fitted tendency model (see ``nfl_tendency_pricing`` for the live board).

Calibration note
----------------
Target / rush shares are treated as **absolute** fractions of team volume.
A residual "other" bucket absorbs the remainder so sparse skill rosters do
not renormalize WR1/RB1 into unrealistic volume (foundation bug).
"""

from __future__ import annotations

import random
from typing import Dict, List, Mapping, Optional, Sequence

from src.services.nfl_season_engine.calibration import (
    DIRICHLET_RUSH_CONCENTRATION,
    DIRICHLET_TARGET_CONCENTRATION,
    USAGE_OTHER_BUCKET_FLOOR,
    with_residual_share,
)
from src.services.nfl_season_engine.types import (
    GameScript,
    PlayerRole,
    PlayerUsage,
    ScriptState,
)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _dirichlet_with_other(
    rng: random.Random,
    absolute_shares: Sequence[float],
    *,
    concentration: float,
) -> List[float]:
    """Dirichlet allocation that preserves absolute means via an other bucket."""
    clipped, other = with_residual_share(absolute_shares, floor=USAGE_OTHER_BUCKET_FLOOR)
    alphas = [max(1e-3, s * concentration) for s in clipped] + [max(1e-3, other * concentration)]
    draws = [rng.gammavariate(a, 1.0) for a in alphas]
    total = sum(draws)
    if total <= 0.0:
        return list(clipped)
    # Drop the other bucket — volume allocated only to modeled players.
    return [d / total for d in draws[:-1]]


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
    plays = _clamp(script.pace_plays + rng.gauss(0.0, 3.5), 48.0, 82.0)
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
        starter_share = 0.955 if starter.depth_order <= 1 else 0.88
        qb_attempts[starter.player_key] = pass_plays * starter_share
        backups = [r for r in qbs if r.player_key != starter.player_key]
        if backups:
            residual = pass_plays * (1.0 - starter_share)
            each = residual / len(backups)
            for b in backups:
                qb_attempts[b.player_key] = each

    rush_base = [max(0.0, r.rush_share) for r in rushers]
    if not any(rush_base) and rushers:
        # Depth-order fallback as absolute-ish shares.
        rush_base = [{1: 0.55, 2: 0.25, 3: 0.12}.get(r.depth_order, 0.05) if r.position == "RB" else 0.08 for r in rushers]
    rush_fracs = _dirichlet_with_other(rng, rush_base, concentration=DIRICHLET_RUSH_CONCENTRATION)
    rush_by_key = {r.player_key: rush_plays * s for r, s in zip(rushers, rush_fracs)}

    tgt_base = [max(0.0, r.target_share) for r in receivers]
    if not any(tgt_base) and receivers:
        tgt_base = [
            {1: 0.22, 2: 0.14, 3: 0.09}.get(r.depth_order, 0.05)
            if r.position in ("WR", "TE")
            else {1: 0.10, 2: 0.06}.get(r.depth_order, 0.03)
            for r in receivers
        ]
    tgt_fracs = _dirichlet_with_other(rng, tgt_base, concentration=DIRICHLET_TARGET_CONCENTRATION)
    tgt_by_key = {r.player_key: pass_plays * s for r, s in zip(receivers, tgt_fracs)}

    # Script nudge: trailing teams push a bit more volume to WR1; leading
    # teams feed the RB1 a few extra carries.
    if team_script == "trail":
        wr1 = next((r for r in receivers if r.position == "WR" and r.depth_order == 1), None)
        if wr1 is not None:
            tgt_by_key[wr1.player_key] = tgt_by_key.get(wr1.player_key, 0.0) + 0.9
    elif team_script == "lead":
        rb1 = next((r for r in rushers if r.position == "RB" and r.depth_order == 1), None)
        if rb1 is not None:
            rush_by_key[rb1.player_key] = rush_by_key.get(rb1.player_key, 0.0) + 1.2

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
