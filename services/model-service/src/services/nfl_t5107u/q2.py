"""Frozen Q2 intercept/slope (t5009u / t5044u) — transfer, no refit.

Source pins (do not rewrite the method):
- coefficients / windows: FROZEN_CONFIG_Q2PB_t5009u @ 8155fd194
- ridge as-of: research/q2s_w7w17_t5044u/phase4/q2pb/strength.py @ 8155fd194
- training window: DEV 2013–2016 REG W2–17 (ends 2016 ≤ 2021) → TRANSFER

G1: existing Q2 coefficients transfer because training data ends in 2016.
No DEV-only 2020–21 refit is authorized or performed.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Mapping, Sequence

# Frozen DEV OLS (2013–16 REG W2–17, n_fit=960). Do not refit.
A_Q2 = 2.5637441292077354
B_Q2 = 1.660624056183471
LAMBDA = 20.0
REGRESS_FRAC = 0.5
Q2S_WEIGHT = 0.5

TRAINING_SEASONS = (2013, 2014, 2015, 2016)
TRAINING_END_SEASON = 2016
TRANSFER_MAX_TRAINING_SEASON = 2021
HISTORY_ONLY_SEASONS = (2017,)
Q2_EVAL_SEASONS_ORIGINAL = (2018, 2019, 2020, 2021, 2022)
RESERVE_SEASONS = (2023,)
SEALED_SEASONS = (2024, 2025, 2026)
T5107U_DEV_SEASONS = (2020, 2021)
T5107U_EVAL_SEASONS = (2022, 2023)

FIT_OBJECT_SHA256 = "70db070dad3fcdb4d4ff165ba09b7840c173c232a71c8fcd670ba9c3c0bc5571"
CONFIG_SHA256 = "aa2b47b3f0b504f39b785d0cb6fc2918bb7a36fb5a22242e80fb37707b790d49"
GAMES_SHA256_PREFIX = "4fe1cdd7"
OUTCOMES_SHA256_PREFIX = "50bda875"
ASOF_RULE = "cf514078"
FIT_POLICY = "TRANSFER_FROZEN_DEV_2013_2016"
PARAMETER_LABEL = "FROZEN_Q2PB_DEV_2013_2016_TRANSFER"
PARAMETER_STATUS = "original_frozen"

PRIOR_ALIAS = {"STL": "LAR", "SD": "LAC", "OAK": "LV"}
PRIOR_ALIAS_REVERSE = {v: k for k, v in PRIOR_ALIAS.items()}

REG_WEEKS = tuple(range(1, 19))


class Q2Refuse(ValueError):
    """Fail-closed Q2 (never impute, never silent refit)."""


@dataclass(frozen=True)
class Game:
    season: int
    week: int
    game_id: str
    home: str
    away: str
    kickoff_utc: datetime
    home_score: float | None = None
    away_score: float | None = None
    season_type: str = "REG"

    @property
    def margin(self) -> float | None:
        if self.home_score is None or self.away_score is None:
            return None
        return float(self.home_score) - float(self.away_score)


@dataclass
class StrengthSolve:
    hfa: float
    ratings: dict[str, float]
    n_games: int
    lam: float


@dataclass
class AsOfFeatures:
    game: Game
    home_s: float
    away_s: float
    rating_diff: float
    n_asof_games: int
    hfa: float


def verify_q2_transfer_policy(
    *,
    training_seasons: Sequence[int] = TRAINING_SEASONS,
    proposed_refit: bool = False,
) -> dict[str, object]:
    """Prove frozen coeffs may transfer (training end ≤ 2021). Refuse a new fit."""
    if not training_seasons:
        raise Q2Refuse("training_seasons empty")
    if any(int(s) in SEALED_SEASONS for s in training_seasons):
        raise Q2Refuse("refusing sealed 2024–26 training seasons")
    training_end = max(int(s) for s in training_seasons)
    if training_end > TRANSFER_MAX_TRAINING_SEASON:
        raise Q2Refuse(
            f"training_end={training_end} > {TRANSFER_MAX_TRAINING_SEASON}; "
            "cannot transfer and cannot invent a new algorithm"
        )
    if proposed_refit:
        raise Q2Refuse(
            "G1 transfer holds (training_end="
            f"{training_end}≤{TRANSFER_MAX_TRAINING_SEASON}); "
            "DEV-only 2020–21 refit is not authorized"
        )
    if tuple(int(s) for s in training_seasons) != TRAINING_SEASONS:
        raise Q2Refuse(
            f"frozen training window is {TRAINING_SEASONS}, got {tuple(training_seasons)}"
        )
    return {
        "fit_policy": FIT_POLICY,
        "parameter_label": PARAMETER_LABEL,
        "parameter_status": PARAMETER_STATUS,
        "training_seasons": list(TRAINING_SEASONS),
        "training_end_season": TRAINING_END_SEASON,
        "transfer_max_training_season": TRANSFER_MAX_TRAINING_SEASON,
        "transfer_verified": True,
        "refit_authorized": False,
        "refit_performed": False,
        "a_q2": A_Q2,
        "b_q2": B_Q2,
        "lam": LAMBDA,
        "regress_frac": REGRESS_FRAC,
        "fit_object_sha256": FIT_OBJECT_SHA256,
        "config_sha256": CONFIG_SHA256,
        "proof": (
            f"Q2 DEV OLS trained on REG {TRAINING_SEASONS} only "
            f"(end {TRAINING_END_SEASON} ≤ {TRANSFER_MAX_TRAINING_SEASON}); "
            "coeffs transfer; no 2020–21 intercept/slope refit."
        ),
    }


def q2_pm_new(rating_diff: float, *, a_q2: float = A_Q2, b_q2: float = B_Q2) -> float:
    if (a_q2, b_q2) != (A_Q2, B_Q2):
        raise Q2Refuse("Q2 intercept/slope are frozen; refusing alternate coefficients")
    return A_Q2 + B_Q2 * float(rating_diff)


def _lookup_prev(team: str, prev: Mapping[str, float]) -> float:
    if team in prev:
        return float(prev[team])
    alias = PRIOR_ALIAS.get(team) or PRIOR_ALIAS_REVERSE.get(team)
    if alias and alias in prev:
        return float(prev[alias])
    return 0.0


def carry_prior(prev: Mapping[str, float], regress_frac: float = REGRESS_FRAC) -> dict[str, float]:
    r = float(regress_frac)
    out: dict[str, float] = {}
    keys = set(prev) | set(PRIOR_ALIAS) | set(PRIOR_ALIAS_REVERSE)
    for team in keys:
        out[team] = (1.0 - r) * _lookup_prev(team, prev)
    for team, val in prev.items():
        out.setdefault(team, (1.0 - r) * val)
    return out


def _solve_linear(a: list[list[float]], b: list[float]) -> list[float]:
    """Gaussian elimination with partial pivoting. No numpy dependency."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[pivot][col]) < 1e-14:
            # ill-conditioned: fall back to least-squares-ish diagonal jitter
            m[col][col] += 1e-8
            pivot = col
        if pivot != col:
            m[col], m[pivot] = m[pivot], m[col]
        div = m[col][col]
        if abs(div) < 1e-14:
            raise Q2Refuse("singular ridge system")
        inv = 1.0 / div
        for j in range(col, n + 1):
            m[col][j] *= inv
        for row in range(n):
            if row == col:
                continue
            factor = m[row][col]
            if factor == 0.0:
                continue
            for j in range(col, n + 1):
                m[row][j] -= factor * m[col][j]
    return [m[i][n] for i in range(n)]


