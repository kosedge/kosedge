"""NBA Chapter 3 — situation classes applied on read.

Classes (not teams): home · B2B/3-in-4 rest · travel (tz band) · altitude venue.
Altitude is a venue flag (Ball Arena / Delta Center), never a team-name branch.
Does not rewrite Ch2 minutes, Ch1 shrink, or Ch5 player means on disk.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from src.services.nba_season_engine import priors as P
from src.services.nba_season_engine.player_projection import (
    get_team_projections,
    load_player_projection_pack,
)
from src.services.nba_season_engine.roster_minutes import get_rebased_team

DATA_DIR = Path(__file__).resolve().parent / "data"
VENUES_PATH = DATA_DIR / "nba_venues_2026.json"
SITUATION_PATH = DATA_DIR / "nba_situation_2026.json"

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


def load_venues_pack(*, force: bool = False) -> Dict[str, Any]:
    if force:
        _CACHE.pop("venues", None)
    return _load(VENUES_PATH, "venues")


def load_situation_pack(*, force: bool = False) -> Dict[str, Any]:
    if force:
        _CACHE.pop("situation", None)
    return _load(SITUATION_PATH, "situation")


def get_venue(team_or_venue: str) -> Optional[Dict[str, Any]]:
    pack = load_venues_pack()
    return (pack.get("venues") or {}).get(str(team_or_venue).upper())


def venue_altitude_class(venue_team: str) -> bool:
    """True when the venue (home arena code) carries altitude_class."""
    v = get_venue(venue_team)
    return bool(v and v.get("altitude_class"))


def coefficients() -> Dict[str, float]:
    pack = load_situation_pack()
    stored = pack.get("coefficients") if isinstance(pack.get("coefficients"), dict) else {}
    return {
        "SITUATION_HOME_NET": float(
            stored.get("SITUATION_HOME_NET", P.SITUATION_HOME_NET)
        ),
        "SITUATION_B2B_NET": float(stored.get("SITUATION_B2B_NET", P.SITUATION_B2B_NET)),
        "SITUATION_TRAVEL_NET": float(
            stored.get("SITUATION_TRAVEL_NET", P.SITUATION_TRAVEL_NET)
        ),
        "SITUATION_ALTITUDE_NET": float(
            stored.get("SITUATION_ALTITUDE_NET", P.SITUATION_ALTITUDE_NET)
        ),
        "SITUATION_NET_CAP": float(stored.get("SITUATION_NET_CAP", P.SITUATION_NET_CAP)),
    }


def classify_side(
    *,
    home: bool,
    b2b: bool = False,
    three_in_four: bool = False,
    tz_delta_hours: float = 0.0,
    venue_team: Optional[str] = None,
    altitude_visitor: Optional[bool] = None,
) -> Dict[str, Any]:
    """Build class flags for one team-side. No team name branches."""
    rest_class = bool(b2b or three_in_four)
    travel_band = float(P.TRAVEL_TZ_BAND_MIN_HOURS)
    travel = abs(float(tz_delta_hours or 0.0)) >= travel_band
    if altitude_visitor is None:
        altitude_visitor = bool(venue_team) and venue_altitude_class(
            str(venue_team)
        ) and (not home)
    return {
        "home": bool(home),
        "b2b": bool(b2b),
        "three_in_four": bool(three_in_four),
        "rest_class": rest_class,
        "tz_delta_hours": float(tz_delta_hours or 0.0),
        "travel": bool(travel),
        "altitude_visitor": bool(altitude_visitor),
        "venue_team": str(venue_team).upper() if venue_team else None,
    }


def situation_net_delta(flags: Mapping[str, Any]) -> Dict[str, Any]:
    """Sum class coefficients with SITUATION_NET_CAP."""
    coefs = coefficients()
    parts: List[Dict[str, float]] = []
    if flags.get("home"):
        parts.append({"class": "home", "net": coefs["SITUATION_HOME_NET"]})
    if flags.get("rest_class"):
        parts.append({"class": "b2b", "net": coefs["SITUATION_B2B_NET"]})
    if flags.get("travel"):
        parts.append({"class": "travel", "net": coefs["SITUATION_TRAVEL_NET"]})
    if flags.get("altitude_visitor"):
        parts.append({"class": "altitude", "net": coefs["SITUATION_ALTITUDE_NET"]})
    raw = float(sum(p["net"] for p in parts))
    cap = float(coefs["SITUATION_NET_CAP"])
    capped = raw
    if abs(raw) > cap:
        capped = math.copysign(cap, raw)
    return {
        "parts": parts,
        "raw_net": round(raw, 4),
        "delta_net": round(float(capped), 4),
        "capped": abs(raw) > cap + 1e-12,
        "cap": cap,
        "coefficients": coefs,
    }


def _split_net_to_ratings(
    base: Mapping[str, Any],
    delta_net: float,
) -> Dict[str, float]:
    """Move net via half ORtg / half DRtg so O−D tracks net."""
    ortg0 = float(base.get("ortg") or 0.0)
    drtg0 = float(base.get("drtg") or 0.0)
    net0 = float(base.get("net_rating") or (ortg0 - drtg0))
    pace = float(base.get("pace") or 100.0)
    half = float(delta_net) / 2.0
    net1 = round(net0 + float(delta_net), 4)
    ortg1 = round(ortg0 + half, 4)
    drtg1 = round(ortg1 - net1, 4)  # keep O−D == net exactly after rounding
    implied = ortg1 * pace / 100.0
    return {
        "ortg": ortg1,
        "drtg": drtg1,
        "net_rating": net1,
        "pace": round(pace, 4),
        "implied_ppg": round(implied, 4),
    }


def apply_situation_to_team(
    team: str,
    *,
    home: bool,
    b2b: bool = False,
    three_in_four: bool = False,
    tz_delta_hours: float = 0.0,
    venue_team: Optional[str] = None,
    altitude_visitor: Optional[bool] = None,
) -> Optional[Dict[str, Any]]:
    """Frozen Ch2 prior + situation delta (on read)."""
    base = get_rebased_team(team)
    if not base:
        return None
    if venue_team is None and home:
        venue_team = str(team).upper()
    flags = classify_side(
        home=home,
        b2b=b2b,
        three_in_four=three_in_four,
        tz_delta_hours=tz_delta_hours,
        venue_team=venue_team,
        altitude_visitor=altitude_visitor,
    )
    sit = situation_net_delta(flags)
    ratings = _split_net_to_ratings(base, sit["delta_net"])
    out = {
        **dict(base),
        **ratings,
        "team": str(team).upper(),
        "baseline_net_rating": float(base.get("net_rating") or 0.0),
        "baseline_ortg": float(base.get("ortg") or 0.0),
        "baseline_drtg": float(base.get("drtg") or 0.0),
        "baseline_implied_ppg": float(base.get("implied_ppg") or 0.0),
        "situation_flags": flags,
        "situation": sit,
        "situation_applied": True,
    }
    return out


def apply_situation_to_player_projections(
    team: str,
    team_line: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    """Copy-through Ch5 rows; scale PTS/USG only if Σ PTS breaks residual cap.

    Minutes grid on disk is never rewritten. Talent means stay; on-read scale
    is identity-only when situation moves implied_ppg beyond the residual cap.
    """
    rows = [dict(r) for r in get_team_projections(team)]
    if not rows:
        return rows
    target = float(team_line.get("implied_ppg") or 0.0)
    sum_pts = float(sum(float(r.get("PTS") or 0.0) for r in rows))
    cap = float(P.TEAM_REBASE_RESIDUAL_CAP)
    drift = abs(sum_pts - target)
    if drift <= cap + 1e-9 or sum_pts <= 1e-9:
        for r in rows:
            r["situation_scaled"] = False
            r["pts_scale"] = 1.0
        return rows
    scale = target / sum_pts
    for r in rows:
        for key in ("PTS", "USG", "PRA", "PR", "RA"):
            if r.get(key) is not None:
                r[key] = round(float(r[key]) * scale, 4)
        # σ dict scales with the mean move when present
        sigma = r.get("sigma")
        if isinstance(sigma, dict):
            r["sigma"] = {
                k: round(float(v) * scale, 4) if v is not None else v
                for k, v in sigma.items()
            }
        r["situation_scaled"] = True
        r["pts_scale"] = round(scale, 6)
    return rows


def find_schedule_game(game_id: str) -> Optional[Dict[str, Any]]:
    pack = load_situation_pack()
    gid = str(game_id)
    for g in pack.get("games") or []:
        if str(g.get("game_id")) == gid:
            return g
    return None


def apply_situation_for_game(
    game_id: str,
    team: str,
) -> Optional[Dict[str, Any]]:
    """Look up schedule SoT flags and apply situation for ``team``."""
    game = find_schedule_game(game_id)
    if not game:
        return None
    t = str(team).upper()
    if t == str(game.get("home") or "").upper():
        side = "home"
        home = True
    elif t == str(game.get("away") or "").upper():
        side = "away"
        home = False
    else:
        return None
    line = apply_situation_to_team(
        t,
        home=home,
        b2b=bool(game.get(f"{side}_b2b")),
        three_in_four=bool(game.get(f"{side}_three_in_four")),
        tz_delta_hours=float(game.get(f"{side}_tz_delta") or 0.0),
        venue_team=str(game.get("venue_team") or game.get("home") or ""),
        altitude_visitor=bool(game.get(f"{side}_altitude_visitor")),
    )
    if not line:
        return None
    players = apply_situation_to_player_projections(t, line)
    sum_pts = float(sum(float(p.get("PTS") or 0.0) for p in players))
    line["player_sum_pts"] = round(sum_pts, 4)
    line["player_pts_drift"] = round(sum_pts - float(line.get("implied_ppg") or 0.0), 4)
    line["players"] = players
    line["game_id"] = str(game_id)
    return line


def documentation() -> Dict[str, Any]:
    sit = load_situation_pack()
    venues = load_venues_pack()
    return {
        "module": "src.services.nba_season_engine.situation",
        "engine_version": P.ENGINE_VERSION,
        "coefficients": coefficients(),
        "TRAVEL_TZ_BAND_MIN_HOURS": P.TRAVEL_TZ_BAND_MIN_HOURS,
        "TEAM_CARRY_SHRINK_unchanged": P.TEAM_CARRY_SHRINK,
        "TEAM_REBASE_RESIDUAL_CAP_unchanged": P.TEAM_REBASE_RESIDUAL_CAP,
        "n_games": sit.get("n_games"),
        "n_venues": len(venues.get("venues") or {}),
        "paths": {"venues": str(VENUES_PATH), "situation": str(SITUATION_PATH)},
        "does_not": sit.get("does_not")
        or [
            "emit KEI or Edge stake tags",
            "props / fantasy",
            "rewrite minutes grid",
            "change TEAM_CARRY_SHRINK",
            "team-name branches",
            "new player means",
        ],
    }
