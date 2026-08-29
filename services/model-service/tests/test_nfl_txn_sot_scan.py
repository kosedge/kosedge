"""Txn feed → DepthSot T1 scanner — propose only; no pack/means mutation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.services.nfl_camp_sot_queue import load_pack
from src.services.nfl_daily_intel import apply_intel_overrides
from src.services.nfl_txn_sot_scan import (
    FORBIDDEN_FEED_FIELDS,
    NOTES_MAY_TOUCH_MEANS,
    PROPOSALS_MAY_AUTO_APPLY,
    TxnFeedEvent,
    index_pack_players,
    map_feed_player_to_pack,
    proposal_doc_for_txn_flag,
    queue_txn_flags,
    scan_txn_flags,
    sleeper_players_to_events,
    txn_work_item_id,
)

PACK_PATH = (
    Path(__file__).resolve().parents[1]
    / "src/services/nfl_season_engine/data/nfl_depth_chart_2026_w1.json"
)


def _pack() -> dict:
    return json.loads(PACK_PATH.read_text(encoding="utf-8"))


def test_feed_cannot_mutate_pack_or_means(tmp_path: Path) -> None:
    pack_copy = tmp_path / "pack.json"
    pack_copy.write_text(PACK_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    before = pack_copy.read_text(encoding="utf-8")
    events = [
        TxnFeedEvent(
            source="sleeper",
            event="ir",
            as_of_date="2026-08-29",
            team="NYG",
            player_name="Tyrone Tracy Jr.",
            position="RB",
            gsis_id="00-0039384",
        )
    ]
    flags = scan_txn_flags(
        events=events,
        pack_path=pack_copy,
        proposed_dir=tmp_path / "queue",
        accepted_log=tmp_path / "accepted.jsonl",
        now=datetime(2026, 8, 29, 18, 0, tzinfo=timezone.utc),
    )
    queue_txn_flags(flags, proposed_dir=tmp_path / "queue", accepted_log=tmp_path / "a.jsonl")
    assert pack_copy.read_text(encoding="utf-8") == before
    assert NOTES_MAY_TOUCH_MEANS is False
    assert PROPOSALS_MAY_AUTO_APPLY is False
    # Empty overrides leave means untouched.
    dry = apply_intel_overrides(load_pack(pack_copy), [], as_of="2026-08-29")
    assert dry.applied == []


def test_duplicate_scan_no_dup_items(tmp_path: Path) -> None:
    qdir = tmp_path / "queue"
    log = tmp_path / "accepted.jsonl"
    events = [
        TxnFeedEvent(
            source="sleeper",
            event="ir",
            as_of_date="2026-08-29",
            team="HOU",
            player_name="Graham Mertz",
            position="QB",
            gsis_id="00-0040211",
        )
    ]
    flags = scan_txn_flags(
        events=events,
        pack_path=PACK_PATH,
        proposed_dir=qdir,
        accepted_log=log,
        now=datetime(2026, 8, 29, 18, 0, tzinfo=timezone.utc),
    )
    assert flags
    first = queue_txn_flags(flags, proposed_dir=qdir, accepted_log=log)
    assert first.created
    second = queue_txn_flags(flags, proposed_dir=qdir, accepted_log=log)
    assert not second.created
    assert second.unchanged
    assert len(list(qdir.glob("work-item-*.json"))) == len(first.created)
    # Same key from duplicate event list.
    flags2 = scan_txn_flags(
        events=[*events, *events],
        pack_path=PACK_PATH,
        proposed_dir=qdir,
        accepted_log=log,
        now=datetime(2026, 8, 29, 18, 0, tzinfo=timezone.utc),
    )
    assert len(flags2) == len(flags)
    wid = txn_work_item_id(
        player_id="00-0040211", event="ir", as_of_date="2026-08-29"
    )
    assert flags[0].work_item_id == wid


def test_sleeper_cannot_close_atl_open_race(tmp_path: Path) -> None:
    """Sleeper depth / Q status must never propose competition_status or depth_order."""
    sleeper = {
        "1": {
            "player_id": "1",
            "full_name": "Tua Tagovailoa",
            "team": "ATL",
            "position": "QB",
            "status": "Active",
            "injury_status": None,
            "depth_chart_order": 1,
            "gsis_id": "00-0036212",
        },
        "2": {
            "player_id": "2",
            "full_name": "Michael Penix",
            "team": "ATL",
            "position": "QB",
            "status": "Active",
            "injury_status": "Questionable",
            "depth_chart_order": 2,
            "gsis_id": "00-0039917",
        },
    }
    events = sleeper_players_to_events(sleeper, as_of_date="2026-08-29")
    flags = scan_txn_flags(
        events=events,
        pack_path=PACK_PATH,
        proposed_dir=tmp_path / "queue",
        accepted_log=tmp_path / "accepted.jsonl",
        now=datetime(2026, 8, 29, 18, 0, tzinfo=timezone.utc),
    )
    for flag in flags:
        assert flag.team != "ATL" or flag.tier != "T1" or "competition" not in flag.sot_flag.lower()
        for ov in flag.proposed_patch:
            assert ov["field"] not in FORBIDDEN_FEED_FIELDS
            assert ov["field"] != "competition_status"
            assert ov["field"] != "depth_order"
    # Penix Q may open T2 injury only — never crowns / race close.
    atl = [f for f in flags if f.team == "ATL"]
    for flag in atl:
        doc = proposal_doc_for_txn_flag(flag)
        assert doc["may_auto_apply"] is False
        assert doc["contract"]["feed_may_close_open_races"] is False
        for ov in flag.proposed_patch:
            assert ov["field"] == "injury_status"


def test_fixture_pack_healthy_sleeper_ir_opens_t1(tmp_path: Path) -> None:
    """Pack healthy + Sleeper IR + depth 1–3 → open T1 with injury proposed_patch."""
    payload = _pack()
    # Ensure Higgins is healthy in the fixture pack copy.
    for row in payload.get("rows") or []:
        if row.get("team") == "HOU" and row.get("player_name") == "Jayden Higgins":
            row.pop("injury_status", None)
            row["depth_order"] = 2
    pack_path = tmp_path / "pack.json"
    pack_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    events = [
        TxnFeedEvent(
            source="sleeper",
            event="ir",
            as_of_date="2026-08-29",
            team="HOU",
            player_name="Jayden Higgins",
            position="WR",
            gsis_id="00-0040130",
            depth_chart_order=9,  # Sleeper depth must NOT become WR1
        )
    ]
    flags = scan_txn_flags(
        events=events,
        pack_path=pack_path,
        proposed_dir=tmp_path / "queue",
        accepted_log=tmp_path / "accepted.jsonl",
        now=datetime(2026, 8, 29, 18, 0, tzinfo=timezone.utc),
    )
    assert len(flags) == 1
    flag = flags[0]
    assert flag.tier == "T1"
    assert flag.team == "HOU"
    assert flag.proposed_patch
    assert flag.proposed_patch[0]["field"] == "injury_status"
    assert flag.proposed_patch[0]["after"] == "out"
    assert all(ov["field"] not in FORBIDDEN_FEED_FIELDS for ov in flag.proposed_patch)
    # Live pack already-out players must not re-open.
    live_flags = scan_txn_flags(
        events=[
            TxnFeedEvent(
                source="sleeper",
                event="ir",
                as_of_date="2026-08-29",
                team="HOU",
                player_name="Jayden Higgins",
                position="WR",
                gsis_id="00-0040130",
            ),
            TxnFeedEvent(
                source="sleeper",
                event="ir",
                as_of_date="2026-08-29",
                team="LAC",
                player_name="Tyler Biadasz",
                position="C",
            ),
            TxnFeedEvent(
                source="sleeper",
                event="ir",
                as_of_date="2026-08-29",
                team="BAL",
                player_name="Danny Pinter",
                position="G",
            ),
            TxnFeedEvent(
                source="sleeper",
                event="ir",
                as_of_date="2026-08-29",
                team="NYG",
                player_name="Calvin Austin",
                position="WR",
                gsis_id="00-0037837",
            ),
        ],
        pack_path=PACK_PATH,
        proposed_dir=tmp_path / "q2",
        accepted_log=tmp_path / "a2.jsonl",
        now=datetime(2026, 8, 29, 18, 0, tzinfo=timezone.utc),
    )
    names = {f.title for f in live_flags if f.tier == "T1"}
    assert not any("Higgins" in n for n in names)
    assert not any("Biadasz" in n for n in names)
    assert not any("Pinter" in n for n in names)
    assert not any("Austin" in n for n in names)


def test_map_prefers_gsis_and_ignores_sleeper_depth() -> None:
    idx = index_pack_players(_pack())
    row = map_feed_player_to_pack(
        {
            "gsis_id": "00-0040130",
            "team": "HOU",
            "full_name": "Jayden Higgins",
            "position": "WR",
            "depth_chart_order": 1,  # bait — must not invent WR1
        },
        idx,
    )
    assert row is not None
    assert row["player_id"] == "00-0040130"
    assert int(row["depth_order"]) == 2  # pack SoT depth, not Sleeper
