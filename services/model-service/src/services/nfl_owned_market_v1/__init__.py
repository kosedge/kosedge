"""Isolated OWNED_MARKET_TRACE_V1 + SYNTHETIC_MARKET_ECONOMIC_EVENTS_V1.

Worker B narrow patch. CERT=0. A registers the profiles.
OWNED_READINESS and FICTIONAL_ECONOMIC stay separate.
"""

from src.services.nfl_owned_market_v1.constants import (
    PACKAGE,
    PROFILE_OWNED_MARKET_TRACE,
    PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
    ROLE_FICTIONAL_ECONOMIC,
    ROLE_OWNED_READINESS,
)
from src.services.nfl_owned_market_v1.produce import (
    build_events_document,
    build_trace_document,
    produce_artifacts,
)
from src.services.nfl_owned_market_v1.profiles import handoff_interface
from src.services.nfl_owned_market_v1.refuse import OwnedMarketRefuse
from src.services.nfl_owned_market_v1.validate import (
    validate_join,
    validate_owned_market_trace,
    validate_synthetic_market_economic_events,
)

__all__ = [
    "PACKAGE",
    "PROFILE_OWNED_MARKET_TRACE",
    "PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS",
    "ROLE_FICTIONAL_ECONOMIC",
    "ROLE_OWNED_READINESS",
    "OwnedMarketRefuse",
    "build_events_document",
    "build_trace_document",
    "handoff_interface",
    "produce_artifacts",
    "validate_join",
    "validate_owned_market_trace",
    "validate_synthetic_market_economic_events",
]
