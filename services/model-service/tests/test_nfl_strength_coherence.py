"""Tests for NFL strength coherence (wins ↔ playoff ↔ SB ↔ win_dist ↔ LAR id)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts" / "nfl"
sys.path.insert(0, str(ROOT / "services" / "model-service" / "src"))
sys.path.insert(0, str(SCRIPTS))


def _load_playoff_mod():
    path = SCRIPTS / "nfl_playoff_from_week_rates.py"
    name = "nfl_playoff_from_week_rates"
    if name in sys.modules:
        # Force reload so new helpers are visible when editing mid-session.
        del sys.modules[name]
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
    from services.nfl_canonical_teams import CANONICAL_TEAMS

    targets = {t: 8.5 for t in CANONICAL_TEAMS}
    targets["LAR"] = 9.7
    targets["SEA"] = 8.5
    seeded = {t: {w: 0.5 for w in range(1, 18)} for t in CANONICAL_TEAMS}
    seeded["LAR"] = {w: float(rates["LA"].get(w, 0.5)) for w in range(1, 18)}
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
    others = [t for t in CANONICAL_TEAMS if t not in {"LAR", "BUF"}]
    remaining = 272.0 - targets["LAR"] - targets["BUF"]
    for t in others:
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
    assert "LAR" in teams
    assert "CHI" in teams
    lar = next(f for f in flags if f["team"] == "LAR")
    assert "high_playoff_thin_sb" in lar["reasons"] or "high_wins_thin_sb" in lar["reasons"]


def test_flag_win_dist_catches_det_secondary_path():
    mod = _load_playoff_mod()
    rows = [{"team": "DET", "expected_wins": 7.0459}]
    dists = [{"team": "DET", "mean": 10.5716}]
    flags = mod.flag_win_dist_board_mismatches(rows, dists)
    assert flags and flags[0]["team"] == "DET"
    assert "win_dist_secondary_path" in flags[0]["reasons"]


def test_build_win_distributions_match_rate_sum():
    """Marginal Bernoullis must use actual week keys (incl. week 18, skip bye)."""
    mod = _load_playoff_mod()
    from services.nfl_canonical_teams import CANONICAL_TEAMS

    rates = {}
    for t in CANONICAL_TEAMS:
        # 17 games: weeks 1-5,7-18 (bye week 6) — mirrors wall-chart shape.
        weeks = {w: 0.4 for w in list(range(1, 6)) + list(range(7, 19))}
        rates[t] = weeks
    rates["DET"] = {w: 0.4145 for w in list(range(1, 6)) + list(range(7, 19))}
    # 17 * 0.4145 ≈ 7.0465
    rows = mod.build_win_distributions_from_marginal_rates(
        rates, n_replicates=8_000, seed=20260811
    )
    det = next(r for r in rows if r["team"] == "DET")
    assert det["mean"] == pytest.approx(7.0465, abs=0.15)
    flags = mod.flag_win_dist_board_mismatches(
        [{"team": "DET", "expected_wins": 7.0465}],
        [det],
    )
    assert flags == []


def test_distribution_row_mean_from_hist():
    mod = _load_playoff_mod()
    counts = np.zeros(18, dtype=np.int64)
    counts[7] = 5000
    counts[8] = 5000
    row = mod._distribution_row_from_hist("DET", counts, n_sims=10_000)
    assert row["team"] == "DET"
    assert row["mean"] == pytest.approx(7.5, abs=0.01)
    assert row["p10"] == 7.0
    assert row["p90"] == 8.0


def test_apply_win_dist_percentiles_to_rows():
    mod = _load_playoff_mod()
    rows = [{"team": "DET", "expected_wins": 7.0, "wins_p10": 7, "wins_p90": 14}]
    dists = [{"team": "DET", "p10": 4.0, "p90": 10.0, "mean": 7.0}]
    out = mod.apply_win_dist_percentiles_to_rows(rows, dists)
    assert out[0]["wins_p10"] == 4
    assert out[0]["wins_p90"] == 10


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
        "expected_wins_check": {"LAR": 10.82},
    }
    out = mod.apply_playoff_probs_to_team_rows(
        rows, recomputed, rewrite_super_bowl=True, rewrite_expected_wins=True
    )
    assert out[0]["team"] == "LAR"
    assert out[0]["playoff_prob"] == 0.55
    assert out[0]["super_bowl_win_prob"] == 0.031
    assert out[0]["expected_wins"] == 10.82


def test_pairwise_wins_crush_noncomplementary_marginals():
    """Independent 0.98 rates are not 0.98 game WPs once hp/(hp+ap) runs."""
    mod = _load_playoff_mod()
    from services.nfl_canonical_teams import CANONICAL_TEAMS

    rates = {t: {w: 0.5 for w in range(1, 19) if w != 11} for t in CANONICAL_TEAMS}
    rates["CHI"] = {w: 0.98 for w in range(1, 19) if w != 11}
    rates["LAR"] = {w: 0.57 for w in range(1, 19) if w != 11}
    marginal = mod.season_wins_from_rates(rates)
    pairwise = mod.pairwise_expected_wins(rates)
    assert marginal["CHI"] == pytest.approx(16.66, abs=0.05)
    assert pairwise["CHI"] < marginal["CHI"] - 2.0
    assert abs(sum(pairwise.values()) - 272.0) < 1e-6


def test_project_rates_onto_schedule_closes_chi_lar_gap():
    mod = _load_playoff_mod()
    from services.nfl_canonical_teams import CANONICAL_TEAMS

    rates = {t: {w: 0.5 for w in range(1, 19) if w != 11} for t in CANONICAL_TEAMS}
    rates["CHI"] = {w: 0.82 for w in range(1, 19) if w != 11}
    rates["LAR"] = {w: 0.57 for w in range(1, 19) if w != 11}
    projected, audit = mod.project_rates_onto_schedule(rates, max_iter=6, tol=0.35)
    assert audit["converged"] is True
    assert audit["final_max_gap"] <= 0.35
    marg = mod.season_wins_from_rates(projected)
    pair = mod.pairwise_expected_wins(projected)
    assert abs(marg["CHI"] - pair["CHI"]) <= 0.35
    assert abs(marg["LAR"] - pair["LAR"]) <= 0.35
    # Must not hand-set LAR to a 12-win pile; just close the dual statistic.
    assert 8.0 <= pair["LAR"] <= 12.5


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
