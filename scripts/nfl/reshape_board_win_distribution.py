#!/usr/bin/env python3
"""Re-stretch board expected_wins from locked PF/PA (no second futures model).

Applies the v1.24.1 consecutive-gap pile-break on the existing production
PF/PA spine, then runs strength coherence so week rates + win_dist track board.

Does **not** hand-edit individual team wins.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "data-platform-nfl" / "src"))
sys.path.insert(0, str(ROOT / "scripts" / "nfl"))

from data_platform_nfl.defensive_production_stack import (  # noqa: E402
    EXPECTED_WINS_SUM,
    WIN_PILE_BREAK_SPREAD,
    WIN_PILE_BREAK_WIDTH,
    WIN_STRETCH_CEILING,
    WIN_STRETCH_DENOM,
    WIN_STRETCH_FLOOR,
    WIN_STRETCH_INTENSITY,
    WIN_STRETCH_TAIL_DAMPEN,
    WIN_STRETCH_TAPER_K,
    _break_soft_piles,
    ceiling_cluster_count,
    pythagorean_wins,
    stretch_centered,
)
from apply_nfl_strength_coherence import apply_coherence  # noqa: E402
from check_season_sim_conservation import win_histogram  # noqa: E402


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(fieldnames), extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def reshape_wins_from_pf_pa(
    pf: Dict[str, float],
    pa: Dict[str, float],
) -> Dict[str, float]:
    wins = pythagorean_wins(pf, pa)
    wins = stretch_centered(
        wins,
        center=8.5,
        intensity=WIN_STRETCH_INTENSITY,
        denom=WIN_STRETCH_DENOM,
        soft_floor=WIN_STRETCH_FLOOR,
        soft_ceiling=WIN_STRETCH_CEILING,
        target_sum=EXPECTED_WINS_SUM,
        taper_k=WIN_STRETCH_TAPER_K,
        tail_dampen=WIN_STRETCH_TAIL_DAMPEN,
    )
    resid = {t: float(pf.get(t, 0.0)) - float(pa.get(t, 0.0)) for t in wins}
    wins = _break_soft_piles(
        wins,
        resid,
        width=WIN_PILE_BREAK_WIDTH,
        spread=WIN_PILE_BREAK_SPREAD,
    )
    w_sum = sum(wins.values()) or 1.0
    return {t: float(v) * (EXPECTED_WINS_SUM / w_sum) for t, v in wins.items()}


def apply_reshape(bundle_dir: Path, *, n_replicates: int = 20_000) -> Dict[str, Any]:
    defense_path = bundle_dir / "team_defense_season_totals.csv"
    outcomes_path = bundle_dir / "team_regular_season_outcomes.csv"
    defense = _read_csv(defense_path)
    outcomes = _read_csv(outcomes_path)

    pf = {r["team"]: float(r["points_for"]) for r in defense}
    pa = {r["team"]: float(r["points_against"]) for r in defense}
    before = {r["team"]: float(r["expected_wins"]) for r in outcomes}
    after = reshape_wins_from_pf_pa(pf, pa)

    for row in outcomes:
        team = row["team"]
        if team in after:
            row["expected_wins"] = f"{after[team]:.4f}"
    for row in defense:
        team = row["team"]
        if team in after:
            row["expected_wins"] = f"{after[team]:.4f}"

    _write_csv(outcomes_path, outcomes, list(outcomes[0].keys()))
    _write_csv(defense_path, defense, list(defense[0].keys()))

    coherence = apply_coherence(bundle_dir, n_replicates=n_replicates)

    audit = {
        "applied_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": "reshape_wins_from_pf_pa_v1_24_1_consecutive_pile_break",
        "pile_break": {
            "width": WIN_PILE_BREAK_WIDTH,
            "spread": WIN_PILE_BREAK_SPREAD,
            "clustering": "consecutive_gap",
        },
        "before": {
            "sum": round(sum(before.values()), 4),
            "hist": win_histogram(before),
            "ceiling_cluster_0_35": ceiling_cluster_count(before),
            "top10": sorted(
                ((t, round(w, 4)) for t, w in before.items()),
                key=lambda x: -x[1],
            )[:10],
        },
        "after": {
            "sum": round(sum(after.values()), 4),
            "hist": win_histogram(after),
            "ceiling_cluster_0_35": ceiling_cluster_count(after),
            "top10": sorted(
                ((t, round(w, 4)) for t, w in after.items()),
                key=lambda x: -x[1],
            )[:10],
            "LAR": round(after.get("LAR", 0.0), 4),
            "DET": round(after.get("DET", 0.0), 4),
        },
        "coherence": {
            "sanity": coherence.get("sanity"),
            "after_lar": coherence.get("after_lar"),
            "after_det": coherence.get("after_det"),
            "e_wins_histogram": coherence.get("e_wins_histogram"),
        },
    }
    (bundle_dir / "win_distribution_reshape.json").write_text(
        json.dumps(audit, indent=2) + "\n", encoding="utf-8"
    )
    return audit


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--bundle",
        default="data/ops/nfl-preseason-sim-2026-20260809T165350Z",
    )
    ap.add_argument("--n-replicates", type=int, default=20_000)
    args = ap.parse_args(argv)

    bundle = Path(args.bundle)
    if not bundle.is_absolute():
        bundle = ROOT / bundle
    if not bundle.exists():
        print(f"FAIL: bundle not found: {bundle}", file=sys.stderr)
        return 2

    audit = apply_reshape(bundle, n_replicates=args.n_replicates)
    print(json.dumps(audit, indent=2))
    print(
        f"\nReshape OK — ceiling {audit['before']['ceiling_cluster_0_35']} → "
        f"{audit['after']['ceiling_cluster_0_35']}; hist {audit['before']['hist']} → "
        f"{audit['after']['hist']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
