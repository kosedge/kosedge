"""Frozen research blend — two complete margins, no extra HFA.

margin_mu_q2s = 0.5 * IF.margin_mu + 0.5 * q2_pm_new

w=0.5 is a predeclared research candidate. It is NOT fitted and is NOT
a proven optimum. Do not add q2_hfa (already inside sealed q2_pm_new
via a_q2). Do not emit candidate win/ATS/OU probabilities.
"""

from __future__ import annotations

import math
from typing import Any

# Predeclared research candidate. Not a fit. Not an optimum claim.
Q2S_WEIGHT = 0.5
Q2S_WEIGHT_NOTE = (
    "w=0.5 is a predeclared research candidate — NOT fitted or proven optimum"
)


class BlendRefuse(ValueError):
    """Fail-closed blend (never impute)."""


def margin_mu_q2s(
    if_margin_mu: Any,
    q2_pm_new: Any,
    *,
    w: float = Q2S_WEIGHT,
    extra_hfa: float = 0.0,
) -> float:
    """Blend two complete home−away margins. extra_hfa must be 0."""
    if extra_hfa != 0.0:
        raise BlendRefuse("Add NO extra HFA/q2_hfa; blend two complete margins")
    if w != Q2S_WEIGHT:
        raise BlendRefuse("w is frozen at the predeclared research candidate 0.5")
    try:
        if_m = float(if_margin_mu)
        q2_m = float(q2_pm_new)
    except (TypeError, ValueError) as exc:
        raise BlendRefuse("non-finite complete margin") from exc
    if not math.isfinite(if_m) or not math.isfinite(q2_m):
        raise BlendRefuse("non-finite complete margin")
    return Q2S_WEIGHT * if_m + Q2S_WEIGHT * q2_m


def coordinate_reverse_same_game(margin: float) -> float:
    """Same event, flip reporting coordinates (home−away → away−home)."""
    return -float(margin)


def venue_swap_q2_pm(a_q2: float, b_q2: float, rating_diff: float) -> tuple[float, float]:
    """Different event: keep home intercept. Returns (orig, swapped).

    orig = a + b*d ; swapped = a − b*d ; sum = 2a.
    Do NOT force swapped == −orig (that drops the intercept).
    """
    orig = float(a_q2) + float(b_q2) * float(rating_diff)
    swapped = float(a_q2) + float(b_q2) * (-float(rating_diff))
    return orig, swapped
