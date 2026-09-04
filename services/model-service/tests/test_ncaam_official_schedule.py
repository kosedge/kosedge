"""Unit tests — NCAAM ESPN official schedule reader + fail-closed B7 map."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
WEB_SRC = REPO / "apps" / "web" / "src"
if str(WEB_SRC) not in sys.path:
    sys.path.insert(0, str(WEB_SRC))

from src.services.ncaam_schedule.official_schedule import (  # noqa: E402
    coverage_report,
    documentation,
    games_from_blob,
    load_official_schedule_blob,
    schedule_path_for_season,
)
from ncaam_espn_schedule_map import (  # noqa: E402
    map_espn_event_sides,
    resolve_espn_team_id,
)
from ncaam_identity import resolve_team_id  # noqa: E402


FIXTURE = {
    "season": "2022-23",
    "season_end_year": 2023,
    "official": True,
    "source": "espn_scoreboard_public",
    "slate_complete": False,
    "games": [
        {
            "game_id": "401493739",
            "espn_game_id": "401493739",
            "tipoff": "2022-12-03T18:00Z",
            "date": "2022-12-03",
            "home": "miami oh",
            "away": "indiana state",
            "home_name": "Miami (OH) RedHawks",
            "away_name": "Indiana State Sycamores",
            "home_espn_id": "193",
            "away_espn_id": "282",
            "neutral_site": False,
            "venue": "Millett Hall",
            "status": "final",
            "home_score": 71,
            "away_score": 68,
            "odds_event_id": None,
            "map_status": "b7_both",
        },
        {
            "game_id": "401479680",
            "espn_game_id": "401479680",
            "tipoff": "2022-12-01T00:00Z",
            "date": "2022-12-01",
            "home": "miami fl",
            "away": "rutgers",
            "home_name": "Miami Hurricanes",
            "away_name": "Rutgers Scarlet Knights",
            "home_espn_id": "2390",
            "away_espn_id": "164",
            "neutral_site": False,
            "venue": "Watsco Center",
            "status": "final",
            "odds_event_id": None,
            "map_status": "b7_both",
        },
        # Fail-closed omit: missing home team_id
        {
            "game_id": "should-skip",
            "espn_game_id": "should-skip",
            "home": "",
            "away": "duke",
            "tipoff": "2022-12-01T00:00Z",
        },
    ],
}


def test_schedule_path_for_season() -> None:
    path = schedule_path_for_season("2022-23")
    assert path.name == "ncaam_official_schedule_2022_23.json"


def test_games_from_blob_fail_closed_and_stable_ids() -> None:
    games = games_from_blob(FIXTURE, season_key="2022-23")
    assert len(games) == 2
    ids = {g["game_id"] for g in games}
    assert ids == {"401493739", "401479680"}
    by_id = {g["game_id"]: g for g in games}
    assert by_id["401493739"]["home"] == "miami oh"
    assert by_id["401479680"]["home"] == "miami fl"
    assert by_id["401493739"]["home"] != by_id["401479680"]["home"]
    assert by_id["401493739"]["odds_event_id"] is None


def test_coverage_report_never_auto_complete() -> None:
    games = games_from_blob(FIXTURE, season_key="2022-23")
    cov = coverage_report(games)
    assert cov["slate_complete"] is False
    assert cov["miami_fl_games"] == 1
    assert cov["miami_oh_games"] == 1
    assert cov["miami_fl_ne_miami_oh"] is True


def test_load_packaged_2022_23_if_present() -> None:
    path = schedule_path_for_season("2022-23")
    if not path.is_file():
        pytest.skip("packaged 2022-23 schedule not present")
    blob = load_official_schedule_blob("2022-23")
    assert blob["present"] is True
    assert blob["slate_complete"] is False
    assert blob.get("official") is True
    games = games_from_blob(blob)
    assert len(games) >= 100
    # Miami FL ≠ Miami OH on packaged receipts
    homes = {g["home"] for g in games} | {g["away"] for g in games}
    assert "miami fl" in homes
    assert "miami oh" in homes
    assert "miami" not in homes
    # No invented Odds crosswalk
    assert all(g.get("odds_event_id") in (None, "") for g in games)
    doc = documentation(blob)
    assert doc["slate_complete"] is False
    assert doc["densified"] is False


def test_espn_map_miami_fl_oh_fail_closed() -> None:
    fl_team = {
        "id": "2390",
        "location": "Miami",
        "name": "Hurricanes",
        "displayName": "Miami Hurricanes",
        "shortDisplayName": "Miami",
        "abbreviation": "MIA",
    }
    oh_team = {
        "id": "193",
        "location": "Miami (OH)",
        "name": "RedHawks",
        "displayName": "Miami (OH) RedHawks",
        "shortDisplayName": "Miami OH",
        "abbreviation": "M-OH",
    }
    fl_id, fl_alias = resolve_espn_team_id(fl_team)
    oh_id, oh_alias = resolve_espn_team_id(oh_team)
    assert fl_id == "miami fl"
    assert oh_id == "miami oh"
    assert fl_id != oh_id
    assert fl_alias == "Miami Hurricanes"
    assert oh_alias == "Miami (OH) RedHawks"

    # Bare location "Miami" alone must omit (ambiguous FL vs OH)
    bare_id, _ = resolve_espn_team_id(
        {"location": "Miami", "displayName": "", "shortDisplayName": "", "name": ""}
    )
    assert bare_id is None
    assert resolve_team_id("miami") is None

    mapped = map_espn_event_sides(fl_team, oh_team)
    assert mapped["ok"] is True
    assert mapped["home"] == "miami fl"
    assert mapped["away"] == "miami oh"

    # Unknown side → omit entire event
    unknown = {
        "displayName": "ZZZ Fake U Explorers",
        "location": "ZZZ Fake U",
        "name": "Explorers",
    }
    bad = map_espn_event_sides(fl_team, unknown)
    assert bad["ok"] is False
    assert bad["away"] is None
