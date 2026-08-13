"""NFL Automation Phase 1 — weekly operate + ROS checkpoint dry-run."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
POINTER = ROOT / "data/ops/nfl-web-launch-bundle.json"
PRESEASON_LOCK = "nfl-season-engine-2026-preseason-lock"


def _load(name: str):
    path = ROOT / "scripts" / "nfl" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _pointer_snapshot() -> tuple[str, str]:
    text = POINTER.read_text(encoding="utf-8")
    doc = json.loads(text)
    return text, str(doc.get("lock_tag") or "")


def test_weekly_last_run_schema_and_stage_status() -> None:
    contract = _load("nfl_operate_contract")
    stages = [
        contract.stage("results_ingest", "skip", "preseason", hook="x"),
        contract.stage("proof_log", "pass", "path ok", hook="y"),
        contract.stage("depth_injury_hook", "human_required", "manual intel", hook="z"),
        contract.stage("identity_audit", "pass", "CLEAR_ERROR=0", hook="a"),
        contract.stage("kei_board_rebuild", "pass", "slate ok", hook="b"),
        contract.stage("health_smoke", "pass", "pointer ok", hook="c"),
    ]
    payload = {
        "schema": contract.WEEKLY_SCHEMA,
        "generated_at_utc": "2026-08-13T00:00:00Z",
        "week": 0,
        "status": contract.overall_status(stages),
        "stages": stages,
        "pointer_flipped": False,
        "never_flips_research_pin": True,
        "weekly_props_live": False,
    }
    assert payload["status"] == "pass"
    assert contract.validate_weekly_last_run(payload) == []
    fail_stages = list(stages)
    fail_stages[3] = contract.stage(
        "identity_audit", "fail", "CLEAR_ERROR=1", hook="a"
    )
    assert contract.overall_status(fail_stages) == "fail"


def test_weekly_dry_run_does_not_flip_pointer(tmp_path: Path) -> None:
    weekly = _load("run_weekly_operate")
    before_text, before_tag = _pointer_snapshot()
    assert before_tag == PRESEASON_LOCK

    last_run = tmp_path / "nfl-weekly-operate-last.json"
    payload = weekly.run_weekly(
        week=0,
        dry_run=True,
        last_run_path=last_run,
        pointer_path=POINTER,
    )
    after_text, after_tag = _pointer_snapshot()

    assert payload["status"] == "pass"
    assert payload["pointer_flipped"] is False
    assert payload["never_flips_research_pin"] is True
    assert payload["weekly_props_live"] is False
    assert payload["pointer_lock_tag"] == PRESEASON_LOCK
    assert after_tag == before_tag == PRESEASON_LOCK
    assert after_text == before_text
    assert last_run.is_file()
    saved = json.loads(last_run.read_text(encoding="utf-8"))
    contract = _load("nfl_operate_contract")
    assert contract.validate_weekly_last_run(saved) == []
    ids = [s["id"] for s in saved["stages"]]
    for required in contract.WEEKLY_STAGE_IDS:
        assert required in ids
    ingest = next(s for s in saved["stages"] if s["id"] == "results_ingest")
    assert ingest["status"] == "skip"
    injury = next(s for s in saved["stages"] if s["id"] == "depth_injury_hook")
    assert injury["status"] == "human_required"


def test_weekly_cli_dry_run_pass(tmp_path: Path) -> None:
    weekly = _load("run_weekly_operate")
    before_text, before_tag = _pointer_snapshot()
    rc = weekly.main(
        [
            "--dry-run",
            "--week",
            "0",
            "--last-run",
            str(tmp_path / "last.json"),
        ]
    )
    after_text, after_tag = _pointer_snapshot()
    assert rc == 0
    assert after_text == before_text
    assert after_tag == before_tag == PRESEASON_LOCK


def test_weekly_source_never_publishes_or_flips_pin() -> None:
    src = (ROOT / "scripts/nfl/run_weekly_operate.py").read_text(encoding="utf-8")
    assert "publish_launch_research_to_web" not in src
    assert "import run_ros_checkpoint_sim" not in src
    assert "from run_ros_checkpoint_sim" not in src
    assert "_write_pointer" not in src
    assert "nfl-web-launch-bundle.json" in src  # read-only guard
    assert "does not invoke ROS" in src or "never calls ROS" in src


def test_identity_audit_clear_error_fails_weekly_without_network(
    tmp_path: Path,
) -> None:
    weekly = _load("run_weekly_operate")
    before_text, before_tag = _pointer_snapshot()

    def fake_audit():
        return {"counts": {"CLEAR_ERROR": 2, "NAME_MATCH_WEAK": 0, "STALE_FP": 0}}

    last_run = tmp_path / "last.json"
    payload = weekly.run_weekly(
        week=0,
        dry_run=True,
        last_run_path=last_run,
        pointer_path=POINTER,
        audit_fn=fake_audit,
        skip_kei=True,
    )
    after_text, after_tag = _pointer_snapshot()
    assert payload["status"] == "fail"
    audit = next(s for s in payload["stages"] if s["id"] == "identity_audit")
    assert audit["status"] == "fail"
    assert audit["CLEAR_ERROR"] == 2
    assert after_text == before_text
    assert after_tag == before_tag == PRESEASON_LOCK


def test_checkpoint_dry_run_week4_shows_plan_without_flipping_pointer(
    tmp_path: Path,
) -> None:
    ros = _load("run_ros_checkpoint_sim")
    before_text, before_tag = _pointer_snapshot()
    last_run = tmp_path / "nfl-ros-checkpoint-last.json"
    payload = ros.run_checkpoint(
        after_week=4,
        dry_run=True,
        execute=False,
        n_team=50_000,
        n_player=1_000,
        post_deadline=False,
        allow_100k=False,
        last_run_path=last_run,
        pointer_path=POINTER,
    )
    after_text, after_tag = _pointer_snapshot()
    assert payload["status"] == "pass"
    assert payload["dry_run"] is True
    assert payload["pointer_flipped"] is False
    assert payload["lock_tag"] == "nfl-season-engine-2026-ros-w4"
    assert payload["n_team_sims"] == 50_000
    plan = payload["plan"]
    assert "--as-of-week 4" in plan["sim"]
    assert "--require-release-gate" in plan["publish"]
    assert "nfl-season-engine-2026-ros-w4" in plan["publish"]
    assert "preseason_release_gate.py" in plan["gate"]
    assert after_text == before_text
    assert after_tag == before_tag == PRESEASON_LOCK
    contract = _load("nfl_operate_contract")
    assert contract.validate_checkpoint_last_run(payload) == []


def test_checkpoint_rejects_non_checkpoint_week(tmp_path: Path) -> None:
    ros = _load("run_ros_checkpoint_sim")
    before_text, _ = _pointer_snapshot()
    payload = ros.run_checkpoint(
        after_week=5,
        dry_run=True,
        execute=False,
        n_team=50_000,
        n_player=1_000,
        post_deadline=False,
        allow_100k=False,
        last_run_path=tmp_path / "last.json",
        pointer_path=POINTER,
    )
    assert payload["status"] == "fail"
    assert payload["pointer_flipped"] is False
    assert POINTER.read_text(encoding="utf-8") == before_text


def test_checkpoint_100k_plan_without_execute_does_not_run_sim(
    tmp_path: Path,
) -> None:
    ros = _load("run_ros_checkpoint_sim")
    before_text, _ = _pointer_snapshot()
    payload = ros.run_checkpoint(
        after_week=4,
        dry_run=True,
        execute=False,
        n_team=100_000,
        n_player=1_000,
        post_deadline=False,
        allow_100k=False,
        last_run_path=tmp_path / "last.json",
        pointer_path=POINTER,
    )
    assert payload["status"] == "pass"
    assert payload["n_team_sims"] == 100_000
    assert "--n-team-sims 100000" in payload["plan"]["sim"]
    assert POINTER.read_text(encoding="utf-8") == before_text


def test_checkpoint_cli_dry_run_week4(tmp_path: Path) -> None:
    ros = _load("run_ros_checkpoint_sim")
    before_text, before_tag = _pointer_snapshot()
    rc = ros.main(
        [
            "--after-week",
            "4",
            "--dry-run",
            "--last-run",
            str(tmp_path / "last.json"),
        ]
    )
    after_text, after_tag = _pointer_snapshot()
    assert rc == 0
    assert after_text == before_text
    assert after_tag == before_tag == PRESEASON_LOCK
    saved = json.loads((tmp_path / "last.json").read_text(encoding="utf-8"))
    assert saved["plan"]["lock_tag"] == "nfl-season-engine-2026-ros-w4"
    assert saved["pointer_flipped"] is False
