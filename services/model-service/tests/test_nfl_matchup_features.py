import os
from typing import Any, Optional

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.nfl_matchup_features import (
    MATCHUP_5G_NULL,
    MATCHUP_GAME_ID_UNRESOLVED,
    MATCHUP_PACK_BY_GAME_ID_SQL,
    MatchupFeatureReject,
    fetch_latest_matchup_feature_pack,
    matchup_pack_to_sim_input_kwargs,
)


class _FakeResult:
    def __init__(self, row: Optional[Any]) -> None:
        self._row = row

    def fetchone(self) -> Optional[Any]:
        return self._row


class _FakeRow:
    def __init__(self, payload: dict) -> None:
        self._mapping = payload


class _FakeSession:
    def __init__(self, row: Optional[Any]) -> None:
        self.row = row
        self.last_sql = ""

    def execute(self, statement: Any, params: dict) -> _FakeResult:
        self.last_sql = str(getattr(statement, "text", statement))
        self.last_params = params
        return _FakeResult(self.row)


def test_matchup_pack_to_sim_input_kwargs_maps_expected_fields() -> None:
    matchup_pack = {
        "season": 2025,
        "week": 9,
        "game_id": "2025_09_NE_BUF",
        "home_team": "BUF",
        "away_team": "NE",
        "home_off_epa_5g": 0.13,
        "away_off_epa_5g": -0.01,
        "home_pass_rate_5g": 0.62,
        "away_pass_rate_5g": 0.55,
        "home_success_offense_5g": 0.47,
        "away_success_offense_5g": 0.40,
        "home_success_defense_allowed_5g": 0.41,
        "away_success_defense_allowed_5g": 0.45,
        "diff_off_epa_5g": 0.14,
        "diff_def_epa_allowed_5g": 0.08,
        "diff_pressure_generated_5g": 0.03,
        "diff_pressure_allowed_5g": 0.02,
        "diff_red_zone_td_rate_5g": 0.06,
    }

    mapped = matchup_pack_to_sim_input_kwargs(matchup_pack)
    assert mapped["matchup_season"] == 2025
    assert mapped["matchup_week"] == 9
    assert mapped["feature_pack_version"] == "nfl-v1.1-matchup-pack-kav"
    assert mapped["matchup_diff_off_epa_5g"] == 0.14
    assert mapped["matchup_diff_pressure_generated_5g"] == 0.03
    assert mapped["matchup_diff_success_rate_5g"] == pytest.approx(0.055)


def test_matchup_pack_to_sim_input_kwargs_handles_missing_values() -> None:
    mapped = matchup_pack_to_sim_input_kwargs(
        {
            "season": 2025,
            "week": 9,
            "game_id": "g1",
            "home_team": "A",
            "away_team": "B",
            "diff_off_epa_5g": None,
        }
    )
    assert mapped["matchup_diff_off_epa_5g"] is None
    assert mapped["matchup_diff_success_rate_5g"] is None


def _valid_5g_pack(**overrides) -> dict:
    payload = {
        "season": 2099,
        "week": 9,
        "game_id": "G-W9",
        "home_team": "SYN",
        "away_team": "OPP",
        "home_off_epa_5g": 0.10,
        "away_off_epa_5g": -0.02,
        "home_def_epa_allowed_5g": 0.11,
        "away_def_epa_allowed_5g": 0.12,
        "home_pass_rate_5g": 0.55,
        "away_pass_rate_5g": 0.56,
    }
    payload.update(overrides)
    return payload


def test_matchup_pack_sql_has_no_latest_week_fallback() -> None:
    sql = MATCHUP_PACK_BY_GAME_ID_SQL
    assert "UNION ALL" not in sql
    assert "priority" not in sql
    assert "ORDER BY" not in sql
    assert "week DESC" not in sql
    assert "WHERE game_id = :game_id" in sql
    assert "home_team = :home_team" not in sql


def test_fetch_matchup_pack_rejects_missing_game_id() -> None:
    session = _FakeSession(None)
    with pytest.raises(MatchupFeatureReject) as exc:
        fetch_latest_matchup_feature_pack(
            session, game_id="G-MISSING", season_year=2099, home_team="SYN", away_team="OPP"
        )
    assert exc.value.code == MATCHUP_GAME_ID_UNRESOLVED
    assert "no latest-week fallback" in exc.value.message


def test_fetch_matchup_pack_rejects_null_5g() -> None:
    session = _FakeSession(_FakeRow(_valid_5g_pack(home_off_epa_5g=None)))
    with pytest.raises(MatchupFeatureReject) as exc:
        fetch_latest_matchup_feature_pack(
            session, game_id="G-W9", season_year=2099, home_team="SYN", away_team="OPP"
        )
    assert exc.value.code == MATCHUP_5G_NULL
    assert "home_off_epa_5g" in exc.value.message


def test_fetch_matchup_pack_returns_game_id_row() -> None:
    session = _FakeSession(_FakeRow(_valid_5g_pack()))
    pack = fetch_latest_matchup_feature_pack(
        session, game_id="G-W9", season_year=2099, home_team="SYN", away_team="OPP"
    )
    assert pack["game_id"] == "G-W9"
    assert pack["home_off_epa_5g"] == 0.10
    assert session.last_params == {"game_id": "G-W9"}
