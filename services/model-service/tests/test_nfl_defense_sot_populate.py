"""Defense SoT populate — durable IR/out + named starters → T1 (no accept)."""

from __future__ import annotations

import json
from pathlib import Path

from src.services.nfl_camp_sot_queue import assert_notes_cannot_touch_lines
from src.services.nfl_daily_intel import apply_intel_overrides
from src.services.nfl_defense_sot_populate import (
    DURABLE_DEFENSE_FACTS,
    DefensePopulateFact,
    format_populate_table,
    queue_defense_flags,
    scan_defense_populate,
)

PACK_PATH = (
    Path(__file__).resolve().parents[1]
    / "src/services/nfl_season_engine/data/nfl_depth_chart_2026_w1.json"
)


def _blank_defense_pack() -> dict:
    payload = json.loads(PACK_PATH.read_text(encoding="utf-8"))
    payload["defense_roles"] = []
    return payload


def test_contract_notes_cannot_touch_lines() -> None:
    assert_notes_cannot_touch_lines()


def test_scan_opens_t1_for_adams_when_pack_blank() -> None:
    items, table = scan_defense_populate(pack=_blank_defense_pack())
    adams = next(i for i in items if "Adams" in i.title)
    assert adams.tier == "T1"
    assert adams.proposed_patch
    ov = adams.proposed_patch[0]
    assert ov["after"] == "ir"
    assert ov.get("create_if_missing") is True
    assert ov["position"] == "S"
    row = next(r for r in table if r.player == "Jamal Adams")
    assert row.already_in_sot is False
    assert row.proposed_t1 is True


def test_scan_sf_seed_already_in_sot_no_t1() -> None:
    payload = json.loads(PACK_PATH.read_text(encoding="utf-8"))
    _items, table = scan_defense_populate(pack=payload)
    bosa = next(r for r in table if r.player == "Nick Bosa")
    assert bosa.already_in_sot is True
    assert bosa.proposed_t1 is False


def test_scan_does_not_invent_unknown_team_starters() -> None:
    """Only curated durable facts — no 32-team invent."""
    items, _table = scan_defense_populate(pack=_blank_defense_pack())
    teams = {i.team for i in items}
    # Curated set only.
    assert teams <= {"MIN", "CAR", "NO", "SEA", "GB"}
    assert "ATL" not in teams
    assert "DAL" not in teams
    # Every proposed item is a known fact name.
    names = {f.player_name for f in DURABLE_DEFENSE_FACTS}
    for i in items:
        assert any(n in i.title for n in names)


def test_create_if_missing_accept_path_inserts_defense_row(tmp_path: Path) -> None:
    """Accept with create_if_missing seeds blank defense_roles then sets IR."""
    pack = _blank_defense_pack()
    fact = next(f for f in DURABLE_DEFENSE_FACTS if f.player_name == "Jamal Adams")
    items, _ = scan_defense_populate(pack=pack)
    adams = next(i for i in items if "Adams" in i.title)
    result = apply_intel_overrides(pack, adams.proposed_patch, as_of="2026-08-29")
    assert result.applied
    defense = result.payload.get("defense_roles") or []
    hit = next(r for r in defense if r.get("player_name") == "Jamal Adams")
    assert hit["injury_status"] == "ir"
    assert hit["position"] == "S"
    assert hit["team"] == "MIN"
    assert fact.depth_slot == hit.get("depth_slot") or hit.get("depth_slot") == "starter"


def test_clark_not_crowned_starter() -> None:
    items, _ = scan_defense_populate(pack=_blank_defense_pack())
    clark = next(i for i in items if "Clark" in i.title)
    seed = clark.proposed_patch[0].get("seed_row") or {}
    assert seed.get("depth_slot") == "depth"
    assert int(seed.get("depth_order") or 0) == 2


def test_queue_writes_work_items_no_pack_mutation(tmp_path: Path) -> None:
    qdir = tmp_path / "queue"
    pack = _blank_defense_pack()
    before = json.dumps(pack, sort_keys=True)
    items, table = scan_defense_populate(pack=pack, proposed_dir=qdir)
    result = queue_defense_flags(items, proposed_dir=qdir)
    assert result.created
    assert list(qdir.glob("work-item-*.json"))
    assert json.dumps(pack, sort_keys=True) == before  # no pack write
    assert "T1" in format_populate_table(table)
    # Idempotent.
    again = queue_defense_flags(items, proposed_dir=qdir)
    assert not again.created
    assert again.unchanged or again.updated is not None


def test_healthy_pack_row_opens_t1_for_durable_out() -> None:
    pack = _blank_defense_pack()
    pack["defense_roles"] = [
        {
            "team": "MIN",
            "position": "S",
            "depth_order": 1,
            "depth_slot": "starter",
            "player_name": "Jamal Adams",
            "player_id": "MIN-S-ADAMS",
            "injury_status": "active",
        }
    ]
    items, table = scan_defense_populate(pack=pack)
    adams = next(i for i in items if "Adams" in i.title)
    assert adams.proposed_patch[0]["after"] == "ir"
    assert not adams.proposed_patch[0].get("create_if_missing")
    row = next(r for r in table if r.player == "Jamal Adams")
    assert row.already_in_sot is True
    assert row.proposed_t1 is True


def test_fact_positions_are_first_class_defense() -> None:
    for fact in DURABLE_DEFENSE_FACTS:
        assert isinstance(fact, DefensePopulateFact)
        assert fact.position in {"EDGE", "DL", "LB", "CB", "S"}
