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
    args = parser.parse_args()
    from .ingest import (
        ingest_nflverse_snapshot,
        materialize_player_projection_features,
        materialize_matchup_features_from_usage,
        materialize_usage_features_from_pbp,
        normalize_pbp_from_raw,
    )

    seasons = _parse_seasons(args.seasons)
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
    else:
        result = ingest_nflverse_snapshot(seasons=seasons, include_pbp=not args.no_pbp)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
