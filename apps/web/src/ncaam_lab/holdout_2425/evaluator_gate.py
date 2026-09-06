"""One-shot holdout evaluator gate — design only; refuses without explicit unseal.

Must never be imported by normal materialization, CI, or pytest fixtures in a way
that auto-scores. Tests exercise refuse paths only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ncaam_lab.holdout_2425.constants import HOLDOUT_ID


class HoldoutSealError(RuntimeError):
    """Raised when seal controls refuse evaluation."""


@dataclass(frozen=True)
class UnsealAuthorization:
    holdout_id: str
    authorize_unseal: bool
    candidate_code_hash: str
    feature_manifest_hash: str
    label_manifest_hash: str
    evaluation_spec_hash: str
    git_clean: bool
    prior_result_receipt_exists: bool
    governance_replication_authorized: bool = False


def assert_may_evaluate(auth: UnsealAuthorization) -> None:
    """Refuse unless every seal control passes. Does not score."""
    if auth.holdout_id != HOLDOUT_ID:
        raise HoldoutSealError("holdout_id mismatch or missing")
    if not auth.authorize_unseal:
        raise HoldoutSealError("explicit unseal authorization flag required")
    if not auth.candidate_code_hash or len(auth.candidate_code_hash) < 16:
        raise HoldoutSealError("exact candidate code/content hash required")
    if not auth.feature_manifest_hash or len(auth.feature_manifest_hash) < 16:
        raise HoldoutSealError("exact feature-manifest hash required")
    if not auth.label_manifest_hash or len(auth.label_manifest_hash) < 16:
        raise HoldoutSealError("exact label-manifest hash required")
    if not auth.evaluation_spec_hash or len(auth.evaluation_spec_hash) < 16:
        raise HoldoutSealError("frozen evaluation specification hash required")
    if not auth.git_clean:
        raise HoldoutSealError("clean git state required")
    if auth.prior_result_receipt_exists and not auth.governance_replication_authorized:
        raise HoldoutSealError(
            "prior result receipt exists; governance replication authorization required"
        )


def evaluate_holdout_refused_by_default(
    auth: Optional[UnsealAuthorization] = None,
) -> None:
    """Public entrypoint with no default scoring path."""
    if auth is None:
        raise HoldoutSealError("no unseal authorization provided; scoring refused")
    assert_may_evaluate(auth)
    raise HoldoutSealError(
        "Phase 2.6A: evaluator designed but scoring is not authorized to execute"
    )
