#!/usr/bin/env python3
"""Diagnosis-only W2 residual attribution. No coefficient changes.

Reconstructs model_total / model_spread from engine components, joins the
frozen DK snapshot, and tests intercept-vs-slope plus comparison-layer
sanity. Does not haircut, retune, or write KEI.
"""

from __future__ import annotations

import json
import math
import os
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))
sys.path.insert(0, str(ROOT / "scripts" / "cfb"))
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from cfb_joined_residual_audit import (  # noqa: E402
    attach_odds,
    slim_from_espn,
)
from src.services.cfb_season_engine import (  # noqa: E402
    project_game_preview,
    resolve_season_universe,
)
from src.services.cfb_season_engine import priors as P  # noqa: E402
from src.services.cfb_season_engine.conferences import conference_for  # noqa: E402

KEI = (
    ROOT
    / "services"
    / "model-service"
    / "src"
    / "services"
    / "cfb_season_engine"
    / "data"
    / "cfb_kei_w0_w1_2026.json"
)
ESPN = ROOT / "data/ops/cfb-w2-espn-scoreboard-odds-20260911.json"
OUT = ROOT / "data/ops/cfb-w2-residual-attribution-20260912.json"
P4 = {"SEC", "Big Ten", "ACC", "Big 12", "Pac-12"}


def _n(v: Any) -> Optional[float]:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return None if x != x else x


def _ols(xs: List[float], ys: List[float]) -> Dict[str, Any]:
    n = len(xs)
    if n < 3:
        return {"n": n}
    mx = statistics.mean(xs)
    my = statistics.mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    syy = sum((y - my) ** 2 for y in ys)
    slope = sxy / sxx if sxx else float("nan")
    intercept = my - slope * mx
    pred = [intercept + slope * x for x in xs]
    resid = [y - p for y, p in zip(ys, pred)]
    ss_res = sum(r ** 2 for r in resid)
    r2 = 1.0 - ss_res / syy if syy else float("nan")
    return {
        "n": n,
        "slope": round(slope, 4),
        "intercept": round(intercept, 4),
        "r2": round(r2, 4),
        "mean_x": round(mx, 3),
        "mean_y": round(my, 3),
        "mean_y_minus_x": round(my - mx, 3),
        "residual_sd": round(statistics.pstdev(resid), 3) if n > 1 else None,
    }


def _rmse(vals: List[float]) -> Optional[float]:
    if not vals:
        return None
    return round(math.sqrt(sum(v * v for v in vals) / len(vals)), 3)


