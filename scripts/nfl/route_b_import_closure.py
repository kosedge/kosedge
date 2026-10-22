#!/usr/bin/env python3
"""Regenerate docs/research/NFL_ROUTE_B_IMPORT_CLOSURE_SHA256.md (K-4)."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MODEL_SERVICE = REPO / "services" / "model-service"
sys.path.insert(0, str(MODEL_SERVICE))

from src.services.nfl_eval_prep.route_b_closure import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
