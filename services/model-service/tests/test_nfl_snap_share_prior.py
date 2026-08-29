"""snap_share_prior on accept — defaults, redistribute, no crowns, fantasy reads same."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.services.nfl_camp_sot_queue import PROPOSALS_MAY_AUTO_APPLY, assert_notes_cannot_touch_lines
from src.services.nfl_daily_intel import ALLOWED_FIELDS, apply_intel_overrides, normalize_override
from src.services.nfl_season_engine.loaders import _role_from_depth_row
from src.services.nfl_snap_share_prior import (
    SNAP_SHARE_PACKAGE_FIELD,
    SNAP_SHARE_PRIOR_FIELD,
    SNAP_SHARE_PRIOR_VERSION,
    default_snap_share_from_depth,
    fantasy_shares_from_pack_rows,
    redistribute_out_snap_share,
    resolve_snap_share_prior,
    validate_no_crown_from_redistribution,
)

PACK_PATH = (
    Path(__file__).resolve().parents[1]
    / "src/services/nfl_season_engine/data/nfl_depth_chart_2026_w1.json"
)


def test_allowed_fields_include_snap_prior_and_package() -> None:
    assert SNAP_SHARE_PRIOR_FIELD in ALLOWED_FIELDS
    assert SNAP_SHARE_PACKAGE_FIELD in ALLOWED_FIELDS
    assert SNAP_SHARE_PRIOR_VERSION == "snap_share_prior_v1"


def test_defaults_from_depth_rank_when_missing() -> None:
    assert resolve_snap_share_prior({"position": "WR", "depth_order": 1}) == pytest.approx(
        default_snap_share_from_depth("WR", 1)
    )
    assert resolve_snap_share_prior({"position": "QB", "depth_order": 2}) == pytest.approx(0.45)
    assert resolve_snap_share_prior(
        {"position": "RB", "depth_order": 2, "snap_share_package": "RB_COMMITTEE"}
    ) == pytest.approx(0.45)


def test_proposed_patch_can_set_prior_and_package() -> None:
    ov = normalize_override(
        {
            "team": "SEA",
            "player_name": "Kenneth Walker III",
            "player_id": "00-0038134",
            "position": "RB",
            "field": "snap_share_prior",
            "before": None,
            "after": 0.55,
            "reason": "desk prior",
            "as_of": "2026-08-29",
            "destination": "sot",
        }
    )
    assert ov["field"] == "snap_share_prior"
    pkg = normalize_override(
        {
            "team": "SEA",
            "player_name": "Kenneth Walker III",
            "field": "snap_share_package",
            "after": "RB_COMMITTEE",
            "reason": "committee package",
            "as_of": "2026-08-29",
            "destination": "sot",
        }
    )
    assert pkg["field"] == "snap_share_package"


def test_out_redistributes_to_existing_committee_no_crown() -> None:
    rows = [
        {
            "team": "ATL",
            "position": "QB",
            "depth_order": 1,
            "player_id": "P1",
            "player_name": "Penix",
            "competition_status": "open_competition",
            "snap_share_prior": 0.55,
        },
        {
            "team": "ATL",
            "position": "QB",
            "depth_order": 2,
            "player_id": "P2",
            "player_name": "Cousin",
            "competition_status": "open_competition",
            "snap_share_prior": 0.45,
        },
    ]
    before = copy.deepcopy(rows)
    rows[0]["injury_status"] = "out"
    result = redistribute_out_snap_share(
        rows, team="ATL", position="QB", out_player_id="P1", out_player_name="Penix"
    )
    assert result["redistributed"] is True
    assert result["crowned"] is False
    assert rows[0]["snap_share_prior"] == 0.0
    assert rows[1]["snap_share_prior"] == pytest.approx(1.0)
    assert rows[1]["depth_order"] == 2
    assert rows[1]["competition_status"] == "open_competition"
    validate_no_crown_from_redistribution(before, rows)


def test_accept_out_via_intel_redistributes_and_fantasy_reads_same() -> None:
    payload = {
        "rows": [
            {
                "team": "HOU",
                "position": "WR",
                "depth_order": 1,
                "player_id": "W1",
                "player_name": "Alpha",
                "snap_share_prior": 0.50,
            },
            {
                "team": "HOU",
                "position": "WR",
                "depth_order": 2,
                "player_id": "W2",
                "player_name": "Bravo",
                "snap_share_prior": 0.30,
            },
            {
                "team": "HOU",
                "position": "WR",
                "depth_order": 3,
                "player_id": "W3",
                "player_name": "Charlie",
                "snap_share_prior": 0.20,
            },
        ]
    }
    result = apply_intel_overrides(
        payload,
        [
            {
                "team": "HOU",
                "player_name": "Alpha",
                "player_id": "W1",
                "position": "WR",
                "field": "injury_status",
                "before": None,
                "after": "out",
                "reason": "IR",
                "as_of": "2026-08-29",
                "destination": "sot",
            }
        ],
        as_of="2026-08-29",
    )
    rows = result.payload["rows"]
    by_id = {r["player_id"]: r for r in rows}
    assert by_id["W1"]["snap_share_prior"] == 0.0
    assert by_id["W1"]["injury_status"] == "out"
    assert by_id["W2"]["depth_order"] == 2
    assert by_id["W3"]["depth_order"] == 3
    # Freed 0.50 split by weights 0.30/0.20 → +0.30 and +0.20
    assert by_id["W2"]["snap_share_prior"] == pytest.approx(0.60)
    assert by_id["W3"]["snap_share_prior"] == pytest.approx(0.40)
    assert result.payload.get("snap_share_redistributions")

    fantasy = fantasy_shares_from_pack_rows(rows, team="HOU", position="WR")
    assert fantasy["W1"] == 0.0
    assert fantasy["W2"] == pytest.approx(by_id["W2"]["snap_share_prior"])
    assert fantasy["W3"] == pytest.approx(by_id["W3"]["snap_share_prior"])


def test_loader_role_reads_pack_snap_share_prior() -> None:
    role, _ = _role_from_depth_row(
        team="SEA",
        pos="RB",
        depth=1,
        name="Walker",
        source="test",
        snap_share_prior=0.58,
    )
    assert role.snap_share == pytest.approx(0.58)

    role_out, _ = _role_from_depth_row(
        team="SEA",
        pos="RB",
        depth=1,
        name="Walker",
        source="test",
        snap_share_prior=0.58,
        injury_status="out",
    )
    assert role_out.snap_share == pytest.approx(0.0)


def test_no_auto_accept_and_no_rest_weather_shock_edits() -> None:
    assert PROPOSALS_MAY_AUTO_APPLY is False
    assert_notes_cannot_touch_lines()
    src = Path(__file__).resolve().parents[1] / "src/services/nfl_snap_share_prior.py"
    text = src.read_text(encoding="utf-8")
    # Doc may mention out-of-scope names; code must not import/edit them.
    body = text.split('"""', 2)[-1]
    assert "SHOCK_TABLE" not in body
    assert "days_rest" not in body
    assert "wind_mph" not in body
    assert "from src.services.nfl_unit_shock" not in body
    assert "from src.services.nfl_rest_weather" not in body


def test_live_pack_unchanged_by_module_import() -> None:
    before = PACK_PATH.read_bytes()
    # Import / resolve only — no pack writes.
    _ = resolve_snap_share_prior({"position": "TE", "depth_order": 1})
    after = PACK_PATH.read_bytes()
    assert before == after
    # Sanity: pack JSON still loads.
    payload = json.loads(after.decode("utf-8"))
    assert isinstance(payload.get("rows"), list)
