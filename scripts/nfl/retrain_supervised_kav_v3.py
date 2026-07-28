#!/usr/bin/env python3
"""Lean supervised schema-v3 retrain (KAV FEATURE_KEYS) with fast importance stub.

Writes active row to nfl_supervised_model_fits and
data/ops/nfl-kav-supervised-retrain-v3.json.
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

OUT = ROOT / "data" / "ops" / "nfl-kav-supervised-retrain-v3.json"


def main() -> int:
    t0 = time.time()
    print(
        f"retrain schema={MODEL_SCHEMA_VERSION} features={len(FEATURE_KEYS)} "
        f"has_kav={'diff_kav_net_5g' in FEATURE_KEYS}",
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
    print(json.dumps({"metrics": result.get("metrics"), "elapsed_sec": result["elapsed_sec"]}, indent=2), flush=True)
    print(f"wrote {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
