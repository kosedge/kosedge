"""2026 Projected Schedule Difficulty (Future SOS).

Outlook tool only: mean projected opponent strength across a team's forward
regular-season slate. Consumed by season expectation surfaces (expected wins,
playoff / survivor path difficulty) — **never** rewrites intrinsic / Week-1 PR.

Opponent package
----------------
Prefer each opponent's **full-strength** offense/defense indices (post QB
premium, continuity, past-SOS prior on the true-PR stack). Full-strength keeps
early-season injury noise from distorting season SOS.

Home/away: apply the engine HFA so road-heavy slates read harder.

Polarity: ``projected_sos_2026`` higher = harder slate.

North star: ``data/ops/nfl-model-vision.md``.
Past SOS (prior performance): ``adjusted_sos.py`` — separate layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from src.services.nfl_season_engine.calibration import (
    HOME_FIELD_POINTS,
    LEAGUE_TEAM_PPG,
)
from src.services.nfl_season_engine.team_strength import (
    expected_team_points,
    win_prob_from_expected_scores,
)
from src.services.nfl_season_engine.types import (
    EngineUniverse,
    ScheduledGame,
    TeamStrengthState,
)

# Week bands for early / late slate difficulty (when schedule supports).
EARLY_WEEK_LAST = 6
LATE_WEEK_FIRST = 12
LATE_WEEK_LAST = 18

# Index-scale HFA on opponent power (aligned with ~1.05 pts / ~21.8 PPG).
_HFA_POWER = float(HOME_FIELD_POINTS) / max(1.0, float(LEAGUE_TEAM_PPG))

# League-average power on the index composite (off+def)/2 at 1.0/1.0.
_LEAGUE_POWER = 1.0

# Soft / hard bands vs league mean (index units). Transparent, not faux CLV.
_EASY_DELTA = -0.025
_HARD_DELTA = 0.025

# Thin opponent book label threshold: share of games with missing opp strength.
_THIN_OPP_SHARE = 0.35


def normalize_team(team: str) -> str:
    t = str(team or "").strip().upper()
    if t == "LAR":
        return "LA"
    return t


def _full_strength_power(state: TeamStrengthState) -> float:
    """Composite opponent power from full-strength indices (higher = stronger)."""
    off = float(
        getattr(state, "full_strength_offense_index", None) or state.offense_index
    )
    deff = float(
        getattr(state, "full_strength_defense_index", None) or state.defense_index
    )
    return 0.5 * (off + deff)


def opponent_effective_power(
    opp: TeamStrengthState,
    *,
    is_home: bool,
) -> float:
    """Effective opponent power for one game (higher = harder for us).

    Home: facing the opponent is slightly easier (subtract HFA power).
    Away: road slate is harder (add HFA power to opponent).
    """
    power = _full_strength_power(opp)
    if is_home:
        return power - _HFA_POWER
    return power + _HFA_POWER


@dataclass(frozen=True)
class ProjectedGameDifficulty:
    week: int
    opponent: str
    is_home: bool
    opponent_power: float
    effective_power: float
    game_id: str = ""


@dataclass
class TeamProjectedSos:
    """Team-level 2026 projected schedule difficulty."""

    team: str
    season: int
    games: int
    projected_sos_2026: float  # higher = harder
    early_sos: Optional[float] = None  # W1–6 when present
    late_sos: Optional[float] = None  # W12–18 when present
    home_games: int = 0
    away_games: int = 0
    status: str = "thin_unavailable"
    opponent_package: str = "full_strength_pr"
    games_detail: List[ProjectedGameDifficulty] = field(default_factory=list)
    notes: Dict[str, Any] = field(default_factory=dict)

    @property
    def difficulty_band(self) -> str:
        delta = float(self.projected_sos_2026) - _LEAGUE_POWER
        if delta <= _EASY_DELTA:
            return "easy"
        if delta >= _HARD_DELTA:
            return "hard"
        return "average"

    def drivers(self) -> Dict[str, Any]:
        ordered = sorted(
            self.games_detail, key=lambda g: float(g.effective_power), reverse=True
        )
        toughest = [
            {
                "week": g.week,
                "opponent": g.opponent,
                "home_away": "home" if g.is_home else "away",
                "effective_power": round(float(g.effective_power), 4),
            }
            for g in ordered[:3]
        ]
        easiest = [
            {
                "week": g.week,
                "opponent": g.opponent,
                "home_away": "home" if g.is_home else "away",
                "effective_power": round(float(g.effective_power), 4),
            }
            for g in list(reversed(ordered))[:3]
        ]
        return {
            "status": self.status,
            "projected_sos_2026": round(float(self.projected_sos_2026), 4),
            "difficulty_band": self.difficulty_band,
            "games": int(self.games),
            "early_sos": (
                None if self.early_sos is None else round(float(self.early_sos), 4)
            ),
            "late_sos": (
                None if self.late_sos is None else round(float(self.late_sos), 4)
            ),
            "home_games": int(self.home_games),
            "away_games": int(self.away_games),
            "home_away_balance": {
                "home": int(self.home_games),
                "away": int(self.away_games),
                "road_heavy": int(self.away_games) > int(self.home_games),
            },
            "toughest_opponents": toughest,
            "easiest_opponents": easiest,
            "opponent_package": self.opponent_package,
            "intrinsic_pr_unchanged": True,
            "league_power_baseline": _LEAGUE_POWER,
            "hfa_power": round(_HFA_POWER, 4),
            **dict(self.notes or {}),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "team": self.team,
            "season": self.season,
            "games": self.games,
            "projected_sos_2026": round(float(self.projected_sos_2026), 4),
            "early_sos": (
                None if self.early_sos is None else round(float(self.early_sos), 4)
            ),
            "late_sos": (
                None if self.late_sos is None else round(float(self.late_sos), 4)
            ),
            "difficulty_band": self.difficulty_band,
            "home_games": self.home_games,
            "away_games": self.away_games,
            "status": self.status,
            "opponent_package": self.opponent_package,
            "drivers": self.drivers(),
        }


def _team_games_from_schedule(
    team: str,
    schedule: Sequence[ScheduledGame],
) -> List[Tuple[ScheduledGame, bool]]:
    t = normalize_team(team)
    out: List[Tuple[ScheduledGame, bool]] = []
    for g in schedule:
        if normalize_team(g.home_team) == t:
            out.append((g, True))
        elif normalize_team(g.away_team) == t:
            out.append((g, False))
    out.sort(key=lambda x: (int(x[0].week), str(x[0].game_id)))
    return out


def compute_team_projected_sos(
    team: str,
    schedule: Sequence[ScheduledGame],
    strengths: Mapping[str, TeamStrengthState],
    *,
    season: int = 2026,
) -> TeamProjectedSos:
    """Mean projected opponent strength across the team's REG slate."""
    t = normalize_team(team)
    team_games = _team_games_from_schedule(t, schedule)
    if not team_games:
        return TeamProjectedSos(
            team=t,
            season=int(season),
            games=0,
            projected_sos_2026=_LEAGUE_POWER,
            status="thin_unavailable",
            notes={"reason": "no_scheduled_games"},
        )

    details: List[ProjectedGameDifficulty] = []
    eff_powers: List[float] = []
    early: List[float] = []
    late: List[float] = []
    home_n = 0
    away_n = 0
    missing_opp = 0

    for game, is_home in team_games:
        opp_code = normalize_team(game.away_team if is_home else game.home_team)
        opp = strengths.get(opp_code)
        if opp is None:
            missing_opp += 1
            # League-average book when opponent missing — labeled approximate.
            opp = TeamStrengthState(
                team=opp_code,
                offense_index=1.0,
                defense_index=1.0,
                full_strength_offense_index=1.0,
                full_strength_defense_index=1.0,
                source="league_average_fallback",
            )
        raw = _full_strength_power(opp)
        eff = opponent_effective_power(opp, is_home=is_home)
        eff_powers.append(float(eff))
        week = int(game.week)
        if week <= EARLY_WEEK_LAST:
            early.append(float(eff))
        if LATE_WEEK_FIRST <= week <= LATE_WEEK_LAST:
            late.append(float(eff))
        if is_home:
            home_n += 1
        else:
            away_n += 1
        details.append(
            ProjectedGameDifficulty(
                week=week,
                opponent=opp_code,
                is_home=is_home,
                opponent_power=round(float(raw), 6),
                effective_power=round(float(eff), 6),
                game_id=str(game.game_id or ""),
            )
        )

    mean_sos = sum(eff_powers) / len(eff_powers)
    thin_share = missing_opp / max(1, len(team_games))
    if thin_share >= _THIN_OPP_SHARE:
        status = "approximate_thin_opponent_book"
    elif missing_opp > 0:
        status = "applied_partial_full_strength"
    else:
        status = "applied_full_strength"

    notes: Dict[str, Any] = {
        "missing_opponent_games": int(missing_opp),
        "thin_opponent_share": round(thin_share, 4),
    }
    if thin_share >= _THIN_OPP_SHARE:
        notes["label"] = (
            "Thin opponent PR → approximate league fill; still better than W%"
        )

    return TeamProjectedSos(
        team=t,
        season=int(season),
        games=len(team_games),
        projected_sos_2026=float(mean_sos),
        early_sos=(sum(early) / len(early)) if early else None,
        late_sos=(sum(late) / len(late)) if late else None,
        home_games=home_n,
        away_games=away_n,
        status=status,
        opponent_package="full_strength_pr",
        games_detail=details,
        notes=notes,
    )


