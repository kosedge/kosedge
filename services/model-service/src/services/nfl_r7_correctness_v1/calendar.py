"""REST_ACTUAL_ET_CALENDAR_V1 — rest from America/New_York calendar dates.

Physical-schedule (non-outcome) input only. Q2 scored history must not
set rest and must not be blocked by validate.py same-week refuse.
Predecessor filter is KO−60 cutoff, not kickoff.
Same-season / REG / PLAYED / source-availability / duplicate-identity
checks; unsupported or ambiguous predecessors refuse.
Preserves actual-versus-scheduled proof. Uses actual kickoff, not scheduled.
Does not import nfl_data.rest_days_from_schedule (IF-forbidden weekday heuristic).
Does not use UTC date subtraction as the bound rest.
CERT=0. Synthetic kickoffs only.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping
from zoneinfo import ZoneInfo

from src.services.nfl_r7_correctness_v1.franchise import franchise_key
from src.services.nfl_r7_correctness_v1.pins import CALENDAR_ID, CALENDAR_TZ, KO_MINUS_MINUTES


class CalendarRefuse(ValueError):
    """Fail-closed ET calendar rest."""


class CalendarHold(CalendarRefuse):
    """Unknown source-availability timestamps — HOLD, not a source-string check."""


_ET = ZoneInfo(CALENDAR_TZ)
_PHYS_REQUIRED = (
    "game_id",
    "season",
    "week",
    "season_type",
    "home_team",
    "away_team",
    "kickoff_utc",
    "status",
    "kickoff_kind",
    "source",
)


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


def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _require_phys_row(row: Mapping[str, Any], *, index: int) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        raise CalendarRefuse(f"physical_schedule[{index}] is not a row")
    missing = [name for name in _PHYS_REQUIRED if row.get(name) in (None, "")]
    if missing:
        raise CalendarRefuse(f"physical_schedule[{index}] missing {missing}")
    actual_raw = row.get("actual_kickoff_utc")
    if actual_raw in (None, ""):
        raise CalendarRefuse(
            "actual_kickoff_utc missing — fallback upgrade to kickoff_utc refused"
        )
    actual = parse_aware_utc(actual_raw, name="actual_kickoff_utc")
    listed = parse_aware_utc(row.get("kickoff_utc"), name="kickoff_utc")
    if actual != listed:
        raise CalendarRefuse(
            "kickoff_utc must equal actual_kickoff_utc (actual-versus-scheduled proof)"
        )
    scheduled_raw = row.get("scheduled_kickoff_utc")
    scheduled = parse_aware_utc(scheduled_raw, name="scheduled_kickoff_utc") if scheduled_raw else actual
    home = franchise_key(row.get("home_team"), source=row.get("home_team_source"))
    away = franchise_key(row.get("away_team"), source=row.get("away_team_source"))
    if home == away:
        raise CalendarRefuse(f"physical_schedule[{index}] home/away franchise collision {home}")
    return {
        "game_id": str(row["game_id"]).strip(),
        "season": int(row["season"]),
        "week": int(row["week"]),
        "season_type": str(row["season_type"]).strip().upper(),
        "home_team": home,
        "away_team": away,
        "kickoff_utc": actual,
        "actual_kickoff_utc": actual,
        "scheduled_kickoff_utc": scheduled,
        "status": str(row["status"]).strip().upper(),
        "kickoff_kind": str(row["kickoff_kind"]).strip().upper(),
        "source": str(row["source"]).strip(),
        "available_at": row.get("available_at"),
        "observed_at": row.get("observed_at"),
        "used_actual_not_scheduled": scheduled != actual,
    }


def _availability_stamp(raw: Any, *, name: str) -> datetime | None:
    text = str(raw or "").strip()
    if not text or text.upper() in {"UNKNOWN", "NONE", "NULL", "N/A"}:
        return None
    return parse_aware_utc(text, name=name)


def assert_source_available_before_seal(row: Mapping[str, Any], *, seal: datetime) -> dict[str, str]:
    """Strict before-seal observed/available timestamps. Unknown → HOLD."""
    available = _availability_stamp(row.get("available_at"), name="available_at")
    observed = _availability_stamp(row.get("observed_at"), name="observed_at")
    if available is None or observed is None:
        raise CalendarHold(
            f"source-availability HOLD: unknown timestamps for {row.get('game_id')}"
        )
    if available >= seal or observed >= seal:
        raise CalendarHold(
            f"source-availability HOLD: timestamps not strictly before seal for {row.get('game_id')}"
        )
    if observed < available:
        raise CalendarRefuse(f"observed_at before available_at for {row.get('game_id')}")
    return {
        "available_at": _fmt(available),
        "observed_at": _fmt(observed),
        "availability": "BEFORE_SEAL",
    }


def last_kickoff_for_franchise(
    physical_schedule: list[Mapping[str, Any]],
    *,
    franchise: str,
    before: datetime,
    kickoff: datetime,
    target_season: int,
) -> dict[str, Any] | None:
    """Return the latest same-season REG PLAYED actual-kickoff predecessor record.

    Direct API: `before` must equal actual kickoff − 60 minutes. Missing
    kickoff or a non-exact cutoff refuses. Rejects unsupported or ambiguous
    predecessors. Other-season rows are excluded, not selected. Duplicate
    game_id identities refuse.
    """
    if kickoff is None:
        raise CalendarRefuse("last_kickoff requires actual kickoff for exact KO−60")
    expected = kickoff - timedelta(minutes=KO_MINUS_MINUTES)
    if before != expected:
        raise CalendarRefuse(
            f"last_kickoff before must equal kickoff−{KO_MINUS_MINUTES} exactly"
        )
    latest: dict[str, Any] | None = None
    seen_ids: dict[str, tuple[str, str, str]] = {}
    for index, raw in enumerate(physical_schedule):
        row = _require_phys_row(raw, index=index)
        ident = (row["home_team"], row["away_team"], _fmt(row["kickoff_utc"]))
        prior = seen_ids.get(row["game_id"])
        if prior is not None and prior != ident:
            raise CalendarRefuse(f"duplicate-identity {row['game_id']}")
        seen_ids[row["game_id"]] = ident
        if franchise not in {row["home_team"], row["away_team"]}:
            continue
        if row["kickoff_utc"] >= before:
            continue
        if row["season"] != int(target_season):
            continue
        if row["season_type"] != "REG":
            raise CalendarRefuse("unsupported predecessor season_type (REG required)")
        if row["status"] != "PLAYED":
            raise CalendarRefuse("predecessor not PLAYED")
        if row["kickoff_kind"] != "ACTUAL_KICKOFF":
            raise CalendarRefuse("predecessor kickoff_kind must be ACTUAL_KICKOFF")
        availability = assert_source_available_before_seal(row, seal=before)
        row = {**row, **availability}
        if latest is not None and row["kickoff_utc"] == latest["kickoff_utc"]:
            if row["game_id"] != latest["game_id"]:
                raise CalendarRefuse("ambiguous predecessor identity")
            continue
        if latest is None or row["kickoff_utc"] > latest["kickoff_utc"]:
            latest = row
    return latest


def _require_physical_schedule(physical_schedule: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    if not isinstance(physical_schedule, list) or not physical_schedule:
        raise CalendarRefuse("physical_schedule missing")
    out: list[Mapping[str, Any]] = []
    for index, row in enumerate(physical_schedule):
        if not isinstance(row, Mapping):
            raise CalendarRefuse(f"physical_schedule[{index}] is not a row")
        if "home_score" in row or "away_score" in row:
            raise CalendarRefuse(
                "physical_schedule must be non-outcome — Q2 scored history cannot set rest"
            )
        out.append(row)
    return out


def bind_rest_from_et_calendar(
    *,
    home_team: str,
    away_team: str,
    kickoff_utc: str,
    physical_schedule: list[Mapping[str, Any]],
    target_season: int,
    cutoff_utc: str | None = None,
    history: list[Mapping[str, Any]] | None = None,
    home_source: Any = None,
    away_source: Any = None,
) -> dict[str, Any]:
    if history is not None:
        raise CalendarRefuse(
            "Q2 history cannot set physical rest — pass physical_schedule "
            "(validate.py same-week refuse must not block rest)"
        )
    schedule = _require_physical_schedule(physical_schedule)
    kickoff = parse_aware_utc(kickoff_utc, name="kickoff_utc")
    expected_cutoff = kickoff - timedelta(minutes=KO_MINUS_MINUTES)
    if cutoff_utc is None:
        cutoff = expected_cutoff
    else:
        cutoff = parse_aware_utc(cutoff_utc, name="cutoff_utc")
        if cutoff != expected_cutoff:
            raise CalendarRefuse(
                f"cutoff_utc must equal kickoff−{KO_MINUS_MINUTES} exactly"
            )
    home_key = franchise_key(home_team, source=home_source)
    away_key = franchise_key(away_team, source=away_source)
    # D2b: predecessor filter bound to exact KO−60 cutoff, not KO and not a near miss.
    home_prev = last_kickoff_for_franchise(
        schedule,
        franchise=home_key,
        before=cutoff,
        kickoff=kickoff,
        target_season=int(target_season),
    )
    away_prev = last_kickoff_for_franchise(
        schedule,
        franchise=away_key,
        before=cutoff,
        kickoff=kickoff,
        target_season=int(target_season),
    )
    if home_prev is None or away_prev is None:
        raise CalendarRefuse("missing prior game for franchise rest bind")
    home_ko = home_prev["kickoff_utc"]
    away_ko = away_prev["kickoff_utc"]
    home_et = rest_days_et(home_ko, kickoff)
    away_et = rest_days_et(away_ko, kickoff)
    return {
        "calendar_id": CALENDAR_ID,
        "tz": CALENDAR_TZ,
        "kickoff_utc": _fmt(kickoff),
        "cutoff_utc": _fmt(cutoff),
        "kickoff_et_date": et_calendar_date(kickoff),
        "target_season": int(target_season),
        "home_franchise": home_key,
        "away_franchise": away_key,
        "home_prev_kickoff_utc": _fmt(home_ko),
        "away_prev_kickoff_utc": _fmt(away_ko),
        "home_prev_et_date": et_calendar_date(home_ko),
        "away_prev_et_date": et_calendar_date(away_ko),
        "home_prev_game_id": home_prev["game_id"],
        "away_prev_game_id": away_prev["game_id"],
        "home_prev_status": home_prev["status"],
        "away_prev_status": away_prev["status"],
        "home_prev_kickoff_kind": home_prev["kickoff_kind"],
        "away_prev_kickoff_kind": away_prev["kickoff_kind"],
        "home_prev_source": home_prev["source"],
        "away_prev_source": away_prev["source"],
        "home_prev_available_at": home_prev["available_at"],
        "away_prev_available_at": away_prev["available_at"],
        "home_prev_observed_at": home_prev["observed_at"],
        "away_prev_observed_at": away_prev["observed_at"],
        "home_prev_availability": home_prev["availability"],
        "away_prev_availability": away_prev["availability"],
        "home_prev_used_actual_not_scheduled": home_prev["used_actual_not_scheduled"],
        "away_prev_used_actual_not_scheduled": away_prev["used_actual_not_scheduled"],
        "rest_days_home": float(home_et),
        "rest_days_away": float(away_et),
        "utc_date_delta_home": utc_calendar_date_delta(home_ko, kickoff),
        "utc_date_delta_away": utc_calendar_date_delta(away_ko, kickoff),
        "used_production_rest_days_from_schedule": False,
        "bound_from": "actual_prior_kickoff_et_calendar_date",
        "predecessor_bound_to": "KO_MINUS_60_CUTOFF",
        "physical_schedule": True,
        "q2_history_used_for_rest": False,
        "actual_versus_scheduled_proof": True,
        "actual_kickoff_provenance": "required",
        "exact_ko_minus_minutes": KO_MINUS_MINUTES,
        "missing_actual_fallback": False,
    }
