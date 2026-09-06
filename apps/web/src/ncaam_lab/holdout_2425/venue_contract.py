"""Venue status contract for Lab holdout foundation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ncaam_lab.holdout_2425.constants import (
    HISTORICAL_STATIC_RECONSTRUCTION,
    SCHEMA_VERSION_VENUE,
    VENUE_STATUS,
)


def normalize_venue_status(
    *,
    neutral_site_raw: Optional[bool],
    venue_name: Optional[str],
    home_team_id: Optional[str],
    season_type: Optional[str],
) -> Dict[str, Any]:
    """Fail-closed venue normalization."""
    conflict_reason: Optional[str] = None
    raw = neutral_site_raw

    if raw is None:
        status = "unknown"
    elif raw is True:
        status = "confirmed_neutral"
    else:
        status = "confirmed_home"
        st = str(season_type or "").lower()
        if st in {"postseason", "post"} and venue_name:
            home_tok = (home_team_id or "").replace(" ", "")
            vlow = venue_name.lower().replace(" ", "")
            if home_tok and home_tok not in vlow and any(
                k in vlow for k in ("arena", "center", "coliseum", "garden", "dome")
            ):
                status = "unknown"
                conflict_reason = "postseason_venue_home_token_mismatch"

    if status not in VENUE_STATUS:
        raise ValueError(status)
    return {
        "venue_status": status,
        "neutral_site_raw": raw,
        "conflict_reason": conflict_reason,
        "metadata_class": HISTORICAL_STATIC_RECONSTRUCTION,
        "schema_version": SCHEMA_VERSION_VENUE,
        "validation_status": "ok" if conflict_reason is None else "conflict_unknown",
        "historical_reconstruction": True,
    }


def build_venue_table(games: List[Dict[str, Any]]) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    counts = {"confirmed_home": 0, "confirmed_neutral": 0, "unknown": 0, "conflicts": 0}
    for g in games:
        home = g.get("home")
        away = g.get("away")
        eid = g.get("espn_game_id") or g.get("game_id")
        norm = normalize_venue_status(
            neutral_site_raw=g.get("neutral_site"),
            venue_name=g.get("venue"),
            home_team_id=home,
            season_type=g.get("season_type"),
        )
        counts[norm["venue_status"]] = counts.get(norm["venue_status"], 0) + 1
        if norm["conflict_reason"]:
            counts["conflicts"] += 1
        rows.append(
            {
                "source_event_id": eid,
                "b7_join_key": f"{g.get('date')}|{home}|{away}",
                "tip_date": g.get("date"),
                "home_team_id": home,
                "away_team_id": away,
                "venue_name": g.get("venue"),
                "venue_id": g.get("venue_id"),
                "venue_city": g.get("venue_city"),
                "venue_state": g.get("venue_state"),
                "source_path": g.get("source_url")
                or g.get("source_endpoint")
                or "espn_scoreboard_public",
                "captured_at": g.get("source_capture_timestamp"),
                "effective_event_time": g.get("tipoff") or g.get("kickoff"),
                "historical_reconstruction_flag": True,
                **norm,
            }
        )
    return {
        "schema_version": SCHEMA_VERSION_VENUE,
        "n_rows": len(rows),
        "coverage_counts": counts,
        "rows": rows,
        "scores_omitted": True,
        "independent_source_validation": "espn_neutralSite_primary_only_phase_26a",
        "note": (
            "Phase 2.6A venue data contract only; B2-PACE-NEUTRAL-v1 not implemented. "
            "Tournament≠auto-neutral; designated-home≠auto-home-court."
        ),
    }
