"""Supervised NFL outcome model: gradient-boosted trees over a rich weekly
feature set, blended into the simulator's market output.

This replaced a from-scratch, dependency-free logistic/linear regression
(13 features, manual gradient descent) with scikit-learn's
HistGradientBoosting (handles missing values natively, captures non-linear
feature interactions the old linear model couldn't) over ~30 features
including injury severity, rest days, situational flags (dome, turf,
divisional game), and previously-computed-but-unused rolling stats
(success rate, red zone rate, early-down pass rate, raw pressure rates).

Chronological holdout (train on earlier games, test on the most recent
slice) is preserved from the original implementation -- this is the right
call for a time-series problem and avoids leakage.
"""

from __future__ import annotations

import base64
import math
import pickle
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sqlalchemy import text

FEATURE_KEYS: Tuple[str, ...] = (
    "week",
    "home_off_epa_5g",
    "away_off_epa_5g",
    "home_def_epa_allowed_5g",
    "away_def_epa_allowed_5g",
    "home_pressure_allowed_5g",
    "away_pressure_allowed_5g",
    "home_pressure_generated_5g",
    "away_pressure_generated_5g",
    "home_pass_rate_5g",
    "away_pass_rate_5g",
    "home_early_down_pass_rate_5g",
    "away_early_down_pass_rate_5g",
    "home_red_zone_td_rate_5g",
    "away_red_zone_td_rate_5g",
    "home_success_offense_5g",
    "away_success_offense_5g",
    "home_success_defense_allowed_5g",
    "away_success_defense_allowed_5g",
    "diff_off_epa_5g",
    "diff_def_epa_allowed_5g",
    "diff_pressure_generated_5g",
    "diff_pressure_allowed_5g",
    "diff_red_zone_td_rate_5g",
    "diff_success_rate_5g",
    "home_kav_offense_5g",
    "away_kav_offense_5g",
    "home_kav_defense_5g",
    "away_kav_defense_5g",
    "home_kav_net_5g",
    "away_kav_net_5g",
    "diff_kav_net_5g",
    "home_injury_impact",
    "away_injury_impact",
    "diff_injury_impact",
    "home_rest_days",
    "away_rest_days",
    "diff_rest_days",
    "roof_dome",
    "surface_turf",
    "is_divisional_game",
)

MODEL_SCHEMA_VERSION = 3

# Experimental ST-KAV keys (schema v4 candidate). NOT in default FEATURE_KEYS.
# Evaluated 2026-07-28: chronological holdout Brier/margin worsened vs v3 — not promoted.
# Opt-in only via scripts/nfl/retrain_supervised_kav_v4.py (auto-rollback on failure).
# Warehouse: infra/db/042_nfl_st_kav.sql + scripts/nfl/build_st_kav_weekly.py
FEATURE_KEYS_ST_EXPERIMENTAL: Tuple[str, ...] = (
    "home_st_kav_net_5g",
    "away_st_kav_net_5g",
    "diff_st_kav_net_5g",
)


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _build_matrix(rows: Sequence[Dict[str, Any]], feature_keys: Sequence[str]) -> np.ndarray:
    """NaN for missing values -- HistGradientBoosting handles these
    natively (splits treat NaN as its own branch), so early-season rows
    with thin rolling windows don't need manual imputation."""
    matrix = np.full((len(rows), len(feature_keys)), np.nan, dtype=np.float64)
    for i, row in enumerate(rows):
        for j, key in enumerate(feature_keys):
            value = row.get(key)
            if value is not None:
                try:
                    matrix[i, j] = float(value)
                except (TypeError, ValueError):
                    pass
    return matrix


def _moneyline_from_prob(prob: float) -> int:
    p = _clamp(float(prob), 0.001, 0.999)
    if p >= 0.5:
        return int(round(-(100.0 * p) / (1.0 - p)))
    return int(round((100.0 * (1.0 - p)) / p))


def _brier(predictions: Sequence[float], actuals: Sequence[float]) -> Optional[float]:
    if not predictions:
        return None
    return float(np.mean((np.asarray(predictions) - np.asarray(actuals)) ** 2))


def _mae(predictions: Sequence[float], actuals: Sequence[float]) -> Optional[float]:
    if not predictions:
        return None
    return float(np.mean(np.abs(np.asarray(predictions) - np.asarray(actuals))))


