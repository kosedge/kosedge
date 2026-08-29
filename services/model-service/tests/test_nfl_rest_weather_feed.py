"""Rest + weather feed — schedule rest, Open-Meteo/NWS weather, stadium roof."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

from src.services.nfl_daily_intel import ALLOWED_FIELDS, normalize_override
from src.services.nfl_rest_weather_feed import (
    REST_WEATHER_FEED_VERSION,
    ScheduleGameRow,
    WeatherFetchResult,
    cards_with_rest_or_weather_modifier,
    compute_rest_fields,
    fetch_weather_cached,
    format_modifier_table,
    load_schedule_games,
    source_game_card,
    source_week_game_cards,
    timezone_shift_hours,
)
from src.services.nfl_rest_weather_game_card import (
    GAME_CARD_FIELDS,
    apply_rest_weather_game_card,
    reject_note_game_card_write,
)
from src.services.nfl_stadium_roof_table import (
    NFL_STADIUM_ROOF,
    resolve_roof,
    stadium_row_for_team,
)


def _game(
    *,
    week: int,
    home: str,
    away: str,
    kickoff: Optional[str] = None,
    venue: Optional[str] = None,
    season: int = 2026,
) -> ScheduleGameRow:
    return ScheduleGameRow(
        season=season,
        week=week,
        game_id=f"{season}-W{week:02d}-{away}@{home}",
        home_team=home,
        away_team=away,
        kickoff_utc=kickoff,
        venue=venue,
    )


def test_rest_from_schedule_kickoffs() -> None:
    """Days rest / short week / TZ derived from schedule kickoffs."""
    g1 = _game(
        week=1,
        home="KC",
        away="DEN",
        kickoff="2026-09-15T00:15:00.000Z",
    )
    g2 = _game(
        week=2,
        home="DEN",
        away="SEA",
        kickoff="2026-09-18T00:15:00.000Z",  # Thu → short week for DEN (~3d)
    )
    g3 = _game(
        week=2,
        home="SEA",
        away="NE",
        kickoff="2026-09-20T20:25:00.000Z",
    )
    # Fix SEA week-2 kickoff after their W1 — use separate slate:
    slate = [
        g1,
        g2,
        _game(
            week=1,
            home="SEA",
            away="NE",
            kickoff="2026-09-10T00:20:00.000Z",
        ),
        _game(
            week=2,
            home="SEA",
            away="SF",
            kickoff="2026-09-20T20:25:00.000Z",
        ),
    ]

    # Week 1: no prior REG → rest None; TZ DEN→KC = 1
    w1 = compute_rest_fields(g1, slate)
    assert w1["days_rest_home"] is None
    assert w1["days_rest_away"] is None
    assert w1["short_week"] is None
    assert w1["timezone_shift"] == pytest.approx(1.0)

    # DEN short week after MNF → Thu
    rest2 = compute_rest_fields(g2, slate)
    assert rest2["days_rest_home"] == 3  # Sep 15 → Sep 18
    assert rest2["short_week"] is True

    # Cross-country TZ
    assert timezone_shift_hours("SEA", "NE") == pytest.approx(3.0)

    # Remat would apply short_week / days_rest when card is sourced
    sourced = source_game_card(g2, slate, fetch_weather=False)
    assert sourced.card["days_rest_home"] == 3
    assert sourced.card["short_week"] is True
    mod = apply_rest_weather_game_card(sourced.card)
    factors = {e.factor for e in mod.applied}
    assert "short_week" in factors or "days_rest" in factors


def test_missing_timeout_weather_no_modifier(tmp_path: Path) -> None:
    """Timeout / missing weather ⇒ no KEI weather modifier (fields stay None)."""

    def boom(**kwargs: Any) -> WeatherFetchResult:
        return WeatherFetchResult(
            available=False,
            source="open-meteo",
            status="timeout",
            as_of="2026-08-29T12:00:00Z",
            error="timed out",
        )

    game = _game(
        week=1,
        home="PHI",
        away="WAS",
        kickoff="2026-09-13T20:25:00.000Z",
        venue="Lincoln Financial Field",
    )
    sourced = source_game_card(
        game,
        [game],
        fetch_weather=True,
        cache_dir=tmp_path,
        fetch_fn=boom,
    )
    assert sourced.card["roof"] == "outdoor"
    assert sourced.card["wind_mph"] is None
    assert sourced.card["precip"] is None
    assert sourced.card["temp_f"] is None
    assert sourced.weather_meta.get("status") == "timeout"
    mod = apply_rest_weather_game_card(sourced.card)
    assert mod.weather_applied is False
    weather_logs = [e for e in mod.considered_not_applied if e.factor == "weather"]
    assert weather_logs
    assert "no KEI change" in weather_logs[0].reason

    # Direct cache helper also records timeout without inventing wind=0
    kickoff = datetime(2026, 9, 13, 20, 25, tzinfo=timezone.utc)
    result = fetch_weather_cached(
        game_id=game.game_id,
        lat=39.9,
        lon=-75.1,
        kickoff=kickoff,
        cache_dir=tmp_path / "wx2",
        fetch_fn=boom,
    )
    assert result.available is False
    assert result.wind_mph is None


def test_notes_cannot_write_feed_fields() -> None:
    assert not (GAME_CARD_FIELDS & set(ALLOWED_FIELDS))
    for name in sorted(GAME_CARD_FIELDS):
        with pytest.raises(ValueError, match="notes cannot write game-card"):
            reject_note_game_card_write(name)
        with pytest.raises(ValueError):
            normalize_override(
                {
                    "team": "PHI",
                    "field": name,
                    "before": None,
                    "after": 1,
                    "source": "camp_note",
                    "confidence": 0.9,
                }
            )


def test_stadium_roof_table_explicit() -> None:
    assert stadium_row_for_team("DET")["roof"] == "dome"
    assert stadium_row_for_team("LV")["roof"] == "dome"
    assert stadium_row_for_team("PHI")["roof"] == "outdoor"
    assert stadium_row_for_team("LAC")["roof"] == "outdoor"  # SoFi — not wind=0 invent
    assert resolve_roof(home="IND") == "retractable_closed"
    assert resolve_roof(home="LA", venue="Melbourne Cricket Ground") == "outdoor"
    # Every 32-team franchise has a row (LA + LAC + LAR aliases ok)
    franchises = {
        "ARI",
        "ATL",
        "BAL",
        "BUF",
        "CAR",
        "CHI",
        "CIN",
        "CLE",
        "DAL",
        "DEN",
        "DET",
        "GB",
        "HOU",
        "IND",
        "JAX",
        "KC",
        "LAC",
        "LA",
        "LV",
        "MIA",
        "MIN",
        "NE",
        "NO",
        "NYG",
        "NYJ",
        "PHI",
        "PIT",
        "SEA",
        "SF",
        "TB",
        "TEN",
        "WAS",
    }
    for team in franchises:
        assert resolve_roof(home=team) is not None, team
    assert "LAR" in NFL_STADIUM_ROOF


def test_cache_writes_as_of(tmp_path: Path) -> None:
    def ok(**kwargs: Any) -> WeatherFetchResult:
        return WeatherFetchResult(
            available=True,
            wind_mph=22.0,
            precip=0.1,
            temp_f=68.0,
            source="open-meteo",
            status="ok",
            as_of="2026-08-29T15:00:00Z",
        )

    kickoff = datetime(2026, 9, 13, 17, 0, tzinfo=timezone.utc)
    first = fetch_weather_cached(
        game_id="2026-W01-TB@CIN",
        lat=39.1,
        lon=-84.5,
        kickoff=kickoff,
        cache_dir=tmp_path,
        fetch_fn=ok,
    )
    assert first.available is True
    assert first.cache_hit is False
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1
    payload = json.loads(files[0].read_text(encoding="utf-8"))
    assert payload.get("as_of")
    assert payload["wind_mph"] == 22.0
    # Cache clock as_of is write time (not the stub provider stamp).
    assert payload.get("fetched_at") == "2026-08-29T15:00:00Z"

    second = fetch_weather_cached(
        game_id="2026-W01-TB@CIN",
        lat=39.1,
        lon=-84.5,
        kickoff=kickoff,
        cache_dir=tmp_path,
        fetch_fn=ok,
    )
    assert second.cache_hit is True
    assert second.as_of == payload["as_of"]


def test_packaged_schedule_loads_week1() -> None:
    games, meta = load_schedule_games(2026)
    assert meta["game_count"] >= 16
    w1 = [g for g in games if g.week == 1]
    assert len(w1) == 16
    # Canonical overlay should attach kickoffs when repo path is present
    with_kick = [g for g in w1 if g.kickoff_utc]
    assert len(with_kick) >= 14
    assert REST_WEATHER_FEED_VERSION.startswith("rest_weather_feed_")


def test_indoor_skips_weather_fetch(tmp_path: Path) -> None:
    called = {"n": 0}

    def should_not_run(**kwargs: Any) -> WeatherFetchResult:
        called["n"] += 1
        return WeatherFetchResult(available=True, wind_mph=40.0, source="x", status="ok")

    game = _game(
        week=1,
        home="DET",
        away="NO",
        kickoff="2026-09-13T17:00:00.000Z",
        venue="Ford Field",
    )
    sourced = source_game_card(
        game, [game], fetch_weather=True, cache_dir=tmp_path, fetch_fn=should_not_run
    )
    assert sourced.card["roof"] == "dome"
    assert called["n"] == 0
    assert sourced.card["wind_mph"] is None
    mod = apply_rest_weather_game_card(sourced.card)
    assert mod.weather_applied is False


def test_format_week1_modifier_table_smoke() -> None:
    """Offline smoke: TZ-only cards appear in the modifier print filter."""
    cards, _meta = source_week_game_cards(
        week=1, season=2026, fetch_weather=False
    )
    hits = cards_with_rest_or_weather_modifier(cards)
    # Several W1 games cross a TZ band (e.g. NE@SEA, MIA@LV).
    assert len(hits) >= 1
    table = format_modifier_table(hits)
    assert "timezone_shift" in table or "Applied" in table
    assert "@" in table
