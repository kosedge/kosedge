"""NFL leakage-free historical-eval PREP (IMV t4175u / P-7 + P-8).

Preparation only. This package does not grade, certify, or run a historical
evaluation on real seasons. Frozen predictive criteria are IMV sha prefixes
``4f832c91`` + ``132ee26c`` under protocol ``6a3aa3d9``. ``c57032db`` is
feature-parity only and is not the criteria.

Do not import production remat, W4–W6 plumbing evidence, or ``scripts/nfl/imv/``.
"""

from src.services.nfl_eval_prep.asof import (
    AsOfProof,
    AsOfViolation,
    validate_asof_proofs,
)
from src.services.nfl_eval_prep.harness import (
    RebuildPlan,
    build_rebuild_plan,
)
from src.services.nfl_eval_prep.leaks import (
    L1_FIXED_JOIN,
    L1_LEAKY_JOIN,
    L2_FIXED_WEEK_CAP,
    L2_LEAKY_WEEK_CAP,
    LeakFlag,
    apply_strict_week_join,
    require_week_cap,
    flag_l3_defaults,
)
from src.services.nfl_eval_prep.splits import (
    CONTAMINATED_EVAL_SEASONS,
    FROZEN_PLUMBING_WEEKS_2026,
    ExpandingWindowFold,
    build_expanding_window_folds,
    assert_train_only,
)

__all__ = [
    "AsOfProof",
    "AsOfViolation",
    "CONTAMINATED_EVAL_SEASONS",
    "ExpandingWindowFold",
    "FROZEN_PLUMBING_WEEKS_2026",
    "L1_FIXED_JOIN",
    "L1_LEAKY_JOIN",
    "L2_FIXED_WEEK_CAP",
    "L2_LEAKY_WEEK_CAP",
    "LeakFlag",
    "RebuildPlan",
    "apply_strict_week_join",
    "assert_train_only",
    "build_expanding_window_folds",
    "build_rebuild_plan",
    "flag_l3_defaults",
    "require_week_cap",
    "validate_asof_proofs",
]
