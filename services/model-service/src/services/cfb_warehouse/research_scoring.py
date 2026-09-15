"""Research-only CFB scoring: efficiency → team points → margin / total.

Pregame opponent-adjusted O/D EPA comes from the frozen #560 method.
This module converts those efficiencies into points. It does **not**
retune λ / n0 / decay. It does **not** turn thin-window EPA h into a spread.

    margin = home_points − away_points
    total  = home_points + away_points

``production_promote=false``. Not KEI. Not production SP+.
Protocol: ``docs/cfb/EVAL_PROTOCOL.md`` (locked before knob search).
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from src.services.cfb_warehouse.identity import known_engine_codes
from src.services.cfb_warehouse.owned_metrics import is_scrimmage
from src.services.cfb_warehouse.research_opp_adj import (
    ESTIMATOR_ID,
    FitResult,
    team_id,
)
from src.services.cfb_warehouse.research_opp_adj_validate import independent_league_raw_mean

PIPELINE_VERSION = "cfb-research-eff-scoring-v1"
PRODUCT_LABEL = "research efficiency-to-points (not KEI)"
RESEARCH_ONLY = True
PRODUCTION_PROMOTE = False
MARGIN_SIGN = "home_points - away_points"
# Frozen EPA stack — do not retune here.
FROZEN_EPA_ESTIMATOR = ESTIMATOR_ID
FROZEN_EPA_KNOBS = {
    "lam": 40.0,
    "prior_n0": 4.0,
    "prior_decay": 0.75,
    "lam_fcs_mult": 4.0,
    "iters": 12,
}

PACE_COMPETITIVE = "competitive_pace_plays"
PACE_RAW = "pace_plays"
PACE_SOURCES = (PACE_COMPETITIVE, PACE_RAW)
HFA_K_GRID = (10.0, 20.0, 40.0, 80.0, 160.0)
COMPETITIVE_MARGIN = 16.0

# Official-score columns on owned SDV PBP. No synthetic fill.
SCORE_HOME_KEYS = ("end.homeScore", "homeScore", "home_score")
SCORE_AWAY_KEYS = ("end.awayScore", "awayScore", "away_score")


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


def _score_from_play(play: Mapping[str, Any], keys: Sequence[str]) -> Optional[int]:
    for key in keys:
        val = _f(play.get(key))
        if math.isfinite(val) and val >= 0:
            return int(val)
    return None


def extract_official_scores(
    plays: Sequence[Mapping[str, Any]],
    *,
    known: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Max running score per game from owned PBP. Missing scores stay missing."""
    known = known if known is not None else known_engine_codes()
    games: Dict[str, Dict[str, Any]] = {}
    for play in plays:
        gid = str(play.get("game_id") or "").split(".")[0]
        if not gid:
            continue
        acc = games.get(gid)
        if acc is None:
            home_name = play.get("homeTeamName") or play.get("home") or play.get("homeTeamAbbrev")
            away_name = play.get("awayTeamName") or play.get("away") or play.get("awayTeamAbbrev")
            home, home_fcs = team_id(home_name, known)
            away, away_fcs = team_id(away_name, known)
            acc = {
                "game_id": gid,
                "season": int(_f(play.get("season"), 0)),
                "week": int(_f(play.get("week"), 0)),
                "home": home,
                "away": away,
                "home_fcs": home_fcs,
                "away_fcs": away_fcs,
                "home_points": None,
                "away_points": None,
                "neutral": False,
                "max_period": 0,
            }
            games[gid] = acc
        if _truthy(play.get("neutral")) or _truthy(play.get("neutral_site")):
            acc["neutral"] = True
        period = _f(play.get("period") or play.get("qtr") or play.get("quarter"))
        if math.isfinite(period):
            acc["max_period"] = max(int(acc["max_period"]), int(period))
        hs = _score_from_play(play, SCORE_HOME_KEYS)
        aws = _score_from_play(play, SCORE_AWAY_KEYS)
        if hs is not None:
            prev = acc["home_points"]
            acc["home_points"] = hs if prev is None else max(int(prev), hs)
        if aws is not None:
            prev = acc["away_points"]
            acc["away_points"] = aws if prev is None else max(int(prev), aws)
    return games


