"""NHL Chapter 3 — situation classes (apply-on-read, goal units).

Home / Rest·B2B / travel (official schedule) / altitude venue.
One coefficient per class; clipped by NHL_SITUATION_GOAL_CAP so
situation ≠ second prior. Does not rewrite Ch1/Ch2/Ch5 packs on disk.
Does not copy NBA +2.0 or WNBA +1.5.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.services.nhl_season_engine import priors as P
from src.services.nhl_season_engine.player_projection import (
    get_team_goalies,
    get_team_skaters,
)
from src.services.nhl_season_engine.team_prior import get_team_prior

DATA_DIR = Path(__file__).resolve().parent / "data"
COEFF_PATH = DATA_DIR / "nhl_situation_coeffs_v0.json"
SCHED_PATH = DATA_DIR / "nhl_situation_schedule_2026.json"
VENUE_PATH = DATA_DIR / "nhl_venue_flags.json"
PAPER_PATH = DATA_DIR / "nhl_situation_paper_sim_ch3.json"

_CACHE: Dict[str, Any] = {}


def clear_ch3_cache() -> None:
    _CACHE.clear()


def _load(path: Path, key: str) -> Dict[str, Any]:
    if key in _CACHE:
        return _CACHE[key]
    if not path.is_file():
        _CACHE[key] = {"present": False}
        return _CACHE[key]
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["present"] = True
    _CACHE[key] = raw
    return raw


def load_situation_coeffs() -> Dict[str, Any]:
    return _load(COEFF_PATH, "coeffs")


def load_schedule_pack() -> Dict[str, Any]:
    return _load(SCHED_PATH, "sched")


def load_venue_flags() -> Dict[str, Any]:
    return _load(VENUE_PATH, "venue")


def load_paper_sim() -> Dict[str, Any]:
    return _load(PAPER_PATH, "paper")


def get_team_game_flags(team: str, game_id: str) -> Optional[Dict[str, Any]]:
    sched = load_schedule_pack()
    t = str(team).upper()
    gid = str(game_id)
    for row in sched.get("team_games") or []:
        if row.get("team") == t and str(row.get("game_id")) == gid:
            return row
    return None


def situation_delta_goals(
    flags: Dict[str, Any], coeffs: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """Compute raw + clipped team-goals Δ from class flags."""
    pack = load_situation_coeffs()
    c = dict(coeffs or (pack.get("coefficients") or {}))
    cap = float(pack.get("NHL_SITUATION_GOAL_CAP") or P.NHL_SITUATION_GOAL_CAP)
    parts = {
        "home": float(c.get("home") or 0.0) if flags.get("home") else 0.0,
        "b2b": float(c.get("b2b") or 0.0) if flags.get("b2b") else 0.0,
        "travel": float(c.get("travel") or 0.0) if flags.get("travel") else 0.0,
        "altitude": 0.0,
    }
    if flags.get("altitude"):
        alt = float(c.get("altitude") or 0.0)
        parts["altitude"] = alt if flags.get("home") else -alt
    raw = sum(parts.values())
    clipped = max(-cap, min(cap, raw))
    return {
        "parts": parts,
        "raw": round(raw, 6),
        "delta_goals": round(clipped, 6),
        "clipped": abs(raw - clipped) > 1e-12,
        "cap": cap,
    }


def apply_situation_team_line(
    team: str,
    game_id: str,
    *,
    flags: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Apply-on-read situation Δ to the Ch1 team GF/G line."""
    base = get_team_prior(team)
    if base is None:
        return {"present": False, "team": str(team).upper()}
    gp = float(base.get("gp") or 82) or 82.0
    gf_pg_base = float(base["gf"]) / gp
    ga_pg_base = float(base["ga"]) / gp
    fr = flags if flags is not None else get_team_game_flags(team, game_id)
    if fr is None:
        return {
            "present": True,
            "team": str(team).upper(),
            "game_id": game_id,
            "flags": None,
            "delta_goals": 0.0,
            "gf_pg_base": gf_pg_base,
            "gf_pg": gf_pg_base,
            "ga_pg": ga_pg_base,
            "ga_pg_base": ga_pg_base,
            "net_rating": float(base.get("net_rating") or 0.0),
            "situation_applied": False,
        }
    adj = situation_delta_goals(fr)
    return {
        "present": True,
        "team": str(team).upper(),
        "game_id": game_id,
        "flags": {
            "home": bool(fr.get("home")),
            "b2b": bool(fr.get("b2b")),
            "travel": bool(fr.get("travel")),
            "altitude": bool(fr.get("altitude")),
            "three_in_four": bool(fr.get("three_in_four")),
            "rest_days": fr.get("rest_days"),
            "venue": fr.get("venue"),
        },
        "parts": adj["parts"],
        "delta_goals_raw": adj["raw"],
        "delta_goals": adj["delta_goals"],
        "clipped": adj["clipped"],
        "gf_pg_base": round(gf_pg_base, 6),
        "gf_pg": round(gf_pg_base + adj["delta_goals"], 6),
        "ga_pg_base": round(ga_pg_base, 6),
        "ga_pg": round(ga_pg_base, 6),  # GA stays Ch1 — not a second prior
        "net_rating": float(base.get("net_rating") or 0.0),
        "situation_applied": True,
        "goal_drift_vs_base": abs(adj["delta_goals"]),
        "within_situation_cap": abs(adj["delta_goals"])
        <= P.NHL_SITUATION_GOAL_CAP + 1e-9,
    }


