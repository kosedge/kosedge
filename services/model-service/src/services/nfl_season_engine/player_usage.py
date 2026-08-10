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
from dataclasses import replace
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from src.services.nfl_season_engine.calibration import (
    ATTEMPT_SHARE_OF_PASS_PLAYS,
    DIRICHLET_RUSH_CONCENTRATION,
    DIRICHLET_TARGET_CONCENTRATION,
    PRIOR_USAGE_ANCHOR_WEIGHT,
    PRIOR_USAGE_MIN_RUSH_ATTEMPTS,
    PRIOR_USAGE_MIN_TARGETS,
    PRIOR_USAGE_NAMED_SHARE_CAP,
    QB1_START_RATE,
    USAGE_OTHER_BUCKET_FLOOR,
    dirichlet_concentration_for_week,
    with_residual_share,
)
from src.services.nfl_season_engine.types import (
    GameScript,
    PlayerRole,
    PlayerUsage,
    ScriptState,
)
from src.services.nfl_season_engine.red_zone import allocate_team_red_zone
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
    include_red_zone: bool = True,
) -> List[PlayerUsage]:
    """Allocate one-team usage for a single game replicate.

    When ``include_red_zone`` is True (default), attach v1.7 RZ / scoring
    opportunity counts after general volume allocation.
    """
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

    # v1.16: prefer per-team pace_plays so volume differs by club identity.
    if side == "home":
        base_plays = float(getattr(script, "home_pace_plays", 0.0) or 0.0) or float(
            script.pace_plays
        )
    else:
        base_plays = float(getattr(script, "away_pace_plays", 0.0) or 0.0) or float(
            script.pace_plays
        )
    plays = _clamp(base_plays + rng.gauss(0.0, 3.5), 48.0, 82.0)
    pass_plays = plays * pass_rate
    rush_plays = plays * (1.0 - pass_rate)
    # Sacks / aborted plays: attempts < pass plays.
    pass_attempts_pool = pass_plays * ATTEMPT_SHARE_OF_PASS_PLAYS

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

    # QB starter draw — prefer healthy QB1 heavily. Real depth charts list
    # QB2/QB3 with emergency snap priors; a flat categorical over-starts them.
    qb_attempts: Dict[str, float] = {r.player_key: 0.0 for r in qbs}
    if qbs:
        qb1_pool = [r for r in qbs if int(r.depth_order or 99) <= 1]
        if qb1_pool and rng.random() < QB1_START_RATE:
            # Highest snap among depth-1 rows (usually one).
            starter = max(
                qb1_pool,
                key=lambda r: float(eff_by_key[r.player_key]["snap_share"] or 0.0),
            )
        else:
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
        qb_attempts[starter.player_key] = pass_attempts_pool * starter_share
        backups = [r for r in qbs if r.player_key != starter.player_key]
        if backups:
            residual = pass_attempts_pool * (1.0 - starter_share)
            each = residual / len(backups)
            for b in backups:
                qb_attempts[b.player_key] = each

    week = int(getattr(script, "week", 0) or 0)
    rush_conc, target_conc = dirichlet_concentration_for_week(
        week,
        base_rush=DIRICHLET_RUSH_CONCENTRATION,
        base_target=DIRICHLET_TARGET_CONCENTRATION,
    )

    rush_base = [max(0.0, float(eff_by_key[r.player_key]["rush_share"])) for r in rushers]
    if not any(rush_base) and rushers:
        rush_base = [
            {"RB1": 0.55, "RB2": 0.25, "RB_COMMITTEE": 0.36}.get(r.usage_role, 0.08)
            for r in rushers
        ]
    rush_fracs = _dirichlet_with_other(rng, rush_base, concentration=rush_conc)
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
    tgt_fracs = _dirichlet_with_other(rng, tgt_base, concentration=target_conc)
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
    if include_red_zone:
        out, _rz_diag = allocate_team_red_zone(
            team=team,
            roles=roles,
            usage_rows=out,
            script=script,
            side=side,
            rng=rng,
        )
    return out


def allocate_game_usage(
    script: GameScript,
    rosters: Mapping[str, Sequence[PlayerRole]],
    *,
    rng: Optional[random.Random] = None,
    include_red_zone: bool = True,
) -> List[PlayerUsage]:
    """Allocate usage for both teams in one game.

    RZ / scoring opportunities are attached inside each team's
    ``allocate_team_usage`` call when ``include_red_zone`` is True.
    """
    rng = rng or random.Random()
    home_roles = list(rosters.get(script.home_team, []))
    away_roles = list(rosters.get(script.away_team, []))
    home = allocate_team_usage(
        team=script.home_team,
        roles=home_roles,
        script=script,
        side="home",
        rng=rng,
        include_red_zone=include_red_zone,
    )
    away = allocate_team_usage(
        team=script.away_team,
        roles=away_roles,
        script=script,
        side="away",
        rng=rng,
        include_red_zone=include_red_zone,
    )
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


def _clamp_share(value: float, high: float = 0.45) -> float:
    return max(0.0, min(high, float(value)))


