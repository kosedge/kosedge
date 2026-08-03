"""Season-path orchestrator: walk ~272 games through all four layers.

Each season replicate:
1. Copy initial team strengths
2. For each scheduled game (week order):
   - Layer 2 game script (+ realized scores)
   - Layer 3 player usage
   - Layer 4 production → append to path player totals
   - Layer 1 strength evolution from realized outcome
3. Aggregate wins + player totals across N replicates

Path coherence: within one replicate, player/team totals are the sum of
that path's game boxes; strengths evolve and affect later weeks.
"""

from __future__ import annotations

import random
import statistics
from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence

from src.services.nfl_season_engine.calibration import ENGINE_VERSION
from src.services.nfl_season_engine.game_script import build_game_script
from src.services.nfl_season_engine.injury_paths import (
    InjuryPath,
    apply_injury_paths_for_week,
    injury_paths_to_dicts,
)
from src.services.nfl_season_engine.player_usage import allocate_game_usage
from src.services.nfl_season_engine.production import produce_box_scores
from src.services.nfl_season_engine.team_strength import (
    copy_strength_book,
    evolve_after_game,
)
from src.services.nfl_season_engine.types import EngineUniverse, SeasonSimResult

DEFAULT_SEASON_ENGINE_VERSION = ENGINE_VERSION

_STAT_KEYS = (
    "pass_yards",
    "pass_tds",
    "ints",
    "rush_yards",
    "rush_tds",
    "rec_yards",
    "receptions",
    "rec_tds",
    "games",
)


def _empty_player_accum(meta: Dict[str, str]) -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "player_key": meta["player_key"],
        "player_name": meta["player_name"],
        "team": meta["team"],
        "position": meta["position"],
    }
    for k in _STAT_KEYS:
        row[k] = 0.0
    return row


def simulate_one_season_path(
    universe: EngineUniverse,
    *,
    rng: random.Random,
    injury_paths: Optional[Sequence[InjuryPath]] = None,
) -> Dict[str, Any]:
    """Simulate one full season path. Returns wins + player totals for the path."""
    strengths = copy_strength_book(universe.strengths)
    wins: Dict[str, int] = {t: 0 for t in universe.teams}
    player_totals: Dict[str, Dict[str, Any]] = {}
    paths = list(injury_paths or [])

    # Seed player meta once from rosters.
    for team, roles in universe.rosters.items():
        for role in roles:
            player_totals[role.player_key] = _empty_player_accum(
                {
                    "player_key": role.player_key,
                    "player_name": role.player_name,
                    "team": team,
                    "position": role.position,
                }
            )

    schedule = sorted(universe.schedule, key=lambda g: (g.week, g.game_id))
    for game in schedule:
        week_rosters, week_strengths, _adj = apply_injury_paths_for_week(
            universe.rosters,
            strengths,
            paths,
            week=game.week,
        )
        script, outcome = build_game_script(game, week_strengths, rng=rng, realized=True)
        usage = allocate_game_usage(script, week_rosters, rng=rng)
        boxes = produce_box_scores(
            usage_rows=usage,
            roles=week_rosters,
            script=script,
            strengths=week_strengths,
            rng=rng,
        )
        for box in boxes:
            row = player_totals.get(box.player_key)
            if row is None:
                continue
            row["pass_yards"] += box.pass_yards
            row["pass_tds"] += box.pass_tds
            row["ints"] += box.ints
            row["rush_yards"] += box.rush_yards
            row["rush_tds"] += box.rush_tds
            row["rec_yards"] += box.rec_yards
            row["receptions"] += box.receptions
            row["rec_tds"] += box.rec_tds
            row["games"] += 1.0

        home_won = bool(outcome["home_won"])
        if home_won:
            wins[game.home_team] += 1
        else:
            wins[game.away_team] += 1

        # Evolve the path strength book (no temporary injury overlay).
        evolve_after_game(
            strengths,
            home_team=game.home_team,
            away_team=game.away_team,
            home_won=home_won,
            home_score=float(outcome["home_score"]),
            away_score=float(outcome["away_score"]),
            rng=rng,
        )

    return {"wins": wins, "players": player_totals, "games": len(schedule)}


