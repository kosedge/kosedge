#!/usr/bin/env python3
"""Pinned frozen row builder — B-4b (filed with expected answers v5).

Builds player ``value`` and ``x_continuity`` with frozen ``precompute_games``
from script 8d188da2 (``_structural_index`` / ``continuity_for_team``) under
HEAD 8e2a15ac injury_paths QB1_INDEX_UNITS = 0.12.

Raw inputs are sha-pinned. games.json is not a source of value, continuity,
or deltas. Naive timestamps STOP (B-4c).

le2023 reproduction: apply_params on these built rows matches export a38a55bb
field-wise on delta_margin / delta_total for all 2863 games (IMV reads outputs).
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

HERE = Path(__file__).resolve().parent

REQUIRED_FIT = "6a5490dbc09b160f4509ea65b3b2257f9703f9d43635092d0da94c1577abb657"
REQUIRED_FROZEN_SCRIPT = "8d188da27d3c9f802acdca76763e1ca05e714040cc5ea3722e4922853f28167c"
REQUIRED_NULL_CONTRACT = "ff8e6527f63b0afd727eed30444436ceae320cc336d9113a2634fd66d4aebad2"
REQUIRED_INJURY_PATHS = "ebd3dac083562afb4928e2ed756f617248894e636356f7426f0bc6ae58344e8b"
REQUIRED_SCHEDULE = "ce80fe92982c1efdc78fc28a5429539c5a19cc061fc34ff979d57020841c5e0f"
PINNED_QB1_INDEX_UNITS = 0.12
BUILT_BY = "8d188da2.precompute_games+injury_paths_8e2a15ac.QB1_INDEX_UNITS=0.12"
LISTINGS_YEAR = __import__("re").compile(r"^listings_(\d{4})\.csv$")
ALWAYS_FORBIDDEN = frozenset({2026})

REQUIRED_ROSTERS = {
    2012: "90628fcdadd9f2dde083bc77d41139cedc9fefd1fcc09f2ce8675823de23291b",
    2013: "abf73c2b1ef10914af78f6b7397338508bd0c9f0372d2f0667a630e06a4484ed",
    2014: "f3c3e9cced60d99ebdcb410b76ffeda72b207b7045983b7a63f677ad9a34814f",
    2015: "63807a50226a94f6724b3694198b41661c76211707115b2d52975237ebc4ecb6",
    2016: "c7a57a4816d05ef651f4c56b8209c38b98e3d60582ddd60cb8048ef657472ca1",
    2017: "22584ad80445611edff6dcbc6dce9ab596bdc484430d8aac298725da15697fd4",
    2018: "60c7f1dabb508acc800ef81b4f69892511b1f78246bdb2cca6115a506c523b0a",
    2019: "b00259cfddf2146512569423275dc17e142d31ddb13bfba6b0b826c9d3d810da",
    2020: "dcf25143db7b54ac488d042b6c24142340effced1d6c8599b2084a9f412b3ed2",
    2021: "a95e57ebe1df25224a4d19ed43aaffc5c2097a8b369954178b8592537ff77d34",
    2022: "864719595d14909c73bd14110adcdcfc304c6621de9ba34feafb83666fac43c9",
    2023: "f98283e6ef420babc597092b5483109a4570f9b5f63b7bfcce69643290960b6c",
}
REQUIRED_LISTINGS = {
    2013: "b84c71cf23be81375bbca62f7d2c51d53fa75330fbcf9f598ec4ac17fea7d8be",
    2014: "e675fd5d86c3451d76e7c5d530095db1641347eb3f9796c9a30dd7a75e3ba634",
    2015: "fbca54ef42594cc52facc0d8c8dd74802b812771b9e33032e44ae8c7e21b0360",
    2016: "504e05968cb9c54ddc730fd9b6e7d1dd16a62db8029cc784d3d7bafcea7ff7cb",
    2017: "0d5139fbf41b0866517bd2bd5fd85bb20dbd4dd9bc36a706fed030a88731de6f",
    2018: "4724e1f37cc3076f564e997fbf269190e7dbe795a39315b903788e0a9c40065e",
    2019: "daddfe8e04ddc3a29bce14f362e774fbadfb274c807f1f0fde7b5bf32aaf6cdf",
    2020: "706cca82824214f6b73ba0c6e537d3ee39766a50c644b8974b9fc28d7518de90",
    2021: "1049fb9ff0fe7cfcf3ba8bfe1f5a35d3aba985c461c8fb7bf5201735b6d34254",
    2022: "5f0d60324e597edd1a2ced8540b04e40b51dd440591dd1df11b8d96343387c9e",
    2023: "16b04e21da5aa3944cfa9c22cafcc84ed7e6d9866eaddf0344e9b8cbf2f63afe",
}


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"B-4b cannot load {name} from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def qb1_from_seeded_injury_paths(pkg: Path) -> float:
    path = pkg / "seeded" / "injury_paths_8e2a15ac.py"
    got = _sha256_file(path)
    if got != REQUIRED_INJURY_PATHS:
        raise AssertionError(f"B-4b injury_paths sha {got} != {REQUIRED_INJURY_PATHS}")
    text = path.read_text(encoding="utf-8")
    if "QB1_INDEX_UNITS = 0.12" not in text:
        raise AssertionError("B-4b seeded injury_paths missing QB1_INDEX_UNITS = 0.12")
    if "QB1_POINTS_PER_INDEX_UNIT = 12.5" not in text:
        raise AssertionError("B-4b seeded injury_paths missing QB1_POINTS_PER_INDEX_UNIT = 12.5")
    if "QB1_FLOOR_SPREAD_POINTS = QB1_INDEX_UNITS * QB1_POINTS_PER_INDEX_UNIT" not in text:
        raise AssertionError("B-4b seeded injury_paths missing floor = units * ppu")
    return PINNED_QB1_INDEX_UNITS


def assert_le2023_raw_pins(pkg: Path) -> Dict[str, str]:
    out = {
        "injury_paths_8e2a15ac": _sha256_file(pkg / "seeded" / "injury_paths_8e2a15ac.py"),
        "schedule": _sha256_file(pkg / "seeded" / "raw-le2023" / "schedule" / "games_reg_le2023.csv"),
    }
    if out["injury_paths_8e2a15ac"] != REQUIRED_INJURY_PATHS:
        raise AssertionError("B-4b injury_paths pin drifted")
    if out["schedule"] != REQUIRED_SCHEDULE:
        raise AssertionError("B-4b schedule pin drifted")
    for year, exp in REQUIRED_ROSTERS.items():
        path = pkg / "seeded" / "raw-le2023" / "rosters" / f"roster_{year}.csv"
        got = _sha256_file(path)
        if got != exp:
            raise AssertionError(f"B-4b roster_{year} sha {got} != {exp}")
        out[f"roster_{year}"] = got
    for year, exp in REQUIRED_LISTINGS.items():
        path = pkg / "seeded" / "listings-le2023" / f"listings_{year}.csv"
        got = _sha256_file(path)
        if got != exp:
            raise AssertionError(f"B-4b listings_{year} sha {got} != {exp}")
        out[f"listings_{year}"] = got
    return out


def load_frozen_script(pkg: Path):
    fit = json.loads((pkg / "seeded" / "fit_object.json").read_text(encoding="utf-8"))
    if _sha256_file(pkg / "seeded" / "fit_object.json") != REQUIRED_FIT:
        raise AssertionError("B-4b fit_object drifted")
    if _sha256_file(pkg / "seeded" / "run_injury_residual_fit.py") != REQUIRED_FROZEN_SCRIPT:
        raise AssertionError("B-4b frozen script drifted")
    if _sha256_file(pkg / "seeded" / "nfl_injury_null_contract_8e2a15ac.py") != REQUIRED_NULL_CONTRACT:
        raise AssertionError("B-4b null contract drifted")
    units = qb1_from_seeded_injury_paths(pkg)
    contract = _load_module("null_contract_ff8e6527", pkg / "seeded" / "nfl_injury_null_contract_8e2a15ac.py")
    injury_paths = types.ModuleType("src.services.nfl_season_engine.injury_paths")
    injury_paths.QB1_INDEX_UNITS = units
    injury_paths.QB1_POINTS_PER_INDEX_UNIT = float(fit["qb1_points_per_index_unit"])
    injury_paths.QB1_FLOOR_SPREAD_POINTS = float(fit["qb1_floor"])
    src = types.ModuleType("src")
    src.services = types.ModuleType("src.services")
    src.services.nfl_injury_null_contract = contract
    src.services.nfl_season_engine = types.ModuleType("src.services.nfl_season_engine")
    src.services.nfl_season_engine.injury_paths = injury_paths
    sys.modules.setdefault("src", src)
    sys.modules["src.services"] = src.services
    sys.modules["src.services.nfl_injury_null_contract"] = contract
    sys.modules["src.services.nfl_season_engine"] = src.services.nfl_season_engine
    sys.modules["src.services.nfl_season_engine.injury_paths"] = injury_paths
    script = _load_module("frozen_fit_8d188da2_builder", pkg / "seeded" / "run_injury_residual_fit.py")
    for name in ("precompute_games", "apply_params", "_structural_index", "continuity_for_team"):
        if not hasattr(script, name):
            raise AssertionError(f"B-4b frozen script missing {name}")
    return script, fit["selected_params"], units


def _refuse_naive_timestamp(value: Any, where: str) -> None:
    raw = "" if value is None else str(value).strip()
    if not raw:
        return
    probe = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        stamp = datetime.fromisoformat(probe)
    except ValueError as exc:
        raise AssertionError(f"B-4c refuse: unparseable timestamp {value!r} at {where}") from exc
    if stamp.tzinfo is None:
        raise AssertionError(f"B-4c refuse: naive/zoneless timestamp {value!r} at {where}")


def assert_listings_not_naive(listings_dir: Path) -> None:
    if not listings_dir.is_dir():
        raise AssertionError(f"B-4b missing listings dir {listings_dir}")
    for child in sorted(listings_dir.iterdir()):
        match = LISTINGS_YEAR.match(child.name)
        if not match:
            continue
        year = int(match.group(1))
        if year in ALWAYS_FORBIDDEN:
            raise AssertionError(f"B-4b refuse: 2026 listings {child.name}")
        with child.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                _refuse_naive_timestamp(row.get("date_modified"), f"{child.name} date_modified")


def refuse_games_json_values(games_path: Optional[Path]) -> None:
    """games.json is not a source of value / x_continuity / deltas."""
    if games_path is None or not games_path.is_file():
        return
    doc = json.loads(games_path.read_text(encoding="utf-8"))
    for game in doc.get("games") or []:
        if "delta_margin" in game or "delta_total" in game:
            raise AssertionError("B-4b refuse: games.json carries deltas; builder is the only source")
        if "x_continuity_home" in game or "x_continuity_away" in game:
            raise AssertionError("B-4b refuse: games.json carries x_continuity; builder is the only source")
        sides = game.get("sides") or {}
        for side in sides.values():
            for player in (side or {}).get("players") or []:
                if "value" in player:
                    raise AssertionError("B-4b refuse: games.json carries player value; builder is the only source")


def load_schedule_csv(path: Path, script) -> List[Dict[str, Any]]:
    if not path.is_file():
        raise AssertionError(f"B-4b missing schedule {path}")
    rows: List[Dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            season = int(row["season"])
            if season in ALWAYS_FORBIDDEN:
                raise AssertionError("B-4b refuse: schedule contains 2026")
            home = script._alias(row.get("home") or row.get("home_team") or "")
            away = script._alias(row.get("away") or row.get("away_team") or "")
            rec = {
                "season": season,
                "week": int(row["week"]),
                "gameday": row.get("gameday") or "",
                "gametime": row.get("gametime") or "",
                "home": home,
                "away": away,
            }
            # Missing gameday/gametime becomes FitRowFailure in precompute_games (G-4).
            rows.append(rec)
    return rows


def load_listings_dir(listings_dir: Path, script, allowed_years: Optional[Sequence[int]] = None) -> List[Dict[str, Any]]:
    allowed = None if allowed_years is None else frozenset(int(y) for y in allowed_years)
    rows: List[Dict[str, Any]] = []
    for child in sorted(listings_dir.iterdir()):
        match = LISTINGS_YEAR.match(child.name)
        if not match:
            continue
        year = int(match.group(1))
        if year in ALWAYS_FORBIDDEN:
            raise AssertionError(f"B-4b refuse: listings_{year}")
        if allowed is not None and year not in allowed:
            continue
        with child.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                season = int(row.get("season") or year)
                if season in ALWAYS_FORBIDDEN:
                    raise AssertionError("B-4b refuse: listing season 2026")
                _refuse_naive_timestamp(row.get("date_modified"), f"{child.name}")
                if str(row.get("game_type") or "REG").upper() != "REG":
                    continue
                try:
                    week = int(row.get("week") or 0)
                except ValueError:
                    continue
                rows.append(
                    {
                        "season": season,
                        "week": week,
                        "team": script._alias(row.get("team") or ""),
                        "player_id": str(row.get("gsis_id") or "").strip(),
                        "player_name": str(row.get("full_name") or "").strip(),
                        "position": str(row.get("position") or "").strip().upper(),
                        "report_status": str(row.get("report_status") or "").strip(),
                        "date_modified": row.get("date_modified") or "",
                    }
                )
    return rows


def load_rosters_dir(rosters_dir: Path, script) -> Tuple[Dict[int, Dict[str, set]], Dict[int, set], Dict[Tuple[int, str, str], Dict[str, Any]]]:
    from collections import defaultdict

    by_team: Dict[int, Dict[str, set]] = defaultdict(lambda: defaultdict(set))
    by_season: Dict[int, set] = defaultdict(set)
    depth: Dict[Tuple[int, str, str], Dict[str, Any]] = {}
    if not rosters_dir.is_dir():
        raise AssertionError(f"B-4b missing rosters dir {rosters_dir}")
    starter = script.STARTER_SLOTS
    for child in sorted(rosters_dir.glob("roster_*.csv")):
        with child.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                year = int(row.get("season") or 0)
                if year in ALWAYS_FORBIDDEN:
                    raise AssertionError("B-4b refuse: roster season 2026")
                pid = str(row.get("gsis_id") or "").strip()
                if not pid:
                    continue
                team = script._alias(row.get("team") or "")
                by_team[year][team].add(pid)
                by_season[year].add(pid)
                pos = str(row.get("depth_chart_position") or row.get("position") or "").strip().upper()
                slot = str(row.get("depth_chart_position") or "").strip().upper()
                d = 1 if slot in starter else 2
                key = (year, team, pid)
                prev = depth.get(key)
                if prev is None or (d == 1 and prev.get("depth") != 1):
                    depth[key] = {"position": pos or str(row.get("position") or "").upper(), "depth": d}
    return by_team, by_season, depth


def build_rows(
    pkg: Path,
    *,
    listings_dir: Path,
    schedule_path: Path,
    rosters_dir: Path,
    games_json: Optional[Path] = None,
    pin_le2023_raw: bool = False,
    allowed_listing_years: Optional[Sequence[int]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Build games with frozen precompute_games. Does not read games.json values."""
    refuse_games_json_values(games_json)
    assert_listings_not_naive(listings_dir)
    pins = {}
    if pin_le2023_raw:
        pins.update(assert_le2023_raw_pins(pkg))
    script, params, units = load_frozen_script(pkg)
    schedule = load_schedule_csv(schedule_path, script)
    listings = load_listings_dir(listings_dir, script, allowed_listing_years)
    roster_by_team, roster_season, depth = load_rosters_dir(rosters_dir, script)
    games, fail_counts, _ident = script.precompute_games(
        schedule, listings, roster_by_team, roster_season, depth, {}
    )
    for game in games:
        game["_built_by"] = BUILT_BY
        game["_qb1_index_units"] = units
        if "delta_margin" in game or "delta_total" in game:
            raise AssertionError("B-4b builder must not emit deltas; apply_params does that")
    pins.update(
        {
            "frozen_script": REQUIRED_FROZEN_SCRIPT,
            "fit_object": REQUIRED_FIT,
            "null_contract": REQUIRED_NULL_CONTRACT,
            "injury_paths_8e2a15ac": REQUIRED_INJURY_PATHS,
            "qb1_index_units": units,
            "qb1_index_units_source": "seeded/injury_paths_8e2a15ac.py QB1_INDEX_UNITS = 0.12 (HEAD 8e2a15ac)",
            "built_by": BUILT_BY,
            "n_games": len(games),
            "fail_counts": fail_counts,
            "selected_params": dict(params),
            "games_json_values_forbidden": True,
        }
    )
    return games, pins


