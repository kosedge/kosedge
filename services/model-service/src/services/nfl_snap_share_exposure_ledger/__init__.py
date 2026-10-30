"""DRAFT-only snap-share `_5g` baseline_personnel_ref exposure ledger.

DEVELOPMENT_ONLY. Not wired to Independent Fair scoring, injury_nowcast,
offense_index / defense_index, H-HL-1/#664 activate, routes, or tasks.

One question: which players, and how much of their participation, sit in
each team's IF `_5g` historical rating window — not how many points they
are worth.
"""

from src.services.nfl_snap_share_exposure_ledger.builder import (
    assert_builder_isolated,
    build_snap_share_5g_exposure_ledger,
)
from src.services.nfl_snap_share_exposure_ledger.identity import (
    canonicalize_as_of_ts,
    canonical_json,
    fingerprint_payload,
    make_ledger_id,
)
from src.services.nfl_snap_share_exposure_ledger.schema import (
    ALLOWED_SNAP_SOURCE_IDS,
    FORBIDDEN_IMPORT_NAMES,
    IF_5G_WINDOW_CONTRACT,
    LEDGER_SCHEMA_VERSION,
    SOURCE_NFLVERSE_SNAP_COUNTS,
    SOURCE_SYNTH_SNAP_COUNTS,
    WINDOW_LABEL_5G,
    ExposureLedger,
    ExposureLedgerReject,
    GameParticipationBundle,
    IdentityLink,
    ScheduleGameRow,
    SituationalWeekRow,
    SnapFact,
)
from src.services.nfl_pregame_asof import (
    IF_MATCHUP_ASOF_CONTRACT,
    contiguous_pregame_rating_week,
    resolve_if_matchup_rolling_row,
    resolve_pregame_rating_week,
)
from src.services.nfl_snap_share_exposure_ledger.window import (
    latest_five_schedule_game_ids,
    resolve_if_5g_window,
)

__all__ = [
    "ALLOWED_SNAP_SOURCE_IDS",
    "FORBIDDEN_IMPORT_NAMES",
    "IF_5G_WINDOW_CONTRACT",
    "IF_MATCHUP_ASOF_CONTRACT",
    "LEDGER_SCHEMA_VERSION",
    "SOURCE_NFLVERSE_SNAP_COUNTS",
    "SOURCE_SYNTH_SNAP_COUNTS",
    "WINDOW_LABEL_5G",
    "ExposureLedger",
    "ExposureLedgerReject",
    "GameParticipationBundle",
    "IdentityLink",
    "ScheduleGameRow",
    "SituationalWeekRow",
    "SnapFact",
    "assert_builder_isolated",
    "build_snap_share_5g_exposure_ledger",
    "contiguous_pregame_rating_week",
    "canonical_json",
    "canonicalize_as_of_ts",
    "fingerprint_payload",
    "latest_five_schedule_game_ids",
    "make_ledger_id",
    "resolve_if_5g_window",
    "resolve_if_matchup_rolling_row",
    "resolve_pregame_rating_week",
]
