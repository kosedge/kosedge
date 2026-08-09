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
    parse_injury_paths,
)
from src.services.nfl_season_engine.projected_sos import (
    TeamProjectedSos,
    compute_league_projected_sos,
    path_difficulty_grade,
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
        "win_rate=0, and are excluded from ranked_picks. Real 2026 schedules "
        "(DB or packaged wall-chart) include bye weeks; demo round-robin "
        "(demo=true) has no byes. Future weeks on bye are skipped when "
        "scoring save_score (not treated as losses)."
    ),
    "projected_sos_2026": (
        "Season schedule difficulty from full-strength opponent PR + HFA "
        "(higher = harder). Outlook / path grade only — does not rewrite "
        "intrinsic PR or game-level Edge Board lines. "
        "Harder schedule ≠ weaker team."
    ),
    "schedule_difficulty": (
        "easy / average / hard band from projected_sos_2026. Moves E[wins] "
        "and path grades with slate difficulty; intrinsic PR unchanged."
    ),
    "path_difficulty_grade": (
        "Letter from projected_sos_2026 vs league baseline (A easiest … F "
        "hardest). Coherent easier-vs-harder path ranking for survivor — "
        "not a power-ranking dial."
    ),
}

# Multi-week planner path-survival (joint across locked picks).
PATH_STRENGTH_STRONG_GEO = 0.68
PATH_STRENGTH_OK_GEO = 0.55

# Hero slate metrics (non-collapsing; joint survival demoted to advanced).
DANGER_WP_THRESHOLD = 0.55
SLATE_GRADE_A = 0.70
SLATE_GRADE_B = 0.62
SLATE_GRADE_C = 0.55
SLATE_GRADE_D = 0.48
# Contrarian-save: require a floor WP before preferring low future value.
CONTRARIAN_MIN_WP = 0.55

