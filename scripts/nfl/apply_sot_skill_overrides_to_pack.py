#!/usr/bin/env python3
"""Apply SOT_SKILL_OVERRIDES onto the live depth pack (no parquet re-download).

Writes the one SoT pack in place. Does not invent a second depth map.
QB1 identities are untouched — no 100k republish flag.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACK = (
    ROOT
    / "services/model-service/src/services/nfl_season_engine/data"
    / "nfl_depth_chart_2026_w1.json"
)
PACKAGER = ROOT / "scripts/nfl/package_season_engine_depth_2026.py"


def _load_packager():
    spec = importlib.util.spec_from_file_location("package_depth_2026", PACKAGER)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {PACKAGER}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    dry = "--dry-run" in sys.argv
    packager = _load_packager()
    payload = json.loads(PACK.read_text(encoding="utf-8"))
    before = list(payload.get("rows") or [])
    after = packager._apply_sot_skill_overrides(before)
    payload["rows"] = after
    notes = list(payload.get("notes") or [])
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    note = (
        f"Skill SoT {stamp}: Walker→SEA RB1, Charbonnet→SEA RB2, "
        "KC RB1 Emmett Johnson (Pacheco-on-DET flagged, not auto-moved)."
    )
    if note not in notes:
        notes.append(note)
    payload["notes"] = notes
    payload["daily_intel_as_of"] = "2026-08-13"

    def slot(rows, team, pos):
        hits = [
            r
            for r in rows
            if r.get("team") == team and r.get("position") == pos
        ]
        hits.sort(key=lambda r: int(r.get("depth_order") or 99))
        return [(int(r["depth_order"]), r.get("player_name")) for r in hits[:4]]

    diff = {
        "dry_run": dry,
        "n_before": len(before),
        "n_after": len(after),
        "sea_rb_before": slot(before, "SEA", "RB"),
        "sea_rb_after": slot(after, "SEA", "RB"),
        "kc_rb_before": slot(before, "KC", "RB"),
        "kc_rb_after": slot(after, "KC", "RB"),
        "walker_after": [
            (r.get("team"), r.get("depth_order"))
            for r in after
            if r.get("player_name") == "Kenneth Walker III"
        ],
        "qb_republish_recommended": False,
    }
    print(json.dumps(diff, indent=2))
    if dry:
        return 0
    PACK.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {PACK}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
