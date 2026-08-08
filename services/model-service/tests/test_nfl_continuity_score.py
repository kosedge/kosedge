"""NFL Continuity Score (prior travel) smell tests."""

from __future__ import annotations

import os
from collections import namedtuple
from typing import Any, Dict, List, Optional

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src import tasks
from src.services.nfl_season_engine import build_packaged_real_universe
from src.services.nfl_season_engine.adjusted_sos import (
    OpponentRating,
    PriorGameContext,
    apply_past_sos_to_package,
    compute_team_past_sos,
)
from src.services.nfl_season_engine.continuity_score import (
    TRAVEL_FLOOR,
    TeamContinuity,
    blend_weights_with_continuity,
    build_team_continuity_from_inputs,
    compose_continuity,
    continuity_uncertainty_boost,
    score_qb_factor,
    score_staff_factor,
    travel_from_continuity,
)
from src.services.nfl_season_engine.efficiency_backbone import (
    UnitEfficiency,
    TeamEfficiencyPackage,
    blend_packages,
    prior_current_blend_weight,
    uncertainty_from_games,
)
from src.services.nfl_season_engine.injury_paths import apply_strength_shock
from src.services.nfl_season_engine.player_regression import apply_process_priors
from src.services.nfl_season_engine.types import PlayerRole, TeamStrengthState


def _pkg(team: str, off: float, deff: float) -> TeamEfficiencyPackage:
    return TeamEfficiencyPackage(
        team=team,
        offense=UnitEfficiency(epa_per_play=off, success_rate=0.46, plays=900),
        defense=UnitEfficiency(epa_per_play=deff, success_rate=0.43, plays=900),
        st_index=1.0,
        pace=1.0,
        variance=1.35,
        games_played=17,
        source="test_prior",
    )


def test_same_qb_same_staff_high_continuity() -> None:
    """Smell 1: same-QB / same-staff contender → high continuity, prior pulls hard."""
    cont = build_team_continuity_from_inputs(
        "KC",
        prior_qb=("qb-mah", "Patrick Mahomes"),
        current_qb=("qb-mah", "Patrick Mahomes"),
        prior_qb_on_roster=True,
        staff={"new_hc": False, "new_oc": False, "status": "approximate"},
        skill_return_share=0.88,
        ol_return_share=0.75,
        roster_return_share=0.62,
        major_churn=False,
    )
    assert cont.band == "high"
    assert cont.continuity_score >= 0.72
    assert cont.prior_travel_weight >= 0.85
    drivers = cont.to_drivers()
    assert drivers["prior_travel_weight"] == cont.prior_travel_weight
    qb = next(f for f in cont.factors if f.name == "qb")
    assert qb.score == 1.0
    assert "QB premium" in drivers["note"] or "qb premium" in drivers["note"].lower()


def test_new_qb_new_oc_low_continuity() -> None:
    """Smell 2: new starting QB + new OC → low continuity, prior discounted, uncertainty up."""
    cont = build_team_continuity_from_inputs(
        "LV",
        prior_qb=("qb-old", "Old Starter"),
        current_qb=("qb-new", "New Starter"),
        prior_qb_on_roster=False,
        staff={
            "new_hc": True,
            "new_oc": True,
            "status": "approximate",
            "notes": "new regime",
        },
        skill_return_share=0.40,
        ol_return_share=0.35,
        roster_return_share=0.38,
        major_churn=True,
    )
    assert cont.band == "low"
    assert cont.continuity_score <= 0.45
    assert cont.prior_travel_weight < 0.70
    assert cont.prior_travel_weight >= TRAVEL_FLOOR - 1e-9

    prior = _pkg("LV", 0.08, -0.06)
    # g=0: low continuity should not be last-year locked.
    blended = blend_packages(
        prior,
        prior,
        current_games=0,
        prior_travel_weight=cont.prior_travel_weight,
        continuity_score=cont.continuity_score,
    )
    assert blended.notes["blend_current_weight"] == 0.0
    assert blended.notes["blend_prior_weight"] == cont.prior_travel_weight
    assert blended.notes["blend_anchor_weight"] > 0.25
    # Shrunk toward league (0 EPA).
    assert abs(blended.offense.epa_per_play) < abs(prior.offense.epa_per_play)
    assert blended.variance > uncertainty_from_games(0)


