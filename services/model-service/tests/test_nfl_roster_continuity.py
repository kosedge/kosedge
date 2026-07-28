from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.nfl_roster_continuity import (
    aggregate_roster_continuity_nowcast,
    fetch_roster_continuity_adjustments,
    fetch_roster_continuity_nowcast,
)


def test_roster_continuity_empty_is_neutral() -> None:
    empty = aggregate_roster_continuity_nowcast([])
    assert empty["adjustment_count"] == 0
    assert empty["offense_multiplier"] == 1.0
    assert empty["defense_multiplier"] == 1.0
    assert empty["impact_score"] == 0.0
    assert empty["confidence"] == 0.0
    assert empty["top_drivers"] == []


def test_roster_continuity_departure_of_star_defender_weakens_defense_only() -> None:
    """A lost elite EDGE/DL (negative impact_score, defense-weighted
    position group) should push defense_multiplier above 1.0 (weaker
    defense, matching the simulator's "higher defense_index = weaker
    defense" convention) while leaving offense_multiplier untouched,
    since the position carries zero offensive weight."""
    rows = [
        {
            "impact_score": -0.6,
            "position_group": "EDGE",
            "reason": "trade",
            "source": "manual",
            "player_name": "Star Defender",
            "notes": "test",
        }
    ]
    summary = aggregate_roster_continuity_nowcast(rows)
    assert summary["adjustment_count"] == 1
    assert summary["offense_multiplier"] == 1.0
    assert summary["defense_multiplier"] > 1.0
    assert summary["impact_score"] > 0.0
    assert summary["confidence"] > 0.0
    assert summary["top_drivers"][0]["player_name"] == "Star Defender"

    # Magnitude should be "meaningful but not extreme": clearly bigger
    # than a single fresh, high-confidence in-season "starter out" report
    # (~1.026x, see nfl_injury_nowcast calibration), but well inside the
    # simulator's own consumption-time ceiling of 1.18x.
    assert 1.03 < summary["defense_multiplier"] < 1.10


def test_roster_continuity_signing_strengthens_offense() -> None:
    """A positive impact_score on an offensive position group (e.g. a
    notable free-agent signing) should push offense_multiplier above 1.0
    and leave defense_multiplier untouched."""
    rows = [
        {
            "impact_score": 0.5,
            "position_group": "WR",
            "reason": "signing",
            "source": "manual",
            "player_name": "New WR1",
        }
    ]
    summary = aggregate_roster_continuity_nowcast(rows)
    assert summary["offense_multiplier"] > 1.0
    assert summary["defense_multiplier"] == 1.0


def test_roster_continuity_impact_score_is_clamped_and_signed_correctly() -> None:
    worse = aggregate_roster_continuity_nowcast(
        [{"impact_score": -1.0, "position_group": "QB", "reason": "injury", "source": "manual"}]
    )
    better = aggregate_roster_continuity_nowcast(
        [{"impact_score": 1.0, "position_group": "QB", "reason": "signing", "source": "manual"}]
    )
    assert worse["offense_multiplier"] < 1.0
    assert better["offense_multiplier"] > 1.0
    # Out-of-range inputs should be clamped rather than raise.
    out_of_range = aggregate_roster_continuity_nowcast(
        [{"impact_score": -5.0, "position_group": "DL", "reason": "departure", "source": "manual"}]
    )
    assert out_of_range["defense_multiplier"] <= 1.18


def test_roster_continuity_source_confidence_ordering() -> None:
    manual = aggregate_roster_continuity_nowcast(
        [{"impact_score": -0.5, "position_group": "DL", "reason": "departure", "source": "manual"}]
    )
    nflverse = aggregate_roster_continuity_nowcast(
        [{"impact_score": -0.5, "position_group": "DL", "reason": "departure", "source": "nflverse"}]
    )
    assert nflverse["confidence"] > manual["confidence"]


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _Row:
    def __init__(self, mapping):
        self._mapping = mapping


class _Session:
    def __init__(self, rows):
        self.rows = rows
        self.queries = []

    def execute(self, sql, params=None):
        self.queries.append((str(sql), params))
        assert "nfl_roster_continuity_adjustments" in str(sql)
        assert params["team"] == "CLE"
        return _Result([_Row(r) for r in self.rows])


def test_fetch_roster_continuity_adjustments_filters_by_season_and_team() -> None:
    session = _Session(
        rows=[
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
    rows = fetch_roster_continuity_adjustments(session, season_year=2026, team="CLE")
    assert len(rows) == 1
    assert rows[0]["player_name"] == "Myles Garrett"

    nowcast = fetch_roster_continuity_nowcast(session, season_year=2026, team="CLE")
    assert nowcast["adjustment_count"] == 1
    assert nowcast["defense_multiplier"] > 1.0


def test_fetch_roster_continuity_adjustments_empty_team_short_circuits() -> None:
    session = _Session(rows=[])
    assert fetch_roster_continuity_adjustments(session, season_year=2026, team="") == []
