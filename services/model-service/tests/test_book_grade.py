"""Grader fixtures — ATS, skip in-progress, late_post CLV note, immutability."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.services.book_ledger.grade import (
    close_and_grade_row,
    close_line_for_side,
    grade_spread_result,
    is_final_status,
    is_in_progress,
)
from src.services.book_ledger.schema import BookRow
from src.services.book_ledger.store import BookStore


def test_grade_spread_home_away_push() -> None:
    # Home -7, home wins 27-17 → margin 10 → cover +3 → win
    assert grade_spread_result(side="home", line=-7.0, home_score=27, away_score=17) == "win"
    # Home -7, home wins 24-17 → margin 7 → push
    assert grade_spread_result(side="home", line=-7.0, home_score=24, away_score=17) == "push"
    # Away +7, away loses 17-27 → margin home 10 → away cover = -10+7 = -3 → loss
    assert grade_spread_result(side="away", line=7.0, home_score=27, away_score=17) == "loss"
    # Away +38.5, away loses 0-35 → cover = -35+38.5 = +3.5 → win
    assert grade_spread_result(side="away", line=38.5, home_score=35, away_score=0) == "win"


def test_status_gates() -> None:
    assert is_in_progress(state="in", name="STATUS_IN_PROGRESS")
    assert not is_final_status(state="in", name="STATUS_IN_PROGRESS", completed=False)
    assert is_final_status(state="post", name="STATUS_FINAL", completed=True)
    assert not is_final_status(state="pre", name="STATUS_SCHEDULED", completed=False)


def test_close_line_for_side() -> None:
    assert close_line_for_side(side="home", spread_home=-38.5) == -38.5
    assert close_line_for_side(side="away", spread_home=-38.5) == 38.5


def test_skip_in_progress_and_settle_final(tmp_path: Path) -> None:
    store = BookStore(root=tmp_path)
    play = store.snapshot(
        BookRow(
            book_id="",
            sport="cfb",
            season=2026,
            week_or_slate="2026-08-29",
            game_id="g_play",
            home="USC",
            away="SJSU",
            type="play",
            market="spread",
            side="away",
            line=38.5,
            posted_at="2026-08-29T16:00:00Z",
            stake_flag="paper",
            late_post=False,
            post_timing="pre_kick",
        )
    )["row"]
    late = store.snapshot(
        BookRow(
            book_id="",
            sport="cfb",
            season=2026,
            week_or_slate="2026-08-29",
            game_id="g_late",
            home="TCU",
            away="UNC",
            type="pass",
            market="spread",
            side="home",
            line=-7.5,
            posted_at="2026-08-29T16:20:00Z",
            stake_flag="paper",
            late_post=True,
            post_timing="after_open",
        )
    )["row"]

    skip = close_and_grade_row(
        store,
        play,
        {
            "state": "in",
            "status_name": "STATUS_IN_PROGRESS",
            "completed": False,
            "home_score": 14,
            "away_score": 7,
            "spread_home": -38.5,
        },
        dry_run=False,
    )
    assert skip["action"] == "skip"
    assert skip["reason"] == "in_progress"
    assert store.get(play["book_id"])["result"] == "pending"

    settled = close_and_grade_row(
        store,
        play,
        {
            "state": "post",
            "status_name": "STATUS_FINAL",
            "completed": True,
            "home_score": 35,
            "away_score": 3,
            "spread_home": -37.0,
            "market_source": "espn_fixture",
        },
    )
    assert settled["action"] == "settle"
    assert settled["result"] == "win"  # away +38.5, lost by 32
    assert settled["clv_note"] == "pre_kick_post"
    row = store.get(play["book_id"])
    assert row["result"] == "win"
    assert row["units"] == 1.0
    assert row["clv"] == pytest.approx(1.5)  # away post 38.5 → close 37; away CLV = close_home - open_home via side convert
    # away post_line 38.5 → open_home -38.5; close_line 37 → close_home -37
    # away CLV = close_home - open_home = -37 - (-38.5) = 1.5

    late_settle = close_and_grade_row(
        store,
        late,
        {
            "state": "post",
            "status_name": "STATUS_FINAL",
            "completed": True,
            "home_score": 28,
            "away_score": 21,
            "spread_home": -7.0,
            "market_source": "espn_fixture",
        },
    )
    assert late_settle["clv_note"] == "after_open_late_post"
    # margin 7, line -7.5 → cover = 7 + (-7.5) = -0.5 → loss
    assert late_settle["result"] == "loss"
    late_row = store.get(late["book_id"])
    assert late_row["info_overlap"] == "late_post_clv"
    assert late_row["payload"]["clv_note"] == "after_open_late_post"

    with pytest.raises(ValueError, match="immutable"):
        store.settle(late["book_id"], result="win")
