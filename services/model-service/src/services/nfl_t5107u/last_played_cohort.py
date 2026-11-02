"""t5149u R4 cohort correction — identity/provenance only.

Does not reconstruct, refit, or score. Derives a REG-only view from the
frozen 502 last-played artifact by excluding the six 2020 Wild Card IDs
t5115u already separated from REG. CERT=0.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from .metric_cohorts import WILDCARD_2020_W18
from .recon_driver import sha256_file, sha256_text

ORIGINAL_502_PATH = (
    "data/ops/nfl-t5146u-r4-last-played-dev/DEV_RECON_LAST_PLAYED_2020_2021.json"
)
ORIGINAL_502_SHA256 = (
    "e2f3fab5255430aa31232c7aa3b88e9001461595ef79a00fb3f1e505e51e23b9"
)
ORIGINAL_MATRIX_PATH = (
    "data/ops/nfl-t5146u-r4-last-played-dev/DEV_RECON_LAST_PLAYED_2020_2021_MATRIX.csv"
)
ORIGINAL_MATRIX_SHA256 = (
    "4255f847281a73d1d5e719ca4f4354a675c4e8c82161d0192a49cd4510fe34a9"
)
SCHEDULE_PATH = (
    "data/ops/nfl-forecast-builder-t5107u/inputs/schedule_results_2020_2023.csv"
)
SCHEDULE_SHA256 = (
    "0853342304d269b55033d3474acda853ce00bdb10590f44b09ae569115148479"
)
COHORT_437_N = 437
EXPECTED_REG = {2020: 240, 2021: 256}
EXPECTED_REG_TOTAL = 496
RECOVERED_2021_PARTIALS = (
    "2021_07_ATL_MIA",
    "2021_07_IND_SF",
    "2021_07_NYJ_NE",
    "2021_07_NO_SEA",
    "2021_08_DAL_MIN",
    "2021_08_JAX_SEA",
    "2021_08_MIA_BUF",
    "2021_08_NE_LAC",
    "2021_08_PIT_CLE",
    "2021_09_LV_NYG",
    "2021_09_MIN_BAL",
    "2021_10_DET_PIT",
    "2021_10_SEA_GB",
    "2021_10_TB_WAS",
    "2021_11_BAL_CHI",
    "2021_11_CIN_LV",
    "2021_11_HOU_TEN",
    "2021_11_NYG_TB",
    "2021_12_LAC_DEN",
    "2021_12_LA_GB",
    "2021_13_ARI_CHI",
    "2021_13_DEN_KC",
    "2021_14_ATL_CAR",
    "2021_14_BAL_CLE",
    "2021_14_CHI_GB",
    "2021_14_JAX_TEN",
    "2021_15_NE_IND",
    "2021_15_NYJ_MIA",
    "2021_15_WAS_PHI",
)


class CohortRefuse(ValueError):
    """Fail-closed REG cohort correction."""


def assert_original_502_bytes(root: Path) -> None:
    path = root / ORIGINAL_502_PATH
    digest = sha256_file(path)
    if digest != ORIGINAL_502_SHA256:
        raise CohortRefuse(
            f"original 502 artifact sha {digest} != preserved {ORIGINAL_502_SHA256}"
        )
    matrix = root / ORIGINAL_MATRIX_PATH
    matrix_digest = sha256_file(matrix)
    if matrix_digest != ORIGINAL_MATRIX_SHA256:
        raise CohortRefuse(
            f"original 502 matrix sha {matrix_digest} != preserved {ORIGINAL_MATRIX_SHA256}"
        )


def frozen_reg_w2plus_ids(root: Path) -> list[str]:
    """REG membership from owned PBP schedule extract — not week<=18."""
    path = root / SCHEDULE_PATH
    digest = sha256_file(path)
    if digest != SCHEDULE_SHA256:
        raise CohortRefuse(f"schedule sha {digest} != pin {SCHEDULE_SHA256}")
    ids: list[str] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            season = int(row["season"])
            week = int(row["week"])
            if season not in (2020, 2021):
                continue
            if str(row["season_type"]).upper() != "REG":
                continue
            if week < 2:
                continue
            ids.append(str(row["game_id"]))
    return ids


def record_identity_deviation(
    original_ids: Sequence[str],
) -> dict[str, Any]:
    present = [gid for gid in WILDCARD_2020_W18 if gid in set(original_ids)]
    missing = [gid for gid in WILDCARD_2020_W18 if gid not in set(original_ids)]
    by_season = Counter(int(gid.split("_", 1)[0]) for gid in original_ids)
    return {
        "schema_version": "nfl-t5149u-identity-deviation-v1",
        "cert_candidate": 0,
        "original_n": len(original_ids),
        "do_not_accept_as_regular_season_coverage": True,
        "n_is_not_declared_reg": True,
        "declared_reg_eligible_2020_2021": EXPECTED_REG_TOTAL,
        "original_n_by_season": {str(k): v for k, v in sorted(by_season.items())},
        "deviation": {
            "kind": "NON_REG_WILDCARD",
            "source": "t5115u IDENTITY_RESOLUTION_2020 / WILDCARD_2020_W18",
            "reason": (
                "2020 REG ended week 17 (256 games). games.csv week=18 rows are "
                "Jan 9–11 2021 Wild Card. week<=18 admitted them. Not extra REG."
            ),
            "game_ids": list(WILDCARD_2020_W18),
            "n": len(WILDCARD_2020_W18),
            "present_in_original_502": present,
            "missing_from_original_502": missing,
        },
        "original_artifact": {
            "path": ORIGINAL_502_PATH,
            "sha256": ORIGINAL_502_SHA256,
            "preserved": True,
            "rewritten": False,
        },
        "not_the_437_previously_complete_cohort": True,
        "cohort_437_n": COHORT_437_N,
    }


def derive_reg_only(
    original: Mapping[str, Any],
    *,
    schedule_ids: Sequence[str],
) -> dict[str, Any]:
    exclude = set(WILDCARD_2020_W18)
    schedule = set(schedule_ids)
    identities = [
        row
        for row in original.get("identities") or []
        if str(row["game_id"]) not in exclude
    ]
    matrix = [
        row
        for row in original.get("matrix") or []
        if str(row["game_id"]) not in exclude
    ]
    complete = [
        gid for gid in (original.get("complete_game_ids") or []) if gid not in exclude
    ]
    derived_ids = [str(row["game_id"]) for row in identities]
    if len(derived_ids) != EXPECTED_REG_TOTAL:
        raise CohortRefuse(
            f"derived n {len(derived_ids)} != expected REG {EXPECTED_REG_TOTAL}"
        )
    by_season = Counter(int(gid.split("_", 1)[0]) for gid in derived_ids)
    if dict(by_season) != EXPECTED_REG:
        raise CohortRefuse(f"derived by season {dict(by_season)} != {EXPECTED_REG}")
    if set(derived_ids) != schedule:
        extra = sorted(set(derived_ids) - schedule)
        missing = sorted(schedule - set(derived_ids))
        raise CohortRefuse(
            f"derived IDs != frozen REG W2+ schedule extra={extra} missing={missing}"
        )
    if exclude & set(derived_ids):
        raise CohortRefuse("Wild Card IDs leaked into REG-only derivative")
    w18_2021 = sorted(gid for gid in derived_ids if gid.startswith("2021_18_"))
    if len(w18_2021) != 16:
        raise CohortRefuse(f"2021 REG week 18 count {len(w18_2021)} != 16")
    missing_recovered = [gid for gid in RECOVERED_2021_PARTIALS if gid not in set(derived_ids)]
    if missing_recovered:
        raise CohortRefuse(f"recovered 2021 cases dropped: {missing_recovered}")
    if len(derived_ids) == COHORT_437_N:
        raise CohortRefuse("derived n collapsed to the 437 previously-complete cohort")
    return {
        "schema_version": "nfl-t5149u-reg-only-derivative-v1",
        "path_id": "R4_LAST_PLAYED_T2_DEV_REG",
        "derived_from": ORIGINAL_502_PATH,
        "derived_from_sha256": ORIGINAL_502_SHA256,
        "original_preserved": True,
        "original_n": 502,
        "excluded_n": 6,
        "n": len(derived_ids),
        "n_by_season": {str(k): v for k, v in sorted(by_season.items())},
        "n_complete_27": len(complete),
        "n_partial": 0,
        "n_refused": 0,
        "cert_candidate": 0,
        "eval": None,
        "scored_look": False,
        "scientific_choice_changed": False,
        "accuracy_run": False,
        "label": original.get("label"),
        "fit_label": original.get("fit_label"),
        "game_ids": derived_ids,
        "complete_game_ids": complete,
        "identities": identities,
        "matrix": matrix,
        "recovered_2021_partials_retained": list(RECOVERED_2021_PARTIALS),
        "reg_week18_2021_retained": w18_2021,
        "wildcard_2020_excluded": list(WILDCARD_2020_W18),
        "schedule_pin": SCHEDULE_SHA256,
        "membership_rule": "season_type=REG on schedule_results_2020_2023.csv; week>=2; not week<=18",
        "not_the_437_previously_complete_cohort": True,
        "publication_timestamp_status": "unverified",
        "observation_timestamp_status": "unverified",
        "production_causal_claim": False,
    }


def exclusion_manifest(original_ids: Sequence[str]) -> dict[str, Any]:
    rows = []
    original_set = set(original_ids)
    for gid in WILDCARD_2020_W18:
        if gid not in original_set:
            raise CohortRefuse(f"{gid} not in original 502 — exclusion set drifted")
        rows.append(
            {
                "game_id": gid,
                "classification": "NON_REG_WILDCARD",
                "season": 2020,
                "week": 18,
                "in_declared_reg_2020": False,
                "reason": "t5115u: 2020 REG ended week 17; this ID is Wild Card POST",
            }
        )
    return {
        "schema_version": "nfl-t5149u-exclusion-manifest-v1",
        "cert_candidate": 0,
        "exclude_exactly": list(WILDCARD_2020_W18),
        "n": 6,
        "source": "services/model-service/src/services/nfl_t5107u/metric_cohorts.py WILDCARD_2020_W18",
        "t5115u_identity": "data/ops/nfl-forecast-builder-t5107u/IDENTITY_RESOLUTION_2020_t5115u.json",
        "not_a_week_le_18_filter": True,
        "does_not_exclude_2021_reg_week_18": True,
        "rows": rows,
    }
