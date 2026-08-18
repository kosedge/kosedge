#!/usr/bin/ops/env python3
"""NFL season-preview market fact-check (Editor — Riley Nash).

Compares stated primary win totals in content/writers/season-previews-2026
against a live DK/RotoWire board snapshot and KosEdge Model expected_wins.

Usage:
  python scripts/writers/preview-market-factcheck.py --as-of 2026-08-17
  python scripts/writers/preview-market-factcheck.py --as-of 2026-08-17 --write-ops
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[2]
PREVIEWS = REPO / "content" / "writers" / "season-previews-2026"
OPS = REPO / "data" / "ops"
LAUNCH_PTR = OPS / "nfl-web-launch-bundle.json"

# DraftKings via RotoWire — August 2026 snapshot (Editor audit).
# Re-verify with a live web scan before each weekly run; update this map.
DK_WIN_TOTALS_AUG2026: Dict[str, float] = {
    "LAR": 11.5,
    "BAL": 11.5,
    "BUF": 10.5,
    "SEA": 10.5,
    "DET": 10.5,
    "PHI": 10.5,
    "KC": 10.5,
    "SF": 10.5,
    "NE": 10.5,
    "GB": 9.5,
    "HOU": 9.5,
    "DEN": 9.5,
    "LAC": 9.5,
    "CHI": 9.5,
    "CIN": 9.5,
    "DAL": 9.5,
    "JAX": 8.5,
    "TB": 8.5,
    "PIT": 8.5,
    "MIN": 8.5,
    "NYG": 7.5,
    "NO": 7.5,
    "CAR": 7.5,
    "WAS": 7.5,
    "IND": 7.5,
    "TEN": 6.5,
    "ATL": 6.5,
    "CLE": 6.5,
    "LV": 5.5,
    "NYJ": 5.5,
    "ARI": 4.5,
    "MIA": 4.5,
}


@dataclass
class Row:
    team: str
    stated: Optional[float]
    live: float
    model: Optional[float]
    title: Optional[float]
    handicapper: Optional[float]


def load_model_wins() -> Dict[str, float]:
    ptr = json.loads(LAUNCH_PTR.read_text())
    bid = ptr["bundle_id"]
    csv_path = OPS / bid / "team_regular_season_outcomes.csv"
    out: Dict[str, float] = {}
    with csv_path.open() as f:
        for r in csv.DictReader(f):
            team = (r.get("team") or r.get("team_id") or "").strip().upper()
            if not team:
                continue
            out[team] = float(r["expected_wins"])
    return out


def extract_stated(text: str) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    title_m = re.search(r"Win Total\s+(\d+\.5)", text)
    title = float(title_m.group(1)) if title_m else None
    hn_m = re.search(r"Market number:\s*\*?\*?(\d+\.5)", text)
    hn = float(hn_m.group(1)) if hn_m else None
    market_m = re.search(
        r"\*\*Market[^*]*\*\*[^\n]*?(\d+\.5)",
        text,
    )
    market = float(market_m.group(1)) if market_m else None
    stated = title if title is not None else (hn if hn is not None else market)
    return stated, title, hn


def audit(board: Dict[str, float]) -> List[Row]:
    model = load_model_wins()
    rows: List[Row] = []
    for path in sorted(PREVIEWS.glob("*.md")):
        if path.name == "INDEX.md":
            continue
        team = path.stem.upper()
        text = path.read_text()
        stated, title, hn = extract_stated(text)
        rows.append(
            Row(
                team=team,
                stated=stated,
                live=board[team],
                model=model.get(team),
                title=title,
                handicapper=hn,
            )
        )
    return rows


def lean_from_gap(model: Optional[float], market: float) -> Tuple[str, str]:
    """Return (lean, note) under Edge Threshold Discipline."""
    if model is None:
        return "Pass", "No Model E[wins] — Pass until SoT loads."
    gap = model - market
    if abs(gap) <= 0.55:
        return "Pass", f"Thin |Model {model:.2f} − market {market}| ≈ {abs(gap):.2f} → Pass."
    if abs(gap) >= 1.5:
        return (
            "Pass",
            f"Material Model↔market conflict (Model {model:.2f} vs {market}) — present both; Pass.",
        )
    if gap > 0:
        return (
            f"Over {market:g} (soft)",
            f"Model {model:.2f} clears {market} by {gap:.2f}; keep confidence ≤2 and shop juice.",
        )
    return (
        f"Under {market:g} (soft)",
        f"Model {model:.2f} sits {abs(gap):.2f} under {market}; keep confidence ≤2 and shop juice.",
    )


def render_ops(rows: List[Row], as_of: str) -> str:
    mismatches = [r for r in rows if r.stated is not None and abs(r.stated - r.live) >= 0.5]
    lines = [
        f"# NFL preview market fact-check — {as_of}",
        "",
        "**Editor:** Riley Nash",
        "**Live board:** DraftKings via RotoWire (August 2026 snapshot — re-scan weekly)",
        f"**Model:** `{json.loads(LAUNCH_PTR.read_text())['bundle_id']}` expected_wins",
        "",
        "## Mistake report (desk owner)",
        "",
        f"Found **{len(mismatches)}** primary-market mismatches (Δ ≥ 0.5).",
        "",
        "| Team | Stated | Live DK | Δ | Model E[wins] | Impact |",
        "|------|-------:|--------:|--:|--------------:|--------|",
    ]
    for r in mismatches:
        delta = (r.stated or 0) - r.live
        lean, note = lean_from_gap(r.model, r.live)
        model_s = f"{r.model:.2f}" if r.model is not None else "—"
        lines.append(
            f"| {r.team} | {r.stated} | {r.live} | {delta:+.1f} | "
            f"{model_s} | {lean} — {note} |"
        )
    lines += [
        "",
        "## Full board",
        "",
        "| Team | Stated | Live | Model | Status |",
        "|------|-------:|-----:|------:|--------|",
    ]
    for r in rows:
        ok = r.stated is not None and abs(r.stated - r.live) < 0.5
        model_s = f"{r.model:.2f}" if r.model is not None else "—"
        lines.append(
            f"| {r.team} | {r.stated} | {r.live} | {model_s} | "
            f"{'ok' if ok else 'MISMATCH'} |"
        )
    lines += [
        "",
        "## Doctrine",
        "",
        "Wrong primary win totals are product bugs. Editor reports first, then fixes.",
        "Thin edges and Model↔market conflicts stay **Pass**.",
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    ap.add_argument("--write-ops", action="store_true")
    ap.add_argument(
        "--board",
        default="aug2026",
        help="Board snapshot key (currently only aug2026 DK/RotoWire).",
    )
    args = ap.parse_args()
    board = DK_WIN_TOTALS_AUG2026
    rows = audit(board)
    mismatches = [r for r in rows if r.stated is not None and abs(r.stated - r.live) >= 0.5]
    print(f"Fact-check {args.as_of}: {len(mismatches)} mismatches / {len(rows)} teams")
    for r in mismatches:
        print(
            f"  {r.team}: stated={r.stated} live={r.live} "
            f"model={r.model:.2f if r.model is not None else None}"
        )
    if args.write_ops:
        stamp = args.as_of.replace("-", "")
        out = OPS / f"nfl-preview-factcheck-{stamp}.md"
        out.write_text(render_ops(rows, args.as_of))
        print(f"wrote {out}")
    return 0 if not mismatches else 1


if __name__ == "__main__":
    raise SystemExit(main())
