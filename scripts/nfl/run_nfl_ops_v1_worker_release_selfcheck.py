#!/usr/bin/env python3
"""Synthetic self-check for the NFL_OPS_V1 worker release/claim record.

Writes SAMPLE_RECORD.json + WORKER_HANDOFF.json under
data/ops/nfl-ops-v1-worker-release-claim/. CERT=0. No real data.
Does not import or run #700/#701 real-outcome tests.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "services" / "model-service"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from src.services.nfl_ops_v1_worker_release import (  # noqa: E402
    SCHEMA_ID,
    CursorCloudReclaimAdapter,
    SyntheticInProcessReleaseAdapter,
    WorkerReleaseRefuse,
    as_worker_handoff,
    attach_successor,
    build_record,
    confirm_release,
    mark_quiescent,
    record_handoff,
    sha256_file,
    sha256_text,
    stamp_platform_limitation,
)

OUT = ROOT / "data" / "ops" / "nfl-ops-v1-worker-release-claim"
SYNTH_HEAD = sha256_text("synthetic-head-primary-b-nfl-ops-v1")


def main() -> int:
    rec = build_record(
        task={
            "id": "synth-primary-b-release-claim",
            "role": "PRIMARY_B",
            "title": "worker final-state / release / claim record",
        },
        worker={
            "id": "synth-worker-b",
            "alias": "primary-b",
            "kind": "cursor_cloud_heavy",
        },
        branch="cursor/synth-worker-handoff",
        head=SYNTH_HEAD,
        workspace_alias="synth-ws-primary-b",
        active_writer=None,
        tests={"commands": [], "passed": None, "label": "SYNTHETIC_SAMPLE"},
    )
    rec = record_handoff(rec)
    rec = mark_quiescent(rec)
    default_stamped = stamp_platform_limitation(rec, CursorCloudReclaimAdapter())
    try:
        confirm_release(rec, CursorCloudReclaimAdapter())
        raise SystemExit("default adapter must not confirm release")
    except WorkerReleaseRefuse as exc:
        if exc.code != "PLATFORM_LIMITATION":
            raise
    board = SyntheticInProcessReleaseAdapter()
    named = attach_successor(rec, successor_id="synth-successor-1", role="INTEGRATION")
    released = confirm_release(named, board)
    handoff = as_worker_handoff(default_stamped)

    OUT.mkdir(parents=True, exist_ok=True)
    sample = OUT / "SAMPLE_RECORD.json"
    handoff_path = OUT / "WORKER_HANDOFF.json"
    sample.write_text(json.dumps(default_stamped, indent=2, sort_keys=True) + "\n")
    handoff_path.write_text(json.dumps(handoff, indent=2, sort_keys=True) + "\n")
    receipt = {
        "schema": SCHEMA_ID,
        "cert": 0,
        "synthetic": True,
        "self_accept": False,
        "sample_sha256": sha256_file(sample),
        "handoff_sha256": sha256_file(handoff_path),
        "sample_state": default_stamped["state"],
        "sample_release_kind": default_stamped["release_evidence"]["kind"],
        "synthetic_board_state": released["state"],
        "synthetic_board_kind": released["release_evidence"]["kind"],
        "default_not_a_pass": default_stamped["release_evidence"]["not_a_pass"],
        "evidence_label_default": default_stamped["release_evidence"]["evidence_label"],
        "evidence_label_synthetic_board": released["release_evidence"]["evidence_label"],
    }
    receipt_path = OUT / "SELFCHECK_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