def compute_league_projected_sos(
    universe: EngineUniverse,
) -> Dict[str, TeamProjectedSos]:
    """Projected SOS for every team in the universe (does not mutate strengths)."""
    out: Dict[str, TeamProjectedSos] = {}
    for team in universe.teams:
        out[normalize_team(team)] = compute_team_projected_sos(
            team,
            universe.schedule,
            universe.strengths,
            season=int(universe.season),
        )
    return out


def projected_sos_summary(
    sos_by_team: Mapping[str, TeamProjectedSos],
) -> Dict[str, Any]:
    """Compact league summary for season-sim / API diagnostics."""
    rows = sorted(
        sos_by_team.values(),
        key=lambda s: float(s.projected_sos_2026),
        reverse=True,
    )
    if not rows:
        return {
            "status": "thin_unavailable",
            "teams": 0,
            "intrinsic_pr_unchanged": True,
        }
    hardest = rows[0]
    easiest = rows[-1]
    return {
        "status": "applied",
        "teams": len(rows),
        "opponent_package": "full_strength_pr",
        "intrinsic_pr_unchanged": True,
        "mean_projected_sos": round(
            sum(float(r.projected_sos_2026) for r in rows) / len(rows), 4
        ),
        "hardest_slate": {
            "team": hardest.team,
            "projected_sos_2026": round(float(hardest.projected_sos_2026), 4),
            "band": hardest.difficulty_band,
        },
        "easiest_slate": {
            "team": easiest.team,
            "projected_sos_2026": round(float(easiest.projected_sos_2026), 4),
            "band": easiest.difficulty_band,
        },
        "by_team": {r.team: r.to_dict() for r in rows},
    }


