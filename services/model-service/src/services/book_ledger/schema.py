"""The Book row schema + validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional

SPORTS = frozenset({"cfb", "nfl", "nba", "mlb", "ncaam", "wnba"})
BOOK_TYPES = frozenset({"play", "lean", "pass"})
MARKETS = frozenset({"spread", "total", "ml", "prop"})
RESULTS = frozenset({"pending", "win", "loss", "push", "void"})
STAKE_FLAGS = frozenset({"paper", "booked"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


@dataclass
class BookRow:
    book_id: str
    sport: str
    season: int
    week_or_slate: str
    game_id: str
    home: str
    away: str
    type: str
    market: str
    side: str
    posted_at: str
    line: Optional[float] = None
    price: Optional[float] = None
    kei_at_post: Dict[str, Any] = field(default_factory=dict)
    market_at_post: Dict[str, Any] = field(default_factory=dict)
    market_source: Optional[str] = None
    close_line: Optional[float] = None
    close_price: Optional[float] = None
    close_at: Optional[str] = None
    clv: Optional[float] = None
    units: float = 0.0
    result: str = "pending"
    pnl_units: Optional[float] = None
    stake_flag: str = "paper"
    actor: Optional[str] = None
    confirmation: Optional[str] = None
    info_overlap: Optional[str] = None
    rest_flag: Optional[str] = None
    weather_flag: Optional[str] = None
    late_post: bool = False
    post_timing: Optional[str] = None
    notes_ref: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    settled_at: Optional[str] = None

    def validate(self) -> None:
        sport = str(self.sport).strip().lower()
        if sport not in SPORTS:
            raise ValueError(f"unsupported sport: {self.sport!r}")
        self.sport = sport
        t = str(self.type).strip().lower()
        if t not in BOOK_TYPES:
            raise ValueError(f"unsupported type: {self.type!r}")
        self.type = t
        m = str(self.market).strip().lower()
        if m not in MARKETS:
            raise ValueError(f"unsupported market: {self.market!r}")
        self.market = m
        r = str(self.result).strip().lower()
        if r not in RESULTS:
            raise ValueError(f"unsupported result: {self.result!r}")
        self.result = r
        sf = str(self.stake_flag).strip().lower()
        if sf not in STAKE_FLAGS:
            raise ValueError(f"unsupported stake_flag: {self.stake_flag!r}")
        self.stake_flag = sf
        if not self.book_id:
            raise ValueError("book_id required")
        if not self.game_id:
            raise ValueError("game_id required")
        if not self.side:
            raise ValueError("side required")
        if not self.posted_at:
            raise ValueError("posted_at required")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "BookRow":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        data = {k: v for k, v in raw.items() if k in known}
        row = cls(**data)  # type: ignore[arg-type]
        row.validate()
        return row


def default_created_at() -> str:
    return _utc_now()
