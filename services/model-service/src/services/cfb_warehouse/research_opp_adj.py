"""Bounded research opponent-adjusted CFB EPA/play (offense + defense).

Research-only. These are **efficiency estimates**, not point spreads, not KEI,
and not a proprietary KE expected-points model. Upstream ``EPA`` keeps its
SportsDataverse name.

Model (team-game grain):

    y_{g,i} = μ + h · home_{g,i} + off_i + def_j + ε

``y`` is garbage-weighted EPA/play on eligible scrimmage plays.
Offense and opposing defense are estimated jointly with ridge shrinkage
toward the decayed prior (``λ`` play-weight + ``n0`` game-equivalents),
an identifiable league baseline (FBS off/def centered at 0), and an
explicit home-field term. ``μ`` and ``h`` are joint weighted OLS on
``y − off − def`` so the intercept does not absorb HFA.

Supporting raw metrics (pace, explosiveness, finishing, havoc, ST) stay
unadjusted and are never the adjustment target.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from src.services.cfb_warehouse.garbage import weight_play
from src.services.cfb_warehouse.identity import known_engine_codes, resolve_team_code
from src.services.cfb_warehouse.owned_metrics import is_scrimmage

PIPELINE_VERSION = "cfb-research-opp-adj-epa-v1"
PRODUCT_LABEL = "research opponent-adjusted EPA/play"
SUCCESS_RATE_LABEL = "EPA_success = EPA>0"
RESEARCH_ONLY = True
NOT_KE_RATINGS = True
# Do not rename upstream EPA.
EPA_SOURCE_NAME = "SportsDataverse espn_cfb_pbp EPA (unchanged)"

# Eligible-play contract (documented; tests lock the rules).
ELIGIBLE_PLAY_RULES = {
    "denominator": "scrimmage_play (pass|rush fallback) with finite EPA — #555/#559",
    "overtime": "exclude period/qtr >= 5; OT is not in the adjustment target",
    "garbage": (
        "warehouse garbage_weight is the play weight (not a hard drop). "
        "Competitive margin 16; late 2nd-half taper; min weight 0.10."
    ),
    "fcs": (
        "FCS opponents are kept and flagged. FCS ratings use stronger ridge "
        "(lambda_fcs_mult). FBS off/def are centered; FCS is not in the "
        "identifiability set."
    ),
    "home": (
        "home = 1 if offense matches home team, 0 if away, 0 if neutral/unknown. "
        "μ and h are joint weighted OLS on y − off − def (not sequential "
        "μ-then-h, which absorbs ~½ HFA into the intercept)."
    ),
    "prior_n0": (
        "Game-equivalent prior observations. Ridge is "
        "(data + (λ + n0·ppg)·prior) / (data + λ + n0·ppg). "
        "n0=0 reduces to λ-only shrinkage toward the prior."
    ),
    "target": "offensive and defensive EPA/play only",
}

DEFAULT_LAMBDA = 80.0
DEFAULT_LAMBDA_FCS_MULT = 4.0
DEFAULT_PRIOR_N0 = 4.0
DEFAULT_PRIOR_DECAY = 0.75
DEFAULT_ITERS = 12
MIN_PLAYS_GAME = 8
COLD_START_GAMES = 0
INSUFFICIENT_GAMES = 2  # below this, prior weight stays high; flag explicitly


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


def _truthy(raw: Any) -> bool:
    if isinstance(raw, bool):
        return raw
    if raw in (None, "", 0, "0"):
        return False
    if isinstance(raw, float) and raw != raw:
        return False
    return str(raw).lower() in {"1", "true", "t", "yes"}


def play_period(play: Mapping[str, Any]) -> Optional[int]:
    for key in ("period", "qtr", "quarter"):
        val = _f(play.get(key))
        if math.isfinite(val) and val > 0:
            return int(val)
    return None


def is_overtime(play: Mapping[str, Any]) -> bool:
    period = play_period(play)
    if period is not None:
        return period >= 5
    half = _f(play.get("half"))
    return math.isfinite(half) and half >= 3


def with_inferred_half(play: Mapping[str, Any]) -> Dict[str, Any]:
    rec = dict(play)
    if rec.get("half") not in (None, ""):
        return rec
    period = play_period(rec)
    if period is None:
        rec["half"] = 2
    elif period <= 2:
        rec["half"] = 1
    elif period <= 4:
        rec["half"] = 2
    else:
        rec["half"] = 3
    return rec


def _norm_name(raw: Any) -> str:
    return " ".join(str(raw or "").strip().lower().replace(".", "").split())


def offense_is_home(play: Mapping[str, Any]) -> Optional[float]:
    if _truthy(play.get("neutral")) or _truthy(play.get("neutral_site")):
        return 0.0
    pos = _norm_name(play.get("pos_team"))
    home = _norm_name(play.get("homeTeamName") or play.get("home") or play.get("homeTeamAbbrev"))
    away = _norm_name(play.get("awayTeamName") or play.get("away") or play.get("awayTeamAbbrev"))
    if not pos:
        return None
    if home and (pos == home or pos in home or home in pos):
        return 1.0
    if away and (pos == away or pos in away or away in pos):
        return 0.0
    abbr = _norm_name(play.get("homeTeamAbbrev"))
    pos_abbr = _norm_name(play.get("pos_team_abbr") or play.get("pos_abbr"))
    if abbr and pos_abbr and abbr == pos_abbr:
        return 1.0
    return None


def team_id(name: Any, known: Mapping[str, Any]) -> Tuple[str, bool]:
    label = str(name or "").strip()
    if not label or label.lower() in {"nan", "none", "nat", "<na>"}:
        return "", True
    code = resolve_team_code(name=label, abbr="", known_codes=known)
    if code:
        return code, False
    return f"fcs:{label}", True


@dataclass
class TeamGameEpa:
    season: int
    week: int
    game_id: str
    offense: str
    defense: str
    y: float
    n_plays: int
    n_weighted: float
    home: float
    fcs_offense: bool
    fcs_defense: bool
    available_week: int
    # Supporting raw metrics only — not adjustment targets.
    success_rate: Optional[float] = None
    explosive_rate: Optional[float] = None
    pace_plays: Optional[float] = None


@dataclass
class AdjParams:
    lam: float = DEFAULT_LAMBDA
    lam_fcs_mult: float = DEFAULT_LAMBDA_FCS_MULT
    prior_n0: float = DEFAULT_PRIOR_N0
    prior_decay: float = DEFAULT_PRIOR_DECAY
    iters: int = DEFAULT_ITERS


@dataclass
class TeamRating:
    team: str
    off: float
    defn: float  # EPA allowed; lower is better
    off_raw: float
    def_raw: float
    n_plays: float
    n_games: int
    fcs_games: int
    prior_off: float
    prior_def: float
    prior_weight: float
    in_season_weight: float
    cold_start: bool
    insufficient_history: bool
    fcs: bool
    uncertainty: float


@dataclass
class FitResult:
    mu: float
    hfa: float
    ratings: Dict[str, TeamRating]
    params: AdjParams
    n_obs: int
    n_teams: int
    n_fbs: int
    iters: int
    league_baseline: float


def eligible_plays(plays: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Scrimmage + finite EPA + regulation. Garbage is a weight, not a drop."""
    out: List[Dict[str, Any]] = []
    for play in plays:
        if not is_scrimmage(play):
            continue
        if is_overtime(play):
            continue
        epa = _f(play.get("EPA"))
        if not math.isfinite(epa):
            continue
        rec = with_inferred_half(play)
        w = weight_play(rec)
        if w <= 0:
            continue
        rec["_w"] = w
        rec["_epa"] = epa
        out.append(rec)
    return out


