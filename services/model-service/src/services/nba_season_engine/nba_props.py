"""NBA Chapter 6 — props desk (dark only).

Desk on Chapter 5 PlayerProjection. Not a second scorer.
Shows proj vs joined line. Zero PLAY / WATCH tags (Ch9 grades first).

Registered (documented, not emitted in dark):
  PROP_PLAY            ≥ 4.0 abs AND ≥ 0.6σ
  PROP_PLAY_CAP_PER_SLATE = 8
Hard minutes gate: MIN < PROP_MINUTES_GATE → row omitted.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from src.services.nba_season_engine import priors as P
from src.services.nba_season_engine.player_projection import (
    load_player_projection_pack,
)

PROPS_VERSION = "nba-props-ch6-dark-v1"
POLICY_VERSION = "nba_props_ch6_dark_v1"

# Register (enterprise plan) — coded for gates/docs; dark mode never emits PLAY.
PROP_PLAY_ABS = 4.0
PROP_PLAY_SIGMA = 0.6
PROP_PLAY_CAP_PER_SLATE = 8
PROP_MINUTES_GATE = 12.0

NBA_PROP_MARKETS = ("pts", "reb", "ast", "threes")

MARKET_TO_VECTOR = {
    "pts": "PTS",
    "reb": "REB",
    "ast": "AST",
    "threes": "3PM",
}

DARK_ONLY = True  # Ch6 phase — force PASS until Ch9 harness + stake policy


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def game_level_std(market_key: str, mean: float) -> float:
    """Game-grain σ for desk math. Ch5 pack σ is season-rate dispersion — too tight for O/U."""
    m = max(float(mean), 0.2)
    mk = str(market_key).lower()
    if mk == "threes":
        return _clamp(0.45 * math.sqrt(m) + 0.55, 0.7, 4.5)
    if mk == "ast":
        return _clamp(0.40 * math.sqrt(m) + 0.7, 0.9, 6.0)
    if mk == "reb":
        return _clamp(0.35 * math.sqrt(m) + 0.8, 1.0, 8.0)
    return _clamp(0.35 * math.sqrt(m) + 0.8, 1.2, 12.0)


def would_clear_prop_play(*, abs_edge: float, z: float) -> bool:
    """Register check only — dark desk never uses this to tag."""
    return abs(float(abs_edge)) >= PROP_PLAY_ABS and abs(float(z)) >= PROP_PLAY_SIGMA


def projection_mean_std(player: Dict[str, Any], market_key: str) -> Optional[Tuple[float, float]]:
    mk = str(market_key).lower()
    vec = MARKET_TO_VECTOR.get(mk)
    if not vec:
        return None
    mean_raw = player.get(vec)
    if mean_raw is None:
        return None
    mean = float(mean_raw)
    # Prefer game-level σ for O/U; keep Ch5 σ in diagnostics.
    std = game_level_std(mk, mean)
    return mean, std


def evaluate_dark_prop(
    *,
    market_key: str,
    model_mean: float,
    model_std: float,
    line: Optional[float],
    minutes: float,
    over_price: Optional[int] = None,
    under_price: Optional[int] = None,
    best_trusted: bool = False,
) -> Dict[str, Any]:
    """Proj vs line math with forced PASS (dark)."""
    mk = str(market_key).lower()
    mean = float(model_mean)
    std = max(0.35, float(model_std))
    mins = float(minutes)

    if mins < PROP_MINUTES_GATE:
        return {
            "tag": "PASS",
            "tag_side": None,
            "reason": "minutes_gate",
            "stake_eligible": False,
            "policy_version": POLICY_VERSION,
            "dark_only": True,
            "market_joined": False,
            "model_mean": round(mean, 3),
            "model_std": round(std, 3),
            "minutes": round(mins, 2),
        }

    if line is None:
        return {
            "tag": "PASS",
            "tag_side": None,
            "reason": "no_market_line",
            "stake_eligible": False,
            "policy_version": POLICY_VERSION,
            "dark_only": True,
            "market_joined": False,
            "model_mean": round(mean, 3),
            "model_std": round(std, 3),
            "minutes": round(mins, 2),
            "over_prob": None,
            "under_prob": None,
            "edge_over": None,
            "edge_under": None,
            "z": None,
            "abs_edge": None,
            "would_clear_play": False,
        }

    line_f = float(line)
    z = (mean - line_f) / std
    if mk == "threes":
        over_prob = 1.0 - _normal_cdf((line_f + 0.5 - mean) / std)
    else:
        over_prob = 1.0 - _normal_cdf((line_f - mean) / std)
    over_prob = _clamp(over_prob, 0.02, 0.98)
    under_prob = 1.0 - over_prob
    # Without reliable two-way prices, edge vs 50/50 is research display only.
    edge_over = over_prob - 0.5
    edge_under = under_prob - 0.5
    if over_price is not None and under_price is not None:
        # Soft display only — still never PLAY in dark.
        try:
            from src.services.nba_prop_edge_policy import devig_two_way

            fo, fu, _vig = devig_two_way(over_price, under_price)
            if fo is not None and fu is not None:
                edge_over = over_prob - fo
                edge_under = under_prob - fu
        except Exception:
            pass

    abs_edge = abs(mean - line_f)
    clears = would_clear_prop_play(abs_edge=abs_edge, z=z)
    reason = "dark_proj_vs_line"
    if not best_trusted:
        reason = "dark_untrusted_or_no_best"
    elif clears:
        reason = "dark_would_clear_play_suppressed"

    return {
        "tag": "PASS",  # dark — zero PLAY
        "tag_side": None,
        "reason": reason,
        "stake_eligible": False,
        "policy_version": POLICY_VERSION,
        "dark_only": True,
        "market_joined": True,
        "model_mean": round(mean, 3),
        "model_std": round(std, 3),
        "line": line_f,
        "z": round(z, 3),
        "abs_edge": round(abs_edge, 3),
        "over_prob": round(over_prob, 4),
        "under_prob": round(under_prob, 4),
        "edge_over": round(edge_over, 4),
        "edge_under": round(edge_under, 4),
        "minutes": round(mins, 2),
        "would_clear_play": clears,
        "prop_play_abs": PROP_PLAY_ABS,
        "prop_play_sigma": PROP_PLAY_SIGMA,
        "market_over_price": over_price,
        "market_under_price": under_price,
    }


def build_dark_props_board(
    *,
    market_key: Optional[str] = None,
    team: Optional[str] = None,
    limit: int = 250,
    market_by_player: Optional[Dict[Tuple[str, str], Dict[str, Any]]] = None,
    best_trusted: bool = False,
) -> Dict[str, Any]:
    """Build Ch6 dark board from PlayerProjection pack (on-read)."""
    pack = load_player_projection_pack()
    if not pack.get("present"):
        return {
            "present": False,
            "props_version": PROPS_VERSION,
            "policy_version": POLICY_VERSION,
            "count": 0,
            "lines": [],
            "play_n": 0,
            "message": "PlayerProjection pack missing — Ch5 required",
        }

    mk_filter = (market_key or "").strip().lower() or None
    team_filter = (team or "").strip().upper() or None
    markets: Sequence[str] = (mk_filter,) if mk_filter else NBA_PROP_MARKETS
    if mk_filter and mk_filter not in NBA_PROP_MARKETS:
        return {
            "present": True,
            "props_version": PROPS_VERSION,
            "count": 0,
            "lines": [],
            "play_n": 0,
            "message": f"unsupported_market:{mk_filter}",
        }

    market_map = market_by_player or {}
    rows: List[Dict[str, Any]] = []
    suppressed_play = 0

    players: Iterable[Dict[str, Any]] = (pack.get("players") or {}).values()
    ordered = sorted(
        players,
        key=lambda r: (-float(r.get("MIN") or 0), str(r.get("player_name") or "")),
    )

    for player in ordered:
        mins = float(player.get("MIN") or 0.0)
        if mins < PROP_MINUTES_GATE:
            continue
        tk = str(player.get("team") or "").upper()
        if team_filter and tk != team_filter:
            continue
        pid = str(player.get("player_id") or "")
        pname = str(player.get("player_name") or pid)
        for mk in markets:
            ms = projection_mean_std(player, mk)
            if ms is None:
                continue
            mean, std = ms
            mkt = (
                market_map.get((pid.lower(), mk))
                or market_map.get((pname.lower(), mk))
                or {}
            )
            line = mkt.get("line")
            try:
                line_f = float(line) if line is not None else None
            except (TypeError, ValueError):
                line_f = None
            over_price = mkt.get("over_price")
            under_price = mkt.get("under_price")
            try:
                over_i = int(over_price) if over_price is not None else None
                under_i = int(under_price) if under_price is not None else None
            except (TypeError, ValueError):
                over_i = under_i = None

            edge = evaluate_dark_prop(
                market_key=mk,
                model_mean=mean,
                model_std=std,
                line=line_f,
                minutes=mins,
                over_price=over_i,
                under_price=under_i,
                best_trusted=best_trusted and line_f is not None,
            )
            if edge.get("would_clear_play"):
                suppressed_play += 1

            ch5_sigma = ((player.get("sigma") or {}).get(MARKET_TO_VECTOR[mk]))
            rows.append(
                {
                    "model_version": PROPS_VERSION,
                    "player_id": pid,
                    "player_name": pname,
                    "team": tk,
                    "market_key": mk,
                    "line": line_f,
                    "model_mean": edge.get("model_mean"),
                    "model_std": edge.get("model_std"),
                    "over_prob": edge.get("over_prob"),
                    "under_prob": edge.get("under_prob"),
                    "edge_over": edge.get("edge_over"),
                    "edge_under": edge.get("edge_under"),
                    "confidence": None,
                    "diagnostics": {
                        "tag": "PASS",
                        "tag_side": None,
                        "reason": edge.get("reason"),
                        "stake_eligible": False,
                        "z": edge.get("z"),
                        "abs_edge": edge.get("abs_edge"),
                        "minutes": mins,
                        "projection_source": "player_projection_ch5",
                        "ch5_sigma": ch5_sigma,
                        "policy_version": POLICY_VERSION,
                        "dark_only": True,
                        "would_clear_play": edge.get("would_clear_play"),
                    },
                    "stake_eligible": False,
                    "tag": "PASS",
                    "tag_side": None,
                }
            )

    # Sort: joined lines first by |mean−line|, then by minutes.
    def _sort_key(r: Dict[str, Any]) -> Tuple[int, float, float]:
        line = r.get("line")
        mean = float(r.get("model_mean") or 0)
        if line is None:
            return (1, 0.0, -float((r.get("diagnostics") or {}).get("minutes") or 0))
        return (0, -abs(mean - float(line)), -float((r.get("diagnostics") or {}).get("minutes") or 0))

    rows.sort(key=_sort_key)
    rows = rows[: max(1, int(limit))]

    play_n = sum(1 for r in rows if str(r.get("tag") or "").upper() == "PLAY")
    return {
        "present": True,
        "props_version": PROPS_VERSION,
        "policy_version": POLICY_VERSION,
        "engine_version": pack.get("engine_version") or P.ENGINE_VERSION,
        "object": "PlayerProjection",
        "dark_only": True,
        "PROP_PLAY_ABS": PROP_PLAY_ABS,
        "PROP_PLAY_SIGMA": PROP_PLAY_SIGMA,
        "PROP_PLAY_CAP_PER_SLATE": PROP_PLAY_CAP_PER_SLATE,
        "PROP_MINUTES_GATE": PROP_MINUTES_GATE,
        "TEAM_CARRY_SHRINK_unchanged": P.TEAM_CARRY_SHRINK,
        "count": len(rows),
        "lines": rows,
        "play_n": play_n,
        "suppressed_play_candidates": suppressed_play,
        "does_not": [
            "PLAY / WATCH tags (dark)",
            "stake-eligible props",
            "second scorer / stub rates as SoT",
            "fantasy board",
            "walking means to the book",
            "CFB/NFL",
            "Ch1/Ch2/Ch5 rematerialize",
        ],
    }


def documentation() -> Dict[str, Any]:
    return {
        "module": "src.services.nba_season_engine.nba_props",
        "props_version": PROPS_VERSION,
        "policy_version": POLICY_VERSION,
        "dark_only": DARK_ONLY,
        "PROP_PLAY_ABS": PROP_PLAY_ABS,
        "PROP_PLAY_SIGMA": PROP_PLAY_SIGMA,
        "PROP_PLAY_CAP_PER_SLATE": PROP_PLAY_CAP_PER_SLATE,
        "PROP_MINUTES_GATE": PROP_MINUTES_GATE,
        "markets": list(NBA_PROP_MARKETS),
        "reads": "PlayerProjection (Ch5)",
        "does_not": [
            "emit PLAY",
            "rescore player means",
            "fantasy",
            "CFB/NFL",
        ],
    }
