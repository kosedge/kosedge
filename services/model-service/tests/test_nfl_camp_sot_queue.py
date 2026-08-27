"""Camp Desk material-depth flags → daily-intel queue (no second SoT)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.services.nfl_camp_sot_queue import (
    accept_proposal,
    proposal_doc_for_flag,
    queue_flags,
    scan_camp_sot_flags,
)
from src.services.nfl_daily_intel import apply_intel_overrides

PACK_PATH = (
    Path(__file__).resolve().parents[1]
    / "src/services/nfl_season_engine/data/nfl_depth_chart_2026_w1.json"
)
CAMP_DIR = Path(__file__).resolve().parents[3] / "content/writers/camp-desk-2026"


def test_scan_finds_aug26_material_flags(tmp_path: Path) -> None:
    flags = scan_camp_sot_flags(
        camp_dir=CAMP_DIR,
        pack_path=PACK_PATH,
        proposed_dir=tmp_path / "proposed",
        accepted_log=tmp_path / "accepted.jsonl",
        now=datetime(2026, 8, 27, 20, 0, tzinfo=timezone.utc),
        overdue_hours=24,
    )
    by_id = {f.flag_id: f for f in flags}
    assert "2026-08-26:CLE" in by_id
    assert "2026-08-26:ATL" in by_id
    assert by_id["2026-08-26:CLE"].overdue is True
    # Watson named starter should draft competition_status when pack still open.
    cle_drafts = by_id["2026-08-26:CLE"].draft_overrides
    assert any(
        d.get("field") == "competition_status" and d.get("after") == "named_starter"
        for d in cle_drafts
    )


def test_never_drafts_depth_order_from_prose(tmp_path: Path) -> None:
    flags = scan_camp_sot_flags(
        camp_dir=CAMP_DIR,
        pack_path=PACK_PATH,
        proposed_dir=tmp_path / "proposed",
        accepted_log=tmp_path / "accepted.jsonl",
        now=datetime(2026, 8, 27, 20, 0, tzinfo=timezone.utc),
    )
    for flag in flags:
        for ov in flag.draft_overrides:
            assert ov["field"] not in {
                "depth_order",
                "depth_slot",
                "player_name",
                "player_id",
            }


def test_queue_and_accept_writes_pending_not_pack_by_default(
    tmp_path: Path, monkeypatch
) -> None:
    proposed = tmp_path / "proposed"
    pending = tmp_path / "pending"
    accepted_log = tmp_path / "accepted.jsonl"
    pack_copy = tmp_path / "pack.json"
    pack_copy.write_text(PACK_PATH.read_text(encoding="utf-8"), encoding="utf-8")

    flags = scan_camp_sot_flags(
        camp_dir=CAMP_DIR,
        pack_path=PACK_PATH,
        proposed_dir=proposed,
        accepted_log=accepted_log,
        now=datetime(2026, 8, 27, 20, 0, tzinfo=timezone.utc),
    )
    cle = next(f for f in flags if f.flag_id == "2026-08-26:CLE")
    written = queue_flags([cle], proposed_dir=proposed)
    assert len(written) == 1
    proposal_path = written[0]
    doc = json.loads(proposal_path.read_text(encoding="utf-8"))
    assert doc["requires_human_accept"] is True
    assert doc["overrides"]

    before = json.loads(pack_copy.read_text(encoding="utf-8"))
    result = accept_proposal(
        proposal_path,
        pack_path=pack_copy,
        pending_dir=pending,
        accepted_log=accepted_log,
        write_pack=False,
    )
    assert result["wrote_pack"] is False
    assert Path(result["pending"]).is_file()
    after = json.loads(pack_copy.read_text(encoding="utf-8"))
    assert after == before
    assert "2026-08-26:CLE" in accepted_log.read_text(encoding="utf-8")


def test_accept_write_applies_via_daily_intel(tmp_path: Path) -> None:
    proposed = tmp_path / "proposed"
    pending = tmp_path / "pending"
    accepted_log = tmp_path / "accepted.jsonl"
    pack_copy = tmp_path / "pack.json"
    pack_copy.write_text(PACK_PATH.read_text(encoding="utf-8"), encoding="utf-8")

    flags = scan_camp_sot_flags(
        camp_dir=CAMP_DIR,
        pack_path=pack_copy,
        proposed_dir=proposed,
        accepted_log=accepted_log,
        now=datetime(2026, 8, 27, 20, 0, tzinfo=timezone.utc),
    )
    hou = next((f for f in flags if f.flag_id == "2026-08-26:HOU"), None)
    # Prefer a flag that drafts injury_status out when player is on pack.
    candidate = next(
        (
            f
            for f in flags
            if any(o.get("field") == "injury_status" for o in f.draft_overrides)
        ),
        hou,
    )
    assert candidate is not None
    assert candidate.draft_overrides
    path = queue_flags([candidate], proposed_dir=proposed)[0]

    result = accept_proposal(
        path,
        pack_path=pack_copy,
        pending_dir=pending,
        accepted_log=accepted_log,
        write_pack=True,
    )
    assert result["wrote_pack"] is True
    assert result["apply"]["applied"]
    disk = json.loads(pack_copy.read_text(encoding="utf-8"))
    ov = candidate.draft_overrides[0]
    layer = ov.get("layer") or "rows"
    matched = next(
        r
        for r in disk.get(layer, [])
        if r.get("player_name") == ov["player_name"]
        and str(r.get("team") or "").upper() in {ov["team"], "LA", "LAR"}
    )
    assert matched.get(ov["field"]) == ov["after"]
    # Same mutation via daily-intel helper on a fresh pack copy.
    dry = apply_intel_overrides(
        json.loads(PACK_PATH.read_text(encoding="utf-8")),
        [ov],
        as_of=candidate.desk_date,
    )
    assert dry.applied


def test_out_draft_does_not_mark_committee_mates(tmp_path: Path) -> None:
    """'Scourton out… Hubbard and Brooks committee' must not IR the RBs."""
    flags = scan_camp_sot_flags(
        camp_dir=CAMP_DIR,
        pack_path=PACK_PATH,
        proposed_dir=tmp_path / "proposed",
        accepted_log=tmp_path / "accepted.jsonl",
        now=datetime(2026, 8, 27, 20, 0, tzinfo=timezone.utc),
    )
    car = next(f for f in flags if f.flag_id == "2026-08-26:CAR")
    injured = {
        d["player_name"]
        for d in car.draft_overrides
        if d.get("field") == "injury_status" and d.get("after") == "out"
    }
    assert "Chuba Hubbard" not in injured
    assert "Jonathon Brooks" not in injured
    assert "Rico Dowdle" not in injured


def test_named_starter_draft_only_for_named_qb(tmp_path: Path) -> None:
    flags = scan_camp_sot_flags(
        camp_dir=CAMP_DIR,
        pack_path=PACK_PATH,
        proposed_dir=tmp_path / "proposed",
        accepted_log=tmp_path / "accepted.jsonl",
        now=datetime(2026, 8, 27, 20, 0, tzinfo=timezone.utc),
    )
    cle = next(f for f in flags if f.flag_id == "2026-08-26:CLE")
    named = [
        d["player_name"]
        for d in cle.draft_overrides
        if d.get("field") == "competition_status" and d.get("after") == "named_starter"
    ]
    assert named == ["Deshaun Watson"]


def test_proposal_doc_schema() -> None:
    flags = scan_camp_sot_flags(
        camp_dir=CAMP_DIR,
        pack_path=PACK_PATH,
        proposed_dir=Path("/tmp/unused-proposed"),
        accepted_log=Path("/tmp/unused-accepted.jsonl"),
        now=datetime(2026, 8, 27, 20, 0, tzinfo=timezone.utc),
    )
    doc = proposal_doc_for_flag(flags[0])
    assert doc["schema"] == "nfl-camp-sot-proposal/v1"
    assert doc["source"] == "camp_desk"
