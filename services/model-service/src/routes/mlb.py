from __future__ import annotations

import os
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from src.db import SessionLocal
from src.services.mlb_data import normalize_team_key, starter_identity_features
from src.services.mlb_market_consensus import weighted_consensus
from src.services.mlb_market_maker import (
    american_implied_prob as mm_american_implied_prob,
    synthetic_no_vig_from_books,
)
from src.services.mlb_pitch_simulator import simulate_mlb_game_pitch_by_pitch
from src.services.mlb_simulator import (
    DEFAULT_MODEL_VERSION,
    MlbGameInputs,
    simulate_mlb_game,
)
from src.services.odds_api import fetch_odds

router = APIRouter(prefix="/mlb", tags=["mlb-model"])
MODEL_STATE_KEY = "mlb_active_model"


def _to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (int, float)):
        return float(v)
    return None


def _to_int(v: Any) -> Optional[int]:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _american_implied_prob(price: Optional[int]) -> Optional[float]:
    return mm_american_implied_prob(price)


def _kelly_fraction(prob: Optional[float], price: Optional[int]) -> Optional[float]:
    if prob is None or price is None:
        return None
    p = max(0.0001, min(0.9999, prob))
    if price > 0:
        b = price / 100.0
    else:
        b = 100.0 / abs(price)
    if b <= 0:
        return None
    q = 1.0 - p
    k = (b * p - q) / b
    return max(0.0, k)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _run_simulation_by_model(
    inputs: MlbGameInputs,
    *,
    simulations: int,
    model_version: str,
) -> Dict[str, Any]:
    if model_version.startswith("mlb-v2-pitch-sim"):
        if not _env_bool("MLB_ENABLE_PITCH_SIM", False):
            raise HTTPException(
                status_code=400,
                detail="mlb-v2-pitch-sim is disabled; set MLB_ENABLE_PITCH_SIM=true",
            )
        return simulate_mlb_game_pitch_by_pitch(
            inputs,
            simulations=simulations,
            model_version=model_version,
        )
    return simulate_mlb_game(
        inputs,
        simulations=simulations,
        model_version=model_version,
    )


def _resolve_active_model_version(session: Any, fallback: str = DEFAULT_MODEL_VERSION) -> str:
    row = session.execute(
        text(
            """
            SELECT active_model_version
            FROM mlb_model_runtime_state
            WHERE state_key = :state_key
            LIMIT 1
            """
        ),
        {"state_key": MODEL_STATE_KEY},
    ).fetchone()
    if not row:
        return fallback
    value = row[0]
    return str(value) if value else fallback


def _safe_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _safe_date(v: Any) -> Optional[date]:
    if v is None:
        return None
    if isinstance(v, date):
        return v
    s = str(v).strip()
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def _safe_payload_float(payload: Dict[str, Any], key: str) -> Optional[float]:
    try:
        value = payload.get(key)
    except Exception:
        return None
    return _safe_float(value)


def _aggregate_nowcast_snapshot_payloads(payloads: List[Dict[str, Any]]) -> Dict[str, Any]:
    run_count = 0
    total_games = 0
    conf_sum = 0.0
    prev_conf_sum = 0.0
    prev_conf_count = 0
    conf_delta_sum = 0.0
    conf_delta_count = 0
    fresh_sum = 0.0
    confirmed_sum = 0.0
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        run_count += 1
        total_games += int(_safe_float(payload.get("context_rows_updated")) or 0)
        conf_val = _safe_payload_float(payload, "avg_nowcast_confidence")
        if conf_val is not None:
            conf_sum += conf_val
        prev_val = _safe_payload_float(payload, "avg_prev_confidence")
        if prev_val is not None:
            prev_conf_sum += prev_val
            prev_conf_count += 1
        delta_val = _safe_payload_float(payload, "avg_confidence_delta")
        if delta_val is not None:
            conf_delta_sum += delta_val
            conf_delta_count += 1
        fresh_val = _safe_payload_float(payload, "avg_freshness_score")
        if fresh_val is not None:
            fresh_sum += fresh_val
        conf_share = _safe_payload_float(payload, "lineup_confirmed_share")
        if conf_share is not None:
            confirmed_sum += conf_share
    return {
        "runs_analyzed": run_count,
        "games_repriced": total_games,
        "avg_nowcast_confidence": round(conf_sum / max(1, run_count), 4),
        "avg_prev_confidence": round(prev_conf_sum / max(1, prev_conf_count), 4)
        if prev_conf_count > 0
        else None,
        "avg_confidence_delta": round(conf_delta_sum / max(1, conf_delta_count), 4)
        if conf_delta_count > 0
        else None,
        "avg_freshness_score": round(fresh_sum / max(1, run_count), 4),
        "lineup_confirmed_share": round(confirmed_sum / max(1, run_count), 4),
    }


def _info_freshness_score(updated_at: Any, lineup_confirmed: bool) -> float:
    if updated_at is None:
        return 0.45
    try:
        if isinstance(updated_at, str):
            dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        else:
            dt = updated_at
        now = datetime.now(timezone.utc)
        age_hours = max(0.0, (now - dt).total_seconds() / 3600.0)
    except Exception:
        age_hours = 24.0
    try:
        half_life_hours = float(os.getenv("MLB_INFO_FRESHNESS_HALFLIFE_HOURS", "18"))
    except ValueError:
        half_life_hours = 18.0
    half_life_hours = max(1.0, half_life_hours)
    score = 0.5 ** (age_hours / half_life_hours)
    if lineup_confirmed:
        score = min(1.0, score + 0.08)
    return max(0.35, min(1.0, score))


def _classify_go_no_go(
    *,
    sample_size: int,
    calendar_days: int,
    last_game_date: Optional[date],
    warning_alerts_24h: int,
    min_sample_size: int,
    min_calendar_days: int,
    max_last_game_age_days: int,
) -> Dict[str, Any]:
    today = date.today()
    last_age = (today - last_game_date).days if last_game_date else None
    checks = {
        "sample_size_ok": sample_size >= min_sample_size,
        "calendar_days_ok": calendar_days >= min_calendar_days,
        "freshness_ok": last_age is not None and last_age <= max_last_game_age_days,
        "alerts_ok": warning_alerts_24h == 0,
    }
    reasons: List[str] = []
    if not checks["sample_size_ok"]:
        reasons.append("low_sample_size")
    if not checks["calendar_days_ok"]:
        reasons.append("low_calendar_coverage")
    if not checks["freshness_ok"]:
        reasons.append("stale_or_missing_outcomes")
    if not checks["alerts_ok"]:
        reasons.append("recent_warning_alerts")

    if not checks["sample_size_ok"] or not checks["calendar_days_ok"] or not checks["freshness_ok"]:
        status = "red"
    elif not checks["alerts_ok"]:
        status = "yellow"
    else:
        status = "green"
    return {
        "status": status,
        "checks": checks,
        "reasons": reasons,
        "last_game_age_days": last_age,
    }


def _fetch_game_row(session: Any, game_id: str) -> Optional[Dict[str, Any]]:
    row = session.execute(
        text(
            """
            SELECT
              g.id AS game_id,
              g.external_id,
              g.start_time,
              home.name AS home_team,
              away.name AS away_team,
              c.probable_pitcher_home,
              c.probable_pitcher_away,
              c.weather_temp_f,
              c.weather_wind_mph,
              c.weather_wind_dir_deg,
              c.weather_humidity_pct,
              c.park_factor_runs,
              c.lineup_confidence_home,
              c.lineup_confidence_away,
              c.offense_index_home,
              c.offense_index_away,
              c.offense_split_index_home,
              c.offense_split_index_away,
              c.recent_form_index_home,
              c.recent_form_index_away,
              c.lineup_strength_index_home,
              c.lineup_strength_index_away,
              c.bullpen_fatigue_home,
              c.bullpen_fatigue_away,
              c.bullpen_ip_last3_home,
              c.bullpen_ip_last3_away,
              c.bullpen_availability_home,
              c.bullpen_availability_away,
              c.bullpen_high_leverage_availability_home,
              c.bullpen_high_leverage_availability_away,
              c.updated_at AS context_updated_at,
              c.umpire_run_factor,
              c.umpire_home_plate,
              c.lineup_confirmed
            FROM games g
            JOIN teams home ON home.id = g.home_team_id
            JOIN teams away ON away.id = g.away_team_id
            LEFT JOIN mlb_game_context c ON c.game_id = g.id
            WHERE g.id = :game_id
            LIMIT 1
            """
        ),
        {"game_id": game_id},
    ).fetchone()
    return dict(row._mapping) if row else None


def _store_projection(session: Any, projection: Dict[str, Any]) -> None:
    markets = projection["markets"]
    diagnostics = projection.get("diagnostics") or {}
    session.execute(
        text(
            """
            INSERT INTO mlb_market_projections (
              game_id, model_version, simulation_count,
              f5_home_win_prob, fg_home_win_prob, f5_total_mean, fg_total_mean,
              fair_f5_home_ml, fair_fg_home_ml, fair_f5_total, fair_fg_total,
              projection
            ) VALUES (
              :game_id, :model_version, :simulation_count,
              :f5_home_win_prob, :fg_home_win_prob, :f5_total_mean, :fg_total_mean,
              :fair_f5_home_ml, :fair_fg_home_ml, :fair_f5_total, :fair_fg_total,
              CAST(:projection AS jsonb)
            )
            """
        ),
        {
            "game_id": projection["game_id"],
            "model_version": projection["model_version"],
            "simulation_count": projection["simulation_count"],
            "f5_home_win_prob": markets["f5_home_win_prob"],
            "fg_home_win_prob": markets["fg_home_win_prob"],
            "f5_total_mean": markets["f5_total_mean"],
            "fg_total_mean": markets["fg_total_mean"],
            "fair_f5_home_ml": markets["fair_f5_home_ml"],
            "fair_fg_home_ml": markets["fair_fg_home_ml"],
            "fair_f5_total": markets["fair_f5_total"],
            "fair_fg_total": markets["fair_fg_total"],
            "projection": __import__("json").dumps(projection),
        },
    )
    session.execute(
        text(
            """
            INSERT INTO mlb_simulation_audit (
              game_id, model_version, simulation_count, random_seed,
              inputs, run_rates, diagnostics, created_at
            ) VALUES (
              :game_id, :model_version, :simulation_count, :random_seed,
              CAST(:inputs AS jsonb), CAST(:run_rates AS jsonb), CAST(:diagnostics AS jsonb), NOW()
            )
            """
        ),
        {
            "game_id": projection["game_id"],
            "model_version": projection["model_version"],
            "simulation_count": projection["simulation_count"],
            "random_seed": None,
            "inputs": __import__("json").dumps(projection.get("inputs") or {}),
            "run_rates": __import__("json").dumps(projection.get("run_rates") or {}),
            "diagnostics": __import__("json").dumps(diagnostics),
        },
    )


