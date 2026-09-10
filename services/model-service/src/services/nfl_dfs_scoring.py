"""NFL DFS site scoring — a pricing layer on player-production truth.

DK Classic and FD Classic are explicit contracts. This is NOT Half-PPR and
does not invent Ceiling = projection × 1.35.

INT / fumble / 2-pt are omitted until the production spine carries them.
K/DST are out of V1.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from src.services.nfl_dfs_identity import canonical_dfs_site
from src.services.nfl_player_production import PlayerGameProduction

SCORING_VERSION = "nfl-dfs-scoring-v1"
DK_CLASSIC = "dk_classic"
FD_CLASSIC = "fd_classic"

# Official classic skill-position scoring (2026 season contracts).
DK_PASS_YD = 0.04
DK_PASS_TD = 4.0
DK_RUSH_YD = 0.10
DK_RUSH_TD = 6.0
DK_REC_YD = 0.10
DK_REC = 1.0
DK_REC_TD = 6.0
DK_BONUS_PASS_300 = 3.0
DK_BONUS_RUSH_100 = 3.0
DK_BONUS_REC_100 = 3.0

FD_PASS_YD = 0.04
FD_PASS_TD = 4.0
FD_RUSH_YD = 0.10
FD_RUSH_TD = 6.0
FD_REC_YD = 0.10
FD_REC = 0.5
FD_REC_TD = 6.0


@dataclass(frozen=True)
class DfsScoredPoints:
    scoring_system: str
    projection: float
    median: Optional[float]
    floor: Optional[float]
    ceiling: Optional[float]
    distribution_available: bool
    bonus_expectation: float
    unavailable_reason: Optional[str] = None


def scoring_system_for_site(site: str) -> str:
    canon = canonical_dfs_site(site)
    if canon == "FD":
        return FD_CLASSIC
    return DK_CLASSIC


def _f(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return float(default)
    try:
        out = float(value)
    except (TypeError, ValueError):
        return float(default)
    if out != out:
        return float(default)
    return out


def _normal_sf(threshold: float, mean: float, std: float) -> float:
    """P(X >= threshold) under a Normal(mean, std). No invented default std."""
    if std <= 0:
        return 1.0 if mean >= threshold else 0.0
    z = (threshold - mean) / std
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def score_counting_line(
    *,
    scoring_system: str,
    pass_yards: float = 0.0,
    pass_tds: float = 0.0,
    rush_yards: float = 0.0,
    rush_tds: float = 0.0,
    receiving_yards: float = 0.0,
    receptions: float = 0.0,
    rec_tds: float = 0.0,
    apply_threshold_bonuses: bool = True,
) -> float:
    """Score one football outcome under an explicit site contract."""
    system = scoring_system.strip().lower()
    if system == FD_CLASSIC:
        pts = (
            pass_yards * FD_PASS_YD
            + pass_tds * FD_PASS_TD
            + rush_yards * FD_RUSH_YD
            + rush_tds * FD_RUSH_TD
            + receiving_yards * FD_REC_YD
            + receptions * FD_REC
            + rec_tds * FD_REC_TD
        )
        return round(pts, 4)
    if system != DK_CLASSIC:
        raise ValueError(f"unsupported DFS scoring system: {scoring_system}")
    pts = (
        pass_yards * DK_PASS_YD
        + pass_tds * DK_PASS_TD
        + rush_yards * DK_RUSH_YD
        + rush_tds * DK_RUSH_TD
        + receiving_yards * DK_REC_YD
        + receptions * DK_REC
        + rec_tds * DK_REC_TD
    )
    if apply_threshold_bonuses:
        if pass_yards >= 300:
            pts += DK_BONUS_PASS_300
        if rush_yards >= 100:
            pts += DK_BONUS_RUSH_100
        if receiving_yards >= 100:
            pts += DK_BONUS_REC_100
    return round(pts, 4)


def expected_dk_bonuses(prod: PlayerGameProduction, *, stds_valid: bool) -> float:
    """Expected DK yardage bonuses from the production distribution.

    If stds are not certified as source-backed, only apply a bonus when the
    mean itself clears the threshold — never invent a 1.35× fantasy ceiling.
    """
    bonus = 0.0
    if stds_valid:
        bonus += DK_BONUS_PASS_300 * _normal_sf(300.0, prod.pass_yards, prod.pass_yards_std)
        bonus += DK_BONUS_RUSH_100 * _normal_sf(100.0, prod.rush_yards, prod.rush_yards_std)
        bonus += DK_BONUS_REC_100 * _normal_sf(100.0, prod.receiving_yards, prod.receiving_yards_std)
    else:
        if prod.pass_yards >= 300:
            bonus += DK_BONUS_PASS_300
        if prod.rush_yards >= 100:
            bonus += DK_BONUS_RUSH_100
        if prod.receiving_yards >= 100:
            bonus += DK_BONUS_REC_100
    return round(bonus, 4)


def _outcome_has_counting_stats(outcome: Mapping[str, Any] | None) -> bool:
    if not outcome:
        return False
    keys = ("pass_yards", "rush_yards", "receiving_yards", "receptions", "touchdowns")
    return any(key in outcome and outcome.get(key) is not None for key in keys)


def _stds_are_source_backed(row: Mapping[str, Any] | None) -> bool:
    """True only when the baseline actually stored std columns (not omitted)."""
    if not row:
        return False
    keys = ("pass_yards_std", "rush_yards_std", "receiving_yards_std", "receptions_std")
    present = 0
    for key in keys:
        raw = row.get(key) if isinstance(row, Mapping) else None
        if raw is None or raw == "":
            continue
        try:
            val = float(raw)
        except (TypeError, ValueError):
            continue
        if val == val and val > 0:
            present += 1
    return present >= 2


def _scale_tds(mean_td: float, outcome_td: Optional[float], mean_total_td: float) -> float:
    if outcome_td is None or mean_total_td <= 0:
        return mean_td
    return max(0.0, mean_td * (float(outcome_td) / mean_total_td))


def score_production_for_site(
    prod: PlayerGameProduction,
    *,
    site: str,
    baseline_row: Mapping[str, Any] | None = None,
) -> DfsScoredPoints:
    """Convert spine production into site fantasy points.

    Floor / median / ceiling come from the spine's outcome distribution.
    If that distribution is missing, projection is emitted and bands stay
    unavailable — never proj × 1.35.
    """
    system = scoring_system_for_site(site)
    stds_valid = _stds_are_source_backed(baseline_row)
    bonus = expected_dk_bonuses(prod, stds_valid=stds_valid) if system == DK_CLASSIC else 0.0
    projection = score_counting_line(
        scoring_system=system,
        pass_yards=prod.pass_yards,
        pass_tds=prod.pass_tds,
        rush_yards=prod.rush_yards,
        rush_tds=prod.rush_tds,
        receiving_yards=prod.receiving_yards,
        receptions=prod.receptions,
        rec_tds=prod.rec_tds,
        apply_threshold_bonuses=False,
    ) + bonus

    floor_outcome = None
    median_outcome = None
    ceiling_outcome = None
    if baseline_row:
        floor_outcome = baseline_row.get("floor_outcome") if isinstance(baseline_row.get("floor_outcome"), Mapping) else None
        median_outcome = baseline_row.get("median_outcome") if isinstance(baseline_row.get("median_outcome"), Mapping) else None
        ceiling_outcome = baseline_row.get("ceiling_outcome") if isinstance(baseline_row.get("ceiling_outcome"), Mapping) else None

    has_dist = _outcome_has_counting_stats(floor_outcome) and _outcome_has_counting_stats(ceiling_outcome)
    if not has_dist:
        return DfsScoredPoints(
            scoring_system=system,
            projection=round(projection, 4),
            median=None,
            floor=None,
            ceiling=None,
            distribution_available=False,
            bonus_expectation=bonus,
            unavailable_reason="distribution_unavailable",
        )

    total_td = prod.pass_tds + prod.rush_tds + prod.rec_tds

    def _score_outcome(outcome: Mapping[str, Any], *, bonuses: bool) -> float:
        floor_td = outcome.get("touchdowns")
        return score_counting_line(
            scoring_system=system,
            pass_yards=_f(outcome.get("pass_yards"), prod.pass_yards),
            pass_tds=_scale_tds(prod.pass_tds, None if floor_td is None else _f(floor_td), total_td),
            rush_yards=_f(outcome.get("rush_yards"), prod.rush_yards),
            rush_tds=_scale_tds(prod.rush_tds, None if floor_td is None else _f(floor_td), total_td),
            receiving_yards=_f(outcome.get("receiving_yards"), prod.receiving_yards),
            receptions=_f(outcome.get("receptions"), prod.receptions),
            rec_tds=_scale_tds(prod.rec_tds, None if floor_td is None else _f(floor_td), total_td),
            apply_threshold_bonuses=bonuses,
        )

    floor_pts = _score_outcome(floor_outcome or {}, bonuses=system == DK_CLASSIC)
    ceiling_pts = _score_outcome(ceiling_outcome or {}, bonuses=system == DK_CLASSIC)
    if _outcome_has_counting_stats(median_outcome):
        median_pts = _score_outcome(median_outcome or {}, bonuses=False) + bonus
    else:
        median_pts = round(projection, 4)

    return DfsScoredPoints(
        scoring_system=system,
        projection=round(projection, 4),
        median=round(median_pts, 4),
        floor=round(min(floor_pts, median_pts), 4),
        ceiling=round(max(ceiling_pts, median_pts), 4),
        distribution_available=True,
        bonus_expectation=bonus,
    )
