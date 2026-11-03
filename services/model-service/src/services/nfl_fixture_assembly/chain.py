"""Additive t5194u A→B offline chain record.

Carries candidate / game / forecast / provenance / cutoff / capability.
Does not rewrite t5178u v0 evidence artifacts.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Mapping

from src.services.nfl_fixture_assembly.contract import (
    CHAIN_CONTRACT_ID,
    CHAIN_SCHEMA_VERSION,
    CONTRACT_ID,
    CONTRACT_SCHEMA_VERSION,
    FIXTURE_CHANNEL,
    SYNTHETIC_ADJUSTMENT_POLICY,
    AssemblyResult,
    FixtureEnvelope,
)
from src.services.nfl_hhl1_capture.identity import canonical_json, sha256_hex


def serialize_fixture_chain(
    envelope: FixtureEnvelope,
    result: AssemblyResult,
) -> Dict[str, Any]:
    forecast = envelope.forecast
    provenance = envelope.provenance
    return {
        "chain_contract_id": CHAIN_CONTRACT_ID,
        "chain_schema_version": CHAIN_SCHEMA_VERSION,
        "base_contract_id": CONTRACT_ID,
        "base_schema_version": CONTRACT_SCHEMA_VERSION,
        "channel": FIXTURE_CHANNEL,
        "fixture": True,
        "production_mode": False,
        "cacheable": False,
        "honor_env_bypass": False,
        "requested_output": envelope.requested_output.value,
        "eligibility": result.eligibility.to_dict(),
        "quote": result.quote.to_dict(),
        "forecast": {
            "forecast_id": forecast.forecast_id,
            "game_id": forecast.game_id,
            "period": forecast.period.value,
            "side": forecast.side.value,
            "point_margin": forecast.point_margin,
        },
        "provenance": asdict(provenance),
        "cutoff": {
            "source_published_at": provenance.source_published_at,
            "captured_at": provenance.captured_at,
            "decision_ts": provenance.decision_ts,
            "kickoff_ts": provenance.kickoff_ts,
            "as_of_ts": provenance.as_of_ts,
        },
        "capability": {"bits": list(result.capability_bits)},
        "l1_candidate": dict(envelope.l1_candidate),
        "game_id": result.admitted_game_id,
        "admitted_capture_id": result.admitted_capture_id,
        "offense_raw": result.offense_raw,
        "defense_raw": result.defense_raw,
        "offense_multiplier": result.offense_multiplier,
        "defense_multiplier": result.defense_multiplier,
        "adjustment_policy": result.adjustment_policy or SYNTHETIC_ADJUSTMENT_POLICY,
    }


def chain_digest(payload: Mapping[str, Any]) -> str:
    return sha256_hex(canonical_json(dict(payload)).encode("utf-8"))
