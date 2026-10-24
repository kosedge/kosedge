#!/usr/bin/env python3
"""injury-residual-cal-v2 fit — ≤2023 REG only.

Run at HEAD 8e2a15ac. No git writes. All NFL_TOTALS_* must be unset.
Does not read 2024/2025/2026 listing, roster, or outcome rows.
E-1: every ledger row tags continuity_source; None continuity is UNKNOWN,
never numeric 0 / neutral.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

REQUIRED_HEAD = "8e2a15ac581277ecda71ea745c3b3477185d733b"
HOLDOUT_YEARS = {2024, 2025, 2026}
FIT_YEARS = list(range(2013, 2024))
RAW = Path("/tmp/injury-fit-raw-le2023")
OOS = Path(
    "/workspace/data/ops/nfl-reopening-packet-20260916/historical-oos/historical_oos_games.csv"
)

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
sys.path.insert(0, "/workspace/services/model-service")

from src.services.nfl_injury_null_contract import (
    APPLICATION_SITE,
    FIT_PROTOCOL_ID,
    FLAG_INJURY_PARTIAL_DEF,
    FLAG_INJURY_PARTIAL_OFF,
    FLAG_INJURY_PARTIAL_OL,
    FLAG_MISSING_KOSEDGE_INJURY_NOWCAST,
    IDENTITY_RULE_SEASON_FALLBACK,
    IDENTITY_RULE_TEAM_MATCH,
    IDENTITY_RULE_UNRESOLVED,
    LEDGER_VERSION,
    FitRowFailure,
    bound_hash,
    config_hash,
    count_identity_resolutions,
    parse_fit_kickoff_utc,
    parse_fit_report_time_utc,
    resolve_fit_player_identity,
    resolve_nfl_totals_env,
    write_sealed_injury_export,
)
from src.services.nfl_season_engine.injury_paths import (
    QB1_FLOOR_SPREAD_POINTS,
    QB1_INDEX_UNITS,
    QB1_POINTS_PER_INDEX_UNIT,
)

THETA_GRID = (0.40, 0.60, 0.80)
CAP_SPREAD_GRID = (2.0, 2.6, 3.2)
CAP_TOTAL_GRID = (2.0, 2.8, 3.4)
DOUBTFUL_GRID = (0.15, 0.25, 0.35)
QUESTIONABLE_GRID = (0.40, 0.50, 0.60)
LIMITED_GRID = (0.75, 0.85, 0.95)
SPEC_A = {
    "spec": "A",
    "theta": 0.60,
    "doubtful": 0.25,
    "questionable": 0.50,
    "limited": 0.85,
    "cap_spread": None,
    "cap_total": None,
}
OUT_STATUSES = frozenset(
    {"out", "ir", "injured reserve", "pup", "suspended", "inactive", "physically unable to perform"}
)
STARTER_SLOTS = frozenset(
    {
        "QB",
        "RB",
        "WR",
        "LWR",
        "RWR",
        "SWR",
        "TE",
        "LT",
        "LG",
        "C",
        "RG",
        "RT",
        "LDE",
        "RDE",
        "DE",
        "EDGE",
        "LOLB",
        "ROLB",
        "MLB",
        "LCB",
        "RCB",
        "CB",
        "FS",
        "SS",
        "S",
    }
)


def _die(msg: str, code: int = 2) -> None:
    sys.stderr.write(f"STOP: {msg}\n")
    raise SystemExit(code)


def _assert_run_invariants() -> None:
    leaked = sorted(k for k in os.environ if k.startswith("NFL_TOTALS_"))
    if leaked:
        _die(f"E-3: NFL_TOTALS_* must be unset; found {leaked}")
    head = os.popen("git -C /workspace rev-parse HEAD").read().strip()
    if head != REQUIRED_HEAD:
        _die(f"E-3: HEAD {head} != required {REQUIRED_HEAD}")
    dirty = os.popen("git -C /workspace status --porcelain").read().strip()
    if dirty:
        _die(f"E-3: working tree not clean:\n{dirty}")


def _alias(team: str) -> str:
    t = str(team or "").strip().upper()
    return {
        "LAR": "LA",
        "STL": "LA",
        "SD": "LAC",
        "OAK": "LV",
        "WSH": "WAS",
        "JAC": "JAX",
    }.get(t, t)


def _unit_for_position(position: str) -> str:
    p = (position or "").strip().upper()
    if p in {"QB", "RB", "WR", "TE", "FB", "HB"}:
        return "off"
    if p in {"LT", "LG", "C", "RG", "RT", "OL", "T", "G", "OT", "OG"}:
        return "ol"
    if p in {"K", "P", "LS"}:
        return "st"
    return "def"


def _structural_index(position: str, depth: int) -> float:
    p = (position or "").strip().upper()
    d = 1 if depth == 1 else 2
    if p == "QB":
        return QB1_INDEX_UNITS if d == 1 else 0.035
    if p in {"RB", "FB", "HB"}:
        return 0.05 if d == 1 else 0.020
    if p == "WR":
        return 0.04 if d == 1 else 0.015
    if p == "TE":
        return 0.030 if d == 1 else 0.012
    if p in {"LT", "RT", "T", "OT"}:
        return 0.055 if d == 1 else 0.020
    if p in {"C"}:
        return 0.040 if d == 1 else 0.015
    if p in {"LG", "RG", "G", "OG", "OL"}:
        return 0.025 if d == 1 else 0.010
    if p in {"DE", "EDGE", "LDE", "RDE"}:
        return 0.050 if d == 1 else 0.020
    if p in {"CB", "LCB", "RCB"}:
        return 0.040 if d == 1 else 0.015
    if p in {"S", "FS", "SS"}:
        return 0.035 if d == 1 else 0.012
    if p in {"LB", "MLB", "OLB", "ILB", "LOLB", "ROLB"}:
        return 0.030 if d == 1 else 0.012
    if p in {"DT", "NT", "DL"}:
        return 0.028 if d == 1 else 0.010
    return 0.010


def _availability(status: str, doubtful: float, questionable: float, limited: float) -> float:
    raw = (status or "").strip().lower()
    if raw in OUT_STATUSES:
        return 0.00
    if raw == "doubtful":
        return float(doubtful)
    if raw == "questionable":
        return float(questionable)
    if raw in {"limited", "probable"}:
        return float(limited)
    return 1.00


def _is_out_status(status: str) -> bool:
    return (status or "").strip().lower() in OUT_STATUSES


def _load_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _refuse_holdout_season(season: int, where: str) -> None:
    if int(season) in HOLDOUT_YEARS:
        _die(f"holdout year {season} touched at {where}")


def load_schedule() -> List[Dict[str, Any]]:
    rows = []
    for row in _load_csv(RAW / "schedule" / "games_reg_le2023.csv"):
        season = int(row["season"])
        _refuse_holdout_season(season, "schedule")
        if season not in FIT_YEARS:
            continue
        if str(row.get("game_type") or "").upper() != "REG":
            continue
        rows.append(
            {
                "season": season,
                "week": int(row["week"]),
                "gameday": row.get("gameday") or "",
                "gametime": row.get("gametime") or "",
                "home": _alias(row.get("home_team") or ""),
                "away": _alias(row.get("away_team") or ""),
            }
        )
    return rows


def load_oos_le2023() -> Dict[Tuple[int, int, str, str], Dict[str, Any]]:
    out: Dict[Tuple[int, int, str, str], Dict[str, Any]] = {}
    with OOS.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            season = int(row["season"])
            if season in HOLDOUT_YEARS:
                continue
            if season not in FIT_YEARS:
                continue
            home = _alias(row.get("home") or "")
            away = _alias(row.get("away") or "")
            try:
                home_score = float(row["home_score"])
                away_score = float(row["away_score"])
                record_spread = float(row["record_spread"])
                record_total = float(row["record_total"])
                market_spread = float(row["market_spread_home"])
                market_total = float(row["market_total"])
            except (TypeError, ValueError):
                continue
            out[(season, int(row["week"]), home, away)] = {
                "actual_margin": home_score - away_score,
                "actual_total": home_score + away_score,
                "baseline_margin": -record_spread,
                "baseline_total": record_total,
                "close_spread_home": market_spread,
                "close_total": market_total,
            }
    return out


def load_listings() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for season in FIT_YEARS:
        path = RAW / "listings" / f"listings_{season}.csv"
        for row in _load_csv(path):
            year = int(row.get("season") or season)
            _refuse_holdout_season(year, f"listings_{season}")
            if str(row.get("game_type") or "REG").upper() != "REG":
                continue
            if year not in FIT_YEARS:
                continue
            try:
                week = int(row.get("week") or 0)
            except ValueError:
                continue
            rows.append(
                {
                    "season": year,
                    "week": week,
                    "team": _alias(row.get("team") or ""),
                    "player_id": str(row.get("gsis_id") or "").strip(),
                    "player_name": str(row.get("full_name") or "").strip(),
                    "position": str(row.get("position") or "").strip().upper(),
                    "report_status": str(row.get("report_status") or "").strip(),
                    "date_modified": row.get("date_modified") or "",
                }
            )
    return rows


def load_rosters() -> Tuple[Dict[int, Dict[str, set]], Dict[int, set], Dict[Tuple[int, str, str], Dict[str, Any]]]:
    by_team: Dict[int, Dict[str, set]] = defaultdict(lambda: defaultdict(set))
    by_season: Dict[int, set] = defaultdict(set)
    depth: Dict[Tuple[int, str, str], Dict[str, Any]] = {}
    for season in range(2012, 2024):
        path = RAW / "rosters" / f"roster_{season}.csv"
        if not path.exists():
            continue
        for row in _load_csv(path):
            year = int(row.get("season") or season)
            _refuse_holdout_season(year, f"roster_{season}")
            pid = str(row.get("gsis_id") or "").strip()
            if not pid:
                continue
            team = _alias(row.get("team") or "")
            if year >= 2013:
                by_team[year][team].add(pid)
                by_season[year].add(pid)
            pos = str(row.get("depth_chart_position") or row.get("position") or "").strip().upper()
            slot = str(row.get("depth_chart_position") or "").strip().upper()
            d = 1 if slot in STARTER_SLOTS else 2
            key = (year, team, pid)
            prev = depth.get(key)
            if prev is None or (d == 1 and prev.get("depth") != 1):
                depth[key] = {"position": pos or str(row.get("position") or "").upper(), "depth": d}
    return by_team, by_season, depth


def last_report_before_kickoff(
    listings: Sequence[Dict[str, Any]],
    kickoff,
) -> Tuple[List[Dict[str, Any]], Optional[Any], int]:
    usable = []
    latest = None
    n_fail_asof = 0
    for row in listings:
        report = parse_fit_report_time_utc(row.get("date_modified"))
        if report is None:
            n_fail_asof += 1
            continue
        if report >= kickoff:
            n_fail_asof += 1
            continue
        kept = dict(row)
        kept["report_time_utc"] = report
        usable.append(kept)
        if latest is None or report > latest:
            latest = report
    # last report per player
    by_player: Dict[str, Dict[str, Any]] = {}
    for row in usable:
        pid = row["player_id"] or row["player_name"]
        prev = by_player.get(pid)
        if prev is None or row["report_time_utc"] >= prev["report_time_utc"]:
            by_player[pid] = row
    return list(by_player.values()), latest, n_fail_asof


def build_out_history(listings: Sequence[Dict[str, Any]]) -> Dict[Tuple[int, str, str], set]:
    hist: Dict[Tuple[int, str, str], set] = defaultdict(set)
    for row in listings:
        if _is_out_status(row.get("report_status") or ""):
            hist[(row["season"], row["team"], row["player_id"])].add(int(row["week"]))
    return hist


def continuity_for_team(
    *,
    season: int,
    team: str,
    current_ids: set,
    listed_ids: set,
    roster_by_team: Dict[int, Dict[str, set]],
    depth: Dict[Tuple[int, str, str], Dict[str, Any]],
) -> Dict[str, Any]:
    prior = roster_by_team.get(season - 1)
    if prior is None:
        return {
            "continuity_source": "UNKNOWN",
            "x_continuity": None,
            "n_departures": None,
        }
    prior_ids = set(prior.get(team, set()))
    if not prior_ids:
        # franchise alias already applied; still no prior team book
        return {
            "continuity_source": "UNKNOWN",
            "x_continuity": None,
            "n_departures": None,
        }
    x = 0.0
    n = 0
    for pid in prior_ids:
        if pid in current_ids or pid in listed_ids:
            continue
        meta = depth.get((season - 1, team, pid)) or {}
        if int(meta.get("depth") or 2) != 1:
            continue
        pos = str(meta.get("position") or "")
        if _unit_for_position(pos) == "st":
            continue
        x += _structural_index(pos, 1)
        n += 1
    return {
        "continuity_source": "roster_yoy_departure",
        "x_continuity": x,
        "n_departures": n,
    }


def precompute_games(
    schedule: Sequence[Dict[str, Any]],
    listings: Sequence[Dict[str, Any]],
    roster_by_team,
    roster_season,
    depth,
    oos,
) -> Tuple[List[Dict[str, Any]], Dict[str, int], Dict[str, int]]:
    listings_by_tw: Dict[Tuple[int, int, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in listings:
        listings_by_tw[(row["season"], row["week"], row["team"])].append(row)
    out_hist = build_out_history(listings)
    fail_counts = {
        "missing_gametime": 0,
        "unparseable_kickoff": 0,
        "other_fit_row": 0,
    }
    identity_rows: List[Dict[str, Any]] = []
    games: List[Dict[str, Any]] = []

    for game in schedule:
        season = game["season"]
        week = game["week"]
        home = game["home"]
        away = game["away"]
        try:
            kickoff = parse_fit_kickoff_utc(game["gameday"], game["gametime"])
        except FitRowFailure as exc:
            msg = str(exc)
            if "missing gametime" in msg:
                fail_counts["missing_gametime"] += 1
            elif "unparseable" in msg or "23:59:59" in msg:
                fail_counts["unparseable_kickoff"] += 1
            else:
                fail_counts["other_fit_row"] += 1
            games.append(
                {
                    "season": season,
                    "week": week,
                    "home": home,
                    "away": away,
                    "row_status": "FitRowFailure",
                    "failure": msg,
                    "complete": False,
                    "continuity_source_home": "UNKNOWN",
                    "continuity_source_away": "UNKNOWN",
                    "x_continuity_home": None,
                    "x_continuity_away": None,
                }
            )
            continue

        sides = {}
        game_ok = True
        for side, team in (("home", home), ("away", away)):
            raw = listings_by_tw.get((season, week, team), [])
            usable, listing_as_of, n_asof_fail = last_report_before_kickoff(raw, kickoff)
            players = []
            listed_ids = set()
            for row in usable:
                ident = resolve_fit_player_identity(
                    player_id=row["player_id"],
                    team=team,
                    roster_by_team=roster_by_team.get(season, {}),
                    roster_season=roster_season.get(season, set()),
                )
                identity_rows.append(ident)
                meta = depth.get((season, team, row["player_id"])) or {}
                pos = row["position"] or str(meta.get("position") or "")
                depth_n = int(meta.get("depth") or 2)
                unit = _unit_for_position(pos)
                lag_weeks = out_hist.get((season, team, row["player_id"]), set())
                n_lag_out = sum(1 for w in lag_weeks if week - 5 <= w <= week - 1)
                players.append(
                    {
                        "player_id": row["player_id"],
                        "player_name": row["player_name"],
                        "position": pos,
                        "unit": unit,
                        "status": row["report_status"],
                        "depth": depth_n,
                        "value": _structural_index(pos, depth_n),
                        "n_lag_out": n_lag_out,
                        "identity_rule": ident["identity_rule"],
                        "identity_resolved": ident["identity_resolved"],
                        "is_qb1_out_candidate": pos == "QB" and depth_n == 1,
                    }
                )
                if row["player_id"]:
                    listed_ids.add(row["player_id"])
            current_ids = set(roster_by_team.get(season, {}).get(team, set()))
            cont = continuity_for_team(
                season=season,
                team=team,
                current_ids=current_ids,
                listed_ids=listed_ids,
                roster_by_team=roster_by_team,
                depth=depth,
            )
            sides[side] = {
                "team": team,
                "players": players,
                "listing_as_of": listing_as_of.isoformat() if listing_as_of else None,
                "n_raw_listings": len(raw),
                "n_usable_listings": len(usable),
                "n_asof_fail": n_asof_fail,
                **cont,
            }
            if not usable:
                # no usable as-of listing → NULL unit residual (not healthy 0)
                sides[side]["units_null"] = True
            else:
                sides[side]["units_null"] = False

        targets = oos.get((season, week, home, away))
        games.append(
            {
                "season": season,
                "week": week,
                "home": home,
                "away": away,
                "kickoff_utc": kickoff.isoformat(),
                "row_status": "ok" if game_ok else "FitRowFailure",
                "sides": sides,
                "targets": targets,
                "complete": (not sides["home"]["units_null"]) and (not sides["away"]["units_null"]),
                "continuity_source_home": sides["home"]["continuity_source"],
                "continuity_source_away": sides["away"]["continuity_source"],
                "x_continuity_home": sides["home"]["x_continuity"],
                "x_continuity_away": sides["away"]["x_continuity"],
            }
        )
    return games, fail_counts, count_identity_resolutions(identity_rows)


def side_units(side: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Optional[float]]:
    if side.get("units_null"):
        return {"off": None, "def": None, "ol": None, "qb1_out": False}
    x = {"off": 0.0, "def": 0.0, "ol": 0.0}
    qb1_out = False
    window = 5.0
    for player in side["players"]:
        if player["unit"] == "st":
            continue
        if not player["identity_resolved"]:
            # C-11: unresolved → that component NULL
            x[player["unit"]] = None
            continue
        if x.get(player["unit"]) is None:
            continue
        avail = _availability(
            player["status"],
            params["doubtful"],
            params["questionable"],
            params["limited"],
        )
        missing = 1.0 - avail
        if missing <= 0:
            continue
        absorbed = 1.0 if (player["n_lag_out"] / window) >= float(params["theta"]) else 0.0
        x[player["unit"]] += missing * (1.0 - absorbed) * float(player["value"])
        if player["is_qb1_out_candidate"] and avail == 0.0:
            qb1_out = True
    return {**x, "qb1_out": qb1_out}


def residual_from_units(
    home_u: Dict[str, Optional[float]],
    away_u: Dict[str, Optional[float]],
    home_c: Optional[float],
    away_c: Optional[float],
    params: Dict[str, Any],
) -> Dict[str, Any]:
    flags = []
    comps = {}
    for name, val in (
        ("off_home", home_u["off"]),
        ("def_home", home_u["def"]),
        ("ol_home", home_u["ol"]),
        ("off_away", away_u["off"]),
        ("def_away", away_u["def"]),
        ("ol_away", away_u["ol"]),
    ):
        comps[name] = None if val is None else val * QB1_POINTS_PER_INDEX_UNIT
        if val is None:
            unit = name.split("_")[0]
            flag = {
                "off": FLAG_INJURY_PARTIAL_OFF,
                "def": FLAG_INJURY_PARTIAL_DEF,
                "ol": FLAG_INJURY_PARTIAL_OL,
            }[unit]
            if flag not in flags:
                flags.append(flag)
    # E-1: UNKNOWN continuity is not folded as 0
    if home_c is None:
        comps["continuity_home"] = None
    else:
        comps["continuity_home"] = home_c * QB1_POINTS_PER_INDEX_UNIT
    if away_c is None:
        comps["continuity_away"] = None
    else:
        comps["continuity_away"] = away_c * QB1_POINTS_PER_INDEX_UNIT

    complete = all(comps[k] is not None for k in ("off_home", "def_home", "ol_home", "off_away", "def_away", "ol_away"))
    if not complete:
        flags.append(FLAG_MISSING_KOSEDGE_INJURY_NOWCAST)
        return {
            "complete": False,
            "components": comps,
            "delta_margin": None,
            "delta_total": None,
            "flags": flags,
        }

    off_home = comps["off_home"] + (0.0 if comps["continuity_home"] is None else comps["continuity_home"])
    off_away = comps["off_away"] + (0.0 if comps["continuity_away"] is None else comps["continuity_away"])
    if home_u["qb1_out"]:
        off_home = max(off_home, QB1_FLOOR_SPREAD_POINTS)
    if away_u["qb1_out"]:
        off_away = max(off_away, QB1_FLOOR_SPREAD_POINTS)
    def_home = comps["def_home"]
    def_away = comps["def_away"]
    ol_home = comps["ol_home"]
    ol_away = comps["ol_away"]
    home_pts = off_home + ol_home + (-def_away)
    away_pts = off_away + ol_away + (-def_home)
    d_margin = home_pts - away_pts
    d_total = home_pts + away_pts
    if abs(d_margin) < 0.05 and abs(d_total) < 0.05:
        d_margin = 0.0
        d_total = 0.0
    cap_s = params.get("cap_spread")
    cap_t = params.get("cap_total")
    if cap_s is not None:
        d_margin = max(-float(cap_s), min(float(cap_s), d_margin))
    if cap_t is not None:
        d_total = max(-float(cap_t), min(float(cap_t), d_total))
    return {
        "complete": True,
        "components": comps,
        "delta_margin": d_margin,
        "delta_total": d_total,
        "flags": flags,
    }


def score_rows(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    n = 0
    mae_m = 0.0
    mae_t = 0.0
    clv = 0.0
    n_clv = 0
    for row in rows:
        if not row.get("complete"):
            continue
        tgt = row.get("targets")
        if not tgt or row.get("delta_margin") is None:
            continue
        r_m = tgt["actual_margin"] - tgt["baseline_margin"]
        r_t = tgt["actual_total"] - tgt["baseline_total"]
        mae_m += abs(r_m - float(row["delta_margin"]))
        mae_t += abs(r_t - float(row["delta_total"]))
        n += 1
        model_spread_home = -(tgt["baseline_margin"] + float(row["delta_margin"]))
        close = tgt["close_spread_home"]
        edge = model_spread_home - close
        actual_spread_home = -tgt["actual_margin"]
        if edge != 0:
            clv += (close - actual_spread_home) * (1.0 if edge > 0 else -1.0)
            n_clv += 1
    return {
        "n": n,
        "mae_margin": (mae_m / n) if n else None,
        "mae_total": (mae_t / n) if n else None,
        "mean_spread_clv_vs_close": (clv / n_clv) if n_clv else None,
        "n_clv": n_clv,
    }


def apply_params(games: Sequence[Dict[str, Any]], params: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for game in games:
        row = {
            "season": game["season"],
            "week": game["week"],
            "home": game["home"],
            "away": game["away"],
            "row_status": game["row_status"],
            "complete": False,
            "continuity_source_home": game.get("continuity_source_home") or "UNKNOWN",
            "continuity_source_away": game.get("continuity_source_away") or "UNKNOWN",
            "x_continuity_home": game.get("x_continuity_home"),
            "x_continuity_away": game.get("x_continuity_away"),
            "targets": game.get("targets"),
            "kickoff_utc": game.get("kickoff_utc"),
            "failure": game.get("failure"),
        }
        if game["row_status"] != "ok":
            out.append(row)
            continue
        home_u = side_units(game["sides"]["home"], params)
        away_u = side_units(game["sides"]["away"], params)
        resid = residual_from_units(
            home_u,
            away_u,
            game.get("x_continuity_home"),
            game.get("x_continuity_away"),
            params,
        )
        row.update(
            {
                "complete": resid["complete"],
                "delta_margin": resid["delta_margin"],
                "delta_total": resid["delta_total"],
                "flags": resid["flags"],
                "components": resid["components"],
            }
        )
        out.append(row)
    return out


def iter_spec_c() -> Iterable[Dict[str, Any]]:
    for theta in THETA_GRID:
        for d in DOUBTFUL_GRID:
            for q in QUESTIONABLE_GRID:
                for lim in LIMITED_GRID:
                    for cs in CAP_SPREAD_GRID:
                        for ct in CAP_TOTAL_GRID:
                            yield {
                                "spec": "C",
                                "theta": theta,
                                "doubtful": d,
                                "questionable": q,
                                "limited": lim,
                                "cap_spread": cs,
                                "cap_total": ct,
                            }


def fold_rows(rows: Sequence[Dict[str, Any]], seasons: Sequence[int]) -> List[Dict[str, Any]]:
    allow = set(seasons)
    return [r for r in rows if r["season"] in allow]


def pick_key(metrics: Dict[str, Any], params: Dict[str, Any]) -> Tuple:
    mae = metrics["mae_margin"]
    mae_t = metrics["mae_total"]
    return (
        mae if mae is not None else 1e9,
        mae_t if mae_t is not None else 1e9,
        float(params["theta"]),
        float(params["doubtful"]),
        float(params.get("cap_spread") or 9),
    )


def main() -> int:
    _assert_run_invariants()
    resolved = resolve_nfl_totals_env({})
    if any(v is not None for v in resolved.values()):
        _die("E-3: config env must resolve all NFL_TOTALS_* as unset")
    cfg = config_hash(env={})
    bnd = bound_hash(code_sha=REQUIRED_HEAD, env={})
    print(f"protocol={FIT_PROTOCOL_ID}")
    print(f"code_sha={REQUIRED_HEAD}")
    print(f"config_hash={cfg}")
    print(f"bound_hash={bnd}")
    print(f"ledger_version={LEDGER_VERSION} application_site={APPLICATION_SITE}")
    print("inner_selection_metric=mean(F1,F2) MAE |r_margin - d_margin| ; Q6 CLV descriptive only")
    print("targets=actual - record/HFA baseline (not market, not 2024/2025 packaged)")
    print("continuity: UNKNOWN if no prior-season roster book; never filled as 0")

    schedule = load_schedule()
    listings = load_listings()
    roster_by_team, roster_season, depth = load_rosters()
    oos = load_oos_le2023()
    print(f"n_schedule_games={len(schedule)} n_listing_rows={len(listings)} n_oos_le2023={len(oos)}")
    games, fail_counts, ident_counts = precompute_games(
        schedule, listings, roster_by_team, roster_season, depth, oos
    )
    n_fail = sum(1 for g in games if g["row_status"] == "FitRowFailure")
    n_complete_feat = sum(1 for g in games if g.get("complete"))
    cont_counts: Dict[str, int] = defaultdict(int)
    for g in games:
        cont_counts[g.get("continuity_source_home") or "UNKNOWN"] += 1
        cont_counts[g.get("continuity_source_away") or "UNKNOWN"] += 1
    print(f"n_precomputed={len(games)} n_fitrow_failure={n_fail} n_feature_complete={n_complete_feat}")
    print("fitrow_failures", json.dumps(fail_counts, sort_keys=True))
    print("identity_counts", json.dumps(ident_counts, sort_keys=True))
    print("continuity_source_counts", json.dumps(dict(cont_counts), sort_keys=True))

    f1_fit, f1_val = list(range(2013, 2022)), [2022]
    f2_fit, f2_val = list(range(2013, 2023)), [2023]

    def evaluate(params: Dict[str, Any]) -> Dict[str, Any]:
        applied = apply_params(games, params)
        s1 = score_rows(fold_rows(applied, f1_val))
        s2 = score_rows(fold_rows(applied, f2_val))
        maes = [m for m in (s1["mae_margin"], s2["mae_margin"]) if m is not None]
        return {
            "params": params,
            "f1_validate": s1,
            "f2_validate": s2,
            "mean_inner_mae_margin": (sum(maes) / len(maes)) if maes else None,
            "applied": applied,
        }

    spec_a = evaluate(SPEC_A)
    print(
        "spec_A",
        json.dumps(
            {
                "mean_inner_mae_margin": spec_a["mean_inner_mae_margin"],
                "f1": spec_a["f1_validate"],
                "f2": spec_a["f2_validate"],
            },
            sort_keys=True,
        ),
    )

    best_b = None
    for theta in THETA_GRID:
        params = dict(SPEC_A)
        params.update({"spec": "B", "theta": theta})
        ev = evaluate(params)
        ev_key = (
            ev["mean_inner_mae_margin"] if ev["mean_inner_mae_margin"] is not None else 1e9,
            pick_key(ev["f1_validate"], params),
        )
        if best_b is None or ev_key < best_b[0]:
            best_b = (ev_key, ev)
    spec_b = best_b[1]
    print(
        "spec_B_selected",
        json.dumps(
            {
                "params": spec_b["params"],
                "mean_inner_mae_margin": spec_b["mean_inner_mae_margin"],
                "f1": spec_b["f1_validate"],
                "f2": spec_b["f2_validate"],
            },
            sort_keys=True,
        ),
    )

    best_c = None
    n_c = 0
    for params in iter_spec_c():
        n_c += 1
        ev = evaluate(params)
        ev_key = (
            ev["mean_inner_mae_margin"] if ev["mean_inner_mae_margin"] is not None else 1e9,
            pick_key(ev["f1_validate"], params),
        )
        if best_c is None or ev_key < best_c[0]:
            best_c = (ev_key, ev)
    spec_c = best_c[1]
    print(f"spec_C_grid_n={n_c}")
    print(
        "spec_C_selected",
        json.dumps(
            {
                "params": spec_c["params"],
                "mean_inner_mae_margin": spec_c["mean_inner_mae_margin"],
                "f1": spec_c["f1_validate"],
                "f2": spec_c["f2_validate"],
            },
            sort_keys=True,
        ),
    )

    candidates = [("A", spec_a), ("B", spec_b), ("C", spec_c)]
    winner_name, winner = min(
        candidates,
        key=lambda item: (
            item[1]["mean_inner_mae_margin"] if item[1]["mean_inner_mae_margin"] is not None else 1e9,
            item[0],
        ),
    )
    print(f"selected_spec={winner_name}")
    applied = winner["applied"]
    fit_years = [y for y in FIT_YEARS]
    if set(fit_years) & HOLDOUT_YEARS:
        _die("T-leak: fit years intersect holdout")

    out_dir = Path("/opt/cursor/artifacts/injury-fit-le2023")
    out_dir.mkdir(parents=True, exist_ok=True)

    fit_object = {
        "kind": "injury_residual_fit_object",
        "protocol": FIT_PROTOCOL_ID,
        "code_sha": REQUIRED_HEAD,
        "config_hash": cfg,
        "bound_hash": bnd,
        "fit_years": fit_years,
        "holdout_years_excluded": sorted(HOLDOUT_YEARS),
        "selected_spec": winner_name,
        "selected_params": winner["params"],
        "spec_A": {k: spec_a[k] for k in ("params", "mean_inner_mae_margin", "f1_validate", "f2_validate")},
        "spec_B": {k: spec_b[k] for k in ("params", "mean_inner_mae_margin", "f1_validate", "f2_validate")},
        "spec_C": {k: spec_c[k] for k in ("params", "mean_inner_mae_margin", "f1_validate", "f2_validate")},
        "inner_selection_metric": "mean(F1,F2) MAE |r_margin-d_margin|",
        "qb1_floor": QB1_FLOOR_SPREAD_POINTS,
        "qb1_points_per_index_unit": QB1_POINTS_PER_INDEX_UNIT,
        "healthy_epsilon": 0.05,
        "n_games": len(applied),
        "n_complete": sum(1 for r in applied if r.get("complete")),
        "n_fitrow_failure": n_fail,
        "fitrow_failure_counts": fail_counts,
        "identity_counts": ident_counts,
        "continuity_source_counts": dict(cont_counts),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    fit_path = out_dir / "fit_object.json"
    fit_blob = json.dumps(fit_object, sort_keys=True, default=str, indent=2) + "\n"
    fit_path.write_text(fit_blob, encoding="utf-8")
    fit_sha = hashlib.sha256(fit_blob.encode("utf-8")).hexdigest()
    print(f"fit_object_sha={fit_sha}")

    ledger_rows = []
    for row in applied:
        tgt = row.get("targets") or {}
        ledger_rows.append(
            {
                "season": row["season"],
                "week": row["week"],
                "home": row["home"],
                "away": row["away"],
                "row_status": row["row_status"],
                "complete": row.get("complete"),
                "applied": False,
                "continuity_source_home": row.get("continuity_source_home") or "UNKNOWN",
                "continuity_source_away": row.get("continuity_source_away") or "UNKNOWN",
                "x_continuity_home": row.get("x_continuity_home"),
                "x_continuity_away": row.get("x_continuity_away"),
                "delta_margin": row.get("delta_margin"),
                "delta_total": row.get("delta_total"),
                "flags": row.get("flags") or [],
                "kickoff_utc": row.get("kickoff_utc"),
                "failure": row.get("failure"),
                "has_targets": bool(tgt),
                "baseline_margin": tgt.get("baseline_margin"),
                "baseline_total": tgt.get("baseline_total"),
            }
        )
    ledger = {
        "kind": "injury_residual_fit_ledger",
        "protocol": FIT_PROTOCOL_ID,
        "code_sha": REQUIRED_HEAD,
        "config_hash": cfg,
        "bound_hash": bnd,
        "fit_object_sha": fit_sha,
        "e1": "continuity_source tagged per side; UNKNOWN when None, never neutral 0",
        "n": len(ledger_rows),
        "rows": ledger_rows,
    }
    ledger_path = out_dir / "fit_ledger.json"
    ledger_blob = json.dumps(ledger, sort_keys=True, default=str) + "\n"
    ledger_path.write_text(ledger_blob, encoding="utf-8")

    players_export = []
    games_export = []
    for game, row in zip(games, applied):
        games_export.append(
            {
                "game_id": f"{row['season']}_{row['week']}_{row['away']}_{row['home']}",
                "season": row["season"],
                "week": row["week"],
                "applied": False,
                "complete": row.get("complete"),
                "continuity_source_home": row.get("continuity_source_home") or "UNKNOWN",
                "continuity_source_away": row.get("continuity_source_away") or "UNKNOWN",
                "delta_margin": row.get("delta_margin"),
                "delta_total": row.get("delta_total"),
            }
        )
        if game.get("sides"):
            for side in ("home", "away"):
                for player in game["sides"][side]["players"]:
                    players_export.append(
                        {
                            "player_id": player["player_id"],
                            "status": player["status"],
                            "unit": player["unit"],
                            "identity_resolved": player["identity_resolved"],
                            "identity_rule": player["identity_rule"],
                            "season": row["season"],
                            "week": row["week"],
                            "team": game["sides"][side]["team"],
                        }
                    )

    export = write_sealed_injury_export(
        str(out_dir / "sealed_injury_export.json"),
        games=games_export,
        players=players_export,
        code_sha=REQUIRED_HEAD,
        config_hash_value=cfg,
        fit_object_sha=fit_sha,
        fit_years=fit_years,
        source_name="sealed_listings_le2023",
    )
    print(f"sealed_export={export}")

    results = {
        "selected_spec": winner_name,
        "selected_params": winner["params"],
        "mean_inner_mae_margin": winner["mean_inner_mae_margin"],
        "f1_validate": winner["f1_validate"],
        "f2_validate": winner["f2_validate"],
        "n_games": len(applied),
        "n_complete": sum(1 for r in applied if r.get("complete")),
        "n_fitrow_failure": n_fail,
        "fitrow_failure_counts": fail_counts,
        "identity_counts": ident_counts,
        "continuity_source_counts": dict(cont_counts),
        "fit_object_sha": fit_sha,
        "code_sha": REQUIRED_HEAD,
        "config_hash": cfg,
        "bound_hash": bnd,
    }
    (out_dir / "fit_results.json").write_text(
        json.dumps(results, sort_keys=True, default=str, indent=2) + "\n",
        encoding="utf-8",
    )
    print("RESULTS", json.dumps(results, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
