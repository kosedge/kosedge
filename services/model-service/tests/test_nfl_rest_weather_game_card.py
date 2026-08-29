"""Rest + weather game-card — deterministic remat modifiers; notes cannot write."""

from __future__ import annotations

import pytest

from src.services.nfl_camp_sot_queue import assert_notes_cannot_touch_lines
from src.services.nfl_daily_intel import ALLOWED_FIELDS, normalize_override
from src.services.nfl_kei_week1_reprice import Week1Pack, apply_week1_kei_reprice
from src.services.nfl_rest_weather_game_card import (
    GAME_CARD_FIELDS,
    NOTES_CANNOT_WRITE_GAME_CARD_FIELDS,
    REST_ADVANTAGE_SPREAD,
    REST_WEATHER_VERSION,
    SHORT_WEEK_SPREAD,
    apply_rest_weather_game_card,
    assert_notes_cannot_write_game_card_fields,
    notes_may_write_game_card_field,
    parse_game_card,
    reject_note_game_card_write,
    weather_is_missing,
)


def _handicap(spread: float = -3.0, total: float = 44.0) -> dict:
    return {"spread_home": spread, "total_mean": total, "home_win_prob": 0.58}


def test_game_card_field_set_is_exact() -> None:
    assert GAME_CARD_FIELDS == {
        "days_rest_home",
        "days_rest_away",
        "short_week",
        "timezone_shift",
        "roof",
        "wind_mph",
        "precip",
        "temp_f",
    }
    assert REST_WEATHER_VERSION == "rest_weather_game_card_v1"
    assert NOTES_CANNOT_WRITE_GAME_CARD_FIELDS is True


def test_missing_weather_no_kei_change() -> None:
    """Missing weather = no KEI change (no invent)."""
    empty = apply_rest_weather_game_card({})
    assert empty.weather_applied is False
    assert empty.total_delta == 0.0
    assert empty.spread_delta == 0.0
    reasons = " ".join(e.reason for e in empty.considered_not_applied)
    assert "weather missing" in reasons or "no KEI change" in reasons

    outdoor_missing = apply_rest_weather_game_card(
        {"roof": "outdoor", "timezone_shift": 0}
    )
    assert outdoor_missing.weather_applied is False
    assert outdoor_missing.total_delta == 0.0
    weather = [e for e in outdoor_missing.considered_not_applied if e.factor == "weather"]
    assert weather and "no KEI change" in weather[0].reason

    assert weather_is_missing(parse_game_card({"roof": "outdoor"})) is True
    assert weather_is_missing(parse_game_card({"roof": "dome"})) is False


def test_notes_cannot_write_game_card_fields() -> None:
    assert_notes_cannot_write_game_card_fields()
    assert_notes_cannot_touch_lines()
    assert not (GAME_CARD_FIELDS & set(ALLOWED_FIELDS))

    for name in sorted(GAME_CARD_FIELDS):
        assert notes_may_write_game_card_field(name) is False
        with pytest.raises(ValueError, match="notes cannot write game-card"):
            reject_note_game_card_write(name)
        with pytest.raises(ValueError):
            normalize_override(
                {
                    "team": "PHI",
                    "field": name,
                    "before": None,
                    "after": 1,
                    "reason": "should fail",
                    "as_of": "2026-08-29",
                    "destination": "kei_only",
                }
            )

    assert notes_may_write_game_card_field("injury_status") is True


def test_deterministic_days_rest_modifier() -> None:
    # Home +4 rest days vs away → home stronger → spread more negative
    a = apply_rest_weather_game_card(
        {"days_rest_home": 10, "days_rest_away": 6, "roof": "dome"}
    )
    b = apply_rest_weather_game_card(
        {"days_rest_home": 10, "days_rest_away": 6, "roof": "dome"}
    )
    assert a.as_dict() == b.as_dict()
    assert a.spread_delta == pytest.approx(-REST_ADVANTAGE_SPREAD)
    assert any(e.factor == "days_rest" and e.applied for e in a.applied)

    small = apply_rest_weather_game_card(
        {"days_rest_home": 7, "days_rest_away": 6, "roof": "dome"}
    )
    assert small.spread_delta == 0.0
    assert any(
        e.factor == "days_rest" and not e.applied for e in small.considered_not_applied
    )


def test_deterministic_short_week_modifier() -> None:
    # Equal rest so days_rest advantage does not stack; away ≤5 → short week.
    card = {"days_rest_home": 4, "days_rest_away": 4, "short_week": True, "roof": "dome"}
    a = apply_rest_weather_game_card(card)
    b = apply_rest_weather_game_card(card)
    assert a.as_dict() == b.as_dict()
    # Both short → offset, not applied when both ≤5
    assert a.spread_delta == 0.0

    away_only = {
        "days_rest_home": 7,
        "days_rest_away": 4,
        "short_week": True,
        "roof": "dome",
    }
    # Rest Δ=3 also fires — isolate short_week via flag without rest advantage:
    flag_only = {"short_week": True, "roof": "dome"}
    sw = apply_rest_weather_game_card(flag_only)
    assert sw.spread_delta == pytest.approx(-SHORT_WEEK_SPREAD)
    assert any(e.factor == "short_week" and e.applied for e in sw.applied)

    stacked = apply_rest_weather_game_card(away_only)
    assert any(e.factor == "short_week" and e.applied for e in stacked.applied)
    assert any(e.factor == "days_rest" and e.applied for e in stacked.applied)



