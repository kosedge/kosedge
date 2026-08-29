"""Desk OS item B — KEI publish hard-block on overdue open T1s."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.services.nfl_camp_sot_queue import (
    CLOSED_DISPOSITIONS,
    DepthSotWorkItem,
    KeiPublishBlocked,
    assert_kei_publish_allowed,
    overdue_t1_blocking_kei_publish,
    t1_past_kei_publish,
)


def _flag(
    *,
    wid: str,
    team: str = "CLE",
    tier: str = "T1",
    status: str = "open",
    overdue: bool = False,
    next_kei: str = "2026-08-28T20:00:00Z",
) -> DepthSotWorkItem:
    return DepthSotWorkItem(
        work_item_id=wid,
        desk_date="2026-08-28",
        team=team,
        title=f"{team} test",
        sot_flag="test flag",
        bottom_line="test",
        tier=tier,  # type: ignore[arg-type]
        status=status,
        overdue=overdue,
        overdue_reason="past_kei_publish" if overdue else "",
        next_kei_publish=next_kei,
        sources=[{"source": "camp_desk"}],
    )


def test_overdue_open_t1_blocks_kei_publish() -> None:
    now = datetime(2026, 8, 29, 18, 0, tzinfo=timezone.utc)
    open_overdue = _flag(wid="wi-open", overdue=True)
    blockers = overdue_t1_blocking_kei_publish([open_overdue], now=now)
    assert [f.work_item_id for f in blockers] == ["wi-open"]
    with pytest.raises(KeiPublishBlocked) as exc:
        assert_kei_publish_allowed([open_overdue], now=now)
    assert "wi-open" in str(exc.value)


def test_accept_no_change_reject_do_not_block() -> None:
    now = datetime(2026, 8, 29, 18, 0, tzinfo=timezone.utc)
    flags = [
        _flag(wid="wi-acc", status="accepted", overdue=True),
        _flag(wid="wi-nc", status="no_change", overdue=True),
        _flag(wid="wi-rej", status="reject", overdue=True),
    ]
    assert CLOSED_DISPOSITIONS == frozenset({"accepted", "reject", "no_change"})
    assert overdue_t1_blocking_kei_publish(flags, now=now) == []
    assert_kei_publish_allowed(flags, now=now)  # does not raise


def test_past_kei_deadline_open_t1_blocks() -> None:
    now = datetime(2026, 8, 29, 18, 0, tzinfo=timezone.utc)
    flag = _flag(wid="wi-past", overdue=False, next_kei="2026-08-28T20:00:00Z")
    assert t1_past_kei_publish([flag], now=now)
    assert overdue_t1_blocking_kei_publish([flag], now=now)
    with pytest.raises(KeiPublishBlocked):
        assert_kei_publish_allowed([flag], now=now)


def test_future_kei_and_not_overdue_allows() -> None:
    now = datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc)
    flag = _flag(wid="wi-ok", overdue=False, next_kei="2026-08-28T20:00:00Z")
    assert overdue_t1_blocking_kei_publish([flag], now=now) == []
    assert_kei_publish_allowed([flag], now=now)
