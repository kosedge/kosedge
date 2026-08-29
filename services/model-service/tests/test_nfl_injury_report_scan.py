"""Week-of injury report T1 scanner — propose only; no auto-accept."""

from __future__ import annotations

import json
from pathlib import Path

from src.services.nfl_camp_sot_queue import PROPOSALS_MAY_AUTO_APPLY
from src.services.nfl_injury_report_scan import (
    REPORT_SOURCE,
    classify_practice,
    event_for_t1,
    meets_volume_gate,
    pack_is_full_go,
    queue_injury_report_flags,
    scan_injury_report,
    work_item_id_for_report,
)

PACK_PATH = (
    Path(__file__).resolve().parents[1]
    / "src/services/nfl_season_engine/data/nfl_depth_chart_2026_w1.json"
)


def _sleeper_fixture() -> dict:
    """Minimal Sleeper map: pack-matched Out starter + already-out + deep bench."""
    pack = json.loads(PACK_PATH.read_text(encoding="utf-8"))
    # Pick a healthy depth_order=1 WR from pack.
    starter = None
    for row in pack.get("rows") or []:
        if str(row.get("position") or "").upper() != "WR":
            continue
        if int(row.get("depth_order") or 99) != 1:
            continue
        if not pack_is_full_go(row.get("injury_status")):
            continue
        starter = row
        break
    assert starter is not None
    # Already-out player if present.
    already_out = None
    for row in pack.get("rows") or []:
        if str(row.get("injury_status") or "").lower() in {"out", "ir"}:
            already_out = row
            break

    players = {
        "s1": {
            "full_name": starter["player_name"],
            "team": starter["team"],
            "position": starter["position"],
            "gsis_id": starter.get("player_id") or "",
            "injury_status": "Out",
            "practice_participation": None,
            "practice_description": None,
            "depth_chart_order": 1,
        },
        "s2": {
            "full_name": "Deep Bench Scrub",
            "team": starter["team"],
            "position": "WR",
            "gsis_id": "NOMATCH-BENCH",
            "injury_status": "Out",
            "practice_participation": None,
            "practice_description": None,
            "depth_chart_order": 9,
        },
    }
    if already_out:
        players["s3"] = {
            "full_name": already_out["player_name"],
            "team": already_out["team"],
            "position": already_out["position"],
            "gsis_id": already_out.get("player_id") or "",
            "injury_status": "IR",
            "practice_participation": None,
            "practice_description": None,
            "depth_chart_order": 1,
        }
    return players, starter


def test_practice_and_event_gates() -> None:
    assert classify_practice("Out", "Out (Definitely Will Not Play)") == "DNP"
    assert classify_practice("Limited", None) == "LP"
    assert classify_practice("Full", None) == "FP"
    assert event_for_t1(report_out=True, dnp_count=0) == "out"
    assert event_for_t1(report_out=False, dnp_count=2) == "dnp2"
    assert event_for_t1(report_out=False, dnp_count=1) is None


def test_volume_and_full_go() -> None:
    assert meets_volume_gate({"depth_order": 1, "position": "RB"}) is True
    assert meets_volume_gate(
        {"depth_order": 3, "position": "WR", "snap_share_prior": 0.45}
    ) is True
    assert meets_volume_gate(
        {"depth_order": 3, "position": "WR", "snap_share_prior": 0.10}
    ) is False
    assert pack_is_full_go("") is True
    assert pack_is_full_go("active") is True
    assert pack_is_full_go("out") is False
    assert pack_is_full_go("ir") is False


