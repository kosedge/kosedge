"""
Minimal pipeline test: run build_ratings with fixture data and assert output schema.
"""
import os
import subprocess
import sys
from pathlib import Path

import polars as pl
import pytest

# Apps/web root
WEB_ROOT = Path(__file__).resolve().parent.parent
SRC = WEB_ROOT / "src"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_build_ratings_produces_valid_schema(tmp_path: Path) -> None:
    """Run build_ratings with minimal KenPom fixture; assert full_ratings has required columns."""
    raw_ratings = tmp_path / "raw" / "ratings"
    processed = tmp_path / "processed"
    raw_ratings.mkdir(parents=True)
    processed.mkdir(parents=True)

    # Copy minimal KenPom CSV (must have teamname, season, adjem, sos)
    kenpom = FIXTURES / "kenpom_mini.csv"
    assert kenpom.exists(), "fixtures/kenpom_mini.csv missing"
    (raw_ratings / "kenpom_ratings_2016-2026.csv").write_text(kenpom.read_text())

    env = os.environ.copy()
    env["DATA_DIR"] = str(tmp_path)

    cmd = [sys.executable, str(SRC / "build_ratings.py")]
    result = subprocess.run(cmd, cwd=WEB_ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, (result.stdout + result.stderr)

    out_path = processed / "full_ratings.parquet"
    assert out_path.exists(), "full_ratings.parquet not created"
    df = pl.read_parquet(out_path)
    assert len(df) >= 2

    sys.path.insert(0, str(WEB_ROOT))
    from src.schema import FULL_RATINGS_COLUMNS, validate_columns
    missing = validate_columns(df, FULL_RATINGS_COLUMNS, "full_ratings")
    assert not missing, f"full_ratings missing columns: {missing}"
