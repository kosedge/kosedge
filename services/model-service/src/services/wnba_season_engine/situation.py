"""WNBA Chapter 3 — situation classes (apply-on-read).

Home / B2B (rest=1 or 3-in-4) / travel / altitude venue.
One coefficient per class; clipped so situation ≠ second prior.
Does not rewrite Ch2 grids or Ch5 opening-night means on disk.
Does not copy NBA coeffs — reads wnba_situation_coeffs_v0.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.services.wnba_season_engine import priors as P
from src.services.wnba_season_engine.player_projection import get_team_projections
from src.services.wnba_season_engine.roster_minutes import get_rebased_team

DATA_DIR = Path(__file__).resolve().parent / "data"
COEFF_PATH = DATA_DIR / "wnba_situation_coeffs_v0.json"
SCHED_PATH = DATA_DIR / "wnba_schedule_2025.json"
VENUE_PATH = DATA_DIR / "wnba_venue_flags.json"
PAPER_PATH = DATA_DIR / "wnba_situation_paper_sim_ch3.json"

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
        if row.get("team") == t and row.get("game_id") == gid:
            return row
    return None


def situation_delta_pts(
    flags: Dict[str, Any], coeffs: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """Compute raw + clipped team-points Δ from class flags."""
    pack = load_situation_coeffs()
    c = dict(coeffs or (pack.get("coefficients") or {}))
    cap = float(pack.get("SITUATION_TEAM_PTS_CAP") or P.SITUATION_TEAM_PTS_CAP)
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
        "delta_pts": round(clipped, 6),
        "clipped": abs(raw - clipped) > 1e-12,
        "cap": cap,
    }


def apply_situation_team_line(
    team: str,
    game_id: str,
    *,
    flags: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Apply-on-read situation Δ to the Ch2 rebased team line (implied_ppg)."""
    base = get_rebased_team(team)
    if base is None:
        return {"present": False, "team": str(team).upper()}
    fr = flags if flags is not None else get_team_game_flags(team, game_id)
    if fr is None:
        return {
            "present": True,
            "team": str(team).upper(),
            "game_id": game_id,
            "flags": None,
            "delta_pts": 0.0,
            "implied_ppg_base": float(base["implied_ppg"]),
            "implied_ppg": float(base["implied_ppg"]),
            "net_rating": float(base["net_rating"]),
            "ortg": float(base["ortg"]),
            "drtg": float(base["drtg"]),
            "pace": float(base["pace"]),
            "situation_applied": False,
        }
    adj = situation_delta_pts(fr)
    base_ppg = float(base["implied_ppg"])
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
        },
        "parts": adj["parts"],
        "delta_pts_raw": adj["raw"],
        "delta_pts": adj["delta_pts"],
        "clipped": adj["clipped"],
        "implied_ppg_base": base_ppg,
        "implied_ppg": round(base_ppg + adj["delta_pts"], 4),
        "net_rating": float(base["net_rating"]),
        "ortg": float(base["ortg"]),
        "drtg": float(base["drtg"]),
        "pace": float(base["pace"]),
        "situation_applied": True,
        "pts_drift_vs_base": abs(adj["delta_pts"]),
        "within_residual_cap": abs(adj["delta_pts"])
        <= P.WNBA_TEAM_REBASE_RESIDUAL_CAP + 1e-9,
    }


def apply_situation_player_projections(
    team: str,
    game_id: str,
    *,
    flags: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Copy-through PlayerProjection PTS only when situation Δ ≠ 0.

    Does not invent new player means or minutes — scales existing PTS to the
    situation-adjusted team total. Other counting stats unchanged.
    """
    line = apply_situation_team_line(team, game_id, flags=flags)
    rows = get_team_projections(team)
    if not rows:
        return {"present": False, "team": str(team).upper(), "players": []}
    base_sum = sum(float(r["PTS"]) for r in rows)
    target = float(line["implied_ppg"])
    delta = float(line.get("delta_pts") or 0.0)
    if abs(delta) < 1e-12 or base_sum <= 0:
        players = [dict(r) for r in rows]
        return {
            "present": True,
            "team": str(team).upper(),
            "game_id": game_id,
            "copy_through": False,
            "sum_pts": round(base_sum, 4),
            "target_pts": round(target, 4),
            "pts_drift": round(abs(base_sum - target), 6),
            "within_residual_cap": abs(base_sum - float(line["implied_ppg_base"]))
            <= P.WNBA_TEAM_REBASE_RESIDUAL_CAP + 1e-6
            or abs(delta) <= P.WNBA_TEAM_REBASE_RESIDUAL_CAP + 1e-9,
            "team_line": line,
            "players": players,
        }

    scale = target / base_sum
    players = []
    for r in rows:
        out = dict(r)
        pts = float(r["PTS"]) * scale
        reb = float(r["REB"])
        ast = float(r["AST"])
        out["PTS"] = round(pts, 4)
        out["PRA"] = round(pts + reb + ast, 4)
        out["PR"] = round(pts + reb, 4)
        sig = dict(r.get("sigma") or {})
        if "PTS" in sig:
            sig["PTS"] = round(float(sig["PTS"]) * scale, 4)
            sig["PRA"] = round(
                (
                    sig["PTS"] ** 2
                    + float(sig.get("REB") or 0) ** 2
                    + float(sig.get("AST") or 0) ** 2
                )
                ** 0.5,
                4,
            )
            sig["PR"] = round(
                (sig["PTS"] ** 2 + float(sig.get("REB") or 0) ** 2) ** 0.5, 4
            )
        out["sigma"] = sig
        out["situation_pts_scale"] = round(scale, 6)
        players.append(out)
    sum_pts = sum(float(p["PTS"]) for p in players)
    return {
        "present": True,
        "team": str(team).upper(),
        "game_id": game_id,
        "copy_through": True,
        "sum_pts": round(sum_pts, 4),
        "target_pts": round(target, 4),
        "pts_drift": round(abs(sum_pts - target), 6),
        "within_residual_cap": abs(delta) <= P.WNBA_TEAM_REBASE_RESIDUAL_CAP + 1e-9,
        "team_line": line,
        "players": players,
    }


def documentation() -> Dict[str, Any]:
    coeffs = load_situation_coeffs()
    return {
        "module": "src.services.wnba_season_engine.situation",
        "engine_version": P.ENGINE_VERSION,
        "SITUATION_TEAM_PTS_CAP": P.SITUATION_TEAM_PTS_CAP,
        "WNBA_TEAM_CARRY_SHRINK_unchanged": P.WNBA_TEAM_CARRY_SHRINK,
        "WNBA_TEAM_REBASE_RESIDUAL_CAP": P.WNBA_TEAM_REBASE_RESIDUAL_CAP,
        "MINUTE_GRID_SUM_unchanged": P.MINUTE_GRID_SUM,
        "coefficients": coeffs.get("coefficients"),
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
            "new minute grid",
            "Ch4 KEI emit",
            "props PLAY",
            "copy NBA coeffs",
            "change WNBA_TEAM_CARRY_SHRINK",
        ],
    }
