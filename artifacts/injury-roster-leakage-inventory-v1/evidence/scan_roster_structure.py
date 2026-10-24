#!/usr/bin/env python3
"""Re-derive one-row-per-player and week-stamp counts from roster_YYYY.csv.

Reads only paths passed on the command line. Refuses 2024/2025/2026
in the filename or in the season column.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

FORBIDDEN = {2024, 2025, 2026}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        sys.stderr.write("usage: scan_roster_structure.py roster_YYYY.csv [...]\n")
        return 2
    years = []
    for raw in argv[1:]:
        path = Path(raw)
        name = path.name
        for year in FORBIDDEN:
            if str(year) in name:
                sys.stderr.write(f"refuse holdout filename {name}\n")
                return 2
        rows = []
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                season = int(row.get("season") or 0)
                if season in FORBIDDEN:
                    sys.stderr.write(f"refuse holdout season {season} in {name}\n")
                    return 2
                pid = (row.get("gsis_id") or "").strip()
                if not pid:
                    continue
                try:
                    week = int(row.get("week") or 0)
                except ValueError:
                    continue
                rows.append(
                    (
                        season,
                        (row.get("team") or "").upper(),
                        pid,
                        week,
                        (row.get("game_type") or "").upper(),
                    )
                )
        keys = {(t, p) for _, t, p, _, _ in rows}
        w1 = sum(1 for *_, week, gt in rows if week == 1 and gt == "REG")
        years.append(
            {
                "path": str(path),
                "sha256": sha256(path),
                "n_rows": len(rows),
                "n_unique_team_pid": len(keys),
                "one_row_per_team_pid": len(keys) == len(rows),
                "n_week1_reg": w1,
                "n_not_week1_reg": len(rows) - w1,
                "week_game_type_top": [
                    {"week": w, "game_type": g, "n": c}
                    for (w, g), c in Counter((r[3], r[4]) for r in rows).most_common(6)
                ],
            }
        )
    json.dump({"years": years}, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
