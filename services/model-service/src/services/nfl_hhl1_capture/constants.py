"""H-HL-1 prospective-capture plumbing pins (t4791u).

This module is schema + validation only. It does not acquire, score, or publish.

Authority (sha256 of filed packets; sha8 MATCH):
  DECISION_RYAN_t4791u  2806545b3ed1b643e4dfdc5e44aea10b50329ae32660d26ec85e36954339d2c8
  COS_ORDER_CURSOR      e0159e6516092e6a81742663c4703bb7b69d03603a7b8691ee3a03409c16681f
  protocol a9f1c28f     a9f1c28f1cbbc0f623603f78b340e09aeff6ecb54926a3fed34e1cf4ee2a242a
  PASS_PROTOCOL         d359ce54ad8c59f005385a226c9a964e183e1e2d724b7244076db76fd14e87c9
  CoS ACCEPT            3d80968f5f3f057c3b49f98df543d82fd94b634851f682fa610dd833a675b7eb
  parent paper          7b4d70ac — UNTOUCHED (not opened, not edited)

Locks: NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen · C10 HOLD ·
Odds HOLD 70c56700 · nowcast OFF. #662/#663 and efficiency STANDBY untouched.
"""

from __future__ import annotations

# --- Authority pins (full sha256; sha8 is the first 8 hex chars) ---

DECISION_SHA256 = "2806545b3ed1b643e4dfdc5e44aea10b50329ae32660d26ec85e36954339d2c8"
ORDER_SHA256 = "e0159e6516092e6a81742663c4703bb7b69d03603a7b8691ee3a03409c16681f"
PROTOCOL_SHA256 = "a9f1c28f1cbbc0f623603f78b340e09aeff6ecb54926a3fed34e1cf4ee2a242a"
PASS_PROTOCOL_SHA256 = "d359ce54ad8c59f005385a226c9a964e183e1e2d724b7244076db76fd14e87c9"
COS_ACCEPT_SHA256 = "3d80968f5f3f057c3b49f98df543d82fd94b634851f682fa610dd833a675b7eb"
PARENT_PAPER_SHA8 = "7b4d70ac"  # UNTOUCHED; full digest not recomputed here

SCHEMA_VERSION = "hhl1-capture-plumbing-v0"
PARSER_VERSION_PLUMBING = "hhl1-capture-plumbing-v0-no-parser"
FACTOR_AVAILABILITY = "availability"

# Protocol §4.3 missingness enum (908b21b4).
MISSINGNESS_OBSERVED = "OBSERVED"
MISSINGNESS_NOT_PUBLISHED = "NOT_PUBLISHED"
MISSINGNESS_SOURCE_DOWN = "SOURCE_DOWN"
MISSINGNESS_NOT_APPLICABLE = "NOT_APPLICABLE"
MISSINGNESS_UNKNOWN = "UNKNOWN"
MISSINGNESS_ENUM = frozenset(
    {
        MISSINGNESS_OBSERVED,
        MISSINGNESS_NOT_PUBLISHED,
        MISSINGNESS_SOURCE_DOWN,
        MISSINGNESS_NOT_APPLICABLE,
        MISSINGNESS_UNKNOWN,
    }
)

# Protocol §5.3 — only admitted capture path (EXISTING BUT UNVERIFIED; not activated).
ADMITTED_SOURCE_ID = "official_nfl_injury_report"
ADMITTED_SOURCE_IDS = frozenset({ADMITTED_SOURCE_ID})
BASELINE_INPUT_SOURCE_ID = "nflverse_snap_counts"  # retro prior-week facts only; not as-of

# R4: these names are sim-input / nowcast-surface labels. They do NOT authorize
# nowcast, and they are not admitted L1 field names while nowcast is OFF.
NOWCAST_SOURCE_IDS = frozenset(
    {
        "nfl_injury_nowcast",
        "injury_nowcast",
        "nowcast",
        "nowcast_surface",
        "fetch_nfl_injury_nowcast",
        "postgres_injuries",
        "postgres_injury_tables",
        "nfl_injuries_table",
    }
)
NOWCAST_FIELD_NAMES = frozenset(
    {
        "injury_nowcast_confidence_home",
        "injury_nowcast_confidence_away",
        "injury_nowcast_freshness_home_hours",
        "injury_nowcast_freshness_away_hours",
        "injury_nowcast_impact_home",
        "injury_nowcast_impact_away",
        "injury_nowcast_offense_multiplier_home",
        "injury_nowcast_offense_multiplier_away",
        "injury_nowcast_defense_multiplier_home",
        "injury_nowcast_defense_multiplier_away",
        "injury_nowcast_source",
        "injury_nowcast_home_drivers",
        "injury_nowcast_away_drivers",
        "injury_nowcast_offense_multiplier",
        "injury_nowcast_defense_multiplier",
    }
)

