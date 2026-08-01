"""WNBA model pipeline jobs (Phase 0–3).

Celery tasks in ``src.tasks`` are thin wrappers around these functions so
``tasks.py`` stays maintainable. Do not import NBA priors into WNBA sims.
"""

from __future__ import annotations

import json
import logging
import os
import time as time_module
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text

from src.db import SessionLocal
from src.services.wnba_calibration import WnbaWalkforwardRow, summarize_walkforward
from src.services.wnba_data import (
    DEFAULT_WNBA_INGEST_SEASONS,
    WNBA_TEAM_ABBREV,
    compute_rest_days_by_team,
    default_league_average_inputs,
    features_from_data_wnba_team_stats,
    fetch_game_detail_data_wnba,
    fetch_schedule_window,
    fetch_season_schedule_data_wnba,
    iter_season_labels,
    normalize_team_key,
    player_stubs_from_data_wnba_detail,
    rolling_average_features,
    season_label_to_start_year,
    try_sportsdata_games_by_date,
    wnba_abbr_match_keys,
    wnba_full_names_for_abbr,
    wnba_season_year_from_date,
)
from src.services.wnba_possession_simulator import (
    DEFAULT_WNBA_MODEL_VERSION,
    WNBA_LEAGUE_DRTG,
    WNBA_LEAGUE_ORTG,
    WNBA_LEAGUE_PACE,
    WNBA_WORKER_BUILD_ID,
    WnbaGameInputs,
    simulate_wnba_game,
)
from src.services.wnba_publish_policy import board_publish_posture
from src.services.wnba_schema import ensure_wnba_model_tables

log = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _to_int_like(v: Any) -> Optional[int]:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _default_projection_seed(game_id: str, model_version: str, simulations: int) -> int:
    return abs(hash(f"{game_id}:{model_version}:{simulations}")) % (2**31 - 1)


def insert_wnba_projection(session: Any, projection: Dict[str, Any]) -> None:
    markets = projection.get("markets") or {}
    session.execute(
        text(
            """
            INSERT INTO wnba_market_projections (
              game_id, model_version, simulation_count,
              home_win_prob, total_mean, margin_mean,
              fair_home_ml, fair_total, fair_spread_home, home_cover_prob,
              worker_build_id, projection, created_at
            ) VALUES (
              :game_id, :model_version, :simulation_count,
              :home_win_prob, :total_mean, :margin_mean,
              :fair_home_ml, :fair_total, :fair_spread_home, :home_cover_prob,
              :worker_build_id, CAST(:projection AS jsonb), :created_at
            )
            """
        ),
        {
            "game_id": projection["game_id"],
            "model_version": projection["model_version"],
            "simulation_count": projection["simulation_count"],
            "home_win_prob": markets.get("home_win_prob"),
            "total_mean": markets.get("total_mean"),
            "margin_mean": markets.get("margin_mean"),
            "fair_home_ml": markets.get("fair_home_ml"),
            "fair_total": markets.get("fair_total"),
            "fair_spread_home": markets.get("fair_spread_home"),
            "home_cover_prob": markets.get("home_cover_prob"),
            "worker_build_id": projection.get("worker_build_id") or WNBA_WORKER_BUILD_ID,
            "projection": json.dumps(projection),
            "created_at": _now_utc(),
        },
    )


def wnba_market_lines_for_game(
    session: Any,
    game_id: str,
    *,
    game_date: Optional[date] = None,
    home_team_key: Optional[str] = None,
    away_team_key: Optional[str] = None,
) -> Dict[str, Optional[float]]:
    """Closing-ish spread/total from owned odds_snapshots — no Odds API burn.

    Lessons from NBA BOCE→BOS bug:
      1) densify stores Odds API full names with heuristic abbrs
      2) UTC tip can shift game_date vs ingest gdte (ET)
      3) ingest ids are wnba.com gids, not hierarchy UUIDs

    Match: UUID → (ET tip date | date±1) + (full name | abbr aliases).
    """
    try:
        row = None
        try:
            import uuid as _uuid

            _uuid.UUID(str(game_id))
            is_uuid = True
        except Exception:
            is_uuid = False
        if is_uuid:
            row = session.execute(
                text(
                    """
                    WITH latest AS (
                      SELECT DISTINCT ON (os.sportsbook_id, m.code)
                        m.code AS market_code,
                        os.spread_home,
                        os.total_points
                      FROM odds_snapshots os
                      JOIN markets m ON m.id = os.market_id
                      WHERE os.game_id = CAST(:game_id AS uuid)
                        AND m.code IN ('spread', 'total')
                      ORDER BY os.sportsbook_id, m.code, os.captured_at DESC
                    )
                    SELECT
                      AVG(spread_home) FILTER (WHERE market_code = 'spread') AS spread_home,
                      AVG(total_points) FILTER (WHERE market_code = 'total') AS total
                    FROM latest
                    """
                ),
                {"game_id": str(game_id)},
            ).fetchone()
        if (row is None or (row[0] is None and row[1] is None)) and game_date and home_team_key:
            home_key = normalize_team_key(str(home_team_key or ""))
            away_key = normalize_team_key(str(away_team_key or ""))
            home_names = [n.upper() for n in wnba_full_names_for_abbr(home_key)]
            away_names = [n.upper() for n in wnba_full_names_for_abbr(away_key)]
            home_abbrs = [a.upper() for a in wnba_abbr_match_keys(home_key)]
            away_abbrs = [a.upper() for a in wnba_abbr_match_keys(away_key)]
            season_year = wnba_season_year_from_date(game_date)
            row = session.execute(
                text(
                    """
                    WITH candidates AS (
                      SELECT
                        g.id AS game_id,
                        g.start_time,
                        CASE
                          WHEN g.start_time IS NOT NULL
                            AND (
                              (g.start_time AT TIME ZONE 'UTC')
                              AT TIME ZONE 'America/New_York'
                            )::date = CAST(:game_date AS date)
                          THEN 0
                          WHEN g.game_date = CAST(:game_date AS date) THEN 1
                          WHEN g.game_date = CAST(:game_date AS date) - INTERVAL '1 day' THEN 2
                          WHEN g.game_date = CAST(:game_date AS date) + INTERVAL '1 day' THEN 3
                          ELSE 9
                        END AS date_rank
                      FROM games g
                      JOIN seasons s ON s.id = g.season_id
                      JOIN leagues l ON l.id = s.league_id
                      JOIN teams home ON home.id = g.home_team_id
                      JOIN teams away ON away.id = g.away_team_id
                      WHERE l.code = 'wnba'
                        AND (
                          s.season_year = :season_year
                          OR s.season_year = :season_year + 1
                          OR s.season_year = CAST(EXTRACT(YEAR FROM CAST(:game_date AS date)) AS int)
                        )
                        AND (
                          g.game_date BETWEEN CAST(:game_date AS date) - INTERVAL '1 day'
                                         AND CAST(:game_date AS date) + INTERVAL '1 day'
                          OR (
                            g.start_time IS NOT NULL
                            AND (
                              (g.start_time AT TIME ZONE 'UTC')
                              AT TIME ZONE 'America/New_York'
                            )::date = CAST(:game_date AS date)
                          )
                        )
                        AND (
                          UPPER(TRIM(home.name)) = ANY(CAST(:home_names AS text[]))
                          OR UPPER(COALESCE(home.abbr, '')) = ANY(CAST(:home_abbrs AS text[]))
                        )
                        AND (
                          UPPER(TRIM(away.name)) = ANY(CAST(:away_names AS text[]))
                          OR UPPER(COALESCE(away.abbr, '')) = ANY(CAST(:away_abbrs AS text[]))
                        )
                      ORDER BY date_rank ASC, g.start_time NULLS LAST
                      LIMIT 1
                    ),
                    latest AS (
                      SELECT DISTINCT ON (os.sportsbook_id, m.code)
                        m.code AS market_code,
                        os.spread_home,
                        os.total_points
                      FROM odds_snapshots os
                      JOIN markets m ON m.id = os.market_id
                      JOIN candidates c ON c.game_id = os.game_id
                      WHERE m.code IN ('spread', 'total')
                      ORDER BY os.sportsbook_id, m.code, os.captured_at DESC
                    )
                    SELECT
                      AVG(spread_home) FILTER (WHERE market_code = 'spread') AS spread_home,
                      AVG(total_points) FILTER (WHERE market_code = 'total') AS total
                    FROM latest
                    """
                ),
                {
                    "game_date": game_date,
                    "season_year": season_year,
                    "home_names": home_names,
                    "away_names": away_names,
                    "home_abbrs": home_abbrs,
                    "away_abbrs": away_abbrs,
                },
            ).fetchone()
    except Exception:
        try:
            session.rollback()
        except Exception:
            pass
        return {"market_spread_home": None, "market_total": None}
    if not row:
        return {"market_spread_home": None, "market_total": None}
    return {
        "market_spread_home": _to_float(row[0]),
        "market_total": _to_float(row[1]),
    }


