"""Season volume budgets — finite team pools before player allocation.

Phase-1 coherence contract (v1.16) + Phase-2 general volume features (v1.25):
- Each team owns a **season pass-yard** and **rush-yard** budget driven by
  offense/pace/pass identity, coaching tendencies, and opponent-defense slate.
- General features (QB rushing profile, returning-QB prior travel, OL
  protection YPA) adjust residuals **before** league-pool renorm — no
  ARI/BAL/SEA named hardcodes.
- Budgets are renormalized to a **league pool** near recent NFL reality.
- Prior-year volume outliers regress toward the structural mean (tails only).
- QB1 / RB1 / WR-TE production must draw from these budgets — not 32
  independent max-projections.

Used by:
- ``season_sim`` path-end conservation (scale named totals into team pools)
- Fantasy / preseason-sim season-total aggregation (same math, dict inputs)
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from src.services.nfl_season_engine.calibration import (
    ATTEMPT_SHARE_OF_PASS_PLAYS,
    DEFAULT_YPA,
    DEFAULT_YPC,
    LEAGUE_BASE_PASS_RATE,
    LEAGUE_BASE_PLAYS,
    LEAGUE_PASS_YARDS_POOL,
    LEAGUE_RUSH_YARDS_POOL,
    PACE_PLAYS_CLAMP,
    USAGE_OTHER_BUCKET_FLOOR,
    VOLUME_PRIOR_BLEND,
    VOLUME_REGRESSION,
)
from src.services.nfl_season_engine.coaching_tendencies import profile_for_team
from src.services.nfl_season_engine.ol_protection import (
    OlProtectionFeature,
    build_ol_protection_book,
)
from src.services.nfl_season_engine.qb_rushing_profile import (
    QbRushingProfile,
    resolve_qb1_profile,
)
from src.services.nfl_season_engine.types import EngineUniverse, TeamStrengthState

GAMES_PER_TEAM = 17.0
# Structural offense → efficiency / pace coupling (documented knobs).
PACE_OFFENSE_SCALE = 0.14
YPA_OFFENSE_SCALE = 0.55
YPC_OFFENSE_SCALE = 0.35
OPP_DEFENSE_PASS_SCALE = 0.16
OPP_DEFENSE_RUSH_SCALE = 0.12
STRENGTH_PASS_BIAS_SCALE = 1.75
COACH_PASS_BIAS_SCALE = 1.35
NAMED_SHARE = 1.0 - USAGE_OTHER_BUCKET_FLOOR

# Returning-QB prior anchor (generalizes the old SEA Darnold 70/30 pile).
# When continuity says same QB1 and a prior pass volume is supplied, blend
# prior*weight + structural*(1-weight). Weight scales with continuity travel.
RETURNING_QB_PRIOR_WEIGHT_MAX = 0.70
# Legacy name kept for import compatibility / ops notes (no longer a team lever).
SEA_DARNOLD_PASS_BASELINE = 3_900.0
# Empty — Phase 2 removed named-team pass identity overlays.
TEAM_PASS_VOLUME_IDENTITY_ADJUSTMENTS: Dict[str, Dict[str, float]] = {}

# Player-keyed pass-yard priors (SoT player_id) — not team hardcodes.
# Revisit by 2026-10-01 once 2026 games update the anchors.
QB_PASS_YARDS_PRIOR_BY_PLAYER_ID: Dict[str, float] = {
    "00-0034869": SEA_DARNOLD_PASS_BASELINE,  # Sam Darnold
}

# Low-continuity high-tail shrink (generalizes ARI soft-ceiling sculpture).
# When prior_travel is low (new staff / new QB regime), compress pass residuals
# above league mean toward the mean. Documented, applies to every team.
LOW_CONTINUITY_TRAVEL_THRESHOLD = 0.50
LOW_CONTINUITY_HIGH_TAIL_K = 0.78  # residual keep-rate above mean

# League-wide soft pass band (all 32 teams) — tanh taper, no named-team pins.
# Replaces ARI/BAL/SEA soft_floor/soft_ceiling piles with one transparent rail.
LEAGUE_PASS_SOFT_FLOOR = 2_900.0
LEAGUE_PASS_SOFT_CEILING = 4_400.0
LEAGUE_PASS_TAPER_K = 0.55


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


@dataclass(frozen=True)
class TeamVolumeFactors:
    """Inputs for one team's season volume budget (engine or fantasy path)."""

    team: str
    offense_index: float = 1.0
    defense_index: float = 1.0
    pace_factor: float = 1.0
    pass_rate_bias: float = 0.0
    opp_defense_index_mean: float = 1.0
    pass_yards_prior: Optional[float] = None
    rush_yards_prior: Optional[float] = None
    games: float = GAMES_PER_TEAM


