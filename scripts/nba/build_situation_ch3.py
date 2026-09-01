#!/usr/bin/env python3
"""Build NBA Chapter 3 situation packs: schedule + venue flags + paper-sim coeffs.

Classes (one coefficient each): home, B2B (rest=1 or 3-in-4), travel, altitude venue.
Cap so situation ≠ second prior. Does not rewrite Ch2 grids or Ch5 means on disk.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import date, datetime
from itertools import product
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "services/model-service/src/services/nba_season_engine/data"
SCHED_SRC = Path("/tmp/nba_sched25.json")
SCHED_OUT = DATA / "nba_schedule_2025_26.json"
VENUE_OUT = DATA / "nba_venue_flags.json"
COEFF_OUT = DATA / "nba_situation_coeffs_v0.json"
PAPER_OUT = DATA / "nba_situation_paper_sim_ch3.json"

ENGINE_VERSION = "nba-season-engine-v0.1"
SITUATION_TEAM_PTS_CAP = 3.0
TRAVEL_MILES_MIN = 1000.0
TRAVEL_TZ_MIN = 2

# Home metro lat/lon/tz_offset_hours (ET=-5 standard; DST ignored for class grain).
TEAM_METRO: dict[str, tuple[float, float, int]] = {
    "ATL": (33.7573, -84.3963, -5),
    "BOS": (42.3662, -71.0621, -5),
    "BKN": (40.6826, -73.9754, -5),
    "CHA": (35.2251, -80.8392, -5),
    "CHI": (41.8807, -87.6742, -6),
    "CLE": (41.4965, -81.6882, -5),
    "DAL": (32.7905, -96.8103, -6),
    "DEN": (39.7487, -105.0077, -7),
    "DET": (42.3411, -83.0550, -5),
    "GSW": (37.7680, -122.3877, -8),
    "HOU": (29.7508, -95.3621, -6),
    "IND": (39.7640, -86.1555, -5),
    "LAC": (33.9930, -118.2670, -8),
    "LAL": (34.0430, -118.2673, -8),
    "MEM": (35.1382, -90.0505, -6),
    "MIA": (25.7814, -80.1870, -5),
    "MIL": (43.0436, -87.9169, -6),
    "MIN": (44.9795, -93.2760, -6),
    "NOP": (29.9490, -90.0821, -6),
    "NYK": (40.7505, -73.9934, -5),
    "OKC": (35.4634, -97.5151, -6),
    "ORL": (28.5392, -81.3839, -5),
    "PHI": (39.9012, -75.1720, -5),
    "PHX": (33.4457, -112.0712, -7),
    "POR": (45.5316, -122.6668, -8),
    "SAC": (38.5803, -121.4990, -8),
    "SAS": (29.4270, -98.4375, -6),
    "TOR": (43.6435, -79.3791, -5),
    "UTA": (40.7683, -111.9011, -7),
    "WAS": (38.8981, -77.0209, -5),
}

# Extra venues (neutral / international) — keyed by (arena, city, state).
EXTRA_VENUE_METRO: dict[tuple[str, str, str], tuple[float, float, int]] = {
    ("Uber Arena", "Berlin", "Germany"): (52.5060, 13.4430, 1),
    ("O2 Arena", "London", "England"): (51.5030, 0.0032, 0),
    ("Arena CDMX", "Mexico City", "Mexico"): (19.3840, -99.0960, -6),
    ("Moody Center", "Austin", "TX"): (30.2805, -97.7308, -6),
}

# Paper-sim grids (one coeff per class). Pick by low clip-rate + mid magnitude.
PAPER_HOME = (1.5, 2.0, 2.5)
PAPER_B2B = (-1.0, -1.5, -2.0)
PAPER_TRAVEL = (-0.5, -1.0, -1.5)
PAPER_ALTITUDE = (0.5, 1.0, 1.5)


def _haversine_miles(a: tuple[float, float], b: tuple[float, float]) -> float:
    r = 3958.8
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _venue_metro(arena: str, city: str, state: str, home_ta: str) -> tuple[float, float, int]:
    key = (arena, city, state)
    if key in EXTRA_VENUE_METRO:
        return EXTRA_VENUE_METRO[key]
    # Default: home team's metro (covers standard arenas without team-if in compose).
    if home_ta in TEAM_METRO:
        return TEAM_METRO[home_ta]
    return TEAM_METRO["NYK"]


def _parse_games(raw: dict) -> list[dict]:
    games: list[dict] = []
    for month in raw.get("lscd") or []:
        for g in (month.get("mscd") or {}).get("g") or []:
            gid = str(g.get("gid") or "")
            if not gid.startswith("002"):
                continue
            games.append(
                {
                    "game_id": gid,
                    "date": g["gdte"],
                    "home": g["h"]["ta"],
                    "away": g["v"]["ta"],
                    "arena": g.get("an") or "",
                    "city": g.get("ac") or "",
                    "state": g.get("as") or "",
                    "status": g.get("stt") or "",
                }
            )
    games.sort(key=lambda r: (r["date"], r["game_id"]))
    return games


def _build_team_timeline(games: list[dict]) -> dict[str, list[dict]]:
    by: dict[str, list[dict]] = defaultdict(list)
    for g in games:
        for side, team in (("home", g["home"]), ("away", g["away"])):
            lat, lon, tz = _venue_metro(g["arena"], g["city"], g["state"], g["home"])
            by[team].append(
                {
                    "game_id": g["game_id"],
                    "date": g["date"],
                    "side": side,
                    "opponent": g["away"] if side == "home" else g["home"],
                    "arena": g["arena"],
                    "city": g["city"],
                    "state": g["state"],
                    "lat": lat,
                    "lon": lon,
                    "tz": tz,
                }
            )
    for team in by:
        by[team].sort(key=lambda r: (r["date"], r["game_id"]))
    return by


def _annotate_flags(
    timeline: dict[str, list[dict]], altitude_venues: set[tuple[str, str, str]]
) -> list[dict]:
    rows: list[dict] = []
    for team, games in timeline.items():
        dates = [datetime.strptime(g["date"], "%Y-%m-%d").date() for g in games]
        for i, g in enumerate(games):
            d = dates[i]
            rest_days = None if i == 0 else (d - dates[i - 1]).days
            window = [x for x in dates[: i + 1] if (d - x).days <= 3]
            three_in_four = len(window) >= 3
            b2b = bool(rest_days == 1 or three_in_four)

            travel = False
            travel_miles = 0.0
            travel_tz = 0
            if i > 0:
                prev = games[i - 1]
                travel_miles = _haversine_miles((prev["lat"], prev["lon"]), (g["lat"], g["lon"]))
                travel_tz = abs(int(g["tz"]) - int(prev["tz"]))
                travel = travel_miles >= TRAVEL_MILES_MIN or travel_tz >= TRAVEL_TZ_MIN

            venue_key = (g["arena"], g["city"], g["state"])
            altitude = venue_key in altitude_venues
            home = g["side"] == "home" and not (
                # Neutral: home team not playing in its usual metro state mismatch is rare;
                # international extras are still "home" for the designated home ta in CDN.
                False
            )

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
                    "arena": g["arena"],
                    "city": g["city"],
                    "state": g["state"],
                }
            )
    return rows


def _delta(flags: dict, coeffs: dict[str, float]) -> tuple[float, float, dict[str, float]]:
    parts = {
        "home": coeffs["home"] if flags["home"] else 0.0,
        "b2b": coeffs["b2b"] if flags["b2b"] else 0.0,
        "travel": coeffs["travel"] if flags["travel"] else 0.0,
        "altitude": 0.0,
    }
    if flags["altitude"]:
        # One altitude coefficient; sign by side at the venue (not if team ==).
        parts["altitude"] = coeffs["altitude"] if flags["home"] else -coeffs["altitude"]
    raw = sum(parts.values())
    clipped = max(-SITUATION_TEAM_PTS_CAP, min(SITUATION_TEAM_PTS_CAP, raw))
    return raw, clipped, parts


def _paper_sim(flag_rows: list[dict]) -> tuple[dict[str, float], dict[str, Any]]:
    results = []
    for home, b2b, travel, alt in product(PAPER_HOME, PAPER_B2B, PAPER_TRAVEL, PAPER_ALTITUDE):
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
        # Prefer mid-magnitude home/b2b, low clip rate, modest mean |Δ|.
        score = (
            clip_rate * 100.0
            + abs(abs(home) - 2.0) * 0.5
            + abs(abs(b2b) - 1.5) * 0.5
            + abs(abs(travel) - 1.0) * 0.25
            + abs(abs(alt) - 1.0) * 0.25
            + mean_abs * 0.1
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
        "as_of": "2026-09-01",
        "season_schedule": "2025-26",
        "n_team_games": len(flag_rows),
        "SITUATION_TEAM_PTS_CAP": SITUATION_TEAM_PTS_CAP,
        "grids": {
            "home": list(PAPER_HOME),
            "b2b": list(PAPER_B2B),
            "travel": list(PAPER_TRAVEL),
            "altitude": list(PAPER_ALTITUDE),
        },
        "travel_thresholds": {"miles": TRAVEL_MILES_MIN, "tz": TRAVEL_TZ_MIN},
        "chosen": chosen,
        "top5": results[:5],
        "prevalence": {
            "home": sum(1 for r in flag_rows if r["home"]) / len(flag_rows),
            "b2b": sum(1 for r in flag_rows if r["b2b"]) / len(flag_rows),
            "travel": sum(1 for r in flag_rows if r["travel"]) / len(flag_rows),
            "altitude": sum(1 for r in flag_rows if r["altitude"]) / len(flag_rows),
            "three_in_four": sum(1 for r in flag_rows if r["three_in_four"]) / len(flag_rows),
        },
    }


def main() -> None:
    if not SCHED_SRC.is_file():
        raise SystemExit(f"missing schedule source {SCHED_SRC}")
    raw = json.loads(SCHED_SRC.read_text(encoding="utf-8"))
    games = _parse_games(raw)

    venue_flags = {
        "engine_version": ENGINE_VERSION,
        "as_of": "2026-09-01",
        "note": "Altitude is a venue flag (arena/city/state), not if team ==.",
        "altitude_venues": [
            {"arena": "Ball Arena", "city": "Denver", "state": "CO"},
            {"arena": "Delta Center", "city": "Salt Lake City", "state": "UT"},
        ],
    }
    alt_set = {(v["arena"], v["city"], v["state"]) for v in venue_flags["altitude_venues"]}

    timeline = _build_team_timeline(games)
    flag_rows = _annotate_flags(timeline, alt_set)
    chosen, paper = _paper_sim(flag_rows)

    # League-sane check: apply clipped Δ to Ch2 implied_ppg sample → stay in 100–130.
    rebased = json.loads((DATA / "nba_team_prior_rebased_2026_27.json").read_text(encoding="utf-8"))
    ppg_adj = []
    for fr in flag_rows:
        base = float(rebased["teams"][fr["team"]]["implied_ppg"])
        _, clipped, _ = _delta(fr, chosen)
        ppg_adj.append(base + clipped)
    paper["ppg_adj_range"] = [round(min(ppg_adj), 2), round(max(ppg_adj), 2)]
    paper["ortg_drtg_note"] = (
        "Situation Δ is team points on the Ch2 implied_ppg line; "
        "ORtg/DRtg remain Ch2 rebased; Δ does not invent a second net prior."
    )

    sched_out = {
        "engine_version": ENGINE_VERSION,
        "as_of": "2026-09-01",
        "season": "2025-26",
        "source": "data.nba.com 00_full_schedule (normalized)",
        "game_count": len(games),
        "team_game_count": len(flag_rows),
        "date_range": [games[0]["date"], games[-1]["date"]],
        "games": games,
        "team_games": flag_rows,
    }

    coeffs_out = {
        "engine_version": ENGINE_VERSION,
        "as_of": "2026-09-01",
        "chapter": 3,
        "SITUATION_TEAM_PTS_CAP": SITUATION_TEAM_PTS_CAP,
        "TEAM_CARRY_SHRINK_unchanged": 0.85,
        "TEAM_REBASE_RESIDUAL_CAP": 3.0,
        "coefficients": chosen,
        "units": "team_points_on_implied_ppg",
        "classes": {
            "home": "designated home side",
            "b2b": "rest_days==1 OR 3 games in 4 calendar days",
            "travel": f"prior venue ≥{TRAVEL_MILES_MIN:.0f} mi OR |Δtz|≥{TRAVEL_TZ_MIN}",
            "altitude": "venue in nba_venue_flags altitude list; +coeff home / −coeff visitor",
        },
        "formula": "Δ_raw = Σ class_coeff; Δ = clip(Δ_raw, ±SITUATION_TEAM_PTS_CAP)",
        "apply": "on_read_team_line; PlayerProjection PTS copy-through only when Δ≠0",
        "does_not": [
            "team if",
            "new player means",
            "new minute grid",
            "Edge PLAY",
            "props tab",
            "CFB/NFL",
            "change TEAM_CARRY_SHRINK",
        ],
        "paper_sim": str(PAPER_OUT.name),
    }

    DATA.mkdir(parents=True, exist_ok=True)
    VENUE_OUT.write_text(json.dumps(venue_flags, indent=2) + "\n", encoding="utf-8")
    SCHED_OUT.write_text(json.dumps(sched_out, indent=2) + "\n", encoding="utf-8")
    PAPER_OUT.write_text(json.dumps(paper, indent=2) + "\n", encoding="utf-8")
    COEFF_OUT.write_text(json.dumps(coeffs_out, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote schedule={len(games)} team_games={len(flag_rows)} "
        f"coeffs={chosen} ppg_adj={paper['ppg_adj_range']}"
    )


if __name__ == "__main__":
    main()
