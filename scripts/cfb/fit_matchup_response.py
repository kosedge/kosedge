#!/usr/bin/env python3
"""Authorized MATCHUP_RESPONSE coefficient-fit on the #543 v1 universe.

Does not change production priors. Does not unseal 2025. Does not use 2026
in the loss. Does not publish PLAY.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "services/model-service"))

from src.services.cfb_season_engine import priors as P  # noqa: E402
from src.services.cfb_season_engine.priors import MATCHUP_RESPONSE  # noqa: E402
from src.services.cfb_season_engine.qb_feature_contract import (  # noqa: E402
    QB_FEATURE_CONTRACT_VERSION,
)
from src.services.cfb_warehouse.matchup_response_fit import (  # noqa: E402
    PRODUCTION_MATCHUP_RESPONSE,
    run_matchup_response_fit,
)

OPS_MD = REPO / "data/ops/cfb-matchup-response-fit-20260912.md"
OPS_JSON = REPO / "data/ops/cfb-matchup-response-fit-20260912.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fmt(val: Any, digits: int = 3) -> str:
    if val is None:
        return "—"
    if isinstance(val, float):
        return f"{val:.{digits}f}"
    return str(val)


def _sensitivity_table(rows: List[Dict[str, Any]], split: str) -> str:
    lines = [
        "| r | n | tot act MAE | tot act bias | tot close bias | tail act bias | mgn act MAE | |spr| | ATS | O/U | loss |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        block = row.get(split) or {}
        tail = block.get("frozen140_high_tail") or {}
        lines.append(
            "| {r} | {n} | {mae} | {bias} | {cbias} | {tb} | {smae} | {asp} | {ats} | {ou} | {loss} |".format(
                r=_fmt(row.get("matchup_response"), 2),
                n=block.get("n", 0),
                mae=_fmt(block.get("total_vs_actual_mae")),
                bias=_fmt(block.get("total_vs_actual_bias")),
                cbias=_fmt(block.get("total_vs_close_bias")),
                tb=_fmt(tail.get("total_vs_actual_bias")),
                smae=_fmt(block.get("margin_vs_actual_mae")),
                asp=_fmt(block.get("mean_abs_model_spread")),
                ats=_fmt(block.get("ats_hit_rate")),
                ou=_fmt(block.get("ou_hit_rate")),
                loss=_fmt(block.get("primary_loss")),
            )
        )
    return "\n".join(lines)


def write_report(payload: Dict[str, Any]) -> None:
    gate = payload.get("decision") or {}
    selected = payload.get("selected")
    lines: List[str] = [
        "# CFB MATCHUP_RESPONSE coefficient-fit",
        "",
        f"**Generated:** `{payload['generated_at']}`  ",
        f"**Contract:** `{QB_FEATURE_CONTRACT_VERSION}`  ",
        f"**Production MATCHUP_RESPONSE:** `{PRODUCTION_MATCHUP_RESPONSE}` (unchanged)  ",
        f"**Authoritative recovery:** PR #{payload.get('authoritative_recovery_pr')}  ",
        "**Kill switch:** ON. 2025 sealed. 2026 not in the loss. No PLAY.",
        "",
        "## Decision",
        "",
        f"**{gate.get('decision')}**",
        "",
        f"Train-1 selected candidate: `{_fmt(selected, 2)}`. "
        "That number is **not** written into `priors.py`.",
        "",
    ]
    for why in gate.get("why") or []:
        lines.append(f"- {why}")
    flags = gate.get("flags") or []
    if flags:
        lines += ["", "Flags:", ""]
        for flag in flags:
            lines.append(f"- {flag}")
    lines += [
        "",
        "Primary ranking uses **actuals**. Close is a diagnostic. "
        "ATS/ROI cannot override a failed MAE/bias gate.",
        "",
        "## Sensitivity — Val-1 (decision)",
        "",
        _sensitivity_table(payload.get("sensitivity") or [], "val_1"),
        "",
        "## Sensitivity — Train-1 (fit window)",
        "",
        _sensitivity_table(payload.get("sensitivity") or [], "train_1"),
        "",
        "## Sensitivity — Val-0",
        "",
        _sensitivity_table(payload.get("sensitivity") or [], "val_0"),
        "",
        "## Sensitivity — Train-0",
        "",
        _sensitivity_table(payload.get("sensitivity") or [], "train_0"),
        "",
        "## Baseline frozen 1.40",
        "",
        json.dumps(payload.get("baseline_1_40") or {}, indent=2),
        "",
        "## Provenance / limits",
        "",
        f"- lake locate: `{json.dumps(payload.get('lake_locate') or {}, default=str)[:1200]}`",
        f"- frozen 1.40 high-tail n: `{payload.get('frozen140_high_tail_n')}`",
        f"- skipped: `{payload.get('skipped')}`",
        "",
    ]
    for note in payload.get("notes") or []:
        lines.append(f"- {note}")
    lines += [
        "",
        "## GO / STOP",
        "",
        f"**{gate.get('decision')}**",
        "",
        "Do not write the candidate into production. Do not unseal 2025. "
        "Do not publish a CFB board or PLAY designation.",
        "",
    ]
    OPS_MD.parent.mkdir(parents=True, exist_ok=True)
    OPS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    if float(P.MATCHUP_RESPONSE) != PRODUCTION_MATCHUP_RESPONSE:
        raise SystemExit(f"MATCHUP_RESPONSE drifted: {P.MATCHUP_RESPONSE}")
    payload = run_matchup_response_fit(lake_only=True)
    payload["generated_at"] = _utc()
    if float(P.MATCHUP_RESPONSE) != PRODUCTION_MATCHUP_RESPONSE:
        raise SystemExit("MATCHUP_RESPONSE leaked after fit")
    write_report(payload)
    OPS_JSON.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ops_md": str(OPS_MD),
                "ops_json": str(OPS_JSON),
                "decision": payload.get("decision"),
                "selected": payload.get("selected"),
                "production_matchup_response": MATCHUP_RESPONSE,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
