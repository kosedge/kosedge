from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "nfl" / "build_clock_play_coherent_state_priors.py"


def _builder_module():
    spec = importlib.util.spec_from_file_location("clock_play_state_priors", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_punt_outcome_uses_nflfastR_punt_flags_before_return_yards() -> None:
    builder = _builder_module()

    assert (
        builder._punt_outcome(
            {
                "punt_fair_catch": 1,
                "return_yards": 0,
            }
        )
        == "fair_catch"
    )
    assert (
        builder._punt_outcome(
            {
                "punt_downed": 1,
                "return_yards": 0,
            }
        )
        == "dead_ball"
    )
    assert builder._punt_outcome({"return_yards": 0}) == "return"


def test_punt_distance_prefers_nflfastR_kick_distance() -> None:
    builder = _builder_module()

    payload = {"kick_distance": 52, "punt_yards": None}
    distance = int(
        round(
            builder._number(payload.get("kick_distance"))
            or builder._number(payload.get("punt_yards"))
            or 0.0
        )
    )

    assert distance == 52