def test_deterministic_timezone_shift_modifier() -> None:
    a = apply_rest_weather_game_card({"timezone_shift": 3, "roof": "dome"})
    b = apply_rest_weather_game_card({"timezone_shift": 3, "roof": "dome"})
    assert a.as_dict() == b.as_dict()
    assert a.spread_delta == pytest.approx(-1.0)
    assert a.total_delta == pytest.approx(-0.50)
    assert any(e.factor == "timezone_shift" and e.applied for e in a.applied)

    same = apply_rest_weather_game_card({"timezone_shift": 0, "roof": "dome"})
    assert same.spread_delta == 0.0
    assert any(
        e.factor == "timezone_shift" and not e.applied
        for e in same.considered_not_applied
    )


def test_deterministic_roof_blocks_weather() -> None:
    extreme = {
        "roof": "dome",
        "wind_mph": 30,
        "precip": 5,
        "temp_f": 5,
    }
    a = apply_rest_weather_game_card(extreme)
    b = apply_rest_weather_game_card(extreme)
    assert a.as_dict() == b.as_dict()
    assert a.weather_applied is False
    assert a.total_delta == 0.0
    reasons = " ".join(e.reason for e in a.considered_not_applied)
    assert "indoor" in reasons


def test_deterministic_wind_precip_temp_modifiers() -> None:
    wind = apply_rest_weather_game_card(
        {"roof": "outdoor", "wind_mph": 28, "temp_f": 55, "precip": 0}
    )
    assert wind.weather_applied is True
    assert wind.total_delta == pytest.approx(-1.5)
    assert wind.spread_delta == 0.0  # weather is totals-only

    cold_precip = apply_rest_weather_game_card(
        {"roof": "outdoor", "wind_mph": 10, "temp_f": 15, "precip": 3}
    )
    assert cold_precip.total_delta == pytest.approx(-1.0)  # cold 0.5 + precip 0.5
    assert any("temp" in e.reason for e in cold_precip.applied)
    assert any("precip" in e.reason for e in cold_precip.applied)

    # Determinism
    again = apply_rest_weather_game_card(
        {"roof": "outdoor", "wind_mph": 10, "temp_f": 15, "precip": 3}
    )
    assert cold_precip.as_dict() == again.as_dict()


def test_remat_kei_uses_game_card_and_skips_missing_weather() -> None:
    """Accept → remat path: game_card drives rest/weather; missing weather flat."""
    new_h, log = apply_week1_kei_reprice(
        handicap=_handicap(),
        home_abbr="PHI",
        away_abbr="WAS",
        week=1,
        season=2026,
        pack=Week1Pack.empty(),
        game_card={
            "short_week": True,
            "timezone_shift": 0,
            "roof": "outdoor",
            # weather intentionally missing
        },
    )
    assert log["skipped"] is False
    factors = " ".join(e["reason"] for e in log["applied_factors"])
    not_applied = " ".join(e["reason"] for e in log["considered_not_applied"])
    assert "short_week" in factors
    assert "no KEI change" in not_applied or "weather missing" in not_applied
    # Short week away weaker → home stronger → more negative spread; weather 0
    assert new_h["spread_home"] == pytest.approx(-3.0 - SHORT_WEEK_SPREAD)
    assert log["total_delta"] == pytest.approx(-0.25)  # short_week total only
    assert not any(
        e["factor"] == "weather" and e["applied"] for e in log["applied_factors"]
    )


def test_remat_kei_game_card_extreme_wind() -> None:
    new_h, log = apply_week1_kei_reprice(
        handicap=_handicap(),
        home_abbr="SEA",
        away_abbr="NE",
        week=1,
        season=2026,
        pack=Week1Pack.empty(),
        game_card={
            "timezone_shift": 3,
            "roof": "outdoor",
            "wind_mph": 28,
            "temp_f": 50,
            "precip": 0,
        },
    )
    assert log["total_delta"] == pytest.approx(-2.0)  # TZ -0.5 + wind -1.5
    assert new_h["total_mean"] == pytest.approx(42.0)
    # timezone visitor weaker + weather totals-only
    assert new_h["spread_home"] == pytest.approx(-4.0)
    reasons = " ".join(e["reason"] for e in log["applied_factors"])
    assert "timezone_shift" in reasons and "wind 28" in reasons


def test_no_snap_or_shock_table_edits_in_module_contract() -> None:
    """Scope guard: this pack is rest+weather game-card only."""
    import src.services.nfl_rest_weather_game_card as mod

    src = open(mod.__file__, encoding="utf-8").read()
    assert "snap_share" not in src
    assert "shock_table" not in src or "Out of scope" in src or "shock_table_v1" in src
    # Module docstring lists out of scope
    assert "snap shares" in mod.__doc__
    assert "shock_table" in mod.__doc__
