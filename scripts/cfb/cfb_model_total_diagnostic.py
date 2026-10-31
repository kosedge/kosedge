#!/usr/bin/env python3
"""Research-only CFB model_total / spread-outlier diagnostic.

Reprojects the frozen 2026 compose path. Does NOT write KEI, change
priors, apply a totals guard, unsat PLAY, or flip the public kill switch.

Usage:
  PYTHONPATH=services/model-service \\
    python3 scripts/cfb/cfb_model_total_diagnostic.py
"""

from __future__ import annotations

import json
import math
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
sys.path.insert(0, str(MS))
sys.path.insert(0, str(ROOT / "scripts" / "cfb"))

from src.services.cfb_season_engine import (  # noqa: E402
    project_game_preview,
    project_game_to_dict,
    resolve_season_universe,
)
from src.services.cfb_season_engine import priors as P  # noqa: E402
from src.services.cfb_season_engine.conferences import conference_for  # noqa: E402
from src.services.cfb_season_engine.fbs_universe import official_fbs_codes  # noqa: E402
from src.services.cfb_season_engine.power_sot import (  # noqa: E402
    sit_missing_power_from_sot_rows,
)
from src.services.cfb_season_engine.team_features import (  # noqa: E402
    require_finite_power_index,
)
from src.services.cfb_season_engine.totals_guard_holdout import (  # noqa: E402
    matchup_inflation_on_sum,
)
from cfb_joined_residual_audit import attach_odds, slim_from_espn  # noqa: E402

KEI_PATH = ROOT / "apps/web/lib/data/cfb-kei-w0-w1-2026.json"
POWER_PATH = MS / "src/services/cfb_season_engine/data/cfb_power_sot_2026.json"
OFFICIAL_PATH = MS / "src/services/cfb_season_engine/data/cfb_official_schedule_2026.json"
W2_ODDS = ROOT / "data/ops/cfb-w2-espn-scoreboard-odds-20260911.json"
W1_CARD = ROOT / "data/ops/cfb-w1-handicap-card-20260831.json"
OUT_JSON = ROOT / "data/ops/cfb-model-diagnostic-20260911.json"
OUT_MD = ROOT / "data/ops/cfb-model-diagnostic-20260911.md"

P4 = frozenset({"SEC", "Big Ten", "Big 12", "ACC"})
G5 = frozenset(
    {
        "AAC",
        "American",
        "Mountain West",
        "MWC",
        "MAC",
        "Sun Belt",
        "CUSA",
        "Conference USA",
    }
)
SERVICE = frozenset({"ARMY", "NAVY", "AFA"})
OUTLIER_PAIRS = (
    ("UNLV", "UNT"),
    ("RUT", "BC"),
    ("USF", "ARMY"),
    ("WKU", "UGA"),
    ("LT", "LSU"),
    ("SDSU", "UCLA"),
)
NEUTRAL_TOTAL = 2.0 * float(P.LEAGUE_TEAM_PPG)  # 51.8


def _f(v: Any) -> Optional[float]:
    if v is None or v == "" or v == "—":
        return None
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    return None if n != n else n


def _mean(xs: Sequence[float]) -> Optional[float]:
    return None if not xs else round(sum(xs) / len(xs), 4)


def _median(xs: Sequence[float]) -> Optional[float]:
    return None if not xs else round(float(statistics.median(xs)), 4)


def _mae(xs: Sequence[float]) -> Optional[float]:
    return None if not xs else round(sum(abs(x) for x in xs) / len(xs), 4)


def _rmse(xs: Sequence[float]) -> Optional[float]:
    if not xs:
        return None
    return round(math.sqrt(sum(x * x for x in xs) / len(xs)), 4)


def _pct(n: int, d: int) -> Optional[float]:
    return None if d <= 0 else round(100.0 * n / d, 1)


