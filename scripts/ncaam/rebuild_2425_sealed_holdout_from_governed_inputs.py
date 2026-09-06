#!/usr/bin/env python3
"""Path B clean-checkout recovery for the 2024–25 sealed holdout.

Deterministically rebuilds:
  1) canonical schedule pack from governed ESPN raw (+ verified sha256 sidecars)
  2) sealed feature/label packages via the sealed-holdout builder

No manual placement of deferred schedule pack or sealed packages.
No Odds API calls. Fail-closed if governed inputs are missing.

Prerequisites (governed):
  - data/ops/lab/ncaam/holdout_2024_25/raw/espn_scoreboard/*.json + *.sha256
    (hydrate from locked R2 role espn_schedule_raw_v1 when absent)
  - apps/web/data/processed/kenpom_snapshots/
  - apps/web/data/processed/ncaab_historical_odds_open_close.parquet

Usage:
  python scripts/ncaam/rebuild_2425_sealed_holdout_from_governed_inputs.py
  python scripts/ncaam/rebuild_2425_sealed_holdout_from_governed_inputs.py --dry-run
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parents[2]
WEB_SRC = REPO / "apps" / "web" / "src"
if str(WEB_SRC) not in sys.path:
    sys.path.insert(0, str(WEB_SRC))

from ncaam_lab.holdout_2425 import constants as C  # noqa: E402


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Unable to load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _require_governed_inputs() -> Dict[str, Any]:
    missing: List[str] = []
    if not C.RAW_ESPN_DIR.exists():
        missing.append(str(C.RAW_ESPN_DIR.relative_to(REPO)))
    else:
        n_json = len(list(C.RAW_ESPN_DIR.glob("espn_scoreboard_*.json")))
        if n_json <= 0:
            missing.append(f"{C.RAW_ESPN_DIR.relative_to(REPO)} (empty)")
    if not C.KENPOM_SNAPSHOT_DIR.exists():
        missing.append(str(C.KENPOM_SNAPSHOT_DIR.relative_to(REPO)))
    if not C.ODDS_PARQUET.exists():
        missing.append(str(C.ODDS_PARQUET.relative_to(REPO)))
    if missing:
        raise SystemExit(
            "FAIL-CLOSED: governed inputs missing for path-B rebuild:\n  - "
            + "\n  - ".join(missing)
            + "\nHydrate ESPN raw from locked R2 first "
            "(scripts/ncaam/hydrate_2425_sealed_holdout_from_r2.py). "
            "Do not manually place hash-only seal artifacts."
        )
    return {
        "raw_espn_dir": str(C.RAW_ESPN_DIR.relative_to(REPO)),
        "kenpom_snapshot_dir": str(C.KENPOM_SNAPSHOT_DIR.relative_to(REPO)),
        "odds_parquet": str(C.ODDS_PARQUET.relative_to(REPO)),
    }


def rebuild(*, dry_run: bool = False) -> Dict[str, Any]:
    inputs = _require_governed_inputs()
    receipt: Dict[str, Any] = {
        "recovery_path": "B_deterministic_rebuild_from_governed_inputs",
        "manual_placement_required": False,
        "odds_api_calls_made": False,
        "inputs": inputs,
        "dry_run": dry_run,
    }
    if dry_run:
        receipt["status"] = "DRY_RUN_INPUTS_PRESENT"
        return receipt

    # Remove any pre-seeded seal so recovery cannot quietly reuse hash-only artifacts.
    seal_path = C.SEAL_DIR / "seal_receipt.json"
    seal_side = C.SEAL_DIR / "seal_receipt.file_sha256"
    for p in (seal_path, seal_side):
        if p.exists():
            p.unlink()

    ingest = _load_module(
        "ingest_espn_official_schedule",
        REPO / "scripts" / "ncaam" / "ingest_espn_official_schedule.py",
    )
    build_mod = _load_module(
        "build_2425_sealed_holdout",
        REPO / "scripts" / "ncaam" / "build_2425_sealed_holdout.py",
    )

    pack = ingest.ingest_from_raw_dir(
        season_key=C.SEASON_KEY,
        raw_dir=C.RAW_ESPN_DIR,
        start=C.WINDOW_START,
        end=C.WINDOW_END,
    )
    C.CANONICAL_PACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    C.CANONICAL_PACK_PATH.write_text(
        json.dumps(pack, indent=2) + "\n", encoding="utf-8"
    )
    receipt["canonical_pack_path"] = str(C.CANONICAL_PACK_PATH.relative_to(REPO))
    receipt["canonical_pack_n_games"] = pack.get("n_games")

    summary = build_mod.build(season=C.SEASON_KEY)
    if not seal_path.exists():
        raise SystemExit("FAIL-CLOSED: rebuild finished but seal_receipt.json missing")
    receipt.update(
        {
            "status": "REBUILT",
            "seal_payload_sha256": summary.get("seal_payload_sha256"),
            "seal_file_sha256": summary.get("seal_file_sha256"),
            "readiness_status": summary.get("readiness_status"),
            "seal_path": str(seal_path.relative_to(REPO)),
        }
    )
    return receipt


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate governed inputs only; do not rebuild.",
    )
    args = parser.parse_args(argv)
    receipt = rebuild(dry_run=args.dry_run)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
