from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List

from sqlalchemy import text

from .db import SessionLocal
from .nfl_com import NflComError, fetch_nfl_com_team_intel_snapshot
from .team_intel import build_standings_rows, infer_depth_chart_rows


def _nflreadpy():
    """Lazy import — workers rematerializing SQL features need not ship nflreadpy."""
    import nflreadpy as nfl

    return nfl


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _checksum(payload: Dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _iter_rows(df: Any) -> Iterable[Dict[str, Any]]:
    # nflreadpy returns Polars DataFrames.
    if df is None:
        return
    if hasattr(df, "iter_rows"):
        for row in df.iter_rows(named=True):
            yield dict(row)


def _safe_load_nflverse_table(loader: Any, *, seasons: List[int]) -> Any:
    """Load nflverse tables; skip unavailable future-season assets without failing ingest."""
    try:
        return loader(seasons=seasons)
    except Exception as exc:
        message = str(exc)
        if any(token in message for token in ("404", "Not Found", "must be between")):
            return None
        raise


def _to_int(v: Any) -> int | None:
    try:
        if v is None:
            return None
        return int(v)
    except (TypeError, ValueError):
        return None


def _to_float(v: Any) -> float | None:
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _upsert_raw(session: Any, *, source: str, object_type: str, object_key: str, season: int | None, week: int | None, game_id: str | None, payload: Dict[str, Any]) -> None:
    session.execute(
        text(
            """
            INSERT INTO nfl_dp_raw_objects (
              source, object_type, object_key, season, week, game_id, payload, checksum, ingested_at
            ) VALUES (
              :source, :object_type, :object_key, :season, :week, :game_id, CAST(:payload AS jsonb), :checksum, :ingested_at
            )
            ON CONFLICT (source, object_type, object_key) DO UPDATE SET
              season = EXCLUDED.season,
              week = EXCLUDED.week,
              game_id = EXCLUDED.game_id,
              payload = EXCLUDED.payload,
              checksum = EXCLUDED.checksum,
              ingested_at = EXCLUDED.ingested_at
            """
        ),
        {
            "source": source,
            "object_type": object_type,
            "object_key": object_key,
            "season": season,
            "week": week,
            "game_id": game_id,
            "payload": json.dumps(payload),
            "checksum": _checksum(payload),
            "ingested_at": _now(),
        },
    )


def _overlay_nfl_com_team_intel(
    *,
    session: Any,
    seasons: List[int],
    metrics: Dict[str, Any],
) -> None:
    rows_metrics = metrics.setdefault("rows", {})
    rows_metrics.setdefault("nfl_com_rosters", 0)
    rows_metrics.setdefault("nfl_com_team_stats", 0)
    rows_metrics.setdefault("nfl_com_standings", 0)

    intel_metrics = metrics.setdefault("nfl_com", {})
    diagnostics: List[Dict[str, Any]] = []
    errors: List[str] = []

    for season in seasons:
        try:
            snapshot = fetch_nfl_com_team_intel_snapshot(season=season)
        except NflComError as exc:
            errors.append(f"{season}:{exc}")
            continue
        except Exception as exc:
            errors.append(f"{season}:unexpected:{exc}")
            continue

        diagnostics.append(snapshot.get("diagnostics") or {})
        rosters = snapshot.get("rosters") or []
        standings = snapshot.get("standings") or []
        team_stats = snapshot.get("team_stats") or []

        for item in rosters:
            player_id = str(item.get("player_id") or "").strip()
            team = str(item.get("team") or "").strip().upper()
            if not player_id or not team:
                continue
            session.execute(
                text(
                    """
                    INSERT INTO nfl_dp_rosters (
                      season, team, player_id, player_name, position, jersey_number, source, updated_at
                    ) VALUES (
                      :season, :team, :player_id, :player_name, :position, :jersey_number, :source, NOW()
                    )
                    ON CONFLICT (season, team, player_id) DO UPDATE SET
                      player_name = EXCLUDED.player_name,
                      position = EXCLUDED.position,
                      jersey_number = EXCLUDED.jersey_number,
                      source = EXCLUDED.source,
                      updated_at = EXCLUDED.updated_at
                    """
                ),
                {
                    "season": season,
                    "team": team,
                    "player_id": player_id,
                    "player_name": item.get("player_name"),
                    "position": item.get("position"),
                    "jersey_number": item.get("jersey_number"),
                    "source": "nfl_com",
                },
            )
            _upsert_raw(
                session,
                source="nfl_com",
                object_type="roster_player",
                object_key=f"{season}:{team}:{player_id}",
                season=season,
                week=snapshot.get("week"),
                game_id=None,
                payload=dict(item),
            )
            rows_metrics["nfl_com_rosters"] += 1

        for item in standings:
            team = str(item.get("team") or "").strip().upper()
            week = _to_int(item.get("week"))
            if not team or week is None:
                continue
            session.execute(
                text(
                    """
                    INSERT INTO nfl_dp_standings_weekly (
                      season, week, team,
                      wins, losses, ties,
                      points_for, points_against, point_diff, win_pct,
                      conference, division,
                      conference_wins, conference_losses, conference_ties, conference_pct,
                      division_wins, division_losses, division_ties, division_pct,
                      source, updated_at
                    ) VALUES (
                      :season, :week, :team,
                      :wins, :losses, :ties,
                      :points_for, :points_against, :point_diff, :win_pct,
                      :conference, :division,
                      :conference_wins, :conference_losses, :conference_ties, :conference_pct,
                      :division_wins, :division_losses, :division_ties, :division_pct,
                      :source, NOW()
                    )
                    ON CONFLICT (season, week, team) DO UPDATE SET
                      wins = EXCLUDED.wins,
                      losses = EXCLUDED.losses,
                      ties = EXCLUDED.ties,
                      points_for = EXCLUDED.points_for,
                      points_against = EXCLUDED.points_against,
                      point_diff = EXCLUDED.point_diff,
                      win_pct = EXCLUDED.win_pct,
                      conference = EXCLUDED.conference,
                      division = EXCLUDED.division,
                      conference_wins = EXCLUDED.conference_wins,
                      conference_losses = EXCLUDED.conference_losses,
                      conference_ties = EXCLUDED.conference_ties,
                      conference_pct = EXCLUDED.conference_pct,
                      division_wins = EXCLUDED.division_wins,
                      division_losses = EXCLUDED.division_losses,
                      division_ties = EXCLUDED.division_ties,
                      division_pct = EXCLUDED.division_pct,
                      source = EXCLUDED.source,
                      updated_at = EXCLUDED.updated_at
                    """
                ),
                {
                    "season": season,
                    "week": week,
                    "team": team,
                    "wins": _to_int(item.get("wins")) or 0,
                    "losses": _to_int(item.get("losses")) or 0,
                    "ties": _to_int(item.get("ties")) or 0,
                    "points_for": _to_int(item.get("points_for")) or 0,
                    "points_against": _to_int(item.get("points_against")) or 0,
                    "point_diff": _to_int(item.get("point_diff")) or 0,
                    "win_pct": _to_float(item.get("win_pct")),
                    "conference": item.get("conference"),
                    "division": item.get("division"),
                    "conference_wins": _to_int(item.get("conference_wins")),
                    "conference_losses": _to_int(item.get("conference_losses")),
                    "conference_ties": _to_int(item.get("conference_ties")),
                    "conference_pct": _to_float(item.get("conference_pct")),
                    "division_wins": _to_int(item.get("division_wins")),
                    "division_losses": _to_int(item.get("division_losses")),
                    "division_ties": _to_int(item.get("division_ties")),
                    "division_pct": _to_float(item.get("division_pct")),
                    "source": "nfl_com",
                },
            )
            _upsert_raw(
                session,
                source="nfl_com",
                object_type="standings_team_week",
                object_key=f"{season}:{week}:{team}",
                season=season,
                week=week,
                game_id=None,
                payload=dict(item),
            )
            rows_metrics["nfl_com_standings"] += 1

        for item in team_stats:
            team = str(item.get("team") or "").strip().upper()
            week = _to_int(item.get("week"))
            if not team or week is None:
                continue
            session.execute(
                text(
                    """
                    INSERT INTO nfl_dp_team_situational_weekly (
                      season, week, team, games_played,
                      offensive_plays, defensive_plays, pass_plays, run_plays,
                      early_down_plays, early_down_pass_plays,
                      third_down_attempts, third_down_conversions,
                      fourth_down_attempts, fourth_down_conversions,
                      red_zone_plays, red_zone_touchdowns,
                      sacks_allowed, qb_hits_allowed, sacks_generated, qb_hits_generated,
                      explosive_pass_plays, explosive_pass_allowed,
                      pass_rate, early_down_pass_rate,
                      third_down_conversion_rate, fourth_down_conversion_rate, red_zone_td_rate,
                      pressure_rate_allowed, pressure_rate_generated,
                      success_rate_offense, success_rate_defense_allowed,
                      epa_per_play_offense, epa_per_play_defense_allowed,
                      source, updated_at
                    ) VALUES (
                      :season, :week, :team, :games_played,
                      :offensive_plays, :defensive_plays, :pass_plays, :run_plays,
                      :early_down_plays, :early_down_pass_plays,
                      :third_down_attempts, :third_down_conversions,
                      :fourth_down_attempts, :fourth_down_conversions,
                      :red_zone_plays, :red_zone_touchdowns,
                      :sacks_allowed, :qb_hits_allowed, :sacks_generated, :qb_hits_generated,
                      :explosive_pass_plays, :explosive_pass_allowed,
                      :pass_rate, :early_down_pass_rate,
                      :third_down_conversion_rate, :fourth_down_conversion_rate, :red_zone_td_rate,
                      :pressure_rate_allowed, :pressure_rate_generated,
                      :success_rate_offense, :success_rate_defense_allowed,
                      :epa_per_play_offense, :epa_per_play_defense_allowed,
                      :source, NOW()
                    )
                    ON CONFLICT (season, week, team) DO UPDATE SET
                      games_played = EXCLUDED.games_played,
                      offensive_plays = EXCLUDED.offensive_plays,
                      defensive_plays = EXCLUDED.defensive_plays,
                      pass_plays = EXCLUDED.pass_plays,
                      run_plays = EXCLUDED.run_plays,
                      early_down_plays = EXCLUDED.early_down_plays,
                      early_down_pass_plays = EXCLUDED.early_down_pass_plays,
                      third_down_attempts = EXCLUDED.third_down_attempts,
                      third_down_conversions = EXCLUDED.third_down_conversions,
                      fourth_down_attempts = EXCLUDED.fourth_down_attempts,
                      fourth_down_conversions = EXCLUDED.fourth_down_conversions,
                      red_zone_plays = EXCLUDED.red_zone_plays,
                      red_zone_touchdowns = EXCLUDED.red_zone_touchdowns,
                      sacks_allowed = EXCLUDED.sacks_allowed,
                      qb_hits_allowed = EXCLUDED.qb_hits_allowed,
                      sacks_generated = EXCLUDED.sacks_generated,
                      qb_hits_generated = EXCLUDED.qb_hits_generated,
                      explosive_pass_plays = EXCLUDED.explosive_pass_plays,
                      explosive_pass_allowed = EXCLUDED.explosive_pass_allowed,
                      pass_rate = EXCLUDED.pass_rate,
                      early_down_pass_rate = EXCLUDED.early_down_pass_rate,
                      third_down_conversion_rate = EXCLUDED.third_down_conversion_rate,
                      fourth_down_conversion_rate = EXCLUDED.fourth_down_conversion_rate,
                      red_zone_td_rate = EXCLUDED.red_zone_td_rate,
                      pressure_rate_allowed = EXCLUDED.pressure_rate_allowed,
                      pressure_rate_generated = EXCLUDED.pressure_rate_generated,
                      success_rate_offense = EXCLUDED.success_rate_offense,
                      success_rate_defense_allowed = EXCLUDED.success_rate_defense_allowed,
                      epa_per_play_offense = EXCLUDED.epa_per_play_offense,
                      epa_per_play_defense_allowed = EXCLUDED.epa_per_play_defense_allowed,
                      source = EXCLUDED.source,
                      updated_at = EXCLUDED.updated_at
                    """
                ),
                {
                    **item,
                    "season": season,
                    "week": week,
                    "team": team,
                    "source": "nfl_com",
                },
            )
            _upsert_raw(
                session,
                source="nfl_com",
                object_type="team_situational_week",
                object_key=f"{season}:{week}:{team}",
                season=season,
                week=week,
                game_id=None,
                payload=dict(item),
            )
            rows_metrics["nfl_com_team_stats"] += 1

    intel_metrics["attempted"] = bool(seasons)
    intel_metrics["diagnostics"] = diagnostics
    if errors:
        intel_metrics["errors"] = errors


def normalize_pbp_from_raw(*, seasons: List[int], replace_existing: bool = False) -> Dict[str, Any]:
    session = SessionLocal()
    run_id = None
    normalized_rows = 0
    metrics = {
        "seasons": seasons,
        "replace_existing": replace_existing,
        "rows": {
            "raw_source_rows": 0,
            "normalized_rows": 0,
        },
    }

    try:
        run_id = session.execute(
            text(
                """
                INSERT INTO nfl_dp_ingestion_runs (source, pipeline, started_at, status, metrics)
                VALUES (:source, :pipeline, :started_at, :status, CAST(:metrics AS jsonb))
                RETURNING id
                """
            ),
            {
                "source": "nflverse",
                "pipeline": "nfl_pbp_normalization",
                "started_at": _now(),
                "status": "running",
                "metrics": json.dumps(metrics),
            },
        ).scalar_one()

        for season in seasons:
            if replace_existing:
                session.execute(
                    text("DELETE FROM nfl_dp_play_by_play WHERE season = :season"),
                    {"season": season},
                )

            raw_count = session.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM nfl_dp_raw_objects
                    WHERE source = 'nflverse'
                      AND object_type = 'pbp_play'
                      AND season = :season
                    """
                ),
                {"season": season},
            ).scalar_one()
            metrics["rows"]["raw_source_rows"] += int(raw_count or 0)

            session.execute(
                text(
                    """
                    INSERT INTO nfl_dp_play_by_play (
                      season, week, game_id, play_id, game_date, game_day, start_time,
                      home_team, away_team, posteam, defteam, play_type, down, ydstogo,
                      yardline_100, yards_gained, passing_yards, rushing_yards, receiving_yards,
                      air_yards, yards_after_catch, passer_player_id, passer_player_name,
                      receiver_player_id, receiver_player_name, rusher_player_id, rusher_player_name,
                      complete_pass, incomplete_pass, interception, touchdown, first_down, sack, qb_hit,
                      fumble, penalty, epa, wpa, success, score_differential, play_description,
                      shotgun, no_huddle, qb_dropback, pass_location, run_location, run_gap,
                      xpass, cp, xyac_epa,
                      offense_personnel, defense_personnel, wp, vegas_wp,
                      fixed_drive, series, qtr, half_seconds_remaining, game_seconds_remaining,
                      source,
                      object_key, updated_at
                    )
                    SELECT
                      COALESCE(
                        CASE
                          WHEN trim(COALESCE(payload->>'season', '')) ~ '^-?[0-9]+(\.[0-9]+)?$'
                            THEN (payload->>'season')::numeric::int
                          ELSE NULL
                        END,
                        season
                      ) AS season,
                      CASE
                        WHEN trim(COALESCE(payload->>'week', '')) ~ '^-?[0-9]+(\.[0-9]+)?$'
                          THEN (payload->>'week')::numeric::int
                        ELSE NULL
                      END AS week,
                      payload->>'game_id' AS game_id,
                      COALESCE(NULLIF(payload->>'play_id', ''), NULLIF(payload->>'old_game_id', '')) AS play_id,
                      NULLIF(payload->>'game_date', '')::date AS game_date,
                      payload->>'game_day' AS game_day,
                      payload->>'start_time' AS start_time,
                      payload->>'home_team' AS home_team,
                      payload->>'away_team' AS away_team,
                      payload->>'posteam' AS posteam,
                      payload->>'defteam' AS defteam,
                      payload->>'play_type' AS play_type,
                      CASE
                        WHEN trim(COALESCE(payload->>'down', '')) ~ '^-?[0-9]+(\.[0-9]+)?$'
                          THEN (payload->>'down')::numeric::int
                        ELSE NULL
                      END AS down,
                      CASE WHEN trim(COALESCE(payload->>'ydstogo', '')) ~ '^-?[0-9]+(\.[0-9]+)?$' THEN (payload->>'ydstogo')::numeric ELSE NULL END AS ydstogo,
                      CASE WHEN trim(COALESCE(payload->>'yardline_100', '')) ~ '^-?[0-9]+(\.[0-9]+)?$' THEN (payload->>'yardline_100')::numeric ELSE NULL END AS yardline_100,
                      CASE WHEN trim(COALESCE(payload->>'yards_gained', '')) ~ '^-?[0-9]+(\.[0-9]+)?$' THEN (payload->>'yards_gained')::numeric ELSE NULL END AS yards_gained,
                      CASE WHEN trim(COALESCE(payload->>'passing_yards', '')) ~ '^-?[0-9]+(\.[0-9]+)?$' THEN (payload->>'passing_yards')::numeric ELSE NULL END AS passing_yards,
                      CASE WHEN trim(COALESCE(payload->>'rushing_yards', '')) ~ '^-?[0-9]+(\.[0-9]+)?$' THEN (payload->>'rushing_yards')::numeric ELSE NULL END AS rushing_yards,
                      CASE WHEN trim(COALESCE(payload->>'receiving_yards', '')) ~ '^-?[0-9]+(\.[0-9]+)?$' THEN (payload->>'receiving_yards')::numeric ELSE NULL END AS receiving_yards,
                      CASE WHEN trim(COALESCE(payload->>'air_yards', '')) ~ '^-?[0-9]+(\.[0-9]+)?$' THEN (payload->>'air_yards')::numeric ELSE NULL END AS air_yards,
                      CASE WHEN trim(COALESCE(payload->>'yards_after_catch', '')) ~ '^-?[0-9]+(\.[0-9]+)?$' THEN (payload->>'yards_after_catch')::numeric ELSE NULL END AS yards_after_catch,
                      payload->>'passer_player_id' AS passer_player_id,
                      payload->>'passer_player_name' AS passer_player_name,
                      payload->>'receiver_player_id' AS receiver_player_id,
                      payload->>'receiver_player_name' AS receiver_player_name,
                      payload->>'rusher_player_id' AS rusher_player_id,
                      payload->>'rusher_player_name' AS rusher_player_name,
                      CASE
                        WHEN payload ? 'complete_pass' THEN
                          CASE
                            WHEN lower(trim(payload->>'complete_pass')) IN ('true', 't', '1', '1.0', 'yes', 'y') THEN TRUE
                            WHEN lower(trim(payload->>'complete_pass')) IN ('false', 'f', '0', '0.0', 'no', 'n') THEN FALSE
                            ELSE NULL
                          END
                        ELSE NULL
                      END AS complete_pass,
                      CASE
                        WHEN payload ? 'incomplete_pass' THEN
                          CASE
                            WHEN lower(trim(payload->>'incomplete_pass')) IN ('true', 't', '1', '1.0', 'yes', 'y') THEN TRUE
                            WHEN lower(trim(payload->>'incomplete_pass')) IN ('false', 'f', '0', '0.0', 'no', 'n') THEN FALSE
                            ELSE NULL
                          END
                        ELSE NULL
                      END AS incomplete_pass,
                      CASE
                        WHEN payload ? 'interception' THEN
                          CASE
                            WHEN lower(trim(payload->>'interception')) IN ('true', 't', '1', '1.0', 'yes', 'y') THEN TRUE
                            WHEN lower(trim(payload->>'interception')) IN ('false', 'f', '0', '0.0', 'no', 'n') THEN FALSE
                            ELSE NULL
                          END
                        ELSE NULL
                      END AS interception,
                      CASE
                        WHEN payload ? 'touchdown' THEN
                          CASE
                            WHEN lower(trim(payload->>'touchdown')) IN ('true', 't', '1', '1.0', 'yes', 'y') THEN TRUE
                            WHEN lower(trim(payload->>'touchdown')) IN ('false', 'f', '0', '0.0', 'no', 'n') THEN FALSE
                            ELSE NULL
                          END
                        ELSE NULL
                      END AS touchdown,
                      CASE
                        WHEN payload ? 'first_down' THEN
                          CASE
                            WHEN lower(trim(payload->>'first_down')) IN ('true', 't', '1', '1.0', 'yes', 'y') THEN TRUE
                            WHEN lower(trim(payload->>'first_down')) IN ('false', 'f', '0', '0.0', 'no', 'n') THEN FALSE
                            ELSE NULL
                          END
                        ELSE NULL
                      END AS first_down,
                      CASE
                        WHEN payload ? 'sack' THEN
                          CASE
                            WHEN lower(trim(payload->>'sack')) IN ('true', 't', '1', '1.0', 'yes', 'y') THEN TRUE
                            WHEN lower(trim(payload->>'sack')) IN ('false', 'f', '0', '0.0', 'no', 'n') THEN FALSE
                            ELSE NULL
                          END
                        ELSE NULL
                      END AS sack,
                      CASE
                        WHEN payload ? 'qb_hit' THEN
                          CASE
                            WHEN lower(trim(payload->>'qb_hit')) IN ('true', 't', '1', '1.0', 'yes', 'y') THEN TRUE
                            WHEN lower(trim(payload->>'qb_hit')) IN ('false', 'f', '0', '0.0', 'no', 'n') THEN FALSE
                            ELSE NULL
                          END
                        ELSE NULL
                      END AS qb_hit,
                      CASE
                        WHEN payload ? 'fumble' THEN
                          CASE
                            WHEN lower(trim(payload->>'fumble')) IN ('true', 't', '1', '1.0', 'yes', 'y') THEN TRUE
                            WHEN lower(trim(payload->>'fumble')) IN ('false', 'f', '0', '0.0', 'no', 'n') THEN FALSE
                            ELSE NULL
                          END
                        ELSE NULL
                      END AS fumble,
                      CASE
                        WHEN payload ? 'penalty' THEN
                          CASE
                            WHEN lower(trim(payload->>'penalty')) IN ('true', 't', '1', '1.0', 'yes', 'y') THEN TRUE
                            WHEN lower(trim(payload->>'penalty')) IN ('false', 'f', '0', '0.0', 'no', 'n') THEN FALSE
                            ELSE NULL
                          END
                        ELSE NULL
                      END AS penalty,
                      CASE WHEN trim(COALESCE(payload->>'epa', '')) ~ '^-?[0-9]+(\.[0-9]+)?$' THEN (payload->>'epa')::numeric ELSE NULL END AS epa,
                      CASE WHEN trim(COALESCE(payload->>'wpa', '')) ~ '^-?[0-9]+(\.[0-9]+)?$' THEN (payload->>'wpa')::numeric ELSE NULL END AS wpa,
                      CASE
                        WHEN payload ? 'success' THEN
                          CASE
                            WHEN lower(trim(payload->>'success')) IN ('true', 't', '1', '1.0', 'yes', 'y') THEN TRUE
                            WHEN lower(trim(payload->>'success')) IN ('false', 'f', '0', '0.0', 'no', 'n') THEN FALSE
                            ELSE NULL
                          END
                        ELSE NULL
                      END AS success,
                      CASE WHEN trim(COALESCE(payload->>'score_differential', '')) ~ '^-?[0-9]+(\.[0-9]+)?$' THEN (payload->>'score_differential')::numeric ELSE NULL END AS score_differential,
                      payload->>'desc' AS play_description,
                      CASE
                        WHEN payload ? 'shotgun' THEN
                          CASE
                            WHEN lower(trim(payload->>'shotgun')) IN ('true', 't', '1', '1.0', 'yes', 'y') THEN TRUE
                            WHEN lower(trim(payload->>'shotgun')) IN ('false', 'f', '0', '0.0', 'no', 'n') THEN FALSE
                            ELSE NULL
                          END
                        ELSE NULL
                      END AS shotgun,
                      CASE
                        WHEN payload ? 'no_huddle' THEN
                          CASE
                            WHEN lower(trim(payload->>'no_huddle')) IN ('true', 't', '1', '1.0', 'yes', 'y') THEN TRUE
                            WHEN lower(trim(payload->>'no_huddle')) IN ('false', 'f', '0', '0.0', 'no', 'n') THEN FALSE
                            ELSE NULL
                          END
                        ELSE NULL
                      END AS no_huddle,
                      CASE
                        WHEN payload ? 'qb_dropback' THEN
                          CASE
                            WHEN lower(trim(payload->>'qb_dropback')) IN ('true', 't', '1', '1.0', 'yes', 'y') THEN TRUE
                            WHEN lower(trim(payload->>'qb_dropback')) IN ('false', 'f', '0', '0.0', 'no', 'n') THEN FALSE
                            ELSE NULL
                          END
                        ELSE NULL
                      END AS qb_dropback,
                      NULLIF(payload->>'pass_location', '') AS pass_location,
                      NULLIF(payload->>'run_location', '') AS run_location,
                      NULLIF(payload->>'run_gap', '') AS run_gap,
                      CASE WHEN trim(COALESCE(payload->>'xpass', '')) ~ '^-?[0-9]+(\.[0-9]+)?$' THEN (payload->>'xpass')::numeric ELSE NULL END AS xpass,
                      CASE WHEN trim(COALESCE(payload->>'cp', '')) ~ '^-?[0-9]+(\.[0-9]+)?$' THEN (payload->>'cp')::numeric ELSE NULL END AS cp,
                      CASE WHEN trim(COALESCE(payload->>'xyac_epa', '')) ~ '^-?[0-9]+(\.[0-9]+)?$' THEN (payload->>'xyac_epa')::numeric ELSE NULL END AS xyac_epa,
                      NULLIF(payload->>'offense_personnel', '') AS offense_personnel,
                      NULLIF(payload->>'defense_personnel', '') AS defense_personnel,
                      CASE WHEN trim(COALESCE(payload->>'wp', '')) ~ '^-?[0-9]+(\.[0-9]+)?$' THEN (payload->>'wp')::numeric ELSE NULL END AS wp,
                      CASE WHEN trim(COALESCE(payload->>'vegas_wp', '')) ~ '^-?[0-9]+(\.[0-9]+)?$' THEN (payload->>'vegas_wp')::numeric ELSE NULL END AS vegas_wp,
                      CASE WHEN trim(COALESCE(payload->>'fixed_drive', '')) ~ '^-?[0-9]+(\.[0-9]+)?$' THEN (payload->>'fixed_drive')::numeric::int ELSE NULL END AS fixed_drive,
                      CASE WHEN trim(COALESCE(payload->>'series', '')) ~ '^-?[0-9]+(\.[0-9]+)?$' THEN (payload->>'series')::numeric::int ELSE NULL END AS series,
                      CASE WHEN trim(COALESCE(payload->>'qtr', '')) ~ '^-?[0-9]+(\.[0-9]+)?$' THEN (payload->>'qtr')::numeric::int ELSE NULL END AS qtr,
                      CASE WHEN trim(COALESCE(payload->>'half_seconds_remaining', '')) ~ '^-?[0-9]+(\.[0-9]+)?$' THEN (payload->>'half_seconds_remaining')::numeric ELSE NULL END AS half_seconds_remaining,
                      CASE WHEN trim(COALESCE(payload->>'game_seconds_remaining', '')) ~ '^-?[0-9]+(\.[0-9]+)?$' THEN (payload->>'game_seconds_remaining')::numeric ELSE NULL END AS game_seconds_remaining,
                      source,
                      object_key,
                      NOW()
                    FROM nfl_dp_raw_objects
                    WHERE source = 'nflverse'
                      AND object_type = 'pbp_play'
                      AND season = :season
                      AND COALESCE(NULLIF(payload->>'game_id', ''), '') <> ''
                      AND COALESCE(NULLIF(payload->>'play_id', ''), NULLIF(payload->>'old_game_id', ''), '') <> ''
                    ON CONFLICT (season, game_id, play_id) DO UPDATE SET
                      week = EXCLUDED.week,
                      game_date = EXCLUDED.game_date,
                      game_day = EXCLUDED.game_day,
                      start_time = EXCLUDED.start_time,
                      home_team = EXCLUDED.home_team,
                      away_team = EXCLUDED.away_team,
                      posteam = EXCLUDED.posteam,
                      defteam = EXCLUDED.defteam,
                      play_type = EXCLUDED.play_type,
                      down = EXCLUDED.down,
                      ydstogo = EXCLUDED.ydstogo,
                      yardline_100 = EXCLUDED.yardline_100,
                      yards_gained = EXCLUDED.yards_gained,
                      passing_yards = EXCLUDED.passing_yards,
                      rushing_yards = EXCLUDED.rushing_yards,
                      receiving_yards = EXCLUDED.receiving_yards,
                      air_yards = EXCLUDED.air_yards,
                      yards_after_catch = EXCLUDED.yards_after_catch,
                      passer_player_id = EXCLUDED.passer_player_id,
                      passer_player_name = EXCLUDED.passer_player_name,
                      receiver_player_id = EXCLUDED.receiver_player_id,
                      receiver_player_name = EXCLUDED.receiver_player_name,
                      rusher_player_id = EXCLUDED.rusher_player_id,
                      rusher_player_name = EXCLUDED.rusher_player_name,
                      complete_pass = EXCLUDED.complete_pass,
                      incomplete_pass = EXCLUDED.incomplete_pass,
                      interception = EXCLUDED.interception,
                      touchdown = EXCLUDED.touchdown,
                      first_down = EXCLUDED.first_down,
                      sack = EXCLUDED.sack,
                      qb_hit = EXCLUDED.qb_hit,
                      fumble = EXCLUDED.fumble,
                      penalty = EXCLUDED.penalty,
                      epa = EXCLUDED.epa,
                      wpa = EXCLUDED.wpa,
                      success = EXCLUDED.success,
                      score_differential = EXCLUDED.score_differential,
                      play_description = EXCLUDED.play_description,
                      shotgun = EXCLUDED.shotgun,
                      no_huddle = EXCLUDED.no_huddle,
                      qb_dropback = EXCLUDED.qb_dropback,
                      pass_location = EXCLUDED.pass_location,
                      run_location = EXCLUDED.run_location,
                      run_gap = EXCLUDED.run_gap,
                      xpass = EXCLUDED.xpass,
                      cp = EXCLUDED.cp,
                      xyac_epa = EXCLUDED.xyac_epa,
                      offense_personnel = EXCLUDED.offense_personnel,
                      defense_personnel = EXCLUDED.defense_personnel,
                      wp = EXCLUDED.wp,
                      vegas_wp = EXCLUDED.vegas_wp,
                      fixed_drive = EXCLUDED.fixed_drive,
                      series = EXCLUDED.series,
                      qtr = EXCLUDED.qtr,
                      half_seconds_remaining = EXCLUDED.half_seconds_remaining,
                      game_seconds_remaining = EXCLUDED.game_seconds_remaining,
                      source = EXCLUDED.source,
                      object_key = EXCLUDED.object_key,
                      updated_at = EXCLUDED.updated_at
                    """
                ),
                {"season": season},
            )

            normalized_for_season = session.execute(
                text("SELECT COUNT(*) FROM nfl_dp_play_by_play WHERE season = :season"),
                {"season": season},
            ).scalar_one()
            normalized_rows += int(normalized_for_season or 0)

            # Keep transactions bounded by season.
            session.commit()

        metrics["rows"]["normalized_rows"] = normalized_rows
        session.execute(
            text(
                """
                UPDATE nfl_dp_ingestion_runs
                SET finished_at = :finished_at,
                    status = :status,
                    metrics = CAST(:metrics AS jsonb)
                WHERE id = :id
                """
            ),
            {
                "id": run_id,
                "finished_at": _now(),
                "status": "success",
                "metrics": json.dumps(metrics),
            },
        )
        session.commit()
        return metrics
    except Exception as exc:
        session.rollback()
        if run_id is not None:
            session.execute(
                text(
                    """
                    UPDATE nfl_dp_ingestion_runs
                    SET finished_at = :finished_at,
                        status = :status,
                        metrics = CAST(:metrics AS jsonb),
                        error_message = :error_message
                    WHERE id = :id
                    """
                ),
                {
                    "id": run_id,
                    "finished_at": _now(),
                    "status": "failed",
                    "metrics": json.dumps(metrics),
                    "error_message": str(exc),
                },
            )
            session.commit()
        raise
    finally:
        session.close()


def materialize_usage_features_from_pbp(
    *, seasons: List[int], replace_existing: bool = False
) -> Dict[str, Any]:
    session = SessionLocal()
    run_id = None
    metrics = {
        "seasons": seasons,
        "replace_existing": replace_existing,
        "rows": {
            "player_usage_rows": 0,
            "team_situational_rows": 0,
        },
    }
    try:
        run_id = session.execute(
            text(
                """
                INSERT INTO nfl_dp_ingestion_runs (source, pipeline, started_at, status, metrics)
                VALUES (:source, :pipeline, :started_at, :status, CAST(:metrics AS jsonb))
                RETURNING id
                """
            ),
            {
                "source": "nflverse",
                "pipeline": "nfl_usage_feature_materialization",
                "started_at": _now(),
                "status": "running",
                "metrics": json.dumps(metrics),
            },
        ).scalar_one()

        for season in seasons:
            if replace_existing:
                session.execute(
                    text("DELETE FROM nfl_dp_player_usage_weekly WHERE season = :season"),
                    {"season": season},
                )
                session.execute(
                    text("DELETE FROM nfl_dp_team_situational_weekly WHERE season = :season"),
                    {"season": season},
                )

            session.execute(
                text(
                    """
                    INSERT INTO nfl_dp_player_usage_weekly (
                      season, week, team, player_id, player_name, position,
                      games_played, involvement_plays, targets, receptions,
                      receiving_yards, air_yards, yards_after_catch,
                      rush_attempts, rush_yards, pass_attempts, pass_yards, pass_touchdowns,
                      red_zone_targets, red_zone_carries, goal_to_go_carries,
                      qb_dropbacks, qb_pressures_taken, touchdowns_scored,
                      first_downs_generated, explosive_plays, success_rate,
                      explosive_play_rate, pressure_rate_allowed, epa_per_involvement, source, updated_at
                    )
                    WITH receiving_events AS (
                      SELECT
                        p.season,
                        p.week,
                        p.game_id,
                        p.posteam AS team,
                        p.receiver_player_id AS player_id,
                        p.receiver_player_name AS player_name,
                        COUNT(*)::int AS involvement_plays,
                        COUNT(*)::int AS targets,
                        SUM(CASE WHEN p.complete_pass THEN 1 ELSE 0 END)::int AS receptions,
                        SUM(COALESCE(p.receiving_yards, 0))::numeric AS receiving_yards,
                        SUM(COALESCE(p.air_yards, 0))::numeric AS air_yards,
                        SUM(COALESCE(p.yards_after_catch, 0))::numeric AS yards_after_catch,
                        0::int AS rush_attempts,
                        0::numeric AS rush_yards,
                        0::int AS pass_attempts,
                        0::numeric AS pass_yards,
                        0::int AS pass_touchdowns,
                        SUM(CASE WHEN p.yardline_100 <= 20 THEN 1 ELSE 0 END)::int AS red_zone_targets,
                        0::int AS red_zone_carries,
                        0::int AS goal_to_go_carries,
                        0::int AS qb_dropbacks,
                        0::int AS qb_pressures_taken,
                        SUM(CASE WHEN p.touchdown THEN 1 ELSE 0 END)::int AS touchdowns_scored,
                        SUM(CASE WHEN p.first_down THEN 1 ELSE 0 END)::int AS first_downs_generated,
                        SUM(CASE WHEN COALESCE(p.receiving_yards, 0) >= 20 THEN 1 ELSE 0 END)::int AS explosive_plays,
                        AVG(CASE WHEN p.success IS NULL THEN NULL ELSE CASE WHEN p.success THEN 1.0 ELSE 0.0 END END)::numeric AS success_rate,
                        SUM(COALESCE(p.epa, 0))::numeric AS epa_sum
                      FROM nfl_dp_play_by_play p
                      WHERE p.season = :season
                        AND p.week IS NOT NULL
                        AND p.receiver_player_id IS NOT NULL
                        AND p.posteam IS NOT NULL
                      GROUP BY p.season, p.week, p.game_id, p.posteam, p.receiver_player_id, p.receiver_player_name
                    ),
                    rushing_events AS (
                      SELECT
                        p.season,
                        p.week,
                        p.game_id,
                        p.posteam AS team,
                        p.rusher_player_id AS player_id,
                        p.rusher_player_name AS player_name,
                        COUNT(*)::int AS involvement_plays,
                        0::int AS targets,
                        0::int AS receptions,
                        0::numeric AS receiving_yards,
                        0::numeric AS air_yards,
                        0::numeric AS yards_after_catch,
                        COUNT(*)::int AS rush_attempts,
                        SUM(COALESCE(p.rushing_yards, 0))::numeric AS rush_yards,
                        0::int AS pass_attempts,
                        0::numeric AS pass_yards,
                        0::int AS pass_touchdowns,
                        0::int AS red_zone_targets,
                        SUM(CASE WHEN p.yardline_100 <= 20 THEN 1 ELSE 0 END)::int AS red_zone_carries,
                        SUM(CASE WHEN p.yardline_100 <= COALESCE(p.ydstogo, 0) THEN 1 ELSE 0 END)::int AS goal_to_go_carries,
                        0::int AS qb_dropbacks,
                        0::int AS qb_pressures_taken,
                        SUM(CASE WHEN p.touchdown THEN 1 ELSE 0 END)::int AS touchdowns_scored,
                        SUM(CASE WHEN p.first_down THEN 1 ELSE 0 END)::int AS first_downs_generated,
                        SUM(CASE WHEN COALESCE(p.rushing_yards, 0) >= 10 THEN 1 ELSE 0 END)::int AS explosive_plays,
                        AVG(CASE WHEN p.success IS NULL THEN NULL ELSE CASE WHEN p.success THEN 1.0 ELSE 0.0 END END)::numeric AS success_rate,
                        SUM(COALESCE(p.epa, 0))::numeric AS epa_sum
                      FROM nfl_dp_play_by_play p
                      WHERE p.season = :season
                        AND p.week IS NOT NULL
                        AND p.rusher_player_id IS NOT NULL
                        AND p.posteam IS NOT NULL
                        AND p.play_type = 'run'
                      GROUP BY p.season, p.week, p.game_id, p.posteam, p.rusher_player_id, p.rusher_player_name
                    ),
                    passing_events AS (
                      SELECT
                        p.season,
                        p.week,
                        p.game_id,
                        p.posteam AS team,
                        p.passer_player_id AS player_id,
                        p.passer_player_name AS player_name,
                        COUNT(*)::int AS involvement_plays,
                        0::int AS targets,
                        0::int AS receptions,
                        0::numeric AS receiving_yards,
                        0::numeric AS air_yards,
                        0::numeric AS yards_after_catch,
                        0::int AS rush_attempts,
                        0::numeric AS rush_yards,
                        COUNT(*)::int AS pass_attempts,
                        SUM(COALESCE(p.passing_yards, 0))::numeric AS pass_yards,
                        SUM(CASE WHEN p.touchdown THEN 1 ELSE 0 END)::int AS pass_touchdowns,
                        0::int AS red_zone_targets,
                        0::int AS red_zone_carries,
                        0::int AS goal_to_go_carries,
                        COUNT(*)::int AS qb_dropbacks,
                        SUM(CASE WHEN p.sack OR p.qb_hit THEN 1 ELSE 0 END)::int AS qb_pressures_taken,
                        SUM(CASE WHEN p.touchdown THEN 1 ELSE 0 END)::int AS touchdowns_scored,
                        SUM(CASE WHEN p.first_down THEN 1 ELSE 0 END)::int AS first_downs_generated,
                        SUM(CASE WHEN COALESCE(p.passing_yards, 0) >= 20 THEN 1 ELSE 0 END)::int AS explosive_plays,
                        AVG(CASE WHEN p.success IS NULL THEN NULL ELSE CASE WHEN p.success THEN 1.0 ELSE 0.0 END END)::numeric AS success_rate,
                        SUM(COALESCE(p.epa, 0))::numeric AS epa_sum
                      FROM nfl_dp_play_by_play p
                      WHERE p.season = :season
                        AND p.week IS NOT NULL
                        AND p.passer_player_id IS NOT NULL
                        AND p.posteam IS NOT NULL
                        AND p.play_type = 'pass'
                      GROUP BY p.season, p.week, p.game_id, p.posteam, p.passer_player_id, p.passer_player_name
                    ),
                    all_events AS (
                      SELECT * FROM receiving_events
                      UNION ALL
                      SELECT * FROM rushing_events
                      UNION ALL
                      SELECT * FROM passing_events
                    ),
                    rolled AS (
                      SELECT
                        season,
                        week,
                        team,
                        player_id,
                        MAX(player_name) AS player_name,
                        COUNT(DISTINCT game_id)::int AS games_played,
                        SUM(involvement_plays)::int AS involvement_plays,
                        SUM(targets)::int AS targets,
                        SUM(receptions)::int AS receptions,
                        SUM(receiving_yards)::numeric AS receiving_yards,
                        SUM(air_yards)::numeric AS air_yards,
                        SUM(yards_after_catch)::numeric AS yards_after_catch,
                        SUM(rush_attempts)::int AS rush_attempts,
                        SUM(rush_yards)::numeric AS rush_yards,
                        SUM(pass_attempts)::int AS pass_attempts,
                        SUM(pass_yards)::numeric AS pass_yards,
                        SUM(pass_touchdowns)::int AS pass_touchdowns,
                        SUM(red_zone_targets)::int AS red_zone_targets,
                        SUM(red_zone_carries)::int AS red_zone_carries,
                        SUM(goal_to_go_carries)::int AS goal_to_go_carries,
                        SUM(qb_dropbacks)::int AS qb_dropbacks,
                        SUM(qb_pressures_taken)::int AS qb_pressures_taken,
                        SUM(touchdowns_scored)::int AS touchdowns_scored,
                        SUM(first_downs_generated)::int AS first_downs_generated,
                        SUM(explosive_plays)::int AS explosive_plays,
                        AVG(success_rate)::numeric AS success_rate,
                        SUM(epa_sum)::numeric AS epa_sum
                      FROM all_events
                      GROUP BY season, week, team, player_id
                    ),
                    roster_dim AS (
                      SELECT DISTINCT ON (season, team, player_id)
                        season, team, player_id, position
                      FROM nfl_dp_rosters
                      ORDER BY season, team, player_id, updated_at DESC
                    )
                    SELECT
                      r.season,
                      r.week,
                      r.team,
                      r.player_id,
                      r.player_name,
                      rd.position,
                      r.games_played,
                      r.involvement_plays,
                      r.targets,
                      r.receptions,
                      r.receiving_yards,
                      r.air_yards,
                      r.yards_after_catch,
                      r.rush_attempts,
                      r.rush_yards,
                      r.pass_attempts,
                      r.pass_yards,
                      r.pass_touchdowns,
                      r.red_zone_targets,
                      r.red_zone_carries,
                      r.goal_to_go_carries,
                      r.qb_dropbacks,
                      r.qb_pressures_taken,
                      r.touchdowns_scored,
                      r.first_downs_generated,
                      r.explosive_plays,
                      r.success_rate,
                      CASE WHEN r.involvement_plays > 0 THEN (r.explosive_plays::numeric / r.involvement_plays::numeric) ELSE NULL END AS explosive_play_rate,
                      CASE WHEN r.qb_dropbacks > 0 THEN (r.qb_pressures_taken::numeric / r.qb_dropbacks::numeric) ELSE NULL END AS pressure_rate_allowed,
                      CASE WHEN r.involvement_plays > 0 THEN (r.epa_sum / r.involvement_plays::numeric) ELSE NULL END AS epa_per_involvement,
                      'pbp_aggregation'::text,
                      NOW()
                    FROM rolled r
                    LEFT JOIN roster_dim rd
                      ON rd.season = r.season AND rd.team = r.team AND rd.player_id = r.player_id
                    ON CONFLICT (season, week, team, player_id) DO UPDATE SET
                      player_name = EXCLUDED.player_name,
                      position = EXCLUDED.position,
                      games_played = EXCLUDED.games_played,
                      involvement_plays = EXCLUDED.involvement_plays,
                      targets = EXCLUDED.targets,
                      receptions = EXCLUDED.receptions,
                      receiving_yards = EXCLUDED.receiving_yards,
                      air_yards = EXCLUDED.air_yards,
                      yards_after_catch = EXCLUDED.yards_after_catch,
                      rush_attempts = EXCLUDED.rush_attempts,
                      rush_yards = EXCLUDED.rush_yards,
                      pass_attempts = EXCLUDED.pass_attempts,
                      pass_yards = EXCLUDED.pass_yards,
                      pass_touchdowns = EXCLUDED.pass_touchdowns,
                      red_zone_targets = EXCLUDED.red_zone_targets,
                      red_zone_carries = EXCLUDED.red_zone_carries,
                      goal_to_go_carries = EXCLUDED.goal_to_go_carries,
                      qb_dropbacks = EXCLUDED.qb_dropbacks,
                      qb_pressures_taken = EXCLUDED.qb_pressures_taken,
                      touchdowns_scored = EXCLUDED.touchdowns_scored,
                      first_downs_generated = EXCLUDED.first_downs_generated,
                      explosive_plays = EXCLUDED.explosive_plays,
                      success_rate = EXCLUDED.success_rate,
                      explosive_play_rate = EXCLUDED.explosive_play_rate,
                      pressure_rate_allowed = EXCLUDED.pressure_rate_allowed,
                      epa_per_involvement = EXCLUDED.epa_per_involvement,
                      source = EXCLUDED.source,
                      updated_at = EXCLUDED.updated_at
                    """
                ),
                {"season": season},
            )

            session.execute(
                text(
                    """
                    INSERT INTO nfl_dp_team_situational_weekly (
                      season, week, team, games_played,
                      offensive_plays, defensive_plays, pass_plays, run_plays,
                      early_down_plays, early_down_pass_plays,
                      third_down_attempts, third_down_conversions,
                      fourth_down_attempts, fourth_down_conversions,
                      red_zone_plays, red_zone_touchdowns,
                      sacks_allowed, qb_hits_allowed, sacks_generated, qb_hits_generated,
                      explosive_pass_plays, explosive_pass_allowed,
                      pass_rate, early_down_pass_rate,
                      third_down_conversion_rate, fourth_down_conversion_rate, red_zone_td_rate,
                      pressure_rate_allowed, pressure_rate_generated,
                      success_rate_offense, success_rate_defense_allowed,
                      epa_per_play_offense, epa_per_play_defense_allowed, source, updated_at
                    )
                    WITH offense AS (
                      SELECT
                        season,
                        week,
                        posteam AS team,
                        COUNT(DISTINCT game_id)::int AS games_played,
                        COUNT(*)::int AS offensive_plays,
                        SUM(CASE WHEN play_type = 'pass' THEN 1 ELSE 0 END)::int AS pass_plays,
                        SUM(CASE WHEN play_type = 'run' THEN 1 ELSE 0 END)::int AS run_plays,
                        SUM(CASE WHEN down IN (1,2) THEN 1 ELSE 0 END)::int AS early_down_plays,
                        SUM(CASE WHEN down IN (1,2) AND play_type = 'pass' THEN 1 ELSE 0 END)::int AS early_down_pass_plays,
                        SUM(CASE WHEN down = 3 THEN 1 ELSE 0 END)::int AS third_down_attempts,
                        SUM(CASE WHEN down = 3 AND first_down THEN 1 ELSE 0 END)::int AS third_down_conversions,
                        SUM(CASE WHEN down = 4 THEN 1 ELSE 0 END)::int AS fourth_down_attempts,
                        SUM(CASE WHEN down = 4 AND first_down THEN 1 ELSE 0 END)::int AS fourth_down_conversions,
                        SUM(CASE WHEN yardline_100 <= 20 THEN 1 ELSE 0 END)::int AS red_zone_plays,
                        SUM(CASE WHEN yardline_100 <= 20 AND touchdown THEN 1 ELSE 0 END)::int AS red_zone_touchdowns,
                        SUM(CASE WHEN play_type = 'pass' AND sack THEN 1 ELSE 0 END)::int AS sacks_allowed,
                        SUM(CASE WHEN play_type = 'pass' AND qb_hit THEN 1 ELSE 0 END)::int AS qb_hits_allowed,
                        SUM(CASE WHEN play_type = 'pass' AND COALESCE(passing_yards, 0) >= 20 THEN 1 ELSE 0 END)::int AS explosive_pass_plays,
                        AVG(CASE WHEN success IS NULL THEN NULL ELSE CASE WHEN success THEN 1.0 ELSE 0.0 END END)::numeric AS success_rate_offense,
                        AVG(epa)::numeric AS epa_per_play_offense,
                        SUM(CASE WHEN play_type = 'pass' THEN CASE WHEN sack OR qb_hit THEN 1 ELSE 0 END ELSE 0 END)::int AS offensive_pressures_allowed,
                        SUM(CASE WHEN play_type = 'pass' THEN 1 ELSE 0 END)::int AS offensive_dropbacks
                      FROM nfl_dp_play_by_play
                      WHERE season = :season
                        AND week IS NOT NULL
                        AND posteam IS NOT NULL
                        AND play_type IN ('pass', 'run')
                      GROUP BY season, week, posteam
                    ),
                    defense AS (
                      SELECT
                        season,
                        week,
                        defteam AS team,
                        COUNT(*)::int AS defensive_plays,
                        SUM(CASE WHEN play_type = 'pass' AND sack THEN 1 ELSE 0 END)::int AS sacks_generated,
                        SUM(CASE WHEN play_type = 'pass' AND qb_hit THEN 1 ELSE 0 END)::int AS qb_hits_generated,
                        SUM(CASE WHEN play_type = 'pass' AND COALESCE(passing_yards, 0) >= 20 THEN 1 ELSE 0 END)::int AS explosive_pass_allowed,
                        AVG(CASE WHEN success IS NULL THEN NULL ELSE CASE WHEN success THEN 1.0 ELSE 0.0 END END)::numeric AS success_rate_defense_allowed,
                        AVG(epa)::numeric AS epa_per_play_defense_allowed,
                        SUM(CASE WHEN play_type = 'pass' THEN CASE WHEN sack OR qb_hit THEN 1 ELSE 0 END ELSE 0 END)::int AS defensive_pressures_generated,
                        SUM(CASE WHEN play_type = 'pass' THEN 1 ELSE 0 END)::int AS defensive_dropbacks_faced
                      FROM nfl_dp_play_by_play
                      WHERE season = :season
                        AND week IS NOT NULL
                        AND defteam IS NOT NULL
                        AND play_type IN ('pass', 'run')
                      GROUP BY season, week, defteam
                    )
                    SELECT
                      o.season,
                      o.week,
                      o.team,
                      o.games_played,
                      o.offensive_plays,
                      COALESCE(d.defensive_plays, 0) AS defensive_plays,
                      o.pass_plays,
                      o.run_plays,
                      o.early_down_plays,
                      o.early_down_pass_plays,
                      o.third_down_attempts,
                      o.third_down_conversions,
                      o.fourth_down_attempts,
                      o.fourth_down_conversions,
                      o.red_zone_plays,
                      o.red_zone_touchdowns,
                      o.sacks_allowed,
                      o.qb_hits_allowed,
                      COALESCE(d.sacks_generated, 0) AS sacks_generated,
                      COALESCE(d.qb_hits_generated, 0) AS qb_hits_generated,
                      o.explosive_pass_plays,
                      COALESCE(d.explosive_pass_allowed, 0) AS explosive_pass_allowed,
                      CASE WHEN o.offensive_plays > 0 THEN (o.pass_plays::numeric / o.offensive_plays::numeric) ELSE NULL END AS pass_rate,
                      CASE WHEN o.early_down_plays > 0 THEN (o.early_down_pass_plays::numeric / o.early_down_plays::numeric) ELSE NULL END AS early_down_pass_rate,
                      CASE WHEN o.third_down_attempts > 0 THEN (o.third_down_conversions::numeric / o.third_down_attempts::numeric) ELSE NULL END AS third_down_conversion_rate,
                      CASE WHEN o.fourth_down_attempts > 0 THEN (o.fourth_down_conversions::numeric / o.fourth_down_attempts::numeric) ELSE NULL END AS fourth_down_conversion_rate,
                      CASE WHEN o.red_zone_plays > 0 THEN (o.red_zone_touchdowns::numeric / o.red_zone_plays::numeric) ELSE NULL END AS red_zone_td_rate,
                      CASE WHEN o.offensive_dropbacks > 0 THEN (o.offensive_pressures_allowed::numeric / o.offensive_dropbacks::numeric) ELSE NULL END AS pressure_rate_allowed,
                      CASE WHEN COALESCE(d.defensive_dropbacks_faced, 0) > 0 THEN (COALESCE(d.defensive_pressures_generated, 0)::numeric / d.defensive_dropbacks_faced::numeric) ELSE NULL END AS pressure_rate_generated,
                      o.success_rate_offense,
                      d.success_rate_defense_allowed,
                      o.epa_per_play_offense,
                      d.epa_per_play_defense_allowed,
                      'nflverse'::text,
                      NOW()
                    FROM offense o
                    LEFT JOIN defense d
                      ON d.season = o.season AND d.week = o.week AND d.team = o.team
                    ON CONFLICT (season, week, team) DO UPDATE SET
                      games_played = EXCLUDED.games_played,
                      offensive_plays = EXCLUDED.offensive_plays,
                      defensive_plays = EXCLUDED.defensive_plays,
                      pass_plays = EXCLUDED.pass_plays,
                      run_plays = EXCLUDED.run_plays,
                      early_down_plays = EXCLUDED.early_down_plays,
                      early_down_pass_plays = EXCLUDED.early_down_pass_plays,
                      third_down_attempts = EXCLUDED.third_down_attempts,
                      third_down_conversions = EXCLUDED.third_down_conversions,
                      fourth_down_attempts = EXCLUDED.fourth_down_attempts,
                      fourth_down_conversions = EXCLUDED.fourth_down_conversions,
                      red_zone_plays = EXCLUDED.red_zone_plays,
                      red_zone_touchdowns = EXCLUDED.red_zone_touchdowns,
                      sacks_allowed = EXCLUDED.sacks_allowed,
                      qb_hits_allowed = EXCLUDED.qb_hits_allowed,
                      sacks_generated = EXCLUDED.sacks_generated,
                      qb_hits_generated = EXCLUDED.qb_hits_generated,
                      explosive_pass_plays = EXCLUDED.explosive_pass_plays,
                      explosive_pass_allowed = EXCLUDED.explosive_pass_allowed,
                      pass_rate = EXCLUDED.pass_rate,
                      early_down_pass_rate = EXCLUDED.early_down_pass_rate,
                      third_down_conversion_rate = EXCLUDED.third_down_conversion_rate,
                      fourth_down_conversion_rate = EXCLUDED.fourth_down_conversion_rate,
                      red_zone_td_rate = EXCLUDED.red_zone_td_rate,
                      pressure_rate_allowed = EXCLUDED.pressure_rate_allowed,
                      pressure_rate_generated = EXCLUDED.pressure_rate_generated,
                      success_rate_offense = EXCLUDED.success_rate_offense,
                      success_rate_defense_allowed = EXCLUDED.success_rate_defense_allowed,
                      epa_per_play_offense = EXCLUDED.epa_per_play_offense,
                      epa_per_play_defense_allowed = EXCLUDED.epa_per_play_defense_allowed,
                      source = EXCLUDED.source,
                      updated_at = EXCLUDED.updated_at
                    WHERE nfl_dp_team_situational_weekly.source <> 'nfl_com'
                    """
                ),
                {"season": season},
            )

            player_rows = session.execute(
                text("SELECT COUNT(*) FROM nfl_dp_player_usage_weekly WHERE season = :season"),
                {"season": season},
            ).scalar_one()
            team_rows = session.execute(
                text("SELECT COUNT(*) FROM nfl_dp_team_situational_weekly WHERE season = :season"),
                {"season": season},
            ).scalar_one()
            metrics["rows"]["player_usage_rows"] += int(player_rows or 0)
            metrics["rows"]["team_situational_rows"] += int(team_rows or 0)

            session.commit()

        session.execute(
            text(
                """
                UPDATE nfl_dp_ingestion_runs
                SET finished_at = :finished_at,
                    status = :status,
                    metrics = CAST(:metrics AS jsonb)
                WHERE id = :id
                """
            ),
            {
                "id": run_id,
                "finished_at": _now(),
                "status": "success",
                "metrics": json.dumps(metrics),
            },
        )
        session.commit()
        return metrics
    except Exception as exc:
        session.rollback()
        if run_id is not None:
            session.execute(
                text(
                    """
                    UPDATE nfl_dp_ingestion_runs
                    SET finished_at = :finished_at,
                        status = :status,
                        metrics = CAST(:metrics AS jsonb),
                        error_message = :error_message
                    WHERE id = :id
                    """
                ),
                {
                    "id": run_id,
                    "finished_at": _now(),
                    "status": "failed",
                    "metrics": json.dumps(metrics),
                    "error_message": str(exc),
                },
            )
            session.commit()
        raise
    finally:
        session.close()


def materialize_matchup_features_from_usage(
    *, seasons: List[int], replace_existing: bool = False
) -> Dict[str, Any]:
    session = SessionLocal()
    run_id = None
    metrics = {
        "seasons": seasons,
        "replace_existing": replace_existing,
        "rows": {
            "team_rolling_rows": 0,
            "matchup_rows": 0,
        },
    }
    try:
        run_id = session.execute(
            text(
                """
                INSERT INTO nfl_dp_ingestion_runs (source, pipeline, started_at, status, metrics)
                VALUES (:source, :pipeline, :started_at, :status, CAST(:metrics AS jsonb))
                RETURNING id
                """
            ),
            {
                "source": "nflverse",
                "pipeline": "nfl_matchup_feature_materialization",
                "started_at": _now(),
                "status": "running",
                "metrics": json.dumps(metrics),
            },
        ).scalar_one()

        for season in seasons:
            if replace_existing:
                session.execute(
                    text("DELETE FROM nfl_dp_matchup_features_weekly WHERE season = :season"),
                    {"season": season},
                )
                session.execute(
                    text("DELETE FROM nfl_dp_team_rolling_features_weekly WHERE season = :season"),
                    {"season": season},
                )

            session.execute(
                text(
                    """
                    INSERT INTO nfl_dp_team_rolling_features_weekly (
                      season, week, team,
                      games_in_window_3, games_in_window_5,
                      off_epa_per_play_3g, off_epa_per_play_5g,
                      def_epa_allowed_per_play_3g, def_epa_allowed_per_play_5g,
                      pressure_rate_allowed_3g, pressure_rate_allowed_5g,
                      pressure_rate_generated_3g, pressure_rate_generated_5g,
                      pass_rate_3g, pass_rate_5g,
                      early_down_pass_rate_3g, early_down_pass_rate_5g,
                      red_zone_td_rate_3g, red_zone_td_rate_5g,
                      success_rate_offense_3g, success_rate_offense_5g,
                      success_rate_defense_allowed_3g, success_rate_defense_allowed_5g,
                      updated_at
                    )
                    WITH base AS (
                      SELECT
                        season,
                        week,
                        team,
                        epa_per_play_offense,
                        epa_per_play_defense_allowed,
                        pressure_rate_allowed,
                        pressure_rate_generated,
                        pass_rate,
                        early_down_pass_rate,
                        red_zone_td_rate,
                        success_rate_offense,
                        success_rate_defense_allowed
                      FROM nfl_dp_team_situational_weekly
                      WHERE season = :season
                    ),
                    rolled AS (
                      SELECT
                        season,
                        week,
                        team,
                        COUNT(*) OVER (
                          PARTITION BY team
                          ORDER BY season, week
                          ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
                        )::int AS games_in_window_3,
                        COUNT(*) OVER (
                          PARTITION BY team
                          ORDER BY season, week
                          ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
                        )::int AS games_in_window_5,
                        AVG(epa_per_play_offense) OVER (
                          PARTITION BY team
                          ORDER BY season, week
                          ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
                        )::numeric AS off_epa_per_play_3g,
                        AVG(epa_per_play_offense) OVER (
                          PARTITION BY team
                          ORDER BY season, week
                          ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
                        )::numeric AS off_epa_per_play_5g,
                        AVG(epa_per_play_defense_allowed) OVER (
                          PARTITION BY team
                          ORDER BY season, week
                          ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
                        )::numeric AS def_epa_allowed_per_play_3g,
                        AVG(epa_per_play_defense_allowed) OVER (
                          PARTITION BY team
                          ORDER BY season, week
                          ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
                        )::numeric AS def_epa_allowed_per_play_5g,
                        AVG(pressure_rate_allowed) OVER (
                          PARTITION BY team
                          ORDER BY season, week
                          ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
                        )::numeric AS pressure_rate_allowed_3g,
                        AVG(pressure_rate_allowed) OVER (
                          PARTITION BY team
                          ORDER BY season, week
                          ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
                        )::numeric AS pressure_rate_allowed_5g,
                        AVG(pressure_rate_generated) OVER (
                          PARTITION BY team
                          ORDER BY season, week
                          ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
                        )::numeric AS pressure_rate_generated_3g,
                        AVG(pressure_rate_generated) OVER (
                          PARTITION BY team
                          ORDER BY season, week
                          ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
                        )::numeric AS pressure_rate_generated_5g,
                        AVG(pass_rate) OVER (
                          PARTITION BY team
                          ORDER BY season, week
                          ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
                        )::numeric AS pass_rate_3g,
                        AVG(pass_rate) OVER (
                          PARTITION BY team
                          ORDER BY season, week
                          ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
                        )::numeric AS pass_rate_5g,
                        AVG(early_down_pass_rate) OVER (
                          PARTITION BY team
                          ORDER BY season, week
                          ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
                        )::numeric AS early_down_pass_rate_3g,
                        AVG(early_down_pass_rate) OVER (
                          PARTITION BY team
                          ORDER BY season, week
                          ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
                        )::numeric AS early_down_pass_rate_5g,
                        AVG(red_zone_td_rate) OVER (
                          PARTITION BY team
                          ORDER BY season, week
                          ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
                        )::numeric AS red_zone_td_rate_3g,
                        AVG(red_zone_td_rate) OVER (
                          PARTITION BY team
                          ORDER BY season, week
                          ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
                        )::numeric AS red_zone_td_rate_5g,
                        AVG(success_rate_offense) OVER (
                          PARTITION BY team
                          ORDER BY season, week
                          ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
                        )::numeric AS success_rate_offense_3g,
                        AVG(success_rate_offense) OVER (
                          PARTITION BY team
                          ORDER BY season, week
                          ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
                        )::numeric AS success_rate_offense_5g,
                        AVG(success_rate_defense_allowed) OVER (
                          PARTITION BY team
                          ORDER BY season, week
                          ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
                        )::numeric AS success_rate_defense_allowed_3g,
                        AVG(success_rate_defense_allowed) OVER (
                          PARTITION BY team
                          ORDER BY season, week
                          ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
                        )::numeric AS success_rate_defense_allowed_5g
                      FROM base
                    )
                    SELECT
                      season, week, team,
                      games_in_window_3, games_in_window_5,
                      off_epa_per_play_3g, off_epa_per_play_5g,
                      def_epa_allowed_per_play_3g, def_epa_allowed_per_play_5g,
                      pressure_rate_allowed_3g, pressure_rate_allowed_5g,
                      pressure_rate_generated_3g, pressure_rate_generated_5g,
                      pass_rate_3g, pass_rate_5g,
                      early_down_pass_rate_3g, early_down_pass_rate_5g,
                      red_zone_td_rate_3g, red_zone_td_rate_5g,
                      success_rate_offense_3g, success_rate_offense_5g,
                      success_rate_defense_allowed_3g, success_rate_defense_allowed_5g,
                      NOW()
                    FROM rolled
                    ON CONFLICT (season, week, team) DO UPDATE SET
                      games_in_window_3 = EXCLUDED.games_in_window_3,
                      games_in_window_5 = EXCLUDED.games_in_window_5,
                      off_epa_per_play_3g = EXCLUDED.off_epa_per_play_3g,
                      off_epa_per_play_5g = EXCLUDED.off_epa_per_play_5g,
                      def_epa_allowed_per_play_3g = EXCLUDED.def_epa_allowed_per_play_3g,
                      def_epa_allowed_per_play_5g = EXCLUDED.def_epa_allowed_per_play_5g,
                      pressure_rate_allowed_3g = EXCLUDED.pressure_rate_allowed_3g,
                      pressure_rate_allowed_5g = EXCLUDED.pressure_rate_allowed_5g,
                      pressure_rate_generated_3g = EXCLUDED.pressure_rate_generated_3g,
                      pressure_rate_generated_5g = EXCLUDED.pressure_rate_generated_5g,
                      pass_rate_3g = EXCLUDED.pass_rate_3g,
                      pass_rate_5g = EXCLUDED.pass_rate_5g,
                      early_down_pass_rate_3g = EXCLUDED.early_down_pass_rate_3g,
                      early_down_pass_rate_5g = EXCLUDED.early_down_pass_rate_5g,
                      red_zone_td_rate_3g = EXCLUDED.red_zone_td_rate_3g,
                      red_zone_td_rate_5g = EXCLUDED.red_zone_td_rate_5g,
                      success_rate_offense_3g = EXCLUDED.success_rate_offense_3g,
                      success_rate_offense_5g = EXCLUDED.success_rate_offense_5g,
                      success_rate_defense_allowed_3g = EXCLUDED.success_rate_defense_allowed_3g,
                      success_rate_defense_allowed_5g = EXCLUDED.success_rate_defense_allowed_5g,
                      updated_at = EXCLUDED.updated_at
                    """
                ),
                {"season": season},
            )

            session.execute(
                text(
                    """
                    INSERT INTO nfl_dp_matchup_features_weekly (
                      season, week, game_id, game_date, home_team, away_team,
                      home_off_epa_5g, away_off_epa_5g,
                      home_def_epa_allowed_5g, away_def_epa_allowed_5g,
                      home_pressure_allowed_5g, away_pressure_allowed_5g,
                      home_pressure_generated_5g, away_pressure_generated_5g,
                      home_pass_rate_5g, away_pass_rate_5g,
                      home_early_down_pass_rate_5g, away_early_down_pass_rate_5g,
                      home_red_zone_td_rate_5g, away_red_zone_td_rate_5g,
                      home_success_offense_5g, away_success_offense_5g,
                      home_success_defense_allowed_5g, away_success_defense_allowed_5g,
                      diff_off_epa_5g, diff_def_epa_allowed_5g,
                      diff_pressure_generated_5g, diff_pressure_allowed_5g,
                      diff_red_zone_td_rate_5g, updated_at
                    )
                    SELECT
                      s.season,
                      s.week,
                      s.game_id,
                      s.game_date,
                      s.home_team,
                      s.away_team,
                      h.off_epa_per_play_5g AS home_off_epa_5g,
                      a.off_epa_per_play_5g AS away_off_epa_5g,
                      h.def_epa_allowed_per_play_5g AS home_def_epa_allowed_5g,
                      a.def_epa_allowed_per_play_5g AS away_def_epa_allowed_5g,
                      h.pressure_rate_allowed_5g AS home_pressure_allowed_5g,
                      a.pressure_rate_allowed_5g AS away_pressure_allowed_5g,
                      h.pressure_rate_generated_5g AS home_pressure_generated_5g,
                      a.pressure_rate_generated_5g AS away_pressure_generated_5g,
                      h.pass_rate_5g AS home_pass_rate_5g,
                      a.pass_rate_5g AS away_pass_rate_5g,
                      h.early_down_pass_rate_5g AS home_early_down_pass_rate_5g,
                      a.early_down_pass_rate_5g AS away_early_down_pass_rate_5g,
                      h.red_zone_td_rate_5g AS home_red_zone_td_rate_5g,
                      a.red_zone_td_rate_5g AS away_red_zone_td_rate_5g,
                      h.success_rate_offense_5g AS home_success_offense_5g,
                      a.success_rate_offense_5g AS away_success_offense_5g,
                      h.success_rate_defense_allowed_5g AS home_success_defense_allowed_5g,
                      a.success_rate_defense_allowed_5g AS away_success_defense_allowed_5g,
                      (h.off_epa_per_play_5g - a.off_epa_per_play_5g) AS diff_off_epa_5g,
                      (a.def_epa_allowed_per_play_5g - h.def_epa_allowed_per_play_5g) AS diff_def_epa_allowed_5g,
                      (h.pressure_rate_generated_5g - a.pressure_rate_generated_5g) AS diff_pressure_generated_5g,
                      (a.pressure_rate_allowed_5g - h.pressure_rate_allowed_5g) AS diff_pressure_allowed_5g,
                      (h.red_zone_td_rate_5g - a.red_zone_td_rate_5g) AS diff_red_zone_td_rate_5g,
                      NOW()
                    FROM nfl_dp_schedules s
                    LEFT JOIN nfl_dp_team_rolling_features_weekly h
                      ON h.season = s.season AND h.week = s.week AND h.team = s.home_team
                    LEFT JOIN nfl_dp_team_rolling_features_weekly a
                      ON a.season = s.season AND a.week = s.week AND a.team = s.away_team
                    WHERE s.season = :season
                    ON CONFLICT (season, week, game_id) DO UPDATE SET
                      game_date = EXCLUDED.game_date,
                      home_team = EXCLUDED.home_team,
                      away_team = EXCLUDED.away_team,
                      home_off_epa_5g = EXCLUDED.home_off_epa_5g,
                      away_off_epa_5g = EXCLUDED.away_off_epa_5g,
                      home_def_epa_allowed_5g = EXCLUDED.home_def_epa_allowed_5g,
                      away_def_epa_allowed_5g = EXCLUDED.away_def_epa_allowed_5g,
                      home_pressure_allowed_5g = EXCLUDED.home_pressure_allowed_5g,
                      away_pressure_allowed_5g = EXCLUDED.away_pressure_allowed_5g,
                      home_pressure_generated_5g = EXCLUDED.home_pressure_generated_5g,
                      away_pressure_generated_5g = EXCLUDED.away_pressure_generated_5g,
                      home_pass_rate_5g = EXCLUDED.home_pass_rate_5g,
                      away_pass_rate_5g = EXCLUDED.away_pass_rate_5g,
                      home_early_down_pass_rate_5g = EXCLUDED.home_early_down_pass_rate_5g,
                      away_early_down_pass_rate_5g = EXCLUDED.away_early_down_pass_rate_5g,
                      home_red_zone_td_rate_5g = EXCLUDED.home_red_zone_td_rate_5g,
                      away_red_zone_td_rate_5g = EXCLUDED.away_red_zone_td_rate_5g,
                      home_success_offense_5g = EXCLUDED.home_success_offense_5g,
                      away_success_offense_5g = EXCLUDED.away_success_offense_5g,
                      home_success_defense_allowed_5g = EXCLUDED.home_success_defense_allowed_5g,
                      away_success_defense_allowed_5g = EXCLUDED.away_success_defense_allowed_5g,
                      diff_off_epa_5g = EXCLUDED.diff_off_epa_5g,
                      diff_def_epa_allowed_5g = EXCLUDED.diff_def_epa_allowed_5g,
                      diff_pressure_generated_5g = EXCLUDED.diff_pressure_generated_5g,
                      diff_pressure_allowed_5g = EXCLUDED.diff_pressure_allowed_5g,
                      diff_red_zone_td_rate_5g = EXCLUDED.diff_red_zone_td_rate_5g,
                      updated_at = EXCLUDED.updated_at
                    """
                ),
                {"season": season},
            )

            rolling_rows = session.execute(
                text("SELECT COUNT(*) FROM nfl_dp_team_rolling_features_weekly WHERE season = :season"),
                {"season": season},
            ).scalar_one()
            matchup_rows = session.execute(
                text("SELECT COUNT(*) FROM nfl_dp_matchup_features_weekly WHERE season = :season"),
                {"season": season},
            ).scalar_one()
            metrics["rows"]["team_rolling_rows"] += int(rolling_rows or 0)
            metrics["rows"]["matchup_rows"] += int(matchup_rows or 0)

            session.commit()

        session.execute(
            text(
                """
                UPDATE nfl_dp_ingestion_runs
                SET finished_at = :finished_at,
                    status = :status,
                    metrics = CAST(:metrics AS jsonb)
                WHERE id = :id
                """
            ),
            {
                "id": run_id,
                "finished_at": _now(),
                "status": "success",
                "metrics": json.dumps(metrics),
            },
        )
        session.commit()
        return metrics
    except Exception as exc:
        session.rollback()
        if run_id is not None:
            session.execute(
                text(
                    """
                    UPDATE nfl_dp_ingestion_runs
                    SET finished_at = :finished_at,
                        status = :status,
                        metrics = CAST(:metrics AS jsonb),
                        error_message = :error_message
                    WHERE id = :id
                    """
                ),
                {
                    "id": run_id,
                    "finished_at": _now(),
                    "status": "failed",
                    "metrics": json.dumps(metrics),
                    "error_message": str(exc),
                },
            )
            session.commit()
        raise
    finally:
        session.close()


def materialize_standings_weekly(
    *, seasons: List[int], week: int | None = None, replace_existing: bool = False
) -> Dict[str, Any]:
    session = SessionLocal()
    run_id = None
    metrics = {
        "seasons": seasons,
        "week": week,
        "replace_existing": replace_existing,
        "rows": {"standings_rows": 0},
    }
    try:
        run_id = session.execute(
            text(
                """
                INSERT INTO nfl_dp_ingestion_runs (source, pipeline, started_at, status, metrics)
                VALUES (:source, :pipeline, :started_at, :status, CAST(:metrics AS jsonb))
                RETURNING id
                """
            ),
            {
                "source": "nflverse",
                "pipeline": "nfl_standings_weekly_materialization",
                "started_at": _now(),
                "status": "running",
                "metrics": json.dumps(metrics),
            },
        ).scalar_one()

        for season in seasons:
            if replace_existing:
                session.execute(
                    text(
                        """
                        DELETE FROM nfl_dp_standings_weekly
                        WHERE season = :season
                          AND (CAST(:week AS int) IS NULL OR week = CAST(:week AS int))
                        """
                    ),
                    {"season": season, "week": week},
                )
            rows = session.execute(
                text(
                    """
                    SELECT season, week, home_team, away_team, home_score, away_score
                    FROM nfl_dp_schedules
                    WHERE season = :season
                      AND week IS NOT NULL
                      AND (CAST(:week AS int) IS NULL OR week <= CAST(:week AS int))
                    ORDER BY week, game_id
                    """
                ),
                {"season": season, "week": week},
            ).fetchall()
            standings_rows = build_standings_rows([dict(r._mapping) for r in rows])
            for item in standings_rows:
                session.execute(
                    text(
                        """
                        INSERT INTO nfl_dp_standings_weekly (
                          season, week, team,
                          wins, losses, ties,
                          points_for, points_against, point_diff, win_pct,
                          conference, division,
                          conference_wins, conference_losses, conference_ties, conference_pct,
                          division_wins, division_losses, division_ties, division_pct,
                          source, updated_at
                        ) VALUES (
                          :season, :week, :team,
                          :wins, :losses, :ties,
                          :points_for, :points_against, :point_diff, :win_pct,
                          :conference, :division,
                          :conference_wins, :conference_losses, :conference_ties, :conference_pct,
                          :division_wins, :division_losses, :division_ties, :division_pct,
                          :source, NOW()
                        )
                        ON CONFLICT (season, week, team) DO UPDATE SET
                          wins = EXCLUDED.wins,
                          losses = EXCLUDED.losses,
                          ties = EXCLUDED.ties,
                          points_for = EXCLUDED.points_for,
                          points_against = EXCLUDED.points_against,
                          point_diff = EXCLUDED.point_diff,
                          win_pct = EXCLUDED.win_pct,
                          conference = EXCLUDED.conference,
                          division = EXCLUDED.division,
                          conference_wins = EXCLUDED.conference_wins,
                          conference_losses = EXCLUDED.conference_losses,
                          conference_ties = EXCLUDED.conference_ties,
                          conference_pct = EXCLUDED.conference_pct,
                          division_wins = EXCLUDED.division_wins,
                          division_losses = EXCLUDED.division_losses,
                          division_ties = EXCLUDED.division_ties,
                          division_pct = EXCLUDED.division_pct,
                          source = EXCLUDED.source,
                          updated_at = EXCLUDED.updated_at
                        WHERE nfl_dp_standings_weekly.source <> 'nfl_com'
                        """
                    ),
                    {
                        **item,
                        "source": "nfl_dp_schedules_derived",
                    },
                )

            rows_for_season = session.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM nfl_dp_standings_weekly
                    WHERE season = :season
                      AND (CAST(:week AS int) IS NULL OR week = CAST(:week AS int))
                    """
                ),
                {"season": season, "week": week},
            ).scalar_one()
            metrics["rows"]["standings_rows"] += int(rows_for_season or 0)
            session.commit()

        session.execute(
            text(
                """
                UPDATE nfl_dp_ingestion_runs
                SET finished_at = :finished_at,
                    status = :status,
                    metrics = CAST(:metrics AS jsonb)
                WHERE id = :id
                """
            ),
            {
                "id": run_id,
                "finished_at": _now(),
                "status": "success",
                "metrics": json.dumps(metrics),
            },
        )
        session.commit()
        return metrics
    except Exception as exc:
        session.rollback()
        if run_id is not None:
            session.execute(
                text(
                    """
                    UPDATE nfl_dp_ingestion_runs
                    SET finished_at = :finished_at,
                        status = :status,
                        metrics = CAST(:metrics AS jsonb),
                        error_message = :error_message
                    WHERE id = :id
                    """
                ),
                {
                    "id": run_id,
                    "finished_at": _now(),
                    "status": "failed",
                    "metrics": json.dumps(metrics),
                    "error_message": str(exc),
                },
            )
            session.commit()
        raise
    finally:
        session.close()


