"""Pure helpers for CFB totals-guard unused holdout (research harness only).

Design SoT: docs/CFB_KEI_CALIBRATOR_DESIGN.md (Task 5).
Does NOT write pack / KEI / enable kei_total divergence / unsat PLAY.

Candidates:
  (b) primary — totals-only matchup-inflation dampen λ on the sum
  (a) fallback — additive level offset on model_total

Fit years: 2023–2024. Eval unused: 2025. Do not retune from 2025.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

# Hist-cal 2026-08-05 primary decision years (same spine as spread Tag holdout).
FIT_SEASONS = frozenset({2023, 2024})
UNUSED_EVAL_SEASONS = frozenset({2025})

# Design §4 GREEN — enable kei_total divergence (W0–2 only). Research bars only.
GREEN_ABS_MEAN_GAP = 1.0
GREEN_MAE_WORSE_THAN_IDENTITY = 0.3
GREEN_OVER_DRUNK_MEAN = 2.0  # mean gap must not stay > +2

# Primary eval window mirrors spread bias-guard early weeks.
PRIMARY_WEEK_MAX = 2  # W0–2 inclusive — FIRST enable window only
OPTIONAL_WEEK_MAX = 4  # W0–4 confirmatory table

# Mismatch buckets (audit CFB_TOTALS_HOT_AUDIT.md): peer vs cupcake MAE split.
PEER_ABS_SPREAD_LT = 10.0
CUPCAKE_ABS_SPREAD_GE = 17.0  # loud cupcake band (|s|≥17); ≥21 also reported

# CoS locks (harness honesty — not product flips).
COS_LOCKS = {
    "no_play_unsat_on_ats_alone": (
        "Do not unsat totals PLAY on ATS-vs-close alone. NFL totals hit ~61% ATS "
        "with ~35% CLV — CFB PLAY stays sat until movement-CLV or a second unused "
        "year. CFB_TOTALS_PLAY_ELIGIBLE stays false even if unused ATS clears 52.4%."
    ),
    "w0_2_first_window_no_w1_retune": (
        "W0–2 is the first enable window only. Proxy λ under-corrects live 2026 "
        "roster ratios — do not retune λ on W1 street."
    ),
    "candidate_order_no_global_response_cut": (
        "(b) primary matchup-inflation dampen on the sum; (a) level offset fallback; "
        "(c) mismatch-bucket offsets exploratory only. No global MATCHUP_RESPONSE cut."
    ),
}


def year_label(season: int) -> str:
    if season in UNUSED_EVAL_SEASONS:
        return "unused"
    if season in FIT_SEASONS:
        return "contaminated"
    return "confirmatory"


def clamp_lambda(lam: float) -> float:
    if not math.isfinite(lam):
        return 1.0
    return max(0.0, min(1.0, float(lam)))


def team_points_with_neutral_matchup(
    diag: Mapping[str, Any],
    *,
    league_ppg: float,
    points_clamp: Tuple[float, float],
) -> float:
    """Rebuild one side's expected points with matchup ratio → 1 (factor = 1).

    Uses stored expected_team_points diagnostics:
      pre_clamp = league_ppg * (ratio**response) * off * def * pace + hfa + coach
    Neutral matchup replaces (ratio**response) with 1.0, then re-clamps.
    """
    ratio = float(diag["matchup_ratio"])
    response = float(diag["matchup_response"])
    matchup = ratio**response
    off = float(diag["offense_boost"])
    damp = float(diag["defense_dampen"])
    pace = float(diag["pace"])
    pre = float(diag["pre_clamp"])
    mult = float(league_ppg) * matchup * off * damp * pace
    additive = pre - mult
    pre_neutral = float(league_ppg) * 1.0 * off * damp * pace + additive
    lo, hi = points_clamp
    return max(float(lo), min(float(hi), pre_neutral))


def matchup_inflation_on_sum(
    *,
    model_total: float,
    home_diag: Mapping[str, Any],
    away_diag: Mapping[str, Any],
    league_ppg: float,
    points_clamp: Tuple[float, float],
    st_nudge: float = 0.0,
) -> Tuple[float, float]:
    """Return (total_neutral, matchup_inflation) where inflation = T0 − T_neutral.

    ST nudge is matchup-independent and applied the same on both paths so it
    cancels in inflation; included on T_neutral for absolute level honesty.
    """
    home_n = team_points_with_neutral_matchup(
        home_diag, league_ppg=league_ppg, points_clamp=points_clamp
    )
    away_n = team_points_with_neutral_matchup(
        away_diag, league_ppg=league_ppg, points_clamp=points_clamp
    )
    total_neutral = home_n + away_n + float(st_nudge)
    inflation = float(model_total) - total_neutral
    return total_neutral, inflation


def apply_matchup_inflation_dampen(
    model_total: float,
    matchup_inflation: float,
    lam: float,
) -> float:
    """Candidate (b): kei_total = T0 − (1−λ)·inflation = T_neutral + λ·inflation.

    Sum-only. Does not rewrite team scores or spread = away − home.
    λ=1 → identity; λ=0 → fully neutralize matchup inflation on the sum.
    """
    lam_c = clamp_lambda(lam)
    return float(model_total) - (1.0 - lam_c) * float(matchup_inflation)


def apply_level_offset(model_total: float, offset: float) -> float:
    """Candidate (a): kei_total = model_total + offset."""
    return float(model_total) + float(offset)


def margin_after_even_total_shift(
    *,
    home_exp: float,
    away_exp: float,
    delta_total: float,
) -> float:
    """Even split of a totals-only ΔT preserves spread/margin identity."""
    home2 = float(home_exp) + 0.5 * float(delta_total)
    away2 = float(away_exp) + 0.5 * float(delta_total)
    return away2 - home2


def fit_lambda_ols(
    rows: Sequence[Mapping[str, Any]],
    *,
    model_key: str = "model_total",
    close_key: str = "close_total",
    inflation_key: str = "matchup_inflation",
    min_abs_inflation: float = 1e-6,
) -> float:
    """OLS λ on fit rows: T_neutral + λ·infl ≈ close → λ = Σ infl·(close−T_n)/Σ infl²."""
    num = 0.0
    den = 0.0
    for r in rows:
        infl = float(r[inflation_key])
        if abs(infl) < min_abs_inflation:
            continue
        t0 = float(r[model_key])
        close = float(r[close_key])
        t_neutral = t0 - infl
        num += infl * (close - t_neutral)
        den += infl * infl
    if den <= 0.0:
        return 1.0
    return clamp_lambda(num / den)


def fit_level_offset(
    rows: Sequence[Mapping[str, Any]],
    *,
    model_key: str = "model_total",
    close_key: str = "close_total",
) -> float:
    """Offset so mean(model + offset − close) = 0 on the fit set."""
    if not rows:
        return 0.0
    gaps = [float(r[model_key]) - float(r[close_key]) for r in rows]
    return -sum(gaps) / len(gaps)


def filter_fit_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    week_max: int = PRIMARY_WEEK_MAX,
) -> List[Mapping[str, Any]]:
    """Contaminated fit seasons only; never include unused eval years."""
    out: List[Mapping[str, Any]] = []
    for r in rows:
        season = int(r["season"])
        week = int(r["week"])
        if season not in FIT_SEASONS:
            continue
        if week < 0 or week > week_max:
            continue
        out.append(r)
    return out


def filter_eval_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    week_max: int = PRIMARY_WEEK_MAX,
    seasons: Optional[Iterable[int]] = None,
) -> List[Mapping[str, Any]]:
    """Unused eval seasons (default 2025) for GREEN/RED; no fit leakage."""
    allowed = frozenset(seasons) if seasons is not None else UNUSED_EVAL_SEASONS
    out: List[Mapping[str, Any]] = []
    for r in rows:
        season = int(r["season"])
        week = int(r["week"])
        if season not in allowed:
            continue
        if week < 0 or week > week_max:
            continue
        out.append(r)
    return out


def assert_no_eval_leakage_in_fit(
    fit_rows: Sequence[Mapping[str, Any]],
    *,
    forbidden: Iterable[int] = UNUSED_EVAL_SEASONS,
) -> None:
    bad = {int(r["season"]) for r in fit_rows} & frozenset(forbidden)
    if bad:
        raise AssertionError(f"fit rows leaked unused eval seasons: {sorted(bad)}")


def summarize_kei_vs_close(
    rows: Sequence[Mapping[str, Any]],
    *,
    kei_key: str = "kei_total",
    close_key: str = "close_total",
) -> Dict[str, Any]:
    """n, mean(KEI−close), MAE, Over-sign bias. CLV labeled unavailable."""
    n = len(rows)
    if n == 0:
        return {
            "n": 0,
            "mean_kei_minus_close": None,
            "mae": None,
            "over_sign_bias": None,
            "over_n": 0,
            "under_n": 0,
            "push_n": 0,
            "clv_plus_rate": None,
            "clv_note": "CLV unavailable — SDV betting has close only (no owned open≠close)",
        }
    gaps = [float(r[kei_key]) - float(r[close_key]) for r in rows]
    over_n = sum(1 for g in gaps if g > 1e-9)
    under_n = sum(1 for g in gaps if g < -1e-9)
    push_n = n - over_n - under_n
    # Over-sign bias ∈ [-1, 1]: (+1 Over, −1 Under, 0 push) mean.
    signed = [(1.0 if g > 1e-9 else (-1.0 if g < -1e-9 else 0.0)) for g in gaps]
    mean_gap = sum(gaps) / n
    mae = sum(abs(g) for g in gaps) / n
    return {
        "n": n,
        "mean_kei_minus_close": round(mean_gap, 4),
        "mae": round(mae, 4),
        "over_sign_bias": round(sum(signed) / n, 4),
        "over_n": over_n,
        "under_n": under_n,
        "push_n": push_n,
        "clv_plus_rate": None,
        "clv_note": "CLV unavailable — SDV betting has close only (no owned open≠close)",
    }


def mismatch_bucket(abs_model_spread: float) -> str:
    """Peer / mod / big / cupcake from |model_spread| (audit buckets)."""
    a = abs(float(abs_model_spread))
    if a < PEER_ABS_SPREAD_LT:
        return "peer"
    if a < 14.0:
        return "mod"
    if a < CUPCAKE_ABS_SPREAD_GE:
        return "big"
    return "cupcake"


def peer_cupcake_mae_split(
    rows: Sequence[Mapping[str, Any]],
    *,
    kei_key: str,
    close_key: str = "close_total",
    spread_key: str = "model_spread_home",
) -> Dict[str, Any]:
    """MAE / mean-gap split: peer (|s|<10) vs cupcake (|s|≥17)."""
    peer = [
        r
        for r in rows
        if abs(float(r[spread_key])) < PEER_ABS_SPREAD_LT
    ]
    cupcake = [
        r
        for r in rows
        if abs(float(r[spread_key])) >= CUPCAKE_ABS_SPREAD_GE
    ]
    cupcake_21 = [
        r
        for r in rows
        if abs(float(r[spread_key])) >= 21.0
    ]
    return {
        "peer_lt_10": summarize_kei_vs_close(peer, kei_key=kei_key, close_key=close_key),
        "cupcake_ge_17": summarize_kei_vs_close(
            cupcake, kei_key=kei_key, close_key=close_key
        ),
        "cupcake_ge_21": summarize_kei_vs_close(
            cupcake_21, kei_key=kei_key, close_key=close_key
        ),
        "bucket_defs": {
            "peer": f"|model_spread| < {PEER_ABS_SPREAD_LT}",
            "cupcake_primary": f"|model_spread| >= {CUPCAKE_ABS_SPREAD_GE}",
            "cupcake_alt": "|model_spread| >= 21",
        },
    }


def cupcake_mae_rule(
    *,
    identity_overall: Mapping[str, Any],
    candidate_overall: Mapping[str, Any],
    identity_split: Mapping[str, Any],
    candidate_split: Mapping[str, Any],
) -> Dict[str, Any]:
    """If (b) kills Over bias but cupcake MAE worsens >0.3: report split; do not auto-kill.

    Does not loosen the overall MAE GREEN bar. Does not reject (b) solely on cupcakes.
    """
    i_mean = identity_overall.get("mean_kei_minus_close")
    c_mean = candidate_overall.get("mean_kei_minus_close")
    i_cup = (identity_split.get("cupcake_ge_17") or {}).get("mae")
    c_cup = (candidate_split.get("cupcake_ge_17") or {}).get("mae")
    bias_killed = False
    if i_mean is not None and c_mean is not None:
        # "Kills the +8-ish bias": candidate mean gap much closer to 0 / not Over-drunk.
        bias_killed = (
            float(i_mean) > GREEN_OVER_DRUNK_MEAN
            and float(c_mean) <= GREEN_OVER_DRUNK_MEAN
        ) or (
            float(i_mean) > GREEN_ABS_MEAN_GAP
            and abs(float(c_mean)) <= GREEN_ABS_MEAN_GAP
        ) or (
            float(i_mean) - float(c_mean) >= 4.0  # large Over haircut vs identity
            and float(c_mean) <= GREEN_OVER_DRUNK_MEAN
        )
    cupcake_mae_worse = None
    cupcake_mae_delta = None
    if i_cup is not None and c_cup is not None:
        cupcake_mae_delta = float(c_cup) - float(i_cup)
        cupcake_mae_worse = cupcake_mae_delta > GREEN_MAE_WORSE_THAN_IDENTITY
    triggered = bool(bias_killed and cupcake_mae_worse)
    return {
        "triggered": triggered,
        "bias_killed": bias_killed,
        "cupcake_mae_worse_than_0_3": cupcake_mae_worse,
        "cupcake_mae_delta": round(cupcake_mae_delta, 4)
        if cupcake_mae_delta is not None
        else None,
        "action": (
            "REPORT peer vs cupcake MAE split — do not auto-kill (b); "
            "do not silently loosen overall MAE bar"
            if triggered
            else "no cupcake-MAE exception triggered"
        ),
        "peer_identity": identity_split.get("peer_lt_10"),
        "peer_candidate": candidate_split.get("peer_lt_10"),
        "cupcake_identity": identity_split.get("cupcake_ge_17"),
        "cupcake_candidate": candidate_split.get("cupcake_ge_17"),
    }


def green_bars_vs_identity(
    *,
    candidate: Mapping[str, Any],
    identity: Mapping[str, Any],
) -> Dict[str, Any]:
    """Design §4 GREEN for enabling kei_total divergence (not PLAY unsat)."""
    c_mean = candidate.get("mean_kei_minus_close")
    c_mae = candidate.get("mae")
    i_mae = identity.get("mae")
    if c_mean is None or c_mae is None or i_mae is None:
        return {
            "level_ok": False,
            "mae_ok": False,
            "direction_ok": False,
            "all_green": False,
            "bars": {
                "abs_mean_gap_le": GREEN_ABS_MEAN_GAP,
                "mae_not_worse_by": GREEN_MAE_WORSE_THAN_IDENTITY,
                "mean_gap_not_gt": GREEN_OVER_DRUNK_MEAN,
            },
            "note": "insufficient n / null metrics",
            "stop_do_not_implement_apply_cfb_kei": False,
        }
    level_ok = abs(float(c_mean)) <= GREEN_ABS_MEAN_GAP
    mae_ok = float(c_mae) <= float(i_mae) + GREEN_MAE_WORSE_THAN_IDENTITY
    direction_ok = float(c_mean) <= GREEN_OVER_DRUNK_MEAN
    all_green = bool(level_ok and mae_ok and direction_ok)
    return {
        "level_ok": level_ok,
        "mae_ok": mae_ok,
        "direction_ok": direction_ok,
        "all_green": all_green,
        "bars": {
            "abs_mean_gap_le": GREEN_ABS_MEAN_GAP,
            "mae_not_worse_by": GREEN_MAE_WORSE_THAN_IDENTITY,
            "mean_gap_not_gt": GREEN_OVER_DRUNK_MEAN,
        },
        # CoS: if (b) GREEN on divergence bars → STOP and report; do not edit apply_cfb_kei.
        "stop_do_not_implement_apply_cfb_kei": all_green,
        "note": (
            "GREEN = divergence research gate only. STOP and report — do NOT implement "
            "into apply_cfb_kei from this harness. Does NOT unsat totals PLAY: "
            "CFB_TOTALS_PLAY_ELIGIBLE stays false even if unused ATS clears 52.4% "
            "(need movement-CLV or a second unused year; NFL ~61% ATS / ~35% CLV)."
        ),
    }


def stop_report_if_b_green(
    *,
    green_b: Mapping[str, Any],
    window: str = "W0-2",
) -> Dict[str, Any]:
    """Explicit CoS stop gate when (b) clears §4 divergence bars."""
    all_green = bool(green_b.get("all_green"))
    return {
        "window": window,
        "b_all_green": all_green,
        "stop": all_green,
        "implement_apply_cfb_kei": False,  # never from this harness
        "product_flag_on": False,
        "pack_recut": False,
        "play_flip": False,
        "message": (
            f"STOP: (b) GREEN on {window} divergence bars — report only; "
            "do NOT implement into apply_cfb_kei; flag OFF; no pack recut; no PLAY flip."
            if all_green
            else (
                f"(b) not all-GREEN on {window} — continue research; still no "
                "apply_cfb_kei edit, flag OFF, no pack recut, no PLAY flip."
            )
        ),
    }
