"""Consume adapter output on the synthetic literal-law path. CERT=0."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional

from src.services.nfl_joint_contract_v1.constants import (
    CERT,
    CONTRACT_HASH,
    CONTRACT_ID,
    DATA_LABEL,
    KNOWN_SETTLEMENT_PROFILE,
    SYNTH_IDENTITY,
    TASK_ID,
)
from src.services.nfl_joint_contract_v1.freeze import require_freeze_intact
from src.services.nfl_joint_contract_v1.oracle import assert_computed_matches_expected
from src.services.nfl_joint_contract_v1.refuse import JointContractRefuse, RefuseClass
from src.services.nfl_joint_contract_v1.settlement import require_known_settlement
from src.services.nfl_joint_contract_v1.spy import (
    ForbiddenSurfaceSpy,
    OutcomeReadSpy,
    assert_zero_forbidden_on_refusal,
)

ALLOWED_CONSUMERS = frozenset({"fixture", "joint_literal"})
DENIED_CONSUMERS = frozenset(
    {
        "fair_lines_api",
        "cache",
        "production",
        "subscriber",
        "direct_api",
    }
)


def consume_literal_law(
    record: Mapping[str, Any],
    *,
    consumer: str = "joint_literal",
    settlement_profile: Optional[str] = KNOWN_SETTLEMENT_PROFILE,
    root: Path | None = None,
    outcome_spy: OutcomeReadSpy | None = None,
    surface: ForbiddenSurfaceSpy | None = None,
) -> dict[str, Any]:
    spy = outcome_spy if outcome_spy is not None else OutcomeReadSpy()
    try:
        if not isinstance(record, Mapping):
            raise JointContractRefuse("adapter record must be an object", refuse_class=RefuseClass.TYPE)
        if record.get("data_label") != DATA_LABEL:
            raise JointContractRefuse(
                f"data_label={record.get('data_label')!r} refused before readers/model/network/DB",
                refuse_class=RefuseClass.REAL_MODE,
            )
        name = (consumer or "").strip().lower()
        if name in DENIED_CONSUMERS or name not in ALLOWED_CONSUMERS:
            raise JointContractRefuse(
                f"consumer {consumer!r} is not on the synthetic literal-law path",
                refuse_class=RefuseClass.CAPABILITY,
            )
        require_known_settlement(settlement_profile)
        freeze = require_freeze_intact(root)
        if record.get("contract_id") != CONTRACT_ID or record.get("contract_hash") != CONTRACT_HASH:
            raise JointContractRefuse(
                "adapter record is not NFL_JOINT_CONTRACT_V1 / 4f2c9e2b",
                refuse_class=RefuseClass.IDENTITY,
            )
        if record.get("freeze_receipt_hash") != freeze.get("receipt_hash"):
            raise JointContractRefuse(
                "adapter freeze_receipt_hash != sealed receipt",
                refuse_class=RefuseClass.HASH_MUTATED,
            )
        ident = record.get("identity")
        if not isinstance(ident, Mapping) or dict(ident) != dict(SYNTH_IDENTITY):
            raise JointContractRefuse(
                "identity is not the sealed synthetic joint envelope",
                refuse_class=RefuseClass.IDENTITY,
            )
        if record.get("fitted") is True:
            raise JointContractRefuse(
                "fitted adapter is not the literal-law path",
                refuse_class=RefuseClass.CAPABILITY,
            )
        bits = (record.get("capability") or {}).get("bits") if isinstance(record.get("capability"), Mapping) else None
        if not isinstance(bits, list) or "JOINT_LITERAL_LAW" not in bits:
            raise JointContractRefuse(
                "JOINT_LITERAL_LAW capability required",
                refuse_class=RefuseClass.CAPABILITY,
            )
        if any(bit in {"JOINT_SCORE", "IF_R6_POINT_MEANS", "CENSORED_NORMAL_686"} for bit in bits):
            raise JointContractRefuse(
                "predictive / IF-R6 / #686 capability bits refused",
                refuse_class=RefuseClass.CAPABILITY,
            )
        settlement = record.get("settlement")
        if not isinstance(settlement, Mapping):
            raise JointContractRefuse("settlement missing", refuse_class=RefuseClass.INCOMPLETE)
        if settlement.get("actionable") is True or settlement.get("fair_odds") is not None:
            raise JointContractRefuse(
                "actionable / fair_odds cannot pass this consumer",
                refuse_class=RefuseClass.ACTIONABLE,
            )
        if settlement.get("ev") is not None:
            raise JointContractRefuse("EV cannot pass this consumer", refuse_class=RefuseClass.ACTIONABLE)
        require_known_settlement(settlement.get("settlement_profile"))
        assert_computed_matches_expected()
        out = dict(record)
        out["consumed"] = True
        out["consumer"] = name
        out["cert"] = CERT
        out["task_id"] = TASK_ID
        out["ready_for_review"] = False
        out["self_accept"] = False
        return out
    except Exception:
        assert_zero_forbidden_on_refusal(outcome_spy=spy, surface=surface)
        raise
