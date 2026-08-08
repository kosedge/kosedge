"""Smell tests for NFL Real QB Premium on the true-PR strength path."""

from __future__ import annotations

from collections import namedtuple

import src.tasks as tasks
from src.services.nfl_season_engine.continuity_score import (
    TRAVEL_FLOOR,
    build_team_continuity_from_inputs,
)
from src.services.nfl_season_engine.efficiency_backbone import (
    UnitEfficiency,
    TeamEfficiencyPackage,
    blend_packages,
    strength_payload_from_package,
)
from src.services.nfl_season_engine.injury_paths import apply_strength_shock
from src.services.nfl_season_engine.qb_premium import (
    PREMIUM_CAP,
    QbQualitySignal,
    apply_qb_premium_to_payload,
    build_team_qb_premium_from_inputs,
    compose_quality_z,
    map_quality_to_premium,
    sample_shrink_from_dropbacks,
)
from src.services.nfl_season_engine.team_strength import initialize_strengths
from src.services.nfl_season_engine.adjusted_sos import apply_past_sos_to_package


def _elite_signal(pid: str = "elite", name: str = "Elite QB") -> QbQualitySignal:
    return QbQualitySignal(
        player_id=pid,
        player_name=name,
        dropbacks=550,
        epa_per_play=0.22,
        success_rate=0.52,
        cpoe=4.5,
        source="epa_process",
        fidelity="real",
    )


def _avg_signal(pid: str = "avg", name: str = "Avg QB") -> QbQualitySignal:
    return QbQualitySignal(
        player_id=pid,
        player_name=name,
        dropbacks=480,
        epa_per_play=0.02,
        success_rate=0.46,
        cpoe=0.0,
        source="epa_process",
        fidelity="real",
    )


def _weak_signal(pid: str = "weak", name: str = "Weak QB") -> QbQualitySignal:
    return QbQualitySignal(
        player_id=pid,
        player_name=name,
        dropbacks=420,
        epa_per_play=-0.12,
        success_rate=0.40,
        cpoe=-3.2,
        source="epa_process",
        fidelity="real",
    )


def _thin_rookie_signal(pid: str = "rook", name: str = "Rookie") -> QbQualitySignal:
    return QbQualitySignal(
        player_id=pid,
        player_name=name,
        dropbacks=25,
        epa_per_play=0.18,  # flashy small sample — must not invent finished elite
        success_rate=0.51,
        cpoe=3.0,
        source="epa_process",
        fidelity="real",
        notes="thin camp/preseason-ish",
    )


def test_elite_qb_clear_positive_premium() -> None:
    """Smell 1: known elite QB → clear positive premium vs QB-neutral."""
    elite = build_team_qb_premium_from_inputs(
        "KC",
        starter=("15", "Mahomes"),
        prior_qb=("15", "Mahomes"),
        starter_signal=_elite_signal("15", "Mahomes"),
        prior_signal_dropbacks=600,
    )
    avg = build_team_qb_premium_from_inputs(
        "NE",
        starter=("10", "Avg"),
        prior_qb=("10", "Avg"),
        starter_signal=_avg_signal("10", "Avg"),
        prior_signal_dropbacks=500,
    )
    assert elite.premium_full > 0.015
    assert elite.premium_full > avg.premium_full + 0.01
    assert elite.fidelity == "real"
    assert elite.signal_source == "epa_process"
    assert abs(elite.premium_full) <= PREMIUM_CAP + 1e-9


def test_weak_qb_clear_penalty() -> None:
    """Smell 2: weak / replacement QB → clear penalty."""
    weak = build_team_qb_premium_from_inputs(
        "CAR",
        starter=("9", "Weak"),
        prior_qb=("9", "Weak"),
        starter_signal=_weak_signal("9", "Weak"),
        prior_signal_dropbacks=400,
    )
    avg = build_team_qb_premium_from_inputs(
        "NE",
        starter=("10", "Avg"),
        prior_qb=("10", "Avg"),
        starter_signal=_avg_signal("10", "Avg"),
        prior_signal_dropbacks=500,
    )
    # Same-QB residual is dampened vs team EPA, but still a clear drag vs average.
    assert weak.premium_full < -0.01
    assert weak.premium_full < avg.premium_full - 0.008
    assert weak.premium_full >= -PREMIUM_CAP - 1e-9


