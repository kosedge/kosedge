"""Odds API hold — default ON. Lift only with H-1 auth cite + PR rotate-confirm.

H-1 decision sha8 ``89fdd45f``. Flipping NFL_W8_ODDS_API_HOLD / ODDS_API_HOLD
off is not enough. No key is read or logged here.
"""

from __future__ import annotations

import os
from typing import Any, Mapping, Optional

# Default ON. Explicit "0"/"false" alone cannot ungate a live pull.
HOLD_ENV = "NFL_W8_ODDS_API_HOLD"
GLOBAL_HOLD_ENV = "ODDS_API_HOLD"
ENV_H1_AUTH_CITE = "NFL_W8_H1_AUTH_CITE"
ENV_PR_ROTATE_CONFIRM = "NFL_W8_PR_ROTATE_CONFIRM"

# DECISION_RYAN_t4455u_H1_LIVE_CAPTURE_AUTH_v1 sha8
H1_AUTH_CITE = "89fdd45f"

# TODO(S2): Ryan has not ruled NFL_W8_PR_ROTATE_CONFIRM vs KEEP existing key.
# Decision a9ae5ae6 KEEP supersedes rotate-first; VERIFY PASS e64e73ac stands.
# Setting NFL_W8_PR_ROTATE_CONFIRM asserts a rotation that did not happen
# (semantic falsehood). Paper reinterpret as key-verify e64e73ac, OR rename
# this flag — Ryan/CoS ruling required. Do NOT change this lift policy here.


class OddsApiHoldError(RuntimeError):
    """Raised when any Odds API network path is attempted under hold."""


def _source(env: Optional[Mapping[str, str]] = None) -> Mapping[str, str]:
    return env if env is not None else os.environ


def _truthy(raw: str) -> bool:
    return str(raw or "").strip().lower() in {"1", "true", "yes", "y", "on", "640"}


def hold_lift_state(env: Optional[Mapping[str, str]] = None) -> dict[str, Any]:
    source = _source(env)
    cite = str(source.get(ENV_H1_AUTH_CITE) or "").strip().lower()
    rotate = str(source.get(ENV_PR_ROTATE_CONFIRM) or "").strip()
    cite_ok = cite == H1_AUTH_CITE
    rotate_ok = _truthy(rotate)
    return {
        "cite": cite,
        "cite_ok": cite_ok,
        "rotate_present": bool(rotate),
        "rotate_ok": rotate_ok,
        "authorized": cite_ok and rotate_ok,
        "h1_auth_cite_required": H1_AUTH_CITE,
    }


def odds_api_hold_is_on(env: Optional[Mapping[str, str]] = None) -> bool:
    """Default ON. Lift only when cite 89fdd45f AND PR rotate-confirm are set.

    TODO(S2): rotate-confirm vs KEEP (a9ae5ae6) is pending Ryan. This function
    is unchanged. Single-invocation lift is process-scoped env only — never a
    CLI flag and never a Railway-global write.
    """
    source = _source(env)
    _ = source.get(HOLD_ENV)
    _ = source.get(GLOBAL_HOLD_ENV)
    return not bool(hold_lift_state(source)["authorized"])


def assert_odds_api_hold(env: Optional[Mapping[str, str]] = None) -> None:
    if odds_api_hold_is_on(env):
        state = hold_lift_state(env)
        raise OddsApiHoldError(
            "H-1a/H-1c Odds API hold in force. "
            "Lift requires NFL_W8_H1_AUTH_CITE=89fdd45f and "
            "NFL_W8_PR_ROTATE_CONFIRM (PR rotate-confirm flag). "
            f"cite_ok={state['cite_ok']} rotate_ok={state['rotate_ok']}. "
            "nfl_w8_capture will not call The Odds API or log ODDS_API_KEY."
        )


def refuse_odds_fetch(
    *,
    endpoint: str = "sports/americanfootball_nfl/odds",
    params: Optional[Mapping[str, Any]] = None,
    env: Optional[Mapping[str, str]] = None,
) -> None:
    """Fail-closed default fetch path. Raises until auth+rotate confirm."""
    del endpoint, params
    assert_odds_api_hold(env)
