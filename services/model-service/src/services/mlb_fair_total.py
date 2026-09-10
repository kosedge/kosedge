"""Certified MLB fair-total / KEI-total quantization.

Locked product policy (do not invent a different board grain):

    fair_*_total = nearest half-run of the matching *_total_mean

That is ``round(mean * 2) / 2`` (Python 3 half-even at exact .25 / .75).
Full-game ``fg_total_mean`` and first-five ``f5_total_mean`` are quantized
independently — they are not the same number and must not be swapped.

This is **not** a stub constant. A slate clustered around 9.09–9.11 will
honestly paint every KEI total as 9.0; means that cross a half-run boundary
must produce a different board total (8.24 → 8.0, 8.26 → 8.5, 9.26 → 9.5).

Provenance token: ``nearest_half_run``.
"""

from __future__ import annotations

from typing import Optional

MLB_FAIR_TOTAL_QUANTIZATION = "nearest_half_run"
MLB_FAIR_TOTAL_TICK = 0.5


def quantize_mlb_fair_total(mean: Optional[float]) -> Optional[float]:
    """Nearest half-run (0.5) of a continuous run total mean.

    Smoking gun (2026-09-10 slate): ``fg_total_mean`` ≈ 9.09 painted
    ``fair_fg_total`` / KEI 9 via this rule — not a hardcoded 9.
    """
    if mean is None:
        return None
    value = float(mean)
    if value != value:  # NaN
        return None
    return round(value * 2.0) / 2.0