def analytic_expected_wins_from_schedule(
    team: str,
    schedule: Sequence[ScheduledGame],
    strengths: Mapping[str, TeamStrengthState],
) -> float:
    """Transparent expected wins from per-game WP (full-strength + HFA).

    Uses the same O/D + HFA contract as Layer 2 — schedule difficulty only;
    does not rewrite PR. Useful for outlook / smell tests without Monte Carlo.
    """
    t = normalize_team(team)
    us = strengths.get(t)
    if us is None:
        return 0.0
    # Snapshot full-strength as the game-time book for season outlook.
    us_fs = TeamStrengthState(
        team=t,
        offense_index=float(us.full_strength_offense_index or us.offense_index),
        defense_index=float(us.full_strength_defense_index or us.defense_index),
        full_strength_offense_index=float(
            us.full_strength_offense_index or us.offense_index
        ),
        full_strength_defense_index=float(
            us.full_strength_defense_index or us.defense_index
        ),
        source=us.source,
    )
    total = 0.0
    for game, is_home in _team_games_from_schedule(t, schedule):
        opp_code = normalize_team(game.away_team if is_home else game.home_team)
        opp = strengths.get(opp_code)
        if opp is None:
            continue
        opp_fs = TeamStrengthState(
            team=opp_code,
            offense_index=float(opp.full_strength_offense_index or opp.offense_index),
            defense_index=float(opp.full_strength_defense_index or opp.defense_index),
            full_strength_offense_index=float(
                opp.full_strength_offense_index or opp.offense_index
            ),
            full_strength_defense_index=float(
                opp.full_strength_defense_index or opp.defense_index
            ),
            source=opp.source,
        )
        week = int(game.week)
        if is_home:
            home_pts = expected_team_points(us_fs, opp_fs, home=True, week=week)
            away_pts = expected_team_points(opp_fs, us_fs, home=False, week=week)
            wp = win_prob_from_expected_scores(home_pts, away_pts, week=week)
        else:
            home_pts = expected_team_points(opp_fs, us_fs, home=True, week=week)
            away_pts = expected_team_points(us_fs, opp_fs, home=False, week=week)
            wp = 1.0 - win_prob_from_expected_scores(home_pts, away_pts, week=week)
        total += float(wp)
    return float(total)


