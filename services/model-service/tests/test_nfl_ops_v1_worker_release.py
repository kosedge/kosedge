"""Synthetic-only tests for NFL_OPS_V1 worker release/claim (Primary B).

CERT=0. No real data, scoring, network, DB, or inherited #700/#701 outcome tests.
"""

from __future__ import annotations

import ast
import json
import math
import threading
from pathlib import Path

import pytest

from src.services.nfl_ops_v1_worker_release import (
    SCHEMA_ID,
    WORKER_HANDOFF_FIELD,
    WORKER_HANDOFF_KEYS,
    CursorCloudReclaimAdapter,
    MockedReclaimAdapter,
    SyntheticInProcessReleaseAdapter,
    WorkerReleaseRefuse,
    as_worker_handoff,
    attach_successor,
    build_record,
    claim_successor,
    confirm_release,
    content_hash_of,
    mark_quiescent,
    persist_new_record,
    record_handoff,
    sha256_text,
    stamp_platform_limitation,
    validate_record,
    with_fields,
)
from src.services.nfl_ops_v1_worker_release.types import (
    FORBIDDEN_CALL_TOKENS,
    RELEASE_PLATFORM_LIMITATION,
    STATE_CLAIMED,
    STATE_HANDOFF_RECORDED,
    STATE_QUIESCENT,
    STATE_RELEASE_CONFIRMED,
    STATE_WRITING,
)

PKG = Path(__file__).resolve().parents[1] / "src" / "services" / "nfl_ops_v1_worker_release"
SYNTH_HEAD = sha256_text("synthetic-head-primary-b-nfl-ops-v1")


def _task() -> dict:
    return {
        "id": "synth-primary-b-release-claim",
        "role": "PRIMARY_B",
        "title": "worker final-state / release / claim record",
    }


def _worker() -> dict:
    return {
        "id": "synth-worker-b",
        "alias": "primary-b",
        "kind": "cursor_cloud_heavy",
    }


def _base(**kwargs):
    kwargs.setdefault("task", _task())
    kwargs.setdefault("worker", _worker())
    kwargs.setdefault("branch", "cursor/synth-worker-handoff")
    kwargs.setdefault("head", SYNTH_HEAD)
    kwargs.setdefault("workspace_alias", "synth-ws-primary-b")
    kwargs.setdefault("active_writer", {"id": "synth-worker-b", "branch": "cursor/synth-worker-handoff"})
    return build_record(**kwargs)


def _idle(record):
    return with_fields(record, active_writer=None, running_jobs=[], pending_prompts=[])


def _to_quiescent(record=None):
    rec = record or _base()
    rec = record_handoff(rec)
    rec = _idle(rec)
    return mark_quiescent(rec)


def test_build_record_starts_writing_and_hashes_stable() -> None:
    rec = _base()
    assert rec["state"] == STATE_WRITING
    assert rec["schema"] == SCHEMA_ID
    assert rec["cert"] == 0
    assert rec["synthetic"] is True
    assert rec["self_accept"] is False
    again = content_hash_of(rec)
    assert again == rec["content_hash"]
    assert len(rec["content_hash"]) == 64


def test_worker_handoff_shape_is_stable() -> None:
    rec = _base()
    handoff = as_worker_handoff(rec)
    assert list(handoff) == list(WORKER_HANDOFF_KEYS)
    assert handoff["field"] == WORKER_HANDOFF_FIELD
    assert handoff["content_hash"] == rec["content_hash"]
    assert handoff["record"]["task"]["id"] == "synth-primary-b-release-claim"
    assert handoff["not_a_pass"] is True


def test_content_mutation_refuses_hash() -> None:
    rec = _base()
    mutated = dict(rec)
    mutated["branch"] = "cursor/mutated"
    with pytest.raises(WorkerReleaseRefuse, match="content_hash") as exc:
        validate_record(mutated)
    assert exc.value.code == "HASH_MISMATCH"