def aggregate_team_game_epa(
    plays: Sequence[Mapping[str, Any]],
    *,
    known: Optional[Mapping[str, Any]] = None,
) -> List[TeamGameEpa]:
    known = known if known is not None else known_engine_codes()
    buckets: Dict[Tuple[Any, ...], Dict[str, float]] = {}
    meta: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
    for play in eligible_plays(plays):
        off, fcs_off = team_id(play.get("pos_team"), known)
        deff, fcs_def = team_id(play.get("def_pos_team"), known)
        if not off or not deff:
            continue
        gid = str(play.get("game_id") or "").split(".")[0]
        if not gid:
            continue
        season = int(_f(play.get("season"), 0))
        week = int(_f(play.get("week"), 0))
        key = (season, week, gid, off, deff)
        acc = buckets.setdefault(
            key,
            {
                "w": 0.0,
                "n": 0.0,
                "epa": 0.0,
                "home_w": 0.0,
                "home_n": 0.0,
                "succ_n": 0.0,
                "succ_d": 0.0,
                "expl": 0.0,
            },
        )
        w = float(play["_w"])
        epa = float(play["_epa"])
        acc["w"] += w
        acc["n"] += 1.0
        acc["epa"] += w * epa
        home = offense_is_home(play)
        if home is not None:
            acc["home_w"] += w * home
            acc["home_n"] += w
        if play.get("EPA_success") not in (None, ""):
            acc["succ_d"] += 1.0
            if _truthy(play.get("EPA_success")):
                acc["succ_n"] += 1.0
        if epa >= 1.0 or _f(play.get("statYardage")) >= 15:
            acc["expl"] += w
        meta[key] = {
            "fcs_off": fcs_off,
            "fcs_def": fcs_def,
        }
    rows: List[TeamGameEpa] = []
    for key, acc in buckets.items():
        if acc["n"] < MIN_PLAYS_GAME or acc["w"] <= 0:
            continue
        season, week, gid, off, deff = key
        home = (acc["home_w"] / acc["home_n"]) if acc["home_n"] else 0.0
        info = meta[key]
        rows.append(
            TeamGameEpa(
                season=int(season),
                week=int(week),
                game_id=str(gid),
                offense=str(off),
                defense=str(deff),
                y=acc["epa"] / acc["w"],
                n_plays=int(acc["n"]),
                n_weighted=acc["w"],
                home=float(home),
                fcs_offense=bool(info["fcs_off"]),
                fcs_defense=bool(info["fcs_def"]),
                available_week=int(week),
                success_rate=(acc["succ_n"] / acc["succ_d"]) if acc["succ_d"] else None,
                explosive_rate=acc["expl"] / acc["w"],
                pace_plays=acc["n"],
            )
        )
    return rows


