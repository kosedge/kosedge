"""KosEdge NFL Decision Engine (Edge Board Action Layer).

Doctrine
--------
We bet prices, not teams.
The same game can be a PLAY, LEAN, or PASS depending only on the current market number.

This layer sits **on top of** locked model fair lines. It does not change true PR /
season-engine math, and it does not unlock or alter the locked preseason baseline.

Contract coexistence (Model vs KEI vs Edge)
------------------------------------------
- **Model research fair** → research / decision-engine fair vs market (this module).
- **KEI reprice** → published product handicap on Edge Board columns.
- **Edge / publish tags** (`publish_tag_*`) → KEI vs market only (existing PLAY desk tags).
- **Action layer** (this module) → Model fair vs market for desk Action Labels + Play-To.

Do not collapse Action Labels into publish tags. Both may coexist on the same row.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Literal, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Constants — preserve exact language and thresholds from the framework.
# ---------------------------------------------------------------------------

BREAKEVEN_ATS_MINUS_110 = 0.5238  # ≈ 52.38%

# Key numbers that make a side edge more valuable when crossed.
SPREAD_KEY_NUMBERS: Tuple[float, ...] = (3.0, 7.0, 10.0, 14.0)
TOTAL_KEY_NUMBERS: Tuple[float, ...] = (37.0, 41.0, 44.0, 47.0, 51.0)

# Cover-probability thresholds (standard -110).
COVER_PASS_MAX = 0.53  # < 53% → PASS
COVER_LEAN_MAX = 0.54  # 53–54% → LEAN
COVER_PLAY_MAX = 0.56  # 54–56% → PLAY
COVER_STRONG_MAX = 0.58  # 56–58% → STRONG PLAY; 58%+ Exceptional
COVER_MODEL_WARNING = 0.60  # 60%+ vs mature markets → model warning

# Totals point thresholds (initial screen).
TOTAL_PASS_MAX = 1.5
TOTAL_LEAN_MAX = 2.0
TOTAL_PLAY_MAX = 3.0
TOTAL_STRONG_MIN = 3.5

# Confidence floors for PLAY / BEST VALUE (0–1 scale, kept separate from edge).
CONFIDENCE_PLAY_MIN = 0.55
CONFIDENCE_BEST_BET_MIN = 0.75

ActionLabel = Literal[
    "PASS",
    "LEAN",
    "PLAY",
    "BEST VALUE",
    "ALERT",
    "STAY AWAY",
]

PointGrade = Literal["PASS", "LEAN", "PLAY", "STRONG PLAY", "EXCEPTIONAL"]
WeekRegime = Literal["early", "standard", "inseason", "late"]
Market = Literal["spread", "total"]


class ConfidenceBand(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(frozen=True)
class SidePointThresholds:
    """Raw point-difference bands for side grading."""

    pass_max: float  # |edge| < pass_max → PASS
    lean_max: float  # pass_max ≤ |edge| < lean_max → LEAN (gaps handled below)
    play_min: float  # |edge| ≥ play_min → at least PLAY
    strong_min: float  # |edge| ≥ strong_min → STRONG PLAY candidate


# Weeks 1–2 (higher uncertainty) — ACTIVE BY DEFAULT at season start.
EARLY_SIDE = SidePointThresholds(
    pass_max=1.5,
    lean_max=2.0,
    play_min=2.5,
    strong_min=3.5,
)

# Initial / mid-season screen (weeks 3–5, and fallback).
STANDARD_SIDE = SidePointThresholds(
    pass_max=1.0,
    lean_max=1.5,
    play_min=2.0,
    strong_min=3.0,
)

# Weeks 6–12 (model has real current-season data) — lower edge required.
INSEASON_SIDE = SidePointThresholds(
    pass_max=1.0,
    lean_max=1.5,
    play_min=2.0,
    strong_min=3.0,  # still escalate magnitude; PLAY opens at 2.0+
)

# Weeks 13+ — keep inseason posture (model mature; injury noise rises separately).
LATE_SIDE = INSEASON_SIDE


@dataclass(frozen=True)
class PlayToLadder:
    """Execution plan for every PLAY or LEAN."""

    side_or_total: str  # e.g. "BUF -4" / "Over 44.5"
    play_to: float
    lean_to: float
    pass_from: float
    fair_line: float
    market_line: float
    edge_points: float
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MarketConfirmation:
    """Market movement as information — never updates the fair line."""

    model_fair: Optional[float]
    opening: Optional[float]
    current: Optional[float]
    closing: Optional[float]
    confirms_thesis: Optional[bool]
    weakens_thesis: Optional[bool]
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConfidenceAssessment:
    """Independent of edge magnitude — never combined into one score."""

    score: float  # 0–1
    band: str  # LOW / MEDIUM / HIGH
    factors: Dict[str, Any] = field(default_factory=dict)
    unresolved_flags: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["unresolved_flags"] = list(self.unresolved_flags)
        return d


@dataclass(frozen=True)
class DecisionResult:
    market: Market
    action_label: ActionLabel
    point_grade: PointGrade
    edge_magnitude: float
    model_confidence: ConfidenceAssessment
    cover_prob: Optional[float]
    cover_grade: Optional[PointGrade]
    play_to: Optional[PlayToLadder]
    market_confirmation: MarketConfirmation
    is_best_bet: bool
    model_warning: bool
    key_number_cross: bool
    price_still_available: bool
    numerical_edge: bool
    confidence_ok: bool
    reason: str
    week: Optional[int]
    week_regime: WeekRegime
    fair_line: Optional[float]
    market_line: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "market": self.market,
            "action_label": self.action_label,
            "point_grade": self.point_grade,
            "edge_magnitude": self.edge_magnitude,
            "model_confidence": self.model_confidence.to_dict(),
            "cover_prob": self.cover_prob,
            "cover_grade": self.cover_grade,
            "play_to": self.play_to.to_dict() if self.play_to else None,
            "market_confirmation": self.market_confirmation.to_dict(),
            "is_best_bet": self.is_best_bet,
            "model_warning": self.model_warning,
            "key_number_cross": self.key_number_cross,
            "price_still_available": self.price_still_available,
            "numerical_edge": self.numerical_edge,
            "confidence_ok": self.confidence_ok,
            "reason": self.reason,
            "week": self.week,
            "week_regime": self.week_regime,
            "fair_line": self.fair_line,
            "market_line": self.market_line,
        }


def week_regime(week: Optional[int]) -> WeekRegime:
    """Week-dependent threshold regime. Weeks 1–2 active by default at season start."""
    if week is None:
        return "early"  # season start default — higher uncertainty
    w = int(week)
    if w <= 2:
        return "early"
    if 6 <= w <= 12:
        return "inseason"
    if w >= 13:
        return "late"
    return "standard"


def side_thresholds_for_week(week: Optional[int]) -> SidePointThresholds:
    regime = week_regime(week)
    if regime == "early":
        return EARLY_SIDE
    if regime in ("inseason", "late"):
        return INSEASON_SIDE
    return STANDARD_SIDE


def confidence_band(score: float) -> str:
    s = max(0.0, min(1.0, float(score)))
    if s >= 0.75:
        return ConfidenceBand.HIGH.value
    if s >= 0.55:
        return ConfidenceBand.MEDIUM.value
    return ConfidenceBand.LOW.value


def assess_confidence(
    *,
    base_score: Optional[float] = None,
    scheme_stable: bool = True,
    injury_clear: bool = True,
    weather_clear: bool = True,
    qb_clear: bool = True,
    historical_fit: Optional[float] = None,
    conflicting_inputs: bool = False,
    liquidity_ok: bool = True,
    extra_flags: Optional[Sequence[str]] = None,
) -> ConfidenceAssessment:
    """Independent model-confidence assessment (not edge magnitude)."""
    score = 0.72 if base_score is None else float(base_score)
    flags: list[str] = []
    if not scheme_stable:
        score -= 0.12
        flags.append("scheme_unstable")
    if not injury_clear:
        score -= 0.18
        flags.append("injury_unresolved")
    if not weather_clear:
        score -= 0.10
        flags.append("weather_unresolved")
    if not qb_clear:
        score -= 0.22
        flags.append("qb_unresolved")
    if conflicting_inputs:
        score -= 0.25
        flags.append("conflicting_inputs")
    if not liquidity_ok:
        score -= 0.08
        flags.append("liquidity_thin")
    if historical_fit is not None:
        # Blend mild historical performance signal without collapsing into edge.
        score = 0.7 * score + 0.3 * max(0.0, min(1.0, float(historical_fit)))
    if extra_flags:
        flags.extend(str(f) for f in extra_flags if f)
    score = max(0.0, min(1.0, round(score, 4)))
    return ConfidenceAssessment(
        score=score,
        band=confidence_band(score),
        factors={
            "scheme_stable": scheme_stable,
            "injury_clear": injury_clear,
            "weather_clear": weather_clear,
            "qb_clear": qb_clear,
            "conflicting_inputs": conflicting_inputs,
            "liquidity_ok": liquidity_ok,
            "historical_fit": historical_fit,
        },
        unresolved_flags=tuple(flags),
    )


def grade_side_points(abs_edge: float, week: Optional[int] = None) -> PointGrade:
    """Raw point difference vs fair line (initial screen), week-aware."""
    e = abs(float(abs_edge))
    t = side_thresholds_for_week(week)
    if e < t.pass_max:
        return "PASS"
    # Gap between lean_max and play_min stays LEAN (not enough for PLAY).
    if e < t.play_min:
        return "LEAN"
    if e < t.strong_min:
        return "PLAY"
    return "STRONG PLAY"


def grade_total_points(abs_edge: float) -> PointGrade:
    """Totals grading framework (point thresholds)."""
    e = abs(float(abs_edge))
    if e < TOTAL_PASS_MAX:
        return "PASS"
    if e < 2.5:  # 1.5–2.0 LEAN; gap 2.0–2.5 stays LEAN
        return "LEAN"
    if e < TOTAL_STRONG_MIN:  # 2.5–3.0 PLAY; gap to 3.5 stays PLAY
        return "PLAY"
    return "STRONG PLAY"


def grade_cover_prob(cover_prob: Optional[float]) -> Optional[PointGrade]:
    """Cover probability thresholds (standard -110). Break-even ≈ 52.38%."""
    if cover_prob is None:
        return None
    p = float(cover_prob)
    if p < COVER_PASS_MAX:
        return "PASS"
    if p < COVER_LEAN_MAX:
        return "LEAN"
    if p < COVER_PLAY_MAX:
        return "PLAY"
    if p < COVER_STRONG_MAX:
        return "STRONG PLAY"
    return "EXCEPTIONAL"


def crosses_key_number(
    fair: float,
    market: float,
    *,
    market_kind: Market = "spread",
) -> bool:
    """True when the edge path crosses a key number (more valuable)."""
    keys = SPREAD_KEY_NUMBERS if market_kind == "spread" else TOTAL_KEY_NUMBERS
    lo = min(float(fair), float(market))
    hi = max(float(fair), float(market))
    if hi <= lo:
        return False
    for k in keys:
        if lo < k < hi or lo < -k < hi:
            return True
    return False


def prefer_key_number_edge(
    abs_edge_a: float,
    crosses_a: bool,
    abs_edge_b: float,
    crosses_b: bool,
) -> Literal["a", "b", "tie"]:
    """A 2.5-pt edge that crosses 3 beats a 2.5-pt edge that does not."""
    # Equal magnitude: prefer key-number cross.
    if abs(abs_edge_a - abs_edge_b) < 1e-9:
        if crosses_a and not crosses_b:
            return "a"
        if crosses_b and not crosses_a:
            return "b"
        return "tie"
    # Slightly smaller edge that crosses key number can beat larger non-cross
    # when within 0.5 pt (framework: key numbers matter).
    if crosses_a and not crosses_b and abs_edge_a + 0.5 >= abs_edge_b:
        return "a"
    if crosses_b and not crosses_a and abs_edge_b + 0.5 >= abs_edge_a:
        return "b"
    return "a" if abs_edge_a > abs_edge_b else "b"


def _round_half(x: float) -> float:
    return round(float(x) * 2.0) / 2.0


def build_side_play_to_ladder(
    *,
    fair_spread_home: float,
    market_spread_home: float,
    home_abbr: str = "HOME",
    away_abbr: str = "AWAY",
) -> PlayToLadder:
    """Play-To ladder for sides.

    Example: Fair BUF −6.0, Market BUF −3, Edge +3.0
      Play to: BUF −4 · Lean: −4.5 · Pass: −5 or worse
    """
    edge = float(fair_spread_home) - float(market_spread_home)
    # Negative edge ⇒ model likes home more than market (home getting more points / less laying).
    likes_home = edge < 0
    abs_edge = abs(edge)
    # Bet side's market number in away-favorite / home-favorite display terms.
    if likes_home:
        # Home number at market (home spread).
        team = home_abbr
        market_num = float(market_spread_home)
        # Improving price for home = higher (less negative / more positive) spread.
        # Play-to keeps ~2/3 of the edge; lean keeps ~1/2; pass when edge nearly gone.
        play_to = _round_half(market_num + abs_edge * (1.0 / 3.0))
        lean_to = _round_half(market_num + abs_edge * 0.5)
        pass_from = _round_half(market_num + abs_edge * (2.0 / 3.0))
        # Ensure ordering for home dog / home fav: play_to is better than lean_to for bettor.
        # For home: better = larger algebraically when buying points.
        if play_to < lean_to:
            play_to, lean_to = lean_to, play_to
        note = f"Play {team} to {play_to:+g}; lean {lean_to:+g}; pass {pass_from:+g} or worse"
    else:
        team = away_abbr
        # Away market number = −home market.
        market_num = -float(market_spread_home)
        # Improving away price = larger algebraically (e.g. −3 → −4 is worse for away fav).
        # For away favorite (negative): better = less laying = larger algebraically (−3 better than −4).
        # Play-to keeps best prices; pass when number moves toward fair.
        play_to = _round_half(market_num - abs_edge * (1.0 / 3.0))
        lean_to = _round_half(market_num - abs_edge * 0.5)
        pass_from = _round_half(market_num - abs_edge * (2.0 / 3.0))
        # Away favorite laying points: play_to should be better (higher) than pass.
        # Example market −3, fair −6 → play −4, lean −4.5, pass −5.
        play_to = _round_half(market_num - (abs_edge / 3.0))
        lean_to = _round_half(market_num - (abs_edge / 2.0))
        pass_from = _round_half(market_num - (abs_edge * 2.0 / 3.0))
        note = f"Play {team} to {play_to:+g}; lean {lean_to:+g}; pass {pass_from:+g} or worse"

    return PlayToLadder(
        side_or_total=f"{team} {market_num:+g}",
        play_to=play_to,
        lean_to=lean_to,
        pass_from=pass_from,
        fair_line=float(fair_spread_home),
        market_line=float(market_spread_home),
        edge_points=round(abs_edge, 3),
        notes=note,
    )


def build_total_play_to_ladder(
    *,
    fair_total: float,
    market_total: float,
) -> PlayToLadder:
    """Play-To ladder for totals.

    Example: Model 47.2, Market 44
      Play Over: 44.5 or better · Lean: 45–45.5 · Pass: 46+
    """
    edge = float(fair_total) - float(market_total)
    likes_over = edge > 0
    abs_edge = abs(edge)
    m = float(market_total)
    if likes_over:
        play_to = _round_half(m + 0.5)  # 44 → play 44.5 or better
        lean_lo = _round_half(m + 1.0)
        lean_hi = _round_half(m + 1.5)
        pass_from = _round_half(m + 2.0)
        label = f"Over {m:g}"
        note = (
            f"Play Over {play_to:g} or better; lean {lean_lo:g}–{lean_hi:g}; "
            f"pass {pass_from:g}+"
        )
        lean_to = lean_hi
    else:
        play_to = _round_half(m - 0.5)
        lean_lo = _round_half(m - 1.5)
        lean_hi = _round_half(m - 1.0)
        pass_from = _round_half(m - 2.0)
        label = f"Under {m:g}"
        note = (
            f"Play Under {play_to:g} or better; lean {lean_lo:g}–{lean_hi:g}; "
            f"pass {pass_from:g} or lower"
        )
        lean_to = lean_lo

    return PlayToLadder(
        side_or_total=label,
        play_to=play_to,
        lean_to=lean_to,
        pass_from=pass_from,
        fair_line=float(fair_total),
        market_line=float(market_total),
        edge_points=round(abs_edge, 3),
        notes=note,
    )


def assess_market_confirmation(
    *,
    model_fair: Optional[float],
    opening: Optional[float],
    current: Optional[float],
    closing: Optional[float] = None,
    likes_home_or_over: Optional[bool] = None,
) -> MarketConfirmation:
    """Record Independent model → open → current → close. Never mutate fair line."""
    confirms: Optional[bool] = None
    weakens: Optional[bool] = None
    note = "Market movement is information only; fair line unchanged."
    if (
        model_fair is not None
        and opening is not None
        and current is not None
        and likes_home_or_over is not None
    ):
        # For spreads (home): thesis "likes home" means wanting higher home spread
        # (or less negative). Movement from open→current toward model confirms.
        move = float(current) - float(opening)
        toward_model = (float(model_fair) - float(opening)) * move > 0
        confirms = toward_model
        weakens = not toward_model and abs(move) >= 0.5
        if confirms:
            note = "Market moved toward model fair — confirms thesis; fair unchanged."
        elif weakens:
            note = "Market moved away from model fair — weakens thesis; fair unchanged."
    return MarketConfirmation(
        model_fair=model_fair,
        opening=opening,
        current=current,
        closing=closing,
        confirms_thesis=confirms,
        weakens_thesis=weakens,
        note=note,
    )


def _point_rank(grade: PointGrade) -> int:
    order = {
        "PASS": 0,
        "LEAN": 1,
        "PLAY": 2,
        "STRONG PLAY": 3,
        "EXCEPTIONAL": 4,
    }
    return order[grade]


def _merge_grades(
    point_grade: PointGrade,
    cover_grade: Optional[PointGrade],
) -> PointGrade:
    """Ultimately prefer cover-prob / EV when available; never ignore key structure."""
    if cover_grade is None:
        return point_grade
    # Use the more conservative of the two for action gating, but surface both.
    return point_grade if _point_rank(point_grade) <= _point_rank(cover_grade) else cover_grade


def evaluate_best_bet(
    *,
    point_grade: PointGrade,
    confidence: ConfidenceAssessment,
    price_available: bool,
    key_number_cross: bool,
    market_confirmation: MarketConfirmation,
    matchup_support: bool,
    liquidity_ok: bool,
) -> bool:
    """Strict Best Bet — largest raw discrepancy alone does NOT qualify."""
    large_edge = point_grade in ("STRONG PLAY", "EXCEPTIONAL") or (
        point_grade == "PLAY" and key_number_cross
    )
    high_conf = confidence.score >= CONFIDENCE_BEST_BET_MIN and confidence.band == "HIGH"
    limited_unresolved = len(confidence.unresolved_flags) == 0
    favorable_number = price_available and not bool(market_confirmation.weakens_thesis)
    return bool(
        large_edge
        and high_conf
        and favorable_number
        and limited_unresolved
        and matchup_support
        and liquidity_ok
    )


def decide_side(
    *,
    fair_spread_home: Optional[float],
    market_spread_home: Optional[float],
    week: Optional[int] = None,
    cover_prob: Optional[float] = None,
    opening_spread_home: Optional[float] = None,
    closing_spread_home: Optional[float] = None,
    home_abbr: str = "HOME",
    away_abbr: str = "AWAY",
    confidence: Optional[ConfidenceAssessment] = None,
    price_still_available: bool = True,
    matchup_support: bool = True,
    liquidity_ok: bool = True,
    stay_away: bool = False,
) -> DecisionResult:
    """Grade a side: Model fair vs market → Action Label + Play-To."""
    conf = confidence or assess_confidence()
    regime = week_regime(week)
    mc = assess_market_confirmation(
        model_fair=fair_spread_home,
        opening=opening_spread_home,
        current=market_spread_home,
        closing=closing_spread_home,
        likes_home_or_over=(
            None
            if fair_spread_home is None or market_spread_home is None
            else (float(fair_spread_home) - float(market_spread_home)) < 0
        ),
    )

    if fair_spread_home is None or market_spread_home is None:
        return DecisionResult(
            market="spread",
            action_label="PASS",
            point_grade="PASS",
            edge_magnitude=0.0,
            model_confidence=conf,
            cover_prob=cover_prob,
            cover_grade=grade_cover_prob(cover_prob),
            play_to=None,
            market_confirmation=mc,
            is_best_bet=False,
            model_warning=False,
            key_number_cross=False,
            price_still_available=price_still_available,
            numerical_edge=False,
            confidence_ok=False,
            reason="missing_fair_or_market",
            week=week,
            week_regime=regime,
            fair_line=fair_spread_home,
            market_line=market_spread_home,
        )

    edge = float(fair_spread_home) - float(market_spread_home)
    abs_edge = abs(edge)
    point_grade = grade_side_points(abs_edge, week)
    cover_grade = grade_cover_prob(cover_prob)
    effective = _merge_grades(point_grade, cover_grade)
    key_cross = crosses_key_number(
        float(fair_spread_home), float(market_spread_home), market_kind="spread"
    )
    # Key-number bump: 2.5-pt edge crossing 3 can elevate LEAN→PLAY consideration.
    if key_cross and point_grade == "LEAN" and abs_edge >= 2.0:
        effective = "PLAY" if _point_rank(effective) < _point_rank("PLAY") else effective
        if point_grade == "LEAN":
            point_grade = "PLAY"

    model_warning = bool(cover_prob is not None and float(cover_prob) >= COVER_MODEL_WARNING)
    numerical_edge = effective in ("LEAN", "PLAY", "STRONG PLAY", "EXCEPTIONAL")
    confidence_ok = conf.score >= CONFIDENCE_PLAY_MIN and "qb_unresolved" not in conf.unresolved_flags
    major_uncertainty = bool(
        conf.unresolved_flags
        and any(
            f in conf.unresolved_flags
            for f in ("qb_unresolved", "injury_unresolved", "weather_unresolved", "conflicting_inputs")
        )
    )

    if stay_away or "conflicting_inputs" in conf.unresolved_flags:
        label: ActionLabel = "STAY AWAY"
        reason = "conflicting_inputs_or_bad_market"
        ladder = None
    elif numerical_edge and major_uncertainty:
        label = "ALERT"
        reason = "edge_with_material_uncertainty"
        ladder = build_side_play_to_ladder(
            fair_spread_home=float(fair_spread_home),
            market_spread_home=float(market_spread_home),
            home_abbr=home_abbr,
            away_abbr=away_abbr,
        )
    elif effective == "PASS":
        label = "PASS"
        reason = "edge_below_week_threshold"
        ladder = None
    elif effective == "LEAN":
        label = "LEAN"
        reason = "mild_edge_watch_list"
        ladder = build_side_play_to_ladder(
            fair_spread_home=float(fair_spread_home),
            market_spread_home=float(market_spread_home),
            home_abbr=home_abbr,
            away_abbr=away_abbr,
        )
    else:
        # PLAY requires three things simultaneously.
        if numerical_edge and confidence_ok and price_still_available:
            is_bb = evaluate_best_bet(
                point_grade=effective if effective != "EXCEPTIONAL" else "STRONG PLAY",
                confidence=conf,
                price_available=price_still_available,
                key_number_cross=key_cross,
                market_confirmation=mc,
                matchup_support=matchup_support,
                liquidity_ok=liquidity_ok,
            )
            if is_bb:
                label = "BEST VALUE"
                reason = "best_bet_strict_cleared"
            else:
                label = "PLAY"
                reason = "play_triple_cleared"
            ladder = build_side_play_to_ladder(
                fair_spread_home=float(fair_spread_home),
                market_spread_home=float(market_spread_home),
                home_abbr=home_abbr,
                away_abbr=away_abbr,
            )
        elif numerical_edge and not price_still_available:
            label = "ALERT"
            reason = "edge_but_price_gone"
            ladder = build_side_play_to_ladder(
                fair_spread_home=float(fair_spread_home),
                market_spread_home=float(market_spread_home),
                home_abbr=home_abbr,
                away_abbr=away_abbr,
            )
        elif numerical_edge and not confidence_ok:
            label = "ALERT"
            reason = "edge_but_confidence_insufficient"
            ladder = build_side_play_to_ladder(
                fair_spread_home=float(fair_spread_home),
                market_spread_home=float(market_spread_home),
                home_abbr=home_abbr,
                away_abbr=away_abbr,
            )
        else:
            label = "LEAN"
            reason = "partial_play_requirements"
            ladder = build_side_play_to_ladder(
                fair_spread_home=float(fair_spread_home),
                market_spread_home=float(market_spread_home),
                home_abbr=home_abbr,
                away_abbr=away_abbr,
            )

    is_best = label == "BEST VALUE"
    if model_warning and label in ("PLAY", "BEST VALUE", "LEAN"):
        reason = f"{reason}|model_warning_60pct_plus_ats"

    return DecisionResult(
        market="spread",
        action_label=label,
        point_grade=point_grade,
        edge_magnitude=round(abs_edge, 3),
        model_confidence=conf,
        cover_prob=cover_prob,
        cover_grade=cover_grade,
        play_to=ladder,
        market_confirmation=mc,
        is_best_bet=is_best,
        model_warning=model_warning,
        key_number_cross=key_cross,
        price_still_available=price_still_available,
        numerical_edge=numerical_edge,
        confidence_ok=confidence_ok,
        reason=reason,
        week=week,
        week_regime=regime,
        fair_line=float(fair_spread_home),
        market_line=float(market_spread_home),
    )


def decide_total(
    *,
    fair_total: Optional[float],
    market_total: Optional[float],
    week: Optional[int] = None,
    over_prob: Optional[float] = None,
    opening_total: Optional[float] = None,
    closing_total: Optional[float] = None,
    confidence: Optional[ConfidenceAssessment] = None,
    price_still_available: bool = True,
    matchup_support: bool = True,
    liquidity_ok: bool = True,
    stay_away: bool = False,
) -> DecisionResult:
    """Grade a total: Model fair vs market → Action Label + Play-To."""
    conf = confidence or assess_confidence()
    regime = week_regime(week)
    mc = assess_market_confirmation(
        model_fair=fair_total,
        opening=opening_total,
        current=market_total,
        closing=closing_total,
        likes_home_or_over=(
            None
            if fair_total is None or market_total is None
            else (float(fair_total) - float(market_total)) > 0
        ),
    )

    if fair_total is None or market_total is None:
        return DecisionResult(
            market="total",
            action_label="PASS",
            point_grade="PASS",
            edge_magnitude=0.0,
            model_confidence=conf,
            cover_prob=over_prob,
            cover_grade=grade_cover_prob(over_prob),
            play_to=None,
            market_confirmation=mc,
            is_best_bet=False,
            model_warning=False,
            key_number_cross=False,
            price_still_available=price_still_available,
            numerical_edge=False,
            confidence_ok=False,
            reason="missing_fair_or_market",
            week=week,
            week_regime=regime,
            fair_line=fair_total,
            market_line=market_total,
        )

    edge = float(fair_total) - float(market_total)
    abs_edge = abs(edge)
    point_grade = grade_total_points(abs_edge)
    # When score distribution exists, over_prob / under_prob drive cover path.
    cover_side_prob = over_prob
    if over_prob is not None and edge < 0:
        cover_side_prob = 1.0 - float(over_prob)
    cover_grade = grade_cover_prob(cover_side_prob)
    effective = _merge_grades(point_grade, cover_grade)
    key_cross = crosses_key_number(
        float(fair_total), float(market_total), market_kind="total"
    )
    model_warning = bool(
        cover_side_prob is not None and float(cover_side_prob) >= COVER_MODEL_WARNING
    )
    numerical_edge = effective in ("LEAN", "PLAY", "STRONG PLAY", "EXCEPTIONAL")
    confidence_ok = conf.score >= CONFIDENCE_PLAY_MIN
    major_uncertainty = bool(conf.unresolved_flags)

    if stay_away or "conflicting_inputs" in conf.unresolved_flags:
        label: ActionLabel = "STAY AWAY"
        reason = "conflicting_inputs_or_bad_market"
        ladder = None
    elif numerical_edge and major_uncertainty and conf.score < CONFIDENCE_PLAY_MIN:
        label = "ALERT"
        reason = "edge_with_material_uncertainty"
        ladder = build_total_play_to_ladder(
            fair_total=float(fair_total), market_total=float(market_total)
        )
    elif effective == "PASS":
        label = "PASS"
        reason = "edge_below_total_threshold"
        ladder = None
    elif effective == "LEAN":
        label = "LEAN"
        reason = "mild_edge_watch_list"
        ladder = build_total_play_to_ladder(
            fair_total=float(fair_total), market_total=float(market_total)
        )
    else:
        if numerical_edge and confidence_ok and price_still_available:
            is_bb = evaluate_best_bet(
                point_grade=effective if effective != "EXCEPTIONAL" else "STRONG PLAY",
                confidence=conf,
                price_available=price_still_available,
                key_number_cross=key_cross,
                market_confirmation=mc,
                matchup_support=matchup_support,
                liquidity_ok=liquidity_ok,
            )
            label = "BEST VALUE" if is_bb else "PLAY"
            reason = "best_bet_strict_cleared" if is_bb else "play_triple_cleared"
            ladder = build_total_play_to_ladder(
                fair_total=float(fair_total), market_total=float(market_total)
            )
        elif numerical_edge and not price_still_available:
            label = "ALERT"
            reason = "edge_but_price_gone"
            ladder = build_total_play_to_ladder(
                fair_total=float(fair_total), market_total=float(market_total)
            )
        elif numerical_edge and not confidence_ok:
            label = "ALERT"
            reason = "edge_but_confidence_insufficient"
            ladder = build_total_play_to_ladder(
                fair_total=float(fair_total), market_total=float(market_total)
            )
        else:
            label = "LEAN"
            reason = "partial_play_requirements"
            ladder = build_total_play_to_ladder(
                fair_total=float(fair_total), market_total=float(market_total)
            )

    return DecisionResult(
        market="total",
        action_label=label,
        point_grade=point_grade,
        edge_magnitude=round(abs_edge, 3),
        model_confidence=conf,
        cover_prob=cover_side_prob,
        cover_grade=cover_grade,
        play_to=ladder,
        market_confirmation=mc,
        is_best_bet=label == "BEST VALUE",
        model_warning=model_warning,
        key_number_cross=key_cross,
        price_still_available=price_still_available,
        numerical_edge=numerical_edge,
        confidence_ok=confidence_ok,
        reason=reason,
        week=week,
        week_regime=regime,
        fair_line=float(fair_total),
        market_line=float(market_total),
    )


def decide_game(
    *,
    week: Optional[int],
    fair_spread_home: Optional[float],
    market_spread_home: Optional[float],
    fair_total: Optional[float],
    market_total: Optional[float],
    home_abbr: str = "HOME",
    away_abbr: str = "AWAY",
    cover_prob: Optional[float] = None,
    over_prob: Optional[float] = None,
    opening_spread_home: Optional[float] = None,
    opening_total: Optional[float] = None,
    closing_spread_home: Optional[float] = None,
    closing_total: Optional[float] = None,
    confidence: Optional[ConfidenceAssessment] = None,
    price_still_available_spread: bool = True,
    price_still_available_total: bool = True,
    matchup_support: bool = True,
    liquidity_ok: bool = True,
    stay_away: bool = False,
) -> Dict[str, Any]:
    """Full-game decision payload for fair-lines / Edge Board rows."""
    conf = confidence or assess_confidence()
    side = decide_side(
        fair_spread_home=fair_spread_home,
        market_spread_home=market_spread_home,
        week=week,
        cover_prob=cover_prob,
        opening_spread_home=opening_spread_home,
        closing_spread_home=closing_spread_home,
        home_abbr=home_abbr,
        away_abbr=away_abbr,
        confidence=conf,
        price_still_available=price_still_available_spread,
        matchup_support=matchup_support,
        liquidity_ok=liquidity_ok,
        stay_away=stay_away,
    )
    total = decide_total(
        fair_total=fair_total,
        market_total=market_total,
        week=week,
        over_prob=over_prob,
        opening_total=opening_total,
        closing_total=closing_total,
        confidence=conf,
        price_still_available=price_still_available_total,
        matchup_support=matchup_support,
        liquidity_ok=liquidity_ok,
        stay_away=stay_away,
    )
    return {
        "doctrine": "We bet prices, not teams.",
        "week": week,
        "week_regime": week_regime(week),
        "spread": side.to_dict(),
        "total": total.to_dict(),
        "edge_magnitude_spread": side.edge_magnitude,
        "edge_magnitude_total": total.edge_magnitude,
        "model_confidence": conf.to_dict(),
        "action_label_spread": side.action_label,
        "action_label_total": total.action_label,
    }