def _pickle_b64(obj: Any) -> str:
    return base64.b64encode(pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)).decode("ascii")


def _unpickle_b64(blob: str) -> Any:
    return pickle.loads(base64.b64decode(blob.encode("ascii")))


def fit_nfl_supervised_models(
    rows: Sequence[Dict[str, Any]],
    *,
    feature_keys: Sequence[str] = FEATURE_KEYS,
    holdout_fraction: float = 0.16,
) -> Dict[str, Any]:
    usable = [
        row
        for row in rows
        if row.get("home_team_won") is not None and row.get("final_total_points") is not None
    ]
    usable = sorted(
        usable,
        key=lambda row: (
            _to_float(row.get("season"), 0.0),
            _to_float(row.get("week"), 0.0),
            str(row.get("game_id") or ""),
        ),
    )
    if len(usable) < 300:
        raise ValueError(f"Not enough training rows for supervised retrain: {len(usable)}")

    holdout_size = int(round(len(usable) * _clamp(holdout_fraction, 0.05, 0.4)))
    holdout_size = max(120, holdout_size)
    holdout_size = min(holdout_size, len(usable) - 120)
    train_rows = usable[:-holdout_size]
    test_rows = usable[-holdout_size:]

    x_train = _build_matrix(train_rows, feature_keys)
    x_test = _build_matrix(test_rows, feature_keys)
    y_win_train = np.array([1.0 if bool(row.get("home_team_won")) else 0.0 for row in train_rows])
    y_win_test = np.array([1.0 if bool(row.get("home_team_won")) else 0.0 for row in test_rows])
    y_total_train = np.array([_to_float(row.get("final_total_points")) for row in train_rows])
    y_total_test = np.array([_to_float(row.get("final_total_points")) for row in test_rows])
    y_margin_train = np.array(
        [_to_float(row.get("home_score")) - _to_float(row.get("away_score")) for row in train_rows]
    )
    y_margin_test = np.array(
        [_to_float(row.get("home_score")) - _to_float(row.get("away_score")) for row in test_rows]
    )

    # Conservative depth/leaf settings: ~3-4k training games and 33 features
    # means a deep/high-capacity booster would overfit fast. Shallow trees,
    # a real L2 term, and early stopping on an internal validation slice
    # (scikit-learn does this automatically when validation_fraction is set)
    # keep this generalizing rather than memorizing.
    # Regularized hard: with ~3k training games and 34 features, a
    # confident-looking average-case holdout metric can still hide rare,
    # badly-extrapolated single-game predictions (observed: -18.4 margin for
    # a competitive matchup). Shallower trees, fewer leaves, and a much
    # bigger L2 term trade a little average accuracy for far fewer wild
    # outliers -- non-negotiable for a product where any one absurd number
    # is a visible credibility hit.
    win_model = HistGradientBoostingClassifier(
        max_iter=300,
        learning_rate=0.04,
        max_depth=3,
        max_leaf_nodes=8,
        l2_regularization=1.5,
        early_stopping=True,
        validation_fraction=0.15,
        n_iter_no_change=20,
        random_state=42,
    )
    win_model.fit(x_train, y_win_train)

    total_model = HistGradientBoostingRegressor(
        max_iter=300,
        learning_rate=0.04,
        max_depth=3,
        max_leaf_nodes=8,
        l2_regularization=1.5,
        early_stopping=True,
        validation_fraction=0.15,
        n_iter_no_change=20,
        random_state=42,
    )
    total_model.fit(x_train, y_total_train)

    margin_model = HistGradientBoostingRegressor(
        max_iter=300,
        learning_rate=0.04,
        max_depth=3,
        max_leaf_nodes=8,
        l2_regularization=1.5,
        early_stopping=True,
        validation_fraction=0.15,
        n_iter_no_change=20,
        random_state=42,
    )
    margin_model.fit(x_train, y_margin_train)

    train_prob = np.clip(win_model.predict_proba(x_train)[:, 1], 0.01, 0.99)
    test_prob = np.clip(win_model.predict_proba(x_test)[:, 1], 0.01, 0.99)
    train_total = np.clip(total_model.predict(x_train), 20.0, 70.0)
    test_total = np.clip(total_model.predict(x_test), 20.0, 70.0)
    train_margin = np.clip(margin_model.predict(x_train), -45.0, 45.0)
    test_margin = np.clip(margin_model.predict(x_test), -45.0, 45.0)

    win_importance = permutation_importance(
        win_model, x_test, y_win_test, scoring="neg_brier_score", n_repeats=5, random_state=42, max_samples=min(len(x_test), 800)
    )
    feature_importance = {
        "win": dict(
            sorted(
                {
                    key: round(float(imp), 5)
                    for key, imp in zip(feature_keys, win_importance.importances_mean)
                }.items(),
                key=lambda item: abs(item[1]),
                reverse=True,
            )
        )
    }

    payload = {
        "schema_version": MODEL_SCHEMA_VERSION,
        "feature_keys": list(feature_keys),
        "algorithm": "sklearn.HistGradientBoosting",
        "models_pickle_b64": {
            "win": _pickle_b64(win_model),
            "total": _pickle_b64(total_model),
            "margin": _pickle_b64(margin_model),
        },
        "blending": {
            # Backtest-validated (not guessed): scripts/nfl/validate_supervised_overlay.py
            # swept blend weights on the true chronological holdout (570 games
            # this model never trained on) and found the supervised model
            # dominates the hand-crafted simulator across the whole range --
            # win Brier improves monotonically through weight=1.0, spread/total
            # MAE bottom out around 0.6-0.8. Picked slightly inside those optima
            # (not the exact argmin) to avoid overfitting to this one holdout's
            # noise. Re-run that script after each retrain to re-check these.
            # NOTE: the historical holdout (real games, real week-to-week
            # variance in rolling features) supports weights as high as
            # 0.6-0.9 -- see scripts/nfl/validate_supervised_overlay.py. But
            # as of this training run, 2026's nfl_dp_team_rolling_features_weekly
            # is a *flat placeholder* (one identical value repeated across
            # all 18 weeks per team, since no 2026 games have been played
            # yet) -- verified via `SELECT COUNT(DISTINCT off_epa_per_play_5g)
            # ... GROUP BY team` = 1 for every team. Most of the supervised
            # model's diff_*_5g inputs are therefore near-constant for 2026,
            # an out-of-distribution regime relative to training (which was
            # all real, week-varying historical data) -- applying it at full
            # trained strength produced individually-absurd 2026 spreads
            # despite great average holdout metrics. Kept deliberately
            # conservative until real 2026 weekly features start flowing (at
            # which point re-run the honest holdout backtest and raise these).
            "home_win_weight": 0.40,
            "total_weight": 0.30,
            "spread_weight": 0.30,
        },
        "feature_importance": feature_importance,
        "metrics": {
            "train_rows": len(train_rows),
            "test_rows": len(test_rows),
            "train_brier": _brier(list(train_prob), list(y_win_train)),
            "test_brier": _brier(list(test_prob), list(y_win_test)),
            "train_total_mae": _mae(list(train_total), list(y_total_train)),
            "test_total_mae": _mae(list(test_total), list(y_total_test)),
            "train_margin_mae": _mae(list(train_margin), list(y_margin_train)),
            "test_margin_mae": _mae(list(test_margin), list(y_margin_test)),
            "test_avg_home_prob": float(np.mean(test_prob)) if len(test_prob) else None,
            "test_avg_total_pred": float(np.mean(test_total)) if len(test_total) else None,
        },
    }
    return payload


