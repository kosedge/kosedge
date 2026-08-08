"""Shared dataclasses for the hierarchical NFL season engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

# Coarse script (backward-compatible Layer 3/4 consumers).
ScriptState = Literal["lead", "trail", "neutral"]
# Fine-grained script detail (v1.6+); maps to ScriptState via coarse_script().
ScriptDetail = Literal[
    "large_lead",
    "small_lead",
    "neutral",
    "small_deficit",
    "large_deficit",
]
TimeBucket = Literal["early", "mid", "late"]


@dataclass
class TeamStrengthState:
    """Layer 1 state for one team inside one season-sim path.

    ``offense_index`` / ``defense_index`` follow the same convention as
    ``nfl_simulator.NflGameInputs`` (1.0 = league average; higher offense
    and higher defense are both *better*).

    Sprint 2 efficiency-backbone fields (``st_index``, ``explosiveness``,
    ``variance``, ``qb_premium``, ``as_of``, ``version``) are additive
    metadata from the in-house NFL efficiency package; O/D/pace remain the
    contract consumed by game script / Edge Board / survivor.
    """

    team: str
    offense_index: float = 1.0
    defense_index: float = 1.0
    pace_factor: float = 1.0
    pass_rate_bias: float = 0.0
    source: str = "placeholder"
    games_played: int = 0
    st_index: float = 1.0
    explosiveness: float = 0.0
    variance: float = 1.0
    qb_premium: float = 0.0
    as_of: str = ""
    version: str = ""
    # True PR split: full-strength = intrinsic (no injury scars); current =
    # offense_index/defense_index after availability overlays. Equal at load
    # until injury_paths / nowcast apply a delta.
    full_strength_offense_index: float = 1.0
    full_strength_defense_index: float = 1.0
    injury_delta_offense: float = 0.0
    injury_delta_defense: float = 0.0
    blend_prior_weight: float = 1.0
    blend_current_weight: float = 0.0
    drivers: Dict[str, Any] = field(default_factory=dict)

    def copy(self) -> "TeamStrengthState":
        return TeamStrengthState(
            team=self.team,
            offense_index=self.offense_index,
            defense_index=self.defense_index,
            pace_factor=self.pace_factor,
            pass_rate_bias=self.pass_rate_bias,
            source=self.source,
            games_played=self.games_played,
            st_index=self.st_index,
            explosiveness=self.explosiveness,
            variance=self.variance,
            qb_premium=self.qb_premium,
            as_of=self.as_of,
            version=self.version,
            full_strength_offense_index=self.full_strength_offense_index,
            full_strength_defense_index=self.full_strength_defense_index,
            injury_delta_offense=self.injury_delta_offense,
            injury_delta_defense=self.injury_delta_defense,
            blend_prior_weight=self.blend_prior_weight,
            blend_current_weight=self.blend_current_weight,
            drivers=dict(self.drivers or {}),
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

    Process / regression fields (v1.13) are filled by
    ``player_regression.apply_process_priors`` — they separate efficiency /
    opportunity process from counting-stat luck. Defaults leave veterans
    neutral until annotated.
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
    # Inspectable usage taxonomy label (QB1, RB1, WR2, WR_SLOT, TE1, …).
    # Assigned by ``usage_roles.annotate_usage_roles``; empty until annotated.
    usage_role: str = ""
    # Per-unit efficiency priors (yards per attempt/carry/reception, TD rates).
    # Defaults match calibration.league priors; loaders overwrite via
    # apply_efficiency_priors / baseline-derived rates.
    ypa: float = 7.15
    ypc: float = 4.2
    ypr: float = 11.8
    catch_rate: float = 0.615
    pass_td_rate: float = 0.043
    rush_td_rate: float = 0.027
    rec_td_rate: float = 0.055
    int_rate: float = 0.018
    source: str = "placeholder"
    # --- v1.13 player process / regression (additive) ---
    is_rookie: bool = False
    draft_round: Optional[int] = None  # 1–7 when known; None = unknown
    # veteran | rookie | unclassified — never invent draft capital when unset
    rookie_status: str = "veteran"
    process_index: float = 1.0  # 1.0 ≈ league process efficiency
    td_process_gap: float = 0.0  # observed TD index − process (>0 = overperformed)
    regression_posture: str = "neutral"  # positive | negative | neutral
    regression_confidence: float = 0.0
    regression_drivers: tuple = ()


@dataclass(frozen=True)
class GameScript:
    """Layer 2 output for one game inside one replicate.

    Coarse ``home_script`` / ``away_script`` remain lead/trail/neutral for
    existing Layer 3/4 consumers. v1.6 adds inspectable play-calling fields:
    script detail, intensity, shared clock bucket, early-down pass rate, and
    a hurry-up proxy. Production should follow usage/play-mix — avoid stacking
    opaque efficiency multipliers on top of these.
    """

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
    # --- v1.6 game-script / play-calling (additive) ---
    minutes_remaining: float = 30.0
    time_bucket: TimeBucket = "mid"
    home_script_detail: ScriptDetail = "neutral"
    away_script_detail: ScriptDetail = "neutral"
    home_script_intensity: float = 0.0
    away_script_intensity: float = 0.0
    home_early_down_pass_rate: float = 0.58
    away_early_down_pass_rate: float = 0.58
    home_hurry_up: float = 0.0
    away_hurry_up: float = 0.0
    home_run_rate: float = 0.42
    away_run_rate: float = 0.42
    # v1.11 early-season uncertainty (week + inspectable posture dict).
    week: int = 0
    early_season_uncertainty: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PlayerUsage:
    """Layer 3 output: volume allocation for one player in one replicate.

    v1.7 adds inspectable red-zone / scoring-usage opportunity counts
    (inside-20 / inside-10 carries, targets, routes) plus TD opportunity
    share. Yards still come from general usage; TDs primarily from RZ.
    """

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
    usage_role: str = ""
    personnel: str = ""
    # v1.6 additive play-calling context (mirrors GameScript side fields).
    script_detail: str = ""
    script_intensity: float = 0.0
    time_bucket: str = ""
    # --- v1.7 red-zone / scoring usage (additive) ---
    rz_carries_i20: float = 0.0
    rz_carries_i10: float = 0.0
    rz_targets_i20: float = 0.0
    rz_targets_i10: float = 0.0
    rz_routes_i20: float = 0.0
    rz_routes_i10: float = 0.0
    td_opportunity_share: float = 0.0
    scoring_role: str = ""


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
    # Win distribution plus optional outlook fields (projected_sos_2026, …).
    team_wins: Dict[str, Dict[str, Any]]
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
    # Populated when callers pass include_diagnostics=True.
    diagnostics: Dict[str, Any] = field(default_factory=dict)


def dist_block(mean: float, std: float, p10: float, p50: float, p90: float) -> Dict[str, float]:
    return {
        "mean": round(mean, 3),
        "std": round(std, 3),
        "p10": round(p10, 3),
        "p50": round(p50, 3),
        "p90": round(p90, 3),
    }
