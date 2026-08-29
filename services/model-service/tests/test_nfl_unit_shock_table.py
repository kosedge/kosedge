"""Unit shock table v1 — Pinter-class C + Adams-class S fixtures.

Accept → pack → remat/KEI inherits shock_table_v1. No rest/weather/snap shares.
No double-count of player deletion + full unit wipe.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.services.nfl_camp_sot_queue import accept_proposal, assert_notes_cannot_touch_lines
from src.services.nfl_daily_intel import apply_intel_overrides, kei_smoke_for_teams
from src.services.nfl_kei_week1_reprice import Week1Pack, apply_week1_kei_reprice
from src.services.nfl_unit_shock_table import (
    SHOCK_TABLE_V1,
    SHOCK_TABLE_VERSION,
    UNIT_WIPE_V1,
    collect_shock_table_v1,
    resolve_shock_role,
)

PACK_PATH = (
    Path(__file__).resolve().parents[1]
    / "src/services/nfl_season_engine/data/nfl_depth_chart_2026_w1.json"
)


def _handicap(spread: float = -3.0, total: float = 44.0) -> dict:
    return {"spread_home": spread, "total_mean": total, "home_win_prob": 0.58}


def test_shock_table_v1_keys_are_keystone_only() -> None:
    assert set(SHOCK_TABLE_V1) == {"C", "LT", "EDGE1", "CB1", "S1"}
    assert SHOCK_TABLE_VERSION == "shock_table_v1"


def test_resolve_pinter_class_center_out() -> None:
    row = {
        "team": "BAL",
        "position": "C",
        "depth_order": 99,
        "depth_slot": "out",
        "player_name": "Danny Pinter",
        "injury_status": "out",
        "player_id": "BAL-C-PINTER",
    }
    assert resolve_shock_role(row) == "C"
    result = collect_shock_table_v1(team="BAL", ol_rows=[row])
    assert len(result.role_shocks) == 1
    assert result.role_shocks[0].spread_pts == SHOCK_TABLE_V1["C"]["spread"]
    assert result.role_shocks[0].total_pts == SHOCK_TABLE_V1["C"]["total"]
    assert len(result.unit_wipe_skips) == 1
    assert result.unit_wipe_skips[0].unit == "ol"
    assert result.unit_wipe_skips[0].spread_pts_not_applied == UNIT_WIPE_V1["ol"]["spread"]


def test_resolve_adams_class_safety_out() -> None:
    row = {
        "team": "MIN",
        "position": "S",
        "depth_order": 1,
        "depth_slot": "starter",
        "player_name": "Jamal Adams",
        "injury_status": "ir",
        "player_id": "MIN-S-ADAMS",
    }
    assert resolve_shock_role(row) == "S1"
    result = collect_shock_table_v1(team="MIN", defense_rows=[row])
    assert len(result.role_shocks) == 1
    assert result.role_shocks[0].role == "S1"
    assert result.role_shocks[0].spread_pts == SHOCK_TABLE_V1["S1"]["spread"]
    assert result.unit_wipe_skips[0].unit == "defense"
    # Explicit no double-count: wipe magnitude is logged, not added to role totals.
    spr, tot = result.team_spread_total("MIN")
    assert spr == SHOCK_TABLE_V1["S1"]["spread"]
    assert tot == SHOCK_TABLE_V1["S1"]["total"]
    assert spr < UNIT_WIPE_V1["defense"]["spread"]


def test_no_double_count_role_plus_unit_wipe() -> None:
    """Player deletion shock must not also apply full unit wipe."""
    ol = [
        {
            "team": "BAL",
            "position": "C",
            "depth_order": 99,
            "depth_slot": "out",
            "player_name": "Danny Pinter",
            "injury_status": "out",
            "player_id": "BAL-C-PINTER",
        }
    ]
    result = collect_shock_table_v1(team="BAL", ol_rows=ol)
    spr, _ = result.team_spread_total("BAL")
    # Role only — wipe points stay in skips, never summed into spr.
    assert spr == SHOCK_TABLE_V1["C"]["spread"]
    wipe_added = sum(s.spread_pts_not_applied for s in result.unit_wipe_skips)
    assert wipe_added == UNIT_WIPE_V1["ol"]["spread"]
    assert spr + wipe_added > spr  # wipe exists but is not applied


def test_fixture_pinter_class_c_moves_kei_via_shock_table() -> None:
    """Pinter-class C out → shock_table_v1 C points on remat/KEI path."""
    healthy = Week1Pack(
        loaded=True,
        ol_by_team={
            "BAL": [
                {
                    "team": "BAL",
                    "position": "C",
                    "depth_order": 1,
                    "depth_slot": "starter",
                    "player_name": "Danny Pinter",
                    "injury_status": "active",
                    "player_id": "BAL-C-PINTER",
                }
            ]
        },
    )
    out_pack = Week1Pack(
        loaded=True,
        ol_by_team={
            "BAL": [
                {
                    "team": "BAL",
                    "position": "C",
                    "depth_order": 99,
                    "depth_slot": "out",
                    "player_name": "Danny Pinter",
                    "injury_status": "out",
                    "player_id": "BAL-C-PINTER",
                }
            ]
        },
    )
    # BAL is away at BUF week 1 — use BAL as away so weaker = home more favored.
    healthy_h, healthy_log = apply_week1_kei_reprice(
        handicap=_handicap(),
        home_abbr="BUF",
        away_abbr="BAL",
        week=1,
        season=2026,
        season_type="REG",
        pack=healthy,
    )
    out_h, out_log = apply_week1_kei_reprice(
        handicap=_handicap(),
        home_abbr="BUF",
        away_abbr="BAL",
        week=1,
        season=2026,
        season_type="REG",
        pack=out_pack,
    )
    d_spread = float(out_log["spread_delta"]) - float(healthy_log["spread_delta"])
    d_total = float(out_log["total_delta"]) - float(healthy_log["total_delta"])
    assert abs(d_spread - (-SHOCK_TABLE_V1["C"]["spread"])) < 1e-9
    assert abs(d_total - SHOCK_TABLE_V1["C"]["total"]) < 1e-9
    assert out_h["spread_home"] < healthy_h["spread_home"]
    reasons = " ".join(e["reason"] for e in out_log["applied_factors"])
    assert "Pinter" in reasons and "shock_table_v1" in reasons
    skipped = " ".join(e["reason"] for e in out_log["considered_not_applied"])
    assert "unit wipe skipped" in skipped
    assert "ol_out" not in reasons  # no flat double-count label


def test_fixture_adams_class_s_moves_kei_via_shock_table() -> None:
    """Adams-class S1 IR → shock_table_v1 S1; no defense unit wipe stacked."""
    healthy = Week1Pack(
        loaded=True,
        defense_by_team={
            "MIN": [
                {
                    "team": "MIN",
                    "position": "S",
                    "depth_order": 1,
                    "depth_slot": "starter",
                    "player_name": "Jamal Adams",
                    "injury_status": "active",
                    "player_id": "MIN-S-ADAMS",
                }
            ]
        },
    )
    out_pack = Week1Pack(
        loaded=True,
        defense_by_team={
            "MIN": [
                {
                    "team": "MIN",
                    "position": "S",
                    "depth_order": 1,
                    "depth_slot": "starter",
                    "player_name": "Jamal Adams",
                    "injury_status": "ir",
                    "player_id": "MIN-S-ADAMS",
                }
            ]
        },
    )
    healthy_h, healthy_log = apply_week1_kei_reprice(
        handicap=_handicap(),
        home_abbr="MIN",
        away_abbr="GB",
        week=1,
        season=2026,
        season_type="REG",
        pack=healthy,
    )
    out_h, out_log = apply_week1_kei_reprice(
        handicap=_handicap(),
        home_abbr="MIN",
        away_abbr="GB",
        week=1,
        season=2026,
        season_type="REG",
        pack=out_pack,
    )
    d_spread = float(out_log["spread_delta"]) - float(healthy_log["spread_delta"])
    assert abs(d_spread - SHOCK_TABLE_V1["S1"]["spread"]) < 1e-9
    assert out_h["spread_home"] > healthy_h["spread_home"]  # home weaker
    reasons = " ".join(e["reason"] for e in out_log["applied_factors"])
    assert "Adams" in reasons and "S1" in reasons and "shock_table_v1" in reasons
    skipped = " ".join(e["reason"] for e in out_log["considered_not_applied"])
    assert "unit wipe skipped" in skipped and "defense" in skipped


def test_accept_pinter_class_c_smoke_line_delta(tmp_path: Path) -> None:
    """DepthSot accept C→out on pack copy → KEI smoke uses shock_table_v1."""
    assert_notes_cannot_touch_lines()
    pack_copy = tmp_path / "pack.json"
    payload = json.loads(PACK_PATH.read_text(encoding="utf-8"))
    # Ensure a healthy C starter exists for the accept transition (fixture room).
    payload["ol_roles"] = [
        r
        for r in (payload.get("ol_roles") or [])
        if not (
            r.get("team") == "BAL"
            and r.get("position") == "C"
            and "Pinter" in str(r.get("player_name") or "")
        )
    ] + [
        {
            "team": "BAL",
            "position": "C",
            "depth_order": 1,
            "depth_slot": "starter",
            "player_name": "Danny Pinter",
            "player_id": "BAL-C-PINTER-FIXTURE",
            "injury_status": "active",
            "role_note": "Fixture healthy C before Pinter-class out accept.",
        }
    ]
    pack_copy.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    work = {
        "schema": "depth_sot_work_item.v1",
        "work_item_id": "work:unit-shock-fixture:BAL-C:2026-08-29",
        "tier": "T1",
        "team": "BAL",
        "as_of": "2026-08-29",
        "sot_flag": "Pinter-class C out fixture — shock_table_v1 only",
        "proposed_patch": {
            "overrides": [
                {
                    "team": "BAL",
                    "player_name": "Danny Pinter",
                    "player_id": "BAL-C-PINTER-FIXTURE",
                    "position": "C",
                    "layer": "ol_roles",
                    "field": "injury_status",
                    "before": "active",
                    "after": "out",
                    "destination": "kei_only",
                    "reason": "fixture Pinter-class C out",
                    "as_of": "2026-08-29",
                    "confidence": "high",
                }
            ]
        },
    }
    proposal = tmp_path / "work-item-BAL-C.json"
    proposal.write_text(json.dumps(work, indent=2) + "\n", encoding="utf-8")
    before = json.loads(pack_copy.read_text(encoding="utf-8"))
    before_smoke = kei_smoke_for_teams(before, ["BAL"])
    result = accept_proposal(
        proposal,
        pack_path=pack_copy,
        pending_dir=tmp_path / "pending",
        accepted_log=tmp_path / "accepted.jsonl",
        receipts_dir=tmp_path / "receipts",
        write_pack=True,
        rematerialize=False,
        actor="fixture",
        reason="Pinter-class C shock_table_v1 fixture",
    )
    assert result.get("disposition") == "accepted" or result.get("status") in {
        "accepted",
        "ok",
        "accepted_pack_written",
    } or "accepted" in str(result.get("disposition") or result.get("status") or "").lower()
    after = json.loads(pack_copy.read_text(encoding="utf-8"))
    after_smoke = kei_smoke_for_teams(after, ["BAL"])
    moved = False
    for row in after_smoke:
        prev = next((r for r in before_smoke if r.get("game") == row.get("game")), {})
        ds = float(row.get("spread_delta") or 0) - float(prev.get("spread_delta") or 0)
        if abs(ds) > 1e-9:
            moved = True
            factors = " ".join(row.get("factors") or [])
            assert "shock_table_v1" in factors or abs(ds) >= SHOCK_TABLE_V1["C"]["spread"] - 1e-6
    assert moved, "BAL C out must move Week 1 KEI via shock_table_v1"


def test_accept_adams_class_s_smoke_line_delta(tmp_path: Path) -> None:
    """Accept S1→IR on pack copy → KEI smoke; no unit wipe double-count."""
    assert_notes_cannot_touch_lines()
    pack_copy = tmp_path / "pack.json"
    payload = json.loads(PACK_PATH.read_text(encoding="utf-8"))
    defense = list(payload.get("defense_roles") or [])
    defense.append(
        {
            "team": "MIN",
            "position": "S",
            "depth_order": 1,
            "depth_slot": "starter",
            "player_name": "Jamal Adams",
            "player_id": "MIN-S-ADAMS-FIXTURE",
            "injury_status": "active",
            "role_note": "Adams-class S fixture seed — accept path only.",
        }
    )
    payload["defense_roles"] = defense
    pack_copy.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    override = {
        "team": "MIN",
        "player_name": "Jamal Adams",
        "player_id": "MIN-S-ADAMS-FIXTURE",
        "position": "S",
        "layer": "defense_roles",
        "field": "injury_status",
        "before": "active",
        "after": "ir",
        "destination": "kei_only",
        "reason": "fixture Adams-class S IR",
        "as_of": "2026-08-29",
        "confidence": "high",
    }
    before = json.loads(pack_copy.read_text(encoding="utf-8"))
    before_smoke = kei_smoke_for_teams(before, ["MIN"])
    applied = apply_intel_overrides(before, [override], as_of="2026-08-29")
    after_smoke = kei_smoke_for_teams(applied.payload, ["MIN"])
    deltas = []
    for row in after_smoke:
        prev = next((r for r in before_smoke if r.get("game") == row.get("game")), {})
        ds = float(row.get("spread_delta") or 0) - float(prev.get("spread_delta") or 0)
        if abs(ds) > 1e-9:
            deltas.append(ds)
            factors = " ".join(row.get("factors") or [])
            not_app = " ".join(row.get("not_applied") or [])
            assert "shock_table_v1" in factors or "Adams" in factors
            # Wipe must not be in applied factors.
            assert "unit wipe" not in factors.lower() or "skipped" in not_app.lower()
    assert deltas, "MIN S1 IR must move Week 1 KEI via shock_table_v1"
