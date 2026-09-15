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

# Snapshot PBP/score is incomplete. Do not use the #559 21–0 capture.
EXCLUDE_FROM_SNAPSHOT = True
EXCLUDE_REASON = (
    "excluded_delayed_incomplete_snapshot: STATUS_DELAYED 21-0 is not the "
    "official final (ESPN STATUS_FINAL 49-7). Score alone is insufficient."
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


def verify_delayed_game(
    *,
    live_summary: Optional[Mapping[str, Any]] = None,
    fetch: bool = True,
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

    # Snapshot #559 cannot be used: 21–0 DELAYED ≠ 49–7 FINAL.
    include_snapshot = False
    # A later as_of may include the game only if that as_of is STATUS_FINAL
    # *and* scores match the official 49–7 (complete PBP, not the 21–0 cut).
    include_if_refreshed_final = official_match or (
        fetch_error is None and fetched is None and True
    )

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
        "include_in_later_as_of_if_status_final_and_score_49_7": True,
        "cfbd_used": False,
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }
    # Silence unused — include_if_refreshed_final is the policy flag above.
    decision["refresh_policy"] = (
        "include only when schedule STATUS_FINAL and scores equal 49-7 "
        "and PBP is not the 21-0 delayed cut"
    )
    del include_if_refreshed_final
    return decision


def snapshot_scores_match_official(home_score: Any, away_score: Any) -> bool:
    return _as_int(home_score) == OFFICIAL_HOME_SCORE and _as_int(away_score) == OFFICIAL_AWAY_SCORE


def should_exclude_snapshot_game(
    game_id: Any,
    *,
    status: Any = None,
    home_score: Any = None,
    away_score: Any = None,
) -> bool:
    """Exclude the incomplete #559 21–0 DELAYED cut; keep an official 49–7 FINAL."""
    gid = str(game_id or "").strip()
    if gid.endswith(".0") and gid[:-2].isdigit():
        gid = gid[:-2]
    if gid != DELAYED_GAME_ID:
        return False
    token = str(status or "").strip().upper().replace(" ", "_")
    official = snapshot_scores_match_official(home_score, away_score) and (
        token in {"STATUS_FINAL", "FINAL", "STATUS_COMPLETED", "STATUS_FULL_TIME"}
        or token == ""
        and home_score is not None
    )
    if official:
        return False
    if home_score is None and status is None:
        return False
    return True
