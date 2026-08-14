#!/usr/bin/env python3
"""NFL ROS checkpoint re-sim — Weeks 4 / 8 / 12 / 16 (+ optional post-deadline).

Default is --dry-run (print plan, do not run sim, do not flip pointer).
--execute runs the existing launch-research sim + publish path, and only
flips the research pin after preseason_release_gate PASS.

Weekly operate must not call this unless after-week is a checkpoint week,
and even then the weekly job only *notes* that a checkpoint is due.

Usage:
  python scripts/nfl/run_ros_checkpoint_sim.py --after-week 4
  python scripts/nfl/run_ros_checkpoint_sim.py --after-week 4 --dry-run
  python scripts/nfl/run_ros_checkpoint_sim.py --after-week 4 --execute
  python scripts/nfl/run_ros_checkpoint_sim.py --after-week 9 --post-deadline --dry-run
  python scripts/nfl/run_ros_checkpoint_sim.py --after-week 4 --execute --n-team-sims 100000 --allow-100k
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "nfl"))

from nfl_operate_contract import (  # noqa: E402
    CHECKPOINT_LAST_RUN_PATH,
    CHECKPOINT_SCHEMA,
    CHECKPOINT_WEEKS,
    DEFAULT_N_PLAYER,
    DEFAULT_N_TEAM,
    HOOKS,
    MAX_N_TEAM_WITHOUT_ALLOW,
    POINTER_PATH,
    POST_DEADLINE_WEEK,
    is_checkpoint_week,
    pointer_lock_tag,
    read_pointer,
    ros_lock_tag,
    utc_now,
    write_json,
)


def _python() -> str:
    venv = ROOT / ".venv" / "bin" / "python3"
    if venv.is_file():
        return str(venv)
    return sys.executable


def build_plan(
    *,
    after_week: int,
    n_team: int,
    n_player: int,
    post_deadline: bool,
    lock_tag: str,
) -> Dict[str, Any]:
    sim = (
        f"{_python()} {HOOKS['research_sim']} "
        f"--n-team-sims {n_team} --n-player-sims {n_player} "
        f"--as-of-week {after_week} --force-packaged --no-hd-mirror"
    )
    gate = f"{_python()} {HOOKS['release_gate']} --bundle <sim-outdir>"
    publish = (
        f"{_python()} {HOOKS['publish']} --source <sim-outdir> "
        f"--lock-tag {lock_tag} --require-release-gate --apply-feature-floors"
    )
    return {
        "after_week": after_week,
        "checkpoint_weeks": list(CHECKPOINT_WEEKS),
        "post_deadline": bool(post_deadline),
        "post_deadline_week": POST_DEADLINE_WEEK,
        "n_team_sims": n_team,
        "n_player_sims": n_player,
        "lock_tag": lock_tag,
        "sim": sim,
        "gate": gate,
        "publish": publish,
        "notes": [
            "Does not change Model vs KEI contract.",
            "Pointer flips only after release gate PASS.",
            "On gate FAIL: no pointer flip; ops note written.",
            "100k requires --execute --allow-100k (not this dry-run).",
        ],
    }


def _parse_bundle(stdout: str) -> Optional[Path]:
    for line in reversed(stdout.splitlines()):
        if line.startswith("DONE bundle="):
            raw = line.split("=", 1)[1].strip()
            path = Path(raw)
            return path if path.is_dir() else ROOT / raw
    return None


def run_checkpoint(
    *,
    after_week: int,
    dry_run: bool,
    execute: bool,
    n_team: int,
    n_player: int,
    post_deadline: bool,
    allow_100k: bool,
    last_run_path: Path = CHECKPOINT_LAST_RUN_PATH,
    pointer_path: Path = POINTER_PATH,
) -> Dict[str, Any]:
    if execute and dry_run:
        raise SystemExit("pass either --dry-run or --execute, not both")
    if not execute:
        dry_run = True
    if execute and n_team > MAX_N_TEAM_WITHOUT_ALLOW and not allow_100k:
        raise SystemExit(
            f"--execute with n_team={n_team} requires --allow-100k "
            "(dry-run may still print a 100k plan)"
        )

    if not is_checkpoint_week(after_week, post_deadline=post_deadline):
        payload = {
            "schema": CHECKPOINT_SCHEMA,
            "generated_at_utc": utc_now(),
            "after_week": after_week,
            "dry_run": dry_run,
            "execute": False,
            "status": "fail",
            "pointer_flipped": False,
            "plan": {},
            "detail": (
                f"after-week {after_week} is not a checkpoint "
                f"{list(CHECKPOINT_WEEKS)}"
                + (" or post-deadline week 9" if post_deadline else "")
                + ". Weekly path must not call ROS except at checkpoints."
            ),
        }
        write_json(last_run_path, payload)
        return payload

    lock_tag = ros_lock_tag(after_week)
    plan = build_plan(
        after_week=after_week,
        n_team=n_team,
        n_player=n_player,
        post_deadline=post_deadline,
        lock_tag=lock_tag,
    )
    lock_before = pointer_lock_tag(read_pointer(pointer_path))

    payload: Dict[str, Any] = {
        "schema": CHECKPOINT_SCHEMA,
        "generated_at_utc": utc_now(),
        "after_week": after_week,
        "dry_run": dry_run,
        "execute": bool(execute),
        "n_team_sims": n_team,
        "n_player_sims": n_player,
        "lock_tag": lock_tag,
        "plan": plan,
        "pointer_path": "data/ops/nfl-web-launch-bundle.json",
        "pointer_lock_tag_before": lock_before,
        "pointer_lock_tag_after": lock_before,
        "pointer_flipped": False,
        "status": "pass",
        "model_vs_kei": "unchanged",
        "require_release_gate": True,
    }

    if dry_run:
        payload["detail"] = (
            f"dry-run plan for ROS after week {after_week}; sim not started; pointer not flipped"
        )
        write_json(last_run_path, payload)
        return payload

    sim_cmd = [
        _python(),
        str(ROOT / HOOKS["research_sim"]),
        "--n-team-sims",
        str(n_team),
        "--n-player-sims",
        str(n_player),
        "--as-of-week",
        str(after_week),
        "--force-packaged",
        "--no-hd-mirror",
    ]
    sim = subprocess.run(sim_cmd, cwd=str(ROOT), capture_output=True, text=True)
    bundle = _parse_bundle(sim.stdout or "")
    if sim.returncode != 0 or bundle is None:
        note = ROOT / f"data/ops/nfl-ros-checkpoint-w{after_week}-failed.md"
        note.write_text(
            "\n".join(
                [
                    f"# ROS checkpoint FAIL — after week {after_week}",
                    "",
                    f"- **status:** sim failed (rc={sim.returncode})",
                    f"- **pointer flipped:** no",
                    f"- **lock_tag before:** `{lock_before}`",
                    "",
                    "```",
                    (sim.stderr or sim.stdout or "")[-4000:],
                    "```",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        payload["status"] = "fail"
        payload["detail"] = f"sim failed; ops note {note.relative_to(ROOT)}"
        payload["ops_note"] = str(note.relative_to(ROOT))
        write_json(last_run_path, payload)
        return payload

    publish_cmd = [
        _python(),
        str(ROOT / HOOKS["publish"]),
        "--source",
        str(bundle),
        "--lock-tag",
        lock_tag,
        "--require-release-gate",
        "--apply-feature-floors",
    ]
    pub = subprocess.run(publish_cmd, cwd=str(ROOT), capture_output=True, text=True)
    lock_after = pointer_lock_tag(read_pointer(pointer_path))
    payload["pointer_lock_tag_after"] = lock_after
    payload["sim_bundle"] = str(bundle)
    if pub.returncode != 0:
        note = ROOT / f"data/ops/nfl-ros-checkpoint-w{after_week}-failed.md"
        note.write_text(
            "\n".join(
                [
                    f"# ROS checkpoint FAIL — after week {after_week}",
                    "",
                    "- **status:** release gate / publish failed",
                    "- **pointer flipped:** no (publish blocked)",
                    f"- **bundle:** `{bundle}`",
                    f"- **lock_tag before:** `{lock_before}`",
                    f"- **lock_tag after:** `{lock_after}`",
                    "",
                    "```",
                    (pub.stderr or pub.stdout or "")[-4000:],
                    "```",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        payload["status"] = "fail"
        payload["pointer_flipped"] = False
        payload["detail"] = f"gate/publish failed; pointer not flipped; {note.relative_to(ROOT)}"
        payload["ops_note"] = str(note.relative_to(ROOT))
        write_json(last_run_path, payload)
        return payload

    payload["pointer_flipped"] = lock_after != lock_before
    payload["detail"] = f"published {bundle} lock_tag={lock_after}"
    write_json(last_run_path, payload)
    return payload


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--after-week", type=int, required=True)
    ap.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print plan only (default when --execute is omitted)",
    )
    ap.add_argument(
        "--execute",
        action="store_true",
        help="Run research sim + publish (gate must PASS to flip pointer)",
    )
    ap.add_argument("--n-team-sims", type=int, default=DEFAULT_N_TEAM)
    ap.add_argument("--n-player-sims", type=int, default=DEFAULT_N_PLAYER)
    ap.add_argument(
        "--post-deadline",
        action="store_true",
        help=f"Allow post-trade-deadline checkpoint (week {POST_DEADLINE_WEEK})",
    )
    ap.add_argument(
        "--allow-100k",
        action="store_true",
        help="Required to actually run N_team >= 100000",
    )
    ap.add_argument("--last-run", type=Path, default=CHECKPOINT_LAST_RUN_PATH)
    args = ap.parse_args(argv)

    if args.execute and args.dry_run:
        print("pass either --dry-run or --execute, not both", file=sys.stderr)
        return 2
    dry_run = not args.execute

    payload = run_checkpoint(
        after_week=args.after_week,
        dry_run=dry_run,
        execute=bool(args.execute),
        n_team=args.n_team_sims,
        n_player=args.n_player_sims,
        post_deadline=args.post_deadline,
        allow_100k=args.allow_100k,
        last_run_path=args.last_run,
    )
    print(json.dumps(payload, indent=2))
    if payload["status"] == "fail":
        print("ROS CHECKPOINT FAILED — pointer not flipped", file=sys.stderr)
        return 1
    mode = "DRY-RUN" if payload.get("dry_run") else "EXECUTE"
    print(
        f"ROS CHECKPOINT {mode} PASS after_week={payload['after_week']} "
        f"pointer_flipped={payload['pointer_flipped']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
