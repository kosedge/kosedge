"""Paired recorder: produce bytes ↔ gate bytes. Unpaired refuse. CERT=0."""

from __future__ import annotations

from typing import Any, Mapping

from src.services.nfl_r7_correctness_v1.pins import CERT, PACKAGE, SCHEMA_ID
from src.services.nfl_t5208u.hashing import canonical_sha256


class PairRefuse(ValueError):
    """Produce/record pair failed."""


def pair_record(
    produce: Mapping[str, Any],
    gated: Mapping[str, Any],
) -> dict[str, Any]:
    if produce.get("cert") != CERT or gated.get("cert") != CERT:
        raise PairRefuse("CERT must stay 0 on both arms")
    if produce.get("package") != PACKAGE:
        raise PairRefuse("produce package is not R7_CORRECTNESS_V1")
    if gated.get("profile") != "R7_CORRECTNESS_V1":
        raise PairRefuse("gated profile is not R7_CORRECTNESS_V1")
    for key in ("packet_hash", "history_hash", "r7_config_hash", "game_id"):
        if produce.get(key) != gated.get(key) and key in produce:
            if produce.get(key) != (gated.get("produce_binds") or {}).get(key):
                raise PairRefuse(f"pair mismatch on {key}")
    produce_hash = canonical_sha256(
        {
            "game_id": produce.get("game_id"),
            "packet_hash": produce.get("packet_hash"),
            "history_hash": produce.get("history_hash"),
            "r7_config_hash": produce.get("r7_config_hash"),
            "r7_code_hash": produce.get("r7_code_hash"),
            "if_margin": produce.get("if_margin"),
            "q2_margin": produce.get("q2_margin"),
            "c_margin": produce.get("c_margin"),
        }
    )
    gate_hash = canonical_sha256(
        {
            "profile": gated.get("profile"),
            "input_hash": gated.get("input_hash"),
            "history_hash": gated.get("history_hash"),
            "config_hash": gated.get("config_hash"),
            "code_hash": gated.get("code_hash"),
            "ok": gated.get("ok"),
        }
    )
    pair_hash = canonical_sha256({"produce": produce_hash, "gate": gate_hash})
    if produce_hash == gate_hash:
        raise PairRefuse("produce/gate hashes collapsed (not a pair)")
    return {
        "schema_id": SCHEMA_ID,
        "package": PACKAGE,
        "cert": CERT,
        "paired": True,
        "produce_hash": produce_hash,
        "gate_hash": gate_hash,
        "pair_hash": pair_hash,
        "game_id": produce.get("game_id"),
        "profile": "R7_CORRECTNESS_V1",
        "ok": bool(gated.get("ok")),
        "ready_for_review": False,
        "accepted": False,
    }
