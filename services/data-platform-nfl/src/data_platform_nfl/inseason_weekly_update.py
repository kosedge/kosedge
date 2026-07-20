"""Pure helpers + DP-scoped runner for the in-season weekly update loop.

The full cross-service orchestrator lives in
`scripts/nfl/run-weekly-inseason-update.sh`. This module owns the data-platform
portion (rolling usage refresh + projection-feature rematerialization) and
exposes a dry-runnable step plan for tests and the CLI.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def build_inseason_weekly_update_plan(
    *,
    season: int,
    week: int,
    skip_ingest: bool = False,
    skip_fantasy: bool = False,
    skip_awards: bool = False,
    rematerialize_remaining_weeks: bool = True,
) -> List[Dict[str, Any]]:
    """Return ordered step descriptors for season+week (idempotent, dry-run safe)."""
    if week < 1 or week > 25:
        raise ValueError(f"week must be 1-25, got {week}")
    if season < 2010:
        raise ValueError(f"season must be >= 2010, got {season}")

    steps: List[Dict[str, Any]] = []
    if not skip_ingest:
        steps.append(
            {
                "id": "ingest_launch_hardening",
                "layer": "data_platform",
                "title": "Ingest / refresh owned tables for week",
                "prerequisite": (
                    "Ensures week real usage lands via --run-launch-hardening. "
                    "Safe to re-run; skips PBP with SKIP_INGEST=1 if already fresh."
                ),
                "cli": (
                    f"python3 -m data_platform_nfl.cli --seasons {season} "
                    f"--week {week} --run-launch-hardening"
                ),
            }
        )

    steps.append(
        {
            "id": "refresh_rolling_player_usage",
            "layer": "data_platform",
            "title": "Refresh future-week usage priors from rolling real weeks",
            "prerequisite": f"Real pbp_aggregation usage through week {week} must exist.",
            "cli": (
                f"python3 -m data_platform_nfl.cli --seasons {season} "
                f"--refresh-rolling-player-usage --through-week {week}"
            ),
        }
    )

    feature_week = None if rematerialize_remaining_weeks else week
    feature_cli = (
        f"python3 -m data_platform_nfl.cli --seasons {season} "
        "--materialize-player-projection-features --replace-player-projection-features"
    )
    if feature_week is not None:
        feature_cli += f" --week {feature_week}"
    steps.append(
        {
            "id": "materialize_player_projection_features",
            "layer": "data_platform",
            "title": (
                "Rematerialize player projection features "
                + ("for remaining season weeks" if rematerialize_remaining_weeks else f"for week {week}")
            ),
            "prerequisite": "Rolling usage refresh should complete first.",
            "cli": feature_cli,
        }
    )

    steps.extend(
        [
            {
                "id": "materialize_player_baselines",
                "layer": "model_service",
                "title": f"Rematerialize player baselines for week {week}",
                "prerequisite": "Projection features must exist for the target week.",
                "cli": (
                    f"POST /nfl/ops/materialize-player-baselines"
                    f"?season={season}&week={week}&model_version=nfl-player-v1"
                ),
            },
            {
                "id": "materialize_box_score_sims",
                "layer": "model_service",
                "title": f"Rematerialize box-score sims for week {week}",
                "prerequisite": "Baselines/features for the week should be current.",
                "cli": (
                    "python3 -c \"from src.tasks import materialize_nfl_player_box_score_sims as m; "
                    f'print(m(season={season}, week={week}))"'
                ),
            },
            {
                "id": "materialize_prop_edges",
                "layer": "model_service",
                "title": f"Rematerialize prop edges for week {week}",
                "prerequisite": "Box-score sims or baselines available for props engine.",
                "cli": (
                    f"POST /nfl/ops/materialize-player-props"
                    f"?season={season}&week={week}&model_version=nfl-player-v1"
                ),
            },
        ]
    )

    if not skip_fantasy:
        steps.append(
            {
                "id": "materialize_fantasy_weekly",
                "layer": "model_service",
                "title": f"Rematerialize fantasy weekly for week {week}",
                "prerequisite": "Player baselines current for the week.",
                "cli": (
                    f"POST /nfl/ops/materialize-fantasy"
                    f"?season={season}&week={week}&model_version=nfl-player-v1"
                ),
            }
        )

    if not skip_awards:
        steps.append(
            {
                "id": "materialize_award_projections",
                "layer": "model_service",
                "title": "Rematerialize award projections (season)",
                "prerequisite": "Cheap season board refresh after baselines update.",
                "cli": (
                    f"POST /nfl/ops/materialize-award-projections"
                    f"?season={season}&model_version=nfl-player-v1&top_n=10"
                ),
            }
        )

    return steps


def summarize_inseason_weekly_update(
    *,
    season: int,
    week: int,
    step_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Collapse per-step results into a printable summary dict."""
    ok = 0
    skipped = 0
    failed = 0
    dry_run = 0
    for result in step_results:
        status = str(result.get("status") or "unknown")
        if status in {"ok", "triggered", "enqueued"}:
            ok += 1
        elif status in {"skipped", "skip"}:
            skipped += 1
        elif status in {"dry_run", "planned"}:
            dry_run += 1
        elif status in {"failed", "error"}:
            failed += 1
    return {
        "season": season,
        "week": week,
        "steps_total": len(step_results),
        "steps_ok": ok,
        "steps_skipped": skipped,
        "steps_dry_run": dry_run,
        "steps_failed": failed,
        "status": "failed" if failed else ("dry_run" if dry_run and not ok else "ok"),
        "steps": step_results,
    }


