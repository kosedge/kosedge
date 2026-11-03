"""Stable hand-off interface for Worker A. B does not register these."""

from __future__ import annotations

from typing import Any

from src.services.nfl_owned_market_v1.constants import (
    CERT,
    DATA_LABEL,
    OWNER_CLEAR,
    PACKAGE,
    PLAN_FINGERPRINT,
    PROFILE_OWNED_MARKET_TRACE,
    PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
    SCOPE_ID,
    TICKET,
    WORKER,
)
from src.services.nfl_owned_market_v1.pins import source_pins
from src.services.nfl_owned_market_v1.produce import produce_artifacts
from src.services.nfl_owned_market_v1.validate import code_content_hash


def handoff_interface(artifacts: dict[str, Any] | None = None) -> dict[str, Any]:
    pack = artifacts if artifacts is not None else produce_artifacts()
    hashes = pack["hashes_doc"]["profiles"]
    return {
        "cert": CERT,
        "code_hash": code_content_hash(),
        "data_label": DATA_LABEL,
        "do_not": [
            "B does not edit shared files",
            "B does not register profiles on the shared evidence gate",
            "A alone registers OWNED_MARKET_TRACE_V1 and SYNTHETIC_MARKET_ECONOMIC_EVENTS_V1 on R7_CORRECTNESS_V1",
            "#714 stays PARTIAL and is not a base",
        ],
        "join_contract": {
            "caused_by_event_id": "observations[].caused_by_event_id -> events[].event_id",
            "game_id": "shared envelope.game_id",
            "timing": "event.available_at < observation.available_at < seal_utc=cutoff_utc=kickoff-60",
            "validator": "src.services.nfl_owned_market_v1.validate:validate_join",
        },
        "owner_clear": OWNER_CLEAR,
        "package": PACKAGE,
        "plan_fingerprint": PLAN_FINGERPRINT,
        "producers": {
            PROFILE_OWNED_MARKET_TRACE: "src.services.nfl_owned_market_v1.produce:build_trace_document",
            PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS: "src.services.nfl_owned_market_v1.produce:build_events_document",
        },
        "profiles": {
            PROFILE_OWNED_MARKET_TRACE: hashes[PROFILE_OWNED_MARKET_TRACE],
            PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS: hashes[
                PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS
            ],
        },
        "ready_for_A": True,
        "scope_id": SCOPE_ID,
        "source_pins": source_pins(),
        "ticket": TICKET,
        "validators": {
            PROFILE_OWNED_MARKET_TRACE: "src.services.nfl_owned_market_v1.validate:validate_owned_market_trace",
            PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS: "src.services.nfl_owned_market_v1.validate:validate_synthetic_market_economic_events",
        },
        "worker": WORKER,
    }
