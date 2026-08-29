"""The Book ledger — units, idempotency, immutability, CLV fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.services.book_ledger.clv import compute_clv
from src.services.book_ledger.ids import make_book_id, units_for_type
from src.services.book_ledger.metrics import unit_roi
from src.services.book_ledger.schema import BookRow
from src.services.book_ledger.store import BookStore


def test_units_play_lean_pass() -> None:
    assert units_for_type("play") == 1.0
    assert units_for_type("lean") == 0.0
    assert units_for_type("pass") == 0.0


def test_book_id_idempotent() -> None:
    a = make_book_id(
        sport="cfb",
        game_id="401856766",
        market="spread",
        side="home",
        posted_at="2026-08-29T16:20:00Z",
        type="pass",
    )
    b = make_book_id(
        sport="cfb",
        game_id="401856766",
        market="spread",
        side="home",
        posted_at="2026-08-29T16:20:00Z",
        type="pass",
    )
    c = make_book_id(
        sport="cfb",
        game_id="401856766",
        market="spread",
        side="away",
        posted_at="2026-08-29T16:20:00Z",
        type="pass",
    )
    assert a == b
    assert a != c
    assert a.startswith("book_")


def test_clv_spread_fixture() -> None:
    # Posted home -7, close home -9 → home CLV = open - close = +2 (beat close)
    assert compute_clv(
        market="spread",
        side="home",
        post_line=-7.0,
        post_price=-110,
        close_line=-9.0,
        close_price=-110,
    ) == 2.0
    # Away +7 post, close away +9 (home -7 → -9): away got worse number → CLV -2
    assert compute_clv(
        market="spread",
        side="away",
        post_line=7.0,
        post_price=-110,
        close_line=9.0,
        close_price=-110,
    ) == -2.0
    # Away +7 post, close away +5 (home -7 → -5): away beat close → CLV +2
    assert compute_clv(
        market="spread",
        side="away",
        post_line=7.0,
        post_price=-110,
        close_line=5.0,
        close_price=-110,
    ) == 2.0


def test_clv_total_fixture() -> None:
    assert compute_clv(
        market="total",
        side="over",
        post_line=45.5,
        post_price=-110,
        close_line=47.5,
        close_price=-110,
    ) == 2.0
    assert compute_clv(
        market="total",
        side="under",
        post_line=45.5,
        post_price=-110,
        close_line=47.5,
        close_price=-110,
    ) == -2.0


def test_snapshot_idempotent_and_units(tmp_path: Path) -> None:
    store = BookStore(root=tmp_path)
    row = BookRow(
        book_id="",
        sport="cfb",
        season=2026,
        week_or_slate="2026-08-29",
        game_id="g1",
        home="TCU",
        away="UNC",
        type="lean",
        market="spread",
        side="home",
        line=-7.5,
        price=-110,
        posted_at="2026-08-29T12:00:00Z",
        kei_at_post={"kei_spread_home": -20.4, "edge_pts": 3.0},
        market_at_post={"spread_home": -7.5},
        market_source="test",
        stake_flag="paper",
        actor="test",
    )
    r1 = store.snapshot(row)
    assert r1["created"] is True
    assert r1["row"]["units"] == 0.0
    assert r1["row"]["type"] == "lean"
    r2 = store.snapshot(row)
    assert r2["created"] is False
    assert r2["row"]["book_id"] == r1["row"]["book_id"]
    assert len(store.list_rows()) == 1

    play = BookRow(
        book_id="",
        sport="cfb",
        season=2026,
        week_or_slate="2026-08-29",
        game_id="g2",
        home="USC",
        away="SJSU",
        type="play",
        market="spread",
        side="away",
        line=38.5,
        posted_at="2026-08-29T12:00:00Z",
        kei_at_post={"edge_pts": -4.2},
        market_at_post={"spread_home": -38.5},
        stake_flag="booked",
        actor="test",
    )
    pr = store.snapshot(play)
    assert pr["row"]["units"] == 1.0


def test_settled_row_immutable(tmp_path: Path) -> None:
    store = BookStore(root=tmp_path)
    row = BookRow(
        book_id="",
        sport="nfl",
        season=2026,
        week_or_slate="1",
        game_id="g9",
        home="KC",
        away="BAL",
        type="play",
        market="spread",
        side="home",
        line=-3.0,
        posted_at="2026-09-10T16:00:00Z",
        stake_flag="booked",
    )
    book_id = store.snapshot(row)["row"]["book_id"]
    store.record_close(book_id, close_line=-4.0, close_at="2026-09-10T20:00:00Z")
    store.settle(book_id, result="win")
    with pytest.raises(ValueError, match="immutable"):
        store.record_close(book_id, close_line=-5.0)
    with pytest.raises(ValueError, match="immutable"):
        store.settle(book_id, result="loss")


def test_unit_roi_excludes_leans_and_paper_by_default(tmp_path: Path) -> None:
    store = BookStore(root=tmp_path)
    for spec in (
        ("play", "booked", "win", 1.0),
        ("play", "paper", "win", 1.0),
        ("lean", "booked", "win", 0.0),
    ):
        t, stake, result, _u = spec
        r = store.snapshot(
            BookRow(
                book_id="",
                sport="cfb",
                season=2026,
                week_or_slate="2026-08-29",
                game_id=f"{t}-{stake}",
                home="H",
                away="A",
                type=t,
                market="spread",
                side="home",
                line=-3,
                posted_at="2026-08-29T12:00:00Z",
                stake_flag=stake,
            )
        )
        store.settle(r["row"]["book_id"], result=result)
    rows = store.list_rows()
    booked = unit_roi(rows, include_paper=False)
    assert booked["n_plays"] == 1
    assert booked["units"] == 1.0
    assert booked["pnl_units"] == 1.0
    both = unit_roi(rows, include_paper=True)
    assert both["n_plays"] == 2
