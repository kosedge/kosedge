"""Stable hand-off interface for Worker A. B does not register these."""

from __future__ import annotations

from typing import Any

from src.services.nfl_owned_market_v1.constants import (
    CERT,
    OWNER_CLEAR,
    PACKAGE,
    PLAN_FINGERPRINT,
    PRIOR_COS_ACCEPT,
    PRIOR_HANDOFF_SHA256,
    PROFILE_OWNED_MARKET_TRACE,
    PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
    RETURN_ID,
    RETURN_TICKET,
    ROLE_FICTIONAL_ECONOMIC,
    ROLE_OWNED_READINESS,
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
        "do_not": [
            "B does not edit shared files",
            "B does not register profiles on the shared evidence gate",
            "A alone registers the two profile names on R7_CORRECTNESS_V1",
            "Do not treat FICTIONAL_ECONOMIC tickets as owned-source completion",
            "Do not join owned 2020/21 quotes to outcomes under this return",
        ],
        "join_contract": {
            "profiles_separate": True,
            "owned_completion_claimed": False,
            "validator": "src.services.nfl_owned_market_v1.validate:validate_join",
        },
        "owner_clear": OWNER_CLEAR,
        "package": PACKAGE,
        "plan_fingerprint": PLAN_FINGERPRINT,
        "preserves": {
            "prior_cos_accept": PRIOR_COS_ACCEPT,
            "prior_handoff_sha256": PRIOR_HANDOFF_SHA256,
        },
        "producers": {
            PROFILE_OWNED_MARKET_TRACE: "src.services.nfl_owned_market_v1.owned_readiness:build_owned_readiness_document",
            PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS: "src.services.nfl_owned_market_v1.produce:build_events_document",
        },
        "profile_roles": {
            PROFILE_OWNED_MARKET_TRACE: ROLE_OWNED_READINESS,
            PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS: ROLE_FICTIONAL_ECONOMIC,
        },
        "profiles": {
            PROFILE_OWNED_MARKET_TRACE: hashes[PROFILE_OWNED_MARKET_TRACE],
            PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS: hashes[
                PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS
            ],
        },
        "ready_for_A": True,
        "return_id": RETURN_ID,
        "return_ticket": RETURN_TICKET,
        "scope_id": SCOPE_ID,
        "source_pins": source_pins(),
        "ticket": TICKET,
        "validators": {
            PROFILE_OWNED_MARKET_TRACE: "src.services.nfl_owned_market_v1.validate:validate_owned_market_trace",
            PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS: "src.services.nfl_owned_market_v1.validate:validate_synthetic_market_economic_events",
        },
        "worker": WORKER,
    }