@router.get("/games")
def mlb_games(
    game_date: date = Query(..., description="UTC date for MLB slate"),
) -> Dict[str, List[Dict[str, Any]]]:
    session = SessionLocal()
    try:
        rows = session.execute(
            text(
                """
                SELECT
                  g.id AS game_id,
                  g.external_id,
                  g.start_time,
                  home.name AS home_team,
                  away.name AS away_team,
                  c.probable_pitcher_home,
                  c.probable_pitcher_away,
                  c.weather_temp_f,
                  c.weather_wind_mph,
                  c.weather_wind_dir_deg,
                  c.weather_humidity_pct,
                  c.park_factor_runs,
                  c.lineup_confidence_home,
                  c.lineup_confidence_away,
                  c.offense_index_home,
                  c.offense_index_away,
                  c.offense_split_index_home,
                  c.offense_split_index_away,
                  c.recent_form_index_home,
                  c.recent_form_index_away,
                  c.lineup_strength_index_home,
                  c.lineup_strength_index_away,
                  c.bullpen_fatigue_home,
                  c.bullpen_fatigue_away,
                  c.bullpen_ip_last3_home,
                  c.bullpen_ip_last3_away,
                  c.bullpen_availability_home,
                  c.bullpen_availability_away,
                  c.bullpen_high_leverage_availability_home,
                  c.bullpen_high_leverage_availability_away,
                  c.updated_at AS context_updated_at,
                  c.umpire_run_factor,
                  c.umpire_home_plate,
                  c.lineup_confirmed,
                  p.model_version,
                  p.created_at AS projection_created_at,
                  p.f5_home_win_prob,
                  p.fg_home_win_prob,
                  p.f5_total_mean,
                  p.fg_total_mean,
                  p.fair_f5_home_ml,
                  p.fair_fg_home_ml,
                  p.fair_f5_total,
                  p.fair_fg_total
                FROM games g
                JOIN seasons s ON s.id = g.season_id
                JOIN leagues l ON l.id = s.league_id
                JOIN teams home ON home.id = g.home_team_id
                JOIN teams away ON away.id = g.away_team_id
                LEFT JOIN mlb_game_context c ON c.game_id = g.id
                LEFT JOIN LATERAL (
                  SELECT *
                  FROM mlb_market_projections mp
                  WHERE mp.game_id = g.id
                  ORDER BY mp.created_at DESC
                  LIMIT 1
                ) p ON TRUE
                WHERE l.code = 'mlb'
                  AND g.game_date = :game_date
                ORDER BY g.start_time
                """
            ),
            {"game_date": game_date},
        ).fetchall()

        games: List[Dict[str, Any]] = []
        for r in rows:
            m = dict(r._mapping)
            games.append(
                {
                    "game_id": m["game_id"],
                    "external_id": m["external_id"],
                    "start_time": m["start_time"],
                    "home_team": m["home_team"],
                    "away_team": m["away_team"],
                    "context": {
                        "probable_pitcher_home": m["probable_pitcher_home"],
                        "probable_pitcher_away": m["probable_pitcher_away"],
                        "weather_temp_f": _to_float(m["weather_temp_f"]),
                        "weather_wind_mph": _to_float(m["weather_wind_mph"]),
                        "weather_wind_dir_deg": _to_float(m["weather_wind_dir_deg"]),
                        "weather_humidity_pct": _to_float(m["weather_humidity_pct"]),
                        "park_factor_runs": _to_float(m["park_factor_runs"]),
                        "lineup_confidence_home": _to_float(m["lineup_confidence_home"]),
                        "lineup_confidence_away": _to_float(m["lineup_confidence_away"]),
                        "offense_index_home": _to_float(m["offense_index_home"]),
                        "offense_index_away": _to_float(m["offense_index_away"]),
                        "offense_split_index_home": _to_float(m["offense_split_index_home"]),
                        "offense_split_index_away": _to_float(m["offense_split_index_away"]),
                        "recent_form_index_home": _to_float(m["recent_form_index_home"]),
                        "recent_form_index_away": _to_float(m["recent_form_index_away"]),
                        "lineup_strength_index_home": _to_float(m["lineup_strength_index_home"]),
                        "lineup_strength_index_away": _to_float(m["lineup_strength_index_away"]),
                        "bullpen_fatigue_home": _to_float(m["bullpen_fatigue_home"]),
                        "bullpen_fatigue_away": _to_float(m["bullpen_fatigue_away"]),
                        "bullpen_ip_last3_home": _to_float(m["bullpen_ip_last3_home"]),
                        "bullpen_ip_last3_away": _to_float(m["bullpen_ip_last3_away"]),
                        "bullpen_availability_home": _to_float(m["bullpen_availability_home"]),
                        "bullpen_availability_away": _to_float(m["bullpen_availability_away"]),
                        "bullpen_high_leverage_availability_home": _to_float(m["bullpen_high_leverage_availability_home"]),
                        "bullpen_high_leverage_availability_away": _to_float(m["bullpen_high_leverage_availability_away"]),
                        "umpire_run_factor": _to_float(m["umpire_run_factor"]),
                        "context_updated_at": m["context_updated_at"],
                        "umpire_home_plate": m["umpire_home_plate"],
                        "lineup_confirmed": bool(m["lineup_confirmed"]) if m["lineup_confirmed"] is not None else False,
                    },
                    "projection": (
                        None
                        if m["model_version"] is None
                        else {
                            "model_version": m["model_version"],
                            "created_at": m["projection_created_at"],
                            "f5_home_win_prob": _to_float(m["f5_home_win_prob"]),
                            "fg_home_win_prob": _to_float(m["fg_home_win_prob"]),
                            "f5_total_mean": _to_float(m["f5_total_mean"]),
                            "fg_total_mean": _to_float(m["fg_total_mean"]),
                            "fair_f5_home_ml": _to_int(m["fair_f5_home_ml"]),
                            "fair_fg_home_ml": _to_int(m["fair_fg_home_ml"]),
                            "fair_f5_total": _to_float(m["fair_f5_total"]),
                            "fair_fg_total": _to_float(m["fair_fg_total"]),
                        }
                    ),
                }
            )
        return {"games": games}
    finally:
        session.close()


@router.post("/simulations/{game_id}")
def run_single_game_simulation(
    game_id: str,
    simulations: int = Query(4000, ge=500, le=20000),
    model_version: Optional[str] = Query(None),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        effective_model_version = model_version or _resolve_active_model_version(session)
        row = _fetch_game_row(session, game_id)
        if row is None:
            raise HTTPException(status_code=404, detail=f"game_not_found: {game_id}")
        lineup_confirmed = bool(row["lineup_confirmed"]) if row["lineup_confirmed"] is not None else False
        freshness = _info_freshness_score(row.get("context_updated_at"), lineup_confirmed)
        starter_home_feat = starter_identity_features(row.get("probable_pitcher_home"))
        starter_away_feat = starter_identity_features(row.get("probable_pitcher_away"))

        inputs = MlbGameInputs(
            game_id=game_id,
            home_team=row["home_team"],
            away_team=row["away_team"],
            starter_home=row["probable_pitcher_home"],
            starter_away=row["probable_pitcher_away"],
            starter_quality_home=float(starter_home_feat.get("starter_quality") or 1.0),
            starter_quality_away=float(starter_away_feat.get("starter_quality") or 1.0),
            starter_k_factor_home=float(starter_home_feat.get("k_factor") or 1.0),
            starter_k_factor_away=float(starter_away_feat.get("k_factor") or 1.0),
            starter_bb_factor_home=float(starter_home_feat.get("bb_factor") or 1.0),
            starter_bb_factor_away=float(starter_away_feat.get("bb_factor") or 1.0),
            starter_gb_factor_home=float(starter_home_feat.get("gb_factor") or 1.0),
            starter_gb_factor_away=float(starter_away_feat.get("gb_factor") or 1.0),
            weather_temp_f=_to_float(row["weather_temp_f"]),
            weather_wind_mph=_to_float(row["weather_wind_mph"]),
            weather_wind_dir_deg=_to_float(row["weather_wind_dir_deg"]),
            weather_humidity_pct=_to_float(row["weather_humidity_pct"]),
            park_factor_runs=_to_float(row["park_factor_runs"]),
            offense_home=_to_float(row["offense_index_home"]) or 1.0,
            offense_away=_to_float(row["offense_index_away"]) or 1.0,
            offense_split_home=_to_float(row["offense_split_index_home"]) or 1.0,
            offense_split_away=_to_float(row["offense_split_index_away"]) or 1.0,
            recent_form_index_home=_to_float(row["recent_form_index_home"]) or 1.0,
            recent_form_index_away=_to_float(row["recent_form_index_away"]) or 1.0,
            lineup_strength_index_home=_to_float(row["lineup_strength_index_home"]) or 1.0,
            lineup_strength_index_away=_to_float(row["lineup_strength_index_away"]) or 1.0,
            umpire_home_plate=row["umpire_home_plate"],
            lineup_confirmed=lineup_confirmed,
            lineup_confidence_home=_to_float(row["lineup_confidence_home"]) or 0.85,
            lineup_confidence_away=_to_float(row["lineup_confidence_away"]) or 0.85,
            bullpen_fatigue_home=_to_float(row["bullpen_fatigue_home"]) or 0.50,
            bullpen_fatigue_away=_to_float(row["bullpen_fatigue_away"]) or 0.50,
            bullpen_ip_last3_home=_to_float(row["bullpen_ip_last3_home"]) or 9.0,
            bullpen_ip_last3_away=_to_float(row["bullpen_ip_last3_away"]) or 9.0,
            bullpen_availability_home=_to_float(row["bullpen_availability_home"]) or 0.65,
            bullpen_availability_away=_to_float(row["bullpen_availability_away"]) or 0.65,
            bullpen_high_lev_availability_home=_to_float(row["bullpen_high_leverage_availability_home"]) or 0.62,
            bullpen_high_lev_availability_away=_to_float(row["bullpen_high_leverage_availability_away"]) or 0.62,
            umpire_run_factor=_to_float(row["umpire_run_factor"]) or 1.0,
            info_freshness_score_home=freshness,
            info_freshness_score_away=freshness,
        )
        projection = _run_simulation_by_model(
            inputs,
            simulations=simulations,
            model_version=effective_model_version,
        )
        _store_projection(session, projection)
        session.commit()
        return projection
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"simulation_failed: {e}")
    finally:
        session.close()