def apply_built_rows(pkg: Path, games: Sequence[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    script, params, units = load_frozen_script(pkg)
    for game in games:
        if game.get("_built_by") != BUILT_BY:
            raise AssertionError("B-4b refuse: row was not built by the pinned frozen builder")
        if "delta_margin" in game or "delta_total" in game:
            raise AssertionError("B-4b refuse: built row already has deltas")
    applied = script.apply_params(list(games), params)
    return applied, {"qb1_index_units": units, "selected_params": dict(params), "built_by": BUILT_BY}


def reproduce_le2023_a38a55bb(pkg: Path) -> Dict[str, Any]:
    """IMV-readable check: rebuilt deltas == export a38a55bb."""
    export_path = pkg / "seeded" / "sealed_injury_export_ts_v1.json"
    export_sha = _sha256_file(export_path)
    if export_sha != "a38a55bb765e977ed88f8808d76715faddf50098b2354b122a5499f0ec706ac8":
        raise AssertionError(f"B-4b le2023 export pin drifted {export_sha}")
    games, pins = build_rows(
        pkg,
        listings_dir=pkg / "seeded" / "listings-le2023",
        schedule_path=pkg / "seeded" / "raw-le2023" / "schedule" / "games_reg_le2023.csv",
        rosters_dir=pkg / "seeded" / "raw-le2023" / "rosters",
        pin_le2023_raw=True,
        allowed_listing_years=range(2013, 2024),
    )
    applied, _ = apply_built_rows(pkg, games)
    exp = {g["game_id"]: g for g in json.loads(export_path.read_text(encoding="utf-8"))["games"]}
    n_dm = n_dt = n_miss = 0
    for game in applied:
        gid = f"{int(game['season'])}_{game['week']}_{game['away']}_{game['home']}"
        row = exp.get(gid)
        if row is None:
            n_miss += 1
            continue
        dm, edm = game.get("delta_margin"), row.get("delta_margin")
        dt, edt = game.get("delta_total"), row.get("delta_total")
        if (dm is None) != (edm is None) or (dm is not None and abs(float(dm) - float(edm)) > 1e-12):
            n_dm += 1
        if (dt is None) != (edt is None) or (dt is not None and abs(float(dt) - float(edt)) > 1e-12):
            n_dt += 1
    if n_miss or n_dm or n_dt:
        raise AssertionError(f"B-4b le2023 a38a55bb mismatch miss={n_miss} dm={n_dm} dt={n_dt}")
    return {
        "n_games": len(applied),
        "n_export": len(exp),
        "n_delta_margin_diff": 0,
        "n_delta_total_diff": 0,
        "export_sha": export_sha,
        "pins": {k: pins[k] for k in ("qb1_index_units", "built_by", "frozen_script", "injury_paths_8e2a15ac")},
    }
