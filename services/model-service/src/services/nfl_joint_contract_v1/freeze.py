"""Seal schema / code / task-bound oracle BEFORE adapter consumers.

Consumers must load this receipt and refuse hash drift. CERT=0.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.services.nfl_joint_contract_v1.constants import (
    CERT,
    CONTRACT_HASH,
    CONTRACT_ID,
    DATA_LABEL,
    FEATURE_CATALOG,
    FREEZE_REL,
    KNOWN_SETTLEMENT_PROFILE,
    ORACLE_REL,
    ORDER_HASH,
    OWNER_CLEAR,
    PACKAGE,
    PROTOCOL,
    SCHEMA_REL,
    SCHEMA_VERSION,
    SCOPE_ID,
    SYNTH_IDENTITY,
    TASK_ID,
)
from src.services.nfl_joint_contract_v1.hashes import sha256_bytes_map, sha256_file, sha256_text
from src.services.nfl_joint_contract_v1.oracle import (
    assert_computed_matches_expected,
    frozen_oracle_body,
)
from src.services.nfl_joint_contract_v1.refuse import JointContractRefuse, RefuseClass

FREEZE_CODE_RELS = (
    "services/model-service/src/services/nfl_joint_contract_v1/constants.py",
    "services/model-service/src/services/nfl_joint_contract_v1/oracle.py",
    "services/model-service/src/services/nfl_joint_contract_v1/freeze.py",
)


def schema_body() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "contract_hash": CONTRACT_HASH,
        "order_hash": ORDER_HASH,
        "owner_clear": OWNER_CLEAR,
        "protocol": PROTOCOL,
        "task_id": TASK_ID,
        "package": PACKAGE,
        "cert": CERT,
        "data_label": DATA_LABEL,
        "eligibility": "UNQUALIFIED",
        "fitted": False,
        "output": "one shared joint law of paired nonnegative integer (H,A) with normalized weights",
        "derive": ["spread", "total", "moneyline"],
        "from": "SAME_JOINT_LAW_ONLY",
        "tie_mass": "preserved",
        "ties_are_away_wins": False,
        "home_spread_rule": "sign(H-A+s) -> cover/push/loss",
        "total_rule": "H+A vs t -> over/push/under",
        "unknown_settlement": "refuse settled_p / fair_odds / EV / actionable",
        "known_settlement_profile": KNOWN_SETTLEMENT_PROFILE,
        "feature_catalog": list(FEATURE_CATALOG),
        "identity": dict(SYNTH_IDENTITY),
        "not_authorized": [
            "real_data",
            "fit",
            "calibrate",
            "forecast",
            "score",
            "qualify",
            "live_capture",
            "customer_output",
            "if_r6_point_means_to_joint",
            "censored_normal_686",
        ],
    }


def _repo_root(root: Path | None) -> Path:
    if root is not None:
        return Path(root)
    return Path(__file__).resolve().parents[5]


def seal_freeze(*, root: Path | None = None) -> dict[str, Any]:
    """Write oracle/schema/receipt. Adapter consumers must not run before this seal."""
    assert_computed_matches_expected()
    repo = _repo_root(root)
    dest = repo / "data" / "ops" / "nfl-joint-contract-v1"
    dest.mkdir(parents=True, exist_ok=True)

    oracle = frozen_oracle_body()
    schema = schema_body()
    oracle_hash = sha256_bytes_map(oracle)
    schema_hash = sha256_bytes_map(schema)

    (repo / ORACLE_REL).write_text(
        json.dumps(oracle, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (repo / SCHEMA_REL).write_text(
        json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    code_files = []
    for rel in FREEZE_CODE_RELS:
        path = repo / rel
        if not path.is_file():
            raise JointContractRefuse(
                f"freeze code missing {rel}",
                refuse_class=RefuseClass.FREEZE,
            )
        code_files.append({"path": rel, "sha256": sha256_file(path)})
    code_files.sort(key=lambda row: row["path"])
    code_hash = sha256_text(json.dumps(code_files, separators=(",", ":"), sort_keys=True))

    receipt = {
        "schema_version": "nfl-joint-contract-v1-freeze-receipt-v1",
        "task_id": TASK_ID,
        "scope_id": SCOPE_ID,
        "package": PACKAGE,
        "contract_id": CONTRACT_ID,
        "contract_hash": CONTRACT_HASH,
        "order_hash": ORDER_HASH,
        "owner_clear": OWNER_CLEAR,
        "cert": CERT,
        "data_label": DATA_LABEL,
        "fitted": False,
        "self_accept": False,
        "ready_for_review": False,
        "oracle_path": ORACLE_REL,
        "schema_path": SCHEMA_REL,
        "oracle_hash": oracle_hash,
        "schema_hash": schema_hash,
        "code_hash": code_hash,
        "code_files": code_files,
        "known_settlement_profile": KNOWN_SETTLEMENT_PROFILE,
        "note": (
            "Sealed before adapter consumers. Hash mismatch refuses consume. "
            "Not a predictive joint-family. Literal-law only."
        ),
    }
    receipt["receipt_hash"] = sha256_bytes_map(
        {k: v for k, v in receipt.items() if k != "receipt_hash"}
    )
    (repo / FREEZE_REL).write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return receipt


def load_freeze(root: Path | None = None) -> dict[str, Any]:
    repo = _repo_root(root)
    path = repo / FREEZE_REL
    if not path.is_file():
        raise JointContractRefuse(
            "freeze receipt missing — adapter consumers refused",
            refuse_class=RefuseClass.FREEZE,
        )
    return json.loads(path.read_text(encoding="utf-8"))


def require_freeze_intact(root: Path | None = None) -> dict[str, Any]:
    repo = _repo_root(root)
    receipt = load_freeze(repo)
    oracle = json.loads((repo / ORACLE_REL).read_text(encoding="utf-8"))
    schema = json.loads((repo / SCHEMA_REL).read_text(encoding="utf-8"))
    if sha256_bytes_map(oracle) != receipt.get("oracle_hash"):
        raise JointContractRefuse(
            "oracle bytes drifted from freeze receipt",
            refuse_class=RefuseClass.HASH_MUTATED,
        )
    if sha256_bytes_map(schema) != receipt.get("schema_hash"):
        raise JointContractRefuse(
            "schema bytes drifted from freeze receipt",
            refuse_class=RefuseClass.HASH_MUTATED,
        )
    if sha256_bytes_map(frozen_oracle_body()) != receipt.get("oracle_hash"):
        raise JointContractRefuse(
            "live oracle body != sealed oracle hash",
            refuse_class=RefuseClass.HASH_MUTATED,
        )
    if sha256_bytes_map(schema_body()) != receipt.get("schema_hash"):
        raise JointContractRefuse(
            "live schema body != sealed schema hash",
            refuse_class=RefuseClass.HASH_MUTATED,
        )
    assert_computed_matches_expected()
    return receipt