def _lambda(team: str, fcs: bool, params: AdjParams) -> float:
    return float(params.lam) * (params.lam_fcs_mult if fcs or str(team).startswith("fcs:") else 1.0)


def _fit_mu_hfa(
    games: Sequence[TeamGameEpa],
    off: Mapping[str, float],
    deff: Mapping[str, float],
) -> Tuple[float, float]:
    """Weighted OLS of (y − off − def) ~ μ + h·home.

    Sequential μ = mean(resid) then h on (resid − μ) absorbs about half of
    HFA into the intercept when home is a 0/1 indicator (~½ the rows).
    """
    sw = sx = sy = sxx = sxy = 0.0
    for g in games:
        resid = g.y - off.get(g.offense, 0.0) - deff.get(g.defense, 0.0)
        w = g.n_weighted
        x = float(g.home)
        sw += w
        sx += w * x
        sy += w * resid
        sxx += w * x * x
        sxy += w * x * resid
    det = sw * sxx - sx * sx
    if sw <= 0:
        return 0.0, 0.0
    if abs(det) < 1e-12:
        return (sy / sw), 0.0
    mu = (sxx * sy - sx * sxy) / det
    hfa = (sw * sxy - sx * sy) / det
    return mu, hfa


def _prior_play_weight(n0: float, play_weight: float, n_games: int) -> float:
    """Convert n0 games into the same units as play-weighted ridge."""
    if n_games <= 0 or play_weight <= 0 or n0 <= 0:
        return 0.0
    return float(n0) * (play_weight / float(n_games))