def test_new_starter_does_not_invent_finished_elite() -> None:
    """Smell 3: new/thin starter — continuity low travel; premium not fake-elite."""
    cont = build_team_continuity_from_inputs(
        "NYJ",
        prior_qb=("8", "Old"),
        current_qb=("7", "New"),
        prior_qb_on_roster=False,
        staff={"new_hc": False, "new_oc": True, "status": "approximate"},
        skill_return_share=0.40,
        roster_return_share=0.45,
    )
    assert cont.continuity_score <= 0.55
    assert cont.prior_travel_weight >= TRAVEL_FLOOR - 1e-9
    assert cont.prior_travel_weight < 0.85

    thin = build_team_qb_premium_from_inputs(
        "NYJ",
        starter=("7", "New"),
        prior_qb=("8", "Old"),
        starter_signal=_thin_rookie_signal("7", "New"),
        prior_signal_dropbacks=0,
    )
    # Thin sample + first-year/rookie → smaller mean + wider uncertainty.
    assert thin.sample_shrink < 0.35
    assert thin.premium_full < 0.025  # not a finished elite identity
    assert thin.variance_boost >= 0.10
    assert thin.tenure in ("rookie", "first_year")


def test_hierarchy_not_chaos_reordered_by_qb_flip() -> None:
    """Smell 4: single QB flip does not absurdly reorder league hierarchy."""
    sea_base = 1.12
    ari_base = 0.94
    sea = build_team_qb_premium_from_inputs(
        "SEA",
        starter=("1", "Good"),
        prior_qb=("1", "Good"),
        starter_signal=_elite_signal("1", "Good"),
        prior_signal_dropbacks=500,
    )
    # ARI suddenly gets an elite QB — lift capped; cannot leapfrog SEA absurdly
    # when SEA already starts much stronger on the reconstructed team.
    ari = build_team_qb_premium_from_inputs(
        "ARI",
        starter=("2", "EliteNew"),
        prior_qb=("3", "Old"),
        starter_signal=_elite_signal("2", "EliteNew"),
        prior_signal_dropbacks=500,
    )
    sea_adj = sea_base + sea.premium_full
    ari_adj = ari_base + ari.premium_full
    assert ari.premium_full <= PREMIUM_CAP + 1e-9
    assert sea_adj > ari_adj  # still SEA ahead; elite QB ≠ rewrite the board
    assert (sea_adj - ari_adj) > 0.05


def test_past_sos_blend_continuity_still_healthy() -> None:
    """Smell 5: Past SOS polarity, games/8, continuity travel remain intact."""
    from src.services.nfl_season_engine.adjusted_sos import TeamPastSos

    soft = TeamEfficiencyPackage(
        team="SOFT",
        offense=UnitEfficiency(epa_per_play=0.10, success_rate=0.47, plays=900),
        defense=UnitEfficiency(epa_per_play=0.02, success_rate=0.43, plays=900),
        games_played=17,
        notes={"off_epa_raw": 0.10, "def_epa_raw": 0.02},
    )
    hard = TeamEfficiencyPackage(
        team="HARD",
        offense=UnitEfficiency(epa_per_play=-0.02, success_rate=0.43, plays=900),
        defense=UnitEfficiency(epa_per_play=-0.02, success_rate=0.45, plays=900),
        games_played=17,
        notes={"off_epa_raw": -0.02, "def_epa_raw": -0.02},
    )
    # Soft schedule → adj EPA down; hard schedule → adj EPA up.
    soft_sos = TeamPastSos(
        team="SOFT",
        games=16,
        actual_sos_offense=0.08,
        actual_sos_defense=-0.04,
        raw_off_epa=0.10,
        raw_def_epa_allowed=0.02,
        schedule_adj_off_epa=0.06,
        schedule_adj_def_epa_allowed=0.03,
        time_of_game_games=16,
        status="applied_time_of_game",
    )
    hard_sos = TeamPastSos(
        team="HARD",
        games=16,
        actual_sos_offense=-0.06,
        actual_sos_defense=0.05,
        raw_off_epa=-0.02,
        raw_def_epa_allowed=-0.02,
        schedule_adj_off_epa=0.01,
        schedule_adj_def_epa_allowed=-0.04,
        time_of_game_games=16,
        status="applied_time_of_game",
    )
    soft_adj = apply_past_sos_to_package(soft, soft_sos)
    hard_adj = apply_past_sos_to_package(hard, hard_sos)
    assert soft_adj.offense.epa_per_play < soft.offense.epa_per_play
    assert hard_adj.offense.epa_per_play > hard.offense.epa_per_play

    high_c = build_team_continuity_from_inputs(
        "KC",
        prior_qb=("1", "M"),
        current_qb=("1", "M"),
        prior_qb_on_roster=True,
        staff={"new_hc": False, "new_oc": False, "status": "approximate"},
        skill_return_share=0.9,
        roster_return_share=0.7,
    )
    blended = blend_packages(
        soft_adj,
        soft_adj,
        current_games=4,
        prior_travel_weight=high_c.prior_travel_weight,
        continuity_score=high_c.continuity_score,
    )
    assert abs(blended.notes["blend_current_weight"] - 0.5) < 1e-9
    # games/8 still owns current weight; continuity only scales residual prior.
    assert blended.notes["blend_prior_weight"] == round(0.5 * high_c.prior_travel_weight, 4)

    # Player finite-production path still importable / healthy (smoke).
    from src.services.nfl_season_engine.player_regression import apply_process_priors

    assert callable(apply_process_priors)