def run_data_platform_inseason_weekly_update(
    *,
    season: int,
    week: int,
    skip_ingest: bool = False,
    rematerialize_remaining_weeks: bool = True,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Execute the data-platform portion of the weekly in-season update.

    Model-service rematerialization is intentionally left to the bash
    orchestrator / ops routes so this CLI stays inside DP ownership.
    """
    plan = build_inseason_weekly_update_plan(
        season=season,
        week=week,
        skip_ingest=skip_ingest,
        skip_fantasy=True,
        skip_awards=True,
        rematerialize_remaining_weeks=rematerialize_remaining_weeks,
    )
    dp_plan = [step for step in plan if step["layer"] == "data_platform"]
    step_results: List[Dict[str, Any]] = []

    if dry_run:
        for step in dp_plan:
            step_results.append({"id": step["id"], "status": "dry_run", "cli": step["cli"]})
        summary = summarize_inseason_weekly_update(
            season=season, week=week, step_results=step_results
        )
        summary["plan"] = dp_plan
        return summary

    from .ingest import materialize_player_projection_features
    from .ops import run_launch_hardening_cycle
    from .preseason_hydration import refresh_future_player_usage_from_rolling_real_weeks

    for step in dp_plan:
        step_id = step["id"]
        try:
            if step_id == "ingest_launch_hardening":
                result = run_launch_hardening_cycle(seasons=[season], week=week, include_pbp=True)
            elif step_id == "refresh_rolling_player_usage":
                result = refresh_future_player_usage_from_rolling_real_weeks(
                    season=season, through_week=week
                )
            elif step_id == "materialize_player_projection_features":
                result = materialize_player_projection_features(
                    seasons=[season],
                    week=None if rematerialize_remaining_weeks else week,
                    replace_existing=True,
                )
            else:
                result = {"status": "skipped", "reason": f"unknown step {step_id}"}
            status = str(result.get("status") or "ok")
            step_results.append({"id": step_id, "status": status, "result": result})
        except Exception as exc:  # noqa: BLE001 - surface in summary for ops
            step_results.append(
                {"id": step_id, "status": "failed", "error": str(exc)}
            )

    summary = summarize_inseason_weekly_update(
        season=season, week=week, step_results=step_results
    )
    summary["plan"] = dp_plan
    return summary
