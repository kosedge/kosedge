from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping

from .nfl_playing_time import (
    allocate_qb_role_shares,
    apply_hard_share_caps,
    rank_keys_by_depth_sot,
)
from .nfl_surface_integrity import PASS_TD_YARDS_PER, REC_TD_YARDS_PER


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _normal_cdf(x: float) -> float:
    # Deterministic normal CDF approximation via erf.
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def fair_price_from_prob(prob: float) -> int:
    p = _clamp(prob, 0.001, 0.999)
    if p >= 0.5:
        return int(round(-(100.0 * p) / (1.0 - p)))
    return int(round((100.0 * (1.0 - p)) / p))


@dataclass(frozen=True)
class PlayerFeatureInputs:
    position: str
    snap_proxy: float
    route_proxy: float
    target_proxy: float
    rush_share: float
    red_zone_share: float
    qb_dropback_factor: float
    qb_pressure_factor: float
    team_pace_factor: float
    team_pass_rate_factor: float
    availability_confidence: float
    role_confidence: float
    experience_confidence: float = 1.0
    team_snap_share: float = 0.0
    """A player's involvement_plays divided by the TEAM's total offensive
    plays that week -- a real, position-agnostic snap share (a starting QB
    lands near 0.90-1.0). Distinct from `snap_proxy`, which is a *touch*
    share (a player's plays divided by every teammate's combined plays) --
    reasonable for skill positions splitting touches with each other, but
    badly wrong for QBs, where it was crushing passing-volume projections
    (see infra/db/031_nfl_player_team_snap_share.sql). Defaults to 0.0 for
    any caller not yet passing it through; `qb_volume_signal` falls back to
    the old (broken) behavior only in that case, so wire this through."""
    opponent_pass_defense_factor: float = 1.0
    opponent_rush_defense_factor: float = 1.0
    """Opponent-adjusted matchup multipliers, >1.0 means the opponent's
    defense is worse than average against that phase of offense (so this
    player should outperform their own team-context-only baseline), <1.0
    means a tougher-than-average matchup. 1.0 (neutral) is the safe default
    for any caller not yet supplying real opponent context."""
    qb_starter_share: float = 1.0
    """Only meaningful for QB. Real bug found via a live production
    spot-check: every rostered QB on a team (not just the real starter) was
    independently clearing this function's QB-branch additive floors
    (`attempts_mean`'s unconditional `22.0 +` base, `qb_volume_signal`'s
    0.25 floor) regardless of `team_snap_share`, because a single-player
    pure function has no way to know it shares a depth chart with other
    QBs -- so a team with 4-5 rostered QBs projected a combined SEASON
    pass-attempt total of ~2,100-2,500, roughly 4-5x what one real starter
    throws in a season. `team_snap_share` alone could not fix this: even
    driven to 0, `qb_volume_signal`'s OTHER additive term
    (`qb_dropback_factor`, an efficiency/mix ratio that is similarly high
    for a starter and a backup alike) plus the attempts formula's own
    unconditional `22.0` base still guaranteed real volume to anyone tagged
    QB. This field is the caller-supplied fix: once the caller has full
    team context (which this function deliberately does not have on its
    own), it     computes each QB's real team-relative share of "who is the
    starter" via `compute_qb_starter_shares` (SoT depth role caps first;
    snaps only when depth is missing) and passes it through here. 1.0 (the
    default, and always correct for a team with only one rostered QB, or
    for any caller not yet wired for team context) means "fully
    independent, could be the starter" -- the original, unscaled behavior.
    Multiplicatively scales `attempts_mean` and `carries_mean` (and
    everything downstream of them: pass/rush yards and TDs), so a clear
    backup projects nowhere near a starter's volume, while a real starter
    (share near 1.0) is essentially unaffected."""
    qb_talent_factor: float = 1.0
    """Only meaningful for QB. Scales pass attempts / YPA toward a
    prior-production talent prior (elite starters >1.0, bridge/game-manager
    starters <1.0). Default 1.0 is neutral. Computed by the materializer from
    recent-season pass yards per startish game; never invents volume for
    backups (still gated by qb_starter_share)."""
    skill_talent_factor: float = 1.0
    """WR/TE/RB prior-production scale (elite >1.0). Default 1.0 is neutral.
    Computed from recent receiving or rushing yards per active game."""
    implied_team_total: float = 0.0
    """Market (or schedule) implied team total points for this game. When >0,
    scales pace / pass-attempt volume toward the game environment the books
    are pricing — closing the gap between usage-trailing pace and scripted
    game totals. 0.0 means unused (pure usage pace)."""
    team_spread: float = 0.0
    """Team-centric spread (negative = favorite). Dogs tilt slightly toward
    pass; favorites toward rush. 0.0 = neutral / unknown."""
    """1.0 for a normal veteran-usage-derived projection. Lower values (see
    ROOKIE_EXPERIENCE_CONFIDENCE) widen the output std without changing the
    mean -- a rookie with the same *projected* mean as a veteran genuinely
    has more outcome uncertainty, since there's no track record backing the
    number up. Sourced from nfl_player_projection_features_weekly's
    feature_payload->>'usage_source' (see PLAYER_HYDRATE/ROOKIE_BASELINE
    source tags in preseason_hydration.py)."""


ROOKIE_EXPERIENCE_CONFIDENCE = 0.45
VETERAN_EXPERIENCE_CONFIDENCE = 1.0
MAX_VARIANCE_WIDENING = 2.0


# Healthy-room QB shares live in nfl_playing_time (QB1 0.94 / QB2 0.06 /
# QB3+ ≈ 0). Residual backup volume is injury/spot-start on QB2 only.


def _allocate_winner_take_most(ranked_keys: list[str]) -> Dict[str, float]:
    """Assign QB1 / QB2 / QB3+ shares. QB3+ is ≈ 0 (playing-time layer)."""
    return allocate_qb_role_shares(ranked_keys)


# Phase 2 (2026-08-19): fresh rematerialize already overshoots RB1 (~+11 resid).
# Soften bell-cow primary slightly so RB1 does not eat unreal committee volume.
_RB_BELL_COW_PRIMARY = 0.68
_RB_BELL_COW_SECONDARY = 0.24
_RB_BELL_COW_TERTIARY = 0.08
_RB_SOFT_PRIMARY = 0.58
_RB_SOFT_SECONDARY = 0.30
_RB_SOFT_TERTIARY = 0.12
_RB_COMMITTEE_PRIMARY = 0.52
_RB_COMMITTEE_SECONDARY = 0.36
_RB_COMMITTEE_TERTIARY = 0.12

