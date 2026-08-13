"""Garbage-time / competitive play weights for CFB PBP.

Defaults are backtestable knobs, not a claim of a unique true filter.
SportsDataverse ``start.TimeSecsRem`` is **seconds remaining in the current
half** (0–1800), not game clock. Pass ``half`` (1/2) so 2nd-half late leads
down-weight correctly.

FCS plays are **not** deleted here — callers flag them.
"""

from __future__ import annotations

from typing import Any, Mapping

# |score diff| below this is always competitive (full weight).
COMPETITIVE_MARGIN = 16.0
# |score diff| at/above this is a blowout when time is also short.
DEEP_MARGIN = 24.0
# 2nd-half seconds remaining below this starts the late-game taper (12:00).
LATE_SECS = 720
# 2nd-half seconds remaining for deep-garbage floor (5:00).
DEEP_SECS = 300
# Under-two + this margin → extra down-weight (either half).
UNDER_TWO_MARGIN = 8.0
UNDER_TWO_MULT = 0.40
MIN_WEIGHT = 0.10
# First-half blowouts still count; only a mild trim.
FIRST_HALF_BLOWOUT_WEIGHT = 0.85

DEFAULTS = {
    "competitive_margin": COMPETITIVE_MARGIN,
    "deep_margin": DEEP_MARGIN,
    "late_secs": LATE_SECS,
    "deep_secs": DEEP_SECS,
    "under_two_margin": UNDER_TWO_MARGIN,
    "under_two_mult": UNDER_TWO_MULT,
    "min_weight": MIN_WEIGHT,
    "first_half_blowout_weight": FIRST_HALF_BLOWOUT_WEIGHT,
    "time_secs_rem_unit": "seconds_remaining_in_half",
}


def game_secs_remaining(time_secs_rem: Any, half: Any = None) -> float:
    """Approximate seconds left in the game from half-clock + half number."""
    try:
        t = max(0.0, float(time_secs_rem or 0.0))
    except (TypeError, ValueError):
        t = 0.0
    try:
        h = int(float(half)) if half not in (None, "") else 2
    except (TypeError, ValueError):
        h = 2
    if h <= 1:
        return t + 1800.0
    return t


def garbage_weight(
    *,
    pos_score_diff: Any = 0,
    time_secs_rem: Any = 1800,
    under_two: Any = False,
    half: Any = None,
) -> float:
    """Competitive = 1.0; decided / deep garbage → progressive down-weight."""
    try:
        abs_d = abs(float(pos_score_diff or 0.0))
    except (TypeError, ValueError):
        abs_d = 0.0
    t = game_secs_remaining(time_secs_rem, half)
    ut = bool(under_two) and str(under_two).lower() not in {"0", "false", "f"}

    try:
        h = int(float(half)) if half not in (None, "") else 2
    except (TypeError, ValueError):
        h = 2

    if abs_d < COMPETITIVE_MARGIN:
        w = 1.0
    elif h <= 1:
        w = FIRST_HALF_BLOWOUT_WEIGHT if abs_d >= DEEP_MARGIN else 1.0
    elif t > LATE_SECS:
        w = 1.0 if abs_d < DEEP_MARGIN else 0.70
    else:
        lead_scale = min(1.0, (abs_d - COMPETITIVE_MARGIN) / 16.0)
        time_scale = 1.0 - (t / float(LATE_SECS))
        w = 1.0 - 0.85 * lead_scale * time_scale
        w = max(MIN_WEIGHT, w)

    if abs_d >= DEEP_MARGIN and t <= DEEP_SECS and h >= 2:
        w = min(w, 0.15)

    if ut and abs_d >= UNDER_TWO_MARGIN:
        w *= UNDER_TWO_MULT

    return max(MIN_WEIGHT, min(1.0, float(w)))


def weight_play(play: Mapping[str, Any]) -> float:
    return garbage_weight(
        pos_score_diff=play.get("pos_score_diff"),
        time_secs_rem=play.get("start.TimeSecsRem", play.get("TimeSecsRem")),
        under_two=play.get("under_2", play.get("Under_two")),
        half=play.get("half"),
    )
