from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from src.db import SessionLocal
from src.services.nba_data import default_league_average_inputs, normalize_team_key
from src.services.nba_possession_simulator import (
    DEFAULT_NBA_MODEL_VERSION,
    NBA_WORKER_BUILD_ID,
    NbaGameInputs,
    simulate_nba_game,
)
from src.services.nba_publish_policy import board_publish_posture, publish_tag
from src.services.nba_schema import ensure_nba_model_tables

router = APIRouter(prefix="/nba", tags=["nba-model"])
log = logging.getLogger(__name__)
MODEL_STATE_KEY = "nba_active_model"


def _to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (int, float)):
        return float(v)
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


def _resolve_active_model_version(
    session: Any, fallback: str = DEFAULT_NBA_MODEL_VERSION
) -> str:
    try:
        row = session.execute(
            text(
                """
                SELECT active_model_version
                FROM nba_model_runtime_state
                WHERE state_key = :state_key
                LIMIT 1
                """
            ),
            {"state_key": MODEL_STATE_KEY},
        ).fetchone()
    except Exception:
        return fallback
    if not row:
        return fallback
    value = row[0]
    return str(value) if value else fallback


def _inputs_from_context_row(m: Dict[str, Any]) -> NbaGameInputs:
    return NbaGameInputs(
        game_id=str(m["game_id"]),
        home_team=str(m.get("home_team") or m.get("home_team_key") or "Home"),
        away_team=str(m.get("away_team") or m.get("away_team_key") or "Away"),
        pace_home=_to_float(m.get("pace_home")) or 100.0,
        pace_away=_to_float(m.get("pace_away")) or 100.0,
        ortg_home=_to_float(m.get("ortg_home")) or 114.0,
        ortg_away=_to_float(m.get("ortg_away")) or 114.0,
        drtg_home=_to_float(m.get("drtg_home")) or 114.0,
        drtg_away=_to_float(m.get("drtg_away")) or 114.0,
        three_pt_rate_home=_to_float(m.get("three_pt_rate_home")) or 0.39,
        three_pt_rate_away=_to_float(m.get("three_pt_rate_away")) or 0.39,
        three_pt_pct_home=_to_float(m.get("three_pt_pct_home")) or 0.36,
        three_pt_pct_away=_to_float(m.get("three_pt_pct_away")) or 0.36,
        rest_days_home=_to_float(m.get("rest_days_home")) or 2.0,
        rest_days_away=_to_float(m.get("rest_days_away")) or 2.0,
        sample_games_home=_to_int(m.get("sample_games_home")),
        sample_games_away=_to_int(m.get("sample_games_away")),
        feature_pack_version=m.get("feature_pack_version"),
        market_spread_home=_to_float(m.get("market_spread_home")),
        market_total=_to_float(m.get("market_total")),
    )


