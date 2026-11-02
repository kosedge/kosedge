#!/usr/bin/env python3
"""t5149u — derive REG-only 496 from preserved 502. Identity only. No recon run."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_t5107u.last_played_cohort import (  # noqa: E402
    ORIGINAL_502_PATH,
    ORIGINAL_MATRIX_PATH,
    assert_original_502_bytes,
    derive_reg_only,
    exclusion_manifest,
    frozen_reg_w2plus_ids,
    record_identity_deviation,
)
from src.services.nfl_t5107u.last_played_recon import (  # noqa: E402
    compare_no_bye_to_exact_week,
)
from src.services.nfl_t5107u.recon_driver import sha256_file  # noqa: E402

OUT = ROOT / "data/ops/nfl-t5146u-r4-last-played-dev"
FROZEN_MATRIX = {
    2020: ROOT / "data/ops/nfl-forecast-builder-t5107u/recon/RECON_MATRIX_2020_REG_W2W18.csv",
    2021: ROOT / "data/ops/nfl-forecast-builder-t5107u/recon/RECON_MATRIX_2021_REG_W2W18.csv",
}


def main() -> int:
    assert_original_502_bytes(ROOT)
    original = json.loads((ROOT / ORIGINAL_502_PATH).read_text(encoding="utf-8"))
    if "matrix" not in original:
        # artifact stored identities only; matrix is the sibling CSV
        with (ROOT / ORIGINAL_MATRIX_PATH).open(newline="", encoding="utf-8") as handle:
            original["matrix"] = list(csv.DictReader(handle))
            for row in original["matrix"]:
                if "season" in row:
                    row["season"] = int(row["season"])
                if "week" in row:
                    row["week"] = int(row["week"])
    original_ids = [row["game_id"] for row in original["identities"]]
    schedule_ids = frozen_reg_w2plus_ids(ROOT)
    deviation = record_identity_deviation(original_ids)
    manifest = exclusion_manifest(original_ids)
    derived = derive_reg_only(original, schedule_ids=schedule_ids)

    compares = {}
    for season, path in FROZEN_MATRIX.items():
        season_ident = [r for r in derived["identities"] if r["season"] == season]
        season_matrix = [r for r in derived["matrix"] if int(r["season"]) == season]
        compares[str(season)] = compare_no_bye_to_exact_week(
            season_ident, season_matrix, path
        )
    compares["note"] = {
        "original_2020_no_bye_included_6_wildcard": 216,
        "reg_only_2020_no_bye": compares["2020"]["n_no_bye_games"],
        "2021_no_bye_unchanged": compares["2021"]["n_no_bye_games"],
    }

    matrix_path = OUT / "DEV_RECON_LAST_PLAYED_2020_2021_REG_MATRIX.csv"
    if derived["matrix"]:
        with matrix_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(derived["matrix"][0].keys()))
            writer.writeheader()
            writer.writerows(derived["matrix"])

    slim = {k: v for k, v in derived.items() if k != "matrix"}
    slim["matrix_file"] = str(matrix_path.relative_to(ROOT))
    slim["matrix_file_sha256"] = sha256_file(matrix_path)
    slim["identities_sha256"] = __import__(
        "src.services.nfl_t5107u.recon_driver", fromlist=["sha256_text"]
    ).sha256_text(
        json.dumps(slim["identities"], sort_keys=True, separators=(",", ":"), default=str)
    )
    artifact_path = OUT / "DEV_RECON_LAST_PLAYED_2020_2021_REG.json"
    artifact_path.write_text(json.dumps(slim, indent=2, default=str) + "\n", encoding="utf-8")
    (OUT / "IDENTITY_DEVIATION_502_INCLUDES_2020_WILDCARD.json").write_text(
        json.dumps(deviation, indent=2) + "\n", encoding="utf-8"
    )
    (OUT / "EXCLUSION_MANIFEST_2020_WILDCARD.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (OUT / "NO_BYE_EXACT_WEEK_COMPARE_REG.json").write_text(
        json.dumps(compares, indent=2) + "\n", encoding="utf-8"
    )
    membership = {
        "schema_version": "nfl-t5149u-reg-membership-v1",
        "schedule_path": "data/ops/nfl-forecast-builder-t5107u/inputs/schedule_results_2020_2023.csv",
        "schedule_sha256": "0853342304d269b55033d3474acda853ce00bdb10590f44b09ae569115148479",
        "rule": "season_type=REG AND season in {2020,2021} AND week>=2 — not week<=18",
        "n_schedule": len(schedule_ids),
        "n_derived": derived["n"],
        "n_by_season": derived["n_by_season"],
        "equal": set(schedule_ids) == set(derived["game_ids"]),
        "not_437": derived["n"] != 437,
    }
    (OUT / "REG_SCHEDULE_MEMBERSHIP.json").write_text(
        json.dumps(membership, indent=2) + "\n", encoding="utf-8"
    )
    summary = {
        "original_n": 502,
        "excluded_n": 6,
        "reg_n": derived["n"],
        "reg_by_season": derived["n_by_season"],
        "2020_no_bye_original": 216,
        "2020_no_bye_reg_only": compares["2020"]["n_no_bye_games"],
        "2021_no_bye": compares["2021"]["n_no_bye_games"],
        "no_bye_reg_pass": {
            "2020": compares["2020"]["pass"],
            "2021": compares["2021"]["pass"],
        },
        "artifact_sha256": sha256_file(artifact_path),
        "matrix_sha256": sha256_file(matrix_path),
        "deviation_sha256": sha256_file(OUT / "IDENTITY_DEVIATION_502_INCLUDES_2020_WILDCARD.json"),
        "exclusion_sha256": sha256_file(OUT / "EXCLUSION_MANIFEST_2020_WILDCARD.json"),
        "membership_sha256": sha256_file(OUT / "REG_SCHEDULE_MEMBERSHIP.json"),
        "no_bye_reg_sha256": sha256_file(OUT / "NO_BYE_EXACT_WEEK_COMPARE_REG.json"),
        "original_502_preserved_sha256": "e2f3fab5255430aa31232c7aa3b88e9001461595ef79a00fb3f1e505e51e23b9",
        "cert_candidate": 0,
        "stop": "AWAITING_ALEX_SOURCE_NUMERICAL_IDENTITY_RO",
    }
    (OUT / "COHORT_CORRECTION_t5149u.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
