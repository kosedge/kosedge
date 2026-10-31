"""Load synthetic Odds-API-shaped fixtures. Never hits the network."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.services.nfl_w8_capture.close import BookMarketCell
from src.services.nfl_w8_capture.timestamps import parse_utc

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
SYNTHETIC_W8_REG = FIXTURE_DIR / "synthetic_w8_reg_game.json"


def load_json_fixture(path: str | Path | None = None) -> dict[str, Any]:
    target = Path(path) if path is not None else SYNTHETIC_W8_REG
    return json.loads(target.read_text(encoding="utf-8"))


def events_from_odds_payload(payload: Any) -> list[dict[str, Any]]:
    """Normalize a /v4 odds body to a list of event dicts. No network."""
    if payload is None:
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        if payload.get("bookmakers") is not None or payload.get("commence_time") is not None:
            return [payload]
        for key in ("data", "games", "events"):
            raw = payload.get(key)
            if isinstance(raw, list):
                return [item for item in raw if isinstance(item, dict)]
        return []
    return []


def select_odds_event(
    payload: Any,
    *,
    game_id: str,
    kickoff_utc: datetime,
    odds_event_id: str = "",
) -> dict[str, Any]:
    """Pick one event from an Odds-shaped payload. Does not invent lines."""
    events = events_from_odds_payload(payload)
    wanted_id = str(odds_event_id or "").strip()
    if wanted_id:
        for event in events:
            if str(event.get("id") or "") == wanted_id:
                return event
        raise ValueError("odds-event-id not present in payload")
    gid = str(game_id or "").strip()
    for event in events:
        if gid and str(event.get("game_id") or event.get("id") or "") == gid:
            return event
    kickoff = parse_utc(kickoff_utc)
    time_hits: list[dict[str, Any]] = []
    if kickoff is not None:
        for event in events:
            commence = parse_utc(event.get("commence_time") or event.get("kickoff_utc"))
            if commence is None:
                continue
            if abs((commence - kickoff).total_seconds()) <= 60:
                time_hits.append(event)
    if len(time_hits) == 1:
        return time_hits[0]
    if len(events) == 1:
        return events[0]
    raise ValueError("could not select a single event from odds payload")


def cells_from_odds_shaped_event(
    event: dict[str, Any],
    *,
    market: str,
    game_id: Optional[str] = None,
    provider_server_ts: Any = None,
    client_received_at: Any = None,
) -> list[BookMarketCell]:
    game_id = str(game_id or event.get("game_id") or "")
    provider_ts = provider_server_ts if provider_server_ts is not None else event.get("provider_server_ts")
    received = client_received_at if client_received_at is not None else event.get("client_received_at")
    cells: list[BookMarketCell] = []
    for book in event.get("bookmakers") or []:
        book_key = str(book.get("key") or "").strip().lower()
        for mkt in book.get("markets") or []:
            if str(mkt.get("key") or "") != market:
                continue
            outcomes = list(mkt.get("outcomes") or [])
            home = str(event.get("home_team") or "")
            line = None
            price = None
            for outcome in outcomes:
                if str(outcome.get("name") or "") == home:
                    line = outcome.get("point")
                    price = outcome.get("price")
                    break
            cells.append(
                BookMarketCell(
                    book=book_key,
                    market=market,
                    game_id=game_id,
                    line=float(line) if line is not None else None,
                    price=int(price) if price is not None else None,
                    market_last_update=mkt.get("last_update"),
                    provider_server_ts=provider_ts,
                    client_received_at=received,
                )
            )
    return cells
