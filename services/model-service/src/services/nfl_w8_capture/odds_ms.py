"""AC-4: Odds snapshot records. Gaps are MISSING and never backfilled."""

from __future__ import annotations

from typing import Any, Mapping, Optional

from src.services.nfl_w8_capture.chain import sha256_hex
from src.services.nfl_w8_capture.constants import MISSING, PARTIAL
from src.services.nfl_w8_capture.timeutil import parse_utc, to_iso


def snapshot_record(
    *,
    game_id: str,
    book: Optional[str],
    captured_at_utc: Optional[str],
    market: Optional[str],
    price: Optional[Any],
    source_captured_at_utc: Optional[str] = None,
    kickoff_utc: Optional[str] = None,
    mint_wall_clock: bool = False,
) -> dict[str, Any]:
    """Build one Odds row. Never invent a price."""
    missing_fields: list[str] = []
    present_fields: list[str] = []
    if not book:
        missing_fields.append("book")
    else:
        present_fields.append("book")
    if not captured_at_utc:
        missing_fields.append("captured_at_utc")
    else:
        present_fields.append("captured_at_utc")
    if not market:
        missing_fields.append("market")
    else:
        present_fields.append("market")
    if price is None or price == "":
        missing_fields.append("price")
    else:
        present_fields.append("price")
    if mint_wall_clock:
        missing_fields.append("captured_at_minted")

    if not missing_fields:
        status = "PRESENT"
    elif not present_fields:
        status = MISSING
    else:
        status = PARTIAL
    cap = parse_utc(captured_at_utc) if captured_at_utc else None
    kick = parse_utc(kickoff_utc) if kickoff_utc else None
    if status == "PRESENT" and cap is not None and kick is not None and cap >= kick:
        status = MISSING
        missing_fields.append("captured_at_not_before_kickoff")

    row = {
        "game_id": game_id,
        "book": book if book else MISSING,
        "captured_at_utc": captured_at_utc if captured_at_utc else MISSING,
        "market": market if market else MISSING,
        "price": MISSING if status == MISSING and price is None else (MISSING if price is None else price),
        "status": status,
        "missing_fields": missing_fields,
        "source_captured_at_utc": source_captured_at_utc or captured_at_utc or MISSING,
    }
    if status in {MISSING, PARTIAL} and (price is None or price == ""):
        row["price"] = MISSING
    row["record_sha256"] = sha256_hex(
        f"{row['game_id']}|{row['book']}|{row['captured_at_utc']}|{row['market']}|{row['price']}|{row['status']}".encode(
            "utf-8"
        )
    )
    if cap is not None:
        row["captured_at_utc"] = to_iso(cap)
    return row


def never_backfill(existing: Mapping[str, Any]) -> Mapping[str, Any]:
    """Identity: a MISSING row must stay MISSING."""
    if existing.get("status") == MISSING:
        return existing
    return existing
