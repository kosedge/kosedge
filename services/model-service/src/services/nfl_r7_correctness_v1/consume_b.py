"""Consume Worker B handoff and register the two isolated profiles.

Worker A is the sole registrar. Imports B validators — does not copy them.
Does not widen B ownership or open real-mode. CERT=0.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.services.nfl_ops_v1_evidence.profiles import (
    PROFILE_OWNED_MARKET_TRACE,
    PROFILE_SYNTHETIC_MARKET_EVENTS,
    WORKER_A_ID,
    WORKER_B_ID,
    register_b_profile,
)
from src.services.nfl_r7_correctness_v1.pins import GATE_713_TIP, R6_A_TIP, R6_B_TIP
from src.services.nfl_t5208u.hashing import sha256_file

# Import — do not copy — B validators.
from src.services.nfl_owned_market_v1.validate import (  # noqa: E402
    validate_join,
    validate_owned_market_trace,
    validate_synthetic_market_economic_events,
)

B_TIP = "f6566c9271ae16e53f67d08555814c4df94fe751"
B_PR = 715
COS_ACCEPT = "5c86d228"
HANDOFF_REL = "data/ops/nfl_owned_market_v1/HANDOFF_INTERFACE.json"
HANDOFF_SHA256 = "5b7ee2e4fb849e1bcaf7d09f888d2e61ff6f9993550727f66b66d0126545b553"

EXPECTED = {
    PROFILE_OWNED_MARKET_TRACE: {
        "schema_hash": "cd564061cb12a45b0cf813d3e23b6e1166e3fefb77d6b3525e6a997a819dfc57",
        "document_hash": "dda58e0bccc509784cb32326f679463c58db8f203c104a1d635c2ceb7f460d59",
        "fixture_sha256": "7e412d1f701929ae963ff0d50d2ee11af93a9b928f14d770e46b310e20da9a4b",
    },
    PROFILE_SYNTHETIC_MARKET_EVENTS: {
        "schema_hash": "326c18108d90ce4b2de5cbbfdb499274abe2aca37baf7a2046a91aa24e3ac021",
        "document_hash": "ab6e0f4ec87a109dee07024ae186c252e6a6643b09fa9ec3538858e283341efd",
        "fixture_sha256": "37b21de21c6bb68493b87b8ac908c89f2cf0ebe03ec996d867646386957eb87f",
    },
}


class HandoffRefuse(ValueError):
    """B handoff failed A's consume checks."""


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def consume_b_handoff(
    *,
    root: Path,
    registered_by: str = WORKER_A_ID,
) -> dict[str, Any]:
    repo = Path(root)
    handoff_path = repo / HANDOFF_REL
    if not handoff_path.is_file():
        raise HandoffRefuse(f"missing B handoff {HANDOFF_REL}")
    actual_sha = sha256_file(handoff_path)
    if actual_sha != HANDOFF_SHA256:
        raise HandoffRefuse(
            f"HANDOFF_INTERFACE.json sha {actual_sha} != pinned {HANDOFF_SHA256}"
        )
    handoff = _load_json(handoff_path)
    if handoff.get("ready_for_A") is not True:
        raise HandoffRefuse("handoff ready_for_A is not true")
    if handoff.get("worker") != "B":
        raise HandoffRefuse("handoff worker is not B")
    if handoff.get("cert") != 0:
        raise HandoffRefuse("handoff cert must be 0")
    pins = handoff.get("source_pins") or {}
    if pins.get("r6_a") != R6_A_TIP or pins.get("r6_b") != R6_B_TIP:
        raise HandoffRefuse("handoff R6 pins drifted")
    if pins.get("gate_713_tip") != GATE_713_TIP:
        raise HandoffRefuse("handoff #713 pin drifted")
    if pins.get("pr_714_is_base") is not False:
        raise HandoffRefuse("#714 must stay not-a-base")

    profiles = handoff.get("profiles") or {}
    fixtures: dict[str, dict[str, Any]] = {}
    binds: dict[str, dict[str, Any]] = {}
    for profile_id, expected in EXPECTED.items():
        row = profiles.get(profile_id) or {}
        for key, digest in expected.items():
            if row.get(key) != digest:
                raise HandoffRefuse(
                    f"{profile_id} {key} {row.get(key)!r} != Cos pin {digest}"
                )
        fixture_path = repo / str(row["fixture_path"])
        schema_path = repo / str(row["schema_path"])
        if sha256_file(fixture_path) != expected["fixture_sha256"]:
            raise HandoffRefuse(f"{profile_id} fixture bytes drifted")
        if sha256_file(schema_path) != row.get("schema_sha256"):
            raise HandoffRefuse(f"{profile_id} schema bytes drifted")
        fixtures[profile_id] = _load_json(fixture_path)
        binds[profile_id] = {
            "schema_hash": expected["schema_hash"],
            "document_hash": expected["document_hash"],
            "fixture_sha256": expected["fixture_sha256"],
            "schema_path": row["schema_path"],
            "fixture_path": row["fixture_path"],
            "validator": (handoff.get("validators") or {}).get(profile_id),
        }

    # Import-only validators. Do not copy B logic.
    trace_ok = validate_owned_market_trace(fixtures[PROFILE_OWNED_MARKET_TRACE])
    events_ok = validate_synthetic_market_economic_events(
        fixtures[PROFILE_SYNTHETIC_MARKET_EVENTS]
    )
    join_ok = validate_join(
        fixtures[PROFILE_OWNED_MARKET_TRACE],
        fixtures[PROFILE_SYNTHETIC_MARKET_EVENTS],
    )
    if trace_ok["document_hash"] != EXPECTED[PROFILE_OWNED_MARKET_TRACE]["document_hash"]:
        raise HandoffRefuse("validated trace document_hash != Cos pin")
    if events_ok["document_hash"] != EXPECTED[PROFILE_SYNTHETIC_MARKET_EVENTS]["document_hash"]:
        raise HandoffRefuse("validated events document_hash != Cos pin")

    registered = []
    for profile_id, bind in binds.items():
        registered.append(
            register_b_profile(
                profile_id,
                registered_by=registered_by,
                handoff={
                    "handoff_sha256": HANDOFF_SHA256,
                    "worker": "B",
                    "worker_id": WORKER_B_ID,
                    "profile_id": profile_id,
                    "isolated_area": "data/ops/nfl_owned_market_v1",
                    "b_tip": B_TIP,
                    "b_pr": B_PR,
                    "cos_accept": COS_ACCEPT,
                    **bind,
                },
            )
        )

    return {
        "ok": True,
        "cert": 0,
        "consumed": True,
        "registered_by": registered_by,
        "handoff_sha256": HANDOFF_SHA256,
        "b_tip": B_TIP,
        "b_pr": B_PR,
        "cos_accept": COS_ACCEPT,
        "validators_imported": [
            "src.services.nfl_owned_market_v1.validate:validate_owned_market_trace",
            "src.services.nfl_owned_market_v1.validate:validate_synthetic_market_economic_events",
            "src.services.nfl_owned_market_v1.validate:validate_join",
        ],
        "copied_validators": False,
        "widened_b_ownership": False,
        "real_mode": False,
        "trace": {
            "validated": True,
            "document_hash": trace_ok["document_hash"],
            "n_observations": trace_ok["n_observations"],
        },
        "events": {
            "validated": True,
            "document_hash": events_ok["document_hash"],
            "n_events": events_ok["n_events"],
        },
        "join": {
            "joined": join_ok["joined"],
            "game_id": join_ok["game_id"],
            "bound_event_ids": join_ok["bound_event_ids"],
        },
        "profiles": [row.profile_id for row in registered],
        "status": {row.profile_id: row.status for row in registered},
    }
