"""2024–25 sealed holdout constants."""

from __future__ import annotations

from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
WEB = REPO / "apps" / "web"

HOLDOUT_ID = "ncaam_holdout_2024_25_v1"
SEASON_KEY = "2024-25"
SEASON_END_YEAR = 2025
WINDOW_START = date(2024, 11, 4)
WINDOW_END = date(2025, 4, 8)

SCHEMA_VERSION_SCHEDULE = "ncaam-schedule-sot-v1"
SCHEMA_VERSION_VENUE = "ncaam-venue-contract-v1"
SCHEMA_VERSION_FEATURE = "ncaam-holdout-feature-v1"
SCHEMA_VERSION_LABEL = "ncaam-holdout-label-v1"
SCHEMA_VERSION_SEAL = "ncaam-holdout-seal-v1"
SCHEMA_VERSION_PACKAGE = "ncaam-holdout-package-v1"

FEATURE_SCHEMA_VERSION = SCHEMA_VERSION_FEATURE
LABEL_SCHEMA_VERSION = SCHEMA_VERSION_LABEL
PACKAGE_SCHEMA_VERSION = SCHEMA_VERSION_PACKAGE

OUT_ROOT = REPO / "data" / "ops" / "lab" / "ncaam" / "holdout_2024_25"
RAW_ESPN_DIR = OUT_ROOT / "raw" / "espn_scoreboard"
SCHEDULE_DIR = OUT_ROOT / "schedule_sot"
VENUE_DIR = OUT_ROOT / "venue"
KENPOM_DIR = OUT_ROOT / "kenpom_audit"
ODDS_DIR = OUT_ROOT / "odds_audit"
FEATURE_DIR = OUT_ROOT / "feature_package"
LABEL_DIR = OUT_ROOT / "label_package"
SEAL_DIR = OUT_ROOT / "seal"
QUARANTINE_DIR = OUT_ROOT / "quarantine"
REJECTED_DIR = OUT_ROOT / "rejected"

CANONICAL_PACK_PATH = (
    REPO
    / "services"
    / "model-service"
    / "src"
    / "services"
    / "ncaam_schedule"
    / "data"
    / "ncaam_official_schedule_2024_25.json"
)
KENPOM_SNAPSHOT_DIR = WEB / "data" / "processed" / "kenpom_snapshots"
ODDS_PARQUET = WEB / "data" / "processed" / "ncaab_historical_odds_open_close.parquet"

ESPN_SCOREBOARD = (
    "https://site.web.api.espn.com/apis/site/v2/sports/basketball/"
    "mens-college-basketball/scoreboard"
)
HISTORICAL_STATIC_RECONSTRUCTION = "HISTORICAL_STATIC_RECONSTRUCTION"
VENUE_STATUS = ("confirmed_home", "confirmed_neutral", "unknown")

READINESS_STATUSES = (
    "SEALED_AND_READY",
    "BLOCKED_PIT_KENPOM",
    "BLOCKED_B1_ODDS",
    "BLOCKED_OUTCOMES",
    "BLOCKED_IDENTITY",
    "BLOCKED_VENUE_CONTRACT",
    "BLOCKED_MULTIPLE",
)
