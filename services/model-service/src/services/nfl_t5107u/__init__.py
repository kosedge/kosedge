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
