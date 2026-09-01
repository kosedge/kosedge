#!/usr/bin/env python3
"""Rebuild NBA Ch3 situation packs (venues + schedule SoT) with paper-sim.

Schedule SoT: data.nba.com 2025 league RS (gid 002*). 2026-27 CDN was 403 in
the build env — swap the fetch URL when published. Venue altitude_class is a
venue flag (Ball Arena / Delta Center), never a team-if.

Usage:
  python scripts/nba/build_situation_ch3.py
"""

from __future__ import annotations

import json
import math
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "services/model-service/src/services/nba_season_engine/data"
REBASED_PATH = DATA / "nba_team_prior_rebased_2026_27.json"
VENUES_OUT = DATA / "nba_venues_2026.json"
SIT_OUT = DATA / "nba_situation_2026.json"

TRAVEL_TZ_BAND_MIN = 2
HOME_SET = [1.5, 2.0, 2.5, 3.0]
B2B_SET = [-1.0, -1.5, -2.0]
TRAVEL_SET = [-0.5, -1.0, -1.5]
ALT_SET = [-0.5, -1.0, -1.5]
CAP_SET = [3.0, 4.0, 5.0]

VENUES = {
    "ATL": {"name": "State Farm Arena", "tz_utc_offset_hours": -5, "altitude_class": False},
    "BOS": {"name": "TD Garden", "tz_utc_offset_hours": -5, "altitude_class": False},
    "BKN": {"name": "Barclays Center", "tz_utc_offset_hours": -5, "altitude_class": False},
    "CHA": {"name": "Spectrum Center", "tz_utc_offset_hours": -5, "altitude_class": False},
    "CHI": {"name": "United Center", "tz_utc_offset_hours": -6, "altitude_class": False},
    "CLE": {"name": "Rocket Mortgage FieldHouse", "tz_utc_offset_hours": -5, "altitude_class": False},
    "DAL": {"name": "American Airlines Center", "tz_utc_offset_hours": -6, "altitude_class": False},
    "DEN": {"name": "Ball Arena", "tz_utc_offset_hours": -7, "altitude_class": True},
    "DET": {"name": "Little Caesars Arena", "tz_utc_offset_hours": -5, "altitude_class": False},
    "GSW": {"name": "Chase Center", "tz_utc_offset_hours": -8, "altitude_class": False},
    "HOU": {"name": "Toyota Center", "tz_utc_offset_hours": -6, "altitude_class": False},
    "IND": {"name": "Gainbridge Fieldhouse", "tz_utc_offset_hours": -5, "altitude_class": False},
    "LAC": {"name": "Crypto.com Arena", "tz_utc_offset_hours": -8, "altitude_class": False},
    "LAL": {"name": "Crypto.com Arena", "tz_utc_offset_hours": -8, "altitude_class": False},
    "MEM": {"name": "FedExForum", "tz_utc_offset_hours": -6, "altitude_class": False},
    "MIA": {"name": "Kaseya Center", "tz_utc_offset_hours": -5, "altitude_class": False},
    "MIL": {"name": "Fiserv Forum", "tz_utc_offset_hours": -6, "altitude_class": False},
    "MIN": {"name": "Target Center", "tz_utc_offset_hours": -6, "altitude_class": False},
    "NOP": {"name": "Smoothie King Center", "tz_utc_offset_hours": -6, "altitude_class": False},
    "NYK": {"name": "Madison Square Garden", "tz_utc_offset_hours": -5, "altitude_class": False},
    "OKC": {"name": "Paycom Center", "tz_utc_offset_hours": -6, "altitude_class": False},
    "ORL": {"name": "Kia Center", "tz_utc_offset_hours": -5, "altitude_class": False},
    "PHI": {"name": "Wells Fargo Center", "tz_utc_offset_hours": -5, "altitude_class": False},
    "PHX": {"name": "Footprint Center", "tz_utc_offset_hours": -7, "altitude_class": False},
    "POR": {"name": "Moda Center", "tz_utc_offset_hours": -8, "altitude_class": False},
    "SAC": {"name": "Golden 1 Center", "tz_utc_offset_hours": -8, "altitude_class": False},
    "SAS": {"name": "Frost Bank Center", "tz_utc_offset_hours": -6, "altitude_class": False},
    "TOR": {"name": "Scotiabank Arena", "tz_utc_offset_hours": -5, "altitude_class": False},
    "UTA": {"name": "Delta Center", "tz_utc_offset_hours": -7, "altitude_class": True},
    "WAS": {"name": "Capital One Arena", "tz_utc_offset_hours": -5, "altitude_class": False},
}

