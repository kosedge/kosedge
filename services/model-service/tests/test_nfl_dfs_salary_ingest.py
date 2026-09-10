from __future__ import annotations

from pathlib import Path

import pytest

from src.services.nfl_dfs_salary_ingest import (
    SalaryParseError,
    normalize_slate,
    parse_dk_csv,
    parse_fd_csv,
)

FIXTURES = Path(__file__).parent / "fixtures"
DK_CSV = (FIXTURES / "nfl_dfs_dk_week1_classic.csv").read_text()
FD_CSV = (FIXTURES / "nfl_dfs_fd_week1_classic.csv").read_text()


def test_parses_real_dk_week1_salaries() -> None:
    rows = parse_dk_csv(DK_CSV)
    by_name = {r.player_name: r for r in rows}
    assert by_name["Josh Allen"].salary == 7000
    assert by_name["Josh Allen"].team == "BUF"
    assert by_name["Josh Allen"].opponent == "HOU"
    assert by_name["Josh Allen"].site == "DK"
    assert by_name["Ja'Marr Chase"].salary == 7800
    assert by_name["Jahmyr Gibbs"].salary == 8000
    assert by_name["Bijan Robinson"].salary == 7700
    assert all(r.site == "DK" for r in rows)
    assert all(r.opponent for r in rows)


def test_fd_csv_stays_fd_and_not_dk_salaries() -> None:
    rows = parse_fd_csv(FD_CSV)
    by_name = {r.player_name: r for r in rows}
    assert by_name["Josh Allen"].site == "FD"
    assert by_name["Josh Allen"].salary == 8800
    assert by_name["Josh Allen"].salary != 7000
    assert by_name["Ja'Marr Chase"].salary == 9600
    assert all(r.site == "FD" for r in rows)


def test_cannot_ingest_dk_file_as_fd() -> None:
    with pytest.raises(SalaryParseError, match="cannot be ingested as FD"):
        normalize_slate(
            site="FD",
            season=2026,
            week=1,
            slate_id="fd-main",
            source="test",
            source_version="v1",
            csv_text=DK_CSV,
        )


def test_cannot_ingest_fd_file_as_dk() -> None:
    with pytest.raises(SalaryParseError, match="cannot be ingested as DK"):
        normalize_slate(
            site="DK",
            season=2026,
            week=1,
            slate_id="151307",
            source="test",
            source_version="v1",
            csv_text=FD_CSV,
        )


def test_normalize_stamps_site_from_source() -> None:
    slate = normalize_slate(
        site="DK",
        season=2026,
        week=1,
        slate_id="151307",
        source="dk_csv",
        source_version="dk-151307-20260910",
        csv_text=DK_CSV,
    )
    assert slate.site == "DK"
    assert slate.week == 1
    assert all(row.site == "DK" for row in slate.rows)
    assert slate.rejected == []
