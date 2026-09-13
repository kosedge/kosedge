#!/usr/bin/env python3
"""Run E1–E5 matchup-architecture holdout. Does not write production knobs."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_warehouse.matchup_architecture_holdout import (  # noqa: E402
    run_matchup_architecture_holdout,
)

OUT_JSON = ROOT / "data/ops/cfb-matchup-architecture-holdout-20260912.json"
OUT_MD = ROOT / "data/ops/cfb-matchup-architecture-holdout-20260912.md"


def _fmt(value: object) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def write_markdown(payload: dict) -> str:
    gate = payload.get("decision") or {}
    lines = [
        "# CFB matchup-architecture holdout (E1–E5)",
        "",
        f"**Generated:** `{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}`",
        f"**Production MATCHUP_RESPONSE:** `{payload.get('matchup_response_frozen')}` (unchanged)",
        f"**Kill switch:** `{payload.get('kill_switch')}`  **#532:** DO NOT MERGE",
        f"**Lake mounted:** `{payload.get('lake_mounted')}`",
        "",
        "Frozen splits (pre-registered, not changed after seeing scores):",
        "",
        "* Train-0 = 2022 W1–14",
        "* Val-0 = 2023 W1–14",
        "* Val-1 = 2024 W1–14 (untouched holdout)",
        "",
        "2025 sealed. 2026 / W2 n=47 is not in this loss. Close is diagnostic.",
        "",
        "## Decision",
        "",
        f"**{gate.get('decision')}**",
        "",
        f"Ship: `{gate.get('ship')}`  Recommended coefficient: `{gate.get('recommended_coefficient')}`",
        "",
    ]
    for why in gate.get("why") or []:
        lines.append(f"- {why}")
    lines += [
        "",
        "## Experiment cards",
        "",
        "Actual-primary. Do not read a smaller |model−close| as a better football model.",
        "",
        "| id | Train-0 n / MAE / bias | Val-0 n / MAE / bias | Val-1 n / MAE / bias / fav-agree | Val-1 close bias | tail n |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for rec in payload.get("experiments") or []:
        t0 = (rec.get("splits") or {}).get("train_0") or {}
        v0 = (rec.get("splits") or {}).get("val_0") or {}
        v1 = (rec.get("splits") or {}).get("val_1") or {}
        lines.append(
            "| {id} | {t0n} / {t0m} / {t0b} | {v0n} / {v0m} / {v0b} | {v1n} / {v1m} / {v1b} / {fav} | {cb} | {tail} |".format(
                id=rec.get("id"),
                t0n=_fmt(t0.get("n")),
                t0m=_fmt(t0.get("total_mae_vs_actual")),
                t0b=_fmt(t0.get("total_bias_vs_actual")),
                v0n=_fmt(v0.get("n")),
                v0m=_fmt(v0.get("total_mae_vs_actual")),
                v0b=_fmt(v0.get("total_bias_vs_actual")),
                v1n=_fmt(v1.get("n")),
                v1m=_fmt(v1.get("total_mae_vs_actual")),
                v1b=_fmt(v1.get("total_bias_vs_actual")),
                fav=_fmt(v1.get("favorite_agree_vs_close")),
                cb=_fmt(v1.get("total_bias_vs_close")),
                tail=_fmt(v1.get("high_tail_n")),
            )
        )
    lines += [
        "",
        "## Year stability (baseline vs E1)",
        "",
        "| season | baseline bias / MAE / fav-agree | E1 bias / MAE / fav-agree |",
        "| --- | --- | --- |",
    ]
    by_id = {r["id"]: r for r in payload.get("experiments") or []}
    base = by_id.get("baseline_140") or {}
    e1 = by_id.get("E1_response_1.00") or {}
    seasons = sorted(
        set((base.get("by_season") or {}).keys()) | set((e1.get("by_season") or {}).keys())
    )
    for season in seasons:
        b = (base.get("by_season") or {}).get(season) or {}
        e = (e1.get("by_season") or {}).get(season) or {}
        lines.append(
            f"| {season} | {_fmt(b.get('total_bias_vs_actual'))} / {_fmt(b.get('total_mae_vs_actual'))} / {_fmt(b.get('favorite_agree_vs_close'))} | {_fmt(e.get('total_bias_vs_actual'))} / {_fmt(e.get('total_mae_vs_actual'))} / {_fmt(e.get('favorite_agree_vs_close'))} |"
        )
    lines += [
        "",
        "## What this is not",
        "",
        "- Not a production coefficient change.",
        "- Not a −10 totals haircut.",
        "- Not a fit to the W2 47-game DK snapshot.",
        "- Not permission to turn the board on.",
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    payload = run_matchup_architecture_holdout(lake_only=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    OUT_MD.write_text(write_markdown(payload), encoding="utf-8")
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")
    print("lake_mounted", payload.get("lake_mounted"))
    print("decision", (payload.get("decision") or {}).get("decision"))
    print("production MATCHUP_RESPONSE still", payload.get("matchup_response_frozen"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
