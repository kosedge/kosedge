#!/usr/bin/env python3
"""Phase 4 freeze — code/config/manifest/rows. Existence-only is insufficient.

P1 lesson from #685: PROTOCOL_FREEZE that only checks .exists() is not a
row bind. This freeze hashes IF mus rows and Q2s rows and refuses if those
files are absent or their sha256 drifts.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PACKET = Path(__file__).resolve().parents[1]
PHASE4 = Path(__file__).resolve().parent
OUT = PHASE4 / "artifacts" / "PROTOCOL_FREEZE.json"
LOOK = PHASE4 / "artifacts" / "LOOK_CONSUMED.json"
MATRIX_SHA256 = "b56be1462e591ac5e04cfaf860938118e013664a2c661e156afdf5c5f41bc216"

FREEZE_PATHS = [
    "phase4/ASSUMPTIONS.md",
    "phase4/AUTHORITY_PHASE4.md",
    "phase4/score_if_w7w17.py",
    "phase4/emit_q2s_w7w17.py",
    "phase4/freeze_protocol.py",
    "phase4/run_phase4.py",
    "phase4/q2s/blend.py",
    "phase4/q2s/coverage.py",
    "phase4/q2s/__init__.py",
    "phase4/q2pb/strength.py",
    "phase4/q2pb/metrics.py",
    "phase4/q2pb/data.py",
    "phase4/q2pb/constants.py",
    "phase4/q2pb/__init__.py",
    "phase4/frozen/FROZEN_CONFIG_Q2PB_t5009u.json",
    "phase4/frozen/FROZEN_CONFIG_Q2PB_t5009u.md",
    "gate1/IDENTITY_MANIFEST.json",
    "gate1/SELECTION_HASH_SEAL.json",
    "gate2/RECON_MATRIX_W7W17.csv",
    "pins/games_4fe1cdd7.csv",
    "pins/outcomes_2013_2022_score_only.csv",
    "phase4/artifacts/IF_MUS_W7W17.json",
    "phase4/artifacts/q2s_rows_w7w17.json",
]

ROW_PATHS = {
    "if_mus": "phase4/artifacts/IF_MUS_W7W17.json",
    "q2s_rows": "phase4/artifacts/q2s_rows_w7w17.json",
}


class FreezeRefuse(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_files() -> dict[str, str]:
    files: dict[str, str] = {}
    for rel in FREEZE_PATHS:
        path = PACKET / rel
        if not path.exists():
            raise FreezeRefuse(f"missing freeze path {rel}")
        files[rel] = sha256_file(path)
    if files["gate2/RECON_MATRIX_W7W17.csv"] != MATRIX_SHA256:
        raise FreezeRefuse(
            "matrix sha drifted from b56be146 — freeze refused (do not rescore over a moved pin)"
        )
    return files


def bind_rows(files: dict[str, str]) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for name, rel in ROW_PATHS.items():
        if rel not in files:
            raise FreezeRefuse(f"row path {rel} not in files map — existence-only freeze refused")
        path = PACKET / rel
        payload = json.loads(path.read_text())
        if not isinstance(payload, dict) or "rows" not in payload:
            raise FreezeRefuse(f"{rel} missing rows[] — row identity required")
        if not payload["rows"]:
            raise FreezeRefuse(f"{rel} rows[] empty")
        digest = files[rel]
        rows[name] = {
            "path": rel,
            "sha256": digest,
            "sha8": digest[:8],
            "n_rows": len(payload["rows"]),
        }
    return rows


def verify_freeze(freeze_path: Path | None = None) -> dict:
    """Re-hash every freeze entry including rows. Refuse on mismatch/absence."""
    path = freeze_path or OUT
    if not path.exists():
        raise FreezeRefuse("PROTOCOL_FREEZE missing — freeze before any look")
    freeze = json.loads(path.read_text())
    files = freeze.get("files")
    rows = freeze.get("rows")
    if not isinstance(files, dict) or not files:
        raise FreezeRefuse("PROTOCOL_FREEZE has no files map")
    if not isinstance(rows, dict) or set(rows) != set(ROW_PATHS):
        raise FreezeRefuse("PROTOCOL_FREEZE missing row-identity bind (P1 / #685)")
    live = hash_files()
    mismatches = []
    missing = []
    for rel, expected in files.items():
        if rel not in live:
            missing.append(rel)
            continue
        if live[rel] != expected:
            mismatches.append({"path": rel, "expected": expected, "actual": live[rel]})
    for name, meta in rows.items():
        rel = str(meta.get("path") or "")
        expected = str(meta.get("sha256") or "")
        if not rel or rel not in live:
            raise FreezeRefuse(f"row bind {name} path missing")
        if live[rel] != expected:
            raise FreezeRefuse(f"row bind {name} sha {live[rel]} != freeze {expected}")
    if LOOK.exists():
        raise FreezeRefuse("LOOK_CONSUMED exists — look is not authorized")
    if missing or mismatches:
        raise FreezeRefuse(
            f"PROTOCOL_FREEZE re-hash mismatch missing={missing} mismatches={mismatches}"
        )
    return freeze


def write_freeze() -> dict:
    if LOOK.exists():
        raise FreezeRefuse("REFUSE: look already consumed; freeze is closed")
    files = hash_files()
    rows = bind_rows(files)
    payload = {
        "ticket": "t5044u",
        "phase": 4,
        "label": "RETRO_FIT / DEV_RESEARCH",
        "cert": 0,
        "nfl": "NO-GO",
        "owner_clear_tip": "12763c08",
        "cos_accept_tip": "adbcf11d",
        "cite": [
            "12763c08",
            "adbcf11d",
            "7cefecef",
            "1114f24e",
            "6ca03716",
            "84eacd96",
            "d7e0a6bc",
        ],
        "frozen_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "matrix_sha256": MATRIX_SHA256,
        "matrix_sha8": "b56be146",
        "files": files,
        "rows": rows,
        "look_run": False,
        "look_authorized": False,
        "existence_only": False,
        "note": (
            "Code/config/source/manifest/IF rows/Q2s rows frozen. "
            "Row identity is hashed, not existence-only (P1 / #685). "
            "Do NOT look until Alex timestamped PASS_RO_PRE_LOOK bound to these hashes."
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        prev = json.loads(OUT.read_text())
        if prev.get("files") != files or prev.get("rows") != rows:
            raise FreezeRefuse("PROTOCOL_FREEZE already exists with different hashes")
        verify_freeze(OUT)
        print(f"PROTOCOL_FREEZE already sealed ({OUT})")
        return prev
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    digest = sha256_file(OUT)
    (OUT.with_suffix(".json.sha256")).write_text(f"{digest}  {OUT.name}\n")
    verify_freeze(OUT)
    print(f"froze {len(files)} paths + {len(rows)} row binds -> {OUT}")
    return payload


def main() -> int:
    try:
        payload = write_freeze()
    except FreezeRefuse as exc:
        print(f"FREEZE_REFUSE: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "ok": True,
                "path": "phase4/artifacts/PROTOCOL_FREEZE.json",
                "n_files": len(payload["files"]),
                "rows": {k: v["sha8"] for k, v in payload["rows"].items()},
                "look_run": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