def test_missing_extra_null_bool_nan_inf_refused() -> None:
    rec = _base()
    missing = dict(rec)
    missing.pop("branch")
    with pytest.raises(WorkerReleaseRefuse) as exc:
        validate_record(missing)
    assert exc.value.code == "MISSING_FIELD"

    extra = dict(rec)
    extra["invented"] = True
    extra["content_hash"] = content_hash_of(extra)
    with pytest.raises(WorkerReleaseRefuse) as exc:
        validate_record(extra)
    assert exc.value.code == "EXTRA_FIELD"

    with pytest.raises(WorkerReleaseRefuse, match="null"):
        validate_record(None)  # type: ignore[arg-type]

    bad_bool = dict(rec)
    bad_bool["synthetic"] = 1
    with pytest.raises(WorkerReleaseRefuse) as exc:
        validate_record(bad_bool)
    assert exc.value.code == "TYPE_ERROR"

    nan_rec = dict(rec)
    nan_rec["tests"] = {"commands": [], "passed": None, "score": math.nan}
    nan_rec["content_hash"] = content_hash_of(nan_rec)
    with pytest.raises(WorkerReleaseRefuse) as exc:
        validate_record(nan_rec)
    assert exc.value.code == "NONFINITE"

    inf_rec = dict(rec)
    inf_rec["tests"] = {"commands": [], "passed": None, "score": math.inf}
    inf_rec["content_hash"] = content_hash_of(inf_rec)
    with pytest.raises(WorkerReleaseRefuse) as exc:
        validate_record(inf_rec)
    assert exc.value.code == "NONFINITE"


def test_illegal_transitions_refused() -> None:
    rec = _base()
    with pytest.raises(WorkerReleaseRefuse) as exc:
        mark_quiescent(rec)
    assert exc.value.code == "ILLEGAL_TRANSITION"

    handed = record_handoff(rec)
    with pytest.raises(WorkerReleaseRefuse) as exc:
        confirm_release(_idle(handed), SyntheticInProcessReleaseAdapter())
    assert exc.value.code == "ILLEGAL_TRANSITION"

    quiet = _to_quiescent()
    with pytest.raises(WorkerReleaseRefuse) as exc:
        record_handoff(quiet)
    assert exc.value.code == "ILLEGAL_TRANSITION"

    # skip RELEASE_CONFIRMED
    dest = Path("/tmp/does-not-matter")
    with pytest.raises(WorkerReleaseRefuse) as exc:
        claim_successor(
            quiet,
            dest=dest,
            successor_id="synth-successor",
            claim_head=quiet["head"],
            claim_content_hash=quiet["content_hash"],
        )
    assert exc.value.code == "ILLEGAL_TRANSITION"


def test_legal_path_on_synthetic_board(tmp_path: Path) -> None:
    board = SyntheticInProcessReleaseAdapter()
    rec = _to_quiescent()
    rec = attach_successor(rec, successor_id="synth-successor-1", role="INTEGRATION")
    rec = confirm_release(rec, board)
    assert rec["state"] == STATE_RELEASE_CONFIRMED
    assert rec["release_evidence"]["kind"] == "SYNTHETIC_PLATFORM_RELEASE"
    assert rec["release_evidence"]["not_a_pass"] is True
    assert rec["release_evidence"]["not_cursor_workspace_reclaim"] is True
    assert rec["release_evidence"]["evidence_label"] == "EXECUTED_HERE"
    assert board.is_released("synth-ws-primary-b")

    dest = tmp_path / "RELEASE.json"
    persist_new_record(dest, rec)
    claimed = claim_successor(
        rec,
        dest=dest,
        successor_id="synth-successor-1",
        claim_head=rec["head"],
        claim_content_hash=rec["content_hash"],
    )
    assert claimed["state"] == STATE_CLAIMED


def test_competing_claims_only_one_wins(tmp_path: Path) -> None:
    board = SyntheticInProcessReleaseAdapter()
    rec = attach_successor(_to_quiescent(), successor_id="synth-successor-1", role="INTEGRATION")
    rec = confirm_release(rec, board)
    dest = tmp_path / "RELEASE.json"
    persist_new_record(dest, rec)

    results: list[object] = [None, None]

    def worker(idx: int) -> None:
        try:
            results[idx] = claim_successor(
                rec,
                dest=dest,
                successor_id="synth-successor-1",
                claim_head=rec["head"],
                claim_content_hash=rec["content_hash"],
            )
        except Exception as exc:  # noqa: BLE001
            results[idx] = exc

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=3)
    oks = [r for r in results if isinstance(r, dict)]
    errs = [r for r in results if isinstance(r, WorkerReleaseRefuse)]
    assert len(oks) == 1
    assert len(errs) == 1
    assert errs[0].code == "COMPETING_CLAIM"
    assert oks[0]["state"] == STATE_CLAIMED


