"""Isolated nfl_owned_market_v1 tests. CERT=0. Synthetic only."""

from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.services.nfl_owned_market_v1.constants import (
    BOOK_ID,
    CERT,
    PINNED_CUTOFF_UTC,
    PINNED_GAME_ID,
    PROFILE_OWNED_MARKET_TRACE,
    PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
)
from src.services.nfl_owned_market_v1.hashing import require_sha256_hex
from src.services.nfl_owned_market_v1.produce import (
    build_events_document,
    build_trace_document,
    produce_artifacts,
)
from src.services.nfl_owned_market_v1.profiles import handoff_interface
from src.services.nfl_owned_market_v1.refuse import OwnedMarketRefuse
from src.services.nfl_owned_market_v1.schema import schema_hash
from src.services.nfl_owned_market_v1.validate import (
    fmt_utc,
    parse_utc,
    rehash_document,
    validate_join,
    validate_owned_market_trace,
    validate_synthetic_market_economic_events,
)


def test_produce_and_join_happy_path(tmp_path: Path) -> None:
    artifacts = produce_artifacts(repo_root=tmp_path)
    assert artifacts["trace_report"]["validated"] is True
    assert artifacts["events_report"]["validated"] is True
    assert artifacts["join_report"]["joined"] is True
    assert artifacts["join_report"]["game_id"] == PINNED_GAME_ID
    assert artifacts["trace_report"]["n_observations"] == 3
    assert artifacts["events_report"]["n_events"] == 3
    for digest in (
        artifacts["hashes_doc"]["profiles"][PROFILE_OWNED_MARKET_TRACE]["fixture_sha256"],
        artifacts["hashes_doc"]["profiles"][PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS][
            "fixture_sha256"
        ],
        artifacts["hashes_doc"]["profiles"][PROFILE_OWNED_MARKET_TRACE]["schema_sha256"],
        artifacts["hashes_doc"]["profiles"][PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS][
            "schema_sha256"
        ],
    ):
        require_sha256_hex(digest, name="artifact")


def test_handoff_names_schemas_hashes(tmp_path: Path) -> None:
    artifacts = produce_artifacts(repo_root=tmp_path)
    interface = handoff_interface(artifacts)
    assert interface["worker"] == "B"
    assert interface["cert"] == CERT
    assert interface["ready_for_A"] is True
    assert set(interface["profiles"]) == {
        PROFILE_OWNED_MARKET_TRACE,
        PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
    }
    assert interface["profiles"][PROFILE_OWNED_MARKET_TRACE]["schema_hash"] == schema_hash(
        PROFILE_OWNED_MARKET_TRACE
    )
    assert interface["source_pins"]["pr_714_is_base"] is False


def test_cutoff_minus_one_second_valid() -> None:
    trace = build_trace_document()
    seal = parse_utc(PINNED_CUTOFF_UTC, name="seal")
    edge = fmt_utc(seal - timedelta(seconds=1))
    obs = trace["observations"][-1]
    obs["available_at"] = edge
    obs["observed_at"] = edge
    rehash_document(trace, kind="trace")
    report = validate_owned_market_trace(trace)
    assert report["validated"] is True


@pytest.mark.parametrize("delta", [0, 1])
def test_seal_or_after_refused(delta: int) -> None:
    trace = build_trace_document()
    seal = parse_utc(PINNED_CUTOFF_UTC, name="seal")
    late = fmt_utc(seal + timedelta(seconds=delta))
    obs = trace["observations"][-1]
    obs["available_at"] = late
    obs["observed_at"] = late
    rehash_document(trace, kind="trace")
    with pytest.raises(OwnedMarketRefuse, match="seal"):
        validate_owned_market_trace(trace)


def test_refuse_real_book() -> None:
    trace = build_trace_document()
    trace["envelope"]["book_id"] = "draftkings"
    rehash_document(trace, kind="trace")
    with pytest.raises(OwnedMarketRefuse, match="book"):
        validate_owned_market_trace(trace)


def test_refuse_play_lean_stake() -> None:
    trace = build_trace_document()
    trace["play"] = "home"
    with pytest.raises(OwnedMarketRefuse, match="forbidden"):
        validate_owned_market_trace(trace)


def test_refuse_non_synthetic_game_id() -> None:
    trace = build_trace_document()
    trace["envelope"]["game_id"] = "2024_01_KC_SF"
    rehash_document(trace, kind="trace")
    with pytest.raises(OwnedMarketRefuse, match="SYNTHETIC"):
        validate_owned_market_trace(trace)


def test_refuse_wrong_row_hash() -> None:
    events = build_events_document()
    events["events"][0]["source_byte_hash"] = "ab" * 32
    with pytest.raises(OwnedMarketRefuse, match="source_byte_hash"):
        validate_synthetic_market_economic_events(events)


def test_refuse_bool_as_number() -> None:
    events = build_events_document()
    events["events"][0]["magnitude"] = True
    rehash_document(events, kind="events")
    with pytest.raises(OwnedMarketRefuse, match="bool-as-number"):
        validate_synthetic_market_economic_events(events)


def test_join_requires_event_to_precede_observation() -> None:
    trace = build_trace_document()
    events = build_events_document()
    events["events"][0]["available_at"] = "2026-12-06T15:10:00Z"
    events["events"][0]["observed_at"] = "2026-12-06T15:10:00Z"
    rehash_document(events, kind="events")
    with pytest.raises(OwnedMarketRefuse, match="precede"):
        validate_join(trace, events)


def test_join_missing_event_refused() -> None:
    trace = build_trace_document()
    events = build_events_document()
    events["events"][0]["event_id"] = "SYNTHETIC_EVT_999"
    rehash_document(events, kind="events")
    with pytest.raises(OwnedMarketRefuse, match="missing from events"):
        validate_join(trace, events)


def test_schema_hashes_stable() -> None:
    a = schema_hash(PROFILE_OWNED_MARKET_TRACE)
    b = schema_hash(PROFILE_OWNED_MARKET_TRACE)
    c = schema_hash(PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS)
    require_sha256_hex(a, name="schema_trace")
    require_sha256_hex(c, name="schema_events")
    assert a == b
    assert a != c


def test_in_memory_builders_validate() -> None:
    trace = build_trace_document()
    events = build_events_document()
    assert validate_owned_market_trace(trace)["validated"] is True
    assert validate_synthetic_market_economic_events(events)["validated"] is True
    assert validate_join(trace, events)["joined"] is True
    assert copy.deepcopy(trace)["envelope"]["book_id"] == BOOK_ID


def test_seal_equals_cutoff_equals_ko_minus_60() -> None:
    kickoff = parse_utc("2026-12-06T18:00:00Z", name="ko")
    cutoff = parse_utc(PINNED_CUTOFF_UTC, name="cutoff")
    assert cutoff == kickoff - timedelta(minutes=60)
    assert PINNED_CUTOFF_UTC == "2026-12-06T17:00:00Z"
    assert cutoff.tzinfo == timezone.utc
    assert isinstance(cutoff, datetime)
