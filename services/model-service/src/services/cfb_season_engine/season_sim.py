"""Season simulation skeleton — path-coherent team W/L paths.

Foundation pass: team-level only (no full player box path yet). Structure
mirrors NFL season_sim so later passes can deepen without rewiring.
"""

from __future__ import annotations

import random
from collections import defaultdict
from typing import Any, Dict, Optional

from src.services.cfb_season_engine import priors as P
from src.services.cfb_season_engine.team_projection import (
    copy_strength_book,
    evolve_after_game,
    realize_game_scores,
)
from src.services.cfb_season_engine.types import EngineUniverse, SeasonSimResult


def simulate_full_season(
    universe: EngineUniverse,
    *,
    n_sims: int = 50,
    seed: int = 2026,
    engine_version: str = P.ENGINE_VERSION,
    progress_every: Optional[int] = None,
) -> SeasonSimResult:
    """Run N path-coherent season sims (team W/L + strength evolution).

    Skeleton: does not yet emit conference standings, playoff brackets, or
    player season totals. Wins are tallied per team across paths.
    """
    if n_sims < 1:
        raise ValueError("n_sims must be >= 1")
    rng = random.Random(seed)
    schedule = list(universe.schedule)
    if not schedule:
        raise ValueError("Universe has empty schedule")

    win_sums: Dict[str, float] = defaultdict(float)
    win_sq: Dict[str, float] = defaultdict(float)

    for i in range(n_sims):
        strengths = copy_strength_book(universe.teams)
        path_wins: Dict[str, float] = defaultdict(float)
        for game in schedule:
            if game.home_team not in strengths or game.away_team not in strengths:
                continue
            outcome = realize_game_scores(game, strengths, rng=rng)
            home_won = bool(outcome["home_won"])
            if home_won:
                path_wins[game.home_team] += 1.0
            else:
                path_wins[game.away_team] += 1.0
            evolve_after_game(
                strengths,
                home_team=game.home_team,
                away_team=game.away_team,
                home_won=home_won,
                home_score=float(outcome["home_score"]),
                away_score=float(outcome["away_score"]),
                rng=rng,
            )
        for team, w in path_wins.items():
            win_sums[team] += w
            win_sq[team] += w * w
        if progress_every and (i + 1) % progress_every == 0:
            print(f"  cfb-season-engine: {i + 1}/{n_sims} paths")

    team_wins: Dict[str, Dict[str, float]] = {}
    n = float(n_sims)
    for team in universe.team_codes:
        mean = win_sums[team] / n
        var = max(0.0, win_sq[team] / n - mean * mean)
        team_wins[team] = {
            "mean": round(mean, 3),
            "std": round(var ** 0.5, 3),
            "wins_sum_check": round(win_sums[team], 3),
        }

    mean_wins_sum = sum(v["mean"] for v in team_wins.values())
    early = {
        str(w): P.early_season_uncertainty(w) for w in range(1, 5)
    }
    return SeasonSimResult(
        season=universe.season,
        n_sims=n_sims,
        games_per_season=len(schedule),
        engine_version=engine_version,
        team_wins=team_wins,
        sample_path_game_count=len(schedule),
        notes={
            **universe.notes,
            "skeleton": "team W/L paths only; player boxes / CFP bracket deferred",
            "fidelity": "approximate",
        },
        diagnostics={
            "mean_wins_sum": round(mean_wins_sum, 4),
            "expected_wins_sum": float(len(schedule)),
            "early_season_uncertainty": early,
            "week_5_plus": P.early_season_uncertainty(5),
        },
    )


def season_sim_to_dict(result: SeasonSimResult) -> Dict[str, Any]:
    top = sorted(result.team_wins.items(), key=lambda kv: -kv[1]["mean"])[:15]
    return {
        "season": result.season,
        "n_sims": result.n_sims,
        "games_per_season": result.games_per_season,
        "engine_version": result.engine_version,
        "top_teams_by_wins": [{"team": t, **stats} for t, stats in top],
        "team_wins": result.team_wins,
        "sample_path_game_count": result.sample_path_game_count,
        "notes": result.notes,
        "diagnostics": result.diagnostics,
    }


def documentation() -> Dict[str, Any]:
    return {
        "layer": "orchestration",
        "name": "season_sim",
        "module": "src.services.cfb_season_engine.season_sim",
        "status": "skeleton",
        "real_vs_approximate": (
            "Path coherence structure is REAL. Win totals / strength evolution "
            "are APPROXIMATE placeholders pending schedule densify + calibration."
        ),
        "deferred": [
            "conference standings",
            "CFP / playoff bracket",
            "player season totals",
            "injury / portal mid-season shocks",
        ],
    }
