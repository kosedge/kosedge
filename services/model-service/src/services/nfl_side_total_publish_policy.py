"""Selective PLAY/LEAN publish policy for NFL sides & totals.

Default tag is PASS. PLAY/LEAN require both:
  1) clear edge magnitude in a historically productive band, and
  2) segment-level ATS and/or CLV evidence that clears the bar.

Evidence basis (settled bucket study + owned OC CLV):
  data/ops/nfl-edge-bucket-roi-study.json

Hard rules:
  - Full-slate PASS is the product default.
  - Props remain research-only (see nfl_prop_edge_policy.PLAY_STAKE_ELIGIBLE).
  - When product-level gates are RED, force PASS even if edge is large.
  - Preseason (PRE) never receives season PLAY tags when NFL_PRESEASON_MODE=info.
  - Week-1 2026 launch: totals are sides-only (confirmatory totals CLV RED).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional

Tag = Literal["PLAY", "LEAN", "PASS"]
Market = Literal["spread", "total"]

# -110 American → ~52.38% breakeven hit rate
BREAKEVEN_ATS = 0.5238

# Edge bands (pts of |model − market|).
# v1 (legacy): spread PLAY |edge| ≥ 2.5 (uncapped) — mean |edge| ~7, CLV diluted by flats.
# v2 (2026-07-28 pre-registration): spread PLAY 2.5 ≤ |edge| < 7.0
#   Caps mega-edges (calibration failures / research-only); movement CLV clears on 2024–25.
# Evidence: data/ops/nfl-play-only-holdout.json + nfl-path-to-95-report.md
# Walk-forward (select 2023 → confirm 2024–25 once): data/ops/nfl-walkforward-play-band-study.json
#   Research-only tighter bands improve confirmatory CLV+ but fail n_clv≥200 GREEN — NOT promoted.
SPREAD_PLAY_MIN = 2.5
SPREAD_PLAY_MAX = 7.0  # half-open upper bound; |edge| ≥ 7.0 → PASS (size-down research)
POLICY_VERSION = "spread_play_v2_cap7"
# Locked by 2024–25 true-close holdout (nfl-path-steam-edge-holdout.json):
# PLAY ATS 63.9% / +21.9% ROI vs kickoff-safe DK/FD close. Do not loosen the
# cap, add steam, or retune blend. Prior ~72% was last-path-snap, not close.
# Ryan Kos product lock 2026-09-03: see NFL_SPREAD_PLAY_LOCKED.md — do not hunt PLAY.

# Research registrations (publish path still uses SPREAD_PLAY_* above).
# Selected on 2023 CLV+; confirmed once on 2024–25. Do not swap product without GREEN n_clv≥200.
RESEARCH_SPREAD_PLAY_BANDS = (
    # registration_id, lo, hi — see nfl-walkforward-play-band-study.json
    # Selected on 2023 CLV+; confirmed once on 2024–25; improve CLV+ vs v2; not product.
    ("spread_play_research_40_80", 4.0, 8.0),  # confirm CLV+ ~0.645, n_clv~155
    ("spread_play_research_40_70", 4.0, 7.0),  # confirm CLV+ ~0.633, n_clv~120
    ("spread_play_research_50_80", 5.0, 8.0),  # 2023 CLV+ leader; confirm ~0.625
    ("spread_play_research_35_70", 3.5, 7.0),  # confirm CLV+ ~0.614, n_clv~145
)
# Spread LEAN disabled: 1.1–2.5 settled ROI −14.4% (n=174) in study.
SPREAD_LEAN_ENABLED = False
SPREAD_LEAN_MIN = 1.1

# Totals: narrow 2.5–3.0 band cleared ATS historically, but confirmatory 2024–25
# movement-CLV is RED (~0.35). Week-1 launch posture = sides-only product.
# Keep band constants for research re-enable; do not stake totals.
TOTAL_PLAY_MIN = 2.5
TOTAL_PLAY_MAX = 3.0
TOTAL_PLAY_ENABLED = False  # sides-only launch; see data/ops/nfl-totals-band-review.md
TOTAL_LEAN_ENABLED = False
TOTAL_LEAN_MIN = 2.1

# Preseason info desk — never mix exhibition ATS into season PLAY gates.
PRESEASON_MODE = (os.getenv("NFL_PRESEASON_MODE", "info") or "info").strip().lower()

# Segment evidence floors (tag-level when full-slate cannot pass).
MIN_SEGMENT_N = 60
MIN_SEGMENT_ATS = BREAKEVEN_ATS
MIN_SEGMENT_CLV_POS_RATE = 0.55
MIN_SEGMENT_CLV_N = 40


def is_preseason_info_mode() -> bool:
    """True when PRE games must not receive season PLAY tags."""
    mode = (os.getenv("NFL_PRESEASON_MODE", "info") or "info").strip().lower()
    return mode in {"info", "watch", "pass", "1", "true", "yes"}


def is_preseason_season_type(season_type: Optional[str]) -> bool:
    if not season_type:
        return False
    token = str(season_type).strip().upper()
    return token in {"PRE", "PRESEASON", "PRE_SEASON", "EXHIBITION"}


@dataclass(frozen=True)
class SegmentEvidence:
    """Historical ATS/CLV for a publishable segment (market × tag band)."""

    n_ats: int
    ats_hit_rate: Optional[float]
    beats_minus_110: bool
    n_clv: int = 0
    clv_positive_rate: Optional[float] = None

    def clears(self) -> bool:
        ats_ok = (
            self.n_ats >= MIN_SEGMENT_N
            and self.ats_hit_rate is not None
            and self.ats_hit_rate >= MIN_SEGMENT_ATS
            and self.beats_minus_110
        )
        clv_ok = (
            self.n_clv >= MIN_SEGMENT_CLV_N
            and self.clv_positive_rate is not None
            and self.clv_positive_rate >= MIN_SEGMENT_CLV_POS_RATE
        )
        # Require ATS clear; CLV is confirmatory when sample exists.
        if self.n_clv >= MIN_SEGMENT_CLV_N:
            return ats_ok and clv_ok
        return ats_ok


# Locked evidence: v2 band on 2024–25 confirmatory holdout (movement CLV).
# Update via scripts/nfl/play_only_holdout.py + evaluate_enterprise_gates.py.
# total:PLAY evidence intentionally fails CLV clear (confirmatory RED).
DEFAULT_SEGMENT_EVIDENCE: Dict[str, SegmentEvidence] = {
    "spread:PLAY": SegmentEvidence(
        n_ats=227,
        ats_hit_rate=0.7313,
        beats_minus_110=True,
        n_clv=206,
        clv_positive_rate=0.6117,
    ),
    "spread:LEAN": SegmentEvidence(
        n_ats=174,
        ats_hit_rate=0.4483,
        beats_minus_110=False,
        n_clv=0,
        clv_positive_rate=None,
    ),
    "total:PLAY": SegmentEvidence(
        n_ats=52,
        ats_hit_rate=0.6154,
        beats_minus_110=True,
        n_clv=43,
        clv_positive_rate=0.3488,  # confirmatory RED — does not clear
    ),
    "total:LEAN": SegmentEvidence(
        n_ats=464,
        ats_hit_rate=0.5022,
        beats_minus_110=False,
        n_clv=0,
        clv_positive_rate=None,
    ),
}


def candidate_tag(market: Market, abs_edge: float) -> Tag:
    """Magnitude-only candidate before evidence / product gates."""
    e = abs(float(abs_edge))
    if market == "spread":
        if SPREAD_PLAY_MIN <= e < SPREAD_PLAY_MAX:
            return "PLAY"
        if SPREAD_LEAN_ENABLED and e >= SPREAD_LEAN_MIN:
            return "LEAN"
        return "PASS"
    # total — launch sides-only (band retained for research re-enable)
    if not TOTAL_PLAY_ENABLED:
        return "PASS"
    if TOTAL_PLAY_MIN <= e < TOTAL_PLAY_MAX:
        return "PLAY"
    if TOTAL_LEAN_ENABLED and e >= TOTAL_LEAN_MIN:
        return "LEAN"
    return "PASS"


def display_action_label(action_label: Optional[str]) -> Optional[str]:
    """Mirror web dead-tier remap: unreachable BEST VALUE → PLAY."""
    if action_label is None:
        return None
    label = str(action_label)
    # CONFIDENCE_TIER_BASE (0.72) < CONFIDENCE_BEST_BET_MIN (0.75) → BEST VALUE dead.
    if label == "BEST VALUE":
        return "PLAY"
    return label


def publish_tag_from_action_label(action_label: Optional[str]) -> Tag:
    """One SoT: publish tag matches subscriber-facing action after dead-tier remap.

    STAY AWAY / ALERT collapse to PASS (publish vocabulary is PLAY|LEAN|PASS).
    """
    shown = display_action_label(action_label)
    if shown in ("PLAY", "BEST VALUE"):
        return "PLAY"
    if shown == "LEAN":
        return "LEAN"
    return "PASS"


def is_market_side_disagreement(
    *,
    model_spread_home: Optional[float],
    market_spread_home: Optional[float],
    min_abs_delta: float = 1.5,
) -> bool:
    """True when model and market disagree on which side is favored by ≥ min_abs_delta.

    Used to block PLAY tags on calibration failures (e.g. model home favorite
    while market has home as a dog). Research board may still show the number.
    """
    if model_spread_home is None or market_spread_home is None:
        return False
    try:
        model = float(model_spread_home)
        market = float(market_spread_home)
    except (TypeError, ValueError):
        return False
    if model == 0.0 or market == 0.0:
        return False
    opposite = (model > 0 and market < 0) or (model < 0 and market > 0)
    return bool(opposite and abs(model - market) >= float(min_abs_delta))


def publish_tag(
    *,
    market: Market,
    abs_edge: Optional[float],
    product_gate_status: str = "YELLOW",
    segment_evidence: Optional[Dict[str, SegmentEvidence]] = None,
    season_type: Optional[str] = None,
    model_spread_home: Optional[float] = None,
    market_spread_home: Optional[float] = None,
) -> Dict[str, Any]:
    """Return tag + stake eligibility for a side/total edge.

    product_gate_status:
      GREEN  — selective PLAY/LEAN allowed when segment clears
      YELLOW — PLAY only (no LEAN); still requires segment clear
      RED    — force PASS (research board only)

    season_type:
      PRE / PRESEASON — blocked when NFL_PRESEASON_MODE=info (default).
    """
    if is_preseason_season_type(season_type) and is_preseason_info_mode():
        return {
            "tag": "PASS",
            "stake_eligible": False,
            "reason": "preseason_info_desk",
            "candidate_tag": "PASS",
            "preseason_mode": os.getenv("NFL_PRESEASON_MODE", "info"),
        }

    if abs_edge is None:
        return {
            "tag": "PASS",
            "stake_eligible": False,
            "reason": "missing_edge",
            "candidate_tag": "PASS",
        }

    if market == "spread" and is_market_side_disagreement(
        model_spread_home=model_spread_home,
        market_spread_home=market_spread_home,
    ):
        return {
            "tag": "PASS",
            "stake_eligible": False,
            "reason": "market_side_disagreement",
            "candidate_tag": candidate_tag(market, abs_edge),
        }

    if market == "total" and not TOTAL_PLAY_ENABLED:
        return {
            "tag": "PASS",
            "stake_eligible": False,
            "reason": "totals_sides_only_launch",
            "candidate_tag": "PASS",
        }

    cand = candidate_tag(market, abs_edge)
    status = (product_gate_status or "YELLOW").upper()
    if status == "RED" or cand == "PASS":
        return {
            "tag": "PASS",
            "stake_eligible": False,
            "reason": "product_gate_red" if status == "RED" else "edge_below_band",
            "candidate_tag": cand,
        }

    if status == "YELLOW" and cand == "LEAN":
        return {
            "tag": "PASS",
            "stake_eligible": False,
            "reason": "lean_blocked_on_yellow_product_gate",
            "candidate_tag": cand,
        }

    evidence_map = segment_evidence or DEFAULT_SEGMENT_EVIDENCE
    key = f"{market}:{cand}"
    evidence = evidence_map.get(key)
    if evidence is None or not evidence.clears():
        return {
            "tag": "PASS",
            "stake_eligible": False,
            "reason": "segment_evidence_failed",
            "candidate_tag": cand,
            "segment_key": key,
        }

    return {
        "tag": cand,
        "stake_eligible": cand == "PLAY",
        "reason": "edge_and_segment_cleared",
        "candidate_tag": cand,
        "segment_key": key,
        "segment_n_ats": evidence.n_ats,
        "segment_ats": evidence.ats_hit_rate,
    }
