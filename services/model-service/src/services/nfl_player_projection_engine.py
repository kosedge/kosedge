from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict


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
    own), it computes each QB's real team-relative share of "who is the
    starter" (this QB's `team_snap_share` divided by the team's single
    highest QB `team_snap_share` that week -- see
    `nfl_player_projection_engine.compute_qb_starter_shares`) and passes it
    through here. 1.0 (the default, and always correct for a team with only
    one rostered QB, or for any caller not yet wired for team context) means
    "fully independent, could be the starter" -- the original, unscaled
    behavior. Multiplicatively scales `attempts_mean` and `carries_mean`
    (and everything downstream of them: pass/rush yards and TDs), so a
    clear backup projects nowhere near a starter's volume, while a real
    starter (share == 1.0) is completely unaffected."""
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


def compute_qb_starter_shares(team_snap_shares: Dict[str, float]) -> Dict[str, float]:
    """Pure: given {player_key: team_snap_share} for every rostered QB on
    ONE team for one week, returns {player_key: qb_starter_share} -- see
    `PlayerFeatureInputs.qb_starter_share`'s docstring for the bug this
    feeds into the fix for.

    The QB with the highest `team_snap_share` is treated as the real
    starter and gets a share of 1.0 (completely unaffected, including the
    single-QB-on-roster case, which always returns 1.0 for that lone QB
    regardless of their `team_snap_share` value -- there's no depth-chart
    competition to resolve when there's only one rostered QB). Every other
    QB's share is their own `team_snap_share` divided by the starter's,
    clamped to [0, 1] -- i.e. purely data-driven from the model's own
    already-calibrated relative-role signal, never a new arbitrary
    constant, and it can only ever discount a backup, never inflate the
    starter above 1.0.
    """
    if not team_snap_shares:
        return {}
    if len(team_snap_shares) == 1:
        return {key: 1.0 for key in team_snap_shares}
    starter_key = max(team_snap_shares, key=lambda k: float(team_snap_shares[k] or 0.0))
    starter_share = float(team_snap_shares[starter_key] or 0.0)
    if starter_share <= 0.0:
        # No real signal to rank by (e.g. every QB hydrated at exactly
        # 0.0) -- leave everyone at 1.0 rather than dividing by zero or
        # guessing at an ordering the data doesn't support.
        return {key: 1.0 for key in team_snap_shares}
    return {
        key: (1.0 if key == starter_key else _clamp(float(value or 0.0) / starter_share, 0.0, 1.0))
        for key, value in team_snap_shares.items()
    }


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
    team_pass_attempts_estimate = pace_factor * pass_factor * 35.2

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
        # team_snap_share (involvement / team offensive plays) is the real
        # signal for "is this the starter" -- snap_proxy is a touch-share
        # metric that badly undercounts QBs (see PlayerFeatureInputs docs).
        # Only fall back to the old snap_proxy-based blend when a caller
        # hasn't wired team_snap_share through yet (value still at its 0.0
        # default), so this degrades gracefully rather than breaking.
        starter_signal = inputs.team_snap_share if inputs.team_snap_share > 0.0 else inputs.snap_proxy
        qb_volume_signal = _clamp(
            (0.55 * starter_signal) + (0.45 * _clamp(inputs.qb_dropback_factor / 1.15, 0.35, 1.35)),
            0.25,
            1.0,
        )
        opp_pass_factor = _clamp(inputs.opponent_pass_defense_factor, 0.75, 1.30)
        opp_rush_factor = _clamp(inputs.opponent_rush_defense_factor, 0.75, 1.30)
        qb_starter_share_factor = _clamp(inputs.qb_starter_share, 0.0, 1.0)
        attempts_mean = (22.0 + (34.0 * qb_volume_signal * pass_factor * pace_factor)) * qb_starter_share_factor
        completion_rate = _clamp(0.60 + (0.05 * inputs.target_proxy) - (0.03 * inputs.qb_pressure_factor), 0.50, 0.74)
        yards_per_attempt = _clamp((6.2 + (1.1 * inputs.target_proxy) - (0.6 * inputs.qb_pressure_factor)) * opp_pass_factor, 5.0, 10.5)
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
        pass_tds_mean = _clamp((pass_yards_mean / 115.0) * (0.72 + (0.32 * inputs.red_zone_share)), 0.15, 3.8) * qb_starter_share_factor
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
        carries_mean = _clamp(4.0 + (24.0 * inputs.rush_share * pace_factor), 0.0, 32.0)
        targets_mean = _clamp(0.5 + (inputs.target_proxy * team_pass_attempts_estimate), 0.0, 11.0)
        rush_yards_mean = carries_mean * _clamp((4.1 + (1.1 * volume_signal)) * opp_rush_factor, 2.8, 7.8)
        receptions_mean = targets_mean * _clamp(0.62 + (0.16 * inputs.route_proxy), 0.40, 0.92)
        receiving_yards_mean = receptions_mean * _clamp((6.0 + (2.8 * inputs.target_proxy)) * opp_pass_factor, 4.2, 15.5)
        rush_tds_mean = _clamp(carries_mean * inputs.red_zone_share * 0.16, 0.0, 1.7)
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
    elif position in {"WR", "TE"}:
        opp_pass_factor = _clamp(inputs.opponent_pass_defense_factor, 0.75, 1.30)
        opp_rush_factor = _clamp(inputs.opponent_rush_defense_factor, 0.75, 1.30)
        targets_mean = _clamp(0.5 + (inputs.target_proxy * team_pass_attempts_estimate), 0.0, 15.0)
        receptions_mean = targets_mean * _clamp(0.56 + (0.28 * inputs.route_proxy), 0.38, 0.93)
        receiving_yards_mean = receptions_mean * _clamp((8.4 + (4.2 * volume_signal)) * opp_pass_factor, 5.5, 23.0)
        carries_mean = _clamp(2.0 * inputs.rush_share, 0.0, 4.0)
        rush_yards_mean = carries_mean * _clamp((5.0 + (0.8 * volume_signal)) * opp_rush_factor, 3.0, 9.0)
        # Real bug found while re-validating the targets_mean fix (same
        # "evaporating share" pattern the box-score engine's backtest
        # addendum flagged, but in TD math this time, not target counts):
        # rec_tds_mean's coefficient (0.14) drastically undercounted real
        # receiving TDs regardless of real volume. A simple ratio-of-sums
        # fit against 2023-2025 usage data (real receiving TDs / real
        # receptions*red_zone_share weighted sum, league-wide) implies
        # ~0.90, but that fit is dominated by low-volume bench WR/TEs and
        # overshoots real elite WR1s once checked end-to-end (a real 126
        # rec / 1,235 yd season projected ~18 receiving TDs -- beyond even
        # the all-time record). A weighted-least-squares fit (weights each
        # real observation by its own volume, so it fits the
        # high-target/high-red-zone-share players who actually drive real
        # receiving-TD totals, not diluted by scrub-role noise) lands at
        # ~0.50 and reproduces realistic real-world TD totals end-to-end
        # (that same real elite WR1 profile: ~9-10 receiving TDs, matching
        # real comparable seasons).
        rec_tds_mean = _clamp(receptions_mean * inputs.red_zone_share * 0.50, 0.0, 1.5)
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
    confidence_floor = 0.72 if position == "QB" else (0.60 if position in {"RB", "FB"} else 0.50)
    confidence_scale = _clamp((0.65 * availability_factor) + (0.35 * role_factor), confidence_floor, 1.0)
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

    pass_yards_std = max(3.0, pass_yards_mean * 0.22) * variance_widening
    rush_yards_std = max(2.2, rush_yards_mean * 0.31) * variance_widening
    receiving_yards_std = max(2.2, receiving_yards_mean * 0.33) * variance_widening
    receptions_std = max(0.4, receptions_mean * 0.29) * variance_widening
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


def evaluate_prop_edge(*, model_mean: float, model_std: float, line: float, market_over_price: int | None, market_under_price: int | None) -> Dict[str, Any]:
    bounded_std = max(0.65, float(model_std))
    z_over = (float(model_mean) - float(line)) / bounded_std
    over_prob = _clamp(_normal_cdf(z_over), 0.01, 0.99)
    under_prob = _clamp(1.0 - over_prob, 0.01, 0.99)

    market_over_prob = None
    market_under_prob = None
    if market_over_price is not None:
        market_over_prob = (abs(market_over_price) / (abs(market_over_price) + 100.0)) if market_over_price < 0 else (100.0 / (market_over_price + 100.0))
    if market_under_price is not None:
        market_under_prob = (abs(market_under_price) / (abs(market_under_price) + 100.0)) if market_under_price < 0 else (100.0 / (market_under_price + 100.0))

    edge_over = over_prob - market_over_prob if market_over_prob is not None else None
    edge_under = under_prob - market_under_prob if market_under_prob is not None else None
    confidence = _clamp((abs(z_over) / 2.6) + (0.30 if market_over_prob is not None and market_under_prob is not None else 0.0), 0.05, 0.99)
    return {
        "over_prob": round(over_prob, 4),
        "under_prob": round(under_prob, 4),
        "fair_over_price": fair_price_from_prob(over_prob),
        "fair_under_price": fair_price_from_prob(under_prob),
        "edge_over": round(edge_over, 4) if edge_over is not None else None,
        "edge_under": round(edge_under, 4) if edge_under is not None else None,
        "confidence": round(confidence, 4),
    }


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
