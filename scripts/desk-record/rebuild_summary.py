#!/usr/bin/env python3
"""Rebuild desk-record season summary from ledger.jsonl (fail-closed).

Does not invent juice, lines, or results. ROI only from stamped American juice.
Pushes: profit 0; stake excluded from risked denominator.

Usage:
  python3 scripts/desk-record/rebuild_summary.py --sport cfb --season 2026
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def american_profit(stake: float, juice: int, won: bool) -> float:
    if not won:
        return -float(stake)
    if juice < 0:
        return float(stake) * (100.0 / abs(juice))
    return float(stake) * (juice / 100.0)


def load_ledger(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def ats_triple(results: list[str]) -> dict[str, int]:
    c = Counter(results)
    return {"w": c.get("W", 0), "l": c.get("L", 0), "p": c.get("P", 0)}


def format_ats(t: dict[str, int]) -> str:
    return f"{t['w']}-{t['l']}-{t['p']}"


def rebuild(sport: str, season: int) -> dict[str, Any]:
    ledger_path = ROOT / "data" / "desk-record" / sport / str(season) / "ledger.jsonl"
    tickets = load_ledger(ledger_path)

    play_settled = [
        t for t in tickets if t.get("grade") == "PLAY" and t.get("result") in ("W", "L", "P")
    ]
    lean_settled = [
        t for t in tickets if t.get("grade") == "LEAN" and t.get("result") in ("W", "L", "P")
    ]
    open_tickets = [t for t in tickets if t.get("result") == "OPEN"]

    play_ats = ats_triple([t["result"] for t in play_settled])
    lean_ats = ats_triple([t["result"] for t in lean_settled])
    combined_ats = ats_triple(
        [t["result"] for t in play_settled + lean_settled]
    )

    profit_sum = 0.0
    risked = 0.0
    roi_tickets = 0
    data_gap_roi = 0
    stamped_juice = 0

    for t in play_settled + lean_settled:
        result = t.get("result")
        stake = float(t.get("stake_u") or 0)
        juice = t.get("juice")
        juice_status = t.get("juice_status") or (
            "DATA_GAP" if juice is None else "stamped"
        )

        if result == "P":
            # Push: profit 0; exclude stake from risked.
            if t.get("profit_u") is None:
                t["profit_u"] = 0.0
            continue

        if juice is None or juice_status == "DATA_GAP":
            data_gap_roi += 1
            continue

        stamped_juice += 1
        j = int(juice)
        if not isinstance(juice, (int, float)) or abs(j) < 100:
            data_gap_roi += 1
            continue

        won = result == "W"
        profit = american_profit(stake, j, won)
        # Prefer ledger profit_u when present and finite; else compute.
        ledger_profit = t.get("profit_u")
        if isinstance(ledger_profit, (int, float)):
            profit = float(ledger_profit)
        profit_sum += profit
        risked += stake
        roi_tickets += 1

    roi: dict[str, Any]
    if risked > 0:
        roi = {
            "status": "ok",
            "profit_u": round(profit_sum, 6),
            "risked_u": round(risked, 6),
            "roi": round(profit_sum / risked, 6),
            "n_tickets": roi_tickets,
            "n_data_gap": data_gap_roi,
            "n_stamped_juice": stamped_juice,
        }
    elif data_gap_roi > 0:
        roi = {
            "status": "DATA_GAP",
            "profit_u": None,
            "risked_u": 0.0,
            "roi": None,
            "n_tickets": 0,
            "n_data_gap": data_gap_roi,
            "n_stamped_juice": stamped_juice,
            "note": "Settled W/L tickets lack stamped pre-kick juice — no flat −110 invent.",
        }
    else:
        roi = {
            "status": "empty",
            "profit_u": 0.0,
            "risked_u": 0.0,
            "roi": None,
            "n_tickets": 0,
            "n_data_gap": 0,
            "n_stamped_juice": 0,
            "note": "No settled W/L tickets with stake at risk yet.",
        }

    return {
        "sport": sport,
        "season": season,
        "contract": {
            "eligible": "desk PLAY/LEAN only (writer packages / stamped desk SoT)",
            "edge_board_tag_plays": "excluded unless also on desk card",
            "juice": "best available pre-kick among Compare Odds books; never invent flat −110",
            "stake_play_u": 1.0,
            "stake_lean_u": 0.5,
            "pushes": "profit 0; stake excluded from risked",
        },
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ledger_path": str(ledger_path.relative_to(ROOT)),
        "n_tickets": len(tickets),
        "n_open": len(open_tickets),
        "play_ats": play_ats,
        "play_ats_str": format_ats(play_ats),
        "lean_ats": lean_ats,
        "lean_ats_str": format_ats(lean_ats),
        "combined_ats": combined_ats,
        "combined_ats_str": format_ats(combined_ats),
        "combined_roi": roi,
        "open_ticket_ids": [t.get("ticket_id") for t in open_tickets],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sport", default="cfb")
    ap.add_argument("--season", type=int, default=2026)
    args = ap.parse_args()

    summary = rebuild(args.sport, args.season)
    out = (
        ROOT
        / "data"
        / "desk-record"
        / args.sport
        / str(args.season)
        / "summary.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