def fit_joint(
    games: Sequence[TeamGameEpa],
    *,
    params: AdjParams = AdjParams(),
    prior_off: Optional[Mapping[str, float]] = None,
    prior_def: Optional[Mapping[str, float]] = None,
) -> FitResult:
    """Joint ridge: offense + opposing defense + HFA + league μ."""
    prior_off = dict(prior_off or {})
    prior_def = dict(prior_def or {})
    teams = sorted({g.offense for g in games} | {g.defense for g in games})
    if not teams or not games:
        return FitResult(
            mu=0.0,
            hfa=0.0,
            ratings={},
            params=params,
            n_obs=0,
            n_teams=0,
            n_fbs=0,
            iters=0,
            league_baseline=0.0,
        )

    fcs_flag = {
        t: t.startswith("fcs:")
        or any((g.offense == t and g.fcs_offense) or (g.defense == t and g.fcs_defense) for g in games)
        for t in teams
    }
    off = {t: float(prior_off.get(t, 0.0)) for t in teams}
    deff = {t: float(prior_def.get(t, 0.0)) for t in teams}
    mu = 0.0
    hfa = 0.0

    fbs = [t for t in teams if not fcs_flag[t]]

    def _center() -> None:
        if not fbs:
            return
        mo = sum(off[t] for t in fbs) / len(fbs)
        md = sum(deff[t] for t in fbs) / len(fbs)
        for t in fbs:
            off[t] -= mo
            deff[t] -= md

    _center()

    for _ in range(max(1, int(params.iters))):
        mu, hfa = _fit_mu_hfa(games, off, deff)

        new_off = {}
        new_def = {}
        for t in teams:
            lam = _lambda(t, fcs_flag[t], params)
            p_off = float(prior_off.get(t, 0.0))
            p_def = float(prior_def.get(t, 0.0))
            n_o = d_o = n_d = d_d = 0.0
            ng_o = ng_d = 0
            for g in games:
                if g.offense == t:
                    n_o += g.n_weighted * (g.y - mu - hfa * g.home - deff.get(g.defense, 0.0))
                    d_o += g.n_weighted
                    ng_o += 1
                if g.defense == t:
                    n_d += g.n_weighted * (g.y - mu - hfa * g.home - off.get(g.offense, 0.0))
                    d_d += g.n_weighted
                    ng_d += 1
            n0_o = _prior_play_weight(params.prior_n0, d_o, ng_o)
            n0_d = _prior_play_weight(params.prior_n0, d_d, ng_d)
            den_o = d_o + lam + n0_o
            den_d = d_d + lam + n0_d
            new_off[t] = (n_o + (lam + n0_o) * p_off) / den_o if den_o else p_off
            new_def[t] = (n_d + (lam + n0_d) * p_def) / den_d if den_d else p_def
        off, deff = new_off, new_def
        _center()

    raw_off_n = {t: 0.0 for t in teams}
    raw_off_s = {t: 0.0 for t in teams}
    raw_def_n = {t: 0.0 for t in teams}
    raw_def_s = {t: 0.0 for t in teams}
    n_games = {t: 0 for t in teams}
    fcs_games = {t: 0 for t in teams}
    for g in games:
        raw_off_s[g.offense] += g.n_weighted * g.y
        raw_off_n[g.offense] += g.n_weighted
        raw_def_s[g.defense] += g.n_weighted * g.y
        raw_def_n[g.defense] += g.n_weighted
        n_games[g.offense] += 1
        if g.fcs_defense:
            fcs_games[g.offense] += 1

    ratings: Dict[str, TeamRating] = {}
    for t in teams:
        n = raw_off_n[t]
        ng = n_games[t]
        prior_w = params.prior_n0 / (params.prior_n0 + max(ng, 0))
        ratings[t] = TeamRating(
            team=t,
            off=off[t],
            defn=deff[t],
            off_raw=(raw_off_s[t] / n) if n else 0.0,
            def_raw=(raw_def_s[t] / raw_def_n[t]) if raw_def_n[t] else 0.0,
            n_plays=n,
            n_games=ng,
            fcs_games=fcs_games[t],
            prior_off=float(prior_off.get(t, 0.0)),
            prior_def=float(prior_def.get(t, 0.0)),
            prior_weight=prior_w,
            in_season_weight=1.0 - prior_w,
            cold_start=ng == COLD_START_GAMES and t not in prior_off,
            insufficient_history=ng < INSUFFICIENT_GAMES,
            fcs=fcs_flag[t],
            uncertainty=1.0 / math.sqrt(n + params.lam),
        )

    return FitResult(
        mu=mu,
        hfa=hfa,
        ratings=ratings,
        params=params,
        n_obs=len(games),
        n_teams=len(teams),
        n_fbs=len(fbs),
        iters=int(params.iters),
        league_baseline=mu,
    )


