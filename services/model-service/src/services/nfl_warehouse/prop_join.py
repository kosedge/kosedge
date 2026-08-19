"""Join Odds API player-prop closes to nflverse-style usage names.

Kickoff-safe: a close is only legal when snapshot_ts is strictly before kickoff.
Name key is first-initial + last token (A.St.Brown for St. Brown).
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Tuple

from src.services.cfb_warehouse.leakage import is_available_before_kickoff
from src.services.nfl_warehouse.odds_lake import _as_season
from src.services.nfl_warehouse.paths import HD_PROPS

_SUFFIX = frozenset({"jr", "sr", "ii", "iii", "iv", "v"})
PROP_MARKET_MAP = {
    "player_pass_yds": "pass_yds",
    "player_rush_yds": "rush_yds",
    "player_reception_yds": "rec_yds",
    "player_receptions": "receptions",
    "player_anytime_td": "anytime_td",
}
CLOSE_KINDS = frozenset({"close", "close_props"})


def normalize_player_key(name: str) -> str:
    raw = (name or "").split("|", 1)[0]
    tokens = [t for t in re.findall(r"[a-z0-9]+", raw.casefold()) if t not in _SUFFIX]
    if not tokens:
        return ""
    if len(tokens[0]) == 1:
        if len(tokens) >= 3 and tokens[1] == "st":
            return f"{tokens[0]}.st.{tokens[-1]}"
        return f"{tokens[0]}.{tokens[-1]}"
    if len(tokens) >= 3 and tokens[-2] == "st":
        return f"{tokens[0][0]}.st.{tokens[-1]}"
    return f"{tokens[0][0]}.{tokens[-1]}"


def split_outcome(outcome: str) -> Tuple[str, str]:
    text = str(outcome or "")
    if "|" in text:
        name, side = text.split("|", 1)
        return name.strip(), side.strip()
    return text.strip(), ""


def props_csv_path() -> Path:
    return HD_PROPS / "lines.csv"


def iter_prop_closes(
    csv_path: Optional[Path] = None,
    *,
    markets: Optional[Sequence[str]] = None,
) -> Iterator[Dict[str, Any]]:
    path = csv_path or props_csv_path()
    wanted = set(markets) if markets else set(PROP_MARKET_MAP)
    if not path.is_file():
        return
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if str(row.get("snapshot_kind") or "") not in CLOSE_KINDS:
                continue
            raw_mkt = str(row.get("market") or "")
            if raw_mkt not in wanted:
                continue
            name, side = split_outcome(str(row.get("outcome") or ""))
            if side and side.casefold() not in {"over", ""}:
                continue
            kickoff = row.get("commence_time")
            captured = row.get("snapshot_ts")
            if not is_available_before_kickoff(
                available_at=captured, kickoff=kickoff, game_date=str(kickoff or "")[:10]
            ):
                continue
            try:
                line = float(row.get("point"))
            except (TypeError, ValueError):
                continue
            yield {
                "event_id": row.get("event_id"),
                "kickoff": kickoff,
                "game_date": str(kickoff or "")[:10],
                "season": _as_season(kickoff),
                "home": row.get("home_team"),
                "away": row.get("away_team"),
                "book": str(row.get("book") or "").lower(),
                "market": PROP_MARKET_MAP.get(raw_mkt, raw_mkt),
                "player": name,
                "player_key": normalize_player_key(name),
                "line": line,
                "price": row.get("price"),
                "captured_at": captured,
            }


def pick_close_by_player(
    rows: Iterable[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """One close per (event, player, market); prefer DK then FD, latest legal ts."""
    ranked: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
    book_rank = {"draftkings": 0, "fanduel": 1}
    for row in rows:
        key = (row.get("event_id"), row.get("player_key"), row.get("market"))
        if not key[1]:
            continue
        prev = ranked.get(key)
        if prev is None:
            ranked[key] = dict(row)
            continue
        pr = book_rank.get(str(prev.get("book") or ""), 9)
        cr = book_rank.get(str(row.get("book") or ""), 9)
        if cr < pr or (cr == pr and str(row.get("captured_at") or "") > str(prev.get("captured_at") or "")):
            ranked[key] = dict(row)
    return list(ranked.values())