# Backtest-validated on the true chronological holdout (2013-2023 train,
# 2024 tune, 2025 held out and touched exactly once) via
# scripts/nfl/tune_blend_weights.py: on real, week-varying rolling features,
# these weights beat the previous conservative defaults with statistical
# significance (spread MAE 8.35 vs 9.51 old-config vs 9.67 Vegas on the
# untouched 2025 season; 95% CI on the vs-Vegas gap excluded zero). Kept
# slightly short of the raw grid-search optimum (which had no trust-region
# clamp at all) because outlier tail risk (P99/max error) was no better
# unclamped -- a modest clamp costs ~0 average accuracy while keeping a
# guardrail against a single wild single-game prediction.
VALIDATED_BLENDING_WEIGHTS: Dict[str, float] = {
    "home_win_weight": 0.75,
    "total_weight": 0.60,
    "spread_weight": 0.85,
}
VALIDATED_MAX_MARGIN_DEVIATION = 14.0
VALIDATED_MAX_TOTAL_DEVIATION = 14.0

# The weights above are only valid when the underlying rolling features are
# real, week-varying data. Before a season's games are actually played,
# nfl_dp_team_rolling_features_weekly is hydrated with a *flat placeholder*
# (identical value repeated across all 18 weeks) -- out-of-distribution
# relative to training, where full trust in the supervised model produced
# individually-absurd predictions despite great average holdout metrics.
# use_validated_weights=False (the safe default) keeps the original
# conservative weights for exactly that case.
CONSERVATIVE_BLENDING_WEIGHTS: Dict[str, float] = {
    "home_win_weight": 0.40,
    "total_weight": 0.30,
    "spread_weight": 0.30,
}
CONSERVATIVE_MAX_MARGIN_DEVIATION = 7.0
CONSERVATIVE_MAX_TOTAL_DEVIATION = 6.0


