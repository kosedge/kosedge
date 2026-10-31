#!/usr/bin/env python3
"""Extract 2013–2022 public finals ONLY from the gated hist index.

Writes six columns: season, week, home, away, home_score, away_score.
Drops trailing_*/packaged_*/EPA/error columns and every 2023–2026 row.
This is not scored reuse of index 1ee90fac (gate 83646d78) — Alex RO confirm.
Label: DEV_RESEARCH. CERT=0.
"""

from __future__ import annotations

import csv
import hashlib
import sys
from pathlib import Path

KEEP = ("season", "week", "home", "away", "home_score", "away_score")
SEASONS = set(range(2013, 2023))  # 2013–2022 inclusive; no 2023/24/25/26


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "/workspace/data/ops/nfl-reopening-packet-20260916/historical-oos/historical_oos_games.csv"
    )
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(
        "/workspace/research/q2_phase_b_t5009u/data/outcomes_2013_2022_score_only.csv"
    )
    digest = sha256(src)
    if not digest.startswith("1ee90fac"):
        print(f"STOP: source hash {digest[:8]} != 1ee90fac", file=sys.stderr)
        return 2
    dst.parent.mkdir(parents=True, exist_ok=True)
    n_in = n_out = n_skip_season = n_skip_score = 0
    with src.open(newline="") as fin, dst.open("w", newline="") as fout:
        reader = csv.DictReader(fin)
        writer = csv.DictWriter(fout, fieldnames=list(KEEP), extrasaction="ignore")
        writer.writeheader()
        for row in reader:
            n_in += 1
            season = int(row["season"])
            if season not in SEASONS:
                n_skip_season += 1
                continue
            if row.get("home_score") in (None, "") or row.get("away_score") in (None, ""):
                n_skip_score += 1
                continue
            writer.writerow({k: row[k] for k in KEEP})
            n_out += 1
    out_hash = sha256(dst)
    print(f"source_sha256={digest}")
    print(f"dest_sha256={out_hash}")
    print(f"n_in={n_in} n_out={n_out} skip_season={n_skip_season} skip_score={n_skip_score}")
    print(f"wrote {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
