"""CFB totals component attribution on the legal v1 universe.

Research only. Production constants stay frozen (MATCHUP_RESPONSE=1.40,
PPG, QB weights, class multipliers, clamps). PR #543 / #545 are the
authoritative scoring universe and MATCHUP_RESPONSE result.

Does not sweep MATCHUP_RESPONSE below 0.70. Does not unseal 2025.
Does not use 2026. Does not publish PLAY or write a production coefficient.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import replace
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from src.services.cfb_season_engine import priors as P
from src.services.cfb_season_engine.priors import (
    overlay_matchup_response,
    overlay_score_components,
)
from src.services.cfb_season_engine.qb_feature_contract import (
    QB_FEATURE_CONTRACT_VERSION,
)
from src.services.cfb_season_engine.qb_situation import build_qb_situation
from src.services.cfb_season_engine.team_projection import compose_team_projection
from src.services.cfb_season_engine.types import EngineUniverse, TeamProjectionState
from src.services.cfb_warehouse.frozen_140_scoring import (
    HIGH_TOTAL_TAIL,
    LEGAL_SEASONS,
    TRAIN0_GATE,
    VAL1_GATE,
    FrozenScoringError,
    assert_frozen_priors,
    load_legal_scoring_bundle,
    refuse_sealed_or_confirm,
    score_joined_rows,
    summarize_scored,
)
from src.services.cfb_warehouse.matchup_response_sweep import (
    FROZEN_RESPONSE,
    OBJECTIVE_SPLITS,
    sanity_check_frozen_140,
    split_card,
)

AUTHORIZED_FLOOR = 0.70
PUBLISHED_FLOOR_VAL1_MAE = 13.987
PUBLISHED_FLOOR_VAL1_BIAS = 4.619
PUBLISHED_FLOOR_VAL1_TAIL_N = 5
PUBLISHED_FLOOR_VAL1_DISAGREE = 7.370

# One family at a time. Do not combine these overlays.
FAMILIES: Tuple[Dict[str, Any], ...] = (
    {
        "id": "od_strength_centering",
        "label": "offensive/defensive strength centering",
        "hypothesis": (
            "Offense indices sit above 1.0 and/or defense below 1.0, so "
            "off/def > 1 on both sides and totals inflate even at r=0.70."
        ),
        "universe": "recenter_indices",
        "score_overlay": {},
    },
    {
        "id": "multiplicative_matchup",
        "label": "multiplicative matchup interaction",
        "hypothesis": (
            "ratio**response is the remaining location engine. Identity "
            "matchup isolates baseline + additive terms."
        ),
        "universe": None,
        "score_overlay": {"matchup_mode": "identity"},
    },
    {
        "id": "qb_talent_scale",
        "label": "QB talent response/scale",
        "hypothesis": (
            "Layer A talent + class + QB_INDEX_BLEND raise offense indices "
            "above the hist-cal placeholder@50 path."
        ),
        "universe": "neutralize_qb",
        "score_overlay": {},
    },
    {
        "id": "supporting_cast",
        "label": "supporting-cast contribution",
        "hypothesis": (
            "Cast is already held at 50 on this universe; neutralizing it "
            "again should be a near-zero move."
        ),
        "universe": "neutralize_cast",
        "score_overlay": {},
    },
    {
        "id": "pace_possessions",
        "label": "pace/possessions assumptions",
        "hypothesis": "Explosiveness-driven pace > 1 systematically lifts totals.",
        "universe": "force_pace_one",
        "score_overlay": {"force_pace_one": True},
    },
    {
        "id": "home_field",
        "label": "home-field contribution",
        "hypothesis": "Variable HFA adds ~1–3 points to every non-neutral total.",
        "universe": None,
        "score_overlay": {"zero_hfa": True},
    },
    {
        "id": "clipping",
        "label": "clipping/floors/ceilings",
        "hypothesis": (
            "EXPECTED_POINTS_CLAMP (7, 55) and ratio soft-clamp distort "
            "location or the upper tail."
        ),
        "universe": None,
        "score_overlay": {"disable_clamp": True, "disable_ratio_clamp": True},
    },
    {
        "id": "double_counted_strength",
        "label": "duplicated / double-counted strength effects",
        "hypothesis": (
            "QB and efficiency enter the weighted score and again via "
            "post-compose index blends, then again through off/def."
        ),
        "universe": "zero_post_compose_blends",
        "score_overlay": {},
    },
    {
        "id": "nonlinear_exponent",
        "label": "nonlinear/exponent interaction",
        "hypothesis": (
            "ratio**r (r=1.40) explodes the upper tail versus a linear "
            "response of the same coefficient."
        ),
        "universe": None,
        "score_overlay": {"matchup_mode": "linear"},
    },
    {
        "id": "efficiency_level",
        "label": "baseline scoring / efficiency PPG level",
        "hypothesis": (
            "Prior-year off_eff/def_eff are not centered at 50, so compose "
            "starts above league average before matchup is applied."
        ),
        "universe": "neutralize_efficiency",
        "score_overlay": {},
    },
)

BLEND_ZERO = {
    "QB_INDEX_BLEND": 0.0,
    "OL_INDEX_BLEND": 0.0,
    "SKILL_INDEX_BLEND": 0.0,
    "EFF_OFF_INDEX_BLEND": 0.0,
    "EFF_DEF_INDEX_BLEND": 0.0,
    "DEF_UNIT_BLEND": 0.0,
}

OD_OFF_TERTILES = ("off_lo", "off_mid", "off_hi")
OD_DEF_TERTILES = ("def_lo", "def_mid", "def_hi")


def totals_equation_doc() -> Dict[str, Any]:
    """Complete mathematical path from raw inputs to predicted total."""
    return {
        "production_constants": {
            "LEAGUE_TEAM_PPG": P.LEAGUE_TEAM_PPG,
            "MATCHUP_RESPONSE": P.MATCHUP_RESPONSE,
            "MATCHUP_RATIO_CLAMP": list(P.MATCHUP_RATIO_CLAMP),
            "MATCHUP_RATIO_EXCESS_RETAIN": P.MATCHUP_RATIO_EXCESS_RETAIN,
            "EXPECTED_POINTS_CLAMP": list(P.EXPECTED_POINTS_CLAMP),
            "STRENGTH_CLAMP": list(P.STRENGTH_CLAMP),
            "QB_SITUATION_INDEX_CLAMP": list(P.QB_SITUATION_INDEX_CLAMP),
            "SCORE_TO_INDEX_DIVISOR": P.SCORE_TO_INDEX_DIVISOR,
            "SCORE_TO_INDEX_CLAMP": list(P.SCORE_TO_INDEX_CLAMP),
            "HFA_BASELINE_POINTS": P.HFA_BASELINE_POINTS,
            "SPECIAL_TEAMS_TOTAL_SCALE": P.SPECIAL_TEAMS_TOTAL_SCALE,
            "QB_CLASS_OFFENSE_MULT": dict(P.QB_CLASS_OFFENSE_MULT),
            "QB_CAST_INDEX_SCALE": P.QB_CAST_INDEX_SCALE,
            "QB_INDEX_BLEND": P.QB_INDEX_BLEND,
            "EFF_OFF_INDEX_BLEND": P.EFF_OFF_INDEX_BLEND,
            "EFF_DEF_INDEX_BLEND": P.EFF_DEF_INDEX_BLEND,
            "WEIGHT_OFF_EFF": P.WEIGHT_OFF_EFF,
            "WEIGHT_QB_SITUATION": P.WEIGHT_QB_SITUATION,
            "WEIGHT_ROSTER_STRENGTH": P.WEIGHT_ROSTER_STRENGTH,
            "EARLY_SEASON_SEPARATION_SOFTEN": dict(P.EARLY_SEASON_SEPARATION_SOFTEN),
        },
        "qb_layer": {
            "talent_index": "1 + (qb_talent - 50) / 80",
            "class_mult": "QB_CLASS_OFFENSE_MULT[class]",
            "cast_mult": "1 + QB_CAST_INDEX_SCALE * (cast - 50) / 50",
            "qb_situation_index": (
                "clamp(talent_index * class_mult * cast_mult, "
                "QB_SITUATION_INDEX_CLAMP)"
            ),
            "qb_situation_score": "clamp(50 + (index - 1) * 80)",
            "v1_reconstruction": (
                "Layer A talent + class + portal. Cast held at 50 so "
                "cast_mult = 1.0. Recruiting / Layer B missing."
            ),
        },
        "compose": {
            "offense_score": (
                "WEIGHT_OFF_EFF*off_eff + WEIGHT_ROSTER_STRENGTH*roster "
                "+ WEIGHT_QB_SITUATION*qb_score + WEIGHT_SKILL_GROUP*skill "
                "+ WEIGHT_OL_GROUP*ol"
            ),
            "defense_score": (
                "WEIGHT_DEF_EFF*def_eff + WEIGHT_DEF_ROSTER_STRENGTH*roster "
                "+ WEIGHT_DEF_FRONT_SEVEN*front_seven "
                "+ WEIGHT_DEF_SECONDARY*secondary "
                "+ WEIGHT_DEF_EXPERIENCE*experience"
            ),
            "score_to_index": (
                "clamp(1 + (score - 50) / SCORE_TO_INDEX_DIVISOR, "
                "SCORE_TO_INDEX_CLAMP)"
            ),
            "post_compose_multiplicative_blends": [
                "offense *= mix(1, qb_index, QB_INDEX_BLEND)",
                "offense *= mix(1, ol_index, OL_INDEX_BLEND)",
                "offense *= mix(1, skill_index, SKILL_INDEX_BLEND)",
                "offense *= mix(1, off_eff_index, EFF_OFF_INDEX_BLEND)",
                "offense *= coaching.offense_index_mult",
                "defense *= mix(1, front7/secondary unit, DEF_UNIT_BLEND)",
                "defense *= mix(1, def_eff_index, EFF_DEF_INDEX_BLEND)",
                "defense *= coaching.defense_index_mult",
                "both clamped to STRENGTH_CLAMP",
            ],
            "pace_factor": (
                "clamp(1 + (skill - front_seven) / 200, 0.85, 1.20) "
                "+ (explosiveness - 50) / 400"
            ),
            "v1_reconstruction": (
                "Roster / units / coaching are league-average fills (50 / "
                "returning). Efficiency is prior-year cfb_ratings, not live SP+."
            ),
        },
        "expected_team_points": {
            "raw_ratio": "offense_index / max(0.50, opponent_defense_index)",
            "ratio": (
                "soft_clamp(raw_ratio, MATCHUP_RATIO_CLAMP, "
                "retain=MATCHUP_RATIO_EXCESS_RETAIN)"
            ),
            "response": (
                "MATCHUP_RESPONSE * EARLY_SEASON_SEPARATION_SOFTEN[week] "
                "for W1–W4; else MATCHUP_RESPONSE"
            ),
            "matchup": "ratio ** response   (power; research may linearize)",
            "unit_offense_boost": (
                "clamp(1 + UNIT_OFFENSE_BOOST_SCALE * signed(OL, skill), "
                "0.85, 1.15)  — identity 1.0 when units=50"
            ),
            "unit_defense_dampen": (
                "clamp(1 - UNIT_DEFENSE_DAMPEN_SCALE * signed(F7, secondary), "
                "0.82, 1.18)  — identity 1.0 when units=50"
            ),
            "pace": "0.5 * (offense.pace_factor + opponent.pace_factor)",
            "multiplicative_core": (
                "LEAGUE_TEAM_PPG * matchup * off_boost * def_dampen * pace"
            ),
            "additive": [
                "variable HFA (home only; 0 on neutral)",
                "week-decayed coaching adj (0 on this reconstruction)",
            ],
            "clip": "clamp(core + additive, EXPECTED_POINTS_CLAMP=(7, 55))",
        },
        "game_total": {
            "st_nudge": (
                "SPECIAL_TEAMS_TOTAL_SCALE * (mean(ST) - 50)  — 0 when ST=50"
            ),
            "expected_total": (
                "home_points + away_points + st_nudge  "
                "(nudge split evenly across both scores)"
            ),
            "spread_home": "away_points - home_points",
        },
        "terms_that_can_move_the_total": [
            "LEAGUE_TEAM_PPG (baseline, multiplicative)",
            "offense_index / defense_index (ratio)",
            "MATCHUP_RESPONSE and W1–W4 soften (exponent)",
            "ratio soft-clamp + excess retain",
            "unit offense boost / defense dampen (identity on v1)",
            "pace / explosiveness",
            "variable HFA (additive to home, therefore to total)",
            "coaching week adj (identity on v1)",
            "EXPECTED_POINTS_CLAMP per team",
            "special-teams nudge (identity on v1)",
            "QB talent / class / cast (via compose + QB_INDEX_BLEND)",
            "efficiency off/def (via weighted score + EFF_*_BLEND)",
            "post-compose double application of QB/efficiency/units",
        ],
        "why_140_can_need_a_huge_downward_response": (
            "If E[offense_index] > E[defense_index], then E[ratio] > 1 on "
            "both sides of a typical game. ratio**1.40 is convex for "
            "ratio>1, so the upper tail explodes and both team scores rise. "
            "Lowering r shrinks that convexity but cannot fix a systematic "
            "O>D location or a double-counted QB/efficiency lever."
        ),
    }


def _fmean(xs: Sequence[float]) -> Optional[float]:
    return statistics.fmean(xs) if xs else None


def _copy_universe(
    universe: EngineUniverse,
    teams: Mapping[str, TeamProjectionState],
    note: str,
) -> EngineUniverse:
    notes = dict(universe.notes)
    notes["attribution_transform"] = note
    return EngineUniverse(
        season=universe.season,
        schedule=list(universe.schedule),
        teams=dict(teams),
        player_hooks=dict(universe.player_hooks),
        conferences=dict(universe.conferences),
        notes=notes,
    )


def _recompose(state: TeamProjectionState) -> TeamProjectionState:
    return compose_team_projection(
        state.team,
        state.roster,
        state.qb,
        state.groups,
        efficiency=state.efficiency,
        home_field=state.home_field,
        coaching=state.coaching,
    )


def transform_universe(universe: EngineUniverse, kind: Optional[str]) -> EngineUniverse:
    if not kind:
        return universe
    teams = universe.teams
    if kind == "recenter_indices":
        offs = [float(t.offense_index) for t in teams.values()]
        defs = [float(t.defense_index) for t in teams.values()]
        mean_o = statistics.fmean(offs) if offs else 1.0
        mean_d = statistics.fmean(defs) if defs else 1.0
        out = {}
        for code, st in teams.items():
            c = st.copy()
            c.offense_index = round(
                max(P.STRENGTH_CLAMP[0], min(P.STRENGTH_CLAMP[1], st.offense_index / mean_o)),
                4,
            )
            c.defense_index = round(
                max(P.STRENGTH_CLAMP[0], min(P.STRENGTH_CLAMP[1], st.defense_index / mean_d)),
                4,
            )
            out[code] = c
        return _copy_universe(
            universe,
            out,
            f"recenter_indices mean_off={mean_o:.4f} mean_def={mean_d:.4f}",
        )
    if kind == "force_pace_one":
        out = {}
        for code, st in teams.items():
            c = st.copy()
            c.pace_factor = 1.0
            out[code] = c
        return _copy_universe(universe, out, "force_pace_one")
    if kind == "neutralize_qb":
        out = {}
        for code, st in teams.items():
            qb = st.qb
            payload = {
                "qb_class": qb.qb_class if qb else "unknown",
                "qb_talent": 50.0,
                "ol_support": 50.0,
                "weapons_support": 50.0,
                "supporting_cast": 50.0,
                "experience_starts": qb.experience_starts if qb else 0,
                "is_portal": False,
                "starter_name": qb.starter_name if qb else "",
                "starter_key": qb.starter_key if qb else "",
                "qb_situation_index": 1.0,
                "qb_situation_score": 50.0,
                "fidelity": "placeholder",
                "source": "attribution_neutralize_qb",
                "notes": "score-time QB neutralization; production priors unchanged",
            }
            new_qb = build_qb_situation(code, payload, default_source="attribution_neutralize_qb")
            rebuilt = compose_team_projection(
                code,
                st.roster,
                new_qb,
                st.groups,
                efficiency=st.efficiency,
                home_field=st.home_field,
                coaching=st.coaching,
            )
            out[code] = rebuilt
        return _copy_universe(universe, out, "neutralize_qb")
    if kind == "neutralize_cast":
        out = {}
        for code, st in teams.items():
            qb = st.qb
            payload = {
                "qb_class": qb.qb_class if qb else "unknown",
                "qb_talent": qb.qb_talent if qb else 50.0,
                "ol_support": 50.0,
                "weapons_support": 50.0,
                "supporting_cast": 50.0,
                "experience_starts": qb.experience_starts if qb else 0,
                "is_portal": bool(qb and qb.qb_class == "portal"),
                "starter_name": qb.starter_name if qb else "",
                "starter_key": qb.starter_key if qb else "",
                "fidelity": "approximate",
                "source": "attribution_neutralize_cast",
            }
            new_qb = build_qb_situation(code, payload, default_source="attribution_neutralize_cast")
            out[code] = compose_team_projection(
                code,
                st.roster,
                new_qb,
                st.groups,
                efficiency=st.efficiency,
                home_field=st.home_field,
                coaching=st.coaching,
            )
        return _copy_universe(universe, out, "neutralize_cast")
    if kind == "zero_post_compose_blends":
        with overlay_score_components(BLEND_ZERO):
            out = {code: _recompose(st) for code, st in teams.items()}
        return _copy_universe(universe, out, "zero_post_compose_blends")
    if kind == "neutralize_efficiency":
        out = {}
        for code, st in teams.items():
            eff = st.efficiency
            if eff is not None:
                eff = replace(
                    eff,
                    off_eff=50.0,
                    def_eff=50.0,
                    explosiveness=50.0,
                    success_off=50.0,
                    success_def=50.0,
                    notes="attribution_neutralize_efficiency",
                )
            out[code] = compose_team_projection(
                code,
                st.roster,
                st.qb,
                st.groups,
                efficiency=eff,
                home_field=st.home_field,
                coaching=st.coaching,
            )
        return _copy_universe(universe, out, "neutralize_efficiency")
    raise FrozenScoringError(f"unknown universe transform {kind}")


def _tertile_edges(xs: Sequence[float]) -> Tuple[float, float]:
    ordered = sorted(float(x) for x in xs)
    if len(ordered) < 3:
        mid = ordered[0] if ordered else 0.0
        return mid, mid

    def _q(p: float) -> float:
        idx = p * (len(ordered) - 1)
        lo = int(math.floor(idx))
        hi = int(math.ceil(idx))
        if lo == hi:
            return ordered[lo]
        w = idx - lo
        return ordered[lo] * (1.0 - w) + ordered[hi] * w

    return _q(1.0 / 3.0), _q(2.0 / 3.0)


def _tertile_label(value: float, lo: float, hi: float, prefix: str) -> str:
    if value < lo:
        return f"{prefix}_lo"
    if value < hi:
        return f"{prefix}_mid"
    return f"{prefix}_hi"


def _component_moments(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    if not rows or rows[0].get("home_off_idx") is None:
        return {}

    def col(key: str) -> List[float]:
        out = []
        for r in rows:
            val = r.get(key)
            if val is None:
                continue
            out.append(float(val))
        return out

    home_off = col("home_off_idx")
    home_def = col("home_def_idx")
    away_off = col("away_off_idx")
    away_def = col("away_def_idx")
    all_off = home_off + away_off
    all_def = home_def + away_def
    ratios = col("home_ratio") + col("away_ratio")
    raw_ratios = col("home_ratio_raw") + col("away_ratio_raw")
    matchups = col("home_matchup_mult") + col("away_matchup_mult")
    paces = col("home_pace_used") + col("away_pace_used")
    hfa = col("home_hfa_pts")
    pre = col("home_pre_clamp") + col("away_pre_clamp")
    clamp_hits = [
        1.0
        for r in rows
        if r.get("home_clamped") or r.get("away_clamped")
    ]
    qb = col("home_qb_index") + col("away_qb_index")
    off_eff = col("home_off_eff") + col("away_off_eff")
    def_eff = col("home_def_eff") + col("away_def_eff")
    two_ppg = 2.0 * float(P.LEAGUE_TEAM_PPG)
    mean_model = _fmean([float(r["model_total"]) for r in rows])
    mean_hfa = _fmean(hfa) or 0.0
    mean_matchup = _fmean(matchups) or 1.0
    mean_pace = _fmean(paces) or 1.0
    # Sequential peel of the mean total (approximate; clamps/HFA interact).
    location = {
        "two_league_ppg": two_ppg,
        "mean_model_total": mean_model,
        "approx_matchup_lift": two_ppg * (mean_matchup - 1.0),
        "approx_pace_lift": two_ppg * mean_matchup * (mean_pace - 1.0),
        "mean_hfa_added_to_total": mean_hfa,
        "residual_after_ppg_matchup_pace_hfa": (
            None
            if mean_model is None
            else mean_model - two_ppg * mean_matchup * mean_pace - mean_hfa
        ),
    }
    return {
        "n": len(rows),
        "mean_offense_index": _fmean(all_off),
        "mean_defense_index": _fmean(all_def),
        "mean_off_minus_def": (
            None
            if not all_off or not all_def
            else _fmean(all_off) - _fmean(all_def)
        ),
        "mean_raw_ratio": _fmean(raw_ratios),
        "mean_clamped_ratio": _fmean(ratios),
        "mean_matchup_mult": _fmean(matchups),
        "mean_pace": _fmean(paces),
        "mean_hfa_points": _fmean(hfa),
        "mean_pre_clamp_team_points": _fmean(pre),
        "clamp_game_rate": (len(clamp_hits) / len(rows)) if rows else None,
        "mean_qb_index": _fmean(qb),
        "mean_off_eff": _fmean(off_eff),
        "mean_def_eff": _fmean(def_eff),
        "std_offense_index": statistics.pstdev(all_off) if len(all_off) > 1 else 0.0,
        "std_defense_index": statistics.pstdev(all_def) if len(all_def) > 1 else 0.0,
        "location_decomposition": location,
    }


def _od_combo_table(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    if not rows or rows[0].get("home_off_idx") is None:
        return {}
    off = [float(r["home_off_idx"]) for r in rows] + [
        float(r["away_off_idx"]) for r in rows
    ]
    deff = [float(r["away_def_idx"]) for r in rows] + [
        float(r["home_def_idx"]) for r in rows
    ]
    # Pair the scoring offense with the defense it faces.
    pairs = [
        (float(r["home_off_idx"]), float(r["away_def_idx"]), float(r["err_total_vs_actual"]), float(r["model_total"]))
        for r in rows
    ] + [
        (float(r["away_off_idx"]), float(r["home_def_idx"]), float(r["err_total_vs_actual"]), float(r["model_total"]))
        for r in rows
    ]
    o_lo, o_hi = _tertile_edges(off)
    d_lo, d_hi = _tertile_edges(deff)
    cells: Dict[str, List[Tuple[float, float]]] = {}
    for o, d, err, pred in pairs:
        key = (
            f"{_tertile_label(o, o_lo, o_hi, 'off')}__"
            f"{_tertile_label(d, d_lo, d_hi, 'def')}"
        )
        cells.setdefault(key, []).append((err, pred))
    out = {
        "offense_tertile_edges": [o_lo, o_hi],
        "defense_tertile_edges": [d_lo, d_hi],
        "cells": {},
    }
    for key, xs in sorted(cells.items()):
        errs = [e for e, _p in xs]
        preds = [p for _e, p in xs]
        out["cells"][key] = {
            "n_team_games": len(xs),
            "mae_vs_actual_teamshare": _fmean([abs(e) for e in errs]),
            "bias_vs_actual_teamshare": _fmean(errs),
            "mean_model_total": _fmean(preds),
        }
    return out


def _error_type(card: Mapping[str, Any], moments: Mapping[str, Any]) -> Dict[str, Any]:
    buckets = card.get("projected_total_buckets") or {}
    biases = []
    for name in ("lt_48", "48_54", "54_60", "60_68", "ge_68"):
        brow = buckets.get(name) or {}
        if brow.get("total_vs_actual_bias") is not None and (brow.get("n") or 0) >= 8:
            biases.append((name, float(brow["total_vs_actual_bias"]), int(brow["n"])))
    loc = float(card.get("bias_vs_actual") or 0.0)
    mae = float(card.get("mae_vs_actual") or 0.0)
    tail_n = int(card.get("high_tail_n") or 0)
    location = abs(loc) >= 3.0
    # Residual MAE after removing mean bias.
    residual = max(0.0, mae - abs(loc))
    scale = False
    nonlinear = False
    if len(biases) >= 3:
        # Bias rising with predicted-total bin ⇒ scale / nonlinearity.
        signed = [b for _n, b, _c in biases]
        if signed[-1] - signed[0] >= 4.0:
            scale = True
        if any(name == "ge_68" and b >= loc + 4.0 for name, b, _c in biases):
            nonlinear = True
    if tail_n >= 30:
        nonlinear = True
    off_minus_def = moments.get("mean_off_minus_def")
    if off_minus_def is not None and float(off_minus_def) >= 0.04:
        scale = True
    kinds = []
    if location:
        kinds.append("LOCATION")
    if scale:
        kinds.append("SCALE")
    if nonlinear:
        kinds.append("NONLINEARITY")
    if not kinds:
        kinds.append("INSUFFICIENT SIGNAL")
    primary = "MULTIPLE" if len(kinds) > 1 else kinds[0]
    return {
        "primary": primary,
        "flags": kinds,
        "val1_bias": loc,
        "val1_mae": mae,
        "mae_minus_abs_bias": residual,
        "bin_biases": biases,
        "high_tail_n": tail_n,
        "mean_off_minus_def": off_minus_def,
        "note": (
            "LOCATION = systematic signed bias. SCALE = error grows with "
            "predicted total / O-D gap. NONLINEARITY = tail or exponent "
            "pathology. MULTIPLE = more than one is material."
        ),
    }


def enrich_card(
    summary: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    splits = summary.get("splits") or {}
    out: Dict[str, Dict[str, Any]] = {}
    for name in OBJECTIVE_SPLITS:
        subset = [
            r
            for r in rows
            if int(r["season"]) in ((2022,) if name == "train_0" else (2023,) if name == "val_0" else (2024,))
            and int(r["week"]) in range(1, 15)
        ]
        block = splits.get(name) or {}
        card = split_card(block)
        card["std_model_total"] = block.get("std_model_total")
        card["model_total_quantiles"] = block.get("model_total_quantiles")
        card["projected_total_buckets"] = {}
        for bname, brow in (block.get("projected_total_buckets") or {}).items():
            card["projected_total_buckets"][bname] = {
                "n": brow.get("n"),
                "mae_vs_actual": brow.get("total_vs_actual_mae"),
                "bias_vs_actual": brow.get("total_vs_actual_bias"),
                "mean_model_total": brow.get("mean_model_total"),
                "mean_actual_total": brow.get("mean_actual_total"),
                "mean_close_total": brow.get("mean_close_total"),
                "mean_abs_disagree_total": brow.get("mean_abs_disagree_total")
                or brow.get("total_vs_close_mae"),
            }
        moments = _component_moments(subset)
        card["moments"] = moments
        card["od_combos"] = _od_combo_table(subset)
        if name == "val_1":
            card["error_type"] = _error_type(card, moments)
        out[name] = card
    return out


def _delta_card(new: Mapping[str, Any], old: Mapping[str, Any]) -> Dict[str, Any]:
    keys = (
        "n",
        "mae_vs_actual",
        "rmse_vs_actual",
        "bias_vs_actual",
        "medae_vs_actual",
        "mean_model_total",
        "std_model_total",
        "mean_abs_disagree_total",
        "bias_vs_close",
        "high_tail_n",
        "high_tail_bias_vs_actual",
        "margin_mae_vs_actual",
        "ats_hit_rate",
    )
    out: Dict[str, Any] = {}
    for key in keys:
        n = new.get(key)
        o = old.get(key)
        delta = None
        if n is not None and o is not None:
            try:
                delta = float(n) - float(o)
            except (TypeError, ValueError):
                delta = None
        out[key] = {"value": n, "reference": o, "delta": delta}
    return out


def score_variant(
    bundle: Mapping[str, Any],
    *,
    lake_only: bool,
    matchup_response: Optional[float],
    score_overlay: Mapping[str, Any],
    universe_kind: Optional[str],
    family_id: str,
    panel: str,
) -> Dict[str, Any]:
    assert_frozen_priors()
    if abs(float(P.MATCHUP_RESPONSE) - FROZEN_RESPONSE) > 1e-9:
        raise FrozenScoringError("production MATCHUP_RESPONSE drifted from 1.40")
    universes = {
        season: transform_universe(uni, universe_kind)
        for season, uni in bundle["universes"].items()
    }
    with overlay_matchup_response(matchup_response):
        with overlay_score_components(score_overlay):
            if abs(float(P.MATCHUP_RESPONSE) - FROZEN_RESPONSE) > 1e-9:
                raise FrozenScoringError("overlay mutated MATCHUP_RESPONSE")
            if abs(float(P.LEAGUE_TEAM_PPG) - 25.9) > 1e-9:
                raise FrozenScoringError("overlay mutated LEAGUE_TEAM_PPG")
            scored, skipped = score_joined_rows(
                bundle["joined"],
                universes,
                lake_only=lake_only,
                with_components=True,
            )
    if abs(float(P.MATCHUP_RESPONSE) - FROZEN_RESPONSE) > 1e-9:
        raise FrozenScoringError("overlay leaked after reset")
    summary = summarize_scored(scored)
    cards = enrich_card(summary, scored)
    return {
        "family_id": family_id,
        "panel": panel,
        "matchup_response_overlay": matchup_response,
        "matchup_response_frozen": P.MATCHUP_RESPONSE,
        "universe_transform": universe_kind,
        "score_overlay": dict(score_overlay),
        "skipped": skipped,
        "n_scored": summary.get("n_scored"),
        "splits": cards,
    }


def decide_attribution(
    *,
    lake_mounted: bool,
    sanity: Mapping[str, Any],
    panel_140: Sequence[Mapping[str, Any]],
    panel_070: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    if not lake_mounted:
        return {
            "recommendation": "INSUFFICIENT EVIDENCE",
            "why": ["legal Odds-API lake not mounted"],
            "ranked": [],
        }
    if not sanity.get("ok"):
        return {
            "recommendation": "INSUFFICIENT EVIDENCE",
            "why": list(sanity.get("why") or ["frozen 1.40 failed PR #543 sanity"]),
            "ranked": [],
        }

    by_id_140 = {r["family_id"]: r for r in panel_140}
    by_id_070 = {r["family_id"]: r for r in panel_070}
    ref140 = by_id_140.get("frozen_140") or {}
    ref070 = by_id_070.get("floor_070") or {}
    v140 = (ref140.get("splits") or {}).get("val_1") or {}
    v070 = (ref070.get("splits") or {}).get("val_1") or {}
    if int(v140.get("n") or 0) < VAL1_GATE or int(
        ((ref140.get("splits") or {}).get("train_0") or {}).get("n") or 0
    ) < TRAIN0_GATE:
        return {
            "recommendation": "INSUFFICIENT EVIDENCE",
            "why": [
                f"Val-1 n={v140.get('n')} (need {VAL1_GATE})",
                f"Train-0 n={((ref140.get('splits') or {}).get('train_0') or {}).get('n')}",
            ],
            "ranked": [],
        }

    ranked = []
    for fam in FAMILIES:
        fid = fam["id"]
        a = ((by_id_140.get(fid) or {}).get("splits") or {}).get("val_1") or {}
        b = ((by_id_070.get(fid) or {}).get("splits") or {}).get("val_1") or {}
        d140 = _delta_card(a, v140)
        d070 = _delta_card(b, v070)
        bias_move_140 = abs((d140.get("bias_vs_actual") or {}).get("delta") or 0.0)
        bias_move_070 = abs((d070.get("bias_vs_actual") or {}).get("delta") or 0.0)
        mae_move_140 = -((d140.get("mae_vs_actual") or {}).get("delta") or 0.0)
        mae_move_070 = -((d070.get("mae_vs_actual") or {}).get("delta") or 0.0)
        tail_move_140 = -((d140.get("high_tail_n") or {}).get("delta") or 0.0)
        ranked.append(
            {
                "family_id": fid,
                "label": fam["label"],
                "hypothesis": fam["hypothesis"],
                "val1_vs_140": d140,
                "val1_vs_070": d070,
                "abs_bias_move_vs_140": bias_move_140,
                "abs_bias_move_vs_070": bias_move_070,
                "mae_improve_vs_140": mae_move_140,
                "mae_improve_vs_070": mae_move_070,
                "tail_n_drop_vs_140": tail_move_140,
                "score": max(bias_move_140, bias_move_070) + 0.25 * max(mae_move_140, 0.0),
            }
        )
    ranked.sort(key=lambda r: (-float(r["score"]), r["family_id"]))

    material = [
        r
        for r in ranked
        if r["abs_bias_move_vs_140"] >= 1.00 or r["abs_bias_move_vs_070"] >= 0.75
    ]
    top = ranked[0] if ranked else None
    error_type = v140.get("error_type") or {}
    remaining = float(v070.get("bias_vs_actual") or 0.0)
    baseline_gap = 2.0 * float(P.LEAGUE_TEAM_PPG) - float(v140.get("mean_actual_total") or 53.74)
    moments140 = v140.get("moments") or {}
    off_minus_def = moments140.get("mean_off_minus_def")

    why: List[str] = []
    why.append(
        f"Val-1 frozen 1.40 MAE={v140.get('mae_vs_actual')} bias={v140.get('bias_vs_actual')} "
        f"tail_n={v140.get('high_tail_n')}"
    )
    why.append(
        f"Val-1 authorized 0.70 floor MAE={v070.get('mae_vs_actual')} "
        f"bias={v070.get('bias_vs_actual')} tail_n={v070.get('high_tail_n')} "
        f"|m-c|={v070.get('mean_abs_disagree_total')}"
    )
    why.append(
        f"2*LEAGUE_TEAM_PPG={2.0 * P.LEAGUE_TEAM_PPG:.1f} vs mean actual "
        f"{v140.get('mean_actual_total')} (PPG-only gap {baseline_gap:+.2f})"
    )
    if off_minus_def is not None:
        why.append(f"mean(offense_index)−mean(defense_index)={float(off_minus_def):+.4f}")
    why.append(f"error type @1.40: {error_type.get('primary')} {error_type.get('flags')}")
    if top:
        why.append(
            f"largest one-family move: {top['family_id']} "
            f"|Δbias@1.40|={top['abs_bias_move_vs_140']:.3f} "
            f"|Δbias@0.70|={top['abs_bias_move_vs_070']:.3f}"
        )

    # Recommendation gate. Exactly one.
    ppg_is_high = baseline_gap >= 1.5
    centering = next((r for r in ranked if r["family_id"] == "od_strength_centering"), None)
    matchup = next((r for r in ranked if r["family_id"] == "multiplicative_matchup"), None)
    nonlinear = next((r for r in ranked if r["family_id"] == "nonlinear_exponent"), None)
    qb = next((r for r in ranked if r["family_id"] == "qb_talent_scale"), None)
    double = next((r for r in ranked if r["family_id"] == "double_counted_strength"), None)

    if ppg_is_high and (not material or (top and top["family_id"] in {"home_field", "clipping"})):
        rec = "BASELINE RECALIBRATION"
        why.append(
            "2*PPG already sits above mean actual; open LEAGUE_TEAM_PPG only "
            "after confirming matchup/QB are identity on the same universe."
        )
    elif (
        nonlinear
        and nonlinear["tail_n_drop_vs_140"] >= 80
        and (error_type.get("primary") in {"NONLINEARITY", "MULTIPLE"})
        and (not centering or centering["abs_bias_move_vs_070"] < 1.5)
        and (not qb or qb["abs_bias_move_vs_140"] < 2.0)
    ):
        rec = "RESPONSE/NONLINEARITY REDESIGN"
        why.append(
            "Linearizing the exponent collapses the tail without a single "
            "component weight explaining remaining location."
        )
    elif (
        len(material) >= 3
        or (
            centering
            and qb
            and centering["abs_bias_move_vs_140"] >= 1.0
            and qb["abs_bias_move_vs_140"] >= 1.0
        )
        or (
            matchup
            and centering
            and matchup["abs_bias_move_vs_140"] >= 1.5
            and centering["abs_bias_move_vs_070"] >= 0.75
        )
    ):
        rec = "MULTIVARIATE RECALIBRATION"
        why.append(
            "More than one family moves Val-1 location/MAE by a material "
            "amount. A single-knob fit would re-create the 1.40 compensating-knob problem."
        )
    elif top and top["family_id"] in {
        "qb_talent_scale",
        "double_counted_strength",
        "od_strength_centering",
        "supporting_cast",
        "pace_possessions",
        "home_field",
        "efficiency_level",
    }:
        rec = "COMPONENT WEIGHT RECALIBRATION"
        why.append(
            f"One family ({top['family_id']}) dominates the one-at-a-time "
            "moves. Open that family's weights/centering next, still frozen elsewhere."
        )
    elif top and top["family_id"] in {"nonlinear_exponent", "multiplicative_matchup"}:
        rec = "RESPONSE/NONLINEARITY REDESIGN"
        why.append(
            "The matchup transform — not a baseline PPG miss — is the dominant family."
        )
    else:
        rec = "INSUFFICIENT EVIDENCE"
        why.append("Ablations did not isolate a material, stable family.")

    evidence_to_open = {
        "BASELINE RECALIBRATION": (
            "2*PPG vs mean actual ≥ +1.5 AND other families move remaining "
            "0.70 bias by <0.75. Then open LEAGUE_TEAM_PPG only."
        ),
        "RESPONSE/NONLINEARITY REDESIGN": (
            "Linear vs power at the same r, plus predicted-total bin slope "
            "and ≥68 tail, plus O-high/D-low cell explosion. Do not open "
            "MATCHUP_RESPONSE below 0.70 as a compensating knob."
        ),
        "COMPONENT WEIGHT RECALIBRATION": (
            "One family (QB blend, efficiency blend, or index centering) "
            "moves Val-1 actual bias by ≥1.0 @1.40 or ≥0.75 of remaining "
            "@0.70, and the others do not."
        ),
        "MULTIVARIATE RECALIBRATION": (
            "≥3 material families, or centering AND QB both ≥1.0 bias-move "
            "@1.40, or matchup identity AND remaining centering @0.70. "
            "Fit jointly on Train-0 with Val-0/Val-1 holdout. Still no 2025."
        ),
        "INSUFFICIENT EVIDENCE": "Lake/n/sanity failed, or no family moved metrics.",
    }
    return {
        "recommendation": rec,
        "why": why,
        "error_type": error_type,
        "remaining_val1_bias_at_070": remaining,
        "material_families": [r["family_id"] for r in material],
        "ranked": ranked,
        "evidence_required_to_open_parameters": evidence_to_open[rec],
        "do_not": [
            "Do not sweep MATCHUP_RESPONSE below 0.70.",
            "Do not write production constants.",
            "Do not unseal 2025 or use 2026.",
            "Do not open PLAY or Line Curve.",
        ],
    }


def run_component_attribution(
    *,
    cache_dir=None,
    lake_only: bool = True,
) -> Dict[str, Any]:
    assert_frozen_priors()
    refuse_sealed_or_confirm(LEGAL_SEASONS)
    if QB_FEATURE_CONTRACT_VERSION != "cfb-qb-feature-v1":
        raise FrozenScoringError("qb feature contract drifted")

    bundle = load_legal_scoring_bundle(cache_dir=cache_dir, lake_only=lake_only)
    lake_mounted = all(
        (bundle.get("lake_locate") or {}).get(str(season), {}).get("mounted")
        for season in LEGAL_SEASONS
    )
    if not lake_mounted:
        gate = decide_attribution(
            lake_mounted=False,
            sanity={"ok": False, "why": ["lake not mounted"]},
            panel_140=[],
            panel_070=[],
        )
        return _payload(bundle, [], [], gate, lake_mounted=False)

    panel_140: List[Dict[str, Any]] = []
    panel_070: List[Dict[str, Any]] = []

    ref140 = score_variant(
        bundle,
        lake_only=lake_only,
        matchup_response=None,
        score_overlay={},
        universe_kind=None,
        family_id="frozen_140",
        panel="reference_140",
    )
    panel_140.append(ref140)
    sanity = sanity_check_frozen_140((ref140.get("splits") or {}).get("val_1") or {})
    if not sanity.get("ok"):
        gate = decide_attribution(
            lake_mounted=True,
            sanity=sanity,
            panel_140=panel_140,
            panel_070=[],
        )
        return _payload(bundle, panel_140, panel_070, gate, lake_mounted=True)

    ref070 = score_variant(
        bundle,
        lake_only=lake_only,
        matchup_response=AUTHORIZED_FLOOR,
        score_overlay={},
        universe_kind=None,
        family_id="floor_070",
        panel="reference_070",
    )
    panel_070.append(ref070)

    for fam in FAMILIES:
        panel_140.append(
            score_variant(
                bundle,
                lake_only=lake_only,
                matchup_response=None,
                score_overlay=fam["score_overlay"],
                universe_kind=fam["universe"],
                family_id=fam["id"],
                panel="ablate_vs_140",
            )
        )
        panel_070.append(
            score_variant(
                bundle,
                lake_only=lake_only,
                matchup_response=AUTHORIZED_FLOOR,
                score_overlay=fam["score_overlay"],
                universe_kind=fam["universe"],
                family_id=fam["id"],
                panel="ablate_vs_070",
            )
        )

    gate = decide_attribution(
        lake_mounted=True,
        sanity=sanity,
        panel_140=panel_140,
        panel_070=panel_070,
    )
    return _payload(bundle, panel_140, panel_070, gate, lake_mounted=True)


def _payload(
    bundle: Mapping[str, Any],
    panel_140: Sequence[Mapping[str, Any]],
    panel_070: Sequence[Mapping[str, Any]],
    gate: Mapping[str, Any],
    *,
    lake_mounted: bool,
) -> Dict[str, Any]:
    return {
        "qb_feature_contract_version": QB_FEATURE_CONTRACT_VERSION,
        "matchup_response_frozen": P.MATCHUP_RESPONSE,
        "league_team_ppg_frozen": P.LEAGUE_TEAM_PPG,
        "engine_version": P.ENGINE_VERSION,
        "kill_switch": True,
        "opened_2025": False,
        "used_2026_for_fitting": False,
        "wrote_production_constant": False,
        "play": False,
        "swept_below_070": False,
        "lake_only": True,
        "lake_mounted": lake_mounted,
        "authoritative": {
            "pr_543": "frozen 1.40 scoring — RECALIBRATION JUSTIFIED",
            "pr_545": "MATCHUP_RESPONSE sweep — BROADER MODEL RECALIBRATION REQUIRED",
            "floor_070_not_a_coefficient": True,
            "published_val1_140": {
                "mae": 16.651,
                "bias": 10.100,
                "tail_n": 217,
            },
            "published_val1_070": {
                "mae": PUBLISHED_FLOOR_VAL1_MAE,
                "bias": PUBLISHED_FLOOR_VAL1_BIAS,
                "tail_n": PUBLISHED_FLOOR_VAL1_TAIL_N,
                "mean_abs_disagree": PUBLISHED_FLOOR_VAL1_DISAGREE,
            },
        },
        "totals_equation": totals_equation_doc(),
        "lake_locate": bundle.get("lake_locate"),
        "load": bundle.get("load"),
        "layer_a_talent": bundle.get("layer_a_talent"),
        "panel_140": list(panel_140),
        "panel_070": list(panel_070),
        "decision": gate,
        "reconstruction_limits": [
            "Score-time overlays only. Production MATCHUP_RESPONSE remains 1.40.",
            "0.70 is the authorized floor from PR #545, not an earned coefficient.",
            "One family at a time. No joint optimization.",
            "Layer A QB only. Layer B cast/recruiting held out at 50.",
            "Roster / units / coaching are league-average fills.",
            "Efficiency is prior-year cfb_ratings.",
            "HFA is curated 2026 venue proxies.",
            "2025 sealed. 2026 excluded. Actual outcomes are the objective.",
        ],
    }
