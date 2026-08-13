"""Walk-forward CFB research fair vs owned lake closes (Week 0–4 emphasis).

Historical seasons (2020–2025 warehouse games) use a **program prior**
built from opponent-adj EPA seasons < Y. The 2026 roster/QB pack is not
applied to 2020–25 (that would leak a future overlay). Week 0–1 is
prior-only. Week 2+ blends prior with entering-week efficiency
(``as_of_week == game.week``, which uses only ``week < W``).

Close = last owned lake snap strictly before kickoff (not a true lock).
No KEI. No in-sample retune.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from src.services.cfb_season_engine.priors import HFA_BASELINE_POINTS
from src.services.cfb_warehouse.identity import known_engine_codes
from src.services.cfb_warehouse.leakage import era_tag, is_available_before_kickoff
from src.services.cfb_warehouse.preseason_prior import NET_EPA_TO_POINTS, program_component

# Spread convention: negative = home favored (Odds API / project-game).
HFA_FLAT = float(HFA_BASELINE_POINTS)  # 1.7 — engine baseline, not 2026 venue map
BLEND = {
    "w0_1": (1.00, 0.00),
    "w2_4": (0.55, 0.45),
    "w5_plus": (0.25, 0.75),
}
MIN_EDGE = 0.5
EXPLORATORY_N = 50
THIN_N = 30


def week_band(week: Any) -> str:
    w = int(week or 0)
    if w <= 1:
        return "w0_1"
    if w <= 4:
        return "w2_4"
    return "w5_plus"


def _f(raw: Any) -> Optional[float]:
    if raw is None or raw == "":
        return None
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(val):
        return None
    return val


def _finite(raw: Any, default: float = 0.0) -> float:
    val = _f(raw)
    return default if val is None else val


def wilson_interval(k: int, n: int, z: float = 1.96) -> Optional[Tuple[float, float]]:
    if n <= 0:
        return None
    p = k / n
    z2 = z * z
    den = 1.0 + z2 / n
    center = (p + z2 / (2.0 * n)) / den
    half = z * math.sqrt((p * (1.0 - p) + z2 / (4.0 * n)) / n) / den
    return (max(0.0, center - half), min(1.0, center + half))


def signed_clv(model: float, open_sp: float, close_sp: float) -> float:
    """Positive = close moved toward the model relative to open.

    Last owned snap ≠ lock. Magnitude is a stub, not CLV PnL.
    """
    return math.copysign(1.0, open_sp - model) * (open_sp - close_sp)


def efficiency_points(row: Mapping[str, Any]) -> Optional[float]:
    off_v = _f(row.get("off_epa_adj"))
    def_v = _f(row.get("def_epa_adj"))
    if off_v is None or def_v is None:
        return None
    return (off_v - def_v) * NET_EPA_TO_POINTS


def build_program_priors(
    season_finals: Sequence[Mapping[str, Any]],
    years: Sequence[int],
) -> Dict[Tuple[int, str], Dict[str, Any]]:
    """prior_year Y uses only seasons < Y."""
    known = known_engine_codes()
    teams = sorted(
        {
            str(r.get("team_id"))
            for r in season_finals
            if str(r.get("team_id") or "") in known
        }
    )
    out: Dict[Tuple[int, str], Dict[str, Any]] = {}
    for year in years:
        legal = [
            r
            for r in season_finals
            if int(_finite(r.get("season"))) < int(year)
            and not str(r.get("team_id", "")).startswith("fcs:")
        ]
        for team in teams:
            prog = program_component(legal, team, prior_year=int(year))
            if not prog["seasons"]:
                continue
            out[(int(year), team)] = prog
    return out


def index_week_efficiency(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[int, int, str], Dict[str, Any]]:
    idx: Dict[Tuple[int, int, str], Dict[str, Any]] = {}
    for row in rows:
        team = str(row.get("team_id") or "")
        if not team or team.startswith("fcs:"):
            continue
        key = (int(_finite(row.get("season"))), int(_finite(row.get("as_of_week"))), team)
        idx[key] = dict(row)
    return idx


def lookup_efficiency(
    idx: Mapping[Tuple[int, int, str], Mapping[str, Any]],
    *,
    season: int,
    week: int,
    team: str,
    kickoff: Any,
    game_date: Any,
) -> Tuple[Optional[Dict[str, Any]], str]:
    """Entering-week snapshot. Week W may only include week < W.

    ``available_at`` on snapshots is a bucket max and is often unusable
    (wrong/missing PBP↔ESPN game_id). Leakage proof is ``feature_week < week``.
    If a timestamp exists and is *after* kickoff, ignore it and keep the week rule.
    """
    row = idx.get((int(season), int(week), str(team)))
    if not row:
        return None, "missing"
    max_included = int(_finite(row.get("max_week_included"), -1))
    feat_week = int(_finite(row.get("feature_week"), max_included))
    if max_included >= int(week) or feat_week >= int(week):
        return None, "leakage"
    week_ok = feat_week < int(week)
    avail = row.get("available_at")
    if avail:
        ts_ok = is_available_before_kickoff(
            available_at=avail, kickoff=kickoff, game_date=game_date
        )
        if ts_ok:
            return dict(row), "timestamp"
        if week_ok:
            return dict(row), "week_fallback_ts_ignored"
        return None, "unprovable"
    if week_ok:
        return dict(row), "week_fallback"
    return None, "unprovable"


def model_fair(
    *,
    week: int,
    home_prior: Optional[float],
    away_prior: Optional[float],
    home_eff: Optional[float],
    away_eff: Optional[float],
    home_cold: bool,
    away_cold: bool,
    neutral: bool,
) -> Tuple[Optional[float], str, Dict[str, Any]]:
    """Return (model_spread_home, status, drivers). Missing pieces → incomplete."""
    band = week_band(week)
    w_prior, w_eff = BLEND[band]
    if home_prior is None or away_prior is None:
        return None, "incomplete_prior", {"band": band}
    prior_margin = float(home_prior) - float(away_prior)
    if band == "w0_1" or w_eff <= 0:
        strength = prior_margin
        blend = "prior_only"
    else:
        if home_eff is None or away_eff is None or home_cold or away_cold:
            return None, "incomplete_efficiency", {"band": band}
        eff_margin = float(home_eff) - float(away_eff)
        strength = w_prior * prior_margin + w_eff * eff_margin
        blend = f"prior {w_prior:.2f} + eff {w_eff:.2f}"
    hfa = 0.0 if neutral else HFA_FLAT
    # home_edge points → spread_home negative when home favored
    spread = -(strength + hfa)
    return (
        round(spread, 3),
        "ok",
        {
            "band": band,
            "blend": blend,
            "prior_margin": round(prior_margin, 3),
            "hfa": hfa,
            "w_prior": w_prior,
            "w_eff": w_eff,
        },
    )


def _pick_home(model: float, close: float) -> Optional[bool]:
    edge = close - model  # >0 model more home-favored than close
    if edge > MIN_EDGE:
        return True
    if edge < -MIN_EDGE:
        return False
    return None


def grade_walkforward_row(
    game: Mapping[str, Any],
    *,
    model_spread_home: Optional[float],
    fair_status: str,
    drivers: Mapping[str, Any],
) -> Dict[str, Any]:
    close = _f(game.get("close_spread_home"))
    open_sp = _f(game.get("open_spread_home"))
    home_score = _f(game.get("home_score"))
    away_score = _f(game.get("away_score"))
    margin = None
    if home_score is not None and away_score is not None:
        margin = home_score - away_score
    spread_error = None
    if model_spread_home is not None and close is not None:
        spread_error = model_spread_home - close
    ats = None
    pick_home = None
    if model_spread_home is not None and close is not None and margin is not None:
        cover = margin + close
        if abs(cover) >= 1e-9:
            pick_home = _pick_home(model_spread_home, close)
            if pick_home is True:
                ats = cover > 0
            elif pick_home is False:
                ats = cover < 0
    clv = None
    if model_spread_home is not None and open_sp is not None and close is not None:
        clv = signed_clv(model_spread_home, open_sp, close)
    fav_home = close < 0 if close is not None else None
    return {
        "game_id": game.get("game_id"),
        "season": int(_finite(game.get("season"))),
        "week": int(_finite(game.get("week"))),
        "week_band": week_band(game.get("week")),
        "era_tag": game.get("era_tag") or era_tag(int(_finite(game.get("season")))),
        "home_team_id": game.get("home_team_id"),
        "away_team_id": game.get("away_team_id"),
        "neutral": bool(game.get("neutral")),
        "home_score": home_score,
        "away_score": away_score,
        "margin": margin,
        "open_spread_home": open_sp,
        "close_spread_home": close,
        "line_source": game.get("source"),
        "line_fidelity": game.get("line_fidelity"),
        "close_captured_at": str(game.get("close_captured_at") or game.get("available_at") or ""),
        "model_spread_home": model_spread_home,
        "fair_status": fair_status,
        "model_fair_present": model_spread_home is not None,
        "spread_error": spread_error,
        "ats_hit": ats,
        "model_pick_home": pick_home,
        "clv_stub": clv,
        "favorite_home": fav_home,
        "drivers": dict(drivers),
    }


def walkforward_games(
    games: Sequence[Mapping[str, Any]],
    *,
    priors: Mapping[Tuple[int, str], Mapping[str, Any]],
    eff_idx: Mapping[Tuple[int, int, str], Mapping[str, Any]],
    known: Optional[Mapping[str, Any]] = None,
) -> List[Dict[str, Any]]:
    known = known if known is not None else known_engine_codes()
    out: List[Dict[str, Any]] = []
    for game in games:
        season = int(_finite(game.get("season")))
        week = int(_finite(game.get("week")))
        home = str(game.get("home_team_id") or "")
        away = str(game.get("away_team_id") or "")
        fcs = bool(game.get("fcs_home") or game.get("fcs_away") or game.get("fcs_opponent"))
        if home not in known or away not in known or fcs:
            out.append(
                grade_walkforward_row(
                    game,
                    model_spread_home=None,
                    fair_status="incomplete_identity",
                    drivers={"band": week_band(week)},
                )
            )
            continue
        home_p = priors.get((season, home))
        away_p = priors.get((season, away))
        home_e, home_how = lookup_efficiency(
            eff_idx,
            season=season,
            week=week,
            team=home,
            kickoff=game.get("kickoff"),
            game_date=game.get("game_date"),
        )
        away_e, away_how = lookup_efficiency(
            eff_idx,
            season=season,
            week=week,
            team=away,
            kickoff=game.get("kickoff"),
            game_date=game.get("game_date"),
        )
        spread, status, drivers = model_fair(
            week=week,
            home_prior=home_p.get("points") if home_p else None,
            away_prior=away_p.get("points") if away_p else None,
            home_eff=efficiency_points(home_e) if home_e else None,
            away_eff=efficiency_points(away_e) if away_e else None,
            home_cold=bool(home_e and home_e.get("cold_start")),
            away_cold=bool(away_e and away_e.get("cold_start")),
            neutral=bool(game.get("neutral")),
        )
        drivers = {
            **drivers,
            "home_eff_proof": home_how,
            "away_eff_proof": away_how,
        }
        out.append(
            grade_walkforward_row(
                game, model_spread_home=spread, fair_status=status, drivers=drivers
            )
        )
    return out


def _slice_metrics(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    graded = [
        r
        for r in rows
        if r.get("model_fair_present") and r.get("close_spread_home") is not None
    ]
    n = len(graded)
    errors = [_f(r.get("spread_error")) for r in graded]
    errors = [e for e in errors if e is not None]
    ats = [r.get("ats_hit") for r in graded if r.get("ats_hit") is not None]
    clvs = [_f(r.get("clv_stub")) for r in graded if r.get("open_spread_home") is not None]
    clvs = [c for c in clvs if c is not None]
    mae = (sum(abs(e) for e in errors) / len(errors)) if errors else None
    mean_err = (sum(errors) / len(errors)) if errors else None
    med = None
    if errors:
        srt = sorted(abs(e) for e in errors)
        med = srt[len(srt) // 2]
    hits = sum(1 for x in ats if x)
    n_ats = len(ats)
    ci = wilson_interval(hits, n_ats) if n_ats else None
    thin = n < THIN_N
    exploratory = n < EXPLORATORY_N
    label = "thin" if thin else ("exploratory" if exploratory else "ok")
    fav = [
        r
        for r in graded
        if r.get("favorite_home") is True and r.get("spread_error") is not None
    ]
    dog = [
        r
        for r in graded
        if r.get("favorite_home") is False and r.get("spread_error") is not None
    ]

    def _mae(rs: Sequence[Mapping[str, Any]]) -> Optional[float]:
        vals = [_f(r.get("spread_error")) for r in rs]
        vals = [v for v in vals if v is not None]
        if not vals:
            return None
        return sum(abs(v) for v in vals) / len(vals)

    return {
        "n_close": n,
        "n_games": len(rows),
        "n_fair": sum(1 for r in rows if r.get("model_fair_present")),
        "n_unmatched_close": sum(1 for r in rows if r.get("close_spread_home") is None),
        "n_incomplete": sum(
            1 for r in rows if str(r.get("fair_status", "")).startswith("incomplete")
        ),
        "mean_error": round(mean_err, 3) if mean_err is not None else None,
        "mae": round(mae, 3) if mae is not None else None,
        "median_ae": round(med, 3) if med is not None else None,
        "ats_n": n_ats,
        "ats_hits": hits,
        "ats_rate": round(hits / n_ats, 4) if n_ats else None,
        "ats_ci95": [round(ci[0], 4), round(ci[1], 4)] if ci else None,
        "sample_flag": label,
        "clv_n": len(clvs),
        "clv_mean": round(sum(clvs) / len(clvs), 3) if clvs else None,
        "clv_pos_rate": round(sum(1 for c in clvs if c > 0) / len(clvs), 4) if clvs else None,
        "mae_home_fav": round(_mae(fav), 3) if fav else None,
        "mae_home_dog": round(_mae(dog), 3) if dog else None,
        "n_home_fav": len(fav),
        "n_home_dog": len(dog),
    }


def summarize(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    by_band: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    by_season: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    portal: List[Mapping[str, Any]] = []
    earlier: List[Mapping[str, Any]] = []
    for r in rows:
        by_band[str(r.get("week_band"))].append(r)
        by_season[str(r.get("season"))].append(r)
        if str(r.get("era_tag")) == "2022-present":
            portal.append(r)
        else:
            earlier.append(r)
    incomplete = defaultdict(int)
    for r in rows:
        incomplete[str(r.get("fair_status"))] += 1
    return {
        "overall": _slice_metrics(rows),
        "by_week_band": {k: _slice_metrics(v) for k, v in sorted(by_band.items())},
        "by_season": {k: _slice_metrics(v) for k, v in sorted(by_season.items())},
        "portal_era_2022plus": _slice_metrics(portal),
        "pre_2022": _slice_metrics(earlier),
        "fair_status_counts": dict(incomplete),
        "hfa_flat": HFA_FLAT,
        "blend": {k: {"w_prior": a, "w_eff": b} for k, (a, b) in BLEND.items()},
        "net_epa_to_points": NET_EPA_TO_POINTS,
        "close_definition": "last owned lake snap strictly before kickoff (not a true lock)",
        "prior_definition": "program EPA prior from seasons < Y (no 2026 roster/QB on historical games)",
    }


def example_row(
    rows: Sequence[Mapping[str, Any]],
    game_id: str = "401628323",
) -> Optional[Dict[str, Any]]:
    for r in rows:
        if str(r.get("game_id")) == str(game_id):
            return dict(r)
    for r in rows:
        if r.get("model_fair_present") and r.get("close_spread_home") is not None:
            return dict(r)
    return None
