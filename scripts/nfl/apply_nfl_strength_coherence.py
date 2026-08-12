#!/usr/bin/env python3
"""Align board wins ↔ week rates ↔ win distributions ↔ playoff/SB on a bundle.

Root cause this repairs: soft-pile / defense finalize rewrote
``team_regular_season_outcomes.expected_wins`` from PF/PA production budgets
while leaving ``team_week_win_rates.json`` and ``team_win_distributions.json``
on the hierarchical MC path. Truth Layer playoffs then read the stale rates
(LAR ~11.1-win strength → ~84% playoff) while displayed wins + softmax SB used
the budget path (LAR ~9.69 → ~0.48% SB). DET kept the secondary path longer:
board/defense ~7.05 wins while win_dist.mean stayed ~10.57 for Season Model /
Futures.

This script:
1. Canonicalizes LA→LAR (and WSH→WAS) on outcomes, week rates, win dist,
   defense, players, and leaders.
2. Rescales week rates so each team's Σ week p matches board expected wins.
3. Projects those rates onto the complementary wall-chart game graph
   (iterate until Σ p ≈ hp/(hp+ap) E[wins]) so playoff MC path records
   match published wins — independent PF/PA rescale is not a valid season.
4. Recomputes 7-seed playoff + strength-bracket Super Bowl from aligned rates.
5. Publishes path-MC expected_wins + win_dist from the same draws.
6. Writes coherence audit JSON next to the bundle.
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
    apply_win_dist_percentiles_to_rows,
    build_win_distributions_from_marginal_rates,
    e_wins_histogram,
    flag_win_dist_board_mismatches,
    flag_wins_playoff_sb_contradictions,
    project_rates_onto_schedule,
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
    before_det = _snapshot_team(before_rows, "DET")

    targets = {
        str(r["team"]): float(r["expected_wins"])
        for r in before_rows
        if str(r["team"]) in CANONICAL_TEAMS
    }
    if len(targets) != 32:
        missing = [t for t in CANONICAL_TEAMS if t not in targets]
        raise SystemExit(f"expected 32 board teams, missing={missing}")

    win_dist_path = bundle_dir / "team_win_distributions.json"
    before_dist_mean: Dict[str, float] = {}
    if win_dist_path.exists():
        for row in json.loads(win_dist_path.read_text(encoding="utf-8")):
            t = canonicalize_team(str(row.get("team") or "")) or str(row.get("team") or "")
            before_dist_mean[t] = float(row.get("mean") or 0)

    raw_rates = json.loads(rates_path.read_text(encoding="utf-8"))
    before_rate_wins = season_wins_from_rates(
        {canonicalize_team(k) or k: v for k, v in raw_rates.items()}
    )
    aligned_rates = rescale_week_rates_to_expected_wins(raw_rates, targets)
    aligned_rates, schedule_proj = project_rates_onto_schedule(aligned_rates)
    after_rate_wins = season_wins_from_rates(aligned_rates)

    recomputed = recompute_playoff_probs(
        aligned_rates,
        n_replicates=n_replicates,
        seed=seed,
        run_super_bowl=True,
    )
    win_distributions = recomputed.get("win_distributions") or (
        build_win_distributions_from_marginal_rates(
            aligned_rates,
            n_replicates=n_replicates,
            seed=seed,
        )
    )
    after_rows = apply_playoff_probs_to_team_rows(
        before_rows,
        recomputed,
        rewrite_expected_wins=True,
        rewrite_super_bowl=True,
    )
    after_rows = apply_win_dist_percentiles_to_rows(after_rows, win_distributions)
    after_lar = _snapshot_team(after_rows, "LAR")
    after_det = _snapshot_team(after_rows, "DET")
    flags = flag_wins_playoff_sb_contradictions(after_rows)
    dist_flags = flag_win_dist_board_mismatches(after_rows, win_distributions)
    hist = e_wins_histogram(after_rows)
    after_dist_mean = {
        str(r["team"]): float(r["mean"]) for r in win_distributions
    }

    audit = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "bundle": bundle_dir.name,
        "root_cause": (
            "Independent week-rate rescale to PF/PA Pythagorean wins made "
            "STRENGTH_ALIGN green on marginals while 7-seed MC uses hp/(hp+ap); "
            "LAR 9.69 board vs ~10.8 path wins (CHI 13.93 vs ~10.8) — same run, "
            "two statistics. Project rates onto the complementary schedule, then "
            "publish path-MC wins/playoff/SB/win_dist from those draws."
        ),
        "method": recomputed["method"],
        "n_replicates": n_replicates,
        "seed": seed,
        "before_lar": before_lar,
        "after_lar": after_lar,
        "before_det": before_det,
        "after_det": after_det,
        "before_rate_wins_lar": round(float(before_rate_wins.get("LAR") or before_rate_wins.get("LA") or 0), 4),
        "after_rate_wins_lar": round(float(after_rate_wins.get("LAR") or 0), 4),
        "before_rate_wins_det": round(float(before_rate_wins.get("DET") or 0), 4),
        "after_rate_wins_det": round(float(after_rate_wins.get("DET") or 0), 4),
        "before_win_dist_mean_det": round(float(before_dist_mean.get("DET") or 0), 4),
        "after_win_dist_mean_det": round(float(after_dist_mean.get("DET") or 0), 4),
        "before_win_dist_mean_lar": round(float(before_dist_mean.get("LAR") or before_dist_mean.get("LA") or 0), 4),
        "after_win_dist_mean_lar": round(float(after_dist_mean.get("LAR") or 0), 4),
        "sanity": recomputed["sanity"],
        "e_wins_histogram": hist,
        "contradiction_flags": flags,
        "win_dist_mismatch_flags": dist_flags,
        "schedule_projection": {
            "iterations": schedule_proj.get("iterations"),
            "final_max_gap": schedule_proj.get("final_max_gap"),
            "converged": schedule_proj.get("converged"),
            "history": schedule_proj.get("history"),
        },
        "production_path": (
            "Player pass/rush/rec yards + TDs and defense PF/PA stay on the "
            "soft-pile finalize budget path. Published expected_wins / playoff / "
            "SB / win_dist are the complementary wall-chart path MC from week "
            "rates (hp/(hp+ap)), not independent PF/PA Pythagorean stretch."
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

    # Rebuild win distributions on the production strength path (not id-only canon).
    if win_distributions:
        win_dist_path.write_text(
            json.dumps(win_distributions, indent=2) + "\n", encoding="utf-8"
        )
    elif win_dist_path.exists():
        dists = json.loads(win_dist_path.read_text(encoding="utf-8"))
        for row in dists:
            row["team"] = canonicalize_team(str(row.get("team") or "")) or row.get("team")
        win_dist_path.write_text(json.dumps(dists, indent=2) + "\n", encoding="utf-8")

    defense_path = bundle_dir / "team_defense_season_totals.csv"
    if defense_path.exists():
        defense = [_canon_team_field(r) for r in _load_csv(defense_path)]
        wins_by_team = {
            str(r["team"]): r.get("expected_wins") for r in after_rows
        }
        for row in defense:
            t = str(row.get("team") or "")
            if t in wins_by_team and wins_by_team[t] is not None:
                row["expected_wins"] = wins_by_team[t]
        _write_csv(defense_path, defense, fieldnames=list(defense[0].keys()))

    players_path = bundle_dir / "player_regular_season_totals.csv"
    if players_path.exists():
        players = [_canon_team_field(r) for r in _load_csv(players_path)]
        _write_csv(players_path, players, fieldnames=list(players[0].keys()))

    leaders_path = bundle_dir / "leaders.json"
    if leaders_path.exists():
        leaders = json.loads(leaders_path.read_text(encoding="utf-8"))
        for _section, payload in list(leaders.items()):
            if not isinstance(payload, dict):
                continue
            for key in ("top10", "bottom5"):
                rows = payload.get(key)
                if not isinstance(rows, list):
                    continue
                for row in rows:
                    if isinstance(row, dict) and row.get("team") is not None:
                        row["team"] = canonicalize_team(str(row["team"])) or row["team"]
                        if row.get("label") in ("LA", "WSH"):
                            row["label"] = row["team"]
        leaders_path.write_text(json.dumps(leaders, indent=2) + "\n", encoding="utf-8")

    qc_path = bundle_dir / "quality_checks.json"
    if qc_path.exists():
        qc = json.loads(qc_path.read_text(encoding="utf-8"))
        honesty = dict(qc.get("honesty") or {})
        honesty["playoff_prob"] = (
            "7-seed MC from week rates projected onto complementary wall-chart games"
        )
        honesty["super_bowl_win_prob"] = (
            "strength-bracket MC on the same path draws as expected_wins / playoff"
        )
        honesty["expected_wins"] = (
            "path-MC mean from complementary hp/(hp+ap) games — not PF/PA Pythagorean stretch"
        )
        honesty["strength_coherence"] = (
            "week rates projected onto schedule until Σp ≈ pairwise E[wins]; "
            "board wins + win_dist + playoff/SB from the same path MC; product id LAR"
        )
        honesty["win_distributions"] = (
            "rebuilt from path-MC win totals (same draws as 7-seed playoff / SB)"
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
            "before_det": before_det,
            "after_det": after_det,
            "before_win_dist_mean_det": audit["before_win_dist_mean_det"],
            "after_win_dist_mean_det": audit["after_win_dist_mean_det"],
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
            "before_det": audit.get("before_det"),
            "after_det": audit.get("after_det"),
            "before_win_dist_mean_det": audit.get("before_win_dist_mean_det"),
            "after_win_dist_mean_det": audit.get("after_win_dist_mean_det"),
            "before_win_dist_mean_lar": audit.get("before_win_dist_mean_lar"),
            "after_win_dist_mean_lar": audit.get("after_win_dist_mean_lar"),
            "sanity": audit["sanity"],
            "e_wins_histogram": audit["e_wins_histogram"],
            "contradiction_flags": audit["contradiction_flags"],
            "win_dist_mismatch_flags": audit.get("win_dist_mismatch_flags"),
            "schedule_projection": audit.get("schedule_projection"),
            "dry_run": args.dry_run,
        },
        indent=2,
    ))


if __name__ == "__main__":
    main()
