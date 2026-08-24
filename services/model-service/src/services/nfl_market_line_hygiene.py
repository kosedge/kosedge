"""Strict NFL Current-line hygiene.

Current on Edge must look like a posted book line. Invalid → None (honest empty).
Never round / invent a nearby half-point (e.g. −3.58 must not become −3.5).

Consensus is the mode of samples that already pass the validator — not AVG.
AVG of real books is how 3.8 / 2.4 / −3.58 leak onto the board.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Literal, Optional, Sequence, Tuple

MarketKind = Literal["spread", "total", "ml"]

# Posted NFL sides are half-points in a tight window. PK (0) is rejected on purpose.
SPREAD_ABS_MIN = 0.5
SPREAD_ABS_MAX = 20.5
# Posted NFL totals: typically 30–65, .0 or .5.
TOTAL_MIN = 30.0
TOTAL_MAX = 65.0
# American ML; decimal ML only when the column is ML.
ML_AMERICAN_ABS_MIN = 100.0
ML_AMERICAN_ABS_MAX = 100_000.0
ML_DECIMAL_MIN = 1.01
ML_DECIMAL_MAX = 50.0

_HALF_POINT_EPS = 1e-6

CURRENT_SPREAD_FIELDS: Tuple[str, ...] = (
    "market_spread_home",
    "best_spread_home",
    "dk_spread_home",
    "fd_spread_home",
    "stake_spread_home",
)
CURRENT_TOTAL_FIELDS: Tuple[str, ...] = (
    "market_total",
    "best_total",
    "dk_total",
    "fd_total",
    "stake_total",
)
CURRENT_ML_FIELDS: Tuple[str, ...] = (
    "market_home_ml",
    "market_away_ml",
)


def to_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(out):
        return None
    return out


def coerce_numeric_samples(raw: Any) -> List[float]:
    """Normalize json_agg / array_agg / scalar snapshot payloads to floats."""
    if raw is None or raw == "":
        return []
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        try:
            raw = json.loads(text)
        except (TypeError, ValueError):
            one = to_float(text)
            return [one] if one is not None else []
    if isinstance(raw, (list, tuple)):
        out: List[float] = []
        for item in raw:
            num = to_float(item)
            if num is not None:
                out.append(num)
        return out
    one = to_float(raw)
    return [one] if one is not None else []


def is_nfl_half_point(value: float, *, eps: float = _HALF_POINT_EPS) -> bool:
    doubled = value * 2.0
    return abs(doubled - round(doubled)) < eps


def canonicalize_half_point(value: float) -> float:
    """Snap a value already known to be on the half-point grid (no invention)."""
    return round(value * 2.0) / 2.0


def sanitize_nfl_spread(value: Any) -> Tuple[Optional[float], Optional[str]]:
    """Return (canonical spread, None) or (None, reject_reason)."""
    if value is None or value == "":
        return None, "null"
    num = to_float(value)
    if num is None:
        return None, "non_finite"
    if abs(num) < 1e-12:
        return None, "zero"
    abs_n = abs(num)
    if not is_nfl_half_point(num):
        if 0 < abs_n < 1:
            return None, "looks_like_probability"
        if abs_n >= ML_AMERICAN_ABS_MIN:
            return None, "looks_like_ml"
        if abs_n >= TOTAL_MIN:
            return None, "looks_like_total"
        if abs_n > SPREAD_ABS_MAX:
            return None, "out_of_range"
        return None, "not_half_point"
    if abs_n >= ML_AMERICAN_ABS_MIN:
        return None, "looks_like_ml"
    if abs_n >= TOTAL_MIN:
        return None, "looks_like_total"
    if abs_n < SPREAD_ABS_MIN or abs_n > SPREAD_ABS_MAX:
        return None, "out_of_range"
    return canonicalize_half_point(num), None


def sanitize_nfl_total(value: Any) -> Tuple[Optional[float], Optional[str]]:
    if value is None or value == "":
        return None, "null"
    num = to_float(value)
    if num is None:
        return None, "non_finite"
    if abs(num) < 1e-12:
        return None, "zero"
    if 0 < num < 1:
        return None, "looks_like_probability"
    if num < TOTAL_MIN:
        return None, "looks_like_spread" if abs(num) <= SPREAD_ABS_MAX else "out_of_range"
    if num > TOTAL_MAX:
        return None, "out_of_range"
    if not is_nfl_half_point(num):
        return None, "not_half_point"
    return canonicalize_half_point(num), None


def sanitize_nfl_ml(value: Any) -> Tuple[Optional[float], Optional[str]]:
    """American ML, or clear decimal ML. Never used to paint the spread slot."""
    if value is None or value == "":
        return None, "null"
    num = to_float(value)
    if num is None:
        return None, "non_finite"
    if abs(num) < 1e-12:
        return None, "zero"
    if 0 < abs(num) < 1:
        return None, "looks_like_probability"
    # American: integer, |n| ≥ 100.
    if abs(num - round(num)) < _HALF_POINT_EPS:
        american = float(int(round(num)))
        if ML_AMERICAN_ABS_MIN <= abs(american) <= ML_AMERICAN_ABS_MAX:
            return american, None
        return None, "out_of_range"
    if is_nfl_half_point(num) and abs(num) <= SPREAD_ABS_MAX:
        return None, "looks_like_spread"
    # 3.8 / 2.4 class leaked into the ML column — not a book ML.
    frac = abs(num - math.trunc(num))
    tenth = frac * 10.0
    if abs(tenth - round(tenth)) < _HALF_POINT_EPS:
        digit = int(round(tenth)) % 10
        if digit in {2, 4, 6, 8}:
            return None, "looks_like_spread"
    # Decimal ML (1.91 class) — only valid in the ML column.
    if ML_DECIMAL_MIN <= num <= ML_DECIMAL_MAX:
        return round(num, 3), None
    return None, "not_american_or_decimal_ml"


def sanitize_nfl_line(value: Any, kind: MarketKind) -> Tuple[Optional[float], Optional[str]]:
    if kind == "spread":
        return sanitize_nfl_spread(value)
    if kind == "total":
        return sanitize_nfl_total(value)
    return sanitize_nfl_ml(value)


def _most_common_reason(reasons: Sequence[str]) -> str:
    if not reasons:
        return "no_samples"
    return Counter(reasons).most_common(1)[0][0]


def consensus_nfl_line(
    samples: Any,
    kind: MarketKind,
) -> Tuple[Optional[float], Optional[str]]:
    """Mode of validator-passing posted lines. Ties: smaller abs, then more negative.

    Does not average. A 50/50 −3 / −3.5 split becomes −3, never −3.25.
    """
    values = coerce_numeric_samples(samples)
    if not values:
        return None, "no_samples"
    valid: List[float] = []
    reasons: List[str] = []
    for item in values:
        cleaned, reason = sanitize_nfl_line(item, kind)
        if cleaned is None:
            reasons.append(reason or "rejected")
        else:
            valid.append(cleaned)
    if not valid:
        return None, _most_common_reason(reasons)
    if kind == "ml":
        counts = Counter(valid)
        best_count = max(counts.values())
        tied = [value for value, count in counts.items() if count == best_count]
        tied.sort(key=lambda v: (abs(v), v))
        return tied[0], None
    ticks = Counter(int(round(v * 2.0)) for v in valid)
    best_count = max(ticks.values())
    tied = [tick / 2.0 for tick, count in ticks.items() if count == best_count]
    tied.sort(key=lambda v: (abs(v), v))
    return tied[0], None


def consensus_nfl_spread(samples: Any) -> Tuple[Optional[float], Optional[str]]:
    return consensus_nfl_line(samples, "spread")


def consensus_nfl_total(samples: Any) -> Tuple[Optional[float], Optional[str]]:
    return consensus_nfl_line(samples, "total")


def consensus_nfl_ml(samples: Any) -> Tuple[Optional[float], Optional[str]]:
    return consensus_nfl_line(samples, "ml")


@dataclass
class CurrentHygieneStats:
    kept_spread: int = 0
    rejected_spread: int = 0
    kept_total: int = 0
    rejected_total: int = 0
    kept_ml: int = 0
    rejected_ml: int = 0
    reasons: Counter = field(default_factory=Counter)

    def record_painted(self, kind: MarketKind, *, had_candidate: bool, kept: bool, reason: Optional[str]) -> None:
        if not had_candidate:
            return
        if kept:
            if kind == "spread":
                self.kept_spread += 1
            elif kind == "total":
                self.kept_total += 1
            else:
                self.kept_ml += 1
            return
        if kind == "spread":
            self.rejected_spread += 1
        elif kind == "total":
            self.rejected_total += 1
        else:
            self.rejected_ml += 1
        self.reasons[f"{kind}:{reason or 'rejected'}"] += 1

    def as_dict(self) -> Dict[str, Any]:
        return {
            "kept_spread": self.kept_spread,
            "rejected_spread": self.rejected_spread,
            "kept_total": self.kept_total,
            "rejected_total": self.rejected_total,
            "kept_ml": self.kept_ml,
            "rejected_ml": self.rejected_ml,
            "reject_reasons": dict(self.reasons),
        }


def _sanitize_fields(
    market: Dict[str, Any],
    fields: Iterable[str],
    kind: MarketKind,
) -> Tuple[bool, bool, Optional[str]]:
    """Sanitize in place. Returns (had_candidate, kept_any, last_reject_reason)."""
    had = False
    kept = False
    last_reason: Optional[str] = None
    for field_name in fields:
        raw = market.get(field_name)
        if raw is None or raw == "":
            continue
        had = True
        cleaned, reason = sanitize_nfl_line(raw, kind)
        if cleaned is None:
            market[field_name] = None
            last_reason = reason
        else:
            market[field_name] = cleaned
            kept = True
    return had, kept, last_reason


def apply_nfl_current_hygiene(
    market: Dict[str, Any],
    stats: Optional[CurrentHygieneStats] = None,
) -> Dict[str, Any]:
    """Null invalid Current fields independently (spread / total / ML)."""
    had_s, kept_s, reason_s = _sanitize_fields(market, CURRENT_SPREAD_FIELDS, "spread")
    had_t, kept_t, reason_t = _sanitize_fields(market, CURRENT_TOTAL_FIELDS, "total")
    had_m, kept_m, reason_m = _sanitize_fields(market, CURRENT_ML_FIELDS, "ml")
    if stats is not None:
        stats.record_painted("spread", had_candidate=had_s, kept=kept_s, reason=reason_s)
        stats.record_painted("total", had_candidate=had_t, kept=kept_t, reason=reason_t)
        stats.record_painted("ml", had_candidate=had_m, kept=kept_m, reason=reason_m)
    return market


def resolve_snapshot_current(
    mapped: Dict[str, Any],
    *,
    samples_key: str,
    scalar_key: str,
    kind: MarketKind,
) -> Tuple[Optional[float], Optional[str]]:
    """Prefer latest-per-book samples (mode); scalar AVG is validated, never repaired."""
    samples = coerce_numeric_samples(mapped.get(samples_key))
    if samples:
        return consensus_nfl_line(samples, kind)
    raw = mapped.get(scalar_key)
    if raw is None or raw == "":
        return None, None
    return sanitize_nfl_line(raw, kind)
