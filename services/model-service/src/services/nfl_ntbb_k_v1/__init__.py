"""NTBB-K V1 SYNTHETIC kernel. CERT=0. RESEARCH_ONLY.

Isolated from owned-market PARTIAL. No fit, forecast, outcomes, or ATS/ROI.
"""

from src.services.nfl_ntbb_k_v1.constants import PACKAGE, PROFILE
from src.services.nfl_ntbb_k_v1.law import log_joint_pmf
from src.services.nfl_ntbb_k_v1.produce import produce_kernel
from src.services.nfl_ntbb_k_v1.refuse import NtbbKRefuse

__all__ = [
    "PACKAGE",
    "PROFILE",
    "NtbbKRefuse",
    "log_joint_pmf",
    "produce_kernel",
]
