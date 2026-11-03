"""State machine: WRITING → HANDOFF_RECORDED → QUIESCENT → RELEASE_CONFIRMED → CLAIMED.

Illegal transitions are refused. No skip. No reverse. No self-kill.
"""

from __future__ import annotations

from typing import Any, Mapping

from .gates import (
    assert_clean_for_release,
    assert_drafts_preserved,
    assert_quiescent_inputs,
)
from .platform import (
    CursorCloudReclaimAdapter,
    WorkspaceReclaimAdapter,
    evidence_from_probe,
)
from .record import stamp_content_hash, utc_now, validate_record
from .types import (
    LEGAL_TRANSITIONS,
    RELEASE_CONFIRMED_KIND,
    RELEASE_PLATFORM_LIMITATION,
    RELEASE_SYNTHETIC,
    STATE_CLAIMED,
    STATE_HANDOFF_RECORDED,
    STATE_QUIESCENT,
    STATE_RELEASE_CONFIRMED,
    STATE_WRITING,
    WorkerReleaseRefuse,
)


def apply_transition(
    record: Mapping[str, Any],
    dest: str,
    *,
    at_utc: str | None = None,
    code: str = "TRANSITION",
) -> dict[str, Any]:
    current = validate_record(record)
    src = current["state"]
    allowed = LEGAL_TRANSITIONS.get(src, frozenset())
    if dest not in allowed:
        raise WorkerReleaseRefuse(
            f"illegal transition {src} -> {dest}",
            code="ILLEGAL_TRANSITION",
            record=current,
        )
    now = at_utc or utc_now()
    nxt = dict(current)
    nxt["state"] = dest
    history = list(current["state_history"])
    history.append({"from": src, "to": dest, "at_utc": now, "code": code})
    nxt["state_history"] = history
    return validate_record(stamp_content_hash(nxt))


def record_handoff(
    record: Mapping[str, Any],
    *,
    at_utc: str | None = None,
) -> dict[str, Any]:
    current = validate_record(record)
    if current["state"] != STATE_WRITING:
        raise WorkerReleaseRefuse(
            f"handoff refused from {current['state']}",
            code="ILLEGAL_TRANSITION",
            record=current,
        )
    assert_drafts_preserved(current)
    return apply_transition(
        current, STATE_HANDOFF_RECORDED, at_utc=at_utc, code="HANDOFF"
    )


def mark_quiescent(
    record: Mapping[str, Any],
    *,
    at_utc: str | None = None,
) -> dict[str, Any]:
    current = validate_record(record)
    if current["state"] != STATE_HANDOFF_RECORDED:
        raise WorkerReleaseRefuse(
            f"quiescent refused from {current['state']}",
            code="ILLEGAL_TRANSITION",
            record=current,
        )
    assert_quiescent_inputs(current)
    return apply_transition(current, STATE_QUIESCENT, at_utc=at_utc, code="QUIESCENT")


def stamp_platform_limitation(
    record: Mapping[str, Any],
    adapter: WorkspaceReclaimAdapter | None = None,
    *,
    at_utc: str | None = None,
) -> dict[str, Any]:
    """Honest limitation stamp. Does not invent RELEASE_CONFIRMED / PASS."""
    current = validate_record(record)
    probe = (adapter or CursorCloudReclaimAdapter()).probe()
    evidence = evidence_from_probe(probe, confirmed=False)
    evidence["kind"] = RELEASE_PLATFORM_LIMITATION
    evidence["not_a_pass"] = True
    evidence["confirmed_at_utc"] = None
    nxt = dict(current)
    nxt["release_evidence"] = evidence
    _ = at_utc
    return validate_record(stamp_content_hash(nxt))


def confirm_release(
    record: Mapping[str, Any],
    adapter: WorkspaceReclaimAdapter | None = None,
    *,
    at_utc: str | None = None,
) -> dict[str, Any]:
    current = validate_record(record)
    if current["state"] != STATE_QUIESCENT:
        raise WorkerReleaseRefuse(
            f"release refused from {current['state']}",
            code="ILLEGAL_TRANSITION",
            record=current,
        )
    assert_clean_for_release(current)
    impl = adapter or CursorCloudReclaimAdapter()
    probe = impl.probe()
    if probe.mocked:
        stamped = stamp_platform_limitation(current, impl, at_utc=at_utc)
        raise WorkerReleaseRefuse(
            "mocked release is not actual platform reclaim",
            code="MOCKED_RELEASE",
            record=stamped,
        )
    if not probe.present:
        stamped = stamp_platform_limitation(current, impl, at_utc=at_utc)
        raise WorkerReleaseRefuse(
            f"PLATFORM_LIMITATION: {probe.detail}",
            code=RELEASE_PLATFORM_LIMITATION,
            record=stamped,
        )
    confirmed = impl.confirm(current["workspace_alias"])
    if confirmed.mocked or not confirmed.present:
        stamped = stamp_platform_limitation(current, impl, at_utc=at_utc)
        raise WorkerReleaseRefuse(
            "platform confirm did not actually release",
            code=RELEASE_PLATFORM_LIMITATION,
            record=stamped,
        )
    evidence = evidence_from_probe(confirmed, confirmed=True)
    if evidence["kind"] not in {RELEASE_SYNTHETIC, RELEASE_CONFIRMED_KIND}:
        raise WorkerReleaseRefuse(
            "confirm produced non-release kind",
            code="PLATFORM_LIMITATION",
            record=current,
        )
    now = at_utc or current["state_history"][-1]["at_utc"]
    evidence["confirmed_at_utc"] = now
    nxt = dict(current)
    nxt["release_evidence"] = evidence
    nxt = validate_record(stamp_content_hash(nxt))
    return apply_transition(
        nxt, STATE_RELEASE_CONFIRMED, at_utc=at_utc, code="RELEASE"
    )


def attach_successor(
    record: Mapping[str, Any],
    *,
    successor_id: str,
    role: str,
) -> dict[str, Any]:
    current = validate_record(record)
    if current["state"] == STATE_CLAIMED:
        raise WorkerReleaseRefuse(
            "successor already claimed",
            code="ILLEGAL_TRANSITION",
            record=current,
        )
    if not successor_id or not str(successor_id).strip():
        raise WorkerReleaseRefuse("successor id missing", code="MISSING_FIELD")
    nxt = dict(current)
    nxt["successor"] = {"id": successor_id, "role": role, "named": True}
    return validate_record(stamp_content_hash(nxt))
