"""Defense depth SoT — same DepthSotWorkItem path as offense; no second queue."""

from __future__ import annotations

import json
from pathlib import Path

from src.services.nfl_camp_sot_queue import (
    NOTES_MAY_TOUCH_MEANS,
    NOTES_MAY_TOUCH_PROPS,
    NOTES_MAY_TOUCH_SPREADS,
    PROPOSALS_MAY_AUTO_APPLY,
    accept_proposal,
    assert_notes_cannot_touch_lines,
)
from src.services.nfl_daily_intel import (
    DEFENSE_POSITIONS,
    PACK_SOT_LAYERS,
    apply_intel_overrides,
    kei_smoke_for_teams,
)
from src.services.nfl_kei_week1_reprice import (
    Week1Pack,
    apply_week1_kei_reprice,
)
from src.services.nfl_season_engine.loaders import load_packaged_depth_chart

PACK_PATH = (
    Path(__file__).resolve().parents[1]
    / "src/services/nfl_season_engine/data/nfl_depth_chart_2026_w1.json"
)

DEFENSE_POS_ORDER = ("EDGE", "DL", "LB", "CB", "S", "NB")


def _handicap(spread: float = -3.0, total: float = 44.0) -> dict:
    return {"spread_home": spread, "total_mean": total, "home_win_prob": 0.58}


def test_pack_has_first_class_defense_positions() -> None:
    payload = json.loads(PACK_PATH.read_text(encoding="utf-8"))
    assert list(payload.get("defense_positions") or []) == list(DEFENSE_POS_ORDER)
    assert DEFENSE_POSITIONS == set(DEFENSE_POS_ORDER)
    assert "defense_roles" in PACK_SOT_LAYERS
    rows = payload.get("defense_roles") or []
    assert rows
    by_pos = {str(r.get("position")): r for r in rows if r.get("team") == "SF"}
    for pos in DEFENSE_POS_ORDER:
        assert pos in by_pos, f"missing SF {pos} defense_roles seed"
        assert by_pos[pos].get("depth_order") == 1
        assert by_pos[pos].get("depth_slot") == "starter"


def test_loaders_expose_defense_roles_in_meta() -> None:
    _rows, meta = load_packaged_depth_chart(2026)
    defense = meta.get("defense_roles") or []
    assert any(r.get("position") == "EDGE" and r.get("team") == "SF" for r in defense)
    assert "EDGE" in (meta.get("defense_positions") or [])


