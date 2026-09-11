"""Train/serve QB feature-contract tests.

Locks the live 2026 definition so hist-cal unknown@50 cannot silently
re-enter a coefficient fit. Does not change MATCHUP_RESPONSE or compose.
Does not open 2025 residuals. Does not ship median→50.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_season_engine.historical_calibration import (  # noqa: E402
    build_historical_proxy_universe,
)
from src.services.cfb_season_engine.loaders import build_packaged_universe  # noqa: E402
from src.services.cfb_season_engine.qb_feature_contract import (  # noqa: E402
    FORBIDDEN_ROSTER_SOURCES,
    LOWSAMPLE_ATTEMPTS,
    MISSING_QB_CLASS,
    MISSING_QB_TALENT,
    QB_FEATURE_CONTRACT_PLACEHOLDER,
    QB_FEATURE_CONTRACT_VERSION,
    FeatureContractError,
    assert_counting_stats_season_legal,
    assert_experience_not_current_leaked,
    assert_legal_for_coefficient_fit,
    assert_placeholder_location,
    assert_roster_source_legal,
    assert_v1_schema,
    assert_v1_talent_location,
    classify_qb,
    contract_version_for_notes,
    documentation,
    iter_universe_qb_talent,
    resolve_qb_talent,
    talent_from_qb_stats,
)
from src.services.cfb_season_engine.qb_situation import (  # noqa: E402
    compute_qb_situation_index,
)
from src.services.cfb_season_engine.team_projection import (  # noqa: E402
    project_game,
    project_game_to_dict,
)

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "cfb"))

from package_real_roster_2026 import (  # noqa: E402
    classify_qb as pack_classify_qb,
    resolve_qb_talent as pack_resolve_qb_talent,
    talent_from_qb_stats as pack_talent_from_qb_stats,
)


def test_contract_version_identity() -> None:
    doc = documentation()
    assert doc["qb_feature_contract_version"] == QB_FEATURE_CONTRACT_VERSION
    assert QB_FEATURE_CONTRACT_VERSION == "cfb-qb-feature-v1"
    assert QB_FEATURE_CONTRACT_PLACEHOLDER == "cfb-qb-feature-placeholder-unknown-50"
    assert QB_FEATURE_CONTRACT_VERSION != QB_FEATURE_CONTRACT_PLACEHOLDER


def test_packager_formula_matches_locked_spec() -> None:
    cases = (
        (0, 0, 0, False),
        (0, 0, 0, True),
        (40, 280, 2, False),
        (79, 600, 5, True),
        (80, 640, 6, False),
        (280, 2100, 18, False),
        (484, 4000, 40, True),
        (600, 5000, 50, False),
    )
    for att, yds, td, portal in cases:
        assert pack_talent_from_qb_stats(
            att, yds, td, is_portal=portal
        ) == talent_from_qb_stats(att, yds, td, is_portal=portal)
        pack = pack_resolve_qb_talent(
            att, yds, td, is_portal=portal, recruiting_class_score=70.0
        )
        spec, _avail = resolve_qb_talent(
            att,
            yds,
            td,
            is_portal=portal,
            recruiting_class_score=70.0,
            recruiting_availability="EXACT",
        )
        assert pack == spec


def test_packager_class_rules_match_locked_spec() -> None:
    kwargs = dict(
        experience_abbr="JR",
        experience_years=3,
        is_portal=False,
        qb_room_size=3,
        competing_with_attempts=10,
    )
    pack = pack_classify_qb(pass_attempts_2025=200, **kwargs)
    spec = classify_qb(pass_attempts_prior=200, **kwargs)
    assert pack[0] == spec[0]


def test_missing_value_semantics() -> None:
    assert talent_from_qb_stats(0, 0, 0, is_portal=False) == 48.0
    assert talent_from_qb_stats(0, 0, 0, is_portal=True) == 52.0
    talent, avail = resolve_qb_talent(
        0,
        0,
        0,
        is_portal=False,
        recruiting_class_score=None,
        recruiting_availability="MISSING",
    )
    assert talent == 48.0
    assert avail == "MISSING"
    assert MISSING_QB_TALENT == 50.0
    assert MISSING_QB_CLASS == "unknown"


def test_lowsample_does_not_inherit_2026_floor_when_recruiting_missing() -> None:
    stats_only, avail = resolve_qb_talent(
        40,
        280,
        2,
        is_portal=False,
        recruiting_class_score=None,
        recruiting_availability="MISSING",
    )
    blended, ok = resolve_qb_talent(
        40,
        280,
        2,
        is_portal=False,
        recruiting_class_score=55.0,
        recruiting_availability="EXACT",
    )
    assert avail == "MISSING"
    assert ok == "EXACT"
    assert stats_only != blended
    assert 40 <= stats_only <= 70


def test_established_ignores_recruiting() -> None:
    assert LOWSAMPLE_ATTEMPTS == 80
    a, _ = resolve_qb_talent(
        400, 3200, 24, is_portal=False, recruiting_class_score=95.0
    )
    b, _ = resolve_qb_talent(
        400, 3200, 24, is_portal=False, recruiting_class_score=40.0
    )
    assert a == b


def test_no_completion_rate_in_formula() -> None:
    src = (
        ROOT
        / "services/model-service/src/services/cfb_season_engine/qb_feature_contract.py"
    ).read_text()
    assert "completion_rate_term" in documentation()["formula"]
    assert documentation()["formula"]["completion_rate_term"] is False
    pack = (ROOT / "scripts/cfb/package_real_roster_2026.py").read_text()
    assert "completionPct" not in pack or "talent_from_qb_stats" in pack
    # Talent formula body must not reference completion.
    start = pack.index("def talent_from_qb_stats")
    end = pack.index("def resolve_qb_talent")
    pack_body = pack[start:end].lower()
    src_body = src[src.index("def talent_from_qb_stats") : src.index("def resolve_qb_talent")].lower()
    assert "completionpct" not in pack_body
    assert "completion_pct" not in src_body
    assert "comp_pct" not in src_body


def test_temporal_cutoff_rejects_same_season_stats() -> None:
    assert_counting_stats_season_legal(
        stats_season=2023, prediction_season=2024, week=1
    )
    with pytest.raises(FeatureContractError, match="same-season"):
        assert_counting_stats_season_legal(
            stats_season=2024, prediction_season=2024, week=1
        )
    with pytest.raises(FeatureContractError, match="after prediction"):
        assert_counting_stats_season_legal(
            stats_season=2025, prediction_season=2024, week=1
        )


def test_roster_source_rejects_current_club_leak() -> None:
    assert_roster_source_legal("espn_core_seasons_Y_team_athletes")
    for src in FORBIDDEN_ROSTER_SOURCES:
        with pytest.raises(FeatureContractError, match="leaks"):
            assert_roster_source_legal(src)


def test_experience_current_class_is_illegal() -> None:
    with pytest.raises(FeatureContractError, match="current-class"):
        assert_experience_not_current_leaked(
            experience_source="espn_core_athlete_experience_unadjusted"
        )


def test_placeholder_cannot_fit_coefficients() -> None:
    with pytest.raises(FeatureContractError, match="refusing coefficient fit"):
        assert_legal_for_coefficient_fit(QB_FEATURE_CONTRACT_PLACEHOLDER)
    assert_legal_for_coefficient_fit(QB_FEATURE_CONTRACT_VERSION)


def test_v1_schema_rejects_silent_proxy() -> None:
    row = {
        "qb_class": "incumbent",
        "qb_talent": 67.0,
        "ol_support": 50.0,
        "weapons_support": 50.0,
        "starter_name": "A",
        "starter_key": "1",
        "is_portal": False,
        "prior_season": 2023,
        "pass_attempts_prior": 300,
        "pass_yards_prior": 2500,
        "pass_td_prior": 20,
        "qb_feature_contract_version": QB_FEATURE_CONTRACT_VERSION,
        "availability": {"recruiting": "PROXY"},
    }
    with pytest.raises(FeatureContractError, match="silent proxy"):
        assert_v1_schema(row)


def test_location_check_rejects_missing_fill_labeled_v1() -> None:
    with pytest.raises(FeatureContractError, match="missing-fill"):
        assert_v1_talent_location([50.0] * 40)
    established = [62.0, 64.0, 67.0, 70.0, 73.0, 76.0, 68.0, 71.5] * 5
    summary = assert_v1_talent_location(established, established=True)
    assert 60.0 <= summary["mean"] <= 78.0


def test_hist_cal_proxy_is_placeholder_not_v1() -> None:
    universe = build_historical_proxy_universe(2023, {})
    assert (
        contract_version_for_notes(universe.notes)
        == QB_FEATURE_CONTRACT_PLACEHOLDER
    )
    talents = list(iter_universe_qb_talent(universe))
    assert talents
    assert_placeholder_location(talents)
    with pytest.raises(FeatureContractError):
        assert_legal_for_coefficient_fit(
            contract_version_for_notes(universe.notes)
        )
    idx, _score, _bd = compute_qb_situation_index(
        qb_class="unknown", qb_talent=50.0, supporting_cast=50.0
    )
    assert abs(idx - 0.92) < 1e-6


def test_packaged_2026_serve_is_v1_and_not_centered_at_50() -> None:
    universe = build_packaged_universe(2026)
    assert (
        contract_version_for_notes(universe.notes) == QB_FEATURE_CONTRACT_VERSION
    )
    talents = list(iter_universe_qb_talent(universe))
    assert len(talents) >= 100
    summary = assert_v1_talent_location(talents)
    assert summary["mean"] > 58.0
    assert summary["sd"] > 4.0
    codes = [c for c in ("ALA", "OSU", "UGA", "OHIO") if c in universe.teams]
    home, away = (codes + ["ALA", "OSU"])[:2]
    proj = project_game(
        universe, home_team=home, away_team=away, week=1, season=2026
    )
    payload = project_game_to_dict(proj)
    assert payload["qb_feature_contract_version"] == QB_FEATURE_CONTRACT_VERSION
    assert payload["engine_version"]


def test_does_not_open_2025_or_change_response() -> None:
    src = (
        ROOT
        / "services/model-service/src/services/cfb_season_engine/qb_feature_contract.py"
    ).read_text()
    assert "unseal" in src.lower()
    from src.services.cfb_season_engine.priors import MATCHUP_RESPONSE

    assert MATCHUP_RESPONSE == 1.40
