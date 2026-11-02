"""t4673u CONTRACT SPEC — Item 2 fixture/builder pins (no C1 bypass).

NOT collected by default pytest. Does NOT enable production paths.
Does NOT download nflverse. Does NOT open DATABASE_URL. Does NOT import odds_api.

Parent: Codex 88a08cae G-C1-BYPASS + G-C1-EPA-PARTIAL · IMV RETURN 75141507 C1/C3 bypass.
"""

from __future__ import annotations

C3_PINS = {
    "depth": "550e1a8d3daef00ca963c91e30849ce368ec631df06302305c64faa69fab2e1d",
    "injury": "0c29ceea500f34dd326e3b8879372fc6f2b6ea821ac72613ce4e35cadf013a97",
    "epa": "cb1fe8c5e0495c417af3dc70f83cf4c419c1c1761b2dd233bc8546ad3face2c2",
    "schedule": "d88ae73440d3da87198ddb9d8986e0a19773cd3626215e495138907c44ff43fe",
}

# Direct NflGameInputs(**json) → simulate_nfl_game is an engine-unit oracle only.
# It is NOT sufficient for C1 PASS after this prep.
FORBIDDEN_AS_SOLE_C1 = "_sim_from_fixture / NflGameInputs(**fx['inputs'])"


def spec_t_c1_pin_1_builder_executed() -> None:
    """T-C1-PIN-1: at least one C1 path per CONSUMED family calls the builder.

    EPA      → _build_current_strength
    injury   → _injury_impacts
    rest     → _load_canonical_week + _rest_days

    Side-effect the unit helper cannot fake:
      EPA source string, or w8_official_report=MISSING from _injury_impacts,
      or rest source != injected 7.0.

    VACUITY MUTATION (forbidden):
      assert "_build_current_strength" in W8_SCRIPT.read_text()  # today's C4

    PROTECTION-REMOVED MUTATION:
      C1 helper returns to NflGameInputs(**fx) only → test FAIL.
    """


def spec_t_c1_pin_2_c3_sha_refuse() -> None:
    """T-C1-PIN-2: one-byte EPA pack swap → SystemExit input_sha_mismatch.

    No silent nflverse refresh. No slate row written.

    VACUITY MUTATION: grep "sha256" in the script.
    PROTECTION-REMOVED MUTATION: delete the sha check; always _download.
    """


def spec_t_c1_pin_3_epa_totals_overlay() -> None:
    """T-C1-PIN-3: perturb only off_epa_per_play / *_epa_5g → totals overlay moves.

    Today's C1_epa_home_boost omits every *_epa_5g field (G-C1-EPA-PARTIAL).
    Offense-index pair remains the index oracle.

    PROTECTION-REMOVED MUTATION: omit *_epa_5g again → declared totals component
    does not move → test FAIL.
    """


def spec_t_c1_pin_4_fixture_manifest() -> None:
    """T-C1-PIN-4: new builder-path fixtures get FIXTURES.sha256 rows.

    Changing a fixture without updating the manifest fails.
    """
