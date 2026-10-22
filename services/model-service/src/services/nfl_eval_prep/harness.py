"""P-7 rebuild harness design. Plan only unless a local synthetic tree is passed.

Does not execute historical evaluation, does not touch evaluation seasons,
and does not read W4–W6 plumbing evidence.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional, Sequence

from src.services.nfl_eval_prep.leaks import leak_fix_diff
from src.services.nfl_eval_prep.splits import (
    DIAGNOSTIC_SEASONS_DEFAULT,
    ExpandingWindowFold,
    build_expanding_window_folds,
)


FROZEN_CRITERIA = {
    "predictive": ("4f832c91", "132ee26c"),
    "protocol": "6a3aa3d9",
    "not_criteria": "c57032db",
    "c57032db_role": "G2 feature-parity (14 fields, 0.005-type tolerances, coverage >= 90%)",
}

HARVEST_BLOCKED = {
    "eval_seasons": (2024, 2025),
    "plumbing_weeks_2026": (4, 5, 6),
    "reason": "78f5ee7e contamination / C-5 plumbing-only",
}


@dataclass(frozen=True)
class RebuildPlan:
    criteria: dict[str, Any]
    diagnostic_seasons: tuple[int, ...]
    folds: tuple[ExpandingWindowFold, ...]
    leak_diff: dict[str, Any]
    blocked: dict[str, Any]
    runner: str
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "criteria": self.criteria,
            "diagnostic_seasons": list(self.diagnostic_seasons),
            "folds": [f.to_dict() for f in self.folds],
            "leak_diff": self.leak_diff,
            "blocked": self.blocked,
            "runner": self.runner,
            "notes": list(self.notes),
            "will_execute_eval": False,
        }


def build_rebuild_plan(
    seasons: Optional[Sequence[int]] = None,
    *,
    min_train_seasons: int = 1,
) -> RebuildPlan:
    universe = tuple(seasons) if seasons is not None else DIAGNOSTIC_SEASONS_DEFAULT
    folds = tuple(
        build_expanding_window_folds(universe, min_train_seasons=min_train_seasons)
    )
    return RebuildPlan(
        criteria=dict(FROZEN_CRITERIA),
        diagnostic_seasons=tuple(int(s) for s in universe),
        folds=folds,
        leak_diff=leak_fix_diff(),
        blocked=dict(HARVEST_BLOCKED),
        runner="src.services.nfl_eval_prep.runner_v2.run_local_rebuild",
        notes=(
            "G3 diagnostic only after LC-1..LC-3 and a Ryan P-1 approval.",
            "G4 sealed 2026 W8+ is the only clean evidence; not built here.",
            "Closing lines are comparison labels, never rebuild features.",
            "n=2998 is UNSUPPORTED until R-6 is re-earned.",
        ),
    )