@dataclass(frozen=True)
class TeamSeasonBudget:
    team: str
    pass_yards: float
    rush_yards: float
    rec_yards: float
    pass_plays: float
    rush_plays: float
    pass_rate: float
    pace_plays: float
    ypa: float
    ypc: float
    structural_pass_yards: float
    structural_rush_yards: float
    notes: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "team": self.team,
            "pass_yards": round(self.pass_yards, 2),
            "rush_yards": round(self.rush_yards, 2),
            "rec_yards": round(self.rec_yards, 2),
            "pass_plays": round(self.pass_plays, 2),
            "rush_plays": round(self.rush_plays, 2),
            "pass_rate": round(self.pass_rate, 4),
            "pace_plays": round(self.pace_plays, 2),
            "ypa": round(self.ypa, 3),
            "ypc": round(self.ypc, 3),
            "structural_pass_yards": round(self.structural_pass_yards, 2),
            "structural_rush_yards": round(self.structural_rush_yards, 2),
            "notes": list(self.notes),
        }


def _replace_pass_yards(budget: TeamSeasonBudget, pass_yards: float, *extra_notes: str) -> TeamSeasonBudget:
    notes = tuple(list(budget.notes) + [n for n in extra_notes if n])
    return TeamSeasonBudget(
        team=budget.team,
        pass_yards=float(pass_yards),
        rush_yards=budget.rush_yards,
        rec_yards=float(pass_yards) * 0.92,
        pass_plays=budget.pass_plays,
        rush_plays=budget.rush_plays,
        pass_rate=budget.pass_rate,
        pace_plays=budget.pace_plays,
        ypa=budget.ypa,
        ypc=budget.ypc,
        structural_pass_yards=budget.structural_pass_yards,
        structural_rush_yards=budget.structural_rush_yards,
        notes=notes,
    )


def _replace_rush_yards(
    budget: TeamSeasonBudget, rush_yards: float, *extra_notes: str
) -> TeamSeasonBudget:
    notes = tuple(list(budget.notes) + [n for n in extra_notes if n])
    return TeamSeasonBudget(
        team=budget.team,
        pass_yards=budget.pass_yards,
        rush_yards=float(rush_yards),
        rec_yards=budget.rec_yards,
        pass_plays=budget.pass_plays,
        rush_plays=budget.rush_plays,
        pass_rate=budget.pass_rate,
        pace_plays=budget.pace_plays,
        ypa=budget.ypa,
        ypc=budget.ypc,
        structural_pass_yards=budget.structural_pass_yards,
        structural_rush_yards=budget.structural_rush_yards,
        notes=notes,
    )


def apply_team_pass_volume_identity_adjustments(
    budgets: Mapping[str, TeamSeasonBudget],
) -> Dict[str, TeamSeasonBudget]:
    """Deprecated no-op — named-team identity overlays removed in Phase 2.

    Kept so older callers / tests import cleanly. Prefer
    ``apply_general_volume_features``.
    """
    return {str(t): b for t, b in budgets.items()}


