"""Normalize sport-specific projection payloads into the unified proof schema."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional


def _opt_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def payload_from_cfb_project_game(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Map CFB project-game / log body fields to unified proof payload."""
    return {
        "sport": "cfb",
        "market_type": str(payload.get("market_type") or "game"),
        "home_team": payload.get("home_team"),
        "away_team": payload.get("away_team"),
        "season": payload.get("season"),
        "week": payload.get("week"),
        "game_key": payload.get("game_key"),
        "engine_version": payload.get("engine_version"),
        "projected_at": payload.get("projected_at"),
        "spread_home": payload.get("spread_home"),
        "model_spread_home": payload.get("model_spread_home"),
        "expected_total": payload.get("expected_total"),
        "model_total": payload.get("model_total"),
        "home_win_prob": payload.get("home_win_prob"),
        "away_win_prob": payload.get("away_win_prob"),
        "expected_home_score": payload.get("expected_home_score"),
        "expected_away_score": payload.get("expected_away_score"),
        "drivers": payload.get("drivers") or {},
        "kei_spread_home": (payload.get("kei") or {}).get("kei_spread_home")
        if isinstance(payload.get("kei"), Mapping)
        else payload.get("kei_spread_home"),
        "kei_version": (payload.get("kei") or {}).get("kei_version")
        if isinstance(payload.get("kei"), Mapping)
        else payload.get("kei_version"),
        "projection": {
            "game_id": payload.get("game_id"),
            "margin_sd": payload.get("margin_sd"),
            "fidelity": payload.get("fidelity"),
            "mode": payload.get("mode"),
            "notes": payload.get("notes"),
            "source": payload.get("source") or "cfb/season-engine/project-game",
            "kei": payload.get("kei"),
        },
    }


def payload_from_nfl_game_boxes(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Map NFL season-engine game-boxes output to unified proof payload."""
    summary = dict(payload.get("game_script_summary") or {})
    eh = _opt_float(summary.get("expected_home_score_mean"))
    ea = _opt_float(summary.get("expected_away_score_mean"))
    spread: Optional[float] = None
    if eh is not None and ea is not None:
        spread = round(-(eh - ea), 2)
    home_wp = _opt_float(summary.get("home_win_prob_mean"))
    away_wp = None
    if home_wp is not None:
        away_wp = round(1.0 - home_wp, 4)
    total = _opt_float(summary.get("expected_total_mean"))
    return {
        "sport": "nfl",
        "market_type": "game",
        "home_team": payload.get("home_team"),
        "away_team": payload.get("away_team"),
        "season": payload.get("season"),
        "week": payload.get("week"),
        "engine_version": payload.get("engine_version"),
        "spread_home": spread,
        "model_spread_home": spread,
        "expected_total": total,
        "model_total": total,
        "home_win_prob": home_wp,
        "away_win_prob": away_wp,
        "expected_home_score": eh,
        "expected_away_score": ea,
        "projection": {
            "game_id": payload.get("game_id"),
            "mode": payload.get("mode"),
            "source": "nfl/season-engine/game-boxes",
            "n_replicates": payload.get("n_replicates"),
        },
    }
