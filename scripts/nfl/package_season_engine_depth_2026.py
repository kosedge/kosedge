#!/usr/bin/env python3
"""Package latest nflverse 2026 skill depth into the season-engine artifact.

Reads ``depth_charts_2026.parquet`` (local path or download URL) and writes
``services/model-service/src/services/nfl_season_engine/data/nfl_depth_chart_2026_w1.json``.

Usage:
  python scripts/nfl/package_season_engine_depth_2026.py \\
      --parquet /tmp/nfl_depth/depth_charts_2026.parquet

  python scripts/nfl/package_season_engine_depth_2026.py --download
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = (
    REPO_ROOT
    / "services/model-service/src/services/nfl_season_engine/data"
    / "nfl_depth_chart_2026_w1.json"
)
DEFAULT_URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/"
    "depth_charts/depth_charts_2026.parquet"
)
SKILL = ("QB", "RB", "WR", "TE")
TEAM_MAP = {"LAR": "LA"}


def _load_frame(parquet_path: Path):
    try:
        import polars as pl
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("polars is required to package depth charts") from exc
    return pl.read_parquet(str(parquet_path))


def package(*, parquet_path: Path, out_path: Path, upstream_last_updated: str = "") -> dict:
    import polars as pl

    df = _load_frame(parquet_path)
    latest_dt = df.select(pl.col("dt").cast(pl.Utf8).max()).item()
    latest = df.filter(pl.col("dt").cast(pl.Utf8) == latest_dt)
    skill = latest.filter(pl.col("pos_abb").is_in(list(SKILL)))

    rows_out = []
    seen: set[tuple[str, str, int]] = set()
    for row in skill.sort(["team", "pos_abb", "pos_rank"]).iter_rows(named=True):
        team = TEAM_MAP.get(str(row["team"]).upper(), str(row["team"]).upper())
        pos = str(row["pos_abb"])
        rank = int(row["pos_rank"] or 0)
        name = str(row["player_name"] or "").strip()
        if rank < 1 or rank > 3 or not name:
            continue
        key = (team, pos, rank)
        if key in seen:
            continue
        seen.add(key)
        player_id = str(row.get("gsis_id") or row.get("espn_id") or "").strip()
        rows_out.append(
            {
                "team": team,
                "position": pos,
                "depth_order": rank,
                "player_id": player_id or f"{team}-{pos}-{rank}",
                "player_name": name,
                "depth_slot": {1: "starter", 2: "backup", 3: "rotation"}.get(rank, "depth"),
                "role_confidence": 0.85 if rank == 1 else (0.65 if rank == 2 else 0.5),
            }
        )

    teams = {r["team"] for r in rows_out}
    full = 0
    for team in teams:
        has = {(r["position"], r["depth_order"]) for r in rows_out if r["team"] == team}
        if all((p, 1) in has for p in SKILL):
            full += 1

    payload = {
        "season": 2026,
        "week": 1,
        "source": "packaged_nflverse_depth_2026",
        "upstream": "nflverse/nflverse-data depth_charts release",
        "upstream_url": DEFAULT_URL,
        "as_of": str(latest_dt)[:10],
        "as_of_timestamp": latest_dt,
        "upstream_last_updated": upstream_last_updated or "",
        "positions": list(SKILL),
        "max_depth_order": 3,
        "team_count": len(teams),
        "row_count": len(rows_out),
        "full_skill_starter_teams": full,
        "notes": [
            "Skill-position slice (QB/RB/WR/TE) from latest nflverse depth-chart snapshot.",
            "Preseason/camp depth — roles can shift; rookies and free-agent landings may be incomplete or volatile.",
            "Used when nfl_dp_depth_chart_weekly / official tables are empty.",
        ],
        "rows": rows_out,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    pos_counts = Counter(r["position"] for r in rows_out)
    print(
        json.dumps(
            {
                "out": str(out_path),
                "teams": len(teams),
                "rows": len(rows_out),
                "full_skill_starter_teams": full,
                "as_of": payload["as_of"],
                "pos_counts": dict(pos_counts),
            },
            indent=2,
        )
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parquet", type=Path, help="Local depth_charts_2026.parquet")
    parser.add_argument(
        "--download",
        action="store_true",
        help=f"Download from {DEFAULT_URL}",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--timestamp-json",
        type=Path,
        help="Optional nflverse timestamp.json for upstream_last_updated",
    )
    args = parser.parse_args(argv)

    parquet = args.parquet
    if args.download:
        parquet = Path("/tmp/nfl_depth_charts_2026.parquet")
        parquet.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading {DEFAULT_URL} -> {parquet}", file=sys.stderr)
        urllib.request.urlretrieve(DEFAULT_URL, parquet)
    if parquet is None or not parquet.is_file():
        raise SystemExit("Provide --parquet PATH or --download")

    upstream_last_updated = ""
    if args.timestamp_json and args.timestamp_json.is_file():
        try:
            upstream_last_updated = str(
                json.loads(args.timestamp_json.read_text(encoding="utf-8")).get(
                    "last_updated"
                )
                or ""
            )
        except json.JSONDecodeError:
            upstream_last_updated = ""

    package(
        parquet_path=parquet,
        out_path=args.out,
        upstream_last_updated=upstream_last_updated,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
