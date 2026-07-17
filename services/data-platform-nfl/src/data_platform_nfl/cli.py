from __future__ import annotations

import argparse
import json
from typing import List


def _parse_seasons(raw: str) -> List[int]:
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return [int(p) for p in parts]


def main() -> None:
    parser = argparse.ArgumentParser(description="NFL data platform ingestion CLI")
    parser.add_argument(
        "--seasons",
        default="2023,2024,2025,2026",
        help="Comma-separated seasons to ingest, e.g. 2023,2024,2025",
    )
    parser.add_argument(
        "--no-pbp",
        action="store_true",
        help="Skip play-by-play raw ingestion",
    )
    parser.add_argument(
        "--normalize-pbp-from-raw",
        action="store_true",
        help="Normalize existing raw pbp rows into nfl_dp_play_by_play",
    )
    parser.add_argument(
        "--replace-normalized",
        action="store_true",
        help="Delete existing normalized rows for target seasons before normalization",
    )
    parser.add_argument(
        "--materialize-usage-features",
        action="store_true",
        help="Build weekly player/team usage features from nfl_dp_play_by_play",
    )
    parser.add_argument(
        "--replace-usage-features",
        action="store_true",
        help="Delete existing usage-feature rows for target seasons before rebuild",
    )
    parser.add_argument(
        "--materialize-matchup-features",
        action="store_true",
        help="Build rolling team form and matchup feature tables",
    )
    parser.add_argument(
        "--replace-matchup-features",
        action="store_true",
        help="Delete existing matchup-feature rows for target seasons before rebuild",
    )
    parser.add_argument(
        "--materialize-player-projection-features",
        action="store_true",
        help="Build weekly player projection features from usage/situational tables",
    )
    parser.add_argument(
        "--materialize-standings-weekly",
        action="store_true",
        help="Build derived weekly standings from schedules/results",
    )
    parser.add_argument(
        "--replace-standings-weekly",
        action="store_true",
        help="Delete existing standings rows for target seasons before rebuild",
    )
    parser.add_argument(
        "--materialize-depth-chart-weekly",
        action="store_true",
        help="Build inferred weekly depth charts from roster/usage/injury data",
    )
    parser.add_argument(
        "--replace-depth-chart-weekly",
        action="store_true",
        help="Delete existing depth chart rows for target seasons before rebuild",
    )
    parser.add_argument(
        "--replace-player-projection-features",
        action="store_true",
        help="Delete existing player projection feature rows for target seasons before rebuild",
    )
    parser.add_argument(
        "--week",
        type=int,
        default=None,
        help="Optional week filter for feature materializations",
    )
    parser.add_argument(
        "--run-launch-hardening",
        action="store_true",
        help="Execute full NFL data ownership hardening cycle and backup manifest",
    )
    parser.add_argument(
        "--backup-owned-data",
        action="store_true",
        help="Generate owned-data backup manifest (and optional row exports)",
    )
    parser.add_argument(
        "--backup-export-dir",
        default=None,
        help="Directory for owned-data exports (defaults to data/ops)",
    )
    parser.add_argument(
        "--backup-include-row-exports",
        action="store_true",
        help="Write table row NDJSON exports in addition to DB-backed manifest",
    )
    args = parser.parse_args()
    from .ops import export_data_ownership_snapshot, run_launch_hardening_cycle

    seasons = _parse_seasons(args.seasons)
    if args.run_launch_hardening:
        result = run_launch_hardening_cycle(
            seasons=seasons,
            week=args.week,
            include_pbp=not args.no_pbp,
            include_row_exports=args.backup_include_row_exports,
            export_dir=args.backup_export_dir,
        )
    elif args.backup_owned_data:
        result = export_data_ownership_snapshot(
            seasons=seasons,
            week=args.week,
            export_dir=args.backup_export_dir,
            include_row_exports=args.backup_include_row_exports,
        )
    else:
        from .ingest import (
            ingest_nflverse_snapshot,
            materialize_depth_chart_weekly,
            materialize_player_projection_features,
            materialize_matchup_features_from_usage,
            materialize_standings_weekly,
            materialize_usage_features_from_pbp,
            normalize_pbp_from_raw,
        )

        if args.normalize_pbp_from_raw:
            result = normalize_pbp_from_raw(
                seasons=seasons,
                replace_existing=args.replace_normalized,
            )
        elif args.materialize_usage_features:
            result = materialize_usage_features_from_pbp(
                seasons=seasons,
                replace_existing=args.replace_usage_features,
            )
        elif args.materialize_matchup_features:
            result = materialize_matchup_features_from_usage(
                seasons=seasons,
                replace_existing=args.replace_matchup_features,
            )
        elif args.materialize_player_projection_features:
            result = materialize_player_projection_features(
                seasons=seasons,
                week=args.week,
                replace_existing=args.replace_player_projection_features,
            )
        elif args.materialize_standings_weekly:
            result = materialize_standings_weekly(
                seasons=seasons,
                week=args.week,
                replace_existing=args.replace_standings_weekly,
            )
        elif args.materialize_depth_chart_weekly:
            result = materialize_depth_chart_weekly(
                seasons=seasons,
                week=args.week,
                replace_existing=args.replace_depth_chart_weekly,
            )
        else:
            result = ingest_nflverse_snapshot(seasons=seasons, include_pbp=not args.no_pbp)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
