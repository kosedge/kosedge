"""2026 live open diagnostic — report only. No KEI. No used_in_spread."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_warehouse.live_open_diagnostic import (
    USED_IN_SPREAD,
    diagnose_opens,
    documentation,
    model_more_favorite,
    open_abs_bucket,
    slice_opens,
    week_label,
)


def test_contract_research_only() -> None:
    assert USED_IN_SPREAD is False
    docs = documentation()
    assert docs["kei"] is False
    assert docs["blend"] is False
    assert docs["not_a_release_gate"] is True


def test_more_favorite_and_buckets() -> None:
    # Open home -7; model -14 → more favorite.
    assert model_more_favorite(-14.0, -7.0) is True
    # Model -3 vs open -7 → less favorite (hist short-favorite).
    assert model_more_favorite(-3.0, -7.0) is False
    # Away favorite open +7; model +14 → more favorite.
    assert model_more_favorite(14.0, 7.0) is True
    assert model_more_favorite(None, -7.0) is None
    assert model_more_favorite(-3.0, 0.0) is None
    assert open_abs_bucket(-2.0) == "pickem_lt3"
    assert open_abs_bucket(-10.0) == "large_7_14"
    assert open_abs_bucket(-21.0) == "blowout_14plus"
    assert week_label(0) == "w0"
    assert week_label(1) == "w1"
    assert week_label(2) == "w2_plus"


def test_thin_slice_hides_metrics() -> None:
    rows = [
        {
            "model_spread_home": -3.0,
            "open_spread_home": -7.0,
            "week": 0,
            "home_team_id": "BALL",
            "away_team_id": "OSU",
        }
    ]
    thin = slice_opens(rows)
    assert thin["thin"] is True
    assert thin["n"] == 1
    assert "vs_open" not in thin
    full = slice_opens(rows, hide_thin=False)
    assert full["vs_open"]["n"] == 1
    assert full["used_in_spread"] is False


def test_diagnose_empty_and_cold() -> None:
    empty = diagnose_opens([], n_opens=55, n_closes=0)
    assert empty["status"] == "insufficient_market_rows"
    assert empty["n_matched"] == 0
    assert empty["bias"] == "insufficient"
    assert empty["gate"]["ready_for_kei_design_brief"] is False
    assert empty["used_in_spread"] is False

    rows = [
        {
            "model_spread_home": -3.0,
            "open_spread_home": -10.0,
            "model_total": 48.0,
            "open_total": 52.0,
            "week": 1,
            "home_team_id": "UGA",
            "away_team_id": "CLEM",
        }
        for _ in range(30)
    ]
    out = diagnose_opens(rows, n_opens=55, n_closes=0)
    assert out["n_matched"] == 30
    assert out["match_rate"] == round(30 / 55, 4)
    assert out["bias"] == "cold"
    assert out["overall"]["vs_open"]["mean"] > 1.5
    assert out["overall"]["short_favorite"]["rate"] == 1.0
    assert out["overall"]["model_more_favorite"]["rate"] == 0.0
    assert out["gate"]["ready_for_kei_design_brief"] is False
    assert out["gate"]["recommendation"] == "hold_through_week_3"
    assert out["kei"] is False
    assert out["not_a_release_gate"] is True
    assert out["by_week"]["w1"]["thin"] is False
    assert "vs_open" in out["by_week"]["w1"]
