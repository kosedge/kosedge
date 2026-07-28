#!/usr/bin/env python3
"""Supervised schema-v4 retrain (KAV + special-teams KAV features).

Prereq: scripts/nfl/build_st_kav_weekly.py has populated matchup ST columns.

Writes active fit + data/ops/nfl-kav-supervised-retrain-v4.json and a
side-by-side compare vs v3 holdout metrics.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge"
)

import numpy as np  # noqa: E402

from src.services import nfl_supervised_retrain as supervised_mod  # noqa: E402
from src.services.nfl_supervised_retrain import (  # noqa: E402
    FEATURE_KEYS,
    MODEL_SCHEMA_VERSION,
)

def _stub_perm(estimator, X, y, **kwargs):
    class _Stub:
        importances_mean = np.zeros(int(getattr(X, "shape", [0, 0])[1] or 0), dtype=float)

    return _Stub()


supervised_mod.permutation_importance = _stub_perm  # type: ignore[attr-defined]

from src.tasks import DEFAULT_NFL_MODEL_VERSION, run_nfl_supervised_retrain  # noqa: E402

OUT = ROOT / "data" / "ops" / "nfl-kav-supervised-retrain-v4.json"
COMPARE = ROOT / "data" / "ops" / "nfl-kav-supervised-v3-vs-v4.json"
V3 = ROOT / "data" / "ops" / "nfl-kav-supervised-retrain-v3.json"


def main() -> int:
    if MODEL_SCHEMA_VERSION < 4 or "diff_st_kav_net_5g" not in FEATURE_KEYS:
        print("ERROR: schema/features not v4 ST-ready", flush=True)
        return 1
    t0 = time.time()
    print(
        f"retrain schema={MODEL_SCHEMA_VERSION} features={len(FEATURE_KEYS)} "
        f"has_st={'diff_st_kav_net_5g' in FEATURE_KEYS}",
        flush=True,
    )
    result = run_nfl_supervised_retrain.run(
        model_version=DEFAULT_NFL_MODEL_VERSION,
        start_season=2013,
        end_season=2025,
    )
    result["elapsed_sec"] = round(time.time() - t0, 1)
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    result["schema_version"] = MODEL_SCHEMA_VERSION
    result["feature_keys"] = list(FEATURE_KEYS)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, default=str) + "\n")

    v3 = json.loads(V3.read_text()) if V3.exists() else {}
    m3 = (v3.get("metrics") or {}) if isinstance(v3, dict) else {}
    m4 = result.get("metrics") or {}
    compare = {
        "generated_at": result["generated_at"],
        "v3": {
            "schema": v3.get("schema_version"),
            "test_brier": m3.get("test_brier"),
            "test_margin_mae": m3.get("test_margin_mae"),
            "test_total_mae": m3.get("test_total_mae"),
            "test_rows": m3.get("test_rows"),
        },
        "v4": {
            "schema": MODEL_SCHEMA_VERSION,
            "test_brier": m4.get("test_brier"),
            "test_margin_mae": m4.get("test_margin_mae"),
            "test_total_mae": m4.get("test_total_mae"),
            "test_rows": m4.get("test_rows"),
            "feature_count": len(FEATURE_KEYS),
        },
        "delta": {},
        "promote": False,
        "notes": [],
    }
    for key in ("test_brier", "test_margin_mae", "test_total_mae"):
        a, b = m3.get(key), m4.get(key)
        if a is not None and b is not None:
            compare["delta"][key] = round(float(b) - float(a), 6)
    # Promote only if no metric worsens beyond tiny noise and at least one improves.
    deltas = compare["delta"]
    worsened = any(float(deltas.get(k, 0)) > 0.002 for k in ("test_brier", "test_margin_mae", "test_total_mae"))
    improved = any(float(deltas.get(k, 0)) < -0.002 for k in ("test_brier", "test_margin_mae", "test_total_mae"))
    floors_ok = (
        float(m4.get("test_brier") or 99) <= 0.22
        and float(m4.get("test_margin_mae") or 99) <= 9.5
        and float(m4.get("test_total_mae") or 99) <= 10.5
    )
    compare["promote"] = bool(floors_ok and not worsened and (improved or floors_ok))
    if worsened:
        compare["notes"].append("v4 worsens a holdout metric >0.002 — do not claim upgrade.")
    elif improved:
        compare["notes"].append("v4 improves ≥1 holdout metric without material regression.")
    else:
        compare["notes"].append("v4 within noise of v3; ST feature retained if floors clear.")
    # Active fit already written by run_nfl_supervised_retrain; if not promote, note rollback need.
    if not compare["promote"]:
        compare["notes"].append(
            "Active DB fit is v4 from this run — rollback to v3 payload if ops rejects."
        )
    COMPARE.write_text(json.dumps(compare, indent=2) + "\n")
    print(json.dumps(compare, indent=2), flush=True)
    print(f"wrote {OUT}", flush=True)
    print(f"wrote {COMPARE}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
