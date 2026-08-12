"""Season-sim conservation C1–C6 + win-ceiling soft-pile guard."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts" / "nfl"
sys.path.insert(0, str(ROOT / "services" / "data-platform-nfl" / "src"))
sys.path.insert(0, str(SCRIPTS))


def _load_conservation():
    path = SCRIPTS / "check_season_sim_conservation.py"
    name = "check_season_sim_conservation"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_break_soft_piles_uses_consecutive_gaps():
    from data_platform_nfl.defensive_production_stack import _break_soft_piles

    # Six teams spaced ≤0.12 apart — must be one cluster under consecutive rule.
    values = {
        "A": 12.55,
        "B": 12.58,
        "C": 12.61,
        "D": 12.64,
        "E": 12.67,
        "F": 12.70,
    }
    residuals = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6}
    out = _break_soft_piles(values, residuals, width=0.15, spread=1.2)
    spread = max(out.values()) - min(out.values())
    assert spread > 0.5, spread  # micro-spread actually separates
    assert abs(sum(out.values()) - sum(values.values())) < 1e-6


def test_ceiling_cluster_count_flags_12_6_pile():
    from data_platform_nfl.defensive_production_stack import ceiling_cluster_count

    pile = {f"T{i}": 12.6 + i * 0.02 for i in range(10)}
    assert ceiling_cluster_count(pile, band=0.35) == 10
    spread = {f"T{i}": 11.0 + i * 0.4 for i in range(10)}
    assert ceiling_cluster_count(spread, band=0.35) <= 2


def test_active_bundle_conservation_green():
    mod = _load_conservation()
    bundle = ROOT / "data" / "ops" / "nfl-preseason-sim-2026-20260809T165350Z"
    if not bundle.exists():
        pytest.skip("locked bundle missing")
    suite = mod.check_bundle(bundle, n_path_replicates=500)
    failed = [r for r in suite.results if not r.ok]
    assert not failed, failed


def test_win_histogram_bins():
    mod = _load_conservation()
    hist = mod.win_histogram(
        {
            "A": 4.0,
            "B": 7.5,
            "C": 10.5,
            "D": 12.5,
        }
    )
    assert hist == {"<=6": 1, "7-9": 1, "10-11": 1, ">=12": 1}
