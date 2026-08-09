#!/usr/bin/env python3
"""NFL Phase 1 data-integrity gate — hard-fail CLI for CI / daily intel.

Usage:
  python scripts/nfl/run_data_integrity_gate.py              # validate active pack
  python scripts/nfl/run_data_integrity_gate.py --archive    # validate + write snapshot archive
  python scripts/nfl/run_data_integrity_gate.py --pack PATH  # validate an explicit pack / fixture

Exit 0 on pass, 1 on fail. No soft warnings for hard-gate checks.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--pack", type=Path, default=None, help="Explicit pack JSON")
    parser.add_argument(
        "--archive",
        action="store_true",
        help="Write immutable snapshot under engine data/snapshots/",
    )
    parser.add_argument(
        "--reference-date",
        type=str,
        default="",
        help="YYYY-MM-DD for stale policy (default: UTC today)",
    )
    parser.add_argument("--max-age-days", type=int, default=7)
    parser.add_argument(
        "--require-archive",
        action="store_true",
        help="Fail if snapshot archive file is missing",
    )
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    from src.services.nfl_season_engine.data_integrity import (
        archive_snapshot,
        ensure_snapshot_metadata,
        packaged_depth_path,
        validate_depth_sot_pack,
        validate_packaged_depth_file,
    )

    ref: date | None = None
    if args.reference_date:
        ref = datetime.strptime(args.reference_date, "%Y-%m-%d").date()

    if args.pack is not None:
        path = args.pack
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload = ensure_snapshot_metadata(payload, pack_path=path)
        if args.archive:
            archive_snapshot(path, payload)
        report = validate_depth_sot_pack(
            payload,
            pack_path=path,
            reference_date=ref,
            max_age_days=args.max_age_days,
        )
    else:
        path = packaged_depth_path(args.season)
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload = ensure_snapshot_metadata(payload, pack_path=path)
        # Persist snapshot_id onto active pack when missing.
        disk = json.loads(path.read_text(encoding="utf-8"))
        if not disk.get("snapshot_id"):
            disk["snapshot_id"] = payload["snapshot_id"]
            disk["identity_scheme"] = payload.get("identity_scheme")
            disk["identity_notes"] = payload.get("identity_notes")
            path.write_text(json.dumps(disk, indent=2) + "\n", encoding="utf-8")
            payload = ensure_snapshot_metadata(disk, pack_path=path)
        if args.archive:
            archive_snapshot(path, payload)
        report = validate_packaged_depth_file(
            args.season,
            reference_date=ref,
            max_age_days=args.max_age_days,
            require_archive=args.require_archive,
        )

    print(json.dumps(report.to_dict(), indent=2))
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report.to_dict(), indent=2) + "\n")

    if report.ok:
        print(
            f"PASS snapshot_id={report.snapshot_id} as_of={report.as_of} "
            f"teams={len(report.teams_touched)}",
            file=sys.stderr,
        )
        return 0
    print(
        f"FAIL snapshot_id={report.snapshot_id} findings={len(report.findings)}",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
