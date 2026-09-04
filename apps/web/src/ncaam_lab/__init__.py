"""NCAAM Fair Lab engine (research only) — Contract v1 / Phase E Lab Protocol.

Does NOT write Edge Board assemble / kei_lines product JSON.
KenPom is a feed, never SoT. Schedule joins use Schedule SoT D only.
"""

from .protocol import PROTOCOL_VERSION, CUT_WINDOWS, ContinuityState
from .materialize import materialize_lab_fair

__all__ = [
    "PROTOCOL_VERSION",
    "CUT_WINDOWS",
    "ContinuityState",
    "materialize_lab_fair",
]