# Phase 2: keep team pass base near league (64×0.55). Do not lift — fresh
# rematerialize already overshoots QB season totals; WR 8+ is near-flat.
# Phase 3B: nudge down for season-pool coherence (cap-17 still had 7 QBs ≥4k).
TEAM_PASS_ATTEMPTS_BASE = 34.8
# Phase 3C: targets/rec share the compressed pass budget. 3B QB attempt
# soft-tail pulled elite pass means down faster than skill receiving (gap
# ~0.17). Dampen the team-attempts denom used for WR/RB/TE targets only —
# do not re-expand QB attempts / n≥4000.
TEAM_PASS_ATTEMPTS_TARGET_SCALE = 0.92


def _rb_depth_score(depth_order: float | None) -> float:
    if depth_order is None:
        return 0.18
    d = float(depth_order)
    if d <= 1.0:
        return 1.0
    if d <= 2.0:
        return 0.45
    if d <= 3.0:
        return 0.18
    return 0.06


def _allocate_rb_ranked_shares(ranked_keys: list[str], *, primary: float, secondary: float, tertiary: float) -> Dict[str, float]:
    out: Dict[str, float] = {key: 0.0 for key in ranked_keys}
    if not ranked_keys:
        return out
    if len(ranked_keys) == 1:
        out[ranked_keys[0]] = 1.0
        return out
    out[ranked_keys[0]] = float(primary)
    out[ranked_keys[1]] = float(secondary)
    if len(ranked_keys) == 2:
        out[ranked_keys[0]] = float(primary) + float(tertiary)
        return out
    residual = float(tertiary)
    others = ranked_keys[2:]
    each = residual / len(others)
    for key in others:
        out[key] = each
    return out


def _normalize_share_map(shares: Dict[str, float]) -> Dict[str, float]:
    total = sum(max(0.0, float(v or 0.0)) for v in shares.values())
    if total <= 0.0:
        n = len(shares)
        if n <= 0:
            return {}
        even = 1.0 / n
        return {k: even for k in shares}
    return {k: max(0.0, float(v or 0.0)) / total for k, v in shares.items()}


def compute_rb_rush_shares(
    trailing_rush_shares: Dict[str, float],
    *,
    depth_orders: Dict[str, float] | None = None,
    prior_carries: Dict[str, float] | None = None,
    offense_snap_pcts: Dict[str, float] | None = None,
) -> Dict[str, float]:
    """Team-scoped RB rush-share allocation (winner-take-most, usage-aware).

    Pure: one team's RB/HB/FB room → shares that sum to ~1.0.

    Ranking uses prior carries + depth + trailing rush share + offense snaps.
    Room shape adapts to usage:
      - bell cow when #1 clearly leads (≈0.68 / 0.24 / 0.08)
      - soft split when leadership is moderate (≈0.58 / 0.30 / 0.12)
      - committee when #1/#2 are close on usage (≈0.52 / 0.36 / 0.12)
    Final shares blend the ranked template with live usage so mid-season
    committees and hot hands move the board as more data arrives.
    """
    if not trailing_rush_shares:
        return {}
    if len(trailing_rush_shares) == 1:
        return {key: 1.0 for key in trailing_rush_shares}

    keys = list(trailing_rush_shares.keys())
    trailing = {k: max(0.0, float(trailing_rush_shares.get(k) or 0.0)) for k in keys}
    depths = depth_orders or {}
    priors = prior_carries or {}
    snaps = offense_snap_pcts or {}

    prior_total = sum(float(priors.get(k) or 0.0) for k in keys)
    trailing_total = sum(trailing.values())
    snap_total = sum(max(0.0, float(snaps.get(k) or 0.0)) for k in keys)
    has_prior = prior_total > 0.0
    has_depth = any(k in depths for k in keys)
    has_snaps = snap_total > 0.0

    scores: Dict[str, float] = {}
    usage_mix: Dict[str, float] = {}
    for k in keys:
        prior_share = float(priors.get(k) or 0.0) / prior_total if has_prior else 0.0
        trail_share = trailing[k] / trailing_total if trailing_total > 0.0 else 0.0
        snap_share = max(0.0, float(snaps.get(k) or 0.0)) / snap_total if has_snaps else 0.0
        depth_score = _rb_depth_score(depths.get(k) if k in depths else None)
        # Usage signal for committee detection + final blend.
        if has_prior and has_snaps:
            usage_mix[k] = (0.55 * prior_share) + (0.25 * trail_share) + (0.20 * snap_share)
        elif has_prior:
            usage_mix[k] = (0.70 * prior_share) + (0.30 * trail_share)
        elif has_snaps:
            usage_mix[k] = (0.55 * snap_share) + (0.45 * trail_share)
        else:
            usage_mix[k] = trail_share if trailing_total > 0.0 else depth_score

        if has_prior:
            scores[k] = (
                (0.45 * prior_share)
                + (0.25 * depth_score)
                + (0.15 * trail_share)
                + (0.15 * snap_share)
            )
        elif has_depth:
            scores[k] = (0.55 * depth_score) + (0.25 * trail_share) + (0.20 * snap_share)
        else:
            scores[k] = (0.60 * trail_share) + (0.40 * snap_share)

    if has_prior and prior_total > 0.0:
        ordered_priors = sorted(((float(priors.get(k) or 0.0), k) for k in keys), reverse=True)
        top_carries, top_key = ordered_priors[0]
        second_carries = ordered_priors[1][0] if len(ordered_priors) > 1 else 0.0
        # Clear workhorse seasons (~180+ carries and ≥1.35× RB2) get a boost
        # past a stale depth-chart-only edge.
        if top_carries >= 180.0 and top_carries >= (1.35 * max(second_carries, 1.0)):
            scores[top_key] = scores.get(top_key, 0.0) + 0.18

    ranked = sorted(
        keys,
        key=lambda k: (-scores[k], float(depths.get(k, 99.0) or 99.0), str(k)),
    )
    usage_ranked = sorted(keys, key=lambda k: (-usage_mix[k], str(k)))
    top_usage = float(usage_mix.get(usage_ranked[0]) or 0.0)
    second_usage = float(usage_mix.get(usage_ranked[1]) or 0.0) if len(usage_ranked) > 1 else 0.0
    lead_ratio = top_usage / max(second_usage, 1e-6)

    if lead_ratio >= 1.45 or (has_prior and top_usage >= 0.55 and lead_ratio >= 1.30):
        template = _allocate_rb_ranked_shares(
            ranked,
            primary=_RB_BELL_COW_PRIMARY,
            secondary=_RB_BELL_COW_SECONDARY,
            tertiary=_RB_BELL_COW_TERTIARY,
        )
        usage_weight = 0.18
    elif lead_ratio <= 1.20 and second_usage >= 0.22:
        template = _allocate_rb_ranked_shares(
            ranked,
            primary=_RB_COMMITTEE_PRIMARY,
            secondary=_RB_COMMITTEE_SECONDARY,
            tertiary=_RB_COMMITTEE_TERTIARY,
        )
        usage_weight = 0.48
    else:
        template = _allocate_rb_ranked_shares(
            ranked,
            primary=_RB_SOFT_PRIMARY,
            secondary=_RB_SOFT_SECONDARY,
            tertiary=_RB_SOFT_TERTIARY,
        )
        usage_weight = 0.32

    usage_norm = _normalize_share_map(usage_mix)
    blended = {
        k: ((1.0 - usage_weight) * float(template.get(k) or 0.0))
        + (usage_weight * float(usage_norm.get(k) or 0.0))
        for k in keys
    }
    committee = lead_ratio <= 1.20 and second_usage >= 0.22
    return apply_hard_share_caps(
        _normalize_share_map(blended),
        depths,
        position="RB",
        committee=committee,
    )


