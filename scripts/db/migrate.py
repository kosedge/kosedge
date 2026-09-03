#!/usr/bin/env python3
"""Repo-root convenience wrapper for the model-service migration CLI.

Usage (from monorepo root)::

    python scripts/db/migrate.py check-integrity
    DATABASE_URL=... python scripts/db/migrate.py status
    DATABASE_URL=... python scripts/db/migrate.py baseline --through 053
    DATABASE_URL=... python scripts/db/migrate.py apply

Never commit credentials. This script does not connect unless a subcommand needs it.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
if str(MS) not in sys.path:
    sys.path.insert(0, str(MS))

from src.db_migrations.__main__ import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
