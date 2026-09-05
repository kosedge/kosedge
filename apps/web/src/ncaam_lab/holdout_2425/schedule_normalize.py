"""Schedule SoT normalization (season-parameterized; no hardcoded holdout dates)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

FINAL_STATUSES = frozenset({"final", "status_final", "post"})


def is_final_status(status: Optional[str]) -> bool:
    return str(status or "").strip().lower() in FINAL_STATUSES


def _home_score(game: Dict[str, Any]) -> Any:
    v = game.get("home_score")
    if v is None:
        v = game.get("home_score")
    return v


def _away_score(game: Dict[str, Any]) -> Any:
    v = game.get("away_score")
    if v is None:
        v = game.get("away_score")
    return v


def outcome_label_ok(game: Dict[str, Any]) -> bool:
    """Final scores present; never coerce missing → 0."""
    if not is_final_status(game.get("status")):
        return False
    hs, aws = _home_score(game), _away_score(game)
    return hs is not None and aws is not None


def detect_duplicate_event_ids(games: List[Dict[str, Any]]) -> List[str]:
    seen: Dict[str, int] = {}
    for g in games:
        eid = str(g.get("espn_game_id") or g.get("game_id") or "")
        if not eid:
            continue
        seen[eid] = seen.get(eid, 0) + 1
    return sorted(eid for eid, n in seen.items() if n > 1)


def detect_participant_reversals(games: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    by_pair: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}
    for g in games:
        tip = str(g.get("date") or "")[:10]
        home = str(g.get("home") or "")
        away = str(g.get("away") or "")
        if not tip or not home or not away:
            continue
        key = (tip, *sorted((home, away)))
        by_pair.setdefault(key, []).append(g)
    out: List[Dict[str, str]] = []
    for _key, rows in by_pair.items():
        if len(rows) < 2:
            continue
        if len({str(r.get("home")) for r in rows}) > 1:
            out.append(
                {
                    "tip": str(rows[0].get("date") or ""),
                    "event_ids": ",".join(str(r.get("espn_game_id") or "") for r in rows),
                    "reason": "participant_reversal_or_duplicate_pair",
                }
            )
    return out


def quarantine_nonfinal(
    games: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    kept: List[Dict[str, Any]] = []
    quarantined: List[Dict[str, Any]] = []
    for g in games:
        if outcome_label_ok(g):
            kept.append(g)
        else:
            quarantined.append(
                {
                    "espn_game_id": g.get("espn_game_id"),
                    "date": g.get("date"),
                    "status": g.get("status"),
                    "home_score_present": _home_score(g) is not None,
                    "away_score_present": _away_score(g) is not None,
                    "reason": "nonfinal_or_missing_scores",
                }
            )
    return kept, quarantined
