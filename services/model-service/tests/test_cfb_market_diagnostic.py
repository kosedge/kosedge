"""Market diagnostic is report-only — no KEI, no used_in_spread, no blend."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_season_engine import engine_status_payload
from src.services.cfb_warehouse.market_diagnostic import (
    DIAGNOSTIC_ID,
    USED_IN_SPREAD,
    annotate_row,
    close_abs_bucket,
    clv_side_hit,
    diagnose,
    diagnostic_week_band,
    documentation,
    slice_report,
)


def test_contract_no_kei_no_spread() -> None:
    assert USED_IN_SPREAD is False
    assert documentation()["kei"] is False
    assert documentation()["blend"] is False
    assert documentation()["used_in_spread"] is False
    assert DIAGNOSTIC_ID.startswith("cfb-market-diagnostic")


def test_week_and_line_buckets() -> None:
    assert diagnostic_week_band(0) == "w0_1"
    assert diagnostic_week_band(1) == "w0_1"
    assert diagnostic_week_band(4) == "w2_4"
    assert diagnostic_week_band(5) == "w5_9"
    assert diagnostic_week_band(9) == "w5_9"
    assert diagnostic_week_band(10) == "w10_plus"
    assert close_abs_bucket(1.5) == "pickem_lt3"
    assert close_abs_bucket(-6.5) == "mid_3_7"
    assert close_abs_bucket(10.0) == "large_7_14"
    assert close_abs_bucket(-21.0) == "blowout_14plus"
    assert close_abs_bucket(None) is None


def test_clv_side_hit_and_no_move() -> None:
    # Open -3, model -7 (more home), close -6 → market moved toward model.
    assert clv_side_hit(-7.0, -3.0, -6.0) is True
    # Model the other way.
    assert clv_side_hit(2.0, -3.0, -6.0) is False
    # No move.
    assert clv_side_hit(-7.0, -3.0, -3.0) is None
    assert clv_side_hit(-7.0, -3.0, -3.1) is None


def test_slice_report_flags_thin_and_stays_research() -> None:
    rows = [
        {
            "model_fair_present": True,
            "model_spread_home": -3.0,
            "open_spread_home": -6.0,
            "close_spread_home": -7.0,
            "spread_error": 4.0,
            "ats_hit": False,
            "favorite_home": True,
            "week": 1,
            "home_team_id": "BALL",
            "away_team_id": "OSU",
            "fair_status": "ok",
        }
    ]
    out = slice_report(rows)
    assert out["used_in_spread"] is False
    assert out["kei"] is False
    assert out["sample_flag"] == "thin"
    assert out["vs_close"]["n"] == 1
    assert out["vs_open"]["n"] == 1
    assert "kei_edge" not in out
    assert out["sigma_slice"] == "skipped_not_on_hist_rows"


def test_diagnose_has_required_slices() -> None:
    row = annotate_row(
        {
            "model_fair_present": True,
            "model_spread_home": -4.0,
            "open_spread_home": -10.0,
            "close_spread_home": -14.5,
            "spread_error": 10.5,
            "ats_hit": False,
            "favorite_home": True,
            "week": 0,
            "home_team_id": "UGA",
            "away_team_id": "CLEM",
            "fair_status": "ok",
        }
    )
    assert row["used_in_spread"] is False
    assert row["kei"] is False
    assert row["diag_week_band"] == "w0_1"
    assert row["close_abs_bucket"] == "blowout_14plus"
    pack = diagnose([row])
    assert pack["used_in_spread"] is False
    assert pack["kei"] is False
    assert "by_diag_week_band" in pack
    assert "by_close_abs_bucket" in pack
    assert "by_favorite_home" in pack
    assert "by_conference_tier" in pack


def test_status_exposes_read_only_diagnostic() -> None:
    status = engine_status_payload(season=2026, demo=True)
    assert status["used_in_spread"] is False
    block = status.get("market_diagnostic") or {}
    assert block.get("used_in_spread") is False
    assert block.get("kei") is False
    assert block.get("blend") is False
