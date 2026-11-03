"""Settlement profile gate. Unknown profile cannot mint settled values. CERT=0."""

from __future__ import annotations

from typing import Any, Mapping, Optional

from src.services.nfl_joint_contract_v1.constants import KNOWN_SETTLEMENT_PROFILE
from src.services.nfl_joint_contract_v1.refuse import JointContractRefuse, RefuseClass

_UNKNOWN = frozenset({"", "UNKNOWN", "unknown", "NONE", "none", "UNSET"})


def require_known_settlement(profile: Any) -> str:
    """Unknown / missing profile refuses settled p / fair odds / EV / actionable."""
    if profile is None or (isinstance(profile, str) and profile.strip() in _UNKNOWN):
        raise JointContractRefuse(
            "unknown settlement profile — refuse settled_p / fair_odds / EV / actionable",
            refuse_class=RefuseClass.SETTLEMENT,
            detail={
                "settled_p": None,
                "fair_odds": None,
                "ev": None,
                "actionable": False,
                "minted": False,
            },
        )
    if type(profile) is not str:
        raise JointContractRefuse(
            f"settlement profile must be str (got {type(profile).__name__})",
            refuse_class=RefuseClass.TYPE,
        )
    if profile != KNOWN_SETTLEMENT_PROFILE:
        raise JointContractRefuse(
            f"settlement profile {profile!r} is not {KNOWN_SETTLEMENT_PROFILE} — "
            "refuse settled_p / fair_odds / EV / actionable",
            refuse_class=RefuseClass.SETTLEMENT,
            detail={
                "settled_p": None,
                "fair_odds": None,
                "ev": None,
                "actionable": False,
                "minted": False,
            },
        )
    return profile


def identity_settlement(partitions: Mapping[str, Any], *, profile: str) -> dict[str, Any]:
    """Known profile only: settled_p is the literal partition mass. No odds/EV."""
    require_known_settlement(profile)
    ml = partitions["ml"]
    spread = partitions["spread"]
    total = partitions["total"]
    return {
        "settlement_profile": profile,
        "settled_p": {
            "ml": {
                "home_win": ml["home_win"],
                "away_win": ml["away_win"],
                "tie": ml["tie"],
            },
            "spread": {
                "cover": spread["cover"],
                "push": spread["push"],
                "loss": spread["loss"],
            },
            "total": {
                "over": total["over"],
                "push": total["push"],
                "under": total["under"],
            },
        },
        "fair_odds": None,
        "ev": None,
        "actionable": False,
        "eligibility": "UNQUALIFIED",
        "minted_odds": False,
        "minted_ev": False,
    }
