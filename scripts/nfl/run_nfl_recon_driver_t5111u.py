#!/usr/bin/env python3
"""t5111u limited 2020–23 reconstruction (default: 2023 REG W2).

Imports hash-verified helper 7e77c57f. Does not call helper.main / OOS.
Does not open 1ee90fac. CERT=0. Not a scored look.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_t5107u.inputs import SOURCE_SHA, sha256_file  # noqa: E402
from src.services.nfl_t5107u.recon_driver import (  # noqa: E402
    DEFAULT_PBP_ARCHIVE,
    HELPER_SHA256,
    attach_kickoffs,
    freeze_completeness,
    load_games_identity,
    load_prior_scores,
    load_verified_helper,
    reconstruct_slate,
    write_recon_bindings,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, default=2023)
    parser.add_argument("--week", type=int, default=2)
    parser.add_argument(
        "--out",
        default=str(ROOT / "data/ops/nfl-forecast-builder-t5107u/recon"),
    )
    args = parser.parse_args()
    helper = load_verified_helper()
    games = load_games_identity()
    completed = attach_kickoffs(load_prior_scores(helper=helper), games)
    targets = [
        g
        for g in games
        if int(g["season"]) == args.season and int(g["week"]) == args.week
    ]
    if not targets:
        raise SystemExit(f"no targets for {args.season} W{args.week}")
    prior_targets = [
        g for g in games if int(g["season"]) == args.season and int(g["week"]) <= args.week
    ]
    seal = freeze_completeness(prior_targets, completed, helper)
    pbp_sha = {args.season: SOURCE_SHA[args.season]}
    result = reconstruct_slate(
        targets=targets,
        games=games,
        completed=completed,
        helper=helper,
        archive=DEFAULT_PBP_ARCHIVE,
        pbp_sha_by_season=pbp_sha,
        completeness_seal=seal,
    )
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    matrix_path = out / f"RECON_MATRIX_{args.season}_W{args.week}.csv"
    if result["matrix"]:
        with matrix_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(result["matrix"][0].keys()))
            writer.writeheader()
            writer.writerows(result["matrix"])
    bindings_path = out / "RECON_BINDINGS.json"
    write_recon_bindings(result, bindings_path)
    seal_path = out / f"COMPLETENESS_SEAL_{args.season}_W{args.week}.json"
    seal_path.write_text(json.dumps(seal, indent=2, default=str) + "\n", encoding="utf-8")
    summary = {
        "helper_sha256": HELPER_SHA256,
        "season": args.season,
        "week": args.week,
        "n_targets": len(targets),
        "n_eligible": seal["n_eligible"],
        "n_excluded": seal["n_excluded"],
        "completeness_sha256": seal["completeness_sha256"],
        "matrix_sha256": result["matrix_sha256"],
        "matrix_file_sha256": sha256_file(matrix_path) if matrix_path.is_file() else "",
        "n_complete_27": result["n_complete_27"],
        "n_partial": result["n_partial"],
        "n_cells": result["n_cells"],
        "label": result["label"],
        "cert_candidate": 0,
    }
    (out / f"RECON_SUMMARY_{args.season}_W{args.week}.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
