"""KosEdge NFL Decision Engine (Edge Board Tag Policy + Play-To).

Doctrine
--------
We bet prices, not teams.
The same game can be a PLAY, LEAN, or PASS depending only on the current market number.

Contract coexistence (Model vs KEI vs Edge)
------------------------------------------
- **Model research fair** → research only (no PLAY from Model alone).
- **KEI reprice** → published product handicap; Fair for tags.
- **Edge / Tag** → **KEI vs best available market only** (this module).
- Thresholds live in ``nfl_tag_policy`` — do not duplicate bands.

Tags are mechanical. Edge magnitude and confidence stay separate fields.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Literal, Optional, Sequence, Tuple

from src.services.nfl_tag_policy import (
    BREAKEVEN_ATS_MINUS_110,
    CONFIDENCE_BEST_BET_MIN,
    CONFIDENCE_PLAY_MIN,
    CONFIDENCE_TIER_BASE,
    COVER_LEAN_MAX,
    COVER_MODEL_WARNING,
    COVER_PASS_MAX,
    COVER_PLAY_MAX,
    COVER_STRONG_MAX,
    EARLY_SIDE,
    INSEASON_SIDE,
    LATE_SIDE,
    SPREAD_KEY_NUMBERS,
    STANDARD_SIDE,
    TOTAL_KEY_NUMBERS,
    TOTAL_PASS_MAX,
    TOTAL_STRONG_MIN,
    SidePointThresholds,
    WeekRegime,
    side_thresholds_for_week,
    total_thresholds_for_week,
    week_regime,
)
from src.services.nfl_side_total_publish_policy import (
    SPREAD_PLAY_MAX,
    SPREAD_PLAY_MIN,
    TOTAL_PLAY_ENABLED,
)

# Re-export policy constants for existing imports / tests.
__all__ = [
    "BREAKEVEN_ATS_MINUS_110",
    "CONFIDENCE_BEST_BET_MIN",
    "CONFIDENCE_PLAY_MIN",
    "CONFIDENCE_TIER_BASE",
    "COVER_LEAN_MAX",
    "COVER_MODEL_WARNING",
    "COVER_PASS_MAX",
    "COVER_PLAY_MAX",
    "COVER_STRONG_MAX",
    "EARLY_SIDE",
    "INSEASON_SIDE",
    "LATE_SIDE",
    "SPREAD_KEY_NUMBERS",
    "STANDARD_SIDE",
    "TOTAL_KEY_NUMBERS",
    "TOTAL_PASS_MAX",
    "TOTAL_STRONG_MIN",
    "ActionLabel",
    "ConfidenceAssessment",
    "ConfidenceBand",
    "DecisionResult",
    "MarketConfirmation",
    "PlayToLadder",
    "PointGrade",
    "SidePointThresholds",
    "WeekRegime",
    "assess_confidence",
    "assess_market_confirmation",
    "build_side_play_to_ladder",
    "build_total_play_to_ladder",
    "confidence_band",
    "crosses_key_number",
    "decide_game",
    "decide_side",
    "decide_total",
    "evaluate_best_bet",
    "grade_cover_prob",
    "grade_side_points",
    "grade_total_points",
    "market_past_play_to",
    "prefer_key_number_edge",
    "side_thresholds_for_week",
    "total_thresholds_for_week",
    "week_regime",
]

ActionLabel = Literal[
    "PASS",
    "LEAN",
    "PLAY",
    "BEST VALUE",
    "ALERT",
    "STAY AWAY",
]

PointGrade = Literal["PASS", "LEAN", "PLAY", "STRONG PLAY", "EXCEPTIONAL"]
Market = Literal["spread", "total"]


class ConfidenceBand(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(frozen=True)
class PlayToLadder:
    """Execution plan for every PLAY / LEAN / BEST VALUE (and ALERT).

    Play-to formula (sides)
    -----------------------
    Let KEI = fair home spread, M = current home market, T = week thresholds.
    Remaining edge at home price H is |KEI − H|.

    - play_to (home): KEI + sign·T.play_min  where sign moves from KEI toward M
      Equivalently: the price where remaining |edge| equals play_min.
    - lean_to (home): KEI + sign·T.lean_max
    - pass_from (home): KEI + sign·T.pass_max

    Away display numbers are −home. Totals use the same remaining-edge idea
    with total thresholds (week1_boost applied in early regime).
    """

    side_or_total: str
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
    """Market movement as information — never updates the fair (KEI) line."""

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
    score = CONFIDENCE_TIER_BASE if base_score is None else float(base_score)
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
    e = abs(float(abs_edge))
    t = side_thresholds_for_week(week)
    if e < t.pass_max:
        return "PASS"
    if e < t.play_min:
        return "LEAN"
    if e < t.strong_min:
        return "PLAY"
    return "STRONG PLAY"


def grade_total_points(abs_edge: float, week: Optional[int] = None) -> PointGrade:
    e = abs(float(abs_edge))
    t = total_thresholds_for_week(week)
    if e < t.pass_max:
        return "PASS"
    if e < t.play_min:
        return "LEAN"
    if e < t.strong_min:
        return "PLAY"
    return "STRONG PLAY"


def grade_cover_prob(cover_prob: Optional[float]) -> Optional[PointGrade]:
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
    if abs(abs_edge_a - abs_edge_b) < 1e-9:
        if crosses_a and not crosses_b:
            return "a"
        if crosses_b and not crosses_a:
            return "b"
        return "tie"
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
    week: Optional[int] = None,
) -> PlayToLadder:
    """Play-To from KEI + week side thresholds (see PlayToLadder docstring)."""
    fair = float(fair_spread_home)
    market = float(market_spread_home)
    edge = fair - market
    abs_edge = abs(edge)
    t = side_thresholds_for_week(week)
    likes_home = edge < 0

    if likes_home:
        team = home_abbr
        market_num = market
        # Home prices worsen toward KEI (more negative / less positive).
        play_to = _round_half(fair + t.play_min)
        lean_to = _round_half(fair + t.lean_max)
        pass_from = _round_half(fair + t.pass_max)
        # Ensure play_to is the best (highest) of the three for home.
        ordered = sorted([play_to, lean_to, pass_from], reverse=True)
        play_to, lean_to, pass_from = ordered[0], ordered[1], ordered[2]
        note = f"Play {team} to {play_to:+g}; lean {lean_to:+g}; pass {pass_from:+g} or worse"
        label_num = market_num
    else:
        team = away_abbr
        market_num = -market
        # Away number: play_to where remaining edge = play_min → away = -(fair - play_min)
        play_to = _round_half(-(fair - t.play_min))
        lean_to = _round_half(-(fair - t.lean_max))
        pass_from = _round_half(-(fair - t.pass_max))
        # Away fav: better = larger algebraically; play_to ≥ lean_to ≥ pass_from
        ordered = sorted([play_to, lean_to, pass_from], reverse=True)
        play_to, lean_to, pass_from = ordered[0], ordered[1], ordered[2]
        note = f"Play {team} to {play_to:+g}; lean {lean_to:+g}; pass {pass_from:+g} or worse"
        label_num = market_num

    return PlayToLadder(
        side_or_total=f"{team} {label_num:+g}",
        play_to=play_to,
        lean_to=lean_to,
        pass_from=pass_from,
        fair_line=fair,
        market_line=market,
        edge_points=round(abs_edge, 3),
        notes=note,
    )


def build_total_play_to_ladder(
    *,
    fair_total: float,
    market_total: float,
    week: Optional[int] = None,
) -> PlayToLadder:
    """Play-To from KEI total + week total thresholds."""
    fair = float(fair_total)
    market = float(market_total)
    edge = fair - market
    abs_edge = abs(edge)
    t = total_thresholds_for_week(week)
    likes_over = edge > 0
    m = market

    if likes_over:
        play_to = _round_half(fair - t.play_min)
        lean_to = _round_half(fair - t.lean_max)
        pass_from = _round_half(fair - t.pass_max)
        # Over: better = lower; play_to ≤ lean_to ≤ pass_from
        ordered = sorted([play_to, lean_to, pass_from])
        play_to, lean_to, pass_from = ordered[0], ordered[1], ordered[2]
        label = f"Over {m:g}"
        note = (
            f"Play Over {play_to:g} or better; lean to {lean_to:g}; "
            f"pass {pass_from:g}+"
        )
    else:
        play_to = _round_half(fair + t.play_min)
        lean_to = _round_half(fair + t.lean_max)
        pass_from = _round_half(fair + t.pass_max)
        ordered = sorted([play_to, lean_to, pass_from], reverse=True)
        play_to, lean_to, pass_from = ordered[0], ordered[1], ordered[2]
        label = f"Under {m:g}"
        note = (
            f"Play Under {play_to:g} or better; lean to {lean_to:g}; "
            f"pass {pass_from:g} or lower"
        )

    return PlayToLadder(
        side_or_total=label,
        play_to=play_to,
        lean_to=lean_to,
        pass_from=pass_from,
        fair_line=fair,
        market_line=market,
        edge_points=round(abs_edge, 3),
        notes=note,
    )


def market_past_play_to(
    *,
    market_kind: Market,
    fair: float,
    market: float,
    ladder: PlayToLadder,
) -> bool:
    """True when current market is past play-to (price no longer PLAY-eligible)."""
    edge = float(fair) - float(market)
    if market_kind == "spread":
        likes_home = edge < 0
        if likes_home:
            # Home: worse = lower. Past play-to when market < play_to.
            return float(market) < float(ladder.play_to) - 1e-9
        away_mkt = -float(market)
        return away_mkt < float(ladder.play_to) - 1e-9
    # totals
    likes_over = edge > 0
    if likes_over:
        return float(market) > float(ladder.play_to) + 1e-9
    return float(market) < float(ladder.play_to) - 1e-9


def assess_market_confirmation(
    *,
    model_fair: Optional[float],
    opening: Optional[float],
    current: Optional[float],
    closing: Optional[float] = None,
    likes_home_or_over: Optional[bool] = None,
) -> MarketConfirmation:
    confirms: Optional[bool] = None
    weakens: Optional[bool] = None
    note = "Market movement is information only; fair line unchanged."
    if (
        model_fair is not None
        and opening is not None
        and current is not None
        and likes_home_or_over is not None
    ):
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


def _cover_wins(
    point_grade: PointGrade,
    cover_grade: Optional[PointGrade],
) -> PointGrade:
    """When cover prob is available it wins for the tag; both are still shown."""
    if cover_grade is None:
        return point_grade
    return cover_grade


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
    """Strict Best Value — largest raw discrepancy alone does NOT qualify."""
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


def _confidence_ok_for_play(conf: ConfidenceAssessment) -> bool:
    if conf.band == ConfidenceBand.LOW.value:
        return False
    if conf.score < CONFIDENCE_PLAY_MIN:
        return False
    if "qb_unresolved" in conf.unresolved_flags:
        return False
    return True


def _major_uncertainty(conf: ConfidenceAssessment) -> bool:
    return any(
        f in conf.unresolved_flags
        for f in (
            "qb_unresolved",
            "injury_unresolved",
            "weather_unresolved",
            "conflicting_inputs",
        )
    )


def _spread_edge_in_play_band(abs_edge: float) -> bool:
    """Locked holdout band spread_play_v2_cap7: 2.5 ≤ |edge| < 7.0."""
    e = abs(float(abs_edge))
    return SPREAD_PLAY_MIN <= e < SPREAD_PLAY_MAX


def _apply_spread_play_holdout_band(
    label: ActionLabel, abs_edge: float, reason: str
) -> Tuple[ActionLabel, str, bool]:
    """Never emit PLAY/BEST VALUE outside the locked holdout band.

    See NFL_SPREAD_PLAY_LOCKED.md (Ryan Kos 2026-09-03).
    """
    if label not in ("PLAY", "BEST VALUE"):
        return label, reason, label == "BEST VALUE"
    if _spread_edge_in_play_band(abs_edge):
        return label, reason, label == "BEST VALUE"
    e = abs(float(abs_edge))
    tagged = f"{reason}|outside_spread_play_v2_cap7"
    if e >= SPREAD_PLAY_MAX:
        return "PASS", tagged, False
    if e >= 1.0:
        return "LEAN", tagged, False
    return "PASS", tagged, False


def _apply_totals_play_sat(
    label: ActionLabel, reason: str
) -> Tuple[ActionLabel, str, bool]:
    """Totals PLAY stays sat until a new unused holdout greens."""
    if TOTAL_PLAY_ENABLED:
        return label, reason, label == "BEST VALUE"
    if label not in ("PLAY", "BEST VALUE"):
        return label, reason, False
    return "LEAN", f"{reason}|totals_play_sat", False


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
    """Grade a side: KEI fair vs best market → Action Label + Play-To."""
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

    fair = float(fair_spread_home)
    market = float(market_spread_home)
    edge = fair - market
    abs_edge = abs(edge)
    point_grade = grade_side_points(abs_edge, week)
    cover_grade = grade_cover_prob(cover_prob)
    effective = _cover_wins(point_grade, cover_grade)
    key_cross = crosses_key_number(fair, market, market_kind="spread")
    if key_cross and point_grade == "LEAN" and abs_edge >= 2.0:
        if cover_grade is None and _point_rank(effective) < _point_rank("PLAY"):
            effective = "PLAY"
        if point_grade == "LEAN":
            point_grade = "PLAY"

    ladder = build_side_play_to_ladder(
        fair_spread_home=fair,
        market_spread_home=market,
        home_abbr=home_abbr,
        away_abbr=away_abbr,
        week=week,
    )
    past_play_to = market_past_play_to(
        market_kind="spread", fair=fair, market=market, ladder=ladder
    )
    # On refresh: market past play-to downgrades — cap cover-inflated PLAY tags.
    if past_play_to and _point_rank(effective) >= _point_rank("PLAY"):
        effective = point_grade if _point_rank(point_grade) < _point_rank("PLAY") else "LEAN"
    price_ok = bool(price_still_available) and not past_play_to

    model_warning = bool(cover_prob is not None and float(cover_prob) >= COVER_MODEL_WARNING)
    numerical_edge = effective in ("LEAN", "PLAY", "STRONG PLAY", "EXCEPTIONAL")
    confidence_ok = _confidence_ok_for_play(conf)
    major_uncertainty = _major_uncertainty(conf)

    if stay_away or "conflicting_inputs" in conf.unresolved_flags:
        label: ActionLabel = "STAY AWAY"
        reason = "conflicting_inputs_or_bad_market"
        out_ladder: Optional[PlayToLadder] = None
    elif numerical_edge and (major_uncertainty or conf.band == ConfidenceBand.LOW.value):
        label = "ALERT"
        reason = (
            "edge_with_low_confidence"
            if conf.band == ConfidenceBand.LOW.value and not major_uncertainty
            else "edge_with_material_uncertainty"
        )
        out_ladder = ladder
    elif effective == "PASS":
        label = "PASS"
        reason = "edge_below_week_threshold"
        out_ladder = None
    elif effective == "LEAN":
        label = "LEAN"
        reason = "mild_edge_watch_list" + ("|past_play_to" if past_play_to else "")
        out_ladder = ladder
    elif numerical_edge and confidence_ok and price_ok:
        is_bb = evaluate_best_bet(
            point_grade=effective if effective != "EXCEPTIONAL" else "STRONG PLAY",
            confidence=conf,
            price_available=price_ok,
            key_number_cross=key_cross,
            market_confirmation=mc,
            matchup_support=matchup_support,
            liquidity_ok=liquidity_ok,
        )
        label = "BEST VALUE" if is_bb else "PLAY"
        reason = "best_bet_strict_cleared" if is_bb else "play_triple_cleared"
        out_ladder = ladder
    elif numerical_edge and not price_ok:
        label = "ALERT" if _point_rank(point_grade) >= _point_rank("PLAY") else "LEAN"
        reason = "edge_but_price_gone|past_play_to" if past_play_to else "edge_but_price_gone"
        out_ladder = ladder
    elif numerical_edge and not confidence_ok:
        label = "ALERT"
        reason = "edge_but_confidence_insufficient"
        out_ladder = ladder
    else:
        label = "LEAN"
        reason = "partial_play_requirements"
        out_ladder = ladder

    if model_warning and label in ("PLAY", "BEST VALUE", "LEAN"):
        reason = f"{reason}|model_warning_60pct_plus_ats"

    label, reason, is_bb = _apply_spread_play_holdout_band(label, abs_edge, reason)

    return DecisionResult(
        market="spread",
        action_label=label,
        point_grade=point_grade,
        edge_magnitude=round(abs_edge, 3),
        model_confidence=conf,
        cover_prob=cover_prob,
        cover_grade=cover_grade,
        play_to=out_ladder,
        market_confirmation=mc,
        is_best_bet=is_bb,
        model_warning=model_warning,
        key_number_cross=key_cross,
        price_still_available=price_ok,
        numerical_edge=numerical_edge,
        confidence_ok=confidence_ok,
        reason=reason,
        week=week,
        week_regime=regime,
        fair_line=fair,
        market_line=market,
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
    """Grade a total: KEI fair vs best market → Action Label + Play-To."""
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

    fair = float(fair_total)
    market = float(market_total)
    edge = fair - market
    abs_edge = abs(edge)
    point_grade = grade_total_points(abs_edge, week)
    cover_side_prob = over_prob
    if over_prob is not None and edge < 0:
        cover_side_prob = 1.0 - float(over_prob)
    cover_grade = grade_cover_prob(cover_side_prob)
    effective = _cover_wins(point_grade, cover_grade)
    key_cross = crosses_key_number(fair, market, market_kind="total")

    ladder = build_total_play_to_ladder(
        fair_total=fair, market_total=market, week=week
    )
    past_play_to = market_past_play_to(
        market_kind="total", fair=fair, market=market, ladder=ladder
    )
    if past_play_to and _point_rank(effective) >= _point_rank("PLAY"):
        effective = point_grade if _point_rank(point_grade) < _point_rank("PLAY") else "LEAN"
    price_ok = bool(price_still_available) and not past_play_to

    model_warning = bool(
        cover_side_prob is not None and float(cover_side_prob) >= COVER_MODEL_WARNING
    )
    numerical_edge = effective in ("LEAN", "PLAY", "STRONG PLAY", "EXCEPTIONAL")
    confidence_ok = _confidence_ok_for_play(conf)
    major_uncertainty = _major_uncertainty(conf) and conf.score < CONFIDENCE_PLAY_MIN

    if stay_away or "conflicting_inputs" in conf.unresolved_flags:
        label: ActionLabel = "STAY AWAY"
        reason = "conflicting_inputs_or_bad_market"
        out_ladder: Optional[PlayToLadder] = None
    elif numerical_edge and (major_uncertainty or conf.band == ConfidenceBand.LOW.value):
        label = "ALERT"
        reason = (
            "edge_with_low_confidence"
            if conf.band == ConfidenceBand.LOW.value
            else "edge_with_material_uncertainty"
        )
        out_ladder = ladder
    elif effective == "PASS":
        label = "PASS"
        reason = "edge_below_total_threshold"
        out_ladder = None
    elif effective == "LEAN":
        label = "LEAN"
        reason = "mild_edge_watch_list" + ("|past_play_to" if past_play_to else "")
        out_ladder = ladder
    elif numerical_edge and confidence_ok and price_ok:
        is_bb = evaluate_best_bet(
            point_grade=effective if effective != "EXCEPTIONAL" else "STRONG PLAY",
            confidence=conf,
            price_available=price_ok,
            key_number_cross=key_cross,
            market_confirmation=mc,
            matchup_support=matchup_support,
            liquidity_ok=liquidity_ok,
        )
        label = "BEST VALUE" if is_bb else "PLAY"
        reason = "best_bet_strict_cleared" if is_bb else "play_triple_cleared"
        out_ladder = ladder
    elif numerical_edge and not price_ok:
        label = "ALERT" if _point_rank(point_grade) >= _point_rank("PLAY") else "LEAN"
        reason = "edge_but_price_gone|past_play_to" if past_play_to else "edge_but_price_gone"
        out_ladder = ladder
    elif numerical_edge and not confidence_ok:
        label = "ALERT"
        reason = "edge_but_confidence_insufficient"
        out_ladder = ladder
    else:
        label = "LEAN"
        reason = "partial_play_requirements"
        out_ladder = ladder

    label, reason, is_bb = _apply_totals_play_sat(label, reason)

    return DecisionResult(
        market="total",
        action_label=label,
        point_grade=point_grade,
        edge_magnitude=round(abs_edge, 3),
        model_confidence=conf,
        cover_prob=cover_side_prob,
        cover_grade=cover_grade,
        play_to=out_ladder,
        market_confirmation=mc,
        is_best_bet=is_bb,
        model_warning=model_warning,
        key_number_cross=key_cross,
        price_still_available=price_ok,
        numerical_edge=numerical_edge,
        confidence_ok=confidence_ok,
        reason=reason,
        week=week,
        week_regime=regime,
        fair_line=fair,
        market_line=market,
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
    """Full-game tag payload for fair-lines / Edge Board rows (KEI vs market)."""
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
