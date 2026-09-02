"""NHL Chapter 6 — props desk (dark only).

Phase: proj vs trusted Best. Zero PLAY. Zero LEAN.
Reads Ch5 PlayerProjection only — does not re-score.

edge = PlayerProjection[market] − trusted_Best

Odds-backed skater markets only (icehockey_nhl): goals assists pts sog.
SAVES exists on Ch5 but Odds has no coded key → goalie rows stay — when
STARTER_GATE is unknown (no goalie PLAY ever in dark).
"""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from src.services.nhl_season_engine import priors as P
from src.services.nhl_season_engine.player_projection import (
    load_player_projection_pack,
)

PROPS_VERSION = "nhl-props-ch6-dark-v1"
POLICY_VERSION = "nhl_props_ch6_dark_v1"

# Register (Ch0) — coded for gates/docs; dark mode never emits PLAY/LEAN.
PROP_PLAY_ABS = 4.0
PROP_PLAY_SIGMA = 0.6
PROP_PLAY_CAP_PER_SLATE = int(P.PROP_PLAY_CAP_PER_SLATE)  # 6
PROP_TOI_GATE = 8.0  # EV+PP minutes; analog to basketball minutes gate
STARTER_GATE = P.STARTER_GATE  # "unknown" → goalie Best stays —

# Odds client maps these for icehockey_nhl (enterprise_training_pull).
ODDS_BACKED_MARKETS = ("goals", "assists", "pts", "sog")
# Ch5 goalie vector present; Odds has no player_saves key → not Odds-joined.
ODDS_MISSING_VECTORS = ("SAVES",)

NHL_PROP_MARKETS = ODDS_BACKED_MARKETS

MARKET_TO_VECTOR = {
    "goals": "G",
    "assists": "A",
    "pts": "P",
    "sog": "SOG",
    "saves": "SAVES",
}

DARK_ONLY = True
ABSURD_VS_PROJ = 8.0  # goal units (not basketball 40)


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def game_level_std(market_key: str, mean: float) -> float:
    """Game-grain σ for desk math. Ch5 pack σ is season-rate — too tight for O/U."""
    m = max(float(mean), 0.05)
    mk = str(market_key).lower()
    if mk == "goals":
        return _clamp(0.55 * math.sqrt(m) + 0.35, 0.35, 2.5)
    if mk == "assists":
        return _clamp(0.50 * math.sqrt(m) + 0.40, 0.40, 2.8)
    if mk == "sog":
        return _clamp(0.45 * math.sqrt(m) + 0.70, 0.80, 4.0)
    if mk == "saves":
        return _clamp(0.35 * math.sqrt(m) + 1.2, 1.5, 12.0)
    # pts
    return _clamp(0.50 * math.sqrt(m) + 0.45, 0.45, 3.0)


def would_clear_prop_play(*, abs_edge: float, z: float) -> bool:
    """Register check only — dark desk never uses this to tag."""
    return abs(float(abs_edge)) >= PROP_PLAY_ABS and abs(float(z)) >= PROP_PLAY_SIGMA


def trust_prop_best(
    *,
    best: Optional[float],
    model_mean: Optional[float] = None,
    book_count: int = 1,
    preseason: bool = False,
    starter_unknown: bool = False,
) -> Dict[str, Any]:
    """Trusted Best gate. Untrusted / starter-unknown → Best cleared (UI —)."""
    if starter_unknown:
        return {"trusted": False, "best": None, "reason": "starter_gate_unknown"}
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
    if model_mean is not None:
        try:
            gap = abs(float(model_mean) - best_f)
            if gap > ABSURD_VS_PROJ:
                return {"trusted": False, "best": None, "reason": "absurd_vs_proj"}
        except (TypeError, ValueError):
            pass
    return {"trusted": True, "best": best_f, "reason": "best"}


