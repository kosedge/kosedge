"""Pure-math tests for CFB totals-guard unused holdout helpers.

No SDV fetch. No pack / KEI writes.
"""

from __future__ import annotations

import pytest

from src.services.cfb_season_engine.totals_guard_holdout import (
    FIT_SEASONS,
    UNUSED_EVAL_SEASONS,
    apply_level_offset,
    apply_matchup_inflation_dampen,
    assert_no_eval_leakage_in_fit,
    filter_eval_rows,
    filter_fit_rows,
    fit_lambda_ols,
    fit_level_offset,
    green_bars_vs_identity,
    margin_after_even_total_shift,
    matchup_inflation_on_sum,
    summarize_kei_vs_close,
    team_points_with_neutral_matchup,
    year_label,
)


def _diag(*, ratio: float, response: float = 1.4, off: float = 1.0, damp: float = 1.0, pace: float = 1.0, hfa_coach: float = 0.0) -> dict:
    league = 25.9
    matchup = ratio**response
    pre = league * matchup * off * damp * pace + hfa_coach
    return {
        "matchup_ratio": ratio,
        "matchup_response": response,
        "offense_boost": off,
        "defense_dampen": damp,
        "pace": pace,
        "pre_clamp": pre,
    }


def test_dampen_preserves_margin_via_even_split() -> None:
    home, away = 31.0, 24.0
    model_total = home + away
    inflation = 6.0
    lam = 0.4
    kei = apply_matchup_inflation_dampen(model_total, inflation, lam)
    delta = kei - model_total
    spread0 = away - home
    spread1 = margin_after_even_total_shift(
        home_exp=home, away_exp=away, delta_total=delta
    )
    assert abs(spread1 - spread0) < 1e-9
    # λ=1 identity; λ=0 full neutralize
    assert apply_matchup_inflation_dampen(model_total, inflation, 1.0) == model_total
    assert abs(
        apply_matchup_inflation_dampen(model_total, inflation, 0.0)
        - (model_total - inflation)
    ) < 1e-9


def test_matchup_inflation_zero_when_ratios_are_one() -> None:
    home_d = _diag(ratio=1.0)
    away_d = _diag(ratio=1.0)
    # model total = clamped neutral sides
    t_n, infl = matchup_inflation_on_sum(
        model_total=25.9 + 25.9,
        home_diag=home_d,
        away_diag=away_d,
        league_ppg=25.9,
        points_clamp=(7.0, 55.0),
        st_nudge=0.0,
    )
    assert abs(infl) < 1e-6
    assert abs(t_n - 51.8) < 1e-6


def test_matchup_inflation_positive_when_favorite_hot() -> None:
    home_d = _diag(ratio=1.3)  # favorite offense vs weak D
    away_d = _diag(ratio=0.85)
    home_pts = team_points_with_neutral_matchup(
        home_d, league_ppg=25.9, points_clamp=(7.0, 55.0)
    )
    # Actual points use real matchup factors
    home_actual = max(7.0, min(55.0, home_d["pre_clamp"]))
    away_actual = max(7.0, min(55.0, away_d["pre_clamp"]))
    model_total = home_actual + away_actual
    t_n, infl = matchup_inflation_on_sum(
        model_total=model_total,
        home_diag=home_d,
        away_diag=away_d,
        league_ppg=25.9,
        points_clamp=(7.0, 55.0),
    )
    assert infl > 0.5
    assert t_n < model_total
    assert abs(home_pts - 25.9) < 1e-6


def test_fit_eval_year_split_no_leakage() -> None:
    rows = [
        {"season": 2023, "week": 1, "model_total": 55.0, "close_total": 52.0, "matchup_inflation": 4.0},
        {"season": 2024, "week": 2, "model_total": 58.0, "close_total": 53.0, "matchup_inflation": 5.0},
        {"season": 2025, "week": 1, "model_total": 60.0, "close_total": 52.0, "matchup_inflation": 7.0},
        {"season": 2024, "week": 5, "model_total": 54.0, "close_total": 53.0, "matchup_inflation": 1.0},
    ]
    fit = filter_fit_rows(rows, week_max=2)
    assert {r["season"] for r in fit} == {2023, 2024}
    assert all(r["week"] <= 2 for r in fit)
    assert_no_eval_leakage_in_fit(fit)

    eval_rows = filter_eval_rows(rows, week_max=2)
    assert {r["season"] for r in eval_rows} == {2025}
    assert UNUSED_EVAL_SEASONS == frozenset({2025})
    assert FIT_SEASONS == frozenset({2023, 2024})
    assert year_label(2025) == "unused"
    assert year_label(2023) == "contaminated"

    with pytest.raises(AssertionError):
        assert_no_eval_leakage_in_fit(rows)  # includes 2025


def test_fit_lambda_and_offset_ignore_eval_year() -> None:
    fit = [
        {"season": 2023, "week": 1, "model_total": 56.0, "close_total": 50.0, "matchup_inflation": 8.0},
        {"season": 2024, "week": 0, "model_total": 54.0, "close_total": 50.0, "matchup_inflation": 6.0},
    ]
    # Ideal λ: T_n + λ*infl = close → λ = (close - T_n)/infl
    # row1: T_n=48, (50-48)/8 = 0.25; row2: T_n=48, (50-48)/6 = 0.333...
    lam = fit_lambda_ols(fit)
    assert 0.0 <= lam <= 1.0
    assert abs(lam - (8 * 2.0 + 6 * 2.0) / (8**2 + 6**2)) < 1e-9

    offset = fit_level_offset(fit)
    # mean(model-close)= (6+4)/2=5 → offset=-5
    assert abs(offset - (-5.0)) < 1e-9
    assert abs(apply_level_offset(56.0, offset) - 51.0) < 1e-9