def test_wrong_successor_refused(tmp_path: Path) -> None:
    board = SyntheticInProcessReleaseAdapter()
    rec = attach_successor(_to_quiescent(), successor_id="synth-successor-1", role="INTEGRATION")
    rec = confirm_release(rec, board)
    dest = tmp_path / "RELEASE.json"
    persist_new_record(dest, rec)
    with pytest.raises(WorkerReleaseRefuse) as exc:
        claim_successor(
            rec,
            dest=dest,
            successor_id="someone-else",
            claim_head=rec["head"],
            claim_content_hash=rec["content_hash"],
        )
    assert exc.value.code == "WRONG_CLAIM"


def test_stale_claim_refused(tmp_path: Path) -> None:
    board = SyntheticInProcessReleaseAdapter()
    rec = attach_successor(_to_quiescent(), successor_id="synth-successor-1", role="INTEGRATION")
    rec = confirm_release(rec, board)
    dest = tmp_path / "RELEASE.json"
    persist_new_record(dest, rec)
    with pytest.raises(WorkerReleaseRefuse) as exc:
        claim_successor(
            rec,
            dest=dest,
            successor_id="synth-successor-1",
            claim_head="a" * 40,
            claim_content_hash=rec["content_hash"],
        )
    assert exc.value.code == "STALE_CLAIM"
    with pytest.raises(WorkerReleaseRefuse) as exc:
        claim_successor(
            rec,
            dest=dest,
            successor_id="synth-successor-1",
            claim_head=rec["head"],
            claim_content_hash="b" * 64,
        )
    assert exc.value.code == "STALE_CLAIM"


def test_dirty_unsaved_blocks_release_and_preserves_draft(tmp_path: Path) -> None:
    draft = tmp_path / "DRAFT_NOTES.txt"
    draft.write_text("synthetic draft — preserve\n", encoding="utf-8")
    rec = _base(
        dirty={
            "clean": False,
            "changed_paths": [str(draft.name)],
            "preserved": True,
        },
        untracked=[str(draft.name)],
    )
    handed = record_handoff(rec)
    assert handed["state"] == STATE_HANDOFF_RECORDED
    assert draft.is_file()
    quiet = mark_quiescent(_idle(handed))
    with pytest.raises(WorkerReleaseRefuse) as exc:
        confirm_release(quiet, SyntheticInProcessReleaseAdapter())
    assert exc.value.code == "DIRTY_UNSAVED"
    assert draft.is_file()
    assert draft.read_text(encoding="utf-8") == "synthetic draft — preserve\n"


def test_dirty_without_preserve_refuses_handoff() -> None:
    rec = _base(
        dirty={"clean": False, "changed_paths": ["notes.txt"], "preserved": False}
    )
    with pytest.raises(WorkerReleaseRefuse) as exc:
        record_handoff(rec)
    assert exc.value.code == "DRAFTS_NOT_PRESERVED"


def test_pending_writer_job_prompt_block_quiescent() -> None:
    handed = record_handoff(_base())
    with pytest.raises(WorkerReleaseRefuse) as exc:
        mark_quiescent(handed)
    assert exc.value.code == "PENDING_WRITER"

    no_writer = with_fields(
        handed,
        active_writer=None,
        running_jobs=[{"id": "job-1", "name": "synth-job"}],
        pending_prompts=[],
    )
    with pytest.raises(WorkerReleaseRefuse) as exc:
        mark_quiescent(no_writer)
    assert exc.value.code == "PENDING_JOB"

    no_job = with_fields(
        handed,
        active_writer=None,
        running_jobs=[],
        pending_prompts=[{"id": "prompt-1", "source": "queue"}],
    )
    with pytest.raises(WorkerReleaseRefuse) as exc:
        mark_quiescent(no_job)
    assert exc.value.code == "PENDING_PROMPT"


