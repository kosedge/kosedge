"""AC-1 / AC-2 seal producer. Not a seal-ack.

produce_seal writes a seal artifact >=60 minutes before kickoff and leaves
an AC-2 custodian receipt slot. refuse_seal (streams.py) remains the AC-12
barrier and always raises.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional

from src.services.nfl_w8_capture.store import BundleStore
from src.services.nfl_w8_capture.timestamps import parse_utc

SEAL_MIN_LEAD = timedelta(minutes=60)
SEALS_DIR = "seals"
UNSET = "UNSET"


class SealWindowError(RuntimeError):
    """Raised when produce_seal is attempted inside the 60-minute window."""


def _aware(value: datetime) -> datetime:
    parsed = parse_utc(value)
    if parsed is None:
        raise SealWindowError("kickoff_utc / now_utc must be a parseable UTC timestamp")
    return parsed


def produce_seal(
    store: BundleStore,
    *,
    game_id: str,
    kickoff_utc: datetime,
    now_utc: datetime,
    artifact_shas: Optional[Mapping[str, str]] = None,
    custodian_receipt_id: str = "",
    actor: str = "nfl_w8_capture",
) -> dict[str, Any]:
    """Write an AC-1 seal + AC-2 receipt slot. Does not seal-ack."""
    kickoff = _aware(kickoff_utc)
    now = _aware(now_utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    lead = kickoff - now
    if lead < SEAL_MIN_LEAD:
        raise SealWindowError(
            "AC-1 seal requires >=60 minutes before kickoff; "
            f"lead={lead.total_seconds():.0f}s"
        )
    receipt_id = str(custodian_receipt_id or "").strip() or UNSET
    receipt = {
        "slot": "AC-2",
        "receipt_id": receipt_id,
        "status": "SLOT_EMPTY" if receipt_id == UNSET else "RECEIPT_RECORDED",
        "seal_ack": "CURSOR_CANNOT_SEAL_ACK",
        "note": "Custodian fills receipt_id. Cursor cannot seal-ack (AC-12).",
    }
    safe = "".join(ch if ch.isalnum() or ch in "-_@" else "_" for ch in game_id)
    relpath = f"{SEALS_DIR}/{safe}.seal.json"
    payload = {
        "ac_1": True,
        "ac_2_custodian_receipt_slot": True,
        "game_id": game_id,
        "sealed_at": now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "kickoff_utc": kickoff.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "lead_seconds": int(lead.total_seconds()),
        "artifact_shas": dict(artifact_shas or {}),
        "custodian_receipt": receipt,
        "seal_ack": "CURSOR_CANNOT_SEAL_ACK",
        "producer": "nfl_w8_capture.seal.produce_seal",
        "note": "Seal producer only. refuse_seal remains the AC-12 ack barrier.",
    }
    store.write_new_file(relpath, payload, actor=actor, note=f"seal:{game_id}")
    return {"relpath": relpath, **payload}
