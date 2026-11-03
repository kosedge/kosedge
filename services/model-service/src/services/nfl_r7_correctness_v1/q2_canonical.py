"""Isolated canonical-state Q2 solver. Concurrent-safe. Does not edit q2.py."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Mapping, Sequence

from src.services.nfl_r7_correctness_v1.franchise import canonical_carry_prior, collapse_to_canonical_slots
from src.services.nfl_t5107u.q2 import (
    A_Q2,
    B_Q2,
    LAMBDA,
    REGRESS_FRAC,
    SEALED_SEASONS,
    AsOfFeatures,
    Game,
    Q2Refuse,
    StrengthSolve,
    _lookup_prev,
    scored_sorted,
    solve_ridge,
    verify_q2_transfer_policy,
)
from src.services.nfl_t5208u.packets import PacketRefuse, history_games_for_q2


def canonical_asof_for_targets(
    history: Sequence[Game],
    targets: Sequence[Game],
    *,
    lam: float = LAMBDA,
    regress_frac: float = REGRESS_FRAC,
    initial_prior: Mapping[str, float] | None = None,
) -> list[AsOfFeatures]:
    """Same as-of rule as q2.asof_for_targets; carry uses canonical slots only."""
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
    incoming = collapse_to_canonical_slots(initial_prior or {})
    for season in seasons:
        sgames = scored_sorted(by_season.get(season, []))
        season_end[season] = solve_ridge(
            sgames, lam, incoming, extra_teams=teams_by_season[season]
        ).ratings
        incoming = canonical_carry_prior(season_end[season], regress_frac)

    out: list[AsOfFeatures] = []
    targets_by_season: dict[int, list[Game]] = defaultdict(list)
    for g in targets:
        targets_by_season[g.season].append(g)
    for season, tlist in targets_by_season.items():
        prevs = [s for s in sorted(season_end) if s < season]
        incoming = (
            canonical_carry_prior(season_end[prevs[-1]], regress_frac)
            if prevs
            else collapse_to_canonical_slots(initial_prior or {})
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


def produce_q2_margin_canonical(
    packet: Mapping[str, object],
    history: list[Mapping[str, object]],
    *,
    lam: float = LAMBDA,
    regress_frac: float = REGRESS_FRAC,
) -> dict[str, object]:
    """Q2 POINT_MARGIN via the isolated canonical-state solver."""
    transfer = verify_q2_transfer_policy(proposed_refit=False)
    target, hist = history_games_for_q2(packet, history)
    feats = canonical_asof_for_targets(
        hist, [target], lam=float(lam), regress_frac=float(regress_frac)
    )
    from src.services.nfl_t5107u.q2 import assert_asof_no_self_target, q2_pm_new

    assert_asof_no_self_target(hist, feats)
    if len(feats) != 1:
        raise PacketRefuse(f"expected 1 Q2 feature row, got {len(feats)}")
    feat = feats[0]
    margin = q2_pm_new(feat.rating_diff)
    return {
        "q2_margin": float(margin),
        "rating_diff": float(feat.rating_diff),
        "n_asof_games": int(feat.n_asof_games),
        "a_q2": A_Q2,
        "b_q2": B_Q2,
        "transfer": transfer,
        "canonical_state_slots": True,
        "solver": "canonical_asof_for_targets",
    }
