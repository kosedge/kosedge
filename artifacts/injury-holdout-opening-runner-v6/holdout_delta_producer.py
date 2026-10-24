#!/usr/bin/env python3
"""Holdout delta producer — B-4 / B-4b / B-4c / B-10 (filed with expected answers v5).

Path 1 holdout export = this composition (B-10):
  1. holdout_frozen_row_builder builds player value and x_continuity
     from pinned raw listings + schedule(gameday,gametime) + rosters
     via frozen precompute_games 8d188da2 (_structural_index / continuity)
     under HEAD 8e2a15ac injury_paths QB1_INDEX_UNITS = 0.12
  2. apply_params from frozen script 8d188da2
  3. selected_params from sha-verified fit_object 6a5490db
  4. under null contract ff8e6527
  5. pre-kickoff information only, with as_of <= kickoff
  6. writer 9947b880 timestamps_for_game (invoked by the runner, not here)
  7. writer 9947b880 write_sidecar_chain (invoked by the runner, not here)

games.json is not a source of value, x_continuity, or deltas (B-4b).
A timestamp with no zone STOPs (B-4c). parse_fit_report_time_utc in
ff8e6527 still coerces naive→UTC; this producer never lets a naive
stamp reach that function.

writer.main() is the le2023 Path 1 entrypoint and is not invoked on holdout.
"""

from __future__ import annotations

import hashlib
import importlib.util
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

HERE = Path(__file__).resolve().parent

REQUIRED_FIT = "6a5490dbc09b160f4509ea65b3b2257f9703f9d43635092d0da94c1577abb657"
REQUIRED_FROZEN_SCRIPT = "8d188da27d3c9f802acdca76763e1ca05e714040cc5ea3722e4922853f28167c"
REQUIRED_NULL_CONTRACT = "ff8e6527f63b0afd727eed30444436ceae320cc336d9113a2634fd66d4aebad2"
REQUIRED_INJURY_PATHS = "ebd3dac083562afb4928e2ed756f617248894e636356f7426f0bc6ae58344e8b"
PINNED_QB1_INDEX_UNITS = 0.12


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"B-4 cannot load {name} from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def import_builder(pkg: Path):
    path = pkg / "holdout_frozen_row_builder.py"
    return _load_module("holdout_frozen_row_builder_v5", path)


def _parse_iso_or_stop(value: Any, where: str) -> Optional[datetime]:
    """B-4c: empty → None. Z/offset → aware. Naive/zoneless → STOP."""
    raw = "" if value is None else str(value).strip()
    if not raw:
        return None
    probe = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        stamp = datetime.fromisoformat(probe)
    except ValueError as exc:
        raise AssertionError(f"B-4c refuse: unparseable timestamp {value!r} at {where}") from exc
    if stamp.tzinfo is None:
        raise AssertionError(f"B-4c refuse: naive/zoneless timestamp {value!r} at {where}")
    return stamp


def _pre_kickoff_only(game: Dict[str, Any]) -> None:
    for key in ("home_score", "away_score", "actual_margin", "actual_total", "close_spread_home", "close_total"):
        if key in game and game.get(key) is not None:
            raise AssertionError(f"B-4 refuse: post-kickoff field {key} on producer input")


def _assert_as_of_before_kickoff(game: Dict[str, Any]) -> None:
    if game.get("row_status") != "ok":
        return
    kickoff = _parse_iso_or_stop(game.get("kickoff_utc"), "kickoff_utc")
    if kickoff is None:
        raise AssertionError("B-4 refuse: ok row missing kickoff_utc")
    sides = game.get("sides") or {}
    for side_name in ("home", "away"):
        side = sides.get(side_name) or {}
        as_of = _parse_iso_or_stop(side.get("listing_as_of"), f"listing_as_of {side_name}")
        if as_of is None:
            raise AssertionError(f"B-4 refuse: ok row missing listing_as_of {side_name}")
        if as_of > kickoff:
            raise AssertionError(
                f"B-4 refuse: listing_as_of {side.get('listing_as_of')} > kickoff {game.get('kickoff_utc')}"
            )


def produce_deltas(
    pkg: Path,
    *,
    listings_dir: Path,
    schedule_path: Path,
    rosters_dir: Path,
    games_json: Optional[Path] = None,
    pin_le2023_raw: bool = False,
    allowed_listing_years: Optional[Sequence[int]] = None,
    allowed_roster_years: Optional[Sequence[int]] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """Build rows from pinned raw inputs, then apply_params.

    Returns (applied, built_rows, pin receipt). built_rows carry sides
    for timestamps_for_game. games.json values are refused.
    """
    builder = import_builder(pkg)
    built, pins = builder.build_rows(
        pkg,
        listings_dir=listings_dir,
        schedule_path=schedule_path,
        rosters_dir=rosters_dir,
        games_json=games_json,
        pin_le2023_raw=pin_le2023_raw,
        allowed_listing_years=allowed_listing_years,
        allowed_roster_years=allowed_roster_years,
    )
    for game in built:
        _pre_kickoff_only(game)
        _assert_as_of_before_kickoff(game)
    applied, extra = builder.apply_built_rows(pkg, built)
    units = extra.get("qb1_index_units")
    if abs(float(units or 0) - PINNED_QB1_INDEX_UNITS) > 1e-12:
        raise AssertionError(f"B-4 QB1_INDEX_UNITS {units} != pinned {PINNED_QB1_INDEX_UNITS}")
    if abs(float(pins.get("qb1_index_units") or 0) - PINNED_QB1_INDEX_UNITS) > 1e-12:
        raise AssertionError("B-4 builder QB1_INDEX_UNITS drifted")
    pins.update(
        {
            "fit_object_sha": REQUIRED_FIT,
            "frozen_script_sha": REQUIRED_FROZEN_SCRIPT,
            "null_contract_sha": REQUIRED_NULL_CONTRACT,
            "injury_paths_sha": REQUIRED_INJURY_PATHS,
            "qb1_index_units": PINNED_QB1_INDEX_UNITS,
            "qb1_index_units_source": (
                "seeded/injury_paths_8e2a15ac.py (HEAD 8e2a15ac) "
                "QB1_INDEX_UNITS = 0.12; QB1_POINTS_PER_INDEX_UNIT = 12.5; "
                "QB1_FLOOR_SPREAD_POINTS = QB1_INDEX_UNITS * QB1_POINTS_PER_INDEX_UNIT"
            ),
            "source": (
                "build_rows(8d188da2.precompute_games) + apply_params(6a5490db) "
                "under ff8e6527; raw listings/schedule/rosters; games.json values forbidden; "
                "naive timestamp STOP"
            ),
            "games_json_raw_deltas_forbidden": True,
            "games_json_values_forbidden": True,
            "naive_timestamp": "STOP",
            "writer_main_not_invoked": True,
        }
    )
    return applied, built, pins