ALIAS = {"BRK": "BKN", "PHO": "PHX", "CHO": "CHA", "NOH": "NOP"}


def norm(t: str) -> str:
    t = str(t or "").upper()
    return ALIAS.get(t, t)


def apply_delta(net, home, rest, travel, alt, coefs, cap):
    parts = []
    if home:
        parts.append(coefs["home"])
    if rest:
        parts.append(coefs["b2b"])
    if travel:
        parts.append(coefs["travel"])
    if alt:
        parts.append(coefs["altitude"])
    raw = sum(parts)
    if abs(raw) > cap:
        raw = math.copysign(cap, raw)
    return net + raw, raw


def main() -> None:
    rebased = json.loads(REBASED_PATH.read_text(encoding="utf-8"))
    assert len(rebased.get("teams") or {}) == 30

    ua = {"User-Agent": "Mozilla/5.0 (compatible; KosEdgeNbaCh3/1.0)"}
    url = (
        "https://data.nba.com/data/10s/v2015/json/mobile_teams/nba/2025/"
        "league/00_full_schedule.json"
    )
    req = urllib.request.Request(url, headers=ua)
    with urllib.request.urlopen(req, timeout=90) as resp:
        raw = json.loads(resp.read().decode())

    games = []
    for m in raw.get("lscd") or []:
        for g in (m.get("mscd") or {}).get("g") or []:
            gid = str(g.get("gid") or "")
            if not gid.startswith("002"):
                continue
            home = norm((g.get("h") or {}).get("ta"))
            away = norm((g.get("v") or {}).get("ta"))
            gdte = str(g.get("gdte") or "")[:10]
            if home not in VENUES or away not in VENUES or not gdte:
                continue
            games.append(
                {
                    "game_id": gid,
                    "date": gdte,
                    "home": home,
                    "away": away,
                    "venue_team": home,
                }
            )
    games.sort(key=lambda x: (x["date"], x["game_id"]))

    last_date: dict[str, date] = {}
    last_venue: dict[str, str] = {}
    annotated = []
    for g in games:
        d = date.fromisoformat(g["date"])
        row = dict(g)
        for side, team in (("home", g["home"]), ("away", g["away"])):
            prev_d = last_date.get(team)
            prev_v = last_venue.get(team)
            rest_days = None if prev_d is None else (d - prev_d).days
            b2b = rest_days == 1 if rest_days is not None else False
            tz_here = VENUES[g["venue_team"]]["tz_utc_offset_hours"]
            tz_prev = VENUES[prev_v]["tz_utc_offset_hours"] if prev_v else tz_here
            tz_delta = abs(tz_here - tz_prev) if prev_v else 0
            travel = tz_delta >= TRAVEL_TZ_BAND_MIN
            altitude_venue = bool(VENUES[g["venue_team"]]["altitude_class"])
            altitude_visitor = altitude_venue and side == "away"
            row[f"{side}_rest_days"] = rest_days
            row[f"{side}_b2b"] = b2b
            row[f"{side}_tz_delta"] = tz_delta
            row[f"{side}_travel"] = travel
            row[f"{side}_altitude_visitor"] = altitude_visitor
            last_date[team] = d
            last_venue[team] = g["venue_team"]
        annotated.append(row)

    history: dict[str, list[date]] = defaultdict(list)
    for row in annotated:
        d = date.fromisoformat(row["date"])
        for side, team in (("home", row["home"]), ("away", row["away"])):
            recent = [x for x in history[team] if 0 < (d - x).days <= 3]
            row[f"{side}_three_in_four"] = len(recent) >= 2
            row[f"{side}_rest_class"] = bool(
                row[f"{side}_b2b"] or row[f"{side}_three_in_four"]
            )
            history[team].append(d)

    n_side = len(annotated) * 2

    def rate(key: str) -> float:
        return (
            sum(
                1
                for r in annotated
                for side in ("home", "away")
                if r[f"{side}_{key}"]
            )
            / n_side
        )

    rates = {
        "home_share": 0.5,
        "b2b_rate": rate("b2b"),
        "three_in_four_rate": rate("three_in_four"),
        "rest_class_rate": rate("rest_class"),
        "travel_rate": rate("travel"),
        "altitude_visitor_rate": rate("altitude_visitor"),
    }

    candidates = []
    for h in HOME_SET:
        for b in B2B_SET:
            for tr in TRAVEL_SET:
                for a in ALT_SET:
                    for cap in CAP_SET:
                        coefs = {
                            "home": h,
                            "b2b": b,
                            "travel": tr,
                            "altitude": a,
                        }
                        deltas = []
                        for r in annotated:
                            for side, team, is_home in (
                                ("home", r["home"], True),
                                ("away", r["away"], False),
                            ):
                                net0 = float(
                                    rebased["teams"][team]["net_rating"]
                                )
                                _, raw = apply_delta(
                                    net0,
                                    is_home,
                                    r[f"{side}_rest_class"],
                                    r[f"{side}_travel"],
                                    r[f"{side}_altitude_visitor"],
                                    coefs,
                                    cap,
                                )
                                deltas.append(raw)
                        mean_delta = mean(deltas)
                        mean_abs = mean(abs(x) for x in deltas)
                        score = (
                            abs(mean_delta) * 3.0
                            + abs(mean_abs - 1.6)
                            + abs(h - 2.0) * 0.25
                            + abs(cap - 4.0) * 0.1
                        )
                        candidates.append(
                            (score, coefs, cap, mean_delta, mean_abs)
                        )

    candidates.sort(key=lambda x: x[0])
    best = candidates[0]
    coefs, cap = best[1], best[2]

    paper_table = []
    for name, coef, share in (
        ("home", coefs["home"], rates["home_share"]),
        ("b2b_rest_class", coefs["b2b"], rates["rest_class_rate"]),
        ("travel", coefs["travel"], rates["travel_rate"]),
        ("altitude_visitor", coefs["altitude"], rates["altitude_visitor_rate"]),
    ):
        paper_table.append(
            {
                "class": name,
                "coefficient_net": coef,
                "observed_rate": round(share, 4),
                "share_weighted_net": round(coef * share, 4),
            }
        )

    examples = []
    for label, flags in (
        ("neutral_baseline", {"home": False, "rest": False, "travel": False, "alt": False}),
        ("home_only", {"home": True, "rest": False, "travel": False, "alt": False}),
        ("away_b2b", {"home": False, "rest": True, "travel": False, "alt": False}),
        ("away_travel", {"home": False, "rest": False, "travel": True, "alt": False}),
        ("away_altitude", {"home": False, "rest": False, "travel": False, "alt": True}),
        ("away_b2b_travel_alt", {"home": False, "rest": True, "travel": True, "alt": True}),
    ):
        nets = []
        for team, t in rebased["teams"].items():
            n1, _ = apply_delta(
                float(t["net_rating"]),
                flags["home"],
                flags["rest"],
                flags["travel"],
                flags["alt"],
                coefs,
                cap,
            )
            nets.append(n1)
        examples.append(
            {
                "scenario": label,
                "mean_net": round(mean(nets), 4),
                "min_net": round(min(nets), 4),
                "max_net": round(max(nets), 4),
                "flags": flags,
            }
        )

    base_nets = [float(t["net_rating"]) for t in rebased["teams"].values()]
    base_ortg = [float(t["ortg"]) for t in rebased["teams"].values()]
    base_drtg = [float(t["drtg"]) for t in rebased["teams"].values()]
    base_ppg = [float(t["implied_ppg"]) for t in rebased["teams"].values()]

    venues_pack = {
        "engine_version": "nba-season-engine-v0.1",
        "as_of": "2026-09-01",
        "note": (
            "Venue class pack for Ch3 situation. altitude_class is a venue "
            "flag (Ball Arena / Delta Center), not a team-if."
        ),
        "travel_tz_band_min_hours": TRAVEL_TZ_BAND_MIN,
        "venues": {k: {**v, "venue_team": k} for k, v in VENUES.items()},
    }

    schedule_rows = []
    for r in annotated:
        schedule_rows.append(
            {
                "game_id": r["game_id"],
                "date": r["date"],
                "home": r["home"],
                "away": r["away"],
                "venue_team": r["venue_team"],
                "home_b2b": r["home_b2b"],
                "away_b2b": r["away_b2b"],
                "home_three_in_four": r["home_three_in_four"],
                "away_three_in_four": r["away_three_in_four"],
                "home_rest_class": r["home_rest_class"],
                "away_rest_class": r["away_rest_class"],
                "home_tz_delta": r["home_tz_delta"],
                "away_tz_delta": r["away_tz_delta"],
                "home_travel": r["home_travel"],
                "away_travel": r["away_travel"],
                "home_altitude_visitor": r["home_altitude_visitor"],
                "away_altitude_visitor": r["away_altitude_visitor"],
            }
        )

    situation_pack = {
        "engine_version": "nba-season-engine-v0.1",
        "as_of": "2026-09-01",
        "schedule_source": (
            "data.nba.com 2025 league 00_full_schedule (RS gid 002*) — "
            "2026-27 CDN unpublished in build env; swap when published"
        ),
        "schedule_season_label": "2025-26_RS_reference",
        "n_games": len(schedule_rows),
        "TEAM_CARRY_SHRINK_unchanged": 0.85,
        "TEAM_REBASE_RESIDUAL_CAP_unchanged": 3.0,
        "travel_tz_band_min_hours": TRAVEL_TZ_BAND_MIN,
        "coefficients": {
            "SITUATION_HOME_NET": coefs["home"],
            "SITUATION_B2B_NET": coefs["b2b"],
            "SITUATION_TRAVEL_NET": coefs["travel"],
            "SITUATION_ALTITUDE_NET": coefs["altitude"],
            "SITUATION_NET_CAP": cap,
        },
        "paper_sim": {
            "home_set": HOME_SET,
            "b2b_set": B2B_SET,
            "travel_set": TRAVEL_SET,
            "altitude_set": ALT_SET,
            "cap_set": CAP_SET,
            "chosen_score": round(best[0], 6),
            "mean_delta_net": round(best[3], 6),
            "mean_abs_delta_net": round(best[4], 6),
            "class_table": paper_table,
            "scenario_board": examples,
            "rates": {k: round(v, 6) for k, v in rates.items()},
            "baseline_league_mean_net": round(mean(base_nets), 4),
            "baseline_league_mean_ortg": round(mean(base_ortg), 4),
            "baseline_league_mean_drtg": round(mean(base_drtg), 4),
            "baseline_implied_ppg_range": [
                round(min(base_ppg), 2),
                round(max(base_ppg), 2),
            ],
        },
        "does_not": [
            "emit KEI or Edge stake tags",
            "props / fantasy",
            "rewrite minutes grid",
            "change TEAM_CARRY_SHRINK",
            "team-name branches",
            "new player means",
        ],
        "games": schedule_rows,
    }

    VENUES_OUT.write_text(json.dumps(venues_pack, indent=2) + "\n", encoding="utf-8")
    SIT_OUT.write_text(json.dumps(situation_pack, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {VENUES_OUT.name} + {SIT_OUT.name} "
        f"n_games={len(schedule_rows)} coefs={coefs} cap={cap}"
    )


if __name__ == "__main__":
    main()
