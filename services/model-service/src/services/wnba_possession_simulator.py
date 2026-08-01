"""WNBA possession-level Monte Carlo simulator (v1 Phase 0–3).

Sport-specific (NOT an NBA copy-paste):
- 40-minute games (4×10); pace = possessions per **40**, not 48
- League pace ~80–82; higher pace volatility → **harmonic mean** of team paces
- ORtg/DRtg priors ~103 (calibrate from ingest)
- Home court start ~2.25 pts
- Do not import NBA player priors or NBA pace defaults
"""

from __future__ import annotations

import os
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, TypedDict

DEFAULT_WNBA_MODEL_VERSION = "wnba-v1-poss-sim"
WNBA_WORKER_BUILD_ID = os.getenv(
    "WNBA_WORKER_BUILD_ID",
    "wnba-poss-sim-20260801-phase3",
)

# Market blend defaults — conservative until close-line walkforward clears.
WNBA_MARKET_BLEND_SPREAD_WEIGHT = float(os.getenv("WNBA_MARKET_BLEND_SPREAD_WEIGHT", "0.42"))
WNBA_MARKET_BLEND_TOTAL_WEIGHT = float(os.getenv("WNBA_MARKET_BLEND_TOTAL_WEIGHT", "0.48"))

# League priors (research-backed starting points; ingest retunes).
WNBA_LEAGUE_PACE = 81.0
WNBA_LEAGUE_ORTG = 103.0
WNBA_LEAGUE_DRTG = 103.0
WNBA_HOME_COURT_DEFAULT = 2.25
WNBA_GAME_MINUTES = 40.0

TeamSide = Literal["home", "away"]


class PossessionEventType(str, Enum):
    """Canonical PBP event vocabulary for future chain deepening."""

    SHOT_MAKE = "shot_make"
    SHOT_MISS = "shot_miss"
    TURNOVER = "turnover"
    FOUL_SHOOTING = "foul_shooting"
    FOUL_NON_SHOOTING = "foul_non_shooting"
    REBOUND_OFF = "rebound_off"
    REBOUND_DEF = "rebound_def"
    FREE_THROW_MAKE = "free_throw_make"
    FREE_THROW_MISS = "free_throw_miss"
    POSSESSION_END = "possession_end"


class ShotZone(str, Enum):
    TWO = "two"
    THREE = "three"
    FREE_THROW = "free_throw"


@dataclass
class PossessionEvent:
    event_type: PossessionEventType
    team: TeamSide
    points: int = 0
    shot_zone: Optional[ShotZone] = None
    player_id: Optional[str] = None
    clock_seconds: Optional[float] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "team": self.team,
            "points": self.points,
            "shot_zone": self.shot_zone.value if self.shot_zone else None,
            "player_id": self.player_id,
            "clock_seconds": self.clock_seconds,
            "meta": self.meta,
        }


class PossessionOutcome(TypedDict):
    offense: TeamSide
    points: int
    events: List[Dict[str, Any]]
    ended_by: str


@dataclass
class WnbaGameInputs:
    game_id: str
    home_team: str
    away_team: str
    # Pace = possessions per 40 minutes (team average).
    pace_home: float = WNBA_LEAGUE_PACE
    pace_away: float = WNBA_LEAGUE_PACE
    # Ratings are points per 100 possessions.
    ortg_home: float = WNBA_LEAGUE_ORTG
    ortg_away: float = WNBA_LEAGUE_ORTG
    drtg_home: float = WNBA_LEAGUE_DRTG
    drtg_away: float = WNBA_LEAGUE_DRTG
    # Rising 3PT rate + assisted offense mix vs historical WNBA.
    three_pt_rate_home: float = 0.34
    three_pt_rate_away: float = 0.34
    three_pt_pct_home: float = 0.34
    three_pt_pct_away: float = 0.34
    two_pt_pct_home: float = 0.50
    two_pt_pct_away: float = 0.50
    ft_rate_home: float = 0.24
    ft_rate_away: float = 0.24
    ft_pct_home: float = 0.80
    ft_pct_away: float = 0.80
    to_rate_home: float = 0.155
    to_rate_away: float = 0.155
    orb_rate_home: float = 0.28
    orb_rate_away: float = 0.28
    rest_days_home: float = 2.0
    rest_days_away: float = 2.0
    home_court_advantage: float = WNBA_HOME_COURT_DEFAULT
    market_spread_home: Optional[float] = None
    market_total: Optional[float] = None
    feature_pack_version: Optional[str] = None
    sample_games_home: Optional[int] = None
    sample_games_away: Optional[int] = None


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _fair_moneyline_from_prob(prob: float) -> int:
    p = _clamp(prob, 0.001, 0.999)
    if p >= 0.5:
        return int(round(-(100.0 * p) / (1.0 - p)))
    return int(round((100.0 * (1.0 - p)) / p))


