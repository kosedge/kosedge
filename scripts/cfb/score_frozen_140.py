#!/usr/bin/env python3
"""Score frozen MATCHUP_RESPONSE=1.40 on the reconstructed v1 universe.

Does not change coefficients. Does not unseal 2025. Does not use 2026 in the loss.
Does not publish PLAY.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "services/model-service"))

from src.services.cfb_season_engine.priors import MATCHUP_RESPONSE  # noqa: E402
from src.services.cfb_season_engine.qb_feature_contract import (  # noqa: E402
    QB_FEATURE_CONTRACT_VERSION,
)
from src.services.cfb_warehouse.frozen_140_scoring import (  # noqa: E402
    HIGH_TOTAL_TAIL,
    TRAIN0_GATE,
    VAL1_GATE,
    run_frozen_140_scoring,
)

OPS_MD = REPO / "data/ops/cfb-frozen-140-scoring-20260912.md"
OPS_JSON = REPO / "data/ops/cfb-frozen-140-scoring-20260912.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fmt(val: Any, digits: int = 3) -> str:
    if val is None:
        return "—"
    if isinstance(val, float):
        return f"{val:.{digits}f}"
    return str(val)


def _metrics_table(block: Dict[str, Any]) -> str:
    keys = [
        ("n", "n"),
        ("spread_vs_close_mae", "spread vs close MAE"),
        ("spread_vs_close_rmse", "spread vs close RMSE"),
        ("spread_vs_close_bias", "spread vs close bias"),
        ("spread_vs_close_median_abs", "spread vs close MedAE"),
        ("margin_vs_actual_mae", "margin vs actual MAE"),
        ("margin_vs_actual_rmse", "margin vs actual RMSE"),
        ("margin_vs_actual_bias", "margin vs actual bias"),
        ("margin_vs_actual_median_abs", "margin vs actual MedAE"),
        ("total_vs_close_mae", "total vs close MAE"),
        ("total_vs_close_rmse", "total vs close RMSE"),
        ("total_vs_close_bias", "total vs close bias"),
        ("total_vs_close_median_abs", "total vs close MedAE"),
        ("total_vs_actual_mae", "total vs actual MAE"),
        ("total_vs_actual_rmse", "total vs actual RMSE"),
        ("total_vs_actual_bias", "total vs actual bias"),
        ("total_vs_actual_median_abs", "total vs actual MedAE"),
        ("mean_model_total", "mean model total"),
        ("mean_close_total", "mean close total"),
        ("mean_actual_total", "mean actual total"),
        ("mean_abs_model_spread", "mean |model spread|"),
        ("mean_abs_close_spread", "mean |close spread|"),
        ("ats_n", "ATS n"),
        ("ats_hit_rate", "ATS hit"),
        ("ats_roi_minus_110", "ATS ROI −110"),
        ("ou_n", "O/U n"),
        ("ou_hit_rate", "O/U hit"),
        ("ou_roi_minus_110", "O/U ROI −110"),
        ("brier_home_wp", "Brier home WP"),
    ]
    lines = ["| Metric | Value |", "| --- | ---: |"]
    for key, label in keys:
        lines.append(f"| {label} | {_fmt(block.get(key))} |")
    return "\n".join(lines)


def _slice_table(slices: Dict[str, Any], metric: str = "total_vs_close_bias") -> str:
    lines = [
        "| Slice | n | total vs close bias | total vs close MAE | spread vs close MAE | ATS | O/U |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, block in slices.items():
        lines.append(
            "| {name} | {n} | {bias} | {tmae} | {smae} | {ats} | {ou} |".format(
                name=name,
                n=block.get("n", 0),
                bias=_fmt(block.get(metric)),
                tmae=_fmt(block.get("total_vs_close_mae")),
                smae=_fmt(block.get("spread_vs_close_mae")),
                ats=_fmt(block.get("ats_hit_rate")),
                ou=_fmt(block.get("ou_hit_rate")),
            )
        )
    return "\n".join(lines)


def _bucket_table(buckets: Dict[str, Any]) -> str:
    lines = [
        "| Bucket | n | total vs close bias | total vs close MAE | mean model total | mean close total |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, block in buckets.items():
        lines.append(
            "| {name} | {n} | {bias} | {mae} | {mt} | {ct} |".format(
                name=name,
                n=block.get("n", 0),
                bias=_fmt(block.get("total_vs_close_bias")),
                mae=_fmt(block.get("total_vs_close_mae")),
                mt=_fmt(block.get("mean_model_total")),
                ct=_fmt(block.get("mean_close_total")),
            )
        )
    return "\n".join(lines)


def write_report(payload: Dict[str, Any]) -> None:
    metrics = payload["metrics"]
    gate = payload["decision"]
    val1 = (metrics.get("splits") or {}).get("val_1") or {}
    train0 = (metrics.get("splits") or {}).get("train_0") or {}
    lines: List[str] = [
        "# Frozen MATCHUP_RESPONSE=1.40 scoring (v1 universe)",
        "",
        f"**Generated:** `{payload['generated_at']}`  ",
        f"**Contract:** `{QB_FEATURE_CONTRACT_VERSION}`  ",
        f"**MATCHUP_RESPONSE:** `{MATCHUP_RESPONSE}` frozen; scored, not changed  ",
        f"**Primary label set:** owned Odds-API lake close+actual (lake_only=`{payload['lake_only']}`)  ",
        "**Kill switch:** ON. 2025 sealed. 2026 not in the loss. No PLAY.",
        "",
        "## Decision",
        "",
        f"**{gate['decision']}**",
        "",
    ]
    for why in gate.get("why") or []:
        lines.append(f"- {why}")
    lines += [
        "",
        f"Train-0 n=`{train0.get('n', 0)}` (gate {TRAIN0_GATE}). "
        f"Val-1 n=`{val1.get('n', 0)}` (gate {VAL1_GATE}).",
        "",
        "Coefficients were **not** moved. Recalibration is **not** performed here.",
        "CFB remains dark.",
        "",
        "## Does the inflation / high-tail pathology persist?",
        "",
        "Previously observed under *live 2026 v1 serve* (not this hist reconstruction):",
        "",
        json.dumps(payload.get("prior_pathology") or {}, indent=2),
        "",
        "This run scores the **same frozen 1.40 formula** on reconstructed "
        "`cfb-qb-feature-v1` Layer A (talent center ~70, not placeholder@50) "
        f"with high-tail = predicted total ≥ {HIGH_TOTAL_TAIL}.",
        "",
        f"Val-1 mean model total `{_fmt(val1.get('mean_model_total'))}` vs "
        f"close `{_fmt(val1.get('mean_close_total'))}` vs actual "
        f"`{_fmt(val1.get('mean_actual_total'))}`.",
        f"Val-1 total vs close bias `{_fmt(val1.get('total_vs_close_bias'))}`.",
        f"Val-1 high-tail n=`{(val1.get('slices') or {}).get('high_total_tail_ge_68', {}).get('n', 0)}` "
        f"bias `{_fmt((val1.get('slices') or {}).get('high_total_tail_ge_68', {}).get('total_vs_close_bias'))}`.",
        "",
        "## Forward-chain splits",
        "",
    ]
    for name in ("train_0", "val_0", "train_1", "val_1"):
        block = (metrics.get("splits") or {}).get(name) or {}
        lines += [
            f"### {name}",
            "",
            _metrics_table(block),
            "",
            "Slices:",
            "",
            _slice_table(block.get("slices") or {}),
            "",
            "Projected-total buckets:",
            "",
            _bucket_table(block.get("projected_total_buckets") or {}),
            "",
            "Model-vs-close spread disagreement buckets:",
            "",
            _bucket_table(block.get("spread_disagree_buckets") or {}),
            "",
        ]
    lines += [
        "## Year-by-year",
        "",
    ]
    for year, block in (metrics.get("by_season") or {}).items():
        lines += [
            f"### {year}",
            "",
            _metrics_table(block),
            "",
            _slice_table(block.get("slices") or {}),
            "",
        ]
    lines += [
        "## Provenance / limits",
        "",
        f"- lake locate: `{json.dumps(payload.get('lake_locate') or {}, default=str)[:1200]}`",
        f"- Layer A talent means: `{payload.get('layer_a_talent')}`",
        f"- skipped: `{payload.get('skipped')}`",
        f"- identity/option: `{metrics.get('identity_option_slice')}`",
        "",
    ]
    for note in payload.get("reconstruction_limits") or []:
        lines.append(f"- {note}")
    lines += [
        "",
        "## GO / STOP",
        "",
        f"**{gate['decision']}**",
        "",
        "Do not recalibrate in this assignment. Do not unseal 2025. "
        "Do not publish a CFB board or PLAY designation.",
        "",
    ]
    OPS_MD.parent.mkdir(parents=True, exist_ok=True)
    OPS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    if MATCHUP_RESPONSE != 1.40:
        raise SystemExit(f"MATCHUP_RESPONSE drifted: {MATCHUP_RESPONSE}")
    payload = run_frozen_140_scoring(lake_only=True)
    payload["generated_at"] = _utc()
    write_report(payload)
    slim = dict(payload)
    slim.pop("n_joined_omitted_from_json", None)
    OPS_JSON.write_text(json.dumps(slim, indent=2, default=str) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ops_md": str(OPS_MD),
                "ops_json": str(OPS_JSON),
                "decision": payload["decision"],
                "splits_n": {
                    k: (payload["metrics"]["splits"].get(k) or {}).get("n")
                    for k in ("train_0", "val_0", "train_1", "val_1")
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
