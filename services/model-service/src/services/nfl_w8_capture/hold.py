"""Odds API hold — fail closed. H-1a / H-1c stay blocking.

This draft never lifts the hold and never issues a network call. Env names
only; no keys are read or logged.
"""

from __future__ import annotations

import os
from typing import Any, Mapping, Optional

# Default ON. Explicit "0"/"false" is still treated as ON in this draft so a
# stray env cannot ungate a live pull from this module.
HOLD_ENV = "NFL_W8_ODDS_API_HOLD"
GLOBAL_HOLD_ENV = "ODDS_API_HOLD"


class OddsApiHoldError(RuntimeError):
    """Raised when any Odds API network path is attempted under hold."""


def odds_api_hold_is_on(env: Optional[Mapping[str, str]] = None) -> bool:
    source = env if env is not None else os.environ
    # Draft ownership: hold stays on regardless of env. Reading the names
    # documents the contract; the value cannot lift the hold from this package.
    _ = source.get(HOLD_ENV)
    _ = source.get(GLOBAL_HOLD_ENV)
    return True


def assert_odds_api_hold(env: Optional[Mapping[str, str]] = None) -> None:
    if odds_api_hold_is_on(env):
        raise OddsApiHoldError(
            "H-1a/H-1c Odds API hold in force. "
            "nfl_w8_capture will not call The Odds API, read ODDS_API_KEY, "
            "or lift the hold. Live pull stays blocked."
        )


def refuse_odds_fetch(
    *,
    endpoint: str = "sports/americanfootball_nfl/odds",
    params: Optional[Mapping[str, Any]] = None,
    env: Optional[Mapping[str, str]] = None,
) -> None:
    """The only fetch entrypoint in this package. Always raises."""
    del endpoint, params
    assert_odds_api_hold(env)
