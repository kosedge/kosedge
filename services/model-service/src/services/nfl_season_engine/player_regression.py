"""Player process priors, regression posture, and finite production.

Layer between usage (3) and production (4):

1. **Process prior** — opponent-/role-adjusted *efficiency* and opportunity,
   not raw yards / TDs / fantasy points as talent.
2. **Regression flags** — positive / negative / neutral with short drivers
   and honest confidence (thin evidence → no forced flag).
3. **Rookies** — conservative mean, wide uncertainty; draft capital may nudge
   mean slightly, never locks a finished product.
4. **Finite production** — team script / total owns the pool; named player
   yards/TDs cannot invent volume past the team cap.

Does not replace team true-PR blend, full-strength/current split, or the
demo-free packaged strength path.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from src.services.nfl_season_engine.calibration import (
    DEFAULT_PASS_TD_RATE,
    DEFAULT_REC_TD_RATE,
    DEFAULT_REC_TD_RATE_RB,
    DEFAULT_REC_TD_RATE_TE,
    DEFAULT_RUSH_TD_RATE_QB,
    DEFAULT_RUSH_TD_RATE_RB,
    DEFAULT_YPA,
    DEFAULT_YPC,
    USAGE_OTHER_BUCKET_FLOOR,
    position_efficiency_defaults,
)
from src.services.nfl_season_engine.types import (
    GameScript,
    PlayerBoxScore,
    PlayerRole,
)

# ---------------------------------------------------------------------------
# Measured knobs (documented — prefer coherent finite production over flash)
# ---------------------------------------------------------------------------
# How hard we shrink TD rates toward process when gap is large.
REGRESSION_SHRINK = 0.55
# Minimum |gap| × confidence before a non-neutral posture is assigned.
POSTURE_GAP_THRESHOLD = 0.12
# Confidence floor to emit a flag (else stay neutral with drivers noting thin evidence).
MIN_FLAG_CONFIDENCE = 0.35
# Rookie mean pull toward league defaults (1.0 = no pull).
ROOKIE_MEAN_SHRINK = 0.72
# Day-2/3 draft capital mild mean bump (never large).
ROOKIE_DRAFT_MEAN_BUMP = {1: 1.025, 2: 1.015, 3: 1.008}
ROOKIE_EXPERIENCE_CONFIDENCE = 0.45
# Finite production slack above team expected pool (poisson / variance headroom).
FINITE_POOL_SLACK = 1.10
# Approx points per offensive TD for converting implied totals → TD pool.
POINTS_PER_OFFENSIVE_TD = 6.6
# Share of team points from offensive TDs (rest FG / defensive / special).
OFFENSIVE_TD_POINT_SHARE = 0.72


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _league_td_rate(position: str, kind: str) -> float:
    pos = (position or "").upper()
    if kind == "pass":
        return DEFAULT_PASS_TD_RATE
    if kind == "rush":
        return DEFAULT_RUSH_TD_RATE_QB if pos == "QB" else DEFAULT_RUSH_TD_RATE_RB
    if pos == "TE":
        return DEFAULT_REC_TD_RATE_TE
    if pos == "RB":
        return DEFAULT_REC_TD_RATE_RB
    return DEFAULT_REC_TD_RATE


def _league_eff(position: str) -> Dict[str, float]:
    return position_efficiency_defaults(position, depth_order=1)


def process_efficiency_index(role: PlayerRole) -> float:
    """Efficiency process index vs league (1.0 = average). Ignores raw volume."""
    pos = (role.position or "").upper()
    league = _league_eff(pos)
    parts: List[float] = []
    if pos == "QB" and role.ypa > 0:
        parts.append(role.ypa / max(1e-6, league["ypa"]))
        # Mild INT process (lower INT → better process).
        if role.int_rate > 0:
            parts.append(max(0.7, min(1.3, league["int_rate"] / max(1e-6, role.int_rate))))
    elif pos == "RB":
        if role.ypc > 0:
            parts.append(role.ypc / max(1e-6, league["ypc"]))
        if role.ypr > 0 and role.target_share > 0.02:
            parts.append(role.ypr / max(1e-6, league["ypr"]))
    else:
        if role.ypr > 0:
            parts.append(role.ypr / max(1e-6, league["ypr"]))
        if role.catch_rate > 0:
            parts.append(role.catch_rate / max(1e-6, league["catch_rate"]))
    if not parts:
        return 1.0
    return _clamp(sum(parts) / len(parts), 0.70, 1.35)


def observed_td_index(role: PlayerRole) -> float:
    """Counting-stat TD-rate index vs league (not treated as talent alone)."""
    pos = (role.position or "").upper()
    ratios: List[float] = []
    if pos == "QB" and role.pass_td_rate > 0:
        ratios.append(role.pass_td_rate / max(1e-6, _league_td_rate(pos, "pass")))
    if role.rush_td_rate > 0 and (pos in ("RB", "QB") or role.rush_share > 0.05):
        ratios.append(role.rush_td_rate / max(1e-6, _league_td_rate(pos, "rush")))
    if role.rec_td_rate > 0 and pos in ("WR", "TE", "RB"):
        ratios.append(role.rec_td_rate / max(1e-6, _league_td_rate(pos, "rec")))
    if not ratios:
        return 1.0
    return _clamp(sum(ratios) / len(ratios), 0.55, 1.70)


def _evidence_weight(role: PlayerRole) -> float:
    """How much we trust process-vs-result signal (thin → low)."""
    conf = _clamp(float(role.role_confidence or 0.0), 0.0, 1.0)
    # Baseline-derived efficiency in source → more evidence than pure league defaults.
    src = (role.source or "").lower()
    baseline_boost = 0.15 if "baseline" in src else 0.0
    # Opportunity presence (not volume as talent — just that a role exists).
    opp = 0.0
    pos = (role.position or "").upper()
    if pos == "QB":
        opp = 0.2 if role.snap_share >= 0.5 else 0.05
    elif pos == "RB":
        opp = _clamp(role.rush_share / 0.45, 0.0, 0.25)
    else:
        opp = _clamp(role.target_share / 0.20, 0.0, 0.25)
    if role.is_rookie:
        # Rookies: never pretend we have a finished process read.
        conf = min(conf, 0.55)
    return _clamp(0.35 * conf + baseline_boost + opp, 0.15, 0.95)


def _situation_drivers(role: PlayerRole, process: float, td_idx: float) -> List[str]:
    drivers: List[str] = []
    gap = td_idx - process
    if gap >= POSTURE_GAP_THRESHOLD:
        drivers.append("td_rate_above_efficiency_process")
    elif gap <= -POSTURE_GAP_THRESHOLD:
        drivers.append("td_rate_below_efficiency_process")
    if process >= 1.08 and td_idx <= 0.95:
        drivers.append("strong_efficiency_soft_finish")
    if process <= 0.95 and td_idx >= 1.12:
        drivers.append("finish_rate_outpaced_process")
    if role.is_rookie:
        drivers.append("rookie_wide_uncertainty")
        if role.draft_round is not None and int(role.draft_round) <= 2:
            drivers.append(f"draft_capital_r{int(role.draft_round)}_mild_mean_nudge")
        else:
            drivers.append("rookie_conservative_mean")
    if float(role.role_confidence or 0.0) < 0.45:
        drivers.append("thin_role_evidence")
    if "baseline" not in (role.source or "").lower() and not role.is_rookie:
        drivers.append("league_default_efficiency_approx")
    # Situation upgrade heuristic: solid opportunity, process not elite yet.
    pos = (role.position or "").upper()
    upgraded = (
        (pos == "RB" and role.rush_share >= 0.40 and process >= 0.98 and td_idx <= 1.02)
        or (pos in ("WR", "TE") and role.target_share >= 0.18 and process >= 1.0 and td_idx <= 0.98)
    )
    if upgraded and gap <= 0.05:
        drivers.append("opportunity_supports_positive_regression")
    return drivers


@dataclass(frozen=True)
class PlayerProcessPrior:
    """Inspectable process / regression summary for one skill player."""

    player_key: str
    process_index: float
    observed_td_index: float
    td_process_gap: float
    regression_posture: str
    regression_confidence: float
    regression_drivers: Tuple[str, ...]
    is_rookie: bool
    experience_confidence: float
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "player_key": self.player_key,
            "process_index": round(self.process_index, 4),
            "observed_td_index": round(self.observed_td_index, 4),
            "td_process_gap": round(self.td_process_gap, 4),
            "regression_posture": self.regression_posture,
            "regression_confidence": round(self.regression_confidence, 4),
            "regression_drivers": list(self.regression_drivers),
            "is_rookie": bool(self.is_rookie),
            "experience_confidence": round(self.experience_confidence, 4),
            "notes": self.notes,
        }


def build_player_process_prior(role: PlayerRole) -> PlayerProcessPrior:
    """Derive process index, TD gap, and regression posture (no rate mutation)."""
    process = process_efficiency_index(role)
    td_idx = observed_td_index(role)
    gap = td_idx - process
    evidence = _evidence_weight(role)
    drivers = _situation_drivers(role, process, td_idx)

    posture = "neutral"
    conf = abs(gap) * evidence
    if conf >= MIN_FLAG_CONFIDENCE and abs(gap) >= POSTURE_GAP_THRESHOLD:
        if gap > 0:
            posture = "negative"
        else:
            posture = "positive"
    elif abs(gap) >= POSTURE_GAP_THRESHOLD and conf < MIN_FLAG_CONFIDENCE:
        drivers = list(drivers) + ["thin_evidence_no_forced_flag"]
        conf = min(conf, MIN_FLAG_CONFIDENCE - 0.01)

    # Situation-only positive candidate when TD gap is mild but opportunity upgraded.
    if (
        posture == "neutral"
        and "opportunity_supports_positive_regression" in drivers
        and evidence >= 0.40
    ):
        posture = "positive"
        conf = max(conf, 0.38)
        drivers = list(drivers) + ["situation_upgrade_candidate"]

    exp = float(role.experience_confidence or 1.0)
    if role.is_rookie:
        exp = min(exp, ROOKIE_EXPERIENCE_CONFIDENCE)

    note = "process_vs_td_finish"
    if role.is_rookie:
        note = "rookie_conservative_process"
    elif "league_default" in " ".join(drivers):
        note = "approximate_league_process"

    return PlayerProcessPrior(
        player_key=role.player_key,
        process_index=process,
        observed_td_index=td_idx,
        td_process_gap=gap,
        regression_posture=posture,
        regression_confidence=_clamp(conf, 0.0, 0.95),
        regression_drivers=tuple(drivers),
        is_rookie=bool(role.is_rookie),
        experience_confidence=exp,
        notes=note,
    )


def _shrink_td_rates(role: PlayerRole, prior: PlayerProcessPrior) -> Dict[str, float]:
    """Pull TD rates toward process; magnitude scaled by confidence."""
    # Positive gap (overperformed) → shrink rates down; negative → mild lift.
    shrink = _clamp(
        prior.td_process_gap * REGRESSION_SHRINK * max(0.25, prior.regression_confidence),
        -0.28,
        0.32,
    )
    scale = 1.0 - shrink
    return {
        "pass_td_rate": max(0.01, role.pass_td_rate * scale) if role.pass_td_rate > 0 else role.pass_td_rate,
        "rush_td_rate": max(0.005, role.rush_td_rate * scale) if role.rush_td_rate > 0 else role.rush_td_rate,
        "rec_td_rate": max(0.01, role.rec_td_rate * scale) if role.rec_td_rate > 0 else role.rec_td_rate,
    }


def _apply_rookie_mean(role: PlayerRole) -> Dict[str, float]:
    """Conservative efficiency mean for rookies; draft capital mild bump only."""
    if not role.is_rookie:
        return {}
    pos = (role.position or "").upper()
    league = _league_eff(pos)
    out: Dict[str, float] = {}
    shrink = ROOKIE_MEAN_SHRINK
    round_bump = 1.0
    if role.draft_round is not None:
        round_bump = float(ROOKIE_DRAFT_MEAN_BUMP.get(int(role.draft_round), 1.0))

    def _pull(val: float, lg: float) -> float:
        return (lg + (val - lg) * shrink) * round_bump

    if pos == "QB" and role.ypa > 0:
        out["ypa"] = _clamp(_pull(role.ypa, league["ypa"]), 5.8, 8.2)
        out["pass_td_rate"] = _clamp(
            _pull(role.pass_td_rate, league["pass_td_rate"]), 0.025, 0.055
        )
    if pos == "RB" and role.ypc > 0:
        out["ypc"] = _clamp(_pull(role.ypc, league["ypc"]), 3.2, 5.2)
        out["rush_td_rate"] = _clamp(
            _pull(role.rush_td_rate, league["rush_td_rate"]), 0.012, 0.045
        )
    if pos in ("WR", "TE", "RB") and role.ypr > 0:
        # Cap rookie YPR well below elite vet band even with draft bump.
        out["ypr"] = _clamp(_pull(role.ypr, league["ypr"]), 5.0, 13.8)
        out["rec_td_rate"] = _clamp(
            _pull(role.rec_td_rate, league.get("rec_td_rate", DEFAULT_REC_TD_RATE)),
            0.015,
            0.075,
        )
    return out


def apply_process_priors(role: PlayerRole) -> PlayerRole:
    """Annotate regression posture and apply measured rate pulls toward process."""
    # Idempotent: loaders may touch roster books more than once.
    if "process_regression_v1" in (role.source or ""):
        return role
    prior = build_player_process_prior(role)
    td_adj = _shrink_td_rates(role, prior)
    mid = replace(
        role,
        pass_td_rate=float(td_adj["pass_td_rate"]),
        rush_td_rate=float(td_adj["rush_td_rate"]),
        rec_td_rate=float(td_adj["rec_td_rate"]),
    )
    rookie_adj = _apply_rookie_mean(mid)
    exp = prior.experience_confidence
    src = role.source
    if "process_regression_v1" not in src:
        src = f"{src}+process_regression_v1"
    return replace(
        mid,
        pass_td_rate=float(rookie_adj.get("pass_td_rate", mid.pass_td_rate)),
        rush_td_rate=float(rookie_adj.get("rush_td_rate", mid.rush_td_rate)),
        rec_td_rate=float(rookie_adj.get("rec_td_rate", mid.rec_td_rate)),
        ypa=float(rookie_adj.get("ypa", mid.ypa)),
        ypc=float(rookie_adj.get("ypc", mid.ypc)),
        ypr=float(rookie_adj.get("ypr", mid.ypr)),
        experience_confidence=exp,
        process_index=prior.process_index,
        td_process_gap=prior.td_process_gap,
        regression_posture=prior.regression_posture,
        regression_confidence=prior.regression_confidence,
        regression_drivers=prior.regression_drivers,
        source=src,
    )


def apply_process_priors_to_roles(roles: Sequence[PlayerRole]) -> List[PlayerRole]:
    return [apply_process_priors(r) for r in roles]


def apply_process_priors_to_roster_book(
    rosters: Mapping[str, Sequence[PlayerRole]],
) -> Dict[str, List[PlayerRole]]:
    return {team: apply_process_priors_to_roles(roles) for team, roles in rosters.items()}


def regression_summary(role: PlayerRole) -> Dict[str, Any]:
    """Compact payload for season totals / game-box player rows."""
    return {
        "regression_posture": role.regression_posture or "neutral",
        "regression_confidence": round(float(role.regression_confidence or 0.0), 4),
        "regression_drivers": list(role.regression_drivers or ()),
        "process_index": round(float(role.process_index or 1.0), 4),
        "td_process_gap": round(float(role.td_process_gap or 0.0), 4),
        "is_rookie": bool(role.is_rookie),
        "experience_confidence": round(float(role.experience_confidence or 1.0), 4),
        "draft_round": role.draft_round,
    }


def efficiency_cv_mult(role: PlayerRole) -> float:
    """Widen production noise when experience_confidence is low (rookies)."""
    exp = _clamp(float(role.experience_confidence or 1.0), 0.0, 1.0)
    # Match player-projection-engine spirit: up to ~2× std at exp=0.
    return 1.0 + (1.0 - exp) * 1.0


def team_production_caps(
    script: GameScript,
    team: str,
    *,
    offense_index: float = 1.0,
) -> Dict[str, float]:
    """Finite yards / TD pools owned by team script (not independent player lines)."""
    if team == script.home_team:
        implied = float(script.home_implied_total or script.expected_home_score or 21.0)
        pass_rate = float(script.home_pass_rate)
    else:
        implied = float(script.away_implied_total or script.expected_away_score or 21.0)
        pass_rate = float(script.away_pass_rate)
    plays = float(script.pace_plays or 63.5)
    oi = _clamp(float(offense_index or 1.0), 0.75, 1.30)
    pass_plays = plays * pass_rate
    rush_plays = plays * (1.0 - pass_rate)
    td_cap = max(
        0.9,
        (implied * OFFENSIVE_TD_POINT_SHARE) / POINTS_PER_OFFENSIVE_TD,
    ) * FINITE_POOL_SLACK
    named_share = 1.0 - USAGE_OTHER_BUCKET_FLOOR
    return {
        "pass_yards": pass_plays * DEFAULT_YPA * oi * FINITE_POOL_SLACK * named_share,
        "rush_yards": rush_plays * DEFAULT_YPC * oi * FINITE_POOL_SLACK * named_share,
        "rec_yards": pass_plays * DEFAULT_YPA * 0.92 * oi * FINITE_POOL_SLACK * named_share,
        "skill_tds": td_cap * named_share,  # rush + rec TDs (QB pass TDs separate)
        "pass_tds": td_cap * 0.62 * named_share,
        "implied_total": implied,
        "named_share": named_share,
    }


def _scale_field(boxes: List[PlayerBoxScore], field: str, scale: float) -> List[PlayerBoxScore]:
    if abs(scale - 1.0) < 1e-9:
        return boxes
    out: List[PlayerBoxScore] = []
    for b in boxes:
        kwargs = {field: round(float(getattr(b, field)) * scale, 2)}
        out.append(replace(b, **kwargs))
    return out


def enforce_finite_team_production(
    boxes: Sequence[PlayerBoxScore],
    *,
    script: GameScript,
    strengths_offense: Optional[Mapping[str, float]] = None,
) -> Tuple[List[PlayerBoxScore], Dict[str, Any]]:
    """Scale named player production down when it overflows team pools.

    Never invents extra volume to fill a pool — only caps absurd overflow so
    three teammates cannot all "regress up" past the team total.
    """
    by_team: Dict[str, List[PlayerBoxScore]] = {}
    for b in boxes:
        by_team.setdefault(b.team, []).append(b)

    diag: Dict[str, Any] = {"teams": {}}
    out: List[PlayerBoxScore] = []
    for team, team_boxes in by_team.items():
        oi = 1.0
        if strengths_offense and team in strengths_offense:
            oi = float(strengths_offense[team])
        caps = team_production_caps(script, team, offense_index=oi)
        pass_y = sum(b.pass_yards for b in team_boxes)
        rush_y = sum(b.rush_yards for b in team_boxes)
        rec_y = sum(b.rec_yards for b in team_boxes)
        skill_td = sum(b.rush_tds + b.rec_tds for b in team_boxes)
        pass_td = sum(b.pass_tds for b in team_boxes)

        scaled = list(team_boxes)
        applied: Dict[str, float] = {}
        if pass_y > caps["pass_yards"] > 0:
            s = caps["pass_yards"] / pass_y
            scaled = _scale_field(scaled, "pass_yards", s)
            applied["pass_yards"] = round(s, 4)
        if rush_y > caps["rush_yards"] > 0:
            s = caps["rush_yards"] / rush_y
            scaled = _scale_field(scaled, "rush_yards", s)
            applied["rush_yards"] = round(s, 4)
        if rec_y > caps["rec_yards"] > 0:
            s = caps["rec_yards"] / rec_y
            scaled = _scale_field(scaled, "rec_yards", s)
            applied["rec_yards"] = round(s, 4)
        if skill_td > caps["skill_tds"] > 0:
            s = caps["skill_tds"] / skill_td
            scaled = _scale_field(scaled, "rush_tds", s)
            scaled = _scale_field(scaled, "rec_tds", s)
            applied["skill_tds"] = round(s, 4)
        if pass_td > caps["pass_tds"] > 0:
            s = caps["pass_tds"] / pass_td
            scaled = _scale_field(scaled, "pass_tds", s)
            applied["pass_tds"] = round(s, 4)

        diag["teams"][team] = {
            "caps": {k: round(v, 3) for k, v in caps.items()},
            "pre": {
                "pass_yards": round(pass_y, 2),
                "rush_yards": round(rush_y, 2),
                "rec_yards": round(rec_y, 2),
                "skill_tds": round(skill_td, 3),
                "pass_tds": round(pass_td, 3),
            },
            "scales_applied": applied,
        }
        out.extend(scaled)
    return out, diag


def named_sums_within_caps(
    boxes: Sequence[PlayerBoxScore],
    script: GameScript,
    *,
    strengths_offense: Optional[Mapping[str, float]] = None,
    tol: float = 1.02,
) -> bool:
    """Smell helper: named player sums ≤ team caps × tol (no mutation)."""
    by_team: Dict[str, List[PlayerBoxScore]] = {}
    for b in boxes:
        by_team.setdefault(b.team, []).append(b)
    for team, team_boxes in by_team.items():
        oi = float((strengths_offense or {}).get(team, 1.0))
        caps = team_production_caps(script, team, offense_index=oi)
        if sum(b.pass_yards for b in team_boxes) > caps["pass_yards"] * tol:
            return False
        if sum(b.rush_yards for b in team_boxes) > caps["rush_yards"] * tol:
            return False
        if sum(b.rec_yards for b in team_boxes) > caps["rec_yards"] * tol:
            return False
        if sum(b.rush_tds + b.rec_tds for b in team_boxes) > caps["skill_tds"] * tol:
            return False
    return True


# Back-compat alias used in early drafts / tests.
finite_coherence_ok = named_sums_within_caps


def method_notes() -> Dict[str, str]:
    return {
        "process_prior": (
            "Efficiency index from ypa/ypc/ypr/catch/int vs league defaults; "
            "opportunity used only for evidence weight — not as talent."
        ),
        "regression": (
            f"Posture when |td_index − process| ≥ {POSTURE_GAP_THRESHOLD} and "
            f"confidence ≥ {MIN_FLAG_CONFIDENCE}; TD rates shrink toward process "
            f"(shrink={REGRESSION_SHRINK}). Thin evidence → neutral."
        ),
        "rookies": (
            f"Mean pull {ROOKIE_MEAN_SHRINK} toward league; experience_confidence "
            f"capped at {ROOKIE_EXPERIENCE_CONFIDENCE}; draft R1–R3 mild bump only."
        ),
        "finite_production": (
            "Team implied total + pace owns yards/TD pools; named players capped "
            f"with other-bucket floor={USAGE_OTHER_BUCKET_FLOOR} and slack={FINITE_POOL_SLACK}."
        ),
        "stubs": (
            "Opponent-adjusted individual EPA/xYards thin when baselines absent — "
            "labeled league_default_efficiency_approx. No demo player production "
            "on packaged/DB paths."
        ),
    }
