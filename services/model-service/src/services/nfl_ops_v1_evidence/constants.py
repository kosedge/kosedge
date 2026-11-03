"""NFL_OPS_V1 evidence-manifest pins. CERT=0. Synthetic only."""

from __future__ import annotations

from typing import FrozenSet, Tuple

SCHEMA_VERSION = "nfl-ops-v1-evidence-manifest-v1"
PACKAGE = "NFL_OPS_V1_EVIDENCE_GATE"
AUTHORITY = "t5245u"
OWNER_CLEAR = "f1fb6735"
PROTOCOL = "ed10e80f"
JOINT_CONTRACT = "4f2c9e2b"
SCOPE_ID = "chief-nflgreen-overnight-ops-20261102-0330"
OWNER = "Primary A"
PROFILE = "SYNTHETIC_WFIX_AB_CHAIN"
CERT = 0
DATA_LABEL = "SYNTHETIC"

# Accepted W-FIX lineage (do not fabricate allow objects).
LINEAGE_707_TIP = "f2c72e8bf7aa3e3f219ca3b48c76b68e7b5a4236"
LINEAGE_706_TIP = "644c517d1b95000105c74269ee54f8e1c63923e4"
LINEAGE_706_PIN = "12bc48c0f44531673c1d2df76b3b62bb9c99c45d"
UTILITY_700_TIP = "9d436eb1cebc29fc1f91bdb3306dbe3dd393805d"
UTILITY_701_TIP = "455a8e43eccc1ed2c39e91821790cce968ffdadb"
BASE_DEPLOY_VERCEL = "f5e3bb58ccbe5a8892fed2a01f347c2308394a2f"

PINNED_CHAIN_DIGEST = "27f32649050578108720b2ff26eacebadb92c7324f1930661c88b8f1ce6e6124"
PINNED_CAPTURE_ID = "adc143a4b27d94bce436c5de5bc642f8c200050f20fa6bf57e01b831e6874877"
PINNED_FORECAST_ID = "3c68732d8757ff695cd1fee3dbeb45ac22bdbb20be0e4a4ea5806e86600d064f"
PINNED_GAME_ID = "2026_99_TST_SYN"
PINNED_TEAM = "SYN"
PINNED_AWAY = "TST"
PINNED_HOME = "SYN"
PINNED_SEASON = 2026
PINNED_WEEK = 99
PINNED_PERIOD = "full_game"
PINNED_POINT_MARGIN = 3.0
PINNED_LINE = -3.0
PINNED_PRICE = -110
PINNED_OFFENSE_RAW = 0.12
PINNED_DEFENSE_RAW = -0.08
PINNED_OFFENSE_MULT = 0.97
PINNED_DEFENSE_MULT = 1.03
PINNED_N = 1

PINNED_OUTPUT_REL = "data/ops/t5194u-wfix-a-chain/positive-output.json"
PINNED_OUTPUT_SHA_REL = "data/ops/t5194u-wfix-a-chain/positive-output.sha256"

EVIDENCE_LABELS: FrozenSet[str] = frozenset(
    {
        "EXECUTED_HERE",
        "INDEPENDENT_EXECUTION",
        "SOURCE_INSPECTION",
        "REPORTED_ONLY",
        "NOT_RUN",
    }
)

TYPED_REF_KINDS: FrozenSet[str] = frozenset({"git_commit", "file_sha256", "receipt_id"})

REQUIRED_TOP_LEVEL: Tuple[str, ...] = (
    "schema_version",
    "package",
    "authority",
    "owner_clear",
    "protocol",
    "joint_contract",
    "scope_id",
    "profile",
    "owner",
    "cert",
    "base",
    "head",
    "spec_hash",
    "schema_hash",
    "changed_files",
    "typed_references",
    "input_identities",
    "cohort",
    "data_label",
    "input_hash",
    "history_hash",
    "config_hash",
    "code_hash",
    "hash_bindings",
    "output_paths",
    "output_hashes",
    "command",
    "cwd",
    "start_utc",
    "end_utc",
    "exit",
    "log_hash",
    "evidence_labels",
    "producer_consumer_trace",
    "common_digest",
    "numerical_output",
    "positive_control",
    "rehashed_faults",
    "spy_positive_control",
    "forbidden_calls_on_refusal",
    "exposure",
    "immutable_input_proof",
    "limitations",
    "failures",
    "review_revision",
    "worker_handoff",
    "ready_for_review",
    "execution",
)

# Allowed at PRE_CONSUME to still be pending (filled after consume / write).
CONSUME_PENDING_KEYS: FrozenSet[str] = frozenset(
    {
        "end_utc",
        "exit",
        "log_hash",
        "output_paths",
        "output_hashes",
        "numerical_output",
        "failures",
    }
)

OPTIONAL_TOP_LEVEL: FrozenSet[str] = frozenset(
    {
        "receipt_sha256",
        "receipt_id",
        "manifest_sha256",
        "appended_at_utc",
        "gate_stage",
        "ok",
        "status",
        "log",
        "accepted",
        "_receipt_path",
        "_sample_path",
    }
)

ALLOWED_TOP_LEVEL: FrozenSet[str] = frozenset(REQUIRED_TOP_LEVEL) | OPTIONAL_TOP_LEVEL

PRE_CONSUME_REQUIRED: Tuple[str, ...] = tuple(
    key for key in REQUIRED_TOP_LEVEL if key not in CONSUME_PENDING_KEYS
)

STAGE_PRE_CONSUME = "PRE_CONSUME"
STAGE_PRE_RECEIPT = "PRE_RECEIPT"

DEFAULT_LIMITATIONS = (
    "CERT=0",
    "SYNTHETIC_ONLY",
    "not self-accept",
    "READY_FOR_REVIEW requires Chief",
    "Primary B worker_handoff SLOT_RESERVED until bound",
    "inherited #700/#701 real-outcome tests NOT_RUN",
    "no real-data fit/calibration/forecast/scoring/outcome join",
)
