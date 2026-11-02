"""Layer A historical reconstruction — contract, leakage, coverage gates.

Does not open 2025. Does not change MATCHUP_RESPONSE.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_season_engine.priors import MATCHUP_RESPONSE  # noqa: E402
from src.services.cfb_season_engine.qb_feature_contract import (  # noqa: E402
    LOWSAMPLE_ATTEMPTS,
    QB_FEATURE_CONTRACT_VERSION,
    assert_counting_stats_season_legal,
    assert_legal_for_coefficient_fit,
    assert_roster_source_legal,
    assert_v1_talent_location,
)

ROOT = Path(__file__).resolve().parents[3]
LAYER_DIR = (
    ROOT
    / "services/model-service/src/services/cfb_season_engine/data/cfb_qb_layer_a"
)
sys.path.insert(0, str(ROOT / "scripts/cfb"))

from build_cfb_qb_layer_a import (  # noqa: E402
    FIRST_STATS_FLOOR,
    ROSTER_SOURCE,
    experience_from_first_appearance,
)


def _maybe_load(season: int) -> dict:
    path = LAYER_DIR / f"season_{season}.json"
    if not path.is_file():
        pytest.skip(f"Layer A artifact not built yet: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def test_coefficients_untouched() -> None:
    assert MATCHUP_RESPONSE == 1.40


def test_roster_source_is_year_locked_core() -> None:
    assert_roster_source_legal(ROSTER_SOURCE)
    assert ROSTER_SOURCE == "espn_core_seasons_Y_team_athletes"


def test_first_appearance_class_reconstruction() -> None:
    abbr, years, note, left = experience_from_first_appearance(2024, 2023)
    assert abbr == "FR" and years == 1
    abbr, years, note, left = experience_from_first_appearance(2024, 2022)
    assert abbr == "SO" and years == 2
    abbr, years, note, left = experience_from_first_appearance(2024, 2021)
    assert abbr == "JR" and years == 3
    abbr, years, note, left = experience_from_first_appearance(2024, 2019)
    assert abbr == "SR" and years == 5
    abbr, years, note, left = experience_from_first_appearance(2024, None)
    assert abbr == "FR" and years == 1
    abbr, years, note, left = experience_from_first_appearance(2024, FIRST_STATS_FLOOR)
    assert left == "CLASS_LEFT_CENSORED"


def test_artifacts_exist_and_pass_contract() -> None:
    for season in (2022, 2023, 2024):
        art = _maybe_load(season)
        assert art["qb_feature_contract_version"] == QB_FEATURE_CONTRACT_VERSION
        assert art["prior_season"] == season - 1
        assert art["roster_source"] == ROSTER_SOURCE
        assert art["layer"] == "A"
        assert float(art["coverage"]) >= 0.90
        teams = art["teams"]
        assert len(teams) == art["n_mapped_fbs"]
        for code, row in teams.items():
            assert row["prior_season"] == season - 1
            assert_counting_stats_season_legal(
                stats_season=int(row["prior_season"]),
                prediction_season=season,
                week=0,
            )
            assert row.get("recruiting_class_score") is None
            assert row.get("ol_support") is None
            assert row.get("weapons_support") is None
            avail = row.get("availability") or {}
            assert avail.get("recruiting") == "MISSING"
            assert avail.get("ol_support") == "MISSING"
            assert "PROXY" not in avail.values()
            prov = row.get("provenance") or {}
            assert prov.get("same_season_stats_used") is False
            assert prov.get("site_roster_used") is False
            assert prov.get("espn_experience_used") is False
            assert prov.get("recruiting_used") is False
            assert "2026" not in str(prov.get("stats_season"))
            if row.get("starter_key"):
                assert row["qb_feature_contract_version"] == QB_FEATURE_CONTRACT_VERSION


def test_established_location_gate() -> None:
    for season in (2022, 2023, 2024):
        art = _maybe_load(season)
        est = [
            float(r["qb_talent"])
            for r in art["teams"].values()
            if r.get("established") and r.get("starter_key")
        ]
        assert_v1_talent_location(est, established=True)
        summary = art["talent_established"]
        assert 62.0 <= float(summary["mean"]) <= 76.0
        assert 5.0 <= float(summary["sd"]) <= 14.0
        assert int(summary["n"]) >= 20


def test_not_placeholder_distribution() -> None:
    for season in (2022, 2023, 2024):
        art = _maybe_load(season)
        talents = [
            float(r["qb_talent"])
            for r in art["teams"].values()
            if r.get("starter_key")
        ]
        loc = assert_v1_talent_location(talents)
        assert loc["mean"] > 55.0
        assert loc["sd"] > 4.0


def test_lowsample_does_not_inherit_2026_floor() -> None:
    for season in (2022, 2023, 2024):
        art = _maybe_load(season)
        for row in art["teams"].values():
            att = int(row.get("pass_attempts_prior") or 0)
            if att < LOWSAMPLE_ATTEMPTS and row.get("starter_key"):
                assert row.get("recruiting_class_score") is None
                assert 55.0 != row.get("qb_talent") or att > 0


def test_fit_gate_still_requires_v1() -> None:
    assert_legal_for_coefficient_fit(QB_FEATURE_CONTRACT_VERSION)


def test_no_2025_or_2026_reconstruction_sources() -> None:
    for season in (2022, 2023, 2024):
        art = _maybe_load(season)
        blob = json.dumps(art)
        assert '"prior_season": 2025' not in blob
        assert '"stats_season": 2025' not in blob
        assert '"stats_season": 2026' not in blob
        src = (
            ROOT / "scripts/cfb/build_cfb_qb_layer_a.py"
        ).read_text()
        assert "2025 labels" in src or "2025 sealed" in src.lower() or "2025" in src
        assert "site.api.espn.com" not in src
        assert "teamHistory" not in src or "team_history_used" in src
