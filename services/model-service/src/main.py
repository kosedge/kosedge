from __future__ import annotations

import logging
import os
from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.celery_app import celery_app, celery_healthcheck
from src.db import engine
from src.routes import edge_board_router, mlb_router, nba_router, nfl_router
from src.services.nba_possession_simulator import DEFAULT_NBA_MODEL_VERSION
from src.services.nfl_simulator import DEFAULT_NFL_MODEL_VERSION

APP_NAME: str = os.getenv("APP_NAME", "kosedge")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger(APP_NAME)

TASK_PULL_ODDS_SNAPSHOT = "src.tasks.pull_odds_snapshot"
TASK_PULL_HISTORICAL_ODDS_BACKFILL = "src.tasks.pull_historical_odds_backfill"
TASK_PULL_MLB_CONTEXT = "src.tasks.pull_mlb_context_snapshot"
TASK_RUN_MLB_SIMULATIONS = "src.tasks.run_mlb_market_simulations"
TASK_PULL_MLB_OUTCOMES = "src.tasks.pull_mlb_outcomes"
TASK_PULL_MLB_DATA_LAKE = "src.tasks.pull_mlb_data_lake_snapshot"
TASK_PULL_NBA_CONTEXT = "src.tasks.pull_nba_context_snapshot"
TASK_RUN_NBA_SIMULATIONS = "src.tasks.run_nba_market_simulations"
TASK_PULL_NBA_INGEST = "src.tasks.pull_nba_schedule_ingest"
TASK_PULL_NBA_SEASON_INGEST = "src.tasks.pull_nba_season_ingest"
TASK_NBA_ROLLING_FEATURES = "src.tasks.materialize_nba_team_rolling_features"
TASK_NBA_ODDS_DENSIFY = "src.tasks.pull_nba_historical_odds_densify"
TASK_NBA_WALKFORWARD = "src.tasks.run_nba_walkforward_sample"
TASK_NBA_PHASE1_BOOTSTRAP = "src.tasks.run_nba_phase1_bootstrap"
TASK_NBA_INVENTORY = "src.tasks.nba_db_inventory"
TASK_PULL_NFL_CONTEXT = "src.tasks.pull_nfl_context_snapshot"
TASK_RUN_NFL_SIMULATIONS = "src.tasks.run_nfl_market_simulations"
TASK_BACKFILL_NFL_HISTORICAL_PROJECTIONS = "src.tasks.backfill_nfl_historical_projections"
TASK_MATERIALIZE_NFL_MARKET_HISTORY = "src.tasks.materialize_nfl_market_history"
TASK_RUN_NFL_CLV_ATTRIBUTION = "src.tasks.run_nfl_clv_attribution"
TASK_PULL_NFL_OUTCOMES = "src.tasks.pull_nfl_outcomes"
TASK_RUN_NFL_QUALITY_GRADING = "src.tasks.run_nfl_quality_grading"
TASK_RUN_NFL_WALKFORWARD_BACKTEST = "src.tasks.run_nfl_walkforward_backtest"
TASK_EVAL_NFL_PROMOTION = "src.tasks.evaluate_nfl_model_promotion"
TASK_RUN_NFL_FRAMEWORK_TUNING = "src.tasks.run_nfl_framework_tuning"
TASK_RUN_NFL_SUPERVISED_RETRAIN = "src.tasks.run_nfl_supervised_retrain"
TASK_RUN_NFL_DECOMPOSITION_DRIFT = "src.tasks.run_nfl_decomposition_drift_monitor"
TASK_RUN_NFL_LAUNCH_HARDENING = "src.tasks.run_nfl_launch_hardening_cycle"
TASK_NFL_PLAYER_BASELINES = "src.tasks.materialize_nfl_player_baseline_projections"
TASK_NFL_PLAYER_PROPS = "src.tasks.materialize_nfl_player_props_edges"
TASK_NFL_PLAYER_FEATURES = "src.tasks.materialize_nfl_player_projection_features"
TASK_NFL_PLAYER_BOX_SIMS = "src.tasks.materialize_nfl_player_box_score_sims"
TASK_NFL_PROPS_LAYER_REBUILD = "src.tasks.run_nfl_props_layer_rebuild"
TASK_NFL_FANTASY = "src.tasks.materialize_nfl_fantasy_projections"
TASK_NFL_PLAYER_CYCLE = "src.tasks.run_nfl_player_projection_cycle"
TASK_NFL_PLAYER_PROP_MARKETS = "src.tasks.pull_nfl_player_prop_market_snapshots"
TASK_NFL_IDENTITY_REFRESH = "src.tasks.run_nfl_identity_refresh"
TASK_NFL_IDENTITY_MANUAL_RESOLUTIONS = "src.tasks.apply_nfl_identity_manual_resolutions"
TASK_NFL_IDENTITY_QUALITY_SNAPSHOT = "src.tasks.run_nfl_identity_quality_snapshot"
TASK_RUN_MLB_DAILY_CYCLE = "src.tasks.run_mlb_daily_cycle"
TASK_EVAL_MLB_PROMOTION = "src.tasks.evaluate_mlb_model_promotion"
TASK_MLB_NOWCAST_REPRICING = "src.tasks.run_mlb_lineup_nowcast_repricing"
TASK_MLB_WALKFORWARD_BACKTEST = "src.tasks.run_mlb_walkforward_backtest"
TASK_MLB_FEATURE_ABLATION = "src.tasks.run_mlb_feature_ablation"
TASK_MLB_DETERMINISM_CHECK = "src.tasks.run_mlb_determinism_check"
TASK_MLB_HISTORICAL_ODDS_DENSIFY = "src.tasks.pull_mlb_historical_odds_densify"
TASK_MLB_CLV_ATTRIBUTION = "src.tasks.run_mlb_clv_attribution"
TASK_MLB_QUALITY_GRADING = "src.tasks.run_mlb_quality_grading"
TASK_MLB_HISTORICAL_RESIM = "src.tasks.backfill_mlb_historical_resim"
MLB_MODEL_STATE_KEY = "mlb_active_model"


def _parse_cors_origins(raw: str) -> List[str]:
    raw = (raw or "").strip()
    if not raw:
        return []
    return [o.strip() for o in raw.split(",") if o.strip()]


def _resolve_cors_settings() -> tuple[List[str], bool]:
    env_name = os.getenv("ENV", os.getenv("NODE_ENV", "development")).strip().lower()
    is_production = env_name == "production"
    origins = _parse_cors_origins(os.getenv("CORS_ORIGINS", ""))

    if not origins:
        if is_production:
            raise RuntimeError("CORS_ORIGINS must be set in production")
        origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

    if "*" in origins and len(origins) > 1:
        raise RuntimeError("CORS_ORIGINS cannot mix '*' with explicit origins")

    # FastAPI/Starlette disallow credentials with wildcard origin.
    allow_credentials = "*" not in origins
    return origins, allow_credentials


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


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return bool(default)
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _resolve_nfl_readiness_policy(*, default_max_last_game_age_days: int) -> Dict[str, Any]:
    mode_raw = str(os.getenv("NFL_READINESS_MODE", "production")).strip().lower()
    mode = mode_raw if mode_raw in {"production", "staging"} else "production"
    effective_max_last_game_age_days = int(default_max_last_game_age_days)
    freshness_gate_enabled = True
    override_active = False
    override_reason = "strict-default"

    if mode == "staging":
        if _env_bool("NFL_READINESS_STAGING_DISABLE_FRESHNESS_GATE", default=False):
            freshness_gate_enabled = False
            override_active = True
            override_reason = "staging-disable-freshness-gate"
        else:
            override_max_raw = os.getenv("NFL_READINESS_STAGING_MAX_LAST_GAME_AGE_DAYS")
            if override_max_raw is not None:
                try:
                    override_max = max(0, int(override_max_raw))
                    effective_max_last_game_age_days = override_max
                    override_active = override_max != int(default_max_last_game_age_days)
                    override_reason = "staging-max-age-override"
                except ValueError:
                    override_reason = "staging-max-age-invalid"

    return {
        "mode": mode,
        "freshness_gate_enabled": freshness_gate_enabled,
        "effective_max_last_game_age_days": effective_max_last_game_age_days,
        "override_active": override_active,
        "override_reason": override_reason,
    }


