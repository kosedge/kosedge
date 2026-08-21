"""Scoped NFL kicker / FG / XP layer for season-engine scoring + game boxes.

Doctrine (2026-08-11): kickers matter for totals, close games, and boxes.
This is a **first-class FG path**, not a full special-teams research project.

Status: ``approximate`` — coarse short/mid/long bands from recent-season
league priors (+ optional team overlays). Thin per-kicker distance samples
are not required; named K1 is attached when depth SoT has a kicker, else
the team profile is anonymous.

Not in scope: ST EPA, return TDs, punt/coverage, K prop board / DFS ranks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# League priors (~2022–2024 NFL regular season shapes; approximate)
# ---------------------------------------------------------------------------
# Teams attempt ~1.7–2.0 FGs / game; league FG make% ~84% overall.
LEAGUE_FG_ATTEMPTS_PER_TEAM_GAME = 1.85
# Coarse bands (collapsed from nflverse 0_19…60_plus).
FG_BANDS: Tuple[str, ...] = ("short", "mid", "long")
LEAGUE_FG_BAND_SHARES: Dict[str, float] = {
    "short": 0.48,  # 0–39
    "mid": 0.33,  # 40–49
    "long": 0.19,  # 50+
}
LEAGUE_FG_MAKE_RATE_BY_BAND: Dict[str, float] = {
    "short": 0.94,
    "mid": 0.82,
    "long": 0.68,
}
POINTS_PER_FG = 3.0
POINTS_PER_XP = 1.0
LEAGUE_XP_MAKE_RATE = 0.960
TWO_POINT_ATTEMPT_RATE = 0.045
# Pace sensitivity: more plays → slightly more FG opportunities.
FG_PACE_SENSITIVITY = 0.35
# Script: leading late → more FG attempts (stall / chew clock).
SCRIPT_FG_ATTEMPT_MULT = {
    "large_lead": 1.14,
    "small_lead": 1.06,
    "neutral": 1.00,
    "small_deficit": 0.94,
    "large_deficit": 0.86,
}
# Weather / roof (simple multipliers; outdoor adverse is opt-in).
DOME_OR_CLOSED_ROOF_TEAMS = frozenset(
    {"ATL", "DET", "NO", "IND", "LV", "MIN", "ARI", "DAL", "HOU"}
)
DOME_LONG_MAKE_MULT = 1.04
DOME_LONG_SHARE_MULT = 1.08
OUTDOOR_ADVERSE_LONG_MAKE_MULT = 0.85
OUTDOOR_ADVERSE_LONG_SHARE_MULT = 0.80
OUTDOOR_ADVERSE_FG_ATTEMPT_MULT = 0.95
# Season / game conservation band (team-games).
LEAGUE_FG_ATT_PER_TEAM_GAME_MIN = 1.20
LEAGUE_FG_ATT_PER_TEAM_GAME_MAX = 2.60
# Season games for sanity (32 × 17).
GAMES_PER_TEAM_SEASON = 17.0
LEAGUE_TEAMS = 32

KICKER_LAYER_VERSION = "kicker-layer-v1-approximate"


@dataclass(frozen=True)
class TeamKickerProfile:
    """Team-level kicking profile (anonymous unless depth has K1)."""

    team: str
    fg_attempts_per_game: float = LEAGUE_FG_ATTEMPTS_PER_TEAM_GAME
    make_rate_by_band: Dict[str, float] = field(
        default_factory=lambda: dict(LEAGUE_FG_MAKE_RATE_BY_BAND)
    )
    band_shares: Dict[str, float] = field(
        default_factory=lambda: dict(LEAGUE_FG_BAND_SHARES)
    )
    xp_make_rate: float = LEAGUE_XP_MAKE_RATE
    kicker_name: str = ""
    kicker_key: str = ""
    source: str = "league_prior"


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def is_dome_team(team: str) -> bool:
    return str(team or "").upper() in DOME_OR_CLOSED_ROOF_TEAMS


def resolve_kicker_from_roster(
    roles: Sequence[Any],
    *,
    team: str,
) -> Tuple[str, str]:
    """Return (kicker_name, kicker_key) for depth-chart K1 when present."""
    kickers = [
        r
        for r in roles
        if str(getattr(r, "position", "") or "").upper() == "K"
        and str(getattr(r, "team", "") or "").upper() == str(team).upper()
    ]
    if not kickers:
        return "", ""
    kickers.sort(key=lambda r: int(getattr(r, "depth_order", 99) or 99))
    top = kickers[0]
    return str(getattr(top, "player_name", "") or ""), str(
        getattr(top, "player_key", "") or ""
    )


def team_kicker_profile(
    team: str,
    *,
    roles: Optional[Sequence[Any]] = None,
    fg_attempts_per_game: Optional[float] = None,
) -> TeamKickerProfile:
    name, key = ("", "")
    if roles is not None:
        name, key = resolve_kicker_from_roster(roles, team=team)
    return TeamKickerProfile(
        team=str(team).upper(),
        fg_attempts_per_game=float(
            fg_attempts_per_game
            if fg_attempts_per_game is not None
            else LEAGUE_FG_ATTEMPTS_PER_TEAM_GAME
        ),
        kicker_name=name,
        kicker_key=key,
        source="depth_k1" if name else "league_prior",
    )


def script_fg_attempt_multiplier(
    *,
    script_detail: str = "neutral",
    time_bucket: str = "mid",
) -> float:
    base = float(SCRIPT_FG_ATTEMPT_MULT.get(str(script_detail or "neutral"), 1.0))
    if str(time_bucket) == "late" and str(script_detail) in (
        "large_lead",
        "small_lead",
    ):
        base *= 1.06
    elif str(time_bucket) == "late" and str(script_detail) == "large_deficit":
        base *= 0.92
    return _clamp(base, 0.75, 1.35)


def weather_fg_multipliers(
    team: str,
    *,
    outdoor_adverse: bool = False,
) -> Dict[str, float]:
    """Return make/share/attempt multipliers for long FGs + overall attempts."""
    dome = is_dome_team(team)
    long_make = 1.0
    long_share = 1.0
    attempt = 1.0
    if dome:
        long_make *= DOME_LONG_MAKE_MULT
        long_share *= DOME_LONG_SHARE_MULT
    elif outdoor_adverse:
        long_make *= OUTDOOR_ADVERSE_LONG_MAKE_MULT
        long_share *= OUTDOOR_ADVERSE_LONG_SHARE_MULT
        attempt *= OUTDOOR_ADVERSE_FG_ATTEMPT_MULT
    return {
        "long_make_mult": long_make,
        "long_share_mult": long_share,
        "attempt_mult": attempt,
        "roof": "dome" if dome else ("outdoor_adverse" if outdoor_adverse else "outdoor"),
    }


def _adjusted_band_shares(
    base_shares: Mapping[str, float],
    *,
    long_share_mult: float,
) -> Dict[str, float]:
    shares = {b: float(base_shares.get(b, 0.0)) for b in FG_BANDS}
    shares["long"] = max(0.0, shares["long"] * float(long_share_mult))
    # Renormalize short/mid to absorb long share change.
    other = shares["short"] + shares["mid"]
    target_other = max(0.0, 1.0 - shares["long"])
    if other > 0:
        scale = target_other / other
        shares["short"] *= scale
        shares["mid"] *= scale
    else:
        shares["short"] = target_other * 0.6
        shares["mid"] = target_other * 0.4
    total = sum(shares.values()) or 1.0
    return {b: shares[b] / total for b in FG_BANDS}


def project_game_kicking(
    *,
    team: str,
    offensive_tds: float,
    pace_plays: float = 63.5,
    script_detail: str = "neutral",
    time_bucket: str = "mid",
    profile: Optional[TeamKickerProfile] = None,
    outdoor_adverse: bool = False,
    league_base_plays: float = 63.5,
) -> Dict[str, Any]:
    """Expected FG attempts/makes by band + XP for one team-game.

    Pure expectation (no RNG). Callers MC-average across scripts/TDs.
    """
    profile = profile or team_kicker_profile(team)
    weather = weather_fg_multipliers(team, outdoor_adverse=outdoor_adverse)
    pace_factor = 1.0 + FG_PACE_SENSITIVITY * (
        (float(pace_plays) / max(1.0, float(league_base_plays))) - 1.0
    )
    pace_factor = _clamp(pace_factor, 0.85, 1.20)
    script_mult = script_fg_attempt_multiplier(
        script_detail=script_detail, time_bucket=time_bucket
    )
    fg_att = (
        float(profile.fg_attempts_per_game)
        * pace_factor
        * script_mult
        * float(weather["attempt_mult"])
    )
    fg_att = _clamp(fg_att, 0.35, 4.5)

    shares = _adjusted_band_shares(
        profile.band_shares, long_share_mult=float(weather["long_share_mult"])
    )
    attempts_by_band = {b: fg_att * shares[b] for b in FG_BANDS}
    makes_by_band: Dict[str, float] = {}
    for band in FG_BANDS:
        rate = float(profile.make_rate_by_band.get(band, LEAGUE_FG_MAKE_RATE_BY_BAND[band]))
        if band == "long":
            rate *= float(weather["long_make_mult"])
        rate = _clamp(rate, 0.35, 0.99)
        makes_by_band[band] = attempts_by_band[band] * rate

    fg_made = sum(makes_by_band.values())
    xp_att = max(0.0, float(offensive_tds)) * (1.0 - TWO_POINT_ATTEMPT_RATE)
    xp_made = xp_att * _clamp(float(profile.xp_make_rate), 0.85, 0.995)
    points_fg = fg_made * POINTS_PER_FG
    points_xp = xp_made * POINTS_PER_XP

    return {
        "team": str(team).upper(),
        "kicker_name": profile.kicker_name,
        "kicker_key": profile.kicker_key,
        "source": profile.source,
        "fg_att": round(fg_att, 4),
        "fg_made": round(fg_made, 4),
        "fg_att_by_band": {b: round(attempts_by_band[b], 4) for b in FG_BANDS},
        "fg_made_by_band": {b: round(makes_by_band[b], 4) for b in FG_BANDS},
        "xp_att": round(xp_att, 4),
        "xp_made": round(xp_made, 4),
        "points_from_fg": round(points_fg, 4),
        "points_from_xp": round(points_xp, 4),
        "points_from_kicking": round(points_fg + points_xp, 4),
        "script_fg_mult": round(script_mult, 4),
        "pace_factor": round(pace_factor, 4),
        "weather": weather,
        "model_status": "approximate",
        "kicker_layer_version": KICKER_LAYER_VERSION,
    }


def kicking_points_for_season_production(
    *,
    team: str,
    offensive_tds: float,
    games: float = GAMES_PER_TEAM_SEASON,
    profile: Optional[TeamKickerProfile] = None,
    outdoor_adverse: bool = False,
) -> Dict[str, float]:
    """Season-scale FG/XP points from offensive TD count + per-game FG volume.

    Used by the scoring bridge to replace the proportional FG stub.
    """
    games = max(1.0, float(games))
    per_game_tds = float(offensive_tds) / games
    # Neutral script / league pace for season bridge (script averages out).
    game = project_game_kicking(
        team=team,
        offensive_tds=per_game_tds,
        pace_plays=63.5,
        script_detail="neutral",
        time_bucket="mid",
        profile=profile,
        outdoor_adverse=outdoor_adverse,
    )
    return {
        "fg_att": round(float(game["fg_att"]) * games, 3),
        "fg_made": round(float(game["fg_made"]) * games, 3),
        "xp_att": round(float(game["xp_att"]) * games, 3),
        "xp_made": round(float(game["xp_made"]) * games, 3),
        "points_from_fg": round(float(game["points_from_fg"]) * games, 3),
        "points_from_xp": round(float(game["points_from_xp"]) * games, 3),
        "points_from_kicking": round(float(game["points_from_kicking"]) * games, 3),
    }


def fg_environment_points_delta(
    team: str,
    *,
    outdoor_adverse: bool = False,
) -> float:
    """Small additive total adjustment so Layer-2 totals feel roof/weather.

    Approximate only — does not re-sculpt Path A calibration. Magnitude
    kept small (~±0.4 pts) so W/L zero-sum stays intact.
    """
    weather = weather_fg_multipliers(team, outdoor_adverse=outdoor_adverse)
    if weather["roof"] == "dome":
        return 0.35
    if weather["roof"] == "outdoor_adverse":
        return -0.40
    return 0.0


def summarize_kicking_replicates(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Mean-aggregate per-replicate ``project_game_kicking`` dicts."""
    if not rows:
        return {}
    n = float(len(rows))
    keys = ("fg_att", "fg_made", "xp_att", "xp_made", "points_from_fg", "points_from_xp", "points_from_kicking")
    out: Dict[str, Any] = {
        "team": rows[0].get("team"),
        "kicker_name": rows[0].get("kicker_name") or "",
        "kicker_key": rows[0].get("kicker_key") or "",
        "source": rows[0].get("source") or "league_prior",
        "model_status": "approximate",
        "kicker_layer_version": KICKER_LAYER_VERSION,
        "n": int(n),
    }
    for k in keys:
        out[k] = round(sum(float(r.get(k) or 0.0) for r in rows) / n, 3)
    # Band means
    for band in FG_BANDS:
        out[f"fg_att_{band}"] = round(
            sum(float((r.get("fg_att_by_band") or {}).get(band) or 0.0) for r in rows)
            / n,
            3,
        )
        out[f"fg_made_{band}"] = round(
            sum(float((r.get("fg_made_by_band") or {}).get(band) or 0.0) for r in rows)
            / n,
            3,
        )
    out["weather_roof"] = (rows[0].get("weather") or {}).get("roof", "outdoor")
    return out


