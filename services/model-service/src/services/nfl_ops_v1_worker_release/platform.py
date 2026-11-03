"""Workspace-platform reclaim probe.

A mocked release is not an actual platform reclaim. The default Cursor /
GitHub / Railway workspace-reclaim capability is absent in this worker,
so the record must say PLATFORM_LIMITATION rather than PASS.

This module never kills processes, never deletes drafts, and never
force-takes a workspace.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .types import (
    CAPABILITY_ABSENT,
    CAPABILITY_PRESENT,
    CURSOR_RECLAIM_CAPABILITY_ID,
    EVIDENCE_EXECUTED_HERE,
    EVIDENCE_SOURCE_INSPECTION,
    MOCKED_CAPABILITY_ID,
    RELEASE_CONFIRMED_KIND,
    RELEASE_PLATFORM_LIMITATION,
    RELEASE_SYNTHETIC,
    SYNTHETIC_BOARD_CAPABILITY_ID,
    WorkerReleaseRefuse,
)


@dataclass(frozen=True)
class PlatformProbe:
    capability_id: str
    present: bool
    mocked: bool
    limitation: str | None
    detail: str
    evidence_label: str


class WorkspaceReclaimAdapter(Protocol):
    capability_id: str

    def probe(self) -> PlatformProbe:
        ...

    def confirm(self, workspace_alias: str) -> PlatformProbe:
        ...


class CursorCloudReclaimAdapter:
    """Default adapter. No reclaim API is registered on this worker."""

    capability_id = CURSOR_RECLAIM_CAPABILITY_ID

    def probe(self) -> PlatformProbe:
        return PlatformProbe(
            capability_id=self.capability_id,
            present=False,
            mocked=False,
            limitation=RELEASE_PLATFORM_LIMITATION,
            detail=(
                "No Cursor Cloud / GitHub / Railway workspace-reclaim API is "
                "registered in this worker. Idle / closed / reclaimable stay "
                "distinct. Chief verifies actual platform release before reuse."
            ),
            evidence_label=EVIDENCE_SOURCE_INSPECTION,
        )

    def confirm(self, workspace_alias: str) -> PlatformProbe:
        probe = self.probe()
        raise WorkerReleaseRefuse(
            f"PLATFORM_LIMITATION: {probe.detail} workspace={workspace_alias}",
            code=RELEASE_PLATFORM_LIMITATION,
        )


class MockedReclaimAdapter:
    """Explicit mock. Confirming through this adapter is never a PASS."""

    capability_id = MOCKED_CAPABILITY_ID

    def probe(self) -> PlatformProbe:
        return PlatformProbe(
            capability_id=self.capability_id,
            present=True,
            mocked=True,
            limitation=RELEASE_PLATFORM_LIMITATION,
            detail="Mocked release is not actual platform reclaim",
            evidence_label=EVIDENCE_SOURCE_INSPECTION,
        )

    def confirm(self, workspace_alias: str) -> PlatformProbe:
        raise WorkerReleaseRefuse(
            "mocked release is not actual platform reclaim",
            code="MOCKED_RELEASE",
        )


class SyntheticInProcessReleaseAdapter:
    """Real in-process lock board. Not a Cursor workspace reclaim.

    Used only to exercise RELEASE_CONFIRMED → CLAIMED on a synthetic board.
    Evidence kind is SYNTHETIC_PLATFORM_RELEASE, never a Cursor PASS.
    """

    capability_id = SYNTHETIC_BOARD_CAPABILITY_ID

    def __init__(self) -> None:
        self._released: dict[str, bool] = {}

    def probe(self) -> PlatformProbe:
        return PlatformProbe(
            capability_id=self.capability_id,
            present=True,
            mocked=False,
            limitation=None,
            detail=(
                "In-process synthetic release board (EXECUTED_HERE). "
                "not_cursor_workspace_reclaim=true"
            ),
            evidence_label=EVIDENCE_EXECUTED_HERE,
        )

    def confirm(self, workspace_alias: str) -> PlatformProbe:
        if not workspace_alias:
            raise WorkerReleaseRefuse("workspace_alias required", code="MISSING_FIELD")
        self._released[workspace_alias] = True
        return self.probe()

    def is_released(self, workspace_alias: str) -> bool:
        return bool(self._released.get(workspace_alias))


def evidence_from_probe(probe: PlatformProbe, *, confirmed: bool = False) -> dict[str, Any]:
    if probe.mocked:
        kind = RELEASE_PLATFORM_LIMITATION
        capability = CAPABILITY_PRESENT if probe.present else CAPABILITY_ABSENT
        not_a_pass = True
    elif not probe.present:
        kind = RELEASE_PLATFORM_LIMITATION
        capability = CAPABILITY_ABSENT
        not_a_pass = True
    elif probe.capability_id == SYNTHETIC_BOARD_CAPABILITY_ID and confirmed:
        kind = RELEASE_SYNTHETIC
        capability = CAPABILITY_PRESENT
        not_a_pass = True  # synthetic board ≠ Cursor platform PASS
    elif confirmed:
        kind = RELEASE_CONFIRMED_KIND
        capability = CAPABILITY_PRESENT
        not_a_pass = False
    else:
        capability = CAPABILITY_PRESENT if probe.present else CAPABILITY_ABSENT
        not_a_pass = True
        if probe.present and probe.capability_id == SYNTHETIC_BOARD_CAPABILITY_ID:
            kind = "NOT_RELEASED"
        else:
            kind = RELEASE_PLATFORM_LIMITATION

    return {
        "kind": kind,
        "platform_capability": capability,
        "capability_id": probe.capability_id,
        "mocked": probe.mocked,
        "limitation": probe.limitation,
        "evidence_label": probe.evidence_label,
        "not_a_pass": not_a_pass,
        "not_cursor_workspace_reclaim": probe.capability_id != CURSOR_RECLAIM_CAPABILITY_ID
        or not probe.present,
        "confirmed_at_utc": None,
        "detail": probe.detail,
    }


def default_adapter() -> CursorCloudReclaimAdapter:
    return CursorCloudReclaimAdapter()