def apply_general_volume_features(
    budgets: Mapping[str, TeamSeasonBudget],
    *,
    qb_profiles: Optional[Mapping[str, QbRushingProfile]] = None,
    ol_protection: Optional[Mapping[str, OlProtectionFeature]] = None,
    continuity_travel: Optional[Mapping[str, float]] = None,
    returning_qb: Optional[Mapping[str, bool]] = None,
    pass_yards_prior: Optional[Mapping[str, float]] = None,
    new_regime: Optional[Mapping[str, bool]] = None,
) -> Dict[str, TeamSeasonBudget]:
    """General pre-pool volume features (QB rush, OL YPA, returning-QB prior).

    Applied to every team identically — no ARI/BAL/SEA hardcodes. League pool
    renorm still follows in ``compute_team_season_budgets``.
    """
    if not budgets:
        return {}
    pass_vals = [float(b.pass_yards) for b in budgets.values()]
    league_mean = statistics.fmean(pass_vals) if pass_vals else (LEAGUE_PASS_YARDS_POOL / 32.0)
    out: Dict[str, TeamSeasonBudget] = {}
    for team, budget in budgets.items():
        y_pass = float(budget.pass_yards)
        y_rush = float(budget.rush_yards)
        notes: List[str] = ["general_volume_features_v1"]

        qb = (qb_profiles or {}).get(str(team))
        if qb is None:
            qb = resolve_qb1_profile(team=str(team))
        y_pass *= float(qb.pass_volume_mult)
        y_rush *= float(qb.rush_volume_mult)
        # Dual-threat script tilt: slight additional rush from designed-run identity.
        if qb.script_run_tilt > 0:
            shift = y_pass * float(qb.script_run_tilt) * 0.35
            y_pass -= shift
            y_rush += shift
        notes.append(f"qb_rush_{qb.tier}")

        ol = (ol_protection or {}).get(str(team))
        if ol is not None and ol.fidelity == "applied":
            y_pass *= float(ol.ypa_mult)
            notes.append(f"ol_ypa_{ol.protection_index:.3f}")

        # Returning-QB prior travel (player-id prior map or caller-supplied).
        is_returning = bool((returning_qb or {}).get(str(team), False))
        prior = (pass_yards_prior or {}).get(str(team))
        if prior is None and qb.player_id:
            prior = QB_PASS_YARDS_PRIOR_BY_PLAYER_ID.get(str(qb.player_id))
            # Pocket returning starter with a published prior ⇒ treat as returning.
            if prior is not None and qb.tier == "pocket":
                is_returning = True
        travel = float((continuity_travel or {}).get(str(team), 0.55))
        if is_returning and prior is not None and float(prior) > 0:
            w = _clamp(RETURNING_QB_PRIOR_WEIGHT_MAX * max(travel, 0.55), 0.0, RETURNING_QB_PRIOR_WEIGHT_MAX)
            y_pass = w * float(prior) + (1.0 - w) * y_pass
            notes.append(f"returning_qb_prior_w_{w:.2f}")

        # Low-continuity / new-regime high-tail shrink (generalizes ARI ceiling).
        regime_new = bool((new_regime or {}).get(str(team), False))
        if (travel < LOW_CONTINUITY_TRAVEL_THRESHOLD or regime_new) and y_pass > league_mean:
            y_pass = league_mean + LOW_CONTINUITY_HIGH_TAIL_K * (y_pass - league_mean)
            notes.append(f"low_cont_high_tail_k_{LOW_CONTINUITY_HIGH_TAIL_K:.2f}")

        # League-wide soft band (all teams) — tanh taper, not a hard clip.
        y_pass = _taper_pass_yards(y_pass)
        notes.append("league_pass_soft_taper")

        out[team] = _replace_rush_yards(
            _replace_pass_yards(budget, y_pass, *notes),
            y_rush,
        )
    return out


def _taper_pass_yards(value: float) -> float:
    """Soft-saturate into league pass band via tanh (no hard pin)."""
    v = float(value)
    lo = LEAGUE_PASS_SOFT_FLOOR
    hi = LEAGUE_PASS_SOFT_CEILING
    half = 0.5 * (hi - lo)
    if lo <= v <= hi:
        return v
    # Map overflow through tanh so extremes bend toward the rail.
    if v > hi:
        over = (v - hi) / max(half, 1.0)
        return hi + half * LEAGUE_PASS_TAPER_K * math.tanh(over)
    under = (lo - v) / max(half, 1.0)
    return lo - half * LEAGUE_PASS_TAPER_K * math.tanh(under)


def mean_opponent_defense(
    schedule: Sequence[Any],
    strengths: Mapping[str, TeamStrengthState],
    team: str,
) -> float:
    """Mean opponent defense_index across the team's REG slate."""
    opp_defs: List[float] = []
    for game in schedule:
        home = getattr(game, "home_team", None) or game.get("home_team")  # type: ignore[union-attr]
        away = getattr(game, "away_team", None) or game.get("away_team")  # type: ignore[union-attr]
        if home == team:
            opp = away
        elif away == team:
            opp = home
        else:
            continue
        state = strengths.get(str(opp))
        if state is not None:
            opp_defs.append(float(state.defense_index))
    if not opp_defs:
        return 1.0
    return sum(opp_defs) / len(opp_defs)


def factors_from_universe(universe: EngineUniverse) -> Dict[str, TeamVolumeFactors]:
    out: Dict[str, TeamVolumeFactors] = {}
    for team in universe.teams:
        state = universe.strengths.get(team) or TeamStrengthState(team=team)
        out[team] = TeamVolumeFactors(
            team=team,
            offense_index=float(state.offense_index),
            defense_index=float(state.defense_index),
            pace_factor=float(state.pace_factor),
            pass_rate_bias=float(state.pass_rate_bias),
            opp_defense_index_mean=mean_opponent_defense(
                universe.schedule, universe.strengths, team
            ),
        )
    return out


