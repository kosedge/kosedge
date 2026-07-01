import os
from datetime import date

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services import nfl_data


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_fetch_nfl_schedule_parses_espn_scoreboard(monkeypatch) -> None:
    payload = {
        "events": [
            {
                "id": "401547001",
                "date": "2026-09-11T00:20:00Z",
                "competitions": [
                    {
                        "status": {"type": {"description": "Scheduled"}},
                        "competitors": [
                            {
                                "homeAway": "home",
                                "team": {"id": "12", "displayName": "Kansas City Chiefs", "abbreviation": "KC"},
                                "score": "24",
                                "records": [{"summary": "12-5"}],
                            },
                            {
                                "homeAway": "away",
                                "team": {"id": "2", "displayName": "Buffalo Bills", "abbreviation": "BUF"},
                                "score": "17",
                                "records": [{"summary": "11-6"}],
                            },
                        ],
                    }
                ],
            }
        ]
    }

    monkeypatch.setattr(nfl_data.requests, "get", lambda *args, **kwargs: _Resp(payload))
    out = nfl_data.fetch_nfl_schedule(date(2026, 9, 11), date(2026, 9, 11))
    assert len(out) == 1
    assert out[0]["home_team"] == "Kansas City Chiefs"
    assert out[0]["away_team"] == "Buffalo Bills"
    assert out[0]["home_score"] == 24
    assert out[0]["away_score"] == 17


def test_team_strength_from_record_handles_basic_cases() -> None:
    off, deff = nfl_data.team_strength_from_record("12-5")
    assert off > 1.0
    assert deff < 1.0
    off2, deff2 = nfl_data.team_strength_from_record(None)
    assert off2 == 1.0
    assert deff2 == 1.0
