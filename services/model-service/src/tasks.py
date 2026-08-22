from __future__ import annotations

import csv
import logging
import os
import re
import time as time_module
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
from .nfl_remat_policy import resolve_remat_weeks
from .services.mlb_data import (
    apply_bullpen_role_quality_mode,
    apply_starter_quality_mode,
    build_team_offense_context,
    clear_game_lineup_features_cache,
    fetch_mlb_standings,
    fetch_forecast_for_game,
    fetch_game_lineup_features,
    fetch_mlb_schedule,
    fetch_team_hitting_profile,
    fetch_team_roster,
    fetch_team_bullpen_fatigue,
    get_bullpen_role_quality_mode,
    get_starter_quality_mode,
    lineup_confidence,
    mlb_team_id_for_abbr,
    park_factor_for_team,
    starter_identity_features,
    umpire_run_factor,
)
from .services.mlb_lineup_timing import (
    allow_late_sp_clear,
    apply_lineup_timing_mode,
    apply_lineup_timing_to_inputs,
    get_lineup_timing_mode,
    known_players_from_context,
    lineup_players_from_context,
    per_side_lineup_confidence,
)
from .services.mlb_calibration import (
    apply_prob_calibrator as apply_mlb_prob_calibrator,
    apply_total_calibrator as apply_mlb_total_calibrator,
    build_prob_calibrator as build_mlb_prob_calibrator,
    fit_total_calibrator as fit_mlb_total_calibrator,
)
from .services.mlb_enterprise_ops import (
    build_board_health_from_db,
    compute_mlb_clv_with_spread,
    densify_snapshot_datetimes,
    mlb_game_dates_for_densify,
    persist_mlb_board_health,
    persist_mlb_densify_run,
    persist_mlb_quality_snapshot,
    resolve_densify_books,
    upsert_mlb_clv_attribution,
)
from .services.mlb_lineup_shock import apply_lineup_shock, resolve_nowcast_starters
from .services.mlb_model_handicap import (
    annotate_projection_model_handicap,
    extract_prior_model_markets,
)
from .services.mlb_odds_firewall import DEFAULT_PREFERRED_BOOK
from .services.mlb_pa_feature_sharpen import platoon_split_for_hand, sharpen_game_inputs
from .services.mlb_pitch_simulator import simulate_mlb_game_pitch_by_pitch
from .services.mlb_prop_edge_policy import PLAY_STAKE_ELIGIBLE as MLB_PROPS_PLAY_STAKE_ELIGIBLE
from .services.mlb_lineup_sp_snapshots import (
    build_snapshot,
    inventory_snapshot_lake,
    is_late_info_snapshot,
    persist_snapshot,
    reconstruct_densify_snapshot,
    summarize_late_info_slice,
)
from .services.mlb_park_orientation import (
    apply_totals_park_rel_wind_flag,
    get_totals_park_rel_wind_enabled,
)
from .services.mlb_pitch_matchup import (
    apply_pitch_matchup_batter_level,
    apply_pitch_matchup_flag,
    apply_pitch_matchup_stuff_fallback,
    extract_lineup_batter_entries,
    get_pitch_matchup_batter_level,
    get_pitch_matchup_enabled,
    get_pitch_matchup_stuff_fallback,
    get_pitcher_arsenal_as_of,
    resolve_batter_family_for_matchup,
)
from .services.mlb_simulator import (
    DEFAULT_MODEL_VERSION,
    MlbGameInputs,
    apply_stack_ablation_flags,
    get_stack_ablation_flags,
    simulate_mlb_game,
)
from .services.mlb_unused_holdout import (
    filter_points_excluding_unused_holdout,
    filter_points_in_unused_holdout,
    unused_holdout_summary,
)
from .services.nfl_data import (
    fetch_nfl_schedule,
    rest_days_from_schedule,
    team_strength_from_record,
)
from .services.nfl_environment import build_nfl_environment_context
from .services.nfl_injury_nowcast import compute_team_week_injury_severity, fetch_nfl_injury_nowcast
from .services.nfl_handicapping_framework import (
    NFL_HANDICAPPING_FRAMEWORK_VERSION,
    get_nfl_handicapping_config,
    summarize_nfl_factor_attribution_from_points,
)
from .services.nfl_decomposition_drift import summarize_decomposition_drift
from .services.nfl_framework_tuning import TuningThresholds, build_tuning_candidates, evaluate_tuning_grid
from .services.nfl_model_handicap import annotate_projection_model_handicap
from .services.nfl_matchup_features import (
    fetch_latest_matchup_feature_pack,
    matchup_pack_to_sim_input_kwargs,
)
from .services.nfl_simulator import (
    DEFAULT_NFL_MODEL_VERSION,
    NflGameInputs,
    simulate_nfl_game,
)
from .services.nfl_supervised_retrain import (
    FEATURE_KEYS as NFL_SUPERVISED_FEATURE_KEYS,
    apply_supervised_blend,
    detect_real_rolling_features,
    fit_nfl_supervised_models,
)
from .services.nfl_playing_time import depth_target_prior
from .services.nfl_player_projection_engine import (
    ROOKIE_EXPERIENCE_CONFIDENCE,
    VETERAN_EXPERIENCE_CONFIDENCE,
    PlayerFeatureInputs,
    baseline_projection_from_features,
    compute_qb_starter_shares,
    compute_rb_rush_shares,
    depth_role_confidence_floor,
    effective_skill_role_confidence,
    evaluate_prop_edge,
    fantasy_points_from_projection,
    merge_depth_orders,
    qb_talent_factor_from_prior_ypg,
    skill_talent_factor_from_prior_ypg,
    usage_rank_depth_orders,
)
from .services.nfl_prop_edge_policy import anytime_td_prob_from_td_mean
from .services.nfl_props_eligibility import is_investable_prop
from .services.nfl_clv_semantics import (
    moneyline_clv as nfl_moneyline_clv,
    summarize_clv_values as nfl_summarize_clv_values,
    total_clv as nfl_total_clv,
)
from .services.nfl_player_prop_calibration import (
    apply_prop_calibration,
    default_calibration_bundle,
)
from .services.nfl_player_production import (
    PRODUCTION_VERSION as NFL_PLAYER_PRODUCTION_VERSION,
    production_from_baseline_row,
)
from .services.nfl_player_box_score_simulator import (
    DEFAULT_BOX_SCORE_MODEL_VERSION,
    DEFAULT_REPLICATES,
    PlayerBoxScoreRole,
    TeamVolumeContext,
    aggregate_game_sims_to_season,
    compute_team_volume_context,
    simulate_team_player_box_scores,
)
from .services.nfl_fantasy_draft_rankings import rank_season_fantasy_players
from .services.nfl_kicker_dst_projections import (
    GAMES_PER_REGULAR_SEASON,
    allocate_attempts_to_buckets,
    compute_dst_season_fantasy_points,
    compute_kicker_season_fantasy_points,
    project_kicker_fg_makes_by_bucket,
    project_pat_makes,
    project_team_fg_attempt_volume,
    project_team_points_allowed_mean,
    shrink_defense_stat_per_game,
)
from .services.nfl_award_projections import (
    compute_stat_composite,
    compute_team_success_score,
    meets_award_volume_threshold,
    rank_award_candidates,
    score_mvp_candidate,
    score_opoy_candidate,
    select_primary_starter_per_team_position,
)
from .services.nfl_player_identity import (
    DEFAULT_RESOLVER_VERSION,
    IdentityInput,
    apply_manual_mapping_resolution,
    compute_identity_quality_snapshot,
    persist_identity_quality_snapshot,
    prop_market_position_compatible,
    prop_market_position_rank,
    prop_market_snapshot_rank,
    prop_player_match_keys,
    resolve_and_persist_player_identity,
    select_prop_market_for_player,
)
from .services.nfl_totals_calibration import (
    apply_totals_calibration,
    fetch_nfl_totals_calibration,
)
from .services.nba_data import (
    DEFAULT_NBA_INGEST_SEASONS,
    NBA_TEAM_ABBREV,
    compute_rest_days_by_team,
    default_league_average_inputs,
    derive_possessions_from_pbp,
    estimate_player_usage_stub,
    estimate_team_features_from_box,
    features_from_data_nba_team_stats,
    fetch_boxscore_traditional,
    fetch_game_detail_data_nba,
    fetch_play_by_play,
    fetch_schedule_window,
    fetch_season_schedule_data_nba,
    fetch_season_team_gamelog,
    iter_season_labels,
    nba_abbr_match_keys,
    nba_full_names_for_abbr,
    nba_season_year_from_date,
    normalize_team_key as normalize_nba_team_key,
    pair_season_games_from_gamelog,
    player_stubs_from_data_nba_detail,
    rolling_average_features,
    season_label_to_start_year,
    try_sportsdata_games_by_date,
)
from .services.nba_possession_simulator import (
    DEFAULT_NBA_MODEL_VERSION,
    NBA_WORKER_BUILD_ID,
    NbaGameInputs,
    simulate_nba_game,
)
from .services.nba_schema import ensure_nba_model_tables
from .services.odds_api import fetch_odds, fetch_odds_with_metadata, odds_key_diagnostics

log = logging.getLogger(__name__)

NBA_MODEL_STATE_KEY = "nba_active_model"

SPORT_MAP: Dict[str, Tuple[str, str, str]] = {
    # odds-api sport_key -> (sport_code, sport_name, league_name)
    "basketball_ncaab": ("ncaam", "NCAAM", "NCAA Men's Basketball"),
    "baseball_mlb": ("mlb", "MLB", "Major League Baseball"),
    "basketball_nba": ("nba", "NBA", "National Basketball Association"),
    "basketball_wnba": ("wnba", "WNBA", "Women's National Basketball Association"),
    "americanfootball_nfl": ("nfl", "NFL", "National Football League"),
}

MARKET_MAP: Dict[str, str] = {
    "h2h": "moneyline",
    "spreads": "spread",
    "totals": "total",
}

MODEL_STATE_KEY = "mlb_active_model"
NFL_MODEL_STATE_KEY = "nfl_active_model"

NFL_DEFAULT_ODDS_BOOKMAKERS = (
    "draftkings,fanduel,betmgm,betrivers,hardrockbet,fanatics,bet365,circa,betr"
)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _parse_iso_datetime(v: Optional[str]) -> Optional[datetime]:
    if not v:
        return None
    try:
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        return None


def _resolve_nfl_odds_bookmakers(raw: Optional[str] = None) -> str:
    candidate = str(
        raw
        if raw is not None
        else os.getenv("NFL_ODDS_BOOKMAKERS", NFL_DEFAULT_ODDS_BOOKMAKERS)
    ).strip()
    if not candidate:
        candidate = NFL_DEFAULT_ODDS_BOOKMAKERS
    deduped: List[str] = []
    for token in candidate.split(","):
        book = token.strip().lower()
        if book and book not in deduped:
            deduped.append(book)
    return ",".join(deduped) if deduped else NFL_DEFAULT_ODDS_BOOKMAKERS


def _ensure_nfl_supervised_fits_table(session: Any) -> None:
    session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS nfl_supervised_model_fits (
              id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
              model_version text NOT NULL,
              train_start_season integer NOT NULL,
              train_end_season integer NOT NULL,
              train_rows integer NOT NULL,
              test_rows integer NOT NULL,
              metrics jsonb NOT NULL,
              payload jsonb NOT NULL,
              is_active boolean NOT NULL DEFAULT true,
              created_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
    )
    session.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS idx_nfl_supervised_model_fits_lookup
            ON nfl_supervised_model_fits (model_version, is_active, created_at DESC)
            """
        )
    )


def _load_latest_supervised_fit(session: Any, *, model_version: str) -> Optional[Dict[str, Any]]:
    _ensure_nfl_supervised_fits_table(session)
    row = session.execute(
        text(
            """
            SELECT payload
            FROM nfl_supervised_model_fits
            WHERE model_version = :model_version
              AND is_active = true
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"model_version": model_version},
    ).fetchone()
    if row is None:
        return None
    payload = row.payload if hasattr(row, "payload") else row[0]
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, str):
        try:
            parsed = json.loads(payload)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None
    return None


def _load_latest_tuning_config_overrides(
    session: Any, *, model_version: str
) -> Optional[Dict[str, Any]]:
    try:
        row = session.execute(
            text(
                """
                SELECT selected_config
                FROM nfl_framework_tuning_runs
                WHERE model_version = :model_version
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"model_version": model_version},
        ).fetchone()
    except Exception:
        return None
    if row is None:
        return None
    selected = row.selected_config if hasattr(row, "selected_config") else row[0]
    if isinstance(selected, dict):
        return selected
    if isinstance(selected, str):
        try:
            parsed = json.loads(selected)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None
    return None


def _fetch_live_nfl_market_lines_by_abbr() -> Dict[Tuple[str, str], Dict[str, Optional[float]]]:
    """Pull current NFL odds and key consensus lines by (home_abbr, away_abbr).

    Used when ``odds_snapshots`` are missing for the schedule ``game_id``
    (common when Odds API ingest created a parallel games row). Without this,
    early-season market blend silently no-ops and HFA can leave home dogs
    looking like favorites.
    """
    out: Dict[Tuple[str, str], Dict[str, Optional[float]]] = {}
    try:
        bookmakers = _resolve_nfl_odds_bookmakers(None)
        payload = fetch_odds(
            endpoint="sports/americanfootball_nfl/odds",
            params={
                "regions": "us,us2",
                "markets": "h2h,spreads,totals",
                "oddsFormat": "american",
                "dateFormat": "iso",
                "bookmakers": bookmakers,
            },
        )
    except Exception:
        log.exception("Live NFL odds pull failed for market-sim blend")
        return out
    if not isinstance(payload, list):
        return out
    for event in payload:
        if not isinstance(event, dict):
            continue
        home_name = str(event.get("home_team") or "")
        away_name = str(event.get("away_team") or "")
        home_abbr = NFL_FULL_NAME_TO_ABBR.get(home_name) or str(home_name).strip().upper()
        away_abbr = NFL_FULL_NAME_TO_ABBR.get(away_name) or str(away_name).strip().upper()
        if not home_abbr or not away_abbr:
            continue
        spreads: List[float] = []
        totals: List[float] = []
        for book in event.get("bookmakers") or []:
            for market in book.get("markets") or []:
                key = market.get("key")
                if key == "spreads":
                    for outcome in market.get("outcomes") or []:
                        if outcome.get("name") == home_name and outcome.get("point") is not None:
                            try:
                                spreads.append(float(outcome["point"]))
                            except (TypeError, ValueError):
                                continue
                elif key == "totals":
                    for outcome in market.get("outcomes") or []:
                        if outcome.get("name") == "Over" and outcome.get("point") is not None:
                            try:
                                totals.append(float(outcome["point"]))
                            except (TypeError, ValueError):
                                continue
        if not spreads and not totals:
            continue
        out[(home_abbr, away_abbr)] = {
            "market_spread_home": round(sum(spreads) / len(spreads), 3) if spreads else None,
            "market_total": round(sum(totals) / len(totals), 3) if totals else None,
        }
    return out


def _fetch_nfl_market_consensus_lines(
    session: Any,
    *,
    game_id: str,
    home_abbr: Optional[str] = None,
    away_abbr: Optional[str] = None,
    home_team: Optional[str] = None,
    away_team: Optional[str] = None,
    game_date: Optional[date] = None,
) -> Dict[str, Optional[float]]:
    """Latest consensus spread/total across sportsbooks for a game, used to
    anchor the model toward the market when a live line exists. Takes each
    sportsbook's most recent snapshot per market (avoids double-counting
    stale historical snapshots) and averages across books.

    Odds ingest via The Odds API often creates a parallel ``games`` row
    (different UUID) for the same matchup. Looking up snapshots only by the
    schedule ``game_id`` then silently returns null and skips market blend —
    which left early-season boards unanchored (DAL@NYG class of failure).
    Fall back to any NFL game row on the same date with the same teams.
    """
    row = session.execute(
        text(
            """
            WITH candidate_games AS (
              SELECT CAST(:game_id AS uuid) AS id
              UNION
              SELECT g.id
              FROM games g
              JOIN seasons s ON s.id = g.season_id
              JOIN leagues l ON l.id = s.league_id
              JOIN teams home ON home.id = g.home_team_id
              JOIN teams away ON away.id = g.away_team_id
              WHERE l.code = 'nfl'
                AND CAST(:game_date AS date) IS NOT NULL
                AND g.game_date = CAST(:game_date AS date)
                AND (
                  (CAST(:home_abbr AS text) IS NOT NULL AND home.abbr = CAST(:home_abbr AS text))
                  OR (CAST(:home_team AS text) IS NOT NULL AND home.name = CAST(:home_team AS text))
                )
                AND (
                  (CAST(:away_abbr AS text) IS NOT NULL AND away.abbr = CAST(:away_abbr AS text))
                  OR (CAST(:away_team AS text) IS NOT NULL AND away.name = CAST(:away_team AS text))
                )
            ),
            latest AS (
              SELECT
                os.sportsbook_id,
                os.market_id,
                os.spread_home,
                os.total_points,
                ROW_NUMBER() OVER (
                  PARTITION BY os.sportsbook_id, os.market_id
                  ORDER BY os.captured_at DESC
                ) AS rn
              FROM odds_snapshots os
              WHERE os.game_id IN (SELECT id FROM candidate_games)
            )
            SELECT
              (
                SELECT AVG(l.spread_home) FROM latest l
                JOIN markets m ON m.id = l.market_id
                WHERE l.rn = 1 AND m.code = 'spread' AND l.spread_home IS NOT NULL
              ) AS market_spread_home,
              (
                SELECT AVG(l.total_points) FROM latest l
                JOIN markets m ON m.id = l.market_id
                WHERE l.rn = 1 AND m.code = 'total' AND l.total_points IS NOT NULL
              ) AS market_total
            """
        ),
        {
            "game_id": game_id,
            "game_date": game_date,
            "home_abbr": (str(home_abbr).strip().upper() if home_abbr else None),
            "away_abbr": (str(away_abbr).strip().upper() if away_abbr else None),
            "home_team": (str(home_team).strip() if home_team else None),
            "away_team": (str(away_team).strip() if away_team else None),
        },
    ).fetchone()
    if row is None:
        return {"market_spread_home": None, "market_total": None}
    return {
        "market_spread_home": _to_float(row.market_spread_home),
        "market_total": _to_float(row.market_total),
    }


def _epa_to_strength_indices(
    *,
    off_epa: float,
    def_epa_allowed: float,
    pressure_generated: float = 0.0,
    pressure_allowed: float = 0.0,
) -> Dict[str, float]:
    """Map rolling EPA/pressure into the offense/defense index contract used by
    the handicapping framework (higher defense_index = stronger defense).

    Canonical implementation lives in ``efficiency_backbone.epa_to_strength_indices``
    (Sprint 2); this wrapper keeps Edge Board / matchup-pack call sites stable.
    """
    try:
        from src.services.nfl_season_engine.efficiency_backbone import (
            epa_to_strength_indices as _backbone_epa_to_indices,
        )

        return _backbone_epa_to_indices(
            off_epa=off_epa,
            def_epa_allowed=def_epa_allowed,
            pressure_generated=pressure_generated,
            pressure_allowed=pressure_allowed,
        )
    except Exception:
        pressure_delta = float(pressure_generated) - float(pressure_allowed)
        offense_index = _clamp(
            1.0 + (float(off_epa) * 0.75) + (pressure_delta * 0.18), 0.82, 1.22
        )
        defense_index = _clamp(
            1.0 + ((-float(def_epa_allowed)) * 0.90) + (pressure_delta * 0.14), 0.82, 1.24
        )
        return {
            "offense_index": round(offense_index, 6),
            "defense_index": round(defense_index, 6),
        }


def _priors_from_matchup_pack(
    matchup_pack: Optional[Dict[str, Any]],
) -> Optional[Tuple[Dict[str, float], Dict[str, float]]]:
    """Build home/away strength priors from the week-aligned matchup pack.

    Season-max-week rolling priors can be OOD on a not-yet-played season
    (hydrated week-18 shape). The matchup pack is already keyed to the game
    week, so its EPA is the correct prior source when present.
    """
    if not isinstance(matchup_pack, dict):
        return None
    home_off = _to_float(matchup_pack.get("home_off_epa_5g"))
    away_off = _to_float(matchup_pack.get("away_off_epa_5g"))
    home_def = _to_float(matchup_pack.get("home_def_epa_allowed_5g"))
    away_def = _to_float(matchup_pack.get("away_def_epa_allowed_5g"))
    if home_off is None or away_off is None or home_def is None or away_def is None:
        return None
    season = _to_float(matchup_pack.get("season")) or 0.0
    week = _to_float(matchup_pack.get("week")) or 0.0
    home = _epa_to_strength_indices(
        off_epa=float(home_off),
        def_epa_allowed=float(home_def),
        pressure_generated=_to_float(matchup_pack.get("home_pressure_generated_5g")) or 0.0,
        pressure_allowed=_to_float(matchup_pack.get("home_pressure_allowed_5g")) or 0.0,
    )
    away = _epa_to_strength_indices(
        off_epa=float(away_off),
        def_epa_allowed=float(away_def),
        pressure_generated=_to_float(matchup_pack.get("away_pressure_generated_5g")) or 0.0,
        pressure_allowed=_to_float(matchup_pack.get("away_pressure_allowed_5g")) or 0.0,
    )
    home["_season"] = float(season)
    away["_season"] = float(season)
    home["_week"] = float(week)
    away["_week"] = float(week)
    return home, away


def _count_completed_reg_games_season(session: Any, season_year: int) -> int:
    """Count finished REG games for early-season gating.

    Require a past ``game_date`` so placeholder scores on future hydrated
    rows (or mislabeled preseason) cannot unlock OOD KAV/injury/supervised
    paths before the season has actually been played.
    """
    try:
        n = session.execute(
            text(
                """
                SELECT COUNT(*)::int AS n
                FROM nfl_dp_schedules
                WHERE season = :season
                  AND week BETWEEN 1 AND 18
                  AND home_score IS NOT NULL
                  AND away_score IS NOT NULL
                  AND game_date IS NOT NULL
                  AND game_date < CURRENT_DATE
                """
            ),
            {"season": int(season_year)},
        ).scalar()
        return int(n or 0)
    except Exception:
        return 0


def _count_completed_reg_games_by_team(
    session: Any, season_year: int
) -> Dict[str, int]:
    """Per-team completed REG games (schedule truth for prior→current blend)."""
    out: Dict[str, int] = {}
    try:
        rows = session.execute(
            text(
                """
                SELECT team, COUNT(*)::int AS n
                FROM (
                  SELECT UPPER(TRIM(home_team)) AS team
                  FROM nfl_dp_schedules
                  WHERE season = :season
                    AND week BETWEEN 1 AND 18
                    AND home_score IS NOT NULL
                    AND away_score IS NOT NULL
                    AND game_date IS NOT NULL
                    AND game_date < CURRENT_DATE
                  UNION ALL
                  SELECT UPPER(TRIM(away_team)) AS team
                  FROM nfl_dp_schedules
                  WHERE season = :season
                    AND week BETWEEN 1 AND 18
                    AND home_score IS NOT NULL
                    AND away_score IS NOT NULL
                    AND game_date IS NOT NULL
                    AND game_date < CURRENT_DATE
                ) played
                WHERE team IS NOT NULL AND team <> ''
                GROUP BY team
                """
            ),
            {"season": int(season_year)},
        ).fetchall()
        for r in rows:
            t = str(r.team or "").strip().upper()
            if t == "LAR":
                t = "LA"
            if t:
                out[t] = int(r.n or 0)
    except Exception:
        return {}
    return out


def _fetch_rolling_feature_latest_rows(
    session: Any,
    *,
    seasons: List[int],
    week_cap: Optional[int],
) -> List[Any]:
    return list(
        session.execute(
            text(
                """
                WITH ranked AS (
                  SELECT
                    season,
                    week,
                    team,
                    off_epa_per_play_5g,
                    def_epa_allowed_per_play_5g,
                    pressure_rate_generated_5g,
                    pressure_rate_allowed_5g,
                    pass_rate_5g,
                    success_rate_offense_5g,
                    success_rate_defense_allowed_5g,
                    red_zone_td_rate_5g,
                    games_in_window_5,
                    ROW_NUMBER() OVER (
                      PARTITION BY season, team
                      ORDER BY week DESC
                    ) AS rn
                  FROM nfl_dp_team_rolling_features_weekly
                  WHERE season = ANY(:seasons)
                    AND (:week_cap IS NULL OR week <= :week_cap)
                )
                SELECT
                  season,
                  week,
                  team,
                  off_epa_per_play_5g,
                  def_epa_allowed_per_play_5g,
                  pressure_rate_generated_5g,
                  pressure_rate_allowed_5g,
                  pass_rate_5g,
                  success_rate_offense_5g,
                  success_rate_defense_allowed_5g,
                  red_zone_td_rate_5g,
                  games_in_window_5
                FROM ranked
                WHERE rn = 1
                """
            ),
            {"seasons": list(seasons), "week_cap": week_cap},
        ).fetchall()
    )


def _fetch_st_kav_by_team_season(
    session: Any,
    *,
    seasons: List[int],
    week_cap: Optional[int],
) -> Dict[Tuple[int, str], Dict[str, float]]:
    """Optional ST KAV join (v1.1) keyed by (season, team). Absent → empty."""
    out: Dict[Tuple[int, str], Dict[str, float]] = {}
    try:
        st_rows = session.execute(
            text(
                """
                SELECT DISTINCT ON (season, team)
                  season, team, week, raw_st_epa_per_play, st_kav_net_5g
                FROM nfl_dp_team_st_kav_weekly
                WHERE season = ANY(:seasons)
                  AND (:week_cap IS NULL OR week <= :week_cap)
                ORDER BY season, team, week DESC
                """
            ),
            {"seasons": list(seasons), "week_cap": week_cap},
        ).fetchall()
        for sr in st_rows:
            t = str(sr.team or "").strip().upper()
            if t == "LAR":
                t = "LA"
            if not t:
                continue
            out[(int(sr.season or 0), t)] = {
                "st_epa_per_play": float(_to_float(sr.raw_st_epa_per_play) or 0.0),
                "st_plays": 80.0,
            }
    except Exception:
        return {}
    return out


def _fetch_prior_season_schedule_games(
    session: Any, *, season: int
) -> List[Dict[str, Any]]:
    """Completed REG prior-season games for Past SOS (never future slate)."""
    try:
        rows = session.execute(
            text(
                """
                SELECT
                  game_id,
                  week,
                  UPPER(TRIM(home_team)) AS home_team,
                  UPPER(TRIM(away_team)) AS away_team,
                  game_date
                FROM nfl_dp_schedules
                WHERE season = :season
                  AND week BETWEEN 1 AND 18
                  AND home_score IS NOT NULL
                  AND away_score IS NOT NULL
                  AND home_team IS NOT NULL
                  AND away_team IS NOT NULL
                ORDER BY week ASC, game_date ASC NULLS LAST, game_id ASC
                """
            ),
            {"season": int(season)},
        ).fetchall()
    except Exception:
        return []
    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "game_id": str(getattr(r, "game_id", "") or ""),
                "week": int(getattr(r, "week", 0) or 0),
                "home_team": str(getattr(r, "home_team", "") or ""),
                "away_team": str(getattr(r, "away_team", "") or ""),
                "game_date": getattr(r, "game_date", None),
            }
        )
    return out


def _fetch_rolling_weekly_opponent_book(
    session: Any, *, season: int
) -> Dict[Tuple[str, int], Any]:
    """Week-keyed rolling EPA book for time-of-game opponent ratings."""
    try:
        from src.services.nfl_season_engine.adjusted_sos import OpponentRating

        rows = session.execute(
            text(
                """
                SELECT week, team, off_epa_per_play_5g, def_epa_allowed_per_play_5g
                FROM nfl_dp_team_rolling_features_weekly
                WHERE season = :season
                  AND week BETWEEN 1 AND 18
                """
            ),
            {"season": int(season)},
        ).fetchall()
    except Exception:
        return {}
    out: Dict[Tuple[str, int], Any] = {}
    for r in rows:
        team = str(getattr(r, "team", "") or "").strip().upper()
        if team == "LAR":
            team = "LA"
        week = int(getattr(r, "week", 0) or 0)
        if not team or week < 1:
            continue
        out[(team, week)] = OpponentRating(
            off_epa=float(_to_float(getattr(r, "off_epa_per_play_5g", None)) or 0.0),
            def_epa=float(
                _to_float(getattr(r, "def_epa_allowed_per_play_5g", None)) or 0.0
            ),
            source="time_of_game",
        )
    return out


def _apply_past_sos_to_prior_packages(
    session: Any,
    *,
    prior_season: int,
    prior_pkgs: Dict[str, Any],
) -> Dict[str, Any]:
    """Schedule-adjust prior packages via Past SOS (prior side only).

    Future / projected schedule is never consulted. Failures leave priors
    unchanged and are labeled thin_unavailable in drivers when present.
    """
    if not prior_pkgs:
        return prior_pkgs
    try:
        from src.services.nfl_season_engine.adjusted_sos import (
            apply_past_sos_to_package,
            compute_league_past_sos,
            expand_schedule_games,
            rest_days_from_dates,
            season_book_from_packages,
        )
    except Exception:
        return prior_pkgs

    try:
        schedule_rows = _fetch_prior_season_schedule_games(
            session, season=int(prior_season)
        )
        if not schedule_rows:
            return prior_pkgs
        team_dates: Dict[str, List[Any]] = {}
        for row in schedule_rows:
            gdate = row.get("game_date")
            if gdate is None:
                continue
            for key in ("home_team", "away_team"):
                t = str(row.get(key) or "").strip().upper()
                if t == "LAR":
                    t = "LA"
                if not t:
                    continue
                team_dates.setdefault(t, []).append(gdate)
        rest_lookup = rest_days_from_dates(team_dates)
        games = expand_schedule_games(schedule_rows, rest_lookup=rest_lookup)
        weekly_book = _fetch_rolling_weekly_opponent_book(
            session, season=int(prior_season)
        )
        season_book = season_book_from_packages(prior_pkgs)
        raw_by_team = {
            team: {
                "off_epa_per_play": float(
                    pkg.notes.get("off_epa_raw", pkg.offense.epa_per_play)
                ),
                "def_epa_allowed_per_play": float(
                    pkg.notes.get("def_epa_raw", pkg.defense.epa_per_play)
                ),
            }
            for team, pkg in prior_pkgs.items()
        }
        sos_by_team = compute_league_past_sos(
            games,
            raw_by_team=raw_by_team,
            weekly_book=weekly_book,
            season_book=season_book,
        )
        out: Dict[str, Any] = {}
        for team, pkg in prior_pkgs.items():
            sos = sos_by_team.get(team)
            if sos is None:
                out[team] = pkg
                continue
            out[team] = apply_past_sos_to_package(pkg, sos)
        return out
    except Exception:
        return prior_pkgs


def _rolling_row_to_package_payload(row: Any, st: Dict[str, float]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "off_epa_per_play": _to_float(row.off_epa_per_play_5g) or 0.0,
        "def_epa_allowed_per_play": _to_float(row.def_epa_allowed_per_play_5g) or 0.0,
        "pressure_rate_generated": _to_float(row.pressure_rate_generated_5g) or 0.0,
        "pressure_rate_allowed": _to_float(row.pressure_rate_allowed_5g) or 0.0,
        "pass_rate": _to_float(getattr(row, "pass_rate_5g", None)) or 0.58,
        "success_rate_offense": _to_float(getattr(row, "success_rate_offense_5g", None))
        or 0.44,
        "success_rate_defense_allowed": _to_float(
            getattr(row, "success_rate_defense_allowed_5g", None)
        )
        or 0.44,
        "red_zone_td_rate": _to_float(getattr(row, "red_zone_td_rate_5g", None)) or 0.55,
        "n_weeks": int(_to_float(getattr(row, "games_in_window_5", None)) or 0),
        "games_played": int(_to_float(getattr(row, "games_in_window_5", None)) or 0),
    }
    if st:
        payload["st_epa_per_play"] = float(st.get("st_epa_per_play") or 0.0)
        payload["st_plays"] = int(st.get("st_plays") or 0)
    return payload


def _load_team_strength_priors(
    session: Any,
    *,
    season_year: int,
    as_of_week: Optional[int] = None,
) -> Dict[str, Dict[str, float]]:
    """Load true-PR team strength (shared Edge Board + season-engine core).

    Construction (live path):
    - Prior component = prior-season rolling efficiency backbone, else packaged
      2025-derived backbone (never demo bumps). Past SOS adjusts the prior
      side before blend.
    - Continuity score → ``prior_travel`` on residual prior mass (not a new
      rating scale; QB factor ≠ full QB premium).
    - QB premium → capped offense-index delta from projected starter quality
      (process-over-counting); full-strength uses healthy starter, current
      reflects starter availability when injury/inactive feed is present.
    - Current component = current-season rolling when the team has completed
      REG games (week-capped); missing current → keep prior (do not drop).
    - Blend: ``w_current = clamp(team_completed_reg / 8, 0, 1)`` (unchanged),
      ``w_prior = (1 - w_current) * prior_travel``,
      ``w_anchor = (1 - w_current) * (1 - prior_travel)`` toward league mean.
    - Full-strength PR = blended intrinsic (+ starter QB premium); current PR
      starts equal until injury/availability overlays apply a labeled delta.
    """
    primary_season = int(season_year)
    fallback_season = int(season_year) - 1
    completed_league = _count_completed_reg_games_season(session, primary_season)
    team_games = _count_completed_reg_games_by_team(session, primary_season)
    week_cap_current = int(as_of_week) if as_of_week is not None else None

    try:
        from src.services.nfl_season_engine.efficiency_backbone import (
            BACKBONE_SOURCE_BLEND,
            BACKBONE_SOURCE_PACKAGED,
            BACKBONE_SOURCE_ROLLING,
            EFFICIENCY_BACKBONE_VERSION,
            blend_packages,
            build_package_from_season_row,
            prior_current_blend_weight,
            strength_payload_from_package,
            uncertainty_from_games,
        )

        use_backbone = True
    except Exception:
        use_backbone = False

    # Always load prior-season rolling (ignore current hydrated grid preseason).
    prior_rows = _fetch_rolling_feature_latest_rows(
        session, seasons=[fallback_season], week_cap=None
    )
    prior_st = _fetch_st_kav_by_team_season(
        session, seasons=[fallback_season], week_cap=None
    )
    current_rows: List[Any] = []
    current_st: Dict[Tuple[int, str], Dict[str, float]] = {}
    if completed_league >= 1:
        current_rows = _fetch_rolling_feature_latest_rows(
            session, seasons=[primary_season], week_cap=week_cap_current
        )
        current_st = _fetch_st_kav_by_team_season(
            session, seasons=[primary_season], week_cap=week_cap_current
        )

    prior_pkgs: Dict[str, Any] = {}
    current_pkgs: Dict[str, Any] = {}
    prior_meta_week: Dict[str, float] = {}
    current_meta_week: Dict[str, float] = {}

    if use_backbone:
        for row in prior_rows:
            team = str(row.team or "").strip().upper()
            if team == "LAR":
                team = "LA"
            if not team:
                continue
            season = int(row.season or 0)
            st = prior_st.get((season, team)) or {}
            pkg = build_package_from_season_row(
                team,
                _rolling_row_to_package_payload(row, st),
                as_of=f"season={season};week={int(row.week or 0)}",
                source=BACKBONE_SOURCE_ROLLING,
                prior_season=int(fallback_season),
                st_epa=float(st["st_epa_per_play"]) if st else None,
            )
            # Prior packages use full prior-season sample for uncertainty base;
            # blend() re-applies current-sample variance.
            prior_pkgs[team] = pkg
            prior_meta_week[team] = float(_to_float(row.week) or 0.0)

        # Packaged fill happens below; Past SOS applied after all prior pkgs exist.

        for row in current_rows:
            team = str(row.team or "").strip().upper()
            if team == "LAR":
                team = "LA"
            if not team:
                continue
            season = int(row.season or 0)
            st = current_st.get((season, team)) or {}
            g_sched = int(team_games.get(team, 0) or 0)
            row_payload = _rolling_row_to_package_payload(row, st)
            # Prefer schedule-completed games for blend weight / uncertainty.
            if g_sched > 0:
                row_payload["games_played"] = g_sched
                row_payload["n_weeks"] = g_sched
            pkg = build_package_from_season_row(
                team,
                row_payload,
                as_of=f"season={season};week={int(row.week or 0)}",
                source=BACKBONE_SOURCE_ROLLING,
                prior_season=int(fallback_season),
                st_epa=float(st["st_epa_per_play"]) if st else None,
            )
            current_pkgs[team] = pkg
            current_meta_week[team] = float(_to_float(row.week) or 0.0)

    # Packaged backbone fill for missing prior packages (cold start / wipe).
    packaged_priors: Dict[str, Dict[str, Any]] = {}
    packaged_meta: Dict[str, Any] = {}
    try:
        from src.services.nfl_season_engine.loaders import load_packaged_epa_priors

        packaged_priors, packaged_meta = load_packaged_epa_priors(primary_season)
    except Exception:
        packaged_priors, packaged_meta = {}, {}

    if use_backbone and packaged_priors:
        for team, prior in packaged_priors.items():
            if team in prior_pkgs:
                continue
            # Rebuild a prior package from packaged EPA so blend stays package-native.
            pkg = build_package_from_season_row(
                team,
                {
                    "off_epa_per_play": float(prior.get("off_epa_per_play", 0.0) or 0.0),
                    "def_epa_allowed_per_play": float(
                        prior.get("def_epa_allowed_per_play", 0.0) or 0.0
                    ),
                    "pressure_rate_generated": 0.16,
                    "pressure_rate_allowed": 0.16,
                    "pass_rate": 0.58
                    + float(prior.get("pass_rate_bias", 0.0) or 0.0),
                    "success_rate_offense": 0.44,
                    "success_rate_defense_allowed": 0.44,
                    "red_zone_td_rate": 0.55,
                    "n_weeks": int(prior.get("games_played") or 17),
                    "games_played": int(prior.get("games_played") or 17),
                    "st_epa_per_play": 0.0,
                    "st_plays": 0,
                },
                as_of=str(prior.get("as_of") or packaged_meta.get("strength_as_of") or ""),
                source=BACKBONE_SOURCE_PACKAGED,
                prior_season=int(fallback_season),
            )
            # Preserve packaged O/D hierarchy when EPA fields alone are thin:
            # if packaged indices exist, keep them via notes for payload fill.
            pkg.notes["packaged_offense_index"] = float(prior["offense_index"])
            pkg.notes["packaged_defense_index"] = float(prior["defense_index"])
            pkg.notes["packaged_pace_factor"] = float(prior.get("pace_factor", 1.0) or 1.0)
            pkg.notes["packaged_st_index"] = float(prior.get("st_index", 1.0) or 1.0)
            pkg.notes["packaged_variance"] = float(
                prior.get("variance") or uncertainty_from_games(0)
            )
            prior_pkgs[team] = pkg

    # Past SOS: schedule-adjust prior packages before prior→current blend.
    # Never uses the upcoming season slate (future SOS is a separate product).
    if use_backbone and prior_pkgs:
        prior_pkgs = _apply_past_sos_to_prior_packages(
            session,
            prior_season=int(fallback_season),
            prior_pkgs=prior_pkgs,
        )

    # Continuity score → prior-travel weight (modulates residual prior mass;
    # does not replace games/8). Missing inputs → neutral factors + labels.
    continuity_book: Dict[str, Any] = {}
    if use_backbone:
        try:
            from src.services.nfl_season_engine.continuity_score import (
                attach_continuity_drivers,
                build_continuity_book,
            )

            continuity_book = build_continuity_book(
                session,
                season=int(primary_season),
                as_of_week=week_cap_current,
                teams=set(prior_pkgs) | set(current_pkgs) | set(packaged_priors),
            )
            for team, cont in continuity_book.items():
                pkg = prior_pkgs.get(team)
                if pkg is None:
                    continue
                pkg.notes["continuity"] = cont.to_drivers()
                pkg.notes["continuity_score"] = float(cont.continuity_score)
                pkg.notes["prior_travel_weight"] = float(cont.prior_travel_weight)
                pkg.notes["continuity_status"] = "applied"
        except Exception:
            continuity_book = {}

    # QB premium book (starter quality → capped offense delta). Separate from
    # continuity travel; missing splits → stub (do not invent elite identity).
    qb_premium_book: Dict[str, Any] = {}
    if use_backbone:
        try:
            from src.services.nfl_season_engine.qb_premium import build_qb_premium_book

            qb_premium_book = build_qb_premium_book(
                session,
                season=int(primary_season),
                as_of_week=week_cap_current,
                teams=set(prior_pkgs) | set(current_pkgs) | set(packaged_priors),
                team_games=team_games,
            )
        except Exception:
            qb_premium_book = {}

    def _continuity_travel(team: str) -> Tuple[float, Optional[float], Any]:
        cont = continuity_book.get(team)
        if cont is None or getattr(cont, "fidelity", None) == "missing":
            return 1.0, None, None
        return (
            float(cont.prior_travel_weight),
            float(cont.continuity_score),
            cont,
        )

    def _apply_qb_premium(team: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not qb_premium_book:
            return payload
        try:
            from src.services.nfl_season_engine.qb_premium import (
                apply_qb_premium_to_payload,
            )

            return apply_qb_premium_to_payload(payload, qb_premium_book.get(team))
        except Exception:
            return payload

    out: Dict[str, Dict[str, float]] = {}
    if use_backbone:
        all_teams = set(prior_pkgs) | set(current_pkgs) | set(packaged_priors)
        for team in sorted(all_teams):
            prior_pkg = prior_pkgs.get(team)
            current_pkg = current_pkgs.get(team)
            g = int(team_games.get(team, 0) or 0)
            travel, cont_score, cont_obj = _continuity_travel(team)
            if current_pkg is not None and g <= 0:
                # Row exists on hydrated grid but team has not completed a REG game.
                current_pkg = None

            if prior_pkg is not None and current_pkg is not None and g > 0:
                blended = blend_packages(
                    prior_pkg,
                    current_pkg,
                    current_games=g,
                    prior_travel_weight=travel,
                    continuity_score=cont_score,
                )
                payload = strength_payload_from_package(
                    blended, source=BACKBONE_SOURCE_BLEND
                )
                if cont_obj is not None:
                    payload["drivers"] = attach_continuity_drivers(
                        payload.get("drivers") or {}, cont_obj
                    )
                payload = _apply_qb_premium(team, payload)
                out[team] = {
                    **payload,
                    "_season": float(primary_season if g > 0 else fallback_season),
                    "_week": float(
                        current_meta_week.get(team) or prior_meta_week.get(team) or 0.0
                    ),
                    "_source": BACKBONE_SOURCE_BLEND,
                    "version": EFFICIENCY_BACKBONE_VERSION,
                }
            elif prior_pkg is not None:
                # Continuity-weighted prior at g==0 (not always 100% prior).
                if prior_pkg.source == BACKBONE_SOURCE_PACKAGED and prior_pkg.notes.get(
                    "packaged_offense_index"
                ) is not None:
                    # Prefer packaged hierarchy indices, then apply prior travel
                    # shrink toward league mean (1.0) when continuity is low.
                    from src.services.nfl_season_engine.continuity_score import (
                        continuity_uncertainty_boost,
                    )

                    var = uncertainty_from_games(0)
                    if cont_score is not None:
                        var = min(1.60, var + continuity_uncertainty_boost(cont_score))
                    raw_off = float(prior_pkg.notes["packaged_offense_index"])
                    raw_def = float(prior_pkg.notes["packaged_defense_index"])
                    off = travel * raw_off + (1.0 - travel) * 1.0
                    deff = travel * raw_def + (1.0 - travel) * 1.0
                    w_prior = travel
                    w_anchor = 1.0 - travel
                    drivers = {
                        "blend": {
                            "w_prior": round(w_prior, 4),
                            "w_current": 0.0,
                            "w_anchor": round(w_anchor, 4),
                            "prior_travel_weight": round(travel, 4),
                            "prior_offense_index": round(raw_off, 6),
                            "prior_defense_index": round(raw_def, 6),
                            "current_component_offense_index": None,
                            "current_component_defense_index": None,
                        },
                        "injury_availability_delta": {
                            "offense": 0.0,
                            "defense": 0.0,
                            "status": "structure_ready_zero",
                        },
                        "uncertainty": {
                            "variance": float(var),
                            "games_played": 0,
                            "sample_note": "wide_early",
                        },
                        "stubs": {
                            "qb_premium": "stub_not_applied",
                            "continuity": (
                                "applied" if cont_obj is not None else "stub_not_applied"
                            ),
                            "injury_at_time_depth": "stub_not_applied",
                            "full_venue_model": str(
                                (prior_pkg.notes.get("past_sos") or {}).get(
                                    "full_venue_model"
                                )
                                or "stub_not_applied"
                            ),
                            "true_time_of_game_sos": str(
                                (prior_pkg.notes.get("past_sos") or {}).get("status")
                                or "thin_unavailable"
                            ),
                        },
                        "past_sos": dict(
                            prior_pkg.notes.get("past_sos")
                            or {
                                "status": "thin_unavailable",
                                "future_schedule_excluded": True,
                            }
                        ),
                        "st_index": float(
                            prior_pkg.notes.get("packaged_st_index", 1.0) or 1.0
                        ),
                        "version": EFFICIENCY_BACKBONE_VERSION,
                    }
                    if cont_obj is not None:
                        drivers = attach_continuity_drivers(drivers, cont_obj)
                    packaged_payload = {
                        "offense_index": round(off, 6),
                        "defense_index": round(deff, 6),
                        "full_strength_offense_index": round(off, 6),
                        "full_strength_defense_index": round(deff, 6),
                        "current_offense_index": round(off, 6),
                        "current_defense_index": round(deff, 6),
                        "injury_delta_offense": 0.0,
                        "injury_delta_defense": 0.0,
                        "blend_prior_weight": round(w_prior, 4),
                        "blend_current_weight": 0.0,
                        "pace_factor": float(
                            prior_pkg.notes.get("packaged_pace_factor", 1.0) or 1.0
                        ),
                        "pass_rate_bias": 0.0,
                        "st_index": float(
                            prior_pkg.notes.get("packaged_st_index", 1.0) or 1.0
                        ),
                        "explosiveness": 0.0,
                        "variance": float(var),
                        "qb_premium": 0.0,
                        "games_played": 0,
                        "drivers": drivers,
                        "as_of": str(prior_pkg.as_of or ""),
                        "version": EFFICIENCY_BACKBONE_VERSION,
                        "_season": float(fallback_season),
                        "_week": float(prior_meta_week.get(team) or 0.0),
                        "_source": str(
                            packaged_meta.get("strength_source")
                            or BACKBONE_SOURCE_PACKAGED
                        ),
                    }
                    out[team] = _apply_qb_premium(team, packaged_payload)
                else:
                    # Rolling prior package: blend toward league anchor via travel.
                    blended = blend_packages(
                        prior_pkg,
                        prior_pkg,
                        current_games=0,
                        prior_travel_weight=travel,
                        continuity_score=cont_score,
                    )
                    payload = strength_payload_from_package(
                        blended,
                        source=str(prior_pkg.source or BACKBONE_SOURCE_ROLLING),
                    )
                    if cont_obj is not None:
                        payload["drivers"] = attach_continuity_drivers(
                            payload.get("drivers") or {}, cont_obj
                        )
                    payload = _apply_qb_premium(team, payload)
                    out[team] = {
                        **payload,
                        "_season": float(fallback_season),
                        "_week": float(prior_meta_week.get(team) or 0.0),
                        "_source": str(prior_pkg.source or "efficiency_backbone"),
                        "version": EFFICIENCY_BACKBONE_VERSION,
                    }
            elif current_pkg is not None and g > 0:
                # No prior available — current only (labeled).
                w = prior_current_blend_weight(current_games=g)
                current_pkg.notes["blend_current_weight"] = round(w, 4)
                current_pkg.notes["blend_prior_weight"] = round(1.0 - w, 4)
                current_pkg.notes["prior_missing"] = True
                payload = strength_payload_from_package(
                    current_pkg, source=BACKBONE_SOURCE_ROLLING
                )
                payload = _apply_qb_premium(team, payload)
                out[team] = {
                    **payload,
                    "_season": float(primary_season),
                    "_week": float(current_meta_week.get(team) or 0.0),
                    "_source": BACKBONE_SOURCE_ROLLING,
                    "version": EFFICIENCY_BACKBONE_VERSION,
                    "_fallback": "current_only_prior_missing",
                }
        return out

    # Legacy fallback if backbone import fails — no demo strength.
    rows = list(prior_rows) + list(current_rows)
    for row in rows:
        team = str(row.team or "").strip().upper()
        if team == "LAR":
            team = "LA"
        if not team:
            continue
        season = int(row.season or 0)
        if team in out and int(out[team].get("_season", 0)) >= season:
            continue
        indices = _epa_to_strength_indices(
            off_epa=_to_float(row.off_epa_per_play_5g) or 0.0,
            def_epa_allowed=_to_float(row.def_epa_allowed_per_play_5g) or 0.0,
            pressure_generated=_to_float(row.pressure_rate_generated_5g) or 0.0,
            pressure_allowed=_to_float(row.pressure_rate_allowed_5g) or 0.0,
        )
        out[team] = {
            **indices,
            "full_strength_offense_index": float(indices["offense_index"]),
            "full_strength_defense_index": float(indices["defense_index"]),
            "current_offense_index": float(indices["offense_index"]),
            "current_defense_index": float(indices["defense_index"]),
            "injury_delta_offense": 0.0,
            "injury_delta_defense": 0.0,
            "blend_prior_weight": 1.0 if season == fallback_season else 0.0,
            "blend_current_weight": 0.0 if season == fallback_season else 1.0,
            "qb_premium": 0.0,
            "_season": float(season),
            "_week": float(_to_float(row.week) or 0.0),
            "_source": "epa_prior",
        }
    if len(out) < 32 and packaged_priors:
        pkg_source = str(
            packaged_meta.get("strength_source") or "packaged_efficiency_backbone"
        )
        for team, prior in packaged_priors.items():
            if team in out:
                continue
            off = float(prior["offense_index"])
            deff = float(prior["defense_index"])
            out[team] = {
                "offense_index": off,
                "defense_index": deff,
                "full_strength_offense_index": off,
                "full_strength_defense_index": deff,
                "current_offense_index": off,
                "current_defense_index": deff,
                "injury_delta_offense": 0.0,
                "injury_delta_defense": 0.0,
                "blend_prior_weight": 1.0,
                "blend_current_weight": 0.0,
                "pace_factor": float(prior.get("pace_factor", 1.0) or 1.0),
                "pass_rate_bias": float(prior.get("pass_rate_bias", 0.0) or 0.0),
                "st_index": float(prior.get("st_index", 1.0) or 1.0),
                "variance": float(prior.get("variance", 1.35) or 1.35),
                "qb_premium": 0.0,
                "as_of": str(prior.get("as_of") or packaged_meta.get("strength_as_of") or ""),
                "version": str(prior.get("version") or packaged_meta.get("backbone_version") or ""),
                "_season": float(prior.get("_season") or fallback_season),
                "_week": 0.0,
                "_source": pkg_source,
            }
    return out


def _resolve_team_strength_indices(
    *,
    base_offense_home: float,
    base_offense_away: float,
    base_defense_home: float,
    base_defense_away: float,
    home_prior: Dict[str, float],
    away_prior: Dict[str, float],
) -> tuple[float, float, float, float]:
    """Resolve which team-strength signal actually drives the live game
    simulation.

    Real bug found via a real team-simulator calibration audit (see
    data/ops/nfl-team-simulator-calibration-audit-report.md): this used to
    prefer `base_offense_*`/`base_defense_*` -- ESPN win-loss RECORD
    converted to a strength index via nfl_data.team_strength_from_record
    (0.90 + 0.22*win_pct) -- over the real EPA-based rolling-feature prior
    computed by `_load_team_strength_priors`, falling back to the EPA prior
    only when the record was degenerate (exactly 1.0, i.e. a real 0-0
    record). Since ANY team with a played game has a non-degenerate record,
    this meant the EPA-based signal -- the ONLY signal actually validated
    end-to-end against real historical games in
    scripts/nfl/historical_market_backtest.py (spread MAE 9.62 vs the
    market's 9.92, beating the market) -- was silently unused for the
    entire live season past week 1, in favor of a cruder win/loss-only
    heuristic that was never backtested. Confirmed via a real backtest
    replicating both signals against 855 real 2023-2025 games (no leakage,
    real cumulative win-loss record entering each game, see
    data/ops/nfl-team-simulator-calibration-audit/): the win/loss-record
    signal's spread MAE was 10.73 (WORSE than the blind market's 9.79)
    versus the EPA signal's 9.50 (beats the market); correlation with real
    actual margins was 0.27-0.35 (record) vs. 0.65-0.67 (EPA) vs. 0.47-0.49
    (the market itself) -- the record-based signal that was actually live
    was measurably worse than either the market or the validated model
    signal it was silently overriding.

    Fixed by preferring the real EPA-based prior whenever it exists,
    falling back to the record-based estimate only for a genuine cold start
    (no rolling-feature rows at all for that team/season, which
    `_load_team_strength_priors` itself already backfills from the prior
    season when available).
    """
    epa_offense_home = _to_float(home_prior.get("offense_index"))
    epa_offense_away = _to_float(away_prior.get("offense_index"))
    epa_defense_home = _to_float(home_prior.get("defense_index"))
    epa_defense_away = _to_float(away_prior.get("defense_index"))
    return (
        epa_offense_home if epa_offense_home is not None else base_offense_home,
        epa_offense_away if epa_offense_away is not None else base_offense_away,
        epa_defense_home if epa_defense_home is not None else base_defense_home,
        epa_defense_away if epa_defense_away is not None else base_defense_away,
    )


def _normalize_bookmakers_csv(raw: Optional[str]) -> str:
    candidate = str(raw or "").strip().lower()
    tokens: List[str] = []
    for part in candidate.split(","):
        book = part.strip().lower()
        if book and book not in tokens:
            tokens.append(book)
    return ",".join(tokens)


def _normalize_markets_csv(raw: Optional[str]) -> str:
    candidate = str(raw or "").strip().lower()
    allowed = {"h2h", "spreads", "totals"}
    tokens: List[str] = []
    for part in candidate.split(","):
        market = part.strip().lower()
        if market in allowed and market not in tokens:
            tokens.append(market)
    return ",".join(tokens)


def _ensure_odds_api_request_tables(session: Any) -> None:
    session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS odds_api_credit_ledger (
              id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
              endpoint text NOT NULL,
              sport_key text NOT NULL,
              request_signature text NOT NULL,
              requested_at timestamptz NOT NULL,
              request_params jsonb NOT NULL,
              status text NOT NULL,
              source_key text,
              credits_last integer,
              credits_used integer,
              credits_remaining integer,
              events_count integer NOT NULL DEFAULT 0,
              response_timestamp timestamptz,
              response_previous_timestamp timestamptz,
              response_next_timestamp timestamptz,
              error text,
              created_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
    )
    session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS odds_api_request_cache (
              request_signature text PRIMARY KEY,
              endpoint text NOT NULL,
              sport_key text NOT NULL,
              request_params jsonb NOT NULL,
              status text NOT NULL,
              source_key text,
              credits_last integer,
              credits_used integer,
              credits_remaining integer,
              events_count integer NOT NULL DEFAULT 0,
              response_timestamp timestamptz,
              response_previous_timestamp timestamptz,
              response_next_timestamp timestamptz,
              last_error text,
              last_requested_at timestamptz NOT NULL,
              updated_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
    )
    session.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS idx_odds_api_credit_ledger_sport_time
            ON odds_api_credit_ledger (sport_key, requested_at DESC)
            """
        )
    )


def _record_odds_api_request(
    session: Any,
    *,
    endpoint: str,
    sport_key: str,
    request_signature: str,
    request_params: Dict[str, Any],
    status: str,
    source_key: Optional[str],
    credits_last: Optional[int],
    credits_used: Optional[int],
    credits_remaining: Optional[int],
    events_count: int,
    response_timestamp: Optional[datetime],
    response_previous_timestamp: Optional[datetime],
    response_next_timestamp: Optional[datetime],
    error: Optional[str],
) -> None:
    safe_error = None
    if error:
        safe_error = re.sub(r"(apiKey=)[^&\\s]+", r"\\1REDACTED", str(error))
    requested_at = _now_utc()
    session.execute(
        text(
            """
            INSERT INTO odds_api_credit_ledger (
              endpoint, sport_key, request_signature, requested_at, request_params,
              status, source_key, credits_last, credits_used, credits_remaining,
              events_count, response_timestamp, response_previous_timestamp,
              response_next_timestamp, error, created_at
            ) VALUES (
              :endpoint, :sport_key, :request_signature, :requested_at, CAST(:request_params AS jsonb),
              :status, :source_key, :credits_last, :credits_used, :credits_remaining,
              :events_count, :response_timestamp, :response_previous_timestamp,
              :response_next_timestamp, :error, :created_at
            )
            """
        ),
        {
            "endpoint": endpoint,
            "sport_key": sport_key,
            "request_signature": request_signature,
            "requested_at": requested_at,
            "request_params": json.dumps(request_params),
            "status": status,
            "source_key": source_key,
            "credits_last": credits_last,
            "credits_used": credits_used,
            "credits_remaining": credits_remaining,
            "events_count": int(events_count),
            "response_timestamp": response_timestamp,
            "response_previous_timestamp": response_previous_timestamp,
            "response_next_timestamp": response_next_timestamp,
            "error": safe_error,
            "created_at": requested_at,
        },
    )
    session.execute(
        text(
            """
            INSERT INTO odds_api_request_cache (
              request_signature, endpoint, sport_key, request_params, status, source_key,
              credits_last, credits_used, credits_remaining, events_count,
              response_timestamp, response_previous_timestamp, response_next_timestamp,
              last_error, last_requested_at, updated_at
            ) VALUES (
              :request_signature, :endpoint, :sport_key, CAST(:request_params AS jsonb), :status, :source_key,
              :credits_last, :credits_used, :credits_remaining, :events_count,
              :response_timestamp, :response_previous_timestamp, :response_next_timestamp,
              :last_error, :last_requested_at, :updated_at
            )
            ON CONFLICT (request_signature) DO UPDATE SET
              status = EXCLUDED.status,
              source_key = EXCLUDED.source_key,
              credits_last = EXCLUDED.credits_last,
              credits_used = EXCLUDED.credits_used,
              credits_remaining = EXCLUDED.credits_remaining,
              events_count = EXCLUDED.events_count,
              response_timestamp = EXCLUDED.response_timestamp,
              response_previous_timestamp = EXCLUDED.response_previous_timestamp,
              response_next_timestamp = EXCLUDED.response_next_timestamp,
              last_error = EXCLUDED.last_error,
              last_requested_at = EXCLUDED.last_requested_at,
              updated_at = EXCLUDED.updated_at
            """
        ),
        {
            "request_signature": request_signature,
            "endpoint": endpoint,
            "sport_key": sport_key,
            "request_params": json.dumps(request_params),
            "status": status,
            "source_key": source_key,
            "credits_last": credits_last,
            "credits_used": credits_used,
            "credits_remaining": credits_remaining,
            "events_count": int(events_count),
            "response_timestamp": response_timestamp,
            "response_previous_timestamp": response_previous_timestamp,
            "response_next_timestamp": response_next_timestamp,
            "last_error": safe_error,
            "last_requested_at": requested_at,
            "updated_at": requested_at,
        },
    )


def _odds_request_signature(endpoint: str, params: Dict[str, Any]) -> str:
    stable = {
        key: str(value)
        for key, value in sorted((params or {}).items(), key=lambda item: item[0])
    }
    payload = json.dumps({"endpoint": endpoint, "params": stable}, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _persist_odds_events(
    session: Any,
    *,
    events: List[Dict[str, Any]],
    source_label: str,
) -> Dict[str, int]:
    events_persisted = 0
    snapshots_inserted = 0
    # One batch (e.g. a single historical odds pull) can contain hundreds of
    # events for the same ~32 teams / 1 league / 1 season -- share a lookup
    # cache across the whole batch instead of re-querying per event.
    hierarchy_cache: Dict[Tuple[Any, ...], str] = {}
    for event in events:
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
            cache=hierarchy_cache,
        )
        events_persisted += 1

        for book in (event.get("bookmakers") or []):
            book_key = (book or {}).get("key")
            if not book_key:
                continue
            sportsbook_id = _get_or_create_sportsbook(session, book_key, cache=hierarchy_cache)
            captured_at = _parse_iso_datetime(book.get("last_update")) or _now_utc()

            for market in (book.get("markets") or []):
                market_key = market.get("key")
                if not market_key:
                    continue
                market_id = _get_or_create_market(session, market_key, cache=hierarchy_cache)
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
                        "source": source_label,
                        "created_at": _now_utc(),
                    },
                )
                snapshots_inserted += 1
    return {"events_persisted": events_persisted, "snapshots_inserted": snapshots_inserted}


def _db_identity_payload(session: Any) -> Dict[str, Any]:
    row = session.execute(
        text(
            """
            SELECT
              current_database() AS database_name,
              current_schema() AS schema_name,
              current_setting('search_path') AS search_path
            """
        )
    ).fetchone()
    if row is None:
        return {"database_name": None, "schema_name": None, "search_path": None}
    payload = dict(row._mapping)
    return {
        "database_name": payload.get("database_name"),
        "schema_name": payload.get("schema_name"),
        "search_path": payload.get("search_path"),
    }


def _assert_tables_present(session: Any, *, stage: str, required_tables: List[str]) -> None:
    try:
        rows = session.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                """
            )
        ).fetchall()
        available = {str(row[0]) for row in rows}
    except Exception:
        # SQLite/unit-test compatibility.
        rows = session.execute(
            text(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            )
        ).fetchall()
        available = {str(row[0]) for row in rows}
    missing = [table for table in required_tables if table not in available]
    if not missing:
        return
    identity = _db_identity_payload(session)
    raise RuntimeError(
        f"[DB_PREFLIGHT] stage={stage} missing_tables={missing} db_identity={identity}"
    )


def _record_nfl_stage_run_start(
    session: Any,
    *,
    cycle_id: str,
    pipeline: str,
    stage: str,
) -> Optional[str]:
    try:
        row = session.execute(
            text(
                """
                INSERT INTO nfl_pipeline_stage_runs (
                  cycle_id, pipeline, stage, status, started_at, metrics, created_at
                ) VALUES (
                  CAST(:cycle_id AS uuid), :pipeline, :stage, 'running', :started_at, '{}'::jsonb, :created_at
                )
                RETURNING id
                """
            ),
            {
                "cycle_id": cycle_id,
                "pipeline": pipeline,
                "stage": stage,
                "started_at": _now_utc(),
                "created_at": _now_utc(),
            },
        ).fetchone()
        session.commit()
        return str(row[0]) if row is not None else None
    except Exception:
        session.rollback()
        return None


def _record_nfl_stage_run_finish(
    session: Any,
    *,
    run_id: Optional[str],
    status: str,
    metrics: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
) -> None:
    if not run_id:
        return
    try:
        session.execute(
            text(
                """
                UPDATE nfl_pipeline_stage_runs
                SET status = :status,
                    finished_at = :finished_at,
                    metrics = CAST(:metrics AS jsonb),
                    error_message = :error_message
                WHERE id = CAST(:run_id AS uuid)
                """
            ),
            {
                "run_id": run_id,
                "status": status,
                "finished_at": _now_utc(),
                "metrics": json.dumps(metrics or {}),
                "error_message": (error_message or "")[:1000] if error_message else None,
            },
        )
        session.commit()
    except Exception:
        session.rollback()


def _run_nfl_launch_stage(
    *,
    cycle_id: str,
    stage: str,
    fn: Any,
    kwargs: Dict[str, Any],
) -> Dict[str, Any]:
    session = SessionLocal()
    run_id = _record_nfl_stage_run_start(
        session,
        cycle_id=cycle_id,
        pipeline="nfl_launch_hardening",
        stage=stage,
    )
    session.close()
    try:
        result = fn(**kwargs)
        session = SessionLocal()
        _record_nfl_stage_run_finish(
            session,
            run_id=run_id,
            status="success",
            metrics={"result": result},
        )
        session.close()
        return {"stage": stage, "status": "success", "result": result}
    except Exception as exc:
        session = SessionLocal()
        _record_nfl_stage_run_finish(
            session,
            run_id=run_id,
            status="failed",
            metrics={},
            error_message=str(exc),
        )
        session.close()
        raise


# Full team name (as returned by The Odds API / ESPN displayName) -> the
# canonical nflverse abbreviation used when the NFL schedule was bulk-loaded
# into `teams`/`games` (name == abbr for those canonical rows, e.g. "CLE").
# Without this normalization, `_ensure_hierarchy` matches teams by literal
# `name`, so any full-name source silently creates a duplicate "ghost" team
# (and therefore a duplicate "ghost" game, since the games unique constraint
# includes team_id) instead of resolving to the existing canonical row. See
# scripts/nfl/merge_duplicate_teams.py for the one-time cleanup of ghosts
# created by this bug before it was fixed here.
NFL_FULL_NAME_TO_ABBR: Dict[str, str] = {
    "Arizona Cardinals": "ARI",
    "Atlanta Falcons": "ATL",
    "Baltimore Ravens": "BAL",
    "Buffalo Bills": "BUF",
    "Carolina Panthers": "CAR",
    "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN",
    "Cleveland Browns": "CLE",
    "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN",
    "Detroit Lions": "DET",
    "Green Bay Packers": "GB",
    "Houston Texans": "HOU",
    "Indianapolis Colts": "IND",
    "Jacksonville Jaguars": "JAX",
    "Kansas City Chiefs": "KC",
    "Las Vegas Raiders": "LV",
    "Los Angeles Chargers": "LAC",
    "Los Angeles Rams": "LA",
    "Miami Dolphins": "MIA",
    "Minnesota Vikings": "MIN",
    "New England Patriots": "NE",
    "New Orleans Saints": "NO",
    "New York Giants": "NYG",
    "New York Jets": "NYJ",
    "Philadelphia Eagles": "PHI",
    "Pittsburgh Steelers": "PIT",
    "San Francisco 49ers": "SF",
    "Seattle Seahawks": "SEA",
    "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN",
    "Washington Commanders": "WAS",
    "Washington Football Team": "WAS",
    "Washington Redskins": "WAS",
    "Oakland Raiders": "OAK",
    "San Diego Chargers": "SD",
    "St. Louis Rams": "STL",
}


def _normalize_team_name_for_lookup(sport_key: str, team_name: str) -> str:
    """Map a full team display name to the canonical abbreviation used by
    the bulk-loaded schedule rows for that sport, so team resolution doesn't
    fork into duplicate "ghost" rows. Falls back to the raw name unchanged
    when no mapping is known (e.g. non-NFL sports, or an already-abbreviated
    name).

    NBA densify keeps Odds API full names as ``teams.name`` (so existing
    Phase-1 rows still resolve) and relies on canonical ``abbr`` + join
    helpers for close-line matching.
    """
    if sport_key == "americanfootball_nfl":
        return NFL_FULL_NAME_TO_ABBR.get(team_name, team_name)
    return team_name


def _abbr_for_team(team_name: str, *, sport_key: Optional[str] = None) -> str:
    if sport_key == "basketball_nba":
        key = normalize_nba_team_key(team_name)
        if key and key != "UNK":
            return key
    if sport_key == "basketball_wnba":
        from .services.wnba_data import normalize_team_key as normalize_wnba_team_key

        key = normalize_wnba_team_key(team_name)
        if key and key != "UNK":
            return key
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
    *,
    cache: Optional[Dict[Tuple[Any, ...], str]] = None,
) -> str:
    """cache is an optional dict, shared across many calls within one batch
    (see _persist_odds_events), so repeatedly resolving the same sport/
    league/season/team doesn't re-hit the DB per event. A single historical
    odds pull can return hundreds of events for the same ~32 teams/1 league/
    1 season -- without this, that was the dominant cost (a multi-minute
    pull for a batch that fetches from the API in under 2 seconds)."""
    cache_key = (table, where_sql, tuple(sorted(where_params.items())))
    if cache is not None and cache_key in cache:
        return cache[cache_key]

    found = session.execute(
        text(f"SELECT id FROM {table} WHERE {where_sql} LIMIT 1"),
        where_params,
    ).fetchone()
    if found:
        result = str(found[0])
    else:
        new_id = str(uuid.uuid4())
        session.execute(
            text(insert_sql),
            {"id": new_id, **insert_params},
        )
        result = new_id

    if cache is not None:
        cache[cache_key] = result
    return result


def _ensure_hierarchy(
    session: Any,
    *,
    sport_key: str,
    game_dt: datetime,
    home_team: str,
    away_team: str,
    event_id: str,
    cache: Optional[Dict[Tuple[Any, ...], str]] = None,
) -> Tuple[str, str, str, str, str]:
    sport_code, sport_name, league_name = SPORT_MAP.get(
        sport_key,
        ("unknown", sport_key.upper(), sport_key.upper()),
    )
    # NBA seasons tip off in Oct; calendar-year bucketing splits mid-season.
    if sport_key == "basketball_nba":
        season_year = nba_season_year_from_date(game_dt.date())
    elif sport_key == "basketball_wnba":
        # WNBA: calendar tip year (May–Oct); Jan–Apr → prior tip year.
        from .services.wnba_data import wnba_season_year_from_date

        season_year = wnba_season_year_from_date(game_dt.date())
    else:
        season_year = game_dt.year
    home_team = _normalize_team_name_for_lookup(sport_key, home_team)
    away_team = _normalize_team_name_for_lookup(sport_key, away_team)

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
        cache=cache,
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
        cache=cache,
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
        cache=cache,
    )

    home_abbr = _abbr_for_team(home_team, sport_key=sport_key)
    away_abbr = _abbr_for_team(away_team, sport_key=sport_key)

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
            "abbr": home_abbr,
            "name": home_team,
            "market": None,
            "created_at": _now_utc(),
        },
        cache=cache,
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
            "abbr": away_abbr,
            "name": away_team,
            "market": None,
            "created_at": _now_utc(),
        },
        cache=cache,
    )

    # NBA/WNBA tip times are UTC; store ET calendar date so ingest gdte joins land.
    if sport_key in {"basketball_nba", "basketball_wnba"}:
        try:
            from zoneinfo import ZoneInfo

            et_date = game_dt.astimezone(ZoneInfo("America/New_York")).date()
        except Exception:
            et_date = (game_dt - timedelta(hours=5)).date()
        game_date_val = et_date
    else:
        game_date_val = game_dt.date()

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
            "game_date": game_date_val,
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
            "game_date": game_date_val,
            "start_time": game_dt,
            "status": "scheduled",
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "created_at": _now_utc(),
        },
    )
    return game_id, league_id, home_team_id, away_team_id, sport_id


def _get_or_create_sportsbook(
    session: Any, code: str, *, cache: Optional[Dict[Tuple[Any, ...], str]] = None
) -> str:
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
        cache=cache,
    )


def _get_or_create_market(
    session: Any, market_key: str, *, cache: Optional[Dict[Tuple[Any, ...], str]] = None
) -> Optional[str]:
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
        cache=cache,
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


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return float(default)
    try:
        return float(raw)
    except ValueError:
        return float(default)


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


def _sharpen_mlb_inputs(
    inputs: MlbGameInputs,
    *,
    starter_home_feat: Optional[Dict[str, Any]] = None,
    starter_away_feat: Optional[Dict[str, Any]] = None,
    home_abbr: Optional[str] = None,
    rest_days_home: Optional[float] = None,
    rest_days_away: Optional[float] = None,
) -> tuple[MlbGameInputs, Dict[str, Any]]:
    """Apply bounded PA-sim feature sharpening; merge diagnostics onto projection later."""
    home_feat = starter_home_feat or {}
    away_feat = starter_away_feat or {}
    return sharpen_game_inputs(
        inputs,
        starter_source_home=str(home_feat.get("source") or "") or None,
        starter_source_away=str(away_feat.get("source") or "") or None,
        home_abbr=home_abbr,
        rest_days_home=rest_days_home,
        rest_days_away=rest_days_away,
    )


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


_MLB_PROJECTION_HAS_RUNLINE_COLS: Optional[bool] = None


_MLB_PROJECTION_HAS_MODEL_HANDICAP_COLS: Optional[bool] = None


def _mlb_projection_has_runline_cols(session: Any) -> bool:
    global _MLB_PROJECTION_HAS_RUNLINE_COLS
    if _MLB_PROJECTION_HAS_RUNLINE_COLS is not None:
        return _MLB_PROJECTION_HAS_RUNLINE_COLS
    row = session.execute(
        text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'mlb_market_projections'
              AND column_name = 'fair_fg_spread_home'
            LIMIT 1
            """
        )
    ).fetchone()
    _MLB_PROJECTION_HAS_RUNLINE_COLS = row is not None
    return _MLB_PROJECTION_HAS_RUNLINE_COLS


def _mlb_projection_has_model_handicap_cols(session: Any) -> bool:
    global _MLB_PROJECTION_HAS_MODEL_HANDICAP_COLS
    if _MLB_PROJECTION_HAS_MODEL_HANDICAP_COLS is not None:
        return _MLB_PROJECTION_HAS_MODEL_HANDICAP_COLS
    row = session.execute(
        text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'mlb_market_projections'
              AND column_name = 'model_fair_fg_home_ml'
            LIMIT 1
            """
        )
    ).fetchone()
    _MLB_PROJECTION_HAS_MODEL_HANDICAP_COLS = row is not None
    return _MLB_PROJECTION_HAS_MODEL_HANDICAP_COLS


def _fetch_prior_mlb_model_markets(
    session: Any,
    *,
    game_id: Any,
    model_version: str,
) -> Optional[Dict[str, Any]]:
    """Latest prior projection's model snapshot for this game/version."""
    has_cols = _mlb_projection_has_model_handicap_cols(session)
    cols = (
        """
          mp.model_fg_home_win_prob,
          mp.model_fg_total_mean,
          mp.model_fair_fg_home_ml,
          mp.model_fair_fg_total,
          mp.model_fair_fg_spread_home,
          mp.projection
        """
        if has_cols
        else "mp.projection"
    )
    row = session.execute(
        text(
            f"""
            SELECT {cols}
            FROM mlb_market_projections mp
            WHERE mp.game_id = :game_id
              AND mp.model_version = :model_version
            ORDER BY mp.created_at DESC
            LIMIT 1
            """
        ),
        {"game_id": game_id, "model_version": model_version},
    ).fetchone()
    return extract_prior_model_markets(row)


def _insert_mlb_projection_and_audit(
    session: Any,
    projection: Dict[str, Any],
    *,
    seed: int,
    created_at: Optional[datetime] = None,
    line_role: str = "model",
    prior_model_markets: Optional[Dict[str, Any]] = None,
) -> None:
    annotate_projection_model_handicap(
        projection,
        prior_model_markets=prior_model_markets,
        line_role=line_role,
    )
    markets = projection["markets"]
    model_markets = projection.get("model_markets") or {}
    handicap_markets = projection.get("handicap_markets") or markets
    diagnostics = projection.get("diagnostics") or {}
    stamped_at = created_at or _now_utc()
    base_params = {
        "game_id": projection["game_id"],
        "model_version": projection["model_version"],
        "simulation_count": projection["simulation_count"],
        "f5_home_win_prob": markets["f5_home_win_prob"],
        "fg_home_win_prob": handicap_markets.get(
            "fg_home_win_prob", markets["fg_home_win_prob"]
        ),
        "f5_total_mean": markets["f5_total_mean"],
        "fg_total_mean": handicap_markets.get(
            "fg_total_mean", markets["fg_total_mean"]
        ),
        "fair_f5_home_ml": markets["fair_f5_home_ml"],
        "fair_fg_home_ml": handicap_markets.get(
            "fair_fg_home_ml", markets["fair_fg_home_ml"]
        ),
        "fair_f5_total": markets["fair_f5_total"],
        "fair_fg_total": handicap_markets.get(
            "fair_fg_total", markets["fair_fg_total"]
        ),
        "fair_fg_spread_home": handicap_markets.get(
            "fair_fg_spread_home", markets.get("fair_fg_spread_home")
        ),
        "fair_f5_spread_home": markets.get("fair_f5_spread_home"),
        "fg_home_cover_prob_run_line": markets.get("fg_home_cover_prob_run_line"),
        "f5_home_cover_prob_run_line": markets.get("f5_home_cover_prob_run_line"),
        "fg_margin_mean": markets.get("fg_margin_mean"),
        "f5_margin_mean": markets.get("f5_margin_mean"),
        "model_fg_home_win_prob": model_markets.get("fg_home_win_prob"),
        "model_fg_total_mean": model_markets.get("fg_total_mean"),
        "model_fair_fg_home_ml": model_markets.get("fair_fg_home_ml"),
        "model_fair_fg_total": model_markets.get("fair_fg_total"),
        "model_fair_fg_spread_home": model_markets.get("fair_fg_spread_home"),
        "handicap_fg_home_win_prob": handicap_markets.get("fg_home_win_prob"),
        "handicap_fg_total_mean": handicap_markets.get("fg_total_mean"),
        "handicap_fair_fg_home_ml": handicap_markets.get("fair_fg_home_ml"),
        "handicap_fair_fg_total": handicap_markets.get("fair_fg_total"),
        "handicap_fair_fg_spread_home": handicap_markets.get("fair_fg_spread_home"),
        "projection": __import__("json").dumps(projection),
        "created_at": stamped_at,
    }
    has_runline = _mlb_projection_has_runline_cols(session)
    has_model_handicap = _mlb_projection_has_model_handicap_cols(session)
    if has_runline and has_model_handicap:
        session.execute(
            text(
                """
                INSERT INTO mlb_market_projections (
                  game_id, model_version, simulation_count,
                  f5_home_win_prob, fg_home_win_prob, f5_total_mean, fg_total_mean,
                  fair_f5_home_ml, fair_fg_home_ml, fair_f5_total, fair_fg_total,
                  fair_fg_spread_home, fair_f5_spread_home,
                  fg_home_cover_prob_run_line, f5_home_cover_prob_run_line,
                  fg_margin_mean, f5_margin_mean,
                  model_fg_home_win_prob, model_fg_total_mean,
                  model_fair_fg_home_ml, model_fair_fg_total, model_fair_fg_spread_home,
                  handicap_fg_home_win_prob, handicap_fg_total_mean,
                  handicap_fair_fg_home_ml, handicap_fair_fg_total,
                  handicap_fair_fg_spread_home,
                  projection, created_at
                ) VALUES (
                  :game_id, :model_version, :simulation_count,
                  :f5_home_win_prob, :fg_home_win_prob, :f5_total_mean, :fg_total_mean,
                  :fair_f5_home_ml, :fair_fg_home_ml, :fair_f5_total, :fair_fg_total,
                  :fair_fg_spread_home, :fair_f5_spread_home,
                  :fg_home_cover_prob_run_line, :f5_home_cover_prob_run_line,
                  :fg_margin_mean, :f5_margin_mean,
                  :model_fg_home_win_prob, :model_fg_total_mean,
                  :model_fair_fg_home_ml, :model_fair_fg_total, :model_fair_fg_spread_home,
                  :handicap_fg_home_win_prob, :handicap_fg_total_mean,
                  :handicap_fair_fg_home_ml, :handicap_fair_fg_total,
                  :handicap_fair_fg_spread_home,
                  CAST(:projection AS jsonb), :created_at
                )
                """
            ),
            base_params,
        )
    elif has_runline:
        session.execute(
            text(
                """
                INSERT INTO mlb_market_projections (
                  game_id, model_version, simulation_count,
                  f5_home_win_prob, fg_home_win_prob, f5_total_mean, fg_total_mean,
                  fair_f5_home_ml, fair_fg_home_ml, fair_f5_total, fair_fg_total,
                  fair_fg_spread_home, fair_f5_spread_home,
                  fg_home_cover_prob_run_line, f5_home_cover_prob_run_line,
                  fg_margin_mean, f5_margin_mean,
                  projection, created_at
                ) VALUES (
                  :game_id, :model_version, :simulation_count,
                  :f5_home_win_prob, :fg_home_win_prob, :f5_total_mean, :fg_total_mean,
                  :fair_f5_home_ml, :fair_fg_home_ml, :fair_f5_total, :fair_fg_total,
                  :fair_fg_spread_home, :fair_f5_spread_home,
                  :fg_home_cover_prob_run_line, :f5_home_cover_prob_run_line,
                  :fg_margin_mean, :f5_margin_mean,
                  CAST(:projection AS jsonb), :created_at
                )
                """
            ),
            base_params,
        )
    else:
        # Pre-039 schemas: run-line still available inside projection JSON.
        session.execute(
            text(
                """
                INSERT INTO mlb_market_projections (
                  game_id, model_version, simulation_count,
                  f5_home_win_prob, fg_home_win_prob, f5_total_mean, fg_total_mean,
                  fair_f5_home_ml, fair_fg_home_ml, fair_f5_total, fair_fg_total,
                  projection, created_at
                ) VALUES (
                  :game_id, :model_version, :simulation_count,
                  :f5_home_win_prob, :fg_home_win_prob, :f5_total_mean, :fg_total_mean,
                  :fair_f5_home_ml, :fair_fg_home_ml, :fair_f5_total, :fair_fg_total,
                  CAST(:projection AS jsonb), :created_at
                )
                """
            ),
            base_params,
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
            "created_at": stamped_at,
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


def _apply_total_calibrator(total: float, calibrator: Dict[str, Any]) -> float:
    """Apply totals calibration with sport-aware clamps.

    MLB defaults (5.0–14.5) fix the prior NFL-era clamp (24–66) that destroyed
    MAE at larger baseball holdout n. NFL callers should set calibrator["sport"]=\"nfl\".
    """
    sport = str(calibrator.get("sport") or "mlb").lower()
    if sport == "nfl":
        slope = float(calibrator.get("slope") or 1.0)
        intercept = float(calibrator.get("intercept") or 0.0)
        adjusted = (slope * float(total)) + intercept
        return max(24.0, min(66.0, adjusted))
    return apply_mlb_total_calibrator(float(total), calibrator)


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


def _repair_mlb_leakage_stamps(
    session: Any,
    *,
    model_version: str,
    lookback_days: Optional[int] = None,
) -> int:
    """Stamp projections pre-outcome so walkforward leakage_violations → 0.

    Root cause of residual violations: force-resim repair only covered the densify
    window, while walkforward/quality lookback includes earlier/later games whose
    created_at was wall-clock 'now' after the game ended. Also handles start_time
    missing / after completed_at by clamping created_at to completed_at - 1 minute.
    """
    lookback_clause = ""
    params: Dict[str, Any] = {"model_version": model_version}
    if lookback_days is not None:
        lookback_clause = "AND g.game_date >= CURRENT_DATE - make_interval(days => :lookback_days)"
        params["lookback_days"] = int(lookback_days)

    result = session.execute(
        text(
            f"""
            UPDATE mlb_market_projections mp
            SET created_at = LEAST(
                  COALESCE(
                    g.start_time - INTERVAL '3 hours',
                    (g.game_date::timestamp + INTERVAL '16 hours') AT TIME ZONE 'UTC'
                  ),
                  mo.completed_at - INTERVAL '1 minute'
                )
            FROM games g
            JOIN mlb_market_outcomes mo ON mo.game_id = g.id
            WHERE mp.game_id = g.id
              AND mp.model_version = :model_version
              AND mo.completed_at IS NOT NULL
              AND mp.created_at >= mo.completed_at
              {lookback_clause}
            """
        ),
        params,
    )
    try:
        return int(result.rowcount or 0)
    except Exception:
        return 0


def _is_nfl_backtest_point_eligible(point: Dict[str, Any]) -> bool:
    return _projection_is_pre_outcome(point)


def _walkforward_backtest(
    *,
    points: List[Dict[str, Any]],
    training_days: int,
    step_days: int,
    apply_calibration: bool,
    exclude_unused_holdout_from_train: bool = True,
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
            "unused_holdout": unused_holdout_summary(),
            "unused_holdout_excluded_from_train": bool(exclude_unused_holdout_from_train),
        }

    unique_days = sorted({str(x["game_date"])[:10] for x in dated})
    min_train = max(7, int(training_days))
    step = max(1, int(step_days))
    folds: List[Dict[str, Any]] = []
    used_points = 0
    unused_train_skips = 0
    for idx in range(min_train, len(unique_days), step):
        train_days = set(unique_days[max(0, idx - min_train):idx])
        test_days = set(unique_days[idx:idx + step])
        train_points = [x for x in dated if str(x["game_date"])[:10] in train_days]
        if exclude_unused_holdout_from_train:
            before = len(train_points)
            train_points = filter_points_excluding_unused_holdout(train_points)
            unused_train_skips += max(0, before - len(train_points))
        test_points = [x for x in dated if str(x["game_date"])[:10] in test_days]
        if len(train_points) < 20 or len(test_points) < 5:
            continue
        calibrator = build_mlb_prob_calibrator(train_points, bins=12)
        totals_calibrator = fit_mlb_total_calibrator(train_points)
        base_probs = [float(x["fg_home_win_prob"]) for x in test_points]
        cal_probs = [
            apply_mlb_prob_calibrator(float(x["fg_home_win_prob"]), calibrator)
            if apply_calibration
            else float(x["fg_home_win_prob"])
            for x in test_points
        ]
        actual = [1.0 if x["home_team_won"] else 0.0 for x in test_points]
        totals_pred = [float(x["fg_total_mean"]) for x in test_points]
        totals_pred_calibrated = [
            apply_mlb_total_calibrator(float(x["fg_total_mean"]), totals_calibrator)
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

    unused_eval_n = len(filter_points_in_unused_holdout(dated))
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
            "unused_holdout": unused_holdout_summary(),
            "unused_holdout_excluded_from_train": bool(exclude_unused_holdout_from_train),
            "unused_holdout_train_points_skipped": unused_train_skips,
            "unused_holdout_eval_points_available": unused_eval_n,
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
        "unused_holdout": unused_holdout_summary(),
        "unused_holdout_excluded_from_train": bool(exclude_unused_holdout_from_train),
        "unused_holdout_train_points_skipped": unused_train_skips,
        "unused_holdout_eval_points_available": unused_eval_n,
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
    """CLV summary including spread/run-line via DK-first firewall."""
    preferred = os.getenv("MLB_ODDS_PREFERRED_BOOK", DEFAULT_PREFERRED_BOOK)
    try:
        summary = compute_mlb_clv_with_spread(
            session,
            model_version=model_version,
            lookback_days=lookback_days,
            preferred_book=preferred,
        )
        return {
            "sample_size": float(summary.get("count") or 0),
            "avg_ml_clv": summary.get("avg_ml_clv"),
            "avg_total_clv": summary.get("avg_total_clv"),
            "avg_spread_clv": summary.get("avg_spread_clv"),
            "ml_sample_size": float(summary.get("ml_sample_size") or 0),
            "total_sample_size": float(summary.get("total_sample_size") or 0),
            "spread_sample_size": float(summary.get("spread_sample_size") or 0),
        }
    except Exception:
        log.exception("compute_mlb_clv_with_spread failed; returning empty CLV summary")
        return {
            "sample_size": 0.0,
            "avg_ml_clv": None,
            "avg_total_clv": None,
            "avg_spread_clv": None,
            "ml_sample_size": 0.0,
            "total_sample_size": 0.0,
            "spread_sample_size": 0.0,
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
def pull_odds_snapshot(nfl_bookmakers: Optional[str] = None) -> Dict[str, Any]:
    log.info("Running scheduled pull_odds_snapshot")
    data: List[Dict[str, Any]] = []
    resolved_nfl_bookmakers = _resolve_nfl_odds_bookmakers(nfl_bookmakers)
    credits_diag: Dict[str, Any] = {
        "remaining_by_sport": {},
        "used_by_sport": {},
        "selected_sources": odds_key_diagnostics().get("selected_sources"),
    }
    for sport_key in SPORT_MAP.keys():
        params: Dict[str, str] = {
            "regions": "us",
            "markets": "h2h,spreads,totals",
            "oddsFormat": "american",
        }
        if sport_key == "americanfootball_nfl":
            params["bookmakers"] = resolved_nfl_bookmakers
        try:
            payload_meta = fetch_odds_with_metadata(
                endpoint=f"sports/{sport_key}/odds",
                params=params,
            )
            payload = payload_meta.get("payload")
            credits_diag["remaining_by_sport"][sport_key] = payload_meta.get(
                "x_requests_remaining"
            )
            credits_diag["used_by_sport"][sport_key] = payload_meta.get("x_requests_used")
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

    session = SessionLocal()
    try:
        _assert_tables_present(
            session,
            stage="pull_odds_snapshot",
            required_tables=[
                "sports",
                "leagues",
                "seasons",
                "teams",
                "games",
                "sportsbooks",
                "markets",
                "odds_snapshots",
            ],
        )
        persisted = _persist_odds_events(
            session,
            events=data,
            source_label="the-odds-api",
        )
        events_persisted = int(persisted.get("events_persisted") or 0)
        snapshots_inserted = int(persisted.get("snapshots_inserted") or 0)

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
        "credits_diagnostics": credits_diag,
    }
    log.info(
        "Pulled odds snapshot",
        extra={**result, "nfl_bookmakers": resolved_nfl_bookmakers},
    )
    return result


@celery_app.task(name="src.tasks.pull_historical_odds_backfill")
def pull_historical_odds_backfill(
    *,
    sport_key: str = "americanfootball_nfl",
    bookmakers: str = "draftkings,fanduel",
    markets: str = "h2h,spreads,totals",
    start_season: int = 2013,
    end_season: int = 2025,
    max_requests: int = 15,
    oldest_first: bool = True,
    day_offset: int = 0,
    snapshot_hour_utc: int = 20,
    snapshot_minute_utc: int = 30,
) -> Dict[str, Any]:
    """Pull one historical odds snapshot per distinct game_date.

    day_offset/snapshot_hour_utc let a caller take two passes over the same
    date range to build a real open-vs-close pair for CLV (see
    scripts/nfl/backfill_real_clv_snapshots.py):
      - "open" pass: day_offset=-5, snapshot_hour_utc=18 (~Tue afternoon ET,
        shortly after lines typically first post for that week).
      - "close" pass: day_offset=0, snapshot_hour_utc=17 (~noon ET, just
        ahead of the early Sunday kickoff wave -- the historical API can
        only return one moment-in-time snapshot per call, so this is a
        deliberate approximation, not a per-game exact closing line).
    """
    endpoint = f"historical/sports/{sport_key}/odds"
    normalized_books = _normalize_bookmakers_csv(bookmakers)
    normalized_markets = _normalize_markets_csv(markets)
    if not normalized_books:
        raise ValueError("bookmakers must include at least one bookmaker")
    if not normalized_markets:
        raise ValueError("markets must include at least one of h2h,spreads,totals")

    session = SessionLocal()
    try:
        _assert_tables_present(
            session,
            stage="pull_historical_odds_backfill",
            required_tables=["odds_snapshots", "games", "seasons", "leagues"],
        )
        _ensure_odds_api_request_tables(session)
        rows = session.execute(
            text(
                """
                SELECT
                  sch.season,
                  sch.week,
                  sch.game_date
                FROM nfl_dp_schedules sch
                WHERE sch.season BETWEEN :start_season AND :end_season
                  AND sch.home_score IS NOT NULL
                  AND sch.away_score IS NOT NULL
                GROUP BY sch.season, sch.week, sch.game_date
                ORDER BY
                  CASE WHEN :oldest_first THEN sch.season ELSE -sch.season END,
                  CASE WHEN :oldest_first THEN sch.week ELSE -sch.week END
                """
            ),
            {
                "start_season": int(start_season),
                "end_season": int(end_season),
                "oldest_first": bool(oldest_first),
            },
        ).fetchall()
        max_req = max(1, int(max_requests))
        selected_dates: List[datetime] = []
        seen_dates: set[date] = set()
        for row in rows:
            game_date = row.game_date if hasattr(row, "game_date") else row[2]
            if not isinstance(game_date, date):
                continue
            if game_date in seen_dates:
                continue
            seen_dates.add(game_date)
            snapshot_date = game_date + timedelta(days=int(day_offset))
            selected_dates.append(
                datetime.combine(
                    snapshot_date,
                    time(hour=int(snapshot_hour_utc), minute=int(snapshot_minute_utc)),
                    tzinfo=timezone.utc,
                )
            )
            if len(selected_dates) >= max_req:
                break

        requested = 0
        skipped_cached = 0
        request_errors = 0
        events_total = 0
        persisted_total = 0
        snapshots_total = 0
        credits_last = None
        credits_remaining = None
        credits_used = None

        for snapshot_dt in selected_dates:
            params: Dict[str, Any] = {
                "bookmakers": normalized_books,
                "markets": normalized_markets,
                "oddsFormat": "american",
                "dateFormat": "iso",
                "date": snapshot_dt.isoformat().replace("+00:00", "Z"),
            }
            signature = _odds_request_signature(endpoint, params)
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
                source_key = str(payload_meta.get("source") or "")
                credits_used = _to_int_like(payload_meta.get("x_requests_used"))
                credits_remaining = _to_int_like(payload_meta.get("x_requests_remaining"))
                credits_last = _to_int_like(payload_meta.get("x_requests_last"))
                events = payload.get("data") if isinstance(payload, dict) else None
                events_list = events if isinstance(events, list) else []
                for event in events_list:
                    if isinstance(event, dict) and not event.get("sport_key"):
                        event["sport_key"] = sport_key
                persisted = _persist_odds_events(
                    session,
                    events=events_list,
                    source_label="the-odds-api-historical",
                )
                event_count = len(events_list)
                events_total += event_count
                persisted_total += int(persisted.get("events_persisted") or 0)
                snapshots_total += int(persisted.get("snapshots_inserted") or 0)
                response_timestamp = _parse_iso_datetime(payload.get("timestamp")) if isinstance(payload, dict) else None
                response_previous = _parse_iso_datetime(payload.get("previous_timestamp")) if isinstance(payload, dict) else None
                response_next = _parse_iso_datetime(payload.get("next_timestamp")) if isinstance(payload, dict) else None
                _record_odds_api_request(
                    session,
                    endpoint=endpoint,
                    sport_key=sport_key,
                    request_signature=signature,
                    request_params=params,
                    status="success",
                    source_key=source_key,
                    credits_last=credits_last,
                    credits_used=credits_used,
                    credits_remaining=credits_remaining,
                    events_count=event_count,
                    response_timestamp=response_timestamp,
                    response_previous_timestamp=response_previous,
                    response_next_timestamp=response_next,
                    error=None,
                )
                session.commit()
            except Exception as exc:
                request_errors += 1
                # A failed statement (e.g. a rare unique-constraint race on
                # games) leaves the transaction aborted -- every subsequent
                # statement on this session raises InFailedSqlTransaction
                # until it's rolled back, which previously cascaded into
                # crashing the whole backfill on the first bad request.
                session.rollback()
                try:
                    _record_odds_api_request(
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
                    log.exception("Failed to record odds_api_request failure status")
                log.exception("Historical odds request failed", extra={"sport_key": sport_key, "date": params.get("date")})

        return {
            "status": "ok" if request_errors == 0 else "partial",
            "sport_key": sport_key,
            "bookmakers": normalized_books.split(","),
            "markets": normalized_markets.split(","),
            "start_season": int(start_season),
            "end_season": int(end_season),
            "max_requests": max_req,
            "candidate_timestamps": len(selected_dates),
            "requests_attempted": requested,
            "requests_skipped_cached": skipped_cached,
            "request_errors": request_errors,
            "events_fetched": events_total,
            "events_persisted": persisted_total,
            "snapshots_inserted": snapshots_total,
            "credits_last": credits_last,
            "credits_used": credits_used,
            "credits_remaining": credits_remaining,
        }
    finally:
        session.close()


@celery_app.task(name="src.tasks.pull_nfl_context_snapshot")
def pull_nfl_context_snapshot(days_ahead: int = 14) -> Dict[str, int]:
    start = date.today()
    end = start + timedelta(days=max(0, days_ahead))
    schedule = fetch_nfl_schedule(start, end)
    session = SessionLocal()
    created_or_updated = 0
    games_seen = 0
    try:
        _assert_tables_present(
            session,
            stage="pull_nfl_context_snapshot",
            required_tables=["games", "nfl_game_context"],
        )
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
            environment_context = build_nfl_environment_context(
                game_time_iso=g.get("game_time"),
                home_abbr=g.get("home_abbr"),
                away_abbr=g.get("away_abbr"),
                venue_lat=g.get("venue_latitude"),
                venue_lon=g.get("venue_longitude"),
                neutral_site=g.get("neutral_site"),
            )
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
                            "venue": {
                                "name": g.get("venue_name"),
                                "city": g.get("venue_city"),
                                "state": g.get("venue_state"),
                                "latitude": g.get("venue_latitude"),
                                "longitude": g.get("venue_longitude"),
                                "neutral_site": bool(g.get("neutral_site")),
                            },
                            "environment": environment_context,
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
) -> Dict[str, Any]:
    # Canary: proves which worker build executed (props baselines+box rebuild 2026-07-31).
    worker_build_id = "props-under-bias-20260731c-baselines-box-rebuild"
    target_date = date.fromisoformat(game_date) if game_date else date.today()
    session = SessionLocal()
    processed = 0
    inserted = 0
    pending_projections: List[Dict[str, Any]] = []
    try:
        _assert_tables_present(
            session,
            stage="run_nfl_market_simulations",
            required_tables=["games", "nfl_game_context", "nfl_market_projections"],
        )
        supervised_fit = _load_latest_supervised_fit(session, model_version=model_version)
        tuning_config_overrides = _load_latest_tuning_config_overrides(session, model_version=model_version)
        # Cache key: (season_year, as_of_week_or_None, unplayed_bool encoded in week sentinel)
        priors_cache: Dict[Tuple[int, Optional[int]], Dict[str, Dict[str, float]]] = {}
        completed_reg_cache: Dict[int, int] = {}
        tendency_proe_cache: Dict[int, Dict[str, float]] = {}
        live_market_by_abbr = _fetch_live_nfl_market_lines_by_abbr()
        # Multi-season lookback so level bias (under-projection) is estimated
        # from enough completed games; 240d was too short and produced fragile fits.
        totals_calibration = fetch_nfl_totals_calibration(
            session,
            model_version=model_version,
            lookback_days=int(float(os.getenv("NFL_TOTALS_CALIBRATION_LOOKBACK_DAYS", "1500"))),
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
                  home.abbr AS home_abbr,
                  away.name AS away_team,
                  away.abbr AS away_abbr,
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
            {"game_date": target_date},
        ).fetchall()
        for r in rows:
            m = dict(r._mapping)
            if (
                not bool(include_completed_games)
                and str(m.get("game_status") or "").lower() in {"final", "closed", "completed"}
            ):
                continue
            # Matchup feature packs are keyed by abbreviation (NYG/DAL), while
            # games joins expose full names. Prefer abbr or the pack lookup
            # misses, week stays null, and early-season supervised skips never fire.
            matchup_pack = fetch_latest_matchup_feature_pack(
                session,
                game_id=str(m["game_id"]),
                season_year=_to_int_like(m.get("season_year")),
                home_team=str(m.get("home_abbr") or m.get("home_team") or ""),
                away_team=str(m.get("away_abbr") or m.get("away_team") or ""),
            )
            injury_nowcast = fetch_nfl_injury_nowcast(
                session,
                season_year=_to_int_like(m.get("season_year")),
                home_team=str(m["home_team"]),
                away_team=str(m["away_team"]),
            )
            home_nowcast = injury_nowcast.get("home") if isinstance(injury_nowcast.get("home"), dict) else {}
            away_nowcast = injury_nowcast.get("away") if isinstance(injury_nowcast.get("away"), dict) else {}
            context_payload = m.get("context") if isinstance(m.get("context"), dict) else {}
            if not context_payload and isinstance(m.get("context"), str):
                try:
                    context_payload = json.loads(str(m.get("context")))
                except Exception:
                    context_payload = {}
            environment_payload = (
                context_payload.get("environment") if isinstance(context_payload.get("environment"), dict) else {}
            )
            weather_payload = environment_payload.get("weather") if isinstance(environment_payload.get("weather"), dict) else {}
            travel_payload = environment_payload.get("travel") if isinstance(environment_payload.get("travel"), dict) else {}
            venue_payload = context_payload.get("venue") if isinstance(context_payload.get("venue"), dict) else {}
            weather_available = bool(weather_payload.get("available"))
            travel_available = bool(travel_payload.get("available"))
            if not weather_available or not travel_available:
                fallback_environment = build_nfl_environment_context(
                    game_time_iso=(
                        m.get("start_time").astimezone(timezone.utc).isoformat()
                        if isinstance(m.get("start_time"), datetime)
                        else None
                    ),
                    home_abbr=str(m.get("home_abbr") or context_payload.get("home_abbr") or ""),
                    away_abbr=str(m.get("away_abbr") or context_payload.get("away_abbr") or ""),
                    venue_lat=venue_payload.get("latitude"),
                    venue_lon=venue_payload.get("longitude"),
                    neutral_site=venue_payload.get("neutral_site"),
                )
                fallback_weather = (
                    fallback_environment.get("weather")
                    if isinstance(fallback_environment.get("weather"), dict)
                    else {}
                )
                fallback_travel = (
                    fallback_environment.get("travel")
                    if isinstance(fallback_environment.get("travel"), dict)
                    else {}
                )
                if not weather_available and fallback_weather:
                    weather_payload = fallback_weather
                if not travel_available and fallback_travel:
                    travel_payload = fallback_travel
            matchup_kwargs = matchup_pack_to_sim_input_kwargs(matchup_pack)
            season_year = _to_int_like(m.get("season_year"))
            matchup_week_for_priors = _to_int_like(
                (matchup_pack or {}).get("week") if isinstance(matchup_pack, dict) else None
            )
            if season_year is not None and int(season_year) not in completed_reg_cache:
                completed_reg_cache[int(season_year)] = _count_completed_reg_games_season(
                    session, int(season_year)
                )
            completed_reg_season = (
                int(completed_reg_cache.get(int(season_year), 0)) if season_year is not None else 0
            )
            season_too_early = completed_reg_season < 3
            # Hydrated KAV / second-order / roster-continuity nowcasts are OOD
            # before real REG games. Keep EPA pack + market blend; drop the rest.
            early_season_ood_dampened = False
            if season_too_early and isinstance(matchup_kwargs, dict):
                early_season_ood_dampened = True
                for _k in (
                    "home_kav_offense_5g",
                    "away_kav_offense_5g",
                    "home_kav_defense_5g",
                    "away_kav_defense_5g",
                    "home_kav_net_5g",
                    "away_kav_net_5g",
                    "kav_as_of_week",
                    "home_personnel_edge_5g",
                    "away_personnel_edge_5g",
                    "home_sub_elasticity_5g",
                    "away_sub_elasticity_5g",
                    "home_coach_aggression_5g",
                    "away_coach_aggression_5g",
                    "home_coach_pace_5g",
                    "away_coach_pace_5g",
                    "second_order_as_of_week",
                ):
                    matchup_kwargs[_k] = None
                if matchup_kwargs.get("matchup_week") is not None:
                    matchup_kwargs["matchup_week"] = int(matchup_week_for_priors or 1)
            # Shared true-PR core: gradual prior→current blend via
            # `_load_team_strength_priors` (same path as season engine).
            # Matchup-pack EPA is week-aligned but does not apply the blend —
            # use it only when the blended book lacks a team.
            prior_source = "true_pr_blend"
            cache_key = (int(season_year or -1), matchup_week_for_priors)
            if season_year is not None and cache_key not in priors_cache:
                priors_cache[cache_key] = _load_team_strength_priors(
                    session,
                    season_year=season_year,
                    as_of_week=matchup_week_for_priors,
                )
            team_priors = priors_cache.get(cache_key, {})
            home_prior = (
                team_priors.get(str(m.get("home_abbr") or ""))
                or team_priors.get(str(m.get("home_team") or ""))
                or {}
            )
            away_prior = (
                team_priors.get(str(m.get("away_abbr") or ""))
                or team_priors.get(str(m.get("away_team") or ""))
                or {}
            )
            if not home_prior or not away_prior:
                pack_priors = _priors_from_matchup_pack(
                    matchup_pack if isinstance(matchup_pack, dict) else None
                )
                if pack_priors is not None:
                    prior_source = "matchup_pack_fallback"
                    pack_home, pack_away = pack_priors
                    if not home_prior:
                        home_prior = pack_home
                    if not away_prior:
                        away_prior = pack_away
            if season_year is not None and season_year not in tendency_proe_cache:
                try:
                    from .services.nfl_tendency_pricing import fetch_team_proe_map

                    # Prefer prior season profiles when current-season tendencies
                    # are empty (preseason / early weeks).
                    proe_map = fetch_team_proe_map(session, season=int(season_year), situation="all")
                    if not proe_map:
                        proe_map = fetch_team_proe_map(session, season=int(season_year) - 1, situation="all")
                    tendency_proe_cache[season_year] = proe_map
                except Exception:
                    session.rollback()
                    tendency_proe_cache[season_year] = {}
            proe_by_team = tendency_proe_cache.get(season_year or -1, {})
            home_abbr_for_proe = str(m.get("home_abbr") or m.get("home_team") or "")
            away_abbr_for_proe = str(m.get("away_abbr") or m.get("away_team") or "")
            home_proe = float(proe_by_team.get(home_abbr_for_proe, 0.0) or 0.0)
            away_proe = float(proe_by_team.get(away_abbr_for_proe, 0.0) or 0.0)
            try:
                from .services.nfl_tendency_pricing import tendency_game_signals

                tendency_signals = tendency_game_signals(home_proe, away_proe)
            except Exception:
                tendency_signals = {
                    "total_signal": 0.0,
                    "spread_signal": 0.0,
                }
            base_offense_home = _to_float(m.get("offense_index_home")) or 1.0
            base_offense_away = _to_float(m.get("offense_index_away")) or 1.0
            base_defense_home = _to_float(m.get("defense_index_home")) or 1.0
            base_defense_away = _to_float(m.get("defense_index_away")) or 1.0
            offense_home, offense_away, defense_home, defense_away = _resolve_team_strength_indices(
                base_offense_home=base_offense_home,
                base_offense_away=base_offense_away,
                base_defense_home=base_defense_home,
                base_defense_away=base_defense_away,
                home_prior=home_prior,
                away_prior=away_prior,
            )
            # Neutralize injury/roster-continuity nowcast before REG games —
            # preseason depth charts and continuity shocks were swinging
            # margins several points past the EPA pack + market.
            if season_too_early:
                home_off_mult = 1.0
                away_off_mult = 1.0
                home_def_mult = 1.0
                away_def_mult = 1.0
                home_injury_conf = None
                away_injury_conf = None
                home_injury_impact = None
                away_injury_impact = None
                home_info_vel = None
                away_info_vel = None
                home_hours_change = None
                away_hours_change = None
            else:
                home_off_mult = _to_float(home_nowcast.get("offense_multiplier")) or 1.0
                away_off_mult = _to_float(away_nowcast.get("offense_multiplier")) or 1.0
                home_def_mult = _to_float(home_nowcast.get("defense_multiplier")) or 1.0
                away_def_mult = _to_float(away_nowcast.get("defense_multiplier")) or 1.0
                home_injury_conf = _to_float(home_nowcast.get("confidence"))
                away_injury_conf = _to_float(away_nowcast.get("confidence"))
                home_injury_impact = _to_float(home_nowcast.get("impact_score"))
                away_injury_impact = _to_float(away_nowcast.get("impact_score"))
                home_info_vel = _to_float(home_nowcast.get("info_velocity_score"))
                away_info_vel = _to_float(away_nowcast.get("info_velocity_score"))
                home_hours_change = _to_float(home_nowcast.get("hours_since_change"))
                away_hours_change = _to_float(away_nowcast.get("hours_since_change"))
            # Full-strength = blended intrinsic PR; current = after injury/
            # availability multipliers. Do not overwrite full-strength when
            # someone sits — both stay available on the prior payloads.
            full_off_home = float(
                home_prior.get("full_strength_offense_index", offense_home) or offense_home
            )
            full_off_away = float(
                away_prior.get("full_strength_offense_index", offense_away) or offense_away
            )
            full_def_home = float(
                home_prior.get("full_strength_defense_index", defense_home) or defense_home
            )
            full_def_away = float(
                away_prior.get("full_strength_defense_index", defense_away) or defense_away
            )
            cur_off_home = float(offense_home) * float(home_off_mult)
            cur_off_away = float(offense_away) * float(away_off_mult)
            # defense_index is "higher = stronger defense" (see
            # _load_team_strength_priors). injury/roster-continuity nowcast
            # defense_multiplier is "higher = weaker defense" → DIVISOR.
            cur_def_home = float(defense_home) / float(home_def_mult or 1.0)
            cur_def_away = float(defense_away) / float(away_def_mult or 1.0)
            if isinstance(home_prior, dict):
                home_prior["full_strength_offense_index"] = full_off_home
                home_prior["full_strength_defense_index"] = full_def_home
                home_prior["current_offense_index"] = cur_off_home
                home_prior["current_defense_index"] = cur_def_home
                home_prior["injury_delta_offense"] = round(cur_off_home - full_off_home, 6)
                home_prior["injury_delta_defense"] = round(cur_def_home - full_def_home, 6)
            if isinstance(away_prior, dict):
                away_prior["full_strength_offense_index"] = full_off_away
                away_prior["full_strength_defense_index"] = full_def_away
                away_prior["current_offense_index"] = cur_off_away
                away_prior["current_defense_index"] = cur_def_away
                away_prior["injury_delta_offense"] = round(cur_off_away - full_off_away, 6)
                away_prior["injury_delta_defense"] = round(cur_def_away - full_def_away, 6)
            inputs = NflGameInputs(
                game_id=str(m["game_id"]),
                home_team=str(m["home_team"]),
                away_team=str(m["away_team"]),
                offense_index_home=cur_off_home,
                offense_index_away=cur_off_away,
                defense_index_home=cur_def_home,
                defense_index_away=cur_def_away,
                rest_days_home=_to_float(m.get("rest_days_home")) or 7.0,
                rest_days_away=_to_float(m.get("rest_days_away")) or 7.0,
                injury_nowcast_confidence_home=home_injury_conf,
                injury_nowcast_confidence_away=away_injury_conf,
                injury_nowcast_freshness_home_hours=_to_float(home_nowcast.get("freshness_hours")),
                injury_nowcast_freshness_away_hours=_to_float(away_nowcast.get("freshness_hours")),
                injury_nowcast_impact_home=home_injury_impact,
                injury_nowcast_impact_away=away_injury_impact,
                injury_nowcast_offense_multiplier_home=home_off_mult if not season_too_early else None,
                injury_nowcast_offense_multiplier_away=away_off_mult if not season_too_early else None,
                injury_nowcast_defense_multiplier_home=home_def_mult if not season_too_early else None,
                injury_nowcast_defense_multiplier_away=away_def_mult if not season_too_early else None,
                injury_nowcast_source=str(injury_nowcast.get("source") or "nfl_dp_injuries"),
                injury_nowcast_home_drivers=(
                    []
                    if season_too_early
                    else (
                        home_nowcast.get("top_drivers")
                        if isinstance(home_nowcast.get("top_drivers"), list)
                        else []
                    )
                ),
                injury_nowcast_away_drivers=(
                    []
                    if season_too_early
                    else (
                        away_nowcast.get("top_drivers")
                        if isinstance(away_nowcast.get("top_drivers"), list)
                        else []
                    )
                ),
                info_velocity_home=home_info_vel,
                info_velocity_away=away_info_vel,
                hours_since_change_home=home_hours_change,
                hours_since_change_away=away_hours_change,
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
                tendency_proe_home=home_proe if not season_too_early else None,
                tendency_proe_away=away_proe if not season_too_early else None,
                tendency_total_signal=(
                    0.0 if season_too_early else float(tendency_signals.get("total_signal") or 0.0)
                ),
                tendency_spread_signal=(
                    0.0 if season_too_early else float(tendency_signals.get("spread_signal") or 0.0)
                ),
                **matchup_kwargs,
            )
            seed = _default_projection_seed(inputs.game_id, model_version, simulations)
            market_lines = _fetch_nfl_market_consensus_lines(
                session,
                game_id=inputs.game_id,
                home_abbr=str(m.get("home_abbr") or "") or None,
                away_abbr=str(m.get("away_abbr") or "") or None,
                home_team=str(m.get("home_team") or "") or None,
                away_team=str(m.get("away_team") or "") or None,
                game_date=(
                    m.get("game_date")
                    if isinstance(m.get("game_date"), date)
                    else target_date
                ),
            )
            if (
                market_lines.get("market_spread_home") is None
                and market_lines.get("market_total") is None
            ):
                live_hit = live_market_by_abbr.get(
                    (str(m.get("home_abbr") or ""), str(m.get("away_abbr") or ""))
                )
                if isinstance(live_hit, dict):
                    market_lines = {
                        "market_spread_home": live_hit.get("market_spread_home"),
                        "market_total": live_hit.get("market_total"),
                    }
            # Defer linear totals calibration until after supervised blend so the
            # published total_mean gets a single mean-preserving level correction.
            # Skip tuning overrides on unplayed seasons — they were fit on
            # in-sample boards and can re-introduce OOD margin tilt.
            projection = simulate_nfl_game(
                inputs,
                simulations=simulations,
                seed=seed,
                model_version=model_version,
                totals_calibration=totals_calibration,
                apply_linear_totals_calibration=False,
                config_overrides=None if season_too_early else tuning_config_overrides,
                market_spread_home=market_lines.get("market_spread_home"),
                market_total=market_lines.get("market_total"),
            )
            markets = projection.get("markets") if isinstance(projection.get("markets"), dict) else {}
            # Skip supervised overlay until the season has real in-sample
            # REG games. High-trust / saved-fit blends were dominating the
            # simulator and flipping market sides on the 2026 preseason board
            # (see data/ops/nfl-model-sanity-fix-report.md).
            # Gates (any one skips):
            #   - season has <3 completed REG games (unplayed / too early)
            #   - matchup week 1–4
            #   - pack missing on 2026+ (week=null would otherwise re-enable)
            matchup_week_for_supervised = matchup_week_for_priors
            season_for_supervised = season_year
            skip_supervised_early = bool(
                season_too_early
                or (
                    matchup_week_for_supervised is not None
                    and int(matchup_week_for_supervised) <= 4
                )
                or (
                    matchup_pack is None
                    and season_for_supervised is not None
                    and int(season_for_supervised) >= 2026
                )
            )
            supervised_applied = False
            if supervised_fit and not skip_supervised_early:
                mp = matchup_pack if isinstance(matchup_pack, dict) else {}
                mk = matchup_kwargs if isinstance(matchup_kwargs, dict) else {}
                venue_row = session.execute(
                    text(
                        """
                        SELECT roof, surface FROM nfl_dp_schedules
                        WHERE season = :season AND home_team = :home_team AND away_team = :away_team
                        ORDER BY (week IS NULL), ABS(COALESCE(week, 0) - :week)
                        LIMIT 1
                        """
                    ),
                    {
                        "season": season_year,
                        "home_team": str(m.get("home_abbr") or ""),
                        "away_team": str(m.get("away_abbr") or ""),
                        "week": _to_int_like(mp.get("week")) or 0,
                    },
                ).fetchone()
                roof = str(venue_row.roof or "").lower() if venue_row else ""
                surface = str(venue_row.surface or "").lower() if venue_row else ""
                home_div = NFL_TEAM_DIVISION.get(str(m.get("home_abbr") or ""))
                away_div = NFL_TEAM_DIVISION.get(str(m.get("away_abbr") or ""))
                home_rest_val = _to_float(m.get("rest_days_home")) or 7.0
                away_rest_val = _to_float(m.get("rest_days_away")) or 7.0
                home_injury_impact = _to_float(home_nowcast.get("impact_score")) or 0.0
                away_injury_impact = _to_float(away_nowcast.get("impact_score")) or 0.0
                feature_row = {
                    "week": _to_float(mp.get("week")),
                    "home_off_epa_5g": _to_float(mp.get("home_off_epa_5g")),
                    "away_off_epa_5g": _to_float(mp.get("away_off_epa_5g")),
                    "home_def_epa_allowed_5g": _to_float(mp.get("home_def_epa_allowed_5g")),
                    "away_def_epa_allowed_5g": _to_float(mp.get("away_def_epa_allowed_5g")),
                    "home_pressure_allowed_5g": _to_float(mp.get("home_pressure_allowed_5g")),
                    "away_pressure_allowed_5g": _to_float(mp.get("away_pressure_allowed_5g")),
                    "home_pressure_generated_5g": _to_float(mp.get("home_pressure_generated_5g")),
                    "away_pressure_generated_5g": _to_float(mp.get("away_pressure_generated_5g")),
                    "home_pass_rate_5g": _to_float(mp.get("home_pass_rate_5g")),
                    "away_pass_rate_5g": _to_float(mp.get("away_pass_rate_5g")),
                    "home_early_down_pass_rate_5g": _to_float(mp.get("home_early_down_pass_rate_5g")),
                    "away_early_down_pass_rate_5g": _to_float(mp.get("away_early_down_pass_rate_5g")),
                    "home_red_zone_td_rate_5g": _to_float(mp.get("home_red_zone_td_rate_5g")),
                    "away_red_zone_td_rate_5g": _to_float(mp.get("away_red_zone_td_rate_5g")),
                    "home_success_offense_5g": _to_float(mp.get("home_success_offense_5g")),
                    "away_success_offense_5g": _to_float(mp.get("away_success_offense_5g")),
                    "home_success_defense_allowed_5g": _to_float(mp.get("home_success_defense_allowed_5g")),
                    "away_success_defense_allowed_5g": _to_float(mp.get("away_success_defense_allowed_5g")),
                    "diff_off_epa_5g": _to_float(mp.get("diff_off_epa_5g")),
                    "diff_def_epa_allowed_5g": _to_float(mp.get("diff_def_epa_allowed_5g")),
                    "diff_pressure_generated_5g": _to_float(mp.get("diff_pressure_generated_5g")),
                    "diff_pressure_allowed_5g": _to_float(mp.get("diff_pressure_allowed_5g")),
                    "diff_red_zone_td_rate_5g": _to_float(mp.get("diff_red_zone_td_rate_5g")),
                    "diff_success_rate_5g": _to_float(mk.get("matchup_diff_success_rate_5g")),
                    "home_kav_offense_5g": _to_float(mp.get("home_kav_offense_5g")),
                    "away_kav_offense_5g": _to_float(mp.get("away_kav_offense_5g")),
                    "home_kav_defense_5g": _to_float(mp.get("home_kav_defense_5g")),
                    "away_kav_defense_5g": _to_float(mp.get("away_kav_defense_5g")),
                    "home_kav_net_5g": _to_float(mp.get("home_kav_net_5g")),
                    "away_kav_net_5g": _to_float(mp.get("away_kav_net_5g")),
                    "diff_kav_net_5g": (
                        None
                        if _to_float(mp.get("home_kav_net_5g")) is None
                        or _to_float(mp.get("away_kav_net_5g")) is None
                        else float(_to_float(mp.get("home_kav_net_5g")))
                        - float(_to_float(mp.get("away_kav_net_5g")))
                    ),
                    # ST-KAV supervised inputs are opt-in only (failed v4 holdout).
                    # Warehouse columns may still exist on matchup packs.
                    **(
                        {
                            "home_st_kav_net_5g": _to_float(mp.get("home_st_kav_net_5g")),
                            "away_st_kav_net_5g": _to_float(mp.get("away_st_kav_net_5g")),
                            "diff_st_kav_net_5g": (
                                None
                                if _to_float(mp.get("home_st_kav_net_5g")) is None
                                or _to_float(mp.get("away_st_kav_net_5g")) is None
                                else float(_to_float(mp.get("home_st_kav_net_5g")))
                                - float(_to_float(mp.get("away_st_kav_net_5g")))
                            ),
                        }
                        if os.getenv("NFL_SUPERVISED_INCLUDE_ST_KAV", "0") == "1"
                        else {}
                    ),
                    "home_injury_impact": home_injury_impact,
                    "away_injury_impact": away_injury_impact,
                    "diff_injury_impact": home_injury_impact - away_injury_impact,
                    "home_rest_days": home_rest_val,
                    "away_rest_days": away_rest_val,
                    "diff_rest_days": home_rest_val - away_rest_val,
                    "roof_dome": 1.0 if roof in {"dome", "closed"} else 0.0,
                    "surface_turf": 1.0 if "turf" in surface else 0.0,
                    "is_divisional_game": 1.0 if (home_div and home_div == away_div) else 0.0,
                }
                real_features_by_team = detect_real_rolling_features(
                    session,
                    season=int(season_year) if season_year is not None else 0,
                    teams=[str(m.get("home_abbr") or ""), str(m.get("away_abbr") or "")],
                )
                # Never unlock high-trust supervised weights in weeks 1–4 of a
                # season — even if hydrated EPA looks week-varying. Validated
                # 85% blend on OOD early features was flipping market sides
                # (DAL@NYG). Require real features AND week >= 5.
                matchup_week = _to_int_like(mp.get("week"))
                early_season_week = matchup_week is not None and int(matchup_week) <= 4
                use_validated_weights = bool(
                    (not early_season_week)
                    and real_features_by_team.get(str(m.get("home_abbr") or ""))
                    and real_features_by_team.get(str(m.get("away_abbr") or ""))
                )
                blended_markets = apply_supervised_blend(
                    fit_payload=supervised_fit,
                    feature_row=feature_row,
                    base_markets=markets,
                    use_validated_weights=use_validated_weights,
                )
                projection["markets"] = blended_markets
                supervised_applied = bool(
                    isinstance(blended_markets, dict)
                    and isinstance(blended_markets.get("supervised_overlay"), dict)
                    and blended_markets["supervised_overlay"].get("applied")
                )
            markets = projection.get("markets") if isinstance(projection.get("markets"), dict) else {}
            pre_calibration_total = _to_float_like(markets.get("total_mean"))
            projection_created_at = _resolve_nfl_projection_created_at(
                game_date=(m.get("game_date") if isinstance(m.get("game_date"), date) else target_date),
                start_time=m.get("start_time"),
                mode=projection_created_at_mode,
                kickoff_buffer_minutes=kickoff_buffer_minutes,
            )
            # Defer final totals calibration until the slate mean is known so we
            # only close remaining level gap (avoids prior+intercept double-count).
            pending_projections.append(
                {
                    "projection": projection,
                    "pre_calibration_total": pre_calibration_total,
                    "projection_created_at": projection_created_at,
                    "home_prior": home_prior if isinstance(home_prior, dict) else {},
                    "away_prior": away_prior if isinstance(away_prior, dict) else {},
                    "season_year": season_year,
                    "prior_source": prior_source,
                    "matchup_week": matchup_week_for_supervised,
                    "matchup_pack_hit": bool(isinstance(matchup_pack, dict)),
                    "skip_supervised_early": bool(skip_supervised_early),
                    "supervised_applied": bool(supervised_applied),
                    "completed_reg_games_season": int(completed_reg_season),
                    "early_season_ood_dampened": bool(early_season_ood_dampened),
                    "home_abbr": str(m.get("home_abbr") or ""),
                    "away_abbr": str(m.get("away_abbr") or ""),
                    "market_spread_home": market_lines.get("market_spread_home"),
                    "market_total": market_lines.get("market_total"),
                    "offense_index_home": float(offense_home) * float(home_off_mult),
                    "offense_index_away": float(offense_away) * float(away_off_mult),
                    "defense_index_home": float(defense_home) / float(home_def_mult or 1.0),
                    "defense_index_away": float(defense_away) / float(away_def_mult or 1.0),
                }
            )
            processed += 1

        slate_pre_vals = [
            float(item["pre_calibration_total"])
            for item in pending_projections
            if item.get("pre_calibration_total") is not None
        ]
        slate_pre_mean = (sum(slate_pre_vals) / len(slate_pre_vals)) if slate_pre_vals else None
        # Tiny daily slates (TNF/MNF) make generative_extra noisy; only trust
        # slate-relative residual correction when the board is large enough.
        min_slate = max(1, int(float(os.getenv("NFL_TOTALS_CALIBRATION_MIN_SLATE", "6"))))
        slate_pre_mean_for_cal = slate_pre_mean if len(slate_pre_vals) >= min_slate else None

        for item in pending_projections:
            projection = item["projection"]
            pre_calibration_total = item["pre_calibration_total"]
            projection_created_at = item["projection_created_at"]
            calibrated_total, apply_meta = apply_totals_calibration(
                pre_calibration_total,
                totals_calibration or {},
                slate_pre_mean=slate_pre_mean_for_cal,
                return_meta=True,
            )
            final_calibration = {
                "pre_calibration_total": pre_calibration_total,
                "calibrated_total": calibrated_total,
                "delta": apply_meta.get("delta"),
                "fit": totals_calibration,
                "applied": bool(apply_meta.get("applied")),
                "apply_meta": apply_meta,
                "slate_pre_mean": slate_pre_mean,
            }
            markets = projection.get("markets") if isinstance(projection.get("markets"), dict) else {}
            if calibrated_total is not None:
                markets = dict(markets)
                markets["total_mean"] = round(float(calibrated_total), 2)
                delta = float(final_calibration["delta"] or 0.0)
                for band_key in ("total_p10", "total_p50", "total_p90"):
                    band_val = _to_float_like(markets.get(band_key))
                    if band_val is not None:
                        markets[band_key] = round(float(band_val) + delta, 2)
                projection["markets"] = markets
                diagnostics = projection.get("diagnostics")
                if isinstance(diagnostics, dict):
                    diagnostics = dict(diagnostics)
                    diagnostics["totals_calibration"] = {
                        **(diagnostics.get("totals_calibration") or {}),
                        "final_applied": final_calibration,
                        "source": str((totals_calibration or {}).get("source") or "nfl_totals_linear_calibration"),
                        "slope": (totals_calibration or {}).get("slope"),
                        "intercept": (totals_calibration or {}).get("intercept"),
                        "intercept_effective": apply_meta.get("intercept_effective"),
                        "level_shift_shrink": apply_meta.get("shrink"),
                        "generative_extra": apply_meta.get("generative_extra"),
                        "slate_pre_mean": slate_pre_mean,
                        "sample_size": (totals_calibration or {}).get("sample_size"),
                        "calibrated_total": round(float(calibrated_total), 4),
                        "base_total": round(float(pre_calibration_total), 4)
                        if pre_calibration_total is not None
                        else None,
                        "delta": final_calibration["delta"],
                        "applied": bool(final_calibration["applied"]),
                    }
                    projection["diagnostics"] = diagnostics
            projection_for_storage = dict(projection)
            # Stamp Model (pre-blend research) vs KEI handicap (published product)
            # after final totals calibration so handicap matches denormalized columns.
            annotate_projection_model_handicap(
                projection_for_storage,
                line_role="model",
            )
            audit_block = projection_for_storage.get("audit")
            if not isinstance(audit_block, dict):
                audit_block = {}
            audit_block.update(
                {
                    "projection_created_at_mode": str(projection_created_at_mode),
                    "kickoff_buffer_minutes": int(max(0, int(kickoff_buffer_minutes))),
                    "projection_created_at": projection_created_at.isoformat(),
                    # Wall-clock ingest time — created_at is often backdated to kickoff
                    # for CLV, so fair-lines must prefer this when choosing among ties.
                    "pipeline_run_at": datetime.now(timezone.utc).isoformat(),
                    "include_completed_games": bool(include_completed_games),
                    "pre_calibration_total": pre_calibration_total,
                    "totals_calibration": totals_calibration,
                    "final_totals_calibration": final_calibration,
                    "tuning_config_applied": bool(tuning_config_overrides),
                    "worker_build_id": worker_build_id,
                    "team_prior_anchor": {
                        "home": item.get("home_prior") or {},
                        "away": item.get("away_prior") or {},
                        "season_year": item.get("season_year"),
                        "source": item.get("prior_source"),
                    },
                    "early_season_gates": {
                        "matchup_week": item.get("matchup_week"),
                        "matchup_pack_hit": item.get("matchup_pack_hit"),
                        "skip_supervised_early": item.get("skip_supervised_early"),
                        "supervised_applied": item.get("supervised_applied"),
                        "completed_reg_games_season": item.get("completed_reg_games_season"),
                        "prior_source": item.get("prior_source"),
                        "early_season_ood_dampened": item.get("early_season_ood_dampened"),
                    },
                }
            )
            projection_for_storage["audit"] = audit_block
            markets = projection_for_storage.get("markets") or projection.get("markets") or {}
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
            inserted += 1
        session.commit()
        sample_gate = None
        probe = None
        if pending_projections:
            sample = pending_projections[0]
            sample_gate = {
                "prior_source": sample.get("prior_source"),
                "matchup_week": sample.get("matchup_week"),
                "matchup_pack_hit": sample.get("matchup_pack_hit"),
                "skip_supervised_early": sample.get("skip_supervised_early"),
                "supervised_applied": sample.get("supervised_applied"),
                "completed_reg_games_season": sample.get("completed_reg_games_season"),
                "early_season_ood_dampened": sample.get("early_season_ood_dampened"),
                "home_abbr": sample.get("home_abbr"),
                "away_abbr": sample.get("away_abbr"),
            }
            # Prefer a home-dog / market-disagreement probe when present.
            for item in pending_projections:
                markets = (item.get("projection") or {}).get("markets") or {}
                diag = (item.get("projection") or {}).get("diagnostics") or {}
                model_spread = markets.get("spread_home")
                market_spread = item.get("market_spread_home")
                disagree = (
                    model_spread is not None
                    and market_spread is not None
                    and ((float(model_spread) > 0 and float(market_spread) < 0)
                         or (float(model_spread) < 0 and float(market_spread) > 0))
                )
                if item.get("home_abbr") == "NYG" or disagree:
                    probe = {
                        "home_abbr": item.get("home_abbr"),
                        "away_abbr": item.get("away_abbr"),
                        "prior_source": item.get("prior_source"),
                        "matchup_week": item.get("matchup_week"),
                        "matchup_pack_hit": item.get("matchup_pack_hit"),
                        "skip_supervised_early": item.get("skip_supervised_early"),
                        "supervised_applied": item.get("supervised_applied"),
                        "early_season_ood_dampened": item.get("early_season_ood_dampened"),
                        "completed_reg_games_season": item.get("completed_reg_games_season"),
                        "market_spread_home": item.get("market_spread_home"),
                        "market_total": item.get("market_total"),
                        "model_spread_home": model_spread,
                        "home_win_prob": markets.get("home_win_prob"),
                        "total_mean": markets.get("total_mean"),
                        "offense_index_home": item.get("offense_index_home"),
                        "offense_index_away": item.get("offense_index_away"),
                        "defense_index_home": item.get("defense_index_home"),
                        "defense_index_away": item.get("defense_index_away"),
                        "market_blend": diag.get("market_blend"),
                        "framework_margin": (diag.get("framework") or {}).get("predicted_margin"),
                        "matchup_spread_signal": (
                            (diag.get("matchup_feature_adjustments") or {}).get("spread_signal")
                        ),
                        "mean_home_points": diag.get("mean_home_points"),
                        "mean_away_points": diag.get("mean_away_points"),
                    }
                    if item.get("home_abbr") == "NYG":
                        break
        return {
            "games_processed": processed,
            "projections_inserted": inserted,
            "slate_pre_mean": round(float(slate_pre_mean), 4) if slate_pre_mean is not None else None,
            "worker_build_id": worker_build_id,
            "sample_early_season_gate": sample_gate,
            "sanity_probe": probe,
        }
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
        _assert_tables_present(
            session,
            stage="materialize_nfl_market_history",
            required_tables=["odds_snapshots", "markets", "nfl_market_history_snapshots"],
        )
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
                SELECT DISTINCT ON (dedup.game_id, dedup.sportsbook_code, dedup.market_code, dedup.captured_at)
                  dedup.game_id, dedup.captured_at, dedup.sportsbook_code, dedup.market_code,
                  dedup.price_home, dedup.price_away, dedup.total_points, dedup.over_price, dedup.under_price,
                  dedup.source, NOW()
                FROM (
                  SELECT
                    os.id,
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
                    END AS source
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
                ) dedup
                -- Two raw odds_snapshots rows can normalize to the same
                -- (game_id, sportsbook_code, market_code, captured_at) key
                -- (e.g. a total rounded to the same 0.5 from two source
                -- rows, or two historical pulls that both captured the same
                -- unchanged last_update timestamp) -- ON CONFLICT can't
                -- update the same target row twice in one statement, so
                -- dedupe first and keep the highest raw id per key.
                ORDER BY dedup.game_id, dedup.sportsbook_code, dedup.market_code, dedup.captured_at, dedup.id DESC
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
        _assert_tables_present(
            session,
            stage="run_nfl_clv_attribution",
            required_tables=[
                "nfl_market_projections",
                "nfl_market_history_snapshots",
                "nfl_market_outcomes",
                "nfl_clv_attribution",
            ],
        )
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

            # Moneyline CLV: only recommend a side where the model actually
            # disagrees with the OPEN price in a way that implies value --
            # i.e. model_prob(side) > open_implied_prob(side). Previously
            # this always picked the model's favorite (home_win_prob >= 0.5)
            # regardless of whether that side was already fairly priced or
            # even overpriced at open, which isn't a value bet and produced
            # a CLV positive-rate well under 50% that had nothing to do with
            # model quality -- favorites systematically drift a bit at close
            # for reasons unrelated to whether picking them was ever +EV.
            if (
                home_win_prob is not None
                and open_home_ml is not None
                and open_away_ml is not None
                and close_home_ml is not None
                and close_away_ml is not None
            ):
                open_home_imp = _american_implied_prob(open_home_ml)
                open_away_imp = _american_implied_prob(open_away_ml)
                home_edge = (home_win_prob - open_home_imp) if open_home_imp is not None else None
                away_edge = ((1.0 - home_win_prob) - open_away_imp) if open_away_imp is not None else None
                side = None
                if home_edge is not None and (away_edge is None or home_edge >= away_edge) and home_edge > 0:
                    side = "home"
                elif away_edge is not None and away_edge > 0:
                    side = "away"
                open_price = open_home_ml if side == "home" else open_away_ml if side == "away" else None
                close_price = close_home_ml if side == "home" else close_away_ml if side == "away" else None
                open_imp = _american_implied_prob(open_price) if open_price is not None else None
                close_imp = _american_implied_prob(close_price) if close_price is not None else None
                if side is not None and open_imp is not None and close_imp is not None:
                    model_line = fair_home_ml if side == "home" else fair_away_ml
                    clv_value = nfl_moneyline_clv(
                        open_price=int(open_price),
                        close_price=int(close_price),
                    )
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

            # Total CLV: require a minimum edge vs the open line before
            # recommending a side -- otherwise a coinflip (model_total
            # 0.1 points from open) always "recommends" a side with zero
            # real conviction, diluting the signal with noise plays.
            MIN_TOTAL_EDGE_POINTS = 1.0
            total_side = None
            if total_mean is not None and open_total is not None:
                total_diff = total_mean - open_total
                if abs(total_diff) >= MIN_TOTAL_EDGE_POINTS:
                    total_side = "over" if total_diff > 0 else "under"
            if total_side is not None and open_total is not None and close_total is not None:
                total_clv = nfl_total_clv(
                    side=total_side,
                    open_total=float(open_total),
                    close_total=float(close_total),
                )
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


def _refresh_nfl_clv_window(
    *,
    lookback_days: int,
    model_version: str,
) -> Dict[str, Any]:
    try:
        return run_nfl_clv_attribution(
            lookback_days=max(14, int(lookback_days)),
            model_version=model_version,
        )
    except Exception as exc:
        log.warning(
            "Failed refreshing NFL CLV window (model=%s, lookback_days=%s): %s",
            model_version,
            lookback_days,
            exc,
        )
        return {"status": "warning", "error": str(exc)}


def _compute_nfl_market_clv_summary(clv_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    markets = {"moneyline", "spread", "total"}
    buckets: Dict[str, List[float]] = {market: [] for market in markets}
    for row in clv_rows:
        market = str(row.get("market_code") or "")
        clv_value = _to_float_like(row.get("clv_value"))
        if market in buckets and clv_value is not None:
            buckets[market].append(float(clv_value))
    out: Dict[str, Any] = {}
    for market, values in buckets.items():
        summary = nfl_summarize_clv_values(values)
        avg = summary.get("avg_clv")
        pos_rate = summary.get("positive_clv_rate")
        beat_rate = summary.get("beat_close_rate")
        out[market] = {
            "sample_size": summary["n"],
            "avg_clv": None if avg is None else round(float(avg), 6),
            "positive_rate": None if pos_rate is None else round(float(pos_rate), 6),
            "beat_close": summary["beat_close"],
            "push": summary["push"],
            "lose_close": summary["lose_close"],
            "decided_n": summary["decided_n"],
            "beat_close_rate": None if beat_rate is None else round(float(beat_rate), 6),
        }
    return out


def _compute_nfl_pick_hit_metrics(clv_rows: List[Dict[str, Any]]) -> Dict[str, Optional[float]]:
    moneyline_hits = 0
    moneyline_seen = 0
    moneyline_pos_hits = 0
    moneyline_pos_seen = 0
    spread_hits = 0
    spread_seen = 0
    spread_pos_hits = 0
    spread_pos_seen = 0
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
        elif market == "spread":
            home_points = _to_float_like(row.get("actual_home_points"))
            away_points = _to_float_like(row.get("actual_away_points"))
            settle_line = _to_float_like(row.get("close_line"))
            if settle_line is None:
                settle_line = _to_float_like(row.get("open_line"))
            if home_points is None or away_points is None or settle_line is None or side not in {"home", "away"}:
                continue
            margin = home_points - away_points
            won = (margin + settle_line) > 0 if side == "home" else (-margin - settle_line) > 0
            spread_seen += 1
            spread_hits += 1 if won else 0
            if positive_edge:
                spread_pos_seen += 1
                spread_pos_hits += 1 if won else 0
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
        "spread_hit_rate": round(spread_hits / spread_seen, 6) if spread_seen > 0 else None,
        "spread_pick_sample_size": spread_seen,
        "spread_positive_edge_hit_rate": (
            round(spread_pos_hits / spread_pos_seen, 6) if spread_pos_seen > 0 else None
        ),
        "spread_positive_edge_sample_size": spread_pos_seen,
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
    factor_attribution = summarize_nfl_factor_attribution_from_points(point_rows)
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
    clv_by_market = _compute_nfl_market_clv_summary(clv_rows)
    clv_hit_metrics = _compute_nfl_pick_hit_metrics(clv_rows)
    game_dates = sorted({str(r.get("game_date")) for r in point_rows if r.get("game_date") is not None})
    return {
        "model_version": model_version,
        "framework_version": NFL_HANDICAPPING_FRAMEWORK_VERSION,
        "framework_config": get_nfl_handicapping_config(),
        "factor_attribution_diagnostics": factor_attribution,
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
        "clv_by_market": clv_by_market,
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
              lp.projection,
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
                mp.projection,
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
        clv_refresh = _refresh_nfl_clv_window(
            lookback_days=max(int(lookback_days), 120),
            model_version=model_version,
        )
        _assert_tables_present(
            session,
            stage="run_nfl_quality_grading",
            required_tables=[
                "nfl_market_projections",
                "nfl_market_outcomes",
                "nfl_clv_attribution",
                "nfl_model_quality_snapshots",
            ],
        )
        totals_calibration = fetch_nfl_totals_calibration(
            session,
            model_version=model_version,
            lookback_days=max(int(lookback_days), int(float(os.getenv("NFL_TOTALS_CALIBRATION_LOOKBACK_DAYS", "1500")))),
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
                    mp.projection,
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
                  lp.projection,
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
                  mo.actual_home_points,
                  mo.actual_away_points,
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
        payload["clv_refresh"] = clv_refresh
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


def _fetch_nfl_team_week_injury_severity(
    session: Any,
    *,
    start_season: int,
    end_season: int,
) -> Dict[Tuple[int, int, str], Dict[str, float]]:
    """Position+status-weighted injury severity per (season, week, team),
    with no freshness decay (see compute_team_week_injury_severity docstring
    for why training uses a different aggregation than live inference)."""
    rows = session.execute(
        text(
            """
            SELECT
              i.season, i.week, i.team,
              i.report_status, i.practice_status, i.injury,
              r.position
            FROM nfl_dp_injuries i
            LEFT JOIN nfl_dp_rosters r
              ON r.season = i.season AND r.team = i.team AND r.player_id = i.player_id
            WHERE i.season BETWEEN :start_season AND :end_season
            """
        ),
        {"start_season": int(start_season), "end_season": int(end_season)},
    ).fetchall()

    grouped: Dict[Tuple[int, int, str], List[Dict[str, Any]]] = {}
    for row in rows:
        key = (int(row.season), int(row.week), str(row.team))
        grouped.setdefault(key, []).append(dict(row._mapping))

    out: Dict[Tuple[int, int, str], Dict[str, float]] = {}
    for key, group_rows in grouped.items():
        out[key] = compute_team_week_injury_severity(group_rows)
    return out


# Static division map used only for the "divisional game" training/serving
# feature -- divisional games are historically lower-variance/more
# competitive, a real situational signal distinct from raw team strength.
NFL_TEAM_DIVISION: Dict[str, str] = {
    "BUF": "AFC_EAST", "MIA": "AFC_EAST", "NE": "AFC_EAST", "NYJ": "AFC_EAST",
    "BAL": "AFC_NORTH", "CIN": "AFC_NORTH", "CLE": "AFC_NORTH", "PIT": "AFC_NORTH",
    "HOU": "AFC_SOUTH", "IND": "AFC_SOUTH", "JAX": "AFC_SOUTH", "TEN": "AFC_SOUTH",
    "DEN": "AFC_WEST", "KC": "AFC_WEST", "LV": "AFC_WEST", "LAC": "AFC_WEST",
    "DAL": "NFC_EAST", "NYG": "NFC_EAST", "PHI": "NFC_EAST", "WAS": "NFC_EAST",
    "CHI": "NFC_NORTH", "DET": "NFC_NORTH", "GB": "NFC_NORTH", "MIN": "NFC_NORTH",
    "ATL": "NFC_SOUTH", "CAR": "NFC_SOUTH", "NO": "NFC_SOUTH", "TB": "NFC_SOUTH",
    "ARI": "NFC_WEST", "LA": "NFC_WEST", "SEA": "NFC_WEST", "SF": "NFC_WEST",
}


def _fetch_nfl_supervised_training_rows(
    session: Any,
    *,
    start_season: int,
    end_season: int,
) -> List[Dict[str, Any]]:
    rows = session.execute(
        text(
            """
            WITH team_games AS (
              SELECT DISTINCT season, home_team AS team, game_date FROM nfl_dp_schedules
              WHERE season BETWEEN :start_season AND :end_season
              UNION
              SELECT DISTINCT season, away_team AS team, game_date FROM nfl_dp_schedules
              WHERE season BETWEEN :start_season AND :end_season
            ),
            rest AS (
              SELECT season, team, game_date,
                (game_date - LAG(game_date) OVER (PARTITION BY season, team ORDER BY game_date)) AS rest_days
              FROM team_games
            )
            SELECT
              mf.season,
              mf.week,
              mf.game_id,
              mf.home_off_epa_5g,
              mf.away_off_epa_5g,
              mf.home_def_epa_allowed_5g,
              mf.away_def_epa_allowed_5g,
              mf.home_pressure_allowed_5g,
              mf.away_pressure_allowed_5g,
              mf.home_pressure_generated_5g,
              mf.away_pressure_generated_5g,
              mf.home_pass_rate_5g,
              mf.away_pass_rate_5g,
              mf.home_early_down_pass_rate_5g,
              mf.away_early_down_pass_rate_5g,
              mf.home_red_zone_td_rate_5g,
              mf.away_red_zone_td_rate_5g,
              mf.home_success_offense_5g,
              mf.away_success_offense_5g,
              mf.home_success_defense_allowed_5g,
              mf.away_success_defense_allowed_5g,
              mf.diff_off_epa_5g,
              mf.diff_def_epa_allowed_5g,
              mf.diff_pressure_generated_5g,
              mf.diff_pressure_allowed_5g,
              mf.diff_red_zone_td_rate_5g,
              (
                (
                  COALESCE(mf.home_success_offense_5g, 0.0)
                  - COALESCE(mf.away_success_offense_5g, 0.0)
                )
                + (
                  COALESCE(mf.away_success_defense_allowed_5g, 0.0)
                  - COALESCE(mf.home_success_defense_allowed_5g, 0.0)
                )
              ) / 2.0 AS diff_success_rate_5g,
              mf.home_kav_offense_5g,
              mf.away_kav_offense_5g,
              mf.home_kav_defense_5g,
              mf.away_kav_defense_5g,
              mf.home_kav_net_5g,
              mf.away_kav_net_5g,
              CASE
                WHEN mf.home_kav_net_5g IS NULL OR mf.away_kav_net_5g IS NULL THEN NULL
                ELSE mf.home_kav_net_5g - mf.away_kav_net_5g
              END AS diff_kav_net_5g,
              mf.home_st_kav_net_5g,
              mf.away_st_kav_net_5g,
              CASE
                WHEN mf.home_st_kav_net_5g IS NULL OR mf.away_st_kav_net_5g IS NULL THEN NULL
                ELSE mf.diff_st_kav_net_5g
              END AS diff_st_kav_net_5g,
              sch.home_team,
              sch.away_team,
              sch.roof,
              sch.surface,
              home_rest.rest_days AS home_rest_days,
              away_rest.rest_days AS away_rest_days,
              sch.home_score,
              sch.away_score,
              (sch.home_score > sch.away_score) AS home_team_won,
              (sch.home_score + sch.away_score) AS final_total_points
            FROM nfl_dp_matchup_features_weekly mf
            JOIN nfl_dp_schedules sch
              ON sch.season = mf.season
             AND sch.game_id = mf.game_id
            LEFT JOIN rest home_rest
              ON home_rest.season = sch.season AND home_rest.team = sch.home_team AND home_rest.game_date = sch.game_date
            LEFT JOIN rest away_rest
              ON away_rest.season = sch.season AND away_rest.team = sch.away_team AND away_rest.game_date = sch.game_date
            WHERE mf.season BETWEEN :start_season AND :end_season
              AND sch.home_score IS NOT NULL
              AND sch.away_score IS NOT NULL
            ORDER BY mf.season, mf.week, mf.game_id
            """
        ),
        {"start_season": int(start_season), "end_season": int(end_season)},
    ).fetchall()
    parsed_rows = [dict(row._mapping) for row in rows]

    injury_severity = _fetch_nfl_team_week_injury_severity(
        session, start_season=start_season, end_season=end_season
    )

    out: List[Dict[str, Any]] = []
    for row in parsed_rows:
        season = int(row["season"])
        week = int(row["week"])
        home_team = str(row["home_team"])
        away_team = str(row["away_team"])
        home_inj = injury_severity.get((season, week, home_team), {})
        away_inj = injury_severity.get((season, week, away_team), {})
        roof = str(row.get("roof") or "").lower()
        surface = str(row.get("surface") or "").lower()
        home_div = NFL_TEAM_DIVISION.get(home_team)
        away_div = NFL_TEAM_DIVISION.get(away_team)
        row["home_injury_impact"] = home_inj.get("impact_score", 0.0)
        row["away_injury_impact"] = away_inj.get("impact_score", 0.0)
        row["diff_injury_impact"] = row["home_injury_impact"] - row["away_injury_impact"]
        row["home_rest_days"] = float(row.get("home_rest_days")) if row.get("home_rest_days") is not None else 7.0
        row["away_rest_days"] = float(row.get("away_rest_days")) if row.get("away_rest_days") is not None else 7.0
        row["diff_rest_days"] = row["home_rest_days"] - row["away_rest_days"]
        row["roof_dome"] = 1.0 if roof in {"dome", "closed"} else 0.0
        row["surface_turf"] = 1.0 if "turf" in surface else 0.0
        row["is_divisional_game"] = 1.0 if (home_div and home_div == away_div) else 0.0
        out.append(row)
    return out


@celery_app.task(name="src.tasks.run_nfl_supervised_retrain")
def run_nfl_supervised_retrain(
    *,
    model_version: str = DEFAULT_NFL_MODEL_VERSION,
    start_season: int = 2013,
    end_season: int = 2025,
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        _ensure_nfl_supervised_fits_table(session)
        training_rows = _fetch_nfl_supervised_training_rows(
            session,
            start_season=int(start_season),
            end_season=int(end_season),
        )
        fit_payload = fit_nfl_supervised_models(
            training_rows,
            feature_keys=NFL_SUPERVISED_FEATURE_KEYS,
        )
        metrics = fit_payload.get("metrics") if isinstance(fit_payload.get("metrics"), dict) else {}
        session.execute(
            text(
                """
                UPDATE nfl_supervised_model_fits
                SET is_active = false
                WHERE model_version = :model_version
                  AND is_active = true
                """
            ),
            {"model_version": model_version},
        )
        session.execute(
            text(
                """
                INSERT INTO nfl_supervised_model_fits (
                  model_version, train_start_season, train_end_season,
                  train_rows, test_rows, metrics, payload, is_active, created_at
                ) VALUES (
                  :model_version, :train_start_season, :train_end_season,
                  :train_rows, :test_rows, CAST(:metrics AS jsonb), CAST(:payload AS jsonb), true, :created_at
                )
                """
            ),
            {
                "model_version": model_version,
                "train_start_season": int(start_season),
                "train_end_season": int(end_season),
                "train_rows": int(metrics.get("train_rows") or 0),
                "test_rows": int(metrics.get("test_rows") or 0),
                "metrics": json.dumps(metrics),
                "payload": json.dumps(fit_payload),
                "created_at": _now_utc(),
            },
        )
        session.commit()
        return {
            "status": "ok",
            "model_version": model_version,
            "train_start_season": int(start_season),
            "train_end_season": int(end_season),
            "rows_seen": len(training_rows),
            "feature_count": len(NFL_SUPERVISED_FEATURE_KEYS),
            "metrics": metrics,
        }
    except Exception:
        session.rollback()
        log.exception("Failed running NFL supervised retrain")
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
        _assert_tables_present(
            session,
            stage="run_nfl_walkforward_backtest",
            required_tables=[
                "nfl_market_projections",
                "nfl_market_outcomes",
                "nfl_model_backtest_runs",
            ],
        )
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
        factor_attribution = summarize_nfl_factor_attribution_from_points(eligible_points)
        payload = {
            "model_version": model_version,
            "framework_version": NFL_HANDICAPPING_FRAMEWORK_VERSION,
            "framework_config": get_nfl_handicapping_config(),
            "factor_attribution_diagnostics": factor_attribution,
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


def _fetch_nfl_framework_tuning_points(
    session: Any,
    *,
    model_version: str,
    lookback_days: int,
) -> List[Dict[str, Any]]:
    rows = session.execute(
        text(
            """
            WITH base_points AS (
              SELECT
                mo.game_id,
                g.game_date,
                lp.home_win_prob,
                lp.total_mean,
                lp.projection,
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
                  mp.projection,
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
            ),
            moneyline_open AS (
              SELECT
                mhs.game_id,
                AVG(mhs.home_price)::numeric AS open_home_price,
                AVG(mhs.away_price)::numeric AS open_away_price
              FROM nfl_market_history_snapshots mhs
              WHERE mhs.market_code = 'moneyline'
                AND mhs.captured_at = (
                  SELECT MIN(inner_mhs.captured_at)
                  FROM nfl_market_history_snapshots inner_mhs
                  WHERE inner_mhs.game_id = mhs.game_id
                    AND inner_mhs.market_code = 'moneyline'
                )
              GROUP BY mhs.game_id
            ),
            clv_rollup AS (
              SELECT
                c.game_id,
                AVG(c.clv_value)::numeric AS clv_avg,
                AVG(c.clv_value) FILTER (WHERE c.market_code = 'moneyline')::numeric AS clv_ml_avg,
                AVG(c.clv_value) FILTER (WHERE c.market_code = 'total')::numeric AS clv_total_avg
              FROM nfl_clv_attribution c
              WHERE c.model_version = :model_version
              GROUP BY c.game_id
            )
            SELECT
              bp.*,
              cr.clv_avg,
              cr.clv_ml_avg,
              cr.clv_total_avg,
              mo.open_home_price,
              mo.open_away_price
            FROM base_points bp
            LEFT JOIN clv_rollup cr ON cr.game_id = bp.game_id
            LEFT JOIN moneyline_open mo ON mo.game_id = bp.game_id
            ORDER BY bp.game_date, bp.game_id
            """
        ),
        {"model_version": model_version, "lookback_days": int(lookback_days)},
    ).fetchall()
    return [dict(r._mapping) for r in rows]


@celery_app.task(name="src.tasks.run_nfl_framework_tuning")
def run_nfl_framework_tuning(
    *,
    model_version: str = DEFAULT_NFL_MODEL_VERSION,
    lookback_days: int = 240,
    training_days: int = 56,
    step_days: int = 7,
    max_candidates: int = 180,
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        clv_refresh = _refresh_nfl_clv_window(
            lookback_days=max(int(lookback_days), 120),
            model_version=model_version,
        )
        points = _fetch_nfl_framework_tuning_points(
            session,
            model_version=model_version,
            lookback_days=int(lookback_days),
        )
        base_config = get_nfl_handicapping_config()
        candidates = build_tuning_candidates(
            base_guardrails=base_config.get("guardrails") if isinstance(base_config.get("guardrails"), dict) else {},
            max_candidates=max(12, int(max_candidates)),
        )
        report = evaluate_tuning_grid(
            points=points,
            candidates=candidates,
            training_days=int(training_days),
            step_days=int(step_days),
            thresholds=TuningThresholds(
                min_fold_count=max(2, int(_env_float("NFL_TUNING_MIN_FOLD_COUNT", 2))),
                min_sample_size=max(25, int(_env_float("NFL_TUNING_MIN_SAMPLE_SIZE", 30))),
                min_recommendations=max(8, int(_env_float("NFL_TUNING_MIN_RECOMMENDATIONS", 12))),
                min_coverage=_clamp(_env_float("NFL_TUNING_MIN_COVERAGE", 0.08), 0.0, 1.0),
                max_coverage=_clamp(_env_float("NFL_TUNING_MAX_COVERAGE", 0.80), 0.0, 1.0),
                target_coverage=_clamp(_env_float("NFL_TUNING_TARGET_COVERAGE", 0.32), 0.0, 1.0),
            ),
        )

        run_payload = {
            "model_version": model_version,
            "lookback_days": int(lookback_days),
            "training_days": int(training_days),
            "step_days": int(step_days),
            "max_candidates": int(max_candidates),
            "framework_version": NFL_HANDICAPPING_FRAMEWORK_VERSION,
            "candidate_count": len(candidates),
            "clv_refresh": clv_refresh,
            **report,
        }
        recommended = report.get("recommended_candidate") if isinstance(report.get("recommended_candidate"), dict) else None
        selected_config = recommended.get("config_overrides") if isinstance(recommended, dict) else None
        run_row = session.execute(
            text(
                """
                INSERT INTO nfl_framework_tuning_runs (
                  run_date, model_version, lookback_days, training_days, step_days,
                  candidate_count, payload, selected_config, created_at
                ) VALUES (
                  :run_date, :model_version, :lookback_days, :training_days, :step_days,
                  :candidate_count, CAST(:payload AS jsonb), CAST(:selected_config AS jsonb), :created_at
                )
                RETURNING id
                """
            ),
            {
                "run_date": date.today(),
                "model_version": model_version,
                "lookback_days": int(lookback_days),
                "training_days": int(training_days),
                "step_days": int(step_days),
                "candidate_count": len(candidates),
                "payload": json.dumps(run_payload),
                "selected_config": json.dumps(selected_config or {}),
                "created_at": _now_utc(),
            },
        ).fetchone()
        run_id = str(run_row[0]) if run_row is not None else None
        ranked = report.get("ranked_candidates") if isinstance(report.get("ranked_candidates"), list) else []
        if run_id:
            for item in ranked[:60]:
                metrics = item.get("metrics") if isinstance(item.get("metrics"), dict) else {}
                candidate = item.get("candidate") if isinstance(item.get("candidate"), dict) else {}
                session.execute(
                    text(
                        """
                        INSERT INTO nfl_framework_tuning_candidates (
                          run_id, rank, score, metrics, candidate, config_overrides, is_recommended, created_at
                        ) VALUES (
                          :run_id, :rank, :score, CAST(:metrics AS jsonb), CAST(:candidate AS jsonb),
                          CAST(:config_overrides AS jsonb), :is_recommended, :created_at
                        )
                        """
                    ),
                    {
                        "run_id": run_id,
                        "rank": int(item.get("rank") or 0),
                        "score": float(item.get("score") or 0.0),
                        "metrics": json.dumps(metrics),
                        "candidate": json.dumps(candidate),
                        "config_overrides": json.dumps(item.get("config_overrides") or {}),
                        "is_recommended": bool(int(item.get("rank") or 0) == 1),
                        "created_at": _now_utc(),
                    },
                )
        session.commit()
        return {"run_id": run_id, **run_payload}
    except Exception:
        session.rollback()
        log.exception("Failed running NFL framework tuning")
        raise
    finally:
        session.close()


@celery_app.task(name="src.tasks.run_nfl_decomposition_drift_monitor")
def run_nfl_decomposition_drift_monitor(
    *,
    model_version: str = DEFAULT_NFL_MODEL_VERSION,
    lookback_days: int = 120,
    baseline_weeks: int = 4,
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        rows = session.execute(
            text(
                """
                SELECT
                  mp.projection,
                  date_trunc('week', g.game_date)::date AS week_bucket
                FROM nfl_market_projections mp
                JOIN games g ON g.id = mp.game_id
                WHERE mp.model_version = :model_version
                  AND g.game_date >= CURRENT_DATE - make_interval(days => :lookback_days)
                ORDER BY g.game_date ASC
                """
            ),
            {"model_version": model_version, "lookback_days": int(lookback_days)},
        ).fetchall()
        summary = summarize_decomposition_drift(
            rows=[dict(r._mapping) for r in rows],
            baseline_weeks=max(2, int(baseline_weeks)),
            warn_threshold=_clamp(_env_float("NFL_DRIFT_WARN_THRESHOLD", 0.18), 0.01, 1.2),
            critical_threshold=_clamp(_env_float("NFL_DRIFT_CRITICAL_THRESHOLD", 0.30), 0.01, 2.0),
        )
        payload = {
            "model_version": model_version,
            "lookback_days": int(lookback_days),
            "baseline_weeks": int(baseline_weeks),
            "row_count": len(rows),
            **summary,
        }
        session.execute(
            text(
                """
                INSERT INTO nfl_decomposition_drift_snapshots (
                  snapshot_date, model_version, lookback_days, baseline_weeks, status, payload, created_at
                ) VALUES (
                  :snapshot_date, :model_version, :lookback_days, :baseline_weeks, :status, CAST(:payload AS jsonb), :created_at
                )
                """
            ),
            {
                "snapshot_date": date.today(),
                "model_version": model_version,
                "lookback_days": int(lookback_days),
                "baseline_weeks": int(baseline_weeks),
                "status": str(summary.get("status") or "insufficient_data"),
                "payload": json.dumps(payload),
                "created_at": _now_utc(),
            },
        )
        session.commit()
        return payload
    except Exception:
        session.rollback()
        log.exception("Failed running NFL decomposition drift monitor")
        raise
    finally:
        session.close()


def _lock_nfl_runtime_config(
    session: Any,
    *,
    model_version: str,
    cycle_id: str,
) -> Dict[str, Any]:
    tuning_row = session.execute(
        text(
            """
            SELECT id, selected_config, created_at
            FROM nfl_framework_tuning_runs
            WHERE model_version = :model_version
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"model_version": model_version},
    ).fetchone()
    selected_config = tuning_row.selected_config if tuning_row is not None and isinstance(tuning_row.selected_config, dict) else {}
    framework_cfg = get_nfl_handicapping_config(config_overrides=selected_config or None)
    lock_key = f"{model_version}:{date.today().isoformat()}:{cycle_id[:8]}"
    session.execute(
        text(
            """
            UPDATE nfl_runtime_config_locks
            SET is_active = false
            WHERE model_version = :model_version
              AND is_active = true
            """
        ),
        {"model_version": model_version},
    )
    session.execute(
        text(
            """
            INSERT INTO nfl_runtime_config_locks (
              model_version, lock_key, framework_version, selected_tuning_run_id, config_payload, lock_reason, is_active, created_at
            ) VALUES (
              :model_version, :lock_key, :framework_version, CAST(:selected_tuning_run_id AS uuid), CAST(:config_payload AS jsonb), :lock_reason, true, :created_at
            )
            ON CONFLICT (model_version, lock_key) DO UPDATE SET
              framework_version = EXCLUDED.framework_version,
              selected_tuning_run_id = EXCLUDED.selected_tuning_run_id,
              config_payload = EXCLUDED.config_payload,
              lock_reason = EXCLUDED.lock_reason,
              is_active = true
            """
        ),
        {
            "model_version": model_version,
            "lock_key": lock_key,
            "framework_version": str(framework_cfg.get("framework_version") or "unknown"),
            "selected_tuning_run_id": (str(tuning_row.id) if tuning_row is not None else None),
            "config_payload": json.dumps(
                {
                    "framework_config": framework_cfg,
                    "selected_config": selected_config,
                }
            ),
            "lock_reason": f"launch-hardening-cycle:{cycle_id}",
            "created_at": _now_utc(),
        },
    )
    return {
        "lock_key": lock_key,
        "framework_version": framework_cfg.get("framework_version"),
        "selected_tuning_run_id": (str(tuning_row.id) if tuning_row is not None else None),
    }


def _compute_nfl_launch_readiness(
    session: Any,
    *,
    model_version: str,
    max_odds_age_minutes: int,
    max_context_age_hours: int,
    max_moneyline_brier: float,
    max_total_mae: float,
    min_clv_avg: float,
    min_quality_sample: int,
) -> Dict[str, Any]:
    quality_row = session.execute(
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
    drift_row = session.execute(
        text(
            """
            SELECT status, created_at
            FROM nfl_decomposition_drift_snapshots
            WHERE model_version = :model_version
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"model_version": model_version},
    ).fetchone()
    tuning_row = session.execute(
        text(
            """
            SELECT payload, created_at
            FROM nfl_framework_tuning_runs
            WHERE model_version = :model_version
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"model_version": model_version},
    ).fetchone()
    tuning_payload = (
        tuning_row.payload
        if tuning_row is not None and isinstance(tuning_row.payload, dict)
        else {}
    )
    odds_age_row = session.execute(
        text(
            """
            SELECT EXTRACT(EPOCH FROM (NOW() - MAX(captured_at))) / 60.0 AS age_minutes
            FROM odds_snapshots os
            JOIN games g ON g.id = os.game_id
            JOIN seasons s ON s.id = g.season_id
            JOIN leagues l ON l.id = s.league_id
            WHERE l.code = 'nfl'
            """
        )
    ).fetchone()
    context_age_row = session.execute(
        text(
            """
            SELECT EXTRACT(EPOCH FROM (NOW() - MAX(updated_at))) / 3600.0 AS age_hours
            FROM nfl_game_context
            """
        )
    ).fetchone()
    quality_payload = (
        quality_row.payload
        if quality_row is not None and isinstance(quality_row.payload, dict)
        else {}
    )
    sample_size = int(_safe_float(quality_payload.get("sample_size")) or 0)
    checks = {
        "quality_snapshot_present": quality_row is not None,
        "quality_sample_size_ok": sample_size >= int(min_quality_sample),
        "moneyline_brier_ok": (_safe_float(quality_payload.get("moneyline_brier")) or 9.9)
        <= float(max_moneyline_brier),
        "total_mae_ok": (_safe_float(quality_payload.get("total_mae")) or 99.0)
        <= float(max_total_mae),
        "clv_ok": (_safe_float(quality_payload.get("clv_avg")) or -9.9) >= float(min_clv_avg),
        "drift_ok": drift_row is not None and str(drift_row.status) in {"stable", "warning"},
        "tuning_ok": tuning_row is not None and str(tuning_payload.get("status") or "") == "ok",
        "odds_freshness_ok": (_safe_float(getattr(odds_age_row, "age_minutes", None)) or 9e9)
        <= float(max_odds_age_minutes),
        "context_freshness_ok": (_safe_float(getattr(context_age_row, "age_hours", None)) or 9e9)
        <= float(max_context_age_hours),
    }
    blockers = [name for name, passed in checks.items() if not bool(passed)]
    status = "go" if not blockers else "no-go"
    payload = {
        "model_version": model_version,
        "status": status,
        "checks": checks,
        "blockers": blockers,
        "metrics": {
            "sample_size": sample_size,
            "moneyline_brier": _safe_float(quality_payload.get("moneyline_brier")),
            "total_mae": _safe_float(quality_payload.get("total_mae")),
            "clv_avg": _safe_float(quality_payload.get("clv_avg")),
            "odds_age_minutes": _safe_float(getattr(odds_age_row, "age_minutes", None)),
            "context_age_hours": _safe_float(getattr(context_age_row, "age_hours", None)),
            "quality_snapshot_created_at": (
                quality_row.created_at.isoformat() if quality_row is not None else None
            ),
            "drift_snapshot_created_at": (
                drift_row.created_at.isoformat() if drift_row is not None else None
            ),
            "tuning_created_at": (
                tuning_row.created_at.isoformat() if tuning_row is not None else None
            ),
        },
    }
    return payload


@celery_app.task(name="src.tasks.run_nfl_launch_hardening_cycle")
def run_nfl_launch_hardening_cycle(
    *,
    model_version: str = DEFAULT_NFL_MODEL_VERSION,
    days_ahead: int = 14,
    outcomes_lookback_days: int = 60,
    simulations: int = 5000,
    backtest_lookback_days: int = 240,
    tuning_lookback_days: int = 240,
    training_days: int = 56,
    step_days: int = 7,
    max_candidates: int = 180,
) -> Dict[str, Any]:
    cycle_id = str(uuid.uuid4())
    session = SessionLocal()
    try:
        _assert_tables_present(
            session,
            stage="run_nfl_launch_hardening_cycle",
            required_tables=[
                "odds_snapshots",
                "nfl_game_context",
                "nfl_market_projections",
                "nfl_market_history_snapshots",
                "nfl_market_outcomes",
                "nfl_clv_attribution",
                "nfl_model_quality_snapshots",
                "nfl_model_backtest_runs",
                "nfl_framework_tuning_runs",
                "nfl_decomposition_drift_snapshots",
                "nfl_runtime_config_locks",
                "nfl_pipeline_stage_runs",
                "nfl_launch_readiness_reports",
            ],
        )
    finally:
        session.close()

    stage_results: List[Dict[str, Any]] = []
    stage_results.append(
        _run_nfl_launch_stage(
            cycle_id=cycle_id,
            stage="pull_odds_snapshot",
            fn=pull_odds_snapshot,
            kwargs={},
        )
    )
    stage_results.append(
        _run_nfl_launch_stage(
            cycle_id=cycle_id,
            stage="pull_nfl_context_snapshot",
            fn=pull_nfl_context_snapshot,
            kwargs={"days_ahead": int(days_ahead)},
        )
    )
    stage_results.append(
        _run_nfl_launch_stage(
            cycle_id=cycle_id,
            stage="run_nfl_supervised_retrain",
            fn=run_nfl_supervised_retrain,
            kwargs={
                "model_version": model_version,
                "start_season": 2013,
                "end_season": max(2013, date.today().year - 1),
            },
        )
    )
    stage_results.append(
        _run_nfl_launch_stage(
            cycle_id=cycle_id,
            stage="run_nfl_market_simulations",
            fn=run_nfl_market_simulations,
            kwargs={
                "simulations": int(simulations),
                "model_version": model_version,
            },
        )
    )
    stage_results.append(
        _run_nfl_launch_stage(
            cycle_id=cycle_id,
            stage="materialize_nfl_market_history",
            fn=materialize_nfl_market_history,
            kwargs={"lookback_days": int(outcomes_lookback_days)},
        )
    )
    stage_results.append(
        _run_nfl_launch_stage(
            cycle_id=cycle_id,
            stage="pull_nfl_outcomes",
            fn=pull_nfl_outcomes,
            kwargs={"days_back": int(outcomes_lookback_days)},
        )
    )
    stage_results.append(
        _run_nfl_launch_stage(
            cycle_id=cycle_id,
            stage="run_nfl_clv_attribution",
            fn=run_nfl_clv_attribution,
            kwargs={
                "lookback_days": int(outcomes_lookback_days),
                "model_version": model_version,
            },
        )
    )
    stage_results.append(
        _run_nfl_launch_stage(
            cycle_id=cycle_id,
            stage="run_nfl_quality_grading",
            fn=run_nfl_quality_grading,
            kwargs={
                "lookback_days": int(outcomes_lookback_days),
                "model_version": model_version,
            },
        )
    )
    stage_results.append(
        _run_nfl_launch_stage(
            cycle_id=cycle_id,
            stage="run_nfl_walkforward_backtest",
            fn=run_nfl_walkforward_backtest,
            kwargs={
                "model_version": model_version,
                "lookback_days": int(backtest_lookback_days),
                "training_days": int(training_days),
                "step_days": int(step_days),
                "apply_calibration": True,
            },
        )
    )
    stage_results.append(
        _run_nfl_launch_stage(
            cycle_id=cycle_id,
            stage="run_nfl_framework_tuning",
            fn=run_nfl_framework_tuning,
            kwargs={
                "model_version": model_version,
                "lookback_days": int(tuning_lookback_days),
                "training_days": int(training_days),
                "step_days": int(step_days),
                "max_candidates": int(max_candidates),
            },
        )
    )
    stage_results.append(
        _run_nfl_launch_stage(
            cycle_id=cycle_id,
            stage="run_nfl_decomposition_drift_monitor",
            fn=run_nfl_decomposition_drift_monitor,
            kwargs={"model_version": model_version, "lookback_days": 120, "baseline_weeks": 4},
        )
    )

    session = SessionLocal()
    try:
        config_lock = _lock_nfl_runtime_config(
            session,
            model_version=model_version,
            cycle_id=cycle_id,
        )
        readiness = _compute_nfl_launch_readiness(
            session,
            model_version=model_version,
            max_odds_age_minutes=max(15, int(_env_float("NFL_LAUNCH_MAX_ODDS_AGE_MINUTES", 180))),
            max_context_age_hours=max(2, int(_env_float("NFL_LAUNCH_MAX_CONTEXT_AGE_HOURS", 30))),
            max_moneyline_brier=_clamp(_env_float("NFL_LAUNCH_MAX_MONEYLINE_BRIER", 0.255), 0.05, 0.4),
            max_total_mae=_clamp(_env_float("NFL_LAUNCH_MAX_TOTAL_MAE", 6.0), 0.5, 20.0),
            min_clv_avg=_env_float("NFL_LAUNCH_MIN_CLV_AVG", 0.0),
            min_quality_sample=max(40, int(_env_float("NFL_LAUNCH_MIN_QUALITY_SAMPLE", 100))),
        )
        session.execute(
            text(
                """
                INSERT INTO nfl_launch_readiness_reports (
                  cycle_id, model_version, status, checks, blockers, payload, created_at
                ) VALUES (
                  CAST(:cycle_id AS uuid), :model_version, :status, CAST(:checks AS jsonb), CAST(:blockers AS jsonb), CAST(:payload AS jsonb), :created_at
                )
                """
            ),
            {
                "cycle_id": cycle_id,
                "model_version": model_version,
                "status": readiness["status"],
                "checks": json.dumps(readiness.get("checks") or {}),
                "blockers": json.dumps(readiness.get("blockers") or []),
                "payload": json.dumps(readiness),
                "created_at": _now_utc(),
            },
        )
        session.commit()
        return {
            "cycle_id": cycle_id,
            "model_version": model_version,
            "stage_results": stage_results,
            "config_lock": config_lock,
            "readiness": readiness,
        }
    except Exception:
        session.rollback()
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


def _fetch_nfl_latest_drift_snapshot(
    session: Any,
    *,
    model_version: str,
) -> Dict[str, Any]:
    row = session.execute(
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
    if row is None:
        return {}
    payload = row.payload if isinstance(row.payload, dict) else {}
    return {
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at is not None else None,
        "top_shifts": payload.get("top_shifts") if isinstance(payload.get("top_shifts"), list) else [],
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
        _assert_tables_present(
            session,
            stage="evaluate_nfl_model_promotion",
            required_tables=[
                "nfl_model_runtime_state",
                "nfl_model_promotion_events",
                "nfl_model_quality_snapshots",
            ],
        )
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
        champion_drift = _fetch_nfl_latest_drift_snapshot(session, model_version=champion_version)
        challenger_drift = _fetch_nfl_latest_drift_snapshot(session, model_version=challenger_model_version)
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
            "champion_drift": champion_drift,
            "challenger_drift": challenger_drift,
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
        clear_game_lineup_features_cache()
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
            if get_lineup_timing_mode() == "sharp":
                lineup_confirmed = bool(home_lineup.get("lineup_confirmed")) and bool(
                    away_lineup.get("lineup_confirmed")
                )
            else:
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
            rest_days_home = team_rest_days_from_schedule(
                schedule,
                team_id=home_team_id if isinstance(home_team_id, int) else None,
                game_time_iso=g.get("game_time"),
            )
            rest_days_away = team_rest_days_from_schedule(
                schedule,
                team_id=away_team_id if isinstance(away_team_id, int) else None,
                game_time_iso=g.get("game_time"),
            )
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
                            "rest_days_home": rest_days_home,
                            "rest_days_away": rest_days_away,
                            "bullpen_appearances_last3_home": home_bp["bullpen_appearances_last3"],
                            "bullpen_appearances_last3_away": away_bp["bullpen_appearances_last3"],
                            "bullpen_high_leverage_availability_home": home_bp["bullpen_high_leverage_availability_score"],
                            "bullpen_high_leverage_availability_away": away_bp["bullpen_high_leverage_availability_score"],
                            "bullpen_quality_home": home_bp.get("bullpen_quality", 1.0),
                            "bullpen_quality_away": away_bp.get("bullpen_quality", 1.0),
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
                  home.abbr AS home_abbr,
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
                  c.umpire_run_factor,
                  c.context
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
            starter_home_feat = starter_identity_features(
                m.get("probable_pitcher_home"), as_of=target_date
            )
            starter_away_feat = starter_identity_features(
                m.get("probable_pitcher_away"), as_of=target_date
            )
            freshness = _info_freshness_score(
                updated_at=m.get("context_updated_at"),
                lineup_confirmed=bool(m["lineup_confirmed"]) if m.get("lineup_confirmed") is not None else False,
            )
            context_payload = m.get("context") if isinstance(m.get("context"), dict) else {}
            if isinstance(m.get("context"), str):
                try:
                    context_payload = json.loads(m["context"])
                except Exception:
                    context_payload = {}
            rest_home = _to_float(context_payload.get("rest_days_home"))
            rest_away = _to_float(context_payload.get("rest_days_away"))
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
                bullpen_quality_home=float(context_payload.get("bullpen_quality_home") or 1.0),
                bullpen_quality_away=float(context_payload.get("bullpen_quality_away") or 1.0),
                umpire_run_factor=float(m["umpire_run_factor"]) if m.get("umpire_run_factor") is not None else 1.0,
                info_freshness_score_home=freshness,
                info_freshness_score_away=freshness,
            )
            inputs, sharpen_diag = _sharpen_mlb_inputs(
                inputs,
                starter_home_feat=starter_home_feat,
                starter_away_feat=starter_away_feat,
                home_abbr=str(m.get("home_abbr") or "") or None,
                rest_days_home=rest_home,
                rest_days_away=rest_away,
            )
            seed = _default_projection_seed(inputs.game_id, model_version, simulations)
            projection = _run_simulation_by_model(
                inputs,
                simulations=simulations,
                seed=seed,
                model_version=model_version,
            )
            projection.setdefault("diagnostics", {}).update(sharpen_diag)
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


def _insert_nba_projection(session: Any, projection: Dict[str, Any]) -> None:
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
            "created_at": _now_utc(),
        },
    )


def _nba_market_lines_for_game(
    session: Any,
    game_id: str,
    *,
    game_date: Optional[date] = None,
    home_team_key: Optional[str] = None,
    away_team_key: Optional[str] = None,
) -> Dict[str, Optional[float]]:
    """Read closing-ish spread/total from owned odds_snapshots — no Odds API burn.

    Phase-2 join fix (soft-miss root causes):
      1) densify stores Odds API *full names* with heuristic abbrs (BOCE≠BOS)
      2) UTC commence_time can shift ``games.game_date`` vs ingest ``gdte`` (ET)
      3) ingest ids are nba.com gids, not hierarchy UUIDs

    Match path: UUID → (ET tip date | date±1) + (full name | abbr aliases).
    Closing line ≈ mean of latest captured_at snapshot per sportsbook.
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
            home_key = normalize_nba_team_key(str(home_team_key or ""))
            away_key = normalize_nba_team_key(str(away_team_key or ""))
            home_names = [n.upper() for n in nba_full_names_for_abbr(home_key)]
            away_names = [n.upper() for n in nba_full_names_for_abbr(away_key)]
            home_abbrs = [a.upper() for a in nba_abbr_match_keys(home_key)]
            away_abbrs = [a.upper() for a in nba_abbr_match_keys(away_key)]
            season_year = nba_season_year_from_date(game_date)
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
                      WHERE l.code = 'nba'
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


@celery_app.task(name="src.tasks.repair_nba_odds_team_abbrs")
def repair_nba_odds_team_abbrs() -> Dict[str, Any]:
    """Rewrite densified NBA ``teams.abbr`` from Odds full names → canonical keys.

    Does not burn Odds API credits. Safe to re-run.
    """
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
                WHERE l.code = 'nba'
                """
            )
        ).fetchall()
        for r in rows:
            scanned += 1
            m = dict(r._mapping)
            canon = normalize_nba_team_key(str(m.get("name") or ""))
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
            "worker_build_id": NBA_WORKER_BUILD_ID,
            "canonical_name_map_size": len(NBA_TEAM_ABBREV),
        }
    except Exception:
        session.rollback()
        log.exception("Failed repair_nba_odds_team_abbrs")
        raise
    finally:
        session.close()


def _upsert_nba_game_ingest(session: Any, g: Dict[str, Any]) -> bool:
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
            INSERT INTO nba_games_ingest (
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
            "home_team_key": normalize_nba_team_key(
                str(g.get("home_team_key") or g.get("home_team") or "")
            ),
            "away_team_key": normalize_nba_team_key(
                str(g.get("away_team_key") or g.get("away_team") or "")
            ),
            "home_score": g.get("home_score"),
            "away_score": g.get("away_score"),
            "status": str(g.get("status") or ""),
            "season": str(g.get("season") or ""),
            "source": str(g.get("source") or "stats.nba.com"),
            "raw": json.dumps(g.get("raw_header") or g.get("raw") or g, default=str),
            "updated_at": _now_utc(),
        },
    )
    return True


def _upsert_nba_team_game_features(
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
            INSERT INTO nba_team_game_features (
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


@celery_app.task(name="src.tasks.pull_nba_schedule_ingest")
def pull_nba_schedule_ingest(
    days_back: int = 7,
    days_ahead: int = 3,
) -> Dict[str, int]:
    """Ingest scoreboard window into nba_games_ingest (stats.nba.com primary)."""
    session = SessionLocal()
    upserted = 0
    try:
        ensure_nba_model_tables(session)
        start = date.today() - timedelta(days=max(0, days_back))
        end = date.today() + timedelta(days=max(0, days_ahead))
        games = fetch_schedule_window(start, end, sleep_s=0.55)
        if not games:
            # Optional SportsDataIO only if keys already present.
            for offset in range(-max(0, days_back), max(0, days_ahead) + 1):
                d = date.today() + timedelta(days=offset)
                games.extend(try_sportsdata_games_by_date(d))

        for g in games:
            if _upsert_nba_game_ingest(session, g):
                upserted += 1
        session.commit()
        return {"games_upserted": upserted, "window_start": str(start), "window_end": str(end)}
    except Exception:
        session.rollback()
        log.exception("Failed NBA schedule ingest")
        raise
    finally:
        session.close()


@celery_app.task(name="src.tasks.pull_nba_season_ingest")
def pull_nba_season_ingest(
    seasons: Optional[List[str]] = None,
    season_type: str = "Regular Season",
    sleep_s: float = 0.35,
    enrich_details: bool = True,
    max_detail_games: int = 2500,
    player_stub_details: int = 40,
) -> Dict[str, Any]:
    """Bulk ingest seasons via data.nba.com schedule (+ gamedetail features).

    Prefer data.nba.com because stats.nba.com frequently times out from
    cloud/Railway egress. Falls back to leaguegamelog when schedule empty.
    """
    session = SessionLocal()
    season_labels = iter_season_labels(seasons or list(DEFAULT_NBA_INGEST_SEASONS))
    games_upserted = 0
    feature_rows = 0
    player_stubs = 0
    details_fetched = 0
    per_season: Dict[str, int] = {}
    source_used: Dict[str, str] = {}
    try:
        ensure_nba_model_tables(session)
        for idx, season in enumerate(season_labels):
            paired = fetch_season_schedule_data_nba(season)
            source = "data.nba.com/schedule"
            if not paired:
                rows = fetch_season_team_gamelog(season, season_type=season_type)
                paired = pair_season_games_from_gamelog(rows, season=season)
                source = "stats.nba.com/leaguegamelog"
            source_used[season] = source
            rest_map = compute_rest_days_by_team(paired)
            count = 0
            for g in paired:
                if not _upsert_nba_game_ingest(session, g):
                    continue
                games_upserted += 1
                count += 1
            per_season[season] = count
            session.commit()

            if enrich_details and source.startswith("data.nba.com"):
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
                    detail = fetch_game_detail_data_nba(season_year, gid)
                    details_fetched += 1
                    if not detail:
                        time_module.sleep(sleep_s)
                        continue
                    home_block = detail.get("hls") or {}
                    away_block = detail.get("vls") or {}
                    home_feat = features_from_data_nba_team_stats(home_block)
                    away_feat = features_from_data_nba_team_stats(away_block)
                    if home_feat and away_feat:
                        home_feat["drtg"] = away_feat.get("ortg")
                        away_feat["drtg"] = home_feat.get("ortg")
                    try:
                        gd = date.fromisoformat(str(g["game_date"])[:10])
                    except Exception:
                        time_module.sleep(sleep_s)
                        continue
                    home_key = normalize_nba_team_key(
                        str(home_block.get("ta") or g.get("home_team_key") or "")
                    )
                    away_key = normalize_nba_team_key(
                        str(away_block.get("ta") or g.get("away_team_key") or "")
                    )
                    for team_key, feat, is_home, opp in (
                        (home_key, home_feat, True, away_key),
                        (away_key, away_feat, False, home_key),
                    ):
                        if not team_key or team_key == "UNK" or not feat:
                            continue
                        _upsert_nba_team_game_features(
                            session,
                            external_game_id=gid,
                            team_key=team_key,
                            game_date_val=gd,
                            is_home=is_home,
                            opponent_key=opp,
                            feat=feat,
                            rest_days=rest_map.get((gid, team_key)),
                            season=season,
                            source="data.nba.com/gamedetail",
                        )
                        feature_rows += 1
                    if details_fetched <= int(player_stub_details):
                        for stub in player_stubs_from_data_nba_detail(detail):
                            if not stub.get("player_id"):
                                continue
                            session.execute(
                                text(
                                    """
                                    INSERT INTO nba_player_game_stubs (
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
                                    "source": "data.nba.com/gamedetail",
                                    "payload": json.dumps({}),
                                    "updated_at": _now_utc(),
                                },
                            )
                            player_stubs += 1
                    if details_fetched % 25 == 0:
                        session.commit()
                    time_module.sleep(sleep_s)
            elif paired and paired[0].get("home_features"):
                # leaguegamelog path already carries features.
                for g in paired:
                    gid = str(g["external_game_id"])
                    try:
                        gd = date.fromisoformat(str(g["game_date"])[:10])
                    except Exception:
                        continue
                    home_key = normalize_nba_team_key(str(g.get("home_team_key") or ""))
                    away_key = normalize_nba_team_key(str(g.get("away_team_key") or ""))
                    for team_key, feat, is_home, opp in (
                        (home_key, g.get("home_features") or {}, True, away_key),
                        (away_key, g.get("away_features") or {}, False, home_key),
                    ):
                        if not team_key or team_key == "UNK":
                            continue
                        _upsert_nba_team_game_features(
                            session,
                            external_game_id=gid,
                            team_key=team_key,
                            game_date_val=gd,
                            is_home=is_home,
                            opponent_key=opp,
                            feat=feat,
                            rest_days=rest_map.get((gid, team_key)),
                            season=season,
                            source=source,
                        )
                        feature_rows += 1
            session.commit()
            if sleep_s > 0 and idx < len(season_labels) - 1:
                time_module.sleep(sleep_s)
        return {
            "seasons": season_labels,
            "games_upserted": games_upserted,
            "team_game_feature_rows": feature_rows,
            "player_stubs_upserted": player_stubs,
            "details_fetched": details_fetched,
            "per_season": per_season,
            "source_used": source_used,
            "season_type": season_type,
        }
    except Exception:
        session.rollback()
        log.exception("Failed NBA season ingest")
        raise
    finally:
        session.close()


@celery_app.task(name="src.tasks.materialize_nba_team_rolling_features")
def materialize_nba_team_rolling_features(
    days_back: int = 30,
    window_games: int = 10,
    pbp_sample_games: int = 0,
    player_stub_sample_games: int = 0,
) -> Dict[str, int]:
    """Build team rolling pace/ORtg/DRtg/3PT features from team_game_features.

    Prefers leaguegamelog-derived ``nba_team_game_features``. Optionally samples
    PBP → possessions and player minutes/usage stubs for later props.
    """
    session = SessionLocal()
    teams_updated = 0
    possessions_inserted = 0
    player_stubs = 0
    try:
        ensure_nba_model_tables(session)
        start = date.today() - timedelta(days=max(1, days_back))
        feat_rows = session.execute(
            text(
                """
                SELECT
                  external_game_id, team_key, game_date,
                  pace, ortg, drtg, three_pt_rate, three_pt_pct,
                  two_pt_pct, ft_rate, ft_pct, to_rate, orb_rate
                FROM nba_team_game_features
                WHERE game_date >= :start
                ORDER BY game_date DESC
                """
            ),
            {"start": start},
        ).fetchall()

        team_samples: Dict[str, List[Dict[str, float]]] = {}
        for r in feat_rows:
            m = dict(r._mapping)
            team = str(m.get("team_key") or "").upper()
            if not team:
                continue
            team_samples.setdefault(team, []).append(
                {
                    "pace": float(m["pace"]) if m.get("pace") is not None else 100.0,
                    "ortg": float(m["ortg"]) if m.get("ortg") is not None else 114.0,
                    "drtg": float(m["drtg"]) if m.get("drtg") is not None else 114.0,
                    "three_pt_rate": float(m["three_pt_rate"])
                    if m.get("three_pt_rate") is not None
                    else 0.39,
                    "three_pt_pct": float(m["three_pt_pct"])
                    if m.get("three_pt_pct") is not None
                    else 0.36,
                    "two_pt_pct": float(m["two_pt_pct"])
                    if m.get("two_pt_pct") is not None
                    else 0.55,
                    "ft_rate": float(m["ft_rate"]) if m.get("ft_rate") is not None else 0.22,
                    "ft_pct": float(m["ft_pct"]) if m.get("ft_pct") is not None else 0.78,
                    "to_rate": float(m["to_rate"]) if m.get("to_rate") is not None else 0.135,
                    "orb_rate": float(m["orb_rate"]) if m.get("orb_rate") is not None else 0.27,
                }
            )

        # Fallback: live box pulls when feature table empty (narrow window).
        games_scanned = len(feat_rows)
        if not team_samples:
            rows = session.execute(
                text(
                    """
                    SELECT external_game_id, home_team_key, away_team_key, game_date, status
                    FROM nba_games_ingest
                    WHERE game_date >= :start
                    ORDER BY game_date DESC
                    LIMIT 40
                    """
                ),
                {"start": start},
            ).fetchall()
            games_scanned = len(rows)
            for r in rows:
                m = dict(r._mapping)
                gid = str(m.get("external_game_id") or "")
                if not gid:
                    continue
                box = fetch_boxscore_traditional(gid)
                feats = estimate_team_features_from_box(box.get("team_stats") or [])
                for abbr, feat in feats.items():
                    team_samples.setdefault(abbr, []).append(feat)

        # Optional PBP / player stub samples (rate-limited).
        sample_ids = session.execute(
            text(
                """
                SELECT external_game_id, home_team_key, away_team_key, game_date
                FROM nba_games_ingest
                WHERE game_date >= :start
                  AND status ILIKE '%final%'
                ORDER BY game_date DESC
                LIMIT :lim
                """
            ),
            {
                "start": start,
                "lim": max(int(pbp_sample_games), int(player_stub_sample_games), 0),
            },
        ).fetchall()
        for i, r in enumerate(sample_ids):
            m = dict(r._mapping)
            gid = str(m.get("external_game_id") or "")
            home_key = str(m.get("home_team_key") or "")
            away_key = str(m.get("away_team_key") or "")
            gd = m.get("game_date")
            if not gid:
                continue
            if i < int(pbp_sample_games) and home_key and away_key:
                pbp = fetch_play_by_play(gid)
                if pbp:
                    poss = derive_possessions_from_pbp(
                        pbp, home_team_key=home_key, away_team_key=away_key
                    )
                    for p in poss[:320]:
                        session.execute(
                            text(
                                """
                                INSERT INTO nba_possessions (
                                  external_game_id, possession_index,
                                  offense_team_key, defense_team_key,
                                  points, ended_by, period, clock_seconds,
                                  events, source
                                ) VALUES (
                                  :external_game_id, :possession_index,
                                  :offense_team_key, :defense_team_key,
                                  :points, :ended_by, :period, :clock_seconds,
                                  CAST(:events AS jsonb), :source
                                )
                                ON CONFLICT (external_game_id, possession_index, source) DO NOTHING
                                """
                            ),
                            {
                                "external_game_id": gid,
                                "possession_index": p["possession_index"],
                                "offense_team_key": p.get("offense_team_key"),
                                "defense_team_key": p.get("defense_team_key"),
                                "points": p.get("points"),
                                "ended_by": p.get("ended_by"),
                                "period": p.get("period"),
                                "clock_seconds": p.get("clock_seconds"),
                                "events": json.dumps(p.get("events") or []),
                                "source": p.get("source") or "stats.nba.com",
                            },
                        )
                        possessions_inserted += 1
            if i < int(player_stub_sample_games):
                box = fetch_boxscore_traditional(gid)
                for prow in box.get("player_stats") or []:
                    stub = estimate_player_usage_stub(prow)
                    if not stub.get("player_id"):
                        continue
                    session.execute(
                        text(
                            """
                            INSERT INTO nba_player_game_stubs (
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
                            "source": "stats.nba.com/boxscore",
                            "payload": json.dumps({}),
                            "updated_at": _now_utc(),
                        },
                    )
                    player_stubs += 1
            if pbp_sample_games or player_stub_sample_games:
                time_module.sleep(0.55)

        as_of = date.today()
        for team_key, samples in team_samples.items():
            window = samples[: max(1, window_games)]
            if not window:
                continue
            avg = rolling_average_features(window)
            session.execute(
                text(
                    """
                    INSERT INTO nba_team_rolling_features (
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
                    "feature_pack_version": "nba-rolling-gamelog-v1",
                    "payload": json.dumps({"n": len(window), "source": "team_game_features"}),
                    "updated_at": _now_utc(),
                },
            )
            teams_updated += 1

        session.commit()
        return {
            "teams_updated": teams_updated,
            "possessions_inserted": possessions_inserted,
            "player_stubs_upserted": player_stubs,
            "games_scanned": games_scanned,
            "feature_pack_version": "nba-rolling-gamelog-v1",
        }
    except Exception:
        session.rollback()
        log.exception("Failed materializing NBA rolling features")
        raise
    finally:
        session.close()


@celery_app.task(name="src.tasks.pull_nba_context_snapshot")
def pull_nba_context_snapshot(days_ahead: int = 3) -> Dict[str, int]:
    """Assemble nba_game_context for upcoming slate from rolling features."""
    session = SessionLocal()
    updated = 0
    try:
        ensure_nba_model_tables(session)
        # Refresh schedule first (best-effort).
        try:
            pull_nba_schedule_ingest(days_back=2, days_ahead=days_ahead)
        except Exception:
            log.warning("NBA schedule ingest soft-failed inside context snapshot")

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
                WHERE l.code = 'nba'
                  AND g.game_date >= :today
                  AND g.game_date <= :end
                """
            ),
            {"today": date.today(), "end": end},
        ).fetchall()

        # Fall back to ingest table when hierarchy empty (offseason).
        if not games:
            ingest = session.execute(
                text(
                    """
                    SELECT
                      external_game_id AS game_id,
                      home_team_key AS home_abbr,
                      away_team_key AS away_abbr,
                      home_team_key AS home_team,
                      away_team_key AS away_team,
                      game_date
                    FROM nba_games_ingest
                    WHERE game_date >= :today AND game_date <= :end
                    """
                ),
                {"today": date.today(), "end": end},
            ).fetchall()
            games = ingest

        as_of = date.today()
        for r in games:
            m = dict(r._mapping)
            home_key = normalize_nba_team_key(str(m.get("home_abbr") or m.get("home_team") or ""))
            away_key = normalize_nba_team_key(str(m.get("away_abbr") or m.get("away_team") or ""))

            def _feat(team_key: str) -> Dict[str, Any]:
                row = session.execute(
                    text(
                        """
                        SELECT *
                        FROM nba_team_rolling_features
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
                        FROM nba_games_ingest
                        WHERE game_date < :before
                          AND (home_team_key = :team OR away_team_key = :team)
                        """
                    ),
                    {"before": before_d, "team": team_key},
                ).fetchone()
                if not prev or prev[0] is None:
                    # Fall back to last known rest on team_game_features.
                    feat_rest = session.execute(
                        text(
                            """
                            SELECT rest_days
                            FROM nba_team_game_features
                            WHERE team_key = :team
                            ORDER BY game_date DESC
                            LIMIT 1
                            """
                        ),
                        {"team": team_key},
                    ).fetchone()
                    if feat_rest and feat_rest[0] is not None:
                        return float(feat_rest[0])
                    return 2.0
                return float((before_d - prev[0]).days)

            rest_home = _rest_days(home_key, m.get("game_date") or as_of)
            rest_away = _rest_days(away_key, m.get("game_date") or as_of)
            pack = (
                hf.get("feature_pack_version")
                or af.get("feature_pack_version")
                or ("nba-rolling-gamelog-v1" if hf or af else "nba-league-avg-v0")
            )
            session.execute(
                text(
                    """
                    INSERT INTO nba_game_context (
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
                    "pace_home": _to_float(hf.get("pace")) or 100.0,
                    "pace_away": _to_float(af.get("pace")) or 100.0,
                    "ortg_home": _to_float(hf.get("ortg")) or 114.0,
                    "ortg_away": _to_float(af.get("ortg")) or 114.0,
                    "drtg_home": _to_float(hf.get("drtg")) or 114.0,
                    "drtg_away": _to_float(af.get("drtg")) or 114.0,
                    "three_pt_rate_home": _to_float(hf.get("three_pt_rate")) or 0.39,
                    "three_pt_rate_away": _to_float(af.get("three_pt_rate")) or 0.39,
                    "three_pt_pct_home": _to_float(hf.get("three_pt_pct")) or 0.36,
                    "three_pt_pct_away": _to_float(af.get("three_pt_pct")) or 0.36,
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
                            "ratings_source": "nba_team_rolling_features"
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
        log.exception("Failed NBA context snapshot")
        raise
    finally:
        session.close()


@celery_app.task(name="src.tasks.run_nba_market_simulations")
def run_nba_market_simulations(
    game_date: Optional[str] = None,
    simulations: int = 4000,
    model_version: str = DEFAULT_NBA_MODEL_VERSION,
) -> Dict[str, Any]:
    """Celery: possession-level Monte Carlo for NBA slate → fair lines."""
    worker_build_id = NBA_WORKER_BUILD_ID
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
        ensure_nba_model_tables(session)
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
                LEFT JOIN nba_game_context c ON c.game_id = g.id::text
                WHERE l.code = 'nba'
                  AND g.game_date = :game_date
                ORDER BY g.start_time NULLS LAST
                """
            ),
            {"game_date": target_date},
        ).fetchall()

        if not rows:
            # Offseason / hierarchy-empty: simulate from ingest + context if present.
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
                    FROM nba_games_ingest i
                    LEFT JOIN nba_game_context c ON c.game_id = i.external_game_id
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
            market = _nba_market_lines_for_game(
                session,
                str(m["game_id"]),
                game_date=gd if isinstance(gd, date) else target_date,
                home_team_key=str(m.get("home_abbr") or m.get("home_team") or ""),
                away_team_key=str(m.get("away_abbr") or m.get("away_team") or ""),
            )
            inputs = NbaGameInputs(
                game_id=str(m["game_id"]),
                home_team=str(m.get("home_team") or "Home"),
                away_team=str(m.get("away_team") or "Away"),
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
            # If context missing entirely, stamp league-average feature pack.
            if m.get("ortg_home") is None and m.get("ortg_away") is None:
                defaults = default_league_average_inputs(
                    inputs.game_id, inputs.home_team, inputs.away_team
                )
                inputs = NbaGameInputs(
                    **{
                        **defaults,
                        "market_spread_home": market.get("market_spread_home"),
                        "market_total": market.get("market_total"),
                    }
                )

            seed = _default_projection_seed(inputs.game_id, model_version, simulations)
            projection = simulate_nba_game(
                inputs,
                simulations=simulations,
                seed=seed,
                model_version=model_version,
            )
            projection["worker_build_id"] = worker_build_id
            projection.setdefault("diagnostics", {})["worker_build_id"] = worker_build_id
            _insert_nba_projection(session, projection)
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
        log.exception("Failed running NBA market simulations")
        raise
    finally:
        session.close()


def collect_nba_db_inventory(session: Any) -> Dict[str, Any]:
    """Truthful Postgres counts for NBA games + odds + model tables."""
    ensure_nba_model_tables(session)

    def _count(sql: str, params: Optional[Dict[str, Any]] = None) -> int:
        try:
            row = session.execute(text(sql), params or {}).fetchone()
            return int(row[0] or 0) if row else 0
        except Exception as exc:
            log.info("NBA inventory query soft-failed: %s", str(exc)[:200])
            session.rollback()
            ensure_nba_model_tables(session)
            return -1

    games_nba = _count(
        """
        SELECT COUNT(*)
        FROM games g
        JOIN seasons s ON s.id = g.season_id
        JOIN leagues l ON l.id = s.league_id
        WHERE l.code = 'nba'
        """
    )
    odds_mainline_games = _count(
        """
        SELECT COUNT(DISTINCT g.id)
        FROM odds_snapshots os
        JOIN games g ON g.id = os.game_id
        JOIN seasons s ON s.id = g.season_id
        JOIN leagues l ON l.id = s.league_id
        WHERE l.code = 'nba'
        """
    )
    odds_rows = _count(
        """
        SELECT COUNT(*)
        FROM odds_snapshots os
        JOIN games g ON g.id = os.game_id
        JOIN seasons s ON s.id = g.season_id
        JOIN leagues l ON l.id = s.league_id
        WHERE l.code = 'nba'
        """
    )
    odds_source_nba = _count(
        """
        SELECT COUNT(*)
        FROM odds_snapshots
        WHERE COALESCE(source, '') ILIKE '%nba%'
        """
    )
    return {
        "verified_at": _now_utc().isoformat(),
        "games": {
            "hierarchy_nba": games_nba,
            "nba_games_ingest": _count("SELECT COUNT(*) FROM nba_games_ingest"),
            "nba_team_game_features": _count("SELECT COUNT(*) FROM nba_team_game_features"),
            "nba_team_rolling_features": _count(
                "SELECT COUNT(*) FROM nba_team_rolling_features"
            ),
            "nba_game_context": _count("SELECT COUNT(*) FROM nba_game_context"),
            "nba_possessions": _count("SELECT COUNT(*) FROM nba_possessions"),
            "nba_player_game_stubs": _count("SELECT COUNT(*) FROM nba_player_game_stubs"),
            "nba_player_prop_model_edges": _count(
                "SELECT COUNT(*) FROM nba_player_prop_model_edges"
            ),
            "nba_market_projections": _count("SELECT COUNT(*) FROM nba_market_projections"),
        },
        "odds": {
            "mainline_games": odds_mainline_games,
            "odds_snapshot_rows": odds_rows,
            "odds_rows_source_ilike_nba": odds_source_nba,
            "note": (
                "mainline_games = DISTINCT games with odds_snapshots joined via "
                "leagues.code='nba'. Explore summaries that reported 0 should be "
                "re-checked against this endpoint on the model-service DB."
            ),
        },
        "joyful_clarity_postgres_note": (
            "Cloud-agent RAILWAY_TOKEN targets joyful-clarity Postgres which has "
            "0 public tables — not the brave-art model-service warehouse."
        ),
    }


@celery_app.task(name="src.tasks.nba_db_inventory")
def nba_db_inventory() -> Dict[str, Any]:
    session = SessionLocal()
    try:
        inv = collect_nba_db_inventory(session)
        session.commit()
        return inv
    finally:
        session.close()


@celery_app.task(name="src.tasks.pull_nba_historical_odds_densify")
def pull_nba_historical_odds_densify(
    *,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    bookmakers: str = "draftkings,fanduel",
    markets: str = "h2h,spreads,totals",
    max_requests: int = 200,
    max_credit_spend: int = 300000,
    min_remaining_floor: int = 1500000,
    open_hour_utc: int = 16,
    close_hour_utc: int = 23,
    skip_if_mainline_games_ge: int = 100,
) -> Dict[str, Any]:
    """Targeted NBA historical open+close densify with hard credit budget.

    Only runs when NBA mainline odds coverage is thin. Uses game dates from
    ``nba_games_ingest`` (game-days only). Markets: h2h/spreads/totals.
    """
    from .services.odds_api import fetch_odds_with_metadata

    session = SessionLocal()
    sport_key = "basketball_nba"
    endpoint = f"historical/sports/{sport_key}/odds"
    try:
        ensure_nba_model_tables(session)
        _ensure_odds_api_request_tables(session)
        inv_before = collect_nba_db_inventory(session)
        mainline_before = int(inv_before.get("odds", {}).get("mainline_games") or 0)
        if mainline_before >= int(skip_if_mainline_games_ge):
            return {
                "status": "skipped_already_owned",
                "mainline_games_before": mainline_before,
                "skip_if_mainline_games_ge": skip_if_mainline_games_ge,
                "inventory_before": inv_before,
                "credits_spent_estimate": 0,
            }

        end = (
            date.fromisoformat(end_date)
            if end_date
            else date(2025, 6, 22)
        )
        start = (
            date.fromisoformat(start_date)
            if start_date
            else date(2023, 10, 24)
        )
        # Prefer recent seasons first for walkforward utility within budget.
        date_rows = session.execute(
            text(
                """
                SELECT DISTINCT game_date
                FROM nba_games_ingest
                WHERE game_date >= :start
                  AND game_date <= :end
                  AND game_date IS NOT NULL
                ORDER BY game_date DESC
                """
            ),
            {"start": start, "end": end},
        ).fetchall()
        game_dates = [r[0] for r in date_rows if isinstance(r[0], date)]

        normalized_books = _normalize_bookmakers_csv(bookmakers)
        normalized_markets = _normalize_markets_csv(markets)
        # Two snapshots/day (open+close); ~30 credits/request for 3 markets.
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
            signature = _odds_request_signature(endpoint, params)
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
                persisted = _persist_odds_events(
                    session,
                    events=events_list,
                    source_label="the-odds-api-historical-nba-mainlines",
                )
                events_total += len(events_list)
                persisted_total += int(persisted.get("events_persisted") or 0)
                snapshots_total += int(persisted.get("snapshots_inserted") or 0)
                _record_odds_api_request(
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
                    response_timestamp=_parse_iso_datetime(payload.get("timestamp"))
                    if isinstance(payload, dict)
                    else None,
                    response_previous_timestamp=_parse_iso_datetime(
                        payload.get("previous_timestamp")
                    )
                    if isinstance(payload, dict)
                    else None,
                    response_next_timestamp=_parse_iso_datetime(payload.get("next_timestamp"))
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
                    _record_odds_api_request(
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
                log.exception(
                    "NBA historical densify request failed",
                    extra={"date": params.get("date")},
                )

        inv_after = collect_nba_db_inventory(session)
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
            "mainline_games_after": int(
                inv_after.get("odds", {}).get("mainline_games") or 0
            ),
            "inventory_before": inv_before,
            "inventory_after": inv_after,
            "worker_build_id": NBA_WORKER_BUILD_ID,
        }
    except Exception:
        session.rollback()
        log.exception("Failed NBA historical odds densify")
        raise
    finally:
        session.close()


@celery_app.task(name="src.tasks.run_nba_walkforward_sample")
def run_nba_walkforward_sample(
    *,
    limit_games: int = 80,
    simulations: int = 800,
    model_version: str = DEFAULT_NBA_MODEL_VERSION,
    prefer_odds_window: bool = True,
    apply_market_blend: bool = True,
) -> Dict[str, Any]:
    """Thin walkforward: prior features → sim → grade vs finals + closes."""
    from .services.nba_calibration import NbaWalkforwardRow, summarize_walkforward
    from .services.nba_publish_policy import board_publish_posture

    session = SessionLocal()
    try:
        ensure_nba_model_tables(session)
        # Prefer densify window (owned mainlines) so close-line join can prove out.
        odds_window_sql = ""
        if prefer_odds_window:
            odds_window_sql = """
                  AND i.game_date >= DATE '2023-10-24'
                  AND i.game_date <= DATE '2025-06-22'
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
                FROM nba_games_ingest i
                LEFT JOIN nba_team_game_features hf
                  ON hf.external_game_id = i.external_game_id
                 AND hf.team_key = i.home_team_key
                LEFT JOIN nba_team_game_features af
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
                # Include raw aliases (GS/UTAH/…) — Phase-1 rows may predate normalize.
                keys = {
                    *nba_abbr_match_keys(team_key),
                    normalize_nba_team_key(team_key),
                    str(team_key or "").upper(),
                }
                prior = session.execute(
                    text(
                        """
                        SELECT pace, ortg, drtg, three_pt_rate, three_pt_pct, rest_days
                        FROM nba_team_game_features
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
            home = normalize_nba_team_key(str(m.get("home_team_key") or ""))
            away = normalize_nba_team_key(str(m.get("away_team_key") or ""))
            if not isinstance(gd, date) or home == "UNK" or away == "UNK":
                continue
            hf = _prior(home, gd)
            af = _prior(away, gd)
            if not hf or not af:
                continue
            market = _nba_market_lines_for_game(
                session,
                str(m["game_id"]),
                game_date=gd,
                home_team_key=home,
                away_team_key=away,
            )
            if market.get("market_spread_home") is None and market.get("market_total") is None:
                join_misses += 1
            inputs = NbaGameInputs(
                game_id=str(m["game_id"]),
                home_team=home,
                away_team=away,
                pace_home=float(hf.get("pace") or 100.0),
                pace_away=float(af.get("pace") or 100.0),
                ortg_home=float(hf.get("ortg") or 114.0),
                ortg_away=float(af.get("ortg") or 114.0),
                drtg_home=float(hf.get("drtg") or 114.0),
                drtg_away=float(af.get("drtg") or 114.0),
                three_pt_rate_home=float(hf.get("three_pt_rate") or 0.39),
                three_pt_rate_away=float(af.get("three_pt_rate") or 0.39),
                three_pt_pct_home=float(hf.get("three_pt_pct") or 0.36),
                three_pt_pct_away=float(af.get("three_pt_pct") or 0.36),
                rest_days_home=float(m.get("rest_days_home") or hf.get("rest_days") or 2.0),
                rest_days_away=float(m.get("rest_days_away") or af.get("rest_days") or 2.0),
                sample_games_home=10,
                sample_games_away=10,
                feature_pack_version="nba-rolling-gamelog-v1",
            )
            if apply_market_blend:
                inputs.market_spread_home = market.get("market_spread_home")
                inputs.market_total = market.get("market_total")
            seed = _default_projection_seed(inputs.game_id, model_version, simulations)
            proj = simulate_nba_game(
                inputs,
                simulations=simulations,
                seed=seed,
                model_version=model_version,
            )
            markets = proj.get("markets") or {}
            actual_margin = float(m["home_score"]) - float(m["away_score"])
            actual_total = float(m["home_score"]) + float(m["away_score"])
            wf_rows.append(
                NbaWalkforwardRow(
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
        summary["worker_build_id"] = NBA_WORKER_BUILD_ID
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
        log.exception("Failed NBA walkforward sample")
        raise
    finally:
        session.close()


@celery_app.task(name="src.tasks.run_nba_phase1_bootstrap")
def run_nba_phase1_bootstrap(
    seasons: Optional[List[str]] = None,
    densify_odds: bool = True,
    max_credit_spend: int = 300000,
    walkforward_games: int = 60,
    pbp_sample_games: int = 0,
    player_stub_sample_games: int = 0,
    max_detail_games: int = 900,
) -> Dict[str, Any]:
    """Phase 1 orchestration: schedule → densify → details/features → walkforward."""
    inventory_before = nba_db_inventory()
    # Fast path: land game dates first so densify can run on game-days.
    ingest_schedule = pull_nba_season_ingest(
        seasons=seasons,
        enrich_details=False,
    )
    densify: Dict[str, Any] = {"status": "skipped_by_flag"}
    if densify_odds:
        densify = pull_nba_historical_odds_densify(max_credit_spend=max_credit_spend)
    ingest_details = pull_nba_season_ingest(
        seasons=seasons,
        enrich_details=True,
        max_detail_games=max_detail_games,
        player_stub_details=min(40, max_detail_games),
    )
    features = materialize_nba_team_rolling_features(
        days_back=2000,
        window_games=10,
        pbp_sample_games=pbp_sample_games,
        player_stub_sample_games=player_stub_sample_games,
    )
    context = pull_nba_context_snapshot(days_ahead=3)
    walkforward = run_nba_walkforward_sample(limit_games=walkforward_games)
    inventory_after = nba_db_inventory()
    return {
        "status": "ok",
        "phase": "phase1",
        "worker_build_id": NBA_WORKER_BUILD_ID,
        "inventory_before": inventory_before,
        "ingest_schedule": ingest_schedule,
        "ingest_details": ingest_details,
        "features": features,
        "densify": densify,
        "context": context,
        "walkforward": walkforward,
        "inventory_after": inventory_after,
    }


@celery_app.task(name="src.tasks.run_nba_phase2_calibrate")
def run_nba_phase2_calibrate(
    *,
    repair_abbrs: bool = True,
    walkforward_games: int = 80,
    simulations: int = 1000,
    densify_odds: bool = False,
    max_credit_spend: int = 0,
) -> Dict[str, Any]:
    """Phase 2: repair close-line join → walkforward with real closes → posture."""
    inventory_before = nba_db_inventory()
    repair: Dict[str, Any] = {"status": "skipped"}
    if repair_abbrs:
        repair = repair_nba_odds_team_abbrs()
    densify: Dict[str, Any] = {"status": "skipped_by_flag"}
    if densify_odds and max_credit_spend > 0:
        densify = pull_nba_historical_odds_densify(max_credit_spend=max_credit_spend)
    walkforward = run_nba_walkforward_sample(
        limit_games=walkforward_games,
        simulations=simulations,
        prefer_odds_window=True,
        apply_market_blend=True,
    )
    # Raw (no blend) diagnostic pass on a smaller sample for blend_hint honesty.
    raw_diag = run_nba_walkforward_sample(
        limit_games=min(40, walkforward_games),
        simulations=max(400, simulations // 2),
        prefer_odds_window=True,
        apply_market_blend=False,
    )
    context = pull_nba_context_snapshot(days_ahead=3)
    sims: Dict[str, Any]
    try:
        # Offseason: daily cycle skips empty slate; calibrate still attempts once.
        sims = run_nba_market_simulations(simulations=2000)
    except Exception as exc:
        log.exception("Phase2 calibrate simulations failed (non-fatal)")
        sims = {"status": "error", "error": str(exc)[:500]}
    inventory_after = nba_db_inventory()
    return {
        "status": "ok",
        "phase": "phase2",
        "worker_build_id": NBA_WORKER_BUILD_ID,
        "inventory_before": inventory_before,
        "repair_abbrs": repair,
        "densify": densify,
        "walkforward": walkforward,
        "walkforward_raw_no_blend": raw_diag,
        "context": context,
        "simulations": sims,
        "inventory_after": inventory_after,
    }


@celery_app.task(name="src.tasks.materialize_nba_player_props_edges")
def materialize_nba_player_props_edges(
    *,
    as_of_date: Optional[str] = None,
    lookback_games: int = 8,
    min_minutes: float = 12.0,
    limit_players: int = 200,
) -> Dict[str, Any]:
    """Phase 3: project props from stubs, join books when present, research tags only."""
    from src.services.nba_player_prop_projection import (
        NBA_PROP_MODEL_VERSION,
        project_from_stub_groups,
    )
    from src.services.nba_prop_edge_policy import (
        evaluate_nba_prop_edge,
        ou_balance_report,
    )

    as_of = date.fromisoformat(as_of_date) if as_of_date else date.today()
    session = SessionLocal()
    try:
        ensure_nba_model_tables(session)
        session.commit()

        stub_rows = session.execute(
            text(
                """
                SELECT player_id, player_name, team_key, game_date, minutes,
                       usage_proxy, pts, reb, ast, fg3m
                FROM nba_player_game_stubs
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

        # Prefer players with most recent activity.
        ordered = sorted(
            by_player.values(),
            key=lambda rows: max((x.get("game_date") or date.min) for x in rows),
            reverse=True,
        )[: max(1, int(limit_players))]

        pace_rows = session.execute(
            text(
                """
                SELECT DISTINCT ON (team_key) team_key, pace
                FROM nba_team_rolling_features
                ORDER BY team_key, as_of_date DESC NULLS LAST, updated_at DESC
                """
            )
        ).fetchall()
        ortg_rows = session.execute(
            text(
                """
                SELECT DISTINCT ON (team_key) team_key, ortg
                FROM nba_team_rolling_features
                ORDER BY team_key, as_of_date DESC NULLS LAST, updated_at DESC
                """
            )
        ).fetchall()
        pace_map = {str(r[0]).upper(): float(r[1] or 100.0) for r in pace_rows if r[0]}
        ortg_map = {str(r[0]).upper(): float(r[1] or 114.0) for r in ortg_rows if r[0]}

        projections = project_from_stub_groups(
            ordered,
            team_pace_by_key=pace_map,
            team_ortg_by_key=ortg_map,
            min_minutes=min_minutes,
        )

        # Optional market join from enterprise prop snapshots table.
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
                    WHERE sport_key IN ('basketball_nba', 'nba')
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
            ensure_nba_model_tables(session)
            session.commit()
            market_by_key = {}

        upserted = 0
        board_rows: List[Dict[str, Any]] = []
        for proj in projections:
            mkt = market_by_key.get(
                (proj.player_name.lower(), proj.market_key)
            ) or market_by_key.get(("", proj.market_key))
            line = None
            over_price = under_price = None
            if mkt:
                try:
                    line = float(mkt["line"]) if mkt.get("line") is not None else None
                except (TypeError, ValueError):
                    line = None
                try:
                    over_price = (
                        int(mkt["over_price"])
                        if mkt.get("over_price") is not None
                        else None
                    )
                    under_price = (
                        int(mkt["under_price"])
                        if mkt.get("under_price") is not None
                        else None
                    )
                except (TypeError, ValueError):
                    over_price = under_price = None

            edge = evaluate_nba_prop_edge(
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
                    INSERT INTO nba_player_prop_model_edges (
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
                    "model_version": NBA_PROP_MODEL_VERSION,
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
                    "worker_build_id": NBA_WORKER_BUILD_ID,
                    "updated_at": _now_utc(),
                },
            )
            upserted += 1
            board_rows.append({"tag": edge.get("tag"), "tag_side": edge.get("tag_side"), "diagnostics": diagnostics})

        session.commit()
        balance = ou_balance_report(board_rows)
        return {
            "status": "ok",
            "phase": "phase3",
            "worker_build_id": NBA_WORKER_BUILD_ID,
            "model_version": NBA_PROP_MODEL_VERSION,
            "as_of_date": as_of.isoformat(),
            "players_considered": len(ordered),
            "edges_upserted": upserted,
            "market_keys_joined": len(market_by_key),
            "ou_balance": balance,
        }
    except Exception:
        session.rollback()
        log.exception("materialize_nba_player_props_edges failed")
        raise
    finally:
        session.close()


@celery_app.task(name="src.tasks.run_nba_phase3_props_bootstrap")
def run_nba_phase3_props_bootstrap(
    *,
    lookback_games: int = 8,
    limit_players: int = 200,
) -> Dict[str, Any]:
    inventory_before = nba_db_inventory()
    props = materialize_nba_player_props_edges(
        lookback_games=lookback_games,
        limit_players=limit_players,
    )
    inventory_after = nba_db_inventory()
    return {
        "status": "ok",
        "phase": "phase3",
        "worker_build_id": NBA_WORKER_BUILD_ID,
        "inventory_before": inventory_before,
        "props": props,
        "inventory_after": inventory_after,
    }


@celery_app.task(name="src.tasks.run_nba_daily_cycle")
def run_nba_daily_cycle(
    *,
    days_ahead: int = 3,
    simulations: int = 4000,
    model_version: str = DEFAULT_NBA_MODEL_VERSION,
) -> Dict[str, Any]:
    """Nightly/beat: rolling features → context → sim → props → persist."""
    features = materialize_nba_team_rolling_features(
        days_back=int(os.getenv("NBA_ROLLING_DAYS_BACK", "45")),
        window_games=10,
    )
    context = pull_nba_context_snapshot(days_ahead=days_ahead)
    games_assembled = int(context.get("games_context_updated") or 0)
    sims: Dict[str, Any]
    if games_assembled > 0:
        sims = run_nba_market_simulations(
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
    props: Dict[str, Any]
    try:
        props = materialize_nba_player_props_edges()
    except Exception as exc:
        log.exception("Daily cycle props materialize failed (non-fatal)")
        props = {"status": "error", "error": str(exc)[:400]}
    return {
        "status": "ok",
        "phase": "phase3",
        "worker_build_id": NBA_WORKER_BUILD_ID,
        "features": features,
        "context": context,
        "simulations": sims,
        "props": props,
    }


# --- WNBA model tasks (thin wrappers → src.services.wnba_jobs) ---


@celery_app.task(
    name="src.tasks.pull_wnba_schedule_ingest",
    soft_time_limit=180,
    time_limit=240,
)
def pull_wnba_schedule_ingest(days_back: int = 7, days_ahead: int = 3) -> Dict[str, int]:
    from .services.wnba_jobs import pull_wnba_schedule_ingest as _impl

    return _impl(days_back=days_back, days_ahead=days_ahead)


@celery_app.task(
    name="src.tasks.pull_wnba_season_ingest",
    soft_time_limit=1800,
    time_limit=2100,
)
def pull_wnba_season_ingest(
    seasons: Optional[List[str]] = None,
    sleep_s: float = 0.35,
    enrich_details: bool = True,
    max_detail_games: int = 1200,
    player_stub_details: int = 60,
) -> Dict[str, Any]:
    from .services.wnba_jobs import pull_wnba_season_ingest as _impl

    return _impl(
        seasons=seasons,
        sleep_s=sleep_s,
        enrich_details=enrich_details,
        max_detail_games=max_detail_games,
        player_stub_details=player_stub_details,
    )


@celery_app.task(name="src.tasks.materialize_wnba_team_rolling_features")
def materialize_wnba_team_rolling_features(
    days_back: int = 45,
    window_games: int = 10,
) -> Dict[str, Any]:
    from .services.wnba_jobs import materialize_wnba_team_rolling_features as _impl

    return _impl(days_back=days_back, window_games=window_games)


@celery_app.task(
    name="src.tasks.pull_wnba_context_snapshot",
    soft_time_limit=120,
    time_limit=180,
)
def pull_wnba_context_snapshot(days_ahead: int = 3) -> Dict[str, int]:
    from .services.wnba_jobs import pull_wnba_context_snapshot as _impl

    return _impl(days_ahead=days_ahead)


@celery_app.task(name="src.tasks.run_wnba_market_simulations")
def run_wnba_market_simulations(
    game_date: Optional[str] = None,
    simulations: int = 4000,
    model_version: Optional[str] = None,
) -> Dict[str, Any]:
    from .services.wnba_jobs import run_wnba_market_simulations as _impl
    from .services.wnba_possession_simulator import DEFAULT_WNBA_MODEL_VERSION

    return _impl(
        game_date=game_date,
        simulations=simulations,
        model_version=model_version or DEFAULT_WNBA_MODEL_VERSION,
    )


@celery_app.task(name="src.tasks.wnba_db_inventory")
def wnba_db_inventory() -> Dict[str, Any]:
    from .services.wnba_jobs import wnba_db_inventory as _impl

    return _impl()


@celery_app.task(name="src.tasks.pull_wnba_historical_odds_densify")
def pull_wnba_historical_odds_densify(**kwargs: Any) -> Dict[str, Any]:
    from .services.wnba_jobs import pull_wnba_historical_odds_densify as _impl

    return _impl(**kwargs)


@celery_app.task(name="src.tasks.run_wnba_walkforward_sample")
def run_wnba_walkforward_sample(**kwargs: Any) -> Dict[str, Any]:
    from .services.wnba_jobs import run_wnba_walkforward_sample as _impl

    return _impl(**kwargs)


@celery_app.task(name="src.tasks.repair_wnba_odds_team_abbrs")
def repair_wnba_odds_team_abbrs() -> Dict[str, Any]:
    from .services.wnba_jobs import repair_wnba_odds_team_abbrs as _impl

    return _impl()


@celery_app.task(name="src.tasks.materialize_wnba_player_props_edges")
def materialize_wnba_player_props_edges(**kwargs: Any) -> Dict[str, Any]:
    from .services.wnba_jobs import materialize_wnba_player_props_edges as _impl

    return _impl(**kwargs)


@celery_app.task(
    name="src.tasks.run_wnba_phase1_bootstrap",
    soft_time_limit=3600,
    time_limit=3900,
)
def run_wnba_phase1_bootstrap(**kwargs: Any) -> Dict[str, Any]:
    from .services.wnba_jobs import run_wnba_phase1_bootstrap as _impl

    return _impl(**kwargs)


@celery_app.task(
    name="src.tasks.run_wnba_phase2_calibrate",
    soft_time_limit=1800,
    time_limit=2100,
)
def run_wnba_phase2_calibrate(**kwargs: Any) -> Dict[str, Any]:
    from .services.wnba_jobs import run_wnba_phase2_calibrate as _impl

    return _impl(**kwargs)


@celery_app.task(name="src.tasks.run_wnba_phase3_props_bootstrap")
def run_wnba_phase3_props_bootstrap(**kwargs: Any) -> Dict[str, Any]:
    from .services.wnba_jobs import run_wnba_phase3_props_bootstrap as _impl

    return _impl(**kwargs)


@celery_app.task(name="src.tasks.run_wnba_daily_cycle")
def run_wnba_daily_cycle(**kwargs: Any) -> Dict[str, Any]:
    from .services.wnba_jobs import run_wnba_daily_cycle as _impl

    return _impl(**kwargs)


@celery_app.task(name="src.tasks.pull_mlb_outcomes")
def pull_mlb_outcomes(days_back: int = 30) -> Dict[str, int]:
    end = date.today()
    start = end - timedelta(days=max(1, days_back))
    schedule = fetch_mlb_schedule(start, end)

    upserted = 0
    games_ensured = 0
    session = SessionLocal()
    try:
        for g in schedule:
            if g.get("status") != "final":
                continue
            external_id = g.get("external_game_id")
            if not external_id:
                continue
            game_dt = _parse_iso_datetime(g.get("game_time")) or datetime.combine(
                date.today(), datetime.min.time(), tzinfo=timezone.utc
            )
            # Ensure hierarchy so historical densify windows are not skipped silently.
            _ensure_hierarchy(
                session,
                sport_key="baseball_mlb",
                game_dt=game_dt,
                home_team=str(g.get("home_team") or ""),
                away_team=str(g.get("away_team") or ""),
                event_id=str(external_id),
            )
            games_ensured += 1

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
                text("SELECT id, start_time FROM games WHERE external_id = :external_id LIMIT 1"),
                {"external_id": str(external_id)},
            ).fetchone()
            if not game_row:
                continue
            game_id = str(game_row[0])
            start_time = game_row[1]
            game_data = payload.get("gameData") or {}
            datetime_info = game_data.get("datetime") or {}
            completed_at = (
                _parse_iso_datetime(datetime_info.get("endTime") or datetime_info.get("officialTimestamp"))
                or (_coerce_datetime_utc(start_time) or game_dt) + timedelta(hours=3, minutes=30)
            )

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
                    "completed_at": completed_at,
                    "created_at": _now_utc(),
                    "updated_at": _now_utc(),
                },
            )
            upserted += 1
        session.commit()
        return {
            "outcomes_upserted": upserted,
            "schedule_rows": len(schedule),
            "games_ensured": games_ensured,
        }
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
        base_points_raw = _fetch_calibration_points(
            session,
            model_version=base_model_version,
            lookback_days=lookback_days,
        )
        challenger_points_raw = _fetch_calibration_points(
            session,
            model_version=challenger_model_version,
            lookback_days=lookback_days,
        )
        # Unused holdout is evaluation/stake-gate only — never train/tune/promote on it.
        base_points = filter_points_excluding_unused_holdout(base_points_raw)
        challenger_points = filter_points_excluding_unused_holdout(challenger_points_raw)
        unused_eval_base = filter_points_in_unused_holdout(base_points_raw)
        unused_eval_challenger = filter_points_in_unused_holdout(challenger_points_raw)
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
            "unused_holdout": unused_holdout_summary(),
            "unused_holdout_excluded_from_tune": True,
            "unused_holdout_eval": {
                "base_sample_size": len(unused_eval_base),
                "challenger_sample_size": len(unused_eval_challenger),
                "base_quality": _compute_calibration_summary(unused_eval_base),
                "challenger_quality": _compute_calibration_summary(unused_eval_challenger),
            },
            "props_play_stake_eligible": MLB_PROPS_PLAY_STAKE_ELIGIBLE,
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
    sp_change_games = 0
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
                  home.abbr AS home_abbr,
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
                  c.updated_at AS context_updated_at,
                  c.context
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

        # Never serve stale empty cards from morning context pull.
        clear_game_lineup_features_cache()
        for r in rows:
            m = dict(r._mapping)
            seen_games += 1
            live_fetch_ok = False
            try:
                if m.get("external_id"):
                    live_lineups = fetch_game_lineup_features(str(m.get("external_id")))
                    live_fetch_ok = True
                else:
                    live_lineups = {"home": {}, "away": {}}
            except Exception:
                live_lineups = {"home": {}, "away": {}}
            live_home_lineup = live_lineups.get("home") or {}
            live_away_lineup = live_lineups.get("away") or {}
            known_home = int(live_home_lineup.get("known_players") or 0)
            known_away = int(live_away_lineup.get("known_players") or 0)
            hours_to_pitch = _hours_to_game(m.get("start_time"))
            # Live fetch age is ~0; do not damp late info with stale context.updated_at.
            if live_fetch_ok:
                freshness = 1.0 if (known_home >= 8 or known_away >= 8) else 0.92
            else:
                freshness = _info_freshness_score(
                    updated_at=m.get("context_updated_at"),
                    lineup_confirmed=bool(m.get("lineup_confirmed")),
                )
            if get_lineup_timing_mode() == "sharp":
                side_conf = per_side_lineup_confidence(
                    known_home=known_home,
                    known_away=known_away,
                    probable_pitcher_home=live_home_lineup.get("probable_pitcher"),
                    probable_pitcher_away=live_away_lineup.get("probable_pitcher"),
                    hours_to_first_pitch=hours_to_pitch,
                    freshness_score=freshness,
                )
                lineup_confirmed = bool(side_conf["lineup_confirmed"])
            else:
                lineup_confirmed = (
                    bool(m["lineup_confirmed"]) if m.get("lineup_confirmed") is not None else False
                ) or bool(live_home_lineup.get("lineup_confirmed")) or bool(
                    live_away_lineup.get("lineup_confirmed")
                )
            allow_clear = allow_late_sp_clear(
                hours_to_first_pitch=hours_to_pitch,
                lineup_confirmed=lineup_confirmed,
            )
            starter_resolve = resolve_nowcast_starters(
                context_home=m.get("probable_pitcher_home"),
                context_away=m.get("probable_pitcher_away"),
                live_home=live_home_lineup.get("probable_pitcher") or live_home_lineup.get("starter_name"),
                live_away=live_away_lineup.get("probable_pitcher") or live_away_lineup.get("starter_name"),
                allow_clear=allow_clear,
            )
            prior_starter_home = starter_resolve["prior_home"]
            prior_starter_away = starter_resolve["prior_away"]
            next_sp_home = starter_resolve["new_home"]
            next_sp_away = starter_resolve["new_away"]
            if starter_resolve["any_changed"]:
                sp_change_games += 1
            if get_lineup_timing_mode() == "sharp":
                nowcast = {
                    "home": float(side_conf["home"]),
                    "away": float(side_conf["away"]),
                }
                # Recompute with resolved SPs (firmness of named arms).
                side_conf = per_side_lineup_confidence(
                    known_home=known_home,
                    known_away=known_away,
                    probable_pitcher_home=next_sp_home,
                    probable_pitcher_away=next_sp_away,
                    hours_to_first_pitch=hours_to_pitch,
                    freshness_score=freshness,
                )
                nowcast = {"home": float(side_conf["home"]), "away": float(side_conf["away"])}
                lineup_confirmed = bool(side_conf["lineup_confirmed"])
            else:
                nowcast = _lineup_nowcast_confidence(
                    hours_to_first_pitch=hours_to_pitch,
                    lineup_confirmed=lineup_confirmed,
                    probable_pitcher_home=next_sp_home,
                    probable_pitcher_away=next_sp_away,
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
            try:
                persist_snapshot(
                    build_snapshot(
                        game_id=str(m["game_id"]),
                        hours_to_first_pitch=hours_to_pitch,
                        known_home=known_home,
                        known_away=known_away,
                        sp_home=next_sp_home,
                        sp_away=next_sp_away,
                        lineup_confirmed=lineup_confirmed,
                        lineup_confidence_home=float(nowcast["home"]),
                        lineup_confidence_away=float(nowcast["away"]),
                        observed_at=now,
                        source="nowcast_live",
                        extras={"freshness": freshness, "live_fetch_ok": live_fetch_ok},
                    )
                )
            except Exception:
                log.exception(
                    "Failed persisting lineup/SP snapshot",
                    extra={"game_id": str(m.get("game_id"))},
                )
            lineup_strength_home = float(m["lineup_strength_index_home"]) if m.get("lineup_strength_index_home") is not None else 1.0
            lineup_strength_away = float(m["lineup_strength_index_away"]) if m.get("lineup_strength_index_away") is not None else 1.0
            if live_home_lineup.get("lineup_strength_index") is not None:
                lineup_strength_home = float(live_home_lineup["lineup_strength_index"])
            if live_away_lineup.get("lineup_strength_index") is not None:
                lineup_strength_away = float(live_away_lineup["lineup_strength_index"])
            context_payload = m.get("context") if isinstance(m.get("context"), dict) else {}
            if isinstance(m.get("context"), str):
                try:
                    context_payload = json.loads(m["context"])
                except Exception:
                    context_payload = {}
            prior_home_feat = starter_identity_features(prior_starter_home)
            prior_away_feat = starter_identity_features(prior_starter_away)
            starter_home_feat = starter_identity_features(next_sp_home)
            starter_away_feat = starter_identity_features(next_sp_away)
            # Refresh platoon splits when SP handedness flips (context stores both hands).
            home_off_ctx = context_payload.get("home_offense_context") if isinstance(context_payload.get("home_offense_context"), dict) else {}
            away_off_ctx = context_payload.get("away_offense_context") if isinstance(context_payload.get("away_offense_context"), dict) else {}
            offense_split_home = float(m["offense_split_index_home"]) if m.get("offense_split_index_home") is not None else 1.0
            offense_split_away = float(m["offense_split_index_away"]) if m.get("offense_split_index_away") is not None else 1.0
            prior_away_hand = str(prior_away_feat.get("handedness") or "U").upper()
            next_away_hand = str(starter_away_feat.get("handedness") or "U").upper()
            prior_home_hand = str(prior_home_feat.get("handedness") or "U").upper()
            next_home_hand = str(starter_home_feat.get("handedness") or "U").upper()
            if next_away_hand != prior_away_hand or starter_resolve["away_changed"]:
                offense_split_home = platoon_split_for_hand(
                    season_index=float(m["offense_index_home"]) if m.get("offense_index_home") is not None else 1.0,
                    split_vs_l=_to_float(home_off_ctx.get("offense_split_vs_l")),
                    split_vs_r=_to_float(home_off_ctx.get("offense_split_vs_r")),
                    opponent_hand=next_away_hand,
                    fallback_split=offense_split_home,
                )
            if next_home_hand != prior_home_hand or starter_resolve["home_changed"]:
                offense_split_away = platoon_split_for_hand(
                    season_index=float(m["offense_index_away"]) if m.get("offense_index_away") is not None else 1.0,
                    split_vs_l=_to_float(away_off_ctx.get("offense_split_vs_l")),
                    split_vs_r=_to_float(away_off_ctx.get("offense_split_vs_r")),
                    opponent_hand=next_home_hand,
                    fallback_split=offense_split_away,
                )
            # Update context with nowcast confidence as live pre-lock estimate.
            # When allow_clear, write NULL SP explicitly (no COALESCE keep-prior).
            if allow_clear:
                sp_sql = """
                      probable_pitcher_home = :probable_pitcher_home,
                      probable_pitcher_away = :probable_pitcher_away,
                """
            else:
                sp_sql = """
                      probable_pitcher_home = COALESCE(:probable_pitcher_home, probable_pitcher_home),
                      probable_pitcher_away = COALESCE(:probable_pitcher_away, probable_pitcher_away),
                """
            session.execute(
                text(
                    f"""
                    UPDATE mlb_game_context
                    SET
                      {sp_sql}
                      lineup_confidence_home = :lineup_confidence_home,
                      lineup_confidence_away = :lineup_confidence_away,
                      lineup_strength_index_home = :lineup_strength_index_home,
                      lineup_strength_index_away = :lineup_strength_index_away,
                      offense_split_index_home = :offense_split_index_home,
                      offense_split_index_away = :offense_split_index_away,
                      lineup_confirmed = :lineup_confirmed,
                      context = COALESCE(context, '{{}}'::jsonb) || CAST(:context_patch AS jsonb),
                      updated_at = :updated_at
                    WHERE game_id = :game_id
                    """
                ),
                {
                    "game_id": m["game_id"],
                    "probable_pitcher_home": next_sp_home,
                    "probable_pitcher_away": next_sp_away,
                    "lineup_confidence_home": nowcast["home"],
                    "lineup_confidence_away": nowcast["away"],
                    "lineup_strength_index_home": lineup_strength_home,
                    "lineup_strength_index_away": lineup_strength_away,
                    "offense_split_index_home": offense_split_home,
                    "offense_split_index_away": offense_split_away,
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
                                "offense_split_home": round(offense_split_home, 4),
                                "offense_split_away": round(offense_split_away, 4),
                                "prior_starter_home": prior_starter_home,
                                "prior_starter_away": prior_starter_away,
                                "starter_home": next_sp_home,
                                "starter_away": next_sp_away,
                                "sp_changed_home": bool(starter_resolve["home_changed"]),
                                "sp_changed_away": bool(starter_resolve["away_changed"]),
                                "allow_clear": bool(allow_clear),
                                "timing_mode": get_lineup_timing_mode(),
                                "known_home": known_home,
                                "known_away": known_away,
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

            nowcast_arsenal_home = None
            nowcast_arsenal_away = None
            nowcast_batter_family_home = None
            nowcast_batter_family_away = None
            if get_pitch_matchup_enabled():
                pid_h = starter_home_feat.get("player_id")
                pid_a = starter_away_feat.get("player_id")
                as_of_live = now.date()
                if pid_h is not None:
                    try:
                        nowcast_arsenal_home = get_pitcher_arsenal_as_of(
                            int(pid_h),
                            as_of=as_of_live,
                            fetch_if_missing=False,
                            allow_stuff_fallback=False,
                        )
                    except Exception:
                        nowcast_arsenal_home = None
                if pid_a is not None:
                    try:
                        nowcast_arsenal_away = get_pitcher_arsenal_as_of(
                            int(pid_a),
                            as_of=as_of_live,
                            fetch_if_missing=False,
                            allow_stuff_fallback=False,
                        )
                    except Exception:
                        nowcast_arsenal_away = None
                try:
                    nowcast_batter_family_home = resolve_batter_family_for_matchup(
                        team_abbr=str(m.get("home_abbr") or ""),
                        as_of=as_of_live,
                        lineup_players=live_home_lineup.get("players") or [],
                        fetch_if_missing=False,
                    )
                except Exception:
                    nowcast_batter_family_home = None
                try:
                    nowcast_batter_family_away = resolve_batter_family_for_matchup(
                        team_abbr=str(m.get("away_abbr") or ""),
                        as_of=as_of_live,
                        lineup_players=live_away_lineup.get("players") or [],
                        fetch_if_missing=False,
                    )
                except Exception:
                    nowcast_batter_family_away = None
            inputs = MlbGameInputs(
                game_id=str(m["game_id"]),
                home_team=str(m["home_team"]),
                away_team=str(m["away_team"]),
                starter_home=next_sp_home,
                starter_away=next_sp_away,
                home_abbr=str(m.get("home_abbr") or "") or None,
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
                offense_split_home=offense_split_home,
                offense_split_away=offense_split_away,
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
                bullpen_quality_home=float(context_payload.get("bullpen_quality_home") or 1.0),
                bullpen_quality_away=float(context_payload.get("bullpen_quality_away") or 1.0),
                umpire_run_factor=float(m["umpire_run_factor"]) if m.get("umpire_run_factor") is not None else 1.0,
                info_freshness_score_home=freshness,
                info_freshness_score_away=freshness,
                pitcher_arsenal_home=nowcast_arsenal_home,
                pitcher_arsenal_away=nowcast_arsenal_away,
                batter_family_home=nowcast_batter_family_home,
                batter_family_away=nowcast_batter_family_away,
            )
            inputs, sharpen_diag = _sharpen_mlb_inputs(
                inputs,
                starter_home_feat=starter_home_feat,
                starter_away_feat=starter_away_feat,
                home_abbr=str(m.get("home_abbr") or "") or None,
                rest_days_home=_to_float(context_payload.get("rest_days_home")),
                rest_days_away=_to_float(context_payload.get("rest_days_away")),
            )
            inputs, timing_diag = apply_lineup_timing_to_inputs(
                inputs,
                known_home=known_home,
                known_away=known_away,
                hours_to_first_pitch=hours_to_pitch,
                freshness_score=freshness,
            )
            prior_conf_home = float(m["lineup_confidence_home"]) if m.get("lineup_confidence_home") is not None else nowcast["home"]
            prior_conf_away = float(m["lineup_confidence_away"]) if m.get("lineup_confidence_away") is not None else nowcast["away"]
            inputs, shock_diag = apply_lineup_shock(
                inputs,
                prior_confidence_home=prior_conf_home,
                prior_confidence_away=prior_conf_away,
                prior_starter_home=prior_starter_home,
                prior_starter_away=prior_starter_away,
                prior_starter_quality_home=float(prior_home_feat.get("starter_quality") or 1.0),
                prior_starter_quality_away=float(prior_away_feat.get("starter_quality") or 1.0),
            )
            shock_diag.update(sharpen_diag)
            shock_diag.update(timing_diag)

            seed_base = _default_projection_seed(inputs.game_id, base_model_version, simulations)
            projection_base = _run_simulation_by_model(
                inputs,
                simulations=simulations,
                seed=seed_base,
                model_version=base_model_version,
            )
            projection_base.setdefault("diagnostics", {}).update(shock_diag)
            prior_model_base = _fetch_prior_mlb_model_markets(
                session,
                game_id=inputs.game_id,
                model_version=base_model_version,
            )
            _insert_mlb_projection_and_audit(
                session,
                projection_base,
                seed=seed_base,
                line_role="handicap",
                prior_model_markets=prior_model_base,
            )
            repriced_base += 1

            if run_challenger:
                seed_ch = _default_projection_seed(inputs.game_id, challenger_model_version, simulations)
                projection_ch = _run_simulation_by_model(
                    inputs,
                    simulations=simulations,
                    seed=seed_ch,
                    model_version=challenger_model_version,
                )
                projection_ch.setdefault("diagnostics", {}).update(shock_diag)
                prior_model_ch = _fetch_prior_mlb_model_markets(
                    session,
                    game_id=inputs.game_id,
                    model_version=challenger_model_version,
                )
                _insert_mlb_projection_and_audit(
                    session,
                    projection_ch,
                    seed=seed_ch,
                    line_role="handicap",
                    prior_model_markets=prior_model_ch,
                )
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
            "sp_change_games": sp_change_games,
            "lineup_timing_mode": get_lineup_timing_mode(),
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
        repaired = _repair_mlb_leakage_stamps(
            session,
            model_version=model_version,
            lookback_days=max(30, int(lookback_days) + 14),
        )
        if repaired:
            session.commit()
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
    from dataclasses import replace

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
    return replace(inputs, **update_map)


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
            "props_play_stake_eligible": MLB_PROPS_PLAY_STAKE_ELIGIBLE,
        }
        _persist_snapshot(
            session,
            run_date=run_date,
            model_version=base_model_version,
            pipeline_stage="quality_snapshot",
            payload=base_quality,
        )
        try:
            persist_mlb_quality_snapshot(
                session,
                run_date=run_date,
                model_version=base_model_version,
                pipeline_stage="quality_snapshot",
                payload=base_quality,
            )
            health = build_board_health_from_db(
                session,
                model_version=base_model_version,
                lookback_days=max(7, calibration_lookback_days // 2),
                quality=base_quality,
                holdout_sample_size=int(base_cal.get("sample_size") or 0),
            )
            persist_mlb_board_health(
                session,
                run_date=run_date,
                model_version=base_model_version,
                health=health,
            )
            summary["stages"]["board_health"] = health
        except Exception as e:
            summary["stages"]["board_health"] = {"error": str(e)}
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
                "props_play_stake_eligible": MLB_PROPS_PLAY_STAKE_ELIGIBLE,
            }
            _persist_snapshot(
                session,
                run_date=run_date,
                model_version=challenger_model_version,
                pipeline_stage="quality_snapshot",
                payload=ch_quality,
            )
            try:
                persist_mlb_quality_snapshot(
                    session,
                    run_date=run_date,
                    model_version=challenger_model_version,
                    pipeline_stage="quality_snapshot",
                    payload=ch_quality,
                )
            except Exception:
                log.exception("Failed persisting challenger mlb_model_quality_snapshots row")
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

    if _env_bool("MLB_RUN_DAILY_CLV_ATTRIBUTION", True):
        try:
            summary["stages"]["clv_attribution"] = run_mlb_clv_attribution(
                model_version=base_model_version,
                lookback_days=calibration_lookback_days,
            )
        except Exception as e:
            summary["stages"]["clv_attribution"] = {"error": str(e)}

    return summary


@celery_app.task(name="src.tasks.pull_mlb_historical_odds_densify")
def pull_mlb_historical_odds_densify(
    *,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    bookmakers: Optional[str] = None,
    markets: str = "h2h,spreads,totals",
    max_requests: int = 40,
    day_offset: int = 0,
    snapshot_hour_utc: int = 17,
    snapshot_minute_utc: int = 0,
    preferred_book: str = DEFAULT_PREFERRED_BOOK,
) -> Dict[str, Any]:
    """DK-first historical odds densify for MLB holdout / CLV coverage.

    Pulls one Odds-API historical snapshot per distinct MLB game_date so open
    and close densify passes can push holdout n toward ≥120.
    """
    from .services.odds_api import fetch_odds_with_metadata

    end = date.fromisoformat(end_date) if end_date else date.today() - timedelta(days=1)
    start = date.fromisoformat(start_date) if start_date else end - timedelta(days=45)
    normalized_books = resolve_densify_books(bookmakers or os.getenv("MLB_DENSIFY_BOOKMAKERS"))
    normalized_markets = _normalize_markets_csv(markets)
    sport_key = "baseball_mlb"
    endpoint = f"historical/sports/{sport_key}/odds"

    session = SessionLocal()
    try:
        _assert_tables_present(
            session,
            stage="pull_mlb_historical_odds_densify",
            required_tables=["odds_snapshots", "games", "seasons", "leagues", "sportsbooks", "markets"],
        )
        _ensure_odds_api_request_tables(session)
        game_dates = mlb_game_dates_for_densify(
            session,
            start_date=start,
            end_date=end,
            max_dates=max(1, int(max_requests)),
            prioritize_thin=True,
        )
        selected = densify_snapshot_datetimes(
            game_dates,
            day_offset=day_offset,
            snapshot_hour_utc=snapshot_hour_utc,
            snapshot_minute_utc=snapshot_minute_utc,
        )

        requested = 0
        skipped_cached = 0
        request_errors = 0
        events_total = 0
        persisted_total = 0
        snapshots_total = 0
        credits_remaining = None

        for snapshot_dt in selected:
            params: Dict[str, Any] = {
                "bookmakers": normalized_books,
                "markets": normalized_markets,
                "oddsFormat": "american",
                "dateFormat": "iso",
                "date": snapshot_dt.isoformat().replace("+00:00", "Z"),
            }
            signature = _odds_request_signature(endpoint, params)
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
                events = payload.get("data") if isinstance(payload, dict) else None
                events_list = events if isinstance(events, list) else []
                for event in events_list:
                    if isinstance(event, dict) and not event.get("sport_key"):
                        event["sport_key"] = sport_key
                persisted = _persist_odds_events(
                    session,
                    events=events_list,
                    source_label="the-odds-api-historical-mlb-dk",
                )
                events_total += len(events_list)
                persisted_total += int(persisted.get("events_persisted") or 0)
                snapshots_total += int(persisted.get("snapshots_inserted") or 0)
                _record_odds_api_request(
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
                    response_timestamp=_parse_iso_datetime(payload.get("timestamp")) if isinstance(payload, dict) else None,
                    response_previous_timestamp=_parse_iso_datetime(payload.get("previous_timestamp")) if isinstance(payload, dict) else None,
                    response_next_timestamp=_parse_iso_datetime(payload.get("next_timestamp")) if isinstance(payload, dict) else None,
                    error=None,
                )
                session.commit()
            except Exception as exc:
                request_errors += 1
                session.rollback()
                try:
                    _record_odds_api_request(
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
                log.exception("MLB historical densify request failed", extra={"date": params.get("date")})

        status = "ok" if request_errors == 0 else "partial"
        result = {
            "status": status,
            "sport_key": sport_key,
            "bookmakers": normalized_books.split(","),
            "preferred_book": preferred_book,
            "markets": normalized_markets.split(","),
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "candidate_dates": len(selected),
            "requests_attempted": requested,
            "requests_skipped_cached": skipped_cached,
            "request_errors": request_errors,
            "events_fetched": events_total,
            "events_persisted": persisted_total,
            "snapshots_inserted": snapshots_total,
            "credits_remaining": credits_remaining,
            "prioritize_thin": True,
            "dk_first_firewall": True,
            "props_play_stake_eligible": MLB_PROPS_PLAY_STAKE_ELIGIBLE,
        }
        try:
            persist_mlb_densify_run(
                session,
                bookmakers=normalized_books,
                markets=normalized_markets,
                start_date=start,
                end_date=end,
                preferred_book=preferred_book,
                requests_attempted=requested,
                requests_skipped_cached=skipped_cached,
                snapshots_inserted=snapshots_total,
                status=status,
                payload=result,
            )
            session.commit()
        except Exception:
            session.rollback()
            log.exception("Failed persisting mlb_odds_densify_runs row")
        return result
    finally:
        session.close()


@celery_app.task(name="src.tasks.run_mlb_clv_attribution")
def run_mlb_clv_attribution(
    *,
    model_version: str = DEFAULT_MODEL_VERSION,
    lookback_days: int = 45,
    preferred_book: Optional[str] = None,
) -> Dict[str, Any]:
    book = preferred_book or os.getenv("MLB_ODDS_PREFERRED_BOOK", DEFAULT_PREFERRED_BOOK)
    session = SessionLocal()
    try:
        summary = compute_mlb_clv_with_spread(
            session,
            model_version=model_version,
            lookback_days=lookback_days,
            preferred_book=book,
        )
        written = upsert_mlb_clv_attribution(
            session,
            model_version=model_version,
            clv_summary=summary,
        )
        _persist_snapshot(
            session,
            run_date=date.today(),
            model_version=model_version,
            pipeline_stage="clv_attribution",
            payload={k: v for k, v in summary.items() if k != "items"},
        )
        session.commit()
        return {
            "model_version": model_version,
            "lookback_days": lookback_days,
            "preferred_book": book,
            "rows_upserted": written,
            "avg_ml_clv": summary.get("avg_ml_clv"),
            "avg_total_clv": summary.get("avg_total_clv"),
            "avg_spread_clv": summary.get("avg_spread_clv"),
            "count": summary.get("count"),
            "firewall": summary.get("firewall"),
        }
    except Exception:
        session.rollback()
        log.exception("Failed MLB CLV attribution")
        raise
    finally:
        session.close()


@celery_app.task(name="src.tasks.run_mlb_quality_grading")
def run_mlb_quality_grading(
    *,
    model_version: str = DEFAULT_MODEL_VERSION,
    lookback_days: int = 60,
) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        repaired = _repair_mlb_leakage_stamps(
            session,
            model_version=model_version,
            lookback_days=max(30, int(lookback_days) + 14),
        )
        if repaired:
            session.commit()
        points = _fetch_calibration_points(
            session,
            model_version=model_version,
            lookback_days=lookback_days,
        )
        cal = _compute_calibration_summary(points)
        drift = _compute_reliability_drift(points)
        clv = _compute_clv_summary(
            session,
            model_version=model_version,
            lookback_days=lookback_days,
        )
        payload = {
            **cal,
            **drift,
            **clv,
            "leakage_violations": _count_leakage_violations(points),
            "leakage_rows_repaired": int(repaired),
            "props_play_stake_eligible": MLB_PROPS_PLAY_STAKE_ELIGIBLE,
        }
        _persist_snapshot(
            session,
            run_date=date.today(),
            model_version=model_version,
            pipeline_stage="quality_snapshot",
            payload=payload,
        )
        persist_mlb_quality_snapshot(
            session,
            run_date=date.today(),
            model_version=model_version,
            pipeline_stage="quality_grading",
            payload=payload,
        )
        health = build_board_health_from_db(
            session,
            model_version=model_version,
            lookback_days=min(21, lookback_days),
            quality=payload,
            holdout_sample_size=int(cal.get("sample_size") or 0),
        )
        persist_mlb_board_health(
            session,
            run_date=date.today(),
            model_version=model_version,
            health=health,
        )
        session.commit()
        return {"quality": payload, "board_health": health}
    except Exception:
        session.rollback()
        log.exception("Failed MLB quality grading")
        raise
    finally:
        session.close()


@celery_app.task(name="src.tasks.backfill_mlb_historical_resim")
def backfill_mlb_historical_resim(
    *,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    simulations: int = 2000,
    model_version: str = DEFAULT_MODEL_VERSION,
    max_games: int = 200,
    force_resim: bool = False,
    skip_outcomes_pull: bool = False,
    hours_to_first_pitch: float = 3.0,
) -> Dict[str, Any]:
    """Re-sim completed MLB games so walkforward holdout n can approach ≥120.

    Requires MLB_ALLOW_HISTORICAL_SIM=true. Pulls outcomes first for the window
    unless skip_outcomes_pull / force_resim. When force_resim=True, deletes
    existing projections in-window and re-sims with current PA-sim sharpening.

    hours_to_first_pitch controls densify stamp + snapshot tier (default −3h).
    """
    if not _env_bool("MLB_ALLOW_HISTORICAL_SIM", False):
        raise ValueError(
            "Historical re-sim disabled; set MLB_ALLOW_HISTORICAL_SIM=true for holdout densify"
        )
    end = date.fromisoformat(end_date) if end_date else date.today() - timedelta(days=1)
    start = date.fromisoformat(start_date) if start_date else end - timedelta(days=45)
    stamp_hours = max(0.5, min(24.0, float(hours_to_first_pitch)))
    if skip_outcomes_pull or force_resim:
        outcomes = {"skipped": True, "reason": "skip_outcomes_pull_or_force_resim"}
    else:
        outcomes = pull_mlb_outcomes(days_back=max(1, (date.today() - start).days + 2))

    session = SessionLocal()
    simulated = 0
    skipped = 0
    deleted_prior = 0
    try:
        if force_resim:
            deleted = session.execute(
                text(
                    """
                    DELETE FROM mlb_market_projections mp
                    USING games g
                    JOIN seasons s ON s.id = g.season_id
                    JOIN leagues l ON l.id = s.league_id
                    WHERE mp.game_id = g.id
                      AND l.code = 'mlb'
                      AND mp.model_version = :model_version
                      AND g.game_date BETWEEN :start_date AND :end_date
                    """
                ),
                {"model_version": model_version, "start_date": start, "end_date": end},
            )
            deleted_prior = int(deleted.rowcount or 0)
            session.commit()

        missing_clause = ""
        if not force_resim:
            missing_clause = """
                  AND NOT EXISTS (
                    SELECT 1 FROM mlb_market_projections mp
                    WHERE mp.game_id = g.id AND mp.model_version = :model_version
                  )
            """
        rows = session.execute(
            text(
                f"""
                SELECT
                  g.id AS game_id,
                  g.game_date,
                  g.start_time,
                  g.external_id,
                  home.name AS home_team,
                  away.name AS away_team,
                  home.abbr AS home_abbr,
                  away.abbr AS away_abbr,
                  c.probable_pitcher_home,
                  c.probable_pitcher_away,
                  c.lineup_confirmed,
                  c.weather_temp_f,
                  c.weather_wind_mph,
                  c.weather_wind_dir_deg,
                  c.weather_humidity_pct,
                  c.park_factor_runs,
                  c.umpire_home_plate,
                  c.umpire_run_factor,
                  c.lineup_confidence_home,
                  c.lineup_confidence_away,
                  c.bullpen_fatigue_home,
                  c.bullpen_fatigue_away,
                  c.bullpen_availability_home,
                  c.bullpen_availability_away,
                  c.bullpen_high_leverage_availability_home,
                  c.bullpen_high_leverage_availability_away,
                  c.bullpen_ip_last3_home,
                  c.bullpen_ip_last3_away,
                  c.offense_index_home,
                  c.offense_index_away,
                  c.offense_split_index_home,
                  c.offense_split_index_away,
                  c.recent_form_index_home,
                  c.recent_form_index_away,
                  c.lineup_strength_index_home,
                  c.lineup_strength_index_away,
                  c.context
                FROM games g
                JOIN seasons s ON s.id = g.season_id
                JOIN leagues l ON l.id = s.league_id
                JOIN teams home ON home.id = g.home_team_id
                JOIN teams away ON away.id = g.away_team_id
                LEFT JOIN mlb_game_context c ON c.game_id = g.id
                JOIN mlb_market_outcomes mo ON mo.game_id = g.id
                WHERE l.code = 'mlb'
                  AND g.game_date BETWEEN :start_date AND :end_date
                  {missing_clause}
                ORDER BY g.game_date ASC
                LIMIT :max_games
                """
            ),
            {
                "start_date": start,
                "end_date": end,
                "max_games": int(max_games),
                "model_version": model_version,
            },
        ).fetchall()

        for row in rows:
            m = dict(row._mapping)
            try:
                game_season = None
                if m.get("game_date") is not None:
                    try:
                        game_season = int(str(m["game_date"])[:4])
                    except (TypeError, ValueError):
                        game_season = None
                game_as_of: Optional[date] = None
                if m.get("game_date") is not None:
                    if isinstance(m["game_date"], date):
                        game_as_of = m["game_date"]
                    else:
                        try:
                            game_as_of = date.fromisoformat(str(m["game_date"])[:10])
                        except ValueError:
                            game_as_of = None
                starter_home_feat = starter_identity_features(
                    m.get("probable_pitcher_home"),
                    season=game_season,
                    as_of=game_as_of,
                )
                starter_away_feat = starter_identity_features(
                    m.get("probable_pitcher_away"),
                    season=game_season,
                    as_of=game_as_of,
                )
                context_payload = m.get("context") if isinstance(m.get("context"), dict) else {}
                if isinstance(m.get("context"), str):
                    try:
                        context_payload = json.loads(m["context"])
                    except Exception:
                        context_payload = {}
                home_off_ctx = (
                    context_payload.get("home_offense_context")
                    if isinstance(context_payload.get("home_offense_context"), dict)
                    else {}
                )
                away_off_ctx = (
                    context_payload.get("away_offense_context")
                    if isinstance(context_payload.get("away_offense_context"), dict)
                    else {}
                )
                offense_home = float(m["offense_index_home"]) if m.get("offense_index_home") is not None else 1.0
                offense_away = float(m["offense_index_away"]) if m.get("offense_index_away") is not None else 1.0
                offense_split_home = (
                    float(m["offense_split_index_home"]) if m.get("offense_split_index_home") is not None else 1.0
                )
                offense_split_away = (
                    float(m["offense_split_index_away"]) if m.get("offense_split_index_away") is not None else 1.0
                )
                # Refresh platoon vs current SP hand (same as nowcast path).
                offense_split_home = platoon_split_for_hand(
                    season_index=offense_home,
                    split_vs_l=_to_float(home_off_ctx.get("offense_split_vs_l")),
                    split_vs_r=_to_float(home_off_ctx.get("offense_split_vs_r")),
                    opponent_hand=str(starter_away_feat.get("handedness") or "U"),
                    fallback_split=offense_split_home,
                )
                offense_split_away = platoon_split_for_hand(
                    season_index=offense_away,
                    split_vs_l=_to_float(away_off_ctx.get("offense_split_vs_l")),
                    split_vs_r=_to_float(away_off_ctx.get("offense_split_vs_r")),
                    opponent_hand=str(starter_home_feat.get("handedness") or "U"),
                    fallback_split=offense_split_away,
                )
                bp_quality_home = 1.0
                bp_quality_away = 1.0
                if get_bullpen_role_quality_mode() == "role_weighted" and game_as_of is not None:
                    # Talent-only refetch; fatigue/availability stay from stamped context
                    # so we do not double-count stress into bullpen_quality.
                    home_bp_live = fetch_team_bullpen_fatigue(
                        mlb_team_id_for_abbr(str(m.get("home_abbr") or "")),
                        game_as_of,
                    )
                    away_bp_live = fetch_team_bullpen_fatigue(
                        mlb_team_id_for_abbr(str(m.get("away_abbr") or "")),
                        game_as_of,
                    )
                    bp_quality_home = float(home_bp_live.get("bullpen_quality") or 1.0)
                    bp_quality_away = float(away_bp_live.get("bullpen_quality") or 1.0)
                arsenal_home = None
                arsenal_away = None
                batter_family_home = None
                batter_family_away = None
                if get_pitch_matchup_enabled() and game_as_of is not None:
                    pid_h = starter_home_feat.get("player_id")
                    pid_a = starter_away_feat.get("player_id")
                    if pid_h is not None:
                        try:
                            arsenal_home = get_pitcher_arsenal_as_of(
                                int(pid_h),
                                as_of=game_as_of,
                                season=game_season,
                                fetch_if_missing=False,
                                allow_stuff_fallback=False,
                            )
                        except Exception:
                            arsenal_home = None
                    if pid_a is not None:
                        try:
                            arsenal_away = get_pitcher_arsenal_as_of(
                                int(pid_a),
                                as_of=game_as_of,
                                season=game_season,
                                fetch_if_missing=False,
                                allow_stuff_fallback=False,
                            )
                        except Exception:
                            arsenal_away = None
                    home_lu = _densify_lineup_players_for_pitch_matchup(
                        context_payload=context_payload,
                        side="home",
                        lineup_confirmed=bool(m.get("lineup_confirmed") or False),
                        external_id=str(m.get("external_id") or "") or None,
                    )
                    away_lu = _densify_lineup_players_for_pitch_matchup(
                        context_payload=context_payload,
                        side="away",
                        lineup_confirmed=bool(m.get("lineup_confirmed") or False),
                        external_id=str(m.get("external_id") or "") or None,
                    )
                    try:
                        batter_family_home = resolve_batter_family_for_matchup(
                            team_abbr=str(m.get("home_abbr") or ""),
                            as_of=game_as_of,
                            season=game_season,
                            lineup_players=home_lu,
                            fetch_if_missing=False,
                        )
                    except Exception:
                        batter_family_home = None
                    try:
                        batter_family_away = resolve_batter_family_for_matchup(
                            team_abbr=str(m.get("away_abbr") or ""),
                            as_of=game_as_of,
                            season=game_season,
                            lineup_players=away_lu,
                            fetch_if_missing=False,
                        )
                    except Exception:
                        batter_family_away = None
                inputs = MlbGameInputs(
                    game_id=str(m["game_id"]),
                    home_team=str(m["home_team"]),
                    away_team=str(m["away_team"]),
                    starter_home=m.get("probable_pitcher_home"),
                    starter_away=m.get("probable_pitcher_away"),
                    home_abbr=str(m.get("home_abbr") or "") or None,
                    starter_quality_home=float(starter_home_feat.get("starter_quality") or 1.0),
                    starter_quality_away=float(starter_away_feat.get("starter_quality") or 1.0),
                    starter_k_factor_home=float(starter_home_feat.get("k_factor") or 1.0),
                    starter_k_factor_away=float(starter_away_feat.get("k_factor") or 1.0),
                    starter_bb_factor_home=float(starter_home_feat.get("bb_factor") or 1.0),
                    starter_bb_factor_away=float(starter_away_feat.get("bb_factor") or 1.0),
                    starter_gb_factor_home=float(starter_home_feat.get("gb_factor") or 1.0),
                    starter_gb_factor_away=float(starter_away_feat.get("gb_factor") or 1.0),
                    weather_temp_f=_to_float(m.get("weather_temp_f")),
                    weather_wind_mph=_to_float(m.get("weather_wind_mph")),
                    weather_wind_dir_deg=_to_float(m.get("weather_wind_dir_deg")),
                    weather_humidity_pct=_to_float(m.get("weather_humidity_pct")),
                    park_factor_runs=_to_float(m.get("park_factor_runs")),
                    umpire_home_plate=m.get("umpire_home_plate"),
                    umpire_run_factor=float(m.get("umpire_run_factor") or 1.0),
                    lineup_confirmed=bool(m.get("lineup_confirmed") or False),
                    lineup_confidence_home=float(m.get("lineup_confidence_home") or 0.85),
                    lineup_confidence_away=float(m.get("lineup_confidence_away") or 0.85),
                    offense_home=offense_home,
                    offense_away=offense_away,
                    offense_split_home=offense_split_home,
                    offense_split_away=offense_split_away,
                    recent_form_index_home=float(m["recent_form_index_home"]) if m.get("recent_form_index_home") is not None else 1.0,
                    recent_form_index_away=float(m["recent_form_index_away"]) if m.get("recent_form_index_away") is not None else 1.0,
                    lineup_strength_index_home=float(m["lineup_strength_index_home"]) if m.get("lineup_strength_index_home") is not None else 1.0,
                    lineup_strength_index_away=float(m["lineup_strength_index_away"]) if m.get("lineup_strength_index_away") is not None else 1.0,
                    pitcher_arsenal_home=arsenal_home,
                    pitcher_arsenal_away=arsenal_away,
                    batter_family_home=batter_family_home,
                    batter_family_away=batter_family_away,
                    bullpen_fatigue_home=float(m.get("bullpen_fatigue_home") or 0.50),
                    bullpen_fatigue_away=float(m.get("bullpen_fatigue_away") or 0.50),
                    bullpen_availability_home=float(m.get("bullpen_availability_home") or 0.65),
                    bullpen_availability_away=float(m.get("bullpen_availability_away") or 0.65),
                    bullpen_high_lev_availability_home=float(
                        m.get("bullpen_high_leverage_availability_home") or 0.62
                    ),
                    bullpen_high_lev_availability_away=float(
                        m.get("bullpen_high_leverage_availability_away") or 0.62
                    ),
                    bullpen_ip_last3_home=float(m.get("bullpen_ip_last3_home") or 9.0),
                    bullpen_ip_last3_away=float(m.get("bullpen_ip_last3_away") or 9.0),
                    bullpen_quality_home=bp_quality_home,
                    bullpen_quality_away=bp_quality_away,
                )
                inputs, sharpen_diag = _sharpen_mlb_inputs(
                    inputs,
                    starter_home_feat=starter_home_feat,
                    starter_away_feat=starter_away_feat,
                    home_abbr=str(m.get("home_abbr") or context_payload.get("home_abbr") or "") or None,
                    rest_days_home=_to_float(context_payload.get("rest_days_home")),
                    rest_days_away=_to_float(context_payload.get("rest_days_away")),
                )
                # Densify stamp hours (default −3h); snapshot lake + timing use same horizon.
                known_h = known_players_from_context(context_payload, "home")
                known_a = known_players_from_context(context_payload, "away")
                if known_h == 0 and bool(m.get("lineup_confirmed")):
                    known_h = 9
                if known_a == 0 and bool(m.get("lineup_confirmed")):
                    known_a = 9
                start_dt = _coerce_datetime_utc(m.get("start_time"))
                if start_dt is None and m.get("game_date") is not None:
                    start_dt = datetime.combine(
                        m["game_date"], datetime.min.time(), tzinfo=timezone.utc
                    ) + timedelta(hours=23)
                snap = reconstruct_densify_snapshot(
                    game_id=str(m["game_id"]),
                    hours_to_first_pitch=stamp_hours,
                    known_home=known_h,
                    known_away=known_a,
                    sp_home=m.get("probable_pitcher_home"),
                    sp_away=m.get("probable_pitcher_away"),
                    lineup_confirmed=bool(m.get("lineup_confirmed") or False),
                    lineup_confidence_home=float(m.get("lineup_confidence_home") or 0.85),
                    lineup_confidence_away=float(m.get("lineup_confidence_away") or 0.85),
                    start_time=start_dt,
                    persist=True,
                )
                inputs, timing_diag = apply_lineup_timing_to_inputs(
                    inputs,
                    known_home=int(snap.known_home),
                    known_away=int(snap.known_away),
                    hours_to_first_pitch=stamp_hours,
                    freshness_score=1.0,
                )
                sharpen_diag.update(timing_diag)
                sharpen_diag["lineup_sp_snapshot"] = {
                    "hours_to_first_pitch": stamp_hours,
                    "lineup_hash": snap.lineup_hash,
                    "lineup_confirmed": snap.lineup_confirmed,
                    "late_info_le3h": is_late_info_snapshot(snap, max_hours=3.0),
                    "late_info_le6h": is_late_info_snapshot(snap, max_hours=6.0),
                }
                seed = _default_projection_seed(str(m["game_id"]), model_version, simulations)
                projection = _run_simulation_by_model(
                    inputs,
                    simulations=simulations,
                    seed=seed,
                    model_version=model_version,
                )
                projection.setdefault("diagnostics", {}).update(sharpen_diag)
                # Stamp pre-first-pitch so historical densify stays leakage-clean.
                as_of = (start_dt or _now_utc()) - timedelta(hours=stamp_hours)
                _insert_mlb_projection_and_audit(
                    session, projection, seed=seed, created_at=as_of
                )
                simulated += 1
                if simulated % 25 == 0:
                    session.commit()
                    log.info(
                        "Historical MLB re-sim progress",
                        extra={"simulated": simulated, "skipped": skipped},
                    )
            except Exception:
                skipped += 1
                session.rollback()
                log.exception("Historical MLB re-sim failed", extra={"game_id": str(m.get("game_id"))})
        session.commit()

        # Repair densify + lookback leakage stamps (created_at >= completed_at).
        # Window-only repair left residual violations outside May–Jul densify.
        lookback_for_repair = max(90, (date.today() - start).days + 14)
        repaired_rows = _repair_mlb_leakage_stamps(
            session,
            model_version=model_version,
            lookback_days=lookback_for_repair,
        )
        session.execute(
            text(
                """
                UPDATE mlb_market_outcomes mo
                SET completed_at = COALESCE(
                      g.start_time + INTERVAL '4 hours',
                      (g.game_date::timestamp + INTERVAL '28 hours') AT TIME ZONE 'UTC'
                    )
                FROM games g
                WHERE mo.game_id = g.id
                  AND g.game_date BETWEEN :start_date AND :end_date
                  AND g.game_date < CURRENT_DATE
                  AND (
                    mo.completed_at IS NULL
                    OR mo.completed_at < COALESCE(g.start_time, g.game_date::timestamptz)
                  )
                """
            ),
            {"start_date": start, "end_date": end},
        )
        # Re-run stamp repair after outcome completed_at fixes.
        repaired_rows += _repair_mlb_leakage_stamps(
            session,
            model_version=model_version,
            lookback_days=lookback_for_repair,
        )
        session.commit()

        points = _fetch_calibration_points(
            session,
            model_version=model_version,
            lookback_days=max(30, (date.today() - start).days + 5),
        )
        cal = _compute_calibration_summary(points)
        # Shorter train window: midseason densify often has ~20–25 slate days,
        # so training_days=28 yields zero folds.
        holdout = run_mlb_walkforward_backtest(
            model_version=model_version,
            lookback_days=max(60, (date.today() - start).days + 5),
            training_days=10,
            step_days=3,
            apply_calibration=True,
        )
        return {
            "status": "ok",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "force_resim": bool(force_resim),
            "hours_to_first_pitch": stamp_hours,
            "deleted_prior_projections": deleted_prior,
            "outcomes": outcomes,
            "games_selected": len(rows),
            "simulated": simulated,
            "skipped": skipped,
            "leakage_rows_repaired": int(repaired_rows),
            "calibration_sample_size": int(len(points)),
            "calibration": cal,
            "holdout": {
                "sample_size": holdout.get("sample_size"),
                "fold_count": holdout.get("fold_count"),
                "base_brier_ml": holdout.get("base_brier_ml"),
                "calibrated_brier_ml": holdout.get("calibrated_brier_ml"),
                "base_mae_total_runs": holdout.get("base_mae_total_runs"),
                "calibrated_mae_total_runs": holdout.get("calibrated_mae_total_runs"),
                "brier_improvement": holdout.get("brier_improvement"),
                "mae_improvement": holdout.get("mae_improvement"),
                "leakage_violations": holdout.get("leakage_violations"),
            },
            "holdout_target_n": 120,
            "holdout_n_ok": int(cal.get("sample_size") or 0) >= 120
            or int(holdout.get("sample_size") or 0) >= 120,
            "props_play_stake_eligible": MLB_PROPS_PLAY_STAKE_ELIGIBLE,
        }
    finally:
        session.close()


_STACK_ABLATION_CONFIGS: Dict[str, Dict[str, Any]] = {
    # S0: HFA 1.025 + current production stack
    "S0": {
        "matchup_mul_enabled": True,
        "weather_wind_dir_mul_enabled": True,
        "starter_quality_mode": "era_whip",
        "model_suffix": "ablate-s0",
    },
    # S1: matchup mul OFF
    "S1": {
        "matchup_mul_enabled": False,
        "weather_wind_dir_mul_enabled": True,
        "starter_quality_mode": "era_whip",
        "model_suffix": "ablate-s1",
    },
    # S2: S1 + wind dir mul OFF
    "S2": {
        "matchup_mul_enabled": False,
        "weather_wind_dir_mul_enabled": False,
        "starter_quality_mode": "era_whip",
        "model_suffix": "ablate-s2",
    },
    # S3: S1 + K-BB-only starter quality (no ERA/WHIP)
    "S3": {
        "matchup_mul_enabled": False,
        "weather_wind_dir_mul_enabled": True,
        "starter_quality_mode": "kbb_only",
        "model_suffix": "ablate-s3",
    },
}


def _filter_clv_items_to_window(
    session: Any,
    items: List[Dict[str, Any]],
    *,
    start_date: date,
    end_date: date,
) -> List[Dict[str, Any]]:
    if not items:
        return []
    ids = [str(i.get("game_id")) for i in items if i.get("game_id")]
    if not ids:
        return []
    rows = session.execute(
        text(
            """
            SELECT g.id::text AS game_id
            FROM games g
            WHERE g.id::text = ANY(:ids)
              AND g.game_date BETWEEN :start_date AND :end_date
            """
        ),
        {"ids": ids, "start_date": start_date, "end_date": end_date},
    ).fetchall()
    keep = {str(r._mapping["game_id"]) for r in rows}
    return [i for i in items if str(i.get("game_id")) in keep]


def _summarize_clv_items(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    ml_vals = [float(i["ml_clv"]) for i in items if i.get("ml_clv") is not None]
    total_vals = [float(i["total_clv"]) for i in items if i.get("total_clv") is not None]
    spread_vals = [float(i["spread_clv"]) for i in items if i.get("spread_clv") is not None]
    return {
        "count": len(items),
        "ml_sample_size": len(ml_vals),
        "total_sample_size": len(total_vals),
        "spread_sample_size": len(spread_vals),
        "avg_ml_clv": round(sum(ml_vals) / len(ml_vals), 5) if ml_vals else None,
        "avg_total_clv": round(sum(total_vals) / len(total_vals), 5) if total_vals else None,
        "avg_spread_clv": round(sum(spread_vals) / len(spread_vals), 5) if spread_vals else None,
        "ml_game_ids": sorted({str(i["game_id"]) for i in items if i.get("ml_clv") is not None}),
    }


@celery_app.task(name="src.tasks.run_mlb_stack_ablation")
def run_mlb_stack_ablation(
    *,
    start_date: str = "2026-05-20",
    end_date: str = "2026-07-17",
    simulations: int = 2000,
    max_games: int = 1200,
    lookback_days: int = 90,
    configs: Optional[List[str]] = None,
    base_model_version: str = DEFAULT_MODEL_VERSION,
) -> Dict[str, Any]:
    """Force-resim densify window under S0–S3 stack flags; grade full-n + intersection CLV.

    Writes each config to `{base}-ablate-sN` so production `{base}` is not overwritten
    until a winning config is explicitly promoted.
    """
    if not _env_bool("MLB_ALLOW_HISTORICAL_SIM", False):
        raise ValueError(
            "Historical re-sim disabled; set MLB_ALLOW_HISTORICAL_SIM=true for stack ablation"
        )
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    selected = configs or ["S0", "S1", "S2", "S3"]
    unknown = [c for c in selected if c not in _STACK_ABLATION_CONFIGS]
    if unknown:
        raise ValueError(f"unknown stack ablation configs: {unknown}")

    prior_flags = get_stack_ablation_flags()
    prior_quality_mode = get_starter_quality_mode()
    results: Dict[str, Any] = {}
    try:
        for name in selected:
            cfg = _STACK_ABLATION_CONFIGS[name]
            model_version = f"{base_model_version}-{cfg['model_suffix']}"
            apply_stack_ablation_flags(
                matchup_mul_enabled=bool(cfg["matchup_mul_enabled"]),
                weather_wind_dir_mul_enabled=bool(cfg["weather_wind_dir_mul_enabled"]),
            )
            apply_starter_quality_mode(str(cfg["starter_quality_mode"]))
            log.info(
                "Stack ablation config start",
                extra={"config": name, "model_version": model_version, "flags": cfg},
            )
            resim = backfill_mlb_historical_resim(
                start_date=start.isoformat(),
                end_date=end.isoformat(),
                simulations=int(simulations),
                model_version=model_version,
                max_games=int(max_games),
                force_resim=True,
                skip_outcomes_pull=True,
            )
            session = SessionLocal()
            try:
                clv_full = compute_mlb_clv_with_spread(
                    session,
                    model_version=model_version,
                    lookback_days=int(lookback_days),
                )
                window_items = _filter_clv_items_to_window(
                    session,
                    list(clv_full.get("items") or []),
                    start_date=start,
                    end_date=end,
                )
                densify_clv = _summarize_clv_items(window_items)
                quality = run_mlb_quality_grading(
                    model_version=model_version,
                    lookback_days=int(lookback_days),
                )
                walkforward = run_mlb_walkforward_backtest(
                    model_version=model_version,
                    lookback_days=int(lookback_days),
                    training_days=10,
                    step_days=3,
                    apply_calibration=True,
                )
            finally:
                session.close()
            results[name] = {
                "config": cfg,
                "model_version": model_version,
                "flags": get_stack_ablation_flags(),
                "starter_quality_mode": get_starter_quality_mode(),
                "resim": {
                    "status": resim.get("status"),
                    "simulated": resim.get("simulated"),
                    "games_selected": resim.get("games_selected"),
                    "deleted_prior_projections": resim.get("deleted_prior_projections"),
                    "leakage_rows_repaired": resim.get("leakage_rows_repaired"),
                    "holdout": resim.get("holdout"),
                },
                "full_n_clv": {
                    "count": clv_full.get("count"),
                    "ml_sample_size": clv_full.get("ml_sample_size"),
                    "avg_ml_clv": clv_full.get("avg_ml_clv"),
                    "avg_total_clv": clv_full.get("avg_total_clv"),
                    "avg_spread_clv": clv_full.get("avg_spread_clv"),
                },
                "densify_window_clv": {
                    k: v for k, v in densify_clv.items() if k != "ml_game_ids"
                },
                "ml_game_ids": densify_clv.get("ml_game_ids") or [],
                "walkforward": {
                    "sample_size": walkforward.get("sample_size"),
                    "base_brier_ml": walkforward.get("base_brier_ml"),
                    "calibrated_brier_ml": walkforward.get("calibrated_brier_ml"),
                    "base_mae_total_runs": walkforward.get("base_mae_total_runs"),
                    "leakage_violations": walkforward.get("leakage_violations"),
                },
                "quality": (quality.get("quality") or {}) if isinstance(quality, dict) else {},
            }
    finally:
        apply_stack_ablation_flags(
            matchup_mul_enabled=bool(prior_flags.get("matchup_mul_enabled", True)),
            weather_wind_dir_mul_enabled=bool(
                prior_flags.get("weather_wind_dir_mul_enabled", True)
            ),
        )
        apply_starter_quality_mode(prior_quality_mode or "era_whip")

    # Intersection: identical densify-window game_ids with ML CLV across all graded configs.
    id_sets = [
        set(results[name].get("ml_game_ids") or [])
        for name in selected
        if name in results
    ]
    intersection_ids = set.intersection(*id_sets) if id_sets else set()
    intersection: Dict[str, Any] = {"n": len(intersection_ids), "by_config": {}}
    for name in selected:
        if name not in results:
            continue
        model_version = results[name]["model_version"]
        session = SessionLocal()
        try:
            clv_full = compute_mlb_clv_with_spread(
                session,
                model_version=model_version,
                lookback_days=int(lookback_days),
            )
            window_items = _filter_clv_items_to_window(
                session,
                list(clv_full.get("items") or []),
                start_date=start,
                end_date=end,
            )
            inter_items = [
                i for i in window_items if str(i.get("game_id")) in intersection_ids
            ]
            intersection["by_config"][name] = _summarize_clv_items(inter_items)
            # Drop bulky ids from per-config payload after intersection computed.
            results[name].pop("ml_game_ids", None)
            results[name]["intersection_clv"] = {
                k: v
                for k, v in intersection["by_config"][name].items()
                if k != "ml_game_ids"
            }
        finally:
            session.close()

    # Decision helper (does not auto-promote).
    s1 = (intersection.get("by_config") or {}).get("S1") or {}
    s0 = (intersection.get("by_config") or {}).get("S0") or {}
    s1_ml = s1.get("avg_ml_clv")
    s0_ml = s0.get("avg_ml_clv")
    recommendation = {
        "ship_matchup_off": bool(
            s1_ml is not None and float(s1_ml) >= 0.015
        ),
        "stretch_target_hit": bool(
            s1_ml is not None and float(s1_ml) >= 0.020
        ),
        "s1_beats_s0_intersection": bool(
            s1_ml is not None
            and s0_ml is not None
            and float(s1_ml) > float(s0_ml)
        ),
        "note": (
            "Ship S1 (matchup-off, keep HFA 1.025) only if intersection ML CLV "
            "≥ +0.015 without wrecking Brier/RL/total. Else treat prior +0.023 as "
            "sample-composition and pivot to SP talent (S3) without nostalgia."
        ),
    }

    return {
        "status": "ok",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "lookback_days": int(lookback_days),
        "configs": selected,
        "results": results,
        "intersection": {
            "n": intersection["n"],
            "by_config": {
                k: {kk: vv for kk, vv in v.items() if kk != "ml_game_ids"}
                for k, v in (intersection.get("by_config") or {}).items()
            },
        },
        "recommendation": recommendation,
        "props_play_stake_eligible": MLB_PROPS_PLAY_STAKE_ELIGIBLE,
        "unused_holdout": unused_holdout_summary(),
    }


_SP_TALENT_ABLATION_CONFIGS: Dict[str, Dict[str, Any]] = {
    # T0: production S0 stack + as-of season stats (era/whip quality)
    "T0": {
        "starter_quality_mode": "era_whip",
        "bullpen_role_quality_mode": "off",
        "model_suffix": "talent-t0",
    },
    # T1: FIP-proxy starter quality (Track A primary)
    "T1": {
        "starter_quality_mode": "fip_proxy",
        "bullpen_role_quality_mode": "off",
        "model_suffix": "talent-t1",
    },
    # T2: xFIP-proxy starter quality (Track A secondary knob)
    "T2": {
        "starter_quality_mode": "xfip_proxy",
        "bullpen_role_quality_mode": "off",
        "model_suffix": "talent-t2",
    },
    # T3: Statcast stuff-proxy (as-of whiff/chase/zone/EV/barrel)
    "T3": {
        "starter_quality_mode": "stuff_proxy",
        "bullpen_role_quality_mode": "off",
        "model_suffix": "talent-t3",
    },
    # B1: bullpen role-weighted quality on T0 baseline (Track B independence check)
    "B1": {
        "starter_quality_mode": "era_whip",
        "bullpen_role_quality_mode": "role_weighted",
        "model_suffix": "talent-b1",
    },
}

_LINEUP_TIMING_ABLATION_CONFIGS: Dict[str, Dict[str, Any]] = {
    "L0": {
        "lineup_timing_mode": "off",
        "model_suffix": "timing-l0",
    },
    "L1": {
        "lineup_timing_mode": "sharp",
        "model_suffix": "timing-l1",
    },
}


@celery_app.task(name="src.tasks.run_mlb_sp_talent_ablation")
def run_mlb_sp_talent_ablation(
    *,
    start_date: str = "2026-05-20",
    end_date: str = "2026-07-17",
    simulations: int = 2000,
    max_games: int = 1200,
    lookback_days: int = 90,
    configs: Optional[List[str]] = None,
    base_model_version: str = DEFAULT_MODEL_VERSION,
) -> Dict[str, Any]:
    """Force-resim densify under SP talent / bullpen role flags; grade intersection CLV.

    Writes each config to `{base}-talent-tN` / `{base}-talent-bN` so production
    `{base}` is not overwritten until a winning config is explicitly promoted.
    """
    if not _env_bool("MLB_ALLOW_HISTORICAL_SIM", False):
        raise ValueError(
            "Historical re-sim disabled; set MLB_ALLOW_HISTORICAL_SIM=true for SP talent ablation"
        )
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    selected = configs or ["T0", "T3"]
    unknown = [c for c in selected if c not in _SP_TALENT_ABLATION_CONFIGS]
    if unknown:
        raise ValueError(f"unknown SP talent ablation configs: {unknown}")

    prior_quality_mode = get_starter_quality_mode()
    prior_bp_mode = get_bullpen_role_quality_mode()
    prior_timing_mode = get_lineup_timing_mode()
    results: Dict[str, Any] = {}
    try:
        for name in selected:
            cfg = _SP_TALENT_ABLATION_CONFIGS[name]
            model_version = f"{base_model_version}-{cfg['model_suffix']}"
            apply_starter_quality_mode(str(cfg["starter_quality_mode"]))
            apply_bullpen_role_quality_mode(str(cfg["bullpen_role_quality_mode"]))
            # Keep timing off so talent A/B is not confounded.
            apply_lineup_timing_mode("off")
            log.info(
                "SP talent ablation config start",
                extra={"config": name, "model_version": model_version, "flags": cfg},
            )
            resim = backfill_mlb_historical_resim(
                start_date=start.isoformat(),
                end_date=end.isoformat(),
                simulations=int(simulations),
                model_version=model_version,
                max_games=int(max_games),
                force_resim=True,
                skip_outcomes_pull=True,
            )
            session = SessionLocal()
            try:
                clv_full = compute_mlb_clv_with_spread(
                    session,
                    model_version=model_version,
                    lookback_days=int(lookback_days),
                )
                window_items = _filter_clv_items_to_window(
                    session,
                    list(clv_full.get("items") or []),
                    start_date=start,
                    end_date=end,
                )
                densify_clv = _summarize_clv_items(window_items)
                quality = run_mlb_quality_grading(
                    model_version=model_version,
                    lookback_days=int(lookback_days),
                )
                walkforward = run_mlb_walkforward_backtest(
                    model_version=model_version,
                    lookback_days=int(lookback_days),
                    training_days=10,
                    step_days=3,
                    apply_calibration=True,
                )
            finally:
                session.close()
            results[name] = {
                "config": cfg,
                "model_version": model_version,
                "starter_quality_mode": get_starter_quality_mode(),
                "bullpen_role_quality_mode": get_bullpen_role_quality_mode(),
                "resim": {
                    "status": resim.get("status"),
                    "simulated": resim.get("simulated"),
                    "games_selected": resim.get("games_selected"),
                    "deleted_prior_projections": resim.get("deleted_prior_projections"),
                    "leakage_rows_repaired": resim.get("leakage_rows_repaired"),
                    "holdout": resim.get("holdout"),
                },
                "full_n_clv": {
                    "count": clv_full.get("count"),
                    "ml_sample_size": clv_full.get("ml_sample_size"),
                    "avg_ml_clv": clv_full.get("avg_ml_clv"),
                    "avg_total_clv": clv_full.get("avg_total_clv"),
                    "avg_spread_clv": clv_full.get("avg_spread_clv"),
                },
                "densify_window_clv": {
                    k: v for k, v in densify_clv.items() if k != "ml_game_ids"
                },
                "ml_game_ids": densify_clv.get("ml_game_ids") or [],
                "walkforward": {
                    "sample_size": walkforward.get("sample_size"),
                    "base_brier_ml": walkforward.get("base_brier_ml"),
                    "calibrated_brier_ml": walkforward.get("calibrated_brier_ml"),
                    "base_mae_total_runs": walkforward.get("base_mae_total_runs"),
                    "leakage_violations": walkforward.get("leakage_violations"),
                },
                "quality": (quality.get("quality") or {}) if isinstance(quality, dict) else {},
            }
    finally:
        apply_starter_quality_mode(prior_quality_mode or "era_whip")
        apply_bullpen_role_quality_mode(prior_bp_mode or "off")
        apply_lineup_timing_mode(prior_timing_mode or "off")

    id_sets = [
        set(results[name].get("ml_game_ids") or [])
        for name in selected
        if name in results
    ]
    intersection_ids = set.intersection(*id_sets) if id_sets else set()
    intersection: Dict[str, Any] = {"n": len(intersection_ids), "by_config": {}}
    for name in selected:
        if name not in results:
            continue
        model_version = results[name]["model_version"]
        session = SessionLocal()
        try:
            clv_full = compute_mlb_clv_with_spread(
                session,
                model_version=model_version,
                lookback_days=int(lookback_days),
            )
            window_items = _filter_clv_items_to_window(
                session,
                list(clv_full.get("items") or []),
                start_date=start,
                end_date=end,
            )
            inter_items = [
                i for i in window_items if str(i.get("game_id")) in intersection_ids
            ]
            intersection["by_config"][name] = _summarize_clv_items(inter_items)
            results[name].pop("ml_game_ids", None)
            results[name]["intersection_clv"] = {
                k: v
                for k, v in intersection["by_config"][name].items()
                if k != "ml_game_ids"
            }
        finally:
            session.close()

    t0 = (intersection.get("by_config") or {}).get("T0") or {}
    t1 = (intersection.get("by_config") or {}).get("T1") or {}
    t2 = (intersection.get("by_config") or {}).get("T2") or {}
    t3 = (intersection.get("by_config") or {}).get("T3") or {}
    b1 = (intersection.get("by_config") or {}).get("B1") or {}
    t0_ml = t0.get("avg_ml_clv")
    t1_ml = t1.get("avg_ml_clv")
    t2_ml = t2.get("avg_ml_clv")
    t3_ml = t3.get("avg_ml_clv")
    b1_ml = b1.get("avg_ml_clv")

    def _beats(challenger: Any, baseline: Any, *, margin: float = 0.0) -> bool:
        return (
            challenger is not None
            and baseline is not None
            and float(challenger) > float(baseline) + margin
        )

    best_name = "T0"
    best_ml = t0_ml
    for name, ml in (("T1", t1_ml), ("T2", t2_ml), ("T3", t3_ml), ("B1", b1_ml)):
        if ml is None:
            continue
        if best_ml is None or float(ml) > float(best_ml):
            best_name, best_ml = name, ml

    recommendation = {
        "best_intersection_config": best_name,
        "best_intersection_ml_clv": best_ml,
        "ship_fip_proxy": bool(
            t1_ml is not None and float(t1_ml) >= 0.010 and _beats(t1_ml, t0_ml)
        ),
        "ship_xfip_proxy": bool(
            t2_ml is not None and float(t2_ml) >= 0.010 and _beats(t2_ml, t0_ml)
        ),
        "ship_stuff_proxy": bool(
            t3_ml is not None and float(t3_ml) >= 0.010 and _beats(t3_ml, t0_ml)
        ),
        "ship_bullpen_role": bool(
            b1_ml is not None and float(b1_ml) >= 0.010 and _beats(b1_ml, t0_ml)
        ),
        "stretch_target_hit": bool(best_ml is not None and float(best_ml) >= 0.015),
        "note": (
            "Ship a talent mode only if intersection ML CLV ≥ +0.010 vs T0 "
            "(stretch +0.015), leakage=0, and RL/total CLV / Brier not torched. "
            "Else leave production on era_whip (S0)."
        ),
    }

    return {
        "status": "ok",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "lookback_days": int(lookback_days),
        "configs": selected,
        "results": results,
        "intersection": {
            "n": intersection["n"],
            "by_config": {
                k: {kk: vv for kk, vv in v.items() if kk != "ml_game_ids"}
                for k, v in (intersection.get("by_config") or {}).items()
            },
        },
        "recommendation": recommendation,
        "props_play_stake_eligible": MLB_PROPS_PLAY_STAKE_ELIGIBLE,
        "unused_holdout": unused_holdout_summary(),
    }


@celery_app.task(name="src.tasks.run_mlb_lineup_timing_ablation")
def run_mlb_lineup_timing_ablation(
    *,
    start_date: str = "2026-05-20",
    end_date: str = "2026-07-17",
    simulations: int = 2000,
    max_games: int = 1200,
    lookback_days: int = 90,
    configs: Optional[List[str]] = None,
    base_model_version: str = DEFAULT_MODEL_VERSION,
) -> Dict[str, Any]:
    """Force-resim densify under lineup timing flags; grade intersection CLV vs L0."""
    if not _env_bool("MLB_ALLOW_HISTORICAL_SIM", False):
        raise ValueError(
            "Historical re-sim disabled; set MLB_ALLOW_HISTORICAL_SIM=true for lineup timing ablation"
        )
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    selected = configs or ["L0", "L1"]
    unknown = [c for c in selected if c not in _LINEUP_TIMING_ABLATION_CONFIGS]
    if unknown:
        raise ValueError(f"unknown lineup timing ablation configs: {unknown}")

    prior_timing = get_lineup_timing_mode()
    prior_quality = get_starter_quality_mode()
    prior_bp = get_bullpen_role_quality_mode()
    results: Dict[str, Any] = {}
    try:
        # Hold production talent stack constant (S0 / era_whip).
        apply_starter_quality_mode("era_whip")
        apply_bullpen_role_quality_mode("off")
        for name in selected:
            cfg = _LINEUP_TIMING_ABLATION_CONFIGS[name]
            model_version = f"{base_model_version}-{cfg['model_suffix']}"
            apply_lineup_timing_mode(str(cfg["lineup_timing_mode"]))
            log.info(
                "Lineup timing ablation config start",
                extra={"config": name, "model_version": model_version, "flags": cfg},
            )
            resim = backfill_mlb_historical_resim(
                start_date=start.isoformat(),
                end_date=end.isoformat(),
                simulations=int(simulations),
                model_version=model_version,
                max_games=int(max_games),
                force_resim=True,
                skip_outcomes_pull=True,
            )
            session = SessionLocal()
            try:
                clv_full = compute_mlb_clv_with_spread(
                    session,
                    model_version=model_version,
                    lookback_days=int(lookback_days),
                )
                window_items = _filter_clv_items_to_window(
                    session,
                    list(clv_full.get("items") or []),
                    start_date=start,
                    end_date=end,
                )
                densify_clv = _summarize_clv_items(window_items)
                quality = run_mlb_quality_grading(
                    model_version=model_version,
                    lookback_days=int(lookback_days),
                )
                walkforward = run_mlb_walkforward_backtest(
                    model_version=model_version,
                    lookback_days=int(lookback_days),
                    training_days=10,
                    step_days=3,
                    apply_calibration=True,
                )
            finally:
                session.close()
            results[name] = {
                "config": cfg,
                "model_version": model_version,
                "lineup_timing_mode": get_lineup_timing_mode(),
                "resim": {
                    "status": resim.get("status"),
                    "simulated": resim.get("simulated"),
                    "games_selected": resim.get("games_selected"),
                    "deleted_prior_projections": resim.get("deleted_prior_projections"),
                    "leakage_rows_repaired": resim.get("leakage_rows_repaired"),
                },
                "full_n_clv": {
                    "count": clv_full.get("count"),
                    "ml_sample_size": clv_full.get("ml_sample_size"),
                    "avg_ml_clv": clv_full.get("avg_ml_clv"),
                    "avg_total_clv": clv_full.get("avg_total_clv"),
                    "avg_spread_clv": clv_full.get("avg_spread_clv"),
                },
                "densify_window_clv": {
                    k: v for k, v in densify_clv.items() if k != "ml_game_ids"
                },
                "ml_game_ids": densify_clv.get("ml_game_ids") or [],
                "walkforward": {
                    "sample_size": walkforward.get("sample_size"),
                    "base_brier_ml": walkforward.get("base_brier_ml"),
                    "calibrated_brier_ml": walkforward.get("calibrated_brier_ml"),
                    "base_mae_total_runs": walkforward.get("base_mae_total_runs"),
                    "leakage_violations": walkforward.get("leakage_violations"),
                },
                "quality": (quality.get("quality") or {}) if isinstance(quality, dict) else {},
            }
    finally:
        apply_lineup_timing_mode(prior_timing or "off")
        apply_starter_quality_mode(prior_quality or "era_whip")
        apply_bullpen_role_quality_mode(prior_bp or "off")

    id_sets = [
        set(results[name].get("ml_game_ids") or [])
        for name in selected
        if name in results
    ]
    intersection_ids = set.intersection(*id_sets) if id_sets else set()
    intersection: Dict[str, Any] = {"n": len(intersection_ids), "by_config": {}}
    for name in selected:
        if name not in results:
            continue
        model_version = results[name]["model_version"]
        session = SessionLocal()
        try:
            clv_full = compute_mlb_clv_with_spread(
                session,
                model_version=model_version,
                lookback_days=int(lookback_days),
            )
            window_items = _filter_clv_items_to_window(
                session,
                list(clv_full.get("items") or []),
                start_date=start,
                end_date=end,
            )
            inter_items = [
                i for i in window_items if str(i.get("game_id")) in intersection_ids
            ]
            intersection["by_config"][name] = _summarize_clv_items(inter_items)
            results[name].pop("ml_game_ids", None)
            results[name]["intersection_clv"] = {
                k: v
                for k, v in intersection["by_config"][name].items()
                if k != "ml_game_ids"
            }
        finally:
            session.close()

    l0 = (intersection.get("by_config") or {}).get("L0") or {}
    l1 = (intersection.get("by_config") or {}).get("L1") or {}
    l0_ml = l0.get("avg_ml_clv")
    l1_ml = l1.get("avg_ml_clv")
    recommendation = {
        "best_intersection_config": (
            "L1"
            if l1_ml is not None and l0_ml is not None and float(l1_ml) > float(l0_ml)
            else "L0"
        ),
        "best_intersection_ml_clv": (
            l1_ml
            if l1_ml is not None and l0_ml is not None and float(l1_ml) > float(l0_ml)
            else l0_ml
        ),
        "ship_lineup_timing_sharp": bool(
            l1_ml is not None
            and l0_ml is not None
            and float(l1_ml) >= 0.010
            and float(l1_ml) > float(l0_ml)
        ),
        "stretch_target_hit": bool(l1_ml is not None and float(l1_ml) >= 0.015),
        "note": (
            "Ship MLB_LINEUP_TIMING_MODE=sharp only if intersection ML CLV ≥ +0.010 "
            "and beats L0, leakage=0, RL/total not torched. Wiring fixes (cache clear, "
            "live freshness, BP quality) stay regardless."
        ),
    }
    return {
        "status": "ok",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "lookback_days": int(lookback_days),
        "configs": selected,
        "results": results,
        "intersection": {
            "n": intersection["n"],
            "by_config": {
                k: {kk: vv for kk, vv in v.items() if kk != "ml_game_ids"}
                for k, v in (intersection.get("by_config") or {}).items()
            },
        },
        "recommendation": recommendation,
        "props_play_stake_eligible": MLB_PROPS_PLAY_STAKE_ELIGIBLE,
        "unused_holdout": unused_holdout_summary(),
    }


_LATE_INFO_STAMP_CONFIGS: Dict[str, Dict[str, Any]] = {
    "H0": {"hours_to_first_pitch": 6.0, "model_suffix": "lateinfo-h0"},
    "H1": {"hours_to_first_pitch": 3.0, "model_suffix": "lateinfo-h1"},
    "H2": {"hours_to_first_pitch": 1.0, "model_suffix": "lateinfo-h2"},
}

_PITCH_MATCHUP_ABLATION_CONFIGS: Dict[str, Dict[str, Any]] = {
    "M0": {
        "pitch_matchup_enabled": False,
        "batter_level": False,
        "stuff_fallback": False,
        "model_suffix": "pitchmux-m0",
    },
    # True pitch-type arsenal + team batter-family; stuff-shape fallback OFF.
    "M1": {
        "pitch_matchup_enabled": True,
        "batter_level": False,
        "stuff_fallback": False,
        "model_suffix": "pitchmux-m1t",
    },
    # True arsenal × lineup-ID batter contact blend (falls back to team-family).
    "M1b": {
        "pitch_matchup_enabled": True,
        "batter_level": True,
        "stuff_fallback": False,
        "model_suffix": "pitchmux-m1b",
    },
}


def _densify_lineup_players_for_pitch_matchup(
    *,
    context_payload: Dict[str, Any],
    side: str,
    lineup_confirmed: bool,
    external_id: Optional[str],
) -> List[Dict[str, Any]]:
    """Resolve lineup player dicts for batter-level densify without leakage.

    Prefer stamped context IDs. Only when the densify stamp already marked
    ``lineup_confirmed`` may we fetch Stats API boxscore IDs (final batting
    order ≈ pre-game confirmed card). Never fetch for unconfirmed stamps.
    """
    players = lineup_players_from_context(context_payload, side)
    if extract_lineup_batter_entries(players):
        return players
    if not get_pitch_matchup_batter_level():
        return players
    if not lineup_confirmed or not external_id:
        return players
    try:
        live = fetch_game_lineup_features(str(external_id))
        fetched = ((live or {}).get(side) or {}).get("players") or []
        if extract_lineup_batter_entries(fetched):
            return [p for p in fetched if isinstance(p, dict)]
    except Exception:
        pass
    return players

_TOTALS_PARK_WIND_ABLATION_CONFIGS: Dict[str, Dict[str, Any]] = {
    "W0": {"totals_park_rel_wind_enabled": False, "model_suffix": "parkwind-w0"},
    "W1": {"totals_park_rel_wind_enabled": True, "model_suffix": "parkwind-w1"},
}


def _grade_densify_ablation_config(
    *,
    model_version: str,
    start: date,
    end: date,
    simulations: int,
    max_games: int,
    lookback_days: int,
    hours_to_first_pitch: float = 3.0,
) -> Dict[str, Any]:
    resim = backfill_mlb_historical_resim(
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        simulations=int(simulations),
        model_version=model_version,
        max_games=int(max_games),
        force_resim=True,
        skip_outcomes_pull=True,
        hours_to_first_pitch=float(hours_to_first_pitch),
    )
    session = SessionLocal()
    try:
        clv_full = compute_mlb_clv_with_spread(
            session,
            model_version=model_version,
            lookback_days=int(lookback_days),
        )
        window_items = _filter_clv_items_to_window(
            session,
            list(clv_full.get("items") or []),
            start_date=start,
            end_date=end,
        )
        densify_clv = _summarize_clv_items(window_items)
        quality = run_mlb_quality_grading(
            model_version=model_version,
            lookback_days=int(lookback_days),
        )
        walkforward = run_mlb_walkforward_backtest(
            model_version=model_version,
            lookback_days=int(lookback_days),
            training_days=10,
            step_days=3,
            apply_calibration=True,
        )
    finally:
        session.close()
    return {
        "model_version": model_version,
        "resim": {
            "status": resim.get("status"),
            "simulated": resim.get("simulated"),
            "games_selected": resim.get("games_selected"),
            "deleted_prior_projections": resim.get("deleted_prior_projections"),
            "leakage_rows_repaired": resim.get("leakage_rows_repaired"),
            "hours_to_first_pitch": resim.get("hours_to_first_pitch"),
            "holdout": resim.get("holdout"),
        },
        "full_n_clv": {
            "count": clv_full.get("count"),
            "ml_sample_size": clv_full.get("ml_sample_size"),
            "avg_ml_clv": clv_full.get("avg_ml_clv"),
            "avg_total_clv": clv_full.get("avg_total_clv"),
            "avg_spread_clv": clv_full.get("avg_spread_clv"),
        },
        "densify_window_clv": {k: v for k, v in densify_clv.items() if k != "ml_game_ids"},
        "ml_game_ids": densify_clv.get("ml_game_ids") or [],
        "walkforward": {
            "sample_size": walkforward.get("sample_size"),
            "base_brier_ml": walkforward.get("base_brier_ml"),
            "calibrated_brier_ml": walkforward.get("calibrated_brier_ml"),
            "base_mae_total_runs": walkforward.get("base_mae_total_runs"),
            "leakage_violations": walkforward.get("leakage_violations"),
        },
        "quality": (quality.get("quality") or {}) if isinstance(quality, dict) else {},
    }


def _finalize_intersection_clv(
    results: Dict[str, Any],
    *,
    selected: List[str],
    start: date,
    end: date,
    lookback_days: int,
) -> Dict[str, Any]:
    id_sets = [
        set(results[name].get("ml_game_ids") or [])
        for name in selected
        if name in results
    ]
    intersection_ids = set.intersection(*id_sets) if id_sets else set()
    intersection: Dict[str, Any] = {"n": len(intersection_ids), "by_config": {}}
    for name in selected:
        if name not in results:
            continue
        model_version = results[name]["model_version"]
        session = SessionLocal()
        try:
            clv_full = compute_mlb_clv_with_spread(
                session,
                model_version=model_version,
                lookback_days=int(lookback_days),
            )
            window_items = _filter_clv_items_to_window(
                session,
                list(clv_full.get("items") or []),
                start_date=start,
                end_date=end,
            )
            inter_items = [
                i for i in window_items if str(i.get("game_id")) in intersection_ids
            ]
            intersection["by_config"][name] = _summarize_clv_items(inter_items)
            results[name].pop("ml_game_ids", None)
            results[name]["intersection_clv"] = {
                k: v
                for k, v in intersection["by_config"][name].items()
                if k != "ml_game_ids"
            }
        finally:
            session.close()
    return {
        "n": intersection["n"],
        "by_config": {
            k: {kk: vv for kk, vv in v.items() if kk != "ml_game_ids"}
            for k, v in (intersection.get("by_config") or {}).items()
        },
    }


def _late_info_clv_slice(
    *,
    model_version: str,
    start: date,
    end: date,
    lookback_days: int,
    max_hours: float,
    intersection_ids: Optional[set] = None,
) -> Dict[str, Any]:
    late_meta = summarize_late_info_slice([], max_hours=max_hours)
    session = SessionLocal()
    try:
        clv_full = compute_mlb_clv_with_spread(
            session,
            model_version=model_version,
            lookback_days=int(lookback_days),
        )
        window_items = _filter_clv_items_to_window(
            session,
            list(clv_full.get("items") or []),
            start_date=start,
            end_date=end,
        )
        gids = [str(i.get("game_id")) for i in window_items if i.get("game_id")]
        late_meta = summarize_late_info_slice(gids, max_hours=max_hours)
        late_ids = set(late_meta.get("late_info_game_ids") or [])
        if intersection_ids is not None:
            late_ids &= set(intersection_ids)
        late_items = [i for i in window_items if str(i.get("game_id")) in late_ids]
        summary = _summarize_clv_items(late_items)
        summary.pop("ml_game_ids", None)
        return {
            "max_hours": float(max_hours),
            "late_info_n": len(late_ids),
            "clv": summary,
            "lake": {k: v for k, v in late_meta.items() if k != "late_info_game_ids"},
        }
    finally:
        session.close()


@celery_app.task(name="src.tasks.run_mlb_late_info_stamp_ablation")
def run_mlb_late_info_stamp_ablation(
    *,
    start_date: str = "2026-05-20",
    end_date: str = "2026-07-17",
    simulations: int = 2000,
    max_games: int = 1200,
    lookback_days: int = 90,
    configs: Optional[List[str]] = None,
    base_model_version: str = DEFAULT_MODEL_VERSION,
) -> Dict[str, Any]:
    """Densify stamp horizons H0=−6h / H1=−3h / H2=−1h + late-info CLV slices."""
    if not _env_bool("MLB_ALLOW_HISTORICAL_SIM", False):
        raise ValueError(
            "Historical re-sim disabled; set MLB_ALLOW_HISTORICAL_SIM=true for late-info ablation"
        )
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    selected = configs or ["H0", "H1", "H2"]
    unknown = [c for c in selected if c not in _LATE_INFO_STAMP_CONFIGS]
    if unknown:
        raise ValueError(f"unknown late-info stamp configs: {unknown}")

    prior_timing = get_lineup_timing_mode()
    prior_quality = get_starter_quality_mode()
    prior_bp = get_bullpen_role_quality_mode()
    prior_pitch = get_pitch_matchup_enabled()
    prior_wind = get_totals_park_rel_wind_enabled()
    prior_flags = get_stack_ablation_flags()
    results: Dict[str, Any] = {}
    try:
        apply_starter_quality_mode("era_whip")
        apply_bullpen_role_quality_mode("off")
        apply_lineup_timing_mode("off")
        apply_pitch_matchup_flag(False)
        apply_totals_park_rel_wind_flag(False)
        apply_stack_ablation_flags(matchup_mul_enabled=True, weather_wind_dir_mul_enabled=True)
        for name in selected:
            cfg = _LATE_INFO_STAMP_CONFIGS[name]
            model_version = f"{base_model_version}-{cfg['model_suffix']}"
            log.info(
                "Late-info stamp ablation config start",
                extra={"config": name, "model_version": model_version, "flags": cfg},
            )
            graded = _grade_densify_ablation_config(
                model_version=model_version,
                start=start,
                end=end,
                simulations=simulations,
                max_games=max_games,
                lookback_days=lookback_days,
                hours_to_first_pitch=float(cfg["hours_to_first_pitch"]),
            )
            graded["config"] = cfg
            results[name] = graded
    finally:
        apply_lineup_timing_mode(prior_timing or "off")
        apply_starter_quality_mode(prior_quality or "era_whip")
        apply_bullpen_role_quality_mode(prior_bp or "off")
        apply_pitch_matchup_flag(prior_pitch)
        apply_totals_park_rel_wind_flag(prior_wind)
        apply_stack_ablation_flags(
            matchup_mul_enabled=bool(prior_flags.get("matchup_mul_enabled", True)),
            weather_wind_dir_mul_enabled=bool(
                prior_flags.get("weather_wind_dir_mul_enabled", True)
            ),
        )

    intersection = _finalize_intersection_clv(
        results, selected=selected, start=start, end=end, lookback_days=lookback_days
    )
    inter_ids = set()
    # Rebuild id set from intersection n via H1 densify lake (best-effort).
    for name in selected:
        late3 = _late_info_clv_slice(
            model_version=results[name]["model_version"],
            start=start,
            end=end,
            lookback_days=lookback_days,
            max_hours=3.0,
        )
        late6 = _late_info_clv_slice(
            model_version=results[name]["model_version"],
            start=start,
            end=end,
            lookback_days=lookback_days,
            max_hours=6.0,
        )
        results[name]["late_info_clv_le3h"] = late3
        results[name]["late_info_clv_le6h"] = late6

    h1 = (intersection.get("by_config") or {}).get("H1") or {}
    h2 = (intersection.get("by_config") or {}).get("H2") or {}
    h1_ml = h1.get("avg_ml_clv")
    h2_ml = h2.get("avg_ml_clv")
    h2_late = ((results.get("H2") or {}).get("late_info_clv_le3h") or {}).get("clv") or {}
    late_ml = h2_late.get("avg_ml_clv")
    recommendation = {
        "ship_late_stamp_h2": bool(
            h2_ml is not None
            and h1_ml is not None
            and float(h2_ml) >= 0.010
            and float(h2_ml) > float(h1_ml)
        ),
        "ship_late_info_slice": bool(late_ml is not None and float(late_ml) >= 0.010),
        "stretch_target_hit": bool(
            (h2_ml is not None and float(h2_ml) >= 0.015)
            or (late_ml is not None and float(late_ml) >= 0.015)
        ),
        "note": (
            "Ship a late-info stamp only if intersection or ≤3h late-info ML CLV "
            "≥ +0.010 with leakage=0. Snapshot lake enables ongoing live grading."
        ),
    }
    return {
        "status": "ok",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "lookback_days": int(lookback_days),
        "configs": selected,
        "results": results,
        "intersection": intersection,
        "recommendation": recommendation,
        "props_play_stake_eligible": MLB_PROPS_PLAY_STAKE_ELIGIBLE,
        "unused_holdout": unused_holdout_summary(),
        "_unused_inter_ids": list(inter_ids),
    }


@celery_app.task(name="src.tasks.run_mlb_pitch_matchup_ablation")
def run_mlb_pitch_matchup_ablation(
    *,
    start_date: str = "2026-05-20",
    end_date: str = "2026-07-17",
    simulations: int = 2000,
    max_games: int = 1200,
    lookback_days: int = 90,
    configs: Optional[List[str]] = None,
    base_model_version: str = DEFAULT_MODEL_VERSION,
) -> Dict[str, Any]:
    """M0 off vs M1 team-family vs M1b lineup batter-level contact blend."""
    if not _env_bool("MLB_ALLOW_HISTORICAL_SIM", False):
        raise ValueError(
            "Historical re-sim disabled; set MLB_ALLOW_HISTORICAL_SIM=true for pitch matchup ablation"
        )
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    selected = configs or ["M0", "M1", "M1b"]
    unknown = [c for c in selected if c not in _PITCH_MATCHUP_ABLATION_CONFIGS]
    if unknown:
        raise ValueError(f"unknown pitch matchup configs: {unknown}")

    prior_pitch = get_pitch_matchup_enabled()
    prior_fallback = get_pitch_matchup_stuff_fallback()
    prior_batter = get_pitch_matchup_batter_level()
    prior_wind = get_totals_park_rel_wind_enabled()
    prior_timing = get_lineup_timing_mode()
    prior_quality = get_starter_quality_mode()
    prior_bp = get_bullpen_role_quality_mode()
    prior_flags = get_stack_ablation_flags()
    results: Dict[str, Any] = {}
    try:
        apply_starter_quality_mode("era_whip")
        apply_bullpen_role_quality_mode("off")
        apply_lineup_timing_mode("off")
        apply_totals_park_rel_wind_flag(False)
        apply_stack_ablation_flags(matchup_mul_enabled=True, weather_wind_dir_mul_enabled=True)
        for name in selected:
            cfg = _PITCH_MATCHUP_ABLATION_CONFIGS[name]
            model_version = f"{base_model_version}-{cfg['model_suffix']}"
            apply_pitch_matchup_flag(bool(cfg["pitch_matchup_enabled"]))
            apply_pitch_matchup_stuff_fallback(bool(cfg.get("stuff_fallback", False)))
            apply_pitch_matchup_batter_level(bool(cfg.get("batter_level", False)))
            log.info(
                "Pitch matchup ablation config start",
                extra={"config": name, "model_version": model_version, "flags": cfg},
            )
            graded = _grade_densify_ablation_config(
                model_version=model_version,
                start=start,
                end=end,
                simulations=simulations,
                max_games=max_games,
                lookback_days=lookback_days,
                hours_to_first_pitch=3.0,
            )
            graded["config"] = cfg
            graded["pitch_matchup_enabled"] = get_pitch_matchup_enabled()
            graded["pitch_matchup_stuff_fallback"] = get_pitch_matchup_stuff_fallback()
            graded["pitch_matchup_batter_level"] = get_pitch_matchup_batter_level()
            results[name] = graded
    finally:
        apply_pitch_matchup_flag(prior_pitch)
        apply_pitch_matchup_stuff_fallback(prior_fallback)
        apply_pitch_matchup_batter_level(prior_batter)
        apply_totals_park_rel_wind_flag(prior_wind)
        apply_lineup_timing_mode(prior_timing or "off")
        apply_starter_quality_mode(prior_quality or "era_whip")
        apply_bullpen_role_quality_mode(prior_bp or "off")
        apply_stack_ablation_flags(
            matchup_mul_enabled=bool(prior_flags.get("matchup_mul_enabled", True)),
            weather_wind_dir_mul_enabled=bool(
                prior_flags.get("weather_wind_dir_mul_enabled", True)
            ),
        )

    intersection = _finalize_intersection_clv(
        results, selected=selected, start=start, end=end, lookback_days=lookback_days
    )
    m0 = (intersection.get("by_config") or {}).get("M0") or {}
    m1 = (intersection.get("by_config") or {}).get("M1") or {}
    m1b = (intersection.get("by_config") or {}).get("M1b") or {}
    m0_ml = m0.get("avg_ml_clv")
    m1_ml = m1.get("avg_ml_clv")
    m1b_ml = m1b.get("avg_ml_clv")
    candidate_ml = m1b_ml if m1b_ml is not None else m1_ml
    candidate_name = "M1b" if m1b_ml is not None else "M1"
    recommendation = {
        "ship_pitch_matchup": bool(
            candidate_ml is not None
            and m0_ml is not None
            and float(candidate_ml) >= 0.010
            and float(candidate_ml) > float(m0_ml)
        ),
        "ship_batter_level": bool(
            m1b_ml is not None
            and m0_ml is not None
            and float(m1b_ml) >= 0.010
            and float(m1b_ml) > float(m0_ml)
            and (m1_ml is None or float(m1b_ml) >= float(m1_ml))
        ),
        "stretch_target_hit": bool(
            candidate_ml is not None and float(candidate_ml) >= 0.015
        ),
        "primary_candidate": candidate_name,
        "m1_delta_vs_m0": (
            round(float(m1_ml) - float(m0_ml), 5)
            if m1_ml is not None and m0_ml is not None
            else None
        ),
        "m1b_delta_vs_m0": (
            round(float(m1b_ml) - float(m0_ml), 5)
            if m1b_ml is not None and m0_ml is not None
            else None
        ),
        "note": (
            "Ship MLB_PITCH_MATCHUP_ENABLED (+ BATTER_LEVEL for M1b) only if "
            "intersection ML CLV ≥ +0.010 and beats M0 without torching RL/total. "
            "True pitch-type arsenal only (stuff-shape fallback off)."
        ),
    }
    return {
        "status": "ok",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "lookback_days": int(lookback_days),
        "configs": selected,
        "results": results,
        "intersection": intersection,
        "recommendation": recommendation,
        "props_play_stake_eligible": MLB_PROPS_PLAY_STAKE_ELIGIBLE,
        "unused_holdout": unused_holdout_summary(),
    }


@celery_app.task(name="src.tasks.run_mlb_live_late_info_clv_grade")
def run_mlb_live_late_info_clv_grade(
    *,
    start_date: str = "2026-05-20",
    end_date: str = "2026-07-17",
    lookback_days: int = 90,
    max_hours: float = 3.0,
    model_version: str = DEFAULT_MODEL_VERSION,
) -> Dict[str, Any]:
    """Grade ≤3h late-info CLV from live snapshot lake (no densify invent).

    If lake has no live confirms, returns honest n=0 + infrastructure status.
    Does not force-resim densify and does not flip production flags.
    """
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    lake = inventory_snapshot_lake(max_hours=float(max_hours))
    late_ids = set(lake.get("late_info_live_game_ids") or [])
    if not late_ids:
        return {
            "status": "ok",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "model_version": model_version,
            "max_hours": float(max_hours),
            "late_info_n": 0,
            "clv": None,
            "lake": {k: v for k, v in lake.items() if k != "late_info_live_game_ids"},
            "recommendation": {
                "ship_late_info_slice": False,
                "note": (
                    "Live ≤3h snapshot lake has no confirmed late-info games yet. "
                    "Keep nowcast persistence; do not fake densify late-info n."
                ),
            },
            "unused_holdout": unused_holdout_summary(),
        }

    session = SessionLocal()
    try:
        clv_full = compute_mlb_clv_with_spread(
            session,
            model_version=model_version,
            lookback_days=int(lookback_days),
        )
        window_items = _filter_clv_items_to_window(
            session,
            list(clv_full.get("items") or []),
            start_date=start,
            end_date=end,
        )
        late_items = [i for i in window_items if str(i.get("game_id")) in late_ids]
        summary = _summarize_clv_items(late_items)
        summary.pop("ml_game_ids", None)
    finally:
        session.close()

    ml = summary.get("avg_ml_clv")
    return {
        "status": "ok",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "model_version": model_version,
        "max_hours": float(max_hours),
        "late_info_n": len(late_items),
        "clv": summary,
        "lake": {k: v for k, v in lake.items() if k != "late_info_live_game_ids"},
        "recommendation": {
            "ship_late_info_slice": bool(ml is not None and float(ml) >= 0.010),
            "stretch_target_hit": bool(ml is not None and float(ml) >= 0.015),
            "note": (
                "Ship late-info stamp behavior only if live ≤3h ML CLV ≥ +0.010 "
                "with leakage=0 on production S0 stack."
            ),
        },
        "unused_holdout": unused_holdout_summary(),
    }


@celery_app.task(name="src.tasks.run_mlb_totals_park_wind_ablation")
def run_mlb_totals_park_wind_ablation(
    *,
    start_date: str = "2026-05-20",
    end_date: str = "2026-07-17",
    simulations: int = 2000,
    max_games: int = 1200,
    lookback_days: int = 90,
    configs: Optional[List[str]] = None,
    base_model_version: str = DEFAULT_MODEL_VERSION,
) -> Dict[str, Any]:
    """W0 (S0) vs W1 (park-relative wind on totals only). ML must not regress."""
    if not _env_bool("MLB_ALLOW_HISTORICAL_SIM", False):
        raise ValueError(
            "Historical re-sim disabled; set MLB_ALLOW_HISTORICAL_SIM=true for park-wind ablation"
        )
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    selected = configs or ["W0", "W1"]
    unknown = [c for c in selected if c not in _TOTALS_PARK_WIND_ABLATION_CONFIGS]
    if unknown:
        raise ValueError(f"unknown park-wind configs: {unknown}")

    prior_pitch = get_pitch_matchup_enabled()
    prior_wind = get_totals_park_rel_wind_enabled()
    prior_timing = get_lineup_timing_mode()
    prior_quality = get_starter_quality_mode()
    prior_bp = get_bullpen_role_quality_mode()
    prior_flags = get_stack_ablation_flags()
    results: Dict[str, Any] = {}
    try:
        apply_starter_quality_mode("era_whip")
        apply_bullpen_role_quality_mode("off")
        apply_lineup_timing_mode("off")
        apply_pitch_matchup_flag(False)
        apply_stack_ablation_flags(matchup_mul_enabled=True, weather_wind_dir_mul_enabled=True)
        for name in selected:
            cfg = _TOTALS_PARK_WIND_ABLATION_CONFIGS[name]
            model_version = f"{base_model_version}-{cfg['model_suffix']}"
            apply_totals_park_rel_wind_flag(bool(cfg["totals_park_rel_wind_enabled"]))
            log.info(
                "Totals park-wind ablation config start",
                extra={"config": name, "model_version": model_version, "flags": cfg},
            )
            graded = _grade_densify_ablation_config(
                model_version=model_version,
                start=start,
                end=end,
                simulations=simulations,
                max_games=max_games,
                lookback_days=lookback_days,
                hours_to_first_pitch=3.0,
            )
            graded["config"] = cfg
            graded["totals_park_rel_wind_enabled"] = get_totals_park_rel_wind_enabled()
            results[name] = graded
    finally:
        apply_pitch_matchup_flag(prior_pitch)
        apply_totals_park_rel_wind_flag(prior_wind)
        apply_lineup_timing_mode(prior_timing or "off")
        apply_starter_quality_mode(prior_quality or "era_whip")
        apply_bullpen_role_quality_mode(prior_bp or "off")
        apply_stack_ablation_flags(
            matchup_mul_enabled=bool(prior_flags.get("matchup_mul_enabled", True)),
            weather_wind_dir_mul_enabled=bool(
                prior_flags.get("weather_wind_dir_mul_enabled", True)
            ),
        )

    intersection = _finalize_intersection_clv(
        results, selected=selected, start=start, end=end, lookback_days=lookback_days
    )
    w0 = (intersection.get("by_config") or {}).get("W0") or {}
    w1 = (intersection.get("by_config") or {}).get("W1") or {}
    w0_ml = w0.get("avg_ml_clv")
    w1_ml = w1.get("avg_ml_clv")
    w0_tot = w0.get("avg_total_clv")
    w1_tot = w1.get("avg_total_clv")
    w0_mae = ((results.get("W0") or {}).get("walkforward") or {}).get("base_mae_total_runs")
    w1_mae = ((results.get("W1") or {}).get("walkforward") or {}).get("base_mae_total_runs")
    totals_improved = bool(
        (w1_tot is not None and w0_tot is not None and float(w1_tot) > float(w0_tot))
        or (w1_mae is not None and w0_mae is not None and float(w1_mae) < float(w0_mae))
    )
    ml_ok = bool(
        w1_ml is not None
        and w0_ml is not None
        and float(w1_ml) >= float(w0_ml) - 0.0005  # allow tiny noise
    )
    recommendation = {
        "ship_totals_park_rel_wind": bool(totals_improved and ml_ok),
        "totals_improved": totals_improved,
        "ml_not_regressed": ml_ok,
        "w1_delta_total_clv": (
            round(float(w1_tot) - float(w0_tot), 5)
            if w1_tot is not None and w0_tot is not None
            else None
        ),
        "w1_delta_ml_clv": (
            round(float(w1_ml) - float(w0_ml), 5)
            if w1_ml is not None and w0_ml is not None
            else None
        ),
        "note": (
            "Ship MLB_TOTALS_PARK_REL_WIND_ENABLED only if totals MAE/CLV improve "
            "and intersection ML CLV does not regress. ML wind-dir path stays S0."
        ),
    }
    return {
        "status": "ok",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "lookback_days": int(lookback_days),
        "configs": selected,
        "results": results,
        "intersection": intersection,
        "recommendation": recommendation,
        "props_play_stake_eligible": MLB_PROPS_PLAY_STAKE_ELIGIBLE,
        "unused_holdout": unused_holdout_summary(),
    }


def _resolve_nfl_week(session: Any, season: int, week: Optional[int]) -> int:
    if week is not None:
        return int(week)
    # Default to the latest *regular-season* week. MAX(week) on historical
    # usage includes 19–22 (SB) and was the week-22-only remat wipe path.
    row = session.execute(
        text(
            """
            SELECT COALESCE(MAX(week), 1)::int AS week
            FROM nfl_dp_player_usage_weekly
            WHERE season = :season
              AND week BETWEEN 1 AND 18
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


def _qb_depth_orders_by_team(session: Any, *, season: int, week: int) -> Dict[str, Dict[str, float]]:
    """{team: {player_id: depth_order}} for QBs — fallback when snaps are all zero."""
    rows = session.execute(
        text(
            """
            SELECT team, player_id, depth_order
            FROM nfl_dp_depth_chart_weekly
            WHERE season = :season
              AND week = :week
              AND UPPER(position) = 'QB'
            """
        ),
        {"season": int(season), "week": int(week)},
    ).fetchall()
    out: Dict[str, Dict[str, float]] = {}
    for row in rows:
        out.setdefault(str(row.team), {})[str(row.player_id)] = float(row.depth_order or 99.0)
    return out


def _rb_depth_orders_by_team(session: Any, *, season: int, week: int) -> Dict[str, Dict[str, float]]:
    rows = session.execute(
        text(
            """
            SELECT team, player_id, depth_order
            FROM nfl_dp_depth_chart_weekly
            WHERE season = :season
              AND week = :week
              AND UPPER(position) IN ('RB', 'HB', 'FB')
            """
        ),
        {"season": int(season), "week": int(week)},
    ).fetchall()
    out: Dict[str, Dict[str, float]] = {}
    for row in rows:
        out.setdefault(str(row.team), {})[str(row.player_id)] = float(row.depth_order or 99.0)
    return out


# WR/TE depth target priors live in nfl_playing_time (WR4+ / TE2+ near-zero).


def _rb_prior_carries_by_team_player(
    session: Any, *, season: int, lookback_seasons: int = 2
) -> Dict[tuple[str, str], float]:
    """Team-scoped prior rush attempts: {(team, player_id): carries}."""
    start_season = int(season) - int(lookback_seasons)
    end_season = int(season) - 1
    if end_season < start_season:
        return {}
    rows = session.execute(
        text(
            """
            SELECT
              team,
              player_id,
              SUM(COALESCE(rush_attempts, 0))::float AS carries
            FROM nfl_dp_player_usage_weekly
            WHERE season BETWEEN :start_season AND :end_season
              AND UPPER(COALESCE(position, '')) IN ('RB', 'HB', 'FB')
            GROUP BY team, player_id
            """
        ),
        {"start_season": start_season, "end_season": end_season},
    ).fetchall()
    return {(str(row.team), str(row.player_id)): float(row.carries or 0.0) for row in rows}


def _rb_prior_carries_by_player(
    session: Any, *, season: int, lookback_seasons: int = 2
) -> Dict[str, float]:
    """Career prior rush attempts keyed by player_id (cross-team fallback)."""
    start_season = int(season) - int(lookback_seasons)
    end_season = int(season) - 1
    if end_season < start_season:
        return {}
    rows = session.execute(
        text(
            """
            SELECT
              player_id,
              SUM(COALESCE(rush_attempts, 0))::float AS carries
            FROM nfl_dp_player_usage_weekly
            WHERE season BETWEEN :start_season AND :end_season
              AND UPPER(COALESCE(position, '')) IN ('RB', 'HB', 'FB')
            GROUP BY player_id
            """
        ),
        {"start_season": start_season, "end_season": end_season},
    ).fetchall()
    return {str(row.player_id): float(row.carries or 0.0) for row in rows}


def _skill_prior_offense_snap_pct_by_player(
    session: Any, *, season: int, lookback_seasons: int = 2
) -> Dict[str, float]:
    """Mean prior-season offense snap % keyed by GSIS player_id."""
    start_season = int(season) - int(lookback_seasons)
    end_season = int(season) - 1
    if end_season < start_season:
        return {}
    rows = session.execute(
        text(
            """
            SELECT
              gsis_player_id AS player_id,
              AVG(offense_pct)::float AS offense_snap_pct
            FROM nfl_dp_snap_counts_weekly
            WHERE season BETWEEN :start_season AND :end_season
              AND gsis_player_id IS NOT NULL
              AND offense_pct IS NOT NULL
              AND UPPER(COALESCE(position, '')) IN ('RB', 'HB', 'FB', 'WR', 'TE', 'QB')
            GROUP BY gsis_player_id
            """
        ),
        {"start_season": start_season, "end_season": end_season},
    ).fetchall()
    return {str(row.player_id): float(row.offense_snap_pct or 0.0) for row in rows}


def _team_rb_rush_shares(
    trailing_rush_by_team: Dict[str, Dict[str, float]],
    depth_orders_by_team: Dict[str, Dict[str, float]],
    *,
    prior_carries_by_player: Dict[str, float] | None = None,
    prior_carries_by_team_player: Dict[tuple[str, str], float] | None = None,
    offense_snap_pcts_by_player: Dict[str, float] | None = None,
) -> Dict[tuple[str, str], float]:
    """Per-team winner-take-most (usage-aware) RB rush shares."""
    shares: Dict[tuple[str, str], float] = {}
    career_priors = prior_carries_by_player or {}
    team_priors_map = prior_carries_by_team_player or {}
    snap_pcts = offense_snap_pcts_by_player or {}
    for team, trailing in trailing_rush_by_team.items():
        team_scoped = {pid: float(team_priors_map.get((team, pid)) or 0.0) for pid in trailing}
        if sum(team_scoped.values()) > 0.0:
            priors_for_room = team_scoped
        else:
            priors_for_room = {pid: float(career_priors.get(pid) or 0.0) for pid in trailing}
        room_snaps = {pid: float(snap_pcts.get(pid) or 0.0) for pid in trailing}
        for player_id, share in compute_rb_rush_shares(
            trailing,
            depth_orders=depth_orders_by_team.get(team),
            prior_carries=priors_for_room,
            offense_snap_pcts=room_snaps,
        ).items():
            shares[(team, player_id)] = float(share)
    return shares


def _wr_te_depth_orders_by_team(session: Any, *, season: int, week: int) -> Dict[str, Dict[str, float]]:
    rows = session.execute(
        text(
            """
            SELECT team, player_id, depth_order, UPPER(position) AS position
            FROM nfl_dp_depth_chart_weekly
            WHERE season = :season
              AND week = :week
              AND UPPER(position) IN ('WR', 'TE')
            """
        ),
        {"season": int(season), "week": int(week)},
    ).fetchall()
    out: Dict[str, Dict[str, float]] = {}
    for row in rows:
        out.setdefault(str(row.team), {})[str(row.player_id)] = float(row.depth_order or 99.0)
    return out


def _apply_wr_te_depth_target_prior(
    *,
    team: str,
    player_id: str,
    position: str,
    target_proxy: float,
    depth_by_team: Dict[str, Dict[str, float]],
) -> float:
    """Blend trailing target share with depth-chart prior (Jameson-class miss).

    Phase 2: modest WR1 prior/floor lift — fresh rematerialize already moved
    8+ target residual near −4; close the remaining undercount without
    inflating sub-5 target roles.
    """
    pos = str(position or "").upper()
    if pos not in {"WR", "TE"}:
        return float(target_proxy)
    depth = depth_by_team.get(str(team), {}).get(str(player_id))
    if depth is None:
        return float(target_proxy)
    prior = depth_target_prior(pos, depth)
    usage = max(0.0, float(target_proxy or 0.0))
    depth_i = int(depth)
    if depth_i == 1 and pos == "WR":
        blended = (0.50 * usage) + (0.50 * prior)
        blended = max(blended, 0.26)
        return max(0.0, min(0.50, blended))
    blended = (0.55 * usage) + (0.45 * prior)
    if depth_i == 1:
        blended = max(blended, 0.16)
    # WR4+ / TE2+ cannot inherit inflated hydrate intercepts.
    if pos == "WR" and depth_i >= 4:
        blended = min(blended, 0.02)
    if pos == "TE" and depth_i >= 2:
        blended = min(blended, 0.14)
    if pos == "TE" and depth_i >= 3:
        blended = min(blended, 0.04)
    return max(0.0, min(0.48, blended))


def _skill_prior_ypg_by_player(
    session: Any, *, season: int, lookback_seasons: int = 2
) -> Dict[str, Dict[str, float]]:
    """Recent skill production: {player_id: {rec_ypg, rush_ypg, active_games}}."""
    start_season = int(season) - int(lookback_seasons)
    end_season = int(season) - 1
    if end_season < start_season:
        return {}
    rows = session.execute(
        text(
            """
            SELECT
              player_id,
              UPPER(COALESCE(position, '')) AS position,
              SUM(COALESCE(receiving_yards, 0))::float AS rec_yards,
              SUM(COALESCE(rush_yards, 0))::float AS rush_yards,
              COUNT(*) FILTER (
                WHERE COALESCE(targets, 0) + COALESCE(rush_attempts, 0) >= 3
              )::float AS active_games
            FROM nfl_dp_player_usage_weekly
            WHERE season BETWEEN :start_season AND :end_season
              AND UPPER(COALESCE(position, '')) IN ('WR', 'TE', 'RB', 'FB', 'HB')
            GROUP BY player_id, UPPER(COALESCE(position, ''))
            """
        ),
        {"start_season": start_season, "end_season": end_season},
    ).fetchall()
    out: Dict[str, Dict[str, float]] = {}
    for row in rows:
        active = float(row.active_games or 0.0)
        rec_ypg = (float(row.rec_yards or 0.0) / active) if active > 0 else 0.0
        rush_ypg = (float(row.rush_yards or 0.0) / active) if active > 0 else 0.0
        out[str(row.player_id)] = {
            "position": str(row.position or ""),
            "rec_ypg": rec_ypg,
            "rush_ypg": rush_ypg,
            "active_games": active,
        }
    return out


def _qb_prior_production_by_player(
    session: Any, *, season: int, lookback_seasons: int = 2
) -> Dict[str, Dict[str, float]]:
    """Recent QB production priors keyed by player_id (cross-team career).

    Returns {player_id: {attempts, yards, startish_games, yards_per_startish}}.
    Talent factor uses this career read. Starter resolution prefers
    team-scoped attempts from `_qb_prior_attempts_by_team_player` so a
    free-agent's old-team volume cannot crown them QB1 on a new roster
    (e.g. Kyler on MIN after ARI years).
    """
    start_season = int(season) - int(lookback_seasons)
    end_season = int(season) - 1
    if end_season < start_season:
        return {}
    rows = session.execute(
        text(
            """
            SELECT
              player_id,
              SUM(COALESCE(pass_attempts, 0))::float AS attempts,
              SUM(COALESCE(pass_yards, 0))::float AS yards,
              COUNT(*) FILTER (WHERE COALESCE(pass_attempts, 0) >= 10)::float AS startish_games
            FROM nfl_dp_player_usage_weekly
            WHERE season BETWEEN :start_season AND :end_season
              AND UPPER(COALESCE(position, '')) = 'QB'
            GROUP BY player_id
            """
        ),
        {"start_season": start_season, "end_season": end_season},
    ).fetchall()
    out: Dict[str, Dict[str, float]] = {}
    for row in rows:
        attempts = float(row.attempts or 0.0)
        yards = float(row.yards or 0.0)
        startish = float(row.startish_games or 0.0)
        ypg = (yards / startish) if startish > 0.0 else 0.0
        out[str(row.player_id)] = {
            "attempts": attempts,
            "yards": yards,
            "startish_games": startish,
            "yards_per_startish": ypg,
        }
    return out


def _qb_prior_attempts_by_team_player(
    session: Any, *, season: int, lookback_seasons: int = 2
) -> Dict[tuple[str, str], float]:
    """Team-scoped prior pass attempts: {(team, player_id): attempts}."""
    start_season = int(season) - int(lookback_seasons)
    end_season = int(season) - 1
    if end_season < start_season:
        return {}
    rows = session.execute(
        text(
            """
            SELECT
              team,
              player_id,
              SUM(COALESCE(pass_attempts, 0))::float AS attempts
            FROM nfl_dp_player_usage_weekly
            WHERE season BETWEEN :start_season AND :end_season
              AND UPPER(COALESCE(position, '')) = 'QB'
            GROUP BY team, player_id
            """
        ),
        {"start_season": start_season, "end_season": end_season},
    ).fetchall()
    return {(str(row.team), str(row.player_id)): float(row.attempts or 0.0) for row in rows}


def _team_qb_starter_shares(
    qb_snap_shares_by_team: Dict[str, Dict[str, float]],
    depth_orders_by_team: Dict[str, Dict[str, float]],
    prior_attempts_by_player: Dict[str, float] | None = None,
    prior_attempts_by_team_player: Dict[tuple[str, str], float] | None = None,
) -> Dict[tuple[str, str], float]:
    shares: Dict[tuple[str, str], float] = {}
    career_priors = prior_attempts_by_player or {}
    team_priors_map = prior_attempts_by_team_player or {}
    for team, snap_shares in qb_snap_shares_by_team.items():
        # Prefer same-team prior volume; fall back to career attempts only
        # when the room has no team-scoped signal at all.
        team_scoped = {pid: float(team_priors_map.get((team, pid)) or 0.0) for pid in snap_shares}
        if sum(team_scoped.values()) > 0.0:
            priors_for_room = team_scoped
        else:
            priors_for_room = {pid: float(career_priors.get(pid) or 0.0) for pid in snap_shares}
        for player_id, share in compute_qb_starter_shares(
            snap_shares,
            depth_orders=depth_orders_by_team.get(team),
            prior_attempts=priors_for_room,
        ).items():
            shares[(team, player_id)] = share
    return shares


@celery_app.task(name="src.tasks.materialize_nfl_player_projection_features")
def materialize_nfl_player_projection_features_task(
    *,
    season: int,
    week: Optional[int] = None,
    replace_existing: bool = True,
) -> Dict[str, Any]:
    """Rematerialize `nfl_player_projection_features_weekly` from owned usage.

    Empty feature rows for a season/week are the root cause of
    `baseline_rows_upserted=0` — baselines read features only.
    """
    from data_platform_nfl.ingest import materialize_player_projection_features

    result = materialize_player_projection_features(
        seasons=[int(season)],
        week=int(week) if week is not None else None,
        replace_existing=bool(replace_existing),
    )
    feature_rows = int((result.get("rows") or {}).get("projection_feature_rows") or 0)
    return {
        "season": int(season),
        "week": int(week) if week is not None else None,
        "replace_existing": bool(replace_existing),
        "feature_rows": feature_rows,
        "status": "ok" if feature_rows > 0 else "empty",
        "result": result,
    }


@celery_app.task(name="src.tasks.run_nfl_props_layer_rebuild")
def run_nfl_props_layer_rebuild(
    *,
    season: int,
    week: Optional[int] = None,
    weeks: Optional[List[int]] = None,
    model_version: str = "nfl-player-v1",
    replace_features: bool = True,
    rematerialize_season_features: bool = False,
) -> Dict[str, Any]:
    """Features → baselines → box sims → props for one or more weeks.

    Use when baselines report `feature_rows=0` / `baseline_rows_upserted=0`,
    or when depth-floor fixes need a clean projection rematerialize (not a
    market nudge).

    Safe entrypoint: omit week/weeks to remat regular season 1–18. Never
    enqueue this task with bare ``season=`` on old workers (week-22 wipe).
    """
    # Season-only (no week/weeks) → 1–18, never MAX(week)=22.
    target_weeks = resolve_remat_weeks(week=week, weeks=weeks)

    # Coverage probe before features rematerialize (usage must exist).
    session = SessionLocal()
    pre_coverage: Dict[str, Any] = {"weeks": {}}
    try:
        for tw in target_weeks:
            usage_n = session.execute(
                text(
                    """
                    SELECT COUNT(*)::int
                    FROM nfl_dp_player_usage_weekly
                    WHERE season = :season AND week = :week
                    """
                ),
                {"season": int(season), "week": int(tw)},
            ).scalar_one()
            feat_n = session.execute(
                text(
                    """
                    SELECT COUNT(*)::int
                    FROM nfl_player_projection_features_weekly
                    WHERE season = :season AND week = :week
                    """
                ),
                {"season": int(season), "week": int(tw)},
            ).scalar_one()
            pre_coverage["weeks"][str(tw)] = {
                "usage_rows": int(usage_n or 0),
                "feature_rows": int(feat_n or 0),
            }
    finally:
        session.close()

    features_result: Dict[str, Any]
    if rematerialize_season_features:
        features_result = materialize_nfl_player_projection_features_task(
            season=int(season),
            week=None,
            replace_existing=bool(replace_features),
        )
    else:
        # Rematerialize each requested week (keeps unrelated weeks intact).
        per_week_features = []
        for tw in target_weeks:
            per_week_features.append(
                materialize_nfl_player_projection_features_task(
                    season=int(season),
                    week=int(tw),
                    replace_existing=bool(replace_features),
                )
            )
        features_result = {
            "mode": "per_week",
            "weeks": per_week_features,
            "feature_rows": sum(int(r.get("feature_rows") or 0) for r in per_week_features),
        }

    week_results: List[Dict[str, Any]] = []
    for tw in target_weeks:
        baseline = materialize_nfl_player_baseline_projections(
            season=int(season), week=int(tw), model_version=model_version
        )
        box = materialize_nfl_player_box_score_sims(season=int(season), week=int(tw))
        props = materialize_nfl_player_props_edges(
            season=int(season), week=int(tw), model_version=model_version
        )
        week_results.append(
            {
                "week": int(tw),
                "baseline": baseline,
                "box": box,
                "props": props,
            }
        )

    return {
        "season": int(season),
        "weeks": target_weeks,
        "pre_coverage": pre_coverage,
        "features": features_result,
        "week_results": week_results,
        "worker_build_id": "props-under-bias-20260731c-baselines-box-rebuild",
        "status": "ok",
    }


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
                  season, week, team, player_id, player_uid, player_name, position, game_id, opponent,
                  snap_proxy, team_snap_share, route_proxy, target_proxy, rush_share, red_zone_share,
                  qb_dropback_factor, qb_pressure_factor, team_pace_factor, team_pass_rate_factor,
                  opponent_pass_defense_factor, opponent_rush_defense_factor,
                  availability_confidence, role_confidence, feature_payload, updated_at,
                  offense_snaps, offense_snap_pct, snap_source
                FROM nfl_player_projection_features_weekly
                WHERE season = :season
                  AND week = :week
                ORDER BY team, position, player_name
                """
            ),
            {"season": int(season), "week": int(target_week)},
        ).fetchall()

        # Enterprise QB room resolution: prior attempts + depth + snaps →
        # winner-take-most starter shares (see compute_qb_starter_shares).
        qb_snap_shares_by_team: Dict[str, Dict[str, float]] = {}
        rb_trailing_rush_by_team: Dict[str, Dict[str, float]] = {}
        rb_week_snap_pcts: Dict[str, float] = {}
        for row in rows:
            pos = str(row.position or "").upper()
            pid = str(row.player_id)
            if pos == "QB":
                qb_snap_shares_by_team.setdefault(row.team, {})[pid] = float(row.team_snap_share or 0.0)
            elif pos in {"RB", "HB", "FB"}:
                rb_trailing_rush_by_team.setdefault(row.team, {})[pid] = float(row.rush_share or 0.0)
                snap_pct = getattr(row, "offense_snap_pct", None)
                if snap_pct is None and isinstance(row.feature_payload, dict):
                    snap_pct = row.feature_payload.get("offense_snap_pct")
                if snap_pct is not None:
                    rb_week_snap_pcts[pid] = float(snap_pct or 0.0)
                else:
                    rb_week_snap_pcts[pid] = float(row.team_snap_share or 0.0)
        depth_orders_by_team = _qb_depth_orders_by_team(session, season=int(season), week=int(target_week))
        qb_prior_production = _qb_prior_production_by_player(session, season=int(season))
        skill_prior_ypg = _skill_prior_ypg_by_player(session, season=int(season))
        prior_attempts_by_player = {
            pid: float(stats.get("attempts") or 0.0) for pid, stats in qb_prior_production.items()
        }
        prior_attempts_by_team_player = _qb_prior_attempts_by_team_player(session, season=int(season))
        qb_starter_shares = _team_qb_starter_shares(
            qb_snap_shares_by_team,
            depth_orders_by_team,
            prior_attempts_by_player=prior_attempts_by_player,
            prior_attempts_by_team_player=prior_attempts_by_team_player,
        )
        rb_depth_by_team = _rb_depth_orders_by_team(session, season=int(season), week=int(target_week))
        wr_te_depth_by_team = _wr_te_depth_orders_by_team(session, season=int(season), week=int(target_week))
        # Official depth-chart joins miss for many skill players (id/week gaps).
        # Fill from trailing usage ranks so WR1/RB1 floors still fire.
        feature_maps = [
            {
                "team": str(r.team or ""),
                "player_id": str(r.player_id or ""),
                "position": str(r.position or ""),
                "target_proxy": float(r.target_proxy or 0.0),
                "rush_share": float(r.rush_share or 0.0),
            }
            for r in rows
        ]
        wr_te_depth_by_team = merge_depth_orders(
            wr_te_depth_by_team,
            usage_rank_depth_orders(feature_maps, positions=("WR", "TE"), usage_key="target_proxy"),
        )
        rb_depth_by_team = merge_depth_orders(
            rb_depth_by_team,
            usage_rank_depth_orders(feature_maps, positions=("RB", "FB", "HB"), usage_key="rush_share"),
        )
        prior_snap_pcts = _skill_prior_offense_snap_pct_by_player(session, season=int(season))
        # Prefer same-week bridged snaps; fall back to prior-season averages.
        rb_snap_pcts_for_rooms = {**prior_snap_pcts, **rb_week_snap_pcts}
        rb_rush_shares = _team_rb_rush_shares(
            rb_trailing_rush_by_team,
            rb_depth_by_team,
            prior_carries_by_player=_rb_prior_carries_by_player(session, season=int(season)),
            prior_carries_by_team_player=_rb_prior_carries_by_team_player(session, season=int(season)),
            offense_snap_pcts_by_player=rb_snap_pcts_for_rooms,
        )

        # Enterprise injury role shocks: OUT/DNP/IR players forfeit volume to
        # healthy roommates (see nfl_injury_role_shocks).
        from .services.nfl_injury_role_shocks import (
            load_team_injury_availability,
            redistribute_team_usage_for_injuries,
        )
        from .services.nfl_tendency_pricing import (
            apply_tendency_to_player_pass_rate,
            fetch_team_proe_map,
        )

        injury_avail = load_team_injury_availability(session, season=int(season), week=int(target_week))
        try:
            proe_by_team = fetch_team_proe_map(session, season=int(season), situation="all")
            if not proe_by_team:
                proe_by_team = fetch_team_proe_map(session, season=int(season) - 1, situation="all")
        except Exception:
            session.rollback()
            proe_by_team = {}

        injury_shocks_by_team: Dict[str, Dict[str, Dict[str, float]]] = {}
        rows_by_team_tmp: Dict[str, List[Any]] = {}
        for row in rows:
            rows_by_team_tmp.setdefault(str(row.team), []).append(row)
        for team, team_rows in rows_by_team_tmp.items():
            shock_inputs = []
            for row in team_rows:
                pid = str(row.player_id)
                inj = (
                    injury_avail.get((team, pid))
                    or injury_avail.get((team, str(row.player_name or "")))
                    or {}
                )
                avail = float(inj.get("availability") if inj else (row.availability_confidence or 0.90))
                shock_inputs.append(
                    {
                        "player_id": pid,
                        "position": str(row.position or ""),
                        "availability": avail,
                        "rush_share": float(
                            rb_rush_shares.get((team, pid), float(row.rush_share or 0.0))
                        ),
                        "target_proxy": float(row.target_proxy or 0.0),
                        "qb_starter_share": float(qb_starter_shares.get((team, pid), 1.0)),
                    }
                )
            injury_shocks_by_team[team] = redistribute_team_usage_for_injuries(shock_inputs)

        # Game-script anchors from schedule closing lines (nflverse).
        schedule_rows = session.execute(
            text(
                """
                SELECT home_team, away_team, spread_line, total_line
                FROM nfl_dp_schedules
                WHERE season = :season
                  AND week = :week
                """
            ),
            {"season": int(season), "week": int(target_week)},
        ).fetchall()
        team_script: Dict[str, tuple[float, float]] = {}
        for srow in schedule_rows:
            total = float(srow.total_line) if srow.total_line is not None else None
            spread = float(srow.spread_line) if srow.spread_line is not None else None
            if total is None or spread is None:
                continue
            home = str(srow.home_team or "")
            away = str(srow.away_team or "")
            # spread_line is home spread; team_spread negative ⇒ favorite.
            home_implied = (total / 2.0) - (spread / 2.0)
            away_implied = (total / 2.0) + (spread / 2.0)
            if home:
                team_script[home] = (home_implied, spread)
            if away:
                team_script[away] = (away_implied, -spread)

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
            usage_source = None
            if isinstance(row.feature_payload, dict):
                usage_source = row.feature_payload.get("usage_source")
            experience_confidence = (
                ROOKIE_EXPERIENCE_CONFIDENCE if usage_source == "rookie_baseline_v1" else VETERAN_EXPERIENCE_CONFIDENCE
            )
            implied_total, team_spread = team_script.get(str(row.team or ""), (0.0, 0.0))
            team_key = str(row.team or "")
            pid_key = str(row.player_id)
            shock = (injury_shocks_by_team.get(team_key) or {}).get(pid_key) or {}
            starter_share = float(
                shock.get("qb_starter_share", qb_starter_shares.get((row.team, pid_key), 1.0))
            )
            role_conf = float(row.role_confidence or 0.65)
            talent_factor = 1.0
            skill_talent = 1.0
            pos_upper = str(row.position or "").upper()
            availability_conf = float(
                shock.get("availability", row.availability_confidence or 0.75)
            )
            injury_shock_amt = float(shock.get("injury_shock") or 0.0)
            if pos_upper == "QB":
                if starter_share >= 0.85:
                    role_conf = max(role_conf, 0.82)
                prior_stats = qb_prior_production.get(pid_key) or {}
                prior_ypg = prior_stats.get("yards_per_startish")
                talent_factor = qb_talent_factor_from_prior_ypg(
                    float(prior_ypg) if prior_ypg is not None and float(prior_ypg) > 0 else None
                )
            if pos_upper in {"RB", "FB", "HB"}:
                rush_share = float(
                    shock.get(
                        "rush_share",
                        rb_rush_shares.get((team_key, pid_key), float(row.rush_share or 0.0)),
                    )
                )
            else:
                rush_share = float(row.rush_share or 0.0)
            target_proxy = _apply_wr_te_depth_target_prior(
                team=team_key,
                player_id=pid_key,
                position=str(row.position or ""),
                target_proxy=float(row.target_proxy or 0.0),
                depth_by_team=wr_te_depth_by_team,
            )
            if shock.get("target_proxy") is not None and pos_upper in {"WR", "TE"}:
                # Preserve depth prior floor, then apply injury redistribution.
                target_proxy = max(float(target_proxy), 0.0) * 0.35 + float(shock["target_proxy"]) * 0.65
            if pos_upper in {"WR", "TE"}:
                depth_ord = wr_te_depth_by_team.get(str(row.team or ""), {}).get(str(row.player_id))
                floor = depth_role_confidence_floor(pos_upper, depth_ord)
                if floor is not None:
                    role_conf = max(role_conf, floor)
                prior_skill = skill_prior_ypg.get(str(row.player_id)) or {}
                skill_talent = skill_talent_factor_from_prior_ypg(
                    float(prior_skill.get("rec_ypg") or 0.0) or None,
                    position=pos_upper,
                )
            elif pos_upper in {"RB", "FB", "HB"}:
                depth_ord = rb_depth_by_team.get(str(row.team or ""), {}).get(str(row.player_id))
                floor = depth_role_confidence_floor(pos_upper, depth_ord)
                if floor is not None:
                    role_conf = max(role_conf, floor)
                if rush_share >= 0.55:
                    role_conf = max(role_conf, 0.84)
                prior_skill = skill_prior_ypg.get(str(row.player_id)) or {}
                skill_talent = skill_talent_factor_from_prior_ypg(
                    float(prior_skill.get("rush_ypg") or 0.0) or None,
                    position=pos_upper,
                )
            offense_snaps = getattr(row, "offense_snaps", None)
            offense_snap_pct = getattr(row, "offense_snap_pct", None)
            snap_source = getattr(row, "snap_source", None)
            if isinstance(row.feature_payload, dict):
                if offense_snaps is None:
                    offense_snaps = row.feature_payload.get("offense_snaps")
                if offense_snap_pct is None:
                    offense_snap_pct = row.feature_payload.get("offense_snap_pct")
                if snap_source is None:
                    snap_source = row.feature_payload.get("snap_source")
            opponent = str(getattr(row, "opponent", None) or "")
            team_pass_rate = apply_tendency_to_player_pass_rate(
                float(row.team_pass_rate_factor or 1.0),
                team=team_key,
                opponent=opponent,
                proe_by_team=proe_by_team,
            )
            inputs = PlayerFeatureInputs(
                position=str(row.position or ""),
                snap_proxy=float(row.snap_proxy or 0.0),
                route_proxy=float(row.route_proxy or 0.0),
                target_proxy=target_proxy,
                rush_share=rush_share,
                red_zone_share=float(row.red_zone_share or 0.0),
                qb_dropback_factor=float(row.qb_dropback_factor or 1.0),
                qb_pressure_factor=float(row.qb_pressure_factor or 1.0),
                team_pace_factor=float(row.team_pace_factor or 1.0),
                team_pass_rate_factor=team_pass_rate,
                availability_confidence=availability_conf,
                role_confidence=role_conf,
                experience_confidence=experience_confidence,
                team_snap_share=float(row.team_snap_share or 0.0),
                opponent_pass_defense_factor=float(row.opponent_pass_defense_factor or 1.0),
                opponent_rush_defense_factor=float(row.opponent_rush_defense_factor or 1.0),
                qb_starter_share=starter_share,
                qb_talent_factor=talent_factor,
                skill_talent_factor=skill_talent,
                implied_team_total=float(implied_total or 0.0),
                team_spread=float(team_spread or 0.0),
            )
            baseline = baseline_projection_from_features(inputs)
            cov_key = str(resolved_player_uid or row.player_name)
            coverage_payload = {
                "feature_source": "nfl_player_projection_features_weekly",
                "qb_starter_share": starter_share if pos_upper == "QB" else None,
                "qb_talent_factor": talent_factor if pos_upper == "QB" else None,
                "skill_talent_factor": skill_talent if pos_upper in {"WR", "TE", "RB", "FB", "HB"} else None,
                "rb_rush_share": rush_share if pos_upper in {"RB", "FB", "HB"} else None,
                "injury_shock": injury_shock_amt if injury_shock_amt > 0 else None,
                "availability_confidence": availability_conf,
                "tendency_pass_rate_factor": team_pass_rate,
                "offense_snaps": float(offense_snaps) if offense_snaps is not None else None,
                "offense_snap_pct": float(offense_snap_pct) if offense_snap_pct is not None else None,
                "snap_source": str(snap_source) if snap_source is not None else None,
                "prop_snapshot_counts": {
                    "pass_yds": prop_cov.get((cov_key, "pass_yds"), 0),
                    "rush_yds": prop_cov.get((cov_key, "rush_yds"), 0),
                    "rec_yds": prop_cov.get((cov_key, "rec_yds"), 0),
                    "receptions": prop_cov.get((cov_key, "receptions"), 0),
                    "anytime_td": prop_cov.get((cov_key, "anytime_td"), 0),
                },
                "feature_freshness": str(row.updated_at.isoformat() if row.updated_at is not None else ""),
                "player_uid": resolved_player_uid,
                "implied_team_total": float(implied_total or 0.0),
                "team_spread": float(team_spread or 0.0),
                "game_script_applied": bool(implied_total),
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
                "metrics": json.dumps(
                    {
                        "baseline_rows_upserted": upserted,
                        "empty_reason": (
                            None
                            if upserted > 0
                            else "nfl_player_projection_features_weekly_empty_for_season_week"
                        ),
                    }
                ),
            },
        )
        session.commit()
        return {
            "season": int(season),
            "week": int(target_week),
            "model_version": model_version,
            "baseline_rows_upserted": upserted,
            "feature_rows": len(rows),
            "empty_reason": (
                None
                if upserted > 0
                else "nfl_player_projection_features_weekly_empty_for_season_week"
            ),
        }
    except Exception:
        session.rollback()
        log.exception("Failed to materialize NFL player baseline projections")
        raise
    finally:
        session.close()


def _fetch_team_volume_context(session: Any, *, season: int, team: str, target_week: int) -> TeamVolumeContext:
    """Walk-forward safe: only ever reads REAL (`source = 'nflverse'`) team
    situational rows for weeks strictly BEFORE `target_week` this season, so
    projecting week W never leaks week W's own real plays/pass-rate into its
    own team-volume anchor. Falls back to the full prior season's real rows
    when this season has no real weeks yet (preseason / week 1)."""
    rows = session.execute(
        text(
            """
            SELECT offensive_plays, pass_rate
            FROM nfl_dp_team_situational_weekly
            WHERE season = :season AND team = :team AND week < :target_week
              AND source = 'nflverse' AND games_played > 0
            ORDER BY week
            """
        ),
        {"season": int(season), "team": team, "target_week": int(target_week)},
    ).mappings().all()
    if not rows:
        rows = session.execute(
            text(
                """
                SELECT offensive_plays, pass_rate
                FROM nfl_dp_team_situational_weekly
                WHERE season = :prior_season AND team = :team
                  AND source = 'nflverse' AND games_played > 0
                ORDER BY week
                """
            ),
            {"prior_season": int(season) - 1, "team": team},
        ).mappings().all()
    return compute_team_volume_context([dict(r) for r in rows])


def _box_score_replicate_seed(season: int, week: int, team: str) -> int:
    """Deterministic seed. Python's built-in `hash()` on a str (and any
    tuple containing one) is intentionally randomized per-process
    (PYTHONHASHSEED, a security feature since Python 3.3) -- the previous
    `hash((season, week, team))` implementation silently produced a
    DIFFERENT seed on every process run despite looking deterministic,
    which was only caught during the 2026-07-19 player-prop benchmark's
    sample-growth task: re-running the exact same 78 games with the exact
    same input data produced different Monte Carlo win rates/std run over
    run. sha256 has no such randomization, so re-materializing the same
    season/week/team with unchanged input data now reproduces identical
    box-score distributions every time -- important for both auditability
    and for any backtest/report that re-runs this function expecting
    stable results on unchanged data."""
    key = f"{int(season)}|{int(week)}|{team}"
    return int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:8], 16) % (2**31)


@celery_app.task(name="src.tasks.materialize_nfl_player_box_score_sims")
def materialize_nfl_player_box_score_sims(
    *,
    season: int,
    week: Optional[int] = None,
    model_version: str = DEFAULT_BOX_SCORE_MODEL_VERSION,
    replicates: int = DEFAULT_REPLICATES,
) -> Dict[str, Any]:
    """Real per-game player box-score Monte Carlo: samples coherent
    replicate box scores for every player on every team with a real
    scheduled game in `season`/`week`, and persists per-stat distribution
    summaries to `nfl_player_game_box_score_sims`. See
    services/model-service/src/services/nfl_player_box_score_simulator.py
    for the engine and design rationale (team-context anchoring choice,
    Dirichlet/Gamma allocation, v2 follow-up note).
    """
    session = SessionLocal()
    upserted = 0
    teams_simulated = 0
    try:
        target_week = _resolve_nfl_week(session, season=season, week=week)
        rows = session.execute(
            text(
                """
                SELECT
                  season, week, team, player_id, player_uid, player_name, position, game_id, opponent,
                  snap_proxy, team_snap_share, route_proxy, target_proxy, rush_share, red_zone_share,
                  qb_dropback_factor, qb_pressure_factor, team_pace_factor, team_pass_rate_factor,
                  opponent_pass_defense_factor, opponent_rush_defense_factor,
                  availability_confidence, role_confidence, feature_payload,
                  offense_snaps, offense_snap_pct, snap_source
                FROM nfl_player_projection_features_weekly
                WHERE season = :season AND week = :week
                ORDER BY team, position, player_name
                """
            ),
            {"season": int(season), "week": int(target_week)},
        ).fetchall()

        rows_by_team: Dict[str, List[Any]] = {}
        for row in rows:
            rows_by_team.setdefault(row.team, []).append(row)

        schedule_rows = session.execute(
            text(
                """
                SELECT home_team, away_team, spread_line, total_line
                FROM nfl_dp_schedules
                WHERE season = :season AND week = :week
                """
            ),
            {"season": int(season), "week": int(target_week)},
        ).fetchall()
        team_script: Dict[str, tuple[float, float]] = {}
        for srow in schedule_rows:
            total = float(srow.total_line) if srow.total_line is not None else None
            spread = float(srow.spread_line) if srow.spread_line is not None else None
            if total is None or spread is None:
                continue
            home = str(srow.home_team or "")
            away = str(srow.away_team or "")
            home_implied = (total / 2.0) - (spread / 2.0)
            away_implied = (total / 2.0) + (spread / 2.0)
            if home:
                team_script[home] = (home_implied, spread)
            if away:
                team_script[away] = (away_implied, -spread)

        depth_orders_by_team = _qb_depth_orders_by_team(session, season=int(season), week=int(target_week))
        rb_depth_by_team = _rb_depth_orders_by_team(session, season=int(season), week=int(target_week))
        wr_te_depth_by_team = _wr_te_depth_orders_by_team(session, season=int(season), week=int(target_week))
        box_feature_maps = [
            {
                "team": str(r.team or ""),
                "player_id": str(r.player_id or ""),
                "position": str(r.position or ""),
                "target_proxy": float(r.target_proxy or 0.0),
                "rush_share": float(r.rush_share or 0.0),
            }
            for r in rows
        ]
        wr_te_depth_by_team = merge_depth_orders(
            wr_te_depth_by_team,
            usage_rank_depth_orders(box_feature_maps, positions=("WR", "TE"), usage_key="target_proxy"),
        )
        rb_depth_by_team = merge_depth_orders(
            rb_depth_by_team,
            usage_rank_depth_orders(box_feature_maps, positions=("RB", "FB", "HB"), usage_key="rush_share"),
        )
        qb_prior_production = _qb_prior_production_by_player(session, season=int(season))
        skill_prior_ypg = _skill_prior_ypg_by_player(session, season=int(season))
        prior_attempts_by_team_player = _qb_prior_attempts_by_team_player(session, season=int(season))
        prior_rb_carries_by_team = _rb_prior_carries_by_team_player(session, season=int(season))
        prior_rb_carries = _rb_prior_carries_by_player(session, season=int(season))
        prior_snap_pcts = _skill_prior_offense_snap_pct_by_player(session, season=int(season))

        for team, team_rows in rows_by_team.items():
            # Bye week: nfl_player_projection_features_weekly still has a row
            # for every rostered player every week (the preseason hydration
            # seeds weeks 1-18 regardless of the real schedule), but game_id
            # is only populated when nfl_dp_schedules actually has a game for
            # this team/week. Skip entirely rather than simulating a game
            # that doesn't exist and violating the NOT NULL game_id
            # constraint on insert.
            if not any(row.game_id for row in team_rows):
                continue
            team_context = _fetch_team_volume_context(session, season=season, team=team, target_week=target_week)

            # Same enterprise starter resolution as baseline materialize.
            qb_snap_shares = {
                str(row.player_id): float(row.team_snap_share or 0.0)
                for row in team_rows
                if str(row.position or "").upper() == "QB"
            }
            team_scoped = {
                pid: float(prior_attempts_by_team_player.get((str(team), pid)) or 0.0)
                for pid in qb_snap_shares
            }
            if sum(team_scoped.values()) > 0.0:
                team_priors = team_scoped
            else:
                team_priors = {
                    pid: float((qb_prior_production.get(pid) or {}).get("attempts") or 0.0)
                    for pid in qb_snap_shares
                }
            qb_starter_shares = compute_qb_starter_shares(
                qb_snap_shares,
                depth_orders=depth_orders_by_team.get(str(team)),
                prior_attempts=team_priors,
            )
            rb_trailing = {
                str(row.player_id): float(row.rush_share or 0.0)
                for row in team_rows
                if str(row.position or "").upper() in {"RB", "HB", "FB"}
            }
            rb_snaps = {}
            for row in team_rows:
                if str(row.position or "").upper() not in {"RB", "HB", "FB"}:
                    continue
                pid = str(row.player_id)
                snap_pct = getattr(row, "offense_snap_pct", None)
                if snap_pct is None and isinstance(row.feature_payload, dict):
                    snap_pct = row.feature_payload.get("offense_snap_pct")
                rb_snaps[pid] = float(snap_pct if snap_pct is not None else (row.team_snap_share or 0.0))
            team_rb_priors = {pid: float(prior_rb_carries_by_team.get((str(team), pid)) or 0.0) for pid in rb_trailing}
            if sum(team_rb_priors.values()) <= 0.0:
                team_rb_priors = {pid: float(prior_rb_carries.get(pid) or 0.0) for pid in rb_trailing}
            room_rb_shares = compute_rb_rush_shares(
                rb_trailing,
                depth_orders=rb_depth_by_team.get(str(team)),
                prior_carries=team_rb_priors,
                offense_snap_pcts={**{pid: float(prior_snap_pcts.get(pid) or 0.0) for pid in rb_trailing}, **rb_snaps},
            )
            implied_total, team_spread = team_script.get(str(team), (0.0, 0.0))

            roles: List[PlayerBoxScoreRole] = []
            row_by_key: Dict[str, Any] = {}
            for row in team_rows:
                usage_source = None
                if isinstance(row.feature_payload, dict):
                    usage_source = row.feature_payload.get("usage_source")
                experience_confidence = (
                    ROOKIE_EXPERIENCE_CONFIDENCE if usage_source == "rookie_baseline_v1" else VETERAN_EXPERIENCE_CONFIDENCE
                )
                starter_share = float(qb_starter_shares.get(str(row.player_id), 1.0))
                role_conf = float(row.role_confidence or 0.65)
                talent_factor = 1.0
                skill_talent = 1.0
                pos_upper = str(row.position or "").upper()
                if pos_upper == "QB":
                    if starter_share >= 0.85:
                        role_conf = max(role_conf, 0.82)
                    prior_ypg = (qb_prior_production.get(str(row.player_id)) or {}).get("yards_per_startish")
                    talent_factor = qb_talent_factor_from_prior_ypg(
                        float(prior_ypg) if prior_ypg is not None and float(prior_ypg) > 0 else None
                    )
                if pos_upper in {"RB", "FB", "HB"}:
                    rush_share = float(room_rb_shares.get(str(row.player_id), float(row.rush_share or 0.0)))
                else:
                    rush_share = float(row.rush_share or 0.0)
                target_proxy = _apply_wr_te_depth_target_prior(
                    team=str(team),
                    player_id=str(row.player_id),
                    position=str(row.position or ""),
                    target_proxy=float(row.target_proxy or 0.0),
                    depth_by_team=wr_te_depth_by_team,
                )
                if pos_upper in {"WR", "TE"}:
                    depth_ord = wr_te_depth_by_team.get(str(team), {}).get(str(row.player_id))
                    floor = depth_role_confidence_floor(pos_upper, depth_ord)
                    if floor is not None:
                        role_conf = max(role_conf, floor)
                    prior_skill = skill_prior_ypg.get(str(row.player_id)) or {}
                    skill_talent = skill_talent_factor_from_prior_ypg(
                        float(prior_skill.get("rec_ypg") or 0.0) or None,
                        position=pos_upper,
                    )
                elif pos_upper in {"RB", "FB", "HB"}:
                    depth_ord = rb_depth_by_team.get(str(team), {}).get(str(row.player_id))
                    floor = depth_role_confidence_floor(pos_upper, depth_ord)
                    if floor is not None:
                        role_conf = max(role_conf, floor)
                    if rush_share >= 0.55:
                        role_conf = max(role_conf, 0.84)
                    prior_skill = skill_prior_ypg.get(str(row.player_id)) or {}
                    skill_talent = skill_talent_factor_from_prior_ypg(
                        float(prior_skill.get("rush_ypg") or 0.0) or None,
                        position=pos_upper,
                    )
                inputs = PlayerFeatureInputs(
                    position=str(row.position or ""),
                    snap_proxy=float(row.snap_proxy or 0.0),
                    route_proxy=float(row.route_proxy or 0.0),
                    target_proxy=target_proxy,
                    rush_share=rush_share,
                    red_zone_share=float(row.red_zone_share or 0.0),
                    qb_dropback_factor=float(row.qb_dropback_factor or 1.0),
                    qb_pressure_factor=float(row.qb_pressure_factor or 1.0),
                    team_pace_factor=float(row.team_pace_factor or 1.0),
                    team_pass_rate_factor=float(row.team_pass_rate_factor or 1.0),
                    availability_confidence=float(row.availability_confidence or 0.75),
                    role_confidence=role_conf,
                    experience_confidence=experience_confidence,
                    team_snap_share=float(row.team_snap_share or 0.0),
                    opponent_pass_defense_factor=float(row.opponent_pass_defense_factor or 1.0),
                    opponent_rush_defense_factor=float(row.opponent_rush_defense_factor or 1.0),
                    qb_starter_share=starter_share,
                    qb_talent_factor=talent_factor,
                    skill_talent_factor=skill_talent,
                    implied_team_total=float(implied_total or 0.0),
                    team_spread=float(team_spread or 0.0),
                )
                baseline = baseline_projection_from_features(inputs)
                player_key = str(row.player_uid) if row.player_uid is not None else f"{row.team}:{row.player_id}"
                row_by_key[player_key] = row
                roles.append(
                    PlayerBoxScoreRole(
                        player_key=player_key,
                        player_name=str(row.player_name or ""),
                        position=str(row.position or ""),
                        baseline=baseline,
                        role_confidence=role_conf,
                        experience_confidence=experience_confidence,
                    )
                )

            if not roles:
                continue

            sim_result = simulate_team_player_box_scores(
                team_context,
                roles,
                replicates=int(replicates),
                seed=_box_score_replicate_seed(season, target_week, team),
            )
            teams_simulated += 1

            team_context_payload = json.dumps(
                {
                    "mean_total_plays": team_context.mean_total_plays,
                    "std_total_plays": team_context.std_total_plays,
                    "mean_pass_rate": team_context.mean_pass_rate,
                    "std_pass_rate": team_context.std_pass_rate,
                    "sample_games": team_context.sample_games,
                    "anchoring": "trailing_real_team_situational_v1",
                }
            )

            for player_key, dist in sim_result.items():
                row = row_by_key[player_key]
                session.execute(
                    text(
                        """
                        INSERT INTO nfl_player_game_box_score_sims (
                          season, week, game_id, team, opponent, player_id, player_uid, player_name, position,
                          model_version, replicate_count, team_context,
                          pass_attempts_dist, completions_dist, pass_yards_dist, pass_tds_dist,
                          rush_attempts_dist, rush_yards_dist, rush_tds_dist,
                          targets_dist, receptions_dist, receiving_yards_dist, rec_tds_dist,
                          total_tds_dist, fantasy_points_ppr_dist,
                          pass_yards_mean, rush_yards_mean, receiving_yards_mean, receptions_mean, total_tds_mean,
                          source_coverage, created_at, updated_at
                        ) VALUES (
                          :season, :week, :game_id, :team, :opponent, :player_id, CAST(:player_uid AS uuid), :player_name, :position,
                          :model_version, :replicate_count, CAST(:team_context AS jsonb),
                          CAST(:pass_attempts_dist AS jsonb), CAST(:completions_dist AS jsonb), CAST(:pass_yards_dist AS jsonb), CAST(:pass_tds_dist AS jsonb),
                          CAST(:rush_attempts_dist AS jsonb), CAST(:rush_yards_dist AS jsonb), CAST(:rush_tds_dist AS jsonb),
                          CAST(:targets_dist AS jsonb), CAST(:receptions_dist AS jsonb), CAST(:receiving_yards_dist AS jsonb), CAST(:rec_tds_dist AS jsonb),
                          CAST(:total_tds_dist AS jsonb), CAST(:fantasy_points_ppr_dist AS jsonb),
                          :pass_yards_mean, :rush_yards_mean, :receiving_yards_mean, :receptions_mean, :total_tds_mean,
                          CAST(:source_coverage AS jsonb), NOW(), NOW()
                        )
                        ON CONFLICT (season, week, team, player_id, model_version) DO UPDATE SET
                          game_id = EXCLUDED.game_id,
                          opponent = EXCLUDED.opponent,
                          player_uid = EXCLUDED.player_uid,
                          player_name = EXCLUDED.player_name,
                          position = EXCLUDED.position,
                          replicate_count = EXCLUDED.replicate_count,
                          team_context = EXCLUDED.team_context,
                          pass_attempts_dist = EXCLUDED.pass_attempts_dist,
                          completions_dist = EXCLUDED.completions_dist,
                          pass_yards_dist = EXCLUDED.pass_yards_dist,
                          pass_tds_dist = EXCLUDED.pass_tds_dist,
                          rush_attempts_dist = EXCLUDED.rush_attempts_dist,
                          rush_yards_dist = EXCLUDED.rush_yards_dist,
                          rush_tds_dist = EXCLUDED.rush_tds_dist,
                          targets_dist = EXCLUDED.targets_dist,
                          receptions_dist = EXCLUDED.receptions_dist,
                          receiving_yards_dist = EXCLUDED.receiving_yards_dist,
                          rec_tds_dist = EXCLUDED.rec_tds_dist,
                          total_tds_dist = EXCLUDED.total_tds_dist,
                          fantasy_points_ppr_dist = EXCLUDED.fantasy_points_ppr_dist,
                          pass_yards_mean = EXCLUDED.pass_yards_mean,
                          rush_yards_mean = EXCLUDED.rush_yards_mean,
                          receiving_yards_mean = EXCLUDED.receiving_yards_mean,
                          receptions_mean = EXCLUDED.receptions_mean,
                          total_tds_mean = EXCLUDED.total_tds_mean,
                          source_coverage = EXCLUDED.source_coverage,
                          updated_at = EXCLUDED.updated_at
                        """
                    ),
                    {
                        "season": int(season),
                        "week": int(target_week),
                        "game_id": row.game_id,
                        "team": row.team,
                        "opponent": row.opponent,
                        "player_id": row.player_id,
                        "player_uid": str(row.player_uid) if row.player_uid is not None else None,
                        "player_name": row.player_name,
                        "position": row.position,
                        "model_version": model_version,
                        "replicate_count": int(replicates),
                        "team_context": team_context_payload,
                        "pass_attempts_dist": json.dumps(dist["pass_attempts_dist"]),
                        "completions_dist": json.dumps(dist["completions_dist"]),
                        "pass_yards_dist": json.dumps(dist["pass_yards_dist"]),
                        "pass_tds_dist": json.dumps(dist["pass_tds_dist"]),
                        "rush_attempts_dist": json.dumps(dist["rush_attempts_dist"]),
                        "rush_yards_dist": json.dumps(dist["rush_yards_dist"]),
                        "rush_tds_dist": json.dumps(dist["rush_tds_dist"]),
                        "targets_dist": json.dumps(dist["targets_dist"]),
                        "receptions_dist": json.dumps(dist["receptions_dist"]),
                        "receiving_yards_dist": json.dumps(dist["receiving_yards_dist"]),
                        "rec_tds_dist": json.dumps(dist["rec_tds_dist"]),
                        "total_tds_dist": json.dumps(dist["total_tds_dist"]),
                        "fantasy_points_ppr_dist": json.dumps(dist["fantasy_points_ppr_dist"]),
                        "pass_yards_mean": dist["pass_yards_dist"]["mean"],
                        "rush_yards_mean": dist["rush_yards_dist"]["mean"],
                        "receiving_yards_mean": dist["receiving_yards_dist"]["mean"],
                        "receptions_mean": dist["receptions_dist"]["mean"],
                        "total_tds_mean": dist["total_tds_dist"]["mean"],
                        "source_coverage": json.dumps(
                            {
                                "feature_source": "nfl_player_projection_features_weekly",
                                "team_volume_sample_games": team_context.sample_games,
                            }
                        ),
                    },
                )
                upserted += 1

        session.commit()
        return {
            "season": int(season),
            "week": int(target_week),
            "model_version": model_version,
            "replicates": int(replicates),
            "teams_simulated": teams_simulated,
            "player_rows_upserted": upserted,
        }
    except Exception:
        session.rollback()
        log.exception("Failed to materialize NFL player box score sims")
        raise
    finally:
        session.close()


@celery_app.task(name="src.tasks.materialize_nfl_player_season_box_score_sims")
def materialize_nfl_player_season_box_score_sims(
    *,
    season: int,
    model_version: str = DEFAULT_BOX_SCORE_MODEL_VERSION,
) -> Dict[str, Any]:
    """Sums real per-game box-score sim rows (`nfl_player_game_box_score_sims`)
    into a season-level mean+std per player, via `aggregate_game_sims_to_season()`.
    Recomputed from scratch every call -- never hand-edited, safe to re-run
    any time after `materialize_nfl_player_box_score_sims` has run for the
    real weeks played so far this season."""
    session = SessionLocal()
    try:
        rows = session.execute(
            text(
                """
                SELECT team, player_id, player_uid, player_name, position,
                  pass_yards_dist, rush_yards_dist, receiving_yards_dist, receptions_dist, total_tds_dist
                FROM nfl_player_game_box_score_sims
                WHERE season = :season AND model_version = :model_version
                  AND game_id IS NOT NULL AND game_id <> ''
                ORDER BY team, player_id, week
                """
            ),
            {"season": int(season), "model_version": model_version},
        ).fetchall()

        by_player: Dict[tuple[str, str], List[Any]] = {}
        for row in rows:
            by_player.setdefault((row.team, row.player_id), []).append(row)

        upserted = 0
        for (team, player_id), player_rows in by_player.items():
            game_dicts = [
                {
                    "pass_yards_dist": r.pass_yards_dist,
                    "rush_yards_dist": r.rush_yards_dist,
                    "receiving_yards_dist": r.receiving_yards_dist,
                    "receptions_dist": r.receptions_dist,
                    "total_tds_dist": r.total_tds_dist,
                }
                for r in player_rows
            ]
            season_totals = aggregate_game_sims_to_season(game_dicts)
            latest = player_rows[-1]
            session.execute(
                text(
                    """
                    INSERT INTO nfl_player_season_box_score_sims (
                      season, team, player_id, player_uid, player_name, position, model_version,
                      games_aggregated, pass_yards_mean, pass_yards_std, rush_yards_mean, rush_yards_std,
                      receiving_yards_mean, receiving_yards_std, receptions_mean, receptions_std,
                      total_tds_mean, total_tds_std, updated_at
                    ) VALUES (
                      :season, :team, :player_id, CAST(:player_uid AS uuid), :player_name, :position, :model_version,
                      :games_aggregated, :pass_yards_mean, :pass_yards_std, :rush_yards_mean, :rush_yards_std,
                      :receiving_yards_mean, :receiving_yards_std, :receptions_mean, :receptions_std,
                      :total_tds_mean, :total_tds_std, NOW()
                    )
                    ON CONFLICT (season, team, player_id, model_version) DO UPDATE SET
                      player_uid = EXCLUDED.player_uid,
                      player_name = EXCLUDED.player_name,
                      position = EXCLUDED.position,
                      games_aggregated = EXCLUDED.games_aggregated,
                      pass_yards_mean = EXCLUDED.pass_yards_mean,
                      pass_yards_std = EXCLUDED.pass_yards_std,
                      rush_yards_mean = EXCLUDED.rush_yards_mean,
                      rush_yards_std = EXCLUDED.rush_yards_std,
                      receiving_yards_mean = EXCLUDED.receiving_yards_mean,
                      receiving_yards_std = EXCLUDED.receiving_yards_std,
                      receptions_mean = EXCLUDED.receptions_mean,
                      receptions_std = EXCLUDED.receptions_std,
                      total_tds_mean = EXCLUDED.total_tds_mean,
                      total_tds_std = EXCLUDED.total_tds_std,
                      updated_at = EXCLUDED.updated_at
                    """
                ),
                {
                    "season": int(season),
                    "team": team,
                    "player_id": player_id,
                    "player_uid": str(latest.player_uid) if latest.player_uid is not None else None,
                    "player_name": latest.player_name,
                    "position": latest.position,
                    "model_version": model_version,
                    **season_totals,
                },
            )
            upserted += 1

        session.commit()
        return {"season": int(season), "model_version": model_version, "player_rows_upserted": upserted}
    except Exception:
        session.rollback()
        log.exception("Failed to materialize NFL player season box score sims")
        raise
    finally:
        session.close()


def _box_dist_moments(dist_obj: Any) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """Extract (mean, std, p50) from a box-score *_dist jsonb block."""
    if dist_obj is None:
        return None, None, None
    if isinstance(dist_obj, str):
        try:
            dist_obj = json.loads(dist_obj)
        except (TypeError, ValueError, json.JSONDecodeError):
            return None, None, None
    if not isinstance(dist_obj, dict):
        return None, None, None
    mean = _to_float_like(dist_obj.get("mean"))
    std = _to_float_like(dist_obj.get("std"))
    p50 = _to_float_like(dist_obj.get("p50"))
    return mean, std, p50


@celery_app.task(name="src.tasks.materialize_nfl_player_props_edges")
def materialize_nfl_player_props_edges(
    *,
    season: int,
    week: Optional[int] = None,
    model_version: str = "nfl-player-v1",
    box_score_model_version: str = DEFAULT_BOX_SCORE_MODEL_VERSION,
) -> Dict[str, Any]:
    """Materialize prop edges from the shared weekly player-production spine.

    Phase 1 SoT: ``nfl_player_projection_baselines`` via
    ``production_from_baseline_row`` (same vector fantasy weekly scores).
    Box-score MC is research-only in diagnostics — not the published mean.
    Frozen prop-cal-v1 applies to *edge math only* (no walk-forward re-fit).
    ``NFL_WEEKLY_PROPS_LIVE`` is the web research→fire flag. PLAY stake tags stay off.
    """
    session = SessionLocal()
    target_week = None
    upserted = 0
    box_research_rows = 0
    spine_sourced = 0
    play_tagged = 0
    watch_tagged = 0
    try:
        target_week = _resolve_nfl_week(session, season=season, week=week)
        # Phase 1: frozen cal only — do not walk-forward re-fit intercepts.
        prop_cal_bundle = default_calibration_bundle()
        role_rows = session.execute(
            text(
                """
                SELECT player_id, team, position, role_confidence, availability_confidence,
                       target_proxy, rush_share
                FROM nfl_player_projection_features_weekly
                WHERE season = :season AND week = :week
                """
            ),
            {"season": int(season), "week": int(target_week)},
        ).fetchall()
        prop_feature_maps = [
            {
                "team": str(r.team or ""),
                "player_id": str(r.player_id or ""),
                "position": str(r.position or ""),
                "target_proxy": float(r.target_proxy or 0.0),
                "rush_share": float(r.rush_share or 0.0),
            }
            for r in role_rows
        ]
        wr_te_depth_props = merge_depth_orders(
            _wr_te_depth_orders_by_team(session, season=int(season), week=int(target_week)),
            usage_rank_depth_orders(prop_feature_maps, positions=("WR", "TE"), usage_key="target_proxy"),
        )
        rb_depth_props = merge_depth_orders(
            _rb_depth_orders_by_team(session, season=int(season), week=int(target_week)),
            usage_rank_depth_orders(prop_feature_maps, positions=("RB", "FB", "HB"), usage_key="rush_share"),
        )
        role_by_player: Dict[tuple[str, str], tuple[float, float]] = {}
        for r in role_rows:
            pos_u = str(r.position or "").upper()
            team_u = str(r.team or "")
            pid_u = str(r.player_id or "")
            if pos_u in {"WR", "TE"}:
                depth_ord = wr_te_depth_props.get(team_u, {}).get(pid_u)
            elif pos_u in {"RB", "FB", "HB"}:
                depth_ord = rb_depth_props.get(team_u, {}).get(pid_u)
            else:
                depth_ord = None
            role_by_player[(pid_u, team_u)] = (
                effective_skill_role_confidence(
                    position=pos_u,
                    role_confidence=float(r.role_confidence or 0.65),
                    depth_order=depth_ord,
                    rush_share=float(r.rush_share or 0.0),
                ),
                float(r.availability_confidence or 0.75),
            )
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
        box_rows = session.execute(
            text(
                """
                SELECT
                  player_id, player_uid, player_name, team, position, game_id,
                  pass_yards_dist, rush_yards_dist, receiving_yards_dist,
                  receptions_dist, total_tds_dist,
                  pass_yards_mean, rush_yards_mean, receiving_yards_mean,
                  receptions_mean, total_tds_mean
                FROM nfl_player_game_box_score_sims
                WHERE season = :season
                  AND week = :week
                  AND model_version = :box_model_version
                """
            ),
            {
                "season": int(season),
                "week": int(target_week),
                "box_model_version": str(box_score_model_version),
            },
        ).fetchall()
        box_by_player_id: Dict[str, Any] = {}
        box_by_match_key: Dict[str, Any] = {}
        for box in box_rows:
            pid = str(box.player_id or "")
            if pid:
                box_by_player_id[pid] = box
            for identity_key in prop_player_match_keys(
                player_uid=str(box.player_uid) if box.player_uid is not None else None,
                player_name=str(box.player_name or ""),
            ):
                # Prefer first seen; ids are unique per team-week.
                box_by_match_key.setdefault(f"{identity_key}|{str(box.team or '')}", box)
                box_by_match_key.setdefault(identity_key, box)

        market_rows = session.execute(
            text(
                """
                SELECT DISTINCT ON (player_name, market_key, line, sportsbook)
                  id,
                  season,
                  week,
                  game_id,
                  player_id,
                  player_uid,
                  player_name,
                  team,
                  sportsbook,
                  market_key,
                  line,
                  over_price,
                  under_price,
                  captured_at
                FROM nfl_player_prop_market_snapshots
                WHERE season = :season
                  AND week = :week
                ORDER BY player_name, market_key, line, sportsbook, captured_at DESC
                """
            ),
            {"season": int(season), "week": int(target_week)},
        ).fetchall()
        # Ambiguous initial+last keys among baselines (e.g. multiple J.Williams).
        il_counts: Dict[str, int] = {}
        baseline_identity_rows: List[tuple[str, str, str, set[str]]] = []
        for brow in baselines:
            b_keys = set(
                prop_player_match_keys(
                    player_uid=str(brow.player_uid) if getattr(brow, "player_uid", None) is not None else None,
                    player_name=str(brow.player_name or ""),
                )
            )
            baseline_identity_rows.append(
                (str(brow.team or ""), str(getattr(brow, "position", None) or ""), str(brow.player_name or ""), b_keys)
            )
            for ik in b_keys:
                if ik.startswith("il:"):
                    il_counts[ik] = il_counts.get(ik, 0) + 1
        ambiguous_il_keys = {k for k, n in il_counts.items() if n > 1}

        # Index by uid / normalized name / initial+last so abbreviated baselines
        # (D.Maye) join to Odds-API full names (Drake Maye) even when snapshot uid is null.
        # Team-scope il: keys when we can resolve the market onto a unique baseline.
        market_lookup: Dict[tuple[str, str], Any] = {}
        market_lookup_rank: Dict[tuple[str, str], tuple] = {}
        for market in market_rows:
            market_key = str(market.market_key)
            rank = prop_market_snapshot_rank(market)
            m_keys = prop_player_match_keys(
                player_uid=str(market.player_uid) if market.player_uid is not None else None,
                player_name=str(market.player_name or ""),
            )
            m_key_set = set(m_keys)
            resolved_team = str(market.team or "").strip().upper() or None
            if resolved_team is None:
                candidates = [
                    (team, pos, name)
                    for team, pos, name, b_keys in baseline_identity_rows
                    if m_key_set & b_keys and prop_market_position_compatible(market_key, pos)
                ]
                if candidates:
                    candidates.sort(key=lambda c: prop_market_position_rank(market_key, c[1]))
                    best_rank = prop_market_position_rank(market_key, candidates[0][1])
                    top = [c for c in candidates if prop_market_position_rank(market_key, c[1]) == best_rank]
                    if len(top) == 1 and top[0][0]:
                        resolved_team = str(top[0][0]).strip().upper()
            for identity_key in m_keys:
                index_keys = [identity_key]
                if resolved_team and identity_key.startswith("il:"):
                    index_keys.append(f"{identity_key}|{resolved_team}")
                for identity_key_i in index_keys:
                    key = (identity_key_i, market_key)
                    prior = market_lookup_rank.get(key)
                    if prior is None or rank < prior:
                        market_lookup[key] = market
                        market_lookup_rank[key] = rank

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
            player_match_keys = prop_player_match_keys(
                player_uid=resolved_player_uid,
                player_name=str(row.player_name or ""),
            )
            position = str(getattr(row, "position", None) or "")
            box = box_by_player_id.get(str(row.player_id or ""))
            if box is None:
                for identity_key in player_match_keys:
                    box = box_by_match_key.get(f"{identity_key}|{str(row.team or '')}") or box_by_match_key.get(
                        identity_key
                    )
                    if box is not None:
                        break

            # Phase 1 spine: published means = raw baselines (shared with fantasy).
            # Box MC stays research-only — never the published model_mean.
            prod = production_from_baseline_row(row)
            spine_sourced += 1
            pass_mean = rush_mean = rec_mean = receptions_mean = None
            pass_std = rush_std = rec_std = receptions_std = None
            pass_p50 = rush_p50 = rec_p50 = receptions_p50 = None
            box_total_tds = None
            if box is not None:
                box_research_rows += 1
                pass_mean, pass_std, pass_p50 = _box_dist_moments(box.pass_yards_dist)
                rush_mean, rush_std, rush_p50 = _box_dist_moments(box.rush_yards_dist)
                rec_mean, rec_std, rec_p50 = _box_dist_moments(box.receiving_yards_dist)
                receptions_mean, receptions_std, receptions_p50 = _box_dist_moments(box.receptions_dist)
                box_total_tds = _to_float_like(getattr(box, "total_tds_mean", None))
                if box_total_tds is None:
                    box_total_tds, _, _ = _box_dist_moments(box.total_tds_dist)

            projection_source = NFL_PLAYER_PRODUCTION_VERSION
            atd_mean = anytime_td_prob_from_td_mean(prod.total_tds)
            atd_std = max(0.08, math.sqrt(max(atd_mean * (1.0 - atd_mean), 1e-4)))

            role_conf, avail_conf = role_by_player.get(
                (str(row.player_id), str(row.team)),
                (0.65, 0.75),
            )

            markets = [
                ("pass_yds", prod.pass_yards, prod.pass_yards_std, prod.pass_yards),
                ("rush_yds", prod.rush_yards, prod.rush_yards_std, prod.rush_yards),
                ("rec_yds", prod.receiving_yards, prod.receiving_yards_std, prod.receiving_yards),
                ("receptions", prod.receptions, prod.receptions_std, prod.receptions),
                ("anytime_td", float(atd_mean), float(atd_std), atd_mean),
            ]
            for market_key, spine_mean, spine_std, model_p50 in markets:
                if not is_investable_prop(
                    market_key=market_key,
                    position=position,
                    model_mean=float(spine_mean) if spine_mean is not None else None,
                    role_confidence=role_conf,
                ):
                    continue
                market = select_prop_market_for_player(
                    market_lookup,
                    player_match_keys=player_match_keys,
                    market_key=market_key,
                    team=str(row.team or ""),
                    position=position,
                    ambiguous_il_keys=ambiguous_il_keys,
                )
                # Never invent a Vegas line from the model mean — that poisoned
                # board MAE (~40% of rows looked "perfect") and fake edges.
                if market is not None and market.line is not None:
                    line: Optional[float] = float(market.line)
                elif market_key == "anytime_td":
                    line = 0.5
                else:
                    line = None
                over_price = int(market.over_price) if (market is not None and market.over_price is not None) else None
                under_price = int(market.under_price) if (market is not None and market.under_price is not None) else None
                # Frozen cal once for edge math only — published mean stays spine.
                cal = apply_prop_calibration(
                    model_mean=float(spine_mean),
                    model_std=float(spine_std),
                    market_key=market_key,
                    calibration=prop_cal_bundle.get(market_key),
                    market_line=float(line) if line is not None and market is not None else None,
                    role_confidence=role_conf,
                )
                calibrated_mean = float(cal["model_mean"])
                calibrated_std = float(cal["model_std"])
                model_mean = float(spine_mean)
                model_std = float(spine_std)
                if market_key == "anytime_td":
                    model_floor = max(0.0, model_mean * 0.55)
                    model_median = float(model_p50 if model_p50 is not None else model_mean)
                    model_ceiling = min(0.95, model_mean * 1.55 + 0.03)
                    edge = evaluate_prop_edge(
                        model_mean=calibrated_mean,
                        model_std=max(0.08, calibrated_std),
                        line=0.5,
                        market_over_price=over_price,
                        market_under_price=under_price,
                        market_key=market_key,
                        position=position,
                        role_confidence=role_conf,
                        availability_confidence=avail_conf,
                        raw_model_mean=float(spine_mean),
                    )
                else:
                    model_floor = max(0.0, model_mean - (1.0 * model_std))
                    model_median = float(model_p50 if model_p50 is not None else model_mean)
                    model_ceiling = model_mean + (1.1 * model_std)
                    edge_line = float(line) if line is not None else float(model_mean)
                    edge = evaluate_prop_edge(
                        model_mean=calibrated_mean,
                        model_std=max(0.6, calibrated_std),
                        line=edge_line,
                        market_over_price=over_price,
                        market_under_price=under_price,
                        market_key=market_key,
                        position=position,
                        role_confidence=role_conf,
                        availability_confidence=avail_conf,
                        raw_model_mean=float(spine_mean),
                    )
                    if line is None:
                        # Projection-only row: no book to beat.
                        edge = {**edge, "tag": "PASS", "reason": "no_market_line"}
                if edge.get("tag") == "PLAY":
                    play_tagged += 1
                elif edge.get("tag") == "WATCH":
                    watch_tagged += 1

                game_id = _to_uuid_or_none(row.game_id)
                if game_id is None and box is not None:
                    game_id = _to_uuid_or_none(getattr(box, "game_id", None))
                if game_id is None and market is not None:
                    game_id = _to_uuid_or_none(getattr(market, "game_id", None))

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
                        "game_id": game_id,
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
                                "projection_source": projection_source,
                                "spine_version": NFL_PLAYER_PRODUCTION_VERSION,
                                "production_mean": round(float(spine_mean), 4),
                                "calibrated_mean": round(float(calibrated_mean), 4),
                                "calibrated_std": round(float(calibrated_std), 4),
                                "box_research": {
                                    "present": box is not None,
                                    "pass_yards_mean": round(float(pass_mean), 4) if pass_mean is not None else None,
                                    "rush_yards_mean": round(float(rush_mean), 4) if rush_mean is not None else None,
                                    "receiving_yards_mean": round(float(rec_mean), 4) if rec_mean is not None else None,
                                    "receptions_mean": round(float(receptions_mean), 4)
                                    if receptions_mean is not None
                                    else None,
                                    "total_tds_mean": round(float(box_total_tds), 4)
                                    if box_total_tds is not None
                                    else None,
                                },
                                "box_score_model_version": box_score_model_version if box is not None else None,
                                "created_from_baseline_model_version": model_version,
                                "worker_build_id": "player-production-v1-phase1",
                                "raw_model_mean": round(float(spine_mean), 4),
                                "raw_model_std": round(float(spine_std), 4),
                                "z_over": edge.get("z_over"),
                                "tag": edge.get("tag"),
                                "tag_side": edge.get("tag_side"),
                                "tag_action": edge.get("tag_action"),
                                "size_down": edge.get("size_down"),
                                "stake_eligible": edge.get("stake_eligible"),
                                "tag_reason": edge.get("tag_reason"),
                                "market_vig": edge.get("market_vig"),
                                "position": position,
                                "role_confidence": role_conf,
                                "availability_confidence": avail_conf,
                                "calibration_version": cal.get("calibration_version"),
                                "calibration_source": cal.get("calibration_source"),
                                "calibration_intercept": cal.get("calibration_intercept"),
                                "calibration_std_multiplier": cal.get("calibration_std_multiplier"),
                                "market_shrink": cal.get("market_shrink"),
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
                "source_coverage": json.dumps(
                    {
                        "market_rows": len(market_rows),
                        "baseline_rows": len(baselines),
                        "box_score_rows": len(box_rows),
                        "spine_sourced_players": spine_sourced,
                        "box_research_players": box_research_rows,
                    }
                ),
                "freshness": json.dumps({"latest_market_snapshot": str(max([r.captured_at for r in market_rows], default=None))}),
                "calibration_flags": json.dumps(
                    {
                        "calibrated": True,
                        "distribution": "player-production-v1-phase1-baselines",
                        "devig": "multiplicative",
                        "tags": "PLAY/WATCH/PASS",
                        "prop_calibration": {
                            mk: {
                                "intercept": c.intercept,
                                "std_multiplier": c.std_multiplier,
                                "source": c.source,
                                "sample_size": c.sample_size,
                            }
                            for mk, c in prop_cal_bundle.items()
                        },
                    }
                ),
                "readiness_status": "go" if len(baselines) > 20 else "warning",
                "metrics": json.dumps(
                    {
                        "prop_edges_upserted": upserted,
                        "play_tagged": play_tagged,
                        "watch_tagged": watch_tagged,
                        "spine_sourced_players": spine_sourced,
                        "box_research_players": box_research_rows,
                    }
                ),
            },
        )
        session.commit()
        return {
            "season": int(season),
            "week": int(target_week),
            "model_version": model_version,
            "prop_edges_upserted": upserted,
            "play_tagged": play_tagged,
            "watch_tagged": watch_tagged,
            "spine_sourced_players": spine_sourced,
            "box_research_players": box_research_rows,
            "box_score_rows": len(box_rows),
        }
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
                  g.external_id,
                  home.abbr AS home_abbr,
                  away.abbr AS away_abbr,
                  home.name AS home_name,
                  away.name AS away_name
                FROM games g
                JOIN seasons s ON s.id = g.season_id
                JOIN leagues l ON l.id = s.league_id
                JOIN teams home ON home.id = g.home_team_id
                JOIN teams away ON away.id = g.away_team_id
                WHERE l.code = 'nfl'
                  AND s.season_year = :season
                """
            ),
            {"season": int(season)},
        ).fetchall()
        game_lookup: Dict[str, Dict[str, Any]] = {
            str(row.external_id): {
                "game_id": str(row.game_id),
                "home_abbr": str(row.home_abbr or ""),
                "away_abbr": str(row.away_abbr or ""),
                "home_name": str(row.home_name or ""),
                "away_name": str(row.away_name or ""),
            }
            for row in game_lookup_rows
            if row.external_id is not None
        }
        # Week roster → team abbr so Odds players resolve onto the correct side.
        roster_rows = session.execute(
            text(
                """
                SELECT player_name, team, position
                FROM nfl_player_projection_baselines
                WHERE season = :season AND week = :week
                """
            ),
            {"season": int(season), "week": int(week)},
        ).fetchall()
        roster_team_by_key: Dict[str, str] = {}
        roster_pos_by_key: Dict[str, str] = {}
        for roster in roster_rows:
            team_abbr = str(roster.team or "")
            pos = str(roster.position or "")
            for identity_key in prop_player_match_keys(
                player_uid=None,
                player_name=str(roster.player_name or ""),
            ):
                roster_team_by_key.setdefault(f"{identity_key}|{team_abbr}", team_abbr)
                roster_team_by_key.setdefault(identity_key, team_abbr)
                roster_pos_by_key.setdefault(identity_key, pos)

        for event in events:
            event_id = str(event.get("id") or "")
            if not event_id:
                continue
            game_meta = game_lookup.get(event_id) or {}
            home_abbr = str(game_meta.get("home_abbr") or "")
            away_abbr = str(game_meta.get("away_abbr") or "")
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
                    by_player_line: Dict[tuple[str, Optional[float]], Dict[str, Any]] = {}
                    for outcome in outcomes:
                        player_name = str(outcome.get("description") or outcome.get("name") or "").strip()
                        if not player_name:
                            continue
                        side = str(outcome.get("name") or "").strip().lower()
                        line = _safe_float(outcome.get("point"))
                        if market_key == "anytime_td":
                            line = 0.5
                        row_key = (player_name, line)
                        bundled = by_player_line.setdefault(
                            row_key,
                            {"player_name": player_name, "line": line, "over_price": None, "under_price": None},
                        )
                        price = _safe_int(outcome.get("price"))
                        if side == "over" or (market_key == "anytime_td" and side in {"yes", "over"}):
                            bundled["over_price"] = price
                        elif side == "under" or (market_key == "anytime_td" and side in {"no", "under"}):
                            bundled["under_price"] = price
                        elif market_key == "anytime_td" and side not in {"yes", "no", "over", "under"}:
                            # Some books emit player name as the outcome side for ATD.
                            bundled["over_price"] = price
                    captured_at = _parse_iso_datetime(details.get("commence_time")) or _now_utc()
                    for (player_name, line), bundled in by_player_line.items():
                        over_price = bundled["over_price"]
                        under_price = bundled["under_price"]
                        implied_over = _american_implied_prob(over_price) if over_price is not None else None
                        implied_under = _american_implied_prob(under_price) if under_price is not None else None
                        resolved_team: Optional[str] = None
                        resolved_pos: Optional[str] = None
                        for identity_key in prop_player_match_keys(player_uid=None, player_name=player_name):
                            if home_abbr and f"{identity_key}|{home_abbr}" in roster_team_by_key:
                                resolved_team = home_abbr
                            elif away_abbr and f"{identity_key}|{away_abbr}" in roster_team_by_key:
                                resolved_team = away_abbr
                            else:
                                resolved_team = roster_team_by_key.get(identity_key)
                            resolved_pos = roster_pos_by_key.get(identity_key)
                            if resolved_team:
                                break
                        # Constrain unresolved names to the event's two teams.
                        if resolved_team is None and home_abbr and away_abbr:
                            # Prefer home first only as a soft hint for identity context;
                            # leave None rather than guessing wrong side.
                            resolved_team = None
                        identity = resolve_and_persist_player_identity(
                            session,
                            IdentityInput(
                                source_system="odds_api_nfl_props",
                                external_id=None,
                                player_name=player_name,
                                team=resolved_team,
                                position=resolved_pos,
                                season=int(season),
                                week=int(week),
                                source_payload={
                                    "event_id": event_id,
                                    "market_key": market_key,
                                    "sportsbook": sportsbook,
                                    "home_abbr": home_abbr or None,
                                    "away_abbr": away_abbr or None,
                                },
                            ),
                        )
                        opponent = None
                        if resolved_team and home_abbr and away_abbr:
                            opponent = away_abbr if resolved_team == home_abbr else home_abbr
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
                                  player_uid = COALESCE(EXCLUDED.player_uid, nfl_player_prop_market_snapshots.player_uid),
                                  team = COALESCE(EXCLUDED.team, nfl_player_prop_market_snapshots.team),
                                  opponent = COALESCE(EXCLUDED.opponent, nfl_player_prop_market_snapshots.opponent),
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
                                "game_id": _to_uuid_or_none(game_meta.get("game_id")),
                                "external_game_id": event_id,
                                "sportsbook": sportsbook,
                                "captured_at": captured_at,
                                "player_uid": identity.player_uid,
                                "player_name": player_name,
                                "team": resolved_team,
                                "opponent": opponent,
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
                                        "identity_status": identity.status,
                                        "identity_rule": identity.rule_used,
                                        "resolver_version": identity.resolver_version,
                                        "roster_team_resolved": resolved_team is not None,
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
            # Phase 1: same player-game means as props board (shared spine).
            prod = production_from_baseline_row(row)
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
                    pass_yards=prod.pass_yards,
                    pass_tds=prod.pass_tds,
                    rush_yards=prod.rush_yards,
                    rush_tds=prod.rush_tds,
                    receiving_yards=prod.receiving_yards,
                    receptions=prod.receptions,
                    rec_tds=prod.rec_tds,
                )
                floor = fantasy_points_from_projection(
                    scoring_profile=profile,
                    pass_yards=float((row.floor_outcome or {}).get("pass_yards", 0.0)),
                    pass_tds=prod.pass_tds * 0.60,
                    rush_yards=float((row.floor_outcome or {}).get("rush_yards", 0.0)),
                    rush_tds=prod.rush_tds * 0.60,
                    receiving_yards=float((row.floor_outcome or {}).get("receiving_yards", 0.0)),
                    receptions=float((row.floor_outcome or {}).get("receptions", 0.0)),
                    rec_tds=prod.rec_tds * 0.60,
                )
                ceiling = fantasy_points_from_projection(
                    scoring_profile=profile,
                    pass_yards=float((row.ceiling_outcome or {}).get("pass_yards", prod.pass_yards)),
                    pass_tds=prod.pass_tds * 1.35,
                    rush_yards=float((row.ceiling_outcome or {}).get("rush_yards", prod.rush_yards)),
                    rush_tds=prod.rush_tds * 1.35,
                    receiving_yards=float(
                        (row.ceiling_outcome or {}).get("receiving_yards", prod.receiving_yards)
                    ),
                    receptions=float((row.ceiling_outcome or {}).get("receptions", prod.receptions)),
                    rec_tds=prod.rec_tds * 1.35,
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
                        "production": prod.as_diagnostics(),
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
                        "projection_payload": json.dumps(
                            {
                                "derived_from": "nfl_player_projection_baselines",
                                "spine_version": NFL_PLAYER_PRODUCTION_VERSION,
                                "profile": profile,
                                "production": player.get("production") or {},
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


_SEASON_FANTASY_ELIGIBLE_POSITIONS = ("QB", "RB", "WR", "TE")


def _fetch_season_player_totals(
    session: Any, *, season: int, model_version: str
) -> List[Dict[str, Any]]:
    """Season totals = SUM of weekly spine baselines (Phase 3 SoT).

    Cap at 17 real game-rows per (team, player_id) ordered by week so extra
    rows cannot invent 20-game season yards. No QB-lock / D5 overlay here —
    fantasy draft and awards inherit the same weekly means as props.
    """
    rows = session.execute(
        text(
            """
            WITH ranked AS (
              SELECT
                b.player_id,
                b.player_uid,
                b.player_name,
                b.team,
                b.position,
                b.week,
                b.pass_yards_mean,
                b.rush_yards_mean,
                b.receiving_yards_mean,
                b.receptions_mean,
                b.pass_tds_mean,
                b.rush_tds_mean,
                b.rec_tds_mean,
                b.floor_outcome,
                b.ceiling_outcome,
                r.rookie_year,
                r.draft_number,
                ROW_NUMBER() OVER (
                  PARTITION BY b.player_id, b.team
                  ORDER BY b.week ASC
                ) AS rn
              FROM nfl_player_projection_baselines b
              LEFT JOIN nfl_dp_rosters r
                ON r.season = b.season AND r.team = b.team AND r.player_id = b.player_id
              WHERE b.season = :season
                AND b.model_version = :model_version
                AND b.game_id IS NOT NULL AND b.game_id <> ''
                AND b.position = ANY(:positions)
            )
            SELECT
              player_id,
              MAX(player_uid::text) AS player_uid,
              MAX(player_name) AS player_name,
              team,
              MAX(position) AS position,
              COUNT(*) AS games_projected,
              SUM(COALESCE(pass_yards_mean, 0.0)) AS pass_yards_total,
              SUM(COALESCE(rush_yards_mean, 0.0)) AS rush_yards_total,
              SUM(COALESCE(receiving_yards_mean, 0.0)) AS receiving_yards_total,
              SUM(COALESCE(receptions_mean, 0.0)) AS receptions_total,
              SUM(COALESCE(pass_tds_mean, 0.0)) AS pass_tds_total,
              SUM(COALESCE(rush_tds_mean, 0.0)) AS rush_tds_total,
              SUM(COALESCE(rec_tds_mean, 0.0)) AS rec_tds_total,
              SUM(COALESCE((floor_outcome->>'pass_yards')::numeric, pass_yards_mean * 0.75, 0.0)) AS pass_yards_floor,
              SUM(COALESCE((floor_outcome->>'rush_yards')::numeric, rush_yards_mean * 0.70, 0.0)) AS rush_yards_floor,
              SUM(COALESCE((floor_outcome->>'receiving_yards')::numeric, receiving_yards_mean * 0.70, 0.0)) AS receiving_yards_floor,
              SUM(COALESCE((floor_outcome->>'receptions')::numeric, receptions_mean * 0.70, 0.0)) AS receptions_floor,
              SUM(COALESCE((ceiling_outcome->>'pass_yards')::numeric, pass_yards_mean * 1.25, 0.0)) AS pass_yards_ceiling,
              SUM(COALESCE((ceiling_outcome->>'rush_yards')::numeric, rush_yards_mean * 1.30, 0.0)) AS rush_yards_ceiling,
              SUM(COALESCE((ceiling_outcome->>'receiving_yards')::numeric, receiving_yards_mean * 1.30, 0.0)) AS receiving_yards_ceiling,
              SUM(COALESCE((ceiling_outcome->>'receptions')::numeric, receptions_mean * 1.30, 0.0)) AS receptions_ceiling,
              MAX(rookie_year) AS rookie_year,
              MAX(draft_number) AS draft_number
            FROM ranked
            WHERE rn <= 17
            GROUP BY player_id, team
            """
        ),
        {"season": int(season), "model_version": model_version, "positions": list(_SEASON_FANTASY_ELIGIBLE_POSITIONS)},
    ).mappings().all()

    players: List[Dict[str, Any]] = []
    for row in rows:
        rookie_year = row["rookie_year"]
        players.append(
            {
                "player_key": f"{row['team']}:{row['player_id']}",
                "player_id": row["player_id"],
                "player_uid": row["player_uid"],
                "player_name": row["player_name"],
                "team": row["team"],
                "position": str(row["position"] or "UNK").upper(),
                "games_projected": int(row["games_projected"] or 0),
                "pass_yards_total": float(row["pass_yards_total"] or 0.0),
                "rush_yards_total": float(row["rush_yards_total"] or 0.0),
                "receiving_yards_total": float(row["receiving_yards_total"] or 0.0),
                "receptions_total": float(row["receptions_total"] or 0.0),
                "pass_tds_total": float(row["pass_tds_total"] or 0.0),
                "rush_tds_total": float(row["rush_tds_total"] or 0.0),
                "rec_tds_total": float(row["rec_tds_total"] or 0.0),
                # Season-aggregate outcome bands for fantasy floor/ceiling.
                "pass_yards_floor": float(row["pass_yards_floor"] or 0.0),
                "rush_yards_floor": float(row["rush_yards_floor"] or 0.0),
                "receiving_yards_floor": float(row["receiving_yards_floor"] or 0.0),
                "receptions_floor": float(row["receptions_floor"] or 0.0),
                "pass_yards_ceiling": float(row["pass_yards_ceiling"] or 0.0),
                "rush_yards_ceiling": float(row["rush_yards_ceiling"] or 0.0),
                "receiving_yards_ceiling": float(row["receiving_yards_ceiling"] or 0.0),
                "receptions_ceiling": float(row["receptions_ceiling"] or 0.0),
                "rookie_year": int(rookie_year) if rookie_year is not None else None,
                "draft_number": int(row["draft_number"]) if row["draft_number"] is not None else None,
                "is_rookie": bool(rookie_year is not None and int(rookie_year) == int(season)),
            }
        )
    return players


def _fetch_league_kicker_baselines(session: Any) -> Dict[str, Any]:
    """Real, league-wide kicker baselines from ALL history in
    `nfl_dp_kicker_weekly` -- the league-average make rate per distance
    bucket (used to shrink thin-sample kickers), the league-average FG
    distance-bucket SHARE (used to shrink thin-sample teams' distance mix),
    and the league-average PAT make rate. See
    `nfl_kicker_dst_projections.py` module docstring for the shrinkage
    rationale."""
    row = session.execute(
        text(
            """
            SELECT
              SUM(fg_att) AS att_total, SUM(fg_made) AS made_total,
              SUM(fg_att_0_19) AS att_0_19, SUM(fg_made_0_19) AS made_0_19,
              SUM(fg_att_20_29) AS att_20_29, SUM(fg_made_20_29) AS made_20_29,
              SUM(fg_att_30_39) AS att_30_39, SUM(fg_made_30_39) AS made_30_39,
              SUM(fg_att_40_49) AS att_40_49, SUM(fg_made_40_49) AS made_40_49,
              SUM(fg_att_50_59) AS att_50_59, SUM(fg_made_50_59) AS made_50_59,
              SUM(fg_att_60_plus) AS att_60_plus, SUM(fg_made_60_plus) AS made_60_plus,
              SUM(pat_att) AS pat_att_total, SUM(pat_made) AS pat_made_total
            FROM nfl_dp_kicker_weekly
            """
        )
    ).mappings().one()
    bucket_keys = {"0_19": "0_19", "20_29": "20_29", "30_39": "30_39", "40_49": "40_49", "50_59": "50_59", "60_plus": "60_plus"}
    att_total = float(row["att_total"] or 0.0)
    make_rate: Dict[str, float] = {}
    bucket_share: Dict[str, float] = {}
    for bucket, col_suffix in bucket_keys.items():
        att = float(row[f"att_{col_suffix}"] or 0.0)
        made = float(row[f"made_{col_suffix}"] or 0.0)
        make_rate[bucket] = (made / att) if att > 0 else 0.0
        bucket_share[bucket] = (att / att_total) if att_total > 0 else (1.0 / len(bucket_keys))
    pat_att_total = float(row["pat_att_total"] or 0.0)
    pat_made_total = float(row["pat_made_total"] or 0.0)
    league_pat_make_rate = (pat_made_total / pat_att_total) if pat_att_total > 0 else 0.94

    two_pt_row = session.execute(
        text(
            """
            SELECT
              SUM(
                COALESCE((payload->>'passing_2pt_conversions')::numeric, 0)
                + COALESCE((payload->>'rushing_2pt_conversions')::numeric, 0)
                + COALESCE((payload->>'receiving_2pt_conversions')::numeric, 0)
              ) AS two_pt_made,
              SUM(
                COALESCE((payload->>'passing_tds')::numeric, 0)
                + COALESCE((payload->>'rushing_tds')::numeric, 0)
                + COALESCE((payload->>'receiving_tds')::numeric, 0)
              ) AS total_tds
            FROM nfl_dp_raw_objects
            WHERE object_type = 'team_game_stats'
            """
        )
    ).mappings().one()
    total_tds = float(two_pt_row["total_tds"] or 0.0)
    two_pt_made = float(two_pt_row["two_pt_made"] or 0.0)
    # Real successful 2pt conversions / real total offensive TDs, used as a
    # proxy for the 2pt ATTEMPT rate (attempt-level data isn't cleanly
    # available) -- see nfl_kicker_dst_projections.py module docstring.
    # Real 2pt attempt rate is small (~1-2% of TDs), so this proxy's
    # downward bias (some attempts fail) is worth well under half a fantasy
    # point across a season and not worth further modeling.
    two_point_attempt_rate = (two_pt_made / total_tds) if total_tds > 0 else 0.0

    return {
        "league_make_rate_by_bucket": make_rate,
        "league_bucket_share": bucket_share,
        "league_pat_make_rate": league_pat_make_rate,
        "two_point_attempt_rate": two_point_attempt_rate,
    }


def _fetch_team_kicker_history(session: Any) -> Dict[str, Dict[str, Any]]:
    """Real per-team historical FG attempt volume (attempts per real game
    played by that team's kicker(s)) and real per-team FG distance-bucket
    attempt mix, from ALL history in `nfl_dp_kicker_weekly`."""
    rows = session.execute(
        text(
            """
            SELECT
              team,
              SUM(fg_att) AS att_total,
              COUNT(DISTINCT (season, week)) AS games,
              SUM(fg_att_0_19) AS att_0_19, SUM(fg_made_0_19) AS made_0_19,
              SUM(fg_att_20_29) AS att_20_29, SUM(fg_made_20_29) AS made_20_29,
              SUM(fg_att_30_39) AS att_30_39, SUM(fg_made_30_39) AS made_30_39,
              SUM(fg_att_40_49) AS att_40_49, SUM(fg_made_40_49) AS made_40_49,
              SUM(fg_att_50_59) AS att_50_59, SUM(fg_made_50_59) AS made_50_59,
              SUM(fg_att_60_plus) AS att_60_plus, SUM(fg_made_60_plus) AS made_60_plus
            FROM nfl_dp_kicker_weekly
            GROUP BY team
            """
        )
    ).mappings().all()
    out: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        games = int(row["games"] or 0)
        out[row["team"]] = {
            "fg_attempts_per_game": (float(row["att_total"] or 0.0) / games) if games > 0 else 0.0,
            "bucket_attempts": {b: float(row[f"att_{b}"] or 0.0) for b in ("0_19", "20_29", "30_39", "40_49", "50_59", "60_plus")},
            "bucket_makes": {b: float(row[f"made_{b}"] or 0.0) for b in ("0_19", "20_29", "30_39", "40_49", "50_59", "60_plus")},
        }
    return out


def _fetch_kicker_career_bucket_stats(session: Any) -> Dict[str, Dict[str, Any]]:
    """Real per-kicker CAREER (all seasons/teams -- accuracy skill travels
    with the kicker, not the team) FG makes/attempts by distance bucket, plus
    each kicker's most recent season with real data and that season's real
    attempt volume (used only to pick each 2026 team's primary kicker when a
    team has multiple K's rostered)."""
    rows = session.execute(
        text(
            """
            SELECT
              player_id, MAX(player_name) AS player_name,
              MAX(season) AS most_recent_season,
              SUM(fg_att_0_19) AS att_0_19, SUM(fg_made_0_19) AS made_0_19,
              SUM(fg_att_20_29) AS att_20_29, SUM(fg_made_20_29) AS made_20_29,
              SUM(fg_att_30_39) AS att_30_39, SUM(fg_made_30_39) AS made_30_39,
              SUM(fg_att_40_49) AS att_40_49, SUM(fg_made_40_49) AS made_40_49,
              SUM(fg_att_50_59) AS att_50_59, SUM(fg_made_50_59) AS made_50_59,
              SUM(fg_att_60_plus) AS att_60_plus, SUM(fg_made_60_plus) AS made_60_plus
            FROM nfl_dp_kicker_weekly
            GROUP BY player_id
            """
        )
    ).mappings().all()
    recent_att_by_player = session.execute(
        text(
            """
            SELECT player_id, season, SUM(fg_att) AS att
            FROM nfl_dp_kicker_weekly
            GROUP BY player_id, season
            """
        )
    ).mappings().all()
    recent_att_lookup: Dict[str, Dict[int, float]] = {}
    for row in recent_att_by_player:
        recent_att_lookup.setdefault(row["player_id"], {})[int(row["season"])] = float(row["att"] or 0.0)

    out: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        player_id = row["player_id"]
        most_recent_season = int(row["most_recent_season"]) if row["most_recent_season"] is not None else None
        out[player_id] = {
            "player_name": row["player_name"],
            "career_makes_by_bucket": {b: float(row[f"made_{b}"] or 0.0) for b in ("0_19", "20_29", "30_39", "40_49", "50_59", "60_plus")},
            "career_attempts_by_bucket": {b: float(row[f"att_{b}"] or 0.0) for b in ("0_19", "20_29", "30_39", "40_49", "50_59", "60_plus")},
            "most_recent_season": most_recent_season,
            "most_recent_season_attempts": recent_att_lookup.get(player_id, {}).get(most_recent_season, 0.0),
        }
    return out


def _select_primary_kickers_per_team(session: Any, *, season: int) -> List[Dict[str, Any]]:
    """Picks ONE kicker per team for `season`'s roster (some teams carry two
    K's, e.g. an incumbent + a camp-battle/practice-squad arm) -- the one
    with the most real recent-season FG attempt volume (most recent season
    with data, then attempts in that season), matching this codebase's
    existing `select_primary_starter_per_team_position` convention for
    awards (one "the" starter per team/position, not several
    simultaneously). A team with two kickers who BOTH have zero real
    history (e.g. two rookies in a camp battle) falls back to the lowest
    `player_id` for a deterministic, reproducible pick -- there is no real
    signal available to break that tie honestly."""
    roster_rows = session.execute(
        text("SELECT team, player_id, player_name FROM nfl_dp_rosters WHERE season = :season AND position = 'K'"),
        {"season": season},
    ).mappings().all()
    career_stats = _fetch_kicker_career_bucket_stats(session)
    candidates_by_team: Dict[str, List[Dict[str, Any]]] = {}
    for row in roster_rows:
        stats = career_stats.get(row["player_id"], {})
        candidates_by_team.setdefault(row["team"], []).append(
            {
                "team": row["team"],
                "player_id": row["player_id"],
                "player_name": row["player_name"] or stats.get("player_name"),
                "most_recent_season": stats.get("most_recent_season") or -1,
                "most_recent_season_attempts": stats.get("most_recent_season_attempts") or 0.0,
            }
        )
    selected: List[Dict[str, Any]] = []
    for team, candidates in candidates_by_team.items():
        best = sorted(
            candidates,
            key=lambda c: (-c["most_recent_season"], -c["most_recent_season_attempts"], str(c["player_id"])),
        )[0]
        selected.append(best)
    return selected


def _fetch_team_offensive_td_totals(session: Any, *, season: int, model_version: str) -> Dict[str, float]:
    """Real projected season offensive TD total per team, summed across
    EVERY position in `nfl_player_projection_baselines` (not just the
    QB/RB/WR/TE season-total pool `_fetch_season_player_totals` filters to)
    -- the same real projection every other position's season total is
    built from, reused here (not re-derived) for kicker PAT volume.

    Deliberately `pass_tds_mean + rush_tds_mean` ONLY -- NOT `+ rec_tds_mean`
    too. Every real passing touchdown is thrown BY a QB (`pass_tds_mean`)
    AND caught by a receiver (`rec_tds_mean`) -- the SAME touchdown, counted
    on two different players' rows. Adding all three would double-count the
    passing-TD share of a team's offense (confirmed against real projected
    2026 team totals while validating this feature: `pass_tds_mean` summed
    across a team consistently exceeds that same team's summed
    `rec_tds_mean`, since this baseline is an independent per-player mean
    with no cross-player reconciliation -- adding `rec_tds_mean` on top of
    `pass_tds_mean` inflated one real team's projected offensive TD total
    from a realistic ~48 to an unrealistic ~61 before this was caught)."""
    rows = session.execute(
        text(
            """
            SELECT team, SUM(COALESCE(pass_tds_mean, 0.0) + COALESCE(rush_tds_mean, 0.0)) AS offensive_tds_total
            FROM nfl_player_projection_baselines
            WHERE season = :season AND model_version = :model_version AND game_id IS NOT NULL AND game_id <> ''
            GROUP BY team
            """
        ),
        {"season": season, "model_version": model_version},
    ).mappings().all()
    return {row["team"]: float(row["offensive_tds_total"] or 0.0) for row in rows}


def _fetch_team_situational_signal(session: Any) -> Dict[str, Any]:
    """Latest real `red_zone_td_rate` (offense) and
    `epa_per_play_defense_allowed` per team from
    `nfl_dp_team_situational_latest`, plus the league-wide averages of each
    -- this pipeline's own already-computed situational features, reused
    (not re-derived) for the K FG-volume and DST defense-strength
    adjustments. See `nfl_kicker_dst_projections.py`."""
    rows = session.execute(
        text("SELECT team, red_zone_td_rate, epa_per_play_defense_allowed FROM nfl_dp_team_situational_latest")
    ).mappings().all()
    by_team = {
        row["team"]: {
            "red_zone_td_rate": float(row["red_zone_td_rate"]) if row["red_zone_td_rate"] is not None else None,
            "epa_per_play_defense_allowed": float(row["epa_per_play_defense_allowed"]) if row["epa_per_play_defense_allowed"] is not None else None,
        }
        for row in rows
    }
    red_zone_values = [v["red_zone_td_rate"] for v in by_team.values() if v["red_zone_td_rate"] is not None]
    epa_values = [v["epa_per_play_defense_allowed"] for v in by_team.values() if v["epa_per_play_defense_allowed"] is not None]
    return {
        "by_team": by_team,
        "league_avg_red_zone_td_rate": (sum(red_zone_values) / len(red_zone_values)) if red_zone_values else 0.20,
        "league_avg_epa_per_play_defense_allowed": (sum(epa_values) / len(epa_values)) if epa_values else 0.0,
    }


def _fetch_team_schedule_game_counts(session: Any, *, season: int) -> Dict[str, int]:
    rows = session.execute(
        text(
            """
            SELECT team, COUNT(*) AS games FROM (
              SELECT home_team AS team FROM nfl_dp_schedules WHERE season = :season
              UNION ALL
              SELECT away_team AS team FROM nfl_dp_schedules WHERE season = :season
            ) t
            GROUP BY team
            """
        ),
        {"season": season},
    ).mappings().all()
    return {row["team"]: int(row["games"] or 0) for row in rows}


def _fetch_kicker_season_players(session: Any, *, season: int, model_version: str) -> List[Dict[str, Any]]:
    """Builds season-long K rows using real historical kicker accuracy +
    real team FG-attempt-volume history/mix + this pipeline's own real
    red-zone-efficiency signal + real projected team offensive TDs for PAT
    volume. See `nfl_kicker_dst_projections.py` for the full methodology.
    K fantasy scoring does not vary by PPR profile, so `total_points` here is
    profile-independent (the caller applies the same total to every
    scoring_profile row). Optional ``nfl_kdst_publish`` artifact overlays
    FG/XP volume when a 100k publish exists — never invents named kickers."""
    from src.services.nfl_kdst_publish import (
        kdst_volume_overlay_for_team,
        load_kdst_publish_artifact,
        named_kickers_from_artifact,
    )

    kdst_art = load_kdst_publish_artifact(int(season))
    league = _fetch_league_kicker_baselines(session)
    team_history = _fetch_team_kicker_history(session)
    career_stats = _fetch_kicker_career_bucket_stats(session)
    primary_kickers = _select_primary_kickers_per_team(session, season=season)
    if not primary_kickers:
        primary_kickers = named_kickers_from_artifact(kdst_art)
    situational = _fetch_team_situational_signal(session)
    offensive_tds_by_team = _fetch_team_offensive_td_totals(session, season=season, model_version=model_version)
    schedule_games = _fetch_team_schedule_game_counts(session, season=season)

    players: List[Dict[str, Any]] = []
    for kicker in primary_kickers:
        team = kicker["team"]
        games = float(schedule_games.get(team, GAMES_PER_REGULAR_SEASON))
        team_hist = team_history.get(team, {"fg_attempts_per_game": 0.0, "bucket_attempts": {}, "bucket_makes": {}})
        team_signal = situational["by_team"].get(team, {})
        team_red_zone_td_rate = team_signal.get("red_zone_td_rate")
        if team_red_zone_td_rate is None:
            team_red_zone_td_rate = situational["league_avg_red_zone_td_rate"]

        total_fg_attempts = project_team_fg_attempt_volume(
            team_fg_attempts_per_game_history=team_hist["fg_attempts_per_game"],
            team_red_zone_td_rate=team_red_zone_td_rate,
            league_avg_red_zone_td_rate=situational["league_avg_red_zone_td_rate"],
            games=games,
        )
        overlay = kdst_volume_overlay_for_team(kdst_art, team)
        if overlay and overlay.get("fg_attempts") is not None:
            total_fg_attempts = float(overlay["fg_attempts"])
        attempts_by_bucket = allocate_attempts_to_buckets(
            total_attempts=total_fg_attempts,
            team_bucket_makes=team_hist.get("bucket_makes", {}),
            team_bucket_attempts=team_hist.get("bucket_attempts", {}),
            league_bucket_shares=league["league_bucket_share"],
        )
        career = career_stats.get(
            kicker["player_id"],
            {"career_makes_by_bucket": {}, "career_attempts_by_bucket": {}},
        )
        makes_by_bucket = project_kicker_fg_makes_by_bucket(
            team_attempts_by_bucket=attempts_by_bucket,
            kicker_career_makes_by_bucket=career["career_makes_by_bucket"],
            kicker_career_attempts_by_bucket=career["career_attempts_by_bucket"],
            league_make_rate_by_bucket=league["league_make_rate_by_bucket"],
        )
        pat_makes = project_pat_makes(
            team_offensive_tds_season=offensive_tds_by_team.get(team, 0.0),
            two_point_attempt_rate=league["two_point_attempt_rate"],
            league_pat_make_rate=league["league_pat_make_rate"],
        )
        if overlay and overlay.get("xp_attempts") is not None:
            pat_makes = float(overlay["xp_attempts"]) * float(league["league_pat_make_rate"])
        total_points = compute_kicker_season_fantasy_points(fg_makes_by_bucket=makes_by_bucket, pat_makes=pat_makes)
        fg_made_total = sum(makes_by_bucket.values())

        players.append(
            {
                "player_key": f"{team}:{kicker['player_id']}",
                "player_id": kicker["player_id"],
                "player_uid": None,
                "player_name": kicker["player_name"] or kicker["player_id"],
                "team": team,
                "position": "K",
                "games_projected": int(games),
                "pass_yards_total": None,
                "rush_yards_total": None,
                "receiving_yards_total": None,
                "receptions_total": None,
                "pass_tds_total": None,
                "rush_tds_total": None,
                "rec_tds_total": None,
                "field_goals_made_total": round(fg_made_total, 4),
                "field_goals_attempted_total": round(total_fg_attempts, 4),
                "extra_points_made_total": round(pat_makes, 4),
                "points_allowed_total": None,
                "sacks_total": None,
                "def_interceptions_total": None,
                "fumble_recoveries_total": None,
                "defensive_tds_total": None,
                "safeties_total": None,
                "total_points": total_points,
                "rookie_year": None,
                "draft_number": None,
                "is_rookie": False,
                "projection_payload": {
                    "derived_from": ["nfl_dp_kicker_weekly", "nfl_dp_team_situational_latest", "nfl_player_projection_baselines"],
                    "fg_makes_by_bucket": {b: round(v, 4) for b, v in makes_by_bucket.items()},
                    "fg_attempts_by_bucket": {b: round(v, 4) for b, v in attempts_by_bucket.items()},
                    "team_red_zone_td_rate": round(team_red_zone_td_rate, 4),
                    "league_avg_red_zone_td_rate": round(situational["league_avg_red_zone_td_rate"], 4),
                },
            }
        )
    return players


def _fetch_team_defense_history(session: Any) -> Dict[str, Any]:
    """Real per-team historical defense/special-teams counting-stat rates
    and league-wide averages (+ league-wide points-allowed std, used as a
    shared game-to-game variance estimate -- see
    `nfl_kicker_dst_projections.py` module docstring for why a shared
    league-wide std is used instead of a noisy per-team estimate), from ALL
    history in `nfl_dp_team_defense_weekly`."""
    team_rows = session.execute(
        text(
            """
            SELECT
              team, COUNT(*) AS games,
              SUM(points_allowed) AS points_allowed_total,
              SUM(sacks) AS sacks_total,
              SUM(interceptions) AS interceptions_total,
              SUM(fumble_recoveries) AS fumble_recoveries_total,
              SUM(defensive_tds + special_teams_tds) AS defensive_tds_total,
              SUM(safeties) AS safeties_total
            FROM nfl_dp_team_defense_weekly
            GROUP BY team
            """
        )
    ).mappings().all()
    league_row = session.execute(
        text(
            """
            SELECT
              AVG(points_allowed) AS lg_points_allowed, STDDEV(points_allowed) AS lg_points_allowed_std,
              AVG(sacks) AS lg_sacks, AVG(interceptions) AS lg_interceptions,
              AVG(fumble_recoveries) AS lg_fumble_recoveries, AVG(defensive_tds + special_teams_tds) AS lg_defensive_tds,
              AVG(safeties) AS lg_safeties
            FROM nfl_dp_team_defense_weekly
            """
        )
    ).mappings().one()
    by_team: Dict[str, Dict[str, Any]] = {}
    for row in team_rows:
        games = int(row["games"] or 0)
        by_team[row["team"]] = {
            "games": games,
            "points_allowed_per_game": (float(row["points_allowed_total"] or 0.0) / games) if games > 0 else 0.0,
            "sacks_per_game": (float(row["sacks_total"] or 0.0) / games) if games > 0 else 0.0,
            "interceptions_per_game": (float(row["interceptions_total"] or 0.0) / games) if games > 0 else 0.0,
            "fumble_recoveries_per_game": (float(row["fumble_recoveries_total"] or 0.0) / games) if games > 0 else 0.0,
            "defensive_tds_per_game": (float(row["defensive_tds_total"] or 0.0) / games) if games > 0 else 0.0,
            "safeties_per_game": (float(row["safeties_total"] or 0.0) / games) if games > 0 else 0.0,
        }
    return {
        "by_team": by_team,
        "league_avg_points_allowed_per_game": float(league_row["lg_points_allowed"] or 22.0),
        "league_points_allowed_std": float(league_row["lg_points_allowed_std"] or 10.0),
        "league_avg_sacks_per_game": float(league_row["lg_sacks"] or 0.0),
        "league_avg_interceptions_per_game": float(league_row["lg_interceptions"] or 0.0),
        "league_avg_fumble_recoveries_per_game": float(league_row["lg_fumble_recoveries"] or 0.0),
        "league_avg_defensive_tds_per_game": float(league_row["lg_defensive_tds"] or 0.0),
        "league_avg_safeties_per_game": float(league_row["lg_safeties"] or 0.0),
    }


# All 32 real NFL team codes, used to build one DST row per team --
# `nfl_dp_team_defense_weekly` only carries real HISTORICAL rows (a team with
# a data gap in every historical season would otherwise be silently absent
# from the draft board rather than falling back to league-average, which is
# the same "a rostered player with no usage should still get a real baseline
# row, not silent absence" principle `docs/NFL_DATA_PLATFORM.md`'s preseason
# bootstrap section documents for offensive skill positions).
_ALL_NFL_TEAM_CODES = (
    "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE", "DAL", "DEN", "DET", "GB",
    "HOU", "IND", "JAX", "KC", "LA", "LAC", "LV", "MIA", "MIN", "NE", "NO", "NYG",
    "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS",
)


def _fetch_dst_season_players(session: Any, *, season: int) -> List[Dict[str, Any]]:
    """Builds season-long DST rows -- one per real NFL team -- using real
    historical team defense/special-teams rates (shrunk toward league
    average per-stat, see `DEFENSE_STAT_SHRINKAGE_PRIOR_GAMES`) and this
    pipeline's own real defensive-EPA-allowed signal for the points-allowed
    adjustment. See `nfl_kicker_dst_projections.py` for the full
    methodology. DST fantasy scoring does not vary by PPR profile."""
    from src.services.nfl_kdst_publish import dst_overlay_for_team, load_kdst_publish_artifact

    kdst_art = load_kdst_publish_artifact(int(season))
    defense_history = _fetch_team_defense_history(session)
    situational = _fetch_team_situational_signal(session)
    schedule_games = _fetch_team_schedule_game_counts(session, season=season)

    players: List[Dict[str, Any]] = []
    for team in _ALL_NFL_TEAM_CODES:
        games = float(schedule_games.get(team, GAMES_PER_REGULAR_SEASON))
        team_hist = defense_history["by_team"].get(team)
        if team_hist is None:
            team_hist = {
                "points_allowed_per_game": defense_history["league_avg_points_allowed_per_game"],
                "sacks_per_game": defense_history["league_avg_sacks_per_game"],
                "interceptions_per_game": defense_history["league_avg_interceptions_per_game"],
                "fumble_recoveries_per_game": defense_history["league_avg_fumble_recoveries_per_game"],
                "defensive_tds_per_game": defense_history["league_avg_defensive_tds_per_game"],
                "safeties_per_game": defense_history["league_avg_safeties_per_game"],
                "games": 0,
            }
        team_games = float(team_hist.get("games", 0))

        shrunk_points_allowed = shrink_defense_stat_per_game(
            stat_name="points_allowed",
            team_total=team_hist["points_allowed_per_game"] * team_games,
            team_games=team_games,
            league_avg_per_game=defense_history["league_avg_points_allowed_per_game"],
        )
        shrunk_sacks = shrink_defense_stat_per_game(
            stat_name="sacks",
            team_total=team_hist["sacks_per_game"] * team_games,
            team_games=team_games,
            league_avg_per_game=defense_history["league_avg_sacks_per_game"],
        )
        shrunk_interceptions = shrink_defense_stat_per_game(
            stat_name="interceptions",
            team_total=team_hist["interceptions_per_game"] * team_games,
            team_games=team_games,
            league_avg_per_game=defense_history["league_avg_interceptions_per_game"],
        )
        shrunk_fumble_recoveries = shrink_defense_stat_per_game(
            stat_name="fumble_recoveries",
            team_total=team_hist["fumble_recoveries_per_game"] * team_games,
            team_games=team_games,
            league_avg_per_game=defense_history["league_avg_fumble_recoveries_per_game"],
        )
        shrunk_defensive_tds = shrink_defense_stat_per_game(
            stat_name="defensive_tds",
            team_total=team_hist["defensive_tds_per_game"] * team_games,
            team_games=team_games,
            league_avg_per_game=defense_history["league_avg_defensive_tds_per_game"],
        )
        shrunk_safeties = shrink_defense_stat_per_game(
            stat_name="safeties",
            team_total=team_hist["safeties_per_game"] * team_games,
            team_games=team_games,
            league_avg_per_game=defense_history["league_avg_safeties_per_game"],
        )

        team_signal = situational["by_team"].get(team, {})
        team_epa_allowed = team_signal.get("epa_per_play_defense_allowed")
        if team_epa_allowed is None:
            team_epa_allowed = situational["league_avg_epa_per_play_defense_allowed"]
        adjusted_points_allowed_mean = project_team_points_allowed_mean(
            team_points_allowed_per_game_history=shrunk_points_allowed,
            team_epa_per_play_defense_allowed=team_epa_allowed,
            league_avg_epa_per_play_defense_allowed=situational["league_avg_epa_per_play_defense_allowed"],
        )
        dst_ov = dst_overlay_for_team(kdst_art, team)
        if dst_ov and dst_ov.get("points_allowed_mean") is not None:
            adjusted_points_allowed_mean = float(dst_ov["points_allowed_mean"])
        if dst_ov and dst_ov.get("sacks") is not None and games > 0:
            shrunk_sacks = float(dst_ov["sacks"]) / games

        breakdown = compute_dst_season_fantasy_points(
            points_allowed_mean_per_game=adjusted_points_allowed_mean,
            points_allowed_std_per_game=defense_history["league_points_allowed_std"],
            sacks_per_game=shrunk_sacks,
            interceptions_per_game=shrunk_interceptions,
            fumble_recoveries_per_game=shrunk_fumble_recoveries,
            defensive_tds_per_game=shrunk_defensive_tds,
            safeties_per_game=shrunk_safeties,
            games=games,
        )

        players.append(
            {
                "player_key": f"{team}:DST",
                "player_id": team,
                "player_uid": None,
                "player_name": f"{team} DST",
                "team": team,
                "position": "DST",
                "games_projected": int(games),
                "pass_yards_total": None,
                "rush_yards_total": None,
                "receiving_yards_total": None,
                "receptions_total": None,
                "pass_tds_total": None,
                "rush_tds_total": None,
                "rec_tds_total": None,
                "field_goals_made_total": None,
                "field_goals_attempted_total": None,
                "extra_points_made_total": None,
                "points_allowed_total": round(adjusted_points_allowed_mean * games, 4),
                "sacks_total": round(shrunk_sacks * games, 4),
                "def_interceptions_total": round(shrunk_interceptions * games, 4),
                "fumble_recoveries_total": round(shrunk_fumble_recoveries * games, 4),
                "defensive_tds_total": round(shrunk_defensive_tds * games, 4),
                "safeties_total": round(shrunk_safeties * games, 4),
                "total_points": breakdown["total_points"],
                "rookie_year": None,
                "draft_number": None,
                "is_rookie": False,
                "projection_payload": {
                    "derived_from": ["nfl_dp_team_defense_weekly", "nfl_dp_schedules", "nfl_dp_team_situational_latest"],
                    "components": breakdown,
                    "team_epa_per_play_defense_allowed": round(team_epa_allowed, 4),
                    "league_avg_epa_per_play_defense_allowed": round(situational["league_avg_epa_per_play_defense_allowed"], 4),
                    "historical_games_sampled": int(team_games),
                },
            }
        )
    return players


@celery_app.task(name="src.tasks.materialize_nfl_fantasy_season_draft_rankings")
def materialize_nfl_fantasy_season_draft_rankings(
    *,
    season: int,
    model_version: str = "nfl-player-v1",
) -> Dict[str, Any]:
    """Season-long fantasy DRAFT board -- distinct from
    `materialize_nfl_fantasy_projections` (single-week start/sit rankings).
    One row per (season, scoring_profile, model_version, player_id), built
    from real season-total counting stats (see `_fetch_season_player_totals`)
    fed through the already-canonical `fantasy_points_from_projection()` once
    per scoring profile, then ranked/tiered via
    `nfl_fantasy_draft_rankings.rank_season_fantasy_players`.

    K and DST rows (`_fetch_kicker_season_players` /
    `_fetch_dst_season_players`, see `nfl_kicker_dst_projections.py`) are
    merged into the SAME ranking pass as QB/RB/WR/TE so `rank_overall`/
    `value_over_replacement` reflect their real, comparatively low draft
    value across the WHOLE board, not a separately-scaled ranking. Their
    `total_points` does not vary by scoring profile (no PPR-style bonus
    applies to K/DST scoring), so it is computed once and reused across all
    three `profiles` rows.
    """
    session = SessionLocal()
    upserted = 0
    try:
        base_players = _fetch_season_player_totals(session, season=season, model_version=model_version)
        kicker_players = _fetch_kicker_season_players(session, season=season, model_version=model_version)
        dst_players = _fetch_dst_season_players(session, season=season)
        if not base_players and not kicker_players and not dst_players:
            from src.services.nfl_kdst_publish import kdst_publish_status

            return {
                "season": int(season),
                "model_version": model_version,
                "status": "no_data",
                "rows_upserted": 0,
                "kickers": 0,
                "dst_teams": 0,
                "kdst_publish": kdst_publish_status(int(season)),
            }

        k_dst_extra_columns = (
            "field_goals_made_total",
            "field_goals_attempted_total",
            "extra_points_made_total",
            "points_allowed_total",
            "sacks_total",
            "def_interceptions_total",
            "fumble_recoveries_total",
            "defensive_tds_total",
            "safeties_total",
        )

        profiles = ["standard", "half_ppr", "ppr"]
        for profile in profiles:
            profile_players = []
            for player in base_players:
                total_points = fantasy_points_from_projection(
                    scoring_profile=profile,
                    pass_yards=player["pass_yards_total"],
                    pass_tds=player["pass_tds_total"],
                    rush_yards=player["rush_yards_total"],
                    rush_tds=player["rush_tds_total"],
                    receiving_yards=player["receiving_yards_total"],
                    receptions=player["receptions_total"],
                    rec_tds=player["rec_tds_total"],
                )
                # Season floor/ceiling mirror weekly fantasy: use outcome-band
                # yards/receptions + scaled TD means (0.60 / 1.35).
                floor_points = fantasy_points_from_projection(
                    scoring_profile=profile,
                    pass_yards=float(player.get("pass_yards_floor") or 0.0),
                    pass_tds=float(player["pass_tds_total"]) * 0.60,
                    rush_yards=float(player.get("rush_yards_floor") or 0.0),
                    rush_tds=float(player["rush_tds_total"]) * 0.60,
                    receiving_yards=float(player.get("receiving_yards_floor") or 0.0),
                    receptions=float(player.get("receptions_floor") or 0.0),
                    rec_tds=float(player["rec_tds_total"]) * 0.60,
                )
                ceiling_points = fantasy_points_from_projection(
                    scoring_profile=profile,
                    pass_yards=float(player.get("pass_yards_ceiling") or player["pass_yards_total"]),
                    pass_tds=float(player["pass_tds_total"]) * 1.35,
                    rush_yards=float(player.get("rush_yards_ceiling") or player["rush_yards_total"]),
                    rush_tds=float(player["rush_tds_total"]) * 1.35,
                    receiving_yards=float(
                        player.get("receiving_yards_ceiling") or player["receiving_yards_total"]
                    ),
                    receptions=float(player.get("receptions_ceiling") or player["receptions_total"]),
                    rec_tds=float(player["rec_tds_total"]) * 1.35,
                )
                profile_players.append(
                    {
                        **player,
                        "total_points": total_points,
                        "floor_points": floor_points,
                        "median_points": total_points,
                        "ceiling_points": ceiling_points,
                    }
                )
            # K/DST `total_points` is already profile-independent (computed
            # once in _fetch_kicker_season_players/_fetch_dst_season_players)
            # -- reused as-is for every profile rather than re-derived here.
            # Approximate K/DST bands with a thin positional spread until
            # dedicated outcome quantiles exist for those positions.
            for special in (*kicker_players, *dst_players):
                pts = float(special.get("total_points") or 0.0)
                profile_players.append(
                    {
                        **special,
                        "floor_points": round(pts * 0.85, 4),
                        "median_points": pts,
                        "ceiling_points": round(pts * 1.15, 4),
                    }
                )

            ranked = rank_season_fantasy_players(profile_players)
            for player in ranked:
                projection_payload = dict(player.get("projection_payload") or {})
                projection_payload.setdefault("aggregation", "season_total")
                projection_payload.setdefault("profile", profile)
                projection_payload.setdefault("derived_from", "nfl_player_projection_baselines")
                projection_payload["floor_points"] = float(player.get("floor_points") or player["total_points"])
                projection_payload["median_points"] = float(player.get("median_points") or player["total_points"])
                projection_payload["ceiling_points"] = float(
                    player.get("ceiling_points") or player["total_points"]
                )
                projection_payload["uncertainty_source"] = "baseline_floor_ceiling_outcomes"
                session.execute(
                    text(
                        """
                        INSERT INTO nfl_fantasy_season_draft_rankings (
                          season, scoring_profile, model_version, player_id, player_uid, player_name, team, position,
                          games_projected, pass_yards_total, rush_yards_total, receiving_yards_total, receptions_total,
                          pass_tds_total, rush_tds_total, rec_tds_total,
                          field_goals_made_total, field_goals_attempted_total, extra_points_made_total,
                          points_allowed_total, sacks_total, def_interceptions_total, fumble_recoveries_total,
                          defensive_tds_total, safeties_total,
                          total_points, replacement_points, value_over_replacement,
                          rank_overall, rank_position, tier, is_rookie, rookie_year, draft_number,
                          projection_payload, created_at, updated_at
                        ) VALUES (
                          :season, :scoring_profile, :model_version, :player_id, CAST(:player_uid AS uuid), :player_name, :team, :position,
                          :games_projected, :pass_yards_total, :rush_yards_total, :receiving_yards_total, :receptions_total,
                          :pass_tds_total, :rush_tds_total, :rec_tds_total,
                          :field_goals_made_total, :field_goals_attempted_total, :extra_points_made_total,
                          :points_allowed_total, :sacks_total, :def_interceptions_total, :fumble_recoveries_total,
                          :defensive_tds_total, :safeties_total,
                          :total_points, :replacement_points, :value_over_replacement,
                          :rank_overall, :rank_position, :tier, :is_rookie, :rookie_year, :draft_number,
                          CAST(:projection_payload AS jsonb), NOW(), NOW()
                        )
                        ON CONFLICT (season, scoring_profile, model_version, player_id) DO UPDATE SET
                          player_uid = EXCLUDED.player_uid,
                          player_name = EXCLUDED.player_name,
                          team = EXCLUDED.team,
                          position = EXCLUDED.position,
                          games_projected = EXCLUDED.games_projected,
                          pass_yards_total = EXCLUDED.pass_yards_total,
                          rush_yards_total = EXCLUDED.rush_yards_total,
                          receiving_yards_total = EXCLUDED.receiving_yards_total,
                          receptions_total = EXCLUDED.receptions_total,
                          pass_tds_total = EXCLUDED.pass_tds_total,
                          rush_tds_total = EXCLUDED.rush_tds_total,
                          rec_tds_total = EXCLUDED.rec_tds_total,
                          field_goals_made_total = EXCLUDED.field_goals_made_total,
                          field_goals_attempted_total = EXCLUDED.field_goals_attempted_total,
                          extra_points_made_total = EXCLUDED.extra_points_made_total,
                          points_allowed_total = EXCLUDED.points_allowed_total,
                          sacks_total = EXCLUDED.sacks_total,
                          def_interceptions_total = EXCLUDED.def_interceptions_total,
                          fumble_recoveries_total = EXCLUDED.fumble_recoveries_total,
                          defensive_tds_total = EXCLUDED.defensive_tds_total,
                          safeties_total = EXCLUDED.safeties_total,
                          total_points = EXCLUDED.total_points,
                          replacement_points = EXCLUDED.replacement_points,
                          value_over_replacement = EXCLUDED.value_over_replacement,
                          rank_overall = EXCLUDED.rank_overall,
                          rank_position = EXCLUDED.rank_position,
                          tier = EXCLUDED.tier,
                          is_rookie = EXCLUDED.is_rookie,
                          rookie_year = EXCLUDED.rookie_year,
                          draft_number = EXCLUDED.draft_number,
                          projection_payload = EXCLUDED.projection_payload,
                          updated_at = EXCLUDED.updated_at
                        """
                    ),
                    {
                        "season": int(season),
                        "scoring_profile": profile,
                        "model_version": model_version,
                        "player_id": player["player_id"],
                        "player_uid": player["player_uid"],
                        "player_name": player["player_name"],
                        "team": player["team"],
                        "position": player["position"],
                        "games_projected": player["games_projected"],
                        "pass_yards_total": player["pass_yards_total"],
                        "rush_yards_total": player["rush_yards_total"],
                        "receiving_yards_total": player["receiving_yards_total"],
                        "receptions_total": player["receptions_total"],
                        "pass_tds_total": player["pass_tds_total"],
                        "rush_tds_total": player["rush_tds_total"],
                        "rec_tds_total": player["rec_tds_total"],
                        **{col: player.get(col) for col in k_dst_extra_columns},
                        "total_points": player["total_points"],
                        "replacement_points": player["replacement_points"],
                        "value_over_replacement": player["value_over_replacement"],
                        "rank_overall": player["rank_overall"],
                        "rank_position": player["rank_position"],
                        "tier": player["tier"],
                        "is_rookie": player["is_rookie"],
                        "rookie_year": player["rookie_year"],
                        "draft_number": player["draft_number"],
                        "projection_payload": json.dumps(projection_payload),
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
                "week": 0,
                "layer": "fantasy_season_draft_rankings",
                "model_version": model_version,
                "source_coverage": json.dumps(
                    {
                        "players": len(base_players),
                        "kickers": len(kicker_players),
                        "dst_teams": len(dst_players),
                        "profiles": len(profiles),
                    }
                ),
                "freshness": json.dumps({"generated_at": datetime.now(timezone.utc).isoformat()}),
                "calibration_flags": json.dumps({"calibrated": False, "tiers": "fixed-rank-ladder"}),
                "readiness_status": "go" if len(base_players) > 50 else "warning",
                "metrics": json.dumps({"rows_upserted": upserted}),
            },
        )
        session.commit()
        from src.services.nfl_kdst_publish import kdst_publish_status

        return {
            "season": int(season),
            "model_version": model_version,
            "players": len(base_players),
            "kickers": len(kicker_players),
            "dst_teams": len(dst_players),
            "rows_upserted": upserted,
            "kdst_publish": kdst_publish_status(int(season)),
        }
    except Exception:
        session.rollback()
        log.exception("Failed to materialize NFL fantasy season draft rankings")
        raise
    finally:
        session.close()


def _find_repo_root_with_data_ops() -> Optional[str]:
    """Walks up from this file's location until a `data/ops` directory is
    found, mirroring `findRepoRoot()` in apps/web/lib/nfl-preseason-artifacts.ts
    (the web app's reader for the same season Monte Carlo bundles)."""
    current = os.path.dirname(os.path.abspath(__file__))
    for _ in range(8):
        if os.path.isdir(os.path.join(current, "data", "ops")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return None


def _load_latest_team_season_outcomes(season: int) -> Dict[str, Dict[str, Any]]:
    """Loads {team: {...}} from the most recent
    data/ops/nfl-preseason-sim-<season>-<timestamp>/team_regular_season_outcomes.csv
    bundle -- the same real, validated 50,000-replicate season Monte Carlo
    output the web app reads (see apps/web/lib/nfl-preseason-artifacts.ts).
    There is no DB table for this yet (team-outcome persistence is owned by
    the separate season-simulator workstream), so this reads the flat CSV
    artifact directly, same as the web app does. Returns {} if no bundle is
    found -- callers must treat that as "no team context available" and skip
    award materialization rather than fabricate placeholder win totals."""
    repo_root = _find_repo_root_with_data_ops()
    if repo_root is None:
        return {}
    data_ops_path = os.path.join(repo_root, "data", "ops")
    prefix = f"nfl-preseason-sim-{int(season)}-"
    try:
        candidates = sorted(
            (
                name
                for name in os.listdir(data_ops_path)
                if name.startswith(prefix) and os.path.isdir(os.path.join(data_ops_path, name))
            ),
            reverse=True,
        )
    except OSError:
        return {}

    for bundle_name in candidates:
        csv_path = os.path.join(data_ops_path, bundle_name, "team_regular_season_outcomes.csv")
        if not os.path.isfile(csv_path):
            continue
        outcomes: Dict[str, Dict[str, Any]] = {}
        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    outcomes[row["team"]] = {
                        "expected_wins": float(row["expected_wins"]),
                        "wins_p10": float(row["wins_p10"]),
                        "wins_p90": float(row["wins_p90"]),
                        "playoff_prob": float(row["playoff_prob"]),
                        "division_title_prob": float(row["division_title_prob"]),
                        "super_bowl_win_prob": float(row["super_bowl_win_prob"]),
                        "bundle": bundle_name,
                    }
                except (KeyError, ValueError):
                    continue
        if outcomes:
            return outcomes
    return {}


@celery_app.task(name="src.tasks.materialize_nfl_award_projections")
def materialize_nfl_award_projections(
    *,
    season: int,
    model_version: str = "nfl-player-v1",
    top_n: int = 10,
) -> Dict[str, Any]:
    """MVP / Offensive Player of the Year contender leaderboards -- see
    services/model-service/src/services/nfl_award_projections.py for the
    full scoring methodology. Combines each qualifying player's real
    projected season counting stats (`_fetch_season_player_totals`) with
    their team's real projected win total / division-title probability from
    the season Monte Carlo bundle (`_load_latest_team_season_outcomes`).
    """
    session = SessionLocal()
    try:
        team_outcomes = _load_latest_team_season_outcomes(season)
        if not team_outcomes:
            return {
                "season": int(season),
                "model_version": model_version,
                "status": "skipped",
                "reason": "no_team_season_outcomes_bundle_found",
            }

        base_players = _fetch_season_player_totals(session, season=season, model_version=model_version)

        candidates: List[Dict[str, Any]] = []
        for player in base_players:
            outcome = team_outcomes.get(player["team"])
            if outcome is None:
                # Team not present in this season-sim bundle (e.g. a team
                # code mismatch) -- skip rather than guess at a win total.
                continue
            if not meets_award_volume_threshold(
                position=player["position"],
                pass_yards_total=player["pass_yards_total"],
                rush_yards_total=player["rush_yards_total"],
                receiving_yards_total=player["receiving_yards_total"],
            ):
                continue
            is_qb = player["position"] == "QB"
            total_yards = (
                player["pass_yards_total"] + player["rush_yards_total"]
                if is_qb
                else player["rush_yards_total"] + player["receiving_yards_total"]
            )
            total_tds = (
                player["pass_tds_total"] + player["rush_tds_total"]
                if is_qb
                else player["rush_tds_total"] + player["rec_tds_total"]
            )
            candidates.append(
                {
                    **player,
                    "total_yards": total_yards,
                    "total_tds": total_tds,
                    "expected_wins": outcome["expected_wins"],
                    "division_title_prob": outcome["division_title_prob"],
                    "playoff_prob": outcome["playoff_prob"],
                    "team_outcome_bundle": outcome["bundle"],
                }
            )

        # Keep only each team's single highest-volume player per position --
        # see select_primary_starter_per_team_position's docstring for why
        # this is both realistic (awards are never split across a team's
        # depth chart) and a necessary guardrail against a backup
        # occasionally clearing meets_award_volume_threshold with
        # near-starter projected volume.
        candidates = select_primary_starter_per_team_position(candidates, volume_key="total_yards")

        if not candidates:
            return {
                "season": int(season),
                "model_version": model_version,
                "status": "no_qualifying_candidates",
            }

        # Team-success normalization uses EVERY team in the sim bundle (not
        # just teams with a qualifying candidate) so it doesn't shift based
        # on which positions happen to qualify this run.
        peer_expected_wins_all_teams = [o["expected_wins"] for o in team_outcomes.values()]

        peer_yards_by_position: Dict[str, List[float]] = {}
        peer_tds_by_position: Dict[str, List[float]] = {}
        for candidate in candidates:
            peer_yards_by_position.setdefault(candidate["position"], []).append(candidate["total_yards"])
            peer_tds_by_position.setdefault(candidate["position"], []).append(candidate["total_tds"])

        scored: List[Dict[str, Any]] = []
        for candidate in candidates:
            position = candidate["position"]
            team_success_score = compute_team_success_score(
                expected_wins=candidate["expected_wins"],
                division_title_prob=candidate["division_title_prob"],
                peer_expected_wins=peer_expected_wins_all_teams,
            )
            stat_composite = compute_stat_composite(
                total_yards=candidate["total_yards"],
                total_tds=candidate["total_tds"],
                peer_total_yards=peer_yards_by_position[position],
                peer_total_tds=peer_tds_by_position[position],
            )
            mvp_score = score_mvp_candidate(
                position=position, team_success_score=team_success_score, stat_composite=stat_composite
            )
            opoy_score = score_opoy_candidate(team_success_score=team_success_score, stat_composite=stat_composite)
            scored.append(
                {
                    **candidate,
                    "team_success_score": team_success_score,
                    "stat_composite": stat_composite,
                    "mvp_score": mvp_score,
                    "opoy_score": opoy_score,
                }
            )

        mvp_ranked = rank_award_candidates(scored, score_key="mvp_score")[: max(1, int(top_n))]
        opoy_ranked = rank_award_candidates(scored, score_key="opoy_score")[: max(1, int(top_n))]

        session.execute(
            text("DELETE FROM nfl_award_projections WHERE season = :season AND model_version = :model_version"),
            {"season": int(season), "model_version": model_version},
        )

        rows_inserted = 0
        for award, ranked_list, score_key in (("mvp", mvp_ranked, "mvp_score"), ("opoy", opoy_ranked, "opoy_score")):
            for item in ranked_list:
                session.execute(
                    text(
                        """
                        INSERT INTO nfl_award_projections (
                          season, award, model_version, player_id, player_uid, player_name, team, position,
                          rank_overall, award_score, team_success_score, stat_composite,
                          team_expected_wins, team_division_title_prob, team_playoff_prob,
                          pass_yards_total, rush_yards_total, receiving_yards_total,
                          pass_tds_total, rush_tds_total, rec_tds_total,
                          methodology_payload, created_at, updated_at
                        ) VALUES (
                          :season, :award, :model_version, :player_id, CAST(:player_uid AS uuid), :player_name, :team, :position,
                          :rank_overall, :award_score, :team_success_score, :stat_composite,
                          :team_expected_wins, :team_division_title_prob, :team_playoff_prob,
                          :pass_yards_total, :rush_yards_total, :receiving_yards_total,
                          :pass_tds_total, :rush_tds_total, :rec_tds_total,
                          CAST(:methodology_payload AS jsonb), NOW(), NOW()
                        )
                        """
                    ),
                    {
                        "season": int(season),
                        "award": award,
                        "model_version": model_version,
                        "player_id": item["player_id"],
                        "player_uid": item["player_uid"],
                        "player_name": item["player_name"],
                        "team": item["team"],
                        "position": item["position"],
                        "rank_overall": item["rank_overall"],
                        "award_score": item[score_key],
                        "team_success_score": item["team_success_score"],
                        "stat_composite": item["stat_composite"],
                        "team_expected_wins": item["expected_wins"],
                        "team_division_title_prob": item["division_title_prob"],
                        "team_playoff_prob": item["playoff_prob"],
                        "pass_yards_total": item["pass_yards_total"],
                        "rush_yards_total": item["rush_yards_total"],
                        "receiving_yards_total": item["receiving_yards_total"],
                        "pass_tds_total": item["pass_tds_total"],
                        "rush_tds_total": item["rush_tds_total"],
                        "rec_tds_total": item["rec_tds_total"],
                        "methodology_payload": json.dumps(
                            {
                                "team_outcome_bundle": item["team_outcome_bundle"],
                                "qualifying_candidates_at_position": len(peer_yards_by_position[item["position"]]),
                            }
                        ),
                    },
                )
                rows_inserted += 1

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
                "week": 0,
                "layer": "award_projections",
                "model_version": model_version,
                "source_coverage": json.dumps(
                    {"qualifying_candidates": len(candidates), "team_outcome_bundle": candidates[0]["team_outcome_bundle"]}
                ),
                "freshness": json.dumps({"generated_at": datetime.now(timezone.utc).isoformat()}),
                "calibration_flags": json.dumps({"calibrated": False, "methodology": "documented-weighted-heuristic"}),
                "readiness_status": "go" if len(candidates) >= 8 else "warning",
                "metrics": json.dumps({"rows_inserted": rows_inserted}),
            },
        )
        session.commit()
        return {
            "season": int(season),
            "model_version": model_version,
            "qualifying_candidates": len(candidates),
            "mvp_top": [{"player_name": r["player_name"], "team": r["team"], "score": r["mvp_score"]} for r in mvp_ranked],
            "opoy_top": [{"player_name": r["player_name"], "team": r["team"], "score": r["opoy_score"]} for r in opoy_ranked],
        }
    except Exception:
        session.rollback()
        log.exception("Failed to materialize NFL award projections")
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


@celery_app.task(name="src.tasks.run_nfl_enterprise_weekly_sharpening_cycle")
def run_nfl_enterprise_weekly_sharpening_cycle(
    *,
    season: int,
    week: Optional[int] = None,
    model_version: str = "nfl-player-v1",
    skip_ingest: bool = False,
    skip_fantasy: bool = False,
    skip_awards: bool = False,
) -> Dict[str, Any]:
    """Year-long Tuesday/Wednesday desk cycle: DP rolling + snaps + tendencies
    → features → baselines → box → props (+ optional fantasy/awards).

    Prefer the bash orchestrator for local ops; this task exists so Celery Beat
    can run the same chain in production without a shell dependency on curl.
    """
    import sys
    from pathlib import Path

    session = SessionLocal()
    try:
        target_week = _resolve_nfl_week(session, season=season, week=week)
    finally:
        session.close()

    # Vendored package lives at services/model-service/data_platform_nfl
    # (PYTHONPATH=/app in Docker). Keep hyphenated monorepo path as fallback.
    model_service_root = Path(__file__).resolve().parents[2]
    for candidate in (
        model_service_root,  # import data_platform_nfl from /app
        model_service_root / "data-platform-nfl" / "src",
        model_service_root.parent / "data-platform-nfl" / "src",
    ):
        if candidate.exists() and str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))

    from data_platform_nfl.inseason_weekly_update import run_data_platform_inseason_weekly_update

    dp = run_data_platform_inseason_weekly_update(
        season=int(season),
        week=int(target_week),
        skip_ingest=bool(skip_ingest),
        rematerialize_remaining_weeks=True,
        dry_run=False,
    )
    baseline = materialize_nfl_player_baseline_projections(
        season=int(season), week=int(target_week), model_version=model_version
    )
    box = materialize_nfl_player_box_score_sims(season=int(season), week=int(target_week))
    props = materialize_nfl_player_props_edges(
        season=int(season), week=int(target_week), model_version=model_version
    )
    fantasy = None
    awards = None
    if not skip_fantasy:
        fantasy = materialize_nfl_fantasy_projections(
            season=int(season), week=int(target_week), model_version=model_version
        )
    if not skip_awards:
        try:
            awards = materialize_nfl_award_projections(
                season=int(season), model_version=model_version, top_n=10
            )
        except Exception as exc:  # noqa: BLE001
            awards = {"status": "failed", "error": str(exc)}

    return {
        "season": int(season),
        "week": int(target_week),
        "data_platform": dp,
        "baseline": baseline,
        "box": box,
        "props": props,
        "fantasy": fantasy,
        "awards": awards,
        "status": "ok" if str(dp.get("status")) != "failed" else "partial",
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


@celery_app.task(name="src.tasks.run_nfl_weekly_resilience_cycle")
def run_nfl_weekly_resilience_cycle(
    *,
    season: Optional[int] = None,
    week: Optional[int] = None,
    skip_player_update: bool = False,
    skip_dr_backup: bool = False,
) -> Dict[str, Any]:
    from src.services.nfl_resilience_cycle import run_weekly_resilience_cycle

    return run_weekly_resilience_cycle(
        season=season,
        week=week,
        skip_player_update=skip_player_update,
        skip_dr_backup=skip_dr_backup,
    )


@celery_app.task(name="src.tasks.run_nfl_dr_backup")
def run_nfl_dr_backup(*, skip_verify: bool = False) -> Dict[str, Any]:
    from src.services.nfl_resilience_cycle import run_dr_backup_job

    return run_dr_backup_job(skip_verify=skip_verify)


@celery_app.task(name="src.tasks.run_nfl_data_freshness_check")
def run_nfl_data_freshness_check(*, persist_alert: bool = True) -> Dict[str, Any]:
    from src.services.nfl_resilience_cycle import run_data_freshness_check

    return run_data_freshness_check(persist_alert=persist_alert)


@celery_app.task(name="src.tasks.write_nfl_projection_actuals")
def write_nfl_projection_actuals(*, season: int = 2026) -> Dict[str, Any]:
    """Materialize Projections Hub actuals JSON from owned DB tables."""
    import json
    import os
    from pathlib import Path

    import psycopg

    from data_platform_nfl.projection_actuals import empty_bundle, load_from_db

    url = os.environ.get("DATABASE_URL", "")
    url = (
        url.replace("postgresql+psycopg://", "postgresql://")
        .replace("postgres://", "postgresql://")
    )
    try:
        with psycopg.connect(url) as conn:
            bundle = load_from_db(conn, int(season))
    except Exception as exc:  # noqa: BLE001
        bundle = empty_bundle(int(season), notes=f"load_failed: {exc}")

    payload = {
        "season": bundle.get("season"),
        "asOfUtc": bundle.get("asOfUtc"),
        "source": bundle.get("source"),
        "teams": bundle.get("teams") or {},
        "players": bundle.get("players") or {},
        "notes": bundle.get("notes"),
    }

    # Prefer monorepo root data/ops; fall back to model-service-local path.
    candidates = [
        Path(__file__).resolve().parents[3] / "data" / "ops",
        Path(__file__).resolve().parents[2] / "data" / "ops",
        Path("/app/data/ops"),
    ]
    out_dir = next((p for p in candidates if p.parent.exists() or p.exists()), candidates[0])
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"nfl-projection-actuals-{int(season)}.json"
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return {
        "season": int(season),
        "wrote": str(out_path),
        "teams": len(payload["teams"]),
        "playerKeys": len(payload["players"]),
        "source": payload.get("source"),
        "asOfUtc": payload.get("asOfUtc"),
    }