def projection_mean_std(
    player: Dict[str, Any], market_key: str
) -> Optional[Tuple[float, float]]:
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
    toi: float,
    over_price: Optional[int] = None,
    under_price: Optional[int] = None,
    best_trusted: bool = False,
    book_count: int = 1,
    preseason: bool = False,
    starter_unknown: bool = False,
) -> Dict[str, Any]:
    """Proj vs trusted Best. edge = mean − Best. Tag always PASS (dark)."""
    mk = str(market_key).lower()
    mean = float(model_mean)
    std = max(0.25, float(model_std))
    minutes = float(toi)

    if mk != "saves" and minutes < PROP_TOI_GATE:
        return {
            "tag": "PASS",
            "tag_side": None,
            "reason": "toi_gate",
            "stake_eligible": False,
            "policy_version": POLICY_VERSION,
            "dark_only": True,
            "market_joined": False,
            "model_mean": round(mean, 3),
            "model_std": round(std, 3),
            "best": None,
            "edge": None,
            "toi": round(minutes, 2),
        }

    trust = trust_prop_best(
        best=line,
        model_mean=mean,
        book_count=book_count,
        preseason=preseason,
        starter_unknown=starter_unknown or (mk == "saves" and STARTER_GATE == "unknown"),
    )
    best_f = trust["best"] if trust["trusted"] else None

    if best_f is None:
        return {
            "tag": "PASS",
            "tag_side": None,
            "reason": trust["reason"]
            if line is None or starter_unknown
            else f"untrusted_{trust['reason']}",
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
            "toi": round(minutes, 2),
            "best_trusted": False,
            "trust_reason": trust["reason"],
            "starter_gate": STARTER_GATE,
        }

    edge = mean - best_f
    z = edge / std
    over_prob = _clamp(1.0 - _normal_cdf((best_f - mean) / std), 0.02, 0.98)
    under_prob = 1.0 - over_prob
    edge_over = over_prob - 0.5
    edge_under = under_prob - 0.5
    if over_price is not None and under_price is not None:
        # Optional juice — never required for dark board.
        try:
            # Keep simple; no NBA prop_edge_policy dependency.
            pass
        except Exception:
            pass

    abs_edge = abs(edge)
    clears = would_clear_prop_play(abs_edge=abs_edge, z=z)
    reason = "dark_proj_vs_best"
    if clears:
        reason = "dark_would_clear_play_suppressed"

    return {
        "tag": "PASS",
        "tag_side": None,
        "reason": reason,
        "stake_eligible": False,
        "policy_version": POLICY_VERSION,
        "dark_only": True,
        "market_joined": True,
        "model_mean": round(mean, 3),
        "model_std": round(std, 3),
        "best": round(best_f, 3),
        "line": round(best_f, 3),
        "edge": round(edge, 3),
        "z": round(z, 3),
        "abs_edge": round(abs_edge, 3),
        "over_prob": round(over_prob, 4),
        "under_prob": round(under_prob, 4),
        "edge_over": round(edge_over, 4),
        "edge_under": round(edge_under, 4),
        "toi": round(minutes, 2),
        "would_clear_play": clears,
        "prop_play_abs": PROP_PLAY_ABS,
        "prop_play_sigma": PROP_PLAY_SIGMA,
        "market_over_price": over_price,
        "market_under_price": under_price,
        "best_trusted": True,
        "trust_reason": trust["reason"],
        "starter_gate": STARTER_GATE,
    }


def _row_from_edge(
    *,
    player: Dict[str, Any],
    mk: str,
    edge: Dict[str, Any],
    toi: float,
    player_type: str,
) -> Dict[str, Any]:
    vec = MARKET_TO_VECTOR[mk]
    ch5_sigma = (player.get("sigma") or {}).get(vec)
    tag = "PASS"
    assert tag not in {"PLAY", "LEAN"}
    return {
        "model_version": PROPS_VERSION,
        "player_id": str(player.get("player_id") or ""),
        "player_name": str(player.get("player_name") or ""),
        "team": str(player.get("team") or "").upper(),
        "player_type": player_type,
        "market_key": mk,
        "line": edge.get("best"),
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
            "toi": toi,
            "projection_source": "player_projection_ch5",
            "ch5_sigma": ch5_sigma,
            "policy_version": POLICY_VERSION,
            "dark_only": True,
            "would_clear_play": edge.get("would_clear_play"),
            "best_trusted": edge.get("best_trusted"),
            "trust_reason": edge.get("trust_reason"),
            "starter_gate": STARTER_GATE,
        },
        "stake_eligible": False,
        "tag": "PASS",
        "tag_side": None,
    }