def upsert_wnba_game_ingest(session: Any, g: Dict[str, Any]) -> bool:
    external_id = str(g.get("external_game_id") or "").strip()
    if not external_id:
        return False
    game_date_raw = g.get("game_date")
    try:
        game_date_val = (
            date.fromisoformat(str(game_date_raw)[:10]) if game_date_raw else date.today()
        )
    except ValueError:
        game_date_val = date.today()
    session.execute(
        text(
            """
            INSERT INTO wnba_games_ingest (
              external_game_id, game_date, start_time,
              home_team_key, away_team_key,
              home_score, away_score, status, season, source, raw, updated_at
            ) VALUES (
              :external_game_id, :game_date, NULL,
              :home_team_key, :away_team_key,
              :home_score, :away_score, :status, :season, :source,
              CAST(:raw AS jsonb), :updated_at
            )
            ON CONFLICT (external_game_id) DO UPDATE SET
              game_date = EXCLUDED.game_date,
              home_team_key = EXCLUDED.home_team_key,
              away_team_key = EXCLUDED.away_team_key,
              home_score = EXCLUDED.home_score,
              away_score = EXCLUDED.away_score,
              status = EXCLUDED.status,
              season = EXCLUDED.season,
              source = EXCLUDED.source,
              raw = EXCLUDED.raw,
              updated_at = EXCLUDED.updated_at
            """
        ),
        {
            "external_game_id": external_id,
            "game_date": game_date_val,
            "home_team_key": normalize_team_key(
                str(g.get("home_team_key") or g.get("home_team") or "")
            ),
            "away_team_key": normalize_team_key(
                str(g.get("away_team_key") or g.get("away_team") or "")
            ),
            "home_score": g.get("home_score"),
            "away_score": g.get("away_score"),
            "status": str(g.get("status") or ""),
            "season": str(g.get("season") or ""),
            "source": str(g.get("source") or "data.wnba.com"),
            "raw": json.dumps(g.get("raw_header") or g.get("raw") or g, default=str),
            "updated_at": _now_utc(),
        },
    )
    return True


def upsert_wnba_team_game_features(
    session: Any,
    *,
    external_game_id: str,
    team_key: str,
    game_date_val: date,
    is_home: bool,
    opponent_key: str,
    feat: Dict[str, Any],
    rest_days: Optional[float],
    season: str,
    source: str,
) -> None:
    session.execute(
        text(
            """
            INSERT INTO wnba_team_game_features (
              external_game_id, team_key, game_date, is_home, opponent_key,
              pace, ortg, drtg, three_pt_rate, three_pt_pct, two_pt_pct,
              ft_rate, ft_pct, to_rate, orb_rate, points, possessions,
              rest_days, season, source, payload, updated_at
            ) VALUES (
              :external_game_id, :team_key, :game_date, :is_home, :opponent_key,
              :pace, :ortg, :drtg, :three_pt_rate, :three_pt_pct, :two_pt_pct,
              :ft_rate, :ft_pct, :to_rate, :orb_rate, :points, :possessions,
              :rest_days, :season, :source, CAST(:payload AS jsonb), :updated_at
            )
            ON CONFLICT (external_game_id, team_key) DO UPDATE SET
              game_date = EXCLUDED.game_date,
              is_home = EXCLUDED.is_home,
              opponent_key = EXCLUDED.opponent_key,
              pace = EXCLUDED.pace,
              ortg = EXCLUDED.ortg,
              drtg = EXCLUDED.drtg,
              three_pt_rate = EXCLUDED.three_pt_rate,
              three_pt_pct = EXCLUDED.three_pt_pct,
              two_pt_pct = EXCLUDED.two_pt_pct,
              ft_rate = EXCLUDED.ft_rate,
              ft_pct = EXCLUDED.ft_pct,
              to_rate = EXCLUDED.to_rate,
              orb_rate = EXCLUDED.orb_rate,
              points = EXCLUDED.points,
              possessions = EXCLUDED.possessions,
              rest_days = EXCLUDED.rest_days,
              season = EXCLUDED.season,
              source = EXCLUDED.source,
              payload = EXCLUDED.payload,
              updated_at = EXCLUDED.updated_at
            """
        ),
        {
            "external_game_id": external_game_id,
            "team_key": team_key,
            "game_date": game_date_val,
            "is_home": is_home,
            "opponent_key": opponent_key,
            "pace": feat.get("pace"),
            "ortg": feat.get("ortg"),
            "drtg": feat.get("drtg"),
            "three_pt_rate": feat.get("three_pt_rate"),
            "three_pt_pct": feat.get("three_pt_pct"),
            "two_pt_pct": feat.get("two_pt_pct"),
            "ft_rate": feat.get("ft_rate"),
            "ft_pct": feat.get("ft_pct"),
            "to_rate": feat.get("to_rate"),
            "orb_rate": feat.get("orb_rate"),
            "points": feat.get("points"),
            "possessions": feat.get("possessions"),
            "rest_days": rest_days,
            "season": season,
            "source": source,
            "payload": json.dumps({"n": 1}, default=str),
            "updated_at": _now_utc(),
        },
    )


def pull_wnba_schedule_ingest(days_back: int = 7, days_ahead: int = 3) -> Dict[str, int]:
    session = SessionLocal()
    upserted = 0
    try:
        ensure_wnba_model_tables(session)
        start = date.today() - timedelta(days=max(0, days_back))
        end = date.today() + timedelta(days=max(0, days_ahead))
        games = fetch_schedule_window(start, end, sleep_s=0.55)
        if not games:
            for offset in range(-max(0, days_back), max(0, days_ahead) + 1):
                d = date.today() + timedelta(days=offset)
                games.extend(try_sportsdata_games_by_date(d))
        for g in games:
            if upsert_wnba_game_ingest(session, g):
                upserted += 1
        session.commit()
        return {"games_upserted": upserted, "window_start": str(start), "window_end": str(end)}
    except Exception:
        session.rollback()
        log.exception("Failed WNBA schedule ingest")
        raise
    finally:
        session.close()


