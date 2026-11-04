"""NFL_OPS_V1 evidence-manifest gate (Primary A). CERT=0. Synthetic only."""

from src.services.nfl_ops_v1_evidence.constants import (
    PACKAGE,
    PROFILE,
    SCHEMA_VERSION,
)
from src.services.nfl_ops_v1_evidence.gate import (
    assert_ready_for_review_allowed,
    gate_before_consume,
    gate_before_final_receipt,
    stamp_ready_for_review,
)
from src.services.nfl_ops_v1_evidence.refuse import EvidenceGateRefuse, RefuseClass
from src.services.nfl_ops_v1_evidence.run import (
    claim_from_import_only,
    run_from_saved_output,
    run_integrated_command,
    run_rehashed_fault_control,
)
from src.services.nfl_ops_v1_evidence.spy import OutcomeReadSpy, run_spy_positive_control
from src.services.nfl_ops_v1_evidence.verify import (
    VerificationContext,
    build_verification_context,
)
from src.services.nfl_ops_v1_evidence.profiles import (
    list_profiles,
    register_b_profile,
    require_active_profile,
)
from src.services.nfl_ops_v1_evidence.worker_handoff import empty_worker_handoff_slot

__all__ = [
    "PACKAGE",
    "PROFILE",
    "SCHEMA_VERSION",
    "EvidenceGateRefuse",
    "RefuseClass",
    "OutcomeReadSpy",
    "assert_ready_for_review_allowed",
    "claim_from_import_only",
    "empty_worker_handoff_slot",
    "gate_before_consume",
    "gate_before_final_receipt",
    "list_profiles",
    "register_b_profile",
    "require_active_profile",
    "run_from_saved_output",
    "run_integrated_command",
    "run_rehashed_fault_control",
    "run_spy_positive_control",
    "stamp_ready_for_review",
    "VerificationContext",
    "build_verification_context",
]