def blend_priors(
    previous: Mapping[str, TeamRating],
    *,
    decay: float,
) -> Tuple[Dict[str, float], Dict[str, float]]:
    off = {}
    deff = {}
    for team, rating in previous.items():
        off[team] = float(decay) * float(rating.off)
        deff[team] = float(decay) * float(rating.defn)
    return off, deff


def games_before_cutoff(
    games: Sequence[TeamGameEpa],
    *,
    season: int,
    week: int,
) -> List[TeamGameEpa]:
    """Pregame cutoff: earlier seasons, or same season with week < target week."""
    out = []
    for g in games:
        if g.season < int(season) or (g.season == int(season) and g.week < int(week)):
            out.append(g)
    return out


def predict_game(
    fit: FitResult,
    *,
    offense: str,
    defense: str,
    home: float,
) -> Dict[str, float]:
    """Predicted offensive EPA/play (and the mirror defensive allowed)."""
    off_r = fit.ratings.get(offense)
    def_r = fit.ratings.get(defense)
    off = off_r.off if off_r else 0.0
    deff = def_r.defn if def_r else 0.0
    pred = fit.mu + fit.hfa * float(home) + off + deff
    return {
        "pred_off_epa": pred,
        "pred_def_epa_allowed": pred,  # same observation, opponent view
        "mu": fit.mu,
        "hfa": fit.hfa * float(home),
        "off_rating": off,
        "def_rating": deff,
    }


def season_final_ratings(fit: FitResult) -> Dict[str, TeamRating]:
    return {k: v for k, v in fit.ratings.items() if not v.fcs}


def rating_row(
    rating: TeamRating,
    *,
    season: int,
    as_of_week: int,
    mu: float,
    hfa: float,
    params: AdjParams,
) -> Dict[str, Any]:
    return {
        "season": int(season),
        "as_of_week": int(as_of_week),
        "team": rating.team,
        "off_epa_adj": round(rating.off, 6),
        "def_epa_adj": round(rating.defn, 6),
        "off_epa_raw": round(rating.off_raw, 6),
        "def_epa_raw": round(rating.def_raw, 6),
        "league_baseline": round(mu, 6),
        "hfa": round(hfa, 6),
        "n_plays_weighted": round(rating.n_plays, 3),
        "n_games": rating.n_games,
        "fcs_games": rating.fcs_games,
        "prior_off": round(rating.prior_off, 6),
        "prior_def": round(rating.prior_def, 6),
        "prior_weight": round(rating.prior_weight, 6),
        "in_season_weight": round(rating.in_season_weight, 6),
        "cold_start": rating.cold_start,
        "insufficient_history": rating.insufficient_history,
        "uncertainty": round(rating.uncertainty, 6),
        "fcs": rating.fcs,
        "opponent_adjusted": True,
        "research_only": True,
        "not_ke_ratings": True,
        "not_point_spread": True,
        "epa_source": EPA_SOURCE_NAME,
        "product_label": PRODUCT_LABEL,
        "pipeline_version": PIPELINE_VERSION,
        "params": asdict(params),
    }
