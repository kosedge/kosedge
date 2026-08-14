"""Shared dataclasses for the hierarchical CFB season engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

QbClass = Literal["incumbent", "portal", "open_competition", "true_freshman", "unknown"]
DataFidelity = Literal["real", "approximate", "placeholder"]
HfaBucket = Literal["elite", "strong", "average", "weak", "poor"]


@dataclass(frozen=True)
class HomeFieldProfile:
    """Variable home-field advantage profile (not flat 3 pts)."""

    team: str
    env_score: float = 50.0  # 0–100 recent-home / venue proxy
    bucket: HfaBucket = "average"
    hfa_points: float = 2.0  # bucket points (pre night bump)
    baseline_points: float = 2.0
    bucket_delta: float = 0.0  # hfa_points - baseline
    major_environment: bool = False
    venue: str = ""
    night_game_default: bool = False
    source: str = "packaged_prior"
    fidelity: DataFidelity = "approximate"
    notes: str = ""


@dataclass(frozen=True)
class CoachingContinuity:
    """Staff continuity / change flags + inspectable early penalties."""

    team: str
    new_hc: bool = False
    new_oc: bool = False
    new_dc: bool = False
    returning_hc: bool = True
    returning_oc: bool = True
    returning_dc: bool = True
    hc_name: str = ""
    continuity_score: float = 100.0  # 0–100; 100 = all returning
    offense_penalty_w1: float = 0.0
    defense_penalty_w1: float = 0.0
    offense_index_mult: float = 1.0
    defense_index_mult: float = 1.0
    uncertainty_boost: float = 0.0
    continuity_bonus_w1: float = 0.0
    source: str = "packaged_prior"
    fidelity: DataFidelity = "approximate"
    notes: str = ""


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
    """Layer 3 — unit grades that feed team projection.

    Headline grades (ol / skill / front_seven / secondary / special_teams) are
    0–100 composites. ``components`` holds inspectable talent / experience /
    portal_impact breakdowns per unit when available.
    """

    team: str
    ol: float = 50.0
    skill: float = 50.0  # RB/WR/TE talent pool
    front_seven: float = 50.0
    secondary: float = 50.0
    special_teams: float = 50.0
    # {"ol": {"talent":..,"experience":..,"portal_impact":..,"grade":..}, ...}
    components: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    source: str = "packaged_prior"
    fidelity: DataFidelity = "approximate"
    notes: str = ""


@dataclass(frozen=True)
class EfficiencyProfile:
    """Opponent-adjusted efficiency backbone (SP+/EPA-style carry).

    Scores are 0–100 (higher = better on both sides). Raw SP+ offense/defense
    kept for transparency; success/explosiveness are proxies when PBP is absent.
    """

    team: str
    off_eff: float = 50.0
    def_eff: float = 50.0
    success_off: float = 50.0
    success_def: float = 50.0
    explosiveness: float = 50.0
    sp_plus: float = 0.0
    sp_offense: Optional[float] = None
    sp_defense: Optional[float] = None
    sp_rank: Optional[int] = None
    prior_year: int = 2025
    carry_to_season: int = 2026
    source: str = "packaged_sp_plus_final_2025"
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
    efficiency: Optional[EfficiencyProfile] = None
    home_field: Optional[HomeFieldProfile] = None
    coaching: Optional[CoachingContinuity] = None
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
            efficiency=self.efficiency,
            home_field=self.home_field,
            coaching=self.coaching,
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
    night_game: bool = False
    kickoff: str = ""
    conference_game: bool = False
    fcs_home: bool = False
    fcs_away: bool = False
    source_game_id: str = ""


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
    # v0.7 role-share player projections (QB + skill) derived from team totals.
    player_projections: List[Dict[str, Any]] = field(default_factory=list)
    drivers: Dict[str, Any] = field(default_factory=dict)
    uncertainty: Dict[str, Any] = field(default_factory=dict)
    notes: Dict[str, str] = field(default_factory=dict)
    fidelity: DataFidelity = "approximate"
    # P3 two-path sim (margin + independent total). Empty on legacy callers.
    distributions: Dict[str, Any] = field(default_factory=dict)
    n_sims: int = 0


@dataclass
class EngineUniverse:
    """Static inputs for season sims / game projections (FBS-focused)."""

    season: int
    schedule: List[ScheduledGame]
    teams: Dict[str, TeamProjectionState]
    player_hooks: Dict[str, List[PlayerHook]] = field(default_factory=dict)
    conferences: Dict[str, str] = field(default_factory=dict)
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
    week_by_week_sample: List[Dict[str, Any]] = field(default_factory=list)
    ranking: List[Dict[str, Any]] = field(default_factory=list)
    conference_standings: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
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
