"""JSON Schema bodies for the two B profiles. CERT=0. Synthetic only."""

from __future__ import annotations

from typing import Any

from src.services.nfl_owned_market_v1.constants import (
    BOOK_ID,
    CERT,
    CHANNEL,
    DATA_LABEL,
    EFFECT_CHANNELS,
    ENVELOPE_FIELDS,
    EVENT_FIELDS,
    EVENT_TYPES,
    IDENTITY_KIND,
    KO_MINUS_MINUTES,
    MARKETS,
    OBS_FIELDS,
    OBS_SOURCE,
    OBS_STATUS,
    PACKAGE,
    PLAYER_SLOTS,
    PROFILE_OWNED_MARKET_TRACE,
    PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
    SCHEMA_OWNED_MARKET_TRACE,
    SCHEMA_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
    SIDES,
    TEAMS,
    TIMING_FIELDS,
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


def envelope_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(ENVELOPE_FIELDS),
        "properties": {
            "game_id": {"type": "string", "pattern": r"^SYNTHETIC_"},
            "season": {"type": "integer"},
            "week": {"type": "integer"},
            "season_type": {"const": "REG"},
            "home_team": {"type": "string", "minLength": 1},
            "away_team": {"type": "string", "minLength": 1},
            "kickoff_utc": _utc_property(),
            "venue_id": {"type": "string", "minLength": 1},
            "identity_kind": {"const": IDENTITY_KIND},
            "book_id": {"const": BOOK_ID},
        },
    }


def timing_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(TIMING_FIELDS),
        "properties": {
            "kickoff_utc": _utc_property(),
            "cutoff_utc": _utc_property(),
            "seal_utc": _utc_property(),
            "ko_minus_minutes": {"const": KO_MINUS_MINUTES},
        },
    }


def observation_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(OBS_FIELDS),
        "properties": {
            "seq": {"type": "integer", "minimum": 1},
            "market": {"enum": sorted(MARKETS)},
            "side": {"enum": sorted(SIDES)},
            "line": {"type": ["number", "null"]},
            "price": {"type": "integer"},
            "available_at": _utc_property(),
            "observed_at": _utc_property(),
            "source": {"const": OBS_SOURCE},
            "status": {"const": OBS_STATUS},
            "caused_by_event_id": {"type": ["string", "null"]},
            "source_byte_hash": _sha256_property(),
        },
    }


def event_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(EVENT_FIELDS),
        "properties": {
            "event_id": {"type": "string", "pattern": r"^SYNTHETIC_EVT_"},
            "event_type": {"enum": sorted(EVENT_TYPES)},
            "effect_channel": {"enum": sorted(EFFECT_CHANNELS)},
            "team": {"enum": sorted(TEAMS)},
            "player_slot": {"enum": sorted(PLAYER_SLOTS)},
            "magnitude": {"type": "number"},
            "available_at": _utc_property(),
            "observed_at": _utc_property(),
            "payload": {"type": "object"},
            "source": {"type": "string", "minLength": 1},
            "source_byte_hash": _sha256_property(),
        },
    }


def owned_market_trace_schema() -> dict[str, Any]:
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": PROFILE_OWNED_MARKET_TRACE,
        "schema_version": SCHEMA_OWNED_MARKET_TRACE,
        "profile": PROFILE_OWNED_MARKET_TRACE,
        "package": PACKAGE,
        "cert": CERT,
        "data_label": DATA_LABEL,
        "channel": CHANNEL,
        "type": "object",
        "additionalProperties": False,
        "required": [
            "schema_version",
            "profile",
            "package",
            "cert",
            "data_label",
            "channel",
            "trace_id",
            "envelope",
            "timing",
            "observations",
            "source_byte_hash",
        ],
        "properties": {
            "schema_version": {"const": SCHEMA_OWNED_MARKET_TRACE},
            "profile": {"const": PROFILE_OWNED_MARKET_TRACE},
            "package": {"const": PACKAGE},
            "cert": {"const": CERT},
            "data_label": {"const": DATA_LABEL},
            "channel": {"const": CHANNEL},
            "trace_id": {"type": "string", "pattern": r"^SYNTHETIC_"},
            "envelope": envelope_schema(),
            "timing": timing_schema(),
            "observations": {
                "type": "array",
                "minItems": 1,
                "items": observation_schema(),
            },
            "source_byte_hash": _sha256_property(),
        },
    }


def synthetic_market_economic_events_schema() -> dict[str, Any]:
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
        "schema_version": SCHEMA_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
        "profile": PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
        "package": PACKAGE,
        "cert": CERT,
        "data_label": DATA_LABEL,
        "channel": CHANNEL,
        "type": "object",
        "additionalProperties": False,
        "required": [
            "schema_version",
            "profile",
            "package",
            "cert",
            "data_label",
            "channel",
            "batch_id",
            "envelope",
            "timing",
            "events",
            "source_byte_hash",
        ],
        "properties": {
            "schema_version": {"const": SCHEMA_SYNTHETIC_MARKET_ECONOMIC_EVENTS},
            "profile": {"const": PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS},
            "package": {"const": PACKAGE},
            "cert": {"const": CERT},
            "data_label": {"const": DATA_LABEL},
            "channel": {"const": CHANNEL},
            "batch_id": {"type": "string", "pattern": r"^SYNTHETIC_"},
            "envelope": envelope_schema(),
            "timing": timing_schema(),
            "events": {
                "type": "array",
                "minItems": 1,
                "items": event_schema(),
            },
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
