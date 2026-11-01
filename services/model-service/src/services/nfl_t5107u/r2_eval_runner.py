"""R2 EVAL runner — loader-only target join. Not an EXEC claim.

#693 ``run_eval_score`` may still accept preloaded outcomes for old callers.
R2 callers must use this path: ``outcomes=None`` plus ``outcome_loader``.
Preloaded scoring outcomes are refused before HOLD/hash/claim, so the
loader is never invoked on that refuse.

CERT=0. No EVAL EXEC. DRAFT≠merge.
"""

from __future__ import annotations

from typing import Any, Mapping

from .evaluator import EvalRefuse, FrozenCohort, run_eval_score
from .outcome_gate import OutcomeGateRefuse, refuse_preloaded_scoring_outcomes


def run_eval_score_r2(
    frozen: FrozenCohort,
    outcomes: Mapping[str, Mapping[str, Any]] | None = None,
    *,
    outcome_loader: Any = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """R2-only EVAL entry. Requires loader. Refuses preloaded scoring outcomes."""
    try:
        refuse_preloaded_scoring_outcomes(outcomes)
    except OutcomeGateRefuse as exc:
        raise EvalRefuse(str(exc)) from exc
    if outcome_loader is None:
        raise EvalRefuse("R2 runner requires outcome_loader (outcomes=None)")
    scored = run_eval_score(
        frozen,
        None,
        outcome_loader=outcome_loader,
        **kwargs,
    )
    scored["r2_runner"] = "run_eval_score_r2"
    scored["preloaded_outcomes"] = False
    return scored
