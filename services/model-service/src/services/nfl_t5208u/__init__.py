"""t5208u R6_CALLER_V1 — research-tree pure caller (SYNTHETIC, POINT_MARGIN, CERT=0)."""

from .caller import call_r6_point_margin
from .pins import CANDIDATE_WEIGHT, CONTRACT_27, C_FORMULA, SCHEMA_ID

__all__ = [
    "CONTRACT_27",
    "CANDIDATE_WEIGHT",
    "C_FORMULA",
    "SCHEMA_ID",
    "call_r6_point_margin",
]
