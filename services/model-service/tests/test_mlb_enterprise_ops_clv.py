from src.services.mlb_enterprise_ops import densify_snapshot_datetimes, rank_thin_densify_dates, resolve_densify_books
from datetime import date


def test_resolve_densify_books_dk_first() -> None:
    assert resolve_densify_books("fanduel,betmgm").startswith("draftkings")


def test_densify_snapshot_datetimes_offset() -> None:
    dts = densify_snapshot_datetimes(
        [date(2025, 5, 1)],
        day_offset=-1,
        snapshot_hour_utc=18,
        snapshot_minute_utc=30,
    )
    assert len(dts) == 1
    assert dts[0].day == 30
    assert dts[0].hour == 18
    assert dts[0].minute == 30


def test_rank_thin_densify_dates_prioritizes_highest_thin_score() -> None:
    ranked = rank_thin_densify_dates(
        [
            (date(2026, 5, 1), 2),
            (date(2026, 6, 30), 15),
            (date(2026, 5, 19), 15),
            (date(2026, 7, 1), 0),
        ],
        max_dates=2,
    )
    assert ranked == [date(2026, 5, 19), date(2026, 6, 30)]
