#!/usr/bin/env python3
"""Time-ordered historical totals experiment (2025 sealed).

Fit window: 2023–2024 W0–2 only.
2025 residuals are not computed unless --open-2025 AND a freeze file exists.

Does not edit production model / KEI / PLAY / kill switch.

Usage:
  PYTHONPATH=services/model-service \\
    python3 scripts/cfb/run_hist_livepath_totals.py --cache-dir data/cfb/raw/sdv
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
sys.path.insert(0, str(MS))

from src.services.cfb_season_engine import priors as P  # noqa: E402
from src.services.cfb_season_engine.historical_calibration import (  # noqa: E402
    build_historical_proxy_state,
    build_historical_proxy_universe,
    load_historical_games,
    ratings_to_efficiency_map,
)
from src.services.cfb_season_engine.hist_week0 import (  # noqa: E402
    RECON_PATH_NAME,
    assert_2025_sealed,
    reconstruction_inventory,
)
from src.services.cfb_season_engine.qb_situation import build_qb_situation  # noqa: E402
from src.services.cfb_season_engine.roster_construction import (  # noqa: E402
    build_roster_construction,
)
from src.services.cfb_season_engine.position_groups import build_position_groups  # noqa: E402
from src.services.cfb_season_engine.team_projection import (  # noqa: E402
    compose_team_projection,
    project_game,
)
from src.services.cfb_season_engine.totals_guard_holdout import (  # noqa: E402
    CUPCAKE_ABS_SPREAD_GE,
    FIT_SEASONS,
    PEER_ABS_SPREAD_LT,
    PRIMARY_WEEK_MAX,
    apply_level_offset,
    apply_matchup_inflation_dampen,
    filter_fit_rows,
    fit_lambda_ols,
    fit_level_offset,
    matchup_inflation_on_sum,
    mismatch_bucket,
    summarize_kei_vs_close,
)

P4_CONFS = {"SEC", "Big Ten", "ACC", "Big 12"}
from src.services.cfb_season_engine.types import EngineUniverse  # noqa: E402

DATA = MS / "src/services/cfb_season_engine/data"
INFLATION_REPRODUCE_MIN = 6.0  # mean matchup inflation on fit W0-2 to allow a λ fit


def _mean(xs: Sequence[float]) -> Optional[float]:
    return None if not xs else round(sum(xs) / len(xs), 4)


def _mae(xs: Sequence[float]) -> Optional[float]:
    return None if not xs else round(sum(abs(x) for x in xs) / len(xs), 4)


def _rmse(xs: Sequence[float]) -> Optional[float]:
    if not xs:
        return None
    return round(math.sqrt(sum(x * x for x in xs) / len(xs)), 4)


def _median(xs: Sequence[float]) -> Optional[float]:
    if not xs:
        return None
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    if n % 2:
        return round(s[mid], 4)
    return round(0.5 * (s[mid - 1] + s[mid]), 4)


def _quantile(xs: Sequence[float], q: float) -> Optional[float]:
    if not xs:
        return None
    s = sorted(xs)
    if len(s) == 1:
        return round(s[0], 4)
    pos = (len(s) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    frac = pos - lo
    return round(s[lo] * (1.0 - frac) + s[hi] * frac, 4)


def _tails(xs: Sequence[float]) -> Dict[str, Any]:
    if not xs:
        return {
            "n": 0,
            "p90_abs": None,
            "p95_abs": None,
            "max_abs": None,
            "share_abs_gt_10": None,
            "share_abs_gt_15": None,
        }
    abs_xs = [abs(x) for x in xs]
    n = len(abs_xs)
    return {
        "n": n,
        "p90_abs": _quantile(abs_xs, 0.90),
        "p95_abs": _quantile(abs_xs, 0.95),
        "max_abs": round(max(abs_xs), 4),
        "share_abs_gt_10": round(sum(1 for x in abs_xs if x > 10) / n, 4),
        "share_abs_gt_15": round(sum(1 for x in abs_xs if x > 15) / n, 4),
    }


def _slice_stats(xs: Sequence[float]) -> Dict[str, Any]:
    return {
        "n": len(xs),
        "mean": _mean(xs),
        "median": _median(xs),
        "mae": _mae(xs),
        "rmse": _rmse(xs),
        "tails": _tails(xs),
    }


def matchup_family(row: Mapping[str, Any]) -> str:
    home_p4 = str(row.get("home_conference") or "") in P4_CONFS
    away_p4 = str(row.get("away_conference") or "") in P4_CONFS
    if home_p4 and away_p4:
        return "p4_vs_p4"
    if home_p4 or away_p4:
        return "p4_vs_g5"
    return "g5_vs_g5"


def load_recon_roster(season: int) -> Dict[str, Any]:
    path = DATA / f"cfb_week0_roster_snapshot_{season}.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8")).get("teams") or {}


def build_recon_universe(
    season: int,
    efficiency_by_code: Mapping[str, Any],
    recon_teams: Mapping[str, Any],
) -> EngineUniverse:
    """ESPN year-locked class/position + SDV efficiency. Recruiting stays 50."""
    from src.services.cfb_season_engine.loaders import load_packaged_team_priors
    from src.services.cfb_season_engine.conferences import load_conference_map

    priors = load_packaged_team_priors()
    teams = {}
    codes = set(efficiency_by_code) | set(recon_teams) | set(priors.get("teams") or {})
    for code in codes:
        recon = recon_teams.get(code) or {}
        prior = (priors.get("teams") or {}).get(code) or {}
        if recon:
            roster = build_roster_construction(
                code,
                {
                    "returning_production": recon.get("returning_production", 50),
                    "returning_snap_share": recon.get("returning_snap_share"),
                    "portal_in_value": 50.0,
                    "portal_out_value": 50.0,
                    "recruiting_class_score": 50.0,
                    "experience_index": recon.get("experience_index", 50),
                    "fidelity": "approximate",
                    "source": "hist_week0_espn_core_recruiting_unminted",
                },
            )
            groups = build_position_groups(
                code,
                {
                    "ol": 50.0,
                    "skill": 50.0,
                    "front_seven": 50.0,
                    "secondary": 50.0,
                    "special_teams": 50.0,
                    "fidelity": "placeholder",
                    "source": "hist_week0_units_unminted_no_recruiting",
                },
            )
            qb = build_qb_situation(
                code,
                {
                    "qb_class": recon.get("qb_class") or "unknown",
                    "qb_talent": 50.0,
                    "ol_support": 50.0,
                    "weapons_support": 50.0,
                    "fidelity": "approximate",
                    "source": "hist_week0_qb_class_only",
                },
                ol_grade=groups.ol,
                skill_grade=groups.skill,
            )
            state = compose_team_projection(
                code,
                roster,
                qb,
                groups,
                efficiency=efficiency_by_code.get(code),
                home_field=build_historical_proxy_state(
                    code, None, home_field_payload=prior.get("home_field")
                ).home_field,
            )
        else:
            state = build_historical_proxy_state(
                code,
                efficiency_by_code.get(code),
                home_field_payload=prior.get("home_field"),
            )
        teams[code] = state
    return EngineUniverse(
        season=season,
        teams=teams,
        schedule=[],
        conferences=load_conference_map(),
        player_hooks={},
        notes={
            "mode": RECON_PATH_NAME,
            "same_as_2026_live_path": False,
            "efficiency": f"sdv_cfb_ratings_{season-1}_not_sp_plus",
        },
    )


def project_rows(
    games,
    universes: Mapping[int, EngineUniverse],
    *,
    week_max: int,
) -> List[Dict[str, Any]]:
    rows = []
    spread_changed = 0
    for g in games:
        if g.week < 0 or g.week > week_max:
            continue
        uni = universes.get(g.season)
        if uni is None or g.home_code not in uni.teams or g.away_code not in uni.teams:
            continue
        proj = project_game(
            uni,
            home_team=g.home_code,
            away_team=g.away_code,
            week=g.week,
            season=g.season,
        )
        d = proj.drivers.get("matchup") or {}
        model_total = float(proj.expected_total)
        model_spread = float(proj.spread_home)
        t_neutral, infl = matchup_inflation_on_sum(
            model_total=model_total,
            home_diag=d.get("home_points_diag") or {},
            away_diag=d.get("away_points_diag") or {},
            league_ppg=float(P.LEAGUE_TEAM_PPG),
            points_clamp=P.EXPECTED_POINTS_CLAMP,
            st_nudge=float(d.get("st_total_nudge") or 0.0),
        )
        # Market baseline = close total as the "prediction"
        rows.append(
            {
                "season": g.season,
                "week": g.week,
                "home": g.home_code,
                "away": g.away_code,
                "model_total": model_total,
                "model_spread_home": model_spread,
                "close_total": float(g.close_total),
                "close_spread_home": float(g.close_spread_home),
                "actual_total": float(g.home_score + g.away_score),
                "matchup_inflation": infl,
                "total_neutral": t_neutral,
                "resid_vs_close": model_total - float(g.close_total),
                "resid_vs_actual": model_total - float(g.home_score + g.away_score),
                "home_conference": g.home_conference,
                "away_conference": g.away_conference,
                "matchup_family": matchup_family(
                    {
                        "home_conference": g.home_conference,
                        "away_conference": g.away_conference,
                    }
                ),
                "spread_bucket": mismatch_bucket(model_spread),
            }
        )
        # Sum-only candidate must not change spread. Check identity after even split.
        from src.services.cfb_season_engine.totals_guard_holdout import (
            margin_after_even_total_shift,
        )

        damp = apply_matchup_inflation_dampen(model_total, infl, 0.5)
        delta = damp - model_total
        m2 = margin_after_even_total_shift(
            home_exp=float(proj.expected_home_score),
            away_exp=float(proj.expected_away_score),
            delta_total=delta,
        )
        if abs(m2 - model_spread) > 1e-6:
            spread_changed += 1
    return rows, spread_changed


def summarize(rows: Sequence[Mapping[str, Any]], *, pred_key: str, truth_key: str) -> Dict[str, Any]:
    xs = [float(r[pred_key]) - float(r[truth_key]) for r in rows]
    return {
        "n": len(rows),
        "mean_bias": _mean(xs),
        "median_bias": _median(xs),
        "mae": _mae(xs),
        "rmse": _rmse(xs),
        "over_n": sum(1 for x in xs if x > 0),
        "under_n": sum(1 for x in xs if x < 0),
    }


def bucket_pred_total(v: float) -> str:
    if v < 48:
        return "<48"
    if v < 52:
        return "48-52"
    if v < 56:
        return "52-56"
    if v < 60:
        return "56-60"
    return ">=60"


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-dir", type=Path, default=ROOT / "data/cfb/raw/sdv")
    ap.add_argument("--open-2025", action="store_true")
    ap.add_argument("--freeze-path", type=Path, default=None)
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT / "data/ops/cfb-hist-livepath-totals-20260911.json",
    )
    args = ap.parse_args(argv)

    inv = reconstruction_inventory()
    assert_2025_sealed(open_2025=args.open_2025, freeze_path=args.freeze_path)

    seasons = [2023, 2024]
    if args.open_2025:
        seasons.append(2025)

    games, load_meta = load_historical_games(seasons, cache_dir=args.cache_dir)
    recon_available = {y: bool(load_recon_roster(y)) for y in seasons}

    universes: Dict[int, EngineUniverse] = {}
    path_used = {}
    for year in seasons:
        eff = ratings_to_efficiency_map(year - 1, cache_dir=args.cache_dir)
        recon = load_recon_roster(year)
        if recon:
            universes[year] = build_recon_universe(year, eff, recon)
            path_used[year] = RECON_PATH_NAME
        else:
            universes[year] = build_historical_proxy_universe(year, eff)
            path_used[year] = "hist_cal_league_avg_fallback_no_recon_pack"

    rows, spread_changed = project_rows(games, universes, week_max=PRIMARY_WEEK_MAX)
    fit_rows = filter_fit_rows(rows, week_max=PRIMARY_WEEK_MAX)
    assert not any(int(r["season"]) == 2025 for r in fit_rows)

    infl = [float(r["matchup_inflation"]) for r in fit_rows]
    mean_infl = _mean(infl) or 0.0
    inflation_reproduced = mean_infl >= INFLATION_REPRODUCE_MIN

    # Candidates computed on FIT rows only. λ not used on 2025 in this run
    # unless freeze exists (and we still refuse to *choose* λ from 2025).
    lam = 1.0
    offset = 0.0
    fitted = False
    if inflation_reproduced:
        lam = fit_lambda_ols(fit_rows)
        offset = fit_level_offset(fit_rows)
        fitted = True
        # Freeze from 2023–24 only.
        freeze = {
            "frozen_from_seasons": [2023, 2024],
            "week_max": PRIMARY_WEEK_MAX,
            "path": path_used,
            "lambda_b": lam,
            "level_offset_a": offset,
            "mean_matchup_inflation_fit": mean_infl,
            "same_as_2026_live_path": False,
        }
        freeze_path = (
            args.freeze_path
            or ROOT / "data/ops/cfb-totals-guard-freeze-2023-2024.json"
        )
        freeze_path.write_text(json.dumps(freeze, indent=2) + "\n", encoding="utf-8")
    else:
        freeze_path = None

    def with_preds(src: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        out = []
        for r in src:
            t0 = float(r["model_total"])
            infl_i = float(r["matchup_inflation"])
            out.append(
                {
                    **dict(r),
                    "pred_frozen": t0,
                    "pred_neutralized": float(r["total_neutral"]),
                    "pred_dampen_b": apply_matchup_inflation_dampen(t0, infl_i, lam)
                    if fitted
                    else None,
                    "pred_offset_a": apply_level_offset(t0, offset) if fitted else None,
                    "pred_market": float(r["close_total"]),
                }
            )
        return out

    labeled = with_preds(fit_rows)
    comparisons = {}
    for name, key in (
        ("frozen", "pred_frozen"),
        ("matchup_neutralized", "pred_neutralized"),
        ("sum_only_dampen_b", "pred_dampen_b"),
        ("level_offset_a", "pred_offset_a"),
        ("market_baseline", "pred_market"),
    ):
        use = [r for r in labeled if r.get(key) is not None]
        if name == "market_baseline":
            comparisons[name] = {
                "vs_close": summarize(use, pred_key="close_total", truth_key="close_total"),
                "vs_actual": summarize(use, pred_key="close_total", truth_key="actual_total"),
                "note": "Market vs itself on close is identically 0; vs actual is the book.",
            }
        else:
            # rewrite summarize to use pred vs close/actual
            close_xs = [float(r[key]) - float(r["close_total"]) for r in use]
            act_xs = [float(r[key]) - float(r["actual_total"]) for r in use]
            frozen_close = comparisons.get("frozen", {}).get("vs_close") or {}
            frozen_act = comparisons.get("frozen", {}).get("vs_actual") or {}
            comparisons[name] = {
                "n": len(use),
                "vs_close": {
                    "mean_bias": _mean(close_xs),
                    "median_bias": _median(close_xs),
                    "mae": _mae(close_xs),
                    "rmse": _rmse(close_xs),
                    "over_n": sum(1 for x in close_xs if x > 0),
                    "under_n": sum(1 for x in close_xs if x < 0),
                    "tails": _tails(close_xs),
                },
                "vs_actual": {
                    "mean_bias": _mean(act_xs),
                    "median_bias": _median(act_xs),
                    "mae": _mae(act_xs),
                    "rmse": _rmse(act_xs),
                    "over_n": sum(1 for x in act_xs if x > 0),
                    "under_n": sum(1 for x in act_xs if x < 0),
                    "tails": _tails(act_xs),
                },
                "delta_vs_frozen": {
                    "mae_vs_close": (
                        None
                        if _mae(close_xs) is None or frozen_close.get("mae") is None
                        else round(float(_mae(close_xs)) - float(frozen_close["mae"]), 4)
                    ),
                    "rmse_vs_close": (
                        None
                        if _rmse(close_xs) is None or frozen_close.get("rmse") is None
                        else round(float(_rmse(close_xs)) - float(frozen_close["rmse"]), 4)
                    ),
                    "mean_bias_vs_close": (
                        None
                        if _mean(close_xs) is None or frozen_close.get("mean_bias") is None
                        else round(float(_mean(close_xs)) - float(frozen_close["mean_bias"]), 4)
                    ),
                    "mae_vs_actual": (
                        None
                        if _mae(act_xs) is None or frozen_act.get("mae") is None
                        else round(float(_mae(act_xs)) - float(frozen_act["mae"]), 4)
                    ),
                }
                if name != "frozen"
                else {"note": "baseline"},
            }

    by_week = defaultdict(list)
    by_bucket = defaultdict(list)
    by_family = defaultdict(list)
    by_spread = defaultdict(list)
    for r in labeled:
        by_week[f"W{r['week']}"].append(r["resid_vs_close"])
        by_bucket[bucket_pred_total(float(r["model_total"]))].append(r["resid_vs_close"])
        by_family[str(r.get("matchup_family") or "unknown")].append(r["resid_vs_close"])
        by_spread[str(r.get("spread_bucket") or "unknown")].append(r["resid_vs_close"])

    payload = {
        "ok": True,
        "research_only": True,
        "production_model_changed": False,
        "kill_switch": "CFB_EDGE_BOARD_PUBLIC_ENABLED=false",
        "inventory": inv,
        "path_used": path_used,
        "recon_packs_present": recon_available,
        "seasons_scored": seasons,
        "2025_opened": bool(args.open_2025),
        "n_fit_rows": len(fit_rows),
        "mean_matchup_inflation_fit": mean_infl,
        "inflation_reproduced_vs_2026": inflation_reproduced,
        "inflation_reproduce_threshold": INFLATION_REPRODUCE_MIN,
        "lambda_fitted": fitted,
        "lambda_b": lam if fitted else None,
        "level_offset_a": offset if fitted else None,
        "freeze_path": str(freeze_path) if freeze_path else None,
        "spread_identity_violations": spread_changed,
        "spread_unchanged_by_sum_only": spread_changed == 0,
        "load_meta": {
            "seasons": load_meta.get("seasons"),
            "mapped_games": load_meta.get("mapped_games"),
        },
        "comparisons_fit_2023_2024_w0_2": comparisons,
        "slices_frozen_vs_close": {
            "week": {k: _slice_stats(v) for k, v in by_week.items()},
            "pred_total_bucket": {k: _slice_stats(v) for k, v in by_bucket.items()},
            "matchup_family": {k: _slice_stats(v) for k, v in by_family.items()},
            "spread_bucket": {k: _slice_stats(v) for k, v in by_spread.items()},
            "notes": {
                "matchup_family": (
                    "P4 = SEC/B1G/ACC/Big 12 on the packaged 2026 affiliation map. "
                    "2023 Pac-12 / 2024 realignment games are labeled by that map, "
                    "not contemporaneous conference names."
                ),
                "spread_bucket": (
                    f"peer |model_spread|<{PEER_ABS_SPREAD_LT}; "
                    f"cupcake |model_spread|>={CUPCAKE_ABS_SPREAD_GE}."
                ),
            },
        },
        "stop": (not inflation_reproduced) or bool(inv.get("stop_same_path")),
        "stop_reason": (
            "2026-style +8 to +10 matchup inflation did not reproduce on the "
            "reconstructable 2023–24 path, and/or the path is not the 2026 "
            "live SP++roster stack. λ was not fit. 2025 remains sealed."
            if not inflation_reproduced
            else inv.get("stop_reason")
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in (
        "n_fit_rows",
        "mean_matchup_inflation_fit",
        "inflation_reproduced_vs_2026",
        "lambda_fitted",
        "stop",
        "path_used",
        "spread_unchanged_by_sum_only",
        "comparisons_fit_2023_2024_w0_2",
    )}, indent=2))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