@router.get("/edges/today")
def mlb_edges_today(
    model_version: Optional[str] = Query(None),
) -> Dict[str, Any]:
    # Pull current MLB market for moneyline + totals.
    market_events = fetch_odds(
        endpoint="sports/baseball_mlb/odds",
        params={
            "regions": "us",
            "markets": "h2h,totals",
            "oddsFormat": "american",
            "dateFormat": "iso",
        },
    )
    session = SessionLocal()
    try:
        effective_model_version = model_version or _resolve_active_model_version(session)
        rows = session.execute(
            text(
                """
                SELECT
                  g.id AS game_id,
                  home.name AS home_team,
                  away.name AS away_team,
                  p.fg_home_win_prob,
                  p.fair_fg_home_ml,
                  p.fair_fg_total,
                  p.projection,
                  p.created_at AS projection_created_at,
                  c.lineup_confidence_home,
                  c.lineup_confidence_away,
                  c.offense_split_index_home,
                  c.offense_split_index_away,
                  c.lineup_strength_index_home,
                  c.lineup_strength_index_away,
                  c.bullpen_availability_home,
                  c.bullpen_availability_away,
                  c.bullpen_high_leverage_availability_home,
                  c.bullpen_high_leverage_availability_away,
                  c.updated_at AS context_updated_at
                FROM games g
                JOIN seasons s ON s.id = g.season_id
                JOIN leagues l ON l.id = s.league_id
                JOIN teams home ON home.id = g.home_team_id
                JOIN teams away ON away.id = g.away_team_id
                LEFT JOIN mlb_game_context c ON c.game_id = g.id
                JOIN LATERAL (
                  SELECT *
                  FROM mlb_market_projections mp
                  WHERE mp.game_id = g.id
                    AND mp.model_version = :model_version
                  ORDER BY mp.created_at DESC
                  LIMIT 1
                ) p ON TRUE
                WHERE l.code = 'mlb'
                  AND g.game_date = CURRENT_DATE
                """
            ),
            {"model_version": effective_model_version},
        ).fetchall()

        projection_by_key = {
            (normalize_team_key(r.home_team), normalize_team_key(r.away_team)): dict(r._mapping)
            for r in rows
        }
        edges: List[Dict[str, Any]] = []

        for e in market_events if isinstance(market_events, list) else []:
            home_team = e.get("home_team")
            away_team = e.get("away_team")
            if not home_team or not away_team:
                continue
            proj = projection_by_key.get(
                (normalize_team_key(home_team), normalize_team_key(away_team))
            )
            if not proj:
                continue

            # Consensus market lines.
            h2h_home_prices: List[tuple[str, int]] = []
            h2h_away_prices: List[tuple[str, int]] = []
            total_points: List[tuple[str, float]] = []
            for b in e.get("bookmakers") or []:
                book_key = str(b.get("key") or "")
                for m in b.get("markets") or []:
                    key = m.get("key")
                    outcomes = m.get("outcomes") or []
                    if key == "h2h":
                        for o in outcomes:
                            if o.get("name") == home_team and o.get("price") is not None:
                                h2h_home_prices.append((book_key, int(o["price"])))
                            elif o.get("name") == away_team and o.get("price") is not None:
                                h2h_away_prices.append((book_key, int(o["price"])))
                    elif key == "totals":
                        for o in outcomes:
                            if o.get("name") == "Over" and o.get("point") is not None:
                                total_points.append((book_key, float(o["point"])))
            market_home_ml_raw = weighted_consensus(h2h_home_prices) if h2h_home_prices else None
            market_away_ml_raw = weighted_consensus(h2h_away_prices) if h2h_away_prices else None
            market_total_raw = weighted_consensus(total_points) if total_points else None
            market_home_ml = _to_int(round(market_home_ml_raw)) if market_home_ml_raw is not None else None
            market_away_ml = _to_int(round(market_away_ml_raw)) if market_away_ml_raw is not None else None
            market_total = round(float(market_total_raw), 2) if market_total_raw is not None else None

            market_home_prob = _american_implied_prob(market_home_ml)
            market_home_prob_no_vig = synthetic_no_vig_from_books(h2h_home_prices, h2h_away_prices)
            model_home_prob = _to_float(proj["fg_home_win_prob"])
            fair_home_ml = _to_int(proj["fair_fg_home_ml"])
            fair_total = _to_float(proj["fair_fg_total"])
            proj_payload = proj.get("projection") if isinstance(proj, dict) else None
            diagnostics = (
                ((proj_payload or {}).get("diagnostics") or {})
                if isinstance(proj_payload, dict)
                else {}
            )
            markets_payload = (
                ((proj_payload or {}).get("markets") or {})
                if isinstance(proj_payload, dict)
                else {}
            )
            drivers = diagnostics.get("drivers") if isinstance(diagnostics, dict) else None
            ml_ci_low = _to_float(markets_payload.get("fg_home_win_prob_ci_low"))
            ml_ci_high = _to_float(markets_payload.get("fg_home_win_prob_ci_high"))
            total_p10 = _to_float(markets_payload.get("fg_total_p10"))
            total_p90 = _to_float(markets_payload.get("fg_total_p90"))
            ml_ci_width = (
                abs((ml_ci_high or 0.0) - (ml_ci_low or 0.0))
                if ml_ci_low is not None and ml_ci_high is not None
                else None
            )
            total_band_width = (
                abs((total_p90 or 0.0) - (total_p10 or 0.0))
                if total_p10 is not None and total_p90 is not None
                else None
            )
            uncertainty_score = min(
                1.0,
                (
                    0.55 * min(1.0, (ml_ci_width or 0.12) / 0.18)
                    + 0.45 * min(1.0, (total_band_width or 4.5) / 6.0)
                ),
            )
            lineup_conf = (
                ((_to_float(proj.get("lineup_confidence_home")) or 0.85)
                 + (_to_float(proj.get("lineup_confidence_away")) or 0.85))
                / 2.0
            )
            lineup_strength = (
                ((_to_float(proj.get("lineup_strength_index_home")) or 1.0)
                 + (_to_float(proj.get("lineup_strength_index_away")) or 1.0))
                / 2.0
            )
            handedness_split = (
                ((_to_float(proj.get("offense_split_index_home")) or 1.0)
                 + (_to_float(proj.get("offense_split_index_away")) or 1.0))
                / 2.0
            )
            freshness_score = _info_freshness_score(
                proj.get("context_updated_at"),
                bool((_to_float(proj.get("lineup_confidence_home")) or 0.85) > 0.93),
            )
            bullpen_avail = (
                ((_to_float(proj.get("bullpen_availability_home")) or 0.65)
                 + (_to_float(proj.get("bullpen_availability_away")) or 0.65))
                / 2.0
            )
            high_lev_avail = (
                ((_to_float(proj.get("bullpen_high_leverage_availability_home")) or 0.62)
                 + (_to_float(proj.get("bullpen_high_leverage_availability_away")) or 0.62))
                / 2.0
            )
            edge_abs = abs((model_home_prob - market_home_prob) if model_home_prob is not None and market_home_prob is not None else 0.0)
            total_edge_abs = abs((fair_total - market_total) if fair_total is not None and market_total is not None else 0.0)
            market_depth = min(1.0, (len(h2h_home_prices) + len(total_points)) / 24.0)
            quality_score = round(
                100.0
                * (
                    0.22 * min(1.0, max(0.0, lineup_conf))
                    + 0.07 * min(1.0, max(0.0, lineup_strength))
                    + 0.05 * min(1.0, max(0.0, handedness_split))
                    + 0.15 * min(1.0, max(0.0, bullpen_avail))
                    + 0.10 * min(1.0, max(0.0, high_lev_avail))
                    + 0.16 * min(1.0, max(0.0, freshness_score))
                    + 0.12 * market_depth
                    + 0.08 * min(1.0, edge_abs / 0.05)
                    + 0.05 * min(1.0, total_edge_abs / 1.2)
                    - 0.10 * uncertainty_score
                ),
                1,
            )
            kelly = _kelly_fraction(model_home_prob, market_home_ml)
            uncertainty_mul = max(0.45, 1.0 - (0.55 * uncertainty_score))
            stake_fraction = (
                None
                if kelly is None
                else round(min(0.03, kelly * max(0.25, quality_score / 100.0) * 0.5 * uncertainty_mul), 4)
            )
            edges.append(
                {
                    "game_id": proj["game_id"],
                    "home_team": home_team,
                    "away_team": away_team,
                    "model_version": effective_model_version,
                    "market_home_ml": market_home_ml,
                    "market_away_ml": market_away_ml,
                    "market_home_prob_no_vig": (
                        round(market_home_prob_no_vig, 4)
                        if market_home_prob_no_vig is not None
                        else None
                    ),
                    "fair_home_ml": fair_home_ml,
                    "ml_edge_prob": (
                        round(
                            model_home_prob
                            - (
                                market_home_prob_no_vig
                                if market_home_prob_no_vig is not None
                                else market_home_prob
                            ),
                            4,
                        )
                        if model_home_prob is not None
                        and (
                            market_home_prob_no_vig is not None
                            or market_home_prob is not None
                        )
                        else None
                    ),
                    "market_total": market_total,
                    "fair_total": fair_total,
                    "total_edge": (
                        round(fair_total - market_total, 2)
                        if fair_total is not None and market_total is not None
                        else None
                    ),
                    "quality_score": quality_score,
                    "recommended_stake_fraction": stake_fraction,
                    "market_depth": len(h2h_home_prices) + len(total_points),
                    "freshness_score": round(freshness_score, 3),
                    "ml_confidence_interval_width": round(ml_ci_width, 4) if ml_ci_width is not None else None,
                    "total_band_width": round(total_band_width, 3) if total_band_width is not None else None,
                    "uncertainty_score": round(uncertainty_score, 4),
                    "explainability": {"drivers": drivers or []},
                }
            )

        return {"edges": edges, "count": len(edges), "model_version": effective_model_version}
    finally:
        session.close()


