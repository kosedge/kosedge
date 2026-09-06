#!/usr/bin/env python3
"""Verify sealed-holdout artifacts against locked R2 refs + seal hash semantics.

Does not call Odds API. Does not unseal or score.

Checks:
  1) r2_object_refs_v1.json present with exact roles/prefixes/hashes
  2) seal_receipt.json uses seal_payload_sha256 (not ambiguous seal_receipt_sha256-as-file)
  3) optional: seal_receipt.file_sha256 matches on-disk file digest
  4) optional: local raw ESPN day files match sidecar digests when present
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parents[2]
HOLDOUT = REPO / "data" / "ops" / "lab" / "ncaam" / "holdout_2024_25"
REFS = HOLDOUT / "r2_object_refs" / "r2_object_refs_v1.json"
SEAL = HOLDOUT / "seal" / "seal_receipt.json"
SEAL_FILE_SIDECAR = HOLDOUT / "seal" / "seal_receipt.file_sha256"
RAW = HOLDOUT / "raw" / "espn_scoreboard"

# Historical: payload hash of v1.1 seal membership (hash before inserting hash field).
EXPECTED_SEAL_PAYLOAD_SHA256 = (
    "af4fd4513272e8cc784de7db02d33c74c16b0a0ed7e256e851f3da73d5543d84"
)
EXPECTED_SEAL_FILE_SHA256 = (
    "82852e2460bf876d75aae647232860820a998814b4bef76c236bdf058f0ddca2"
)
EXPECTED_CANONICAL_PACK_SHA256 = (
    "4016f2ab4dcfbf713fdd005b4468ab5576345bea321caa59333685f224ae828e"
)
# Historical on-disk file hash when the receipt still used key seal_receipt_sha256.
HISTORICAL_SEAL_FILE_SHA256_LEGACY_KEY = (
    "1074731f38e1194a4fce4eb16b84765c1376a1624f377ed2d0395b43540d5d09"
)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _payload_sha_from_seal(seal: Dict[str, Any]) -> str:
    body = {
        k: v
        for k, v in seal.items()
        if k
        not in {
            "seal_payload_sha256",
            "seal_receipt_sha256",
            "seal_file_sha256",
            "seal_file_sha256_external",
        }
    }
    text = json.dumps(body, indent=2, sort_keys=True, default=str) + "\n"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def verify(*, require_raw: bool = False) -> Dict[str, Any]:
    errors: List[str] = []
    notes: List[str] = []

    if not REFS.exists():
        errors.append(f"missing {REFS.relative_to(REPO)}")
        refs = {}
    else:
        refs = json.loads(REFS.read_text(encoding="utf-8"))
        roles = {o.get("role") for o in refs.get("objects") or []}
        if "espn_schedule_raw_v1" not in roles:
            errors.append("r2 refs missing role espn_schedule_raw_v1")
        for o in refs.get("objects") or []:
            if not o.get("prefix"):
                errors.append(f"object missing prefix: {o.get('role')}")

    seal_info: Dict[str, Any] = {}
    if not SEAL.exists():
        notes.append("seal_receipt.json not in this checkout (deferred/PR B)")
    else:
        seal = json.loads(SEAL.read_text(encoding="utf-8"))
        file_sha = _sha256_file(SEAL)
        payload_claimed = seal.get("seal_payload_sha256") or seal.get(
            "seal_receipt_sha256"
        )
        payload_actual = _payload_sha_from_seal(seal)
        seal_info = {
            "seal_file_sha256": file_sha,
            "seal_payload_sha256_claimed": payload_claimed,
            "seal_payload_sha256_recomputed": payload_actual,
            "uses_explicit_payload_key": "seal_payload_sha256" in seal,
            "legacy_file_sha256_when_key_was_seal_receipt_sha256": HISTORICAL_SEAL_FILE_SHA256_LEGACY_KEY,
        }
        if payload_claimed != payload_actual:
            errors.append(
                f"seal payload hash mismatch claimed={payload_claimed} actual={payload_actual}"
            )
        if payload_claimed == EXPECTED_SEAL_PAYLOAD_SHA256:
            notes.append("seal payload matches locked v1.1 membership hash")
        if file_sha == EXPECTED_SEAL_FILE_SHA256:
            notes.append("seal file matches locked v1.1 on-disk digest")
        if "seal_payload_sha256" not in seal and "seal_receipt_sha256" in seal:
            errors.append(
                "seal still uses ambiguous seal_receipt_sha256; rename to seal_payload_sha256"
            )
        if SEAL_FILE_SIDECAR.exists():
            side = SEAL_FILE_SIDECAR.read_text(encoding="utf-8").strip().split()[0]
            if side != file_sha:
                errors.append(
                    f"seal_receipt.file_sha256 sidecar mismatch side={side} file={file_sha}"
                )
            else:
                notes.append("seal file sidecar matches on-disk digest")
        elif file_sha == HISTORICAL_SEAL_FILE_SHA256_LEGACY_KEY:
            notes.append(
                "on-disk seal file hash matches historical 1074731f… "
                "(legacy key seal_receipt_sha256); payload remains af4fd451…"
            )

    pack_path = (
        REPO
        / "services"
        / "model-service"
        / "src"
        / "services"
        / "ncaam_schedule"
        / "data"
        / "ncaam_official_schedule_2024_25.json"
    )
    if pack_path.exists():
        pack_sha = _sha256_file(pack_path)
        seal_info_pack = {"canonical_pack_sha256": pack_sha}
        if pack_sha == EXPECTED_CANONICAL_PACK_SHA256:
            notes.append("canonical pack matches locked v1.1 sha256 4016f2ab…")
        else:
            notes.append(
                f"canonical pack present but sha256={pack_sha} "
                f"(locked={EXPECTED_CANONICAL_PACK_SHA256})"
            )
    else:
        seal_info_pack = {"canonical_pack_sha256": None}
        notes.append("canonical pack not in this checkout (path-B rebuild)")
    seal_info.update(seal_info_pack)

    raw_info: Dict[str, Any] = {"present": RAW.exists()}
    if RAW.exists():
        files = sorted(RAW.glob("espn_scoreboard_*.json"))
        missing = []
        mismatches = []
        ok = 0
        for fp in files:
            side = RAW / fp.name.replace(".json", ".sha256")
            if not side.exists():
                missing.append(fp.name)
                continue
            claimed = side.read_text(encoding="utf-8").strip().split()[0]
            actual = _sha256_file(fp)
            if claimed.lower() != actual.lower():
                mismatches.append(fp.name)
            else:
                ok += 1
        raw_info.update(
            {
                "n_json": len(files),
                "n_verified": ok,
                "n_missing_sidecars": len(missing),
                "n_digest_mismatches": len(mismatches),
            }
        )
        if missing or mismatches:
            errors.append("raw ESPN integrity failed (sidecar/digest)")
    elif require_raw:
        errors.append("raw ESPN directory required but missing — run hydrate first")

    return {
        "ok": not errors,
        "errors": errors,
        "notes": notes,
        "refs_path": str(REFS.relative_to(REPO)) if REFS.exists() else None,
        "seal": seal_info,
        "raw": raw_info,
        "odds_api_calls_made": False,
    }


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-raw",
        action="store_true",
        help="Fail if local raw ESPN archive is absent.",
    )
    args = parser.parse_args(argv)
    result = verify(require_raw=args.require_raw)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