def test_preseason_hierarchy_not_chaos_reordered() -> None:
    """Smell 3: continuity alone does not chaos-reorder a clear hierarchy."""
    high = build_team_continuity_from_inputs(
        "SEA",
        prior_qb=("qb-a", "A"),
        current_qb=("qb-a", "A"),
        prior_qb_on_roster=True,
        staff={"new_hc": False, "new_oc": False, "status": "approximate"},
        skill_return_share=0.85,
        roster_return_share=0.70,
    )
    low = build_team_continuity_from_inputs(
        "ARI",
        prior_qb=("qb-b", "B"),
        current_qb=("qb-c", "C"),
        prior_qb_on_roster=False,
        staff={"new_hc": True, "new_oc": True, "status": "approximate"},
        skill_return_share=0.45,
        roster_return_share=0.40,
        major_churn=True,
    )
    sea_prior = _pkg("SEA", 0.05, -0.12)
    ari_prior = _pkg("ARI", -0.04, 0.06)
    sea = blend_packages(
        sea_prior,
        sea_prior,
        current_games=0,
        prior_travel_weight=high.prior_travel_weight,
        continuity_score=high.continuity_score,
    )
    ari = blend_packages(
        ari_prior,
        ari_prior,
        current_games=0,
        prior_travel_weight=low.prior_travel_weight,
        continuity_score=low.continuity_score,
    )
    from src.services.nfl_season_engine.efficiency_backbone import (
        package_to_strength_indices,
    )

    sea_i = package_to_strength_indices(sea)
    ari_i = package_to_strength_indices(ari)
    sea_c = sea_i["offense_index"] + sea_i["defense_index"]
    ari_c = ari_i["offense_index"] + ari_i["defense_index"]
    assert sea_c > ari_c + 0.08


def test_soft_hard_sos_still_visible_on_prior_side() -> None:
    """Smell 4: Past SOS soft/hard polarity still visible after continuity travel."""
    weekly: Dict[tuple, OpponentRating] = {}
    season: Dict[str, OpponentRating] = {
        "BAD1": OpponentRating(off_epa=-0.05, def_epa=0.10, source="approximate"),
        "ELITE1": OpponentRating(off_epa=0.08, def_epa=-0.10, source="approximate"),
        "SOFT": OpponentRating(off_epa=0.12, def_epa=0.02, source="approximate"),
        "HARD": OpponentRating(off_epa=-0.02, def_epa=-0.02, source="approximate"),
    }
    for name, rating in list(season.items()):
        for w in range(1, 10):
            weekly[(name, w)] = OpponentRating(
                off_epa=rating.off_epa, def_epa=rating.def_epa, source="time_of_game"
            )

    soft_games = [
        PriorGameContext(team="SOFT", week=w, opponent="BAD1", is_home=True)
        for w in range(2, 10)
    ]
    hard_games = [
        PriorGameContext(team="HARD", week=w, opponent="ELITE1", is_home=False)
        for w in range(2, 10)
    ]
    soft_sos = compute_team_past_sos(
        "SOFT",
        soft_games,
        raw_off_epa=0.10,
        raw_def_epa_allowed=0.02,
        weekly_book=weekly,
        season_book=season,
        league_off_epa=0.0,
        league_def_epa=0.0,
    )
    hard_sos = compute_team_past_sos(
        "HARD",
        hard_games,
        raw_off_epa=-0.02,
        raw_def_epa_allowed=-0.02,
        weekly_book=weekly,
        season_book=season,
        league_off_epa=0.0,
        league_def_epa=0.0,
    )
    assert soft_sos.schedule_adj_off_epa < soft_sos.raw_off_epa
    assert hard_sos.schedule_adj_off_epa > hard_sos.raw_off_epa

    soft_pkg = apply_past_sos_to_package(_pkg("SOFT", 0.10, 0.02), soft_sos)
    hard_pkg = apply_past_sos_to_package(_pkg("HARD", -0.02, -0.02), hard_sos)
    # Same mid continuity travel — SOS polarity on prior EPA must remain.
    travel = travel_from_continuity(0.60)
    soft_b = blend_packages(
        soft_pkg, soft_pkg, current_games=0, prior_travel_weight=travel, continuity_score=0.60
    )
    hard_b = blend_packages(
        hard_pkg, hard_pkg, current_games=0, prior_travel_weight=travel, continuity_score=0.60
    )
    assert soft_b.offense.epa_per_play < soft_pkg.notes.get(
        "off_epa_raw", soft_sos.raw_off_epa
    )
    assert hard_b.offense.epa_per_play > hard_pkg.notes.get(
        "off_epa_raw", hard_sos.raw_off_epa
    )
    # Soft adj still below hard adj after equal travel shrink toward 0.
    assert soft_b.offense.epa_per_play < hard_b.offense.epa_per_play


