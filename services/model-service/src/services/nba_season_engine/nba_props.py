"""NBA Chapter 6 — props desk (dark only).

Phase: proj vs trusted Best. Zero PLAY. Zero LEAN.
Reads Ch5 PlayerProjection only — does not re-score.

edge = PlayerProjection[market] − trusted_Best

Odds-backed markets only (basketball_nba). Missing Odds key → missing
(do not guess). Current Odds client keys: pts reb ast threes pra.
PR / RA exist on Ch5 but Odds does not return them → not boarded.
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

# Register (enterprise plan) — coded for gates/docs; dark mode never emits PLAY/LEAN.
PROP_PLAY_ABS = 4.0
PROP_PLAY_SIGMA = 0.6
PROP_PLAY_CAP_PER_SLATE = 8
PROP_MINUTES_GATE = 12.0

# Odds client already maps these for basketball_nba (enterprise_training_pull).
ODDS_BACKED_MARKETS = ("pts", "reb", "ast", "threes", "pra")
# Ch5 vectors present but Odds client has no key → missing (not boarded).
ODDS_MISSING_VECTORS = ("PR", "RA")

NBA_PROP_MARKETS = ODDS_BACKED_MARKETS

MARKET_TO_VECTOR = {
    "pts": "PTS",
    "reb": "REB",
    "ast": "AST",
    "threes": "3PM",
    "pra": "PRA",
}

DARK_ONLY = True


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
    if mk == "pra":
        return _clamp(0.45 * math.sqrt(m) + 1.2, 2.0, 14.0)
    return _clamp(0.35 * math.sqrt(m) + 0.8, 1.2, 12.0)


def would_clear_prop_play(*, abs_edge: float, z: float) -> bool:
    """Register check only — dark desk never uses this to tag."""
    return abs(float(abs_edge)) >= PROP_PLAY_ABS and abs(float(z)) >= PROP_PLAY_SIGMA


def trust_prop_best(
    *,
    best: Optional[float],
    model_mean: Optional[float] = None,
    book_count: int = 1,
    preseason: bool = False,
) -> Dict[str, Any]:
    """Trusted Best gate for props. Untrusted → Best cleared to None (UI shows —)."""
    if preseason:
        return {"trusted": False, "best": None, "reason": "preseason"}
    if best is None:
        return {"trusted": False, "best": None, "reason": "no_market"}
    try:
        best_f = float(best)
    except (TypeError, ValueError):
        return {"trusted": False, "best": None, "reason": "no_market"}
    if not math.isfinite(best_f):
        return {"trusted": False, "best": None, "reason": "no_market"}
    if book_count < 1:
        return {"trusted": False, "best": None, "reason": "no_book"}
    # Absurd vs model: refuse fake books (same spirit as team ABSURD gate).
    if model_mean is not None:
        try:
            gap = abs(float(model_mean) - best_f)
            if gap > 40.0:
                return {"trusted": False, "best": None, "reason": "absurd_vs_proj"}
        except (TypeError, ValueError):
            pass
    return {"trusted": True, "best": best_f, "reason": "best"}


def projection_mean_std(player: Dict[str, Any], market_key: str) -> Optional[Tuple[float, float]]:
    mk = str(market_key).lower()
    vec = MARKET_TO_VECTOR.get(mk)
    if not vec:
        return None
    mean_raw = player.get(vec)
    if mean_raw is None:
        return None
    mean = float(mean_raw)
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
    book_count: int = 1,
    preseason: bool = False,
) -> Dict[str, Any]:
    """Proj vs trusted Best. edge = mean − Best. Tag always PASS (dark)."""
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
            "best": None,
            "edge": None,
            "minutes": round(mins, 2),
        }

    trust = trust_prop_best(
        best=line,
        model_mean=mean,
        book_count=book_count,
        preseason=preseason,
    )
    # Untrusted Best → cleared (—). Never invent a book.
    best_f = trust["best"] if trust["trusted"] else None
    trusted = bool(trust["trusted"]) and (best_trusted or trust["reason"] == "best")

    if best_f is None:
        return {
            "tag": "PASS",
            "tag_side": None,
            "reason": trust["reason"] if line is None else f"untrusted_{trust['reason']}",
            "stake_eligible": False,
            "policy_version": POLICY_VERSION,
            "dark_only": True,
            "market_joined": False,
            "model_mean": round(mean, 3),
            "model_std": round(std, 3),
            "best": None,
            "line": None,
            "edge": None,
            "over_prob": None,
            "under_prob": None,
            "edge_over": None,
            "edge_under": None,
            "z": None,
            "abs_edge": None,
            "would_clear_play": False,
            "minutes": round(mins, 2),
            "best_trusted": False,
            "trust_reason": trust["reason"],
        }

    # edge = PlayerProjection[market] − trusted_Best
    edge = mean - best_f
    z = edge / std
    if mk == "threes":
        over_prob = 1.0 - _normal_cdf((best_f + 0.5 - mean) / std)
    else:
        over_prob = 1.0 - _normal_cdf((best_f - mean) / std)
    over_prob = _clamp(over_prob, 0.02, 0.98)
    under_prob = 1.0 - over_prob
    edge_over = over_prob - 0.5
    edge_under = under_prob - 0.5
    if over_price is not None and under_price is not None:
        try:
            from src.services.nba_prop_edge_policy import devig_two_way

            fo, fu, _vig = devig_two_way(over_price, under_price)
            if fo is not None and fu is not None:
                edge_over = over_prob - fo
                edge_under = under_prob - fu
        except Exception:
            pass

    abs_edge = abs(edge)
    clears = would_clear_prop_play(abs_edge=abs_edge, z=z)
    reason = "dark_proj_vs_best"
    if clears:
        reason = "dark_would_clear_play_suppressed"

    return {
        "tag": "PASS",  # dark — zero PLAY / LEAN
        "tag_side": None,
        "reason": reason,
        "stake_eligible": False,
        "policy_version": POLICY_VERSION,
        "dark_only": True,
        "market_joined": True,
        "model_mean": round(mean, 3),
        "model_std": round(std, 3),
        "best": round(best_f, 3),
        "line": round(best_f, 3),  # alias for existing board field
        "edge": round(edge, 3),
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
        "best_trusted": True,
        "trust_reason": trust["reason"],
    }


def build_dark_props_board(
    *,
    market_key: Optional[str] = None,
    team: Optional[str] = None,
    limit: int = 250,
    market_by_player: Optional[Dict[Tuple[str, str], Dict[str, Any]]] = None,
    best_trusted: bool = True,
    preseason: bool = False,
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
            "lean_n": 0,
            "message": "PlayerProjection pack missing — Ch5 required",
        }

    mk_filter = (market_key or "").strip().lower() or None
    team_filter = (team or "").strip().upper() or None
    markets: Sequence[str] = (mk_filter,) if mk_filter else NBA_PROP_MARKETS
    if mk_filter and mk_filter not in NBA_PROP_MARKETS:
        # Missing Odds key (e.g. pr/ra) → missing, do not guess.
        return {
            "present": True,
            "props_version": PROPS_VERSION,
            "count": 0,
            "lines": [],
            "play_n": 0,
            "lean_n": 0,
            "message": f"missing_odds_key:{mk_filter}",
            "odds_missing_vectors": list(ODDS_MISSING_VECTORS),
        }

    market_map = market_by_player or {}
    rows: List[Dict[str, Any]] = []
    suppressed_play = 0

    players: Iterable[Dict[str, Any]] = (pack.get("players") or {}).values()
    ordered = sorted(
        players,
        key=lambda r: (-float(r.get("MIN") or 0), -float(r.get("PTS") or 0), str(r.get("player_name") or "")),
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
            raw_line = mkt.get("line")
            try:
                line_f = float(raw_line) if raw_line is not None else None
            except (TypeError, ValueError):
                line_f = None
            over_price = mkt.get("over_price")
            under_price = mkt.get("under_price")
            try:
                over_i = int(over_price) if over_price is not None else None
                under_i = int(under_price) if under_price is not None else None
            except (TypeError, ValueError):
                over_i = under_i = None
            book_count = int(mkt.get("book_count") or (1 if line_f is not None else 0))

            edge = evaluate_dark_prop(
                market_key=mk,
                model_mean=mean,
                model_std=std,
                line=line_f,
                minutes=mins,
                over_price=over_i,
                under_price=under_i,
                best_trusted=best_trusted,
                book_count=book_count,
                preseason=preseason,
            )
            if edge.get("would_clear_play"):
                suppressed_play += 1

            ch5_sigma = (player.get("sigma") or {}).get(MARKET_TO_VECTOR[mk])
            tag = "PASS"
            # Hard ban: never emit PLAY/LEAN strings on a prop row.
            assert tag not in {"PLAY", "LEAN"}
            rows.append(
                {
                    "model_version": PROPS_VERSION,
                    "player_id": pid,
                    "player_name": pname,
                    "team": tk,
                    "market_key": mk,
                    "line": edge.get("best"),  # cleared when untrusted
                    "best": edge.get("best"),
                    "model_mean": edge.get("model_mean"),
                    "model_std": edge.get("model_std"),
                    "edge": edge.get("edge"),
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
                        "edge": edge.get("edge"),
                        "minutes": mins,
                        "projection_source": "player_projection_ch5",
                        "ch5_sigma": ch5_sigma,
                        "policy_version": POLICY_VERSION,
                        "dark_only": True,
                        "would_clear_play": edge.get("would_clear_play"),
                        "best_trusted": edge.get("best_trusted"),
                        "trust_reason": edge.get("trust_reason"),
                    },
                    "stake_eligible": False,
                    "tag": "PASS",
                    "tag_side": None,
                }
            )

    def _sort_key(r: Dict[str, Any]) -> Tuple[int, float, float]:
        best = r.get("best")
        mean = float(r.get("model_mean") or 0)
        if best is None:
            return (1, 0.0, -float((r.get("diagnostics") or {}).get("minutes") or 0))
        return (0, -abs(mean - float(best)), -float((r.get("diagnostics") or {}).get("minutes") or 0))

    rows.sort(key=_sort_key)
    rows = rows[: max(1, int(limit))]

    play_n = sum(1 for r in rows if str(r.get("tag") or "").upper() == "PLAY")
    lean_n = sum(1 for r in rows if str(r.get("tag") or "").upper() == "LEAN")
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
        "odds_backed_markets": list(ODDS_BACKED_MARKETS),
        "odds_missing_vectors": list(ODDS_MISSING_VECTORS),
        "count": len(rows),
        "lines": rows,
        "play_n": play_n,
        "lean_n": lean_n,
        "suppressed_play_candidates": suppressed_play,
        "does_not": [
            "PLAY / LEAN tags (dark)",
            "stake-eligible props",
            "second scorer / stub rates as SoT",
            "fake Odds keys (PR/RA)",
            "fantasy board",
            "walking means to the book",
            "CFB/NFL",
            "Ch1/Ch2/Ch5 rematerialize",
            "Ch3/Ch4 retune",
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
        "odds_missing_vectors": list(ODDS_MISSING_VECTORS),
        "reads": "PlayerProjection (Ch5)",
        "edge": "PlayerProjection[market] - trusted_Best",
        "does_not": [
            "emit PLAY or LEAN",
            "rescore player means",
            "guess missing Odds keys",
            "fantasy",
            "CFB/NFL",
        ],
    }
