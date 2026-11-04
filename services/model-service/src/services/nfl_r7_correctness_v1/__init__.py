"""t5289u R7_CORRECTNESS_V1 — opt-in synthetic IF/Q2 + shared gate. CERT=0."""

from src.services.nfl_r7_correctness_v1.produce import produce_r7_point_margin

__all__ = ["produce_r7_point_margin", "run_r7_integrated"]


def __getattr__(name: str):
    if name == "run_r7_integrated":
        from src.services.nfl_r7_correctness_v1.run import run_r7_integrated

        return run_r7_integrated
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