def anchor_roles_to_prior_usage_shares(
    roles: Sequence[PlayerRole],
    prior_by_player_id: Mapping[str, Mapping[str, float]],
    *,
    weight: float = PRIOR_USAGE_ANCHOR_WEIGHT,
    min_targets: float = PRIOR_USAGE_MIN_TARGETS,
    min_rush_attempts: float = PRIOR_USAGE_MIN_RUSH_ATTEMPTS,
    named_share_cap: float = PRIOR_USAGE_NAMED_SHARE_CAP,
) -> Tuple[List[PlayerRole], Dict[str, Any]]:
    """Blend depth archetype shares toward Y−1 team volume shares.

    Returning players with material prior targets / rush attempts pull
    ``target_share`` / ``rush_share`` toward their prior-season share of
    *team* targets / rush attempts. Rookies / unmatched / thin priors keep
    depth-order archetypes. Does **not** touch final season yards.
    """
    w = _clamp(float(weight), 0.0, 1.0)
    out: List[PlayerRole] = []
    anchored_tgt = 0
    anchored_rush = 0
    skipped_no_history = 0
    for role in roles:
        pid = str(getattr(role, "player_id", "") or "").strip()
        prior = prior_by_player_id.get(pid) if pid else None
        if not prior:
            skipped_no_history += 1
            out.append(role)
            continue
        pos = (role.position or "").upper()
        new_tgt = float(role.target_share or 0.0)
        new_rush = float(role.rush_share or 0.0)
        notes = []
        prior_tgt_n = float(prior.get("targets") or 0.0)
        prior_rush_n = float(prior.get("rush_attempts") or 0.0)
        prior_tgt_share = float(prior.get("target_share") or 0.0)
        prior_rush_share = float(prior.get("rush_share") or 0.0)

        if pos in ("WR", "TE", "RB") and prior_tgt_n >= min_targets and prior_tgt_share > 0:
            new_tgt = (1.0 - w) * new_tgt + w * prior_tgt_share
            new_tgt = _clamp_share(new_tgt, 0.40 if pos != "RB" else 0.22)
            anchored_tgt += 1
            notes.append("prior_tgt")
        if pos in ("RB", "QB") and prior_rush_n >= min_rush_attempts and prior_rush_share > 0:
            # QBs: rush only — pass volume stays team-pool × QB1 snap.
            high = 0.85 if pos == "RB" else 0.22
            new_rush = (1.0 - w) * new_rush + w * prior_rush_share
            new_rush = _clamp_share(new_rush, high)
            anchored_rush += 1
            notes.append("prior_rush")
        if not notes:
            skipped_no_history += 1
            out.append(role)
            continue
        route = float(role.route_share or 0.0)
        if pos in ("WR", "TE") and new_tgt > 0:
            route = max(route, new_tgt * 3.8)
        elif pos == "RB" and new_tgt > 0:
            route = max(route, new_tgt * 2.4)
        out.append(
            replace(
                role,
                target_share=round(new_tgt, 5),
                rush_share=round(new_rush, 5),
                route_share=round(route, 5),
                source=f"{role.source}+prior_usage_anchor",
            )
        )

    # Soft renorm when named shares exceed residual-other room.
    def _renorm(field: str) -> None:
        nonlocal out
        total = sum(float(getattr(r, field) or 0.0) for r in out)
        if total <= named_share_cap or total <= 0:
            return
        scale = named_share_cap / total
        out = [
            replace(r, **{field: round(float(getattr(r, field) or 0.0) * scale, 5)})
            for r in out
        ]

    _renorm("target_share")
    _renorm("rush_share")
    diag = {
        "anchored_target": anchored_tgt,
        "anchored_rush": anchored_rush,
        "skipped_no_history": skipped_no_history,
        "weight": w,
        "named_share_cap": named_share_cap,
    }
    return out, diag


def anchor_roster_book_to_prior_usage_shares(
    rosters: Mapping[str, Sequence[PlayerRole]],
    prior_by_player_id: Mapping[str, Mapping[str, float]],
    **kwargs: Any,
) -> Tuple[Dict[str, List[PlayerRole]], Dict[str, Any]]:
    """Apply :func:`anchor_roles_to_prior_usage_shares` per team."""
    out: Dict[str, List[PlayerRole]] = {}
    totals = {
        "anchored_target": 0,
        "anchored_rush": 0,
        "skipped_no_history": 0,
        "teams": 0,
    }
    for team, roles in rosters.items():
        anchored, diag = anchor_roles_to_prior_usage_shares(
            roles, prior_by_player_id, **kwargs
        )
        out[team] = anchored
        totals["anchored_target"] += int(diag["anchored_target"])
        totals["anchored_rush"] += int(diag["anchored_rush"])
        totals["skipped_no_history"] += int(diag["skipped_no_history"])
        totals["teams"] += 1
    totals["weight"] = float(
        kwargs.get("weight", PRIOR_USAGE_ANCHOR_WEIGHT)
    )
    return out, totals


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
