"""NBA Chapter 4 — team KEI emitter (sides/totals only).

KEI_spread_home = f(rebased_net_home − rebased_net_away + situation_Δ)
KEI_total       = f(ppg_home + ppg_away)  # situation already inside implied_ppg
WP              = erf mapper on KEI_spread

--kei-only: reads Ch2 rebased + Ch3 apply-on-read. Does not rematerialize packs.
Does not walk KEI to the book. Props stay dark.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.services.nba_season_engine import priors as P
from src.services.nba_season_engine.roster_minutes import get_rebased_team
from src.services.nba_season_engine.situation import (
    apply_situation_team_line,
    get_team_game_flags,
    load_schedule_pack,
)

DATA_DIR = Path(__file__).resolve().parent / "data"
KEI_PACK_PATH = DATA_DIR / "nba_kei_lines_ch4.json"

KEI_VERSION = "nba-kei-v0.1-ch4"
# Versioned NBA margin σ for WP (points). Not CFB 15.2.
NBA_MARGIN_SD = 12.0

PLAY_EDGE_PTS = 4.0
LEAN_EDGE_PTS = 2.5


def _wp_from_spread(spread_home: float, margin_sd: float = NBA_MARGIN_SD) -> float:
    sd = max(float(margin_sd or NBA_MARGIN_SD), 6.0)
    z = (-float(spread_home)) / sd
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
    """Build one game KEI from Ch2 nets + Ch3 situation (apply-on-read)."""
    h = str(home).upper()
    a = str(away).upper()
    home_line = apply_situation_team_line(h, game_id, flags=flags_home)
    away_line = apply_situation_team_line(a, game_id, flags=flags_away)
    home_base = get_rebased_team(h) or {}
    away_base = get_rebased_team(a) or {}

    net_h = float(home_line.get("net_rating") or home_base.get("net_rating") or 0.0)
    net_a = float(away_line.get("net_rating") or away_base.get("net_rating") or 0.0)
    delta_h = float(home_line.get("delta_pts") or 0.0)
    delta_a = float(away_line.get("delta_pts") or 0.0)
    situation_delta = delta_h - delta_a
    pace_h = float(home_line.get("pace") or home_base.get("pace") or 100.0)
    pace_a = float(away_line.get("pace") or away_base.get("pace") or 100.0)
    pace = 0.5 * (pace_h + pace_a)

    # f(net_h − net_a + situation_Δ): net→points via pace/100; situation already points.
    net_diff = net_h - net_a
    margin_home = (net_diff * (pace / 100.0)) + situation_delta
    kei_spread_home = -margin_home

    ppg_h = float(home_line.get("implied_ppg") or home_base.get("implied_ppg") or 0.0)
    ppg_a = float(away_line.get("implied_ppg") or away_base.get("implied_ppg") or 0.0)
    kei_total = ppg_h + ppg_a

    wp = _wp_from_spread(kei_spread_home)

    return {
        "game_id": game_id,
        "home": h,
        "away": a,
        "home_team": home_base.get("team_name") or h,
        "away_team": away_base.get("team_name") or a,
        "kei_spread_home": _round(kei_spread_home, 2),
        "kei_total": _round(kei_total, 2),
        "kei_home_win_prob": _round(wp, 4),
        "model_spread_home": _round(kei_spread_home, 2),
        "model_total": _round(kei_total, 2),
        "inputs": {
            "rebased_net_home": _round(net_h, 4),
            "rebased_net_away": _round(net_a, 4),
            "net_diff": _round(net_diff, 4),
            "situation_delta": _round(situation_delta, 4),
            "situation_delta_home": _round(delta_h, 4),
            "situation_delta_away": _round(delta_a, 4),
            "pace": _round(pace, 4),
            "ppg_home": _round(ppg_h, 4),
            "ppg_away": _round(ppg_a, 4),
            "ortg_home": _round(float(home_line.get("ortg") or 0.0), 4),
            "drtg_home": _round(float(home_line.get("drtg") or 0.0), 4),
            "ortg_away": _round(float(away_line.get("ortg") or 0.0), 4),
            "drtg_away": _round(float(away_line.get("drtg") or 0.0), 4),
        },
        "thresholds": {"lean": LEAN_EDGE_PTS, "play": PLAY_EDGE_PTS},
        "kei_version": KEI_VERSION,
        "engine_version": P.ENGINE_VERSION,
    }


def emit_kei_for_schedule(*, limit: Optional[int] = None) -> Dict[str, Any]:
    """--kei-only emitter over the Ch3 schedule pack. No Ch1/Ch2/Ch5 rewrite."""
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
        row["arena"] = g.get("arena")
        lines.append(row)
    return {
        "engine_version": P.ENGINE_VERSION,
        "kei_version": KEI_VERSION,
        "as_of": "2026-09-01",
        "chapter": 4,
        "mode": "kei_only",
        "TEAM_CARRY_SHRINK_unchanged": P.TEAM_CARRY_SHRINK,
        "SITUATION_TEAM_PTS_CAP_unchanged": P.SITUATION_TEAM_PTS_CAP,
        "NBA_MARGIN_SD": NBA_MARGIN_SD,
        "PLAY_EDGE_PTS": PLAY_EDGE_PTS,
        "LEAN_EDGE_PTS": LEAN_EDGE_PTS,
        "formula": {
            "spread": "kei_spread_home = -((net_h - net_a) * pace/100 + (sit_h - sit_a))",
            "total": "kei_total = ppg_h' + ppg_a'  (Ch3 implied_ppg)",
            "wp": "Φ(-spread / NBA_MARGIN_SD)",
        },
        "does_not": [
            "rematerialize Ch1/Ch2/Ch5 packs",
            "retune Ch3 coeffs",
            "new shrink / grid / player means",
            "props / Ch6",
            "fantasy",
            "team if",
            "walk KEI to the book",
            "futures",
            "CFB/NFL",
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
            # inclusive window by ISO date string compare (YYYY-MM-DD)
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
        "module": "src.services.nba_season_engine.nba_kei",
        "kei_version": KEI_VERSION,
        "engine_version": P.ENGINE_VERSION,
        "PLAY_EDGE_PTS": PLAY_EDGE_PTS,
        "LEAN_EDGE_PTS": LEAN_EDGE_PTS,
        "NBA_MARGIN_SD": NBA_MARGIN_SD,
        "path": str(KEI_PACK_PATH),
        "game_count": pack.get("game_count"),
        "does_not": pack.get("does_not"),
    }
