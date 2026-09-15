"""Chronological validation + 2026 research application.

Training/validation select adjustment strength. The final holdout season is
untouched until the recommendation is written.

Baselines on the same next-game observations:
  (a) unadjusted season-to-date EPA/play
  (b) simple prior-season blend (n0=4, raw EPA — not opponent-adjusted)
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from src.services.cfb_warehouse.research_opp_adj import (
    DEFAULT_LAMBDA,
    DEFAULT_PRIOR_DECAY,
    DEFAULT_PRIOR_N0,
    EPA_SOURCE_NAME,
    PIPELINE_VERSION,
    PRODUCT_LABEL,
    AdjParams,
    FitResult,
    TeamGameEpa,
    TeamRating,
    blend_priors,
    fit_joint,
    games_before_cutoff,
    predict_game,
    rating_row,
)

HOLDOUT_SEASON = 2025
# Priors for the first modeled season come from these earlier years.
PRIOR_SEED_SEASONS = (2014, 2015)
TRAIN_SEASONS = tuple(range(2016, 2023))  # 2016–2022
VAL_SEASONS = (2023, 2024)
APPLY_SEASON = 2026
SIMPLE_BLEND_N0 = 4.0
EARLY_WEEKS = (1, 2, 3, 4)

PARAM_GRID = (
    AdjParams(lam=40.0, prior_n0=3.0, prior_decay=0.65),
    AdjParams(lam=40.0, prior_n0=4.0, prior_decay=0.75),
    AdjParams(lam=80.0, prior_n0=3.0, prior_decay=0.75),
    AdjParams(lam=80.0, prior_n0=4.0, prior_decay=0.75),
    AdjParams(lam=80.0, prior_n0=6.0, prior_decay=0.75),
    AdjParams(lam=80.0, prior_n0=4.0, prior_decay=0.85),
    AdjParams(lam=160.0, prior_n0=4.0, prior_decay=0.75),
    AdjParams(lam=160.0, prior_n0=6.0, prior_decay=0.85),
)

FROZEN_DEFAULT = AdjParams(
    lam=DEFAULT_LAMBDA,
    prior_n0=DEFAULT_PRIOR_N0,
    prior_decay=DEFAULT_PRIOR_DECAY,
)


def _mae(errors: Sequence[float]) -> Optional[float]:
    if not errors:
        return None
    return sum(abs(x) for x in errors) / len(errors)


def _rmse(errors: Sequence[float]) -> Optional[float]:
    if not errors:
        return None
    return math.sqrt(sum(x * x for x in errors) / len(errors))


def _bias(errors: Sequence[float]) -> Optional[float]:
    if not errors:
        return None
    return sum(errors) / len(errors)


def _summarize(errors: Sequence[float]) -> Dict[str, Any]:
    return {
        "n": len(errors),
        "mae": _mae(errors),
        "rmse": _rmse(errors),
        "bias": _bias(errors),
    }


def _std_to_date(
    games: Sequence[TeamGameEpa],
    *,
    season: int,
    week: int,
) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, int]]:
    off_s: Dict[str, float] = defaultdict(float)
    off_n: Dict[str, float] = defaultdict(float)
    def_s: Dict[str, float] = defaultdict(float)
    def_n: Dict[str, float] = defaultdict(float)
    n_g: Dict[str, int] = defaultdict(int)
    for g in games:
        if g.season != season or g.week >= week:
            continue
        off_s[g.offense] += g.n_weighted * g.y
        off_n[g.offense] += g.n_weighted
        def_s[g.defense] += g.n_weighted * g.y
        def_n[g.defense] += g.n_weighted
        n_g[g.offense] += 1
    off = {t: off_s[t] / off_n[t] for t in off_n if off_n[t]}
    deff = {t: def_s[t] / def_n[t] for t in def_n if def_n[t]}
    return off, deff, dict(n_g)


def _season_raw_means(
    games: Sequence[TeamGameEpa],
    season: int,
) -> Tuple[Dict[str, float], Dict[str, float]]:
    return _std_to_date(games, season=season, week=99)[:2]


def build_season_finals(
    games: Sequence[TeamGameEpa],
    seasons: Sequence[int],
    params: AdjParams,
) -> Dict[int, FitResult]:
    """Walk seasons forward. Each season-final is the prior seed for the next."""
    finals: Dict[int, FitResult] = {}
    prior_off: Dict[str, float] = {}
    prior_def: Dict[str, float] = {}
    for season in seasons:
        season_games = [g for g in games if g.season == int(season)]
        if not season_games:
            continue
        fit = fit_joint(
            season_games, params=params, prior_off=prior_off, prior_def=prior_def
        )
        finals[int(season)] = fit
        prior_off, prior_def = blend_priors(fit.ratings, decay=params.prior_decay)
    return finals


def pregame_fit(
    games: Sequence[TeamGameEpa],
    *,
    season: int,
    week: int,
    params: AdjParams,
    prior_fit: Optional[FitResult],
) -> FitResult:
    prior_off, prior_def = ({}, {})
    if prior_fit is not None:
        prior_off, prior_def = blend_priors(prior_fit.ratings, decay=params.prior_decay)
    window = [g for g in games if g.season == int(season) and g.week < int(week)]
    if not window:
        # Early season: ratings = decayed prior; μ/HFA from last season.
        if prior_fit is None:
            return fit_joint([], params=params)
        ratings = {}
        for team, rating in prior_fit.ratings.items():
            ratings[team] = TeamRating(
                team=team,
                off=float(params.prior_decay) * rating.off,
                defn=float(params.prior_decay) * rating.defn,
                off_raw=rating.off_raw,
                def_raw=rating.def_raw,
                n_plays=0.0,
                n_games=0,
                fcs_games=0,
                prior_off=float(params.prior_decay) * rating.off,
                prior_def=float(params.prior_decay) * rating.defn,
                prior_weight=1.0,
                in_season_weight=0.0,
                cold_start=False,
                insufficient_history=True,
                fcs=rating.fcs,
                uncertainty=1.0 / math.sqrt(params.lam),
            )
        return FitResult(
            mu=prior_fit.mu,
            hfa=prior_fit.hfa,
            ratings=ratings,
            params=params,
            n_obs=0,
            n_teams=len(ratings),
            n_fbs=sum(1 for r in ratings.values() if not r.fcs),
            iters=0,
            league_baseline=prior_fit.mu,
        )
    return fit_joint(window, params=params, prior_off=prior_off, prior_def=prior_def)


def evaluate_seasons(
    games: Sequence[TeamGameEpa],
    seasons: Sequence[int],
    params: AdjParams,
    *,
    finals: Optional[Mapping[int, FitResult]] = None,
) -> Dict[str, Any]:
    """Next-game off/def EPA error. Fits use only games before each cutoff."""
    if finals is None:
        seed = list(PRIOR_SEED_SEASONS) + [s for s in seasons if s < min(seasons)]
        # Build finals for every season before and including eval, except we
        # only need the prior season for each eval year.
        all_prior_seasons = sorted(
            {int(s) for s in list(PRIOR_SEED_SEASONS) + list(seasons)}
        )
        # Season-final for year Y uses all of Y — that would leak if we used
        # Y's final to predict Y. We only pass Y-1 as prior_fit.
        finals = build_season_finals(games, all_prior_seasons, params)

    adj_off: List[float] = []
    adj_def: List[float] = []
    raw_off: List[float] = []
    raw_def: List[float] = []
    blend_off: List[float] = []
    blend_def: List[float] = []
    early_adj_off: List[float] = []
    early_adj_def: List[float] = []
    n_cold = 0
    n_insufficient = 0
    n_games = 0

    by_week: Dict[str, Any] = {}

    for season in seasons:
        prior = finals.get(int(season) - 1)
        prior_raw_off, prior_raw_def = (
            _season_raw_means(games, int(season) - 1)
            if any(g.season == int(season) - 1 for g in games)
            else ({}, {})
        )
        weeks = sorted({g.week for g in games if g.season == int(season)})
        for week in weeks:
            fit = pregame_fit(
                games, season=int(season), week=int(week), params=params, prior_fit=prior
            )
            std_off, std_def, n_g = _std_to_date(games, season=int(season), week=int(week))
            targets = [
                g
                for g in games
                if g.season == int(season) and g.week == int(week) and not g.fcs_offense
            ]
            week_off = []
            week_def = []
            for g in targets:
                pred = predict_game(
                    fit, offense=g.offense, defense=g.defense, home=g.home
                )
                e_off = pred["pred_off_epa"] - g.y
                adj_off.append(e_off)
                week_off.append(e_off)
                # Defense observation for the defending team: same y.
                e_def = pred["pred_def_epa_allowed"] - g.y
                adj_def.append(e_def)
                week_def.append(e_def)

                raw_o = std_off.get(g.offense)
                raw_d = std_def.get(g.defense)
                if raw_o is None:
                    raw_o = prior_raw_off.get(g.offense, fit.mu)
                if raw_d is None:
                    raw_d = prior_raw_def.get(g.defense, fit.mu)
                raw_off.append(raw_o - g.y)
                raw_def.append(raw_d - g.y)

                ng = n_g.get(g.offense, 0)
                w = ng / (ng + SIMPLE_BLEND_N0)
                blend_o = w * raw_o + (1.0 - w) * prior_raw_off.get(g.offense, fit.mu)
                ngd = sum(
                    1
                    for x in games
                    if x.season == int(season) and x.week < int(week) and x.defense == g.defense
                )
                wd = ngd / (ngd + SIMPLE_BLEND_N0)
                blend_d = wd * raw_d + (1.0 - wd) * prior_raw_def.get(g.defense, fit.mu)
                blend_off.append(blend_o - g.y)
                blend_def.append(blend_d - g.y)

                off_r = fit.ratings.get(g.offense)
                if off_r and off_r.cold_start:
                    n_cold += 1
                if off_r and off_r.insufficient_history:
                    n_insufficient += 1
                n_games += 1
                if int(week) in EARLY_WEEKS:
                    early_adj_off.append(e_off)
                    early_adj_def.append(e_def)
            by_week[f"{season}w{week}"] = {
                "n": len(targets),
                "adj_off_mae": _mae(week_off),
                "adj_def_mae": _mae(week_def),
            }

    return {
        "params": asdict(params),
        "seasons": list(seasons),
        "n_team_games": n_games,
        "n_cold_start": n_cold,
        "n_insufficient_history": n_insufficient,
        "adjusted": {
            "off": _summarize(adj_off),
            "def": _summarize(adj_def),
            "early_off": _summarize(early_adj_off),
            "early_def": _summarize(early_adj_def),
        },
        "unadjusted_std": {
            "off": _summarize(raw_off),
            "def": _summarize(raw_def),
        },
        "prior_blend": {
            "off": _summarize(blend_off),
            "def": _summarize(blend_def),
            "n0": SIMPLE_BLEND_N0,
        },
        "by_week_head": {k: by_week[k] for k in list(by_week)[:12]},
        "mean_mae": _mean_pair_mae(adj_off, adj_def),
        "mean_mae_unadj": _mean_pair_mae(raw_off, raw_def),
        "mean_mae_blend": _mean_pair_mae(blend_off, blend_def),
    }


def _mean_pair_mae(a: Sequence[float], b: Sequence[float]) -> Optional[float]:
    ma, mb = _mae(a), _mae(b)
    if ma is None or mb is None:
        return None
    return 0.5 * (ma + mb)


def select_params(
    games: Sequence[TeamGameEpa],
    *,
    grid: Sequence[AdjParams] = PARAM_GRID,
    val_seasons: Sequence[int] = VAL_SEASONS,
) -> Dict[str, Any]:
    """Select on validation seasons only. Holdout is not passed in."""
    results = []
    best: Optional[AdjParams] = None
    best_mae = float("inf")
    # Season finals for priors: seed + train + val-1. Built per-params.
    prior_seasons = list(PRIOR_SEED_SEASONS) + list(TRAIN_SEASONS) + [
        s for s in val_seasons if s < max(val_seasons)
    ]
    for params in grid:
        finals = build_season_finals(
            games,
            sorted(set(int(s) for s in prior_seasons + list(val_seasons))),
            params,
        )
        ev = evaluate_seasons(games, val_seasons, params, finals=finals)
        mae = ev.get("mean_mae")
        results.append(
            {
                "params": asdict(params),
                "mean_mae": mae,
                "mean_mae_unadj": ev.get("mean_mae_unadj"),
                "mean_mae_blend": ev.get("mean_mae_blend"),
                "n": ev["n_team_games"],
            }
        )
        if mae is not None and mae < best_mae:
            best_mae = mae
            best = params
    if best is None:
        best = FROZEN_DEFAULT
    return {
        "selected": asdict(best),
        "selected_val_mae": None if best_mae == float("inf") else best_mae,
        "grid": results,
        "selection_seasons": list(val_seasons),
        "holdout_season": HOLDOUT_SEASON,
        "holdout_used_for_selection": False,
        "note": "Adjustment strength chosen on validation only; 2025 holdout untouched.",
    }


def recommend(holdout: Mapping[str, Any], selection: Mapping[str, Any]) -> Dict[str, Any]:
    """advance / revise / reject from held-out evidence only."""
    adj = holdout.get("mean_mae")
    raw = holdout.get("mean_mae_unadj")
    blend = holdout.get("mean_mae_blend")
    n = int(holdout.get("n_team_games") or 0)
    if adj is None or raw is None or n < 200:
        return {
            "recommendation": "reject",
            "reason": "holdout too thin or missing MAE",
            "n": n,
        }
    beat_raw = adj < raw - 1e-6
    beat_blend = blend is None or adj < blend - 1e-6
    # Material improvement: ≥1% relative MAE cut vs both baselines, or ≥0.005 abs.
    rel_raw = (raw - adj) / raw if raw else 0.0
    rel_blend = ((blend - adj) / blend) if blend else 0.0
    material = (rel_raw >= 0.01 and (blend is None or rel_blend >= 0.01)) or (
        (raw - adj) >= 0.005 and (blend is None or (blend - adj) >= 0.005)
    )
    if beat_raw and beat_blend and material:
        rec = "advance"
        reason = (
            "Holdout next-game O/D EPA MAE beats unadjusted STD and prior-season "
            "blend by a material margin. Research-only — not a production promote."
        )
    elif beat_raw or beat_blend:
        rec = "revise"
        reason = (
            "Holdout beats one baseline but not both, or the gain is thin. "
            "Keep research; do not promote. Revisit HFA / FCS / early-season shrink."
        )
    else:
        rec = "reject"
        reason = (
            "Holdout does not beat the unadjusted or prior-blend baselines. "
            "Do not promote. Do not convert to spreads."
        )
    return {
        "recommendation": rec,
        "reason": reason,
        "holdout_mae_adj": adj,
        "holdout_mae_unadj": raw,
        "holdout_mae_blend": blend,
        "rel_improvement_vs_unadj": rel_raw,
        "rel_improvement_vs_blend": rel_blend,
        "n": n,
        "selected_params": selection.get("selected"),
        "production_promote": False,
    }


def apply_to_season(
    games: Sequence[TeamGameEpa],
    *,
    season: int,
    as_of_week: int,
    params: AdjParams,
    prior_fit: Optional[FitResult],
) -> Dict[str, Any]:
    fit = pregame_fit(
        games, season=int(season), week=int(as_of_week), params=params, prior_fit=prior_fit
    )
    rows = []
    for team, rating in sorted(fit.ratings.items()):
        if rating.fcs:
            continue
        rows.append(
            rating_row(
                rating,
                season=int(season),
                as_of_week=int(as_of_week),
                mu=fit.mu,
                hfa=fit.hfa,
                params=params,
            )
        )
    return {
        "pipeline_version": PIPELINE_VERSION,
        "product_label": PRODUCT_LABEL,
        "research_only": True,
        "not_ke_ratings": True,
        "not_point_spread": True,
        "not_kei": True,
        "epa_source": EPA_SOURCE_NAME,
        "season": int(season),
        "as_of_week": int(as_of_week),
        "mu": fit.mu,
        "hfa": fit.hfa,
        "n_obs": fit.n_obs,
        "n_teams": len(rows),
        "params": asdict(params),
        "ratings": rows,
    }


def run_validation_suite(
    games: Sequence[TeamGameEpa],
    *,
    dest: Optional[Path] = None,
) -> Dict[str, Any]:
    selection = select_params(games)
    selected = AdjParams(**selection["selected"])
    # Rebuild finals with selected params for holdout + apply.
    all_seasons = sorted({g.season for g in games})
    finals = build_season_finals(games, all_seasons, selected)
    # Train diagnostic (not used for selection).
    train = evaluate_seasons(games, TRAIN_SEASONS, selected, finals=finals)
    val = evaluate_seasons(games, VAL_SEASONS, selected, finals=finals)
    holdout = evaluate_seasons(games, (HOLDOUT_SEASON,), selected, finals=finals)
    rec = recommend(holdout, selection)
    report = {
        "pipeline_version": PIPELINE_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "not_ke_ratings": True,
        "epa_source": EPA_SOURCE_NAME,
        "eligible_play_rules": (
            "scrimmage + finite EPA + regulation; garbage-weighted; FCS kept"
        ),
        "pregame_cutoff": "same-season week < target week; priors from earlier seasons only",
        "selection": selection,
        "train_diagnostic": train,
        "validation": val,
        "holdout": holdout,
        "recommendation": rec,
        "production_sp_plus_unchanged": True,
        "production_nfl_unchanged": True,
        "production_kei_unchanged": True,
        "spreads_totals_out_of_scope": True,
    }
    if dest is not None:
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "validation_report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
