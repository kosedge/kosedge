"""t5213u R6_CALLER_V1 — offline manifest / caller / ledger (CERT=0).

POINT_MARGIN only. Real mode refuses. Live A invoke → B seal.
"""

from src.services.nfl_r6_caller.contract import (
    ALGORITHM_TIP,
    CONTRACT_27,
    IF_TIP,
    OUTPUT_KIND,
    PACKAGE_ID,
    R6Refuse,
    R6RefuseCode,
    expected_c_mean,
    pin_block,
)
from src.services.nfl_r6_caller.ledger import PairedArmLedger, make_seal_record
from src.services.nfl_r6_caller.caller import (
    bind_a_api,
    invoke_a_frozen_caller,
    locate_a_output,
    prove_real_mode_refuse,
    prove_ryan_cases,
    prove_seal_refuses,
    refuse_real_mode,
    run_live_a_e2e,
    run_synthetic_e2e,
)

__all__ = [
    "ALGORITHM_TIP",
    "CONTRACT_27",
    "IF_TIP",
    "OUTPUT_KIND",
    "PACKAGE_ID",
    "PairedArmLedger",
    "R6Refuse",
    "R6RefuseCode",
    "expected_c_mean",
    "bind_a_api",
    "invoke_a_frozen_caller",
    "locate_a_output",
    "make_seal_record",
    "pin_block",
    "prove_real_mode_refuse",
    "prove_ryan_cases",
    "prove_seal_refuses",
    "refuse_real_mode",
    "run_live_a_e2e",
    "run_synthetic_e2e",
]
