"""Team season pass/rush budgets for fantasy / preseason-sim season totals.

Mirrors ``nfl_season_engine.season_budgets`` math without importing
model-service (service-boundary: this package aggregates baselines only).

Contract: after weekly means are summed (and QB starter lock applied),
scale each team's named player yards into a conserved team budget so the
board is not 32 independent ~4.2k QB1 lines.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

# Keep in sync with nfl_season_engine.calibration / season_budgets (v1.17).
LEAGUE_BASE_PLAYS = 63.5
LEAGUE_BASE_PASS_RATE = 0.565
DEFAULT_YPA = 6.95
DEFAULT_YPC = 4.20
ATTEMPT_SHARE_OF_PASS_PLAYS = 0.925
LEAGUE_PASS_YARDS_POOL = 126_000.0
LEAGUE_RUSH_YARDS_POOL = 60_000.0  # Phase-1 offensive stack band (58–62k)
VOLUME_REGRESSION = 0.40
VOLUME_PRIOR_BLEND = 0.30
NAMED_SHARE = 0.92
GAMES_PER_TEAM = 17.0
PACE_OFFENSE_SCALE = 0.14
YPA_OFFENSE_SCALE = 0.55
YPC_OFFENSE_SCALE = 0.35
STRENGTH_PASS_BIAS_SCALE = 1.75
COACH_PASS_BIAS_SCALE = 1.35

# Targeted identity overlays (mirror season_budgets v1.17). Pre-pool only.
SEA_DARNOLD_PASS_BASELINE = 3_900.0
TEAM_PASS_VOLUME_IDENTITY_ADJUSTMENTS: Dict[str, Dict[str, float]] = {
    "ARI": {
        "residual_regression": 0.78,
        "scheme_mult": 0.92,
        "soft_ceiling": 4_250.0,
    },
    "BAL": {
        "residual_regression": 0.88,
        "scheme_mult": 1.12,
        "soft_floor": 3_150.0,
    },
    "SEA": {
        "darnold_anchor_weight": 0.70,
        "new_oc_weight": 0.30,
        "darnold_baseline": SEA_DARNOLD_PASS_BASELINE,
        "scheme_mult": 1.05,
        "soft_floor": 3_400.0,
    },
}

# Curated coaching pass biases (subset; others → 0). Keep modest.
_COACH_PASS_BIAS: Dict[str, float] = {
    "KC": 0.028,
    "BUF": 0.018,
    "SF": -0.022,
    "BAL": -0.028,
    "PHI": -0.020,
    "MIA": 0.030,
    "CIN": 0.022,
    "DET": 0.018,
    "MIN": 0.022,
    "DAL": 0.015,
    "LA": 0.018,
    "LAC": 0.020,
    "TB": 0.016,
    "PIT": -0.020,
    "TEN": -0.018,
    "CLE": -0.018,
    "NYJ": -0.012,
    "NE": -0.015,
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


@dataclass(frozen=True)
class TeamSeasonBudget:
    team: str
    pass_yards: float
    rush_yards: float
    rec_yards: float


def _structural_pass_rush(
    team: str,
    *,
    offense_index: float,
    pace_factor: float,
    pass_rate_bias: float,
) -> Tuple[float, float]:
    coach_bias = float(_COACH_PASS_BIAS.get(team, 0.0))
    pass_rate = _clamp(
        LEAGUE_BASE_PASS_RATE
        + STRENGTH_PASS_BIAS_SCALE * pass_rate_bias
        + COACH_PASS_BIAS_SCALE * coach_bias,
        0.42,
        0.72,
    )
    pace = _clamp(
        LEAGUE_BASE_PLAYS
        * pace_factor
        * (1.0 + PACE_OFFENSE_SCALE * (offense_index - 1.0)),
        48.0,
        78.0,
    )
    ypa = DEFAULT_YPA * _clamp(
        1.0 + YPA_OFFENSE_SCALE * (offense_index - 1.0), 0.88, 1.14
    )
    ypc = DEFAULT_YPC * _clamp(
        1.0 + YPC_OFFENSE_SCALE * (offense_index - 1.0), 0.90, 1.12
    )
    pass_plays = pace * pass_rate * GAMES_PER_TEAM
    rush_plays = pace * (1.0 - pass_rate) * GAMES_PER_TEAM
    pass_y = pass_plays * ATTEMPT_SHARE_OF_PASS_PLAYS * ypa * NAMED_SHARE
    rush_y = rush_plays * ypc * NAMED_SHARE
    # Mild structural-tail shrink (no prior available on this path).
    league_pass = LEAGUE_PASS_YARDS_POOL / 32.0
    league_rush = LEAGUE_RUSH_YARDS_POOL / 32.0
    pass_y = league_pass + (1.0 - 0.18 * VOLUME_REGRESSION) * (pass_y - league_pass)
    rush_y = league_rush + (1.0 - 0.18 * VOLUME_REGRESSION) * (rush_y - league_rush)
    return pass_y, rush_y


def synthetic_strengths_from_team_pass_raw(
    team_pass_raw: Mapping[str, float],
) -> Dict[str, Dict[str, float]]:
    if not team_pass_raw:
        return {}
    values = list(team_pass_raw.values())
    mean = statistics.mean(values) if values else 1.0
    stdev = statistics.pstdev(values) if len(values) > 1 else 1.0
    stdev = max(stdev, 1.0)
    out: Dict[str, Dict[str, float]] = {}
    for team, raw in team_pass_raw.items():
        z = (float(raw) - mean) / stdev
        out[str(team)] = {
            "offense_index": _clamp(1.0 + 0.06 * z, 0.86, 1.16),
            "pace_factor": _clamp(1.0 + 0.02 * z, 0.92, 1.08),
            "pass_rate_bias": _clamp(0.025 * z, -0.06, 0.06),
        }
    return out


def _apply_pass_identity_adjustments(
    raw: Mapping[str, Tuple[float, float]],
) -> Dict[str, Tuple[float, float]]:
    """ARI/BAL/SEA pass residual weights before league-pool renorm."""
    if not raw:
        return {}
    pass_vals = [float(p) for p, _ in raw.values()]
    league_mean = statistics.fmean(pass_vals) if pass_vals else (LEAGUE_PASS_YARDS_POOL / 32.0)
    out: Dict[str, Tuple[float, float]] = {}
    for team, (pass_y, rush_y) in raw.items():
        cfg = TEAM_PASS_VOLUME_IDENTITY_ADJUSTMENTS.get(str(team))
        if cfg is None:
            out[team] = (pass_y, rush_y)
            continue
        y = float(pass_y)
        if team == "SEA":
            baseline = float(cfg.get("darnold_baseline", SEA_DARNOLD_PASS_BASELINE))
            w_d = float(cfg.get("darnold_anchor_weight", 0.70))
            w_oc = float(cfg.get("new_oc_weight", 0.30))
            w_sum = w_d + w_oc
            if w_sum <= 0:
                w_d, w_oc, w_sum = 0.70, 0.30, 1.0
            y = (w_d * baseline + w_oc * y) / w_sum
        else:
            k = float(cfg.get("residual_regression", 1.0))
            y = league_mean + k * (y - league_mean)
        y *= float(cfg.get("scheme_mult", 1.0))
        floor = cfg.get("soft_floor")
        ceiling = cfg.get("soft_ceiling")
        if floor is not None:
            y = max(y, float(floor))
        if ceiling is not None:
            y = min(y, float(ceiling))
        out[team] = (y, rush_y)
    return out


def compute_team_season_budgets(
    strengths: Mapping[str, Mapping[str, float]],
) -> Dict[str, TeamSeasonBudget]:
    raw: Dict[str, Tuple[float, float]] = {}
    for team, payload in strengths.items():
        pass_y, rush_y = _structural_pass_rush(
            str(team),
            offense_index=float(payload.get("offense_index", 1.0) or 1.0),
            pace_factor=float(payload.get("pace_factor", 1.0) or 1.0),
            pass_rate_bias=float(payload.get("pass_rate_bias", 0.0) or 0.0),
        )
        raw[str(team)] = (pass_y, rush_y)
    adjusted = _apply_pass_identity_adjustments(raw)
    pass_sum = sum(p for p, _ in adjusted.values()) or 1.0
    rush_sum = sum(r for _, r in adjusted.values()) or 1.0
    pass_scale = LEAGUE_PASS_YARDS_POOL / pass_sum
    rush_scale = LEAGUE_RUSH_YARDS_POOL / rush_sum
    out: Dict[str, TeamSeasonBudget] = {}
    for team, (pass_y, rush_y) in adjusted.items():
        py = pass_y * pass_scale
        ry = rush_y * rush_scale
        out[team] = TeamSeasonBudget(
            team=team, pass_yards=py, rush_yards=ry, rec_yards=py * 0.92
        )
    return out


def _scale_field(
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


def allocate_season_totals_into_team_budgets(
    rows: List[Dict[str, Any]],
    budgets: Mapping[str, TeamSeasonBudget],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    by_team: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        by_team.setdefault(str(row.get("team") or ""), []).append(row)

    audit: Dict[str, Any] = {"teams": {}, "method": "fantasy_team_budget_alloc_v1"}
    for team, team_rows in by_team.items():
        budget = budgets.get(team)
        if budget is None or not team:
            continue
        pass_sum = sum(float(r.get("pass_yards_total") or 0.0) for r in team_rows)
        rush_sum = sum(float(r.get("rush_yards_total") or 0.0) for r in team_rows)
        rec_sum = sum(float(r.get("receiving_yards_total") or 0.0) for r in team_rows)
        scales: Dict[str, float] = {}
        if pass_sum > 1e-6:
            s = budget.pass_yards / pass_sum
            scales["pass_yards_total"] = round(s, 4)
            _scale_field(team_rows, "pass_yards_total", s, companions=("pass_tds_total",))
        if rush_sum > 1e-6:
            s = budget.rush_yards / rush_sum
            scales["rush_yards_total"] = round(s, 4)
            _scale_field(team_rows, "rush_yards_total", s, companions=("rush_tds_total",))
        if rec_sum > 1e-6:
            s = budget.rec_yards / rec_sum
            scales["receiving_yards_total"] = round(s, 4)
            _scale_field(team_rows, "receiving_yards_total", s, companions=("rec_tds_total",))
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
                float(r.get("pass_yards_total") or 0.0)
                + float(r.get("rush_yards_total") or 0.0)
                + float(r.get("receiving_yards_total") or 0.0)
            ),
            str(r.get("player_name") or ""),
        )
    )
    return rows, audit


def apply_team_volume_budgets(
    rows: List[Dict[str, Any]],
    *,
    strengths: Optional[Mapping[str, Mapping[str, float]]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Public entry: derive budgets + allocate player season totals into them."""
    team_pass_raw: Dict[str, float] = {}
    for row in rows:
        team = str(row.get("team") or "")
        if not team:
            continue
        team_pass_raw[team] = team_pass_raw.get(team, 0.0) + float(
            row.get("pass_yards_total") or 0.0
        )
    strength_book = dict(strengths or {}) or synthetic_strengths_from_team_pass_raw(
        team_pass_raw
    )
    # Ensure every team with rows has a strength entry.
    for team in team_pass_raw:
        strength_book.setdefault(
            team,
            {"offense_index": 1.0, "pace_factor": 1.0, "pass_rate_bias": 0.0},
        )
    budgets = compute_team_season_budgets(strength_book)
    rows, alloc_audit = allocate_season_totals_into_team_budgets(rows, budgets)
    alloc_audit["applied"] = True
    alloc_audit["strength_source"] = (
        "provided" if strengths else "synthetic_from_raw_pass_approx"
    )
    alloc_audit["pass_pool"] = round(sum(b.pass_yards for b in budgets.values()), 1)
    alloc_audit["rush_pool"] = round(sum(b.rush_yards for b in budgets.values()), 1)
    return rows, alloc_audit
