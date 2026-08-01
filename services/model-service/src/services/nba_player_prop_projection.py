"""NBA player prop projections from stub minutes/usage + team pace (Phase 3).

Enterprise rules:
  - Project from owned box stubs — never invent from market lines.
  - Markets: pts, reb, ast, threes (Odds API player_* keys).
  - No cosmetic nudge toward books.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence

NBA_PROP_MARKETS = ("pts", "reb", "ast", "threes")
NBA_PROP_MODEL_VERSION = "nba-player-props-v1"

# Per-minute rates used when stub box rates are thin (league priors).
_DEFAULT_PER_MIN = {
    "pts": 0.48,
    "reb": 0.18,
    "ast": 0.12,
    "threes": 0.05,
}


@dataclass(frozen=True)
class NbaPlayerPropProjection:
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
    team_pace: float = 100.0,
    team_ortg: float = 114.0,
) -> List[NbaPlayerPropProjection]:
    """Project pts/reb/ast/threes for one player.

    Primary: minutes × per-min rates from stubs.
    Secondary: soft pace/efficiency scale (bounded) so team environment matters
    without overwriting role evidence.
    """
    mins = _clamp(float(minutes or 0.0), 0.0, 48.0)
    if mins < 4.0:
        return []

    pace_mul = _clamp(float(team_pace) / 100.0, 0.90, 1.12)
    ortg_mul = _clamp(float(team_ortg) / 114.0, 0.92, 1.10)
    env_mul = math.sqrt(pace_mul * ortg_mul)

    rates = {
        "pts": pts_per_min if pts_per_min and pts_per_min > 0 else _DEFAULT_PER_MIN["pts"],
        "reb": reb_per_min if reb_per_min and reb_per_min > 0 else _DEFAULT_PER_MIN["reb"],
        "ast": ast_per_min if ast_per_min and ast_per_min > 0 else _DEFAULT_PER_MIN["ast"],
        "threes": threes_per_min
        if threes_per_min and threes_per_min > 0
        else _DEFAULT_PER_MIN["threes"],
    }

    # Usage soft-scale: higher usage_proxy → slightly higher scoring/assist means.
    usage = max(0.0, float(usage_proxy or 0.0))
    usage_mul = _clamp(1.0 + (usage - 18.0) * 0.008, 0.85, 1.25)

    out: List[NbaPlayerPropProjection] = []
    for market in NBA_PROP_MARKETS:
        raw = mins * rates[market]
        if market in ("pts", "ast", "threes"):
            mean = raw * env_mul * (usage_mul if market != "reb" else 1.0)
        else:
            mean = raw * _clamp(pace_mul, 0.94, 1.08)

        # Dispersion grows with mean; floor so O/U probs are defined.
        std = _clamp(0.35 * math.sqrt(max(mean, 0.5)) + 0.8, 1.2, 12.0)
        if market == "threes":
            std = _clamp(0.45 * math.sqrt(max(mean, 0.2)) + 0.55, 0.7, 4.5)
        if market == "ast":
            std = _clamp(0.40 * math.sqrt(max(mean, 0.3)) + 0.7, 0.9, 6.0)

        source = "stub_rates" if sample_games >= 3 else "stub_rates_prior_mix"
        out.append(
            NbaPlayerPropProjection(
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
    """Collapse recent stub games into per-minute rates + minutes."""
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
    min_minutes: float = 12.0,
) -> List[NbaPlayerPropProjection]:
    pace_map = team_pace_by_key or {}
    ortg_map = team_ortg_by_key or {}
    projections: List[NbaPlayerPropProjection] = []
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
                team_pace=float(pace_map.get(tk, 100.0)),
                team_ortg=float(ortg_map.get(tk, 114.0)),
            )
        )
    return projections
