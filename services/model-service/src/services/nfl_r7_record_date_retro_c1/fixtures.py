"""Visibly SYNTHETIC fixtures for RETRO_C1. Cannot pass a future real-data gate."""

from __future__ import annotations

from typing import Any

CHANNEL = "SYNTHETIC"
SOURCE = "SYNTHETIC_RETRO_C1_FIXTURE"

# Recorded dates only. Naive start_time_raw is audit text, never UTC.
SYNTHETIC_SCHEDULE: list[dict[str, Any]] = [
    {"game_id": "SYNTHETIC_2018_W01_LAC_MIA", "season": 2018, "week": 1, "season_type": "REG",
     "home": "LAC", "away": "MIA", "recorded_game_date": "2018-09-09", "start_time_raw": "9/9/18, 13:00:00"},
    {"game_id": "SYNTHETIC_2018_W01_LAR_BUF", "season": 2018, "week": 1, "season_type": "REG",
     "home": "LAR", "away": "BUF", "recorded_game_date": "2018-09-09", "start_time_raw": "9/9/18, 16:25:00"},
    {"game_id": "SYNTHETIC_2018_W02_KC_LAC", "season": 2018, "week": 2, "season_type": "REG",
     "home": "LAC", "away": "KC", "recorded_game_date": "2018-09-16", "start_time_raw": "9/16/18, 16:05:00"},
    {"game_id": "SYNTHETIC_2018_W02_LAR_NE", "season": 2018, "week": 2, "season_type": "REG",
     "home": "NE", "away": "LAR", "recorded_game_date": "2018-09-16", "start_time_raw": "9/16/18, 13:00:00"},
    {"game_id": "SYNTHETIC_2018_W03_LAC_LAR", "season": 2018, "week": 3, "season_type": "REG",
     "home": "LAR", "away": "LAC", "recorded_game_date": "2018-09-23", "start_time_raw": "9/23/18, 16:25:00"},
    {"game_id": "SYNTHETIC_2018_W04_LAC_SF", "season": 2018, "week": 4, "season_type": "REG",
     "home": "LAC", "away": "SF", "recorded_game_date": "2018-09-30", "start_time_raw": "9/30/18, 16:05:00"},
    {"game_id": "SYNTHETIC_2018_W04_LAR_MIN", "season": 2018, "week": 4, "season_type": "REG",
     "home": "LAR", "away": "MIN", "recorded_game_date": "2018-09-27", "start_time_raw": "9/27/18, 20:20:00"},
    {"game_id": "SYNTHETIC_2018_W05_BYE_MARKER_LAC", "season": 2018, "week": 5, "season_type": "REG",
     "home": "DEN", "away": "NYJ", "recorded_game_date": "2018-10-07", "start_time_raw": "10/7/18, 13:00:00"},
    {"game_id": "SYNTHETIC_2018_W06_LAC_LAR", "season": 2018, "week": 6, "season_type": "REG",
     "home": "LAC", "away": "LAR", "recorded_game_date": "2018-10-13", "start_time_raw": "10/13/18, 16:25:00"},
]

# Alias + postponement + date-tie controls (separate from the TNF path).
ALIAS_SCHEDULE: list[dict[str, Any]] = [
    {"game_id": "SYNTHETIC_2018_W01_SD_MIA", "season": 2018, "week": 1, "season_type": "REG",
     "home": "SD", "away": "MIA", "recorded_game_date": "2018-09-09"},
    {"game_id": "SYNTHETIC_2018_W02_STL_BUF", "season": 2018, "week": 2, "season_type": "REG",
     "home": "STL", "away": "BUF", "recorded_game_date": "2018-09-16"},
    {"game_id": "SYNTHETIC_2018_W06_LAC_LAR", "season": 2018, "week": 6, "season_type": "REG",
     "home": "LAC", "away": "LAR", "recorded_game_date": "2018-10-13"},
]

TIE_SCHEDULE: list[dict[str, Any]] = [
    {"game_id": "SYNTHETIC_2018_W01_LAC_MIA", "season": 2018, "week": 1, "season_type": "REG",
     "home": "LAC", "away": "MIA", "recorded_game_date": "2018-09-09"},
    {"game_id": "SYNTHETIC_2018_W01B_LAC_NYJ", "season": 2018, "week": 1, "season_type": "REG",
     "home": "NYJ", "away": "LAC", "recorded_game_date": "2018-09-09"},
    {"game_id": "SYNTHETIC_2018_W02_LAC_KC", "season": 2018, "week": 2, "season_type": "REG",
     "home": "LAC", "away": "KC", "recorded_game_date": "2018-09-16"},
]

