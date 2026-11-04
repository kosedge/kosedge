"""Per-target prior-assigned-week + nominal KO−60 history filter. CERT=0."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Iterable, Mapping

from src.services.nfl_r7_record_date_retro_c1.pins import KO_MINUS_MINUTES
from src.services.nfl_r7_record_date_retro_c1.refuse import RetroRefuse
from src.services.nfl_r7_record_date_retro_c1.rest import parse_nominal_utc


def filter_history_for_target(
    history: Iterable[Mapping[str, Any]],
    *,
    target_season: int,
    target_week: int,
    target_game_id: str,
    nominal_kickoff_utc: str,
) -> dict[str, Any]:
    """Keep strictly earlier assigned-week rows whose kickoff is before KO−60."""
    kickoff = parse_nominal_utc(nominal_kickoff_utc, name="nominal_kickoff_utc")
    cutoff = kickoff - timedelta(minutes=KO_MINUS_MINUTES)
    kept: list[dict[str, Any]] = []
    dropped: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in history:
        gid = str(raw.get("game_id") or "").strip()
        if not gid:
            raise RetroRefuse("history row missing game_id")
        if gid in seen:
            raise RetroRefuse(f"duplicate history identity {gid}")
        seen.add(gid)
        if gid == target_game_id:
            dropped.append({"game_id": gid, "reason": "target_own_game"})
            continue
        season = int(raw.get("season"))
        week = int(raw.get("week"))
        earlier_week = season < int(target_season) or (
            season == int(target_season) and week < int(target_week)
        )
        if not earlier_week:
            dropped.append({"game_id": gid, "reason": "not_prior_assigned_week"})
            continue
        hist_ko = parse_nominal_utc(
            raw.get("kickoff_utc") or raw.get("nominal_kickoff_utc"),
            name=f"{gid}.kickoff_utc",
        )
        if hist_ko >= cutoff:
            dropped.append({"game_id": gid, "reason": "not_before_nominal_ko_minus_60"})
            continue
        # Identity/state only on the filtered path. Scores stay on SYNTHETIC fixtures.
        kept.append(dict(raw))
    return {
        "target_game_id": target_game_id,
        "target_season": int(target_season),
        "target_week": int(target_week),
        "nominal_kickoff_utc": kickoff.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "nominal_cutoff_utc": cutoff.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ko_minus_minutes": KO_MINUS_MINUTES,
        "n_in": len(seen),
        "n_kept": len(kept),
        "n_dropped": len(dropped),
        "rows": kept,
        "dropped": dropped,
        "actual_clock_claimed": False,
    }
