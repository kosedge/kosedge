#!/usr/bin/env python3
"""Build NHL Chapter 3 situation packs: schedule flags + venue + paper-sim coeffs.

Classes (one coefficient each, goal units): home, Rest/B2B, travel, altitude venue.
Cap NHL_SITUATION_GOAL_CAP so situation ≠ second prior.
Does not rewrite Ch1 prior, Ch2 TOI/tandem, or Ch5 means on disk.
Does not copy NBA +2.0 or WNBA +1.5.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from itertools import product
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


def _utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "services/model-service/src/services/nhl_season_engine/data"
SCHED_SRC = DATA / "nhl_schedule_2026.json"
PRIOR_PATH = DATA / "nhl_team_prior_2026.json"
SCHED_OUT = DATA / "nhl_situation_schedule_2026.json"
VENUE_OUT = DATA / "nhl_venue_flags.json"
COEFF_OUT = DATA / "nhl_situation_coeffs_v0.json"
PAPER_OUT = DATA / "nhl_situation_paper_sim_ch3.json"

ENGINE_VERSION = "nhl-season-engine-v0.1"
NHL_TEAM_CARRY_SHRINK = 0.85
NHL_TEAM_REBASE_RESIDUAL_CAP = 0.15
# Situation ≠ second prior: cap below ~0.4 G/G carry scale; paper-sim picks coeffs.
NHL_SITUATION_GOAL_CAP = 0.35
TRAVEL_MILES_MIN = 1000.0
TRAVEL_TZ_MIN = 2

# Home arena metro lat/lon/tz_offset_hours (standard time; DST ignored at class grain).
TEAM_METRO: Dict[str, Tuple[float, float, int]] = {
    "ANA": (33.8078, -117.8765, -8),
    "BOS": (42.3662, -71.0621, -5),
    "BUF": (42.8750, -78.8764, -5),
    "CGY": (51.0374, -114.0519, -7),
    "CAR": (35.8033, -78.7219, -5),
    "CHI": (41.8807, -87.6742, -6),
    "COL": (39.7487, -105.0077, -7),
    "CBJ": (39.9692, -83.0061, -5),
    "DAL": (32.7905, -96.8103, -6),
    "DET": (42.3411, -83.0550, -5),
    "EDM": (53.5469, -113.4979, -7),
    "FLA": (26.1585, -80.3256, -5),
    "LAK": (34.0430, -118.2673, -8),
    "MIN": (44.9447, -93.1011, -6),
    "MTL": (45.4961, -73.5693, -5),
    "NSH": (36.1592, -86.7785, -6),
    "NJD": (40.7336, -74.1711, -5),
    "NYI": (40.7227, -73.5905, -5),
    "NYR": (40.7505, -73.9934, -5),
    "OTT": (45.2969, -75.9271, -5),
    "PHI": (39.9012, -75.1720, -5),
    "PIT": (40.4394, -79.9893, -5),
    "SJS": (37.3328, -121.9012, -8),
    "SEA": (47.6221, -122.3540, -8),
    "STL": (38.6268, -90.2026, -6),
    "TBL": (27.9427, -82.4518, -5),
    "TOR": (43.6435, -79.3791, -5),
    "UTA": (40.7683, -111.9011, -7),
    "VAN": (49.2777, -123.1089, -8),
    "VGK": (36.1029, -115.1784, -8),
    "WPG": (49.8927, -97.1436, -6),
    "WSH": (38.8981, -77.0209, -5),
}

# Extra / outdoor / alternate venues keyed by venue string from official schedule.
EXTRA_VENUE_METRO: Dict[str, Tuple[float, float, int]] = {
    "Rice-Eccles Stadium": (40.7599, -111.8489, -7),  # SLC outdoor
}

# NHL goal-unit paper-sim grids — not NBA +2.0 / WNBA +1.5.
PAPER_HOME = (0.10, 0.15, 0.20, 0.25)
PAPER_B2B = (-0.10, -0.15, -0.20)
PAPER_TRAVEL = (-0.05, -0.08, -0.10)
PAPER_ALTITUDE = (0.08, 0.12, 0.15, 0.20)

# League-sane GF/G band after situation Δ (Ch1 ~2.5–3.6 ± cap).
GF_PG_BAND = (2.0, 4.5)


def _haversine_miles(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    r = 3958.8
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _venue_metro(venue: str, home_ta: str) -> Tuple[float, float, int]:
    if venue in EXTRA_VENUE_METRO:
        return EXTRA_VENUE_METRO[venue]
    if home_ta in TEAM_METRO:
        return TEAM_METRO[home_ta]
    return TEAM_METRO["NYR"]


def _parse_games(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    games: List[Dict[str, Any]] = []
    for g in raw.get("games") or []:
        gid = str(g.get("game_id") or "")
        if not gid:
            continue
        games.append(
            {
                "game_id": gid,
                "date": str(g.get("game_date") or "")[:10],
                "home": str(g.get("home") or "").upper(),
                "away": str(g.get("away") or "").upper(),
                "venue": str(g.get("venue") or ""),
                "start_time_utc": g.get("start_time_utc"),
                "game_type": g.get("game_type"),
                "game_state": g.get("game_state"),
            }
        )
    games.sort(key=lambda r: (r["date"], r["game_id"]))
    return games


def _build_team_timeline(games: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    by: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for g in games:
        for side, team in (("home", g["home"]), ("away", g["away"])):
            lat, lon, tz = _venue_metro(g["venue"], g["home"])
            by[team].append(
                {
                    "game_id": g["game_id"],
                    "date": g["date"],
                    "side": side,
                    "opponent": g["away"] if side == "home" else g["home"],
                    "venue": g["venue"],
                    "lat": lat,
                    "lon": lon,
                    "tz": tz,
                }
            )
    for team in by:
        by[team].sort(key=lambda r: (r["date"], r["game_id"]))
    return by


def _annotate_flags(
    timeline: Dict[str, List[Dict[str, Any]]],
    altitude_venues: Set[str],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for team, games in timeline.items():
        dates = [datetime.strptime(g["date"], "%Y-%m-%d").date() for g in games]
        for i, g in enumerate(games):
            d = dates[i]
            rest_days: Optional[int] = None if i == 0 else (d - dates[i - 1]).days
            window = [x for x in dates[: i + 1] if (d - x).days <= 3]
            three_in_four = len(window) >= 3
            # Rest / B2B class: true rest=1 or compressed 3-in-4.
            b2b = bool(rest_days == 1 or three_in_four)

            travel = False
            travel_miles = 0.0
            travel_tz = 0
            if i > 0:
                prev = games[i - 1]
                travel_miles = _haversine_miles(
                    (prev["lat"], prev["lon"]), (g["lat"], g["lon"])
                )
                travel_tz = abs(int(g["tz"]) - int(prev["tz"]))
                travel = travel_miles >= TRAVEL_MILES_MIN or travel_tz >= TRAVEL_TZ_MIN

            altitude = g["venue"] in altitude_venues
            home = g["side"] == "home"

            rows.append(
                {
                    "team": team,
                    "game_id": g["game_id"],
                    "date": g["date"],
                    "side": g["side"],
                    "home": home,
                    "b2b": b2b,
                    "rest_days": rest_days,
                    "three_in_four": three_in_four,
                    "travel": travel,
                    "travel_miles": round(travel_miles, 1),
                    "travel_tz": travel_tz,
                    "altitude": altitude,
                    "venue": g["venue"],
                }
            )
    return rows


def _delta(
    flags: Dict[str, Any], coeffs: Dict[str, float]
) -> Tuple[float, float, Dict[str, float]]:
    parts = {
        "home": coeffs["home"] if flags["home"] else 0.0,
        "b2b": coeffs["b2b"] if flags["b2b"] else 0.0,
        "travel": coeffs["travel"] if flags["travel"] else 0.0,
        "altitude": 0.0,
    }
    if flags["altitude"]:
        # Venue flag; sign by side at the venue (not if team ==).
        parts["altitude"] = (
            coeffs["altitude"] if flags["home"] else -coeffs["altitude"]
        )
    raw = sum(parts.values())
    clipped = max(-NHL_SITUATION_GOAL_CAP, min(NHL_SITUATION_GOAL_CAP, raw))
    return raw, clipped, parts


def _paper_sim(flag_rows: List[Dict[str, Any]]) -> Tuple[Dict[str, float], Dict[str, Any]]:
    results = []
    for home, b2b, travel, alt in product(
        PAPER_HOME, PAPER_B2B, PAPER_TRAVEL, PAPER_ALTITUDE
    ):
        coeffs = {"home": home, "b2b": b2b, "travel": travel, "altitude": alt}
        raws = []
        clips = 0
        for fr in flag_rows:
            raw, clipped, _ = _delta(fr, coeffs)
            raws.append(raw)
            if abs(raw - clipped) > 1e-12:
                clips += 1
        mean_abs = sum(abs(x) for x in raws) / len(raws)
        mean_signed = sum(raws) / len(raws)
        clip_rate = clips / len(raws)
        # NHL goal units: low clip + modest |Δ|; prefer mid of NHL grids (not NBA 2.0).
        score = (
            clip_rate * 100.0
            + abs(home - 0.15) * 0.5
            + abs(abs(b2b) - 0.15) * 0.5
            + abs(abs(travel) - 0.08) * 0.25
            + abs(abs(alt) - 0.12) * 0.25
            + mean_abs * 2.0
        )
        results.append(
            {
                "coeffs": coeffs,
                "clip_rate": round(clip_rate, 6),
                "mean_abs_raw": round(mean_abs, 4),
                "mean_signed_raw": round(mean_signed, 4),
                "max_abs_raw": round(max(abs(x) for x in raws), 4),
                "score": round(score, 6),
            }
        )
    results.sort(key=lambda r: r["score"])
    chosen = results[0]["coeffs"]
    return chosen, {
        "engine_version": ENGINE_VERSION,
        "as_of": _utc_today(),
        "season_schedule": "2026-27",
        "n_team_games": len(flag_rows),
        "NHL_SITUATION_GOAL_CAP": NHL_SITUATION_GOAL_CAP,
        "units": "goals_per_game_on_team_gf",
        "grids": {
            "home": list(PAPER_HOME),
            "b2b": list(PAPER_B2B),
            "travel": list(PAPER_TRAVEL),
            "altitude": list(PAPER_ALTITUDE),
        },
        "travel_thresholds": {"miles": TRAVEL_MILES_MIN, "tz": TRAVEL_TZ_MIN},
        "chosen": chosen,
        "top5": results[:5],
        "not_copied": {"nba_home": 2.0, "wnba_home": 1.5},
        "prevalence": {
            "home": sum(1 for r in flag_rows if r["home"]) / len(flag_rows),
            "b2b": sum(1 for r in flag_rows if r["b2b"]) / len(flag_rows),
            "travel": sum(1 for r in flag_rows if r["travel"]) / len(flag_rows),
            "altitude": sum(1 for r in flag_rows if r["altitude"]) / len(flag_rows),
            "three_in_four": sum(1 for r in flag_rows if r["three_in_four"])
            / len(flag_rows),
        },
    }


def main() -> None:
    if not SCHED_SRC.is_file():
        raise SystemExit(f"missing schedule source {SCHED_SRC}")
    raw = json.loads(SCHED_SRC.read_text(encoding="utf-8"))
    games = _parse_games(raw)

    venue_flags = {
        "engine_version": ENGINE_VERSION,
        "as_of": _utc_today(),
        "note": "Altitude is a venue flag (venue name), not if team ==.",
        "altitude_venues": [
            {"venue": "Ball Arena"},
            {"venue": "Delta Center"},
            {"venue": "Rice-Eccles Stadium"},
        ],
    }
    alt_set = {v["venue"] for v in venue_flags["altitude_venues"]}

    timeline = _build_team_timeline(games)
    flag_rows = _annotate_flags(timeline, alt_set)
    chosen, paper = _paper_sim(flag_rows)

    prior = json.loads(PRIOR_PATH.read_text(encoding="utf-8"))
    gf_adj: List[float] = []
    for fr in flag_rows:
        team = prior["teams"][fr["team"]]
        gp = float(team.get("gp") or 82) or 82.0
        base = float(team["gf"]) / gp
        _, clipped, _ = _delta(fr, chosen)
        gf_adj.append(base + clipped)
    paper["gf_pg_adj_range"] = [round(min(gf_adj), 4), round(max(gf_adj), 4)]
    paper["gf_pg_band"] = list(GF_PG_BAND)
    paper["ga_note"] = (
        "Situation Δ is goals on the Ch1 GF/G line; GA remains Ch1 shrunk; "
        "Δ does not invent a second net prior."
    )
    if paper["gf_pg_adj_range"][0] < GF_PG_BAND[0] or paper["gf_pg_adj_range"][1] > GF_PG_BAND[1]:
        raise SystemExit(f"GF/G after Δ outside band: {paper['gf_pg_adj_range']}")

    # Chosen home must not be NBA/WNBA point anchors.
    if abs(chosen["home"] - 2.0) < 1e-9 or abs(chosen["home"] - 1.5) < 1e-9:
        raise SystemExit(f"refusing NBA/WNBA home copy: {chosen}")

    sched_out = {
        "engine_version": ENGINE_VERSION,
        "as_of": paper["as_of"],
        "season": "2026-27",
        "source": "nhl_schedule_2026.json (official) + situation flags",
        "game_count": len(games),
        "team_game_count": len(flag_rows),
        "date_range": [games[0]["date"], games[-1]["date"]],
        "games": games,
        "team_games": flag_rows,
        "does_not": [
            "rewrite nhl_schedule_2026.json fetcher pack",
            "rewrite Ch1/Ch2/Ch5 packs",
            "fill KEINHL",
            "props PLAY",
        ],
    }

    coeffs_out = {
        "engine_version": ENGINE_VERSION,
        "as_of": paper["as_of"],
        "chapter": 3,
        "NHL_SITUATION_GOAL_CAP": NHL_SITUATION_GOAL_CAP,
        "NHL_TEAM_CARRY_SHRINK_unchanged": NHL_TEAM_CARRY_SHRINK,
        "NHL_TEAM_REBASE_RESIDUAL_CAP": NHL_TEAM_REBASE_RESIDUAL_CAP,
        "coefficients": chosen,
        "units": "goals_per_game_on_team_gf",
        "classes": {
            "home": "designated home side",
            "b2b": "rest_days==1 OR 3 games in 4 calendar days (Rest / B2B)",
            "travel": (
                f"prior venue ≥{TRAVEL_MILES_MIN:.0f} mi OR |Δtz|≥{TRAVEL_TZ_MIN} "
                "(official schedule metros)"
            ),
            "altitude": (
                "venue in nhl_venue_flags altitude list; +coeff home / −coeff visitor"
            ),
        },
        "formula": (
            "Δ_raw = Σ class_coeff; Δ = clip(Δ_raw, ±NHL_SITUATION_GOAL_CAP); "
            "gf_pg' = Ch1_gf/gp + Δ"
        ),
        "apply": (
            "on_read_team_line; skater G / goalie SA copy-through only when Δ≠0"
        ),
        "does_not": [
            "team if",
            "new player means",
            "new TOI grid",
            "fill KEINHL / board emit",
            "props PLAY",
            "change NHL_TEAM_CARRY_SHRINK 0.85",
            "NBA/WNBA/CFB/NFL",
            "copy NBA +2.0 or WNBA +1.5",
        ],
        "paper_sim": PAPER_OUT.name,
    }

    DATA.mkdir(parents=True, exist_ok=True)
    VENUE_OUT.write_text(json.dumps(venue_flags, indent=2) + "\n", encoding="utf-8")
    SCHED_OUT.write_text(json.dumps(sched_out, indent=2) + "\n", encoding="utf-8")
    PAPER_OUT.write_text(json.dumps(paper, indent=2) + "\n", encoding="utf-8")
    COEFF_OUT.write_text(json.dumps(coeffs_out, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote games={len(games)} team_games={len(flag_rows)} "
        f"coeffs={chosen} gf_pg_adj={paper['gf_pg_adj_range']} "
        f"clip_rate={results_clip(paper)}"
    )


def results_clip(paper: Dict[str, Any]) -> float:
    top = (paper.get("top5") or [{}])[0]
    return float(top.get("clip_rate") or 0.0)


if __name__ == "__main__":
    main()
