#!/usr/bin/env python3
"""Holdout delta producer — B-4 / B-10 composition (filed with expected answers v3).

Path 1 holdout export = this composition (B-10):
  1. apply_params from frozen script 8d188da2
  2. selected_params from sha-verified fit_object 6a5490db
  3. under null contract ff8e6527
  4. pre-kickoff information only
  5. writer 9947b880 timestamps_for_game (invoked by the runner, not here)
  6. writer 9947b880 write_sidecar_chain (invoked by the runner, not here)

writer.main() is the le2023 Path 1 entrypoint and is not invoked on holdout.
games.json raw delta_margin / delta_total are forbidden as a source.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import types
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

HERE = Path(__file__).resolve().parent

REQUIRED_FIT = "6a5490dbc09b160f4509ea65b3b2257f9703f9d43635092d0da94c1577abb657"
REQUIRED_FROZEN_SCRIPT = "8d188da27d3c9f802acdca76763e1ca05e714040cc5ea3722e4922853f28167c"
REQUIRED_NULL_CONTRACT = "ff8e6527f63b0afd727eed30444436ceae320cc336d9113a2634fd66d4aebad2"

PRE_KICKOFF_PLAYER_KEYS = ("unit", "identity_resolved", "status", "n_lag_out", "value", "is_qb1_out_candidate")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def assert_producer_pins(pkg: Path) -> Dict[str, str]:
    pairs = (
        (pkg / "seeded" / "fit_object.json", REQUIRED_FIT, "fit_object"),
        (pkg / "seeded" / "run_injury_residual_fit.py", REQUIRED_FROZEN_SCRIPT, "frozen_script"),
        (pkg / "seeded" / "nfl_injury_null_contract_8e2a15ac.py", REQUIRED_NULL_CONTRACT, "null_contract"),
    )
    out: Dict[str, str] = {}
    for path, exp, label in pairs:
        got = _sha256_file(path)
        if got != exp:
            raise AssertionError(f"B-4 pin {label} sha {got} != {exp}")
        out[label] = got
    return out


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"B-4 cannot load {name} from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_apply_params(pkg: Path):
    """Sha-verify then load frozen apply_params. Stubs only the import graph."""
    assert_producer_pins(pkg)
    fit = json.loads((pkg / "seeded" / "fit_object.json").read_text(encoding="utf-8"))
    contract = _load_module("null_contract_ff8e6527", pkg / "seeded" / "nfl_injury_null_contract_8e2a15ac.py")
    injury_paths = types.ModuleType("src.services.nfl_season_engine.injury_paths")
    injury_paths.QB1_FLOOR_SPREAD_POINTS = float(fit["qb1_floor"])
    injury_paths.QB1_POINTS_PER_INDEX_UNIT = float(fit["qb1_points_per_index_unit"])
    injury_paths.QB1_INDEX_UNITS = 1.0
    src = types.ModuleType("src")
    src.services = types.ModuleType("src.services")
    src.services.nfl_injury_null_contract = contract
    src.services.nfl_season_engine = types.ModuleType("src.services.nfl_season_engine")
    src.services.nfl_season_engine.injury_paths = injury_paths
    sys.modules.setdefault("src", src)
    sys.modules["src.services"] = src.services
    sys.modules["src.services.nfl_injury_null_contract"] = contract
    sys.modules["src.services.nfl_season_engine"] = src.services.nfl_season_engine
    sys.modules["src.services.nfl_season_engine.injury_paths"] = injury_paths
    script = _load_module("frozen_fit_8d188da2", pkg / "seeded" / "run_injury_residual_fit.py")
    if not hasattr(script, "apply_params") or not hasattr(script, "residual_from_units"):
        raise AssertionError("B-4 frozen script missing apply_params/residual_from_units")
    return script, fit["selected_params"]


def _refuse_raw_deltas(games: Sequence[Dict[str, Any]]) -> None:
    for game in games:
        if "delta_margin" in game or "delta_total" in game:
            raise AssertionError(
                "B-4 refuse: games.json raw delta_margin/delta_total are not a source; "
                "deltas must come from apply_params(6a5490db selected_params, 8d188da2)"
            )


def _pre_kickoff_only(game: Dict[str, Any]) -> None:
    """No post-kickoff outcome fields may enter the residual."""
    for key in ("home_score", "away_score", "actual_margin", "actual_total", "close_spread_home", "close_total"):
        if key in game and game.get(key) is not None:
            raise AssertionError(f"B-4 refuse: post-kickoff field {key} on producer input")


def produce_deltas(pkg: Path, games: Sequence[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Derive delta_margin/delta_total. Returns (applied games, pin receipt)."""
    _refuse_raw_deltas(games)
    for game in games:
        _pre_kickoff_only(game)
        if game.get("row_status") == "ok":
            sides = game.get("sides") or {}
            for side_name in ("home", "away"):
                side = sides.get(side_name) or {}
                for player in side.get("players") or []:
                    extra = set(player) - set(PRE_KICKOFF_PLAYER_KEYS)
                    # listing identity fields beyond the unit vector are ignored
                    _ = extra
    script, params = load_apply_params(pkg)
    applied = script.apply_params(list(games), params)
    pins = {
        "fit_object_sha": REQUIRED_FIT,
        "frozen_script_sha": REQUIRED_FROZEN_SCRIPT,
        "null_contract_sha": REQUIRED_NULL_CONTRACT,
        "selected_params": dict(params),
        "source": "apply_params(8d188da2, selected_params from 6a5490db) under ff8e6527; pre-kickoff only",
        "games_json_raw_deltas_forbidden": True,
        "writer_main_not_invoked": True,
    }
    return applied, pins
