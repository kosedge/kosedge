"""REST_ACTUAL_ET_CALENDAR_V1 — rest from America/New_York calendar dates.

Does not import nfl_data.rest_days_from_schedule (IF-forbidden weekday heuristic).
Does not use UTC date subtraction as the bound rest.
CERT=0. Synthetic kickoffs only.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping
from zoneinfo import ZoneInfo

from src.services.nfl_r7_correctness_v1.franchise import franchise_key
from src.services.nfl_r7_correctness_v1.pins import CALENDAR_ID, CALENDAR_TZ


class CalendarRefuse(ValueError):
    """Fail-closed ET calendar rest."""


_ET = ZoneInfo(CALENDAR_TZ)


def parse_aware_utc(raw: Any, *, name: str) -> datetime:
    text = str(raw or "").strip()
    if not text:
        raise CalendarRefuse(f"{name} missing")
    if text.endswith("Z") or text.endswith("z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError as exc:
        raise CalendarRefuse(f"{name} is not a time: {raw!r}") from exc
    if dt.tzinfo is None:
        raise CalendarRefuse(f"{name} naive datetime refused: {raw!r}")
    return dt.astimezone(timezone.utc)


def et_calendar_date(dt: datetime) -> str:
    return dt.astimezone(_ET).date().isoformat()


def rest_days_et(prev_kickoff_utc: datetime, this_kickoff_utc: datetime) -> int:
    if this_kickoff_utc <= prev_kickoff_utc:
        raise CalendarRefuse("this kickoff does not follow previous kickoff")
    prev_d = this_kickoff_utc.astimezone(_ET).date()
    last_d = prev_kickoff_utc.astimezone(_ET).date()
    delta = (prev_d - last_d).days
    if delta < 1:
        raise CalendarRefuse(f"ET rest days {delta} < 1")
    return delta


def utc_calendar_date_delta(prev_kickoff_utc: datetime, this_kickoff_utc: datetime) -> int:
    return (this_kickoff_utc.astimezone(timezone.utc).date() - prev_kickoff_utc.astimezone(timezone.utc).date()).days


def last_kickoff_for_franchise(
    history: list[Mapping[str, Any]],
    *,
    franchise: str,
    before: datetime,
) -> datetime | None:
    latest: datetime | None = None
    for row in history:
        home = franchise_key(row.get("home_team"))
        away = franchise_key(row.get("away_team"))
        if franchise not in {home, away}:
            continue
        ko = parse_aware_utc(row.get("kickoff_utc"), name="history.kickoff_utc")
        if ko >= before:
            continue
        if latest is None or ko > latest:
            latest = ko
    return latest


def bind_rest_from_et_calendar(
    *,
    home_team: str,
    away_team: str,
    kickoff_utc: str,
    history: list[Mapping[str, Any]],
) -> dict[str, Any]:
    kickoff = parse_aware_utc(kickoff_utc, name="kickoff_utc")
    home_key = franchise_key(home_team)
    away_key = franchise_key(away_team)
    home_prev = last_kickoff_for_franchise(history, franchise=home_key, before=kickoff)
    away_prev = last_kickoff_for_franchise(history, franchise=away_key, before=kickoff)
    if home_prev is None or away_prev is None:
        raise CalendarRefuse("missing prior game for franchise rest bind")
    home_et = rest_days_et(home_prev, kickoff)
    away_et = rest_days_et(away_prev, kickoff)
    return {
        "calendar_id": CALENDAR_ID,
        "tz": CALENDAR_TZ,
        "kickoff_utc": kickoff.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "kickoff_et_date": et_calendar_date(kickoff),
        "home_franchise": home_key,
        "away_franchise": away_key,
        "home_prev_kickoff_utc": home_prev.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "away_prev_kickoff_utc": away_prev.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "home_prev_et_date": et_calendar_date(home_prev),
        "away_prev_et_date": et_calendar_date(away_prev),
        "rest_days_home": float(home_et),
        "rest_days_away": float(away_et),
        "utc_date_delta_home": utc_calendar_date_delta(home_prev, kickoff),
        "utc_date_delta_away": utc_calendar_date_delta(away_prev, kickoff),
        "used_production_rest_days_from_schedule": False,
        "bound_from": "actual_prior_kickoff_et_calendar_date",
    }
