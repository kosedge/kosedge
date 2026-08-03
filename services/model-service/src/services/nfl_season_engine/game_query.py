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

from src.services.nfl_season_engine.calibration import ENGINE_VERSION
from src.services.nfl_season_engine.game_script import (
    build_game_script,
    summarize_script_distribution,
)
from src.services.nfl_season_engine.injury_paths import (
    InjuryPath,
    apply_injury_paths_for_week,
    injury_paths_to_dicts,
    summarize_adjustments,
)
from src.services.nfl_season_engine.player_usage import (
    allocate_game_usage,
    share_integrity_summary,
    usage_share_diagnostics,
)
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
from src.services.nfl_season_engine.usage_roles import annotate_usage_roles

DEFAULT_SEASON_ENGINE_VERSION = ENGINE_VERSION

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
    injury_paths: Optional[Sequence[InjuryPath]] = None,
    include_diagnostics: bool = False,
) -> GameBoxProjection:
    """Monte Carlo player box projections for one future game.

    When ``include_diagnostics`` is True, attach structured usage shares,
    script/personnel state, share-integrity checks, and injury availability
    applied for the query week (kept off by default to avoid bloating
    responses).
    """
    n_replicates = max(50, int(n_replicates))
    game = _find_game(
        universe,
        home_team=home_team,
        away_team=away_team,
        week=week,
        game_id=game_id,
    )
    rng = random.Random(seed)
    paths = list(injury_paths or [])
    week_rosters, week_strengths, adjustments = apply_injury_paths_for_week(
        universe.rosters,
        universe.strengths,
        paths,
        week=game.week,
    )

    scripts = []
    accum: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    meta: Dict[str, Dict[str, str]] = {}
    usage_role_by_key: Dict[str, str] = {}
    personnel_by_key: Dict[str, str] = {}
    script_state_by_key: Dict[str, str] = {}
    # Neutral-script share dump for inspectability (pre-MC).
    home_roles = annotate_usage_roles(week_rosters.get(game.home_team, []))
    away_roles = annotate_usage_roles(week_rosters.get(game.away_team, []))
    for role in list(home_roles) + list(away_roles):
        usage_role_by_key[role.player_key] = role.usage_role

    for _ in range(n_replicates):
        script, _outcome = build_game_script(game, week_strengths, rng=rng, realized=True)
        scripts.append(script)
        usage = allocate_game_usage(script, week_rosters, rng=rng)
        boxes = produce_box_scores(
            usage_rows=usage,
            roles=week_rosters,
            script=script,
            strengths=week_strengths,
            rng=rng,
        )
        for u in usage:
            if u.usage_role:
                usage_role_by_key[u.player_key] = u.usage_role
            if u.personnel:
                personnel_by_key[u.player_key] = u.personnel
            script_state_by_key[u.player_key] = u.script
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
                "usage_role": usage_role_by_key.get(key, ""),
                "personnel": personnel_by_key.get(key, ""),
                "script": script_state_by_key.get(key, ""),
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

    on_schedule = any(
        g.home_team == game.home_team
        and g.away_team == game.away_team
        and g.week == game.week
        for g in universe.schedule
    )
    notes = {
        **dict(universe.notes),
        "query_mode": "single_game_marginal_mc",
        "layers": (
            "1=injury-adjusted strength → 2=game_script → 3=player_usage → 4=production "
            "(strengths frozen at query-time book + week injury shocks)"
        ),
        "schedule_match": "on_loaded_schedule" if on_schedule else "synthetic_matchup",
    }
    if paths:
        notes["injury_path_count"] = str(len(paths))
        notes["injury_active_adjustments"] = str(len(adjustments))

    diagnostics: Dict[str, Any] = {}
    if include_diagnostics:
        diagnostics = {
            "usage_shares_home": usage_share_diagnostics(
                home_roles, script="neutral", pass_rate=0.58
            ),
            "usage_shares_away": usage_share_diagnostics(
                away_roles, script="neutral", pass_rate=0.58
            ),
            "share_integrity_home": share_integrity_summary(
                home_roles, script="neutral", pass_rate=0.58
            ),
            "share_integrity_away": share_integrity_summary(
                away_roles, script="neutral", pass_rate=0.58
            ),
            "injury_paths": injury_paths_to_dicts(paths) if paths else [],
            "injury_adjustments": summarize_adjustments(adjustments),
            "game_script_summary": summarize_script_distribution(scripts),
            "schedule_match": notes["schedule_match"],
            "seed": seed,
        }

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
        notes=notes,
        diagnostics=diagnostics,
    )
