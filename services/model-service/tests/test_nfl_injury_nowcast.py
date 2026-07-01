from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.services.nfl_injury_nowcast import _aggregate_team_nowcast


def test_injury_nowcast_directional_effects() -> None:
    now = datetime.now(timezone.utc)
    rows = [
        {
            "player_name": "QB One",
            "position": "QB",
            "report_status": "out",
            "practice_status": "did not participate",
            "injury": "concussion",
            "updated_at": now,
        },
        {
            "player_name": "CB One",
            "position": "CB",
            "report_status": "questionable",
            "practice_status": "limited",
            "injury": "hamstring",
            "updated_at": now,
        },
    ]
    summary = _aggregate_team_nowcast(rows)
    assert summary["injury_count"] == 2
    assert summary["offense_multiplier"] < 1.0
    assert summary["defense_multiplier"] > 1.0
    assert summary["confidence"] > 0.0


def test_injury_nowcast_stale_and_no_data_fallback() -> None:
    stale = datetime.now(timezone.utc) - timedelta(hours=240)
    stale_summary = _aggregate_team_nowcast(
        [
            {
                "player_name": "WR Two",
                "position": "WR",
                "report_status": "out",
                "practice_status": "did not participate",
                "injury": "knee",
                "updated_at": stale,
            }
        ]
    )
    assert stale_summary["freshness_multiplier"] <= 0.2
    assert stale_summary["offense_multiplier"] >= 0.95

    empty = _aggregate_team_nowcast([])
    assert empty["injury_count"] == 0
    assert empty["offense_multiplier"] == 1.0
    assert empty["defense_multiplier"] == 1.0
