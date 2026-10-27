"""Week slate runner — emit only when current inputs audit PASSes.

t4559u: if completeness fails, stop. Do not invent numbers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from src.services.nfl_model_forecast_emit.completeness import (
    assert_week_inputs_complete,
    audit_week_inputs,
)
from src.services.nfl_model_forecast_emit.emit import ForecastIncompleteError


def run_week_slate(
    *,
    season: int = 2026,
    week: int = 8,
    dest_dir: Optional[Path] = None,
    now_utc: Any = None,
    n_replicates: Optional[int] = None,
) -> Dict[str, Any]:
    """Run full-engine week slate or fail-closed with the completeness report.

    Engine projection is intentionally not invoked unless the current-input
    audit is clean. dest_dir is reserved for later emit writes (not seal dests).
    """
    del dest_dir, n_replicates  # unused unless audit passes
    report = audit_week_inputs(season=season, week=week, now_utc=now_utc)
    if not report["ok"]:
        raise ForecastIncompleteError(
            "t4559u slate blocked: "
            + ", ".join(report["failing_components"]),
            gap="G8",
            reason="slate_inputs_incomplete",
        )
    # Reached only when current depth + injury + in-season EPA exist.
    # Not implemented here because the packaged VM inputs do not pass.
    raise ForecastIncompleteError(
        "slate projection path is reserved until current inputs exist",
        gap="G8",
        reason="slate_projection_not_armed",
    )


def audit_or_raise(**kwargs: Any) -> Dict[str, Any]:
    return assert_week_inputs_complete(**kwargs)
