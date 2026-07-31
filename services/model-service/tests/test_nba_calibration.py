from datetime import date

from src.services.nba_calibration import (
    NbaWalkforwardRow,
    build_enterprise_report_stub,
    summarize_walkforward,
)


def test_summarize_walkforward_empty() -> None:
    summary = summarize_walkforward([])
    assert summary["n_games"] == 0
    assert summary["status"] == "awaiting_outcomes"
    assert summary["model_spread_mae"] is None


def test_summarize_walkforward_basic() -> None:
    rows = [
        NbaWalkforwardRow(
            game_id="1",
            game_date=date(2026, 1, 10),
            model_spread_home=-4.0,
            model_total=220.0,
            close_spread_home=-3.5,
            close_total=222.0,
            actual_margin=6.0,
            actual_total=218.0,
        ),
        NbaWalkforwardRow(
            game_id="2",
            game_date=date(2026, 1, 11),
            model_spread_home=2.5,
            model_total=230.0,
            close_spread_home=3.0,
            close_total=228.5,
            actual_margin=-5.0,
            actual_total=235.0,
        ),
    ]
    summary = summarize_walkforward(rows)
    assert summary["n_games"] == 2
    assert summary["n_spread_graded"] == 2
    assert summary["n_total_graded"] == 2
    assert summary["model_spread_mae"] is not None
    assert summary["model_total_mae"] is not None
    assert summary["status"] == "ready"
    assert 0.0 <= float(summary["model_ats_cover_rate"]) <= 1.0


def test_enterprise_report_stub() -> None:
    report = build_enterprise_report_stub(
        worker_build_id="nba-poss-sim-20260731-phase0",
        model_version="nba-v1-poss-sim",
        phase="phase0",
    )
    assert report["sport"] == "nba"
    assert report["publish_policy"]["props"] == "queued_until_mainlines_honest"
    assert report["data_policy"]["odds_api_historical_repull"] is False