def compute_qb_starter_shares(
    team_snap_shares: Dict[str, float],
    *,
    depth_orders: Dict[str, float] | None = None,
    prior_attempts: Dict[str, float] | None = None,
    power: float = 1.75,
) -> Dict[str, float]:
    """Pure: {player_key: team_snap_share} for one team's QBs → starter shares.

    Playing-time doctrine (Phase 1): **depth SoT is authoritative**. Last
    year's passer who is now QB3 cannot take 0.92 of team attempts just
    because team-scoped priors still point at him (O'Connell / Cook class).

    1. Depth present → rank by depth_order, allocate QB1 0.94 / QB2 0.06 /
       QB3+ ≈ 0. Priors are ignored for ranking (injury shocks reallocate
       when the SoT starter is out).
    2. No depth, snaps exist → power-law on snap share, then hard caps.
    3. No depth, no snaps → leave everyone at 1.0 (caller should supply
       depth; inventing an order is worse).
    """
    if not team_snap_shares:
        return {}
    if len(team_snap_shares) == 1:
        return {key: 1.0 for key in team_snap_shares}

    keys = list(team_snap_shares.keys())
    snaps = {k: float(team_snap_shares.get(k) or 0.0) for k in keys}
    depths = depth_orders or {}
    has_depth = any(k in depths for k in keys)

    if has_depth:
        ranked = rank_keys_by_depth_sot(keys, depths, snaps=snaps)
        return apply_hard_share_caps(
            _allocate_winner_take_most(ranked),
            depths,
            position="QB",
        )

    # Depth missing: snaps only. Do not let prior attempts invent a QB1.
    _ = prior_attempts  # kept on the signature for callers; unused for ranking
    starter_key = max(keys, key=lambda k: snaps[k])
    starter_share = snaps[starter_key]
    if starter_share <= 0.0:
        return {key: 1.0 for key in keys}
    p = max(1.0, float(power))
    raw = {
        key: (
            1.0
            if key == starter_key
            else _clamp((snaps[key] / starter_share) ** p, 0.0, 1.0)
        )
        for key in keys
    }
    # Without depth, treat snap rank as a synthetic depth so QB3-class
    # residuals still get clipped.
    snap_depth = {
        k: float(i)
        for i, k in enumerate(
            sorted(keys, key=lambda x: (-snaps[x], str(x))),
            start=1,
        )
    }
    return apply_hard_share_caps(raw, snap_depth, position="QB")


def qb_talent_factor_from_prior_ypg(prior_yards_per_startish_game: float | None) -> float:
    """Map recent pass yards / startish game → multiplicative talent prior.

    Anchors (2023-2025 starter weeks): league startish ~230-250 ypg, elite
    leaders ~270-290, bridge/game-managers ~180-210. Returns a gentle
    scale in [0.88, 1.18] so hierarchy moves without blowing up books.
    """
    if prior_yards_per_startish_game is None:
        return 1.0
    ypg = float(prior_yards_per_startish_game)
    if ypg <= 0.0:
        return 0.94
    # Center near ~240 ypg; ±40 ypg → about ±0.10 factor before clamp.
    return _clamp(1.0 + ((ypg - 240.0) / 400.0), 0.88, 1.18)


def skill_talent_factor_from_prior_ypg(
    prior_yards_per_game: float | None, *, position: str
) -> float:
    """Map recent skill yards/game → talent prior for WR/TE/RB.

    Centers: WR ~70 rec yd/g, TE ~45, RB ~65 rush yd/g. Elites (Chase /
    Jefferson / Barkley-class) land above 1.10; committee/depth pieces below 1.0.
    """
    if prior_yards_per_game is None:
        return 1.0
    ypg = float(prior_yards_per_game)
    if ypg <= 0.0:
        return 0.94
    pos = (position or "").upper()
    if pos == "WR":
        return _clamp(1.0 + ((ypg - 70.0) / 220.0), 0.90, 1.22)
    if pos == "TE":
        return _clamp(1.0 + ((ypg - 45.0) / 180.0), 0.90, 1.20)
    if pos in {"RB", "FB", "HB"}:
        return _clamp(1.0 + ((ypg - 65.0) / 200.0), 0.90, 1.24)
    return 1.0


def depth_role_confidence_floor(position: str, depth_order: float | None) -> float | None:
    """Minimum role_confidence for designated depth-chart starters.

    Production failure: Chase-class WR1s hydrated at role_confidence ~0.28,
    which crushed targets via role_vol and again via confidence_scale —
    landing ~57 yd/g vs real ~100. Depth-1 skill players must not be treated
    as committee scraps.
    """
    if depth_order is None:
        return None
    d = int(float(depth_order))
    pos = (position or "").upper()
    if pos == "WR":
        return {1: 0.88, 2: 0.72, 3: 0.58}.get(d)
    if pos == "TE":
        return {1: 0.85, 2: 0.62}.get(d)
    if pos in {"RB", "FB", "HB"}:
        return {1: 0.88, 2: 0.70, 3: 0.55}.get(d)
    return None


