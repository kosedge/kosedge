"""Holdout scale + HFA for CFB program-prior → spread (no EPA, no KEI).

Fit on train seasons only. Evaluate on holdout. Adopt only if holdout MAE
improves by a clear margin. Sign convention matches the lake:

    fair_spread_home = -HFA - scale * (prior_home - prior_away)

Negative = home favored. ``HFA`` is home-field *points* in [0, 4]
(equivalent to a negative spread intercept). Neutral sites use HFA = 0.

The brief's ``HFA - scale * diff`` form is the same if that HFA is stored
as a signed spread intercept (home-favored negative). We store points > 0.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from src.services.cfb_warehouse.identity import known_engine_codes
from src.services.cfb_warehouse.paths import REPO_ROOT
from src.services.cfb_warehouse.walkforward import (
    HFA_FLAT,
    _finite,
    _f,
    _slice_metrics,
    example_row,
    grade_walkforward_row,
    week_band,
)

TRAIN_YEARS = (2020, 2021, 2022, 2023)
HOLDOUT_YEARS = (2024, 2025)
FIT_MAX_WEEK = 4
SCALE_MIN = 0.25
SCALE_MAX = 5.0
HFA_MIN = 0.0
HFA_MAX = 4.0
# Holdout Week 0–4 MAE must beat baseline by at least this many points.
ADOPT_MAE_MARGIN = 0.50
BASELINE_SCALE = 1.0
BASELINE_HFA = float(HFA_FLAT)

PACKAGED_PATH = (
    REPO_ROOT
    / "services"
    / "model-service"
    / "src"
    / "services"
    / "cfb_season_engine"
    / "data"
    / "cfb_prior_scale_hfa.json"
)


def scaled_spread(
    prior_diff: float,
    *,
    scale: float,
    hfa: float,
    neutral: bool,
) -> float:
    """Home spread. Negative = home favored."""
    hfa_pts = 0.0 if neutral else float(hfa)
    return round(-hfa_pts - float(scale) * float(prior_diff), 3)


def collect_eligible(
    games: Sequence[Mapping[str, Any]],
    priors: Mapping[Tuple[int, str], Mapping[str, Any]],
    *,
    years: Sequence[int],
    max_week: Optional[int] = None,
    known: Optional[Mapping[str, Any]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Rows with prior + close. Missing either → excluded (counts reported)."""
    known = known if known is not None else known_engine_codes()
    year_set = {int(y) for y in years}
    counts = {
        "n_games": 0,
        "excluded_year": 0,
        "excluded_week": 0,
        "excluded_identity": 0,
        "excluded_no_prior": 0,
        "excluded_no_close": 0,
        "eligible": 0,
    }
    out: List[Dict[str, Any]] = []
    for game in games:
        counts["n_games"] += 1
        season = int(_finite(game.get("season")))
        if season not in year_set:
            counts["excluded_year"] += 1
            continue
        week = int(_finite(game.get("week")))
        if max_week is not None and week > int(max_week):
            counts["excluded_week"] += 1
            continue
        home = str(game.get("home_team_id") or "")
        away = str(game.get("away_team_id") or "")
        fcs = bool(game.get("fcs_home") or game.get("fcs_away") or game.get("fcs_opponent"))
        if home not in known or away not in known or fcs:
            counts["excluded_identity"] += 1
            continue
        close = _f(game.get("close_spread_home"))
        if close is None:
            counts["excluded_no_close"] += 1
            continue
        home_p = priors.get((season, home))
        away_p = priors.get((season, away))
        if not home_p or not away_p:
            counts["excluded_no_prior"] += 1
            continue
        home_pts = _f(home_p.get("points"))
        away_pts = _f(away_p.get("points"))
        if home_pts is None or away_pts is None:
            counts["excluded_no_prior"] += 1
            continue
        diff = home_pts - away_pts
        row = dict(game)
        row["prior_diff"] = diff
        row["prior_home"] = home_p.get("points")
        row["prior_away"] = away_p.get("points")
        out.append(row)
        counts["eligible"] += 1
    return out, counts