PATH_FORMULA_NOTES = {
    **FORMULA_NOTES,
    "path_survival": (
        "ADVANCED / secondary. Fraction of season sims where every locked "
        "(week, team) pick wins its game that week. Empty slate → 1.0 "
        "(vacuous). Collapses toward ~0 on long parlays — not the hero metric."
    ),
    "path_strength": (
        f"Band from geometric mean of locked marginal week WPs "
        f"(or path_survival^(1/n) when n>0): "
        f"Strong ≥{PATH_STRENGTH_STRONG_GEO:.2f}, "
        f"OK ≥{PATH_STRENGTH_OK_GEO:.2f}, else Fragile. Empty when no locks."
    ),
    "avg_locked_wp": (
        "Hero metric. Mean of each locked pick's marginal week win rate "
        "(wins_in_week / n_sims). Stays in a readable band even on a full "
        "17-pick slate — unlike joint path survival."
    ),
    "danger_weeks": (
        f"Count of locked picks with marginal week WP < {DANGER_WP_THRESHOLD:.0%}. "
        "Honest stress signal without multiplying probabilities."
    ),
    "best_remaining_equity": (
        "Max this-week WP among unused teams that still play in any open "
        "week (chalk left on the board). Null when the slate is full."
    ),
    "slate_grade": (
        f"Letter from avg_locked_wp: A≥{SLATE_GRADE_A:.0%}, B≥{SLATE_GRADE_B:.0%}, "
        f"C≥{SLATE_GRADE_C:.0%}, D≥{SLATE_GRADE_D:.0%}, else F. Downgrade one "
        "letter for every two danger weeks (floor F). Empty when no locks."
    ),
    "slate_score": (
        "0–100 display score = round(100 * avg_locked_wp) minus 4 per danger "
        "week (floored at 0). Encouraging but honest; does not collapse to 0 "
        "on a full chalky slate."
    ),
    "suggested_paths": (
        "Heuristic full-season paths from the same week×team WP matrix "
        "(not an LLM): chalk = greedy max WP/week; balanced = greedy "
        "pick_now_score/week; contrarian_save = among WP≥"
        f"{CONTRARIAN_MIN_WP:.0%} candidates prefer lowest save_score "
        "(bank premium future spots)."
    ),
    "planner_exclusion": (
        "A team locked in any week is removed from ranked_picks for every "
        "other week. Duplicate team locks across weeks are rejected."
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
    if injury_paths is None:
        paths = parse_injury_paths(getattr(universe, "packaged_injury_paths", None) or [])
    else:
        paths = list(injury_paths)
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
    # Preserve None so simulate_team_wl_path can load packaged SoT paths.
    paths: Optional[Sequence[InjuryPath]] = (
        None if injury_paths is None else list(injury_paths)
    )
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
    projected_sos: Optional[TeamProjectedSos] = None,
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
    if projected_sos is not None:
        sos_val = float(projected_sos.projected_sos_2026)
        row["projected_sos_2026"] = round(sos_val, 4)
        row["schedule_difficulty"] = projected_sos.difficulty_band
        row["path_difficulty_grade"] = path_difficulty_grade(sos_val)
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
    sos_by_team = compute_league_projected_sos(universe)

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
            projected_sos=sos_by_team.get(team),
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
    notes["projected_sos_2026"] = FORMULA_NOTES["projected_sos_2026"]
    notes["schedule_difficulty"] = FORMULA_NOTES["schedule_difficulty"]
    notes["path_difficulty_grade"] = FORMULA_NOTES["path_difficulty_grade"]
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
            "projected_sos_2026": {
                "intrinsic_pr_unchanged": True,
                "easier_path_teams": sorted(
                    (
                        r["team"]
                        for r in all_rows
                        if r.get("schedule_difficulty") == "easy"
                    )
                )[:8],
                "harder_path_teams": sorted(
                    (
                        r["team"]
                        for r in all_rows
                        if r.get("schedule_difficulty") == "hard"
                    )
                )[:8],
            },
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


@dataclass
class SurvivorPlanResult:
    """Multi-week survivor planner payload (one sim pass)."""

    season: int
    n_sims: int
    engine_version: str
    locked_picks: Dict[str, str]
    used_teams: List[str]
    weeks: List[Dict[str, Any]]
    path_survival: float
    path_survival_pct: float
    path_strength: str
    path_strength_geo: Optional[float]
    locked_pick_count: int
    avg_locked_wp: Optional[float] = None
    danger_weeks: int = 0
    best_remaining_equity: Optional[float] = None
    slate_grade: str = "Empty"
    slate_score: Optional[int] = None
    formula: Dict[str, str] = field(default_factory=dict)
    notes: Dict[str, str] = field(default_factory=dict)
    diagnostics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SurvivorSuggestedPathsResult:
    """Heuristic AI suggested full-season survivor paths."""

    season: int
    n_sims: int
    engine_version: str
    paths: List[Dict[str, Any]]
    formula: Dict[str, str] = field(default_factory=dict)
    notes: Dict[str, str] = field(default_factory=dict)
    diagnostics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _normalize_team_code(raw: Any) -> str:
    t = str(raw or "").strip().upper()
    if t == "LAR":
        return "LA"
    if t == "WSH":
        return "WAS"
    return t


def normalize_plan_picks(
    picks: Optional[Mapping[Any, Any]],
) -> Dict[int, str]:
    """Normalize ``{week: team}`` picks; reject bad keys / duplicate teams."""
    if picks is None:
        return {}
    out: Dict[int, str] = {}
    seen_teams: Set[str] = set()
    for raw_week, raw_team in picks.items():
        try:
            week = int(raw_week)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Invalid planner week key {raw_week!r}; expected integer week"
            ) from exc
        if week < 1 or week > 22:
            raise ValueError(f"Planner week {week} out of range (1–22)")
        team = _normalize_team_code(raw_team)
        if not team:
            raise ValueError(f"Empty team for week {week}")
        if week in out:
            raise ValueError(f"Duplicate pick for week {week}")
        if team in seen_teams:
            raise ValueError(
                f"Team {team} locked in multiple weeks; survivor allows one use"
            )
        seen_teams.add(team)
        out[week] = team
    return dict(sorted(out.items()))


def validate_plan_picks(
    universe: EngineUniverse,
    picks: Mapping[int, str],
) -> None:
    """Reject unknown teams, bye-week locks, and weeks with no slate."""
    by_week = schedule_index(universe.schedule)
    team_set = {str(t).upper() for t in universe.teams}
    if "LAR" in team_set:
        team_set.add("LA")
    for week, team in picks.items():
        if team not in team_set and team not in universe.teams:
            # Allow any team that appears on the schedule even if not in strengths.
            on_schedule = any(
                team in week_map for week_map in by_week.values()
            )
            if not on_schedule:
                raise ValueError(f"Unknown team {team} for week {week}")
        week_games = by_week.get(week)
        if not week_games:
            raise ValueError(
                f"Week {week} has no scheduled games on this universe"
            )
        if team not in week_games:
            raise ValueError(
                f"Team {team} is on bye or not scheduled in week {week}"
            )


def path_strength_band(
    *,
    locked_count: int,
    path_survival: float,
    locked_marginal_wps: Sequence[float],
) -> Tuple[str, Optional[float]]:
    """Return ``(band, geo_mean)`` for the locked slate."""
    if locked_count <= 0:
        return "Empty", None
    if locked_marginal_wps:
        product = 1.0
        for wp in locked_marginal_wps:
            product *= max(0.0, float(wp))
        geo = product ** (1.0 / locked_count)
    else:
        geo = float(path_survival) ** (1.0 / locked_count)
    if geo >= PATH_STRENGTH_STRONG_GEO:
        return "Strong", round(geo, 4)
    if geo >= PATH_STRENGTH_OK_GEO:
        return "OK", round(geo, 4)
    return "Fragile", round(geo, 4)


def _letter_from_avg_wp(avg_wp: float) -> str:
    if avg_wp >= SLATE_GRADE_A:
        return "A"
    if avg_wp >= SLATE_GRADE_B:
        return "B"
    if avg_wp >= SLATE_GRADE_C:
        return "C"
    if avg_wp >= SLATE_GRADE_D:
        return "D"
    return "F"


def _downgrade_letter(letter: str, steps: int) -> str:
    order = ["A", "B", "C", "D", "F"]
    try:
        idx = order.index(letter)
    except ValueError:
        return "F"
    return order[min(len(order) - 1, idx + max(0, int(steps)))]


def compute_slate_metrics(
    *,
    locked_marginal_wps: Sequence[float],
    best_remaining_equity: Optional[float],
) -> Dict[str, Any]:
    """Hero planner metrics that stay readable on long locked slates."""
    locked_count = len(locked_marginal_wps)
    if locked_count <= 0:
        return {
            "avg_locked_wp": None,
            "danger_weeks": 0,
            "best_remaining_equity": (
                None
                if best_remaining_equity is None
                else round(float(best_remaining_equity), 4)
            ),
            "slate_grade": "Empty",
            "slate_score": None,
        }
    avg_wp = sum(float(wp) for wp in locked_marginal_wps) / locked_count
    danger = sum(
        1 for wp in locked_marginal_wps if float(wp) < DANGER_WP_THRESHOLD
    )
    letter = _downgrade_letter(_letter_from_avg_wp(avg_wp), danger // 2)
    score = max(0, int(round(100.0 * avg_wp)) - 4 * danger)
    return {
        "avg_locked_wp": round(avg_wp, 4),
        "danger_weeks": int(danger),
        "best_remaining_equity": (
            None
            if best_remaining_equity is None
            else round(float(best_remaining_equity), 4)
        ),
        "slate_grade": letter,
        "slate_score": score,
    }


def _enrich_pick_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Add matchup label + favorite flag for planner UI (additive)."""
    out = dict(row)
    team = str(out.get("team") or "")
    opponent = out.get("opponent")
    home_away = out.get("home_away")
    wp = float(out.get("win_rate") or out.get("win_prob") or 0.0)
    if opponent:
        if home_away == "away":
            out["matchup_label"] = f"{team} @ {opponent}"
        else:
            out["matchup_label"] = f"{team} vs {opponent}"
    else:
        out["matchup_label"] = team or None
    out["this_week_wp"] = round(wp, 4)
    out["is_favorite"] = wp >= 0.5
    out["favorite_team"] = team if wp >= 0.5 else (opponent or team)
    out["favorite_wp"] = round(wp if wp >= 0.5 else max(0.0, 1.0 - wp), 4)
    return out


def _week_candidate_rows(
    *,
    week: int,
    week_games: Mapping[str, ScheduledGame],
    n_sims: int,
    wins_out: Mapping[str, Mapping[int, int]],
    sched_out: Mapping[str, Mapping[int, int]],
    max_week: int,
    used_teams: Sequence[str],
    sos_by_team: Optional[Mapping[str, TeamProjectedSos]] = None,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    sos_book = sos_by_team or {}
    for team in sorted(week_games.keys()):
        row = score_team_survivor(
            team=team,
            week=week,
            n_sims=n_sims,
            win_counts=wins_out,
            games_scheduled=sched_out,
            max_week=max_week,
            already_used=used_teams,
            game=week_games.get(team),
            projected_sos=sos_book.get(team),
        )
        if row["remaining"] and row["plays_this_week"]:
            rows.append(_enrich_pick_row(row))
    return rows


def _pick_strategy_team(
    candidates: Sequence[Dict[str, Any]],
    strategy: str,
) -> Optional[Dict[str, Any]]:
    if not candidates:
        return None
    if strategy == "chalk":
        return max(
            candidates,
            key=lambda r: (float(r["win_rate"]), float(r["pick_now_score"]), r["team"]),
        )
    if strategy == "balanced":
        return max(
            candidates,
            key=lambda r: (float(r["pick_now_score"]), float(r["win_rate"]), r["team"]),
        )
    if strategy == "contrarian_save":
        floor = [
            r for r in candidates if float(r["win_rate"]) >= CONTRARIAN_MIN_WP
        ]
        pool = floor or list(candidates)
        return min(
            pool,
            key=lambda r: (
                float(r.get("save_score") or 0.0),
                -float(r["win_rate"]),
                r["team"],
            ),
        )
    raise ValueError(f"Unknown suggest-paths strategy {strategy!r}")


def _build_win_matrix(
    universe: EngineUniverse,
    *,
    n_sims: int,
    seed: int,
    injury_paths: Sequence[InjuryPath],
    locked_items: Sequence[Tuple[int, str]],
) -> Tuple[
    Dict[str, Dict[int, int]],
    Dict[str, Dict[int, int]],
    Dict[int, Dict[str, ScheduledGame]],
    int,
    int,
]:
    """Shared season W/L matrix for planner + suggest-paths."""
    by_week = schedule_index(universe.schedule)
    schedule_weeks = sorted(by_week.keys())
    max_week = max(schedule_weeks) if schedule_weeks else 1

    win_counts: Dict[str, Dict[int, int]] = {
        t: defaultdict(int) for t in universe.teams
    }
    for week_map in by_week.values():
        for team in week_map:
            win_counts.setdefault(team, defaultdict(int))

    games_scheduled: Dict[str, Dict[int, int]] = {
        t: defaultdict(int) for t in win_counts
    }
    for game in universe.schedule:
        games_scheduled.setdefault(game.home_team, defaultdict(int))
        games_scheduled.setdefault(game.away_team, defaultdict(int))
        games_scheduled[game.home_team][game.week] = 1
        games_scheduled[game.away_team][game.week] = 1

    rng = random.Random(seed)
    path_ok = 0
    paths = list(injury_paths)
    for _ in range(n_sims):
        week_winners = simulate_team_wl_path(
            universe, rng=rng, injury_paths=paths
        )
        for week, winners in week_winners.items():
            for team in winners:
                if team in win_counts:
                    win_counts[team][week] += 1
        if locked_items and all(
            team in week_winners.get(week, set())
            for week, team in locked_items
        ):
            path_ok += 1
        elif not locked_items:
            path_ok += 1

    wins_out = {
        t: {int(w): int(c) for w, c in weeks.items()}
        for t, weeks in win_counts.items()
    }
    sched_out = {
        t: {int(w): int(c) for w, c in weeks.items()}
        for t, weeks in games_scheduled.items()
    }
    return wins_out, sched_out, by_week, max_week, path_ok


def evaluate_survivor_plan(
    universe: EngineUniverse,
    *,
    picks: Optional[Mapping[Any, Any]] = None,
    n_sims: int = 300,
    seed: int = 42,
    injury_paths: Optional[Sequence[InjuryPath]] = None,
    engine_version: str = DEFAULT_SEASON_ENGINE_VERSION,
    top_n: int = 8,
    include_diagnostics: bool = True,
) -> SurvivorPlanResult:
    """One multi-week planner pass: path survival + per-week recommendations.

    Runs ``n_sims`` team W/L season paths once. For each unlocked week,
    ranks remaining teams (excluding all locked picks) with the same
    inspectable pick-now / save scores as ``evaluate_survivor``.
    """
    n_sims = max(1, int(n_sims))
    top_n = max(1, int(top_n))
    locked = normalize_plan_picks(picks)
    validate_plan_picks(universe, locked)
    used_teams = list(locked.values())
    paths = list(injury_paths or [])
    locked_items = list(locked.items())

    wins_out, sched_out, by_week, max_week, path_ok = _build_win_matrix(
        universe,
        n_sims=n_sims,
        seed=seed,
        injury_paths=paths,
        locked_items=locked_items,
    )
    schedule_weeks = sorted(by_week.keys())
    sos_by_team = compute_league_projected_sos(universe)

    path_survival = path_ok / n_sims
    locked_marginal: List[float] = []
    for week, team in locked_items:
        locked_marginal.append(int(wins_out.get(team, {}).get(week, 0)) / n_sims)

    strength, geo = path_strength_band(
        locked_count=len(locked_items),
        path_survival=path_survival,
        locked_marginal_wps=locked_marginal,
    )

    weeks_out: List[Dict[str, Any]] = []
    best_remaining: Optional[float] = None
    for week in schedule_weeks:
        week_games = by_week.get(week, {})
        if week in locked:
            team = locked[week]
            game = week_games.get(team)
            row = _enrich_pick_row(
                score_team_survivor(
                    team=team,
                    week=week,
                    n_sims=n_sims,
                    win_counts=wins_out,
                    games_scheduled=sched_out,
                    max_week=max_week,
                    already_used=[],
                    game=game,
                    projected_sos=sos_by_team.get(team),
                )
            )
            weeks_out.append(
                {
                    "week": week,
                    "status": "locked",
                    "locked_team": team,
                    "locked_pick": row,
                    "ranked_picks": [],
                }
            )
            continue

        ranked = _week_candidate_rows(
            week=week,
            week_games=week_games,
            n_sims=n_sims,
            wins_out=wins_out,
            sched_out=sched_out,
            max_week=max_week,
            used_teams=used_teams,
            sos_by_team=sos_by_team,
        )
        ranked.sort(
            key=lambda r: (
                -float(r["pick_now_score"]),
                -float(r["win_rate"]),
                str(r["team"]),
            )
        )
        if ranked:
            chalk_wp = max(float(r["win_rate"]) for r in ranked)
            if best_remaining is None or chalk_wp > best_remaining:
                best_remaining = chalk_wp
        available = [str(r["team"]) for r in ranked]
        weeks_out.append(
            {
                "week": week,
                "status": "open",
                "locked_team": None,
                "locked_pick": None,
                "ranked_picks": ranked[:top_n],
                "available_teams": available,
            }
        )

    slate = compute_slate_metrics(
        locked_marginal_wps=locked_marginal,
        best_remaining_equity=best_remaining,
    )

    notes = dict(universe.notes)
    notes["survivor_mode"] = (
        "planner team_wl_paths (Layers 1–2 + injury strength shocks; "
        "Layers 3–4 skipped for speed)"
    )
    notes["path_survival"] = PATH_FORMULA_NOTES["path_survival"]
    notes["path_strength"] = PATH_FORMULA_NOTES["path_strength"]
    notes["avg_locked_wp"] = PATH_FORMULA_NOTES["avg_locked_wp"]
    notes["danger_weeks"] = PATH_FORMULA_NOTES["danger_weeks"]
    notes["slate_grade"] = PATH_FORMULA_NOTES["slate_grade"]
    notes["projected_sos_2026"] = PATH_FORMULA_NOTES["projected_sos_2026"]
    notes["schedule_difficulty"] = PATH_FORMULA_NOTES["schedule_difficulty"]
    notes["path_difficulty_grade"] = PATH_FORMULA_NOTES["path_difficulty_grade"]
    notes["used_teams"] = ",".join(used_teams) if used_teams else "(none)"
    if paths:
        notes["injury_paths"] = f"{len(paths)} path(s) applied"

    diagnostics: Dict[str, Any] = {}
    if include_diagnostics:
        diagnostics = {
            "seed": seed,
            "teams": len(universe.teams),
            "schedule_weeks": schedule_weeks,
            "max_week": max_week,
            "injury_path_count": len(paths),
            "injury_paths": injury_paths_to_dicts(paths) if paths else [],
            "locked_marginal_win_rates": [
                {"week": w, "team": t, "win_rate": round(wp, 4)}
                for (w, t), wp in zip(locked_items, locked_marginal)
            ],
            "path_ok_sims": path_ok,
            "scoring_knobs": {
                "premium_wp": PREMIUM_WP,
                "save_penalty": SAVE_PENALTY,
                "edge_bonus": EDGE_BONUS,
                "path_strength_strong_geo": PATH_STRENGTH_STRONG_GEO,
                "path_strength_ok_geo": PATH_STRENGTH_OK_GEO,
                "danger_wp_threshold": DANGER_WP_THRESHOLD,
            },
            "top_n": top_n,
            "used_excluded_from_ranked": used_teams,
            "hero_metrics": slate,
        }

    locked_str_keys = {str(w): t for w, t in locked.items()}
    return SurvivorPlanResult(
        season=universe.season,
        n_sims=n_sims,
        engine_version=engine_version,
        locked_picks=locked_str_keys,
        used_teams=used_teams,
        weeks=weeks_out,
        path_survival=round(path_survival, 6),
        path_survival_pct=round(path_survival * 100.0, 2),
        path_strength=strength,
        path_strength_geo=geo,
        locked_pick_count=len(locked_items),
        avg_locked_wp=slate["avg_locked_wp"],
        danger_weeks=int(slate["danger_weeks"]),
        best_remaining_equity=slate["best_remaining_equity"],
        slate_grade=str(slate["slate_grade"]),
        slate_score=slate["slate_score"],
        formula=dict(PATH_FORMULA_NOTES),
        notes=notes,
        diagnostics=diagnostics,
    )


def suggest_survivor_paths(
    universe: EngineUniverse,
    *,
    n_sims: int = 300,
    seed: int = 42,
    injury_paths: Optional[Sequence[InjuryPath]] = None,
    engine_version: str = DEFAULT_SEASON_ENGINE_VERSION,
    already_locked: Optional[Mapping[Any, Any]] = None,
    include_diagnostics: bool = True,
) -> SurvivorSuggestedPathsResult:
    """Generate 2–3 transparent heuristic full-season survivor paths.

    Uses the same week×team WP matrix as the planner (not an LLM).
    Strategies: chalk, balanced (pick_now), contrarian_save.
    """
    n_sims = max(1, int(n_sims))
    locked = normalize_plan_picks(already_locked)
    validate_plan_picks(universe, locked)
    paths = list(injury_paths or [])
    locked_items = list(locked.items())

    wins_out, sched_out, by_week, max_week, _path_ok = _build_win_matrix(
        universe,
        n_sims=n_sims,
        seed=seed,
        injury_paths=paths,
        locked_items=locked_items,
    )
    schedule_weeks = sorted(by_week.keys())
    sos_by_team = compute_league_projected_sos(universe)

    strategy_specs = [
        ("chalk", "Chalk", "Highest weekly win % among unused teams."),
        (
            "balanced",
            "Balanced",
            "Greedy pick_now_score — chalk tempered by future-save value.",
        ),
        (
            "contrarian_save",
            "Contrarian save",
            f"Among WP≥{CONTRARIAN_MIN_WP:.0%} options, burn lowest save_score first.",
        ),
    ]

    suggested: List[Dict[str, Any]] = []
    for strategy_id, label, blurb in strategy_specs:
        used = set(locked.values())
        picks: Dict[int, str] = dict(locked)
        week_detail: List[Dict[str, Any]] = []
        for week in schedule_weeks:
            if week in picks:
                team = picks[week]
                game = by_week.get(week, {}).get(team)
                row = _enrich_pick_row(
                    score_team_survivor(
                        team=team,
                        week=week,
                        n_sims=n_sims,
                        win_counts=wins_out,
                        games_scheduled=sched_out,
                        max_week=max_week,
                        already_used=[],
                        game=game,
                        projected_sos=sos_by_team.get(team),
                    )
                )
                week_detail.append(
                    {
                        "week": week,
                        "team": team,
                        "source": "locked",
                        "win_rate": row["win_rate"],
                        "matchup_label": row.get("matchup_label"),
                        "opponent": row.get("opponent"),
                        "home_away": row.get("home_away"),
                    }
                )
                continue
            candidates = _week_candidate_rows(
                week=week,
                week_games=by_week.get(week, {}),
                n_sims=n_sims,
                wins_out=wins_out,
                sched_out=sched_out,
                max_week=max_week,
                used_teams=list(used),
                sos_by_team=sos_by_team,
            )
            choice = _pick_strategy_team(candidates, strategy_id)
            if choice is None:
                continue
            team = str(choice["team"])
            picks[week] = team
            used.add(team)
            week_detail.append(
                {
                    "week": week,
                    "team": team,
                    "source": "suggested",
                    "win_rate": choice["win_rate"],
                    "matchup_label": choice.get("matchup_label"),
                    "opponent": choice.get("opponent"),
                    "home_away": choice.get("home_away"),
                    "pick_now_score": choice.get("pick_now_score"),
                    "save_score": choice.get("save_score"),
                }
            )

        marginal = [
            float(wins_out.get(team, {}).get(week, 0)) / n_sims
            for week, team in sorted(picks.items())
        ]
        # Remaining equity after this full path → always null / slate full.
        slate = compute_slate_metrics(
            locked_marginal_wps=marginal,
            best_remaining_equity=None,
        )
        suggested.append(
            {
                "id": strategy_id,
                "label": label,
                "blurb": blurb,
                "picks": {str(w): t for w, t in sorted(picks.items())},
                "pick_count": len(picks),
                "weeks": week_detail,
                "avg_locked_wp": slate["avg_locked_wp"],
                "danger_weeks": slate["danger_weeks"],
                "slate_grade": slate["slate_grade"],
                "slate_score": slate["slate_score"],
            }
        )

    notes = dict(universe.notes)
    notes["suggested_paths"] = PATH_FORMULA_NOTES["suggested_paths"]
    if paths:
        notes["injury_paths"] = f"{len(paths)} path(s) applied"

    diagnostics: Dict[str, Any] = {}
    if include_diagnostics:
        diagnostics = {
            "seed": seed,
            "schedule_weeks": schedule_weeks,
            "already_locked": {str(w): t for w, t in locked.items()},
            "strategies": [s[0] for s in strategy_specs],
        }

    return SurvivorSuggestedPathsResult(
        season=universe.season,
        n_sims=n_sims,
        engine_version=engine_version,
        paths=suggested,
        formula={
            k: PATH_FORMULA_NOTES[k]
            for k in (
                "suggested_paths",
                "avg_locked_wp",
                "danger_weeks",
                "slate_grade",
                "pick_now_score",
                "save_score",
            )
        },
        notes=notes,
        diagnostics=diagnostics,
    )
