from __future__ import annotations

import os
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from src.celery_app import celery_app
from src.db import SessionLocal
from src.services.odds_api import fetch_odds
from src.services.nfl_injury_nowcast import fetch_nfl_injury_nowcast
from src.services.nfl_matchup_features import (
    fetch_latest_matchup_feature_pack,
    matchup_pack_to_sim_input_kwargs,
)
from src.services.nfl_portfolio_optimizer import optimize_nfl_portfolio
from src.services.nfl_player_identity import apply_manual_mapping_resolution
from src.services.nfl_simulator import (
    DEFAULT_NFL_MODEL_VERSION,
    NflGameInputs,
    simulate_nfl_game,
)
from src.services.nfl_totals_calibration import fetch_nfl_totals_calibration

router = APIRouter(prefix="/nfl", tags=["nfl-model"])
MODEL_STATE_KEY = "nfl_active_model"
TASK_EVAL_NFL_PROMOTION = "src.tasks.evaluate_nfl_model_promotion"
TASK_NFL_PLAYER_BASELINES = "src.tasks.materialize_nfl_player_baseline_projections"
TASK_NFL_PLAYER_PROPS = "src.tasks.materialize_nfl_player_props_edges"
TASK_NFL_FANTASY = "src.tasks.materialize_nfl_fantasy_projections"
TASK_NFL_PLAYER_CYCLE = "src.tasks.run_nfl_player_projection_cycle"
TASK_NFL_IDENTITY_REFRESH = "src.tasks.run_nfl_identity_refresh"
TASK_NFL_IDENTITY_MANUAL_RESOLUTIONS = "src.tasks.apply_nfl_identity_manual_resolutions"
TASK_NFL_IDENTITY_QUALITY_SNAPSHOT = "src.tasks.run_nfl_identity_quality_snapshot"


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return float(default)
    try:
        return float(raw)
    except ValueError:
        return float(default)


def _to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _to_int(v: Any) -> Optional[int]:
    if v is None:
        return None


def _time_window_from_start(start_time: Any) -> str:
    if start_time is None:
        return "unknown"
    try:
        dt = start_time
        if isinstance(start_time, str):
            dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        hour = dt.astimezone(timezone.utc).hour
        if hour < 18:
            return "early"
        if hour < 22:
            return "prime"
        return "late"
    except Exception:
        return "unknown"


def _resolve_active_nfl_model_version(session: Any, fallback: str = DEFAULT_NFL_MODEL_VERSION) -> str:
    row = session.execute(
        text(
            """
            SELECT active_model_version
            FROM nfl_model_runtime_state
            WHERE state_key = :state_key
            LIMIT 1
            """
        ),
        {"state_key": MODEL_STATE_KEY},
    ).fetchone()
    if row is None or row[0] is None:
        return fallback
    return str(row[0])
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _normalize_team_key(name: Optional[str]) -> str:
    if not name:
        return ""
    return "".join(ch for ch in name.lower() if ch.isalnum())


def _american_implied_prob(price: Optional[int]) -> Optional[float]:
    if price is None:
        return None
    if price > 0:
        return 100.0 / (price + 100.0)
    if price < 0:
        return abs(price) / (abs(price) + 100.0)
    return None


NFL_EDGE_MIN_QUALITY_DEFAULT = _env_float("NFL_EDGE_MIN_QUALITY_SCORE", 58.0)
NFL_EDGE_MIN_CONFIDENCE_DEFAULT = _env_float("NFL_EDGE_MIN_CONFIDENCE_SCORE", 0.53)
NFL_EDGE_MIN_ML_EDGE_DEFAULT = _env_float("NFL_EDGE_MIN_ML_EDGE_PROB", 0.01)


@router.get("/games")
def nfl_games(game_date: Optional[str] = Query(None)) -> Dict[str, Any]:
    target = date.fromisoformat(game_date) if game_date else date.today()
    session = SessionLocal()
    try:
        rows = session.execute(
            text(
                """
                SELECT
                  g.id AS game_id,
                  g.external_id,
                  g.game_date,
                  g.start_time,
                  g.status,
                  home.name AS home_team,
                  away.name AS away_team,
                  c.offense_index_home,
                  c.offense_index_away,
                  c.defense_index_home,
                  c.defense_index_away,
                  c.rest_days_home,
                  c.rest_days_away
                FROM games g
                JOIN seasons s ON s.id = g.season_id
                JOIN leagues l ON l.id = s.league_id
                JOIN teams home ON home.id = g.home_team_id
                JOIN teams away ON away.id = g.away_team_id
                LEFT JOIN nfl_game_context c ON c.game_id = g.id
                WHERE l.code = 'nfl'
                  AND g.game_date = :game_date
                ORDER BY g.start_time
                """
            ),
            {"game_date": target},
        ).fetchall()
        return {"count": len(rows), "games": [dict(r._mapping) for r in rows]}
    finally:
        session.close()


@router.get("/market-history")
def nfl_market_history(
    game_date: Optional[str] = Query(None),
    market_code: Optional[str] = Query(None, pattern="^(moneyline|total)$"),
    limit: int = Query(500, ge=1, le=5000),
) -> Dict[str, Any]:
    target = date.fromisoformat(game_date) if game_date else date.today()
    session = SessionLocal()
    try:
        rows = session.execute(
            text(
                """
                SELECT
                  g.id AS game_id,
                  g.game_date,
                  home.name AS home_team,
                  away.name AS away_team,
                  mhs.captured_at,
                  mhs.sportsbook_code,
                  mhs.market_code,
                  mhs.home_price,
                  mhs.away_price,
                  mhs.total_points,
                  mhs.over_price,
                  mhs.under_price
                FROM nfl_market_history_snapshots mhs
                JOIN games g ON g.id = mhs.game_id
                JOIN seasons s ON s.id = g.season_id
                JOIN leagues l ON l.id = s.league_id
                JOIN teams home ON home.id = g.home_team_id
                JOIN teams away ON away.id = g.away_team_id
                WHERE l.code = 'nfl'
                  AND g.game_date = :game_date
                  AND (:market_code IS NULL OR mhs.market_code = :market_code)
                ORDER BY g.start_time, mhs.captured_at DESC
                LIMIT :limit
                """
            ),
            {
                "game_date": target,
                "market_code": market_code,
                "limit": limit,
            },
        ).fetchall()
        return {"count": len(rows), "rows": [dict(r._mapping) for r in rows]}
    finally:
        session.close()


