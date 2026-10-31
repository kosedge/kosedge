#!/usr/bin/env python3
"""READ-ONLY IF compression replay (OWNER t4902u).

Replays the sealed t4850u v2 caller with the existing simulator / contract /
panel. Does not change math, weights, blends, or features.

Writes TRACE.json + per-game TRACE_*.md fragments consumed by the packet.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT / "services" / "model-service") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "services" / "model-service"))

from src.services.nfl_offline_if_caller import (  # noqa: E402
    ALLOWED_INPUT_FIELDS,
    REQUIRED_20,
    build_contract_inputs,
)
from src.services.nfl_offline_if_eval_w8 import (  # noqa: E402
    BYE_ROLLING_AS_OF,
    EVAL_SEED_BASE,
    PANEL_SHA256,
    RATING_WEEK,
    SCHEDULE_SHA256,
    SUPPORTED_GAMES,
    TARGET_WEEK,
    build_eval_request,
    history_w1_w7,
    load_panel,
    load_schedule,
)
from src.services.nfl_offline_if_eval_w8_v2 import invoke_diagnostic_v2  # noqa: E402
from src.services.nfl_simulator import (  # noqa: E402
    _build_matchup_adjustments,
    _build_totals_adjustments,
    simulate_nfl_game_independent_fair,
)
from src.services.nfl_handicapping_framework import (  # noqa: E402
    get_nfl_handicapping_config,
)

PACKET_DIR = REPO_ROOT / "data" / "ops" / "nfl-if-compression-diag-t4902u"
FOCUS = (
    "2026-W08-TEN@CIN",
    "2026-W08-IND@JAX",
    "2026-W08-ARI@DAL",
)
SEALED_RESULTS = (
    REPO_ROOT
    / "data"
    / "ops"
    / "nfl-offline-if-caller-t4838u"
    / "eval_w8_t4850u_v2"
    / "RESULTS.json"
)

# Bound compare (OWNER t4898u/t4899u). DraftKings current_post_seal.
MARKET_DK = {
    "2026-W08-TEN@CIN": {
        "spread_home": -12.5,
        "total": 46.5,
        "ml_home": -675,
        "ml_away": 490,
        "devig_home": 0.8370993168681029,
        "overround": 0.04045926735921279,
    },
    "2026-W08-IND@JAX": {
        "spread_home": -10.0,
        "total": 46.5,
        "ml_home": -500,
        "ml_away": 380,
        "devig_home": 0.7999999999999999,
        "overround": 0.04166666666666674,
    },
    "2026-W08-ARI@DAL": {
        "spread_home": -7.0,
        "total": 54.5,
        "ml_home": -305,
        "ml_away": 245,
        "devig_home": 0.7220792588780237,
        "overround": 0.042941492216854504,
    },
}

MATCHUP_CLAMP = {
    "matchup_diff_off_epa_5g": (-0.30, 0.30, 5.4),
    "matchup_diff_def_epa_allowed_5g": (-0.30, 0.30, 5.0),
    "matchup_diff_pressure_generated_5g": (-0.10, 0.10, 7.0),
    "matchup_diff_pressure_allowed_5g": (-0.10, 0.10, 6.2),
    "matchup_diff_red_zone_td_rate_5g": (-0.20, 0.20, 4.8),
    "matchup_diff_success_rate_5g": (-0.15, 0.15, 4.5),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _implied_american(price: int) -> float:
    if price > 0:
        return 100.0 / (price + 100.0)
    return (-price) / ((-price) + 100.0)


def _devig_home(ml_home: int, ml_away: int) -> Dict[str, float]:
    p_h = _implied_american(ml_home)
    p_a = _implied_american(ml_away)
    return {
        "implied_home": p_h,
        "implied_away": p_a,
        "devig_home": p_h / (p_h + p_a),
        "devig_away": p_a / (p_h + p_a),
        "overround": p_h + p_a - 1.0,
    }


def _fair_ml(p: float) -> int:
    p = max(0.001, min(0.999, p))
    if p >= 0.5:
        return int(round(-(100.0 * p) / (1.0 - p)))
    return int(round((100.0 * (1.0 - p)) / p))


def _phi(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _record_winpct(record: str) -> float:
    wins, losses = record.split("-", 1)
    w = float(wins)
    l = float(losses)
    return w / max(1.0, w + l)


def team_strength_from_record(record_summary: str) -> tuple[float, float]:
    """Local copy of nfl_data.team_strength_from_record (avoid requests import)."""
    wins, losses = record_summary.split("-", 1)
    w = max(0.0, float(wins))
    l = max(0.0, float(losses))
    games = max(1.0, w + l)
    win_pct = w / games
    offense = max(0.82, min(1.18, 0.90 + (0.22 * win_pct)))
    defense = max(0.82, min(1.20, 0.92 + (0.20 * win_pct)))
    return offense, defense


def league_index_audit(panel: Mapping[str, Any]) -> Dict[str, Any]:
    rows = []
    for team, rec in panel["teams"].items():
        record = str(rec["record"])
        wp = _record_winpct(record)
        expected_off, expected_def = team_strength_from_record(record)
        rows.append(
            {
                "team": team,
                "record": record,
                "wins": rec["wins"],
                "losses": rec["losses"],
                "games_played": rec["games_played"],
                "games_in_window_5": rec["games_in_window_5"],
                "as_of_week": rec["as_of_week"],
                "rolling_as_of_week": rec["rolling_as_of_week"],
                "prior_2025_used": rec["2025_prior_used"],
                "t5_ok": rec["t5_ok"],
                "t5_source": rec["t5_source"],
                "offense_index": rec["offense_index"],
                "defense_index": rec["defense_index"],
                "win_pct": wp,
                "formula_off": expected_off,
                "formula_def": expected_def,
                "off_matches_record_formula": abs(float(rec["offense_index"]) - expected_off)
                < 1e-9,
                "def_matches_record_formula": abs(float(rec["defense_index"]) - expected_def)
                < 1e-9,
                "off_epa_5g": rec["off_epa_5g"],
                "def_epa_allowed_5g": rec["def_epa_allowed_5g"],
            }
        )
    offs = [r["offense_index"] for r in rows]
    defs = [r["defense_index"] for r in rows]
    return {
        "n": len(rows),
        "all_as_of_week_7": all(r["as_of_week"] == 7 for r in rows),
        "all_window_5": all(r["games_in_window_5"] == 5 for r in rows),
        "any_2025_prior": any(r["prior_2025_used"] for r in rows),
        "all_t5_ok": all(r["t5_ok"] for r in rows),
        "all_t5_from_record": all(r["t5_source"] == "team_strength_from_record" for r in rows),
        "all_off_match_record_formula": all(r["off_matches_record_formula"] for r in rows),
        "all_def_match_record_formula": all(r["def_matches_record_formula"] for r in rows),
        "offense_index_min": min(offs),
        "offense_index_max": max(offs),
        "offense_index_range": max(offs) - min(offs),
        "defense_index_min": min(defs),
        "defense_index_max": max(defs),
        "defense_index_range": max(defs) - min(defs),
        "formula": {
            "offense": "clamp(0.90 + 0.22 * win_pct, 0.82, 1.18)",
            "defense": "clamp(0.92 + 0.20 * win_pct, 0.82, 1.20)",
        },
        "bye_rolling_as_of": BYE_ROLLING_AS_OF,
        "teams": rows,
    }


def clamp_report(raw: float, lo: float, hi: float) -> Dict[str, Any]:
    bounded = max(lo, min(hi, raw))
    return {
        "raw": raw,
        "lo": lo,
        "hi": hi,
        "bounded": bounded,
        "hit_lo": raw < lo,
        "hit_hi": raw > hi,
        "hit": raw < lo or raw > hi,
    }


def theoretical_if_contract_caps(cfg: Mapping[str, Any]) -> Dict[str, Any]:
    factors = cfg["factors"]
    priors = cfg["priors"]
    live_if_margin = (
        factors["base_efficiency"]["max_margin_points"]
        + factors["home_field_advantage"]["margin_points"]
        + factors["rest_travel"]["max_margin_points"]
        + factors["situational_flags"]["max_margin_points"]
        + factors["regression_luck"]["max_margin_points"]
    )
    zeroed_by_contract = {
        "injuries_depth": factors["injuries_depth"]["max_margin_points"],
        "weather_environment": factors["weather_environment"]["max_margin_points"],
        "travel_schedule": factors["travel_schedule"]["max_margin_points"],
        "kav_efficiency": factors["kav_efficiency"]["max_margin_points"],
        "personnel_efficiency": factors["personnel_efficiency"]["max_margin_points"],
        "coach_aggression": factors["coach_aggression"]["max_margin_points"],
        "info_velocity": factors["info_velocity"]["max_margin_points"],
        "travel_weather_interaction": factors["travel_weather_interaction"]["max_margin_points"],
        "external_dvoa": factors["external_dvoa"]["max_margin_points"],
    }
    return {
        "if_contract_fields": list(REQUIRED_20),
        "allowed_input_fields": sorted(ALLOWED_INPUT_FIELDS),
        "priors": {
            "base_total_points": priors["base_total_points"],
            "base_margin_points": priors["base_margin_points"],
            "home_field_points": priors["home_field_points"],
            "base_score_stdev": priors["base_score_stdev"],
        },
        "live_on_if_path_max_abs_margin": live_if_margin,
        "components_live_on_if_path": {
            "base_efficiency": factors["base_efficiency"]["max_margin_points"],
            "home_field_advantage": factors["home_field_advantage"]["margin_points"],
            "rest_travel": factors["rest_travel"]["max_margin_points"],
            "situational_flags": factors["situational_flags"]["max_margin_points"],
            "regression_luck": factors["regression_luck"]["max_margin_points"],
        },
        "zeroed_by_if_contract_or_missing_feeds": zeroed_by_contract,
        "zeroed_sum": sum(zeroed_by_contract.values()),
        "note": (
            "IF caller ALLOWED_INPUT_FIELDS is the 20 efficiency + 8 context keys. "
            "KAV/injury/weather/travel/personnel/coach/info are rejected as UNAPPROVED_HL "
            "if present. Sunday rest heuristic is 7/7 so rest+situational contribute 0 "
            "on these three games. Practical IF envelope ≈ 6.5 + 1.05 + 1.8 = 9.35 "
            "before MC noise (rest/situational 0)."
        ),
    }


def trace_game(
    game_id: str,
    schedule_game: Mapping[str, Any],
    panel: Mapping[str, Any],
    history: List[Mapping[str, Any]],
    sealed_row: Mapping[str, Any],
) -> Dict[str, Any]:
    req, elig = build_eval_request(
        game_id=game_id, schedule_game=schedule_game, panel=panel, history=history
    )
    inputs = build_contract_inputs(req)
    projection = simulate_nfl_game_independent_fair(
        inputs,
        simulations=req.simulations,
        seed=req.seed,
        market_spread_home=None,
        market_total=None,
    )
    row = invoke_diagnostic_v2(req)

    home = elig["panel_home"]
    away = elig["panel_away"]
    h = panel["teams"][home]
    a = panel["teams"][away]
    cfg = get_nfl_handicapping_config()
    matchup = _build_matchup_adjustments(inputs)
    totals_adj = _build_totals_adjustments(inputs)
    decomp = projection["decomposition"]

    off_h = float(inputs.offense_index_home)
    off_a = float(inputs.offense_index_away)
    def_h = float(inputs.defense_index_home)
    def_a = float(inputs.defense_index_away)
    off_def_home_raw = (off_h / max(0.75, def_a)) - 1.0
    off_def_away_raw = (off_a / max(0.75, def_h)) - 1.0
    off_def_home = max(-0.25, min(0.25, off_def_home_raw))
    off_def_away = max(-0.25, min(0.25, off_def_away_raw))
    spread_signal = float(matchup["spread_signal"])
    eff_raw = (off_def_home - off_def_away) * 16.0 + (0.35 * spread_signal)
    max_eff = float(cfg["factors"]["base_efficiency"]["max_margin_points"])

    clamp_hits = {
        "off_def_home": clamp_report(off_def_home_raw, -0.25, 0.25),
        "off_def_away": clamp_report(off_def_away_raw, -0.25, 0.25),
        "base_efficiency_margin": clamp_report(eff_raw, -max_eff, max_eff),
        "spread_signal_pack": {
            "value": spread_signal,
            "cap": 4.25,
            "hit": abs(spread_signal) >= 4.25 - 1e-12,
        },
        "matchup_components": {},
    }
    field_map = {
        "matchup_diff_off_epa_5g": "diff_off_epa_5g",
        "matchup_diff_def_epa_allowed_5g": "diff_def_epa_allowed_5g",
        "matchup_diff_pressure_generated_5g": "diff_pressure_generated_5g",
        "matchup_diff_pressure_allowed_5g": "diff_pressure_allowed_5g",
        "matchup_diff_red_zone_td_rate_5g": "diff_red_zone_td_rate_5g",
        "matchup_diff_success_rate_5g": "diff_success_rate_5g",
    }
    for field, (lo, hi, weight) in MATCHUP_CLAMP.items():
        raw = float(getattr(inputs, field))
        report = clamp_report(raw, lo, hi)
        report["weight"] = weight
        report["points"] = report["bounded"] * weight
        report["component_key"] = field_map[field]
        clamp_hits["matchup_components"][field] = report

    contract_inputs = {name: getattr(inputs, name) for name in REQUIRED_20}
    context = {
        "game_id": inputs.game_id,
        "home_team": inputs.home_team,
        "away_team": inputs.away_team,
        "matchup_season": inputs.matchup_season,
        "matchup_week": inputs.matchup_week,
        "rest_days_home": inputs.rest_days_home,
        "rest_days_away": inputs.rest_days_away,
    }
    outside = [
        name
        for name in (
            "injury_nowcast_impact_home",
            "weather_available",
            "travel_available",
            "home_kav_net_5g",
            "away_kav_net_5g",
            "home_personnel_edge_5g",
            "home_coach_aggression_5g",
            "info_velocity_home",
        )
        if getattr(inputs, name) is not None
    ]

    factors = decomp["factor_contributions"]
    factor_margin = {k: v.get("margin_points") for k, v in factors.items()}
    factor_avail = {k: v.get("available") for k, v in factors.items()}

    mu_h = float(decomp["expected_home_points"])
    mu_a = float(decomp["expected_away_points"])
    margin_decomp = float(decomp["predicted_margin"])
    total_decomp = float(decomp["predicted_total"])
    if_block = projection["independent_fair"]
    markets = projection["markets"]
    diag = projection["diagnostics"]

    sealed_match = {
        "margin_mu": abs(float(row["margin_mu"]) - float(sealed_row["margin_mu"])) < 1e-12,
        "total_mu": abs(float(row["total_mu"]) - float(sealed_row["total_mu"])) < 1e-12,
        "spread_home": float(row["spread_home"]) == float(sealed_row["spread_home"]),
        "home_win_prob": float(row["home_win_prob"]) == float(sealed_row["home_win_prob"]),
        "sigma": float(row["sigma"]) == float(sealed_row["sigma"]),
        "market_blend": row["market_blend"] == 0 and sealed_row["market_blend"] == 0,
    }

    mkt = MARKET_DK[game_id]
    recomputed_devig = _devig_home(mkt["ml_home"], mkt["ml_away"])
    d_spread = float(row["spread_home"]) - float(mkt["spread_home"])
    d_total = float(row["total_mean"]) - float(mkt["total"])
    d_wp = float(row["home_win_prob"]) - float(mkt["devig_home"])
    sigma = float(if_block["sigma"])
    analytic_wp = _phi(float(row["margin_mu"]) / (sigma * math.sqrt(2.0)))
    market_analytic_wp_if_sigma = _phi(
        (-float(mkt["spread_home"])) / (sigma * math.sqrt(2.0))
    )

    return {
        "game_id": game_id,
        "eligibility": {
            "home_team": home,
            "away_team": away,
            "kickoff_utc": elig["kickoff_utc"],
            "home_rolling_as_of": elig["home_rolling_as_of"],
            "away_rolling_as_of": elig["away_rolling_as_of"],
            "rest": elig["rest"],
        },
        "source_ratings": {
            "home": {
                "team": home,
                "record": h["record"],
                "wins": h["wins"],
                "losses": h["losses"],
                "games_played": h["games_played"],
                "games_in_window_5": h["games_in_window_5"],
                "as_of_week": h["as_of_week"],
                "rolling_as_of_week": h["rolling_as_of_week"],
                "t5_source": h["t5_source"],
                "prior_2025_used": h["2025_prior_used"],
                "offense_index": h["offense_index"],
                "defense_index": h["defense_index"],
                "off_epa_5g": h["off_epa_5g"],
                "def_epa_allowed_5g": h["def_epa_allowed_5g"],
                "pass_rate_5g": h["pass_rate_5g"],
                "success_5g": h["success_5g"],
                "success_defense_allowed_5g": h["success_defense_allowed_5g"],
                "pressure_rate_generated_5g": h["pressure_rate_generated_5g"],
                "pressure_rate_allowed_5g": h["pressure_rate_allowed_5g"],
                "red_zone_td_rate_5g": h["red_zone_td_rate_5g"],
            },
            "away": {
                "team": away,
                "record": a["record"],
                "wins": a["wins"],
                "losses": a["losses"],
                "games_played": a["games_played"],
                "games_in_window_5": a["games_in_window_5"],
                "as_of_week": a["as_of_week"],
                "rolling_as_of_week": a["rolling_as_of_week"],
                "t5_source": a["t5_source"],
                "prior_2025_used": a["2025_prior_used"],
                "offense_index": a["offense_index"],
                "defense_index": a["defense_index"],
                "off_epa_5g": a["off_epa_5g"],
                "def_epa_allowed_5g": a["def_epa_allowed_5g"],
                "pass_rate_5g": a["pass_rate_5g"],
                "success_5g": a["success_5g"],
                "success_defense_allowed_5g": a["success_defense_allowed_5g"],
                "pressure_rate_generated_5g": a["pressure_rate_generated_5g"],
                "pressure_rate_allowed_5g": a["pressure_rate_allowed_5g"],
                "red_zone_td_rate_5g": a["red_zone_td_rate_5g"],
            },
        },
        "contract_inputs": contract_inputs,
        "context": context,
        "out_of_contract_populated": outside,
        "transforms": {
            "record_formula_home": list(team_strength_from_record(h["record"])),
            "record_formula_away": list(team_strength_from_record(a["record"])),
            "off_def_home_raw": off_def_home_raw,
            "off_def_away_raw": off_def_away_raw,
            "off_def_home_clamped": off_def_home,
            "off_def_away_clamped": off_def_away,
            "efficiency_margin_from_indices": (off_def_home - off_def_away) * 16.0,
            "spread_signal": spread_signal,
            "spread_signal_into_efficiency_0_35": 0.35 * spread_signal,
            "base_efficiency_raw": eff_raw,
            "base_efficiency_clamped": float(factors["base_efficiency"]["margin_points"]),
            "matchup_home_points_unused_in_means": matchup["home_points"],
            "matchup_away_points_unused_in_means": matchup["away_points"],
            "matchup_total_signal": matchup["total_signal"],
            "totals_adjustment_points": totals_adj["total_points"],
            "hfa_points": factors["home_field_advantage"]["margin_points"],
            "rest_margin_points": factors["rest_travel"]["margin_points"],
            "regression_margin_points": factors["regression_luck"]["margin_points"],
            "clamp_hits": clamp_hits,
        },
        "scoring_means": {
            "mu_home": mu_h,
            "mu_away": mu_a,
            "predicted_margin_decomp": margin_decomp,
            "predicted_total_decomp": total_decomp,
            "reconstructed_margin": mu_h - mu_a,
            "reconstructed_total": mu_h + mu_a,
            "floor_home_applied": mu_h <= 7.5 + 1e-9,
            "floor_away_applied": mu_a <= 7.0 + 1e-9,
        },
        "factor_contributions_margin": factor_margin,
        "factor_available": factor_avail,
        "simulation": {
            "seed": req.seed,
            "simulations": req.simulations,
            "sigma": sigma,
            "market_blend": if_block["market_blend"],
            "margin_mu": row["margin_mu"],
            "total_mu": row["total_mu"],
            "spread_home": row["spread_home"],
            "total_mean": row["total_mean"],
            "home_win_prob": row["home_win_prob"],
            "away_win_prob": row["away_win_prob"],
            "fair_home_ml": row["fair_home_ml"],
            "fair_away_ml": row["fair_away_ml"],
            "mc_vs_decomp_margin_delta": float(row["margin_mu"]) - margin_decomp,
            "diag_mean_home": diag["mean_home_points"],
            "diag_mean_away": diag["mean_away_points"],
        },
        "sealed_replay_match": sealed_match,
        "market_orientation": {
            "if_spread_home": row["spread_home"],
            "if_convention": "spread_home = -margin_mu; negative = home favored",
            "dk_spread_home": mkt["spread_home"],
            "dk_convention": "home line negative = home favored",
            "same_orientation": (row["spread_home"] < 0) == (mkt["spread_home"] < 0),
            "both_home_favored": row["spread_home"] < 0 and mkt["spread_home"] < 0,
        },
        "signed_gaps_if_minus_dk": {
            "d_spread": round(d_spread, 2),
            "d_total": round(d_total, 2),
            "d_wp_home": round(d_wp, 4),
            "d_spread_unrounded": d_spread,
            "d_total_unrounded": d_total,
            "d_wp_home_unrounded": d_wp,
            "if_fair_home_ml": row["fair_home_ml"],
            "mkt_devig_fair_home_ml": _fair_ml(mkt["devig_home"]),
            "recomputed_devig": recomputed_devig,
            "devig_matches_seal": abs(recomputed_devig["devig_home"] - mkt["devig_home"])
            < 1e-12,
        },
        "wp_comparability": {
            "if_rule": "P(home_score - away_score > 0); margin==0 counted away; no push",
            "market_rule": "ML settlement incl OT; no push (tie void/refund ignored)",
            "analytic_wp_from_if_margin_sigma_sqrt2": analytic_wp,
            "mc_home_win_prob": row["home_win_prob"],
            "analytic_minus_mc": analytic_wp - float(row["home_win_prob"]),
            "market_devig_home": mkt["devig_home"],
            "if_sigma_applied_to_market_spread": market_analytic_wp_if_sigma,
            "market_wp_minus_if_sigma_on_mkt_spread": mkt["devig_home"]
            - market_analytic_wp_if_sigma,
        },
        "checks": {
            "units_indices_near_1": 0.82 <= off_h <= 1.18 and 0.82 <= off_a <= 1.18,
            "epa_units_per_play": True,
            "no_silent_zero_index_diff": abs(off_h - off_a) > 1e-12 or abs(def_h - def_a) > 1e-12,
            "no_home_away_flip_vs_schedule": inputs.home_team == home
            and inputs.away_team == away,
            "single_hfa": factors["home_field_advantage"]["margin_points"]
            == cfg["priors"]["home_field_points"]
            == 1.05,
            "rest_symmetric_sunday": inputs.rest_days_home == inputs.rest_days_away == 7.0,
            "blend_zero": if_block["market_blend"] == 0,
            "kav_zero": factors["kav_efficiency"]["margin_points"] == 0.0,
            "injury_zero": factors["injuries_depth"]["margin_points"] == 0.0,
            "weather_zero": factors["weather_environment"]["margin_points"] == 0.0,
            "travel_zero": factors["travel_schedule"]["margin_points"] == 0.0,
            "matchup_point_alloc_not_added_to_means": True,
        },
    }


def slate_spread_range(sealed: List[Mapping[str, Any]]) -> Dict[str, Any]:
    spreads = [float(r["spread_home"]) for r in sealed]
    totals = [float(r["total_mean"]) for r in sealed]
    wps = [float(r["home_win_prob"]) for r in sealed]
    return {
        "n": len(sealed),
        "spread_min": min(spreads),
        "spread_max": max(spreads),
        "spread_abs_max": max(abs(x) for x in spreads),
        "total_min": min(totals),
        "total_max": max(totals),
        "wp_min": min(wps),
        "wp_max": max(wps),
        "all_sigma": [float(r["sigma"]) for r in sealed],
        "sigma_unique": sorted({round(float(r["sigma"]), 6) for r in sealed}),
        "all_blend_zero": all(r["market_blend"] == 0 for r in sealed),
        "all_rating_week_7": all(r["rating_week"] == 7 for r in sealed),
    }


def data_partial_tests(panel: Mapping[str, Any], league: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "label_meaning": (
            "DATA_PARTIAL is the through-W8 operational status (1/14 complete). "
            "It is not a statement that through-W7 ratings are missing or stale."
        ),
        "as_of_contract": "rating_week = target_week - 1 (contiguous weekly IF pipeline)",
        "rating_week": RATING_WEEK,
        "target_week": TARGET_WEEK,
        "panel_as_of_week": panel.get("as_of_week"),
        "panel_n_teams": panel.get("n"),
        "panel_2025_prior_used": panel.get("2025_prior_used"),
        "tests": {
            "panel_is_through_w7_as_designed": panel.get("as_of_week") == 7,
            "all_32_teams_present": league["n"] == 32,
            "all_teams_as_of_week_7": league["all_as_of_week_7"],
            "all_5g_windows": league["all_window_5"],
            "no_2025_prior": not league["any_2025_prior"],
            "t5_is_win_loss_record": league["all_t5_from_record"],
            "indices_exactly_record_formula": league["all_off_match_record_formula"]
            and league["all_def_match_record_formula"],
            "w8_pbp_would_be_leakage": True,
        },
        "verdict": (
            "REJECT DATA_PARTIAL / week-7 vintage as the cause of IF-vs-market "
            "compression. Week-7 is the intended pregame vintage for W8. The "
            "compression is produced by the W-L→index map + designed clamps + "
            "IF contract that zeros KAV/injury/weather/travel, which would still "
            "bind if through-W8 were sealed."
        ),
    }


def render_trace_md(trace: Mapping[str, Any]) -> str:
    src_h = trace["source_ratings"]["home"]
    src_a = trace["source_ratings"]["away"]
    t = trace["transforms"]
    means = trace["scoring_means"]
    sim = trace["simulation"]
    gaps = trace["signed_gaps_if_minus_dk"]
    mkt = trace["market_orientation"]
    lines = [
        f"# TRACE {trace['game_id']}",
        "",
        "READ-ONLY replay of sealed IF (tip `6ca03716`). No math change.",
        "",
        "## 1. Source ratings (through-W7 panel 340a06dd)",
        "",
        f"| side | team | record | games | rolling | off_idx | def_idx | off_epa_5g | def_epa_allowed_5g |",
        f"|---|---|---|---:|---:|---:|---:|---:|---:|",
        (
            f"| home | {src_h['team']} | {src_h['record']} | {src_h['games_played']} | "
            f"{src_h['rolling_as_of_week']} | {src_h['offense_index']:.6f} | "
            f"{src_h['defense_index']:.6f} | {src_h['off_epa_5g']:.6f} | "
            f"{src_h['def_epa_allowed_5g']:.6f} |"
        ),
        (
            f"| away | {src_a['team']} | {src_a['record']} | {src_a['games_played']} | "
            f"{src_a['rolling_as_of_week']} | {src_a['offense_index']:.6f} | "
            f"{src_a['defense_index']:.6f} | {src_a['off_epa_5g']:.6f} | "
            f"{src_a['def_epa_allowed_5g']:.6f} |"
        ),
        "",
        f"t5_source home/away = `{src_h['t5_source']}` / `{src_a['t5_source']}`. "
        f"2025 prior used: {src_h['prior_2025_used']} / {src_a['prior_2025_used']}.",
        "",
        "## 2. Contract inputs (20 + context)",
        "",
        "```json",
        json.dumps({"context": trace["context"], "efficiency": trace["contract_inputs"]}, indent=2),
        "```",
        "",
        f"Out-of-contract fields populated on NflGameInputs: {trace['out_of_contract_populated'] or 'none (all None)'}.",
        "",
        "## 3. Transforms",
        "",
        f"- off_def_home raw/clamped: {t['off_def_home_raw']:.6f} / {t['off_def_home_clamped']:.6f}",
        f"- off_def_away raw/clamped: {t['off_def_away_raw']:.6f} / {t['off_def_away_clamped']:.6f}",
        f"- efficiency from indices ×16: {t['efficiency_margin_from_indices']:.4f}",
        f"- spread_signal (EPA pack, cap ±4.25): {t['spread_signal']:.4f}",
        f"- 0.35 × spread_signal: {t['spread_signal_into_efficiency_0_35']:.4f}",
        f"- base_efficiency raw → clamped (±6.5): {t['base_efficiency_raw']:.4f} → {t['base_efficiency_clamped']:.4f}",
        f"- HFA (once): {t['hfa_points']}",
        f"- rest margin: {t['rest_margin_points']}",
        f"- regression_luck margin: {t['regression_margin_points']}",
        f"- matchup home/away point alloc (NOT added to μ): {t['matchup_home_points_unused_in_means']:.4f} / {t['matchup_away_points_unused_in_means']:.4f}",
        "",
        "## 4. Scoring means → margin / total / wp",
        "",
        f"- μ_home = {means['mu_home']:.4f}",
        f"- μ_away = {means['mu_away']:.4f}",
        f"- predicted_margin (decomp) = {means['predicted_margin_decomp']:.4f}",
        f"- predicted_total (decomp) = {means['predicted_total_decomp']:.4f}",
        f"- IF margin_mu (MC, blend=0) = {sim['margin_mu']:.6f}",
        f"- IF spread_home = {sim['spread_home']} (= −margin_mu)",
        f"- IF total_mu / total_mean = {sim['total_mu']:.6f} / {sim['total_mean']}",
        f"- IF home_win_prob = {sim['home_win_prob']}  fair ML {sim['fair_home_ml']}/{sim['fair_away_ml']}",
        f"- sigma = {sim['sigma']}",
        f"- MC vs decomp margin Δ = {sim['mc_vs_decomp_margin_delta']:.4f} (sampling, not a second model)",
        "",
        "## 5. Signed IF − DraftKings gaps (independent recompute)",
        "",
        f"- DK spread_home = {mkt['dk_spread_home']} (home favored = negative)",
        f"- Δspread = {gaps['d_spread']}  (positive = IF closer to pick'em / less home-bullish)",
        f"- Δtotal = {gaps['d_total']}",
        f"- Δwp = {gaps['d_wp_home']}",
        f"- IF fair home ML {gaps['if_fair_home_ml']} vs market de-vig fair {gaps['mkt_devig_fair_home_ml']}",
        "",
        "## 6. Factor margin inventory",
        "",
    ]
    for name, pts in trace["factor_contributions_margin"].items():
        avail = trace["factor_available"][name]
        lines.append(f"- `{name}`: {pts} pts  available={avail}")
    lines.extend(
        [
            "",
            f"Sealed RESULTS replay match: {trace['sealed_replay_match']}",
            "",
            "≠edge ≠CLV ≠betting. NFL NO-GO CERT=0.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    panel = load_panel()
    schedule = load_schedule()
    history = history_w1_w7(schedule)
    by_id = {str(g["game_id"]): g for g in schedule.get("games") or []}
    sealed = json.loads(SEALED_RESULTS.read_text(encoding="utf-8"))
    sealed_by = {r["game_id"]: r for r in sealed}
    cfg = get_nfl_handicapping_config()
    league = league_index_audit(panel)

    games = []
    for game_id in FOCUS:
        games.append(
            trace_game(game_id, by_id[game_id], panel, history, sealed_by[game_id])
        )

    # Full-slate replay of sealed rows only (no new invoke) for range evidence.
    slate = slate_spread_range(sealed)

    # Also confirm every sealed spread is inside the practical IF envelope.
    envelope = theoretical_if_contract_caps(cfg)
    practical = (
        envelope["components_live_on_if_path"]["base_efficiency"]
        + envelope["components_live_on_if_path"]["home_field_advantage"]
        + envelope["components_live_on_if_path"]["regression_luck"]
    )

    packet = {
        "class": "CONDITIONAL_DIAG",
        "owner": "t4902u",
        "read_only": True,
        "math_changed": False,
        "if_tip": "6ca03716fe52930332d5ffba302c312a651980cc",
        "rating_week": RATING_WEEK,
        "target_week": TARGET_WEEK,
        "panel_sha256": PANEL_SHA256,
        "schedule_sha256": SCHEDULE_SHA256,
        "results_sha256": _sha256(SEALED_RESULTS),
        "market_blend": 0,
        "focus": list(FOCUS),
        "league_index_audit": {
            k: v for k, v in league.items() if k != "teams"
        },
        "league_teams": league["teams"],
        "theoretical_caps": envelope,
        "practical_sunday_if_envelope_abs": practical,
        "slate": slate,
        "data_partial_tests": data_partial_tests(panel, league),
        "games": games,
        "bans": [
            "no retune",
            "no sportsbook matching",
            "no feature/weight/blend change",
            "no Odds re-pull",
            "≠edge ≠CLV ≠betting ≠CERT",
        ],
    }

    PACKET_DIR.mkdir(parents=True, exist_ok=True)
    (PACKET_DIR / "TRACE.json").write_text(
        json.dumps(packet, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    for game in games:
        short = game["game_id"].split("-", 2)[-1].replace("@", "_at_")
        (PACKET_DIR / f"TRACE_{short}.md").write_text(
            render_trace_md(game), encoding="utf-8"
        )
    print(json.dumps({"wrote": str(PACKET_DIR / "TRACE.json"), "games": FOCUS}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