def extract_team_pace(
    plays: Sequence[Mapping[str, Any]],
    *,
    known: Optional[Mapping[str, Any]] = None,
) -> Dict[Tuple[str, str], Dict[str, float]]:
    """Owned #555/#559 pace + possessions per (game_id, offense)."""
    known = known if known is not None else known_engine_codes()
    buckets: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for play in plays:
        if not is_scrimmage(play):
            continue
        gid = str(play.get("game_id") or "").split(".")[0]
        off, _fcs = team_id(play.get("pos_team"), known)
        if not gid or not off:
            continue
        key = (gid, off)
        acc = buckets.setdefault(
            key,
            {"pace_plays": 0.0, "competitive_pace_plays": 0.0, "drives": set()},
        )
        acc["pace_plays"] += 1.0
        margin = _f(play.get("pos_score_diff"))
        if math.isfinite(margin) and abs(margin) < COMPETITIVE_MARGIN:
            acc["competitive_pace_plays"] += 1.0
        did = str(play.get("drive.id") or play.get("drive_id") or "").strip()
        if did:
            acc["drives"].add(did)
    out: Dict[Tuple[str, str], Dict[str, float]] = {}
    for key, acc in buckets.items():
        n_drives = float(len(acc["drives"]))
        pace = float(acc["pace_plays"])
        out[key] = {
            "pace_plays": pace,
            "competitive_pace_plays": float(acc["competitive_pace_plays"]),
            "n_drives": n_drives,
            "plays_per_possession": (pace / n_drives) if n_drives >= 1 else float("nan"),
        }
    return out


def plays_per_possession(
    pace_rows: Mapping[Tuple[str, str], Mapping[str, float]],
    scores: Mapping[str, Mapping[str, Any]],
    *,
    seasons: Sequence[int],
) -> float:
    """Train-period mean of pace_plays / n_drives on FBS-offense team-games."""
    season_set = {int(s) for s in seasons}
    vals: List[float] = []
    for (gid, team), row in pace_rows.items():
        game = scores.get(gid)
        if game is None or int(game.get("season") or 0) not in season_set:
            continue
        if team.startswith("fcs:"):
            continue
        ppp = _f(row.get("plays_per_possession"))
        if math.isfinite(ppp) and ppp > 0:
            vals.append(ppp)
    if not vals:
        return 6.5  # documented last-resort constant; not a synthetic game fill
    return sum(vals) / len(vals)


def shrink_hfa(*, h_window: float, h_prior: float, n: float, k: float) -> float:
    """James-Stein style shrink of window HFA toward the train prior.

    h_pts = (N / (N + k)) * h_window + (k / (N + k)) * h_prior
    N is the HFA estimation sample (train non-neutral games), not a 2026 thin window.
    """
    n = max(float(n), 0.0)
    k = max(float(k), 0.0)
    den = n + k
    if den <= 0:
        return float(h_prior)
    return (n / den) * float(h_window) + (k / den) * float(h_prior)


def _solve_3(ata: List[List[float]], atb: List[float]) -> Optional[Tuple[float, float, float]]:
    """3x3 Gaussian elimination. Returns None if singular."""
    m = [ata[i][:] + [atb[i]] for i in range(3)]
    for i in range(3):
        pivot = max(range(i, 3), key=lambda r: abs(m[r][i]))
        if abs(m[pivot][i]) < 1e-12:
            return None
        m[i], m[pivot] = m[pivot], m[i]
        div = m[i][i]
        for j in range(i, 4):
            m[i][j] /= div
        for r in range(3):
            if r == i:
                continue
            fac = m[r][i]
            for j in range(i, 4):
                m[r][j] -= fac * m[i][j]
    return m[0][3], m[1][3], m[2][3]


def ols_points(
    rows: Sequence[Mapping[str, Any]],
) -> Tuple[float, float, float]:
    """points = a + b * (epa * exp_plays) + h * home. Train only."""
    ata = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
    atb = [0.0, 0.0, 0.0]
    n = 0
    for row in rows:
        y = _f(row.get("points"))
        x1 = _f(row.get("epa_plays"))
        x2 = _f(row.get("home"))
        if not math.isfinite(y) or not math.isfinite(x1) or not math.isfinite(x2):
            continue
        x = (1.0, x1, x2)
        for i in range(3):
            atb[i] += x[i] * y
            for j in range(3):
                ata[i][j] += x[i] * x[j]
        n += 1
    if n < 10:
        return 24.0, 1.0, 2.5
    sol = _solve_3(ata, atb)
    if sol is None:
        return 24.0, 1.0, 2.5
    return sol


