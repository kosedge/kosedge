"""PART B close definition for W8 prospective capture.

Close = last snapshot whose PROVIDER SERVER timestamp is <= kickoff_utc and
whose age (kickoff − provider_server_ts) is <= S=10 minutes.

Rules:
- market-level last_update missing => UNKNOWN => not a close
- client receive time alone is never a close
- missing PRIMARY cell (including circa) = MISSING, never imputed
- k=3 PRIMARY present + non-stale per game-market, else close=MISSING
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Iterable, Optional

from src.services.nfl_w8_capture.books import PRIMARY_BOOKS, classify_book_role
from src.services.nfl_w8_capture.timestamps import parse_utc

CLOSE_MAX_AGE = timedelta(minutes=10)
PRIMARY_K_REQUIRED = 3

CloseStatus = str  # CLOSE | MISSING | UNKNOWN


@dataclass(frozen=True)
class BookMarketCell:
    book: str
    market: str
    game_id: str
    line: Optional[float] = None
    price: Optional[int] = None
    market_last_update: Optional[Any] = None
    provider_server_ts: Optional[Any] = None
    client_received_at: Optional[Any] = None

    @property
    def book_key(self) -> str:
        return str(self.book or "").strip().lower()


@dataclass
class BookCloseVerdict:
    book: str
    role: str
    cell_status: str  # PRESENT | MISSING | UNKNOWN | STALE | NOT_CLOSE
    reason: str
    provider_server_ts: Optional[datetime] = None
    market_last_update: Optional[datetime] = None
    age_seconds: Optional[float] = None
    line: Optional[float] = None
    price: Optional[int] = None


@dataclass
class GameMarketClose:
    game_id: str
    market: str
    kickoff_utc: datetime
    status: CloseStatus
    reason: str
    primary_fresh_count: int
    k_required: int = PRIMARY_K_REQUIRED
    books: list[BookCloseVerdict] = field(default_factory=list)
    selected: Optional[BookCloseVerdict] = None


def _age_ok(provider_ts: datetime, kickoff_utc: datetime) -> tuple[bool, float]:
    age = (kickoff_utc - provider_ts).total_seconds()
    return 0 <= age <= CLOSE_MAX_AGE.total_seconds(), age


def evaluate_cell(
    cell: Optional[BookMarketCell],
    *,
    book: str,
    kickoff_utc: datetime,
) -> BookCloseVerdict:
    role = classify_book_role(book)
    if cell is None:
        return BookCloseVerdict(
            book=book,
            role=role,
            cell_status="MISSING",
            reason="missing_cell_never_impute",
        )

    last_update = parse_utc(cell.market_last_update)
    if last_update is None:
        return BookCloseVerdict(
            book=book,
            role=role,
            cell_status="UNKNOWN",
            reason="missing_last_update_not_a_close",
            line=cell.line,
            price=cell.price,
        )

    provider_ts = parse_utc(cell.provider_server_ts)
    if provider_ts is None:
        return BookCloseVerdict(
            book=book,
            role=role,
            cell_status="NOT_CLOSE",
            reason="client_receive_alone_is_not_a_close",
            market_last_update=last_update,
            line=cell.line,
            price=cell.price,
        )

    if provider_ts > kickoff_utc:
        return BookCloseVerdict(
            book=book,
            role=role,
            cell_status="NOT_CLOSE",
            reason="provider_server_ts_after_kickoff",
            provider_server_ts=provider_ts,
            market_last_update=last_update,
            line=cell.line,
            price=cell.price,
        )

    if last_update > kickoff_utc:
        return BookCloseVerdict(
            book=book,
            role=role,
            cell_status="NOT_CLOSE",
            reason="last_update_after_kickoff",
            provider_server_ts=provider_ts,
            market_last_update=last_update,
            line=cell.line,
            price=cell.price,
        )

    ok, age = _age_ok(provider_ts, kickoff_utc)
    if not ok:
        return BookCloseVerdict(
            book=book,
            role=role,
            cell_status="STALE",
            reason="age_gt_S_10min",
            provider_server_ts=provider_ts,
            market_last_update=last_update,
            age_seconds=age,
            line=cell.line,
            price=cell.price,
        )

    return BookCloseVerdict(
        book=book,
        role=role,
        cell_status="PRESENT",
        reason="provider_ts_le_kickoff_age_le_S",
        provider_server_ts=provider_ts,
        market_last_update=last_update,
        age_seconds=age,
        line=cell.line,
        price=cell.price,
    )


def _index_cells(
    cells: Iterable[BookMarketCell],
    *,
    game_id: str,
    market: str,
) -> dict[str, BookMarketCell]:
    indexed: dict[str, BookMarketCell] = {}
    for cell in cells:
        if cell.game_id != game_id or cell.market != market:
            continue
        key = cell.book_key
        existing = indexed.get(key)
        # Last snapshot: prefer later provider server ts; never invent.
        if existing is None:
            indexed[key] = cell
            continue
        new_ts = parse_utc(cell.provider_server_ts)
        old_ts = parse_utc(existing.provider_server_ts)
        if new_ts is not None and (old_ts is None or new_ts > old_ts):
            indexed[key] = cell
    return indexed


def evaluate_game_market_close(
    *,
    game_id: str,
    market: str,
    kickoff_utc: datetime,
    cells: Iterable[BookMarketCell],
) -> GameMarketClose:
    kickoff = parse_utc(kickoff_utc)
    if kickoff is None:
        raise ValueError("kickoff_utc is required and must be parseable")

    indexed = _index_cells(cells, game_id=game_id, market=market)
    verdicts: list[BookCloseVerdict] = []
    for book in PRIMARY_BOOKS:
        verdicts.append(
            evaluate_cell(indexed.get(book), book=book, kickoff_utc=kickoff)
        )

    # Secondary books are recorded but never fill a PRIMARY hole.
    for book, cell in indexed.items():
        if classify_book_role(book) == "secondary":
            verdicts.append(evaluate_cell(cell, book=book, kickoff_utc=kickoff))

    fresh_primary = [
        v
        for v in verdicts
        if v.role == "primary" and v.cell_status == "PRESENT"
    ]
    unknown_primary = [v for v in verdicts if v.role == "primary" and v.cell_status == "UNKNOWN"]

    if len(fresh_primary) < PRIMARY_K_REQUIRED:
        # UNKNOWN last_update on a PRIMARY cell is not a close contributor.
        # Circa (or any PRIMARY) hole stays MISSING — never imputed.
        reason = "k_lt_3_primary_present_non_stale"
        if unknown_primary and len(fresh_primary) == 0:
            status: CloseStatus = "UNKNOWN"
            reason = "primary_last_update_unknown_not_a_close"
        else:
            status = "MISSING"
        return GameMarketClose(
            game_id=game_id,
            market=market,
            kickoff_utc=kickoff,
            status=status,
            reason=reason,
            primary_fresh_count=len(fresh_primary),
            books=verdicts,
            selected=None,
        )

    selected = max(
        fresh_primary,
        key=lambda v: v.provider_server_ts or datetime.min,
    )
    return GameMarketClose(
        game_id=game_id,
        market=market,
        kickoff_utc=kickoff,
        status="CLOSE",
        reason="k_ge_3_primary_present_non_stale",
        primary_fresh_count=len(fresh_primary),
        books=verdicts,
        selected=selected,
    )
