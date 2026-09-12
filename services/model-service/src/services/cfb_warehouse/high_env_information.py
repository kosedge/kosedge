"""Pregame information-sufficiency study for the CFB high-scoring tail.

Research only. Does not touch the scoring equation. A1 / E3 / C2 / A3 stay
frozen. The question is not “can we predict the total?” It is:

    Using only information legitimately available pregame in the v1
    reconstruction, can we distinguish HIGH_ENV games (actual total ≥ 68)
    from ordinary games at all?

If the top decile of a predeclared feature or small combination captures a
large share of the 140 Val-1 shootouts, the information exists and the
functional form is wrong. If discrimination is flat, v1 is data-insufficient
and we acquire data instead of torturing α.

2025 sealed. 2026 not in the loss. Board OFF. No PLAY. No production write.
Close is diagnostic only — not a v1 feature.
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from src.services.cfb_season_engine import priors as P
from src.services.cfb_season_engine.historical_calibration import fetch_sdv_csv
from src.services.cfb_season_engine.loaders import load_packaged_team_priors
from src.services.cfb_season_engine.qb_feature_contract import (
    QB_FEATURE_CONTRACT_VERSION,
)
from src.services.cfb_season_engine.team_features import (
    CFB_EDGE_BOARD_PUBLIC_ENABLED,
)
from src.services.cfb_warehouse.frozen_140_scoring import (
    LEGAL_SEASONS,
    SDV_CACHE,
    FrozenScoringError,
    _eligible,
    assert_frozen_priors,
    load_legal_scoring_bundle,
    refuse_sealed_or_confirm,
)
from src.services.cfb_warehouse.identity import resolve_team_code
from src.services.cfb_warehouse.matchup_architecture_holdout import (
    FROZEN_BASELINE,
    PROTOCOL_SPLITS,
    _split_rows,
)

# Locked before feature work. Do not edit after seeing scores.
HIGH_ENV_THRESHOLD = 68.0
N_DECILES = 10

# Predeclared gates. Not tuned on Val-1.
VAL1_AUC_MIN = 0.60
VAL1_TOP_DECILE_LIFT_MIN = 2.0
VAL0_AUC_MIN = 0.57
STRONG_CAPTURE = 0.40
MARKET_AUC_NOTE = 0.60

HALF_SLOPE = P.LEAGUE_TEAM_PPG / (2.0 * P.SCORE_TO_INDEX_DIVISOR)

ABSENT_FAMILIES: Tuple[Dict[str, str], ...] = (
    {
        "id": "pbp_explosiveness",
        "why": "cfb_ratings explosiveness is 50+0.15*(off−def), not PBP iso-explosiveness. Local PBP parquet is not mounted.",
    },
    {
        "id": "explosive_play_rate_allowed",
        "why": "No PBP / opponent-adjusted explosive-allowed series in the v1 cache.",
    },
    {
        "id": "red_zone_finishing",
        "why": "team_box has no red-zone attempts or TD rate.",
    },
    {
        "id": "havoc",
        "why": "No TFL / FF / PBU / havoc rate in cfb_ratings or team_box.",
    },
    {
        "id": "returning_production_real",
        "why": "Layer B roster is a league-average 50-fill on this reconstruction.",
    },
    {
        "id": "coaching_continuity_real",
        "why": "Historical coaching flags are not wired; every staff is assumed returning.",
    },
    {
        "id": "unit_grades_real",
        "why": "OL / skill / front seven / secondary are league-average 50-fills.",
    },
    {
        "id": "opponent_adjusted_current_season_epa",
        "why": "No week-indexed adj-EPA mart. Current-season evidence, if any, is raw box only.",
    },
)


def _f(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _mean(xs: Sequence[float]) -> Optional[float]:
    return statistics.fmean(xs) if xs else None


def roc_auc(scores: Sequence[Optional[float]], labels: Sequence[int]) -> Optional[float]:
    pairs = [
        (float(s), int(y))
        for s, y in zip(scores, labels)
        if s is not None and not math.isnan(float(s))
    ]
    pos = [s for s, y in pairs if y == 1]
    neg = [s for s, y in pairs if y == 0]
    if not pos or not neg:
        return None
    # Tie-aware Mann–Whitney / (n_pos * n_neg). O(n log n) via ranks.
    ordered = sorted(pairs, key=lambda t: t[0])
    rank_sum_pos = 0.0
    i = 0
    n = len(ordered)
    while i < n:
        j = i
        while j < n and ordered[j][0] == ordered[i][0]:
            j += 1
        avg_rank = 0.5 * ((i + 1) + j)  # 1-based ranks
        for k in range(i, j):
            if ordered[k][1] == 1:
                rank_sum_pos += avg_rank
        i = j
    u = rank_sum_pos - len(pos) * (len(pos) + 1) / 2.0
    return u / (len(pos) * len(neg))


def average_precision(
    scores: Sequence[Optional[float]], labels: Sequence[int]
) -> Optional[float]:
    pairs = [
        (float(s), int(y))
        for s, y in zip(scores, labels)
        if s is not None and not math.isnan(float(s))
    ]
    n_pos = sum(y for _s, y in pairs)
    if n_pos == 0 or n_pos == len(pairs):
        return None
    pairs.sort(key=lambda t: t[0], reverse=True)
    tp = 0
    seen = 0
    ap = 0.0
    for _s, y in pairs:
        seen += 1
        if y == 1:
            tp += 1
            ap += tp / seen
    return ap / n_pos


def decile_card(
    scores: Sequence[Optional[float]],
    labels: Sequence[int],
    *,
    n_bins: int = N_DECILES,
) -> Dict[str, Any]:
    pairs = [
        (float(s), int(y))
        for s, y in zip(scores, labels)
        if s is not None and not math.isnan(float(s))
    ]
    if len(pairs) < n_bins:
        return {"n": len(pairs), "bins": []}
    pairs.sort(key=lambda t: t[0])
    n = len(pairs)
    n_pos = sum(y for _s, y in pairs)
    prev = n_pos / n if n else None
    bins: List[Dict[str, Any]] = []
    captured = 0
    for b in range(n_bins):
        lo = int(round(b * n / n_bins))
        hi = int(round((b + 1) * n / n_bins))
        chunk = pairs[lo:hi]
        hits = sum(y for _s, y in chunk)
        captured_from_top = None
        rate = hits / len(chunk) if chunk else None
        bins.append(
            {
                "decile": b + 1,
                "n": len(chunk),
                "high_env_n": hits,
                "high_env_rate": rate,
                "lift_vs_prevalence": (
                    None if not prev or rate is None else rate / prev
                ),
                "mean_score": _mean([s for s, _y in chunk]),
            }
        )
    # capture from the top (decile 10 down)
    top_to_bottom = list(reversed(bins))
    running = 0
    for row in top_to_bottom:
        running += int(row["high_env_n"])
        row["high_env_share_from_top"] = (running / n_pos) if n_pos else None
    top = bins[-1] if bins else {}
    return {
        "n": n,
        "n_pos": n_pos,
        "prevalence": prev,
        "top_decile_n": top.get("n"),
        "top_decile_high_env_n": top.get("high_env_n"),
        "top_decile_rate": top.get("high_env_rate"),
        "top_decile_lift": top.get("lift_vs_prevalence"),
        "top_decile_capture": (
            (int(top.get("high_env_n") or 0) / n_pos) if n_pos else None
        ),
        "bins": bins,
    }


def _pct_ranks(values: Sequence[Optional[float]]) -> List[Optional[float]]:
    indexed = [
        (i, float(v))
        for i, v in enumerate(values)
        if v is not None and not math.isnan(float(v))
    ]
    out: List[Optional[float]] = [None] * len(values)
    if not indexed:
        return out
    indexed.sort(key=lambda t: t[1])
    n = len(indexed)
    i = 0
    while i < n:
        j = i
        while j < n and indexed[j][1] == indexed[i][1]:
            j += 1
        rank = 0.5 * (i + j - 1) / max(1, n - 1) if n > 1 else 0.5
        for k in range(i, j):
            out[indexed[k][0]] = rank
        i = j
    return out


def _parse_eff(text: Any) -> Optional[float]:
    if text is None:
        return None
    raw = str(text)
    if "-" not in raw:
        return _f(raw)
    left, right = raw.split("-", 1)
    den = _f(right)
    num = _f(left)
    if num is None or not den:
        return None
    return num / den


def _parse_clock(text: Any) -> Optional[float]:
    if text is None or text == "":
        return None
    raw = str(text)
    if ":" not in raw:
        return _f(raw)
    mm, ss = raw.split(":", 1)
    mins = _f(mm)
    secs = _f(ss)
    if mins is None or secs is None:
        return None
    return mins + secs / 60.0


def _team_id_map(season: int, cache_dir: Path) -> Dict[str, str]:
    box = fetch_sdv_csv(
        "espn_cfb_team_box",
        f"team_box_{int(season)}.csv.gz",
        cache_dir=cache_dir,
    )
    known = load_packaged_team_priors().get("teams") or {}
    out: Dict[str, str] = {}
    for row in box:
        code = resolve_team_code(
            abbr=row.get("team_abbreviation", ""),
            name=row.get("team_name", ""),
            known_codes=known,
        )
        if code:
            out[str(row["team_id"])] = code
    return out


def load_ratings_extras(
    season_prior: int, *, cache_dir: Path
) -> Dict[str, Dict[str, float]]:
    refuse_sealed_or_confirm([season_prior + 1])
    tid_map = _team_id_map(season_prior, cache_dir)
    rows = fetch_sdv_csv(
        "cfb_ratings", f"cfb_ratings_{int(season_prior)}.csv", cache_dir=cache_dir
    )
    out: Dict[str, Dict[str, float]] = {}
    for row in rows:
        code = tid_map.get(str(row.get("team_id") or ""))
        if not code:
            continue
        parsed = {
            "adj_off_epa": _f(row.get("adj_off_epa")),
            "adj_def_epa": _f(row.get("adj_def_epa")),
            "adj_st_epa": _f(row.get("adj_st_epa")),
            "adj_net": _f(row.get("adj_net")),
            "fei_off": _f(row.get("fei_off")),
            "fei_def": _f(row.get("fei_def")),
            "off_pace": _f(row.get("off_pace")),
        }
        out[code] = {k: v for k, v in parsed.items() if v is not None}
    return out


def load_prior_env(
    season_prior: int, *, cache_dir: Path
) -> Dict[str, Dict[str, float]]:
    """Season-Y−1 FBS–FBS scoring environment. Never reads season Y."""
    refuse_sealed_or_confirm([season_prior + 1])
    tid_map = _team_id_map(season_prior, cache_dir)
    sched = fetch_sdv_csv(
        "espn_cfb_schedules",
        f"cfb_schedule_{int(season_prior)}.csv.gz",
        cache_dir=cache_dir,
    )
    box = fetch_sdv_csv(
        "espn_cfb_team_box",
        f"team_box_{int(season_prior)}.csv.gz",
        cache_dir=cache_dir,
    )
    games_by_id: Dict[str, Dict[str, Any]] = {}
    for row in sched:
        gid = str(row.get("game_id") or "")
        hid = tid_map.get(str(row.get("home_id") or ""))
        aid = tid_map.get(str(row.get("away_id") or ""))
        hs = _f(row.get("home_score"))
        aws = _f(row.get("away_score"))
        if not gid or hid is None or aid is None or hs is None or aws is None:
            continue
        games_by_id[gid] = {
            "home": hid,
            "away": aid,
            "home_score": hs,
            "away_score": aws,
            "total": hs + aws,
            "week": _f(row.get("week")),
        }
    box_by: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in box:
        gid = str(row.get("game_id") or "")
        code = tid_map.get(str(row.get("team_id") or ""))
        if not gid or not code:
            continue
        rush = _f(row.get("rushingAttempts")) or 0.0
        # completionAttempts is "21/39"
        pass_att = None
        ca = str(row.get("completionAttempts") or "")
        if "/" in ca:
            pass_att = _f(ca.split("/")[-1])
        plays = rush + (pass_att or 0.0)
        box_by[(gid, code)] = {
            "plays": plays,
            "ypp": _f(row.get("yardsPerPass")),
            "ypr": _f(row.get("yardsPerRushAttempt")),
            "turnovers": _f(row.get("turnovers")),
            "third": _parse_eff(row.get("thirdDownEff")),
            "poss": _parse_clock(row.get("possessionTime")),
        }
    acc: Dict[str, Dict[str, List[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for gid, g in games_by_id.items():
        for side, opp, pf, pa in (
            ("home", "away", g["home_score"], g["away_score"]),
            ("away", "home", g["away_score"], g["home_score"]),
        ):
            code = g[side]
            acc[code]["pf"].append(float(pf))
            acc[code]["pa"].append(float(pa))
            acc[code]["total"].append(float(g["total"]))
            acc[code]["high"].append(1.0 if g["total"] >= HIGH_ENV_THRESHOLD else 0.0)
            bx = box_by.get((gid, code))
            if bx:
                if bx.get("plays"):
                    acc[code]["plays"].append(float(bx["plays"]))
                if bx.get("ypp") is not None:
                    acc[code]["ypp"].append(float(bx["ypp"]))
                if bx.get("turnovers") is not None:
                    acc[code]["to"].append(float(bx["turnovers"]))
                if bx.get("third") is not None:
                    acc[code]["third"].append(float(bx["third"]))
    out: Dict[str, Dict[str, float]] = {}
    for code, cols in acc.items():
        out[code] = {
            "mean_total": float(statistics.fmean(cols["total"])),
            "high_env_rate": float(statistics.fmean(cols["high"])),
            "mean_pf": float(statistics.fmean(cols["pf"])),
            "n": float(len(cols["total"])),
        }
        if cols["plays"]:
            out[code]["mean_plays"] = float(statistics.fmean(cols["plays"]))
        if cols["ypp"]:
            out[code]["mean_ypp"] = float(statistics.fmean(cols["ypp"]))
        if cols["to"]:
            out[code]["mean_to"] = float(statistics.fmean(cols["to"]))
        if cols["third"]:
            out[code]["mean_third"] = float(statistics.fmean(cols["third"]))
    return out


def load_current_env(
    season: int, *, cache_dir: Path
) -> Dict[Tuple[str, int], Dict[str, float]]:
    """Same-season box/schedule before week W. Key = (code, week) using weeks < W.

    Not a v1 feature. Week-0 freeze has none of this. Evaluated separately.
    """
    refuse_sealed_or_confirm([season])
    tid_map = _team_id_map(season, cache_dir)
    sched = fetch_sdv_csv(
        "espn_cfb_schedules",
        f"cfb_schedule_{int(season)}.csv.gz",
        cache_dir=cache_dir,
    )
    by_team: Dict[str, List[Tuple[int, float, float]]] = defaultdict(list)
    for row in sched:
        hid = tid_map.get(str(row.get("home_id") or ""))
        aid = tid_map.get(str(row.get("away_id") or ""))
        week = _f(row.get("week"))
        hs = _f(row.get("home_score"))
        aws = _f(row.get("away_score"))
        if hid is None or aid is None or week is None or hs is None or aws is None:
            continue
        w = int(week)
        total = hs + aws
        by_team[hid].append((w, total, hs))
        by_team[aid].append((w, total, aws))
    out: Dict[Tuple[str, int], Dict[str, float]] = {}
    for code, games in by_team.items():
        games.sort()
        for w in range(1, 15):
            prior = [g for g in games if g[0] < w]
            if len(prior) < 2:
                continue
            totals = [g[1] for g in prior]
            out[(code, w)] = {
                "n": float(len(prior)),
                "mean_total": float(statistics.fmean(totals)),
                "high_env_rate": float(
                    statistics.fmean(
                        [1.0 if t >= HIGH_ENV_THRESHOLD else 0.0 for t in totals]
                    )
                ),
                "mean_pf": float(statistics.fmean([g[2] for g in prior])),
            }
    return out


def _state_feats(state) -> Dict[str, Optional[float]]:
    eff = state.efficiency
    qb = state.qb
    roster = state.roster
    groups = state.groups
    hf = state.home_field
    return {
        "off_eff": float(eff.off_eff) if eff else None,
        "def_eff": float(eff.def_eff) if eff else None,
        "explosiveness": float(eff.explosiveness) if eff else None,
        "success_off": float(eff.success_off) if eff else None,
        "offense_index": float(state.offense_index),
        "defense_index": float(state.defense_index),
        "pace_factor": float(state.pace_factor),
        "pass_rate_bias": float(state.pass_rate_bias),
        "qb_talent": float(qb.qb_talent) if qb else None,
        "exp_starts": float(qb.experience_starts) if qb else None,
        "portal": 1.0 if qb and qb.qb_class == "portal" else 0.0,
        "returning_production": float(roster.returning_production) if roster else None,
        "ol": float(groups.ol) if groups else None,
        "hfa_env": float(hf.env_score) if hf else None,
    }


def _pair(a: Optional[float], b: Optional[float], fn) -> Optional[float]:
    if a is None or b is None:
        return None
    return fn(float(a), float(b))


def extract_game_features(
    raw: Mapping[str, Any],
    *,
    universes: Mapping[int, Any],
    ratings: Mapping[int, Mapping[str, Mapping[str, float]]],
    prior_env: Mapping[int, Mapping[str, Mapping[str, float]]],
    current_env: Mapping[int, Mapping[Tuple[str, int], Mapping[str, float]]],
    layer_a: Mapping[int, Mapping[str, Any]],
) -> Optional[Dict[str, Any]]:
    season = int(raw["season"])
    week = int(raw["week"])
    home = str(raw["home_team_id"])
    away = str(raw["away_team_id"])
    universe = universes.get(season)
    if universe is None or home not in universe.teams or away not in universe.teams:
        return None
    hs = raw.get("home_score")
    aws = raw.get("away_score")
    if hs is None or aws is None:
        return None
    actual_total = float(int(hs) + int(aws))
    h = _state_feats(universe.teams[home])
    a = _state_feats(universe.teams[away])
    hr = (ratings.get(season - 1) or {}).get(home) or {}
    ar = (ratings.get(season - 1) or {}).get(away) or {}
    hp = (prior_env.get(season - 1) or {}).get(home) or {}
    ap = (prior_env.get(season - 1) or {}).get(away) or {}
    hc = (current_env.get(season) or {}).get((home, week)) or {}
    ac = (current_env.get(season) or {}).get((away, week)) or {}
    hla = ((layer_a.get(season) or {}).get("teams") or {}).get(home) or {}
    ala = ((layer_a.get(season) or {}).get("teams") or {}).get(away) or {}

    def _ypa(row: Mapping[str, Any]) -> Optional[float]:
        att = _f(row.get("pass_attempts_prior"))
        yds = _f(row.get("pass_yards_prior"))
        if not att or yds is None:
            return None
        return yds / att

    e3_home = None
    e3_away = None
    a1_home = None
    a1_away = None
    if None not in (h["off_eff"], a["def_eff"], a["off_eff"], h["def_eff"]):
        # Frozen identities, not a new coefficient. Index clamp ignored so
        # the proxy matches the raw-efficiency research path.
        h_off_idx = 1.0 + (float(h["off_eff"]) - 50.0) / P.SCORE_TO_INDEX_DIVISOR
        a_def_idx = 1.0 + (float(a["def_eff"]) - 50.0) / P.SCORE_TO_INDEX_DIVISOR
        a_off_idx = 1.0 + (float(a["off_eff"]) - 50.0) / P.SCORE_TO_INDEX_DIVISOR
        h_def_idx = 1.0 + (float(h["def_eff"]) - 50.0) / P.SCORE_TO_INDEX_DIVISOR
        e3_home = P.LEAGUE_TEAM_PPG * (h_off_idx / max(0.50, a_def_idx))
        e3_away = P.LEAGUE_TEAM_PPG * (a_off_idx / max(0.50, h_def_idx))
        a1_home = P.LEAGUE_TEAM_PPG + HALF_SLOPE * (
            float(h["off_eff"]) - 50.0
        ) + HALF_SLOPE * (50.0 - float(a["def_eff"]))
        a1_away = P.LEAGUE_TEAM_PPG + HALF_SLOPE * (
            float(a["off_eff"]) - 50.0
        ) + HALF_SLOPE * (50.0 - float(h["def_eff"]))

    feats: Dict[str, Optional[float]] = {
        "sum_off_eff": _pair(h["off_eff"], a["off_eff"], lambda x, y: x + y),
        "max_off_eff": _pair(h["off_eff"], a["off_eff"], max),
        "min_off_eff": _pair(h["off_eff"], a["off_eff"], min),
        "sum_def_susc": _pair(
            h["def_eff"], a["def_eff"], lambda x, y: (100.0 - x) + (100.0 - y)
        ),
        "min_def_eff": _pair(h["def_eff"], a["def_eff"], min),
        "max_off_minus_opp_def": _pair(
            _pair(h["off_eff"], a["def_eff"], lambda o, d: o - d),
            _pair(a["off_eff"], h["def_eff"], lambda o, d: o - d),
            max,
        ),
        "product_mismatch": _pair(
            _pair(h["off_eff"], a["def_eff"], lambda o, d: o * (100.0 - d)),
            _pair(a["off_eff"], h["def_eff"], lambda o, d: o * (100.0 - d)),
            lambda x, y: x + y,
        ),
        "sum_qb_talent": _pair(h["qb_talent"], a["qb_talent"], lambda x, y: x + y),
        "max_qb_talent": _pair(h["qb_talent"], a["qb_talent"], max),
        "qb_portal_either": _pair(h["portal"], a["portal"], max),
        "sum_exp_starts": _pair(h["exp_starts"], a["exp_starts"], lambda x, y: x + y),
        "sum_offense_index": _pair(
            h["offense_index"], a["offense_index"], lambda x, y: x + y
        ),
        "pace_factor_mean": _pair(
            h["pace_factor"], a["pace_factor"], lambda x, y: 0.5 * (x + y)
        ),
        "pass_rate_bias_sum": _pair(
            h["pass_rate_bias"], a["pass_rate_bias"], lambda x, y: x + y
        ),
        "hfa_env": h["hfa_env"],
        "e3_proxy_total": _pair(e3_home, e3_away, lambda x, y: x + y),
        "a1_proxy_total": _pair(a1_home, a1_away, lambda x, y: x + y),
        "explosiveness_sum": _pair(
            h["explosiveness"], a["explosiveness"], lambda x, y: x + y
        ),
        "sum_off_pace": _pair(hr.get("off_pace"), ar.get("off_pace"), lambda x, y: x + y),
        "max_off_pace": _pair(hr.get("off_pace"), ar.get("off_pace"), max),
        "sum_fei_off": _pair(hr.get("fei_off"), ar.get("fei_off"), lambda x, y: x + y),
        "sum_fei_def": _pair(hr.get("fei_def"), ar.get("fei_def"), lambda x, y: x + y),
        "sum_adj_st": _pair(hr.get("adj_st_epa"), ar.get("adj_st_epa"), lambda x, y: x + y),
        "sum_adj_net": _pair(hr.get("adj_net"), ar.get("adj_net"), lambda x, y: x + y),
        "prior_mean_game_total": _pair(
            hp.get("mean_total"), ap.get("mean_total"), lambda x, y: 0.5 * (x + y)
        ),
        "prior_max_game_total": _pair(
            hp.get("mean_total"), ap.get("mean_total"), max
        ),
        "prior_high_env_rate_mean": _pair(
            hp.get("high_env_rate"), ap.get("high_env_rate"), lambda x, y: 0.5 * (x + y)
        ),
        "prior_high_env_rate_max": _pair(
            hp.get("high_env_rate"), ap.get("high_env_rate"), max
        ),
        "prior_mean_pf_sum": _pair(
            hp.get("mean_pf"), ap.get("mean_pf"), lambda x, y: x + y
        ),
        "prior_plays_sum": _pair(
            hp.get("mean_plays"), ap.get("mean_plays"), lambda x, y: x + y
        ),
        "prior_ypp_mean": _pair(
            hp.get("mean_ypp"), ap.get("mean_ypp"), lambda x, y: 0.5 * (x + y)
        ),
        "prior_to_sum": _pair(hp.get("mean_to"), ap.get("mean_to"), lambda x, y: x + y),
        "prior_third_mean": _pair(
            hp.get("mean_third"), ap.get("mean_third"), lambda x, y: 0.5 * (x + y)
        ),
        "qb_ypa_prior_sum": _pair(_ypa(hla), _ypa(ala), lambda x, y: x + y),
        "curr_mean_game_total": _pair(
            hc.get("mean_total"), ac.get("mean_total"), lambda x, y: 0.5 * (x + y)
        ),
        "curr_high_env_rate": _pair(
            hc.get("high_env_rate"), ac.get("high_env_rate"), lambda x, y: 0.5 * (x + y)
        ),
        "returning_production_sum": _pair(
            h["returning_production"],
            a["returning_production"],
            lambda x, y: x + y,
        ),
        "unit_ol_sum": _pair(h["ol"], a["ol"], lambda x, y: x + y),
        "close_total": _f(raw.get("close_total")),
        "pace_x_mismatch": None,
    }
    if feats["sum_off_pace"] is not None and feats["max_off_minus_opp_def"] is not None:
        feats["pace_x_mismatch"] = float(feats["sum_off_pace"]) * float(
            feats["max_off_minus_opp_def"]
        )
    return {
        "season": season,
        "week": week,
        "home": home,
        "away": away,
        "actual_total": actual_total,
        "high_env": 1 if actual_total >= HIGH_ENV_THRESHOLD else 0,
        "prior_season_used": season - 1,
        "current_season_n": _pair(hc.get("n"), ac.get("n"), lambda x, y: min(x, y)),
        "features": feats,
    }


# Predeclared feature card. direction: +1 means higher → more HIGH_ENV.
FEATURE_SPECS: Tuple[Dict[str, Any], ...] = (
    {"id": "sum_off_eff", "family": "v1_efficiency", "dir": 1, "role": "v1"},
    {"id": "max_off_eff", "family": "v1_efficiency", "dir": 1, "role": "v1"},
    {"id": "min_off_eff", "family": "v1_efficiency", "dir": 1, "role": "v1"},
    {"id": "sum_def_susc", "family": "v1_efficiency", "dir": 1, "role": "v1"},
    {"id": "min_def_eff", "family": "v1_efficiency", "dir": -1, "role": "v1"},
    {"id": "max_off_minus_opp_def", "family": "v1_interaction", "dir": 1, "role": "v1"},
    {"id": "product_mismatch", "family": "v1_interaction", "dir": 1, "role": "v1"},
    {"id": "sum_qb_talent", "family": "v1_qb", "dir": 1, "role": "v1"},
    {"id": "max_qb_talent", "family": "v1_qb", "dir": 1, "role": "v1"},
    {"id": "qb_portal_either", "family": "v1_qb", "dir": 1, "role": "v1"},
    {"id": "sum_exp_starts", "family": "v1_qb", "dir": 1, "role": "v1"},
    {"id": "qb_ypa_prior_sum", "family": "v1_qb", "dir": 1, "role": "v1"},
    {"id": "sum_offense_index", "family": "v1_compose", "dir": 1, "role": "v1"},
    {"id": "pace_factor_mean", "family": "v1_compose", "dir": 1, "role": "v1"},
    {"id": "pass_rate_bias_sum", "family": "v1_compose", "dir": 1, "role": "v1"},
    {"id": "hfa_env", "family": "v1_hfa", "dir": 1, "role": "v1"},
    {"id": "e3_proxy_total", "family": "frozen_identity", "dir": 1, "role": "v1"},
    {"id": "a1_proxy_total", "family": "frozen_identity", "dir": 1, "role": "v1"},
    {"id": "explosiveness_sum", "family": "v1_proxy", "dir": 1, "role": "v1"},
    {"id": "sum_off_pace", "family": "unused_ratings", "dir": 1, "role": "owned_unused"},
    {"id": "max_off_pace", "family": "unused_ratings", "dir": 1, "role": "owned_unused"},
    {"id": "sum_fei_off", "family": "unused_ratings", "dir": 1, "role": "owned_unused"},
    {"id": "sum_fei_def", "family": "unused_ratings", "dir": -1, "role": "owned_unused"},
    {"id": "sum_adj_st", "family": "unused_ratings", "dir": 1, "role": "owned_unused"},
    {"id": "sum_adj_net", "family": "unused_ratings", "dir": 1, "role": "owned_unused"},
    {"id": "prior_mean_game_total", "family": "prior_env", "dir": 1, "role": "owned_unused"},
    {"id": "prior_max_game_total", "family": "prior_env", "dir": 1, "role": "owned_unused"},
    {"id": "prior_high_env_rate_mean", "family": "prior_env", "dir": 1, "role": "owned_unused"},
    {"id": "prior_high_env_rate_max", "family": "prior_env", "dir": 1, "role": "owned_unused"},
    {"id": "prior_mean_pf_sum", "family": "prior_env", "dir": 1, "role": "owned_unused"},
    {"id": "prior_plays_sum", "family": "prior_box", "dir": 1, "role": "owned_unused"},
    {"id": "prior_ypp_mean", "family": "prior_box", "dir": 1, "role": "owned_unused"},
    {"id": "prior_to_sum", "family": "prior_box", "dir": 1, "role": "owned_unused"},
    {"id": "prior_third_mean", "family": "prior_box", "dir": 1, "role": "owned_unused"},
    {"id": "pace_x_mismatch", "family": "v1_interaction", "dir": 1, "role": "owned_unused"},
    {
        "id": "curr_mean_game_total",
        "family": "current_season_box",
        "dir": 1,
        "role": "current_not_v1",
    },
    {
        "id": "curr_high_env_rate",
        "family": "current_season_box",
        "dir": 1,
        "role": "current_not_v1",
    },
    {"id": "close_total", "family": "market_diagnostic", "dir": 1, "role": "diagnostic"},
    {
        "id": "returning_production_sum",
        "family": "constant_fill",
        "dir": 1,
        "role": "negative_control",
    },
    {"id": "unit_ol_sum", "family": "constant_fill", "dir": 1, "role": "negative_control"},
)

COMPOSITE_MEMBERS = (
    "sum_off_eff",
    "sum_def_susc",
    "sum_off_pace",
    "prior_mean_game_total",
)


def _oriented(values: Sequence[Optional[float]], direction: int) -> List[Optional[float]]:
    if direction >= 0:
        return list(values)
    return [None if v is None else -float(v) for v in values]


def score_feature(
    rows: Sequence[Mapping[str, Any]], spec: Mapping[str, Any]
) -> Dict[str, Any]:
    raw = [((r.get("features") or {}).get(spec["id"])) for r in rows]
    labels = [int(r["high_env"]) for r in rows]
    oriented = _oriented(raw, int(spec.get("dir") or 1))
    n_present = sum(1 for v in oriented if v is not None)
    auc = roc_auc(oriented, labels)
    prauc = average_precision(oriented, labels)
    dec = decile_card(oriented, labels)
    xs = [float(v) for v in oriented if v is not None]
    return {
        "id": spec["id"],
        "family": spec["family"],
        "role": spec["role"],
        "direction": int(spec.get("dir") or 1),
        "n": len(rows),
        "n_present": n_present,
        "coverage": n_present / len(rows) if rows else 0.0,
        "mean": _mean(xs),
        "sd": statistics.pstdev(xs) if len(xs) > 1 else None,
        "auc": auc,
        "pr_auc": prauc,
        "prevalence": dec.get("prevalence"),
        "top_decile_rate": dec.get("top_decile_rate"),
        "top_decile_lift": dec.get("top_decile_lift"),
        "top_decile_capture": dec.get("top_decile_capture"),
        "deciles": dec,
    }


def score_composite(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    labels = [int(r["high_env"]) for r in rows]
    ranks: List[List[Optional[float]]] = []
    for fid in COMPOSITE_MEMBERS:
        spec = next(s for s in FEATURE_SPECS if s["id"] == fid)
        raw = [((r.get("features") or {}).get(fid)) for r in rows]
        ranks.append(_pct_ranks(_oriented(raw, int(spec["dir"]))))
    combo: List[Optional[float]] = []
    for i in range(len(rows)):
        vals = [col[i] for col in ranks if col[i] is not None]
        combo.append(statistics.fmean(vals) if vals else None)
    dec = decile_card(combo, labels)
    return {
        "id": "rank_avg_env",
        "family": "predeclared_composite",
        "role": "v1_plus_owned_unused",
        "members": list(COMPOSITE_MEMBERS),
        "n": len(rows),
        "n_present": sum(1 for v in combo if v is not None),
        "auc": roc_auc(combo, labels),
        "pr_auc": average_precision(combo, labels),
        "prevalence": dec.get("prevalence"),
        "top_decile_rate": dec.get("top_decile_rate"),
        "top_decile_lift": dec.get("top_decile_lift"),
        "top_decile_capture": dec.get("top_decile_capture"),
        "deciles": dec,
        "note": "Equal-weight average of within-split percentile ranks. Not a fit.",
    }


def _split_card(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    labels = [int(r["high_env"]) for r in rows]
    n_pos = sum(labels)
    features = [score_feature(rows, spec) for spec in FEATURE_SPECS]
    composite = score_composite(rows)
    return {
        "n": len(rows),
        "high_env_n": n_pos,
        "prevalence": (n_pos / len(rows)) if rows else None,
        "mean_actual_total": _mean([float(r["actual_total"]) for r in rows]),
        "mean_actual_total_high": _mean(
            [float(r["actual_total"]) for r in rows if r["high_env"]]
        ),
        "mean_actual_total_other": _mean(
            [float(r["actual_total"]) for r in rows if not r["high_env"]]
        ),
        "features": features,
        "composite": composite,
    }


def leakage_audit(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    seasons = sorted({int(r["season"]) for r in rows})
    prior_ok = all(int(r["prior_season_used"]) == int(r["season"]) - 1 for r in rows)
    returning = [
        (r.get("features") or {}).get("returning_production_sum") for r in rows
    ]
    ol = [(r.get("features") or {}).get("unit_ol_sum") for r in rows]
    pace = [(r.get("features") or {}).get("pace_factor_mean") for r in rows]
    expl = [(r.get("features") or {}).get("explosiveness_sum") for r in rows]
    off = [(r.get("features") or {}).get("sum_off_eff") for r in rows]
    susc = [(r.get("features") or {}).get("sum_def_susc") for r in rows]
    # explosiveness should be a near-linear function of off−def on this reconstruction
    return {
        "seasons": seasons,
        "opened_2025": 2025 in seasons,
        "opened_2026": 2026 in seasons,
        "prior_season_always_ym1": prior_ok,
        "returning_production_sd": (
            statistics.pstdev([float(v) for v in returning if v is not None])
            if sum(1 for v in returning if v is not None) > 1
            else None
        ),
        "unit_ol_sd": (
            statistics.pstdev([float(v) for v in ol if v is not None])
            if sum(1 for v in ol if v is not None) > 1
            else None
        ),
        "pace_factor_sd": (
            statistics.pstdev([float(v) for v in pace if v is not None])
            if sum(1 for v in pace if v is not None) > 1
            else None
        ),
        "note": (
            "returning_production and unit_ol should be ~0 SD (50-fills). "
            "explosiveness is 50+0.15*(off−def) in ratings_to_efficiency_map, "
            "not a PBP measure. current-season features use week < game week only."
        ),
        "forbidden_seasons_present": [s for s in seasons if s in (2025, 2026)],
    }


def _passes_signal(feat: Mapping[str, Any], val0: Optional[Mapping[str, Any]]) -> bool:
    auc = feat.get("auc")
    lift = feat.get("top_decile_lift")
    if auc is None or lift is None:
        return False
    if float(auc) < VAL1_AUC_MIN or float(lift) < VAL1_TOP_DECILE_LIFT_MIN:
        return False
    if val0 is None or val0.get("auc") is None:
        return False
    return float(val0["auc"]) >= VAL0_AUC_MIN


def decide(cards: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    v1 = cards.get("val_1") or {}
    v0 = cards.get("val_0") or {}
    feats_v1 = {f["id"]: f for f in (v1.get("features") or [])}
    feats_v0 = {f["id"]: f for f in (v0.get("features") or [])}
    why: List[str] = [
        "HIGH_ENV = actual total ≥ 68 was locked before feature work.",
        "No scoring coefficient was touched. A1/E3/C2/A3 stay frozen.",
        "Close is diagnostic only.",
    ]
    legal_roles = {"v1", "owned_unused", "v1_plus_owned_unused"}
    signal: List[str] = []
    strong: List[str] = []
    for feat in list(v1.get("features") or []) + [v1.get("composite") or {}]:
        if not feat or feat.get("role") not in legal_roles:
            continue
        v0f = feats_v0.get(feat["id"]) if feat["id"] != "rank_avg_env" else (
            v0.get("composite") or {}
        )
        if _passes_signal(feat, v0f):
            signal.append(feat["id"])
            cap = feat.get("top_decile_capture")
            if cap is not None and float(cap) >= STRONG_CAPTURE:
                strong.append(feat["id"])
        why.append(
            f"{feat.get('id')}: Val-1 AUC={feat.get('auc')} lift={feat.get('top_decile_lift')} "
            f"capture={feat.get('top_decile_capture')} role={feat.get('role')}"
        )
    market = feats_v1.get("close_total") or {}
    market_auc = market.get("auc")
    if strong:
        decision = "SIGNAL_EXISTS_BUILD_NONLINEAR_LAYER"
        note = (
            "Top decile captures ≥40% of Val-1 HIGH_ENV games on a stable "
            "predeclared feature. Information exists. Functional form is the fork."
        )
    elif signal:
        decision = "WEAK_SIGNAL_INVESTIGATE_FEATURES"
        note = (
            "Some predeclared features clear the modest AUC/lift gate. Not "
            "the 40% capture fork. Do not promote. Investigate those features."
        )
    elif market_auc is not None and float(market_auc) >= MARKET_AUC_NOTE:
        decision = "DATA_INSUFFICIENT_INFORMATION_EXISTS_OUTSIDE_V1"
        note = (
            "v1 / owned-unused features cannot rank HIGH_ENV, but the close "
            "total can. The information exists in the world. It is not in v1."
        )
    else:
        decision = "DATA_INSUFFICIENT"
        note = (
            "No predeclared v1 or owned-unused feature ranks the 68+ tail. "
            "Do not torture α. Acquire data or accept that scoring-environment "
            "variance is mostly unpredictable from this reconstruction."
        )
    return {
        "decision": decision,
        "ship": False,
        "winner": None,
        "play": False,
        "signal_features": signal,
        "strong_features": strong,
        "market_auc_val_1": market_auc,
        "note": note,
        "why": why[:12] + [f"... {max(0, len(why) - 12)} more feature lines in JSON"],
        "why_full_n": len(why),
    }


def run_high_env_information(
    *,
    cache_dir=None,
    lake_only: bool = True,
) -> Dict[str, Any]:
    assert_frozen_priors()
    refuse_sealed_or_confirm(LEGAL_SEASONS)
    if QB_FEATURE_CONTRACT_VERSION != "cfb-qb-feature-v1":
        raise FrozenScoringError("qb feature contract drifted")
    if CFB_EDGE_BOARD_PUBLIC_ENABLED:
        raise FrozenScoringError("public board kill switch must stay off")
    if abs(float(P.MATCHUP_RESPONSE) - FROZEN_BASELINE) > 1e-9:
        raise FrozenScoringError("production MATCHUP_RESPONSE drifted from 1.40")

    cache = Path(cache_dir or SDV_CACHE)
    bundle = load_legal_scoring_bundle(cache_dir=cache, lake_only=lake_only)
    lake_mounted = all(
        (bundle.get("lake_locate") or {}).get(str(season), {}).get("mounted")
        for season in LEGAL_SEASONS
    )
    cards: Dict[str, Any] = {}
    audit = {"n": 0}
    rows: List[Dict[str, Any]] = []
    if lake_mounted:
        ratings = {
            season - 1: load_ratings_extras(season - 1, cache_dir=cache)
            for season in LEGAL_SEASONS
        }
        prior = {}
        for season in LEGAL_SEASONS:
            try:
                prior[season - 1] = load_prior_env(season - 1, cache_dir=cache)
            except Exception:
                prior[season - 1] = {}
        current = {
            season: load_current_env(season, cache_dir=cache) for season in LEGAL_SEASONS
        }
        layer_a = {}
        from src.services.cfb_warehouse.frozen_140_scoring import load_layer_a

        for season in LEGAL_SEASONS:
            layer_a[season] = load_layer_a(season)
        for raw in bundle["joined"]:
            if not _eligible(raw, lake_only=lake_only):
                continue
            feat = extract_game_features(
                raw,
                universes=bundle["universes"],
                ratings=ratings,
                prior_env=prior,
                current_env=current,
                layer_a=layer_a,
            )
            if feat is not None:
                rows.append(feat)
        for name in PROTOCOL_SPLITS:
            cards[name] = _split_card(_split_rows(rows, name))
        audit = leakage_audit(rows)

    gate = (
        decide(cards)
        if lake_mounted
        else {
            "decision": "INSUFFICIENT_EVIDENCE_DO_NOT_SHIP",
            "ship": False,
            "winner": None,
            "play": False,
            "why": ["odds lake not mounted"],
        }
    )
    return {
        "role": "high_env_information_sufficiency",
        "target": {
            "name": "HIGH_ENV",
            "rule": "actual_total >= 68",
            "threshold": HIGH_ENV_THRESHOLD,
            "locked_before_features": True,
        },
        "do_not_tune": True,
        "scoring_equation_frozen": True,
        "kill_switch": "OFF",
        "merge_532": False,
        "used_2026_for_fitting": False,
        "opened_2025": False,
        "wrote_production_coefficient": False,
        "play": False,
        "qb_feature_contract_version": QB_FEATURE_CONTRACT_VERSION,
        "matchup_response_frozen": P.MATCHUP_RESPONSE,
        "protocol_splits": PROTOCOL_SPLITS,
        "gates": {
            "val1_auc_min": VAL1_AUC_MIN,
            "val1_top_decile_lift_min": VAL1_TOP_DECILE_LIFT_MIN,
            "val0_auc_min": VAL0_AUC_MIN,
            "strong_capture": STRONG_CAPTURE,
        },
        "absent_families": list(ABSENT_FAMILIES),
        "predeclared_features": [
            {"id": s["id"], "family": s["family"], "role": s["role"], "dir": s["dir"]}
            for s in FEATURE_SPECS
        ],
        "composite_members": list(COMPOSITE_MEMBERS),
        "lake_mounted": lake_mounted,
        "n_eligible": len(rows),
        "leakage": audit,
        "splits": cards,
        "decision": gate,
        "reconstruction_limits": [
            "v1 varies prior-year adj EPA + Layer A QB. Roster/units/coaching are 50-fills.",
            "explosiveness is a linear proxy of off−def, not PBP.",
            "owned_unused columns come from the same cfb_ratings / prior-year box already in cache.",
            "current_season_box is not v1. It uses week < game week only.",
            "close_total is diagnostic. It is not a promotion feature.",
            "2025 sealed. 2026 W2 is not in this loss.",
        ],
    }
