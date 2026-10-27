"""NFL timestamped model-forecast emit (Alex paper f1fa86e7, CERT=0)."""

from src.services.nfl_model_forecast_emit.binding import bind_forecast_to_seal_hook
from src.services.nfl_model_forecast_emit.completeness import (
    audit_week_inputs,
    assert_week_inputs_complete,
)
from src.services.nfl_model_forecast_emit.emit import (
    ForecastIncompleteError,
    emit_model_forecast,
    write_forecast_artifact,
)
from src.services.nfl_model_forecast_emit.engine_adapter import (
    inputs_from_engine_projection,
)
from src.services.nfl_model_forecast_emit.schema import (
    CERT_CANDIDATE,
    EVAL_RECORD_PAPER_SHA8,
    SCHEMA_VERSION,
)
from src.services.nfl_model_forecast_emit.slate import run_week_slate

__all__ = [
    "CERT_CANDIDATE",
    "EVAL_RECORD_PAPER_SHA8",
    "ForecastIncompleteError",
    "SCHEMA_VERSION",
    "assert_week_inputs_complete",
    "audit_week_inputs",
    "bind_forecast_to_seal_hook",
    "emit_model_forecast",
    "inputs_from_engine_projection",
    "run_week_slate",
    "write_forecast_artifact",
]
