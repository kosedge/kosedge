from src.services.nba_data import (
    derive_possessions_from_pbp,
    estimate_team_features_from_box,
    normalize_team_key,
)


def test_normalize_team_key() -> None:
    assert normalize_team_key("Boston Celtics") == "BOS"
    assert normalize_team_key("LAL") == "LAL"


def test_estimate_team_features_from_box() -> None:
    feats = estimate_team_features_from_box(
        [
            {
                "TEAM_ABBREVIATION": "BOS",
                "FGA": 90,
                "FTA": 20,
                "TOV": 12,
                "OREB": 10,
                "DREB": 35,
                "FG3A": 40,
                "FG3M": 15,
                "FGM": 42,
                "PTS": 112,
            },
            {
                "TEAM_ABBREVIATION": "NYK",
                "FGA": 88,
                "FTA": 22,
                "TOV": 14,
                "OREB": 9,
                "DREB": 33,
                "FG3A": 36,
                "FG3M": 12,
                "FGM": 40,
                "PTS": 108,
            },
        ]
    )
    assert "BOS" in feats and "NYK" in feats
    assert feats["BOS"]["ortg"] > 0
    assert feats["BOS"]["drtg"] == feats["NYK"]["ortg"]


def test_derive_possessions_from_pbp() -> None:
    rows = [
        {"PERIOD": 1, "EVENTMSGTYPE": 1, "HOMEDESCRIPTION": "3PT Jump Shot", "VISITORDESCRIPTION": None},
        {"PERIOD": 1, "EVENTMSGTYPE": 2, "HOMEDESCRIPTION": None, "VISITORDESCRIPTION": "Layup"},
        {"PERIOD": 1, "EVENTMSGTYPE": 4, "HOMEDESCRIPTION": "Defensive Rebound", "VISITORDESCRIPTION": None},
        {"PERIOD": 1, "EVENTMSGTYPE": 5, "HOMEDESCRIPTION": "Turnover", "VISITORDESCRIPTION": None},
    ]
    poss = derive_possessions_from_pbp(rows, home_team_key="BOS", away_team_key="NYK")
    assert len(poss) >= 2
    assert any(p["ended_by"] == "shot_make" for p in poss)
    assert all("events" in p for p in poss)
