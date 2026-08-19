"""Single weekly player-production spine (Phase 1).

Fantasy weekly and props board must read the same player-game means.
SoT for Phase 1: ``nfl_player_projection_baselines`` (raw), not box MC blend
and not a private props fork.

Frozen prop-cal-v1 may be applied for *edge math only* on the props path.
Do not re-fit intercepts here. Season box sims (D4) and season-engine (D5)
are not weekly SoT until Phase 3.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Mapping, Optional

PRODUCTION_VERSION = "player-production-v3-phase3b"
PRODUCTION_SOURCE = "nfl_player_projection_baselines"
# Surfaces that must share this vector for weekly player numbers.
WEEKLY_SPINE_SURFACES = ("fantasy_weekly", "props_board")

MARKET_TO_FIELD = {
    "pass_yds": "pass_yards",
    "rush_yds": "rush_yards",
    "rec_yds": "receiving_yards",
    "receptions": "receptions",
    "anytime_td": "total_tds",
}


@dataclass(frozen=True)
class PlayerGameProduction:
    """Canonical weekly production means for one player-game."""

    pass_yards: float
    rush_yards: float
    receiving_yards: float
    receptions: float
    pass_tds: float
    rush_tds: float
    rec_tds: float
    total_tds: float
    pass_yards_std: float
    rush_yards_std: float
    receiving_yards_std: float
    receptions_std: float
    source: str = PRODUCTION_SOURCE
    version: str = PRODUCTION_VERSION

    def mean_for_market(self, market_key: str) -> Optional[float]:
        field = MARKET_TO_FIELD.get(str(market_key or ""))
        if not field:
            return None
        return float(getattr(self, field))

    def std_for_market(self, market_key: str) -> float:
        if market_key == "pass_yds":
            return float(self.pass_yards_std)
        if market_key == "rush_yds":
            return float(self.rush_yards_std)
        if market_key == "rec_yds":
            return float(self.receiving_yards_std)
        if market_key == "receptions":
            return float(self.receptions_std)
        if market_key == "anytime_td":
            return 0.25
        return 4.0

    def as_diagnostics(self) -> Dict[str, Any]:
        return {
            "spine_version": self.version,
            "spine_source": self.source,
            "production_pass_yards": self.pass_yards,
            "production_rush_yards": self.rush_yards,
            "production_receiving_yards": self.receiving_yards,
            "production_receptions": self.receptions,
            "production_pass_tds": self.pass_tds,
            "production_rush_tds": self.rush_tds,
            "production_rec_tds": self.rec_tds,
            "production_total_tds": self.total_tds,
        }


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


def production_from_baseline_row(row: Mapping[str, Any] | Any) -> PlayerGameProduction:
    """Phase 1 SoT: raw baseline means (same vector fantasy already scored)."""

    def get(key: str) -> Any:
        if isinstance(row, Mapping):
            try:
                return row[key]
            except KeyError:
                return None
        return getattr(row, key, None)

    pass_tds = _f(get("pass_tds_mean"))
    rush_tds = _f(get("rush_tds_mean"))
    rec_tds = _f(get("rec_tds_mean"))
    total = get("total_tds_mean")
    total_tds = _f(total, pass_tds + rush_tds + rec_tds)
    return PlayerGameProduction(
        pass_yards=_f(get("pass_yards_mean")),
        rush_yards=_f(get("rush_yards_mean")),
        receiving_yards=_f(get("receiving_yards_mean")),
        receptions=_f(get("receptions_mean")),
        pass_tds=pass_tds,
        rush_tds=rush_tds,
        rec_tds=rec_tds,
        total_tds=total_tds,
        pass_yards_std=max(0.65, _f(get("pass_yards_std"), 4.0)),
        rush_yards_std=max(0.65, _f(get("rush_yards_std"), 4.0)),
        receiving_yards_std=max(0.65, _f(get("receiving_yards_std"), 4.0)),
        receptions_std=max(0.65, _f(get("receptions_std"), 1.0)),
    )


def production_means_equal(
    left: PlayerGameProduction,
    right: PlayerGameProduction,
    *,
    tol: float = 1e-6,
) -> bool:
    for field in (
        "pass_yards",
        "rush_yards",
        "receiving_yards",
        "receptions",
        "pass_tds",
        "rush_tds",
        "rec_tds",
        "total_tds",
    ):
        if abs(float(getattr(left, field)) - float(getattr(right, field))) > tol:
            return False
    return left.version == right.version and left.source == right.source


def production_as_dict(prod: PlayerGameProduction) -> Dict[str, Any]:
    return asdict(prod)
