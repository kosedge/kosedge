from datetime import date

from src.services import mlb_data


class _DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_extract_probable_pitchers_from_live_feed() -> None:
    payload = {
        "gameData": {
            "probablePitchers": {
                "home": {"fullName": "Yoshinobu Yamamoto"},
                "away": {"fullName": "Joe Musgrove"},
            }
        }
    }
    out = mlb_data.extract_probable_pitchers_from_live_feed(payload)
    assert out["home"] == "Yoshinobu Yamamoto"
    assert out["away"] == "Joe Musgrove"


def test_fetch_game_lineup_features_includes_probable_pitchers(monkeypatch) -> None:
    mlb_data.fetch_game_lineup_features.cache_clear()
    payload = {
        "gameData": {
            "probablePitchers": {
                "home": {"fullName": "Gerrit Cole"},
                "away": {"fullName": "Freddy Peralta"},
            }
        },
        "liveData": {
            "boxscore": {
                "teams": {
                    "home": {"players": {}},
                    "away": {"players": {}},
                }
            }
        },
    }
    monkeypatch.setattr(
        mlb_data.requests,
        "get",
        lambda *args, **kwargs: _DummyResponse(payload),
    )
    out = mlb_data.fetch_game_lineup_features("777")
    assert out["home"]["probable_pitcher"] == "Gerrit Cole"
    assert out["away"]["probable_pitcher"] == "Freddy Peralta"


def test_fetch_mlb_schedule_parses_expected_fields(monkeypatch) -> None:
    payload = {
        "dates": [
            {
                "games": [
                    {
                        "gamePk": 123,
                        "gameDate": "2026-04-15T23:10:00Z",
                        "status": {"detailedState": "Scheduled"},
                        "teams": {
                            "home": {
                                "team": {"id": 119, "name": "Los Angeles Dodgers", "abbreviation": "LAD"},
                                "probablePitcher": {"fullName": "Yoshinobu Yamamoto"},
                            },
                            "away": {
                                "team": {"id": 135, "name": "San Diego Padres", "abbreviation": "SD"},
                                "probablePitcher": {"fullName": "Joe Musgrove"},
                            },
                        },
                        "officials": [
                            {
                                "officialType": "Home Plate",
                                "official": {"fullName": "Test Umpire"},
                            }
                        ],
                    }
                ]
            }
        ]
    }

    monkeypatch.setattr(
        mlb_data.requests,
        "get",
        lambda *args, **kwargs: _DummyResponse(payload),
    )
    out = mlb_data.fetch_mlb_schedule(date(2026, 4, 15), date(2026, 4, 15))
    assert len(out) == 1
    assert out[0]["external_game_id"] == "123"
    assert out[0]["home_abbr"] == "LAD"
    assert out[0]["away_abbr"] == "SD"
    assert out[0]["home_team_id"] == 119
    assert out[0]["away_team_id"] == 135
    assert out[0]["umpire_home_plate"] == "Test Umpire"


def test_fetch_forecast_for_game_maps_weather(monkeypatch) -> None:
    weather_payload = {
        "hourly": {
            "time": ["2026-04-15T23:00"],
            "temperature_2m": [20.0],
            "relative_humidity_2m": [60.0],
            "wind_speed_10m": [12.0],
            "wind_direction_10m": [210.0],
        }
    }

    monkeypatch.setattr(
        mlb_data.requests,
        "get",
        lambda *args, **kwargs: _DummyResponse(weather_payload),
    )
    out = mlb_data.fetch_forecast_for_game(
        team_abbr="LAD",
        game_time_iso="2026-04-15T23:10:00Z",
    )
    assert round(out["weather_temp_f"], 1) == 68.0
    assert round(out["weather_wind_mph"], 2) == round(12.0 * 0.621371, 2)
    assert out["weather_humidity_pct"] == 60.0