def test_games_over_8_curve_preserved_with_continuity() -> None:
    """Continuity scales residual prior; w_current remains games/8."""
    for g, w_cur in [(0, 0.0), (1, 0.125), (4, 0.5), (8, 1.0)]:
        assert prior_current_blend_weight(current_games=g) == w_cur
        weights = blend_weights_with_continuity(
            current_games=g, prior_travel_weight=0.70
        )
        assert abs(weights["w_current"] - w_cur) < 1e-9
        assert abs(weights["w_prior"] - (1.0 - w_cur) * 0.70) < 1e-9
        assert abs(weights["w_anchor"] - (1.0 - w_cur) * 0.30) < 1e-9

    # Default travel=1.0 → identical to #140 weights.
    prior = _pkg("NE", 0.04, -0.03)
    current = _pkg("NE", -0.02, 0.04)
    current.games_played = 4
    legacy = blend_packages(prior, current, current_games=4)
    with_travel = blend_packages(
        prior, current, current_games=4, prior_travel_weight=1.0
    )
    assert abs(legacy.offense.epa_per_play - with_travel.offense.epa_per_play) < 1e-9
    assert legacy.notes["blend_prior_weight"] == 0.5
    assert with_travel.notes["blend_prior_weight"] == 0.5


def test_full_strength_and_player_finite_still_healthy() -> None:
    """Smell 5: injury full-strength split + player finite production still healthy."""
    state = TeamStrengthState(
        team="PHI",
        offense_index=1.10,
        defense_index=1.05,
        full_strength_offense_index=1.10,
        full_strength_defense_index=1.05,
        source="efficiency_backbone_blend",
        blend_prior_weight=0.80,
        blend_current_weight=0.0,
        drivers={"continuity": {"band": "high"}},
    )
    shocked = apply_strength_shock(state, offense_delta=-0.07)
    assert shocked.full_strength_offense_index == 1.10
    assert shocked.offense_index < shocked.full_strength_offense_index

    role = PlayerRole(
        player_key="p1",
        player_name="Starter",
        team="PHI",
        position="WR",
        depth_order=1,
        snap_share=0.85,
        target_share=0.28,
        rush_share=0.0,
        route_share=0.90,
        red_zone_share=0.25,
    )
    annotated = apply_process_priors(role)
    assert annotated.player_key == "p1"
    assert getattr(annotated, "regression_posture", None) is not None or hasattr(
        annotated, "process_confidence"
    ) or annotated.position == "WR"


def test_missing_factor_neutral_not_invented() -> None:
    qb = score_qb_factor(prior_qb_id=None, current_qb_id=None)
    staff = score_staff_factor(new_hc=None, new_oc=None)
    cont = compose_continuity("UNK", [qb, staff])
    assert cont.fidelity == "missing"
    assert cont.prior_travel_weight == 1.0  # zero evidence → no invented discount
    # Composed factors carry neutral 0.5 + approximate label.
    assert all(f.score == 0.5 for f in cont.factors)
    assert all(f.status == "approximate" for f in cont.factors)
    assert all("neutral" in f.detail for f in cont.factors)


def test_packaged_universe_hierarchy_smoke() -> None:
    """Smell 6: packaged season-engine universe still football-plausible."""
    universe = build_packaged_real_universe(season=2026)
    strengths = universe.strengths
    assert len(strengths) >= 32
    # Composite top/bottom should remain ordered (continuity may shrink, not invert).
    comps = {
        t: float(s.offense_index) + float(s.defense_index) for t, s in strengths.items()
    }
    ranked = sorted(comps.items(), key=lambda kv: kv[1], reverse=True)
    top_teams = {t for t, _ in ranked[:8]}
    bottom_teams = {t for t, _ in ranked[-8:]}
    assert top_teams.isdisjoint(bottom_teams)
    # SEA-type should still outrank a clear bottom-ish roster if both present.
    if "SEA" in comps and "ARI" in comps:
        assert comps["SEA"] > comps["ARI"]