def predict_epa_no_hfa(fit: FitResult, *, offense: str, defense: str) -> float:
    """Pregame EPA/play without the EPA-model h·home term.

    HFA is applied in points (shrunk). Do not multiply thin-window EPA h by plays.
    """
    off_r = fit.ratings.get(offense)
    def_r = fit.ratings.get(defense)
    off = off_r.off if off_r else 0.0
    deff = def_r.defn if def_r else 0.0
    return float(fit.mu) + off + deff


def predict_team_points(
    *,
    intercept: float,
    slope: float,
    h_pts: float,
    epa: float,
    exp_plays: float,
    home: float,
) -> float:
    return float(intercept) + float(slope) * float(epa) * float(exp_plays) + float(h_pts) * float(home)


def margin_total(
    home_points: float, away_points: float
) -> Tuple[float, float]:
    return float(home_points) - float(away_points), float(home_points) + float(away_points)


@dataclass
class ScoringKnobs:
    pace_source: str = PACE_COMPETITIVE
    hfa_k: float = 40.0

    def as_dict(self) -> Dict[str, Any]:
        return {"pace_source": self.pace_source, "hfa_k": float(self.hfa_k)}


@dataclass
class ScoringFit:
    intercept: float
    slope: float
    h_window: float
    h_prior: float
    h_pts: float
    hfa_k: float
    n_hfa: int
    ppp: float
    league_pace: float
    train_league_points: float
    pace_source: str
    n_train_team_games: int

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def home_margin_prior(games: Sequence[Mapping[str, Any]]) -> Tuple[float, int]:
    """Train-only mean(home − away) on non-neutral games with official scores."""
    vals = []
    for g in games:
        if g.get("neutral"):
            continue
        hp = _f(g.get("home_points"))
        ap = _f(g.get("away_points"))
        if math.isfinite(hp) and math.isfinite(ap):
            vals.append(hp - ap)
    if not vals:
        return 2.5, 0
    return sum(vals) / len(vals), len(vals)


def fit_scoring(
    team_rows: Sequence[Mapping[str, Any]],
    game_rows: Sequence[Mapping[str, Any]],
    *,
    knobs: ScoringKnobs,
    ppp: float,
    league_pace: float,
    train_league_points: float,
) -> ScoringFit:
    a, b, h_window = ols_points(team_rows)
    h_prior, n_hfa = home_margin_prior(game_rows)
    h_pts = shrink_hfa(h_window=h_window, h_prior=h_prior, n=float(n_hfa), k=knobs.hfa_k)
    return ScoringFit(
        intercept=a,
        slope=b,
        h_window=h_window,
        h_prior=h_prior,
        h_pts=h_pts,
        hfa_k=float(knobs.hfa_k),
        n_hfa=n_hfa,
        ppp=float(ppp),
        league_pace=float(league_pace),
        train_league_points=float(train_league_points),
        pace_source=knobs.pace_source,
        n_train_team_games=len(team_rows),
    )


def apply_scoring_fit(
    fit: ScoringFit,
    *,
    epa: float,
    exp_plays: float,
    home: float,
) -> float:
    return predict_team_points(
        intercept=fit.intercept,
        slope=fit.slope,
        h_pts=fit.h_pts,
        epa=epa,
        exp_plays=exp_plays,
        home=home,
    )


def unused_epa_mean_note() -> str:
    """Keep IBF helper imported so scoring baselines share the same fallback spirit."""
    return (
        "Scoring point-baselines use train league mean points (2016–2022), "
        f"analogous to IBF-v1 raw-EPA mean (helper={independent_league_raw_mean.__name__})."
    )


def forbidden_thin_window_spread(h_epa: float, n_plays: float) -> Dict[str, Any]:
    """Document the conversion we refuse to ship."""
    return {
        "forbidden_spread": float(h_epa) * float(n_plays),
        "h_epa": float(h_epa),
        "n_plays": float(n_plays),
        "note": (
            "Do not multiply thin-window EPA h≈0.244 by play count and call it "
            "a spread. Scoring uses shrink_hfa in points."
        ),
        "used": False,
    }