def pull_wnba_season_ingest(
    seasons: Optional[List[str]] = None,
    sleep_s: float = 0.35,
    enrich_details: bool = True,
    max_detail_games: int = 1200,
    player_stub_details: int = 60,
) -> Dict[str, Any]:
    session = SessionLocal()
    season_labels = iter_season_labels(seasons or list(DEFAULT_WNBA_INGEST_SEASONS))
    games_upserted = 0
    feature_rows = 0
    player_stubs = 0
    details_fetched = 0
    per_season: Dict[str, int] = {}
    source_used: Dict[str, str] = {}
    try:
        ensure_wnba_model_tables(session)
        for season in season_labels:
            paired = fetch_season_schedule_data_wnba(season)
            source = "data.wnba.com/schedule"
            source_used[season] = source
            rest_map = compute_rest_days_by_team(paired)
            count = 0
            for g in paired:
                if not upsert_wnba_game_ingest(session, g):
                    continue
                games_upserted += 1
                count += 1
            per_season[season] = count
            session.commit()

            if enrich_details and paired:
                try:
                    season_year = season_label_to_start_year(season)
                except ValueError:
                    season_year = None
                finals = [
                    g
                    for g in paired
                    if str(g.get("status") or "").lower().startswith("final")
                    and g.get("home_score") is not None
                ]
                for g in finals:
                    if details_fetched >= int(max_detail_games):
                        break
                    if season_year is None:
                        break
                    gid = str(g["external_game_id"])
                    detail = fetch_game_detail_data_wnba(season_year, gid)
                    details_fetched += 1
                    if not detail:
                        time_module.sleep(sleep_s)
                        continue
                    home_block = detail.get("hls") or {}
                    away_block = detail.get("vls") or {}
                    home_feat = features_from_data_wnba_team_stats(home_block)
                    away_feat = features_from_data_wnba_team_stats(away_block)
                    if home_feat and away_feat:
                        home_feat["drtg"] = away_feat.get("ortg")
                        away_feat["drtg"] = home_feat.get("ortg")
                    try:
                        gd = date.fromisoformat(str(g["game_date"])[:10])
                    except Exception:
                        time_module.sleep(sleep_s)
                        continue
                    home_key = normalize_team_key(
                        str(home_block.get("ta") or g.get("home_team_key") or "")
                    )
                    away_key = normalize_team_key(
                        str(away_block.get("ta") or g.get("away_team_key") or "")
                    )
                    for team_key, feat, is_home, opp in (
                        (home_key, home_feat, True, away_key),
                        (away_key, away_feat, False, home_key),
                    ):
                        if not team_key or team_key == "UNK" or not feat:
                            continue
                        upsert_wnba_team_game_features(
                            session,
                            external_game_id=gid,
                            team_key=team_key,
                            game_date_val=gd,
                            is_home=is_home,
                            opponent_key=opp,
                            feat=feat,
                            rest_days=rest_map.get((gid, team_key)),
                            season=season,
                            source="data.wnba.com/gamedetail",
                        )
                        feature_rows += 1
                    if details_fetched <= int(player_stub_details):
                        for stub in player_stubs_from_data_wnba_detail(detail):
                            if not stub.get("player_id"):
                                continue
                            session.execute(
                                text(
                                    """
                                    INSERT INTO wnba_player_game_stubs (
                                      external_game_id, player_id, player_name, team_key,
                                      game_date, minutes, usage_proxy, pts, reb, ast, fg3m,
                                      fga, fta, tov, source, payload, updated_at
                                    ) VALUES (
                                      :external_game_id, :player_id, :player_name, :team_key,
                                      :game_date, :minutes, :usage_proxy, :pts, :reb, :ast, :fg3m,
                                      :fga, :fta, :tov, :source, CAST(:payload AS jsonb), :updated_at
                                    )
                                    ON CONFLICT (external_game_id, player_id) DO UPDATE SET
                                      minutes = EXCLUDED.minutes,
                                      usage_proxy = EXCLUDED.usage_proxy,
                                      pts = EXCLUDED.pts,
                                      reb = EXCLUDED.reb,
                                      ast = EXCLUDED.ast,
                                      fg3m = EXCLUDED.fg3m,
                                      updated_at = EXCLUDED.updated_at
                                    """
                                ),
                                {
                                    "external_game_id": gid,
                                    "player_id": stub["player_id"],
                                    "player_name": stub.get("player_name"),
                                    "team_key": stub.get("team_key"),
                                    "game_date": gd,
                                    "minutes": stub.get("minutes"),
                                    "usage_proxy": stub.get("usage_proxy"),
                                    "pts": stub.get("pts"),
                                    "reb": stub.get("reb"),
                                    "ast": stub.get("ast"),
                                    "fg3m": stub.get("fg3m"),
                                    "fga": stub.get("fga"),
                                    "fta": stub.get("fta"),
                                    "tov": stub.get("tov"),
                                    "source": "data.wnba.com/gamedetail",
                                    "payload": json.dumps({}),
                                    "updated_at": _now_utc(),
                                },
                            )
                            player_stubs += 1
                    # Commit often so API canaries are not blocked on long txn locks.
                    if details_fetched % 5 == 0:
                        session.commit()
                    time_module.sleep(sleep_s)
        session.commit()
        return {
            "games_upserted": games_upserted,
            "feature_rows": feature_rows,
            "player_stubs": player_stubs,
            "details_fetched": details_fetched,
            "per_season": per_season,
            "source_used": source_used,
            "worker_build_id": WNBA_WORKER_BUILD_ID,
        }
    except Exception:
        session.rollback()
        log.exception("Failed WNBA season ingest")
        raise
    finally:
        session.close()


def materialize_wnba_team_rolling_features(
    days_back: int = 45,
    window_games: int = 10,
) -> Dict[str, Any]:
    session = SessionLocal()
    teams_updated = 0
    try:
        ensure_wnba_model_tables(session)
        as_of = date.today()
        start = as_of - timedelta(days=max(1, days_back))
        rows = session.execute(
            text(
                """
                SELECT team_key, game_date, pace, ortg, drtg, three_pt_rate, three_pt_pct,
                       two_pt_pct, ft_rate, ft_pct, to_rate, orb_rate
                FROM wnba_team_game_features
                WHERE game_date >= :start AND game_date <= :as_of
                ORDER BY team_key, game_date DESC
                """
            ),
            {"start": start, "as_of": as_of},
        ).fetchall()
        by_team: Dict[str, List[Dict[str, Any]]] = {}
        for r in rows:
            m = dict(r._mapping)
            by_team.setdefault(str(m["team_key"]), []).append(m)
        for team_key, samples in by_team.items():
            window = samples[: max(1, window_games)]
            avg = rolling_average_features(window)
            session.execute(
                text(
                    """
                    INSERT INTO wnba_team_rolling_features (
                      team_key, as_of_date, window_games,
                      pace, ortg, drtg, three_pt_rate, three_pt_pct,
                      two_pt_pct, ft_rate, ft_pct, to_rate, orb_rate,
                      sample_games, feature_pack_version, payload, updated_at
                    ) VALUES (
                      :team_key, :as_of_date, :window_games,
                      :pace, :ortg, :drtg, :three_pt_rate, :three_pt_pct,
                      :two_pt_pct, :ft_rate, :ft_pct, :to_rate, :orb_rate,
                      :sample_games, :feature_pack_version, CAST(:payload AS jsonb), :updated_at
                    )
                    ON CONFLICT (team_key, as_of_date, window_games) DO UPDATE SET
                      pace = EXCLUDED.pace,
                      ortg = EXCLUDED.ortg,
                      drtg = EXCLUDED.drtg,
                      three_pt_rate = EXCLUDED.three_pt_rate,
                      three_pt_pct = EXCLUDED.three_pt_pct,
                      two_pt_pct = EXCLUDED.two_pt_pct,
                      ft_rate = EXCLUDED.ft_rate,
                      ft_pct = EXCLUDED.ft_pct,
                      to_rate = EXCLUDED.to_rate,
                      orb_rate = EXCLUDED.orb_rate,
                      sample_games = EXCLUDED.sample_games,
                      feature_pack_version = EXCLUDED.feature_pack_version,
                      payload = EXCLUDED.payload,
                      updated_at = EXCLUDED.updated_at
                    """
                ),
                {
                    "team_key": team_key,
                    "as_of_date": as_of,
                    "window_games": window_games,
                    "pace": avg["pace"],
                    "ortg": avg["ortg"],
                    "drtg": avg["drtg"],
                    "three_pt_rate": avg["three_pt_rate"],
                    "three_pt_pct": avg["three_pt_pct"],
                    "two_pt_pct": avg["two_pt_pct"],
                    "ft_rate": avg["ft_rate"],
                    "ft_pct": avg["ft_pct"],
                    "to_rate": avg["to_rate"],
                    "orb_rate": avg["orb_rate"],
                    "sample_games": len(window),
                    "feature_pack_version": "wnba-rolling-gamelog-v1",
                    "payload": json.dumps({"n": len(window), "source": "team_game_features"}),
                    "updated_at": _now_utc(),
                },
            )
            teams_updated += 1
        session.commit()
        return {
            "teams_updated": teams_updated,
            "feature_pack_version": "wnba-rolling-gamelog-v1",
            "worker_build_id": WNBA_WORKER_BUILD_ID,
        }
    except Exception:
        session.rollback()
        log.exception("Failed materializing WNBA rolling features")
        raise
    finally:
        session.close()


