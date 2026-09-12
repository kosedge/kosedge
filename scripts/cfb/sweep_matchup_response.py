#!/usr/bin/env python3
"""MATCHUP_RESPONSE-only sweep on the legal 2022–24 v1 universe.

Does not change production MATCHUP_RESPONSE=1.40.
Does not unseal 2025. Does not use 2026 for selection. Does not publish PLAY.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "services/model-service"))

from src.services.cfb_season_engine.priors import MATCHUP_RESPONSE  # noqa: E402
from src.services.cfb_season_engine.qb_feature_contract import (  # noqa: E402
    QB_FEATURE_CONTRACT_VERSION,
)
from src.services.cfb_warehouse.matchup_response_sweep import (  # noqa: E402
    FROZEN_RESPONSE,
    run_matchup_response_sweep,
)

OPS_MD = REPO / "data/ops/cfb-matchup-response-sweep-20260912.md"
OPS_JSON = REPO / "data/ops/cfb-matchup-response-sweep-20260912.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fmt(val: Any, digits: int = 3) -> str:
    if val is None:
        return "—"
    if isinstance(val, float):
        return f"{val:.{digits}f}"
    return str(val)


def _delta(val: Any, base: Any, digits: int = 3) -> str:
    if val is None or base is None:
        return "—"
    try:
        return f"{float(val) - float(base):+.{digits}f}"
    except (TypeError, ValueError):
        return "—"


def _sensitivity_table(candidates: List[Mapping[str, Any]]) -> str:
    header = (
        "| r | phase | Train-0 n / MAE / bias | Val-0 n / MAE / bias | "
        "Val-1 n / MAE / RMSE / bias / MedAE | Val-1 vs close bias / "
        "|m−c| | tail n / act-bias / close-bias | ATS / ROI |"
    )
    lines = [
        header,
        "| ---: | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for rec in candidates:
        splits = rec.get("splits") or {}
        t0 = splits.get("train_0") or {}
        v0 = splits.get("val_0") or {}
        v1 = splits.get("val_1") or {}
        lines.append(
            "| {r:.2f} | {phase} | {t0} | {v0} | {v1} | {close} | {tail} | {ats} |".format(
                r=float(rec["matchup_response"]),
                phase=rec.get("phase") or "",
                t0="{n} / {mae} / {bias}".format(
                    n=t0.get("n", 0),
                    mae=_fmt(t0.get("mae_vs_actual")),
                    bias=_fmt(t0.get("bias_vs_actual")),
                ),
                v0="{n} / {mae} / {bias}".format(
                    n=v0.get("n", 0),
                    mae=_fmt(v0.get("mae_vs_actual")),
                    bias=_fmt(v0.get("bias_vs_actual")),
                ),
                v1="{n} / {mae} / {rmse} / {bias} / {med}".format(
                    n=v1.get("n", 0),
                    mae=_fmt(v1.get("mae_vs_actual")),
                    rmse=_fmt(v1.get("rmse_vs_actual")),
                    bias=_fmt(v1.get("bias_vs_actual")),
                    med=_fmt(v1.get("medae_vs_actual")),
                ),
                close="{bias} / {dis}".format(
                    bias=_fmt(v1.get("bias_vs_close")),
                    dis=_fmt(v1.get("mean_abs_disagree_total")),
                ),
                tail="{n} / {ab} / {cb}".format(
                    n=v1.get("high_tail_n", 0),
                    ab=_fmt(v1.get("high_tail_bias_vs_actual")),
                    cb=_fmt(v1.get("high_tail_bias_vs_close")),
                ),
                ats="{hit} / {roi}".format(
                    hit=_fmt(v1.get("ats_hit_rate"), 3),
                    roi=_fmt(v1.get("ats_roi_minus_110"), 3),
                ),
            )
        )
    return "\n".join(lines)


def _compare_table(cmp: Optional[Mapping[str, Any]]) -> str:
    if not cmp:
        return "_No comparison available._"
    lines = [
        "| Metric | candidate | frozen 1.40 | Δ |",
        "| --- | ---: | ---: | ---: |",
    ]
    labels = [
        ("n", "n"),
        ("mae_vs_actual", "MAE vs actual"),
        ("rmse_vs_actual", "RMSE vs actual"),
        ("bias_vs_actual", "bias vs actual"),
        ("medae_vs_actual", "MedAE vs actual"),
        ("bias_vs_close", "bias vs close (diagnostic)"),
        ("mae_vs_close", "MAE vs close (diagnostic)"),
        ("mean_abs_disagree_total", "mean |model−close|"),
        ("high_tail_n", "high-tail n (≥68)"),
        ("high_tail_bias_vs_actual", "high-tail bias vs actual"),
        ("high_tail_bias_vs_close", "high-tail bias vs close"),
        ("mean_model_total", "mean model total"),
        ("mean_actual_total", "mean actual total"),
        ("mean_close_total", "mean close total"),
        ("ats_hit_rate", "ATS hit"),
        ("ats_roi_minus_110", "ATS ROI −110"),
        ("margin_mae_vs_actual", "margin MAE vs actual"),
    ]
    for key, label in labels:
        row = cmp.get(key) or {}
        lines.append(
            f"| {label} | {_fmt(row.get('candidate'))} | "
            f"{_fmt(row.get('frozen_140'))} | {_fmt(row.get('delta'))} |"
        )
    return "\n".join(lines)


def _bucket_table(card: Mapping[str, Any]) -> str:
    buckets = card.get("total_disagree_buckets") or {}
    if not buckets:
        return "_No disagreement buckets._"
    lines = [
        "| |model−close| bucket | n | MAE vs actual | bias vs actual | ATS |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name, brow in buckets.items():
        lines.append(
            "| {name} | {n} | {mae} | {bias} | {ats} |".format(
                name=name,
                n=brow.get("n", 0),
                mae=_fmt(brow.get("mae_vs_actual")),
                bias=_fmt(brow.get("bias_vs_actual")),
                ats=_fmt(brow.get("ats_hit_rate")),
            )
        )
    return "\n".join(lines)


def write_report(payload: Dict[str, Any]) -> None:
    gate = payload.get("decision") or {}
    candidates = list(payload.get("candidates") or [])
    frozen = next(
        (
            r
            for r in candidates
            if abs(float(r.get("matchup_response") or 0) - FROZEN_RESPONSE) < 1e-9
        ),
        None,
    )
    recommended = gate.get("recommended")
    rec = next(
        (
            r
            for r in candidates
            if recommended is not None
            and abs(float(r.get("matchup_response") or 0) - float(recommended)) < 1e-9
        ),
        None,
    )
    lines: List[str] = [
        "# MATCHUP_RESPONSE coefficient sweep (v1 universe)",
        "",
        f"**Generated:** `{payload.get('generated_at')}`  ",
        f"**Contract:** `{QB_FEATURE_CONTRACT_VERSION}`  ",
        f"**Production MATCHUP_RESPONSE:** `{MATCHUP_RESPONSE}` (unchanged)  ",
        "**Sweep:** score-time overlay only. Early-season soften still applies.  ",
        "**Primary objective:** actual outcomes. Close is a benchmark, not the target.  ",
        "**Kill switch:** ON. 2025 sealed. 2026 not in the loss. No PLAY. No Line Curve.",
        "",
        "## Decision",
        "",
        f"**{gate.get('decision')}**",
        "",
    ]
    if recommended is not None:
        lines.append(f"Recommended coefficient (research only): **{recommended:.2f}**")
        lines.append("")
    region = gate.get("best_region") or {}
    if region:
        lines.append("Best-candidate region:")
        lines.append("")
        for key, val in region.items():
            lines.append(f"- `{key}` = `{val}`")
        lines.append("")
    for why in gate.get("why") or []:
        lines.append(f"- {why}")
    lines += [
        "",
        "Production `priors.MATCHUP_RESPONSE` was **not** written. "
        "CFB remains dark. 2025 remains sealed.",
        "",
        "## Sensitivity table",
        "",
        "MAE / bias columns are **vs actual** unless labeled close. "
        "Do not read a smaller |model−close| as a better football model.",
        "",
        _sensitivity_table(candidates),
        "",
        "## Comparison vs frozen 1.40 (Val-1)",
        "",
        _compare_table(gate.get("comparison_vs_140")),
        "",
        "## Tail inflation",
        "",
    ]
    if rec and frozen:
        v1 = (rec.get("splits") or {}).get("val_1") or {}
        f1 = (frozen.get("splits") or {}).get("val_1") or {}
        lines += [
            f"Candidate `{rec.get('matchup_response')}` high-tail n="
            f"`{v1.get('high_tail_n')}` bias vs actual "
            f"`{_fmt(v1.get('high_tail_bias_vs_actual'))}` "
            f"(vs close `{_fmt(v1.get('high_tail_bias_vs_close'))}`).",
            "",
            f"Frozen 1.40 high-tail n=`{f1.get('high_tail_n')}` bias vs actual "
            f"`{_fmt(f1.get('high_tail_bias_vs_actual'))}` "
            f"(vs close `{_fmt(f1.get('high_tail_bias_vs_close'))}`).",
            "",
            "Δ tail n "
            f"`{_delta(v1.get('high_tail_n'), f1.get('high_tail_n'), 0)}`; "
            "Δ tail bias vs actual "
            f"`{_delta(v1.get('high_tail_bias_vs_actual'), f1.get('high_tail_bias_vs_actual'))}`.",
            "",
        ]
    elif frozen:
        f1 = (frozen.get("splits") or {}).get("val_1") or {}
        lines += [
            "No earned candidate. Frozen 1.40 tail remains the reference:",
            "",
            f"- n=`{f1.get('high_tail_n')}`",
            f"- bias vs actual `{_fmt(f1.get('high_tail_bias_vs_actual'))}`",
            f"- bias vs close `{_fmt(f1.get('high_tail_bias_vs_close'))}`",
            "",
        ]
    if rec:
        lines += [
            "### Val-1 disagreement buckets (candidate)",
            "",
            _bucket_table((rec.get("splits") or {}).get("val_1") or {}),
            "",
        ]
    if frozen:
        lines += [
            "### Val-1 disagreement buckets (frozen 1.40)",
            "",
            _bucket_table((frozen.get("splits") or {}).get("val_1") or {}),
            "",
        ]
    lines += [
        "## Provenance / limits",
        "",
        f"- lake mounted: `{payload.get('lake_mounted')}`",
        f"- lake locate: `{json.dumps(payload.get('lake_locate') or {}, default=str)[:1200]}`",
        f"- Layer A talent: `{payload.get('layer_a_talent')}`",
        f"- sanity: `{json.dumps((gate.get('sanity') or {}), default=str)[:800]}`",
        "",
    ]
    for note in payload.get("reconstruction_limits") or []:
        lines.append(f"- {note}")
    lines += [
        "",
        "## GO / STOP",
        "",
        f"**{gate.get('decision')}**",
        "",
        "STOP. Do not touch 2025, 2026, production CFB, PLAY labels, or Line Curve. "
        "Do not write a new production coefficient in this assignment.",
        "",
    ]
    OPS_MD.parent.mkdir(parents=True, exist_ok=True)
    OPS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    if MATCHUP_RESPONSE != 1.40:
        raise SystemExit(f"MATCHUP_RESPONSE drifted: {MATCHUP_RESPONSE}")
    payload = run_matchup_response_sweep(lake_only=True)
    payload["generated_at"] = _utc()
    write_report(payload)
    OPS_JSON.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ops_md": str(OPS_MD),
                "ops_json": str(OPS_JSON),
                "decision": payload.get("decision"),
                "n_candidates": len(payload.get("candidates") or []),
                "matchup_response_still": MATCHUP_RESPONSE,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
