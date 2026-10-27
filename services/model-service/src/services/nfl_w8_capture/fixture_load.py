"""Load synthetic Odds-API-shaped fixtures. Never hits the network."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.services.nfl_w8_capture.close import BookMarketCell

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
SYNTHETIC_W8_REG = FIXTURE_DIR / "synthetic_w8_reg_game.json"


def load_json_fixture(path: str | Path | None = None) -> dict[str, Any]:
    target = Path(path) if path is not None else SYNTHETIC_W8_REG
    return json.loads(target.read_text(encoding="utf-8"))


def cells_from_odds_shaped_event(event: dict[str, Any], *, market: str) -> list[BookMarketCell]:
    game_id = str(event.get("game_id") or "")
    provider_ts = event.get("provider_server_ts")
    received = event.get("client_received_at")
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
