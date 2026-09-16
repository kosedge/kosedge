"""KE Football v1 Phase 2A — unit ratings (Off/Def Efficiency).

No Team Strength. No ATS. No opponent-adjustment reopen.
"""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.ke_football import (
    OPP_ADJ_PROMOTED,
    OPP_ADJ_RESULT,
    PHASE,
    PRODUCTION_PROMOTE,
    TAXONOMY,
)
from src.services.ke_football.aggregate import build_team_games
from src.services.ke_football.provenance import Layer, modeled
from src.services.ke_football.unit_features import (
    FEATURE_BOOK,
    assert_not_excluded,
    feature_policy,
    pass_core_ids,
    specs_for,
)
from src.services.ke_football.unit_ratings import (
    FORBIDDEN_OBJECTIVES,
    MethodFit,
    clear_z_cache,
    fit_selection,
    pca_loadings,
    predict_method,
    ridge_fit,
    shrink,
    snapshot_book,
)
from src.services.ke_football.unit_validate import (
    evaluate_methods,
    future_week_changes_unit,
    run_phase2a,
)
from tests.test_ke_football_measurement import _slate


def test_phase2a_flags() -> None:
    assert PRODUCTION_PROMOTE is False
    assert TAXONOMY == ("RAW", "DERIVED", "ADJUSTED", "MODELED")
    assert PHASE == "unit_ratings_phase2a"
    assert OPP_ADJ_PROMOTED is False
    assert OPP_ADJ_RESULT == "NO_ADJUSTMENT_WINNER"
    assert "ats" in FORBIDDEN_OBJECTIVES


def test_feature_policy_excludes_forbidden() -> None:
    for sport in ("nfl", "cfb"):
        pol = feature_policy(sport=sport)
        assert pol["opp_adj_reopened"] is False
        assert pol["named_havoc"] is False
        assert pol["team_strength"] is False
        assert pol["pace_in_unit_rating"] is False
        assert pol["finishing_auto_promote"] is False
        for side in ("off", "def"):
            ids = [s.cid for s in specs_for(sport, side)]
            assert_not_excluded(ids, sport=sport)
            assert "ke.havoc" not in ids
            assert "ke.team_strength" not in ids
            assert "ke.pace" not in ids
            assert "ke.st" not in ids
    assert "ke.off_eff" in FEATURE_BOOK["nfl"]["off"]["pass"]
    assert "ke.finish" in FEATURE_BOOK["nfl"]["off"]["partial_research"]
    assert "ke.finish" not in FEATURE_BOOK["nfl"]["off"]["pass"]
    nfl_def = [s.cid for s in specs_for("nfl", "def")]
    assert "ke.disruption_proxy_nfl" in nfl_def
    cfb_def = [s.cid for s in specs_for("cfb", "def")]
    assert "ke.disruption_sack" not in cfb_def
    assert "ke.havoc" not in cfb_def


def test_assert_excluded_raises() -> None:
    try:
        assert_not_excluded(["ke.havoc"], sport="nfl")
    except AssertionError:
        return
    raise AssertionError("expected exclusion")


def test_linalg_ridge_and_pca() -> None:
    X = [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0], [2.0, 1.0]]
    y = [1.0, 1.0, 2.0, 3.0]
    beta = ridge_fit(X, y, lam=0.1)
    assert beta is not None and len(beta) == 3
    w = pca_loadings(X)
    assert w is not None and abs(sum(x * x for x in w) - 1.0) < 1e-6
    assert shrink(1.0, 0.0, 10.0, 0.0) == 0.0
    assert shrink(None, 10.0, 10.0, 0.0) is None


def test_modeled_publisher() -> None:
    cell = modeled("ke.off_unit", 0.05, unit="epa_per_play", n=200)
    assert cell.layer == Layer.MODELED
    assert cell.value == 0.05
    empty = modeled("ke.off_unit", None, unit="epa_per_play", n=0)
    assert empty.value is None
    assert empty.status.value == "DATA_INSUFFICIENT"


def test_unit_bakeoff_on_slate_no_team_strength() -> None:
    clear_z_cache()
    games = build_team_games(_slate())
    fit = fit_selection(games, sport="nfl", side="off", selection_weeks=(2, 2))
    ev = evaluate_methods(
        games,
        sport="nfl",
        side="off",
        fit=fit,
        selection_weeks=(2, 2),
        confirmation_weeks=(2, 2),
        full_weeks=(2, 2),
    )
    assert ev["production_promote"] is False
    assert "ats" in ev["forbidden"]
    assert ev["winner"] in {
        "epa_raw",
        "epa_shrunken",
        "z_pass",
        "z_earned",
        "pca_earned",
        "ridge_earned",
    }
    book = snapshot_book(
        games,
        sport="nfl",
        season=2025,
        as_of_week=3,
        fits={"off": fit, "def": fit},
        methods={"off": ev["winner"], "def": "epa_raw"},
    )
    assert book
    assert all(r["components"]["ke.team_strength"]["status"] == "OMIT" for r in book)
    assert all(r["production_promote"] is False for r in book)


def test_unit_leakage_future_week() -> None:
    clear_z_cache()
    games = build_team_games(_slate())
    fit = MethodFit()
    from copy import deepcopy

    leak = deepcopy(games[0])
    leak.week = 3
    leak.game_id = "LEAK_FUTURE"
    leak.off_epa_sum = 50.0
    leak.off_epa_n = 80
    assert (
        future_week_changes_unit(
            games,
            sport="nfl",
            side="off",
            team=leak.team,
            as_of_week=3,
            method="epa_raw",
            fit=fit,
            future_game=leak,
        )
        is False
    )


def test_run_phase2a_hard_stops() -> None:
    clear_z_cache()
    games = build_team_games(_slate())
    out = run_phase2a(
        games,
        sport="nfl",
        season=2025,
        as_of_week=3,
        example_teams=["AAA"],
        selection_weeks=(2, 2),
        confirmation_weeks=(2, 2),
        full_weeks=(2, 2),
        early_through=1,
        late_from=2,
    )
    assert out["production_promote"] is False
    assert out["hard_stops"]["team_strength"] is False
    assert out["opp_adj_reopened"] is False
    assert out["grades"]["off"]["id"] == "ke.off_unit"
    assert out["grades"]["def"]["id"] == "ke.def_unit"
    assert out["leakage_live"]["future_week_changes_unit"]["off"] is False
    core = pass_core_ids("nfl", "off")
    assert "ke.off_eff" in core
    assert "ke.finish" not in core
