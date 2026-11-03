"""Release/claim gates. Dirty drafts are preserved, never deleted."""

from __future__ import annotations

from typing import Any, Mapping

from .types import WorkerReleaseRefuse


def _paths(record: Mapping[str, Any]) -> list[str]:
    dirty = record.get("dirty") or {}
    changed = list(dirty.get("changed_paths") or [])
    untracked = list(record.get("untracked") or [])
    return [p for p in changed + untracked if p]


def is_dirty(record: Mapping[str, Any]) -> bool:
    dirty = record.get("dirty") or {}
    if dirty.get("clean") is False:
        return True
    return bool(_paths(record))


def assert_drafts_preserved(record: Mapping[str, Any]) -> None:
    dirty = record.get("dirty") or {}
    if is_dirty(record) and dirty.get("preserved") is not True:
        raise WorkerReleaseRefuse(
            "dirty/untracked drafts must be preserved (not deleted)",
            code="DRAFTS_NOT_PRESERVED",
            record=dict(record),
        )


def assert_no_pending_writer(record: Mapping[str, Any]) -> None:
    if record.get("active_writer") is not None:
        raise WorkerReleaseRefuse(
            "active writer still present — cannot go QUIESCENT",
            code="PENDING_WRITER",
            record=dict(record),
        )


def assert_no_running_jobs(record: Mapping[str, Any]) -> None:
    jobs = record.get("running_jobs") or []
    if jobs:
        raise WorkerReleaseRefuse(
            "running jobs still present — cannot go QUIESCENT",
            code="PENDING_JOB",
            record=dict(record),
        )


def assert_no_pending_prompts(record: Mapping[str, Any]) -> None:
    prompts = record.get("pending_prompts") or []
    if prompts:
        raise WorkerReleaseRefuse(
            "pending prompts still present — cannot go QUIESCENT",
            code="PENDING_PROMPT",
            record=dict(record),
        )


def assert_quiescent_inputs(record: Mapping[str, Any]) -> None:
    assert_drafts_preserved(record)
    assert_no_pending_writer(record)
    assert_no_running_jobs(record)
    assert_no_pending_prompts(record)


def assert_clean_for_release(record: Mapping[str, Any]) -> None:
    """Dirty/unsaved work blocks RELEASE_CONFIRMED and CLAIM. Drafts stay on disk."""
    assert_drafts_preserved(record)
    if is_dirty(record):
        raise WorkerReleaseRefuse(
            "dirty/unsaved work blocks release and claim",
            code="DIRTY_UNSAVED",
            record=dict(record),
        )


def assert_successor_named(record: Mapping[str, Any], successor_id: str) -> None:
    successor = record.get("successor") or {}
    named = successor.get("id")
    if not successor.get("named") or not named:
        raise WorkerReleaseRefuse(
            "successor not named — refuse claim",
            code="WRONG_CLAIM",
            record=dict(record),
        )
    if named != successor_id:
        raise WorkerReleaseRefuse(
            "wrong successor id — refuse claim",
            code="WRONG_CLAIM",
            record=dict(record),
        )