def solve_ridge(
    games: Sequence[Game],
    lam: float = LAMBDA,
    prior: Mapping[str, float] | None = None,
    extra_teams: Iterable[str] | None = None,
) -> StrengthSolve:
    scored = [g for g in games if g.margin is not None]
    teams = sorted(
        {g.home for g in scored}
        | {g.away for g in scored}
        | set(prior or {})
        | set(extra_teams or [])
    )
    if not teams:
        return StrengthSolve(hfa=0.0, ratings={}, n_games=0, lam=float(lam))
    idx = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    prior_vec = [0.0] * n
    if prior:
        for t, i in idx.items():
            prior_vec[i] = _lookup_prev(t, prior)
    if not scored:
        return StrengthSolve(
            hfa=0.0,
            ratings={t: float(prior_vec[idx[t]]) for t in teams},
            n_games=0,
            lam=float(lam),
        )

    xtx = [[0.0] * n for _ in range(n)]
    xty = [0.0] * n
    xto = [0.0] * n
    oto = 0.0
    oty = 0.0
    for g in scored:
        i_h = idx[g.home]
        i_a = idx[g.away]
        y = float(g.margin)
        xtx[i_h][i_h] += 1.0
        xtx[i_a][i_a] += 1.0
        xtx[i_h][i_a] -= 1.0
        xtx[i_a][i_h] -= 1.0
        xty[i_h] += y
        xty[i_a] -= y
        xto[i_h] += 1.0
        xto[i_a] -= 1.0
        oto += 1.0
        oty += y

    dim = n + 1
    a = [[0.0] * dim for _ in range(dim)]
    b = [0.0] * dim
    a[0][0] = oto + 1e-8
    b[0] = oty
    for i in range(n):
        a[0][i + 1] = xto[i]
        a[i + 1][0] = xto[i]
        b[i + 1] = xty[i] + float(lam) * prior_vec[i]
        for j in range(n):
            a[i + 1][j + 1] = xtx[i][j] + (float(lam) if i == j else 0.0)

    beta = _solve_linear(a, b)
    hfa = float(beta[0])
    s = beta[1:]
    mean_s = sum(s) / n
    s = [v - mean_s for v in s]
    return StrengthSolve(
        hfa=hfa,
        ratings={t: float(s[idx[t]]) for t in teams},
        n_games=len(scored),
        lam=float(lam),
    )


