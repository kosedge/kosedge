"""
Celery Beat schedule for KosEdge.

- Single source of truth for periodic jobs
- Task names must match @celery_app.task(name="...")
- Environment overrides for easy tuning
"""

from __future__ import annotations

import os
from typing import Any, Dict

from celery.schedules import crontab

TASK_PULL_ODDS_SNAPSHOT = os.getenv("TASK_PULL_ODDS_SNAPSHOT", "src.tasks.pull_odds_snapshot")
TASK_PULL_NFL_CONTEXT = os.getenv("TASK_PULL_NFL_CONTEXT", "src.tasks.pull_nfl_context_snapshot")
TASK_RUN_NFL_SIMULATIONS = os.getenv("TASK_RUN_NFL_SIMULATIONS", "src.tasks.run_nfl_market_simulations")
TASK_MATERIALIZE_NFL_MARKET_HISTORY = os.getenv(
    "TASK_MATERIALIZE_NFL_MARKET_HISTORY",
    "src.tasks.materialize_nfl_market_history",
)
TASK_RUN_NFL_CLV_ATTRIBUTION = os.getenv(
    "TASK_RUN_NFL_CLV_ATTRIBUTION",
    "src.tasks.run_nfl_clv_attribution",
)
TASK_PULL_NFL_OUTCOMES = os.getenv("TASK_PULL_NFL_OUTCOMES", "src.tasks.pull_nfl_outcomes")
TASK_RUN_NFL_QUALITY_GRADING = os.getenv("TASK_RUN_NFL_QUALITY_GRADING", "src.tasks.run_nfl_quality_grading")
TASK_EVAL_NFL_PROMOTION = os.getenv("TASK_EVAL_NFL_PROMOTION", "src.tasks.evaluate_nfl_model_promotion")
TASK_RUN_NFL_SUPERVISED_RETRAIN = os.getenv(
    "TASK_RUN_NFL_SUPERVISED_RETRAIN", "src.tasks.run_nfl_supervised_retrain"
)
TASK_NFL_PLAYER_BASELINES = os.getenv(
    "TASK_NFL_PLAYER_BASELINES",
    "src.tasks.materialize_nfl_player_baseline_projections",
)
TASK_NFL_PLAYER_PROPS = os.getenv(
    "TASK_NFL_PLAYER_PROPS",
    "src.tasks.materialize_nfl_player_props_edges",
)
TASK_NFL_FANTASY = os.getenv(
    "TASK_NFL_FANTASY",
    "src.tasks.materialize_nfl_fantasy_projections",
)
TASK_NFL_PLAYER_CYCLE = os.getenv(
    "TASK_NFL_PLAYER_CYCLE",
    "src.tasks.run_nfl_player_projection_cycle",
)
TASK_NFL_IDENTITY_REFRESH = os.getenv(
    "TASK_NFL_IDENTITY_REFRESH",
    "src.tasks.run_nfl_identity_refresh",
)
TASK_NFL_IDENTITY_MANUAL_RESOLUTIONS = os.getenv(
    "TASK_NFL_IDENTITY_MANUAL_RESOLUTIONS",
    "src.tasks.apply_nfl_identity_manual_resolutions",
)
TASK_NFL_IDENTITY_QUALITY_SNAPSHOT = os.getenv(
    "TASK_NFL_IDENTITY_QUALITY_SNAPSHOT",
    "src.tasks.run_nfl_identity_quality_snapshot",
)
TASK_NFL_WEEKLY_RESILIENCE = os.getenv(
    "TASK_NFL_WEEKLY_RESILIENCE",
    "src.tasks.run_nfl_weekly_resilience_cycle",
)
TASK_NFL_ENTERPRISE_WEEKLY_SHARPENING = os.getenv(
    "TASK_NFL_ENTERPRISE_WEEKLY_SHARPENING",
    "src.tasks.run_nfl_enterprise_weekly_sharpening_cycle",
)
TASK_NFL_WALKFORWARD_BACKTEST = os.getenv(
    "TASK_NFL_WALKFORWARD_BACKTEST",
    "src.tasks.run_nfl_walkforward_backtest",
)
TASK_NFL_DR_BACKUP = os.getenv(
    "TASK_NFL_DR_BACKUP",
    "src.tasks.run_nfl_dr_backup",
)
TASK_NFL_DATA_FRESHNESS = os.getenv(
    "TASK_NFL_DATA_FRESHNESS",
    "src.tasks.run_nfl_data_freshness_check",
)
TASK_PULL_MLB_CONTEXT = os.getenv("TASK_PULL_MLB_CONTEXT", "src.tasks.pull_mlb_context_snapshot")
TASK_RUN_MLB_SIMULATIONS = os.getenv(
    "TASK_RUN_MLB_SIMULATIONS", "src.tasks.run_mlb_market_simulations"
)
TASK_PULL_MLB_OUTCOMES = os.getenv("TASK_PULL_MLB_OUTCOMES", "src.tasks.pull_mlb_outcomes")
TASK_PULL_MLB_DATA_LAKE = os.getenv("TASK_PULL_MLB_DATA_LAKE", "src.tasks.pull_mlb_data_lake_snapshot")
TASK_RUN_MLB_DAILY_CYCLE = os.getenv("TASK_RUN_MLB_DAILY_CYCLE", "src.tasks.run_mlb_daily_cycle")
TASK_EVAL_MLB_PROMOTION = os.getenv("TASK_EVAL_MLB_PROMOTION", "src.tasks.evaluate_mlb_model_promotion")
TASK_PULL_NBA_CONTEXT = os.getenv("TASK_PULL_NBA_CONTEXT", "src.tasks.pull_nba_context_snapshot")
TASK_RUN_NBA_SIMULATIONS = os.getenv(
    "TASK_RUN_NBA_SIMULATIONS", "src.tasks.run_nba_market_simulations"
)
TASK_PULL_NBA_INGEST = os.getenv("TASK_PULL_NBA_INGEST", "src.tasks.pull_nba_schedule_ingest")
TASK_NBA_ROLLING_FEATURES = os.getenv(
    "TASK_NBA_ROLLING_FEATURES", "src.tasks.materialize_nba_team_rolling_features"
)
TASK_NBA_DAILY_CYCLE = os.getenv("TASK_NBA_DAILY_CYCLE", "src.tasks.run_nba_daily_cycle")
TASK_MLB_NOWCAST_REPRICING = os.getenv(
    "TASK_MLB_NOWCAST_REPRICING",
    "src.tasks.run_mlb_lineup_nowcast_repricing",
)
TASK_MLB_WALKFORWARD_BACKTEST = os.getenv(
    "TASK_MLB_WALKFORWARD_BACKTEST",
    "src.tasks.run_mlb_walkforward_backtest",
)
TASK_MLB_FEATURE_ABLATION = os.getenv(
    "TASK_MLB_FEATURE_ABLATION",
    "src.tasks.run_mlb_feature_ablation",
)
TASK_MLB_DETERMINISM_CHECK = os.getenv(
    "TASK_MLB_DETERMINISM_CHECK",
    "src.tasks.run_mlb_determinism_check",
)
TASK_MLB_CLV_ATTRIBUTION = os.getenv(
    "TASK_MLB_CLV_ATTRIBUTION",
    "src.tasks.run_mlb_clv_attribution",
)
TASK_MLB_QUALITY_GRADING = os.getenv(
    "TASK_MLB_QUALITY_GRADING",
    "src.tasks.run_mlb_quality_grading",
)

