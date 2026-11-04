"""Source pins Worker B consumed. Read-only. #714 is PARTIAL, not a base."""

from __future__ import annotations

from src.services.nfl_owned_market_v1.constants import (
    PIN_713_TIP,
    PIN_714_IS_BASE,
    PIN_714_PARTIAL,
    PIN_BASE,
    PIN_R6_A,
    PIN_R6_B,
)


def source_pins() -> dict[str, object]:
    return {
        "r6_a": PIN_R6_A,
        "r6_b": PIN_R6_B,
        "gate_713_tip": PIN_713_TIP,
        "pr_714_partial": PIN_714_PARTIAL,
        "pr_714_is_base": PIN_714_IS_BASE,
        "base_deploy_vercel": PIN_BASE,
        "timing_law": "seal_utc=cutoff_utc=kickoff-60; available_at/observed_at strictly precede seal",
    }
