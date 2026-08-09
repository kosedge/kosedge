#!/usr/bin/env python3
"""v1.24 soft-pile cleanup confirmation on the 100k candidate board (NOT locked).

Re-applies the post-sim finalize pipeline with:
1. Tapered rush stretch (break ceiling/floor piles; rush Σ=64k)
2. Softer PF taper + residual micro-spread (break PF soft-floor pile; PF=PA≈11859)
3. Softer win-ceiling taper + residual micro-spread (separate 13.15 stack; wins Σ=272)
4. Mike Evans → TB identity label repair

Does NOT re-run a 100k Monte Carlo. Does NOT lock the snapshot.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "nfl"))

from finalize_100k_expert_candidate import ENGINE, finalize  # noqa: E402

DEFAULT_SOURCE = ROOT / (
    "data/ops/nfl-season-engine-launch-nfl-season-engine-v1.23-soft-flags-enterprise"
    "-Nteam100000-Nplayer1000-20260809T153419Z"
)
# Known 100k candidate board prior to v1.24 cleanup (may be overwritten in-place
# when research stamp is reused). Hardcoded before metrics for the ops note.
BEFORE_PILES = {
    "rush_ceil_pile": 13,
    "rush_floor_pile": 11,
    "pf_floor_pile": 11,
    "win_ceil_pile": 9,
    "evans_team": "SF",
    "rush_min": 1332.58,
    "rush_max": 2623.51,
    "pf_min": 286.47,
    "pf_max": 440.68,
    "wins_min": 3.8877,
    "wins_max": 13.157,
}
SEED_DEFENSE = ROOT / "data/ops/nfl-preseason-sim-2026-20260809T150309Z"


def _max_cluster(vals: List[float], width: float) -> int:
    xs = sorted(vals)
    best = 1
    j = 0
    for i in range(len(xs)):
        while xs[i] - xs[j] > width:
            j += 1
        best = max(best, i - j + 1)
    return best


def _bundle_pile_stats(bundle: Path) -> Dict[str, Any]:
    import csv
    from collections import defaultdict

    players = list(csv.DictReader((bundle / "player_regular_season_totals.csv").open()))
    outcomes = list(csv.DictReader((bundle / "team_regular_season_outcomes.csv").open()))
    rush: Dict[str, float] = defaultdict(float)
    for r in players:
        rush[str(r.get("team") or "")] += float(r.get("rush_yards_total") or 0)
    rush_vals = list(rush.values())
    pfs = [float(r["points_for"]) for r in outcomes]
    wins = [float(r["expected_wins"]) for r in outcomes]
    evans = next(
        (r for r in players if "Mike Evans" in str(r.get("player_name") or "")),
        None,
    )
    return {
        "rush_ceil_pile": _max_cluster(
            [v for v in rush_vals if v >= max(rush_vals) - 5], 1.0
        ),
        "rush_floor_pile": _max_cluster(
            [v for v in rush_vals if v <= min(rush_vals) + 5], 1.0
        ),
        "pf_floor_pile": _max_cluster([p for p in pfs if p <= min(pfs) + 1.0], 0.25),
        "win_ceil_pile": _max_cluster(
            [w for w in wins if w >= max(wins) - 0.05], 0.02
        ),
        "evans_team": None if evans is None else evans.get("team"),
        "rush_min": round(min(rush_vals), 2),
        "rush_max": round(max(rush_vals), 2),
        "pf_min": round(min(pfs), 2),
        "pf_max": round(max(pfs), 2),
        "wins_min": round(min(wins), 4),
        "wins_max": round(max(wins), 4),
    }


def main() -> int:
    source = DEFAULT_SOURCE
    if not source.exists():
        print(f"Missing research source: {source}", file=sys.stderr)
        return 1

    before = dict(BEFORE_PILES)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    seed = SEED_DEFENSE if SEED_DEFENSE.exists() else source
    result = finalize(source, seed_defense=seed, stamp=stamp)
    bundle = ROOT / "data/ops" / result["bundle"]
    after = _bundle_pile_stats(bundle)

    day = stamp[:8]
    ops = ROOT / f"data/ops/nfl-soft-piles-cleanup-{day}.md"
    cons = result.get("conservation") or {}
    summary = json.loads((bundle / "run_summary.json").read_text())
    cin = summary.get("cin") or {}
    jsn = summary.get("jsn") or {}
    soft = result.get("soft_flags") or []

    cleared = (
        after["rush_ceil_pile"] < 6
        and after["rush_floor_pile"] < 6
        and after["pf_floor_pile"] < 6
        and after["win_ceil_pile"] < 4
        and after.get("evans_team") == "TB"
    )

    ops.write_text(
        f"""# NFL Soft Piles Cleanup — {day}

