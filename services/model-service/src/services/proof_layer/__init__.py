"""Unified projection proof layer — log, close, result, grade for NFL + CFB."""

from src.services.proof_layer.adapters import (
    payload_from_cfb_project_game,
    payload_from_nfl_game_boxes,
)
from src.services.proof_layer.core import (
    AUTO_LOG_ENV,
    BACKEND,
    JSONL_NAME,
    LAKE_DIR,
    ProjectionLog,
    auto_log_enabled,
    compute_spread_clv,
    compute_total_clv,
    documentation,
    game_key,
    get_projection,
    grade_projection,
    list_projections,
    log_projection,
    maybe_auto_log_projection,
    performance_summary,
    record_close,
    record_result,
)

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
    "payload_from_cfb_project_game",
    "payload_from_nfl_game_boxes",
    "performance_summary",
    "record_close",
    "record_result",
]
