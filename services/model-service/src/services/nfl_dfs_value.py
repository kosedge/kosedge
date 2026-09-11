"""NFL DFS value primitives.

points_per_$1K is a transparent number, not the KosEdge DFS rating.
Salary-relative positional value compares a player to same-position
roster-cost peers on this slate only.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Iterable, Optional, Sequence


@dataclass(frozen=True)
class DfsValue:
    points_per_1k: Optional[float]
    salary_rel_delta: Optional[float]
    salary_rel_per_1k: Optional[float]
    band_size: int
    band_median_projection: Optional[float]


def points_per_1k(projection: Optional[float], salary: Optional[int]) -> Optional[float]:
    if projection is None or salary is None:
        return None
    if not (salary > 0) or projection != projection:
        return None
    return round(float(projection) / (float(salary) / 1000.0), 4)


def _nearest_salary_peers(
    *,
    salary: int,
    peers: Sequence[tuple[int, float]],
    band_ratio: float = 0.15,
    min_band: int = 3,
    fallback_n: int = 5,
) -> list[tuple[int, float]]:
    if not peers:
        return []
    lo = salary * (1.0 - band_ratio)
    hi = salary * (1.0 + band_ratio)
    band = [p for p in peers if lo <= p[0] <= hi]
    if len(band) >= min_band:
        return list(band)
    ordered = sorted(peers, key=lambda item: abs(item[0] - salary))
    return ordered[: max(fallback_n, min_band)]


def salary_relative_positional_value(
    *,
    projection: Optional[float],
    salary: Optional[int],
    peer_salaries_and_projections: Iterable[tuple[int, float]],
) -> DfsValue:
    """Compare this player's output to players at a similar roster cost.

    `peer_salaries_and_projections` must already be same-position, same-slate,
    certified rows (including self). Fewer than two peers → unavailable.
    """
    p1k = points_per_1k(projection, salary)
    if projection is None or salary is None or salary <= 0:
        return DfsValue(p1k, None, None, 0, None)
    peers = [(int(s), float(y)) for s, y in peer_salaries_and_projections if s and s > 0]
    if len(peers) < 2:
        return DfsValue(p1k, None, None, len(peers), None)
    band = _nearest_salary_peers(salary=int(salary), peers=peers)
    if len(band) < 2:
        return DfsValue(p1k, None, None, len(band), None)
    band_median = float(median(y for _s, y in band))
    delta = float(projection) - band_median
    return DfsValue(
        points_per_1k=p1k,
        salary_rel_delta=round(delta, 4),
        salary_rel_per_1k=round(delta / (float(salary) / 1000.0), 4),
        band_size=len(band),
        band_median_projection=round(band_median, 4),
    )
