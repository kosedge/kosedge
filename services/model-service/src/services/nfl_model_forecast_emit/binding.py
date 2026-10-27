"""Forecast ↔ game_id ↔ seal bind hooks. CERT_CANDIDATE=0. No seal writes."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from src.services.nfl_model_forecast_emit.emit import ForecastIncompleteError, sha256_hex
from src.services.nfl_model_forecast_emit.schema import (
    CERT_CANDIDATE,
    PR_641_TIP,
    SEAL_BIND_HOOK,
    SEAL_BINDING_STATUS_UNBOUND,
)


def bind_forecast_to_seal_hook(
    forecast: Mapping[str, Any],
    *,
    seal_game_id: str,
    seal_sha256: Optional[str] = None,
    seal_relpath: Optional[str] = None,
) -> Dict[str, Any]:
    """Return a CERT=0 binding record. Does not write seal dests or close."""
    game_id = str(forecast.get("game_id") or "").strip().upper()
    want = str(seal_game_id or "").strip().upper()
    if not game_id or not want:
        raise ForecastIncompleteError(
            "bind hook requires forecast.game_id and seal_game_id",
            gap="G1",
            reason="bind_game_id_missing",
        )
    if game_id != want:
        raise ForecastIncompleteError(
            f"bind game_id mismatch forecast={game_id} seal={want}",
            gap="G1",
            reason="bind_game_id_mismatch",
        )
    if forecast.get("cert_candidate") != CERT_CANDIDATE:
        raise ForecastIncompleteError(
            "bind refuses cert_candidate != 0",
            gap="G5",
            reason="bind_cert_not_zero",
        )
    record_sha = str(forecast.get("record_sha256") or "").strip().lower()
    if not record_sha:
        record_sha = sha256_hex(
            __import__("json").dumps(dict(forecast), sort_keys=True, separators=(",", ":")).encode()
        )
    return {
        "cert_candidate": CERT_CANDIDATE,
        "status": SEAL_BINDING_STATUS_UNBOUND,
        "hook": SEAL_BIND_HOOK,
        "game_id": game_id,
        "forecast_ts_utc": forecast.get("forecast_ts_utc"),
        "record_sha256": record_sha,
        "seal_sha256": seal_sha256,
        "seal_relpath": None if seal_relpath else None,
        "untouched_pr_641_tip": PR_641_TIP,
        "note": (
            "Hook only. Does not write close, seals/, or #641 dests. "
            "F2 PHI@WAS capture remains waiting."
        ),
    }