def detect_real_rolling_features(
    session: Any,
    *,
    season: int,
    teams: Sequence[str],
) -> Dict[str, bool]:
    """True per team if that team's nfl_dp_team_rolling_features_weekly rows
    for this season show real week-to-week variation (a season that has
    actually been played, at least partially). False if every week has an
    identical value -- the signature of a not-yet-played season hydrated
    with a flat placeholder prior (see VALIDATED_BLENDING_WEIGHTS docstring).
    `games_in_window_5` is NOT a reliable signal for this -- it's populated
    with a plausible-looking ramp (1,2,3,4,5,5,5...) even for placeholder
    seasons, so this checks actual EPA variance instead."""
    if not teams:
        return {}
    rows = session.execute(
        text(
            """
            SELECT team, COUNT(DISTINCT off_epa_per_play_5g) AS distinct_values
            FROM nfl_dp_team_rolling_features_weekly
            WHERE season = :season AND team = ANY(:teams) AND off_epa_per_play_5g IS NOT NULL
            GROUP BY team
            """
        ),
        {"season": int(season), "teams": list(teams)},
    ).fetchall()
    result = {team: False for team in teams}
    for row in rows:
        result[str(row.team)] = int(row.distinct_values) > 1
    return result


def apply_supervised_blend(
    *,
    fit_payload: Optional[Dict[str, Any]],
    feature_row: Dict[str, Any],
    base_markets: Dict[str, Any],
    use_validated_weights: bool = False,
) -> Dict[str, Any]:
    if not isinstance(fit_payload, dict):
        return dict(base_markets)

    schema_version = fit_payload.get("schema_version")
    feature_keys = fit_payload.get("feature_keys")
    if use_validated_weights:
        blending = {**VALIDATED_BLENDING_WEIGHTS}
        max_margin_deviation = VALIDATED_MAX_MARGIN_DEVIATION
        max_total_deviation = VALIDATED_MAX_TOTAL_DEVIATION
    else:
        blending = fit_payload.get("blending") or CONSERVATIVE_BLENDING_WEIGHTS
        max_margin_deviation = CONSERVATIVE_MAX_MARGIN_DEVIATION
        max_total_deviation = CONSERVATIVE_MAX_TOTAL_DEVIATION
    if not isinstance(feature_keys, list):
        return dict(base_markets)

    base_home_prob = _to_float(base_markets.get("home_win_prob"), 0.5)
    base_total = _to_float(base_markets.get("total_mean"), 44.0)
    base_spread_home = _to_float(base_markets.get("spread_home"), 0.0)

    if schema_version == MODEL_SCHEMA_VERSION:
        models_b64 = fit_payload.get("models_pickle_b64")
        if not isinstance(models_b64, dict):
            return dict(base_markets)
        try:
            win_model = _unpickle_b64(models_b64["win"])
            total_model = _unpickle_b64(models_b64["total"])
            margin_model = _unpickle_b64(models_b64["margin"])
        except Exception:
            return dict(base_markets)

        x_vec = _build_matrix([feature_row], feature_keys)
        sup_home_prob = _clamp(float(win_model.predict_proba(x_vec)[:, 1][0]), 0.01, 0.99)
        sup_total_raw = _clamp(float(total_model.predict(x_vec)[0]), 30.0, 66.0)
        sup_margin_raw = _clamp(float(margin_model.predict(x_vec)[0]), -45.0, 45.0)

        # Trust-region guardrail: a gradient-boosted model can still
        # occasionally extrapolate to an absurd single-game prediction (see
        # nfl_supervised_retrain module docstring / the -18.4 margin case
        # that motivated this). Rather than trust it unconditionally, cap
        # how far the supervised prediction may pull the *pre-supervised*
        # base number, so an outlier attenuates itself instead of dominating
        # the blend. Genuine signal well inside this radius still comes
        # through at full strength.
        base_margin = -base_spread_home
        sup_margin = _clamp(sup_margin_raw, base_margin - max_margin_deviation, base_margin + max_margin_deviation)
        sup_total = _clamp(sup_total_raw, base_total - max_total_deviation, base_total + max_total_deviation)
        sup_spread_home = -sup_margin  # margin: positive = home favored; spread_home: negative = home favored
    else:
        # Legacy schema (hand-rolled logistic/linear) support, in case an
        # older payload is still active when this deploys.
        standardization = fit_payload.get("standardization")
        home_win_model = fit_payload.get("home_win_model")
        total_model_legacy = fit_payload.get("total_model")
        if not (isinstance(standardization, dict) and isinstance(home_win_model, dict) and isinstance(total_model_legacy, dict)):
            return dict(base_markets)
        means = standardization.get("mean")
        stds = standardization.get("std")
        logistic_w = home_win_model.get("weights")
        logistic_b = _to_float(home_win_model.get("bias"))
        linear_w = total_model_legacy.get("weights")
        linear_b = _to_float(total_model_legacy.get("bias"))
        if not (isinstance(means, list) and isinstance(stds, list) and isinstance(logistic_w, list) and isinstance(linear_w, list)):
            return dict(base_markets)
        x_raw = [_to_float(feature_row.get(key)) for key in feature_keys]
        x = [(x_raw[i] - means[i]) / (stds[i] if abs(stds[i]) > 1e-9 else 1.0) for i in range(len(feature_keys))]

        def _sigmoid(v: float) -> float:
            return 1.0 / (1.0 + math.exp(-v)) if v >= 0 else math.exp(v) / (1.0 + math.exp(v))

        sup_home_prob = _clamp(_sigmoid(logistic_b + sum(logistic_w[i] * x[i] for i in range(len(x)))), 0.01, 0.99)
        sup_total = _clamp(linear_b + sum(linear_w[i] * x[i] for i in range(len(x))), 30.0, 58.0)
        sup_spread_home = base_spread_home  # legacy schema never modeled margin directly

    home_weight = _clamp(_to_float(blending.get("home_win_weight"), 0.40), 0.0, 1.0)
    total_weight = _clamp(_to_float(blending.get("total_weight"), 0.30), 0.0, 1.0)
    spread_weight = _clamp(_to_float(blending.get("spread_weight"), 0.30), 0.0, 1.0)

    blended_home_prob = _clamp(((1.0 - home_weight) * base_home_prob) + (home_weight * sup_home_prob), 0.01, 0.99)
    blended_total = _clamp(((1.0 - total_weight) * base_total) + (total_weight * sup_total), 28.0, 64.0)
    # Absolute final guardrail regardless of weights/model behavior --
    # nflverse's 2013-2025 closing lines (the real market, see
    # scripts/nfl/historical_market_backtest.py) never exceed roughly +/-24.
    blended_spread_home = _clamp(
        ((1.0 - spread_weight) * base_spread_home) + (spread_weight * sup_spread_home), -24.0, 24.0
    )

    out = dict(base_markets)
    out["home_win_prob"] = round(blended_home_prob, 4)
    out["away_win_prob"] = round(1.0 - blended_home_prob, 4)
    out["fair_home_ml"] = _moneyline_from_prob(blended_home_prob)
    out["fair_away_ml"] = _moneyline_from_prob(1.0 - blended_home_prob)
    out["total_mean"] = round(float(blended_total), 2)
    out["spread_home"] = round(float(blended_spread_home), 2)
    out["supervised_overlay"] = {
        "applied": True,
        "schema_version": schema_version,
        "home_win_weight": home_weight,
        "total_weight": total_weight,
        "spread_weight": spread_weight,
        "supervised_home_prob": round(sup_home_prob, 4),
        "supervised_total_mean": round(sup_total, 3),
        "supervised_spread_home": round(sup_spread_home, 3),
        "base_home_prob": round(base_home_prob, 4),
        "base_total_mean": round(base_total, 3),
        "base_spread_home": round(base_spread_home, 3),
    }
    return out
