"""R2 EVAL runner — loader-only target join + file-byte rehash.

#693 ``run_eval_score`` may still accept preloaded outcomes for old callers.
R2 callers must use this path: ``outcomes=None`` plus ``outcome_loader``.
Preloaded scoring outcomes are refused before HOLD/hash/claim, so the
loader is never invoked on that refuse.

t5129u: hash frozen forecast **file** bytes, quote **manifest** file bytes,
and **each** admitted quote extract file. Bind those hashes into a new
runtime-byte record. Manifest pin / in-memory serialize alone is
insufficient. Mutation refuses before claim and before outcome_loader.

When ``score_body`` is omitted the inherited EVAL result contract applies
(vs IF **and** market). Stubs skip the contract. No live EVAL EXEC.

CERT=0. DRAFT≠merge.
"""

from __future__ import annotations

from typing import Any, Mapping

from .eval_result_contract import EvalResultContractRefuse, apply_eval_result_contract
from .evaluator import EvalRefuse, FrozenCohort, run_eval_score, run_paired_margin_eval
from .outcome_gate import OutcomeGateRefuse, refuse_preloaded_scoring_outcomes
from .r2_byte_rehash import R2ByteRefuse, verify_r2_runtime_bytes


def run_eval_score_r2(
    frozen: FrozenCohort,
    outcomes: Mapping[str, Mapping[str, Any]] | None = None,
    *,
    outcome_loader: Any = None,
    forecast_file: Any = None,
    quote_manifest_file: Any = None,
    quote_extract_files: Any = None,
    r2_byte_bind: Any = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """R2-only EVAL entry. Loader-only. File-byte rehash before claim."""
    try:
        refuse_preloaded_scoring_outcomes(outcomes)
    except OutcomeGateRefuse as exc:
        raise EvalRefuse(str(exc)) from exc
    if outcome_loader is None:
        raise EvalRefuse("R2 runner requires outcome_loader (outcomes=None)")
    try:
        runtime_bytes = verify_r2_runtime_bytes(
            forecast_file=forecast_file,
            quote_manifest_file=quote_manifest_file,
            quote_extract_files=quote_extract_files,
            r2_byte_bind=r2_byte_bind,
        )
    except R2ByteRefuse as exc:
        raise EvalRefuse(str(exc)) from exc

    score_body = kwargs.get("score_body")
    if score_body is None:
        def _gated_score(*args: Any, **score_kwargs: Any) -> dict[str, Any]:
            scored_inner = run_paired_margin_eval(*args, **score_kwargs)
            try:
                return apply_eval_result_contract(scored_inner)
            except EvalResultContractRefuse as contract_exc:
                raise EvalRefuse(str(contract_exc)) from contract_exc

        kwargs["score_body"] = _gated_score

    scored = run_eval_score(
        frozen,
        None,
        outcome_loader=outcome_loader,
        **kwargs,
    )
    scored["r2_runner"] = "run_eval_score_r2"
    scored["preloaded_outcomes"] = False
    scored["r2_runtime_bytes"] = runtime_bytes
    return scored