@router.get("/features/player-usage")
def nfl_player_usage_features(
    season: int = Query(..., ge=2010, le=2100),
    week: Optional[int] = Query(None, ge=1, le=25),
    team: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=2000),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        rows = session.execute(
            text(
                """
                SELECT
                  season, week, team, player_id, player_name, position,
                  games_played, involvement_plays, targets, receptions,
                  receiving_yards, air_yards, yards_after_catch,
                  rush_attempts, rush_yards, pass_attempts, pass_yards, pass_touchdowns,
                  red_zone_targets, red_zone_carries, goal_to_go_carries,
                  qb_dropbacks, qb_pressures_taken, touchdowns_scored,
                  first_downs_generated, explosive_plays, success_rate,
                  explosive_play_rate, pressure_rate_allowed, epa_per_involvement
                FROM nfl_dp_player_usage_weekly
                WHERE season = :season
                  AND (:week IS NULL OR week = :week)
                  AND (:team IS NULL OR team = :team)
                ORDER BY week DESC, involvement_plays DESC, player_name
                LIMIT :limit
                """
            ),
            {"season": season, "week": week, "team": team, "limit": limit},
        ).fetchall()
        return {"count": len(rows), "rows": [dict(r._mapping) for r in rows]}
    finally:
        session.close()