def usage_rank_depth_orders(
    players: Iterable[Mapping[str, Any]],
    *,
    positions: Iterable[str],
    usage_key: str,
) -> Dict[str, Dict[str, float]]:
    """Assign depth_order 1..n within team from trailing usage when chart misses.

    Production failure (2025 W17 props board): official depth-chart joins miss
    for many WR1s (id / week gaps), so depth floors never fire and receiving
    means collapse to ~12–20 yd against 40–90 yd books — then PLAY tags the
    residual as Under. Ranking by the same usage share the feature table
    already stores (target_proxy / rush_share) restores a leakage-safe depth
    prior without inventing market-driven volume.
    """
    pos_set = {str(p or "").upper() for p in positions}
    # Rank within team × position so WR1 and TE1 can both be depth_order=1.
    buckets: Dict[tuple[str, str], list[tuple[float, str]]] = {}
    for row in players:
        pos = str(row.get("position") or "").upper()
        if pos not in pos_set:
            continue
        team = str(row.get("team") or "").strip().upper()
        pid = str(row.get("player_id") or "").strip()
        if not team or not pid:
            continue
        usage = _safe_float(row.get(usage_key), 0.0)
        buckets.setdefault((team, pos), []).append((usage, pid))

    out: Dict[str, Dict[str, float]] = {}
    for (team, _pos), items in buckets.items():
        # Stable: higher usage first; player_id tie-break.
        ordered = sorted(items, key=lambda it: (-it[0], it[1]))
        team_map = out.setdefault(team, {})
        for idx, (_usage, pid) in enumerate(ordered, start=1):
            team_map[pid] = float(idx)
    return out


def merge_depth_orders(
    primary: Mapping[str, Mapping[str, float]] | None,
    fallback: Mapping[str, Mapping[str, float]] | None,
) -> Dict[str, Dict[str, float]]:
    """Chart depth wins; usage-rank fills missing player_ids only."""
    merged: Dict[str, Dict[str, float]] = {}
    for team, cmap in (primary or {}).items():
        merged[str(team)] = {str(pid): float(depth) for pid, depth in dict(cmap).items()}
    for team, fmap in (fallback or {}).items():
        slot = merged.setdefault(str(team), {})
        for pid, depth in dict(fmap).items():
            slot.setdefault(str(pid), float(depth))
    return merged


def effective_skill_role_confidence(
    *,
    position: str,
    role_confidence: float,
    depth_order: float | None,
    rush_share: float = 0.0,
) -> float:
    """Apply the same depth / bell-cow floors used by baseline + box materializers.

    Props edge tagging historically read the compact involvement score from
    `nfl_player_projection_features_weekly` (skill p50 ≈ 0.20) and compared it
    to starter-probability thresholds (0.55), so every prop looked "low role".
    """
    role = _clamp(_safe_float(role_confidence, 0.65), 0.0, 1.0)
    pos = (position or "").upper()
    floor = depth_role_confidence_floor(pos, depth_order)
    if floor is not None:
        role = max(role, float(floor))
    if pos in {"RB", "FB", "HB"} and float(rush_share or 0.0) >= 0.55:
        role = max(role, 0.84)
    return role


