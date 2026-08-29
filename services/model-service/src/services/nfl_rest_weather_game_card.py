"""Rest + weather game-card fields — cheap handicap modifiers on remat / KEI.

Doctrine
--------
- Game-card / schedule + forecast fields only. Not depth-pack SoT.
- Deterministic remat modifiers from explicit fields — never invent weather.
- **Missing weather ⇒ no KEI change** (no climatology, no stadium guess).
- Notes / camp / sleeper / DepthSot notes **cannot write** these fields.
- Out of scope: snap shares, shock_table_v1 edits, live desk accepts.

Fields
------
``days_rest_home``, ``days_rest_away``, ``short_week``, ``timezone_shift``,
``roof``, ``wind_mph``, ``precip``, ``temp_f``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

REST_WEATHER_VERSION = "rest_weather_game_card_v1"

GAME_CARD_FIELDS = frozenset(
    {
        "days_rest_home",
        "days_rest_away",
        "short_week",
        "timezone_shift",
        "roof",
        "wind_mph",
        "precip",
        "temp_f",
    }
)

# Hard contract — notes / proposals never invent rest or weather card values.
NOTES_CANNOT_WRITE_GAME_CARD_FIELDS = True

# Indoor / dome / typically-closed retractable roofs — weather bands do not fire.
ROOF_INDOOR = frozenset(
    {
        "dome",
        "indoor",
        "retractable_closed",
        "closed",
        "roof_closed",
    }
)
ROOF_OUTDOOR = frozenset({"outdoor", "open", "retractable_open", "roof_open"})

# Magnitudes aligned with Gate B / B.1 desk bands (totals first for weather).
REST_ADVANTAGE_DAYS = 3
REST_ADVANTAGE_SPREAD = 0.50
REST_ADVANTAGE_TOTAL = 0.15

SHORT_WEEK_MAX_DAYS = 5
SHORT_WEEK_SPREAD = 0.75
SHORT_WEEK_TOTAL = -0.25

# timezone_shift = |away_tz − home_tz| hours west-of-ET style bands.
TZ_BANDS: Tuple[Tuple[int, float, float], ...] = (
    (3, 1.00, -0.50),
    (2, 0.75, -0.30),
    (1, 0.35, -0.15),
)

WEATHER_TOTAL_CAP = 1.5
WIND_BAND_MPH = 20.0
WIND_EXTREME_MPH = 25.0
COLD_BAND_F = 20.0
PRECIP_BAND = 2.0  # precip field units (mm when from forecast)


def _to_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> Optional[int]:
    f = _to_float(value)
    if f is None:
        return None
    return int(round(f))


def _to_bool(value: Any) -> Optional[bool]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in {"1", "true", "yes", "y", "short"}:
        return True
    if s in {"0", "false", "no", "n"}:
        return False
    return None


def _norm_roof(raw: Any) -> Optional[str]:
    if raw is None or raw == "":
        return None
    s = str(raw).strip().lower()
    return s or None


def _clamp(value: float, cap: float) -> float:
    if value > cap:
        return cap
    if value < -cap:
        return -cap
    return value


@dataclass
class FactorLog:
    factor: str
    applied: bool
    spread_pts: float = 0.0
    total_pts: float = 0.0
    reason: str = ""
    source: str = REST_WEATHER_VERSION

    def as_dict(self) -> Dict[str, Any]:
        return {
            "factor": self.factor,
            "applied": self.applied,
            "spread_pts": round(self.spread_pts, 4),
            "total_pts": round(self.total_pts, 4),
            "reason": self.reason,
            "source": self.source,
        }


@dataclass
class GameCard:
    """Cheap handicap card for remat. Missing weather fields stay None."""

    days_rest_home: Optional[int] = None
    days_rest_away: Optional[int] = None
    short_week: Optional[bool] = None
    timezone_shift: Optional[float] = None
    roof: Optional[str] = None
    wind_mph: Optional[float] = None
    precip: Optional[float] = None
    temp_f: Optional[float] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "days_rest_home": self.days_rest_home,
            "days_rest_away": self.days_rest_away,
            "short_week": self.short_week,
            "timezone_shift": self.timezone_shift,
            "roof": self.roof,
            "wind_mph": self.wind_mph,
            "precip": self.precip,
            "temp_f": self.temp_f,
        }


@dataclass
class RestWeatherResult:
    spread_delta: float = 0.0  # home-spread convention: + = home weaker
    total_delta: float = 0.0
    weather_applied: bool = False
    applied: List[FactorLog] = field(default_factory=list)
    considered_not_applied: List[FactorLog] = field(default_factory=list)
    source: str = REST_WEATHER_VERSION

    def as_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "spread_delta": round(self.spread_delta, 4),
            "total_delta": round(self.total_delta, 4),
            "weather_applied": self.weather_applied,
            "applied_factors": [e.as_dict() for e in self.applied],
            "considered_not_applied": [e.as_dict() for e in self.considered_not_applied],
        }


def parse_game_card(raw: Optional[Mapping[str, Any]]) -> GameCard:
    """Parse only GAME_CARD_FIELDS — ignore depth / note / snap keys."""
    if not raw:
        return GameCard()
    return GameCard(
        days_rest_home=_to_int(raw.get("days_rest_home")),
        days_rest_away=_to_int(raw.get("days_rest_away")),
        short_week=_to_bool(raw.get("short_week")),
        timezone_shift=_to_float(raw.get("timezone_shift")),
        roof=_norm_roof(raw.get("roof")),
        wind_mph=_to_float(raw.get("wind_mph")),
        precip=_to_float(raw.get("precip")),
        temp_f=_to_float(raw.get("temp_f")),
    )


def assert_notes_cannot_write_game_card_fields() -> None:
    """Guardrail — notes / camp / DepthSot overrides never own rest/weather card."""
    assert NOTES_CANNOT_WRITE_GAME_CARD_FIELDS is True
    # Lazy import avoids circular import at module load.
    from src.services.nfl_daily_intel import ALLOWED_FIELDS

    overlap = GAME_CARD_FIELDS & set(ALLOWED_FIELDS)
    assert not overlap, f"notes ALLOWED_FIELDS must not include game-card fields: {overlap}"


def notes_may_write_game_card_field(field: str) -> bool:
    """Always False for GAME_CARD_FIELDS; True for unrelated field names."""
    name = str(field or "").strip()
    if name in GAME_CARD_FIELDS:
        return False
    return True


def reject_note_game_card_write(field: str) -> None:
    """Raise if a note / override tries to write a rest/weather game-card field."""
    name = str(field or "").strip()
    if name in GAME_CARD_FIELDS:
        raise ValueError(
            f"notes cannot write game-card field {name!r} "
            f"(rest/weather remat SoT only; {REST_WEATHER_VERSION})"
        )


def weather_is_missing(card: GameCard) -> bool:
    """True when outdoor (or unknown roof) and no usable weather readings."""
    roof = card.roof
    if roof is not None and roof in ROOF_INDOOR:
        return False  # indoor is an explicit "no weather" state, not missing
    return card.wind_mph is None and card.precip is None and card.temp_f is None


def _days_rest_modifiers(card: GameCard, out: RestWeatherResult) -> None:
    home_r = card.days_rest_home
    away_r = card.days_rest_away
    if home_r is None and away_r is None:
        out.considered_not_applied.append(
            FactorLog(
                factor="days_rest",
                applied=False,
                reason="days_rest not on game-card — not applied",
            )
        )
        return

    if home_r is None or away_r is None:
        out.considered_not_applied.append(
            FactorLog(
                factor="days_rest",
                applied=False,
                reason="days_rest incomplete (need home+away) — not applied",
            )
        )
        return

    delta = home_r - away_r  # + = home more rested
    if abs(delta) < REST_ADVANTAGE_DAYS:
        out.considered_not_applied.append(
            FactorLog(
                factor="days_rest",
                applied=False,
                reason=(
                    f"days_rest home={home_r} away={away_r} "
                    f"(Δ{delta:+d} < {REST_ADVANTAGE_DAYS}) — not applied"
                ),
            )
        )
        return

    # Home more rested → home stronger → home spread more negative.
    sign = -1.0 if delta > 0 else 1.0
    spr = sign * REST_ADVANTAGE_SPREAD
    tot = REST_ADVANTAGE_TOTAL if delta > 0 else -REST_ADVANTAGE_TOTAL
    out.spread_delta += spr
    out.total_delta += tot
    out.applied.append(
        FactorLog(
            factor="days_rest",
            applied=True,
            spread_pts=spr,
            total_pts=tot,
            reason=(
                f"days_rest home={home_r} away={away_r} "
                f"(Δ{delta:+d} ≥ {REST_ADVANTAGE_DAYS}) — rested side stronger"
            ),
        )
    )


def _short_week_modifiers(card: GameCard, out: RestWeatherResult) -> None:
    flagged = card.short_week
    home_r = card.days_rest_home
    away_r = card.days_rest_away

    short_home = False
    short_away = False
    if flagged is True:
        # Explicit card flag without side → treat as away short week (visitor).
        if home_r is not None and home_r <= SHORT_WEEK_MAX_DAYS:
            short_home = True
        if away_r is not None and away_r <= SHORT_WEEK_MAX_DAYS:
            short_away = True
        if not short_home and not short_away:
            short_away = True
    else:
        if home_r is not None and home_r <= SHORT_WEEK_MAX_DAYS:
            short_home = True
        if away_r is not None and away_r <= SHORT_WEEK_MAX_DAYS:
            short_away = True

    if flagged is False and not short_home and not short_away:
        out.considered_not_applied.append(
            FactorLog(
                factor="short_week",
                applied=False,
                reason="short_week false on game-card — not applied",
            )
        )
        return

    if not short_home and not short_away and flagged is None:
        out.considered_not_applied.append(
            FactorLog(
                factor="short_week",
                applied=False,
                reason="short_week not on game-card — not applied",
            )
        )
        return

    if not short_home and not short_away:
        out.considered_not_applied.append(
            FactorLog(
                factor="short_week",
                applied=False,
                reason="short_week flagged but no side ≤5 days rest — not applied",
            )
        )
        return

    if short_home and short_away:
        out.considered_not_applied.append(
            FactorLog(
                factor="short_week",
                applied=False,
                reason="both sides short week — offset, not applied",
            )
        )
        return

    if short_away:
        # Away weaker → home relatively stronger → spread more negative.
        spr, tot = -SHORT_WEEK_SPREAD, SHORT_WEEK_TOTAL
        side = "away"
    else:
        spr, tot = SHORT_WEEK_SPREAD, SHORT_WEEK_TOTAL
        side = "home"

    out.spread_delta += spr
    out.total_delta += tot
    out.applied.append(
        FactorLog(
            factor="short_week",
            applied=True,
            spread_pts=spr,
            total_pts=tot,
            reason=f"short_week {side} (≤{SHORT_WEEK_MAX_DAYS} days rest) — side weaker",
        )
    )


def _timezone_modifiers(card: GameCard, out: RestWeatherResult) -> None:
    shift = card.timezone_shift
    if shift is None:
        out.considered_not_applied.append(
            FactorLog(
                factor="timezone_shift",
                applied=False,
                reason="timezone_shift not on game-card — not applied",
            )
        )
        return

    bands = abs(float(shift))
    chosen: Optional[Tuple[float, float]] = None
    band_n = 0
    for threshold, spr, tot in TZ_BANDS:
        if bands >= threshold:
            chosen = (spr, tot)
            band_n = threshold
            break

    if chosen is None:
        out.considered_not_applied.append(
            FactorLog(
                factor="timezone_shift",
                applied=False,
                reason=f"timezone_shift {shift:g} (same-coast) — not applied",
            )
        )
        return

    # Positive timezone_shift means away travels west of home (visitor weaker).
    # Negative means home is the traveler relative to venue convention —
    # we still tax the visitor absolute bands; sign of shift only for logging.
    spr, tot = -chosen[0], chosen[1]
    out.spread_delta += spr
    out.total_delta += tot
    out.applied.append(
        FactorLog(
            factor="timezone_shift",
            applied=True,
            spread_pts=spr,
            total_pts=tot,
            reason=(
                f"timezone_shift {shift:g} (≥{band_n} band) — visitor weaker"
            ),
        )
    )


def _weather_modifiers(card: GameCard, out: RestWeatherResult) -> None:
    roof = card.roof
    if roof is not None and roof in ROOF_INDOOR:
        out.considered_not_applied.append(
            FactorLog(
                factor="roof",
                applied=False,
                reason=f"roof={roof} indoor — weather not applied (no KEI change)",
            )
        )
        out.considered_not_applied.append(
            FactorLog(
                factor="weather",
                applied=False,
                reason="weather not applied (indoor roof)",
            )
        )
        return

    if weather_is_missing(card):
        roof_note = f"roof={roof}" if roof else "roof unset"
        out.considered_not_applied.append(
            FactorLog(
                factor="weather",
                applied=False,
                reason=(
                    f"weather missing ({roof_note}; no wind/precip/temp) "
                    f"— no KEI change"
                ),
            )
        )
        return

    notes: List[str] = []
    total = 0.0
    wind = card.wind_mph
    temp = card.temp_f
    precip = card.precip

    if wind is not None:
        if wind >= WIND_EXTREME_MPH:
            total -= 1.5
            notes.append(f"wind {wind:.0f} mph")
        elif wind >= WIND_BAND_MPH:
            total -= 1.0
            notes.append(f"wind {wind:.0f} mph")
    if temp is not None and temp <= COLD_BAND_F:
        total -= 0.5
        notes.append(f"temp {temp:.0f}F")
    if precip is not None and precip >= PRECIP_BAND:
        total -= 0.5
        notes.append(f"precip {precip:.1f}")

    total = _clamp(total, WEATHER_TOTAL_CAP)

    if roof is not None and roof in ROOF_OUTDOOR:
        out.considered_not_applied.append(
            FactorLog(
                factor="roof",
                applied=False,
                reason=f"roof={roof} outdoor — weather bands eligible",
            )
        )

    if not notes:
        detail = []
        if wind is not None:
            detail.append(f"wind {wind:.0f}")
        if temp is not None:
            detail.append(f"temp {temp:.0f}F")
        if precip is not None:
            detail.append(f"precip {precip:.1f}")
        tail = ", ".join(detail) if detail else "bands quiet"
        out.considered_not_applied.append(
            FactorLog(
                factor="weather",
                applied=False,
                reason=f"weather below KEI bands ({tail}) — no KEI change",
            )
        )
        return

    out.total_delta += total
    out.weather_applied = True
    out.applied.append(
        FactorLog(
            factor="weather",
            applied=True,
            total_pts=total,
            reason=(
                f"weather game-card: {', '.join(notes)} "
                f"(totals first, cap ±{WEATHER_TOTAL_CAP})"
            ),
        )
    )


def apply_rest_weather_game_card(
    card_raw: Optional[Mapping[str, Any]] = None,
    *,
    card: Optional[GameCard] = None,
) -> RestWeatherResult:
    """Deterministic remat modifiers from game-card fields only.

    Missing weather ⇒ weather factor not applied (spread/total weather = 0).
    """
    parsed = card if card is not None else parse_game_card(card_raw)
    out = RestWeatherResult()
    _days_rest_modifiers(parsed, out)
    _short_week_modifiers(parsed, out)
    _timezone_modifiers(parsed, out)
    _weather_modifiers(parsed, out)
    out.spread_delta = round(out.spread_delta, 4)
    out.total_delta = round(out.total_delta, 4)
    return out


def build_game_card_from_teams(
    *,
    home: str,
    away: str,
    days_rest_home: Any = None,
    days_rest_away: Any = None,
    short_week: Any = None,
    roof: Any = None,
    wind_mph: Any = None,
    precip: Any = None,
    temp_f: Any = None,
    timezone_shift: Any = None,
    tz_hours_fn: Optional[Any] = None,
) -> GameCard:
    """Helper for remat callers — derives timezone_shift when not supplied."""
    shift = _to_float(timezone_shift)
    if shift is None and tz_hours_fn is not None:
        try:
            shift = float(abs(tz_hours_fn(away) - tz_hours_fn(home)))
        except Exception:
            shift = None
    return GameCard(
        days_rest_home=_to_int(days_rest_home),
        days_rest_away=_to_int(days_rest_away),
        short_week=_to_bool(short_week),
        timezone_shift=shift,
        roof=_norm_roof(roof),
        wind_mph=_to_float(wind_mph),
        precip=_to_float(precip),
        temp_f=_to_float(temp_f),
    )