# Pre-season / offseason default (Jul–Aug): hourly daytime + one 3am full refresh.
# In-season: override ODDS_PULL_ACTIVE_MINUTE_PATTERN to */5 or */10 around
# injury-report windows — do NOT redeploy for cadence changes.
ACTIVE_START_HOUR = os.getenv("ODDS_PULL_ACTIVE_START_HOUR", "7")
ACTIVE_END_HOUR = os.getenv("ODDS_PULL_ACTIVE_END_HOUR", "23")
# Single overnight slot (3:00) unless explicitly widened.
LATE_START_HOUR = os.getenv("ODDS_PULL_LATE_START_HOUR", "3")
LATE_END_HOUR = os.getenv("ODDS_PULL_LATE_END_HOUR", "3")

ACTIVE_MINUTE_PATTERN = os.getenv("ODDS_PULL_ACTIVE_MINUTE_PATTERN", "0")  # top of each hour
LATE_MINUTE_PATTERN = os.getenv("ODDS_PULL_LATE_MINUTE_PATTERN", "0")
LATE_MINUTE = os.getenv("ODDS_PULL_LATE_MINUTE", "0")
NFL_BOARD_REFRESH_MINUTE = os.getenv("NFL_SEASON_BOARD_REFRESH_MINUTE", "15")
NFL_BOARD_REFRESH_HOURS = os.getenv("NFL_SEASON_BOARD_REFRESH_HOURS", "7-23")
NFL_CONTEXT_REFRESH_MINUTE = os.getenv("NFL_CONTEXT_REFRESH_MINUTE", "20")