def test_summarize_and_green_bars() -> None:
    identity_rows = [
        {"kei_total": 58.0, "close_total": 50.0},
        {"kei_total": 56.0, "close_total": 52.0},
    ]
    cand_rows = [
        {"kei_total": 50.5, "close_total": 50.0},
        {"kei_total": 51.5, "close_total": 52.0},
    ]
    ident = summarize_kei_vs_close(identity_rows)
    cand = summarize_kei_vs_close(cand_rows)
    assert ident["mean_kei_minus_close"] == 6.0
    assert ident["clv_plus_rate"] is None
    assert "unavailable" in ident["clv_note"].lower()
    green = green_bars_vs_identity(candidate=cand, identity=ident)
    assert green["all_green"] is True
    assert green["level_ok"] is True
    assert green["stop_do_not_implement_apply_cfb_kei"] is True

    still_hot = summarize_kei_vs_close(
        [{"kei_total": 55.0, "close_total": 50.0}, {"kei_total": 54.0, "close_total": 50.0}]
    )
    red = green_bars_vs_identity(candidate=still_hot, identity=ident)
    assert red["direction_ok"] is False or red["level_ok"] is False
    assert red["all_green"] is False
    assert red["stop_do_not_implement_apply_cfb_kei"] is False


def test_stop_report_if_b_green() -> None:
    from src.services.cfb_season_engine.totals_guard_holdout import stop_report_if_b_green

    stop = stop_report_if_b_green(green_b={"all_green": True}, window="W0-2")
    assert stop["stop"] is True
    assert stop["implement_apply_cfb_kei"] is False
    assert stop["product_flag_on"] is False
    assert stop["play_flip"] is False
    assert "STOP" in stop["message"]

    go = stop_report_if_b_green(green_b={"all_green": False}, window="W0-2")
    assert go["stop"] is False
    assert go["implement_apply_cfb_kei"] is False


def test_mismatch_bucket_and_cupcake_mae_rule() -> None:
    from src.services.cfb_season_engine.totals_guard_holdout import (
        cupcake_mae_rule,
        mismatch_bucket,
        peer_cupcake_mae_split,
    )

    assert mismatch_bucket(5.0) == "peer"
    assert mismatch_bucket(12.0) == "mod"
    assert mismatch_bucket(15.0) == "big"
    assert mismatch_bucket(18.0) == "cupcake"
    assert mismatch_bucket(-22.0) == "cupcake"

    rows = [
        {"model_spread_home": -5.0, "kei_total": 60.0, "close_total": 50.0},  # peer hot
        {"model_spread_home": -6.0, "kei_total": 58.0, "close_total": 52.0},
        {"model_spread_home": -20.0, "kei_total": 70.0, "close_total": 52.0},  # cupcake
        {"model_spread_home": -19.0, "kei_total": 68.0, "close_total": 50.0},
    ]
    cand = [
        {"model_spread_home": -5.0, "kei_total": 51.0, "close_total": 50.0},
        {"model_spread_home": -6.0, "kei_total": 52.0, "close_total": 52.0},
        # cupcake MAE worse: gaps 10 and 12 vs identity 18 and 18 — wait we need MAE worse
        {"model_spread_home": -20.0, "kei_total": 40.0, "close_total": 52.0},  # |gap|=12
        {"model_spread_home": -19.0, "kei_total": 35.0, "close_total": 50.0},  # |gap|=15
    ]
    # identity cupcake MAE = (18+18)/2 = 18; cand = (12+15)/2 = 13.5 — better, not worse
    # Make cand cupcake MAE worse: overshoot under
    cand_worse = [
        {"model_spread_home": -5.0, "kei_total": 50.5, "close_total": 50.0},
        {"model_spread_home": -6.0, "kei_total": 52.0, "close_total": 52.0},
        {"model_spread_home": -20.0, "kei_total": 30.0, "close_total": 52.0},  # 22
        {"model_spread_home": -19.0, "kei_total": 28.0, "close_total": 50.0},  # 22
    ]
    i_split = peer_cupcake_mae_split(rows, kei_key="kei_total")
    c_split = peer_cupcake_mae_split(cand_worse, kei_key="kei_total")
    i_overall = summarize_kei_vs_close(rows)
    c_overall = summarize_kei_vs_close(cand_worse)
    rule = cupcake_mae_rule(
        identity_overall=i_overall,
        candidate_overall=c_overall,
        identity_split=i_split,
        candidate_split=c_split,
    )
    assert rule["bias_killed"] is True
    assert rule["cupcake_mae_worse_than_0_3"] is True
    assert rule["triggered"] is True
    assert "auto-kill" in rule["action"].lower() or "REPORT" in rule["action"]
    # Must not loosen bar / must report split payloads
    assert rule["peer_identity"]["n"] == 2
    assert rule["cupcake_candidate"]["mae"] > rule["cupcake_identity"]["mae"] + 0.3
