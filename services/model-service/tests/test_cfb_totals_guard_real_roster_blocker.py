"""Same-path / reconstructability locks for CFB real-roster totals-guard.

No SDV fetch. No pack / KEI writes. No fake eval numbers.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.services.cfb_season_engine.totals_guard_holdout import (
    FIT_SEASONS,
    UNUSED_EVAL_SEASONS,
    assert_no_eval_leakage_in_fit,
    filter_fit_rows,
)
from src.services.cfb_season_engine.totals_guard_real_roster import (
    PROXY_ROSTER_PATH,
    REAL_ROSTER_PATH,
    REQUIRED_ROSTER_SEASONS,
    REQUIRED_SP_PLUS_CARRIES,
    assert_no_eval_year_in_fit,
    assert_same_roster_path,
    blocker_payload,
    inventory,
    packaged_roster_seasons,
    packaged_sp_plus_carries,
    real_roster_path_reconstructable,
)

DATA = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "services"
    / "cfb_season_engine"
    / "data"
)


def test_fit_eval_year_split_unchanged() -> None:
    assert FIT_SEASONS == frozenset({2023, 2024})
    assert UNUSED_EVAL_SEASONS == frozenset({2025})
    rows = [
        {"season": 2023, "week": 1},
        {"season": 2024, "week": 2},
        {"season": 2025, "week": 1},
    ]
    fit = filter_fit_rows(rows, week_max=2)
    assert_no_eval_leakage_in_fit(fit)
    assert_no_eval_year_in_fit(r["season"] for r in fit)
    with pytest.raises(AssertionError):
        assert_no_eval_year_in_fit([2023, 2025])


def test_same_path_required_and_proxy_mix_forbidden() -> None:
    assert_same_roster_path(REAL_ROSTER_PATH, REAL_ROSTER_PATH)
    assert_same_roster_path(PROXY_ROSTER_PATH, PROXY_ROSTER_PATH)
    with pytest.raises(AssertionError, match="same-path"):
        assert_same_roster_path(PROXY_ROSTER_PATH, REAL_ROSTER_PATH)
    with pytest.raises(AssertionError, match="proxy-fit"):
        assert_same_roster_path(
            REAL_ROSTER_PATH, REAL_ROSTER_PATH, proxy_lambda=0.542555
        )


def test_inventory_only_2026_roster_and_2025_carry_today() -> None:
    seasons = packaged_roster_seasons(data_dir=DATA)
    carries = packaged_sp_plus_carries(data_dir=DATA)
    assert 2026 in seasons
    assert seasons.isdisjoint({2023, 2024, 2025})
    assert (2025, 2026) in carries
    assert not (REQUIRED_SP_PLUS_CARRIES & carries)
    inv = inventory(data_dir=DATA)
    assert inv["missing_roster_seasons"] == [2023, 2024, 2025]
    assert len(inv["missing_sp_plus_carries"]) == 3


def test_reconstructability_stop_today() -> None:
    gate = real_roster_path_reconstructable(data_dir=DATA)
    assert gate["reconstructable"] is False
    assert gate["stop"] is True
    assert "STOP" in gate["message"]
    payload = blocker_payload(data_dir=DATA)
    assert payload["verdict"] == "STOP"
    assert payload["product"]["apply_cfb_kei"] is False
    assert payload["product"]["totals_guard_flag"] == "OFF"
    assert payload["eval_table"] is None
    assert payload["coefficients"] is None


def test_ops_blocker_summary_json_committed() -> None:
    path = (
        Path(__file__).resolve().parents[3]
        / "data"
        / "ops"
        / "cfb-totals-guard-real-roster-holdout-blocker-20260903"
        / "summary.json"
    )
    assert path.is_file()
    blob = json.loads(path.read_text(encoding="utf-8"))
    assert blob["verdict"] == "STOP"
    assert blob["eval_table"] is None
    assert blob["product"]["apply_cfb_kei"] is False
    assert 2023 in blob["missing"]["real_roster_snapshot_years"]
    assert 2024 in blob["missing"]["real_roster_snapshot_years"]


def test_required_sets_cover_fit_and_eval() -> None:
    # Fit 2023–24 + eval 2025 all need roster packs; each needs prior-year SP+.
    assert REQUIRED_ROSTER_SEASONS == frozenset({2023, 2024, 2025})
    assert REQUIRED_SP_PLUS_CARRIES == frozenset(
        {(2022, 2023), (2023, 2024), (2024, 2025)}
    )
