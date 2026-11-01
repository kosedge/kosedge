"""t5107u offline forecast builder + real-data evaluator scaffolding.

CERT=0 · DRAFT≠merge · RESEARCH_CONSUMED_RETRO · no EXEC scoring.
Reuses frozen Q2 intercept/slope (DEV 2013–16) and IF pin 6ca03716.
"""

from .builder import (  # noqa: F401
    CHALLENGER_WEIGHT,
    BuilderRefuse,
    ForecastRow,
    build_forecasts,
    challenger_margin,
)
from .if_control import (  # noqa: F401
    IF_TIP,
    LABEL_ARCHIVED,
    LABEL_RECONSTRUCTED,
    resolve_if_margin,
)
from .manifest import (  # noqa: F401
    FROZEN_MANIFEST_SCHEMA,
    seal_frozen_manifest,
)
from .q2 import (  # noqa: F401
    A_Q2,
    B_Q2,
    FIT_POLICY,
    q2_pm_new,
    verify_q2_transfer_policy,
)
from .dev_research import (  # noqa: F401
    LABEL as DEV_RESEARCH_LABEL,
    run_dev_research_e2e,
)
from .dev_research_cohort import run_dev_research_cohort  # noqa: F401
from .r2_eval_runner import run_eval_score_r2  # noqa: F401
from .r2_market_e2e import run_market_e2e  # noqa: F401
from .r2_byte_rehash import (  # noqa: F401
    bind_r2_runtime_bytes,
    enumerate_admitted_extracts,
    r2_hash_set,
    sha256_file_bytes,
    verify_r2_runtime_bytes,
)
from .eval_result_contract import (  # noqa: F401
    apply_eval_result_contract,
    validate_eval_result_contract,
)
from .evaluator import (  # noqa: F401
    EvalRefuse,
    freeze_eligible_cohorts,
    freeze_forecast_cohort,
    run_eval_score,
    run_paired_margin_eval,
)
from .outcome_gate import ScoringOutcomeLoader  # noqa: F401
from .if_produce import produce_if_mu  # noqa: F401
from .one_run import OneRunRefuse, bind_one_run  # noqa: F401
from .recon_driver import (  # noqa: F401
    HELPER_SHA256,
    ReconRefuse,
    freeze_completeness,
    load_verified_helper,
    reconstruct_slate,
)
