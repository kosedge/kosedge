"""Produce isolated fixtures. CERT=0. Profiles stay separate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.services.nfl_owned_market_v1.arithmetic import portfolio_roi, settle_ticket
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
    PINNED_WEEK,
    PROFILE_OWNED_MARKET_TRACE,
    PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
    ROLE_FICTIONAL_ECONOMIC,
    SCHEMA_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
    VENUE_ID,
)
from src.services.nfl_owned_market_v1.hashing import canonical_dumps, sha256_bytes
from src.services.nfl_owned_market_v1.owned_readiness import build_owned_readiness_document
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


def _tkt(**fields: Any) -> dict[str, Any]:
    row = {
        "away_score": None,
        "close_line": None,
        "close_price": None,
        "home_score": None,
        "juice": None,
        "juice_status": "DATA_GAP",
        "line": None,
        "open_line": None,
        "open_price": None,
        "settlement_status": "final",
        "source": EVT_SOURCE,
        "source_byte_hash": "11" * 32,
        **fields,
    }
    return row


def build_events_document() -> dict[str, Any]:
    """FICTIONAL_ECONOMIC risk1 win/loss/push/void + ATS + ROI + line-CLV."""
    tickets = [
        _tkt(
            ticket_id="SYNTHETIC_TKT_001",
            event_type="RISK1_SETTLEMENT",
            market="spread",
            side="home",
            line=-3.0,
            juice=-110,
            juice_status="stamped",
            open_line=-3.0,
            close_line=-4.0,
            open_price=-110,
            close_price=-115,
            home_score=24,
            away_score=20,
            available_at="2026-12-06T15:10:00Z",
            observed_at="2026-12-06T15:10:05Z",
        ),
        _tkt(
            ticket_id="SYNTHETIC_TKT_002",
            event_type="ATS_GRADE",
            market="spread",
            side="home",
            line=-3.0,
            juice=-110,
            juice_status="stamped",
            open_line=-3.0,
            close_line=-3.0,
            open_price=-110,
            close_price=-110,
            home_score=23,
            away_score=20,
            available_at="2026-12-06T15:20:00Z",
            observed_at="2026-12-06T15:20:05Z",
        ),
        _tkt(
            ticket_id="SYNTHETIC_TKT_003",
            event_type="RISK1_SETTLEMENT",
            market="spread",
            side="away",
            line=7.0,
            juice=-105,
            juice_status="stamped",
            open_line=7.0,
            close_line=6.5,
            open_price=-105,
            close_price=-108,
            home_score=30,
            away_score=10,
            available_at="2026-12-06T15:40:00Z",
            observed_at="2026-12-06T15:40:05Z",
        ),
        _tkt(
            ticket_id="SYNTHETIC_TKT_004",
            event_type="RISK1_SETTLEMENT",
            market="total",
            side="under",
            line=44.5,
            juice=-110,
            juice_status="stamped",
            open_line=44.5,
            close_line=43.5,
            open_price=-110,
            close_price=-110,
            home_score=17,
            away_score=20,
            available_at="2026-12-06T16:00:00Z",
            observed_at="2026-12-06T16:00:05Z",
        ),
        _tkt(
            ticket_id="SYNTHETIC_TKT_005",
            event_type="RISK1_SETTLEMENT",
            market="spread",
            side="home",
            line=-2.5,
            juice=None,
            juice_status="excluded_void",
            open_line=-2.5,
            close_line=-2.5,
            open_price=-110,
            close_price=-110,
            home_score=None,
            away_score=None,
            settlement_status="void",
            available_at="2026-12-06T16:10:00Z",
            observed_at="2026-12-06T16:10:05Z",
        ),
    ]
    hashed = [dict(t) for t in tickets]
    for row in hashed:
        from src.services.nfl_owned_market_v1.validate import rehash_row

        rehash_row(row)
    settlements = [settle_ticket(row) for row in hashed]
    roi = portfolio_roi(settlements)
    doc = {
        "batch_id": PINNED_BATCH_ID,
        "cert": CERT,
        "channel": CHANNEL,
        "data_label": DATA_LABEL,
        "envelope": envelope(),
        "package": PACKAGE,
        "profile": PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
        "profile_role": ROLE_FICTIONAL_ECONOMIC,
        "roi": roi,
        "schema_version": SCHEMA_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
        "settlements": settlements,
        "source_byte_hash": "11" * 32,
        "tickets": hashed,
        "timing": timing(),
    }
    return rehash_document(doc, kind="events")


def build_trace_document(*, repo_root: Path | None = None) -> dict[str, Any]:
    """OWNED_READINESS. Never a fictional owned-source completion."""
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    return build_owned_readiness_document(root)


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
    trace = build_trace_document(repo_root=root)
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
        "fixture_trace": ops / "fixtures" / "owned_market_trace.readiness.json",
        "fixture_events": ops / "fixtures" / "synthetic_market_economic_events.risk1.json",
        "hashes": ops / "hashes" / "FIXTURE_HASHES.json",
        "handoff_json": ops / "HANDOFF_INTERFACE.json",
        "unavailable": ops / "OWNED_187_400_CLOCK_UNAVAILABLE.md",
    }
    file_hashes = {
        "schema_trace": _write_json(paths["schema_trace"], schema_trace),
        "schema_events": _write_json(paths["schema_events"], schema_events),
        "fixture_trace": _write_json(paths["fixture_trace"], trace),
        "fixture_events": _write_json(paths["fixture_events"], events),
    }

    hashes_doc = {
        "cert": CERT,
        "data_label": {
            PROFILE_OWNED_MARKET_TRACE: trace.get("data_label"),
            PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS: DATA_LABEL,
        },
        "package": PACKAGE,
        "prior_handoff_sha256": "5b7ee2e4fb849e1bcaf7d09f888d2e61ff6f9993550727f66b66d0126545b553",
        "profiles": {
            PROFILE_OWNED_MARKET_TRACE: {
                "document_hash": trace_report["document_hash"],
                "fixture_path": str(paths["fixture_trace"].relative_to(root)),
                "fixture_sha256": file_hashes["fixture_trace"],
                "profile_role": "OWNED_READINESS",
                "schema_hash": schema_trace_hash,
                "schema_path": str(paths["schema_trace"].relative_to(root)),
                "schema_sha256": file_hashes["schema_trace"],
            },
            PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS: {
                "document_hash": events_report["document_hash"],
                "fixture_path": str(paths["fixture_events"].relative_to(root)),
                "fixture_sha256": file_hashes["fixture_events"],
                "profile_role": "FICTIONAL_ECONOMIC",
                "schema_hash": schema_events_hash,
                "schema_path": str(paths["schema_events"].relative_to(root)),
                "schema_sha256": file_hashes["schema_events"],
            },
        },
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
