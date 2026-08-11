"""Tests for NFL strength coherence (wins ↔ playoff ↔ SB ↔ LAR id)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts" / "nfl"
sys.path.insert(0, str(ROOT / "services" / "model-service" / "src"))
sys.path.insert(0, str(SCRIPTS))


def _load_playoff_mod():
    path = SCRIPTS / "nfl_playoff_from_week_rates.py"
    name = "nfl_playoff_from_week_rates"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_canonicalize_la_to_lar_in_week_rates():
    mod = _load_playoff_mod()
    rates = {
        "LA": {1: 0.6, 2: 0.55, 3: 0.5},
        "SEA": {1: 0.4, 2: 0.45, 3: 0.5},
    }
    # targets only for present teams — function fills all 32; use tiny synthetic via normalize
    from services.nfl_canonical_teams import CANONICAL_TEAMS

    targets = {t: 8.5 for t in CANONICAL_TEAMS}
    targets["LAR"] = 9.7
    targets["SEA"] = 8.5
    # Seed flat rates for every team so rescale has profiles
    seeded = {t: {w: 0.5 for w in range(1, 18)} for t in CANONICAL_TEAMS}
    seeded["LAR"] = {w: float(rates["LA"].get(w, 0.5)) for w in range(1, 18)}
    # Put LA key only (legacy) — rescale must canonicalize
    seeded_legacy = {"LA" if t == "LAR" else t: weeks for t, weeks in seeded.items()}
    out = mod.rescale_week_rates_to_expected_wins(seeded_legacy, targets)
    assert "LAR" in out
    assert "LA" not in out
    assert sum(out["LAR"].values()) == pytest.approx(9.7, abs=0.15)


def test_rescale_aligns_season_wins_to_board():
    mod = _load_playoff_mod()
    from services.nfl_canonical_teams import CANONICAL_TEAMS

    rates = {t: {w: 0.5 for w in range(1, 18)} for t in CANONICAL_TEAMS}
    targets = {t: 8.5 for t in CANONICAL_TEAMS}
    targets["LAR"] = 9.6938
    targets["BUF"] = 12.8297
    # Keep sum ≈ 272
    others = [t for t in CANONICAL_TEAMS if t not in {"LAR", "BUF"}]
    remaining = 272.0 - targets["LAR"] - targets["BUF"]
    for i, t in enumerate(others):
        targets[t] = remaining / len(others)
    aligned = mod.rescale_week_rates_to_expected_wins(rates, targets)
    wins = mod.season_wins_from_rates(aligned)
    assert wins["LAR"] == pytest.approx(9.6938, abs=0.2)
    assert wins["BUF"] == pytest.approx(12.8297, abs=0.2)
    assert sum(wins.values()) == pytest.approx(272.0, abs=1.0)


def test_strength_win_prob_monotonic():
    mod = _load_playoff_mod()
    weak = mod.strength_win_prob(7.0, 12.0, home_field=False)
    strong = mod.strength_win_prob(12.0, 7.0, home_field=False)
    assert strong > 0.7
    assert weak < 0.3
    assert abs(strong + weak - 1.0) < 1e-9


def test_flag_contradictions_catches_lar_style_split():
    mod = _load_playoff_mod()
    rows = [
        {
            "team": "LAR",
            "expected_wins": 9.7,
            "playoff_prob": 0.84,
            "super_bowl_win_prob": 0.0048,
        },
        {
            "team": "CHI",
            "expected_wins": 12.7,
            "playoff_prob": 0.20,
            "super_bowl_win_prob": 0.10,
        },
    ]
    flags = mod.flag_wins_playoff_sb_contradictions(rows)
    teams = {f["team"] for f in flags}
    assert "LAR" in teams  # high playoff thin SB and/or high wins thin SB
    assert "CHI" in teams  # high wins low playoff
    lar = next(f for f in flags if f["team"] == "LAR")
    assert "high_playoff_thin_sb" in lar["reasons"] or "high_wins_thin_sb" in lar["reasons"]


def test_apply_playoff_rewrites_sb_when_requested():
    mod = _load_playoff_mod()
    rows = [
        {
            "team": "LA",
            "expected_wins": 9.7,
            "playoff_prob": 0.1,
            "division_title_prob": 0.05,
            "super_bowl_win_prob": 0.001,
        }
    ]
    recomputed = {
        "playoff_prob": {"LAR": 0.55},
        "division_title_prob": {"LAR": 0.22},
        "super_bowl_win_prob": {"LAR": 0.031},
    }
    out = mod.apply_playoff_probs_to_team_rows(
        rows, recomputed, rewrite_super_bowl=True
    )
    assert out[0]["team"] == "LAR"
    assert out[0]["playoff_prob"] == 0.55
    assert out[0]["super_bowl_win_prob"] == 0.031


def test_histogram_bands():
    mod = _load_playoff_mod()
    rows = [
        {"expected_wins": 4.0},
        {"expected_wins": 6.0},
        {"expected_wins": 9.0},
        {"expected_wins": 11.0},
        {"expected_wins": 13.0},
    ]
    assert mod.e_wins_histogram(rows) == {
        "<=5": 1,
        "5-7": 1,
        "7-10": 1,
        "10-12": 1,
        ">=12": 1,
    }
