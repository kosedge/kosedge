"""NFL Power Ratings desk — Model PR (points vs avg, neutral field) + Ryan layer.

Method **B** (documented): each franchise vs a synthetic league-average opponent
using the same ``expected_team_points`` path as the season engine. Raw margin is
then **zero-centered** so mean(Model PR) ≈ 0.

This is an **output** of existing Layer-1 strength — not a second hand-built
mini-model. No EPA/QB/OL/SOS double-count on top of the strength book.

Ryan Adj defaults to 0; Ryan PR = Model PR + Adj. Adj never overwrites Model PR.
Early-season Bayesian shrinkage updates Model PR only; Ryan applies after.

Edge Board Game PR (opponent/situation) stays on the game path — not here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from src.services.nfl_season_engine.calibration import (
    ENGINE_VERSION,
    LEAGUE_TEAM_PPG,
    MATCHUP_RESPONSE,
)
from src.services.nfl_season_engine.team_strength import expected_team_points
from src.services.nfl_season_engine.types import TeamStrengthState

POWER_RATINGS_DESK_VERSION = "v1.0-method-b"
METHOD_ID = "B"
METHOD_LABEL = (
    "B — expected margin vs synthetic league-average opponent "
    "(expected_team_points), then zero-center"
)

# Canonical product team ids (LAR not LA). Package strengths may still use LA.
_PRODUCT_TEAM_ALIASES = {"LA": "LAR", "WSH": "WAS"}

# ---------------------------------------------------------------------------
# Early-season Bayesian shrinkage — α = weight on new evidence (PR_data)
# PR_published = (1 − α_W) * PR_prior + α_W * PR_data
# ---------------------------------------------------------------------------
# Midpoint of the brief's ranges; config is the single source of truth.
ALPHA_BY_WEEK: Dict[int, float] = {
    1: 0.12,
    2: 0.20,
    3: 0.30,
    4: 0.40,
    5: 0.50,
    6: 0.55,
    7: 0.62,
    8: 0.70,
}
ALPHA_WEEK_9_PLUS = 0.80  # majority season data; soft cap below 1.0
ALPHA_CAP = 0.90

# Extra shrink (multiply α) when evidence is thin / noisy.
ALPHA_MULT_BACKUP_QB = 0.70
ALPHA_MULT_TINY_SAMPLE = 0.75
ALPHA_MULT_EXTREME_SCRIPT = 0.80
ALPHA_MULT_MISSING_INJURY = 0.85

MEAN_TOLERANCE = 1e-6

# Ryan adj policy (documentation + validation helpers; Cursor invents zero adjs).
RYAN_ADJ_POLICY = {
    "routine": 0.25,
    "meaningful": 0.50,
    "major": 1.00,
    "requires_written_reason_above": 1.00,
}


def _utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(x)))


def product_team_id(team: str) -> str:
    code = str(team or "").strip().upper()
    return _PRODUCT_TEAM_ALIASES.get(code, code)


def alpha_for_week(week: int) -> float:
    """α_W — weight on PR_data after week W is final (ET Tuesday publish)."""
    w = int(week or 0)
    if w <= 0:
        return 0.0
    if w in ALPHA_BY_WEEK:
        return float(ALPHA_BY_WEEK[w])
    return float(ALPHA_WEEK_9_PLUS)


def adjusted_alpha(
    week: int,
    *,
    backup_qb: bool = False,
    tiny_sample: bool = False,
    extreme_script: bool = False,
    missing_injury_info: bool = False,
) -> float:
    """α after optional shrink-more multipliers; never exceeds ALPHA_CAP."""
    a = alpha_for_week(week)
    if backup_qb:
        a *= ALPHA_MULT_BACKUP_QB
    if tiny_sample:
        a *= ALPHA_MULT_TINY_SAMPLE
    if extreme_script:
        a *= ALPHA_MULT_EXTREME_SCRIPT
    if missing_injury_info:
        a *= ALPHA_MULT_MISSING_INJURY
    return _clamp(a, 0.0, ALPHA_CAP)


def apply_shrinkage(
    prior: float,
    data: float,
    alpha: float,
) -> float:
    """Bayesian blend: prior dominates early; data dominates mid/late."""
    a = _clamp(float(alpha), 0.0, 1.0)
    return (1.0 - a) * float(prior) + a * float(data)


def zero_center(values: Mapping[str, float]) -> Dict[str, float]:
    """Force mean ≈ 0 over the provided franchise set."""
    if not values:
        return {}
    mean = sum(float(v) for v in values.values()) / float(len(values))
    return {k: float(v) - mean for k, v in values.items()}


def _league_average_strength() -> TeamStrengthState:
    return TeamStrengthState(
        team="AVG",
        offense_index=1.0,
        defense_index=1.0,
        full_strength_offense_index=1.0,
        full_strength_defense_index=1.0,
        st_index=1.0,
        source="synthetic_league_average",
    )


def expected_margin_vs_average(
    strength: TeamStrengthState,
    *,
    use_full_strength: bool = True,
    week: int = 0,
) -> float:
    """Method B core: expected neutral-field margin vs average (no HFA)."""
    avg = _league_average_strength()
    if use_full_strength:
        off = float(
            getattr(strength, "full_strength_offense_index", None)
            or strength.offense_index
            or 1.0
        )
        deff = float(
            getattr(strength, "full_strength_defense_index", None)
            or strength.defense_index
            or 1.0
        )
    else:
        off = float(strength.offense_index or 1.0)
        deff = float(strength.defense_index or 1.0)

    team_off = TeamStrengthState(
        team=strength.team,
        offense_index=off,
        defense_index=deff,
        st_index=float(getattr(strength, "st_index", 1.0) or 1.0),
        source=str(getattr(strength, "source", "") or ""),
    )
    pts_for = expected_team_points(
        team_off, avg, home=False, week=int(week or 0)
    )
    pts_against = expected_team_points(
        avg, team_off, home=False, week=int(week or 0)
    )
    return float(pts_for) - float(pts_against)


def component_off_pr(strength: TeamStrengthState, *, week: int = 0) -> float:
    """Offense points vs league PPG facing average defense (neutral)."""
    avg = _league_average_strength()
    off = float(
        getattr(strength, "full_strength_offense_index", None)
        or strength.offense_index
        or 1.0
    )
    team_off = TeamStrengthState(
        team=strength.team, offense_index=off, defense_index=1.0
    )
    return float(expected_team_points(team_off, avg, home=False, week=week)) - float(
        LEAGUE_TEAM_PPG
    )


def component_def_pr(strength: TeamStrengthState, *, week: int = 0) -> float:
    """Defense points prevented vs league PPG (higher = better defense)."""
    avg = _league_average_strength()
    deff = float(
        getattr(strength, "full_strength_defense_index", None)
        or strength.defense_index
        or 1.0
    )
    team_def = TeamStrengthState(
        team=strength.team, offense_index=1.0, defense_index=deff
    )
    allowed = float(expected_team_points(avg, team_def, home=False, week=week))
    return float(LEAGUE_TEAM_PPG) - allowed


def component_st_pr(strength: TeamStrengthState) -> Tuple[float, bool]:
    """ST contribution in points; approximate when only st_index is available.

    Post-kicker-layer ST may be thin — callers should label ``approximate``.
    """
    st = float(getattr(strength, "st_index", 1.0) or 1.0)
    # Scale index gap through the same matchup response × PPG band as O/D.
    pts = float(LEAGUE_TEAM_PPG) * float(MATCHUP_RESPONSE) * (st - 1.0)
    approximate = abs(st - 1.0) < 1e-9 or True  # always label ST as approximate for now
    return pts, approximate


@dataclass
class RyanAdj:
    team: str
    adj: float = 0.0
    reason: str = ""
    updated_at_utc: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "team": self.team,
            "adj": round(float(self.adj), 4),
            "reason": self.reason or "",
            "updated_at_utc": self.updated_at_utc or "",
        }


@dataclass
class PowerRatingDeskRow:
    team: str
    model_pr: float
    ryan_adj: float = 0.0
    ryan_pr: float = 0.0
    market_pr: Optional[float] = None
    delta_market: Optional[float] = None
    off_pr: float = 0.0
    def_pr: float = 0.0
    st_pr: float = 0.0
    st_approximate: bool = True
    base_pr: float = 0.0
    active_pr: float = 0.0
    uncertainty: Optional[float] = None
    prev_week_model_pr: Optional[float] = None
    weekly_delta: Optional[float] = None
    ryan_reason: str = ""
    rank: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "team": self.team,
            "rank": self.rank,
            "model_pr": round(self.model_pr, 3),
            "ryan_adj": round(self.ryan_adj, 3),
            "ryan_pr": round(self.ryan_pr, 3),
            "market_pr": None
            if self.market_pr is None
            else round(float(self.market_pr), 3),
            "delta_market": None
            if self.delta_market is None
            else round(float(self.delta_market), 3),
            "off_pr": round(self.off_pr, 3),
            "def_pr": round(self.def_pr, 3),
            "st_pr": round(self.st_pr, 3),
            "st_approximate": bool(self.st_approximate),
            "base_pr": round(self.base_pr, 3),
            "active_pr": round(self.active_pr, 3),
            "uncertainty": None
            if self.uncertainty is None
            else round(float(self.uncertainty), 3),
            "prev_week_model_pr": None
            if self.prev_week_model_pr is None
            else round(float(self.prev_week_model_pr), 3),
            "weekly_delta": None
            if self.weekly_delta is None
            else round(float(self.weekly_delta), 3),
            "ryan_reason": self.ryan_reason or "",
        }


@dataclass
class ShrinkAuditRow:
    team: str
    prior_model_pr: float
    pr_data: float
    alpha: float
    published_model_pr: float
    ryan_adj: float
    ryan_pr: float
    off_pr: float
    def_pr: float
    st_pr: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "team": self.team,
            "prior_model_pr": round(self.prior_model_pr, 4),
            "pr_data": round(self.pr_data, 4),
            "alpha": round(self.alpha, 4),
            "published_model_pr": round(self.published_model_pr, 4),
            "ryan_adj": round(self.ryan_adj, 4),
            "ryan_pr": round(self.ryan_pr, 4),
            "off_pr": round(self.off_pr, 4),
            "def_pr": round(self.def_pr, 4),
            "st_pr": round(self.st_pr, 4),
        }


def uncertainty_from_strength(strength: TeamStrengthState, *, as_of_week: int) -> float:
    """Higher early / prior-heavy → higher uncertainty (points-ish band)."""
    w_prior = float(getattr(strength, "blend_prior_weight", 1.0) or 1.0)
    gp = int(getattr(strength, "games_played", 0) or 0)
    week = int(as_of_week or 0)
    base = 1.8 if week <= 4 else 1.2 if week <= 8 else 0.8
    prior_boost = 0.9 * w_prior
    sample_relief = min(0.9, 0.08 * gp)
    return round(max(0.35, base + prior_boost - sample_relief), 3)


def derive_raw_model_prs(
    strengths: Mapping[str, TeamStrengthState],
    *,
    use_full_strength: bool = True,
    week: int = 0,
) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for team, state in strengths.items():
        code = product_team_id(team)
        out[code] = expected_margin_vs_average(
            state, use_full_strength=use_full_strength, week=week
        )
    return out


def build_desk_rows(
    strengths: Mapping[str, TeamStrengthState],
    *,
    as_of_week: int = 0,
    ryan_adjs: Optional[Mapping[str, RyanAdj]] = None,
    market_prs: Optional[Mapping[str, float]] = None,
    prev_week_model_prs: Optional[Mapping[str, float]] = None,
    published_model_prs: Optional[Mapping[str, float]] = None,
) -> List[PowerRatingDeskRow]:
    """Build the master desk table from Layer-1 strengths.

    If ``published_model_prs`` is provided (post-shrink Tuesday snapshot), use
    those as Model PR; otherwise derive Method B from full-strength indices.
    """
    ryan_adjs = ryan_adjs or {}
    market_prs = market_prs or {}
    prev_week_model_prs = prev_week_model_prs or {}

    raw = derive_raw_model_prs(strengths, use_full_strength=True, week=0)
    model = (
        {product_team_id(k): float(v) for k, v in published_model_prs.items()}
        if published_model_prs
        else zero_center(raw)
    )
    # Keep mean ≈ 0 even if a published map drifts.
    model = zero_center(model)

    active_raw = derive_raw_model_prs(strengths, use_full_strength=False, week=0)
    active = zero_center(active_raw)

    off_raw = {
        product_team_id(t): component_off_pr(s)
        for t, s in strengths.items()
    }
    def_raw = {
        product_team_id(t): component_def_pr(s)
        for t, s in strengths.items()
    }
    off_c = zero_center(off_raw)
    def_c = zero_center(def_raw)

    # Dedup LA/LAR — prefer the strength row that already maps to product id.
    by_team: Dict[str, TeamStrengthState] = {}
    for team, state in strengths.items():
        code = product_team_id(team)
        if code not in by_team or str(team).upper() == code:
            by_team[code] = state

    rows: List[PowerRatingDeskRow] = []
    for team, state in by_team.items():
        mpr = float(model.get(team, 0.0))
        adj_obj = ryan_adjs.get(team) or RyanAdj(team=team, adj=0.0)
        adj = float(adj_obj.adj or 0.0)
        rpr = mpr + adj
        st_pts, st_approx = component_st_pr(state)
        mkt = market_prs.get(team)
        delta_mkt = None if mkt is None else rpr - float(mkt)
        prev = prev_week_model_prs.get(team)
        weekly = None if prev is None else mpr - float(prev)
        # Base = Ryan PR when adj ≠ 0 else Model PR (documented).
        base = rpr if abs(adj) > 1e-12 else mpr
        act = float(active.get(team, mpr)) + adj
        rows.append(
            PowerRatingDeskRow(
                team=team,
                model_pr=mpr,
                ryan_adj=adj,
                ryan_pr=rpr,
                market_pr=None if mkt is None else float(mkt),
                delta_market=delta_mkt,
                off_pr=float(off_c.get(team, 0.0)),
                def_pr=float(def_c.get(team, 0.0)),
                st_pr=round(st_pts, 3),
                st_approximate=st_approx,
                base_pr=base,
                active_pr=act,
                uncertainty=uncertainty_from_strength(state, as_of_week=as_of_week),
                prev_week_model_pr=None if prev is None else float(prev),
                weekly_delta=weekly,
                ryan_reason=adj_obj.reason or "",
            )
        )

    rows.sort(key=lambda r: (-r.model_pr, r.team))
    for i, row in enumerate(rows, start=1):
        row.rank = i
    return rows


def shrink_model_prs(
    prior: Mapping[str, float],
    data: Mapping[str, float],
    *,
    week: int,
    alpha_overrides: Optional[Mapping[str, float]] = None,
    flags: Optional[Mapping[str, Mapping[str, bool]]] = None,
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Apply per-team shrinkage; return (published zero-centered, alphas used)."""
    teams = sorted(set(prior.keys()) | set(data.keys()))
    alphas: Dict[str, float] = {}
    blended: Dict[str, float] = {}
    for team in teams:
        code = product_team_id(team)
        fl = dict((flags or {}).get(code) or (flags or {}).get(team) or {})
        if alpha_overrides and (code in alpha_overrides or team in alpha_overrides):
            a = float(alpha_overrides.get(code, alpha_overrides.get(team, 0.0)))
        else:
            a = adjusted_alpha(
                week,
                backup_qb=bool(fl.get("backup_qb")),
                tiny_sample=bool(fl.get("tiny_sample")),
                extreme_script=bool(fl.get("extreme_script")),
                missing_injury_info=bool(fl.get("missing_injury_info")),
            )
        alphas[code] = a
        blended[code] = apply_shrinkage(
            float(prior.get(code, prior.get(team, 0.0))),
            float(data.get(code, data.get(team, 0.0))),
            a,
        )
    return zero_center(blended), alphas