# O-c: market values enter neither IF nor L1 nor HF.
MARKET_FIELD_NAMES = frozenset(
    {
        "market_line",
        "open",
        "close",
        "consensus",
        "price",
        "market_blend",
        "odds",
        "spread_line",
        "total_line",
        "line_at_decision",
        "dk_spread",
        "american_price",
    }
)

# Report designations that remove a player from expected_starters_asof.
# Questionable is kept (provisional Q-weight; see R3). Inactive lists NOT used.
STARTER_REMOVING_STATUSES = frozenset({"out", "doubtful", "ir", "injured reserve"})
QUESTIONABLE_STATUS = "questionable"

# ---------------------------------------------------------------------------
# R1 — Preserve simulator SHA conflict. Do NOT select either for scoring.
# Protocol pin (kosedge-merge / IMV spot): 9b61c5c3
# Current deploy-vercel tip bytes (1b39f4e9 worktree): 52d9e909
# Capture plumbing must not depend on an unverified simulator.
# Exact executable identity is deferred to a future scoring CLEAR.
# ---------------------------------------------------------------------------
SIMULATOR_SHA_PROTOCOL_PIN = "9b61c5c3"
SIMULATOR_SHA_TIP_BYTES = "52d9e909"
SIMULATOR_EXECUTABLE_IDENTITY = "UNRESOLVED_CONFLICT_9b61c5c3_vs_52d9e909"
# This plumbing does not import or execute nfl_simulator.py.

# ---------------------------------------------------------------------------
# R2 — 2013–2025 calibration claim is UNVERIFIED (code comment only).
# Pin 73cad579 is the sha256 of nfl_injury_nowcast.py on this worktree.
# Freeze as opaque table identity. Do not rebuild historical calibration.
# Do not touch protected samples. Do not import the nowcast module.
# ---------------------------------------------------------------------------
NOWCAST_TABLE_SHA256 = "73cad579ae2c6302b88ce7e5b756470f368deea02abfbabbfca0b3bcfcbca64c"
NOWCAST_TABLE_SHA8 = "73cad579"
CALIBRATION_2013_2025_CLAIM = "UNVERIFIED"  # code comment in 73cad579 L283–290 only

# ---------------------------------------------------------------------------
# R3 — Provisional protocol constants. NOT empirically validated here.
# Rating-window definition is intentionally UNRESOLVED (do not invent).
# ---------------------------------------------------------------------------
DECISION_OFFSET_BEFORE_KICKOFF_MINUTES = 90  # provisional
SNAP_SHARE_THRESHOLD = 0.50  # provisional ≥50% snap share
QUESTIONABLE_KEPT = True  # Q kept at status weight; weight itself not applied here
QUESTIONABLE_STATUS_WEIGHT = "PROVISIONAL_UNVALIDATED"  # do not invent a number for scoring
RATING_WINDOW_DEFINITION = "UNRESOLVED"  # IMV R3: underspecified vs G34; do not invent

# Env names that would attempt to authorize this path. Env cannot lift the CLEAR.
HHL1_ENABLE_ENV_VARS = (
    "HHL1_LIVE_CAPTURE",
    "HHL1_NOWCAST_ENABLED",
    "HHL1_SCORING",
    "HHL1_PUBLISH",
    "HHL1_EXTERNAL_ACQUISITION",
    "HHL1_HISTORICAL_RECONSTRUCTION",
)

# Protocol 4.4(vi) — delta-constant env overrides are FORBIDDEN on a future
# scoring run. Listed for the gate; this CLEAR does not score.
DELTA_CONSTANT_OVERRIDE_ENV_VARS = (
    "NFL_INJURY_MAX_RAW_OFFENSE",
    "NFL_INJURY_MAX_RAW_DEFENSE",
    "NFL_INJURY_IMPACT_SCALE",
    "NFL_INJURY_CONFIDENCE_SCALE",
    "NFL_INJURY_ROWS_FOR_FULL_CONFIDENCE",
    "NFL_INJURY_HALFLIFE_HOURS",
    "NFL_INJURY_STALE_HOURS",
    "NFL_INJURY_STALE_FLOOR",
)

# Truthy strings that cannot authorize a disabled path.
TRUTHY_ENV_VALUES = frozenset({"1", "true", "yes", "y", "on"})
