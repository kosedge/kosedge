#!/usr/bin/env python3
"""W8 capture dry-run (DR-1..DR-6). No credentials, no publish, no grade."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "services", "model-service"))

from src.services.nfl_w8_capture.dry_run import run_tamper_suite  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="NFL W8 capture dry-run (synthetic only)")
    parser.add_argument("--root", default="", help="Output directory (default: temp)")
    args = parser.parse_args()
    root = args.root or tempfile.mkdtemp(prefix="nfl-w8-dry-run-")
    payload = run_tamper_suite(root)
    print(json.dumps(payload, indent=2))
    return 0 if payload.get("all_ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
