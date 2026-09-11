#!/usr/bin/env python3
"""QB talent train/serve contract + term ablations (research only).

Falsifies: talent_from_qb_stats is a location shift vs the hist-cal
feature contract (league-avg QB @ 50 / unknown), not a W1/W2 tune.

Does not open 2025 residuals. Does not fit λ. Does not change
MATCHUP_RESPONSE or production coefficients.

Usage:
  PYTHONPATH=services/model-service \\
    python3 scripts/cfb/cfb_2026_qb_talent_contract_diagnostic.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
sys.path.insert(0, str(MS))
sys.path.insert(0, str(ROOT / "scripts" / "cfb"))

from src.services.cfb_season_engine import (  # noqa: E402
    project_game_preview,
    resolve_season_universe,
)
from src.services.cfb_season_engine import priors as P  # noqa: E402
from src.services.cfb_season_engine.fbs_universe import official_fbs_codes  # noqa: E402
from src.services.cfb_season_engine.power_sot import (  # noqa: E402
    sit_missing_power_from_sot_rows,
)
from src.services.cfb_season_engine.qb_situation import (  # noqa: E402
    apply_qb_situation_soft_ceiling,
    build_qb_situation,
    compute_qb_situation_index,
)
from src.services.cfb_season_engine.team_projection import (  # noqa: E402
    project_game_to_dict,
)
from src.services.cfb_season_engine.types import TeamProjectionState  # noqa: E402
from cfb_2026_roster_inflation_diagnostic import (  # noqa: E402
    SNAP,
    W1_CARD,
    W2_ODDS,
    OFFICIAL,
    POWER,
    _mean,
    _median,
    _sd,
    _mae,
    _rmse,
    _quantile,
    dist,
    compose_from,
    rebuild_qb,
    recruiting_channel_state,
    load_qb_stats,
    load_w1_totals,
    bucket_pred_total,
    slim_from_espn,
    attach_odds,
)
OUT_JSON = ROOT / "data/ops/cfb-2026-qb-talent-contract-20260911.json"
OUT_MD = ROOT / "data/ops/cfb-2026-qb-talent-contract-20260911.md"

ESTABLISHED_ATTEMPTS = 80  # same threshold as resolve_qb_talent stats path
FALSIFY_RESID = 3.0
RECRUITING_CONTROL_BAND = (8.0, 10.0)


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(v)))


def decompose_talent(
    attempts: int,
    yards: int,
    tds: int,
    *,
    is_portal: bool,
) -> Dict[str, Any]:
    """Exact live formula terms. No completion-rate input exists."""
    att = int(attempts or 0)
    yds = int(yards or 0)
    td = int(tds or 0)
    if att <= 0:
        default = 52.0 if is_portal else 48.0
        return {
            "attempts": att,
            "yards": yds,
            "tds": td,
            "ypa": None,
            "zero_attempt": True,
            "intercept": None,
            "attempt_term": 0.0,
            "attempt_term_raw": 0.0,
            "attempt_capped": False,
            "ypa_term": 0.0,
            "ypa_term_raw": 0.0,
            "ypa_capped": False,
            "td_term": 0.0,
            "td_term_raw": 0.0,
            "td_capped": False,
            "portal_bump": 0.0,
            "completion_term": None,
            "raw_pre_clamp": default,
            "talent_stats": default,
            "hit_floor_35": False,
            "hit_cap_96": False,
        }
    ypa = yds / max(att, 1)
    attempt_raw = att / 22.0
    ypa_raw = ypa * 1.1
    td_raw = td * 0.35
    attempt_term = min(22.0, attempt_raw)
    ypa_term = min(12.0, ypa_raw)
    td_term = min(10.0, td_raw)
    portal_bump = 2.0 if is_portal else 0.0
    raw = 42.0 + attempt_term + ypa_term + td_term + portal_bump
    talent = _clamp(raw, 35.0, 96.0)
    return {
        "attempts": att,
        "yards": yds,
        "tds": td,
        "ypa": round(ypa, 4),
        "zero_attempt": False,
        "intercept": 42.0,
        "attempt_term": round(attempt_term, 4),
        "attempt_term_raw": round(attempt_raw, 4),
        "attempt_capped": attempt_raw > 22.0 + 1e-9,
        "ypa_term": round(ypa_term, 4),
        "ypa_term_raw": round(ypa_raw, 4),
        "ypa_capped": ypa_raw > 12.0 + 1e-9,
        "td_term": round(td_term, 4),
        "td_term_raw": round(td_raw, 4),
        "td_capped": td_raw > 10.0 + 1e-9,
        "portal_bump": portal_bump,
        "completion_term": None,
        "raw_pre_clamp": round(raw, 4),
        "talent_stats": round(talent, 4),
        "hit_floor_35": raw < 35.0,
        "hit_cap_96": raw > 96.0,
    }


def talent_from_terms(
    parts: Mapping[str, Any],
    *,
    drop: Optional[str] = None,
    attempt_mode: str = "capped",
    intercept: Optional[float] = None,
    apply_clamp: bool = True,
    portal: bool = True,
    zero_att_default: Optional[float] = None,
) -> float:
    if parts.get("zero_attempt"):
        if zero_att_default is not None:
            return float(zero_att_default)
        return float(parts["talent_stats"])
    att_raw = float(parts["attempt_term_raw"])
    if attempt_mode == "zero":
        attempt_term = 0.0
    elif attempt_mode == "uncapped":
        attempt_term = att_raw
    elif attempt_mode == "old_phase1c":
        attempt_term = min(28.0, float(parts["attempts"]) / 18.0)
    else:
        attempt_term = min(22.0, att_raw)
    ypa_term = 0.0 if drop == "ypa" else min(12.0, float(parts["ypa_term_raw"]))
    td_term = 0.0 if drop == "td" else min(10.0, float(parts["td_term_raw"]))
    bump = float(parts["portal_bump"]) if portal else 0.0
    base = 42.0 if intercept is None else float(intercept)
    raw = base + attempt_term + ypa_term + td_term + bump
    return _clamp(raw, 35.0, 96.0) if apply_clamp else raw


def resolve_with_stats_talent(
    stats_talent: float,
    attempts: int,
    recruiting: float,
    *,
    force_stats: bool = False,
    force_blend: bool = False,
) -> float:
    att = int(attempts or 0)
    if force_stats:
        return _clamp(stats_talent, 0.0, 100.0)
    if force_blend or att < ESTABLISHED_ATTEMPTS:
        fallback = _clamp(float(recruiting), 0.0, 100.0)
        w = math.sqrt(att / float(ESTABLISHED_ATTEMPTS)) if att > 0 else 0.0
        if force_blend:
            return _clamp((1.0 - w) * fallback + w * stats_talent, 0.0, 100.0)
        return _clamp((1.0 - w) * fallback + w * stats_talent, 0.0, 100.0)
    return _clamp(stats_talent, 0.0, 100.0)


def location_shift(values: Sequence[float], *, median: float, target: float = 50.0) -> List[float]:
    """Rank-preserving location map: x' = x - (median - target). SD unchanged."""
    delta = float(median) - float(target)
    return [float(x) - delta for x in values]


