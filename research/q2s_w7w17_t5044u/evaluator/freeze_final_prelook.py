#!/usr/bin/env python3
"""Write FINAL_PRELOOK_FREEZE.json — appends onto 90774bd4, does not rewrite it."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

EVAL = Path(__file__).resolve().parent
if str(EVAL) not in sys.path:
    sys.path.insert(0, str(EVAL))

from verify_final_prelook import (  # noqa: E402
    EVALUATOR_PATHS,
    FINAL_FREEZE_PATH,
    IF_MUS_SHA,
    MATRIX_SHA,
    PACKET,
    PARENT_FREEZE_PATH,
    PARENT_FREEZE_SHA,
    Q2S_SHA,
    LookGateRefuse,
    sha256_file,
    verify_parent_history,
)


class FreezeRefuse(RuntimeError):
    pass


def build_payload() -> dict:
    parent = verify_parent_history()
    files = dict(parent["files"])
    files["phase4/artifacts/PROTOCOL_FREEZE.json"] = PARENT_FREEZE_SHA
    for rel in EVALUATOR_PATHS:
        path = PACKET / rel
        if not path.exists():
            raise FreezeRefuse(f"missing evaluator path {rel}")
        files[rel] = sha256_file(path)
    rows = {
        "if_mus": {
            "n_rows": 141,
            "path": "phase4/artifacts/IF_MUS_W7W17.json",
            "sha256": IF_MUS_SHA,
            "sha8": "32e97434",
            "unchanged_from_parent": True,
        },
        "q2s_rows": {
            "n_rows": 141,
            "path": "phase4/artifacts/q2s_rows_w7w17.json",
            "sha256": Q2S_SHA,
            "sha8": "55d8c8bc",
            "unchanged_from_parent": True,
        },
    }
    return {
        "ticket": "t5053u",
        "phase": "final_prelook_evaluator",
        "label": "RETRO_FIT / DEV_RESEARCH",
        "cert": 0,
        "nfl": "NO-GO",
        "owner_clear_tip": "12763c08",
        "cite": [
            "12763c08",
            "t5053u",
            "90774bd4",
            "8b80ad7b",
            "4b9cac5e",
            "8155fd19",
            "d7e0a6bc",
        ],
        "parent_freeze": {
            "path": "phase4/artifacts/PROTOCOL_FREEZE.json",
            "sha256": PARENT_FREEZE_SHA,
            "sha8": "90774bd4",
            "role": "history — prediction rows / emit code. Not rewritten.",
        },
        "parent_rewritten": False,
        "prediction_head": "8155fd194ae2960765647e86839cfa964f0a5cea",
        "matrix_sha256": MATRIX_SHA,
        "matrix_sha8": "b56be146",
        "files": files,
        "evaluator_files": {rel: files[rel] for rel in EVALUATOR_PATHS},
        "rows": rows,
        "metric_protocol": "evaluator/METRIC_PROTOCOL.md",
        "bootstrap": {"B": 10000, "seed": 20261102, "week_blocks": 11},
        "look_authorized": False,
        "look_run": False,
        "existence_only": False,
        "alex_receipt_8b80ad7b_authorizes_this_look": False,
        "awaiting": (
            "Alex RO of this final evaluator freeze, bound alongside "
            "unchanged prediction-row hashes 32e97434 / 55d8c8bc / b56be146 / 90774bd4. "
            "Do NOT look until CoS re-authorizes after that PASS."
        ),
        "frozen_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": (
            "Complete expected hash set = parent 90774bd4 files + parent freeze "
            "object + evaluator code/protocol/fixtures/tests. Comparison path "
            "must re-hash this complete set and require a matching independent "
            "Alex receipt for the *final* freeze sha."
        ),
    }


def write_freeze() -> dict:
    if FINAL_FREEZE_PATH.exists():
        prev = json.loads(FINAL_FREEZE_PATH.read_text())
        payload = build_payload()
        # timestamps may differ — compare bound maps only
        if (
            prev.get("files") != payload["files"]
            or prev.get("rows") != payload["rows"]
            or prev.get("parent_freeze") != payload["parent_freeze"]
        ):
            raise FreezeRefuse("FINAL_PRELOOK_FREEZE exists with different hashes")
        return prev
    payload = build_payload()
    FINAL_FREEZE_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    digest = sha256_file(FINAL_FREEZE_PATH)
    FINAL_FREEZE_PATH.with_suffix(".json.sha256").write_text(
        f"{digest}  {FINAL_FREEZE_PATH.name}\n"
    )
    return payload


def main() -> int:
    try:
        payload = write_freeze()
        digest = sha256_file(FINAL_FREEZE_PATH)
    except (FreezeRefuse, LookGateRefuse) as exc:
        print(f"FINAL_FREEZE_REFUSE: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "ok": True,
                "path": "evaluator/FINAL_PRELOOK_FREEZE.json",
                "sha256": digest,
                "parent_sha8": "90774bd4",
                "n_files": len(payload["files"]),
                "look_run": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