ODDS_QUEUE = os.getenv("CELERY_ODDS_QUEUE", "odds")
MODELS_QUEUE = os.getenv("CELERY_MODELS_QUEUE", "models")

beat_schedule: Dict[str, Dict[str, Any]] = {
    "pull-odds-season-cadence": {
        "task": TASK_PULL_ODDS_SNAPSHOT,
        "schedule": crontab(
            minute=ACTIVE_MINUTE_PATTERN,
            hour=f"{ACTIVE_START_HOUR}-{ACTIVE_END_HOUR}",
        ),
        "options": {"queue": ODDS_QUEUE},
    },
    # 3:00am ET — odds pull (part of full site data refresh).
    "pull-odds-3am-refresh": {
        "task": TASK_PULL_ODDS_SNAPSHOT,
        "schedule": crontab(
            minute=LATE_MINUTE_PATTERN if LATE_MINUTE_PATTERN else LATE_MINUTE,
            hour=f"{LATE_START_HOUR}-{LATE_END_HOUR}",
        ),
        "options": {"queue": ODDS_QUEUE},
    },
    # Hourly daytime board refresh (fair-lines / edges) — not a container redeploy.
    "run-nfl-season-board-refresh": {
        "task": TASK_RUN_NFL_SIMULATIONS,
        "schedule": crontab(
            minute=NFL_BOARD_REFRESH_MINUTE,
            hour=NFL_BOARD_REFRESH_HOURS,
        ),
        "kwargs": {
            "simulations": int(os.getenv("NFL_SEASON_BOARD_SIM_COUNT", "1500")),
            "model_version": os.getenv("NFL_BASE_MODEL_VERSION", "nfl-v1.5-matchup-sim"),
        },
        "options": {"queue": MODELS_QUEUE},
    },
    "pull-nfl-context-season-cadence": {
        "task": TASK_PULL_NFL_CONTEXT,
        "schedule": crontab(
            minute=NFL_CONTEXT_REFRESH_MINUTE,
            hour=NFL_BOARD_REFRESH_HOURS,
        ),
        "kwargs": {"days_ahead": int(os.getenv("NFL_CONTEXT_DAYS_AHEAD", "14"))},
        "options": {"queue": MODELS_QUEUE},
    },
    # 3:05am context + 3:15am fuller sims = "reset/refresh the whole site" data layer.
    "pull-nfl-context-3am-refresh": {
        "task": TASK_PULL_NFL_CONTEXT,
        "schedule": crontab(minute="5", hour="3"),
        "kwargs": {"days_ahead": int(os.getenv("NFL_CONTEXT_DAYS_AHEAD", "14"))},
        "options": {"queue": MODELS_QUEUE},
    },
    "run-nfl-simulations-3am-refresh": {
        "task": TASK_RUN_NFL_SIMULATIONS,
        "schedule": crontab(minute="15", hour="3"),
        "kwargs": {
            "simulations": int(os.getenv("NFL_SIM_3AM_COUNT", os.getenv("NFL_SIM_DAILY_COUNT", "4000"))),
            "model_version": os.getenv("NFL_BASE_MODEL_VERSION", "nfl-v1.5-matchup-sim"),
        },
        "options": {"queue": MODELS_QUEUE},
    },
    "materialize-nfl-market-history-3am-refresh": {
        "task": TASK_MATERIALIZE_NFL_MARKET_HISTORY,
        "schedule": crontab(minute="25", hour="3"),
        "kwargs": {"lookback_days": int(os.getenv("NFL_MARKET_HISTORY_LOOKBACK_DAYS", "45"))},
        "options": {"queue": MODELS_QUEUE},
    },
    "pull-mlb-context-morning": {
        "task": TASK_PULL_MLB_CONTEXT,
        "schedule": crontab(minute="15", hour="6"),
        "kwargs": {"days_ahead": 5},
        "options": {"queue": MODELS_QUEUE},
    },
    # NBA Phase 0/1 — light cadence; offseason empty slate is honest.
    "pull-nba-ingest-morning": {
        "task": TASK_PULL_NBA_INGEST,
        "schedule": crontab(minute="20", hour="6"),
        "kwargs": {
            "days_back": int(os.getenv("NBA_INGEST_DAYS_BACK", "7")),
            "days_ahead": int(os.getenv("NBA_INGEST_DAYS_AHEAD", "3")),
        },
        "options": {"queue": MODELS_QUEUE},
    },
    "pull-nba-context-morning": {
        "task": TASK_PULL_NBA_CONTEXT,
        "schedule": crontab(minute="30", hour="6"),
        "kwargs": {"days_ahead": int(os.getenv("NBA_CONTEXT_DAYS_AHEAD", "3"))},
        "options": {"queue": MODELS_QUEUE},
    },
    "run-nba-simulations-morning": {
        "task": TASK_RUN_NBA_SIMULATIONS,
        "schedule": crontab(minute="40", hour="6"),
        "kwargs": {
            "simulations": int(os.getenv("NBA_SIM_DAILY_COUNT", "4000")),
            "model_version": os.getenv("NBA_BASE_MODEL_VERSION", "nba-v1-poss-sim"),
        },
        "options": {"queue": MODELS_QUEUE},
    },
    # Phase 2 chained cycle: rolling → context → sim (skips empty offseason).
    "run-nba-daily-cycle-3am": {
        "task": TASK_NBA_DAILY_CYCLE,
        "schedule": crontab(minute="45", hour="3"),
        "kwargs": {
            "days_ahead": int(os.getenv("NBA_CONTEXT_DAYS_AHEAD", "3")),
            "simulations": int(os.getenv("NBA_SIM_DAILY_COUNT", "4000")),
            "model_version": os.getenv("NBA_BASE_MODEL_VERSION", "nba-v1-poss-sim"),
        },
        "options": {"queue": MODELS_QUEUE},
    },
    "materialize-nba-rolling-features-nightly": {
        "task": TASK_NBA_ROLLING_FEATURES,
        "schedule": crontab(minute="50", hour="3"),
        "kwargs": {
            "days_back": int(os.getenv("NBA_ROLLING_DAYS_BACK", "30")),
            "window_games": int(os.getenv("NBA_ROLLING_WINDOW_GAMES", "10")),
        },
        "options": {"queue": MODELS_QUEUE},
    },
    "pull-nfl-context-morning": {
        "task": TASK_PULL_NFL_CONTEXT,
        "schedule": crontab(minute="5", hour="6"),
        "kwargs": {"days_ahead": int(os.getenv("NFL_CONTEXT_DAYS_AHEAD", "14"))},
        "options": {"queue": MODELS_QUEUE},
    },
    "run-nfl-simulations-daily": {
        "task": TASK_RUN_NFL_SIMULATIONS,
        "schedule": crontab(minute="12", hour="6"),
        "kwargs": {
            "simulations": int(os.getenv("NFL_SIM_DAILY_COUNT", "4000")),
            "model_version": os.getenv("NFL_BASE_MODEL_VERSION", "nfl-v1.5-matchup-sim"),
        },
        "options": {"queue": MODELS_QUEUE},
    },
    "materialize-nfl-market-history-hourly": {
        "task": TASK_MATERIALIZE_NFL_MARKET_HISTORY,
        "schedule": crontab(minute="17"),
        "kwargs": {"lookback_days": int(os.getenv("NFL_MARKET_HISTORY_LOOKBACK_DAYS", "45"))},
        "options": {"queue": MODELS_QUEUE},
    },
    "run-nfl-clv-attribution-morning": {
        "task": TASK_RUN_NFL_CLV_ATTRIBUTION,
        "schedule": crontab(minute="28", hour="6"),
        "kwargs": {
            "lookback_days": int(os.getenv("NFL_CLV_LOOKBACK_DAYS", "45")),
            "model_version": os.getenv("NFL_BASE_MODEL_VERSION", "nfl-v1.5-matchup-sim"),
        },
        "options": {"queue": MODELS_QUEUE},
    },
    "pull-nfl-outcomes-nightly": {
        "task": TASK_PULL_NFL_OUTCOMES,
        "schedule": crontab(minute="18", hour="3"),
        "kwargs": {"days_back": int(os.getenv("NFL_OUTCOMES_LOOKBACK_DAYS", "60"))},
        "options": {"queue": MODELS_QUEUE},
    },
    "run-nfl-quality-grading-morning": {
        "task": TASK_RUN_NFL_QUALITY_GRADING,
        "schedule": crontab(minute="40", hour="6"),
        "kwargs": {
            "lookback_days": int(os.getenv("NFL_QUALITY_LOOKBACK_DAYS", "60")),
            "model_version": os.getenv("NFL_BASE_MODEL_VERSION", "nfl-v1.5-matchup-sim"),
        },
        "options": {"queue": MODELS_QUEUE},
    },
    "evaluate-nfl-promotion-morning": {
        "task": TASK_EVAL_NFL_PROMOTION,
        "schedule": crontab(minute="52", hour="6"),
        "kwargs": {
            "challenger_model_version": os.getenv("NFL_CHALLENGER_MODEL_VERSION", "nfl-v1.6-enterprise"),
            "lookback_days": int(os.getenv("NFL_PROMOTION_LOOKBACK_DAYS", "45")),
            "auto_promote": os.getenv("NFL_AUTO_PROMOTE_ENABLED", "false").strip().lower() in {"1", "true", "yes", "y", "on"},
        },
        "options": {"queue": MODELS_QUEUE},
    },
    "run-nfl-supervised-retrain-weekly": {
        "task": TASK_RUN_NFL_SUPERVISED_RETRAIN,
        # Weekly (not daily): new *completed* games only arrive once a week,
        # so daily retraining would just refit on the same data. Tuesday
        # morning, after Monday Night Football has graded out and outcomes
        # have been pulled (pull-nfl-outcomes-nightly, 3:18am) and quality
        # grading (evaluate-nfl-promotion-morning, 6:52am) has run.
        "schedule": crontab(minute="5", hour="7", day_of_week=os.getenv("NFL_SUPERVISED_RETRAIN_DAY_OF_WEEK", "tue")),
        "kwargs": {
            "model_version": os.getenv("NFL_BASE_MODEL_VERSION", "nfl-v1.5-matchup-sim"),
            "start_season": int(os.getenv("NFL_SUPERVISED_RETRAIN_START_SEASON", "2013")),
            "end_season": int(os.getenv("NFL_SUPERVISED_RETRAIN_END_SEASON", "2026")),
        },
        "options": {"queue": MODELS_QUEUE},
    },
    "run-nfl-player-cycle-thursday": {
        "task": TASK_NFL_PLAYER_CYCLE,
        "schedule": crontab(minute="8", hour="7", day_of_week=os.getenv("NFL_PLAYER_CYCLE_DAY_OF_WEEK", "thu")),
        "kwargs": {
            "season": int(os.getenv("NFL_PLAYER_CYCLE_SEASON", "2026")),
            "week": int(os.getenv("NFL_PLAYER_CYCLE_WEEK", "1")),
            "model_version": os.getenv("NFL_PLAYER_MODEL_VERSION", "nfl-player-v1"),
        },
        "options": {"queue": MODELS_QUEUE},
    },
    "run-nfl-player-props-hourly": {
        "task": TASK_NFL_PLAYER_PROPS,
        "schedule": crontab(minute="13"),
        "kwargs": {
            "season": int(os.getenv("NFL_PLAYER_CYCLE_SEASON", "2026")),
            "week": int(os.getenv("NFL_PLAYER_CYCLE_WEEK", "1")),
            "model_version": os.getenv("NFL_PLAYER_MODEL_VERSION", "nfl-player-v1"),
        },
        "options": {"queue": MODELS_QUEUE},
    },
    "run-nfl-fantasy-refresh-twice-daily": {
        "task": TASK_NFL_FANTASY,
        "schedule": crontab(minute="42", hour="6,11"),
        "kwargs": {
            "season": int(os.getenv("NFL_PLAYER_CYCLE_SEASON", "2026")),
            "week": int(os.getenv("NFL_PLAYER_CYCLE_WEEK", "1")),
            "model_version": os.getenv("NFL_PLAYER_MODEL_VERSION", "nfl-player-v1"),
        },
        "options": {"queue": MODELS_QUEUE},
    },
    "run-nfl-identity-refresh-weekly": {
        "task": TASK_NFL_IDENTITY_REFRESH,
        "schedule": crontab(minute="22", hour="5", day_of_week=os.getenv("NFL_IDENTITY_REFRESH_DAY_OF_WEEK", "tue")),
        "kwargs": {
            "season": int(os.getenv("NFL_PLAYER_CYCLE_SEASON", "2026")),
            "week": int(os.getenv("NFL_PLAYER_CYCLE_WEEK", "1")),
            "model_version": os.getenv("NFL_PLAYER_MODEL_VERSION", "nfl-player-v1"),
        },
        "options": {"queue": MODELS_QUEUE},
    },
    "run-nfl-identity-manual-resolutions-weekly": {
        "task": TASK_NFL_IDENTITY_MANUAL_RESOLUTIONS,
        "schedule": crontab(minute="38", hour="5", day_of_week=os.getenv("NFL_IDENTITY_REFRESH_DAY_OF_WEEK", "tue")),
        "kwargs": {
            "limit": int(os.getenv("NFL_IDENTITY_MANUAL_REVIEW_LIMIT", "200")),
            "reviewer": os.getenv("NFL_IDENTITY_DEFAULT_REVIEWER", "system-weekly-identity-sync"),
        },
        "options": {"queue": MODELS_QUEUE},
    },
    "run-nfl-identity-quality-snapshot-weekly": {
        "task": TASK_NFL_IDENTITY_QUALITY_SNAPSHOT,
        "schedule": crontab(minute="48", hour="5", day_of_week=os.getenv("NFL_IDENTITY_REFRESH_DAY_OF_WEEK", "tue")),
        "kwargs": {
            "season": int(os.getenv("NFL_PLAYER_CYCLE_SEASON", "2026")),
            "week": int(os.getenv("NFL_PLAYER_CYCLE_WEEK", "1")),
            "source_system": None,
        },
        "options": {"queue": MODELS_QUEUE},
    },
    # Tuesday ownership cycle: ingest → player rematerialize → DR backup → freshness.
    # Runs after overnight outcomes (03:18) and before supervised retrain (07:05).
    "run-nfl-weekly-resilience-cycle": {
        "task": TASK_NFL_WEEKLY_RESILIENCE,
        "schedule": crontab(
            minute=os.getenv("NFL_RESILIENCE_CYCLE_MINUTE", "15"),
            hour=os.getenv("NFL_RESILIENCE_CYCLE_HOUR", "4"),
            day_of_week=os.getenv("NFL_RESILIENCE_CYCLE_DAY_OF_WEEK", "tue"),
        ),
        "kwargs": {
            "skip_player_update": os.getenv("NFL_RESILIENCE_SKIP_PLAYER_UPDATE", "false")
            .strip()
            .lower()
            in {"1", "true", "yes", "y", "on"},
            "skip_dr_backup": os.getenv("NFL_RESILIENCE_SKIP_DR_BACKUP", "false")
            .strip()
            .lower()
            in {"1", "true", "yes", "y", "on"},
        },
        "options": {"queue": MODELS_QUEUE},
    },
    # Full enterprise sharpening: snaps + tendencies + rolling usage + features
    # + baselines/box/props. Set NFL_PLAYER_CYCLE_WEEK each week (or automate
    # week resolution inside the task via _resolve_nfl_week).
    "run-nfl-enterprise-weekly-sharpening": {
        "task": TASK_NFL_ENTERPRISE_WEEKLY_SHARPENING,
        "schedule": crontab(
            minute=os.getenv("NFL_ENTERPRISE_WEEKLY_MINUTE", "40"),
            hour=os.getenv("NFL_ENTERPRISE_WEEKLY_HOUR", "5"),
            day_of_week=os.getenv("NFL_ENTERPRISE_WEEKLY_DAY_OF_WEEK", "tue"),
        ),
        "kwargs": {
            "season": int(os.getenv("NFL_PLAYER_CYCLE_SEASON", "2026")),
            "week": int(os.getenv("NFL_PLAYER_CYCLE_WEEK", "1")),
            "model_version": os.getenv("NFL_PLAYER_MODEL_VERSION", "nfl-player-v1"),
            "skip_ingest": os.getenv("NFL_ENTERPRISE_WEEKLY_SKIP_INGEST", "false")
            .strip()
            .lower()
            in {"1", "true", "yes", "y", "on"},
        },
        "options": {"queue": MODELS_QUEUE},
    },
    "run-nfl-walkforward-backtest-weekly": {
        "task": TASK_NFL_WALKFORWARD_BACKTEST,
        "schedule": crontab(
            minute=os.getenv("NFL_WALKFORWARD_MINUTE", "20"),
            hour=os.getenv("NFL_WALKFORWARD_HOUR", "8"),
            day_of_week=os.getenv("NFL_WALKFORWARD_DAY_OF_WEEK", "wed"),
        ),
        "kwargs": {
            "model_version": os.getenv("NFL_MODEL_VERSION", "nfl-v1.5-matchup-sim"),
            "lookback_days": int(os.getenv("NFL_WALKFORWARD_LOOKBACK_DAYS", "240")),
            "training_days": int(os.getenv("NFL_WALKFORWARD_TRAINING_DAYS", "56")),
            "step_days": int(os.getenv("NFL_WALKFORWARD_STEP_DAYS", "7")),
            "apply_calibration": True,
        },
        "options": {"queue": MODELS_QUEUE},
    },
    "run-nfl-data-freshness-check-morning": {
        "task": TASK_NFL_DATA_FRESHNESS,
        "schedule": crontab(minute="10", hour="8"),
        "kwargs": {"persist_alert": True},
        "options": {"queue": MODELS_QUEUE},
    },
    "run-nfl-dr-backup-sunday": {
        "task": TASK_NFL_DR_BACKUP,
        "schedule": crontab(
            minute="40",
            hour="3",
            day_of_week=os.getenv("NFL_DR_BACKUP_DAY_OF_WEEK", "sun"),
        ),
        "kwargs": {
            "skip_verify": os.getenv("NFL_DR_BACKUP_SKIP_VERIFY", "false")
            .strip()
            .lower()
            in {"1", "true", "yes", "y", "on"},
        },
        "options": {"queue": MODELS_QUEUE},
    },
    "run-mlb-simulations-daily": {
        "task": TASK_RUN_MLB_SIMULATIONS,
        "schedule": crontab(minute="20", hour="6"),
        "kwargs": {"simulations": int(os.getenv("MLB_SIM_DAILY_COUNT", "4000"))},
        "options": {"queue": MODELS_QUEUE},
    },
    "pull-mlb-outcomes-nightly": {
        "task": TASK_PULL_MLB_OUTCOMES,
        "schedule": crontab(minute="10", hour="3"),
        "kwargs": {"days_back": int(os.getenv("MLB_OUTCOMES_LOOKBACK_DAYS", "30"))},
        "options": {"queue": MODELS_QUEUE},
    },
    "pull-mlb-data-lake-nightly": {
        "task": TASK_PULL_MLB_DATA_LAKE,
        "schedule": crontab(minute="25", hour="3"),
        "kwargs": {
            "days_back": int(os.getenv("MLB_DATA_LAKE_DAYS_BACK", "60")),
            "days_ahead": int(os.getenv("MLB_DATA_LAKE_DAYS_AHEAD", "7")),
            "include_rosters": os.getenv("MLB_DATA_LAKE_INCLUDE_ROSTERS", "true").strip().lower() in {"1", "true", "yes", "y", "on"},
            "include_game_feeds": os.getenv("MLB_DATA_LAKE_INCLUDE_GAME_FEEDS", "true").strip().lower() in {"1", "true", "yes", "y", "on"},
        },
        "options": {"queue": MODELS_QUEUE},
    },
    "run-mlb-daily-cycle-morning": {
        "task": TASK_RUN_MLB_DAILY_CYCLE,
        "schedule": crontab(minute="35", hour="6"),
        "kwargs": {
            "days_ahead": int(os.getenv("MLB_DAILY_DAYS_AHEAD", "5")),
            "outcomes_lookback_days": int(os.getenv("MLB_OUTCOMES_LOOKBACK_DAYS", "60")),
            "simulations": int(os.getenv("MLB_SIM_DAILY_COUNT", "4000")),
            "base_model_version": os.getenv("MLB_BASE_MODEL_VERSION", "mlb-v1-pa-sim"),
            "challenger_model_version": os.getenv("MLB_CHALLENGER_MODEL_VERSION", "mlb-v2-pitch-sim"),
            "run_challenger": os.getenv("MLB_RUN_CHALLENGER", "true").strip().lower() in {"1", "true", "yes", "y", "on"},
            "calibration_lookback_days": int(os.getenv("MLB_CALIBRATION_LOOKBACK_DAYS", "45")),
        },
        "options": {"queue": MODELS_QUEUE},
    },
    "evaluate-mlb-promotion-morning": {
        "task": TASK_EVAL_MLB_PROMOTION,
        "schedule": crontab(minute="50", hour="6"),
        "kwargs": {
            "base_model_version": os.getenv("MLB_BASE_MODEL_VERSION", "mlb-v1-pa-sim"),
            "challenger_model_version": os.getenv("MLB_CHALLENGER_MODEL_VERSION", "mlb-v2-pitch-sim"),
            "lookback_days": int(os.getenv("MLB_CALIBRATION_LOOKBACK_DAYS", "45")),
            "auto_promote": os.getenv("MLB_AUTO_PROMOTE_ENABLED", "false").strip().lower() in {"1", "true", "yes", "y", "on"},
        },
        "options": {"queue": MODELS_QUEUE},
    },
    "run-mlb-clv-attribution-morning": {
        "task": TASK_MLB_CLV_ATTRIBUTION,
        "schedule": crontab(minute="42", hour="6"),
        "kwargs": {
            "model_version": os.getenv("MLB_BASE_MODEL_VERSION", "mlb-v1-pa-sim"),
            "lookback_days": int(os.getenv("MLB_CLV_LOOKBACK_DAYS", "45")),
        },
        "options": {"queue": MODELS_QUEUE},
    },
    "run-mlb-quality-grading-morning": {
        "task": TASK_MLB_QUALITY_GRADING,
        "schedule": crontab(minute="48", hour="6"),
        "kwargs": {
            "model_version": os.getenv("MLB_BASE_MODEL_VERSION", "mlb-v1-pa-sim"),
            "lookback_days": int(os.getenv("MLB_QUALITY_LOOKBACK_DAYS", "60")),
        },
        "options": {"queue": MODELS_QUEUE},
    },
    "run-mlb-lineup-nowcast-repricing": {
        "task": TASK_MLB_NOWCAST_REPRICING,
        "schedule": crontab(minute="*/10", hour="8-23"),
        "kwargs": {
            "horizon_hours": int(os.getenv("MLB_NOWCAST_HORIZON_HOURS", "18")),
            "simulations": int(os.getenv("MLB_NOWCAST_SIM_COUNT", "2500")),
            "base_model_version": os.getenv("MLB_BASE_MODEL_VERSION", "mlb-v1-pa-sim"),
            "challenger_model_version": os.getenv("MLB_CHALLENGER_MODEL_VERSION", "mlb-v2-pitch-sim"),
            "run_challenger": os.getenv("MLB_RUN_CHALLENGER", "true").strip().lower() in {"1", "true", "yes", "y", "on"},
        },
        "options": {"queue": MODELS_QUEUE},
    },
    "run-mlb-determinism-check-midday": {
        "task": TASK_MLB_DETERMINISM_CHECK,
        "schedule": crontab(minute="5", hour="12"),
        "kwargs": {
            "model_version": os.getenv("MLB_BASE_MODEL_VERSION", "mlb-v1-pa-sim"),
            "simulations": int(os.getenv("MLB_DETERMINISM_SIM_COUNT", "800")),
        },
        "options": {"queue": MODELS_QUEUE},
    },
    "run-mlb-feature-ablation-weekly": {
        "task": TASK_MLB_FEATURE_ABLATION,
        "schedule": crontab(minute="20", hour="7", day_of_week="mon"),
        "kwargs": {
            "model_version": os.getenv("MLB_BASE_MODEL_VERSION", "mlb-v1-pa-sim"),
            "simulations": int(os.getenv("MLB_ABLATION_SIM_COUNT", "1500")),
        },
        "options": {"queue": MODELS_QUEUE},
    },
    "run-mlb-walkforward-backtest-weekly": {
        "task": TASK_MLB_WALKFORWARD_BACKTEST,
        "schedule": crontab(minute="35", hour="7", day_of_week="mon"),
        "kwargs": {
            "model_version": os.getenv("MLB_BASE_MODEL_VERSION", "mlb-v1-pa-sim"),
            "lookback_days": int(os.getenv("MLB_BACKTEST_LOOKBACK_DAYS", "180")),
            "training_days": int(os.getenv("MLB_BACKTEST_TRAINING_DAYS", "45")),
            "step_days": int(os.getenv("MLB_BACKTEST_STEP_DAYS", "7")),
            "apply_calibration": os.getenv("MLB_BACKTEST_APPLY_CALIBRATION", "true").strip().lower() in {"1", "true", "yes", "y", "on"},
        },
        "options": {"queue": MODELS_QUEUE},
    },
}