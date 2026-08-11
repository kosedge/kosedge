#!/usr/bin/env python3
"""Edge Board Week 1 complete-slate guardrail (no silent drops).

Fails when the canonical 2026 REG Week 1 schedule pack count is not 16, or
when an optional board snapshot is missing any schedule game_id.

Usage:
  python scripts/nfl/check_edge_board_week1.py
  python scripts/nfl/check_edge_board_week1.py --board /tmp/week1-rows.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

ROOT = Path(__file__).resolve().parents[2]
SCHEDULE_PACK = (
    ROOT
    / "services"
    / "model-service"
    / "src"
    / "services"
    / "nfl_season_engine"
    / "data"
    / "nfl_regular_schedule_2026.json"
)
WALL_CHART = ROOT / "apps" / "web" / "lib" / "nfl-wall-chart-2026.schedule.json"

WEEK1_EXPECTED = 16


def _canon(team: str) -> str:
    t = str(team or "").strip().upper()
    if t == "LA":
        return "LAR"
    if t == "WSH":
        return "WAS"
    if t == "JAC":
        return "JAX"
    return t


def _pack_abbr(team: str) -> str:
    c = _canon(team)
    return "LA" if c == "LAR" else c


def load_week1_from_pack() -> List[Dict[str, Any]]:
    raw = json.loads(SCHEDULE_PACK.read_text(encoding="utf-8"))
    games = [
        g
        for g in raw.get("games") or []
        if int(g.get("week") or 0) == 1
    ]
    out: List[Dict[str, Any]] = []
    for g in games:
        away = _canon(g.get("away_team"))
        home = _canon(g.get("home_team"))
        gid = str(
            g.get("game_id")
            or f"2026-W01-{_pack_abbr(away)}@{_pack_abbr(home)}"
        )
        out.append(
            {
                "game_id": gid,
                "away": away,
                "home": home,
                "week": 1,
                "season_type": "REG",
                "kickoff": g.get("kickoff") or g.get("start_time") or g.get("game_date"),
            }
        )
    return sorted(out, key=lambda r: r["game_id"])


def load_week1_from_wall_chart() -> List[Dict[str, Any]]:
    chart = json.loads(WALL_CHART.read_text(encoding="utf-8"))
    games: List[Dict[str, Any]] = []
    for team, weeks in chart.items():
        label = (weeks or {}).get("1") or (weeks or {}).get(1)
        if not label:
            continue
        text = str(label).strip()
        if not text.lower().startswith("vs"):
            continue
        opp = text.split(None, 1)[1].strip() if " " in text else ""
        home = _canon(team)
        away = _canon(opp)
        games.append(
            {
                "game_id": f"2026-W01-{_pack_abbr(away)}@{_pack_abbr(home)}",
                "away": away,
                "home": home,
                "week": 1,
                "season_type": "REG",
                "kickoff": None,
            }
        )
    return sorted(games, key=lambda r: r["game_id"])


def _row_pair(row: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    away = row.get("awayAbbr") or row.get("away_abbr") or row.get("away")
    home = row.get("homeAbbr") or row.get("home_abbr") or row.get("home")
    if away and home:
        return _canon(str(away)), _canon(str(home))
    game = str(row.get("game") or "")
    if " @ " in game:
        a, h = game.split(" @ ", 1)
        # Allow abbr-only game labels used in unit fixtures.
        if len(a.strip()) <= 3 and len(h.strip()) <= 3:
            return _canon(a), _canon(h)
    return None


def board_pairs(rows: Iterable[Dict[str, Any]]) -> Set[Tuple[str, str]]:
    out: Set[Tuple[str, str]] = set()
    for row in rows:
        pair = _row_pair(row)
        if pair:
            out.add(pair)
    return out


def check_week1(
    *,
    board_rows: Optional[Sequence[Dict[str, Any]]] = None,
) -> List[Tuple[str, bool, str]]:
    results: List[Tuple[str, bool, str]] = []
    pack = load_week1_from_pack()
    wall = load_week1_from_wall_chart()

    pack_ok = len(pack) == WEEK1_EXPECTED
    results.append(
        (
            "WEEK1_SCHEDULE_PACK_COUNT",
            pack_ok,
            f"pack_week1={len(pack)} expected={WEEK1_EXPECTED}",
        )
    )

    wall_ok = len(wall) == WEEK1_EXPECTED
    results.append(
        (
            "WEEK1_WALL_CHART_COUNT",
            wall_ok,
            f"wall_chart_week1={len(wall)} expected={WEEK1_EXPECTED}",
        )
    )

    pack_keys = {(_canon(g["away"]), _canon(g["home"])) for g in pack}
    wall_keys = {(_canon(g["away"]), _canon(g["home"])) for g in wall}
    sync_ok = pack_keys == wall_keys
    results.append(
        (
            "WEEK1_PACK_WALL_SYNC",
            sync_ok,
            f"pack_only={sorted(pack_keys - wall_keys)} wall_only={sorted(wall_keys - pack_keys)}",
        )
    )

    if board_rows is not None:
        present = board_pairs(board_rows)
        missing = sorted(
            g["game_id"]
            for g in pack
            if (_canon(g["away"]), _canon(g["home"])) not in present
        )
        board_ok = not missing and len(present) >= WEEK1_EXPECTED
        if missing:
            print("MISSING_ON_BOARD:", ", ".join(missing), file=sys.stderr)
        results.append(
            (
                "WEEK1_BOARD_COMPLETE",
                board_ok,
                f"board_pairs={len(present)} missing={missing}",
            )
        )

    return results


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--board",
        default=None,
        help="Optional Edge Board rows JSON (array or {rows:[...]})",
    )
    args = ap.parse_args(argv)

    board_rows = None
    if args.board:
        payload = json.loads(Path(args.board).read_text(encoding="utf-8"))
        if isinstance(payload, list):
            board_rows = payload
        elif isinstance(payload, dict):
            board_rows = payload.get("rows") or payload.get("games") or []
        else:
            print("FAIL: board JSON must be list or object with rows", file=sys.stderr)
            return 2

    results = check_week1(board_rows=board_rows)
    ok = True
    for check_id, passed, detail in results:
        flag = "PASS" if passed else "FAIL"
        print(f"{flag} {check_id}: {detail}")
        ok = ok and passed

    # Always print the 16-game ground truth for ops.
    print("\nREG Week 1 schedule pack:")
    for g in load_week1_from_pack():
        print(
            f"  {g['game_id']}  {g['away']}@{g['home']}  week={g['week']}  "
            f"season_type={g['season_type']}  kickoff={g['kickoff']}"
        )

    if not ok:
        print(
            "\nEdge Board Week 1 complete-slate check FAILED — "
            "board count must equal schedule pack (no silent drops).",
            file=sys.stderr,
        )
        return 1
    print("\nEdge Board Week 1 complete-slate check OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