def league_fg_volume_sanity(
    team_fg_attempts: Sequence[float],
    *,
    games_per_team: float = GAMES_PER_TEAM_SEASON,
) -> Dict[str, Any]:
    """Conservation check: league FG volume in a realistic band (not 0, not every drive)."""
    n_teams = len(team_fg_attempts)
    total_att = float(sum(team_fg_attempts))
    if n_teams <= 0 or games_per_team <= 0:
        return {
            "ok": False,
            "reason": "empty_input",
            "total_fg_att": 0.0,
            "per_team_game": 0.0,
        }
    per_team_game = total_att / (n_teams * float(games_per_team))
    ok = LEAGUE_FG_ATT_PER_TEAM_GAME_MIN <= per_team_game <= LEAGUE_FG_ATT_PER_TEAM_GAME_MAX
    zero_fail = total_att <= 1e-6
    return {
        "ok": bool(ok and not zero_fail),
        "zero_fg_fail": bool(zero_fail),
        "total_fg_att": round(total_att, 2),
        "per_team_game": round(per_team_game, 4),
        "band": [LEAGUE_FG_ATT_PER_TEAM_GAME_MIN, LEAGUE_FG_ATT_PER_TEAM_GAME_MAX],
        "n_teams": n_teams,
        "reason": (
            "zero_fg_league"
            if zero_fail
            else ("ok" if ok else "outside_realistic_band")
        ),
    }


