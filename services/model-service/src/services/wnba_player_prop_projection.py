"""WNBA player prop projections from stub minutes/usage + team pace (Phase 3).

Enterprise rules:
  - Project from owned box stubs — never invent from market lines.
  - Markets: pts, reb, ast, threes.
  - WNBA priors (not NBA): shorter minutes (40), higher usage concentration.
  - No cosmetic nudge toward books.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence

from src.services.wnba_possession_simulator import WNBA_LEAGUE_ORTG, WNBA_LEAGUE_PACE

WNBA_PROP_MARKETS = ("pts", "reb", "ast", "threes")
WNBA_PROP_MODEL_VERSION = "wnba-player-props-v1"

# Per-minute rates (40-min game priors — higher scoring rate than NBA per-min).
_DEFAULT_PER_MIN = {
    "pts": 0.55,
    "reb": 0.22,
    "ast": 0.14,
    "threes": 0.055,
}


@dataclass(frozen=True)
class WnbaPlayerPropProjection:
    player_id: str
    player_name: str
    team_key: str
    market_key: str
    model_mean: float
    model_std: float
    minutes: float
    usage_proxy: float
    sample_games: int
    projection_source: str


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def project_player_markets(
    *,
    player_id: str,
    player_name: str,
    team_key: str,
    minutes: float,
    usage_proxy: float,
    pts_per_min: Optional[float] = None,
    reb_per_min: Optional[float] = None,
    ast_per_min: Optional[float] = None,
    threes_per_min: Optional[float] = None,
    sample_games: int = 0,
    team_pace: float = WNBA_LEAGUE_PACE,
    team_ortg: float = WNBA_LEAGUE_ORTG,
) -> List[WnbaPlayerPropProjection]:
    mins = _clamp(float(minutes or 0.0), 0.0, 40.0)
    if mins < 4.0:
        return []

    pace_mul = _clamp(float(team_pace) / WNBA_LEAGUE_PACE, 0.88, 1.14)
    ortg_mul = _clamp(float(team_ortg) / WNBA_LEAGUE_ORTG, 0.90, 1.12)
    env_mul = math.sqrt(pace_mul * ortg_mul)

    rates = {
        "pts": pts_per_min if pts_per_min and pts_per_min > 0 else _DEFAULT_PER_MIN["pts"],
        "reb": reb_per_min if reb_per_min and reb_per_min > 0 else _DEFAULT_PER_MIN["reb"],
        "ast": ast_per_min if ast_per_min and ast_per_min > 0 else _DEFAULT_PER_MIN["ast"],
        "threes": threes_per_min
        if threes_per_min and threes_per_min > 0
        else _DEFAULT_PER_MIN["threes"],
    }

    # Usage concentration often higher than NBA — stronger soft scale.
    usage = max(0.0, float(usage_proxy or 0.0))
    usage_mul = _clamp(1.0 + (usage - 16.0) * 0.010, 0.82, 1.35)

    out: List[WnbaPlayerPropProjection] = []
    for market in WNBA_PROP_MARKETS:
        raw = mins * rates[market]
        if market in ("pts", "ast", "threes"):
            mean = raw * env_mul * (usage_mul if market != "reb" else 1.0)
        else:
            mean = raw * _clamp(pace_mul, 0.92, 1.10)

        std = _clamp(0.38 * math.sqrt(max(mean, 0.5)) + 0.75, 1.0, 11.0)
        if market == "threes":
            std = _clamp(0.48 * math.sqrt(max(mean, 0.2)) + 0.50, 0.6, 4.0)
        if market == "ast":
            std = _clamp(0.42 * math.sqrt(max(mean, 0.3)) + 0.65, 0.8, 5.5)

        source = "stub_rates" if sample_games >= 3 else "stub_rates_prior_mix"
        out.append(
            WnbaPlayerPropProjection(
                player_id=str(player_id),
                player_name=str(player_name or player_id),
                team_key=str(team_key or "").upper(),
                market_key=market,
                model_mean=round(mean, 3),
                model_std=round(std, 3),
                minutes=round(mins, 2),
                usage_proxy=round(usage, 3),
                sample_games=int(sample_games or 0),
                projection_source=source,
            )
        )
    return out


def aggregate_stub_rows(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return {}
    minutes_sum = 0.0
    pts_sum = reb_sum = ast_sum = threes_sum = usage_sum = 0.0
    n = 0
    player_id = ""
    player_name = ""
    team_key = ""
    for r in rows:
        mins = _safe_float(r.get("minutes"))
        if mins <= 0:
            continue
        n += 1
        minutes_sum += mins
        pts_sum += _safe_float(r.get("pts"))
        reb_sum += _safe_float(r.get("reb"))
        ast_sum += _safe_float(r.get("ast"))
        threes_sum += _safe_float(r.get("fg3m"), _safe_float(r.get("threes")))
        usage_sum += _safe_float(r.get("usage_proxy"))
        player_id = str(r.get("player_id") or player_id)
        player_name = str(r.get("player_name") or player_name)
        team_key = str(r.get("team_key") or team_key)
    if n == 0 or minutes_sum <= 0:
        return {}
    return {
        "player_id": player_id,
        "player_name": player_name,
        "team_key": team_key,
        "minutes": minutes_sum / n,
        "usage_proxy": usage_sum / n,
        "pts_per_min": pts_sum / minutes_sum,
        "reb_per_min": reb_sum / minutes_sum,
        "ast_per_min": ast_sum / minutes_sum,
        "threes_per_min": threes_sum / minutes_sum,
        "sample_games": n,
    }


def project_from_stub_groups(
    groups: Iterable[Sequence[Dict[str, Any]]],
    *,
    team_pace_by_key: Optional[Dict[str, float]] = None,
    team_ortg_by_key: Optional[Dict[str, float]] = None,
    min_minutes: float = 10.0,
) -> List[WnbaPlayerPropProjection]:
    pace_map = team_pace_by_key or {}
    ortg_map = team_ortg_by_key or {}
    projections: List[WnbaPlayerPropProjection] = []
    for rows in groups:
        agg = aggregate_stub_rows(rows)
        if not agg or float(agg["minutes"]) < min_minutes:
            continue
        tk = str(agg["team_key"] or "").upper()
        projections.extend(
            project_player_markets(
                player_id=agg["player_id"],
                player_name=agg["player_name"],
                team_key=tk,
                minutes=float(agg["minutes"]),
                usage_proxy=float(agg["usage_proxy"]),
                pts_per_min=float(agg["pts_per_min"]),
                reb_per_min=float(agg["reb_per_min"]),
                ast_per_min=float(agg["ast_per_min"]),
                threes_per_min=float(agg["threes_per_min"]),
                sample_games=int(agg["sample_games"]),
                team_pace=float(pace_map.get(tk, WNBA_LEAGUE_PACE)),
                team_ortg=float(ortg_map.get(tk, WNBA_LEAGUE_ORTG)),
            )
        )
    return projections