def _bucket_total(v: Optional[float]) -> str:
    if v is None:
        return "na"
    if v < 48:
        return "<48"
    if v < 52:
        return "48-52"
    if v < 56:
        return "52-56"
    if v < 60:
        return "56-60"
    if v < 64:
        return "60-64"
    return ">=64"


def _bucket_pace(v: Optional[float]) -> str:
    if v is None:
        return "na"
    if v < 0.97:
        return "slow<0.97"
    if v <= 1.03:
        return "neutral"
    return "fast>1.03"


def _bucket_cont(v: Optional[float]) -> str:
    if v is None:
        return "na"
    if v < 40:
        return "low<40"
    if v < 60:
        return "mid40-60"
    return "high>=60"


def _tier(conf: str) -> str:
    if conf in P4:
        return "P4"
    if conf in G5:
        return "G5"
    if conf == "Independent":
        return "IND"
    return conf or "UNK"


def _mismatch_bucket(abs_spread: float) -> str:
    a = abs(float(abs_spread))
    if a < 10:
        return "peer<10"
    if a < 14:
        return "mod10-14"
    if a < 17:
        return "big14-17"
    return "cupcake>=17"


def parse_book_total(best: Any) -> Optional[float]:
    if best is None:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)", str(best))
    return float(m.group(1)) if m else None


def parse_card_spread_home(pair: str, best: Any) -> Optional[float]:
    """Parse 'MASS +29.5 (Hard Rock Bet)' on MASS@RUT → home −29.5."""
    if not best or "@" not in pair:
        return None
    away, home = pair.split("@", 1)
    m = re.search(r"([A-Za-z0-9:]+)\s+([+-]?\d+(?:\.\d+)?)", str(best))
    if not m:
        return None
    token = m.group(1).upper()
    pts = float(m.group(2))
    if token == home.upper():
        return pts
    if token == away.upper() or token.endswith(away.upper()):
        return -pts
    return None


def load_w1_card() -> Dict[str, Dict[str, Optional[float]]]:
    raw = json.loads(W1_CARD.read_text(encoding="utf-8"))
    out: Dict[str, Dict[str, Optional[float]]] = {}
    for row in raw.get("spreads") or []:
        pair = str(row.get("game") or "")
        if not pair or pair.startswith("FCS:"):
            continue
        out.setdefault(pair, {})["market_spread_home"] = parse_card_spread_home(
            pair, row.get("best")
        )
    for row in raw.get("totals") or []:
        pair = str(row.get("game") or "")
        if not pair or pair.startswith("FCS:"):
            continue
        out.setdefault(pair, {})["market_total"] = parse_book_total(row.get("best"))
    return out


def hydrate_power(universe, official: Dict[str, Any]) -> int:
    official_fbs = official_fbs_codes()
    required = set()
    for raw in official.get("games") or []:
        try:
            week = int(raw.get("week"))
        except (TypeError, ValueError):
            continue
        if week not in (0, 1, 2):
            continue
        for side in (raw.get("home"), raw.get("away")):
            code = str(side or "").upper()
            if code in official_fbs:
                required.add(code)
    pack = json.loads(POWER_PATH.read_text(encoding="utf-8"))
    return sit_missing_power_from_sot_rows(
        universe,
        pack.get("teams") or [],
        required=sorted(required),
        context="cfb_model_total_diagnostic",
    )


def reconstruct_side(diag: Dict[str, Any]) -> Dict[str, float]:
    """Rebuild one side's expected points from stored diagnostics."""
    ratio = float(diag["matchup_ratio"])
    response = float(diag["matchup_response"])
    matchup = ratio**response
    off = float(diag["offense_boost"])
    damp = float(diag["defense_dampen"])
    pace = float(diag["pace"])
    pre = float(diag["pre_clamp"])
    ppg = float(P.LEAGUE_TEAM_PPG)
    mult = ppg * matchup * off * damp * pace
    additive = pre - mult
    hfa = 0.0
    hfa_block = diag.get("hfa") or {}
    if isinstance(hfa_block, dict):
        hfa = float(hfa_block.get("hfa_points") or 0.0)
    coach = float(diag.get("coaching_net_adj") or 0.0)
    lo, hi = P.EXPECTED_POINTS_CLAMP
    clamped = max(lo, min(hi, pre))
    return {
        "matchup_factor": round(matchup, 4),
        "off_boost": round(off, 4),
        "def_dampen": round(damp, 4),
        "pace": round(pace, 4),
        "mult": round(mult, 4),
        "additive": round(additive, 4),
        "hfa": round(hfa, 4),
        "coach": round(coach, 4),
        "pre_clamp": round(pre, 4),
        "clamped": round(clamped, 4),
        "clamp_delta": round(clamped - pre, 4),
        "ppg_x_matchup": round(ppg * matchup, 4),
        "ppg_only": ppg,
    }


