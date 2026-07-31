from src.services.nba_data import (
    compute_rest_days_by_team,
    derive_possessions_from_pbp,
    estimate_player_usage_stub,
    estimate_team_features_from_box,
    features_from_data_nba_team_stats,
    features_from_gamelog_row,
    normalize_team_key,
    pair_season_games_from_gamelog,
    rolling_average_features,
    season_label_to_start_year,
)


def test_normalize_team_key() -> None:
    assert normalize_team_key("Boston Celtics") == "BOS"
    assert normalize_team_key("LAL") == "LAL"
    assert season_label_to_start_year("2023-24") == 2023


def test_features_from_data_nba_team_stats() -> None:
    feat = features_from_data_nba_team_stats(
        {
            "s": 104,
            "tstsg": {
                "fga": 81,
                "fgm": 40,
                "tpa": 25,
                "tpm": 11,
                "fta": 16,
                "ftm": 13,
                "oreb": 4,
                "dreb": 40,
                "tov": 14,
            },
        }
    )
    assert feat["ortg"] > 0
    assert 0 < feat["three_pt_rate"] < 1


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


def test_pair_season_games_and_rest() -> None:
    rows = [
        {
            "GAME_ID": "0022300001",
            "GAME_DATE": "2023-10-24",
            "TEAM_ABBREVIATION": "BOS",
            "MATCHUP": "BOS vs. NYK",
            "FGA": 90,
            "FTA": 20,
            "TOV": 12,
            "OREB": 10,
            "DREB": 35,
            "FG3A": 40,
            "FG3M": 15,
            "FGM": 42,
            "FTM": 16,
            "PTS": 112,
        },
        {
            "GAME_ID": "0022300001",
            "GAME_DATE": "2023-10-24",
            "TEAM_ABBREVIATION": "NYK",
            "MATCHUP": "NYK @ BOS",
            "FGA": 88,
            "FTA": 22,
            "TOV": 14,
            "OREB": 9,
            "DREB": 33,
            "FG3A": 36,
            "FG3M": 12,
            "FGM": 40,
            "FTM": 18,
            "PTS": 108,
        },
        {
            "GAME_ID": "0022300010",
            "GAME_DATE": "2023-10-26",
            "TEAM_ABBREVIATION": "BOS",
            "MATCHUP": "BOS @ MIA",
            "FGA": 85,
            "FTA": 18,
            "TOV": 11,
            "OREB": 8,
            "DREB": 34,
            "FG3A": 38,
            "FG3M": 14,
            "FGM": 40,
            "FTM": 14,
            "PTS": 110,
        },
        {
            "GAME_ID": "0022300010",
            "GAME_DATE": "2023-10-26",
            "TEAM_ABBREVIATION": "MIA",
            "MATCHUP": "MIA vs. BOS",
            "FGA": 86,
            "FTA": 19,
            "TOV": 13,
            "OREB": 9,
            "DREB": 32,
            "FG3A": 35,
            "FG3M": 11,
            "FGM": 39,
            "FTM": 15,
            "PTS": 104,
        },
    ]
    games = pair_season_games_from_gamelog(rows, season="2023-24")
    assert len(games) == 2
    assert games[0]["home_team_key"] == "BOS"
    assert games[0]["away_team_key"] == "NYK"
    assert "ortg" in games[0]["home_features"]
    rest = compute_rest_days_by_team(games)
    assert rest[("0022300010", "BOS")] == 2.0
    avg = rolling_average_features([features_from_gamelog_row(rows[0])])
    assert avg["ortg"] > 0
    stub = estimate_player_usage_stub(
        {
            "PLAYER_ID": 1,
            "PLAYER_NAME": "Test",
            "TEAM_ABBREVIATION": "BOS",
            "MIN": "34:12",
            "FGA": 18,
            "FTA": 4,
            "TOV": 2,
            "PTS": 24,
            "REB": 5,
            "AST": 6,
        }
    )
    assert stub["minutes"] > 34
    assert stub["usage_proxy"] > 0


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
