#!/usr/bin/env python3
"""CLI: NCAAM Lab results-join densify coverage receipt (#14 CONTINUE GO).

Compares thin event_id→actual_margins baseline vs Schedule SoT pack densify.
Does NOT overwrite frozen scorecard v1 grades. No Odds API pulls.

Usage (repo root):
  python3 apps/web/scripts/lab_ncaam_results_coverage_receipt.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

WEB = Path(__file__).resolve().parents[1]
SRC = WEB / "src"
ROOT = WEB.parent.parent

for p in (str(WEB), str(SRC)):
    if p not in sys.path:
        sys.path.insert(0, p)


def main() -> int:
    parser = argparse.ArgumentParser(description="Lab results densify coverage receipt")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Lab fair parquet dir (default: data/ops/lab/ncaam)",
    )
    parser.add_argument(
        "--actuals",
        type=Path,
        default=None,
        help="Optional actual_margins.parquet override",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print receipt JSON only; no writes",
    )
    args = parser.parse_args()

    import polars as pl

    from ncaam_lab.results_attach import (
        attach_lab_outcomes,
        coverage_vs_event_id_only,
        load_event_id_actuals,
        load_schedule_pack_results,
    )

    out_dir = args.out_dir or (ROOT / "data" / "ops" / "lab" / "ncaam")
    generated = datetime.now(timezone.utc).isoformat()

    pack_results, pack_receipt = load_schedule_pack_results()
    event_actuals = load_event_id_actuals(actuals_path=args.actuals)

    cuts: dict = {}
    for cut in ("train_a", "test_a"):
        latest = out_dir / f"ncaam-fair-lab-{cut}-latest.parquet"
        if not latest.exists():
            cuts[cut] = {"error": f"missing {latest.name}"}
            continue
        lab = pl.read_parquet(latest)
        before = coverage_vs_event_id_only(lab, actuals_path=args.actuals)
        densified, after_receipt = attach_lab_outcomes(
            lab,
            pack_results=pack_results,
            event_actuals=event_actuals,
        )
        # Continuity / leakage honesty from fair parquet (not re-graded)
        continuity = {}
        if "continuity_state" in densified.columns:
            for state in densified["continuity_state"].to_list():
                continuity[str(state)] = continuity.get(str(state), 0) + 1
        settled = int(continuity.get("SETTLED", 0))
        cuts[cut] = {
            "before": before,
            "after": {
                "n_lab": after_receipt["n_lab"],
                "n_with_actual": after_receipt["n_with_actual"],
                "outcome_coverage": after_receipt["outcome_coverage"],
                "n_with_actual_pack": after_receipt["n_with_actual_pack"],
                "n_with_actual_event_id_fill": after_receipt["n_with_actual_event_id_fill"],
                "sources": after_receipt["sources"],
            },
            "continuity_counts": continuity,
            "settled_forbidden_count": settled,
            "lift_n": after_receipt["n_with_actual"] - before["n_with_actual"],
            "lift_coverage_pp": round(
                (after_receipt["outcome_coverage"] - before["outcome_coverage"]) * 100,
                2,
            ),
        }

    leakage_ok = True
    leakage_violations = 0
    for cut in ("train_a", "test_a"):
        mans = sorted(out_dir.glob(f"ncaam-fair-lab-{cut}-*.manifest.json"))
        if not mans:
            continue
        man = json.loads(mans[-1].read_text(encoding="utf-8"))
        if man.get("kenpom_leakage_ok") is False:
            leakage_ok = False
        leakage_violations += int(man.get("kenpom_leakage_violations") or 0)

    receipt = {
        "receipt_version": "ncaam-lab-results-densify-v1",
        "generated_at": generated,
        "protocol_note": "Scorecard v1 grades FROZEN — this receipt enables v1.1 later; no peek-tune.",
        "hard_not": [
            "no_odds_densify",
            "no_invent_margins",
            "no_fake_settled",
            "b7_fail_closed",
            "no_v1_grade_retune",
        ],
        "join_policy": {
            "lab_schedule_sot": "D",
            "results_primary": "schedule_sot_packs_tip_date_plus_b7_team_id",
            "results_secondary": "event_id_owned_actual_margins_or_results_csv",
            "ambiguous_key_policy": "omit",
            "unresolved_b7_policy": "omit",
        },
        "pack_receipt": pack_receipt,
        "n_event_id_owned_actuals": len(event_actuals),
        "cuts": cuts,
        "leakage_receipt": {
            "kenpom_leakage_ok": leakage_ok,
            "kenpom_leakage_violations": leakage_violations,
            "settled_forbidden_total": sum(
                int((cuts.get(c) or {}).get("settled_forbidden_count") or 0)
                for c in ("train_a", "test_a")
            ),
        },
        "diagnosis": {
            "root_cause": (
                "Scorecard v1 joined only thin actual_margins.parquet (406 event_ids). "
                "espn_cbb_games_*.csv scrapes are sparse + short-name B7 miss rate high; "
                "SportsData parquet is 2025-only (scrambled trial margins). "
                "Schedule SoT packs already carry B7-mapped final scores for Lab tip windows."
            ),
            "artifacts_verified": {
                "schedule_packs": "primary densify — join tip_date + team_id",
                "actual_margins.parquet": "secondary event_id overlay only",
                "results.csv": "secondary event_id overlay only",
                "espn_cbb_games_*.csv": "insufficient alone (sparse + alias gaps)",
                "all_sportsdata_results_2016-2025.parquet": "2025 season only; not Train/Test-A",
            },
        },
    }

    if args.dry_run:
        print(json.dumps(receipt, indent=2))
        return 0

    ops_dir = ROOT / "data" / "ops"
    ops_dir.mkdir(parents=True, exist_ok=True)
    stamped = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = ops_dir / "ncaam-lab-results-densify-receipt.json"
    stamped_json = ops_dir / f"ncaam-lab-results-densify-receipt-{stamped}.json"
    md_path = ops_dir / "ncaam-lab-results-densify-20260904.md"

    payload = json.dumps(receipt, indent=2) + "\n"
    json_path.write_text(payload, encoding="utf-8")
    stamped_json.write_text(payload, encoding="utf-8")
    md_path.write_text(_render_md(receipt), encoding="utf-8")

    # Also drop a pointer under lab/ncaam without touching frozen v1 scorecard
    lab_ptr = out_dir / "results-densify-receipt-latest.json"
    lab_ptr.write_text(payload, encoding="utf-8")

    print(
        json.dumps(
            {
                "outputs": {
                    "json": str(json_path.relative_to(ROOT)),
                    "stamped_json": str(stamped_json.relative_to(ROOT)),
                    "ops_md": str(md_path.relative_to(ROOT)),
                    "lab_ptr": str(lab_ptr.relative_to(ROOT)),
                },
                "cuts": {
                    c: {
                        "before_n": (cuts.get(c) or {}).get("before", {}).get("n_with_actual"),
                        "after_n": (cuts.get(c) or {}).get("after", {}).get("n_with_actual"),
                        "before_cov": (cuts.get(c) or {}).get("before", {}).get("outcome_coverage"),
                        "after_cov": (cuts.get(c) or {}).get("after", {}).get("outcome_coverage"),
                    }
                    for c in ("train_a", "test_a")
                },
                "leakage_receipt": receipt["leakage_receipt"],
                "v1_grades_touched": False,
            },
            indent=2,
        )
    )
    return 0


def _render_md(receipt: dict) -> str:
    cuts = receipt.get("cuts") or {}
    train = cuts.get("train_a") or {}
    test = cuts.get("test_a") or {}
    leak = receipt.get("leakage_receipt") or {}
    tb, ta = train.get("before") or {}, train.get("after") or {}
    xb, xa = test.get("before") or {}, test.get("after") or {}

    def row(label: str, before: dict, after: dict, lift_n, lift_pp) -> list[str]:
        return [
            f"| {label} n_lab | {before.get('n_lab')} | {after.get('n_lab')} | — |",
            f"| {label} n_with_actual | {before.get('n_with_actual')} | {after.get('n_with_actual')} | +{lift_n} |",
            f"| {label} outcome_coverage | {before.get('outcome_coverage')} | {after.get('outcome_coverage')} | +{lift_pp} pp |",
        ]

    lines = [
        "# NCAAM Lab — results-join densify (#14 CONTINUE GO)",
        "",
        f"**As of:** {str(receipt.get('generated_at') or '')[:10]}",
        "**Base branch:** `deploy-vercel`",
        "**Scorecard v1:** FROZEN (no grade retune; enables v1.1 later)",
        "",
        "## Diagnosis",
        "",
        str((receipt.get("diagnosis") or {}).get("root_cause") or ""),
        "",
        "## Coverage receipt (cited n)",
        "",
        "| Metric | Before (event_id actual_margins) | After (Schedule SoT packs + B7) | Lift |",
        "| ------ | -------------------------------- | ------------------------------- | ---- |",
        *row("Train-A", tb, ta, train.get("lift_n"), train.get("lift_coverage_pp")),
        *row("Test-A", xb, xa, test.get("lift_n"), test.get("lift_coverage_pp")),
        "",
        "## Join policy",
        "",
        "- Lab schedule SoT remains **D** (Odds `event_id` + B7)",
        "- Results primary: Schedule SoT packs on `tip_date` + `home_team_id`/`away_team_id`",
        "- Results secondary: owned `actual_margins.parquet` / `results.csv` by `event_id`",
        "- Fail-closed: unresolved B7 / ambiguous keys → omit; never invent margins",
        "- **No Odds API densify / credit burn**",
        "",
        "## Leakage / continuity",
        "",
        f"- KenPom leakage OK: `{leak.get('kenpom_leakage_ok')}`",
        f"- KenPom leakage violations: `{leak.get('kenpom_leakage_violations')}` (must be 0)",
        f"- SETTLED forbidden total: `{leak.get('settled_forbidden_total')}` (must be 0)",
        f"- Continuity Train-A: `{train.get('continuity_counts')}`",
        f"- Continuity Test-A: `{test.get('continuity_counts')}`",
        "",
        "## Artifacts verified",
        "",
    ]
    for k, v in ((receipt.get("diagnosis") or {}).get("artifacts_verified") or {}).items():
        lines.append(f"- `{k}`: {v}")
    lines += [
        "",
        "## Hard NOT (held)",
        "",
        "- Odds densify / credit burn",
        "- Edge Board / PLAY / Conf% / props",
        "- Invent tips / fake SETTLED / KenPom-as-SoT / #12 GO-2",
        "- Peek-tuning of v1 scorecard grade gates or rewriting frozen v1 numbers",
        "",
        "## How to re-run",
        "",
        "```bash",
        "python3 apps/web/scripts/lab_ncaam_results_coverage_receipt.py",
        "```",
        "",
        "Scorecard path uses densify by default (`densify_results=True`) for future v1.1;",
        "reproduce thin v1 baseline with `build_scorecard(densify_results=False)`.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
