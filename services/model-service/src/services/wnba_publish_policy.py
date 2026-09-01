"""WNBA sides/totals publish policy (Ch4 team KEI) + props posture (Phase 3).

Chapter 4 tags vs trusted Best: LEAN ≥ 2.5 / PLAY ≥ 4.0.
Default force_research_only until walkforward vs *real closes* clears floors.
Props board stays research_only (never stake-eligible). Ch6 dark is later.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional

Tag = Literal["PLAY", "LEAN", "PASS"]
Market = Literal["spread", "total"]

BREAKEVEN_ATS = 0.5238
POLICY_VERSION = "wnba_mainlines_ch4_kei_v1"
PROPS_POLICY_VERSION = "wnba_props_phase3_research_v1"

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

MIN_CLOSE_JOIN_N = 30  # shorter season than NBA
MIN_SEGMENT_N = 45
MIN_SEGMENT_ATS = BREAKEVEN_ATS


@dataclass(frozen=True)
class WnbaSegmentEvidence:
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


DEFAULT_SEGMENT_EVIDENCE: Dict[str, WnbaSegmentEvidence] = {
    "spread:PLAY": WnbaSegmentEvidence(n_ats=0, ats_hit_rate=None, n_with_close_lines=0),
    "total:PLAY": WnbaSegmentEvidence(n_ats=0, ats_hit_rate=None, n_with_close_lines=0),
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
    evidence: Optional[WnbaSegmentEvidence] = None,
    force_research_only: bool = True,
    already_final: bool = False,
) -> Dict[str, Any]:
    if already_final:
        return {
            "tag": "PASS",
            "market": market,
            "policy_version": POLICY_VERSION,
            "reason": "already_final",
            "abs_edge": None
            if model_line is None or market_line is None
            else abs(float(model_line) - float(market_line)),
        }
    if force_research_only or model_line is None or market_line is None:
        return {
            "tag": "PASS",
            "market": market,
            "policy_version": POLICY_VERSION,
            "reason": "research_only_until_close_line_ats_clears",
            "abs_edge": None
            if model_line is None or market_line is None
            else abs(float(model_line) - float(market_line)),
        }
    abs_edge = abs(float(model_line) - float(market_line))
    cand = candidate_tag(market, abs_edge)
    ev = evidence or DEFAULT_SEGMENT_EVIDENCE.get(f"{market}:{cand}")
    if cand != "PASS" and (ev is None or not ev.clears()):
        return {
            "tag": "PASS",
            "market": market,
            "policy_version": POLICY_VERSION,
            "reason": "candidate_failed_evidence_floor",
            "candidate": cand,
            "abs_edge": abs_edge,
        }
    return {
        "tag": cand,
        "market": market,
        "policy_version": POLICY_VERSION,
        "reason": "cleared" if cand != "PASS" else "below_edge_band",
        "abs_edge": abs_edge,
    }


def board_publish_posture(
    *, n_with_close_lines: int = 0, ats: Optional[float] = None
) -> Dict[str, Any]:
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
        "props": "research_only",
        "force_research_only": mainlines == "research_only",
        "n_with_close_lines": n_with_close_lines,
        "ats": ats,
    }