def hist_qb_index() -> Dict[str, Any]:
    index, score, bd = compute_qb_situation_index(
        qb_class="unknown",
        qb_talent=50.0,
        supporting_cast=50.0,
    )
    return {
        "qb_class": "unknown",
        "qb_talent": 50.0,
        "supporting_cast": 50.0,
        "class_mult": P.QB_CLASS_OFFENSE_MULT["unknown"],
        "qb_situation_index": index,
        "qb_situation_score": score,
        "breakdown": bd,
        "note": (
            "build_historical_proxy_state hard-codes this payload. "
            "50 is a missing-value fill, not a sample mean of counting stats."
        ),
    }


def feature_contract_audit() -> Dict[str, Any]:
    hist = hist_qb_index()
    return {
        "calibration_event": {
            "writeup": "data/ops/cfb-historical-calibration-20260805.md",
            "engine": "cfb-season-engine-v0.8.1-hist-cal",
            "primary_fit_window": "2023–2024 closes (2025 was in the full-sample grade; this audit does not re-open 2025 residuals)",
            "identity_reconstruction": "league-avg roster / QB / units",
            "efficiency": "prior-year cfb_ratings adj EPA (not SP+)",
            "knobs_moved": {
                "MATCHUP_RESPONSE": {"before": 1.22, "after": 1.40, "why": "spreads compressed vs close under league-avg identity"},
                "LEAGUE_TEAM_PPG": {"before": 27.5, "after": 25.9},
                "WEIGHT_OFF_EFF": {"before": 0.28, "after": 0.34},
                "WEIGHT_QB_SITUATION": {"before": 0.26, "after": 0.24},
            },
            "explicit_limit": (
                "Hist-cal grades efficiency/HFA/PPG/matchup response — "
                "not a counterfactual of that year's portal/QB class."
            ),
        },
        "hist_cal_qb_payload": hist,
        "inputs": [
            {
                "input": "qb_talent",
                "hist_cal": "constant 50.0 (placeholder)",
                "live_2026": "talent_from_qb_stats(2025 att/yds/td) + low-sample recruiting blend",
                "same_definition": False,
                "same_units": "0–100 label only — hist 50 is a fill, live ~67 is a counting-stat composite",
                "same_centering": False,
                "same_missing_semantics": False,
                "same_temporal_cutoff": False,
                "same_distribution": False,
                "same_cap_floor": False,
                "hist_missing": "unavailable → 50",
                "live_missing": "att<=0 → 48 (or 52 if portal); att<80 → sqrt blend to recruiting",
                "live_temporal": "prior full season 2025 ESPN career-split attempts (not season-to-date 2026)",
            },
            {
                "input": "pass_attempts / yards / tds",
                "hist_cal": "not an input",
                "live_2026": "prior-year counting stats on ESPN-listed QB1",
                "same_definition": False,
                "same_units": "n/a vs attempts/yards/TDs",
                "same_centering": False,
                "same_missing_semantics": False,
                "same_temporal_cutoff": False,
                "same_distribution": False,
                "same_cap_floor": "n/a vs attempt term cap 22 @ 484 att; YPA cap 12; TD cap 10",
            },
            {
                "input": "completion_pct / efficiency EPA",
                "hist_cal": "not an input",
                "live_2026": "not an input (YPA is the only efficiency proxy)",
                "same_definition": True,
                "same_units": True,
                "note": "Neither path has completion rate. Do not invent one.",
            },
            {
                "input": "qb_class / class_mult",
                "hist_cal": "unknown → 0.92 for every team",
                "live_2026": "incumbent 1.06 / portal 0.95 / open 0.87 / freshman 0.79 from ESPN class+attempts",
                "same_definition": False,
                "same_centering": False,
                "same_missing_semantics": False,
                "same_temporal_cutoff": False,
                "same_distribution": False,
                "same_cap_floor": True,
            },
            {
                "input": "supporting_cast (OL/weapons)",
                "hist_cal": "50 / 50",
                "live_2026": "derived unit grades (recruiting-anchored ~60)",
                "same_definition": False,
                "same_centering": False,
            },
            {
                "input": "recruiting fallback",
                "hist_cal": "not used (talent never looks at recruiting)",
                "live_2026": "att<80 blends to recruiting_class_score (floor often 55)",
                "same_definition": False,
            },
            {
                "input": "expert override / W1 confirm",
                "hist_cal": "not used",
                "live_2026": "can change class / named QB1; talent still from pack stats",
                "same_definition": False,
            },
            {
                "input": "qb_situation_index downstream",
                "hist_cal": "≈0.92 for every team (unknown@50@cast50)",
                "live_2026": "mean ≈1.20, 58/136 at/above soft knee 1.25",
                "same_definition": True,
                "same_centering": False,
                "same_distribution": False,
                "note": "Same function, different inputs. MATCHUP_RESPONSE=1.40 was raised on the hist (narrow, 0.92) distribution.",
            },
        ],
        "verdict_preview": (
            "Train/serve skew on QB talent and class. Hist-cal never saw "
            "counting-stat talent. 50 meant missing, not league-average starter."
        ),
    }


