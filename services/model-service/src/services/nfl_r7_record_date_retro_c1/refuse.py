"""Fail-closed refuse for R7_RECORD_DATE_RETRO_C1. CERT=0."""


class RetroRefuse(ValueError):
    """Typed refuse. Callers must not impute, retry, or open real data."""


class RetroHold(RetroRefuse):
    """DATA_HOLD — unknown actual-clock / missing real GO."""