def structural_team_budget(factors: TeamVolumeFactors) -> TeamSeasonBudget:
    """Team season pool from strength / coaching / slate (pre league-renorm)."""
    coach = profile_for_team(factors.team)
    pass_rate = _clamp(
        LEAGUE_BASE_PASS_RATE
        + STRENGTH_PASS_BIAS_SCALE * float(factors.pass_rate_bias)
        + COACH_PASS_BIAS_SCALE * float(coach.pass_rate_bias),
        0.42,
        0.72,
    )
    pace = _clamp(
        LEAGUE_BASE_PLAYS
        * float(factors.pace_factor)
        * (1.0 + PACE_OFFENSE_SCALE * (float(factors.offense_index) - 1.0)),
        PACE_PLAYS_CLAMP[0],
        PACE_PLAYS_CLAMP[1],
    )
    opp_pass_mult = _clamp(
        1.0 - OPP_DEFENSE_PASS_SCALE * (float(factors.opp_defense_index_mean) - 1.0),
        0.88,
        1.12,
    )
    opp_rush_mult = _clamp(
        1.0 - OPP_DEFENSE_RUSH_SCALE * (float(factors.opp_defense_index_mean) - 1.0),
        0.90,
        1.10,
    )
    ypa = DEFAULT_YPA * _clamp(
        1.0 + YPA_OFFENSE_SCALE * (float(factors.offense_index) - 1.0),
        0.88,
        1.14,
    )
    ypc = DEFAULT_YPC * _clamp(
        1.0 + YPC_OFFENSE_SCALE * (float(factors.offense_index) - 1.0),
        0.90,
        1.12,
    )
    games = max(1.0, float(factors.games or GAMES_PER_TEAM))
    pass_plays = pace * pass_rate * games
    rush_plays = pace * (1.0 - pass_rate) * games
    # Named skill share of team pool; QB attempts ≈ pass plays × attempt share.
    structural_pass = (
        pass_plays
        * ATTEMPT_SHARE_OF_PASS_PLAYS
        * ypa
        * opp_pass_mult
        * NAMED_SHARE
    )
    structural_rush = rush_plays * ypc * opp_rush_mult * NAMED_SHARE
    notes: List[str] = [
        "structural_budget_v1",
        f"coach={coach.label}",
    ]

    pass_yards = structural_pass
    rush_yards = structural_rush
    league_pass_team = LEAGUE_PASS_YARDS_POOL / 32.0
    league_rush_team = LEAGUE_RUSH_YARDS_POOL / 32.0

    if factors.pass_yards_prior is not None and float(factors.pass_yards_prior) > 0:
        prior = float(factors.pass_yards_prior)
        prior_regressed = league_pass_team + (1.0 - VOLUME_REGRESSION) * (
            prior - league_pass_team
        )
        pass_yards = (1.0 - VOLUME_PRIOR_BLEND) * structural_pass + VOLUME_PRIOR_BLEND * prior_regressed
        notes.append("pass_volume_prior_regression")
    else:
        # Mild shrink of structural tails without erasing team strength.
        pass_yards = league_pass_team + (1.0 - 0.18 * VOLUME_REGRESSION) * (
            structural_pass - league_pass_team
        )

    if factors.rush_yards_prior is not None and float(factors.rush_yards_prior) > 0:
        prior = float(factors.rush_yards_prior)
        prior_regressed = league_rush_team + (1.0 - VOLUME_REGRESSION) * (
            prior - league_rush_team
        )
        rush_yards = (1.0 - VOLUME_PRIOR_BLEND) * structural_rush + VOLUME_PRIOR_BLEND * prior_regressed
        notes.append("rush_volume_prior_regression")
    else:
        rush_yards = league_rush_team + (1.0 - 0.18 * VOLUME_REGRESSION) * (
            structural_rush - league_rush_team
        )

    return TeamSeasonBudget(
        team=factors.team,
        pass_yards=pass_yards,
        rush_yards=rush_yards,
        rec_yards=pass_yards * 0.92,
        pass_plays=pass_plays,
        rush_plays=rush_plays,
        pass_rate=pass_rate,
        pace_plays=pace,
        ypa=ypa * opp_pass_mult,
        ypc=ypc * opp_rush_mult,
        structural_pass_yards=structural_pass,
        structural_rush_yards=structural_rush,
        notes=tuple(notes),
    )


def _renormalize_pool(
    budgets: Dict[str, TeamSeasonBudget],
    *,
    pass_pool: float,
    rush_pool: float,
) -> Dict[str, TeamSeasonBudget]:
    pass_sum = sum(b.pass_yards for b in budgets.values()) or 1.0
    rush_sum = sum(b.rush_yards for b in budgets.values()) or 1.0
    pass_scale = float(pass_pool) / pass_sum
    rush_scale = float(rush_pool) / rush_sum
    out: Dict[str, TeamSeasonBudget] = {}
    for team, b in budgets.items():
        out[team] = TeamSeasonBudget(
            team=b.team,
            pass_yards=b.pass_yards * pass_scale,
            rush_yards=b.rush_yards * rush_scale,
            rec_yards=b.pass_yards * pass_scale * 0.92,
            pass_plays=b.pass_plays,
            rush_plays=b.rush_plays,
            pass_rate=b.pass_rate,
            pace_plays=b.pace_plays,
            ypa=b.ypa,
            ypc=b.ypc,
            structural_pass_yards=b.structural_pass_yards,
            structural_rush_yards=b.structural_rush_yards,
            notes=tuple(list(b.notes) + ["league_pool_renorm"]),
        )
    return out


