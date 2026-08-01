from src.services.mlb_lineup_shock import resolve_nowcast_starters
from src.services.mlb_lineup_timing import (
    allow_late_sp_clear,
    apply_lineup_timing_mode,
    apply_lineup_timing_to_inputs,
    get_lineup_timing_mode,
    per_side_lineup_confidence,
)
from src.services.mlb_simulator import MlbGameInputs


def test_per_side_requires_both_for_confirmed() -> None:
    one = per_side_lineup_confidence(
        known_home=9,
        known_away=4,
        probable_pitcher_home="A",
        probable_pitcher_away="B",
        hours_to_first_pitch=2.0,
        freshness_score=1.0,
    )
    both = per_side_lineup_confidence(
        known_home=9,
        known_away=9,
        probable_pitcher_home="A",
        probable_pitcher_away="B",
        hours_to_first_pitch=2.0,
        freshness_score=1.0,
    )
    assert one["home_confirmed"] is True
    assert one["away_confirmed"] is False
    assert one["lineup_confirmed"] is False
    assert both["lineup_confirmed"] is True
    assert both["home"] >= one["home"]


def test_late_sp_clear_only_when_sharp_and_near() -> None:
    prior = get_lineup_timing_mode()
    try:
        apply_lineup_timing_mode("off")
        assert allow_late_sp_clear(hours_to_first_pitch=1.0, lineup_confirmed=True) is False
        apply_lineup_timing_mode("sharp")
        assert allow_late_sp_clear(hours_to_first_pitch=1.0, lineup_confirmed=True) is True
        assert allow_late_sp_clear(hours_to_first_pitch=6.0, lineup_confirmed=True) is False
        assert allow_late_sp_clear(hours_to_first_pitch=1.0, lineup_confirmed=False) is False
    finally:
        apply_lineup_timing_mode(prior)


def test_resolve_nowcast_starters_allow_clear() -> None:
    kept = resolve_nowcast_starters(
        context_home="Ace",
        context_away="Buddy",
        live_home=None,
        live_away="Buddy",
        allow_clear=False,
    )
    cleared = resolve_nowcast_starters(
        context_home="Ace",
        context_away="Buddy",
        live_home=None,
        live_away="Buddy",
        allow_clear=True,
    )
    assert kept["new_home"] == "Ace"
    assert cleared["new_home"] is None
    assert cleared["home_changed"] is True


def test_apply_lineup_timing_to_inputs_sharp() -> None:
    prior = get_lineup_timing_mode()
    try:
        apply_lineup_timing_mode("sharp")
        base = MlbGameInputs(
            game_id="g1",
            home_team="A",
            away_team="B",
            starter_home="Ace",
            starter_away="Buddy",
            lineup_confidence_home=0.70,
            lineup_confidence_away=0.70,
            starter_firmness_home=0.80,
            starter_firmness_away=0.80,
        )
        updated, diag = apply_lineup_timing_to_inputs(
            base,
            known_home=9,
            known_away=9,
            hours_to_first_pitch=3.0,
            freshness_score=1.0,
        )
        assert diag["applied"] is True
        assert updated.lineup_confirmed is True
        assert updated.lineup_confidence_home > base.lineup_confidence_home
        assert updated.starter_firmness_home > base.starter_firmness_home
    finally:
        apply_lineup_timing_mode(prior)
