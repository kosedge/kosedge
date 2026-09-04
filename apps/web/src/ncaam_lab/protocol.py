"""Frozen Phase E Lab Protocol constants — do not peek-tune after scorecard.

Baselines:
  B1 — close consensus (Path A parquet mean across books)
  B2 — legacy KenPom AdjEM + HCA with PRIOR/UNKNOWN continuity honesty

Cut-dates LOCKED (tip dates, inclusive). 2025 pocket OUT.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Dict, Optional, Tuple


PROTOCOL_VERSION = "ncaam-fair-lab-protocol-v1.0"
PROTOCOL_DOC = "docs/lab/NCAAM_FAIR_LAB_PROTOCOL_v1.md"
SPORT_KEY = "ncaam"
SCHEDULE_SOT = "D"  # Odds API event_id + commence + B7 team_id

# Legacy KenPom+HCA (B2) — from ensemble_weights.json receipt (KenPom-only live).
# Documented experiment evidence: docs/CBB_KEI_MODEL_RUN_AND_METHODOLOGY.md
DEFAULT_HCA = 2.8696
SPREAD_CLIP = 28.0
ADJEM_DIFF_CLIP = 30.0

# Uncertainty floors (pts) when continuity is not SETTLED (portal model = DATA GAP).
# Pre-registered — not retuned after viewing scorecard.
UNCERTAINTY_SIGMA_PRIOR = 4.0
UNCERTAINTY_SIGMA_UNKNOWN = 6.0

# Market Edge honesty: exclude open snapshots whose API timestamp drifts >7d from filename.
OPEN_TIMESTAMP_MAX_DRIFT_DAYS = 7

# Fair total method stamp (only emitted when AdjOE/AdjDE/AdjT all present as-of tip).
FAIR_TOTAL_METHOD = "kenpom_adj_oe_de_tempo_v1"
# fair_total = (pace/100) * (adjoe_h + adjde_a + adjoe_a + adjde_h) / 2
# pace = (adjt_h + adjt_a) / 2


class ContinuityState(str, Enum):
    """Portal continuity model is DATA GAP — never emit SETTLED."""

    PRIOR = "PRIOR"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class CutWindow:
    name: str
    start: date
    end: date
    role: str  # universe | train | test | excluded


CUT_WINDOWS: Dict[str, CutWindow] = {
    "universe_path_a": CutWindow(
        name="universe_path_a",
        start=date(2022, 11, 1),
        end=date(2024, 1, 28),
        role="universe",
    ),
    "train_a": CutWindow(
        name="train_a",
        start=date(2022, 11, 7),
        end=date(2023, 3, 12),
        role="train",
    ),
    # Valid-A folded into Train-A (locked).
    "test_a": CutWindow(
        name="test_a",
        start=date(2023, 11, 6),
        end=date(2024, 1, 28),
        role="test",
    ),
}

# Explicit OUT pocket — never materialize as Lab fair research set.
EXCLUDED_POCKETS: Tuple[CutWindow, ...] = (
    CutWindow(
        name="pocket_2025",
        start=date(2025, 11, 1),
        end=date(2025, 12, 31),
        role="excluded",
    ),
)


def classify_tip(tip: date) -> Optional[str]:
    """Return primary cut label for a tip date, or None if outside Path A universe / excluded."""
    for pocket in EXCLUDED_POCKETS:
        if pocket.start <= tip <= pocket.end:
            return None
    # Prefer train/test labels when they nest inside universe.
    if CUT_WINDOWS["train_a"].start <= tip <= CUT_WINDOWS["train_a"].end:
        return "train_a"
    if CUT_WINDOWS["test_a"].start <= tip <= CUT_WINDOWS["test_a"].end:
        return "test_a"
    u = CUT_WINDOWS["universe_path_a"]
    if u.start <= tip <= u.end:
        return "universe_path_a"
    return None


def protocol_manifest() -> dict:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "sport": SPORT_KEY,
        "schedule_sot": SCHEDULE_SOT,
        "baselines": {
            "B1": "close_consensus_path_a",
            "B2": "kenpom_adjem_plus_hca_prior_unknown_honesty",
        },
        "cut_windows": {
            k: {
                "start": v.start.isoformat(),
                "end": v.end.isoformat(),
                "role": v.role,
            }
            for k, v in CUT_WINDOWS.items()
        },
        "excluded_pockets": [
            {
                "name": p.name,
                "start": p.start.isoformat(),
                "end": p.end.isoformat(),
                "role": p.role,
            }
            for p in EXCLUDED_POCKETS
        ],
        "hca_default": DEFAULT_HCA,
        "uncertainty_sigma": {
            ContinuityState.PRIOR.value: UNCERTAINTY_SIGMA_PRIOR,
            ContinuityState.UNKNOWN.value: UNCERTAINTY_SIGMA_UNKNOWN,
            "SETTLED": "FORBIDDEN — portal model DATA GAP",
        },
        "open_timestamp_max_drift_days": OPEN_TIMESTAMP_MAX_DRIFT_DAYS,
        "fair_total_method": FAIR_TOTAL_METHOD,
        "hard_not": [
            "edge_board_populate",
            "play_lean_conf",
            "props",
            "odds_densify_credit_burns",
            "invent_tips",
            "kenpom_as_sot",
            "peek_tune_after_scorecard",
            "edge_gt_4_shopping",
            "silent_spread_to_ml",
            "fake_settled_continuity",
        ],
    }