def compute_team_season_budgets(
    factors_by_team: Mapping[str, TeamVolumeFactors],
    *,
    pass_pool: float = LEAGUE_PASS_YARDS_POOL,
    rush_pool: float = LEAGUE_RUSH_YARDS_POOL,
    qb_profiles: Optional[Mapping[str, QbRushingProfile]] = None,
    ol_protection: Optional[Mapping[str, OlProtectionFeature]] = None,
    continuity_travel: Optional[Mapping[str, float]] = None,
    returning_qb: Optional[Mapping[str, bool]] = None,
    pass_yards_prior: Optional[Mapping[str, float]] = None,
    new_regime: Optional[Mapping[str, bool]] = None,
) -> Dict[str, TeamSeasonBudget]:
    """Build conserved team season budgets for the league."""
    raw = {
        team: structural_team_budget(factors)
        for team, factors in factors_by_team.items()
    }
    # General features after base talent/scheme, before 126k two-way pool.
    adjusted = apply_general_volume_features(
        raw,
        qb_profiles=qb_profiles,
        ol_protection=ol_protection,
        continuity_travel=continuity_travel,
        returning_qb=returning_qb,
        pass_yards_prior=pass_yards_prior,
        new_regime=new_regime,
    )
    return _renormalize_pool(adjusted, pass_pool=pass_pool, rush_pool=rush_pool)


def _volume_feature_context_from_universe(
    universe: EngineUniverse,
) -> Dict[str, Any]:
    """Pull QB / OL / continuity inputs from SoT + roster rush shares."""
    from src.services.nfl_season_engine.qb_rushing_profile import (
        profiles_from_depth_rows,
    )

    qb_profiles: Dict[str, QbRushingProfile] = {}
    # Prefer packaged depth SoT player_ids (identity join).
    try:
        from src.services.nfl_season_engine.loaders import load_packaged_depth_chart

        depth_rows, depth_meta = load_packaged_depth_chart(int(universe.season))
        qb_profiles.update(profiles_from_depth_rows(depth_rows))
        ol_roles = list(depth_meta.get("ol_roles") or [])
    except Exception:
        depth_rows, depth_meta, ol_roles = [], {}, []

    # Fill gaps from roster rush_share (demo / thin packs).
    for team, roles in (universe.rosters or {}).items():
        if str(team) in qb_profiles:
            continue
        for role in roles or []:
            if str(getattr(role, "position", "") or "").upper() != "QB":
                continue
            try:
                depth = int(getattr(role, "depth_order", 99) or 99)
            except (TypeError, ValueError):
                continue
            if depth != 1:
                continue
            rs = float(getattr(role, "rush_share", 0.0) or 0.0)
            qb_profiles[str(team)] = resolve_qb1_profile(
                player_id=str(getattr(role, "player_id", "") or ""),
                player_name=str(getattr(role, "player_name", "") or ""),
                team=str(team),
                rush_share=rs if rs > 0 else None,
            )

    notes = getattr(universe, "notes", None) or {}
    if isinstance(notes, Mapping) and notes.get("ol_roles"):
        ol_roles = list(notes.get("ol_roles") or [])  # type: ignore[arg-type]

    ol_book = build_ol_protection_book(
        [r for r in ol_roles if isinstance(r, Mapping)],
        teams=list(factors_from_universe(universe).keys()),
    )

    continuity_travel: Dict[str, float] = {}
    returning_qb: Dict[str, bool] = {}
    new_regime: Dict[str, bool] = {}
    for team, state in (universe.strengths or {}).items():
        drivers = getattr(state, "drivers", None) or {}
        if not isinstance(drivers, Mapping):
            continue
        cont = drivers.get("continuity") or {}
        if not isinstance(cont, Mapping):
            continue
        travel = cont.get("prior_travel_weight")
        if travel is not None:
            continuity_travel[str(team)] = float(travel)
        for fac in cont.get("factors") or []:
            if not isinstance(fac, Mapping):
                continue
            name = str(fac.get("name") or "")
            if name in {"qb", "qb_returning", "qb_continuity"}:
                returning_qb[str(team)] = float(fac.get("score") or 0) >= 0.6
            if name in {"staff", "hc_oc", "coaching_staff"}:
                # Low staff continuity ⇒ new regime.
                if float(fac.get("score") or 1.0) < 0.45:
                    new_regime[str(team)] = True
        if str(team) not in returning_qb and cont.get("continuity_score") is not None:
            returning_qb[str(team)] = float(cont["continuity_score"]) >= 0.62
        if cont.get("continuity_score") is not None and float(cont["continuity_score"]) < 0.45:
            new_regime[str(team)] = True

    # Curated staff change book (continuity_score.CURATED_STAFF_BY_SEASON) as
    # new-regime signal when drivers lack continuity factors.
    try:
        from src.services.nfl_season_engine.continuity_score import (
            CURATED_STAFF_BY_SEASON,
        )

        staff = CURATED_STAFF_BY_SEASON.get(int(universe.season)) or {}
        for team, flags in staff.items():
            if flags.get("new_hc") or flags.get("new_oc"):
                new_regime[str(team)] = True
                # New OC alone still allows returning-QB prior; new HC+OC or
                # new HC dampens travel if not already set.
                if flags.get("new_hc") and flags.get("new_oc"):
                    continuity_travel.setdefault(str(team), 0.40)
                elif flags.get("new_oc"):
                    continuity_travel.setdefault(str(team), 0.55)
    except Exception:
        pass

    return {
        "qb_profiles": qb_profiles,
        "ol_protection": ol_book,
        "continuity_travel": continuity_travel,
        "returning_qb": returning_qb,
        "new_regime": new_regime,
    }


