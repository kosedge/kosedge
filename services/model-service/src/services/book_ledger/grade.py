"""Grade The Book rows from official final scores + close line.

No lookahead: only settle when ESPN says final/completed.
In-progress and pre-kick rows stay pending.
late_post rows may settle after final but CLV is tagged after_open (not pre-kick).
Settled rows remain immutable via BookStore.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence

import requests

from src.services.book_ledger.cfb_snapshot import (
    ESPN_SCOREBOARD,
    ESPN_SUMMARY,
    _extract_espn_odds,
    fetch_espn_summary_market,
)
from src.services.book_ledger.store import BookStore, get_store

log = logging.getLogger("kosedge.book_ledger.grade")

_FINAL_STATES = frozenset({"post"})
_FINAL_NAMES = frozenset(
    {
        "STATUS_FINAL",
        "STATUS_FULL_TIME",
        "STATUS_FULLTIME",
        "FINAL",
        "STATUS_COMPLETED",
    }
)
_VOID_NAMES = frozenset(
    {
        "STATUS_CANCELED",
        "STATUS_CANCELLED",
        "STATUS_POSTPONED",
        "STATUS_FORFEIT",
    }
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _f(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def is_final_status(*, state: Optional[str], name: Optional[str], completed: Any = None) -> bool:
    if completed is True:
        return True
    st = str(state or "").strip().lower()
    nm = str(name or "").strip().upper()
    if st in _FINAL_STATES:
        return True
    if nm in _FINAL_NAMES or nm.endswith("_FINAL"):
        return True
    return False


def is_void_status(*, name: Optional[str]) -> bool:
    nm = str(name or "").strip().upper()
    return nm in _VOID_NAMES


def is_in_progress(*, state: Optional[str], name: Optional[str]) -> bool:
    st = str(state or "").strip().lower()
    if st == "in":
        return True
    nm = str(name or "").strip().upper()
    return "IN_PROGRESS" in nm or nm in {"STATUS_HALFTIME", "STATUS_END_PERIOD"}


def grade_spread_result(
    *,
    side: str,
    line: Optional[float],
    home_score: float,
    away_score: float,
) -> str:
    """Official ATS vs the posted side line. push on exact cover."""
    if line is None:
        raise ValueError("spread line required to grade")
    margin = float(home_score) - float(away_score)
    side_tok = str(side).strip().lower()
    if side_tok == "home":
        # Home covers if margin + home_line > 0
        cover = margin + float(line)
    elif side_tok == "away":
        # Away line is away spread (e.g. +38.5). Cover if -margin + away_line > 0
        cover = (-margin) + float(line)
    else:
        raise ValueError(f"unsupported spread side: {side!r}")
    if abs(cover) < 1e-9:
        return "push"
    return "win" if cover > 0 else "loss"


def close_line_for_side(*, side: str, spread_home: Optional[float]) -> Optional[float]:
    if spread_home is None:
        return None
    side_tok = str(side).strip().lower()
    if side_tok == "home":
        return float(spread_home)
    if side_tok == "away":
        return -float(spread_home)
    return float(spread_home)


def fetch_espn_game_results(slate_date: str) -> Dict[str, Dict[str, Any]]:
    """Map ESPN event id → scores, status, close-ish market snapshot."""
    ymd = slate_date.replace("-", "")
    url = f"{ESPN_SCOREBOARD}?dates={ymd}&limit=100"
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    out: Dict[str, Dict[str, Any]] = {}
    for ev in resp.json().get("events") or []:
        gid = str(ev.get("id") or "")
        comp = (ev.get("competitions") or [{}])[0]
        status = (comp.get("status") or {}).get("type") or {}
        teams = comp.get("competitors") or []
        home = next((t for t in teams if t.get("homeAway") == "home"), {})
        away = next((t for t in teams if t.get("homeAway") == "away"), {})
        market = _extract_espn_odds(comp.get("odds") or [])
        if market.get("spread_home") is None:
            market = fetch_espn_summary_market(gid) or market
        out[gid] = {
            "game_id": gid,
            "home_score": _f(home.get("score")),
            "away_score": _f(away.get("score")),
            "state": status.get("state"),
            "status_name": status.get("name"),
            "completed": bool(status.get("completed")),
            "spread_home": market.get("spread_home"),
            "total": market.get("total"),
            "market_source": market.get("source") or "espn_scoreboard",
            "provider": market.get("provider"),
        }
    return out


def close_and_grade_row(
    store: BookStore,
    row: Mapping[str, Any],
    game: Mapping[str, Any],
    *,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Apply close+grade for one pending row. Skips non-finals."""
    book_id = str(row.get("book_id"))
    status_name = game.get("status_name")
    state = game.get("state")

    base = {
        "book_id": book_id,
        "game_id": row.get("game_id"),
        "away": row.get("away"),
        "home": row.get("home"),
        "type": row.get("type"),
        "late_post": bool(row.get("late_post")),
        "post_timing": row.get("post_timing"),
        "espn_state": state,
        "espn_status": status_name,
    }

    if str(row.get("result", "pending")).lower() != "pending":
        return {**base, "action": "skip", "reason": "already_settled"}

    if is_void_status(name=status_name):
        if dry_run:
            return {**base, "action": "void", "reason": "void_status", "dry_run": True}
        store.settle(book_id, result="void", pnl_units=0.0)
        return {**base, "action": "void", "reason": "void_status"}

    if is_in_progress(state=state, name=status_name):
        return {**base, "action": "skip", "reason": "in_progress"}

    if not is_final_status(state=state, name=status_name, completed=game.get("completed")):
        return {**base, "action": "skip", "reason": "not_final"}

    home_score = _f(game.get("home_score"))
    away_score = _f(game.get("away_score"))
    if home_score is None or away_score is None:
        return {**base, "action": "skip", "reason": "missing_scores"}

    market = str(row.get("market") or "spread").lower()
    if market != "spread":
        return {**base, "action": "skip", "reason": f"market_{market}_not_implemented"}

    close_line = close_line_for_side(side=str(row.get("side")), spread_home=_f(game.get("spread_home")))
    close_at = _utc_now()
    late = bool(row.get("late_post")) or str(row.get("post_timing") or "") == "after_open"

    result = grade_spread_result(
        side=str(row.get("side")),
        line=_f(row.get("line")),
        home_score=home_score,
        away_score=away_score,
    )

    detail = {
        **base,
        "action": "settle",
        "home_score": home_score,
        "away_score": away_score,
        "posted_line": row.get("line"),
        "close_line": close_line,
        "result": result,
        "clv_note": "after_open_late_post" if late else "pre_kick_post",
        "close_source": game.get("market_source"),
    }

    if dry_run:
        detail["dry_run"] = True
        return detail

    store.record_close(
        book_id,
        close_line=close_line,
        close_price=None,
        close_at=close_at,
    )
    store.annotate_pending(
        book_id,
        info_overlap=("late_post_clv" if late else existing_info(row)),
        payload={
            "clv_note": detail["clv_note"],
            "official_home_score": home_score,
            "official_away_score": away_score,
            "close_source": game.get("market_source"),
        },
    )
    store.settle(book_id, result=result)
    fresh = store.get(book_id) or {}
    detail["clv"] = fresh.get("clv")
    detail["pnl_units"] = fresh.get("pnl_units")
    return detail