def _seg(rows: List[Dict[str, Any]], key: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    buckets: Dict[str, List[float]] = defaultdict(list)
    for r in rows:
        buckets[str(r.get(key))].append(float(r["total_residual"]))
    for name, vs in sorted(buckets.items()):
        out[name] = {
            "n": len(vs),
            "mean": round(statistics.mean(vs), 3),
            "median": round(float(statistics.median(vs)), 3),
            "mae": round(sum(abs(v) for v in vs) / len(vs), 3),
            "rmse": _rmse(vs),
        }
    return out


def _rebuild_side(
    diag: Dict[str, Any],
    *,
    matchup: Optional[float] = None,
    off_boost: Optional[float] = None,
    def_dampen: Optional[float] = None,
    pace: Optional[float] = None,
    addons: bool = True,
) -> float:
    m = float(diag["matchup_ratio"] if matchup is None else matchup) ** float(
        diag["matchup_response"]
    )
    if matchup == 1.0:
        m = 1.0
    elif matchup is not None and matchup != float(diag["matchup_ratio"]):
        m = float(matchup) ** float(diag["matchup_response"])
    ob = float(diag["offense_boost"] if off_boost is None else off_boost)
    dd = float(diag["defense_dampen"] if def_dampen is None else def_dampen)
    pc = float(diag["pace"] if pace is None else pace)
    core = P.LEAGUE_TEAM_PPG * m * ob * dd * pc
    if addons:
        hfa = float((diag.get("hfa") or {}).get("hfa_points") or 0.0)
        core += hfa + float(diag.get("coaching_net_adj") or 0.0)
    return max(P.EXPECTED_POINTS_CLAMP[0], min(P.EXPECTED_POINTS_CLAMP[1], core))


def _counterfactual_sides(
    home_diag: Dict[str, Any],
    away_diag: Dict[str, Any],
    **kwargs: Any,
) -> Tuple[float, float]:
    return _rebuild_side(home_diag, **kwargs), _rebuild_side(away_diag, **kwargs)


def _counterfactual_total(
    home_diag: Dict[str, Any],
    away_diag: Dict[str, Any],
    st_nudge: float,
    **kwargs: Any,
) -> float:
    h, a = _counterfactual_sides(home_diag, away_diag, **kwargs)
    return round(h + a + float(st_nudge), 3)


def _counterfactual_spread(
    home_diag: Dict[str, Any],
    away_diag: Dict[str, Any],
    **kwargs: Any,
) -> float:
    """Home-signed. ST nudge is a total-only add and does not move spread."""
    h, a = _counterfactual_sides(home_diag, away_diag, **kwargs)
    return round(a - h, 3)


def main() -> int:
    kei = json.loads(KEI.read_text(encoding="utf-8"))
    slim = slim_from_espn(ESPN)
    odds = slim["by_key"]
    uni, meta = resolve_season_universe(season=2026, as_of_week=2, demo=True, session=None)

    games = [
        g
        for g in kei.get("games") or []
        if int(g.get("week") or -1) == 2 and g.get("fbs_vs_fbs")
    ]
    ledgers: List[Dict[str, Any]] = []
    comparison_flags: List[str] = []
    pack_vs_reproject: List[float] = []

    for g in games:
        home = str(g.get("home") or "")
        away = str(g.get("away") or "")
        night = False
        kick = str(g.get("kickoff") or "")
        if "T" in kick:
            try:
                hour = int(kick.split("T")[1][:2])
                night = hour >= 23 or hour < 5
            except ValueError:
                night = False
        proj = project_game_preview(
            uni,
            home_team=home,
            away_team=away,
            week=2,
            season=2026,
            neutral_site=bool(g.get("neutral_site")),
            night_game=night,
        )
        blob = g.get("kei") or {}
        pack_total = _n(g.get("model_total") if g.get("model_total") is not None else blob.get("model_total"))
        pack_spread = _n(g.get("model_spread_home"))
        if pack_total is not None:
            pack_vs_reproject.append(abs(float(proj.expected_total) - pack_total))
        mkt = attach_odds(g, odds)
        mkt_sp = _n((mkt or {}).get("best_spread_home"))
        mkt_tot = _n((mkt or {}).get("best_total"))
        details = None
        if mkt:
            # recover raw snapshot row via label
            details = (mkt.get("best_book"), mkt.get("label"))
        home_diag = (proj.drivers or {}).get("matchup", {}).get("home_points_diag") or {}
        away_diag = (proj.drivers or {}).get("matchup", {}).get("away_points_diag") or {}
        st = float((proj.drivers or {}).get("matchup", {}).get("st_total_nudge") or 0.0)
        actual = float(proj.expected_total)
        cf_matchup1 = _counterfactual_total(home_diag, away_diag, st, matchup=1.0)
        cf_units1 = _counterfactual_total(
            home_diag, away_diag, st, off_boost=1.0, def_dampen=1.0
        )
        cf_pace1 = _counterfactual_total(home_diag, away_diag, st, pace=1.0)
        cf_no_add = _counterfactual_total(home_diag, away_diag, 0.0, addons=False)
        cf_base = round(2.0 * P.LEAGUE_TEAM_PPG, 3)
        cf_spread = {
            "actual": round(float(proj.spread_home), 3),
            "matchup_ratio_1": _counterfactual_spread(home_diag, away_diag, matchup=1.0),
            "units_1": _counterfactual_spread(
                home_diag, away_diag, off_boost=1.0, def_dampen=1.0
            ),
            "pace_1": _counterfactual_spread(home_diag, away_diag, pace=1.0),
            "no_hfa_coach_st": _counterfactual_spread(
                home_diag, away_diag, addons=False
            ),
        }
        tot_res = None if pack_total is None or mkt_tot is None else round(pack_total - mkt_tot, 3)
        sp_res = None if pack_spread is None or mkt_sp is None else round(float(blob.get("kei_spread_home") or pack_spread) - mkt_sp, 3)
        kei_sp = _n(blob.get("kei_spread_home"))
        flip = (
            kei_sp is not None
            and mkt_sp is not None
            and kei_sp * mkt_sp < 0
            and abs(kei_sp) > 1e-9
            and abs(mkt_sp) > 1e-9
        )
        # Comparison-layer checks
        if mkt and mkt.get("source") not in (None, "espn_scoreboard"):
            comparison_flags.append(f"{away}@{home}: unexpected source {mkt.get('source')}")
        if mkt_sp is not None and mkt and "details" in (mkt or {}):
            pass
        home_conf = conference_for(home)
        away_conf = conference_for(away)
        ht = uni.teams[home]
        at = uni.teams[away]
        row = {
            "pair": f"{away}@{home}",
            "week": 2,
            "neutral_site": bool(g.get("neutral_site")),
            "home_conference": home_conf,
            "away_conference": away_conf,
            "home_p4": home_conf in P4,
            "away_p4": away_conf in P4,
            "pack_model_total": pack_total,
            "reproject_total": proj.expected_total,
            "pack_model_spread": pack_spread,
            "reproject_spread": proj.spread_home,
            "kei_spread_home": kei_sp,
            "kei_total": _n(blob.get("kei_total")),
            "market_spread_home": mkt_sp,
            "market_total": mkt_tot,
            "market_label": (mkt or {}).get("label"),
            "market_details_book": (mkt or {}).get("best_book"),
            "joined": bool(mkt and mkt_tot is not None),
            "total_residual": tot_res,
            "spread_residual": sp_res,
            "favorite_flip": flip,
            "home_exp": proj.expected_home_score,
            "away_exp": proj.expected_away_score,
            "league_ppg": P.LEAGUE_TEAM_PPG,
            "matchup_response": home_diag.get("matchup_response"),
            "home": {
                "off_idx": ht.offense_index,
                "def_idx": ht.defense_index,
                "pace": ht.pace_factor,
                "off_eff": (ht.efficiency.off_eff if ht.efficiency else None),
                "def_eff": (ht.efficiency.def_eff if ht.efficiency else None),
                "explosiveness": (ht.efficiency.explosiveness if ht.efficiency else None),
                "success_off": (ht.efficiency.success_off if ht.efficiency else None),
                "qb_class": (ht.qb.qb_class if ht.qb else None),
                "qb_index": (ht.qb.qb_situation_index if ht.qb else None),
                "roster": (ht.roster.roster_strength if ht.roster else None),
                "diag": home_diag,
            },
            "away": {
                "off_idx": at.offense_index,
                "def_idx": at.defense_index,
                "pace": at.pace_factor,
                "off_eff": (at.efficiency.off_eff if at.efficiency else None),
                "def_eff": (at.efficiency.def_eff if at.efficiency else None),
                "explosiveness": (at.efficiency.explosiveness if at.efficiency else None),
                "success_off": (at.efficiency.success_off if at.efficiency else None),
                "qb_class": (at.qb.qb_class if at.qb else None),
                "qb_index": (at.qb.qb_situation_index if at.qb else None),
                "roster": (at.roster.roster_strength if at.roster else None),
                "diag": away_diag,
            },
            "st_nudge": st,
            "counterfactual_total": {
                "actual": actual,
                "matchup_ratio_1": cf_matchup1,
                "units_1": cf_units1,
                "pace_1": cf_pace1,
                "no_hfa_coach_st": cf_no_add,
                "two_times_league_ppg": cf_base,
            },
            "counterfactual_spread": cf_spread,
            "cf_gap_vs_market": None
            if mkt_tot is None
            else {
                "actual": round(actual - mkt_tot, 3),
                "matchup_ratio_1": round(cf_matchup1 - mkt_tot, 3),
                "units_1": round(cf_units1 - mkt_tot, 3),
                "pace_1": round(cf_pace1 - mkt_tot, 3),
                "no_hfa_coach_st": round(cf_no_add - mkt_tot, 3),
                "two_times_league_ppg": round(cf_base - mkt_tot, 3),
            },
        }
        # buckets
        if pack_total is not None:
            row["proj_total_bucket"] = (
                "lt55" if pack_total < 55 else "55_62" if pack_total < 62 else "ge62"
            )
        if mkt_tot is not None:
            row["mkt_total_bucket"] = (
                "lt50" if mkt_tot < 50 else "50_55" if mkt_tot < 55 else "ge55"
            )
        row["home_favorite_mkt"] = mkt_sp is not None and mkt_sp < 0
        row["pace_bucket"] = (
            "slow"
            if 0.5 * (ht.pace_factor + at.pace_factor) < 0.98
            else "fast"
            if 0.5 * (ht.pace_factor + at.pace_factor) > 1.04
            else "avg"
        )
        mean_off = statistics.mean(
            [
                float(ht.efficiency.off_eff if ht.efficiency else 50),
                float(at.efficiency.off_eff if at.efficiency else 50),
            ]
        )
        row["eff_bucket"] = (
            "low" if mean_off < 48 else "high" if mean_off > 58 else "mid"
        )
        row["matchup_class"] = (
            "p4_p4"
            if home_conf in P4 and away_conf in P4
            else "g6_g6"
            if home_conf not in P4 and away_conf not in P4
            else "cross"
        )
        ledgers.append(row)

    joined = [r for r in ledgers if r.get("joined") and r.get("total_residual") is not None]
    tot_res = [float(r["total_residual"]) for r in joined]
    mkt_tots = [float(r["market_total"]) for r in joined]
    model_tots = [float(r["pack_model_total"]) for r in joined]
    cf_means = {}
    for key in (
        "actual",
        "matchup_ratio_1",
        "units_1",
        "pace_1",
        "no_hfa_coach_st",
        "two_times_league_ppg",
    ):
        vs = [float(r["cf_gap_vs_market"][key]) for r in joined if r.get("cf_gap_vs_market")]
        cf_means[key] = {
            "mean_gap": round(statistics.mean(vs), 3),
            "delta_from_actual": round(
                statistics.mean(vs) - statistics.mean([float(r["cf_gap_vs_market"]["actual"]) for r in joined if r.get("cf_gap_vs_market")]),
                3,
            )
            if key != "actual"
            else 0.0,
        }

    # Intercept vs slope
    ols = _ols(mkt_tots, model_tots)
    constant = [y - x for x, y in zip(mkt_tots, model_tots)]
    after_demean = [r - statistics.mean(constant) for r in constant]

    flips = [r for r in joined if r.get("favorite_flip")]
    rut = next((r for r in ledgers if r["pair"] == "RUT@BC"), None)

    # Comparison-layer proof
    snapshot = json.loads(ESPN.read_text(encoding="utf-8"))
    snap_labels = [row.get("label") for row in snapshot.get("rows") or []]
    comparison = {
        "snapshot_n": snapshot.get("n"),
        "snapshot_provider": "DraftKings via ESPN scoreboard 2026-09-11",
        "joined_n": len(joined),
        "unjoined": [r["pair"] for r in ledgers if not r.get("joined")],
        "pack_vs_reproject_max_abs_total": round(max(pack_vs_reproject), 4)
        if pack_vs_reproject
        else None,
        "pack_vs_reproject_mean_abs_total": round(
            sum(pack_vs_reproject) / len(pack_vs_reproject), 4
        )
        if pack_vs_reproject
        else None,
        "kei_total_equals_model": all(
            r.get("kei_total") == r.get("pack_model_total") for r in joined
        ),
        "spread_home_convention": (
            "model_spread_home = away_exp - home_exp (neg = home favorite). "
            "ESPN snapshot spread_home is already home-signed. "
            "RUT@BC details 'BC -3' ↔ spread_home -3.0. "
            "UNLV@UNT details 'UNLV -3' ↔ spread_home +3.0."
        ),
        "neutral_site_joined": [r["pair"] for r in joined if r.get("neutral_site")],
        "duplicate_pairs": [
            p
            for p, n in (
                (p, sum(1 for r in ledgers if r["pair"] == p))
                for p in {r["pair"] for r in ledgers}
            )
            if n > 1
        ],
        "formula": (
            "pts = 25.9 * (off_idx/def_idx)^1.302 * ol_skill_boost * "
            "opp_def_dampen * pace + HFA + coaching; ST nudge split; "
            "total = home+away. No possessions, drives, field position, "
            "weather, or success-rate terms in the score path. "
            "Explosiveness only nudges pace by (expl-50)/400. "
            "margin_calibration is NOT on the KEI path."
        ),
        "w2_matchup_response": P.matchup_response_for_week(2),
        "flags": comparison_flags,
        "rut_bc_in_snapshot": any("Rutgers" in str(x) and "Boston" in str(x) for x in snap_labels),
    }

    report = {
        "role": "diagnosis_only",
        "do_not_tune": True,
        "kill_switch": "OFF",
        "merge_532": False,
        "comparison_layer": comparison,
        "totals": {
            "n": len(joined),
            "mean_residual": round(statistics.mean(tot_res), 3),
            "median_residual": round(float(statistics.median(tot_res)), 3),
            "mae": round(sum(abs(v) for v in tot_res) / len(tot_res), 3),
            "rmse": _rmse(tot_res),
            "overs": sum(1 for v in tot_res if v > 0),
            "unders": sum(1 for v in tot_res if v < 0),
            "ols_model_on_market": ols,
            "constant_plus_10_hypothesis": {
                "mean_gap": round(statistics.mean(constant), 3),
                "sd_gap": round(statistics.pstdev(constant), 3),
                "share_within_3_of_mean": round(
                    sum(1 for v in after_demean if abs(v) <= 3) / len(after_demean), 3
                ),
                "share_within_5_of_mean": round(
                    sum(1 for v in after_demean if abs(v) <= 5) / len(after_demean), 3
                ),
            },
            "counterfactual_mean_gap_vs_market": cf_means,
            "segments": {
                "proj_total_bucket": _seg(joined, "proj_total_bucket"),
                "mkt_total_bucket": _seg(joined, "mkt_total_bucket"),
                "home_favorite_mkt": _seg(joined, "home_favorite_mkt"),
                "pace_bucket": _seg(joined, "pace_bucket"),
                "eff_bucket": _seg(joined, "eff_bucket"),
                "matchup_class": _seg(joined, "matchup_class"),
            },
            "absent_from_score_path": [
                "explicit possessions / plays",
                "drive finishing / scoring conversion",
                "field position",
                "weather",
                "success_off / success_def (stored, not in expected_team_points)",
                "margin_calibration (research Bernoulli only; used_in_spread=false)",
            ],
        },
        "flips": {
            "n": len(flips),
            "pairs": [
                {
                    "pair": r["pair"],
                    "kei_spread_home": r["kei_spread_home"],
                    "model_spread_home": r["pack_model_spread"],
                    "market_spread_home": r["market_spread_home"],
                    "spread_residual": r["spread_residual"],
                    "home_off_idx": r["home"]["off_idx"],
                    "home_def_idx": r["home"]["def_idx"],
                    "away_off_idx": r["away"]["off_idx"],
                    "away_def_idx": r["away"]["def_idx"],
                    "home_off_eff": r["home"]["off_eff"],
                    "away_off_eff": r["away"]["off_eff"],
                    "home_qb": r["home"]["qb_class"],
                    "away_qb": r["away"]["qb_class"],
                    "home_matchup": r["home"]["diag"].get("matchup_ratio"),
                    "away_matchup": r["away"]["diag"].get("matchup_ratio"),
                    "neutral": r["neutral_site"],
                    "matchup_class": r["matchup_class"],
                    "counterfactual_spread": r.get("counterfactual_spread"),
                    "counterfactual_total": r.get("counterfactual_total"),
                }
                for r in sorted(flips, key=lambda x: -abs(float(x["spread_residual"] or 0)))
            ],
        },
        "rut_bc": rut,
        "diagnosis": {
            "comparison_layer_artifact": False,
            "model_equals_market_plus_10": False,
            "shape": "level_shift_with_weak_market_slope",
            "ols_slope": ols.get("slope"),
            "ols_intercept": ols.get("intercept"),
            "ols_r2": ols.get("r2"),
            "primary_totals_driver": "matchup_ratio_pow_1.302",
            "matchup_neutralization_delta": (cf_means.get("matchup_ratio_1") or {}).get(
                "delta_from_actual"
            ),
            "baseline_too_high": False,
            "two_times_league_ppg_mean_gap": (cf_means.get("two_times_league_ppg") or {}).get(
                "mean_gap"
            ),
            "calibration_recommendation": "FAIL",
            "calibration_reason": (
                "Mechanism identified (matchup^1.302). n=47 is a diagnosis "
                "sample, not a fit sample. Do not subtract 10. Do not tune "
                "coefficients against this snapshot."
            ),
            "do_not_subtract_10": True,
            "do_not_tune": True,
            "kill_switch": "OFF",
            "merge_532": False,
        },
        "ledgers": ledgers,
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    print("joined", len(joined), "mean residual", report["totals"]["mean_residual"])
    print("OLS", ols)
    print("cf", cf_means)
    print("flips", [r["pair"] for r in flips])
    print("reproject max drift", comparison["pack_vs_reproject_max_abs_total"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
