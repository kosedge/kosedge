#!/usr/bin/env python3
"""Score predeclared raw O/D identities. Does not write production knobs."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_warehouse.raw_od_interaction import (  # noqa: E402
    run_raw_od_interaction,
)

OUT_JSON = ROOT / "data/ops/cfb-raw-od-interaction-20260912.json"
OUT_MD = ROOT / "data/ops/cfb-raw-od-interaction-20260912.md"


def _fmt(value: object) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def _bucket_line(card: dict) -> str:
    parts = []
    for name in ("lt_48", "48_54", "54_60", "60_68", "ge_68"):
        row = (card or {}).get(name) or {}
        parts.append(f"{name} n={row.get('n', 0)} b={_fmt(row.get('bias'))}")
    return "; ".join(parts)


def write_markdown(payload: dict) -> str:
    gate = payload.get("decision") or {}
    lines = [
        "# CFB raw O/D interaction specification",
        "",
        f"**Generated:** `{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}`",
        f"**Production MATCHUP_RESPONSE:** `{payload.get('matchup_response_frozen')}` (unchanged)",
        f"**Kill switch:** `{payload.get('kill_switch')}`  **#532:** DO NOT MERGE",
        f"**Lake mounted:** `{payload.get('lake_mounted')}`",
        "",
        "Frozen splits unchanged: Train-0=2022, Val-0=2023, Val-1=2024 W1–14.",
        "2025 sealed. 2026 / W2 n=47 not in the loss. Actual scores are the objective.",
        "",
        "## Decision",
        "",
        f"**{gate.get('decision')}**",
        "",
        f"Ship: `{gate.get('ship')}`  Winner: `{gate.get('winner')}`",
        "",
    ]
    for why in gate.get("why") or []:
        lines.append(f"- {why}")
    lines += [
        "",
        "## Predeclared candidates",
        "",
    ]
    for spec in payload.get("predeclared_candidates") or []:
        lines.append(f"### {spec.get('id')}")
        lines.append("")
        lines.append(str(spec.get("label") or ""))
        lines.append("")
        lines.append(str(spec.get("rationale") or ""))
        lines.append("")
    lines += [
        "## E3 residual attribution (Val-1)",
        "",
    ]
    attr = ((payload.get("e3_residual_attribution") or {}).get("val_1") or {})
    lines.append(
        f"n={attr.get('n')} mean residual={_fmt(attr.get('mean_residual'))} "
        f"MAE={_fmt(attr.get('mae'))} bucket range={_fmt(attr.get('projected_total_bias_range'))}"
    )
    lines.append("")
    ols = attr.get("ols_residual_on_projected_total") or {}
    lines.append(
        f"OLS residual ~ projected total: slope={_fmt(ols.get('slope'))} "
        f"intercept={_fmt(ols.get('intercept'))} r²={_fmt(ols.get('r2'))}"
    )
    lines.append("")
    scale = attr.get("scale") or {}
    lines.append(
        f"Scale: mean off_eff={_fmt(scale.get('mean_off_eff'))} "
        f"mean def_eff={_fmt(scale.get('mean_def_eff'))} "
        f"mean raw ratio={_fmt(scale.get('mean_raw_ratio'))} "
        f"composed off−def={_fmt(scale.get('mean_composed_off_minus_def'))}"
    )
    lines.append("")
    lines.append("Projected-total buckets: " + _bucket_line(attr.get("projected_total_buckets") or {}))
    lines.append("")
    lines.append("O/D interaction:")
    lines.append("")
    for name, row in (attr.get("od_interaction") or {}).items():
        lines.append(
            f"- {name}: n={row.get('n')} bias={_fmt(row.get('bias'))} "
            f"mae={_fmt(row.get('mae'))} model={_fmt(row.get('mean_model'))}"
        )
    lines += [
        "",
        "## Candidate scorecards",
        "",
        "| id | Train-0 MAE / bias / range | Val-0 MAE / bias / range | Val-1 MAE / bias / range / fav |",
        "| --- | --- | --- | --- |",
    ]
    for rec in payload.get("candidates") or []:
        t0 = (rec.get("splits") or {}).get("train_0") or {}
        v0 = (rec.get("splits") or {}).get("val_0") or {}
        v1 = (rec.get("splits") or {}).get("val_1") or {}
        s0 = (rec.get("shape") or {}).get("train_0") or {}
        sv0 = (rec.get("shape") or {}).get("val_0") or {}
        sv1 = (rec.get("shape") or {}).get("val_1") or {}
        lines.append(
            "| {id} | {t0m} / {t0b} / {t0r} | {v0m} / {v0b} / {v0r} | {v1m} / {v1b} / {v1r} / {fav} |".format(
                id=rec.get("id"),
                t0m=_fmt(t0.get("total_mae_vs_actual")),
                t0b=_fmt(t0.get("total_bias_vs_actual")),
                t0r=_fmt(s0.get("projected_total_bias_range")),
                v0m=_fmt(v0.get("total_mae_vs_actual")),
                v0b=_fmt(v0.get("total_bias_vs_actual")),
                v0r=_fmt(sv0.get("projected_total_bias_range")),
                v1m=_fmt(v1.get("total_mae_vs_actual")),
                v1b=_fmt(v1.get("total_bias_vs_actual")),
                v1r=_fmt(sv1.get("projected_total_bias_range")),
                fav=_fmt(v1.get("favorite_agree_vs_close")),
            )
        )
    lines += [
        "",
        "## What this is not",
        "",
        "- Not a production coefficient.",
        "- Not permission to write `MATCHUP_RESPONSE = 1.00`.",
        "- Not a −10 haircut or a projected-total spline.",
        "- Not a board-on decision.",
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    payload = run_raw_od_interaction(lake_only=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    OUT_MD.write_text(write_markdown(payload), encoding="utf-8")
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")
    print("decision", (payload.get("decision") or {}).get("decision"))
    print("MATCHUP_RESPONSE still", payload.get("matchup_response_frozen"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
