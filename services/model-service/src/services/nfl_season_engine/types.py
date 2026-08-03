"""Shared dataclasses for the hierarchical NFL season engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

ScriptState = Literal["lead", "trail", "neutral"]


@dataclass
class TeamStrengthState:
    """Layer 1 state for one team inside one season-sim path.

    ``offense_index`` / ``defense_index`` follow the same convention as
    ``nfl_simulator.NflGameInputs`` (1.0 = league average; higher offense
    and higher defense are both *better*).
    """

    team: str
    offense_index: float = 1.0
    defense_index: float = 1.0
    pace_factor: float = 1.0
    pass_rate_bias: float = 0.0
    source: str = "placeholder"
    games_played: int = 0

    def copy(self) -> "TeamStrengthState":
        return TeamStrengthState(
            team=self.team,
            offense_index=self.offense_index,
            defense_index=self.defense_index,
            pace_factor=self.pace_factor,
            pass_rate_bias=self.pass_rate_bias,
            source=self.source,
            games_played=self.games_played,
        )


@dataclass(frozen=True)
class ScheduledGame:
    season: int
    week: int
    game_id: str
    home_team: str
    away_team: str


@dataclass(frozen=True)
class PlayerRole:
    """Depth-chart / usage role for a skill player on a team.

    REAL when loaded from ``nfl_dp_depth_chart_weekly`` + prior usage.
    PLACEHOLDER when synthesized from a demo depth chart.
    """

    player_key: str
    player_name: str
    team: str
    position: str  # QB | RB | WR | TE
    depth_order: int = 1
    snap_share: float = 0.0
    target_share: float = 0.0
    rush_share: float = 0.0
    route_share: float = 0.0
    red_zone_share: float = 0.0
    role_confidence: float = 0.65
    experience_confidence: float = 1.0
    # Per-unit efficiency priors (yards per attempt/carry/reception, TD rates).
    ypa: float = 7.0
    ypc: float = 4.2
    ypr: float = 11.5
    catch_rate: float = 0.62
    pass_td_rate: float = 0.045
    rush_td_rate: float = 0.035
    rec_td_rate: float = 0.065
    int_rate: float = 0.022
    source: str = "placeholder"


@dataclass(frozen=True)
class GameScript:
    """Layer 2 output for one game inside one replicate."""

    game_id: str
    home_team: str
    away_team: str
    home_win_prob: float
    expected_total: float
    expected_home_score: float
    expected_away_score: float
    pace_plays: float
    home_pass_rate: float
    away_pass_rate: float
    home_script: ScriptState
    away_script: ScriptState
    home_implied_total: float
    away_implied_total: float
    source: str = "team_strength_analytic"


@dataclass(frozen=True)
class PlayerUsage:
    """Layer 3 output: volume allocation for one player in one replicate."""

    player_key: str
    player_name: str
    team: str
    position: str
    snap_share: float
    route_share: float
    targets: float
    carries: float
    pass_attempts: float
    script: ScriptState


@dataclass(frozen=True)
class PlayerBoxScore:
    """Layer 4 output: one replicate box score for a skill player."""

    player_key: str
    player_name: str
    team: str
    position: str
    pass_yards: float = 0.0
    pass_tds: float = 0.0
    ints: float = 0.0
    rush_yards: float = 0.0
    rush_tds: float = 0.0
    rec_yards: float = 0.0
    receptions: float = 0.0
    rec_tds: float = 0.0
    pass_attempts: float = 0.0
    carries: float = 0.0
    targets: float = 0.0


@dataclass
class EngineUniverse:
    """All static inputs needed to run season sims or game queries."""

    season: int
    schedule: List[ScheduledGame]
    strengths: Dict[str, TeamStrengthState]
    rosters: Dict[str, List[PlayerRole]]
    notes: Dict[str, str] = field(default_factory=dict)

    @property
    def teams(self) -> List[str]:
        return sorted(self.strengths.keys())


@dataclass
class SeasonSimResult:
    season: int
    n_sims: int
    games_per_season: int
    engine_version: str
    team_wins: Dict[str, Dict[str, float]]
    player_season_totals: List[Dict[str, Any]]
    sample_path_game_count: int
    notes: Dict[str, str] = field(default_factory=dict)
    diagnostics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GameBoxProjection:
    season: int
    week: int
    game_id: str
    home_team: str
    away_team: str
    n_replicates: int
    engine_version: str
    game_script_summary: Dict[str, Any]
    players: List[Dict[str, Any]]
    notes: Dict[str, str] = field(default_factory=dict)


def dist_block(mean: float, std: float, p10: float, p50: float, p90: float) -> Dict[str, float]:
    return {
        "mean": round(mean, 3),
        "std": round(std, 3),
        "p10": round(p10, 3),
        "p50": round(p50, 3),
        "p90": round(p90, 3),
    }
