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
TASK_PULL_MLB_CONTEXT = os.getenv("TASK_PULL_MLB_CONTEXT", "src.tasks.pull_mlb_context_snapshot")
TASK_RUN_MLB_SIMULATIONS = os.getenv(
    "TASK_RUN_MLB_SIMULATIONS", "src.tasks.run_mlb_market_simulations"
)
TASK_PULL_MLB_OUTCOMES = os.getenv("TASK_PULL_MLB_OUTCOMES", "src.tasks.pull_mlb_outcomes")
TASK_PULL_MLB_DATA_LAKE = os.getenv("TASK_PULL_MLB_DATA_LAKE", "src.tasks.pull_mlb_data_lake_snapshot")
TASK_RUN_MLB_DAILY_CYCLE = os.getenv("TASK_RUN_MLB_DAILY_CYCLE", "src.tasks.run_mlb_daily_cycle")
TASK_EVAL_MLB_PROMOTION = os.getenv("TASK_EVAL_MLB_PROMOTION", "src.tasks.evaluate_mlb_model_promotion")
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

ACTIVE_START_HOUR = os.getenv("ODDS_PULL_ACTIVE_START_HOUR", "7")   # 7am
ACTIVE_END_HOUR = os.getenv("ODDS_PULL_ACTIVE_END_HOUR", "21")      # 9pm
LATE_START_HOUR = os.getenv("ODDS_PULL_LATE_START_HOUR", "22")      # 10pm
LATE_END_HOUR = os.getenv("ODDS_PULL_LATE_END_HOUR", "23")          # 11pm

ACTIVE_MINUTE_PATTERN = os.getenv("ODDS_PULL_ACTIVE_MINUTE_PATTERN", "*/30")
LATE_MINUTE = os.getenv("ODDS_PULL_LATE_MINUTE", "0")

ODDS_QUEUE = os.getenv("CELERY_ODDS_QUEUE", "odds")
MODELS_QUEUE = os.getenv("CELERY_MODELS_QUEUE", "models")

beat_schedule: Dict[str, Dict[str, Any]] = {
    "pull-odds-every-30-min-active": {
        "task": TASK_PULL_ODDS_SNAPSHOT,
        "schedule": crontab(
            minute=ACTIVE_MINUTE_PATTERN,
            hour=f"{ACTIVE_START_HOUR}-{ACTIVE_END_HOUR}",
        ),
        "options": {"queue": ODDS_QUEUE},
    },
    "pull-odds-hourly-late": {
        "task": TASK_PULL_ODDS_SNAPSHOT,
        "schedule": crontab(
            minute=LATE_MINUTE,
            hour=f"{LATE_START_HOUR}-{LATE_END_HOUR}",
        ),
        "options": {"queue": ODDS_QUEUE},
    },
    "pull-mlb-context-morning": {
        "task": TASK_PULL_MLB_CONTEXT,
        "schedule": crontab(minute="15", hour="6"),
        "kwargs": {"days_ahead": 5},
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