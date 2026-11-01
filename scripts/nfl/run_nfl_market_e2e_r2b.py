#!/usr/bin/env python3
"""Consume sealed R2-A quotes for market E2E. Does not invoke EVAL."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/model-service"))

from src.services.nfl_t5107u.r2_market_e2e import (  # noqa: E402
    DEFAULT_DEST,
    default_outcome_loader,
    run_market_e2e,
)


def main() -> int:
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DEST
    eval_rec = run_market_e2e(split="eval", emit_metrics=False)
    dev_rec = run_market_e2e(split="dev_reg", emit_metrics=False)
    matched = [p["game_id"] for p in dev_rec["market_points"]]
    loader = default_outcome_loader(matched)
    matched_rec = run_market_e2e(
        split="dev_reg",
        eligible_ids=matched,
        outcome_loader=loader,
        emit_metrics=True,
    )
    receipt = {
        "schema_version": "nfl-t5119u-r2b-market-e2e-receipt-v1",
        "cert_candidate": 0,
        "eval": None,
        "eval_invoked": False,
        "one_run_claim": False,
        "r2a_tip": "3821941d758feb7ba05e680da6ecec283291dd2a",
        "cos_accept": "770f72da",
        "cos_order": "e7330717",
        "eval_cohort": {
            "eligible_n": eval_rec["eligible_n"],
            "joined_n": eval_rec["joined_n"],
            "missing_n": eval_rec["missing_n"],
            "bind_ready": eval_rec["bind_ready"],
        },
        "dev_reg_cohort": {
            "eligible_n": dev_rec["eligible_n"],
            "joined_n": dev_rec["joined_n"],
            "missing_n": dev_rec["missing_n"],
            "bind_ready": dev_rec["bind_ready"],
        },
        "dev_matched_subset": {
            "eligible_n": matched_rec["eligible_n"],
            "joined_n": matched_rec["joined_n"],
            "bind_ready": matched_rec["bind_ready"],
            "mae_market": matched_rec["market_contract"].get("mae_market"),
            "rmse_market": matched_rec["market_contract"].get("rmse_market"),
            "bias_market": matched_rec["market_contract"].get("bias_market"),
        },
        "market_ready_for_eval_bind": False,
        "market_ready_for_dev_matched_bind": bool(matched_rec["bind_ready"]),
        "reason": (
            "EVAL 449 incomplete (95/449). DEV 437 incomplete (72/437). "
            "DEV matched 72 has sealed market_margin. No EVAL invoked."
        ),
        "g5_loosened": False,
        "notes": eval_rec["notes"],
    }
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        raise SystemExit(f"refusing overwrite {dest}")
    dest.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(dest), "eval_bind_ready": False, "dev_matched_bind_ready": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
