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
from .evaluator import (  # noqa: F401
    EvalRefuse,
    freeze_forecast_cohort,
    run_eval_score,
)
