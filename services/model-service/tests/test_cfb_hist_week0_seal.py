"""2025 residual seal + no 2026 recruiting leak on hist Week-0 path."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.services.cfb_season_engine.hist_week0 import (
    FIELD_AUDIT,
    assert_2025_sealed,
    reconstruction_inventory,
)


def test_2025_sealed_without_freeze(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="2025 is sealed"):
        assert_2025_sealed(open_2025=True, freeze_path=tmp_path / "missing.json")


def test_2025_sealed_ok_when_not_requested() -> None:
    assert_2025_sealed(open_2025=False, freeze_path=None)


def test_inventory_is_not_live_path() -> None:
    inv = reconstruction_inventory()
    assert inv["same_as_2026_live_path"] is False
    assert inv["stop_same_path"] is True
    assert FIELD_AUDIT["connelly_sp_plus_prior_year"]["status"] == "missing_2022_2023_2024"
    assert FIELD_AUDIT["recruiting_capital"]["status"] == "unminted"
    assert "2026" in FIELD_AUDIT["recruiting_capital"]["notes"]


def test_site_roster_season_param_is_forbidden() -> None:
    row = FIELD_AUDIT["espn_site_roster_season_param"]
    assert row["status"] == "not_year_locked"