def test_full_strength_differs_when_starter_out() -> None:
    """Smell 6: full-strength ≠ current when starter unavailable (backup path)."""
    prem = build_team_qb_premium_from_inputs(
        "BUF",
        starter=("17", "Allen"),
        backup=("10", "Backup"),
        prior_qb=("17", "Allen"),
        starter_signal=_elite_signal("17", "Allen"),
        backup_signal=_weak_signal("10", "Backup"),
        prior_signal_dropbacks=600,
        starter_available=False,
    )
    assert prem.premium_full > 0.015
    assert prem.premium_current < prem.premium_full
    payload = {
        "offense_index": 1.08,
        "defense_index": 1.05,
        "full_strength_offense_index": 1.08,
        "full_strength_defense_index": 1.05,
        "current_offense_index": 1.08,
        "current_defense_index": 1.05,
        "injury_delta_offense": 0.0,
        "variance": 1.20,
        "drivers": {"stubs": {}},
    }
    out = apply_qb_premium_to_payload(payload, prem)
    assert out["full_strength_offense_index"] > out["offense_index"]
    assert out["injury_delta_offense"] < 0.0
    assert out["drivers"]["stubs"]["qb_premium"] == "applied"
    assert out["drivers"]["injury_availability_delta"]["status"] == "qb_starter_unavailable"

    # Injury shock path still preserves full-strength separately.
    book = initialize_strengths(
        {
            "BUF": {
                "offense_index": out["full_strength_offense_index"],
                "defense_index": out["defense_index"],
                "full_strength_offense_index": out["full_strength_offense_index"],
                "full_strength_defense_index": out["full_strength_defense_index"],
                "qb_premium": out["qb_premium"],
                "drivers": out["drivers"],
            }
        }
    )
    assert book["BUF"].qb_premium == out["qb_premium"]
    # apply_strength_shock locks full-strength from pre-shock current on first scar.
    shocked = apply_strength_shock(book["BUF"], offense_delta=-0.05)
    assert shocked.offense_index < shocked.full_strength_offense_index


def test_drivers_show_qb_contribution_and_counting_fallback_labeled() -> None:
    """Smell 7: drivers expose QB contribution; counting fallback labeled."""
    counting = QbQualitySignal(
        player_id="c1",
        player_name="Counting",
        dropbacks=300,
        yards_per_attempt=8.2,
        completion_rate=0.68,
        source="counting_fallback",
        fidelity="approximate",
    )
    z, src, notes = compose_quality_z(counting)
    assert src == "counting_fallback"
    assert any("fallback" in n for n in notes)
    prem = build_team_qb_premium_from_inputs(
        "WAS",
        starter=("c1", "Counting"),
        prior_qb=("c1", "Counting"),
        starter_signal=counting,
        prior_signal_dropbacks=300,
    )
    assert prem.fidelity == "approximate"
    drivers = prem.to_drivers()
    assert drivers["premium_full"] == prem.premium_full
    assert drivers["signal_source"] == "counting_fallback"
    assert "anti_double_count" in drivers["detail"]


def test_caps_and_sample_shrink_math() -> None:
    assert sample_shrink_from_dropbacks(0) == 0.0
    assert sample_shrink_from_dropbacks(500) == 1.0
    assert abs(map_quality_to_premium(10.0, sample_shrink=1.0, identity_weight=1.0)) <= PREMIUM_CAP
    assert map_quality_to_premium(2.0, sample_shrink=0.0, identity_weight=1.0) == 0.0


