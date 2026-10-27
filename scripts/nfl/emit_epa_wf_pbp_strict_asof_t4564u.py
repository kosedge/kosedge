#!/usr/bin/env python3
"""t4564u EPA WF feature emit from nflverse PBP (CERT_CANDIDATE=0).

COS_ORDER_CURSOR_t4564u_EPA_WF_FEATURE_EMIT_v1.txt sha8 65b1c0fb.

Warehouse ``nfl_dp_team_rolling_features_weekly`` 2013–2022 cannot be
materialized on this VM (DATABASE_URL unset; Railway values hidden).
This script does **not** invent warehouse rows.

Instead it rebuilds the data-platform situational week grain from public
nflverse PBP (pass/run, AVG(epa), pressure on dropbacks) and rolls a
**strict as-of** 5-game window: only team-weeks with (season, week)
strictly before the target. Warehouse SQL uses CURRENT ROW (same-week
leakage); we refuse that.

Emit: one row per walkforward_export_82ffb211 games.csv row (2013–2023
REG+POST, n=2992) with **that file's 52 columns in that order**, EPA
block filled. Join key (season, week, game_id) order-identical.

No Odds. No merge. No F2/#641. NFL NO-GO. Never /seals/.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[2]
MS_SRC = ROOT / "services" / "model-service"
if str(MS_SRC) not in sys.path:
    sys.path.insert(0, str(MS_SRC))
_USER_SITE = Path.home() / ".local/lib/python3.12/site-packages"
if _USER_SITE.is_dir() and str(_USER_SITE) not in sys.path:
    sys.path.insert(0, str(_USER_SITE))

from src.services.nfl_canonical_teams import canonicalize_team  # noqa: E402
from src.services.nfl_handicapping_framework import (  # noqa: E402
    NFL_HANDICAPPING_FRAMEWORK_VERSION,
)
from src.services.nfl_season_engine.efficiency_backbone import (  # noqa: E402
    epa_to_strength_indices,
)
from src.services.nfl_simulator import (  # noqa: E402
    DEFAULT_NFL_MODEL_VERSION,
    NflGameInputs,
    simulate_nfl_game,
)

CERT_CANDIDATE = 0
LABEL = "RESEARCH_DIAGNOSTIC"
TICKET = "t4564u"
COS_ORDER_SHA8 = "65b1c0fb"
ALEX_BLOCK_SHA8 = "db42ad49"
WF_TIP_FULL = "82ffb211d389b20e4d6ec305e4a0466532a48a6d"
GAMES_CSV_SHA256 = "4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8"
SIMULATIONS = 4000
WINDOW = 5
SEED_NAMESPACE = "t4564u-epa-wf-pbp-strict-asof"
FILE_MODE = 0o444
SEAL_DEST_MARKERS = ("/seals/", "/seal/", "w8_first_seal", ".seal.json")

PBP_URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/"
    "pbp/play_by_play_{season}.parquet"
)
GAMES_URL = (
    "https://raw.githubusercontent.com/kosedge/kosedge/"
    f"{WF_TIP_FULL}/data/ops/nfl-t4422u-walkforward-pergame-unblended-2013-2023/games.csv"
)

# games.csv column order — COS “columns in that order”
GAMES_COLUMNS = [
    "season",
    "week",
    "game_id",
    "home",
    "away",
    "kickoff_utc",
    "nflverse_gameday",
    "nflverse_gametime",
    "nflverse_location",
    "nflverse_join",
    "record_entering_home",
    "record_entering_away",
    "record_offense_index_home",
    "record_offense_index_away",
    "record_defense_index_home",
    "record_defense_index_away",
    "record_pred_margin_home",
    "record_spread_home",
    "record_total",
    "record_decomp_pred_margin_home",
    "record_decomp_spread_home",
    "record_decomp_total",
    "home_win_prob",
    "away_win_prob",
    "cover_prob",
    "cover_prob_home",
    "over_prob",
    "market_spread_home",
    "market_total",
    "market_line_source",
    "apply_market_blend",
    "research_label",
    "cert_candidate",
    "epa_trailing_spread_home",
    "epa_trailing_total",
    "epa_home_win_prob",
    "epa_away_win_prob",
    "epa_status",
    "epa_blocker",
    "market_blend_applied",
    "injury_overlay",
    "ifb_overlay",
    "personnel_overlay",
    "rest_days_home",
    "rest_days_away",
    "simulations",
    "seed",
    "model_version",
    "framework_version",
    "pit_schedule_path",
    "pit_schedule_sha256",
    "pit_record_rule",
]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _fmt_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_head() -> str:
    out = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=str(ROOT), text=True
    ).strip()
    if not re.fullmatch(r"[0-9a-f]{40}", out):
        raise SystemExit("code_tip_sha unresolved")
    return out


def _assert_not_seal(path: Path) -> None:
    text = str(path.resolve()).replace("\\", "/").lower()
    for marker in SEAL_DEST_MARKERS:
        if marker in text:
            raise SystemExit(f"refuse seal dest write: {path}")


def _write_readonly(path: Path, blob: bytes) -> None:
    _assert_not_seal(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.chmod(0o644)
    path.write_bytes(blob)
    path.chmod(FILE_MODE)


def _write_json(path: Path, payload: Mapping[str, Any]) -> str:
    blob = (json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n").encode()
    _write_readonly(path, blob)
    return _sha256_bytes(blob)


def _franchise(team: str) -> str:
    raw = str(team or "").strip().upper()
    return str(canonicalize_team(raw) or raw)


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "kosedge-research/t4564u"})
    with urllib.request.urlopen(req, timeout=300) as res:
        dest.write_bytes(res.read())


def _probe_database_url() -> Dict[str, Any]:
    local_ok = False
    local_err = ""
    try:
        sock = socket.create_connection(("127.0.0.1", 5432), timeout=0.4)
        sock.close()
        local_ok = True
    except Exception as exc:
        local_err = f"{type(exc).__name__}: {exc}"
    return {
        "DATABASE_URL_present": bool((os.environ.get("DATABASE_URL") or "").strip()),
        "LAUNCH_RESEARCH_DATABASE_URL_present": bool(
            (os.environ.get("LAUNCH_RESEARCH_DATABASE_URL") or "").strip()
        ),
        "local_5432_accepting": local_ok,
        "local_5432_error": local_err,
        "railway_cli": "not_installed",
        "psycopg_importable": _psycopg_ok(),
        "railway_mcp": {
            "project": "KosEdge",
            "project_id": "da3d68f8-d925-462f-b262-c4ef3e488245",
            "environment_id": "4bf00465-0220-4764-8b3b-e7adce18ca64",
            "model_service_id": "e0c54f94-3ee0-41c0-8081-e96d3e246a4a",
            "postgres_service_id": "4d1abc93-e819-4926-98a0-82feb43b3280",
            "DATABASE_URL_name_present": True,
            "values_readable": False,
            "note": "Railway list-variables returns names only for this OAuth app.",
        },
        "warehouse_table": "nfl_dp_team_rolling_features_weekly",
        "warehouse_known_coverage": "2023-2026 (HISTORICAL_OOS_DIAGNOSTIC)",
        "blocker_sha8": ALEX_BLOCK_SHA8,
        "repro": [
            "echo DATABASE_URL=${DATABASE_URL:-UNSET}",
            "python3 -c \"import socket; socket.create_connection(('127.0.0.1',5432),0.4)\"",
            "python3 scripts/nfl/materialize_team_rolling_features.py --dry-run --seasons 2013,2014",
        ],
    }


def _psycopg_ok() -> bool:
    try:
        import psycopg  # noqa: F401

        return True
    except Exception:
        try:
            import psycopg2  # noqa: F401

            return True
        except Exception:
            return False


def _stable_seed(game_id: str) -> int:
    digest = hashlib.sha256(f"{game_id}|{SEED_NAMESPACE}".encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % (2**31)


def _as_bool_series(s: Any):
    if s is None:
        return 0
    if isinstance(s, bool):
        return int(s)
    text = str(s).strip().lower()
    if text in {"1", "true", "t", "yes"}:
        return 1
    try:
        return int(float(s) != 0.0)
    except (TypeError, ValueError):
        return 0


def _load_pbp_week_rows(cache: Path, seasons: Sequence[int]) -> List[Dict[str, Any]]:
    import pandas as pd

    weekly: List[Dict[str, Any]] = []
    keep = [
        "season",
        "week",
        "game_id",
        "posteam",
        "defteam",
        "play_type",
        "epa",
        "sack",
        "qb_hit",
        "season_type",
    ]
    for season in seasons:
        dest = cache / f"play_by_play_{season}.parquet"
        if not dest.is_file() or dest.stat().st_size < 10_000:
            print(f"[pbp] download {season}", flush=True)
            _download(PBP_URL.format(season=season), dest)
        print(f"[pbp] load {season} bytes={dest.stat().st_size}", flush=True)
        import pyarrow.parquet as pq

        schema_names = list(pq.ParquetFile(dest).schema.names)
        present = [c for c in keep if c in schema_names]
        df = pd.read_parquet(dest, columns=present)
        if "season" not in df.columns:
            df["season"] = season
        if "season_type" in df.columns:
            st = df["season_type"].astype(str).str.upper()
            df = df[st.isin(("REG", "POST", "REGULAR", "POSTSEASON"))]
        df = df[df["play_type"].astype(str).isin(("pass", "run"))]
        df = df[df["posteam"].notna() & df["defteam"].notna() & df["week"].notna()]
        df["epa"] = pd.to_numeric(df["epa"], errors="coerce")
        df = df[df["epa"].notna()]
        df["is_pass"] = df["play_type"].astype(str).eq("pass")
        sack = df["sack"].map(_as_bool_series) if "sack" in df.columns else 0
        hit = df["qb_hit"].map(_as_bool_series) if "qb_hit" in df.columns else 0
        df["pressure"] = ((sack + hit) > 0).astype(int)

        off = (
            df.groupby(["season", "week", "posteam"], observed=True)
            .agg(
                off_plays=("epa", "count"),
                off_epa=("epa", "mean"),
                dropbacks=("is_pass", "sum"),
                pressures_allowed=("pressure", "sum"),
            )
            .reset_index()
        )
        deff = (
            df.groupby(["season", "week", "defteam"], observed=True)
            .agg(
                def_plays=("epa", "count"),
                def_epa_allowed=("epa", "mean"),
                dropbacks_faced=("is_pass", "sum"),
                pressures_generated=("pressure", "sum"),
            )
            .reset_index()
        )
        merged = off.merge(
            deff,
            left_on=["season", "week", "posteam"],
            right_on=["season", "week", "defteam"],
            how="outer",
        )
        for rec in merged.to_dict("records"):
            team = str(rec.get("posteam") or rec.get("defteam") or "").strip().upper()
            if not team:
                continue
            dropbacks = float(rec.get("dropbacks") or 0)
            faced = float(rec.get("dropbacks_faced") or 0)
            weekly.append(
                {
                    "season": int(rec["season"]),
                    "week": int(rec["week"]),
                    "team": team,
                    "franchise": _franchise(team),
                    "off_plays": float(rec.get("off_plays") or 0),
                    "off_epa": float(rec["off_epa"]) if rec.get("off_epa") == rec.get("off_epa") else None,
                    "def_plays": float(rec.get("def_plays") or 0),
                    "def_epa_allowed": (
                        float(rec["def_epa_allowed"])
                        if rec.get("def_epa_allowed") == rec.get("def_epa_allowed")
                        else None
                    ),
                    "pressure_rate_allowed": (
                        float(rec.get("pressures_allowed") or 0) / dropbacks
                        if dropbacks > 0
                        else None
                    ),
                    "pressure_rate_generated": (
                        float(rec.get("pressures_generated") or 0) / faced
                        if faced > 0
                        else None
                    ),
                }
            )
        del df, off, deff, merged
    weekly.sort(key=lambda r: (r["franchise"], r["season"], r["week"], r["team"]))
    return weekly


def _mean(vals: Sequence[Optional[float]]) -> Optional[float]:
    clean = [float(v) for v in vals if v is not None]
    if not clean:
        return None
    return sum(clean) / len(clean)


def _rolling_before(
    history: Mapping[str, List[Mapping[str, Any]]],
    *,
    franchise: str,
    season: int,
    week: int,
) -> Optional[Dict[str, Any]]:
    recs = [
        r
        for r in history.get(franchise, [])
        if (int(r["season"]), int(r["week"])) < (season, week)
        and r.get("off_epa") is not None
        and r.get("def_epa_allowed") is not None
    ]
    recs = recs[-WINDOW:]
    if not recs:
        return None
    off = _mean([r["off_epa"] for r in recs])
    deff = _mean([r["def_epa_allowed"] for r in recs])
    if off is None or deff is None:
        return None
    p_all = _mean([r.get("pressure_rate_allowed") for r in recs]) or 0.0
    p_gen = _mean([r.get("pressure_rate_generated") for r in recs]) or 0.0
    idx = epa_to_strength_indices(
        off_epa=off,
        def_epa_allowed=deff,
        pressure_generated=p_gen,
        pressure_allowed=p_all,
    )
    return {
        "games": len(recs),
        "off_epa_per_play_5g": round(off, 6),
        "def_epa_allowed_per_play_5g": round(deff, 6),
        "pressure_rate_allowed_5g": round(p_all, 6),
        "pressure_rate_generated_5g": round(p_gen, 6),
        "offense_index": idx["offense_index"],
        "defense_index": idx["defense_index"],
        "first": f"{recs[0]['season']}W{int(recs[0]['week']):02d}",
        "last": f"{recs[-1]['season']}W{int(recs[-1]['week']):02d}",
    }


def _load_wf_games(cache: Path) -> Tuple[List[Dict[str, str]], List[str]]:
    dest = cache / "walkforward_games_82ffb211.csv"
    if not dest.is_file() or dest.stat().st_size < 1000:
        _download(GAMES_URL, dest)
    digest = _sha256_file(dest)
    if digest != GAMES_CSV_SHA256:
        raise SystemExit(
            f"walkforward games.csv sha256 mismatch: got {digest} want {GAMES_CSV_SHA256}"
        )
    with dest.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        cols = list(reader.fieldnames or [])
        rows = list(reader)
    if cols != GAMES_COLUMNS:
        raise SystemExit(f"games.csv column order drift: {cols}")
    if len(rows) != 2992:
        raise SystemExit(f"expected 2992 walkforward games, got {len(rows)}")
    return rows, cols


def main() -> int:
    forecast_ts = _utc_now()
    run_id = f"nfl-epa-wf-pbp-2013-2023-{TICKET}-{forecast_ts.strftime('%Y%m%dT%H%M%SZ')}"
    cache = Path("/tmp/nflverse-pbp-epa")
    cache.mkdir(parents=True, exist_ok=True)
    dest = ROOT / "data/ops/nfl-t4564u-epa-wf-feature-emit" / run_id
    box = Path("/workspace/ops/nfl_enterprise_green_t4359u/research_runs") / run_id
    code_tip = _git_head()
    db_probe = _probe_database_url()

    wf_rows, cols = _load_wf_games(cache)
    weekly = _load_pbp_week_rows(cache, list(range(2012, 2024)))
    history: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for rec in weekly:
        history[str(rec["franchise"])].append(rec)

    rolling_rows: List[Dict[str, Any]] = []
    seen = set()
    for rec in weekly:
        key = (int(rec["season"]), int(rec["week"]), rec["franchise"])
        if key in seen or int(rec["season"]) < 2013:
            continue
        seen.add(key)
        rolled = _rolling_before(
            history,
            franchise=rec["franchise"],
            season=int(rec["season"]),
            week=int(rec["week"]),
        )
        rolling_rows.append(
            {
                "season": int(rec["season"]),
                "week": int(rec["week"]),
                "team": rec["franchise"],
                "pbp_team": rec["team"],
                "games_in_window_5": 0 if rolled is None else rolled["games"],
                "off_epa_per_play_5g": "" if rolled is None else rolled["off_epa_per_play_5g"],
                "def_epa_allowed_per_play_5g": (
                    "" if rolled is None else rolled["def_epa_allowed_per_play_5g"]
                ),
                "pressure_rate_allowed_5g": (
                    "" if rolled is None else rolled["pressure_rate_allowed_5g"]
                ),
                "pressure_rate_generated_5g": (
                    "" if rolled is None else rolled["pressure_rate_generated_5g"]
                ),
                "asof_policy": "strict_prior_weeks_unweighted_weekly_mean_last5",
                "source": "nflverse_pbp_pass_run_offline",
                "not_warehouse_table": True,
            }
        )

    blocker_note = (
        "warehouse nfl_dp_team_rolling_features_weekly not mounted "
        f"(DATABASE_URL unset; Railway values hidden; Alex {ALEX_BLOCK_SHA8}). "
        "Numbers from nflverse PBP pass/run AVG(epa) weekly means, last-5 "
        "completed team-weeks, strict (season,week) < target, "
        "epa_to_strength_indices + simulate_nfl_game. CERT=0. Not warehouse SoT."
    )
    out_rows: List[Dict[str, Any]] = []
    status_counts: Dict[str, int] = defaultdict(int)
    for i, game in enumerate(wf_rows, start=1):
        season = int(game["season"])
        week = int(game["week"])
        home = str(game["home"]).strip().upper()
        away = str(game["away"]).strip().upper()
        gid = str(game["game_id"]).strip()
        ht = _rolling_before(history, franchise=_franchise(home), season=season, week=week)
        at = _rolling_before(history, franchise=_franchise(away), season=season, week=week)
        row = dict(game)
        row["research_label"] = LABEL
        row["cert_candidate"] = str(CERT_CANDIDATE)
        row["simulations"] = str(SIMULATIONS)
        if ht is None or at is None:
            status = "MISSING"
            row["epa_trailing_spread_home"] = ""
            row["epa_trailing_total"] = ""
            row["epa_home_win_prob"] = ""
            row["epa_away_win_prob"] = ""
            row["epa_status"] = status
            row["epa_blocker"] = (
                "strict_asof_window_empty for "
                f"{'home' if ht is None else 'away'} {season}-W{week:02d}; "
                + blocker_note
            )
            row["seed"] = ""
            status_counts[status] += 1
            out_rows.append(row)
            continue
        seed = _stable_seed(gid)
        inputs = NflGameInputs(
            game_id=gid,
            home_team=home,
            away_team=away,
            offense_index_home=float(ht["offense_index"]),
            offense_index_away=float(at["offense_index"]),
            defense_index_home=float(ht["defense_index"]),
            defense_index_away=float(at["defense_index"]),
            rest_days_home=7.0,
            rest_days_away=7.0,
            home_off_epa_5g=ht["off_epa_per_play_5g"],
            away_off_epa_5g=at["off_epa_per_play_5g"],
            home_def_epa_allowed_5g=ht["def_epa_allowed_per_play_5g"],
            away_def_epa_allowed_5g=at["def_epa_allowed_per_play_5g"],
        )
        result = simulate_nfl_game(
            inputs,
            simulations=SIMULATIONS,
            seed=seed,
            model_version=DEFAULT_NFL_MODEL_VERSION,
            apply_linear_totals_calibration=True,
            totals_calibration=None,
        )
        markets = result["markets"]
        row["epa_trailing_spread_home"] = float(markets["spread_home"])
        row["epa_trailing_total"] = float(markets["total_mean"])
        row["epa_home_win_prob"] = float(markets["home_win_prob"])
        row["epa_away_win_prob"] = float(markets["away_win_prob"])
        row["epa_status"] = "ok_nflverse_pbp_strict_asof"
        row["epa_blocker"] = blocker_note
        row["seed"] = seed
        row["model_version"] = DEFAULT_NFL_MODEL_VERSION
        row["framework_version"] = NFL_HANDICAPPING_FRAMEWORK_VERSION
        status_counts["ok_nflverse_pbp_strict_asof"] += 1
        out_rows.append(row)
        if i % 400 == 0 or i == len(wf_rows):
            print(f"[epa-wf] {i}/{len(wf_rows)} {dict(status_counts)}", flush=True)

    join_ok = (
        [(int(r["season"]), int(r["week"]), r["game_id"]) for r in out_rows]
        == [(int(g["season"]), int(g["week"]), g["game_id"]) for g in wf_rows]
    )
    if not join_ok:
        raise SystemExit("join key order mismatch vs walkforward_export_82ffb211")

    from io import StringIO

    sio = StringIO()
    writer = csv.DictWriter(sio, fieldnames=cols, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(out_rows)
    csv_blob = sio.getvalue().encode("utf-8")

    rsio = StringIO()
    rfields = [
        "season",
        "week",
        "team",
        "pbp_team",
        "games_in_window_5",
        "off_epa_per_play_5g",
        "def_epa_allowed_per_play_5g",
        "pressure_rate_allowed_5g",
        "pressure_rate_generated_5g",
        "asof_policy",
        "source",
        "not_warehouse_table",
    ]
    rw = csv.DictWriter(rsio, fieldnames=rfields, extrasaction="ignore")
    rw.writeheader()
    rw.writerows(rolling_rows)
    rolling_blob = rsio.getvalue().encode("utf-8")

    manifest = {
        "run_id": run_id,
        "ticket": TICKET,
        "cos_order_sha8": COS_ORDER_SHA8,
        "alex_block_sha8": ALEX_BLOCK_SHA8,
        "walkforward_tip": WF_TIP_FULL,
        "walkforward_games_sha256": GAMES_CSV_SHA256,
        "label": LABEL,
        "cert_candidate": CERT_CANDIDATE,
        "forecast_ts_utc": _fmt_utc(forecast_ts),
        "code_tip_sha": code_tip,
        "code_tip_sha8": code_tip[:8],
        "n_games": len(out_rows),
        "column_order": cols,
        "column_order_source": "walkforward_export_82ffb211/games.csv FIELDNAMES (52 cols, this order)",
        "asof_policy": (
            "data-platform situational grain from nflverse PBP play_type in "
            "{pass,run} AVG(epa); rolling = unweighted mean of last 5 weekly "
            "means with (season,week) < target; franchise aliases STL/SD/OAK; "
            "NO current-week leakage"
        ),
        "engine": {
            "function": "src.services.nfl_simulator.simulate_nfl_game",
            "epa_to_indices": "efficiency_backbone.epa_to_strength_indices",
            "model_version": DEFAULT_NFL_MODEL_VERSION,
            "framework_version": NFL_HANDICAPPING_FRAMEWORK_VERSION,
            "simulations": SIMULATIONS,
            "market_blend": False,
            "injury_overlay": False,
            "rest_days": 7.0,
        },
        "status_counts": dict(status_counts),
        "database_probe": db_probe,
        "join_keys": ["season", "week", "game_id"],
        "join_order_matches_82ffb211": True,
        "includes_post": True,
        "warehouse_table_written": False,
        "nfl_nogo": True,
        "coming_soon": True,
    }
    missing = {
        "warehouse_rolling_features_2013_2022": {
            "status": "BLOCKED",
            "blocker_sha8": ALEX_BLOCK_SHA8,
            "exact_blocker": db_probe,
            "offline_bypass": (
                "nflverse PBP → weekly situational → strict-as-of last-5 CSV. "
                "not_warehouse_table=true. Do not treat as DB SoT."
            ),
        },
        "cos_order_file": {
            "status": "NOT_IN_CONNECTED_SOURCES",
            "name": "COS_ORDER_CURSOR_t4564u_EPA_WF_FEATURE_EMIT_v1.txt",
            "sha8": COS_ORDER_SHA8,
            "columns_in_that_order": "walkforward_export_82ffb211/games.csv 52 FIELDNAMES",
        },
    }

    def _deposit(path: Path) -> Dict[str, str]:
        path.mkdir(parents=True, exist_ok=True)
        _assert_not_seal(path)
        sums: Dict[str, str] = {}
        csv_path = path / "epa_wf_features_2013_2023.csv"
        _write_readonly(csv_path, csv_blob)
        sums[csv_path.name] = _sha256_bytes(csv_blob)
        roll_path = path / "rolling_features_weekly_pbp_strict_asof_2013_2023.csv"
        _write_readonly(roll_path, rolling_blob)
        sums[roll_path.name] = _sha256_bytes(rolling_blob)
        sums["manifest.json"] = _write_json(path / "manifest.json", manifest)
        sums["MISSING.json"] = _write_json(path / "MISSING.json", missing)
        sums["DATABASE_URL_BLOCKER.json"] = _write_json(
            path / "DATABASE_URL_BLOCKER.json", db_probe
        )
        readme = (
            f"# t4564u EPA WF PBP strict as-of\n\n"
            f"run_id: `{run_id}`\n\n"
            f"COS sha8 `{COS_ORDER_SHA8}` · Alex block `{ALEX_BLOCK_SHA8}`\n\n"
            f"tip `{code_tip}` (sha8 `{code_tip[:8]}`)\n\n"
            f"n={len(out_rows)} REG+POST joinable to walkforward_export_82ffb211 "
            f"games.csv (52 columns, that order).\n\n"
            f"status_counts: {json.dumps(dict(status_counts))}\n\n"
            f"Warehouse table **not** written. CERT_CANDIDATE=0. NFL NO-GO.\n"
        )
        _write_readonly(path / "README.md", readme.encode())
        sums["README.md"] = _sha256_file(path / "README.md")
        lines = [f"{sha}  {name}" for name, sha in sorted(sums.items())]
        _write_readonly(path / "SHA256SUMS", ("\n".join(lines) + "\n").encode())
        return sums

    repo_sums = _deposit(dest)
    _deposit(box)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "repo_path": str(dest.relative_to(ROOT)),
                "code_tip_sha8": code_tip[:8],
                "n_games": len(out_rows),
                "status_counts": dict(status_counts),
                "csv_sha256": repo_sums["epa_wf_features_2013_2023.csv"],
                "rolling_sha256": repo_sums[
                    "rolling_features_weekly_pbp_strict_asof_2013_2023.csv"
                ],
                "warehouse_table_written": False,
                "database_url_present": db_probe["DATABASE_URL_present"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
