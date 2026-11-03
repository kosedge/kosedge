"""NFL_JOINT_CONTRACT_V1 literal-law adapter. CERT=0. SYNTHETIC_ONLY."""

from src.services.nfl_joint_contract_v1.adapter import adapt_literal_law
from src.services.nfl_joint_contract_v1.constants import (
    CONTRACT_ID,
    KNOWN_SETTLEMENT_PROFILE,
    PACKAGE,
    SCHEMA_VERSION,
)
from src.services.nfl_joint_contract_v1.consume import consume_literal_law
from src.services.nfl_joint_contract_v1.handoff import bind_handoff
from src.services.nfl_joint_contract_v1.refuse import JointContractRefuse, RefuseClass
from src.services.nfl_joint_contract_v1.run import run_literal_law_command
from src.services.nfl_joint_contract_v1.spy import OutcomeReadSpy, run_spy_positive_control

__all__ = [
    "CONTRACT_ID",
    "KNOWN_SETTLEMENT_PROFILE",
    "PACKAGE",
    "SCHEMA_VERSION",
    "JointContractRefuse",
    "RefuseClass",
    "OutcomeReadSpy",
    "adapt_literal_law",
    "bind_handoff",
    "consume_literal_law",
    "run_literal_law_command",
    "run_spy_positive_control",
]