def _quantile(sorted_vals: List[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    q = _clamp(q, 0.0, 1.0)
    idx = int(round((len(sorted_vals) - 1) * q))
    return float(sorted_vals[idx])


def _beta_interval_from_wins(wins: int, losses: int, z: float = 1.645) -> Dict[str, float]:
    a = wins + 1.0
    b = losses + 1.0
    mean = a / (a + b)
    var = (a * b) / (((a + b) ** 2) * (a + b + 1.0))
    sd = max(var, 0.0) ** 0.5
    return {"low": _clamp(mean - z * sd, 0.0, 1.0), "high": _clamp(mean + z * sd, 0.0, 1.0)}


def _rest_multiplier(rest_days: float) -> float:
    # WNBA travel denser mid-season; mild B2B tilt.
    if rest_days <= 0.5:
        return 0.970
    if rest_days <= 1.0:
        return 0.982
    if rest_days >= 4.0:
        return 1.012
    return 1.0


def harmonic_mean_pace(pace_home: float, pace_away: float) -> float:
    """Expected game pace via harmonic mean (pace-volatility lesson).

    Arithmetic mean understates slowdown when one team is much slower;
    WNBA matchup pace spread (~24%) is wider than NBA (~15%).
    """
    a = max(1e-6, float(pace_home))
    b = max(1e-6, float(pace_away))
    return 2.0 * a * b / (a + b)


def _expected_possessions(inputs: WnbaGameInputs) -> float:
    pace = harmonic_mean_pace(inputs.pace_home, inputs.pace_away)
    return _clamp(pace, 68.0, 95.0)


def _offense_ppp(inputs: WnbaGameInputs, offense: TeamSide) -> float:
    if offense == "home":
        raw = 0.5 * (inputs.ortg_home + (200.0 - inputs.drtg_away)) / 100.0
        raw *= _rest_multiplier(inputs.rest_days_home)
        raw += inputs.home_court_advantage / 100.0
    else:
        raw = 0.5 * (inputs.ortg_away + (200.0 - inputs.drtg_home)) / 100.0
        raw *= _rest_multiplier(inputs.rest_days_away)
    return _clamp(raw, 0.78, 1.28)


def _team_rates(inputs: WnbaGameInputs, offense: TeamSide) -> Dict[str, float]:
    if offense == "home":
        return {
            "three_pt_rate": _clamp(inputs.three_pt_rate_home, 0.18, 0.50),
            "three_pt_pct": _clamp(inputs.three_pt_pct_home, 0.26, 0.42),
            "two_pt_pct": _clamp(inputs.two_pt_pct_home, 0.40, 0.62),
            "ft_rate": _clamp(inputs.ft_rate_home, 0.12, 0.42),
            "ft_pct": _clamp(inputs.ft_pct_home, 0.62, 0.94),
            "to_rate": _clamp(inputs.to_rate_home, 0.10, 0.24),
            "orb_rate": _clamp(inputs.orb_rate_home, 0.16, 0.40),
        }
    return {
        "three_pt_rate": _clamp(inputs.three_pt_rate_away, 0.18, 0.50),
        "three_pt_pct": _clamp(inputs.three_pt_pct_away, 0.26, 0.42),
        "two_pt_pct": _clamp(inputs.two_pt_pct_away, 0.40, 0.62),
        "ft_rate": _clamp(inputs.ft_rate_away, 0.12, 0.42),
        "ft_pct": _clamp(inputs.ft_pct_away, 0.62, 0.94),
        "to_rate": _clamp(inputs.to_rate_away, 0.10, 0.24),
        "orb_rate": _clamp(inputs.orb_rate_away, 0.16, 0.40),
    }


def _scale_make_probs(
    rates: Dict[str, float],
    *,
    target_ppp: float,
) -> Dict[str, float]:
    three_rate = rates["three_pt_rate"]
    two_rate = 1.0 - three_rate
    ft_rate = rates["ft_rate"]
    to_rate = rates["to_rate"]
    baseline = (
        (1.0 - to_rate)
        * (
            three_rate * 3.0 * rates["three_pt_pct"]
            + two_rate * 2.0 * rates["two_pt_pct"]
            + ft_rate * 2.0 * rates["ft_pct"] * 0.55
        )
    )
    scale = target_ppp / max(0.65, baseline)
    return {
        **rates,
        "three_pt_pct": _clamp(rates["three_pt_pct"] * scale, 0.24, 0.46),
        "two_pt_pct": _clamp(rates["two_pt_pct"] * scale, 0.38, 0.66),
    }


def resolve_possession(
    rng: random.Random,
    *,
    offense: TeamSide,
    inputs: WnbaGameInputs,
    collect_events: bool = False,
) -> PossessionOutcome:
    rates = _scale_make_probs(_team_rates(inputs, offense), target_ppp=_offense_ppp(inputs, offense))
    events: List[Dict[str, Any]] = []
    points = 0
    ended_by = "unknown"
    for _chain in range(4):
        if rng.random() < rates["to_rate"]:
            if collect_events:
                events.append(
                    PossessionEvent(
                        event_type=PossessionEventType.TURNOVER,
                        team=offense,
                    ).to_dict()
                )
            ended_by = "turnover"
            break

        is_three = rng.random() < rates["three_pt_rate"]
        zone = ShotZone.THREE if is_three else ShotZone.TWO
        make_prob = rates["three_pt_pct"] if is_three else rates["two_pt_pct"]

        if rng.random() < rates["ft_rate"] * 0.35:
            if collect_events:
                events.append(
                    PossessionEvent(
                        event_type=PossessionEventType.FOUL_SHOOTING,
                        team=offense,
                        shot_zone=zone,
                    ).to_dict()
                )
            ft_attempts = 3 if is_three else 2
            for _ in range(ft_attempts):
                made = rng.random() < rates["ft_pct"]
                if made:
                    points += 1
                if collect_events:
                    events.append(
                        PossessionEvent(
                            event_type=(
                                PossessionEventType.FREE_THROW_MAKE
                                if made
                                else PossessionEventType.FREE_THROW_MISS
                            ),
                            team=offense,
                            points=1 if made else 0,
                            shot_zone=ShotZone.FREE_THROW,
                        ).to_dict()
                    )
            ended_by = "shooting_foul"
            break

        made = rng.random() < make_prob
        if made:
            scored = 3 if is_three else 2
            points += scored
            if collect_events:
                events.append(
                    PossessionEvent(
                        event_type=PossessionEventType.SHOT_MAKE,
                        team=offense,
                        points=scored,
                        shot_zone=zone,
                    ).to_dict()
                )
            ended_by = "shot_make"
            break

        if collect_events:
            events.append(
                PossessionEvent(
                    event_type=PossessionEventType.SHOT_MISS,
                    team=offense,
                    shot_zone=zone,
                ).to_dict()
            )
        if rng.random() < rates["orb_rate"]:
            if collect_events:
                events.append(
                    PossessionEvent(
                        event_type=PossessionEventType.REBOUND_OFF,
                        team=offense,
                    ).to_dict()
                )
            continue
        if collect_events:
            defense: TeamSide = "away" if offense == "home" else "home"
            events.append(
                PossessionEvent(
                    event_type=PossessionEventType.REBOUND_DEF,
                    team=defense,
                ).to_dict()
            )
        ended_by = "defensive_rebound"
        break
    else:
        ended_by = "orb_chain_cap"

    if collect_events:
        events.append(
            PossessionEvent(
                event_type=PossessionEventType.POSSESSION_END,
                team=offense,
                points=points,
                meta={"ended_by": ended_by},
            ).to_dict()
        )

    return {
        "offense": offense,
        "points": points,
        "events": events,
        "ended_by": ended_by,
    }


def _apply_market_blend(
    *,
    margin_mean: float,
    total_mean: float,
    market_spread_home: Optional[float],
    market_total: Optional[float],
    sample_games_home: Optional[int],
    sample_games_away: Optional[int],
) -> Dict[str, Any]:
    spread_w = _clamp(WNBA_MARKET_BLEND_SPREAD_WEIGHT, 0.0, 0.85)
    total_w = _clamp(WNBA_MARKET_BLEND_TOTAL_WEIGHT, 0.0, 0.85)
    # Thin-sample boost — WNBA season is shorter (~40 games).
    sample = min(
        int(sample_games_home or 40),
        int(sample_games_away or 40),
    )
    if sample < 8:
        spread_w = _clamp(spread_w + 0.22, 0.0, 0.85)
        total_w = _clamp(total_w + 0.22, 0.0, 0.85)
    elif sample < 18:
        spread_w = _clamp(spread_w + 0.12, 0.0, 0.85)
        total_w = _clamp(total_w + 0.12, 0.0, 0.85)

    blended_margin = margin_mean
    blended_total = total_mean
    applied_spread = False
    applied_total = False
    if market_spread_home is not None:
        market_margin = -float(market_spread_home)
        blended_margin = (1.0 - spread_w) * margin_mean + spread_w * market_margin
        applied_spread = True
    if market_total is not None:
        blended_total = (1.0 - total_w) * total_mean + total_w * float(market_total)
        applied_total = True
    return {
        "margin_mean": blended_margin,
        "total_mean": blended_total,
        "spread_weight": spread_w if applied_spread else 0.0,
        "total_weight": total_w if applied_total else 0.0,
        "applied_spread": applied_spread,
        "applied_total": applied_total,
        "sample_games_min": sample,
        "pace_method": "harmonic_mean",
    }


def simulate_wnba_game(
    inputs: WnbaGameInputs,
    *,
    simulations: int = 4000,
    seed: Optional[int] = None,
    model_version: str = DEFAULT_WNBA_MODEL_VERSION,
    collect_event_sample: bool = False,
) -> Dict[str, Any]:
    """Run possession-level Monte Carlo → ML / spread / total distributions."""
    rng = random.Random(seed)
    sims = max(300, int(simulations))
    expected_poss = _expected_possessions(inputs)
    home_ppp = _offense_ppp(inputs, "home")
    away_ppp = _offense_ppp(inputs, "away")

    home_scores: List[float] = []
    away_scores: List[float] = []
    totals: List[float] = []
    margins: List[float] = []
    home_wins = 0
    ot_games = 0
    event_sample: List[Dict[str, Any]] = []

    for sim_idx in range(sims):
        # Pace is possessions *per team* per 40; full game ≈ 2× pace alternating.
        # Slightly wider pace noise than NBA (higher matchup volatility).
        n_poss = max(120, int(round(rng.gauss(2.0 * expected_poss, 6.0))))
        home = 0
        away = 0
        offense: TeamSide = "home" if rng.random() < 0.52 else "away"
        for _ in range(n_poss):
            want_events = collect_event_sample and sim_idx == 0
            outcome = resolve_possession(
                rng,
                offense=offense,
                inputs=inputs,
                collect_events=want_events,
            )
            if offense == "home":
                home += outcome["points"]
            else:
                away += outcome["points"]
            if want_events:
                event_sample.extend(outcome["events"])
            offense = "away" if offense == "home" else "home"

        # Overtime: WNBA OT is 5 minutes ≈ 4–6 possessions each.
        ot_rounds = 0
        while home == away and ot_rounds < 6:
            ot_rounds += 1
            ot_games += 1 if ot_rounds == 1 else 0
            for _ in range(5):
                outcome = resolve_possession(rng, offense=offense, inputs=inputs)
                if offense == "home":
                    home += outcome["points"]
                else:
                    away += outcome["points"]
                offense = "away" if offense == "home" else "home"

        if home > away:
            home_wins += 1
        home_scores.append(float(home))
        away_scores.append(float(away))
        totals.append(float(home + away))
        margins.append(float(home - away))

    totals_sorted = sorted(totals)
    margins_sorted = sorted(margins)
    home_mean = sum(home_scores) / sims
    away_mean = sum(away_scores) / sims
    total_mean = sum(totals) / sims
    margin_mean = sum(margins) / sims

    blend = _apply_market_blend(
        margin_mean=margin_mean,
        total_mean=total_mean,
        market_spread_home=inputs.market_spread_home,
        market_total=inputs.market_total,
        sample_games_home=inputs.sample_games_home,
        sample_games_away=inputs.sample_games_away,
    )
    margin_shift = blend["margin_mean"] - margin_mean
    total_shift = blend["total_mean"] - total_mean
    adj_margins = [m + margin_shift for m in margins]
    adj_totals = [t + total_shift for t in totals]
    adj_margins_sorted = sorted(adj_margins)
    adj_totals_sorted = sorted(adj_totals)
    adj_margin_mean = blend["margin_mean"]
    adj_total_mean = blend["total_mean"]
    adj_home_mean = (adj_total_mean + adj_margin_mean) / 2.0
    adj_away_mean = (adj_total_mean - adj_margin_mean) / 2.0

    adj_home_wins = sum(1 for m in adj_margins if m > 0)
    adj_pushes = sum(1 for m in adj_margins if m == 0)
    win_denom = max(1, sims - adj_pushes)
    home_win_prob = adj_home_wins / win_denom
    ci = _beta_interval_from_wins(adj_home_wins, max(0, win_denom - adj_home_wins))

    fair_spread_home = -round(adj_margin_mean * 2.0) / 2.0
    if abs(fair_spread_home) < 0.5:
        fair_spread_home = -0.5 if adj_margin_mean >= 0 else 0.5
    fair_total = round(adj_total_mean * 2.0) / 2.0

    home_covers = sum(1 for m in adj_margins if (m + fair_spread_home) > 0)
    home_cover_pushes = sum(1 for m in adj_margins if (m + fair_spread_home) == 0)
    cover_denom = max(1, sims - home_cover_pushes)
    home_cover_prob = home_covers / cover_denom

    return {
        "game_id": inputs.game_id,
        "model_version": model_version,
        "worker_build_id": WNBA_WORKER_BUILD_ID,
        "simulation_count": sims,
        "inputs": {
            "home_team": inputs.home_team,
            "away_team": inputs.away_team,
            "pace_home": inputs.pace_home,
            "pace_away": inputs.pace_away,
            "ortg_home": inputs.ortg_home,
            "ortg_away": inputs.ortg_away,
            "drtg_home": inputs.drtg_home,
            "drtg_away": inputs.drtg_away,
            "three_pt_rate_home": inputs.three_pt_rate_home,
            "three_pt_rate_away": inputs.three_pt_rate_away,
            "rest_days_home": inputs.rest_days_home,
            "rest_days_away": inputs.rest_days_away,
            "home_court_advantage": inputs.home_court_advantage,
            "market_spread_home": inputs.market_spread_home,
            "market_total": inputs.market_total,
            "feature_pack_version": inputs.feature_pack_version,
            "sample_games_home": inputs.sample_games_home,
            "sample_games_away": inputs.sample_games_away,
        },
        "rates": {
            "expected_possessions": round(expected_poss, 3),
            "pace_method": "harmonic_mean",
            "game_minutes": WNBA_GAME_MINUTES,
            "home_ppp": round(home_ppp, 4),
            "away_ppp": round(away_ppp, 4),
        },
        "markets": {
            "home_win_prob": home_win_prob,
            "away_win_prob": 1.0 - home_win_prob,
            "home_win_prob_ci_low": ci["low"],
            "home_win_prob_ci_high": ci["high"],
            "home_score_mean": round(adj_home_mean, 4),
            "away_score_mean": round(adj_away_mean, 4),
            "total_mean": round(adj_total_mean, 4),
            "total_p10": _quantile(adj_totals_sorted, 0.10),
            "total_p50": _quantile(adj_totals_sorted, 0.50),
            "total_p90": _quantile(adj_totals_sorted, 0.90),
            "margin_mean": round(adj_margin_mean, 4),
            "margin_p10": _quantile(adj_margins_sorted, 0.10),
            "margin_p50": _quantile(adj_margins_sorted, 0.50),
            "margin_p90": _quantile(adj_margins_sorted, 0.90),
            "fair_home_ml": _fair_moneyline_from_prob(home_win_prob),
            "fair_away_ml": _fair_moneyline_from_prob(1.0 - home_win_prob),
            "fair_total": fair_total,
            "fair_spread_home": fair_spread_home,
            "home_cover_prob": round(home_cover_prob, 6),
            "raw_total_mean": round(total_mean, 4),
            "raw_margin_mean": round(margin_mean, 4),
            "raw_home_score_mean": round(home_mean, 4),
            "raw_away_score_mean": round(away_mean, 4),
        },
        "diagnostics": {
            "simulator_type": "possession_monte_carlo",
            "sport": "wnba",
            "ot_rate": ot_games / sims,
            "push_rate": adj_pushes / sims,
            "market_blend": blend,
            "event_interface_version": "wnba-pbp-events-v1",
            "worker_build_id": WNBA_WORKER_BUILD_ID,
        },
        "event_sample": event_sample if collect_event_sample else [],
    }
