"""Fail-closed validators for the two B profiles. CERT=0.

Timing law inherited from R6 A 54b08a30: seal_utc = cutoff_utc = kickoff-60.
available_at and observed_at must strictly precede seal. Boundary: cutoff-1s
valid; exact seal / +1s refuse.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from src.services.nfl_owned_market_v1.constants import (
    BOOK_ID,
    CERT,
    CHANNEL,
    CODE_BIND_FILES,
    DATA_LABEL,
    EFFECT_CHANNELS,
    ENVELOPE_FIELDS,
    EVENT_FIELDS,
    EVENT_TYPES,
    FORBIDDEN_BOOK_IDS,
    FORBIDDEN_OUTPUT_KEYS,
    IDENTITY_KIND,
    KO_MINUS_MINUTES,
    MARKETS,
    OBS_FIELDS,
    OBS_SOURCE,
    OBS_STATUS,
    PACKAGE,
    PINNED_AWAY,
    PINNED_GAME_ID,
    PINNED_HOME,
    PINNED_SEASON,
    PINNED_SEASON_TYPE,
    PINNED_WEEK,
    PLAYER_SLOTS,
    PROFILE_OWNED_MARKET_TRACE,
    PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
    SCHEMA_OWNED_MARKET_TRACE,
    SCHEMA_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
    SIDES,
    SYNTHETIC_TOKEN,
    TEAMS,
    TIMING_FIELDS,
)
from src.services.nfl_owned_market_v1.hashing import (
    body_without_hash,
    canonical_sha256,
    require_sha256_hex,
    sha256_file,
)
from src.services.nfl_owned_market_v1.refuse import OwnedMarketRefuse


def parse_utc(raw: Any, *, name: str) -> datetime:
    text = str(raw or "").strip()
    if not text or text.lower() in {"not-a-time", "none", "null"}:
        raise OwnedMarketRefuse(f"{name} is not a time: {raw!r}")
    if text.endswith("Z") or text.endswith("z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError as exc:
        raise OwnedMarketRefuse(f"{name} is not a time: {raw!r}") from exc
    if dt.tzinfo is None:
        raise OwnedMarketRefuse(f"{name} naive datetime refused: {raw!r}")
    return dt.astimezone(timezone.utc)


def fmt_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _require_mapping(value: Any, *, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise OwnedMarketRefuse(f"{name} is missing/invalid")
    return dict(value)


def _require_nonempty_str(value: Any, *, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OwnedMarketRefuse(f"{name} must be a non-empty string")
    return value


def _require_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise OwnedMarketRefuse(f"{name} is not an int (bool-as-number refused)")
    return int(value)


def _require_finite_number(value: Any, *, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OwnedMarketRefuse(f"{name} is not a number (bool-as-number refused)")
    number = float(value)
    if not math.isfinite(number):
        raise OwnedMarketRefuse(f"{name} is not finite")
    return number


def _refuse_forbidden_keys(payload: Mapping[str, Any], *, name: str) -> None:
    lowered = {str(key).lower() for key in payload}
    hit = sorted(lowered & FORBIDDEN_OUTPUT_KEYS)
    if hit:
        raise OwnedMarketRefuse(f"{name} carries forbidden output keys {hit}")


def _refuse_real_book(book_id: str) -> None:
    if book_id.strip().lower() in FORBIDDEN_BOOK_IDS:
        raise OwnedMarketRefuse(f"real/paid book_id refused: {book_id!r}")
    if book_id != BOOK_ID:
        raise OwnedMarketRefuse(f"book_id must be {BOOK_ID}: {book_id!r}")


def observation_content_hash(obs: Mapping[str, Any]) -> str:
    return canonical_sha256(body_without_hash(dict(obs)))


def event_content_hash(event: Mapping[str, Any]) -> str:
    return canonical_sha256(body_without_hash(dict(event)))


def document_content_hash(doc: Mapping[str, Any]) -> str:
    return canonical_sha256(body_without_hash(dict(doc)))


def code_content_hash() -> str:
    here = Path(__file__).resolve().parent
    rows: list[str] = []
    for name in CODE_BIND_FILES:
        path = here / name
        if not path.is_file():
            raise OwnedMarketRefuse(f"code bind missing {path}")
        rows.append(f"nfl_owned_market_v1/{name}={sha256_file(path)}")
    digest = canonical_sha256(rows)
    require_sha256_hex(digest, name="code_hash")
    return digest


def _validate_envelope(env: Mapping[str, Any]) -> dict[str, Any]:
    missing = [name for name in ENVELOPE_FIELDS if name not in env or env.get(name) in (None, "")]
    if missing:
        raise OwnedMarketRefuse(f"envelope missing {missing}")
    extra = sorted(set(env) - set(ENVELOPE_FIELDS))
    if extra:
        raise OwnedMarketRefuse(f"envelope unknown fields {extra}")
    game_id = _require_nonempty_str(env.get("game_id"), name="envelope.game_id")
    if SYNTHETIC_TOKEN not in game_id:
        raise OwnedMarketRefuse("envelope.game_id is not SYNTHETIC")
    season = _require_int(env.get("season"), name="envelope.season")
    week = _require_int(env.get("week"), name="envelope.week")
    season_type = _require_nonempty_str(env.get("season_type"), name="envelope.season_type").upper()
    if season_type != PINNED_SEASON_TYPE:
        raise OwnedMarketRefuse(f"envelope.season_type must be REG: {season_type!r}")
    if week != PINNED_WEEK or season != PINNED_SEASON:
        raise OwnedMarketRefuse(
            f"envelope must stay on fictional week-99 cohort "
            f"({PINNED_SEASON}/{PINNED_WEEK}); got {season}/{week}"
        )
    if game_id != PINNED_GAME_ID:
        raise OwnedMarketRefuse(f"envelope.game_id must be {PINNED_GAME_ID}")
    home = _require_nonempty_str(env.get("home_team"), name="envelope.home_team")
    away = _require_nonempty_str(env.get("away_team"), name="envelope.away_team")
    if home != PINNED_HOME or away != PINNED_AWAY:
        raise OwnedMarketRefuse("envelope teams must be fictional AAA/ZZZ")
    identity = _require_nonempty_str(env.get("identity_kind"), name="envelope.identity_kind")
    if identity != IDENTITY_KIND or SYNTHETIC_TOKEN not in identity:
        raise OwnedMarketRefuse("bad SYNTHETIC identity_kind")
    book_id = _require_nonempty_str(env.get("book_id"), name="envelope.book_id")
    _refuse_real_book(book_id)
    _require_nonempty_str(env.get("venue_id"), name="envelope.venue_id")
    kickoff = parse_utc(env.get("kickoff_utc"), name="envelope.kickoff_utc")
    return {
        "game_id": game_id,
        "season": season,
        "week": week,
        "season_type": season_type,
        "home_team": home,
        "away_team": away,
        "kickoff": kickoff,
        "book_id": book_id,
    }


def _validate_timing(timing: Mapping[str, Any], *, kickoff: datetime) -> dict[str, Any]:
    missing = [name for name in TIMING_FIELDS if name not in timing]
    if missing:
        raise OwnedMarketRefuse(f"timing missing {missing}")
    extra = sorted(set(timing) - set(TIMING_FIELDS))
    if extra:
        raise OwnedMarketRefuse(f"timing unknown fields {extra}")
    ko = parse_utc(timing.get("kickoff_utc"), name="timing.kickoff_utc")
    if ko != kickoff:
        raise OwnedMarketRefuse("timing.kickoff_utc != envelope.kickoff_utc")
    cutoff = parse_utc(timing.get("cutoff_utc"), name="timing.cutoff_utc")
    seal = parse_utc(timing.get("seal_utc"), name="timing.seal_utc")
    expected = kickoff - timedelta(minutes=KO_MINUS_MINUTES)
    if cutoff != expected:
        raise OwnedMarketRefuse(
            f"cutoff_utc must equal kickoff-{KO_MINUS_MINUTES}: "
            f"{fmt_utc(cutoff)} != {fmt_utc(expected)}"
        )
    if seal != cutoff:
        raise OwnedMarketRefuse("seal_utc must equal cutoff_utc")
    minutes = _require_int(timing.get("ko_minus_minutes"), name="timing.ko_minus_minutes")
    if minutes != KO_MINUS_MINUTES:
        raise OwnedMarketRefuse(f"ko_minus_minutes must be {KO_MINUS_MINUTES}")
    return {"kickoff": kickoff, "cutoff": cutoff, "seal": seal}


def _precede_seal(available: datetime, observed: datetime, seal: datetime, *, name: str) -> None:
    if available > observed:
        raise OwnedMarketRefuse(f"{name} available_at after observed_at")
    if available >= seal or observed >= seal:
        kind = "equal-to-seal" if available == seal or observed == seal else "late vs KO"
        raise OwnedMarketRefuse(
            f"{name} {kind}: must strictly precede seal/cutoff "
            f"{fmt_utc(seal)} (seal_utc=cutoff_utc=KO−{KO_MINUS_MINUTES})"
        )


def _validate_observation(obs: Mapping[str, Any], *, index: int, seal: datetime) -> dict[str, Any]:
    name = f"observations[{index}]"
    _refuse_forbidden_keys(obs, name=name)
    missing = [field for field in OBS_FIELDS if field not in obs]
    if missing:
        raise OwnedMarketRefuse(f"{name} missing {missing}")
    extra = sorted(set(obs) - set(OBS_FIELDS))
    if extra:
        raise OwnedMarketRefuse(f"{name} unknown fields {extra}")
    seq = _require_int(obs.get("seq"), name=f"{name}.seq")
    if seq != index + 1:
        raise OwnedMarketRefuse(f"{name}.seq must be {index + 1}")
    market = _require_nonempty_str(obs.get("market"), name=f"{name}.market")
    if market not in MARKETS:
        raise OwnedMarketRefuse(f"{name}.market not typed: {market!r}")
    side = _require_nonempty_str(obs.get("side"), name=f"{name}.side")
    if side not in SIDES:
        raise OwnedMarketRefuse(f"{name}.side not typed: {side!r}")
    if market == "ml":
        if obs.get("line") is not None:
            raise OwnedMarketRefuse(f"{name}.line must be null for ml")
    else:
        _require_finite_number(obs.get("line"), name=f"{name}.line")
    _require_int(obs.get("price"), name=f"{name}.price")
    if str(obs.get("status") or "") != OBS_STATUS:
        raise OwnedMarketRefuse(f"{name}.status is not {OBS_STATUS}")
    if str(obs.get("source") or "") != OBS_SOURCE:
        raise OwnedMarketRefuse(f"{name}.source is not {OBS_SOURCE}")
    available = parse_utc(obs.get("available_at"), name=f"{name}.available_at")
    observed = parse_utc(obs.get("observed_at"), name=f"{name}.observed_at")
    _precede_seal(available, observed, seal, name=name)
    caused = obs.get("caused_by_event_id")
    if caused is not None:
        caused_s = _require_nonempty_str(caused, name=f"{name}.caused_by_event_id")
        if SYNTHETIC_TOKEN not in caused_s:
            raise OwnedMarketRefuse(f"{name}.caused_by_event_id is not SYNTHETIC")
    else:
        caused_s = None
    try:
        claimed = require_sha256_hex(obs.get("source_byte_hash"), name=f"{name}.source_byte_hash")
    except ValueError as exc:
        raise OwnedMarketRefuse(str(exc)) from exc
    actual = observation_content_hash(obs)
    if claimed != actual:
        raise OwnedMarketRefuse(f"{name} wrong source_byte_hash")
    return {
        "seq": seq,
        "market": market,
        "available": available,
        "caused_by_event_id": caused_s,
    }


def _validate_event(event: Mapping[str, Any], *, index: int, seal: datetime) -> dict[str, Any]:
    name = f"events[{index}]"
    _refuse_forbidden_keys(event, name=name)
    missing = [field for field in EVENT_FIELDS if field not in event]
    if missing:
        raise OwnedMarketRefuse(f"{name} missing {missing}")
    extra = sorted(set(event) - set(EVENT_FIELDS))
    if extra:
        raise OwnedMarketRefuse(f"{name} unknown fields {extra}")
    event_id = _require_nonempty_str(event.get("event_id"), name=f"{name}.event_id")
    if not event_id.startswith("SYNTHETIC_EVT_"):
        raise OwnedMarketRefuse(f"{name}.event_id must be SYNTHETIC_EVT_*")
    event_type = _require_nonempty_str(event.get("event_type"), name=f"{name}.event_type")
    if event_type not in EVENT_TYPES:
        raise OwnedMarketRefuse(f"{name}.event_type not typed: {event_type!r}")
    channel = _require_nonempty_str(event.get("effect_channel"), name=f"{name}.effect_channel")
    if channel not in EFFECT_CHANNELS:
        raise OwnedMarketRefuse(f"{name}.effect_channel not typed: {channel!r}")
    team = _require_nonempty_str(event.get("team"), name=f"{name}.team")
    if team not in TEAMS:
        raise OwnedMarketRefuse(f"{name}.team not typed: {team!r}")
    slot = _require_nonempty_str(event.get("player_slot"), name=f"{name}.player_slot")
    if slot not in PLAYER_SLOTS:
        raise OwnedMarketRefuse(f"{name}.player_slot not typed: {slot!r}")
    _require_finite_number(event.get("magnitude"), name=f"{name}.magnitude")
    payload = event.get("payload")
    if not isinstance(payload, Mapping):
        raise OwnedMarketRefuse(f"{name}.payload must be an object")
    _refuse_forbidden_keys(payload, name=f"{name}.payload")
    _require_nonempty_str(event.get("source"), name=f"{name}.source")
    available = parse_utc(event.get("available_at"), name=f"{name}.available_at")
    observed = parse_utc(event.get("observed_at"), name=f"{name}.observed_at")
    _precede_seal(available, observed, seal, name=name)
    try:
        claimed = require_sha256_hex(event.get("source_byte_hash"), name=f"{name}.source_byte_hash")
    except ValueError as exc:
        raise OwnedMarketRefuse(str(exc)) from exc
    actual = event_content_hash(event)
    if claimed != actual:
        raise OwnedMarketRefuse(f"{name} wrong source_byte_hash")
    return {"event_id": event_id, "available": available}


def _validate_document_prefix(
    doc: Mapping[str, Any],
    *,
    profile: str,
    schema_version: str,
) -> dict[str, Any]:
    if not isinstance(doc, Mapping):
        raise OwnedMarketRefuse("document is missing/invalid")
    _refuse_forbidden_keys(doc, name="document")
    cert = doc.get("cert")
    if isinstance(cert, bool) or not isinstance(cert, int) or cert != CERT:
        raise OwnedMarketRefuse("cert must be 0")
    if str(doc.get("package") or "") != PACKAGE:
        raise OwnedMarketRefuse("package mismatch")
    if str(doc.get("data_label") or "") != DATA_LABEL:
        raise OwnedMarketRefuse("data_label must be SYNTHETIC")
    if str(doc.get("channel") or "") != CHANNEL:
        raise OwnedMarketRefuse("channel must be SYNTHETIC")
    if str(doc.get("profile") or "") != profile:
        raise OwnedMarketRefuse(f"profile must be {profile}")
    if str(doc.get("schema_version") or "") != schema_version:
        raise OwnedMarketRefuse(f"schema_version must be {schema_version}")
    env = _validate_envelope(_require_mapping(doc.get("envelope"), name="envelope"))
    timing = _validate_timing(
        _require_mapping(doc.get("timing"), name="timing"),
        kickoff=env["kickoff"],
    )
    return {"env": env, "timing": timing}


def _bind_document_hash(doc: Mapping[str, Any], *, name: str) -> str:
    try:
        claimed = require_sha256_hex(doc.get("source_byte_hash"), name=f"{name}.source_byte_hash")
    except ValueError as exc:
        raise OwnedMarketRefuse(str(exc)) from exc
    actual = document_content_hash(doc)
    if claimed != actual:
        raise OwnedMarketRefuse(f"{name} wrong source_byte_hash")
    return actual


def validate_owned_market_trace(doc: Mapping[str, Any]) -> dict[str, Any]:
    prefix = _validate_document_prefix(
        doc,
        profile=PROFILE_OWNED_MARKET_TRACE,
        schema_version=SCHEMA_OWNED_MARKET_TRACE,
    )
    trace_id = _require_nonempty_str(doc.get("trace_id"), name="trace_id")
    if SYNTHETIC_TOKEN not in trace_id:
        raise OwnedMarketRefuse("trace_id is not SYNTHETIC")
    observations = doc.get("observations")
    if not isinstance(observations, list) or not observations:
        raise OwnedMarketRefuse("observations is missing/invalid")
    seal = prefix["timing"]["seal"]
    parsed: list[dict[str, Any]] = []
    for index, obs in enumerate(observations):
        if not isinstance(obs, Mapping):
            raise OwnedMarketRefuse(f"observations[{index}] is missing/invalid")
        parsed.append(_validate_observation(obs, index=index, seal=seal))
    for prev, cur in zip(parsed, parsed[1:]):
        if cur["available"] < prev["available"]:
            raise OwnedMarketRefuse("observations are not time-ordered")
    doc_hash = _bind_document_hash(doc, name="owned_market_trace")
    return {
        "profile": PROFILE_OWNED_MARKET_TRACE,
        "validated": True,
        "cert": CERT,
        "document_hash": doc_hash,
        "n_observations": len(parsed),
        "seal_utc": fmt_utc(seal),
        "cutoff_utc": fmt_utc(prefix["timing"]["cutoff"]),
        "kickoff_utc": fmt_utc(prefix["timing"]["kickoff"]),
        "game_id": prefix["env"]["game_id"],
        "caused_by_event_ids": [
            row["caused_by_event_id"] for row in parsed if row["caused_by_event_id"]
        ],
        "available_at": [fmt_utc(row["available"]) for row in parsed],
    }


def validate_synthetic_market_economic_events(doc: Mapping[str, Any]) -> dict[str, Any]:
    prefix = _validate_document_prefix(
        doc,
        profile=PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
        schema_version=SCHEMA_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
    )
    batch_id = _require_nonempty_str(doc.get("batch_id"), name="batch_id")
    if SYNTHETIC_TOKEN not in batch_id:
        raise OwnedMarketRefuse("batch_id is not SYNTHETIC")
    events = doc.get("events")
    if not isinstance(events, list) or not events:
        raise OwnedMarketRefuse("events is missing/invalid")
    seal = prefix["timing"]["seal"]
    parsed: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, event in enumerate(events):
        if not isinstance(event, Mapping):
            raise OwnedMarketRefuse(f"events[{index}] is missing/invalid")
        row = _validate_event(event, index=index, seal=seal)
        if row["event_id"] in seen:
            raise OwnedMarketRefuse(f"duplicate event_id {row['event_id']}")
        seen.add(row["event_id"])
        parsed.append(row)
    for prev, cur in zip(parsed, parsed[1:]):
        if cur["available"] < prev["available"]:
            raise OwnedMarketRefuse("events are not time-ordered")
    doc_hash = _bind_document_hash(doc, name="synthetic_market_economic_events")
    return {
        "profile": PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
        "validated": True,
        "cert": CERT,
        "document_hash": doc_hash,
        "n_events": len(parsed),
        "event_ids": [row["event_id"] for row in parsed],
        "seal_utc": fmt_utc(seal),
        "cutoff_utc": fmt_utc(prefix["timing"]["cutoff"]),
        "kickoff_utc": fmt_utc(prefix["timing"]["kickoff"]),
        "game_id": prefix["env"]["game_id"],
    }


def validate_join(trace: Mapping[str, Any], events: Mapping[str, Any]) -> dict[str, Any]:
    """Join contract for A. Does not register a shared-gate profile."""
    t = validate_owned_market_trace(trace)
    e = validate_synthetic_market_economic_events(events)
    if t["game_id"] != e["game_id"]:
        raise OwnedMarketRefuse("join game_id mismatch")
    if t["seal_utc"] != e["seal_utc"]:
        raise OwnedMarketRefuse("join seal_utc mismatch")
    event_by_id = {
        ev["event_id"]: ev
        for ev in events.get("events", [])
        if isinstance(ev, Mapping)
    }
    for obs in trace.get("observations", []):
        if not isinstance(obs, Mapping):
            continue
        caused = obs.get("caused_by_event_id")
        if not caused:
            continue
        if caused not in event_by_id:
            raise OwnedMarketRefuse(f"caused_by_event_id {caused} missing from events")
        ev = event_by_id[caused]
        ev_avail = parse_utc(ev.get("available_at"), name="join.event.available_at")
        obs_avail = parse_utc(obs.get("available_at"), name="join.obs.available_at")
        if ev_avail >= obs_avail:
            raise OwnedMarketRefuse(
                f"event {caused} must strictly precede observation seq={obs.get('seq')}"
            )
    return {
        "joined": True,
        "cert": CERT,
        "game_id": t["game_id"],
        "n_observations": t["n_observations"],
        "n_events": e["n_events"],
        "bound_event_ids": t["caused_by_event_ids"],
        "trace_hash": t["document_hash"],
        "events_hash": e["document_hash"],
    }


def rehash_row(row: dict[str, Any]) -> dict[str, Any]:
    row["source_byte_hash"] = canonical_sha256(body_without_hash(row))
    return row


def rehash_document(doc: dict[str, Any], *, kind: str) -> dict[str, Any]:
    if kind == "trace":
        for obs in doc.get("observations", []):
            if isinstance(obs, dict):
                rehash_row(obs)
    elif kind == "events":
        for event in doc.get("events", []):
            if isinstance(event, dict):
                rehash_row(event)
    else:
        raise OwnedMarketRefuse(f"unknown rehash kind {kind!r}")
    doc["source_byte_hash"] = document_content_hash(doc)
    return doc
