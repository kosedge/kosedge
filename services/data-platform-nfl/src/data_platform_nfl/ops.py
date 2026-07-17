from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from .db import SessionLocal


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _required_tables() -> List[str]:
    return [
        "nfl_dp_ingestion_runs",
        "nfl_dp_raw_objects",
        "nfl_dp_schedules",
        "nfl_dp_team_game_stats",
        "nfl_dp_player_game_stats",
        "nfl_dp_injuries",
        "nfl_dp_rosters",
        "nfl_dp_team_situational_weekly",
        "nfl_dp_player_usage_weekly",
        "nfl_dp_matchup_features_weekly",
        "nfl_dp_standings_weekly",
        "nfl_dp_depth_chart_weekly",
        "nfl_player_projection_features_weekly",
    ]


def run_data_ownership_preflight() -> Dict[str, Any]:
    session = SessionLocal()
    try:
        tables = {
            str(name)
            for name in session.execute(
                text(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    """
                )
            ).scalars()
        }
        required = _required_tables()
        missing = [name for name in required if name not in tables]
        return {
            "status": "ok" if not missing else "failed",
            "checked_at": _now_iso(),
            "required_table_count": len(required),
            "missing_tables": missing,
        }
    finally:
        session.close()


def _table_metrics_query(table: str) -> str:
    if table == "nfl_dp_ingestion_runs":
        return """
            SELECT
              COUNT(*)::bigint AS row_count,
              MAX(COALESCE(finished_at, started_at)) AS latest_ts
            FROM nfl_dp_ingestion_runs
        """
    if table == "nfl_dp_raw_objects":
        return """
            SELECT
              COUNT(*)::bigint AS row_count,
              MAX(ingested_at) AS latest_ts
            FROM nfl_dp_raw_objects
            WHERE (:season IS NULL OR season = :season)
              AND (CAST(:week AS int) IS NULL OR week = CAST(:week AS int))
        """
    if table == "nfl_dp_rosters":
        return """
            SELECT
              COUNT(*)::bigint AS row_count,
              MAX(updated_at) AS latest_ts
            FROM nfl_dp_rosters
            WHERE (:season IS NULL OR season = :season)
        """
    return f"""
        SELECT
          COUNT(*)::bigint AS row_count,
          MAX(updated_at) AS latest_ts
        FROM {table}
        WHERE (:season IS NULL OR season = :season)
          AND (CAST(:week AS int) IS NULL OR week = CAST(:week AS int))
    """


def _write_table_export(
    session: Any,
    *,
    table: str,
    export_path: Path,
    season: Optional[int],
    week: Optional[int],
) -> int:
    if table == "nfl_dp_ingestion_runs":
        rows = session.execute(
            text(
                """
                SELECT row_to_json(t) AS payload
                FROM (
                  SELECT *
                  FROM nfl_dp_ingestion_runs
                ) t
                """
            )
        ).fetchall()
    elif table == "nfl_dp_rosters":
        rows = session.execute(
            text(
                """
                SELECT row_to_json(t) AS payload
                FROM (
                  SELECT *
                  FROM nfl_dp_rosters
                  WHERE (:season IS NULL OR season = :season)
                ) t
                """
            ),
            {"season": season},
        ).fetchall()
    else:
        rows = session.execute(
            text(
                f"""
                SELECT row_to_json(t) AS payload
                FROM (
                  SELECT *
                  FROM {table}
                  WHERE (:season IS NULL OR season = :season)
                    AND (CAST(:week AS int) IS NULL OR week = CAST(:week AS int))
                ) t
                """
            ),
            {"season": season, "week": week},
        ).fetchall()
    with export_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            payload = row.payload if isinstance(row.payload, dict) else {}
            handle.write(json.dumps(payload, sort_keys=True))
            handle.write("\n")
    return len(rows)


def export_data_ownership_snapshot(
    *,
    seasons: List[int],
    week: Optional[int] = None,
    export_dir: Optional[str] = None,
    include_row_exports: bool = False,
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        target_season = max(seasons) if seasons else None
        tracked_tables = _required_tables()
        table_metrics: Dict[str, Any] = {}
        for table in tracked_tables:
            row = session.execute(
                text(_table_metrics_query(table)),
                {"season": target_season, "week": week},
            ).fetchone()
            table_metrics[table] = {
                "row_count": int(getattr(row, "row_count", 0) or 0),
                "latest_ts": (
                    row.latest_ts.isoformat()
                    if row is not None and getattr(row, "latest_ts", None) is not None
                    else None
                ),
            }

        backup_key = datetime.now(timezone.utc).strftime("nfl-owned-data-%Y%m%dT%H%M%SZ")
        artifact_dir: Optional[Path] = None
        exported_files: Dict[str, Any] = {}
        if include_row_exports:
            base = Path(export_dir or "data/ops")
            artifact_dir = base / backup_key
            artifact_dir.mkdir(parents=True, exist_ok=True)
            for table in tracked_tables:
                path = artifact_dir / f"{table}.ndjson"
                row_count = _write_table_export(
                    session,
                    table=table,
                    export_path=path,
                    season=target_season,
                    week=week,
                )
                exported_files[table] = {"path": str(path), "rows": row_count}

        manifest: Dict[str, Any] = {
            "backup_key": backup_key,
            "created_at": _now_iso(),
            "season_scope": target_season,
            "week_scope": week,
            "table_metrics": table_metrics,
            "exports_enabled": bool(include_row_exports),
            "exported_files": exported_files,
        }

        session.execute(
            text(
                """
                INSERT INTO nfl_data_ownership_backups (
                  backup_key, artifact_dir, manifest, created_at
                ) VALUES (
                  :backup_key, :artifact_dir, CAST(:manifest AS jsonb), NOW()
                )
                ON CONFLICT (backup_key) DO UPDATE SET
                  artifact_dir = EXCLUDED.artifact_dir,
                  manifest = EXCLUDED.manifest
                """
            ),
            {
                "backup_key": backup_key,
                "artifact_dir": str(artifact_dir) if artifact_dir is not None else None,
                "manifest": json.dumps(manifest),
            },
        )
        session.commit()
        return manifest
    finally:
        session.close()


def run_launch_hardening_cycle(
    *,
    seasons: List[int],
    week: Optional[int],
    include_pbp: bool,
    include_row_exports: bool,
    export_dir: Optional[str],
) -> Dict[str, Any]:
    from .ingest import (
        ingest_nflverse_snapshot,
        materialize_depth_chart_weekly,
        materialize_matchup_features_from_usage,
        materialize_player_projection_features,
        materialize_standings_weekly,
        materialize_usage_features_from_pbp,
        normalize_pbp_from_raw,
    )

    preflight = run_data_ownership_preflight()
    if preflight["status"] != "ok":
        return {"status": "failed", "preflight": preflight, "stages": []}

    stages: List[Dict[str, Any]] = []
    stages.append(
        {
            "stage": "ingest_nflverse_snapshot",
            "result": ingest_nflverse_snapshot(seasons=seasons, include_pbp=include_pbp),
        }
    )
    if include_pbp:
        stages.append(
            {
                "stage": "normalize_pbp_from_raw",
                "result": normalize_pbp_from_raw(seasons=seasons, replace_existing=False),
            }
        )
    stages.append(
        {
            "stage": "materialize_usage_features",
            "result": materialize_usage_features_from_pbp(seasons=seasons, replace_existing=False),
        }
    )
    stages.append(
        {
            "stage": "materialize_matchup_features",
            "result": materialize_matchup_features_from_usage(seasons=seasons, replace_existing=False),
        }
    )
    stages.append(
        {
            "stage": "materialize_player_projection_features",
            "result": materialize_player_projection_features(
                seasons=seasons,
                week=week,
                replace_existing=False,
            ),
        }
    )
    stages.append(
        {
            "stage": "materialize_standings",
            "result": materialize_standings_weekly(
                seasons=seasons,
                week=week,
                replace_existing=False,
            ),
        }
    )
    stages.append(
        {
            "stage": "materialize_depth_charts",
            "result": materialize_depth_chart_weekly(
                seasons=seasons,
                week=week,
                replace_existing=False,
            ),
        }
    )
    backup = export_data_ownership_snapshot(
        seasons=seasons,
        week=week,
        export_dir=export_dir,
        include_row_exports=include_row_exports,
    )
    return {
        "status": "ok",
        "preflight": preflight,
        "stages": stages,
        "backup_manifest": backup,
    }
