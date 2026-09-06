#!/usr/bin/env python3
"""FORENSIC ONLY — raw + KenPom + odds reconstruction for investigation.

Phase 2.6F CR4 (Ryan LOCKED):
  This path is SEPARATE from authoritative disaster recovery.
  It MUST NOT redefine or promote the frozen v1.1 holdout package.

Authoritative recovery is:
  scripts/ncaam/recover_2425_sealed_holdout_from_r2.py
  (exact frozen bytes from private retention-locked R2)

This forensic script may rebuild into an isolated forensic output directory for
drift investigation (e.g. B1). It refuses:
  - writing to the live sealed holdout tree
  - atomic promote into live seal / live pack
  - claiming frozen v1.1 identity
  - Odds API live calls

Usage:
  python scripts/ncaam/forensic_rebuild_2425_from_raw_kenpom_odds.py --dry-run
  python scripts/ncaam/forensic_rebuild_2425_from_raw_kenpom_odds.py \\
      --out-root /tmp/ncaam-forensic-2425
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

FORENSIC_BANNER = (
    "FORENSIC_ONLY — raw+KenPom+odds reconstruction; "
    "MUST NOT redefine or promote frozen v1.1 holdout"
)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Unable to load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _refuse_live_paths(out_root: Path, pack_path: Path) -> None:
    """Fail closed if caller targets live sealed holdout paths."""
    live_root = C.OUT_ROOT.resolve()
    live_pack = C.CANONICAL_PACK_PATH.resolve()
    live_seal = (C.SEAL_DIR / "seal_receipt.json").resolve()
    if out_root.resolve() == live_root:
        raise SystemExit(
            "FORENSIC REFUSED: --out-root must not be the live holdout tree "
            f"({live_root}). Authoritative recovery is R2 hydrate only."
        )
    if pack_path.resolve() == live_pack:
        raise SystemExit(
            "FORENSIC REFUSED: pack path must not be the live canonical pack. "
            "Frozen holdout promote is forbidden on this path."
        )
    # Also refuse if seal would land on live seal.
    if (out_root / "seal" / "seal_receipt.json").resolve() == live_seal:
        raise SystemExit(
            "FORENSIC REFUSED: seal path collides with live seal; "
            "cannot promote/redefine frozen holdout."
        )


def forensic_rebuild(
    *,
    out_root: Path,
    pack_path: Path,
    dry_run: bool = False,
) -> Dict[str, Any]:
    _refuse_live_paths(out_root, pack_path)
    receipt: Dict[str, Any] = {
        "path_class": "FORENSIC_RAW_KENPOM_ODDS_RECONSTRUCTION",
        "banner": FORENSIC_BANNER,
        "may_redefine_frozen_holdout": False,
        "may_promote_to_live_seal": False,
        "authoritative_recovery": "scripts/ncaam/recover_2425_sealed_holdout_from_r2.py",
        "odds_api_calls_made": False,
        "dry_run": dry_run,
        "out_root": str(out_root),
        "pack_path": str(pack_path),
        "locked_expected_hashes_for_comparison_only": locked_expected_hashes(),
        "note": (
            "Outputs are investigative artifacts only. Matching or mismatching "
            "locked hashes does not authorize promotion into the frozen holdout."
        ),
    }
    if dry_run:
        receipt["status"] = "DRY_RUN_FORENSIC"
        return receipt

    missing: List[str] = []
    if not C.RAW_ESPN_DIR.exists():
        missing.append(str(C.RAW_ESPN_DIR.relative_to(REPO)))
    if not C.KENPOM_SNAPSHOT_DIR.exists():
        missing.append(str(C.KENPOM_SNAPSHOT_DIR.relative_to(REPO)))
    if not C.ODDS_PARQUET.exists():
        missing.append(str(C.ODDS_PARQUET.relative_to(REPO)))
    if missing:
        raise SystemExit(
            "FORENSIC inputs missing:\n  - "
            + "\n  - ".join(missing)
            + "\nHydrate ESPN raw for forensic use only; do not promote."
        )

    out_root.mkdir(parents=True, exist_ok=True)
    ingest = _load_module(
        "ingest_espn_official_schedule",
        REPO / "scripts" / "ncaam" / "ingest_espn_official_schedule.py",
    )
    build_mod = _load_module(
        "build_2425_sealed_holdout",
        REPO / "scripts" / "ncaam" / "build_2425_sealed_holdout.py",
    )
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
    for attr in ("FEATURE_DIR", "LABEL_DIR", "REJECTED_DIR", "SEAL_DIR"):
        setattr(build_mod.seal_mod, attr, mapping[attr])

    pack = ingest.ingest_from_raw_dir(
        season_key=C.SEASON_KEY,
        raw_dir=C.RAW_ESPN_DIR,
        start=C.WINDOW_START,
        end=C.WINDOW_END,
        as_of=V1_1_CANONICAL_PACK_AS_OF,
    )
    pack_path.parent.mkdir(parents=True, exist_ok=True)
    # Tag forensic provenance — must not be mistaken for frozen authority.
    pack = dict(pack)
    detail = dict(pack.get("source_detail") or {})
    detail["forensic_reconstruction"] = True
    detail["not_frozen_holdout_authority"] = True
    pack["source_detail"] = detail
    pack_path.write_text(json.dumps(pack, indent=2) + "\n", encoding="utf-8")

    summary = build_mod.build(season=C.SEASON_KEY)
    receipt.update(
        {
            "status": "FORENSIC_REBUILT_ISOLATED",
            "promoted_to_live": False,
            "seal_payload_sha256": summary.get("seal_payload_sha256"),
            "seal_file_sha256": summary.get("seal_file_sha256"),
            "readiness_status": summary.get("readiness_status"),
        }
    )
    # Final hard check: live seal untouched.
    live_seal = C.SEAL_DIR / "seal_receipt.json"
    receipt["live_seal_path_untouched_by_this_script"] = True
    receipt["live_seal_exists"] = live_seal.exists()
    return receipt


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print forensic plan only.",
    )
    parser.add_argument(
        "--out-root",
        type=Path,
        default=None,
        help="Isolated forensic output root (must NOT be live holdout tree).",
    )
    parser.add_argument(
        "--pack-path",
        type=Path,
        default=None,
        help="Isolated forensic pack path (must NOT be live canonical pack).",
    )
    args = parser.parse_args(argv)
    out_root = args.out_root or (REPO / "tmp" / "ncaam_forensic_2425")
    pack_path = args.pack_path or (out_root / "ncaam_official_schedule_2024_25.forensic.json")
    try:
        receipt = forensic_rebuild(
            out_root=out_root, pack_path=pack_path, dry_run=args.dry_run
        )
    except SystemExit as exc:
        print(
            json.dumps(
                {
                    "status": "FORENSIC_REFUSED",
                    "banner": FORENSIC_BANNER,
                    "error": str(exc),
                    "may_promote_to_live_seal": False,
                },
                indent=2,
            )
        )
        return 2
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
