"""S-MKT / S-IND forecast archiver. Lands scaffolds in the evidence bundle.

Does not invent sealed predictions. Prediction fields stay UNSET.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

from src.services.nfl_w8_capture.pin import UNSET, UNSET_SHA
from src.services.nfl_w8_capture.store import FORECASTS_IND, FORECASTS_MKT, BundleStore
from src.services.nfl_w8_capture.streams import (
    STREAM_IND,
    STREAM_MKT,
    check_s_ind_forbidden_inputs,
    scaffold_streams,
)


def archive_forecasts(
    store: BundleStore,
    *,
    game_id: str,
    s_mkt_features: Optional[Mapping[str, Any]] = None,
    s_ind_features: Optional[Mapping[str, Any]] = None,
    actor: str = "nfl_w8_capture",
) -> dict[str, Any]:
    if s_ind_features is not None:
        check_s_ind_forbidden_inputs(s_ind_features)
    bundles = scaffold_streams(
        game_id,
        s_mkt_features=s_mkt_features,
        s_ind_features=s_ind_features,
    )
    written: dict[str, Any] = {}
    mapping = {
        STREAM_MKT: FORECASTS_MKT,
        STREAM_IND: FORECASTS_IND,
    }
    for stream, dest_dir in mapping.items():
        bundle = bundles[stream]
        relpath = (dest_dir / bundle.path).as_posix()
        artifact = {
            "game_id": game_id,
            "stream": stream,
            "sealed": False,
            "seal_ack": "CURSOR_CANNOT_SEAL_ACK",
            "prediction": UNSET,
            "prediction_sha": UNSET_SHA,
            "features": bundle.features,
        }
        written[stream] = store.write_new_file(
            relpath,
            artifact,
            actor=actor,
            note=f"archive:{stream}:{game_id}",
            extra={"stream": stream, "game_id": game_id},
        )
    return written
