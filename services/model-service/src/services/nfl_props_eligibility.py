"""Investable NFL props universe — skill positions + involvement floors.

Primary Props board is a desk, not a roster export. Prefer missing rows over
OL / DL / K anytime-TD junk with 0.0 model means.

Tune floors here; do not softmax or invent markets in the UI.
"""

from __future__ import annotations

import json
from typing import Any, FrozenSet, Mapping, Optional, Sequence, Tuple

# Canonical groups. Aliases fold into these before the market matrix.
POSITION_ALIASES = {
    "HB": "RB",
    "FB": "RB",
    "OT": "OL",
    "OG": "OL",
    "C": "OL",
    "T": "OL",
    "G": "OL",
    "LT": "OL",
    "LG": "OL",
    "RG": "OL",
    "RT": "OL",
    "DE": "DL",
    "DT": "DL",
    "NT": "DL",
    "ILB": "LB",
    "OLB": "LB",
    "MLB": "LB",
    "CB": "DB",
    "S": "DB",
    "FS": "DB",
    "SS": "DB",
    "SAF": "DB",
    "P": "ST",
    "LS": "ST",
    "DEF": "DST",
}

SKILL_GROUPS: FrozenSet[str] = frozenset({"QB", "RB", "WR", "TE"})
EXCLUDED_GROUPS: FrozenSet[str] = frozenset({"OL", "DL", "LB", "DB", "ST", "DST"})

# v1 primary board. Kicker FG only if both layer + market exist (not yet).
MARKETS_BY_GROUP: Mapping[str, FrozenSet[str]] = {
    "QB": frozenset(
        {"pass_yds", "pass_tds", "completions", "attempts", "rush_yds", "anytime_td"}
    ),
    "RB": frozenset(
        {"rush_yds", "rush_att", "rec_yds", "receptions", "anytime_td"}
    ),
    "WR": frozenset({"rec_yds", "receptions", "anytime_td", "longest_reception"}),
    "TE": frozenset({"rec_yds", "receptions", "anytime_td", "longest_reception"}),
    "K": frozenset({"fg_made", "fg_att"}),
}

PRIMARY_BOARD_MARKETS: FrozenSet[str] = frozenset().union(*MARKETS_BY_GROUP.values())

# Model-mean floors. Starter-role rows may use the lower bound but never 0.0.
MEAN_FLOORS: Mapping[str, Mapping[str, float]] = {
    "pass_yds": {"QB": 150.0, "*": 150.0},
    "pass_tds": {"QB": 0.80, "*": 0.80},
    "completions": {"QB": 15.0, "*": 15.0},
    "attempts": {"QB": 22.0, "*": 22.0},
    "rush_yds": {"QB": 18.0, "RB": 25.0, "WR": 8.0, "*": 20.0},
    "rush_att": {"RB": 6.0, "*": 6.0},
    "rec_yds": {"RB": 8.0, "WR": 20.0, "TE": 18.0, "*": 15.0},
    "receptions": {"RB": 1.2, "WR": 2.5, "TE": 2.0, "*": 1.5},
    "anytime_td": {"QB": 0.12, "RB": 0.10, "WR": 0.08, "TE": 0.08, "*": 0.10},
    "longest_reception": {"WR": 12.0, "TE": 12.0, "*": 12.0},
    "fg_made": {"K": 1.2, "*": 1.2},
    "fg_att": {"K": 1.5, "*": 1.5},
}

# Depth / usage-rank starter probability after effective_skill_role_confidence.
STARTER_ROLE_CONFIDENCE = 0.55
# Absolute zero / placeholder: never show even for starters.
ZERO_MEAN_EPS = 1e-6
# Reliability `confidence` is independent of edge (PR 428). Do not use it as a
# placeholder signal — involvement floors + market join already gate junk.


def canonicalize_position(position: Optional[str]) -> str:
    pos = str(position or "").strip().upper()
    if not pos:
        return ""
    return POSITION_ALIASES.get(pos, pos)


