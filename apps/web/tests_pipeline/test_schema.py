"""Test schema validation helpers."""
import sys
from pathlib import Path

import polars as pl

WEB = Path(__file__).resolve().parent.parent
if str(WEB) not in sys.path:
    sys.path.insert(0, str(WEB))
from src.schema import FULL_RATINGS_COLUMNS, validate_columns, assert_schema


def test_validate_columns_ok() -> None:
    df = pl.DataFrame({
        "season": [2024],
        "team_norm": ["villanova"],
        "adjem": [25.0],
        "sos": [10.0],
    })
    assert validate_columns(df, FULL_RATINGS_COLUMNS) == []


def test_validate_columns_missing() -> None:
    df = pl.DataFrame({"season": [2024], "team_norm": ["villanova"]})
    missing = validate_columns(df, FULL_RATINGS_COLUMNS)
    assert "adjem" in missing
    assert "sos" in missing


def test_assert_schema_raises() -> None:
    df = pl.DataFrame({"season": [2024]})
    try:
        assert_schema(df, FULL_RATINGS_COLUMNS, "test")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "missing required columns" in str(e)
