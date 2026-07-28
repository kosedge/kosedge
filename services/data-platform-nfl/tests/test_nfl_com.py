from __future__ import annotations

from data_platform_nfl import nfl_com


def test_fetch_nfl_com_team_intel_snapshot_normalizes_rows(monkeypatch) -> None:
    monkeypatch.setattr(nfl_com, "_resolve_auth_token", lambda: ("token", "test"))
    monkeypatch.setattr(nfl_com, "_resolve_week_context", lambda _token: (7, "REG"))

    def _fake_fetch_json(*, path, query, token, timeout_seconds=0.0, retries=0):  # type: ignore[no-untyped-def]
        assert token == "token"
        if path == "/football/v2/rosters":
            return {
                "items": [
                    {
                        "team_abbreviation": "BUF",
                        "persons": [
                            {
                                "person_gsis_id": "00-001",
                                "person_display_name": "Alpha QB",
                                "position": "QB",
                                "jersey_number": "17",
                            }
                        ],
                    }
                ]
            }
        if path == "/football/v2/standings":
            return {
                "items": [
                    {
                        "team_abbreviation": "BUF",
                        "wins": 6,
                        "losses": 1,
                        "ties": 0,
                        "points_for": 197,
                        "points_against": 151,
                        "win_pct": 0.8571,
                    }
                ]
            }
        if path == "/football/v2/stats/team-stats":
            return {
                "items": [
                    {
                        "team_abbreviation": "BUF",
                        "stats": {
                            "games_played": 7,
                            "offensive_plays": 452,
                            "defensive_plays": 428,
                            "pass_plays": 267,
                            "run_plays": 185,
                            "third_down_attempts": 93,
                            "third_down_conversions": 41,
                            "red_zone_plays": 58,
                            "red_zone_touchdowns": 37,
                            "pass_rate": 0.59,
                            "success_rate_offense": 0.47,
                            "success_rate_defense_allowed": 0.41,
                        },
                    }
                ]
            }
        raise AssertionError(f"Unexpected path: {path}")

    monkeypatch.setattr(nfl_com, "_fetch_json", _fake_fetch_json)
    payload = nfl_com.fetch_nfl_com_team_intel_snapshot(season=2026)

    assert payload["week"] == 7
    assert payload["season_type"] == "REG"
    assert payload["rosters"][0]["team"] == "BUF"
    assert payload["rosters"][0]["player_id"] == "00-001"
    assert payload["standings"][0]["wins"] == 6
    assert payload["team_stats"][0]["offensive_plays"] == 452
    assert payload["team_stats"][0]["pass_rate"] == 0.59
    assert payload["diagnostics"]["errors"] == []


def test_fetch_nfl_com_team_intel_snapshot_collects_endpoint_errors(monkeypatch) -> None:
    monkeypatch.setattr(nfl_com, "_resolve_auth_token", lambda: ("token", "test"))
    monkeypatch.setattr(nfl_com, "_resolve_week_context", lambda _token: (8, "REG"))

    def _fake_fetch_json(*, path, query, token, timeout_seconds=0.0, retries=0):  # type: ignore[no-untyped-def]
        if path == "/football/v2/rosters":
            return {"items": []}
        raise nfl_com.NflComError("boom")

    monkeypatch.setattr(nfl_com, "_fetch_json", _fake_fetch_json)
    payload = nfl_com.fetch_nfl_com_team_intel_snapshot(season=2026)

    assert payload["rosters"] == []
    assert payload["standings"] == []
    assert payload["team_stats"] == []
    assert any(str(err).startswith("standings:") for err in payload["diagnostics"]["errors"])
    assert any(str(err).startswith("team_stats:") for err in payload["diagnostics"]["errors"])