def _store_projection(session: Any, projection: Dict[str, Any]) -> None:
    markets = projection.get("markets") or {}
    session.execute(
        text(
            """
            INSERT INTO nba_market_projections (
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
            "worker_build_id": projection.get("worker_build_id") or NBA_WORKER_BUILD_ID,
            "projection": json.dumps(projection),
            "created_at": datetime.now(timezone.utc),
        },
    )


def _fetch_upcoming_games(session: Any, target_date: date) -> List[Dict[str, Any]]:
    """Prefer core games hierarchy; fall back to nba_games_ingest."""
    try:
        rows = session.execute(
            text(
                """
                SELECT
                  g.id AS game_id,
                  g.game_date,
                  g.start_time,
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
                  c.feature_pack_version
                FROM games g
                JOIN seasons s ON s.id = g.season_id
                JOIN leagues l ON l.id = s.league_id
                JOIN teams home ON home.id = g.home_team_id
                JOIN teams away ON away.id = g.away_team_id
                LEFT JOIN nba_game_context c ON c.game_id = g.id::text
                WHERE l.code = 'nba'
                  AND g.game_date = :game_date
                ORDER BY g.start_time NULLS LAST
                """
            ),
            {"game_date": target_date},
        ).fetchall()
        return [dict(r._mapping) for r in rows]
    except Exception as exc:
        log.info("NBA games hierarchy query unavailable: %s", str(exc)[:200])

    try:
        rows = session.execute(
            text(
                """
                SELECT
                  external_game_id AS game_id,
                  game_date,
                  start_time,
                  status AS game_status,
                  home_team_key AS home_team,
                  away_team_key AS away_team,
                  home_team_key AS home_abbr,
                  away_team_key AS away_abbr
                FROM nba_games_ingest
                WHERE game_date = :game_date
                ORDER BY start_time NULLS LAST
                """
            ),
            {"game_date": target_date},
        ).fetchall()
        return [dict(r._mapping) for r in rows]
    except Exception as exc:
        log.info("NBA ingest games query unavailable: %s", str(exc)[:200])
        return []


@router.get("/health")
def nba_health() -> Dict[str, Any]:
    """Lightweight NBA model health / canary probe."""
    session = SessionLocal()
    try:
        ensure_nba_model_tables(session)
        session.commit()
        active = _resolve_active_model_version(session)
        proj_count = 0
        try:
            row = session.execute(
                text("SELECT COUNT(*) FROM nba_market_projections")
            ).fetchone()
            proj_count = int(row[0]) if row else 0
        except Exception:
            proj_count = 0
        return {
            "ok": True,
            "sport": "nba",
            "active_model_version": active,
            "default_model_version": DEFAULT_NBA_MODEL_VERSION,
            "worker_build_id": NBA_WORKER_BUILD_ID,
            "projections_stored": proj_count,
            "simulator": "possession_monte_carlo",
            "props_model_version": "nba-player-props-v1",
            "phase": "phase3",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"nba_health_failed: {exc}") from exc
    finally:
        session.close()


@router.get("/fair-lines")
def nba_fair_lines(
    game_date: Optional[date] = Query(None, description="UTC date; defaults to today"),
    model_version: Optional[str] = Query(None),
    days_ahead: int = Query(3, ge=0, le=14),
) -> Dict[str, Any]:
    """Desk fair-lines board: ML, spread, total from latest possession sims.

    Empty slate is honest in offseason — returns count=0 with slate_status label,
    never invents prices.
    """
    session = SessionLocal()
    try:
        try:
            ensure_nba_model_tables(session)
            session.commit()
        except Exception:
            session.rollback()

        effective_model_version = model_version or _resolve_active_model_version(session)
        target_date = game_date or date.today()
        lines: List[Dict[str, Any]] = []
        schema_ready = True

        try:
            if game_date is not None or days_ahead == 0:
                rows = session.execute(
                    text(
                        """
                        SELECT DISTINCT ON (mp.game_id)
                          mp.game_id,
                          g.game_date,
                          g.start_time,
                          home.name AS home_team,
                          away.name AS away_team,
                          mp.home_win_prob,
                          mp.fair_home_ml,
                          mp.total_mean,
                          mp.fair_total,
                          mp.fair_spread_home,
                          mp.home_cover_prob,
                          mp.margin_mean,
                          mp.worker_build_id,
                          mp.model_version,
                          mp.created_at AS projected_at
                        FROM nba_market_projections mp
                        LEFT JOIN games g ON g.id::text = mp.game_id
                        LEFT JOIN teams home ON home.id = g.home_team_id
                        LEFT JOIN teams away ON away.id = g.away_team_id
                        WHERE mp.model_version = :model_version
                          AND (g.game_date = :game_date OR g.game_date IS NULL)
                        ORDER BY mp.game_id, mp.created_at DESC
                        """
                    ),
                    {"model_version": effective_model_version, "game_date": target_date},
                ).fetchall()
            else:
                rows = session.execute(
                    text(
                        """
                        SELECT DISTINCT ON (mp.game_id)
                          mp.game_id,
                          g.game_date,
                          g.start_time,
                          home.name AS home_team,
                          away.name AS away_team,
                          mp.home_win_prob,
                          mp.fair_home_ml,
                          mp.total_mean,
                          mp.fair_total,
                          mp.fair_spread_home,
                          mp.home_cover_prob,
                          mp.margin_mean,
                          mp.worker_build_id,
                          mp.model_version,
                          mp.created_at AS projected_at
                        FROM nba_market_projections mp
                        LEFT JOIN games g ON g.id::text = mp.game_id
                        LEFT JOIN teams home ON home.id = g.home_team_id
                        LEFT JOIN teams away ON away.id = g.away_team_id
                        WHERE mp.model_version = :model_version
                          AND (
                            g.game_date IS NULL
                            OR (
                              g.game_date >= :game_date
                              AND g.game_date <= CAST(:game_date AS date) + (:days_ahead * INTERVAL '1 day')
                            )
                          )
                        ORDER BY mp.game_id, mp.created_at DESC
                        """
                    ),
                    {
                        "model_version": effective_model_version,
                        "game_date": target_date,
                        "days_ahead": days_ahead,
                    },
                ).fetchall()
        except Exception as exc:
            log.warning("NBA fair-lines query failed (schema/runtime): %s", str(exc)[:300])
            schema_ready = False
            rows = []

        for r in rows:
            m = dict(r._mapping)
            # Prefer joined team names; fall back to projection JSON.
            home_team = m.get("home_team")
            away_team = m.get("away_team")
            if not home_team or not away_team:
                try:
                    proj_row = session.execute(
                        text(
                            """
                            SELECT projection FROM nba_market_projections
                            WHERE game_id = :game_id AND model_version = :model_version
                            ORDER BY created_at DESC LIMIT 1
                            """
                        ),
                        {
                            "game_id": m["game_id"],
                            "model_version": effective_model_version,
                        },
                    ).fetchone()
                    if proj_row:
                        proj = proj_row[0]
                        if isinstance(proj, str):
                            proj = json.loads(proj)
                        inputs = (proj or {}).get("inputs") or {}
                        home_team = home_team or inputs.get("home_team")
                        away_team = away_team or inputs.get("away_team")
                except Exception:
                    pass

            fair_spread = _to_float(m.get("fair_spread_home"))
            fair_total = _to_float(m.get("fair_total"))
            lines.append(
                {
                    "game_id": m["game_id"],
                    "game_date": m.get("game_date") or target_date,
                    "start_time": m.get("start_time"),
                    "home_team": home_team or "Home",
                    "away_team": away_team or "Away",
                    "home_win_prob": _to_float(m.get("home_win_prob")),
                    "fair_home_ml": _to_int(m.get("fair_home_ml")),
                    "total_mean": _to_float(m.get("total_mean")),
                    "fair_total": fair_total,
                    "fair_spread_home": fair_spread,
                    "home_cover_prob": _to_float(m.get("home_cover_prob")),
                    "margin_mean": _to_float(m.get("margin_mean")),
                    "worker_build_id": m.get("worker_build_id"),
                    "projected_at": m.get("projected_at"),
                    # Research-only until close-line ATS clears evidence floors.
                    "publish": {
                        "spread": publish_tag(
                            "spread",
                            model_line=fair_spread,
                            market_line=None,
                            force_research_only=True,
                        ),
                        "total": publish_tag(
                            "total",
                            model_line=fair_total,
                            market_line=None,
                            force_research_only=True,
                        ),
                    },
                }
            )

        # Offseason / empty-slate honesty (July 31 2026 is preseason build window).
        month = target_date.month
        in_regular_season_window = month in {10, 11, 12, 1, 2, 3, 4, 5, 6}
        if len(lines) == 0:
            slate_status = (
                "offseason_empty"
                if not in_regular_season_window
                else ("schema_not_ready" if not schema_ready else "no_projections_yet")
            )
            message = (
                "NBA possession sim board is live; no projections for this date. "
                "Offseason empty slate — not inventing fair prices."
                if slate_status == "offseason_empty"
                else (
                    "NBA fair-lines schema/runtime not ready."
                    if slate_status == "schema_not_ready"
                    else "No NBA projections stored yet for this date. Run simulations after context assemble."
                )
            )
        else:
            slate_status = "ok"
            message = None

        posture = board_publish_posture()
        return {
            "game_date": target_date,
            "model_version": effective_model_version,
            "worker_build_id": NBA_WORKER_BUILD_ID,
            "count": len(lines),
            "lines": lines,
            "slate_status": slate_status,
            "message": message,
            "publish_posture": posture,
            "features_mode": (
                "rolling_features_when_assembled"
                if in_regular_season_window
                else "offseason_honest_empty"
            ),
            "phase": "phase3",
        }
    finally:
        session.close()


@router.get("/props/board")
def nba_props_board(
    as_of_date: Optional[date] = Query(None),
    model_version: str = Query("nba-player-props-v1"),
    market_key: Optional[str] = Query(None),
    team: Optional[str] = Query(None),
    tag: Optional[str] = Query(None, description="PLAY | WATCH | PASS"),
    limit: int = Query(250, ge=1, le=2000),
) -> Dict[str, Any]:
    """Research-only NBA player props board (pts/reb/ast/threes)."""
    from src.services.nba_prop_edge_policy import ou_balance_report

    session = SessionLocal()
    try:
        try:
            ensure_nba_model_tables(session)
            session.commit()
        except Exception:
            session.rollback()

        target = as_of_date or date.today()
        tag_filter = (tag or "").strip().upper() or None
        rows = session.execute(
            text(
                """
                SELECT
                  model_version, as_of_date, player_id, player_name, team_key,
                  market_key, line, model_mean, model_std,
                  over_prob, under_prob, fair_over_price, fair_under_price,
                  market_over_price, market_under_price, edge_over, edge_under,
                  confidence, diagnostics, worker_build_id, updated_at
                FROM nba_player_prop_model_edges
                WHERE as_of_date = :as_of_date
                  AND model_version = :model_version
                  AND (CAST(:market_key AS text) IS NULL OR market_key = CAST(:market_key AS text))
                  AND (CAST(:team AS text) IS NULL OR team_key = CAST(:team AS text))
                ORDER BY
                  GREATEST(ABS(COALESCE(edge_over, 0)), ABS(COALESCE(edge_under, 0))) DESC,
                  player_name ASC
                LIMIT :limit
                """
            ),
            {
                "as_of_date": target,
                "model_version": model_version,
                "market_key": market_key,
                "team": team.upper() if team else None,
                "limit": limit,
            },
        ).fetchall()

        lines: List[Dict[str, Any]] = []
        for r in rows:
            diag = r[18] if len(r) > 18 else {}
            if isinstance(diag, str):
                try:
                    diag = json.loads(diag)
                except Exception:
                    diag = {}
            if not isinstance(diag, dict):
                diag = {}
            row_tag = str(diag.get("tag") or "PASS").upper()
            if tag_filter and row_tag != tag_filter:
                continue
            lines.append(
                {
                    "model_version": r[0],
                    "as_of_date": r[1],
                    "player_id": r[2],
                    "player_name": r[3],
                    "team": r[4],
                    "market_key": r[5],
                    "line": _to_float(r[6]),
                    "model_mean": _to_float(r[7]),
                    "model_std": _to_float(r[8]),
                    "over_prob": _to_float(r[9]),
                    "under_prob": _to_float(r[10]),
                    "fair_over_price": _to_int(r[11]),
                    "fair_under_price": _to_int(r[12]),
                    "market_over_price": _to_int(r[13]),
                    "market_under_price": _to_int(r[14]),
                    "edge_over": _to_float(r[15]),
                    "edge_under": _to_float(r[16]),
                    "confidence": _to_float(r[17]),
                    "diagnostics": diag,
                    "worker_build_id": r[19],
                    "updated_at": r[20],
                    "stake_eligible": False,
                }
            )

        balance = ou_balance_report(lines)
        return {
            "as_of_date": target,
            "model_version": model_version,
            "worker_build_id": NBA_WORKER_BUILD_ID,
            "count": len(lines),
            "lines": lines,
            "ou_balance": balance,
            "publish_posture": board_publish_posture(),
            "phase": "phase3",
            "message": (
                None
                if lines
                else "No NBA prop edges materialized for this date. Run phase3 props bootstrap."
            ),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"nba_props_board_failed: {exc}") from exc
    finally:
        session.close()


@router.get("/ops/inventory")
def nba_ops_inventory() -> Dict[str, Any]:
    """Live Postgres truth for NBA games/odds/model tables."""
    from src.tasks import collect_nba_db_inventory

    session = SessionLocal()
    try:
        inv = collect_nba_db_inventory(session)
        session.commit()
        inv["worker_build_id"] = NBA_WORKER_BUILD_ID
        inv["phase"] = "phase3"
        return inv
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"nba_inventory_failed: {exc}") from exc
    finally:
        session.close()


@router.post("/simulations/demo")
def nba_demo_simulation(
    home_team: str = Query("Boston Celtics"),
    away_team: str = Query("New York Knicks"),
    simulations: int = Query(2000, ge=300, le=20000),
    seed: int = Query(42),
    model_version: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """Stateless demo sim for canary / desk smoke tests (no DB required)."""
    defaults = default_league_average_inputs(
        game_id="demo-nba",
        home_team=home_team,
        away_team=away_team,
    )
    inputs = NbaGameInputs(**defaults)
    return simulate_nba_game(
        inputs,
        simulations=simulations,
        seed=seed,
        model_version=model_version or DEFAULT_NBA_MODEL_VERSION,
        collect_event_sample=True,
    )


@router.post("/simulations/{game_id}")
def nba_run_single_game_simulation(
    game_id: str,
    simulations: int = Query(4000, ge=300, le=20000),
    model_version: Optional[str] = Query(None),
    persist: bool = Query(True),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        ensure_nba_model_tables(session)
        session.commit()
        effective_model_version = model_version or _resolve_active_model_version(session)

        row = None
        try:
            row = session.execute(
                text(
                    """
                    SELECT
                      g.id AS game_id,
                      home.name AS home_team,
                      away.name AS away_team,
                      c.pace_home, c.pace_away,
                      c.ortg_home, c.ortg_away,
                      c.drtg_home, c.drtg_away,
                      c.three_pt_rate_home, c.three_pt_rate_away,
                      c.three_pt_pct_home, c.three_pt_pct_away,
                      c.rest_days_home, c.rest_days_away,
                      c.sample_games_home, c.sample_games_away,
                      c.feature_pack_version
                    FROM games g
                    JOIN seasons s ON s.id = g.season_id
                    JOIN leagues l ON l.id = s.league_id
                    JOIN teams home ON home.id = g.home_team_id
                    JOIN teams away ON away.id = g.away_team_id
                    LEFT JOIN nba_game_context c ON c.game_id = g.id::text
                    WHERE l.code = 'nba' AND g.id::text = :game_id
                    LIMIT 1
                    """
                ),
                {"game_id": game_id},
            ).fetchone()
        except Exception:
            row = None

        if row is None:
            # Allow demo-style IDs / ingest-only IDs with league averages.
            defaults = default_league_average_inputs(
                game_id=game_id,
                home_team="Home",
                away_team="Away",
            )
            inputs = NbaGameInputs(**defaults)
        else:
            inputs = _inputs_from_context_row(dict(row._mapping))

        seed = abs(hash(f"{game_id}:{effective_model_version}:{simulations}")) % (2**31 - 1)
        projection = simulate_nba_game(
            inputs,
            simulations=simulations,
            seed=seed,
            model_version=effective_model_version,
        )
        if persist:
            _store_projection(session, projection)
            session.commit()
        return projection
    except HTTPException:
        session.rollback()
        raise
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"simulation_failed: {exc}") from exc
    finally:
        session.close()


@router.get("/ops/active-model")
def nba_active_model() -> Dict[str, Any]:
    session = SessionLocal()
    try:
        ensure_nba_model_tables(session)
        session.commit()
        row = session.execute(
            text(
                """
                SELECT state_key, active_model_version, previous_model_version, reason, updated_at
                FROM nba_model_runtime_state
                WHERE state_key = :state_key
                LIMIT 1
                """
            ),
            {"state_key": MODEL_STATE_KEY},
        ).fetchone()
        if not row:
            return {
                "state_key": MODEL_STATE_KEY,
                "active_model_version": DEFAULT_NBA_MODEL_VERSION,
                "previous_model_version": None,
                "reason": "default",
                "worker_build_id": NBA_WORKER_BUILD_ID,
            }
        m = dict(row._mapping)
        m["worker_build_id"] = NBA_WORKER_BUILD_ID
        return m
    finally:
        session.close()


@router.get("/games")
def nba_games(
    game_date: Optional[date] = Query(None),
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        ensure_nba_model_tables(session)
        session.commit()
        target = game_date or date.today()
        games = _fetch_upcoming_games(session, target)
        return {
            "game_date": target,
            "count": len(games),
            "games": [
                {
                    "game_id": g.get("game_id"),
                    "game_date": g.get("game_date"),
                    "start_time": g.get("start_time"),
                    "home_team": g.get("home_team"),
                    "away_team": g.get("away_team"),
                    "home_abbr": normalize_team_key(str(g.get("home_abbr") or g.get("home_team") or "")),
                    "away_abbr": normalize_team_key(str(g.get("away_abbr") or g.get("away_team") or "")),
                    "status": g.get("game_status"),
                    "feature_pack_version": g.get("feature_pack_version"),
                }
                for g in games
            ],
        }
    finally:
        session.close()
