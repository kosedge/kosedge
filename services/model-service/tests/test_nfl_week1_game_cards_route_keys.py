"""Fair-lines Week 1 cards — route lookup keys, not hand-stubbed flags.

Live FAIL after #403: game_card_source=failed, SF@LAR stayed on legacy
same-coast / visual_crossing. Tests must use the same (home, away) keys the
API emits (LAR, SF) and must not set ``_international`` after sourcing.
"""

from __future__ import annotations

from src.services.nfl_kei_week1_reprice import apply_week1_kei_reprice, load_week1_pack
from src.services.nfl_week1_game_cards import (
    WEEK1_INTERNATIONAL_SITES,
    build_week1_game_cards,
    lookup_week1_game_card,
)


def test_build_week1_cards_lookup_lar_sf_is_melbourne() -> None:
    """API emits home_abbr=LAR away_abbr=SF — that exact key must hit Melbourne."""
    index = build_week1_game_cards(season=2026, fetch_weather=False)
    card = lookup_week1_game_card(index, home_abbr="LAR", away_abbr="SF")
    assert card is not None, "week1_game_cards[(LAR, SF)] missing — route would legacy"
    # Must come from the builder, not a test-side stub.
    assert card.get("_international") is True
    assert card.get("_venue") == "Melbourne Cricket Ground"
    assert card.get("_location") == "Melbourne"
    assert index.kickoff_for("LAR", "SF",) or index.kickoffs.get(("LAR", "SF"))
    ko = index.kickoff_for("LAR", "SF")
    assert ko is not None and ko.startswith("2026-09-11T00:35")


def test_build_week1_cards_lookup_la_sf_alias() -> None:
    index = build_week1_game_cards(season=2026, fetch_weather=False)
    card = lookup_week1_game_card(index, home_abbr="LA", away_abbr="SF")
    assert card is not None
    assert card.get("_location") == "Melbourne"


def test_baked_melbourne_survives_schedule_failure(monkeypatch) -> None:
    """Railway: schedule/canonical may fail — bake-in must still serve (LAR, SF)."""

    def _boom(*_a, **_k):
        raise RuntimeError("schedule missing on image")

    monkeypatch.setattr(
        "src.services.nfl_rest_weather_feed.source_week_game_cards",
        _boom,
    )
    # build imports source_week_game_cards inside try — force total schedule failure
    import src.services.nfl_week1_game_cards as mod

    def _build_fail(*_a, **_k):
        raise RuntimeError("no schedule")

    monkeypatch.setattr(
        "src.services.nfl_rest_weather_feed.source_week_game_cards",
        _build_fail,
        raising=False,
    )
    # Even if import path raises, baked sites alone must work via direct inject.
    from src.services.nfl_week1_game_cards import Week1GameCardIndex, _inject_baked_international

    index = Week1GameCardIndex(source="failed")
    _inject_baked_international(index)
    card = index.lookup("LAR", "SF")
    assert card is not None
    assert card["_venue"] == "Melbourne Cricket Ground"
    assert card["_international"] is True
    assert any(s["home_abbr"] == "LAR" for s in WEEK1_INTERNATIONAL_SITES)


def test_kei_reprice_via_route_lookup_no_hand_stub() -> None:
    """End-to-end: builder → (LAR, SF) lookup → reprice chips. No _international stub."""
    index = build_week1_game_cards(season=2026, fetch_weather=False)
    card = lookup_week1_game_card(index, home_abbr="LAR", away_abbr="SF")
    assert card is not None
    # Refuse test-side mutation — card must already be international from builder.
    assert "_international" in card and card["_international"] is True

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
        start_time="2026-09-10T20:00:00Z",  # legacy odds commence must not win chips
    )
    chips = " ".join(
        e["reason"]
        for e in (log.get("applied_factors") or [])
        + (log.get("considered_not_applied") or [])
    )
    assert "same-coast (SF → LA)" not in chips
    assert "visual_crossing" not in chips.lower()
    assert "Melbourne" in chips
    assert "Cricket Ground" in chips
    travel = next(
        (
            e
            for e in (log.get("considered_not_applied") or [])
            if e.get("factor") == "travel"
        ),
        None,
    )
    weather = next(
        (
            e
            for e in (log.get("considered_not_applied") or [])
            if e.get("factor") == "weather"
        ),
        None,
    )
    assert travel is not None and "Melbourne" in str(travel.get("reason"))
    assert weather is not None and "Melbourne" in str(weather.get("reason"))


def test_kei_reprice_none_card_still_blocks_legacy_for_sf_lar() -> None:
    """Even game_card=None must not emit LA same-coast for SF@LAR Week 1."""
    pack = load_week1_pack(2026)
    _h, log = apply_week1_kei_reprice(
        handicap={"spread_home": -3.5, "total_mean": 48.0, "home_win_prob": 0.58},
        home_abbr="LAR",
        away_abbr="SF",
        week=1,
        season=2026,
        season_type="REG",
        pack=pack,
        game_card=None,
    )
    chips = " ".join(
        e["reason"]
        for e in (log.get("applied_factors") or [])
        + (log.get("considered_not_applied") or [])
    )
    assert "same-coast (SF → LA)" not in chips
    assert "visual_crossing" not in chips.lower()
    assert "Melbourne" in chips
