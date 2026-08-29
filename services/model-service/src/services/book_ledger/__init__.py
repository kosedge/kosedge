"""The Book — multi-sport ledger (CLV-first).

Plays units=1; leans/pass units=0. Leans excluded from unit ROI.
Settled rows immutable. Paper vs booked never mixed in ROI.
"""

from src.services.book_ledger.clv import compute_clv
from src.services.book_ledger.ids import make_book_id, units_for_type
from src.services.book_ledger.metrics import (
    calibration_by_kei_edge,
    clv_distribution,
    lean_hit_rate,
    live_exposure,
    unit_roi,
)
from src.services.book_ledger.schema import (
    BOOK_TYPES,
    MARKETS,
    RESULTS,
    STAKE_FLAGS,
    SPORTS,
    BookRow,
)
from src.services.book_ledger.store import BookStore, get_store

__all__ = [
    "BOOK_TYPES",
    "MARKETS",
    "RESULTS",
    "SPORTS",
    "STAKE_FLAGS",
    "BookRow",
    "BookStore",
    "calibration_by_kei_edge",
    "clv_distribution",
    "compute_clv",
    "get_store",
    "lean_hit_rate",
    "live_exposure",
    "make_book_id",
    "unit_roi",
    "units_for_type",
]
