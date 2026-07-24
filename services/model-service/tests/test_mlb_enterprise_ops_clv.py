from src.services.mlb_enterprise_ops import densify_snapshot_datetimes, resolve_densify_books
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
