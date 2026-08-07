"""NFL data freshness SLOs for subscription boards and ops alerting."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text

from .db import SessionLocal
from .source_matrix import SOURCE_FALLBACK_MATRIX, source_matrix_payload

# Ops-only checks: real SLOs for ownership/DR, but must not paint guest boards
# as "data freshness degraded" when live board probes are healthy.
OPS_ONLY_CHECK_NAMES = frozenset({"dr_backup"})


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _blocker_check_name(blocker: str) -> str:
    return str(blocker or "").split(":", 1)[0]


def _hours_since(ts: Optional[datetime]) -> Optional[float]:
    if ts is None:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return max(0.0, (_now() - ts).total_seconds() / 3600.0)


def resolve_active_season_week(session: Any) -> Tuple[Optional[int], Optional[int]]:
    """Pick the most relevant season/week for ops (completed or next upcoming)."""
    row = session.execute(
        text(
            """
            WITH completed AS (
              SELECT season, week
              FROM nfl_dp_schedules
              WHERE home_score IS NOT NULL
                AND week IS NOT NULL
              ORDER BY season DESC, week DESC
              LIMIT 1
            ),
            upcoming AS (
              SELECT season, week
              FROM nfl_dp_schedules
              WHERE game_date IS NOT NULL
                AND game_date >= CURRENT_DATE
                AND week IS NOT NULL
              ORDER BY game_date ASC, week ASC
              LIMIT 1
            )
            SELECT
              COALESCE((SELECT season FROM upcoming), (SELECT season FROM completed)) AS season,
              COALESCE((SELECT week FROM upcoming), (SELECT week FROM completed)) AS week
            """
        )
    ).fetchone()
    if row is None:
        return None, None
    return (
        int(row.season) if row.season is not None else None,
        int(row.week) if row.week is not None else None,
    )


def _latest_ts(session: Any, sql: str, params: Optional[Dict[str, Any]] = None) -> Optional[datetime]:
    row = session.execute(text(sql), params or {}).fetchone()
    if row is None:
        return None
    return getattr(row, "latest_ts", None)


def evaluate_data_freshness(
    *,
    season: Optional[int] = None,
    week: Optional[int] = None,
    persist: bool = True,
    in_season: Optional[bool] = None,
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        resolved_season, resolved_week = resolve_active_season_week(session)
        season = season if season is not None else resolved_season
        week = week if week is not None else resolved_week

        if in_season is None:
            # Treat as in-season when there is a game within +/- 10 days.
            nearby = session.execute(
                text(
                    """
                    SELECT COUNT(*)::int AS n
                    FROM nfl_dp_schedules
                    WHERE game_date BETWEEN CURRENT_DATE - 10 AND CURRENT_DATE + 10
                    """
                )
            ).scalar_one()
            in_season = int(nearby or 0) > 0

        probes: Dict[str, Dict[str, Any]] = {
            "schedules_scores": {
                "latest_ts": _latest_ts(
                    session,
                    "SELECT MAX(updated_at) AS latest_ts FROM nfl_dp_schedules",
                ),
                "max_age_hours": 36,
            },
            "play_by_play": {
                "latest_ts": _latest_ts(
                    session,
                    """
                    SELECT MAX(ingested_at) AS latest_ts
                    FROM nfl_dp_raw_objects
                    WHERE object_type = 'pbp_play'
                    """,
                ),
                "max_age_hours": 48,
            },
            "injuries": {
                "latest_ts": _latest_ts(
                    session,
                    "SELECT MAX(updated_at) AS latest_ts FROM nfl_dp_injuries",
                ),
                "max_age_hours": 24,
            },
            "rosters": {
                "latest_ts": _latest_ts(
                    session,
                    "SELECT MAX(updated_at) AS latest_ts FROM nfl_dp_rosters",
                ),
                "max_age_hours": 72,
            },
            "snap_counts": {
                "latest_ts": _latest_ts(
                    session,
                    """
                    SELECT MAX(updated_at) AS latest_ts
                    FROM nfl_dp_snap_counts_weekly
                    """,
                ),
                "max_age_hours": 48,
                "optional_until_backfilled": True,
            },
            "depth_charts_official": {
                "latest_ts": _latest_ts(
                    session,
                    """
                    SELECT MAX(updated_at) AS latest_ts
                    FROM nfl_dp_official_depth_charts
                    """,
                ),
                "max_age_hours": 72,
                "optional_until_backfilled": True,
            },
            "player_props_odds": {
                "latest_ts": _latest_ts(
                    session,
                    """
                    SELECT MAX(captured_at) AS latest_ts
                    FROM nfl_player_prop_market_snapshots
                    """,
                ),
                "max_age_hours": float(os.getenv("NFL_PROPS_ODDS_MAX_AGE_HOURS", "6")),
            },
            "dr_backup": {
                "latest_ts": _latest_ts(
                    session,
                    """
                    SELECT MAX(created_at) AS latest_ts
                    FROM nfl_data_ownership_backups
                    WHERE backup_type = 'pg_dump'
                       OR COALESCE(manifest->>'backup_type', '') = 'pg_dump'
                    """,
                ),
                "max_age_hours": float(os.getenv("NFL_DR_BACKUP_MAX_AGE_HOURS", "192")),  # 8 days
            },
        }

        # In offseason, relax live board SLOs but keep DR backup SLO.
        checks: Dict[str, Any] = {}
        blockers: List[str] = []
        warnings: List[str] = []

        for name, probe in probes.items():
            age_h = _hours_since(probe.get("latest_ts"))
            max_age = probe.get("max_age_hours")
            optional = bool(probe.get("optional_until_backfilled"))
            enforce = bool(in_season) or name == "dr_backup"
            if name == "player_props_odds" and not in_season:
                enforce = False

            ok = True
            reason = None
            if age_h is None:
                if optional:
                    ok = True
                    reason = "not_backfilled_yet"
                    warnings.append(f"{name}:not_backfilled_yet")
                elif enforce:
                    ok = False
                    reason = "missing_timestamp"
                    blockers.append(f"{name}:missing_timestamp")
                else:
                    reason = "offseason_unenforced_missing"
            elif enforce and max_age is not None and age_h > float(max_age):
                ok = False
                reason = f"stale_{age_h:.1f}h>{max_age}h"
                blockers.append(f"{name}:{reason}")
            elif max_age is not None and age_h > float(max_age):
                reason = f"stale_offseason_{age_h:.1f}h"
                warnings.append(f"{name}:{reason}")

            checks[name] = {
                "ok": ok,
                "age_hours": None if age_h is None else round(age_h, 3),
                "max_age_hours": max_age,
                "latest_ts": (
                    probe["latest_ts"].isoformat()
                    if isinstance(probe.get("latest_ts"), datetime)
                    else None
                ),
                "enforced": enforce,
                "reason": reason,
            }

        # Ingest failure watch
        failed_ingest = session.execute(
            text(
                """
                SELECT COUNT(*)::int AS n
                FROM nfl_dp_ingestion_runs
                WHERE status = 'failed'
                  AND started_at >= NOW() - INTERVAL '7 days'
                """
            )
        ).scalar_one()
        ingest_ok = int(failed_ingest or 0) == 0
        checks["recent_ingest_failures"] = {
            "ok": ingest_ok,
            "failed_last_7d": int(failed_ingest or 0),
            "enforced": True,
            "reason": None if ingest_ok else "ingestion_failures_present",
        }
        if not ingest_ok:
            blockers.append("recent_ingest_failures")

        board_blockers = [
            b for b in blockers if _blocker_check_name(b) not in OPS_ONLY_CHECK_NAMES
        ]
        ops_blockers = [
            b for b in blockers if _blocker_check_name(b) in OPS_ONLY_CHECK_NAMES
        ]
        # Keep DR/ops failures visible without claiming board data is stale.
        for b in ops_blockers:
            if b not in warnings:
                warnings.append(b)

        board_check_failed = any(
            (not c.get("ok")) and bool(c.get("enforced"))
            for name, c in checks.items()
            if name not in OPS_ONLY_CHECK_NAMES
        )
        status = "degraded" if board_blockers or board_check_failed else "ok"
        ops_status = "degraded" if ops_blockers else "ok"

        payload = {
            "status": status,
            "ops_status": ops_status,
            "checked_at": _now().isoformat(),
            "in_season": bool(in_season),
            "season": season,
            "week": week,
            "checks": checks,
            "blockers": board_blockers,
            "ops_blockers": ops_blockers,
            "warnings": warnings,
            "source_matrix": source_matrix_payload(),
            "product_guidance": {
                "fair_lines_board": "usable" if status == "ok" else "show_stale_banner",
                "play_stake_tags": "allowed_if_model_ready" if status == "ok" else "suppress",
                "subscription_claim": (
                    "Data ownership + freshness gates are active."
                    if status == "ok"
                    else "Boards should disclose degraded/stale data state."
                ),
            },
        }

        if persist:
            # Persist full blocker set (board + ops) for ops history.
            persist_blockers = board_blockers + ops_blockers
            persist_status = "degraded" if persist_blockers else status
            session.execute(
                text(
                    """
                    INSERT INTO nfl_data_freshness_snapshots (
                      status, season, week, checks, blockers, source_matrix, created_at
                    ) VALUES (
                      :status, :season, :week, CAST(:checks AS jsonb),
                      CAST(:blockers AS jsonb), CAST(:source_matrix AS jsonb), NOW()
                    )
                    """
                ),
                {
                    "status": persist_status,
                    "season": season,
                    "week": week,
                    "checks": json.dumps(checks),
                    "blockers": json.dumps(persist_blockers),
                    "source_matrix": json.dumps(source_matrix_payload()),
                },
            )
            session.commit()
        return payload
    finally:
        session.close()


def domain_max_age_hours(domain: str) -> Optional[float]:
    for row in SOURCE_FALLBACK_MATRIX:
        if row["domain"] == domain:
            val = row.get("max_age_hours_in_season")
            return float(val) if val is not None else None
    return None