@router.get("/edges/premium-feed")
def mlb_premium_feed(
    model_version: Optional[str] = Query(None),
    min_quality_score: float = Query(62.0, ge=0.0, le=100.0),
    min_ml_edge_prob: float = Query(0.012, ge=0.0, le=0.2),
    min_total_edge: float = Query(0.35, ge=0.0, le=5.0),
    max_results: int = Query(15, ge=1, le=100),
    max_per_team_plays: int = Query(2, ge=1, le=8),
    max_market_share: float = Query(0.70, ge=0.3, le=1.0),
    correlation_penalty: float = Query(0.35, ge=0.0, le=0.9),
    max_total_stake_fraction: float = Query(0.12, ge=0.01, le=1.0),
    max_team_stake_fraction: float = Query(0.05, ge=0.005, le=1.0),
    min_freshness_score: float = Query(0.50, ge=0.0, le=1.0),
    min_market_depth: int = Query(6, ge=0, le=40),
    max_uncertainty_score: float = Query(0.72, ge=0.0, le=1.0),
    max_ml_ci_width: float = Query(0.17, ge=0.02, le=0.5),
    max_total_band_width: float = Query(6.0, ge=1.0, le=20.0),
    risk_profile: str = Query("balanced", pattern="^(conservative|balanced|aggressive)$"),
    bankroll: float = Query(1000.0, ge=10.0, le=500000.0),
) -> Dict[str, Any]:
    profile_cfg = {
        "conservative": {"stake_mul": 0.65, "max_total_mul": 0.70, "max_team_mul": 0.75},
        "balanced": {"stake_mul": 1.0, "max_total_mul": 1.0, "max_team_mul": 1.0},
        "aggressive": {"stake_mul": 1.25, "max_total_mul": 1.20, "max_team_mul": 1.15},
    }[risk_profile]
    max_total_stake_fraction = min(1.0, max_total_stake_fraction * profile_cfg["max_total_mul"])
    max_team_stake_fraction = min(1.0, max_team_stake_fraction * profile_cfg["max_team_mul"])
    payload = mlb_edges_today(model_version=model_version)
    edges = payload.get("edges") or []
    candidates: List[Dict[str, Any]] = []
    rejected_counts: Dict[str, int] = {
        "quality": 0,
        "freshness": 0,
        "market_depth": 0,
        "uncertainty": 0,
        "edge_threshold": 0,
    }
    for edge in edges:
        quality = _to_float(edge.get("quality_score")) or 0.0
        if quality < min_quality_score:
            rejected_counts["quality"] += 1
            continue
        home_team = str(edge.get("home_team") or "")
        away_team = str(edge.get("away_team") or "")
        game_id = str(edge.get("game_id") or "")
        freshness = _to_float(edge.get("freshness_score")) or 0.45
        if freshness < min_freshness_score:
            rejected_counts["freshness"] += 1
            continue
        market_depth = int(_to_float(edge.get("market_depth")) or 0)
        if market_depth < min_market_depth:
            rejected_counts["market_depth"] += 1
            continue
        uncertainty = _to_float(edge.get("uncertainty_score")) or 0.8
        ml_ci_width = _to_float(edge.get("ml_confidence_interval_width"))
        total_band_width = _to_float(edge.get("total_band_width"))
        if (
            uncertainty > max_uncertainty_score
            or (ml_ci_width is not None and ml_ci_width > max_ml_ci_width)
            or (total_band_width is not None and total_band_width > max_total_band_width)
        ):
            rejected_counts["uncertainty"] += 1
            continue
        drivers = ((edge.get("explainability") or {}).get("drivers") or []) if isinstance(edge.get("explainability"), dict) else []
        ml_edge = abs(_to_float(edge.get("ml_edge_prob")) or 0.0)
        total_edge = abs(_to_float(edge.get("total_edge")) or 0.0)
        if ml_edge >= min_ml_edge_prob:
            ml_score = (quality * 0.62) + (ml_edge * 100.0 * 0.26) + (freshness * 100.0 * 0.12)
            ml_side = "home" if (_to_float(edge.get("ml_edge_prob")) or 0.0) >= 0 else "away"
            candidates.append(
                {
                    "game_id": game_id,
                    "home_team": home_team,
                    "away_team": away_team,
                    "market": "moneyline",
                    "selection": ml_side,
                    "edge_value": round(ml_edge, 4),
                    "quality_score": quality,
                    "freshness_score": round(freshness, 3),
                    "uncertainty_score": round(uncertainty, 4),
                    "raw_score": round(ml_score, 3),
                    "base_stake_fraction": (_to_float(edge.get("recommended_stake_fraction")) or 0.003)
                    * profile_cfg["stake_mul"],
                    "explainability": {"drivers": drivers},
                }
            )
        if total_edge >= min_total_edge:
            total_score = (quality * 0.58) + (total_edge * 14.0 * 0.30) + (freshness * 100.0 * 0.12)
            total_side = "over" if (_to_float(edge.get("total_edge")) or 0.0) >= 0 else "under"
            base_total_stake = (
                min(0.025, max(0.002, (quality / 100.0) * min(0.03, total_edge / 20.0)))
                * profile_cfg["stake_mul"]
            )
            candidates.append(
                {
                    "game_id": game_id,
                    "home_team": home_team,
                    "away_team": away_team,
                    "market": "total",
                    "selection": total_side,
                    "edge_value": round(total_edge, 3),
                    "quality_score": quality,
                    "freshness_score": round(freshness, 3),
                    "uncertainty_score": round(uncertainty, 4),
                    "raw_score": round(total_score, 3),
                    "base_stake_fraction": base_total_stake,
                    "explainability": {"drivers": drivers},
                }
            )
        if ml_edge < min_ml_edge_prob and total_edge < min_total_edge:
            rejected_counts["edge_threshold"] += 1

    candidates = sorted(candidates, key=lambda x: x["raw_score"], reverse=True)
    selected: List[Dict[str, Any]] = []
    team_play_count: Dict[str, int] = {}
    market_count: Dict[str, int] = {}
    selected_game_ids: Dict[str, int] = {}

    for c in candidates:
        if len(selected) >= max_results:
            break
        home = c["home_team"]
        away = c["away_team"]
        game_id = c["game_id"]
        market = c["market"]

        if team_play_count.get(home, 0) >= max_per_team_plays:
            continue
        if team_play_count.get(away, 0) >= max_per_team_plays:
            continue
        projected_market_count = market_count.get(market, 0) + 1
        projected_size = len(selected) + 1
        if projected_size > 1 and projected_market_count / projected_size > max_market_share:
            continue

        adjusted_score = float(c["raw_score"])
        if selected_game_ids.get(game_id, 0) > 0:
            adjusted_score *= max(0.05, 1.0 - correlation_penalty)
        if adjusted_score < 20.0:
            continue
        c2 = dict(c)
        c2["adjusted_score"] = round(adjusted_score, 3)
        selected.append(c2)
        selected_game_ids[game_id] = selected_game_ids.get(game_id, 0) + 1
        team_play_count[home] = team_play_count.get(home, 0) + 1
        team_play_count[away] = team_play_count.get(away, 0) + 1
        market_count[market] = market_count.get(market, 0) + 1

    base_sum = sum(max(0.0, _to_float(x.get("base_stake_fraction")) or 0.0) for x in selected)
    avg_uncertainty = (
        sum((_to_float(x.get("uncertainty_score")) or 0.0) for x in selected) / max(1, len(selected))
    )
    uncertainty_throttle = max(0.55, 1.0 - (0.45 * avg_uncertainty))
    adjusted_total_limit = max_total_stake_fraction * uncertainty_throttle
    scale = min(1.0, adjusted_total_limit / base_sum) if base_sum > 0 else 0.0
    team_stake: Dict[str, float] = {}
    final_selected: List[Dict[str, Any]] = []
    for x in selected:
        home = x["home_team"]
        away = x["away_team"]
        stake = (_to_float(x.get("base_stake_fraction")) or 0.0) * scale
        home_rem = max(0.0, max_team_stake_fraction - team_stake.get(home, 0.0))
        away_rem = max(0.0, max_team_stake_fraction - team_stake.get(away, 0.0))
        stake = min(stake, home_rem, away_rem)
        if stake < 0.001:
            continue
        team_stake[home] = team_stake.get(home, 0.0) + stake
        team_stake[away] = team_stake.get(away, 0.0) + stake
        item = dict(x)
        item["recommended_stake_fraction"] = round(stake, 4)
        item["portfolio_group"] = item["game_id"]
        final_selected.append(item)

    total_stake = round(sum(_to_float(x.get("recommended_stake_fraction")) or 0.0 for x in final_selected), 4)
    total_stake_amount = round(total_stake * bankroll, 2)
    for item in final_selected:
        frac = _to_float(item.get("recommended_stake_fraction")) or 0.0
        item["recommended_stake_amount"] = round(frac * bankroll, 2)
    return {
        "model_version": payload.get("model_version"),
        "count": len(final_selected),
        "filters": {
            "min_quality_score": min_quality_score,
            "min_ml_edge_prob": min_ml_edge_prob,
            "min_total_edge": min_total_edge,
            "max_results": max_results,
            "max_per_team_plays": max_per_team_plays,
            "max_market_share": max_market_share,
            "correlation_penalty": correlation_penalty,
            "max_total_stake_fraction": max_total_stake_fraction,
            "max_team_stake_fraction": max_team_stake_fraction,
            "min_freshness_score": min_freshness_score,
            "min_market_depth": min_market_depth,
            "max_uncertainty_score": max_uncertainty_score,
            "max_ml_ci_width": max_ml_ci_width,
            "max_total_band_width": max_total_band_width,
            "risk_profile": risk_profile,
            "bankroll": bankroll,
        },
        "portfolio_summary": {
            "total_recommended_stake_fraction": total_stake,
            "total_recommended_stake_amount": total_stake_amount,
            "avg_uncertainty_score": round(avg_uncertainty, 4),
            "uncertainty_throttle": round(uncertainty_throttle, 4),
            "adjusted_total_stake_limit": round(adjusted_total_limit, 4),
            "team_exposure": {k: round(v, 4) for k, v in sorted(team_stake.items(), key=lambda kv: kv[1], reverse=True)},
            "market_mix": market_count,
            "rejected_counts": rejected_counts,
        },
        "recommendations": final_selected,
    }


