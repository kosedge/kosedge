from __future__ import annotations

import os
from datetime import date

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

import src.services.mlb_data as mlb_data


def test_compute_fip_from_stat_elite_pitcher() -> None:
    # Elite K/BB → FIP well under league avg.
    elite = {
        "inningsPitched": "100.0",
        "homeRuns": 8,
        "baseOnBalls": 20,
        "hitByPitch": 2,
        "strikeOuts": 130,
        "groundOuts": 90,
        "airOuts": 80,
    }
    fip = mlb_data.compute_fip_from_stat(elite, use_xfip=False)
    assert fip is not None and fip < 3.5

    # HR-lucky (many HR allowed vs modest air outs) ⇒ xFIP should be kinder than FIP.
    hr_unlucky = {
        "inningsPitched": "100.0",
        "homeRuns": 22,
        "baseOnBalls": 30,
        "hitByPitch": 3,
        "strikeOuts": 90,
        "groundOuts": 120,
        "airOuts": 60,
    }
    fip_u = mlb_data.compute_fip_from_stat(hr_unlucky, use_xfip=False)
    xfip_u = mlb_data.compute_fip_from_stat(hr_unlucky, use_xfip=True)
    assert fip_u is not None and xfip_u is not None
    assert xfip_u < fip_u


def test_fip_proxy_ignores_bad_era_good_components(monkeypatch) -> None:
    mlb_data._live_starter_features.cache_clear()
    prior = mlb_data.get_starter_quality_mode()

    class _Resp:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    def fake_get(url, *args, **kwargs):
        if url.endswith("/people/search"):
            return _Resp(
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
        if "/people/700001/stats" in url:
            return _Resp(
                {
                    "stats": [
                        {
                            "splits": [
                                {
                                    "stat": {
                                        "era": "5.80",
                                        "whip": "1.45",
                                        "strikeoutsPer9Inn": "11.5",
                                        "walksPer9Inn": "1.8",
                                        "groundOutsToAirouts": "1.20",
                                        "inningsPitched": "90.0",
                                        "homeRuns": 6,
                                        "baseOnBalls": 18,
                                        "hitByPitch": 2,
                                        "strikeOuts": 115,
                                        "groundOuts": 100,
                                        "airOuts": 70,
                                    }
                                }
                            ]
                        }
                    ]
                }
            )
        raise AssertionError(url)

    try:
        monkeypatch.setattr(mlb_data.requests, "get", fake_get)
        mlb_data.apply_starter_quality_mode("era_whip")
        era = mlb_data.starter_identity_features("Tarik Skubal", season=2026)
        mlb_data.apply_starter_quality_mode("fip_proxy")
        fip = mlb_data.starter_identity_features("Tarik Skubal", season=2026)
        mlb_data.apply_starter_quality_mode("xfip_proxy")
        xfip = mlb_data.starter_identity_features("Tarik Skubal", season=2026)
        assert era["starter_quality"] > 1.0  # bad ERA/WHIP
        assert fip["starter_quality"] < 1.0  # good FIP components
        assert xfip["starter_quality"] < 1.05
        assert fip["quality_mode"] == "fip_proxy"
        assert "fip" in fip
        # walksPer9Inn must feed bb_factor (legacy baseOnBallsPer9Inn was always null)
        assert fip["bb_factor"] < 1.0
    finally:
        mlb_data.apply_starter_quality_mode(prior)


def test_as_of_uses_by_date_range(monkeypatch) -> None:
    mlb_data._live_starter_features.cache_clear()
    prior = mlb_data.get_starter_quality_mode()
    seen_params = []

    class _Resp:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    def fake_get(url, *args, **kwargs):
        params = kwargs.get("params") or {}
        if url.endswith("/people/search"):
            return _Resp(
                {
                    "people": [
                        {
                            "id": 700002,
                            "fullName": "Paul Skenes",
                            "active": True,
                            "primaryPosition": {"code": "1"},
                            "pitchHand": {"code": "R"},
                        }
                    ]
                }
            )
        if "/people/700002/stats" in url:
            seen_params.append(dict(params))
            return _Resp(
                {
                    "stats": [
                        {
                            "splits": [
                                {
                                    "stat": {
                                        "era": "2.50",
                                        "whip": "0.95",
                                        "strikeoutsPer9Inn": "11.0",
                                        "walksPer9Inn": "2.0",
                                        "groundOutsToAirouts": "1.1",
                                        "inningsPitched": "60.0",
                                        "homeRuns": 5,
                                        "baseOnBalls": 13,
                                        "hitByPitch": 1,
                                        "strikeOuts": 73,
                                        "groundOuts": 50,
                                        "airOuts": 45,
                                    }
                                }
                            ]
                        }
                    ]
                }
            )
        raise AssertionError(url)

    try:
        monkeypatch.setattr(mlb_data.requests, "get", fake_get)
        mlb_data.apply_starter_quality_mode("fip_proxy")
        feat = mlb_data.starter_identity_features(
            "Paul Skenes",
            season=2026,
            as_of=date(2026, 6, 15),
        )
        assert feat["as_of"] == "2026-06-15"
        assert feat["stat_window"] == "as_of_season"
        assert any(p.get("stats") == "byDateRange" for p in seen_params)
        by_range = next(p for p in seen_params if p.get("stats") == "byDateRange")
        assert by_range["endDate"] == "2026-06-14"  # day before game
        assert by_range["startDate"] == "2026-03-20"
    finally:
        mlb_data.apply_starter_quality_mode(prior)


def test_bullpen_role_quality_weights_closer(monkeypatch) -> None:
    prior = mlb_data.get_bullpen_role_quality_mode()

    class _Resp:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    schedule_payload = {
        "dates": [
            {"games": [{"status": {"codedGameState": "F"}, "gamePk": 2001}]},
        ]
    }
    # Elite closer line vs mop-up disaster — role weight should pull quality down less.
    box_payload = {
        "teams": {
            "home": {
                "team": {"id": 119},
                "players": {
                    "ID1": {
                        "stats": {
                            "pitching": {
                                "gamesStarted": "0",
                                "inningsPitched": "1.0",
                                "saves": "1",
                                "strikeOuts": "2",
                                "baseOnBalls": "0",
                                "homeRuns": "0",
                                "hitByPitch": "0",
                            }
                        }
                    },
                    "ID2": {
                        "stats": {
                            "pitching": {
                                "gamesStarted": "0",
                                "inningsPitched": "2.0",
                                "strikeOuts": "0",
                                "baseOnBalls": "3",
                                "homeRuns": "2",
                                "hitByPitch": "0",
                            }
                        }
                    },
                },
            },
            "away": {"team": {"id": 120}, "players": {}},
        }
    }

    def fake_get(url, *args, **kwargs):
        if "schedule" in url:
            return _Resp(schedule_payload)
        if "boxscore" in url:
            return _Resp(box_payload)
        raise AssertionError(url)

    try:
        monkeypatch.setattr(mlb_data.requests, "get", fake_get)
        mlb_data.apply_bullpen_role_quality_mode("off")
        off = mlb_data.fetch_team_bullpen_fatigue(119, date(2026, 6, 1))
        assert off["bullpen_quality"] == 1.0

        mlb_data.apply_bullpen_role_quality_mode("role_weighted")
        on = mlb_data.fetch_team_bullpen_fatigue(119, date(2026, 6, 1))
        # Closer weight should keep aggregate better than pure mop-up average.
        mop_only = mlb_data._reliever_app_fip_quality(
            box_payload["teams"]["home"]["players"]["ID2"]["stats"]["pitching"]
        )
        assert on["bullpen_quality"] < mop_only
        assert 0.85 <= on["bullpen_quality"] <= 1.15
        # Fatigue still computed independently.
        assert on["bullpen_fatigue_score"] != on["bullpen_quality"]
    finally:
        mlb_data.apply_bullpen_role_quality_mode(prior)


def test_walks_per_9_field_used_for_bb_factor() -> None:
    feat = mlb_data._starter_features_from_stat(
        starter_name="Test",
        player_id=1,
        season=2026,
        handedness="R",
        stat={
            "era": "4.00",
            "whip": "1.20",
            "strikeoutsPer9Inn": "8.5",
            "walksPer9Inn": "1.5",
            "groundOutsToAirouts": "1.0",
            "inningsPitched": "50.0",
            "homeRuns": 5,
            "baseOnBalls": 8,
            "hitByPitch": 1,
            "strikeOuts": 47,
        },
    )
    assert feat is not None
    assert feat["bb_factor"] < 1.0
