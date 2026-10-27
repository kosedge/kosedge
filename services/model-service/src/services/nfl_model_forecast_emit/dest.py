"""SOP 4a017f22 research_runs landing. Never writes under seals/."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from src.services.nfl_model_forecast_emit.emit import (
    ForecastIncompleteError,
    format_utc,
    write_forecast_artifact,
)
from src.services.nfl_model_forecast_emit.schema import (
    CERT_CANDIDATE,
    DEFAULT_RESEARCH_RUNS_ROOT,
    FILE_MODE_READONLY,
    SOP_4A017F22,
)


def research_runs_root() -> Path:
    raw = (os.environ.get("NFL_FORECAST_RESEARCH_RUNS_ROOT") or "").strip()
    return Path(raw or DEFAULT_RESEARCH_RUNS_ROOT)


def make_run_id(
    *,
    season: int,
    week: int,
    forecast_ts_utc: str,
    code_tip_sha: str,
) -> str:
    compact = str(forecast_ts_utc).replace("-", "").replace(":", "")
    if compact.endswith("Z"):
        pass
    return f"nfl-mfe-{int(season)}-w{int(week):02d}-{compact}-{code_tip_sha[:8]}"


def run_dir_for(run_id: str, *, root: Optional[Path] = None) -> Path:
    dest = (root or research_runs_root()) / run_id
    text = str(dest.resolve()) if dest.exists() else str(dest)
    lowered = text.replace("\\", "/").lower()
    if "/seals/" in lowered or "/seal/" in lowered:
        raise ForecastIncompleteError(
            f"refuse SOP dest that looks like a seal path: {dest}",
            gap="G6",
            reason="seal_dest_refused",
        )
    return dest


def write_readonly_json(path: Path, payload: Dict[str, Any]) -> str:
    wrote = write_forecast_artifact(payload, path)
    os.chmod(path, FILE_MODE_READONLY)
    return wrote["record_sha256"]
