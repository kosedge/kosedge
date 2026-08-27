#!/usr/bin/env python3
"""Shared NFL operate-loop contract (Phase 1).

Not a model. Weekly jobs never flip the research pointer.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[2]
POINTER_PATH = ROOT / "data/ops/nfl-web-launch-bundle.json"
WEEKLY_LAST_RUN_PATH = ROOT / "data/ops/nfl-weekly-operate-last.json"
CHECKPOINT_LAST_RUN_PATH = ROOT / "data/ops/nfl-ros-checkpoint-last.json"

PRESEASON_LOCK_TAG = "nfl-season-engine-2026-preseason-lock"
WEEKLY_PROPS_LIVE = False  # NFL_WEEKLY_PROPS_LIVE stays gated

CHECKPOINT_WEEKS: tuple[int, ...] = (4, 8, 12, 16)
POST_DEADLINE_WEEK = 9  # typical Tue after Week 8
DEFAULT_N_TEAM = 50_000
MAX_N_TEAM_WITHOUT_ALLOW = 50_000
DEFAULT_N_PLAYER = 1_000

STAGE_STATUSES = ("pass", "fail", "skip", "human_required")
WEEKLY_STAGE_IDS = (
    "results_ingest",
    "proof_log",
    "depth_injury_hook",
    "identity_audit",
    "kei_board_rebuild",
    "health_smoke",
)
WEEKLY_SCHEMA = "nfl-weekly-operate-last/v1"
CHECKPOINT_SCHEMA = "nfl-ros-checkpoint-last/v1"

HOOKS = {
    "results_ingest": "scripts/nfl/run-weekly-inseason-update.sh",
    "projection_actuals": "scripts/nfl/write_projection_actuals.py",
    "rolling_features": "scripts/nfl/materialize_team_rolling_features.py",
    "proof_lake": "services/model-service/src/services/proof_layer/proof_lake.py",
    "daily_intel": "scripts/nfl/apply_daily_intel_overrides.py",
    "camp_sot_queue": "scripts/nfl/queue_camp_sot_flags.py",
    "injury_kei": "scripts/nfl/injury_kei_reprice.py",
    "identity_audit": "scripts/nfl/audit_nfl_pack_vs_market.py",
    "edge_board": "scripts/nfl/check_edge_board_week1.py",
    "release_gate": "scripts/nfl/preseason_release_gate.py",
    "research_sim": "scripts/nfl/run_launch_research_sims.py",
    "publish": "scripts/nfl/publish_launch_research_to_web.py",
}

HUMAN_ONLY = (
    "CLEAR_ERROR pack overrides (review mismatch markdown; Walker stays KC unless human override)",
    "SOT_SKILL_OVERRIDES / tag policy judgment",
    "True outages (Railway / Vercel / DB down)",
    "Approved daily-intel writes to the one SoT pack",
    "Camp Desk SoT proposals: queue_camp_sot_flags.py --accept [--write] then rematerialize",
    "ROS checkpoint --execute (50k/100k research sim + pointer flip after gate PASS)",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def read_pointer(path: Path = POINTER_PATH) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def pointer_lock_tag(pointer: Mapping[str, Any] | None = None) -> str:
    doc = pointer if pointer is not None else read_pointer()
    return str(doc.get("lock_tag") or doc.get("lineage", {}).get("lockTag") or "")


def ros_lock_tag(after_week: int) -> str:
    return f"nfl-season-engine-2026-ros-w{int(after_week)}"


def is_checkpoint_week(after_week: int, *, post_deadline: bool = False) -> bool:
    week = int(after_week)
    if week in CHECKPOINT_WEEKS:
        return True
    if post_deadline and week == POST_DEADLINE_WEEK:
        return True
    return False


def stage(
    stage_id: str,
    status: str,
    detail: str,
    *,
    hook: str = "",
    extra: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    if status not in STAGE_STATUSES:
        raise ValueError(f"invalid stage status {status!r}")
    row: Dict[str, Any] = {
        "id": stage_id,
        "status": status,
        "detail": detail,
        "hook": hook,
    }
    if extra:
        row.update(dict(extra))
    return row


def overall_status(stages: Sequence[Mapping[str, Any]]) -> str:
    """Pipeline overall: fail if any stage fails; otherwise pass.

    ``skip`` / ``human_required`` do not fail the job. Humans stay listed
    separately so preseason dry-runs can PASS with honest intel gaps.
    """
    if any(str(s.get("status")) == "fail" for s in stages):
        return "fail"
    return "pass"


def human_required_items(stages: Sequence[Mapping[str, Any]]) -> List[str]:
    out: List[str] = []
    for s in stages:
        if str(s.get("status")) == "human_required":
            out.append(f"{s.get('id')}: {s.get('detail')}")
    return out


def validate_weekly_last_run(payload: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    if payload.get("schema") != WEEKLY_SCHEMA:
        errors.append("schema")
    if payload.get("status") not in ("pass", "fail"):
        errors.append("status")
    if not payload.get("generated_at_utc"):
        errors.append("generated_at_utc")
    if "week" not in payload:
        errors.append("week")
    if payload.get("pointer_flipped") is not False:
        errors.append("pointer_flipped must be false")
    if payload.get("never_flips_research_pin") is not True:
        errors.append("never_flips_research_pin")
    if payload.get("weekly_props_live") is not False:
        errors.append("weekly_props_live")
    stages = payload.get("stages")
    if not isinstance(stages, list) or not stages:
        errors.append("stages")
        return errors
    ids = [str(s.get("id")) for s in stages]
    for required in WEEKLY_STAGE_IDS:
        if required not in ids:
            errors.append(f"missing stage {required}")
    for s in stages:
        if s.get("status") not in STAGE_STATUSES:
            errors.append(f"stage {s.get('id')} status")
        if not s.get("detail"):
            errors.append(f"stage {s.get('id')} detail")
    return errors


def validate_checkpoint_last_run(payload: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    if payload.get("schema") != CHECKPOINT_SCHEMA:
        errors.append("schema")
    if payload.get("status") not in ("pass", "fail"):
        errors.append("status")
    if "after_week" not in payload:
        errors.append("after_week")
    if not isinstance(payload.get("plan"), dict):
        errors.append("plan")
    if payload.get("dry_run") and payload.get("pointer_flipped") is not False:
        errors.append("dry-run must not flip pointer")
    return errors


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def pending_intel_files(intel_dir: Path | None = None) -> List[Path]:
    """Approved-but-unapplied intel lives in nfl-daily-intel/pending/."""
    base = intel_dir or (ROOT / "data/ops/nfl-daily-intel/pending")
    if not base.is_dir():
        return []
    return sorted(
        p
        for p in base.glob("*.json")
        if p.is_file() and not p.name.startswith(".")
    )


def proposed_camp_sot_files(proposed_dir: Path | None = None) -> List[Path]:
    """Camp Desk SoT proposals awaiting human accept (not auto-applied)."""
    base = proposed_dir or (ROOT / "data/ops/nfl-daily-intel/proposed")
    if not base.is_dir():
        return []
    return sorted(
        p
        for p in base.glob("camp-flag-*.json")
        if p.is_file() and not p.name.startswith(".")
    )
