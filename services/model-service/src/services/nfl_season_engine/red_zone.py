"""Red-zone / scoring-usage layer (between Layer 3 usage and Layer 4 TDs).

Explicit, inspectable opportunity counts:

- Inside-20 / inside-10 **carries**
- Inside-20 / inside-10 **targets** and **routes**
- Script-conditioned **RZ pass rate** (lead → more RZ run / RB GL;
  trail → more RZ pass / WR·TE targets)

Touchdown means in ``production`` primarily flow from these opportunity
counts × role finish rates — not from opaque TD multipliers on total
yards. General usage still drives yards; a small non-RZ residual keeps
long/explosive TDs from vanishing entirely.

Injury: players with zeroed general rush/target (availability 0) receive
zero RZ opportunities; remaining shares renormalize via the same residual
"other" pattern as Layer 3. Role tables elevate RB1 inside-10 vs committee
splits; optional ``RB_GL`` when a back's loaded ``red_zone_share`` clearly
exceeds general rush share.
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from src.services.nfl_season_engine.calibration import USAGE_OTHER_BUCKET_FLOOR, with_residual_share
from src.services.nfl_season_engine.coaching_tendencies import (
    CoachingProfile,
    profile_for_team,
)
from src.services.nfl_season_engine.types import (
    GameScript,
    PlayerRole,
    PlayerUsage,
    ScriptDetail,
    ScriptState,
    TimeBucket,
)
from src.services.nfl_season_engine.usage_roles import annotate_usage_roles

# ---------------------------------------------------------------------------
# Team RZ volume priors (per-team offensive plays)
# ~12% of snaps occur inside the 20; ~35% of those are inside the 10.
# ---------------------------------------------------------------------------
RZ_PLAY_FRACTION_OF_TEAM_PLAYS = 0.145
I10_FRACTION_OF_RZ_PLAYS = 0.36
# Neutral RZ pass rate is slightly below league overall (more run near GL).
RZ_BASE_PASS_RATE = 0.52

# ---------------------------------------------------------------------------
# Role shares — absolute fractions of team RZ rush / pass volume.
# Named cores + residual other ≈ 1.0 (same spirit as Layer 3).
# ---------------------------------------------------------------------------
# Inside-20 carry shares (of team RZ rushes).
RZ_CARRY_SHARE_I20: Dict[str, float] = {
    "RB1": 0.56,
    "RB2": 0.22,
    "RB_COMMITTEE": 0.36,
    "RB_GL": 0.42,
    "QB1": 0.10,
    "QB2": 0.01,
    "WR1": 0.02,
    "OTHER": 0.04,
}

# Inside-10 / goal-line carries — more concentrated on feature / GL.
RZ_CARRY_SHARE_I10: Dict[str, float] = {
    "RB1": 0.66,
    "RB2": 0.14,
    "RB_COMMITTEE": 0.32,
    "RB_GL": 0.52,
    "QB1": 0.14,
    "QB2": 0.01,
    "WR1": 0.01,
    "OTHER": 0.03,
}

# Inside-20 target shares (of team RZ passes).
RZ_TARGET_SHARE_I20: Dict[str, float] = {
    "WR1": 0.24,
    "WR2": 0.15,
    "WR3": 0.08,
    "WR_SLOT": 0.13,
    "TE1": 0.16,
    "TE2": 0.07,
    "RB1": 0.09,
    "RB2": 0.04,
    "RB_COMMITTEE": 0.06,
    "RB_GL": 0.03,
    "OTHER": 0.05,
}

# Inside-10 targets — TE1 / WR1 elevated; WR3 faded.
RZ_TARGET_SHARE_I10: Dict[str, float] = {
    "WR1": 0.26,
    "WR2": 0.13,
    "WR3": 0.05,
    "WR_SLOT": 0.11,
    "TE1": 0.22,
    "TE2": 0.06,
    "RB1": 0.08,
    "RB2": 0.03,
    "RB_COMMITTEE": 0.05,
    "RB_GL": 0.04,
    "OTHER": 0.04,
}

# Route participation inside RZ (participation rate on RZ pass plays).
RZ_ROUTE_SHARE_I20: Dict[str, float] = {
    "WR1": 0.92,
    "WR2": 0.80,
    "WR3": 0.48,
    "WR_SLOT": 0.74,
    "TE1": 0.78,
    "TE2": 0.42,
    "RB1": 0.28,
    "RB2": 0.16,
    "RB_COMMITTEE": 0.22,
    "RB_GL": 0.12,
    "OTHER": 0.15,
}

RZ_ROUTE_SHARE_I10: Dict[str, float] = {
    "WR1": 0.90,
    "WR2": 0.72,
    "WR3": 0.38,
    "WR_SLOT": 0.68,
    "TE1": 0.86,
    "TE2": 0.40,
    "RB1": 0.22,
    "RB2": 0.12,
    "RB_COMMITTEE": 0.16,
    "RB_GL": 0.10,
    "OTHER": 0.12,
}

# Finish rates: P(TD | opportunity). Primary TD path in production.
# cal-v2: slight pass-TD lift (elite QB season TDs were light); mild rec-i10
# fade so TE1/WR1 RZ TDs stay in recent positional bands.
RZ_FINISH_RUSH_I20 = 0.12  # carry inside 20 but outside 10
RZ_FINISH_RUSH_I10 = 0.37
RZ_FINISH_REC_I20 = 0.19  # per RZ target (catch embedded)
RZ_FINISH_REC_I10 = 0.32
RZ_FINISH_PASS_I20 = 0.20  # QB pass TD per RZ pass attempt (team-level cross-check)
RZ_FINISH_PASS_I10 = 0.35

# Small non-RZ residual so explosive TDs are not zeroed (fraction of old rate).
NON_RZ_TD_RESIDUAL = 0.17

# Script deltas on RZ pass rate (stronger than overall play-mix near GL).
_RZ_PASS_DETAIL_DELTA: Dict[ScriptDetail, float] = {
    "large_lead": -0.16,
    "small_lead": -0.08,
    "neutral": 0.0,
    "small_deficit": 0.09,
    "large_deficit": 0.16,
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def maybe_assign_rb_gl(role: PlayerRole, teammates: Sequence[PlayerRole]) -> Optional[str]:
    """Return ``RB_GL`` when a back is clearly a goal-line specialist.

    Clean heuristic only: RB depth ≥ 2 (or committee depth ≥ 3) whose loaded
    ``red_zone_share`` substantially exceeds general ``rush_share``. Feature
    RB1 is never relabeled — they already own elevated I10 shares.
    """
    pos = (role.position or "").upper()
    if pos != "RB":
        return None
    depth = max(1, int(role.depth_order or 1))
    if depth <= 1:
        return None
    rush = max(0.0, float(role.rush_share))
    rz = max(0.0, float(role.red_zone_share))
    if rz < 0.12:
        return None
    # Specialist: RZ share clearly ahead of general rush (or high RZ with low rush).
    if rush <= 0.18 and rz >= 0.16:
        return "RB_GL"
    if rush > 0.0 and rz >= rush * 1.45 and rz >= 0.14:
        return "RB_GL"
    # Avoid relabeling a true committee co-back with balanced usage.
    same = [r for r in teammates if (r.position or "").upper() == "RB"]
    if len(same) >= 2 and rush >= 0.28:
        return None
    return None


def scoring_usage_role(role: PlayerRole, teammates: Sequence[PlayerRole]) -> str:
    """Role label for RZ tables — prefers RB_GL when heuristic fires."""
    gl = maybe_assign_rb_gl(role, teammates)
    if gl:
        return gl
    return role.usage_role or "OTHER"


def rz_pass_rate_from_script(
    *,
    base_team_pass_rate: float,
    detail: ScriptDetail,
    intensity: float,
    time_bucket: TimeBucket,
    coaching: Optional[CoachingProfile] = None,
    team: Optional[str] = None,
) -> float:
    """Script-conditioned red-zone pass rate (inspectable).

    Leading → more RZ run / RB GL carries; trailing → more RZ pass / WR·TE.
    Starts from a RZ-specific base blended with team pass rate, then applies
    score/time deltas (stronger near the goal line than overall play-mix).
    v1.8: optional coaching ``rz_pass_bias`` overlay (modest ±0.04).
    """
    profile = coaching or (profile_for_team(team) if team else None)
    rz_bias = float(profile.rz_pass_bias) if profile is not None else 0.0
    blend = 0.55 * RZ_BASE_PASS_RATE + 0.45 * _clamp(base_team_pass_rate, 0.32, 0.82)
    late = {"early": 0.45, "mid": 0.80, "late": 1.0}[time_bucket]
    inten = _clamp(float(intensity), 0.0, 1.0)
    delta = _RZ_PASS_DETAIL_DELTA.get(detail, 0.0)
    scale = (0.40 + 1.10 * inten) * late
    if detail == "neutral":
        scale = 0.0
    pass_rate = blend + delta * _clamp(scale, 0.0, 1.85) + rz_bias
    return round(_clamp(pass_rate, 0.28, 0.78), 4)


def estimate_team_rz_volume(
    *,
    team_plays: float,
    rng: Optional[random.Random] = None,
) -> Dict[str, float]:
    """Expected RZ / I10 play counts for one team offense."""
    rng = rng or random.Random()
    plays = _clamp(float(team_plays), 40.0, 90.0)
    rz_plays = plays * RZ_PLAY_FRACTION_OF_TEAM_PLAYS
    rz_plays = max(0.5, rng.gauss(rz_plays, 0.85))
    i10_plays = rz_plays * I10_FRACTION_OF_RZ_PLAYS
    return {
        "rz_plays": round(rz_plays, 3),
        "i10_plays": round(max(0.2, i10_plays), 3),
        "i20_outside_i10_plays": round(max(0.0, rz_plays - i10_plays), 3),
    }


def _absolute_share_for_role(
    label: str,
    table: Mapping[str, float],
) -> float:
    return float(table.get(label, table.get("OTHER", 0.04)))


def _dirichlet_alloc(
    rng: random.Random,
    absolute_shares: Sequence[float],
    *,
    concentration: float = 28.0,
) -> List[float]:
    clipped, other = with_residual_share(absolute_shares, floor=USAGE_OTHER_BUCKET_FLOOR)
    alphas = [max(1e-3, s * concentration) for s in clipped] + [max(1e-3, other * concentration)]
    draws = [rng.gammavariate(a, 1.0) for a in alphas]
    total = sum(draws)
    if total <= 0.0:
        return list(clipped)
    return [d / total for d in draws[:-1]]


def _eligible_for_rz_rush(role: PlayerRole, general_carries: float) -> bool:
    # Injured-out: rush_share and carries both zeroed.
    if float(role.rush_share) <= 1e-9 and general_carries <= 1e-9:
        # QBs may still sneak GL carries if snap > 0.
        if (role.position or "").upper() == "QB" and float(role.snap_share) > 0.05:
            return True
        return False
    return True


def _eligible_for_rz_target(role: PlayerRole, general_targets: float) -> bool:
    if float(role.target_share) <= 1e-9 and general_targets <= 1e-9:
        return False
    return (role.position or "").upper() in ("WR", "TE", "RB")


def allocate_team_red_zone(
    *,
    team: str,
    roles: Sequence[PlayerRole],
    usage_rows: Sequence[PlayerUsage],
    script: GameScript,
    side: str,
    rng: Optional[random.Random] = None,
) -> Tuple[List[PlayerUsage], Dict[str, Any]]:
    """Attach RZ opportunity counts onto usage rows; return rows + team diag."""
    rng = rng or random.Random()
    roles = annotate_usage_roles(roles)
    usage_by_key = {u.player_key: u for u in usage_rows}

    if side == "home":
        team_script: ScriptState = script.home_script
        detail: ScriptDetail = script.home_script_detail  # type: ignore[assignment]
        intensity = float(script.home_script_intensity)
        pass_rate = float(script.home_pass_rate)
    else:
        team_script = script.away_script
        detail = script.away_script_detail  # type: ignore[assignment]
        intensity = float(script.away_script_intensity)
        pass_rate = float(script.away_pass_rate)
    time_bucket: TimeBucket = script.time_bucket  # type: ignore[assignment]

    # Team offensive plays ≈ pace_plays (per-team expectation in this engine).
    team_plays = _clamp(float(script.pace_plays) + rng.gauss(0.0, 2.5), 48.0, 82.0)
    vol = estimate_team_rz_volume(team_plays=team_plays, rng=rng)
    coach = profile_for_team(team)
    rz_pass = rz_pass_rate_from_script(
        base_team_pass_rate=pass_rate,
        detail=detail,
        intensity=intensity,
        time_bucket=time_bucket,
        coaching=coach,
    )
    rz_run = 1.0 - rz_pass

    rz_pass_plays = vol["rz_plays"] * rz_pass
    rz_rush_plays = vol["rz_plays"] * rz_run
    i10_pass = vol["i10_plays"] * rz_pass
    i10_rush = vol["i10_plays"] * rz_run
    # I20 outside I10
    i20o_pass = max(0.0, rz_pass_plays - i10_pass)
    i20o_rush = max(0.0, rz_rush_plays - i10_rush)

    labels: Dict[str, str] = {
        r.player_key: scoring_usage_role(r, roles) for r in roles
    }

    rushers = [
        r
        for r in roles
        if _eligible_for_rz_rush(r, float(usage_by_key.get(r.player_key).carries if usage_by_key.get(r.player_key) else 0.0))
        and (
            _absolute_share_for_role(labels[r.player_key], RZ_CARRY_SHARE_I20) > 1e-9
            or (r.position or "").upper() in ("RB", "QB")
        )
    ]
    receivers = [
        r
        for r in roles
        if _eligible_for_rz_target(
            r,
            float(usage_by_key.get(r.player_key).targets if usage_by_key.get(r.player_key) else 0.0),
        )
        and _absolute_share_for_role(labels[r.player_key], RZ_TARGET_SHARE_I20) > 1e-9
    ]
    if not rushers:
        rushers = [r for r in roles if (r.position or "").upper() in ("RB", "QB") and float(r.snap_share) > 0]
    if not receivers:
        receivers = [
            r
            for r in roles
            if (r.position or "").upper() in ("WR", "TE", "RB") and float(r.target_share) > 0
        ]

    rush_base_i20 = [_absolute_share_for_role(labels[r.player_key], RZ_CARRY_SHARE_I20) for r in rushers]
    rush_base_i10 = [_absolute_share_for_role(labels[r.player_key], RZ_CARRY_SHARE_I10) for r in rushers]
    # Blend loaded red_zone_share as a mild prior tilt (does not replace tables).
    for i, r in enumerate(rushers):
        prior = max(0.0, float(r.red_zone_share))
        if prior > 0:
            rush_base_i20[i] = 0.75 * rush_base_i20[i] + 0.25 * prior
            rush_base_i10[i] = 0.70 * rush_base_i10[i] + 0.30 * prior

    tgt_base_i20 = [_absolute_share_for_role(labels[r.player_key], RZ_TARGET_SHARE_I20) for r in receivers]
    tgt_base_i10 = [_absolute_share_for_role(labels[r.player_key], RZ_TARGET_SHARE_I10) for r in receivers]
    for i, r in enumerate(receivers):
        prior = max(0.0, float(r.red_zone_share))
        if prior > 0 and (r.position or "").upper() in ("WR", "TE", "RB"):
            tgt_base_i20[i] = 0.80 * tgt_base_i20[i] + 0.20 * prior
            tgt_base_i10[i] = 0.75 * tgt_base_i10[i] + 0.25 * prior

    rush_frac_i20 = _dirichlet_alloc(rng, rush_base_i20) if rushers else []
    rush_frac_i10 = _dirichlet_alloc(rng, rush_base_i10) if rushers else []
    tgt_frac_i20 = _dirichlet_alloc(rng, tgt_base_i20) if receivers else []
    tgt_frac_i10 = _dirichlet_alloc(rng, tgt_base_i10) if receivers else []

    carries_i20: Dict[str, float] = {}
    carries_i10: Dict[str, float] = {}
    for r, f20, f10 in zip(rushers, rush_frac_i20, rush_frac_i10):
        # Total I20 carries = I10 + outside; store total I20 and I10 separately.
        c10 = i10_rush * f10
        c20o = i20o_rush * f20
        carries_i10[r.player_key] = c10
        carries_i20[r.player_key] = c10 + c20o

    targets_i20: Dict[str, float] = {}
    targets_i10: Dict[str, float] = {}
    for r, f20, f10 in zip(receivers, tgt_frac_i20, tgt_frac_i10):
        t10 = i10_pass * f10
        t20o = i20o_pass * f20
        targets_i10[r.player_key] = t10
        targets_i20[r.player_key] = t10 + t20o

    # TD opportunity shares (inspectable): weight I10 heavier than I20-outside.
    opp_weight: Dict[str, float] = {}
    for r in roles:
        key = r.player_key
        w = (
            carries_i10.get(key, 0.0) * 1.35
            + max(0.0, carries_i20.get(key, 0.0) - carries_i10.get(key, 0.0)) * 0.55
            + targets_i10.get(key, 0.0) * 1.25
            + max(0.0, targets_i20.get(key, 0.0) - targets_i10.get(key, 0.0)) * 0.50
        )
        opp_weight[key] = w
    opp_total = sum(opp_weight.values()) or 1.0

    out: List[PlayerUsage] = []
    player_diag: List[Dict[str, Any]] = []
    for u in usage_rows:
        role = next((r for r in roles if r.player_key == u.player_key), None)
        label = labels.get(u.player_key, u.usage_role or "OTHER")
        c20 = carries_i20.get(u.player_key, 0.0)
        c10 = carries_i10.get(u.player_key, 0.0)
        t20 = targets_i20.get(u.player_key, 0.0)
        t10 = targets_i10.get(u.player_key, 0.0)
        route_i20 = _absolute_share_for_role(label, RZ_ROUTE_SHARE_I20)
        route_i10 = _absolute_share_for_role(label, RZ_ROUTE_SHARE_I10)
        # Zero routes when player has no RZ targets and is not a route runner.
        if t20 <= 1e-9 and (u.position or "").upper() not in ("WR", "TE"):
            route_i20 = 0.0
            route_i10 = 0.0
        td_share = opp_weight.get(u.player_key, 0.0) / opp_total
        # Injured fully out → hard zero RZ (belt + suspenders).
        if role is not None:
            if (role.position or "").upper() == "RB" and float(role.rush_share) <= 1e-9 and u.carries <= 1e-9:
                c20 = c10 = 0.0
            if float(role.target_share) <= 1e-9 and u.targets <= 1e-9 and (role.position or "").upper() != "QB":
                t20 = t10 = 0.0
                route_i20 = route_i10 = 0.0
            if float(role.snap_share) <= 1e-9 and float(role.rush_share) <= 1e-9 and float(role.target_share) <= 1e-9:
                c20 = c10 = t20 = t10 = 0.0
                route_i20 = route_i10 = 0.0
                td_share = 0.0

        updated = PlayerUsage(
            player_key=u.player_key,
            player_name=u.player_name,
            team=u.team,
            position=u.position,
            snap_share=u.snap_share,
            route_share=u.route_share,
            targets=u.targets,
            carries=u.carries,
            pass_attempts=u.pass_attempts,
            script=u.script,
            usage_role=u.usage_role,
            personnel=u.personnel,
            script_detail=u.script_detail,
            script_intensity=u.script_intensity,
            time_bucket=u.time_bucket,
            rz_carries_i20=round(c20, 3),
            rz_carries_i10=round(c10, 3),
            rz_targets_i20=round(t20, 3),
            rz_targets_i10=round(t10, 3),
            rz_routes_i20=round(route_i20, 4),
            rz_routes_i10=round(route_i10, 4),
            td_opportunity_share=round(td_share, 4),
            scoring_role=label,
        )
        out.append(updated)
        player_diag.append(
            {
                "player_key": u.player_key,
                "player_name": u.player_name,
                "team": team,
                "position": u.position,
                "usage_role": u.usage_role,
                "scoring_role": label,
                "rz_carries_i20": updated.rz_carries_i20,
                "rz_carries_i10": updated.rz_carries_i10,
                "rz_targets_i20": updated.rz_targets_i20,
                "rz_targets_i10": updated.rz_targets_i10,
                "rz_routes_i20": updated.rz_routes_i20,
                "rz_routes_i10": updated.rz_routes_i10,
                "td_opportunity_share": updated.td_opportunity_share,
            }
        )

    team_diag: Dict[str, Any] = {
        "team": team,
        "script": team_script,
        "script_detail": detail,
        "script_intensity": round(intensity, 4),
        "time_bucket": time_bucket,
        "team_plays": round(team_plays, 2),
        "rz_plays": vol["rz_plays"],
        "i10_plays": vol["i10_plays"],
        "rz_pass_rate": rz_pass,
        "rz_run_rate": round(rz_run, 4),
        "rz_pass_plays": round(rz_pass_plays, 3),
        "rz_rush_plays": round(rz_rush_plays, 3),
        "i10_pass_plays": round(i10_pass, 3),
        "i10_rush_plays": round(i10_rush, 3),
        "coaching_profile": coach.to_dict(),
        "tendency_effects": {
            "rz_pass_bias_applied": coach.rz_pass_bias,
            "rz_pass_rate_after": rz_pass,
        },
        "players": player_diag,
    }
    return out, team_diag


def allocate_game_red_zone(
    script: GameScript,
    rosters: Mapping[str, Sequence[PlayerRole]],
    usage_rows: Sequence[PlayerUsage],
    *,
    rng: Optional[random.Random] = None,
) -> Tuple[List[PlayerUsage], Dict[str, Any]]:
    """Apply RZ allocation to both teams; return updated usage + diagnostics."""
    rng = rng or random.Random()
    home_u = [u for u in usage_rows if u.team == script.home_team]
    away_u = [u for u in usage_rows if u.team == script.away_team]
    home_roles = list(rosters.get(script.home_team, []))
    away_roles = list(rosters.get(script.away_team, []))
    home_out, home_diag = allocate_team_red_zone(
        team=script.home_team,
        roles=home_roles,
        usage_rows=home_u,
        script=script,
        side="home",
        rng=rng,
    )
    away_out, away_diag = allocate_team_red_zone(
        team=script.away_team,
        roles=away_roles,
        usage_rows=away_u,
        script=script,
        side="away",
        rng=rng,
    )
    return home_out + away_out, {"home": home_diag, "away": away_diag}


def red_zone_share_tables() -> Dict[str, Any]:
    """Serialize RZ tables for /status and ops dumps."""
    return {
        "rz_play_fraction_of_team_plays": RZ_PLAY_FRACTION_OF_TEAM_PLAYS,
        "i10_fraction_of_rz_plays": I10_FRACTION_OF_RZ_PLAYS,
        "rz_base_pass_rate": RZ_BASE_PASS_RATE,
        "carry_share_i20": RZ_CARRY_SHARE_I20,
        "carry_share_i10": RZ_CARRY_SHARE_I10,
        "target_share_i20": RZ_TARGET_SHARE_I20,
        "target_share_i10": RZ_TARGET_SHARE_I10,
        "route_share_i20": RZ_ROUTE_SHARE_I20,
        "route_share_i10": RZ_ROUTE_SHARE_I10,
        "finish_rates": {
            "rush_i20": RZ_FINISH_RUSH_I20,
            "rush_i10": RZ_FINISH_RUSH_I10,
            "rec_i20": RZ_FINISH_REC_I20,
            "rec_i10": RZ_FINISH_REC_I10,
            "pass_i20": RZ_FINISH_PASS_I20,
            "pass_i10": RZ_FINISH_PASS_I10,
        },
        "non_rz_td_residual": NON_RZ_TD_RESIDUAL,
        "rz_pass_detail_delta": dict(_RZ_PASS_DETAIL_DELTA),
        "script_interaction": (
            "Leading → lower RZ pass rate / more RB I10 carries; "
            "trailing → higher RZ pass rate / more WR1·TE1 I10 targets. "
            "Intensity × time-bucket scaling mirrors v1.6 usage matrix. "
            "v1.8: coaching rz_pass_bias overlays the scripted RZ pass rate."
        ),
        "td_path": (
            "Layer 4 TD means = RZ opportunities × finish rates "
            f"+ {NON_RZ_TD_RESIDUAL:.0%} residual of legacy usage×rate "
            "(yards still from general usage; no double-count of RZ volume into yards)."
        ),
        "rb_gl": (
            "Optional RB_GL when depth≥2 RB has red_zone_share ≫ rush_share; "
            "feature RB1 keeps RB1 label with elevated I10 table shares."
        ),
    }


def scoring_usage_diagnostics(
    roles: Sequence[PlayerRole],
    *,
    script: ScriptState = "neutral",
    script_detail: ScriptDetail = "neutral",
    script_intensity: float = 0.55,
    time_bucket: TimeBucket = "mid",
    pass_rate: float = 0.58,
    team: Optional[str] = None,
) -> Dict[str, Any]:
    """Static (no MC) inspectable RZ share dump for a roster."""
    roles = annotate_usage_roles(roles)
    team_key = team or (roles[0].team if roles else None)
    rz_pass = rz_pass_rate_from_script(
        base_team_pass_rate=pass_rate,
        detail=script_detail,
        intensity=script_intensity,
        time_bucket=time_bucket,
        team=team_key,
    )
    rows = []
    for role in roles:
        label = scoring_usage_role(role, roles)
        rows.append(
            {
                "player_key": role.player_key,
                "player_name": role.player_name,
                "team": role.team,
                "position": role.position,
                "usage_role": role.usage_role,
                "scoring_role": label,
                "rz_carry_share_i20": _absolute_share_for_role(label, RZ_CARRY_SHARE_I20),
                "rz_carry_share_i10": _absolute_share_for_role(label, RZ_CARRY_SHARE_I10),
                "rz_target_share_i20": _absolute_share_for_role(label, RZ_TARGET_SHARE_I20),
                "rz_target_share_i10": _absolute_share_for_role(label, RZ_TARGET_SHARE_I10),
                "loaded_red_zone_share": round(float(role.red_zone_share), 4),
            }
        )
    return {
        "script": script,
        "script_detail": script_detail,
        "script_intensity": script_intensity,
        "time_bucket": time_bucket,
        "rz_pass_rate": rz_pass,
        "rz_run_rate": round(1.0 - rz_pass, 4),
        "players": rows,
    }