def _classify_mlb_readiness(
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


def _readiness_ok_flag(status: str) -> int:
    return 1 if status in {"green", "yellow"} else 0


def _classify_nfl_readiness(
    *,
    sample_size: int,
    calendar_days: int,
    last_game_date: Optional[date],
    moneyline_brier: Optional[float],
    total_mae: Optional[float],
    clv_avg: Optional[float],
    min_sample_size: int,
    min_calendar_days: int,
    max_last_game_age_days: int,
    freshness_gate_enabled: bool,
    max_moneyline_brier: float,
    max_total_mae: float,
    min_clv_avg: float,
) -> Dict[str, Any]:
    today = date.today()
    last_age = (today - last_game_date).days if last_game_date else None
    checks = {
        "sample_size_ok": sample_size >= min_sample_size,
        "calendar_days_ok": calendar_days >= min_calendar_days,
        "freshness_ok": (last_age is not None and last_age <= max_last_game_age_days)
        if freshness_gate_enabled
        else True,
        "moneyline_brier_ok": moneyline_brier is not None and moneyline_brier <= max_moneyline_brier,
        "total_mae_ok": total_mae is not None and total_mae <= max_total_mae,
        "clv_ok": clv_avg is not None and clv_avg >= min_clv_avg,
    }
    failed_reasons = [name for name, passed in checks.items() if not passed]
    status = "go" if all(checks.values()) else "no-go"
    return {
        "status": status,
        "checks": checks,
        "reasons": failed_reasons,
        "staleness_days": last_age,
    }


app = FastAPI(
    title="KosEdge Model Service",
    version=os.getenv("APP_VERSION", "0.1.0"),
)

# Routers
app.include_router(edge_board_router)
app.include_router(mlb_router)
app.include_router(nba_router)
app.include_router(nfl_router)

# CORS (single middleware registration)
origins, allow_credentials = _resolve_cors_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "service": APP_NAME}


@app.get("/health/db")
def health_db() -> Dict[str, Any]:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except SQLAlchemyError as e:
        log.exception("DB healthcheck failed")
        raise HTTPException(status_code=503, detail=f"db_unavailable: {e}")


@app.get("/health/celery")
def health_celery() -> Dict[str, Any]:
    return {"status": "ok", "celery": celery_healthcheck()}


