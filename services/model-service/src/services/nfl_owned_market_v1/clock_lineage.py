"""Bounded CSV envelope clock/source-lineage (EVIDENCE 70648). CERT=0.

Compares 44 selected CSV associations to request / provider-snapshot /
book-update / download metadata. Does not invent clock_provenance.
Does not mark freeze#limitations verified. Does not copy quote values.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from src.services.nfl_owned_market_v1.constants import (
    CERT,
    PACKAGE,
    PIN_CSV_CLOCK_METADATA_BYTES,
    PIN_CSV_CLOCK_METADATA_PATH,
    PIN_CSV_CLOCK_METADATA_SHA256,
    PIN_CSV_CLOCK_ORIGINAL_METADATA_SHA256,
    PIN_CSV_SELECTED_N,
    PIN_FREEZE_PATH,
    PIN_JSONL_UNKNOWN_N,
    PIN_OWNED_HISTORY,
    PIN_SELECTED_187,
)
from src.services.nfl_owned_market_v1.hashing import sha256_bytes
from src.services.nfl_owned_market_v1.refuse import OwnedMarketRefuse

VALUE_KEYS = frozenset(
    {"line", "price", "price_home", "price_away", "spread_home", "home_margin", "total_points"}
)
FREEZE_LIMITATIONS_LOCATOR = (
    f"{PIN_OWNED_HISTORY}:{PIN_FREEZE_PATH}#limitations"
)


def verify_staged_metadata(path: Path) -> bytes:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != PIN_CSV_CLOCK_METADATA_SHA256:
        raise OwnedMarketRefuse(
            f"{path} sha256 {digest} != pinned {PIN_CSV_CLOCK_METADATA_SHA256}"
        )
    if len(raw) != PIN_CSV_CLOCK_METADATA_BYTES:
        raise OwnedMarketRefuse(f"{path} bytes {len(raw)} != {PIN_CSV_CLOCK_METADATA_BYTES}")
    return raw


def _require_no_values(payload: Any, *, where: str) -> None:
    if isinstance(payload, dict):
        hit = sorted(set(payload) & VALUE_KEYS)
        if hit:
            raise OwnedMarketRefuse(f"{where} carries quote-value keys {hit}")
        for key, value in payload.items():
            _require_no_values(value, where=f"{where}.{key}")
    elif isinstance(payload, list):
        for i, item in enumerate(payload):
            _require_no_values(item, where=f"{where}[{i}]")


def expand_selected_associations(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """44 = event×book rows that carry spreads market_last_update."""
    rows: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for env_i, source in enumerate(doc.get("sources") or []):
        _require_no_values(source, where=f"sources[{env_i}]")
        claimed = int(source.get("selected_csv_book_quote_n") or 0)
        got = 0
        for event in source.get("matching_events_metadata") or []:
            for book in event.get("books_metadata") or []:
                markets = book.get("market_last_updates") or []
                spreads = next((m for m in markets if m.get("key") == "spreads"), None)
                base = {
                    "book": book.get("key"),
                    "envelope_index": env_i,
                    "envelope_path": source.get("path"),
                    "envelope_sha256": source.get("sha256"),
                    "event_id": event.get("id"),
                    "locator": f"{PIN_CSV_CLOCK_METADATA_PATH}#sources[{env_i}]",
                }
                if spreads is None:
                    excluded.append({**base, "reason": "no spreads market_last_update"})
                    continue
                got += 1
                rows.append(
                    {
                        **base,
                        "book_last_update": book.get("last_update"),
                        "commence_time": event.get("commence_time"),
                        "endpoint": source.get("endpoint"),
                        "market_key": "spreads",
                        "market_last_update": spreads.get("last_update"),
                        "next_timestamp": source.get("next_timestamp"),
                        "payload_timestamp": source.get("payload_timestamp"),
                        "previous_timestamp": source.get("previous_timestamp"),
                        "pulled_at": source.get("pulled_at"),
                        "request_date": source.get("request_date"),
                    }
                )
        if got != claimed:
            raise OwnedMarketRefuse(
                f"sources[{env_i}] selected_csv_book_quote_n {claimed} != expanded {got}"
            )
    if len(rows) != PIN_CSV_SELECTED_N:
        raise OwnedMarketRefuse(f"selected associations {len(rows)} != {PIN_CSV_SELECTED_N}")
    return rows


def build_clock_lineage_ledger(repo_root: Path) -> dict[str, Any]:
    staged = repo_root / PIN_CSV_CLOCK_METADATA_PATH
    raw = verify_staged_metadata(staged)
    doc = json.loads(raw.decode("utf-8"))
    _require_no_values(doc, where="CSV_CLOCK_METADATA")
    if doc.get("codex_staging", {}).get("original_metadata_sha256") != (
        PIN_CSV_CLOCK_ORIGINAL_METADATA_SHA256
    ):
        raise OwnedMarketRefuse("original_metadata_sha256 mismatch")
    subset = expand_selected_associations(doc)

    evidenced = [
        {
            "field": "request_date",
            "mapping": "sources[].request_date",
            "n": PIN_CSV_SELECTED_N,
            "semantic": "Odds API historical as-of request clock (query time on historical endpoint)",
            "status": "EVIDENCED_ON_44",
        },
        {
            "field": "payload_timestamp",
            "mapping": "sources[].payload_timestamp",
            "n": PIN_CSV_SELECTED_N,
            "semantic": "provider historical snapshot stamp on the response envelope",
            "status": "EVIDENCED_ON_44",
        },
        {
            "field": "previous_timestamp",
            "mapping": "sources[].previous_timestamp",
            "n": PIN_CSV_SELECTED_N,
            "semantic": "provider previous historical snapshot neighbor",
            "status": "EVIDENCED_ON_44",
        },
        {
            "field": "next_timestamp",
            "mapping": "sources[].next_timestamp",
            "n": PIN_CSV_SELECTED_N,
            "semantic": "provider next historical snapshot neighbor",
            "status": "EVIDENCED_ON_44",
        },
        {
            "field": "book.last_update",
            "mapping": "matching_events_metadata[].books_metadata[].last_update",
            "n": PIN_CSV_SELECTED_N,
            "semantic": "provider book-update stamp inside the historical snapshot",
            "status": "EVIDENCED_ON_44",
        },
        {
            "field": "market_last_updates[spreads].last_update",
            "mapping": "books_metadata[].market_last_updates[key=spreads].last_update",
            "n": PIN_CSV_SELECTED_N,
            "semantic": "provider spreads market-update stamp inside the historical snapshot",
            "status": "EVIDENCED_ON_44",
        },
        {
            "field": "commence_time",
            "mapping": "matching_events_metadata[].commence_time",
            "n": PIN_CSV_SELECTED_N,
            "semantic": "provider event commence (kickoff) on the historical envelope",
            "status": "EVIDENCED_ON_44",
        },
        {
            "field": "pulled_at",
            "mapping": "sources[].pulled_at",
            "n": PIN_CSV_SELECTED_N,
            "semantic": "download/retrieval clock (2026-08-18). NOT contemporaneous model availability",
            "status": "EVIDENCED_AS_DOWNLOAD_ONLY",
        },
        {
            "field": "path",
            "mapping": "sources[].path",
            "n": 3,
            "semantic": "repo-style raw/ locator (paths-only transform)",
            "status": "EVIDENCED_ON_3_ENVELOPES",
        },
    ]

    unresolved = [
        {
            "field": "publication_timestamp_status",
            "locator": FREEZE_LIMITATIONS_LOCATOR,
            "reason": "envelope association does not close freeze publication timestamp verification",
            "status": "HOLD_UNVERIFIED",
        },
        {
            "field": "observation_timestamp_status",
            "locator": FREEZE_LIMITATIONS_LOCATOR,
            "reason": "envelope association does not close freeze observation timestamp verification",
            "status": "HOLD_UNVERIFIED",
        },
        {
            "field": "event_id → selected-187 game_id / JSONL row",
            "locator": f"{PIN_CSV_CLOCK_METADATA_PATH}#matching_events_metadata[].id vs {PIN_OWNED_HISTORY}:{PIN_FREEZE_PATH}#intersection.games[].quotes.game_id",
            "reason": "Odds API event ids do not overlap freeze game_ids; no identity join in this metadata",
            "status": "UNRESOLVED_MAPPING",
        },
        {
            "field": "captured_at|available_at|observed_at on JSONL quotes",
            "locator": f"{PIN_OWNED_HISTORY}:ADMISSIBLE_QUOTES_B1.jsonl / freeze quotes",
            "reason": "44 CSV associations do not prove JSONL clock fields; 143 remain unknown",
            "status": "UNRESOLVED",
        },
        {
            "field": "143 JSONL unknown clocks",
            "locator": f"187 selected identities − {PIN_CSV_SELECTED_N} CSV associations = {PIN_JSONL_UNKNOWN_N}",
            "reason": "preserved unknown absent actual proof; metadata evidence_limit states this",
            "status": "PRESERVED_UNKNOWN",
        },
        {
            "field": "contemporaneous model availability",
            "locator": "sources[].pulled_at vs sources[].request_date / payload_timestamp",
            "reason": "provider historical timestamp is NOT contemporaneous model availability; pulled_at is 2026-08-18 retrieval",
            "status": "NOT_CAUSAL",
        },
        {
            "field": "full price/value/export lineage",
            "locator": PIN_CSV_CLOCK_METADATA_PATH,
            "reason": "metadata only; no quote lines/prices/outcomes; do not promote envelope association",
            "status": "OUT_OF_SCOPE",
        },
        {
            "field": "all-187 clock coverage",
            "locator": PIN_CSV_CLOCK_METADATA_PATH,
            "reason": f"only {PIN_CSV_SELECTED_N}/{PIN_SELECTED_187} have CSV envelope association",
            "status": "NOT_CLAIMED",
        },
    ]

    remaining_field_reasons = [
        {
            "n": PIN_JSONL_UNKNOWN_N,
            "object": "selected-187 JSONL quote clocks without CSV envelope association",
            "reason": "no event_id↔game_id proof and no per-quote metadata for these 143",
        },
        {
            "n": 2,
            "object": "envelope-2 book metadata rows lacking spreads market_last_update",
            "reason": "present on matching_events_metadata but excluded from selected 44",
            "locator": f"{PIN_CSV_CLOCK_METADATA_PATH}#sources[2].matching_events_metadata[].books_metadata",
        },
        {
            "n": 400,
            "object": "missingness game_ids",
            "reason": "unchanged; this evidence does not address missing_n=400",
        },
    ]

    return {
        "cert": CERT,
        "claimed_full_lineage": False,
        "freeze_limitations_marked_verified": False,
        "n_envelopes": len(doc.get("sources") or []),
        "n_jsonl_unknown_preserved": PIN_JSONL_UNKNOWN_N,
        "n_selected_csv_associations": PIN_CSV_SELECTED_N,
        "original_metadata_sha256": PIN_CSV_CLOCK_ORIGINAL_METADATA_SHA256,
        "owned_completion_claimed": False,
        "package": PACKAGE,
        "provider_historical_timestamp_is_contemporaneous_model_availability": False,
        "evidenced": evidenced,
        "remaining_field_reasons": remaining_field_reasons,
        "scientific_hold": [
            "no outcome join",
            "no real forecast",
            "no invented clock_provenance",
            "freeze#limitations remain unverified",
        ],
        "staged_bytes": PIN_CSV_CLOCK_METADATA_BYTES,
        "staged_path": PIN_CSV_CLOCK_METADATA_PATH,
        "staged_sha256": PIN_CSV_CLOCK_METADATA_SHA256,
        "staged_sha256_match": True,
        "subset": subset,
        "ticket": "t5324u",
        "unresolved": unresolved,
    }


def write_clock_lineage_ledger(repo_root: Path) -> dict[str, Any]:
    ledger = build_clock_lineage_ledger(repo_root)
    out = repo_root / "data/ops/nfl_owned_market_v1/CLOCK_LINEAGE_LEDGER_70648.json"
    text = json.dumps(ledger, indent=2, sort_keys=True) + "\n"
    raw = text.encode("utf-8")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(raw)
    return {
        "ledger": ledger,
        "path": str(out.relative_to(repo_root)),
        "sha256": sha256_bytes(raw),
    }
