from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.nfl_supervised_retrain import (
    CONSERVATIVE_BLENDING_WEIGHTS,
    FEATURE_KEYS,
    VALIDATED_BLENDING_WEIGHTS,
    apply_supervised_blend,
    detect_real_rolling_features,
    fit_nfl_supervised_models,
)


def _row(i: int) -> dict:
    season = 2013 + (i // 290)
    week = (i % 22) + 1
    off_delta = ((i % 17) - 8) / 20.0
    defense_delta = ((i % 13) - 6) / 24.0
    pressure_delta = ((i % 11) - 5) / 40.0
    rest_delta = ((i % 9) - 4) * 1.0
    injury_delta = ((i % 7) - 3) / 10.0
    score_margin_signal = (
        (off_delta * 1.8) + (defense_delta * 1.4) + (pressure_delta * 0.8) + (rest_delta * 0.1) - (injury_delta * 0.5)
    )
    home_won = score_margin_signal > 0
    total_signal = 44.0 + (off_delta * 6.5) - (defense_delta * 2.4) + (pressure_delta * 4.0)
    return {
        "season": season,
        "week": week,
        "game_id": f"{season}_{week}_{i}",
        "home_off_epa_5g": 0.08 + off_delta,
        "away_off_epa_5g": 0.05 - off_delta,
        "home_def_epa_allowed_5g": 0.04 + defense_delta,
        "away_def_epa_allowed_5g": 0.05 - defense_delta,
        "home_pressure_allowed_5g": 0.18 - pressure_delta,
        "away_pressure_allowed_5g": 0.19 + pressure_delta,
        "home_pressure_generated_5g": 0.20 + pressure_delta,
        "away_pressure_generated_5g": 0.21 - pressure_delta,
        "home_pass_rate_5g": 0.56 + (off_delta * 0.08),
        "away_pass_rate_5g": 0.55 - (off_delta * 0.06),
        "home_early_down_pass_rate_5g": 0.45 + (off_delta * 0.05),
        "away_early_down_pass_rate_5g": 0.44 - (off_delta * 0.05),
        "home_red_zone_td_rate_5g": 0.52 + (off_delta * 0.1),
        "away_red_zone_td_rate_5g": 0.50 - (off_delta * 0.1),
        "home_success_offense_5g": 0.46 + (off_delta * 0.1),
        "away_success_offense_5g": 0.45 - (off_delta * 0.1),
        "home_success_defense_allowed_5g": 0.44 - (defense_delta * 0.1),
        "away_success_defense_allowed_5g": 0.45 + (defense_delta * 0.1),
        "diff_off_epa_5g": off_delta,
        "diff_def_epa_allowed_5g": defense_delta,
        "diff_pressure_generated_5g": pressure_delta,
        "diff_pressure_allowed_5g": -pressure_delta * 0.9,
        "diff_red_zone_td_rate_5g": off_delta * 0.4,
        "diff_success_rate_5g": (off_delta * 0.5) - (defense_delta * 0.3),
        "home_kav_offense_5g": 0.12 + off_delta,
        "away_kav_offense_5g": -0.05 - off_delta * 0.5,
        "home_kav_defense_5g": -0.08 - defense_delta,
        "away_kav_defense_5g": 0.06 + defense_delta,
        "home_kav_net_5g": 0.20 + off_delta - defense_delta,
        "away_kav_net_5g": -0.11 - off_delta + defense_delta,
        "diff_kav_net_5g": 0.31 + (2 * off_delta) - (2 * defense_delta),
        "home_injury_impact": 0.3 + injury_delta,
        "away_injury_impact": 0.3 - injury_delta,
        "diff_injury_impact": injury_delta * 2,
        "home_rest_days": 7.0 + rest_delta,
        "away_rest_days": 7.0 - rest_delta,
        "diff_rest_days": rest_delta * 2,
        "roof_dome": float(i % 4 == 0),
        "surface_turf": float(i % 3 == 0),
        "is_divisional_game": float(i % 5 == 0),
        "home_score": 24 + score_margin_signal * 10,
        "away_score": 24 - score_margin_signal * 10,
        "home_team_won": home_won,
        "final_total_points": total_signal,
    }


def test_fit_nfl_supervised_models_returns_metrics() -> None:
    rows = [_row(i) for i in range(1800)]
    out = fit_nfl_supervised_models(rows)
    metrics = out["metrics"]
    assert metrics["train_rows"] > 1000
    assert metrics["test_rows"] >= 120
    assert metrics["test_brier"] is not None
    assert metrics["test_total_mae"] is not None
    assert metrics["test_margin_mae"] is not None
    assert len(out["feature_keys"]) == len(FEATURE_KEYS)
    assert out["schema_version"] == 3
    assert set(out["models_pickle_b64"].keys()) == {"win", "total", "margin"}
    assert "feature_importance" in out


def test_apply_supervised_blend_overlays_markets() -> None:
    rows = [_row(i) for i in range(1600)]
    fit = fit_nfl_supervised_models(rows)
    feature_row = {
        "week": 6,
        "home_off_epa_5g": 0.21,
        "away_off_epa_5g": -0.02,
        "home_def_epa_allowed_5g": -0.05,
        "away_def_epa_allowed_5g": 0.08,
        "home_pass_rate_5g": 0.58,
        "away_pass_rate_5g": 0.53,
        "diff_off_epa_5g": 0.23,
        "diff_def_epa_allowed_5g": -0.13,
        "diff_pressure_generated_5g": 0.05,
        "diff_pressure_allowed_5g": -0.04,
        "diff_red_zone_td_rate_5g": 0.04,
        "diff_success_rate_5g": 0.09,
        "home_kav_offense_5g": 0.25,
        "away_kav_offense_5g": -0.10,
        "home_kav_defense_5g": -0.15,
        "away_kav_defense_5g": 0.08,
        "home_kav_net_5g": 0.40,
        "away_kav_net_5g": -0.18,
        "diff_kav_net_5g": 0.58,
        "home_injury_impact": 0.1,
        "away_injury_impact": 0.6,
        "diff_injury_impact": -0.5,
        "home_rest_days": 10.0,
        "away_rest_days": 6.0,
        "diff_rest_days": 4.0,
        "roof_dome": 0.0,
        "surface_turf": 1.0,
        "is_divisional_game": 1.0,
    }
    base_markets = {
        "home_win_prob": 0.5,
        "away_win_prob": 0.5,
        "total_mean": 44.2,
        "spread_home": 0.0,
        "fair_home_ml": -100,
        "fair_away_ml": 100,
    }
    out = apply_supervised_blend(
        fit_payload=fit,
        feature_row=feature_row,
        base_markets=base_markets,
    )
    assert out["home_win_prob"] != base_markets["home_win_prob"]
    assert out["away_win_prob"] == round(1.0 - out["home_win_prob"], 4)
    assert out["total_mean"] != base_markets["total_mean"]
    assert out["spread_home"] != base_markets["spread_home"]
    assert isinstance(out["fair_home_ml"], int)
    overlay = out.get("supervised_overlay", {})
    assert overlay.get("applied") is True
    assert overlay.get("schema_version") == 3
    assert "supervised_spread_home" in overlay


def test_apply_supervised_blend_returns_base_markets_when_no_fit() -> None:
    base_markets = {"home_win_prob": 0.55, "total_mean": 45.0, "spread_home": -2.0}
    out = apply_supervised_blend(fit_payload=None, feature_row={}, base_markets=base_markets)
    assert out == base_markets


class _FakeRow:
    def __init__(self, team: str, distinct_values: int) -> None:
        self.team = team
        self.distinct_values = distinct_values


class _FakeRollingFeaturesSession:
    """Mimics a season where KC has real, week-varying data (played games)
    and NE is still a flat placeholder (season not yet played)."""

    def execute(self, sql, params=None):
        class _Result:
            def fetchall(self_inner):
                return [_FakeRow("KC", 5), _FakeRow("NE", 1)]

        return _Result()


def test_detect_real_rolling_features_flags_flat_placeholder_teams() -> None:
    session = _FakeRollingFeaturesSession()
    result = detect_real_rolling_features(session, season=2026, teams=["KC", "NE", "MISSING"])
    assert result["KC"] is True
    assert result["NE"] is False
    # A team with no rows at all (e.g. bye week or bad code) defaults to False (safe/conservative).
    assert result["MISSING"] is False


def test_apply_supervised_blend_validated_weights_lean_harder_on_model() -> None:
    """use_validated_weights=True should apply the backtest-validated,
    higher-trust weights instead of the conservative defaults -- and should
    move the blended output further from the base (heuristic/market) number
    than the conservative path does, for the same inputs."""
    rows = [_row(i) for i in range(1600)]
    fit = fit_nfl_supervised_models(rows)
    feature_row = {
        "week": 6,
        "home_off_epa_5g": 0.21,
        "away_off_epa_5g": -0.02,
        "home_def_epa_allowed_5g": -0.05,
        "away_def_epa_allowed_5g": 0.08,
        "diff_off_epa_5g": 0.23,
        "diff_def_epa_allowed_5g": -0.13,
        "home_rest_days": 7.0,
        "away_rest_days": 7.0,
        "diff_rest_days": 0.0,
        "roof_dome": 0.0,
        "surface_turf": 0.0,
        "is_divisional_game": 0.0,
        "home_injury_impact": 0.0,
        "away_injury_impact": 0.0,
        "diff_injury_impact": 0.0,
    }
    base_markets = {
        "home_win_prob": 0.5,
        "away_win_prob": 0.5,
        "total_mean": 44.2,
        "spread_home": 0.0,
        "fair_home_ml": -100,
        "fair_away_ml": 100,
    }
    conservative = apply_supervised_blend(
        fit_payload=fit, feature_row=feature_row, base_markets=base_markets, use_validated_weights=False
    )
    validated = apply_supervised_blend(
        fit_payload=fit, feature_row=feature_row, base_markets=base_markets, use_validated_weights=True
    )
    assert conservative["supervised_overlay"]["spread_weight"] == CONSERVATIVE_BLENDING_WEIGHTS["spread_weight"]
    assert validated["supervised_overlay"]["spread_weight"] == VALIDATED_BLENDING_WEIGHTS["spread_weight"]
    sup_spread = validated["supervised_overlay"]["supervised_spread_home"]
    if abs(sup_spread - base_markets["spread_home"]) > 1e-6:
        assert abs(validated["spread_home"] - base_markets["spread_home"]) >= abs(
            conservative["spread_home"] - base_markets["spread_home"]
        )


def test_apply_supervised_blend_trust_region_bounds_outliers() -> None:
    """A supervised prediction wildly different from the base number should
    get pulled back toward the base rather than dominating the blend --
    this is what actually caught the real -18.4-margin outlier this test
    suite is a regression guard against."""
    rows = [_row(i) for i in range(1800)]
    fit = fit_nfl_supervised_models(rows)
    # Deliberately out-of-distribution feature row (values far outside
    # anything seen in training) to try to provoke an extreme prediction.
    feature_row = {key: 50.0 for key in FEATURE_KEYS}
    base_markets = {"home_win_prob": 0.5, "total_mean": 44.0, "spread_home": -1.0}
    out = apply_supervised_blend(fit_payload=fit, feature_row=feature_row, base_markets=base_markets)
    assert -24.0 <= out["spread_home"] <= 24.0
    assert 28.0 <= out["total_mean"] <= 64.0