def serialize_power_ratings_desk(
    universe: Any,
    *,
    season: int = 2026,
    as_of_week: int = 0,
    phase: str = "preseason",
    active_run_id: Optional[str] = None,
    engine_version: str = "",
    ryan_adjs: Optional[Mapping[str, RyanAdj]] = None,
    market_prs: Optional[Mapping[str, float]] = None,
    prev_week_model_prs: Optional[Mapping[str, float]] = None,
    published_model_prs: Optional[Mapping[str, float]] = None,
    schedule_meta: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    strengths = getattr(universe, "strengths", {}) or {}
    rows = build_desk_rows(
        strengths,
        as_of_week=as_of_week,
        ryan_adjs=ryan_adjs,
        market_prs=market_prs,
        prev_week_model_prs=prev_week_model_prs,
        published_model_prs=published_model_prs,
    )
    mean_model = (
        sum(r.model_pr for r in rows) / float(len(rows)) if rows else 0.0
    )
    meta = dict(schedule_meta or {})
    return {
        "desk_version": POWER_RATINGS_DESK_VERSION,
        "method": METHOD_ID,
        "method_label": METHOD_LABEL,
        "engine_version": engine_version or ENGINE_VERSION,
        "season": int(season),
        "as_of_week": int(as_of_week),
        "phase": phase,
        "active_run_id": active_run_id,
        "generated_at_utc": _utc_now(),
        "team_count": len(rows),
        "mean_model_pr": round(mean_model, 6),
        "invariants": {
            "mean_model_pr_approx_0": abs(mean_model) < 0.05,
            "one_row_per_franchise": len(rows) == len({r.team for r in rows}),
        },
        "ryan_adj_policy": RYAN_ADJ_POLICY,
        "shrinkage": {
            "formula": "PR_published = (1 - alpha_W) * PR_prior + alpha_W * PR_data",
            "alpha_by_week": dict(ALPHA_BY_WEEK),
            "alpha_week_9_plus": ALPHA_WEEK_9_PLUS,
            "alpha_cap": ALPHA_CAP,
            "applies_to": "Model PR only; Ryan Adj applied after publish",
        },
        "base_active_game": {
            "base_pr": "Ryan PR if adj != 0 else Model PR",
            "active_pr": "Method B on current (injury-aware) indices + Ryan Adj",
            "game_pr": "Edge Board path only — not stored on this desk",
        },
        "strength_source": meta.get("strength_source") or meta.get("strengths") or "",
        "schedule_source": meta.get("schedule_source") or "",
        "columns": [
            "Team",
            "Model PR",
            "Ryan Adj",
            "Ryan PR",
            "Market PR",
            "Δ Mkt",
            "Off",
            "Def",
            "ST",
            "Active PR",
            "Unc.",
            "Prev Week",
            "Weekly Δ",
        ],
        "teams": [r.to_dict() for r in rows],
    }


def default_ryan_adjs(teams: Sequence[str]) -> Dict[str, RyanAdj]:
    """Cursor invents zero Ryan adjs — all default 0."""
    return {
        product_team_id(t): RyanAdj(team=product_team_id(t), adj=0.0, reason="")
        for t in teams
    }


def build_tuesday_audit(
    *,
    week: int,
    prior: Mapping[str, float],
    data: Mapping[str, float],
    published: Mapping[str, float],
    alphas: Mapping[str, float],
    desk_rows: Sequence[PowerRatingDeskRow],
    active_run_id: Optional[str],
    engine_version: str,
) -> Dict[str, Any]:
    by_team = {r.team: r for r in desk_rows}
    audits: List[Dict[str, Any]] = []
    for team in sorted(set(prior.keys()) | set(data.keys()) | set(published.keys())):
        code = product_team_id(team)
        row = by_team.get(code)
        audits.append(
            ShrinkAuditRow(
                team=code,
                prior_model_pr=float(prior.get(code, prior.get(team, 0.0))),
                pr_data=float(data.get(code, data.get(team, 0.0))),
                alpha=float(alphas.get(code, alphas.get(team, 0.0))),
                published_model_pr=float(
                    published.get(code, published.get(team, 0.0))
                ),
                ryan_adj=float(row.ryan_adj if row else 0.0),
                ryan_pr=float(row.ryan_pr if row else published.get(code, 0.0)),
                off_pr=float(row.off_pr if row else 0.0),
                def_pr=float(row.def_pr if row else 0.0),
                st_pr=float(row.st_pr if row else 0.0),
            ).to_dict()
        )
    return {
        "job": "tuesday_power_ratings_update",
        "week": int(week),
        "timezone_note": (
            "Publish Tuesday after the prior week's games are final (US/Eastern). "
            "Cutoff: Tuesday 06:00 ET (games may shift if MNF/TNF makeup)."
        ),
        "active_run_id": active_run_id,
        "engine_version": engine_version,
        "generated_at_utc": _utc_now(),
        "team_count": len(audits),
        "teams": audits,
    }