def neutralize_total(
    home_diag: Dict[str, Any],
    away_diag: Dict[str, Any],
    *,
    st_nudge: float,
    matchup: bool = True,
    off_boost: bool = True,
    def_dampen: bool = True,
    pace: bool = True,
    additive: bool = True,
) -> float:
    """Rebuild T with selected multiplicative/additive terms zeroed to 1 / 0."""

    def one(diag: Dict[str, Any]) -> float:
        ratio = float(diag["matchup_ratio"])
        response = float(diag["matchup_response"])
        m = (ratio**response) if matchup else 1.0
        off = float(diag["offense_boost"]) if off_boost else 1.0
        damp = float(diag["defense_dampen"]) if def_dampen else 1.0
        p = float(diag["pace"]) if pace else 1.0
        pre = float(diag["pre_clamp"])
        raw_m = float(P.LEAGUE_TEAM_PPG) * (ratio**response) * float(
            diag["offense_boost"]
        ) * float(diag["defense_dampen"]) * float(diag["pace"])
        add = (pre - raw_m) if additive else 0.0
        pre2 = float(P.LEAGUE_TEAM_PPG) * m * off * damp * p + add
        lo, hi = P.EXPECTED_POINTS_CLAMP
        return max(lo, min(hi, pre2))

    return one(home_diag) + one(away_diag) + float(st_nudge)


def team_identity(universe, code: str) -> Dict[str, Any]:
    st = universe.teams[code]
    roster = st.roster
    qb = st.qb
    groups = st.groups
    eff = st.efficiency
    coach = st.coaching
    return {
        "conference": conference_for(code, universe.conferences),
        "offense_index": st.offense_index,
        "defense_index": st.defense_index,
        "power_index": round(0.5 * (st.offense_index + st.defense_index), 4),
        "pace_factor": st.pace_factor,
        "early_u": st.early_season_uncertainty,
        "source": st.source,
        "roster_strength": None if roster is None else round(float(roster.roster_strength), 2),
        "continuity": None if roster is None else round(float(roster.continuity_score), 2),
        "experience": None if roster is None else round(float(roster.experience_index), 2),
        "qb_index": None if qb is None else round(float(qb.qb_situation_index), 4),
        "qb_class": None if qb is None else qb.qb_class,
        "qb_name": None if qb is None else qb.starter_name,
        "off_eff": None if eff is None else round(float(eff.off_eff), 2),
        "def_eff": None if eff is None else round(float(eff.def_eff), 2),
        "sp_plus": None if eff is None else round(float(eff.sp_plus), 2),
        "explosiveness": None if eff is None else round(float(eff.explosiveness), 2),
        "ol": None if groups is None else round(float(groups.ol), 1),
        "skill": None if groups is None else round(float(groups.skill), 1),
        "front_seven": None if groups is None else round(float(groups.front_seven), 1),
        "secondary": None if groups is None else round(float(groups.secondary), 1),
        "new_hc": bool(coach.new_hc) if coach else False,
        "new_oc": bool(coach.new_oc) if coach else False,
        "new_dc": bool(coach.new_dc) if coach else False,
        "hfa_bucket": st.home_field.bucket if st.home_field else None,
        "hfa_points": None if not st.home_field else round(float(st.home_field.hfa_points), 2),
    }