def compute_universe_season_budgets(universe: EngineUniverse) -> Dict[str, TeamSeasonBudget]:
    ctx = _volume_feature_context_from_universe(universe)
    return compute_team_season_budgets(factors_from_universe(universe), **ctx)


def qb1_pass_yards_by_team(
    player_rows: Iterable[Mapping[str, Any]],
    *,
    pass_key: str = "pass_yards",
) -> Dict[str, float]:
    """Max pass yards per team (QB1 proxy)."""
    by_team: Dict[str, float] = {}
    for row in player_rows:
        if str(row.get("position") or "").upper() != "QB":
            continue
        team = str(row.get("team") or "")
        if not team:
            continue
        yards = float(row.get(pass_key) or row.get("pass_yards_mean") or row.get("pass_yards_total") or 0.0)
        by_team[team] = max(by_team.get(team, 0.0), yards)
    return by_team


def qb1_distribution_metrics(
    player_rows: Iterable[Mapping[str, Any]],
    *,
    pass_key: str = "pass_yards",
) -> Dict[str, Any]:
    qb1 = list(qb1_pass_yards_by_team(player_rows, pass_key=pass_key).values())
    if not qb1:
        return {
            "n_teams": 0,
            "ge_4000": 0,
            "ge_4500": 0,
            "median": 0.0,
            "p10": 0.0,
            "p90": 0.0,
            "min": 0.0,
            "max": 0.0,
            "mean": 0.0,
        }
    qb1_sorted = sorted(qb1)
    n = len(qb1_sorted)

    def _pct(p: float) -> float:
        if n == 1:
            return qb1_sorted[0]
        idx = int(round(p * (n - 1)))
        return qb1_sorted[max(0, min(n - 1, idx))]

    return {
        "n_teams": n,
        "ge_4000": sum(1 for x in qb1 if x >= 4000.0),
        "ge_4500": sum(1 for x in qb1 if x >= 4500.0),
        "median": round(statistics.median(qb1), 2),
        "p10": round(_pct(0.10), 2),
        "p90": round(_pct(0.90), 2),
        "min": round(min(qb1), 2),
        "max": round(max(qb1), 2),
        "mean": round(statistics.mean(qb1), 2),
        "stdev": round(statistics.pstdev(qb1), 2) if n > 1 else 0.0,
    }


def league_yard_totals(
    player_rows: Iterable[Mapping[str, Any]],
    *,
    pass_key: str = "pass_yards",
    rush_key: str = "rush_yards",
    rec_key: str = "rec_yards",
) -> Dict[str, float]:
    pass_y = 0.0
    rush_y = 0.0
    rec_y = 0.0
    for row in player_rows:
        pass_y += float(row.get(pass_key) or row.get("pass_yards_mean") or row.get("pass_yards_total") or 0.0)
        rush_y += float(row.get(rush_key) or row.get("rush_yards_mean") or row.get("rush_yards_total") or 0.0)
        rec_y += float(
            row.get(rec_key)
            or row.get("rec_yards_mean")
            or row.get("receiving_yards_total")
            or row.get("rec_yards_total")
            or 0.0
        )
    return {
        "pass_yards": round(pass_y, 2),
        "rush_yards": round(rush_y, 2),
        "rec_yards": round(rec_y, 2),
    }


