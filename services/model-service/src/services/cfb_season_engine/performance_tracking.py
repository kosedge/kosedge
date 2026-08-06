"""CFB season-engine performance tracking — thin wrapper over unified proof_layer.

Preserves existing import paths and CFB-specific env vars while storing records
in the shared JSONL lake (with ``sport=cfb``) unless ``CFB_PROJECTION_LOG_DIR``
is set for legacy isolation.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from src.services.cfb_season_engine import priors as P
from src.services.proof_layer.adapters import payload_from_cfb_project_game
from src.services.proof_layer.core import (
    AUTO_LOG_ENV as PROOF_AUTO_LOG_ENV,
    BACKEND as PROOF_BACKEND,
    JSONL_NAME,
    ProjectionLog,
    auto_log_enabled as _proof_auto_log_enabled,
    compute_spread_clv,
    compute_total_clv,
    documentation as _proof_documentation,
    game_key,
    get_projection,
    grade_projection,
    list_projections as _list_projections,
    log_projection as _log_projection,
    maybe_auto_log_projection as _maybe_auto_log,
    performance_summary as _performance_summary,
    record_close as _record_close,
    record_result as _record_result,
)
from src.services.proof_layer.core import LAKE_DIR as UNIFIED_LAKE_DIR

# Legacy env names (CFB-specific overrides).
LAKE_DIR = Path(os.getenv("CFB_PROJECTION_LOG_DIR") or UNIFIED_LAKE_DIR)
BACKEND = (os.getenv("CFB_PROJECTION_LOG_BACKEND") or PROOF_BACKEND or "auto").strip().lower()
AUTO_LOG_ENV = "CFB_AUTO_LOG_PROJECTIONS"


def _cfb_lake(lake_dir: Optional[Path] = None) -> Optional[Path]:
    if lake_dir is not None:
        return lake_dir
    if os.getenv("CFB_PROJECTION_LOG_DIR"):
        return Path(os.getenv("CFB_PROJECTION_LOG_DIR"))
    return None


def log_projection(
    payload: Mapping[str, Any],
    *,
    lake_dir: Optional[Path] = None,
    projection_id: Optional[str] = None,
) -> ProjectionLog:
    normalized = payload_from_cfb_project_game(payload)
    return _log_projection(
        normalized,
        sport="cfb",
        lake_dir=_cfb_lake(lake_dir),
        projection_id=projection_id,
    )


def record_close(
    proj_id: str,
    *,
    close_spread_home: Optional[float] = None,
    close_total: Optional[float] = None,
    source: str = "manual",
    lake_dir: Optional[Path] = None,
) -> Optional[ProjectionLog]:
    return _record_close(
        proj_id,
        close_spread_home=close_spread_home,
        close_total=close_total,
        source=source,
        lake_dir=_cfb_lake(lake_dir),
    )


def record_result(
    proj_id: str,
    *,
    home_score: int,
    away_score: int,
    source: str = "manual",
    lake_dir: Optional[Path] = None,
    apply_inseason: bool = False,
) -> Optional[ProjectionLog]:
    return _record_result(
        proj_id,
        home_score=home_score,
        away_score=away_score,
        source=source,
        lake_dir=_cfb_lake(lake_dir),
        apply_inseason=apply_inseason,
    )


def list_projections(
    *,
    limit: int = 50,
    engine_version: Optional[str] = None,
    lake_dir: Optional[Path] = None,
) -> List[ProjectionLog]:
    return _list_projections(
        sport="cfb",
        limit=limit,
        engine_version=engine_version,
        lake_dir=_cfb_lake(lake_dir),
    )


def performance_summary(
    *,
    limit: int = 200,
    engine_version: Optional[str] = None,
    lake_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    payload = _performance_summary(
        sport="cfb",
        limit=limit,
        engine_version=engine_version,
        lake_dir=_cfb_lake(lake_dir),
    )
    payload["current_engine_version"] = P.ENGINE_VERSION
    payload["lake_dir"] = str(_cfb_lake(lake_dir) or UNIFIED_LAKE_DIR)
    payload["backend"] = BACKEND
    return payload


def auto_log_enabled() -> bool:
    return _proof_auto_log_enabled(sport="cfb")


def maybe_auto_log_projection(payload: Mapping[str, Any]) -> None:
    normalized = payload_from_cfb_project_game(payload)
    _maybe_auto_log(normalized, sport="cfb")


def documentation() -> Dict[str, Any]:
    doc = _proof_documentation()
    doc["module"] = "performance_tracking"
    doc["engine_version"] = P.ENGINE_VERSION
    doc["lake_dir"] = str(LAKE_DIR)
    doc["backend"] = BACKEND
    doc["db_opt_in_env"] = "PROOF_LAKE_BACKEND=postgres (auto when DATABASE_URL set)"
    doc["auto_log_env"] = AUTO_LOG_ENV
    doc["unified"] = {
        "module": "src.services.proof_layer",
        "endpoints": "/proof/projections",
    }
    return doc


__all__ = [
    "AUTO_LOG_ENV",
    "BACKEND",
    "JSONL_NAME",
    "LAKE_DIR",
    "ProjectionLog",
    "auto_log_enabled",
    "compute_spread_clv",
    "compute_total_clv",
    "documentation",
    "game_key",
    "get_projection",
    "grade_projection",
    "list_projections",
    "log_projection",
    "maybe_auto_log_projection",
    "performance_summary",
    "record_close",
    "record_result",
]
