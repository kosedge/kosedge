"""t4673u CONTRACT SPEC — Item 4 W8 missingness guarantees.

NOT collected by default pytest. Does NOT enable production paths.
Does NOT invent W8 official rows. Does NOT SELECT nfl_dp_injuries.

Parent: Codex 88a08cae G-INVENT-W8 + G-DUP-INJURY · IMV RETURN 75141507 invent W8.
Official-W8 SoT: NONE today. PRESENT is forbidden from nflverse designations.
"""

from __future__ import annotations

SEALED_INJURY_PACK_SHA256 = (
    "0c29ceea500f34dd326e3b8879372fc6f2b6ea821ac72613ce4e35cadf013a97"
)
SEALED_RESTORE_ORACLE_SHA8 = "6d303b90"
REQUIRED_G3_FLAGS = ("w8_official_injury_report", "injury_as_of_week8", "injury_as_of_week8_away")

# Three writers. Tests must CALL them. Injecting {as_of_week: 7} is not C2.
WRITERS = (
    "_injury_impacts",
    "_materialize_current_packs",
    "audit_week_inputs",
)


def spec_t_g3_1_empty_w8_stubs_not_week8() -> None:
    """T-G3-1: W7 designations + week-8 empty stubs → as_of_week != 8.

    Call _injury_impacts (not a pre-built dict).
    Assert w8_official_report=MISSING and G3 flags still appended.

    PROTECTION-REMOVED MUTATION:
      restore as_of_week = max(week) on empty stubs (run_w8 :325)
      → as_of_week==8 drops injury_as_of_week8 (:465-468) → test FAIL.

    VACUITY MUTATION (forbidden):
      test_c2_g3_w8_official_missing_not_invented  # injects as_of_week 7/6
    """


def spec_t_g3_2_nflverse_w8_designations_not_present() -> None:
    """T-G3-2: a week-8 designated nflverse row must NOT mint PRESENT.

    Call _injury_impacts AND the pack writer.
    Official remains MISSING. G3 flags remain.

    PROTECTION-REMOVED MUTATION:
      restore PRESENT if latest_week >= WEEK (run_w8 :691) → test FAIL.
    """


def spec_t_g3_3_completeness_not_from_pack_week() -> None:
    """T-G3-3: pack week==8 is not official PRESENT.

    Completeness official evidence stays MISSING unless a pinned official-W8
    SoT exists (none today).

    PROTECTION-REMOVED MUTATION:
      PRESENT if inj_week == week (audit_w8_input_completeness_t4605u.py:270-272).
    """


def spec_t_g3_4_one_fixture_three_writers_agree() -> None:
    """T-G3-4: one hashed parquet slice → one documented function of as_of /
    pack week / official flag / completeness evidence. Disagreement is FAIL.

    VACUITY MUTATION: assert each writer 'returns a dict'.
    """


def spec_t_g3_5_sealed_restore_still_honest_c4() -> None:
    """T-G3-5: C2_sealed_restore_oracle 6d303b90 — 14/14 flags, week=7,
    pack 0c29ceea…, MISSING. Dropping flags to green T-G3-1 is C4 FAIL.
    """


def spec_t_g3_6_no_warehouse_injury_import() -> None:
    """T-G3-6: import-graph walk of run_w8_research_forecast_t4564u.py
    excludes nfl_injury_nowcast / FROM nfl_dp_injuries.

    VACUITY MUTATION: grep the one script file only.
    PROTECTION-REMOVED MUTATION: import fetch_nfl_injury_nowcast → test FAIL.
    """
