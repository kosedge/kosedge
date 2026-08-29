"""DepthSotWorkItem pipeline — no snapshot dumps; accept/reject gates only."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.services.nfl_camp_sot_queue import (
    NOTES_MAY_TOUCH_MEANS,
    PROPOSALS_MAY_AUTO_APPLY,
    RECEIPT_SCHEMA,
    WORK_ITEM_SCHEMA,
    accept_proposal,
    assert_notes_cannot_touch_lines,
    classify_tier,
    close_work_item,
    load_pack,
    next_kei_publish_utc,
    proposal_doc_for_flag,
    queue_flags,
    scan_camp_sot_flags,
    work_item_id_for,
)
from src.services.nfl_daily_intel import apply_intel_overrides

PACK_PATH = (
    Path(__file__).resolve().parents[1]
    / "src/services/nfl_season_engine/data/nfl_depth_chart_2026_w1.json"
)
CAMP_DIR = Path(__file__).resolve().parents[3] / "content/writers/camp-desk-2026"


def _pre_accept_pack_bytes() -> str:
    """Pack state before CLE Watson / HOU Higgins desk accepts (#296).

    Live SoT pack may already have those fields applied; heuristic drafts skip
    no-ops, so accept/preview tests need the pre-accept competition/injury rows.
    """
    payload = json.loads(PACK_PATH.read_text(encoding="utf-8"))
    for row in payload.get("rows") or []:
        if not isinstance(row, dict):
            continue
        if row.get("team") == "CLE" and row.get("player_name") == "Deshaun Watson":
            row["competition_status"] = "open_competition"
        if row.get("team") == "HOU" and row.get("player_name") == "Jayden Higgins":
            row.pop("injury_status", None)
    return json.dumps(payload, indent=2) + "\n"


def _write_pre_accept_pack(path: Path) -> Path:
    path.write_text(_pre_accept_pack_bytes(), encoding="utf-8")
    return path


def _cle_id() -> str:
    return work_item_id_for(
        as_of="2026-08-26", team_id="CLE", note_id="note-2026-08-26-CLE"
    )


def _hou_id() -> str:
    return work_item_id_for(
        as_of="2026-08-26", team_id="HOU", note_id="note-2026-08-26-HOU"
    )


def test_contract_notes_never_touch_lines() -> None:
    assert NOTES_MAY_TOUCH_MEANS is False
    assert PROPOSALS_MAY_AUTO_APPLY is False
    assert_notes_cannot_touch_lines()


def test_note_text_cannot_change_means(tmp_path: Path) -> None:
    """Queue/scan never mutate the depth pack (share math ignores note prose)."""
    pack_copy = tmp_path / "pack.json"
    pack_copy.write_text(PACK_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    before = pack_copy.read_text(encoding="utf-8")
    flags = scan_camp_sot_flags(
        camp_dir=CAMP_DIR,
        pack_path=pack_copy,
        proposed_dir=tmp_path / "queue",
        accepted_log=tmp_path / "accepted.jsonl",
        now=datetime(2026, 8, 27, 20, 0, tzinfo=timezone.utc),
    )
    queue_flags(flags, proposed_dir=tmp_path / "queue", accepted_log=tmp_path / "a.jsonl")
    assert pack_copy.read_text(encoding="utf-8") == before
    # Prose alone is not an override path.
    dry = apply_intel_overrides(load_pack(pack_copy), [], as_of="2026-08-26")
    assert dry.applied == []


def test_proposed_patch_never_auto_applies(tmp_path: Path) -> None:
    pack_copy = _write_pre_accept_pack(tmp_path / "pack.json")
    before = json.loads(before_text := pack_copy.read_text(encoding="utf-8"))
    flags = scan_camp_sot_flags(
        camp_dir=CAMP_DIR,
        pack_path=pack_copy,
        proposed_dir=tmp_path / "queue",
        accepted_log=tmp_path / "accepted.jsonl",
        now=datetime(2026, 8, 27, 20, 0, tzinfo=timezone.utc),
    )
    cle = next(f for f in flags if f.team == "CLE")
    assert cle.proposed_patch
    queue_flags([cle], proposed_dir=tmp_path / "queue")
    after = json.loads(pack_copy.read_text(encoding="utf-8"))
    assert after == before
    assert before_text == pack_copy.read_text(encoding="utf-8")


def test_queue_idempotent_no_duplicate_open_items(tmp_path: Path) -> None:
    qdir = tmp_path / "queue"
    log = tmp_path / "accepted.jsonl"
    flags = scan_camp_sot_flags(
        camp_dir=CAMP_DIR,
        pack_path=PACK_PATH,
        proposed_dir=qdir,
        accepted_log=log,
        now=datetime(2026, 8, 27, 20, 0, tzinfo=timezone.utc),
    )
    first = queue_flags(flags, proposed_dir=qdir, accepted_log=log)
    assert first.created
    assert not first.updated
    second = queue_flags(flags, proposed_dir=qdir, accepted_log=log)
    assert not second.created
    assert second.unchanged
    assert len(list(qdir.glob("work-item-*.json"))) == len(first.created)


def test_dry_run_previews_without_writing(tmp_path: Path) -> None:
    qdir = tmp_path / "queue"
    pending = tmp_path / "pending"
    log = tmp_path / "accepted.jsonl"
    receipts = tmp_path / "receipts"
    pack_copy = _write_pre_accept_pack(tmp_path / "pack.json")
    before = pack_copy.read_text(encoding="utf-8")

    flags = scan_camp_sot_flags(
        camp_dir=CAMP_DIR,
        pack_path=pack_copy,
        proposed_dir=qdir,
        accepted_log=log,
        now=datetime(2026, 8, 27, 20, 0, tzinfo=timezone.utc),
    )
    cle = next(f for f in flags if f.work_item_id == _cle_id())
    path = queue_flags([cle], proposed_dir=qdir, accepted_log=log).created[0]

    result = accept_proposal(
        path,
        pack_path=pack_copy,
        pending_dir=pending,
        accepted_log=log,
        receipts_dir=receipts,
        dry_run=True,
        actor="desk",
        reason="preview Watson QB1",
    )
    assert result["disposition"] == "dry_run"
    assert result["wrote_pack"] is False
    assert result["receipt"] is None
    assert result["pack_diff"]
    assert result["committed_fields"]
    assert pack_copy.read_text(encoding="utf-8") == before
    assert path.is_file()
    assert not log.exists() or "accepted" not in log.read_text(encoding="utf-8")
    assert not list(pending.glob("*"))


def test_accept_writes_pack_then_remats_once(tmp_path: Path) -> None:
    qdir = tmp_path / "queue"
    pending = tmp_path / "pending"
    log = tmp_path / "accepted.jsonl"
    receipts = tmp_path / "receipts"
    pack_copy = _write_pre_accept_pack(tmp_path / "pack.json")

    flags = scan_camp_sot_flags(
        camp_dir=CAMP_DIR,
        pack_path=pack_copy,
        proposed_dir=qdir,
        accepted_log=log,
        now=datetime(2026, 8, 27, 20, 0, tzinfo=timezone.utc),
    )
    cle = next(f for f in flags if f.work_item_id == _cle_id())
    path = queue_flags([cle], proposed_dir=qdir, accepted_log=log).created[0]

    result = accept_proposal(
        path,
        pack_path=pack_copy,
        pending_dir=pending,
        accepted_log=log,
        receipts_dir=receipts,
        write_pack=True,
        rematerialize=True,
        actor="desk",
        reason="Watson named QB1",
    )
    assert result["disposition"] == "accepted"
    assert result["wrote_pack"] is True
    assert result["actor"] == "desk"
    assert result["remat_run_id"]
    assert result["pack_before_sha256"]
    assert result["pack_after_sha256"]
    assert result["pack_diff"]
    receipt = json.loads(Path(result["receipt"]).read_text(encoding="utf-8"))
    assert receipt["schema"] == RECEIPT_SCHEMA
    assert receipt["audit"]["actor"] == "desk"
    assert receipt["audit"]["remat_run_id"]
    assert "pack_diff" in receipt
    assert "line_delta" in receipt
    assert receipt["contract"]["public_accept_ui"] is False

    path.write_text(json.dumps(proposal_doc_for_flag(cle), indent=2) + "\n", encoding="utf-8")
    try:
        accept_proposal(
            path,
            pack_path=pack_copy,
            pending_dir=pending,
            accepted_log=log,
            receipts_dir=receipts,
            write_pack=True,
            rematerialize=True,
            actor="desk",
        )
        assert False, "expected already-closed error"
    except ValueError as exc:
        assert "already closed" in str(exc)


def test_remat_fail_rolls_back_and_is_not_accepted(tmp_path: Path) -> None:
    from src.services.nfl_camp_sot_queue import failing_remat

    qdir = tmp_path / "queue"
    log = tmp_path / "accepted.jsonl"
    receipts = tmp_path / "receipts"
    pack_copy = _write_pre_accept_pack(tmp_path / "pack.json")
    before = pack_copy.read_text(encoding="utf-8")

    flags = scan_camp_sot_flags(
        camp_dir=CAMP_DIR,
        pack_path=pack_copy,
        proposed_dir=qdir,
        accepted_log=log,
        now=datetime(2026, 8, 27, 20, 0, tzinfo=timezone.utc),
    )
    cle = next(f for f in flags if f.work_item_id == _cle_id())
    path = queue_flags([cle], proposed_dir=qdir, accepted_log=log).created[0]

    result = accept_proposal(
        path,
        pack_path=pack_copy,
        pending_dir=tmp_path / "pending",
        accepted_log=log,
        receipts_dir=receipts,
        write_pack=True,
        rematerialize=True,
        remat_fn=failing_remat("celery down"),
        actor="desk",
        reason="should rollback",
    )
    assert result["disposition"] == "remat_failed"
    assert result["wrote_pack"] is False
    assert pack_copy.read_text(encoding="utf-8") == before
    assert path.is_file()  # still open for retry
    assert '"disposition": "remat_failed"' in log.read_text(encoding="utf-8")
    assert '"disposition": "accepted"' not in log.read_text(encoding="utf-8")


def test_reject_and_no_change_write_nothing(tmp_path: Path) -> None:
    qdir = tmp_path / "queue"
    log = tmp_path / "accepted.jsonl"
    receipts = tmp_path / "receipts"
    pack_copy = tmp_path / "pack.json"
    pack_copy.write_text(PACK_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    before = pack_copy.read_text(encoding="utf-8")

    flags = scan_camp_sot_flags(
        camp_dir=CAMP_DIR,
        pack_path=pack_copy,
        proposed_dir=qdir,
        accepted_log=log,
        now=datetime(2026, 8, 27, 20, 0, tzinfo=timezone.utc),
    )
    ari = next(f for f in flags if f.team == "ARI")
    atl = next(f for f in flags if f.team == "ATL")
    paths = queue_flags([ari, atl], proposed_dir=qdir, accepted_log=log).created
    by_team = {p.stem.split("-")[-1]: p for p in paths}

    rejected = close_work_item(
        by_team["ARI"], disposition="reject", accepted_log=log, receipts_dir=receipts
    )
    cleared = close_work_item(
        by_team["ATL"], disposition="no_change", accepted_log=log, receipts_dir=receipts
    )
    assert rejected["wrote_pack"] is False
    assert rejected["rematerialize_status"] == "skipped"
    assert cleared["wrote_pack"] is False
    assert cleared["pack_diff"] == []
    assert pack_copy.read_text(encoding="utf-8") == before


def test_scan_tiers_and_kei_deadline(tmp_path: Path) -> None:
    flags = scan_camp_sot_flags(
        camp_dir=CAMP_DIR,
        pack_path=PACK_PATH,
        proposed_dir=tmp_path / "queue",
        accepted_log=tmp_path / "accepted.jsonl",
        now=datetime(2026, 8, 27, 20, 0, tzinfo=timezone.utc),
    )
    by_team = {f.team: f for f in flags}
    assert by_team["CLE"].tier == "T1"
    assert by_team["CLE"].work_item_id == _cle_id()
    assert by_team["HOU"].tier == "T1"
    assert by_team["HOU"].work_item_id == _hou_id()
    assert by_team["ATL"].tier == "T3"
    assert by_team["CLE"].next_kei_publish
    # Wed desk → next KEI is Thu 16:00 ET.
    deadline = next_kei_publish_utc(datetime(2026, 8, 26, 16, 0, tzinfo=timezone.utc))
    assert deadline.astimezone(timezone.utc).day == 27  # Thu Aug 27


def test_bal_season_ending_is_t1(tmp_path: Path) -> None:
    flags = scan_camp_sot_flags(
        camp_dir=CAMP_DIR,
        pack_path=PACK_PATH,
        proposed_dir=tmp_path / "queue",
        accepted_log=tmp_path / "accepted.jsonl",
        now=datetime(2026, 8, 27, 20, 0, tzinfo=timezone.utc),
    )
    bal = next(f for f in flags if f.team == "BAL")
    assert bal.tier == "T1"


def test_never_drafts_depth_order(tmp_path: Path) -> None:
    flags = scan_camp_sot_flags(
        camp_dir=CAMP_DIR,
        pack_path=PACK_PATH,
        proposed_dir=tmp_path / "queue",
        accepted_log=tmp_path / "accepted.jsonl",
        now=datetime(2026, 8, 27, 20, 0, tzinfo=timezone.utc),
    )
    for flag in flags:
        for ov in flag.proposed_patch:
            assert ov["field"] not in {
                "depth_order",
                "depth_slot",
                "player_name",
                "player_id",
            }


def test_named_starter_and_committee_guards(tmp_path: Path) -> None:
    pack_copy = _write_pre_accept_pack(tmp_path / "pack.json")
    flags = scan_camp_sot_flags(
        camp_dir=CAMP_DIR,
        pack_path=pack_copy,
        proposed_dir=tmp_path / "queue",
        accepted_log=tmp_path / "accepted.jsonl",
        now=datetime(2026, 8, 27, 20, 0, tzinfo=timezone.utc),
    )
    cle = next(f for f in flags if f.team == "CLE")
    named = [
        d["player_name"]
        for d in cle.proposed_patch
        if d.get("field") == "competition_status" and d.get("after") == "named_starter"
    ]
    assert named == ["Deshaun Watson"]
    car = next(f for f in flags if f.team == "CAR")
    injured = {
        d["player_name"]
        for d in car.proposed_patch
        if d.get("field") == "injury_status"
    }
    assert "Chuba Hubbard" not in injured


def test_classify_tier_helpers() -> None:
    assert classify_tier(sot_flag="x", proposed_patch=[{"field": "injury_status"}]) == "T1"
    assert classify_tier(sot_flag="Do not crown either player.", proposed_patch=[]) == "T3"
    assert classify_tier(sot_flag="monitor bubble battle", proposed_patch=[]) == "T2"


def test_proposal_schema() -> None:
    flags = scan_camp_sot_flags(
        camp_dir=CAMP_DIR,
        pack_path=PACK_PATH,
        proposed_dir=Path("/tmp/unused-q"),
        accepted_log=Path("/tmp/unused-a.jsonl"),
        now=datetime(2026, 8, 27, 20, 0, tzinfo=timezone.utc),
    )
    doc = proposal_doc_for_flag(flags[0])
    assert doc["schema"] == WORK_ITEM_SCHEMA
    assert doc["may_auto_apply"] is False
    assert doc["note_id"]
    assert doc["as_of"]
    assert doc["team_id"]
