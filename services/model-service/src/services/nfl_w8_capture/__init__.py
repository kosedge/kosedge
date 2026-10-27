"""Week-8 prospective NFL capture — paper/code draft (t4445u RD-7).

Isolated from production Odds pull / fair-lines / Coming Soon. Does not call
The Odds API. Seal-ack is out of scope (AC-12: Cursor cannot seal-ack).

Spec cites (sha8, not invented):
- IMV_SPEC_W8_PROSPECTIVE_CAPTURE_ACCEPTANCE_t4191u_v2 ``08808adf``
- FINAL ADOPT PART B ``0448042a`` / freeze ``2e40ead4``
- DECISION_RYAN_t4445u_RD7_CURSOR_W8_BUILDER_v1 (ops path cite ``91aebe69``)
- PR unblock path ``0511c346``
"""

from src.services.nfl_w8_capture.books import (
    OPTIONAL_SECONDARY_BOOKS,
    PRIMARY_BOOKS,
    W8_ODDS_REGIONS,
    build_w8_odds_request_params,
    classify_book_role,
)
from src.services.nfl_w8_capture.cadence import (
    AlertKind,
    plan_pre_kickoff_samples,
    review_sample_coverage,
)
from src.services.nfl_w8_capture.close import (
    CLOSE_MAX_AGE,
    PRIMARY_K_REQUIRED,
    CloseStatus,
    evaluate_game_market_close,
)
from src.services.nfl_w8_capture.evidence import (
    append_evidence_entry,
    verify_evidence_chain,
)
from src.services.nfl_w8_capture.hold import (
    OddsApiHoldError,
    assert_odds_api_hold,
    odds_api_hold_is_on,
)
from src.services.nfl_w8_capture.pin import (
    UNSET_SHA,
    build_pin_manifest,
    validate_pin_manifest,
)
from src.services.nfl_w8_capture.snapshots import (
    append_snapshot,
    snapshot_content_sha,
)
from src.services.nfl_w8_capture.streams import (
    STREAM_IND,
    STREAM_MKT,
    ForbiddenInputError,
    check_s_ind_forbidden_inputs,
)

__all__ = [
    "PRIMARY_BOOKS",
    "OPTIONAL_SECONDARY_BOOKS",
    "W8_ODDS_REGIONS",
    "build_w8_odds_request_params",
    "classify_book_role",
    "AlertKind",
    "plan_pre_kickoff_samples",
    "review_sample_coverage",
    "CLOSE_MAX_AGE",
    "PRIMARY_K_REQUIRED",
    "CloseStatus",
    "evaluate_game_market_close",
    "append_evidence_entry",
    "verify_evidence_chain",
    "OddsApiHoldError",
    "assert_odds_api_hold",
    "odds_api_hold_is_on",
    "UNSET_SHA",
    "build_pin_manifest",
    "validate_pin_manifest",
    "append_snapshot",
    "snapshot_content_sha",
    "STREAM_IND",
    "STREAM_MKT",
    "ForbiddenInputError",
    "check_s_ind_forbidden_inputs",
]
