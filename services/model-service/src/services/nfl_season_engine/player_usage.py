"""Layer 3 — Player usage (targets, carries, routes, snap share).

Consumes Layer 2 game script + roster roles. Script tilts pass/rush volume;
role shares come from depth-chart / prior-usage ``PlayerRole`` rows, annotated
with an explicit usage-role taxonomy (see ``usage_roles.py``).

REAL vs PLACEHOLDER
-------------------
- REAL roles: loaded from depth chart + usage features when DB is available.
- PLACEHOLDER roles: demo depth charts in ``loaders.build_demo_universe``.
- Script / personnel tilts are transparent tables in ``usage_roles``
  (``SCRIPT_USAGE_MATRIX``, ``PERSONNEL_MIX_TABLE``), not opaque stacks.

Calibration note
----------------
Target / rush shares are treated as **absolute** fractions of team volume.
A residual "other" bucket absorbs the remainder so sparse skill rosters do
not renormalize WR1/RB1 into unrealistic volume (foundation bug).
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Mapping, Optional, Sequence

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
from src.services.nfl_season_engine.usage_roles import (
    annotate_usage_roles,
    effective_usage_shares,
    infer_personnel_package,
    script_matrix_documentation,
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
        team_detail = script.home_script_detail
        team_intensity = script.home_script_intensity
    else:
        pass_rate = script.away_pass_rate
        team_script = script.away_script
        team_detail = script.away_script_detail
        team_intensity = script.away_script_intensity
    time_bucket = script.time_bucket

    roles = annotate_usage_roles(roles)
    personnel = infer_personnel_package(
        pass_rate,
        team_script,
        script_intensity=team_intensity,
        time_bucket=time_bucket,
    )

    # Pre-compute effective absolute shares (role table + script + personnel).
    eff_by_key: Dict[str, Dict[str, Any]] = {}
    for role in roles:
        eff_by_key[role.player_key] = effective_usage_shares(
            role,
            script=team_script,
            pass_rate=pass_rate,
            script_intensity=team_intensity,
            time_bucket=time_bucket,
            script_detail=team_detail,
        )

    # script.pace_plays is already a per-team offensive-play expectation.
    plays = _clamp(script.pace_plays + rng.gauss(0.0, 3.5), 48.0, 82.0)
    pass_plays = plays * pass_rate
    rush_plays = plays * (1.0 - pass_rate)

    qbs = [r for r in roles if r.position == "QB"]
    # Include only players with positive effective shares so injured zeros
    # (availability 0) do not re-enter via Dirichlet residual mass.
    rushers = [
        r for r in roles if float(eff_by_key[r.player_key]["rush_share"]) > 1e-9
    ]
    receivers = [
        r for r in roles if float(eff_by_key[r.player_key]["target_share"]) > 1e-9
    ]
    # Healthy depth fallback when a team has no positive rush/target priors.
    if not rushers:
        rushers = [r for r in roles if r.position in ("RB", "QB")]
    if not receivers:
        receivers = [r for r in roles if r.position in ("WR", "TE", "RB")]

    # QB starter draw (categorical) — same spirit as box-score simulator.
    qb_attempts: Dict[str, float] = {r.player_key: 0.0 for r in qbs}
    if qbs:
        weights = [
            max(
                0.01,
                (1.0 / max(1, r.depth_order))
                * max(0.05, eff_by_key[r.player_key]["snap_share"] or 0.2),
            )
            for r in qbs
        ]
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
        if team_script == "lead" and (
            team_detail == "large_lead" or (time_bucket == "late" and team_intensity >= 0.6)
        ):
            # Large / late lead → slightly more backup looks.
            starter_share = min(starter_share, 0.91) if starter.depth_order <= 1 else starter_share
        elif team_script == "lead":
            starter_share = min(starter_share, 0.93) if starter.depth_order <= 1 else starter_share
        qb_attempts[starter.player_key] = pass_plays * starter_share
        backups = [r for r in qbs if r.player_key != starter.player_key]
        if backups:
            residual = pass_plays * (1.0 - starter_share)
            each = residual / len(backups)
            for b in backups:
                qb_attempts[b.player_key] = each

    rush_base = [max(0.0, float(eff_by_key[r.player_key]["rush_share"])) for r in rushers]
    if not any(rush_base) and rushers:
        rush_base = [
            {"RB1": 0.55, "RB2": 0.25, "RB_COMMITTEE": 0.36}.get(r.usage_role, 0.08)
            for r in rushers
        ]
    rush_fracs = _dirichlet_with_other(rng, rush_base, concentration=DIRICHLET_RUSH_CONCENTRATION)
    rush_by_key = {r.player_key: rush_plays * s for r, s in zip(rushers, rush_fracs)}

    tgt_base = [max(0.0, float(eff_by_key[r.player_key]["target_share"])) for r in receivers]
    if not any(tgt_base) and receivers:
        tgt_base = [
            {
                "WR1": 0.23,
                "WR2": 0.16,
                "WR3": 0.09,
                "WR_SLOT": 0.13,
                "TE1": 0.14,
                "TE2": 0.07,
                "RB1": 0.10,
                "RB2": 0.05,
                "RB_COMMITTEE": 0.07,
            }.get(r.usage_role, 0.05)
            for r in receivers
        ]
    tgt_fracs = _dirichlet_with_other(rng, tgt_base, concentration=DIRICHLET_TARGET_CONCENTRATION)
    tgt_by_key = {r.player_key: pass_plays * s for r, s in zip(receivers, tgt_fracs)}

    out: List[PlayerUsage] = []
    for role in roles:
        eff = eff_by_key[role.player_key]
        snap = float(eff["snap_share"])
        route = float(eff["route_share"])
        # Route participation scales with pass volume intensity (personnel).
        if role.position in ("WR", "TE") and pass_plays > 0:
            # Keep route as participation rate; nudge mildly with targets.
            tgt_frac = tgt_by_key.get(role.player_key, 0.0) / max(1.0, pass_plays)
            route = _clamp(max(route, tgt_frac * 1.05), 0.0, 1.0)

        out.append(
            PlayerUsage(
                player_key=role.player_key,
                player_name=role.player_name,
                team=team,
                position=role.position,
                snap_share=round(snap, 4),
                route_share=round(route, 4),
                targets=round(tgt_by_key.get(role.player_key, 0.0), 3),
                carries=round(rush_by_key.get(role.player_key, 0.0), 3),
                pass_attempts=round(qb_attempts.get(role.player_key, 0.0), 3),
                script=team_script,
                usage_role=str(eff["usage_role"]),
                personnel=personnel,
                script_detail=str(team_detail),
                script_intensity=float(team_intensity),
                time_bucket=str(time_bucket),
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


def usage_share_diagnostics(
    roles: Sequence[PlayerRole],
    *,
    script: ScriptState = "neutral",
    pass_rate: float = 0.58,
    script_intensity: float = 0.55,
    time_bucket: str = "mid",
    script_detail: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Inspectable dump of role labels + effective absolute shares."""
    annotated = annotate_usage_roles(roles)
    rows: List[Dict[str, Any]] = []
    for role in annotated:
        eff = effective_usage_shares(
            role,
            script=script,
            pass_rate=pass_rate,
            script_intensity=script_intensity,
            time_bucket=time_bucket,  # type: ignore[arg-type]
            script_detail=script_detail,  # type: ignore[arg-type]
        )
        rows.append(
            {
                "player_key": role.player_key,
                "player_name": role.player_name,
                "team": role.team,
                "position": role.position,
                "depth_order": role.depth_order,
                "usage_role": eff["usage_role"],
                "personnel": eff["personnel"],
                "script": script,
                "script_detail": eff.get("script_detail", script_detail or ""),
                "script_intensity": eff.get("script_intensity", script_intensity),
                "time_bucket": eff.get("time_bucket", time_bucket),
                "snap_share": round(float(eff["snap_share"]), 4),
                "rush_share": round(float(eff["rush_share"]), 4),
                "target_share": round(float(eff["target_share"]), 4),
                "route_share": round(float(eff["route_share"]), 4),
                "base_rush_share": round(float(role.rush_share), 4),
                "base_target_share": round(float(role.target_share), 4),
            }
        )
    return rows


