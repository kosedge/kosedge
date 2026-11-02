"""t4673u CONTRACT SPEC — Item 1 C1-STDEV market invariance.

NOT collected by default pytest (filename is *.spec.py, not test_*.py).
Does NOT enable production paths. Does NOT import Odds / warehouse / W8 emit.
Implementation after Ryan CLEAR copies these asserts into the #645 oracle file.

Parent: Codex 88a08cae G-C1-STDEV · IMV RETURN 75141507 C1-STDEV.
Landing (a) INVARIANT is the default. Landing (b) needs CLEAR.

Vacuity law: a suite that keeps only the means asserts (today's
test_c1_injury_impact_field_consumed_means_gated) is RETURN.
"""

from __future__ import annotations

# Hashed #645 fixtures (do not re-mint; re-hash on the repair tip).
C1_BASE_SHA8 = "fc0f79f8"
C1_INJ_SHA8 = "ef31a571"
SEED = 4643
SIMS = 1200

# Codex 88a08cae independent re-run (seed 4643 / 1200). Pin for reproduce.
# Not a new experiment in this prep PR.
CODEX_OBSERVED = {
    "C1_base": {
        "spread_home": -0.14,
        "home_wp": 0.4892,
        "mean_home": 23.175,
        "injuries_depth.margin": 0.0,
        "error_regime.stdev_widen": 0.2182,
    },
    "C1_inj_impact_only": {
        "spread_home": -0.13,  # WRONG COMPONENT — must not remain after B1
        "home_wp": 0.4892,
        "mean_home": 23.175,
        "injuries_depth.margin": 0.0,
        "error_regime.stdev_widen": 0.2387,
    },
}


def spec_t_c1_stdev_1_market_equality_landing_a() -> None:
    """T-C1-STDEV-1: hashed C1-INJ pair leaves markets + stdev_widen unchanged.

    After B1 landing (a), assert:
      markets.spread_home                 equal
      markets.home_win_prob               equal
      posted total / mean_total           equal
      error_regime.raw_signals.stdev_widen equal
      injuries_depth.margin_points        == 0.0
      mean_home_points / mean_away_points equal

    PROTECTION-REMOVED MUTATION (must FAIL the test):
      keep error_regime injury term ungated (framework.py:837-861 raw impact)
      → spread_home and/or stdev_widen move (Codex −0.14 → −0.13).

    VACUITY MUTATION (forbidden / RETURN):
      drop market + stdev asserts; keep only means. That is the current green test.
    """


def spec_t_c1_stdev_2_identity() -> None:
    """T-C1-STDEV-2: impact identity still 0.45 / 0.05 on the hashed pair.

    VACUITY MUTATION: accept any impact values as long as markets match.
    """


def spec_t_c1_stdev_3_totals_overlay_conf_gated() -> None:
    """T-C1-STDEV-3: totals-overlay stdev_points == 0.0 at conf=0.

    Already gated at nfl_simulator.py:438-447. Keep it. Do not feed raw impact.

    PROTECTION-REMOVED MUTATION: multiply stdev by raw impact (no injury_conf).
    """


def spec_t_c1_stdev_4_r1_not_current_consume() -> None:
    """T-C1-STDEV-4: confidence-injected mean-effect test is REPAIR_TARGET only.

    test_c1_injury_with_confidence_moves_means_repair_target already passes
    because the engine honors injected confidence. Builder does not set it.
    Do not cite as C1 evidence of current consume.
    """
