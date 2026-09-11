"""P0 Odds Expansion — market-driven discovery, lake, consensus, polling.

Extends ``odds_snapshots`` / ``pull_odds_snapshot``. Does not invent a
parallel ledger. HIST backfill and CFB public ungate are out of scope.
"""

from .consensus import (
    BookQuote,
    ConsensusResult,
    isolate_rogue_or_stale,
    multi_book_consensus,
)
from .discovery import (
    EXPANSION_SPORT_KEYS,
    catalog_coverage,
    event_has_verified_mainline,
    filter_ingestible_events,
    should_ingest_event,
)
from .lake import (
    LAKE_FIELDS,
    SNAPSHOT_KINDS,
    lake_row_from_wide_snapshot,
    snapshot_kind_from_history,
)
from .polling import (
    POLLING_TIERS,
    classify_polling_tier,
    should_refresh_on_cadence,
)

__all__ = [
    "BookQuote",
    "ConsensusResult",
    "EXPANSION_SPORT_KEYS",
    "LAKE_FIELDS",
    "POLLING_TIERS",
    "SNAPSHOT_KINDS",
    "catalog_coverage",
    "classify_polling_tier",
    "event_has_verified_mainline",
    "filter_ingestible_events",
    "isolate_rogue_or_stale",
    "lake_row_from_wide_snapshot",
    "multi_book_consensus",
    "should_ingest_event",
    "should_refresh_on_cadence",
    "snapshot_kind_from_history",
]
