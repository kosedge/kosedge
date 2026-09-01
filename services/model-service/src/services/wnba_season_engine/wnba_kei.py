"""WNBA Chapter 4 — team KEI emitter (sides/totals only).

KEI_spread_home = f(rebased_net_home − rebased_net_away + situation_Δ)
KEI_total       = f(ppg_home + ppg_away + situation_total_Δ)
WP              = erf mapper on KEI_spread

--kei-only: reads Ch2 rebased + Ch3 apply-on-read. Does not rematerialize packs.
Does not walk KEI to the book. Props stay dark. Does not blend Aug-1 leftovers.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.services.wnba_season_engine import priors as P
from src.services.wnba_season_engine.roster_minutes import get_rebased_team
from src.services.wnba_season_engine.situation import (
    apply_situation_team_line,
    get_team_game_flags,
    load_schedule_pack,
)

DATA_DIR = Path(__file__).resolve().parent / "data"
KEI_PACK_PATH = DATA_DIR / "wnba_kei_lines_ch4.json"

KEI_VERSION = "wnba-kei-v0.1-ch4"
# WNBA margin σ for WP (points). WNBA-point — not a copy of NBA 12.0.
WNBA_MARGIN_SD = 11.0

PLAY_EDGE_PTS = 4.0
LEAN_EDGE_PTS = 2.5

FORBIDDEN_LEFTOVER_FAIR_LINE_GAME_IDS = ("401857105", "401857106")

# Live 2026 remainder seed (CDN blocked in build env). CON@ATL resumes Sep 17.
LIVE_REMAINDER_GAMES: List[Dict[str, Any]] = [
    {
        "game_id": "401857190",
        "date": "2026-09-17",
        "home": "ATL",
        "away": "CON",
        "arena": "Gateway Center Arena @ College Park",
        "status": "Scheduled",
        "flags_home": {
            "home": True,
            "b2b": False,
            "travel": False,
            "altitude": False,
            "three_in_four": False,
        },
        "flags_away": {
            "home": False,
            "b2b": False,
            "travel": True,
            "altitude": False,
            "three_in_four": False,
        },
    },
]


def _wp_from_spread(spread_home: float, margin_sd: float = WNBA_MARGIN_SD) -> float:
    sd = max(float(margin_sd or WNBA_MARGIN_SD), 5.0)
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
    already_final: bool = False,
) -> str:
    """Tag = KEI vs trusted Best only. PASS if Best missing/untrusted/final."""
    if already_final or not best_trusted or abs_edge is None:
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
    pace_h = float(home_line.get("pace") or home_base.get("pace") or 80.0)
    pace_a = float(away_line.get("pace") or away_base.get("pace") or 80.0)
    pace = 0.5 * (pace_h + pace_a)

    # f(net_h − net_a + situation_Δ): net→points via pace/100; situation already points.
    net_diff = net_h - net_a
    margin_home = (net_diff * (pace / 100.0)) + situation_delta
    kei_spread_home = -margin_home

    # Totals: ppg already includes each side's situation Δ when flags applied.
    ppg_h = float(home_line.get("implied_ppg") or home_base.get("implied_ppg") or 0.0)
    ppg_a = float(away_line.get("implied_ppg") or away_base.get("implied_ppg") or 0.0)
    kei_total = ppg_h + ppg_a
    situation_total_delta = delta_h + delta_a

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
            "situation_total_delta": _round(situation_total_delta, 4),
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


def _emit_one(
    home: str,
    away: str,
    game_id: str,
    *,
    date: Optional[str] = None,
    arena: Optional[str] = None,
    status: Optional[str] = None,
    flags_home: Optional[Dict[str, Any]] = None,
    flags_away: Optional[Dict[str, Any]] = None,
    slate: str = "schedule",
) -> Dict[str, Any]:
    row = compute_game_kei(
        home, away, game_id, flags_home=flags_home, flags_away=flags_away
    )
    row["date"] = date
    row["arena"] = arena
    row["status"] = status
    row["slate"] = slate
    return row


def emit_kei_for_schedule(*, limit: Optional[int] = None) -> Dict[str, Any]:
    """--kei-only emitter over Ch3 schedule + live remainder. No Ch1/Ch2/Ch5 rewrite."""
    sched = load_schedule_pack()
    games = list(sched.get("games") or [])
    if limit is not None:
        games = games[: int(limit)]
    lines: List[Dict[str, Any]] = []
    seen: set[str] = set()

    for g in games:
        gid = str(g["game_id"])
        if gid in FORBIDDEN_LEFTOVER_FAIR_LINE_GAME_IDS:
            continue
        home = str(g["home"]).upper()
        away = str(g["away"]).upper()
        fh = get_team_game_flags(home, gid)
        fa = get_team_game_flags(away, gid)
        row = _emit_one(
            home,
            away,
            gid,
            date=g.get("date"),
            arena=g.get("arena"),
            status=g.get("status"),
            flags_home=fh,
            flags_away=fa,
            slate="schedule_2025_paper",
        )
        lines.append(row)
        seen.add(gid)

    live_rows: List[Dict[str, Any]] = []
    for g in LIVE_REMAINDER_GAMES:
        gid = str(g["game_id"])
        if gid in FORBIDDEN_LEFTOVER_FAIR_LINE_GAME_IDS or gid in seen:
            continue
        row = _emit_one(
            str(g["home"]),
            str(g["away"]),
            gid,
            date=g.get("date"),
            arena=g.get("arena"),
            status=g.get("status"),
            flags_home=g.get("flags_home"),
            flags_away=g.get("flags_away"),
            slate="live_remainder_2026",
        )
        lines.append(row)
        live_rows.append(row)
        seen.add(gid)

    return {
        "engine_version": P.ENGINE_VERSION,
        "kei_version": KEI_VERSION,
        "as_of": "2026-09-01",
        "chapter": 4,
        "mode": "kei_only",
        "WNBA_TEAM_CARRY_SHRINK_unchanged": P.WNBA_TEAM_CARRY_SHRINK,
        "SITUATION_TEAM_PTS_CAP_unchanged": P.SITUATION_TEAM_PTS_CAP,
        "MINUTE_GRID_SUM_unchanged": P.MINUTE_GRID_SUM,
        "situation_coeffs_frozen": {
            "home": 1.5,
            "b2b": -1.5,
            "travel": -0.5,
            "altitude": 0.5,
        },
        "WNBA_MARGIN_SD": WNBA_MARGIN_SD,
        "PLAY_EDGE_PTS": PLAY_EDGE_PTS,
        "LEAN_EDGE_PTS": LEAN_EDGE_PTS,
        "formula": {
            "spread": "kei_spread_home = -((net_h - net_a) * pace/100 + (sit_h - sit_a))",
            "total": "kei_total = ppg_h' + ppg_a'  (Ch3 implied_ppg; situation_total_Δ inside)",
            "wp": "Φ(-spread / WNBA_MARGIN_SD)",
        },
        "forbidden_leftover_fair_line_game_ids": list(
            FORBIDDEN_LEFTOVER_FAIR_LINE_GAME_IDS
        ),
        "does_not": [
            "rematerialize Ch1/Ch2/Ch5 packs",
            "retune Ch3 coeffs",
            "new shrink / grid / player means",
            "props / Ch6",
            "team if",
            "walk KEI to the book",
            "blend Aug-1 leftover fair-lines 401857105/401857106",
            "NBA/CFB/NFL packs",
        ],
        "game_count": len(lines),
        "live_remainder_count": len(live_rows),
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
    include_live_remainder: bool = True,
) -> List[Dict[str, Any]]:
    pack = load_kei_pack()
    games = [
        g
        for g in (pack.get("games") or [])
        if str(g.get("game_id")) not in FORBIDDEN_LEFTOVER_FAIR_LINE_GAME_IDS
    ]
    if game_date:
        from datetime import date, timedelta

        start = date.fromisoformat(game_date)
        end = start + timedelta(days=int(days_ahead))
        windowed = [
            g
            for g in games
            if g.get("date")
            and start <= date.fromisoformat(str(g["date"])) <= end
        ]
        if windowed:
            games = windowed
        elif include_live_remainder:
            # Midseason: CDN schedule missing — serve live remainder + any
            # upcoming-dated rows rather than Aug-1 leftovers.
            live = [g for g in games if g.get("slate") == "live_remainder_2026"]
            upcoming = [
                g
                for g in games
                if g.get("date")
                and date.fromisoformat(str(g["date"])) >= start
                and str(g.get("status") or "").lower() != "final"
            ]
            games = live or upcoming or games[:limit]
        else:
            games = windowed
    return games[: int(limit)]


def documentation() -> Dict[str, Any]:
    pack = load_kei_pack()
    return {
        "module": "src.services.wnba_season_engine.wnba_kei",
        "kei_version": KEI_VERSION,
        "engine_version": P.ENGINE_VERSION,
        "PLAY_EDGE_PTS": PLAY_EDGE_PTS,
        "LEAN_EDGE_PTS": LEAN_EDGE_PTS,
        "WNBA_MARGIN_SD": WNBA_MARGIN_SD,
        "path": str(KEI_PACK_PATH),
        "game_count": pack.get("game_count"),
        "forbidden_leftover_fair_line_game_ids": list(
            FORBIDDEN_LEFTOVER_FAIR_LINE_GAME_IDS
        ),
        "does_not": pack.get("does_not"),
    }
