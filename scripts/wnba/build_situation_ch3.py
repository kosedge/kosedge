#!/usr/bin/env python3
"""Build WNBA Chapter 3 situation packs: schedule + venue flags + paper-sim coeffs.

Classes (one coefficient each): home, B2B (rest=1 or 3-in-4), travel, altitude venue.
Cap so situation ≠ second prior. Does not rewrite Ch2 grids or Ch5 means on disk.
Does not copy NBA home=+2.0 / b2b=−1.5 — paper-sim on WNBA points.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import datetime
from itertools import product
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "services/model-service/src/services/wnba_season_engine/data"
# 2026 CDN 403 in build env — paper-sim uses completed 2025 RS schedule.
SCHED_SRC = Path("/tmp/wnba_sched2025.json")
SCHED_OUT = DATA / "wnba_schedule_2025.json"
VENUE_OUT = DATA / "wnba_venue_flags.json"
COEFF_OUT = DATA / "wnba_situation_coeffs_v0.json"
PAPER_OUT = DATA / "wnba_situation_paper_sim_ch3.json"
REBASED_PATH = DATA / "wnba_team_prior_rebased_2026.json"

ENGINE_VERSION = "wnba-season-engine-v0.1"
SITUATION_TEAM_PTS_CAP = 3.0
TRAVEL_MILES_MIN = 1000.0
TRAVEL_TZ_MIN = 2

# CDN → desk keys (Ch1/Ch2 canonical).
CDN_TO_CANON = {
    "ATL": "ATL",
    "CHI": "CHI",
    "CON": "CON",
    "DAL": "DAL",
    "GSV": "GSV",
    "IND": "IND",
    "LVA": "LAS",  # Aces
    "LAS": "LA",  # Sparks on data.wnba.com
    "MIN": "MIN",
    "NYL": "NY",
    "PHX": "PHX",
    "POR": "POR",
    "SEA": "SEA",
    "TOR": "TOR",
    "WAS": "WSH",
}
TEAM_CODES = set(CDN_TO_CANON.values())

# Home metro lat/lon/tz_offset_hours (standard time; DST ignored at class grain).
TEAM_METRO: dict[str, tuple[float, float, int]] = {
    "ATL": (33.6500, -84.4500, -5),  # College Park / Gateway
    "CHI": (41.8530, -87.6210, -6),
    "CON": (41.4830, -72.0920, -5),
    "DAL": (32.7300, -97.1100, -6),
    "GSV": (37.7680, -122.3877, -8),
    "IND": (39.7640, -86.1555, -5),
    "LAS": (36.0900, -115.1800, -8),
    "LA": (34.0430, -118.2673, -8),
    "MIN": (44.9795, -93.2760, -6),
    "NY": (40.6826, -73.9754, -5),
    "PHX": (33.4457, -112.0712, -7),
    "POR": (45.5316, -122.6668, -8),
    "SEA": (47.6220, -122.3540, -8),
    "TOR": (43.6435, -79.3791, -5),
    "WSH": (38.8981, -77.0209, -5),
}

# WNBA-point paper-sim grids — not imported from nba_situation_coeffs_v0.
# Includes 2.25 near Ch0 poss-sim HCA research; score does not prefer NBA mids.
PAPER_HOME = (1.5, 2.0, 2.25, 2.5)
PAPER_B2B = (-1.0, -1.25, -1.5, -2.0)
PAPER_TRAVEL = (-0.5, -0.75, -1.0, -1.25)
PAPER_ALTITUDE = (0.5, 0.75, 1.0)

PPG_BAND_AFTER = (72.0, 94.0)


def _haversine_miles(a: tuple[float, float], b: tuple[float, float]) -> float:
    r = 3958.8
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(h))


def _canon(raw: str) -> str | None:
    t = (raw or "").strip().upper()
    return CDN_TO_CANON.get(t)


def _venue_metro(
    arena: str, city: str, state: str, home_ta: str
) -> tuple[float, float, int]:
    # Default: designated home team's metro (no team-if in altitude compose).
    if home_ta in TEAM_METRO:
        return TEAM_METRO[home_ta]
    return TEAM_METRO["NY"]


def _parse_games(raw: dict) -> list[dict]:
    games: list[dict] = []
    for month in raw.get("lscd") or []:
        for g in (month.get("mscd") or {}).get("g") or []:
            gid = str(g.get("gid") or "")
            # Regular season on data.wnba.com (preseason 101*, cup/other skipped).
            if not gid.startswith("102"):
                continue
            home = _canon((g.get("h") or {}).get("ta") or "")
            away = _canon((g.get("v") or {}).get("ta") or "")
            if not home or not away:
                continue
            if home not in TEAM_CODES or away not in TEAM_CODES:
                continue
            games.append(
                {
                    "game_id": gid,
                    "date": str(g.get("gdte") or "")[:10],
                    "home": home,
                    "away": away,
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
                travel_miles = _haversine_miles(
                    (prev["lat"], prev["lon"]), (g["lat"], g["lon"])
                )
                travel_tz = abs(int(g["tz"]) - int(prev["tz"]))
                travel = (
                    travel_miles >= TRAVEL_MILES_MIN or travel_tz >= TRAVEL_TZ_MIN
                )

            venue_key = (g["arena"], g["city"], g["state"])
            altitude = venue_key in altitude_venues
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
                    "arena": g["arena"],
                    "city": g["city"],
                    "state": g["state"],
                }
            )
    return rows


def _delta(
    flags: dict, coeffs: dict[str, float]
) -> tuple[float, float, dict[str, float]]:
    parts = {
        "home": coeffs["home"] if flags["home"] else 0.0,
        "b2b": coeffs["b2b"] if flags["b2b"] else 0.0,
        "travel": coeffs["travel"] if flags["travel"] else 0.0,
        "altitude": 0.0,
    }
    if flags["altitude"]:
        # One altitude coefficient; sign by side at the venue (not if team ==).
        parts["altitude"] = (
            coeffs["altitude"] if flags["home"] else -coeffs["altitude"]
        )
    raw = sum(parts.values())
    clipped = max(-SITUATION_TEAM_PTS_CAP, min(SITUATION_TEAM_PTS_CAP, raw))
    return raw, clipped, parts


def _paper_sim(flag_rows: list[dict]) -> tuple[dict[str, float], dict[str, Any]]:
    """WNBA-point search — score by clip + |Δ| only (no NBA mid-magnitude anchors)."""
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
        max_abs = max(abs(x) for x in raws)
        # Prefer low clip, modest mean |Δ|, and not routinely hitting the cap.
        score = (
            clip_rate * 100.0
            + mean_abs * 0.25
            + max(0.0, max_abs - SITUATION_TEAM_PTS_CAP) * 5.0
            + abs(mean_signed) * 0.05
        )
        results.append(
            {
                "coeffs": coeffs,
                "clip_rate": round(clip_rate, 6),
                "mean_abs_raw": round(mean_abs, 4),
                "mean_signed_raw": round(mean_signed, 4),
                "max_abs_raw": round(max_abs, 4),
                "score": round(score, 6),
            }
        )
    results.sort(key=lambda r: r["score"])
    chosen = results[0]["coeffs"]
    return chosen, {
        "engine_version": ENGINE_VERSION,
        "as_of": "2026-09-01",
        "season_schedule": "2025",
        "schedule_note": (
            "Paper-sim on 2025 RS (gid 102*). 2026 CDN schedule 403 in build env; "
            "coeffs are WNBA-point, not copied from nba_situation_coeffs_v0."
        ),
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
            "three_in_four": sum(1 for r in flag_rows if r["three_in_four"])
            / len(flag_rows),
        },
    }


def main() -> None:
    if not SCHED_SRC.is_file():
        raise SystemExit(f"missing schedule source {SCHED_SRC}")
    raw = json.loads(SCHED_SRC.read_text(encoding="utf-8"))
    games = _parse_games(raw)
    if len(games) < 100:
        raise SystemExit(f"expected ≥100 RS games, got {len(games)}")

    # No WNBA home arenas at NBA-class altitude (DEN/UTA). Keep the class;
    # venue list empty ⇒ altitude never fires until a flagged venue is added.
    venue_flags = {
        "engine_version": ENGINE_VERSION,
        "as_of": "2026-09-01",
        "note": (
            "Altitude is a venue flag (arena/city/state), not if team ==. "
            "No WNBA regular home arenas registered at altitude for v0."
        ),
        "altitude_venues": [],
    }
    alt_set = {
        (v["arena"], v["city"], v["state"]) for v in venue_flags["altitude_venues"]
    }

    timeline = _build_team_timeline(games)
    flag_rows = _annotate_flags(timeline, alt_set)
    chosen, paper = _paper_sim(flag_rows)

    rebased = json.loads(REBASED_PATH.read_text(encoding="utf-8"))
    ppg_adj = []
    for fr in flag_rows:
        team = fr["team"]
        if team not in rebased["teams"]:
            continue
        base = float(rebased["teams"][team]["implied_ppg"])
        _, clipped, _ = _delta(fr, chosen)
        ppg_adj.append(base + clipped)
    if not ppg_adj:
        raise SystemExit("no PPG′ sample — rebased teams missing from schedule")
    paper["ppg_adj_range"] = [round(min(ppg_adj), 2), round(max(ppg_adj), 2)]
    paper["ortg_drtg_note"] = (
        "Situation Δ is team points on the Ch2 implied_ppg line; "
        "ORtg/DRtg remain Ch2 rebased; Δ does not invent a second net prior."
    )
    low, high = PPG_BAND_AFTER
    if paper["ppg_adj_range"][0] < low or paper["ppg_adj_range"][1] > high:
        raise SystemExit(
            f"PPG′ after Δ out of band {PPG_BAND_AFTER}: {paper['ppg_adj_range']}"
        )

    sched_out = {
        "engine_version": ENGINE_VERSION,
        "as_of": "2026-09-01",
        "season": "2025",
        "source": "data.wnba.com 10_full_schedule (normalized, gid 102* RS)",
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
        "WNBA_TEAM_CARRY_SHRINK_unchanged": 0.85,
        "WNBA_TEAM_REBASE_RESIDUAL_CAP": 3.0,
        "MINUTE_GRID_SUM_unchanged": 200,
        "coefficients": chosen,
        "units": "team_points_on_implied_ppg",
        "classes": {
            "home": "designated home side",
            "b2b": "rest_days==1 OR 3 games in 4 calendar days",
            "travel": (
                f"prior venue ≥{TRAVEL_MILES_MIN:.0f} mi OR |Δtz|≥{TRAVEL_TZ_MIN}"
            ),
            "altitude": (
                "venue in wnba_venue_flags altitude list; +coeff home / −coeff visitor"
            ),
        },
        "formula": "Δ_raw = Σ class_coeff; Δ = clip(Δ_raw, ±SITUATION_TEAM_PTS_CAP)",
        "apply": "on_read_team_line; PlayerProjection PTS copy-through only when Δ≠0",
        "does_not": [
            "team if",
            "new player means",
            "new minute grid",
            "Ch4 KEI emit",
            "props PLAY",
            "copy NBA home=+2.0 / b2b=−1.5",
            "change WNBA_TEAM_CARRY_SHRINK",
            "NBA/CFB/NFL packs",
        ],
        "forbidden_leftover_fair_line_game_ids": ["401857105", "401857106"],
        "paper_sim": str(PAPER_OUT.name),
    }

    DATA.mkdir(parents=True, exist_ok=True)
    VENUE_OUT.write_text(json.dumps(venue_flags, indent=2) + "\n", encoding="utf-8")
    SCHED_OUT.write_text(json.dumps(sched_out, indent=2) + "\n", encoding="utf-8")
    PAPER_OUT.write_text(json.dumps(paper, indent=2) + "\n", encoding="utf-8")
    COEFF_OUT.write_text(json.dumps(coeffs_out, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote schedule={len(games)} team_games={len(flag_rows)} "
        f"coeffs={chosen} ppg_adj={paper['ppg_adj_range']} "
        f"clip_rate={paper['top5'][0]['clip_rate']}"
    )


if __name__ == "__main__":
    main()
