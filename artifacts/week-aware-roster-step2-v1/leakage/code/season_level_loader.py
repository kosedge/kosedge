#!/usr/bin/env python3
"""Season-level roster loader — SUPERSEDED.

T-PIT-10: when GPIT_MODE=1 this path HARD_STOPs. It must not produce
week-1 membership from a season snapshot. This package never loads
2024/25 holdout files.
"""

from __future__ import annotations

import os
import sys

STOP_MSG = "G-PIT STOP: season-level roster loader forbidden"


def load_rosters(*_args, **_kwargs):
    if os.environ.get("GPIT_MODE") == "1":
        print(STOP_MSG, file=sys.stderr)
        sys.exit(2)
    print("SUPERSEDED: season-level roster loader refused", file=sys.stderr)
    sys.exit(2)


def load_rosters_dir(*_args, **_kwargs):
    return load_rosters(*_args, **_kwargs)


if __name__ == "__main__":
    load_rosters(sys.argv[1] if len(sys.argv) > 1 else "-")
