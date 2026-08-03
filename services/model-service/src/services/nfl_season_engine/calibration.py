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
CALIBRATION_TAG = "nfl-season-engine-cal-v1"
ENGINE_VERSION = "nfl-season-engine-v1.1-calibrated"

# ---------------------------------------------------------------------------
# League environment (team / game script)
# Sources: recent NFL regular-season averages (~43–45 game totals, ~22 PPG,
# ~62–65 offensive plays/team, pass rate ~57–59%). HFA / score SD aligned with
# nfl_handicapping_framework priors (home_field_points≈1.05, base_score_stdev≈9.8).
# ---------------------------------------------------------------------------
LEAGUE_TEAM_PPG = 21.8
HOME_FIELD_POINTS = 1.05
SCORE_NOISE_SD = 9.8
WIN_PROB_MARGIN_SD = 13.8
LEAGUE_BASE_PLAYS = 63.0
LEAGUE_BASE_PASS_RATE = 0.58
EXPECTED_POINTS_CLAMP = (9.0, 38.0)
PACE_PLAYS_CLAMP = (50.0, 76.0)

# Strength path evolution — softened vs foundation so win totals do not
# explode/compress mid-season from over-reactive updates.
STRENGTH_UPDATE_RATE = 0.025
STRENGTH_MEAN_REVERT = 0.016
STRENGTH_NOISE = 0.010
STRENGTH_CLAMP = (0.70, 1.35)

# ---------------------------------------------------------------------------
# Production efficiency (per attempt / carry / reception)
# League-ish rates; elite demo names get mild talent bumps in loaders.
# INT% ~1.8% of attempts (recent NFL starter band); pass TD% ~4.1%;
# rush TD% ~2.7%/carry for primary RBs; rec TD% ~5.5%/reception WR/TE.
# ---------------------------------------------------------------------------
EFFICIENCY_CV_PASS = 0.22
EFFICIENCY_CV_RUSH = 0.24
EFFICIENCY_CV_REC = 0.23
CATCH_RATE_NOISE = 0.055

DEFAULT_YPA = 7.05
DEFAULT_YPC = 4.20
DEFAULT_YPR_WR = 11.8
DEFAULT_YPR_TE = 10.6
DEFAULT_YPR_RB = 7.8

DEFAULT_CATCH_WR = 0.615
DEFAULT_CATCH_TE = 0.675
DEFAULT_CATCH_RB = 0.72

DEFAULT_PASS_TD_RATE = 0.041
DEFAULT_RUSH_TD_RATE_RB = 0.027
DEFAULT_RUSH_TD_RATE_QB = 0.045
DEFAULT_REC_TD_RATE = 0.055
DEFAULT_REC_TD_RATE_RB = 0.035
DEFAULT_INT_RATE = 0.018
ELITE_INT_RATE = 0.015

# Usage residual: treat role shares as absolute fractions of team volume.
# Sparse demo/depth rosters must NOT renormalize to 100% (that was inflating
# WR1/RB1 production into unrealistic ranges).
USAGE_OTHER_BUCKET_FLOOR = 0.08
DIRICHLET_RUSH_CONCENTRATION = 32.0
DIRICHLET_TARGET_CONCENTRATION = 36.0

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
SEASON_SANITY = {
    "qb_pass_yards": (2800.0, 5200.0),
    "qb_ints": (5.0, 18.0),
    "rb1_rush_yards": (600.0, 1600.0),
    "wr1_rec_yards": (500.0, 1400.0),
    "wr1_receptions": (45.0, 120.0),
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


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
            "rec_td_rate": DEFAULT_REC_TD_RATE,
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
    source_suffix: str = "league_efficiency_v1",
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
            f"plays={LEAGUE_BASE_PLAYS}, pass_rate={LEAGUE_BASE_PASS_RATE}"
        ),
        "efficiency": (
            f"ypa={DEFAULT_YPA}, ypc={DEFAULT_YPC}, int_rate={DEFAULT_INT_RATE}, "
            f"pass_td_rate={DEFAULT_PASS_TD_RATE}, rush_td_rate_rb={DEFAULT_RUSH_TD_RATE_RB}"
        ),
        "usage": (
            "Absolute target/rush shares with residual 'other' bucket "
            f"(floor={USAGE_OTHER_BUCKET_FLOOR}) — prevents sparse-roster inflation."
        ),
        "sources": (
            "Recent NFL season shapes (2022–2024) + alignment with "
            "nfl_handicapping_framework HFA/stdev and box-score EFFICIENCY_CV≈0.22. "
            "No fabricated player grades; DB baselines used when present."
        ),
    }