def allowed_markets_for_position(position: Optional[str]) -> FrozenSet[str]:
    group = canonicalize_position(position)
    if group in EXCLUDED_GROUPS:
        return frozenset()
    return MARKETS_BY_GROUP.get(group, frozenset())


def mean_floor(market_key: str, position: Optional[str]) -> float:
    by_pos = MEAN_FLOORS.get(str(market_key or ""), {})
    group = canonicalize_position(position)
    if group in by_pos:
        return float(by_pos[group])
    return float(by_pos.get("*", 0.0))


def _volume(*, market_key: str, model_mean: Optional[float], line: Optional[float]) -> float:
    """Involvement proxy. ATD line is always 0.5 — do not treat it as volume."""
    mean = float(model_mean) if model_mean is not None else None
    if mean is not None and mean > ZERO_MEAN_EPS:
        return mean
    if str(market_key) == "anytime_td":
        return 0.0
    if line is not None and float(line) > ZERO_MEAN_EPS:
        return float(line)
    return 0.0


def is_investable_prop(
    *,
    market_key: str,
    position: Optional[str] = None,
    model_mean: Optional[float] = None,
    line: Optional[float] = None,
    confidence: Optional[float] = None,
    role_confidence: Optional[float] = None,
    market_joined: Optional[bool] = None,
) -> bool:
    """Hard filter for the primary Props board.

    Unknown position: still allow skill markets that clear involvement floors
    (covers rows whose diagnostics omitted position). Never allow ATD at 0.0.
    """
    mk = str(market_key or "").strip()
    if not mk:
        return False
    group = canonicalize_position(position)

    if group in EXCLUDED_GROUPS:
        return False
    if group == "K" and mk == "anytime_td":
        return False

    allowed = allowed_markets_for_position(group) if group else PRIMARY_BOARD_MARKETS - {"fg_made", "fg_att"}
    # Unknown position: skill counting + ATD only — never K FG placeholders.
    if not group:
        allowed = frozenset(
            {
                "pass_yds",
                "pass_tds",
                "completions",
                "attempts",
                "rush_yds",
                "rush_att",
                "rec_yds",
                "receptions",
                "anytime_td",
                "longest_reception",
            }
        )
    if mk not in allowed:
        return False

    volume = _volume(market_key=mk, model_mean=model_mean, line=line)
    if volume <= ZERO_MEAN_EPS:
        return False

    floor = mean_floor(mk, group or None)
    starter = (
        role_confidence is not None
        and float(role_confidence) >= STARTER_ROLE_CONFIDENCE
        and group in SKILL_GROUPS
    )
    # Starters still need real volume; floor is halved, not waived.
    need = floor * (0.5 if starter else 1.0)
    if volume + 1e-9 < need:
        return False

    # confidence / market_joined stay in the signature for callers, but reliability
    # confidence must not eligibility-drop (PR 428 — independent of edge).
    return True


def filter_investable_rows(rows: Sequence[Mapping[str, Any]]) -> Tuple[list, int]:
    """Return (kept, dropped_count). Reads board/API row dicts."""
    kept: list = []
    dropped = 0
    for row in rows:
        diagnostics = row.get("diagnostics")
        if isinstance(diagnostics, str):
            try:
                diagnostics = json.loads(diagnostics)
            except (TypeError, ValueError):
                diagnostics = {}
        if not isinstance(diagnostics, dict):
            diagnostics = {}
        position = row.get("position") or (diagnostics or {}).get("position")
        role_conf = (diagnostics or {}).get("role_confidence")
        market_over = row.get("market_over_price")
        market_under = row.get("market_under_price")
        joined = market_over is not None or market_under is not None
        if is_investable_prop(
            market_key=str(row.get("market_key") or ""),
            position=str(position) if position is not None else None,
            model_mean=_opt_float(row.get("model_mean")),
            line=_opt_float(row.get("line")),
            confidence=_opt_float(row.get("confidence")),
            role_confidence=_opt_float(role_conf),
            market_joined=joined,
        ):
            kept.append(row)
        else:
            dropped += 1
    return kept, dropped


def _opt_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    if n != n:  # NaN
        return None
    return n
