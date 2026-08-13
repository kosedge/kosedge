#!/usr/bin/env python3
"""Print 32-team depth + coaching SoT coverage (Go-mode Gate A).

Usage:
  python scripts/nfl/audit_depth_sot.py
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.nfl_season_engine.coaching_staff import load_packaged_coaching_staff  # noqa: E402
from src.services.nfl_season_engine.loaders import NFL_TEAMS, load_packaged_depth_chart  # noqa: E402

SKILL = ("QB", "RB", "WR", "TE")


def main() -> int:
    rows, dmeta = load_packaged_depth_chart(2026)
    book, cmeta = load_packaged_coaching_staff(2026)
    by = defaultdict(lambda: defaultdict(list))
    for r in rows:
        by[r["team"]][r["position"]].append(r)

    print(f"as_of={dmeta.get('roster_as_of')} snapshot={dmeta.get('snapshot_id')}")
    print(f"depth_source={dmeta.get('roster_source')} teams={len(by)} rows={len(rows)}")
    print(
        f"HC named={cmeta.get('coaching_named_hc_count')}/32 "
        f"full_staff={cmeta.get('coaching_full_staff_count')}/32 "
        f"thin_dc={cmeta.get('coaching_thin_dc')}"
    )
    print()
    print(f"{'Tm':<4} {'QB1':<22} {'RB1':<22} {'WR1':<22} {'TE1':<20} {'HC':<20} OC/DC")
    holes = []
    for team in NFL_TEAMS:
        def n1(pos: str) -> str:
            slots = sorted(by[team][pos], key=lambda x: int(x.get("depth_order") or 99))
            if not slots:
                return "MISSING"
            return str(slots[0].get("player_name") or "UNNAMED")

        qb, rb, wr, te = n1("QB"), n1("RB"), n1("WR"), n1("TE")
        st = book.get(team) or {}
        hc = st.get("hc_name") or "MISSING"
        oc = st.get("oc_name") or "THIN"
        dc = st.get("dc_name") or "THIN"
        print(f"{team:<4} {qb:<22} {rb:<22} {wr:<22} {te:<20} {hc:<20} {oc}/{dc}")
        for label, val in (("QB1", qb), ("RB1", rb), ("WR1", wr), ("TE1", te), ("HC", hc)):
            if val in ("MISSING", "UNNAMED"):
                holes.append(f"{team} {label}")
    print()
    print("holes:", holes or "none")
    open_battles = [
        r
        for r in rows
        if r.get("competition_status") == "open_competition" and int(r.get("depth_order") or 0) <= 2
    ]
    print("open_competition QB/skill (depth 1–2):")
    for r in open_battles:
        print(f"  {r['team']} {r['position']}{r['depth_order']} {r['player_name']}")
    return 0 if not holes else 1


if __name__ == "__main__":
    raise SystemExit(main())
