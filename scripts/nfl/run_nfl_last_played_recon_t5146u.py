#!/usr/bin/env python3
"""t5146u R4 ONE EXEC — 2020–21 DEV last-played reconstruction.

Opt-in path only. Does not call reconstruct_slate (exact-week).
No 2022–26. No EVAL. No target scores in the artifact. CERT=0.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_t5107u.inputs import SOURCE_SHA, sha256_file  # noqa: E402
from src.services.nfl_t5107u.last_played_recon import (  # noqa: E402
    DEV_SEASONS,
    classify_2021_previous_partials,
    compare_no_bye_to_exact_week,
    reconstruct_slate_last_played,
)
from src.services.nfl_t5107u.recon_driver import (  # noqa: E402
    DEFAULT_PBP_ARCHIVE,
    HELPER_SHA256,
    attach_kickoffs,
    load_games_identity,
    load_pbp_plays,
    load_prior_scores,
    load_verified_helper,
    sha256_text,
)

PREVIOUS_2021_PARTIALS = [
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
]
FROZEN_MATRIX = {
    2020: ROOT / "data/ops/nfl-forecast-builder-t5107u/recon/RECON_MATRIX_2020_REG_W2W18.csv",
    2021: ROOT / "data/ops/nfl-forecast-builder-t5107u/recon/RECON_MATRIX_2021_REG_W2W18.csv",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        default=str(ROOT / "data/ops/nfl-t5146u-r4-last-played-dev"),
    )
    parser.add_argument("--go", required=True, help="must be 686ce4dc")
    args = parser.parse_args()
    if args.go != "686ce4dc":
        raise SystemExit("refusing EXEC without Alex PREFLIGHT GO 686ce4dc")

    helper = load_verified_helper()
    games = [
        g
        for g in load_games_identity()
        if int(g["season"]) in DEV_SEASONS and 1 <= int(g["week"]) <= 18
    ]
    missing_2023 = Path("/tmp/t5146u-no-2023-scores-do-not-create")
    completed = attach_kickoffs(
        load_prior_scores(helper=helper, scores_2023_path=missing_2023),
        games,
    )
    completed = [row for row in completed if int(row["season"]) in DEV_SEASONS]
    targets = [g for g in games if int(g["week"]) >= 2]
    plays = load_pbp_plays(
        archive=DEFAULT_PBP_ARCHIVE,
        seasons=DEV_SEASONS,
        max_week=17,
        helper=helper,
    )
    pbp_sha = {season: SOURCE_SHA[season] for season in DEV_SEASONS}
    for season, digest in pbp_sha.items():
        path = DEFAULT_PBP_ARCHIVE / f"play_by_play_{season}.csv"
        got = sha256_file(path)
        if got != digest:
            raise SystemExit(f"PBP {season} sha {got} != pin {digest}")

    result = reconstruct_slate_last_played(
        targets=targets,
        games=games,
        completed_prior=completed,
        helper=helper,
        plays=plays,
        pbp_sha_by_season=pbp_sha,
    )
    if result["target_scoring_labels_loaded"] or result["error_join"]:
        raise SystemExit("artifact contract violated")

    compares = {}
    for season, path in FROZEN_MATRIX.items():
        season_ident = [r for r in result["identities"] if r["season"] == season]
        season_matrix = [r for r in result["matrix"] if r["season"] == season]
        compares[str(season)] = compare_no_bye_to_exact_week(
            season_ident, season_matrix, path
        )
    if any(not item["pass"] for item in compares.values()):
        raise SystemExit(f"no-bye exact-week compare failed: {compares}")

    prev = classify_2021_previous_partials(
        PREVIOUS_2021_PARTIALS,
        complete=result["complete_game_ids"],
        partial=result["partial"],
        refused=result["refused"],
        identities=result["identities"],
    )

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    matrix_path = out / "DEV_RECON_LAST_PLAYED_2020_2021_MATRIX.csv"
    if result["matrix"]:
        with matrix_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(result["matrix"][0].keys()))
            writer.writeheader()
            writer.writerows(result["matrix"])

    artifact = {
        k: v
        for k, v in result.items()
        if k != "matrix"
    }
    artifact["matrix_file"] = str(matrix_path.relative_to(ROOT))
    artifact["matrix_file_sha256"] = sha256_file(matrix_path) if matrix_path.is_file() else ""
    artifact["written_at_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    artifact_path = out / "DEV_RECON_LAST_PLAYED_2020_2021.json"
    artifact_path.write_text(
        json.dumps(artifact, indent=2, default=str) + "\n", encoding="utf-8"
    )
    prev_path = out / "DEV_RECON_2021_PREVIOUSLY_PARTIAL.json"
    prev_path.write_text(json.dumps(prev, indent=2) + "\n", encoding="utf-8")
    compare_path = out / "NO_BYE_EXACT_WEEK_COMPARE.json"
    compare_path.write_text(json.dumps(compares, indent=2) + "\n", encoding="utf-8")

    summary = {
        "schema_version": "nfl-t5146u-r4-last-played-exec-v1",
        "cert_candidate": 0,
        "alex_preflight_go": "686ce4dc",
        "helper_sha256": HELPER_SHA256,
        "n_targets": result["n_targets"],
        "n_complete_27": result["n_complete_27"],
        "n_partial": result["n_partial"],
        "n_refused": result["n_refused"],
        "matrix_sha256": result["matrix_sha256"],
        "identities_sha256": result["identities_sha256"],
        "artifact_file_sha256": sha256_file(artifact_path),
        "matrix_file_sha256": sha256_file(matrix_path),
        "previous_partial_file_sha256": sha256_file(prev_path),
        "no_bye_compare_file_sha256": sha256_file(compare_path),
        "n_2021_previous_partial_now_complete": prev["n_now_complete"],
        "n_2021_previous_partial_still": prev["n_still_refused_or_partial"],
        "no_bye_compare_pass": {k: v["pass"] for k, v in compares.items()},
        "label": "RECONSTRUCTED",
        "fit_label": "RETRO_FIT",
        "eval": None,
        "stop": "AWAITING_ALEX_PHASE_B_RO",
    }
    summary_path = out / "EXEC_RESULT_t5146u.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    summary["exec_result_sha256"] = sha256_file(summary_path)
    print(json.dumps({**summary, "exec_result_sha256": sha256_text(json.dumps(summary, sort_keys=True))}, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
