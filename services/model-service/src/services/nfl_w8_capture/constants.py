"""W8 capture acceptance criteria and Odds MS contract.

Official IMV Odds MS-1..MS-10 memo is **not in this public repo**. The
MS-1..MS-10 IDs below implement AC-4 from the 2026-10-22 acceptance text
(gaps = MISSING, never backfilled; book / captured_at / price). If the
off-repo memo differs, that difference is UNKNOWN.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

# AC-1 default one seal by 10-29 19:15 ET. Official seal time = custodian receipt of sha.
DEFAULT_SEAL_BY_ET = datetime(2026, 10, 29, 19, 15, tzinfo=ET)
MIN_LEAD_MINUTES = 60

STREAM_MARKET = "market_informed"
STREAM_INDEPENDENT = "independent"

# AC-6: independent stream must not contain these keys (or prefix matches).
FORBIDDEN_INDEPENDENT_KEYS = frozenset(
    {
        "spread_line",
        "total_line",
        "market_spread",
        "market_total",
        "market_spread_home",
        "market_total_home",
        "close",
        "close_spread",
        "close_total",
        "closing_spread",
        "closing_total",
        "book",
        "price",
        "odds",
        "moneyline",
        "ml_home",
        "ml_away",
        "implied_prob",
        "consensus",
        "open_spread",
        "open_total",
    }
)
FORBIDDEN_INDEPENDENT_PREFIXES = ("odds_", "market_", "close_", "book_", "price_")

# AC-4 local MS contract (see module docstring).
ODDS_MS = {
    "MS-1": "Record book, captured_at_utc, market, price; any missing field → status=MISSING",
    "MS-2": "captured_at_utc is the source capture time, never request/wall-clock mint",
    "MS-3": "captured_at_utc strictly before kickoff_utc",
    "MS-4": "Gaps written MISSING; never filled, interpolated, or carried forward",
    "MS-5": "No post-seal price append (AC-7)",
    "MS-6": "Independent stream forbidden from any market field (AC-6)",
    "MS-7": "Seal ≥ 60 minutes before kickoff (AC-1)",
    "MS-8": "One row per (game_id, book, market, captured_at_utc); no consensus invent",
    "MS-9": "Checksum every snapshot record",
    "MS-10": "Dry-run uses no production credentials; live keys are operator-supplied off-agent",
}

MISSING = "MISSING"
PARTIAL = "PARTIAL"
STATUS_FAIL = "FAIL"
STATUS_SEALED = "SEALED_PENDING_CUSTODIAN"
STATUS_OFFICIAL = "OFFICIALLY_SEALED"

BLIND_GRADER = "NOT_CAPTURE_BUILDER"
CHAIN_GENESIS = "W8_CAPTURE_CHAIN_V1"
