"""Chronological scoring validation. Protocol locked in docs/cfb/EVAL_PROTOCOL.md.

Fit on 2016–2022. Select knobs on 2023 only. Seal on 2024 weeks ≥ 10.
2025 is development evidence — never selection, never the recommendation seal.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from src.services.cfb_warehouse.research_opp_adj import AdjParams, TeamGameEpa
from src.services.cfb_warehouse.research_opp_adj_validate import (
    IBF_FALLBACK_SEASONS,
    PRIOR_SEED_SEASONS,
    build_season_finals,
    pregame_fit,
)
from src.services.cfb_warehouse.research_scoring import (
    FROZEN_EPA_KNOBS,
    HFA_K_GRID,
    MARGIN_SIGN,
    PACE_COMPETITIVE,
    PACE_SOURCES,
    PIPELINE_VERSION,
    PRODUCTION_PROMOTE,
    PRODUCT_LABEL,
    RESEARCH_ONLY,
    ScoringFit,
    ScoringKnobs,
    apply_scoring_fit,
    fit_scoring,
    plays_per_possession,
    predict_epa_no_hfa,
)

PROTOCOL_PATH = "docs/cfb/EVAL_PROTOCOL.md"
SCORING_TRAIN_SEASONS = tuple(range(2016, 2023))  # 2016–2022
SCORING_VAL_SEASONS = (2023,)
SCORING_CONFIRM_SEASON = 2024
SCORING_CONFIRM_MIN_WEEK = 10
SCORING_DEV_EVIDENCE_SEASON = 2025
POINTS_BLEND_N0 = 4.0
EARLY_WEEKS = (1, 2, 3, 4)
MID_WEEKS = (5, 6, 7, 8, 9)

FROZEN_PARAMS = AdjParams(
    lam=FROZEN_EPA_KNOBS["lam"],
    prior_n0=FROZEN_EPA_KNOBS["prior_n0"],
    prior_decay=FROZEN_EPA_KNOBS["prior_decay"],
    lam_fcs_mult=FROZEN_EPA_KNOBS["lam_fcs_mult"],
    iters=int(FROZEN_EPA_KNOBS["iters"]),
)


def _f(raw: Any, default: float = float("nan")) -> float:
    if raw is None or raw == "":
        return default
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(val):
        return default
    return val


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
    return {"n": len(errors), "mae": _mae(errors), "rmse": _rmse(errors), "bias": _bias(errors)}


def in_scoring_train(season: int) -> bool:
    return int(season) in SCORING_TRAIN_SEASONS


def in_scoring_val(season: int, week: int) -> bool:
    return int(season) in SCORING_VAL_SEASONS


def in_scoring_confirm(season: int, week: int) -> bool:
    return int(season) == SCORING_CONFIRM_SEASON and int(week) >= SCORING_CONFIRM_MIN_WEEK


def in_dev_evidence(season: int) -> bool:
    return int(season) == SCORING_DEV_EVIDENCE_SEASON


def scoring_set_label(season: int, week: int) -> str:
    if in_scoring_train(season):
        return "train"
    if in_scoring_val(season, week):
        return "validation"
    if in_scoring_confirm(season, week):
        return "confirmation"
    if in_dev_evidence(season):
        return "development_evidence"
    return "other"


def week_band(week: int) -> str:
    if int(week) in EARLY_WEEKS:
        return "early"
    if int(week) in MID_WEEKS:
        return "mid"
    return "late"


def _std_points_to_date(
    games: Sequence[Mapping[str, Any]],
    *,
    season: int,
    week: int,
) -> Dict[str, float]:
    s: Dict[str, float] = defaultdict(float)
    n: Dict[str, int] = defaultdict(int)
    for g in games:
        if int(g["season"]) != int(season) or int(g["week"]) >= int(week):
            continue
        if g.get("home_points") is None or g.get("away_points") is None:
            continue
        s[str(g["home"])] += float(g["home_points"])
        n[str(g["home"])] += 1
        s[str(g["away"])] += float(g["away_points"])
        n[str(g["away"])] += 1
    return {t: s[t] / n[t] for t in n if n[t]}


def _season_points_means(
    games: Sequence[Mapping[str, Any]], season: int
) -> Dict[str, float]:
    return _std_points_to_date(games, season=season, week=99)


def train_league_points(games: Sequence[Mapping[str, Any]]) -> float:
    vals = []
    for g in games:
        if int(g["season"]) not in SCORING_TRAIN_SEASONS:
            continue
        for key in ("home_points", "away_points"):
            val = _f(g.get(key))
            if math.isfinite(val):
                vals.append(val)
    if not vals:
        return 27.0
    return sum(vals) / len(vals)


def train_league_pace(
    pace_rows: Mapping[Tuple[str, str], Mapping[str, float]],
    scores: Mapping[str, Mapping[str, Any]],
    *,
    source: str,
) -> float:
    vals = []
    for (gid, team), row in pace_rows.items():
        game = scores.get(gid)
        if game is None or int(game.get("season") or 0) not in SCORING_TRAIN_SEASONS:
            continue
        if str(team).startswith("fcs:"):
            continue
        val = _f(row.get(source))
        if math.isfinite(val) and val > 0:
            vals.append(val)
    if not vals:
        return 65.0
    return sum(vals) / len(vals)


def pregame_pace(
    team: str,
    *,
    season: int,
    week: int,
    source: str,
    pace_by_team_week: Mapping[Tuple[int, int, str], List[float]],
    prior_pace: Mapping[str, float],
    league_pace: float,
) -> float:
    same = []
    for (s, w, t), vals in pace_by_team_week.items():
        if s == int(season) and w < int(week) and t == team:
            same.extend(vals)
    if same:
        return sum(same) / len(same)
    if team in prior_pace:
        return float(prior_pace[team])
    return float(league_pace)


def index_pace_by_team_week(
    pace_rows: Mapping[Tuple[str, str], Mapping[str, float]],
    scores: Mapping[str, Mapping[str, Any]],
    *,
    source: str,
) -> Dict[Tuple[int, int, str], List[float]]:
    out: Dict[Tuple[int, int, str], List[float]] = defaultdict(list)
    for (gid, team), row in pace_rows.items():
        game = scores.get(gid)
        if game is None:
            continue
        val = _f(row.get(source))
        if math.isfinite(val) and val > 0:
            out[(int(game["season"]), int(game["week"]), str(team))].append(val)
    return out


def prior_season_pace(
    pace_rows: Mapping[Tuple[str, str], Mapping[str, float]],
    scores: Mapping[str, Mapping[str, Any]],
    *,
    season: int,
    source: str,
) -> Dict[str, float]:
    acc: Dict[str, List[float]] = defaultdict(list)
    for (gid, team), row in pace_rows.items():
        game = scores.get(gid)
        if game is None or int(game.get("season") or 0) != int(season):
            continue
        val = _f(row.get(source))
        if math.isfinite(val) and val > 0:
            acc[str(team)].append(val)
    return {t: sum(v) / len(v) for t, v in acc.items()}


def build_game_list(
    scores: Mapping[str, Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    out = []
    for gid, g in scores.items():
        hp, ap = g.get("home_points"), g.get("away_points")
        if hp is None or ap is None:
            continue
        if not g.get("home") or not g.get("away"):
            continue
        if g["home"].startswith("fcs:") and g["away"].startswith("fcs:"):
            continue
        out.append(
            {
                "game_id": gid,
                "season": int(g["season"]),
                "week": int(g["week"]),
                "home": str(g["home"]),
                "away": str(g["away"]),
                "home_points": float(hp),
                "away_points": float(ap),
                "neutral": bool(g.get("neutral")),
                "home_fcs": bool(g.get("home_fcs")),
                "away_fcs": bool(g.get("away_fcs")),
                "fbs_vs_fbs": (not g.get("home_fcs")) and (not g.get("away_fcs")),
                "margin": float(hp) - float(ap),
                "total": float(hp) + float(ap),
                "set": scoring_set_label(int(g["season"]), int(g["week"])),
                "band": week_band(int(g["week"])),
            }
        )
    out.sort(key=lambda r: (r["season"], r["week"], r["game_id"]))
    return out


def attach_pregame_epa(
    games: Sequence[Mapping[str, Any]],
    epa_games: Sequence[TeamGameEpa],
    *,
    params: AdjParams = FROZEN_PARAMS,
) -> List[Dict[str, Any]]:
    """Pregame off/def EPA without converting EPA h into points."""
    seasons = sorted({int(g["season"]) for g in games} | {int(x.season) for x in epa_games})
    prior_seasons = sorted(set(list(PRIOR_SEED_SEASONS) + [s for s in seasons if s <= max(seasons)]))
    finals = build_season_finals(epa_games, prior_seasons, params)
    by_sw: Dict[Tuple[int, int], List[Dict[str, Any]]] = defaultdict(list)
    for g in games:
        by_sw[(int(g["season"]), int(g["week"]))].append(dict(g))
    out: List[Dict[str, Any]] = []
    for (season, week), rows in sorted(by_sw.items()):
        prior = finals.get(int(season) - 1)
        fit = pregame_fit(
            epa_games, season=int(season), week=int(week), params=params, prior_fit=prior
        )
        for g in rows:
            g["epa_home"] = predict_epa_no_hfa(fit, offense=g["home"], defense=g["away"])
            g["epa_away"] = predict_epa_no_hfa(fit, offense=g["away"], defense=g["home"])
            g["epa_mu"] = fit.mu
            g["epa_h_unused"] = fit.hfa
            out.append(g)
    return out


def attach_expected_pace(
    games: Sequence[Mapping[str, Any]],
    pace_rows: Mapping[Tuple[str, str], Mapping[str, float]],
    scores: Mapping[str, Mapping[str, Any]],
    *,
    source: str,
    league_pace: float,
) -> List[Dict[str, Any]]:
    indexed = index_pace_by_team_week(pace_rows, scores, source=source)
    out = []
    for g in games:
        prior = prior_season_pace(
            pace_rows, scores, season=int(g["season"]) - 1, source=source
        )
        ph = pregame_pace(
            g["home"],
            season=int(g["season"]),
            week=int(g["week"]),
            source=source,
            pace_by_team_week=indexed,
            prior_pace=prior,
            league_pace=league_pace,
        )
        pa = pregame_pace(
            g["away"],
            season=int(g["season"]),
            week=int(g["week"]),
            source=source,
            pace_by_team_week=indexed,
            prior_pace=prior,
            league_pace=league_pace,
        )
        rec = dict(g)
        rec["pace_home"] = ph
        rec["pace_away"] = pa
        rec["exp_plays"] = 0.5 * (ph + pa)
        rec["pace_source"] = source
        out.append(rec)
    return out


def team_rows_from_games(games: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for g in games:
        exp = _f(g.get("exp_plays"))
        if not math.isfinite(exp) or exp <= 0:
            continue
        rows.append(
            {
                "game_id": g["game_id"],
                "season": g["season"],
                "week": g["week"],
                "team": g["home"],
                "points": g["home_points"],
                "epa": g["epa_home"],
                "epa_plays": float(g["epa_home"]) * exp,
                "exp_plays": exp,
                "home": 0.0 if g.get("neutral") else 1.0,
                "set": g["set"],
                "band": g["band"],
                "fbs_vs_fbs": g.get("fbs_vs_fbs"),
            }
        )
        rows.append(
            {
                "game_id": g["game_id"],
                "season": g["season"],
                "week": g["week"],
                "team": g["away"],
                "points": g["away_points"],
                "epa": g["epa_away"],
                "epa_plays": float(g["epa_away"]) * exp,
                "exp_plays": exp,
                "home": 0.0,
                "set": g["set"],
                "band": g["band"],
                "fbs_vs_fbs": g.get("fbs_vs_fbs"),
            }
        )
    return rows


def predict_games(games: Sequence[Mapping[str, Any]], fit: ScoringFit) -> List[Dict[str, Any]]:
    out = []
    for g in games:
        exp = _f(g.get("exp_plays"))
        home_ind = 0.0 if g.get("neutral") else 1.0
        ph = apply_scoring_fit(fit, epa=float(g["epa_home"]), exp_plays=exp, home=home_ind)
        pa = apply_scoring_fit(fit, epa=float(g["epa_away"]), exp_plays=exp, home=0.0)
        pred_margin = ph - pa
        pred_total = ph + pa
        rec = dict(g)
        rec["pred_home_points"] = ph
        rec["pred_away_points"] = pa
        rec["pred_margin"] = pred_margin
        rec["pred_total"] = pred_total
        rec["err_margin"] = pred_margin - float(g["margin"])
        rec["err_total"] = pred_total - float(g["total"])
        rec["err_home_points"] = ph - float(g["home_points"])
        rec["err_away_points"] = pa - float(g["away_points"])
        out.append(rec)
    return out


def baseline_predict(
    games: Sequence[Mapping[str, Any]],
    all_games: Sequence[Mapping[str, Any]],
    *,
    train_pts: float,
) -> Dict[str, List[Dict[str, Any]]]:
    """Vegas-free point baselines. IBF-style train league mean if STD/prior missing."""
    std_rows = []
    blend_rows = []
    league_rows = []
    n_prior: Dict[Tuple[int, int, str], int] = {}
    by_season_week: Dict[Tuple[int, int], List[Mapping[str, Any]]] = defaultdict(list)
    for x in all_games:
        by_season_week[(int(x["season"]), int(x["week"]))].append(x)
    running: Dict[Tuple[int, str], int] = defaultdict(int)
    for (season, week) in sorted(by_season_week):
        for team in list({str(x["home"]) for x in by_season_week[(season, week)]} | {str(x["away"]) for x in by_season_week[(season, week)]}):
            n_prior[(season, week, team)] = running[(season, team)]
        for x in by_season_week[(season, week)]:
            running[(season, str(x["home"]))] += 1
            running[(season, str(x["away"]))] += 1
    for g in games:
        std = _std_points_to_date(all_games, season=int(g["season"]), week=int(g["week"]))
        prior = _season_points_means(all_games, int(g["season"]) - 1)
        sh = std.get(g["home"])
        sa = std.get(g["away"])
        if sh is None:
            sh = prior.get(g["home"], train_pts)
        if sa is None:
            sa = prior.get(g["away"], train_pts)
        ng_h = n_prior.get((int(g["season"]), int(g["week"]), str(g["home"])), 0)
        ng_a = n_prior.get((int(g["season"]), int(g["week"]), str(g["away"])), 0)
        wh = ng_h / (ng_h + POINTS_BLEND_N0)
        wa = ng_a / (ng_a + POINTS_BLEND_N0)
        bh = wh * sh + (1.0 - wh) * prior.get(g["home"], train_pts)
        ba = wa * sa + (1.0 - wa) * prior.get(g["away"], train_pts)
        std_rows.append(_baseline_row(g, sh, sa))
        blend_rows.append(_baseline_row(g, bh, ba))
        league_rows.append(_baseline_row(g, train_pts, train_pts))
    return {
        "std_points": std_rows,
        "prior_blend_points": blend_rows,
        "league_mean_points": league_rows,
    }


def _baseline_row(g: Mapping[str, Any], ph: float, pa: float) -> Dict[str, Any]:
    pred_margin = ph - pa
    pred_total = ph + pa
    return {
        **dict(g),
        "pred_home_points": ph,
        "pred_away_points": pa,
        "pred_margin": pred_margin,
        "pred_total": pred_total,
        "err_margin": pred_margin - float(g["margin"]),
        "err_total": pred_total - float(g["total"]),
        "err_home_points": ph - float(g["home_points"]),
        "err_away_points": pa - float(g["away_points"]),
    }


def metrics_block(rows: Sequence[Mapping[str, Any]], *, fbs_vs_fbs: Optional[bool] = True) -> Dict[str, Any]:
    use = [r for r in rows if (fbs_vs_fbs is None or r.get("fbs_vs_fbs") == fbs_vs_fbs)]
    by_band = {"early": [], "mid": [], "late": []}
    for r in use:
        by_band[str(r.get("band") or week_band(int(r["week"])))].append(r)

    def _pack(subset: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
        return {
            "n_games": len(subset),
            "margin": _summarize([float(r["err_margin"]) for r in subset]),
            "total": _summarize([float(r["err_total"]) for r in subset]),
            "home_points": _summarize([float(r["err_home_points"]) for r in subset]),
            "away_points": _summarize([float(r["err_away_points"]) for r in subset]),
            "team_points": _summarize(
                [float(r["err_home_points"]) for r in subset]
                + [float(r["err_away_points"]) for r in subset]
            ),
        }

    return {
        "all": _pack(use),
        "early": _pack(by_band["early"]),
        "mid": _pack(by_band["mid"]),
        "late": _pack(by_band["late"]),
        "fbs_vs_fbs": fbs_vs_fbs,
        "margin_sign": MARGIN_SIGN,
    }


def select_scoring_params(
    *,
    val_games: Sequence[Mapping[str, Any]],
    train_team_rows_by_pace: Mapping[str, Sequence[Mapping[str, Any]]],
    train_games: Sequence[Mapping[str, Any]],
    val_games_by_pace: Mapping[str, Sequence[Mapping[str, Any]]],
    ppp: float,
    league_pace_by_source: Mapping[str, float],
    train_pts: float,
    val_seasons: Sequence[int] = SCORING_VAL_SEASONS,
) -> Dict[str, Any]:
    """Select on validation seasons only. Confirmation / 2025 are not passed in."""
    if tuple(val_seasons) != SCORING_VAL_SEASONS:
        raise ValueError(f"scoring selection must use {SCORING_VAL_SEASONS}, got {val_seasons}")
    grid = []
    best: Optional[ScoringKnobs] = None
    best_score = float("inf")
    best_bias = float("inf")
    best_fit: Optional[ScoringFit] = None
    for source in PACE_SOURCES:
        train_rows = train_team_rows_by_pace[source]
        for k in HFA_K_GRID:
            knobs = ScoringKnobs(pace_source=source, hfa_k=float(k))
            fitted = fit_scoring(
                train_rows,
                train_games,
                knobs=knobs,
                ppp=ppp,
                league_pace=league_pace_by_source[source],
                train_league_points=train_pts,
            )
            pred = predict_games(val_games_by_pace[source], fitted)
            block = metrics_block(pred)
            m_mae = block["all"]["margin"]["mae"]
            t_mae = block["all"]["total"]["mae"]
            if m_mae is None or t_mae is None:
                continue
            score = 0.5 * (m_mae + t_mae)
            bias = abs(block["all"]["margin"]["bias"] or 0.0)
            grid.append(
                {
                    "knobs": knobs.as_dict(),
                    "val_margin_mae": m_mae,
                    "val_total_mae": t_mae,
                    "val_objective": score,
                    "val_margin_bias": block["all"]["margin"]["bias"],
                    "n": block["all"]["n_games"],
                }
            )
            if score < best_score - 1e-12 or (
                abs(score - best_score) <= 1e-12 and bias < best_bias
            ):
                best_score = score
                best_bias = bias
                best = knobs
                best_fit = fitted
    if best is None or best_fit is None:
        best = ScoringKnobs()
        best_fit = fit_scoring(
            train_team_rows_by_pace[PACE_COMPETITIVE],
            train_games,
            knobs=best,
            ppp=ppp,
            league_pace=league_pace_by_source[PACE_COMPETITIVE],
            train_league_points=train_pts,
        )
    return {
        "selected": best.as_dict(),
        "selected_fit": best_fit.as_dict(),
        "selected_val_objective": None if best_score == float("inf") else best_score,
        "grid": grid,
        "selection_seasons": list(val_seasons),
        "confirmation_season": SCORING_CONFIRM_SEASON,
        "confirmation_min_week": SCORING_CONFIRM_MIN_WEEK,
        "development_evidence_season": SCORING_DEV_EVIDENCE_SEASON,
        "holdout_used_for_selection": False,
        "confirmation_used_for_selection": False,
        "dev_evidence_used_for_selection": False,
        "protocol": PROTOCOL_PATH,
    }


def recommend_scoring(
    confirm: Mapping[str, Any],
    baselines: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    """advance / revise / reject from the confirmation set only."""
    adj_m = (confirm.get("all") or {}).get("margin") or {}
    adj_t = (confirm.get("all") or {}).get("total") or {}
    n = int((confirm.get("all") or {}).get("n_games") or 0)
    if adj_m.get("mae") is None or adj_t.get("mae") is None or n < 150:
        return {
            "recommendation": "reject",
            "reason": "confirmation too thin or missing MAE",
            "n": n,
            "production_promote": False,
        }

    def _best_base(metric: str) -> Tuple[str, float]:
        best_name = None
        best_mae = float("inf")
        for name, block in baselines.items():
            mae = ((block.get("all") or {}).get(metric) or {}).get("mae")
            if mae is not None and mae < best_mae:
                best_mae = mae
                best_name = name
        return str(best_name), best_mae

    base_m_name, base_m = _best_base("margin")
    base_t_name, base_t = _best_base("total")

    def _beats(adj: float, base: float) -> bool:
        if base <= 0:
            return False
        rel = (base - adj) / base
        return rel >= 0.01 or (base - adj) >= 0.25

    beat_m = _beats(float(adj_m["mae"]), base_m)
    beat_t = _beats(float(adj_t["mae"]), base_t)

    def _bias_ok(adj_bias: Optional[float], metric: str) -> bool:
        best_abs = float("inf")
        for block in baselines.values():
            b = ((block.get("all") or {}).get(metric) or {}).get("bias")
            if b is not None:
                best_abs = min(best_abs, abs(float(b)))
        if adj_bias is None or best_abs == float("inf"):
            return True
        return abs(float(adj_bias)) <= best_abs + 1.5

    bias_ok = _bias_ok(adj_m.get("bias"), "margin") and _bias_ok(adj_t.get("bias"), "total")
    if beat_m and beat_t and bias_ok:
        rec = "advance"
        reason = (
            "Confirmation (2024 weeks ≥ 10) margin and total MAE beat both "
            "Vegas-free point baselines by the locked threshold. Research-only "
            "— not a production promote."
        )
    elif beat_m or beat_t:
        rec = "revise"
        reason = (
            "Confirmation beats one of {margin, total} or the gain is thin / "
            "bias is worse than +1.5 vs the better baseline. Keep research."
        )
    else:
        rec = "reject"
        reason = (
            "Confirmation does not beat the Vegas-free point baselines on "
            "margin and total. Do not promote. Do not reopen boards."
        )
    return {
        "recommendation": rec,
        "reason": reason,
        "n": n,
        "confirm_margin_mae": adj_m.get("mae"),
        "confirm_total_mae": adj_t.get("mae"),
        "best_baseline_margin": {"name": base_m_name, "mae": base_m},
        "best_baseline_total": {"name": base_t_name, "mae": base_t},
        "rel_margin": None if not base_m else (base_m - float(adj_m["mae"])) / base_m,
        "rel_total": None if not base_t else (base_t - float(adj_t["mae"])) / base_t,
        "production_promote": False,
        "confirmation_set": "2024 weeks >= 10",
        "dev_evidence_2025_not_used_for_call": True,
    }


def run_scoring_suite(
    *,
    epa_games: Sequence[TeamGameEpa],
    scores: Mapping[str, Mapping[str, Any]],
    pace_rows: Mapping[Tuple[str, str], Mapping[str, float]],
) -> Dict[str, Any]:
    games = build_game_list(scores)
    games = attach_pregame_epa(games, epa_games)
    ppp = plays_per_possession(pace_rows, scores, seasons=SCORING_TRAIN_SEASONS)
    train_pts = train_league_points(games)
    league_pace = {src: train_league_pace(pace_rows, scores, source=src) for src in PACE_SOURCES}

    by_pace: Dict[str, List[Dict[str, Any]]] = {}
    for src in PACE_SOURCES:
        by_pace[src] = attach_expected_pace(
            games, pace_rows, scores, source=src, league_pace=league_pace[src]
        )

    train_games = [g for g in by_pace[PACE_COMPETITIVE] if g["set"] == "train"]
    train_rows = {src: team_rows_from_games([g for g in by_pace[src] if g["set"] == "train"]) for src in PACE_SOURCES}
    val_by_pace = {src: [g for g in by_pace[src] if g["set"] == "validation"] for src in PACE_SOURCES}

    selection = select_scoring_params(
        val_games=val_by_pace[PACE_COMPETITIVE],
        train_team_rows_by_pace=train_rows,
        train_games=train_games,
        val_games_by_pace=val_by_pace,
        ppp=ppp,
        league_pace_by_source=league_pace,
        train_pts=train_pts,
    )
    knobs = ScoringKnobs(**selection["selected"])
    chosen = by_pace[knobs.pace_source]
    fitted = fit_scoring(
        train_rows[knobs.pace_source],
        train_games,
        knobs=knobs,
        ppp=ppp,
        league_pace=league_pace[knobs.pace_source],
        train_league_points=train_pts,
    )

    def _eval(label: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Any]]:
        subset = [g for g in chosen if g["set"] == label]
        pred = predict_games(subset, fitted)
        model = metrics_block(pred)
        bases_pred = baseline_predict(subset, games, train_pts=train_pts)
        bases = {name: metrics_block(rows) for name, rows in bases_pred.items()}
        return pred, model, bases

    train_pred, train_m, train_b = _eval("train")
    val_pred, val_m, val_b = _eval("validation")
    confirm_pred, confirm_m, confirm_b = _eval("confirmation")
    dev_pred, dev_m, dev_b = _eval("development_evidence")
    rec = recommend_scoring(confirm_m, confirm_b)

    return {
        "pipeline_version": PIPELINE_VERSION,
        "product_label": PRODUCT_LABEL,
        "research_only": RESEARCH_ONLY,
        "production_promote": PRODUCTION_PROMOTE,
        "protocol": PROTOCOL_PATH,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "margin_sign": MARGIN_SIGN,
        "frozen_epa": {"estimator": "fit_joint_v2_joint_mu_hfa_n0_ridge", **asdict(FROZEN_PARAMS)},
        "ibf_fallback_seasons": list(IBF_FALLBACK_SEASONS),
        "splits": {
            "train": list(SCORING_TRAIN_SEASONS),
            "validation": list(SCORING_VAL_SEASONS),
            "confirmation": {
                "season": SCORING_CONFIRM_SEASON,
                "min_week": SCORING_CONFIRM_MIN_WEEK,
            },
            "development_evidence": SCORING_DEV_EVIDENCE_SEASON,
        },
        "hfa": {
            "rule": "h_pts = (N/(N+k))*h_window + (k/(N+k))*h_prior",
            "units": "points added to the home team (0 on neutrals)",
            "thin_window_epa_h_times_plays": False,
            **fitted.as_dict(),
        },
        "pace": {
            "formula": "exp_plays = 0.5 * (pregame_home + pregame_away); exp_poss = exp_plays / ppp",
            "ppp": ppp,
            "ppp_definition": "train mean of pace_plays / n_drives on FBS-offense team-games",
            "source_selected": knobs.pace_source,
            "league_pace": league_pace,
        },
        "selection": selection,
        "train": {"model": train_m, "baselines": train_b, "n_pred": len(train_pred)},
        "validation": {"model": val_m, "baselines": val_b, "n_pred": len(val_pred)},
        "confirmation": {
            "model": confirm_m,
            "baselines": confirm_b,
            "n_pred": len(confirm_pred),
            "label": "2024 weeks >= 10 — scoring seal",
        },
        "development_evidence_2025": {
            "model": dev_m,
            "baselines": dev_b,
            "n_pred": len(dev_pred),
            "label": "development evidence — EPA-known year, not confirmation",
            "used_for_selection": False,
            "used_for_recommendation": False,
        },
        "recommendation": rec,
        "production_sp_plus_unchanged": True,
        "production_nfl_unchanged": True,
        "production_kei_unchanged": True,
        "boards_stay_coming_soon": True,
    }