def scored_sorted(games: Iterable[Game]) -> list[Game]:
    return sorted(
        [g for g in games if g.margin is not None],
        key=lambda g: (g.kickoff_utc, g.game_id),
    )


def asof_for_targets(
    history: Sequence[Game],
    targets: Sequence[Game],
    *,
    lam: float = LAMBDA,
    regress_frac: float = REGRESS_FRAC,
    initial_prior: Mapping[str, float] | None = None,
) -> list[AsOfFeatures]:
    """As-of ratings: only kickoff strictly before the target (cf514078)."""
    if any(g.season in SEALED_SEASONS for g in list(history) + list(targets)):
        raise Q2Refuse("refusing 2024–26 rows")
    by_season: dict[int, list[Game]] = defaultdict(list)
    teams_by_season: dict[int, set[str]] = defaultdict(set)
    for g in history:
        by_season[g.season].append(g)
        teams_by_season[g.season].add(g.home)
        teams_by_season[g.season].add(g.away)
    for g in targets:
        teams_by_season[g.season].add(g.home)
        teams_by_season[g.season].add(g.away)

    seasons = sorted(set(by_season) | {g.season for g in targets})
    season_end: dict[int, dict[str, float]] = {}
    incoming = dict(initial_prior or {})
    for season in seasons:
        sgames = scored_sorted(by_season.get(season, []))
        season_end[season] = solve_ridge(
            sgames, lam, incoming, extra_teams=teams_by_season[season]
        ).ratings
        incoming = carry_prior(season_end[season], regress_frac)

    out: list[AsOfFeatures] = []
    targets_by_season: dict[int, list[Game]] = defaultdict(list)
    for g in targets:
        targets_by_season[g.season].append(g)
    for season, tlist in targets_by_season.items():
        prevs = [s for s in sorted(season_end) if s < season]
        incoming = (
            carry_prior(season_end[prevs[-1]], regress_frac)
            if prevs
            else dict(initial_prior or {})
        )
        sgames = scored_sorted(by_season.get(season, []))
        extra = teams_by_season[season]
        tlist = sorted(tlist, key=lambda g: (g.kickoff_utc, g.game_id))
        cache: dict[datetime, StrengthSolve] = {}
        for g in tlist:
            ko = g.kickoff_utc
            if ko not in cache:
                asof_games = [h for h in sgames if h.kickoff_utc < ko]
                cache[ko] = solve_ridge(asof_games, lam, incoming, extra_teams=extra)
            sol = cache[ko]
            hs = sol.ratings.get(g.home, _lookup_prev(g.home, incoming))
            aws = sol.ratings.get(g.away, _lookup_prev(g.away, incoming))
            out.append(
                AsOfFeatures(
                    game=g,
                    home_s=float(hs),
                    away_s=float(aws),
                    rating_diff=float(hs) - float(aws),
                    n_asof_games=sol.n_games,
                    hfa=sol.hfa,
                )
            )
    return out


def assert_asof_no_self_target(history: Sequence[Game], feats: Sequence[AsOfFeatures]) -> None:
    by_season: dict[int, list[Game]] = defaultdict(list)
    for g in history:
        if g.margin is not None:
            by_season[g.season].append(g)
    for feat in feats:
        g = feat.game
        n = sum(1 for h in by_season[g.season] if h.kickoff_utc < g.kickoff_utc)
        if n != feat.n_asof_games:
            raise Q2Refuse(f"as-of n mismatch {g.game_id}: feat={feat.n_asof_games} recount={n}")
        if any(h.game_id == g.game_id and h.kickoff_utc < g.kickoff_utc for h in by_season[g.season]):
            raise Q2Refuse(f"self-inclusion {g.game_id}")
        # Target result cannot enter its own forecast window.
        if g.margin is not None:
            own = [h for h in by_season[g.season] if h.game_id == g.game_id]
            if own and any(h.kickoff_utc < g.kickoff_utc for h in own):
                raise Q2Refuse(f"target outcome leaked into as-of {g.game_id}")


def parse_kickoff(raw: object) -> datetime:
    if isinstance(raw, datetime):
        dt = raw
        if dt.tzinfo is None:
            raise Q2Refuse("naive kickoff refused (no timezone contract)")
        return dt.astimezone(timezone.utc)
    text = str(raw or "").strip()
    if not text:
        raise Q2Refuse("missing kickoff")
    if text.endswith("Z") or text.endswith("z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError as exc:
        raise Q2Refuse(f"unparseable kickoff {raw!r}") from exc
    if dt.tzinfo is None:
        raise Q2Refuse(f"naive kickoff refused: {raw!r}")
    return dt.astimezone(timezone.utc)
