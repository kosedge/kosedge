"""REST_RECORDED_GAME_DATE_RETRO_V1 — date arithmetic only. CERT=0.

Recorded football calendar date, not actual UTC kickoff. No 7/default/cap
fallback. Home/away independent. Equal latest dates refuse.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable, Mapping

from src.services.nfl_r7_correctness_v1.franchise import franchise_key
from src.services.nfl_r7_record_date_retro_c1.pins import CALENDAR_ID
from src.services.nfl_r7_record_date_retro_c1.refuse import RetroRefuse


def parse_recorded_date(raw: Any, *, name: str = "recorded_game_date") -> date:
    text = str(raw or "").strip()
    if not text:
        raise RetroRefuse(f"{name} missing")
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise RetroRefuse(f"{name} is not an ISO date: {raw!r}") from exc


def refuse_naive_as_utc(raw: Any, *, name: str) -> None:
    text = str(raw or "").strip()
    if not text:
        return
    if text.endswith("Z") or "+" in text[10:]:
        return
    # Naive start_time_raw / nflverse_gametime must never become UTC.
    raise RetroRefuse(f"{name} naive timestamp must not be inferred as UTC: {raw!r}")


def _row_teams(row: Mapping[str, Any]) -> tuple[str, str]:
    home = franchise_key(row.get("home") or row.get("home_team") or row.get("home_franchise"))
    away = franchise_key(row.get("away") or row.get("away_team") or row.get("away_franchise"))
    if home == away:
        raise RetroRefuse(f"home/away franchise collision {home}")
    return home, away


def project_recorded_date_rest(
    *,
    target: Mapping[str, Any],
    schedule: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Select unique most-recent same-season REG with strictly earlier date."""
    tgt_id = str(target.get("game_id") or "").strip()
    if not tgt_id:
        raise RetroRefuse("target game_id missing")
    season = int(target.get("season"))
    tgt_date = parse_recorded_date(
        target.get("recorded_game_date") or target.get("game_date") or target.get("recorded_target_date"),
        name="target_recorded_date",
    )
    home, away = _row_teams(target)
    seen: dict[str, tuple[str, str, str]] = {}
    pool: list[dict[str, Any]] = []
    for raw in schedule:
        gid = str(raw.get("game_id") or "").strip()
        if not gid:
            raise RetroRefuse("schedule row missing game_id")
        st = str(raw.get("season_type") or "REG").strip().upper()
        if st != "REG":
            raise RetroRefuse(f"non-REG schedule row {gid}")
        row_season = int(raw.get("season"))
        rec = parse_recorded_date(
            raw.get("recorded_game_date") or raw.get("game_date"),
            name=f"{gid}.recorded_game_date",
        )
        h, a = _row_teams(raw)
        ident = (h, a, rec.isoformat())
        prior = seen.get(gid)
        if prior is not None and prior != ident:
            raise RetroRefuse(f"duplicate/conflicting identity {gid}")
        seen[gid] = ident
        if gid == tgt_id:
            continue
        if row_season != season:
            continue
        if rec >= tgt_date:
            continue
        pool.append({"game_id": gid, "home": h, "away": a, "date": rec, "season": row_season})

    def _pick(team: str) -> dict[str, Any]:
        cands = [row for row in pool if team in {row["home"], row["away"]}]
        if not cands:
            raise RetroRefuse(f"missing prior same-season recorded date for {team} before {tgt_id}")
        latest = max(row["date"] for row in cands)
        top = [row for row in cands if row["date"] == latest]
        if len(top) != 1:
            raise RetroRefuse(f"equal latest recorded dates for {team} before {tgt_id}")
        return top[0]

    home_prev = _pick(home)
    away_prev = _pick(away)
    home_days = (tgt_date - home_prev["date"]).days
    away_days = (tgt_date - away_prev["date"]).days
    if home_days < 1 or away_days < 1:
        raise RetroRefuse("recorded-date rest days < 1")
    return {
        "calendar_id": CALENDAR_ID,
        "game_id": tgt_id,
        "season": season,
        "home_franchise": home,
        "away_franchise": away,
        "recorded_target_date": tgt_date.isoformat(),
        "home": {
            "calendar_days": home_days,
            "predecessor_game_id": home_prev["game_id"],
            "recorded_predecessor_date": home_prev["date"].isoformat(),
        },
        "away": {
            "calendar_days": away_days,
            "predecessor_game_id": away_prev["game_id"],
            "recorded_predecessor_date": away_prev["date"].isoformat(),
        },
        "asymmetric": home_days != away_days,
        "used_utc_hours": False,
        "used_default_seven": False,
        "used_actual_kickoff": False,
        "claimed_actual_clock": False,
        "status": "RECORDED_DATE_METADATA_ONLY_NOT_ACTUAL_CLOCK_GO",
    }


def parse_nominal_utc(raw: Any, *, name: str) -> datetime:
    text = str(raw or "").strip()
    if not text:
        raise RetroRefuse(f"{name} missing")
    if not (text.endswith("Z") or text.endswith("z") or "+" in text[10:]):
        raise RetroRefuse(f"{name} naive datetime refused: {raw!r}")
    if text.endswith("Z") or text.endswith("z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError as exc:
        raise RetroRefuse(f"{name} is not a time: {raw!r}") from exc