def baseline_projection_from_features(inputs: PlayerFeatureInputs) -> Dict[str, Any]:
    position = (inputs.position or "").upper()
    volume_signal = _clamp(
        (0.32 * inputs.snap_proxy)
        + (0.28 * inputs.route_proxy)
        + (0.22 * inputs.target_proxy)
        + (0.18 * inputs.rush_share),
        0.01,
        0.98,
    )
    role_factor = _clamp(0.55 + (0.45 * inputs.role_confidence), 0.35, 1.0)
    availability_factor = _clamp(0.45 + (0.55 * inputs.availability_confidence), 0.35, 1.0)
    pace_factor = _clamp(inputs.team_pace_factor, 0.78, 1.22)
    pass_factor = _clamp(inputs.team_pass_rate_factor, 0.78, 1.22)
    # Game-script / market environment: implied team total scales volume;
    # spread tilts pass rate (dogs throw more, favorites run more).
    if inputs.implied_team_total and inputs.implied_team_total > 0:
        pace_factor *= _clamp(float(inputs.implied_team_total) / 22.5, 0.88, 1.15)
    if inputs.team_spread:
        # team_spread < 0 ⇒ favorite ⇒ slightly fewer passes.
        pass_factor *= _clamp(1.0 + (0.018 * _clamp(float(inputs.team_spread) / 3.5, -2.0, 2.0)), 0.92, 1.08)
    pace_factor = _clamp(pace_factor, 0.78, 1.25)
    pass_factor = _clamp(pass_factor, 0.78, 1.25)
    # Real, derived estimate of this team's real pass attempts/game --
    # pace_factor and pass_factor are both already normalized around real
    # league baselines (64 plays/game, 0.55 pass rate -- see
    # materialize_player_projection_features's SQL), so their product times
    # that same baseline recovers a real attempts-per-game number, not an
    # arbitrary constant. This is the fix for a real, foundational
    # calibration bug: target_proxy is a real target SHARE (targets divided
    # by team targets), so the mathematically correct expected value is
    # target_proxy * team's real attempts -- the old formulas instead
    # multiplied target_proxy by a small, arbitrary fixed coefficient
    # (11.5 for WR/TE, 7.0 for RB) with no connection to real team pass
    # volume, which drastically undercounted every pass-catcher's targets
    # (a real elite WR1 with a genuine ~31% target share on a real team
    # projected for only ~5 targets/game instead of a realistic ~12-13,
    # cascading into unrealistically low receptions/receiving yards for
    # the entire receiving corps league-wide -- confirmed via a live
    # production spot-check, see docs/NFL_PROPS_FANTASY_FOUNDATION.md).
    team_pass_attempts_estimate = (
        pace_factor * pass_factor * TEAM_PASS_ATTEMPTS_BASE * TEAM_PASS_ATTEMPTS_TARGET_SCALE
    )

    attempts_mean = 0.0
    carries_mean = 0.0
    targets_mean = 0.0
    pass_yards_mean = 0.0
    rush_yards_mean = 0.0
    receiving_yards_mean = 0.0
    receptions_mean = 0.0
    pass_tds_mean = 0.0
    rush_tds_mean = 0.0
    rec_tds_mean = 0.0

    if position == "QB":
        # team_snap_share (involvement / team offensive plays) ranks QBs and
        # feeds volume. Healthy starters often land ~0.35-0.55 on this metric
        # (involvement ≈ dropbacks+QB runs, not every OL snap) — that range
        # already produces ~230-270 pass yards with the attempts formula, so
        # do NOT floor mid snaps up to ~0.9 (that overshoots books by ~70 yd).
        # Only lift true cold-starts: designated starter with almost no usage
        # yet (new starter / returning from injury with empty involvement).
        raw_snap = inputs.team_snap_share if inputs.team_snap_share > 0.0 else inputs.snap_proxy
        if inputs.qb_starter_share >= 0.85 and raw_snap < 0.28:
            starter_signal = max(raw_snap, 0.72)
        else:
            starter_signal = raw_snap
        qb_volume_signal = _clamp(
            (0.55 * starter_signal) + (0.45 * _clamp(inputs.qb_dropback_factor / 1.15, 0.35, 1.35)),
            0.25,
            1.0,
        )
        opp_pass_factor = _clamp(inputs.opponent_pass_defense_factor, 0.75, 1.30)
        opp_rush_factor = _clamp(inputs.opponent_rush_defense_factor, 0.75, 1.30)
        # Opponent EPA factors can hit the ±30% clamp; applying that full
        # range to YPA pushed Prescott/Maye-class means ~40-70 yards over
        # books. Soften to ~±12% for yards-per-attempt only.
        opp_ypa_factor = _clamp(1.0 + (0.40 * (opp_pass_factor - 1.0)), 0.88, 1.12)
        qb_starter_share_factor = _clamp(inputs.qb_starter_share, 0.0, 1.0)
        talent_factor = _clamp(float(inputs.qb_talent_factor or 1.0), 0.85, 1.22)
        # Phase 2: compress attempt schedule — fresh rematerialize flipped
        # pass residual positive (~+9.5 raw vs actual) and inflated ≥4k season
        # sums. Prefer fewer attempts over YPA hacks; qb_pace damping restored.
        # Phase 3B: further upper-tail compression on attempts (not YPA / not
        # per-QB overrides) so cap-17 season sums lose the ≥4k cluster.
        qb_pace = _clamp(0.52 + (0.42 * pace_factor), 0.84, 1.10)
        attempts_mean = (18.2 + (30.8 * qb_volume_signal * pass_factor * qb_pace)) * qb_starter_share_factor
        attempts_mean *= talent_factor
        attempts_mean = min(attempts_mean, 40.2)
        if attempts_mean > 35.5:
            attempts_mean = 35.5 + (attempts_mean - 35.5) * 0.88
        # Low-scoring games compress pass volume (CLE/PIT 35.5). Dogs in
        # blowouts still throw — don't crush them by raw implied points alone.
        if inputs.implied_team_total and inputs.implied_team_total > 0:
            env_pts = float(inputs.implied_team_total)
            if inputs.team_spread and float(inputs.team_spread) > 0:
                # Dogs still throw; floor near league-average script, not blowout.
                env_pts = max(env_pts, 21.5)
            attempts_mean *= _clamp(env_pts / 22.5, 0.86, 1.14)
        if inputs.team_spread and float(inputs.team_spread) <= -7.0:
            # Heavy favorite: more likely to run clock / sit starters late.
            attempts_mean *= _clamp(1.0 + (0.015 * float(inputs.team_spread)), 0.85, 1.0)
        # Low role confidence (emergency / short-leash starters) compress volume
        # toward game-manager ranges books price (Cook/Sanders-class).
        if inputs.role_confidence < 0.70:
            attempts_mean *= _clamp(0.72 + (0.40 * inputs.role_confidence), 0.78, 1.0)
        completion_rate = _clamp(0.60 + (0.05 * inputs.target_proxy) - (0.03 * inputs.qb_pressure_factor), 0.50, 0.74)
        # YPA: pressure-adjusted intercept 6.97 (2023-2025 weighted fit) plus
        # a soft talent bump so elites finish drives / chunk plays without
        # rewriting the pressure slope.
        yards_per_attempt = _clamp(
            (6.97 - (0.6 * inputs.qb_pressure_factor)) * opp_ypa_factor * (0.97 + (0.03 * talent_factor)),
            5.0,
            9.5,
        )
        pass_yards_mean = attempts_mean * yards_per_attempt
        # Real bug found while re-validating the targets_mean fix (same
        # "arbitrary undercalibrated coefficient" pattern): rush_share is
        # the same real, correctly-denominated share metric RB's
        # carries_mean already uses successfully (rush_attempts / team
        # rush_attempts) -- but the QB branch scaled it by a coefficient
        # ~7.5x too small (4.0 vs. RB's 24.0), so a real mobile starter
        # (e.g. a genuine ~0.19-0.29 rush_share) projected for only
        # ~2.0-2.4 carries/game instead of a realistic ~6-9. Confirmed via
        # real weighted linear regression against 110 real
        # 2023-2025 QB-seasons (>=8 games): carries_per_game = 0.26 +
        # 29.85*rush_share, R^2=0.857 -- a strong, real fit, not curve-fit
        # noise. This drastically undercounted every mobile QB's rushing
        # yards/TDs league-wide (e.g. a real ~700-yard/16-TD rushing
        # season projected for only ~110 yards/~5 TDs).
        carries_mean = _clamp(0.3 + (29.8 * inputs.rush_share), 0.0, 10.0) * qb_starter_share_factor
        rush_yards_mean = carries_mean * _clamp((4.6 - (0.7 * inputs.qb_pressure_factor)) * opp_rush_factor, 2.6, 7.0)
        # Surface integrity (2026-08-29): pass TDs must share a yards rate
        # with pass_yards. Historical league TD leaders land mid-30s to
        # mid-40s on ~4k–4.5k yards ⇒ ~115 yards / TD. The prior
        # (yards/115)*0.79 discount (~146 yd/TD) capped live leaders near
        # ~29 and left projections hubs printing ~17–20. Rate is now
        # yards/PASS_TD_YARDS_PER with no discount; RZ share stays out
        # (still a rushing-share proxy for QBs, not pass efficiency).
        pass_tds_mean = (
            _clamp(pass_yards_mean / PASS_TD_YARDS_PER, 0.15, 3.8) * qb_starter_share_factor
        )
        # rush_tds_mean's coefficient is refit alongside carries_mean above
        # (same real regression exercise): real QB rushing TDs, isolated
        # from passing TDs via (touchdowns_scored - pass_touchdowns) across
        # the same 2023-2025 sample, divided by the real
        # rush_attempts*red_zone_share weighted sum, implies ~0.50 -- the
        # old 0.12 was calibrated against carries_mean's old (also too
        # small) volume, so it needed the same correction once carries_mean
        # was fixed, not just a proportional pass-through.
        rush_tds_mean = _clamp(carries_mean * inputs.red_zone_share * 0.50, 0.0, 1.5)
        receptions_mean = 0.0
        receiving_yards_mean = 0.0
    elif position in {"RB", "FB"}:
        opp_pass_factor = _clamp(inputs.opponent_pass_defense_factor, 0.75, 1.30)
        opp_rush_factor = _clamp(inputs.opponent_rush_defense_factor, 0.75, 1.30)
        skill_talent = _clamp(float(inputs.skill_talent_factor or 1.0), 0.88, 1.26)
        # Enterprise rush retune: bell cows clear ~90-110 rush yd/g (~1500-1900
        # /17); old 4+24*share flattened leaders near ~60-70 yd/g.
        # Phase 2: compress carry schedule — fresh rematerialize overshoots
        # rush actual (~+12 resid; RB1 ~+11). v3 half-step still left ~+7;
        # tighten further while keeping committee shares physical.
        carries_mean = _clamp(4.0 + (22.5 * inputs.rush_share * pace_factor), 0.0, 30.0)
        carries_mean *= skill_talent
        targets_mean = _clamp(0.5 + (inputs.target_proxy * team_pass_attempts_estimate), 0.0, 11.0)
        rush_yards_mean = carries_mean * _clamp(
            (4.05 + (1.15 * volume_signal)) * opp_rush_factor * (0.96 + (0.04 * skill_talent)),
            2.8,
            7.8,
        )
        # Real bug found while auditing residual receiving-yards undercount
        # after the targets_mean fix (prop Vegas benchmark, CURRENT arm still
        # ~-12 yd bias vs truth / ~-6 yd vs market on receiving props):
        # targets_mean was already roughly right (slightly high), but
        # catch rate and YPR were both systematically low. Confirmed via
        # real weighted least squares against 738 real 2023-2025 RB
        # game-rows (weeks 4-17, targets>=1, receptions>=1, weighted by
        # targets/receptions): catch_rate ~ 0.81 + 0.02*route_proxy
        # (R^2≈0 — route adds nothing; weighted mean CR=0.81) vs. the old
        # 0.62+0.16*route which biased -0.15; YPR/opp ~
        # 7.06 + 3.65*target_proxy (weighted mean YPR≈7.4) vs. old
        # 6.0+2.8*target_proxy which biased -1.17 YPR. Refit both.
        receptions_mean = targets_mean * _clamp(0.81 + (0.02 * inputs.route_proxy), 0.50, 0.95)
        receiving_yards_mean = receptions_mean * _clamp((7.06 + (3.65 * inputs.target_proxy)) * opp_pass_factor, 4.2, 15.5)
        # Real bug found via a live 2026 spot-check: 7+ different real
        # bell-cow RBs (J.Taylor, D.Henry, C.McCaffrey, J.Gibbs, J.Williams,
        # C.Brown, B.Robinson) were all simultaneously projecting for 15-19
        # season rushing TDs -- real NFL seasons rarely see more than 2-3
        # backs clear 15 rushing TDs, not a cluster of 7. The 0.16
        # coefficient itself was the culprit (the underlying carries_mean
        # ~14-17/game and red_zone_share ~0.40-0.45 inputs were both
        # legitimate real shares). Confirmed via real weighted least
        # squares against 259 real 2023-2025 RB-seasons (>=8 games,
        # regular season only -- weeks<=18, excluding playoffs to match the
        # model's own 17-game season unit), weighted by real season
        # carries volume, real rushing TDs isolated from receiving TDs via
        # play-by-play (play_type='run', touchdown=true), against the
        # SAME red_zone_share definition production uses
        # ((red_zone_targets+red_zone_carries)/team_red_zone_events, see
        # materialize_player_projection_features): coefficient 0.098
        # (R^2=0.489) -- a real, meaningful ~40% overshoot, not noise (a
        # real 348-carry/0.393-red-zone-share bell-cow like 2024 Barkley
        # projected 23.2 season rush TDs at 0.16 vs. a real 14; refit lands
        # at a realistic 14.2).
        # Enterprise soft retune: 0.10 was truth-fit but clustered too many
        # bell cows near 15+ season rush TDs once carries lifted; 0.092 keeps
        # hierarchy while capping the top of the board.
        rush_tds_mean = _clamp(carries_mean * inputs.red_zone_share * 0.092, 0.0, 1.55)
        # Real bug found while re-validating the targets_mean fix: rec_tds's
        # coefficient (0.08) was calibrated against the OLD, drastically
        # undercounted receptions_mean -- and was independently too small
        # even accounting for that. Real fit against 2023-2025 usage data
        # (real receiving TDs credited to RB, isolated from rushing TDs via
        # team pass_touchdowns minus WR/TE touchdowns_scored): a simple
        # ratio-of-sums fit implies ~0.17, but a weighted-least-squares fit
        # (which properly weights the high-volume/high-red-zone-share
        # players who dominate real receiving-TD counts, instead of letting
        # small-sample noise from low-usage RBs skew a simple ratio) lands
        # at ~0.10 -- used here since the ratio-of-sums version visibly
        # overshot elite receiving RBs once checked end-to-end.
        rec_tds_mean = _clamp(receptions_mean * inputs.red_zone_share * 0.10, 0.0, 1.2)
    elif position == "WR":
        opp_pass_factor = _clamp(inputs.opponent_pass_defense_factor, 0.75, 1.30)
        opp_rush_factor = _clamp(inputs.opponent_rush_defense_factor, 0.75, 1.30)
        # Soften ±30% EPA matchup on YPR — full factor inflated McLaurin-class
        # means ~20-30 yards over books on soft defenses.
        opp_ypr = _clamp(1.0 + (0.40 * (opp_pass_factor - 1.0)), 0.88, 1.12)
        skill_talent = _clamp(float(inputs.skill_talent_factor or 1.0), 0.88, 1.24)
        # Enterprise fix: old role_vol (0.55+0.45*role) crushed WR1s hydrated
        # at role_confidence~0.28 down to ~67% of earned targets — Chase-class
        # landed ~57 yd/g vs real ~100. Milder role_vol + talent restore
        # alpha while depth-1 role floors (materializer) keep hierarchy.
        role_vol = _clamp(0.80 + (0.20 * inputs.role_confidence), 0.72, 1.0)
        targets_mean = _clamp(
            (0.6 + (inputs.target_proxy * team_pass_attempts_estimate)) * role_vol * skill_talent,
            0.0,
            15.0,
        )
        # Catch rate / YPR from 2023-2025 WLS; soft talent bump on YPR for
        # elites without rewriting the flat efficiency prior.
        receptions_mean = targets_mean * _clamp(0.62 + (0.12 * inputs.route_proxy), 0.40, 0.93)
        receiving_yards_mean = receptions_mean * _clamp(
            13.1 * opp_ypr * (0.97 + (0.03 * skill_talent)),
            5.5,
            20.5,
        )
        # rush_share is fraction of team rushes — scale by ~team rush volume
        # (~22), not a 2.0 stub that understated gadget/jet-sweep WRs ~16x.
        carries_mean = _clamp(22.0 * inputs.rush_share * pace_factor, 0.0, 8.0)
        rush_yards_mean = carries_mean * _clamp((5.0 + (0.8 * volume_signal)) * opp_rush_factor, 3.0, 9.0)
        # Surface integrity (2026-08-29): receiving TDs must share a yards
        # rate with receiving_yards. Receptions×RZ alone let Chase-class
        # volume print ~9–10 TDs on ~1.8k yards (and zero-TD rows with
        # hundreds of yards). Historical WR TD leaders land ~12–18 on
        # ~1.2k–1.8k yards ⇒ ~100 yards / TD.
        rec_tds_mean = _clamp(receiving_yards_mean / REC_TD_YARDS_PER, 0.0, 1.5)
        rush_tds_mean = _clamp(carries_mean * inputs.red_zone_share * 0.08, 0.0, 0.7)
    elif position == "TE":
        opp_pass_factor = _clamp(inputs.opponent_pass_defense_factor, 0.75, 1.30)
        opp_rush_factor = _clamp(inputs.opponent_rush_defense_factor, 0.75, 1.30)
        opp_ypr = _clamp(1.0 + (0.40 * (opp_pass_factor - 1.0)), 0.88, 1.12)
        skill_talent = _clamp(float(inputs.skill_talent_factor or 1.0), 0.88, 1.22)
        role_vol = _clamp(0.80 + (0.20 * inputs.role_confidence), 0.72, 1.0)
        targets_mean = _clamp(
            (0.55 + (inputs.target_proxy * team_pass_attempts_estimate)) * role_vol * skill_talent,
            0.0,
            14.0,
        )
        receptions_mean = targets_mean * _clamp(0.73 + (0.07 * inputs.route_proxy), 0.45, 0.95)
        receiving_yards_mean = receptions_mean * _clamp(
            10.6 * opp_ypr * (0.97 + (0.03 * skill_talent)),
            5.5,
            18.5,
        )
        carries_mean = _clamp(18.0 * inputs.rush_share * pace_factor, 0.0, 6.0)
        rush_yards_mean = carries_mean * _clamp((5.0 + (0.8 * volume_signal)) * opp_rush_factor, 3.0, 9.0)
        rec_tds_mean = _clamp(receiving_yards_mean / REC_TD_YARDS_PER, 0.0, 1.5)
        rush_tds_mean = _clamp(carries_mean * inputs.red_zone_share * 0.08, 0.0, 0.7)
    # else: OL/DL/LB/DB/K/P/LS/ST -- every *_mean stays at its 0.0 default.
    # Real bug found via a live production spot-check: this branch used to
    # be a bare `else` covering "everyone who isn't QB/RB/FB", which meant
    # every defensive player, offensive lineman, kicker, and punter got
    # routed through the WR/TE formula above. That formula has ADDITIVE
    # FLOORS by design for genuine skill players (targets_mean's `1.2 +`
    # base, receiving_yards_mean's `5.5` minimum yards/catch) -- appropriate
    # for a real WR/TE, who will always see a nonzero target share, but with
    # zero position-awareness those same floors guaranteed EVERY non-QB/RB
    # player a nonzero season-long receiving projection, including a rare
    # real one-off event (e.g. a real trick-play catch by an offensive
    # tackle in a single 2025 game) getting amplified into a ~90+ yard
    # SEASON projection for a player at a position that structurally never
    # accumulates meaningful passing-game usage. Confirmed live: 1,998 of
    # 1,998 OL/DL/LB/DB/K/P-tagged players in the deployed 2026 bundle had
    # nonzero receiving yards before this fix -- 100% of them, which is
    # itself the signature of a formula-floor bug, not real signal.

    # Availability and role confidence reduce all outcomes in a deterministic, bounded manner.
    # WR/TE floors raised: old 0.50 floor + low role_confidence double-crushed
    # alpha receivers after role_vol had already cut targets.
    if position == "QB":
        confidence_floor = 0.72
    elif position in {"RB", "FB"}:
        confidence_floor = 0.68
    elif position in {"WR", "TE"}:
        confidence_floor = 0.74
    else:
        confidence_floor = 0.50
    confidence_scale = _clamp((0.70 * availability_factor) + (0.30 * role_factor), confidence_floor, 1.0)
    pass_yards_mean *= confidence_scale
    rush_yards_mean *= confidence_scale
    receiving_yards_mean *= confidence_scale
    receptions_mean *= confidence_scale
    carries_mean *= confidence_scale
    attempts_mean *= confidence_scale
    pass_tds_mean *= confidence_scale
    rush_tds_mean *= confidence_scale
    rec_tds_mean *= confidence_scale

    # A rookie (or anyone with no real usage history backing their
    # projection) has genuinely more outcome uncertainty than a veteran
    # projected to the same mean -- there's no track record to tighten the
    # distribution around. This widens std only, never the mean.
    variance_widening = _clamp(
        1.0 + (1.0 - _clamp(inputs.experience_confidence, 0.0, 1.0)) * (MAX_VARIANCE_WIDENING - 1.0),
        1.0,
        MAX_VARIANCE_WIDENING,
    )

    # Slightly wider pass CV: Vegas regrade showed 68% residual coverage ~60%
    # at the old 0.22 coefficient (enterprise cal also inflates post-blend).
    pass_yards_std = max(3.0, pass_yards_mean * 0.26) * variance_widening
    rush_yards_std = max(2.2, rush_yards_mean * 0.33) * variance_widening
    receiving_yards_std = max(2.2, receiving_yards_mean * 0.34) * variance_widening
    receptions_std = max(0.4, receptions_mean * 0.31) * variance_widening
    attempts_std = max(0.8, attempts_mean * 0.18) * variance_widening
    carries_std = max(0.6, carries_mean * 0.24) * variance_widening
    targets_std = max(0.5, targets_mean * 0.26) * variance_widening

    anytime_td_prob = _clamp(1.0 - math.exp(-(rush_tds_mean + rec_tds_mean)), 0.005, 0.92)
    total_td_mean = pass_tds_mean + rush_tds_mean + rec_tds_mean
    outcome_floor = {
        "pass_yards": max(0.0, pass_yards_mean - (1.05 * pass_yards_std)),
        "rush_yards": max(0.0, rush_yards_mean - (0.95 * rush_yards_std)),
        "receiving_yards": max(0.0, receiving_yards_mean - (0.95 * receiving_yards_std)),
        "receptions": max(0.0, receptions_mean - (0.9 * receptions_std)),
        "touchdowns": max(0.0, total_td_mean * 0.35),
    }
    outcome_median = {
        "pass_yards": pass_yards_mean,
        "rush_yards": rush_yards_mean,
        "receiving_yards": receiving_yards_mean,
        "receptions": receptions_mean,
        "touchdowns": total_td_mean,
    }
    outcome_ceiling = {
        "pass_yards": pass_yards_mean + (1.15 * pass_yards_std),
        "rush_yards": rush_yards_mean + (1.15 * rush_yards_std),
        "receiving_yards": receiving_yards_mean + (1.25 * receiving_yards_std),
        "receptions": receptions_mean + (1.2 * receptions_std),
        "touchdowns": min(4.0, total_td_mean * 1.9 + 0.25),
    }
    return {
        "attempts_mean": round(attempts_mean, 3),
        "attempts_std": round(attempts_std, 3),
        "carries_mean": round(carries_mean, 3),
        "carries_std": round(carries_std, 3),
        "targets_mean": round(targets_mean, 3),
        "targets_std": round(targets_std, 3),
        "completions_mean": round((attempts_mean * completion_rate) if position == "QB" else 0.0, 3),
        "pass_yards_mean": round(pass_yards_mean, 3),
        "pass_yards_std": round(pass_yards_std, 3),
        "rush_yards_mean": round(rush_yards_mean, 3),
        "rush_yards_std": round(rush_yards_std, 3),
        "receiving_yards_mean": round(receiving_yards_mean, 3),
        "receiving_yards_std": round(receiving_yards_std, 3),
        "receptions_mean": round(receptions_mean, 3),
        "receptions_std": round(receptions_std, 3),
        "pass_tds_mean": round(pass_tds_mean, 3),
        "rush_tds_mean": round(rush_tds_mean, 3),
        "rec_tds_mean": round(rec_tds_mean, 3),
        "anytime_td_prob": round(anytime_td_prob, 4),
        "floor_outcome": outcome_floor,
        "median_outcome": outcome_median,
        "ceiling_outcome": outcome_ceiling,
        "uncertainty": {
            "confidence_scale": round(confidence_scale, 4),
            "volume_signal": round(volume_signal, 4),
            "availability_factor": round(availability_factor, 4),
            "role_factor": round(role_factor, 4),
            "experience_confidence": round(_clamp(inputs.experience_confidence, 0.0, 1.0), 4),
            "variance_widening": round(variance_widening, 4),
        },
        "matchup": {
            "opponent_pass_defense_factor": round(_clamp(inputs.opponent_pass_defense_factor, 0.75, 1.30), 4),
            "opponent_rush_defense_factor": round(_clamp(inputs.opponent_rush_defense_factor, 0.75, 1.30), 4),
        },
    }


