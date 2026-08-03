"""Query API: future game → player box-score distributions.

Runs Layers 2–4 for ``n_replicates`` Monte Carlo draws at the current
(universe) strength book — no in-path evolution, since the query is for a
single future game's marginal distribution. Season-long coherence lives in
``season_sim.simulate_full_season``; this endpoint answers "what does the
box look like for this matchup right now?"
"""

from __future__ import annotations

import random
import statistics
from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence

from src.services.nfl_season_engine.game_script import (
    build_game_script,
    summarize_script_distribution,
)
from src.services.nfl_season_engine.player_usage import allocate_game_usage
from src.services.nfl_season_engine.production import (
    box_score_to_stat_dict,
    produce_box_scores,
)
from src.services.nfl_season_engine.types import (
    EngineUniverse,
    GameBoxProjection,
    ScheduledGame,
    dist_block,
)

DEFAULT_SEASON_ENGINE_VERSION = "nfl-season-engine-v1"

_POSITION_STATS = {
    "QB": ("pass_yards", "pass_tds", "ints", "rush_yards"),
    "RB": ("rush_yards", "rush_tds", "rec_yards", "receptions"),
    "WR": ("rec_yards", "receptions", "rec_tds"),
    "TE": ("rec_yards", "receptions", "rec_tds"),
}


def _find_game(
    universe: EngineUniverse,
    *,
    home_team: str,
    away_team: str,
    week: Optional[int] = None,
    game_id: Optional[str] = None,
) -> ScheduledGame:
    home = "LA" if home_team == "LAR" else home_team
    away = "LA" if away_team == "LAR" else away_team
    candidates = [
        g
        for g in universe.schedule
        if g.home_team == home and g.away_team == away
        and (week is None or g.week == week)
        and (game_id is None or g.game_id == game_id)
    ]
    if candidates:
        return candidates[0]
    # Synthetic future game when not on the loaded schedule.
    return ScheduledGame(
        season=universe.season,
        week=int(week or 1),
        game_id=game_id or f"{universe.season}-W{int(week or 1):02d}-{away}@{home}",
        home_team=home,
        away_team=away,
    )


def _summarize(values: Sequence[float]) -> Dict[str, float]:
    if not values:
        return dist_block(0.0, 0.0, 0.0, 0.0, 0.0)
    ordered = sorted(values)
    n = len(ordered)
    mean = statistics.fmean(values)
    std = statistics.pstdev(values) if n > 1 else 0.0
    return dist_block(
        mean,
        std,
        ordered[max(0, int(round((n - 1) * 0.10)))],
        ordered[max(0, int(round((n - 1) * 0.50)))],
        ordered[max(0, int(round((n - 1) * 0.90)))],
    )


def project_game_player_boxes(
    universe: EngineUniverse,
    *,
    home_team: str,
    away_team: str,
    week: Optional[int] = None,
    game_id: Optional[str] = None,
    n_replicates: int = 500,
    seed: int = 7,
    engine_version: str = DEFAULT_SEASON_ENGINE_VERSION,
) -> GameBoxProjection:
    """Monte Carlo player box projections for one future game."""
    n_replicates = max(50, int(n_replicates))
    game = _find_game(
        universe,
        home_team=home_team,
        away_team=away_team,
        week=week,
        game_id=game_id,
    )
    rng = random.Random(seed)

    scripts = []
    accum: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    meta: Dict[str, Dict[str, str]] = {}

    for _ in range(n_replicates):
        script, _outcome = build_game_script(game, universe.strengths, rng=rng, realized=True)
        scripts.append(script)
        usage = allocate_game_usage(script, universe.rosters, rng=rng)
        boxes = produce_box_scores(
            usage_rows=usage,
            roles=universe.rosters,
            script=script,
            strengths=universe.strengths,
            rng=rng,
        )
        for box in boxes:
            meta[box.player_key] = {
                "player_key": box.player_key,
                "player_name": box.player_name,
                "team": box.team,
                "position": box.position,
            }
            stats = box_score_to_stat_dict(box)
            for k, v in stats.items():
                accum[box.player_key][k].append(float(v))
            # Always keep full raw counters for transparency.
            accum[box.player_key]["pass_attempts"].append(float(box.pass_attempts))
            accum[box.player_key]["carries"].append(float(box.carries))
            accum[box.player_key]["targets"].append(float(box.targets))

    players: List[Dict[str, Any]] = []
    for key, info in meta.items():
        pos = info["position"]
        wanted = _POSITION_STATS.get(pos, ("rec_yards", "receptions", "rec_tds"))
        distributions = {stat: _summarize(accum[key].get(stat, [])) for stat in wanted}
        # Attach volume context.
        distributions["pass_attempts"] = _summarize(accum[key].get("pass_attempts", []))
        distributions["carries"] = _summarize(accum[key].get("carries", []))
        distributions["targets"] = _summarize(accum[key].get("targets", []))
        point = {stat: distributions[stat]["mean"] for stat in wanted}
        players.append(
            {
                **info,
                "point_estimate": point,
                "distributions": distributions,
            }
        )

    def _sort_key(row: Dict[str, Any]) -> float:
        pe = row.get("point_estimate") or {}
        pos = row.get("position")
        if pos == "QB":
            return float(pe.get("pass_yards") or 0.0)
        if pos == "RB":
            return float(pe.get("rush_yards") or 0.0)
        return float(pe.get("rec_yards") or 0.0)

    players.sort(key=_sort_key, reverse=True)

    return GameBoxProjection(
        season=universe.season,
        week=game.week,
        game_id=game.game_id,
        home_team=game.home_team,
        away_team=game.away_team,
        n_replicates=n_replicates,
        engine_version=engine_version,
        game_script_summary=summarize_script_distribution(scripts),
        players=players,
        notes={
            **dict(universe.notes),
            "query_mode": "single_game_marginal_mc",
            "layers": "2=game_script → 3=player_usage → 4=production (strengths frozen at query-time book)",
        },
    )
