"""Bounded lineup / nowcast timing sharpness (Track 2).

Modes:
  off (default): production behavior unchanged at the sim-input layer
  sharp: per-side confirmation, both-sides gate for confirmed flag,
         late SP-clear allowance near first pitch, freshness=1 on live fetch
"""

from __future__ import annotations

import os
from dataclasses import replace
from typing import Any, Dict, Optional, Tuple

from .mlb_simulator import MlbGameInputs

LINEUP_TIMING_MODES = frozenset({"off", "sharp"})
LINEUP_TIMING_MODE = (os.getenv("MLB_LINEUP_TIMING_MODE") or "off").strip().lower()


def apply_lineup_timing_mode(mode: str) -> str:
    global LINEUP_TIMING_MODE
    normalized = (mode or "off").strip().lower()
    if normalized not in LINEUP_TIMING_MODES:
        raise ValueError(f"unsupported lineup timing mode: {mode}")
    LINEUP_TIMING_MODE = normalized
    return LINEUP_TIMING_MODE


def get_lineup_timing_mode() -> str:
    return LINEUP_TIMING_MODE


def reset_lineup_timing_mode_from_env() -> str:
    return apply_lineup_timing_mode((os.getenv("MLB_LINEUP_TIMING_MODE") or "off").strip().lower())


def per_side_lineup_confidence(
    *,
    known_home: int,
    known_away: int,
    probable_pitcher_home: Optional[str],
    probable_pitcher_away: Optional[str],
    hours_to_first_pitch: float = 12.0,
    freshness_score: float = 1.0,
) -> Dict[str, Any]:
    """Asymmetric confidence from per-side card completeness + timing ladder."""
    home_confirmed = int(known_home) >= 8
    away_confirmed = int(known_away) >= 8
    both_confirmed = home_confirmed and away_confirmed

    def _side_base(side_confirmed: bool) -> float:
        if side_confirmed:
            return 0.96
        if hours_to_first_pitch <= 1:
            return 0.88
        if hours_to_first_pitch <= 3:
            return 0.82
        if hours_to_first_pitch <= 6:
            return 0.76
        if hours_to_first_pitch <= 12:
            return 0.70
        return 0.64

    home = _side_base(home_confirmed)
    away = _side_base(away_confirmed)
    if probable_pitcher_home:
        home += 0.02
    if probable_pitcher_away:
        away += 0.02
    # Both-sides confirmation unlocks a small mutual bump (card is real).
    if both_confirmed:
        home = min(1.0, home + 0.02)
        away = min(1.0, away + 0.02)
    freshness = max(0.45, min(1.0, float(freshness_score)))
    home = max(0.35, min(1.0, home * freshness))
    away = max(0.35, min(1.0, away * freshness))
    return {
        "home": home,
        "away": away,
        "home_confirmed": home_confirmed,
        "away_confirmed": away_confirmed,
        "lineup_confirmed": both_confirmed,
    }


def allow_late_sp_clear(*, hours_to_first_pitch: float, lineup_confirmed: bool) -> bool:
    """Only clear scratched SP near first pitch when cards are real."""
    if get_lineup_timing_mode() != "sharp":
        return False
    return bool(lineup_confirmed) and float(hours_to_first_pitch) <= 3.0


def apply_lineup_timing_to_inputs(
    inputs: MlbGameInputs,
    *,
    known_home: int,
    known_away: int,
    hours_to_first_pitch: float = 3.0,
    freshness_score: float = 1.0,
) -> Tuple[MlbGameInputs, Dict[str, Any]]:
    """Rewrite confidence / confirmed flag when timing mode is sharp."""
    if get_lineup_timing_mode() != "sharp":
        return inputs, {"lineup_timing_mode": "off", "applied": False}

    conf = per_side_lineup_confidence(
        known_home=known_home,
        known_away=known_away,
        probable_pitcher_home=inputs.starter_home,
        probable_pitcher_away=inputs.starter_away,
        hours_to_first_pitch=hours_to_first_pitch,
        freshness_score=freshness_score,
    )
    firm_bump_home = 0.06 if conf["home_confirmed"] else 0.0
    firm_bump_away = 0.06 if conf["away_confirmed"] else 0.0
    updated = replace(
        inputs,
        lineup_confirmed=bool(conf["lineup_confirmed"]),
        lineup_confidence_home=float(conf["home"]),
        lineup_confidence_away=float(conf["away"]),
        info_freshness_score_home=max(0.35, min(1.0, float(freshness_score))),
        info_freshness_score_away=max(0.35, min(1.0, float(freshness_score))),
        starter_firmness_home=max(
            0.35, min(1.0, float(inputs.starter_firmness_home) + firm_bump_home)
        ),
        starter_firmness_away=max(
            0.35, min(1.0, float(inputs.starter_firmness_away) + firm_bump_away)
        ),
    )
    return updated, {
        "lineup_timing_mode": "sharp",
        "applied": True,
        "known_home": int(known_home),
        "known_away": int(known_away),
        "hours_to_first_pitch": float(hours_to_first_pitch),
        **conf,
    }


def known_players_from_context(context_payload: Dict[str, Any], side: str) -> int:
    """Count lineup players stamped on context JSON (home_lineup_players / away)."""
    key = "home_lineup_players" if side == "home" else "away_lineup_players"
    players = context_payload.get(key) if isinstance(context_payload, dict) else None
    if isinstance(players, list):
        return len(players)
    # Nested nowcast stamp
    nowcast = context_payload.get("lineup_nowcast") if isinstance(context_payload, dict) else None
    if isinstance(nowcast, dict):
        nested = nowcast.get(key) or nowcast.get(f"{side}_lineup_players")
        if isinstance(nested, list):
            return len(nested)
    return 0
