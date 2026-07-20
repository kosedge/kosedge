from __future__ import annotations

import os
from decimal import Decimal
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, TypedDict

import logging

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError, SQLAlchemyError

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
from src.services.nfl_handicapping_framework import (
    evaluate_nfl_edge_guardrails,
    get_nfl_handicapping_config,
)
from src.services.nfl_totals_calibration import fetch_nfl_totals_calibration

router = APIRouter(prefix="/nfl", tags=["nfl-model"])
log = logging.getLogger(__name__)
MODEL_STATE_KEY = "nfl_active_model"
TASK_EVAL_NFL_PROMOTION = "src.tasks.evaluate_nfl_model_promotion"
TASK_NFL_PLAYER_BASELINES = "src.tasks.materialize_nfl_player_baseline_projections"
TASK_NFL_PLAYER_PROPS = "src.tasks.materialize_nfl_player_props_edges"
TASK_NFL_FANTASY = "src.tasks.materialize_nfl_fantasy_projections"
TASK_NFL_FANTASY_DRAFT_RANKINGS = "src.tasks.materialize_nfl_fantasy_season_draft_rankings"
TASK_NFL_AWARD_PROJECTIONS = "src.tasks.materialize_nfl_award_projections"
TASK_NFL_PLAYER_CYCLE = "src.tasks.run_nfl_player_projection_cycle"
TASK_NFL_IDENTITY_REFRESH = "src.tasks.run_nfl_identity_refresh"
TASK_NFL_IDENTITY_MANUAL_RESOLUTIONS = "src.tasks.apply_nfl_identity_manual_resolutions"
TASK_NFL_IDENTITY_QUALITY_SNAPSHOT = "src.tasks.run_nfl_identity_quality_snapshot"
TASK_NFL_FRAMEWORK_TUNING = "src.tasks.run_nfl_framework_tuning"
TASK_NFL_DECOMPOSITION_DRIFT = "src.tasks.run_nfl_decomposition_drift_monitor"
NFL_DEFAULT_ODDS_BOOKMAKERS = "draftkings"

NFL_TEAM_CONFERENCE_MAP: Dict[str, str] = {
    "ARI": "NFC",
    "ATL": "NFC",
    "BAL": "AFC",
    "BUF": "AFC",
    "CAR": "NFC",
    "CHI": "NFC",
    "CIN": "AFC",
    "CLE": "AFC",
    "DAL": "NFC",
    "DEN": "AFC",
    "DET": "NFC",
    "GB": "NFC",
    "HOU": "AFC",
    "IND": "AFC",
    "JAX": "AFC",
    "KC": "AFC",
    "LV": "AFC",
    "LAC": "AFC",
    "LAR": "NFC",
    "MIA": "AFC",
    "MIN": "NFC",
    "NE": "AFC",
    "NO": "NFC",
    "NYG": "NFC",
    "NYJ": "AFC",
    "PHI": "NFC",
    "PIT": "AFC",
    "SEA": "NFC",
    "SF": "NFC",
    "TB": "NFC",
    "TEN": "AFC",
    "WAS": "NFC",
}

NFL_TEAM_DIVISION_MAP: Dict[str, str] = {
    "ARI": "West",
    "ATL": "South",
    "BAL": "North",
    "BUF": "East",
    "CAR": "South",
    "CHI": "North",
    "CIN": "North",
    "CLE": "North",
    "DAL": "East",
    "DEN": "West",
    "DET": "North",
    "GB": "North",
    "HOU": "South",
    "IND": "South",
    "JAX": "South",
    "KC": "West",
    "LV": "West",
    "LAC": "West",
    "LAR": "West",
    "MIA": "East",
    "MIN": "North",
    "NE": "East",
    "NO": "South",
    "NYG": "East",
    "NYJ": "East",
    "PHI": "East",
    "PIT": "North",
    "SEA": "West",
    "SF": "West",
    "TB": "South",
    "TEN": "South",
    "WAS": "East",
}


def _build_team_case_sql(mapping: Dict[str, str], *, team_column: str = "team") -> str:
    when_clauses = " ".join(
        f"WHEN '{team_code}' THEN '{value}'" for team_code, value in sorted(mapping.items())
    )
    return f"CASE UPPER(BTRIM({team_column})) {when_clauses} ELSE NULL END"


NFL_TEAM_CONFERENCE_CASE_SQL = _build_team_case_sql(NFL_TEAM_CONFERENCE_MAP)
NFL_TEAM_DIVISION_CASE_SQL = _build_team_case_sql(NFL_TEAM_DIVISION_MAP)

# Odds API uses full club names; DB teams often store abbr-only in `name`.
NFL_ABBR_TO_FULL_NAME: Dict[str, str] = {
    "ARI": "Arizona Cardinals",
    "ATL": "Atlanta Falcons",
    "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills",
    "CAR": "Carolina Panthers",
    "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals",
    "CLE": "Cleveland Browns",
    "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos",
    "DET": "Detroit Lions",
    "GB": "Green Bay Packers",
    "HOU": "Houston Texans",
    "IND": "Indianapolis Colts",
    "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs",
    "LV": "Las Vegas Raiders",
    "LAC": "Los Angeles Chargers",
    "LAR": "Los Angeles Rams",
    "LA": "Los Angeles Rams",
    "MIA": "Miami Dolphins",
    "MIN": "Minnesota Vikings",
    "NE": "New England Patriots",
    "NO": "New Orleans Saints",
    "NYG": "New York Giants",
    "NYJ": "New York Jets",
    "PHI": "Philadelphia Eagles",
    "PIT": "Pittsburgh Steelers",
    "SEA": "Seattle Seahawks",
    "SF": "San Francisco 49ers",
    "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans",
    "WAS": "Washington Commanders",
    "WSH": "Washington Commanders",
}
NFL_FULL_NAME_TO_ABBR: Dict[str, str] = {}
for _abbr, _full in NFL_ABBR_TO_FULL_NAME.items():
    # Prefer canonical codes over aliases (LA→LAR, WSH→WAS).
    if _abbr in {"LA", "WSH"}:
        continue
    NFL_FULL_NAME_TO_ABBR["".join(ch for ch in _full.lower() if ch.isalnum())] = _abbr


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
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _round_intel_numeric_value(value: Any) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, (float, Decimal)):
        rounded = round(float(value), 3)
        return 0.0 if rounded == 0 else rounded
    return value


def _serialize_intel_rows(rows: List[Any]) -> List[Dict[str, Any]]:
    serialized: List[Dict[str, Any]] = []
    for row in rows:
        mapped = dict(row._mapping)
        serialized.append({key: _round_intel_numeric_value(val) for key, val in mapped.items()})
    return serialized


def _resolve_nfl_odds_bookmakers(raw: Optional[str] = None) -> str:
    candidate = str(
        raw
        if raw is not None
        else os.getenv("NFL_ODDS_BOOKMAKERS", NFL_DEFAULT_ODDS_BOOKMAKERS)
    ).strip()
    if not candidate:
        candidate = NFL_DEFAULT_ODDS_BOOKMAKERS
    books: List[str] = []
    for token in candidate.split(","):
        book = token.strip().lower()
        if book and book not in books:
            books.append(book)
    return ",".join(books) if books else NFL_DEFAULT_ODDS_BOOKMAKERS


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


def _normalize_team_key(name: Optional[str]) -> str:
    if not name:
        return ""
    return "".join(ch for ch in name.lower() if ch.isalnum())


def _nfl_team_to_abbr(name: Optional[str]) -> Optional[str]:
    """Map Odds API full names or DB abbr/name strings to a canonical team abbr."""
    if not name:
        return None
    raw = str(name).strip()
    if not raw:
        return None
    upper = raw.upper()
    if upper in NFL_ABBR_TO_FULL_NAME:
        if upper == "LA":
            return "LAR"
        if upper == "WSH":
            return "WAS"
        return upper
    return NFL_FULL_NAME_TO_ABBR.get(_normalize_team_key(raw))


def _extract_book_market_prices(
    event: Dict[str, Any],
) -> Tuple[Optional[int], Optional[int], Optional[float], Optional[float], int]:
    """Return (home_ml, away_ml, total, spread_home, market_depth) from an odds event."""
    home_team = str(event.get("home_team") or "")
    away_team = str(event.get("away_team") or "")
    home_prices: List[int] = []
    away_prices: List[int] = []
    totals: List[float] = []
    spreads: List[float] = []
    for book in event.get("bookmakers") or []:
        for market in book.get("markets") or []:
            key = market.get("key")
            if key == "h2h":
                for outcome in market.get("outcomes") or []:
                    if outcome.get("name") == home_team and outcome.get("price") is not None:
                        home_prices.append(int(outcome["price"]))
                    elif outcome.get("name") == away_team and outcome.get("price") is not None:
                        away_prices.append(int(outcome["price"]))
            elif key == "totals":
                for outcome in market.get("outcomes") or []:
                    if outcome.get("name") == "Over" and outcome.get("point") is not None:
                        totals.append(float(outcome["point"]))
            elif key == "spreads":
                for outcome in market.get("outcomes") or []:
                    if outcome.get("name") == home_team and outcome.get("point") is not None:
                        spreads.append(float(outcome["point"]))
    market_home_ml = int(round(sum(home_prices) / len(home_prices))) if home_prices else None
    market_away_ml = int(round(sum(away_prices) / len(away_prices))) if away_prices else None
    market_total = round(sum(totals) / len(totals), 2) if totals else None
    market_spread_home = round(sum(spreads) / len(spreads), 2) if spreads else None
    market_depth = len(home_prices) + len(totals) + len(spreads)
    return market_home_ml, market_away_ml, market_total, market_spread_home, market_depth


def _american_implied_prob(price: Optional[int]) -> Optional[float]:
    if price is None:
        return None
    if price > 0:
        return 100.0 / (price + 100.0)
    if price < 0:
        return abs(price) / (abs(price) + 100.0)
    return None


