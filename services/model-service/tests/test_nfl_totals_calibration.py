from src.services.nfl_totals_calibration import _fit_linear_calibration, apply_totals_calibration


def test_fit_linear_calibration_is_mean_preserving_under_slope_clamp(monkeypatch) -> None:
    monkeypatch.setenv("NFL_FRAMEWORK_PRIOR_TOTAL_POINTS", "43.5")
    monkeypatch.setenv("NFL_TOTALS_CALIBRATION_PRIOR_REFERENCE", "43.5")
    # Predictions systematically ~4pts low — the failure mode that flooded Unders.
    points = [
        {"pred_total": 42.0 + (i % 5) * 0.3, "actual_total": 46.0 + (i % 5) * 0.3}
        for i in range(120)
    ]
    fit = _fit_linear_calibration(
        points,
        min_sample_size=80,
        slope_min=0.8,
        slope_max=1.2,
        intercept_abs_max=18.0,
    )
    assert fit["eligible"] is True
    assert abs(float(fit["signed_bias_post"])) < 0.2
    assert float(fit["signed_bias_pre"]) < -3.0
    # Applying at training mean should land near actual mean (~46).
    pred_mean = float(fit["pred_mean"])
    calibrated_mean = apply_totals_calibration(pred_mean, fit)
    assert calibrated_mean is not None
    assert abs(float(calibrated_mean) - float(fit["actual_mean"])) < 0.25


def test_old_intercept_clamp_would_break_mean_new_fit_does_not(monkeypatch) -> None:
    monkeypatch.setenv("NFL_FRAMEWORK_PRIOR_TOTAL_POINTS", "43.5")
    monkeypatch.setenv("NFL_TOTALS_CALIBRATION_PRIOR_REFERENCE", "43.5")
    points = [{"pred_total": 42.5, "actual_total": 46.5} for _ in range(100)]
    fit = _fit_linear_calibration(
        points,
        min_sample_size=80,
        slope_min=0.8,
        slope_max=1.2,
        intercept_abs_max=18.0,
    )
    # Broken legacy behavior: slope clamped to 0.8 and intercept to +8
    # yields 0.8*42.5+8 = 42.0 (still low / worse).
    legacy = (0.8 * 42.5) + 8.0
    fixed = apply_totals_calibration(42.5, fit)
    assert fixed is not None
    assert float(fixed) > legacy + 3.0
    assert abs(float(fixed) - 46.5) < 0.3


def test_apply_totals_calibration_skips_ineligible() -> None:
    out = apply_totals_calibration(44.0, {"slope": 1.2, "intercept": -6.0, "eligible": False, "sample_size": 200})
    assert out == 44.0


def test_fit_prefers_level_shift_for_pure_bias(monkeypatch) -> None:
    # Disable prior-delta adjustment for this unit case.
    monkeypatch.setenv("NFL_FRAMEWORK_PRIOR_TOTAL_POINTS", "43.5")
    monkeypatch.setenv("NFL_TOTALS_CALIBRATION_PRIOR_REFERENCE", "43.5")
    points = [{"pred_total": 40.0 + i * 0.05, "actual_total": 44.0 + i * 0.05} for i in range(100)]
    fit = _fit_linear_calibration(
        points,
        min_sample_size=80,
        slope_min=0.85,
        slope_max=1.25,
        intercept_abs_max=18.0,
    )
    assert fit["fit_mode"] == "level_shift"
    assert abs(float(fit["slope"]) - 1.0) < 1e-9
    assert abs(float(fit["intercept"]) - 4.0) < 0.05
    assert abs(float(fit["signed_bias_post"])) < 0.05


def test_level_shift_removes_prior_delta(monkeypatch) -> None:
    monkeypatch.setenv("NFL_FRAMEWORK_PRIOR_TOTAL_POINTS", "45.3")
    monkeypatch.setenv("NFL_TOTALS_CALIBRATION_PRIOR_REFERENCE", "43.5")
    monkeypatch.setenv("NFL_TOTALS_LEVEL_SHIFT_SHRINK", "1.0")
    points = [{"pred_total": 42.0, "actual_total": 46.0} for _ in range(100)]
    fit = _fit_linear_calibration(
        points,
        min_sample_size=80,
        slope_min=0.85,
        slope_max=1.25,
        intercept_abs_max=18.0,
    )
    # Raw bias +4, prior lift +1.8 → remaining intercept ~+2.2
    assert fit["fit_mode"] == "level_shift"
    assert abs(float(fit["intercept"]) - 2.2) < 0.05


def test_prefers_level_shift_when_affine_slope_hits_clamp(monkeypatch) -> None:
    monkeypatch.setenv("NFL_FRAMEWORK_PRIOR_TOTAL_POINTS", "45.3")
    monkeypatch.setenv("NFL_TOTALS_CALIBRATION_PRIOR_REFERENCE", "45.3")
    # Near-zero mean bias but wild slope that will clamp to the max.
    points = []
    for i in range(100):
        x = 40.0 + (i % 20) * 0.5
        # Amplify residuals so OLS wants a steep slope while means stay close.
        y = 45.5 + 3.0 * (x - 45.0) + ((i % 3) - 1) * 0.2
        points.append({"pred_total": x, "actual_total": y})
    fit = _fit_linear_calibration(
        points,
        min_sample_size=80,
        slope_min=0.85,
        slope_max=1.25,
        intercept_abs_max=18.0,
    )
    assert fit["fit_mode"] == "level_shift"
    assert fit.get("slope_clamped") is True
    assert abs(float(fit["slope"]) - 1.0) < 1e-9


def test_apply_does_not_double_count_prior_on_live_slate(monkeypatch) -> None:
    """Live boards already on the new prior must not get the full historical lift."""
    monkeypatch.setenv("NFL_FRAMEWORK_PRIOR_TOTAL_POINTS", "45.3")
    monkeypatch.setenv("NFL_TOTALS_CALIBRATION_PRIOR_REFERENCE", "43.5")
    monkeypatch.delenv("NFL_TOTALS_LEVEL_SHIFT_SHRINK", raising=False)
    monkeypatch.setenv("NFL_TOTALS_LEVEL_SHIFT_SHRINK_DEFAULT_WITH_PRIOR_DELTA", "0.50")
    points = [{"pred_total": 42.5, "actual_total": 45.8} for _ in range(100)]
    fit = _fit_linear_calibration(
        points,
        min_sample_size=80,
        slope_min=0.85,
        slope_max=1.25,
        intercept_abs_max=18.0,
    )
    assert fit["fit_mode"] == "level_shift"
    # Historical intercept after prior_delta (~1.8) ≈ 45.8-42.5-1.8 = 1.5
    assert abs(float(fit["intercept"]) - 1.5) < 0.1

    # New slate already near market (~44.8); full +1.5 would overshoot to ~46.3.
    slate_pre = 44.8
    calibrated = apply_totals_calibration(44.8, fit, slate_pre_mean=slate_pre)
    assert calibrated is not None
    # Remaining gap to actual (~1.0) * shrink 0.5 ≈ 0.5 → ~45.3
    assert 45.0 <= float(calibrated) <= 45.6
    # Must be materially below naive full intercept apply.
    naive = 44.8 + float(fit["intercept"])
    assert float(calibrated) < naive - 0.7
