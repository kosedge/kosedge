from __future__ import annotations

from typing import Any, Dict, List


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def optimize_nfl_portfolio(
    *,
    candidates: List[Dict[str, Any]],
    bankroll: float,
    risk_profile: str,
    max_total_exposure: float,
    max_per_game_exposure: float,
    max_per_team_exposure: float,
    max_per_window_exposure: float,
    max_bet_fraction: float,
    correlation_penalty: float,
    max_per_player_exposure: float = 0.045,
    same_game_player_penalty: float = 0.30,
    qb_wr_correlation_penalty: float = 0.45,
) -> Dict[str, Any]:
    profile = {
        "conservative": {"stake_mul": 0.65, "min_score": 20.0, "edge_mul": 0.85},
        "balanced": {"stake_mul": 1.00, "min_score": 16.0, "edge_mul": 1.0},
        "aggressive": {"stake_mul": 1.25, "min_score": 13.0, "edge_mul": 1.18},
    }.get(risk_profile, {"stake_mul": 1.0, "min_score": 16.0, "edge_mul": 1.0})

    rejected: Dict[str, int] = {
        "low_quality": 0,
        "low_confidence": 0,
        "low_edge": 0,
        "game_exposure_cap": 0,
        "team_exposure_cap": 0,
        "window_exposure_cap": 0,
        "portfolio_exposure_cap": 0,
        "player_exposure_cap": 0,
        "min_bet_threshold": 0,
    }
    selected: List[Dict[str, Any]] = []
    excluded: List[Dict[str, Any]] = []
    game_exposure: Dict[str, float] = {}
    team_exposure: Dict[str, float] = {}
    player_exposure: Dict[str, float] = {}
    window_exposure: Dict[str, float] = {}
    game_player_group_exposure: Dict[str, float] = {}
    total_exposure = 0.0

    ranked = sorted(
        candidates,
        key=lambda edge: (
            _safe_float(edge.get("quality_score"), 0.0),
            abs(_safe_float(edge.get("ml_edge_prob"), 0.0)),
        ),
        reverse=True,
    )
    for edge in ranked:
        quality = _safe_float(edge.get("quality_score"), 0.0)
        confidence = _safe_float(edge.get("confidence_score"), 0.0)
        edge_prob = abs(_safe_float(edge.get("ml_edge_prob"), 0.0))
        if quality < profile["min_score"] * 3.0:
            rejected["low_quality"] += 1
            excluded.append({"candidate": edge, "reason": "low_quality"})
            continue
        if confidence < 0.30:
            rejected["low_confidence"] += 1
            excluded.append({"candidate": edge, "reason": "low_confidence"})
            continue
        if edge_prob < 0.005:
            rejected["low_edge"] += 1
            excluded.append({"candidate": edge, "reason": "low_edge"})
            continue

        game_id = str(edge.get("game_id") or "")
        home = str(edge.get("home_team") or "")
        away = str(edge.get("away_team") or "")
        window = str(edge.get("time_window") or "unknown")
        side = "home" if _safe_float(edge.get("ml_edge_prob"), 0.0) >= 0 else "away"
        team_selection = home if side == "home" else away
        player_id = str(edge.get("player_id") or edge.get("player_name") or "")
        market = str(edge.get("market") or "moneyline")
        position = str(edge.get("position") or "")
        corr_group = str(edge.get("correlation_group") or f"{game_id}:{market}:{position}:{player_id}")

        base = min(
            max_bet_fraction,
            max(
                0.001,
                (
                    (quality / 100.0)
                    * (0.35 + 0.65 * confidence)
                    * min(1.0, edge_prob / 0.045)
                    * 0.030
                    * profile["stake_mul"]
                    * profile["edge_mul"]
                ),
            ),
        )

        if game_id and game_id in game_exposure:
            base *= _clamp(1.0 - correlation_penalty, 0.05, 1.0)
        if team_selection and team_exposure.get(team_selection, 0.0) > 0.0:
            base *= _clamp(1.0 - (0.70 * correlation_penalty), 0.10, 1.0)
        if window_exposure.get(window, 0.0) > 0.0:
            base *= _clamp(1.0 - (0.45 * correlation_penalty), 0.20, 1.0)
        if player_id and player_exposure.get(player_id, 0.0) > 0.0:
            base *= _clamp(1.0 - (0.85 * correlation_penalty), 0.08, 1.0)
        if game_id and game_player_group_exposure.get(f"{game_id}:{corr_group}", 0.0) > 0.0:
            base *= _clamp(1.0 - same_game_player_penalty, 0.10, 1.0)
        if position == "WR" and game_id and game_player_group_exposure.get(f"{game_id}:QB_STACK", 0.0) > 0.0:
            base *= _clamp(1.0 - qb_wr_correlation_penalty, 0.05, 1.0)
        if position == "QB":
            base *= _clamp(1.0 - (0.25 * qb_wr_correlation_penalty), 0.15, 1.0)

        remaining_total = max(0.0, max_total_exposure - total_exposure)
        if remaining_total <= 0.0:
            rejected["portfolio_exposure_cap"] += 1
            excluded.append({"candidate": edge, "reason": "portfolio_exposure_cap"})
            continue

        remaining_game = max(0.0, max_per_game_exposure - game_exposure.get(game_id, 0.0))
        if remaining_game <= 0.0:
            rejected["game_exposure_cap"] += 1
            excluded.append({"candidate": edge, "reason": "game_exposure_cap"})
            continue
        remaining_home = max(0.0, max_per_team_exposure - team_exposure.get(home, 0.0))
        remaining_away = max(0.0, max_per_team_exposure - team_exposure.get(away, 0.0))
        if remaining_home <= 0.0 or remaining_away <= 0.0:
            rejected["team_exposure_cap"] += 1
            excluded.append({"candidate": edge, "reason": "team_exposure_cap"})
            continue
        remaining_window = max(0.0, max_per_window_exposure - window_exposure.get(window, 0.0))
        if remaining_window <= 0.0:
            rejected["window_exposure_cap"] += 1
            excluded.append({"candidate": edge, "reason": "window_exposure_cap"})
            continue
        remaining_player = max(0.0, max_per_player_exposure - player_exposure.get(player_id, 0.0))
        if player_id and remaining_player <= 0.0:
            rejected["player_exposure_cap"] += 1
            excluded.append({"candidate": edge, "reason": "player_exposure_cap"})
            continue

        final_stake = min(
            base,
            remaining_total,
            remaining_game,
            remaining_home,
            remaining_away,
            remaining_window,
            remaining_player if player_id else max_bet_fraction,
        )
        if final_stake < 0.001:
            rejected["min_bet_threshold"] += 1
            excluded.append({"candidate": edge, "reason": "min_bet_threshold"})
            continue

        game_exposure[game_id] = game_exposure.get(game_id, 0.0) + final_stake
        team_exposure[home] = team_exposure.get(home, 0.0) + final_stake
        team_exposure[away] = team_exposure.get(away, 0.0) + final_stake
        window_exposure[window] = window_exposure.get(window, 0.0) + final_stake
        if player_id:
            player_exposure[player_id] = player_exposure.get(player_id, 0.0) + final_stake
        if game_id:
            game_player_group_exposure[f"{game_id}:{corr_group}"] = game_player_group_exposure.get(f"{game_id}:{corr_group}", 0.0) + final_stake
            if position == "QB":
                game_player_group_exposure[f"{game_id}:QB_STACK"] = game_player_group_exposure.get(f"{game_id}:QB_STACK", 0.0) + final_stake
        total_exposure += final_stake

        selected.append(
            {
                **edge,
                "selection": side,
                "recommended_stake_fraction": round(final_stake, 4),
                "recommended_stake_amount": round(final_stake * bankroll, 2),
                "correlation_penalized": bool(game_id in game_exposure and game_exposure[game_id] > final_stake),
                "diagnostics": {
                    "corr_group": corr_group,
                    "position": position,
                    "player_id": player_id,
                },
            }
        )

    return {
        "recommendations": selected,
        "diagnostics": {
            "input_count": len(candidates),
            "selected_count": len(selected),
            "excluded_count": max(0, len(candidates) - len(selected)),
            "excluded_reasons": rejected,
            "exposure_utilization": {
                "total": round(total_exposure, 4),
                "total_limit": round(max_total_exposure, 4),
                "game_exposure": {k: round(v, 4) for k, v in game_exposure.items()},
                "team_exposure": {k: round(v, 4) for k, v in sorted(team_exposure.items())},
                "player_exposure": {k: round(v, 4) for k, v in sorted(player_exposure.items())},
                "time_window_exposure": {k: round(v, 4) for k, v in sorted(window_exposure.items())},
            },
            "excluded_examples": excluded[:30],
        },
    }

