#!/usr/bin/env python3
"""Verify sealed-holdout artifacts against locked R2 refs + seal hash semantics.

Does not call Odds API. Does not unseal or score.

CR7: reads the **active release** (CURRENT) via ``active_release`` — never the
legacy flat ``seal/`` or static model-service DATA_DIR pack when CURRENT exists.
Missing authoritative canonical pack is a **hard failure**, not a note.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parents[2]
WEB_SRC = REPO / "apps" / "web" / "src"
if str(WEB_SRC) not in sys.path:
    sys.path.insert(0, str(WEB_SRC))

from ncaam_lab.holdout_2425.active_release import (  # noqa: E402
    ActiveReleaseError,
    active_artifacts,
    current_is_set,
    load_canonical_pack,
    load_seal_receipt,
    require_artifact,
)
from ncaam_lab.holdout_2425.path_b_promote import sha256_file  # noqa: E402

HOLDOUT = REPO / "data" / "ops" / "lab" / "ncaam" / "holdout_2024_25"
REFS = HOLDOUT / "r2_object_refs" / "r2_object_refs_v1.json"
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


def verify(
    *,
    require_raw: bool = False,
    live_root: Path | None = None,
) -> Dict[str, Any]:
    errors: List[str] = []
    notes: List[str] = []
    root = live_root if live_root is not None else HOLDOUT
    # Refs inventory lives on governance PR B; isolated live_root recoveries
    # verify package bytes only (skip repo-level refs gate).
    check_refs = live_root is None

    if check_refs:
        if not REFS.exists():
            errors.append(f"missing {REFS.relative_to(REPO)}")
            refs: Dict[str, Any] = {}
        else:
            refs = json.loads(REFS.read_text(encoding="utf-8"))
            roles = {o.get("role") for o in refs.get("objects") or []}
            if "espn_schedule_raw_v1" not in roles:
                errors.append("r2 refs missing role espn_schedule_raw_v1")
            for o in refs.get("objects") or []:
                if not o.get("prefix"):
                    errors.append(f"object missing prefix: {o.get('role')}")
    else:
        notes.append("skipped repo r2_object_refs gate (isolated live_root)")

    seal_info: Dict[str, Any] = {
        "current_set": current_is_set(live_root=root),
    }
    arts = active_artifacts(live_root=root)
    seal_info["release_dir"] = str(arts["release_dir"])
    seal_info["seal_receipt_path"] = str(arts["seal_receipt"])
    seal_info["pack_path"] = str(arts["pack_path"])

    # --- Authoritative seal (FAIL if unavailable) ---
    try:
        seal_path = require_artifact("seal_receipt", live_root=root)
        seal = load_seal_receipt(live_root=root)
        file_sha = sha256_file(seal_path)
        payload_claimed = seal.get("seal_payload_sha256") or seal.get(
            "seal_receipt_sha256"
        )
        payload_actual = _payload_sha_from_seal(seal)
        seal_info.update(
            {
                "seal_file_sha256": file_sha,
                "seal_payload_sha256_claimed": payload_claimed,
                "seal_payload_sha256_recomputed": payload_actual,
                "uses_explicit_payload_key": "seal_payload_sha256" in seal,
                "legacy_file_sha256_when_key_was_seal_receipt_sha256": (
                    HISTORICAL_SEAL_FILE_SHA256_LEGACY_KEY
                ),
            }
        )
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
        side_path = arts["seal_sidecar"]
        if side_path.exists():
            side = side_path.read_text(encoding="utf-8").strip().split()[0]
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
    except ActiveReleaseError as exc:
        errors.append(f"authoritative seal unavailable: {exc}")

    # --- Authoritative canonical pack (FAIL if unavailable) ---
    try:
        pack_path = require_artifact("pack_path", live_root=root)
        pack_sha = sha256_file(pack_path)
        seal_info["canonical_pack_sha256"] = pack_sha
        # Touch load path used by governed pack reader.
        pack = load_canonical_pack(live_root=root)
        n_games = len(pack.get("games") or [])
        seal_info["canonical_pack_n_games"] = n_games
        if pack_sha == EXPECTED_CANONICAL_PACK_SHA256:
            notes.append("canonical pack matches locked v1.1 sha256 4016f2ab…")
        else:
            errors.append(
                f"canonical pack sha256={pack_sha} "
                f"(locked={EXPECTED_CANONICAL_PACK_SHA256})"
            )
        if n_games <= 0:
            errors.append("authoritative canonical pack has zero games")
    except ActiveReleaseError as exc:
        errors.append(f"authoritative canonical pack unavailable: {exc}")
        seal_info["canonical_pack_sha256"] = None

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
            actual = sha256_file(fp)
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
        "authority": "active_release_CURRENT",
    }


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-raw",
        action="store_true",
        help="Fail if local raw ESPN archive is absent.",
    )
    parser.add_argument(
        "--live-root",
        type=Path,
        default=None,
        help="Override holdout live_root (tests / isolated recovery).",
    )
    args = parser.parse_args(argv)
    result = verify(require_raw=args.require_raw, live_root=args.live_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
