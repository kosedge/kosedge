"""NFL_JOINT_CONTRACT_V1 pins. CERT=0. SYNTHETIC_ONLY. Not a fitted family."""

from __future__ import annotations

SCHEMA_VERSION = "nfl-joint-contract-v1-literal-law-v1"
CONTRACT_ID = "NFL_JOINT_CONTRACT_V1"
CONTRACT_HASH = "4f2c9e2b"
ORDER_HASH = "ce74d8eb"
OWNER_CLEAR = "f1fb6735"
PROTOCOL = "ed10e80f"
SCOPE_ID = "chief-nflgreen-overnight-ops-20261102-0330"
TASK_ID = "chief-nflgreen-overnight-ops-20261102-0330-successor-joint-literal-law"
PACKAGE = "NFL_JOINT_CONTRACT_V1_LITERAL_LAW"
CERT = 0
DATA_LABEL = "SYNTHETIC"
ELIGIBILITY = "UNQUALIFIED"

KNOWN_SETTLEMENT_PROFILE = "SYNTHETIC_LAW_IDENTITY_V1"

# Task-bound oracle (fiction; equal weights). Not historical. Not fitted.
ORACLE_PAIRS = ((24, 21), (21, 24), (20, 20), (27, 21))
ORACLE_WEIGHTS = (0.25, 0.25, 0.25, 0.25)
ORACLE_HOME_SPREAD = -3.0
ORACLE_TOTAL = 45.0

EXPECTED_ML = {"home_win": 0.5, "away_win": 0.25, "tie": 0.25}
EXPECTED_MEANS = {"margin": 1.5, "total": 44.5}
EXPECTED_SPREAD = {"cover": 0.25, "push": 0.25, "loss": 0.5}
EXPECTED_TOTAL = {"over": 0.25, "push": 0.5, "under": 0.25}

SYNTH_IDENTITY = {
    "game_id": "2026_99_SYN_TST_JNT",
    "season": 2026,
    "week": 99,
    "season_type": "REG",
    "home": "SYN",
    "away": "TST",
    "kickoff_ts": "2026-11-08T18:00:00Z",
    "venue": "SYNTH-JOINT-VENUE",
}

FEATURE_CATALOG = (
    "literal_joint_pairs",
    "literal_equal_weights",
)

FREEZE_REL = "data/ops/nfl-joint-contract-v1/FREEZE_RECEIPT.json"
ORACLE_REL = "data/ops/nfl-joint-contract-v1/ORACLE.json"
SCHEMA_REL = "data/ops/nfl-joint-contract-v1/SCHEMA.json"
