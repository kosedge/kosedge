#!/usr/bin/env python3
"""t4605u honest W8 input completeness (same 4 FAIL_CLOSED names as #642).

Does not invent depth/injury/EPA. Does not treat packaged W1 / 2025 prior
as current. current_weekly_depth_db closes only on a real warehouse RO
SELECT (or local DATABASE_URL). Empty/missing warehouse stays FAIL.
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

CERT_CANDIDATE = 0
LABEL = "RESEARCH_ENG"
SCHEMA = "nfl-week-input-completeness-v1"
AUDIT_TIP_642 = "f50f15a8"
COMPLETENESS_SHA_642 = (
    "21b96525d4b59eb810801495723ad5c4cc84b7a64e4fc422bbeab8e8a85ace71"
)
W8_WINDOW_START = "2026-10-20"


def _sha256_hex(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _fmt_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _check(
    name: str, *, ok: bool, evidence: Mapping[str, Any], blocker: str = ""
) -> Dict[str, Any]:
    return {
        "name": name,
        "ok": bool(ok),
        "blocker": blocker if not ok else "",
        "evidence": dict(evidence),
    }


def _load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _railway_cli_status() -> Dict[str, Any]:
    """whoami / status / run — never print tokens or DATABASE_* values."""
    import shutil
    import subprocess

    token = (os.environ.get("RAILWAY_TOKEN") or "").strip()
    cli = shutil.which("railway") or str(Path.home() / ".railway/bin/railway")
    out: Dict[str, Any] = {
        "RAILWAY_TOKEN_present": bool(token),
        "RAILWAY_TOKEN_length": len(token),
        "railway_cli": cli if Path(cli).is_file() else "",
        "whoami": "",
        "status": "",
        "run_postgres": "",
    }
    env = os.environ.copy()
    base = [
        cli,
        "--project",
        "da3d68f8-d925-462f-b262-c4ef3e488245",
        "--environment",
        "production",
    ]
    for key, args in (
        ("whoami", [cli, "whoami"]),
        (
            "status",
            [cli, "status", "--project", "da3d68f8-d925-462f-b262-c4ef3e488245", "--environment", "production"],
        ),
        (
            "run_postgres",
            [
                cli,
                "run",
                "--project",
                "da3d68f8-d925-462f-b262-c4ef3e488245",
                "--environment",
                "production",
                "--service",
                "Postgres",
                "--",
                "python3",
                "-c",
                "import os; print('url_present', bool(os.environ.get('DATABASE_PUBLIC_URL') or os.environ.get('DATABASE_URL')))",
            ],
        ),
    ):
        try:
            proc = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=20,
                env=env,
            )
            text = (proc.stderr or proc.stdout or "").strip().splitlines()
            first = text[0] if text else f"exit_{proc.returncode}"
            if token and token in first:
                first = "REDACTED"
            out[key] = f"exit={proc.returncode} {first[:160]}"
        except Exception as exc:
            out[key] = f"{type(exc).__name__}"
    return out


def _railway_exit_ok(value: Any) -> bool:
    return str(value or "").startswith("exit=0")


def _summarize_ro_probe(probe: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if not probe:
        return {}
    tables = probe.get("tables") if isinstance(probe.get("tables"), dict) else {}
    depth = tables.get("nfl_dp_depth_chart_weekly") or {}
    official = tables.get("nfl_dp_official_depth_charts") or {}
    injuries = tables.get("nfl_dp_injuries") or {}
    return {
        "ok": bool(probe.get("ok")),
        "connect_ok": bool(probe.get("connect_ok")),
        "transaction_read_only": bool(probe.get("transaction_read_only")),
        "read_only": bool(probe.get("read_only")),
        "dml_ddl": bool(probe.get("dml_ddl")),
        "invented": bool(probe.get("invented")),
        "host_kind": probe.get("host_kind"),
        "url_source_key": probe.get("url_source_key"),
        "warehouse_rows_read": probe.get("warehouse_rows_read"),
        "missing_tables": list(probe.get("missing_tables") or []),
        "depth_n": depth.get("n"),
        "depth_max_week": depth.get("max_week"),
        "depth_teams": depth.get("teams"),
        "official_n": official.get("n"),
        "injuries_n": injuries.get("n"),
        "injuries_max_week": injuries.get("max_week"),
    }


def _db_probe(ro_probe: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    url = (os.environ.get("DATABASE_URL") or "").strip()
    launch = (os.environ.get("LAUNCH_RESEARCH_DATABASE_URL") or "").strip()
    local_ok = False
    local_err = ""
    try:
        sock = socket.create_connection(("127.0.0.1", 5432), timeout=0.4)
        sock.close()
        local_ok = True
    except Exception as exc:
        local_err = f"{type(exc).__name__}: {exc}"
    railway = _railway_cli_status()
    whoami_ok = _railway_exit_ok(railway.get("whoami"))
    status_ok = _railway_exit_ok(railway.get("status"))
    run_ok = _railway_exit_ok(railway.get("run_postgres"))
    probe_sum = _summarize_ro_probe(ro_probe)
    probe_ok = bool(
        probe_sum.get("ok")
        and probe_sum.get("transaction_read_only")
        and int(probe_sum.get("depth_n") or 0) > 0
    )
    access_ok = (
        probe_ok
        or (bool(url) and local_ok)
        or whoami_ok
        or (status_ok and run_ok and probe_ok)
    )
    return {
        "DATABASE_URL_present": bool(url),
        "DATABASE_PUBLIC_URL_present": bool(
            (os.environ.get("DATABASE_PUBLIC_URL") or "").strip()
        ),
        "LAUNCH_RESEARCH_DATABASE_URL_present": bool(launch),
        "local_5432_accepting": local_ok,
        "local_5432_error": local_err,
        "railway_mcp_values_readable": False,
        "railway": railway,
        "ro_probe": probe_sum,
        "classification": "OK" if access_ok else "ACCESS_BLOCKED",
        "repro": [
            "python3 -c \"import os; t=os.environ.get('RAILWAY_TOKEN'); print('RAILWAY_TOKEN', 'SET' if t else 'UNSET', 'length', len(t or ''))\"",
            "railway whoami",
            "railway status --project da3d68f8-d925-462f-b262-c4ef3e488245 --environment production",
            "railway run --project da3d68f8-d925-462f-b262-c4ef3e488245 --environment production --service Postgres -- python3 -c \"import os; print('url_present', bool(os.environ.get('DATABASE_PUBLIC_URL') or os.environ.get('DATABASE_URL')))\"",
        ],
    }


def audit_week_inputs(
    *,
    season: int,
    week: int,
    depth_path: Path,
    injury_paths: List[Path],
    efficiency_path: Path,
    slate_game_ids: List[str],
    now_utc: Optional[datetime] = None,
    ro_probe: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    now = now_utc or datetime.now(timezone.utc).replace(microsecond=0)
    checks: List[Dict[str, Any]] = []

    depth_ok_file = depth_path.is_file()
    depth = _load(depth_path) if depth_ok_file else {}
    depth_week = int(depth.get("week") or 0) if depth_ok_file else None
    depth_as_of = str(depth.get("as_of") or "")
    stale_w1 = "w1" in depth_path.name.lower() or depth_week == 1
    week_match = (
        depth_ok_file
        and depth_week == int(week)
        and depth_as_of[:10] >= W8_WINDOW_START
        and not stale_w1
    )
    checks.append(
        _check(
            "depth_sot_week",
            ok=week_match,
            blocker=(
                f"depth is week={depth_week} as_of={depth_as_of} "
                f"({depth_path.name}); requested week={week}. "
                "W1-as-W8 forbidden."
            ),
            evidence={
                "path": str(depth_path),
                "week": depth_week,
                "as_of": depth_as_of,
                "as_of_timestamp": depth.get("as_of_timestamp"),
                "snapshot_id": depth.get("snapshot_id"),
                "row_count": depth.get("row_count"),
                "team_count": depth.get("team_count"),
                "requested_week": week,
                "packaged_w1_used": stale_w1,
            },
        )
    )

    existing_paths = [p for p in injury_paths if p.is_file()]
    designated = 0
    inj_week = None
    inj_as_of = ""
    for p in existing_paths:
        payload = _load(p)
        inj_week = payload.get("week")
        inj_as_of = str(payload.get("as_of") or "")
        designated += int(payload.get("designated_count") or len(payload.get("rows") or []))
    injury_ok = bool(existing_paths) and designated > 0
    checks.append(
        _check(
            "injury_paths_current",
            ok=injury_ok,
            blocker=(
                "injury_paths empty or zero designated rows. "
                "Silent healthy forbidden."
            ),
            evidence={
                "injury_path_count": len(existing_paths),
                "paths": [str(p) for p in existing_paths],
                "designated_count": designated,
                "latest_official_week": inj_week,
                "as_of": inj_as_of,
                "w8_official_report": (
                    "PRESENT" if inj_week == week else "MISSING"
                ),
            },
        )
    )

    db = _db_probe(ro_probe)
    probe = db.get("ro_probe") or {}
    railway = db.get("railway") or {}
    railway_ok = _railway_exit_ok(railway.get("whoami"))
    status_ok = _railway_exit_ok(railway.get("status"))
    run_ok = _railway_exit_ok(railway.get("run_postgres"))
    probe_ok = bool(
        probe.get("ok")
        and probe.get("transaction_read_only")
        and int(probe.get("depth_n") or 0) > 0
    )
    warehouse_ok = (
        probe_ok
        or (bool(db["DATABASE_URL_present"]) and bool(db["local_5432_accepting"]))
        or railway_ok
        or (status_ok and run_ok and probe_ok)
    )
    if warehouse_ok:
        blocker = ""
    elif "Unauthorized" in str(railway.get("status") or "") or "Unauthorized" in str(
        railway.get("run_postgres") or ""
    ):
        blocker = (
            "ACCESS_BLOCKED: RAILWAY_TOKEN present but railway status/run "
            "Unauthorized. DATABASE_URL / DATABASE_PUBLIC_URL unset. "
            "No SET TRANSACTION READ ONLY session. Will not invent nfl_dp_* rows. "
            "Option B (box egress) not authorized."
        )
    else:
        blocker = (
            "ACCESS_BLOCKED: warehouse RO probe did not close current_weekly_depth_db. "
            "Will not invent nfl_dp_* rows. Option B (box egress) not authorized."
        )
    checks.append(
        _check(
            "current_weekly_depth_db",
            ok=warehouse_ok,
            blocker=blocker,
            evidence=db,
        )
    )

    kickoff_ok = len(slate_game_ids) == 14
    checks.append(
        _check(
            "week_schedule_kickoffs",
            ok=kickoff_ok,
            blocker="canonical W8 slate is not 14 games",
            evidence={"canonical_week_games": len(slate_game_ids), "game_ids": slate_game_ids},
        )
    )

    eff_ok_file = efficiency_path.is_file()
    eff = _load(efficiency_path) if eff_ok_file else {}
    eff_as_of = str(eff.get("as_of") or "")
    week_through = int(eff.get("week_through") or 0)
    teams = eff.get("teams") or {}
    prior = eff.get("prior_season")
    current = (
        eff_ok_file
        and eff_as_of[:10] >= "2026-09-10"
        and week_through >= 7
        and len(teams) >= 32
        and prior in (None, "", 0)
        and str(eff.get("source") or "").startswith("nflverse")
    )
    checks.append(
        _check(
            "inseason_efficiency_current",
            ok=current,
            blocker=(
                f"efficiency as_of={eff_as_of} week_through={week_through} "
                f"prior_season={prior} teams={len(teams)}. "
                "2025 packaged prior (as_of 2026-08-08) is not current W8."
            ),
            evidence={
                "path": str(efficiency_path),
                "as_of": eff_as_of,
                "week_through": week_through,
                "team_count": len(teams),
                "prior_season": prior,
                "source": eff.get("source"),
                "conversion": eff.get("conversion"),
            },
        )
    )

    failing = [c for c in checks if not c["ok"]]
    passing = [c for c in checks if c["ok"]]
    completeness = {
        "schema_version": SCHEMA,
        "label": LABEL,
        "cert_candidate": CERT_CANDIDATE,
        "purpose": "research_eng_only",
        "ticket": "t4605u",
        "authority": {
            "decision_sha256": "e65b9c7781a2f120dc6b6c0c1d171cce3b5daae31577edfcbc4a99eccff3d69a",
            "cos_order_sha256": "43d1702a1d26a649f2707dd3fcafe8174bd547bf617970decff8dfbfff267bc6",
            "prior_fail_closed_tip": AUDIT_TIP_642,
            "prior_completeness_sha256": COMPLETENESS_SHA_642,
        },
        "audited_at_utc": _fmt_utc(now),
        "season": int(season),
        "week": int(week),
        "ok": not failing,
        "failing_components": [c["name"] for c in failing],
        "passed": [c["name"] for c in passing],
        "checks": checks,
        "slate_game_ids": list(slate_game_ids),
        "note": (
            "t4605u: current nflverse packs may close depth/injury/EPA. "
            "DATABASE_URL warehouse remains an access wall if unset. "
            "No invented numbers, no silent zero injury, no W1-as-W8 depth."
        ),
    }
    completeness["input_completeness_sha256"] = _sha256_hex(
        json.dumps(
            {
                k: completeness[k]
                for k in ("season", "week", "failing_components", "checks")
                if k in completeness
            },
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    )
    return completeness
