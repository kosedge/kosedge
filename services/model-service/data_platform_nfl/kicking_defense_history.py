"""Real per-kicker and per-team defense/special-teams weekly stats, built
entirely from ALREADY-INGESTED nflreadpy data -- no new external fetch.

`ingest_nflverse_snapshot` already loads nflreadpy's `load_player_stats()`
(which includes real per-kicker field-goal-by-distance-bucket and extra-point
counts for every K, since kicking is a `position_group = 'SPEC'` stat) and
`load_team_stats()` (which includes real per-team sacks/interceptions/fumble
recoveries/defensive+special-teams touchdowns/safeties) -- but only ever
persists a narrow points_for/points_against/yards/epa/success_rate/turnovers
slice of `load_team_stats()` onto `nfl_dp_team_game_stats`, and stores every
`load_player_stats()` row's FULL payload as an opaque `metrics` jsonb blob on
`nfl_dp_player_game_stats` keyed by `stat_type = position_group` (real
kicking numbers were always there, just never normalized into typed columns
before this module).

This module is a pure NORMALIZATION pass over data that is already sitting in
Postgres:
  - `nfl_dp_player_game_stats.metrics` (WHERE `position = 'K'`) ->
    `nfl_dp_kicker_weekly` (real FG attempts/makes by nflverse's own 6
    distance buckets, plus PAT attempts/makes).
  - `nfl_dp_raw_objects.payload` (WHERE `object_type = 'team_game_stats'`,
    the untouched full `load_team_stats()` row saved by `_upsert_raw` during
    every ingest run) -> `nfl_dp_team_defense_weekly` (real sacks,
    interceptions, fumble recoveries, defensive + special-teams touchdowns,
    safeties).

Both feed `services/model-service/src/services/nfl_kicker_dst_projections.py`
(a separate service -- shares only the Postgres schema, same architectural
boundary as every other model-service/data-platform-nfl table). Safe to
re-run any time (idempotent upserts); call again after every
`ingest_nflverse_snapshot` run to pick up newly-ingested games.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy import text

from .db import SessionLocal


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_int(v: Any) -> int:
    try:
        if v is None:
            return 0
        return int(v)
    except (TypeError, ValueError):
        return 0


def _to_float(v: Any) -> float | None:
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def materialize_kicker_weekly_history(*, seasons: List[int], replace_existing: bool = False) -> Dict[str, Any]:
    """Normalizes real kicker FG-by-bucket + PAT stats already sitting in
    `nfl_dp_player_game_stats.metrics` (position = 'K') into
    `nfl_dp_kicker_weekly`. `team` is read from `metrics->>'team'`, not the
    outer `nfl_dp_player_game_stats.team` column -- that column is a
    pre-existing gap in the general player_game_stats ingest (always NULL for
    every position, not specific to kickers), out of scope for this module to
    fix; the real team code IS present inside every row's own metrics
    payload (`load_player_stats()`'s `team` field), so this reads from there
    directly."""
    session = SessionLocal()
    rows_written = 0
    try:
        for season in seasons:
            if replace_existing:
                session.execute(
                    text("DELETE FROM nfl_dp_kicker_weekly WHERE season = :season"),
                    {"season": season},
                )
            rows = session.execute(
                text(
                    """
                    SELECT season, week, game_id, player_id, player_name, metrics
                    FROM nfl_dp_player_game_stats
                    WHERE season = :season AND position = 'K'
                    """
                ),
                {"season": season},
            ).fetchall()
            for row in rows:
                metrics = row.metrics or {}
                team = metrics.get("team") or metrics.get("recent_team")
                if not team:
                    continue
                made = {b: _to_int(metrics.get(f"fg_made_{b}")) for b in ("0_19", "20_29", "30_39", "40_49", "50_59", "60_")}
                missed = {b: _to_int(metrics.get(f"fg_missed_{b}")) for b in ("0_19", "20_29", "30_39", "40_49", "50_59", "60_")}
                att = {b: made[b] + missed[b] for b in made}
                session.execute(
                    text(
                        """
                        INSERT INTO nfl_dp_kicker_weekly (
                          season, week, team, player_id, player_name, game_id,
                          fg_att, fg_made,
                          fg_att_0_19, fg_made_0_19, fg_att_20_29, fg_made_20_29,
                          fg_att_30_39, fg_made_30_39, fg_att_40_49, fg_made_40_49,
                          fg_att_50_59, fg_made_50_59, fg_att_60_plus, fg_made_60_plus,
                          pat_att, pat_made, source, updated_at
                        ) VALUES (
                          :season, :week, :team, :player_id, :player_name, :game_id,
                          :fg_att, :fg_made,
                          :fg_att_0_19, :fg_made_0_19, :fg_att_20_29, :fg_made_20_29,
                          :fg_att_30_39, :fg_made_30_39, :fg_att_40_49, :fg_made_40_49,
                          :fg_att_50_59, :fg_made_50_59, :fg_att_60_plus, :fg_made_60_plus,
                          :pat_att, :pat_made, 'nflverse', :updated_at
                        )
                        ON CONFLICT (season, week, team, player_id) DO UPDATE SET
                          player_name = EXCLUDED.player_name,
                          game_id = EXCLUDED.game_id,
                          fg_att = EXCLUDED.fg_att,
                          fg_made = EXCLUDED.fg_made,
                          fg_att_0_19 = EXCLUDED.fg_att_0_19,
                          fg_made_0_19 = EXCLUDED.fg_made_0_19,
                          fg_att_20_29 = EXCLUDED.fg_att_20_29,
                          fg_made_20_29 = EXCLUDED.fg_made_20_29,
                          fg_att_30_39 = EXCLUDED.fg_att_30_39,
                          fg_made_30_39 = EXCLUDED.fg_made_30_39,
                          fg_att_40_49 = EXCLUDED.fg_att_40_49,
                          fg_made_40_49 = EXCLUDED.fg_made_40_49,
                          fg_att_50_59 = EXCLUDED.fg_att_50_59,
                          fg_made_50_59 = EXCLUDED.fg_made_50_59,
                          fg_att_60_plus = EXCLUDED.fg_att_60_plus,
                          fg_made_60_plus = EXCLUDED.fg_made_60_plus,
                          pat_att = EXCLUDED.pat_att,
                          pat_made = EXCLUDED.pat_made,
                          updated_at = EXCLUDED.updated_at
                        """
                    ),
                    {
                        "season": season,
                        "week": row.week,
                        "team": team,
                        "player_id": row.player_id,
                        "player_name": row.player_name,
                        "game_id": row.game_id,
                        "fg_att": sum(att.values()),
                        "fg_made": sum(made.values()),
                        "fg_att_0_19": att["0_19"],
                        "fg_made_0_19": made["0_19"],
                        "fg_att_20_29": att["20_29"],
                        "fg_made_20_29": made["20_29"],
                        "fg_att_30_39": att["30_39"],
                        "fg_made_30_39": made["30_39"],
                        "fg_att_40_49": att["40_49"],
                        "fg_made_40_49": made["40_49"],
                        "fg_att_50_59": att["50_59"],
                        "fg_made_50_59": made["50_59"],
                        "fg_att_60_plus": att["60_"],
                        "fg_made_60_plus": made["60_"],
                        "pat_att": _to_int(metrics.get("pat_att")),
                        "pat_made": _to_int(metrics.get("pat_made")),
                        "updated_at": _now(),
                    },
                )
                rows_written += 1
        session.commit()
        return {"seasons": seasons, "rows_written": rows_written}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def materialize_team_defense_weekly_history(*, seasons: List[int], replace_existing: bool = False) -> Dict[str, Any]:
    """Normalizes real team defense/special-teams counting stats already
    sitting in `nfl_dp_raw_objects.payload` (object_type = 'team_game_stats',
    the untouched full `load_team_stats()` row saved during every ingest run)
    into `nfl_dp_team_defense_weekly`.

    `points_allowed` is deliberately NOT read from that same raw payload --
    `nflreadpy.load_team_stats()` has no points/points_allowed field at all
    (confirmed by direct inspection of the real ingested payload keys), which
    is exactly why `nfl_dp_team_game_stats.points_for`/`points_against` have
    silently been NULL for every single row already in this database (a
    real, pre-existing gap discovered while building this module, predating
    it and out of scope to fix in the general ingest pipeline here -- see
    docs/NFL_PROPS_FANTASY_FOUNDATION.md's K/DST section). The REAL final
    score IS available, from `nfl_dp_schedules.home_score`/`away_score`, so
    `points_allowed` here is the opponent's real final score for that game,
    joined in from there instead."""
    session = SessionLocal()
    rows_written = 0
    try:
        for season in seasons:
            if replace_existing:
                session.execute(
                    text("DELETE FROM nfl_dp_team_defense_weekly WHERE season = :season"),
                    {"season": season},
                )
            rows = session.execute(
                text(
                    """
                    SELECT
                      r.season, r.week, r.game_id, r.payload,
                      CASE WHEN s.home_team = r.payload->>'team' THEN s.away_score ELSE s.home_score END AS points_allowed
                    FROM nfl_dp_raw_objects r
                    LEFT JOIN nfl_dp_schedules s
                      ON s.season = r.season AND s.game_id = r.game_id
                    WHERE r.object_type = 'team_game_stats' AND r.season = :season
                    """
                ),
                {"season": season},
            ).fetchall()
            for row in rows:
                payload = row.payload or {}
                team = payload.get("team")
                if not team:
                    continue
                session.execute(
                    text(
                        """
                        INSERT INTO nfl_dp_team_defense_weekly (
                          season, week, team, opponent, game_id, points_allowed,
                          sacks, interceptions, fumble_recoveries, defensive_tds,
                          special_teams_tds, safeties, source, updated_at
                        ) VALUES (
                          :season, :week, :team, :opponent, :game_id, :points_allowed,
                          :sacks, :interceptions, :fumble_recoveries, :defensive_tds,
                          :special_teams_tds, :safeties, 'nflverse', :updated_at
                        )
                        ON CONFLICT (season, week, team) DO UPDATE SET
                          opponent = EXCLUDED.opponent,
                          game_id = EXCLUDED.game_id,
                          points_allowed = EXCLUDED.points_allowed,
                          sacks = EXCLUDED.sacks,
                          interceptions = EXCLUDED.interceptions,
                          fumble_recoveries = EXCLUDED.fumble_recoveries,
                          defensive_tds = EXCLUDED.defensive_tds,
                          special_teams_tds = EXCLUDED.special_teams_tds,
                          safeties = EXCLUDED.safeties,
                          updated_at = EXCLUDED.updated_at
                        """
                    ),
                    {
                        "season": season,
                        "week": row.week,
                        "team": team,
                        "opponent": payload.get("opponent_team"),
                        "game_id": row.game_id,
                        "points_allowed": _to_float(row.points_allowed),
                        "sacks": _to_float(payload.get("def_sacks")) or 0.0,
                        "interceptions": _to_float(payload.get("def_interceptions")) or 0.0,
                        "fumble_recoveries": _to_float(payload.get("fumble_recovery_opp")) or 0.0,
                        "defensive_tds": _to_float(payload.get("def_tds")) or 0.0,
                        "special_teams_tds": _to_float(payload.get("special_teams_tds")) or 0.0,
                        "safeties": _to_float(payload.get("def_safeties")) or 0.0,
                        "updated_at": _now(),
                    },
                )
                rows_written += 1
        session.commit()
        return {"seasons": seasons, "rows_written": rows_written}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def materialize_kicking_and_defense_history(*, seasons: List[int], replace_existing: bool = False) -> Dict[str, Any]:
    kicker_result = materialize_kicker_weekly_history(seasons=seasons, replace_existing=replace_existing)
    defense_result = materialize_team_defense_weekly_history(seasons=seasons, replace_existing=replace_existing)
    return {"kicker": kicker_result, "team_defense": defense_result}
