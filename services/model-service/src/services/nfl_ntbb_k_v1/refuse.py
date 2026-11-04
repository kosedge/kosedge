"""Fail-closed refusals. CERT=0."""


class NtbbKRefuse(ValueError):
    """NTBB-K SYNTHETIC kernel refusal. Not a production credential."""