def existing_info(row: Mapping[str, Any]) -> Optional[str]:
    v = row.get("info_overlap")
    return str(v) if v is not None else None


def close_and_grade_slate(
    *,
    sport: str = "cfb",
    week_or_slate: str,
    extra_dates: Optional[Sequence[str]] = None,
    store: Optional[BookStore] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    store = store or get_store()
    rows = store.list_rows(sport=sport, week_or_slate=week_or_slate, result="pending")
    dates = [week_or_slate] + list(extra_dates or [])
    games: Dict[str, Dict[str, Any]] = {}
    for d in dates:
        try:
            games.update(fetch_espn_game_results(d))
        except Exception as exc:  # noqa: BLE001
            log.warning("espn results fetch failed date=%s err=%s", d, exc)

    actions: List[Dict[str, Any]] = []
    for row in rows:
        gid = str(row.get("game_id"))
        game = games.get(gid)
        if not game:
            actions.append(
                {
                    "book_id": row.get("book_id"),
                    "game_id": gid,
                    "action": "skip",
                    "reason": "no_espn_game",
                    "late_post": bool(row.get("late_post")),
                }
            )
            continue
        actions.append(close_and_grade_row(store, row, game, dry_run=dry_run))

    summary = {
        "ok": True,
        "sport": sport,
        "week_or_slate": week_or_slate,
        "dry_run": dry_run,
        "n_pending_in": len(rows),
        "n_settled": sum(1 for a in actions if a.get("action") == "settle"),
        "n_void": sum(1 for a in actions if a.get("action") == "void"),
        "n_skipped": sum(1 for a in actions if a.get("action") == "skip"),
        "actions": actions,
        "note": "No lookahead. In-progress skipped. late_post CLV tagged after_open.",
    }
    return summary
