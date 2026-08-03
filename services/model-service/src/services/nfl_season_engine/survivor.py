"""Survivor-pool evaluation on top of the hierarchical season engine.

Runs many **team W/L-only** season paths (Layers 1–2 + injury strength
shocks; skips Layers 3–4 player boxes for speed) and aggregates a
week × team win matrix for survivor decision support.

Public questions answered
-------------------------
1. Given ``already_used`` teams, what are the best remaining picks in week N?
2. How often does team Y win in week N across season sims?

Path-value / pick-now heuristics (inspectable, not black-box EV)
---------------------------------------------------------------
Let ``p[t, w]`` = fraction of sims where team ``t`` wins its week-``w`` game
(0 if the team is on bye / has no game that week in a given path — see
``games_scheduled`` / ``win_rate`` notes).

For evaluation week ``W`` and remaining teams ``R`` (not in ``already_used``):

* ``this_week_wp`` = ``p[t, W]``
* Future weeks ``F(t)`` = scheduled weeks ``w > W`` for team ``t``
* ``future_avg_wp`` = mean ``p[t, w]`` over ``F(t)`` (0 if empty)
* ``future_max_wp`` = max ``p[t, w]`` over ``F(t)`` (0 if empty)
* ``premium_spots`` = count of ``w in F(t)`` with ``p[t, w] >= PREMIUM_WP``
* ``save_score`` (future value, 0–1 scale)::

      save_score = 0.50 * future_avg_wp
                 + 0.35 * future_max_wp
                 + 0.15 * min(1.0, premium_spots / 3.0)

* ``pick_now_score`` (higher → lean pick this week)::

      pick_now_score = this_week_wp
                     - SAVE_PENALTY * save_score
                     + EDGE_BONUS * (this_week_wp - future_avg_wp)

Default knobs: ``PREMIUM_WP = 0.70``, ``SAVE_PENALTY = 0.45``,
``EDGE_BONUS = 0.10``.

Ranked recommendations default to ``pick_now_score`` descending among
remaining teams that play in week ``W``.
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from src.services.nfl_season_engine.calibration import ENGINE_VERSION
from src.services.nfl_season_engine.game_script import build_game_script
from src.services.nfl_season_engine.injury_paths import (
    InjuryPath,
    apply_injury_paths_for_week,
    injury_paths_to_dicts,
)
from src.services.nfl_season_engine.team_strength import (
    copy_strength_book,
    evolve_after_game,
)
from src.services.nfl_season_engine.types import EngineUniverse, ScheduledGame

DEFAULT_SEASON_ENGINE_VERSION = ENGINE_VERSION

# Documented scoring knobs (exposed in API diagnostics).
PREMIUM_WP = 0.70
SAVE_PENALTY = 0.45
EDGE_BONUS = 0.10
SAVE_WEIGHT_AVG = 0.50
SAVE_WEIGHT_MAX = 0.35
SAVE_WEIGHT_PREMIUM = 0.15
PREMIUM_SPOT_CAP = 3.0

FORMULA_NOTES = {
    "save_score": (
        "0.50*future_avg_wp + 0.35*future_max_wp + "
        "0.15*min(1, premium_spots/3); premium = future week WP >= 0.70"
    ),
    "pick_now_score": (
        "this_week_wp - 0.45*save_score + 0.10*(this_week_wp - future_avg_wp); "
        "high this-week WP + low unique future value → pick now"
    ),
    "win_rate": "wins_in_week / n_sims (bye / missing game counts as non-win)",
    "bye_handling": (
        "Teams with no scheduled game in week W have plays_this_week=false, "
        "win_rate=0, and are excluded from ranked_picks. Demo round-robin "
        "schedules have no byes; DB schedules may. Future weeks on bye are "
        "skipped when scoring save_score (not treated as losses)."
    ),
}


@dataclass
class SurvivorEvalResult:
    """Structured survivor evaluation payload."""

    season: int
    week: int
    n_sims: int
    engine_version: str
    already_used: List[str]
    ranked_picks: List[Dict[str, Any]]
    all_teams_week: List[Dict[str, Any]]
    formula: Dict[str, str] = field(default_factory=dict)
    notes: Dict[str, str] = field(default_factory=dict)
    diagnostics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _normalize_teams(teams: Optional[Sequence[str]]) -> List[str]:
    out: List[str] = []
    seen: Set[str] = set()
    for raw in teams or []:
        t = str(raw or "").strip().upper()
        if t == "LAR":
            t = "LA"
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def schedule_index(
    schedule: Sequence[ScheduledGame],
) -> Dict[int, Dict[str, ScheduledGame]]:
    """Map week → team → game for opponent / home-away lookup."""
    by_week: Dict[int, Dict[str, ScheduledGame]] = defaultdict(dict)
    for game in schedule:
        by_week[game.week][game.home_team] = game
        by_week[game.week][game.away_team] = game
    return dict(by_week)


def simulate_team_wl_path(
    universe: EngineUniverse,
    *,
    rng: random.Random,
    injury_paths: Optional[Sequence[InjuryPath]] = None,
) -> Dict[int, Set[str]]:
    """One season path returning ``{week: set(winning_teams)}``.

    Uses Layers 1–2 only (plus injury strength overlays). Player usage /
    production are intentionally skipped for survivor throughput.

    Injury overlays are applied **once per week** (not per game). When no
    paths are supplied, the path strength book is used directly — avoiding
    per-game roster deep-copies from ``apply_injury_paths_for_week``.
    """
    strengths = copy_strength_book(universe.strengths)
    paths = list(injury_paths or [])
    week_winners: Dict[int, Set[str]] = defaultdict(set)

    schedule = sorted(universe.schedule, key=lambda g: (g.week, g.game_id))
    # Group by week so injury strength shocks are built once per week.
    by_week: Dict[int, List] = defaultdict(list)
    for game in schedule:
        by_week[game.week].append(game)

    for week in sorted(by_week):
        for game in by_week[week]:
            if paths:
                # Strength shocks only — skip Layer-3 roster realloc for speed.
                # Re-apply each game so within-week strength evolution feeds in.
                _rosters, week_strengths, _adj = apply_injury_paths_for_week(
                    universe.rosters,
                    strengths,
                    paths,
                    week=week,
                    strengths_only=True,
                )
            else:
                week_strengths = strengths

            _script, outcome = build_game_script(
                game, week_strengths, rng=rng, realized=True
            )
            home_won = bool(outcome["home_won"])
            winner = game.home_team if home_won else game.away_team
            week_winners[week].add(winner)

            # Evolve the unshocked path book (same contract as season_sim).
            evolve_after_game(
                strengths,
                home_team=game.home_team,
                away_team=game.away_team,
                home_won=home_won,
                home_score=float(outcome["home_score"]),
                away_score=float(outcome["away_score"]),
                rng=rng,
            )

    return dict(week_winners)


def aggregate_week_team_wins(
    universe: EngineUniverse,
    *,
    n_sims: int,
    seed: int,
    injury_paths: Optional[Sequence[InjuryPath]] = None,
) -> Tuple[Dict[str, Dict[int, int]], Dict[str, Dict[int, int]]]:
    """Return ``(win_counts[team][week], games_scheduled[team][week])``.

    ``games_scheduled`` is 0/1 from the static schedule (same every path).
    """
    n_sims = max(1, int(n_sims))
    rng = random.Random(seed)
    paths = list(injury_paths or [])
    win_counts: Dict[str, Dict[int, int]] = {
        t: defaultdict(int) for t in universe.teams
    }
    games_scheduled: Dict[str, Dict[int, int]] = {
        t: defaultdict(int) for t in universe.teams
    }
    for game in universe.schedule:
        games_scheduled[game.home_team][game.week] = 1
        games_scheduled[game.away_team][game.week] = 1

    for _ in range(n_sims):
        week_winners = simulate_team_wl_path(
            universe, rng=rng, injury_paths=paths
        )
        for week, winners in week_winners.items():
            for team in winners:
                if team in win_counts:
                    win_counts[team][week] += 1

    # Freeze as plain dicts of ints.
    wins_out = {
        t: {int(w): int(c) for w, c in weeks.items()}
        for t, weeks in win_counts.items()
    }
    sched_out = {
        t: {int(w): int(c) for w, c in weeks.items()}
        for t, weeks in games_scheduled.items()
    }
    return wins_out, sched_out


def _matchup_fields(
    game: Optional[ScheduledGame], team: str
) -> Dict[str, Any]:
    if game is None:
        return {
            "opponent": None,
            "home_away": None,
            "game_id": None,
            "plays_this_week": False,
        }
    if team == game.home_team:
        return {
            "opponent": game.away_team,
            "home_away": "home",
            "game_id": game.game_id,
            "plays_this_week": True,
        }
    return {
        "opponent": game.home_team,
        "home_away": "away",
        "game_id": game.game_id,
        "plays_this_week": True,
    }


def score_team_survivor(
    *,
    team: str,
    week: int,
    n_sims: int,
    win_counts: Mapping[str, Mapping[int, int]],
    games_scheduled: Mapping[str, Mapping[int, int]],
    max_week: int,
    already_used: Sequence[str],
    game: Optional[ScheduledGame],
) -> Dict[str, Any]:
    """Compute inspectable survivor scores for one team at ``week``."""
    used = set(_normalize_teams(already_used))
    n_sims = max(1, int(n_sims))
    team_wins = win_counts.get(team) or {}
    team_sched = games_scheduled.get(team) or {}

    this_wins = int(team_wins.get(week, 0))
    this_week_wp = this_wins / n_sims
    plays = bool(team_sched.get(week, 0))

    future_wps: List[float] = []
    premium_spots = 0
    future_week_detail: List[Dict[str, Any]] = []
    for w in range(week + 1, max_week + 1):
        if not team_sched.get(w, 0):
            continue
        wp = int(team_wins.get(w, 0)) / n_sims
        future_wps.append(wp)
        if wp >= PREMIUM_WP:
            premium_spots += 1
        future_week_detail.append({"week": w, "win_rate": round(wp, 4)})

    future_avg_wp = sum(future_wps) / len(future_wps) if future_wps else 0.0
    future_max_wp = max(future_wps) if future_wps else 0.0
    premium_frac = min(1.0, premium_spots / PREMIUM_SPOT_CAP)
    save_score = (
        SAVE_WEIGHT_AVG * future_avg_wp
        + SAVE_WEIGHT_MAX * future_max_wp
        + SAVE_WEIGHT_PREMIUM * premium_frac
    )
    pick_now_score = (
        this_week_wp
        - SAVE_PENALTY * save_score
        + EDGE_BONUS * (this_week_wp - future_avg_wp)
    )

    remaining = team not in used
    row: Dict[str, Any] = {
        "team": team,
        "week": week,
        "win_rate": round(this_week_wp, 4),
        "win_prob": round(this_week_wp, 4),
        "wins_in_sims": this_wins,
        "n_sims": n_sims,
        "remaining": remaining,
        "already_used": not remaining,
        "future_avg_wp": round(future_avg_wp, 4),
        "future_max_wp": round(future_max_wp, 4),
        "premium_spots": premium_spots,
        "future_value": round(save_score, 4),
        "save_score": round(save_score, 4),
        "pick_now_score": round(pick_now_score, 4),
        "future_weeks_scored": len(future_wps),
        "future_week_win_rates": future_week_detail,
        **_matchup_fields(game, team),
        "plays_this_week": plays,
    }
    return row


def evaluate_survivor(
    universe: EngineUniverse,
    *,
    week: int,
    n_sims: int = 300,
    seed: int = 42,
    already_used: Optional[Sequence[str]] = None,
    injury_paths: Optional[Sequence[InjuryPath]] = None,
    engine_version: str = DEFAULT_SEASON_ENGINE_VERSION,
    top_n: int = 32,
    include_diagnostics: bool = True,
) -> SurvivorEvalResult:
    """Run team W/L season paths and rank survivor picks for ``week``."""
    week = int(week)
    n_sims = max(1, int(n_sims))
    used = _normalize_teams(already_used)
    paths = list(injury_paths or [])
    win_counts, games_scheduled = aggregate_week_team_wins(
        universe,
        n_sims=n_sims,
        seed=seed,
        injury_paths=paths,
    )
    by_week = schedule_index(universe.schedule)
    max_week = max((g.week for g in universe.schedule), default=week)
    week_games = by_week.get(week, {})

    all_rows: List[Dict[str, Any]] = []
    bye_teams: List[str] = []
    for team in universe.teams:
        row = score_team_survivor(
            team=team,
            week=week,
            n_sims=n_sims,
            win_counts=win_counts,
            games_scheduled=games_scheduled,
            max_week=max_week,
            already_used=used,
            game=week_games.get(team),
        )
        if not row["plays_this_week"]:
            bye_teams.append(team)
        all_rows.append(row)

    all_rows.sort(
        key=lambda r: (
            -float(r["win_rate"]),
            -float(r["pick_now_score"]),
            str(r["team"]),
        )
    )

    ranked = [
        r
        for r in all_rows
        if r["remaining"] and r["plays_this_week"]
    ]
    ranked.sort(
        key=lambda r: (
            -float(r["pick_now_score"]),
            -float(r["win_rate"]),
            str(r["team"]),
        )
    )
    ranked = ranked[: max(1, int(top_n))]

    notes = dict(universe.notes)
    notes["survivor_mode"] = (
        "team_wl_paths (Layers 1–2 + injury strength shocks; "
        "Layers 3–4 skipped for speed)"
    )
    notes["already_used"] = ",".join(used) if used else "(none)"
    notes["bye_handling"] = FORMULA_NOTES["bye_handling"]
    if paths:
        notes["injury_paths"] = f"{len(paths)} path(s) applied"

    diagnostics: Dict[str, Any] = {}
    if include_diagnostics:
        diagnostics = {
            "seed": seed,
            "teams": len(universe.teams),
            "max_week": max_week,
            "injury_path_count": len(paths),
            "injury_paths": injury_paths_to_dicts(paths) if paths else [],
            "scoring_knobs": {
                "premium_wp": PREMIUM_WP,
                "save_penalty": SAVE_PENALTY,
                "edge_bonus": EDGE_BONUS,
                "save_weights": {
                    "future_avg_wp": SAVE_WEIGHT_AVG,
                    "future_max_wp": SAVE_WEIGHT_MAX,
                    "premium_frac": SAVE_WEIGHT_PREMIUM,
                },
                "premium_spot_cap": PREMIUM_SPOT_CAP,
            },
            "remaining_teams_playing": len(ranked),
            "used_excluded_from_ranked": used,
            "bye_teams_this_week": sorted(bye_teams),
            "bye_count": len(bye_teams),
        }

    return SurvivorEvalResult(
        season=universe.season,
        week=week,
        n_sims=n_sims,
        engine_version=engine_version,
        already_used=used,
        ranked_picks=ranked,
        all_teams_week=all_rows,
        formula=dict(FORMULA_NOTES),
        notes=notes,
        diagnostics=diagnostics,
    )


def week_win_rate_for_team(
    result: SurvivorEvalResult, team: str
) -> Optional[float]:
    """Convenience: P(team wins evaluation week) from an eval result."""
    t = str(team or "").strip().upper()
    if t == "LAR":
        t = "LA"
    for row in result.all_teams_week:
        if row["team"] == t:
            return float(row["win_rate"])
    return None
