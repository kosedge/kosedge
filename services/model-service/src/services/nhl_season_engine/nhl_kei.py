"""NHL Chapter 4 — team KEI emitter (puck / total / WP).

KEI_puck_home = −(rebased_net_h − rebased_net_a + situation_Δ)
KEI_total     = gf_h' + gf_a'   # situation already inside gf_pg'
WP            = Φ(−puck / NHL_MARGIN_SD)

--kei-only: reads Ch1 prior + Ch3 apply-on-read. Does not rematerialize packs.
Does not walk KEI to the book. Props stay dark. Starter-unknown goalie rows stay —.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.services.nhl_season_engine import priors as P
from src.services.nhl_season_engine.situation import (
    apply_situation_team_line,
    get_team_game_flags,
    load_schedule_pack,
)
from src.services.nhl_season_engine.team_prior import get_team_prior

DATA_DIR = Path(__file__).resolve().parent / "data"
KEI_PACK_PATH = DATA_DIR / "nhl_kei_lines_ch4.json"

KEI_VERSION = "nhl-kei-v0.1-ch4"
# Goal-margin σ for WP (goals). Not NBA 12 / WNBA 11 / CFB 15.2.
NHL_MARGIN_SD = 1.85

PLAY_EDGE_PTS = 4.0
LEAN_EDGE_PTS = 2.5


def _wp_from_puck(puck_home: float, margin_sd: float = NHL_MARGIN_SD) -> float:
    sd = max(float(margin_sd or NHL_MARGIN_SD), 1.0)
    z = (-float(puck_home)) / sd
    return max(0.02, min(0.98, 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))))


def _round(v: Optional[float], nd: int = 2) -> Optional[float]:
    if v is None or not math.isfinite(float(v)):
        return None
    return round(float(v), nd)


def tag_from_edge(
    abs_edge: Optional[float],
    *,
    best_trusted: bool,
    preseason: bool = False,
) -> str:
    """Tag = KEI vs trusted Best only. PASS if Best missing/untrusted/preseason."""
    if preseason or not best_trusted or abs_edge is None:
        return "PASS"
    e = abs(float(abs_edge))
    if e >= PLAY_EDGE_PTS:
        return "PLAY"
    if e >= LEAN_EDGE_PTS:
        return "LEAN"
    return "PASS"


def compute_game_kei(
    home: str,
    away: str,
    game_id: str,
    *,
    flags_home: Optional[Dict[str, Any]] = None,
    flags_away: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build one game KEI from Ch1 nets + Ch3 situation (apply-on-read)."""
    h = str(home).upper()
    a = str(away).upper()
    home_line = apply_situation_team_line(h, game_id, flags=flags_home)
    away_line = apply_situation_team_line(a, game_id, flags=flags_away)
    home_base = get_team_prior(h) or {}
    away_base = get_team_prior(a) or {}

    gp_h = float(home_base.get("gp") or 82) or 82.0
    gp_a = float(away_base.get("gp") or 82) or 82.0
    net_h = (float(home_base.get("gf") or 0) - float(home_base.get("ga") or 0)) / gp_h
    net_a = (float(away_base.get("gf") or 0) - float(away_base.get("ga") or 0)) / gp_a

    delta_h = float(home_line.get("delta_goals") or 0.0)
    delta_a = float(away_line.get("delta_goals") or 0.0)
    situation_delta = delta_h - delta_a
    situation_total_delta = delta_h + delta_a

    # f(rebased_home − rebased_away + situation_Δ) → home-signed puck (neg = home fav).
    net_diff = net_h - net_a
    margin_home = net_diff + situation_delta
    kei_puck_home = -margin_home

    gf_h = float(home_line.get("gf_pg") or (float(home_base.get("gf") or 0) / gp_h))
    gf_a = float(away_line.get("gf_pg") or (float(away_base.get("gf") or 0) / gp_a))
    # f(gf_home + gf_away + situation_total_Δ) — gf_pg' already includes each side's Δ.
    kei_total = gf_h + gf_a

    wp = _wp_from_puck(kei_puck_home)

    return {
        "game_id": game_id,
        "home": h,
        "away": a,
        "home_team": home_base.get("team_name") or h,
        "away_team": away_base.get("team_name") or a,
        "kei_spread_home": _round(kei_puck_home, 2),
        "kei_puck_home": _round(kei_puck_home, 2),
        "kei_total": _round(kei_total, 2),
        "kei_home_win_prob": _round(wp, 4),
        "model_spread_home": _round(kei_puck_home, 2),
        "model_total": _round(kei_total, 2),
        "inputs": {
            "rebased_net_home": _round(net_h, 4),
            "rebased_net_away": _round(net_a, 4),
            "net_diff": _round(net_diff, 4),
            "situation_delta": _round(situation_delta, 4),
            "situation_delta_home": _round(delta_h, 4),
            "situation_delta_away": _round(delta_a, 4),
            "situation_total_delta": _round(situation_total_delta, 4),
            "gf_pg_home": _round(gf_h, 4),
            "gf_pg_away": _round(gf_a, 4),
            "ga_pg_home": _round(float(home_line.get("ga_pg") or 0.0), 4),
            "ga_pg_away": _round(float(away_line.get("ga_pg") or 0.0), 4),
        },
        "thresholds": {"lean": LEAN_EDGE_PTS, "play": PLAY_EDGE_PTS},
        "kei_version": KEI_VERSION,
        "engine_version": P.ENGINE_VERSION,
    }