POSTPONE_SCHEDULE: list[dict[str, Any]] = [
    {"game_id": "SYNTHETIC_2018_W01_LAC_MIA", "season": 2018, "week": 1, "season_type": "REG",
     "home": "LAC", "away": "MIA", "recorded_game_date": "2018-09-09"},
    {"game_id": "SYNTHETIC_2018_W01_DEN_SEA", "season": 2018, "week": 1, "season_type": "REG",
     "home": "DEN", "away": "SEA", "recorded_game_date": "2018-09-09"},
    {"game_id": "SYNTHETIC_2018_W02_LAC_KC", "season": 2018, "week": 2, "season_type": "REG",
     "home": "LAC", "away": "KC", "recorded_game_date": "2018-09-23"},
    {"game_id": "SYNTHETIC_2018_W03_LAC_DEN", "season": 2018, "week": 3, "season_type": "REG",
     "home": "DEN", "away": "LAC", "recorded_game_date": "2018-09-30"},
]

SYNTHETIC_TARGET = {
    "game_id": "SYNTHETIC_2018_W06_LAC_LAR",
    "season": 2018,
    "week": 6,
    "season_type": "REG",
    "home": "LAC",
    "away": "LAR",
    "recorded_game_date": "2018-10-13",
    "nominal_kickoff_utc": "2018-10-14T00:25:00Z",
    "channel": CHANNEL,
    "real_mode_usable": False,
    "y_margin": 3.0,
    "y_source": "SYNTHETIC_LABEL_NOT_REAL_OUTCOME",
}

SYNTHETIC_HISTORY: list[dict[str, Any]] = [
    {"game_id": "SYNTHETIC_2017_W14_BUF_NE", "season": 2017, "week": 14, "home_team": "NE", "away_team": "BUF",
     "kickoff_utc": "2017-12-10T18:00:00Z", "home_score": 28, "away_score": 10, "channel": CHANNEL},
    {"game_id": "SYNTHETIC_2018_W01_LAC_MIA", "season": 2018, "week": 1, "home_team": "LAC", "away_team": "MIA",
     "kickoff_utc": "2018-09-09T17:00:00Z", "home_score": 27, "away_score": 20, "channel": CHANNEL},
    {"game_id": "SYNTHETIC_2018_W02_KC_LAC", "season": 2018, "week": 2, "home_team": "LAC", "away_team": "KC",
     "kickoff_utc": "2018-09-16T20:05:00Z", "home_score": 31, "away_score": 28, "channel": CHANNEL},
    {"game_id": "SYNTHETIC_2018_W04_LAC_SF", "season": 2018, "week": 4, "home_team": "LAC", "away_team": "SF",
     "kickoff_utc": "2018-09-30T20:05:00Z", "home_score": 29, "away_score": 27, "channel": CHANNEL},
    {"game_id": "SYNTHETIC_2018_W04_LAR_MIN", "season": 2018, "week": 4, "home_team": "LAR", "away_team": "MIN",
     "kickoff_utc": "2018-09-28T00:20:00Z", "home_score": 38, "away_score": 31, "channel": CHANNEL},
    {"game_id": "SYNTHETIC_2018_W06_SAMEWEEK_LAC_DEN", "season": 2018, "week": 6, "home_team": "DEN", "away_team": "LAC",
     "kickoff_utc": "2018-10-14T17:00:00Z", "home_score": 17, "away_score": 20, "channel": CHANNEL},
    {"game_id": "SYNTHETIC_2018_W06_LAC_LAR", "season": 2018, "week": 6, "home_team": "LAC", "away_team": "LAR",
     "kickoff_utc": "2018-10-14T00:25:00Z", "home_score": 23, "away_score": 20, "channel": CHANNEL},
]


def synthetic_target() -> dict[str, Any]:
    return dict(SYNTHETIC_TARGET)


def synthetic_schedule() -> list[dict[str, Any]]:
    return [dict(row) for row in SYNTHETIC_SCHEDULE]


def synthetic_history() -> list[dict[str, Any]]:
    return [dict(row) for row in SYNTHETIC_HISTORY]
