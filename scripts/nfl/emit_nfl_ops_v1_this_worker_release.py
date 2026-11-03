#!/usr/bin/env python3
"""Emit THIS worker's release/claim record from a read-only git snapshot.

CERT=0. Does not kill processes, delete drafts, or claim a platform workspace.
Default Cursor reclaim capability is absent → PLATFORM_LIMITATION, not PASS.
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
    CursorCloudReclaimAdapter,
    as_worker_handoff,
    build_record,
    hash_saved_artifacts,
    mark_quiescent,
    record_handoff,
    snapshot_git,
    stamp_platform_limitation,
    with_fields,
)

OUT = ROOT / "data" / "ops" / "nfl-ops-v1-worker-release-claim"
WORKER_ID = "bc-3a3acab2-0de1-51eb-80e0-8ac958dfe2c7"
WORKSPACE_ALIAS = "cursor-vm-primary-b-bc-3a3acab2"


def main() -> int:
    git = snapshot_git(ROOT)
    artifact_paths = [
        OUT / "SCHEMA.json",
        OUT / "SAMPLE_RECORD.json",
        OUT / "WORKER_HANDOFF.json",
        OUT / "SELFCHECK_RECEIPT.json",
        OUT / "TEST_COMMANDS.json",
    ]
    existing = [p for p in artifact_paths if p.is_file()]
    saved = hash_saved_artifacts(ROOT, existing)
    log_hashes = [row for row in saved if row["path"].endswith("SELFCHECK_RECEIPT.json")]
    rec = build_record(
        task={
            "id": "chief-nflgreen-overnight-ops-20261102-0330-primary-b",
            "role": "PRIMARY_B",
            "title": "worker final-state / release / claim record",
        },
        worker={
            "id": WORKER_ID,
            "alias": "primary-b",
            "kind": "cursor_cloud_heavy",
            "url": "https://cursor.com/agents/" + WORKER_ID,
        },
        branch=git["branch"],
        head=git["head"],
        workspace_alias=WORKSPACE_ALIAS,
        dirty=git["dirty"],
        untracked=git["untracked"],
        saved_artifacts=saved,
        log_hashes=log_hashes,
        tests={
            "commands": [],
            "passed": None,
            "label": "SEE_TEST_COMMANDS_JSON",
        },
        active_writer={"id": WORKER_ID, "branch": git["branch"]},
        running_jobs=[],
        pending_prompts=[],
    )
    rec = record_handoff(rec)
    # Writer is finishing this emit; no queued prompts remain.
    rec = with_fields(rec, active_writer=None, running_jobs=[], pending_prompts=[])
    rec = mark_quiescent(rec)
    rec = stamp_platform_limitation(rec, CursorCloudReclaimAdapter())
    handoff = as_worker_handoff(rec)
    OUT.mkdir(parents=True, exist_ok=True)
    rec_path = OUT / "THIS_WORKER_RELEASE.json"
    handoff_path = OUT / "THIS_WORKER_HANDOFF.json"
    rec_path.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    handoff_path.write_text(json.dumps(handoff, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "state": rec["state"],
        "release_kind": rec["release_evidence"]["kind"],
        "not_a_pass": rec["release_evidence"]["not_a_pass"],
        "dirty_clean": rec["dirty"]["clean"],
        "untracked": rec["untracked"],
        "branch": rec["branch"],
        "head": rec["head"],
        "content_hash": rec["content_hash"],
        "path": str(rec_path.relative_to(ROOT)),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