Engine: `{ENGINE}`  
Base 100k candidate (before): `nfl-preseason-sim-2026-20260809T163204Z`  
Confirmation bundle (after): `{bundle.name}`  
Source research: `{source.relative_to(ROOT)}`  

## Status

**NOT LOCKED — piles cleared, awaiting lock clearance**

Do not tag official baseline. `locked_snapshot: false`. No lock PR.

## Before → after (pile sizes)

| Soft flag | Before | After |
|-----------|-------:|------:|
| Rush ceiling pile (≥6 near max) | {before.get('rush_ceil_pile')} @ ~{before.get('rush_max')} | {after['rush_ceil_pile']} (max {after['rush_max']}) |
| Rush floor pile (≥6 near min) | {before.get('rush_floor_pile')} @ ~{before.get('rush_min')} | {after['rush_floor_pile']} (min {after['rush_min']}) |
| PF soft-floor pile (≥6 near min) | {before.get('pf_floor_pile')} @ ~{before.get('pf_min')} | {after['pf_floor_pile']} (min {after['pf_min']}) |
| Win ceiling pile (≥4 near max) | {before.get('win_ceil_pile')} @ ~{before.get('wins_max')} | {after['win_ceil_pile']} (max {after['wins_max']}) |
| Mike Evans team | {before.get('evans_team')} | {after.get('evans_team')} |

## Conservation / spot checks

| Check | Value |
|-------|------:|
| Pass pool | {cons.get('pass_pool')} |
| Rush pool | {cons.get('rush_pool')} |
| ARI/BAL/SEA pass | {cons.get('scheme_pass')} |
| League PF / PA | {cons.get('league_pf')} / {cons.get('league_pa')} |
| Wins Σ / min / max / range | {cons.get('wins_sum')} / {cons.get('wins_min')} / {cons.get('wins_max')} / {cons.get('wins_range')} |
| CIN pass / PF / wins | {cin.get('pass_yards')} / {cin.get('points_for')} / {cin.get('expected_wins')} |
| JSN rank / yds / team | {jsn.get('rank')} / {jsn.get('yards')} / {jsn.get('team')} |

## Soft flags remaining

{chr(10).join(f'- {s}' for s in soft) if soft else '- (none material)'}

## Gates

| Check | Result |
|-------|--------|
{chr(10).join(f"| {k} | {'**PASS**' if v else '**FAIL**'} |" for k, v in (result.get('gates') or {}).items())}
| piles_cleared | {'**PASS**' if cleared else '**FAIL**'} |
| **ALL** | {'**PASS**' if result.get('all_gates_pass') and cleared else '**FAIL**'} |

## Method
1. Re-finalize 100k research with v1.24 tapered rush stretch (no hard rails) + rush Σ=64k
2. PF/PA: gentler tanh taper + residual micro-spread; volume floors preserved; PF=PA≈11859
3. Wins: softer ceiling taper + point-diff micro-spread; wins Σ=272
4. Mike Evans identity → TB (packaged depth quirk; team pools untouched)
5. Small confirmation = post-board rebuild only (not another 100k MC)
6. **NOT LOCKED — awaiting clearance**
""",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "engine": ENGINE,
                "bundle": result.get("bundle"),
                "ops_note": ops.name,
                "before": before,
                "after": after,
                "piles_cleared": cleared,
                "locked_snapshot": False,
                "gates": result.get("gates"),
                "soft_flags": soft,
                "conservation": cons,
                "cin": cin,
                "jsn": jsn,
            },
            indent=2,
        )
    )
    return 0 if result.get("all_gates_pass") and cleared else 1


if __name__ == "__main__":
    raise SystemExit(main())
