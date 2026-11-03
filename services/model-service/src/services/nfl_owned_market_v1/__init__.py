"""Isolated OWNED_MARKET_TRACE_V1 + SYNTHETIC_MARKET_ECONOMIC_EVENTS_V1.

Worker B narrow patch. CERT=0. Synthetic only. A registers the profiles.
"""

from src.services.nfl_owned_market_v1.constants import (
    PACKAGE,
    PROFILE_OWNED_MARKET_TRACE,
    PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
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
    "OwnedMarketRefuse",
    "build_events_document",
    "build_trace_document",
    "handoff_interface",
    "produce_artifacts",
    "validate_join",
    "validate_owned_market_trace",
    "validate_synthetic_market_economic_events",
]
