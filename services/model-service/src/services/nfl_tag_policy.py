"""Central Edge Board Tag Policy thresholds (2026-08-11).

Doctrine: we bet prices, not teams. Tags are mechanical.
Edge / Tag = KEI vs best available market only.
Edge magnitude and confidence stay separate — never one mysterious score.

Consumed by ``nfl_decision_engine`` (labels + play-to). Do not duplicate bands.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

WeekRegime = Literal["early", "standard", "inseason", "late"]

BREAKEVEN_ATS_MINUS_110 = 0.5238  # ≈ 52.38% at -110

# ---------------------------------------------------------------------------
# Cover-probability bands (standard -110)
# ---------------------------------------------------------------------------
COVER_PASS_MAX = 0.53  # < 53% → PASS
COVER_LEAN_MAX = 0.54  # 53–54% → LEAN
COVER_PLAY_MAX = 0.56  # 54–56% → PLAY
COVER_STRONG_MAX = 0.58  # 56–58% → strong / BEST VALUE only with high conf
COVER_MODEL_WARNING = 0.60  # 60%+ vs mature markets → ops/log flag

# ---------------------------------------------------------------------------
# Side point bands
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SidePointThresholds:
    """|KEI − market| bands for sides."""

    pass_max: float  # |edge| < pass_max → PASS
    lean_max: float  # upper end of LEAN band (gap to play_min stays LEAN)
    play_min: float  # |edge| ≥ play_min → at least PLAY
    strong_min: float  # |edge| ≥ strong_min → STRONG PLAY candidate


# Weeks 1–2 (tighter / higher uncertainty) — 2026-08-11 brief
EARLY_SIDE = SidePointThresholds(
    pass_max=1.25,
    lean_max=1.75,
    play_min=2.25,
    strong_min=3.25,
)

# Midseason baseline (after Week 2)
STANDARD_SIDE = SidePointThresholds(
    pass_max=1.0,
    lean_max=1.5,
    play_min=2.0,
    strong_min=3.0,
)

# Weeks 6–12 / 13+ — same baseline magnitudes; confidence handles noise
INSEASON_SIDE = STANDARD_SIDE
LATE_SIDE = INSEASON_SIDE

# ---------------------------------------------------------------------------
# Totals point bands (+ week1_boost)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TotalPointThresholds:
    pass_max: float
    lean_max: float
    play_min: float
    strong_min: float


# Baseline totals (after Week 2)
BASELINE_TOTAL = TotalPointThresholds(
    pass_max=1.5,
    lean_max=2.0,
    play_min=2.5,
    strong_min=3.5,
)

# Week 1–2: +0.25 pt on each band → 1.75 / 2.25 / 2.75 / 3.75
WEEK1_TOTAL_BOOST = 0.25

EARLY_TOTAL = TotalPointThresholds(
    pass_max=BASELINE_TOTAL.pass_max + WEEK1_TOTAL_BOOST,
    lean_max=BASELINE_TOTAL.lean_max + WEEK1_TOTAL_BOOST,
    play_min=BASELINE_TOTAL.play_min + WEEK1_TOTAL_BOOST,
    strong_min=BASELINE_TOTAL.strong_min + WEEK1_TOTAL_BOOST,
)

# Back-compat aliases used by older call sites / tests
TOTAL_PASS_MAX = BASELINE_TOTAL.pass_max
TOTAL_LEAN_MAX = BASELINE_TOTAL.lean_max
TOTAL_PLAY_MAX = 3.0  # PLAY band ceiling before strong (gap stays PLAY)
TOTAL_STRONG_MIN = BASELINE_TOTAL.strong_min

# ---------------------------------------------------------------------------
# Confidence floors (separate from edge magnitude)
# ---------------------------------------------------------------------------
CONFIDENCE_PLAY_MIN = 0.55
CONFIDENCE_BEST_BET_MIN = 0.75
CONFIDENCE_TIER_BASE = 0.72

# ---------------------------------------------------------------------------
# Key numbers
# ---------------------------------------------------------------------------
SPREAD_KEY_NUMBERS = (3.0, 7.0, 10.0, 14.0)
TOTAL_KEY_NUMBERS = (37.0, 41.0, 44.0, 47.0, 51.0)


def week_regime(week: Optional[int]) -> WeekRegime:
    """Week from schedule pack. Weeks 1–2 → early; after Week 2 → baseline."""
    if week is None:
        return "early"
    w = int(week)
    if w <= 2:
        return "early"
    if 6 <= w <= 12:
        return "inseason"
    if w >= 13:
        return "late"
    return "standard"


def side_thresholds_for_week(week: Optional[int]) -> SidePointThresholds:
    regime = week_regime(week)
    if regime == "early":
        return EARLY_SIDE
    if regime in ("inseason", "late"):
        return INSEASON_SIDE
    return STANDARD_SIDE


def total_thresholds_for_week(week: Optional[int]) -> TotalPointThresholds:
    if week_regime(week) == "early":
        return EARLY_TOTAL
    return BASELINE_TOTAL