def mae_for(rows: Sequence[Mapping[str, Any]], *, scale: float, hfa: float) -> Optional[float]:
    if not rows:
        return None
    total = 0.0
    n = 0
    for row in rows:
        close = _f(row.get("close_spread_home"))
        if close is None:
            continue
        fair = scaled_spread(
            float(row["prior_diff"]),
            scale=scale,
            hfa=hfa,
            neutral=bool(row.get("neutral")),
        )
        total += abs(fair - close)
        n += 1
    return total / n if n else None


def fit_scale_hfa(
    train_rows: Sequence[Mapping[str, Any]],
    *,
    scale_step: float = 0.05,
    hfa_step: float = 0.10,
) -> Dict[str, Any]:
    """Grid-search train MAE. scale > 0; HFA in [0, 4]. Does not look at holdout."""
    if not train_rows:
        raise ValueError("No train rows with prior + close")
    best: Optional[Dict[str, Any]] = None
    scale = SCALE_MIN
    while scale <= SCALE_MAX + 1e-9:
        hfa = HFA_MIN
        while hfa <= HFA_MAX + 1e-9:
            mae = mae_for(train_rows, scale=scale, hfa=hfa)
            if mae is not None and (best is None or mae < best["train_mae"]):
                best = {
                    "scale": round(scale, 4),
                    "hfa": round(hfa, 4),
                    "train_mae": round(mae, 4),
                    "method": "grid_mae",
                }
            hfa += hfa_step
        scale += scale_step
    if not best or best["scale"] <= 0:
        raise ValueError("Fit failed to produce scale > 0")
    best["n_train"] = len(train_rows)
    best["baseline_train_mae"] = round(
        mae_for(train_rows, scale=BASELINE_SCALE, hfa=BASELINE_HFA) or 0.0, 4
    )
    return best


def grade_scaled(
    rows: Sequence[Mapping[str, Any]],
    *,
    scale: float,
    hfa: float,
    label: str,
) -> List[Dict[str, Any]]:
    graded: List[Dict[str, Any]] = []
    for row in rows:
        fair = scaled_spread(
            float(row["prior_diff"]),
            scale=scale,
            hfa=hfa,
            neutral=bool(row.get("neutral")),
        )
        graded.append(
            grade_walkforward_row(
                row,
                model_spread_home=fair,
                fair_status="ok",
                drivers={
                    "band": week_band(row.get("week")),
                    "blend": "prior_only_scaled",
                    "scale": scale,
                    "hfa": 0.0 if row.get("neutral") else hfa,
                    "prior_diff": round(float(row["prior_diff"]), 3),
                    "label": label,
                },
            )
        )
    return graded


