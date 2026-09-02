"""SF@LAR Melbourne — no LA same-coast / SoFi weather on KEI Lines."""

from __future__ import annotations

from src.services.nfl_kei_week1_reprice import apply_week1_kei_reprice, load_week1_pack
from src.services.nfl_rest_weather_feed import load_schedule_games, source_game_card
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
    geo = resolve_venue_geo(home=hit.home_team, venue=hit.venue)
    assert geo is not None
    assert geo["lat"] < 0  # southern hemisphere — not SoFi


def test_sf_lar_kei_reprice_no_la_same_coast_or_sofi_weather() -> None:
    games, _ = load_schedule_games(2026)
    game = next(
        g
        for g in games
        if g.week == 1 and g.away_team == "SF" and g.home_team in {"LA", "LAR"}
    )
    sourced = source_game_card(game, games, fetch_weather=False)
    card = dict(sourced.card)
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
    )
    chips = " ".join(
        e["reason"]
        for e in (log.get("applied_factors") or [])
        + (log.get("considered_not_applied") or [])
    )
    assert "same-coast (SF → LA)" not in chips
    assert "visual_crossing" not in chips.lower()
    assert "Melbourne" in chips or "neutral" in chips.lower()
    assert "74F" not in chips  # LA desktop weather string from screenshots