def slice_table(rows: Sequence[Dict[str, Any]], key_fn) -> Dict[str, Any]:
    buckets: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        buckets[str(key_fn(r))].append(r)
    out = {}
    for k, grp in sorted(buckets.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        tot = [r["total_resid"] for r in grp if r.get("total_resid") is not None]
        spr = [r["spread_resid"] for r in grp if r.get("spread_resid") is not None]
        infl = [r["matchup_inflation"] for r in grp]
        out[k] = {
            "n": len(grp),
            "n_total": len(tot),
            "mean_total_resid": _mean(tot),
            "median_total_resid": _median(tot),
            "total_mae": _mae(tot),
            "mean_spread_resid": _mean(spr),
            "spread_mae": _mae(spr),
            "mean_matchup_inflation": _mean(infl),
            "mean_model_total": _mean([r["model_total"] for r in grp]),
            "mean_market_total": _mean(
                [r["market_total"] for r in grp if r.get("market_total") is not None]
            ),
        }
    return out


def main() -> int:
    universe, meta = resolve_season_universe(
        season=2026, as_of_week=1, demo=True, session=None
    )
    official = json.loads(OFFICIAL_PATH.read_text(encoding="utf-8"))
    filled = hydrate_power(universe, official)
    kei_pack = json.loads(KEI_PATH.read_text(encoding="utf-8"))
    w2_odds = slim_from_espn(W2_ODDS)
    w1_card = load_w1_card()

    # Verify kill switch files still hard-false (read-only check).
    public_src = (ROOT / "apps/web/lib/cfb-edge-board-public.ts").read_text(
        encoding="utf-8"
    )
    assert "export const CFB_EDGE_BOARD_PUBLIC_ENABLED = false;" in public_src

    rows: List[Dict[str, Any]] = []
    reconstruct_err = 0.0
    for raw in official.get("games") or []:
        try:
            week = int(raw.get("week"))
        except (TypeError, ValueError):
            continue
        if week not in (0, 1, 2):
            continue
        home = str(raw.get("home") or "").upper()
        away = str(raw.get("away") or "").upper()
        if raw.get("fcs_home") or raw.get("fcs_away"):
            continue
        if home.startswith("FCS:") or away.startswith("FCS:"):
            continue
        if home not in universe.teams or away not in universe.teams:
            continue
        # Fail closed — do not silently 1.0 hydrate.
        require_finite_power_index(
            universe.teams[home].offense_index, field="offense_index", team=home
        )
        require_finite_power_index(
            universe.teams[away].offense_index, field="offense_index", team=away
        )
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
        drivers = proj.get("drivers") or {}
        matchup = drivers.get("matchup") or {}
        home_diag = matchup.get("home_points_diag") or {}
        away_diag = matchup.get("away_points_diag") or {}
        st_nudge = float(matchup.get("st_total_nudge") or 0.0)
        home_rec = reconstruct_side(home_diag)
        away_rec = reconstruct_side(away_diag)
        model_total = float(proj["expected_total"])
        model_spread = float(proj["spread_home"])
        rebuilt = home_rec["clamped"] + away_rec["clamped"] + st_nudge
        reconstruct_err = max(reconstruct_err, abs(rebuilt - model_total))

        t_neutral, inflation = matchup_inflation_on_sum(
            model_total=model_total,
            home_diag=home_diag,
            away_diag=away_diag,
            league_ppg=float(P.LEAGUE_TEAM_PPG),
            points_clamp=P.EXPECTED_POINTS_CLAMP,
            st_nudge=st_nudge,
        )
        cf = {
            "actual": model_total,
            "matchup_off": neutralize_total(
                home_diag, away_diag, st_nudge=st_nudge, matchup=False
            ),
            "off_boost_off": neutralize_total(
                home_diag, away_diag, st_nudge=st_nudge, off_boost=False
            ),
            "def_dampen_off": neutralize_total(
                home_diag, away_diag, st_nudge=st_nudge, def_dampen=False
            ),
            "pace_off": neutralize_total(
                home_diag, away_diag, st_nudge=st_nudge, pace=False
            ),
            "additive_off": neutralize_total(
                home_diag, away_diag, st_nudge=st_nudge, additive=False
            ),
            "all_mult_off": neutralize_total(
                home_diag,
                away_diag,
                st_nudge=st_nudge,
                matchup=False,
                off_boost=False,
                def_dampen=False,
                pace=False,
            ),
        }
        pair = f"{away}@{home}"
        market_spread = None
        market_total = None
        market_src = None
        if week == 2:
            odds = attach_odds(
                {
                    "home": home,
                    "away": away,
                    "home_name": raw.get("home_name"),
                    "away_name": raw.get("away_name"),
                },
                w2_odds["by_key"],
            )
            if odds:
                market_spread = _f(odds.get("best_spread_home"))
                market_total = _f(odds.get("best_total"))
                market_src = "espn_dk_w2"
        elif week == 1:
            card = w1_card.get(pair) or {}
            market_spread = card.get("market_spread_home")
            market_total = card.get("market_total")
            market_src = "w1_handicap_card" if card else None

        home_id = team_identity(universe, home)
        away_id = team_identity(universe, away)
        home_conf = home_id["conference"]
        away_conf = away_id["conference"]
        total_resid = (
            None if market_total is None else round(model_total - market_total, 4)
        )
        spread_resid = (
            None if market_spread is None else round(model_spread - market_spread, 4)
        )
        kei_spread = None
        for kg in kei_pack.get("games") or []:
            if (
                str(kg.get("home") or "").upper() == home
                and str(kg.get("away") or "").upper() == away
                and int(kg.get("week") or -1) == week
            ):
                kei = kg.get("kei") or {}
                kei_spread = _f(kei.get("kei_spread_home"))
                break
        kei_spread_resid = (
            None
            if market_spread is None or kei_spread is None
            else round(kei_spread - market_spread, 4)
        )
        fav_flip = False
        if market_spread is not None and kei_spread is not None:
            if abs(market_spread) >= 0.5 and abs(kei_spread) >= 0.5:
                fav_flip = (market_spread > 0) != (kei_spread > 0)

        pace_mean = 0.5 * (
            float(home_diag.get("pace") or 1.0) + float(away_diag.get("pace") or 1.0)
        )
        cont_mean = None
        if home_id["continuity"] is not None and away_id["continuity"] is not None:
            cont_mean = 0.5 * (home_id["continuity"] + away_id["continuity"])
        off_mean = 0.5 * (home_id["offense_index"] + away_id["offense_index"])
        def_mean = 0.5 * (home_id["defense_index"] + away_id["defense_index"])

        rows.append(
            {
                "week": week,
                "pair": pair,
                "away": away,
                "home": home,
                "neutral_site": bool(raw.get("neutral_site")),
                "home_conf": home_conf,
                "away_conf": away_conf,
                "same_conf": home_conf == away_conf,
                "matchup_type": (
                    "service"
                    if home in SERVICE or away in SERVICE
                    else f"{_tier(away_conf)}@{_tier(home_conf)}"
                ),
                "model_total": round(model_total, 4),
                "model_spread_home": round(model_spread, 4),
                "kei_spread_home": kei_spread,
                "home_exp": float(proj["expected_home_score"]),
                "away_exp": float(proj["expected_away_score"]),
                "market_spread_home": market_spread,
                "market_total": market_total,
                "market_src": market_src,
                "total_resid": total_resid,
                "spread_resid": spread_resid,
                "kei_spread_resid": kei_spread_resid,
                "fav_flip": fav_flip,
                "st_nudge": round(st_nudge, 4),
                "matchup_inflation": round(inflation, 4),
                "total_neutral": round(t_neutral, 4),
                "home_rec": home_rec,
                "away_rec": away_rec,
                "counterfactual": {k: round(v, 4) for k, v in cf.items()},
                "home_id": home_id,
                "away_id": away_id,
                "pace_mean": round(pace_mean, 4),
                "continuity_mean": None if cont_mean is None else round(cont_mean, 2),
                "off_index_mean": round(off_mean, 4),
                "def_index_mean": round(def_mean, 4),
                "home_ratio": home_rec["matchup_factor"],
                "away_ratio": away_rec["matchup_factor"],
                "mean_matchup_factor": round(
                    0.5 * (home_rec["matchup_factor"] + away_rec["matchup_factor"]), 4
                ),
                "response": home_diag.get("matchup_response"),
                "mismatch_bucket": _mismatch_bucket(model_spread),
                "proj_total_bucket": _bucket_total(model_total),
                "mkt_total_bucket": _bucket_total(market_total),
                "pace_bucket": _bucket_pace(pace_mean),
                "continuity_bucket": _bucket_cont(cont_mean),
                "off_bucket": (
                    "hot>=1.15"
                    if off_mean >= 1.15
                    else ("mid" if off_mean >= 1.0 else "cool<1.0")
                ),
                "def_bucket": (
                    "strong>=1.15"
                    if def_mean >= 1.15
                    else ("mid" if def_mean >= 1.0 else "weak<1.0")
                ),
            }
        )

    joined = [r for r in rows if r.get("total_resid") is not None]
    w2 = [r for r in joined if r["week"] == 2]
    w1 = [r for r in joined if r["week"] == 1]

    # Fleet counterfactual: hold street fixed, zero one term.
    def fleet_cf(grp: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        if not grp:
            return {}
        street = [r["market_total"] for r in grp if r.get("market_total") is not None]
        if not street:
            return {}
        street_mean = sum(street) / len(street)
        out = {}
        for name in (
            "actual",
            "matchup_off",
            "off_boost_off",
            "def_dampen_off",
            "pace_off",
            "additive_off",
            "all_mult_off",
        ):
            xs = [r["counterfactual"][name] for r in grp]
            gap = sum(xs) / len(xs) - street_mean
            out[name] = {
                "mean_model": round(sum(xs) / len(xs), 3),
                "mean_gap_vs_street": round(gap, 3),
                "delta_from_actual_gap": round(
                    gap
                    - (
                        sum(r["counterfactual"]["actual"] for r in grp) / len(grp)
                        - street_mean
                    ),
                    3,
                ),
            }
        out["street_mean"] = round(street_mean, 3)
        out["n"] = len(grp)
        return out

    outliers = []
    for away, home in OUTLIER_PAIRS:
        hit = next((r for r in rows if r["away"] == away and r["home"] == home), None)
        if not hit:
            outliers.append({"pair": f"{away}@{home}", "missing": True})
            continue
        h = hit["home_id"]
        a = hit["away_id"]
        # Who the model likes vs market.
        model_home_fav = hit["model_spread_home"] < 0
        mkt_home_fav = (
            None if hit["market_spread_home"] is None else hit["market_spread_home"] < 0
        )
        # Feature deltas (home − away) that build the margin.
        outliers.append(
            {
                "pair": hit["pair"],
                "week": hit["week"],
                "model_spread_home": hit["model_spread_home"],
                "kei_spread_home": hit["kei_spread_home"],
                "market_spread_home": hit["market_spread_home"],
                "spread_resid_model": hit["spread_resid"],
                "spread_resid_kei": hit["kei_spread_resid"],
                "fav_flip": hit["fav_flip"],
                "model_total": hit["model_total"],
                "market_total": hit["market_total"],
                "total_resid": hit["total_resid"],
                "home_exp": hit["home_exp"],
                "away_exp": hit["away_exp"],
                "matchup_inflation": hit["matchup_inflation"],
                "home_matchup_factor": hit["home_rec"]["matchup_factor"],
                "away_matchup_factor": hit["away_rec"]["matchup_factor"],
                "home_hfa": hit["home_rec"]["hfa"],
                "home_coach": hit["home_rec"]["coach"],
                "away_coach": hit["away_rec"]["coach"],
                "model_home_favorite": model_home_fav,
                "market_home_favorite": mkt_home_fav,
                "deltas_home_minus_away": {
                    "offense_index": round(h["offense_index"] - a["offense_index"], 4),
                    "defense_index": round(h["defense_index"] - a["defense_index"], 4),
                    "power_index": round(h["power_index"] - a["power_index"], 4),
                    "off_eff": _safe_sub(h["off_eff"], a["off_eff"]),
                    "def_eff": _safe_sub(h["def_eff"], a["def_eff"]),
                    "sp_plus": _safe_sub(h["sp_plus"], a["sp_plus"]),
                    "roster_strength": _safe_sub(h["roster_strength"], a["roster_strength"]),
                    "continuity": _safe_sub(h["continuity"], a["continuity"]),
                    "qb_index": _safe_sub(h["qb_index"], a["qb_index"]),
                },
                "home": h,
                "away": a,
                "primary_driver": _primary_spread_driver(hit, h, a),
            }
        )

    payload = {
        "ok": True,
        "research_only": True,
        "kill_switch": "CFB_EDGE_BOARD_PUBLIC_ENABLED=false — unchanged",
        "production_model_changed": False,
        "engine_version": str(P.ENGINE_VERSION),
        "kei_version": kei_pack.get("kei_version"),
        "universe_mode": meta.get("mode"),
        "power_sot_fill": filled,
        "league_team_ppg": P.LEAGUE_TEAM_PPG,
        "neutral_2x_ppg": NEUTRAL_TOTAL,
        "matchup_response_raw": P.MATCHUP_RESPONSE,
        "matchup_response_w1": P.matchup_response_for_week(1),
        "matchup_response_w2": P.matchup_response_for_week(2),
        "max_reconstruct_abs_err": round(reconstruct_err, 4),
        "n_reprojected_fbs": len(rows),
        "n_joined_total": len(joined),
        "fleet": {
            "w1_w2": _fleet_stats(joined),
            "w1": _fleet_stats(w1),
            "w2": _fleet_stats(w2),
        },
        "counterfactual_vs_street": {
            "w1": fleet_cf(w1),
            "w2": fleet_cf(w2),
            "w1_w2": fleet_cf(joined),
        },
        "slices": {
            "week": slice_table(joined, lambda r: f"W{r['week']}"),
            "conference_home": slice_table(joined, lambda r: r["home_conf"]),
            "matchup_type": slice_table(joined, lambda r: r["matchup_type"]),
            "same_conf": slice_table(joined, lambda r: "same" if r["same_conf"] else "cross"),
            "mismatch": slice_table(joined, lambda r: r["mismatch_bucket"]),
            "proj_total": slice_table(joined, lambda r: r["proj_total_bucket"]),
            "market_total": slice_table(joined, lambda r: r["mkt_total_bucket"]),
            "pace": slice_table(joined, lambda r: r["pace_bucket"]),
            "offense": slice_table(joined, lambda r: r["off_bucket"]),
            "defense": slice_table(joined, lambda r: r["def_bucket"]),
            "continuity": slice_table(joined, lambda r: r["continuity_bucket"]),
            "home_fav_vs_dog": slice_table(
                [r for r in joined if r.get("market_spread_home") is not None],
                lambda r: "home_fav" if r["market_spread_home"] < 0 else "home_dog",
            ),
            "neutral_site": slice_table(
                joined, lambda r: "neutral" if r["neutral_site"] else "home"
            ),
        },
        "spread_outliers": outliers,
        "games": [
            {
                k: r[k]
                for k in (
                    "week",
                    "pair",
                    "model_total",
                    "market_total",
                    "total_resid",
                    "model_spread_home",
                    "kei_spread_home",
                    "market_spread_home",
                    "spread_resid",
                    "kei_spread_resid",
                    "fav_flip",
                    "matchup_inflation",
                    "total_neutral",
                    "mean_matchup_factor",
                    "pace_mean",
                    "matchup_type",
                    "mismatch_bucket",
                    "home_conf",
                    "away_conf",
                )
            }
            for r in rows
        ],
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT_JSON}")
    print(
        "joined",
        len(joined),
        "w2",
        len(w2),
        "w1",
        len(w1),
        "reconstruct_err",
        payload["max_reconstruct_abs_err"],
    )
    print("w2 fleet", json.dumps(payload["fleet"]["w2"], indent=2))
    print("w2 cf", json.dumps(payload["counterfactual_vs_street"]["w2"], indent=2))
    return 0


def _safe_sub(a: Any, b: Any) -> Optional[float]:
    if a is None or b is None:
        return None
    return round(float(a) - float(b), 4)


def _primary_spread_driver(hit: Dict[str, Any], h: Dict[str, Any], a: Dict[str, Any]) -> str:
    """Label the largest inspectable identity gap. Not a coefficient retune."""
    gaps = []
    if h.get("sp_plus") is not None and a.get("sp_plus") is not None:
        gaps.append(("sp_plus", abs(h["sp_plus"] - a["sp_plus"])))
    if h.get("qb_index") is not None and a.get("qb_index") is not None:
        gaps.append(("qb_index", abs(h["qb_index"] - a["qb_index"]) * 40.0))
    if h.get("roster_strength") is not None and a.get("roster_strength") is not None:
        gaps.append(("roster_strength", abs(h["roster_strength"] - a["roster_strength"])))
    gaps.append(("offense_index", abs(h["offense_index"] - a["offense_index"]) * 40.0))
    gaps.append(("defense_index", abs(h["defense_index"] - a["defense_index"]) * 40.0))
    if hit["home"] in SERVICE or hit["away"] in SERVICE:
        return "service_academy_identity"
    if not gaps:
        return "unlabeled"
    gaps.sort(key=lambda x: -x[1])
    return gaps[0][0]


def _fleet_stats(grp: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    tot = [r["total_resid"] for r in grp if r.get("total_resid") is not None]
    spr = [r["spread_resid"] for r in grp if r.get("spread_resid") is not None]
    kei_spr = [r["kei_spread_resid"] for r in grp if r.get("kei_spread_resid") is not None]
    infl = [r["matchup_inflation"] for r in grp]
    flips = sum(1 for r in grp if r.get("fav_flip"))
    over_n = sum(1 for t in tot if t > 0)
    return {
        "n": len(grp),
        "mean_total_resid": _mean(tot),
        "median_total_resid": _median(tot),
        "total_mae": _mae(tot),
        "total_rmse": _rmse(tot),
        "over_n": over_n,
        "under_n": len(tot) - over_n,
        "mean_matchup_inflation": _mean(infl),
        "mean_model_total": _mean([r["model_total"] for r in grp]),
        "mean_market_total": _mean(
            [r["market_total"] for r in grp if r.get("market_total") is not None]
        ),
        "mean_spread_resid_model": _mean(spr),
        "spread_mae_model": _mae(spr),
        "spread_rmse_model": _rmse(spr),
        "mean_spread_resid_kei": _mean(kei_spr),
        "spread_mae_kei": _mae(kei_spr),
        "favorite_flips": flips,
        "mean_home_matchup_factor": _mean([r["home_rec"]["matchup_factor"] for r in grp]),
        "mean_away_matchup_factor": _mean([r["away_rec"]["matchup_factor"] for r in grp]),
        "mean_pace": _mean([r["pace_mean"] for r in grp]),
        "mean_st_nudge": _mean([r["st_nudge"] for r in grp]),
        "mean_unit_boost_home": _mean([r["home_rec"]["off_boost"] for r in grp]),
        "mean_unit_dampen_home": _mean([r["home_rec"]["def_dampen"] for r in grp]),
    }


if __name__ == "__main__":
    raise SystemExit(main())
