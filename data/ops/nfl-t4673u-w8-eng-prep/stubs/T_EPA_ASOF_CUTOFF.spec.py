"""t4673u CONTRACT SPEC — Item 3 historical EPA as-of cutoff.

NOT collected by default pytest. Does NOT enable production paths.
Does NOT download nflverse. Does NOT open the 2025 prior pack in a live run.

Parent: Codex 88a08cae G-TIME-EPA + G-LIVE-DOWNLOAD + G-C2-EPA-PRIOR
        · IMV RETURN 75141507 time leakage / stale grain.

TNF pin (not a free pass): 2026-W08-CAR@GB kickoff 2026-10-30T00:15:00Z.
Sealed Oct 28 emit is pre-kickoff. This is a re-run / future-download hole.
"""

from __future__ import annotations

PRIOR_2025_PACK = "nfl_team_efficiency_backbone_2026.json"
PRIOR_2025_AS_OF = "2026-08-08"
PRIOR_SEASON = 2025
C3_EPA_SHA256 = "cb1fe8c5e0495c417af3dc70f83cf4c419c1c1761b2dd233bc8546ad3face2c2"
FIRST_W8_KICKOFF = "2026-10-30T00:15:00Z"


def spec_t_epa_asof_1_week8_excluded_or_refused() -> None:
    """T-EPA-ASOF-1: week=8 extreme EPA (+5.0) must not enter W1–W7 strength.

    Pass iff exclude (indices unchanged vs week<=7-only frame) OR refuse
    (SystemExit naming week-8). Source must not claim w1_w7 if week-8 used.

    PROTECTION-REMOVED MUTATION:
      delete week<=7 filter (today: only team_df['week'].max() < 7 → exit).
      Extreme week-8 EPA moves strength → test FAIL.

    VACUITY MUTATION (forbidden):
      assert team_df['week'].max() >= 7  # stays green when week-8 leaks
    """


def spec_t_epa_asof_2_epa_5g_grain_flag() -> None:
    """T-EPA-ASOF-2: do not silently store season-to-date in *_epa_5g.

    After builder: fields unset OR notes include epa_grain=season_to_date_w1_w7
    (or fields renamed). Silent 5g name is FAIL.

    PROTECTION-REMOVED MUTATION:
      write season EPA into home_off_epa_5g with no flag (today :433-436).
    """


def spec_t_epa_asof_3_builder_empty_not_2025_prior() -> None:
    """T-EPA-ASOF-3: _build_current_strength(empty / week.max<7) SystemExit
    MISSING current strength AND the 2025 pack file is never opened.

    Probe: wrap open / Path.read_text on nfl_team_efficiency_backbone_2026.json.

    VACUITY MUTATION (forbidden):
      test_c2_epa_missing_refuses_to_sim  # injects strength={} into _simulate_one

    PROTECTION-REMOVED MUTATION:
      one-line fallback onto the 2025 pack → test FAIL.
    """


def spec_t_epa_asof_4_kickoff_not_a_free_pass() -> None:
    """T-EPA-ASOF-4: forecast_ts before TNF kickoff + week-8 EPA rows still
    fails T-EPA-ASOF-1. Do not weaken _g18_artifact post-kickoff forecast_ts block.
    """
