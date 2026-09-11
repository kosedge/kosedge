from __future__ import annotations

from pathlib import Path

from src.services.nfl_dfs_store import SALARY_OBS_IDENTITY_KEYS


def test_salary_current_identity_includes_season_and_week() -> None:
    assert "season" in SALARY_OBS_IDENTITY_KEYS
    assert "week" in SALARY_OBS_IDENTITY_KEYS
    assert SALARY_OBS_IDENTITY_KEYS == (
        "site",
        "season",
        "week",
        "slate_id",
        "source_player_id",
        "source_version",
    )


def test_persist_sql_scopes_current_flag_and_upsert_to_week() -> None:
    src = Path(__file__).resolve().parents[1] / "src/services/nfl_dfs_store.py"
    text = src.read_text()
    assert "AND season = :season" in text
    assert "AND week = :week" in text
    assert "ON CONFLICT (site, season, week, slate_id, source_player_id, source_version)" in text
    assert "ON CONFLICT (site, slate_id, source_player_id, source_version)" not in text