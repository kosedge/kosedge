"""Synthetic literal-law adapter. NOT a fitted predictor. CERT=0.

Derives spread / total / ML from the frozen joint law only.
Does not map IF/R6 point means → joint. Does not replay #686.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional

from src.services.nfl_joint_contract_v1.constants import (
    CERT,
    CONTRACT_HASH,
    CONTRACT_ID,
    DATA_LABEL,
    ELIGIBILITY,
    FEATURE_CATALOG,
    KNOWN_SETTLEMENT_PROFILE,
    PACKAGE,
    SCHEMA_VERSION,
    SYNTH_IDENTITY,
    TASK_ID,
)
from src.services.nfl_joint_contract_v1.freeze import require_freeze_intact
from src.services.nfl_joint_contract_v1.oracle import (
    assert_computed_matches_expected,
    partitions_from_law,
)
from src.services.nfl_joint_contract_v1.refuse import JointContractRefuse, RefuseClass
from src.services.nfl_joint_contract_v1.settlement import identity_settlement, require_known_settlement
from src.services.nfl_joint_contract_v1.spy import (
    ForbiddenSurfaceSpy,
    OutcomeReadSpy,
    assert_zero_forbidden_on_refusal,
)

_FORBIDDEN_REQUESTS = frozenset(
    {
        "JOINT_SCORE",
        "JOINT_SCORE_PREDICTIVE",
        "IF_R6_POINT_MEANS",
        "CENSORED_NORMAL_686",
        "POINT_MARGIN_FROM_MEANS",
    }
)


def _capability(requested: str) -> dict[str, Any]:
    if requested in _FORBIDDEN_REQUESTS:
        raise JointContractRefuse(
            f"requested_output {requested!r} is not the literal-law adapter "
            "(no IF/R6 point-means→joint; no #686; no predictive joint-family)",
            refuse_class=RefuseClass.CAPABILITY,
        )
    if requested != "LITERAL_JOINT_PARTITIONS":
        raise JointContractRefuse(
            f"unsupported requested_output {requested!r}",
            refuse_class=RefuseClass.CAPABILITY,
        )
    return {
        "bits": ["JOINT_LITERAL_LAW"],
        "not_bits": sorted(_FORBIDDEN_REQUESTS),
        "requested_output": requested,
        "fitted": False,
    }


def _provenance(freeze: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "source": "frozen_literal_oracle",
        "fitted": False,
        "historical": False,
        "data_label": DATA_LABEL,
        "observation": "AUTHORED",
        "availability": "literal_catalog",
        "feature_catalog": list(FEATURE_CATALOG),
        "oracle_hash": freeze.get("oracle_hash"),
        "schema_hash": freeze.get("schema_hash"),
        "code_hash": freeze.get("code_hash"),
        "receipt_hash": freeze.get("receipt_hash"),
        "task_id": TASK_ID,
    }


def _exposure() -> dict[str, Any]:
    return {
        "subscriber_consumable": False,
        "betting_consumable": False,
        "production_consumable": False,
        "env_bypass_honored": False,
        "cacheable": False,
        "public_output": False,
        "actionable": False,
        "cert": CERT,
    }


def adapt_literal_law(
    *,
    root: Path | None = None,
    settlement_profile: Optional[str] = KNOWN_SETTLEMENT_PROFILE,
    requested_output: str = "LITERAL_JOINT_PARTITIONS",
    data_label: str = DATA_LABEL,
    outcome_spy: OutcomeReadSpy | None = None,
    surface: ForbiddenSurfaceSpy | None = None,
) -> dict[str, Any]:
    """Produce adapter output from the sealed oracle. Synthetic only."""
    spy = outcome_spy if outcome_spy is not None else OutcomeReadSpy()
    try:
        if data_label != DATA_LABEL:
            raise JointContractRefuse(
                f"data_label={data_label!r} refused before readers/model/network/DB",
                refuse_class=RefuseClass.REAL_MODE,
            )
        require_known_settlement(settlement_profile)
        freeze = require_freeze_intact(root)
        capability = _capability(requested_output)
        computed = partitions_from_law()
        assert_computed_matches_expected(computed)
        settlement = identity_settlement(computed, profile=settlement_profile)
        return {
            "ok": True,
            "schema_version": SCHEMA_VERSION,
            "package": PACKAGE,
            "contract_id": CONTRACT_ID,
            "contract_hash": CONTRACT_HASH,
            "task_id": TASK_ID,
            "cert": CERT,
            "data_label": DATA_LABEL,
            "eligibility": ELIGIBILITY,
            "fitted": False,
            "self_accept": False,
            "ready_for_review": False,
            "identity": dict(SYNTH_IDENTITY),
            "capability": capability,
            "provenance": _provenance(freeze),
            "channel": "FIXTURE",
            "production_mode": False,
            "cacheable": False,
            "partitions": {
                "ml": computed["ml"],
                "means": computed["means"],
                "spread": computed["spread"],
                "total": computed["total"],
                "weight_sum": computed["weight_sum"],
                "n": computed["n"],
            },
            "outcomes": computed["outcomes"],
            "settlement": settlement,
            "exposure": _exposure(),
            "freeze_receipt_hash": freeze.get("receipt_hash"),
        }
    except Exception:
        assert_zero_forbidden_on_refusal(outcome_spy=spy, surface=surface)
        raise
