#!/usr/bin/env python3
"""NFL #564 remat + integrity (research only).

Packaged EPA, personnel/injury overlays OFF. Does not write Railway,
does not flip Coming soon, does not change the scoring equation.

  PYTHONPATH=services/model-service python3 scripts/nfl/nfl_564_remediation_remat.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MS_SRC = ROOT / "services" / "model-service"
if str(MS_SRC) not in sys.path:
    sys.path.insert(0, str(MS_SRC))

from src.services.nfl_epa_authority import (  # noqa: E402
    NFL_564_REMEDIATION,
    PRODUCTION_PROMOTE,
    build_multi_matchup_integrity_report,
    rematerialize_week_epa_overlays_off,
    sha256_canonical,
    week1_outcomes_coverage_fixture,
)

OUT_DIR = ROOT / "data" / "ops" / "nfl-564-remediation-20260915"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    coverage = week1_outcomes_coverage_fixture()
    remat = rematerialize_week_epa_overlays_off(run_id=f"{NFL_564_REMEDIATION}-w2")
    integrity = build_multi_matchup_integrity_report(remat=remat)
    summary = {
        "run_id": NFL_564_REMEDIATION,
        "production_promote": PRODUCTION_PROMOTE,
        "recommendation": "HOLD_PUBLIC",
        "coming_soon": True,
        "scoring_equation_changed": False,
        "before_readiness_sample_size": coverage["before_ingest_sample_size"],
        "after_readiness_sample_size": coverage["after_ingest_sample_size"],
        "week1_last_game_date": coverage["last_game_date"],
        "w2_remat_run_id": remat["run_id"],
        "w2_remat_checksum_sha256": remat["checksum_sha256"],
        "w2_game_count": remat["game_count"],
        "integrity_checksum_sha256": integrity["checksum_sha256"],
        "integrity_passed": integrity["passed"],
        "double_count_check": integrity["double_count_check"],
        "overlays_off": True,
    }
    summary["checksum_sha256"] = sha256_canonical(summary)

    (OUT_DIR / "week1_outcomes_coverage.json").write_text(
        json.dumps(coverage, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (OUT_DIR / "w2_remat_epa_overlays_off.json").write_text(
        json.dumps(remat, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (OUT_DIR / "multi_matchup_integrity.json").write_text(
        json.dumps(integrity, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (OUT_DIR / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print("NFL #564 remat artifact (research only)")
    print(f"run_id={summary['run_id']}")
    print(
        f"readiness sample_size {summary['before_readiness_sample_size']} -> "
        f"{summary['after_readiness_sample_size']}"
    )
    print(f"w2 remat checksum {summary['w2_remat_checksum_sha256']}")
    print(f"integrity {summary['double_count_check']} checksum {summary['integrity_checksum_sha256']}")
    print(f"production_promote={PRODUCTION_PROMOTE} recommendation=HOLD_PUBLIC")
    print(f"wrote {OUT_DIR}")
    return 0 if integrity["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