def simulate_full_season(
    universe: EngineUniverse,
    *,
    n_sims: int = 100,
    seed: int = 2026,
    engine_version: str = DEFAULT_SEASON_ENGINE_VERSION,
    progress_every: Optional[int] = None,
    injury_paths: Optional[List[InjuryPath]] = None,
) -> SeasonSimResult:
    """Run ``n_sims`` path-coherent season simulations."""
    n_sims = max(1, int(n_sims))
    rng = random.Random(seed)
    paths = list(injury_paths or [])

    win_samples: Dict[str, List[int]] = {t: [] for t in universe.teams}
    player_samples: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    player_meta: Dict[str, Dict[str, str]] = {}
    sample_games = 0

    for i in range(n_sims):
        path = simulate_one_season_path(universe, rng=rng, injury_paths=paths)
        sample_games = int(path["games"])
        for team, w in path["wins"].items():
            win_samples[team].append(int(w))
        for key, row in path["players"].items():
            if key not in player_meta:
                player_meta[key] = {
                    "player_key": row["player_key"],
                    "player_name": row["player_name"],
                    "team": row["team"],
                    "position": row["position"],
                }
            for stat in _STAT_KEYS:
                player_samples[key][stat].append(float(row[stat]))
        if progress_every and (i + 1) % progress_every == 0:
            print(f"  season-engine: {i + 1}/{n_sims} paths")

    team_wins: Dict[str, Dict[str, float]] = {}
    for team, samples in win_samples.items():
        ordered = sorted(samples)
        team_wins[team] = {
            "mean": round(statistics.fmean(samples), 3),
            "p10": float(ordered[max(0, int(round((len(ordered) - 1) * 0.10)))]),
            "p50": float(ordered[max(0, int(round((len(ordered) - 1) * 0.50)))]),
            "p90": float(ordered[max(0, int(round((len(ordered) - 1) * 0.90)))]),
        }

    player_rows: List[Dict[str, Any]] = []
    for key, meta in player_meta.items():
        samples = player_samples[key]
        row: Dict[str, Any] = dict(meta)
        for stat in _STAT_KEYS:
            vals = samples.get(stat) or [0.0]
            ordered = sorted(vals)
            mean = statistics.fmean(vals)
            std = statistics.pstdev(vals) if len(vals) > 1 else 0.0
            row[f"{stat}_mean"] = round(mean, 3)
            row[f"{stat}_std"] = round(std, 3)
            row[f"{stat}_p10"] = round(ordered[max(0, int(round((len(ordered) - 1) * 0.10)))], 3)
            row[f"{stat}_p50"] = round(ordered[max(0, int(round((len(ordered) - 1) * 0.50)))], 3)
            row[f"{stat}_p90"] = round(ordered[max(0, int(round((len(ordered) - 1) * 0.90)))], 3)
        player_rows.append(row)

    # Rank skill leaders by position-primary volume for readability.
    def _primary_sort(r: Dict[str, Any]) -> float:
        pos = str(r.get("position") or "")
        if pos == "QB":
            return float(r.get("pass_yards_mean") or 0.0)
        if pos == "RB":
            return float(r.get("rush_yards_mean") or 0.0)
        return float(r.get("rec_yards_mean") or 0.0)

    player_rows.sort(key=_primary_sort, reverse=True)

    win_means = [v["mean"] for v in team_wins.values()]
    win_mean_sorted = sorted(win_means)
    win_spread = (
        round(win_mean_sorted[-1] - win_mean_sorted[0], 3) if win_mean_sorted else 0.0
    )
    win_stdev = (
        round(statistics.pstdev(win_means), 3) if len(win_means) > 1 else 0.0
    )

    notes = dict(universe.notes)
    if paths:
        notes["injury_paths"] = f"{len(paths)} path(s) applied week-by-week inside sim"
        notes["injury_paths_detail"] = str(injury_paths_to_dicts(paths))

    return SeasonSimResult(
        season=universe.season,
        n_sims=n_sims,
        games_per_season=sample_games,
        engine_version=engine_version,
        team_wins=team_wins,
        player_season_totals=player_rows,
        sample_path_game_count=sample_games,
        notes=notes,
        diagnostics={
            "teams": len(universe.teams),
            "rostered_players": len(player_rows),
            "seed": seed,
            "mean_wins_sum": round(sum(v["mean"] for v in team_wins.values()), 3),
            "win_mean_min": round(win_mean_sorted[0], 3) if win_mean_sorted else 0.0,
            "win_mean_max": round(win_mean_sorted[-1], 3) if win_mean_sorted else 0.0,
            "win_mean_spread": win_spread,
            "win_mean_stdev": win_stdev,
            "injury_path_count": len(paths),
            "injury_paths": injury_paths_to_dicts(paths) if paths else [],
        },
    )
