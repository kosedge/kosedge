from src.services.mlb_lineup_shock import apply_lineup_shock, compute_lineup_shock
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