@app.get("/health/mlb-production-readiness")
def health_mlb_production_readiness(
    min_sample_size: int = Query(120, ge=1, le=5000),
    min_calendar_days: int = Query(14, ge=1, le=365),
    max_last_game_age_days: int = Query(3, ge=0, le=30),
) -> Dict[str, Any]:
    try:
        with engine.connect() as conn:
            active_row = conn.execute(
                text(
                    """
                    SELECT active_model_version
                    FROM mlb_model_runtime_state
                    WHERE state_key = :state_key
                    LIMIT 1
                    """
                ),
                {"state_key": MLB_MODEL_STATE_KEY},
            ).fetchone()
            model_version = (
                str(active_row[0]) if active_row and active_row[0] is not None else "mlb-v1-pa-sim"
            )

            snapshot_row = conn.execute(
                text(
                    """
                    SELECT payload, created_at
                    FROM mlb_model_run_snapshots
                    WHERE model_version = :model_version
                      AND pipeline_stage = 'quality_snapshot'
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                ),
                {"model_version": model_version},
            ).fetchone()
            if not snapshot_row:
                raise HTTPException(
                    status_code=503,
                    detail={
                        "status": "red",
                        "model_version": model_version,
                        "reason": "missing_quality_snapshot",
                    },
                )

            payload = dict(snapshot_row._mapping).get("payload") or {}
            sample_size = int(_safe_float(payload.get("sample_size")) or 0)
            calendar_days = int(_safe_float(payload.get("calendar_days_covered")) or 0)
            last_game_date = _safe_date(payload.get("last_game_date"))
            warning_count = conn.execute(
                text(
                    """
                    SELECT COUNT(*)::int
                    FROM mlb_alert_events
                    WHERE severity = 'warning'
                      AND created_at >= NOW() - INTERVAL '24 hours'
                    """
                )
            ).scalar_one()

        classification = _classify_mlb_readiness(
            sample_size=sample_size,
            calendar_days=calendar_days,
            last_game_date=last_game_date,
            warning_alerts_24h=int(warning_count),
            min_sample_size=min_sample_size,
            min_calendar_days=min_calendar_days,
            max_last_game_age_days=max_last_game_age_days,
        )
        response = {
            "status": classification["status"],
            "model_version": model_version,
            "checks": classification["checks"],
            "reasons": classification["reasons"],
            "last_game_age_days": classification["last_game_age_days"],
            "quality_snapshot_created_at": snapshot_row.created_at,
            "recent_warning_alerts_24h": int(warning_count),
        }
        if classification["status"] == "red":
            raise HTTPException(status_code=503, detail=response)
        return response
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        log.exception("MLB readiness healthcheck failed")
        raise HTTPException(status_code=503, detail=f"mlb_readiness_unavailable: {e}")


@app.get("/health/mlb-production-readiness/prometheus", response_class=PlainTextResponse)
def health_mlb_production_readiness_prometheus(
    min_sample_size: int = Query(120, ge=1, le=5000),
    min_calendar_days: int = Query(14, ge=1, le=365),
    max_last_game_age_days: int = Query(3, ge=0, le=30),
) -> PlainTextResponse:
    try:
        payload = health_mlb_production_readiness(
            min_sample_size=min_sample_size,
            min_calendar_days=min_calendar_days,
            max_last_game_age_days=max_last_game_age_days,
        )
        status = str(payload.get("status") or "red")
        ok = _readiness_ok_flag(status)
        body = (
            "# HELP kosedge_mlb_production_readiness_ok MLB production readiness health flag (1=ready,0=not ready)\n"
            "# TYPE kosedge_mlb_production_readiness_ok gauge\n"
            f'kosedge_mlb_production_readiness_ok{{status="{status}",model_version="{payload.get("model_version","unknown")}"}} {ok}\n'
        )
        return PlainTextResponse(content=body, status_code=200)
    except HTTPException as e:
        detail = e.detail if isinstance(e.detail, dict) else {"status": "red", "model_version": "unknown"}
        status = str(detail.get("status") or "red")
        model_version = str(detail.get("model_version") or "unknown")
        body = (
            "# HELP kosedge_mlb_production_readiness_ok MLB production readiness health flag (1=ready,0=not ready)\n"
            "# TYPE kosedge_mlb_production_readiness_ok gauge\n"
            f'kosedge_mlb_production_readiness_ok{{status="{status}",model_version="{model_version}"}} 0\n'
        )
        return PlainTextResponse(content=body, status_code=503)


@app.get("/health/nfl-production-readiness")
def health_nfl_production_readiness(
    model_version: str = Query(DEFAULT_NFL_MODEL_VERSION),
    min_sample_size: int = Query(100, ge=1, le=5000),
    min_calendar_days: int = Query(14, ge=1, le=365),
    max_last_game_age_days: int = Query(8, ge=0, le=90),
    max_moneyline_brier: float = Query(0.255, ge=0.01, le=0.5),
    max_total_mae: float = Query(6.0, ge=0.2, le=20.0),
    min_clv_avg: float = Query(0.0, ge=-0.5, le=0.5),
) -> Dict[str, Any]:
    try:
        policy = _resolve_nfl_readiness_policy(default_max_last_game_age_days=int(max_last_game_age_days))
        with engine.connect() as conn:
            snapshot_row = conn.execute(
                text(
                    """
                    SELECT run_date, payload, created_at
                    FROM nfl_model_quality_snapshots
                    WHERE model_version = :model_version
                      AND pipeline_stage = 'weekly_quality'
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                ),
                {"model_version": model_version},
            ).fetchone()
            if not snapshot_row:
                raise HTTPException(
                    status_code=503,
                    detail={
                        "status": "no-go",
                        "model_version": model_version,
                        "reason": "missing_quality_snapshot",
                    },
                )
            drift_row = conn.execute(
                text(
                    """
                    SELECT status, payload, created_at
                    FROM nfl_decomposition_drift_snapshots
                    WHERE model_version = :model_version
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                ),
                {"model_version": model_version},
            ).fetchone()
        payload = dict(snapshot_row._mapping).get("payload") or {}
        sample_size = int(_safe_float(payload.get("sample_size")) or 0)
        calendar_days = int(_safe_float(payload.get("calendar_days_covered")) or 0)
        last_game_date = _safe_date(payload.get("last_game_date"))
        moneyline_brier = _safe_float(payload.get("moneyline_brier"))
        total_mae = _safe_float(payload.get("total_mae"))
        clv_avg = _safe_float(payload.get("clv_avg"))
        classification = _classify_nfl_readiness(
            sample_size=sample_size,
            calendar_days=calendar_days,
            last_game_date=last_game_date,
            moneyline_brier=moneyline_brier,
            total_mae=total_mae,
            clv_avg=clv_avg,
            min_sample_size=min_sample_size,
            min_calendar_days=min_calendar_days,
            max_last_game_age_days=int(policy["effective_max_last_game_age_days"]),
            freshness_gate_enabled=bool(policy["freshness_gate_enabled"]),
            max_moneyline_brier=max_moneyline_brier,
            max_total_mae=max_total_mae,
            min_clv_avg=min_clv_avg,
        )
        response = {
            "status": classification["status"],
            "model_version": model_version,
            "gating_checks": classification["checks"],
            "reasons": classification["reasons"],
            "quality_snapshot_created_at": (
                snapshot_row.created_at.isoformat()
                if getattr(snapshot_row, "created_at", None) is not None
                else None
            ),
            "freshness_policy": {
                "mode": policy["mode"],
                "override_active": bool(policy["override_active"]),
                "override_reason": policy["override_reason"],
                "freshness_gate_enabled": bool(policy["freshness_gate_enabled"]),
                "max_last_game_age_days_applied": (
                    int(policy["effective_max_last_game_age_days"])
                    if bool(policy["freshness_gate_enabled"])
                    else None
                ),
            },
            "metrics": {
                "sample_size": sample_size,
                "calendar_days_covered": calendar_days,
                "last_game_date": last_game_date.isoformat() if last_game_date else None,
                "staleness_days": classification["staleness_days"],
                "moneyline_brier": moneyline_brier,
                "total_mae": total_mae,
                "clv_avg": clv_avg,
            },
            "drift_monitor": (
                {
                    "status": str(drift_row.status),
                    "created_at": drift_row.created_at.isoformat() if drift_row.created_at is not None else None,
                    "top_shifts": (
                        (drift_row.payload or {}).get("top_shifts")
                        if isinstance(drift_row.payload, dict)
                        else []
                    ),
                }
                if drift_row is not None
                else None
            ),
        }
        if classification["status"] != "go":
            raise HTTPException(status_code=503, detail=response)
        return response
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        log.exception("NFL readiness healthcheck failed")
        raise HTTPException(status_code=503, detail=f"nfl_readiness_unavailable: {e}")


@app.get("/health/nfl-production-readiness/prometheus", response_class=PlainTextResponse)
def health_nfl_production_readiness_prometheus(
    model_version: str = Query(DEFAULT_NFL_MODEL_VERSION),
    min_sample_size: int = Query(100, ge=1, le=5000),
    min_calendar_days: int = Query(14, ge=1, le=365),
    max_last_game_age_days: int = Query(8, ge=0, le=90),
    max_moneyline_brier: float = Query(0.255, ge=0.01, le=0.5),
    max_total_mae: float = Query(6.0, ge=0.2, le=20.0),
    min_clv_avg: float = Query(0.0, ge=-0.5, le=0.5),
) -> PlainTextResponse:
    try:
        payload = health_nfl_production_readiness(
            model_version=model_version,
            min_sample_size=min_sample_size,
            min_calendar_days=min_calendar_days,
            max_last_game_age_days=max_last_game_age_days,
            max_moneyline_brier=max_moneyline_brier,
            max_total_mae=max_total_mae,
            min_clv_avg=min_clv_avg,
        )
        status = str(payload.get("status") or "no-go")
        ok = 1 if status == "go" else 0
        body = (
            "# HELP kosedge_nfl_production_readiness_ok NFL production readiness health flag (1=ready,0=not ready)\n"
            "# TYPE kosedge_nfl_production_readiness_ok gauge\n"
            f'kosedge_nfl_production_readiness_ok{{status="{status}",model_version="{payload.get("model_version","unknown")}"}} {ok}\n'
        )
        return PlainTextResponse(content=body, status_code=200)
    except HTTPException as e:
        detail = e.detail if isinstance(e.detail, dict) else {"status": "no-go", "model_version": "unknown"}
        status = str(detail.get("status") or "no-go")
        model_version = str(detail.get("model_version") or "unknown")
        body = (
            "# HELP kosedge_nfl_production_readiness_ok NFL production readiness health flag (1=ready,0=not ready)\n"
            "# TYPE kosedge_nfl_production_readiness_ok gauge\n"
            f'kosedge_nfl_production_readiness_ok{{status="{status}",model_version="{model_version}"}} 0\n'
        )
        return PlainTextResponse(content=body, status_code=503)


@app.get("/health/nfl-data-freshness")
def health_nfl_data_freshness(persist: bool = Query(False)) -> Dict[str, Any]:
    """Subscription data ownership freshness SLOs (ingest, odds, DR backup)."""
    try:
        from src.services.nfl_resilience_cycle import run_data_freshness_check

        payload = run_data_freshness_check(persist_alert=False)
        # Optionally persist snapshot without webhook noise from the health probe.
        if persist and str(payload.get("status")) != "failed":
            pass
        status = str(payload.get("status") or "failed")
        if status != "ok":
            raise HTTPException(status_code=503, detail=payload)
        return payload
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("NFL data freshness healthcheck failed")
        raise HTTPException(status_code=503, detail={"status": "failed", "error": str(exc)})


@app.get("/health/nfl-data-freshness/prometheus", response_class=PlainTextResponse)
def health_nfl_data_freshness_prometheus() -> PlainTextResponse:
    try:
        payload = health_nfl_data_freshness(persist=False)
        status = str(payload.get("status") or "failed")
        ok = 1 if status == "ok" else 0
        body = (
            "# HELP kosedge_nfl_data_freshness_ok NFL owned-data freshness SLOs (1=ok,0=degraded)\n"
            "# TYPE kosedge_nfl_data_freshness_ok gauge\n"
            f'kosedge_nfl_data_freshness_ok{{status="{status}"}} {ok}\n'
        )
        return PlainTextResponse(content=body, status_code=200)
    except HTTPException as e:
        detail = e.detail if isinstance(e.detail, dict) else {"status": "failed"}
        status = str(detail.get("status") or "failed")
        body = (
            "# HELP kosedge_nfl_data_freshness_ok NFL owned-data freshness SLOs (1=ok,0=degraded)\n"
            "# TYPE kosedge_nfl_data_freshness_ok gauge\n"
            f'kosedge_nfl_data_freshness_ok{{status="{status}"}} 0\n'
        )
        return PlainTextResponse(content=body, status_code=503)


@app.get("/api/odds/snapshots")
def get_odds_snapshots(
    limit: int = Query(10, ge=1, le=200),
    offset: int = Query(0, ge=0),
    include_payload: bool = Query(False),
) -> List[Dict[str, Any]]:
    cols = "id, source, created_at"
    if include_payload:
        cols += ", payload"

    sql = text(
        f"""
        SELECT {cols}
        FROM odds_snapshots
        ORDER BY created_at DESC
        LIMIT :limit
        OFFSET :offset
        """
    )

    try:
        with engine.connect() as conn:
            rows = conn.execute(sql, {"limit": limit, "offset": offset}).fetchall()
        return [dict(r._mapping) for r in rows]
    except SQLAlchemyError as e:
        log.exception("Failed to query odds_snapshots")
        raise HTTPException(status_code=500, detail=f"db_error: {e}")


@app.post("/api/jobs/pull-odds-snapshot")
def job_pull_odds_snapshot(
    nfl_bookmakers: Optional[str] = Query(
        None,
        description="Comma-separated NFL bookmaker keys for The Odds API (defaults to NFL_ODDS_BOOKMAKERS or draftkings).",
    ),
) -> Dict[str, str]:
    try:
        if nfl_bookmakers is not None:
            async_result = celery_app.send_task(
                TASK_PULL_ODDS_SNAPSHOT,
                kwargs={"nfl_bookmakers": nfl_bookmakers},
            )
        else:
            async_result = celery_app.send_task(TASK_PULL_ODDS_SNAPSHOT)
        return {"task_id": async_result.id, "task_name": TASK_PULL_ODDS_SNAPSHOT}
    except Exception as e:
        log.exception("Failed to enqueue pull-odds-snapshot")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/pull-historical-odds-backfill")
def job_pull_historical_odds_backfill(
    sport_key: str = Query("americanfootball_nfl"),
    bookmakers: str = Query("draftkings,fanduel"),
    markets: str = Query("h2h,spreads,totals"),
    start_season: int = Query(2013, ge=2000, le=2100),
    end_season: int = Query(date.today().year - 1, ge=2000, le=2100),
    max_requests: int = Query(15, ge=1, le=3000),
    oldest_first: bool = Query(True),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_PULL_HISTORICAL_ODDS_BACKFILL,
            kwargs={
                "sport_key": sport_key,
                "bookmakers": bookmakers,
                "markets": markets,
                "start_season": int(start_season),
                "end_season": int(end_season),
                "max_requests": int(max_requests),
                "oldest_first": bool(oldest_first),
            },
        )
        return {"task_id": async_result.id, "task_name": TASK_PULL_HISTORICAL_ODDS_BACKFILL}
    except Exception as e:
        log.exception("Failed to enqueue pull-historical-odds-backfill")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/pull-mlb-context")
def job_pull_mlb_context(days_ahead: int = Query(5, ge=0, le=14)) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(TASK_PULL_MLB_CONTEXT, kwargs={"days_ahead": days_ahead})
        return {"task_id": async_result.id, "task_name": TASK_PULL_MLB_CONTEXT}
    except Exception as e:
        log.exception("Failed to enqueue pull-mlb-context")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/run-mlb-simulations")
def job_run_mlb_simulations(
    game_date: Optional[str] = Query(None, description="YYYY-MM-DD (defaults to today if omitted)"),
    simulations: int = Query(4000, ge=500, le=20000),
    model_version: str = Query("mlb-v1-pa-sim"),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_RUN_MLB_SIMULATIONS,
            kwargs={
                "game_date": game_date,
                "simulations": simulations,
                "model_version": model_version,
            },
        )
        return {"task_id": async_result.id, "task_name": TASK_RUN_MLB_SIMULATIONS}
    except Exception as e:
        log.exception("Failed to enqueue run-mlb-simulations")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/pull-nba-context")
def job_pull_nba_context(days_ahead: int = Query(3, ge=0, le=14)) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_PULL_NBA_CONTEXT, kwargs={"days_ahead": days_ahead}
        )
        return {"task_id": async_result.id, "task_name": TASK_PULL_NBA_CONTEXT}
    except Exception as e:
        log.exception("Failed to enqueue pull-nba-context")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/pull-nba-ingest")
def job_pull_nba_ingest(
    days_back: int = Query(7, ge=0, le=60),
    days_ahead: int = Query(3, ge=0, le=14),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_PULL_NBA_INGEST,
            kwargs={"days_back": days_back, "days_ahead": days_ahead},
        )
        return {"task_id": async_result.id, "task_name": TASK_PULL_NBA_INGEST}
    except Exception as e:
        log.exception("Failed to enqueue pull-nba-ingest")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/pull-nba-season-ingest")
def job_pull_nba_season_ingest(
    seasons: Optional[str] = Query(
        None, description="Comma-separated NBA seasons, e.g. 2021-22,2022-23"
    ),
) -> Dict[str, str]:
    try:
        season_list = (
            [s.strip() for s in seasons.split(",") if s.strip()] if seasons else None
        )
        async_result = celery_app.send_task(
            TASK_PULL_NBA_SEASON_INGEST,
            kwargs={"seasons": season_list},
        )
        return {"task_id": async_result.id, "task_name": TASK_PULL_NBA_SEASON_INGEST}
    except Exception as e:
        log.exception("Failed to enqueue pull-nba-season-ingest")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/materialize-nba-rolling-features")
def job_materialize_nba_rolling_features(
    days_back: int = Query(2000, ge=1, le=4000),
    window_games: int = Query(10, ge=1, le=40),
    pbp_sample_games: int = Query(8, ge=0, le=40),
    player_stub_sample_games: int = Query(8, ge=0, le=40),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_NBA_ROLLING_FEATURES,
            kwargs={
                "days_back": days_back,
                "window_games": window_games,
                "pbp_sample_games": pbp_sample_games,
                "player_stub_sample_games": player_stub_sample_games,
            },
        )
        return {"task_id": async_result.id, "task_name": TASK_NBA_ROLLING_FEATURES}
    except Exception as e:
        log.exception("Failed to enqueue materialize-nba-rolling-features")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/pull-nba-historical-odds-densify")
def job_pull_nba_historical_odds_densify(
    max_credit_spend: int = Query(300000, ge=0, le=400000),
    max_requests: int = Query(200, ge=1, le=2000),
    skip_if_mainline_games_ge: int = Query(100, ge=0, le=100000),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_NBA_ODDS_DENSIFY,
            kwargs={
                "max_credit_spend": max_credit_spend,
                "max_requests": max_requests,
                "skip_if_mainline_games_ge": skip_if_mainline_games_ge,
            },
        )
        return {"task_id": async_result.id, "task_name": TASK_NBA_ODDS_DENSIFY}
    except Exception as e:
        log.exception("Failed to enqueue pull-nba-historical-odds-densify")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/run-nba-walkforward-sample")
def job_run_nba_walkforward_sample(
    limit_games: int = Query(60, ge=5, le=400),
    simulations: int = Query(800, ge=300, le=5000),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_NBA_WALKFORWARD,
            kwargs={"limit_games": limit_games, "simulations": simulations},
        )
        return {"task_id": async_result.id, "task_name": TASK_NBA_WALKFORWARD}
    except Exception as e:
        log.exception("Failed to enqueue run-nba-walkforward-sample")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/run-nba-phase1-bootstrap")
def job_run_nba_phase1_bootstrap(
    densify_odds: bool = Query(True),
    max_credit_spend: int = Query(300000, ge=0, le=400000),
    walkforward_games: int = Query(60, ge=5, le=400),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_NBA_PHASE1_BOOTSTRAP,
            kwargs={
                "densify_odds": densify_odds,
                "max_credit_spend": max_credit_spend,
                "walkforward_games": walkforward_games,
            },
        )
        return {"task_id": async_result.id, "task_name": TASK_NBA_PHASE1_BOOTSTRAP}
    except Exception as e:
        log.exception("Failed to enqueue run-nba-phase1-bootstrap")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.get("/api/jobs/nba-inventory")
def job_nba_inventory_sync() -> Dict[str, Any]:
    """Synchronous inventory against model-service DATABASE_URL."""
    try:
        from src.tasks import nba_db_inventory

        return nba_db_inventory()
    except Exception as e:
        log.exception("Failed NBA inventory")
        raise HTTPException(status_code=500, detail=f"inventory_failed: {e}")


@app.post("/api/jobs/run-nba-simulations")
def job_run_nba_simulations(
    game_date: Optional[str] = Query(None, description="YYYY-MM-DD (defaults to today if omitted)"),
    simulations: int = Query(4000, ge=300, le=20000),
    model_version: str = Query(DEFAULT_NBA_MODEL_VERSION),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_RUN_NBA_SIMULATIONS,
            kwargs={
                "game_date": game_date,
                "simulations": simulations,
                "model_version": model_version,
            },
        )
        return {"task_id": async_result.id, "task_name": TASK_RUN_NBA_SIMULATIONS}
    except Exception as e:
        log.exception("Failed to enqueue run-nba-simulations")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/pull-nfl-context")
def job_pull_nfl_context(days_ahead: int = Query(14, ge=0, le=45)) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(TASK_PULL_NFL_CONTEXT, kwargs={"days_ahead": days_ahead})
        return {"task_id": async_result.id, "task_name": TASK_PULL_NFL_CONTEXT}
    except Exception as e:
        log.exception("Failed to enqueue pull-nfl-context")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/run-nfl-simulations")
def job_run_nfl_simulations(
    game_date: Optional[str] = Query(None, description="YYYY-MM-DD (defaults to today if omitted)"),
    simulations: int = Query(4000, ge=300, le=20000),
    model_version: str = Query(DEFAULT_NFL_MODEL_VERSION),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_RUN_NFL_SIMULATIONS,
            kwargs={
                "game_date": game_date,
                "simulations": simulations,
                "model_version": model_version,
            },
        )
        return {"task_id": async_result.id, "task_name": TASK_RUN_NFL_SIMULATIONS}
    except Exception as e:
        log.exception("Failed to enqueue run-nfl-simulations")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/backfill-nfl-historical-projections")
def job_backfill_nfl_historical_projections(
    start_date: str = Query(..., description="YYYY-MM-DD"),
    end_date: str = Query(..., description="YYYY-MM-DD"),
    simulations: int = Query(4000, ge=300, le=20000),
    model_version: str = Query(DEFAULT_NFL_MODEL_VERSION),
    kickoff_buffer_minutes: int = Query(30, ge=0, le=720),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_BACKFILL_NFL_HISTORICAL_PROJECTIONS,
            kwargs={
                "start_date": start_date,
                "end_date": end_date,
                "simulations": simulations,
                "model_version": model_version,
                "kickoff_buffer_minutes": kickoff_buffer_minutes,
            },
        )
        return {"task_id": async_result.id, "task_name": TASK_BACKFILL_NFL_HISTORICAL_PROJECTIONS}
    except Exception as e:
        log.exception("Failed to enqueue backfill-nfl-historical-projections")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/materialize-nfl-market-history")
def job_materialize_nfl_market_history(
    lookback_days: int = Query(45, ge=1, le=3650),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_MATERIALIZE_NFL_MARKET_HISTORY,
            kwargs={"lookback_days": lookback_days},
        )
        return {"task_id": async_result.id, "task_name": TASK_MATERIALIZE_NFL_MARKET_HISTORY}
    except Exception as e:
        log.exception("Failed to enqueue materialize-nfl-market-history")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/run-nfl-clv-attribution")
def job_run_nfl_clv_attribution(
    lookback_days: int = Query(45, ge=7, le=365),
    model_version: str = Query(DEFAULT_NFL_MODEL_VERSION),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_RUN_NFL_CLV_ATTRIBUTION,
            kwargs={"lookback_days": lookback_days, "model_version": model_version},
        )
        return {"task_id": async_result.id, "task_name": TASK_RUN_NFL_CLV_ATTRIBUTION}
    except Exception as e:
        log.exception("Failed to enqueue run-nfl-clv-attribution")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/pull-nfl-outcomes")
def job_pull_nfl_outcomes(days_back: int = Query(60, ge=1, le=365)) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(TASK_PULL_NFL_OUTCOMES, kwargs={"days_back": days_back})
        return {"task_id": async_result.id, "task_name": TASK_PULL_NFL_OUTCOMES}
    except Exception as e:
        log.exception("Failed to enqueue pull-nfl-outcomes")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/run-nfl-quality-grading")
def job_run_nfl_quality_grading(
    lookback_days: int = Query(60, ge=7, le=365),
    model_version: str = Query(DEFAULT_NFL_MODEL_VERSION),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_RUN_NFL_QUALITY_GRADING,
            kwargs={"lookback_days": lookback_days, "model_version": model_version},
        )
        return {"task_id": async_result.id, "task_name": TASK_RUN_NFL_QUALITY_GRADING}
    except Exception as e:
        log.exception("Failed to enqueue run-nfl-quality-grading")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/run-nfl-walkforward-backtest")
def job_run_nfl_walkforward_backtest(
    model_version: str = Query(DEFAULT_NFL_MODEL_VERSION),
    lookback_days: int = Query(240, ge=30, le=1460),
    training_days: int = Query(56, ge=14, le=365),
    step_days: int = Query(7, ge=1, le=30),
    apply_calibration: bool = Query(True),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_RUN_NFL_WALKFORWARD_BACKTEST,
            kwargs={
                "model_version": model_version,
                "lookback_days": lookback_days,
                "training_days": training_days,
                "step_days": step_days,
                "apply_calibration": apply_calibration,
            },
        )
        return {"task_id": async_result.id, "task_name": TASK_RUN_NFL_WALKFORWARD_BACKTEST}
    except Exception as e:
        log.exception("Failed to enqueue run-nfl-walkforward-backtest")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/evaluate-nfl-promotion")
def job_evaluate_nfl_promotion(
    challenger_model_version: str = Query(..., min_length=3, max_length=128),
    lookback_days: int = Query(45, ge=7, le=365),
    auto_promote: bool = Query(True),
    champion_model_version: Optional[str] = Query(None),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_EVAL_NFL_PROMOTION,
            kwargs={
                "challenger_model_version": challenger_model_version,
                "lookback_days": int(lookback_days),
                "auto_promote": bool(auto_promote),
                "champion_model_version": champion_model_version,
            },
        )
        return {"task_id": async_result.id, "task_name": TASK_EVAL_NFL_PROMOTION}
    except Exception as e:
        log.exception("Failed to enqueue evaluate-nfl-promotion")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/run-nfl-framework-tuning")
def job_run_nfl_framework_tuning(
    model_version: str = Query(DEFAULT_NFL_MODEL_VERSION),
    lookback_days: int = Query(240, ge=45, le=1460),
    training_days: int = Query(56, ge=14, le=365),
    step_days: int = Query(7, ge=1, le=30),
    max_candidates: int = Query(180, ge=12, le=1000),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_RUN_NFL_FRAMEWORK_TUNING,
            kwargs={
                "model_version": model_version,
                "lookback_days": int(lookback_days),
                "training_days": int(training_days),
                "step_days": int(step_days),
                "max_candidates": int(max_candidates),
            },
        )
        return {"task_id": async_result.id, "task_name": TASK_RUN_NFL_FRAMEWORK_TUNING}
    except Exception as e:
        log.exception("Failed to enqueue run-nfl-framework-tuning")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/run-nfl-supervised-retrain")
def job_run_nfl_supervised_retrain(
    model_version: str = Query(DEFAULT_NFL_MODEL_VERSION),
    start_season: int = Query(2013, ge=2000, le=2100),
    end_season: int = Query(date.today().year - 1, ge=2000, le=2100),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_RUN_NFL_SUPERVISED_RETRAIN,
            kwargs={
                "model_version": model_version,
                "start_season": int(start_season),
                "end_season": int(end_season),
            },
        )
        return {"task_id": async_result.id, "task_name": TASK_RUN_NFL_SUPERVISED_RETRAIN}
    except Exception as e:
        log.exception("Failed to enqueue run-nfl-supervised-retrain")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/run-nfl-decomposition-drift")
def job_run_nfl_decomposition_drift(
    model_version: str = Query(DEFAULT_NFL_MODEL_VERSION),
    lookback_days: int = Query(120, ge=21, le=730),
    baseline_weeks: int = Query(4, ge=2, le=16),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_RUN_NFL_DECOMPOSITION_DRIFT,
            kwargs={
                "model_version": model_version,
                "lookback_days": int(lookback_days),
                "baseline_weeks": int(baseline_weeks),
            },
        )
        return {"task_id": async_result.id, "task_name": TASK_RUN_NFL_DECOMPOSITION_DRIFT}
    except Exception as e:
        log.exception("Failed to enqueue run-nfl-decomposition-drift")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/run-nfl-launch-hardening")
def job_run_nfl_launch_hardening(
    model_version: str = Query(DEFAULT_NFL_MODEL_VERSION),
    days_ahead: int = Query(14, ge=1, le=45),
    outcomes_lookback_days: int = Query(60, ge=14, le=365),
    simulations: int = Query(5000, ge=500, le=30000),
    backtest_lookback_days: int = Query(240, ge=60, le=1460),
    tuning_lookback_days: int = Query(240, ge=60, le=1460),
    training_days: int = Query(56, ge=14, le=365),
    step_days: int = Query(7, ge=1, le=30),
    max_candidates: int = Query(180, ge=12, le=1000),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_RUN_NFL_LAUNCH_HARDENING,
            kwargs={
                "model_version": model_version,
                "days_ahead": int(days_ahead),
                "outcomes_lookback_days": int(outcomes_lookback_days),
                "simulations": int(simulations),
                "backtest_lookback_days": int(backtest_lookback_days),
                "tuning_lookback_days": int(tuning_lookback_days),
                "training_days": int(training_days),
                "step_days": int(step_days),
                "max_candidates": int(max_candidates),
            },
        )
        return {"task_id": async_result.id, "task_name": TASK_RUN_NFL_LAUNCH_HARDENING}
    except Exception as e:
        log.exception("Failed to enqueue run-nfl-launch-hardening")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/run-nfl-player-baselines")
def job_run_nfl_player_baselines(
    season: int = Query(..., ge=2010, le=2100),
    week: Optional[int] = Query(None, ge=1, le=25),
    model_version: str = Query("nfl-player-v1"),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_NFL_PLAYER_BASELINES,
            kwargs={"season": season, "week": week, "model_version": model_version},
        )
        return {"task_id": async_result.id, "task_name": TASK_NFL_PLAYER_BASELINES}
    except Exception as e:
        log.exception("Failed to enqueue run-nfl-player-baselines")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/run-nfl-player-features")
def job_run_nfl_player_features(
    season: int = Query(..., ge=2010, le=2100),
    week: Optional[int] = Query(None, ge=1, le=25),
    replace_existing: bool = Query(True),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_NFL_PLAYER_FEATURES,
            kwargs={"season": season, "week": week, "replace_existing": replace_existing},
        )
        return {"task_id": async_result.id, "task_name": TASK_NFL_PLAYER_FEATURES}
    except Exception as e:
        log.exception("Failed to enqueue run-nfl-player-features")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/run-nfl-player-box-sims")
def job_run_nfl_player_box_sims(
    season: int = Query(..., ge=2010, le=2100),
    week: Optional[int] = Query(None, ge=1, le=25),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_NFL_PLAYER_BOX_SIMS,
            kwargs={"season": season, "week": week},
        )
        return {"task_id": async_result.id, "task_name": TASK_NFL_PLAYER_BOX_SIMS}
    except Exception as e:
        log.exception("Failed to enqueue run-nfl-player-box-sims")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/run-nfl-props-layer-rebuild")
def job_run_nfl_props_layer_rebuild(
    season: int = Query(..., ge=2010, le=2100),
    week: Optional[int] = Query(None, ge=1, le=25),
    weeks: Optional[str] = Query(None, description="Comma-separated weeks"),
    model_version: str = Query("nfl-player-v1"),
    replace_features: bool = Query(True),
    rematerialize_season_features: bool = Query(False),
) -> Dict[str, Any]:
    try:
        week_list = None
        if weeks:
            week_list = sorted({int(part.strip()) for part in weeks.split(",") if part.strip()})
        async_result = celery_app.send_task(
            TASK_NFL_PROPS_LAYER_REBUILD,
            kwargs={
                "season": season,
                "week": week,
                "weeks": week_list,
                "model_version": model_version,
                "replace_features": replace_features,
                "rematerialize_season_features": rematerialize_season_features,
            },
        )
        return {
            "task_id": async_result.id,
            "task_name": TASK_NFL_PROPS_LAYER_REBUILD,
            "season": season,
            "week": week,
            "weeks": week_list,
        }
    except Exception as e:
        log.exception("Failed to enqueue run-nfl-props-layer-rebuild")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/run-nfl-player-props")
def job_run_nfl_player_props(
    season: int = Query(..., ge=2010, le=2100),
    week: Optional[int] = Query(None, ge=1, le=25),
    model_version: str = Query("nfl-player-v1"),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_NFL_PLAYER_PROPS,
            kwargs={"season": season, "week": week, "model_version": model_version},
        )
        return {"task_id": async_result.id, "task_name": TASK_NFL_PLAYER_PROPS}
    except Exception as e:
        log.exception("Failed to enqueue run-nfl-player-props")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/pull-nfl-player-prop-markets")
def job_pull_nfl_player_prop_markets(
    season: int = Query(..., ge=2010, le=2100),
    week: int = Query(..., ge=1, le=25),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_NFL_PLAYER_PROP_MARKETS,
            kwargs={"season": season, "week": week},
        )
        return {"task_id": async_result.id, "task_name": TASK_NFL_PLAYER_PROP_MARKETS}
    except Exception as e:
        log.exception("Failed to enqueue pull-nfl-player-prop-markets")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/run-nfl-fantasy-projections")
def job_run_nfl_fantasy_projections(
    season: int = Query(..., ge=2010, le=2100),
    week: Optional[int] = Query(None, ge=1, le=25),
    model_version: str = Query("nfl-player-v1"),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_NFL_FANTASY,
            kwargs={"season": season, "week": week, "model_version": model_version},
        )
        return {"task_id": async_result.id, "task_name": TASK_NFL_FANTASY}
    except Exception as e:
        log.exception("Failed to enqueue run-nfl-fantasy-projections")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/run-nfl-player-cycle")
def job_run_nfl_player_cycle(
    season: int = Query(..., ge=2010, le=2100),
    week: Optional[int] = Query(None, ge=1, le=25),
    model_version: str = Query("nfl-player-v1"),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_NFL_PLAYER_CYCLE,
            kwargs={"season": season, "week": week, "model_version": model_version},
        )
        return {"task_id": async_result.id, "task_name": TASK_NFL_PLAYER_CYCLE}
    except Exception as e:
        log.exception("Failed to enqueue run-nfl-player-cycle")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/run-nfl-identity-refresh")
def job_run_nfl_identity_refresh(
    season: int = Query(..., ge=2010, le=2100),
    week: Optional[int] = Query(None, ge=1, le=25),
    model_version: str = Query("nfl-player-v1"),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_NFL_IDENTITY_REFRESH,
            kwargs={"season": season, "week": week, "model_version": model_version},
        )
        return {"task_id": async_result.id, "task_name": TASK_NFL_IDENTITY_REFRESH}
    except Exception as e:
        log.exception("Failed to enqueue run-nfl-identity-refresh")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/run-nfl-identity-manual-resolutions")
def job_run_nfl_identity_manual_resolutions(
    limit: int = Query(200, ge=1, le=5000),
    reviewer: str = Query("system-weekly-identity-sync", min_length=2, max_length=128),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_NFL_IDENTITY_MANUAL_RESOLUTIONS,
            kwargs={"limit": limit, "reviewer": reviewer},
        )
        return {"task_id": async_result.id, "task_name": TASK_NFL_IDENTITY_MANUAL_RESOLUTIONS}
    except Exception as e:
        log.exception("Failed to enqueue run-nfl-identity-manual-resolutions")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/run-nfl-identity-quality-snapshot")
def job_run_nfl_identity_quality_snapshot(
    season: Optional[int] = Query(None, ge=2010, le=2100),
    week: Optional[int] = Query(None, ge=1, le=25),
    source_system: Optional[str] = Query(None),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_NFL_IDENTITY_QUALITY_SNAPSHOT,
            kwargs={"season": season, "week": week, "source_system": source_system},
        )
        return {"task_id": async_result.id, "task_name": TASK_NFL_IDENTITY_QUALITY_SNAPSHOT}
    except Exception as e:
        log.exception("Failed to enqueue run-nfl-identity-quality-snapshot")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/run-nfl-weekly-resilience-cycle")
def job_run_nfl_weekly_resilience_cycle(
    season: Optional[int] = Query(None, ge=2010, le=2100),
    week: Optional[int] = Query(None, ge=1, le=25),
    skip_player_update: bool = Query(False),
    skip_dr_backup: bool = Query(False),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            "src.tasks.run_nfl_weekly_resilience_cycle",
            kwargs={
                "season": season,
                "week": week,
                "skip_player_update": skip_player_update,
                "skip_dr_backup": skip_dr_backup,
            },
        )
        return {
            "task_id": async_result.id,
            "task_name": "src.tasks.run_nfl_weekly_resilience_cycle",
        }
    except Exception as e:
        log.exception("Failed to enqueue run-nfl-weekly-resilience-cycle")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/run-nfl-dr-backup")
def job_run_nfl_dr_backup(skip_verify: bool = Query(False)) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            "src.tasks.run_nfl_dr_backup",
            kwargs={"skip_verify": skip_verify},
        )
        return {"task_id": async_result.id, "task_name": "src.tasks.run_nfl_dr_backup"}
    except Exception as e:
        log.exception("Failed to enqueue run-nfl-dr-backup")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/run-nfl-data-freshness-check")
def job_run_nfl_data_freshness_check(
    persist_alert: bool = Query(True),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            "src.tasks.run_nfl_data_freshness_check",
            kwargs={"persist_alert": persist_alert},
        )
        return {
            "task_id": async_result.id,
            "task_name": "src.tasks.run_nfl_data_freshness_check",
        }
    except Exception as e:
        log.exception("Failed to enqueue run-nfl-data-freshness-check")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/pull-mlb-outcomes")
def job_pull_mlb_outcomes(days_back: int = Query(30, ge=1, le=365)) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(TASK_PULL_MLB_OUTCOMES, kwargs={"days_back": days_back})
        return {"task_id": async_result.id, "task_name": TASK_PULL_MLB_OUTCOMES}
    except Exception as e:
        log.exception("Failed to enqueue pull-mlb-outcomes")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/pull-mlb-data-lake")
def job_pull_mlb_data_lake(
    days_back: int = Query(60, ge=1, le=365),
    days_ahead: int = Query(7, ge=0, le=30),
    season: Optional[int] = Query(None, ge=2000, le=2100),
    include_rosters: bool = Query(True),
    include_game_feeds: bool = Query(True),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_PULL_MLB_DATA_LAKE,
            kwargs={
                "days_back": days_back,
                "days_ahead": days_ahead,
                "season": season,
                "include_rosters": include_rosters,
                "include_game_feeds": include_game_feeds,
            },
        )
        return {"task_id": async_result.id, "task_name": TASK_PULL_MLB_DATA_LAKE}
    except Exception as e:
        log.exception("Failed to enqueue pull-mlb-data-lake")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/run-mlb-daily-cycle")
def job_run_mlb_daily_cycle(
    days_ahead: int = Query(5, ge=0, le=14),
    outcomes_lookback_days: int = Query(60, ge=7, le=365),
    simulations: int = Query(4000, ge=500, le=30000),
    base_model_version: str = Query("mlb-v1-pa-sim"),
    challenger_model_version: str = Query("mlb-v2-pitch-sim"),
    run_challenger: bool = Query(True),
    calibration_lookback_days: int = Query(45, ge=7, le=365),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_RUN_MLB_DAILY_CYCLE,
            kwargs={
                "days_ahead": days_ahead,
                "outcomes_lookback_days": outcomes_lookback_days,
                "simulations": simulations,
                "base_model_version": base_model_version,
                "challenger_model_version": challenger_model_version,
                "run_challenger": run_challenger,
                "calibration_lookback_days": calibration_lookback_days,
            },
        )
        return {"task_id": async_result.id, "task_name": TASK_RUN_MLB_DAILY_CYCLE}
    except Exception as e:
        log.exception("Failed to enqueue run-mlb-daily-cycle")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/evaluate-mlb-promotion")
def job_evaluate_mlb_promotion(
    base_model_version: str = Query("mlb-v1-pa-sim"),
    challenger_model_version: str = Query("mlb-v2-pitch-sim"),
    lookback_days: int = Query(45, ge=7, le=365),
    auto_promote: bool = Query(True),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_EVAL_MLB_PROMOTION,
            kwargs={
                "base_model_version": base_model_version,
                "challenger_model_version": challenger_model_version,
                "lookback_days": lookback_days,
                "auto_promote": auto_promote,
            },
        )
        return {"task_id": async_result.id, "task_name": TASK_EVAL_MLB_PROMOTION}
    except Exception as e:
        log.exception("Failed to enqueue evaluate-mlb-promotion")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/mlb-lineup-nowcast-repricing")
def job_mlb_lineup_nowcast_repricing(
    horizon_hours: int = Query(18, ge=1, le=48),
    simulations: int = Query(3000, ge=200, le=20000),
    base_model_version: str = Query("mlb-v1-pa-sim"),
    challenger_model_version: str = Query("mlb-v2-pitch-sim"),
    run_challenger: bool = Query(True),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_MLB_NOWCAST_REPRICING,
            kwargs={
                "horizon_hours": horizon_hours,
                "simulations": simulations,
                "base_model_version": base_model_version,
                "challenger_model_version": challenger_model_version,
                "run_challenger": run_challenger,
            },
        )
        return {"task_id": async_result.id, "task_name": TASK_MLB_NOWCAST_REPRICING}
    except Exception as e:
        log.exception("Failed to enqueue mlb-lineup-nowcast-repricing")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/mlb-walkforward-backtest")
def job_mlb_walkforward_backtest(
    model_version: str = Query("mlb-v1-pa-sim"),
    lookback_days: int = Query(180, ge=30, le=730),
    training_days: int = Query(45, ge=14, le=365),
    step_days: int = Query(7, ge=1, le=30),
    apply_calibration: bool = Query(True),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_MLB_WALKFORWARD_BACKTEST,
            kwargs={
                "model_version": model_version,
                "lookback_days": lookback_days,
                "training_days": training_days,
                "step_days": step_days,
                "apply_calibration": apply_calibration,
            },
        )
        return {"task_id": async_result.id, "task_name": TASK_MLB_WALKFORWARD_BACKTEST}
    except Exception as e:
        log.exception("Failed to enqueue mlb-walkforward-backtest")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/mlb-feature-ablation")
def job_mlb_feature_ablation(
    game_date: Optional[str] = Query(None),
    model_version: str = Query("mlb-v1-pa-sim"),
    simulations: int = Query(1500, ge=500, le=10000),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_MLB_FEATURE_ABLATION,
            kwargs={
                "game_date": game_date,
                "model_version": model_version,
                "simulations": simulations,
            },
        )
        return {"task_id": async_result.id, "task_name": TASK_MLB_FEATURE_ABLATION}
    except Exception as e:
        log.exception("Failed to enqueue mlb-feature-ablation")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/mlb-historical-odds-densify")
def job_mlb_historical_odds_densify(
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    bookmakers: str = Query("draftkings,fanduel"),
    markets: str = Query("h2h,spreads,totals"),
    max_requests: int = Query(40, ge=1, le=500),
    day_offset: int = Query(0, ge=-7, le=2),
    snapshot_hour_utc: int = Query(17, ge=0, le=23),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_MLB_HISTORICAL_ODDS_DENSIFY,
            kwargs={
                "start_date": start_date,
                "end_date": end_date,
                "bookmakers": bookmakers,
                "markets": markets,
                "max_requests": int(max_requests),
                "day_offset": int(day_offset),
                "snapshot_hour_utc": int(snapshot_hour_utc),
            },
        )
        return {"task_id": async_result.id, "task_name": TASK_MLB_HISTORICAL_ODDS_DENSIFY}
    except Exception as e:
        log.exception("Failed to enqueue mlb-historical-odds-densify")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/mlb-clv-attribution")
def job_mlb_clv_attribution(
    model_version: str = Query("mlb-v1-pa-sim"),
    lookback_days: int = Query(45, ge=7, le=365),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_MLB_CLV_ATTRIBUTION,
            kwargs={
                "model_version": model_version,
                "lookback_days": int(lookback_days),
            },
        )
        return {"task_id": async_result.id, "task_name": TASK_MLB_CLV_ATTRIBUTION}
    except Exception as e:
        log.exception("Failed to enqueue mlb-clv-attribution")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/mlb-quality-grading")
def job_mlb_quality_grading(
    model_version: str = Query("mlb-v1-pa-sim"),
    lookback_days: int = Query(60, ge=7, le=365),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_MLB_QUALITY_GRADING,
            kwargs={
                "model_version": model_version,
                "lookback_days": int(lookback_days),
            },
        )
        return {"task_id": async_result.id, "task_name": TASK_MLB_QUALITY_GRADING}
    except Exception as e:
        log.exception("Failed to enqueue mlb-quality-grading")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/mlb-historical-resim")
def job_mlb_historical_resim(
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    simulations: int = Query(2000, ge=500, le=10000),
    model_version: str = Query("mlb-v1-pa-sim"),
    max_games: int = Query(200, ge=1, le=2000),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_MLB_HISTORICAL_RESIM,
            kwargs={
                "start_date": start_date,
                "end_date": end_date,
                "simulations": int(simulations),
                "model_version": model_version,
                "max_games": int(max_games),
            },
        )
        return {"task_id": async_result.id, "task_name": TASK_MLB_HISTORICAL_RESIM}
    except Exception as e:
        log.exception("Failed to enqueue mlb-historical-resim")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.post("/api/jobs/mlb-determinism-check")
def job_mlb_determinism_check(
    game_date: Optional[str] = Query(None),
    model_version: str = Query("mlb-v1-pa-sim"),
    simulations: int = Query(800, ge=500, le=5000),
) -> Dict[str, str]:
    try:
        async_result = celery_app.send_task(
            TASK_MLB_DETERMINISM_CHECK,
            kwargs={
                "game_date": game_date,
                "model_version": model_version,
                "simulations": simulations,
            },
        )
        return {"task_id": async_result.id, "task_name": TASK_MLB_DETERMINISM_CHECK}
    except Exception as e:
        log.exception("Failed to enqueue mlb-determinism-check")
        raise HTTPException(status_code=500, detail=f"enqueue_failed: {e}")


@app.get("/api/jobs/{task_id}")
def job_status(task_id: str) -> Dict[str, Any]:
    res = celery_app.AsyncResult(task_id)
    payload: Dict[str, Any] = {"task_id": task_id, "state": res.state}

    if res.successful():
        payload["result"] = res.result
    elif res.failed():
        payload["error"] = str(res.result)

    return payload