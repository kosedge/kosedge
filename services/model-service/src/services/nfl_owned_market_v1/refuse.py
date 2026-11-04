"""Fail-closed refuse for nfl_owned_market_v1. CERT=0."""


class OwnedMarketRefuse(ValueError):
    """Typed refuse. Callers must not impute or continue."""
