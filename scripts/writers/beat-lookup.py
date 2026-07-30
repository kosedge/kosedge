#!/usr/bin/env python3
"""Print NFL beat writers + suggested search queries for a team code."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "data" / "writers" / "nfl-beat-writers.json"

ALIASES = {
    "WSH": "WAS",
    "WFT": "WAS",
    "JAC": "JAX",
    "LA": "LAR",
    "STL": "LAR",
    "SD": "LAC",
    "OAK": "LV",
}


def load_registry() -> dict:
    if not REGISTRY.exists():
        raise SystemExit(f"Missing registry: {REGISTRY}")
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def normalize(team: str) -> str:
    code = team.strip().upper()
    return ALIASES.get(code, code)


def format_team(code: str, data: dict) -> str:
    teams = data["teams"]
    if code not in teams:
        known = ", ".join(sorted(teams))
        raise SystemExit(f"Unknown team {code!r}. Known: {known}")

    t = teams[code]
    lines = [
        f"{code} — {t['team']} ({t['division']})",
        f"Registry updated: {data.get('updated')} · team confidence: {t.get('confidence', 'n/a')}",
        f"Kos Edge writer: {t.get('kos_edge_writer') or 'unassigned'}",
    ]
    if t.get("notes"):
        lines.append(f"Notes: {t['notes']}")
    lines.append("")
    lines.append("Beat writers:")
    for w in t["writers"]:
        xs = ", ".join(w.get("x") or ["(no handle listed)"])
        conf = w.get("confidence", t.get("confidence", "n/a"))
        lines.append(
            f"  - {w['name']} | {w['outlet']} | {xs} | role={w.get('role')} | conf={conf}"
        )
        if w.get("notes"):
            lines.append(f"      {w['notes']}")

    lines.append("")
    lines.append("League breakers (supplement):")
    for w in data.get("league_breakers", []):
        lines.append(f"  - {w['name']} ({w['outlet']}) {', '.join(w.get('x') or [])}")

    queries = [
        f"{t['team']} training camp {data.get('season', '2026')}",
        f"{t['team']} injury report practice participation",
        f"{t['team']} depth chart QB competition",
        f"{t['team']} roster cuts 53-man",
        f"{t['team']} Week 1 availability",
    ]
    # Add a query naming the top primary writer when available
    primaries = [w for w in t["writers"] if w.get("role") == "primary"]
    if primaries:
        queries.append(f"{primaries[0]['name']} {t['team']} camp")

    lines.append("")
    lines.append("Suggested WebSearch queries:")
    for q in queries:
        lines.append(f"  - {q}")

    lines.append("")
    lines.append("Next: WebSearch → beat scan → official injury/roster → model conflict → write")
    lines.append("See: research-standards.md · docs/writers/TRAINING_CAMP_DESK.md")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lookup NFL beat writers and suggested camp search queries."
    )
    parser.add_argument(
        "--team",
        required=True,
        help="Team abbreviation, e.g. BUF, MIN, LAR (also accepts JAC, WSH, etc.)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print raw team JSON instead of formatted text",
    )
    args = parser.parse_args(argv)
    data = load_registry()
    code = normalize(args.team)
    if args.json:
        if code not in data["teams"]:
            raise SystemExit(f"Unknown team {code!r}")
        print(json.dumps(data["teams"][code], indent=2))
        return 0
    print(format_team(code, data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
