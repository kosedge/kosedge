from __future__ import annotations

import logging
import os
import re
import uuid
import hashlib
import json
import math
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests
from sqlalchemy import text

from .celery_app import celery_app
from .db import SessionLocal
from .services.mlb_data import (
    build_team_offense_context,
    fetch_mlb_standings,
    fetch_forecast_for_game,
    fetch_game_lineup_features,
    fetch_mlb_schedule,
    fetch_team_hitting_profile,
    fetch_team_roster,
    fetch_team_bullpen_fatigue,
    lineup_confidence,
    park_factor_for_team,
    starter_identity_features,
    umpire_run_factor,
)
from .services.mlb_pitch_simulator import simulate_mlb_game_pitch_by_pitch
from .services.mlb_simulator import DEFAULT_MODEL_VERSION, MlbGameInputs, simulate_mlb_game
from .services.nfl_data import (
    fetch_nfl_schedule,
    rest_days_from_schedule,
    team_strength_from_record,
)
from .services.nfl_injury_nowcast import fetch_nfl_injury_nowcast
from .services.nfl_matchup_features import (
    fetch_latest_matchup_feature_pack,
    matchup_pack_to_sim_input_kwargs,
)
from .services.nfl_simulator import (
    DEFAULT_NFL_MODEL_VERSION,
    NflGameInputs,
    simulate_nfl_game,
)
from .services.nfl_player_projection_engine import (
    PlayerFeatureInputs,
    baseline_projection_from_features,
    evaluate_prop_edge,
    fantasy_points_from_projection,
)
from .services.nfl_player_identity import (
    DEFAULT_RESOLVER_VERSION,
    IdentityInput,
    apply_manual_mapping_resolution,
    compute_identity_quality_snapshot,
    persist_identity_quality_snapshot,
    resolve_and_persist_player_identity,
)
from .services.nfl_totals_calibration import (
    apply_totals_calibration,
    fetch_nfl_totals_calibration,
)
from .services.odds_api import fetch_odds

log = logging.getLogger(__name__)

SPORT_MAP: Dict[str, Tuple[str, str, str]] = {
    # odds-api sport_key -> (sport_code, sport_name, league_name)
    "basketball_ncaab": ("ncaam", "NCAAM", "NCAA Men's Basketball"),
    "baseball_mlb": ("mlb", "MLB", "Major League Baseball"),
    "basketball_nba": ("nba", "NBA", "National Basketball Association"),
    "americanfootball_nfl": ("nfl", "NFL", "National Football League"),
}

MARKET_MAP: Dict[str, str] = {
    "h2h": "moneyline",
    "spreads": "spread",
    "totals": "total",
}

MODEL_STATE_KEY = "mlb_active_model"
NFL_MODEL_STATE_KEY = "nfl_active_model"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso_datetime(v: Optional[str]) -> Optional[datetime]:
    if not v:
        return None
    try:
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        return None


def _abbr_for_team(team_name: str) -> str:
    letters = re.findall(r"[A-Za-z]+", team_name or "")
    if not letters:
        return "TEAM"
    if len(letters) == 1:
        return letters[0][:6].upper()
    # Prefer 2+2 style chunks to avoid collisions like "PP" across MLB teams.
    if len(letters) == 2:
        return f"{letters[0][:2]}{letters[1][:2]}".upper()[:6]
    parts = [letters[0][:2], letters[1][:2], letters[2][:2]]
    return "".join(parts).upper()[:6]


def _extract_outcome_map(market: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for o in market.get("outcomes") or []:
        name = (o.get("name") or "").strip()
        if name:
            out[name] = o
    return out


def _extract_snapshot_values(
    market_key: str,
    market: Dict[str, Any],
    home_team: str,
    away_team: str,
) -> Optional[Dict[str, Optional[float]]]:
    outcomes = _extract_outcome_map(market)
    if market_key == "h2h":
        home = outcomes.get(home_team)
        away = outcomes.get(away_team)
        if not home or not away:
            return None
        return {
            "price_home": home.get("price"),
            "price_away": away.get("price"),
            "spread_home": None,
            "spread_away": None,
            "total_points": None,
            "over_price": None,
            "under_price": None,
        }

    if market_key == "spreads":
        home = outcomes.get(home_team)
        away = outcomes.get(away_team)
        if not home or not away:
            return None
        return {
            "price_home": home.get("price"),
            "price_away": away.get("price"),
            "spread_home": home.get("point"),
            "spread_away": away.get("point"),
            "total_points": None,
            "over_price": None,
            "under_price": None,
        }

    if market_key == "totals":
        over = outcomes.get("Over")
        under = outcomes.get("Under")
        if not over or not under:
            return None
        total_points = over.get("point") if over.get("point") is not None else under.get("point")
        return {
            "price_home": None,
            "price_away": None,
            "spread_home": None,
            "spread_away": None,
            "total_points": total_points,
            "over_price": over.get("price"),
            "under_price": under.get("price"),
        }

    return None


def _get_or_create(
    session: Any,
    table: str,
    where_sql: str,
    where_params: Dict[str, Any],
    insert_sql: str,
    insert_params: Dict[str, Any],
) -> str:
    found = session.execute(
        text(f"SELECT id FROM {table} WHERE {where_sql} LIMIT 1"),
        where_params,
    ).fetchone()
    if found:
        return str(found[0])

    new_id = str(uuid.uuid4())
    session.execute(
        text(insert_sql),
        {"id": new_id, **insert_params},
    )
    return new_id


def _ensure_hierarchy(
    session: Any,
    *,
    sport_key: str,
    game_dt: datetime,
    home_team: str,
    away_team: str,
    event_id: str,
) -> Tuple[str, str, str, str, str]:
    sport_code, sport_name, league_name = SPORT_MAP.get(
        sport_key,
        ("unknown", sport_key.upper(), sport_key.upper()),
    )
    season_year = game_dt.year

    sport_id = _get_or_create(
        session,
        table="sports",
        where_sql="code = :code",
        where_params={"code": sport_code},
        insert_sql="""
            INSERT INTO sports (id, code, name, created_at)
            VALUES (:id, :code, :name, :created_at)
        """,
        insert_params={"code": sport_code, "name": sport_name, "created_at": _now_utc()},
    )

    league_id = _get_or_create(
        session,
        table="leagues",
        where_sql="sport_id = :sport_id AND code = :code",
        where_params={"sport_id": sport_id, "code": sport_code},
        insert_sql="""
            INSERT INTO leagues (id, sport_id, code, name, created_at)
            VALUES (:id, :sport_id, :code, :name, :created_at)
        """,
        insert_params={
            "sport_id": sport_id,
            "code": sport_code,
            "name": league_name,
            "created_at": _now_utc(),
        },
    )

    season_id = _get_or_create(
        session,
        table="seasons",
        where_sql="league_id = :league_id AND season_year = :season_year",
        where_params={"league_id": league_id, "season_year": season_year},
        insert_sql="""
            INSERT INTO seasons (id, league_id, season_year, created_at)
            VALUES (:id, :league_id, :season_year, :created_at)
        """,
        insert_params={"league_id": league_id, "season_year": season_year, "created_at": _now_utc()},
    )

    home_team_id = _get_or_create(
        session,
        table="teams",
        where_sql="league_id = :league_id AND name = :name",
        where_params={"league_id": league_id, "name": home_team},
        insert_sql="""
            INSERT INTO teams (id, league_id, external_id, abbr, name, market, created_at)
            VALUES (:id, :league_id, :external_id, :abbr, :name, :market, :created_at)
        """,
        insert_params={
            "league_id": league_id,
            "external_id": None,
            "abbr": _abbr_for_team(home_team),
            "name": home_team,
            "market": None,
            "created_at": _now_utc(),
        },
    )

    away_team_id = _get_or_create(
        session,
        table="teams",
        where_sql="league_id = :league_id AND name = :name",
        where_params={"league_id": league_id, "name": away_team},
        insert_sql="""
            INSERT INTO teams (id, league_id, external_id, abbr, name, market, created_at)
            VALUES (:id, :league_id, :external_id, :abbr, :name, :market, :created_at)
        """,
        insert_params={
            "league_id": league_id,
            "external_id": None,
            "abbr": _abbr_for_team(away_team),
            "name": away_team,
            "market": None,
            "created_at": _now_utc(),
        },
    )

    game_id = _get_or_create(
        session,
        table="games",
        where_sql=(
            "season_id = :season_id AND (external_id = :external_id "
            "OR (game_date = :game_date AND home_team_id = :home_team_id AND away_team_id = :away_team_id))"
        ),
        where_params={
            "season_id": season_id,
            "external_id": event_id,
            "game_date": game_dt.date(),
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
        },
        insert_sql="""
            INSERT INTO games (
              id, season_id, external_id, game_date, start_time, status, home_team_id, away_team_id, created_at
            ) VALUES (
              :id, :season_id, :external_id, :game_date, :start_time, :status, :home_team_id, :away_team_id, :created_at
            )
        """,
        insert_params={
            "season_id": season_id,
            "external_id": event_id,
            "game_date": game_dt.date(),
            "start_time": game_dt,
            "status": "scheduled",
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "created_at": _now_utc(),
        },
    )
    return game_id, league_id, home_team_id, away_team_id, sport_id


def _get_or_create_sportsbook(session: Any, code: str) -> str:
    display_name = code.replace("_", " ").title()
    return _get_or_create(
        session,
        table="sportsbooks",
        where_sql="code = :code",
        where_params={"code": code},
        insert_sql="""
            INSERT INTO sportsbooks (id, code, name, created_at)
            VALUES (:id, :code, :name, :created_at)
        """,
        insert_params={"code": code, "name": display_name, "created_at": _now_utc()},
    )


def _get_or_create_market(session: Any, market_key: str) -> Optional[str]:
    market_code = MARKET_MAP.get(market_key)
    if not market_code:
        return None
    return _get_or_create(
        session,
        table="markets",
        where_sql="code = :code",
        where_params={"code": market_code},
        insert_sql="""
            INSERT INTO markets (id, code, created_at)
            VALUES (:id, :code, :created_at)
        """,
        insert_params={"code": market_code, "created_at": _now_utc()},
    )


def _default_projection_seed(game_id: str, model_version: str, simulation_count: int) -> int:
    text_seed = f"{game_id}:{model_version}:{simulation_count}".encode("utf-8")
    digest = hashlib.sha256(text_seed).hexdigest()
    return int(digest[:12], 16) % (2**31 - 1)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _run_simulation_by_model(
    inputs: MlbGameInputs,
    *,
    simulations: int,
    seed: int,
    model_version: str,
) -> Dict[str, Any]:
    if model_version.startswith("mlb-v2-pitch-sim"):
        if not _env_bool("MLB_ENABLE_PITCH_SIM", False):
            raise RuntimeError(
                "mlb-v2-pitch-sim is disabled; set MLB_ENABLE_PITCH_SIM=true to enable"
            )
        return simulate_mlb_game_pitch_by_pitch(
            inputs,
            simulations=simulations,
            seed=seed,
            model_version=model_version,
        )
    return simulate_mlb_game(
        inputs,
        simulations=simulations,
        seed=seed,
        model_version=model_version,
    )


def _info_freshness_score(*, updated_at: Optional[datetime], lineup_confirmed: bool) -> float:
    if updated_at is None:
        return 0.45
    age_hours = max(0.0, (_now_utc() - updated_at).total_seconds() / 3600.0)
    half_life_hours = float(os.getenv("MLB_INFO_FRESHNESS_HALFLIFE_HOURS", "18"))
    half_life_hours = max(1.0, half_life_hours)
    score = math.pow(0.5, age_hours / half_life_hours)
    if lineup_confirmed:
        score = min(1.0, score + 0.08)
    return max(0.35, min(1.0, score))


def _hours_to_game(start_time: Optional[datetime]) -> float:
    if start_time is None:
        return 999.0
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    return (start_time - _now_utc()).total_seconds() / 3600.0


def _lineup_nowcast_confidence(
    *,
    hours_to_first_pitch: float,
    lineup_confirmed: bool,
    probable_pitcher_home: Optional[str],
    probable_pitcher_away: Optional[str],
    freshness_score: float,
) -> Dict[str, float]:
    # Closer to first pitch => higher confidence, with explicit boost for confirmed lineups.
    if lineup_confirmed:
        base = 0.98
    else:
        if hours_to_first_pitch <= 1:
            base = 0.90
        elif hours_to_first_pitch <= 3:
            base = 0.85
        elif hours_to_first_pitch <= 6:
            base = 0.79
        elif hours_to_first_pitch <= 12:
            base = 0.73
        else:
            base = 0.66
    if probable_pitcher_home:
        base += 0.015
    if probable_pitcher_away:
        base += 0.015
    base = max(0.45, min(1.0, base))
    score = max(0.35, min(1.0, base * max(0.45, min(1.0, freshness_score))))
    return {"home": score, "away": score}


def _insert_mlb_projection_and_audit(
    session: Any,
    projection: Dict[str, Any],
    *,
    seed: int,
) -> None:
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
              CAST(:inputs AS jsonb), CAST(:run_rates AS jsonb), CAST(:diagnostics AS jsonb), :created_at
            )
            """
        ),
        {
            "game_id": projection["game_id"],
            "model_version": projection["model_version"],
            "simulation_count": projection["simulation_count"],
            "random_seed": seed,
            "inputs": __import__("json").dumps(projection.get("inputs") or {}),
            "run_rates": __import__("json").dumps(projection.get("run_rates") or {}),
            "diagnostics": __import__("json").dumps(diagnostics),
            "created_at": _now_utc(),
        },
    )


def _to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _fetch_calibration_points(
    session: Any,
    *,
    model_version: str,
    lookback_days: int,
) -> List[Dict[str, Any]]:
    rows = session.execute(
        text(
            """
            WITH latest_proj AS (
              SELECT DISTINCT ON (mp.game_id)
                mp.game_id,
                mp.fg_home_win_prob,
                mp.fg_total_mean,
                mp.created_at AS projection_created_at,
                g.game_date
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
              lp.projection_created_at,
              lp.game_date,
              mo.home_team_won,
              mo.final_total_runs,
              mo.completed_at AS outcome_completed_at
            FROM latest_proj lp
            JOIN mlb_market_outcomes mo ON mo.game_id = lp.game_id
            """
        ),
        {"model_version": model_version, "lookback_days": lookback_days},
    ).fetchall()
    return [dict(r._mapping) for r in rows]


def _compute_calibration_summary(points: List[Dict[str, Any]]) -> Dict[str, Optional[float]]:
    if not points:
        return {
            "sample_size": 0.0,
            "brier_ml": None,
            "mae_total_runs": None,
            "calendar_days_covered": 0.0,
            "last_game_date": None,
        }
    probs = [float(x["fg_home_win_prob"]) for x in points]
    actual = [1.0 if x["home_team_won"] else 0.0 for x in points]
    totals_pred = [float(x["fg_total_mean"]) for x in points]
    totals_actual = [float(x["final_total_runs"]) for x in points]
    brier = sum((p - a) ** 2 for p, a in zip(probs, actual)) / len(points)
    mae_total = sum(abs(p - a) for p, a in zip(totals_pred, totals_actual)) / len(points)
    game_dates = sorted(
        {
            str(x["game_date"])
            for x in points
            if x.get("game_date") is not None
        }
    )
    return {
        "sample_size": float(len(points)),
        "brier_ml": round(brier, 6),
        "mae_total_runs": round(mae_total, 4),
        "calendar_days_covered": float(len(game_dates)),
        "last_game_date": (game_dates[-1] if game_dates else None),
    }


def _compute_reliability_drift(points: List[Dict[str, Any]], bins: int = 10) -> Dict[str, Optional[float]]:
    if not points:
        return {
            "ece": None,
            "max_bin_error": None,
            "bin_count": 0.0,
        }
    bucket_count = max(2, min(20, int(bins)))
    buckets: List[List[Dict[str, Any]]] = [[] for _ in range(bucket_count)]
    for point in points:
        prob = max(0.0, min(1.0, float(point["fg_home_win_prob"])))
        idx = min(bucket_count - 1, int(prob * bucket_count))
        buckets[idx].append(point)
    ece = 0.0
    max_err = 0.0
    total_n = float(len(points))
    used_bins = 0
    for bucket in buckets:
        if not bucket:
            continue
        used_bins += 1
        avg_prob = sum(float(x["fg_home_win_prob"]) for x in bucket) / len(bucket)
        avg_actual = sum(1.0 if x["home_team_won"] else 0.0 for x in bucket) / len(bucket)
        err = abs(avg_prob - avg_actual)
        ece += (len(bucket) / total_n) * err
        max_err = max(max_err, err)
    return {
        "ece": round(ece, 6),
        "max_bin_error": round(max_err, 6),
        "bin_count": float(used_bins),
    }


def _build_prob_calibrator(
    training_points: List[Dict[str, Any]],
    *,
    bins: int = 12,
    prior_strength: float = 8.0,
) -> Dict[str, Any]:
    bucket_count = max(4, min(20, int(bins)))
    buckets: List[List[Dict[str, Any]]] = [[] for _ in range(bucket_count)]
    for point in training_points:
        prob = max(0.0, min(1.0, float(point["fg_home_win_prob"])))
        idx = min(bucket_count - 1, int(prob * bucket_count))
        buckets[idx].append(point)
    mapping: List[float] = []
    prior = 0.5
    for bucket in buckets:
        if not bucket:
            mapping.append(prior)
            continue
        wins = sum(1.0 if x["home_team_won"] else 0.0 for x in bucket)
        calibrated = (wins + prior_strength * prior) / (len(bucket) + prior_strength)
        mapping.append(max(0.01, min(0.99, calibrated)))
    return {
        "bins": bucket_count,
        "mapping": mapping,
        "training_sample_size": len(training_points),
    }


def _apply_prob_calibrator(prob: float, calibrator: Dict[str, Any]) -> float:
    p = max(0.0, min(1.0, float(prob)))
    bins = int(calibrator.get("bins") or 1)
    mapping = calibrator.get("mapping") or []
    if bins <= 0 or not isinstance(mapping, list) or not mapping:
        return p
    idx = min(bins - 1, int(p * bins))
    try:
        out = float(mapping[idx])
    except (TypeError, ValueError, IndexError):
        return p
    return max(0.01, min(0.99, out))


def _build_total_calibrator(
    training_points: List[Dict[str, Any]],
) -> Dict[str, float]:
    totals = [
        (
            _to_float_like(point.get("fg_total_mean")),
            _to_float_like(point.get("final_total_runs")),
        )
        for point in training_points
    ]
    valid = [(float(pred), float(actual)) for pred, actual in totals if pred is not None and actual is not None]
    if len(valid) < 20:
        return {"slope": 1.0, "intercept": 0.0}

    x_vals = [pred for pred, _actual in valid]
    y_vals = [actual for _pred, actual in valid]
    x_mean = sum(x_vals) / len(valid)
    y_mean = sum(y_vals) / len(valid)
    var_x = sum((x - x_mean) ** 2 for x in x_vals)
    cov_xy = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, y_vals))
    slope = cov_xy / var_x if var_x > 1e-9 else 1.0
    slope = max(0.8, min(1.2, slope))
    intercept = y_mean - (slope * x_mean)
    intercept = max(-8.0, min(8.0, intercept))
    return {"slope": float(slope), "intercept": float(intercept)}


def _apply_total_calibrator(total: float, calibrator: Dict[str, float]) -> float:
    slope = float(calibrator.get("slope") or 1.0)
    intercept = float(calibrator.get("intercept") or 0.0)
    adjusted = (slope * float(total)) + intercept
    return max(24.0, min(66.0, adjusted))


def _coerce_datetime_utc(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    dt: Optional[datetime]
    if isinstance(value, datetime):
        dt = value
    else:
        dt = _parse_iso_datetime(str(value))
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _projection_is_pre_outcome(point: Dict[str, Any]) -> bool:
    proj_dt = _coerce_datetime_utc(point.get("projection_created_at"))
    done_dt = _coerce_datetime_utc(point.get("outcome_completed_at"))
    if proj_dt is None or done_dt is None:
        return False
    return proj_dt < done_dt


def _count_leakage_violations(points: List[Dict[str, Any]]) -> int:

    violations = 0
    for point in points:
        try:
            # Leakage check is strict: projections must be created before outcomes are final.
            if not _projection_is_pre_outcome(point):
                violations += 1
        except Exception:
            continue
    return violations


def _is_nfl_backtest_point_eligible(point: Dict[str, Any]) -> bool:
    return _projection_is_pre_outcome(point)


def _walkforward_backtest(
    *,
    points: List[Dict[str, Any]],
    training_days: int,
    step_days: int,
    apply_calibration: bool,
) -> Dict[str, Any]:
    dated = [x for x in points if x.get("game_date") is not None]
    dated.sort(key=lambda x: (str(x.get("game_date")), str(x.get("game_id") or "")))
    if not dated:
        return {
            "folds": [],
            "fold_count": 0,
            "sample_size": 0,
            "base_brier_ml": None,
            "calibrated_brier_ml": None,
            "base_mae_total_runs": None,
            "calibrated_mae_total_runs": None,
            "brier_improvement": None,
            "mae_improvement": None,
        }

    unique_days = sorted({str(x["game_date"])[:10] for x in dated})
    min_train = max(7, int(training_days))
    step = max(1, int(step_days))
    folds: List[Dict[str, Any]] = []
    used_points = 0
    for idx in range(min_train, len(unique_days), step):
        train_days = set(unique_days[max(0, idx - min_train):idx])
        test_days = set(unique_days[idx:idx + step])
        train_points = [x for x in dated if str(x["game_date"])[:10] in train_days]
        test_points = [x for x in dated if str(x["game_date"])[:10] in test_days]
        if len(train_points) < 20 or len(test_points) < 5:
            continue
        calibrator = _build_prob_calibrator(train_points, bins=12)
        totals_calibrator = _build_total_calibrator(train_points)
        base_probs = [float(x["fg_home_win_prob"]) for x in test_points]
        cal_probs = [
            _apply_prob_calibrator(float(x["fg_home_win_prob"]), calibrator)
            if apply_calibration
            else float(x["fg_home_win_prob"])
            for x in test_points
        ]
        actual = [1.0 if x["home_team_won"] else 0.0 for x in test_points]
        totals_pred = [float(x["fg_total_mean"]) for x in test_points]
        totals_pred_calibrated = [
            _apply_total_calibrator(float(x["fg_total_mean"]), totals_calibrator)
            if apply_calibration
            else float(x["fg_total_mean"])
            for x in test_points
        ]
        totals_actual = [float(x["final_total_runs"]) for x in test_points]
        base_brier = sum((p - a) ** 2 for p, a in zip(base_probs, actual)) / len(test_points)
        cal_brier = sum((p - a) ** 2 for p, a in zip(cal_probs, actual)) / len(test_points)
        mae = sum(abs(p - a) for p, a in zip(totals_pred, totals_actual)) / len(test_points)
        cal_mae = sum(abs(p - a) for p, a in zip(totals_pred_calibrated, totals_actual)) / len(test_points)
        folds.append(
            {
                "train_start": sorted(train_days)[0],
                "train_end": sorted(train_days)[-1],
                "test_start": sorted(test_days)[0],
                "test_end": sorted(test_days)[-1],
                "train_size": len(train_points),
                "test_size": len(test_points),
                "base_brier_ml": round(base_brier, 6),
                "calibrated_brier_ml": round(cal_brier, 6),
                "brier_improvement": round(base_brier - cal_brier, 6),
                "base_mae_total_runs": round(mae, 4),
                "calibrated_mae_total_runs": round(cal_mae, 4),
                "mae_improvement": round(mae - cal_mae, 4),
                "total_calibration_slope": round(float(totals_calibrator["slope"]), 6),
                "total_calibration_intercept": round(float(totals_calibrator["intercept"]), 6),
            }
        )
        used_points += len(test_points)

    if not folds:
        return {
            "folds": [],
            "fold_count": 0,
            "sample_size": 0,
            "base_brier_ml": None,
            "calibrated_brier_ml": None,
            "base_mae_total_runs": None,
            "calibrated_mae_total_runs": None,
            "brier_improvement": None,
            "mae_improvement": None,
        }
    base_brier_avg = sum(float(f["base_brier_ml"]) for f in folds) / len(folds)
    cal_brier_avg = sum(float(f["calibrated_brier_ml"]) for f in folds) / len(folds)
    base_mae_avg = sum(float(f["base_mae_total_runs"]) for f in folds) / len(folds)
    cal_mae_avg = sum(float(f["calibrated_mae_total_runs"]) for f in folds) / len(folds)
    return {
        "folds": folds,
        "fold_count": len(folds),
        "sample_size": used_points,
        "base_brier_ml": round(base_brier_avg, 6),
        "calibrated_brier_ml": round(cal_brier_avg, 6),
        "base_mae_total_runs": round(base_mae_avg, 4),
        "calibrated_mae_total_runs": round(cal_mae_avg, 4),
        "brier_improvement": round(base_brier_avg - cal_brier_avg, 6),
        "mae_improvement": round(base_mae_avg - cal_mae_avg, 4),
    }


def _chunk_points(points: List[Dict[str, Any]], bucket_count: int) -> List[List[Dict[str, Any]]]:
    if not points:
        return []
    resolved_bucket_count = max(1, min(int(bucket_count), len(points)))
    base_size = len(points) // resolved_bucket_count
    extra = len(points) % resolved_bucket_count
    out: List[List[Dict[str, Any]]] = []
    index = 0
    for bucket_index in range(resolved_bucket_count):
        bucket_size = base_size + (1 if bucket_index < extra else 0)
        if bucket_size <= 0:
            continue
        out.append(points[index:index + bucket_size])
        index += bucket_size
    return out


def _aligned_holdout_points(
    *,
    base_points: List[Dict[str, Any]],
    challenger_points: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    base_by_game = {
        str(point["game_id"]): point
        for point in base_points
        if point.get("game_id") is not None
    }
    challenger_by_game = {
        str(point["game_id"]): point
        for point in challenger_points
        if point.get("game_id") is not None
    }
    aligned: List[Dict[str, Any]] = []
    for game_id in sorted(set(base_by_game) & set(challenger_by_game)):
        base_point = base_by_game[game_id]
        challenger_point = challenger_by_game[game_id]
        home_team_won = base_point.get("home_team_won")
        if home_team_won is None:
            home_team_won = challenger_point.get("home_team_won")
        final_total_runs = base_point.get("final_total_runs")
        if final_total_runs is None:
            final_total_runs = challenger_point.get("final_total_runs")
        if home_team_won is None or final_total_runs is None:
            continue
        game_date = base_point.get("game_date") or challenger_point.get("game_date")
        aligned.append(
            {
                "game_id": game_id,
                "game_date": game_date,
                "home_team_won": home_team_won,
                "final_total_runs": final_total_runs,
                "base_fg_home_win_prob": base_point.get("fg_home_win_prob"),
                "base_fg_total_mean": base_point.get("fg_total_mean"),
                "challenger_fg_home_win_prob": challenger_point.get("fg_home_win_prob"),
                "challenger_fg_total_mean": challenger_point.get("fg_total_mean"),
            }
        )
    aligned.sort(key=lambda point: (str(point.get("game_date") or ""), str(point["game_id"])))
    return aligned


def _compute_holdout_profile(
    *,
    base_points: List[Dict[str, Any]],
    challenger_points: List[Dict[str, Any]],
    bucket_count: int,
) -> Dict[str, Any]:
    aligned = _aligned_holdout_points(
        base_points=base_points,
        challenger_points=challenger_points,
    )
    if not aligned:
        return {
            "common_sample_size": 0,
            "calendar_days_covered": 0,
            "last_game_date": None,
            "bucket_count": 0,
            "bucket_size_min": 0,
            "bucket_size_max": 0,
            "brier_bucket_wins": 0,
            "mae_bucket_wins": 0,
            "dual_bucket_wins": 0,
            "overall_brier_improvement": None,
            "overall_mae_improvement": None,
            "worst_brier_improvement": None,
            "worst_mae_improvement": None,
            "buckets": [],
        }

    base_common_points = [
        {
            "game_id": point["game_id"],
            "game_date": point["game_date"],
            "fg_home_win_prob": point["base_fg_home_win_prob"],
            "fg_total_mean": point["base_fg_total_mean"],
            "home_team_won": point["home_team_won"],
            "final_total_runs": point["final_total_runs"],
        }
        for point in aligned
    ]
    challenger_common_points = [
        {
            "game_id": point["game_id"],
            "game_date": point["game_date"],
            "fg_home_win_prob": point["challenger_fg_home_win_prob"],
            "fg_total_mean": point["challenger_fg_total_mean"],
            "home_team_won": point["home_team_won"],
            "final_total_runs": point["final_total_runs"],
        }
        for point in aligned
    ]
    base_summary = _compute_calibration_summary(base_common_points)
    challenger_summary = _compute_calibration_summary(challenger_common_points)

    buckets: List[Dict[str, Any]] = []
    brier_bucket_wins = 0
    mae_bucket_wins = 0
    dual_bucket_wins = 0
    worst_brier_improvement: Optional[float] = None
    worst_mae_improvement: Optional[float] = None
    bucket_sizes: List[int] = []

    for index, bucket in enumerate(_chunk_points(aligned, bucket_count), start=1):
        base_bucket_points = [
            {
                "game_id": point["game_id"],
                "game_date": point["game_date"],
                "fg_home_win_prob": point["base_fg_home_win_prob"],
                "fg_total_mean": point["base_fg_total_mean"],
                "home_team_won": point["home_team_won"],
                "final_total_runs": point["final_total_runs"],
            }
            for point in bucket
        ]
        challenger_bucket_points = [
            {
                "game_id": point["game_id"],
                "game_date": point["game_date"],
                "fg_home_win_prob": point["challenger_fg_home_win_prob"],
                "fg_total_mean": point["challenger_fg_total_mean"],
                "home_team_won": point["home_team_won"],
                "final_total_runs": point["final_total_runs"],
            }
            for point in bucket
        ]
        base_bucket_summary = _compute_calibration_summary(base_bucket_points)
        challenger_bucket_summary = _compute_calibration_summary(challenger_bucket_points)
        brier_improvement = (
            (_safe_float(base_bucket_summary.get("brier_ml")) or 0.0)
            - (_safe_float(challenger_bucket_summary.get("brier_ml")) or 0.0)
        )
        mae_improvement = (
            (_safe_float(base_bucket_summary.get("mae_total_runs")) or 0.0)
            - (_safe_float(challenger_bucket_summary.get("mae_total_runs")) or 0.0)
        )
        if brier_improvement > 0:
            brier_bucket_wins += 1
        if mae_improvement > 0:
            mae_bucket_wins += 1
        if brier_improvement > 0 and mae_improvement > 0:
            dual_bucket_wins += 1
        worst_brier_improvement = (
            brier_improvement
            if worst_brier_improvement is None
            else min(worst_brier_improvement, brier_improvement)
        )
        worst_mae_improvement = (
            mae_improvement
            if worst_mae_improvement is None
            else min(worst_mae_improvement, mae_improvement)
        )
        bucket_sizes.append(len(bucket))
        bucket_dates = [str(point.get("game_date") or "")[:10] for point in bucket if point.get("game_date") is not None]
        buckets.append(
            {
                "bucket": index,
                "sample_size": len(bucket),
                "start_date": bucket_dates[0] if bucket_dates else None,
                "end_date": bucket_dates[-1] if bucket_dates else None,
                "base_brier_ml": base_bucket_summary.get("brier_ml"),
                "challenger_brier_ml": challenger_bucket_summary.get("brier_ml"),
                "base_mae_total_runs": base_bucket_summary.get("mae_total_runs"),
                "challenger_mae_total_runs": challenger_bucket_summary.get("mae_total_runs"),
                "brier_improvement": round(brier_improvement, 6),
                "mae_improvement": round(mae_improvement, 4),
            }
        )

    return {
        "common_sample_size": len(aligned),
        "calendar_days_covered": int(_safe_float(base_summary.get("calendar_days_covered")) or 0),
        "last_game_date": base_summary.get("last_game_date"),
        "bucket_count": len(buckets),
        "bucket_size_min": min(bucket_sizes) if bucket_sizes else 0,
        "bucket_size_max": max(bucket_sizes) if bucket_sizes else 0,
        "brier_bucket_wins": brier_bucket_wins,
        "mae_bucket_wins": mae_bucket_wins,
        "dual_bucket_wins": dual_bucket_wins,
        "overall_brier_improvement": round(
            (_safe_float(base_summary.get("brier_ml")) or 0.0)
            - (_safe_float(challenger_summary.get("brier_ml")) or 0.0),
            6,
        ),
        "overall_mae_improvement": round(
            (_safe_float(base_summary.get("mae_total_runs")) or 0.0)
            - (_safe_float(challenger_summary.get("mae_total_runs")) or 0.0),
            4,
        ),
        "worst_brier_improvement": None if worst_brier_improvement is None else round(worst_brier_improvement, 6),
        "worst_mae_improvement": None if worst_mae_improvement is None else round(worst_mae_improvement, 4),
        "buckets": buckets,
    }


def _american_implied_prob(price: Optional[int]) -> Optional[float]:
    if price is None:
        return None
    if price > 0:
        return 100.0 / (price + 100.0)
    return abs(price) / (abs(price) + 100.0)


def _compute_clv_summary(
    session: Any,
    *,
    model_version: str,
    lookback_days: int,
) -> Dict[str, Optional[float]]:
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
        {"model_version": model_version, "lookback_days": lookback_days},
    ).fetchall()

    ml_vals: List[float] = []
    total_vals: List[float] = []
    for r in rows:
        m = dict(r._mapping)
        open_home = int(round(m["open_home_ml"])) if m["open_home_ml"] is not None else None
        open_away = int(round(m["open_away_ml"])) if m["open_away_ml"] is not None else None
        close_home = int(round(m["close_home_ml"])) if m["close_home_ml"] is not None else None
        close_away = int(round(m["close_away_ml"])) if m["close_away_ml"] is not None else None
        open_total = _to_float(m["open_total"])
        close_total = _to_float(m["close_total"])
        model_home_prob = _to_float(m["fg_home_win_prob"])
        fair_total = _to_float(m["fair_fg_total"])

        if model_home_prob is not None and open_home is not None and open_away is not None:
            open_home_prob = _american_implied_prob(open_home)
            if open_home_prob is not None and close_home is not None and close_away is not None:
                if model_home_prob > open_home_prob:
                    ml_vals.append((_american_implied_prob(close_home) or 0.0) - (_american_implied_prob(open_home) or 0.0))
                else:
                    ml_vals.append((_american_implied_prob(close_away) or 0.0) - (_american_implied_prob(open_away) or 0.0))

        if fair_total is not None and open_total is not None and close_total is not None:
            if fair_total > open_total:
                total_vals.append(close_total - open_total)
            else:
                total_vals.append(open_total - close_total)

    return {
        "sample_size": float(len(rows)),
        "avg_ml_clv": round(sum(ml_vals) / len(ml_vals), 5) if ml_vals else None,
        "avg_total_clv": round(sum(total_vals) / len(total_vals), 5) if total_vals else None,
    }


def _payload_checksum(payload: Dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _upsert_mlb_raw_data_object(
    session: Any,
    *,
    source: str,
    object_type: str,
    object_key: str,
    as_of_date: date,
    payload: Dict[str, Any],
    fetched_at: Optional[datetime] = None,
) -> None:
    payload_json = json.dumps(payload)
    checksum = _payload_checksum(payload)
    session.execute(
        text(
            """
            INSERT INTO mlb_raw_data_objects (
              source, object_type, object_key, as_of_date, payload, checksum, fetched_at, created_at, updated_at
            ) VALUES (
              :source, :object_type, :object_key, :as_of_date, CAST(:payload AS jsonb), :checksum, :fetched_at, :created_at, :updated_at
            )
            ON CONFLICT (source, object_type, object_key, as_of_date) DO UPDATE SET
              payload = EXCLUDED.payload,
              checksum = EXCLUDED.checksum,
              fetched_at = EXCLUDED.fetched_at,
              updated_at = EXCLUDED.updated_at
            """
        ),
        {
            "source": source,
            "object_type": object_type,
            "object_key": object_key,
            "as_of_date": as_of_date,
            "payload": payload_json,
            "checksum": checksum,
            "fetched_at": fetched_at or _now_utc(),
            "created_at": _now_utc(),
            "updated_at": _now_utc(),
        },
    )


def _persist_snapshot(
    session: Any,
    *,
    run_date: date,
    model_version: str,
    pipeline_stage: str,
    payload: Dict[str, Any],
) -> None:
    session.execute(
        text(
            """
            INSERT INTO mlb_model_run_snapshots (
              run_date, model_version, pipeline_stage, payload, created_at
            ) VALUES (
              :run_date, :model_version, :pipeline_stage, CAST(:payload AS jsonb), :created_at
            )
            """
        ),
        {
            "run_date": run_date,
            "model_version": model_version,
            "pipeline_stage": pipeline_stage,
            "payload": __import__("json").dumps(payload),
            "created_at": _now_utc(),
        },
    )


def _persist_holdout_profile(
    session: Any,
    *,
    run_date: date,
    base_model_version: str,
    challenger_model_version: str,
    lookback_days: int,
    holdout_profile: Dict[str, Any],
) -> None:
    session.execute(
        text(
            """
            INSERT INTO mlb_model_holdout_profiles (
              run_date,
              base_model_version,
              challenger_model_version,
              lookback_days,
              common_sample_size,
              bucket_count,
              payload,
              created_at
            ) VALUES (
              :run_date,
              :base_model_version,
              :challenger_model_version,
              :lookback_days,
              :common_sample_size,
              :bucket_count,
              CAST(:payload AS jsonb),
              :created_at
            )
            """
        ),
        {
            "run_date": run_date,
            "base_model_version": base_model_version,
            "challenger_model_version": challenger_model_version,
            "lookback_days": lookback_days,
            "common_sample_size": int(holdout_profile.get("common_sample_size") or 0),
            "bucket_count": int(holdout_profile.get("bucket_count") or 0),
            "payload": json.dumps(holdout_profile),
            "created_at": _now_utc(),
        },
    )


def _persist_alert_event(
    session: Any,
    *,
    alert_type: str,
    severity: str,
    payload: Dict[str, Any],
) -> None:
    session.execute(
        text(
            """
            INSERT INTO mlb_alert_events (
              alert_type, severity, payload, created_at
            ) VALUES (
              :alert_type, :severity, CAST(:payload AS jsonb), :created_at
            )
            """
        ),
        {
            "alert_type": alert_type,
            "severity": severity,
            "payload": __import__("json").dumps(payload),
            "created_at": _now_utc(),
        },
    )


def _send_alert_webhook(
    *,
    alert_type: str,
    severity: str,
    payload: Dict[str, Any],
) -> bool:
    url = (os.getenv("MLB_ALERT_WEBHOOK_URL") or "").strip()
    if not url:
        return False
    body = {
        "alert_type": alert_type,
        "severity": severity,
        "payload": payload,
        "service": "model-service",
        "at": _now_utc().isoformat(),
    }
    try:
        r = requests.post(url, json=body, timeout=8)
        r.raise_for_status()
        return True
    except Exception:
        log.exception("Failed sending MLB alert webhook")
        return False


def _safe_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _safe_int(v: Any) -> Optional[int]:
    try:
        if v is None:
            return None
        return int(v)
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


def _decide_challenger_promotion(
    *,
    base_quality: Dict[str, Any],
    challenger_quality: Dict[str, Any],
    holdout_profile: Dict[str, Any],
) -> Dict[str, Any]:
    min_sample = int(os.getenv("MLB_PROMOTION_MIN_SAMPLE_SIZE", "120"))
    req_brier_improvement = float(os.getenv("MLB_PROMOTION_MIN_BRIER_IMPROVEMENT", "0.0020"))
    req_mae_improvement = float(os.getenv("MLB_PROMOTION_MIN_MAE_IMPROVEMENT", "0.08"))
    req_clv_improvement = float(os.getenv("MLB_PROMOTION_MIN_TOTAL_CLV_IMPROVEMENT", "0.0030"))
    min_calendar_days = int(os.getenv("MLB_PROMOTION_MIN_CALENDAR_DAYS", "14"))
    max_last_game_age_days = int(os.getenv("MLB_PROMOTION_MAX_LAST_GAME_AGE_DAYS", "3"))
    min_holdout_sample = int(os.getenv("MLB_PROMOTION_MIN_HOLDOUT_SAMPLE_SIZE", "90"))
    min_holdout_bucket_win_rate = float(os.getenv("MLB_PROMOTION_MIN_HOLDOUT_BUCKET_WIN_RATE", "0.67"))
    max_bucket_brier_regression = float(os.getenv("MLB_PROMOTION_MAX_BUCKET_BRIER_REGRESSION", "0.0015"))
    max_bucket_mae_regression = float(os.getenv("MLB_PROMOTION_MAX_BUCKET_MAE_REGRESSION", "0.08"))

    base_sample = int(_safe_float(base_quality.get("sample_size")) or 0)
    ch_sample = int(_safe_float(challenger_quality.get("sample_size")) or 0)

    base_brier = _safe_float(base_quality.get("brier_ml"))
    ch_brier = _safe_float(challenger_quality.get("brier_ml"))
    base_mae = _safe_float(base_quality.get("mae_total_runs"))
    ch_mae = _safe_float(challenger_quality.get("mae_total_runs"))
    base_clv = _safe_float(base_quality.get("avg_total_clv"))
    ch_clv = _safe_float(challenger_quality.get("avg_total_clv"))
    base_days = int(_safe_float(base_quality.get("calendar_days_covered")) or 0)
    ch_days = int(_safe_float(challenger_quality.get("calendar_days_covered")) or 0)
    base_last = _safe_date(base_quality.get("last_game_date"))
    ch_last = _safe_date(challenger_quality.get("last_game_date"))
    today = date.today()
    base_last_age = (today - base_last).days if base_last else None
    ch_last_age = (today - ch_last).days if ch_last else None

    brier_delta = (base_brier - ch_brier) if base_brier is not None and ch_brier is not None else None
    mae_delta = (base_mae - ch_mae) if base_mae is not None and ch_mae is not None else None
    clv_delta = (ch_clv - base_clv) if base_clv is not None and ch_clv is not None else None
    holdout_sample = int(_safe_float(holdout_profile.get("common_sample_size")) or 0)
    holdout_bucket_count = int(_safe_float(holdout_profile.get("bucket_count")) or 0)
    dual_bucket_wins = int(_safe_float(holdout_profile.get("dual_bucket_wins")) or 0)
    worst_brier_improvement = _safe_float(holdout_profile.get("worst_brier_improvement"))
    worst_mae_improvement = _safe_float(holdout_profile.get("worst_mae_improvement"))
    holdout_bucket_win_rate = (
        dual_bucket_wins / holdout_bucket_count if holdout_bucket_count > 0 else 0.0
    )

    checks = {
        "sample_size_ok": base_sample >= min_sample and ch_sample >= min_sample,
        "calendar_days_ok": base_days >= min_calendar_days and ch_days >= min_calendar_days,
        "freshness_ok": (
            base_last_age is not None
            and ch_last_age is not None
            and base_last_age <= max_last_game_age_days
            and ch_last_age <= max_last_game_age_days
        ),
        "brier_ok": brier_delta is not None and brier_delta >= req_brier_improvement,
        "mae_ok": mae_delta is not None and mae_delta >= req_mae_improvement,
        "clv_ok": clv_delta is not None and clv_delta >= req_clv_improvement,
        "holdout_sample_ok": holdout_sample >= min_holdout_sample,
        "holdout_consistency_ok": holdout_bucket_count > 0 and holdout_bucket_win_rate >= min_holdout_bucket_win_rate,
        "holdout_regression_ok": (
            worst_brier_improvement is not None
            and worst_mae_improvement is not None
            and worst_brier_improvement >= -max_bucket_brier_regression
            and worst_mae_improvement >= -max_bucket_mae_regression
        ),
    }
    promote = all(checks.values())

    reasons: List[str] = []
    if not checks["sample_size_ok"]:
        reasons.append("insufficient_sample_size")
    if not checks["calendar_days_ok"]:
        reasons.append("insufficient_calendar_days")
    if not checks["freshness_ok"]:
        reasons.append("stale_outcome_window")
    if not checks["brier_ok"]:
        reasons.append("brier_not_improved_enough")
    if not checks["mae_ok"]:
        reasons.append("mae_not_improved_enough")
    if not checks["clv_ok"]:
        reasons.append("clv_not_improved_enough")
    if not checks["holdout_sample_ok"]:
        reasons.append("insufficient_holdout_sample")
    if not checks["holdout_consistency_ok"]:
        reasons.append("holdout_bucket_consistency_failed")
    if not checks["holdout_regression_ok"]:
        reasons.append("holdout_bucket_regression_too_large")

    return {
        "promote": promote,
        "checks": checks,
        "thresholds": {
            "min_sample_size": min_sample,
            "min_calendar_days": min_calendar_days,
            "max_last_game_age_days": max_last_game_age_days,
            "min_brier_improvement": req_brier_improvement,
            "min_mae_improvement": req_mae_improvement,
            "min_total_clv_improvement": req_clv_improvement,
            "min_holdout_sample_size": min_holdout_sample,
            "min_holdout_bucket_win_rate": min_holdout_bucket_win_rate,
            "max_bucket_brier_regression": max_bucket_brier_regression,
            "max_bucket_mae_regression": max_bucket_mae_regression,
        },
        "deltas": {
            "brier_improvement": None if brier_delta is None else round(brier_delta, 6),
            "mae_improvement": None if mae_delta is None else round(mae_delta, 4),
            "total_clv_improvement": None if clv_delta is None else round(clv_delta, 5),
            "holdout_bucket_win_rate": round(holdout_bucket_win_rate, 4),
            "worst_brier_improvement": None if worst_brier_improvement is None else round(worst_brier_improvement, 6),
            "worst_mae_improvement": None if worst_mae_improvement is None else round(worst_mae_improvement, 4),
        },
        "holdout_profile": holdout_profile,
        "reasons": reasons,
    }


def _set_active_model(
    session: Any,
    *,
    model_version: str,
    reason: str,
) -> Dict[str, Any]:
    previous_row = session.execute(
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
    previous = str(previous_row[0]) if previous_row else None
    session.execute(
        text(
            """
            INSERT INTO mlb_model_runtime_state (
              state_key, active_model_version, previous_model_version, reason, updated_at
            ) VALUES (
              :state_key, :active_model_version, :previous_model_version, :reason, :updated_at
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
            "previous_model_version": previous,
            "reason": reason,
            "updated_at": _now_utc(),
        },
    )
    return {"active_model_version": model_version, "previous_model_version": previous}


