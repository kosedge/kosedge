from src.services.nfl_player_prop_calibration import (
    apply_prop_calibration,
    fit_prop_calibration_from_points,
    frozen_calibration_for,
)


def test_frozen_pass_has_negative_market_intercept() -> None:
    cal = frozen_calibration_for("pass_yds")
    assert cal.intercept < 0
    assert cal.std_multiplier > 1.0


def test_apply_widens_std_and_applies_pass_intercept() -> None:
    out = apply_prop_calibration(
        model_mean=240.0,
        model_std=40.0,
        market_key="pass_yds",
        market_line=None,
        role_confidence=0.8,
    )
    assert out["model_mean"] < 240.0
    assert out["model_std"] > 40.0


def test_market_shrink_stronger_when_low_role() -> None:
    solid = apply_prop_calibration(
        model_mean=200.0,
        model_std=40.0,
        market_key="pass_yds",
        market_line=210.0,  # small gap — base shrink only
        role_confidence=0.8,
    )
    weak = apply_prop_calibration(
        model_mean=200.0,
        model_std=40.0,
        market_key="pass_yds",
        market_line=210.0,
        role_confidence=0.4,
    )
    assert solid["market_shrink"] >= 0.12
    assert weak["market_shrink"] > solid["market_shrink"]
    assert weak["model_mean"] > solid["model_mean"]


def test_market_shrink_ramps_on_large_gap() -> None:
    close = apply_prop_calibration(
        model_mean=240.0,
        model_std=40.0,
        market_key="pass_yds",
        market_line=250.0,
        role_confidence=0.8,
    )
    far = apply_prop_calibration(
        model_mean=240.0,
        model_std=40.0,
        market_key="pass_yds",
        market_line=170.0,
        role_confidence=0.8,
    )
    assert far["market_shrink"] > close["market_shrink"]
    assert far["model_mean"] < close["model_mean"]


def test_pass_uses_stronger_market_shrink_base() -> None:
    pass_cal = apply_prop_calibration(
        model_mean=220.0,
        model_std=40.0,
        market_key="pass_yds",
        market_line=210.0,
        role_confidence=0.8,
    )
    rush_cal = apply_prop_calibration(
        model_mean=70.0,
        model_std=20.0,
        market_key="rush_yds",
        market_line=65.0,
        role_confidence=0.8,
    )
    assert pass_cal["market_shrink"] > rush_cal["market_shrink"]


def test_fit_from_points_recovers_level_shift() -> None:
    points = [{"pred": 10.0 + i * 0.01, "actual": 14.0 + i * 0.01, "std": 5.0} for i in range(100)]
    cal = fit_prop_calibration_from_points(points, market_key="rush_yds", min_sample_size=50)
    assert cal.eligible
    assert 3.5 < cal.intercept < 4.5
