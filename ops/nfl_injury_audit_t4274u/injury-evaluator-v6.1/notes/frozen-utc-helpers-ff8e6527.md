# W-4 frozen UTC helpers + null contract `ff8e6527`

Filed before any v5 scorer run. Source: HEAD `8e2a15ac` file
`services/model-service/src/services/nfl_injury_null_contract.py`
sha256 `ff8e6527f63b0afd727eed30444436ceae320cc336d9113a2634fd66d4aebad2`

Full file deposited at `seeded/nfl_injury_null_contract_8e2a15ac.py`.

Evaluator P-4 is stricter than these helpers: a **naive/zoneless** timestamp in the
scorer is STOP. These fit-path helpers still treat naive report times as UTC and
naive kickoffs as America/New_York. That difference is disclosed; the scorer does
not call these helpers on the fold path.

## `parse_fit_kickoff_utc` (L590–614)

```
def parse_fit_kickoff_utc(gameday: Any, gametime: Any) -> datetime:
    """UTC-normalize a fit-path kickoff. Missing gametime fails the row (G-4 / C-4).

    Source wall clock is America/New_York. Never defaults to 23:59:59.
    """
    if gametime is None or str(gametime).strip() == "":
        raise FitRowFailure("missing gametime")
    if isinstance(gametime, datetime):
        kickoff = gametime
        if kickoff.tzinfo is None:
            kickoff = kickoff.replace(tzinfo=FIT_KICKOFF_SOURCE_TZ)
        return kickoff.astimezone(timezone.utc)
    if gameday is None or str(gameday).strip() == "":
        raise FitRowFailure("missing gameday")
    if isinstance(gameday, datetime):
        day = gameday.date()
    else:
        day_text = str(gameday).strip()
        try:
            day = datetime.strptime(day_text[:10], "%Y-%m-%d").date()
        except ValueError as exc:
            raise FitRowFailure(f"unparseable gameday: {gameday!r}") from exc
    clock = gametime if isinstance(gametime, time) else _parse_clock_component(gametime)
    local = datetime.combine(day, clock, tzinfo=FIT_KICKOFF_SOURCE_TZ)
    return local.astimezone(timezone.utc)
```

`FIT_KICKOFF_SOURCE_TZ = ZoneInfo("America/New_York")`. Never 23:59:59.

## `parse_fit_report_time_utc` (L617–635)

```
def parse_fit_report_time_utc(value: Any) -> Optional[datetime]:
    """UTC-normalize a listing report_time. None stays None (caller fails the row)."""
    if value is None or str(value).strip() == "":
        return None
    if isinstance(value, datetime):
        stamp = value
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        return stamp.astimezone(timezone.utc)
    raw = str(value).strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        stamp = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp.astimezone(timezone.utc)
```

Naive `date_modified` is treated as UTC on the fit path. The v5 scorer does not
do that: P-4 dies on zoneless input.
