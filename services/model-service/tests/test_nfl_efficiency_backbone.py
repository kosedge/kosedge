"""Sprint 2: in-house NFL efficiency backbone → existing strength slot."""

from __future__ import annotations

from src.services.nfl_season_engine import (
    EFFICIENCY_BACKBONE_VERSION,
    build_demo_universe,
    build_packaged_real_universe,
    load_packaged_epa_priors,
)
from src.services.nfl_season_engine.efficiency_backbone import (
    UnitEfficiency,
    TeamEfficiencyPackage,
    blend_packages,
    build_package_from_season_row,
    epa_to_strength_indices,
    package_to_strength_indices,
    packages_from_team_rows,
    prior_current_blend_weight,
    rank_packages,
    uncertainty_from_games,
)
from src.services.nfl_season_engine.loaders import (
    STRENGTH_SOURCE_DEMO,
    STRENGTH_SOURCE_PACKAGED_EFFICIENCY,
)


def test_epa_to_strength_indices_matches_edge_board_contract() -> None:
    idx = epa_to_strength_indices(
        off_epa=0.05,
        def_epa_allowed=-0.10,
        pressure_generated=0.18,
        pressure_allowed=0.14,
    )
    assert 0.82 <= idx["offense_index"] <= 1.22
    assert 0.82 <= idx["defense_index"] <= 1.24
    # Elite D (negative EPA allowed) → defense_index > 1
    assert idx["defense_index"] > 1.05


def test_uncertainty_tightens_with_games() -> None:
    assert uncertainty_from_games(0) > uncertainty_from_games(8)
    assert uncertainty_from_games(16) <= 0.60


def test_prior_current_blend_weight() -> None:
    assert prior_current_blend_weight(current_games=0) == 0.0
    assert prior_current_blend_weight(current_games=4) == 0.5
    assert prior_current_blend_weight(current_games=8) == 1.0


def test_package_exposes_off_def_st_pace_variance() -> None:
    pkg = build_package_from_season_row(
        "SEA",
        {
            "off_epa_per_play": 0.045,
            "def_epa_allowed_per_play": -0.124,
            "success_rate_offense": 0.48,
            "success_rate_defense_allowed": 0.40,
            "explosive_pass_plays": 90,
            "explosive_pass_allowed": 60,
            "offensive_plays": 1050,
            "defensive_plays": 1020,
            "red_zone_td_rate": 0.62,
            "pass_rate": 0.56,
            "pressure_rate_generated": 0.20,
            "pressure_rate_allowed": 0.14,
            "n_weeks": 17,
        },
        as_of="2026-08-07",
        source="test",
        prior_season=2025,
    )
    assert pkg.version == EFFICIENCY_BACKBONE_VERSION
    assert pkg.st_index == 1.0  # no ST EPA → neutral
    assert pkg.pace > 0.9
    assert pkg.variance < uncertainty_from_games(0)
    idx = package_to_strength_indices(pkg)
    assert "offense_index" in idx and "defense_index" in idx
    assert "pace_factor" in idx and "pass_rate_bias" in idx


def test_one_game_craziness_regressed_via_blend() -> None:
    prior = TeamEfficiencyPackage(
        team="NE",
        offense=UnitEfficiency(epa_per_play=0.08, success_rate=0.47, plays=1000),
        defense=UnitEfficiency(epa_per_play=-0.08, success_rate=0.41, plays=1000),
        games_played=17,
        variance=0.55,
        source="prior",
        prior_season=2025,
    )
    # One-game outlier: absurd off EPA should not fully rewrite book.
    current = TeamEfficiencyPackage(
        team="NE",
        offense=UnitEfficiency(epa_per_play=0.45, success_rate=0.70, plays=60),
        defense=UnitEfficiency(epa_per_play=-0.40, success_rate=0.25, plays=60),
        games_played=1,
        variance=uncertainty_from_games(1),
        source="current",
    )
    blended = blend_packages(prior, current)
    assert blended.notes["blend_current_weight"] == 0.125
    assert blended.offense.epa_per_play < 0.20  # not worshipping the one-game spike


def test_packaged_backbone_smell_sea_ari_ne() -> None:
    packaged = build_packaged_real_universe(2026)
    assert packaged.notes.get("strength_source") in (
        STRENGTH_SOURCE_PACKAGED_EFFICIENCY,
        "packaged_epa_prior",  # legacy fallback if backbone file missing
    )
    sea = packaged.strengths["SEA"]
    ari = packaged.strengths["ARI"]
    assert sea.offense_index > ari.offense_index + 0.03
    assert sea.defense_index > ari.defense_index + 0.10
    assert (sea.offense_index + sea.defense_index) > (
        ari.offense_index + ari.defense_index + 0.15
    )

    ranked = sorted(
        packaged.strengths,
        key=lambda t: -(
            packaged.strengths[t].offense_index + packaged.strengths[t].defense_index
        ),
    )
    ne_rank = ranked.index("NE") + 1
    assert ne_rank <= 10, f"NE power rank {ne_rank} among {ranked}"
    assert packaged.strengths["NE"].offense_index >= 1.04
    assert "NE" not in set(ranked[-5:])
    # Demo bumps must stay demo-only.
    demo = build_demo_universe(2026)
    assert demo.strengths["NE"].source == STRENGTH_SOURCE_DEMO
    assert demo.strengths["NE"].offense_index < 0.96


def test_load_packaged_priors_prefer_backbone_when_present() -> None:
    priors, meta = load_packaged_epa_priors(2026)
    assert len(priors) == 32
    assert meta["team_count"] == 32
    # After artifact build, source should be efficiency backbone.
    # If only legacy file exists, still 32 teams with valid indices.
    for team, row in priors.items():
        assert 0.80 <= float(row["offense_index"]) <= 1.25
        assert 0.80 <= float(row["defense_index"]) <= 1.25


def test_packages_from_rows_opponent_centers() -> None:
    rows = [
        {
            "team": "AAA",
            "off_epa_per_play": 0.10,
            "def_epa_allowed_per_play": -0.10,
            "success_rate_offense": 0.50,
            "success_rate_defense_allowed": 0.40,
            "offensive_plays": 1000,
            "defensive_plays": 1000,
            "n_weeks": 17,
            "pass_rate": 0.58,
            "pressure_rate_generated": 0.16,
            "pressure_rate_allowed": 0.16,
            "red_zone_td_rate": 0.55,
        },
        {
            "team": "BBB",
            "off_epa_per_play": -0.10,
            "def_epa_allowed_per_play": 0.10,
            "success_rate_offense": 0.40,
            "success_rate_defense_allowed": 0.50,
            "offensive_plays": 1000,
            "defensive_plays": 1000,
            "n_weeks": 17,
            "pass_rate": 0.58,
            "pressure_rate_generated": 0.16,
            "pressure_rate_allowed": 0.16,
            "red_zone_td_rate": 0.55,
        },
    ]
    # Use real team codes so ranking helpers stay usable; opponent adjust is relative.
    rows[0]["team"] = "SEA"
    rows[1]["team"] = "ARI"
    pkgs = packages_from_team_rows(rows, as_of="test", prior_season=2025)
    ranked = rank_packages(pkgs)
    assert ranked[0][0] == "SEA"
    assert ranked[-1][0] == "ARI"