def test_park_and_lineup_helpers(monkeypatch) -> None:
    assert mlb_data.park_factor_for_team("COL") > 1.05
    assert mlb_data.park_factor_for_team("SF") < 1.0
    c = mlb_data.lineup_confidence(
        lineup_confirmed=True,
        probable_pitcher_home="A",
        probable_pitcher_away="B",
    )
    assert c["home"] >= 0.95
    assert c["away"] >= 0.95
    known = mlb_data.umpire_run_factor("Laz Diaz")
    unknown = mlb_data.umpire_run_factor("Unknown Umpire")
    assert 0.95 <= known <= 1.05
    assert 0.97 <= unknown <= 1.03
    mlb_data._live_starter_features.cache_clear()
    monkeypatch.setattr(
        mlb_data.requests,
        "get",
        lambda *args, **kwargs: _DummyResponse({"people": []}),
    )
    # Live miss → static prior for known ace names.
    starter_known = mlb_data.starter_identity_features("Gerrit Cole", season=2026)
    starter_unknown = mlb_data.starter_identity_features("Some Pitcher", season=2026)
    assert 0.85 <= starter_known["starter_quality"] <= 1.15
    assert starter_known["handedness"] in {"L", "R", "U"}
    assert starter_known["source"] == "static-prior"
    assert 0.85 <= starter_unknown["starter_quality"] <= 1.15
    assert starter_unknown["source"] == "heuristic-fallback"
    assert mlb_data.normalize_pitcher_name("Jacob deGrom Jr.") == "jacob degrom"


def test_starter_identity_features_uses_live_pitcher_stats(monkeypatch) -> None:
    mlb_data._live_starter_features.cache_clear()

    def fake_get(url, *args, **kwargs):
        if url.endswith("/people/search"):
            return _DummyResponse(
                {
                    "people": [
                        {
                            "id": 700001,
                            "fullName": "Tarik Skubal",
                            "active": True,
                            "primaryPosition": {"code": "1"},
                            "pitchHand": {"code": "L"},
                        }
                    ]
                }
            )
        if url.endswith("/people/700001/stats"):
            return _DummyResponse(
                {
                    "stats": [
                        {
                            "splits": [
                                {
                                    "stat": {
                                        "era": "2.78",
                                        "whip": "0.91",
                                        "strikeoutsPer9Inn": "11.4",
                                        "walksPer9Inn": "1.8",
                                        "groundOutsToAirouts": "1.23",
                                    }
                                }
                            ]
                        }
                    ]
                }
            )
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr(mlb_data.requests, "get", fake_get)
    starter = mlb_data.starter_identity_features("Tarik Skubal", season=2026)
    assert starter["source"] == "mlb-stats-api"
    assert starter["handedness"] == "L"
    assert starter["starter_quality"] < 1.0
    assert starter["k_factor"] > 1.05
    assert starter["bb_factor"] < 1.0


def test_fetch_team_bullpen_fatigue_aggregates_recent_relief_work(monkeypatch) -> None:
    schedule_payload = {
        "dates": [
            {"games": [{"status": {"codedGameState": "F"}, "gamePk": 1003}]},
            {"games": [{"status": {"codedGameState": "F"}, "gamePk": 1002}]},
            {"games": [{"status": {"codedGameState": "F"}, "gamePk": 1001}]},
        ]
    }
    box_payload = {
        "teams": {
            "home": {
                "team": {"id": 119},
                "players": {
                    "ID1": {"stats": {"pitching": {"gamesStarted": "1", "inningsPitched": "5.0"}}},
                    "ID2": {"stats": {"pitching": {"gamesStarted": "0", "inningsPitched": "2.0"}}},
                    "ID3": {"stats": {"pitching": {"gamesStarted": "0", "inningsPitched": "1.0"}}},
                },
            },
            "away": {"team": {"id": 120}, "players": {}},
        }
    }

    def fake_get(url, *args, **kwargs):
        if url.endswith("/schedule"):
            return _DummyResponse(schedule_payload)
        if "/boxscore" in url:
            return _DummyResponse(box_payload)
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr(mlb_data.requests, "get", fake_get)
    out = mlb_data.fetch_team_bullpen_fatigue(119, date(2026, 4, 15))
    assert out["bullpen_ip_last3"] == 9.0
    assert out["bullpen_appearances_last3"] == 6.0
    assert 0.45 <= out["bullpen_fatigue_score"] <= 0.65
    assert 0.10 <= out["bullpen_availability_score"] <= 0.95
    assert 0.08 <= out["bullpen_high_leverage_availability_score"] <= 0.95
