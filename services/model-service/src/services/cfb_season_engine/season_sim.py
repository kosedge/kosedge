"""Season simulation — path-coherent team W/L paths with week samples.

Uses Layers 1–4 (roster / QB / position groups / team projection) via the
composed strength book. Full-season paths read the official ESPN slate when
``slate_complete``; otherwise win tables stay incomplete / not final.
Research only — used_in_spread stays false. CFP/natty stay stub.
"""

from __future__ import annotations

import random
import statistics
from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence

from src.services.cfb_season_engine import priors as P
from src.services.cfb_season_engine.conferences import conference_for
from src.services.cfb_season_engine.fbs_universe import is_official_fbs
from src.services.cfb_season_engine.team_projection import (
    copy_strength_book,
    evolve_after_game,
    realize_game_scores,
)
from src.services.cfb_season_engine.types import EngineUniverse, SeasonSimResult, dist_block


def _dist_from_values(values: Sequence[float]) -> Dict[str, float]:
    clean = [float(v) for v in values]
    if not clean:
        return dist_block(0.0, 0.0, 0.0, 0.0, 0.0)
    ordered = sorted(clean)
    n = len(ordered)
    mean = statistics.fmean(clean)
    std = statistics.pstdev(clean) if n > 1 else 0.0

    def _pct(p: float) -> float:
        return ordered[max(0, min(n - 1, int(round((n - 1) * p))))]

    return dist_block(mean, std, _pct(0.10), _pct(0.50), _pct(0.90))


def _simulate_one_path(
    universe: EngineUniverse,
    *,
    rng: random.Random,
    collect_week_sample: bool = False,
) -> Dict[str, Any]:
    strengths = copy_strength_book(universe.teams)
    path_wins: Dict[str, float] = defaultdict(float)
    conf_wins: Dict[str, float] = defaultdict(float)
    conf_games: Dict[str, float] = defaultdict(float)
    week_rows: List[Dict[str, Any]] = []
    schedule = sorted(universe.schedule, key=lambda g: (g.week, g.game_id))

    for game in schedule:
        if game.home_team not in strengths or game.away_team not in strengths:
            continue
        outcome = realize_game_scores(game, strengths, rng=rng)
        home_won = bool(outcome["home_won"])
        if home_won:
            path_wins[game.home_team] += 1.0
            winner, loser = game.home_team, game.away_team
        else:
            path_wins[game.away_team] += 1.0
            winner, loser = game.away_team, game.home_team

        home_conf = conference_for(game.home_team, universe.conferences)
        away_conf = conference_for(game.away_team, universe.conferences)
        if home_conf == away_conf and home_conf != "Independent":
            conf_games[game.home_team] += 1.0
            conf_games[game.away_team] += 1.0
            if home_won:
                conf_wins[game.home_team] += 1.0
            else:
                conf_wins[game.away_team] += 1.0

        if collect_week_sample:
            week_rows.append(
                {
                    "week": game.week,
                    "game_id": game.game_id,
                    "home_team": game.home_team,
                    "away_team": game.away_team,
                    "home_score": round(float(outcome["home_score"]), 1),
                    "away_score": round(float(outcome["away_score"]), 1),
                    "winner": winner,
                    "loser": loser,
                    "neutral_site": game.neutral_site,
                    "early_season": 0 <= game.week <= P.EARLY_SEASON_LAST_WEEK,
                }
            )

        evolve_after_game(
            strengths,
            home_team=game.home_team,
            away_team=game.away_team,
            home_won=home_won,
            home_score=float(outcome["home_score"]),
            away_score=float(outcome["away_score"]),
            week=game.week,
            rng=rng,
        )

    return {
        "wins": dict(path_wins),
        "conf_wins": dict(conf_wins),
        "conf_games": dict(conf_games),
        "week_rows": week_rows,
    }


