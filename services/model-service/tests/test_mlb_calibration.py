from src.services.mlb_calibration import (
    MLB_TOTAL_MAX,
    MLB_TOTAL_MIN,
    apply_total_calibrator,
    fit_total_calibrator,
)


def test_mlb_total_calibrator_stays_in_baseball_bounds() -> None:
    points = [
        {"fg_total_mean": 8.2 + (i % 5) * 0.15, "final_total_runs": 7.0 + (i % 6)}
        for i in range(40)
    ]
    fit = fit_total_calibrator(points)
    assert fit["eligible"] is True
    assert fit["sport"] == "mlb"
    calibrated = apply_total_calibrator(9.0, fit)
    assert MLB_TOTAL_MIN <= calibrated <= MLB_TOTAL_MAX


def test_mlb_total_calibrator_does_not_use_nfl_clamp() -> None:
    # A pathological NFL-style clamp would pin baseball totals near 24+.
    fit = {"slope": 1.0, "intercept": 0.0, "eligible": True, "sport": "mlb"}
    out = apply_total_calibrator(8.5, fit)
    assert out == 8.5
    assert out < 20.0


def test_ineligible_fit_passthrough_clamped() -> None:
    fit = fit_total_calibrator([{"fg_total_mean": 8.0, "final_total_runs": 9.0}])
    assert fit["eligible"] is False
    assert apply_total_calibrator(8.1, fit) == 8.1
