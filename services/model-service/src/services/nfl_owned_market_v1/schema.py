"""JSON Schema bodies. Profiles stay separate. CERT=0."""

from __future__ import annotations

from typing import Any

from src.services.nfl_owned_market_v1.constants import (
    CERT,
    EVENT_TYPES,
    MARKETS,
    PACKAGE,
    PROFILE_OWNED_MARKET_TRACE,
    PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
    ROLE_FICTIONAL_ECONOMIC,
    ROLE_OWNED_READINESS,
    SCHEMA_OWNED_MARKET_TRACE,
    SCHEMA_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
    SIDES,
    TICKET_FIELDS,
)
from src.services.nfl_owned_market_v1.hashing import canonical_sha256


def _sha256_property() -> dict[str, Any]:
    return {
        "type": "string",
        "pattern": "^[0-9a-f]{64}$",
        "not": {"const": "0" * 64},
    }


def _utc_property() -> dict[str, Any]:
    return {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"}


def ticket_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(TICKET_FIELDS),
        "properties": {
            "ticket_id": {"type": "string", "pattern": r"^SYNTHETIC_TKT_"},
            "event_type": {"enum": sorted(EVENT_TYPES)},
            "market": {"enum": sorted(MARKETS)},
            "side": {"enum": sorted(SIDES)},
            "line": {"type": ["number", "null"]},
            "juice": {"type": ["integer", "null"]},
            "juice_status": {"enum": ["stamped", "DATA_GAP", "excluded_void"]},
            "open_line": {"type": ["number", "null"]},
            "close_line": {"type": ["number", "null"]},
            "open_price": {"type": ["integer", "null"]},
            "close_price": {"type": ["integer", "null"]},
            "home_score": {"type": ["number", "null"]},
            "away_score": {"type": ["number", "null"]},
            "settlement_status": {"enum": ["final", "void"]},
            "available_at": _utc_property(),
            "observed_at": _utc_property(),
            "source": {"const": "SYNTHETIC_RISK1_TICKET"},
            "source_byte_hash": _sha256_property(),
        },
    }


def owned_market_trace_schema() -> dict[str, Any]:
    """OWNED_READINESS only. Not a fictional quote completion."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": PROFILE_OWNED_MARKET_TRACE,
        "schema_version": SCHEMA_OWNED_MARKET_TRACE,
        "profile": PROFILE_OWNED_MARKET_TRACE,
        "profile_role": ROLE_OWNED_READINESS,
        "package": PACKAGE,
        "cert": CERT,
        "type": "object",
        "additionalProperties": False,
        "required": [
            "schema_version",
            "profile",
            "profile_role",
            "package",
            "cert",
            "channel",
            "data_label",
            "owned_completion_claimed",
            "probe",
            "unavailable",
            "scientific_hold",
            "source_byte_hash",
        ],
        "properties": {
            "schema_version": {"const": SCHEMA_OWNED_MARKET_TRACE},
            "profile": {"const": PROFILE_OWNED_MARKET_TRACE},
            "profile_role": {"const": ROLE_OWNED_READINESS},
            "package": {"const": PACKAGE},
            "cert": {"const": CERT},
            "channel": {"const": "OWNED_READINESS"},
            "data_label": {
                "enum": ["OWNED_SOURCE_UNAVAILABLE", "OWNED_SOURCE_BOUND"]
            },
            "owned_completion_claimed": {"const": False},
            "probe": {"type": "object"},
            "unavailable": {"type": "array"},
            "scientific_hold": {"type": "array", "items": {"type": "string"}},
            "source_byte_hash": _sha256_property(),
        },
    }


def synthetic_market_economic_events_schema() -> dict[str, Any]:
    """FICTIONAL_ECONOMIC risk1 settlement. Not owned-readiness."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
        "schema_version": SCHEMA_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
        "profile": PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
        "profile_role": ROLE_FICTIONAL_ECONOMIC,
        "package": PACKAGE,
        "cert": CERT,
        "type": "object",
        "additionalProperties": False,
        "required": [
            "schema_version",
            "profile",
            "profile_role",
            "package",
            "cert",
            "data_label",
            "channel",
            "batch_id",
            "envelope",
            "timing",
            "tickets",
            "settlements",
            "roi",
            "source_byte_hash",
        ],
        "properties": {
            "schema_version": {"const": SCHEMA_SYNTHETIC_MARKET_ECONOMIC_EVENTS},
            "profile": {"const": PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS},
            "profile_role": {"const": ROLE_FICTIONAL_ECONOMIC},
            "package": {"const": PACKAGE},
            "cert": {"const": CERT},
            "data_label": {"const": "SYNTHETIC"},
            "channel": {"const": "SYNTHETIC"},
            "batch_id": {"type": "string", "pattern": r"^SYNTHETIC_"},
            "envelope": {"type": "object"},
            "timing": {"type": "object"},
            "tickets": {
                "type": "array",
                "minItems": 1,
                "items": ticket_schema(),
            },
            "settlements": {"type": "array"},
            "roi": {"type": "object"},
            "source_byte_hash": _sha256_property(),
        },
    }


def schema_for(profile: str) -> dict[str, Any]:
    if profile == PROFILE_OWNED_MARKET_TRACE:
        return owned_market_trace_schema()
    if profile == PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS:
        return synthetic_market_economic_events_schema()
    raise ValueError(f"unknown profile {profile!r}")


def schema_hash(profile: str) -> str:
    return canonical_sha256(schema_for(profile))