def pull_wnba_context_snapshot(days_ahead: int = 3) -> Dict[str, int]:
    session = SessionLocal()
    updated = 0
    try:
        ensure_wnba_model_tables(session)
        try:
            pull_wnba_schedule_ingest(days_back=2, days_ahead=days_ahead)
        except Exception:
            log.warning("WNBA schedule ingest soft-failed inside context snapshot")

        end = date.today() + timedelta(days=max(0, days_ahead))
        games = session.execute(
            text(
                """
                SELECT
                  g.id AS game_id,
                  home.abbr AS home_abbr,
                  away.abbr AS away_abbr,
                  home.name AS home_team,
                  away.name AS away_team,
                  g.game_date
                FROM games g
                JOIN seasons s ON s.id = g.season_id
                JOIN leagues l ON l.id = s.league_id
                JOIN teams home ON home.id = g.home_team_id
                JOIN teams away ON away.id = g.away_team_id
                WHERE l.code = 'wnba'
                  AND g.game_date >= :today
                  AND g.game_date <= :end
                """
            ),
            {"today": date.today(), "end": end},
        ).fetchall()

        if not games:
            games = session.execute(
                text(
                    """
                    SELECT
                      external_game_id AS game_id,
                      home_team_key AS home_abbr,
                      away_team_key AS away_abbr,
                      home_team_key AS home_team,
                      away_team_key AS away_team,
                      game_date
                    FROM wnba_games_ingest
                    WHERE game_date >= :today AND game_date <= :end
                    """
                ),
                {"today": date.today(), "end": end},
            ).fetchall()

        as_of = date.today()
        for r in games:
            m = dict(r._mapping)
            home_key = normalize_team_key(str(m.get("home_abbr") or m.get("home_team") or ""))
            away_key = normalize_team_key(str(m.get("away_abbr") or m.get("away_team") or ""))

            def _feat(team_key: str) -> Dict[str, Any]:
                row = session.execute(
                    text(
                        """
                        SELECT *
                        FROM wnba_team_rolling_features
                        WHERE team_key = :team_key
                          AND as_of_date <= :as_of
                        ORDER BY as_of_date DESC
                        LIMIT 1
                        """
                    ),
                    {"team_key": team_key, "as_of": as_of},
                ).fetchone()
                return dict(row._mapping) if row else {}

            hf = _feat(home_key)
            af = _feat(away_key)

            def _rest_days(team_key: str, before: Any) -> float:
                try:
                    before_d = (
                        before
                        if isinstance(before, date)
                        else date.fromisoformat(str(before)[:10])
                    )
                except Exception:
                    return 2.0
                prev = session.execute(
                    text(
                        """
                        SELECT MAX(game_date)
                        FROM wnba_games_ingest
                        WHERE game_date < :before
                          AND (home_team_key = :team OR away_team_key = :team)
                        """
                    ),
                    {"before": before_d, "team": team_key},
                ).fetchone()
                if not prev or prev[0] is None:
                    return 2.0
                return float((before_d - prev[0]).days)

            rest_home = _rest_days(home_key, m.get("game_date") or as_of)
            rest_away = _rest_days(away_key, m.get("game_date") or as_of)
            pack = (
                hf.get("feature_pack_version")
                or af.get("feature_pack_version")
                or ("wnba-rolling-gamelog-v1" if hf or af else "wnba-league-avg-v0")
            )
            session.execute(
                text(
                    """
                    INSERT INTO wnba_game_context (
                      game_id, pace_home, pace_away, ortg_home, ortg_away,
                      drtg_home, drtg_away, three_pt_rate_home, three_pt_rate_away,
                      three_pt_pct_home, three_pt_pct_away,
                      rest_days_home, rest_days_away,
                      sample_games_home, sample_games_away,
                      feature_pack_version, context, updated_at
                    ) VALUES (
                      :game_id, :pace_home, :pace_away, :ortg_home, :ortg_away,
                      :drtg_home, :drtg_away, :three_pt_rate_home, :three_pt_rate_away,
                      :three_pt_pct_home, :three_pt_pct_away,
                      :rest_days_home, :rest_days_away,
                      :sample_games_home, :sample_games_away,
                      :feature_pack_version, CAST(:context AS jsonb), :updated_at
                    )
                    ON CONFLICT (game_id) DO UPDATE SET
                      pace_home = EXCLUDED.pace_home,
                      pace_away = EXCLUDED.pace_away,
                      ortg_home = EXCLUDED.ortg_home,
                      ortg_away = EXCLUDED.ortg_away,
                      drtg_home = EXCLUDED.drtg_home,
                      drtg_away = EXCLUDED.drtg_away,
                      three_pt_rate_home = EXCLUDED.three_pt_rate_home,
                      three_pt_rate_away = EXCLUDED.three_pt_rate_away,
                      three_pt_pct_home = EXCLUDED.three_pt_pct_home,
                      three_pt_pct_away = EXCLUDED.three_pt_pct_away,
                      rest_days_home = EXCLUDED.rest_days_home,
                      rest_days_away = EXCLUDED.rest_days_away,
                      sample_games_home = EXCLUDED.sample_games_home,
                      sample_games_away = EXCLUDED.sample_games_away,
                      feature_pack_version = EXCLUDED.feature_pack_version,
                      context = EXCLUDED.context,
                      updated_at = EXCLUDED.updated_at
                    """
                ),
                {
                    "game_id": str(m["game_id"]),
                    "pace_home": _to_float(hf.get("pace")) or WNBA_LEAGUE_PACE,
                    "pace_away": _to_float(af.get("pace")) or WNBA_LEAGUE_PACE,
                    "ortg_home": _to_float(hf.get("ortg")) or WNBA_LEAGUE_ORTG,
                    "ortg_away": _to_float(af.get("ortg")) or WNBA_LEAGUE_ORTG,
                    "drtg_home": _to_float(hf.get("drtg")) or WNBA_LEAGUE_DRTG,
                    "drtg_away": _to_float(af.get("drtg")) or WNBA_LEAGUE_DRTG,
                    "three_pt_rate_home": _to_float(hf.get("three_pt_rate")) or 0.34,
                    "three_pt_rate_away": _to_float(af.get("three_pt_rate")) or 0.34,
                    "three_pt_pct_home": _to_float(hf.get("three_pt_pct")) or 0.34,
                    "three_pt_pct_away": _to_float(af.get("three_pt_pct")) or 0.34,
                    "rest_days_home": rest_home,
                    "rest_days_away": rest_away,
                    "sample_games_home": _to_float(hf.get("sample_games")) or 0,
                    "sample_games_away": _to_float(af.get("sample_games")) or 0,
                    "feature_pack_version": pack,
                    "context": json.dumps(
                        {
                            "home_team": m.get("home_team"),
                            "away_team": m.get("away_team"),
                            "home_abbr": home_key,
                            "away_abbr": away_key,
                            "rest_days_home": rest_home,
                            "rest_days_away": rest_away,
                            "pace_method": "harmonic_mean",
                            "ratings_source": "wnba_team_rolling_features"
                            if (hf or af)
                            else "league_avg",
                        }
                    ),
                    "updated_at": _now_utc(),
                },
            )
            updated += 1
        session.commit()
        return {"games_context_updated": updated}
    except Exception:
        session.rollback()
        log.exception("Failed WNBA context snapshot")
        raise
    finally:
        session.close()


def run_wnba_market_simulations(
    game_date: Optional[str] = None,
    simulations: int = 4000,
    model_version: str = DEFAULT_WNBA_MODEL_VERSION,
) -> Dict[str, Any]:
    worker_build_id = WNBA_WORKER_BUILD_ID
    if game_date:
        try:
            target_date = date.fromisoformat(game_date)
        except ValueError as e:
            raise ValueError(f"game_date must be YYYY-MM-DD, got {game_date}") from e
    else:
        target_date = date.today()

    session = SessionLocal()
    processed = 0
    inserted = 0
    try:
        ensure_wnba_model_tables(session)
        session.commit()
        rows = session.execute(
            text(
                """
                SELECT
                  g.id AS game_id,
                  g.game_date,
                  g.status AS game_status,
                  home.name AS home_team,
                  away.name AS away_team,
                  home.abbr AS home_abbr,
                  away.abbr AS away_abbr,
                  c.pace_home, c.pace_away,
                  c.ortg_home, c.ortg_away,
                  c.drtg_home, c.drtg_away,
                  c.three_pt_rate_home, c.three_pt_rate_away,
                  c.three_pt_pct_home, c.three_pt_pct_away,
                  c.rest_days_home, c.rest_days_away,
                  c.sample_games_home, c.sample_games_away,
                  c.feature_pack_version,
                  c.context
                FROM games g
                JOIN seasons s ON s.id = g.season_id
                JOIN leagues l ON l.id = s.league_id
                JOIN teams home ON home.id = g.home_team_id
                JOIN teams away ON away.id = g.away_team_id
                LEFT JOIN wnba_game_context c ON c.game_id = g.id::text
                WHERE l.code = 'wnba'
                  AND g.game_date = :game_date
                ORDER BY g.start_time NULLS LAST
                """
            ),
            {"game_date": target_date},
        ).fetchall()

        if not rows:
            rows = session.execute(
                text(
                    """
                    SELECT
                      i.external_game_id AS game_id,
                      i.game_date,
                      i.status AS game_status,
                      COALESCE(i.home_team_key, 'Home') AS home_team,
                      COALESCE(i.away_team_key, 'Away') AS away_team,
                      i.home_team_key AS home_abbr,
                      i.away_team_key AS away_abbr,
                      c.pace_home, c.pace_away,
                      c.ortg_home, c.ortg_away,
                      c.drtg_home, c.drtg_away,
                      c.three_pt_rate_home, c.three_pt_rate_away,
                      c.three_pt_pct_home, c.three_pt_pct_away,
                      c.rest_days_home, c.rest_days_away,
                      c.sample_games_home, c.sample_games_away,
                      c.feature_pack_version,
                      c.context
                    FROM wnba_games_ingest i
                    LEFT JOIN wnba_game_context c ON c.game_id = i.external_game_id
                    WHERE i.game_date = :game_date
                    """
                ),
                {"game_date": target_date},
            ).fetchall()

        for r in rows:
            m = dict(r._mapping)
            status = str(m.get("game_status") or "").strip().lower()
            if status in {"final", "closed", "completed"}:
                continue
            gd = m.get("game_date")
            market = wnba_market_lines_for_game(
                session,
                str(m["game_id"]),
                game_date=gd if isinstance(gd, date) else target_date,
                home_team_key=str(m.get("home_abbr") or m.get("home_team") or ""),
                away_team_key=str(m.get("away_abbr") or m.get("away_team") or ""),
            )
            inputs = WnbaGameInputs(
                game_id=str(m["game_id"]),
                home_team=str(m.get("home_team") or "Home"),
                away_team=str(m.get("away_team") or "Away"),
                pace_home=_to_float(m.get("pace_home")) or WNBA_LEAGUE_PACE,
                pace_away=_to_float(m.get("pace_away")) or WNBA_LEAGUE_PACE,
                ortg_home=_to_float(m.get("ortg_home")) or WNBA_LEAGUE_ORTG,
                ortg_away=_to_float(m.get("ortg_away")) or WNBA_LEAGUE_ORTG,
                drtg_home=_to_float(m.get("drtg_home")) or WNBA_LEAGUE_DRTG,
                drtg_away=_to_float(m.get("drtg_away")) or WNBA_LEAGUE_DRTG,
                three_pt_rate_home=_to_float(m.get("three_pt_rate_home")) or 0.34,
                three_pt_rate_away=_to_float(m.get("three_pt_rate_away")) or 0.34,
                three_pt_pct_home=_to_float(m.get("three_pt_pct_home")) or 0.34,
                three_pt_pct_away=_to_float(m.get("three_pt_pct_away")) or 0.34,
                rest_days_home=_to_float(m.get("rest_days_home")) or 2.0,
                rest_days_away=_to_float(m.get("rest_days_away")) or 2.0,
                sample_games_home=int(m["sample_games_home"])
                if m.get("sample_games_home") is not None
                else 0,
                sample_games_away=int(m["sample_games_away"])
                if m.get("sample_games_away") is not None
                else 0,
                feature_pack_version=m.get("feature_pack_version"),
                market_spread_home=market.get("market_spread_home"),
                market_total=market.get("market_total"),
            )
            if m.get("ortg_home") is None and m.get("ortg_away") is None:
                defaults = default_league_average_inputs(
                    inputs.game_id, inputs.home_team, inputs.away_team
                )
                inputs = WnbaGameInputs(
                    **{
                        **defaults,
                        "market_spread_home": market.get("market_spread_home"),
                        "market_total": market.get("market_total"),
                    }
                )

            seed = _default_projection_seed(inputs.game_id, model_version, simulations)
            projection = simulate_wnba_game(
                inputs,
                simulations=simulations,
                seed=seed,
                model_version=model_version,
            )
            projection["worker_build_id"] = worker_build_id
            projection.setdefault("diagnostics", {})["worker_build_id"] = worker_build_id
            insert_wnba_projection(session, projection)
            processed += 1
            inserted += 1

        session.commit()
        return {
            "games_processed": processed,
            "projections_inserted": inserted,
            "game_date": str(target_date),
            "model_version": model_version,
            "worker_build_id": worker_build_id,
        }
    except Exception:
        session.rollback()
        log.exception("Failed running WNBA market simulations")
        raise
    finally:
        session.close()


