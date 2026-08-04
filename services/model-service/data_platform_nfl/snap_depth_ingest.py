"""Ingest model-critical nflverse snap counts + official depth charts into owned tables."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import nflreadpy as nfl
from sqlalchemy import text

from .db import SessionLocal
from .ingest import _iter_rows, _safe_load_nflverse_table, _to_float, _to_int, _upsert_raw


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _jsonable_row(row: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key, value in row.items():
        if hasattr(value, "isoformat"):
            try:
                out[key] = value.isoformat()
                continue
            except Exception:
                pass
        # Avoid json.dumps failures on NaN/Inf from Polars/numpy.
        if isinstance(value, float) and (value != value or value in (float("inf"), float("-inf"))):
            out[key] = None
            continue
        out[key] = value
    return out


def _normalize_pct(value: Any) -> Optional[float]:
    """nflverse offense_pct is often 0-1; accept 0-100 and normalize to 0-1."""
    pct = _to_float(value)
    if pct is None:
        return None
    if pct != pct:  # NaN
        return None
    if pct > 1.5:
        return max(0.0, min(1.0, pct / 100.0))
    return max(0.0, min(1.0, pct))


def _pfr_to_gsis_map() -> Dict[str, str]:
    """Bridge nflverse snap PFR ids onto GSIS ids used by usage/features."""
    # load_players is a global directory (no seasons= kwarg).
    players = nfl.load_players()
    out: Dict[str, str] = {}
    for row in _iter_rows(players):
        pfr = str(row.get("pfr_id") or "").strip()
        gsis = str(row.get("gsis_id") or "").strip()
        if pfr and gsis:
            out[pfr] = gsis
    return out


def ingest_snap_counts(*, seasons: List[int], commit_every: int = 500) -> Dict[str, Any]:
    """Persist snap counts into the typed owned table.

    Note: we intentionally do NOT mirror every snap row into nfl_dp_raw_objects
    (already multi-GB). Typed table + ingestion_runs metrics are the ownership
    contract for this feed. Also resolves gsis_player_id so features can join
    snaps onto nfl_dp_player_usage_weekly (GSIS) rows for RB/WR usage tracking.
    """
    session = SessionLocal()
    metrics = {"seasons": seasons, "rows": 0, "gsis_linked": 0, "commit_batches": 0}
    run_id = None
    try:
        run_id = session.execute(
            text(
                """
                INSERT INTO nfl_dp_ingestion_runs (source, pipeline, started_at, status, metrics)
                VALUES ('nflverse', 'snap_counts_weekly', :started_at, 'running', CAST(:metrics AS jsonb))
                RETURNING id
                """
            ),
            {"started_at": _now(), "metrics": json.dumps(metrics)},
        ).scalar_one()
        session.commit()

        pfr_to_gsis = _pfr_to_gsis_map()
        snaps = _safe_load_nflverse_table(nfl.load_snap_counts, seasons=seasons)
        insert_sql = text(
            """
            INSERT INTO nfl_dp_snap_counts_weekly (
              season, week, game_id, player_id, gsis_player_id, player_name, team, position,
              offense_snaps, offense_pct, defense_snaps, defense_pct,
              st_snaps, st_pct, source, updated_at
            ) VALUES (
              :season, :week, :game_id, :player_id, :gsis_player_id, :player_name, :team, :position,
              :offense_snaps, :offense_pct, :defense_snaps, :defense_pct,
              :st_snaps, :st_pct, 'nflverse', :updated_at
            )
            ON CONFLICT (season, week, team, player_id) DO UPDATE SET
              game_id = EXCLUDED.game_id,
              gsis_player_id = COALESCE(EXCLUDED.gsis_player_id, nfl_dp_snap_counts_weekly.gsis_player_id),
              player_name = EXCLUDED.player_name,
              position = EXCLUDED.position,
              offense_snaps = EXCLUDED.offense_snaps,
              offense_pct = EXCLUDED.offense_pct,
              defense_snaps = EXCLUDED.defense_snaps,
              defense_pct = EXCLUDED.defense_pct,
              st_snaps = EXCLUDED.st_snaps,
              st_pct = EXCLUDED.st_pct,
              source = EXCLUDED.source,
              updated_at = EXCLUDED.updated_at
            """
        )
        batch = 0
        now = _now()
        for row in _iter_rows(snaps):
            season = _to_int(row.get("season"))
            week = _to_int(row.get("week"))
            team = str(row.get("team") or "").strip().upper()
            player_id = str(row.get("pfr_player_id") or "").strip()
            if not season or week is None or not team or not player_id:
                continue
            gsis_player_id = pfr_to_gsis.get(player_id)
            if gsis_player_id:
                metrics["gsis_linked"] += 1
            session.execute(
                insert_sql,
                {
                    "season": season,
                    "week": week,
                    "game_id": str(row.get("game_id") or "") or None,
                    "player_id": player_id,
                    "gsis_player_id": gsis_player_id,
                    "player_name": row.get("player"),
                    "team": team,
                    "position": row.get("position"),
                    "offense_snaps": _to_float(row.get("offense_snaps")),
                    "offense_pct": _normalize_pct(row.get("offense_pct")),
                    "defense_snaps": _to_float(row.get("defense_snaps")),
                    "defense_pct": _normalize_pct(row.get("defense_pct")),
                    "st_snaps": _to_float(row.get("st_snaps")),
                    "st_pct": _normalize_pct(row.get("st_pct")),
                    "updated_at": now,
                },
            )
            metrics["rows"] += 1
            batch += 1
            if batch >= commit_every:
                session.commit()
                metrics["commit_batches"] += 1
                batch = 0
                now = _now()

        if batch:
            session.commit()
            metrics["commit_batches"] += 1

        session.execute(
            text(
                """
                UPDATE nfl_dp_ingestion_runs
                SET finished_at = :finished_at, status = 'success', metrics = CAST(:metrics AS jsonb)
                WHERE id = :id
                """
            ),
            {"finished_at": _now(), "metrics": json.dumps(metrics), "id": run_id},
        )
        session.commit()
        return {"status": "success", "metrics": metrics}
    except Exception as exc:
        session.rollback()
        if run_id is not None:
            try:
                session.execute(
                    text(
                        """
                        UPDATE nfl_dp_ingestion_runs
                        SET finished_at = :finished_at, status = 'failed',
                            error_message = :error_message, metrics = CAST(:metrics AS jsonb)
                        WHERE id = :id
                        """
                    ),
                    {
                        "finished_at": _now(),
                        "error_message": str(exc)[:2000],
                        "metrics": json.dumps(metrics),
                        "id": run_id,
                    },
                )
                session.commit()
            except Exception:
                session.rollback()
        raise
    finally:
        session.close()


def _map_date_to_season_week(session: Any, as_of: datetime) -> tuple[Optional[int], Optional[int]]:
    row = session.execute(
        text(
            """
            SELECT season, week
            FROM nfl_dp_schedules
            WHERE game_date IS NOT NULL
            ORDER BY ABS(game_date - CAST(:as_of AS date)) ASC, season DESC, week DESC
            LIMIT 1
            """
        ),
        {"as_of": as_of.date()},
    ).fetchone()
    if row is None:
        return None, None
    return _to_int(row.season), _to_int(row.week)


def ingest_official_depth_charts(*, seasons: List[int]) -> Dict[str, Any]:
    """Persist the latest nflverse depth-chart snapshot mapped onto nearest schedule week."""
    session = SessionLocal()
    metrics: Dict[str, Any] = {
        "seasons": seasons,
        "rows": 0,
        "raw_objects": 0,
        "as_of": None,
        "season": None,
        "week": None,
    }
    run_id = None
    try:
        run_id = session.execute(
            text(
                """
                INSERT INTO nfl_dp_ingestion_runs (source, pipeline, started_at, status, metrics)
                VALUES ('nflverse', 'official_depth_charts', :started_at, 'running', CAST(:metrics AS jsonb))
                RETURNING id
                """
            ),
            {"started_at": _now(), "metrics": json.dumps(metrics)},
        ).scalar_one()
        session.commit()

        depth = _safe_load_nflverse_table(nfl.load_depth_charts, seasons=seasons)
        rows = list(_iter_rows(depth))
        if not rows:
            metrics["note"] = "empty_depth_charts"
            session.execute(
                text(
                    """
                    UPDATE nfl_dp_ingestion_runs
                    SET finished_at = :finished_at, status = 'success', metrics = CAST(:metrics AS jsonb)
                    WHERE id = :id
                    """
                ),
                {"finished_at": _now(), "metrics": json.dumps(metrics), "id": run_id},
            )
            session.commit()
            return {"status": "success", "metrics": metrics}

        def _parse_dt(value: Any) -> Optional[datetime]:
            if value is None:
                return None
            if isinstance(value, datetime):
                return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
            text_v = str(value).strip()
            if not text_v:
                return None
            try:
                return datetime.fromisoformat(text_v.replace("Z", "+00:00"))
            except ValueError:
                return None

        latest_dt_raw = max((str(r.get("dt") or "") for r in rows), default="")
        latest_dt = _parse_dt(latest_dt_raw)
        if latest_dt is None:
            raise RuntimeError("depth charts missing dt timestamps")
        latest_rows = [r for r in rows if str(r.get("dt") or "") == latest_dt_raw]
        season, week = _map_date_to_season_week(session, latest_dt)
        if season is None or week is None:
            season = max(seasons)
            week = 1
        metrics["as_of"] = latest_dt.isoformat()
        metrics["season"] = season
        metrics["week"] = week

        insert_sql = text(
            """
            INSERT INTO nfl_dp_official_depth_charts (
              season, week, team, position, depth_team, player_id, player_name, source, updated_at
            ) VALUES (
              :season, :week, :team, :position, :depth_team, :player_id, :player_name, 'nflverse', :updated_at
            )
            ON CONFLICT (season, week, team, position, depth_team, player_id) DO UPDATE SET
              player_name = EXCLUDED.player_name,
              source = EXCLUDED.source,
              updated_at = EXCLUDED.updated_at
            """
        )
        now = _now()
        for idx, row in enumerate(latest_rows, start=1):
            team = str(row.get("team") or "").strip().upper()
            position = str(row.get("pos_abb") or row.get("pos_name") or "").strip()
            player_id = str(row.get("gsis_id") or row.get("espn_id") or "").strip()
            depth_team = _to_int(row.get("pos_rank")) or 1
            if not team or not position or not player_id:
                continue
            session.execute(
                insert_sql,
                {
                    "season": season,
                    "week": week,
                    "team": team,
                    "position": position,
                    "depth_team": depth_team,
                    "player_id": player_id,
                    "player_name": row.get("player_name"),
                    "updated_at": now,
                },
            )
            # Keep a compact raw sample for audit (every 25th row), not full chart dump.
            if idx % 25 == 0:
                _upsert_raw(
                    session,
                    source="nflverse",
                    object_type="official_depth_chart_sample",
                    object_key=f"{season}:{week}:{team}:{position}:{depth_team}:{player_id}",
                    season=season,
                    week=week,
                    game_id=None,
                    payload=_jsonable_row(row),
                )
                metrics["raw_objects"] += 1
            metrics["rows"] += 1
            if metrics["rows"] % 500 == 0:
                session.commit()

        session.commit()
        session.execute(
            text(
                """
                UPDATE nfl_dp_ingestion_runs
                SET finished_at = :finished_at, status = 'success', metrics = CAST(:metrics AS jsonb)
                WHERE id = :id
                """
            ),
            {"finished_at": _now(), "metrics": json.dumps(metrics), "id": run_id},
        )
        session.commit()
        return {"status": "success", "metrics": metrics}
    except Exception as exc:
        session.rollback()
        if run_id is not None:
            try:
                session.execute(
                    text(
                        """
                        UPDATE nfl_dp_ingestion_runs
                        SET finished_at = :finished_at, status = 'failed',
                            error_message = :error_message, metrics = CAST(:metrics AS jsonb)
                        WHERE id = :id
                        """
                    ),
                    {
                        "finished_at": _now(),
                        "error_message": str(exc)[:2000],
                        "metrics": json.dumps(metrics),
                        "id": run_id,
                    },
                )
                session.commit()
            except Exception:
                session.rollback()
        raise
    finally:
        session.close()

def materialize_weekly_from_official_depth(
    *,
    seasons: List[int],
    week: Optional[int] = None,
    replace_existing: bool = False,
) -> Dict[str, Any]:
    """Bridge ``nfl_dp_official_depth_charts`` → ``nfl_dp_depth_chart_weekly``.

    Preseason path: inferred weekly materialization needs usage rows; until
    those exist, copy official nflverse skill depth into the weekly table the
    season engine already prefers.
    """
    session = SessionLocal()
    metrics: Dict[str, Any] = {
        "seasons": seasons,
        "week": week,
        "replace_existing": replace_existing,
        "rows": 0,
        "teams": 0,
    }
    run_id = None
    skill_positions = ("QB", "RB", "WR", "TE")
    try:
        run_id = session.execute(
            text(
                """
                INSERT INTO nfl_dp_ingestion_runs (source, pipeline, started_at, status, metrics)
                VALUES ('nflverse', 'depth_weekly_from_official', :started_at, 'running', CAST(:metrics AS jsonb))
                RETURNING id
                """
            ),
            {"started_at": _now(), "metrics": json.dumps(metrics)},
        ).scalar_one()
        session.commit()

        insert_sql = text(
            """
            INSERT INTO nfl_dp_depth_chart_weekly (
              season, week, team, position, depth_order, depth_slot,
              player_uid, player_id, player_name, role_confidence,
              inferred_source, updated_at
            ) VALUES (
              :season, :week, :team, :position, :depth_order, :depth_slot,
              NULL, :player_id, :player_name, :role_confidence,
              :inferred_source, :updated_at
            )
            ON CONFLICT (season, week, team, position, depth_order) DO UPDATE SET
              depth_slot = EXCLUDED.depth_slot,
              player_id = EXCLUDED.player_id,
              player_name = EXCLUDED.player_name,
              role_confidence = EXCLUDED.role_confidence,
              inferred_source = EXCLUDED.inferred_source,
              updated_at = EXCLUDED.updated_at
            """
        )
        now = _now()
        teams_seen: set[str] = set()
        for season in seasons:
            target_week = week
            if target_week is None:
                row = session.execute(
                    text(
                        """
                        SELECT week
                        FROM nfl_dp_official_depth_charts
                        WHERE season = :season
                        ORDER BY week DESC
                        LIMIT 1
                        """
                    ),
                    {"season": int(season)},
                ).fetchone()
                target_week = int(row.week) if row is not None else 1

            if replace_existing:
                session.execute(
                    text(
                        """
                        DELETE FROM nfl_dp_depth_chart_weekly
                        WHERE season = :season
                          AND week = :week
                          AND inferred_source = 'official_nflverse_bridge'
                        """
                    ),
                    {"season": int(season), "week": int(target_week)},
                )

            official = session.execute(
                text(
                    """
                    SELECT DISTINCT ON (team, position, depth_team)
                      team, position, depth_team, player_id, player_name
                    FROM nfl_dp_official_depth_charts
                    WHERE season = :season
                      AND week = :week
                      AND position IN ('QB', 'RB', 'WR', 'TE')
                      AND depth_team BETWEEN 1 AND 3
                    ORDER BY team, position, depth_team, player_id
                    """
                ),
                {"season": int(season), "week": int(target_week)},
            ).fetchall()

            for r in official:
                team = str(r.team or "").strip().upper()
                if team == "LAR":
                    team = "LA"
                pos = str(r.position or "").strip().upper()
                depth_order = int(r.depth_team or 0)
                player_id = str(r.player_id or "").strip()
                player_name = str(r.player_name or "").strip()
                if (
                    not team
                    or pos not in skill_positions
                    or depth_order < 1
                    or not player_id
                    or not player_name
                ):
                    continue
                depth_slot = {1: "starter", 2: "backup", 3: "rotation"}.get(
                    depth_order, "depth"
                )
                session.execute(
                    insert_sql,
                    {
                        "season": int(season),
                        "week": int(target_week),
                        "team": team,
                        "position": pos,
                        "depth_order": depth_order,
                        "depth_slot": depth_slot,
                        "player_id": player_id,
                        "player_name": player_name,
                        "role_confidence": 0.85 if depth_order == 1 else 0.65,
                        "inferred_source": "official_nflverse_bridge",
                        "updated_at": now,
                    },
                )
                metrics["rows"] += 1
                teams_seen.add(team)

        metrics["teams"] = len(teams_seen)
        session.commit()
        session.execute(
            text(
                """
                UPDATE nfl_dp_ingestion_runs
                SET finished_at = :finished_at, status = 'success', metrics = CAST(:metrics AS jsonb)
                WHERE id = :id
                """
            ),
            {"finished_at": _now(), "metrics": json.dumps(metrics), "id": run_id},
        )
        session.commit()
        return {"status": "success", "metrics": metrics}
    except Exception as exc:
        session.rollback()
        if run_id is not None:
            try:
                session.execute(
                    text(
                        """
                        UPDATE nfl_dp_ingestion_runs
                        SET finished_at = :finished_at, status = 'failed',
                            error_message = :error_message, metrics = CAST(:metrics AS jsonb)
                        WHERE id = :id
                        """
                    ),
                    {
                        "finished_at": _now(),
                        "error_message": str(exc)[:2000],
                        "metrics": json.dumps(metrics),
                        "id": run_id,
                    },
                )
                session.commit()
            except Exception:
                session.rollback()
        raise
    finally:
        session.close()

