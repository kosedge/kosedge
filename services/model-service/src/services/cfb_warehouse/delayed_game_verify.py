"""Independent close of the #559 delayed game (research-only, no CFBD).

#559 included ESPN ``401868140`` (Eastern Kentucky @ Jacksonville State,
week 1) because the snapshot had scores and was not a live status.
The snapshot was ``STATUS_DELAYED`` 21–0 — a mid-game lightning delay,
not an official final.

A score alone is insufficient. This module confirms official final via
ESPN schedule/summary/box (no CFBD) and records include/exclude.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional
from urllib.request import Request, urlopen

DELAYED_GAME_ID = "401868140"
DELAYED_WEEK = 1
DELAYED_HOME = "Jacksonville State Gamecocks"
DELAYED_AWAY = "Eastern Kentucky Colonels"
# #559 snapshot (eligibility_manifest.json)
SNAPSHOT_STATUS = "STATUS_DELAYED"
SNAPSHOT_HOME_SCORE = 21
SNAPSHOT_AWAY_SCORE = 0
SNAPSHOT_INCLUDED = True

# Independently verified 2026-09-15 (this close).
OFFICIAL_STATUS = "STATUS_FINAL"
OFFICIAL_HOME_SCORE = 49
OFFICIAL_AWAY_SCORE = 7
OFFICIAL_STATE = "post"
OFFICIAL_COMPLETED = True

ESPN_SUMMARY_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/football/"
    "college-football/summary?event={game_id}"
)
ESPN_BOX_URL = "https://www.espn.com/college-football/boxscore/_/gameId/{game_id}"
ESPN_RECAP_URL = "https://www.espn.com/college-football/recap?gameId={game_id}"
USER_AGENT = "kosedge-cfb-research-opp-adj/1.0"

# Snapshot PBP/score is incomplete. Do not use the #559 21–0 / Q2 cut.
EXCLUDE_FROM_SNAPSHOT = True
EXCLUDE_REASON = (
    "excluded_incomplete_pbp: #559 PBP SHA da0ec956 ends Q2 10:27 at 28-0 "
    "(Nix INT TD). Official ESPN FINAL is 49-7 through Q4. Fail-closed."
)

# Official ESPN scoring sequence (2026-09-05). PBP must reach the last marker.
OFFICIAL_SCORING = (
    {"period": 1, "home": 7, "away": 0, "clock": "6:27", "note": "Williams 13yd pass"},
    {"period": 1, "home": 14, "away": 0, "clock": "4:25", "note": "Williams 55yd pass"},
    {"period": 2, "home": 21, "away": 0, "clock": "12:24", "note": "Williams 30yd pass"},
    {"period": 2, "home": 28, "away": 0, "clock": "10:27", "note": "Nix 43yd INT return"},
    {"period": 2, "home": 28, "away": 7, "clock": "9:45", "note": "Hensley 72yd rush"},
    {"period": 2, "home": 35, "away": 7, "clock": "5:28", "note": "Likely 45yd rush"},
    {"period": 3, "home": 42, "away": 7, "clock": "6:03", "note": "Gilbert 24yd pass"},
    {"period": 4, "home": 49, "away": 7, "clock": "7:09", "note": "Williams 4yd pass"},
)


def fetch_espn_summary(game_id: str = DELAYED_GAME_ID, *, timeout: int = 30) -> Dict[str, Any]:
    url = ESPN_SUMMARY_URL.format(game_id=game_id)
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    header = payload.get("header") or {}
    comps = header.get("competitions") or []
    comp = comps[0] if comps else {}
    status = (comp.get("status") or {}).get("type") or {}
    scores: Dict[str, Any] = {}
    for side in comp.get("competitors") or []:
        scores[str(side.get("homeAway"))] = {
            "team": ((side.get("team") or {}).get("displayName")),
            "score": _as_int(side.get("score")),
            "winner": bool(side.get("winner")),
        }
    return {
        "game_id": str(header.get("id") or game_id),
        "week": ((header.get("week") or {}) if isinstance(header.get("week"), dict) else {"number": header.get("week")}).get("number"),
        "status_name": status.get("name"),
        "status_state": status.get("state"),
        "status_completed": bool(status.get("completed")),
        "status_description": status.get("description"),
        "home": scores.get("home"),
        "away": scores.get("away"),
        "n_scoring_plays": len(payload.get("scoringPlays") or []),
        "n_previous_drives": len(((payload.get("drives") or {}).get("previous")) or []),
        "source": url,
    }


def _as_int(raw: Any) -> Optional[int]:
    if raw is None or raw == "":
        return None
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return None


def _norm_gid(raw: Any) -> str:
    gid = str(raw or "").strip()
    if gid.endswith(".0") and gid[:-2].replace("-", "", 1).isdigit():
        gid = gid[:-2]
    return gid


def audit_pbp_vs_official_final(
    plays: Any,
    *,
    game_id: str = DELAYED_GAME_ID,
) -> Dict[str, Any]:
    """Fail-closed completeness vs ESPN 49–7. Incomplete PBP → exclude.

    A completed-game schedule status is not enough if PBP stops at the delay.
    """
    rows = []
    for play in plays or []:
        if _norm_gid(play.get("game_id")) != str(game_id):
            continue
        rows.append(play)
    if not rows:
        return {
            "game_id": str(game_id),
            "n_plays": 0,
            "n_drives": 0,
            "max_period": None,
            "max_home_score": None,
            "max_away_score": None,
            "last_clock": None,
            "last_type": None,
            "reached_official_markers": [],
            "missing_official_markers": [dict(m) for m in OFFICIAL_SCORING],
            "complete_through_final": False,
            "decision": "exclude",
            "reason": "no_pbp_rows",
            "fail_closed": True,
        }

    def _max_score(keys: tuple[str, ...]) -> Optional[int]:
        best = None
        for play in rows:
            for key in keys:
                val = _as_int(play.get(key))
                if val is None:
                    continue
                best = val if best is None else max(best, val)
        return best

    periods = [_as_int(p.get("period") or p.get("qtr") or p.get("quarter")) for p in rows]
    periods = [p for p in periods if p is not None]
    max_period = max(periods) if periods else None
    max_home = _max_score(("end.homeScore", "homeScore", "lag_homeScore"))
    max_away = _max_score(("end.awayScore", "awayScore", "lag_awayScore"))
    last = max(rows, key=lambda p: _as_int(p.get("id")) or 0)
    drives = {str(p.get("drive.id") or p.get("drive_id") or "") for p in rows}
    drives.discard("")

    reached = []
    missing = []
    for marker in OFFICIAL_SCORING:
        hit = False
        for play in rows:
            period = _as_int(play.get("period") or play.get("qtr"))
            home = _as_int(play.get("end.homeScore") if play.get("end.homeScore") is not None else play.get("homeScore"))
            away = _as_int(play.get("end.awayScore") if play.get("end.awayScore") is not None else play.get("awayScore"))
            if period == marker["period"] and home == marker["home"] and away == marker["away"]:
                hit = True
                break
        (reached if hit else missing).append(dict(marker))

    complete = (
        max_period is not None
        and max_period >= 4
        and max_home == OFFICIAL_HOME_SCORE
        and max_away == OFFICIAL_AWAY_SCORE
        and not missing
    )
    return {
        "game_id": str(game_id),
        "n_plays": len(rows),
        "n_drives": len(drives),
        "max_period": max_period,
        "max_home_score": max_home,
        "max_away_score": max_away,
        "last_clock": last.get("clock.displayValue"),
        "last_type": last.get("type.text"),
        "last_end_home": _as_int(last.get("end.homeScore")),
        "last_end_away": _as_int(last.get("end.awayScore")),
        "reached_official_markers": reached,
        "missing_official_markers": missing,
        "complete_through_final": complete,
        "decision": "include" if complete else "exclude",
        "reason": (
            "pbp_complete_through_official_49_7"
            if complete
            else "pbp_partial_vs_official_49_7"
        ),
        "fail_closed": True,
        "standing_rule": "DELAYED + score is not eligibility. Incomplete PBP = exclude.",
    }


def verify_delayed_game(
    *,
    live_summary: Optional[Mapping[str, Any]] = None,
    fetch: bool = True,
    plays: Any = None,
) -> Dict[str, Any]:
    """Return the include/exclude decision plus verification evidence."""
    fetched: Optional[Dict[str, Any]] = None
    fetch_error: Optional[str] = None
    if live_summary is None and fetch:
        try:
            fetched = fetch_espn_summary(DELAYED_GAME_ID)
        except Exception as exc:  # noqa: BLE001 — research evidence, not a crash
            fetch_error = str(exc)[:300]
    elif live_summary is not None:
        fetched = dict(live_summary)

    live_status = (fetched or {}).get("status_name")
    live_completed = bool((fetched or {}).get("status_completed"))
    live_home = ((fetched or {}).get("home") or {}).get("score")
    live_away = ((fetched or {}).get("away") or {}).get("score")
    official_match = (
        live_status == OFFICIAL_STATUS
        and live_completed
        and live_home == OFFICIAL_HOME_SCORE
        and live_away == OFFICIAL_AWAY_SCORE
    )
    snapshot_is_official = (
        SNAPSHOT_STATUS == OFFICIAL_STATUS
        and SNAPSHOT_HOME_SCORE == OFFICIAL_HOME_SCORE
        and SNAPSHOT_AWAY_SCORE == OFFICIAL_AWAY_SCORE
    )

    include_snapshot = False

    decision = {
        "game_id": DELAYED_GAME_ID,
        "teams": {"home": DELAYED_HOME, "away": DELAYED_AWAY},
        "week": DELAYED_WEEK,
        "old_status": SNAPSHOT_STATUS,
        "old_score": {"home": SNAPSHOT_HOME_SCORE, "away": SNAPSHOT_AWAY_SCORE},
        "old_included_in_559": SNAPSHOT_INCLUDED,
        "verification_source": [
            ESPN_SUMMARY_URL.format(game_id=DELAYED_GAME_ID),
            ESPN_BOX_URL.format(game_id=DELAYED_GAME_ID),
            ESPN_RECAP_URL.format(game_id=DELAYED_GAME_ID),
            "Jacksonville State Athletics recap 2026-09-05 (lightning delay; final 49-7)",
        ],
        "official_status": OFFICIAL_STATUS,
        "official_score": {"home": OFFICIAL_HOME_SCORE, "away": OFFICIAL_AWAY_SCORE},
        "official_state": OFFICIAL_STATE,
        "official_completed": OFFICIAL_COMPLETED,
        "live_fetch": fetched,
        "live_fetch_error": fetch_error,
        "live_matches_official": official_match if fetched else None,
        "snapshot_matches_official": snapshot_is_official,
        "decision_on_559_snapshot": "exclude",
        "reason": EXCLUDE_REASON,
        "include_in_regenerated_559_outputs": include_snapshot,
        "include_in_later_as_of_if_pbp_complete_through_49_7": True,
        "standing_eligibility_rule": (
            "DELAYED + score is not a standing include. "
            "Fail-closed: incomplete PBP for a completed game = exclude."
        ),
        "cfbd_used": False,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "refresh_policy": (
            "include only when schedule STATUS_FINAL and PBP is complete "
            "through official 49-7 (period>=4, scores 49-7, all 8 scoring markers)"
        ),
    }
    if plays is not None:
        decision["pbp_audit"] = audit_pbp_vs_official_final(plays)
        if not decision["pbp_audit"]["complete_through_final"]:
            decision["decision_on_559_snapshot"] = "exclude"
            decision["include_in_regenerated_559_outputs"] = False
    return decision


def snapshot_scores_match_official(home_score: Any, away_score: Any) -> bool:
    return _as_int(home_score) == OFFICIAL_HOME_SCORE and _as_int(away_score) == OFFICIAL_AWAY_SCORE


def should_exclude_snapshot_game(
    game_id: Any,
    *,
    status: Any = None,
    home_score: Any = None,
    away_score: Any = None,
    pbp_complete: Optional[bool] = None,
) -> bool:
    """Fail-closed for 401868140. DELAYED+score is never enough.

    Keep only when PBP is complete through official 49–7 *and* status is FINAL.
    Unknown / incomplete PBP → exclude.
    """
    gid = _norm_gid(game_id)
    if gid != DELAYED_GAME_ID:
        return False
    token = str(status or "").strip().upper().replace(" ", "_")
    status_final = token in {
        "STATUS_FINAL",
        "FINAL",
        "STATUS_COMPLETED",
        "STATUS_FULL_TIME",
    }
    if pbp_complete is True and status_final and snapshot_scores_match_official(
        home_score, away_score
    ):
        return False
    return True
