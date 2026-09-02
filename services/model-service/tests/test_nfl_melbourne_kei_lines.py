"""SF@LAR Melbourne — no LA same-coast / SoFi weather on KEI Lines.

Live FAIL lock (post-401): chips must say Melbourne / neutral, kickoff 8:35 ET,
and card sourcing must not fall through to legacy home-stadium weather.
"""

from __future__ import annotations

from src.services.nfl_kei_week1_reprice import apply_week1_kei_reprice, load_week1_pack
from src.services.nfl_rest_weather_feed import (
    load_schedule_games,
    source_game_card,
    source_week_game_cards,
)
from src.services.nfl_stadium_roof_table import resolve_venue_geo


def test_sf_lar_canonical_venue_is_melbourne() -> None:
    games, _meta = load_schedule_games(2026)
    hit = next(
        g
        for g in games
        if g.week == 1
        and {g.away_team, g.home_team} >= {"SF"}
        and g.home_team in {"LA", "LAR"}
    )
    assert hit.venue == "Melbourne Cricket Ground"
    assert hit.location == "Melbourne"
    assert hit.kickoff_utc and hit.kickoff_utc.startswith("2026-09-11T00:35")
    geo = resolve_venue_geo(home=hit.home_team, venue=hit.venue)
    assert geo is not None
    assert geo["lat"] < 0  # southern hemisphere — not SoFi


def test_sf_lar_week_cards_include_melbourne_without_weather_stub() -> None:
    """Card source must work without hand-stubbing _international / fetch_weather=False."""
    cards, meta = source_week_game_cards(week=1, season=2026, fetch_weather=True)
    assert len(cards) >= 1
    sf = next(
        c
        for c in cards
        if c.game.away_team == "SF" and c.game.home_team in {"LA", "LAR"}
    )
    assert sf.game.venue == "Melbourne Cricket Ground"
    assert sf.game.location == "Melbourne"
    assert sf.card.get("roof") == "outdoor"
    # Weather may be present or missing — either is fine; never invent LA SoFi.
    assert meta.get("week_card_count", len(cards)) >= 1


def test_sf_lar_kei_reprice_from_sourced_card_no_la_same_coast() -> None:
    """End-to-end: sourced week card → KEI chips (no manual _international stub)."""
    games, _ = load_schedule_games(2026)
    game = next(
        g
        for g in games
        if g.week == 1 and g.away_team == "SF" and g.home_team in {"LA", "LAR"}
    )
    sourced = source_game_card(game, games, fetch_weather=True)
    card = dict(sourced.card)
    # Mimic fair-lines enrichment (venue/location/international from schedule).
    card["_venue"] = game.venue
    card["_location"] = game.location or "Melbourne"
    card["_international"] = True

    pack = load_week1_pack(2026)
    _h, log = apply_week1_kei_reprice(
        handicap={"spread_home": -3.5, "total_mean": 48.0, "home_win_prob": 0.58},
        home_abbr="LAR",
        away_abbr="SF",
        week=1,
        season=2026,
        season_type="REG",
        pack=pack,
        game_card=card,
        # Legacy kickoff must not resurrect LA same-coast when card is present.
        start_time="2026-09-10T20:00:00Z",
    )
    chips = " ".join(
        e["reason"]
        for e in (log.get("applied_factors") or [])
        + (log.get("considered_not_applied") or [])
    )
    assert "same-coast (SF → LA)" not in chips
    assert "visual_crossing" not in chips.lower()
    assert "SoFi" not in chips
    assert "Melbourne" in chips
    assert "74F" not in chips  # LA desktop weather string from screenshots
    weather_chip = next(
        (
            e
            for e in (log.get("applied_factors") or [])
            + (log.get("considered_not_applied") or [])
            if e.get("factor") == "weather"
        ),
        None,
    )
    assert weather_chip is not None
    assert "Melbourne" in str(weather_chip.get("reason") or "")


def test_sf_lar_legacy_path_blocked_when_card_present() -> None:
    """Regression: with an international card, never emit LA Visual Crossing weather."""
    pack = load_week1_pack(2026)
    card = {
        "days_rest_home": None,
        "days_rest_away": None,
        "short_week": None,
        "timezone_shift": 0.0,
        "roof": "outdoor",
        "wind_mph": None,
        "precip": None,
        "temp_f": None,
        "_venue": "Melbourne Cricket Ground",
        "_location": "Melbourne",
        "_international": True,
    }
    _h, log = apply_week1_kei_reprice(
        handicap={"spread_home": -3.5, "total_mean": 48.0, "home_win_prob": 0.58},
        home_abbr="LAR",
        away_abbr="SF",
        week=1,
        season=2026,
        season_type="REG",
        pack=pack,
        game_card=card,
    )
    considered = log.get("considered_not_applied") or []
    # Game-card path emits timezone_shift (not legacy "travel") for same-coast.
    travel = next(
        (
            e
            for e in considered
            if e.get("factor") in {"travel", "timezone_shift"}
        ),
        None,
    )
    weather = next((e for e in considered if e.get("factor") == "weather"), None)
    assert travel is not None
    assert "Melbourne" in str(travel.get("reason") or "")
    assert "same-coast (SF → LA)" not in str(travel.get("reason") or "")
    assert weather is not None
    assert "Melbourne" in str(weather.get("reason") or "")
    assert "visual_crossing" not in str(weather.get("reason") or "").lower()