def materialize_depth_chart_weekly(
    *, seasons: List[int], week: int | None = None, replace_existing: bool = False
) -> Dict[str, Any]:
    session = SessionLocal()
    run_id = None
    metrics = {
        "seasons": seasons,
        "week": week,
        "replace_existing": replace_existing,
        "rows": {"depth_chart_rows": 0},
    }
    try:
        run_id = session.execute(
            text(
                """
                INSERT INTO nfl_dp_ingestion_runs (source, pipeline, started_at, status, metrics)
                VALUES (:source, :pipeline, :started_at, :status, CAST(:metrics AS jsonb))
                RETURNING id
                """
            ),
            {
                "source": "nflverse",
                "pipeline": "nfl_depth_chart_weekly_materialization",
                "started_at": _now(),
                "status": "running",
                "metrics": json.dumps(metrics),
            },
        ).scalar_one()

        for season in seasons:
            weeks = [week] if week is not None else [
                int(w)
                for w in session.execute(
                    text(
                        """
                        SELECT DISTINCT week
                        FROM nfl_dp_player_usage_weekly
                        WHERE season = :season
                          AND week IS NOT NULL
                        ORDER BY week
                        """
                    ),
                    {"season": season},
                ).scalars().all()
            ]
            if not weeks:
                continue

            roster_rows = [
                dict(r._mapping)
                for r in session.execute(
                    text(
                        """
                        SELECT season, team, player_id, player_name, position
                        FROM nfl_dp_rosters
                        WHERE season = :season
                        """
                    ),
                    {"season": season},
                ).fetchall()
            ]

            for target_week in weeks:
                if replace_existing:
                    session.execute(
                        text(
                            """
                            DELETE FROM nfl_dp_depth_chart_weekly
                            WHERE season = :season
                              AND week = :week
                            """
                        ),
                        {"season": season, "week": target_week},
                    )
                usage_rows = [
                    dict(r._mapping)
                    for r in session.execute(
                        text(
                            """
                            SELECT
                              team,
                              player_id,
                              SUM(involvement_plays)::int AS involvement,
                              SUM(targets)::int AS targets,
                              SUM(rush_attempts)::int AS rush_attempts,
                              SUM(pass_attempts)::int AS pass_attempts,
                              COUNT(DISTINCT week)::int AS active_weeks,
                              MAX(week)::int AS latest_week
                            FROM nfl_dp_player_usage_weekly
                            WHERE season = :season
                              AND week BETWEEN GREATEST(1, :week - 2) AND :week
                            GROUP BY team, player_id
                            """
                        ),
                        {"season": season, "week": target_week},
                    ).fetchall()
                ]
                injury_rows = [
                    dict(r._mapping)
                    for r in session.execute(
                        text(
                            """
                            SELECT team, player_id, player_name, report_status, practice_status
                            FROM nfl_dp_injuries
                            WHERE season = :season
                              AND week = :week
                            """
                        ),
                        {"season": season, "week": target_week},
                    ).fetchall()
                ]
                inferred_rows = infer_depth_chart_rows(
                    season=season,
                    week=target_week,
                    roster_rows=roster_rows,
                    usage_rows=usage_rows,
                    injury_rows=injury_rows,
                )
                for item in inferred_rows:
                    session.execute(
                        text(
                            """
                            INSERT INTO nfl_dp_depth_chart_weekly (
                              season, week, team, position, depth_order, depth_slot,
                              player_uid, player_id, player_name, role_confidence, inferred_source, updated_at
                            ) VALUES (
                              :season, :week, :team, :position, :depth_order, :depth_slot,
                              :player_uid, :player_id, :player_name, :role_confidence, :inferred_source, NOW()
                            )
                            ON CONFLICT (season, week, team, position, depth_order) DO UPDATE SET
                              depth_slot = EXCLUDED.depth_slot,
                              player_uid = EXCLUDED.player_uid,
                              player_id = EXCLUDED.player_id,
                              player_name = EXCLUDED.player_name,
                              role_confidence = EXCLUDED.role_confidence,
                              inferred_source = EXCLUDED.inferred_source,
                              updated_at = EXCLUDED.updated_at
                            """
                        ),
                        item,
                    )
                session.commit()

            rows_for_season = session.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM nfl_dp_depth_chart_weekly
                    WHERE season = :season
                      AND (CAST(:week AS int) IS NULL OR week = CAST(:week AS int))
                    """
                ),
                {"season": season, "week": week},
            ).scalar_one()
            metrics["rows"]["depth_chart_rows"] += int(rows_for_season or 0)

        session.execute(
            text(
                """
                UPDATE nfl_dp_ingestion_runs
                SET finished_at = :finished_at,
                    status = :status,
                    metrics = CAST(:metrics AS jsonb)
                WHERE id = :id
                """
            ),
            {
                "id": run_id,
                "finished_at": _now(),
                "status": "success",
                "metrics": json.dumps(metrics),
            },
        )
        session.commit()
        return metrics
    except Exception as exc:
        session.rollback()
        if run_id is not None:
            session.execute(
                text(
                    """
                    UPDATE nfl_dp_ingestion_runs
                    SET finished_at = :finished_at,
                        status = :status,
                        metrics = CAST(:metrics AS jsonb),
                        error_message = :error_message
                    WHERE id = :id
                    """
                ),
                {
                    "id": run_id,
                    "finished_at": _now(),
                    "status": "failed",
                    "metrics": json.dumps(metrics),
                    "error_message": str(exc),
                },
            )
            session.commit()
        raise
    finally:
        session.close()


def ingest_nflverse_snapshot(*, seasons: List[int], include_pbp: bool = True) -> Dict[str, Any]:
    nfl = _nflreadpy()
    session = SessionLocal()
    run_id = None
    metrics = {
        "seasons": seasons,
        "rows": {
            "schedules": 0,
            "team_game_stats": 0,
            "player_game_stats": 0,
            "injuries": 0,
            "rosters": 0,
            "nfl_com_rosters": 0,
            "nfl_com_team_stats": 0,
            "nfl_com_standings": 0,
            "pbp_raw_objects": 0,
            "raw_objects": 0,
        },
    }
    try:
        run_id = session.execute(
            text(
                """
                INSERT INTO nfl_dp_ingestion_runs (source, pipeline, started_at, status, metrics)
                VALUES (:source, :pipeline, :started_at, :status, CAST(:metrics AS jsonb))
                RETURNING id
                """
            ),
            {
                "source": "nflverse",
                "pipeline": "nflreadpy_snapshot",
                "started_at": _now(),
                "status": "running",
                "metrics": json.dumps(metrics),
            },
        ).scalar_one()

        schedules = nfl.load_schedules(seasons=seasons)
        team_stats = _safe_load_nflverse_table(nfl.load_team_stats, seasons=seasons)
        player_stats = _safe_load_nflverse_table(nfl.load_player_stats, seasons=seasons)
        injuries = _safe_load_nflverse_table(nfl.load_injuries, seasons=seasons)
        rosters = nfl.load_rosters(seasons=seasons)
        pbp = (
            _safe_load_nflverse_table(nfl.load_pbp, seasons=seasons)
            if include_pbp
            else None
        )

        for row in _iter_rows(schedules):
            season = _to_int(row.get("season"))
            week = _to_int(row.get("week"))
            game_id = str(row.get("game_id") or "")
            if not season or not game_id:
                continue
            session.execute(
                text(
                    """
                    INSERT INTO nfl_dp_schedules (
                      season, week, game_id, game_date, home_team, away_team,
                      home_score, away_score, spread_line, total_line, location, roof, surface, source, updated_at
                    ) VALUES (
                      :season, :week, :game_id, :game_date, :home_team, :away_team,
                      :home_score, :away_score, :spread_line, :total_line, :location, :roof, :surface, :source, :updated_at
                    )
                    ON CONFLICT (season, game_id) DO UPDATE SET
                      week = EXCLUDED.week,
                      game_date = EXCLUDED.game_date,
                      home_team = EXCLUDED.home_team,
                      away_team = EXCLUDED.away_team,
                      home_score = EXCLUDED.home_score,
                      away_score = EXCLUDED.away_score,
                      spread_line = EXCLUDED.spread_line,
                      total_line = EXCLUDED.total_line,
                      location = EXCLUDED.location,
                      roof = EXCLUDED.roof,
                      surface = EXCLUDED.surface,
                      source = EXCLUDED.source,
                      updated_at = EXCLUDED.updated_at
                    """
                ),
                {
                    "season": season,
                    "week": week,
                    "game_id": game_id,
                    "game_date": row.get("gameday"),
                    "home_team": row.get("home_team"),
                    "away_team": row.get("away_team"),
                    "home_score": _to_int(row.get("home_score")),
                    "away_score": _to_int(row.get("away_score")),
                    "spread_line": _to_float(row.get("spread_line")),
                    "total_line": _to_float(row.get("total_line")),
                    "location": row.get("stadium"),
                    "roof": row.get("roof"),
                    "surface": row.get("surface"),
                    "source": "nflverse",
                    "updated_at": _now(),
                },
            )
            _upsert_raw(
                session,
                source="nflverse",
                object_type="schedule_game",
                object_key=f"{season}:{game_id}",
                season=season,
                week=week,
                game_id=game_id,
                payload=row,
            )
            metrics["rows"]["schedules"] += 1
            metrics["rows"]["raw_objects"] += 1

        for row in _iter_rows(team_stats):
            season = _to_int(row.get("season"))
            game_id = str(row.get("game_id") or "")
            team = str(row.get("team") or "")
            if not season or not game_id or not team:
                continue
            session.execute(
                text(
                    """
                    INSERT INTO nfl_dp_team_game_stats (
                      season, week, game_id, team, opponent, points_for, points_against, yards, epa, success_rate, turnovers, source, updated_at
                    ) VALUES (
                      :season, :week, :game_id, :team, :opponent, :points_for, :points_against, :yards, :epa, :success_rate, :turnovers, :source, :updated_at
                    )
                    ON CONFLICT (season, game_id, team) DO UPDATE SET
                      week = EXCLUDED.week,
                      opponent = EXCLUDED.opponent,
                      points_for = EXCLUDED.points_for,
                      points_against = EXCLUDED.points_against,
                      yards = EXCLUDED.yards,
                      epa = EXCLUDED.epa,
                      success_rate = EXCLUDED.success_rate,
                      turnovers = EXCLUDED.turnovers,
                      source = EXCLUDED.source,
                      updated_at = EXCLUDED.updated_at
                    """
                ),
                {
                    "season": season,
                    "week": _to_int(row.get("week")),
                    "game_id": game_id,
                    "team": team,
                    "opponent": row.get("opponent_team"),
                    "points_for": _to_float(row.get("points")),
                    "points_against": _to_float(row.get("points_allowed")),
                    "yards": _to_float(row.get("yards")),
                    "epa": _to_float(row.get("total_epa")),
                    "success_rate": _to_float(row.get("success_rate")),
                    "turnovers": _to_int(row.get("turnovers")),
                    "source": "nflverse",
                    "updated_at": _now(),
                },
            )
            _upsert_raw(
                session,
                source="nflverse",
                object_type="team_game_stats",
                object_key=f"{season}:{game_id}:{team}",
                season=season,
                week=_to_int(row.get("week")),
                game_id=game_id,
                payload=row,
            )
            metrics["rows"]["team_game_stats"] += 1
            metrics["rows"]["raw_objects"] += 1

        for row in _iter_rows(player_stats):
            season = _to_int(row.get("season"))
            game_id = str(row.get("game_id") or "")
            player_id = str(row.get("player_id") or "")
            stat_type = str(row.get("position_group") or "unknown")
            if not season or not game_id or not player_id:
                continue
            session.execute(
                text(
                    """
                    INSERT INTO nfl_dp_player_game_stats (
                      season, week, game_id, player_id, player_name, team, position, stat_type, metrics, source, updated_at
                    ) VALUES (
                      :season, :week, :game_id, :player_id, :player_name, :team, :position, :stat_type, CAST(:metrics AS jsonb), :source, :updated_at
                    )
                    ON CONFLICT (season, game_id, player_id, stat_type) DO UPDATE SET
                      week = EXCLUDED.week,
                      player_name = EXCLUDED.player_name,
                      team = EXCLUDED.team,
                      position = EXCLUDED.position,
                      metrics = EXCLUDED.metrics,
                      source = EXCLUDED.source,
                      updated_at = EXCLUDED.updated_at
                    """
                ),
                {
                    "season": season,
                    "week": _to_int(row.get("week")),
                    "game_id": game_id,
                    "player_id": player_id,
                    "player_name": row.get("player_name"),
                    "team": row.get("recent_team"),
                    "position": row.get("position"),
                    "stat_type": stat_type,
                    "metrics": json.dumps(row),
                    "source": "nflverse",
                    "updated_at": _now(),
                },
            )
            metrics["rows"]["player_game_stats"] += 1

        for row in _iter_rows(injuries):
            season = _to_int(row.get("season"))
            week = _to_int(row.get("week"))
            team = str(row.get("team") or "")
            player_id = str(row.get("gsis_id") or "")
            player_name = str(row.get("full_name") or "")
            injury_label = (
                row.get("report_primary_injury")
                or row.get("practice_primary_injury")
                or row.get("report_secondary_injury")
                or row.get("practice_secondary_injury")
            )
            if not season or week is None or not team:
                continue
            player_key = player_id or player_name or "unknown"
            session.execute(
                text(
                    """
                    INSERT INTO nfl_dp_injuries (
                      season, week, team, player_key, player_id, player_name, report_status, practice_status, injury, source, updated_at
                    ) VALUES (
                      :season, :week, :team, :player_key, :player_id, :player_name, :report_status, :practice_status, :injury, :source, :updated_at
                    )
                    ON CONFLICT (season, week, team, player_key) DO UPDATE SET
                      player_id = EXCLUDED.player_id,
                      player_name = EXCLUDED.player_name,
                      report_status = EXCLUDED.report_status,
                      practice_status = EXCLUDED.practice_status,
                      injury = EXCLUDED.injury,
                      source = EXCLUDED.source,
                      updated_at = EXCLUDED.updated_at
                    """
                ),
                {
                    "season": season,
                    "week": week,
                    "team": team,
                    "player_key": player_key,
                    "player_id": player_id or None,
                    "player_name": player_name or None,
                    "report_status": row.get("report_status"),
                    "practice_status": row.get("practice_status"),
                    "injury": injury_label,
                    "source": "nflverse",
                    "updated_at": _now(),
                },
            )
            metrics["rows"]["injuries"] += 1

        for row in _iter_rows(rosters):
            season = _to_int(row.get("season"))
            team = str(row.get("team") or "")
            player_id = str(row.get("gsis_id") or "")
            if not season or not team or not player_id:
                continue
            session.execute(
                text(
                    """
                    INSERT INTO nfl_dp_rosters (
                      season, team, player_id, player_name, position, jersey_number,
                      entry_year, rookie_year, draft_number, source, updated_at
                    ) VALUES (
                      :season, :team, :player_id, :player_name, :position, :jersey_number,
                      :entry_year, :rookie_year, :draft_number, :source, :updated_at
                    )
                    ON CONFLICT (season, team, player_id) DO UPDATE SET
                      player_name = EXCLUDED.player_name,
                      position = EXCLUDED.position,
                      jersey_number = EXCLUDED.jersey_number,
                      entry_year = COALESCE(EXCLUDED.entry_year, nfl_dp_rosters.entry_year),
                      rookie_year = COALESCE(EXCLUDED.rookie_year, nfl_dp_rosters.rookie_year),
                      draft_number = COALESCE(EXCLUDED.draft_number, nfl_dp_rosters.draft_number),
                      source = EXCLUDED.source,
                      updated_at = EXCLUDED.updated_at
                    """
                ),
                {
                    "season": season,
                    "team": team,
                    "player_id": player_id,
                    "player_name": row.get("full_name")
                    or row.get("football_name")
                    or row.get("player_name"),
                    "position": row.get("position"),
                    "jersey_number": str(row.get("jersey_number") or ""),
                    "entry_year": _to_int(row.get("entry_year")),
                    "rookie_year": _to_int(row.get("rookie_year")),
                    "draft_number": _to_int(row.get("draft_number")),
                    "source": "nflverse",
                    "updated_at": _now(),
                },
            )
            metrics["rows"]["rosters"] += 1

        if pbp is not None:
            for row in _iter_rows(pbp):
                season = _to_int(row.get("season"))
                game_id = str(row.get("game_id") or "")
                play_id = str(row.get("play_id") or row.get("old_game_id") or "")
                if not season or not game_id or not play_id:
                    continue
                _upsert_raw(
                    session,
                    source="nflverse",
                    object_type="pbp_play",
                    object_key=f"{season}:{game_id}:{play_id}",
                    season=season,
                    week=_to_int(row.get("week")),
                    game_id=game_id,
                    payload=row,
                )
                metrics["rows"]["pbp_raw_objects"] += 1
                metrics["rows"]["raw_objects"] += 1

        # NFL.com overlays run after nflverse ingestion so upstream rows are preferred
        # when available, while still preserving nflverse as the fallback source.
        try:
            _overlay_nfl_com_team_intel(session=session, seasons=seasons, metrics=metrics)
        except Exception as nfl_com_exc:
            metrics.setdefault("nfl_com", {})["overlay_error"] = str(nfl_com_exc)

        session.execute(
            text(
                """
                UPDATE nfl_dp_ingestion_runs
                SET finished_at = :finished_at,
                    status = :status,
                    metrics = CAST(:metrics AS jsonb)
                WHERE id = :id
                """
            ),
            {
                "id": run_id,
                "finished_at": _now(),
                "status": "success",
                "metrics": json.dumps(metrics),
            },
        )
        session.commit()
        return metrics
    except Exception as exc:
        session.rollback()
        if run_id is not None:
            session.execute(
                text(
                    """
                    UPDATE nfl_dp_ingestion_runs
                    SET finished_at = :finished_at,
                        status = :status,
                        metrics = CAST(:metrics AS jsonb),
                        error_message = :error_message
                    WHERE id = :id
                    """
                ),
                {
                    "id": run_id,
                    "finished_at": _now(),
                    "status": "failed",
                    "metrics": json.dumps(metrics),
                    "error_message": str(exc),
                },
            )
            session.commit()
        raise
    finally:
        session.close()


def materialize_player_projection_features(
    *, seasons: List[int], week: int | None = None, replace_existing: bool = False
) -> Dict[str, Any]:
    session = SessionLocal()
    run_id = None
    metrics = {
        "seasons": seasons,
        "week": week,
        "replace_existing": replace_existing,
        "rows": {"projection_feature_rows": 0},
    }
    try:
        run_id = session.execute(
            text(
                """
                INSERT INTO nfl_dp_ingestion_runs (source, pipeline, started_at, status, metrics)
                VALUES (:source, :pipeline, :started_at, :status, CAST(:metrics AS jsonb))
                RETURNING id
                """
            ),
            {
                "source": "nflverse",
                "pipeline": "nfl_player_projection_feature_materialization",
                "started_at": _now(),
                "status": "running",
                "metrics": json.dumps(metrics),
            },
        ).scalar_one()

        for season in seasons:
            if replace_existing:
                session.execute(
                    text(
                        """
                        DELETE FROM nfl_player_projection_features_weekly
                        WHERE season = :season
                          AND (CAST(:week AS int) IS NULL OR week = CAST(:week AS int))
                        """
                    ),
                    {"season": season, "week": week},
                )

            session.execute(
                text(
                    """
                    INSERT INTO nfl_player_projection_features_weekly (
                      season, week, team, player_id, player_name, position,
                      game_id, opponent, game_date,
                      snap_proxy, team_snap_share, route_proxy, target_proxy, rush_share, red_zone_share,
                      qb_dropback_factor, qb_pressure_factor, team_pace_factor, team_pass_rate_factor,
                      opponent_pass_defense_factor, opponent_rush_defense_factor,
                      availability_confidence, role_confidence,
                      offense_snaps, offense_snap_pct, snap_source,
                      feature_payload, source, created_at, updated_at
                    )
                    WITH usage AS (
                      SELECT
                        u.season,
                        u.week,
                        u.team,
                        u.player_id,
                        u.player_name,
                        u.position,
                        u.involvement_plays,
                        u.targets,
                        u.receptions,
                        u.rush_attempts,
                        u.red_zone_targets,
                        u.red_zone_carries,
                        u.qb_dropbacks,
                        u.qb_pressures_taken,
                        u.success_rate,
                        u.source AS usage_source,
                        SUM(u.involvement_plays) OVER (PARTITION BY u.season, u.week, u.team) AS team_involvement,
                        SUM(u.targets) OVER (PARTITION BY u.season, u.week, u.team) AS team_targets,
                        SUM(u.rush_attempts) OVER (PARTITION BY u.season, u.week, u.team) AS team_rush_attempts,
                        SUM(u.red_zone_targets + u.red_zone_carries) OVER (PARTITION BY u.season, u.week, u.team) AS team_red_zone_events
                      FROM nfl_dp_player_usage_weekly u
                      WHERE u.season = :season
                        AND (CAST(:week AS int) IS NULL OR u.week = CAST(:week AS int))
                    ),
                    snaps AS (
                      -- Real offense snaps from nflverse (PFR), bridged to GSIS via gsis_player_id.
                      SELECT
                        season,
                        week,
                        team,
                        gsis_player_id AS player_id,
                        MAX(offense_snaps) AS offense_snaps,
                        MAX(offense_pct) AS offense_pct
                      FROM nfl_dp_snap_counts_weekly
                      WHERE season = :season
                        AND (CAST(:week AS int) IS NULL OR week = CAST(:week AS int))
                        AND gsis_player_id IS NOT NULL
                      GROUP BY season, week, team, gsis_player_id
                    ),
                    injury AS (
                      -- Enterprise availability: report status dominates, practice
                      -- (DNP/limited) can only pull confidence down. Aligns with
                      -- model-service nfl_injury_role_shocks.availability_from_injury_statuses.
                      SELECT
                        i.season,
                        i.week,
                        i.team,
                        COALESCE(NULLIF(i.player_id, ''), NULLIF(i.player_name, ''), i.player_key) AS player_key,
                        MAX(
                          LEAST(
                            0.98,
                            GREATEST(
                              0.05,
                              (
                                0.72 * CASE
                                  WHEN lower(COALESCE(i.report_status, '')) IN ('out') THEN 0.08
                                  WHEN lower(COALESCE(i.report_status, '')) IN ('doubtful') THEN 0.12
                                  WHEN lower(COALESCE(i.report_status, '')) LIKE '%injured reserve%'
                                    OR lower(COALESCE(i.report_status, '')) = 'ir' THEN 0.08
                                  WHEN lower(COALESCE(i.report_status, '')) IN ('questionable') THEN 0.52
                                  WHEN lower(COALESCE(i.report_status, '')) IN ('probable', 'limited') THEN 0.82
                                  WHEN lower(COALESCE(i.report_status, '')) IN ('healthy', '') THEN 0.95
                                  ELSE 0.88
                                END
                                + 0.28 * CASE
                                  WHEN lower(COALESCE(i.practice_status, '')) LIKE '%did not participate%'
                                    OR lower(COALESCE(i.practice_status, '')) = 'dnp' THEN 0.15
                                  WHEN lower(COALESCE(i.practice_status, '')) LIKE '%limited%' THEN 0.62
                                  WHEN lower(COALESCE(i.practice_status, '')) LIKE '%full%' THEN 0.96
                                  ELSE 0.90
                                END
                              )
                            )
                          )
                        ) AS availability_confidence
                      FROM nfl_dp_injuries i
                      WHERE i.season = :season
                        AND (CAST(:week AS int) IS NULL OR i.week = CAST(:week AS int))
                      GROUP BY i.season, i.week, i.team, COALESCE(NULLIF(i.player_id, ''), NULLIF(i.player_name, ''), i.player_key)
                    ),
                    schedule_dim AS (
                      SELECT
                        s.season,
                        s.week,
                        s.game_id,
                        s.game_date,
                        s.home_team,
                        s.away_team
                      FROM nfl_dp_schedules s
                      WHERE s.season = :season
                        AND (CAST(:week AS int) IS NULL OR s.week = CAST(:week AS int))
                    ),
                    league_defense AS (
                      SELECT
                        season,
                        week,
                        AVG(epa_per_play_defense_allowed) AS league_avg_epa_allowed
                      FROM nfl_dp_team_situational_weekly
                      WHERE season = :season
                        AND (CAST(:week AS int) IS NULL OR week = CAST(:week AS int))
                      GROUP BY season, week
                    )
                    SELECT
                      u.season,
                      u.week,
                      u.team,
                      u.player_id,
                      u.player_name,
                      u.position,
                      sd.game_id,
                      CASE WHEN sd.home_team = u.team THEN sd.away_team ELSE sd.home_team END AS opponent,
                      sd.game_date,
                      GREATEST(0.0, LEAST(1.0, (u.involvement_plays::numeric / NULLIF(u.team_involvement::numeric, 0)))) AS snap_proxy,
                      -- Prefer real offense snap % when bridged; else PBP involvement proxy.
                      GREATEST(
                        0.0,
                        LEAST(
                          1.0,
                          COALESCE(
                            sc.offense_pct,
                            (u.involvement_plays::numeric / NULLIF(t.offensive_plays::numeric, 0))
                          )
                        )
                      ) AS team_snap_share,
                      GREATEST(0.0, LEAST(1.0, ((u.targets + u.receptions)::numeric / NULLIF((u.team_targets + 1)::numeric, 0)))) AS route_proxy,
                      GREATEST(0.0, LEAST(1.0, (u.targets::numeric / NULLIF((u.team_targets + 1)::numeric, 0)))) AS target_proxy,
                      GREATEST(0.0, LEAST(1.0, (u.rush_attempts::numeric / NULLIF((u.team_rush_attempts + 1)::numeric, 0)))) AS rush_share,
                      GREATEST(0.0, LEAST(1.0, ((u.red_zone_targets + u.red_zone_carries)::numeric / NULLIF((u.team_red_zone_events + 1)::numeric, 0)))) AS red_zone_share,
                      GREATEST(0.5, LEAST(1.5, (u.qb_dropbacks::numeric / NULLIF((u.involvement_plays + 1)::numeric, 0)))) AS qb_dropback_factor,
                      GREATEST(0.5, LEAST(1.5, (u.qb_pressures_taken::numeric / NULLIF((u.qb_dropbacks + 1)::numeric, 0)) * 3.0)) AS qb_pressure_factor,
                      GREATEST(0.75, LEAST(1.25, (t.offensive_plays::numeric / 64.0))) AS team_pace_factor,
                      GREATEST(0.75, LEAST(1.25, COALESCE(t.pass_rate, 0.55) / 0.55)) AS team_pass_rate_factor,
                      -- Real opponent-adjusted matchup factors: the scheduled opponent's
                      -- actual defensive EPA allowed vs. league average that week, so a
                      -- player facing a bad defense projects above their team-context-only
                      -- baseline and vice versa. EPA/play is naturally ~zero-centered
                      -- league-wide, so this needs no separate normalization constant.
                      -- No pass/rush defensive EPA split exists yet (see
                      -- nfl_dp_team_situational_weekly), so both factors share the same
                      -- overall defensive signal; the pass factor additionally folds in the
                      -- opponent's real pass-rush pressure rate, which IS pass-specific.
                      GREATEST(0.75, LEAST(1.30,
                        1.0
                        + (1.15 * (COALESCE(opp_t.epa_per_play_defense_allowed, 0.0) - COALESCE(ld.league_avg_epa_allowed, 0.0)))
                        - (0.35 * (COALESCE(opp_t.pressure_rate_generated, 0.22) - 0.22))
                      )) AS opponent_pass_defense_factor,
                      GREATEST(0.75, LEAST(1.30,
                        1.0
                        + (1.15 * (COALESCE(opp_t.epa_per_play_defense_allowed, 0.0) - COALESCE(ld.league_avg_epa_allowed, 0.0)))
                      )) AS opponent_rush_defense_factor,
                      COALESCE(inj.availability_confidence, 0.90) AS availability_confidence,
                      -- QBs almost never draw targets; the target_proxy term
                      -- collapsed role_confidence into ~0.15-0.35 for real
                      -- starters and starved box-score concentration. Use
                      -- team snap + dropback mix for QBs instead.
                      CASE
                        WHEN UPPER(COALESCE(u.position, '')) = 'QB' THEN
                          GREATEST(
                            0.20,
                            LEAST(
                              0.99,
                              (0.70 * GREATEST(0.0, LEAST(1.0, (u.involvement_plays::numeric / NULLIF(t.offensive_plays::numeric, 0)))))
                              + (0.30 * GREATEST(0.0, LEAST(1.0, (u.qb_dropbacks::numeric / NULLIF((u.involvement_plays + 1)::numeric, 0)))))
                            )
                          )
                        ELSE
                          GREATEST(
                            0.15,
                            LEAST(
                              0.99,
                              (0.40 * GREATEST(0.0, LEAST(1.0, (u.involvement_plays::numeric / NULLIF(u.team_involvement::numeric, 0)))))
                              + (0.35 * GREATEST(0.0, LEAST(1.0, (u.targets::numeric / NULLIF((u.team_targets + 1)::numeric, 0)))))
                              + (0.25 * GREATEST(0.0, LEAST(1.0, COALESCE(u.success_rate, 0.50))))
                            )
                          )
                      END AS role_confidence,
                      sc.offense_snaps AS offense_snaps,
                      sc.offense_pct AS offense_snap_pct,
                      CASE
                        WHEN sc.offense_pct IS NOT NULL THEN 'nfl_dp_snap_counts_weekly'
                        ELSE 'pbp_involvement_proxy'
                      END AS snap_source,
                      jsonb_build_object(
                        'involvement_plays', u.involvement_plays,
                        'targets', u.targets,
                        'rush_attempts', u.rush_attempts,
                        'red_zone_targets', u.red_zone_targets,
                        'red_zone_carries', u.red_zone_carries,
                        'success_rate', u.success_rate,
                        'usage_source', u.usage_source,
                        'offense_snaps', sc.offense_snaps,
                        'offense_snap_pct', sc.offense_pct,
                        'snap_source', CASE
                          WHEN sc.offense_pct IS NOT NULL THEN 'nfl_dp_snap_counts_weekly'
                          ELSE 'pbp_involvement_proxy'
                        END
                      ) AS feature_payload,
                      'nfl_dp_usage_situational'::text AS source,
                      NOW(),
                      NOW()
                    FROM usage u
                    LEFT JOIN nfl_dp_team_situational_weekly t
                      ON t.season = u.season AND t.week = u.week AND t.team = u.team
                    LEFT JOIN snaps sc
                      ON sc.season = u.season
                      AND sc.week = u.week
                      AND sc.team = u.team
                      AND sc.player_id = u.player_id
                    LEFT JOIN injury inj
                      ON inj.season = u.season
                      AND inj.week = u.week
                      AND inj.team = u.team
                      AND inj.player_key IN (u.player_id, u.player_name)
                    LEFT JOIN schedule_dim sd
                      ON sd.season = u.season
                      AND sd.week = u.week
                      AND (sd.home_team = u.team OR sd.away_team = u.team)
                    LEFT JOIN nfl_dp_team_situational_weekly opp_t
                      ON opp_t.season = sd.season
                      AND opp_t.week = sd.week
                      AND opp_t.team = (CASE WHEN sd.home_team = u.team THEN sd.away_team ELSE sd.home_team END)
                    LEFT JOIN league_defense ld
                      ON ld.season = u.season AND ld.week = u.week
                    ON CONFLICT (season, week, team, player_id) DO UPDATE SET
                      player_name = EXCLUDED.player_name,
                      position = EXCLUDED.position,
                      game_id = EXCLUDED.game_id,
                      opponent = EXCLUDED.opponent,
                      game_date = EXCLUDED.game_date,
                      snap_proxy = EXCLUDED.snap_proxy,
                      team_snap_share = EXCLUDED.team_snap_share,
                      route_proxy = EXCLUDED.route_proxy,
                      target_proxy = EXCLUDED.target_proxy,
                      rush_share = EXCLUDED.rush_share,
                      red_zone_share = EXCLUDED.red_zone_share,
                      qb_dropback_factor = EXCLUDED.qb_dropback_factor,
                      qb_pressure_factor = EXCLUDED.qb_pressure_factor,
                      team_pace_factor = EXCLUDED.team_pace_factor,
                      team_pass_rate_factor = EXCLUDED.team_pass_rate_factor,
                      opponent_pass_defense_factor = EXCLUDED.opponent_pass_defense_factor,
                      opponent_rush_defense_factor = EXCLUDED.opponent_rush_defense_factor,
                      availability_confidence = EXCLUDED.availability_confidence,
                      role_confidence = EXCLUDED.role_confidence,
                      offense_snaps = EXCLUDED.offense_snaps,
                      offense_snap_pct = EXCLUDED.offense_snap_pct,
                      snap_source = EXCLUDED.snap_source,
                      feature_payload = EXCLUDED.feature_payload,
                      source = EXCLUDED.source,
                      updated_at = EXCLUDED.updated_at
                    """
                ),
                {"season": season, "week": week},
            )

            rows_for_season = session.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM nfl_player_projection_features_weekly
                    WHERE season = :season
                      AND (CAST(:week AS int) IS NULL OR week = CAST(:week AS int))
                    """
                ),
                {"season": season, "week": week},
            ).scalar_one()
            metrics["rows"]["projection_feature_rows"] += int(rows_for_season or 0)
            session.commit()

        session.execute(
            text(
                """
                UPDATE nfl_dp_ingestion_runs
                SET finished_at = :finished_at,
                    status = :status,
                    metrics = CAST(:metrics AS jsonb)
                WHERE id = :id
                """
            ),
            {
                "id": run_id,
                "finished_at": _now(),
                "status": "success",
                "metrics": json.dumps(metrics),
            },
        )
        session.commit()
        return metrics
    except Exception as exc:
        session.rollback()
        if run_id is not None:
            session.execute(
                text(
                    """
                    UPDATE nfl_dp_ingestion_runs
                    SET finished_at = :finished_at,
                        status = :status,
                        metrics = CAST(:metrics AS jsonb),
                        error_message = :error_message
                    WHERE id = :id
                    """
                ),
                {
                    "id": run_id,
                    "finished_at": _now(),
                    "status": "failed",
                    "metrics": json.dumps(metrics),
                    "error_message": str(exc),
                },
            )
            session.commit()
        raise
    finally:
        session.close()