def _fetch_calibration_points(session: Any, model_version: str, lookback_days: int) -> List[Dict[str, Any]]:
    rows = session.execute(
        text(
            """
            WITH latest_proj AS (
              SELECT DISTINCT ON (mp.game_id)
                mp.game_id,
                mp.fg_home_win_prob,
                mp.fg_total_mean
              FROM mlb_market_projections mp
              JOIN games g ON g.id = mp.game_id
              WHERE mp.model_version = :model_version
                AND g.game_date >= CURRENT_DATE - make_interval(days => :lookback_days)
              ORDER BY mp.game_id, mp.created_at DESC
            )
            SELECT
              lp.game_id,
              lp.fg_home_win_prob,
              lp.fg_total_mean,
              mo.home_team_won,
              mo.final_total_runs
            FROM latest_proj lp
            JOIN mlb_market_outcomes mo ON mo.game_id = lp.game_id
            """
        ),
        {"model_version": model_version, "lookback_days": lookback_days},
    ).fetchall()
    return [dict(r._mapping) for r in rows]


def _bucketed_reliability(points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    buckets: List[List[Dict[str, Any]]] = [[] for _ in range(10)]
    for p in points:
        prob = float(p["fg_home_win_prob"])
        idx = min(9, max(0, int(prob * 10.0)))
        buckets[idx].append(p)

    out: List[Dict[str, Any]] = []
    for i, bucket in enumerate(buckets):
        if not bucket:
            continue
        preds = [float(x["fg_home_win_prob"]) for x in bucket]
        actual = [1.0 if x["home_team_won"] else 0.0 for x in bucket]
        out.append(
            {
                "bucket": f"{i*10:02d}-{(i+1)*10:02d}%",
                "count": len(bucket),
                "avg_pred_home_win_prob": round(sum(preds) / len(preds), 4),
                "actual_home_win_rate": round(sum(actual) / len(actual), 4),
                "calibration_gap": round(sum(preds) / len(preds) - sum(actual) / len(actual), 4),
            }
        )
    return out


@router.get("/markets/closing-lines")
def mlb_closing_lines(
    game_date: date = Query(..., description="UTC date"),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        rows = session.execute(
            text(
                """
                WITH latest_book AS (
                  SELECT DISTINCT ON (os.game_id, os.sportsbook_id, m.code)
                    os.game_id,
                    m.code AS market_code,
                    os.price_home,
                    os.price_away,
                    os.total_points,
                    os.over_price,
                    os.under_price,
                    os.captured_at
                  FROM odds_snapshots os
                  JOIN markets m ON m.id = os.market_id
                  JOIN games g ON g.id = os.game_id
                  JOIN seasons s ON s.id = g.season_id
                  JOIN leagues l ON l.id = s.league_id
                  WHERE l.code = 'mlb'
                    AND g.game_date = :game_date
                    AND m.code IN ('moneyline', 'total')
                  ORDER BY os.game_id, os.sportsbook_id, m.code, os.captured_at DESC
                )
                SELECT
                  g.id AS game_id,
                  home.name AS home_team,
                  away.name AS away_team,
                  AVG(CASE WHEN lb.market_code = 'moneyline' THEN lb.price_home END) AS closing_home_ml,
                  AVG(CASE WHEN lb.market_code = 'moneyline' THEN lb.price_away END) AS closing_away_ml,
                  AVG(CASE WHEN lb.market_code = 'total' THEN lb.total_points END) AS closing_total,
                  MAX(lb.captured_at) AS last_market_capture_at
                FROM games g
                JOIN seasons s ON s.id = g.season_id
                JOIN leagues l ON l.id = s.league_id
                JOIN teams home ON home.id = g.home_team_id
                JOIN teams away ON away.id = g.away_team_id
                LEFT JOIN latest_book lb ON lb.game_id = g.id
                WHERE l.code = 'mlb'
                  AND g.game_date = :game_date
                GROUP BY g.id, home.name, away.name
                ORDER BY g.start_time
                """
            ),
            {"game_date": game_date},
        ).fetchall()

        games: List[Dict[str, Any]] = []
        for r in rows:
            m = dict(r._mapping)
            games.append(
                {
                    "game_id": m["game_id"],
                    "home_team": m["home_team"],
                    "away_team": m["away_team"],
                    "closing_home_ml": _to_int(round(m["closing_home_ml"])) if m["closing_home_ml"] is not None else None,
                    "closing_away_ml": _to_int(round(m["closing_away_ml"])) if m["closing_away_ml"] is not None else None,
                    "closing_total": _to_float(m["closing_total"]),
                    "last_market_capture_at": m["last_market_capture_at"],
                }
            )
        return {"game_date": game_date, "games": games, "count": len(games)}
    finally:
        session.close()


@router.get("/metrics/clv")
def mlb_clv_metrics(
    model_version: Optional[str] = Query(None),
    lookback_days: int = Query(30, ge=7, le=365),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        effective_model_version = model_version or _resolve_active_model_version(session)
        rows = session.execute(
            text(
                """
                WITH latest_proj AS (
                  SELECT DISTINCT ON (mp.game_id)
                    mp.game_id,
                    mp.fg_home_win_prob,
                    mp.fair_fg_total
                  FROM mlb_market_projections mp
                  JOIN games g ON g.id = mp.game_id
                  WHERE mp.model_version = :model_version
                    AND g.game_date >= CURRENT_DATE - make_interval(days => :lookback_days)
                  ORDER BY mp.game_id, mp.created_at DESC
                ),
                ml_first AS (
                  SELECT os.game_id, AVG(os.price_home)::numeric AS open_home_ml, AVG(os.price_away)::numeric AS open_away_ml
                  FROM odds_snapshots os
                  JOIN markets m ON m.id = os.market_id
                  JOIN (
                    SELECT game_id, MIN(captured_at) AS t
                    FROM odds_snapshots os2 JOIN markets m2 ON m2.id = os2.market_id
                    WHERE m2.code = 'moneyline'
                    GROUP BY game_id
                  ) f ON f.game_id = os.game_id AND f.t = os.captured_at
                  WHERE m.code = 'moneyline'
                  GROUP BY os.game_id
                ),
                ml_last AS (
                  SELECT os.game_id, AVG(os.price_home)::numeric AS close_home_ml, AVG(os.price_away)::numeric AS close_away_ml
                  FROM odds_snapshots os
                  JOIN markets m ON m.id = os.market_id
                  JOIN (
                    SELECT game_id, MAX(captured_at) AS t
                    FROM odds_snapshots os2 JOIN markets m2 ON m2.id = os2.market_id
                    WHERE m2.code = 'moneyline'
                    GROUP BY game_id
                  ) f ON f.game_id = os.game_id AND f.t = os.captured_at
                  WHERE m.code = 'moneyline'
                  GROUP BY os.game_id
                ),
                total_first AS (
                  SELECT os.game_id, AVG(os.total_points)::numeric AS open_total
                  FROM odds_snapshots os
                  JOIN markets m ON m.id = os.market_id
                  JOIN (
                    SELECT game_id, MIN(captured_at) AS t
                    FROM odds_snapshots os2 JOIN markets m2 ON m2.id = os2.market_id
                    WHERE m2.code = 'total'
                    GROUP BY game_id
                  ) f ON f.game_id = os.game_id AND f.t = os.captured_at
                  WHERE m.code = 'total'
                  GROUP BY os.game_id
                ),
                total_last AS (
                  SELECT os.game_id, AVG(os.total_points)::numeric AS close_total
                  FROM odds_snapshots os
                  JOIN markets m ON m.id = os.market_id
                  JOIN (
                    SELECT game_id, MAX(captured_at) AS t
                    FROM odds_snapshots os2 JOIN markets m2 ON m2.id = os2.market_id
                    WHERE m2.code = 'total'
                    GROUP BY game_id
                  ) f ON f.game_id = os.game_id AND f.t = os.captured_at
                  WHERE m.code = 'total'
                  GROUP BY os.game_id
                )
                SELECT
                  lp.game_id,
                  lp.fg_home_win_prob,
                  lp.fair_fg_total,
                  mf.open_home_ml,
                  mf.open_away_ml,
                  ml.close_home_ml,
                  ml.close_away_ml,
                  tf.open_total,
                  tl.close_total
                FROM latest_proj lp
                LEFT JOIN ml_first mf ON mf.game_id = lp.game_id
                LEFT JOIN ml_last ml ON ml.game_id = lp.game_id
                LEFT JOIN total_first tf ON tf.game_id = lp.game_id
                LEFT JOIN total_last tl ON tl.game_id = lp.game_id
                """
            ),
            {"model_version": effective_model_version, "lookback_days": lookback_days},
        ).fetchall()
        items: List[Dict[str, Any]] = []
        for r in rows:
            m = dict(r._mapping)
            open_home = _to_int(round(m["open_home_ml"])) if m["open_home_ml"] is not None else None
            open_away = _to_int(round(m["open_away_ml"])) if m["open_away_ml"] is not None else None
            close_home = _to_int(round(m["close_home_ml"])) if m["close_home_ml"] is not None else None
            close_away = _to_int(round(m["close_away_ml"])) if m["close_away_ml"] is not None else None
            open_total = _to_float(m["open_total"])
            close_total = _to_float(m["close_total"])
            model_home_prob = _to_float(m["fg_home_win_prob"])
            fair_total = _to_float(m["fair_fg_total"])

            ml_pick = None
            ml_clv = None
            if model_home_prob is not None and open_home is not None and open_away is not None:
                open_home_prob = _american_implied_prob(open_home)
                if open_home_prob is not None:
                    ml_pick = "home" if model_home_prob > open_home_prob else "away"
                    if close_home is not None and close_away is not None:
                        if ml_pick == "home":
                            ml_clv = round(
                                (_american_implied_prob(close_home) or 0.0) - (_american_implied_prob(open_home) or 0.0),
                                4,
                            )
                        else:
                            ml_clv = round(
                                (_american_implied_prob(close_away) or 0.0) - (_american_implied_prob(open_away) or 0.0),
                                4,
                            )

            total_pick = None
            total_clv = None
            if fair_total is not None and open_total is not None and close_total is not None:
                total_pick = "over" if fair_total > open_total else "under"
                total_clv = (
                    round(close_total - open_total, 3)
                    if total_pick == "over"
                    else round(open_total - close_total, 3)
                )

            items.append(
                {
                    "game_id": m["game_id"],
                    "ml_pick": ml_pick,
                    "ml_clv": ml_clv,
                    "total_pick": total_pick,
                    "total_clv": total_clv,
                    "open_home_ml": open_home,
                    "close_home_ml": close_home,
                    "open_total": open_total,
                    "close_total": close_total,
                }
            )

        ml_vals = [x["ml_clv"] for x in items if x["ml_clv"] is not None]
        total_vals = [x["total_clv"] for x in items if x["total_clv"] is not None]
        return {
            "model_version": effective_model_version,
            "lookback_days": lookback_days,
            "count": len(items),
            "avg_ml_clv": round(sum(ml_vals) / len(ml_vals), 5) if ml_vals else None,
            "avg_total_clv": round(sum(total_vals) / len(total_vals), 5) if total_vals else None,
            "items": items,
        }
    finally:
        session.close()


@router.get("/metrics/calibration")
def mlb_calibration_metrics(
    model_version: Optional[str] = Query(None),
    lookback_days: int = Query(30, ge=7, le=365),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        effective_model_version = model_version or _resolve_active_model_version(session)
        points = _fetch_calibration_points(session, effective_model_version, lookback_days)
        if not points:
            return {
                "model_version": effective_model_version,
                "lookback_days": lookback_days,
                "sample_size": 0,
                "brier_ml": None,
                "mae_total_runs": None,
                "avg_pred_home_win_prob": None,
                "actual_home_win_rate": None,
                "buckets": [],
                "reliability_curve": [],
            }

        probs = [float(x["fg_home_win_prob"]) for x in points]
        actual = [1.0 if x["home_team_won"] else 0.0 for x in points]
        totals_pred = [float(x["fg_total_mean"]) for x in points]
        totals_actual = [float(x["final_total_runs"]) for x in points]
        brier = sum((p - a) ** 2 for p, a in zip(probs, actual)) / len(points)
        mae_total = sum(abs(p - a) for p, a in zip(totals_pred, totals_actual)) / len(points)
        buckets = _bucketed_reliability(points)
        return {
            "model_version": effective_model_version,
            "lookback_days": lookback_days,
            "sample_size": len(points),
            "brier_ml": round(brier, 6),
            "mae_total_runs": round(mae_total, 4),
            "avg_pred_home_win_prob": round(sum(probs) / len(probs), 4),
            "actual_home_win_rate": round(sum(actual) / len(actual), 4),
            "buckets": buckets,
            "reliability_curve": buckets,
        }
    finally:
        session.close()


@router.get("/metrics/version-compare")
def mlb_version_compare(
    base_version: str = Query(DEFAULT_MODEL_VERSION),
    challenger_version: str = Query("mlb-v2-pitch-sim"),
    lookback_days: int = Query(30, ge=7, le=365),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        base_points = _fetch_calibration_points(session, base_version, lookback_days)
        ch_points = _fetch_calibration_points(session, challenger_version, lookback_days)

        def _summary(points: List[Dict[str, Any]]) -> Dict[str, Optional[float]]:
            if not points:
                return {"sample_size": 0, "brier_ml": None, "mae_total_runs": None}
            probs = [float(x["fg_home_win_prob"]) for x in points]
            actual = [1.0 if x["home_team_won"] else 0.0 for x in points]
            totals_pred = [float(x["fg_total_mean"]) for x in points]
            totals_actual = [float(x["final_total_runs"]) for x in points]
            brier = sum((p - a) ** 2 for p, a in zip(probs, actual)) / len(points)
            mae_total = sum(abs(p - a) for p, a in zip(totals_pred, totals_actual)) / len(points)
            return {
                "sample_size": float(len(points)),
                "brier_ml": round(brier, 6),
                "mae_total_runs": round(mae_total, 4),
            }

        base = _summary(base_points)
        challenger = _summary(ch_points)
        brier_delta = None
        mae_delta = None
        if base["brier_ml"] is not None and challenger["brier_ml"] is not None:
            brier_delta = round(challenger["brier_ml"] - base["brier_ml"], 6)
        if base["mae_total_runs"] is not None and challenger["mae_total_runs"] is not None:
            mae_delta = round(challenger["mae_total_runs"] - base["mae_total_runs"], 4)

        return {
            "lookback_days": lookback_days,
            "base_version": {"model_version": base_version, **base},
            "challenger_version": {"model_version": challenger_version, **challenger},
            "delta_challenger_minus_base": {
                "brier_ml": brier_delta,
                "mae_total_runs": mae_delta,
            },
        }
    finally:
        session.close()


@router.get("/metrics/regime-calibration")
def mlb_regime_calibration(
    model_version: Optional[str] = Query(None),
    lookback_days: int = Query(45, ge=7, le=365),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        effective_model_version = model_version or _resolve_active_model_version(session)
        rows = session.execute(
            text(
                """
                WITH latest_proj AS (
                  SELECT DISTINCT ON (mp.game_id)
                    mp.game_id,
                    mp.fg_home_win_prob,
                    mp.fg_total_mean
                  FROM mlb_market_projections mp
                  JOIN games g ON g.id = mp.game_id
                  WHERE mp.model_version = :model_version
                    AND g.game_date >= CURRENT_DATE - make_interval(days => :lookback_days)
                  ORDER BY mp.game_id, mp.created_at DESC
                ),
                ml_last AS (
                  SELECT os.game_id, AVG(os.price_home)::numeric AS close_home_ml
                  FROM odds_snapshots os
                  JOIN markets m ON m.id = os.market_id
                  JOIN (
                    SELECT game_id, MAX(captured_at) AS t
                    FROM odds_snapshots os2
                    JOIN markets m2 ON m2.id = os2.market_id
                    WHERE m2.code = 'moneyline'
                    GROUP BY game_id
                  ) x ON x.game_id = os.game_id AND x.t = os.captured_at
                  WHERE m.code = 'moneyline'
                  GROUP BY os.game_id
                ),
                total_last AS (
                  SELECT os.game_id, AVG(os.total_points)::numeric AS close_total
                  FROM odds_snapshots os
                  JOIN markets m ON m.id = os.market_id
                  JOIN (
                    SELECT game_id, MAX(captured_at) AS t
                    FROM odds_snapshots os2
                    JOIN markets m2 ON m2.id = os2.market_id
                    WHERE m2.code = 'total'
                    GROUP BY game_id
                  ) x ON x.game_id = os.game_id AND x.t = os.captured_at
                  WHERE m.code = 'total'
                  GROUP BY os.game_id
                )
                SELECT
                  lp.game_id,
                  lp.fg_home_win_prob,
                  lp.fg_total_mean,
                  mo.home_team_won,
                  mo.final_total_runs,
                  ml.close_home_ml,
                  tl.close_total,
                  c.weather_temp_f,
                  c.park_factor_runs
                FROM latest_proj lp
                JOIN mlb_market_outcomes mo ON mo.game_id = lp.game_id
                LEFT JOIN ml_last ml ON ml.game_id = lp.game_id
                LEFT JOIN total_last tl ON tl.game_id = lp.game_id
                LEFT JOIN mlb_game_context c ON c.game_id = lp.game_id
                """
            ),
            {"model_version": effective_model_version, "lookback_days": lookback_days},
        ).fetchall()

        regimes: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            m = dict(r._mapping)
            model_prob = _to_float(m.get("fg_home_win_prob"))
            model_total = _to_float(m.get("fg_total_mean"))
            actual_win = 1.0 if bool(m.get("home_team_won")) else 0.0
            actual_total = _to_float(m.get("final_total_runs"))
            if model_prob is None or model_total is None or actual_total is None:
                continue
            close_ml = _to_int(round(m["close_home_ml"])) if m.get("close_home_ml") is not None else None
            market_prob = _american_implied_prob(close_ml)
            close_total = _to_float(m.get("close_total"))
            temp = _to_float(m.get("weather_temp_f"))
            park = _to_float(m.get("park_factor_runs"))

            favdog = "fav" if market_prob is not None and market_prob >= 0.55 else "dog_or_even"
            total_band = "high_total" if close_total is not None and close_total >= 9.0 else "low_total"
            weather_band = "hot" if temp is not None and temp >= 78 else "cool_or_mid"
            park_band = "hitter_park" if park is not None and park >= 1.03 else "neutral_or_pitcher_park"
            key = f"{favdog}|{total_band}|{weather_band}|{park_band}"

            reg = regimes.setdefault(
                key,
                {
                    "regime": key,
                    "count": 0,
                    "brier_sum": 0.0,
                    "mae_total_sum": 0.0,
                    "avg_model_prob_sum": 0.0,
                    "avg_actual_win_sum": 0.0,
                },
            )
            reg["count"] += 1
            reg["brier_sum"] += (model_prob - actual_win) ** 2
            reg["mae_total_sum"] += abs(model_total - actual_total)
            reg["avg_model_prob_sum"] += model_prob
            reg["avg_actual_win_sum"] += actual_win

        out: List[Dict[str, Any]] = []
        for reg in regimes.values():
            n = max(1, int(reg["count"]))
            out.append(
                {
                    "regime": reg["regime"],
                    "count": reg["count"],
                    "brier_ml": round(reg["brier_sum"] / n, 6),
                    "mae_total_runs": round(reg["mae_total_sum"] / n, 4),
                    "avg_model_home_win_prob": round(reg["avg_model_prob_sum"] / n, 4),
                    "actual_home_win_rate": round(reg["avg_actual_win_sum"] / n, 4),
                }
            )
        out = sorted(out, key=lambda x: int(x["count"]), reverse=True)
        return {
            "model_version": effective_model_version,
            "lookback_days": lookback_days,
            "regimes": out,
            "count": len(out),
        }
    finally:
        session.close()


@router.get("/ops/snapshots")
def mlb_ops_snapshots(
    limit: int = Query(20, ge=1, le=200),
    model_version: Optional[str] = Query(None),
    pipeline_stage: Optional[str] = Query(None),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        where: List[str] = []
        params: Dict[str, Any] = {"limit": limit}
        if model_version:
            where.append("model_version = :model_version")
            params["model_version"] = model_version
        if pipeline_stage:
            where.append("pipeline_stage = :pipeline_stage")
            params["pipeline_stage"] = pipeline_stage
        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        rows = session.execute(
            text(
                f"""
                SELECT run_date, model_version, pipeline_stage, payload, created_at
                FROM mlb_model_run_snapshots
                {where_sql}
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            params,
        ).fetchall()
        snapshots = [dict(r._mapping) for r in rows]
        return {"count": len(snapshots), "snapshots": snapshots}
    finally:
        session.close()


@router.get("/data-lake/raw-objects")
def mlb_data_lake_raw_objects(
    object_type: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    as_of_date: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        where: List[str] = []
        params: Dict[str, Any] = {"limit": limit}
        if object_type:
            where.append("object_type = :object_type")
            params["object_type"] = object_type
        if source:
            where.append("source = :source")
            params["source"] = source
        if as_of_date:
            where.append("as_of_date = :as_of_date")
            params["as_of_date"] = as_of_date
        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        rows = session.execute(
            text(
                f"""
                SELECT source, object_type, object_key, as_of_date, checksum, fetched_at, updated_at
                FROM mlb_raw_data_objects
                {where_sql}
                ORDER BY as_of_date DESC, updated_at DESC
                LIMIT :limit
                """
            ),
            params,
        ).fetchall()
        objs = [dict(r._mapping) for r in rows]
        return {"count": len(objs), "objects": objs}
    finally:
        session.close()


@router.get("/data-lake/team-stats")
def mlb_data_lake_team_stats(
    season: Optional[int] = Query(None, ge=2000, le=2100),
    as_of_date: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=500),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        where: List[str] = []
        params: Dict[str, Any] = {"limit": limit}
        if season is not None:
            where.append("season = :season")
            params["season"] = int(season)
        if as_of_date:
            where.append("as_of_date = :as_of_date")
            params["as_of_date"] = as_of_date
        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        rows = session.execute(
            text(
                f"""
                SELECT
                  as_of_date, season, team_id, team_name,
                  offense_index, offense_split_vs_l, offense_split_vs_r,
                  recent_form_index, wins, losses, run_diff, source, updated_at
                FROM mlb_team_daily_stats
                {where_sql}
                ORDER BY as_of_date DESC, team_id
                LIMIT :limit
                """
            ),
            params,
        ).fetchall()
        out = [dict(r._mapping) for r in rows]
        return {"count": len(out), "team_stats": out}
    finally:
        session.close()


@router.get("/data-lake/player-stats")
def mlb_data_lake_player_stats(
    season: Optional[int] = Query(None, ge=2000, le=2100),
    as_of_date: Optional[str] = Query(None),
    stat_group: Optional[str] = Query(None),
    team_id: Optional[int] = Query(None),
    limit: int = Query(200, ge=1, le=500),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        where: List[str] = []
        params: Dict[str, Any] = {"limit": limit}
        if season is not None:
            where.append("season = :season")
            params["season"] = int(season)
        if as_of_date:
            where.append("as_of_date = :as_of_date")
            params["as_of_date"] = as_of_date
        if stat_group:
            where.append("stat_group = :stat_group")
            params["stat_group"] = stat_group
        if team_id is not None:
            where.append("team_id = :team_id")
            params["team_id"] = int(team_id)
        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        rows = session.execute(
            text(
                f"""
                SELECT
                  as_of_date, season, player_id, player_name, team_id,
                  stat_group, split_key, metrics, source, updated_at
                FROM mlb_player_daily_stats
                {where_sql}
                ORDER BY as_of_date DESC, player_id
                LIMIT :limit
                """
            ),
            params,
        ).fetchall()
        out = [dict(r._mapping) for r in rows]
        return {"count": len(out), "player_stats": out}
    finally:
        session.close()


@router.get("/ops/nowcast-runs")
def mlb_nowcast_runs(
    limit: int = Query(30, ge=1, le=300),
    model_version: Optional[str] = Query(None),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        params: Dict[str, Any] = {"limit": limit}
        where = "WHERE pipeline_stage = 'lineup_nowcast_repricing'"
        if model_version:
            where += " AND model_version = :model_version"
            params["model_version"] = model_version
        rows = session.execute(
            text(
                f"""
                SELECT run_date, model_version, pipeline_stage, payload, created_at
                FROM mlb_model_run_snapshots
                {where}
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            params,
        ).fetchall()
        runs: List[Dict[str, Any]] = []
        for r in rows:
            row = dict(r._mapping)
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            runs.append(
                {
                    "run_date": row.get("run_date"),
                    "created_at": row.get("created_at"),
                    "model_version": row.get("model_version"),
                    "games_seen": int(_safe_float(payload.get("games_seen")) or 0),
                    "context_rows_updated": int(_safe_float(payload.get("context_rows_updated")) or 0),
                    "repriced_base": int(_safe_float(payload.get("repriced_base")) or 0),
                    "repriced_challenger": int(_safe_float(payload.get("repriced_challenger")) or 0),
                    "avg_nowcast_confidence": _safe_payload_float(payload, "avg_nowcast_confidence"),
                    "avg_prev_confidence": _safe_payload_float(payload, "avg_prev_confidence"),
                    "avg_confidence_delta": _safe_payload_float(payload, "avg_confidence_delta"),
                    "avg_freshness_score": _safe_payload_float(payload, "avg_freshness_score"),
                    "lineup_confirmed_share": _safe_payload_float(payload, "lineup_confirmed_share"),
                    "horizon_hours": int(_safe_float(payload.get("horizon_hours")) or 0),
                }
            )
        return {"count": len(runs), "runs": runs}
    finally:
        session.close()


@router.get("/ops/nowcast-confidence-drift")
def mlb_nowcast_confidence_drift(
    lookback_hours: int = Query(24, ge=1, le=168),
    model_version: Optional[str] = Query(None),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        params: Dict[str, Any] = {"lookback_hours": int(lookback_hours)}
        where = """
            WHERE pipeline_stage = 'lineup_nowcast_repricing'
              AND created_at >= NOW() - make_interval(hours => :lookback_hours)
        """
        if model_version:
            where += " AND model_version = :model_version"
            params["model_version"] = model_version
        rows = session.execute(
            text(
                f"""
                SELECT payload, created_at
                FROM mlb_model_run_snapshots
                {where}
                ORDER BY created_at DESC
                """
            ),
            params,
        ).fetchall()
        payloads: List[Dict[str, Any]] = []
        for r in rows:
            payload = dict(r._mapping).get("payload")
            if not isinstance(payload, dict):
                continue
            payloads.append(payload)
        summary = _aggregate_nowcast_snapshot_payloads(payloads)
        return {
            "lookback_hours": lookback_hours,
            "model_version": model_version,
            **summary,
        }
    finally:
        session.close()


@router.get("/ops/backtest-runs")
def mlb_backtest_runs(
    limit: int = Query(20, ge=1, le=200),
    model_version: Optional[str] = Query(None),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        params: Dict[str, Any] = {"limit": limit}
        where = "WHERE pipeline_stage = 'walkforward_backtest'"
        if model_version:
            where += " AND model_version = :model_version"
            params["model_version"] = model_version
        rows = session.execute(
            text(
                f"""
                SELECT run_date, model_version, payload, created_at
                FROM mlb_model_run_snapshots
                {where}
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            params,
        ).fetchall()
        out: List[Dict[str, Any]] = []
        for row in rows:
            m = dict(row._mapping)
            payload = m.get("payload") if isinstance(m.get("payload"), dict) else {}
            out.append(
                {
                    "run_date": m.get("run_date"),
                    "created_at": m.get("created_at"),
                    "model_version": m.get("model_version"),
                    "fold_count": int(_safe_float(payload.get("fold_count")) or 0),
                    "sample_size": int(_safe_float(payload.get("sample_size")) or 0),
                    "base_brier_ml": _safe_float(payload.get("base_brier_ml")),
                    "calibrated_brier_ml": _safe_float(payload.get("calibrated_brier_ml")),
                    "brier_improvement": _safe_float(payload.get("brier_improvement")),
                    "mae_improvement": _safe_float(payload.get("mae_improvement")),
                    "leakage_violations": int(_safe_float(payload.get("leakage_violations")) or 0),
                }
            )
        return {"count": len(out), "runs": out}
    finally:
        session.close()


@router.get("/ops/model-card")
def mlb_model_card(model_version: Optional[str] = Query(None)) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        effective_model_version = model_version or _resolve_active_model_version(session)
        snapshots = session.execute(
            text(
                """
                SELECT pipeline_stage, payload, created_at
                FROM mlb_model_run_snapshots
                WHERE model_version = :model_version
                  AND pipeline_stage IN (
                    'quality_snapshot',
                    'lineup_nowcast_repricing',
                    'walkforward_backtest',
                    'determinism_check',
                    'feature_ablation'
                  )
                ORDER BY created_at DESC
                """
            ),
            {"model_version": effective_model_version},
        ).fetchall()
        latest_by_stage: Dict[str, Dict[str, Any]] = {}
        for row in snapshots:
            stage = str(row.pipeline_stage)
            if stage in latest_by_stage:
                continue
            latest_by_stage[stage] = {
                "payload": row.payload if isinstance(row.payload, dict) else {},
                "created_at": row.created_at,
            }
        alert_count = session.execute(
            text(
                """
                SELECT COUNT(*)::int AS c
                FROM mlb_alert_events
                WHERE created_at >= NOW() - INTERVAL '24 hours'
                """
            )
        ).scalar_one()
        quality = latest_by_stage.get("quality_snapshot", {}).get("payload", {})
        backtest = latest_by_stage.get("walkforward_backtest", {}).get("payload", {})
        determinism = latest_by_stage.get("determinism_check", {}).get("payload", {})
        nowcast = latest_by_stage.get("lineup_nowcast_repricing", {}).get("payload", {})
        return {
            "model_version": effective_model_version,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "quality_snapshot": {
                "created_at": latest_by_stage.get("quality_snapshot", {}).get("created_at"),
                "sample_size": int(_safe_float(quality.get("sample_size")) or 0),
                "brier_ml": _safe_float(quality.get("brier_ml")),
                "mae_total_runs": _safe_float(quality.get("mae_total_runs")),
                "ece": _safe_float(quality.get("ece")),
                "max_bin_error": _safe_float(quality.get("max_bin_error")),
                "leakage_violations": int(_safe_float(quality.get("leakage_violations")) or 0),
            },
            "backtest": {
                "created_at": latest_by_stage.get("walkforward_backtest", {}).get("created_at"),
                "fold_count": int(_safe_float(backtest.get("fold_count")) or 0),
                "sample_size": int(_safe_float(backtest.get("sample_size")) or 0),
                "brier_improvement": _safe_float(backtest.get("brier_improvement")),
            },
            "nowcast": {
                "created_at": latest_by_stage.get("lineup_nowcast_repricing", {}).get("created_at"),
                "avg_confidence_delta": _safe_float(nowcast.get("avg_confidence_delta")),
                "lineup_confirmed_share": _safe_float(nowcast.get("lineup_confirmed_share")),
            },
            "determinism": {
                "created_at": latest_by_stage.get("determinism_check", {}).get("created_at"),
                "deterministic": bool(determinism.get("deterministic", False)),
            },
            "assumptions": [
                "Model outputs are generated pre-result and evaluated on completed outcomes only.",
                "Calibration uses rolling historical windows and is monitored with ECE/max-bin-error.",
                "Premium feed applies uncertainty, freshness, and market-depth guardrails before recommendations.",
            ],
            "recent_alert_count_24h": int(alert_count),
        }
    finally:
        session.close()


@router.get("/ops/active-model")
def mlb_active_model() -> Dict[str, Any]:
    session = SessionLocal()
    try:
        row = session.execute(
            text(
                """
                SELECT state_key, active_model_version, previous_model_version, reason, updated_at
                FROM mlb_model_runtime_state
                WHERE state_key = :state_key
                LIMIT 1
                """
            ),
            {"state_key": MODEL_STATE_KEY},
        ).fetchone()
        if not row:
            return {
                "state_key": MODEL_STATE_KEY,
                "active_model_version": DEFAULT_MODEL_VERSION,
                "previous_model_version": None,
                "reason": "default",
                "updated_at": None,
            }
        return dict(row._mapping)
    finally:
        session.close()


@router.post("/ops/active-model")
def set_mlb_active_model(
    model_version: str = Query(..., min_length=3, max_length=64),
    reason: str = Query("manual-override", min_length=3, max_length=200),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        prev = session.execute(
            text(
                """
                SELECT active_model_version
                FROM mlb_model_runtime_state
                WHERE state_key = :state_key
                LIMIT 1
                """
            ),
            {"state_key": MODEL_STATE_KEY},
        ).fetchone()
        previous_model_version = str(prev[0]) if prev else None
        session.execute(
            text(
                """
                INSERT INTO mlb_model_runtime_state (
                  state_key, active_model_version, previous_model_version, reason, updated_at
                ) VALUES (
                  :state_key, :active_model_version, :previous_model_version, :reason, NOW()
                )
                ON CONFLICT (state_key) DO UPDATE SET
                  active_model_version = EXCLUDED.active_model_version,
                  previous_model_version = EXCLUDED.previous_model_version,
                  reason = EXCLUDED.reason,
                  updated_at = EXCLUDED.updated_at
                """
            ),
            {
                "state_key": MODEL_STATE_KEY,
                "active_model_version": model_version,
                "previous_model_version": previous_model_version,
                "reason": reason,
            },
        )
        session.commit()
        return {
            "state_key": MODEL_STATE_KEY,
            "active_model_version": model_version,
            "previous_model_version": previous_model_version,
            "reason": reason,
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@router.get("/ops/alerts")
def mlb_alert_events(
    limit: int = Query(50, ge=1, le=200),
    severity: Optional[str] = Query(None),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        if severity:
            rows = session.execute(
                text(
                    """
                    SELECT id, alert_type, severity, payload, created_at
                    FROM mlb_alert_events
                    WHERE severity = :severity
                    ORDER BY created_at DESC
                    LIMIT :limit
                    """
                ),
                {"severity": severity, "limit": limit},
            ).fetchall()
        else:
            rows = session.execute(
                text(
                    """
                    SELECT id, alert_type, severity, payload, created_at
                    FROM mlb_alert_events
                    ORDER BY created_at DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).fetchall()
        alerts = [dict(r._mapping) for r in rows]
        return {"count": len(alerts), "alerts": alerts}
    finally:
        session.close()


@router.get("/ops/go-no-go")
def mlb_go_no_go(
    model_version: Optional[str] = Query(None),
    min_sample_size: int = Query(120, ge=1, le=5000),
    min_calendar_days: int = Query(14, ge=1, le=365),
    max_last_game_age_days: int = Query(3, ge=0, le=30),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        effective_model_version = model_version or _resolve_active_model_version(session)
        snapshot_row = session.execute(
            text(
                """
                SELECT run_date, payload, created_at
                FROM mlb_model_run_snapshots
                WHERE model_version = :model_version
                  AND pipeline_stage = 'quality_snapshot'
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"model_version": effective_model_version},
        ).fetchone()
        if not snapshot_row:
            return {
                "status": "red",
                "model_version": effective_model_version,
                "reason": "missing_quality_snapshot",
                "checks": {
                    "sample_size_ok": False,
                    "calendar_days_ok": False,
                    "freshness_ok": False,
                    "alerts_ok": True,
                },
            }

        payload = dict(snapshot_row._mapping).get("payload") or {}
        sample_size = int(_safe_float(payload.get("sample_size")) or 0)
        calendar_days = int(_safe_float(payload.get("calendar_days_covered")) or 0)
        last_game_date = _safe_date(payload.get("last_game_date"))

        warning_count = session.execute(
            text(
                """
                SELECT COUNT(*)::int AS c
                FROM mlb_alert_events
                WHERE severity = 'warning'
                  AND created_at >= NOW() - INTERVAL '24 hours'
                """
            )
        ).scalar_one()

        classification = _classify_go_no_go(
            sample_size=sample_size,
            calendar_days=calendar_days,
            last_game_date=last_game_date,
            warning_alerts_24h=int(warning_count),
            min_sample_size=min_sample_size,
            min_calendar_days=min_calendar_days,
            max_last_game_age_days=max_last_game_age_days,
        )
        return {
            "model_version": effective_model_version,
            "status": classification["status"],
            "checks": classification["checks"],
            "reasons": classification["reasons"],
            "last_game_age_days": classification["last_game_age_days"],
            "quality_snapshot_created_at": snapshot_row.created_at,
            "metrics": {
                "sample_size": sample_size,
                "calendar_days_covered": calendar_days,
                "last_game_date": last_game_date.isoformat() if last_game_date else None,
                "brier_ml": _safe_float(payload.get("brier_ml")),
                "mae_total_runs": _safe_float(payload.get("mae_total_runs")),
                "avg_ml_clv": _safe_float(payload.get("avg_ml_clv")),
                "avg_total_clv": _safe_float(payload.get("avg_total_clv")),
            },
            "recent_warning_alerts_24h": int(warning_count),
        }
    finally:
        session.close()
