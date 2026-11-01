#!/usr/bin/env python3
"""ONE Appendix O comparison after freeze. Do not rerun with another weight."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from q2s.bootstrap import (  # noqa: E402
    BOOT_B,
    BOOT_SEED,
    paired_delta_mae,
    paired_game_bootstrap_ci,
)
from q2s.freeze_guard import (  # noqa: E402
    FreezeGuardRefuse,
    assert_freeze_and_rows,
)

ROWS = ROOT / "artifacts" / "q2s_rows_t5033u.json"
FREEZE = ROOT / "artifacts" / "PROTOCOL_FREEZE.json"
LOOK = ROOT / "artifacts" / "LOOK_CONSUMED.json"
OUT_JSON = ROOT / "artifacts" / "APPENDIX_O.json"
OUT_MD = ROOT / "APPENDIX_O_COMPARISON.md"
RETRO = "RETRO_FIT / DEV_RESEARCH"


class LookRefuse(RuntimeError):
    pass


def _mae(pred, act) -> float:
    return float(np.mean(np.abs(np.asarray(pred) - np.asarray(act))))


def _rmse(pred, act) -> float:
    return float(np.sqrt(np.mean((np.asarray(pred) - np.asarray(act)) ** 2)))


def main() -> int:
    if not FREEZE.exists():
        raise LookRefuse("PROTOCOL_FREEZE missing — freeze before the look")
    try:
        assert_freeze_and_rows(ROOT)
    except FreezeGuardRefuse as exc:
        raise LookRefuse(str(exc)) from exc
    if LOOK.exists() or OUT_JSON.exists():
        raise LookRefuse("Appendix O look already consumed — no second look")
    if not ROWS.exists():
        raise LookRefuse("q2s_rows_t5033u.json missing")

    payload = json.loads(ROWS.read_text())
    if payload.get("refused"):
        raise LookRefuse(f"adapter refused comparison: {payload.get('blocker')}")
    rows = list(payload.get("rows") or [])
    if len(rows) != 70:
        raise LookRefuse(f"incomplete coverage n={len(rows)} — no silent subset")
    if payload.get("n_missing"):
        raise LookRefuse("missing coverage present — comparison refused")

    cand, base, act, weeks = [], [], [], []
    for row in rows:
        q2s = row["research"]["q2s"]
        bl = row["baseline"]
        if not bl.get("unchanged"):
            raise LookRefuse("baseline.unchanged is not True")
        if bl.get("mc_draws_unchanged") is not True:
            raise LookRefuse("MC draws not marked unchanged")
        if q2s.get("w") != 0.5:
            raise LookRefuse("w != predeclared 0.5")
        cand.append(float(q2s["margin_mu_q2s"]))
        base.append(float(bl["if_margin_mu"]))
        act.append(float(bl["realized_margin"]))
        weeks.append(int(row["week"]))
        if "win_prob" in q2s or "ats_prob" in q2s or "ou_prob" in q2s:
            raise LookRefuse("candidate probabilities present — forbidden")

    cand_a = np.asarray(cand, dtype=float)
    base_a = np.asarray(base, dtype=float)
    act_a = np.asarray(act, dtype=float)
    deltas = paired_delta_mae(cand_a, base_a, act_a)
    boot = paired_game_bootstrap_ci(deltas, B=BOOT_B, seed=BOOT_SEED)
    mae_c = _mae(cand_a, act_a)
    mae_b = _mae(base_a, act_a)
    rmse_c = _rmse(cand_a, act_a)
    rmse_b = _rmse(base_a, act_a)
    ci_crosses = boot["ci_lo"] <= 0.0 <= boot["ci_hi"]
    if ci_crosses:
        verdict = "INCONCLUSIVE — CI crosses zero; NOT FQ PASS"
    elif boot["mean"] < 0:
        verdict = "POINT_IMPROVEMENT — negative ΔMAE; not FQ PASS; CERT=0"
    else:
        verdict = "POINT_WORSE — positive ΔMAE; not FQ FAIL-as-cert; CERT=0"

    by_week: dict[int, dict[str, float]] = {}
    grouped: dict[int, list[int]] = defaultdict(list)
    for i, w in enumerate(weeks):
        grouped[w].append(i)
    for w, idxs in sorted(grouped.items()):
        ix = np.asarray(idxs, dtype=int)
        by_week[w] = {
            "n": float(ix.size),
            "mae_baseline": _mae(base_a[ix], act_a[ix]),
            "mae_candidate": _mae(cand_a[ix], act_a[ix]),
            "delta_mae": float(deltas[ix].mean()),
            "rmse_baseline": _rmse(base_a[ix], act_a[ix]),
            "rmse_candidate": _rmse(cand_a[ix], act_a[ix]),
        }

    report = {
        "label": RETRO,
        "cert": 0,
        "nfl": "NO-GO",
        "ticket": "t5033u",
        "amend": "fdf91ff5",
        "delegation": "d7e0a6bc",
        "work_package": "2db90f76",
        "guardrails": "52c79ee6",
        "score_results_control": "2b9f302e",
        "q2_eval_closed": "03a4dd90 CLOSED",
        "annotate_684_accept": "9982d42f undisturbed",
        "looked_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n": 70,
        "weight": 0.5,
        "weight_note": "predeclared research candidate — NOT fitted or proven optimum",
        "primary": {
            "delta_mae": boot["mean"],
            "mae_baseline": mae_b,
            "mae_candidate": mae_c,
            "n": 70,
            "bootstrap": boot,
            "ci_crosses_zero": ci_crosses,
            "sign_note": "Negative Δ = point improvement; CI crossing zero = inconclusive, NOT FQ PASS",
        },
        "descriptive": {
            "rmse_baseline": rmse_b,
            "rmse_candidate": rmse_c,
            "per_week": {str(k): v for k, v in by_week.items()},
        },
        "limitations": [
            "Paired game-bootstrap treats games as exchangeable; repeated-team and same-week dependence is not modeled.",
            "Research-consumed exposure: this 70-game SCORE_RESULTS tip is now used for one Q2s look.",
            "w=0.5 was not selected on these outcomes; a failed or inconclusive result does not authorize another weight.",
            "Baseline IF mus/sigma/MC draws were not redrawn; no candidate win/ATS/OU probabilities are claimed.",
            "Original Q2 EVAL 03a4dd90 remains CLOSED.",
            "No market/edge/CERT claim.",
            RETRO,
        ],
        "verdict": verdict,
        "holds": [
            "CERT=0",
            "NFL NO-GO",
            "no merge/deploy/pub/bet",
            "no second look",
            "no second weight",
        ],
    }

    OUT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    LOOK.write_text(
        json.dumps(
            {
                "consumed": True,
                "looked_at_utc": report["looked_at_utc"],
                "n": 70,
                "delta_mae": boot["mean"],
                "label": RETRO,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    OUT_MD.write_text(_render_md(report))
    print(
        f"Appendix O n=70 ΔMAE={boot['mean']:.6f} "
        f"CI[{boot['ci_lo']:.6f},{boot['ci_hi']:.6f}] {verdict}"
    )
    return 0


def _render_md(report: dict) -> str:
    p = report["primary"]
    b = p["bootstrap"]
    d = report["descriptive"]
    lines = [
        "# Appendix O — one Q2s comparison (t5033u)",
        "",
        f"**{RETRO} · CERT=0 · NFL NO-GO · research-consumed only · DRAFT.**",
        "",
        "Cite t5033u · fdf91ff5 · d7e0a6bc · 2db90f76 · 2b9f302e · 03a4dd90 CLOSED.",
        "#684 ACCEPT `9982d42f` undisturbed. Guardrails `52c79ee6`.",
        "",
        "Frozen before this look. **One look only.** No market/edge/CERT claim.",
        "w=0.5 is a predeclared research candidate — NOT fitted or proven optimum.",
        "",
        "## Primary (paired ΔMAE)",
        "",
        f"- n = **{int(p['n'])}** (2017 REG W2–W6 sealed 70; no subset)",
        f"- MAE baseline (IF.margin_mu) = **{p['mae_baseline']:.6f}**",
        f"- MAE candidate (research.q2s.margin_mu_q2s) = **{p['mae_candidate']:.6f}**",
        f"- ΔMAE = mean(|cand−act| − |base−act|) = **{p['delta_mae']:.6f}**",
        f"- 95% paired game-bootstrap CI (B={int(b['B'])}, seed={int(b['seed'])}): "
        f"**[{b['ci_lo']:.6f}, {b['ci_hi']:.6f}]**",
        f"- CI crosses zero: **{p['ci_crosses_zero']}**",
        "",
        p["sign_note"],
        "",
        f"**Verdict:** {report['verdict']}",
        "",
        "## Descriptive",
        "",
        f"- RMSE baseline = {d['rmse_baseline']:.6f}",
        f"- RMSE candidate = {d['rmse_candidate']:.6f}",
        "",
        "| week | n | MAE base | MAE cand | ΔMAE | RMSE base | RMSE cand |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for week, rec in d["per_week"].items():
        lines.append(
            f"| {week} | {int(rec['n'])} | {rec['mae_baseline']:.4f} | "
            f"{rec['mae_candidate']:.4f} | {rec['delta_mae']:.4f} | "
            f"{rec['rmse_baseline']:.4f} | {rec['rmse_candidate']:.4f} |"
        )
    lines.extend(["", "## Limitations", ""])
    for item in report["limitations"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Isolation",
            "",
            "Baseline IF.margin_mu / total_mu / sigma / MC draws unchanged.",
            "No candidate win/ATS/OU probabilities or coherence claims.",
            "Amends #681 §4 + H6 for this comparison only.",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except LookRefuse as exc:
        print(f"REFUSE: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
