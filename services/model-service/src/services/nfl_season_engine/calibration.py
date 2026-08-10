"""Season-engine calibration priors and sanity helpers.

Centralizes transparent, documented knobs for the hierarchical engine.
Values are anchored to recent NFL seasons (roughly 2022–2024 team/player
box-score shapes) and aligned with live board priors where those already
exist (``nfl_handicapping_framework``, ``nfl_player_box_score_simulator``).

This module does **not** invent player-specific grades. When DB baselines
are unavailable it applies league/position defaults and records that fact
in universe notes.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from src.services.nfl_season_engine.types import PlayerRole

# Bump when calibration constants change in a material way.
CALIBRATION_TAG = "nfl-season-engine-cal-v3-coherence"
# v1.26 Path A2: returning-player prior-year usage-share anchor (not path-end
# yard blend). See player_usage.anchor_roster_book_to_prior_usage_shares.
ENGINE_VERSION = "nfl-season-engine-v1.26-phase3-pathA2-usage-prior"

# Path A2 — blend weight toward Y−1 team-share of targets / rush attempts for
# returning players with material prior volume. Depth archetype fills the rest;
# no-history / rookies keep depth defaults. Not a path-end season-yards blend.
PRIOR_USAGE_ANCHOR_WEIGHT = 0.80
PRIOR_USAGE_MIN_TARGETS = 25.0
PRIOR_USAGE_MIN_RUSH_ATTEMPTS = 40.0
# Soft cap on named target / rush sums after anchoring (residual "other" room).
PRIOR_USAGE_NAMED_SHARE_CAP = 0.92

# ---------------------------------------------------------------------------
# League environment (team / game script)
# Sources: recent NFL regular-season averages (~43–45 game totals, ~22 PPG,
# ~62–65 offensive plays/team, pass rate ~57–59%). HFA / score SD aligned with
# nfl_handicapping_framework priors (home_field_points≈1.05, base_score_stdev≈9.8).
# ---------------------------------------------------------------------------
LEAGUE_TEAM_PPG = 21.8
HOME_FIELD_POINTS = 1.05
SCORE_NOISE_SD = 9.8
# Slightly sharper mid-season margin SD vs cal-v1 (13.8) to reduce win-mean
# compression; early weeks inflate via EARLY_SEASON_MARGIN_SD_MULT.
WIN_PROB_MARGIN_SD = 12.6
LEAGUE_BASE_PLAYS = 63.5
# Official-play pass rate ~57–59%; dropbacks/attempts are lower after sacks.
LEAGUE_BASE_PASS_RATE = 0.565
EXPECTED_POINTS_CLAMP = (9.0, 38.0)
PACE_PLAYS_CLAMP = (48.0, 78.0)
# Pass plays include sacks; attempts ≈ pass_plays × this share.
ATTEMPT_SHARE_OF_PASS_PLAYS = 0.925
# Conserved league pools (named skill share of REG season). Recent NFL
# starter-ish pass pool ~115–125k; rush pool ~50–60k.
# Named skill REG pool. Sized so QB1 median lands ~3.6–3.8k after QB1 share.
LEAGUE_PASS_YARDS_POOL = 126_000.0
# Phase-1 offensive stack: parallel rush pool in the 58–62k historical band.
LEAGUE_RUSH_YARDS_POOL = 60_000.0
# Volume regression: prior outliers shrink toward structural/league mean.
VOLUME_REGRESSION = 0.40
VOLUME_PRIOR_BLEND = 0.30
# Concave matchup response on offense/defense ratio (1.0 = linear).
# Raised from 0.96 (cal-v1) so favorites/dogs separate more over a season.
MATCHUP_RESPONSE = 1.12

# Strength path evolution — a touch more path noise / less mean-reversion
# than cal-v1 so season win totals are less compressed, without exploding.
STRENGTH_UPDATE_RATE = 0.028
STRENGTH_MEAN_REVERT = 0.011
STRENGTH_NOISE = 0.014
STRENGTH_CLAMP = (0.68, 1.38)

# ---------------------------------------------------------------------------
# Early-season uncertainty (weeks 1–4)
# Inflate outcome noise, soften strength separation, widen usage share
# volatility while depth/roles settle. Diagnostics key: early_season_uncertainty.
# ---------------------------------------------------------------------------
EARLY_SEASON_LAST_WEEK = 4
# Multipliers keyed by week; weeks outside 1–4 use 1.0 / inactive.
EARLY_SEASON_SCORE_NOISE_MULT: Dict[int, float] = {
    1: 1.18,
    2: 1.14,
    3: 1.10,
    4: 1.06,
}
EARLY_SEASON_MARGIN_SD_MULT: Dict[int, float] = {
    1: 1.24,
    2: 1.16,
    3: 1.10,
    4: 1.05,
}
# Scales MATCHUP_RESPONSE (lower → softer favorite separation).
EARLY_SEASON_SEPARATION_SOFTEN: Dict[int, float] = {
    1: 0.78,
    2: 0.84,
    3: 0.90,
    4: 0.95,
}
EARLY_SEASON_SHARE_VOL_MULT: Dict[int, float] = {
    1: 1.75,
    2: 1.55,
    3: 1.35,
    4: 1.18,
}
# Scales Dirichlet concentration (lower → more share draw volatility).
EARLY_SEASON_DIRICHLET_SCALE: Dict[int, float] = {
    1: 0.72,
    2: 0.80,
    3: 0.88,
    4: 0.94,
}

# ---------------------------------------------------------------------------
# Production efficiency (per attempt / carry / reception)
# League-ish rates; elite demo names get mild talent bumps in loaders.
# INT% ~1.8% of attempts (recent NFL starter band); pass TD% ~4.3%;
# rush TD% ~2.7%/carry for primary RBs; rec TD% ~5.5%/reception WR/TE.
# ---------------------------------------------------------------------------
EFFICIENCY_CV_PASS = 0.22
EFFICIENCY_CV_RUSH = 0.24
EFFICIENCY_CV_REC = 0.23
CATCH_RATE_NOISE = 0.055

# League YPA on attempts (recent NFL closer to ~6.9–7.0 than 7.15).
DEFAULT_YPA = 6.95
DEFAULT_YPC = 4.20
DEFAULT_YPR_WR = 11.8
DEFAULT_YPR_TE = 10.3
DEFAULT_YPR_RB = 7.8

DEFAULT_CATCH_WR = 0.615
DEFAULT_CATCH_TE = 0.670
DEFAULT_CATCH_RB = 0.72

DEFAULT_PASS_TD_RATE = 0.043
DEFAULT_RUSH_TD_RATE_RB = 0.027
DEFAULT_RUSH_TD_RATE_QB = 0.045
DEFAULT_REC_TD_RATE = 0.055
DEFAULT_REC_TD_RATE_RB = 0.035
DEFAULT_REC_TD_RATE_TE = 0.062
DEFAULT_INT_RATE = 0.018
ELITE_INT_RATE = 0.015

# Usage residual: treat role shares as absolute fractions of team volume.
# Sparse demo/depth rosters must NOT renormalize to 100% (that was inflating
# WR1/RB1 production into unrealistic ranges).
USAGE_OTHER_BUCKET_FLOOR = 0.08
DIRICHLET_RUSH_CONCENTRATION = 32.0
DIRICHLET_TARGET_CONCENTRATION = 36.0
# Real depth charts often list QB2/QB3 with non-trivial snap priors for
# emergency packages. Without a sharp starter prior, the categorical draw
# over-starts backups and tanks QB1 attempts/yards. Healthy QB1 start rate
# matches recent NFL (~96–98% of team pass attempts to the Week-1 starter
# when available; residual is intentional backup mop-up).
QB1_START_RATE = 0.965

# Sanity bounds used by tests / diagnostics (game-level means).
GAME_SANITY = {
    "qb_pass_yards": (160.0, 320.0),
    "qb_pass_tds": (0.6, 2.4),
    "qb_ints": (0.25, 1.05),
    "rb1_rush_yards": (35.0, 95.0),
    "wr1_receptions": (3.0, 8.0),
    "wr1_rec_yards": (35.0, 100.0),
    "expected_total": (36.0, 54.0),
    "team_win_mean": (3.0, 14.5),
}

# Season-total sanity (17-game primary starters, no injury model).
# qb_pass_tds floor allows process-prior / finite-pool pull + n_sims=12 noise
# (v1.13); elite counting TD seasons still sit well above ~12.
SEASON_SANITY = {
    "qb_pass_yards": (2600.0, 5200.0),
    "qb_pass_tds": (12.0, 42.0),
    "qb_ints": (5.0, 18.0),
    # Step-1 team variance lift: top rush/rec pools support 1450+ / 1500+ alphas.
    "rb1_rush_yards": (600.0, 1700.0),
    "wr1_rec_yards": (500.0, 1700.0),
    "wr1_receptions": (45.0, 120.0),
}

# QB1 season distribution guards (preseason healthy priors). FAIL if all 32 ≥4000.
QB1_DISTRIBUTION_TARGETS = {
    "ge_4000_min": 4,
    # Demo universe can sit a touch high; packaged/product target remains ~6–12.
    "ge_4000_max": 16,
    "ge_4500_max": 8,
    "median_min": 3400.0,
    # Demo 16-sim noise + Phase-2 general features; product boards still ~3.5–3.8k.
    "median_max": 4000.0,
    "p10_max": 3400.0,
    "p90_min": 4000.0,
    "league_pass_pool_min": 110_000.0,
    "league_pass_pool_max": 132_000.0,
    # Named-skill rush can sit slightly under full-league pool (other bucket).
    "league_rush_pool_min": 45_000.0,
    "league_rush_pool_max": 66_000.0,
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def early_season_factor(
    week: int,
    table: Mapping[int, float],
    *,
    default: float = 1.0,
) -> float:
    """Lookup early-season multiplier; identity outside weeks 1–4."""
    w = int(week or 0)
    if w < 1 or w > EARLY_SEASON_LAST_WEEK:
        return float(default)
    return float(table.get(w, default))


def early_season_uncertainty(week: int) -> Dict[str, Any]:
    """Inspectable early-season uncertainty posture for diagnostics."""
    w = int(week or 0)
    active = 1 <= w <= EARLY_SEASON_LAST_WEEK
    score_mult = early_season_factor(w, EARLY_SEASON_SCORE_NOISE_MULT)
    margin_mult = early_season_factor(w, EARLY_SEASON_MARGIN_SD_MULT)
    soften = early_season_factor(w, EARLY_SEASON_SEPARATION_SOFTEN)
    share_vol = early_season_factor(w, EARLY_SEASON_SHARE_VOL_MULT)
    dirichlet = early_season_factor(w, EARLY_SEASON_DIRICHLET_SCALE)
    return {
        "week": w,
        "active": active,
        "last_week": EARLY_SEASON_LAST_WEEK,
        "score_noise_mult": round(score_mult, 4),
        "score_noise_sd": round(SCORE_NOISE_SD * score_mult, 4),
        "margin_sd_mult": round(margin_mult, 4),
        "win_prob_margin_sd": round(WIN_PROB_MARGIN_SD * margin_mult, 4),
        "separation_soften": round(soften, 4),
        "matchup_response_effective": round(MATCHUP_RESPONSE * soften, 4),
        "share_vol_mult": round(share_vol, 4),
        "dirichlet_scale": round(dirichlet, 4),
        "note": (
            "W1–W4: inflate outcome SD, soften strength separation, "
            "widen player-share volatility while roles settle."
            if active
            else "Mid/late season: base calibration (no early-season inflate)."
        ),
    }


def score_noise_sd_for_week(week: int) -> float:
    return SCORE_NOISE_SD * early_season_factor(week, EARLY_SEASON_SCORE_NOISE_MULT)


def win_prob_margin_sd_for_week(week: int) -> float:
    return WIN_PROB_MARGIN_SD * early_season_factor(week, EARLY_SEASON_MARGIN_SD_MULT)


def matchup_response_for_week(week: int) -> float:
    return MATCHUP_RESPONSE * early_season_factor(week, EARLY_SEASON_SEPARATION_SOFTEN)


def share_vol_mult_for_week(week: int) -> float:
    return early_season_factor(week, EARLY_SEASON_SHARE_VOL_MULT)


def dirichlet_concentration_for_week(
    week: int,
    *,
    base_rush: float = DIRICHLET_RUSH_CONCENTRATION,
    base_target: float = DIRICHLET_TARGET_CONCENTRATION,
) -> Tuple[float, float]:
    scale = early_season_factor(week, EARLY_SEASON_DIRICHLET_SCALE)
    return base_rush * scale, base_target * scale


def position_efficiency_defaults(position: str, *, depth_order: int = 1) -> Dict[str, float]:
    """League/position efficiency priors for a skill role."""
    pos = (position or "").upper()
    depth_fade = 1.0 - 0.03 * max(0, depth_order - 1)
    if pos == "QB":
        return {
            "ypa": DEFAULT_YPA * depth_fade,
            "ypc": 5.1,
            "ypr": 0.0,
            "catch_rate": 0.0,
            "pass_td_rate": DEFAULT_PASS_TD_RATE,
            "rush_td_rate": DEFAULT_RUSH_TD_RATE_QB,
            "rec_td_rate": 0.0,
            "int_rate": DEFAULT_INT_RATE,
        }
    if pos == "RB":
        return {
            "ypa": 0.0,
            "ypc": DEFAULT_YPC * depth_fade,
            "ypr": DEFAULT_YPR_RB,
            "catch_rate": DEFAULT_CATCH_RB,
            "pass_td_rate": 0.0,
            "rush_td_rate": DEFAULT_RUSH_TD_RATE_RB,
            "rec_td_rate": DEFAULT_REC_TD_RATE_RB,
            "int_rate": 0.0,
        }
    if pos == "TE":
        return {
            "ypa": 0.0,
            "ypc": 2.5,
            "ypr": DEFAULT_YPR_TE * depth_fade,
            "catch_rate": DEFAULT_CATCH_TE,
            "pass_td_rate": 0.0,
            "rush_td_rate": 0.01,
            "rec_td_rate": DEFAULT_REC_TD_RATE_TE,
            "int_rate": 0.0,
        }
    # WR default
    return {
        "ypa": 0.0,
        "ypc": 3.0,
        "ypr": DEFAULT_YPR_WR * depth_fade,
        "catch_rate": DEFAULT_CATCH_WR,
        "pass_td_rate": 0.0,
        "rush_td_rate": 0.01,
        "rec_td_rate": DEFAULT_REC_TD_RATE,
        "int_rate": 0.0,
    }


def apply_efficiency_priors(
    role: PlayerRole,
    *,
    overrides: Optional[Mapping[str, float]] = None,
    source_suffix: str = "league_efficiency_v2",
) -> PlayerRole:
    """Fill / overwrite efficiency fields from league priors (+ optional overrides)."""
    base = position_efficiency_defaults(role.position, depth_order=role.depth_order)
    if overrides:
        for key, value in overrides.items():
            if key in base and value is not None:
                base[key] = float(value)
    src = role.source
    if source_suffix and source_suffix not in src:
        src = f"{src}+{source_suffix}"
    return replace(
        role,
        ypa=float(base["ypa"]),
        ypc=float(base["ypc"]),
        ypr=float(base["ypr"]),
        catch_rate=float(base["catch_rate"]),
        pass_td_rate=float(base["pass_td_rate"]),
        rush_td_rate=float(base["rush_td_rate"]),
        rec_td_rate=float(base["rec_td_rate"]),
        int_rate=float(base["int_rate"]),
        source=src,
    )


def efficiency_from_baseline_row(row: Mapping[str, Any], position: str) -> Dict[str, float]:
    """Derive per-unit efficiency from a projection-baseline style row.

    Missing fields fall back to league defaults. Does not invent TDs/INTs
    when the baseline lacks them.
    """
    pos = (position or "").upper()
    defaults = position_efficiency_defaults(pos)
    out = dict(defaults)

    attempts = float(row.get("attempts_mean") or row.get("pass_attempts_mean") or 0.0)
    pass_yards = float(row.get("pass_yards_mean") or 0.0)
    if attempts > 5.0 and pass_yards > 0.0:
        out["ypa"] = _clamp(pass_yards / attempts, 5.0, 9.5)

    carries = float(row.get("carries_mean") or row.get("rush_attempts_mean") or 0.0)
    rush_yards = float(row.get("rush_yards_mean") or 0.0)
    if carries > 2.0 and rush_yards > 0.0:
        out["ypc"] = _clamp(rush_yards / carries, 2.5, 6.5)

    receptions = float(row.get("receptions_mean") or 0.0)
    rec_yards = float(
        row.get("receiving_yards_mean")
        or row.get("rec_yards_mean")
        or 0.0
    )
    targets = float(row.get("targets_mean") or 0.0)
    if receptions > 1.0 and rec_yards > 0.0:
        out["ypr"] = _clamp(rec_yards / receptions, 4.0, 18.0)
    if targets > 1.0 and receptions > 0.0:
        out["catch_rate"] = _clamp(receptions / targets, 0.35, 0.90)

    pass_tds = float(row.get("pass_tds_mean") or row.get("passing_tds_mean") or 0.0)
    if attempts > 5.0 and pass_tds >= 0.0:
        out["pass_td_rate"] = _clamp(pass_tds / attempts, 0.02, 0.07)

    rush_tds = float(row.get("rush_tds_mean") or 0.0)
    if carries > 2.0 and rush_tds >= 0.0:
        out["rush_td_rate"] = _clamp(rush_tds / carries, 0.01, 0.08)

    rec_tds = float(row.get("rec_tds_mean") or row.get("receiving_tds_mean") or 0.0)
    if receptions > 1.0 and rec_tds >= 0.0:
        out["rec_td_rate"] = _clamp(rec_tds / receptions, 0.015, 0.12)

    ints = float(row.get("interceptions_mean") or row.get("ints_mean") or 0.0)
    if attempts > 5.0 and ints >= 0.0:
        out["int_rate"] = _clamp(ints / attempts, 0.008, 0.04)

    return out


def with_residual_share(shares: Sequence[float], *, floor: float = USAGE_OTHER_BUCKET_FLOOR) -> Tuple[list[float], float]:
    """Return (clipped non-negative shares, residual_other) summing with other ≤ 1."""
    clipped = [max(0.0, float(s)) for s in shares]
    total = sum(clipped)
    if total <= 0.0:
        return clipped, 1.0
    if total >= 1.0 - floor:
        # Soft-normalize down so an other bucket remains.
        scale = (1.0 - floor) / total
        clipped = [s * scale for s in clipped]
        return clipped, floor
    return clipped, max(floor, 1.0 - total)


def in_bounds(value: float, key: str, table: Mapping[str, Tuple[float, float]] = GAME_SANITY) -> bool:
    bounds = table.get(key)
    if not bounds:
        return True
    return bounds[0] <= value <= bounds[1]


def calibration_notes() -> Dict[str, str]:
    return {
        "calibration_tag": CALIBRATION_TAG,
        "league_env": (
            f"PPG={LEAGUE_TEAM_PPG}, HFA={HOME_FIELD_POINTS}, score_sd={SCORE_NOISE_SD}, "
            f"plays={LEAGUE_BASE_PLAYS}, pass_rate={LEAGUE_BASE_PASS_RATE}, "
            f"matchup_response={MATCHUP_RESPONSE}, margin_sd={WIN_PROB_MARGIN_SD}"
        ),
        "efficiency": (
            f"ypa={DEFAULT_YPA}, ypc={DEFAULT_YPC}, ypr_te={DEFAULT_YPR_TE}, "
            f"int_rate={DEFAULT_INT_RATE}, pass_td_rate={DEFAULT_PASS_TD_RATE}, "
            f"rush_td_rate_rb={DEFAULT_RUSH_TD_RATE_RB}"
        ),
        "usage": (
            "Absolute target/rush shares with residual 'other' bucket "
            f"(floor={USAGE_OTHER_BUCKET_FLOOR}) — prevents sparse-roster inflation. "
            "v1.3: usage_roles taxonomy + SCRIPT_USAGE_MATRIX + personnel mix."
        ),
        "early_season": (
            "v1.11: weeks 1–4 inflate score/margin SD, soften matchup separation, "
            "widen share volatility + lower Dirichlet concentration "
            "(diagnostics.early_season_uncertainty)."
        ),
        "survivor": (
            "v1.4: team W/L season paths → week win rates + inspectable "
            "save_score / pick_now_score (see survivor.py FORMULA_NOTES)."
        ),
        "harden": (
            "v1.4.1: dual-name injury matching, include_diagnostics explain "
            "payloads, thin-roster/NaN guards, contract docs."
        ),
        "depth_volatility": (
            "v1.5: depth_chart feature/committee RB + clear/murky WR; "
            "committee splits 55/45 or 45/35/20; weekly share drift + rare "
            "role shuffle; injury promotions (see depth_chart.py)."
        ),
        "game_script": (
            "v1.6: score diff + remaining-clock snapshot → script_detail "
            "(large/small lead|deficit), time_bucket, intensity; explicit "
            "pass_rate / early_down_pass_rate / hurry_up; usage matrix "
            "intensity-scaled (see game_script.py + usage_roles.py)."
        ),
        "coaching_tendencies": (
            "v1.8: team coaching profiles (pass_rate_bias, script_aggression, "
            "rz_pass_bias, early_down_pass_bias, two_minute_aggression) overlay "
            "Layer-2 play-mix + RZ pass rate; diagnostics expose coaching_profile "
            "+ tendency_effects (see coaching_tendencies.py)."
        ),
        "real_schedule": (
            "v1.9: default universe uses real 2026 REG schedule (272 games, "
            "weeks 1–18 with byes) from nfl_dp_schedules when present, else "
            "packaged wall-chart JSON. demo=true keeps round-robin for tests."
        ),
        "smoke_polish": (
            "v1.9.2: final smoke/trust check + light UI polish; game-box notes "
            "flag synthetic matchups and bye-week teams in the query."
        ),
        "survivor_planner": (
            "v1.10: multi-week survivor planner — one season-sim pass ranks "
            "each unlocked week (used-team exclusion) and reports joint "
            "path_survival for locked picks (see survivor.py PATH_FORMULA_NOTES)."
        ),
        "deeper_calibration": (
            "v1.11: cal-v2 — wider win-total separation, role/RZ TD tune, "
            "early-season uncertainty (W1–W4). No new major features."
        ),
        "survivor_planner_ux": (
            "v1.12: planner hero slate metrics (avg weekly WP, danger weeks, "
            "best remaining equity, letter grade) + suggest-paths heuristics "
            "(chalk / balanced / contrarian-save). Joint path_survival kept "
            "as advanced secondary. See PATH_FORMULA_NOTES / suggest_survivor_paths."
        ),
        "player_regression": (
            "v1.13: process priors (efficiency vs league, not raw yards/TDs) → "
            "positive/negative/neutral regression posture + drivers; rookie "
            "conservative mean / wide uncertainty; finite team yards/TD caps "
            "so named players cannot overflow the script pool "
            "(see player_regression.py)."
        ),
        "projected_sos": (
            "v1.14: 2026 projected schedule difficulty — mean full-strength "
            "opponent power across the REG slate with HFA; attaches to season "
            "outlook (expected wins / survivor path grades) only. Never rewrites "
            "intrinsic PR / Week-1 blend (see projected_sos.py)."
        ),
        "true_pr_harden": (
            "v1.15: populate is_rookie / draft_round from nflverse roster join "
            "(DB nfl_dp_rosters or packaged flags) so rookie mean-shrink + wider "
            "CV fire live; season-path finite audit dampens named skill aggregates "
            "that exceed summed per-game team pools (see player_regression.py)."
        ),
        "season_coherence": (
            "v1.16: team season pass/rush budgets (strength + coaching + opp D "
            "slate) with league pool renorm; per-team pace_plays; attempt share "
            "of pass plays; offense-coupled YPA; volume regression on priors; "
            "QB1 distribution guards (not 32/32 ≥4000). See season_budgets.py + "
            "scoring_bridge.py. Fantasy preseason-sim totals use the same budget "
            "allocator after QB starter lock."
        ),
        "team_pass_priors": (
            "v1.17: ARI/BAL/SEA multiplicative identity weights on pre-pool "
            "pass-volume residual (Brissett/LaFleur dampen; Doyle dual-threat "
            "restore; Darnold 70/30 + Fleury/Shanahan-tree). Soft floors/ceilings "
            "before 126k two-way renorm; other 29 teams untouched."
        ),
        "offensive_production_stack": (
            "v1.18: on locked pass yards — parallel 60k rush pool; yards→TD "
            "curves with efficiency/defense/scheme residuals; INT rates "
            "1.8–3.4%; receiving/rush allocation via depth usage + rookie "
            "season ramps; conservation renorm (pass≈rec ±1.5%). "
            "See data_platform_nfl/offensive_production_stack.py."
        ),
        "defense_points_wl": (
            "v1.19: team PF from offensive production + FG stub; PA from "
            "schedule-weighted opponent PF × defense_index; yards allowed / "
            "INTs forced / sacks; Pythagorean expected wins renormed to 272. "
            "See data_platform_nfl/defensive_production_stack.py."
        ),
        "defense_variance_lift": (
            "v1.20: multiplicative stretch on PA / sacks / INTs (yards follow "
            "PA residual at 0.6× intensity); soft floors/ceilings; exact "
            "renorm to league totals; Pythagorean wins recomputed from new PA."
        ),
        "offense_variance_lift": (
            "v1.21 Step-1: asymmetric rush stretch (pos ~1.4× / neg ~0.55×) to "
            "~64k league rush pool with soft 1280–2520 team bands; pass pool + "
            "ARI/BAL/SEA weights frozen; PF residual stretch + light PA "
            "re-stretch; Pythagorean wins renormed to 272. Player alpha "
            "re-anchor is Step-2."
        ),
        "alpha_usage_reanchor": (
            "v1.22 Step-2: sticky prior-year elite target/carry shares "
            "(85–90% retention) with cut volume regression for alphas; "
            "WR/RB yard floors (WR12–15 / 1400+ bell-cows); TE compression "
            "when WR1 alpha present; team pass/rush pools locked; "
            "rec≈pass ±1.5%. Snapshot NOT final-locked."
        ),
        "phase2_general_features": (
            "v1.25: remove ARI/BAL/SEA pass identity soft floors/ceilings and "
            "named scheme TD / OL proxy piles; replace with QB rushing profile "
            "(SoT player_id tiers), OL protection index from ol_roles, coaching "
            "tendencies for ARI/SEA/WAS, returning-QB prior travel. League pools "
            "+ Σ wins=272 conserved. See qb_rushing_profile.py / ol_protection.py."
        ),
        "pathA2_usage_prior": (
            "v1.26 Path A2: returning players with material Y−1 volume get "
            "target_share / rush_share blended toward prior-season share of "
            "team targets / rush attempts at usage construction "
            f"(weight={PRIOR_USAGE_ANCHOR_WEIGHT}); no-history keep depth "
            "archetypes; no path-end season-yards blend. Scorecard player "
            "pass/rush/rec prior baselines use the same position filters as "
            "the model pool."
        ),
        "sources": (
            "Recent NFL season shapes (2022–2024) + alignment with "
            "nfl_handicapping_framework HFA/stdev and box-score EFFICIENCY_CV≈0.22. "
            "No fabricated player grades; DB baselines used when present."
        ),
    }
