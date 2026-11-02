#!/usr/bin/env python3
"""65b1c0fb — emit 2013–2022 pregame rolling EPA features (research only).

CERT_CANDIDATE=0. RESEARCH_DIAGNOSTIC. NFL NO-GO. No F2 / Odds / holdout open.
No production table writes. No EPA win-prob invention.

Builds joinable CSVs for t4422u / historical OOS on
(season, week, home, away) and join_game_id={season}_{week:02d}_{away}_{home}.

Usage:
  python3 data/ops/nfl-epa-wf-feature-emit-65b1c0fb/emit_rolling_2013_2022.py
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

from rolling import (  # noqa: E402
    CERT_CANDIDATE,
    FEATURE_SOURCE,
    ORDER_ID,
    PIT_RULE,
    RESEARCH_LABEL,
    ROLLED_NAME,
    aggregate_team_weeks,
    expand_pregame_to_oos_weeks,
    fmt_num,
    join_oos_games,
    oos_team_from_pbp,
    pbp_team_from_oos,
    sha256_bytes,
)

SEASON_START = 2013
SEASON_END = 2022
OOS_PATH = ROOT / "data/ops/nfl-reopening-packet-20260916/historical-oos/historical_oos_games.csv"
PBP_DIR = Path("/tmp/nflverse_pbp")
PBP_URL = "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{season}.parquet"

TEAM_WEEK_COLS = [
    "season",
    "week",
    "oos_team",
    "pbp_team",
    "games_in_window_3",
    "games_in_window_5",
    "asof_max_week",
    "off_epa_per_play_3g",
    "off_epa_per_play_5g",
    "def_epa_allowed_per_play_3g",
    "def_epa_allowed_per_play_5g",
    "pressure_rate_allowed_3g",
    "pressure_rate_allowed_5g",
    "pressure_rate_generated_3g",
    "pressure_rate_generated_5g",
    "pass_rate_3g",
    "pass_rate_5g",
    "early_down_pass_rate_3g",
    "early_down_pass_rate_5g",
    "red_zone_td_rate_3g",
    "red_zone_td_rate_5g",
    "success_rate_offense_3g",
    "success_rate_offense_5g",
    "success_rate_defense_allowed_3g",
    "success_rate_defense_allowed_5g",
    "pit_rule",
    "source",
    "research_label",
    "cert_candidate",
    "order_id",
]


def _write_blocker(reason: str, detail: Dict[str, Any]) -> Path:
    payload = {
        "order_id": ORDER_ID,
        "label": RESEARCH_LABEL,
        "cert_candidate": CERT_CANDIDATE,
        "scope": "epa_wf_feature_emit_2013_2022",
        "status": "ACCESS_BLOCKED",
        "blocker": reason,
        "detail": detail,
        "warehouse_note": (
            "nfl_dp_team_rolling_features_weekly is warehouse-only and "
            "documented 2023–2026. DATABASE_URL unset on this tip."
        ),
        "not_done": [
            "No production remat",
            "No 2024+ holdout open",
            "No Odds API",
            "No F2 / #641",
            "No EPA win-prob invention",
        ],
    }
    path = HERE / "ACCESS_BLOCKER.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (HERE / "ACCESS_BLOCKER.json.sha256").write_text(
        sha256_bytes(path.read_bytes()) + "  " + path.name + "\n", encoding="utf-8"
    )
    return path


def _load_oos() -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with OOS_PATH.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                season = int(row["season"])
            except (KeyError, TypeError, ValueError):
                continue
            if SEASON_START <= season <= SEASON_END:
                rows.append(row)
    return rows


def _ensure_pbp(seasons: List[int]) -> Tuple[List[Path], Optional[str]]:
    PBP_DIR.mkdir(parents=True, exist_ok=True)
    paths: List[Path] = []
    missing: List[int] = []
    for season in seasons:
        dest = PBP_DIR / f"play_by_play_{season}.parquet"
        if dest.exists() and dest.stat().st_size > 1000:
            paths.append(dest)
            continue
        url = PBP_URL.format(season=season)
        try:
            import urllib.request

            print(f"[pbp] download {season} ← {url}", flush=True)
            urllib.request.urlretrieve(url, dest)
        except Exception as exc:  # noqa: BLE001
            missing.append(season)
            print(f"[pbp] FAIL {season}: {exc}", flush=True)
            continue
        if dest.exists() and dest.stat().st_size > 1000:
            paths.append(dest)
        else:
            missing.append(season)
    if missing:
        return paths, f"nflverse PBP parquet missing/unreadable for seasons {missing}"
    return paths, None


def _team_weeks_via_duckdb(parquet_paths: List[Path]) -> Tuple[List[Dict[str, Any]], Dict[Tuple[int, int, str, str], str]]:
    import duckdb

    con = duckdb.connect()
    files = [str(p) for p in parquet_paths]
    raw = con.execute(
        """
        SELECT
          CAST(season AS INTEGER) AS season,
          CAST(week AS INTEGER) AS week,
          CAST(game_id AS VARCHAR) AS game_id,
          posteam,
          defteam,
          play_type,
          down,
          first_down,
          yardline_100,
          touchdown,
          sack,
          qb_hit,
          passing_yards,
          success,
          epa,
          home_team,
          away_team
        FROM read_parquet(?)
        WHERE season_type IN ('REG', 'POST')
          AND play_type IN ('pass', 'run')
          AND posteam IS NOT NULL
          AND week IS NOT NULL
        """,
        [files],
    ).fetchall()
    cols = [
        "season",
        "week",
        "game_id",
        "posteam",
        "defteam",
        "play_type",
        "down",
        "first_down",
        "yardline_100",
        "touchdown",
        "sack",
        "qb_hit",
        "passing_yards",
        "success",
        "epa",
        "home_team",
        "away_team",
    ]
    plays = [dict(zip(cols, row)) for row in raw]
    print(f"[pbp] pass/run plays={len(plays)}", flush=True)
    team_weeks = aggregate_team_weeks(plays)
    game_ids: Dict[Tuple[int, int, str, str], str] = {}
    for play in plays:
        try:
            season = int(play["season"])
            week = int(play["week"])
        except (TypeError, ValueError):
            continue
        home = oos_team_from_pbp(play.get("home_team"), season)
        away = oos_team_from_pbp(play.get("away_team"), season)
        # store under pbp modern pair as well
        pbp_home = pbp_team_from_oos(home, season)
        pbp_away = pbp_team_from_oos(away, season)
        gid = str(play.get("game_id") or "")
        if gid:
            game_ids[(season, week, pbp_home, pbp_away)] = gid
    return team_weeks, game_ids


def _write_csv(path: Path, fieldnames: List[str], rows: List[Dict[str, Any]]) -> str:
    import io

    fh = io.StringIO()
    w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    for row in rows:
        out = {}
        for col in fieldnames:
            val = row.get(col, "")
            if col in (
                "season",
                "week",
                "games_in_window_3",
                "games_in_window_5",
                "asof_max_week",
                "cert_candidate",
                "home_games_in_window_3",
                "home_games_in_window_5",
                "away_games_in_window_3",
                "away_games_in_window_5",
                "home_asof_max_week",
                "away_asof_max_week",
            ):
                out[col] = "" if val in (None, "") else str(int(val)) if val is not None else ""
            elif isinstance(val, float):
                out[col] = fmt_num(val)
            else:
                out[col] = "" if val is None else val
        w.writerow(out)
    raw = fh.getvalue().encode("utf-8")
    path.write_bytes(raw)
    digest = sha256_bytes(raw)
    path.with_suffix(path.suffix + ".sha256").write_text(
        f"{digest}  {path.name}\n", encoding="utf-8"
    )
    return digest


def _join_fieldnames() -> List[str]:
    cols = [
        "season",
        "week",
        "oos_key",
        "home",
        "away",
        "join_game_id",
        "pbp_game_id",
        "feature_status",
        "research_label",
        "cert_candidate",
        "pit_rule",
        "order_id",
        "epa_home_win_prob",
        "epa_away_win_prob",
        "epa_win_prob_status",
        "epa_win_prob_blocker",
    ]
    for side in ("home", "away"):
        cols.extend(
            [
                f"{side}_games_in_window_3",
                f"{side}_games_in_window_5",
                f"{side}_asof_max_week",
            ]
        )
        for name in ROLLED_NAME.values():
            cols.append(f"{side}_{name}_3g")
            cols.append(f"{side}_{name}_5g")
    return cols


def main() -> int:
    seasons = list(range(SEASON_START, SEASON_END + 1))
    if not OOS_PATH.exists():
        _write_blocker(
            "historical_oos_games.csv missing",
            {"path": str(OOS_PATH)},
        )
        print("ACCESS_BLOCKED: OOS spine missing", file=sys.stderr)
        return 2

    oos = _load_oos()
    print(f"[oos] 2013-2022 games={len(oos)} from {OOS_PATH}", flush=True)

    try:
        import duckdb  # noqa: F401
    except ImportError:
        _write_blocker(
            "duckdb not importable; cannot read nflverse PBP parquet on this tip",
            {
                "fix": "pip install duckdb (research VM only; not a production dep)",
                "pbp_url": PBP_URL,
                "database_url": "UNSET",
            },
        )
        print("ACCESS_BLOCKED: duckdb missing", file=sys.stderr)
        return 3

    paths, err = _ensure_pbp(seasons)
    if err:
        _write_blocker(
            err,
            {
                "pbp_dir": str(PBP_DIR),
                "found": [p.name for p in paths],
                "url": PBP_URL,
                "database_url": "UNSET",
                "warehouse": "nfl_dp_team_rolling_features_weekly only 2023-2026",
            },
        )
        print(f"ACCESS_BLOCKED: {err}", file=sys.stderr)
        return 4

    team_weeks, pbp_ids = _team_weeks_via_duckdb(paths)
    print(f"[agg] team-weeks={len(team_weeks)}", flush=True)
    rolled = expand_pregame_to_oos_weeks(team_weeks, oos)
    for row in rolled:
        row["research_label"] = RESEARCH_LABEL
        row["cert_candidate"] = CERT_CANDIDATE
        row["order_id"] = ORDER_ID
    joined = join_oos_games(oos, rolled, pbp_ids)

    team_path = HERE / "team_week_rolling_pregame_2013_2022.csv"
    join_path = HERE / "games_join_2013_2022.csv"
    team_sha = _write_csv(team_path, TEAM_WEEK_COLS, rolled)
    join_sha = _write_csv(join_path, _join_fieldnames(), joined)

    status_counts: Dict[str, int] = {}
    by_season: Dict[str, int] = {}
    present_both = 0
    for row in joined:
        status_counts[row["feature_status"]] = status_counts.get(row["feature_status"], 0) + 1
        by_season[str(row["season"])] = by_season.get(str(row["season"]), 0) + 1
        if row["feature_status"] == "PRESENT":
            present_both += 1

    manifest = {
        "order_id": ORDER_ID,
        "label": RESEARCH_LABEL,
        "cert_candidate": CERT_CANDIDATE,
        "emitted_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pit_rule": PIT_RULE,
        "feature_source": FEATURE_SOURCE,
        "seasons": f"{SEASON_START}-{SEASON_END}",
        "holdout_2024_plus": "not_opened",
        "oos_spine": str(OOS_PATH.relative_to(ROOT)),
        "oos_games": len(oos),
        "team_week_rows": len(rolled),
        "join_rows": len(joined),
        "feature_status_counts": status_counts,
        "join_rows_by_season": by_season,
        "join_present_n": present_both,
        "pbp_files": {p.name: p.stat().st_size for p in paths},
        "files": {
            team_path.name: team_sha,
            join_path.name: join_sha,
        },
        "join_keys": [
            "season,week,home,away (OOS historical labels)",
            "oos_key (AWAY@HOME)",
            "join_game_id = {season}_{week:02d}_{away}_{home} (t4422u)",
        ],
        "not_emitted": [
            "epa_home_win_prob / epa_away_win_prob (engine call out of scope)",
            "warehouse remat of nfl_dp_team_rolling_features_weekly",
            "2024+ holdout",
        ],
        "constraints": {
            "nfl_board": "NO-GO",
            "coming_soon": True,
            "f2": False,
            "odds_api": False,
            "production_writes": False,
        },
    }
    man_path = HERE / "MANIFEST.json"
    man_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    man_sha = sha256_bytes(man_path.read_bytes())
    (HERE / "MANIFEST.json.sha256").write_text(
        f"{man_sha}  {man_path.name}\n", encoding="utf-8"
    )

    access = {
        "order_id": ORDER_ID,
        "status": "EMITTED",
        "label": RESEARCH_LABEL,
        "cert_candidate": CERT_CANDIDATE,
        "warehouse_table": "nfl_dp_team_rolling_features_weekly NOT mounted (DATABASE_URL unset; documented 2023-2026 only)",
        "backfill_source": "public nflverse PBP parquet (no Odds spend)",
        "pit_rule": PIT_RULE,
        "joinable_csv": str(join_path.relative_to(ROOT)),
        "team_week_csv": str(team_path.relative_to(ROOT)),
        "manifest_sha256": man_sha,
    }
    acc_path = HERE / "ACCESS.json"
    acc_path.write_text(json.dumps(access, indent=2) + "\n", encoding="utf-8")
    (HERE / "ACCESS.json.sha256").write_text(
        sha256_bytes(acc_path.read_bytes()) + "  " + acc_path.name + "\n",
        encoding="utf-8",
    )

    print(f"team_week {team_path.name} sha256={team_sha} n={len(rolled)}")
    print(f"games_join {join_path.name} sha256={join_sha} n={len(joined)}")
    print(f"status={status_counts}")
    print(f"MANIFEST sha256={man_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