def test_missing_platform_capability_is_limitation_not_pass() -> None:
    quiet = _to_quiescent()
    with pytest.raises(WorkerReleaseRefuse) as exc:
        confirm_release(quiet, CursorCloudReclaimAdapter())
    assert exc.value.code == RELEASE_PLATFORM_LIMITATION
    stamped = exc.value.record
    assert stamped is not None
    assert stamped["state"] == STATE_QUIESCENT
    assert stamped["release_evidence"]["kind"] == RELEASE_PLATFORM_LIMITATION
    assert stamped["release_evidence"]["not_a_pass"] is True
    assert stamped["release_evidence"]["platform_capability"] == "ABSENT"
    assert "PASS" not in stamped["release_evidence"]["kind"]
    handoff = as_worker_handoff(stamped)
    assert handoff["release_kind"] == RELEASE_PLATFORM_LIMITATION
    assert handoff["not_a_pass"] is True
    assert handoff["mocked_release"] is False


def test_default_adapter_stamps_limitation() -> None:
    quiet = _to_quiescent()
    stamped = stamp_platform_limitation(quiet)
    assert stamped["release_evidence"]["kind"] == RELEASE_PLATFORM_LIMITATION
    assert stamped["release_evidence"]["not_a_pass"] is True
    assert stamped["state"] == STATE_QUIESCENT


def test_mocked_release_is_not_actual_reclaim() -> None:
    quiet = _to_quiescent()
    with pytest.raises(WorkerReleaseRefuse) as exc:
        confirm_release(quiet, MockedReclaimAdapter())
    assert exc.value.code == "MOCKED_RELEASE"
    stamped = exc.value.record
    assert stamped is not None
    assert stamped["release_evidence"]["kind"] == RELEASE_PLATFORM_LIMITATION
    assert stamped["release_evidence"]["mocked"] is True
    assert stamped["release_evidence"]["not_a_pass"] is True
    assert stamped["state"] != STATE_RELEASE_CONFIRMED


def test_source_has_no_kill_delete_or_takeover() -> None:
    forbidden_attrs = {"kill", "killpg", "rmtree"}
    forbidden_fn_needles = ("takeover", "self_kill", "steal_workspace", "hijack")
    for path in sorted(PKG.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                if node.attr in forbidden_attrs:
                    # allow mentioning the names only inside the token tuple
                    if path.name != "types.py":
                        raise AssertionError(f"{path.name} uses .{node.attr}")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in forbidden_attrs
            if isinstance(node, ast.FunctionDef):
                assert not any(n in node.name for n in forbidden_fn_needles)
    # types.py may list the tokens; executable modules must not contain them.
    for path in sorted(PKG.glob("*.py")):
        if path.name == "types.py":
            continue
        src = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_CALL_TOKENS:
            assert token not in src, f"{path.name} contains {token}"


def test_schema_json_matches_python_contract() -> None:
    schema_path = (
        Path(__file__).resolve().parents[3]
        / "data"
        / "ops"
        / "nfl-ops-v1-worker-release-claim"
        / "SCHEMA.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema["schema"] == SCHEMA_ID
    assert schema["worker_handoff_field"] == WORKER_HANDOFF_FIELD
    assert schema["worker_handoff_keys"] == list(WORKER_HANDOFF_KEYS)
    assert schema["cert"] == 0
    assert schema["self_accept"] is False


def test_cert_nonzero_and_real_flag_refused() -> None:
    rec = _base()
    bad = dict(rec)
    bad["cert"] = 1
    bad["content_hash"] = content_hash_of(bad)
    with pytest.raises(WorkerReleaseRefuse) as exc:
        validate_record(bad)
    assert exc.value.code == "CERT"
    real = dict(rec)
    real["synthetic"] = False
    real["content_hash"] = content_hash_of(real)
    with pytest.raises(WorkerReleaseRefuse) as exc:
        validate_record(real)
    assert exc.value.code == "SYNTHETIC"
