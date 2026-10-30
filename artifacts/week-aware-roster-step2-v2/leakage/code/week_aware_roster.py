"""Week-aware roster reconstruction (Step 2 v2 leakage package).

Implements SPEC.md / IMV SPEC 8eb532c1 for synthetic + coverage use.
Not a production SoT pin. Does not read 2024/25 holdout packs.
Does not invent weekly coverage. Does not refit.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Optional

CLOSED_AT_CUTOFF = False
ACT_53 = frozenset({"ACT"})
NOT_53 = frozenset({"DEV", "CUT"})

MISSING_OK = "OK"
MISSING_ROW = "MISSING_ROW"
MISSING_TS = "MISSING_TS"
INELIGIBLE_PLAYOFF = "INELIGIBLE_PLAYOFF_FOR_REG"
TS_AFTER = "TS_AFTER_CUTOFF"
TS_EQUAL = "TS_EQUAL_CUTOFF"


def parse_ts(value: Any) -> Optional[datetime]:
    """Return an aware datetime, or None if missing/unusable.

    Naive timestamps are refused (MISSING_TS). Ingest/updated_at is never
    accepted as a substitute — callers must pass availability_ts / report_time.
    """
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else None
    text = str(value).strip()
    if not text or text.lower() == "null":
        return None
    try:
        ts = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if ts.tzinfo is None:
        return None
    return ts


def prediction_cutoff(game: dict) -> datetime:
    kickoff = parse_ts(game.get("kickoff_utc"))
    if kickoff is None:
        raise ValueError("game.kickoff_utc missing or naive")
    decision = parse_ts(game.get("decision_ts")) if game.get("decision_ts") else None
    cutoff = min(kickoff, decision) if decision is not None else kickoff
    if cutoff > kickoff:
        raise ValueError("prediction_cutoff after kickoff")
    return cutoff


def classify_row(row: dict, game: dict, cutoff: Optional[datetime] = None) -> tuple[bool, str]:
    """G-PIT classify one membership/depth row against a REG (or other) game."""
    if cutoff is None:
        cutoff = prediction_cutoff(game)
    if row.get("season") != game.get("season"):
        return False, MISSING_ROW
    row_gt = row.get("game_type") or "REG"
    game_gt = game.get("game_type") or "REG"
    if game_gt == "REG" and row_gt != "REG":
        return False, INELIGIBLE_PLAYOFF
    if int(row.get("week", 99)) > int(game.get("week", 0)):
        return False, MISSING_ROW
    ts = parse_ts(row.get("availability_ts"))
    if ts is None:
        return False, MISSING_TS
    if ts > cutoff:
        return False, TS_AFTER
    if ts == cutoff:
        if CLOSED_AT_CUTOFF:
            return True, MISSING_OK
        return False, TS_EQUAL
    return True, MISSING_OK


def _latest_eligible(rows: Iterable[dict], game: dict, player_id: str) -> tuple[Optional[dict], str]:
    cutoff = prediction_cutoff(game)
    eligible: list[dict] = []
    saw_missing_ts = False
    for row in rows:
        if row.get("player_id") != player_id:
            continue
        ok, code = classify_row(row, game, cutoff)
        if code == MISSING_TS and int(row.get("week", 99)) <= int(game.get("week", 0)):
            if row.get("season") == game.get("season"):
                saw_missing_ts = True
        if ok:
            eligible.append(row)
    if not eligible:
        return None, MISSING_TS if saw_missing_ts else MISSING_ROW
    eligible.sort(key=lambda r: (int(r["week"]), parse_ts(r["availability_ts"])))
    return eligible[-1], MISSING_OK


def _eligible_transactions(transactions: Iterable[dict], player_id: str, cutoff: datetime) -> list[dict]:
    out: list[dict] = []
    for txn in transactions:
        if txn.get("player_id") != player_id:
            continue
        ts = parse_ts(txn.get("availability_ts"))
        if ts is None:
            continue
        if ts < cutoff:
            out.append(txn)
    out.sort(key=lambda t: parse_ts(t["availability_ts"]) or datetime.min)
    return out


def assignment(
    player_id: str,
    game: dict,
    roster_rows: Iterable[dict],
    transactions: Optional[Iterable[dict]] = None,
) -> dict:
    """Week-aware team/status for one player at one game. Look-back + txn as-of."""
    cutoff = prediction_cutoff(game)
    latest, miss = _latest_eligible(roster_rows, game, player_id)
    if miss == MISSING_TS:
        return {
            "player_id": player_id,
            "team": None,
            "status": None,
            "promoted_role": False,
            "missingness": MISSING_TS,
        }
    team = latest.get("team") if latest else None
    status = latest.get("status") if latest else None
    promoted = False
    for txn in _eligible_transactions(transactions or [], player_id, cutoff):
        etype = txn.get("event_type")
        if etype == "trade":
            team = txn.get("to_team")
        elif etype == "PS_up":
            status = "ACT"
            promoted = True
    if team is None:
        return {
            "player_id": player_id,
            "team": None,
            "status": None,
            "promoted_role": False,
            "missingness": MISSING_ROW,
        }
    member_53 = status in ACT_53
    missingness = MISSING_OK if member_53 else MISSING_ROW
    return {
        "player_id": player_id,
        "team": team,
        "status": status,
        "promoted_role": promoted,
        "member_53": member_53,
        "missingness": missingness,
    }


def has_eligible_membership_row(player_id: str, game: dict, roster_rows: Iterable[dict]) -> bool:
    latest, miss = _latest_eligible(roster_rows, game, player_id)
    return miss == MISSING_OK and latest is not None


def roster_status_applied(player_id: str, game: dict, roster_rows: Iterable[dict]) -> bool:
    """True iff an *eligible* roster row's status is used for this game.

    Look-ahead-only snapshots (T-PIT-5 week-17 RES vs week-1 game) → False.
    Mutating that row to an eligible week-1 RES with ts < cutoff → True.
    """
    latest, miss = _latest_eligible(roster_rows, game, player_id)
    return miss == MISSING_OK and latest is not None and bool(latest.get("status"))


def imputed_from_season(
    player_id: str,
    game: dict,
    roster_rows: Iterable[dict],
    mem: dict,
) -> bool:
    """True if membership/assignment used a non-G-PIT-eligible row."""
    _latest, miss = _latest_eligible(roster_rows, game, player_id)
    if mem.get("member") and miss != MISSING_OK:
        return True
    asg = mem.get("assignment") or {}
    if asg.get("team") and miss != MISSING_OK:
        return True
    return False


def silent_include_flag(member: bool, has_eligible_row: bool) -> bool:
    """True if the player is treated as a member with no eligible row."""
    return bool(member) and not has_eligible_row


def is_member(
    player_id: str,
    team: str,
    game: dict,
    roster_rows: Iterable[dict],
    transactions: Optional[Iterable[dict]] = None,
) -> dict:
    asg = assignment(player_id, game, roster_rows, transactions)
    eligible = has_eligible_membership_row(player_id, game, roster_rows)
    if asg["missingness"] == MISSING_TS:
        member = False
        miss = MISSING_TS
    elif asg.get("team") == team and asg.get("status") in ACT_53:
        member = True
        miss = MISSING_OK
    else:
        member = False
        miss = asg["missingness"] if asg["missingness"] != MISSING_OK else MISSING_ROW
    return {
        "member": member,
        "missingness": miss,
        "silent_include": silent_include_flag(member, eligible),
        "assignment": asg,
    }


def depth_order_for(
    player_id: str,
    game: dict,
    depth_rows: Iterable[dict],
) -> Optional[int]:
    cutoff = prediction_cutoff(game)
    eligible = []
    for row in depth_rows:
        if row.get("player_id") != player_id:
            continue
        ok, _code = classify_row(row, game, cutoff)
        if ok:
            eligible.append(row)
    if not eligible:
        return None
    eligible.sort(key=lambda r: (int(r["week"]), parse_ts(r["availability_ts"])))
    return int(eligible[-1]["depth_order"])


def defaulted_depth_2(player_id: str, game: dict, depth_rows: Iterable[dict]) -> bool:
    """True only if depth_order==2 was returned with no eligible depth row."""
    cutoff = prediction_cutoff(game)
    any_eligible = False
    for row in depth_rows:
        if row.get("player_id") != player_id:
            continue
        ok, _code = classify_row(row, game, cutoff)
        if ok:
            any_eligible = True
            break
    depth = depth_order_for(player_id, game, depth_rows)
    return depth == 2 and not any_eligible


def qb1_id(game: dict, depth_rows: Iterable[dict]) -> Optional[str]:
    """Single eligible QB with depth_order==1. Multiple QB-slot rows are not all QB1."""
    cutoff = prediction_cutoff(game)
    ones: list[dict] = []
    for row in depth_rows:
        if row.get("position") != "QB":
            continue
        ok, _code = classify_row(row, game, cutoff)
        if ok and int(row.get("depth_order", 99)) == 1:
            ones.append(row)
    if len(ones) != 1:
        return None
    return ones[0].get("player_id")


def listing_status(player_id: str, game: dict, listings: Iterable[dict]) -> dict:
    """Injury listings only; report_time < kickoff. Roster RES/INA must not leak."""
    kickoff = parse_ts(game.get("kickoff_utc"))
    if kickoff is None:
        return {"status": None, "listing_as_of_ok": False}
    eligible = []
    for row in listings:
        if row.get("player_id") != player_id:
            continue
        rt = parse_ts(row.get("report_time"))
        if rt is None or rt >= kickoff:
            continue
        eligible.append(row)
    if not eligible:
        return {"status": None, "listing_as_of_ok": False}
    eligible.sort(key=lambda r: parse_ts(r["report_time"]))
    latest = eligible[-1]
    return {"status": latest.get("report_status"), "listing_as_of_ok": True}


def x_continuity(current_ids: Optional[Iterable[str]], prior_ids: Optional[Iterable[str]]) -> Optional[float]:
    """Current side must be week-aware. Missing book → None (E-1). Never 0-fill."""
    if current_ids is None or prior_ids is None:
        return None
    cur = set(current_ids)
    pri = set(prior_ids)
    if not cur or not pri:
        return None
    return len(cur & pri) / len(cur | pri)


def season_union_would_mark_res(player_id: str, roster_rows: Iterable[dict]) -> bool:
    return any(r.get("player_id") == player_id and r.get("status") == "RES" for r in roster_rows)