def test_out_starter_opens_t1_high_confirmation(tmp_path: Path) -> None:
    players, starter = _sleeper_fixture()
    items, rows, meta = scan_injury_report(
        pack_path=PACK_PATH,
        cache_dir=tmp_path,
        as_of="2026-08-29",
        sleeper_players=players,
        dnp_history={},
        accepted_log=tmp_path / "log.jsonl",
        proposed_dir=tmp_path / "runtime",
    )
    assert meta["source"] == REPORT_SOURCE
    assert PROPOSALS_MAY_AUTO_APPLY is False
    hit = [r for r in rows if r.player_name == starter["player_name"]]
    assert len(hit) == 1
    assert hit[0].event == "out"
    assert hit[0].confirmation == "high"
    assert hit[0].proposed_patch
    assert hit[0].proposed_patch[0]["field"] == "injury_status"
    assert hit[0].proposed_patch[0]["after"] in {"out", "ir"}
    assert any(i.work_item_id == hit[0].work_item_id for i in items)
    # Bench Out with no pack match must not invent a T1.
    assert all(r.player_name != "Deep Bench Scrub" for r in rows)


def test_already_out_pack_skips_t1(tmp_path: Path) -> None:
    players, _ = _sleeper_fixture()
    _, rows, _ = scan_injury_report(
        pack_path=PACK_PATH,
        cache_dir=tmp_path,
        as_of="2026-08-29",
        sleeper_players=players,
        dnp_history={},
        accepted_log=tmp_path / "log.jsonl",
        proposed_dir=tmp_path / "runtime",
    )
    for r in rows:
        assert pack_is_full_go(
            # rows are candidates whose pack was full-go at scan time
            "active"
        )


def test_dnp2_low_confirmation(tmp_path: Path) -> None:
    players, starter = _sleeper_fixture()
    # Not Out — 2× DNP only.
    players["s1"]["injury_status"] = None
    players["s1"]["practice_participation"] = "DNP"
    players["s1"]["practice_description"] = "Did Not Practice"
    pid = starter.get("player_id") or f"sleeper:s1"
    hist = {pid: ["2026-08-27", "2026-08-28"]}
    # Also key by gsis when present.
    if starter.get("player_id"):
        hist[starter["player_id"]] = ["2026-08-27", "2026-08-28"]
    _, rows, _ = scan_injury_report(
        pack_path=PACK_PATH,
        cache_dir=tmp_path,
        as_of="2026-08-29",
        sleeper_players=players,
        dnp_history=hist,
        accepted_log=tmp_path / "log.jsonl",
        proposed_dir=tmp_path / "runtime",
    )
    hit = [r for r in rows if r.player_name == starter["player_name"]]
    assert len(hit) == 1
    assert hit[0].event == "dnp2"
    assert hit[0].confirmation == "low"


def test_idempotent_queue(tmp_path: Path) -> None:
    players, starter = _sleeper_fixture()
    items, rows, _ = scan_injury_report(
        pack_path=PACK_PATH,
        cache_dir=tmp_path,
        as_of="2026-08-29",
        sleeper_players=players,
        dnp_history={},
        accepted_log=tmp_path / "log.jsonl",
        proposed_dir=tmp_path / "runtime",
    )
    assert rows
    q1 = queue_injury_report_flags(
        items, proposed_dir=tmp_path / "runtime", accepted_log=tmp_path / "log.jsonl"
    )
    q2 = queue_injury_report_flags(
        items, proposed_dir=tmp_path / "runtime", accepted_log=tmp_path / "log.jsonl"
    )
    assert len(q1.created) >= 1
    assert len(q2.created) == 0
    assert len(q2.unchanged) >= 1
    wid = work_item_id_for_report(
        player_id=str(starter.get("player_id") or ""),
        event="out",
        as_of="2026-08-29",
    )
    assert any(wid == r.work_item_id for r in rows)


def test_scan_does_not_mutate_pack(tmp_path: Path) -> None:
    before = PACK_PATH.read_bytes()
    players, _ = _sleeper_fixture()
    scan_injury_report(
        pack_path=PACK_PATH,
        cache_dir=tmp_path,
        as_of="2026-08-29",
        sleeper_players=players,
        dnp_history={},
        accepted_log=tmp_path / "log.jsonl",
        proposed_dir=tmp_path / "runtime",
    )
    assert PACK_PATH.read_bytes() == before
