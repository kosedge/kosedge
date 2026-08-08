#!/usr/bin/env python3
"""Materialize NFL team rolling / matchup features (Sprint 2 live path).

Railway ``nfl_dp_team_rolling_features_weekly`` was empty after Hobby wipe —
season engine / Edge Board fell back to packaged priors. This script rebuilds
rolling 3g/5g features from ``nfl_dp_team_situational_weekly`` via the existing
data-platform materializer (no parallel system).

Usage:
  # Dry-run: count situational vs rolling, do not write
  python scripts/nfl/materialize_team_rolling_features.py --dry-run

  # Materialize seasons (calls data_platform_nfl.cli)
  python scripts/nfl/materialize_team_rolling_features.py --seasons 2023,2024,2025,2026

  # Also rebuild packaged efficiency backbone JSON
  python scripts/nfl/materialize_team_rolling_features.py --seasons 2025 --rebuild-packaged

Env:
  DATABASE_URL / LAUNCH_RESEARCH_DATABASE_URL for remote targets (Railway).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
DP = ROOT / "services" / "data-platform-nfl"


def _connect(dsn: str):
    try:
        import psycopg

        return psycopg.connect(dsn)
    except Exception:
        import psycopg2

        return psycopg2.connect(dsn)


def _candidate_dsns(explicit: Optional[str]) -> List[str]:
    out: List[str] = []
    if explicit:
        out.append(explicit)
    out.append("postgresql://ryankos:postgres@127.0.0.1:5432/kosedge")
    for key in ("LAUNCH_RESEARCH_DATABASE_URL", "DATABASE_URL"):
        raw = (os.getenv(key) or "").strip()
        if not raw:
            continue
        raw = raw.replace("postgresql+psycopg://", "postgresql://").replace(
            "postgresql+psycopg2://", "postgresql://"
        )
        if raw not in out:
            out.append(raw)
    return out


def _inventory(conn: Any, seasons: List[int]) -> Dict[str, Any]:
    cur = conn.cursor()
    inv: Dict[str, Any] = {"seasons": {}}
    for season in seasons:
        cur.execute(
            "SELECT COUNT(*) FROM nfl_dp_team_situational_weekly WHERE season = %s",
            (season,),
        )
        situational = int(cur.fetchone()[0] or 0)
        cur.execute(
            "SELECT COUNT(*) FROM nfl_dp_team_rolling_features_weekly WHERE season = %s",
            (season,),
        )
        rolling = int(cur.fetchone()[0] or 0)
        cur.execute(
            "SELECT COUNT(*) FROM nfl_dp_matchup_features_weekly WHERE season = %s",
            (season,),
        )
        matchup = int(cur.fetchone()[0] or 0)
        cur.execute(
            """
            SELECT COUNT(DISTINCT team)
            FROM nfl_dp_team_rolling_features_weekly
            WHERE season = %s
            """,
            (season,),
        )
        teams = int(cur.fetchone()[0] or 0)
        inv["seasons"][str(season)] = {
            "situational_rows": situational,
            "rolling_rows": rolling,
            "matchup_rows": matchup,
            "rolling_teams": teams,
        }
    cur.close()
    return inv


def _run_materialize(seasons: List[int], *, replace: bool) -> int:
    seasons_arg = ",".join(str(s) for s in seasons)
    cmd = [
        sys.executable,
        "-m",
        "data_platform_nfl.cli",
        "--seasons",
        seasons_arg,
        "--materialize-matchup-features",
    ]
    if replace:
        cmd.append("--replace-matchup-features")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(DP / "src") + (
        os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
    )
    print(f"[materialize] {' '.join(cmd)}", flush=True)
    proc = subprocess.run(cmd, cwd=str(DP), env=env, check=False)
    return int(proc.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seasons", default="2023,2024,2025,2026")
    parser.add_argument("--dsn", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--replace", action="store_true", default=True)
    parser.add_argument("--no-replace", action="store_true")
    parser.add_argument("--rebuild-packaged", action="store_true")
    parser.add_argument("--packaged-season", type=int, default=2026)
    args = parser.parse_args()
    seasons = [int(x.strip()) for x in str(args.seasons).split(",") if x.strip()]
    replace = bool(args.replace) and not bool(args.no_replace)

    used_dsn = ""
    inv: Dict[str, Any] = {}
    last_err: Optional[Exception] = None
    for candidate in _candidate_dsns(args.dsn or None):
        try:
            with _connect(candidate) as conn:
                inv = _inventory(conn, seasons)
            used_dsn = candidate.split("@")[-1] if "@" in candidate else candidate
            break
        except Exception as exc:
            last_err = exc
            continue
    if not inv:
        raise SystemExit(f"Could not inventory DB. last_err={last_err}")

    report = {
        "dsn_host": used_dsn,
        "dry_run": bool(args.dry_run),
        "before": inv,
    }
    print(json.dumps(report, indent=2))

    empty_rolling = [
        s
        for s, row in inv["seasons"].items()
        if int(row.get("rolling_rows") or 0) == 0
        and int(row.get("situational_rows") or 0) > 0
    ]
    if empty_rolling:
        print(
            f"[materialize] seasons with situational but empty rolling: {empty_rolling}",
            flush=True,
        )

    if args.dry_run:
        print("[materialize] dry-run complete (no writes)")
        return

    rc = _run_materialize(seasons, replace=replace)
    if rc != 0:
        raise SystemExit(f"materialize failed rc={rc}")

    after: Dict[str, Any] = {}
    for candidate in _candidate_dsns(args.dsn or None):
        try:
            with _connect(candidate) as conn:
                after = _inventory(conn, seasons)
            break
        except Exception:
            continue
    print(json.dumps({"after": after}, indent=2))

    if args.rebuild_packaged:
        build_script = ROOT / "scripts" / "nfl" / "build_packaged_efficiency_backbone.py"
        cmd = [
            sys.executable,
            str(build_script),
            "--season",
            str(int(args.packaged_season)),
        ]
        if args.dsn:
            cmd.extend(["--dsn", args.dsn])
        print(f"[materialize] rebuilding packaged backbone: {' '.join(cmd)}", flush=True)
        subprocess.run(cmd, check=True)

    print("[materialize] done")


if __name__ == "__main__":
    main()
