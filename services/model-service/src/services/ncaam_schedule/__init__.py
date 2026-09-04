"""NCAAM official schedule package (ESPN scoreboard SoT — Option A)."""

from src.services.ncaam_schedule.official_schedule import (
    coverage_report,
    documentation,
    games_from_blob,
    load_official_schedule_blob,
    schedule_path_for_season,
)

__all__ = [
    "coverage_report",
    "documentation",
    "games_from_blob",
    "load_official_schedule_blob",
    "schedule_path_for_season",
]
