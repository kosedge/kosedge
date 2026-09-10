"""NFL DFS ownership contract.

Ownership stays unavailable until a defensible source/model exists.
Do not fabricate ownership or leverage. This module is the plug-in point
so later ownership does not rewrite player/slate identity.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

OWNERSHIP_CONTRACT_VERSION = "nfl-dfs-ownership-v1"
OWNERSHIP_UNAVAILABLE_REASON = "no_defensible_source"


@dataclass(frozen=True)
class OwnershipProjection:
    """Identity-stable ownership slot. V1 always publishes unavailable."""

    site: str
    season: int
    week: int
    slate_id: str
    player_uid: str
    status: str = "unavailable"
    projected_own: Optional[float] = None
    leverage: Optional[float] = None
    source: Optional[str] = None
    source_version: Optional[str] = None
    model_version: Optional[str] = None
    reason: str = OWNERSHIP_UNAVAILABLE_REASON
    contract_version: str = OWNERSHIP_CONTRACT_VERSION

    def as_public(self) -> Dict[str, Any]:
        payload = asdict(self)
        # Never leak a made-up number. Status is the product.
        if self.status != "projected":
            payload["projected_own"] = None
            payload["leverage"] = None
        return payload


def unavailable_ownership(
    *,
    site: str,
    season: int,
    week: int,
    slate_id: str,
    player_uid: str,
    reason: str = OWNERSHIP_UNAVAILABLE_REASON,
) -> OwnershipProjection:
    return OwnershipProjection(
        site=site,
        season=season,
        week=week,
        slate_id=slate_id,
        player_uid=player_uid,
        reason=reason,
    )


def leverage_from_upside_and_own(
    *,
    upside_probability: Optional[float],
    expected_ownership: Optional[float],
) -> Optional[float]:
    """Reserved production formula.

    Leverage = modeled upside probability relative to expected ownership.
    Exact shipping formula must be validated before this returns a number.
    """
    if upside_probability is None or expected_ownership is None:
        return None
    # Hard lock: V1 must not compute leverage from invented ownership.
    return None