def share_integrity_summary(
    roles: Sequence[PlayerRole],
    *,
    script: ScriptState = "neutral",
    pass_rate: float = 0.58,
    script_intensity: float = 0.55,
    time_bucket: str = "mid",
    script_detail: Optional[str] = None,
) -> Dict[str, Any]:
    """Named absolute share totals + residual other (should stay ≤ ~1.0)."""
    rows = usage_share_diagnostics(
        roles,
        script=script,
        pass_rate=pass_rate,
        script_intensity=script_intensity,
        time_bucket=time_bucket,
        script_detail=script_detail,
    )
    rush = sum(float(r["rush_share"]) for r in rows)
    tgt = sum(float(r["target_share"]) for r in rows)
    _, rush_other = with_residual_share(
        [float(r["rush_share"]) for r in rows], floor=USAGE_OTHER_BUCKET_FLOOR
    )
    _, tgt_other = with_residual_share(
        [float(r["target_share"]) for r in rows], floor=USAGE_OTHER_BUCKET_FLOOR
    )
    clipped_rush, _ = with_residual_share(
        [float(r["rush_share"]) for r in rows], floor=USAGE_OTHER_BUCKET_FLOOR
    )
    clipped_tgt, _ = with_residual_share(
        [float(r["target_share"]) for r in rows], floor=USAGE_OTHER_BUCKET_FLOOR
    )
    return {
        "script": script,
        "script_detail": script_detail or "",
        "script_intensity": script_intensity,
        "time_bucket": time_bucket,
        "pass_rate": pass_rate,
        "named_rush_share_sum": round(rush, 4),
        "named_target_share_sum": round(tgt, 4),
        "residual_other_rush": round(rush_other, 4),
        "residual_other_target": round(tgt_other, 4),
        "modeled_rush_plus_other": round(sum(clipped_rush) + rush_other, 4),
        "modeled_target_plus_other": round(sum(clipped_tgt) + tgt_other, 4),
        "ok": (
            rush_other >= 0.0
            and tgt_other >= 0.0
            and rush >= 0.0
            and tgt >= 0.0
            and abs((sum(clipped_rush) + rush_other) - 1.0) < 1e-6
            and abs((sum(clipped_tgt) + tgt_other) - 1.0) < 1e-6
        ),
    }


def usage_rules_documentation() -> Dict[str, Any]:
    """Expose role / script / personnel tables for /status and ops dumps."""
    return script_matrix_documentation()
