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
"""

from __future__ import annotations

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

# Totals: only the narrow 2.5–3.0 PLAY band cleared ATS in the shipped sim;
# ≥3.0 was toxic (size-down / PASS).
TOTAL_PLAY_MIN = 2.5
TOTAL_PLAY_MAX = 3.0
TOTAL_LEAN_ENABLED = False
TOTAL_LEAN_MIN = 2.1

# Segment evidence floors (tag-level when full-slate cannot pass).
MIN_SEGMENT_N = 60
MIN_SEGMENT_ATS = BREAKEVEN_ATS
MIN_SEGMENT_CLV_POS_RATE = 0.55
MIN_SEGMENT_CLV_N = 40


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
        n_ats=63,
        ats_hit_rate=0.5714,
        beats_minus_110=True,
        n_clv=45,
        clv_positive_rate=0.556,
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
    # total
    if TOTAL_PLAY_MIN <= e < TOTAL_PLAY_MAX:
        return "PLAY"
    if TOTAL_LEAN_ENABLED and e >= TOTAL_LEAN_MIN:
        return "LEAN"
    return "PASS"


def publish_tag(
    *,
    market: Market,
    abs_edge: Optional[float],
    product_gate_status: str = "YELLOW",
    segment_evidence: Optional[Dict[str, SegmentEvidence]] = None,
) -> Dict[str, Any]:
    """Return tag + stake eligibility for a side/total edge.

    product_gate_status:
      GREEN  — selective PLAY/LEAN allowed when segment clears
      YELLOW — PLAY only (no LEAN); still requires segment clear
      RED    — force PASS (research board only)
    """
    if abs_edge is None:
        return {
            "tag": "PASS",
            "stake_eligible": False,
            "reason": "missing_edge",
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