def build_dark_props_board(
    *,
    market_key: Optional[str] = None,
    team: Optional[str] = None,
    limit: int = 250,
    market_by_player: Optional[Dict[Tuple[str, str], Dict[str, Any]]] = None,
    best_trusted: bool = True,
    preseason: bool = False,
    include_goalie_dash_rows: bool = True,
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
    markets: Sequence[str] = (mk_filter,) if mk_filter else NHL_PROP_MARKETS

    if mk_filter and mk_filter == "saves":
        # Explicit saves request: goalie dash rows only (STARTER_GATE).
        pass
    elif mk_filter and mk_filter not in NHL_PROP_MARKETS:
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

    skaters: Iterable[Dict[str, Any]] = (pack.get("skaters") or {}).values()
    ordered_sk = sorted(
        skaters,
        key=lambda r: (
            -(float(r.get("TOI_EV") or 0) + float(r.get("TOI_PP") or 0)),
            -float(r.get("P") or 0),
            str(r.get("player_name") or ""),
        ),
    )

    if mk_filter != "saves":
        for player in ordered_sk:
            toi = float(player.get("TOI_EV") or 0) + float(player.get("TOI_PP") or 0)
            if toi < PROP_TOI_GATE:
                continue
            tk = str(player.get("team") or "").upper()
            if team_filter and tk != team_filter:
                continue
            pid = str(player.get("player_id") or "")
            pname = str(player.get("player_name") or pid)
            for mk in markets:
                if mk not in NHL_PROP_MARKETS:
                    continue
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
                try:
                    over_i = (
                        int(mkt["over_price"]) if mkt.get("over_price") is not None else None
                    )
                    under_i = (
                        int(mkt["under_price"])
                        if mkt.get("under_price") is not None
                        else None
                    )
                except (TypeError, ValueError):
                    over_i = under_i = None
                book_count = int(mkt.get("book_count") or (1 if line_f is not None else 0))

                edge = evaluate_dark_prop(
                    market_key=mk,
                    model_mean=mean,
                    model_std=std,
                    line=line_f,
                    toi=toi,
                    over_price=over_i,
                    under_price=under_i,
                    best_trusted=best_trusted,
                    book_count=book_count,
                    preseason=preseason,
                    starter_unknown=False,
                )
                if edge.get("would_clear_play"):
                    suppressed_play += 1
                rows.append(
                    _row_from_edge(
                        player=player, mk=mk, edge=edge, toi=toi, player_type="skater"
                    )
                )

    # Goalie SAVES rows: always Best — while STARTER_GATE is unknown.
    if include_goalie_dash_rows and (mk_filter is None or mk_filter == "saves"):
        goalies: Iterable[Dict[str, Any]] = (pack.get("goalies") or {}).values()
        ordered_g = sorted(
            goalies,
            key=lambda r: (
                -float(r.get("start_share") or 0),
                -float(r.get("SAVES") or 0),
                str(r.get("player_name") or ""),
            ),
        )
        for player in ordered_g:
            share = float(player.get("start_share") or 0)
            if share <= 0:
                continue
            tk = str(player.get("team") or "").upper()
            if team_filter and tk != team_filter:
                continue
            ms = projection_mean_std(player, "saves")
            if ms is None:
                continue
            mean, std = ms
            edge = evaluate_dark_prop(
                market_key="saves",
                model_mean=mean,
                model_std=std,
                line=None,
                toi=0.0,
                best_trusted=False,
                book_count=0,
                preseason=preseason,
                starter_unknown=True,
            )
            rows.append(
                _row_from_edge(
                    player=player,
                    mk="saves",
                    edge=edge,
                    toi=0.0,
                    player_type="goalie",
                )
            )

    def _sort_key(r: Dict[str, Any]) -> Tuple[int, float, float]:
        best = r.get("best")
        mean = float(r.get("model_mean") or 0)
        toi = float((r.get("diagnostics") or {}).get("toi") or 0)
        if best is None:
            return (1, 0.0, -toi)
        return (0, -abs(mean - float(best)), -toi)

    skater_rows = [r for r in rows if r.get("player_type") != "goalie"]
    goalie_rows = [r for r in rows if r.get("player_type") == "goalie"]
    skater_rows.sort(key=_sort_key)
    # Keep starter-unknown goalie dash rows visible (Best stays —),
    # but never crowd out the skater desk on small limits.
    lim = max(1, int(limit))
    goalie_cap = min(16, len(goalie_rows), max(0, lim // 4))
    if lim >= 40:
        goalie_cap = min(16, len(goalie_rows), max(goalie_cap, 8))
    sk_cap = max(0, lim - goalie_cap)
    rows = skater_rows[:sk_cap] + goalie_rows[:goalie_cap]

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
        "PROP_TOI_GATE": PROP_TOI_GATE,
        "STARTER_GATE": STARTER_GATE,
        "NHL_TEAM_CARRY_SHRINK_unchanged": P.NHL_TEAM_CARRY_SHRINK,
        "odds_backed_markets": list(ODDS_BACKED_MARKETS),
        "odds_missing_vectors": list(ODDS_MISSING_VECTORS),
        "ODDS_SPORT_KEY": P.ODDS_SPORT_KEY,
        "count": len(rows),
        "lines": rows,
        "play_n": play_n,
        "lean_n": lean_n,
        "suppressed_play_candidates": suppressed_play,
        "does_not": [
            "PLAY / LEAN tags (dark)",
            "stake-eligible props",
            "goalie PLAY while STARTER_GATE unknown",
            "fake Odds keys (SAVES join)",
            "fantasy board",
            "walking means to the book",
            "NBA/WNBA/CFB/NFL",
            "Ch1/Ch2/Ch5 rematerialize",
            "Ch3/Ch4 retune",
        ],
    }


def documentation() -> Dict[str, Any]:
    return {
        "module": "src.services.nhl_season_engine.nhl_props",
        "props_version": PROPS_VERSION,
        "policy_version": POLICY_VERSION,
        "dark_only": DARK_ONLY,
        "PROP_PLAY_ABS": PROP_PLAY_ABS,
        "PROP_PLAY_SIGMA": PROP_PLAY_SIGMA,
        "PROP_PLAY_CAP_PER_SLATE": PROP_PLAY_CAP_PER_SLATE,
        "PROP_TOI_GATE": PROP_TOI_GATE,
        "STARTER_GATE": STARTER_GATE,
        "markets": list(NHL_PROP_MARKETS),
        "odds_missing_vectors": list(ODDS_MISSING_VECTORS),
        "reads": "PlayerProjection (Ch5)",
        "edge": "PlayerProjection[market] - trusted_Best",
        "does_not": [
            "emit PLAY or LEAN",
            "rescore player means",
            "guess missing Odds saves key",
            "goalie PLAY under STARTER_GATE unknown",
            "fantasy",
            "NBA/WNBA/CFB/NFL",
        ],
    }