@router.get("/features/team-situational")
def nfl_team_situational_features(
    season: int = Query(..., ge=2010, le=2100),
    week: Optional[int] = Query(None, ge=1, le=25),
    team: Optional[str] = Query(None),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        rows = session.execute(
            text(
                """
                SELECT
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
                  epa_per_play_offense, epa_per_play_defense_allowed
                FROM nfl_dp_team_situational_weekly
                WHERE season = :season
                  AND (:week IS NULL OR week = :week)
                  AND (:team IS NULL OR team = :team)
                ORDER BY week DESC, team
                """
            ),
            {"season": season, "week": week, "team": team},
        ).fetchall()
        return {"count": len(rows), "rows": [dict(r._mapping) for r in rows]}
    finally:
        session.close()


@router.get("/features/team-rolling")
def nfl_team_rolling_features(
    season: int = Query(..., ge=2010, le=2100),
    week: Optional[int] = Query(None, ge=1, le=25),
    team: Optional[str] = Query(None),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        rows = session.execute(
            text(
                """
                SELECT
                  season, week, team, games_in_window_3, games_in_window_5,
                  off_epa_per_play_3g, off_epa_per_play_5g,
                  def_epa_allowed_per_play_3g, def_epa_allowed_per_play_5g,
                  pressure_rate_allowed_3g, pressure_rate_allowed_5g,
                  pressure_rate_generated_3g, pressure_rate_generated_5g,
                  pass_rate_3g, pass_rate_5g,
                  early_down_pass_rate_3g, early_down_pass_rate_5g,
                  red_zone_td_rate_3g, red_zone_td_rate_5g,
                  success_rate_offense_3g, success_rate_offense_5g,
                  success_rate_defense_allowed_3g, success_rate_defense_allowed_5g
                FROM nfl_dp_team_rolling_features_weekly
                WHERE season = :season
                  AND (:week IS NULL OR week = :week)
                  AND (:team IS NULL OR team = :team)
                ORDER BY week DESC, team
                """
            ),
            {"season": season, "week": week, "team": team},
        ).fetchall()
        return {"count": len(rows), "rows": [dict(r._mapping) for r in rows]}
    finally:
        session.close()


@router.get("/features/matchup-pack")
def nfl_matchup_feature_pack(
    season: int = Query(..., ge=2010, le=2100),
    week: int = Query(..., ge=1, le=25),
    home_team: str = Query(...),
    away_team: str = Query(...),
    top_players: int = Query(6, ge=1, le=12),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        matchup = session.execute(
            text(
                """
                SELECT
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
                  diff_red_zone_td_rate_5g
                FROM nfl_dp_matchup_features_weekly
                WHERE season = :season
                  AND week = :week
                  AND home_team = :home_team
                  AND away_team = :away_team
                LIMIT 1
                """
            ),
            {
                "season": season,
                "week": week,
                "home_team": home_team,
                "away_team": away_team,
            },
        ).fetchone()
        if matchup is None:
            raise HTTPException(
                status_code=404,
                detail="Matchup feature pack not found for requested season/week/teams",
            )

        home_players = session.execute(
            text(
                """
                SELECT
                  season, week, team, player_id, player_name, position,
                  involvement_plays, targets, receptions, receiving_yards,
                  rush_attempts, rush_yards, pass_attempts, pass_yards,
                  red_zone_targets, red_zone_carries,
                  explosive_play_rate, pressure_rate_allowed, epa_per_involvement
                FROM nfl_dp_player_usage_weekly
                WHERE season = :season
                  AND week = :week
                  AND team = :team
                ORDER BY involvement_plays DESC, targets DESC, player_name
                LIMIT :top_players
                """
            ),
            {
                "season": season,
                "week": week,
                "team": home_team,
                "top_players": top_players,
            },
        ).fetchall()

        away_players = session.execute(
            text(
                """
                SELECT
                  season, week, team, player_id, player_name, position,
                  involvement_plays, targets, receptions, receiving_yards,
                  rush_attempts, rush_yards, pass_attempts, pass_yards,
                  red_zone_targets, red_zone_carries,
                  explosive_play_rate, pressure_rate_allowed, epa_per_involvement
                FROM nfl_dp_player_usage_weekly
                WHERE season = :season
                  AND week = :week
                  AND team = :team
                ORDER BY involvement_plays DESC, targets DESC, player_name
                LIMIT :top_players
                """
            ),
            {
                "season": season,
                "week": week,
                "team": away_team,
                "top_players": top_players,
            },
        ).fetchall()

        return {
            "matchup": dict(matchup._mapping),
            "home_top_usage_players": [dict(r._mapping) for r in home_players],
            "away_top_usage_players": [dict(r._mapping) for r in away_players],
            "feature_pack_version": "nfl-v1-matchup-pack",
        }
    finally:
        session.close()


@router.get("/clv-summary")
def nfl_clv_summary(
    model_version: str = Query(DEFAULT_NFL_MODEL_VERSION),
    lookback_days: int = Query(45, ge=7, le=365),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        rows = session.execute(
            text(
                """
                SELECT
                  market_code,
                  COUNT(*)::int AS sample_size,
                  AVG(clv_value)::numeric AS avg_clv,
                  SUM(CASE WHEN clv_value > 0 THEN 1 ELSE 0 END)::int AS positive_clv,
                  SUM(CASE WHEN clv_value <= 0 THEN 1 ELSE 0 END)::int AS non_positive_clv
                FROM nfl_clv_attribution
                WHERE model_version = :model_version
                  AND created_at >= NOW() - make_interval(days => :lookback_days)
                GROUP BY market_code
                ORDER BY market_code
                """
            ),
            {"model_version": model_version, "lookback_days": int(lookback_days)},
        ).fetchall()

        market_stats: Dict[str, Any] = {}
        for row in rows:
            m = dict(row._mapping)
            sample_size = _to_int(m.get("sample_size")) or 0
            positive = _to_int(m.get("positive_clv")) or 0
            hit_rate = (positive / sample_size) if sample_size > 0 else None
            market_stats[str(m.get("market_code"))] = {
                "sample_size": sample_size,
                "avg_clv": _to_float(m.get("avg_clv")),
                "positive_clv": positive,
                "non_positive_clv": _to_int(m.get("non_positive_clv")) or 0,
                "positive_clv_rate": hit_rate,
            }

        return {
            "model_version": model_version,
            "lookback_days": int(lookback_days),
            "markets": market_stats,
        }
    finally:
        session.close()


@router.get("/quality/latest")
def nfl_quality_latest(
    model_version: str = Query(DEFAULT_NFL_MODEL_VERSION),
    pipeline_stage: str = Query("weekly_quality"),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        row = session.execute(
            text(
                """
                SELECT
                  run_date,
                  model_version,
                  pipeline_stage,
                  payload,
                  created_at
                FROM nfl_model_quality_snapshots
                WHERE model_version = :model_version
                  AND pipeline_stage = :pipeline_stage
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"model_version": model_version, "pipeline_stage": pipeline_stage},
        ).fetchone()
        if row is None:
            return {
                "model_version": model_version,
                "pipeline_stage": pipeline_stage,
                "summary": None,
            }
        payload = dict(row._mapping).get("payload") or {}
        return {
            "model_version": str(row.model_version),
            "pipeline_stage": str(row.pipeline_stage),
            "run_date": str(row.run_date),
            "created_at": row.created_at,
            "summary": {
                "sample_size": _to_int(payload.get("sample_size")) or 0,
                "moneyline_brier": _to_float(payload.get("moneyline_brier")),
                "total_mae": _to_float(payload.get("total_mae")),
                "clv_avg": _to_float(payload.get("clv_avg")),
                "clv_positive_rate": _to_float(payload.get("clv_positive_rate")),
                "moneyline_hit_rate": _to_float(payload.get("moneyline_hit_rate")),
                "total_hit_rate": _to_float(payload.get("total_hit_rate")),
                "moneyline_positive_edge_hit_rate": _to_float(payload.get("moneyline_positive_edge_hit_rate")),
                "total_positive_edge_hit_rate": _to_float(payload.get("total_positive_edge_hit_rate")),
            },
            "payload": payload,
        }
    finally:
        session.close()


@router.get("/ops/backtest-runs")
def nfl_backtest_runs(
    limit: int = Query(20, ge=1, le=200),
    model_version: str = Query(DEFAULT_NFL_MODEL_VERSION),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        rows = session.execute(
            text(
                """
                SELECT run_date, model_version, payload, created_at
                FROM nfl_model_backtest_runs
                WHERE model_version = :model_version
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            {"limit": int(limit), "model_version": model_version},
        ).fetchall()
        runs: List[Dict[str, Any]] = []
        for row in rows:
            payload = row.payload if isinstance(row.payload, dict) else {}
            runs.append(
                {
                    "run_date": row.run_date,
                    "created_at": row.created_at,
                    "model_version": row.model_version,
                    "fold_count": _to_int(payload.get("fold_count")) or 0,
                    "sample_size": _to_int(payload.get("sample_size")) or 0,
                    "base_brier_ml": _to_float(payload.get("base_brier_ml")),
                    "calibrated_brier_ml": _to_float(payload.get("calibrated_brier_ml")),
                    "brier_improvement": _to_float(payload.get("brier_improvement")),
                    "base_mae_total_runs": _to_float(payload.get("base_mae_total_runs")),
                    "calibrated_mae_total_runs": _to_float(payload.get("calibrated_mae_total_runs")),
                    "mae_improvement": _to_float(payload.get("mae_improvement")),
                    "leakage_violations": _to_int(payload.get("leakage_violations")) or 0,
                }
            )
        return {"count": len(runs), "runs": runs}
    finally:
        session.close()


@router.get("/ops/backtest-report")
def nfl_backtest_report(
    model_version: str = Query(DEFAULT_NFL_MODEL_VERSION),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        row = session.execute(
            text(
                """
                SELECT run_date, model_version, payload, created_at
                FROM nfl_model_backtest_runs
                WHERE model_version = :model_version
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"model_version": model_version},
        ).fetchone()
        if row is None:
            return {"model_version": model_version, "report": None}
        payload = row.payload if isinstance(row.payload, dict) else {}
        return {
            "model_version": model_version,
            "report": {
                "run_date": row.run_date,
                "created_at": row.created_at,
                "summary": {
                    "fold_count": _to_int(payload.get("fold_count")) or 0,
                    "sample_size": _to_int(payload.get("sample_size")) or 0,
                    "base_brier_ml": _to_float(payload.get("base_brier_ml")),
                    "calibrated_brier_ml": _to_float(payload.get("calibrated_brier_ml")),
                    "brier_improvement": _to_float(payload.get("brier_improvement")),
                    "base_mae_total_runs": _to_float(payload.get("base_mae_total_runs")),
                    "calibrated_mae_total_runs": _to_float(payload.get("calibrated_mae_total_runs")),
                    "mae_improvement": _to_float(payload.get("mae_improvement")),
                    "leakage_violations": _to_int(payload.get("leakage_violations")) or 0,
                },
                "folds": payload.get("folds") if isinstance(payload.get("folds"), list) else [],
            },
        }
    finally:
        session.close()


@router.get("/edges/today")
def nfl_edges_today(
    model_version: Optional[str] = Query(None),
    min_quality_score: float = Query(NFL_EDGE_MIN_QUALITY_DEFAULT, ge=0.0, le=100.0),
    min_confidence_score: float = Query(NFL_EDGE_MIN_CONFIDENCE_DEFAULT, ge=0.0, le=1.0),
    min_ml_edge_prob: float = Query(NFL_EDGE_MIN_ML_EDGE_DEFAULT, ge=0.0, le=0.25),
) -> Dict[str, Any]:
    market_events = fetch_odds(
        endpoint="sports/americanfootball_nfl/odds",
        params={
            "regions": "us",
            "markets": "h2h,totals",
            "oddsFormat": "american",
            "dateFormat": "iso",
        },
    )
    session = SessionLocal()
    try:
        effective_model_version = model_version or _resolve_active_nfl_model_version(session)
        rows = session.execute(
            text(
                """
                SELECT
                  g.id AS game_id,
                  g.start_time,
                  home.name AS home_team,
                  away.name AS away_team,
                  p.home_win_prob,
                  p.total_mean,
                  p.projection,
                  p.created_at
                FROM games g
                JOIN seasons s ON s.id = g.season_id
                JOIN leagues l ON l.id = s.league_id
                JOIN teams home ON home.id = g.home_team_id
                JOIN teams away ON away.id = g.away_team_id
                JOIN LATERAL (
                  SELECT *
                  FROM nfl_market_projections np
                  WHERE np.game_id = g.id
                    AND np.model_version = :model_version
                  ORDER BY np.created_at DESC
                  LIMIT 1
                ) p ON TRUE
                WHERE l.code = 'nfl'
                  AND g.game_date = CURRENT_DATE
                """
            ),
            {"model_version": effective_model_version},
        ).fetchall()
        quality_row = session.execute(
            text(
                """
                SELECT payload
                FROM nfl_model_quality_snapshots
                WHERE model_version = :model_version
                  AND pipeline_stage = 'weekly_quality'
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"model_version": effective_model_version},
        ).fetchone()
    finally:
        session.close()

    quality_payload = dict(quality_row._mapping).get("payload") if quality_row is not None else {}
    quality_payload = quality_payload if isinstance(quality_payload, dict) else {}
    brier = _to_float(quality_payload.get("moneyline_brier")) or 0.28
    mae = _to_float(quality_payload.get("total_mae")) or 8.5
    clv = _to_float(quality_payload.get("clv_avg")) or -0.01
    base_quality = max(
        0.0,
        min(
            100.0,
            100.0
            * (
                0.50 * max(0.0, 1.0 - (brier / 0.35))
                + 0.25 * max(0.0, 1.0 - (mae / 12.0))
                + 0.25 * max(0.0, min(1.0, (clv + 0.03) / 0.08))
            ),
        ),
    )

    projection_by_key = {
        (_normalize_team_key(r.home_team), _normalize_team_key(r.away_team)): dict(r._mapping)
        for r in rows
    }

    candidates: List[Dict[str, Any]] = []
    filtered_reasons: Dict[str, int] = {"quality_score": 0, "confidence_score": 0, "ml_edge_prob": 0}

    for event in market_events if isinstance(market_events, list) else []:
        home_team = str(event.get("home_team") or "")
        away_team = str(event.get("away_team") or "")
        if not home_team or not away_team:
            continue
        proj = projection_by_key.get((_normalize_team_key(home_team), _normalize_team_key(away_team)))
        if proj is None:
            continue

        home_prices: List[int] = []
        away_prices: List[int] = []
        totals: List[float] = []
        for book in event.get("bookmakers") or []:
            for market in book.get("markets") or []:
                if market.get("key") == "h2h":
                    for outcome in market.get("outcomes") or []:
                        if outcome.get("name") == home_team and outcome.get("price") is not None:
                            home_prices.append(int(outcome["price"]))
                        elif outcome.get("name") == away_team and outcome.get("price") is not None:
                            away_prices.append(int(outcome["price"]))
                elif market.get("key") == "totals":
                    for outcome in market.get("outcomes") or []:
                        if outcome.get("name") == "Over" and outcome.get("point") is not None:
                            totals.append(float(outcome["point"]))

        if not home_prices or not away_prices:
            continue

        market_home_ml = int(round(sum(home_prices) / len(home_prices)))
        market_away_ml = int(round(sum(away_prices) / len(away_prices)))
        market_total = round(sum(totals) / len(totals), 2) if totals else None
        home_prob = _to_float(proj.get("home_win_prob"))
        market_home_prob = _american_implied_prob(market_home_ml)
        market_away_prob = _american_implied_prob(market_away_ml)
        no_vig_prob = None
        if market_home_prob is not None and market_away_prob is not None and (market_home_prob + market_away_prob) > 0:
            no_vig_prob = market_home_prob / (market_home_prob + market_away_prob)
        if home_prob is None:
            continue
        edge_prob = home_prob - (no_vig_prob if no_vig_prob is not None else (market_home_prob or 0.5))

        projection_payload = proj.get("projection") if isinstance(proj.get("projection"), dict) else {}
        markets_payload = projection_payload.get("markets") if isinstance(projection_payload, dict) else {}
        markets_payload = markets_payload if isinstance(markets_payload, dict) else {}
        total_p10 = _to_float(markets_payload.get("total_p10"))
        total_p90 = _to_float(markets_payload.get("total_p90"))
        total_band_width = (
            abs((total_p90 or 0.0) - (total_p10 or 0.0))
            if total_p10 is not None and total_p90 is not None
            else 11.0
        )
        market_depth = len(home_prices) + len(totals)
        confidence_score = max(
            0.0,
            min(
                1.0,
                0.58 * min(1.0, abs(home_prob - 0.5) * 2.25)
                + 0.25 * min(1.0, market_depth / 14.0)
                + 0.17 * max(0.0, 1.0 - (total_band_width / 16.0)),
            ),
        )
        quality_score = round(
            max(
                0.0,
                min(
                    100.0,
                    0.56 * base_quality
                    + 25.0 * confidence_score
                    + 14.0 * min(1.0, market_depth / 14.0)
                    + 5.0 * min(1.0, abs(edge_prob) / 0.045),
                ),
            ),
            1,
        )

        if quality_score < min_quality_score:
            filtered_reasons["quality_score"] += 1
            continue
        if confidence_score < min_confidence_score:
            filtered_reasons["confidence_score"] += 1
            continue
        if abs(edge_prob) < min_ml_edge_prob:
            filtered_reasons["ml_edge_prob"] += 1
            continue

        candidates.append(
            {
                "game_id": proj.get("game_id"),
                "start_time": proj.get("start_time"),
                "time_window": _time_window_from_start(proj.get("start_time")),
                "home_team": home_team,
                "away_team": away_team,
                "model_version": effective_model_version,
                "market_home_ml": market_home_ml,
                "market_away_ml": market_away_ml,
                "market_total": market_total,
                "model_home_win_prob": round(home_prob, 4),
                "market_home_prob_no_vig": round(no_vig_prob, 4) if no_vig_prob is not None else None,
                "ml_edge_prob": round(edge_prob, 4),
                "total_mean": _to_float(proj.get("total_mean")),
                "total_band_width": round(total_band_width, 3) if total_band_width is not None else None,
                "market_depth": market_depth,
                "quality_score": quality_score,
                "confidence_score": round(confidence_score, 4),
            }
        )

    candidates = sorted(candidates, key=lambda item: (float(item["quality_score"]), abs(float(item["ml_edge_prob"]))), reverse=True)
    filtered_count = int(sum(filtered_reasons.values()))
    return {
        "model_version": effective_model_version,
        "count": len(candidates),
        "edges": candidates,
        "gating": {
            "min_quality_score": min_quality_score,
            "min_confidence_score": min_confidence_score,
            "min_ml_edge_prob": min_ml_edge_prob,
        },
        "diagnostics": {
            "filtered_count": filtered_count,
            "filtered_reasons": filtered_reasons,
            "base_quality_score": round(base_quality, 2),
        },
    }


@router.post("/simulations/{game_id}")
def run_nfl_simulation(
    game_id: str,
    simulations: int = Query(4000, ge=300, le=30000),
    model_version: str = Query(DEFAULT_NFL_MODEL_VERSION),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        row = session.execute(
            text(
                """
                SELECT
                  g.id AS game_id,
                  s.season_year,
                  home.name AS home_team,
                  away.name AS away_team,
                  c.offense_index_home,
                  c.offense_index_away,
                  c.defense_index_home,
                  c.defense_index_away,
                  c.rest_days_home,
                  c.rest_days_away
                FROM games g
                JOIN seasons s ON s.id = g.season_id
                JOIN leagues l ON l.id = s.league_id
                JOIN teams home ON home.id = g.home_team_id
                JOIN teams away ON away.id = g.away_team_id
                LEFT JOIN nfl_game_context c ON c.game_id = g.id
                WHERE l.code = 'nfl'
                  AND g.id = :game_id
                LIMIT 1
                """
            ),
            {"game_id": game_id},
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="NFL game not found")
        m = dict(row._mapping)
        totals_calibration = fetch_nfl_totals_calibration(
            session,
            model_version=model_version,
            lookback_days=int(float(os.getenv("NFL_TOTALS_CALIBRATION_LOOKBACK_DAYS", "240"))),
        )
        matchup_pack = fetch_latest_matchup_feature_pack(
            session,
            game_id=str(m["game_id"]),
            season_year=_to_int(m.get("season_year")),
            home_team=str(m["home_team"]),
            away_team=str(m["away_team"]),
        )
        injury_nowcast = fetch_nfl_injury_nowcast(
            session,
            season_year=_to_int(m.get("season_year")),
            home_team=str(m["home_team"]),
            away_team=str(m["away_team"]),
        )
        home_nowcast = injury_nowcast.get("home") if isinstance(injury_nowcast.get("home"), dict) else {}
        away_nowcast = injury_nowcast.get("away") if isinstance(injury_nowcast.get("away"), dict) else {}
        matchup_kwargs = matchup_pack_to_sim_input_kwargs(matchup_pack)
        inputs = NflGameInputs(
            game_id=str(m["game_id"]),
            home_team=str(m["home_team"]),
            away_team=str(m["away_team"]),
            offense_index_home=(_to_float(m.get("offense_index_home")) or 1.0)
            * (_to_float(home_nowcast.get("offense_multiplier")) or 1.0),
            offense_index_away=(_to_float(m.get("offense_index_away")) or 1.0)
            * (_to_float(away_nowcast.get("offense_multiplier")) or 1.0),
            defense_index_home=(_to_float(m.get("defense_index_home")) or 1.0)
            * (_to_float(home_nowcast.get("defense_multiplier")) or 1.0),
            defense_index_away=(_to_float(m.get("defense_index_away")) or 1.0)
            * (_to_float(away_nowcast.get("defense_multiplier")) or 1.0),
            rest_days_home=_to_float(m.get("rest_days_home")) or 7.0,
            rest_days_away=_to_float(m.get("rest_days_away")) or 7.0,
            injury_nowcast_confidence_home=_to_float(home_nowcast.get("confidence")),
            injury_nowcast_confidence_away=_to_float(away_nowcast.get("confidence")),
            injury_nowcast_freshness_home_hours=_to_float(home_nowcast.get("freshness_hours")),
            injury_nowcast_freshness_away_hours=_to_float(away_nowcast.get("freshness_hours")),
            injury_nowcast_impact_home=_to_float(home_nowcast.get("impact_score")),
            injury_nowcast_impact_away=_to_float(away_nowcast.get("impact_score")),
            injury_nowcast_offense_multiplier_home=_to_float(home_nowcast.get("offense_multiplier")),
            injury_nowcast_offense_multiplier_away=_to_float(away_nowcast.get("offense_multiplier")),
            injury_nowcast_defense_multiplier_home=_to_float(home_nowcast.get("defense_multiplier")),
            injury_nowcast_defense_multiplier_away=_to_float(away_nowcast.get("defense_multiplier")),
            injury_nowcast_source=str(injury_nowcast.get("source") or "nfl_dp_injuries"),
            injury_nowcast_home_drivers=home_nowcast.get("top_drivers") if isinstance(home_nowcast.get("top_drivers"), list) else [],
            injury_nowcast_away_drivers=away_nowcast.get("top_drivers") if isinstance(away_nowcast.get("top_drivers"), list) else [],
            **matchup_kwargs,
        )
        projection = simulate_nfl_game(
            inputs,
            simulations=simulations,
            model_version=model_version,
            totals_calibration=totals_calibration,
        )
        markets = projection.get("markets") or {}
        session.execute(
            text(
                """
                INSERT INTO nfl_market_projections (
                  game_id, model_version, simulation_count,
                  home_win_prob, away_win_prob, total_mean, spread_home,
                  fair_home_ml, fair_away_ml, projection, created_at
                ) VALUES (
                  :game_id, :model_version, :simulation_count,
                  :home_win_prob, :away_win_prob, :total_mean, :spread_home,
                  :fair_home_ml, :fair_away_ml, CAST(:projection AS jsonb), NOW()
                )
                """
            ),
            {
                "game_id": projection["game_id"],
                "model_version": projection["model_version"],
                "simulation_count": projection["simulation_count"],
                "home_win_prob": markets.get("home_win_prob"),
                "away_win_prob": markets.get("away_win_prob"),
                "total_mean": markets.get("total_mean"),
                "spread_home": markets.get("spread_home"),
                "fair_home_ml": markets.get("fair_home_ml"),
                "fair_away_ml": markets.get("fair_away_ml"),
                "projection": __import__("json").dumps(projection),
            },
        )
        session.commit()
        return projection
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@router.get("/ops/active-model")
def nfl_active_model() -> Dict[str, Any]:
    session = SessionLocal()
    try:
        row = session.execute(
            text(
                """
                SELECT state_key, active_model_version, previous_model_version, reason, metadata, updated_at
                FROM nfl_model_runtime_state
                WHERE state_key = :state_key
                LIMIT 1
                """
            ),
            {"state_key": MODEL_STATE_KEY},
        ).fetchone()
        if row is None:
            return {
                "state_key": MODEL_STATE_KEY,
                "active_model_version": DEFAULT_NFL_MODEL_VERSION,
                "previous_model_version": None,
                "reason": "default",
                "metadata": {},
                "updated_at": None,
            }
        return dict(row._mapping)
    finally:
        session.close()


@router.get("/ops/promotion-events")
def nfl_promotion_events(limit: int = Query(20, ge=1, le=200)) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        rows = session.execute(
            text(
                """
                SELECT
                  id, evaluated_at, champion_model_version, challenger_model_version,
                  lookback_days, auto_promote_requested, auto_promote_enabled,
                  promoted, decision, payload
                FROM nfl_model_promotion_events
                ORDER BY evaluated_at DESC
                LIMIT :limit
                """
            ),
            {"limit": int(limit)},
        ).fetchall()
        return {"count": len(rows), "events": [dict(r._mapping) for r in rows]}
    finally:
        session.close()


@router.post("/ops/evaluate-promotion")
def nfl_trigger_promotion_evaluation(
    challenger_model_version: str = Query(..., min_length=3, max_length=128),
    lookback_days: int = Query(45, ge=7, le=365),
    auto_promote: bool = Query(True),
) -> Dict[str, Any]:
    async_result = celery_app.send_task(
        TASK_EVAL_NFL_PROMOTION,
        kwargs={
            "challenger_model_version": challenger_model_version,
            "lookback_days": int(lookback_days),
            "auto_promote": bool(auto_promote),
        },
    )
    return {
        "task_id": async_result.id,
        "task_name": TASK_EVAL_NFL_PROMOTION,
        "challenger_model_version": challenger_model_version,
        "lookback_days": int(lookback_days),
        "auto_promote": bool(auto_promote),
    }


@router.get("/edges/optimize")
def nfl_optimize_edges(
    model_version: Optional[str] = Query(None),
    bankroll: float = Query(1000.0, ge=50.0, le=500000.0),
    risk_profile: str = Query("balanced", pattern="^(conservative|balanced|aggressive)$"),
    min_quality_score: float = Query(58.0, ge=0.0, le=100.0),
    min_confidence_score: float = Query(0.53, ge=0.0, le=1.0),
    min_ml_edge_prob: float = Query(0.01, ge=0.0, le=0.25),
    max_total_exposure: float = Query(0.10, ge=0.01, le=0.8),
    max_per_game_exposure: float = Query(0.04, ge=0.005, le=0.4),
    max_per_team_exposure: float = Query(0.06, ge=0.005, le=0.4),
    max_per_window_exposure: float = Query(0.08, ge=0.01, le=0.8),
    max_per_player_exposure: float = Query(0.045, ge=0.002, le=0.4),
    max_bet_fraction: float = Query(0.03, ge=0.001, le=0.2),
    correlation_penalty: float = Query(0.35, ge=0.0, le=0.95),
    same_game_player_penalty: float = Query(0.30, ge=0.0, le=0.95),
    qb_wr_correlation_penalty: float = Query(0.45, ge=0.0, le=0.95),
) -> Dict[str, Any]:
    edge_payload = nfl_edges_today(
        model_version=model_version,
        min_quality_score=min_quality_score,
        min_confidence_score=min_confidence_score,
        min_ml_edge_prob=min_ml_edge_prob,
    )
    candidates = edge_payload.get("edges") if isinstance(edge_payload.get("edges"), list) else []
    optimized = optimize_nfl_portfolio(
        candidates=candidates,
        bankroll=bankroll,
        risk_profile=risk_profile,
        max_total_exposure=max_total_exposure,
        max_per_game_exposure=max_per_game_exposure,
        max_per_team_exposure=max_per_team_exposure,
        max_per_window_exposure=max_per_window_exposure,
        max_per_player_exposure=max_per_player_exposure,
        max_bet_fraction=max_bet_fraction,
        correlation_penalty=correlation_penalty,
        same_game_player_penalty=same_game_player_penalty,
        qb_wr_correlation_penalty=qb_wr_correlation_penalty,
    )
    recommendations = optimized.get("recommendations") if isinstance(optimized.get("recommendations"), list) else []
    diagnostics = optimized.get("diagnostics") if isinstance(optimized.get("diagnostics"), dict) else {}

    session = SessionLocal()
    run_id: Optional[str] = None
    try:
        run_row = session.execute(
            text(
                """
                INSERT INTO nfl_portfolio_runs (
                  model_version, risk_profile, bankroll, filters, diagnostics, created_at
                ) VALUES (
                  :model_version, :risk_profile, :bankroll, CAST(:filters AS jsonb), CAST(:diagnostics AS jsonb), NOW()
                )
                RETURNING id
                """
            ),
            {
                "model_version": edge_payload.get("model_version") or DEFAULT_NFL_MODEL_VERSION,
                "risk_profile": risk_profile,
                "bankroll": bankroll,
                "filters": __import__("json").dumps(
                    {
                        "min_quality_score": min_quality_score,
                        "min_confidence_score": min_confidence_score,
                        "min_ml_edge_prob": min_ml_edge_prob,
                        "max_total_exposure": max_total_exposure,
                        "max_per_game_exposure": max_per_game_exposure,
                        "max_per_team_exposure": max_per_team_exposure,
                        "max_per_window_exposure": max_per_window_exposure,
                        "max_per_player_exposure": max_per_player_exposure,
                        "max_bet_fraction": max_bet_fraction,
                        "correlation_penalty": correlation_penalty,
                        "same_game_player_penalty": same_game_player_penalty,
                        "qb_wr_correlation_penalty": qb_wr_correlation_penalty,
                    }
                ),
                "diagnostics": __import__("json").dumps(diagnostics),
            },
        ).fetchone()
        run_id = str(run_row[0]) if run_row is not None else None
        if run_id:
            for rec in recommendations:
                session.execute(
                    text(
                        """
                        INSERT INTO nfl_portfolio_recommendations (
                          run_id, game_id, market, selection, score, edge_value,
                          recommended_stake_fraction, recommended_stake_amount, reason, created_at
                        ) VALUES (
                          :run_id, :game_id, :market, :selection, :score, :edge_value,
                          :recommended_stake_fraction, :recommended_stake_amount, CAST(:reason AS jsonb), NOW()
                        )
                        """
                    ),
                    {
                        "run_id": run_id,
                        "game_id": rec.get("game_id"),
                        "market": "moneyline",
                        "selection": rec.get("selection"),
                        "score": _to_float(rec.get("quality_score")),
                        "edge_value": _to_float(rec.get("ml_edge_prob")),
                        "recommended_stake_fraction": _to_float(rec.get("recommended_stake_fraction")) or 0.0,
                        "recommended_stake_amount": _to_float(rec.get("recommended_stake_amount")) or 0.0,
                        "reason": __import__("json").dumps(
                            {
                                "confidence_score": rec.get("confidence_score"),
                                "time_window": rec.get("time_window"),
                                "market_depth": rec.get("market_depth"),
                            }
                        ),
                    },
                )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    return {
        "model_version": edge_payload.get("model_version"),
        "run_id": run_id,
        "risk_profile": risk_profile,
        "bankroll": bankroll,
        "count": len(recommendations),
        "diagnostics": diagnostics,
        "recommendations": recommendations,
    }


@router.get("/projections/players")
def nfl_player_projections(
    season: int = Query(..., ge=2010, le=2100),
    week: int = Query(..., ge=1, le=25),
    model_version: str = Query("nfl-player-v1"),
    team: Optional[str] = Query(None),
    position: Optional[str] = Query(None),
    limit: int = Query(250, ge=1, le=2000),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        rows = session.execute(
            text(
                """
                SELECT
                  season, week, team, player_id, player_uid, player_name, position, model_version,
                  pass_yards_mean, rush_yards_mean, receiving_yards_mean,
                  receptions_mean, anytime_td_prob, floor_outcome, median_outcome,
                  ceiling_outcome, uncertainty, source_coverage, updated_at
                FROM nfl_player_projection_baselines
                WHERE season = :season
                  AND week = :week
                  AND model_version = :model_version
                  AND (:team IS NULL OR team = :team)
                  AND (:position IS NULL OR position = :position)
                ORDER BY position, team, player_name
                LIMIT :limit
                """
            ),
            {
                "season": season,
                "week": week,
                "model_version": model_version,
                "team": team,
                "position": position,
                "limit": limit,
            },
        ).fetchall()
        return {"count": len(rows), "rows": [dict(r._mapping) for r in rows]}
    finally:
        session.close()


@router.get("/props/board")
def nfl_props_board(
    season: int = Query(..., ge=2010, le=2100),
    week: int = Query(..., ge=1, le=25),
    model_version: str = Query("nfl-player-v1"),
    market_key: Optional[str] = Query(None),
    team: Optional[str] = Query(None),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    min_abs_edge: float = Query(0.0, ge=0.0, le=0.5),
    limit: int = Query(250, ge=1, le=2000),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        rows = session.execute(
            text(
                """
                SELECT
                  season, week, model_version, game_id, player_id, player_uid, player_name, team, market_key, line,
                  model_mean, model_std, model_floor, model_median, model_ceiling,
                  over_prob, under_prob, fair_over_price, fair_under_price,
                  market_over_price, market_under_price, edge_over, edge_under, confidence, diagnostics, updated_at
                FROM nfl_player_prop_model_edges
                WHERE season = :season
                  AND week = :week
                  AND model_version = :model_version
                  AND (:market_key IS NULL OR market_key = :market_key)
                  AND (:team IS NULL OR team = :team)
                  AND confidence >= :min_confidence
                  AND GREATEST(ABS(COALESCE(edge_over, 0)), ABS(COALESCE(edge_under, 0))) >= :min_abs_edge
                ORDER BY confidence DESC, GREATEST(ABS(COALESCE(edge_over, 0)), ABS(COALESCE(edge_under, 0))) DESC
                LIMIT :limit
                """
            ),
            {
                "season": season,
                "week": week,
                "model_version": model_version,
                "market_key": market_key,
                "team": team,
                "min_confidence": min_confidence,
                "min_abs_edge": min_abs_edge,
                "limit": limit,
            },
        ).fetchall()
        return {"count": len(rows), "rows": [dict(r._mapping) for r in rows]}
    finally:
        session.close()


@router.get("/fantasy/rankings")
def nfl_fantasy_rankings(
    season: int = Query(..., ge=2010, le=2100),
    week: int = Query(..., ge=1, le=25),
    scoring_profile: str = Query("half_ppr", pattern="^(standard|half_ppr|ppr)$"),
    model_version: str = Query("nfl-player-v1"),
    position: Optional[str] = Query(None),
    tier_max: Optional[int] = Query(None, ge=1, le=12),
    limit: int = Query(300, ge=1, le=3000),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        rows = session.execute(
            text(
                """
                SELECT
                  season, week, scoring_profile, model_version, player_id, player_uid, player_name, team, position,
                  expected_points, floor_points, median_points, ceiling_points,
                  rank_overall, rank_position, tier, projection_payload, updated_at
                FROM nfl_fantasy_weekly_projections
                WHERE season = :season
                  AND week = :week
                  AND scoring_profile = :scoring_profile
                  AND model_version = :model_version
                  AND (:position IS NULL OR position = :position)
                  AND (:tier_max IS NULL OR tier <= :tier_max)
                ORDER BY rank_overall
                LIMIT :limit
                """
            ),
            {
                "season": season,
                "week": week,
                "scoring_profile": scoring_profile,
                "model_version": model_version,
                "position": position,
                "tier_max": tier_max,
                "limit": limit,
            },
        ).fetchall()
        return {"count": len(rows), "rows": [dict(r._mapping) for r in rows]}
    finally:
        session.close()


@router.get("/ops/projections-readiness")
def nfl_projection_layer_readiness(
    season: int = Query(..., ge=2010, le=2100),
    week: int = Query(..., ge=1, le=25),
    model_version: str = Query("nfl-player-v1"),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        rows = session.execute(
            text(
                """
                SELECT DISTINCT ON (layer)
                  layer, readiness_status, source_coverage, freshness, calibration_flags, metrics, created_at
                FROM nfl_projection_audit_runs
                WHERE season = :season
                  AND week = :week
                  AND model_version = :model_version
                ORDER BY layer, created_at DESC
                """
            ),
            {"season": season, "week": week, "model_version": model_version},
        ).fetchall()
        layer_payload = {str(row.layer): dict(row._mapping) for row in rows}
        statuses = [str(row.readiness_status) for row in rows]
        overall = "go" if statuses and all(s == "go" for s in statuses) else ("warning" if statuses else "missing")
        return {"season": season, "week": week, "model_version": model_version, "overall_status": overall, "layers": layer_payload}
    finally:
        session.close()


@router.post("/ops/materialize-player-baselines")
def nfl_trigger_player_baseline_materialization(
    season: int = Query(..., ge=2010, le=2100),
    week: Optional[int] = Query(None, ge=1, le=25),
    model_version: str = Query("nfl-player-v1"),
) -> Dict[str, Any]:
    task = celery_app.send_task(
        TASK_NFL_PLAYER_BASELINES,
        kwargs={"season": int(season), "week": int(week) if week is not None else None, "model_version": model_version},
    )
    return {"task_id": task.id, "task_name": TASK_NFL_PLAYER_BASELINES, "season": season, "week": week, "model_version": model_version}


@router.post("/ops/materialize-player-props")
def nfl_trigger_player_props_materialization(
    season: int = Query(..., ge=2010, le=2100),
    week: Optional[int] = Query(None, ge=1, le=25),
    model_version: str = Query("nfl-player-v1"),
) -> Dict[str, Any]:
    task = celery_app.send_task(
        TASK_NFL_PLAYER_PROPS,
        kwargs={"season": int(season), "week": int(week) if week is not None else None, "model_version": model_version},
    )
    return {"task_id": task.id, "task_name": TASK_NFL_PLAYER_PROPS, "season": season, "week": week, "model_version": model_version}


@router.post("/ops/materialize-fantasy")
def nfl_trigger_fantasy_materialization(
    season: int = Query(..., ge=2010, le=2100),
    week: Optional[int] = Query(None, ge=1, le=25),
    model_version: str = Query("nfl-player-v1"),
) -> Dict[str, Any]:
    task = celery_app.send_task(
        TASK_NFL_FANTASY,
        kwargs={"season": int(season), "week": int(week) if week is not None else None, "model_version": model_version},
    )
    return {"task_id": task.id, "task_name": TASK_NFL_FANTASY, "season": season, "week": week, "model_version": model_version}


@router.post("/ops/run-player-cycle")
def nfl_trigger_player_cycle(
    season: int = Query(..., ge=2010, le=2100),
    week: Optional[int] = Query(None, ge=1, le=25),
    model_version: str = Query("nfl-player-v1"),
) -> Dict[str, Any]:
    task = celery_app.send_task(
        TASK_NFL_PLAYER_CYCLE,
        kwargs={"season": int(season), "week": int(week) if week is not None else None, "model_version": model_version},
    )
    return {"task_id": task.id, "task_name": TASK_NFL_PLAYER_CYCLE, "season": season, "week": week, "model_version": model_version}


@router.get("/identity/queue")
def nfl_identity_queue(
    queue_status: str = Query("pending", pattern="^(pending|approved|rejected|resolved)$"),
    reason: Optional[str] = Query(None),
    season: Optional[int] = Query(None, ge=2010, le=2100),
    week: Optional[int] = Query(None, ge=1, le=25),
    limit: int = Query(200, ge=1, le=2000),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        rows = session.execute(
            text(
                """
                SELECT
                  q.id,
                  q.mapping_event_id,
                  q.queue_status,
                  q.priority,
                  q.reason,
                  q.observed_source,
                  q.observed_external_id,
                  q.observed_player_name,
                  q.normalized_name,
                  q.observed_team,
                  q.observed_position,
                  q.observed_season,
                  q.observed_week,
                  q.candidate_player_uids,
                  q.proposed_player_uid,
                  q.reviewer,
                  q.reviewer_notes,
                  q.approved_player_uid,
                  q.reviewed_at,
                  q.created_at,
                  q.updated_at
                FROM nfl_player_mapping_review_queue q
                WHERE q.queue_status = :queue_status
                  AND (:reason IS NULL OR q.reason = :reason)
                  AND (:season IS NULL OR q.observed_season = :season)
                  AND (:week IS NULL OR q.observed_week = :week)
                ORDER BY q.created_at DESC
                LIMIT :limit
                """
            ),
            {
                "queue_status": queue_status,
                "reason": reason,
                "season": season,
                "week": week,
                "limit": limit,
            },
        ).fetchall()
        return {"count": len(rows), "rows": [dict(r._mapping) for r in rows]}
    finally:
        session.close()


@router.post("/identity/queue/{queue_id}/action")
def nfl_identity_queue_action(
    queue_id: str,
    action: str = Query(..., pattern="^(approve|reject)$"),
    reviewer: str = Query(..., min_length=2, max_length=128),
    player_uid: Optional[str] = Query(None),
    notes: Optional[str] = Query(None, max_length=5000),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        result = apply_manual_mapping_resolution(
            session,
            queue_id=queue_id,
            action=action,
            reviewer=reviewer,
            player_uid=player_uid,
            notes=notes,
        )
        if not bool(result.get("updated")):
            reason = str(result.get("reason") or "identity_queue_item_not_found")
            code = 404 if reason == "queue_item_not_found" else 400
            raise HTTPException(status_code=code, detail=reason)
        session.commit()
        return {
            "queue_id": queue_id,
            "action": action,
            "queue_status": result.get("status"),
            "reviewer": reviewer,
            "player_uid": player_uid,
        }
    except HTTPException:
        session.rollback()
        raise
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@router.post("/identity/refresh")
def nfl_identity_refresh(
    season: int = Query(..., ge=2010, le=2100),
    week: Optional[int] = Query(None, ge=1, le=25),
    model_version: str = Query("nfl-player-v1"),
) -> Dict[str, Any]:
    task = celery_app.send_task(
        TASK_NFL_IDENTITY_REFRESH,
        kwargs={"season": int(season), "week": int(week) if week is not None else None, "model_version": model_version},
    )
    return {
        "task_id": task.id,
        "task_name": TASK_NFL_IDENTITY_REFRESH,
        "season": season,
        "week": week,
        "model_version": model_version,
    }


@router.post("/identity/manual-reconciliations")
def nfl_identity_manual_reconciliations(
    limit: int = Query(200, ge=1, le=2000),
    reviewer: str = Query("system-weekly-identity-sync", min_length=2, max_length=128),
) -> Dict[str, Any]:
    task = celery_app.send_task(
        TASK_NFL_IDENTITY_MANUAL_RESOLUTIONS,
        kwargs={"limit": int(limit), "reviewer": reviewer},
    )
    return {"task_id": task.id, "task_name": TASK_NFL_IDENTITY_MANUAL_RESOLUTIONS, "limit": limit, "reviewer": reviewer}


@router.post("/identity/quality-snapshot")
def nfl_identity_quality_snapshot(
    season: Optional[int] = Query(None, ge=2010, le=2100),
    week: Optional[int] = Query(None, ge=1, le=25),
    source_system: Optional[str] = Query(None),
) -> Dict[str, Any]:
    task = celery_app.send_task(
        TASK_NFL_IDENTITY_QUALITY_SNAPSHOT,
        kwargs={"season": season, "week": week, "source_system": source_system},
    )
    return {
        "task_id": task.id,
        "task_name": TASK_NFL_IDENTITY_QUALITY_SNAPSHOT,
        "season": season,
        "week": week,
        "source_system": source_system,
    }


@router.get("/identity/quality/latest")
def nfl_identity_quality_latest(
    season: Optional[int] = Query(None, ge=2010, le=2100),
    week: Optional[int] = Query(None, ge=1, le=25),
    source_system: Optional[str] = Query(None),
    resolver_version: Optional[str] = Query(None),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        row = session.execute(
            text(
                """
                SELECT
                  snapshot_date,
                  season,
                  week,
                  resolver_version,
                  source_system,
                  coverage_rate,
                  high_confidence_auto_map_rate,
                  unresolved_rate,
                  conflict_rate,
                  remap_count,
                  reversal_count,
                  source_freshness_hours,
                  readiness_status,
                  metrics,
                  created_at
                FROM nfl_player_mapping_quality_snapshots
                WHERE (:season IS NULL OR season = :season)
                  AND (:week IS NULL OR week = :week)
                  AND (:source_system IS NULL OR source_system = :source_system)
                  AND (:resolver_version IS NULL OR resolver_version = :resolver_version)
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {
                "season": season,
                "week": week,
                "source_system": source_system,
                "resolver_version": resolver_version,
            },
        ).fetchone()
        if row is None:
            return {"snapshot": None}
        payload = dict(row._mapping)
        unresolved_rate = _to_float(payload.get("unresolved_rate")) or 0.0
        conflict_rate = _to_float(payload.get("conflict_rate")) or 0.0
        readiness = "go"
        if unresolved_rate > 0.06 or conflict_rate > 0.02:
            readiness = "no-go"
        elif unresolved_rate > 0.04 or conflict_rate > 0.012:
            readiness = "warning"
        payload["readiness_status"] = readiness
        return {"snapshot": payload}
    finally:
        session.close()