def test_accept_defense_patch_updates_all_defense_positions(tmp_path: Path) -> None:
    """proposed_patch → human accept → pack write for EDGE/DL/LB/CB/S/NB."""
    assert_notes_cannot_touch_lines()
    pack_copy = tmp_path / "pack.json"
    pack_copy.write_text(PACK_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    overrides = []
    for pos in DEFENSE_POS_ORDER:
        overrides.append(
            {
                "team": "SF",
                "player_name": {
                    "EDGE": "Nick Bosa",
                    "DL": "Javon Hargrave",
                    "LB": "Fred Warner",
                    "CB": "Charvarius Ward",
                    "S": "Talanoa Hufanga",
                    "NB": "Deommodore Lenoir",
                }[pos],
                "position": pos,
                "layer": "defense_roles",
                "field": "injury_status",
                "before": "active",
                "after": "out",
                "destination": "kei_only",
                "reason": f"fixture accept {pos}",
                "as_of": "2026-08-29",
                "confidence": "high",
            }
        )
    work = {
        "schema": "depth_sot_work_item.v1",
        "work_item_id": "work:defense-fixture:SF:2026-08-29",
        "tier": "T1",
        "team": "SF",
        "as_of": "2026-08-29",
        "sot_flag": "SF defense fixture outs",
        "proposed_patch": {"overrides": overrides},
    }
    proposal = tmp_path / "work-item-defense-SF.json"
    proposal.write_text(json.dumps(work, indent=2) + "\n", encoding="utf-8")

    before = json.loads(pack_copy.read_text(encoding="utf-8"))
    before_status = {
        r["position"]: r.get("injury_status")
        for r in before["defense_roles"]
        if r.get("team") == "SF"
    }
    assert all(before_status[p] == "active" for p in DEFENSE_POS_ORDER)

    result = accept_proposal(
        proposal,
        pack_path=pack_copy,
        pending_dir=tmp_path / "pending",
        accepted_log=tmp_path / "accepted.jsonl",
        receipts_dir=tmp_path / "receipts",
        write_pack=True,
        rematerialize=False,
        actor="fixture",
        reason="defense accept path",
    )
    assert result["disposition"] == "accepted"
    assert result["wrote_pack"] is True
    after = json.loads(pack_copy.read_text(encoding="utf-8"))
    after_status = {
        r["position"]: r.get("injury_status")
        for r in after["defense_roles"]
        if r.get("team") == "SF"
    }
    for pos in DEFENSE_POS_ORDER:
        assert after_status[pos] == "out"
    # Offense skill rows untouched.
    assert before["rows"] == after["rows"]
    assert before["ol_roles"] == after["ol_roles"]


def test_fixture_starter_edge_out_moves_side_and_total() -> None:
    """Starter EDGE → out moves side + total on surfaces that already consume pack."""
    base = Week1Pack(
        loaded=True,
        skill_by_team={
            "SF": [
                {
                    "team": "SF",
                    "position": "QB",
                    "depth_order": 1,
                    "player_name": "Brock Purdy",
                    "competition_status": "named_starter",
                }
            ],
            "LA": [
                {
                    "team": "LA",
                    "position": "QB",
                    "depth_order": 1,
                    "player_name": "Matthew Stafford",
                    "competition_status": "named_starter",
                }
            ],
        },
        defense_by_team={
            "SF": [
                {
                    "team": "SF",
                    "position": "EDGE",
                    "depth_order": 1,
                    "depth_slot": "starter",
                    "player_name": "Nick Bosa",
                    "injury_status": "active",
                }
            ]
        },
    )
    healthy_h, healthy_log = apply_week1_kei_reprice(
        handicap=_handicap(),
        home_abbr="LA",
        away_abbr="SF",
        week=1,
        season=2026,
        season_type="REG",
        pack=base,
    )
    out_pack = Week1Pack(
        loaded=True,
        skill_by_team=base.skill_by_team,
        defense_by_team={
            "SF": [
                {
                    "team": "SF",
                    "position": "EDGE",
                    "depth_order": 1,
                    "depth_slot": "starter",
                    "player_name": "Nick Bosa",
                    "injury_status": "out",
                }
            ]
        },
    )
    out_h, out_log = apply_week1_kei_reprice(
        handicap=_handicap(),
        home_abbr="LA",
        away_abbr="SF",
        week=1,
        season=2026,
        season_type="REG",
        pack=out_pack,
    )
    d_spread = float(out_log["spread_delta"]) - float(healthy_log["spread_delta"])
    d_total = float(out_log["total_delta"]) - float(healthy_log["total_delta"])
    assert abs(d_spread) > 1e-9, "EDGE out must move side"
    assert abs(d_total) > 1e-9, "EDGE out must move total"
    # Away EDGE out → away weaker → home spread more negative (home more favored).
    assert out_h["spread_home"] < healthy_h["spread_home"]
    assert out_h["total_mean"] > healthy_h["total_mean"]
    reasons = " ".join(e["reason"] for e in out_log["applied_factors"])
    assert "Bosa" in reasons
    assert "defense_roles" in reasons


def test_fixture_accept_edge_out_line_delta_via_smoke(tmp_path: Path) -> None:
    """Accept EDGE out on live pack copy → kei smoke side+total delta."""
    pack_copy = tmp_path / "pack.json"
    payload = json.loads(PACK_PATH.read_text(encoding="utf-8"))
    pack_copy.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    before_smoke = kei_smoke_for_teams(payload, ["SF"])
    overrides = [
        {
            "team": "SF",
            "player_name": "Nick Bosa",
            "position": "EDGE",
            "layer": "defense_roles",
            "field": "injury_status",
            "before": "active",
            "after": "out",
            "destination": "kei_only",
            "reason": "fixture EDGE out",
            "as_of": "2026-08-29",
            "confidence": "high",
        }
    ]
    applied = apply_intel_overrides(payload, overrides, as_of="2026-08-29")
    assert applied.applied
    after_smoke = kei_smoke_for_teams(applied.payload, ["SF"])
    before = {r["game"]: r for r in before_smoke}
    moved = False
    for row in after_smoke:
        prev = before.get(row["game"]) or {}
        ds = float(row.get("spread_delta") or 0) - float(prev.get("spread_delta") or 0)
        dt = float(row.get("total_delta") or 0) - float(prev.get("total_delta") or 0)
        if abs(ds) > 1e-9 and abs(dt) > 1e-9:
            moved = True
            break
    assert moved, "SF EDGE out must move side and total on W1 smoke"


def test_notes_and_proposals_cannot_write_kei_or_auto_accept() -> None:
    """Notes/Sleeper-style proposals never write KEI; no auto-accept."""
    assert NOTES_MAY_TOUCH_MEANS is False
    assert NOTES_MAY_TOUCH_PROPS is False
    assert NOTES_MAY_TOUCH_SPREADS is False
    assert PROPOSALS_MAY_AUTO_APPLY is False
    assert_notes_cannot_touch_lines()
    payload = json.loads(PACK_PATH.read_text(encoding="utf-8"))
    before_defense = list(payload.get("defense_roles") or [])
    before_rows = list(payload.get("rows") or [])
    # Empty overrides = note prose alone — nothing written.
    dry = apply_intel_overrides(payload, [], as_of="2026-08-29")
    assert dry.applied == []
    assert dry.payload.get("defense_roles") == before_defense
    assert dry.payload.get("rows") == before_rows


def test_offense_depth_sot_unbroken_after_defense_layer() -> None:
    """Skill + OL still load; defense layer does not enter skill rows."""
    rows, meta = load_packaged_depth_chart(2026)
    assert any(r.get("position") == "QB" for r in rows)
    assert not any(r.get("position") in DEFENSE_POSITIONS for r in rows)
    assert meta.get("ol_roles")
    assert meta.get("defense_roles")
    # Pack Week1Pack still indexes skill for existing KEI paths.
    pack = Week1Pack.from_payload(json.loads(PACK_PATH.read_text(encoding="utf-8")))
    assert pack.loaded
    assert pack.skill("KC")
    assert pack.defense("SF")
