#!/usr/bin/env python3
"""G-PIT gate over cited production load_rosters / load_rosters_dir.

Executes `load_rosters_dir` L267–302 from the deposited copy of
holdout_frozen_row_builder.py (sha 247744d2) and STARTER_SLOTS / _alias
from run_injury_residual_fit.py (sha 8d188da2).

GPIT_MODE=1 → STOP (exit 2), do not run the season-union body.
GPIT_MODE unset → invoke the cited function on the synthetic 2098
season CSV only (distinct: leaked membership + SUPERSEDED on stderr,
exit 0).

Does not open 2024/25 holdout files. Does not call cited main/build_rows.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple

HERE = Path(__file__).resolve().parent
CITED_FIT = HERE / "cited" / "run_injury_residual_fit.py"
CITED_BUILDER = HERE / "cited" / "holdout_frozen_row_builder.py"
REQUIRED_FIT = "8d188da27d3c9f802acdca76763e1ca05e714040cc5ea3722e4922853f28167c"
REQUIRED_BUILDER = "247744d23fef6f289e11da78523bdb007ada136f070916cf66a2bfee161e9cad"
STOP_MSG = "G-PIT STOP: season-level roster loader forbidden"
SUPERSEDED_MSG = "SUPERSEDED: season-level roster loader invoked without GPIT_MODE"
HOLD_OUT_MARKERS = ("2024", "2025", "nfl_depth_chart_2024", "nfl_depth_chart_2025")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_cited_pins() -> tuple[str, str]:
    fit = _sha256(CITED_FIT)
    builder = _sha256(CITED_BUILDER)
    if fit != REQUIRED_FIT or builder != REQUIRED_BUILDER:
        print("STOP: cited loader sha mismatch", file=sys.stderr)
        sys.exit(2)
    return fit, builder


def _refuse_holdout_path(path: Path) -> None:
    text = str(path)
    name = path.name
    if any(m in text or m in name for m in HOLD_OUT_MARKERS):
        print("DO-NOT-OPEN: holdout-era path refused", file=sys.stderr)
        sys.exit(2)
    if path.is_dir():
        for child in path.iterdir():
            if any(m in child.name for m in HOLD_OUT_MARKERS):
                print("DO-NOT-OPEN: holdout-era file in dir", file=sys.stderr)
                sys.exit(2)


def load_rosters_dir_from_cited(rosters_dir: Path, allowed_years: Sequence[int]):
    """Exec deposited load_rosters_dir L267–302 (1-indexed)."""
    _refuse_holdout_path(rosters_dir)
    fit_lines = CITED_FIT.read_text().splitlines(keepends=True)
    builder_lines = CITED_BUILDER.read_text().splitlines(keepends=True)
    ns: dict[str, Any] = {
        "csv": csv,
        "Path": Path,
        "Optional": Optional,
        "Sequence": Sequence,
        "Tuple": Tuple,
        "Dict": Dict,
        "Any": Any,
        "frozenset": frozenset,
    }
    # ALWAYS_FORBIDDEN = ...  (builder L37)
    exec(builder_lines[36], ns)
    # STARTER_SLOTS = frozenset({...})  (fit L78–106)
    exec("".join(fit_lines[77:106]), ns)
    # def _alias(...)  (fit L126–136)
    exec("".join(fit_lines[125:136]), ns)

    class _Script:
        STARTER_SLOTS = ns["STARTER_SLOTS"]
        _alias = staticmethod(ns["_alias"])

    ns["script"] = _Script
    # def load_rosters_dir(...)  (builder L267–302)
    exec("".join(builder_lines[266:302]), ns)
    return ns["load_rosters_dir"](rosters_dir, _Script, list(allowed_years))


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    assert_cited_pins()
    rosters_dir = Path(argv[0]) if argv else Path("-")
    if os.environ.get("GPIT_MODE") == "1":
        print(STOP_MSG, file=sys.stderr)
        print(json.dumps({"n_members": 0, "player_ids": [], "in_aaa": False}))
        return 2
    by_team, by_season, _depth = load_rosters_dir_from_cited(rosters_dir, [2098])
    pids = sorted(by_season.get(2098, set()))
    aaa = set(by_team.get(2098, {}).get("AAA", set()))
    print(SUPERSEDED_MSG, file=sys.stderr)
    print(
        json.dumps(
            {
                "n_members": len(pids),
                "player_ids": pids,
                "in_aaa": "00-SYN-JOIN" in aaa,
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