def apply_situation_player_projections(
    team: str,
    game_id: str,
    *,
    flags: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Copy-through skater G / goalie SA only when situation Δ ≠ 0.

    Scales existing Ch5 means to the situation-adjusted team GF/G.
    TOI, goalie shares, SV%, GAA unchanged. No new means / no new TOI grid.
    """
    line = apply_situation_team_line(team, game_id, flags=flags)
    skaters = get_team_skaters(team)
    goalies = get_team_goalies(team)
    if not skaters:
        return {"present": False, "team": str(team).upper(), "skaters": [], "goalies": []}

    base_sum_g = sum(float(r["G"]) for r in skaters)
    target = float(line["gf_pg"])
    delta = float(line.get("delta_goals") or 0.0)
    base_gf = float(line.get("gf_pg_base") or target)

    if abs(delta) < 1e-12 or base_sum_g <= 0:
        return {
            "present": True,
            "team": str(team).upper(),
            "game_id": game_id,
            "copy_through": False,
            "sum_g": round(base_sum_g, 4),
            "target_gf_pg": round(target, 6),
            "g_drift": round(abs(base_sum_g - target), 6),
            "within_residual_cap": abs(base_sum_g - base_gf)
            <= P.NHL_TEAM_REBASE_RESIDUAL_CAP + 1e-6,
            "sum_start_share": round(
                sum(float(g.get("start_share") or 0) for g in goalies), 8
            ),
            "team_line": line,
            "skaters": [dict(r) for r in skaters],
            "goalies": [dict(r) for r in goalies],
        }

    scale = target / base_sum_g
    out_skaters: List[Dict[str, Any]] = []
    for r in skaters:
        row = dict(r)
        g = float(r["G"]) * scale
        a = float(r["A"])
        row["G"] = round(g, 4)
        row["P"] = round(g + a, 4)
        sig = dict(r.get("sigma") or {})
        if "G" in sig:
            sig["G"] = round(float(sig["G"]) * scale, 4)
            sig["P"] = round(
                (sig["G"] ** 2 + float(sig.get("A") or 0) ** 2) ** 0.5, 4
            )
        row["sigma"] = sig
        row["situation_g_scale"] = round(scale, 6)
        out_skaters.append(row)

    # Goalie SA volume tracks the same game-script scale; shares / SV% / GAA fixed.
    sa_scale = target / base_gf if base_gf > 0 else 1.0
    out_goalies: List[Dict[str, Any]] = []
    for r in goalies:
        row = dict(r)
        sa = float(r["SA"]) * sa_scale
        sv = float(r["SV_pct"])
        row["SA"] = round(sa, 4)
        row["SAVES"] = round(sa * sv, 4)
        sig = dict(r.get("sigma") or {})
        if "SA" in sig:
            sig["SA"] = round(float(sig["SA"]) * sa_scale, 4)
        if "SAVES" in sig:
            sig["SAVES"] = round(float(sig["SAVES"]) * sa_scale, 4)
        row["sigma"] = sig
        row["situation_sa_scale"] = round(sa_scale, 6)
        out_goalies.append(row)

    sum_g = sum(float(p["G"]) for p in out_skaters)
    sum_share = sum(float(g.get("start_share") or 0) for g in out_goalies)
    return {
        "present": True,
        "team": str(team).upper(),
        "game_id": game_id,
        "copy_through": True,
        "sum_g": round(sum_g, 4),
        "target_gf_pg": round(target, 6),
        "g_drift": round(abs(sum_g - target), 6),
        "within_residual_cap": abs(sum_g - target)
        <= P.NHL_TEAM_REBASE_RESIDUAL_CAP + 1e-6,
        "sum_start_share": round(sum_share, 8),
        "team_line": line,
        "skaters": out_skaters,
        "goalies": out_goalies,
    }


def documentation() -> Dict[str, Any]:
    coeffs = load_situation_coeffs()
    return {
        "module": "src.services.nhl_season_engine.situation",
        "engine_version": P.ENGINE_VERSION,
        "NHL_SITUATION_GOAL_CAP": P.NHL_SITUATION_GOAL_CAP,
        "NHL_TEAM_CARRY_SHRINK_unchanged": P.NHL_TEAM_CARRY_SHRINK,
        "NHL_TEAM_REBASE_RESIDUAL_CAP": P.NHL_TEAM_REBASE_RESIDUAL_CAP,
        "coefficients": coeffs.get("coefficients"),
        "units": "goals_per_game_on_team_gf",
        "paths": {
            "coeffs": str(COEFF_PATH),
            "schedule": str(SCHED_PATH),
            "venue_flags": str(VENUE_PATH),
            "paper_sim": str(PAPER_PATH),
        },
        "does_not": coeffs.get("does_not")
        or [
            "team if",
            "new player means",
            "new TOI grid",
            "fill KEINHL / board emit",
            "props PLAY",
            "change NHL_TEAM_CARRY_SHRINK 0.85",
            "NBA/WNBA/CFB/NFL",
            "copy NBA +2.0 or WNBA +1.5",
        ],
    }
