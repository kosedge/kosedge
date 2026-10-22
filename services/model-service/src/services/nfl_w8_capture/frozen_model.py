"""Frozen W8 predictor (RA-1). Isolated from production remat and hist rebuild.

LK-2 / LK-7..LK-10 are locked out of this model. LK-1 and LK-4 are resolved
per stream: neither stream applies the 0.30 close-blend; the independent
stream forbids market inputs entirely.

Predictions are deterministic (REPRO_MODE=byte_identical, PINNED_SEED unused
because there is no RNG). An independent rebuild must match bytes.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from src.services.nfl_w8_capture.constants import STREAM_INDEPENDENT, STREAM_MARKET
from src.services.nfl_w8_capture.streams import forbidden_independent_keys


# Pre-filed W8 constants. These are NOT the 2023–25 tuned pair (1.05 / 45.3).
W8_MODEL_VERSION = "nfl-w8-frozen-v1"
W8_HOME_FIELD_POINTS = 0.0
W8_PRIOR_TOTAL_POINTS = 43.0
W8_EPA_MARGIN_WEIGHT = 16.0
W8_EPA_TOTAL_WEIGHT = 10.0
W8_MARKET_BLEND_WEIGHT = 0.0
PINNED_SEED = 4141
REPRO_MODE = "byte_identical"
REPRO_TOLERANCE = None

FORBIDDEN_INPUT_NAMES = frozenset(
    {
        "packaged_epa",
        "season_epa",
        "season_level_epa",
        "prefer_packaged_epa",
        "nfl_2026_epa_pack",
    }
)

REQUIRED_FEATURES = (
    "home_off_epa_5g",
    "away_off_epa_5g",
    "home_def_epa_allowed_5g",
    "away_def_epa_allowed_5g",
)


class FrozenModelError(ValueError):
    """Frozen W8 model refused an input or leak."""


def _f(row: Mapping[str, Any], key: str) -> float:
    value = row.get(key)
    if value is None or value == "":
        raise FrozenModelError(f"RA-6: missing feature {key} (FAIL, stays in n)")
    return float(value)


def assert_no_lk10_season_epa(row: Mapping[str, Any]) -> None:
    for key in row:
        if str(key) in FORBIDDEN_INPUT_NAMES:
            raise FrozenModelError(f"LK-10: season-level EPA input {key} is forbidden")


def assert_lagged_epa(row: Mapping[str, Any]) -> None:
    game_week = row.get("game_week")
    feature_week = row.get("feature_week")
    if game_week is None or feature_week is None:
        raise FrozenModelError("LK-2: feature_week and game_week required (week match is not a proof)")
    if int(feature_week) >= int(game_week):
        raise FrozenModelError("LK-2: same-week EPA is forbidden (feature_week must be < game_week)")


def assert_observed_rest_injury(row: Mapping[str, Any]) -> None:
    if row.get("rest_observed") is not True:
        raise FrozenModelError("LK-9: rest must be observed (no default 7.0)")
    if row.get("injury_observed") is not True:
        raise FrozenModelError("LK-9: injury must be observed (no default 0.0)")
    if "rest_days_home" not in row or "rest_days_away" not in row:
        raise FrozenModelError("LK-9: rest days missing")
    if "home_injury_impact" not in row or "away_injury_impact" not in row:
        raise FrozenModelError("LK-9: injury impact missing")


def score_row(row: Mapping[str, Any], *, stream: str) -> dict[str, Any]:
    """Deterministic W8 score. No market blend. No supervised 16% overlay."""
    assert_no_lk10_season_epa(row)
    assert_lagged_epa(row)
    assert_observed_rest_injury(row)
    if stream == STREAM_INDEPENDENT:
        banned = forbidden_independent_keys(row)
        if banned:
            raise FrozenModelError(f"LK-4: independent stream has market keys {list(banned)}")
    off_h = _f(row, "home_off_epa_5g")
    off_a = _f(row, "away_off_epa_5g")
    def_h = _f(row, "home_def_epa_allowed_5g")
    def_a = _f(row, "away_def_epa_allowed_5g")
    rest_h = _f(row, "rest_days_home")
    rest_a = _f(row, "rest_days_away")
    inj_h = _f(row, "home_injury_impact")
    inj_a = _f(row, "away_injury_impact")
    rest_adj = 0.18 * (rest_h - rest_a)
    inj_adj = 2.75 * (inj_a - inj_h)
    margin = (
        ((off_h - def_a) - (off_a - def_h)) * W8_EPA_MARGIN_WEIGHT
        + W8_HOME_FIELD_POINTS
        + rest_adj
        + inj_adj
    )
    total = W8_PRIOR_TOTAL_POINTS + (off_h + off_a) * W8_EPA_TOTAL_WEIGHT
    # LK-1 / LK-4: blend weight is locked at 0.0 on both streams.
    if W8_MARKET_BLEND_WEIGHT != 0.0:
        raise FrozenModelError("LK-1: market blend weight must stay 0.0")
    spread_home = round(-margin, 4)
    total = round(total, 4)
    home_win_prob = round(0.5 + max(-0.45, min(0.45, margin / 28.0)), 4)
    return {
        "game_id": str(row.get("game_id") or ""),
        "spread_home": spread_home,
        "total": total,
        "home_win_prob": home_win_prob,
        "model_version": W8_MODEL_VERSION,
        "stream": stream,
        "blend_weight": W8_MARKET_BLEND_WEIGHT,
        "seed": PINNED_SEED,
        "repro_mode": REPRO_MODE,
    }


def predict_stream(
    rows: Sequence[Mapping[str, Any]],
    *,
    stream: str,
) -> list[dict[str, Any]]:
    if stream not in {STREAM_MARKET, STREAM_INDEPENDENT}:
        raise FrozenModelError(f"unknown stream {stream}")
    return [score_row(row, stream=stream) for row in rows]


def predictions_bytes(rows: Sequence[Mapping[str, Any]]) -> bytes:
    """Canonical JSONL for RA-2 byte-identical rebuild."""
    return "".join(json.dumps(dict(row), sort_keys=True, separators=(",", ":")) + "\n" for row in rows).encode(
        "utf-8"
    )


def rebuild_matches(left: bytes, right: bytes) -> bool:
    if REPRO_MODE != "byte_identical" or REPRO_TOLERANCE is not None:
        return False
    return left == right