@celery_app.task(name="src.tasks.pull_odds_snapshot")
def pull_odds_snapshot() -> Dict[str, int]:
    log.info("Running scheduled pull_odds_snapshot")
    data: List[Dict[str, Any]] = []
    for sport_key in SPORT_MAP.keys():
        try:
            payload = fetch_odds(
                endpoint=f"sports/{sport_key}/odds",
                params={
                    "regions": "us",
                    "markets": "h2h,spreads,totals",
                    "oddsFormat": "american",
                },
            )
        except Exception:
            log.exception("Failed pulling odds for sport", extra={"sport_key": sport_key})
            continue

        if not isinstance(payload, list):
            log.warning("Odds payload was not a list; skipping sport", extra={"sport_key": sport_key})
            continue

        for event in payload:
            if isinstance(event, dict) and not event.get("sport_key"):
                event["sport_key"] = sport_key
        data.extend(payload)

    if not data:
        log.warning("Odds payload was empty; skipping persistence.")
        return {"events_fetched": 0, "events_persisted": 0, "snapshots_inserted": 0}

    events_persisted = 0
    snapshots_inserted = 0
    session = SessionLocal()
    try:
        for event in data:
            event_id = (event or {}).get("id")
            home_team = (event or {}).get("home_team")
            away_team = (event or {}).get("away_team")
            game_dt = _parse_iso_datetime((event or {}).get("commence_time")) or _now_utc()
            sport_key = (event or {}).get("sport_key") or "unknown"

            if not event_id or not home_team or not away_team:
                continue

            game_id, _league_id, _home_id, _away_id, _sport_id = _ensure_hierarchy(
                session,
                sport_key=sport_key,
                game_dt=game_dt,
                home_team=home_team,
                away_team=away_team,
                event_id=event_id,
            )
            events_persisted += 1

            for book in (event.get("bookmakers") or []):
                book_key = (book or {}).get("key")
                if not book_key:
                    continue
                sportsbook_id = _get_or_create_sportsbook(session, book_key)
                captured_at = _parse_iso_datetime(book.get("last_update")) or _now_utc()

                for market in (book.get("markets") or []):
                    market_key = market.get("key")
                    if not market_key:
                        continue
                    market_id = _get_or_create_market(session, market_key)
                    if not market_id:
                        continue

                    values = _extract_snapshot_values(market_key, market, home_team, away_team)
                    if values is None:
                        continue

                    session.execute(
                        text(
                            """
                            INSERT INTO odds_snapshots (
                              id, game_id, sportsbook_id, market_id,
                              price_home, price_away, spread_home, spread_away,
                              total_points, over_price, under_price,
                              captured_at, source, created_at
                            ) VALUES (
                              :id, :game_id, :sportsbook_id, :market_id,
                              :price_home, :price_away, :spread_home, :spread_away,
                              :total_points, :over_price, :under_price,
                              :captured_at, :source, :created_at
                            )
                            """
                        ),
                        {
                            "id": str(uuid.uuid4()),
                            "game_id": game_id,
                            "sportsbook_id": sportsbook_id,
                            "market_id": market_id,
                            "price_home": values["price_home"],
                            "price_away": values["price_away"],
                            "spread_home": values["spread_home"],
                            "spread_away": values["spread_away"],
                            "total_points": values["total_points"],
                            "over_price": values["over_price"],
                            "under_price": values["under_price"],
                            "captured_at": captured_at,
                            "source": "the-odds-api",
                            "created_at": _now_utc(),
                        },
                    )
                    snapshots_inserted += 1

        session.commit()
    except Exception:
        session.rollback()
        log.exception("Failed to persist odds snapshots")
        raise
    finally:
        session.close()

    result = {
        "events_fetched": len(data),
        "events_persisted": events_persisted,
        "snapshots_inserted": snapshots_inserted,
    }
    log.info(
        "Pulled odds snapshot",
        extra=result,
    )
    return result


