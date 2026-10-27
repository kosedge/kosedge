#!/usr/bin/env python3
"""t4564u EPA walk-forward feature emit (CERT_CANDIDATE=0).

COS_ORDER_CURSOR_t4564u_EPA_WF_FEATURE_EMIT_v1.txt sha8 65b1c0fb.
Alex EPA WF BLOCKED db42ad49: warehouse ``nfl_dp_team_rolling_features_weekly``
is 2023–2026 only and this VM has no RO DATABASE_URL (Railway MCP/OAuth
returns variable *names* only).

This script does **not** invent warehouse rows. It backfills trailing EPA
from public nflverse ``stats_team_week`` 2012–2023 with **strict as-of**:
only games with (season, week) strictly before the target kickoff week,
plus prior-season games for week-1 / thin windows. Last-5 completed games,
play-weighted. Does **not** include the current week's plays (warehouse
default ``ROWS … CURRENT ROW`` leaks same-week EPA; we refuse that).

Then emits a per-game CSV 2013–2023 joinable to walkforward_export_82ffb211
on (season, week, game_id). §2 column order = join keys + PR #638 FIELDNAMES
EPA block (COS order file not in Slack/Linear/Notion/repo; reconstructed).

No Odds API. No merge. No F2 / #641. NFL NO-GO. Never writes /seals/.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
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
from src.services.nfl_season_engine.efficiency_backbone import (  # noqa: E402
    epa_to_strength_indices,
)
from src.services.nfl_simulator import (  # noqa: E402
    DEFAULT_NFL_MODEL_VERSION,
    NflGameInputs,
    simulate_nfl_game,
)
from src.services.nfl_handicapping_framework import (  # noqa: E402
    NFL_HANDICAPPING_FRAMEWORK_VERSION,
)

CERT_CANDIDATE = 0
LABEL = "RESEARCH_DIAGNOSTIC"
TICKET = "t4564u"
COS_ORDER_SHA8 = "65b1c0fb"
ALEX_BLOCK_SHA8 = "db42ad49"
WF_TIP = "82ffb211"
WF_TIP_FULL = "82ffb211d389b20e4d6ec305e4a0466532a48a6d"
GAMES_CSV_SHA256 = "4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8"
SIMULATIONS = 4000
WINDOW = 5
SEED_NAMESPACE = "t4564u-epa-wf-strict-asof"
FILE_MODE = 0o444
SEAL_DEST_MARKERS = ("/seals/", "/seal/", "w8_first_seal", ".seal.json")

# §2: join keys + PR #638 EPA block, this exact order.
SECTION2_COLUMNS = [
    "season",
    "week",
    "game_id",
    "home",
    "away",
    "epa_trailing_spread_home",
    "epa_trailing_total",
    "epa_home_win_prob",
    "epa_away_win_prob",
    "epa_status",
    "epa_blocker",
]

EXTRA_COLUMNS = [
    "kickoff_utc",
    "seed",
    "simulations",
    "epa_window_games_home",
    "epa_window_games_away",
    "home_off_epa_per_play",
    "home_def_epa_allowed_per_play",
    "away_off_epa_per_play",
    "away_def_epa_allowed_per_play",
    "offense_index_home",
    "defense_index_home",
    "offense_index_away",
    "defense_index_away",
    "asof_policy",
    "cert_candidate",
    "research_label",
]

STATS_URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/"
    "stats_team/stats_team_week_{season}.parquet"
)
GAMES_URL = (
    "https://raw.githubusercontent.com/kosedge/kosedge/"
    f"{WF_TIP_FULL}/data/ops/nfl-t4422u-walkforward-pergame-unblended-2013-2023/games.csv"
)

# Franchise members so STL/SD/OAK history follows LAR/LAC/LV.
FRANCHISE_MEMBERS: Dict[str, Tuple[str, ...]] = {
    "LAR": ("LAR", "LA", "STL"),
    "LAC": ("LAC", "SD"),
    "LV": ("LV", "OAK"),
    "WAS": ("WAS", "WSH"),
    "JAX": ("JAX", "JAC"),
}


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
    canon = canonicalize_team(raw) or raw
    return str(canon)


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "kosedge-research/t4564u"})
    with urllib.request.urlopen(req, timeout=180) as res:
        dest.write_bytes(res.read())


def _probe_database_url() -> Dict[str, Any]:
    env_url = (os.environ.get("DATABASE_URL") or "").strip()
    launch = (os.environ.get("LAUNCH_RESEARCH_DATABASE_URL") or "").strip()
    local_ok = False
    local_err = ""
    try:
        import socket

        sock = socket.create_connection(("127.0.0.1", 5432), timeout=0.4)
        sock.close()
        local_ok = True
    except Exception as exc:
        local_err = f"{type(exc).__name__}: {exc}"
    return {
        "DATABASE_URL_present": bool(env_url),
        "LAUNCH_RESEARCH_DATABASE_URL_present": bool(launch),
        "local_5432_accepting": local_ok,
        "local_5432_error": local_err,
        "railway_mcp": {
            "project": "KosEdge",
            "project_id": "da3d68f8-d925-462f-b262-c4ef3e488245",
            "environment": "production",
            "environment_id": "4bf00465-0220-4764-8b3b-e7adce18ca64",
            "model_service_id": "e0c54f94-3ee0-41c0-8081-e96d3e246a4a",
            "postgres_service_id": "4d1abc93-e819-4926-98a0-82feb43b3280",
            "DATABASE_URL_name_present_on_model_service": True,
            "DATABASE_URL_name_present_on_postgres": True,
            "values_readable": False,
            "mcp_note": (
                "Railway list-variables returns names only for this OAuth "
                "connection. Values are not shown to connected apps."
            ),
        },
        "warehouse_rolling_known_coverage": "2023-2026 (HISTORICAL_OOS_DIAGNOSTIC)",
        "blocker_sha8": ALEX_BLOCK_SHA8,
        "repro": [
            "echo DATABASE_URL=${DATABASE_URL:-UNSET}",
            "python3 -c \"import socket; socket.create_connection(('127.0.0.1',5432),0.4)\"",
            "Railway MCP list-variables on model-service / Postgres → names only",
            "scripts/nfl/materialize_team_rolling_features.py --dry-run --seasons 2013,2014 → fails without DSN",
        ],
    }


def _load_stats(cache: Path, seasons: Sequence[int]) -> List[Dict[str, Any]]:
    import pandas as pd

    rows: List[Dict[str, Any]] = []
    for season in seasons:
        dest = cache / f"stats_team_week_{season}.parquet"
        if not dest.is_file() or dest.stat().st_size < 1000:
            _download(STATS_URL.format(season=season), dest)
        df = pd.read_parquet(dest)
        if "season" not in df.columns:
            df["season"] = season
        if "season_type" in df.columns:
            st = df["season_type"].astype(str).str.upper()
            df = df[st.isin(("REG", "REGULAR"))]
        keep = [
            c
            for c in (
                "season",
                "week",
                "game_id",
                "team",
                "opponent_team",
                "opponent",
                "attempts",
                "sacks_suffered",
                "carries",
                "passing_epa",
                "rushing_epa",
            )
            if c in df.columns
        ]
        for data in df[keep].to_dict("records"):
            team = str(data.get("team") or "").strip().upper()
            opp = str(data.get("opponent_team") or data.get("opponent") or "").strip().upper()
            gid = str(data.get("game_id") or "").strip()
            week = int(data.get("week") or 0)
            seas = int(data.get("season") or season)
            if not team or week < 1:
                continue
            plays = (
                float(data.get("attempts") or 0)
                + float(data.get("sacks_suffered") or 0)
                + float(data.get("carries") or 0)
            )
            off_epa = float(data.get("passing_epa") or 0) + float(
                data.get("rushing_epa") or 0
            )
            rows.append(
                {
                    "season": seas,
                    "week": week,
                    "game_id": gid,
                    "team": team,
                    "opp": opp,
                    "franchise": _franchise(team),
                    "plays": plays,
                    "off_epa": off_epa,
                }
            )
    return rows


def _pair_defense(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    by_game_team: Dict[Tuple[str, str], Mapping[str, Any]] = {}
    for r in rows:
        by_game_team[(str(r["game_id"]), str(r["team"]))] = r
    out: List[Dict[str, Any]] = []
    for r in rows:
        opp = by_game_team.get((str(r["game_id"]), str(r["opp"])))
        if opp is None:
            continue
        rec = dict(r)
        rec["def_plays"] = float(opp["plays"])
        rec["def_epa_allowed"] = float(opp["off_epa"])
        out.append(rec)
    return out


def _trailing(
    history: Mapping[str, List[Mapping[str, Any]]],
    *,
    franchise: str,
    season: int,
    week: int,
) -> Optional[Dict[str, Any]]:
    recs = [
        r
        for r in history.get(franchise, [])
        if (int(r["season"]) < season)
        or (int(r["season"]) == season and int(r["week"]) < week)
    ]
    recs = recs[-WINDOW:]
    if not recs:
        return None
    off_plays = sum(float(r["plays"]) for r in recs)
    def_plays = sum(float(r["def_plays"]) for r in recs)
    off_epa = sum(float(r["off_epa"]) for r in recs)
    def_epa = sum(float(r["def_epa_allowed"]) for r in recs)
    if off_plays <= 0 or def_plays <= 0:
        return None
    off_pp = off_epa / off_plays
    def_pp = def_epa / def_plays
    idx = epa_to_strength_indices(off_epa=off_pp, def_epa_allowed=def_pp)
    return {
        "games": len(recs),
        "off_epa_per_play": round(off_pp, 6),
        "def_epa_allowed_per_play": round(def_pp, 6),
        "offense_index": idx["offense_index"],
        "defense_index": idx["defense_index"],
        "first": f"{recs[0]['season']}W{recs[0]['week']}",
        "last": f"{recs[-1]['season']}W{recs[-1]['week']}",
    }


def _stable_seed(game_id: str) -> int:
    digest = hashlib.sha256(f"{game_id}|{SEED_NAMESPACE}".encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % (2**31)


def _load_wf_games(cache: Path) -> List[Dict[str, str]]:
    dest = cache / "walkforward_games_82ffb211.csv"
    if not dest.is_file() or dest.stat().st_size < 1000:
        _download(GAMES_URL, dest)
    digest = _sha256_file(dest)
    if digest != GAMES_CSV_SHA256:
        raise SystemExit(
            f"walkforward games.csv sha256 mismatch: got {digest} want {GAMES_CSV_SHA256}"
        )
    with dest.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if len(rows) != 2992:
        raise SystemExit(f"expected 2992 walkforward games, got {len(rows)}")
    return rows


def main() -> int:
    forecast_ts = _utc_now()
    run_id = f"nfl-epa-wf-2013-2023-{TICKET}-{forecast_ts.strftime('%Y%m%dT%H%M%SZ')}"
    cache = Path("/tmp/nflverse-epa")
    cache.mkdir(parents=True, exist_ok=True)
    dest = ROOT / "data/ops/nfl-t4564u-epa-wf-feature-emit" / run_id
    box = Path("/workspace/ops/nfl_enterprise_green_t4359u/research_runs") / run_id
    code_tip = _git_head()
    db_probe = _probe_database_url()

    wf_rows = _load_wf_games(cache)
    raw_stats = _load_stats(cache, list(range(2012, 2024)))
    paired = _pair_defense(raw_stats)
    history: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for rec in sorted(paired, key=lambda r: (r["season"], r["week"], r["game_id"], r["team"])):
        history[str(rec["franchise"])].append(rec)

    out_rows: List[Dict[str, Any]] = []
    status_counts: Dict[str, int] = defaultdict(int)
    for i, game in enumerate(wf_rows, start=1):
        season = int(game["season"])
        week = int(game["week"])
        home = str(game["home"]).strip().upper()
        away = str(game["away"]).strip().upper()
        gid = str(game["game_id"]).strip()
        ht = _trailing(history, franchise=_franchise(home), season=season, week=week)
        at = _trailing(history, franchise=_franchise(away), season=season, week=week)
        if ht is None or at is None:
            status = "MISSING"
            blocker = (
                "strict_asof_window_empty: no completed nflverse team-week "
                f"EPA before {season}-W{week:02d} for "
                f"{'home' if ht is None else 'away'} "
                f"(warehouse rolling still blocked: {ALEX_BLOCK_SHA8} / "
                "DATABASE_URL unset)"
            )
            row = {
                "season": season,
                "week": week,
                "game_id": gid,
                "home": home,
                "away": away,
                "epa_trailing_spread_home": "",
                "epa_trailing_total": "",
                "epa_home_win_prob": "",
                "epa_away_win_prob": "",
                "epa_status": status,
                "epa_blocker": blocker,
                "kickoff_utc": game.get("kickoff_utc") or "",
                "seed": "",
                "simulations": SIMULATIONS,
                "epa_window_games_home": 0 if ht is None else ht["games"],
                "epa_window_games_away": 0 if at is None else at["games"],
                "home_off_epa_per_play": "",
                "home_def_epa_allowed_per_play": "",
                "away_off_epa_per_play": "",
                "away_def_epa_allowed_per_play": "",
                "offense_index_home": "",
                "defense_index_home": "",
                "offense_index_away": "",
                "defense_index_away": "",
                "asof_policy": "strict_prior_weeks_last5_play_weighted",
                "cert_candidate": CERT_CANDIDATE,
                "research_label": LABEL,
            }
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
            home_off_epa_5g=ht["off_epa_per_play"],
            away_off_epa_5g=at["off_epa_per_play"],
            home_def_epa_allowed_5g=ht["def_epa_allowed_per_play"],
            away_def_epa_allowed_5g=at["def_epa_allowed_per_play"],
        )
        # Do not pass market lines — current-branch simulate_nfl_game blends
        # when lines are present (apply_market_blend flag lives only on #638).
        result = simulate_nfl_game(
            inputs,
            simulations=SIMULATIONS,
            seed=seed,
            model_version=DEFAULT_NFL_MODEL_VERSION,
            apply_linear_totals_calibration=True,
            totals_calibration=None,
        )
        markets = result["markets"]
        status = "ok_nflverse_strict_asof"
        blocker = (
            "warehouse nfl_dp_team_rolling_features_weekly not mounted "
            f"(DATABASE_URL unset; Railway values hidden; Alex {ALEX_BLOCK_SHA8}). "
            "Numbers from nflverse stats_team_week last-5 completed games, "
            "strict week < target, epa_to_strength_indices + simulate_nfl_game. "
            "CERT=0 RESEARCH. Not warehouse rolling."
        )
        row = {
            "season": season,
            "week": week,
            "game_id": gid,
            "home": home,
            "away": away,
            "epa_trailing_spread_home": float(markets["spread_home"]),
            "epa_trailing_total": float(markets["total_mean"]),
            "epa_home_win_prob": float(markets["home_win_prob"]),
            "epa_away_win_prob": float(markets["away_win_prob"]),
            "epa_status": status,
            "epa_blocker": blocker,
            "kickoff_utc": game.get("kickoff_utc") or "",
            "seed": seed,
            "simulations": SIMULATIONS,
            "epa_window_games_home": ht["games"],
            "epa_window_games_away": at["games"],
            "home_off_epa_per_play": ht["off_epa_per_play"],
            "home_def_epa_allowed_per_play": ht["def_epa_allowed_per_play"],
            "away_off_epa_per_play": at["off_epa_per_play"],
            "away_def_epa_allowed_per_play": at["def_epa_allowed_per_play"],
            "offense_index_home": ht["offense_index"],
            "defense_index_home": ht["defense_index"],
            "offense_index_away": at["offense_index"],
            "defense_index_away": at["defense_index"],
            "asof_policy": "strict_prior_weeks_last5_play_weighted",
            "cert_candidate": CERT_CANDIDATE,
            "research_label": LABEL,
        }
        status_counts[status] += 1
        out_rows.append(row)
        if i % 400 == 0 or i == len(wf_rows):
            print(f"[epa-wf] {i}/{len(wf_rows)} status={dict(status_counts)}", flush=True)

    fieldnames = SECTION2_COLUMNS + EXTRA_COLUMNS
    from io import StringIO

    sio = StringIO()
    writer = csv.DictWriter(sio, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(out_rows)
    csv_blob = sio.getvalue().encode("utf-8")

    join_ok = (
        [(r["season"], r["week"], r["game_id"]) for r in out_rows]
        == [(int(g["season"]), int(g["week"]), g["game_id"]) for g in wf_rows]
    )
    if not join_ok:
        raise SystemExit("join key order mismatch vs walkforward_export_82ffb211")

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
        "section2_columns": SECTION2_COLUMNS,
        "section2_source": (
            "PR #638 FIELDNAMES EPA block + join keys; COS file "
            "COS_ORDER_CURSOR_t4564u_EPA_WF_FEATURE_EMIT_v1.txt not in "
            "Slack/Linear/Notion/this repo"
        ),
        "asof_policy": (
            "last 5 completed REG team-weeks with (season,week) < target; "
            "prior season allowed; play-weighted passing_epa+rushing_epa / "
            "(attempts+sacks_suffered+carries); opponent off EPA = def allowed; "
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
        "nfl_nogo": True,
        "coming_soon": True,
    }
    missing = {
        "warehouse_rolling_features_2013_2022": {
            "status": "BLOCKED_AND_BYPASSED_OFFLINE",
            "blocker_sha8": ALEX_BLOCK_SHA8,
            "exact_blocker": db_probe,
            "note": (
                "Could not materialize nfl_dp_team_rolling_features_weekly "
                "2013–2022. Emitted from nflverse stats_team_week instead. "
                "Do not treat as warehouse SoT."
            ),
        },
        "cos_order_file": {
            "status": "NOT_IN_CONNECTED_SOURCES",
            "name": "COS_ORDER_CURSOR_t4564u_EPA_WF_FEATURE_EMIT_v1.txt",
            "sha8": COS_ORDER_SHA8,
            "section2_reconstructed_from": "walkforward_export_82ffb211 FIELDNAMES",
        },
    }

    def _deposit(path: Path) -> Dict[str, str]:
        path.mkdir(parents=True, exist_ok=True)
        _assert_not_seal(path)
        sums: Dict[str, str] = {}
        csv_path = path / "epa_wf_features_2013_2023.csv"
        _write_readonly(csv_path, csv_blob)
        sums[csv_path.name] = _sha256_bytes(csv_blob)
        sums["manifest.json"] = _write_json(path / "manifest.json", manifest)
        sums["MISSING.json"] = _write_json(path / "MISSING.json", missing)
        sums["DATABASE_URL_BLOCKER.json"] = _write_json(
            path / "DATABASE_URL_BLOCKER.json", db_probe
        )
        readme = (
            f"# t4564u EPA WF feature emit\n\n"
            f"run_id: `{run_id}`\n\n"
            f"COS sha8 `{COS_ORDER_SHA8}` · Alex block `{ALEX_BLOCK_SHA8}`\n\n"
            f"tip `{code_tip}` (sha8 `{code_tip[:8]}`)\n\n"
            f"n={len(out_rows)} joinable to walkforward_export_82ffb211 "
            f"on season,week,game_id.\n\n"
            f"status_counts: {json.dumps(dict(status_counts))}\n\n"
            f"CERT_CANDIDATE=0. NFL NO-GO. Warehouse rolling not mounted.\n"
        )
        _write_readonly(path / "README.md", readme.encode())
        sums["README.md"] = _sha256_file(path / "README.md")
        lines = [f"{sha}  {name}" for name, sha in sorted(sums.items())]
        _write_readonly(path / "SHA256SUMS", ("\n".join(lines) + "\n").encode())
        return sums

    repo_sums = _deposit(dest)
    box_sums = _deposit(box)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "repo_path": str(dest.relative_to(ROOT)),
                "box_path": str(box),
                "code_tip_sha8": code_tip[:8],
                "n_games": len(out_rows),
                "status_counts": dict(status_counts),
                "csv_sha256": repo_sums["epa_wf_features_2013_2023.csv"],
                "database_url_present": db_probe["DATABASE_URL_present"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
