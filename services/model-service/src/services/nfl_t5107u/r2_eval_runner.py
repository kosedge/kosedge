"""R2 EVAL runner — loader-only target join + file-byte rehash.

#693 ``run_eval_score`` may still accept preloaded outcomes for old callers.
R2 callers must use this path: ``outcomes=None`` plus ``outcome_loader``.
Preloaded scoring outcomes are refused before HOLD/hash/claim, so the
loader is never invoked on that refuse.

t5129u / RETURN-FIX: hash frozen forecast **file** bytes, quote **manifest**
file bytes, and **each** admitted quote extract file. Bind those hashes
(bind_id + hash sets) into **ONE_RUN**. ``verify_one_run`` checks them
before claim. Side-bind + fresh rebind after mutation is insufficient.

Forecast file bytes must derive the same FrozenCohort as ``frozen.payload``.
Admitted extracts are enumerated from hashed manifest contents.
Incomplete market refuses before claim (no IF-only look burn).

CERT=0. DRAFT≠merge. No EVAL EXEC.
"""

from __future__ import annotations

from typing import Any, Mapping

from .eval_result_contract import (
    EvalResultContractRefuse,
    apply_eval_result_contract,
    refuse_incomplete_market_before_claim,
)
from .evaluator import EvalRefuse, FrozenCohort, run_eval_score, run_paired_margin_eval
from .one_run import OneRunRefuse, load_one_run, verify_one_run
from .outcome_gate import OutcomeGateRefuse, refuse_preloaded_scoring_outcomes
from .r2_byte_rehash import (
    R2ByteRefuse,
    refuse_unrelated_forecast_file,
    r2_hash_set,
    verify_r2_runtime_bytes,
)


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
        refuse_unrelated_forecast_file(frozen, forecast_file)
        runtime_bytes = verify_r2_runtime_bytes(
            forecast_file=forecast_file,
            quote_manifest_file=quote_manifest_file,
            quote_extract_files=quote_extract_files,
            r2_byte_bind=r2_byte_bind,
        )
        live_r2 = r2_hash_set(runtime_bytes)
        one_run_path = kwargs.get("one_run_path")
        record = load_one_run(one_run_path)
        verify_one_run(
            record,
            forecast_sha256=frozen.forecast_sha256,
            cohort_sha256=frozen.cohort_sha256,
            exec_bind=kwargs.get("exec_bind"),
            alex_go_id=kwargs.get("alex_go_id"),
            live_effective_spec_sha256=kwargs.get("live_effective_spec_sha256"),
            live_code_sha256=kwargs.get("live_code_sha256"),
            live_input_sha256=kwargs.get("live_input_sha256"),
            code_root=kwargs.get("code_root"),
            spec_path=kwargs.get("spec_path"),
            input_path=kwargs.get("input_path"),
            path=one_run_path,
            r2_runtime_bytes=live_r2,
            require_r2_runtime_bytes=True,
        )
    except (R2ByteRefuse, OneRunRefuse) as exc:
        raise EvalRefuse(str(exc)) from exc

    score_body = kwargs.get("score_body")
    if score_body is None:
        try:
            refuse_incomplete_market_before_claim(
                eligible_cohorts=kwargs.get("eligible_cohorts"),
                market_points=kwargs.get("market_points"),
            )
        except EvalResultContractRefuse as exc:
            raise EvalRefuse(str(exc)) from exc

        def _gated_score(*args: Any, **score_kwargs: Any) -> dict[str, Any]:
            scored_inner = run_paired_margin_eval(*args, **score_kwargs)
            try:
                return apply_eval_result_contract(scored_inner)
            except EvalResultContractRefuse as contract_exc:
                raise EvalRefuse(str(contract_exc)) from contract_exc

        kwargs["score_body"] = _gated_score

    kwargs["r2_runtime_bytes"] = live_r2
    kwargs["require_r2_runtime_bytes"] = True
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
