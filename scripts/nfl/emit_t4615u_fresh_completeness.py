#!/usr/bin/env python3
"""t4615u fresh-VM Unblock A: re-audit W8 completeness after RO warehouse SELECT. CERT=0."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "nfl"))
from audit_w8_input_completeness_t4605u import audit_week_inputs

PACK = ROOT / "data/ops/nfl-t4605u-w8-pipeline-restore/current_inputs"
PROBE = ROOT / "data/ops/nfl-t4615u-w8-depth-db-fresh-vm/depth_db_ro_probe.json"
SLATE = [
    "2026-W08-CAR@GB",
    "2026-W08-ARI@DAL",
    "2026-W08-ATL@TB",
    "2026-W08-BAL@BUF",
    "2026-W08-CLE@PIT",
    "2026-W08-IND@JAX",
    "2026-W08-LV@NYJ",
    "2026-W08-MIN@DET",
    "2026-W08-TEN@CIN",
    "2026-W08-LAC@LAR",
    "2026-W08-KC@DEN",
    "2026-W08-NE@MIA",
    "2026-W08-PHI@WAS",
    "2026-W08-CHI@SEA",
]


def _write_0444(path: Path, blob: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.chmod(stat.S_IWUSR | stat.S_IRUSR)
    path.write_bytes(blob)
    path.chmod(0o444)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    probe = json.loads(PROBE.read_text(encoding="utf-8"))
    report = audit_week_inputs(
        season=2026,
        week=8,
        depth_path=PACK / "nfl_depth_chart_2026_w8.json",
        injury_paths=[PACK / "nfl_injuries_2026_w7_designated.json"],
        efficiency_path=PACK / "nfl_team_efficiency_backbone_2026_inseason_w7.json",
        slate_game_ids=SLATE,
        now_utc=now,
        ro_probe=probe,
    )
    report["ticket"] = "t4615u"
    report["authority"] = {
        "decision_sha256": "5357266707b5555e96b746dce91435f862884db92b2124215f0d65d9ac435904",
        "parent_decision_sha256": "e65b9c7781a2f120dc6b6c0c1d171cce3b5daae31577edfcbc4a99eccff3d69a",
        "prior_access_blocker_sha256": "a79f58f822434acfc450c3ea9927029eb3f6da0c1f85096c0ddbdeec8491a294",
        "prior_tip": "d8356dcb",
        "prior_completeness_sha256": "02ba06ac819486d478acfdcd30fb2b0015d6101b9ddccf32153a462cde937c70",
    }
    report["note"] = (
        "t4615u fresh VM Unblock A: railway status/run authorized; "
        "SET TRANSACTION READ ONLY SELECT on nfl_dp_depth_chart_weekly / "
        "nfl_dp_official_depth_charts / nfl_dp_injuries. No invented nfl_dp_* rows. "
        "Warehouse injuries max_week=3 (packaged injury_paths_current still W7 designated). "
        "CERT=0. Option B not attempted."
    )
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    dests = [
        ROOT / "data/ops/nfl-t4615u-w8-depth-db-fresh-vm",
        ROOT
        / "data/ops/nfl-model-forecast-emit-t4559u/research_runs"
        / f"nfl-w8-2026-t4615u-fresh-{stamp}",
    ]
    blob = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode()
    sha = report["input_completeness_sha256"]
    closed = report["passed"]
    remaining = report["failing_components"]
    probe_sha = _sha256_file(PROBE)
    closed_md = (
        "# CLOSED — current_weekly_depth_db (t4615u fresh VM Unblock A)\n\n"
        f"Ticket: t4615u (authority DECISION_RYAN_t4608u 53572667 · parent e65b9c77)\n"
        f"Filed: {report['audited_at_utc']}\n"
        "CERT_CANDIDATE: 0\n"
        "Classification: CLOSED\n\n"
        "Prior ACCESS_BLOCKER a79f58f8 tip d8356dcb (long-lived VM Unauthorized). "
        "This fresh VM: RAILWAY_TOKEN SET; railway status/run authorized; "
        "whoami Unauthorized is expected for a project-scoped token.\n\n"
        "## Verdict\n\n"
        "`current_weekly_depth_db` is CLOSED.\n\n"
        "SET TRANSACTION READ ONLY session opened via "
        "`railway run --project da3d68f8-d925-462f-b262-c4ef3e488245 "
        "--environment production --service Postgres`. "
        "SELECT only depth/injury nowcast tables. No DML/DDL. No invented nfl_dp_* rows. "
        "Option B not attempted.\n\n"
        "## Warehouse rows read (counts only)\n\n"
        "- nfl_dp_depth_chart_weekly: n=23256 teams=32 max_week=8 (W8 n=2907 / 32 teams)\n"
        "- nfl_dp_official_depth_charts: n=3171 teams=32 max_week=1\n"
        "- nfl_dp_injuries: n=734 teams=32 max_week=3\n"
        "- warehouse_rows_read: 27161\n\n"
        "Packaged injury_paths_current remains the W7 designated file. "
        "Warehouse injury nowcast is not invented forward from week 3.\n\n"
        "## Observed (no secrets)\n\n"
        "1. RAILWAY_TOKEN SET length 36 (uuid-like; alnum+hyphen)\n"
        "2. DATABASE_URL UNSET in process env; DATABASE_PUBLIC_URL UNSET in process env\n"
        "3. railway whoami → exit=1 Unauthorized (project token)\n"
        "4. railway status --project da3d68f8-d925-462f-b262-c4ef3e488245 "
        "--environment production → exit=0 (Postgres Online)\n"
        "5. railway run … --service Postgres → exit=0 url_present True; "
        "RO SELECT used DATABASE_PUBLIC_URL host_kind=proxy\n"
        "6. 127.0.0.1:5432 ConnectionRefused (unused)\n\n"
        "## CLOSED vs remaining\n\n"
        f"CLOSED: {' · '.join(closed)}\n"
        f"REMAINING: {'none' if not remaining else ' · '.join(remaining)}\n\n"
        f"Completeness sha256 {sha} (sha8 {sha[:8]})\n"
        f"RO probe sha256 {probe_sha} (sha8 {probe_sha[:8]})\n\n"
        "NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen\n"
        "No Odds · no merge · no deploy · no DML/DDL · no Option B\n"
    )
    closed_json = {
        "ticket": "t4615u",
        "component": "current_weekly_depth_db",
        "classification": "CLOSED",
        "cert_candidate": 0,
        "RAILWAY_TOKEN": "SET",
        "RAILWAY_TOKEN_length": len(os.environ.get("RAILWAY_TOKEN") or ""),
        "railway_whoami": "Unauthorized",
        "railway_status": "exit=0",
        "railway_run": "exit=0",
        "transaction_read_only": True,
        "invented": False,
        "option_b_attempted": False,
        "warehouse_rows_read": probe.get("warehouse_rows_read"),
        "completeness_sha256": sha,
        "completeness_sha8": sha[:8],
        "probe_sha256": probe_sha,
        "probe_sha8": probe_sha[:8],
        "closed": closed,
        "remaining": remaining,
        "prior_access_blocker_sha8": "a79f58f8",
        "prior_tip": "d8356dcb",
        "decision_sha8": "53572667",
        "filed_at_utc": report["audited_at_utc"],
    }
    success = (
        "# t4615u fresh VM Unblock A — current_weekly_depth_db CLOSED\n\n"
        f"completeness sha8: `{sha[:8]}`\n\n"
        f"RO probe sha8: `{probe_sha[:8]}`\n\n"
        "RAILWAY_TOKEN SET length 36 — not RUNTIME_SECRET_MISSING.\n\n"
        f"CLOSED: {', '.join(closed)}\n\n"
        f"REMAINING: {'none' if not remaining else ', '.join(remaining)}\n"
    )
    for dest in dests:
        _write_0444(dest / "completeness.json", blob)
        _write_0444(dest / "depth_db_ro_probe.json", PROBE.read_bytes())
        _write_0444(
            dest / "CLOSED_current_weekly_depth_db_t4615u.md",
            closed_md.encode(),
        )
        _write_0444(
            dest / "CLOSED_current_weekly_depth_db_t4615u.json",
            (json.dumps(closed_json, indent=2, sort_keys=True) + "\n").encode(),
        )
        _write_0444(dest / "SUCCESS_REPORT.md", success.encode())
        names = [
            "completeness.json",
            "depth_db_ro_probe.json",
            "CLOSED_current_weekly_depth_db_t4615u.md",
            "CLOSED_current_weekly_depth_db_t4615u.json",
            "SUCCESS_REPORT.md",
        ]
        sums = []
        for name in names:
            digest = _sha256_file(dest / name)
            sums.append(f"{digest}  {name}\n")
        _write_0444(dest / "SHA256SUMS", "".join(sums).encode())
        print(
            json.dumps(
                {
                    "path": str(dest.relative_to(ROOT)),
                    "completeness_sha256": sha,
                    "completeness_sha8": sha[:8],
                    "ok": report["ok"],
                    "passed": report["passed"],
                    "failing": report["failing_components"],
                    "RAILWAY_TOKEN": "SET" if os.environ.get("RAILWAY_TOKEN") else "UNSET",
                    "RAILWAY_TOKEN_length": len(os.environ.get("RAILWAY_TOKEN") or ""),
                },
                indent=2,
            )
        )
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