def high_tail(rows: Sequence[Mapping[str, Any]], *, lo: float = 68.0) -> Dict[str, Any]:
    tail = [r for r in rows if float(r["model_total"]) >= lo]
    resid = [float(r["total_resid"]) for r in tail]
    return {
        "threshold": lo,
        "n": len(tail),
        "mean_resid": _mean(resid),
        "median_resid": _median(resid),
        "mae": _mae(resid),
    }


def summarize_rows(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    resid = [float(r["total_resid"]) for r in rows]
    totals = [float(r["model_total"]) for r in rows]
    by_bucket: Dict[str, List[float]] = {}
    for r in rows:
        by_bucket.setdefault(bucket_pred_total(float(r["model_total"])), []).append(
            float(r["total_resid"])
        )
    return {
        "n": len(rows),
        "mean_model_total": _mean(totals),
        "sd_model_total": _sd(totals),
        "p10_model_total": _quantile(totals, 0.10),
        "p50_model_total": _median(totals),
        "p90_model_total": _quantile(totals, 0.90),
        "mean_resid": _mean(resid),
        "median_resid": _median(resid),
        "mae": _mae(resid),
        "rmse": _rmse(resid),
        "high_total_tail_ge_68": high_tail(rows),
        "calibration_by_pred_bucket": {
            k: {"n": len(v), "mean_resid": _mean(v), "mae": _mae(v)}
            for k, v in sorted(by_bucket.items())
        },
    }


def score_variant(
    universe,
    live_states: Mapping[str, TeamProjectionState],
    official: Mapping[str, Any],
    w1: Mapping[str, float],
    w2_index: Mapping[str, Any],
    states: Mapping[str, TeamProjectionState],
) -> List[Dict[str, Any]]:
    rows = []
    for raw in official.get("games") or []:
        week = int(raw.get("week") or -1)
        if week not in (1, 2):
            continue
        if raw.get("fcs_home") or raw.get("fcs_away"):
            continue
        home = str(raw.get("home") or "").upper()
        away = str(raw.get("away") or "").upper()
        if home not in live_states or away not in live_states:
            continue
        pair = f"{away}@{home}"
        market = None
        if week == 2:
            odds = attach_odds(
                {
                    "home": home,
                    "away": away,
                    "home_name": raw.get("home_name"),
                    "away_name": raw.get("away_name"),
                },
                w2_index,
            )
            if odds and odds.get("best_total") is not None:
                market = float(odds["best_total"])
        else:
            market = w1.get(pair)
        if market is None:
            continue
        hs = states.get(home) or live_states[home]
        aws = states.get(away) or live_states[away]
        universe.teams[home] = hs
        universe.teams[away] = aws
        proj = project_game_to_dict(
            project_game_preview(
                universe,
                home_team=home,
                away_team=away,
                week=week,
                season=2026,
                neutral_site=bool(raw.get("neutral_site")),
            )
        )
        model_total = float(proj["expected_total"])
        rows.append(
            {
                "week": week,
                "pair": pair,
                "model_total": round(model_total, 4),
                "market_total": market,
                "total_resid": round(model_total - market, 4),
                "home_off": hs.offense_index,
                "away_off": aws.offense_index,
            }
        )
        universe.teams[home] = live_states[home]
        universe.teams[away] = live_states[away]
    return rows


def fbs_from_states(states: Mapping[str, TeamProjectionState]) -> Dict[str, Any]:
    official = official_fbs_codes()
    talents = []
    offs = []
    indexes = []
    for code, st in states.items():
        if code not in official:
            continue
        talents.append(float(st.qb.qb_talent))
        offs.append(float(st.offense_index))
        indexes.append(float(st.qb.qb_situation_index))
    return {
        "qb_talent": dist(talents),
        "qb_index": dist(indexes),
        "offense_index": dist(offs),
    }


def build_states_for_talent(
    live_states: Mapping[str, TeamProjectionState],
    talent_by_code: Mapping[str, float],
    *,
    qb_class: Optional[str] = None,
    class_mult_identity: bool = False,
) -> Dict[str, TeamProjectionState]:
    out = {}
    for code, live in live_states.items():
        talent = float(talent_by_code.get(code, live.qb.qb_talent))
        if class_mult_identity:
            cast = float(live.qb.supporting_cast)
            talent_index = 1.0 + (talent - 50.0) / 80.0
            cast_mult = 1.0 + P.QB_CAST_INDEX_SCALE * (cast - 50.0) / 50.0
            raw = talent_index * 1.0 * cast_mult
            index = apply_qb_situation_soft_ceiling(raw)
            qb = build_qb_situation(
                live.team,
                {
                    "qb_class": live.qb.qb_class,
                    "qb_talent": talent,
                    "ol_support": live.qb.ol_support,
                    "weapons_support": live.qb.weapons_support,
                    "qb_situation_index": index,
                    "starter_name": live.qb.starter_name,
                    "starter_key": live.qb.starter_key,
                    "experience_starts": live.qb.experience_starts,
                    "source": "research_class_mult_1",
                    "fidelity": live.qb.fidelity,
                },
            )
        else:
            qb = rebuild_qb(
                live.qb,
                talent=talent,
                qb_class=qb_class,
            )
        out[code] = compose_from(live, qb=qb)
    return out


def write_report(payload: Mapping[str, Any]) -> None:
    c = payload["conclusion"]
    lines = [
        "# 2026 QB talent train/serve contract (research diagnostic)",
        "",
        "**Date:** 2026-09-11  ",
        "**PR:** #539  ",
        "**Kill switch:** ON. 2025 sealed. No λ. No MATCHUP_RESPONSE change. No PLAY.",
        "",
        "## Conclusion",
        "",
        f"**{c['label']}**",
        "",
        c["text"],
        "",
        f"Pre-registered gate: attempt-term or rank-preserving location resid < +{FALSIFY_RESID} "
        "while recruiting_channel_50 stays ~+9.",
        "",
        f"- attempt_term_zero mean resid = **{c['attempt_resid']}** → gate "
        f"{'PASS' if c['attempt_gate'] else 'FAIL'}",
        f"- loc_shift_established_median_to_50 mean resid = **{c['location_resid']}** → gate "
        f"{'PASS' if c['location_gate'] else 'FAIL'}",
        f"- recruiting_channel_50 mean resid = **{c['recruiting_resid']}** → control "
        f"{'IN BAND' if c['recruiting_in_band'] else 'OUT OF BAND'}",
        f"- Mechanism survives this stage: **{c['mechanism_survives']}**",
        "",
        "## 1. Feature-contract audit",
        "",
        "When `MATCHUP_RESPONSE` was raised 1.22 → **1.40** (2026-08-05 hist-cal, "
        "primary window 2023–24), every team's QB payload was:",
        "",
        "```python",
        '{"qb_class": "unknown", "qb_talent": 50.0, "ol_support": 50.0, "weapons_support": 50.0}',
        "```",
        "",
        f"That produces `qb_situation_index` = **{payload['hist_qb']['qb_situation_index']}** "
        f"(class_mult {payload['hist_qb']['class_mult']}), not 1.00. "
        "50 is a **missing-value fill**. Counting stats were not an input. "
        "The writeup says so: grades efficiency/HFA/PPG/response, "
        "*not* that year's portal/QB class.",
        "",
        "| Input | Hist-cal (train) | Live 2026 (serve) | Same def? | Same center? | Same missing? | Same time? |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in payload["contract"]["inputs"]:
        lines.append(
            "| {input} | {hist} | {live} | {defn} | {cen} | {miss} | {time} |".format(
                input=row["input"],
                hist=str(row.get("hist_cal", ""))[:80],
                live=str(row.get("live_2026", ""))[:80],
                defn=row.get("same_definition"),
                cen=row.get("same_centering"),
                miss=row.get("same_missing_semantics"),
                time=row.get("same_temporal_cutoff"),
            )
        )
    sat = payload["saturation"]
    lines += [
        "",
        "Live formula (no completion term exists):",
        "",
        "```text",
        "if att<=0: 48 (52 if portal)",
        "else: clamp(42 + min(22, att/22) + min(12, ypa·1.1) + min(10, td·0.35) + 2·portal, 35, 96)",
        "if att<80: sqrt(att/80)·stats + (1-w)·recruiting",
        "```",
        "",
        "Saturation on official FBS (n={n}):".format(n=sat["n_fbs"]),
        "",
        f"- stats path (att≥{ESTABLISHED_ATTEMPTS}): {sat['n_established']}",
        f"- zero 2025 attempts: {sat['n_zero_attempt']}",
        f"- attempt term at cap 22 (≥484 att): {sat['n_attempt_capped']}",
        f"- YPA term at cap 12: {sat['n_ypa_capped']}",
        f"- TD term at cap 10: {sat['n_td_capped']}",
        f"- talent floor 35 / cap 96: {sat['n_floor_35']} / {sat['n_cap_96']}",
        f"- established-starter talent median: **{sat['established_median_talent']}** "
        f"(mean {sat['established_mean_talent']}, sd {sat['established_sd_talent']})",
        "",
        "A typical established starter is 42 + ~12–18 (attempts) + ~8 (YPA) + ~6 (TD) ≈ **67**. "
        "That is the formula's natural location, not a 2026-specific bug inside the arithmetic.",
        "",
        "## 2. Term-level ablations (confirmatory W1/W2 books)",
        "",
        "Not a fit. Deltas vs frozen. High-total tail = predicted total ≥ 68.",
        "",
        "| Variant | QB talent mean/sd/p50 | off-idx mean/sd | mean T | mean/med resid | MAE | tail n / mean resid |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name in payload["variant_order"]:
        s = payload["ablations"][name]
        td = s["team_dist"]["qb_talent"]
        od = s["team_dist"]["offense_index"]
        tail = s["board"]["high_total_tail_ge_68"]
        lines.append(
            "| {name} | {tm}/{tsd}/{tp} | {om}/{os} | {mt} | {mr}/{md} | {mae} | {tn} / {tr} |".format(
                name=name,
                tm=td.get("mean"),
                tsd=td.get("sd"),
                tp=td.get("p50"),
                om=od.get("mean"),
                os=od.get("sd"),
                mt=s["board"]["mean_model_total"],
                mr=s["board"]["mean_resid"],
                md=s["board"]["median_resid"],
                mae=s["board"]["mae"],
                tn=tail.get("n"),
                tr=tail.get("mean_resid"),
            )
        )
    lines += [
        "",
        "## 3. Before / after distributions (key variants)",
        "",
    ]
    for name in (
        "frozen",
        "attempt_term_zero",
        "loc_shift_established_median_to_50",
        "hist_contract_qb",
        "recruiting_channel_50",
    ):
        if name not in payload["ablations"]:
            continue
        s = payload["ablations"][name]
        lines.append(f"### {name}")
        lines.append("")
        for key in ("qb_talent", "offense_index"):
            d = s["team_dist"][key]
            lines.append(
                f"- {key}: mean {d['mean']} sd {d['sd']} p10 {d['p10']} p50 {d['p50']} p90 {d['p90']}"
            )
        lines.append("")
    lines += [
        "## 4. What this is not",
        "",
        "- Median→50 improving W1/W2 is **not** a ship criterion. If it only works "
        "because it restores the hist-cal *fill* on a path that now has real stats, "
        "that is pipeline mismatch evidence.",
        "- Not a λ / MATCHUP_RESPONSE / PLAY proposal.",
        "- 2025 residuals were not scored.",
        "",
        f"JSON: `{OUT_JSON.name}`",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    universe, meta = resolve_season_universe(
        season=2026, as_of_week=1, demo=True, session=None
    )
    official = json.loads(OFFICIAL.read_text(encoding="utf-8"))
    fbs = official_fbs_codes()
    required = set()
    for raw in official.get("games") or []:
        if int(raw.get("week") or -1) not in (1, 2):
            continue
        for side in (raw.get("home"), raw.get("away")):
            code = str(side or "").upper()
            if code in fbs:
                required.add(code)
    sit_missing_power_from_sot_rows(
        universe,
        json.loads(POWER.read_text(encoding="utf-8")).get("teams") or [],
        required=sorted(required),
        context="cfb_2026_qb_talent_contract_diagnostic",
    )
    live_states = {c: universe.teams[c] for c in universe.teams}
    qb_stats = load_qb_stats()
    snap = json.loads(SNAP.read_text(encoding="utf-8"))
    recruiting = {
        code: float((row.get("roster") or {}).get("recruiting_class_score") or 55.0)
        for code, row in (snap.get("teams") or {}).items()
    }
    w1 = load_w1_totals()
    w2 = slim_from_espn(W2_ODDS)

    parts_by: Dict[str, Dict[str, Any]] = {}
    live_talent: Dict[str, float] = {}
    established_talents: List[float] = []
    sat = {
        "n_fbs": 0,
        "n_established": 0,
        "n_zero_attempt": 0,
        "n_attempt_capped": 0,
        "n_ypa_capped": 0,
        "n_td_capped": 0,
        "n_floor_35": 0,
        "n_cap_96": 0,
    }
    for code, live in live_states.items():
        if code not in fbs:
            continue
        st = qb_stats.get(code) or {}
        parts = decompose_talent(
            int(st.get("pass_attempts_2025") or 0),
            int(st.get("pass_yards_2025") or 0),
            int(st.get("pass_td_2025") or 0),
            is_portal=bool(st.get("is_portal")),
        )
        parts_by[code] = parts
        live_talent[code] = float(live.qb.qb_talent)
        sat["n_fbs"] += 1
        if parts["zero_attempt"]:
            sat["n_zero_attempt"] += 1
        else:
            if parts["attempt_capped"]:
                sat["n_attempt_capped"] += 1
            if parts["ypa_capped"]:
                sat["n_ypa_capped"] += 1
            if parts["td_capped"]:
                sat["n_td_capped"] += 1
            if parts["hit_floor_35"]:
                sat["n_floor_35"] += 1
            if parts["hit_cap_96"]:
                sat["n_cap_96"] += 1
        if int(st.get("pass_attempts_2025") or 0) >= ESTABLISHED_ATTEMPTS:
            sat["n_established"] += 1
            established_talents.append(float(live.qb.qb_talent))

    est_med = _median(established_talents) or 67.0
    sat["established_median_talent"] = est_med
    sat["established_mean_talent"] = _mean(established_talents)
    sat["established_sd_talent"] = _sd(established_talents)
    all_med = _median(list(live_talent.values())) or 67.0

    def talents_for(variant: str) -> Dict[str, float]:
        out = {}
        for code, live in live_states.items():
            parts = parts_by.get(code)
            st = qb_stats.get(code) or {}
            rec = recruiting.get(code, 55.0)
            att = int(st.get("pass_attempts_2025") or 0)
            if parts is None:
                out[code] = float(live.qb.qb_talent)
                continue
            if variant == "frozen":
                out[code] = float(live.qb.qb_talent)
            elif variant == "attempt_term_zero":
                stats_t = talent_from_terms(parts, attempt_mode="zero")
                out[code] = resolve_with_stats_talent(stats_t, att, rec)
            elif variant == "attempt_term_uncapped":
                stats_t = talent_from_terms(parts, attempt_mode="uncapped")
                out[code] = resolve_with_stats_talent(stats_t, att, rec)
            elif variant == "ypa_term_zero":
                stats_t = talent_from_terms(parts, drop="ypa")
                out[code] = resolve_with_stats_talent(stats_t, att, rec)
            elif variant == "td_term_zero":
                stats_t = talent_from_terms(parts, drop="td")
                out[code] = resolve_with_stats_talent(stats_t, att, rec)
            elif variant == "portal_bump_zero":
                stats_t = talent_from_terms(parts, portal=False)
                out[code] = resolve_with_stats_talent(stats_t, att, rec)
            elif variant == "clamp_off":
                stats_t = talent_from_terms(parts, apply_clamp=False)
                out[code] = resolve_with_stats_talent(stats_t, att, rec)
            elif variant == "zero_att_default_50":
                stats_t = talent_from_terms(parts, zero_att_default=50.0)
                out[code] = resolve_with_stats_talent(stats_t, att, rec)
            elif variant == "lowsample_blend_off":
                stats_t = talent_from_terms(parts)
                out[code] = resolve_with_stats_talent(stats_t, att, rec, force_stats=True)
            elif variant == "hist_contract_qb":
                out[code] = 50.0
            else:
                out[code] = float(live.qb.qb_talent)
        if variant == "loc_shift_established_median_to_50":
            shifted = {}
            for code, t in live_talent.items():
                shifted[code] = t - (est_med - 50.0)
            return shifted
        if variant == "loc_shift_all_median_to_50":
            return {code: t - (all_med - 50.0) for code, t in live_talent.items()}
        return out

    variant_order = [
        "frozen",
        "attempt_term_zero",
        "attempt_term_uncapped",
        "ypa_term_zero",
        "td_term_zero",
        "portal_bump_zero",
        "clamp_off",
        "zero_att_default_50",
        "lowsample_blend_off",
        "class_to_unknown",
        "class_mult_identity",
        "loc_shift_established_median_to_50",
        "loc_shift_all_median_to_50",
        "hist_contract_qb",
        "recruiting_channel_50",
    ]

    ablations: Dict[str, Any] = {}
    for name in variant_order:
        if name == "recruiting_channel_50":
            states = {
                code: recruiting_channel_state(live, qb_stats)
                for code, live in live_states.items()
            }
        elif name == "class_to_unknown":
            states = build_states_for_talent(
                live_states, live_talent, qb_class="unknown"
            )
        elif name == "class_mult_identity":
            states = build_states_for_talent(
                live_states, live_talent, class_mult_identity=True
            )
        elif name == "hist_contract_qb":
            states = build_states_for_talent(
                live_states, talents_for(name), qb_class="unknown"
            )
        else:
            states = build_states_for_talent(live_states, talents_for(name))
        rows = score_variant(
            universe, live_states, official, w1, w2["by_key"], states
        )
        board = summarize_rows(rows)
        team_dist = fbs_from_states({c: s for c, s in states.items() if c in fbs})
        fr = ablations.get("frozen", {}).get("board") if name != "frozen" else None
        ablations[name] = {
            "board": board,
            "team_dist": team_dist,
            "delta_vs_frozen": None
            if fr is None
            else {
                "mean_resid": round(float(board["mean_resid"]) - float(fr["mean_resid"]), 4),
                "mae": round(float(board["mae"]) - float(fr["mae"]), 4),
            },
        }
        print(
            f"{name:36s} resid={board['mean_resid']} mae={board['mae']} "
            f"talent_mean={team_dist['qb_talent']['mean']} "
            f"tail={board['high_total_tail_ge_68']['mean_resid']}"
        )

    attempt_r = ablations["attempt_term_zero"]["board"]["mean_resid"]
    loc_r = ablations["loc_shift_established_median_to_50"]["board"]["mean_resid"]
    rec_r = ablations["recruiting_channel_50"]["board"]["mean_resid"]
    attempt_gate = attempt_r is not None and float(attempt_r) < FALSIFY_RESID
    location_gate = loc_r is not None and float(loc_r) < FALSIFY_RESID
    rec_in = rec_r is not None and RECRUITING_CONTROL_BAND[0] <= float(rec_r) <= RECRUITING_CONTROL_BAND[1]
    survives = (attempt_gate or location_gate) and rec_in

    if survives:
        label = "pipeline scale mismatch (train/serve skew)"
        text = (
            "Hist-cal trained MATCHUP_RESPONSE=1.40 and the QB offense weight on a "
            "universe where every QB was unknown@50 (index ≈0.92). Live 2026 serves "
            "prior-year counting stats whose natural center is ~67 (index ≈1.20). "
            "The attempt-term and/or rank-preserving location diagnostic dropped "
            "W1/W2 residual below +3 while recruiting_channel_50 stayed ~+9. "
            "That is the same formula on a different feature contract — not evidence "
            "that 1.40 should become 1.18, and not a ship of median→50."
        )
    elif rec_in and not (attempt_gate or location_gate):
        label = "insufficient evidence / mixed"
        text = (
            "Recruiting control stayed ~+9, but neither the attempt-term ablation "
            "nor the rank-preserving location map crossed the pre-registered +3 line. "
            "Do not treat median→50 as a coefficient. Revisit term definitions "
            "before touching MATCHUP_RESPONSE."
        )
    else:
        label = "insufficient evidence"
        text = (
            "The pre-registered gate did not fire cleanly. Do not change production "
            "coefficients. Do not interpret W1/W2 movement as a model improvement."
        )

    payload = {
        "ok": True,
        "research_only": True,
        "production_model_changed": False,
        "2025_opened": False,
        "lambda_fitted": False,
        "matchup_response_changed": False,
        "kill_switch": "CFB_EDGE_BOARD_PUBLIC_ENABLED=false",
        "universe_mode": meta.get("mode"),
        "pre_register": {
            "falsify_mean_resid_lt": FALSIFY_RESID,
            "recruiting_control_band": list(RECRUITING_CONTROL_BAND),
            "established_starter": f"prior-year attempts >= {ESTABLISHED_ATTEMPTS}",
            "location_map": "x' = x - (median_established - 50); rank and SD preserved",
        },
        "hist_qb": hist_qb_index(),
        "contract": feature_contract_audit(),
        "saturation": sat,
        "variant_order": variant_order,
        "ablations": ablations,
        "conclusion": {
            "label": label,
            "text": text,
            "attempt_resid": attempt_r,
            "location_resid": loc_r,
            "recruiting_resid": rec_r,
            "attempt_gate": attempt_gate,
            "location_gate": location_gate,
            "recruiting_in_band": rec_in,
            "mechanism_survives": survives,
        },
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_report(payload)
    print(json.dumps(payload["conclusion"], indent=2))
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