def _scale_rows_field(
    rows: Sequence[MutableMapping[str, Any]],
    field: str,
    scale: float,
    *,
    companions: Sequence[str] = (),
) -> None:
    if abs(scale - 1.0) < 1e-9:
        return
    for row in rows:
        row[field] = float(row.get(field) or 0.0) * scale
        for c in companions:
            if c in row:
                row[c] = float(row.get(c) or 0.0) * scale


def enforce_team_season_budgets_on_path(
    player_totals: Dict[str, Dict[str, Any]],
    budgets: Mapping[str, TeamSeasonBudget],
    *,
    tol: float = 1.02,
) -> Dict[str, Any]:
    """Allocate named season totals **into** team budgets (path conservation).

    Two-way scale (same contract as fantasy ``allocate_season_totals_into_team_budgets``):
    overflow caps down, underfill lifts toward the team pool. Scale-down-only left
    the packaged board with a dead ~3.1k QB1 median while budgets sat near 3.7k.
    """
    by_team: Dict[str, List[str]] = {}
    for key, row in player_totals.items():
        team = str(row.get("team") or "")
        if team:
            by_team.setdefault(team, []).append(key)

    teams_diag: Dict[str, Any] = {}
    scaled_fields = 0
    for team in sorted(by_team.keys()):
        keys = by_team[team]
        budget = budgets.get(team)
        if budget is None:
            continue
        pass_sum = sum(float(player_totals[k].get("pass_yards") or 0.0) for k in keys)
        rush_sum = sum(float(player_totals[k].get("rush_yards") or 0.0) for k in keys)
        rec_sum = sum(float(player_totals[k].get("rec_yards") or 0.0) for k in keys)
        scales: Dict[str, float] = {}

        def _allocate(field: str, td_field: str, total: float, target: float) -> None:
            nonlocal scaled_fields
            if total <= 1e-9 or target <= 0:
                return
            ratio = total / target
            # Skip microscopic drift inside tol band.
            if (1.0 / tol) <= ratio <= tol:
                return
            s = target / total
            scales[field] = round(s, 4)
            scaled_fields += 1
            for k in keys:
                player_totals[k][field] = float(player_totals[k].get(field) or 0.0) * s
                player_totals[k][td_field] = float(player_totals[k].get(td_field) or 0.0) * s

        _allocate("pass_yards", "pass_tds", pass_sum, float(budget.pass_yards))
        _allocate("rush_yards", "rush_tds", rush_sum, float(budget.rush_yards))
        _allocate("rec_yards", "rec_tds", rec_sum, float(budget.rec_yards))
        teams_diag[team] = {
            "budget": budget.to_dict(),
            "pre": {
                "pass_yards": round(pass_sum, 2),
                "rush_yards": round(rush_sum, 2),
                "rec_yards": round(rec_sum, 2),
            },
            "scales": scales,
        }
    return {
        "ok": scaled_fields == 0,
        "scaled_fields": scaled_fields,
        "teams": teams_diag,
        "method": "season_budget_path_allocate_v2",
    }


