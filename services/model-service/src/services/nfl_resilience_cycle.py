"""Orchestrate NFL weekly resilience cycle from model-service/Celery."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from src.db import SessionLocal
from src.services.nfl_ops_alerts import send_nfl_alert

log = logging.getLogger("kosedge.nfl_resilience_cycle")


def repo_root() -> Path:
    """Resolve repo root locally, or /app in Railway/Docker images."""
    here = Path(__file__).resolve()
    candidates: List[Path] = []
    # parents[i] raises IndexError when i is out of range (was the opaque freshness "4").
    for idx, parent in enumerate(here.parents):
        if idx > 6:
            break
        candidates.append(parent)
    for parent in candidates:
        if (parent / "pnpm-workspace.yaml").exists():
            return parent
        if (parent / "services" / "data-platform-nfl").exists():
            return parent
        if (parent / "data_platform_nfl").exists() and (parent / "src").exists():
            return parent
    if Path("/app/src").exists():
        return Path("/app")
    return candidates[min(2, len(candidates) - 1)] if candidates else Path.cwd()


def resolve_active_season_week() -> Dict[str, Optional[int]]:
    session = SessionLocal()
    try:
        row = session.execute(
            text(
                """
                WITH completed AS (
                  SELECT season, week
                  FROM nfl_dp_schedules
                  WHERE home_score IS NOT NULL AND week IS NOT NULL
                  ORDER BY season DESC, week DESC
                  LIMIT 1
                ),
                upcoming AS (
                  SELECT season, week
                  FROM nfl_dp_schedules
                  WHERE game_date IS NOT NULL
                    AND game_date >= CURRENT_DATE
                    AND week IS NOT NULL
                  ORDER BY game_date ASC, week ASC
                  LIMIT 1
                )
                SELECT
                  COALESCE((SELECT season FROM upcoming), (SELECT season FROM completed)) AS season,
                  COALESCE((SELECT week FROM upcoming), (SELECT week FROM completed)) AS week
                """
            )
        ).fetchone()
        if row is None:
            return {"season": None, "week": None}
        return {
            "season": int(row.season) if row.season is not None else None,
            "week": int(row.week) if row.week is not None else None,
        }
    finally:
        session.close()


def _run(cmd: List[str], *, env: Optional[Dict[str, str]] = None, timeout: int = 60 * 60 * 6) -> Dict[str, Any]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    proc = subprocess.run(
        cmd,
        cwd=str(repo_root()),
        env=merged,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-8000:],
        "stderr_tail": (proc.stderr or "")[-8000:],
        "ok": proc.returncode == 0,
    }


def run_weekly_resilience_cycle(
    *,
    season: Optional[int] = None,
    week: Optional[int] = None,
    skip_player_update: bool = False,
    skip_dr_backup: bool = False,
) -> Dict[str, Any]:
    resolved = resolve_active_season_week()
    season = season or resolved.get("season")
    week = week or resolved.get("week")
    if season is None or week is None:
        payload = {"error": "unable_to_resolve_season_week", "resolved": resolved}
        send_nfl_alert(alert_type="nfl_resilience_cycle_failed", severity="critical", payload=payload)
        return {"status": "failed", **payload}

    script = repo_root() / "scripts" / "nfl" / "run-weekly-resilience-cycle.sh"
    env = {
        "SEASON": str(season),
        "WEEK": str(week),
        "SKIP_PLAYER_UPDATE": "1" if skip_player_update else "0",
        "SKIP_DR_BACKUP": "1" if skip_dr_backup else "0",
        "DATABASE_URL": os.environ.get(
            "DATABASE_URL",
            "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge",
        ),
        "PYTHON_BIN": os.environ.get("PYTHON_BIN", str(repo_root() / ".venv" / "bin" / "python3")),
        "NFL_PG_BIN_DIR": os.environ.get(
            "NFL_PG_BIN_DIR",
            "/usr/local/opt/postgresql@16/bin",
        ),
    }
    result = _run(["bash", str(script)], env=env)
    status = "ok" if result["ok"] else "failed"
    response = {
        "status": status,
        "season": season,
        "week": week,
        "script_result": result,
    }
    if status != "ok":
        send_nfl_alert(
            alert_type="nfl_resilience_cycle_failed",
            severity="critical",
            payload=response,
        )
    else:
        send_nfl_alert(
            alert_type="nfl_resilience_cycle_ok",
            severity="info",
            payload={"season": season, "week": week},
        )
    return response


def _dr_backup_script() -> Path:
    """Prefer the image-bundled script; fall back to monorepo path."""
    bundled = Path("/app/scripts/nfl/run-ownership-dr-backup.sh")
    if bundled.exists():
        return bundled
    local = repo_root() / "scripts" / "nfl" / "run-ownership-dr-backup.sh"
    if local.exists():
        return local
    # model-service checkout layout (path-as-root deploys)
    sibling = Path(__file__).resolve().parents[2] / "scripts" / "nfl" / "run-ownership-dr-backup.sh"
    return sibling


def run_dr_backup_job(*, skip_verify: bool = False) -> Dict[str, Any]:
    script = _dr_backup_script()
    default_pg_bin = "/usr/bin" if Path("/app/src").exists() else "/usr/local/opt/postgresql@16/bin"
    env = {
        "SKIP_VERIFY": "1" if skip_verify else "0",
        # Local disk backup clears freshness; remote upload is optional via NFL_DR_REMOTE_URI.
        "SKIP_UPLOAD": os.environ.get("SKIP_UPLOAD", "0" if os.environ.get("NFL_DR_REMOTE_URI") else "1"),
        "DATABASE_URL": os.environ.get(
            "DATABASE_URL",
            "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge",
        ),
        "PYTHON_BIN": os.environ.get("PYTHON_BIN") or sys.executable,
        "NFL_PG_BIN_DIR": os.environ.get("NFL_PG_BIN_DIR", default_pg_bin),
    }
    if not script.exists():
        return {
            "status": "failed",
            "error": "dr_backup_script_missing",
            "script": str(script),
        }
    result = _run(["bash", str(script)], env=env)
    status = "ok" if result["ok"] else "failed"
    response = {"status": status, "script_result": result}
    if status != "ok":
        send_nfl_alert(alert_type="nfl_dr_backup_failed", severity="critical", payload=response)
    return response


def run_data_freshness_check(*, persist_alert: bool = True) -> Dict[str, Any]:
    root = repo_root()
    # Prefer the running interpreter (Railway/Docker). The monorepo .venv path
    # does not exist in production images and previously surfaced as opaque errors.
    python_bin = os.environ.get("PYTHON_BIN") or sys.executable
    dp_src = root / "services" / "data-platform-nfl" / "src"
    # Vendored package lives at /app/data_platform_nfl in production images.
    pythonpath_parts = [str(p) for p in (dp_src, root) if p.exists()]
    env = {
        "DATABASE_URL": os.environ.get(
            "DATABASE_URL",
            "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge",
        ),
        "PYTHONPATH": os.pathsep.join(
            pythonpath_parts + ([os.environ["PYTHONPATH"]] if os.environ.get("PYTHONPATH") else [])
        ),
    }
    # Compact single-line JSON avoids truncation issues from pretty CLI output.
    result = _run(
        [
            python_bin,
            "-c",
            (
                "import json; from data_platform_nfl.freshness import evaluate_data_freshness; "
                "print(json.dumps(evaluate_data_freshness(), default=str))"
            ),
        ],
        env=env,
        timeout=120,
    )
    payload: Dict[str, Any] = {
        "status": "failed",
        "script_result": {
            "ok": result.get("ok"),
            "returncode": result.get("returncode"),
            "stderr_tail": (result.get("stderr_tail") or "")[-1200:],
            "stdout_tail": (result.get("stdout_tail") or "")[-1200:],
            "python_bin": python_bin,
        },
    }
    if result["ok"]:
        raw_out = (result.get("stdout_tail") or "").strip()
        start = raw_out.find("{")
        end = raw_out.rfind("}")
        try:
            payload = json.loads(raw_out[start : end + 1] if start >= 0 and end > start else raw_out)
        except Exception:
            payload = {"status": "unknown", "raw": raw_out[-4000:]}

    status = str(payload.get("status") or "failed")
    ops_status = str(payload.get("ops_status") or "ok") if isinstance(payload, dict) else "ok"
    ops_blockers = payload.get("ops_blockers") if isinstance(payload, dict) else None
    # Board degradation or ops-only DR failures both warrant ops alerts.
    # Guest product status may still be ok when only ops_blockers are present.
    if persist_alert and (status != "ok" or ops_status != "ok" or ops_blockers):
        alert_status = status if status != "ok" else f"ops_{ops_status}"
        send_nfl_alert(
            alert_type="nfl_data_freshness_degraded",
            severity="warning" if alert_status in {"degraded", "ops_degraded"} else "critical",
            payload=payload if isinstance(payload, dict) else {"payload": payload},
        )
    return payload if isinstance(payload, dict) else {"status": status, "payload": payload}
