"""NBA sides/totals publish policy (Phase 2+) + props posture (Phase 3).

Default tag is PASS / research_only until walkforward vs *real closes*
clears evidence floors. Props board is research_only (never stake-eligible).

Mirrors NFL side/total discipline without copying NFL edge bands:
  - Full-slate PASS is the product default.
  - PLAY/LEAN require close-line join coverage + ATS floors.
  - Offseason / empty slate stays honest (no invented prices).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional

Tag = Literal["PLAY", "LEAN", "PASS"]
Market = Literal["spread", "total"]

BREAKEVEN_ATS = 0.5238
POLICY_VERSION = "nba_mainlines_phase2_research_v1"
PROPS_POLICY_VERSION = "nba_props_phase3_research_v1"

# Chapter 4 team KEI tags vs trusted Best (pts).
SPREAD_PLAY_MIN = 4.0
SPREAD_PLAY_MAX = 99.0
SPREAD_LEAN_MIN = 2.5
SPREAD_LEAN_ENABLED = True

TOTAL_PLAY_MIN = 4.0
TOTAL_PLAY_MAX = 99.0
TOTAL_PLAY_ENABLED = True
TOTAL_LEAN_ENABLED = True
TOTAL_LEAN_MIN = 2.5

MIN_CLOSE_JOIN_N = 40
MIN_SEGMENT_N = 60
MIN_SEGMENT_ATS = BREAKEVEN_ATS


@dataclass(frozen=True)
class NbaSegmentEvidence:
    n_ats: int
    ats_hit_rate: Optional[float]
    n_with_close_lines: int = 0

    def clears(self) -> bool:
        return (
            self.n_with_close_lines >= MIN_CLOSE_JOIN_N
            and self.n_ats >= MIN_SEGMENT_N
            and self.ats_hit_rate is not None
            and self.ats_hit_rate >= MIN_SEGMENT_ATS
        )


# Locked until Phase-2 walkforward with real closes updates these.
DEFAULT_SEGMENT_EVIDENCE: Dict[str, NbaSegmentEvidence] = {
    "spread:PLAY": NbaSegmentEvidence(n_ats=0, ats_hit_rate=None, n_with_close_lines=0),
    "total:PLAY": NbaSegmentEvidence(n_ats=0, ats_hit_rate=None, n_with_close_lines=0),
}


def candidate_tag(market: Market, abs_edge: float) -> Tag:
    e = abs(float(abs_edge))
    if market == "spread":
        if e >= SPREAD_PLAY_MIN:
            return "PLAY"
        if SPREAD_LEAN_ENABLED and e >= SPREAD_LEAN_MIN:
            return "LEAN"
        return "PASS"
    if e >= TOTAL_PLAY_MIN and TOTAL_PLAY_ENABLED:
        return "PLAY"
    if TOTAL_LEAN_ENABLED and e >= TOTAL_LEAN_MIN:
        return "LEAN"
    return "PASS"


def publish_tag(
    market: Market,
    *,
    model_line: Optional[float],
    market_line: Optional[float],
    evidence: Optional[NbaSegmentEvidence] = None,
    force_research_only: bool = True,
    preseason: bool = False,
    best_trusted: bool = False,
) -> Dict[str, Any]:
    """Return PASS/LEAN/PLAY. Ch4: PASS if Best missing/untrusted/preseason."""
    if (
        preseason
        or force_research_only
        or model_line is None
        or market_line is None
        or not best_trusted
    ):
        reason = "preseason_pass" if preseason else (
            "research_only_until_trusted_best"
            if force_research_only or not best_trusted or market_line is None
            else "missing_model"
        )
        return {
            "tag": "PASS",
            "market": market,
            "policy_version": POLICY_VERSION,
            "reason": reason,
            "abs_edge": None
            if model_line is None or market_line is None
            else abs(float(model_line) - float(market_line)),
        }
    abs_edge = abs(float(model_line) - float(market_line))
    cand = candidate_tag(market, abs_edge)
    # Ch4: tag from magnitude vs trusted Best; evidence floors remain for later ATS.
    return {
        "tag": cand,
        "market": market,
        "policy_version": POLICY_VERSION,
        "reason": "cleared_vs_trusted_best" if cand != "PASS" else "below_edge_band",
        "abs_edge": abs_edge,
    }


def board_publish_posture(*, n_with_close_lines: int = 0, ats: Optional[float] = None) -> Dict[str, Any]:
    """Desk-level posture for fair-lines / ops."""
    mainlines = "research_only"
    if (
        n_with_close_lines >= MIN_CLOSE_JOIN_N
        and ats is not None
        and ats >= MIN_SEGMENT_ATS
    ):
        mainlines = "calibrating"
    return {
        "policy_version": POLICY_VERSION,
        "props_policy_version": PROPS_POLICY_VERSION,
        "mainlines": mainlines,
        # Props board is live as research desk; stake tags stay off.
        "props": "research_only",
        "force_research_only": mainlines == "research_only",
        "n_with_close_lines": n_with_close_lines,
        "ats": ats,
    }
