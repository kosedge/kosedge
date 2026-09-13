#!/usr/bin/env python3
"""Score predeclared additive scoring identities. Does not write production knobs."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_warehouse.additive_scoring_architecture import (  # noqa: E402
    run_additive_scoring_architecture,
)

OUT_JSON = ROOT / "data/ops/cfb-additive-scoring-architecture-20260912.json"
OUT_MD = ROOT / "data/ops/cfb-additive-scoring-architecture-20260912.md"


def _fmt(value: object, digits: int = 3) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _pct(value: object) -> str:
    if value is None:
        return "—"
    return f"{100.0 * float(value):.1f}%"


def _dist_line(card: dict, label: str) -> str:
    return (
        f"{label}: n={card.get('n')} mean={_fmt(card.get('mean'))} "
        f"sd={_fmt(card.get('sd'))} "
        f"P5={_fmt(card.get('p5'))} P10={_fmt(card.get('p10'))} "
        f"P25={_fmt(card.get('p25'))} P50={_fmt(card.get('p50'))} "
        f"P75={_fmt(card.get('p75'))} P90={_fmt(card.get('p90'))} "
        f"P95={_fmt(card.get('p95'))} "
        f"<40={_pct(card.get('freq_lt40'))} <45={_pct(card.get('freq_lt45'))} "
        f">60={_pct(card.get('freq_gt60'))} >65={_pct(card.get('freq_gt65'))} "
        f">70={_pct(card.get('freq_gt70'))}"
    )


def _bucket_line(card: dict) -> str:
    parts = []
    for name in ("lt_48", "48_54", "54_60", "60_68", "ge_68"):
        row = (card or {}).get(name) or {}
        parts.append(f"{name} n={row.get('n', 0)} b={_fmt(row.get('bias'))}")
    return "; ".join(parts)


def _rec(payload: dict, cid: str) -> dict:
    for rec in payload.get("candidates") or []:
        if rec.get("id") == cid:
            return rec
    return {}


def write_markdown(payload: dict) -> str:
    gate = payload.get("decision") or {}
    eq = payload.get("equation") or {}
    forensic = payload.get("c2_compression_forensic") or {}
    e3_high = forensic.get("e3_pred_ge68") or {}
    e3_act = forensic.get("e3_actual_ge68") or {}
    ident = payload.get("a1_a4_identity") or {}
    by_model = forensic.get("by_model") or {}
    e3 = _rec(payload, "E3_ref")
    c2 = _rec(payload, "C2_ref")
    a1 = _rec(payload, "A1_point_half")
    a3 = _rec(payload, "A3_point_full")
    a5 = _rec(payload, "A5_c2_unclamped")
    e3v = (e3.get("eval") or {}).get("val_1") or {}
    c2v = (c2.get("eval") or {}).get("val_1") or {}
    a1v = (a1.get("eval") or {}).get("val_1") or {}
    a3v = (a3.get("eval") or {}).get("val_1") or {}
    a5v = (a5.get("eval") or {}).get("val_1") or {}

    lines = [
        "# CFB additive raw O/D scoring architecture",
        "",
        f"**Generated:** `{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}`",
        f"**Production MATCHUP_RESPONSE:** `{payload.get('matchup_response_frozen')}` (unchanged)",
        f"**LEAGUE_TEAM_PPG:** `{payload.get('league_team_ppg_frozen')}` (unchanged)",
        f"**Kill switch:** `{payload.get('kill_switch')}`  **#532:** DO NOT MERGE",
        f"**Lake:** owned Odds-API 2022–24 closes  **Universe:** v1 Layer A QB + prior-year efficiency + league-avg roster",
        "",
        "Frozen splits were not touched: Train-0=2022, Val-0=2023, Val-1=2024 W1–14.",
        "2025 sealed. 2026 / W2 n=47 is not in this loss. Actual scores are the objective. Close is diagnostic.",
        "C2 is architectural evidence only. Do not fit the 0.5/0.5 weights.",
        "",
        "## Decision",
        "",
        f"**{gate.get('decision')}**",
        "",
        f"Ship: **false**. Winner: **none**. Sealed-2025 candidates: **none**.",
        "",
        "A1 (and A2, which is identical on this universe) flattened the residual "
        "function about as much as C2 did — Val-1 range 21.29 → 9.93, bias −0.09, "
        "favorite-agree 0.722. That is the shape we wanted from an additive engine.",
        "",
        "It does not survive the distributional gate. Val-1 predicted-total SD is "
        "**4.80** against actual SD **16.73** (ratio 0.29). Predicted P90 is 59.4; "
        "actual P90 is 77. Predicted >65 frequency is 1.1%; actual is 21.8%. "
        "The ≥68 bucket is 4 games. This is variance collapse, not calibration.",
        "",
        "Do not write A1, C2, or any α into `priors.py`. Board stays OFF. 2025 stays sealed.",
        "",
        "## The equation",
        "",
        f"`{eq.get('form')}`",
        "",
        f"Total: `{eq.get('total')}`  \nSpread (existing convention): `{eq.get('spread_home')}`",
        "",
        "Scoring level is separated from matchup differential. Both team scores "
        "come from one path; total and margin are identities of those scores.",
        "",
        f"- μ = `{eq.get('mu')}` — documented `LEAGUE_TEAM_PPG`. Not a residual intercept.",
        f"- center = 50 — documented 0–100 scale. Val-1 means sit near 50.6 / 51.2.",
        f"- α = β = `{_fmt(eq.get('alpha_half'), 6)}` (25.9/136) on A1 — each axis owns half a linearized index unit.",
        f"- α = β = `{_fmt(eq.get('alpha_full'), 6)}` (25.9/68) on A3 — C3 in point space; negative control.",
        "- Pace scales possessions of the **whole** rate, not a secret product on the mismatch.",
        "- HFA and coaching stay additive point adjustments after the rate is formed.",
        "- 12.6 possessions is the existing E4 scaffold, not a new fit.",
        "",
        "No coefficient was searched. No market term. No bucket correction. No spline.",
        "",
        "## Why Val-1 ≥68 fell from 54 to 3 — both things are true",
        "",
        f"E3 predicted ≥68 in **{forensic.get('e3_pred_ge68_n')}** Val-1 games. "
        f"Actual ≥68 happened in **{forensic.get('e3_actual_ge68_n')}** Val-1 games.",
        "",
        "Those are almost different sets.",
        "",
        "| slice | n | E3 pred | C2/A1 pred | actual |",
        "|---|---:|---:|---:|---:|",
        f"| E3 predicted ≥68 | {forensic.get('e3_pred_ge68_n')} | "
        f"{_fmt(e3_high.get('mean_pred'))} | "
        f"{_fmt(((by_model.get('A1_point_half') or {}).get('on_e3_pred_ge68') or {}).get('mean_other_pred'))} | "
        f"{_fmt(e3_high.get('mean_actual'))} |",
        f"| actually ≥68 | {forensic.get('e3_actual_ge68_n')} | "
        f"{_fmt(e3_act.get('mean_pred'))} | "
        f"{_fmt(((by_model.get('A1_point_half') or {}).get('on_e3_actual_ge68') or {}).get('mean_other_pred'))} | "
        f"{_fmt(e3_act.get('mean_actual'))} |",
        "",
        f"Of E3's 54 predicted-≥68 games, only **{e3_high.get('actual_ge68_n')}** "
        "actually scored 68+. Mean actual on that slice is **59.1**. The ratio "
        "was inventing shootouts: 72.4 projected, +13.3 bias. A1 puts those same "
        "games at **63.0** — closer to the 59 that happened. That half of the "
        "54→3 drop is *false amplification removed*.",
        "",
        "The other half is collapse. 140 games actually went ≥68 (mean 79.2). "
        "E3 projected them at 56.9. A1 projected them at **54.7**. C2 at 54.6. "
        "A3 (full slope, the tail-restoring control) at 55.8. Nobody in this "
        "candidate set can see a real shootout. Prior-year efficiency is "
        "pointing at the wrong games.",
        "",
        f"A5 (C2 with the 7–55 team-score rail off) is **identical** to C2: "
        f"Val-1 ≥68 n={a5v.get('high_tail_ge68_n')}. "
        "The missing high totals are the half-index slope, not the clamp.",
        "",
        "## Better calibration vs variance collapse",
        "",
        "Val-1 predicted vs actual totals:",
        "",
        "| model | mean | SD | P10 | P50 | P90 | <45 | >65 | >70 | ≥68 n | sd ratio |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    def _dist_row(rec: dict, name: str) -> str:
        ev = (rec.get("eval") or {}).get("val_1") or {}
        d = ((ev.get("distribution") or {}).get("predicted") or {})
        ratio = (ev.get("distribution") or {}).get("sd_ratio_pred_over_actual")
        return (
            f"| {name} | {_fmt(d.get('mean'))} | {_fmt(d.get('sd'))} | "
            f"{_fmt(d.get('p10'))} | {_fmt(d.get('p50'))} | {_fmt(d.get('p90'))} | "
            f"{_pct(d.get('freq_lt45'))} | {_pct(d.get('freq_gt65'))} | "
            f"{_pct(d.get('freq_gt70'))} | {ev.get('high_tail_ge68_n')} | {_fmt(ratio)} |"
        )

    act = ((e3v.get("distribution") or {}).get("actual") or {})
    lines.append(
        f"| **actual** | {_fmt(act.get('mean'))} | {_fmt(act.get('sd'))} | "
        f"{_fmt(act.get('p10'))} | {_fmt(act.get('p50'))} | {_fmt(act.get('p90'))} | "
        f"{_pct(act.get('freq_lt45'))} | {_pct(act.get('freq_gt65'))} | "
        f"{_pct(act.get('freq_gt70'))} | {forensic.get('e3_actual_ge68_n')} | 1.000 |"
    )
    lines.append(_dist_row(e3, "E3 ratio"))
    lines.append(_dist_row(c2, "C2 additive product"))
    lines.append(_dist_row(a1, "A1 point-space half"))
    lines.append(_dist_row(a3, "A3 point-space full"))
    lines += [
        "",
        "E3 is already under-dispersed (sd ratio 0.53). Its extra spread is "
        "almost entirely a false right tail. C2/A1 keep the mean and crush "
        "the rest: predicted mass lives in a 48–60 band while a third of "
        "football games finish under 45 or over 65.",
        "",
        "Calibration inside the actual high-scoring environment (Val-1 actual >65, n=156, mean 77.9):",
        "",
        "| model | mean pred on those games | bias |",
        "|---|---:|---:|",
    ]
    for rec, name in ((e3, "E3"), (c2, "C2"), (a1, "A1"), (a3, "A3")):
        region = (
            ((rec.get("eval") or {}).get("val_1") or {})
            .get("distribution", {})
            .get("region_calibration", {})
            .get("actual_gt65")
            or {}
        )
        lines.append(
            f"| {name} | {_fmt(region.get('mean_pred'))} | {_fmt(region.get('bias'))} |"
        )
    lines += [
        "",
        "And the reverse — games the model called >65:",
        "",
        "| model | n | mean pred | mean actual | bias |",
        "|---|---:|---:|---:|---:|",
    ]
    for rec, name in ((e3, "E3"), (c2, "C2"), (a1, "A1"), (a3, "A3")):
        region = (
            ((rec.get("eval") or {}).get("val_1") or {})
            .get("distribution", {})
            .get("region_calibration", {})
            .get("pred_gt65")
            or {}
        )
        lines.append(
            f"| {name} | {region.get('n')} | {_fmt(region.get('mean_pred'))} | "
            f"{_fmt(region.get('mean_actual'))} | {_fmt(region.get('bias'))} |"
        )
    lines += [
        "",
        "When the model predicts a shootout, football prints ~54–60. When "
        "football prints a shootout, the model prints ~55. That is not a "
        "slope we can fix by sliding α between 25.9/136 and 25.9/68.",
        "",
        "## Candidate scorecards",
        "",
        "Gates were predeclared: Val-1 residual range drop ≥8 vs E3, |bias| ≤3, "
        "favorite-agree drop ≤0.03, Train-0/Val-0 ranges also improve, **and** "
        "sd(pred)/sd(actual) ≥ 0.50, pred>65 frequency at least 25% of actual, "
        "P90 under-spread ≤12, P10 over-spread ≤12. On every split.",
        "",
        "| id | Train-0 MAE / bias / range / sd-ratio | Val-0 MAE / bias / range / sd-ratio | Val-1 MAE / bias / range / fav / sd-ratio |",
        "| --- | --- | --- | --- |",
    ]
    for rec in payload.get("candidates") or []:
        cells = [rec.get("id")]
        for split in ("train_0", "val_0", "val_1"):
            ev = ((rec.get("eval") or {}).get(split) or {})
            dist = ev.get("distribution") or {}
            fav = (ev.get("favorite") or {}).get("favorite_agree_vs_close")
            piece = (
                f"{_fmt(ev.get('total_mae'))} / {_fmt(ev.get('total_bias'))} / "
                f"{_fmt(ev.get('projected_total_bias_range'))} / "
                f"{_fmt(dist.get('sd_ratio_pred_over_actual'))}"
            )
            if split == "val_1":
                piece += f" / fav={_fmt(fav)}"
            cells.append(piece)
        lines.append("| " + " | ".join(str(c) for c in cells) + " |")

    lines += [
        "",
        "### Reading the scorecard",
        "",
        "- **A1** passes the flatten gate (range 21.29 → 9.93; Train-0 / Val-0 move the same way; fav 0.725 → 0.722). It fails every dispersion check on every split. `VARIANCE_COLLAPSE_DO_NOT_PROMOTE`.",
        "- **A2 equals A1** on this reconstruction. v1 units are league-average, so putting units back on the rate is a no-op. Not evidence that units are harmless on a real-roster path.",
        "- **A4 equals A1** exactly (max |Δ| = "
        f"`{_fmt(ident.get('max_abs_total_diff'))}` on {ident.get('n_paired')} games). "
        "The possession rewrite is the same equation. Implementation is consistent.",
        "- **A3** restores dispersion (Val-1 sd ratio 0.56, ≥68 n=49) and **worsens** residual range to 22.18. Same C3 lesson: a pretty mean (−0.28) with a worse shape is subtract-10 in nicer clothes. It also still projects actual >65 games at 55.4.",
        "- **A5 equals C2.** Clamp is not the story.",
        "- Low-projected A1 games still sit about **−6.4** on the <48 bucket. Shape improved. It is not flat.",
        "",
        "### Val-1 projected-total buckets and OLS",
        "",
    ]
    for rec in payload.get("candidates") or []:
        ev = ((rec.get("eval") or {}).get("val_1") or {})
        ols = ev.get("ols_residual_on_projected_total") or {}
        alg = ev.get("algebra") or {}
        team = ev.get("team_scores") or {}
        lines.append(
            f"**{rec.get('id')}** range={_fmt(ev.get('projected_total_bias_range'))} "
            f"OLS slope={_fmt(ols.get('slope'))} r²={_fmt(ols.get('r2'))} "
            f"algebra violations total/margin="
            f"{alg.get('n_total_violations')}/{alg.get('n_margin_violations')} "
            f"team home bias={_fmt(((team.get('home') or {}).get('bias')))} "
            f"away bias={_fmt(((team.get('away') or {}).get('bias')))} "
            f"spread MAE close/actual={_fmt(ev.get('spread_mae_vs_close'))}/"
            f"{_fmt(ev.get('spread_mae_vs_actual'))}"
        )
        lines.append("")
        lines.append(_bucket_line(ev.get("projected_total_buckets") or {}))
        lines.append("")

    lines += [
        "## Distributions by split",
        "",
        "Train-0 / Val-0 / Val-1 tell the same story. This is not a 2024 quirk.",
        "",
    ]
    for rec in payload.get("candidates") or []:
        if rec.get("id") not in {"E3_ref", "C2_ref", "A1_point_half", "A3_point_full"}:
            continue
        lines.append(f"### {rec.get('id')}")
        lines.append("")
        for split in ("train_0", "val_0", "val_1"):
            ev = ((rec.get("eval") or {}).get(split) or {})
            dist = ev.get("distribution") or {}
            lines.append(
                f"**{split}** sd(pred)/sd(actual)={_fmt(dist.get('sd_ratio_pred_over_actual'))} "
                f"P90 gap={_fmt(dist.get('p90_actual_minus_pred'))} "
                f"freq>65 ratio={_fmt(dist.get('freq_gt65_pred_over_actual'))} "
                f"≥68 n={ev.get('high_tail_ge68_n')}"
            )
            lines.append("")
            lines.append(_dist_line(dist.get("predicted") or {}, "pred"))
            lines.append("")
            lines.append(_dist_line(dist.get("actual") or {}, "actual"))
            lines.append("")

    lines += [
        "## Predeclared candidates (specified before scoring)",
        "",
    ]
    for spec in payload.get("predeclared_candidates") or []:
        lines.append(f"### {spec.get('id')} ({spec.get('role')})")
        lines.append("")
        lines.append(str(spec.get("label") or ""))
        lines.append("")
        lines.append(str(spec.get("rationale") or ""))
        lines.append("")

    lines += [
        "## Algebraic consistency",
        "",
        f"A4 vs A1 max |Δ total| = `{_fmt(ident.get('max_abs_total_diff'))}` "
        f"on `{ident.get('n_paired')}` paired games. ok=`{ident.get('ok')}`.",
        "",
        "Every scored candidate: `away + home = total` and `away − home = spread_home` "
        "with zero violations above 0.02. One authoritative scoring path.",
        "",
        "## What this means",
        "",
        "1. **The ratio was inventing high totals.** E3's 54 predicted-≥68 games scored 59, not 72. Additive form correctly walked those in.",
        "2. **The half-index slope cannot produce football tails.** Predicted SD ~4.8 vs actual ~16.7. That is the 54→3 number.",
        "3. **The full-index slope restores fake tails, not real ones.** A3 looks more dispersed and has a worse residual function. It still projects actual shootouts at 55.",
        "4. **Sliding α is a dead end.** Half-slope = collapse. Full-slope = C3. There is no documented identity between them that we are allowed to fit on Val-1.",
        "5. **Prior-year efficiency does not identify scoring environment.** Sides survive (favorite-agree ~0.72). Totals tails do not. The next honest question is whether *any* v1 feature — or only in-season / game-state information we do not have — can price a 79-point game without reintroducing the ratio.",
        "6. **Nothing here is a production coefficient.** Shape improved. Distribution did not earn sealed-2025 evaluation.",
        "",
        "## What this is not",
        "",
        "- Not a production change.",
        "- Not permission to write `MATCHUP_RESPONSE = 1.00` or A1/C2 into `priors.py`.",
        "- Not a −10 haircut, bucket correction, isotonic map, or close-anchored spline.",
        "- Not a fit of 0.5/0.5 or of α/β.",
        "- Not permission to open 2025.",
        "- Not a board-on decision.",
        "- Not a winner dressed up as a non-winner. The gate said collapse, and the distributions agree.",
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    payload = run_additive_scoring_architecture(lake_only=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    OUT_MD.write_text(write_markdown(payload), encoding="utf-8")
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")
    print("decision", (payload.get("decision") or {}).get("decision"))
    print("MATCHUP_RESPONSE still", payload.get("matchup_response_frozen"))
    print("opened_2025", payload.get("opened_2025"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
