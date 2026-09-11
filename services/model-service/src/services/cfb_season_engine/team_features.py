"""Fail-closed contract for required CFB team features.

Missing official-FBS identity / power / efficiency must hard-fail rebuild/pack
(raise / non-zero exit). Never invent Independent affiliation or
league-average 1.0 power.
"""

from __future__ import annotations

import os
from typing import Any, Iterable, Optional


class MissingRequiredTeamFeature(ValueError):
    """Official FBS row is missing a required feature — hard-fail pack/rebuild."""


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
            f"Official FBS {team} missing {field} — hard-fail, do not default 1.0"
        )
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise MissingRequiredTeamFeature(
            f"Official FBS {team} non-numeric {field}={value!r} — "
            "hard-fail, do not default 1.0"
        ) from exc
    if out != out:  # NaN
        raise MissingRequiredTeamFeature(
            f"Official FBS {team} NaN {field} — hard-fail, do not default 1.0"
        )
    return out


def require_finite_power_for_codes(
    teams: Any,
    required: Iterable[str],
    *,
    context: str = "rebuild/pack",
) -> None:
    """Hard-fail when a required official-FBS code lacks real power.

    ``teams`` may be an EngineUniverse, a ``teams`` mapping, or anything with
    ``.teams`` / ``.get``. Does not invent 1.0.
    """
    if hasattr(teams, "teams"):
        lookup = teams.teams
    else:
        lookup = teams
    missing: list[str] = []
    for code in sorted({str(c or "").upper() for c in required if c}):
        st = None
        if hasattr(lookup, "get"):
            st = lookup.get(code)
        if st is None:
            missing.append(f"{code}:absent")
            continue
        off = getattr(st, "offense_index", None)
        deff = getattr(st, "defense_index", None)
        if isinstance(st, dict):
            off = st.get("offense_index")
            deff = st.get("defense_index")
        try:
            require_finite_power_index(off, field="offense_index", team=code)
            require_finite_power_index(deff, field="defense_index", team=code)
        except MissingRequiredTeamFeature:
            missing.append(f"{code}:null_power")
    if missing:
        raise MissingRequiredTeamFeature(
            f"Required FBS slate teams missing features during {context} "
            f"(do not hydrate 1.0): {missing}"
        )


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
