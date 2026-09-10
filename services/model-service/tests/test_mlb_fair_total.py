"""MLB fair-total quantization contract — not a stub 9."""

from __future__ import annotations

from src.services.mlb_fair_total import (
    MLB_FAIR_TOTAL_QUANTIZATION,
    quantize_mlb_fair_total,
)
from src.services.mlb_simulator import MlbGameInputs, simulate_mlb_game


def test_smoking_gun_909_is_nearest_half_run_not_stub() -> None:
    # 2026-09-10 slate: totalMean ≈ 9.09 painted fairTotal/KEI 9.
    assert quantize_mlb_fair_total(9.09) == 9.0
    assert quantize_mlb_fair_total(9.10) == 9.0
    assert quantize_mlb_fair_total(9.11) == 9.0
    assert MLB_FAIR_TOTAL_QUANTIZATION == "nearest_half_run"


def test_varied_means_do_not_collapse_to_constant_nine() -> None:
    assert quantize_mlb_fair_total(8.24) == 8.0
    assert quantize_mlb_fair_total(8.26) == 8.5
    assert quantize_mlb_fair_total(8.74) == 8.5
    assert quantize_mlb_fair_total(8.76) == 9.0
    assert quantize_mlb_fair_total(9.24) == 9.0
    assert quantize_mlb_fair_total(9.26) == 9.5
    assert quantize_mlb_fair_total(7.5) == 7.5
    kei = {
        quantize_mlb_fair_total(8.24),
        quantize_mlb_fair_total(8.26),
        quantize_mlb_fair_total(9.26),
    }
    assert kei == {8.0, 8.5, 9.5}


def test_half_even_ties_match_python_round() -> None:
    # Exact .25 / .75 → *2 lands on .5 → banker's round.
    assert quantize_mlb_fair_total(8.25) == 8.0  # 16.5 → 16
    assert quantize_mlb_fair_total(8.75) == 9.0  # 17.5 → 18


def test_none_and_nan() -> None:
    assert quantize_mlb_fair_total(None) is None
    assert quantize_mlb_fair_total(float("nan")) is None


def test_simulator_fair_totals_match_certified_quantize() -> None:
    out = simulate_mlb_game(
        MlbGameInputs(
            game_id="quant-1",
            home_team="New York Yankees",
            away_team="Boston Red Sox",
            weather_temp_f=74.0,
            weather_wind_mph=8.0,
            weather_humidity_pct=55.0,
            park_factor_runs=1.03,
        ),
        simulations=800,
        seed=42,
    )
    markets = out["markets"]
    assert markets["fair_fg_total"] == quantize_mlb_fair_total(
        markets["fg_total_mean"]
    )
    assert markets["fair_f5_total"] == quantize_mlb_fair_total(
        markets["f5_total_mean"]
    )
    assert markets["fair_total_quantization"] == MLB_FAIR_TOTAL_QUANTIZATION
    # F5 and FG means stay distinct; both follow the same rule.
    assert markets["f5_total_mean"] != markets["fg_total_mean"]