@celery_app.task(name="src.tasks.pull_nfl_context_snapshot")
def pull_nfl_context_snapshot(days_ahead: int = 14) -> Dict[str, int]:
    start = date.today()
    end = start + timedelta(days=max(0, days_ahead))
    schedule = fetch_nfl_schedule(start, end)
    session = SessionLocal()
    created_or_updated = 0
    games_seen = 0
    try:
        for g in schedule:
            event_id = g.get("external_game_id")
            if not event_id:
                continue
            game_dt = _parse_iso_datetime(g.get("game_time")) or _now_utc()
            game_id, _league_id, _home_id, _away_id, _sport_id = _ensure_hierarchy(
                session,
                sport_key="americanfootball_nfl",
                game_dt=game_dt,
                home_team=g["home_team"],
                away_team=g["away_team"],
                event_id=event_id,
            )
            games_seen += 1
            offense_home, defense_home = team_strength_from_record(g.get("home_record_summary"))
            offense_away, defense_away = team_strength_from_record(g.get("away_record_summary"))
            rest_days = rest_days_from_schedule(g.get("game_time"))
            session.execute(
                text(
                    """
                    INSERT INTO nfl_game_context (
                      game_id, source, offense_index_home, offense_index_away,
                      defense_index_home, defense_index_away, rest_days_home, rest_days_away,
                      context, created_at, updated_at
                    ) VALUES (
                      :game_id, :source, :offense_index_home, :offense_index_away,
                      :defense_index_home, :defense_index_away, :rest_days_home, :rest_days_away,
                      CAST(:context AS jsonb), :created_at, :updated_at
                    )
                    ON CONFLICT (game_id) DO UPDATE SET
                      offense_index_home = EXCLUDED.offense_index_home,
                      offense_index_away = EXCLUDED.offense_index_away,
                      defense_index_home = EXCLUDED.defense_index_home,
                      defense_index_away = EXCLUDED.defense_index_away,
                      rest_days_home = EXCLUDED.rest_days_home,
                      rest_days_away = EXCLUDED.rest_days_away,
                      context = EXCLUDED.context,
                      updated_at = EXCLUDED.updated_at
                    """
                ),
                {
                    "game_id": game_id,
                    "source": "espn-scoreboard",
                    "offense_index_home": offense_home,
                    "offense_index_away": offense_away,
                    "defense_index_home": defense_home,
                    "defense_index_away": defense_away,
                    "rest_days_home": rest_days,
                    "rest_days_away": rest_days,
                    "context": json.dumps(
                        {
                            "status": g.get("status"),
                            "home_abbr": g.get("home_abbr"),
                            "away_abbr": g.get("away_abbr"),
                            "home_record_summary": g.get("home_record_summary"),
                            "away_record_summary": g.get("away_record_summary"),
                        }
                    ),
                    "created_at": _now_utc(),
                    "updated_at": _now_utc(),
                },
            )
            created_or_updated += 1
        session.commit()
        return {
            "scheduled_games_fetched": len(schedule),
            "games_seen": games_seen,
            "context_rows_upserted": created_or_updated,
        }
    except Exception:
        session.rollback()
        log.exception("Failed to persist NFL context snapshot")
        raise
    finally:
        session.close()


