#!/usr/bin/env python3
"""Align board wins ↔ week rates ↔ playoff/SB on a preseason bundle.

Root cause this repairs: soft-pile / defense finalize rewrote
``team_regular_season_outcomes.expected_wins`` from PF/PA production budgets
while leaving ``team_week_win_rates.json`` on the hierarchical MC path. Truth
Layer playoffs then read the stale rates (LAR ~11.1-win strength → ~84%
playoff) while displayed wins + softmax SB used the budget path (LAR ~9.69 →
~0.48% SB).

This script:
1. Canonicalizes LA→LAR (and WSH→WAS) on outcomes, week rates, win dist,
   defense, and player totals.
2. Rescales week rates so each team's Σ week p matches board expected wins.
3. Recomputes 7-seed playoff + strength-bracket Super Bowl from aligned rates.
4. Writes coherence audit JSON next to the bundle.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service" / "src"))
sys.path.insert(0, str(ROOT / "scripts" / "nfl"))

from services.nfl_canonical_teams import (  # noqa: E402
    CANONICAL_TEAMS,
    canonicalize_team,
)
from nfl_playoff_from_week_rates import (  # noqa: E402
    apply_playoff_probs_to_team_rows,
    e_wins_histogram,
    flag_wins_playoff_sb_contradictions,
    recompute_playoff_probs,
    rescale_week_rates_to_expected_wins,
    season_wins_from_rates,
)


def _load_csv(path: Path) -> List[Dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return [dict(r) for r in csv.DictReader(fh)]


def _write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: Optional[List[str]] = None) -> None:
    if not rows:
        return
    fields = fieldnames or list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k) for k in fields})


def _canon_team_field(row: Dict[str, Any], key: str = "team") -> Dict[str, Any]:
    out = dict(row)
    raw = out.get(key)
    if raw is not None:
        out[key] = canonicalize_team(str(raw)) or str(raw).strip().upper()
    return out


def _snapshot_team(rows: List[Dict[str, Any]], team: str) -> Dict[str, Any]:
    for r in rows:
        if canonicalize_team(str(r.get("team") or "")) == team:
            return {
                "team": team,
                "expected_wins": float(r.get("expected_wins") or 0),
                "playoff_prob": float(r.get("playoff_prob") or 0),
                "division_title_prob": float(r.get("division_title_prob") or 0),
                "super_bowl_win_prob": float(r.get("super_bowl_win_prob") or 0),
            }
    return {"team": team}


def apply_coherence(
    bundle_dir: Path,
    *,
    n_replicates: int = 20_000,
    seed: int = 20260811,
    dry_run: bool = False,
) -> Dict[str, Any]:
    outcomes_path = bundle_dir / "team_regular_season_outcomes.csv"
    rates_path = bundle_dir / "team_week_win_rates.json"
    if not outcomes_path.exists() or not rates_path.exists():
        raise SystemExit(f"bundle missing outcomes or week rates: {bundle_dir}")

    before_rows = [_canon_team_field(r) for r in _load_csv(outcomes_path)]
    # Dedupe LA+LAR if both somehow present — keep first (canonical).
    by_team: Dict[str, Dict[str, Any]] = {}
    for r in before_rows:
        t = str(r["team"])
        if t not in by_team:
            by_team[t] = r
    before_rows = list(by_team.values())
    before_lar = _snapshot_team(before_rows, "LAR")

    targets = {
        str(r["team"]): float(r["expected_wins"])
        for r in before_rows
        if str(r["team"]) in CANONICAL_TEAMS
    }
    if len(targets) != 32:
        missing = [t for t in CANONICAL_TEAMS if t not in targets]
        raise SystemExit(f"expected 32 board teams, missing={missing}")

    raw_rates = json.loads(rates_path.read_text(encoding="utf-8"))
    before_rate_wins = season_wins_from_rates(
        {canonicalize_team(k) or k: v for k, v in raw_rates.items()}
    )
    aligned_rates = rescale_week_rates_to_expected_wins(raw_rates, targets)
    after_rate_wins = season_wins_from_rates(aligned_rates)

    recomputed = recompute_playoff_probs(
        aligned_rates,
        n_replicates=n_replicates,
        seed=seed,
        run_super_bowl=True,
    )
    after_rows = apply_playoff_probs_to_team_rows(
        before_rows,
        recomputed,
        rewrite_super_bowl=True,
    )
    after_lar = _snapshot_team(after_rows, "LAR")
    flags = flag_wins_playoff_sb_contradictions(after_rows)
    hist = e_wins_histogram(after_rows)

    audit = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "bundle": bundle_dir.name,
        "root_cause": (
            "Soft-pile/defense expected_wins (production PF/PA path) diverged from "
            "hierarchical team_week_win_rates; Truth Layer playoffs used stale rates "
            "while SB softmax used board wins — LAR showed ~9.7 wins + ~0.48% SB with "
            "~84% playoff."
        ),
        "method": recomputed["method"],
        "n_replicates": n_replicates,
        "seed": seed,
        "before_lar": before_lar,
        "after_lar": after_lar,
        "before_rate_wins_lar": round(float(before_rate_wins.get("LAR") or before_rate_wins.get("LA") or 0), 4),
        "after_rate_wins_lar": round(float(after_rate_wins.get("LAR") or 0), 4),
        "sanity": recomputed["sanity"],
        "e_wins_histogram": hist,
        "contradiction_flags": flags,
        "production_path": (
            "Player pass/rush/rec yards + TDs and defense PF/PA/expected_wins share the "
            "soft-pile finalize budget path; week rates are rescaled to those board wins "
            "so playoff/SB join the same strength story (no separate LAR-lite production)."
        ),
        "team_id_scheme": "product_canonical_LAR",
    }

    if dry_run:
        return audit

    # Persist aligned + canonical artifacts.
    outcome_fields = list(after_rows[0].keys())
    # Prefer stable column order; keep any extra finalize fields (PF/PA, etc.).
    preferred = [
        "season",
        "team",
        "conference",
        "division",
        "expected_wins",
        "sim_expected_wins",
        "wins_p10",
        "wins_p90",
        "playoff_prob",
        "division_title_prob",
        "super_bowl_win_prob",
    ]
    fieldnames = [c for c in preferred if c in outcome_fields] + [
        c for c in outcome_fields if c not in preferred
    ]
    _write_csv(
        outcomes_path,
        sorted(after_rows, key=lambda r: (-float(r["expected_wins"]), str(r["team"]))),
        fieldnames=fieldnames,
    )
    rates_path.write_text(json.dumps(aligned_rates, indent=2) + "\n", encoding="utf-8")

    win_dist_path = bundle_dir / "team_win_distributions.json"
    if win_dist_path.exists():
        dists = json.loads(win_dist_path.read_text(encoding="utf-8"))
        for row in dists:
            row["team"] = canonicalize_team(str(row.get("team") or "")) or row.get("team")
        win_dist_path.write_text(json.dumps(dists, indent=2) + "\n", encoding="utf-8")

    defense_path = bundle_dir / "team_defense_season_totals.csv"
    if defense_path.exists():
        defense = [_canon_team_field(r) for r in _load_csv(defense_path)]
        _write_csv(defense_path, defense, fieldnames=list(defense[0].keys()))

    players_path = bundle_dir / "player_regular_season_totals.csv"
    if players_path.exists():
        players = [_canon_team_field(r) for r in _load_csv(players_path)]
        _write_csv(players_path, players, fieldnames=list(players[0].keys()))

    qc_path = bundle_dir / "quality_checks.json"
    if qc_path.exists():
        qc = json.loads(qc_path.read_text(encoding="utf-8"))
        honesty = dict(qc.get("honesty") or {})
        honesty["playoff_prob"] = (
            "7-seed MC from week rates rescaled to board expected_wins (strength coherence)"
        )
        honesty["super_bowl_win_prob"] = (
            "strength-bracket MC on same aligned week rates (not softmax-only)"
        )
        honesty["strength_coherence"] = (
            "week rates Σ aligned to soft-pile/board expected_wins; product id LAR"
        )
        qc["honesty"] = honesty
        sanity = dict(qc.get("sanity") or {})
        sanity.update(
            {
                "sum_super_bowl_prob": recomputed["sanity"].get("sum_super_bowl"),
                "sum_playoff_prob": recomputed["sanity"]["sum_playoff_league"],
                "sum_playoff_afc": recomputed["sanity"]["sum_playoff_afc"],
                "sum_playoff_nfc": recomputed["sanity"]["sum_playoff_nfc"],
            }
        )
        qc["sanity"] = sanity
        qc["strength_coherence"] = {
            "applied_at_utc": audit["generated_at_utc"],
            "method": recomputed["method"],
            "before_lar": before_lar,
            "after_lar": after_lar,
        }
        qc_path.write_text(json.dumps(qc, indent=2) + "\n", encoding="utf-8")

    audit_path = bundle_dir / "strength_coherence_recompute.json"
    audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    return audit


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--bundle",
        default="data/ops/nfl-preseason-sim-2026-20260809T165350Z",
        help="Bundle directory under repo root (or absolute)",
    )
    ap.add_argument("--n-replicates", type=int, default=20_000)
    ap.add_argument("--seed", type=int, default=20260811)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    bundle = Path(args.bundle)
    if not bundle.is_absolute():
        bundle = ROOT / bundle
    audit = apply_coherence(
        bundle,
        n_replicates=args.n_replicates,
        seed=args.seed,
        dry_run=args.dry_run,
    )
    print(json.dumps(
        {
            "bundle": audit["bundle"],
            "before_lar": audit["before_lar"],
            "after_lar": audit["after_lar"],
            "sanity": audit["sanity"],
            "e_wins_histogram": audit["e_wins_histogram"],
            "contradiction_flags": audit["contradiction_flags"],
            "dry_run": args.dry_run,
        },
        indent=2,
    ))


if __name__ == "__main__":
    main()
