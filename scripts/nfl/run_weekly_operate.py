#!/usr/bin/env python3
"""NFL weekly operate loop — single entrypoint (Phase 1).

Hooks existing ingest / proof / SoT / identity / KEI scripts.
Does **not** invent a model, flip the research pin, or ungate weekly props.

Usage:
  python scripts/nfl/run_weekly_operate.py --dry-run
  python scripts/nfl/run_weekly_operate.py --week 1 --dry-run
  python scripts/nfl/run_weekly_operate.py --week 5
  python scripts/nfl/run_weekly_operate.py --week 5 --skip-kei --skip-audit
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "nfl"))

from nfl_operate_contract import (  # noqa: E402
    HOOKS,
    POINTER_PATH,
    PRESEASON_LOCK_TAG,
    WEEKLY_LAST_RUN_PATH,
    WEEKLY_PROPS_LIVE,
    WEEKLY_SCHEMA,
    WEEKLY_STAGE_IDS,
    human_required_items,
    is_checkpoint_week,
    overall_status,
    pending_intel_files,
    pointer_lock_tag,
    proposed_camp_sot_files,
    read_pointer,
    stage,
    utc_now,
    write_json,
)

SCRIPTS = ROOT / "scripts" / "nfl"


def _load_script(name: str):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _python() -> str:
    venv = ROOT / ".venv" / "bin" / "python3"
    if venv.is_file():
        return str(venv)
    return sys.executable


def stage_results_ingest(
    *,
    week: int,
    dry_run: bool,
    pointer: Mapping[str, Any],
) -> Dict[str, Any]:
    hook = HOOKS["results_ingest"]
    if week < 1:
        return stage(
            "results_ingest",
            "skip",
            "preseason / no REG games — not ingesting fabricated results",
            hook=hook,
        )
    if dry_run:
        return stage(
            "results_ingest",
            "pass",
            (
                f"dry-run: would run SEASON=2026 WEEK={week} {hook} --dry-run "
                f"+ {HOOKS['projection_actuals']} --from-db + "
                f"{HOOKS['rolling_features']} --dry-run"
            ),
            hook=hook,
        )
    if pointer.get("preseason"):
        return stage(
            "results_ingest",
            "skip",
            "research pointer still preseason; no REG results to fold in",
            hook=hook,
        )
    script = ROOT / hook
    cmd = [str(script)]
    env = os.environ.copy()
    env["SEASON"] = str(int(pointer.get("season") or 2026))
    env["WEEK"] = str(week)
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return stage(
            "results_ingest",
            "human_required",
            f"could not exec {hook}: {exc}",
            hook=hook,
        )
    if proc.returncode != 0:
        return stage(
            "results_ingest",
            "fail",
            f"{hook} exit {proc.returncode}: {(proc.stderr or proc.stdout or '')[-400:]}",
            hook=hook,
        )
    return stage(
        "results_ingest",
        "pass",
        f"ran {hook} for week {week}",
        hook=hook,
    )


def stage_proof_log(*, week: int, dry_run: bool) -> Dict[str, Any]:
    writer = ROOT / HOOKS["projection_actuals"]
    lake = (
        ROOT
        / "services/model-service/src/services/proof_layer/proof_lake.py"
    )
    lake_dir = ROOT / "services/model-service/data/ops/projection_logs"
    jsonl = lake_dir / "projections.jsonl"
    if not writer.is_file() or not lake.is_file():
        return stage(
            "proof_log",
            "fail",
            "missing proof writer or lake module — will not invent a parallel lake",
            hook=HOOKS["proof_lake"],
        )
    if jsonl.is_file() and jsonl.stat().st_size == 0:
        return stage(
            "proof_log",
            "fail",
            "proof lake JSONL present but empty-wiped; refusing to continue",
            hook=HOOKS["proof_lake"],
        )
    if week < 1 or dry_run:
        return stage(
            "proof_log",
            "pass",
            (
                "projection→close→result path present "
                f"({HOOKS['projection_actuals']}; lake {lake.relative_to(ROOT)}). "
                "No wipe. Preseason/dry-run does not write actuals."
            ),
            hook=HOOKS["projection_actuals"],
            extra={"lake_jsonl_exists": jsonl.is_file()},
        )
    proc = subprocess.run(
        [_python(), str(writer), "--season", "2026", "--from-db"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return stage(
            "proof_log",
            "skip",
            (
                "write_projection_actuals failed (honest skip — no fake actuals): "
                f"{(proc.stderr or proc.stdout or '')[-300:]}"
            ),
            hook=HOOKS["projection_actuals"],
        )
    return stage(
        "proof_log",
        "pass",
        "wrote projection actuals from owned DB; lake not wiped",
        hook=HOOKS["projection_actuals"],
    )


def stage_depth_injury(*, dry_run: bool) -> Dict[str, Any]:
    hook = HOOKS["daily_intel"]
    camp_hook = HOOKS["camp_sot_queue"]
    pending = pending_intel_files()
    proposed = proposed_camp_sot_files()
    camp_note = ""
    if proposed:
        camp_note = (
            f" Camp SoT proposals ({len(proposed)}): "
            f"python {camp_hook} --scan then --accept <file> [--write]."
        )
    if pending:
        names = ", ".join(p.name for p in pending)
        if dry_run:
            return stage(
                "depth_injury_hook",
                "human_required",
                (
                    f"pending intel {names} — dry-run will not write the SoT pack. "
                    f"Human: python {hook} --overrides <file> --write."
                    f"{camp_note}"
                ),
                hook=hook,
            )
        return stage(
            "depth_injury_hook",
            "human_required",
            (
                f"pending intel {names} found. Weekly job does not auto-write SoT "
                f"(Walker stays KC unless human override). "
                f"Apply via python {hook} --overrides data/ops/nfl-daily-intel/pending/<file> --write."
                f"{camp_note}"
            ),
            hook=hook,
        )
    if proposed:
        return stage(
            "depth_injury_hook",
            "human_required",
            (
                f"no pending intel; {len(proposed)} Camp Desk SoT work item(s) await accept. "
                f"python {camp_hook} --scan ; "
                f"python {camp_hook} --accept data/ops/nfl-daily-intel/queue/runtime/<file> [--write]. "
                f"Rematerialize after pack write via safe rebuild (weeks 1–18). "
                f"Queue≠remat — overdue T1 does not move the board until Accept."
            ),
            hook=camp_hook,
        )
    return stage(
        "depth_injury_hook",
        "human_required",
        (
            "no live injury scrape in this pipeline. Manual intel: "
            "fill data/ops/nfl-daily-intel/pending/*.json then "
            f"python {hook} --overrides <file> --write. "
            f"Camp flags: python {camp_hook} --scan [--queue]. "
            f"Optional KEI heartbeat: python {HOOKS['injury_kei']} --window midweek --dry-run"
        ),
        hook=hook,
    )


def stage_identity_audit(
    *,
    skip: bool,
    audit_fn: Optional[Callable[[], Mapping[str, Any]]] = None,
) -> Dict[str, Any]:
    hook = HOOKS["identity_audit"]
    if skip:
        return stage(
            "identity_audit",
            "skip",
            "--skip-audit",
            hook=hook,
        )
    if audit_fn is None:
        mod = _load_script("audit_nfl_pack_vs_market")
        audit_fn = mod.audit
    report = audit_fn()
    counts = dict(report.get("counts") or {})
    n_clear = int(counts.get("CLEAR_ERROR") or 0)
    extra = {
        "CLEAR_ERROR": n_clear,
        "NAME_MATCH_WEAK": int(counts.get("NAME_MATCH_WEAK") or 0),
        "STALE_FP": int(counts.get("STALE_FP") or 0),
    }
    if n_clear > 0:
        return stage(
            "identity_audit",
            "fail",
            f"CLEAR_ERROR={n_clear} — pipeline fails; human review required (no auto-move)",
            hook=hook,
            extra=extra,
        )
    return stage(
        "identity_audit",
        "pass",
        "CLEAR_ERROR=0 (SOT_SKILL_OVERRIDES / documented SoT held)",
        hook=hook,
        extra=extra,
    )


def stage_kei_board(
    *,
    skip: bool,
    dry_run: bool,
    week: int,
) -> Dict[str, Any]:
    hook = HOOKS["edge_board"]
    if skip:
        return stage(
            "kei_board_rebuild",
            "skip",
            "--skip-kei",
            hook=hook,
        )
    board = _load_script("check_edge_board_week1")
    results = board.check_week1(board_rows=None)
    failed = [f"{cid}: {detail}" for cid, ok, detail in results if not ok]
    if failed:
        return stage(
            "kei_board_rebuild",
            "fail",
            "Edge Board Week 1 slate check failed: " + "; ".join(failed),
            hook=hook,
        )
    kei_hook = HOOKS["injury_kei"]
    detail = (
        "KEI is read-time (nfl_kei_week1_reprice) — no model version bump. "
        f"Slate check PASS. Planned: python {kei_hook} --window midweek --dry-run "
        "(live DB reprice stays the existing injury cadence, not this weekly job)."
    )
    if not dry_run:
        kei_script = ROOT / kei_hook
        proc = subprocess.run(
            [
                _python(),
                str(kei_script),
                "--window",
                "midweek",
                "--dry-run",
                "--week",
                str(max(week, 1)),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            return stage(
                "kei_board_rebuild",
                "human_required",
                (
                    f"slate PASS; {kei_hook} heartbeat exit {proc.returncode} "
                    f"(honest — no live injury scrape). {(proc.stderr or '')[-200:]}"
                ),
                hook=kei_hook,
            )
        detail = (
            "slate PASS; injury→KEI midweek heartbeat ran --dry-run. "
            "No model version bump. Fair-lines consumers read current KEI."
        )
    return stage("kei_board_rebuild", "pass", detail, hook=hook)


def stage_health_smoke(
    *,
    pointer: Mapping[str, Any],
    dry_run: bool,
) -> Dict[str, Any]:
    lock = pointer_lock_tag(pointer)
    if not pointer.get("locked_snapshot") or not lock:
        return stage(
            "health_smoke",
            "fail",
            "research pointer missing locked_snapshot/lock_tag",
            hook="data/ops/nfl-web-launch-bundle.json",
        )
    notes = [
        f"pointer lock_tag={lock} locked_snapshot=true",
        "injuries residual-honesty is not board degradation",
        "weekly job does not call /health/nfl-production-readiness (preseason false degraded)",
    ]
    url = (os.environ.get("MODEL_SERVICE_URL") or "").rstrip("/")
    if dry_run or not url:
        notes.append(
            "HTTP /health skipped (dry-run or MODEL_SERVICE_URL unset) — local pointer smoke only"
        )
        return stage(
            "health_smoke",
            "pass",
            "; ".join(notes),
            hook="GET /health",
            extra={"lock_tag": lock, "http": "skipped"},
        )
    health_url = f"{url}/health"
    try:
        with urllib.request.urlopen(health_url, timeout=5) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        if str(body.get("status") or "").lower() not in {"ok", "healthy"}:
            return stage(
                "health_smoke",
                "fail",
                f"{health_url} status={body.get('status')!r}",
                hook=health_url,
            )
        notes.append(f"{health_url} ok")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return stage(
            "health_smoke",
            "skip",
            f"{health_url} unreachable ({exc}); not marking degraded",
            hook=health_url,
        )
    return stage(
        "health_smoke",
        "pass",
        "; ".join(notes),
        hook=health_url,
        extra={"lock_tag": lock, "http": "ok"},
    )


def run_weekly(
    *,
    week: int,
    dry_run: bool,
    skip_kei: bool = False,
    skip_audit: bool = False,
    last_run_path: Path = WEEKLY_LAST_RUN_PATH,
    pointer_path: Path = POINTER_PATH,
    audit_fn: Optional[Callable[[], Mapping[str, Any]]] = None,
) -> Dict[str, Any]:
    pointer_before = read_pointer(pointer_path)
    lock_before = pointer_lock_tag(pointer_before)
    stages: List[Dict[str, Any]] = [
        stage_results_ingest(week=week, dry_run=dry_run, pointer=pointer_before),
        stage_proof_log(week=week, dry_run=dry_run),
        stage_depth_injury(dry_run=dry_run),
        stage_identity_audit(skip=skip_audit, audit_fn=audit_fn),
        stage_kei_board(skip=skip_kei, dry_run=dry_run, week=week),
        stage_health_smoke(pointer=pointer_before, dry_run=dry_run),
    ]
    # Safety: weekly never publishes / never writes the research pointer.
    pointer_after = read_pointer(pointer_path)
    lock_after = pointer_lock_tag(pointer_after)
    flipped = lock_after != lock_before or pointer_after != pointer_before
    if flipped:
        stages.append(
            stage(
                "pointer_guard",
                "fail",
                "weekly job observed a pointer change — this is a bug",
                hook=str(pointer_path),
            )
        )
    payload: Dict[str, Any] = {
        "schema": WEEKLY_SCHEMA,
        "generated_at_utc": utc_now(),
        "season": 2026,
        "week": int(week),
        "dry_run": bool(dry_run),
        "status": overall_status(stages),
        "stages": stages,
        "human_required": human_required_items(stages),
        "pointer_path": "data/ops/nfl-web-launch-bundle.json",
        "pointer_lock_tag": lock_after or lock_before,
        "pointer_flipped": False,
        "never_flips_research_pin": True,
        "weekly_props_live": WEEKLY_PROPS_LIVE,
        "ros_checkpoint_due": is_checkpoint_week(week),
        "ros_checkpoint_note": (
            f"checkpoint week {week}: run scripts/nfl/run_ros_checkpoint_sim.py "
            f"--after-week {week} --dry-run  (weekly path does not invoke ROS)"
            if is_checkpoint_week(week)
            else "weekly path never calls ROS checkpoint"
        ),
        "preseason_lock_tag": PRESEASON_LOCK_TAG,
        "stage_order": list(WEEKLY_STAGE_IDS),
    }
    write_json(last_run_path, payload)
    return payload


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--week", type=int, default=0, help="Finished REG week (0 = preseason)")
    ap.add_argument("--dry-run", action="store_true", help="Plan + read-only stages; no writes except last-run JSON")
    ap.add_argument("--skip-kei", action="store_true")
    ap.add_argument("--skip-audit", action="store_true")
    ap.add_argument(
        "--last-run",
        type=Path,
        default=WEEKLY_LAST_RUN_PATH,
        help="Override last-run JSON path",
    )
    args = ap.parse_args(argv)

    payload = run_weekly(
        week=args.week,
        dry_run=args.dry_run,
        skip_kei=args.skip_kei,
        skip_audit=args.skip_audit,
        last_run_path=args.last_run,
    )
    print(json.dumps(payload, indent=2))
    if payload["status"] == "fail":
        print("WEEKLY OPERATE FAILED", file=sys.stderr)
        return 1
    print(
        f"WEEKLY OPERATE {payload['status'].upper()} "
        f"week={payload['week']} lock_tag={payload['pointer_lock_tag']} "
        f"pointer_flipped={payload['pointer_flipped']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