def collect_wnba_db_inventory(session: Any) -> Dict[str, Any]:
    ensure_wnba_model_tables(session)

    def _count(sql: str, params: Optional[Dict[str, Any]] = None) -> int:
        try:
            row = session.execute(text(sql), params or {}).fetchone()
            return int(row[0] or 0) if row else 0
        except Exception as exc:
            log.info("WNBA inventory query soft-failed: %s", str(exc)[:200])
            session.rollback()
            ensure_wnba_model_tables(session)
            return -1

    games_wnba = _count(
        """
        SELECT COUNT(*)
        FROM games g
        JOIN seasons s ON s.id = g.season_id
        JOIN leagues l ON l.id = s.league_id
        WHERE l.code = 'wnba'
        """
    )
    odds_mainline_games = _count(
        """
        SELECT COUNT(DISTINCT g.id)
        FROM odds_snapshots os
        JOIN games g ON g.id = os.game_id
        JOIN seasons s ON s.id = g.season_id
        JOIN leagues l ON l.id = s.league_id
        WHERE l.code = 'wnba'
        """
    )
    odds_rows = _count(
        """
        SELECT COUNT(*)
        FROM odds_snapshots os
        JOIN games g ON g.id = os.game_id
        JOIN seasons s ON s.id = g.season_id
        JOIN leagues l ON l.id = s.league_id
        WHERE l.code = 'wnba'
        """
    )
    return {
        "verified_at": _now_utc().isoformat(),
        "games": {
            "hierarchy_wnba": games_wnba,
            "wnba_games_ingest": _count("SELECT COUNT(*) FROM wnba_games_ingest"),
            "wnba_team_game_features": _count("SELECT COUNT(*) FROM wnba_team_game_features"),
            "wnba_team_rolling_features": _count(
                "SELECT COUNT(*) FROM wnba_team_rolling_features"
            ),
            "wnba_game_context": _count("SELECT COUNT(*) FROM wnba_game_context"),
            "wnba_possessions": _count("SELECT COUNT(*) FROM wnba_possessions"),
            "wnba_player_game_stubs": _count("SELECT COUNT(*) FROM wnba_player_game_stubs"),
            "wnba_player_prop_model_edges": _count(
                "SELECT COUNT(*) FROM wnba_player_prop_model_edges"
            ),
            "wnba_market_projections": _count("SELECT COUNT(*) FROM wnba_market_projections"),
        },
        "odds": {
            "mainline_games": odds_mainline_games,
            "odds_snapshot_rows": odds_rows,
            "note": (
                "mainline_games = DISTINCT games with odds_snapshots joined via "
                "leagues.code='wnba'."
            ),
        },
        "worker_build_id": WNBA_WORKER_BUILD_ID,
    }


def wnba_db_inventory() -> Dict[str, Any]:
    session = SessionLocal()
    try:
        inv = collect_wnba_db_inventory(session)
        session.commit()
        return inv
    finally:
        session.close()


def repair_wnba_odds_team_abbrs() -> Dict[str, Any]:
    session = SessionLocal()
    updated = 0
    scanned = 0
    try:
        rows = session.execute(
            text(
                """
                SELECT t.id, t.name, t.abbr
                FROM teams t
                JOIN leagues l ON l.id = t.league_id
                WHERE l.code = 'wnba'
                """
            )
        ).fetchall()
        for r in rows:
            scanned += 1
            m = dict(r._mapping)
            canon = normalize_team_key(str(m.get("name") or ""))
            if not canon or canon == "UNK":
                continue
            old = str(m.get("abbr") or "").upper()
            if old == canon:
                continue
            session.execute(
                text("UPDATE teams SET abbr = :abbr WHERE id = CAST(:id AS uuid)"),
                {"abbr": canon, "id": str(m["id"])},
            )
            updated += 1
        session.commit()
        return {
            "status": "ok",
            "scanned": scanned,
            "updated": updated,
            "worker_build_id": WNBA_WORKER_BUILD_ID,
            "canonical_name_map_size": len(WNBA_TEAM_ABBREV),
        }
    except Exception:
        session.rollback()
        log.exception("Failed repair_wnba_odds_team_abbrs")
        raise
    finally:
        session.close()