def simulate_full_season(
    universe: EngineUniverse,
    *,
    n_sims: int = 50,
    seed: int = 2026,
    engine_version: str = P.ENGINE_VERSION,
    progress_every: Optional[int] = None,
) -> SeasonSimResult:
    """Run N path-coherent season sims (team W/L + mild strength evolution)."""
    if n_sims < 1:
        raise ValueError("n_sims must be >= 1")
    rng = random.Random(seed)
    schedule = list(universe.schedule)
    if not schedule:
        raise ValueError("Universe has empty schedule")

    win_paths: Dict[str, List[float]] = {t: [] for t in universe.team_codes}
    conf_win_sums: Dict[str, float] = defaultdict(float)
    conf_game_sums: Dict[str, float] = defaultdict(float)
    week_sample: List[Dict[str, Any]] = []

    for i in range(n_sims):
        collect = i == 0
        path = _simulate_one_path(universe, rng=rng, collect_week_sample=collect)
        if collect:
            week_sample = path["week_rows"]
        for team in universe.team_codes:
            win_paths[team].append(float(path["wins"].get(team, 0.0)))
        for team, w in path["conf_wins"].items():
            conf_win_sums[team] += w
        for team, g in path["conf_games"].items():
            conf_game_sums[team] += g
        if progress_every and (i + 1) % progress_every == 0:
            print(f"  cfb-season-engine: {i + 1}/{n_sims} paths")

    team_wins: Dict[str, Dict[str, float]] = {}
    for team, values in win_paths.items():
        dist = _dist_from_values(values)
        team_wins[team] = dist

    ranking = sorted(
        (
            {
                "team": team,
                "conference": conference_for(team, universe.conferences),
                **stats,
            }
            for team, stats in team_wins.items()
        ),
        key=lambda row: (-row["mean"], -row["p50"], row["team"]),
    )
    top_for_rank = []
    for idx, row in enumerate(ranking, start=1):
        item = dict(row)
        item["rank"] = idx
        top_for_rank.append(item)

    # Optional conference standings (mean conf wins) — cheap from path aggregates.
    by_conf: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    n = float(n_sims)
    for team in universe.team_codes:
        conf = conference_for(team, universe.conferences)
        if conf == "Independent":
            continue
        cg = conf_game_sums[team] / n
        if cg < 0.5:
            continue
        by_conf[conf].append(
            {
                "team": team,
                "conf_wins_mean": round(conf_win_sums[team] / n, 3),
                "conf_games_mean": round(cg, 3),
                "wins_mean": team_wins[team]["mean"],
            }
        )
    conference_standings: Dict[str, List[Dict[str, Any]]] = {}
    for conf, rows in by_conf.items():
        conference_standings[conf] = sorted(
            rows, key=lambda r: (-r["conf_wins_mean"], -r["wins_mean"], r["team"])
        )

    mean_wins_sum = sum(v["mean"] for v in team_wins.values())
    teams_with_wins = sum(1 for v in team_wins.values() if v["mean"] > 0.05)
    early = {str(w): P.early_season_uncertainty(w) for w in range(1, 5)}
    slate_complete = str(universe.notes.get("slate_complete", "")).lower() == "true"
    official_schedule = str(universe.notes.get("official_schedule", "")).lower() == "true"
    win_tables_status = (
        "research_limited" if slate_complete else "incomplete_slate_not_final"
    )

    return SeasonSimResult(
        season=universe.season,
        n_sims=n_sims,
        games_per_season=len(schedule),
        engine_version=engine_version,
        team_wins=team_wins,
        sample_path_game_count=len(schedule),
        week_by_week_sample=week_sample,
        ranking=top_for_rank,
        conference_standings=conference_standings,
        notes={
            **universe.notes,
            "season_sim": (
                "path-coherent team W/L with mild strength evolution + early noise; "
                "player boxes / CFP bracket deferred"
            ),
            "fidelity": "approximate",
            "schedule_fidelity": universe.notes.get("schedule_fidelity", "approximate"),
            "win_tables_status": win_tables_status,
            "win_tables_final": "false",
            "used_in_spread": "false",
        },
        diagnostics={
            "mean_wins_sum": round(mean_wins_sum, 4),
            "expected_wins_sum": float(len(schedule)),
            "teams_with_positive_mean_wins": teams_with_wins,
            "team_count": len(universe.team_codes),
            "official_fbs_in_ranking": sum(
                1 for row in ranking if is_official_fbs(str(row["team"]))
            ),
            "slate_complete": slate_complete,
            "official_schedule": official_schedule,
            "win_tables_status": win_tables_status,
            "win_tables_final": False,
            "used_in_spread": False,
            "cfp_make": None,
            "natty": None,
            "early_season_uncertainty": early,
            "early_season_narrowing": P.early_season_narrowing_schedule(),
            "week_5_plus": P.early_season_uncertainty(5),
            "week_sample_path_index": 0,
            "conference_count": len(conference_standings),
            "strength_evolution": "mild + week-indexed early noise",
            "variable_hfa": True,
            "coaching_continuity": True,
            "hfa_baseline_points": P.HFA_BASELINE_POINTS,
            "layers_in_path": [
                "roster",
                "qb",
                "position_groups",
                "variable_hfa",
                "coaching_continuity",
            ],
        },
    )


def season_sim_to_dict(result: SeasonSimResult) -> Dict[str, Any]:
    top = result.ranking[:25] if result.ranking else []
    # Week-by-week: group sample path by week for readability.
    by_week: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in result.week_by_week_sample:
        by_week[str(row["week"])].append(row)

    return {
        "season": result.season,
        "n_sims": result.n_sims,
        "games_per_season": result.games_per_season,
        "engine_version": result.engine_version,
        "top_teams_by_wins": top,
        "ranking": result.ranking,
        "team_wins": result.team_wins,
        "week_by_week_sample": result.week_by_week_sample,
        "week_by_week_grouped": dict(sorted(by_week.items(), key=lambda kv: int(kv[0]))),
        "conference_standings": result.conference_standings,
        "sample_path_game_count": result.sample_path_game_count,
        "notes": result.notes,
        "diagnostics": result.diagnostics,
        "slate_complete": bool(result.diagnostics.get("slate_complete")),
        "win_tables_status": result.diagnostics.get("win_tables_status"),
        "win_tables_final": False,
        "used_in_spread": False,
        "cfp_make": None,
        "natty": None,
    }


def documentation() -> Dict[str, Any]:
    return {
        "layer": "orchestration",
        "name": "season_sim",
        "module": "src.services.cfb_season_engine.season_sim",
        "status": "season_paths",
        "real_vs_approximate": (
            "Path coherence structure is REAL. Official ESPN slate is used when "
            "packaged. Win totals / strength evolution / conference standings "
            "remain APPROXIMATE research (used_in_spread=false). Incomplete "
            "slate refuses final win tables. CFP/natty stay stub."
        ),
        "outputs": [
            "per-team wins distribution (mean/std/p10/p50/p90)",
            "ranking-ish standings by mean wins",
            "week-by-week results sample (path 0)",
            "optional conference standings (approximate affiliations)",
            "early-season uncertainty narrowing schedule",
        ],
        "deferred": [
            "CFP / playoff bracket (P4 stub)",
            "player season totals",
            "injury / portal mid-season shocks",
            "used_in_spread / KEI",
        ],
    }