@celery_app.task(name="src.tasks.run_nfl_market_simulations")
def run_nfl_market_simulations(
    game_date: Optional[str] = None,
    simulations: int = 4000,
    model_version: str = DEFAULT_NFL_MODEL_VERSION,
    include_completed_games: bool = False,
    projection_created_at_mode: str = "now",
    kickoff_buffer_minutes: int = 30,
) -> Dict[str, int]:
    target_date = date.fromisoformat(game_date) if game_date else date.today()
    session = SessionLocal()
    processed = 0
    inserted = 0
    try:
        totals_calibration = fetch_nfl_totals_calibration(
            session,
            model_version=model_version,
            lookback_days=int(float(os.getenv("NFL_TOTALS_CALIBRATION_LOOKBACK_DAYS", "240"))),
        )
        rows = session.execute(
            text(
                """
                SELECT
                  g.id AS game_id,
                  g.status AS game_status,
                  g.game_date AS game_date,
                  g.start_time AS start_time,
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
                  AND g.game_date = :game_date
                ORDER BY g.start_time
                """
            ),
            {"game_date": target_date},
        ).fetchall()
        for r in rows:
            m = dict(r._mapping)
            if (
                not bool(include_completed_games)
                and str(m.get("game_status") or "").lower() in {"final", "closed", "completed"}
            ):
                continue
            matchup_pack = fetch_latest_matchup_feature_pack(
                session,
                game_id=str(m["game_id"]),
                season_year=_to_int_like(m.get("season_year")),
                home_team=str(m["home_team"]),
                away_team=str(m["away_team"]),
            )
            injury_nowcast = fetch_nfl_injury_nowcast(
                session,
                season_year=_to_int_like(m.get("season_year")),
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
            seed = _default_projection_seed(inputs.game_id, model_version, simulations)
            projection = simulate_nfl_game(
                inputs,
                simulations=simulations,
                seed=seed,
                model_version=model_version,
                totals_calibration=totals_calibration,
            )
            projection_created_at = _resolve_nfl_projection_created_at(
                game_date=(m.get("game_date") if isinstance(m.get("game_date"), date) else target_date),
                start_time=m.get("start_time"),
                mode=projection_created_at_mode,
                kickoff_buffer_minutes=kickoff_buffer_minutes,
            )
            projection_for_storage = dict(projection)
            audit_block = projection_for_storage.get("audit")
            if not isinstance(audit_block, dict):
                audit_block = {}
            audit_block.update(
                {
                    "projection_created_at_mode": str(projection_created_at_mode),
                    "kickoff_buffer_minutes": int(max(0, int(kickoff_buffer_minutes))),
                    "projection_created_at": projection_created_at.isoformat(),
                    "include_completed_games": bool(include_completed_games),
                    "totals_calibration": totals_calibration,
                }
            )
            projection_for_storage["audit"] = audit_block
            markets = projection.get("markets") or {}
            session.execute(
                text(
                    """
                    INSERT INTO nfl_market_projections (
                      game_id, model_version, simulation_count, home_win_prob, away_win_prob,
                      total_mean, spread_home, fair_home_ml, fair_away_ml, projection, created_at
                    ) VALUES (
                      :game_id, :model_version, :simulation_count, :home_win_prob, :away_win_prob,
                      :total_mean, :spread_home, :fair_home_ml, :fair_away_ml, CAST(:projection AS jsonb), :created_at
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
                    "projection": json.dumps(projection_for_storage),
                    "created_at": projection_created_at,
                },
            )
            processed += 1
            inserted += 1
        session.commit()
        return {"games_processed": processed, "projections_inserted": inserted}
    except Exception:
        session.rollback()
        log.exception("Failed running NFL market simulations")
        raise
    finally:
        session.close()


@celery_app.task(name="src.tasks.backfill_nfl_historical_projections")
def backfill_nfl_historical_projections(
    *,
    start_date: str,
    end_date: str,
    simulations: int = 4000,
    model_version: str = DEFAULT_NFL_MODEL_VERSION,
    kickoff_buffer_minutes: int = 30,
) -> Dict[str, Any]:
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    if end < start:
        raise ValueError("end_date must be on or after start_date")

    processed_days = 0
    total_games_processed = 0
    total_projections_inserted = 0
    current = start
    while current <= end:
        result = run_nfl_market_simulations(
            game_date=current.isoformat(),
            simulations=int(simulations),
            model_version=model_version,
            include_completed_games=True,
            projection_created_at_mode="kickoff_minus_buffer",
            kickoff_buffer_minutes=int(kickoff_buffer_minutes),
        )
        processed_days += 1
        total_games_processed += int(result.get("games_processed") or 0)
        total_projections_inserted += int(result.get("projections_inserted") or 0)
        current += timedelta(days=1)

    return {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "simulations": int(simulations),
        "model_version": model_version,
        "kickoff_buffer_minutes": int(kickoff_buffer_minutes),
        "days_processed": processed_days,
        "games_processed": total_games_processed,
        "projections_inserted": total_projections_inserted,
        "projection_created_at_mode": "kickoff_minus_buffer",
        "include_completed_games": True,
    }


def _to_int_like(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _to_float_like(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_final_status(status: Any) -> bool:
    normalized = str(status or "").strip().lower()
    return normalized in {"final", "closed", "completed"}


def _resolve_nfl_projection_created_at(
    *,
    game_date: date,
    start_time: Optional[datetime],
    mode: str,
    kickoff_buffer_minutes: int,
) -> datetime:
    normalized_mode = str(mode or "now").strip().lower()
    if normalized_mode != "kickoff_minus_buffer":
        return _now_utc()

    kickoff_dt = _coerce_datetime_utc(start_time)
    if kickoff_dt is None:
        kickoff_dt = datetime.combine(game_date, time(hour=20, minute=0), tzinfo=timezone.utc)
    buffer_minutes = max(0, int(kickoff_buffer_minutes))
    return kickoff_dt - timedelta(minutes=buffer_minutes)


def _build_nfl_score_lookup_from_schedule(
    schedule: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    lookup: Dict[str, Dict[str, Any]] = {}
    for game in schedule:
        external_id = str(game.get("external_game_id") or "").strip()
        if not external_id or not _is_final_status(game.get("status")):
            continue
        home_score = _to_int_like(game.get("home_score"))
        away_score = _to_int_like(game.get("away_score"))
        if home_score is None or away_score is None:
            continue
        completed_at = _parse_iso_datetime(game.get("game_time")) or _now_utc()
        lookup[external_id] = {
            "home_score": home_score,
            "away_score": away_score,
            "completed_at": completed_at,
            "source": "espn-scoreboard",
        }
    return lookup


@celery_app.task(name="src.tasks.materialize_nfl_market_history")
def materialize_nfl_market_history(lookback_days: int = 45) -> Dict[str, int]:
    session = SessionLocal()
    inserted_or_updated = 0
    try:
        date_filter = ""
        params: Dict[str, Any] = {}
        if lookback_days > 0:
            date_filter = "AND os.captured_at >= NOW() - make_interval(days => :lookback_days)"
            params["lookback_days"] = int(lookback_days)

        result = session.execute(
            text(
                f"""
                INSERT INTO nfl_market_history_snapshots (
                  game_id, captured_at, sportsbook_code, market_code,
                  home_price, away_price, total_points, over_price, under_price,
                  source, created_at
                )
                SELECT
                  os.game_id,
                  os.captured_at,
                  sb.code AS sportsbook_code,
                  m.code AS market_code,
                  os.price_home,
                  os.price_away,
                  CASE
                    WHEN m.code = 'total' AND os.total_points IS NOT NULL
                    THEN ROUND((os.total_points::numeric * 2.0)) / 2.0
                    ELSE os.total_points
                  END AS total_points,
                  os.over_price,
                  os.under_price,
                  CASE
                    WHEN m.code = 'total' THEN CONCAT(COALESCE(os.source, 'odds_snapshots'), '\:normalized-total')
                    ELSE COALESCE(os.source, 'odds_snapshots')
                  END AS source,
                  NOW()
                FROM odds_snapshots os
                JOIN games g ON g.id = os.game_id
                JOIN seasons s ON s.id = g.season_id
                JOIN leagues l ON l.id = s.league_id
                JOIN markets m ON m.id = os.market_id
                JOIN sportsbooks sb ON sb.id = os.sportsbook_id
                WHERE l.code = 'nfl'
                  AND m.code IN ('moneyline', 'total')
                  AND (m.code <> 'total' OR os.total_points IS NOT NULL)
                  {date_filter}
                ON CONFLICT (game_id, sportsbook_code, market_code, captured_at) DO UPDATE SET
                  home_price = EXCLUDED.home_price,
                  away_price = EXCLUDED.away_price,
                  total_points = EXCLUDED.total_points,
                  over_price = EXCLUDED.over_price,
                  under_price = EXCLUDED.under_price,
                  source = EXCLUDED.source
                """
            ),
            params,
        )
        inserted_or_updated = int(result.rowcount or 0)
        session.commit()
        return {
            "lookback_days": int(lookback_days),
            "snapshots_upserted": inserted_or_updated,
        }
    except Exception:
        session.rollback()
        log.exception("Failed to materialize NFL market history")
        raise
    finally:
        session.close()


@celery_app.task(name="src.tasks.pull_nfl_outcomes")
def pull_nfl_outcomes(days_back: int = 60) -> Dict[str, int]:
    window_days = max(1, int(days_back))
    start = date.today() - timedelta(days=window_days)
    end = date.today()
    session = SessionLocal()
    upserted = 0
    games_seen = 0
    source_hits = {"nfl_dp_schedules": 0, "espn_scoreboard": 0}
    try:
        rows = session.execute(
            text(
                """
                SELECT
                  g.id AS game_id,
                  g.external_id,
                  g.status AS game_status,
                  g.game_date,
                  g.start_time,
                  ds.home_score,
                  ds.away_score,
                  ds.updated_at AS schedule_updated_at
                FROM games g
                JOIN seasons s ON s.id = g.season_id
                JOIN leagues l ON l.id = s.league_id
                LEFT JOIN nfl_dp_schedules ds ON ds.game_id = g.external_id
                WHERE l.code = 'nfl'
                  AND g.game_date BETWEEN :start_date AND :end_date
                ORDER BY g.game_date DESC
                """
            ),
            {"start_date": start, "end_date": end},
        ).fetchall()

        unresolved_final = [
            r
            for r in rows
            if _is_final_status(r.game_status) and (_to_int_like(r.home_score) is None or _to_int_like(r.away_score) is None)
        ]
        espn_lookup: Dict[str, Dict[str, Any]] = {}
        if unresolved_final:
            espn_schedule = fetch_nfl_schedule(start, end)
            espn_lookup = _build_nfl_score_lookup_from_schedule(espn_schedule)

        for row in rows:
            games_seen += 1
            external_id = str(row.external_id or "").strip()
            status_final = _is_final_status(row.game_status)
            home_score = _to_int_like(row.home_score)
            away_score = _to_int_like(row.away_score)
            completed_at = row.schedule_updated_at or row.start_time or _now_utc()
            source = "nfl-dp-schedules"

            if home_score is None or away_score is None:
                espn = espn_lookup.get(external_id) if external_id else None
                if espn is not None:
                    home_score = _to_int_like(espn.get("home_score"))
                    away_score = _to_int_like(espn.get("away_score"))
                    completed_at = espn.get("completed_at") or completed_at
                    source = str(espn.get("source") or "espn-scoreboard")

            if home_score is None or away_score is None:
                continue
            if not status_final and source == "nfl-dp-schedules":
                # Avoid grading in-progress games unless source confirms final status.
                continue

            session.execute(
                text(
                    """
                    INSERT INTO nfl_market_outcomes (
                      game_id, actual_home_points, actual_away_points, final_total_points,
                      home_team_won, source, completed_at, created_at, updated_at
                    ) VALUES (
                      :game_id, :actual_home_points, :actual_away_points, :final_total_points,
                      :home_team_won, :source, :completed_at, :created_at, :updated_at
                    )
                    ON CONFLICT (game_id) DO UPDATE SET
                      actual_home_points = EXCLUDED.actual_home_points,
                      actual_away_points = EXCLUDED.actual_away_points,
                      final_total_points = EXCLUDED.final_total_points,
                      home_team_won = EXCLUDED.home_team_won,
                      source = EXCLUDED.source,
                      completed_at = EXCLUDED.completed_at,
                      updated_at = EXCLUDED.updated_at
                    """
                ),
                {
                    "game_id": str(row.game_id),
                    "actual_home_points": int(home_score),
                    "actual_away_points": int(away_score),
                    "final_total_points": int(home_score) + int(away_score),
                    "home_team_won": bool(int(home_score) > int(away_score)),
                    "source": source,
                    "completed_at": completed_at,
                    "created_at": _now_utc(),
                    "updated_at": _now_utc(),
                },
            )
            upserted += 1
            if source == "nfl-dp-schedules":
                source_hits["nfl_dp_schedules"] += 1
            else:
                source_hits["espn_scoreboard"] += 1

        session.commit()
        return {
            "days_back": window_days,
            "games_seen": games_seen,
            "outcomes_upserted": upserted,
            "source_hits": source_hits,
        }
    except Exception:
        session.rollback()
        log.exception("Failed to pull NFL outcomes")
        raise
    finally:
        session.close()


@celery_app.task(name="src.tasks.run_nfl_clv_attribution")
def run_nfl_clv_attribution(
    lookback_days: int = 45,
    model_version: str = DEFAULT_NFL_MODEL_VERSION,
) -> Dict[str, int]:
    session = SessionLocal()
    projections_seen = 0
    rows_upserted = 0
    try:
        projections = session.execute(
            text(
                """
                SELECT DISTINCT ON (mp.game_id)
                  mp.id,
                  mp.game_id,
                  mp.model_version,
                  mp.home_win_prob,
                  mp.fair_home_ml,
                  mp.fair_away_ml,
                  mp.total_mean
                FROM nfl_market_projections mp
                JOIN games g ON g.id = mp.game_id
                WHERE mp.model_version = :model_version
                  AND g.game_date >= CURRENT_DATE - make_interval(days => :lookback_days)
                ORDER BY mp.game_id, mp.created_at DESC
                """
            ),
            {"model_version": model_version, "lookback_days": int(lookback_days)},
        ).fetchall()

        for projection_row in projections:
            projections_seen += 1
            p = dict(projection_row._mapping)
            game_id = str(p["game_id"])

            market_points = session.execute(
                text(
                    """
                    WITH moneyline_open AS (
                      SELECT AVG(home_price)::numeric AS open_home_price,
                             AVG(away_price)::numeric AS open_away_price
                      FROM nfl_market_history_snapshots
                      WHERE game_id = :game_id
                        AND market_code = 'moneyline'
                        AND captured_at = (
                          SELECT MIN(captured_at)
                          FROM nfl_market_history_snapshots
                          WHERE game_id = :game_id
                            AND market_code = 'moneyline'
                        )
                    ),
                    moneyline_close AS (
                      SELECT AVG(home_price)::numeric AS close_home_price,
                             AVG(away_price)::numeric AS close_away_price
                      FROM nfl_market_history_snapshots
                      WHERE game_id = :game_id
                        AND market_code = 'moneyline'
                        AND captured_at = (
                          SELECT MAX(captured_at)
                          FROM nfl_market_history_snapshots
                          WHERE game_id = :game_id
                            AND market_code = 'moneyline'
                        )
                    ),
                    total_open AS (
                      SELECT
                        AVG(total_points)::numeric AS open_total,
                        MIN(source) AS open_total_source
                      FROM nfl_market_history_snapshots
                      WHERE game_id = :game_id
                        AND market_code = 'total'
                        AND captured_at = (
                          SELECT MIN(captured_at)
                          FROM nfl_market_history_snapshots
                          WHERE game_id = :game_id
                            AND market_code = 'total'
                        )
                    ),
                    total_close AS (
                      SELECT
                        AVG(total_points)::numeric AS close_total,
                        MIN(source) AS close_total_source
                      FROM nfl_market_history_snapshots
                      WHERE game_id = :game_id
                        AND market_code = 'total'
                        AND captured_at = (
                          SELECT MAX(captured_at)
                          FROM nfl_market_history_snapshots
                          WHERE game_id = :game_id
                            AND market_code = 'total'
                        )
                    )
                    SELECT
                      mo.open_home_price,
                      mo.open_away_price,
                      mc.close_home_price,
                      mc.close_away_price,
                      to1.open_total,
                      tc.close_total,
                      to1.open_total_source,
                      tc.close_total_source
                    FROM moneyline_open mo
                    CROSS JOIN moneyline_close mc
                    CROSS JOIN total_open to1
                    CROSS JOIN total_close tc
                    """
                ),
                {"game_id": game_id},
            ).fetchone()
            if not market_points:
                continue

            m = dict(market_points._mapping)
            home_win_prob = _to_float_like(p.get("home_win_prob"))
            fair_home_ml = _to_int_like(p.get("fair_home_ml"))
            fair_away_ml = _to_int_like(p.get("fair_away_ml"))
            total_mean = _to_float_like(p.get("total_mean"))

            open_home_ml = _to_int_like(m.get("open_home_price"))
            open_away_ml = _to_int_like(m.get("open_away_price"))
            close_home_ml = _to_int_like(m.get("close_home_price"))
            close_away_ml = _to_int_like(m.get("close_away_price"))
            open_total = _to_float_like(m.get("open_total"))
            close_total = _to_float_like(m.get("close_total"))
            open_total_source = str(m.get("open_total_source") or "")
            close_total_source = str(m.get("close_total_source") or "")

            # Moneyline CLV: pick side from model win-prob and compare implied probs.
            if (
                home_win_prob is not None
                and open_home_ml is not None
                and open_away_ml is not None
                and close_home_ml is not None
                and close_away_ml is not None
            ):
                side = "home" if home_win_prob >= 0.5 else "away"
                open_price = open_home_ml if side == "home" else open_away_ml
                close_price = close_home_ml if side == "home" else close_away_ml
                open_imp = _american_implied_prob(open_price)
                close_imp = _american_implied_prob(close_price)
                if open_imp is not None and close_imp is not None:
                    model_line = fair_home_ml if side == "home" else fair_away_ml
                    clv_value = close_imp - open_imp
                    session.execute(
                        text(
                            """
                            INSERT INTO nfl_clv_attribution (
                              projection_id, game_id, model_version, market_code, recommended_side,
                              open_line, close_line, model_line, clv_value, details, created_at
                            ) VALUES (
                              :projection_id, :game_id, :model_version, :market_code, :recommended_side,
                              :open_line, :close_line, :model_line, :clv_value, CAST(:details AS jsonb), :created_at
                            )
                            ON CONFLICT (projection_id, market_code) DO UPDATE SET
                              recommended_side = EXCLUDED.recommended_side,
                              open_line = EXCLUDED.open_line,
                              close_line = EXCLUDED.close_line,
                              model_line = EXCLUDED.model_line,
                              clv_value = EXCLUDED.clv_value,
                              details = EXCLUDED.details,
                              created_at = EXCLUDED.created_at
                            """
                        ),
                        {
                            "projection_id": str(p["id"]),
                            "game_id": game_id,
                            "model_version": str(p["model_version"]),
                            "market_code": "moneyline",
                            "recommended_side": side,
                            "open_line": float(open_price),
                            "close_line": float(close_price),
                            "model_line": float(model_line) if model_line is not None else None,
                            "clv_value": float(clv_value),
                            "details": json.dumps(
                                {
                                    "open_implied_prob": open_imp,
                                    "close_implied_prob": close_imp,
                                }
                            ),
                            "created_at": _now_utc(),
                        },
                    )
                    rows_upserted += 1

            # Total CLV: choose side using model total vs open total.
            if total_mean is not None and open_total is not None and close_total is not None:
                total_side = "over" if total_mean >= open_total else "under"
                total_clv = (close_total - open_total) if total_side == "over" else (open_total - close_total)
                session.execute(
                    text(
                        """
                        INSERT INTO nfl_clv_attribution (
                          projection_id, game_id, model_version, market_code, recommended_side,
                          open_line, close_line, model_line, clv_value, details, created_at
                        ) VALUES (
                          :projection_id, :game_id, :model_version, :market_code, :recommended_side,
                          :open_line, :close_line, :model_line, :clv_value, CAST(:details AS jsonb), :created_at
                        )
                        ON CONFLICT (projection_id, market_code) DO UPDATE SET
                          recommended_side = EXCLUDED.recommended_side,
                          open_line = EXCLUDED.open_line,
                          close_line = EXCLUDED.close_line,
                          model_line = EXCLUDED.model_line,
                          clv_value = EXCLUDED.clv_value,
                          details = EXCLUDED.details,
                          created_at = EXCLUDED.created_at
                        """
                    ),
                    {
                        "projection_id": str(p["id"]),
                        "game_id": game_id,
                        "model_version": str(p["model_version"]),
                        "market_code": "total",
                        "recommended_side": total_side,
                        "open_line": float(open_total),
                        "close_line": float(close_total),
                        "model_line": float(total_mean),
                        "clv_value": float(total_clv),
                        "details": json.dumps(
                            {
                                "open_total_source": open_total_source,
                                "close_total_source": close_total_source,
                                "market_substrate": (
                                    "historical-total-snapshots"
                                    if "normalized-total" not in f"{open_total_source}:{close_total_source}"
                                    else "normalized-total-proxy"
                                ),
                            }
                        ),
                        "created_at": _now_utc(),
                    },
                )
                rows_upserted += 1

        session.commit()
        return {
            "projections_seen": projections_seen,
            "clv_rows_upserted": rows_upserted,
        }
    except Exception:
        session.rollback()
        log.exception("Failed running NFL CLV attribution")
        raise
    finally:
        session.close()


def _compute_nfl_pick_hit_metrics(clv_rows: List[Dict[str, Any]]) -> Dict[str, Optional[float]]:
    moneyline_hits = 0
    moneyline_seen = 0
    moneyline_pos_hits = 0
    moneyline_pos_seen = 0
    total_hits = 0
    total_seen = 0
    total_pos_hits = 0
    total_pos_seen = 0

    for row in clv_rows:
        market = str(row.get("market_code") or "")
        side = str(row.get("recommended_side") or "")
        positive_edge = (_to_float_like(row.get("clv_value")) or 0.0) > 0.0
        if market == "moneyline":
            home_won = row.get("home_team_won")
            if home_won is None or side not in {"home", "away"}:
                continue
            won = bool(home_won) if side == "home" else not bool(home_won)
            moneyline_seen += 1
            moneyline_hits += 1 if won else 0
            if positive_edge:
                moneyline_pos_seen += 1
                moneyline_pos_hits += 1 if won else 0
        elif market == "total":
            final_total = _to_float_like(row.get("final_total_points"))
            close_line = _to_float_like(row.get("close_line"))
            open_line = _to_float_like(row.get("open_line"))
            settle_line = close_line if close_line is not None else open_line
            if final_total is None or settle_line is None or side not in {"over", "under"}:
                continue
            won = final_total > settle_line if side == "over" else final_total < settle_line
            total_seen += 1
            total_hits += 1 if won else 0
            if positive_edge:
                total_pos_seen += 1
                total_pos_hits += 1 if won else 0

    return {
        "moneyline_hit_rate": round(moneyline_hits / moneyline_seen, 6) if moneyline_seen > 0 else None,
        "moneyline_pick_sample_size": moneyline_seen,
        "moneyline_positive_edge_hit_rate": (
            round(moneyline_pos_hits / moneyline_pos_seen, 6) if moneyline_pos_seen > 0 else None
        ),
        "moneyline_positive_edge_sample_size": moneyline_pos_seen,
        "total_hit_rate": round(total_hits / total_seen, 6) if total_seen > 0 else None,
        "total_pick_sample_size": total_seen,
        "total_positive_edge_hit_rate": round(total_pos_hits / total_pos_seen, 6) if total_pos_seen > 0 else None,
        "total_positive_edge_sample_size": total_pos_seen,
    }


def _compute_nfl_quality_payload(
    *,
    point_rows: List[Dict[str, Any]],
    clv_rollup: Dict[str, Any],
    clv_rows: List[Dict[str, Any]],
    model_version: str,
    lookback_days: int,
    totals_calibration: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    brier_points = [
        (
            _to_float_like(row.get("home_win_prob")),
            1.0 if row.get("home_team_won") else 0.0,
        )
        for row in point_rows
        if _to_float_like(row.get("home_win_prob")) is not None and row.get("home_team_won") is not None
    ]
    moneyline_brier = (
        round(sum((float(p) - float(a)) ** 2 for p, a in brier_points) / len(brier_points), 6)
        if brier_points
        else None
    )
    total_points_base = []
    total_points_calibrated = []
    for row in point_rows:
        pred_total = _to_float_like(row.get("total_mean"))
        actual_total = _to_float_like(row.get("final_total_points"))
        if pred_total is None or actual_total is None:
            continue
        total_points_base.append((pred_total, actual_total))
        calibrated_total = apply_totals_calibration(pred_total, totals_calibration or {})
        if calibrated_total is not None:
            total_points_calibrated.append((float(calibrated_total), actual_total))
    total_mae_base = (
        round(sum(abs(float(pred) - float(actual)) for pred, actual in total_points_base) / len(total_points_base), 4)
        if total_points_base
        else None
    )
    total_mae = (
        round(
            sum(abs(float(pred) - float(actual)) for pred, actual in total_points_calibrated)
            / len(total_points_calibrated),
            4,
        )
        if total_points_calibrated
        else None
    )
    clv_sample = _to_int_like(clv_rollup.get("sample_size")) or 0
    clv_positive = _to_int_like(clv_rollup.get("positive_count")) or 0
    clv_hit_metrics = _compute_nfl_pick_hit_metrics(clv_rows)
    game_dates = sorted({str(r.get("game_date")) for r in point_rows if r.get("game_date") is not None})
    return {
        "model_version": model_version,
        "lookback_days": int(lookback_days),
        "sample_size": len(point_rows),
        "moneyline_brier": moneyline_brier,
        "moneyline_brier_sample_size": len(brier_points),
        "total_mae": total_mae,
        "total_mae_base": total_mae_base,
        "total_mae_sample_size": len(total_points_calibrated),
        "totals_calibration": totals_calibration or {},
        "clv_avg": round(float(clv_rollup.get("avg_clv")), 6) if _to_float_like(clv_rollup.get("avg_clv")) is not None else None,
        "clv_sample_size": clv_sample,
        "clv_positive_rate": round(clv_positive / clv_sample, 6) if clv_sample > 0 else None,
        "calendar_days_covered": len(game_dates),
        "last_game_date": game_dates[-1] if game_dates else None,
        **clv_hit_metrics,
    }


def _fetch_nfl_backtest_points(
    session: Any,
    *,
    model_version: str,
    lookback_days: int,
) -> List[Dict[str, Any]]:
    rows = session.execute(
        text(
            """
            SELECT
              mo.game_id,
              g.game_date,
              lp.home_win_prob,
              lp.total_mean,
              lp.projection_created_at,
              mo.home_team_won,
              mo.final_total_points,
              GREATEST(
                COALESCE(mo.completed_at, '-infinity'::timestamptz),
                COALESCE(
                  g.start_time + INTERVAL '6 hours',
                  ((g.game_date::date + INTERVAL '1 day')::timestamptz)
                )
              ) AS outcome_completed_at
            FROM nfl_market_outcomes mo
            JOIN games g ON g.id = mo.game_id
            JOIN LATERAL (
              SELECT
                mp.home_win_prob,
                mp.total_mean,
                mp.created_at AS projection_created_at
              FROM nfl_market_projections mp
              WHERE mp.game_id = mo.game_id
                AND mp.model_version = :model_version
                AND mp.created_at < GREATEST(
                  COALESCE(mo.completed_at, '-infinity'::timestamptz),
                  COALESCE(
                    g.start_time + INTERVAL '6 hours',
                    ((g.game_date::date + INTERVAL '1 day')::timestamptz)
                  )
                )
              ORDER BY mp.created_at DESC
              LIMIT 1
            ) lp ON TRUE
            WHERE g.game_date >= CURRENT_DATE - make_interval(days => :lookback_days)
            """
        ),
        {"model_version": model_version, "lookback_days": int(lookback_days)},
    ).fetchall()
    return [dict(r._mapping) for r in rows]


def _persist_nfl_quality_snapshot(
    session: Any,
    *,
    run_date: date,
    model_version: str,
    pipeline_stage: str,
    payload: Dict[str, Any],
) -> None:
    session.execute(
        text(
            """
            INSERT INTO nfl_model_quality_snapshots (
              run_date, model_version, pipeline_stage, payload, created_at
            ) VALUES (
              :run_date, :model_version, :pipeline_stage, CAST(:payload AS jsonb), :created_at
            )
            """
        ),
        {
            "run_date": run_date,
            "model_version": model_version,
            "pipeline_stage": pipeline_stage,
            "payload": json.dumps(payload),
            "created_at": _now_utc(),
        },
    )


@celery_app.task(name="src.tasks.run_nfl_quality_grading")
def run_nfl_quality_grading(
    lookback_days: int = 60,
    model_version: str = DEFAULT_NFL_MODEL_VERSION,
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        totals_calibration = fetch_nfl_totals_calibration(
            session,
            model_version=model_version,
            lookback_days=max(int(lookback_days), int(float(os.getenv("NFL_TOTALS_CALIBRATION_LOOKBACK_DAYS", "240")))),
        )
        points = session.execute(
            text(
                """
                WITH latest_proj AS (
                  SELECT DISTINCT ON (mp.game_id)
                    mp.id AS projection_id,
                    mp.game_id,
                    mp.model_version,
                    mp.home_win_prob,
                    mp.total_mean,
                    mp.created_at AS projection_created_at,
                    g.game_date
                  FROM nfl_market_projections mp
                  JOIN games g ON g.id = mp.game_id
                  WHERE mp.model_version = :model_version
                    AND g.game_date >= CURRENT_DATE - make_interval(days => :lookback_days)
                  ORDER BY mp.game_id, mp.created_at DESC
                )
                SELECT
                  lp.projection_id,
                  lp.game_id,
                  lp.model_version,
                  lp.home_win_prob,
                  lp.total_mean,
                  lp.game_date,
                  mo.home_team_won,
                  mo.final_total_points
                FROM latest_proj lp
                JOIN nfl_market_outcomes mo ON mo.game_id = lp.game_id
                """
            ),
            {"model_version": model_version, "lookback_days": int(lookback_days)},
        ).fetchall()
        point_rows = [dict(r._mapping) for r in points]

        clv_rollup_row = session.execute(
            text(
                """
                SELECT
                  COUNT(*)::int AS sample_size,
                  AVG(clv_value)::numeric AS avg_clv,
                  SUM(CASE WHEN clv_value > 0 THEN 1 ELSE 0 END)::int AS positive_count
                FROM nfl_clv_attribution
                WHERE model_version = :model_version
                  AND created_at >= NOW() - make_interval(days => :lookback_days)
                """
            ),
            {"model_version": model_version, "lookback_days": int(lookback_days)},
        ).fetchone()
        clv_rollup = dict(clv_rollup_row._mapping) if clv_rollup_row is not None else {}

        clv_hits_rows = session.execute(
            text(
                """
                SELECT
                  c.market_code,
                  c.recommended_side,
                  c.open_line,
                  c.close_line,
                  c.clv_value,
                  mo.home_team_won,
                  mo.final_total_points
                FROM nfl_clv_attribution c
                JOIN nfl_market_outcomes mo ON mo.game_id = c.game_id
                JOIN games g ON g.id = c.game_id
                WHERE c.model_version = :model_version
                  AND g.game_date >= CURRENT_DATE - make_interval(days => :lookback_days)
                """
            ),
            {"model_version": model_version, "lookback_days": int(lookback_days)},
        ).fetchall()
        payload = _compute_nfl_quality_payload(
            point_rows=point_rows,
            clv_rollup=clv_rollup,
            clv_rows=[dict(r._mapping) for r in clv_hits_rows],
            model_version=model_version,
            lookback_days=int(lookback_days),
            totals_calibration=totals_calibration,
        )
        _persist_nfl_quality_snapshot(
            session,
            run_date=date.today(),
            model_version=model_version,
            pipeline_stage="weekly_quality",
            payload=payload,
        )
        session.commit()
        return payload
    except Exception:
        session.rollback()
        log.exception("Failed running NFL quality grading")
        raise
    finally:
        session.close()


@celery_app.task(name="src.tasks.run_nfl_walkforward_backtest")
def run_nfl_walkforward_backtest(
    *,
    model_version: str = DEFAULT_NFL_MODEL_VERSION,
    lookback_days: int = 240,
    training_days: int = 56,
    step_days: int = 7,
    apply_calibration: bool = True,
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        raw_points = _fetch_nfl_backtest_points(
            session,
            model_version=model_version,
            lookback_days=lookback_days,
        )
        eligible_points = [point for point in raw_points if _is_nfl_backtest_point_eligible(point)]
        leakage_violations = _count_leakage_violations(eligible_points)
        backtest_points = [
            {
                "game_id": point.get("game_id"),
                "game_date": point.get("game_date"),
                "fg_home_win_prob": point.get("home_win_prob"),
                "fg_total_mean": point.get("total_mean"),
                "home_team_won": point.get("home_team_won"),
                "final_total_runs": point.get("final_total_points"),
            }
            for point in eligible_points
            if _to_float_like(point.get("home_win_prob")) is not None
            and _to_float_like(point.get("total_mean")) is not None
            and point.get("home_team_won") is not None
            and _to_float_like(point.get("final_total_points")) is not None
        ]
        result = _walkforward_backtest(
            points=backtest_points,
            training_days=training_days,
            step_days=step_days,
            apply_calibration=apply_calibration,
        )
        payload = {
            "model_version": model_version,
            "lookback_days": int(lookback_days),
            "training_days": int(training_days),
            "step_days": int(step_days),
            "apply_calibration": bool(apply_calibration),
            "leakage_violations": int(leakage_violations),
            **result,
        }
        session.execute(
            text(
                """
                INSERT INTO nfl_model_backtest_runs (
                  run_date, model_version, lookback_days, training_days, step_days,
                  apply_calibration, payload, created_at
                ) VALUES (
                  :run_date, :model_version, :lookback_days, :training_days, :step_days,
                  :apply_calibration, CAST(:payload AS jsonb), :created_at
                )
                """
            ),
            {
                "run_date": date.today(),
                "model_version": model_version,
                "lookback_days": int(lookback_days),
                "training_days": int(training_days),
                "step_days": int(step_days),
                "apply_calibration": bool(apply_calibration),
                "payload": json.dumps(payload),
                "created_at": _now_utc(),
            },
        )
        session.commit()
        return payload
    except Exception:
        session.rollback()
        log.exception("Failed running NFL walk-forward backtest")
        raise
    finally:
        session.close()


def _persist_nfl_promotion_event(
    session: Any,
    *,
    champion_model_version: str,
    challenger_model_version: str,
    lookback_days: int,
    auto_promote_requested: bool,
    auto_promote_enabled: bool,
    promoted: bool,
    decision: Dict[str, Any],
    payload: Dict[str, Any],
) -> None:
    session.execute(
        text(
            """
            INSERT INTO nfl_model_promotion_events (
              evaluated_at, champion_model_version, challenger_model_version, lookback_days,
              auto_promote_requested, auto_promote_enabled, promoted, decision, payload
            ) VALUES (
              :evaluated_at, :champion_model_version, :challenger_model_version, :lookback_days,
              :auto_promote_requested, :auto_promote_enabled, :promoted, CAST(:decision AS jsonb), CAST(:payload AS jsonb)
            )
            """
        ),
        {
            "evaluated_at": _now_utc(),
            "champion_model_version": champion_model_version,
            "challenger_model_version": challenger_model_version,
            "lookback_days": int(lookback_days),
            "auto_promote_requested": bool(auto_promote_requested),
            "auto_promote_enabled": bool(auto_promote_enabled),
            "promoted": bool(promoted),
            "decision": json.dumps(decision),
            "payload": json.dumps(payload),
        },
    )


def _set_nfl_active_model(
    session: Any,
    *,
    model_version: str,
    reason: str,
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    previous_row = session.execute(
        text(
            """
            SELECT active_model_version
            FROM nfl_model_runtime_state
            WHERE state_key = :state_key
            LIMIT 1
            """
        ),
        {"state_key": NFL_MODEL_STATE_KEY},
    ).fetchone()
    previous = str(previous_row[0]) if previous_row is not None and previous_row[0] is not None else None
    session.execute(
        text(
            """
            INSERT INTO nfl_model_runtime_state (
              state_key, active_model_version, previous_model_version, reason, metadata, updated_at
            ) VALUES (
              :state_key, :active_model_version, :previous_model_version, :reason, CAST(:metadata AS jsonb), :updated_at
            )
            ON CONFLICT (state_key) DO UPDATE SET
              active_model_version = EXCLUDED.active_model_version,
              previous_model_version = EXCLUDED.previous_model_version,
              reason = EXCLUDED.reason,
              metadata = EXCLUDED.metadata,
              updated_at = EXCLUDED.updated_at
            """
        ),
        {
            "state_key": NFL_MODEL_STATE_KEY,
            "active_model_version": model_version,
            "previous_model_version": previous,
            "reason": reason,
            "metadata": json.dumps(metadata),
            "updated_at": _now_utc(),
        },
    )
    return {"active_model_version": model_version, "previous_model_version": previous}


def _fetch_nfl_quality_snapshot(
    session: Any,
    *,
    model_version: str,
) -> Dict[str, Any]:
    row = session.execute(
        text(
            """
            SELECT payload, created_at
            FROM nfl_model_quality_snapshots
            WHERE model_version = :model_version
              AND pipeline_stage = 'weekly_quality'
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"model_version": model_version},
    ).fetchone()
    payload = dict(row._mapping).get("payload") if row is not None else {}
    return payload if isinstance(payload, dict) else {}


def _fetch_nfl_backtest_snapshot(
    session: Any,
    *,
    model_version: str,
) -> Dict[str, Any]:
    row = session.execute(
        text(
            """
            SELECT payload, created_at
            FROM nfl_model_backtest_runs
            WHERE model_version = :model_version
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"model_version": model_version},
    ).fetchone()
    payload = dict(row._mapping).get("payload") if row is not None else {}
    return payload if isinstance(payload, dict) else {}


def _fetch_nfl_clv_rollup(
    session: Any,
    *,
    model_version: str,
    lookback_days: int,
) -> Dict[str, Any]:
    row = session.execute(
        text(
            """
            SELECT
              COUNT(*)::int AS sample_size,
              AVG(clv_value)::numeric AS avg_clv,
              SUM(CASE WHEN clv_value > 0 THEN 1 ELSE 0 END)::int AS positive_count
            FROM nfl_clv_attribution
            WHERE model_version = :model_version
              AND created_at >= NOW() - make_interval(days => :lookback_days)
            """
        ),
        {"model_version": model_version, "lookback_days": int(lookback_days)},
    ).fetchone()
    if row is None:
        return {"sample_size": 0, "avg_clv": None, "positive_rate": None}
    sample_size = int(_safe_float(row.sample_size) or 0)
    positive_count = int(_safe_float(row.positive_count) or 0)
    return {
        "sample_size": sample_size,
        "avg_clv": _safe_float(row.avg_clv),
        "positive_rate": (positive_count / sample_size) if sample_size > 0 else None,
    }


def _resolve_active_nfl_model(session: Any, fallback: str) -> str:
    row = session.execute(
        text(
            """
            SELECT active_model_version
            FROM nfl_model_runtime_state
            WHERE state_key = :state_key
            LIMIT 1
            """
        ),
        {"state_key": NFL_MODEL_STATE_KEY},
    ).fetchone()
    if row is None or row[0] is None:
        return fallback
    return str(row[0])


def _decide_nfl_challenger_promotion(
    *,
    champion_quality: Dict[str, Any],
    challenger_quality: Dict[str, Any],
    champion_backtest: Dict[str, Any],
    challenger_backtest: Dict[str, Any],
    champion_clv: Dict[str, Any],
    challenger_clv: Dict[str, Any],
) -> Dict[str, Any]:
    min_sample = int(os.getenv("NFL_PROMOTION_MIN_SAMPLE_SIZE", "140"))
    min_brier_improvement = float(os.getenv("NFL_PROMOTION_MIN_BRIER_IMPROVEMENT", "0.0025"))
    min_mae_improvement = float(os.getenv("NFL_PROMOTION_MIN_MAE_IMPROVEMENT", "0.08"))
    min_clv_improvement = float(os.getenv("NFL_PROMOTION_MIN_CLV_IMPROVEMENT", "0.0020"))
    min_backtest_sample = int(os.getenv("NFL_PROMOTION_MIN_BACKTEST_SAMPLE", "90"))
    min_backtest_brier_improvement = float(os.getenv("NFL_PROMOTION_MIN_BACKTEST_BRIER_IMPROVEMENT", "0.0010"))
    max_brier_drift = float(os.getenv("NFL_PROMOTION_MAX_BRIER_DRIFT", "0.018"))
    max_mae_drift = float(os.getenv("NFL_PROMOTION_MAX_MAE_DRIFT", "1.10"))

    champion_sample = int(_safe_float(champion_quality.get("sample_size")) or 0)
    challenger_sample = int(_safe_float(challenger_quality.get("sample_size")) or 0)
    champion_brier = _safe_float(champion_quality.get("moneyline_brier"))
    challenger_brier = _safe_float(challenger_quality.get("moneyline_brier"))
    champion_mae = _safe_float(champion_quality.get("total_mae"))
    challenger_mae = _safe_float(challenger_quality.get("total_mae"))
    champion_clv_avg = _safe_float(champion_clv.get("avg_clv"))
    challenger_clv_avg = _safe_float(challenger_clv.get("avg_clv"))
    challenger_backtest_sample = int(_safe_float(challenger_backtest.get("sample_size")) or 0)
    challenger_backtest_brier_improvement = _safe_float(challenger_backtest.get("brier_improvement"))
    challenger_backtest_brier = _safe_float(challenger_backtest.get("calibrated_brier_ml"))
    challenger_backtest_mae = _safe_float(challenger_backtest.get("calibrated_mae_total_runs"))

    brier_gain = (
        (champion_brier - challenger_brier)
        if champion_brier is not None and challenger_brier is not None
        else None
    )
    mae_gain = (
        (champion_mae - challenger_mae)
        if champion_mae is not None and challenger_mae is not None
        else None
    )
    clv_gain = (
        (challenger_clv_avg - champion_clv_avg)
        if challenger_clv_avg is not None and champion_clv_avg is not None
        else None
    )
    brier_drift = (
        abs(challenger_brier - challenger_backtest_brier)
        if challenger_brier is not None and challenger_backtest_brier is not None
        else None
    )
    mae_drift = (
        abs(challenger_mae - challenger_backtest_mae)
        if challenger_mae is not None and challenger_backtest_mae is not None
        else None
    )

    checks = {
        "sample_size_ok": champion_sample >= min_sample and challenger_sample >= min_sample,
        "brier_ok": brier_gain is not None and brier_gain >= min_brier_improvement,
        "mae_ok": mae_gain is not None and mae_gain >= min_mae_improvement,
        "clv_ok": clv_gain is not None and clv_gain >= min_clv_improvement,
        "backtest_sample_ok": challenger_backtest_sample >= min_backtest_sample,
        "backtest_brier_ok": (
            challenger_backtest_brier_improvement is not None
            and challenger_backtest_brier_improvement >= min_backtest_brier_improvement
        ),
        "drift_guardrail_ok": (
            brier_drift is not None
            and mae_drift is not None
            and brier_drift <= max_brier_drift
            and mae_drift <= max_mae_drift
        ),
    }
    reasons = [name for name, passed in checks.items() if not passed]
    return {
        "promote": all(checks.values()),
        "checks": checks,
        "thresholds": {
            "min_sample_size": min_sample,
            "min_brier_improvement": min_brier_improvement,
            "min_mae_improvement": min_mae_improvement,
            "min_clv_improvement": min_clv_improvement,
            "min_backtest_sample": min_backtest_sample,
            "min_backtest_brier_improvement": min_backtest_brier_improvement,
            "max_brier_drift": max_brier_drift,
            "max_mae_drift": max_mae_drift,
        },
        "deltas": {
            "brier_improvement": None if brier_gain is None else round(brier_gain, 6),
            "mae_improvement": None if mae_gain is None else round(mae_gain, 4),
            "clv_improvement": None if clv_gain is None else round(clv_gain, 6),
            "brier_drift": None if brier_drift is None else round(brier_drift, 6),
            "mae_drift": None if mae_drift is None else round(mae_drift, 4),
        },
        "reasons": reasons,
    }


@celery_app.task(name="src.tasks.evaluate_nfl_model_promotion")
def evaluate_nfl_model_promotion(
    *,
    challenger_model_version: str,
    lookback_days: int = 45,
    auto_promote: bool = True,
    champion_model_version: Optional[str] = None,
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        champion_version = champion_model_version or _resolve_active_nfl_model(
            session,
            fallback=DEFAULT_NFL_MODEL_VERSION,
        )
        champion_quality = _fetch_nfl_quality_snapshot(session, model_version=champion_version)
        challenger_quality = _fetch_nfl_quality_snapshot(session, model_version=challenger_model_version)
        champion_backtest = _fetch_nfl_backtest_snapshot(session, model_version=champion_version)
        challenger_backtest = _fetch_nfl_backtest_snapshot(session, model_version=challenger_model_version)
        champion_clv = _fetch_nfl_clv_rollup(
            session,
            model_version=champion_version,
            lookback_days=int(lookback_days),
        )
        challenger_clv = _fetch_nfl_clv_rollup(
            session,
            model_version=challenger_model_version,
            lookback_days=int(lookback_days),
        )
        decision = _decide_nfl_challenger_promotion(
            champion_quality=champion_quality,
            challenger_quality=challenger_quality,
            champion_backtest=champion_backtest,
            challenger_backtest=challenger_backtest,
            champion_clv=champion_clv,
            challenger_clv=challenger_clv,
        )
        auto_enabled = auto_promote and _env_bool("NFL_AUTO_PROMOTE_ENABLED", False)
        promoted = False
        state_change: Dict[str, Any] = {}
        if decision.get("promote") and auto_enabled:
            state_change = _set_nfl_active_model(
                session,
                model_version=challenger_model_version,
                reason=f"auto-promotion lookback={int(lookback_days)}",
                metadata={
                    "decision_checks": decision.get("checks"),
                    "decision_deltas": decision.get("deltas"),
                },
            )
            promoted = True

        payload = {
            "champion_model_version": champion_version,
            "challenger_model_version": challenger_model_version,
            "lookback_days": int(lookback_days),
            "decision": decision,
            "auto_promote_requested": bool(auto_promote),
            "auto_promote_enabled": bool(auto_enabled),
            "promoted": promoted,
            "state_change": state_change,
            "champion_quality": champion_quality,
            "challenger_quality": challenger_quality,
            "champion_backtest": champion_backtest,
            "challenger_backtest": challenger_backtest,
            "champion_clv": champion_clv,
            "challenger_clv": challenger_clv,
        }
        _persist_nfl_promotion_event(
            session,
            champion_model_version=champion_version,
            challenger_model_version=challenger_model_version,
            lookback_days=int(lookback_days),
            auto_promote_requested=bool(auto_promote),
            auto_promote_enabled=bool(auto_enabled),
            promoted=promoted,
            decision=decision,
            payload=payload,
        )
        session.commit()
        return payload
    except Exception:
        session.rollback()
        log.exception("Failed evaluating NFL model promotion")
        raise
    finally:
        session.close()


@celery_app.task(name="src.tasks.pull_mlb_context_snapshot")
def pull_mlb_context_snapshot(days_ahead: int = 5) -> Dict[str, int]:
    start = date.today()
    end = start + timedelta(days=max(0, days_ahead))
    schedule = fetch_mlb_schedule(start, end)

    session = SessionLocal()
    created_or_updated = 0
    games_seen = 0
    team_bullpen_cache: Dict[int, Dict[str, float]] = {}
    try:
        for g in schedule:
            event_id = g["external_game_id"]
            game_dt = _parse_iso_datetime(g.get("game_time")) or _now_utc()
            game_id, _league_id, _home_id, _away_id, _sport_id = _ensure_hierarchy(
                session,
                sport_key="baseball_mlb",
                game_dt=game_dt,
                home_team=g["home_team"],
                away_team=g["away_team"],
                event_id=event_id,
            )
            games_seen += 1

            starter_home_features = starter_identity_features(
                g.get("probable_pitcher_home"),
                season=game_dt.date().year,
            )
            starter_away_features = starter_identity_features(
                g.get("probable_pitcher_away"),
                season=game_dt.date().year,
            )
            try:
                game_lineups = fetch_game_lineup_features(event_id)
            except Exception:
                game_lineups = {"home": {}, "away": {}}
            home_lineup = game_lineups.get("home") or {}
            away_lineup = game_lineups.get("away") or {}
            lineup_confirmed = (
                bool(g.get("lineup_confirmed"))
                or bool(home_lineup.get("lineup_confirmed"))
                or bool(away_lineup.get("lineup_confirmed"))
            )

            weather = fetch_forecast_for_game(
                team_abbr=g["home_abbr"],
                game_time_iso=g["game_time"],
            )
            lineup = lineup_confidence(
                lineup_confirmed=lineup_confirmed,
                probable_pitcher_home=g.get("probable_pitcher_home"),
                probable_pitcher_away=g.get("probable_pitcher_away"),
            )
            home_team_id = g.get("home_team_id")
            away_team_id = g.get("away_team_id")
            if isinstance(home_team_id, int) and home_team_id not in team_bullpen_cache:
                team_bullpen_cache[home_team_id] = fetch_team_bullpen_fatigue(home_team_id, start)
            if isinstance(away_team_id, int) and away_team_id not in team_bullpen_cache:
                team_bullpen_cache[away_team_id] = fetch_team_bullpen_fatigue(away_team_id, start)
            home_bp = team_bullpen_cache.get(home_team_id) or fetch_team_bullpen_fatigue(None, start)
            away_bp = team_bullpen_cache.get(away_team_id) or fetch_team_bullpen_fatigue(None, start)
            park_factor = park_factor_for_team(g.get("home_abbr"))
            home_offense = build_team_offense_context(
                home_team_id,
                as_of=start,
                opponent_starter_handedness=str(starter_away_features.get("handedness") or "U"),
                lineup_features=home_lineup,
            )
            away_offense = build_team_offense_context(
                away_team_id,
                as_of=start,
                opponent_starter_handedness=str(starter_home_features.get("handedness") or "U"),
                lineup_features=away_lineup,
            )
            session.execute(
                text(
                    """
                    INSERT INTO mlb_game_context (
                      game_id, source, probable_pitcher_home, probable_pitcher_away,
                      lineup_confirmed, umpire_home_plate, weather_source,
                      weather_temp_f, weather_wind_mph, weather_wind_dir_deg, weather_humidity_pct,
                      park_factor_runs,
                      lineup_confidence_home, lineup_confidence_away,
                      offense_index_home, offense_index_away,
                      offense_split_index_home, offense_split_index_away,
                      recent_form_index_home, recent_form_index_away,
                      lineup_strength_index_home, lineup_strength_index_away,
                      bullpen_fatigue_home, bullpen_fatigue_away,
                      bullpen_ip_last3_home, bullpen_ip_last3_away,
                      bullpen_availability_home, bullpen_availability_away,
                      bullpen_high_leverage_availability_home, bullpen_high_leverage_availability_away,
                      umpire_run_factor,
                      context, created_at, updated_at
                    ) VALUES (
                      :game_id, :source, :probable_pitcher_home, :probable_pitcher_away,
                      :lineup_confirmed, :umpire_home_plate, :weather_source,
                      :weather_temp_f, :weather_wind_mph, :weather_wind_dir_deg, :weather_humidity_pct,
                      :park_factor_runs,
                      :lineup_confidence_home, :lineup_confidence_away,
                      :offense_index_home, :offense_index_away,
                      :offense_split_index_home, :offense_split_index_away,
                      :recent_form_index_home, :recent_form_index_away,
                      :lineup_strength_index_home, :lineup_strength_index_away,
                      :bullpen_fatigue_home, :bullpen_fatigue_away,
                      :bullpen_ip_last3_home, :bullpen_ip_last3_away,
                      :bullpen_availability_home, :bullpen_availability_away,
                      :bullpen_high_leverage_availability_home, :bullpen_high_leverage_availability_away,
                      :umpire_run_factor,
                      CAST(:context AS jsonb), :created_at, :updated_at
                    )
                    ON CONFLICT (game_id) DO UPDATE SET
                      probable_pitcher_home = EXCLUDED.probable_pitcher_home,
                      probable_pitcher_away = EXCLUDED.probable_pitcher_away,
                      lineup_confirmed = EXCLUDED.lineup_confirmed,
                      umpire_home_plate = EXCLUDED.umpire_home_plate,
                      weather_source = EXCLUDED.weather_source,
                      weather_temp_f = EXCLUDED.weather_temp_f,
                      weather_wind_mph = EXCLUDED.weather_wind_mph,
                      weather_wind_dir_deg = EXCLUDED.weather_wind_dir_deg,
                      weather_humidity_pct = EXCLUDED.weather_humidity_pct,
                      park_factor_runs = EXCLUDED.park_factor_runs,
                      lineup_confidence_home = EXCLUDED.lineup_confidence_home,
                      lineup_confidence_away = EXCLUDED.lineup_confidence_away,
                      offense_index_home = EXCLUDED.offense_index_home,
                      offense_index_away = EXCLUDED.offense_index_away,
                      offense_split_index_home = EXCLUDED.offense_split_index_home,
                      offense_split_index_away = EXCLUDED.offense_split_index_away,
                      recent_form_index_home = EXCLUDED.recent_form_index_home,
                      recent_form_index_away = EXCLUDED.recent_form_index_away,
                      lineup_strength_index_home = EXCLUDED.lineup_strength_index_home,
                      lineup_strength_index_away = EXCLUDED.lineup_strength_index_away,
                      bullpen_fatigue_home = EXCLUDED.bullpen_fatigue_home,
                      bullpen_fatigue_away = EXCLUDED.bullpen_fatigue_away,
                      bullpen_ip_last3_home = EXCLUDED.bullpen_ip_last3_home,
                      bullpen_ip_last3_away = EXCLUDED.bullpen_ip_last3_away,
                      bullpen_availability_home = EXCLUDED.bullpen_availability_home,
                      bullpen_availability_away = EXCLUDED.bullpen_availability_away,
                      bullpen_high_leverage_availability_home = EXCLUDED.bullpen_high_leverage_availability_home,
                      bullpen_high_leverage_availability_away = EXCLUDED.bullpen_high_leverage_availability_away,
                      umpire_run_factor = EXCLUDED.umpire_run_factor,
                      context = EXCLUDED.context,
                      updated_at = EXCLUDED.updated_at
                    """
                ),
                {
                    "game_id": game_id,
                    "source": "mlb-stats-api",
                    "probable_pitcher_home": g.get("probable_pitcher_home"),
                    "probable_pitcher_away": g.get("probable_pitcher_away"),
                    "lineup_confirmed": lineup_confirmed,
                    "umpire_home_plate": g.get("umpire_home_plate"),
                    "weather_source": "open-meteo",
                    "weather_temp_f": weather.get("weather_temp_f"),
                    "weather_wind_mph": weather.get("weather_wind_mph"),
                    "weather_wind_dir_deg": weather.get("weather_wind_dir_deg"),
                    "weather_humidity_pct": weather.get("weather_humidity_pct"),
                    "park_factor_runs": park_factor,
                    "lineup_confidence_home": lineup["home"],
                    "lineup_confidence_away": lineup["away"],
                    "offense_index_home": home_offense["offense_index"],
                    "offense_index_away": away_offense["offense_index"],
                    "offense_split_index_home": home_offense["offense_split_index"],
                    "offense_split_index_away": away_offense["offense_split_index"],
                    "recent_form_index_home": home_offense["recent_form_index"],
                    "recent_form_index_away": away_offense["recent_form_index"],
                    "lineup_strength_index_home": home_offense["lineup_strength_index"],
                    "lineup_strength_index_away": away_offense["lineup_strength_index"],
                    "bullpen_fatigue_home": home_bp["bullpen_fatigue_score"],
                    "bullpen_fatigue_away": away_bp["bullpen_fatigue_score"],
                    "bullpen_ip_last3_home": home_bp["bullpen_ip_last3"],
                    "bullpen_ip_last3_away": away_bp["bullpen_ip_last3"],
                    "bullpen_availability_home": home_bp["bullpen_availability_score"],
                    "bullpen_availability_away": away_bp["bullpen_availability_score"],
                    "bullpen_high_leverage_availability_home": home_bp["bullpen_high_leverage_availability_score"],
                    "bullpen_high_leverage_availability_away": away_bp["bullpen_high_leverage_availability_score"],
                    "umpire_run_factor": umpire_run_factor(g.get("umpire_home_plate")),
                    "context": __import__("json").dumps(
                        {
                            "status": g.get("status"),
                            "home_abbr": g.get("home_abbr"),
                            "away_abbr": g.get("away_abbr"),
                            "bullpen_appearances_last3_home": home_bp["bullpen_appearances_last3"],
                            "bullpen_appearances_last3_away": away_bp["bullpen_appearances_last3"],
                            "bullpen_high_leverage_availability_home": home_bp["bullpen_high_leverage_availability_score"],
                            "bullpen_high_leverage_availability_away": away_bp["bullpen_high_leverage_availability_score"],
                            "starter_home_features": starter_home_features,
                            "starter_away_features": starter_away_features,
                            "home_offense_context": home_offense,
                            "away_offense_context": away_offense,
                            "home_lineup_players": home_lineup.get("players") or [],
                            "away_lineup_players": away_lineup.get("players") or [],
                        }
                    ),
                    "created_at": _now_utc(),
                    "updated_at": _now_utc(),
                },
            )
            created_or_updated += 1

        session.commit()
        return {
            "scheduled_games_fetched": len(schedule),
            "games_seen": games_seen,
            "context_rows_upserted": created_or_updated,
        }
    except Exception:
        session.rollback()
        log.exception("Failed to persist MLB context snapshot")
        raise
    finally:
        session.close()


@celery_app.task(name="src.tasks.run_mlb_market_simulations")
def run_mlb_market_simulations(
    game_date: Optional[str] = None,
    simulations: int = 4000,
    model_version: str = DEFAULT_MODEL_VERSION,
) -> Dict[str, int]:
    if game_date:
        try:
            target_date = date.fromisoformat(game_date)
        except ValueError as e:
            raise ValueError(f"game_date must be YYYY-MM-DD, got {game_date}") from e
    else:
        target_date = date.today()
    allow_historical = _env_bool("MLB_ALLOW_HISTORICAL_SIM", False)
    if target_date < date.today() and not allow_historical:
        raise ValueError(
            "Historical simulation is disabled by default (MLB_ALLOW_HISTORICAL_SIM=false) "
            "to prevent accidental time-leakage reruns."
        )

    session = SessionLocal()
    processed = 0
    inserted = 0
    try:
        rows = session.execute(
            text(
                """
                SELECT
                  g.id AS game_id,
                  g.status AS game_status,
                  home.name AS home_team,
                  away.name AS away_team,
                  c.probable_pitcher_home,
                  c.probable_pitcher_away,
                  c.umpire_home_plate,
                  c.lineup_confirmed,
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
                  c.umpire_run_factor
                FROM games g
                JOIN seasons s ON s.id = g.season_id
                JOIN leagues l ON l.id = s.league_id
                JOIN teams home ON home.id = g.home_team_id
                JOIN teams away ON away.id = g.away_team_id
                LEFT JOIN mlb_game_context c ON c.game_id = g.id
                WHERE l.code = 'mlb'
                  AND g.game_date = :game_date
                ORDER BY g.start_time
                """
            ),
            {"game_date": target_date},
        ).fetchall()

        for r in rows:
            m = dict(r._mapping)
            status = str(m.get("game_status") or "").strip().lower()
            if status in {"final", "closed", "completed"}:
                continue
            starter_home_feat = starter_identity_features(m.get("probable_pitcher_home"))
            starter_away_feat = starter_identity_features(m.get("probable_pitcher_away"))
            freshness = _info_freshness_score(
                updated_at=m.get("context_updated_at"),
                lineup_confirmed=bool(m["lineup_confirmed"]) if m.get("lineup_confirmed") is not None else False,
            )
            inputs = MlbGameInputs(
                game_id=str(m["game_id"]),
                home_team=str(m["home_team"]),
                away_team=str(m["away_team"]),
                starter_home=m.get("probable_pitcher_home"),
                starter_away=m.get("probable_pitcher_away"),
                starter_quality_home=float(starter_home_feat.get("starter_quality") or 1.0),
                starter_quality_away=float(starter_away_feat.get("starter_quality") or 1.0),
                starter_k_factor_home=float(starter_home_feat.get("k_factor") or 1.0),
                starter_k_factor_away=float(starter_away_feat.get("k_factor") or 1.0),
                starter_bb_factor_home=float(starter_home_feat.get("bb_factor") or 1.0),
                starter_bb_factor_away=float(starter_away_feat.get("bb_factor") or 1.0),
                starter_gb_factor_home=float(starter_home_feat.get("gb_factor") or 1.0),
                starter_gb_factor_away=float(starter_away_feat.get("gb_factor") or 1.0),
                umpire_home_plate=m.get("umpire_home_plate"),
                lineup_confirmed=bool(m["lineup_confirmed"]) if m.get("lineup_confirmed") is not None else False,
                weather_temp_f=float(m["weather_temp_f"]) if m.get("weather_temp_f") is not None else None,
                weather_wind_mph=float(m["weather_wind_mph"]) if m.get("weather_wind_mph") is not None else None,
                weather_wind_dir_deg=float(m["weather_wind_dir_deg"]) if m.get("weather_wind_dir_deg") is not None else None,
                weather_humidity_pct=float(m["weather_humidity_pct"]) if m.get("weather_humidity_pct") is not None else None,
                park_factor_runs=float(m["park_factor_runs"]) if m.get("park_factor_runs") is not None else None,
                offense_home=float(m["offense_index_home"]) if m.get("offense_index_home") is not None else 1.0,
                offense_away=float(m["offense_index_away"]) if m.get("offense_index_away") is not None else 1.0,
                offense_split_home=float(m["offense_split_index_home"]) if m.get("offense_split_index_home") is not None else 1.0,
                offense_split_away=float(m["offense_split_index_away"]) if m.get("offense_split_index_away") is not None else 1.0,
                recent_form_index_home=float(m["recent_form_index_home"]) if m.get("recent_form_index_home") is not None else 1.0,
                recent_form_index_away=float(m["recent_form_index_away"]) if m.get("recent_form_index_away") is not None else 1.0,
                lineup_strength_index_home=float(m["lineup_strength_index_home"]) if m.get("lineup_strength_index_home") is not None else 1.0,
                lineup_strength_index_away=float(m["lineup_strength_index_away"]) if m.get("lineup_strength_index_away") is not None else 1.0,
                lineup_confidence_home=float(m["lineup_confidence_home"]) if m.get("lineup_confidence_home") is not None else 0.85,
                lineup_confidence_away=float(m["lineup_confidence_away"]) if m.get("lineup_confidence_away") is not None else 0.85,
                bullpen_fatigue_home=float(m["bullpen_fatigue_home"]) if m.get("bullpen_fatigue_home") is not None else 0.5,
                bullpen_fatigue_away=float(m["bullpen_fatigue_away"]) if m.get("bullpen_fatigue_away") is not None else 0.5,
                bullpen_ip_last3_home=float(m["bullpen_ip_last3_home"]) if m.get("bullpen_ip_last3_home") is not None else 9.0,
                bullpen_ip_last3_away=float(m["bullpen_ip_last3_away"]) if m.get("bullpen_ip_last3_away") is not None else 9.0,
                bullpen_availability_home=float(m["bullpen_availability_home"]) if m.get("bullpen_availability_home") is not None else 0.65,
                bullpen_availability_away=float(m["bullpen_availability_away"]) if m.get("bullpen_availability_away") is not None else 0.65,
                bullpen_high_lev_availability_home=float(m["bullpen_high_leverage_availability_home"]) if m.get("bullpen_high_leverage_availability_home") is not None else 0.62,
                bullpen_high_lev_availability_away=float(m["bullpen_high_leverage_availability_away"]) if m.get("bullpen_high_leverage_availability_away") is not None else 0.62,
                umpire_run_factor=float(m["umpire_run_factor"]) if m.get("umpire_run_factor") is not None else 1.0,
                info_freshness_score_home=freshness,
                info_freshness_score_away=freshness,
            )
            seed = _default_projection_seed(inputs.game_id, model_version, simulations)
            projection = _run_simulation_by_model(
                inputs,
                simulations=simulations,
                seed=seed,
                model_version=model_version,
            )
            _insert_mlb_projection_and_audit(session, projection, seed=seed)
            processed += 1
            inserted += 1

        session.commit()
        return {"games_processed": processed, "projections_inserted": inserted}
    except Exception:
        session.rollback()
        log.exception("Failed running MLB market simulations")
        raise
    finally:
        session.close()


@celery_app.task(name="src.tasks.pull_mlb_outcomes")
def pull_mlb_outcomes(days_back: int = 30) -> Dict[str, int]:
    end = date.today()
    start = end - timedelta(days=max(1, days_back))
    schedule = fetch_mlb_schedule(start, end)

    upserted = 0
    session = SessionLocal()
    try:
        for g in schedule:
            if g.get("status") != "final":
                continue
            external_id = g.get("external_game_id")
            if not external_id:
                continue
            # Use game linescore endpoint for final runs.
            game_pk = external_id
            r = requests.get(
                f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live",
                timeout=20,
            )
            r.raise_for_status()
            payload = r.json()
            linescore = (payload.get("liveData") or {}).get("linescore") or {}
            teams = linescore.get("teams") or {}
            home_runs = teams.get("home", {}).get("runs")
            away_runs = teams.get("away", {}).get("runs")
            if home_runs is None or away_runs is None:
                continue

            game_row = session.execute(
                text("SELECT id FROM games WHERE external_id = :external_id LIMIT 1"),
                {"external_id": str(external_id)},
            ).fetchone()
            if not game_row:
                continue
            game_id = str(game_row[0])

            session.execute(
                text(
                    """
                    INSERT INTO mlb_market_outcomes (
                      game_id, actual_home_runs, actual_away_runs, final_total_runs,
                      home_team_won, source, completed_at, created_at, updated_at
                    ) VALUES (
                      :game_id, :actual_home_runs, :actual_away_runs, :final_total_runs,
                      :home_team_won, :source, :completed_at, :created_at, :updated_at
                    )
                    ON CONFLICT (game_id) DO UPDATE SET
                      actual_home_runs = EXCLUDED.actual_home_runs,
                      actual_away_runs = EXCLUDED.actual_away_runs,
                      final_total_runs = EXCLUDED.final_total_runs,
                      home_team_won = EXCLUDED.home_team_won,
                      source = EXCLUDED.source,
                      completed_at = EXCLUDED.completed_at,
                      updated_at = EXCLUDED.updated_at
                    """
                ),
                {
                    "game_id": game_id,
                    "actual_home_runs": int(home_runs),
                    "actual_away_runs": int(away_runs),
                    "final_total_runs": int(home_runs) + int(away_runs),
                    "home_team_won": bool(int(home_runs) > int(away_runs)),
                    "source": "mlb-stats-api",
                    "completed_at": _now_utc(),
                    "created_at": _now_utc(),
                    "updated_at": _now_utc(),
                },
            )
            upserted += 1
        session.commit()
        return {"outcomes_upserted": upserted, "schedule_rows": len(schedule)}
    except Exception:
        session.rollback()
        log.exception("Failed to pull MLB outcomes")
        raise
    finally:
        session.close()


@celery_app.task(name="src.tasks.pull_mlb_data_lake_snapshot")
def pull_mlb_data_lake_snapshot(
    *,
    days_back: int = 45,
    days_ahead: int = 7,
    season: Optional[int] = None,
    include_rosters: bool = True,
    include_game_feeds: bool = True,
) -> Dict[str, Any]:
    today = date.today()
    start = today - timedelta(days=max(1, int(days_back)))
    end = today + timedelta(days=max(0, int(days_ahead)))
    target_season = int(season or today.year)
    schedule = fetch_mlb_schedule(start, end)

    session = SessionLocal()
    raw_objects = 0
    team_rows = 0
    player_rows = 0
    roster_rows = 0
    game_feed_rows = 0
    team_ids: set[int] = set()
    try:
        for game in schedule:
            game_pk = str(game.get("external_game_id") or "")
            game_day = _parse_iso_datetime(game.get("game_time") or "") or datetime.now(timezone.utc)
            as_of = game_day.date()
            _upsert_mlb_raw_data_object(
                session,
                source="mlb-stats-api",
                object_type="schedule_game",
                object_key=game_pk or f"{game.get('home_team')}::{game.get('away_team')}::{as_of.isoformat()}",
                as_of_date=as_of,
                payload=game,
                fetched_at=_now_utc(),
            )
            raw_objects += 1
            if isinstance(game.get("home_team_id"), int):
                team_ids.add(int(game["home_team_id"]))
            if isinstance(game.get("away_team_id"), int):
                team_ids.add(int(game["away_team_id"]))

            if include_game_feeds and game_pk:
                try:
                    r = requests.get(
                        f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live",
                        timeout=20,
                    )
                    r.raise_for_status()
                    feed_payload = r.json() or {}
                    _upsert_mlb_raw_data_object(
                        session,
                        source="mlb-stats-api",
                        object_type="game_feed_live",
                        object_key=game_pk,
                        as_of_date=as_of,
                        payload=feed_payload,
                        fetched_at=_now_utc(),
                    )
                    raw_objects += 1
                    game_feed_rows += 1
                    teams = (((feed_payload.get("liveData") or {}).get("boxscore") or {}).get("teams") or {})
                    for side in ("home", "away"):
                        players = ((teams.get(side) or {}).get("players") or {})
                        team_id = ((teams.get(side) or {}).get("team") or {}).get("id")
                        for p in players.values():
                            person = p.get("person") or {}
                            player_id = person.get("id")
                            if player_id is None:
                                continue
                            season_batting = ((p.get("seasonStats") or {}).get("batting") or {})
                            season_pitching = ((p.get("seasonStats") or {}).get("pitching") or {})
                            season_fielding = ((p.get("seasonStats") or {}).get("fielding") or {})
                            season_payload = {
                                "batting": season_batting,
                                "pitching": season_pitching,
                                "fielding": season_fielding,
                                "position": (p.get("position") or {}).get("abbreviation"),
                                "status": p.get("status"),
                            }
                            session.execute(
                                text(
                                    """
                                    INSERT INTO mlb_player_daily_stats (
                                      as_of_date, season, player_id, player_name, team_id, stat_group, split_key, metrics, source, created_at, updated_at
                                    ) VALUES (
                                      :as_of_date, :season, :player_id, :player_name, :team_id, :stat_group, :split_key, CAST(:metrics AS jsonb), :source, :created_at, :updated_at
                                    )
                                    ON CONFLICT (as_of_date, season, player_id, stat_group, split_key) DO UPDATE SET
                                      player_name = EXCLUDED.player_name,
                                      team_id = EXCLUDED.team_id,
                                      metrics = EXCLUDED.metrics,
                                      source = EXCLUDED.source,
                                      updated_at = EXCLUDED.updated_at
                                    """
                                ),
                                {
                                    "as_of_date": as_of,
                                    "season": target_season,
                                    "player_id": int(player_id),
                                    "player_name": person.get("fullName"),
                                    "team_id": int(team_id) if team_id is not None else None,
                                    "stat_group": "season",
                                    "split_key": "all",
                                    "metrics": json.dumps(season_payload),
                                    "source": "mlb-stats-api",
                                    "created_at": _now_utc(),
                                    "updated_at": _now_utc(),
                                },
                            )
                            player_rows += 1
                except Exception:
                    log.exception("Failed to ingest live game feed for game_pk=%s", game_pk)

        standings = fetch_mlb_standings(target_season)
        for standing in standings:
            team_id = int(standing["team_id"])
            team_ids.add(team_id)
            _upsert_mlb_raw_data_object(
                session,
                source="mlb-stats-api",
                object_type="standings_team",
                object_key=f"{target_season}:{team_id}",
                as_of_date=today,
                payload=standing,
                fetched_at=_now_utc(),
            )
            raw_objects += 1

        for team_id in sorted(team_ids):
            season_profile = fetch_team_hitting_profile(team_id, season=target_season)
            split_vs_l = fetch_team_hitting_profile(team_id, season=target_season, sit_code="vl")
            split_vs_r = fetch_team_hitting_profile(team_id, season=target_season, sit_code="vr")
            recent_start = today - timedelta(days=30)
            recent_profile = fetch_team_hitting_profile(
                team_id,
                season=target_season,
                start_date=recent_start,
                end_date=today,
            )
            team_payload = {
                "season_profile": season_profile,
                "split_vs_l": split_vs_l,
                "split_vs_r": split_vs_r,
                "recent_30d": recent_profile,
            }
            _upsert_mlb_raw_data_object(
                session,
                source="mlb-stats-api",
                object_type="team_hitting_profile",
                object_key=f"{target_season}:{team_id}",
                as_of_date=today,
                payload=team_payload,
                fetched_at=_now_utc(),
            )
            raw_objects += 1
            session.execute(
                text(
                    """
                    INSERT INTO mlb_team_daily_stats (
                      as_of_date, season, team_id, team_name,
                      offense_index, offense_split_vs_l, offense_split_vs_r,
                      recent_form_index, wins, losses, run_diff,
                      source, created_at, updated_at
                    ) VALUES (
                      :as_of_date, :season, :team_id, :team_name,
                      :offense_index, :offense_split_vs_l, :offense_split_vs_r,
                      :recent_form_index, :wins, :losses, :run_diff,
                      :source, :created_at, :updated_at
                    )
                    ON CONFLICT (as_of_date, season, team_id) DO UPDATE SET
                      team_name = EXCLUDED.team_name,
                      offense_index = EXCLUDED.offense_index,
                      offense_split_vs_l = EXCLUDED.offense_split_vs_l,
                      offense_split_vs_r = EXCLUDED.offense_split_vs_r,
                      recent_form_index = EXCLUDED.recent_form_index,
                      wins = EXCLUDED.wins,
                      losses = EXCLUDED.losses,
                      run_diff = EXCLUDED.run_diff,
                      source = EXCLUDED.source,
                      updated_at = EXCLUDED.updated_at
                    """
                ),
                {
                    "as_of_date": today,
                    "season": target_season,
                    "team_id": team_id,
                    "team_name": None,
                    "offense_index": _safe_float(season_profile.get("ops_index")) or 1.0,
                    "offense_split_vs_l": _safe_float(split_vs_l.get("ops_index")) or 1.0,
                    "offense_split_vs_r": _safe_float(split_vs_r.get("ops_index")) or 1.0,
                    "recent_form_index": _safe_float(recent_profile.get("ops_index")) or 1.0,
                    "wins": None,
                    "losses": None,
                    "run_diff": None,
                    "source": "mlb-stats-api",
                    "created_at": _now_utc(),
                    "updated_at": _now_utc(),
                },
            )
            team_rows += 1

            if include_rosters:
                try:
                    roster = fetch_team_roster(team_id, target_season)
                except Exception:
                    roster = []
                for row in roster:
                    _upsert_mlb_raw_data_object(
                        session,
                        source="mlb-stats-api",
                        object_type="team_roster_player",
                        object_key=f"{target_season}:{team_id}:{row['player_id']}",
                        as_of_date=today,
                        payload=row,
                        fetched_at=_now_utc(),
                    )
                    raw_objects += 1
                    session.execute(
                        text(
                            """
                            INSERT INTO mlb_player_daily_stats (
                              as_of_date, season, player_id, player_name, team_id, stat_group, split_key, metrics, source, created_at, updated_at
                            ) VALUES (
                              :as_of_date, :season, :player_id, :player_name, :team_id, :stat_group, :split_key, CAST(:metrics AS jsonb), :source, :created_at, :updated_at
                            )
                            ON CONFLICT (as_of_date, season, player_id, stat_group, split_key) DO UPDATE SET
                              player_name = EXCLUDED.player_name,
                              team_id = EXCLUDED.team_id,
                              metrics = EXCLUDED.metrics,
                              source = EXCLUDED.source,
                              updated_at = EXCLUDED.updated_at
                            """
                        ),
                        {
                            "as_of_date": today,
                            "season": target_season,
                            "player_id": int(row["player_id"]),
                            "player_name": row.get("player_name"),
                            "team_id": int(row["team_id"]),
                            "stat_group": "roster",
                            "split_key": row.get("position_abbr") or "NA",
                            "metrics": json.dumps(row),
                            "source": "mlb-stats-api",
                            "created_at": _now_utc(),
                            "updated_at": _now_utc(),
                        },
                    )
                    roster_rows += 1

        summary = {
            "season": target_season,
            "date_window": {"start": start.isoformat(), "end": end.isoformat()},
            "scheduled_games_fetched": len(schedule),
            "team_count": len(team_ids),
            "raw_objects_upserted": raw_objects,
            "team_rows_upserted": team_rows,
            "player_rows_upserted": player_rows,
            "roster_rows_upserted": roster_rows,
            "game_feeds_ingested": game_feed_rows,
        }
        _persist_snapshot(
            session,
            run_date=today,
            model_version=DEFAULT_MODEL_VERSION,
            pipeline_stage="data_lake_snapshot",
            payload=summary,
        )
        session.commit()
        return summary
    except Exception:
        session.rollback()
        log.exception("Failed pulling MLB data lake snapshot")
        raise
    finally:
        session.close()


@celery_app.task(name="src.tasks.evaluate_mlb_model_promotion")
def evaluate_mlb_model_promotion(
    *,
    base_model_version: str = DEFAULT_MODEL_VERSION,
    challenger_model_version: str = "mlb-v2-pitch-sim",
    lookback_days: int = 45,
    auto_promote: bool = True,
) -> Dict[str, Any]:
    session = SessionLocal()
    run_date = date.today()
    try:
        holdout_bucket_count = int(os.getenv("MLB_PROMOTION_HOLDOUT_BUCKETS", "3"))
        base_points = _fetch_calibration_points(
            session,
            model_version=base_model_version,
            lookback_days=lookback_days,
        )
        challenger_points = _fetch_calibration_points(
            session,
            model_version=challenger_model_version,
            lookback_days=lookback_days,
        )
        base_quality = {
            **_compute_calibration_summary(base_points),
            **_compute_clv_summary(
                session,
                model_version=base_model_version,
                lookback_days=lookback_days,
            ),
        }
        challenger_quality = {
            **_compute_calibration_summary(challenger_points),
            **_compute_clv_summary(
                session,
                model_version=challenger_model_version,
                lookback_days=lookback_days,
            ),
        }
        holdout_profile = _compute_holdout_profile(
            base_points=base_points,
            challenger_points=challenger_points,
            bucket_count=holdout_bucket_count,
        )
        decision = _decide_challenger_promotion(
            base_quality=base_quality,
            challenger_quality=challenger_quality,
            holdout_profile=holdout_profile,
        )
        auto_enabled = auto_promote and _env_bool("MLB_AUTO_PROMOTE_ENABLED", False)
        promoted = False
        state_change: Dict[str, Any] = {}
        if decision["promote"] and auto_enabled:
            state_change = _set_active_model(
                session,
                model_version=challenger_model_version,
                reason=f"auto-promotion lookback={lookback_days}",
            )
            promoted = True

        payload = {
            "base_model_version": base_model_version,
            "challenger_model_version": challenger_model_version,
            "lookback_days": lookback_days,
            "base_quality": base_quality,
            "challenger_quality": challenger_quality,
            "holdout_profile": holdout_profile,
            "decision": decision,
            "auto_promote_requested": auto_promote,
            "auto_promote_enabled": auto_enabled,
            "promoted": promoted,
            "state_change": state_change,
        }

        _persist_holdout_profile(
            session,
            run_date=run_date,
            base_model_version=base_model_version,
            challenger_model_version=challenger_model_version,
            lookback_days=lookback_days,
            holdout_profile=holdout_profile,
        )

        _persist_snapshot(
            session,
            run_date=run_date,
            model_version=challenger_model_version,
            pipeline_stage="promotion_decision",
            payload=payload,
        )

        severity = "info"
        alert_type = "mlb.promotion.skipped"
        if promoted:
            severity = "warning"
            alert_type = "mlb.promotion.promoted"
        elif not decision["promote"] and "sample_size_ok" in (decision.get("checks") or {}) and not decision["checks"]["sample_size_ok"]:
            severity = "info"
            alert_type = "mlb.promotion.insufficient_sample"
        elif not decision["promote"] and "holdout_sample_ok" in (decision.get("checks") or {}) and not decision["checks"]["holdout_sample_ok"]:
            severity = "info"
            alert_type = "mlb.promotion.insufficient_holdout"
        elif not decision["promote"]:
            severity = "warning"
            alert_type = "mlb.promotion.underperformed"

        _persist_alert_event(
            session,
            alert_type=alert_type,
            severity=severity,
            payload=payload,
        )
        webhook_sent = _send_alert_webhook(
            alert_type=alert_type,
            severity=severity,
            payload=payload,
        )
        payload["webhook_sent"] = webhook_sent
        session.commit()
        return payload
    except Exception:
        session.rollback()
        log.exception("Failed evaluating MLB model promotion")
        raise
    finally:
        session.close()


@celery_app.task(name="src.tasks.run_mlb_lineup_nowcast_repricing")
def run_mlb_lineup_nowcast_repricing(
    *,
    horizon_hours: int = 18,
    simulations: int = 3000,
    base_model_version: str = DEFAULT_MODEL_VERSION,
    challenger_model_version: str = "mlb-v2-pitch-sim",
    run_challenger: bool = True,
) -> Dict[str, Any]:
    now = _now_utc()
    max_hours = max(1, min(48, int(horizon_hours)))
    end_ts = now + timedelta(hours=max_hours)

    session = SessionLocal()
    updated_context = 0
    repriced_base = 0
    repriced_challenger = 0
    seen_games = 0
    nowcast_conf_sum = 0.0
    prev_conf_sum = 0.0
    confidence_delta_sum = 0.0
    prev_conf_count = 0
    freshness_sum = 0.0
    confirmed_count = 0
    try:
        rows = session.execute(
            text(
                """
                SELECT
                  g.id AS game_id,
                                    g.external_id,
                  g.start_time,
                  g.status AS game_status,
                  home.name AS home_team,
                  away.name AS away_team,
                  c.probable_pitcher_home,
                  c.probable_pitcher_away,
                  c.umpire_home_plate,
                  c.lineup_confirmed,
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
                  c.umpire_run_factor,
                  c.updated_at AS context_updated_at
                FROM games g
                JOIN seasons s ON s.id = g.season_id
                JOIN leagues l ON l.id = s.league_id
                JOIN teams home ON home.id = g.home_team_id
                JOIN teams away ON away.id = g.away_team_id
                LEFT JOIN mlb_game_context c ON c.game_id = g.id
                WHERE l.code = 'mlb'
                  AND g.start_time >= :now_ts
                  AND g.start_time <= :end_ts
                  AND LOWER(COALESCE(g.status, 'scheduled')) IN ('scheduled', 'pre-game', 'pregame')
                ORDER BY g.start_time
                """
            ),
            {"now_ts": now, "end_ts": end_ts},
        ).fetchall()

        for r in rows:
            m = dict(r._mapping)
            seen_games += 1
            try:
                live_lineups = fetch_game_lineup_features(str(m.get("external_id"))) if m.get("external_id") else {"home": {}, "away": {}}
            except Exception:
                live_lineups = {"home": {}, "away": {}}
            live_home_lineup = live_lineups.get("home") or {}
            live_away_lineup = live_lineups.get("away") or {}
            lineup_confirmed = (
                bool(m["lineup_confirmed"]) if m.get("lineup_confirmed") is not None else False
            ) or bool(live_home_lineup.get("lineup_confirmed")) or bool(live_away_lineup.get("lineup_confirmed"))
            freshness = _info_freshness_score(
                updated_at=m.get("context_updated_at"),
                lineup_confirmed=lineup_confirmed,
            )
            hours_to_pitch = _hours_to_game(m.get("start_time"))
            nowcast = _lineup_nowcast_confidence(
                hours_to_first_pitch=hours_to_pitch,
                lineup_confirmed=lineup_confirmed,
                probable_pitcher_home=m.get("probable_pitcher_home"),
                probable_pitcher_away=m.get("probable_pitcher_away"),
                freshness_score=freshness,
            )
            prev_home = float(m["lineup_confidence_home"]) if m.get("lineup_confidence_home") is not None else None
            prev_away = float(m["lineup_confidence_away"]) if m.get("lineup_confidence_away") is not None else None
            prev_avg = (
                ((prev_home or 0.0) + (prev_away or 0.0)) / 2.0
                if (prev_home is not None or prev_away is not None)
                else None
            )
            next_avg = (nowcast["home"] + nowcast["away"]) / 2.0
            nowcast_conf_sum += next_avg
            freshness_sum += freshness
            if lineup_confirmed:
                confirmed_count += 1
            if prev_avg is not None:
                prev_conf_sum += prev_avg
                confidence_delta_sum += abs(next_avg - prev_avg)
                prev_conf_count += 1
            lineup_strength_home = float(m["lineup_strength_index_home"]) if m.get("lineup_strength_index_home") is not None else 1.0
            lineup_strength_away = float(m["lineup_strength_index_away"]) if m.get("lineup_strength_index_away") is not None else 1.0
            if live_home_lineup.get("lineup_strength_index") is not None:
                lineup_strength_home = float(live_home_lineup["lineup_strength_index"])
            if live_away_lineup.get("lineup_strength_index") is not None:
                lineup_strength_away = float(live_away_lineup["lineup_strength_index"])
            # Update context with nowcast confidence as live pre-lock estimate.
            session.execute(
                text(
                    """
                    UPDATE mlb_game_context
                    SET
                      lineup_confidence_home = :lineup_confidence_home,
                      lineup_confidence_away = :lineup_confidence_away,
                      lineup_strength_index_home = :lineup_strength_index_home,
                      lineup_strength_index_away = :lineup_strength_index_away,
                      lineup_confirmed = :lineup_confirmed,
                      context = COALESCE(context, '{}'::jsonb) || CAST(:context_patch AS jsonb),
                      updated_at = :updated_at
                    WHERE game_id = :game_id
                    """
                ),
                {
                    "game_id": m["game_id"],
                    "lineup_confidence_home": nowcast["home"],
                    "lineup_confidence_away": nowcast["away"],
                    "lineup_strength_index_home": lineup_strength_home,
                    "lineup_strength_index_away": lineup_strength_away,
                    "lineup_confirmed": lineup_confirmed,
                    "context_patch": json.dumps(
                        {
                            "lineup_nowcast": {
                                "hours_to_first_pitch": round(hours_to_pitch, 3),
                                "lineup_confirmed": lineup_confirmed,
                                "freshness_score": round(freshness, 4),
                                "confidence_home": round(nowcast["home"], 4),
                                "confidence_away": round(nowcast["away"], 4),
                                "lineup_strength_home": round(lineup_strength_home, 4),
                                "lineup_strength_away": round(lineup_strength_away, 4),
                                "home_lineup_players": live_home_lineup.get("players") or [],
                                "away_lineup_players": live_away_lineup.get("players") or [],
                                "generated_at": _now_utc().isoformat(),
                            }
                        }
                    ),
                    "updated_at": _now_utc(),
                },
            )
            updated_context += 1

            starter_home_feat = starter_identity_features(m.get("probable_pitcher_home"))
            starter_away_feat = starter_identity_features(m.get("probable_pitcher_away"))
            inputs = MlbGameInputs(
                game_id=str(m["game_id"]),
                home_team=str(m["home_team"]),
                away_team=str(m["away_team"]),
                starter_home=m.get("probable_pitcher_home"),
                starter_away=m.get("probable_pitcher_away"),
                starter_quality_home=float(starter_home_feat.get("starter_quality") or 1.0),
                starter_quality_away=float(starter_away_feat.get("starter_quality") or 1.0),
                starter_k_factor_home=float(starter_home_feat.get("k_factor") or 1.0),
                starter_k_factor_away=float(starter_away_feat.get("k_factor") or 1.0),
                starter_bb_factor_home=float(starter_home_feat.get("bb_factor") or 1.0),
                starter_bb_factor_away=float(starter_away_feat.get("bb_factor") or 1.0),
                starter_gb_factor_home=float(starter_home_feat.get("gb_factor") or 1.0),
                starter_gb_factor_away=float(starter_away_feat.get("gb_factor") or 1.0),
                umpire_home_plate=m.get("umpire_home_plate"),
                lineup_confirmed=lineup_confirmed,
                weather_temp_f=float(m["weather_temp_f"]) if m.get("weather_temp_f") is not None else None,
                weather_wind_mph=float(m["weather_wind_mph"]) if m.get("weather_wind_mph") is not None else None,
                weather_wind_dir_deg=float(m["weather_wind_dir_deg"]) if m.get("weather_wind_dir_deg") is not None else None,
                weather_humidity_pct=float(m["weather_humidity_pct"]) if m.get("weather_humidity_pct") is not None else None,
                park_factor_runs=float(m["park_factor_runs"]) if m.get("park_factor_runs") is not None else None,
                offense_home=float(m["offense_index_home"]) if m.get("offense_index_home") is not None else 1.0,
                offense_away=float(m["offense_index_away"]) if m.get("offense_index_away") is not None else 1.0,
                offense_split_home=float(m["offense_split_index_home"]) if m.get("offense_split_index_home") is not None else 1.0,
                offense_split_away=float(m["offense_split_index_away"]) if m.get("offense_split_index_away") is not None else 1.0,
                recent_form_index_home=float(m["recent_form_index_home"]) if m.get("recent_form_index_home") is not None else 1.0,
                recent_form_index_away=float(m["recent_form_index_away"]) if m.get("recent_form_index_away") is not None else 1.0,
                lineup_strength_index_home=lineup_strength_home,
                lineup_strength_index_away=lineup_strength_away,
                lineup_confidence_home=nowcast["home"],
                lineup_confidence_away=nowcast["away"],
                bullpen_fatigue_home=float(m["bullpen_fatigue_home"]) if m.get("bullpen_fatigue_home") is not None else 0.5,
                bullpen_fatigue_away=float(m["bullpen_fatigue_away"]) if m.get("bullpen_fatigue_away") is not None else 0.5,
                bullpen_ip_last3_home=float(m["bullpen_ip_last3_home"]) if m.get("bullpen_ip_last3_home") is not None else 9.0,
                bullpen_ip_last3_away=float(m["bullpen_ip_last3_away"]) if m.get("bullpen_ip_last3_away") is not None else 9.0,
                bullpen_availability_home=float(m["bullpen_availability_home"]) if m.get("bullpen_availability_home") is not None else 0.65,
                bullpen_availability_away=float(m["bullpen_availability_away"]) if m.get("bullpen_availability_away") is not None else 0.65,
                bullpen_high_lev_availability_home=float(m["bullpen_high_leverage_availability_home"]) if m.get("bullpen_high_leverage_availability_home") is not None else 0.62,
                bullpen_high_lev_availability_away=float(m["bullpen_high_leverage_availability_away"]) if m.get("bullpen_high_leverage_availability_away") is not None else 0.62,
                umpire_run_factor=float(m["umpire_run_factor"]) if m.get("umpire_run_factor") is not None else 1.0,
                info_freshness_score_home=freshness,
                info_freshness_score_away=freshness,
            )

            seed_base = _default_projection_seed(inputs.game_id, base_model_version, simulations)
            projection_base = _run_simulation_by_model(
                inputs,
                simulations=simulations,
                seed=seed_base,
                model_version=base_model_version,
            )
            _insert_mlb_projection_and_audit(session, projection_base, seed=seed_base)
            repriced_base += 1

            if run_challenger:
                seed_ch = _default_projection_seed(inputs.game_id, challenger_model_version, simulations)
                projection_ch = _run_simulation_by_model(
                    inputs,
                    simulations=simulations,
                    seed=seed_ch,
                    model_version=challenger_model_version,
                )
                _insert_mlb_projection_and_audit(session, projection_ch, seed=seed_ch)
                repriced_challenger += 1

        summary = {
            "horizon_hours": max_hours,
            "games_seen": seen_games,
            "context_rows_updated": updated_context,
            "repriced_base": repriced_base,
            "repriced_challenger": repriced_challenger,
            "base_model_version": base_model_version,
            "challenger_model_version": challenger_model_version if run_challenger else None,
            "avg_nowcast_confidence": round(nowcast_conf_sum / max(1, updated_context), 4),
            "avg_prev_confidence": round(prev_conf_sum / max(1, prev_conf_count), 4) if prev_conf_count > 0 else None,
            "avg_confidence_delta": round(confidence_delta_sum / max(1, prev_conf_count), 4) if prev_conf_count > 0 else None,
            "avg_freshness_score": round(freshness_sum / max(1, updated_context), 4),
            "lineup_confirmed_share": round(confirmed_count / max(1, updated_context), 4),
        }
        _persist_snapshot(
            session,
            run_date=date.today(),
            model_version=base_model_version,
            pipeline_stage="lineup_nowcast_repricing",
            payload=summary,
        )
        session.commit()
        return summary
    except Exception:
        session.rollback()
        log.exception("Failed running MLB lineup nowcast repricing")
        raise
    finally:
        session.close()


@celery_app.task(name="src.tasks.run_mlb_walkforward_backtest")
def run_mlb_walkforward_backtest(
    *,
    model_version: str = DEFAULT_MODEL_VERSION,
    lookback_days: int = 180,
    training_days: int = 45,
    step_days: int = 7,
    apply_calibration: bool = True,
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        points = _fetch_calibration_points(
            session,
            model_version=model_version,
            lookback_days=lookback_days,
        )
        leakage_violations = _count_leakage_violations(points)
        result = _walkforward_backtest(
            points=points,
            training_days=training_days,
            step_days=step_days,
            apply_calibration=apply_calibration,
        )
        payload = {
            "model_version": model_version,
            "lookback_days": lookback_days,
            "training_days": training_days,
            "step_days": step_days,
            "apply_calibration": apply_calibration,
            "leakage_violations": leakage_violations,
            **result,
        }
        _persist_snapshot(
            session,
            run_date=date.today(),
            model_version=model_version,
            pipeline_stage="walkforward_backtest",
            payload=payload,
        )
        severity = "warning" if leakage_violations > 0 else "info"
        _persist_alert_event(
            session,
            alert_type="mlb.backtest.completed",
            severity=severity,
            payload=payload,
        )
        session.commit()
        return payload
    except Exception:
        session.rollback()
        log.exception("Failed running MLB walk-forward backtest")
        raise
    finally:
        session.close()


def _ablated_inputs(inputs: MlbGameInputs, feature: str) -> MlbGameInputs:
    update_map: Dict[str, Any] = {}
    if feature == "weather":
        update_map = {
            "weather_temp_f": None,
            "weather_wind_mph": None,
            "weather_wind_dir_deg": None,
            "weather_humidity_pct": None,
        }
    elif feature == "bullpen":
        update_map = {
            "bullpen_fatigue_home": 0.5,
            "bullpen_fatigue_away": 0.5,
            "bullpen_availability_home": 0.65,
            "bullpen_availability_away": 0.65,
            "bullpen_high_lev_availability_home": 0.62,
            "bullpen_high_lev_availability_away": 0.62,
        }
    elif feature == "starter_identity":
        update_map = {
            "starter_quality_home": 1.0,
            "starter_quality_away": 1.0,
            "starter_k_factor_home": 1.0,
            "starter_k_factor_away": 1.0,
            "starter_bb_factor_home": 1.0,
            "starter_bb_factor_away": 1.0,
            "starter_gb_factor_home": 1.0,
            "starter_gb_factor_away": 1.0,
        }
    elif feature == "lineup_strength":
        update_map = {
            "lineup_strength_index_home": 1.0,
            "lineup_strength_index_away": 1.0,
            "offense_split_home": 1.0,
            "offense_split_away": 1.0,
        }
    elif feature == "freshness":
        update_map = {
            "info_freshness_score_home": 1.0,
            "info_freshness_score_away": 1.0,
            "lineup_confidence_home": max(0.85, float(inputs.lineup_confidence_home)),
            "lineup_confidence_away": max(0.85, float(inputs.lineup_confidence_away)),
        }
    return inputs.model_copy(update=update_map)


@celery_app.task(name="src.tasks.run_mlb_feature_ablation")
def run_mlb_feature_ablation(
    *,
    game_date: Optional[str] = None,
    model_version: str = DEFAULT_MODEL_VERSION,
    simulations: int = 2000,
) -> Dict[str, Any]:
    base = run_mlb_market_simulations(game_date=game_date, simulations=simulations, model_version=model_version)
    if game_date:
        target_date = date.fromisoformat(game_date)
    else:
        target_date = date.today()
    session = SessionLocal()
    try:
        rows = session.execute(
            text(
                """
                SELECT
                  g.id AS game_id,
                  home.name AS home_team,
                  away.name AS away_team,
                  c.probable_pitcher_home,
                  c.probable_pitcher_away,
                  c.umpire_home_plate,
                  c.lineup_confirmed,
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
                  c.umpire_run_factor
                FROM games g
                JOIN seasons s ON s.id = g.season_id
                JOIN leagues l ON l.id = s.league_id
                JOIN teams home ON home.id = g.home_team_id
                JOIN teams away ON away.id = g.away_team_id
                LEFT JOIN mlb_game_context c ON c.game_id = g.id
                WHERE l.code = 'mlb'
                  AND g.game_date = :game_date
                ORDER BY g.start_time
                LIMIT 24
                """
            ),
            {"game_date": target_date},
        ).fetchall()
        features = ["weather", "bullpen", "starter_identity", "lineup_strength", "freshness"]
        impacts = {f: {"delta_prob_sum": 0.0, "delta_total_sum": 0.0, "count": 0} for f in features}
        for r in rows:
            m = dict(r._mapping)
            starter_home_feat = starter_identity_features(m.get("probable_pitcher_home"))
            starter_away_feat = starter_identity_features(m.get("probable_pitcher_away"))
            freshness = _info_freshness_score(
                updated_at=m.get("context_updated_at"),
                lineup_confirmed=bool(m["lineup_confirmed"]) if m.get("lineup_confirmed") is not None else False,
            )
            inputs = MlbGameInputs(
                game_id=str(m["game_id"]),
                home_team=str(m["home_team"]),
                away_team=str(m["away_team"]),
                starter_home=m.get("probable_pitcher_home"),
                starter_away=m.get("probable_pitcher_away"),
                starter_quality_home=float(starter_home_feat.get("starter_quality") or 1.0),
                starter_quality_away=float(starter_away_feat.get("starter_quality") or 1.0),
                starter_k_factor_home=float(starter_home_feat.get("k_factor") or 1.0),
                starter_k_factor_away=float(starter_away_feat.get("k_factor") or 1.0),
                starter_bb_factor_home=float(starter_home_feat.get("bb_factor") or 1.0),
                starter_bb_factor_away=float(starter_away_feat.get("bb_factor") or 1.0),
                starter_gb_factor_home=float(starter_home_feat.get("gb_factor") or 1.0),
                starter_gb_factor_away=float(starter_away_feat.get("gb_factor") or 1.0),
                umpire_home_plate=m.get("umpire_home_plate"),
                lineup_confirmed=bool(m["lineup_confirmed"]) if m.get("lineup_confirmed") is not None else False,
                weather_temp_f=float(m["weather_temp_f"]) if m.get("weather_temp_f") is not None else None,
                weather_wind_mph=float(m["weather_wind_mph"]) if m.get("weather_wind_mph") is not None else None,
                weather_wind_dir_deg=float(m["weather_wind_dir_deg"]) if m.get("weather_wind_dir_deg") is not None else None,
                weather_humidity_pct=float(m["weather_humidity_pct"]) if m.get("weather_humidity_pct") is not None else None,
                park_factor_runs=float(m["park_factor_runs"]) if m.get("park_factor_runs") is not None else None,
                offense_home=float(m["offense_index_home"]) if m.get("offense_index_home") is not None else 1.0,
                offense_away=float(m["offense_index_away"]) if m.get("offense_index_away") is not None else 1.0,
                offense_split_home=float(m["offense_split_index_home"]) if m.get("offense_split_index_home") is not None else 1.0,
                offense_split_away=float(m["offense_split_index_away"]) if m.get("offense_split_index_away") is not None else 1.0,
                recent_form_index_home=float(m["recent_form_index_home"]) if m.get("recent_form_index_home") is not None else 1.0,
                recent_form_index_away=float(m["recent_form_index_away"]) if m.get("recent_form_index_away") is not None else 1.0,
                lineup_strength_index_home=float(m["lineup_strength_index_home"]) if m.get("lineup_strength_index_home") is not None else 1.0,
                lineup_strength_index_away=float(m["lineup_strength_index_away"]) if m.get("lineup_strength_index_away") is not None else 1.0,
                lineup_confidence_home=float(m["lineup_confidence_home"]) if m.get("lineup_confidence_home") is not None else 0.85,
                lineup_confidence_away=float(m["lineup_confidence_away"]) if m.get("lineup_confidence_away") is not None else 0.85,
                bullpen_fatigue_home=float(m["bullpen_fatigue_home"]) if m.get("bullpen_fatigue_home") is not None else 0.5,
                bullpen_fatigue_away=float(m["bullpen_fatigue_away"]) if m.get("bullpen_fatigue_away") is not None else 0.5,
                bullpen_ip_last3_home=float(m["bullpen_ip_last3_home"]) if m.get("bullpen_ip_last3_home") is not None else 9.0,
                bullpen_ip_last3_away=float(m["bullpen_ip_last3_away"]) if m.get("bullpen_ip_last3_away") is not None else 9.0,
                bullpen_availability_home=float(m["bullpen_availability_home"]) if m.get("bullpen_availability_home") is not None else 0.65,
                bullpen_availability_away=float(m["bullpen_availability_away"]) if m.get("bullpen_availability_away") is not None else 0.65,
                bullpen_high_lev_availability_home=float(m["bullpen_high_leverage_availability_home"]) if m.get("bullpen_high_leverage_availability_home") is not None else 0.62,
                bullpen_high_lev_availability_away=float(m["bullpen_high_leverage_availability_away"]) if m.get("bullpen_high_leverage_availability_away") is not None else 0.62,
                umpire_run_factor=float(m["umpire_run_factor"]) if m.get("umpire_run_factor") is not None else 1.0,
                info_freshness_score_home=freshness,
                info_freshness_score_away=freshness,
            )
            seed = _default_projection_seed(inputs.game_id, model_version, simulations)
            base_proj = _run_simulation_by_model(
                inputs,
                simulations=simulations,
                seed=seed,
                model_version=model_version,
            )
            base_prob = float((base_proj.get("markets") or {}).get("fg_home_win_prob") or 0.5)
            base_total = float((base_proj.get("markets") or {}).get("fg_total_mean") or 9.0)
            for feature in features:
                ablated = _ablated_inputs(inputs, feature)
                ablated_seed = _default_projection_seed(inputs.game_id, f"{model_version}:{feature}", simulations)
                ablated_proj = _run_simulation_by_model(
                    ablated,
                    simulations=simulations,
                    seed=ablated_seed,
                    model_version=model_version,
                )
                ablated_prob = float((ablated_proj.get("markets") or {}).get("fg_home_win_prob") or 0.5)
                ablated_total = float((ablated_proj.get("markets") or {}).get("fg_total_mean") or 9.0)
                impacts[feature]["delta_prob_sum"] += abs(base_prob - ablated_prob)
                impacts[feature]["delta_total_sum"] += abs(base_total - ablated_total)
                impacts[feature]["count"] += 1

        feature_impacts: List[Dict[str, Any]] = []
        for feature, v in impacts.items():
            n = max(1, int(v["count"]))
            feature_impacts.append(
                {
                    "feature": feature,
                    "sample_size": int(v["count"]),
                    "avg_abs_delta_fg_home_win_prob": round(float(v["delta_prob_sum"]) / n, 5),
                    "avg_abs_delta_fg_total_mean": round(float(v["delta_total_sum"]) / n, 4),
                }
            )
        feature_impacts = sorted(
            feature_impacts,
            key=lambda x: float(x["avg_abs_delta_fg_home_win_prob"]) + float(x["avg_abs_delta_fg_total_mean"]) / 10.0,
            reverse=True,
        )
        payload = {
            "model_version": model_version,
            "game_date": target_date.isoformat(),
            "simulations": simulations,
            "base_run": base,
            "feature_impacts": feature_impacts,
        }
        _persist_snapshot(
            session,
            run_date=target_date,
            model_version=model_version,
            pipeline_stage="feature_ablation",
            payload=payload,
        )
        session.commit()
        return payload
    except Exception:
        session.rollback()
        log.exception("Failed MLB feature ablation task")
        raise
    finally:
        session.close()


@celery_app.task(name="src.tasks.run_mlb_determinism_check")
def run_mlb_determinism_check(
    *,
    model_version: str = DEFAULT_MODEL_VERSION,
    simulations: int = 800,
    game_date: Optional[str] = None,
) -> Dict[str, Any]:
    sim_result = run_mlb_market_simulations(game_date=game_date, simulations=max(500, simulations), model_version=model_version)
    payload = {
        "model_version": model_version,
        "simulations": simulations,
        "game_date": game_date or date.today().isoformat(),
        "simulation_run": sim_result,
        "deterministic": True,
        "checked": 0,
    }
    session = SessionLocal()
    try:
        points = _fetch_calibration_points(
            session,
            model_version=model_version,
            lookback_days=30,
        )
        # Deterministic seed contract should always hold for helper.
        if points:
            gid = str(points[0].get("game_id"))
            s1 = _default_projection_seed(gid, model_version, simulations)
            s2 = _default_projection_seed(gid, model_version, simulations)
            payload["deterministic"] = s1 == s2
            payload["checked"] = 1
        _persist_snapshot(
            session,
            run_date=date.today(),
            model_version=model_version,
            pipeline_stage="determinism_check",
            payload=payload,
        )
        if not payload["deterministic"]:
            _persist_alert_event(
                session,
                alert_type="mlb.determinism.failed",
                severity="warning",
                payload=payload,
            )
        session.commit()
        return payload
    except Exception:
        session.rollback()
        log.exception("Failed MLB determinism check")
        raise
    finally:
        session.close()


@celery_app.task(name="src.tasks.run_mlb_daily_cycle")
def run_mlb_daily_cycle(
    *,
    days_ahead: int = 5,
    outcomes_lookback_days: int = 60,
    simulations: int = 4000,
    base_model_version: str = DEFAULT_MODEL_VERSION,
    challenger_model_version: str = "mlb-v2-pitch-sim",
    run_challenger: bool = True,
    calibration_lookback_days: int = 45,
) -> Dict[str, Any]:
    run_date = date.today()
    summary: Dict[str, Any] = {"run_date": run_date.isoformat(), "stages": {}}

    if _env_bool("MLB_RUN_DAILY_DATA_LAKE", True):
        try:
            summary["stages"]["data_lake"] = pull_mlb_data_lake_snapshot(
                days_back=int(os.getenv("MLB_DATA_LAKE_DAYS_BACK", "60")),
                days_ahead=max(days_ahead, int(os.getenv("MLB_DATA_LAKE_DAYS_AHEAD", "7"))),
                season=run_date.year,
                include_rosters=_env_bool("MLB_DATA_LAKE_INCLUDE_ROSTERS", True),
                include_game_feeds=_env_bool("MLB_DATA_LAKE_INCLUDE_GAME_FEEDS", True),
            )
        except Exception as e:
            summary["stages"]["data_lake"] = {"error": str(e)}

    context_result = pull_mlb_context_snapshot(days_ahead=days_ahead)
    summary["stages"]["context"] = context_result

    base_result = run_mlb_market_simulations(
        game_date=run_date.isoformat(),
        simulations=simulations,
        model_version=base_model_version,
    )
    summary["stages"]["base_simulations"] = base_result

    challenger_result: Dict[str, Any] = {"skipped": True}
    if run_challenger:
        challenger_result = run_mlb_market_simulations(
            game_date=run_date.isoformat(),
            simulations=simulations,
            model_version=challenger_model_version,
        )
    summary["stages"]["challenger_simulations"] = challenger_result

    outcomes_result = pull_mlb_outcomes(days_back=outcomes_lookback_days)
    summary["stages"]["outcomes"] = outcomes_result

    session = SessionLocal()
    try:
        base_points = _fetch_calibration_points(
            session,
            model_version=base_model_version,
            lookback_days=calibration_lookback_days,
        )
        base_cal = _compute_calibration_summary(base_points)
        base_clv = _compute_clv_summary(
            session,
            model_version=base_model_version,
            lookback_days=calibration_lookback_days,
        )
        base_drift = _compute_reliability_drift(base_points)
        base_leakage = _count_leakage_violations(base_points)
        base_quality = {
            **base_cal,
            **base_clv,
            **base_drift,
            "leakage_violations": base_leakage,
        }
        _persist_snapshot(
            session,
            run_date=run_date,
            model_version=base_model_version,
            pipeline_stage="quality_snapshot",
            payload=base_quality,
        )
        summary["stages"]["base_quality"] = base_quality

        if run_challenger:
            ch_points = _fetch_calibration_points(
                session,
                model_version=challenger_model_version,
                lookback_days=calibration_lookback_days,
            )
            ch_cal = _compute_calibration_summary(ch_points)
            ch_clv = _compute_clv_summary(
                session,
                model_version=challenger_model_version,
                lookback_days=calibration_lookback_days,
            )
            ch_drift = _compute_reliability_drift(ch_points)
            ch_leakage = _count_leakage_violations(ch_points)
            ch_quality = {
                **ch_cal,
                **ch_clv,
                **ch_drift,
                "leakage_violations": ch_leakage,
            }
            _persist_snapshot(
                session,
                run_date=run_date,
                model_version=challenger_model_version,
                pipeline_stage="quality_snapshot",
                payload=ch_quality,
            )
            summary["stages"]["challenger_quality"] = ch_quality
        max_ece = float(os.getenv("MLB_MAX_ACCEPTABLE_ECE", "0.06"))
        for version, quality in [
            (base_model_version, base_quality),
            (challenger_model_version, summary["stages"].get("challenger_quality") if run_challenger else None),
        ]:
            if not isinstance(quality, dict):
                continue
            ece = _safe_float(quality.get("ece"))
            leakage = int(_safe_float(quality.get("leakage_violations")) or 0)
            if (ece is not None and ece > max_ece) or leakage > 0:
                _persist_alert_event(
                    session,
                    alert_type="mlb.quality.drift",
                    severity="warning",
                    payload={
                        "model_version": version,
                        "ece": ece,
                        "max_acceptable_ece": max_ece,
                        "leakage_violations": leakage,
                        "run_date": run_date.isoformat(),
                    },
                )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    if _env_bool("MLB_RUN_DAILY_BACKTEST", False):
        try:
            summary["stages"]["walkforward_backtest"] = run_mlb_walkforward_backtest(
                model_version=base_model_version,
                lookback_days=max(90, calibration_lookback_days * 4),
                training_days=max(28, calibration_lookback_days),
                step_days=7,
                apply_calibration=True,
            )
        except Exception as e:
            summary["stages"]["walkforward_backtest"] = {"error": str(e)}

    if _env_bool("MLB_RUN_DAILY_DETERMINISM_CHECK", True):
        try:
            summary["stages"]["determinism_check"] = run_mlb_determinism_check(
                model_version=base_model_version,
                simulations=800,
            )
        except Exception as e:
            summary["stages"]["determinism_check"] = {"error": str(e)}

    if _env_bool("MLB_RUN_DAILY_ABLATION", False):
        try:
            summary["stages"]["feature_ablation"] = run_mlb_feature_ablation(
                model_version=base_model_version,
                simulations=1500,
            )
        except Exception as e:
            summary["stages"]["feature_ablation"] = {"error": str(e)}

    if run_challenger:
        try:
            promotion = evaluate_mlb_model_promotion(
                base_model_version=base_model_version,
                challenger_model_version=challenger_model_version,
                lookback_days=calibration_lookback_days,
                auto_promote=True,
            )
            summary["stages"]["promotion"] = promotion
        except Exception as e:
            summary["stages"]["promotion"] = {"error": str(e)}

    return summary


def _resolve_nfl_week(session: Any, season: int, week: Optional[int]) -> int:
    if week is not None:
        return int(week)
    row = session.execute(
        text(
            """
            SELECT COALESCE(MAX(week), 1)::int AS week
            FROM nfl_dp_player_usage_weekly
            WHERE season = :season
            """
        ),
        {"season": int(season)},
    ).fetchone()
    if row is None:
        return 1
    return int(row[0] or 1)


def _to_uuid_or_none(value: Any) -> Any:
    if value is None:
        return None
    try:
        return uuid.UUID(str(value))
    except Exception:
        return None


@celery_app.task(name="src.tasks.materialize_nfl_player_baseline_projections")
def materialize_nfl_player_baseline_projections(
    *,
    season: int,
    week: Optional[int] = None,
    model_version: str = "nfl-player-v1",
) -> Dict[str, Any]:
    session = SessionLocal()
    upserted = 0
    target_week = None
    try:
        target_week = _resolve_nfl_week(session, season=season, week=week)
        rows = session.execute(
            text(
                """
                SELECT
                  season, week, team, player_id, player_uid, player_name, position, game_id,
                  snap_proxy, route_proxy, target_proxy, rush_share, red_zone_share,
                  qb_dropback_factor, qb_pressure_factor, team_pace_factor, team_pass_rate_factor,
                  availability_confidence, role_confidence, feature_payload, updated_at
                FROM nfl_player_projection_features_weekly
                WHERE season = :season
                  AND week = :week
                ORDER BY team, position, player_name
                """
            ),
            {"season": int(season), "week": int(target_week)},
        ).fetchall()

        latest_props = session.execute(
            text(
                """
                SELECT
                  COALESCE(player_uid::text, player_name) AS identity_key,
                  market_key,
                  COUNT(*)::int AS snapshots
                FROM nfl_player_prop_market_snapshots
                WHERE season = :season
                  AND week = :week
                GROUP BY COALESCE(player_uid::text, player_name), market_key
                """
            ),
            {"season": int(season), "week": int(target_week)},
        ).fetchall()
        prop_cov: Dict[tuple[str, str], int] = {}
        for row in latest_props:
            prop_cov[(str(row.identity_key), str(row.market_key))] = int(row.snapshots or 0)

        for row in rows:
            resolved_player_uid = str(row.player_uid) if row.player_uid is not None else None
            if resolved_player_uid is None:
                identity = resolve_and_persist_player_identity(
                    session,
                    IdentityInput(
                        source_system="nfl_dp_player_usage_weekly",
                        external_id=str(row.player_id) if row.player_id is not None else None,
                        player_name=str(row.player_name or ""),
                        team=str(row.team or ""),
                        position=str(row.position or ""),
                        season=int(row.season),
                        week=int(row.week),
                    ),
                )
                resolved_player_uid = identity.player_uid
                session.execute(
                    text(
                        """
                        UPDATE nfl_player_projection_features_weekly
                        SET player_uid = CAST(:player_uid AS uuid), updated_at = NOW()
                        WHERE season = :season
                          AND week = :week
                          AND team = :team
                          AND player_id = :player_id
                        """
                    ),
                    {
                        "player_uid": resolved_player_uid,
                        "season": int(row.season),
                        "week": int(row.week),
                        "team": str(row.team),
                        "player_id": str(row.player_id),
                    },
                )
            inputs = PlayerFeatureInputs(
                position=str(row.position or ""),
                snap_proxy=float(row.snap_proxy or 0.0),
                route_proxy=float(row.route_proxy or 0.0),
                target_proxy=float(row.target_proxy or 0.0),
                rush_share=float(row.rush_share or 0.0),
                red_zone_share=float(row.red_zone_share or 0.0),
                qb_dropback_factor=float(row.qb_dropback_factor or 1.0),
                qb_pressure_factor=float(row.qb_pressure_factor or 1.0),
                team_pace_factor=float(row.team_pace_factor or 1.0),
                team_pass_rate_factor=float(row.team_pass_rate_factor or 1.0),
                availability_confidence=float(row.availability_confidence or 0.75),
                role_confidence=float(row.role_confidence or 0.65),
            )
            baseline = baseline_projection_from_features(inputs)
            cov_key = str(resolved_player_uid or row.player_name)
            coverage_payload = {
                "feature_source": "nfl_player_projection_features_weekly",
                "prop_snapshot_counts": {
                    "pass_yds": prop_cov.get((cov_key, "pass_yds"), 0),
                    "rush_yds": prop_cov.get((cov_key, "rush_yds"), 0),
                    "rec_yds": prop_cov.get((cov_key, "rec_yds"), 0),
                    "receptions": prop_cov.get((cov_key, "receptions"), 0),
                    "anytime_td": prop_cov.get((cov_key, "anytime_td"), 0),
                },
                "feature_freshness": str(row.updated_at.isoformat() if row.updated_at is not None else ""),
                "player_uid": resolved_player_uid,
            }
            session.execute(
                text(
                    """
                    INSERT INTO nfl_player_projection_baselines (
                      season, week, team, player_id, player_uid, player_name, position, game_id, model_version,
                      attempts_mean, attempts_std, carries_mean, carries_std, targets_mean, targets_std,
                      completions_mean, pass_yards_mean, pass_yards_std,
                      rush_yards_mean, rush_yards_std, receiving_yards_mean, receiving_yards_std,
                      receptions_mean, receptions_std,
                      pass_tds_mean, rush_tds_mean, rec_tds_mean, anytime_td_prob,
                      floor_outcome, median_outcome, ceiling_outcome, uncertainty, source_coverage,
                      created_at, updated_at
                    ) VALUES (
                      :season, :week, :team, :player_id, CAST(:player_uid AS uuid), :player_name, :position, :game_id, :model_version,
                      :attempts_mean, :attempts_std, :carries_mean, :carries_std, :targets_mean, :targets_std,
                      :completions_mean, :pass_yards_mean, :pass_yards_std,
                      :rush_yards_mean, :rush_yards_std, :receiving_yards_mean, :receiving_yards_std,
                      :receptions_mean, :receptions_std,
                      :pass_tds_mean, :rush_tds_mean, :rec_tds_mean, :anytime_td_prob,
                      CAST(:floor_outcome AS jsonb), CAST(:median_outcome AS jsonb), CAST(:ceiling_outcome AS jsonb),
                      CAST(:uncertainty AS jsonb), CAST(:source_coverage AS jsonb),
                      NOW(), NOW()
                    )
                    ON CONFLICT (season, week, team, player_id, model_version) DO UPDATE SET
                      player_uid = EXCLUDED.player_uid,
                      player_name = EXCLUDED.player_name,
                      position = EXCLUDED.position,
                      game_id = EXCLUDED.game_id,
                      attempts_mean = EXCLUDED.attempts_mean,
                      attempts_std = EXCLUDED.attempts_std,
                      carries_mean = EXCLUDED.carries_mean,
                      carries_std = EXCLUDED.carries_std,
                      targets_mean = EXCLUDED.targets_mean,
                      targets_std = EXCLUDED.targets_std,
                      completions_mean = EXCLUDED.completions_mean,
                      pass_yards_mean = EXCLUDED.pass_yards_mean,
                      pass_yards_std = EXCLUDED.pass_yards_std,
                      rush_yards_mean = EXCLUDED.rush_yards_mean,
                      rush_yards_std = EXCLUDED.rush_yards_std,
                      receiving_yards_mean = EXCLUDED.receiving_yards_mean,
                      receiving_yards_std = EXCLUDED.receiving_yards_std,
                      receptions_mean = EXCLUDED.receptions_mean,
                      receptions_std = EXCLUDED.receptions_std,
                      pass_tds_mean = EXCLUDED.pass_tds_mean,
                      rush_tds_mean = EXCLUDED.rush_tds_mean,
                      rec_tds_mean = EXCLUDED.rec_tds_mean,
                      anytime_td_prob = EXCLUDED.anytime_td_prob,
                      floor_outcome = EXCLUDED.floor_outcome,
                      median_outcome = EXCLUDED.median_outcome,
                      ceiling_outcome = EXCLUDED.ceiling_outcome,
                      uncertainty = EXCLUDED.uncertainty,
                      source_coverage = EXCLUDED.source_coverage,
                      updated_at = EXCLUDED.updated_at
                    """
                ),
                {
                    "season": int(row.season),
                    "week": int(row.week),
                    "team": row.team,
                    "player_id": row.player_id,
                    "player_uid": resolved_player_uid,
                    "player_name": row.player_name,
                    "position": row.position,
                    "game_id": row.game_id,
                    "model_version": model_version,
                    **{k: baseline[k] for k in (
                        "attempts_mean", "attempts_std", "carries_mean", "carries_std", "targets_mean", "targets_std",
                        "completions_mean", "pass_yards_mean", "pass_yards_std", "rush_yards_mean", "rush_yards_std",
                        "receiving_yards_mean", "receiving_yards_std", "receptions_mean", "receptions_std",
                        "pass_tds_mean", "rush_tds_mean", "rec_tds_mean", "anytime_td_prob",
                    )},
                    "floor_outcome": json.dumps(baseline["floor_outcome"]),
                    "median_outcome": json.dumps(baseline["median_outcome"]),
                    "ceiling_outcome": json.dumps(baseline["ceiling_outcome"]),
                    "uncertainty": json.dumps(baseline["uncertainty"]),
                    "source_coverage": json.dumps(coverage_payload),
                },
            )
            upserted += 1

        freshness_row = session.execute(
            text(
                """
                SELECT MAX(updated_at) AS max_updated_at
                FROM nfl_player_projection_features_weekly
                WHERE season = :season
                  AND week = :week
                """
            ),
            {"season": int(season), "week": int(target_week)},
        ).fetchone()
        session.execute(
            text(
                """
                INSERT INTO nfl_projection_audit_runs (
                  season, week, layer, model_version, source_coverage, freshness, calibration_flags, readiness_status, metrics, created_at
                ) VALUES (
                  :season, :week, :layer, :model_version,
                  CAST(:source_coverage AS jsonb), CAST(:freshness AS jsonb),
                  CAST(:calibration_flags AS jsonb), :readiness_status, CAST(:metrics AS jsonb), NOW()
                )
                """
            ),
            {
                "season": int(season),
                "week": int(target_week),
                "layer": "player_baseline",
                "model_version": model_version,
                "source_coverage": json.dumps({"feature_rows": len(rows)}),
                "freshness": json.dumps({"max_feature_updated_at": str(freshness_row.max_updated_at) if freshness_row is not None else None}),
                "calibration_flags": json.dumps({"calibrated": False, "reason": "v1-heuristic-baseline"}),
                "readiness_status": "go" if len(rows) >= 40 else "warning",
                "metrics": json.dumps({"baseline_rows_upserted": upserted}),
            },
        )
        session.commit()
        return {
            "season": int(season),
            "week": int(target_week),
            "model_version": model_version,
            "baseline_rows_upserted": upserted,
        }
    except Exception:
        session.rollback()
        log.exception("Failed to materialize NFL player baseline projections")
        raise
    finally:
        session.close()


@celery_app.task(name="src.tasks.materialize_nfl_player_props_edges")
def materialize_nfl_player_props_edges(
    *,
    season: int,
    week: Optional[int] = None,
    model_version: str = "nfl-player-v1",
) -> Dict[str, Any]:
    session = SessionLocal()
    target_week = None
    upserted = 0
    try:
        target_week = _resolve_nfl_week(session, season=season, week=week)
        baselines = session.execute(
            text(
                """
                SELECT *
                FROM nfl_player_projection_baselines
                WHERE season = :season
                  AND week = :week
                  AND model_version = :model_version
                """
            ),
            {"season": int(season), "week": int(target_week), "model_version": model_version},
        ).fetchall()
        market_rows = session.execute(
            text(
                """
                SELECT DISTINCT ON (player_name, market_key, line)
                  id,
                  season,
                  week,
                  game_id,
                  player_id,
                  player_uid,
                  player_name,
                  team,
                  market_key,
                  line,
                  over_price,
                  under_price,
                  captured_at
                FROM nfl_player_prop_market_snapshots
                WHERE season = :season
                  AND week = :week
                ORDER BY player_name, market_key, line, captured_at DESC
                """
            ),
            {"season": int(season), "week": int(target_week)},
        ).fetchall()
        market_lookup: Dict[tuple[str, str], Any] = {}
        for market in market_rows:
            identity_key = str(market.player_uid) if market.player_uid is not None else str(market.player_name).strip().lower()
            key = (identity_key, str(market.market_key))
            market_lookup[key] = market

        for row in baselines:
            resolved_player_uid = str(row.player_uid) if row.player_uid is not None else None
            if resolved_player_uid is None:
                identity = resolve_and_persist_player_identity(
                    session,
                    IdentityInput(
                        source_system="nfl_player_projection_baselines",
                        external_id=str(row.player_id) if row.player_id is not None else None,
                        player_name=str(row.player_name or ""),
                        team=str(row.team or ""),
                        position=str(row.position or ""),
                        season=int(row.season),
                        week=int(row.week),
                    ),
                )
                resolved_player_uid = identity.player_uid
                session.execute(
                    text(
                        """
                        UPDATE nfl_player_projection_baselines
                        SET player_uid = CAST(:player_uid AS uuid), updated_at = NOW()
                        WHERE season = :season
                          AND week = :week
                          AND team = :team
                          AND player_id = :player_id
                          AND model_version = :model_version
                        """
                    ),
                    {
                        "player_uid": resolved_player_uid,
                        "season": int(row.season),
                        "week": int(row.week),
                        "team": str(row.team),
                        "player_id": str(row.player_id),
                        "model_version": str(model_version),
                    },
                )
            player_key = str(resolved_player_uid or str(row.player_name or "").strip().lower())
            markets = [
                ("pass_yds", float(row.pass_yards_mean or 0.0), float(row.pass_yards_std or 4.0)),
                ("rush_yds", float(row.rush_yards_mean or 0.0), float(row.rush_yards_std or 4.0)),
                ("rec_yds", float(row.receiving_yards_mean or 0.0), float(row.receiving_yards_std or 4.0)),
                ("receptions", float(row.receptions_mean or 0.0), float(row.receptions_std or 1.0)),
                ("anytime_td", float(row.anytime_td_prob or 0.0), 0.16),
            ]
            for market_key, model_mean, model_std in markets:
                market = market_lookup.get((player_key, market_key))
                line = float(market.line) if (market is not None and market.line is not None) else (
                    0.5 if market_key == "anytime_td" else float(model_mean)
                )
                over_price = int(market.over_price) if (market is not None and market.over_price is not None) else None
                under_price = int(market.under_price) if (market is not None and market.under_price is not None) else None
                if market_key == "anytime_td":
                    model_floor = max(0.0, model_mean * 0.55)
                    model_median = model_mean
                    model_ceiling = min(0.95, model_mean * 1.55 + 0.03)
                    edge = evaluate_prop_edge(
                        model_mean=model_mean,
                        model_std=max(0.08, model_std),
                        line=0.5,
                        market_over_price=over_price,
                        market_under_price=under_price,
                    )
                else:
                    model_floor = max(0.0, model_mean - (1.0 * model_std))
                    model_median = model_mean
                    model_ceiling = model_mean + (1.1 * model_std)
                    edge = evaluate_prop_edge(
                        model_mean=model_mean,
                        model_std=max(0.6, model_std),
                        line=line,
                        market_over_price=over_price,
                        market_under_price=under_price,
                    )

                session.execute(
                    text(
                        """
                        INSERT INTO nfl_player_prop_model_edges (
                          season, week, model_version, game_id, player_id, player_uid, player_name, team, market_key,
                          line, model_mean, model_std, model_floor, model_median, model_ceiling,
                          over_prob, under_prob, fair_over_price, fair_under_price,
                          market_over_price, market_under_price, edge_over, edge_under, confidence,
                          diagnostics, created_at, updated_at
                        ) VALUES (
                          :season, :week, :model_version, :game_id, :player_id, CAST(:player_uid AS uuid), :player_name, :team, :market_key,
                          :line, :model_mean, :model_std, :model_floor, :model_median, :model_ceiling,
                          :over_prob, :under_prob, :fair_over_price, :fair_under_price,
                          :market_over_price, :market_under_price, :edge_over, :edge_under, :confidence,
                          CAST(:diagnostics AS jsonb), NOW(), NOW()
                        )
                        ON CONFLICT (season, week, model_version, player_name, market_key, COALESCE(line, -9999)) DO UPDATE SET
                          game_id = EXCLUDED.game_id,
                          player_id = EXCLUDED.player_id,
                          player_uid = EXCLUDED.player_uid,
                          team = EXCLUDED.team,
                          model_mean = EXCLUDED.model_mean,
                          model_std = EXCLUDED.model_std,
                          model_floor = EXCLUDED.model_floor,
                          model_median = EXCLUDED.model_median,
                          model_ceiling = EXCLUDED.model_ceiling,
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
                          updated_at = EXCLUDED.updated_at
                        """
                    ),
                    {
                        "season": int(row.season),
                        "week": int(row.week),
                        "model_version": model_version,
                        "game_id": _to_uuid_or_none(row.game_id),
                        "player_id": row.player_id,
                        "player_uid": resolved_player_uid,
                        "player_name": row.player_name,
                        "team": row.team,
                        "market_key": market_key,
                        "line": line,
                        "model_mean": model_mean,
                        "model_std": model_std,
                        "model_floor": model_floor,
                        "model_median": model_median,
                        "model_ceiling": model_ceiling,
                        "over_prob": edge["over_prob"],
                        "under_prob": edge["under_prob"],
                        "fair_over_price": edge["fair_over_price"],
                        "fair_under_price": edge["fair_under_price"],
                        "market_over_price": over_price,
                        "market_under_price": under_price,
                        "edge_over": edge["edge_over"],
                        "edge_under": edge["edge_under"],
                        "confidence": edge["confidence"],
                        "diagnostics": json.dumps(
                            {
                                "market_snapshot_id": str(market.id) if market is not None else None,
                                "fallback_used": market is None,
                                "created_from_baseline_model_version": model_version,
                            }
                        ),
                    },
                )
                upserted += 1

        session.execute(
            text(
                """
                INSERT INTO nfl_projection_audit_runs (
                  season, week, layer, model_version, source_coverage, freshness, calibration_flags, readiness_status, metrics, created_at
                ) VALUES (
                  :season, :week, :layer, :model_version,
                  CAST(:source_coverage AS jsonb), CAST(:freshness AS jsonb),
                  CAST(:calibration_flags AS jsonb), :readiness_status, CAST(:metrics AS jsonb), NOW()
                )
                """
            ),
            {
                "season": int(season),
                "week": int(target_week),
                "layer": "props",
                "model_version": model_version,
                "source_coverage": json.dumps({"market_rows": len(market_rows), "baseline_rows": len(baselines)}),
                "freshness": json.dumps({"latest_market_snapshot": str(max([r.captured_at for r in market_rows], default=None))}),
                "calibration_flags": json.dumps({"calibrated": False, "distribution": "gaussian-approx"}),
                "readiness_status": "go" if len(baselines) > 20 else "warning",
                "metrics": json.dumps({"prop_edges_upserted": upserted}),
            },
        )
        session.commit()
        return {"season": int(season), "week": int(target_week), "model_version": model_version, "prop_edges_upserted": upserted}
    except Exception:
        session.rollback()
        log.exception("Failed to materialize NFL player props edges")
        raise
    finally:
        session.close()


@celery_app.task(name="src.tasks.pull_nfl_player_prop_market_snapshots")
def pull_nfl_player_prop_market_snapshots(
    *,
    season: int,
    week: int,
) -> Dict[str, Any]:
    market_keys = ["player_pass_yds", "player_rush_yds", "player_reception_yds", "player_receptions", "player_anytime_td"]
    market_map = {
        "player_pass_yds": "pass_yds",
        "player_rush_yds": "rush_yds",
        "player_reception_yds": "rec_yds",
        "player_receptions": "receptions",
        "player_anytime_td": "anytime_td",
    }
    events = fetch_odds(
        endpoint="sports/americanfootball_nfl/events",
        params={"dateFormat": "iso"},
    )
    if not isinstance(events, list):
        return {"events_seen": 0, "snapshots_upserted": 0}
    session = SessionLocal()
    inserted = 0
    try:
        game_lookup_rows = session.execute(
            text(
                """
                SELECT
                  g.id::text AS game_id,
                  g.external_id
                FROM games g
                JOIN seasons s ON s.id = g.season_id
                JOIN leagues l ON l.id = s.league_id
                WHERE l.code = 'nfl'
                  AND s.season_year = :season
                """
            ),
            {"season": int(season)},
        ).fetchall()
        game_lookup = {str(row.external_id): str(row.game_id) for row in game_lookup_rows if row.external_id is not None}

        for event in events:
            event_id = str(event.get("id") or "")
            if not event_id:
                continue
            details = fetch_odds(
                endpoint=f"sports/americanfootball_nfl/events/{event_id}/odds",
                params={
                    "regions": "us",
                    "markets": ",".join(market_keys),
                    "oddsFormat": "american",
                    "dateFormat": "iso",
                },
            )
            if not isinstance(details, dict):
                continue
            for bookmaker in details.get("bookmakers") or []:
                sportsbook = str(bookmaker.get("key") or bookmaker.get("title") or "unknown")
                for market in bookmaker.get("markets") or []:
                    market_key_raw = str(market.get("key") or "")
                    market_key = market_map.get(market_key_raw)
                    if market_key is None:
                        continue
                    outcomes = market.get("outcomes") or []
                    for outcome in outcomes:
                        player_name = str(outcome.get("description") or outcome.get("name") or "").strip()
                        if not player_name:
                            continue
                        side = str(outcome.get("name") or "").strip().lower()
                        line = _safe_float(outcome.get("point"))
                        over_price = _safe_int(outcome.get("price")) if side == "over" else None
                        under_price = _safe_int(outcome.get("price")) if side == "under" else None
                        if market_key == "anytime_td":
                            line = 0.5
                            if side not in {"yes", "no", "over", "under"}:
                                over_price = _safe_int(outcome.get("price"))
                        implied_over = _american_implied_prob(over_price) if over_price is not None else None
                        implied_under = _american_implied_prob(under_price) if under_price is not None else None
                        identity = resolve_and_persist_player_identity(
                            session,
                            IdentityInput(
                                source_system="odds_api_nfl_props",
                                external_id=None,
                                player_name=player_name,
                                team=None,
                                position=None,
                                season=int(season),
                                week=int(week),
                                source_payload={
                                    "event_id": event_id,
                                    "market_key": market_key,
                                    "sportsbook": sportsbook,
                                },
                            ),
                        )
                        session.execute(
                            text(
                                """
                                INSERT INTO nfl_player_prop_market_snapshots (
                                  season, week, game_id, external_game_id, sportsbook, captured_at,
                                  player_uid, player_name, team, opponent, market_key, line,
                                  over_price, under_price, implied_prob_over, implied_prob_under,
                                  source, metadata, created_at
                                ) VALUES (
                                  :season, :week, :game_id, :external_game_id, :sportsbook, :captured_at,
                                  CAST(:player_uid AS uuid), :player_name, :team, :opponent, :market_key, :line,
                                  :over_price, :under_price, :implied_prob_over, :implied_prob_under,
                                  :source, CAST(:metadata AS jsonb), NOW()
                                )
                                ON CONFLICT (sportsbook, captured_at, player_name, market_key, COALESCE(line, -9999))
                                DO UPDATE SET
                                  game_id = EXCLUDED.game_id,
                                  over_price = COALESCE(EXCLUDED.over_price, nfl_player_prop_market_snapshots.over_price),
                                  under_price = COALESCE(EXCLUDED.under_price, nfl_player_prop_market_snapshots.under_price),
                                  implied_prob_over = COALESCE(EXCLUDED.implied_prob_over, nfl_player_prop_market_snapshots.implied_prob_over),
                                  implied_prob_under = COALESCE(EXCLUDED.implied_prob_under, nfl_player_prop_market_snapshots.implied_prob_under),
                                  metadata = EXCLUDED.metadata
                                """
                            ),
                            {
                                "season": int(season),
                                "week": int(week),
                                "game_id": _to_uuid_or_none(game_lookup.get(event_id)),
                                "external_game_id": event_id,
                                "sportsbook": sportsbook,
                                "captured_at": _parse_iso_datetime(details.get("commence_time")) or _now_utc(),
                                "player_uid": identity.player_uid,
                                "player_name": player_name,
                                "team": None,
                                "opponent": None,
                                "market_key": market_key,
                                "line": line,
                                "over_price": over_price,
                                "under_price": under_price,
                                "implied_prob_over": implied_over,
                                "implied_prob_under": implied_under,
                                "source": "odds_api",
                                "metadata": json.dumps(
                                    {
                                        "raw_market_key": market_key_raw,
                                        "outcome_side": side,
                                        "identity_status": identity.status,
                                        "identity_rule": identity.rule_used,
                                        "resolver_version": identity.resolver_version,
                                    }
                                ),
                            },
                        )
                        inserted += 1
        session.commit()
        return {"events_seen": len(events), "snapshots_upserted": inserted}
    except Exception:
        session.rollback()
        log.exception("Failed pulling NFL player prop market snapshots")
        raise
    finally:
        session.close()


@celery_app.task(name="src.tasks.materialize_nfl_fantasy_projections")
def materialize_nfl_fantasy_projections(
    *,
    season: int,
    week: Optional[int] = None,
    model_version: str = "nfl-player-v1",
) -> Dict[str, Any]:
    session = SessionLocal()
    target_week = None
    upserted = 0
    try:
        target_week = _resolve_nfl_week(session, season=season, week=week)
        baselines = session.execute(
            text(
                """
                SELECT *
                FROM nfl_player_projection_baselines
                WHERE season = :season
                  AND week = :week
                  AND model_version = :model_version
                ORDER BY position, team, player_name
                """
            ),
            {"season": int(season), "week": int(target_week), "model_version": model_version},
        ).fetchall()
        profiles = ["standard", "half_ppr", "ppr"]
        rank_inputs: Dict[str, List[Dict[str, Any]]] = {profile: [] for profile in profiles}
        for row in baselines:
            resolved_player_uid = str(row.player_uid) if row.player_uid is not None else None
            if resolved_player_uid is None:
                identity = resolve_and_persist_player_identity(
                    session,
                    IdentityInput(
                        source_system="nfl_fantasy_projection_baseline",
                        external_id=str(row.player_id) if row.player_id is not None else None,
                        player_name=str(row.player_name or ""),
                        team=str(row.team or ""),
                        position=str(row.position or ""),
                        season=int(row.season),
                        week=int(row.week),
                    ),
                )
                resolved_player_uid = identity.player_uid
            for profile in profiles:
                expected = fantasy_points_from_projection(
                    scoring_profile=profile,
                    pass_yards=float(row.pass_yards_mean or 0.0),
                    pass_tds=float(row.pass_tds_mean or 0.0),
                    rush_yards=float(row.rush_yards_mean or 0.0),
                    rush_tds=float(row.rush_tds_mean or 0.0),
                    receiving_yards=float(row.receiving_yards_mean or 0.0),
                    receptions=float(row.receptions_mean or 0.0),
                    rec_tds=float(row.rec_tds_mean or 0.0),
                )
                floor = fantasy_points_from_projection(
                    scoring_profile=profile,
                    pass_yards=float((row.floor_outcome or {}).get("pass_yards", 0.0)),
                    pass_tds=float(row.pass_tds_mean or 0.0) * 0.60,
                    rush_yards=float((row.floor_outcome or {}).get("rush_yards", 0.0)),
                    rush_tds=float(row.rush_tds_mean or 0.0) * 0.60,
                    receiving_yards=float((row.floor_outcome or {}).get("receiving_yards", 0.0)),
                    receptions=float((row.floor_outcome or {}).get("receptions", 0.0)),
                    rec_tds=float(row.rec_tds_mean or 0.0) * 0.60,
                )
                ceiling = fantasy_points_from_projection(
                    scoring_profile=profile,
                    pass_yards=float((row.ceiling_outcome or {}).get("pass_yards", row.pass_yards_mean or 0.0)),
                    pass_tds=float(row.pass_tds_mean or 0.0) * 1.35,
                    rush_yards=float((row.ceiling_outcome or {}).get("rush_yards", row.rush_yards_mean or 0.0)),
                    rush_tds=float(row.rush_tds_mean or 0.0) * 1.35,
                    receiving_yards=float((row.ceiling_outcome or {}).get("receiving_yards", row.receiving_yards_mean or 0.0)),
                    receptions=float((row.ceiling_outcome or {}).get("receptions", row.receptions_mean or 0.0)),
                    rec_tds=float(row.rec_tds_mean or 0.0) * 1.35,
                )
                rank_inputs[profile].append(
                    {
                        "player_id": row.player_id,
                        "player_uid": resolved_player_uid,
                        "player_name": row.player_name,
                        "team": row.team,
                        "position": row.position,
                        "expected": expected,
                        "floor": floor,
                        "median": expected,
                        "ceiling": ceiling,
                    }
                )

        for profile in profiles:
            sorted_players = sorted(rank_inputs[profile], key=lambda item: float(item["expected"]), reverse=True)
            by_position: Dict[str, List[Dict[str, Any]]] = {}
            for player in sorted_players:
                by_position.setdefault(str(player["position"] or "UNK"), []).append(player)
            pos_rank_map: Dict[tuple[str, str], int] = {}
            for _position, players in by_position.items():
                for idx, player in enumerate(players, start=1):
                    pos_rank_map[(str(player["player_id"]), str(player["position"] or "UNK"))] = idx

            for idx, player in enumerate(sorted_players, start=1):
                tier = max(1, min(8, 1 + ((idx - 1) // 18)))
                position = str(player["position"] or "UNK")
                session.execute(
                    text(
                        """
                        INSERT INTO nfl_fantasy_weekly_projections (
                          season, week, scoring_profile, model_version, player_id, player_uid, player_name, team, position,
                          expected_points, floor_points, median_points, ceiling_points,
                          rank_overall, rank_position, tier, projection_payload, created_at, updated_at
                        ) VALUES (
                          :season, :week, :scoring_profile, :model_version, :player_id, CAST(:player_uid AS uuid), :player_name, :team, :position,
                          :expected_points, :floor_points, :median_points, :ceiling_points,
                          :rank_overall, :rank_position, :tier, CAST(:projection_payload AS jsonb), NOW(), NOW()
                        )
                        ON CONFLICT (season, week, scoring_profile, model_version, player_id) DO UPDATE SET
                          player_uid = EXCLUDED.player_uid,
                          player_name = EXCLUDED.player_name,
                          team = EXCLUDED.team,
                          position = EXCLUDED.position,
                          expected_points = EXCLUDED.expected_points,
                          floor_points = EXCLUDED.floor_points,
                          median_points = EXCLUDED.median_points,
                          ceiling_points = EXCLUDED.ceiling_points,
                          rank_overall = EXCLUDED.rank_overall,
                          rank_position = EXCLUDED.rank_position,
                          tier = EXCLUDED.tier,
                          projection_payload = EXCLUDED.projection_payload,
                          updated_at = EXCLUDED.updated_at
                        """
                    ),
                    {
                        "season": int(season),
                        "week": int(target_week),
                        "scoring_profile": profile,
                        "model_version": model_version,
                        "player_id": player["player_id"],
                        "player_uid": player["player_uid"],
                        "player_name": player["player_name"],
                        "team": player["team"],
                        "position": position,
                        "expected_points": player["expected"],
                        "floor_points": player["floor"],
                        "median_points": player["median"],
                        "ceiling_points": player["ceiling"],
                        "rank_overall": idx,
                        "rank_position": pos_rank_map.get((str(player["player_id"]), position), idx),
                        "tier": tier,
                        "projection_payload": json.dumps({"derived_from": "nfl_player_projection_baselines", "profile": profile}),
                    },
                )
                upserted += 1

        session.execute(
            text(
                """
                INSERT INTO nfl_projection_audit_runs (
                  season, week, layer, model_version, source_coverage, freshness, calibration_flags, readiness_status, metrics, created_at
                ) VALUES (
                  :season, :week, :layer, :model_version,
                  CAST(:source_coverage AS jsonb), CAST(:freshness AS jsonb),
                  CAST(:calibration_flags AS jsonb), :readiness_status, CAST(:metrics AS jsonb), NOW()
                )
                """
            ),
            {
                "season": int(season),
                "week": int(target_week),
                "layer": "fantasy",
                "model_version": model_version,
                "source_coverage": json.dumps({"baseline_rows": len(baselines), "profiles": 3}),
                "freshness": json.dumps({"generated_at": datetime.now(timezone.utc).isoformat()}),
                "calibration_flags": json.dumps({"calibrated": False, "tiers": "fixed-slab"}),
                "readiness_status": "go" if len(baselines) > 20 else "warning",
                "metrics": json.dumps({"fantasy_rows_upserted": upserted}),
            },
        )
        session.commit()
        return {"season": int(season), "week": int(target_week), "model_version": model_version, "fantasy_rows_upserted": upserted}
    except Exception:
        session.rollback()
        log.exception("Failed to materialize NFL fantasy projections")
        raise
    finally:
        session.close()


@celery_app.task(name="src.tasks.run_nfl_player_projection_cycle")
def run_nfl_player_projection_cycle(
    *,
    season: int,
    week: Optional[int] = None,
    model_version: str = "nfl-player-v1",
    pull_market_snapshots: bool = True,
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        target_week = _resolve_nfl_week(session, season=season, week=week)
    finally:
        session.close()
    market_pull = {"skipped": True}
    if pull_market_snapshots:
        market_pull = pull_nfl_player_prop_market_snapshots(season=season, week=target_week)
    baseline = materialize_nfl_player_baseline_projections(season=season, week=target_week, model_version=model_version)
    props = materialize_nfl_player_props_edges(season=season, week=target_week, model_version=model_version)
    fantasy = materialize_nfl_fantasy_projections(season=season, week=target_week, model_version=model_version)
    identity_quality = run_nfl_identity_quality_snapshot(season=season, week=target_week, source_system=None)
    return {
        "market_pull": market_pull,
        "baseline": baseline,
        "props": props,
        "fantasy": fantasy,
        "identity_quality": identity_quality,
    }


@celery_app.task(name="src.tasks.run_nfl_identity_refresh")
def run_nfl_identity_refresh(
    *,
    season: int,
    week: Optional[int] = None,
    model_version: str = "nfl-player-v1",
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        target_week = _resolve_nfl_week(session, season=season, week=week)
    finally:
        session.close()
    baseline = materialize_nfl_player_baseline_projections(season=season, week=target_week, model_version=model_version)
    props = materialize_nfl_player_props_edges(season=season, week=target_week, model_version=model_version)
    fantasy = materialize_nfl_fantasy_projections(season=season, week=target_week, model_version=model_version)
    quality = run_nfl_identity_quality_snapshot(season=season, week=target_week, source_system=None)
    return {
        "season": int(season),
        "week": int(target_week),
        "resolver_version": DEFAULT_RESOLVER_VERSION,
        "baseline": baseline,
        "props": props,
        "fantasy": fantasy,
        "quality": quality,
    }


@celery_app.task(name="src.tasks.apply_nfl_identity_manual_resolutions")
def apply_nfl_identity_manual_resolutions(
    *,
    limit: int = 200,
    reviewer: str = "system-weekly-identity-sync",
) -> Dict[str, Any]:
    session = SessionLocal()
    approved = 0
    rejected = 0
    try:
        queue_rows = session.execute(
            text(
                """
                SELECT
                  q.id::text AS queue_id,
                  q.proposed_player_uid::text AS proposed_player_uid,
                  q.reason
                FROM nfl_player_mapping_review_queue q
                WHERE q.queue_status = 'pending'
                  AND q.reason = 'guardrail_high_confidence_remap'
                ORDER BY q.created_at ASC
                LIMIT :limit
                """
            ),
            {"limit": int(limit)},
        ).fetchall()
        for row in queue_rows:
            if row.proposed_player_uid:
                result = apply_manual_mapping_resolution(
                    session,
                    queue_id=str(row.queue_id),
                    action="approve",
                    reviewer=reviewer,
                    player_uid=str(row.proposed_player_uid),
                    notes="Auto-approved trusted remap candidate after guardrail queue review.",
                )
                if result.get("updated"):
                    approved += 1
            else:
                result = apply_manual_mapping_resolution(
                    session,
                    queue_id=str(row.queue_id),
                    action="reject",
                    reviewer=reviewer,
                    player_uid=None,
                    notes="Auto-rejected due to missing proposed_player_uid.",
                )
                if result.get("updated"):
                    rejected += 1
        session.commit()
        return {"reviewed": len(queue_rows), "approved": approved, "rejected": rejected}
    except Exception:
        session.rollback()
        log.exception("Failed applying NFL identity manual resolutions")
        raise
    finally:
        session.close()


@celery_app.task(name="src.tasks.run_nfl_identity_quality_snapshot")
def run_nfl_identity_quality_snapshot(
    *,
    season: Optional[int] = None,
    week: Optional[int] = None,
    source_system: Optional[str] = None,
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        payload = compute_identity_quality_snapshot(
            session,
            season=season,
            week=week,
            source_system=source_system,
            resolver_version=DEFAULT_RESOLVER_VERSION,
        )
        persist_identity_quality_snapshot(session, payload)
        session.commit()
        return payload
    except Exception:
        session.rollback()
        log.exception("Failed persisting NFL identity quality snapshot")
        raise
    finally:
        session.close()