def test_live_loader_applies_qb_premium(monkeypatch) -> None:
    """Live loader wires premium onto offense indices + drivers."""
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
                            2025, 18, "KC", 0.04, -0.05, 0.2, 0.14, 0.58, 0.47, 0.41, 0.58, 5
                        ),
                        Row(
                            2025, 18, "CAR", 0.04, -0.05, 0.18, 0.16, 0.58, 0.47, 0.41, 0.55, 5
                        ),
                    ]
                )
            raise AssertionError(query)

    elite = build_team_qb_premium_from_inputs(
        "KC",
        starter=("15", "Mahomes"),
        prior_qb=("15", "Mahomes"),
        starter_signal=_elite_signal("15", "Mahomes"),
        prior_signal_dropbacks=600,
    )
    weak = build_team_qb_premium_from_inputs(
        "CAR",
        starter=("9", "Weak"),
        prior_qb=("9", "Weak"),
        starter_signal=_weak_signal("9", "Weak"),
        prior_signal_dropbacks=400,
    )
    monkeypatch.setattr(
        "src.services.nfl_season_engine.loaders.load_packaged_epa_priors",
        lambda season: ({}, {}),
    )
    monkeypatch.setattr(
        "src.services.nfl_season_engine.continuity_score.build_continuity_book",
        lambda *a, **k: {},
    )
    monkeypatch.setattr(
        "src.services.nfl_season_engine.qb_premium.build_qb_premium_book",
        lambda *a, **k: {"KC": elite, "CAR": weak},
    )
    out = tasks._load_team_strength_priors(_Session(), season_year=2026, as_of_week=1)
    assert out["KC"]["qb_premium"] == elite.premium_full
    assert out["CAR"]["qb_premium"] == weak.premium_full
    assert out["KC"]["offense_index"] > out["CAR"]["offense_index"]
    assert out["KC"]["drivers"]["stubs"]["qb_premium"] == "applied"
    assert out["KC"]["drivers"]["qb_premium"]["starter_name"] == "Mahomes"
    # Same reconstructed EPA base → premium alone separates them.
    assert out["KC"]["full_strength_offense_index"] - out["CAR"]["full_strength_offense_index"] > 0.03


def test_new_good_qb_not_erased_by_continuity_alone() -> None:
    """New + good: low travel shrinks prior, premium still adds identity lift."""
    cont = build_team_continuity_from_inputs(
        "NYJ",
        prior_qb=("8", "Old"),
        current_qb=("7", "GoodNew"),
        prior_qb_on_roster=False,
        staff={"new_hc": True, "new_oc": True, "status": "approximate"},
        skill_return_share=0.30,
        roster_return_share=0.35,
        major_churn=True,
    )
    prem = build_team_qb_premium_from_inputs(
        "NYJ",
        starter=("7", "GoodNew"),
        prior_qb=("8", "Old"),
        starter_signal=_elite_signal("7", "GoodNew"),
        prior_signal_dropbacks=500,
    )
    assert cont.prior_travel_weight < 0.70
    assert prem.same_as_prior is False
    assert prem.identity_weight >= 0.85  # fuller identity for new starter
    assert prem.premium_full > 0.02

    prior = TeamEfficiencyPackage(
        team="NYJ",
        offense=UnitEfficiency(epa_per_play=0.05, plays=900),
        defense=UnitEfficiency(epa_per_play=-0.02, plays=900),
        games_played=17,
    )
    # Low travel shrinks toward league mean; premium re-adds starter quality.
    blended = blend_packages(
        prior,
        prior,
        current_games=0,
        prior_travel_weight=cont.prior_travel_weight,
        continuity_score=cont.continuity_score,
    )
    payload = strength_payload_from_package(blended)
    with_prem = apply_qb_premium_to_payload(payload, prem)
    # Relative to continuity-shrunk baseline, premium lifts offense.
    assert with_prem["offense_index"] > payload["offense_index"]
    assert with_prem["variance"] >= payload["variance"]


def test_same_qb_premium_dampened_vs_new_qb() -> None:
    """Anti-double-count: same-QB residual < new-QB fuller identity for same signal."""
    sig = _elite_signal("15", "Mahomes")
    same = build_team_qb_premium_from_inputs(
        "KC",
        starter=("15", "Mahomes"),
        prior_qb=("15", "Mahomes"),
        starter_signal=sig,
        prior_signal_dropbacks=600,
    )
    new = build_team_qb_premium_from_inputs(
        "NYJ",
        starter=("15", "Mahomes"),
        prior_qb=("8", "Old"),
        starter_signal=sig,
        prior_signal_dropbacks=600,
    )
    assert same.identity_weight < new.identity_weight
    assert same.premium_full < new.premium_full
