"""t5289u R7_CORRECTNESS_V1 — opt-in synthetic IF/Q2 + shared gate. CERT=0."""

from src.services.nfl_r7_correctness_v1.produce import produce_r7_point_margin
from src.services.nfl_r7_correctness_v1.run import run_r7_integrated

__all__ = ["produce_r7_point_margin", "run_r7_integrated"]
