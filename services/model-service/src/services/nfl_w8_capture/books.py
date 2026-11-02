"""PART B book set for W8 prospective capture.

Production ``NFL_ODDS_API_CARRIED_BOOKMAKERS`` omits ``circa`` (UI-designated
only). That list is insufficient for PART B. This module is the W8 request
shape only — it does not change live fair-lines or fire The Odds API.
"""

from __future__ import annotations

from typing import Iterable, Literal, Optional, Sequence

BookRole = Literal["primary", "secondary", "other"]

# FINAL ADOPT PART B — five PRIMARY books, exact keys.
PRIMARY_BOOKS: tuple[str, ...] = (
    "draftkings",
    "fanduel",
    "betmgm",
    "fanatics",
    "circa",
)

# Optional secondary. Never substitutes a missing PRIMARY cell.
OPTIONAL_SECONDARY_BOOKS: tuple[str, ...] = ("ballybet",)

W8_ODDS_REGIONS = "us,us2"
W8_ODDS_MARKETS = "h2h,spreads,totals"
W8_SPORT_KEY = "americanfootball_nfl"

# Env names only — no secrets, no invented production values.
ENV_ODDS_API_KEY = "ODDS_API_KEY"
ENV_ODDS_API_KEY_BACKUP = "ODDS_API_KEY_BACKUP"
ENV_W8_BOOKMAKERS = "NFL_W8_ODDS_BOOKMAKERS"
ENV_W8_INCLUDE_SECONDARY = "NFL_W8_INCLUDE_BALLYBET"


def classify_book_role(book: str) -> BookRole:
    key = str(book or "").strip().lower()
    if key in PRIMARY_BOOKS:
        return "primary"
    if key in OPTIONAL_SECONDARY_BOOKS:
        return "secondary"
    return "other"


def normalize_book_keys(raw: Optional[str | Iterable[str]]) -> list[str]:
    if raw is None:
        tokens: Iterable[str] = ()
    elif isinstance(raw, str):
        tokens = raw.split(",")
    else:
        tokens = raw
    out: list[str] = []
    for token in tokens:
        book = str(token).strip().lower()
        if book and book not in out:
            out.append(book)
    return out


def w8_request_bookmakers(*, include_secondary: bool = False) -> list[str]:
    books = list(PRIMARY_BOOKS)
    if include_secondary:
        for extra in OPTIONAL_SECONDARY_BOOKS:
            if extra not in books:
                books.append(extra)
    return books


def build_w8_odds_request_params(
    *,
    include_secondary: bool = False,
    bookmakers: Optional[Sequence[str]] = None,
) -> dict[str, str]:
    """Params that a future hold-lift pull would send. Does not fetch.

    ``bookmakers`` always includes ``circa``. A list without circa is rejected
    so the current production carried list cannot be reused as-is.
    """
    books = (
        normalize_book_keys(bookmakers)
        if bookmakers is not None
        else w8_request_bookmakers(include_secondary=include_secondary)
    )
    if "circa" not in books:
        raise ValueError(
            "PART B request bookmakers= must include circa; "
            "production NFL_ODDS_API_CARRIED_BOOKMAKERS is insufficient"
        )
    missing_primary = [b for b in PRIMARY_BOOKS if b not in books]
    if missing_primary:
        raise ValueError(
            f"PART B request missing PRIMARY books: {','.join(missing_primary)}"
        )
    return {
        "regions": W8_ODDS_REGIONS,
        "markets": W8_ODDS_MARKETS,
        "oddsFormat": "american",
        "bookmakers": ",".join(books),
        "sport_key": W8_SPORT_KEY,
    }