def emit_kei_for_schedule(*, limit: Optional[int] = None) -> Dict[str, Any]:
    """--kei-only emitter over the Ch3 schedule pack. No Ch1/Ch2/Ch3/Ch5 rewrite."""
    sched = load_schedule_pack()
    games = list(sched.get("games") or [])
    if limit is not None:
        games = games[: int(limit)]
    lines: List[Dict[str, Any]] = []
    for g in games:
        gid = str(g["game_id"])
        home = str(g["home"]).upper()
        away = str(g["away"]).upper()
        fh = get_team_game_flags(home, gid)
        fa = get_team_game_flags(away, gid)
        row = compute_game_kei(home, away, gid, flags_home=fh, flags_away=fa)
        row["date"] = g.get("date")
        row["venue"] = g.get("venue")
        row["start_time_utc"] = g.get("start_time_utc")
        lines.append(row)
    return {
        "engine_version": P.ENGINE_VERSION,
        "kei_version": KEI_VERSION,
        "as_of": "2026-09-02",
        "chapter": 4,
        "mode": "kei_only",
        "NHL_TEAM_CARRY_SHRINK_unchanged": P.NHL_TEAM_CARRY_SHRINK,
        "NHL_SITUATION_GOAL_CAP_unchanged": P.NHL_SITUATION_GOAL_CAP,
        "situation_coeffs_frozen": {
            "home": 0.10,
            "b2b": -0.15,
            "travel": -0.08,
            "altitude": 0.12,
        },
        "NHL_MARGIN_SD": NHL_MARGIN_SD,
        "PLAY_EDGE_PTS": PLAY_EDGE_PTS,
        "LEAN_EDGE_PTS": LEAN_EDGE_PTS,
        "ODDS_SPORT_KEY": P.ODDS_SPORT_KEY,
        "formula": {
            "puck": "kei_puck_home = -((net_h - net_a) + (sit_h - sit_a))",
            "total": "kei_total = gf_h' + gf_a'  (Ch3 gf_pg')",
            "wp": "Φ(-puck / NHL_MARGIN_SD)",
        },
        "does_not": [
            "rematerialize Ch1/Ch2/Ch5 packs",
            "retune Ch3 coeffs",
            "new shrink / TOI / player means",
            "props / Ch6",
            "team if",
            "walk KEI to the book",
            "NBA/WNBA/CFB/NFL",
            "starter PLAY on unknown goalie",
        ],
        "game_count": len(lines),
        "games": lines,
    }


def load_kei_pack(force: bool = False) -> Dict[str, Any]:
    if not force and hasattr(load_kei_pack, "_cache") and load_kei_pack._cache:  # type: ignore[attr-defined]
        return load_kei_pack._cache  # type: ignore[attr-defined]
    if not KEI_PACK_PATH.is_file():
        out = {"present": False, "games": []}
        load_kei_pack._cache = out  # type: ignore[attr-defined]
        return out
    raw = json.loads(KEI_PACK_PATH.read_text(encoding="utf-8"))
    raw["present"] = True
    load_kei_pack._cache = raw  # type: ignore[attr-defined]
    return raw


def clear_kei_cache() -> None:
    if hasattr(load_kei_pack, "_cache"):
        load_kei_pack._cache = None  # type: ignore[attr-defined]


def kei_lines_for_dates(
    *,
    game_date: Optional[str] = None,
    days_ahead: int = 0,
    limit: int = 80,
) -> List[Dict[str, Any]]:
    pack = load_kei_pack()
    games = list(pack.get("games") or [])
    if game_date:
        if days_ahead <= 0:
            games = [g for g in games if g.get("date") == game_date]
        else:
            from datetime import date, timedelta

            start = date.fromisoformat(game_date)
            end = start + timedelta(days=int(days_ahead))
            games = [
                g
                for g in games
                if g.get("date")
                and start <= date.fromisoformat(str(g["date"])) <= end
            ]
    return games[: int(limit)]


def documentation() -> Dict[str, Any]:
    pack = load_kei_pack()
    return {
        "module": "src.services.nhl_season_engine.nhl_kei",
        "kei_version": KEI_VERSION,
        "engine_version": P.ENGINE_VERSION,
        "NHL_MARGIN_SD": NHL_MARGIN_SD,
        "PLAY_EDGE_PTS": PLAY_EDGE_PTS,
        "LEAN_EDGE_PTS": LEAN_EDGE_PTS,
        "NHL_TEAM_CARRY_SHRINK_unchanged": P.NHL_TEAM_CARRY_SHRINK,
        "NHL_SITUATION_GOAL_CAP_unchanged": P.NHL_SITUATION_GOAL_CAP,
        "game_count": pack.get("game_count"),
        "path": str(KEI_PACK_PATH),
        "does_not": pack.get("does_not"),
    }
