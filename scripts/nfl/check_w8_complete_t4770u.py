#!/usr/bin/env python3
"""RO check: is 2026 W8 14/14 final including MNF CHI@SEA?

Does not seal DATA_READY. Does not emit. Does not mutate the accepted
through-W7 packet. Optional --fetch writes a working parquet only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "nfl"))

from build_efficiency_2026_w1_w8_t4770u import (  # noqa: E402
    APPROVED_PBP_URL,
    RAW_DIR,
    TARGET_THROUGH_WEEK,
    classify_schedule_games,
    complete_games_from_pbp,
    fetch_pbp,
    load_pbp_frame,
    load_schedule,
    sha256_file,
    _iso,
    _now_utc,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true", help="re-fetch PBP to working path (RO check)")
    args = parser.parse_args()

    schedule = load_schedule()
    raw_path = RAW_DIR / "play_by_play_2026.parquet"
    fetched_at = None
    if args.fetch:
        source = fetch_pbp(raw_path)
        fetched_at = source.get("fetched_at_utc")
    elif not raw_path.exists():
        print(json.dumps({"ok": False, "reason": "no local PBP; pass --fetch"}))
        return 2

    frame = load_pbp_frame(raw_path)
    coverage = classify_schedule_games(
        schedule["w1_w8"], complete_games_from_pbp(frame), _now_utc()
    )
    missing_ids = [row["game_id"] for row in coverage["week8_missing"]]
    report = {
        "as_of_utc": _iso(_now_utc()),
        "fetched_at_utc": fetched_at,
        "pbp_sha256": sha256_file(raw_path) if raw_path.exists() else None,
        "pbp_url": APPROVED_PBP_URL,
        "week8_complete_count": coverage["week8_complete_count"],
        "week8_expected_count": coverage["week8_expected_count"],
        "through_w8_complete": coverage["through_w8_complete"],
        "mnf_present": "2026-W08-CHI@SEA" not in missing_ids,
        "week8_missing": coverage["week8_missing"],
        "ready_authorized": False,
        "note": (
            "RO only. DATA_READY requires 14/14 including MNF CHI@SEA, then "
            "re-fetch+archive, T5 through W8, 20-field IF consume, rest_days "
            "spot-check, and a new seal. ≠emit ≠merge #663."
        ),
    }
    print(json.dumps(report, indent=2))
    return 0 if coverage["through_w8_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