def attach_projected_sos_to_team_wins(
    team_wins: Mapping[str, Mapping[str, float]],
    sos_by_team: Mapping[str, TeamProjectedSos],
    *,
    strengths: Optional[Mapping[str, TeamStrengthState]] = None,
    schedule: Optional[Sequence[ScheduledGame]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Enrich win-total outlook with schedule difficulty (PR unchanged)."""
    out: Dict[str, Dict[str, Any]] = {}
    for team, stats in team_wins.items():
        row: Dict[str, Any] = dict(stats)
        sos = sos_by_team.get(normalize_team(team))
        if sos is not None:
            row["projected_sos_2026"] = round(float(sos.projected_sos_2026), 4)
            row["schedule_difficulty"] = sos.difficulty_band
            row["early_sos"] = (
                None if sos.early_sos is None else round(float(sos.early_sos), 4)
            )
            row["late_sos"] = (
                None if sos.late_sos is None else round(float(sos.late_sos), 4)
            )
            row["sos_drivers"] = {
                "toughest_opponents": sos.drivers().get("toughest_opponents"),
                "easiest_opponents": sos.drivers().get("easiest_opponents"),
                "home_away_balance": sos.drivers().get("home_away_balance"),
                "status": sos.status,
            }
            if strengths is not None and schedule is not None:
                row["analytic_expected_wins"] = round(
                    analytic_expected_wins_from_schedule(team, schedule, strengths),
                    3,
                )
        out[team] = row
    return out


def path_difficulty_grade(projected_sos: float) -> str:
    """Letter-ish path grade for survivor / season outlook (not a PR dial)."""
    delta = float(projected_sos) - _LEAGUE_POWER
    if delta <= _EASY_DELTA - 0.015:
        return "A"
    if delta <= _EASY_DELTA:
        return "B"
    if delta < _HARD_DELTA:
        return "C"
    if delta < _HARD_DELTA + 0.015:
        return "D"
    return "F"


def assert_strengths_unchanged(
    before: Mapping[str, TeamStrengthState],
    after: Mapping[str, TeamStrengthState],
) -> None:
    """Hard guard used by tests: projected SOS must not move intrinsic PR."""
    if set(before) != set(after):
        raise AssertionError("projected SOS mutated strength book keys")
    for team, b in before.items():
        a = after[team]
        if (
            abs(float(b.offense_index) - float(a.offense_index)) > 1e-12
            or abs(float(b.defense_index) - float(a.defense_index)) > 1e-12
            or abs(
                float(b.full_strength_offense_index)
                - float(a.full_strength_offense_index)
            )
            > 1e-12
            or abs(
                float(b.full_strength_defense_index)
                - float(a.full_strength_defense_index)
            )
            > 1e-12
        ):
            raise AssertionError(
                f"projected SOS must not change intrinsic PR for {team}"
            )
