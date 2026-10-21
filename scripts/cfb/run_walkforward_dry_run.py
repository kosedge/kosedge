#!/usr/bin/env python3
"""Documented CFB walk-forward dry-run (no KEI, no 100k).

Prints leakage rules, then calls the existing Week 0–4 harness on a ``--limit``
slice when warehouse parquet is present. If HD / repo parquet is missing,
prints the rules and skips (or uses --fixtures). Does not write KEI files.

Usage:
  python scripts/cfb/run_walkforward_dry_run.py
  python scripts/cfb/run_walkforward_dry_run.py --limit 8
  python scripts/cfb/run_walkforward_dry_run.py --fixtures
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.cfb_warehouse.leakage import documentation  # noqa: E402
from src.services.cfb_warehouse.paths import clean_dir, hd_mounted  # noqa: E402
from src.services.cfb_warehouse.walkforward import (  # noqa: E402
    build_program_priors,
    summarize,
    walkforward_games,
)

KEI_FORBIDDEN = (
    ROOT / "apps" / "web" / "data" / "kei_lines_cfb.json",
    ROOT / "data" / "kei_lines_cfb.json",
)


def _fixture_games() -> list[dict[str, Any]]:
    return [
        {
            "game_id": "dry-uga-clem-2024",
            "season": 2024,
            "week": 1,
            "home_team_id": "UGA",
            "away_team_id": "CLEM",
            "kickoff": "2024-08-31T16:00:00+00:00",
            "game_date": "2024-08-31",
            "neutral": True,
            "home_score": 34,
            "away_score": 3,
            "close_spread_home": -13.5,
            "open_spread_home": -13.5,
            "era_tag": "2022-present",
        }
    ]


def _fixture_priors() -> dict[tuple[int, str], dict[str, Any]]:
    return {
        (2024, "UGA"): {"points": 12.0, "seasons": [2023]},
        (2024, "CLEM"): {"points": 4.0, "seasons": [2023]},
    }


def _read_parquet(path: Path) -> list[dict[str, Any]]:
    import pandas as pd

    return pd.read_parquet(path).to_dict(orient="records")


def _parse_seasons(raw: str) -> list[int]:
    raw = raw.strip()
    if not raw:
        return []
    if "-" in raw and "," not in raw:
        a, b = raw.split("-", 1)
        return list(range(int(a), int(b) + 1))
    return [int(s.strip()) for s in raw.split(",") if s.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--seasons", default="2020-2025")
    parser.add_argument("--repo-fallback", action="store_true")
    parser.add_argument(
        "--fixtures",
        action="store_true",
        help="Use in-repo toy games (no HD). Default when parquet is missing.",
    )
    parser.add_argument(
        "--write-research-summary",
        type=Path,
        default=None,
        help="Optional path for a research JSON summary. Never writes kei_lines_cfb.json.",
    )
    args = parser.parse_args(argv)

    leakage = documentation()
    banner = {
        "dry_run": True,
        "kei": False,
        "n_sims_note": "not a 100k sim; this is a research-fair vs close slice",
        "leakage": leakage,
        "forbidden": leakage.get("forbidden"),
        "do_not": [
            "publish KEI from this prior",
            "write kei_lines_cfb.json",
            "copy Project Game onto Edge Board as edge",
            "UPDATE an existing (model_version, as_of, game_id) snapshot",
        ],
    }
    print(json.dumps(banner, indent=2))

    prefer_hd = not args.repo_fallback
    clean = clean_dir(prefer_hd=prefer_hd)
    games_path = clean / "games.parquet"
    closes_path = clean / "closing_lines.parquet"
    week_path = clean / "efficiency" / "team_week_efficiency.parquet"
    season_path = clean / "efficiency" / "team_season_efficiency.parquet"
    missing = [p for p in (games_path, closes_path, week_path, season_path) if not p.is_file()]

    used_fixtures = bool(args.fixtures or missing)
    if missing and not args.fixtures:
        print(
            json.dumps(
                {
                    "status": "skipped_missing_parquet",
                    "hd_mounted": hd_mounted(),
                    "clean_dir": str(clean),
                    "missing": [str(p) for p in missing],
                    "note": "HD not required. Re-run with --fixtures or mount warehouse parquet.",
                },
                indent=2,
            )
        )
        if not args.fixtures:
            # Still run fixtures so the dry-run is documented end-to-end.
            used_fixtures = True

    if used_fixtures:
        graded = walkforward_games(
            _fixture_games(),
            priors=_fixture_priors(),
            eff_idx={},
        )
        source = "fixtures"
    else:
        seasons = _parse_seasons(args.seasons) or list(range(2020, 2026))
        games = [g for g in _read_parquet(games_path) if int(g.get("season") or 0) in set(seasons)]
        closes = _read_parquet(closes_path)
        by_id = {str(c.get("game_id")): c for c in closes}
        joined: list[dict[str, Any]] = []
        for g in games:
            row = dict(g)
            c = by_id.get(str(g.get("game_id")))
            if c:
                for k in (
                    "close_spread_home",
                    "open_spread_home",
                    "close_total",
                    "open_total",
                    "book",
                    "source",
                    "line_fidelity",
                    "close_captured_at",
                    "available_at",
                ):
                    if c.get(k) is not None:
                        row[k] = c.get(k)
            joined.append(row)
        if args.limit and args.limit > 0:
            joined = joined[: args.limit]
        finals = _read_parquet(season_path)
        priors = build_program_priors(finals, seasons)
        from src.services.cfb_warehouse.walkforward import index_week_efficiency

        eff_idx = index_week_efficiency(_read_parquet(week_path))
        graded = walkforward_games(joined, priors=priors, eff_idx=eff_idx)
        source = "warehouse_parquet"

    summary = summarize(graded)
    result = {
        "status": "ok",
        "source": source,
        "n_graded": len(graded),
        "kei_written": False,
        "summary": summary,
    }
    print(json.dumps(result, indent=2, default=str))

    if args.write_research_summary:
        out = Path(args.write_research_summary)
        if out.name.startswith("kei_lines"):
            print("refusing to write a KEI filename", file=sys.stderr)
            return 2
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2, default=str) + "\n")

    leaked = [p for p in KEI_FORBIDDEN if p.exists()]
    if leaked:
        print(f"unexpected KEI file present: {leaked}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
