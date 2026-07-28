from src.services.mlb_lineup_shock import (
    apply_lineup_shock,
    compute_lineup_shock,
    resolve_nowcast_starters,
)
from src.services.mlb_pa_feature_sharpen import compute_sp_change_shock
from src.services.mlb_simulator import MlbGameInputs


def test_lineup_shock_is_bounded() -> None:
    shock = compute_lineup_shock(
        prior_confidence_home=0.40,
        prior_confidence_away=0.85,
        new_confidence_home=0.95,
        new_confidence_away=0.85,
        max_abs_shock=0.08,
    )
    assert 1.0 < shock["home_offense_mul"] <= 1.08
    assert shock["away_offense_mul"] == 1.0


def test_apply_lineup_shock_moves_home_offense() -> None:
    base = MlbGameInputs(
        game_id="g1",
        home_team="A",
        away_team="B",
        lineup_confidence_home=0.95,
        offense_home=1.0,
        lineup_strength_index_home=1.0,
    )
    updated, diag = apply_lineup_shock(base, prior_confidence_home=0.45, prior_confidence_away=0.85)
    assert updated.offense_home > base.offense_home
    assert "lineup_shock" in diag


def test_sp_change_shock_is_recorded() -> None:
    base = MlbGameInputs(
        game_id="g2",
        home_team="A",
        away_team="B",
        starter_home="New Starter",
        starter_quality_home=0.92,
        lineup_confidence_home=0.90,
        offense_away=1.0,
    )
    updated, diag = apply_lineup_shock(
        base,
        prior_confidence_home=0.90,
        prior_confidence_away=0.90,
        prior_starter_home="Old Starter",
        prior_starter_away=None,
        prior_starter_quality_home=1.12,
        prior_starter_quality_away=1.0,
    )
    assert diag["sp_change_shock"]["home"]["changed"] == 1.0
    assert 0.78 <= updated.offense_away <= 1.25
    assert "sp_change_shock" in diag


def test_resolve_nowcast_starters_detects_sp_change() -> None:
    resolved = resolve_nowcast_starters(
        context_home="Ace Acevedo",
        context_away="Buddy Bullpen",
        live_home="Scratch Starter",
        live_away="Buddy Bullpen",
    )
    assert resolved["home_changed"] is True
    assert resolved["away_changed"] is False
    assert resolved["any_changed"] is True
    assert resolved["new_home"] == "Scratch Starter"
    assert resolved["prior_home"] == "Ace Acevedo"


def test_sp_change_shock_is_bounded_and_nonzero() -> None:
    shock = compute_sp_change_shock(
        prior_starter="Ace Acevedo",
        new_starter="Scratch Starter",
        prior_quality=0.92,
        new_quality=1.12,
        max_abs_allowed_shock=0.07,
    )
    assert shock["changed"] == 1.0
    assert 1.0 < shock["allowed_mul"] <= 1.07


def test_apply_lineup_shock_reprices_on_sp_change() -> None:
    base = MlbGameInputs(
        game_id="g2",
        home_team="A",
        away_team="B",
        starter_home="Scratch Starter",
        starter_away="Buddy Bullpen",
        starter_quality_home=1.12,
        starter_quality_away=1.0,
        lineup_confidence_home=0.80,
        lineup_confidence_away=0.80,
        offense_home=1.0,
        offense_away=1.0,
        lineup_strength_index_home=1.0,
        lineup_strength_index_away=1.0,
    )
    updated, diag = apply_lineup_shock(
        base,
        prior_confidence_home=0.80,
        prior_confidence_away=0.80,
        prior_starter_home="Ace Acevedo",
        prior_starter_away="Buddy Bullpen",
        prior_starter_quality_home=0.92,
        prior_starter_quality_away=1.0,
    )
    # Home SP worsened for hitters facing him → away offense nudged up (bounded).
    assert updated.offense_away != base.offense_away or updated.offense_home != base.offense_home
    assert diag["sp_change_shock"]["home"]["changed"] == 1.0
    assert 0.78 <= updated.offense_away <= 1.25
    assert 0.78 <= updated.offense_home <= 1.25
