"""Truth Layer invariant suite — blocks publish when red."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts" / "nfl"
sys.path.insert(0, str(ROOT / "services" / "model-service" / "src"))
sys.path.insert(0, str(SCRIPTS))


def _load_check_module():
    path = SCRIPTS / "check_nfl_invariants.py"
    name = "check_nfl_invariants"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_american_odds_rejects_corrupt_midrange():
    mod = _load_check_module()
    assert mod.is_valid_american(-110)
    assert mod.is_valid_american(105)
    assert not mod.is_valid_american(-66)
    assert not mod.is_valid_american(50)
    assert not mod.is_valid_american(0)


def test_edge_recompute():
    mod = _load_check_module()
    assert mod.recompute_edge(-3.5, -2.5) == pytest.approx(-1.0)


def test_active_bundle_invariants_green():
    mod = _load_check_module()
    bundle = ROOT / "data" / "ops" / "nfl-preseason-sim-2026-20260809T165350Z"
    if not bundle.exists():
        pytest.skip("locked bundle missing")
    suite = mod.check_bundle(bundle)
    failed = [r for r in suite.results if not r.ok]
    assert not failed, failed


def test_deliberate_i3_break_fails():
    mod = _load_check_module()
    bundle = ROOT / "data" / "ops" / "nfl-preseason-sim-2026-20260809T165350Z"
    if not bundle.exists():
        pytest.skip("locked bundle missing")
    suite = mod.check_bundle(bundle, deliberate_break="I3")
    i3 = next(r for r in suite.results if r.id == "I3")
    assert i3.ok is False
    assert suite.ok is False


def test_canonical_team_la_maps_to_lar():
    from services.nfl_canonical_teams import canonicalize_team, missing_canonical_teams

    assert canonicalize_team("LA") == "LAR"
    assert canonicalize_team("lar") == "LAR"
    assert missing_canonical_teams(["LA"] + ["BUF"] * 31)  # still missing most
    assert missing_canonical_teams(
        [
            "ARI",
            "ATL",
            "BAL",
            "BUF",
            "CAR",
            "CHI",
            "CIN",
            "CLE",
            "DAL",
            "DEN",
            "DET",
            "GB",
            "HOU",
            "IND",
            "JAX",
            "KC",
            "LAC",
            "LA",  # alias
            "LV",
            "MIA",
            "MIN",
            "NE",
            "NO",
            "NYG",
            "NYJ",
            "PHI",
            "PIT",
            "SEA",
            "SF",
            "TB",
            "TEN",
            "WAS",
        ]
    ) == []


def test_playoff_recompute_sums_to_seven():
    from nfl_playoff_from_week_rates import (
        load_week_rates_from_bundle,
        recompute_playoff_probs,
    )

    bundle = ROOT / "data" / "ops" / "nfl-preseason-sim-2026-20260809T165350Z"
    if not (bundle / "team_week_win_rates.json").exists():
        pytest.skip("week rates missing")
    out = recompute_playoff_probs(
        load_week_rates_from_bundle(bundle),
        n_replicates=2_000,
        seed=7,
    )
    assert out["sanity"]["sum_playoff_afc"] == pytest.approx(7.0, abs=0.05)
    assert out["sanity"]["sum_playoff_nfc"] == pytest.approx(7.0, abs=0.05)