def evaluate_prop_edge(
    *,
    model_mean: float,
    model_std: float,
    line: float,
    market_over_price: int | None,
    market_under_price: int | None,
    market_key: str = "",
    position: str = "",
    role_confidence: float | None = None,
    availability_confidence: float | None = None,
    raw_model_mean: float | None = None,
    market_shrink: float | None = None,
    calibration_source: str | None = None,
    fallback_used: bool = False,
    joined_book_count: int = 0,
) -> Dict[str, Any]:
    # De-vig + PLAY/WATCH tags live in nfl_prop_edge_policy (enterprise path).
    from .nfl_prop_edge_policy import evaluate_prop_edge as _evaluate_prop_edge

    return _evaluate_prop_edge(
        model_mean=model_mean,
        model_std=model_std,
        line=line,
        market_over_price=market_over_price,
        market_under_price=market_under_price,
        market_key=market_key,
        position=position,
        role_confidence=role_confidence,
        availability_confidence=availability_confidence,
        raw_model_mean=raw_model_mean,
        market_shrink=market_shrink,
        calibration_source=calibration_source,
        fallback_used=fallback_used,
        joined_book_count=joined_book_count,
    )


def fantasy_points_from_projection(*, scoring_profile: str, pass_yards: float, pass_tds: float, rush_yards: float, rush_tds: float, receiving_yards: float, receptions: float, rec_tds: float) -> float:
    profile = scoring_profile.strip().lower()
    ppr_bonus = 0.0
    if profile == "half_ppr":
        ppr_bonus = 0.5
    elif profile == "ppr":
        ppr_bonus = 1.0
    return round(
        (pass_yards / 25.0)
        + (pass_tds * 4.0)
        + (rush_yards / 10.0)
        + (rush_tds * 6.0)
        + (receiving_yards / 10.0)
        + (receptions * ppr_bonus)
        + (rec_tds * 6.0),
        4,
    )
