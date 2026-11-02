#!/usr/bin/env python3
"""t5151u Package A — freeze ONE task manifest BEFORE verification.

Reads authoritative REG schedule membership and accepted identity records.
Never derives the allowed list from an output under check.
Does not reconstruct, fit, score, or run EVAL. CERT=0.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_t5107u.cohort_enforcement import (  # noqa: E402
    ACCEPTED_MARKET72_PATH,
    DEV_IF437_IDENTITY_SHA256,
    DEV_MARKET72_FILE_SHA256,
    DEV_MARKET72_IDENTITY_SHA256,
    FEATURE_RECON_REG496_ARTIFACT_SHA256,
    METRIC_COHORTS_PATH,
    OUT_DIR,
    ORIGINAL_502_PATH,
    ORIGINAL_502_SHA256,
    PROFILE_DEV_IF437,
    PROFILE_DEV_MARKET72,
    PROFILE_FEATURE_RECON_REG496,
    REG496_IDENTITY_SHA256,
    SCHEDULE_PATH,
    SCHEDULE_SHA256,
    TASK_MANIFEST_NAME,
    build_task_manifest,
    cohort_identity_sha256,
    sha256_file,
)
from src.services.nfl_t5107u.last_played_cohort import (  # noqa: E402
    frozen_reg_w2plus_ids,
)
from src.services.nfl_t5107u.metric_cohorts import WILDCARD_2020_W18  # noqa: E402


def main() -> int:
    schedule = ROOT / SCHEDULE_PATH
    if sha256_file(schedule) != SCHEDULE_SHA256:
        raise SystemExit("schedule bytes drifted — refuse freeze")
    if sha256_file(ROOT / ORIGINAL_502_PATH) != ORIGINAL_502_SHA256:
        raise SystemExit("original 502 bytes drifted — refuse freeze")
    market72_path = ROOT / ACCEPTED_MARKET72_PATH
    if sha256_file(market72_path) != DEV_MARKET72_FILE_SHA256:
        raise SystemExit("accepted matched72 identity bytes drifted — refuse freeze")

    reg496 = frozen_reg_w2plus_ids(ROOT)
    if cohort_identity_sha256(reg496) != REG496_IDENTITY_SHA256:
        raise SystemExit("REG496 identity hash drifted from schedule membership")

    metric = json.loads((ROOT / METRIC_COHORTS_PATH).read_text(encoding="utf-8"))
    if437 = [str(g) for g in metric["dev_reg"]["game_ids"]]
    if cohort_identity_sha256(if437) != DEV_IF437_IDENTITY_SHA256:
        raise SystemExit("DEV_IF437 identity hash drifted from 92b91585")

    market72 = [str(g) for g in json.loads(market72_path.read_text(encoding="utf-8"))]
    if Counter(g.split("_", 1)[0] for g in market72) != {"2020": 35, "2021": 37}:
        raise SystemExit("DEV_MARKET72 season counts drifted from 35+37")
    if set(WILDCARD_2020_W18) & set(reg496):
        raise SystemExit("REG schedule leaked 2020 Wild Cards")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = build_task_manifest(
        reg496_ids=reg496,
        if437_ids=if437,
        market72_ids=market72,
    )
    dest = ROOT / "data/ops/nfl-t5151u-cohort-enforcement" / TASK_MANIFEST_NAME
    dest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    digest = sha256_file(dest)
    print(
        json.dumps(
            {
                "task_manifest": str(dest.relative_to(ROOT)),
                "task_manifest_sha256": digest,
                "profiles": {
                    PROFILE_FEATURE_RECON_REG496: {
                        "n": 496,
                        "identity_sha256": REG496_IDENTITY_SHA256,
                        "accepted_artifact_sha256": FEATURE_RECON_REG496_ARTIFACT_SHA256,
                    },
                    PROFILE_DEV_IF437: {
                        "n": 437,
                        "identity_sha256": DEV_IF437_IDENTITY_SHA256,
                    },
                    PROFILE_DEV_MARKET72: {
                        "n": 72,
                        "file_sha256": DEV_MARKET72_FILE_SHA256,
                        "identity_sha256": DEV_MARKET72_IDENTITY_SHA256,
                    },
                },
                "frozen_before_verification": True,
                "cert_candidate": 0,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