def allocate_season_totals_into_team_budgets(
    rows: List[Dict[str, Any]],
    budgets: Mapping[str, TeamSeasonBudget],
    *,
    pass_key: str = "pass_yards_total",
    rush_key: str = "rush_yards_total",
    rec_key: str = "receiving_yards_total",
    pass_td_key: str = "pass_tds_total",
    rush_td_key: str = "rush_tds_total",
    rec_td_key: str = "rec_tds_total",
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Fantasy / CSV path: scale player season totals into team budgets.

    Preserves within-team share structure (after QB starter lock). Does not
    invent volume when a team is under budget — only caps overflow and, when
    under by a large margin, gently lifts the primary skill shares so league
    pools stay near target.
    """
    by_team: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        by_team.setdefault(str(row.get("team") or ""), []).append(row)

    audit: Dict[str, Any] = {"teams": {}, "method": "fantasy_team_budget_alloc_v1"}
    for team, team_rows in by_team.items():
        budget = budgets.get(team)
        if budget is None or not team:
            continue
        pass_sum = sum(float(r.get(pass_key) or 0.0) for r in team_rows)
        rush_sum = sum(float(r.get(rush_key) or 0.0) for r in team_rows)
        rec_sum = sum(float(r.get(rec_key) or 0.0) for r in team_rows)
        scales: Dict[str, float] = {}
        if pass_sum > 1e-6:
            s = budget.pass_yards / pass_sum
            scales[pass_key] = round(s, 4)
            _scale_rows_field(team_rows, pass_key, s, companions=(pass_td_key,))
        if rush_sum > 1e-6:
            s = budget.rush_yards / rush_sum
            scales[rush_key] = round(s, 4)
            _scale_rows_field(team_rows, rush_key, s, companions=(rush_td_key,))
        if rec_sum > 1e-6:
            s = budget.rec_yards / rec_sum
            scales[rec_key] = round(s, 4)
            _scale_rows_field(team_rows, rec_key, s, companions=(rec_td_key,))
        audit["teams"][team] = {
            "budget_pass": round(budget.pass_yards, 1),
            "budget_rush": round(budget.rush_yards, 1),
            "pre_pass": round(pass_sum, 1),
            "pre_rush": round(rush_sum, 1),
            "scales": scales,
        }

    rows.sort(
        key=lambda r: (
            -(
                float(r.get(pass_key) or 0.0)
                + float(r.get(rush_key) or 0.0)
                + float(r.get(rec_key) or 0.0)
            ),
            str(r.get("player_name") or ""),
        )
    )
    return rows, audit


def factors_from_strength_dicts(
    strengths: Mapping[str, Mapping[str, Any]],
    *,
    opp_defense: Optional[Mapping[str, float]] = None,
    pass_priors: Optional[Mapping[str, float]] = None,
    rush_priors: Optional[Mapping[str, float]] = None,
) -> Dict[str, TeamVolumeFactors]:
    """Build factors from plain dicts (fantasy / CSV path, no EngineUniverse)."""
    out: Dict[str, TeamVolumeFactors] = {}
    for team, payload in strengths.items():
        out[str(team)] = TeamVolumeFactors(
            team=str(team),
            offense_index=float(payload.get("offense_index", 1.0) or 1.0),
            defense_index=float(payload.get("defense_index", 1.0) or 1.0),
            pace_factor=float(payload.get("pace_factor", 1.0) or 1.0),
            pass_rate_bias=float(payload.get("pass_rate_bias", 0.0) or 0.0),
            opp_defense_index_mean=float((opp_defense or {}).get(str(team), 1.0)),
            pass_yards_prior=(pass_priors or {}).get(str(team)),
            rush_yards_prior=(rush_priors or {}).get(str(team)),
        )
    return out


def synthetic_strengths_from_team_pass_raw(
    team_pass_raw: Mapping[str, float],
) -> Dict[str, Dict[str, Any]]:
    """When no Layer-1 book exists, derive relative offense from raw pass volume.

    Used only as a fallback so fantasy aggregation can still apply conserved
    budgets. Labels the result as approximate.
    """
    if not team_pass_raw:
        return {}
    values = list(team_pass_raw.values())
    mean = statistics.mean(values) if values else 1.0
    stdev = statistics.pstdev(values) if len(values) > 1 else 1.0
    stdev = max(stdev, 1.0)
    out: Dict[str, Dict[str, Any]] = {}
    for team, raw in team_pass_raw.items():
        z = (float(raw) - mean) / stdev
        # Map z≈[-2,2] → offense_index≈[0.88, 1.12]
        oi = _clamp(1.0 + 0.06 * z, 0.86, 1.16)
        pass_bias = _clamp(0.025 * z, -0.06, 0.06)
        pace = _clamp(1.0 + 0.02 * z, 0.92, 1.08)
        out[str(team)] = {
            "offense_index": oi,
            "defense_index": 1.0,
            "pace_factor": pace,
            "pass_rate_bias": pass_bias,
            "source": "synthetic_from_raw_pass_approx",
        }
    return out


def budget_pool_diagnostics(budgets: Mapping[str, TeamSeasonBudget]) -> Dict[str, Any]:
    pass_vals = [b.pass_yards for b in budgets.values()]
    rush_vals = [b.rush_yards for b in budgets.values()]
    return {
        "n_teams": len(budgets),
        "pass_pool": round(sum(pass_vals), 2),
        "rush_pool": round(sum(rush_vals), 2),
        "pass_budget_min": round(min(pass_vals), 2) if pass_vals else 0.0,
        "pass_budget_max": round(max(pass_vals), 2) if pass_vals else 0.0,
        "pass_budget_stdev": round(statistics.pstdev(pass_vals), 2) if len(pass_vals) > 1 else 0.0,
        "pass_pool_target": LEAGUE_PASS_YARDS_POOL,
        "rush_pool_target": LEAGUE_RUSH_YARDS_POOL,
        "pass_pool_ok": abs(sum(pass_vals) - LEAGUE_PASS_YARDS_POOL) < 1.0,
        "rush_pool_ok": abs(sum(rush_vals) - LEAGUE_RUSH_YARDS_POOL) < 1.0,
    }
