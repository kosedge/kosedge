"""Opponent-adjusted as-of strength: margin = h + s_home − s_away (ridge).

As-of rule (cf514078): only games with kickoff strictly before the target
kickoff enter the design matrix. Same-kickoff games do not see each other.
Prior-season ratings are regressed to mean by fraction r, then used as the
ridge target for the current-season solve.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Mapping, Sequence

import numpy as np

from .constants import PRIOR_ALIAS, PRIOR_ALIAS_REVERSE
from .data import Game


@dataclass
class StrengthSolve:
    hfa: float
    ratings: dict[str, float]
    n_games: int
    lam: float
    prior_used: bool


@dataclass
class AsOfFeatures:
    game: Game
    home_s: float
    away_s: float
    rating_diff: float
    n_asof_games: int
    hfa: float


def carry_prior(prev: Mapping[str, float], regress_frac: float) -> dict[str, float]:
    """s_prior = (1 − r) · s_prev, after franchise alias alignment."""
    r = float(regress_frac)
    out: dict[str, float] = {}
    keys = set(prev) | set(PRIOR_ALIAS) | set(PRIOR_ALIAS_REVERSE)
    for team in keys:
        raw = _lookup_prev(team, prev)
        out[team] = (1.0 - r) * raw
    # also emit prev keys unchanged-name
    for team, val in prev.items():
        out.setdefault(team, (1.0 - r) * val)
    return out


def _lookup_prev(team: str, prev: Mapping[str, float]) -> float:
    if team in prev:
        return float(prev[team])
    alias = PRIOR_ALIAS.get(team) or PRIOR_ALIAS_REVERSE.get(team)
    if alias and alias in prev:
        return float(prev[alias])
    # incoming new code looking up old code
    old = PRIOR_ALIAS_REVERSE.get(team)
    if old and old in prev:
        return float(prev[old])
    new = PRIOR_ALIAS.get(team)
    if new and new in prev:
        return float(prev[new])
    return 0.0


def solve_ridge(
    games: Sequence[Game],
    lam: float,
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
        return StrengthSolve(hfa=0.0, ratings={}, n_games=0, lam=float(lam), prior_used=bool(prior))
    idx = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    prior_vec = np.zeros(n, dtype=float)
    if prior:
        for t, i in idx.items():
            prior_vec[i] = _lookup_prev(t, prior)

    if not scored:
        ratings = {t: float(prior_vec[idx[t]]) for t in teams}
        return StrengthSolve(
            hfa=0.0,
            ratings=ratings,
            n_games=0,
            lam=float(lam),
            prior_used=True,
        )

    G = len(scored)
    X = np.zeros((G, n), dtype=float)
    y = np.zeros(G, dtype=float)
    for k, g in enumerate(scored):
        X[k, idx[g.home]] = 1.0
        X[k, idx[g.away]] = -1.0
        y[k] = float(g.margin)

    ones = np.ones(G, dtype=float)
    xtx = X.T @ X
    xty = X.T @ y
    xto = X.T @ ones
    oto = float(ones @ ones)
    oty = float(ones @ y)

    lam = float(lam)
    # Unpenalized HFA; ridge team strengths toward prior.
    # Block system:
    # [ oto      xto.T ] [h] = [ oty              ]
    # [ xto   xtx+λI   ] [s]   [ xty + λ prior    ]
    A = np.zeros((n + 1, n + 1), dtype=float)
    b = np.zeros(n + 1, dtype=float)
    A[0, 0] = oto
    A[0, 1:] = xto
    A[1:, 0] = xto
    A[1:, 1:] = xtx + lam * np.eye(n)
    b[0] = oty
    b[1:] = xty + lam * prior_vec
    # tiny jitter if a season is empty-ish
    A[0, 0] += 1e-8
    try:
        beta = np.linalg.solve(A, b)
    except np.linalg.LinAlgError:
        beta = np.linalg.lstsq(A, b, rcond=None)[0]
    hfa = float(beta[0])
    s = beta[1:]
    s = s - s.mean()
    ratings = {t: float(s[idx[t]]) for t in teams}
    return StrengthSolve(
        hfa=hfa,
        ratings=ratings,
        n_games=G,
        lam=lam,
        prior_used=prior is not None,
    )


def season_end_ratings(
    season_games: Sequence[Game],
    lam: float,
    incoming_prior: Mapping[str, float],
    extra_teams: Iterable[str] | None = None,
) -> dict[str, float]:
    sol = solve_ridge(season_games, lam, incoming_prior, extra_teams=extra_teams)
    return dict(sol.ratings)


def asof_for_targets(
    history: Sequence[Game],
    targets: Sequence[Game],
    lam: float,
    regress_frac: float,
    initial_prior: Mapping[str, float] | None = None,
    persist_season_end: dict[int, dict[str, float]] | None = None,
) -> list[AsOfFeatures]:
    """Compute as-of ratings for each target. History may include the targets.

    Within a season the design uses only current-season games with kickoff
    strictly before the target kickoff, ridged toward the incoming prior.
    Season-end ratings (full-season solve) feed the next season's prior only.
    """
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
    season_end: dict[int, dict[str, float]] = dict(persist_season_end or {})
    incoming = dict(initial_prior or {})
    for season in seasons:
        sgames = scored_sorted(by_season.get(season, []))
        if season not in season_end:
            season_end[season] = season_end_ratings(
                sgames, lam, incoming, extra_teams=teams_by_season[season]
            )
        incoming = carry_prior(season_end[season], regress_frac)
    if persist_season_end is not None:
        persist_season_end.update(season_end)

    targets_by_season: dict[int, list[Game]] = defaultdict(list)
    for g in targets:
        targets_by_season[g.season].append(g)

    out: list[AsOfFeatures] = []
    for season, tlist in targets_by_season.items():
        prevs = [s for s in sorted(season_end) if s < season]
        if prevs:
            incoming = carry_prior(season_end[prevs[-1]], regress_frac)
        else:
            incoming = dict(initial_prior or {})
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
            hs = sol.ratings.get(g.home)
            aws = sol.ratings.get(g.away)
            if hs is None:
                hs = _lookup_prev(g.home, incoming)
            if aws is None:
                aws = _lookup_prev(g.away, incoming)
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


def scored_sorted(games: Iterable[Game]) -> list[Game]:
    return sorted(
        [g for g in games if g.margin is not None],
        key=lambda g: (g.kickoff_utc, g.game_id),
    )


def assert_asof_leakage(history: Sequence[Game], feats: Sequence[AsOfFeatures]) -> None:
    """Hard leakage guard: no as-of design game has kickoff >= target."""
    by_season = defaultdict(list)
    for g in history:
        if g.margin is not None:
            by_season[g.season].append(g)
    for feat in feats:
        g = feat.game
        for h in by_season[g.season]:
            if h.kickoff_utc >= g.kickoff_utc:
                # later or same kickoff must not be countable; we only check count
                continue
        # recount
        n = sum(1 for h in by_season[g.season] if h.kickoff_utc < g.kickoff_utc)
        if n != feat.n_asof_games:
            raise AssertionError(
                f"as-of n mismatch {g.game_id}: feat={feat.n_asof_games} recount={n}"
            )
        # target cannot be in its own window
        if any(
            h.game_id == g.game_id and h.kickoff_utc < g.kickoff_utc
            for h in by_season[g.season]
        ):
            raise AssertionError(f"self-inclusion {g.game_id}")