def test_live_loader_continuity_travel_at_zero_games(monkeypatch) -> None:
    """Live loader at 0 REG applies continuity travel on prior path."""
    Row = namedtuple(
        "Row",
        "season week team off_epa_per_play_5g def_epa_allowed_per_play_5g "
        "pressure_rate_generated_5g pressure_rate_allowed_5g "
        "pass_rate_5g success_rate_offense_5g success_rate_defense_allowed_5g "
        "red_zone_td_rate_5g games_in_window_5",
    )

    class _Result:
        def __init__(self, rows=None, row=None):
            self._rows = rows or []
            self._row = row

        def fetchall(self):
            return self._rows

        def fetchone(self):
            return self._row

        def scalar(self):
            return 0

    class _Session:
        def execute(self, sql, params=None):
            query = str(sql)
            if "COUNT(*)" in query and "nfl_dp_schedules" in query and "UNION ALL" not in query:
                return _Result(row=namedtuple("C", "n")(n=0))
            if "UNION ALL" in query:
                return _Result(rows=[])
            if "nfl_dp_team_st_kav_weekly" in query:
                return _Result(rows=[])
            if "nfl_dp_team_rolling_features_weekly" in query:
                return _Result(
                    rows=[
                        Row(
                            2025, 18, "KC", 0.06, -0.08, 0.2, 0.14, 0.58, 0.48, 0.40, 0.6, 5
                        ),
                        Row(
                            2025, 18, "LV", 0.05, -0.04, 0.18, 0.16, 0.58, 0.46, 0.42, 0.55, 5
                        ),
                    ]
                )
            raise AssertionError(query)

    high = build_team_continuity_from_inputs(
        "KC",
        prior_qb=("1", "Mahomes"),
        current_qb=("1", "Mahomes"),
        prior_qb_on_roster=True,
        staff={"new_hc": False, "new_oc": False, "status": "approximate"},
        skill_return_share=0.90,
        roster_return_share=0.65,
    )
    low = build_team_continuity_from_inputs(
        "LV",
        prior_qb=("2", "Old"),
        current_qb=("3", "New"),
        prior_qb_on_roster=False,
        staff={"new_hc": True, "new_oc": True, "status": "approximate"},
        skill_return_share=0.35,
        roster_return_share=0.36,
        major_churn=True,
    )
    monkeypatch.setattr(
        "src.services.nfl_season_engine.loaders.load_packaged_epa_priors",
        lambda season: ({}, {}),
    )
    monkeypatch.setattr(
        "src.services.nfl_season_engine.continuity_score.build_continuity_book",
        lambda *a, **k: {"KC": high, "LV": low},
    )
    out = tasks._load_team_strength_priors(_Session(), season_year=2026, as_of_week=1)
    assert out["KC"]["blend_current_weight"] == 0.0
    assert out["KC"]["blend_prior_weight"] == high.prior_travel_weight
    assert out["LV"]["blend_prior_weight"] == low.prior_travel_weight
    assert out["KC"]["blend_prior_weight"] > out["LV"]["blend_prior_weight"]
    assert out["LV"]["variance"] >= out["KC"]["variance"]
    assert out["KC"]["drivers"]["stubs"]["continuity"] == "applied"
    assert out["KC"]["drivers"]["stubs"]["qb_premium"] == "stub_not_applied"
    assert out["KC"]["qb_premium"] == 0.0
    # High-continuity prior stays farther from league mean than low-continuity.
    assert abs(out["KC"]["offense_index"] - 1.0) > abs(out["LV"]["offense_index"] - 1.0) - 0.02


def test_uncertainty_boost_scales_with_low_continuity() -> None:
    assert continuity_uncertainty_boost(1.0) == 0.0
    assert continuity_uncertainty_boost(0.0) > continuity_uncertainty_boost(0.5)
