#!/usr/bin/env python3
"""Ablation holdout for narrow second-order factors (E/H/B/A/D).

Method (additive, leakage-safe):
  - Baseline = stored pre-kickoff nfl_market_projections (v3 board).
  - For each factor, compute bounded margin/total deltas from week-lagged
    warehouse features (or stored weather/travel inputs) and apply to the
    stored model spread/total.
  - Re-tag selective PLAY (spread_play_v2_cap7) and grade ATS + movement CLV
    on confirmatory 2024–25 and primary 2025.

Promote rule (same discipline as ST/QB):
  Kill a factor if confirmatory PLAY ATS hit_rate worsens by >0.5pp OR
  movement CLV+ worsens by >1.0pp at comparable n (n drop >15% also fails).

Writes:
  data/ops/nfl-second-order-ablation.json
  data/ops/nfl-second-order-ablation.md
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge"
)

from sqlalchemy import create_engine, text  # noqa: E402

from src.services.nfl_handicapping_framework import (  # noqa: E402
    compute_nfl_projection_decomposition,
    get_nfl_handicapping_config,
)
from src.services.nfl_injury_nowcast import compute_team_info_velocity  # noqa: E402
from src.services.nfl_side_total_publish_policy import (  # noqa: E402
    BREAKEVEN_ATS,
    POLICY_VERSION,
    SPREAD_PLAY_MAX,
    SPREAD_PLAY_MIN,
    candidate_tag,
)

OUT_JSON = ROOT / "data" / "ops" / "nfl-second-order-ablation.json"
OUT_MD = ROOT / "data" / "ops" / "nfl-second-order-ablation.md"

WIN_PROFIT = 100.0 / 110.0
CONFIRMATORY = (2024, 2025)
PRIMARY = 2025
# Strict ST/QB discipline: any confirmatory ATS regression kills the factor.
ATS_WORSEN_PP = 0.0
CLV_WORSEN_PP = 0.01
N_DROP_FRAC = 0.15


def _db_url() -> str:
    url = os.environ.get("DATABASE_URL") or "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge"
    if "postgres:5432" in url:
        url = url.replace("postgres:5432", "127.0.0.1:5432")
    if url.startswith("postgresql://") and "+psycopg" not in url:
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


def _f(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _unit_pnl(won: Optional[bool]) -> float:
    if won is None:
        return 0.0
    return WIN_PROFIT if won else -1.0


def _summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    decided = [r for r in rows if r.get("won") is not None]
    n = len(decided)
    if n == 0:
        return {
            "n": 0,
            "hit_rate": None,
            "roi": None,
            "units": 0.0,
            "n_clv_move": 0,
            "clv_positive_rate": None,
            "mean_abs_edge": None,
            "gate": "RED",
        }
    hits = sum(1 for r in decided if r["won"])
    hit_rate = hits / n
    units = sum(_unit_pnl(r["won"]) for r in decided)
    edges = [float(r["abs_edge"]) for r in decided]
    clv_move = [float(r["clv"]) for r in decided if r.get("clv") is not None and abs(float(r["clv"])) > 1e-9]
    n_clv = len(clv_move)
    clv_pos = (sum(1 for x in clv_move if x > 0) / n_clv) if n_clv else None
    ats_ok = n >= 60 and hit_rate >= BREAKEVEN_ATS
    clv_ok = n_clv >= 200 and clv_pos is not None and clv_pos >= 0.55
    clv_soft = n_clv >= 40 and clv_pos is not None and clv_pos >= 0.55
    if ats_ok and clv_ok:
        gate = "GREEN"
    elif ats_ok and clv_soft:
        gate = "YELLOW"
    elif ats_ok:
        gate = "YELLOW"
    else:
        gate = "RED"
    return {
        "n": n,
        "hits": hits,
        "hit_rate": round(hit_rate, 4),
        "roi": round(units / n, 4),
        "units": round(units, 3),
        "mean_abs_edge": round(sum(edges) / len(edges), 3),
        "n_clv_move": n_clv,
        "clv_positive_rate": round(clv_pos, 4) if clv_pos is not None else None,
        "gate": gate,
    }


def _load_board(conn: Any) -> List[Dict[str, Any]]:
    oc_rows = conn.execute(
        text(
            """
            WITH nfl_games AS (
              SELECT g.id AS game_id
              FROM games g
              JOIN seasons s ON s.id = g.season_id
              JOIN leagues l ON l.id = s.league_id
              WHERE lower(l.code) IN ('nfl', 'americanfootball_nfl')
            ),
            agg AS (
              SELECT
                o.game_id,
                (ARRAY_AGG(o.spread_home ORDER BY o.captured_at ASC)
                  FILTER (WHERE o.spread_home IS NOT NULL))[1] AS open_spread,
                (ARRAY_AGG(o.spread_home ORDER BY o.captured_at DESC)
                  FILTER (WHERE o.spread_home IS NOT NULL))[1] AS close_spread,
                COUNT(*) FILTER (WHERE o.spread_home IS NOT NULL)::int AS n_snaps_spread
              FROM odds_snapshots o
              JOIN nfl_games g ON g.game_id = o.game_id
              GROUP BY o.game_id
            )
            SELECT * FROM agg
            """
        )
    ).mappings().all()
    oc_by = {str(r["game_id"]): dict(r) for r in oc_rows}

    sched = conn.execute(
        text(
            """
            SELECT
              sch.season, sch.week, sch.game_id AS nflverse_game_id,
              sch.home_team, sch.away_team,
              sch.spread_line, sch.total_line,
              sch.home_score, sch.away_score,
              g.id AS game_uuid
            FROM nfl_dp_schedules sch
            JOIN games g ON g.external_id = sch.game_id
            WHERE sch.home_score IS NOT NULL
              AND sch.away_score IS NOT NULL
              AND sch.season BETWEEN 2023 AND 2025
            ORDER BY sch.season, sch.week, sch.game_id
            """
        )
    ).mappings().all()

    # Pull only the input fields needed for H/E/D — full projection jsonb OOMs/hangs locally.
    proj_rows = conn.execute(
        text(
            """
            SELECT DISTINCT ON (mp.game_id)
              mp.game_id, mp.spread_home, mp.total_mean, mp.model_version,
              mp.projection->'inputs' AS inputs
            FROM nfl_market_projections mp
            JOIN games g ON g.id = mp.game_id
            WHERE mp.spread_home IS NOT NULL
              AND mp.total_mean IS NOT NULL
              AND (g.start_time IS NULL OR mp.created_at < g.start_time)
            ORDER BY mp.game_id,
              CASE WHEN mp.projection->'audit'->>'pipeline_run_at' IS NOT NULL THEN 0 ELSE 1 END,
              COALESCE(
                (mp.projection->'audit'->>'pipeline_run_at')::timestamptz,
                mp.created_at
              ) DESC
            """
        )
    ).mappings().all()
    proj_by = {str(r["game_id"]): dict(r) for r in proj_rows}

    rows: List[Dict[str, Any]] = []
    for sch in sched:
        gid = str(sch["game_uuid"]) if sch.get("game_uuid") else None
        if not gid:
            continue
        proj = proj_by.get(gid)
        if not proj:
            continue
        model_spread = _f(proj.get("spread_home"))
        model_total = _f(proj.get("total_mean"))
        if model_spread is None or model_total is None:
            continue
        oc = oc_by.get(gid) or {}
        close_spread = _f(oc.get("close_spread"))
        open_spread = _f(oc.get("open_spread"))
        nflverse_spread = _f(sch.get("spread_line"))
        if close_spread is None and nflverse_spread is not None:
            close_spread = -nflverse_spread
        if close_spread is None:
            continue
        home_margin = float(sch["home_score"]) - float(sch["away_score"])
        season = int(sch["season"])
        week = int(sch["week"])
        inputs_raw = proj.get("inputs")
        if isinstance(inputs_raw, str):
            try:
                inputs_raw = json.loads(inputs_raw)
            except Exception:
                inputs_raw = {}
        inputs = inputs_raw if isinstance(inputs_raw, dict) else {}
        rows.append(
            {
                "game_id": gid,
                "season": season,
                "week": week,
                "home_team": str(sch["home_team"]),
                "away_team": str(sch["away_team"]),
                "model_spread": model_spread,
                "model_total": model_total,
                "close_spread": close_spread,
                "open_spread": open_spread,
                "home_margin": home_margin,
                "inputs": inputs,
                "n_snaps_spread": int(oc.get("n_snaps_spread") or 0),
            }
        )
    return rows


def _load_lagged_second_order(conn: Any) -> Dict[Tuple[int, int, str], Dict[str, Any]]:
    """Map (season, game_week, team) -> week-1 lagged second-order features."""
    out: Dict[Tuple[int, int, str], Dict[str, Any]] = {}
    # Personnel
    try:
        pers = conn.execute(
            text(
                """
                SELECT season, week, team,
                       personnel_edge_5g, personnel_edge
                FROM nfl_dp_personnel_efficiency_weekly
                WHERE season BETWEEN 2023 AND 2025
                """
            )
        ).mappings().all()
    except Exception:
        pers = []
    for r in pers:
        season, week, team = int(r["season"]), int(r["week"]), str(r["team"])
        # as_of week W usable for game week W+1
        key = (season, week + 1, team)
        out.setdefault(key, {})
        out[key]["personnel_edge_5g"] = _f(r.get("personnel_edge_5g") if r.get("personnel_edge_5g") is not None else r.get("personnel_edge"))

    try:
        sub = conn.execute(
            text(
                """
                SELECT season, week, team, AVG(elasticity_5g) AS e
                FROM nfl_dp_substitution_elasticity_weekly
                WHERE season BETWEEN 2023 AND 2025
                  AND position_group IN ('RB','WR','TE','OL')
                GROUP BY season, week, team
                """
            )
        ).mappings().all()
    except Exception:
        sub = []
    for r in sub:
        key = (int(r["season"]), int(r["week"]) + 1, str(r["team"]))
        out.setdefault(key, {})
        out[key]["sub_elasticity_5g"] = _f(r.get("e"))

    try:
        coach = conn.execute(
            text(
                """
                SELECT season, week, team,
                       aggression_latent_5g, aggression_latent,
                       pace_latent_5g, pace_latent
                FROM nfl_coach_aggression_weekly
                WHERE season BETWEEN 2023 AND 2025
                """
            )
        ).mappings().all()
    except Exception:
        coach = []
    for r in coach:
        key = (int(r["season"]), int(r["week"]) + 1, str(r["team"]))
        out.setdefault(key, {})
        out[key]["coach_aggression_5g"] = _f(
            r.get("aggression_latent_5g") if r.get("aggression_latent_5g") is not None else r.get("aggression_latent")
        )
        out[key]["coach_pace_5g"] = _f(
            r.get("pace_latent_5g") if r.get("pace_latent_5g") is not None else r.get("pace_latent")
        )
    return out


def _load_injury_velocity_by_team_week(conn: Any) -> Dict[Tuple[int, int, str], Dict[str, Any]]:
    """Compute WoW info velocity for each team-week using injuries as-of that week vs prior.

    For game week G, use velocity as-of week G-1 (leakage-safe).
    """
    rows = conn.execute(
        text(
            """
            SELECT i.season, i.week, i.team, i.player_key, i.player_name,
                   i.report_status, i.practice_status, i.injury, i.updated_at,
                   r.position
            FROM nfl_dp_injuries i
            LEFT JOIN nfl_dp_rosters r
              ON r.season = i.season AND r.team = i.team AND r.player_id = i.player_id
            WHERE i.season BETWEEN 2023 AND 2025
              AND i.week IS NOT NULL
            """
        )
    ).mappings().all()
    by_tw: Dict[Tuple[int, int, str], List[Dict[str, Any]]] = {}
    for r in rows:
        key = (int(r["season"]), int(r["week"]), str(r["team"]))
        by_tw.setdefault(key, []).append(dict(r))

    vel_asof: Dict[Tuple[int, int, str], Dict[str, Any]] = {}
    for (season, week, team), curr in by_tw.items():
        prior = by_tw.get((season, week - 1, team), [])
        vel = compute_team_info_velocity(curr, prior)
        vel_asof[(season, week, team)] = vel

    # Map to game week = as_of + 1
    for_game: Dict[Tuple[int, int, str], Dict[str, Any]] = {}
    for (season, week, team), vel in vel_asof.items():
        for_game[(season, week + 1, team)] = vel
    return for_game


def _factor_deltas(
    *,
    board_row: Dict[str, Any],
    so_home: Dict[str, Any],
    so_away: Dict[str, Any],
    vel_home: Optional[Dict[str, Any]],
    vel_away: Optional[Dict[str, Any]],
    enabled: Dict[str, bool],
) -> Dict[str, Dict[str, float]]:
    """Return per-factor margin/total deltas under the given enable mask."""
    inputs = board_row.get("inputs") or {}
    cfg = get_nfl_handicapping_config(
        config_overrides={
            "factors": {
                "personnel_efficiency": {"enabled": bool(enabled.get("personnel_efficiency"))},
                "coach_aggression": {"enabled": bool(enabled.get("coach_aggression"))},
                "info_velocity": {"enabled": bool(enabled.get("info_velocity"))},
                "travel_weather_interaction": {"enabled": bool(enabled.get("travel_weather_interaction"))},
                "error_regime": {"enabled": bool(enabled.get("error_regime"))},
            }
        }
    )
    # Use a neutral base so only second-order factors move points.
    decomp = compute_nfl_projection_decomposition(
        offense_index_home=1.0,
        offense_index_away=1.0,
        defense_index_home=1.0,
        defense_index_away=1.0,
        rest_days_home=7.0,
        rest_days_away=7.0,
        matchup_adjustments={},
        totals_adjustments={"stdev_points": 0.0},
        injury_nowcast_impact_home=_f(inputs.get("injury_nowcast_impact_home")),
        injury_nowcast_impact_away=_f(inputs.get("injury_nowcast_impact_away")),
        injury_nowcast_freshness_home_hours=_f(inputs.get("injury_nowcast_freshness_home_hours")),
        injury_nowcast_freshness_away_hours=_f(inputs.get("injury_nowcast_freshness_away_hours")),
        injury_nowcast_confidence_home=_f(inputs.get("injury_nowcast_confidence_home")),
        injury_nowcast_confidence_away=_f(inputs.get("injury_nowcast_confidence_away")),
        injury_nowcast_offense_multiplier_home=_f(inputs.get("injury_nowcast_offense_multiplier_home")),
        injury_nowcast_offense_multiplier_away=_f(inputs.get("injury_nowcast_offense_multiplier_away")),
        injury_nowcast_defense_multiplier_home=_f(inputs.get("injury_nowcast_defense_multiplier_home")),
        injury_nowcast_defense_multiplier_away=_f(inputs.get("injury_nowcast_defense_multiplier_away")),
        weather_available=bool(inputs.get("weather_available")),
        weather_wind_mph=_f(inputs.get("weather_wind_mph")),
        weather_precip_mm=_f(inputs.get("weather_precip_mm")),
        weather_temp_f=_f(inputs.get("weather_temp_f")),
        travel_available=bool(inputs.get("travel_available")),
        travel_miles_home=_f(inputs.get("travel_miles_home")),
        travel_miles_away=_f(inputs.get("travel_miles_away")),
        travel_timezone_delta_home=_f(inputs.get("travel_timezone_delta_home")),
        travel_timezone_delta_away=_f(inputs.get("travel_timezone_delta_away")),
        home_personnel_edge_5g=so_home.get("personnel_edge_5g"),
        away_personnel_edge_5g=so_away.get("personnel_edge_5g"),
        home_sub_elasticity_5g=so_home.get("sub_elasticity_5g"),
        away_sub_elasticity_5g=so_away.get("sub_elasticity_5g"),
        home_coach_aggression_5g=so_home.get("coach_aggression_5g"),
        away_coach_aggression_5g=so_away.get("coach_aggression_5g"),
        home_coach_pace_5g=so_home.get("coach_pace_5g"),
        away_coach_pace_5g=so_away.get("coach_pace_5g"),
        second_order_as_of_week=board_row["week"] - 1 if board_row["week"] > 1 else None,
        info_velocity_home=_f((vel_home or {}).get("velocity_score")),
        info_velocity_away=_f((vel_away or {}).get("velocity_score")),
        hours_since_change_home=_f((vel_home or {}).get("hours_since_change")),
        hours_since_change_away=_f((vel_away or {}).get("hours_since_change")),
        config_overrides={
            "factors": {
                "personnel_efficiency": {"enabled": bool(enabled.get("personnel_efficiency"))},
                "coach_aggression": {"enabled": bool(enabled.get("coach_aggression"))},
                "info_velocity": {"enabled": bool(enabled.get("info_velocity"))},
                "travel_weather_interaction": {"enabled": bool(enabled.get("travel_weather_interaction"))},
                "error_regime": {"enabled": bool(enabled.get("error_regime"))},
                # Zero non-target factors in this neutral shell.
                "base_efficiency": {"margin_weight": 0.0, "total_weight": 0.0, "max_margin_points": 0.0, "max_total_points": 0.0},
                "home_field_advantage": {"margin_points": 0.0},
                "rest_travel": {"margin_per_day": 0.0, "total_per_day_abs": 0.0},
                "injuries_depth": {"margin_weight": 0.0, "total_weight": 0.0},
                "weather_environment": {"enabled": False},
                "travel_schedule": {"enabled": False},
                "situational_flags": {"short_rest_margin_points": 0.0},
                "regression_luck": {"margin_weight": 0.0, "total_weight": 0.0},
                "kav_efficiency": {"enabled": False},
                "external_dvoa": {"enabled": False},
            },
            "priors": {"base_total_points": 0.0, "home_field_points": 0.0},
        },
    )
    contrib = decomp["factor_contributions"]
    keys = [
        "personnel_efficiency",
        "coach_aggression",
        "info_velocity",
        "travel_weather_interaction",
        "error_regime",
    ]
    out: Dict[str, Dict[str, float]] = {}
    for k in keys:
        item = contrib.get(k) or {}
        out[k] = {
            "margin": float(item.get("margin_points") or 0.0),
            "total": float(item.get("total_points") or 0.0),
            "available": 1.0 if item.get("available") else 0.0,
            "stdev_widen": float((item.get("raw_signals") or {}).get("stdev_widen") or 0.0)
            if k == "error_regime"
            else 0.0,
        }
    # Also stash confidence effect for error regime (no point shift).
    out["error_regime"]["confidence_penalty"] = float(
        (decomp.get("uncertainty_penalties") or {}).get("error_regime") or 0.0
    )
    out["_meta"] = {
        "predicted_margin": float(decomp.get("predicted_margin") or 0.0),
        "error_regime_stdev_widen": float(decomp.get("error_regime_stdev_widen") or 0.0),
        "config_max_coach": float(cfg["factors"]["coach_aggression"]["max_margin_points"]),
    }
    return out


def _grade_variant(
    board: List[Dict[str, Any]],
    *,
    so_map: Dict[Tuple[int, int, str], Dict[str, Any]],
    vel_map: Dict[Tuple[int, int, str], Dict[str, Any]],
    enabled: Dict[str, bool],
    seasons: Tuple[int, ...],
) -> Dict[str, Any]:
    plays: List[Dict[str, Any]] = []
    coverage = {k: 0 for k in enabled}
    n_games = 0
    for row in board:
        if row["season"] not in seasons:
            continue
        n_games += 1
        home = row["home_team"]
        away = row["away_team"]
        key_h = (row["season"], row["week"], home)
        key_a = (row["season"], row["week"], away)
        so_h = so_map.get(key_h, {})
        so_a = so_map.get(key_a, {})
        vel_h = vel_map.get(key_h)
        vel_a = vel_map.get(key_a)
        deltas = _factor_deltas(
            board_row=row,
            so_home=so_h,
            so_away=so_a,
            vel_home=vel_h,
            vel_away=vel_a,
            enabled=enabled,
        )
        margin_delta = 0.0
        for k, on in enabled.items():
            if not on:
                continue
            d = deltas.get(k) or {}
            if d.get("available"):
                coverage[k] += 1
            margin_delta += float(d.get("margin") or 0.0)
        # predicted_margin > 0 ⇒ home stronger ⇒ home spread more negative.
        # Match play_only_holdout.py: signed = model_spread - close; lean_home if signed < 0.
        adj_spread = float(row["model_spread"]) - margin_delta
        signed_spread = adj_spread - float(row["close_spread"])
        abs_edge = abs(signed_spread)
        tag = candidate_tag(market="spread", abs_edge=abs_edge)
        if tag != "PLAY":
            continue
        lean_home = signed_spread < 0
        diff = float(row["home_margin"]) + float(row["close_spread"])
        if abs(diff) < 1e-9:
            won = None
        elif lean_home:
            won = True if diff > 1e-9 else False
        else:
            won = True if diff < -1e-9 else False
        clv = None
        if row.get("open_spread") is not None and row["n_snaps_spread"] >= 2:
            clv = (
                (float(row["open_spread"]) - float(row["close_spread"]))
                if lean_home
                else (float(row["close_spread"]) - float(row["open_spread"]))
            )
        plays.append(
            {
                "season": row["season"],
                "week": row["week"],
                "won": won,
                "abs_edge": abs_edge,
                "clv": clv,
            }
        )
    summary = _summary(plays)
    summary["n_games_scanned"] = n_games
    summary["factor_signal_rows"] = coverage
    summary["play_policy"] = POLICY_VERSION
    summary["spread_band"] = [SPREAD_PLAY_MIN, SPREAD_PLAY_MAX]
    return summary


def _promote_decision(baseline: Dict[str, Any], variant: Dict[str, Any]) -> Dict[str, Any]:
    b_hr = baseline.get("hit_rate")
    v_hr = variant.get("hit_rate")
    b_clv = baseline.get("clv_positive_rate")
    v_clv = variant.get("clv_positive_rate")
    b_n = int(baseline.get("n") or 0)
    v_n = int(variant.get("n") or 0)
    reasons: List[str] = []
    promote = True
    if b_hr is None or v_hr is None or b_n < 60 or v_n < 40:
        return {"promote": False, "reasons": ["insufficient_sample"], "delta_hit_rate": None, "delta_clv": None}
    d_hr = float(v_hr) - float(b_hr)
    d_clv = (float(v_clv) - float(b_clv)) if (b_clv is not None and v_clv is not None) else None
    if d_hr < -ATS_WORSEN_PP:
        promote = False
        reasons.append(f"ats_worsened_{d_hr:.4f}")
    if d_clv is not None and d_clv < -CLV_WORSEN_PP:
        promote = False
        reasons.append(f"clv_worsened_{d_clv:.4f}")
    if b_n > 0 and (b_n - v_n) / b_n > N_DROP_FRAC and d_hr <= 0:
        promote = False
        reasons.append("play_n_collapsed_without_ats_gain")
    if promote and d_hr <= 0 and (d_clv is None or d_clv <= 0):
        # Neutral: keep but mark as no-lift (still allowed if not worse).
        reasons.append("no_material_lift_keep_if_not_worse")
    if promote and not reasons:
        reasons.append("clears_worsen_bar")
    return {
        "promote": promote,
        "reasons": reasons,
        "delta_hit_rate": round(d_hr, 4),
        "delta_clv": round(d_clv, 4) if d_clv is not None else None,
        "delta_n": v_n - b_n,
    }


def main() -> int:
    t0 = time.time()
    eng = create_engine(_db_url(), pool_pre_ping=True)
    with eng.connect() as conn:
        print("loading board...", flush=True)
        board = _load_board(conn)
        print(f"board={len(board)} sec={time.time()-t0:.1f}", flush=True)
        print("loading second-order maps...", flush=True)
        so_map = _load_lagged_second_order(conn)
        print(f"so_keys={len(so_map)} sec={time.time()-t0:.1f}", flush=True)
        print("loading info velocity...", flush=True)
        vel_map = _load_injury_velocity_by_team_week(conn)
        print(f"vel_keys={len(vel_map)} sec={time.time()-t0:.1f}", flush=True)
        # Coverage diagnostics
        n_pers = conn.execute(text("SELECT COUNT(*) FROM nfl_dp_personnel_efficiency_weekly")).scalar() or 0
        n_coach = conn.execute(text("SELECT COUNT(*) FROM nfl_coach_aggression_weekly")).scalar() or 0
        n_pers_filled = 0  # public nflverse PBP parquet lacks offense_personnel

    factor_keys = [
        "personnel_efficiency",
        "coach_aggression",
        "info_velocity",
        "travel_weather_interaction",
        "error_regime",
    ]
    off = {k: False for k in factor_keys}
    variants: Dict[str, Dict[str, bool]] = {
        "baseline": dict(off),
        "A_coach": {**off, "coach_aggression": True},
        "B_personnel": {**off, "personnel_efficiency": True},
        "E_info_velocity": {**off, "info_velocity": True},
        "H_travel_weather": {**off, "travel_weather_interaction": True},
        "D_error_regime": {**off, "error_regime": True},
        "all_enabled": {k: True for k in factor_keys},
    }

    results: Dict[str, Any] = {}
    for name, enabled in variants.items():
        print(f"grading {name}...", flush=True)
        results[name] = {
            "enabled": enabled,
            "confirmatory_2024_2025": _grade_variant(
                board, so_map=so_map, vel_map=vel_map, enabled=enabled, seasons=CONFIRMATORY
            ),
            "primary_2025": _grade_variant(
                board, so_map=so_map, vel_map=vel_map, enabled=enabled, seasons=(PRIMARY,)
            ),
            "full_slate_scan_note": "Ablation grades selective PLAY only; full-slate remains product RED unless enterprise gates re-run.",
        }

    baseline_c = results["baseline"]["confirmatory_2024_2025"]
    decisions: Dict[str, Any] = {}
    for name in ["A_coach", "B_personnel", "E_info_velocity", "H_travel_weather", "D_error_regime", "all_enabled"]:
        decisions[name] = _promote_decision(baseline_c, results[name]["confirmatory_2024_2025"])
        # Hard-kill B when warehouse has no personnel signal.
        if name == "B_personnel" and int(n_pers) == 0:
            decisions[name] = {
                "promote": False,
                "reasons": ["no_personnel_signal_coverage_offense_personnel_missing_from_public_pbp"],
                "delta_hit_rate": decisions[name].get("delta_hit_rate"),
                "delta_clv": decisions[name].get("delta_clv"),
                "delta_n": decisions[name].get("delta_n"),
            }

    # Recommended product mask: start from all off, enable only promoted singles.
    # error_regime has 0 point shift — promote if it doesn't collapse PLAY n via confidence
    # (our ablation doesn't re-filter on confidence, so D is always "no point effect";
    # keep enabled for uncertainty only unless PLAY n changes somehow — it shouldn't).
    promoted = []
    killed = []
    for name, dec in decisions.items():
        if name == "all_enabled":
            continue
        # Never promote no-signal factors even if deltas are flat.
        if name == "B_personnel" and int(n_pers) == 0:
            dec["promote"] = False
            reasons = list(dec.get("reasons") or [])
            if "no_personnel_signal_coverage_offense_personnel_missing_from_public_pbp" not in reasons:
                reasons.append("no_personnel_signal_coverage_offense_personnel_missing_from_public_pbp")
            dec["reasons"] = reasons
            decisions[name] = dec
        if dec.get("promote"):
            promoted.append(name)
        else:
            killed.append(name)

    recommended_enabled = {
        "coach_aggression": "A_coach" in promoted,
        "personnel_efficiency": False,  # no warehouse signal
        "info_velocity": "E_info_velocity" in promoted,
        "travel_weather_interaction": "H_travel_weather" in promoted,
        "error_regime": "D_error_regime" in promoted,
    }
    # Re-grade recommended combo
    results["recommended"] = {
        "enabled": recommended_enabled,
        "confirmatory_2024_2025": _grade_variant(
            board, so_map=so_map, vel_map=vel_map, enabled=recommended_enabled, seasons=CONFIRMATORY
        ),
        "primary_2025": _grade_variant(
            board, so_map=so_map, vel_map=vel_map, enabled=recommended_enabled, seasons=(PRIMARY,)
        ),
    }
    decisions["recommended"] = _promote_decision(baseline_c, results["recommended"]["confirmatory_2024_2025"])

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_sec": round(time.time() - t0, 1),
        "method": "additive_delta_on_stored_v3_projections",
        "leakage_rule": "personnel/coach/info_velocity use week G-1 only; weather/travel from stored pre-kickoff inputs",
        "policy": POLICY_VERSION,
        "warehouse": {
            "board_rows_2023_2025": len(board),
            "personnel_weekly_rows": int(n_pers),
            "coach_weekly_rows": int(n_coach),
            "pbp_offense_personnel_filled_2023_2025": int(n_pers_filled),
            "second_order_keys": len(so_map),
            "velocity_game_keys": len(vel_map),
            "visual_crossing_key_present": bool(
                os.getenv("VISUAL_CROSSING_API_KEY") or os.getenv("VISUALCROSSING_API_KEY")
            ),
        },
        "variants": results,
        "decisions": decisions,
        "promoted": promoted,
        "killed": killed,
        "recommended_enabled": recommended_enabled,
        "promote_thresholds": {
            "ats_worsen_pp": ATS_WORSEN_PP,
            "clv_worsen_pp": CLV_WORSEN_PP,
            "n_drop_frac": N_DROP_FRAC,
        },
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2))

    lines = [
        "# NFL Second-Order Ablation Holdout",
        "",
        f"Generated: {payload['generated_at']}",
        f"Policy: `{POLICY_VERSION}`",
        f"Method: additive deltas on stored v3 projections (week−1 lag)",
        "",
        "## Warehouse",
        f"- board rows 2023–25: {payload['warehouse']['board_rows_2023_2025']}",
        f"- coach weekly rows: {n_coach}",
        f"- personnel weekly rows: {n_pers}",
        f"- PBP offense_personnel filled: {n_pers_filled}",
        f"- VC key present: {payload['warehouse']['visual_crossing_key_present']}",
        "",
        "## Confirmatory PLAY (2024–25)",
        "",
        "| Variant | n | ATS | CLV+ (move) | n_clv | Gate | Promote? | ΔATS | ΔCLV |",
        "|---|---:|---:|---:|---:|---|---|---:|---:|",
    ]
    for name in ["baseline", "A_coach", "B_personnel", "E_info_velocity", "H_travel_weather", "D_error_regime", "all_enabled", "recommended"]:
        s = results[name]["confirmatory_2024_2025"]
        dec = decisions.get(name) or {}
        lines.append(
            f"| {name} | {s.get('n')} | {s.get('hit_rate')} | {s.get('clv_positive_rate')} | {s.get('n_clv_move')} | {s.get('gate')} | {dec.get('promote')} | {dec.get('delta_hit_rate')} | {dec.get('delta_clv')} |"
        )
    lines += [
        "",
        "## Primary 2025 PLAY",
        "",
        "| Variant | n | ATS | CLV+ | n_clv | Gate |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for name in ["baseline", "recommended", "all_enabled"]:
        s = results[name]["primary_2025"]
        lines.append(
            f"| {name} | {s.get('n')} | {s.get('hit_rate')} | {s.get('clv_positive_rate')} | {s.get('n_clv_move')} | {s.get('gate')} |"
        )
    lines += [
        "",
        "## Promoted vs killed",
        f"- Promoted: {', '.join(promoted) if promoted else '(none)'}",
        f"- Killed: {', '.join(killed) if killed else '(none)'}",
        f"- Recommended enables: `{json.dumps(recommended_enabled)}`",
        "",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n")
    print(json.dumps({"ok": True, "out_json": str(OUT_JSON), "promoted": promoted, "killed": killed, "recommended_enabled": recommended_enabled, "baseline": baseline_c, "recommended": results["recommended"]["confirmatory_2024_2025"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