def pull_wnba_historical_odds_densify(
    *,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    bookmakers: str = "draftkings,fanduel",
    markets: str = "h2h,spreads,totals",
    max_requests: int = 160,
    max_credit_spend: int = 200000,
    min_remaining_floor: int = 1500000,
    open_hour_utc: int = 16,
    close_hour_utc: int = 23,
    skip_if_mainline_games_ge: int = 80,
) -> Dict[str, Any]:
    """Targeted WNBA historical open+close densify with hard credit budget."""
    from src.services.odds_api import fetch_odds_with_metadata
    from src import tasks as tasks_mod

    session = SessionLocal()
    sport_key = "basketball_wnba"
    endpoint = f"historical/sports/{sport_key}/odds"
    try:
        ensure_wnba_model_tables(session)
        tasks_mod._ensure_odds_api_request_tables(session)
        inv_before = collect_wnba_db_inventory(session)
        mainline_before = int(inv_before.get("odds", {}).get("mainline_games") or 0)
        if mainline_before >= int(skip_if_mainline_games_ge):
            return {
                "status": "skipped_already_owned",
                "mainline_games_before": mainline_before,
                "skip_if_mainline_games_ge": skip_if_mainline_games_ge,
                "inventory_before": inv_before,
                "credits_spent_estimate": 0,
            }

        end = date.fromisoformat(end_date) if end_date else date(2025, 10, 20)
        start = date.fromisoformat(start_date) if start_date else date(2023, 5, 19)
        date_rows = session.execute(
            text(
                """
                SELECT DISTINCT game_date
                FROM wnba_games_ingest
                WHERE game_date >= :start
                  AND game_date <= :end
                  AND game_date IS NOT NULL
                ORDER BY game_date DESC
                """
            ),
            {"start": start, "end": end},
        ).fetchall()
        game_dates = [r[0] for r in date_rows if isinstance(r[0], date)]

        normalized_books = tasks_mod._normalize_bookmakers_csv(bookmakers)
        normalized_markets = tasks_mod._normalize_markets_csv(markets)
        credits_per_request = 10 * max(1, len(normalized_markets.split(",")))
        max_req_by_budget = max(1, int(max_credit_spend) // max(1, credits_per_request))
        max_req = min(int(max_requests), max_req_by_budget)

        selected: List[datetime] = []
        for gd in game_dates:
            if len(selected) >= max_req:
                break
            for hour in (int(open_hour_utc), int(close_hour_utc)):
                selected.append(
                    datetime.combine(gd, time(hour=hour, minute=0), tzinfo=timezone.utc)
                )
                if len(selected) >= max_req:
                    break

        requested = 0
        skipped_cached = 0
        request_errors = 0
        events_total = 0
        persisted_total = 0
        snapshots_total = 0
        credits_remaining = None
        credits_spent_est = 0
        stopped_for_floor = False

        for snapshot_dt in selected:
            if credits_remaining is not None and credits_remaining <= int(min_remaining_floor):
                stopped_for_floor = True
                break
            if credits_spent_est >= int(max_credit_spend):
                break
            params: Dict[str, Any] = {
                "bookmakers": normalized_books,
                "markets": normalized_markets,
                "oddsFormat": "american",
                "dateFormat": "iso",
                "date": snapshot_dt.isoformat().replace("+00:00", "Z"),
            }
            signature = tasks_mod._odds_request_signature(endpoint, params)
            cache_row = session.execute(
                text(
                    """
                    SELECT status
                    FROM odds_api_request_cache
                    WHERE request_signature = :request_signature
                    LIMIT 1
                    """
                ),
                {"request_signature": signature},
            ).fetchone()
            if cache_row is not None and str(cache_row[0]) == "success":
                skipped_cached += 1
                continue
            requested += 1
            try:
                payload_meta = fetch_odds_with_metadata(endpoint=endpoint, params=params)
                payload = payload_meta.get("payload")
                credits_remaining = _to_int_like(payload_meta.get("x_requests_remaining"))
                last = _to_int_like(payload_meta.get("x_requests_last")) or credits_per_request
                credits_spent_est += int(last)
                events = payload.get("data") if isinstance(payload, dict) else None
                events_list = events if isinstance(events, list) else []
                for event in events_list:
                    if isinstance(event, dict) and not event.get("sport_key"):
                        event["sport_key"] = sport_key
                persisted = tasks_mod._persist_odds_events(
                    session,
                    events=events_list,
                    source_label="the-odds-api-historical-wnba-mainlines",
                )
                events_total += len(events_list)
                persisted_total += int(persisted.get("events_persisted") or 0)
                snapshots_total += int(persisted.get("snapshots_inserted") or 0)
                tasks_mod._record_odds_api_request(
                    session,
                    endpoint=endpoint,
                    sport_key=sport_key,
                    request_signature=signature,
                    request_params=params,
                    status="success",
                    source_key=str(payload_meta.get("source") or ""),
                    credits_last=_to_int_like(payload_meta.get("x_requests_last")),
                    credits_used=_to_int_like(payload_meta.get("x_requests_used")),
                    credits_remaining=credits_remaining,
                    events_count=len(events_list),
                    response_timestamp=tasks_mod._parse_iso_datetime(payload.get("timestamp"))
                    if isinstance(payload, dict)
                    else None,
                    response_previous_timestamp=tasks_mod._parse_iso_datetime(
                        payload.get("previous_timestamp")
                    )
                    if isinstance(payload, dict)
                    else None,
                    response_next_timestamp=tasks_mod._parse_iso_datetime(payload.get("next_timestamp"))
                    if isinstance(payload, dict)
                    else None,
                    error=None,
                )
                session.commit()
                time_module.sleep(0.30)
            except Exception as exc:
                request_errors += 1
                session.rollback()
                try:
                    tasks_mod._record_odds_api_request(
                        session,
                        endpoint=endpoint,
                        sport_key=sport_key,
                        request_signature=signature,
                        request_params=params,
                        status="failed",
                        source_key=None,
                        credits_last=None,
                        credits_used=None,
                        credits_remaining=None,
                        events_count=0,
                        response_timestamp=None,
                        response_previous_timestamp=None,
                        response_next_timestamp=None,
                        error=str(exc)[:1000],
                    )
                    session.commit()
                except Exception:
                    session.rollback()
                log.exception("WNBA historical densify request failed")

        inv_after = collect_wnba_db_inventory(session)
        session.commit()
        return {
            "status": "ok" if request_errors == 0 else "partial",
            "sport_key": sport_key,
            "markets": normalized_markets.split(","),
            "bookmakers": normalized_books.split(","),
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "game_dates_available": len(game_dates),
            "requests_attempted": requested,
            "skipped_cached": skipped_cached,
            "request_errors": request_errors,
            "events_total": events_total,
            "events_persisted": persisted_total,
            "snapshots_inserted": snapshots_total,
            "credits_spent_estimate": credits_spent_est,
            "credits_remaining": credits_remaining,
            "max_credit_spend": max_credit_spend,
            "min_remaining_floor": min_remaining_floor,
            "stopped_for_floor": stopped_for_floor,
            "mainline_games_before": mainline_before,
            "mainline_games_after": int(inv_after.get("odds", {}).get("mainline_games") or 0),
            "inventory_before": inv_before,
            "inventory_after": inv_after,
            "worker_build_id": WNBA_WORKER_BUILD_ID,
        }
    except Exception:
        session.rollback()
        log.exception("Failed WNBA historical odds densify")
        raise
    finally:
        session.close()


def run_wnba_walkforward_sample(
    *,
    limit_games: int = 60,
    simulations: int = 800,
    model_version: str = DEFAULT_WNBA_MODEL_VERSION,
    prefer_odds_window: bool = True,
    apply_market_blend: bool = True,
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        ensure_wnba_model_tables(session)
        odds_window_sql = ""
        if prefer_odds_window:
            odds_window_sql = """
                  AND i.game_date >= DATE '2023-05-19'
                  AND i.game_date <= DATE '2025-10-20'
            """
        rows = session.execute(
            text(
                f"""
                SELECT
                  i.external_game_id AS game_id,
                  i.game_date,
                  i.home_team_key,
                  i.away_team_key,
                  i.home_score,
                  i.away_score,
                  hf.pace AS pace_home,
                  af.pace AS pace_away,
                  hf.ortg AS ortg_home,
                  af.ortg AS ortg_away,
                  hf.drtg AS drtg_home,
                  af.drtg AS drtg_away,
                  hf.three_pt_rate AS three_pt_rate_home,
                  af.three_pt_rate AS three_pt_rate_away,
                  hf.three_pt_pct AS three_pt_pct_home,
                  af.three_pt_pct AS three_pt_pct_away,
                  hf.rest_days AS rest_days_home,
                  af.rest_days AS rest_days_away
                FROM wnba_games_ingest i
                LEFT JOIN wnba_team_game_features hf
                  ON hf.external_game_id = i.external_game_id
                 AND hf.team_key = i.home_team_key
                LEFT JOIN wnba_team_game_features af
                  ON af.external_game_id = i.external_game_id
                 AND af.team_key = i.away_team_key
                WHERE i.home_score IS NOT NULL
                  AND i.away_score IS NOT NULL
                  AND i.game_date IS NOT NULL
                  {odds_window_sql}
                ORDER BY i.game_date DESC
                LIMIT :lim
                """
            ),
            {"lim": max(1, int(limit_games) * 3)},
        ).fetchall()

        wf_rows: List[Any] = []
        join_misses = 0
        scanned = 0
        for r in rows:
            if len(wf_rows) >= int(limit_games):
                break
            m = dict(r._mapping)
            scanned += 1

            def _prior(team_key: str, before: date) -> Dict[str, Any]:
                keys = {
                    *wnba_abbr_match_keys(team_key),
                    normalize_team_key(team_key),
                    str(team_key or "").upper(),
                }
                prior = session.execute(
                    text(
                        """
                        SELECT pace, ortg, drtg, three_pt_rate, three_pt_pct, rest_days
                        FROM wnba_team_game_features
                        WHERE team_key = ANY(CAST(:teams AS text[]))
                          AND game_date < :before
                        ORDER BY game_date DESC
                        LIMIT 10
                        """
                    ),
                    {"teams": sorted(k for k in keys if k), "before": before},
                ).fetchall()
                samples = [dict(x._mapping) for x in prior]
                return rolling_average_features(samples) if samples else {}

            gd = m["game_date"]
            home = normalize_team_key(str(m.get("home_team_key") or ""))
            away = normalize_team_key(str(m.get("away_team_key") or ""))
            if not isinstance(gd, date) or home == "UNK" or away == "UNK":
                continue
            hf = _prior(home, gd)
            af = _prior(away, gd)
            if not hf or not af:
                continue
            market = wnba_market_lines_for_game(
                session,
                str(m["game_id"]),
                game_date=gd,
                home_team_key=home,
                away_team_key=away,
            )
            if market.get("market_spread_home") is None and market.get("market_total") is None:
                join_misses += 1
            inputs = WnbaGameInputs(
                game_id=str(m["game_id"]),
                home_team=home,
                away_team=away,
                pace_home=float(hf.get("pace") or WNBA_LEAGUE_PACE),
                pace_away=float(af.get("pace") or WNBA_LEAGUE_PACE),
                ortg_home=float(hf.get("ortg") or WNBA_LEAGUE_ORTG),
                ortg_away=float(af.get("ortg") or WNBA_LEAGUE_ORTG),
                drtg_home=float(hf.get("drtg") or WNBA_LEAGUE_DRTG),
                drtg_away=float(af.get("drtg") or WNBA_LEAGUE_DRTG),
                three_pt_rate_home=float(hf.get("three_pt_rate") or 0.34),
                three_pt_rate_away=float(af.get("three_pt_rate") or 0.34),
                three_pt_pct_home=float(hf.get("three_pt_pct") or 0.34),
                three_pt_pct_away=float(af.get("three_pt_pct") or 0.34),
                rest_days_home=float(m.get("rest_days_home") or hf.get("rest_days") or 2.0),
                rest_days_away=float(m.get("rest_days_away") or af.get("rest_days") or 2.0),
                sample_games_home=10,
                sample_games_away=10,
                feature_pack_version="wnba-rolling-gamelog-v1",
            )
            if apply_market_blend:
                inputs.market_spread_home = market.get("market_spread_home")
                inputs.market_total = market.get("market_total")
            seed = _default_projection_seed(inputs.game_id, model_version, simulations)
            proj = simulate_wnba_game(
                inputs,
                simulations=simulations,
                seed=seed,
                model_version=model_version,
            )
            markets = proj.get("markets") or {}
            actual_margin = float(m["home_score"]) - float(m["away_score"])
            actual_total = float(m["home_score"]) + float(m["away_score"])
            wf_rows.append(
                WnbaWalkforwardRow(
                    game_id=str(m["game_id"]),
                    game_date=gd,
                    model_spread_home=float(markets.get("fair_spread_home") or 0.0),
                    model_total=float(markets.get("fair_total") or 0.0),
                    close_spread_home=market.get("market_spread_home"),
                    close_total=market.get("market_total"),
                    actual_margin=actual_margin,
                    actual_total=actual_total,
                )
            )

        summary = summarize_walkforward(wf_rows)
        summary["limit_games"] = limit_games
        summary["simulations"] = simulations
        summary["model_version"] = model_version
        summary["worker_build_id"] = WNBA_WORKER_BUILD_ID
        summary["n_with_close_lines"] = sum(
            1
            for r in wf_rows
            if r.close_spread_home is not None or r.close_total is not None
        )
        summary["close_line_join"] = {
            "scanned_candidates": scanned,
            "graded": len(wf_rows),
            "join_misses": join_misses,
            "prefer_odds_window": prefer_odds_window,
            "apply_market_blend": apply_market_blend,
        }
        summary["publish_posture"] = board_publish_posture(
            n_with_close_lines=int(summary["n_with_close_lines"]),
            ats=summary.get("model_vs_close_ats_cover_rate"),
        )
        return summary
    except Exception:
        session.rollback()
        log.exception("Failed WNBA walkforward sample")
        raise
    finally:
        session.close()


def materialize_wnba_player_props_edges(
    *,
    as_of_date: Optional[str] = None,
    lookback_games: int = 8,
    min_minutes: float = 10.0,
    limit_players: int = 200,
) -> Dict[str, Any]:
    from src.services.wnba_player_prop_projection import (
        WNBA_PROP_MODEL_VERSION,
        project_from_stub_groups,
    )
    from src.services.wnba_prop_edge_policy import (
        evaluate_wnba_prop_edge,
        ou_balance_report,
    )

    as_of = date.fromisoformat(as_of_date) if as_of_date else date.today()
    session = SessionLocal()
    try:
        ensure_wnba_model_tables(session)
        session.commit()

        stub_rows = session.execute(
            text(
                """
                SELECT player_id, player_name, team_key, game_date, minutes,
                       usage_proxy, pts, reb, ast, fg3m
                FROM wnba_player_game_stubs
                WHERE game_date IS NOT NULL
                  AND minutes IS NOT NULL
                  AND minutes >= 1
                ORDER BY player_id, game_date DESC
                """
            )
        ).fetchall()

        by_player: Dict[str, List[Dict[str, Any]]] = {}
        for r in stub_rows:
            pid = str(r[0] or "")
            if not pid:
                continue
            bucket = by_player.setdefault(pid, [])
            if len(bucket) >= lookback_games:
                continue
            bucket.append(
                {
                    "player_id": pid,
                    "player_name": r[1],
                    "team_key": r[2],
                    "game_date": r[3],
                    "minutes": r[4],
                    "usage_proxy": r[5],
                    "pts": r[6],
                    "reb": r[7],
                    "ast": r[8],
                    "fg3m": r[9],
                }
            )

        ordered = sorted(
            by_player.values(),
            key=lambda rows: max((x.get("game_date") or date.min) for x in rows),
            reverse=True,
        )[: max(1, int(limit_players))]

        pace_rows = session.execute(
            text(
                """
                SELECT DISTINCT ON (team_key) team_key, pace
                FROM wnba_team_rolling_features
                ORDER BY team_key, as_of_date DESC NULLS LAST, updated_at DESC
                """
            )
        ).fetchall()
        ortg_rows = session.execute(
            text(
                """
                SELECT DISTINCT ON (team_key) team_key, ortg
                FROM wnba_team_rolling_features
                ORDER BY team_key, as_of_date DESC NULLS LAST, updated_at DESC
                """
            )
        ).fetchall()
        pace_map = {str(r[0]).upper(): float(r[1] or WNBA_LEAGUE_PACE) for r in pace_rows if r[0]}
        ortg_map = {str(r[0]).upper(): float(r[1] or WNBA_LEAGUE_ORTG) for r in ortg_rows if r[0]}

        projections = project_from_stub_groups(
            ordered,
            team_pace_by_key=pace_map,
            team_ortg_by_key=ortg_map,
            min_minutes=min_minutes,
        )

        market_by_key: Dict[Tuple[str, str], Dict[str, Any]] = {}
        try:
            mrows = session.execute(
                text(
                    """
                    SELECT DISTINCT ON (player_name, market_key)
                      lower(player_name) AS pname,
                      market_key,
                      line,
                      over_price,
                      under_price
                    FROM player_prop_market_snapshots
                    WHERE sport_key IN ('basketball_wnba', 'wnba')
                      AND market_key IN ('pts', 'reb', 'ast', 'threes')
                    ORDER BY player_name, market_key, captured_at DESC NULLS LAST
                    """
                )
            ).fetchall()
            for mr in mrows:
                market_by_key[(str(mr[0] or ""), str(mr[1] or ""))] = {
                    "line": mr[2],
                    "over_price": mr[3],
                    "under_price": mr[4],
                }
        except Exception:
            session.rollback()
            ensure_wnba_model_tables(session)
            session.commit()
            market_by_key = {}

        upserted = 0
        board_rows: List[Dict[str, Any]] = []
        for proj in projections:
            mkt = market_by_key.get((proj.player_name.lower(), proj.market_key))
            line = None
            over_price = under_price = None
            if mkt:
                try:
                    line = float(mkt["line"]) if mkt.get("line") is not None else None
                except (TypeError, ValueError):
                    line = None
                try:
                    over_price = (
                        int(mkt["over_price"]) if mkt.get("over_price") is not None else None
                    )
                    under_price = (
                        int(mkt["under_price"]) if mkt.get("under_price") is not None else None
                    )
                except (TypeError, ValueError):
                    over_price = under_price = None

            edge = evaluate_wnba_prop_edge(
                market_key=proj.market_key,
                model_mean=proj.model_mean,
                model_std=proj.model_std,
                line=line,
                over_price=over_price,
                under_price=under_price,
                sample_games=proj.sample_games,
                projection_source=proj.projection_source,
            )
            confidence = 0.35 + min(0.45, 0.04 * proj.sample_games)
            if edge.get("market_joined"):
                confidence += 0.1
            diagnostics = {
                "tag": edge.get("tag"),
                "tag_side": edge.get("tag_side"),
                "reason": edge.get("reason"),
                "stake_eligible": False,
                "z": edge.get("z"),
                "projection_source": proj.projection_source,
                "minutes": proj.minutes,
                "usage_proxy": proj.usage_proxy,
                "sample_games": proj.sample_games,
                "policy_version": edge.get("policy_version"),
            }
            session.execute(
                text(
                    """
                    INSERT INTO wnba_player_prop_model_edges (
                      model_version, as_of_date, player_id, player_name, team_key,
                      market_key, line, model_mean, model_std,
                      over_prob, under_prob, fair_over_price, fair_under_price,
                      market_over_price, market_under_price, edge_over, edge_under,
                      confidence, diagnostics, worker_build_id, updated_at
                    ) VALUES (
                      :model_version, :as_of_date, :player_id, :player_name, :team_key,
                      :market_key, :line, :model_mean, :model_std,
                      :over_prob, :under_prob, :fair_over_price, :fair_under_price,
                      :market_over_price, :market_under_price, :edge_over, :edge_under,
                      :confidence, CAST(:diagnostics AS jsonb), :worker_build_id, :updated_at
                    )
                    ON CONFLICT (model_version, as_of_date, player_id, market_key)
                    DO UPDATE SET
                      line = EXCLUDED.line,
                      model_mean = EXCLUDED.model_mean,
                      model_std = EXCLUDED.model_std,
                      over_prob = EXCLUDED.over_prob,
                      under_prob = EXCLUDED.under_prob,
                      fair_over_price = EXCLUDED.fair_over_price,
                      fair_under_price = EXCLUDED.fair_under_price,
                      market_over_price = EXCLUDED.market_over_price,
                      market_under_price = EXCLUDED.market_under_price,
                      edge_over = EXCLUDED.edge_over,
                      edge_under = EXCLUDED.edge_under,
                      confidence = EXCLUDED.confidence,
                      diagnostics = EXCLUDED.diagnostics,
                      worker_build_id = EXCLUDED.worker_build_id,
                      updated_at = EXCLUDED.updated_at
                    """
                ),
                {
                    "model_version": WNBA_PROP_MODEL_VERSION,
                    "as_of_date": as_of,
                    "player_id": proj.player_id,
                    "player_name": proj.player_name,
                    "team_key": proj.team_key,
                    "market_key": proj.market_key,
                    "line": line,
                    "model_mean": proj.model_mean,
                    "model_std": proj.model_std,
                    "over_prob": edge.get("over_prob"),
                    "under_prob": edge.get("under_prob"),
                    "fair_over_price": edge.get("fair_over_price"),
                    "fair_under_price": edge.get("fair_under_price"),
                    "market_over_price": over_price,
                    "market_under_price": under_price,
                    "edge_over": edge.get("edge_over"),
                    "edge_under": edge.get("edge_under"),
                    "confidence": round(confidence, 3),
                    "diagnostics": json.dumps(diagnostics),
                    "worker_build_id": WNBA_WORKER_BUILD_ID,
                    "updated_at": _now_utc(),
                },
            )
            upserted += 1
            board_rows.append(
                {"tag": edge.get("tag"), "tag_side": edge.get("tag_side"), "diagnostics": diagnostics}
            )

        session.commit()
        balance = ou_balance_report(board_rows)
        return {
            "status": "ok",
            "phase": "phase3",
            "worker_build_id": WNBA_WORKER_BUILD_ID,
            "model_version": WNBA_PROP_MODEL_VERSION,
            "as_of_date": as_of.isoformat(),
            "players_considered": len(ordered),
            "edges_upserted": upserted,
            "market_keys_joined": len(market_by_key),
            "ou_balance": balance,
        }
    except Exception:
        session.rollback()
        log.exception("materialize_wnba_player_props_edges failed")
        raise
    finally:
        session.close()


def run_wnba_phase1_bootstrap(
    seasons: Optional[List[str]] = None,
    densify_odds: bool = True,
    max_credit_spend: int = 200000,
    walkforward_games: int = 60,
    max_detail_games: int = 800,
) -> Dict[str, Any]:
    inventory_before = wnba_db_inventory()
    ingest_schedule = pull_wnba_season_ingest(seasons=seasons, enrich_details=False)
    densify: Dict[str, Any] = {"status": "skipped_by_flag"}
    if densify_odds:
        densify = pull_wnba_historical_odds_densify(max_credit_spend=max_credit_spend)
    ingest_details = pull_wnba_season_ingest(
        seasons=seasons,
        enrich_details=True,
        max_detail_games=max_detail_games,
        player_stub_details=min(60, max_detail_games),
    )
    features = materialize_wnba_team_rolling_features(days_back=2000, window_games=10)
    context = pull_wnba_context_snapshot(days_ahead=3)
    walkforward = run_wnba_walkforward_sample(limit_games=walkforward_games)
    inventory_after = wnba_db_inventory()
    return {
        "status": "ok",
        "phase": "phase1",
        "worker_build_id": WNBA_WORKER_BUILD_ID,
        "inventory_before": inventory_before,
        "ingest_schedule": ingest_schedule,
        "ingest_details": ingest_details,
        "features": features,
        "densify": densify,
        "context": context,
        "walkforward": walkforward,
        "inventory_after": inventory_after,
    }


def run_wnba_phase2_calibrate(
    *,
    repair_abbrs: bool = True,
    walkforward_games: int = 60,
    simulations: int = 1000,
    densify_odds: bool = False,
    max_credit_spend: int = 0,
) -> Dict[str, Any]:
    inventory_before = wnba_db_inventory()
    repair: Dict[str, Any] = {"status": "skipped"}
    if repair_abbrs:
        repair = repair_wnba_odds_team_abbrs()
    densify: Dict[str, Any] = {"status": "skipped_by_flag"}
    if densify_odds and max_credit_spend > 0:
        densify = pull_wnba_historical_odds_densify(max_credit_spend=max_credit_spend)
    walkforward = run_wnba_walkforward_sample(
        limit_games=walkforward_games,
        simulations=simulations,
        prefer_odds_window=True,
        apply_market_blend=True,
    )
    raw_diag = run_wnba_walkforward_sample(
        limit_games=min(40, walkforward_games),
        simulations=max(400, simulations // 2),
        prefer_odds_window=True,
        apply_market_blend=False,
    )
    context = pull_wnba_context_snapshot(days_ahead=3)
    try:
        sims = run_wnba_market_simulations(simulations=2000)
    except Exception as exc:
        log.exception("Phase2 calibrate simulations failed (non-fatal)")
        sims = {"status": "error", "error": str(exc)[:500]}
    inventory_after = wnba_db_inventory()
    return {
        "status": "ok",
        "phase": "phase2",
        "worker_build_id": WNBA_WORKER_BUILD_ID,
        "inventory_before": inventory_before,
        "repair_abbrs": repair,
        "densify": densify,
        "walkforward": walkforward,
        "walkforward_raw_no_blend": raw_diag,
        "context": context,
        "simulations": sims,
        "inventory_after": inventory_after,
    }


def run_wnba_phase3_props_bootstrap(
    *,
    lookback_games: int = 8,
    limit_players: int = 200,
) -> Dict[str, Any]:
    inventory_before = wnba_db_inventory()
    props = materialize_wnba_player_props_edges(
        lookback_games=lookback_games,
        limit_players=limit_players,
    )
    inventory_after = wnba_db_inventory()
    return {
        "status": "ok",
        "phase": "phase3",
        "worker_build_id": WNBA_WORKER_BUILD_ID,
        "inventory_before": inventory_before,
        "props": props,
        "inventory_after": inventory_after,
    }


def run_wnba_daily_cycle(
    *,
    days_ahead: int = 3,
    simulations: int = 4000,
    model_version: str = DEFAULT_WNBA_MODEL_VERSION,
) -> Dict[str, Any]:
    features = materialize_wnba_team_rolling_features(
        days_back=int(os.getenv("WNBA_ROLLING_DAYS_BACK", "45")),
        window_games=10,
    )
    context = pull_wnba_context_snapshot(days_ahead=days_ahead)
    games_assembled = int(context.get("games_context_updated") or 0)
    if games_assembled > 0:
        sims = run_wnba_market_simulations(
            simulations=simulations,
            model_version=model_version,
        )
    else:
        sims = {
            "status": "skipped_empty_slate",
            "note": "Offseason / no upcoming games — honest empty, no fake projections",
            "processed": 0,
            "inserted": 0,
        }
    try:
        props = materialize_wnba_player_props_edges()
    except Exception as exc:
        log.exception("Daily cycle props materialize failed (non-fatal)")
        props = {"status": "error", "error": str(exc)[:400]}
    return {
        "status": "ok",
        "phase": "phase3",
        "worker_build_id": WNBA_WORKER_BUILD_ID,
        "features": features,
        "context": context,
        "simulations": sims,
        "props": props,
    }