def _fetch_latest_framework_tuning_summary(session: Any, *, model_version: str) -> Optional[Dict[str, Any]]:
    row = session.execute(
        text(
            """
            SELECT id, payload, selected_config, created_at
            FROM nfl_framework_tuning_runs
            WHERE model_version = :model_version
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"model_version": model_version},
    ).fetchone()
    if row is None:
        return None
    payload = row.payload if isinstance(row.payload, dict) else {}
    selected_config = row.selected_config if isinstance(row.selected_config, dict) else {}
    return {
        "run_id": str(row.id),
        "created_at": row.created_at,
        "payload": payload,
        "selected_config": selected_config,
    }


def _fetch_latest_tuned_guardrails(
    session: Any,
    *,
    model_version: str,
    fallback: Dict[str, Any],
) -> Dict[str, Any]:
    tuning = _fetch_latest_framework_tuning_summary(session, model_version=model_version)
    if not tuning:
        return fallback
    selected_config = tuning.get("selected_config") if isinstance(tuning.get("selected_config"), dict) else {}
    guardrails = selected_config.get("guardrails") if isinstance(selected_config.get("guardrails"), dict) else {}
    if not guardrails:
        return fallback
    return {
        "min_quality_score": _to_float(guardrails.get("min_quality_score")) or _to_float(fallback.get("min_quality_score")) or 58.0,
        "min_confidence_score": _to_float(guardrails.get("min_confidence_score")) or _to_float(fallback.get("min_confidence_score")) or 0.53,
        "min_ml_edge_prob": _to_float(guardrails.get("min_ml_edge_prob")) or _to_float(fallback.get("min_ml_edge_prob")) or 0.01,
        "max_uncertainty_penalty": _to_float(guardrails.get("max_uncertainty_penalty"))
        or _to_float(fallback.get("max_uncertainty_penalty"))
        or 0.33,
        "min_factor_coverage": _to_float(guardrails.get("min_factor_coverage"))
        or _to_float(fallback.get("min_factor_coverage"))
        or 0.55,
        "max_injury_freshness_hours": _to_float(guardrails.get("max_injury_freshness_hours"))
        or _to_float(fallback.get("max_injury_freshness_hours"))
        or 72.0,
    }


_FRAMEWORK_GUARDRAILS = get_nfl_handicapping_config()["guardrails"]
NFL_EDGE_MIN_QUALITY_DEFAULT = float(_FRAMEWORK_GUARDRAILS["min_quality_score"])
NFL_EDGE_MIN_CONFIDENCE_DEFAULT = float(_FRAMEWORK_GUARDRAILS["min_confidence_score"])
NFL_EDGE_MIN_ML_EDGE_DEFAULT = float(_FRAMEWORK_GUARDRAILS["min_ml_edge_prob"])


class _IntelAvailability(TypedDict):
    season: Optional[int]
    week: Optional[int]
    row_count: int
    team_count: int


def _empty_intel_availability() -> _IntelAvailability:
    return {"season": None, "week": None, "row_count": 0, "team_count": 0}


def _fetch_weekly_intel_availability(
    session: Any,
    *,
    source_sql: str,
    season: Optional[int] = None,
) -> _IntelAvailability:
    row = session.execute(
        text(
            f"""
            WITH availability AS (
              {source_sql}
            ),
            aggregated AS (
              SELECT
                season,
                week,
                COUNT(*)::int AS row_count,
                COUNT(DISTINCT team)::int AS team_count
              FROM availability
              WHERE week IS NOT NULL
                AND (CAST(:season AS int) IS NULL OR season = CAST(:season AS int))
              GROUP BY season, week
            )
            SELECT season, week, row_count, team_count
            FROM aggregated
            ORDER BY
              CASE WHEN team_count >= 16 THEN 1 ELSE 0 END DESC,
              season DESC,
              week DESC,
              team_count DESC,
              row_count DESC
            LIMIT 1
            """
        ),
        {"season": season},
    ).fetchone()
    if row is None:
        return _empty_intel_availability()
    payload = dict(row._mapping)
    return {
        "season": _to_int(payload.get("season")),
        "week": _to_int(payload.get("week")),
        "row_count": _to_int(payload.get("row_count")) or 0,
        "team_count": _to_int(payload.get("team_count")) or 0,
    }


def _fetch_weekly_intel_requested_availability(
    session: Any,
    *,
    source_sql: str,
    season: int,
    week: int,
) -> _IntelAvailability:
    row = session.execute(
        text(
            f"""
            WITH availability AS (
              {source_sql}
            )
            SELECT
              :season AS season,
              :week AS week,
              COUNT(*)::int AS row_count,
              COUNT(DISTINCT team)::int AS team_count
            FROM availability
            WHERE season = :season
              AND week = :week
            """
        ),
        {"season": season, "week": week},
    ).fetchone()
    if row is None:
        return {"season": season, "week": week, "row_count": 0, "team_count": 0}
    payload = dict(row._mapping)
    return {
        "season": season,
        "week": week,
        "row_count": _to_int(payload.get("row_count")) or 0,
        "team_count": _to_int(payload.get("team_count")) or 0,
    }


def _fetch_nfl_intel_latest_availability(
    session: Any,
    *,
    endpoint: str,
    season: Optional[int] = None,
) -> _IntelAvailability:
    if endpoint == "stats":
        return _fetch_weekly_intel_availability(
            session,
            source_sql="SELECT season, week, team FROM nfl_dp_team_situational_weekly",
            season=season,
        )
    if endpoint == "standings":
        return _fetch_weekly_intel_availability(
            session,
            source_sql="SELECT season, week, team FROM nfl_dp_standings_weekly",
            season=season,
        )
    if endpoint == "depth-charts":
        return _fetch_weekly_intel_availability(
            session,
            source_sql="SELECT season, week, team FROM nfl_dp_depth_chart_weekly",
            season=season,
        )
    if endpoint == "injuries":
        return _fetch_weekly_intel_availability(
            session,
            source_sql="SELECT season, week, team FROM nfl_dp_injuries",
            season=season,
        )
    if endpoint == "rosters":
        row = session.execute(
            text(
                """
                WITH season_availability AS (
                  SELECT
                    season,
                    COUNT(*)::int AS row_count,
                    COUNT(DISTINCT team)::int AS team_count
                  FROM nfl_dp_rosters
                  WHERE (CAST(:season AS int) IS NULL OR season = CAST(:season AS int))
                  GROUP BY season
                )
                SELECT season, row_count, team_count
                FROM season_availability
                ORDER BY
                  CASE WHEN team_count >= 16 THEN 1 ELSE 0 END DESC,
                  season DESC,
                  team_count DESC,
                  row_count DESC
                LIMIT 1
                """
            ),
            {"season": season},
        ).fetchone()
        if row is None:
            return _empty_intel_availability()
        season_payload = dict(row._mapping)
        resolved_season = _to_int(season_payload.get("season"))
        weekly = _fetch_weekly_intel_availability(
            session,
            source_sql="""
                SELECT season, week, team FROM nfl_dp_team_situational_weekly
                UNION ALL
                SELECT season, week, team FROM nfl_dp_standings_weekly
                UNION ALL
                SELECT season, week, team FROM nfl_dp_depth_chart_weekly
                UNION ALL
                SELECT season, week, team FROM nfl_dp_injuries
            """,
            season=resolved_season,
        )
        return {
            "season": resolved_season,
            "week": weekly.get("week"),
            "row_count": _to_int(season_payload.get("row_count")) or 0,
            "team_count": _to_int(season_payload.get("team_count")) or 0,
        }
    return _empty_intel_availability()


INTEL_REQUIRED_TABLES: Dict[str, List[str]] = {
    "rosters": [
        "nfl_dp_rosters",
        "nfl_dp_depth_chart_weekly",
        "nfl_dp_injuries",
        "nfl_dp_team_situational_weekly",
        "nfl_dp_standings_weekly",
    ],
    "stats": ["nfl_dp_team_situational_weekly", "nfl_dp_standings_weekly"],
    "standings": ["nfl_dp_standings_weekly"],
    "depth-charts": ["nfl_dp_depth_chart_weekly"],
    "injuries": ["nfl_dp_injuries"],
}


def _fetch_intel_table_presence(session: Any, *, endpoint: str) -> Dict[str, Any]:
    required_tables = INTEL_REQUIRED_TABLES.get(endpoint, [])
    missing_tables: List[str] = []
    present_tables: List[str] = []
    for table in required_tables:
        regclass = session.execute(
            text("SELECT to_regclass(:qualified_name)"),
            {"qualified_name": f"public.{table}"},
        ).scalar_one_or_none()
        if regclass is None:
            missing_tables.append(table)
        else:
            present_tables.append(table)
    return {
        "required_tables": required_tables,
        "present_tables": present_tables,
        "missing_tables": missing_tables,
        "schema_ready": len(missing_tables) == 0,
    }


def _fetch_intel_source_mix(
    session: Any,
    *,
    endpoint: str,
    season: Optional[int],
    week: Optional[int],
) -> Dict[str, Any]:
    if endpoint == "rosters":
        rows = session.execute(
            text(
                """
                SELECT source, COUNT(*)::int AS row_count
                FROM nfl_dp_rosters
                WHERE (CAST(:season AS int) IS NULL OR season = CAST(:season AS int))
                GROUP BY source
                ORDER BY row_count DESC, source
                """
            ),
            {"season": season},
        ).fetchall()
    elif endpoint == "stats":
        rows = session.execute(
            text(
                """
                SELECT 'nfl_dp_team_situational_weekly'::text AS source, COUNT(*)::int AS row_count
                FROM nfl_dp_team_situational_weekly
                WHERE (CAST(:season AS int) IS NULL OR season = CAST(:season AS int))
                  AND (CAST(:week AS int) IS NULL OR week = CAST(:week AS int))
                GROUP BY 1
                ORDER BY row_count DESC, source
                """
            ),
            {"season": season, "week": week},
        ).fetchall()
    elif endpoint == "standings":
        rows = session.execute(
            text(
                """
                SELECT source, COUNT(*)::int AS row_count
                FROM nfl_dp_standings_weekly
                WHERE (CAST(:season AS int) IS NULL OR season = CAST(:season AS int))
                  AND (CAST(:week AS int) IS NULL OR week = CAST(:week AS int))
                GROUP BY source
                ORDER BY row_count DESC, source
                """
            ),
            {"season": season, "week": week},
        ).fetchall()
    elif endpoint == "injuries":
        rows = session.execute(
            text(
                """
                SELECT source, COUNT(*)::int AS row_count
                FROM nfl_dp_injuries
                WHERE (CAST(:season AS int) IS NULL OR season = CAST(:season AS int))
                  AND (CAST(:week AS int) IS NULL OR week = CAST(:week AS int))
                GROUP BY source
                ORDER BY row_count DESC, source
                """
            ),
            {"season": season, "week": week},
        ).fetchall()
    else:
        return {"active_source": None, "mix": []}

    mix = [
        {"source": str(r.source), "row_count": int(_to_int(r.row_count) or 0)}
        for r in rows
    ]
    active_source = mix[0]["source"] if mix else None
    return {"active_source": active_source, "mix": mix}


def _empty_intel_selection_metadata(
    *,
    season: Optional[int],
    week: Optional[int],
    team: Optional[str],
) -> Dict[str, Any]:
    resolved_team = str(team).strip().upper() if team else None
    resolved_season = int(season) if season is not None else None
    resolved_week = int(week) if week is not None else None
    return {
        "requested": {"season": season, "week": week, "team": resolved_team},
        "resolved": {"season": resolved_season, "week": resolved_week, "team": resolved_team},
        "used_default": {
            "season": season is None,
            "week": week is None,
            "any": season is None or week is None,
        },
        "latest_available": _empty_intel_availability(),
        "requested_availability": None,
        "fallback_applied": False,
    }


def _intel_unavailable_payload(
    *,
    endpoint: str,
    season: Optional[int],
    week: Optional[int],
    team: Optional[str],
    reason: str,
    diagnostics: Dict[str, Any],
) -> Dict[str, Any]:
    resolved_team = str(team).strip().upper() if team else None
    resolved_season = int(season) if season is not None else None
    resolved_week = int(week) if week is not None else None
    return {
        "season": resolved_season,
        "week": resolved_week,
        "team": resolved_team,
        "count": 0,
        "rows": [],
        "selection": _empty_intel_selection_metadata(season=season, week=week, team=team),
        "availability": {
            "status": "unavailable",
            "endpoint": endpoint,
            "reason": reason,
            "diagnostics": diagnostics,
        },
        "error": f"intel_data_unavailable:{reason}",
    }


def _handle_intel_data_access_error(
    *,
    session: Any,
    endpoint: str,
    season: Optional[int],
    week: Optional[int],
    team: Optional[str],
    exc: Exception,
) -> Dict[str, Any]:
    # SQL errors leave the transaction in an aborted state; rollback so
    # diagnostics queries can run and return structured intel payloads.
    try:
        session.rollback()
    except Exception:
        pass
    schema = _fetch_intel_table_presence(session, endpoint=endpoint)
    error_text = str(getattr(exc, "orig", exc) or exc)
    is_schema_error = (
        "undefinedtable" in error_text.lower()
        or "undefinedcolumn" in error_text.lower()
        or "does not exist" in error_text.lower()
        or not bool(schema.get("schema_ready"))
    )
    diagnostics = {
        "exception_type": exc.__class__.__name__,
        "error": error_text[:500],
        "schema": schema,
    }
    if is_schema_error:
        log.warning("NFL intel schema unavailable", extra={"endpoint": endpoint, "diagnostics": diagnostics})
        return _intel_unavailable_payload(
            endpoint=endpoint,
            season=season,
            week=week,
            team=team,
            reason="schema_not_ready",
            diagnostics=diagnostics,
        )
    log.exception("NFL intel query failed", extra={"endpoint": endpoint, "diagnostics": diagnostics})
    raise HTTPException(
        status_code=503,
        detail={
            "code": "intel_query_failed",
            "endpoint": endpoint,
            "message": "NFL intel query failed; inspect diagnostics for details.",
            "diagnostics": diagnostics,
        },
    )


def _fetch_nfl_intel_requested_availability(
    session: Any,
    *,
    endpoint: str,
    season: int,
    week: int,
) -> _IntelAvailability:
    if endpoint == "stats":
        return _fetch_weekly_intel_requested_availability(
            session,
            source_sql="SELECT season, week, team FROM nfl_dp_team_situational_weekly",
            season=season,
            week=week,
        )
    if endpoint == "standings":
        return _fetch_weekly_intel_requested_availability(
            session,
            source_sql="SELECT season, week, team FROM nfl_dp_standings_weekly",
            season=season,
            week=week,
        )
    if endpoint == "depth-charts":
        return _fetch_weekly_intel_requested_availability(
            session,
            source_sql="SELECT season, week, team FROM nfl_dp_depth_chart_weekly",
            season=season,
            week=week,
        )
    if endpoint == "injuries":
        return _fetch_weekly_intel_requested_availability(
            session,
            source_sql="SELECT season, week, team FROM nfl_dp_injuries",
            season=season,
            week=week,
        )
    if endpoint == "rosters":
        row = session.execute(
            text(
                """
                SELECT
                  :season AS season,
                  COUNT(*)::int AS row_count,
                  COUNT(DISTINCT team)::int AS team_count
                FROM nfl_dp_rosters
                WHERE season = :season
                """
            ),
            {"season": season},
        ).fetchone()
        payload = dict(row._mapping) if row is not None else {}
        return {
            "season": season,
            "week": week,
            "row_count": _to_int(payload.get("row_count")) or 0,
            "team_count": _to_int(payload.get("team_count")) or 0,
        }
    return {"season": season, "week": week, "row_count": 0, "team_count": 0}


def _resolve_nfl_intel_filters(
    session: Any,
    *,
    endpoint: str,
    season: Optional[int],
    week: Optional[int],
    team: Optional[str],
) -> tuple[int, int, Optional[str], Dict[str, Any]]:
    latest_all = _fetch_nfl_intel_latest_availability(session, endpoint=endpoint, season=None)
    latest_for_requested_season: Optional[_IntelAvailability] = None

    resolved_season = season
    if resolved_season is None:
        resolved_season = latest_all.get("season") or int(date.today().year)

    resolved_week = week
    if resolved_week is None:
        latest_for_requested_season = _fetch_nfl_intel_latest_availability(
            session,
            endpoint=endpoint,
            season=resolved_season,
        )
        resolved_week = latest_for_requested_season.get("week") or latest_all.get("week") or 1

    resolved_team = str(team).strip().upper() if team else None
    requested_has_data: Optional[bool] = None
    requested_availability: Optional[_IntelAvailability] = None
    if season is not None and week is not None:
        requested_availability = _fetch_nfl_intel_requested_availability(
            session,
            endpoint=endpoint,
            season=int(season),
            week=int(week),
        )
        requested_has_data = bool((requested_availability.get("row_count") or 0) > 0)

    metadata: Dict[str, Any] = {
        "requested": {"season": season, "week": week, "team": resolved_team},
        "resolved": {"season": int(resolved_season), "week": int(resolved_week), "team": resolved_team},
        "used_default": {
            "season": season is None,
            "week": week is None,
            "any": season is None or week is None,
        },
        "latest_available": {
            "season": latest_all.get("season"),
            "week": latest_all.get("week"),
            "row_count": latest_all.get("row_count"),
            "team_count": latest_all.get("team_count"),
        },
        "requested_availability": (
            {
                "season": requested_availability.get("season"),
                "week": requested_availability.get("week"),
                "row_count": requested_availability.get("row_count"),
                "team_count": requested_availability.get("team_count"),
                "has_data": requested_has_data,
            }
            if requested_availability is not None
            else None
        ),
        "fallback_applied": bool(
            (season is None or week is None)
            and latest_all.get("season") is not None
            and latest_all.get("week") is not None
            and (int(resolved_season) != int(latest_all.get("season")) or int(resolved_week) != int(latest_all.get("week")))
        ),
    }
    return int(resolved_season), int(resolved_week), resolved_team, metadata


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
                  c.rest_days_away,
                  c.context
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


# ---------------------------------------------------------------------------
# Real situational/tendency analytics (nfl_dp_team_situational_tendencies,
# nfl_dp_team_direction_tendencies, nfl_dp_qb_situational_splits -- built by
# services/data-platform-nfl/src/data_platform_nfl/tendency_profiles.py from
# real nflverse PBP). See docs/NFL_TENDENCY_ANALYTICS.md for full scope and
# honest limits (no coverage-scheme labels -- those do not exist in free
# nflverse/nflreadpy data).
# ---------------------------------------------------------------------------


@router.get("/tendencies/team")
def nfl_team_tendency_profile(
    season: int = Query(..., ge=2010, le=2100),
    team: str = Query(...),
    perspective: str = Query("offense", pattern="^(offense|defense)$"),
    situation_type: Optional[str] = Query(None, pattern="^(down_distance|score_state|field_position)$"),
) -> Dict[str, Any]:
    """Real, situational-bucket tendency profile for one team/season --
    down & distance, score state/game script, and field position splits
    (pass/run mix, shotgun/no-huddle rate, real xpass-relative
    pass-rate-over-expected, EPA, success rate, explosive-play rate, sack
    rate). `perspective=defense` returns what that team's defense
    faces/allows in the same situational buckets (the real matchup-ready
    "flip side")."""
    session = SessionLocal()
    try:
        rows = session.execute(
            text(
                """
                SELECT
                  season, team, perspective, situation_type, situation_bucket,
                  plays, pass_plays, rush_plays, pass_rate,
                  dropback_plays, dropback_rate, avg_xpass, pass_rate_over_expected,
                  shotgun_plays, shotgun_rate, no_huddle_plays, no_huddle_rate,
                  epa_per_play, success_rate, explosive_play_rate, sack_rate, computed_at
                FROM nfl_dp_team_situational_tendencies
                WHERE season = :season
                  AND team = :team
                  AND perspective = :perspective
                  AND (CAST(:situation_type AS text) IS NULL OR situation_type = CAST(:situation_type AS text))
                ORDER BY situation_type, situation_bucket
                """
            ),
            {"season": season, "team": team, "perspective": perspective, "situation_type": situation_type},
        ).fetchall()
        direction = session.execute(
            text(
                """
                SELECT
                  season, team, perspective,
                  pass_plays_with_location, pass_left_rate, pass_middle_rate, pass_right_rate,
                  run_plays_with_location, run_left_rate, run_middle_rate, run_right_rate,
                  run_plays_with_gap, run_end_rate, run_guard_rate, run_tackle_rate, computed_at
                FROM nfl_dp_team_direction_tendencies
                WHERE season = :season AND team = :team AND perspective = :perspective
                """
            ),
            {"season": season, "team": team, "perspective": perspective},
        ).fetchone()
        return {
            "season": season,
            "team": team,
            "perspective": perspective,
            "situational": [dict(r._mapping) for r in rows],
            "direction": dict(direction._mapping) if direction is not None else None,
        }
    finally:
        session.close()


@router.get("/tendencies/team-direction")
def nfl_team_direction_tendency(
    season: int = Query(..., ge=2010, le=2100),
    perspective: str = Query("offense", pattern="^(offense|defense)$"),
    team: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """Real pass-direction (left/middle/right) and run-direction/gap
    tendency by team, plus a `team=LEAGUE` league-average row for context.
    Omit `team` to fetch every team (including LEAGUE) for a season."""
    session = SessionLocal()
    try:
        rows = session.execute(
            text(
                """
                SELECT
                  season, team, perspective,
                  pass_plays_with_location, pass_left_rate, pass_middle_rate, pass_right_rate,
                  run_plays_with_location, run_left_rate, run_middle_rate, run_right_rate,
                  run_plays_with_gap, run_end_rate, run_guard_rate, run_tackle_rate, computed_at
                FROM nfl_dp_team_direction_tendencies
                WHERE season = :season
                  AND perspective = :perspective
                  AND (CAST(:team AS text) IS NULL OR team = CAST(:team AS text))
                ORDER BY (team = 'LEAGUE') DESC, team
                """
            ),
            {"season": season, "perspective": perspective, "team": team},
        ).fetchall()
        return {"count": len(rows), "rows": [dict(r._mapping) for r in rows]}
    finally:
        session.close()


@router.get("/tendencies/qb")
def nfl_qb_situational_splits(
    season: int = Query(..., ge=2010, le=2100),
    player_id: Optional[str] = Query(None),
    team: Optional[str] = Query(None),
    situation_type: Optional[str] = Query(
        None, pattern="^(overall|down_type|pressure|score_state|field_position)$"
    ),
    min_dropbacks: int = Query(0, ge=0, le=1000),
    limit: int = Query(500, ge=1, le=3000),
) -> Dict[str, Any]:
    """Real QB situational efficiency splits -- completion%, YPA, EPA/play,
    CPOE (completion% over nflfastR's own `cp` model), sack/INT/TD rate --
    broken out by down type (early vs. money down), pressure (real
    sack/qb_hit proxy) vs. clean pocket, score state, and field position.
    Provide at least one of `player_id` or `team` for a scoped, useful
    result; omitting both returns a season-wide (large) result set."""
    session = SessionLocal()
    try:
        rows = session.execute(
            text(
                """
                SELECT
                  season, player_id, player_name, team, situation_type, situation_bucket,
                  dropbacks, pass_attempts, completions, completion_rate, pass_yards,
                  yards_per_attempt, epa_per_play, success_rate, avg_cp, cpoe,
                  sacks, sack_rate, interceptions, interception_rate, passing_tds, td_rate, computed_at
                FROM nfl_dp_qb_situational_splits
                WHERE season = :season
                  AND (CAST(:player_id AS text) IS NULL OR player_id = CAST(:player_id AS text))
                  AND (CAST(:team AS text) IS NULL OR team = CAST(:team AS text))
                  AND (CAST(:situation_type AS text) IS NULL OR situation_type = CAST(:situation_type AS text))
                  AND dropbacks >= :min_dropbacks
                ORDER BY player_name, situation_type, situation_bucket
                LIMIT :limit
                """
            ),
            {
                "season": season,
                "player_id": player_id,
                "team": team,
                "situation_type": situation_type,
                "min_dropbacks": min_dropbacks,
                "limit": limit,
            },
        ).fetchall()
        return {"count": len(rows), "rows": [dict(r._mapping) for r in rows]}
    finally:
        session.close()


@router.get("/tendencies/matchup")
def nfl_tendency_matchup_breakdown(
    season: int = Query(..., ge=2010, le=2100),
    home_team: str = Query(...),
    away_team: str = Query(...),
) -> Dict[str, Any]:
    """Combined real matchup breakdown: each team's own offensive tendency
    (by situational bucket) next to the opponent's real defensive tendency
    allowed in that exact same bucket, for both sides of the matchup. This
    is the "break down every game" deliverable built entirely from real,
    honest situational splits -- not coverage-scheme labels (see
    docs/NFL_TENDENCY_ANALYTICS.md)."""
    session = SessionLocal()
    try:
        def _situational(team: str, perspective: str) -> List[Dict[str, Any]]:
            rows = session.execute(
                text(
                    """
                    SELECT situation_type, situation_bucket, plays, pass_rate,
                           pass_rate_over_expected, shotgun_rate, no_huddle_rate,
                           epa_per_play, success_rate, explosive_play_rate, sack_rate
                    FROM nfl_dp_team_situational_tendencies
                    WHERE season = :season AND team = :team AND perspective = :perspective
                    ORDER BY situation_type, situation_bucket
                    """
                ),
                {"season": season, "team": team, "perspective": perspective},
            ).fetchall()
            return [dict(r._mapping) for r in rows]

        def _direction(team: str, perspective: str) -> Optional[Dict[str, Any]]:
            row = session.execute(
                text(
                    """
                    SELECT pass_left_rate, pass_middle_rate, pass_right_rate,
                           run_left_rate, run_middle_rate, run_right_rate,
                           run_end_rate, run_guard_rate, run_tackle_rate
                    FROM nfl_dp_team_direction_tendencies
                    WHERE season = :season AND team = :team AND perspective = :perspective
                    """
                ),
                {"season": season, "team": team, "perspective": perspective},
            ).fetchone()
            return dict(row._mapping) if row is not None else None

        home_off = _situational(home_team, "offense")
        away_def = _situational(away_team, "defense")
        away_off = _situational(away_team, "offense")
        home_def = _situational(home_team, "defense")

        def _by_bucket(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
            return {f"{r['situation_type']}:{r['situation_bucket']}": r for r in rows}

        home_off_by_bucket = _by_bucket(home_off)
        away_def_by_bucket = _by_bucket(away_def)
        away_off_by_bucket = _by_bucket(away_off)
        home_def_by_bucket = _by_bucket(home_def)

        home_offense_vs_away_defense = [
            {"bucket": bucket, "home_offense": home_off_by_bucket[bucket], "away_defense_allowed": away_def_by_bucket.get(bucket)}
            for bucket in home_off_by_bucket
        ]
        away_offense_vs_home_defense = [
            {"bucket": bucket, "away_offense": away_off_by_bucket[bucket], "home_defense_allowed": home_def_by_bucket.get(bucket)}
            for bucket in away_off_by_bucket
        ]

        return {
            "season": season,
            "home_team": home_team,
            "away_team": away_team,
            "home_offense_vs_away_defense": home_offense_vs_away_defense,
            "away_offense_vs_home_defense": away_offense_vs_home_defense,
            "home_offense_direction": _direction(home_team, "offense"),
            "away_defense_direction_allowed": _direction(away_team, "defense"),
            "away_offense_direction": _direction(away_team, "offense"),
            "home_defense_direction_allowed": _direction(home_team, "defense"),
            "methodology_note": (
                "Real situational/direction tendency splits only -- no "
                "defensive coverage-scheme labels (Cover 2/3, man/zone) "
                "exist in free nflverse/nflreadpy PBP; pass_rate_over_expected "
                "is real but is a dropback-rate-vs-nflfastR's-own-xpass-model "
                "signal, not a verified play-call read."
            ),
        }
    finally:
        session.close()


@router.get("/intel/rosters")
def nfl_intel_rosters(
    season: Optional[int] = Query(None, ge=2010, le=2100),
    week: Optional[int] = Query(None, ge=1, le=25),
    team: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=5000),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        resolved_season, resolved_week, resolved_team, selection_metadata = _resolve_nfl_intel_filters(
            session,
            endpoint="rosters",
            season=season,
            week=week,
            team=team,
        )
        rows = session.execute(
            text(
                """
                SELECT
                  r.season,
                  CAST(:week AS int) AS week,
                  r.team,
                  r.player_id,
                  r.player_name,
                  r.position,
                  r.jersey_number,
                  r.source AS roster_source,
                  dc.depth_slot,
                  dc.depth_order,
                  dc.role_confidence,
                  i.report_status,
                  i.practice_status,
                  i.injury,
                  i.source AS injury_source
                FROM nfl_dp_rosters r
                LEFT JOIN nfl_dp_depth_chart_weekly dc
                  ON dc.season = r.season
                 AND dc.week = :week
                 AND dc.team = r.team
                 AND dc.player_id = r.player_id
                 AND dc.position = r.position
                LEFT JOIN nfl_dp_injuries i
                  ON i.season = r.season
                 AND i.week = :week
                 AND i.team = r.team
                 AND (
                   i.player_id = r.player_id
                   OR (i.player_id IS NULL AND i.player_name = r.player_name)
                 )
                WHERE r.season = :season
                  AND (CAST(:team AS text) IS NULL OR r.team = CAST(:team AS text))
                ORDER BY r.team, r.position, COALESCE(dc.depth_order, 999), r.player_name
                LIMIT :limit
                """
            ),
            {
                "season": resolved_season,
                "week": resolved_week,
                "team": resolved_team,
                "limit": limit,
            },
        ).fetchall()
        source_diagnostics = _fetch_intel_source_mix(
            session,
            endpoint="rosters",
            season=resolved_season,
            week=resolved_week,
        )
        return {
            "season": resolved_season,
            "week": resolved_week,
            "team": resolved_team,
            "count": len(rows),
            "rows": _serialize_intel_rows(rows),
            "selection": selection_metadata,
            "source_diagnostics": source_diagnostics,
        }
    except (ProgrammingError, OperationalError, SQLAlchemyError) as exc:
        return _handle_intel_data_access_error(
            session=session,
            endpoint="rosters",
            season=season,
            week=week,
            team=team,
            exc=exc,
        )
    finally:
        session.close()


@router.get("/intel/health")
def nfl_intel_health() -> Dict[str, Any]:
    session = SessionLocal()
    try:
        framework_cfg = get_nfl_handicapping_config()
        tuned_guardrails = framework_cfg["guardrails"]
        tuning_summary: Optional[Dict[str, Any]] = None
        try:
            tuning_summary = _fetch_latest_framework_tuning_summary(
                session,
                model_version=DEFAULT_NFL_MODEL_VERSION,
            )
            tuned_guardrails = _fetch_latest_tuned_guardrails(
                session,
                model_version=DEFAULT_NFL_MODEL_VERSION,
                fallback=framework_cfg["guardrails"],
            )
        except Exception:
            tuning_summary = None
        endpoints = ["rosters", "stats", "standings", "depth-charts", "injuries"]
        schema: Dict[str, Any] = {}
        for endpoint in endpoints:
            schema[endpoint] = _fetch_intel_table_presence(session, endpoint=endpoint)

        availability = {
            endpoint: _fetch_nfl_intel_latest_availability(session, endpoint=endpoint, season=None)
            for endpoint in endpoints
        }
        active_sources = {
            endpoint: _fetch_intel_source_mix(
                session,
                endpoint=endpoint,
                season=availability.get(endpoint, {}).get("season"),
                week=availability.get(endpoint, {}).get("week"),
            ).get("active_source")
            for endpoint in endpoints
            if endpoint != "depth-charts"
        }
        all_ready = all(bool(schema[endpoint]["schema_ready"]) for endpoint in endpoints)
        return {
            "status": "ok" if all_ready else "degraded",
            "framework": {
                "version": framework_cfg["framework_version"],
                "guardrails": framework_cfg["guardrails"],
                "effective_guardrails": tuned_guardrails,
                "tuning": {
                    "latest_run_id": tuning_summary.get("run_id") if isinstance(tuning_summary, dict) else None,
                    "latest_created_at": tuning_summary.get("created_at") if isinstance(tuning_summary, dict) else None,
                },
            },
            "schema": schema,
            "availability": availability,
            "active_sources": active_sources,
        }
    except (ProgrammingError, OperationalError, SQLAlchemyError) as exc:
        detail = {
            "code": "intel_health_unavailable",
            "message": "Unable to compute intel health due to database error.",
            "error": str(getattr(exc, "orig", exc) or exc)[:500],
        }
        raise HTTPException(status_code=503, detail=detail)
    finally:
        session.close()


@router.get("/intel/stats")
def nfl_intel_stats(
    season: Optional[int] = Query(None, ge=2010, le=2100),
    week: Optional[int] = Query(None, ge=1, le=25),
    team: Optional[str] = Query(None),
    limit: int = Query(128, ge=1, le=2000),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        resolved_season, resolved_week, resolved_team, selection_metadata = _resolve_nfl_intel_filters(
            session,
            endpoint="stats",
            season=season,
            week=week,
            team=team,
        )
        rows = session.execute(
            text(
                """
                SELECT
                  t.season,
                  t.week,
                  t.team,
                  t.games_played,
                  t.offensive_plays,
                  t.defensive_plays,
                  t.pass_rate,
                  t.early_down_pass_rate,
                  t.red_zone_td_rate,
                  t.pressure_rate_allowed,
                  t.pressure_rate_generated,
                  t.success_rate_offense,
                  t.success_rate_defense_allowed,
                  t.epa_per_play_offense,
                  t.epa_per_play_defense_allowed,
                  'nfl_dp_team_situational_weekly'::text AS stats_source,
                  s.wins,
                  s.losses,
                  s.ties,
                  s.points_for,
                  s.points_against,
                  s.point_diff,
                  s.win_pct,
                  s.source AS standings_source
                FROM nfl_dp_team_situational_weekly t
                LEFT JOIN nfl_dp_standings_weekly s
                  ON s.season = t.season
                 AND s.week = t.week
                 AND s.team = t.team
                WHERE t.season = :season
                  AND t.week = :week
                  AND (CAST(:team AS text) IS NULL OR t.team = CAST(:team AS text))
                ORDER BY t.team
                LIMIT :limit
                """
            ),
            {
                "season": resolved_season,
                "week": resolved_week,
                "team": resolved_team,
                "limit": limit,
            },
        ).fetchall()
        source_diagnostics = _fetch_intel_source_mix(
            session,
            endpoint="stats",
            season=resolved_season,
            week=resolved_week,
        )
        return {
            "season": resolved_season,
            "week": resolved_week,
            "team": resolved_team,
            "count": len(rows),
            "rows": _serialize_intel_rows(rows),
            "selection": selection_metadata,
            "source_diagnostics": source_diagnostics,
        }
    except (ProgrammingError, OperationalError, SQLAlchemyError) as exc:
        return _handle_intel_data_access_error(
            session=session,
            endpoint="stats",
            season=season,
            week=week,
            team=team,
            exc=exc,
        )
    finally:
        session.close()


@router.get("/intel/standings")
def nfl_intel_standings(
    season: Optional[int] = Query(None, ge=2010, le=2100),
    week: Optional[int] = Query(None, ge=1, le=25),
    team: Optional[str] = Query(None),
    limit: int = Query(128, ge=1, le=2000),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        resolved_season, resolved_week, resolved_team, selection_metadata = _resolve_nfl_intel_filters(
            session,
            endpoint="standings",
            season=season,
            week=week,
            team=team,
        )
        rows = session.execute(
            text(
                f"""
                WITH standings AS (
                  SELECT
                    season,
                    week,
                    team,
                    wins,
                    losses,
                    ties,
                    points_for,
                    points_against,
                    point_diff,
                    win_pct,
                    COALESCE(
                      NULLIF(UPPER(BTRIM(conference)), ''),
                      {NFL_TEAM_CONFERENCE_CASE_SQL},
                      'Unknown'
                    ) AS conference,
                    COALESCE(
                      NULLIF(INITCAP(LOWER(BTRIM(division))), ''),
                      {NFL_TEAM_DIVISION_CASE_SQL},
                      'Unknown'
                    ) AS division,
                    conference_wins,
                    conference_losses,
                    conference_ties,
                    conference_pct,
                    division_wins,
                    division_losses,
                    division_ties,
                    division_pct
                  FROM nfl_dp_standings_weekly
                  WHERE season = :season
                    AND week = :week
                    AND (CAST(:team AS text) IS NULL OR team = CAST(:team AS text))
                )
                SELECT
                  season, week, team, wins, losses, ties,
                  points_for, points_against, point_diff, win_pct,
                  conference, division,
                  conference_wins, conference_losses, conference_ties, conference_pct,
                  division_wins, division_losses, division_ties, division_pct
                FROM standings
                ORDER BY
                  CASE conference WHEN 'AFC' THEN 0 WHEN 'NFC' THEN 1 ELSE 2 END,
                  CASE division WHEN 'East' THEN 0 WHEN 'North' THEN 1 WHEN 'South' THEN 2 WHEN 'West' THEN 3 ELSE 4 END,
                  wins DESC NULLS LAST,
                  win_pct DESC NULLS LAST,
                  point_diff DESC NULLS LAST,
                  team ASC
                LIMIT :limit
                """
            ),
            {
                "season": resolved_season,
                "week": resolved_week,
                "team": resolved_team,
                "limit": limit,
            },
        ).fetchall()
        return {
            "season": resolved_season,
            "week": resolved_week,
            "team": resolved_team,
            "count": len(rows),
            "rows": _serialize_intel_rows(rows),
            "selection": selection_metadata,
        }
    except (ProgrammingError, OperationalError, SQLAlchemyError) as exc:
        return _handle_intel_data_access_error(
            session=session,
            endpoint="standings",
            season=season,
            week=week,
            team=team,
            exc=exc,
        )
    finally:
        session.close()


@router.get("/intel/depth-charts")
def nfl_intel_depth_charts(
    season: Optional[int] = Query(None, ge=2010, le=2100),
    week: Optional[int] = Query(None, ge=1, le=25),
    team: Optional[str] = Query(None),
    limit: int = Query(800, ge=1, le=5000),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        resolved_season, resolved_week, resolved_team, selection_metadata = _resolve_nfl_intel_filters(
            session,
            endpoint="depth-charts",
            season=season,
            week=week,
            team=team,
        )
        rows = session.execute(
            text(
                """
                SELECT
                  dc.season,
                  dc.week,
                  dc.team,
                  dc.position,
                  dc.depth_slot,
                  dc.depth_order,
                  dc.player_uid,
                  dc.player_id,
                  dc.player_name,
                  dc.role_confidence,
                  dc.inferred_source,
                  u.pass_yards,
                  u.pass_touchdowns,
                  u.rush_yards,
                  u.receptions,
                  u.receiving_yards,
                  u.touchdowns_scored,
                  p.pass_yards_mean,
                  p.rush_yards_mean,
                  p.receiving_yards_mean,
                  p.receptions_mean,
                  p.pass_tds_mean,
                  p.rush_tds_mean,
                  p.rec_tds_mean,
                  p.anytime_td_prob,
                  p.model_version AS projection_model_version,
                  f.expected_points AS fantasy_points_roy,
                  f.floor_points AS fantasy_floor_roy,
                  f.ceiling_points AS fantasy_ceiling_roy,
                  f.rank_position AS fantasy_rank_position_roy,
                  f.tier AS fantasy_tier_roy,
                  f.model_version AS fantasy_model_version,
                  f.scoring_profile AS fantasy_scoring_profile
                FROM nfl_dp_depth_chart_weekly dc
                LEFT JOIN nfl_dp_player_usage_weekly u
                  ON u.season = dc.season
                 AND u.week = dc.week
                 AND u.team = dc.team
                 AND u.player_id = dc.player_id
                LEFT JOIN LATERAL (
                  SELECT
                    pb.pass_yards_mean,
                    pb.rush_yards_mean,
                    pb.receiving_yards_mean,
                    pb.receptions_mean,
                    pb.pass_tds_mean,
                    pb.rush_tds_mean,
                    pb.rec_tds_mean,
                    pb.anytime_td_prob,
                    pb.model_version
                  FROM nfl_player_projection_baselines pb
                  WHERE pb.season = dc.season
                    AND pb.week = dc.week
                    AND pb.team = dc.team
                    AND pb.player_id = dc.player_id
                  ORDER BY CASE WHEN pb.model_version = 'nfl-player-v1' THEN 0 ELSE 1 END, pb.updated_at DESC
                  LIMIT 1
                ) p ON TRUE
                LEFT JOIN LATERAL (
                  SELECT
                    fp.expected_points,
                    fp.floor_points,
                    fp.ceiling_points,
                    fp.rank_position,
                    fp.tier,
                    fp.model_version,
                    fp.scoring_profile
                  FROM nfl_fantasy_weekly_projections fp
                  WHERE fp.season = dc.season
                    AND fp.week = dc.week
                    AND fp.team = dc.team
                    AND fp.player_id = dc.player_id
                  ORDER BY
                    CASE WHEN fp.scoring_profile = 'half_ppr' THEN 0 ELSE 1 END,
                    CASE WHEN fp.model_version = 'nfl-player-v1' THEN 0 ELSE 1 END,
                    fp.updated_at DESC
                  LIMIT 1
                ) f ON TRUE
                WHERE dc.season = :season
                  AND dc.week = :week
                  AND (CAST(:team AS text) IS NULL OR dc.team = CAST(:team AS text))
                ORDER BY
                  dc.team,
                  CASE
                    WHEN dc.position = 'QB' THEN 0
                    WHEN dc.position = 'RB' THEN 1
                    WHEN dc.position = 'WR' THEN 2
                    WHEN dc.position = 'TE' THEN 3
                    ELSE 10
                  END,
                  dc.position,
                  CASE
                    WHEN dc.depth_slot = 'starter' THEN 0
                    WHEN dc.depth_slot = 'backup' THEN 1
                    WHEN dc.depth_slot = 'rotation' THEN 2
                    WHEN dc.depth_slot = 'depth' THEN 3
                    ELSE 4
                  END,
                  dc.depth_order,
                  dc.player_name
                LIMIT :limit
                """
            ),
            {
                "season": resolved_season,
                "week": resolved_week,
                "team": resolved_team,
                "limit": limit,
            },
        ).fetchall()
        return {
            "season": resolved_season,
            "week": resolved_week,
            "team": resolved_team,
            "count": len(rows),
            "rows": _serialize_intel_rows(rows),
            "selection": selection_metadata,
        }
    except (ProgrammingError, OperationalError, SQLAlchemyError) as exc:
        return _handle_intel_data_access_error(
            session=session,
            endpoint="depth-charts",
            season=season,
            week=week,
            team=team,
            exc=exc,
        )
    finally:
        session.close()


@router.get("/intel/injuries")
def nfl_intel_injuries(
    season: Optional[int] = Query(None, ge=2010, le=2100),
    week: Optional[int] = Query(None, ge=1, le=25),
    team: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=5000),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        resolved_season, resolved_week, resolved_team, selection_metadata = _resolve_nfl_intel_filters(
            session,
            endpoint="injuries",
            season=season,
            week=week,
            team=team,
        )
        rows = session.execute(
            text(
                """
                SELECT
                  season, week, team, player_key, player_id, player_name,
                  report_status, practice_status, injury, updated_at
                FROM nfl_dp_injuries
                WHERE season = :season
                  AND week = :week
                  AND (CAST(:team AS text) IS NULL OR team = CAST(:team AS text))
                ORDER BY team, report_status DESC NULLS LAST, player_name
                LIMIT :limit
                """
            ),
            {
                "season": resolved_season,
                "week": resolved_week,
                "team": resolved_team,
                "limit": limit,
            },
        ).fetchall()
        return {
            "season": resolved_season,
            "week": resolved_week,
            "team": resolved_team,
            "count": len(rows),
            "rows": _serialize_intel_rows(rows),
            "selection": selection_metadata,
        }
    except (ProgrammingError, OperationalError, SQLAlchemyError) as exc:
        return _handle_intel_data_access_error(
            session=session,
            endpoint="injuries",
            season=season,
            week=week,
            team=team,
            exc=exc,
        )
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
                    "framework_version": payload.get("framework_version"),
                    "factor_attribution_diagnostics": payload.get("factor_attribution_diagnostics"),
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
                    "framework_version": payload.get("framework_version"),
                    "factor_attribution_diagnostics": payload.get("factor_attribution_diagnostics"),
                },
                "folds": payload.get("folds") if isinstance(payload.get("folds"), list) else [],
            },
        }
    finally:
        session.close()


@router.post("/ops/framework-tuning")
def nfl_trigger_framework_tuning(
    model_version: str = Query(DEFAULT_NFL_MODEL_VERSION),
    lookback_days: int = Query(240, ge=45, le=1460),
    training_days: int = Query(56, ge=14, le=365),
    step_days: int = Query(7, ge=1, le=30),
    max_candidates: int = Query(180, ge=12, le=1000),
) -> Dict[str, Any]:
    async_result = celery_app.send_task(
        TASK_NFL_FRAMEWORK_TUNING,
        kwargs={
            "model_version": model_version,
            "lookback_days": int(lookback_days),
            "training_days": int(training_days),
            "step_days": int(step_days),
            "max_candidates": int(max_candidates),
        },
    )
    return {
        "task_id": async_result.id,
        "task_name": TASK_NFL_FRAMEWORK_TUNING,
        "model_version": model_version,
        "lookback_days": int(lookback_days),
        "training_days": int(training_days),
        "step_days": int(step_days),
        "max_candidates": int(max_candidates),
    }


@router.get("/ops/framework-tuning/latest")
def nfl_framework_tuning_latest(
    model_version: str = Query(DEFAULT_NFL_MODEL_VERSION),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        row = session.execute(
            text(
                """
                SELECT id, run_date, model_version, payload, selected_config, created_at
                FROM nfl_framework_tuning_runs
                WHERE model_version = :model_version
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"model_version": model_version},
        ).fetchone()
        if row is None:
            return {"model_version": model_version, "latest": None}
        payload = row.payload if isinstance(row.payload, dict) else {}
        selected_config = row.selected_config if isinstance(row.selected_config, dict) else {}
        candidates = session.execute(
            text(
                """
                SELECT rank, score, metrics, candidate, config_overrides, is_recommended
                FROM nfl_framework_tuning_candidates
                WHERE run_id = :run_id
                ORDER BY rank ASC
                LIMIT 20
                """
            ),
            {"run_id": str(row.id)},
        ).fetchall()
        return {
            "model_version": model_version,
            "latest": {
                "run_id": str(row.id),
                "run_date": row.run_date,
                "created_at": row.created_at,
                "payload": payload,
                "selected_config": selected_config,
                "top_candidates": [dict(r._mapping) for r in candidates],
            },
        }
    finally:
        session.close()


@router.post("/ops/decomposition-drift")
def nfl_trigger_decomposition_drift(
    model_version: str = Query(DEFAULT_NFL_MODEL_VERSION),
    lookback_days: int = Query(120, ge=21, le=730),
    baseline_weeks: int = Query(4, ge=2, le=16),
) -> Dict[str, Any]:
    async_result = celery_app.send_task(
        TASK_NFL_DECOMPOSITION_DRIFT,
        kwargs={
            "model_version": model_version,
            "lookback_days": int(lookback_days),
            "baseline_weeks": int(baseline_weeks),
        },
    )
    return {
        "task_id": async_result.id,
        "task_name": TASK_NFL_DECOMPOSITION_DRIFT,
        "model_version": model_version,
        "lookback_days": int(lookback_days),
        "baseline_weeks": int(baseline_weeks),
    }


@router.get("/ops/decomposition-drift/latest")
def nfl_decomposition_drift_latest(
    model_version: str = Query(DEFAULT_NFL_MODEL_VERSION),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        row = session.execute(
            text(
                """
                SELECT snapshot_date, model_version, status, payload, created_at
                FROM nfl_decomposition_drift_snapshots
                WHERE model_version = :model_version
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"model_version": model_version},
        ).fetchone()
        if row is None:
            return {"model_version": model_version, "latest": None}
        payload = row.payload if isinstance(row.payload, dict) else {}
        return {
            "model_version": model_version,
            "latest": {
                "snapshot_date": row.snapshot_date,
                "status": row.status,
                "created_at": row.created_at,
                "payload": payload,
                "top_shifts": payload.get("top_shifts") if isinstance(payload.get("top_shifts"), list) else [],
            },
        }
    finally:
        session.close()


@router.get("/edges/today")
def nfl_edges_today(
    model_version: Optional[str] = Query(None),
    min_quality_score: Optional[float] = Query(None, ge=0.0, le=100.0),
    min_confidence_score: Optional[float] = Query(None, ge=0.0, le=1.0),
    min_ml_edge_prob: Optional[float] = Query(None, ge=0.0, le=0.25),
    bookmakers: Optional[str] = Query(
        None,
        description="Comma-separated The Odds API bookmaker keys. Defaults to NFL_ODDS_BOOKMAKERS or draftkings.",
    ),
) -> Dict[str, Any]:
    framework_cfg = get_nfl_handicapping_config()
    market_events: List[Dict[str, Any]] = []
    odds_feed_error: Optional[str] = None
    resolved_bookmakers = _resolve_nfl_odds_bookmakers(bookmakers)
    try:
        raw_market_events = fetch_odds(
            endpoint="sports/americanfootball_nfl/odds",
            params={
                "regions": "us",
                "markets": "h2h,totals",
                "oddsFormat": "american",
                "dateFormat": "iso",
                "bookmakers": resolved_bookmakers,
            },
        )
        if isinstance(raw_market_events, list):
            market_events = raw_market_events
    except Exception as exc:
        odds_feed_error = str(exc)[:500]
        log.warning("NFL odds feed unavailable for edges endpoint: %s", odds_feed_error)
    session = SessionLocal()
    tuned_guardrails = framework_cfg["guardrails"]
    tuning_summary: Optional[Dict[str, Any]] = None
    try:
        effective_model_version = model_version or _resolve_active_nfl_model_version(session)
        try:
            tuning_summary = _fetch_latest_framework_tuning_summary(
                session,
                model_version=effective_model_version,
            )
            tuned_guardrails = _fetch_latest_tuned_guardrails(
                session,
                model_version=effective_model_version,
                fallback=framework_cfg["guardrails"],
            )
        except Exception:
            tuned_guardrails = framework_cfg["guardrails"]
        rows = session.execute(
            text(
                """
                SELECT
                  g.id AS game_id,
                  g.start_time,
                  home.name AS home_team,
                  away.name AS away_team,
                  home.abbr AS home_abbr,
                  away.abbr AS away_abbr,
                  p.home_win_prob,
                  p.away_win_prob,
                  p.spread_home,
                  p.total_mean,
                  p.fair_home_ml,
                  p.fair_away_ml,
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
    except SQLAlchemyError as exc:
        diagnostics = {
            "code": "nfl_edges_schema_not_ready",
            "message": "NFL edges query failed due to database schema/runtime mismatch.",
            "database_error": str(exc)[:500],
            "bookmakers": resolved_bookmakers.split(","),
        }
        raise HTTPException(status_code=503, detail=diagnostics)
    finally:
        session.close()

    resolved_min_quality = float(min_quality_score) if min_quality_score is not None else float(tuned_guardrails["min_quality_score"])
    resolved_min_confidence = (
        float(min_confidence_score) if min_confidence_score is not None else float(tuned_guardrails["min_confidence_score"])
    )
    resolved_min_edge = float(min_ml_edge_prob) if min_ml_edge_prob is not None else float(tuned_guardrails["min_ml_edge_prob"])

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
    projection_by_abbr = {
        (
            _nfl_team_to_abbr(getattr(r, "home_abbr", None) or r.home_team) or "",
            _nfl_team_to_abbr(getattr(r, "away_abbr", None) or r.away_team) or "",
        ): dict(r._mapping)
        for r in rows
    }

    candidates: List[Dict[str, Any]] = []
    filtered_reasons: Dict[str, int] = {"quality_score": 0, "confidence_score": 0, "ml_edge_prob": 0}
    filtered_reason_codes: Dict[str, int] = {}
    filtered_examples: List[Dict[str, Any]] = []
    reason_compat_map = {
        "quality_score_below_threshold": "quality_score",
        "confidence_score_below_threshold": "confidence_score",
        "edge_prob_below_threshold": "ml_edge_prob",
    }

    for event in market_events if isinstance(market_events, list) else []:
        home_team = str(event.get("home_team") or "")
        away_team = str(event.get("away_team") or "")
        if not home_team or not away_team:
            continue
        home_abbr = _nfl_team_to_abbr(home_team)
        away_abbr = _nfl_team_to_abbr(away_team)
        proj = projection_by_key.get((_normalize_team_key(home_team), _normalize_team_key(away_team)))
        if proj is None and home_abbr and away_abbr:
            proj = projection_by_abbr.get((home_abbr, away_abbr))
        if proj is None:
            continue

        market_home_ml, market_away_ml, market_total, _market_spread_home, market_depth = _extract_book_market_prices(
            event
        )
        if market_home_ml is None or market_away_ml is None:
            continue

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
        decomposition_payload = (
            projection_payload.get("decomposition") if isinstance(projection_payload.get("decomposition"), dict) else {}
        )
        markets_payload = projection_payload.get("markets") if isinstance(projection_payload, dict) else {}
        markets_payload = markets_payload if isinstance(markets_payload, dict) else {}
        total_p10 = _to_float(markets_payload.get("total_p10"))
        total_p90 = _to_float(markets_payload.get("total_p90"))
        total_band_width = (
            abs((total_p90 or 0.0) - (total_p10 or 0.0))
            if total_p10 is not None and total_p90 is not None
            else 11.0
        )
        fallback_confidence = max(
            0.0,
            min(
                1.0,
                0.58 * min(1.0, abs(home_prob - 0.5) * 2.25)
                + 0.25 * min(1.0, market_depth / 14.0)
                + 0.17 * max(0.0, 1.0 - (total_band_width / 16.0)),
            ),
        )
        confidence_score = _to_float(decomposition_payload.get("confidence_score")) or fallback_confidence
        factor_coverage = _to_float(decomposition_payload.get("factor_coverage")) or 0.0
        uncertainty_payload = (
            decomposition_payload.get("uncertainty_penalties")
            if isinstance(decomposition_payload.get("uncertainty_penalties"), dict)
            else {}
        )
        uncertainty_penalty = _to_float(uncertainty_payload.get("total_penalty")) or max(0.0, min(0.35, total_band_width / 40.0))
        injury_diag = (
            projection_payload.get("diagnostics", {}).get("injury_nowcast")
            if isinstance(projection_payload.get("diagnostics"), dict)
            else {}
        )
        injury_freshness_hours = max(
            _to_float(injury_diag.get("home_freshness_hours")) or 0.0,
            _to_float(injury_diag.get("away_freshness_hours")) or 0.0,
        )
        quality_score_raw = (
            0.50 * base_quality
            + 23.0 * confidence_score
            + 14.0 * min(1.0, market_depth / 14.0)
            + 7.0 * min(1.0, abs(edge_prob) / 0.045)
            + 4.0 * factor_coverage
            - 13.0 * uncertainty_penalty
        )
        quality_score = round(
            max(
                0.0,
                min(
                    100.0,
                    quality_score_raw,
                ),
            ),
            1,
        )
        guardrails_eval = evaluate_nfl_edge_guardrails(
            edge_prob=edge_prob,
            quality_score=quality_score,
            confidence_score=confidence_score,
            uncertainty_penalty=uncertainty_penalty,
            factor_coverage=factor_coverage,
            injury_freshness_hours=injury_freshness_hours,
            min_quality_score=resolved_min_quality,
            min_confidence_score=resolved_min_confidence,
            min_ml_edge_prob=resolved_min_edge,
            max_uncertainty_penalty=_to_float(tuned_guardrails.get("max_uncertainty_penalty")),
            min_factor_coverage=_to_float(tuned_guardrails.get("min_factor_coverage")),
        )
        if not bool(guardrails_eval.get("eligible")):
            reason_codes = guardrails_eval.get("reason_codes") if isinstance(guardrails_eval.get("reason_codes"), list) else []
            for code in reason_codes:
                key = str(code)
                filtered_reason_codes[key] = filtered_reason_codes.get(key, 0) + 1
                compat = reason_compat_map.get(key)
                if compat:
                    filtered_reasons[compat] = filtered_reasons.get(compat, 0) + 1
            filtered_examples.append(
                {
                    "game_id": proj.get("game_id"),
                    "home_team": home_team,
                    "away_team": away_team,
                    "reason_codes": reason_codes,
                    "quality_score": quality_score,
                    "confidence_score": round(confidence_score, 4),
                    "ml_edge_prob": round(edge_prob, 4),
                }
            )
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
                "spread_home": _to_float(proj.get("spread_home")),
                "fair_home_ml": _to_int(proj.get("fair_home_ml")),
                "fair_away_ml": _to_int(proj.get("fair_away_ml")),
                "total_mean": _to_float(proj.get("total_mean")),
                "total_band_width": round(total_band_width, 3) if total_band_width is not None else None,
                "market_depth": market_depth,
                "quality_score": quality_score,
                "confidence_score": round(confidence_score, 4),
                "framework_version": str(
                    decomposition_payload.get("framework_version") or framework_cfg.get("framework_version")
                ),
                "decomposition": decomposition_payload if isinstance(decomposition_payload, dict) else {},
                "edge_metrics": {
                    "home_ml_prob_edge": round(edge_prob, 4),
                    "total_points_edge": (
                        round((_to_float(proj.get("total_mean")) or 0.0) - float(market_total), 3)
                        if market_total is not None
                        else None
                    ),
                    "market_home_prob_with_vig": round(market_home_prob, 4) if market_home_prob is not None else None,
                    "market_home_prob_no_vig": round(no_vig_prob, 4) if no_vig_prob is not None else None,
                },
                "guardrails": guardrails_eval,
            }
        )

    candidates = sorted(candidates, key=lambda item: (float(item["quality_score"]), abs(float(item["ml_edge_prob"]))), reverse=True)
    filtered_count = int(sum(filtered_reasons.values()))
    return {
        "model_version": effective_model_version,
        "count": len(candidates),
        "edges": candidates,
        "gating": {
            "min_quality_score": resolved_min_quality,
            "min_confidence_score": resolved_min_confidence,
            "min_ml_edge_prob": resolved_min_edge,
        },
        "diagnostics": {
            "filtered_count": filtered_count,
            "filtered_reasons": filtered_reasons,
            "filtered_reason_codes": filtered_reason_codes,
            "filtered_examples": filtered_examples[:25],
            "base_quality_score": round(base_quality, 2),
            "tuning_latest_run_id": tuning_summary.get("run_id") if isinstance(tuning_summary, dict) else None,
            "odds_feed_status": "degraded" if odds_feed_error else "ok",
            "odds_feed_error": odds_feed_error,
            "odds_events_seen": len(market_events),
            "bookmakers": resolved_bookmakers.split(","),
        },
        "framework": {
            "version": framework_cfg["framework_version"],
            "guardrails": framework_cfg["guardrails"],
            "effective_guardrails": tuned_guardrails,
        },
    }


@router.get("/fair-lines")
def nfl_fair_lines(
    season: int = Query(2026, ge=2010, le=2100),
    days_ahead: int = Query(14, ge=1, le=365),
    include_past_days: int = Query(0, ge=0, le=60),
    model_version: Optional[str] = Query(None),
    bookmakers: Optional[str] = Query(
        None,
        description="Comma-separated The Odds API bookmaker keys. Defaults to NFL_ODDS_BOOKMAKERS or draftkings.",
    ),
) -> Dict[str, Any]:
    """Kosedge fair-lines board for an upcoming (and optionally recent) slate.

    Returns latest LATERAL projection per game with optional live market
    comparison. If the odds feed is unavailable, Kosedge lines are still returned
    with market fields set to null.
    """
    market_events: List[Dict[str, Any]] = []
    odds_feed_error: Optional[str] = None
    resolved_bookmakers = _resolve_nfl_odds_bookmakers(bookmakers)
    try:
        raw_market_events = fetch_odds(
            endpoint="sports/americanfootball_nfl/odds",
            params={
                "regions": "us",
                "markets": "h2h,spreads,totals",
                "oddsFormat": "american",
                "dateFormat": "iso",
                "bookmakers": resolved_bookmakers,
            },
        )
        if isinstance(raw_market_events, list):
            market_events = raw_market_events
    except Exception as exc:
        odds_feed_error = str(exc)[:500]
        log.warning("NFL odds feed unavailable for fair-lines endpoint: %s", odds_feed_error)

    session = SessionLocal()
    try:
        effective_model_version = model_version or _resolve_active_nfl_model_version(session)
        rows = session.execute(
            text(
                """
                SELECT
                  g.id AS game_id,
                  g.start_time,
                  g.game_date,
                  s.season_year AS season,
                  home.name AS home_team,
                  home.abbr AS home_abbr,
                  away.name AS away_team,
                  away.abbr AS away_abbr,
                  p.home_win_prob,
                  p.away_win_prob,
                  p.spread_home,
                  p.total_mean,
                  p.fair_home_ml,
                  p.fair_away_ml,
                  p.model_version,
                  p.simulation_count,
                  p.created_at AS projection_created_at
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
                  AND s.season_year = :season
                  AND COALESCE(g.start_time, g.game_date::timestamptz) IS NOT NULL
                  AND COALESCE(g.start_time, g.game_date::timestamptz)
                      >= (NOW() - CAST(:include_past_days AS integer) * INTERVAL '1 day')
                  AND COALESCE(g.start_time, g.game_date::timestamptz)
                      <= (NOW() + CAST(:days_ahead AS integer) * INTERVAL '1 day')
                ORDER BY COALESCE(g.start_time, g.game_date::timestamptz) ASC NULLS LAST
                """
            ),
            {
                "season": season,
                "model_version": effective_model_version,
                "days_ahead": days_ahead,
                "include_past_days": include_past_days,
            },
        ).fetchall()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "nfl_fair_lines_schema_not_ready",
                "message": "NFL fair-lines query failed due to database schema/runtime mismatch.",
                "database_error": str(exc)[:500],
            },
        )
    finally:
        session.close()

    market_by_abbr: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for event in market_events:
        home_abbr = _nfl_team_to_abbr(str(event.get("home_team") or ""))
        away_abbr = _nfl_team_to_abbr(str(event.get("away_team") or ""))
        if not home_abbr or not away_abbr:
            continue
        market_home_ml, market_away_ml, market_total, market_spread_home, market_depth = _extract_book_market_prices(
            event
        )
        market_by_abbr[(home_abbr, away_abbr)] = {
            "market_home_ml": market_home_ml,
            "market_away_ml": market_away_ml,
            "market_total": market_total,
            "market_spread_home": market_spread_home,
            "market_depth": market_depth,
            "odds_home_team": event.get("home_team"),
            "odds_away_team": event.get("away_team"),
        }

    lines: List[Dict[str, Any]] = []
    market_joined_count = 0
    for row in rows:
        mapped = dict(row._mapping)
        home_abbr = _nfl_team_to_abbr(mapped.get("home_abbr") or mapped.get("home_team")) or str(
            mapped.get("home_abbr") or mapped.get("home_team") or ""
        )
        away_abbr = _nfl_team_to_abbr(mapped.get("away_abbr") or mapped.get("away_team")) or str(
            mapped.get("away_abbr") or mapped.get("away_team") or ""
        )
        home_win_prob = _to_float(mapped.get("home_win_prob"))
        away_win_prob = _to_float(mapped.get("away_win_prob"))
        if away_win_prob is None and home_win_prob is not None:
            away_win_prob = max(0.0, min(1.0, 1.0 - home_win_prob))

        market = market_by_abbr.get((home_abbr, away_abbr), {})
        market_home_ml = market.get("market_home_ml")
        market_away_ml = market.get("market_away_ml")
        market_total = market.get("market_total")
        market_spread_home = market.get("market_spread_home")
        has_market = any(v is not None for v in (market_home_ml, market_away_ml, market_total, market_spread_home))
        if has_market:
            market_joined_count += 1

        spread_home = _to_float(mapped.get("spread_home"))
        total_mean = _to_float(mapped.get("total_mean"))
        ml_edge_prob = None
        total_edge = None
        spread_edge = None
        market_home_prob_no_vig = None
        if market_home_ml is not None and market_away_ml is not None and home_win_prob is not None:
            market_home_prob = _american_implied_prob(int(market_home_ml))
            market_away_prob = _american_implied_prob(int(market_away_ml))
            if market_home_prob is not None and market_away_prob is not None and (market_home_prob + market_away_prob) > 0:
                market_home_prob_no_vig = market_home_prob / (market_home_prob + market_away_prob)
                ml_edge_prob = round(home_win_prob - market_home_prob_no_vig, 4)
        if market_total is not None and total_mean is not None:
            total_edge = round(total_mean - float(market_total), 3)
        if market_spread_home is not None and spread_home is not None:
            spread_edge = round(spread_home - float(market_spread_home), 3)

        home_display = NFL_ABBR_TO_FULL_NAME.get(home_abbr, str(mapped.get("home_team") or home_abbr))
        away_display = NFL_ABBR_TO_FULL_NAME.get(away_abbr, str(mapped.get("away_team") or away_abbr))

        lines.append(
            {
                "game_id": str(mapped.get("game_id")),
                "season": int(mapped.get("season") or season),
                "start_time": mapped.get("start_time"),
                "game_date": mapped.get("game_date"),
                "home_team": home_display,
                "away_team": away_display,
                "home_abbr": home_abbr,
                "away_abbr": away_abbr,
                "home_win_prob": round(home_win_prob, 4) if home_win_prob is not None else None,
                "away_win_prob": round(away_win_prob, 4) if away_win_prob is not None else None,
                "spread_home": round(spread_home, 2) if spread_home is not None else None,
                "total_mean": round(total_mean, 2) if total_mean is not None else None,
                "fair_home_ml": _to_int(mapped.get("fair_home_ml")),
                "fair_away_ml": _to_int(mapped.get("fair_away_ml")),
                "model_version": str(mapped.get("model_version") or effective_model_version),
                "simulation_count": _to_int(mapped.get("simulation_count")),
                "projection_created_at": mapped.get("projection_created_at"),
                "market_home_ml": market_home_ml,
                "market_away_ml": market_away_ml,
                "market_total": market_total,
                "market_spread_home": market_spread_home,
                "market_home_prob_no_vig": (
                    round(market_home_prob_no_vig, 4) if market_home_prob_no_vig is not None else None
                ),
                "ml_edge_prob": ml_edge_prob,
                "total_edge": total_edge,
                "spread_edge": spread_edge,
                "market_joined": has_market,
            }
        )

    return {
        "season": season,
        "model_version": effective_model_version,
        "count": len(lines),
        "lines": lines,
        "window": {
            "days_ahead": days_ahead,
            "include_past_days": include_past_days,
        },
        "diagnostics": {
            "odds_feed_status": "degraded" if odds_feed_error else ("ok" if market_events else "empty"),
            "odds_feed_error": odds_feed_error,
            "odds_events_seen": len(market_events),
            "market_joined_count": market_joined_count,
            "bookmakers": resolved_bookmakers.split(","),
            "kosedge_only": market_joined_count == 0,
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
        context_payload = m.get("context") if isinstance(m.get("context"), dict) else {}
        if not context_payload and isinstance(m.get("context"), str):
            try:
                context_payload = __import__("json").loads(str(m.get("context")))
            except Exception:
                context_payload = {}
        environment_payload = (
            context_payload.get("environment") if isinstance(context_payload.get("environment"), dict) else {}
        )
        weather_payload = environment_payload.get("weather") if isinstance(environment_payload.get("weather"), dict) else {}
        travel_payload = environment_payload.get("travel") if isinstance(environment_payload.get("travel"), dict) else {}
        matchup_kwargs = matchup_pack_to_sim_input_kwargs(matchup_pack)
        inputs = NflGameInputs(
            game_id=str(m["game_id"]),
            home_team=str(m["home_team"]),
            away_team=str(m["away_team"]),
            offense_index_home=(_to_float(m.get("offense_index_home")) or 1.0)
            * (_to_float(home_nowcast.get("offense_multiplier")) or 1.0),
            offense_index_away=(_to_float(m.get("offense_index_away")) or 1.0)
            * (_to_float(away_nowcast.get("offense_multiplier")) or 1.0),
            # See the matching comment in tasks.py::run_nfl_market_simulations --
            # defense_index is "higher = stronger defense", so a
            # defense_multiplier documented as "higher = weaker defense"
            # (injury/roster-continuity nowcast) must be applied as a
            # divisor, not a multiplier.
            defense_index_home=(_to_float(m.get("defense_index_home")) or 1.0)
            / (_to_float(home_nowcast.get("defense_multiplier")) or 1.0),
            defense_index_away=(_to_float(m.get("defense_index_away")) or 1.0)
            / (_to_float(away_nowcast.get("defense_multiplier")) or 1.0),
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
            weather_available=bool(weather_payload.get("available")),
            weather_wind_mph=_to_float(weather_payload.get("wind_mph")),
            weather_precip_mm=_to_float(weather_payload.get("precip_mm")),
            weather_temp_f=_to_float(weather_payload.get("temp_f")),
            weather_source=str(weather_payload.get("source") or "open-meteo"),
            travel_available=bool(travel_payload.get("available")),
            travel_miles_home=_to_float(travel_payload.get("travel_miles_home")),
            travel_miles_away=_to_float(travel_payload.get("travel_miles_away")),
            travel_timezone_delta_home=_to_float(travel_payload.get("timezone_delta_home")),
            travel_timezone_delta_away=_to_float(travel_payload.get("timezone_delta_away")),
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
                  AND (CAST(:market_key AS text) IS NULL OR market_key = CAST(:market_key AS text))
                  AND (CAST(:team AS text) IS NULL OR team = CAST(:team AS text))
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
        serialized = [dict(r._mapping) for r in rows]
        with_market = sum(
            1
            for row in serialized
            if row.get("market_over_price") is not None or row.get("market_under_price") is not None
        )
        return {
            "count": len(serialized),
            "rows": serialized,
            "diagnostics": {
                "market_joined_count": with_market,
                "kosedge_only": with_market == 0 and len(serialized) > 0,
            },
        }
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


@router.get("/fantasy/draft-rankings")
def nfl_fantasy_draft_rankings(
    season: int = Query(..., ge=2010, le=2100),
    scoring_profile: str = Query("half_ppr", pattern="^(standard|half_ppr|ppr)$"),
    model_version: str = Query("nfl-player-v1"),
    position: Optional[str] = Query(None),
    tier: Optional[str] = Query(None),
    rookies_only: bool = Query(False),
    limit: int = Query(300, ge=1, le=3000),
) -> Dict[str, Any]:
    """SEASON-LONG fantasy draft board (distinct from `/fantasy/rankings`,
    which is a single week's start/sit ranking) -- one row per player summed
    across the whole real projected season, with overall rank, position
    rank, draft tier, and a rookie flag. See
    `nfl_fantasy_season_draft_rankings` / `materialize_nfl_fantasy_season_draft_rankings`."""
    session = SessionLocal()
    try:
        rows = session.execute(
            text(
                """
                SELECT
                  season, scoring_profile, model_version, player_id, player_uid, player_name, team, position,
                  games_projected, pass_yards_total, rush_yards_total, receiving_yards_total, receptions_total,
                  pass_tds_total, rush_tds_total, rec_tds_total,
                  field_goals_made_total, field_goals_attempted_total, extra_points_made_total,
                  points_allowed_total, sacks_total, def_interceptions_total, fumble_recoveries_total,
                  defensive_tds_total, safeties_total,
                  total_points, replacement_points, value_over_replacement,
                  rank_overall, rank_position, tier, is_rookie, rookie_year, draft_number, updated_at
                FROM nfl_fantasy_season_draft_rankings
                WHERE season = :season
                  AND scoring_profile = :scoring_profile
                  AND model_version = :model_version
                  AND (CAST(:position AS text) IS NULL OR position = CAST(:position AS text))
                  AND (CAST(:tier AS text) IS NULL OR tier = CAST(:tier AS text))
                  AND (CAST(:rookies_only AS boolean) = FALSE OR is_rookie = TRUE)
                ORDER BY rank_overall
                LIMIT :limit
                """
            ),
            {
                "season": season,
                "scoring_profile": scoring_profile,
                "model_version": model_version,
                "position": position,
                "tier": tier,
                "rookies_only": rookies_only,
                "limit": limit,
            },
        ).fetchall()
        return {"count": len(rows), "rows": [dict(r._mapping) for r in rows]}
    finally:
        session.close()


@router.get("/awards/projections")
def nfl_award_projections_board(
    season: int = Query(..., ge=2010, le=2100),
    award: Optional[str] = Query(None, pattern="^(mvp|opoy)$"),
    model_version: str = Query("nfl-player-v1"),
    limit: int = Query(20, ge=1, le=50),
) -> Dict[str, Any]:
    """MVP / Offensive Player of the Year contender leaderboard. Each row
    carries the supporting projected stats (team win total, division-title
    probability, passing/rushing/receiving yards+TDs) and the intermediate
    `team_success_score` / `stat_composite` terms behind `award_score`, so the
    ranking is inspectable rather than a bare name+score. See
    `services/model-service/src/services/nfl_award_projections.py` for the
    full weighting methodology."""
    session = SessionLocal()
    try:
        rows = session.execute(
            text(
                """
                SELECT
                  season, award, model_version, player_id, player_uid, player_name, team, position,
                  rank_overall, award_score, team_success_score, stat_composite,
                  team_expected_wins, team_division_title_prob, team_playoff_prob,
                  pass_yards_total, rush_yards_total, receiving_yards_total,
                  pass_tds_total, rush_tds_total, rec_tds_total, methodology_payload, updated_at
                FROM nfl_award_projections
                WHERE season = :season
                  AND model_version = :model_version
                  AND (CAST(:award AS text) IS NULL OR award = CAST(:award AS text))
                ORDER BY award, rank_overall
                LIMIT :limit
                """
            ),
            {"season": season, "model_version": model_version, "award": award, "limit": limit},
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


@router.post("/ops/materialize-fantasy-draft-rankings")
def nfl_trigger_fantasy_draft_rankings_materialization(
    season: int = Query(..., ge=2010, le=2100),
    model_version: str = Query("nfl-player-v1"),
) -> Dict[str, Any]:
    task = celery_app.send_task(
        TASK_NFL_FANTASY_DRAFT_RANKINGS,
        kwargs={"season": int(season), "model_version": model_version},
    )
    return {"task_id": task.id, "task_name": TASK_NFL_FANTASY_DRAFT_RANKINGS, "season": season, "model_version": model_version}


@router.post("/ops/materialize-award-projections")
def nfl_trigger_award_projections_materialization(
    season: int = Query(..., ge=2010, le=2100),
    model_version: str = Query("nfl-player-v1"),
    top_n: int = Query(10, ge=1, le=25),
) -> Dict[str, Any]:
    task = celery_app.send_task(
        TASK_NFL_AWARD_PROJECTIONS,
        kwargs={"season": int(season), "model_version": model_version, "top_n": int(top_n)},
    )
    return {"task_id": task.id, "task_name": TASK_NFL_AWARD_PROJECTIONS, "season": season, "model_version": model_version}


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
