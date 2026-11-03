"""Fail-closed validators. Profiles stay separate. CERT=0."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from src.services.nfl_owned_market_v1.arithmetic import portfolio_roi, settle_ticket
from src.services.nfl_owned_market_v1.constants import (
    BOOK_ID,
    CERT,
    CODE_BIND_FILES,
    ENVELOPE_FIELDS,
    FORBIDDEN_BOOK_IDS,
    FORBIDDEN_OUTPUT_KEYS,
    IDENTITY_KIND,
    KO_MINUS_MINUTES,
    PACKAGE,
    PINNED_AWAY,
    PINNED_GAME_ID,
    PINNED_HOME,
    PINNED_SEASON,
    PINNED_SEASON_TYPE,
    PINNED_WEEK,
    PROFILE_OWNED_MARKET_TRACE,
    PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
    ROLE_FICTIONAL_ECONOMIC,
    ROLE_OWNED_READINESS,
    SCHEMA_OWNED_MARKET_TRACE,
    SCHEMA_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
    SYNTHETIC_TOKEN,
    TICKET_FIELDS,
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


def _refuse_forbidden_keys(payload: Mapping[str, Any], *, name: str) -> None:
    lowered = {str(key).lower() for key in payload}
    hit = sorted(lowered & FORBIDDEN_OUTPUT_KEYS)
    if hit:
        raise OwnedMarketRefuse(f"{name} carries forbidden output keys {hit}")


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


def _bind_document_hash(doc: Mapping[str, Any], *, name: str) -> str:
    try:
        claimed = require_sha256_hex(doc.get("source_byte_hash"), name=f"{name}.source_byte_hash")
    except ValueError as exc:
        raise OwnedMarketRefuse(str(exc)) from exc
    actual = document_content_hash(doc)
    if claimed != actual:
        raise OwnedMarketRefuse(f"{name} wrong source_byte_hash")
    return actual


def _validate_envelope(env: Mapping[str, Any]) -> dict[str, Any]:
    missing = [name for name in ENVELOPE_FIELDS if name not in env or env.get(name) in (None, "")]
    if missing:
        raise OwnedMarketRefuse(f"envelope missing {missing}")
    game_id = _require_nonempty_str(env.get("game_id"), name="envelope.game_id")
    if SYNTHETIC_TOKEN not in game_id or game_id != PINNED_GAME_ID:
        raise OwnedMarketRefuse("economic envelope must stay fictional SYNTHETIC week-99")
    season = _require_int(env.get("season"), name="envelope.season")
    week = _require_int(env.get("week"), name="envelope.week")
    if season != PINNED_SEASON or week != PINNED_WEEK:
        raise OwnedMarketRefuse("economic envelope must stay fictional week-99")
    if _require_nonempty_str(env.get("season_type"), name="envelope.season_type") != PINNED_SEASON_TYPE:
        raise OwnedMarketRefuse("envelope.season_type must be REG")
    if env.get("home_team") != PINNED_HOME or env.get("away_team") != PINNED_AWAY:
        raise OwnedMarketRefuse("envelope teams must be fictional AAA/ZZZ")
    if env.get("identity_kind") != IDENTITY_KIND:
        raise OwnedMarketRefuse("bad SYNTHETIC identity_kind")
    book_id = _require_nonempty_str(env.get("book_id"), name="envelope.book_id")
    if book_id.strip().lower() in FORBIDDEN_BOOK_IDS or book_id != BOOK_ID:
        raise OwnedMarketRefuse(f"real/paid book_id refused: {book_id!r}")
    kickoff = parse_utc(env.get("kickoff_utc"), name="envelope.kickoff_utc")
    return {"game_id": game_id, "kickoff": kickoff}


def _validate_timing(timing: Mapping[str, Any], *, kickoff: datetime) -> dict[str, Any]:
    missing = [name for name in TIMING_FIELDS if name not in timing]
    if missing:
        raise OwnedMarketRefuse(f"timing missing {missing}")
    ko = parse_utc(timing.get("kickoff_utc"), name="timing.kickoff_utc")
    if ko != kickoff:
        raise OwnedMarketRefuse("timing.kickoff_utc != envelope.kickoff_utc")
    cutoff = parse_utc(timing.get("cutoff_utc"), name="timing.cutoff_utc")
    seal = parse_utc(timing.get("seal_utc"), name="timing.seal_utc")
    expected = kickoff - timedelta(minutes=KO_MINUS_MINUTES)
    if cutoff != expected or seal != cutoff:
        raise OwnedMarketRefuse("seal_utc must equal cutoff_utc = kickoff-60")
    if _require_int(timing.get("ko_minus_minutes"), name="timing.ko_minus_minutes") != KO_MINUS_MINUTES:
        raise OwnedMarketRefuse(f"ko_minus_minutes must be {KO_MINUS_MINUTES}")
    return {"kickoff": kickoff, "cutoff": cutoff, "seal": seal}


def _precede_seal(available: datetime, observed: datetime, seal: datetime, *, name: str) -> None:
    if available > observed:
        raise OwnedMarketRefuse(f"{name} available_at after observed_at")
    if available >= seal or observed >= seal:
        kind = "equal-to-seal" if available == seal or observed == seal else "late vs KO"
        raise OwnedMarketRefuse(
            f"{name} {kind}: must strictly precede seal/cutoff {fmt_utc(seal)}"
        )


def validate_owned_market_trace(doc: Mapping[str, Any]) -> dict[str, Any]:
    """OWNED_READINESS. Fictional observations are not owned completion."""
    if not isinstance(doc, Mapping):
        raise OwnedMarketRefuse("owned readiness document missing")
    _refuse_forbidden_keys(doc, name="owned_readiness")
    if "observations" in doc:
        raise OwnedMarketRefuse(
            "OWNED_MARKET_TRACE_V1 must not carry fictional observations as owned-source completion"
        )
    if doc.get("profile") != PROFILE_OWNED_MARKET_TRACE:
        raise OwnedMarketRefuse("profile must be OWNED_MARKET_TRACE_V1")
    if doc.get("profile_role") != ROLE_OWNED_READINESS:
        raise OwnedMarketRefuse("profile_role must be OWNED_READINESS")
    if doc.get("schema_version") != SCHEMA_OWNED_MARKET_TRACE:
        raise OwnedMarketRefuse("owned schema_version mismatch")
    if doc.get("package") != PACKAGE or doc.get("cert") != CERT:
        raise OwnedMarketRefuse("package/cert mismatch")
    if doc.get("owned_completion_claimed") is not False:
        raise OwnedMarketRefuse("owned_completion_claimed must be false")
    if doc.get("channel") != "OWNED_READINESS":
        raise OwnedMarketRefuse("channel must be OWNED_READINESS")
    label = str(doc.get("data_label") or "")
    if label not in {"OWNED_SOURCE_UNAVAILABLE", "OWNED_SOURCE_BOUND"}:
        raise OwnedMarketRefuse("owned data_label invalid")
    probe = _require_mapping(doc.get("probe"), name="probe")
    required = probe.get("required")
    if not isinstance(required, list) or not required:
        raise OwnedMarketRefuse("probe.required missing")
    unavailable = doc.get("unavailable")
    if not isinstance(unavailable, list):
        raise OwnedMarketRefuse("unavailable must be a list")
    if label == "OWNED_SOURCE_UNAVAILABLE" and not unavailable:
        raise OwnedMarketRefuse("UNAVAILABLE label requires unavailable[] rows")
    if label == "OWNED_SOURCE_BOUND" and unavailable:
        raise OwnedMarketRefuse("BOUND label cannot carry unavailable rows")
    holds = doc.get("scientific_hold")
    if not isinstance(holds, list) or "no outcome join" not in holds:
        raise OwnedMarketRefuse("scientific_hold must include no outcome join")
    digest = _bind_document_hash(doc, name="owned_readiness")
    return {
        "profile": PROFILE_OWNED_MARKET_TRACE,
        "profile_role": ROLE_OWNED_READINESS,
        "validated": True,
        "cert": CERT,
        "document_hash": digest,
        "owned_completion_claimed": False,
        "data_label": label,
        "n_unavailable": len(unavailable),
    }


def _validate_ticket(ticket: Mapping[str, Any], *, index: int, seal: datetime) -> dict[str, Any]:
    name = f"tickets[{index}]"
    _refuse_forbidden_keys(ticket, name=name)
    missing = [field for field in TICKET_FIELDS if field not in ticket]
    if missing:
        raise OwnedMarketRefuse(f"{name} missing {missing}")
    extra = sorted(set(ticket) - set(TICKET_FIELDS))
    if extra:
        raise OwnedMarketRefuse(f"{name} unknown fields {extra}")
    tid = _require_nonempty_str(ticket.get("ticket_id"), name=f"{name}.ticket_id")
    if not tid.startswith("SYNTHETIC_TKT_"):
        raise OwnedMarketRefuse(f"{name}.ticket_id must be SYNTHETIC_TKT_*")
    available = parse_utc(ticket.get("available_at"), name=f"{name}.available_at")
    observed = parse_utc(ticket.get("observed_at"), name=f"{name}.observed_at")
    _precede_seal(available, observed, seal, name=name)
    try:
        claimed = require_sha256_hex(ticket.get("source_byte_hash"), name=f"{name}.source_byte_hash")
    except ValueError as exc:
        raise OwnedMarketRefuse(str(exc)) from exc
    actual = canonical_sha256(body_without_hash(dict(ticket)))
    if claimed != actual:
        raise OwnedMarketRefuse(f"{name} wrong source_byte_hash")
    return settle_ticket(ticket)


def validate_synthetic_market_economic_events(doc: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(doc, Mapping):
        raise OwnedMarketRefuse("economic document missing")
    _refuse_forbidden_keys(doc, name="economic")
    if doc.get("profile") != PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS:
        raise OwnedMarketRefuse("profile must be SYNTHETIC_MARKET_ECONOMIC_EVENTS_V1")
    if doc.get("profile_role") != ROLE_FICTIONAL_ECONOMIC:
        raise OwnedMarketRefuse("profile_role must be FICTIONAL_ECONOMIC")
    if doc.get("schema_version") != SCHEMA_SYNTHETIC_MARKET_ECONOMIC_EVENTS:
        raise OwnedMarketRefuse("economic schema_version mismatch")
    if doc.get("data_label") != "SYNTHETIC" or doc.get("channel") != "SYNTHETIC":
        raise OwnedMarketRefuse("economic data_label/channel must be SYNTHETIC")
    if doc.get("cert") != CERT or doc.get("package") != PACKAGE:
        raise OwnedMarketRefuse("package/cert mismatch")
    env = _validate_envelope(_require_mapping(doc.get("envelope"), name="envelope"))
    timing = _validate_timing(_require_mapping(doc.get("timing"), name="timing"), kickoff=env["kickoff"])
    tickets = doc.get("tickets")
    if not isinstance(tickets, list) or not tickets:
        raise OwnedMarketRefuse("tickets missing")
    settled: list[dict[str, Any]] = []
    for i, ticket in enumerate(tickets):
        if not isinstance(ticket, Mapping):
            raise OwnedMarketRefuse(f"tickets[{i}] invalid")
        settled.append(_validate_ticket(ticket, index=i, seal=timing["seal"]))
    claimed_settlements = doc.get("settlements")
    if not isinstance(claimed_settlements, list) or len(claimed_settlements) != len(settled):
        raise OwnedMarketRefuse("settlements length mismatch")
    for i, (got, claimed) in enumerate(zip(settled, claimed_settlements)):
        if not isinstance(claimed, Mapping):
            raise OwnedMarketRefuse(f"settlements[{i}] invalid")
        for key in ("ats_result", "profit_u", "risked_u", "roi_eligible"):
            if claimed.get(key) != got.get(key):
                raise OwnedMarketRefuse(f"settlements[{i}].{key} does not match arithmetic")
    roi = portfolio_roi(settled)
    claimed_roi = _require_mapping(doc.get("roi"), name="roi")
    if claimed_roi.get("status") != roi["status"]:
        raise OwnedMarketRefuse("roi.status does not match arithmetic")
    if roi["status"] == "ok":
        if abs(float(claimed_roi.get("roi")) - float(roi["roi"])) > 1e-9:
            raise OwnedMarketRefuse("roi.roi does not match arithmetic")
    digest = _bind_document_hash(doc, name="economic")
    return {
        "profile": PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
        "profile_role": ROLE_FICTIONAL_ECONOMIC,
        "validated": True,
        "cert": CERT,
        "document_hash": digest,
        "n_tickets": len(settled),
        "roi": roi,
        "game_id": env["game_id"],
        "seal_utc": fmt_utc(timing["seal"]),
    }


def validate_join(owned: Mapping[str, Any], economic: Mapping[str, Any]) -> dict[str, Any]:
    """Profiles remain separate. Economic fiction is not owned completion."""
    o = validate_owned_market_trace(owned)
    e = validate_synthetic_market_economic_events(economic)
    if o["owned_completion_claimed"] is not False:
        raise OwnedMarketRefuse("join must not claim owned completion")
    if o["profile_role"] == e["profile_role"]:
        raise OwnedMarketRefuse("owned-readiness and fictional-economic roles must differ")
    return {
        "joined": False,
        "profiles_separate": True,
        "owned_completion_claimed": False,
        "cert": CERT,
        "owned_hash": o["document_hash"],
        "economic_hash": e["document_hash"],
        "note": "OWNED_READINESS and FICTIONAL_ECONOMIC stay separate; no outcome join",
    }


def rehash_row(row: dict[str, Any]) -> dict[str, Any]:
    row["source_byte_hash"] = canonical_sha256(body_without_hash(row))
    return row


def rehash_document(doc: dict[str, Any], *, kind: str) -> dict[str, Any]:
    if kind == "events":
        for ticket in doc.get("tickets", []):
            if isinstance(ticket, dict):
                rehash_row(ticket)
    elif kind == "trace":
        pass
    else:
        raise OwnedMarketRefuse(f"unknown rehash kind {kind!r}")
    doc["source_byte_hash"] = document_content_hash(doc)
    return doc
