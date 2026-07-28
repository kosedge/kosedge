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

# Edge bands (pts of |model − market|). Derived from tag_band_simulations
# in nfl-edge-bucket-roi-study.json — LEAN spread band historically toxic.
SPREAD_PLAY_MIN = 2.5
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


# Locked evidence from nfl-edge-bucket-roi-study tag_band_simulations.data_driven_shipped
# plus owned OC CLV rollups where available. Update via evaluate_enterprise_gates.py.
DEFAULT_SEGMENT_EVIDENCE: Dict[str, SegmentEvidence] = {
    "spread:PLAY": SegmentEvidence(
        n_ats=535,
        ats_hit_rate=0.5645,
        beats_minus_110=True,
        n_clv=0,
        clv_positive_rate=None,
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
        if e >= SPREAD_PLAY_MIN:
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
