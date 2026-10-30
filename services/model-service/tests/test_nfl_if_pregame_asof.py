"""t4822u — Independent Fair pregame as-of join vs pin 1b39f4e9.

No rematerialize, no scoring, no snap admit. Proves the matchup join
consumes rating_week = target_week - 1 and cannot ingest the target
or a future game. Pin same-week join is preserved as a cited contrast.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.services.nfl_pregame_asof import (
    IF_MATCHUP_ROLLING_JOIN_AWAY,
    IF_MATCHUP_ROLLING_JOIN_HOME,
    PINNED_IF_INGEST_SHA,
    PINNED_IF_MATCHUP_JOIN_AWAY,
    PINNED_IF_MATCHUP_JOIN_HOME,
    PregameAsofReject,
    contiguous_pregame_rating_week,
    reject_if_not_pregame_game,
    resolve_if_matchup_rolling_row,
    resolve_pregame_rating_week,
)
from src.services.nfl_snap_share_exposure_ledger import resolve_if_5g_window
from src.services.nfl_snap_share_exposure_ledger.schema import (
    REJECT_FUTURE_GAME_IN_WINDOW,
    REJECT_RATING_WEEK_NOT_LAGGED,
    REJECT_RATING_WEEK_STALE,
    REJECT_RATING_WEEK_UNRESOLVED,
    REJECT_TARGET_WEEK_INVALID,
    ExposureLedgerReject,
    ScheduleGameRow,
    SituationalWeekRow,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
MODEL_INGEST = (
    REPO_ROOT
    / "services/model-service/data_platform_nfl/ingest.py"
)
STANDALONE_INGEST = (
    REPO_ROOT
    / "services/data-platform-nfl/src/data_platform_nfl/ingest.py"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_rating_week_is_completed_data_week_not_forecast_target():
    assert contiguous_pregame_rating_week(9) == 8
    assert resolve_pregame_rating_week(target_week=9) == 8
    assert PINNED_IF_INGEST_SHA == "1b39f4e9"


def test_if_matchup_join_uses_target_minus_1_not_same_week():
    rolling_weeks = (2, 3, 4, 6, 8)
    assert resolve_if_matchup_rolling_row(
        target_week=9, team="SYN", rolling_weeks=rolling_weeks
    ) == 8
    with pytest.raises(PregameAsofReject) as exc:
        resolve_if_matchup_rolling_row(
            target_week=8, team="SYN", rolling_weeks=rolling_weeks
        )
    assert exc.value.code == REJECT_RATING_WEEK_UNRESOLVED


def test_pin_same_week_join_is_not_the_corrected_predicate():
    assert PINNED_IF_MATCHUP_JOIN_HOME != IF_MATCHUP_ROLLING_JOIN_HOME
    assert PINNED_IF_MATCHUP_JOIN_AWAY != IF_MATCHUP_ROLLING_JOIN_AWAY
    assert "h.week = s.week" in PINNED_IF_MATCHUP_JOIN_HOME
    assert "h.week = (s.week - 1)" in IF_MATCHUP_ROLLING_JOIN_HOME


@pytest.mark.parametrize("ingest_path", [MODEL_INGEST, STANDALONE_INGEST])
def test_ingest_sql_uses_lagged_join_and_not_pin_same_week(ingest_path: Path):
    text = _read(ingest_path)
    assert IF_MATCHUP_ROLLING_JOIN_HOME in text
    assert IF_MATCHUP_ROLLING_JOIN_AWAY in text
    assert PINNED_IF_MATCHUP_JOIN_HOME not in text
    assert PINNED_IF_MATCHUP_JOIN_AWAY not in text
    assert "h.week = (s.week - 1)" in text
    assert "a.week = (s.week - 1)" in text
    # No silent latest-week substitute.
    assert "MAX(h.week)" not in text
    assert "MAX(a.week)" not in text


def test_target_and_future_games_cannot_enter_if_baseline_join():
    rolling_weeks = (2, 3, 4, 6, 8, 9, 10)
    chosen = resolve_if_matchup_rolling_row(
        target_week=9, team="SYN", rolling_weeks=rolling_weeks
    )
    assert chosen == 8
    assert chosen != 9
    assert chosen < 9
    with pytest.raises(PregameAsofReject) as exc:
        reject_if_not_pregame_game(
            game_week=9, target_week=9, game_id="SYN-2099-09", target_game_id="SYN-2099-09"
        )
    assert exc.value.code == REJECT_FUTURE_GAME_IN_WINDOW
    with pytest.raises(PregameAsofReject) as exc:
        reject_if_not_pregame_game(game_week=10, target_week=9, game_id="SYN-2099-10")
    assert exc.value.code == REJECT_FUTURE_GAME_IN_WINDOW


def test_week1_target_fail_closed():
    with pytest.raises(PregameAsofReject) as exc:
        contiguous_pregame_rating_week(1)
    assert exc.value.code == REJECT_TARGET_WEEK_INVALID


def test_stale_and_same_week_rating_rejected():
    with pytest.raises(PregameAsofReject) as exc:
        resolve_pregame_rating_week(target_week=9, rating_week=9)
    assert exc.value.code == REJECT_RATING_WEEK_NOT_LAGGED
    with pytest.raises(PregameAsofReject) as exc:
        resolve_pregame_rating_week(target_week=9, rating_week=7)
    assert exc.value.code == REJECT_RATING_WEEK_STALE


def test_reconstructed_if_window_excludes_target_game_stats():
    sit = [
        SituationalWeekRow(season=2099, week=w, team="SYN", games_played=1)
        for w in (2, 3, 4, 6, 8, 9)
    ]
    sched = [
        ScheduleGameRow(
            season=2099,
            week=w,
            game_id=f"SYN-2099-{w:02d}",
            home_team="SYN",
            away_team="OPP",
            completed=True,
        )
        for w in (2, 3, 4, 6, 8, 9, 10)
    ]
    window = resolve_if_5g_window(
        season=2099,
        target_week=9,
        team="SYN",
        situational_rows=sit,
        schedule_rows=sched,
    )
    assert window.rating_week == 8
    assert window.target_week == 9
    assert window.game_ids == (
        "SYN-2099-02",
        "SYN-2099-03",
        "SYN-2099-04",
        "SYN-2099-06",
        "SYN-2099-08",
    )
    assert "SYN-2099-09" not in window.game_ids
    assert "SYN-2099-10" not in window.game_ids