def kicker_layer_documentation() -> Dict[str, Any]:
    try:
        from src.services.nfl_kdst_publish import kdst_publish_status

        publish = kdst_publish_status(2026)
    except Exception:
        publish = {"status": "missing"}
    return {
        "version": KICKER_LAYER_VERSION,
        "status": "approximate",
        "bands": list(FG_BANDS),
        "league_fg_attempts_per_team_game": LEAGUE_FG_ATTEMPTS_PER_TEAM_GAME,
        "league_fg_make_rate_by_band": dict(LEAGUE_FG_MAKE_RATE_BY_BAND),
        "league_fg_band_shares": dict(LEAGUE_FG_BAND_SHARES),
        "league_xp_make_rate": LEAGUE_XP_MAKE_RATE,
        "two_point_attempt_rate": TWO_POINT_ATTEMPT_RATE,
        "points_per_fg": POINTS_PER_FG,
        "points_per_xp": POINTS_PER_XP,
        "script_fg_attempt_mult": dict(SCRIPT_FG_ATTEMPT_MULT),
        "dome_teams": sorted(DOME_OR_CLOSED_ROOF_TEAMS),
        "kdst_publish": publish,
        "notes": (
            "Coarse short/mid/long FG model + near-constant XP. "
            "Script (lead late → more FG) and dome/outdoor-adverse knobs "
            "are light multipliers. Named Fantasy K/DST wait on "
            "nfl_kdst_publish artifact → nfl_fantasy_season_draft_rankings. "
            "Not a calibrated per-kicker distance market."
        ),
    }
