from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.nfl_injury_nowcast import (
    _aggregate_team_nowcast,
    _merge_roster_continuity_into_nowcast,
    fetch_nfl_injury_nowcast,
)


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


def test_merge_roster_continuity_is_noop_with_no_adjustments() -> None:
    nowcast = _aggregate_team_nowcast([])
    continuity = {"adjustment_count": 0, "offense_multiplier": 1.0, "defense_multiplier": 1.0, "confidence": 0.0, "impact_score": 0.0, "top_drivers": []}
    merged = _merge_roster_continuity_into_nowcast(nowcast, continuity)
    assert merged is nowcast


def test_merge_roster_continuity_compounds_with_live_injury_nowcast() -> None:
    now = datetime.now(timezone.utc)
    live_rows = [
        {
            "player_name": "CB One",
            "position": "CB",
            "report_status": "questionable",
            "practice_status": "limited",
            "injury": "hamstring",
            "updated_at": now,
        }
    ]
    live_nowcast = _aggregate_team_nowcast(live_rows)
    continuity = {
        "adjustment_count": 1,
        "offense_multiplier": 1.0,
        "defense_multiplier": 1.0446,
        "confidence": 0.8,
        "impact_score": 0.0279,
        "top_drivers": [{"kind": "roster_continuity", "player_name": "Star Defender", "impact_score": -0.6}],
    }
    merged = _merge_roster_continuity_into_nowcast(live_nowcast, continuity)
    # Compounding two independent defense-weakening signals should push
    # defense_multiplier higher than either signal alone (but still within
    # the simulator's consumption-time ceiling of 1.18).
    assert merged["defense_multiplier"] > live_nowcast["defense_multiplier"]
    assert merged["defense_multiplier"] > continuity["defense_multiplier"]
    assert merged["defense_multiplier"] <= 1.18
    assert merged["roster_continuity_adjustment_count"] == 1
    assert any(d.get("kind") == "roster_continuity" for d in merged["top_drivers"])


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _Row:
    def __init__(self, mapping):
        self._mapping = mapping


class _InjuryNowcastSession:
    """Fake session routing by SQL substring, mirroring the pattern used
    in test_nfl_tasks.py -- returns empty live-injury rows (as in the
    2026 preseason, before any weekly injury report exists) and one
    roster-continuity adjustment row for the home team only."""

    def __init__(self, continuity_rows):
        self.continuity_rows = continuity_rows

    def execute(self, sql, params=None):
        query = str(sql)
        if "nfl_dp_injuries" in query:
            return _Result([])
        if "nfl_roster_continuity_adjustments" in query:
            rows = self.continuity_rows if params.get("team") == "CLE" else []
            return _Result([_Row(r) for r in rows])
        raise AssertionError(f"Unexpected SQL: {query}")


def test_fetch_nfl_injury_nowcast_blends_in_roster_continuity_for_preseason() -> None:
    session = _InjuryNowcastSession(
        continuity_rows=[
            {
                "season": 2026,
                "team": "CLE",
                "player_name": "Myles Garrett",
                "position_group": "EDGE",
                "impact_score": -0.6,
                "reason": "trade",
                "source": "manual",
                "notes": "placeholder",
                "created_at": None,
            }
        ]
    )
    nowcast = fetch_nfl_injury_nowcast(session, season_year=2026, home_team="CLE", away_team="CIN")
    assert nowcast["source"] == "nfl_dp_injuries+roster_continuity"
    assert nowcast["home"]["defense_multiplier"] > 1.0
    assert nowcast["home"]["roster_continuity_adjustment_count"] == 1
    assert nowcast["away"]["defense_multiplier"] == 1.0
    assert nowcast["away"].get("roster_continuity_adjustment_count") is None


def test_fetch_nfl_injury_nowcast_source_unchanged_without_roster_continuity() -> None:
    session = _InjuryNowcastSession(continuity_rows=[])
    nowcast = fetch_nfl_injury_nowcast(session, season_year=2026, home_team="CLE", away_team="CIN")
    assert nowcast["source"] == "nfl_dp_injuries"
    assert nowcast["home"]["defense_multiplier"] == 1.0
