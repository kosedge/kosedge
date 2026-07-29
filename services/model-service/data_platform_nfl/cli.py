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
        "--materialize-kav",
        action="store_true",
        help="Build owned KAV opponent-adjusted efficiency tables from PBP",
    )
    parser.add_argument(
        "--replace-kav",
        action="store_true",
        help="Delete existing KAV rows for target seasons before rebuild",
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
        "--run-preseason-bootstrap",
        action="store_true",
        help=(
            "Seed team/player priors for a future season with no real games "
            "yet: full prior-season averages (not a single-week snapshot), "
            "market-anchored team strength, and real historical draft-tier "
            "baselines for rookies. Uses the LAST season in --seasons as the "
            "target season and that minus 1 as the prior season unless "
            "--prior-season is set. Safe to re-run any time."
        ),
    )
    parser.add_argument(
        "--prior-season",
        type=int,
        default=None,
        help="Override the prior season used by --run-preseason-bootstrap",
    )
    parser.add_argument(
        "--no-market-signal",
        action="store_true",
        help="Skip the Super Bowl futures market anchor in --run-preseason-bootstrap",
    )
    parser.add_argument(
        "--refresh-rolling-player-usage",
        action="store_true",
        help=(
            "Blend real in-season usage (through --through-week) into "
            "remaining future weeks still tagged with a synthetic "
            "preseason/rookie/rolling source, so projections keep tracking "
            "a player's actual role instead of staying frozen at the "
            "preseason prior. Uses the LAST season in --seasons."
        ),
    )
    parser.add_argument(
        "--through-week",
        type=int,
        default=None,
        help="Last real week to treat as 'known' for --refresh-rolling-player-usage",
    )
    parser.add_argument(
        "--run-inseason-weekly-update",
        action="store_true",
        help=(
            "Data-platform portion of the in-season weekly update: optional "
            "launch-hardening ingest for --week, rolling usage refresh "
            "(--through-week or --week), and rematerialize player projection "
            "features. Prefer scripts/nfl/run-weekly-inseason-update.sh for "
            "the full DP + model-service loop. Uses the LAST season in --seasons."
        ),
    )
    parser.add_argument(
        "--skip-ingest",
        action="store_true",
        help="With --run-inseason-weekly-update, skip --run-launch-hardening",
    )
    parser.add_argument(
        "--target-week-features-only",
        action="store_true",
        help=(
            "With --run-inseason-weekly-update, rematerialize projection "
            "features only for --week instead of the full remaining season"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="With --run-inseason-weekly-update, print the DP step plan without writing",
    )
    parser.add_argument(
        "--materialize-tendency-profiles",
        action="store_true",
        help=(
            "Build real situational/tendency analytics (team down-distance/"
            "score-state/field-position tendencies, pass/run direction "
            "tendency, QB situational splits) from normalized PBP. Requires "
            "034_nfl_pbp_tendency_columns.sql to be applied and "
            "--normalize-pbp-from-raw --replace-normalized to have been run "
            "at least once after that migration so shotgun/xpass/cp/etc are "
            "backfilled."
        ),
    )
    parser.add_argument(
        "--materialize-kicking-defense-history",
        action="store_true",
        help=(
            "Normalize real per-kicker FG-by-distance-bucket/PAT stats and "
            "real per-team sacks/interceptions/fumble-recoveries/defensive+"
            "special-teams-touchdowns/safeties from ALREADY-INGESTED "
            "nfl_dp_player_game_stats/nfl_dp_raw_objects payloads into "
            "nfl_dp_kicker_weekly / nfl_dp_team_defense_weekly -- no new "
            "external fetch, just a normalization pass. Feeds "
            "model-service's K/DST season-long fantasy projections."
        ),
    )
    parser.add_argument(
        "--replace-kicking-defense-history",
        action="store_true",
        help="Delete existing rows for target seasons before rebuild",
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
    parser.add_argument(
        "--run-dr-backup",
        action="store_true",
        help="Run enterprise pg_dump DR backup (+ verify/retention/optional remote upload)",
    )
    parser.add_argument(
        "--skip-dr-verify",
        action="store_true",
        help="With --run-dr-backup, skip restore verification into ephemeral DB",
    )
    parser.add_argument(
        "--skip-dr-upload",
        action="store_true",
        help="With --run-dr-backup, skip remote upload even if NFL_DR_REMOTE_URI is set",
    )
    parser.add_argument(
        "--evaluate-data-freshness",
        action="store_true",
        help="Evaluate NFL data freshness SLOs and persist a snapshot",
    )
    parser.add_argument(
        "--ingest-snap-counts",
        action="store_true",
        help="Ingest nflverse snap counts into nfl_dp_snap_counts_weekly",
    )
    parser.add_argument(
        "--ingest-official-depth-charts",
        action="store_true",
        help="Ingest latest nflverse official depth charts",
    )
    parser.add_argument(
        "--print-source-matrix",
        action="store_true",
        help="Print the executable source fallback matrix JSON",
    )
    parser.add_argument(
        "--materialize-personnel-efficiency",
        action="store_true",
        help="Build personnel efficiency + substitution elasticity weekly (week-lagged)",
    )
    parser.add_argument(
        "--replace-personnel-efficiency",
        action="store_true",
        help="Delete existing personnel/sub-elasticity rows for target seasons before rebuild",
    )
    parser.add_argument(
        "--materialize-coach-aggression",
        action="store_true",
        help="Build coach aggression weekly latents from PBP (week-lagged)",
    )
    parser.add_argument(
        "--replace-coach-aggression",
        action="store_true",
        help="Delete existing coach aggression rows for target seasons before rebuild",
    )
    parser.add_argument(
        "--ingest-participation",
        action="store_true",
        help="Ingest nflverse participation/snap participation into weekly table",
    )
    parser.add_argument(
        "--ingest-draft-picks",
        action="store_true",
        help="Ingest nflverse draft picks into nfl_dp_raw_objects",
    )
    parser.add_argument(
        "--print-external-source-status",
        action="store_true",
        help="Print Visual Crossing / OTC / Spotrac / PFF env status (no network)",
    )
    args = parser.parse_args()
    seasons = _parse_seasons(args.seasons)
    if args.print_source_matrix:
        from .source_matrix import source_matrix_payload

        result = source_matrix_payload()
    elif args.print_external_source_status:
        from .external_sources import external_source_status

        result = external_source_status()
    elif args.ingest_participation:
        from .extended_ingest import ingest_participation_weekly

        result = ingest_participation_weekly(seasons=seasons, replace_existing=False)
    elif args.ingest_draft_picks:
        from .extended_ingest import ingest_draft_picks_raw

        result = ingest_draft_picks_raw(seasons=seasons)
    elif args.materialize_personnel_efficiency:
        from .personnel_efficiency import (
            attach_personnel_to_matchup_features,
            materialize_personnel_efficiency,
        )
        from .db import SessionLocal

        result = materialize_personnel_efficiency(
            seasons=seasons,
            replace_existing=args.replace_personnel_efficiency,
        )
        if result.get("ok"):
            session = SessionLocal()
            try:
                result["matchup_attach"] = attach_personnel_to_matchup_features(
                    session, seasons=seasons
                )
            finally:
                session.close()
    elif args.materialize_coach_aggression:
        from .coach_aggression import materialize_coach_aggression

        result = materialize_coach_aggression(
            seasons=seasons,
            replace_existing=args.replace_coach_aggression,
        )
    elif args.run_dr_backup:
        from .dr_backup import run_dr_backup

        result = run_dr_backup(
            verify=not args.skip_dr_verify,
            upload=not args.skip_dr_upload,
            backup_dir=args.backup_export_dir,
        )
    elif args.evaluate_data_freshness:
        from .freshness import evaluate_data_freshness

        result = evaluate_data_freshness(season=seasons[-1] if seasons else None, week=args.week)
    elif args.ingest_snap_counts:
        from .snap_depth_ingest import ingest_snap_counts

        result = ingest_snap_counts(seasons=seasons)
    elif args.ingest_official_depth_charts:
        from .snap_depth_ingest import ingest_official_depth_charts

        result = ingest_official_depth_charts(seasons=seasons)
    elif args.run_preseason_bootstrap:
        from .preseason_hydration import run_preseason_bootstrap

        result = run_preseason_bootstrap(
            season=seasons[-1],
            prior_season=args.prior_season,
            use_market_signal=not args.no_market_signal,
        )
    elif args.run_inseason_weekly_update:
        from .inseason_weekly_update import run_data_platform_inseason_weekly_update

        target_week = args.week if args.week is not None else args.through_week
        if target_week is None:
            raise SystemExit(
                "--week (or --through-week) is required with --run-inseason-weekly-update"
            )
        result = run_data_platform_inseason_weekly_update(
            season=seasons[-1],
            week=int(target_week),
            skip_ingest=args.skip_ingest,
            rematerialize_remaining_weeks=not args.target_week_features_only,
            dry_run=args.dry_run,
        )
    elif args.refresh_rolling_player_usage:
        from .preseason_hydration import refresh_future_player_usage_from_rolling_real_weeks

        if args.through_week is None:
            raise SystemExit("--through-week is required with --refresh-rolling-player-usage")
        result = refresh_future_player_usage_from_rolling_real_weeks(
            season=seasons[-1],
            through_week=args.through_week,
        )
    elif args.run_launch_hardening:
        from .ops import run_launch_hardening_cycle

        result = run_launch_hardening_cycle(
            seasons=seasons,
            week=args.week,
            include_pbp=not args.no_pbp,
            include_row_exports=args.backup_include_row_exports,
            export_dir=args.backup_export_dir,
        )
    elif args.backup_owned_data:
        from .ops import export_data_ownership_snapshot

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
        elif args.materialize_kav:
            from .kav import materialize_kav

            result = materialize_kav(
                seasons=seasons,
                replace_existing=args.replace_kav,
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
        elif args.materialize_tendency_profiles:
            from .tendency_profiles import materialize_all_tendency_profiles

            result = materialize_all_tendency_profiles(seasons=seasons)
        elif args.materialize_kicking_defense_history:
            from .kicking_defense_history import materialize_kicking_and_defense_history

            result = materialize_kicking_and_defense_history(
                seasons=seasons,
                replace_existing=args.replace_kicking_defense_history,
            )
        else:
            result = ingest_nflverse_snapshot(seasons=seasons, include_pbp=not args.no_pbp)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
