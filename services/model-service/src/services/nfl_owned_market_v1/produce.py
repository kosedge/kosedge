"""Produce deterministic synthetic fixtures. CERT=0. No network/DB."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.services.nfl_owned_market_v1.constants import (
    BOOK_ID,
    CERT,
    CHANNEL,
    DATA_LABEL,
    EVT_SOURCE,
    IDENTITY_KIND,
    KO_MINUS_MINUTES,
    PACKAGE,
    PINNED_AWAY,
    PINNED_BATCH_ID,
    PINNED_CUTOFF_UTC,
    PINNED_GAME_ID,
    PINNED_HOME,
    PINNED_KICKOFF_UTC,
    PINNED_SEAL_UTC,
    PINNED_SEASON,
    PINNED_SEASON_TYPE,
    PINNED_TRACE_ID,
    PINNED_WEEK,
    PROFILE_OWNED_MARKET_TRACE,
    PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
    SCHEMA_OWNED_MARKET_TRACE,
    SCHEMA_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
    VENUE_ID,
)
from src.services.nfl_owned_market_v1.hashing import canonical_dumps, sha256_bytes
from src.services.nfl_owned_market_v1.schema import (
    owned_market_trace_schema,
    schema_hash,
    synthetic_market_economic_events_schema,
)
from src.services.nfl_owned_market_v1.validate import (
    rehash_document,
    validate_join,
    validate_owned_market_trace,
    validate_synthetic_market_economic_events,
)

OPS_REL = Path("data/ops/nfl_owned_market_v1")


def envelope() -> dict[str, Any]:
    return {
        "away_team": PINNED_AWAY,
        "book_id": BOOK_ID,
        "game_id": PINNED_GAME_ID,
        "home_team": PINNED_HOME,
        "identity_kind": IDENTITY_KIND,
        "kickoff_utc": PINNED_KICKOFF_UTC,
        "season": PINNED_SEASON,
        "season_type": PINNED_SEASON_TYPE,
        "venue_id": VENUE_ID,
        "week": PINNED_WEEK,
    }


def timing() -> dict[str, Any]:
    return {
        "cutoff_utc": PINNED_CUTOFF_UTC,
        "kickoff_utc": PINNED_KICKOFF_UTC,
        "ko_minus_minutes": KO_MINUS_MINUTES,
        "seal_utc": PINNED_SEAL_UTC,
    }


def _obs(
    *,
    seq: int,
    market: str,
    side: str,
    line: float | None,
    price: int,
    available_at: str,
    observed_at: str,
    caused_by_event_id: str | None,
) -> dict[str, Any]:
    return {
        "available_at": available_at,
        "caused_by_event_id": caused_by_event_id,
        "line": line,
        "market": market,
        "observed_at": observed_at,
        "price": price,
        "seq": seq,
        "side": side,
        "source": "SYNTHETIC_OWNED_QUOTE",
        "source_byte_hash": "11" * 32,
        "status": "DERIVED_PREGAME",
    }


def _evt(
    *,
    event_id: str,
    event_type: str,
    effect_channel: str,
    team: str,
    player_slot: str,
    magnitude: float,
    available_at: str,
    observed_at: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "available_at": available_at,
        "effect_channel": effect_channel,
        "event_id": event_id,
        "event_type": event_type,
        "magnitude": magnitude,
        "observed_at": observed_at,
        "payload": payload,
        "player_slot": player_slot,
        "source": EVT_SOURCE,
        "source_byte_hash": "11" * 32,
        "team": team,
    }


def build_events_document() -> dict[str, Any]:
    doc = {
        "batch_id": PINNED_BATCH_ID,
        "cert": CERT,
        "channel": CHANNEL,
        "data_label": DATA_LABEL,
        "envelope": envelope(),
        "events": [
            _evt(
                event_id="SYNTHETIC_EVT_001",
                event_type="LINEUP_CONFIRM",
                effect_channel="USAGE",
                team=PINNED_HOME,
                player_slot="QB1",
                magnitude=0.25,
                available_at="2026-12-06T15:00:00Z",
                observed_at="2026-12-06T15:00:30Z",
                payload={"slot": "QB1", "status": "CONFIRMED", "fictional": True},
            ),
            _evt(
                event_id="SYNTHETIC_EVT_002",
                event_type="WEATHER_SHIFT",
                effect_channel="TOTAL",
                team="NEUTRAL",
                player_slot="NONE",
                magnitude=-0.5,
                available_at="2026-12-06T15:30:00Z",
                observed_at="2026-12-06T15:30:20Z",
                payload={"wind_mph": 18, "precip": "SYNTHETIC_NONE", "fictional": True},
            ),
            _evt(
                event_id="SYNTHETIC_EVT_003",
                event_type="LIQUIDITY_SHOCK",
                effect_channel="VIG",
                team="NEUTRAL",
                player_slot="NONE",
                magnitude=0.1,
                available_at="2026-12-06T16:00:00Z",
                observed_at="2026-12-06T16:00:10Z",
                payload={"limit_units": 1.0, "fictional": True},
            ),
        ],
        "package": PACKAGE,
        "profile": PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
        "schema_version": SCHEMA_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
        "source_byte_hash": "11" * 32,
        "timing": timing(),
    }
    return rehash_document(doc, kind="events")


def build_trace_document() -> dict[str, Any]:
    doc = {
        "cert": CERT,
        "channel": CHANNEL,
        "data_label": DATA_LABEL,
        "envelope": envelope(),
        "observations": [
            _obs(
                seq=1,
                market="spread",
                side="home",
                line=-3.0,
                price=-110,
                available_at="2026-12-06T15:10:00Z",
                observed_at="2026-12-06T15:10:05Z",
                caused_by_event_id="SYNTHETIC_EVT_001",
            ),
            _obs(
                seq=2,
                market="total",
                side="under",
                line=44.5,
                price=-108,
                available_at="2026-12-06T15:40:00Z",
                observed_at="2026-12-06T15:40:05Z",
                caused_by_event_id="SYNTHETIC_EVT_002",
            ),
            _obs(
                seq=3,
                market="ml",
                side="home",
                line=None,
                price=-155,
                available_at="2026-12-06T16:20:00Z",
                observed_at="2026-12-06T16:20:05Z",
                caused_by_event_id=None,
            ),
        ],
        "package": PACKAGE,
        "profile": PROFILE_OWNED_MARKET_TRACE,
        "schema_version": SCHEMA_OWNED_MARKET_TRACE,
        "source_byte_hash": "11" * 32,
        "timing": timing(),
        "trace_id": PINNED_TRACE_ID,
    }
    return rehash_document(doc, kind="trace")


def _write_json(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    raw = text.encode("utf-8")
    path.write_bytes(raw)
    return sha256_bytes(raw)


def produce_artifacts(*, repo_root: Path | None = None) -> dict[str, Any]:
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    ops = root / OPS_REL
    events = build_events_document()
    trace = build_trace_document()
    events_report = validate_synthetic_market_economic_events(events)
    trace_report = validate_owned_market_trace(trace)
    join_report = validate_join(trace, events)

    schema_trace = owned_market_trace_schema()
    schema_events = synthetic_market_economic_events_schema()
    schema_trace_hash = schema_hash(PROFILE_OWNED_MARKET_TRACE)
    schema_events_hash = schema_hash(PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS)

    paths = {
        "schema_trace": ops / "schemas" / "OWNED_MARKET_TRACE_V1.schema.json",
        "schema_events": ops / "schemas" / "SYNTHETIC_MARKET_ECONOMIC_EVENTS_V1.schema.json",
        "fixture_trace": ops / "fixtures" / "owned_market_trace.synthetic.json",
        "fixture_events": ops / "fixtures" / "synthetic_market_economic_events.synthetic.json",
        "hashes": ops / "hashes" / "FIXTURE_HASHES.json",
        "handoff_json": ops / "HANDOFF_INTERFACE.json",
    }
    file_hashes = {
        "schema_trace": _write_json(paths["schema_trace"], schema_trace),
        "schema_events": _write_json(paths["schema_events"], schema_events),
        "fixture_trace": _write_json(paths["fixture_trace"], trace),
        "fixture_events": _write_json(paths["fixture_events"], events),
    }

    hashes_doc = {
        "cert": CERT,
        "data_label": DATA_LABEL,
        "package": PACKAGE,
        "profiles": {
            PROFILE_OWNED_MARKET_TRACE: {
                "document_hash": trace_report["document_hash"],
                "fixture_path": str(paths["fixture_trace"].relative_to(root)),
                "fixture_sha256": file_hashes["fixture_trace"],
                "schema_hash": schema_trace_hash,
                "schema_path": str(paths["schema_trace"].relative_to(root)),
                "schema_sha256": file_hashes["schema_trace"],
            },
            PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS: {
                "document_hash": events_report["document_hash"],
                "fixture_path": str(paths["fixture_events"].relative_to(root)),
                "fixture_sha256": file_hashes["fixture_events"],
                "schema_hash": schema_events_hash,
                "schema_path": str(paths["schema_events"].relative_to(root)),
                "schema_sha256": file_hashes["schema_events"],
            },
        },
        "canonical_note": (
            "document_hash is sha256(canonical JSON without source_byte_hash). "
            "fixture_sha256 / schema_sha256 are sha256 of on-disk bytes "
            "(indent=2, sort_keys, trailing newline)."
        ),
    }
    file_hashes["hashes"] = _write_json(paths["hashes"], hashes_doc)
    return {
        "events": events,
        "trace": trace,
        "events_report": events_report,
        "trace_report": trace_report,
        "join_report": join_report,
        "file_hashes": file_hashes,
        "hashes_doc": hashes_doc,
        "paths": {key: str(value) for key, value in paths.items()},
        "canonical_dumps_len": len(canonical_dumps(hashes_doc)),
    }
