"""Fail-closed contract for required CFB team features.

Missing official-FBS identity / power / efficiency must sit or raise.
Never invent Independent affiliation or league-average 1.0 power.
"""

from __future__ import annotations

import os
from typing import Any, Optional


class MissingRequiredTeamFeature(ValueError):
    """Official FBS row is missing a required feature — sit / hard error."""


# Public CFB Edge Board kill switch. Must stay false until Ryan/CoS unsats
# public reactivation (out of scope for the structural restore).
# Env may only keep it off; it cannot silently turn the public board on.
_ENV_PUBLIC = os.environ.get("CFB_EDGE_BOARD_PUBLIC_ENABLED", "").strip().lower()
CFB_EDGE_BOARD_PUBLIC_ENABLED = False if _ENV_PUBLIC in {"", "0", "false", "off", "no"} else False


def env_public_board_enabled() -> bool:
    """Always false until an explicit product unsat. Env cannot flip this on."""
    return bool(CFB_EDGE_BOARD_PUBLIC_ENABLED)


def require_finite_power_index(value: Any, *, field: str, team: str) -> float:
    """Reject null / blank power. Do not coerce to 1.0."""
    if value is None or value == "":
        raise MissingRequiredTeamFeature(
            f"Official FBS {team} missing {field} — sit, do not default 1.0"
        )
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise MissingRequiredTeamFeature(
            f"Official FBS {team} non-numeric {field}={value!r} — sit, do not default 1.0"
        ) from exc
    if out != out:  # NaN
        raise MissingRequiredTeamFeature(
            f"Official FBS {team} NaN {field} — sit, do not default 1.0"
        )
    return out


def reject_silent_default_power(
    offense_index: Optional[float],
    defense_index: Optional[float],
    *,
    team: str,
    invented: bool,
) -> None:
    """Hard-error the null→1.0 hydrate path."""
    if invented:
        raise MissingRequiredTeamFeature(
            f"Official FBS {team} silent default 1.0 power is forbidden "
            f"(off={offense_index!r} def={defense_index!r})"
        )