def band_metrics(graded: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    w01 = [r for r in graded if r.get("week_band") == "w0_1"]
    w04 = [r for r in graded if int(r.get("week") or 0) <= FIT_MAX_WEEK]
    return {
        "w0_1": _slice_metrics(w01),
        "w0_4": _slice_metrics(w04),
        "all_eligible": _slice_metrics(list(graded)),
    }


def decide_adopt(
    *,
    baseline_holdout_mae: Optional[float],
    calibrated_holdout_mae: Optional[float],
    holdout_n: int,
    scale: float,
) -> Tuple[bool, str]:
    if scale <= 0:
        return False, "scale_not_positive"
    if holdout_n < 50:
        return False, "holdout_thin"
    if baseline_holdout_mae is None or calibrated_holdout_mae is None:
        return False, "missing_mae"
    delta = baseline_holdout_mae - calibrated_holdout_mae
    if delta >= ADOPT_MAE_MARGIN:
        return True, f"holdout_mae_improved_{delta:.3f}"
    return False, f"holdout_mae_delta_{delta:.3f}_below_margin_{ADOPT_MAE_MARGIN}"


def run_holdout_calibration(
    games: Sequence[Mapping[str, Any]],
    priors: Mapping[Tuple[int, str], Mapping[str, Any]],
    *,
    train_years: Sequence[int] = TRAIN_YEARS,
    holdout_years: Sequence[int] = HOLDOUT_YEARS,
    example_id: str = "401628323",
) -> Dict[str, Any]:
    overlap = set(int(y) for y in train_years) & set(int(y) for y in holdout_years)
    if overlap:
        raise ValueError(f"Train/holdout overlap: {sorted(overlap)}")

    train_rows, train_ex = collect_eligible(
        games, priors, years=train_years, max_week=FIT_MAX_WEEK
    )
    holdout_rows, hold_ex = collect_eligible(
        games, priors, years=holdout_years, max_week=FIT_MAX_WEEK
    )
    fit = fit_scale_hfa(train_rows)
    scale, hfa = float(fit["scale"]), float(fit["hfa"])

    base_train = grade_scaled(
        train_rows, scale=BASELINE_SCALE, hfa=BASELINE_HFA, label="baseline"
    )
    cal_train = grade_scaled(train_rows, scale=scale, hfa=hfa, label="calibrated")
    base_hold = grade_scaled(
        holdout_rows, scale=BASELINE_SCALE, hfa=BASELINE_HFA, label="baseline"
    )
    cal_hold = grade_scaled(holdout_rows, scale=scale, hfa=hfa, label="calibrated")

    hold_base_m = band_metrics(base_hold)
    hold_cal_m = band_metrics(cal_hold)
    hold_n = int(hold_cal_m["w0_4"]["n_close"] or 0)
    hold_base_mae = hold_base_m["w0_4"]["mae"]
    hold_cal_mae = hold_cal_m["w0_4"]["mae"]
    adopted, reason = decide_adopt(
        baseline_holdout_mae=hold_base_mae,
        calibrated_holdout_mae=hold_cal_mae,
        holdout_n=hold_n,
        scale=scale,
    )

    example_base = example_row(base_hold, example_id) or example_row(base_train, example_id)
    example_cal = example_row(cal_hold, example_id) or example_row(cal_train, example_id)

    return {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "adopted": adopted,
        "adopt_reason": reason,
        "scale": scale if adopted else None,
        "hfa": hfa if adopted else None,
        "fitted_scale": scale,
        "fitted_hfa": hfa,
        "baseline_scale": BASELINE_SCALE,
        "baseline_hfa": BASELINE_HFA,
        "train_years": list(train_years),
        "holdout_years": list(holdout_years),
        "fit_weeks": f"0-{FIT_MAX_WEEK}",
        "fair": "fair_spread_home = -HFA - scale * (prior_home - prior_away)",
        "sign": "negative = home favored (lake / project-game)",
        "epa_in_fair": False,
        "used_in_spread": False,
        "close_definition": "last owned lake snap strictly before kickoff (not a true lock)",
        "mae_adopt_margin": ADOPT_MAE_MARGIN,
        "fit": fit,
        "exclusions": {"train": train_ex, "holdout": hold_ex},
        "train": {
            "baseline": band_metrics(base_train),
            "calibrated": band_metrics(cal_train),
        },
        "holdout": {
            "baseline": hold_base_m,
            "calibrated": hold_cal_m,
        },
        "example_game_id": example_id,
        "example_baseline": example_base,
        "example_calibrated": example_cal,
    }


def write_pack(pack: Mapping[str, Any], *, path: Optional[Path] = None) -> Path:
    dest = path or PACKAGED_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)
    slim = {
        "as_of": pack.get("as_of"),
        "adopted": pack.get("adopted"),
        "adopt_reason": pack.get("adopt_reason"),
        "scale": pack.get("scale"),
        "hfa": pack.get("hfa"),
        "fitted_scale": pack.get("fitted_scale"),
        "fitted_hfa": pack.get("fitted_hfa"),
        "baseline_scale": pack.get("baseline_scale"),
        "baseline_hfa": pack.get("baseline_hfa"),
        "train_years": pack.get("train_years"),
        "holdout_years": pack.get("holdout_years"),
        "fit_weeks": pack.get("fit_weeks"),
        "fair": pack.get("fair"),
        "epa_in_fair": False,
        "used_in_spread": False,
        "mae_adopt_margin": pack.get("mae_adopt_margin"),
        "fit": pack.get("fit"),
        "holdout_w0_4_mae_baseline": (pack.get("holdout") or {})
        .get("baseline", {})
        .get("w0_4", {})
        .get("mae"),
        "holdout_w0_4_mae_calibrated": (pack.get("holdout") or {})
        .get("calibrated", {})
        .get("w0_4", {})
        .get("mae"),
    }
    dest.write_text(json.dumps(slim, indent=2) + "\n")
    return dest
