#!/usr/bin/env python3
"""EXPERIMENTAL supervised schema-v4 retrain (KAV + special-teams KAV).

Default product path remains schema v3 (ST features NOT in FEATURE_KEYS).
This script temporarily injects ST keys, retrains, compares chronological
holdout to v3, and **rolls back the active DB fit** unless promote=True.

Prereq: scripts/nfl/build_st_kav_weekly.py

Writes:
  data/ops/nfl-kav-supervised-retrain-v4.json
  data/ops/nfl-kav-supervised-v3-vs-v4.json
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
from sqlalchemy import create_engine, text  # noqa: E402

from src.services import nfl_supervised_retrain as supervised_mod  # noqa: E402
from src.services.nfl_supervised_retrain import (  # noqa: E402
    FEATURE_KEYS,
    FEATURE_KEYS_ST_EXPERIMENTAL,
)

# Experimental keys — not in default FEATURE_KEYS (v3 product path).
FEATURE_KEYS_V4_ST = tuple(FEATURE_KEYS) + tuple(FEATURE_KEYS_ST_EXPERIMENTAL)
SCHEMA_V4 = 4


def _stub_perm(estimator, X, y, **kwargs):
    class _Stub:
        importances_mean = np.zeros(int(getattr(X, "shape", [0, 0])[1] or 0), dtype=float)

    return _Stub()


supervised_mod.permutation_importance = _stub_perm  # type: ignore[attr-defined]
# Force experimental feature set + schema for this process only.
supervised_mod.FEATURE_KEYS = FEATURE_KEYS_V4_ST  # type: ignore[attr-defined]
supervised_mod.MODEL_SCHEMA_VERSION = SCHEMA_V4  # type: ignore[attr-defined]

from src.tasks import DEFAULT_NFL_MODEL_VERSION, run_nfl_supervised_retrain  # noqa: E402
import src.tasks as tasks_mod  # noqa: E402

tasks_mod.NFL_SUPERVISED_FEATURE_KEYS = FEATURE_KEYS_V4_ST  # type: ignore[attr-defined]

OUT = ROOT / "data" / "ops" / "nfl-kav-supervised-retrain-v4.json"
COMPARE = ROOT / "data" / "ops" / "nfl-kav-supervised-v3-vs-v4.json"
V3 = ROOT / "data" / "ops" / "nfl-kav-supervised-retrain-v3.json"


def _db_url() -> str:
    url = os.environ["DATABASE_URL"]
    if url.startswith("postgresql://") and "+psycopg" not in url:
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


def _rollback_active_to_schema(schema: int = 3) -> str | None:
    """Deactivate current active fit; reactivate latest fit with schema_version."""
    engine = create_engine(_db_url())
    with engine.begin() as conn:
        prior = conn.execute(
            text(
                """
                SELECT id FROM nfl_supervised_model_fits
                WHERE model_version = :mv
                  AND (payload->>'schema_version')::int = :schema
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"mv": DEFAULT_NFL_MODEL_VERSION, "schema": schema},
        ).scalar()
        if prior is None:
            return None
        conn.execute(
            text(
                """
                UPDATE nfl_supervised_model_fits
                SET is_active = false
                WHERE model_version = :mv AND is_active = true
                """
            ),
            {"mv": DEFAULT_NFL_MODEL_VERSION},
        )
        conn.execute(
            text(
                """
                UPDATE nfl_supervised_model_fits
                SET is_active = true
                WHERE id = :id
                """
            ),
            {"id": prior},
        )
        return str(prior)


def main() -> int:
    t0 = time.time()
    print(
        f"EXPERIMENTAL retrain schema={SCHEMA_V4} features={len(FEATURE_KEYS_V4_ST)} "
        f"has_st=True (default product path remains v3)",
        flush=True,
    )
    result = run_nfl_supervised_retrain.run(
        model_version=DEFAULT_NFL_MODEL_VERSION,
        start_season=2013,
        end_season=2025,
    )
    result["elapsed_sec"] = round(time.time() - t0, 1)
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    result["schema_version"] = SCHEMA_V4
    result["feature_keys"] = list(FEATURE_KEYS_V4_ST)
    result["experimental"] = True
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, default=str) + "\n")

    v3 = json.loads(V3.read_text()) if V3.exists() else {}
    m3 = (v3.get("metrics") or {}) if isinstance(v3, dict) else {}
    m4 = result.get("metrics") or {}
    compare: dict = {
        "generated_at": result["generated_at"],
        "v3": {
            "schema": v3.get("schema_version"),
            "test_brier": m3.get("test_brier"),
            "test_margin_mae": m3.get("test_margin_mae"),
            "test_total_mae": m3.get("test_total_mae"),
            "test_rows": m3.get("test_rows"),
        },
        "v4": {
            "schema": SCHEMA_V4,
            "test_brier": m4.get("test_brier"),
            "test_margin_mae": m4.get("test_margin_mae"),
            "test_total_mae": m4.get("test_total_mae"),
            "test_rows": m4.get("test_rows"),
            "feature_count": len(FEATURE_KEYS_V4_ST),
        },
        "delta": {},
        "promote": False,
        "rolled_back_to_v3": False,
        "active_fit_id": None,
        "notes": [],
    }
    for key in ("test_brier", "test_margin_mae", "test_total_mae"):
        a, b = m3.get(key), m4.get(key)
        if a is not None and b is not None:
            compare["delta"][key] = round(float(b) - float(a), 6)

    deltas = compare["delta"]
    worsened = any(
        float(deltas.get(k, 0)) > 0.002
        for k in ("test_brier", "test_margin_mae", "test_total_mae")
    )
    improved = any(
        float(deltas.get(k, 0)) < -0.002
        for k in ("test_brier", "test_margin_mae", "test_total_mae")
    )
    floors_ok = (
        float(m4.get("test_brier") or 99) <= 0.22
        and float(m4.get("test_margin_mae") or 99) <= 9.5
        and float(m4.get("test_total_mae") or 99) <= 10.5
    )
    # Require real improvement on margin or brier (totals-only win is not enough).
    side_improved = any(
        float(deltas.get(k, 0)) < -0.002 for k in ("test_brier", "test_margin_mae")
    )
    compare["promote"] = bool(floors_ok and not worsened and side_improved)

    if worsened:
        compare["notes"].append(
            "v4 worsens holdout Brier/margin vs v3 — do not claim upgrade."
        )
    elif compare["promote"]:
        compare["notes"].append(
            "v4 improves side holdout metric without material regression — promoted."
        )
    else:
        compare["notes"].append(
            "v4 does not clear promote bar (need side-metric improvement, no regression)."
        )

    if not compare["promote"]:
        active_id = _rollback_active_to_schema(3)
        compare["rolled_back_to_v3"] = bool(active_id)
        compare["active_fit_id"] = active_id
        compare["notes"].append(
            "Failed retune NOT promoted. Active DB fit rolled back to schema v3."
            if active_id
            else "WARNING: could not find schema-v3 fit to reactivate."
        )
        compare["notes"].append(
            "ST KAV warehouse retained (nfl_dp_team_st_kav_weekly + matchup columns) "
            "for future work; default FEATURE_KEYS stay v3."
        )
    else:
        compare["notes"].append("Active DB fit remains schema v4 from this run.")

    COMPARE.write_text(json.dumps(compare, indent=2) + "\n")
    print(json.dumps(compare, indent=2), flush=True)
    print(f"wrote {OUT}", flush=True)
    print(f"wrote {COMPARE}", flush=True)
    return 0 if compare.get("rolled_back_to_v3") or compare["promote"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
