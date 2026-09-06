#!/usr/bin/env python3
"""Path B clean-checkout recovery for the 2024–25 sealed holdout.

Deterministically rebuilds into a staging directory, verifies canonical pack +
content + manifest + seal hashes against locked v1.1 expectations, then
atomically promotes. The live seal is never unlinked/overwritten before
successful verification.

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
from ncaam_lab.holdout_2425.locked_identity import (  # noqa: E402
    V1_1_CANONICAL_PACK_AS_OF,
    locked_expected_hashes,
)
from ncaam_lab.holdout_2425.path_b_promote import (  # noqa: E402
    PromoteVerificationError,
    cleanup_staging,
    collect_staging_hashes,
    promote_staging_to_live,
    verify_against_locked,
)


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


def _remap_build_paths(build_mod: Any, *, out_root: Path, pack_path: Path) -> None:
    """Point builder constants at the staging tree (live seal untouched)."""
    mapping = {
        "OUT_ROOT": out_root,
        "SCHEDULE_DIR": out_root / "schedule_sot",
        "VENUE_DIR": out_root / "venue",
        "KENPOM_DIR": out_root / "kenpom_audit",
        "ODDS_DIR": out_root / "odds_audit",
        "FEATURE_DIR": out_root / "feature_package",
        "LABEL_DIR": out_root / "label_package",
        "SEAL_DIR": out_root / "seal",
        "QUARANTINE_DIR": out_root / "quarantine",
        "REJECTED_DIR": out_root / "rejected",
        "CANONICAL_PACK_PATH": pack_path,
    }
    for attr, val in mapping.items():
        setattr(build_mod.C, attr, val)
    # seal_package imports dirs by name at call time via constants / out_root;
    # builder passes through C.* only — also patch seal_mod module attrs used
    # when out_root is None (build uses seal_mod without out_root).
    for attr in ("FEATURE_DIR", "LABEL_DIR", "REJECTED_DIR", "SEAL_DIR"):
        setattr(build_mod.seal_mod, attr, mapping[attr])


def rebuild(
    *,
    dry_run: bool = False,
    require_locked_hashes: bool = True,
    staging_root: Path | None = None,
) -> Dict[str, Any]:
    inputs = _require_governed_inputs()
    live_seal_path = C.SEAL_DIR / "seal_receipt.json"
    live_seal_side = C.SEAL_DIR / "seal_receipt.file_sha256"
    live_seal_before = None
    if live_seal_path.exists():
        live_seal_before = live_seal_path.read_bytes()

    receipt: Dict[str, Any] = {
        "recovery_path": "B_deterministic_rebuild_from_governed_inputs",
        "manual_placement_required": False,
        "odds_api_calls_made": False,
        "inputs": inputs,
        "dry_run": dry_run,
        "live_seal_preserved_until_verify": True,
        "live_seal_existed_before": live_seal_before is not None,
        "require_locked_hashes": require_locked_hashes,
        "locked_expected_hashes": locked_expected_hashes(),
    }
    if dry_run:
        receipt["status"] = "DRY_RUN_INPUTS_PRESENT"
        return receipt

    staging = staging_root or (C.OUT_ROOT / "_path_b_staging")
    staging_pack = C.CANONICAL_PACK_PATH.with_name(
        C.CANONICAL_PACK_PATH.name + ".path_b_staging"
    )
    # Fresh staging; do NOT touch live seal.
    if staging.exists():
        cleanup_staging(staging, None)
    staging.mkdir(parents=True, exist_ok=True)

    try:
        ingest = _load_module(
            "ingest_espn_official_schedule",
            REPO / "scripts" / "ncaam" / "ingest_espn_official_schedule.py",
        )
        build_mod = _load_module(
            "build_2425_sealed_holdout",
            REPO / "scripts" / "ncaam" / "build_2425_sealed_holdout.py",
        )
        _remap_build_paths(build_mod, out_root=staging, pack_path=staging_pack)

        pack = ingest.ingest_from_raw_dir(
            season_key=C.SEASON_KEY,
            raw_dir=C.RAW_ESPN_DIR,
            start=C.WINDOW_START,
            end=C.WINDOW_END,
            as_of=V1_1_CANONICAL_PACK_AS_OF,
        )
        staging_pack.parent.mkdir(parents=True, exist_ok=True)
        staging_pack.write_text(
            json.dumps(pack, indent=2) + "\n", encoding="utf-8"
        )
        receipt["staging_pack_path"] = str(staging_pack)
        receipt["canonical_pack_n_games"] = pack.get("n_games")

        summary = build_mod.build(season=C.SEASON_KEY)
        staging_seal = staging / "seal" / "seal_receipt.json"
        if not staging_seal.exists():
            raise SystemExit(
                "FAIL-CLOSED: staging rebuild finished but seal_receipt.json missing"
            )

        # Live seal must still be untouched at this point.
        if live_seal_before is not None:
            if not live_seal_path.exists():
                raise SystemExit(
                    "FAIL-CLOSED: live seal disappeared before promote "
                    "(staging/verify must never unlink live seal)"
                )
            if live_seal_path.read_bytes() != live_seal_before:
                raise SystemExit(
                    "FAIL-CLOSED: live seal mutated before successful verification"
                )

        actual_hashes = collect_staging_hashes(
            staging_root=staging, staging_pack_path=staging_pack
        )
        receipt["staging_hashes"] = actual_hashes
        if require_locked_hashes:
            verify_against_locked(actual_hashes)
            receipt["locked_hash_verification"] = "PASS"
        else:
            receipt["locked_hash_verification"] = "SKIPPED"

        promote_receipt = promote_staging_to_live(
            staging_root=staging,
            staging_pack_path=staging_pack,
            live_root=C.OUT_ROOT,
            live_pack_path=C.CANONICAL_PACK_PATH,
            live_seal_dir=C.SEAL_DIR,
        )
        receipt["promote"] = promote_receipt
        receipt.update(
            {
                "status": "REBUILT_VERIFIED_PROMOTED",
                "seal_payload_sha256": summary.get("seal_payload_sha256"),
                "seal_file_sha256": summary.get("seal_file_sha256"),
                "readiness_status": summary.get("readiness_status"),
                "seal_path": str(live_seal_path.relative_to(REPO))
                if live_seal_path.exists()
                else str(C.SEAL_DIR / "seal_receipt.json"),
                "canonical_pack_path": str(C.CANONICAL_PACK_PATH.relative_to(REPO)),
            }
        )
        return receipt
    except PromoteVerificationError as exc:
        # Refuse promotion; preserve live seal bytes.
        if live_seal_before is not None:
            if (
                not live_seal_path.exists()
                or live_seal_path.read_bytes() != live_seal_before
            ):
                live_seal_path.parent.mkdir(parents=True, exist_ok=True)
                live_seal_path.write_bytes(live_seal_before)
        receipt.update(
            {
                "status": "REFUSED_PROMOTION_HASH_MISMATCH",
                "error": str(exc),
                "live_seal_preserved": True,
                "live_seal_sidecar_untouched": live_seal_side.exists()
                if live_seal_before is not None
                else None,
            }
        )
        exc.receipt = receipt  # type: ignore[attr-defined]
        raise
    finally:
        cleanup_staging(staging, staging_pack)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate governed inputs only; do not rebuild.",
    )
    parser.add_argument(
        "--skip-locked-hash-check",
        action="store_true",
        help=(
            "Staging verify still runs integrity checks, but do not require "
            "exact locked v1.1 hash match (debug only)."
        ),
    )
    args = parser.parse_args(argv)
    try:
        receipt = rebuild(
            dry_run=args.dry_run,
            require_locked_hashes=not args.skip_locked_hash_check,
        )
    except PromoteVerificationError as exc:
        receipt = getattr(exc, "receipt", {"status": "REFUSED_PROMOTION_HASH_MISMATCH"})
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 2
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
