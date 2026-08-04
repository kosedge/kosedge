"""Shared dataclasses for the hierarchical CFB season engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

QbClass = Literal["incumbent", "portal", "open_competition", "true_freshman", "unknown"]
DataFidelity = Literal["real", "approximate", "placeholder"]


@dataclass(frozen=True)
class RosterConstruction:
    """Layer 1 — how the 2026 roster was built (not last-year team strength).

    Scores are roughly 0–100 unless noted. Shares are 0–1. ``source`` /
    ``fidelity`` make honesty about packaged priors vs live feeds explicit.
    """

    team: str
    # Snap-/start-weighted returning production (0–100 composite).
    returning_production: float = 50.0
    returning_snap_share: float = 0.50  # 0–1 prior-year snap share returning
    returning_start_share: float = 0.50  # 0–1 prior-year start share returning
    portal_in_value: float = 50.0  # quality/quantity of portal additions
    portal_out_value: float = 50.0  # higher = more production lost via portal
    portal_net: float = 50.0  # inspectable in − out residual (0–100)
    recruiting_class_score: float = 50.0  # HS class / transfer capital composite
    experience_index: float = 50.0  # upperclassmen / starts distribution
    continuity_score: float = 50.0  # derived continuity after portal churn
    roster_strength: float = 50.0  # inspectable Layer-1 signal (0–100)
    # Back-compat aliases used by older priors / callers.
    portal_in_score: float = 50.0
    portal_out_score: float = 50.0
    recruiting_capital: float = 50.0
    source: str = "packaged_prior"
    fidelity: DataFidelity = "approximate"
    notes: str = ""


@dataclass(frozen=True)
class QbSituation:
    """Layer 2 — first-class quarterback situation for 2026."""

    team: str
    qb_class: QbClass = "unknown"
    starter_name: str = ""
    starter_key: str = ""
    experience_starts: int = 0
    qb_talent: float = 50.0  # 0–100 composite
    ol_support: float = 50.0
    weapons_support: float = 50.0
    supporting_cast: float = 50.0  # blend of OL + weapons
    uncertainty: float = 0.35  # 0–1; higher early / open competition
    # First-class lever (~0.55–1.55). Materially drives offense index.
    qb_situation_index: float = 1.0
    qb_situation_score: float = 50.0  # 0–100 mirror of index for weighted compose
    source: str = "packaged_prior"
    fidelity: DataFidelity = "approximate"
    notes: str = ""


@dataclass(frozen=True)
class PositionGroupGrades:
    """Layer 3 — unit grades that feed team projection."""

    team: str
    ol: float = 50.0
    skill: float = 50.0  # RB/WR/TE talent pool
    front_seven: float = 50.0
    secondary: float = 50.0
    special_teams: float = 50.0
    source: str = "packaged_prior"
    fidelity: DataFidelity = "approximate"
    notes: str = ""


@dataclass
class TeamProjectionState:
    """Layer 4 input state — projected team strength for one season path."""

    team: str
    offense_index: float = 1.0  # 1.0 = FBS average; higher = better
    defense_index: float = 1.0
    pace_factor: float = 1.0
    pass_rate_bias: float = 0.0
    early_season_uncertainty: float = 0.35
    roster: Optional[RosterConstruction] = None
    qb: Optional[QbSituation] = None
    groups: Optional[PositionGroupGrades] = None
    source: str = "hierarchical_compose"
    fidelity: DataFidelity = "approximate"
    games_played: int = 0
    notes: Dict[str, str] = field(default_factory=dict)

    def copy(self) -> "TeamProjectionState":
        return TeamProjectionState(
            team=self.team,
            offense_index=self.offense_index,
            defense_index=self.defense_index,
            pace_factor=self.pace_factor,
            pass_rate_bias=self.pass_rate_bias,
            early_season_uncertainty=self.early_season_uncertainty,
            roster=self.roster,
            qb=self.qb,
            groups=self.groups,
            source=self.source,
            fidelity=self.fidelity,
            games_played=self.games_played,
            notes=dict(self.notes),
        )


@dataclass(frozen=True)
class ScheduledGame:
    season: int
    week: int
    game_id: str
    home_team: str
    away_team: str
    neutral_site: bool = False


@dataclass(frozen=True)
class PlayerHook:
    """Thin player-level hook (skill / QB) when identity is available."""

    player_key: str
    player_name: str
    team: str
    position: str  # QB | RB | WR | TE
    depth_order: int = 1
    usage_share: float = 0.0
    talent: float = 50.0
    source: str = "packaged_prior"
    fidelity: DataFidelity = "approximate"


@dataclass(frozen=True)
class GameProjection:
    """Team-level projection for one matchup."""

    season: int
    week: int
    game_id: str
    home_team: str
    away_team: str
    engine_version: str
    home_win_prob: float
    away_win_prob: float
    expected_home_score: float
    expected_away_score: float
    expected_total: float
    spread_home: float  # negative ⇒ home favored
    margin_sd: float
    early_season_uncertainty: Dict[str, Any]
    home_layers: Dict[str, Any]
    away_layers: Dict[str, Any]
    player_hooks: List[Dict[str, Any]] = field(default_factory=list)
    notes: Dict[str, str] = field(default_factory=dict)
    fidelity: DataFidelity = "approximate"


@dataclass
class EngineUniverse:
    """Static inputs for season sims / game projections (FBS-focused)."""

    season: int
    schedule: List[ScheduledGame]
    teams: Dict[str, TeamProjectionState]
    player_hooks: Dict[str, List[PlayerHook]] = field(default_factory=dict)
    notes: Dict[str, str] = field(default_factory=dict)

    @property
    def team_codes(self) -> List[str]:
        return sorted(self.teams.keys())


@dataclass
class SeasonSimResult:
    season: int
    n_sims: int
    games_per_season: int
    engine_version: str
    team_wins: Dict[str, Dict[str, float]]
    sample_path_game_count: int
    notes: Dict[str, str] = field(default_factory=dict)
    diagnostics: Dict[str, Any] = field(default_factory=dict)


def dist_block(mean: float, std: float, p10: float, p50: float, p90: float) -> Dict[str, float]:
    return {
        "mean": round(mean, 3),
        "std": round(std, 3),
        "p10": round(p10, 3),
        "p50": round(p50, 3),
        "p90": round(p90, 3),
    }
